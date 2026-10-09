"""[ADR-105] C-5 의 단일 결정 지점 배선 — reach 를 AST 로 고정한다.

사고: config/qc_levels.json 의 정적 `solvent_line`(acetonitrile ε 35.7)이
`qc_adapter.sh:sei_qc_input` 에 그대로 스플라이스되어 P1/P1b/P5 가 14,464 core-h 를
잘못된 용매에서 돌았다(ADR-066/067 재발, 열한 번째 인스턴스). C-5 precheck 는
endpoint_prep.sh **하나에만** 있었다 — "wired, but not everywhere".

여기서 고정하는 것:
  1. resolve_solvent_line 이 qc_adapter.sh 의 heredoc 에서 **실제 ast.Call 로** 호출된다
     (이름 등장이 아니라 호출 — ADR-092: name-occurrence sweep 은 두 번 틀렸다).
  2. 어떤 payload 도 다른 경로로 scrf/용매 줄을 만들지 않는다.
  3. config 에 이름-용매 route 가 남아 있지 않다.
  4. 거부의 방향: 결정이 없으면 이름 있는 용매가 아니라 **거부**가 나온다.
"""

import json
import os
import re
import unittest

import context  # noqa: F401
from sei_pilot import solvent
from test_guard_reach import _called_names_in_heredocs

PKG = context.PKG_ROOT
PAYLOAD_DIR = os.path.join(PKG, "payload")


class TestReachByAst(unittest.TestCase):
    def test_resolve_solvent_deck_is_actually_called_from_qc_adapter(self):
        """ADR-105 항목 3: solvent.py 에 외부 호출자가 있어야 한다 — AST Call 로 확인.
        [P-0] deck 형(route 조각 + read 섹션) 호출로 바뀌었다; 라인 래퍼든 deck 이든
        결정은 같은 한 곳(resolve_solvent_deck)이다."""
        called = _called_names_in_heredocs(os.path.join(PAYLOAD_DIR, "qc_adapter.sh"))
        self.assertTrue({"resolve_solvent_deck", "resolve_solvent_line"} & called,
                        "qc_adapter.sh 가 단일 결정 지점을 호출하지 않는다 — "
                        "정적 config 스플라이스로 되돌아갔을 가능성")

    def test_endpoint_prep_precheck_calls_the_same_single_decision(self):
        called = _called_names_in_heredocs(os.path.join(PAYLOAD_DIR, "endpoint_prep.sh"))
        self.assertIn("resolve_solvent_line", called)
        self.assertNotIn("solvent_line", called,
                         "endpoint_prep 이 결정 지점을 우회해 SMD 전용 규칙을 직접 부른다")


class TestNoOtherPathEmitsASolventLine(unittest.TestCase):
    def test_no_payload_carries_a_literal_scrf_fragment(self):
        """route 의 scrf 조각은 config 템플릿 + resolve_solvent_line 으로만 만들어진다."""
        offenders = []
        for name in sorted(os.listdir(PAYLOAD_DIR)):
            if not name.endswith(".sh"):
                continue
            for i, line in enumerate(open(os.path.join(PAYLOAD_DIR, name),
                                          errors="replace"), start=1):
                if line.strip().startswith("#"):
                    continue
                # `scrf=` = 방출 형태의 리터럴만 잡는다 (parse_scrf_dielectric 같은
                # 파서 **호출**은 방출 경로가 아니다).
                if "scrf=" in line.lower():
                    offenders.append("%s:%d" % (name, i))
        self.assertEqual([], offenders,
                         "payload 가 scrf 조각을 직접 만들고 있다: %s" % offenders)

    def test_config_route_templates_never_name_a_solvent(self):
        cfg = json.load(open(os.path.join(PKG, "config", "qc_levels.json")))
        g = cfg["gaussian16"]
        for jt, tmpl in g["job_types"].items():
            self.assertNotIn(solvent.FORBIDDEN_FALLBACK, tmpl,
                             "job_type %s 에 이름-용매가 남아 있다" % jt)
            m = re.search(r"solvent=(\w+)", tmpl)
            self.assertIsNone(m, "job_type %s 가 용매를 이름으로 박았다: %s"
                              % (jt, m and m.group(0)))

    def test_config_levels_carry_no_solvent_line_key(self):
        """그 키가 있으면 누군가 다시 읽는다 — 같은 진실이 두 곳에."""
        cfg = json.load(open(os.path.join(PKG, "config", "qc_levels.json")))
        for key, lvl in cfg["gaussian16"].items():
            if key.startswith("level") and isinstance(lvl, dict):
                self.assertNotIn("solvent_line", lvl,
                                 "%s 에 정적 solvent_line 이 되살아났다" % key)

    def test_solvent_policy_ships_adr108_pcm_unverified(self):
        """지금 이 순간의 진실 (ADR-108): PCM ε=18.5 승인, 단 deck_verified=false —
        후보 덱은 smoke 만 통과하고 본계산은 거부된다. deck_verified 를 올리는 것은
        클러스터 smoke 통과 확인 후 lead/사용자 몫이다 — 조용히 켜지 마라."""
        cfg = json.load(open(os.path.join(PKG, "config", "qc_levels.json")))
        pol = cfg["gaussian16"]["solvent_policy"]
        self.assertEqual("pcm_numeric", pol["model"])
        self.assertEqual(18.5, pol["epsilon"])
        self.assertIs(False, pol["deck_verified"])


class TestTheDecisionRefusesInTheRightDirection(unittest.TestCase):
    def test_no_decision_refuses_and_names_the_incident(self):
        with self.assertRaises(solvent.SolventUndecided) as cm:
            solvent.resolve_solvent_line(None)
        msg = str(cm.exception)
        self.assertIn("acetonitrile", msg)
        self.assertIn("14,464", msg)

    def test_unverified_pcm_deck_never_reaches_a_production_route(self):
        """[P-0 §4] 승인(ADR-108)이 났어도 deck_verified=false 면 본계산 덱은 거부 —
        미검증 덱 위로 8,000 core-h 가 나가는 사고를 코드가 막는다."""
        pol = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": False}
        with self.assertRaises(solvent.SolventUndecided) as cm:
            solvent.resolve_solvent_deck(pol, None, "production")
        self.assertIn("deck_verified", str(cm.exception))

    def test_smoke_gets_the_labelled_candidate_deck(self):
        """[P-0 §1/§3] smoke 경로는 후보 덱을 받되, [UNVERIFIED] 라벨이 붙는다.
        형식: numeric-ε generic + `read` 섹션 (epsilon_scan_line 과 같은 메커니즘,
        ε 는 route 줄이 아니라 read 추가 입력 섹션에)."""
        pol = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": False}
        deck = solvent.resolve_solvent_deck(pol, None, "smoke")
        self.assertEqual("scrf=(pcm,solvent=acetone,read)", deck["route_fragment"])
        self.assertEqual(["eps=18.5"], deck["extra_input_lines"])
        self.assertEqual(solvent.UNVERIFIED_DECK_LABEL, deck["label"])
        self.assertNotIn(solvent.FORBIDDEN_FALLBACK, deck["route_fragment"])

    def test_verified_pcm_deck_opens_production_without_the_label(self):
        pol = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": True}
        deck = solvent.resolve_solvent_deck(pol, None, "production")
        self.assertEqual("scrf=(pcm,solvent=acetone,read)", deck["route_fragment"])
        self.assertIsNone(deck["label"])

    def test_pcm_numeric_with_no_or_named_epsilon_refuses(self):
        self.assertRaises(solvent.SolventUndecided, solvent.resolve_solvent_line,
                          {"model": "pcm_numeric"})
        # ε 가 이름으로 오면(ADR-104 위반) 숫자 변환 실패 → 거부, 예외 누출 아님
        self.assertRaises(solvent.SolventUndecided, solvent.resolve_solvent_line,
                          {"model": "pcm_numeric", "epsilon": "acetonitrile",
                           "deck_verified": True})

    def test_noneq_variants_under_pcm_are_closed_pending_respecification(self):
        pol = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": True}
        for v in ("noneq_write", "noneq_read"):
            self.assertRaises(solvent.SolventUndecided,
                              solvent.resolve_solvent_deck, pol, v, "production")

    def test_smd_path_still_refuses_while_the_table_is_empty(self):
        self.assertRaises(solvent.SolventDescriptorsMissing,
                          solvent.resolve_solvent_line,
                          {"model": "smd_descriptors"})

    def test_smd_path_emits_generic_when_descriptors_are_supplied(self):
        """양성 대조군(H-2 의 satisfiability): 거부만 하는 결정 지점은 죽은 것과
        구별되지 않는다. [FIXTURE] 기술자로 실제 방출을 확인한다."""
        policy = json.loads(context.TEST_SOLVENT_POLICY_JSON)
        line = solvent.resolve_solvent_line(policy)
        self.assertIn("solvent=generic", line)
        self.assertNotIn(solvent.FORBIDDEN_FALLBACK, line)

    def test_noneq_variants_compose_on_the_emitted_line(self):
        policy = json.loads(context.TEST_SOLVENT_POLICY_JSON)
        w = solvent.resolve_solvent_line(policy, "noneq_write")
        r = solvent.resolve_solvent_line(policy, "noneq_read")
        self.assertIn(",NonEq=write)", w)
        self.assertIn(",NonEq=read)", r)
        self.assertIn("solvent=generic", w)

    def test_pcm_fallback_variants_are_closed_pending_respecification(self):
        policy = json.loads(context.TEST_SOLVENT_POLICY_JSON)
        for v in ("noneq_write_pcm", "noneq_read_pcm", "eq_pcm"):
            self.assertRaises(solvent.SolventUndecided,
                              solvent.resolve_solvent_line, policy, v)

    def test_noneq_variant_matches_the_previously_shipped_shape(self):
        """이전에 실려 나간 형태와 같은 자리(scrf 괄호 안 마지막 항목)에 삽입된다."""
        self.assertEqual("scrf=(smd,solvent=generic,read,NonEq=write) Eps=18.5",
                         solvent.noneq_variant(
                             "scrf=(smd,solvent=generic,read) Eps=18.5", "write"))
        self.assertRaises(ValueError, solvent.noneq_variant, "no scrf here", "write")
        self.assertRaises(ValueError, solvent.noneq_variant,
                          "scrf=(smd,solvent=generic,read) x", "sideways")


import shutil
import subprocess
import tempfile


@unittest.skipUnless(shutil.which("bash"), "bash 없음")
class TestPcmCandidateDeckEndToEnd(unittest.TestCase):
    """[P-0] sei_qc_input 이 실제로 쓰는 .gjf 에 후보 PCM 덱이 올바로 들어가는가 —
    route 에 scrf=(pcm,solvent=acetone,read), eps 는 read 추가 입력 섹션(기저 블록 뒤)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_pcm_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.xyz = os.path.join(self.d, "mol.xyz")
        with open(self.xyz, "w") as fh:
            fh.write("2\ntest\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")

    def _gen(self, purpose, deck_verified):
        pol = json.dumps({"model": "pcm_numeric", "epsilon": 18.5,
                          "deck_verified": deck_verified})
        script = ('source "%s/payload/qc_adapter.sh"; '
                  'sei_qc_input "%s/out.gjf" 1 opt_freq 0 1 "%s"'
                  % (PKG, self.d, self.xyz))
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_JOB_DIR=self.d,
                   SEI_TOTAL_CORES="4", SEI_NODE_RAM_GB="16",
                   SEI_SOLVENT_POLICY_JSON=pol)
        if purpose:
            env["SEI_QC_PURPOSE"] = purpose
        return subprocess.run(["bash", "-c", script], env=env,
                              capture_output=True, universal_newlines=True)

    def test_smoke_purpose_writes_the_candidate_deck_with_read_section(self):
        res = self._gen("smoke", False)
        self.assertEqual(0, res.returncode, res.stderr)
        text = open(os.path.join(self.d, "out.gjf")).read()
        route = next(l for l in text.splitlines() if l.startswith("#p "))
        self.assertIn("scrf=(pcm,solvent=acetone,read)", route)
        self.assertNotIn("eps=", route, "ε 는 route 줄이 아니라 read 섹션에 간다")
        # read 섹션은 기저 블록(****) 뒤에 온다
        self.assertIn("eps=18.5", text)
        self.assertGreater(text.rindex("eps=18.5"), text.rindex("****"))
        self.assertTrue(text.endswith("\n\n"))
        meta = json.loads(res.stdout)
        self.assertEqual(solvent.UNVERIFIED_DECK_LABEL, meta["solvent_deck_label"])
        self.assertEqual(["eps=18.5"], meta["solvent_extra_input_lines"])
        self.assertIn(solvent.UNVERIFIED_DECK_LABEL, res.stderr)  # 출력 양쪽 라벨

    def test_production_purpose_is_refused_while_unverified(self):
        res = self._gen(None, False)
        self.assertEqual(4, res.returncode)
        self.assertIn("solvent_refused (C-5)", res.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out.gjf")))

    def test_production_opens_after_verification_without_the_label(self):
        res = self._gen(None, True)
        self.assertEqual(0, res.returncode, res.stderr)
        meta = json.loads(res.stdout)
        self.assertIsNone(meta["solvent_deck_label"])
        self.assertIn("scrf=(pcm,solvent=acetone,read)", meta["route"])


# [S-1] G16 이 "Normal termination" 과 유전상수 줄을 찍는 목 — ε 실증 경로 검증용.
# 유전상수 문자열은 parse_scrf_dielectric 의 후보 패턴 중 하나를 쓴다(패턴 자체가
# [UNVERIFIED] 후보라는 사실은 파서 쪽 주석에 있다 — 이 테스트는 파서의 동작을 고정).
MOCK_G16_PCM = r"""#!/bin/bash
cat > /dev/null
echo " Entering Gaussian System, Link 0=g16"
if [ "${MOCK_PRINT_EPS:-1}" = "1" ]; then
  echo " Dielectric constant of the solvent =    ${MOCK_EPS_VALUE:-18.5000}"
fi
echo " SCF Done:  E(RwB97XD) =  -1.100000000     A.U. after   5 cycles"
echo " Normal termination of Gaussian 16 at Sun Aug 17 12:00:00 2026."
exit 0
"""

PCM_UNVERIFIED_POLICY = ('{"model": "pcm_numeric", "epsilon": 18.5, '
                         '"deck_verified": false}')


@unittest.skipUnless(shutil.which("bash"), "bash 없음")
class TestS1EpsilonVerificationInSmoke(unittest.TestCase):
    """[S-1] smoke 가 route echo 만 보지 않고 **G16 출력의 유전상수**를 요청 ε 와
    대조한다 — eps 는 read 추가 입력 섹션에 있어, G16 이 그 섹션을 무시해도 route
    echo 는 멀쩡하다는 것이 이 검사의 존재 이유다. 매치되면 같은 잡의 본계산
    게이트가 열린다(한 왕복 설계)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_s1_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        with open(os.path.join(self.bin, "g16"), "w") as fh:
            fh.write(MOCK_G16_PCM)
        os.chmod(os.path.join(self.bin, "g16"), 0o755)

    def _smoke(self, extra_env=None):
        script = ('source "%s/payload/qc_adapter.sh"; '
                  'SEI_QC=gaussian16; SEI_QC_BIN="%s/g16"; export SEI_QC SEI_QC_BIN; '
                  'sei_qc_smoke' % (PKG, self.bin))
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_JOB_DIR=self.d,
                   SEI_TOTAL_CORES="2", SEI_NODE_RAM_GB="8",
                   SEI_SOLVENT_POLICY_JSON=PCM_UNVERIFIED_POLICY,
                   PATH=self.bin + os.pathsep + os.environ.get("PATH", ""))
        env.update(extra_env or {})
        return subprocess.run(["bash", "-c", script], env=env,
                              capture_output=True, universal_newlines=True)

    def _verification(self):
        with open(os.path.join(self.d, "deck_verification.json")) as fh:
            return json.load(fh)

    def test_matching_eps_in_g16_output_verifies_the_deck_in_run(self):
        res = self._smoke()
        self.assertEqual(0, res.returncode, res.stdout + res.stderr)
        self.assertIn("smoke_eps_verification=ok", res.stdout)
        v = self._verification()
        self.assertTrue(v["eps_matched"])
        self.assertEqual(18.5, v["eps_requested"])
        self.assertTrue(v["evidence_lines"], "증거 원문 없이 통과했다")
        self.assertEqual(solvent.VERIFIED_IN_RUN_LABEL, v["label"])
        # 🔒 같은 잡의 본계산 게이트가 이 기록으로 열린다
        script = ('source "%s/payload/qc_adapter.sh"; '
                  'printf "2\\nt\\nH 0 0 0\\nH 0 0 0.74\\n" > "%s/mol.xyz"; '
                  'sei_qc_input "%s/out.gjf" 1 opt_freq 0 1 "%s/mol.xyz"'
                  % (PKG, self.d, self.d, self.d))
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_JOB_DIR=self.d,
                   SEI_TOTAL_CORES="2", SEI_NODE_RAM_GB="8",
                   SEI_SOLVENT_POLICY_JSON=PCM_UNVERIFIED_POLICY)
        res2 = subprocess.run(["bash", "-c", script], env=env,
                              capture_output=True, universal_newlines=True)
        self.assertEqual(0, res2.returncode, res2.stderr)
        meta = json.loads(res2.stdout)
        self.assertEqual(solvent.VERIFIED_IN_RUN_LABEL, meta["solvent_deck_label"])

    def test_missing_eps_in_g16_output_fails_the_smoke(self):
        """🔴 G16 이 섹션을 무시하는(유전상수 출력 없음) 케이스 — route echo 는
        멀쩡하지만 smoke 가 실패해야 하고, 본계산은 열리면 안 된다."""
        res = self._smoke({"MOCK_PRINT_EPS": "0"})
        self.assertNotEqual(0, res.returncode)
        self.assertIn("smoke_eps_verification=FAILED", res.stdout)
        v = self._verification()
        self.assertFalse(v["eps_matched"])
        self.assertRaises(solvent.SolventUndecided, solvent.resolve_solvent_deck,
                          json.loads(PCM_UNVERIFIED_POLICY), None, "production", v)

    def test_wrong_eps_in_g16_output_fails_the_smoke(self):
        """ε 35.7(acetonitrile 값)이 찍히면 — 정확히 그 사고 — 불일치로 거부."""
        res = self._smoke({"MOCK_EPS_VALUE": "35.7000"})
        self.assertNotEqual(0, res.returncode)
        v = self._verification()
        self.assertFalse(v["eps_matched"])
        self.assertIn(35.7, v["eps_found_values"])


class TestS1ParserAndRuntimeGate(unittest.TestCase):
    def test_parse_scrf_dielectric_collects_values_and_verbatim_lines(self):
        from sei_pilot.criteria import g16 as g16_mod
        text = (" Dielectric constant of the solvent =   18.5000\n"
                " unrelated line\n Eps= 35.7\n")
        rec = g16_mod.parse_scrf_dielectric(text)
        self.assertEqual([18.5, 35.7], rec["values"])
        self.assertEqual(2, len(rec["evidence_lines"]))
        self.assertIn("에코", rec["_echo_caveat"])

    def test_runtime_verification_is_bound_to_the_requested_epsilon(self):
        """다른 ε 로 통과한 기록으로 이 덱을 열 수 없다."""
        good = {"eps_matched": True, "eps_requested": 18.5}
        self.assertTrue(solvent.runtime_verification_ok(good, 18.5))
        self.assertFalse(solvent.runtime_verification_ok(good, 35.7))
        self.assertFalse(solvent.runtime_verification_ok(
            {"eps_matched": False, "eps_requested": 18.5}, 18.5))
        self.assertFalse(solvent.runtime_verification_ok(None, 18.5))

    def test_run_verified_deck_carries_the_in_run_label_not_silence(self):
        pol = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": False}
        rv = {"eps_matched": True, "eps_requested": 18.5}
        deck = solvent.resolve_solvent_deck(pol, None, "production", rv)
        self.assertEqual(solvent.VERIFIED_IN_RUN_LABEL, deck["label"])

    def test_code_never_flips_the_config_flag(self):
        """[S-2] deck_verified 를 올리는 것은 lead 몫 — 코드 어디에도 쓰기가 없다."""
        import re as _re
        src_dir = os.path.join(PKG, "sei_pilot")
        offenders = []
        for root, _d, files in os.walk(src_dir):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                text = open(os.path.join(root, fn), errors="replace").read()
                if _re.search(r'''["']deck_verified["']\s*\]\s*=''', text):
                    offenders.append(fn)
        self.assertEqual([], offenders, "코드가 deck_verified 를 씀 — S-2 위반")


@unittest.skipUnless(shutil.which("bash"), "bash 없음")
class TestPurposeSmugglingIsCutAtTheJobTemplate(unittest.TestCase):
    """🔴 [critic9 BLOCKER 재현] `SEI_QC_PURPOSE=smoke` 가 제출 환경에 남아 있으면
    (#PBS -V 상속) 본계산 payload 전부가 smoke 로 위장해 deck_verified 게이트를
    통과한다 — 잡 템플릿이 잡 시작 시 반드시 unset 해야 한다."""

    def test_all_three_templates_unset_the_purpose_channel(self):
        tdir = os.path.join(PKG, "sei_pilot", "templates")
        for name in ("pbs.sh.tmpl", "slurm.sh.tmpl", "local.sh.tmpl"):
            text = open(os.path.join(tdir, name)).read()
            self.assertIn("unset SEI_QC_PURPOSE", text, name)
            self.assertIn("unset SEI_SOLVENT_POLICY_JSON", text, name)
            self.assertIn("unset SEI_C8_ENDPOINTS_JSON", text, name)
            # [U56-2] #PBS -V 상속 노출 클래스가 같다 — 제출 환경의 낡은 ModRedundant
            # 파일 경로가 잡 안으로 새면 안 된다 (payload 는 호출 시점에 스스로 지정한다).
            self.assertIn("unset SEI_QC_MODREDUNDANT_FILE", text, name)

    def test_the_bypass_input_itself_a_production_job_with_purpose_smoke_in_env(self):
        """우회 입력 그대로: 부모 환경에 SEI_QC_PURPOSE=smoke 를 심고 템플릿 렌더
        스크립트로 본계산 sei_qc_input 을 돌린다 — 그래도 거부돼야 한다."""
        from sei_pilot import scheduler as sch
        from sei_pilot.shellrun import FakeShell
        from sei_pilot.state import Store
        d = tempfile.mkdtemp(prefix="sei_purpose_")
        self.addCleanup(shutil.rmtree, d, True)
        store = Store(d)
        job_dir = store.job_dir("P5")
        payload = os.path.join(d, "prod_payload.sh")
        with open(payload, "w") as fh:
            fh.write('#!/bin/bash\nset -u\n'
                     'source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"\n'
                     'printf "2\\nt\\nH 0 0 0\\nH 0 0 0.74\\n" > "${SEI_JOB_DIR}/mol.xyz"\n'
                     'if sei_qc_input "${SEI_JOB_DIR}/out.gjf" 1 opt_freq 0 1 '
                     '"${SEI_JOB_DIR}/mol.xyz" > "${SEI_JOB_DIR}/meta.json" '
                     '2> "${SEI_JOB_DIR}/meta.err"; then\n'
                     '  echo leaked > "${SEI_JOB_DIR}/leaked.txt"\nfi\nexit 0\n')
        os.chmod(payload, 0o755)
        adapter = sch.LocalAdapter(FakeShell(),
                                   os.path.join(PKG, "sei_pilot", "templates"),
                                   workdir=d)
        spec = sch.JobSpec("P5", "bash %s" % payload, nodes=1, cores_per_node=1,
                           wall_h=0.5, job_dir=job_dir,
                           env={"SEI_PKG_ROOT": PKG, "SEI_WORKDIR": d,
                                "SEI_NODE_RAM_GB": "8"})
        script = adapter.write_script(spec)
        env = dict(os.environ,
                   SEI_QC_PURPOSE="smoke",                       # 우회 시도
                   SEI_SOLVENT_POLICY_JSON=PCM_UNVERIFIED_POLICY)  # 이것도 잘려야 함
        res = subprocess.run(["bash", script], env=env, capture_output=True,
                             universal_newlines=True, timeout=120)
        self.assertFalse(os.path.exists(os.path.join(job_dir, "leaked.txt")),
                         "SEI_QC_PURPOSE=smoke 상속으로 본계산 덱이 나갔다 — "
                         "8,000+ core-h 가 미검증 덱 위로 나가는 그 사고")
        err = open(os.path.join(job_dir, "meta.err"), errors="replace").read()
        self.assertIn("solvent_refused (C-5)", err)


@unittest.skipUnless(shutil.which("bash"), "bash 없음")
class TestRelaxedScanDeckOrderAndSolventWiring(unittest.TestCase):
    """[U56-2 B-1] relaxed_scan job_type — 덱 섹션 순서와 용매 배선.

    스캔 좌표(ModRedundant `B i j S N step`)는 route 가 아니라 추가 입력 섹션으로,
    **좌표 뒤·gen 기저 블록 앞**에 온다. 용매는 다른 모든 job_type 과 같은 단일 결정
    지점({solvent} placeholder → resolve_solvent_deck)을 지난다 — 스캔이라고 예외가
    생기면 그것이 ADR-105 의 12번째 인스턴스다.
    """

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_scan_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.xyz = os.path.join(self.d, "mol.xyz")
        with open(self.xyz, "w") as fh:
            fh.write("2\ntest\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")
        self.section = os.path.join(self.d, "scan_section.txt")
        with open(self.section, "w") as fh:
            fh.write("B 1 2 S 12 0.1000\n")

    def _gen(self, job_type, modred=None, policy=None):
        script = ('source "%s/payload/qc_adapter.sh"; '
                  'sei_qc_input "%s/out.gjf" 3 %s 0 2 "%s"'
                  % (PKG, self.d, job_type, self.xyz))
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_JOB_DIR=self.d,
                   SEI_TOTAL_CORES="4", SEI_NODE_RAM_GB="16",
                   SEI_SOLVENT_POLICY_JSON=policy or json.dumps(
                       {"model": "pcm_numeric", "epsilon": 18.5,
                        "deck_verified": True}))
        if modred:
            env["SEI_QC_MODREDUNDANT_FILE"] = modred
        return subprocess.run(["bash", "-c", script], env=env,
                              capture_output=True, universal_newlines=True)

    def test_relaxed_scan_is_in_the_nosymm_required_list(self):
        """§39.39(b) 조건 2 — scan 도 nosymm 필수 목록에 있어야 B-2(G16 의 점군
        재검출)가 스캔에서 재발하지 않는다."""
        cfg = json.load(open(os.path.join(PKG, "config", "qc_levels.json")))
        g = cfg["gaussian16"]
        self.assertIn("relaxed_scan", g["job_types"])
        self.assertIn("relaxed_scan", g["_nosymm_required_job_types"])
        self.assertIn("nosymm", g["job_types"]["relaxed_scan"])
        self.assertIn("modredundant", g["job_types"]["relaxed_scan"])

    def test_section_order_coords_modredundant_basis_eps(self):
        res = self._gen("relaxed_scan", modred=self.section)
        self.assertEqual(0, res.returncode, res.stderr)
        text = open(os.path.join(self.d, "out.gjf")).read()
        i_coord = text.index(" 0.74000000")             # 좌표 마지막 줄
        i_scan = text.index("B 1 2 S 12 0.1000")
        i_basis = text.index("****")                    # gen 기저 블록
        i_eps = text.rindex("eps=18.5")                 # scrf read 섹션
        self.assertTrue(i_coord < i_scan < i_basis < i_eps,
                        "섹션 순서(좌표→ModRedundant→기저→eps)가 깨졌다:\n" + text)
        meta = json.loads(res.stdout)
        self.assertEqual(["B 1 2 S 12 0.1000"], meta["modredundant_lines"])

    def test_scan_without_a_section_is_refused_not_emitted(self):
        """🔴 섹션 없는 modredundant 덱: G16 이 기저 블록을 ModRedundant 입력으로
        읽어 쓰레기 스캔이 조용히 돈다 — 덱을 내기 전에 멈춰야 한다."""
        res = self._gen("relaxed_scan", modred=None)
        self.assertNotEqual(0, res.returncode)
        self.assertIn("ModRedundant", res.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out.gjf")))

    def test_section_for_a_non_scan_job_type_is_ignored_with_a_warning(self):
        res = self._gen("sp", modred=self.section)
        self.assertEqual(0, res.returncode, res.stderr)
        self.assertIn("무시한다", res.stderr)
        self.assertNotIn("B 1 2 S", open(os.path.join(self.d, "out.gjf")).read())

    def test_scan_solvent_goes_through_the_single_decision_point(self):
        """결정 없음 → 거부. 스캔이라고 이름-용매 폴백이 생기면 안 된다."""
        res = self._gen("relaxed_scan", modred=self.section,
                        policy='{"model": null}')
        self.assertNotEqual(0, res.returncode)
        self.assertIn("solvent_refused (C-5)", res.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.d, "out.gjf")))


class TestLoadPolicy(unittest.TestCase):
    def test_env_injection_wins_and_config_is_the_default(self):
        os.environ["SEI_SOLVENT_POLICY_JSON"] = '{"model": "smd_descriptors"}'
        try:
            self.assertEqual("smd_descriptors", solvent.load_policy()["model"])
        finally:
            del os.environ["SEI_SOLVENT_POLICY_JSON"]
        pol = solvent.load_policy()
        self.assertIsNotNone(pol, "config 의 solvent_policy 블록이 사라졌다")
        self.assertEqual("pcm_numeric", pol["model"])   # ADR-108 상태


class TestEpsInfReachesTheDeckThroughTheAdapter(unittest.TestCase):
    """🔴 [§39.73] The deck-side fix is useless unless the adapter actually passes a value.
    This is the producer/consumer half of it — the shape this project keeps finding.

    🔒 And it is deliberately NOT defaulted in the adapter: §39.73's fix is a BRACKET (run both
    physically admissible ends and see whether the answer moves), so choosing a value in the
    adapter would pre-decide the experiment that decides whether the value matters.
    """

    def test_no_epsinf_plumbing_remains(self):
        """🔒 [USER RULING 2026-08-21] the PCM deck names a carrier solvent; EpsInf is never
        emitted and the adapter no longer reads SEI_QC_EPSINF. A supplied value is ignored."""
        from sei_pilot import solvent
        path = os.path.join(context.PKG_ROOT, "payload", "qc_adapter.sh")
        with open(path, errors="replace") as fh:
            src = fh.read()
        self.assertNotIn("SEI_QC_EPSINF", src)
        policy = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": True}
        deck = solvent.resolve_solvent_deck(policy, eps_inf=1.0)
        self.assertFalse([l for l in deck["extra_input_lines"] if "EpsInf" in l])
        self.assertIn("ignored", deck["_eps_inf_status"])
        self.assertEqual("acetone", deck["carrier_solvent"])



if __name__ == "__main__":
    unittest.main()


class TestCertificateMustMatchProductionMethod(unittest.TestCase):
    """[§39.92/§39.93/§39.101] a certificate is a certificate of a MODEL: level, functional,
    basis, grid and solvent deck must all equal production, else the C-8 guard refuses."""
    POLICY = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": True}

    def _meta(self, **over):
        from sei_pilot import config
        g = config.load("qc_levels.json", {})["gaussian16"]
        m = {"level": "level2", "basis_real_name": g["level2"]["basis_real_name"],
             "route": "#p nosymm %s/gen scrf=(pcm,solvent=acetone,read) opt=(tight,calcfc) "
                      "freq Int(Grid=UltraFine)" % g["level2"]["functional"],
             "solvent_extra_input_lines": ["eps=18.5"]}
        m.update(over)
        return m

    def test_production_certificate_passes(self):
        from sei_pilot import solvent
        ok, why = solvent.certificate_matches_production(self._meta(), self.POLICY, "level2")
        self.assertTrue(ok, why)

    def test_each_axis_is_checked(self):
        from sei_pilot import solvent
        cases = {
            "level": self._meta(level="level3"),
            "basis": self._meta(basis_real_name="def2-SVPD"),
            "grid": self._meta(route=self._meta()["route"].replace(" Int(Grid=UltraFine)", "")),
            "solvent route": self._meta(route=self._meta()["route"].replace("acetone", "generic")),
            "solvent read block": self._meta(solvent_extra_input_lines=["eps=18.5", "EpsInf=18.5"]),
            # [§39.105] P5-style plain `opt` is 30x looser than opt=(tight): not a C-8 certificate
            "opt convergence": self._meta(route=self._meta()["route"].replace("opt=(tight,calcfc)", "opt")),
            "ecp": self._meta(has_ecp=True),
        }
        for name, meta in cases.items():
            ok, why = solvent.certificate_matches_production(meta, self.POLICY, "level2")
            self.assertFalse(ok, name)
            self.assertIn("method_mismatch", why, name)

    def test_not_computed_is_distinguished_from_wrong_model(self):
        from sei_pilot import solvent
        ok, why = solvent.certificate_matches_production({}, self.POLICY, "level2")
        self.assertFalse(ok)
        self.assertIn("not_computed", why)

    def test_real_returned_certificate_is_refused(self):
        """The only converged endpoint on disk was generic+EpsInf=18.5 at level3 -- refused."""
        from sei_pilot import solvent
        p = os.path.join(context.PKG_ROOT, "..", "..", "cpu_machine_pilot_results",
                         "sei_pilot_work", "jobs", "endpoint_prep_reactant_epsinf_full",
                         "endpoint_tight.meta.json")
        if not os.path.exists(p):
            self.skipTest("returned tree not present")
        meta = json.load(open(p))
        ok, why = solvent.certificate_matches_production(meta, self.POLICY, "level2")
        self.assertFalse(ok, why)
        self.assertIn("solvent route", why)


class TestLegacyGenericDeckIsSmokeOnly(unittest.TestCase):
    POLICY = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": True}

    def test_smoke_gets_the_legacy_deck_production_is_refused(self):
        from sei_pilot import solvent
        deck = solvent.resolve_solvent_deck(self.POLICY, "legacy_generic_epsinf", "smoke")
        self.assertEqual("scrf=(pcm,solvent=generic,read)", deck["route_fragment"])
        self.assertEqual(["eps=18.5", "EpsInf=18.5"], deck["extra_input_lines"])
        self.assertRaises(solvent.SolventUndecided, solvent.resolve_solvent_deck,
                          self.POLICY, "legacy_generic_epsinf", "production")

    def test_route_template_exists_and_is_not_nosymm_exempt(self):
        from sei_pilot import config
        jt = config.load("qc_levels.json", {})["gaussian16"]["job_types"]
        self.assertIn("{solvent_legacy_generic_epsinf}", jt["freq_smoke_legacy_generic"])
        self.assertIn("nosymm", jt["freq_smoke_legacy_generic"])
