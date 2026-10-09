"""[C-8-1] TS 전제조건 게이트 — payload/P1.sh 의 실제 실행으로 검증.

사고 (이번 회신 + ADR-066): P1.sh 는 헤더 스스로 "GUESS GEOMETRY (idealized, not
optimized)" 를 선언하는 입력을 그대로 QST2 에 넣었다. 용매상 최적화 0회, CREST 스킵.
02_METHOD_SPEC C-8 은 "양끝단이 같은 level 의 수렴 극소(n_imag=0)가 아니면 TS 탐색은
시작을 거부한다" 인데, `guards.require_ts_precondition` 를 부르는 payload 가 0곳이었다
(C-5 의 ADR-105 와 같은 계열, C-8 은 영 곳). 실측 증상: imag −48.4 cm⁻¹ + IRC 양끝
동일 극소(R3).

이 게이트는 오늘 상태(인증 기록 없음)에서 **반드시 거부한다 — 그게 옳은 동작이다.**
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from test_u27_noneq import MOCK_G16

HAVE_BASH = shutil.which("bash") is not None


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _P1Run(unittest.TestCase):
    INJECT_ENDPOINTS = None     # None = 인증 기록 없음(오늘의 실제 상태)

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_c8_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        mock = os.path.join(self.bin, "g16")
        with open(mock, "w") as fh:
            fh.write(MOCK_G16)
        os.chmod(mock, 0o755)
        self.job_dir = os.path.join(self.d, "jobs", "P1")
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": "P1",
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8",
                    "MOCK_MODE": "accepting", "MOCK_QST2_MODE": "good_ts",
                    "SEI_SOLVENT_POLICY_JSON": context.TEST_SOLVENT_POLICY_JSON,
                    "PATH": self.bin + os.pathsep + env.get("PATH", "")})
        if self.INJECT_ENDPOINTS is not None:
            env["SEI_C8_ENDPOINTS_JSON"] = self.INJECT_ENDPOINTS
        self.proc = subprocess.run(
            ["bash", os.path.join(context.PKG_ROOT, "payload", "P1.sh")],
            env=env, capture_output=True, text=True, timeout=600)

    def decision(self):
        with open(os.path.join(self.job_dir, "c8_precondition.json")) as fh:
            return json.load(fh)


class TestGateRefusesOnTodaysInputs(_P1Run):
    """🔴 사고 재현 입력 그대로: 인증 기록이 어디에도 없는 동봉 guess 두 벌.
    수정 전에는 이 입력에서 QST2 가 그냥 발사됐다(RT-1: 302 core-h → 아티팩트 판정)."""

    INJECT_ENDPOINTS = None

    def test_p1_refuses_with_the_distinct_exit(self):
        self.assertEqual(6, self.proc.returncode,
                         self.proc.stdout[-1500:] + self.proc.stderr[-500:])
        self.assertIn("C-8", self.proc.stdout)

    def test_no_qst2_deck_was_generated(self):
        """거부는 덱 생성 **전**이어야 한다 — 거부하고도 덱이 나갔다면 게이트가 아니다."""
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "ts_qst2.gjf")))
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "ts_qst2.log")))

    def test_decision_record_lands_with_reasons_and_source(self):
        d = self.decision()
        self.assertFalse(d["may_start"])
        self.assertTrue(d["blocking_reasons"])
        self.assertEqual("none_on_record", d["endpoints_source"])
        # unknown 은 허가가 아니다 — n_imag 미지가 사유에 있어야 한다
        self.assertTrue(any("n_imag" in r for r in d["blocking_reasons"]))

    def test_refusal_is_surfaced_by_the_collector_as_a_result_not_a_failure(self):
        from sei_pilot import collect as collect_mod
        from sei_pilot.state import Store
        store = Store(self.d)
        store.mark_done("P1", {"start_epoch": 0, "end_epoch": 60, "rc": 0})
        res = collect_mod.collect_p1(store)
        self.assertIn("c8_precondition", res)
        self.assertTrue(any("c8_refused" in w for w in res.get("warnings") or []),
                        "C-8 거부가 회신 warnings 에 없다 — 측정했는데 안 읽는 값")


class TestGateOpensOnCertifiedEndpoints(_P1Run):
    """[H-2 satisfiability] 거부만 하는 게이트는 죽은 게이트와 구별되지 않는다.
    [FIXTURE] 인증을 주입하면 게이트가 열리고 QST2 가 실제로 발사돼야 한다.
    (판정은 여전히 guard 가 한다 — 주입은 데이터 채널이지 우회가 아니다.)"""

    INJECT_ENDPOINTS = context.TEST_C8_ENDPOINTS_JSON

    def test_gate_passes_and_qst2_launches(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-1500:] + self.proc.stderr[-500:])
        d = self.decision()
        self.assertTrue(d["may_start"])
        self.assertIn("[FIXTURE]", d["endpoints_source"])
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "ts_qst2.log")))

    def test_injected_source_is_labelled_not_presented_as_certification(self):
        self.assertIn("test injection, not a certification",
                      self.decision()["endpoints_source"])


class TestUncertifiedInjectionStillRefuses(_P1Run):
    """주입 채널로도 **미인증 데이터는 거부**된다 — 채널이 우회가 아니라는 증명."""

    INJECT_ENDPOINTS = json.dumps({
        "reactant": {"optimised": False, "converged": True, "n_imag": 0,
                     "level": "level2"},
        "product": {"optimised": True, "converged": True, "n_imag": 0,
                    "level": "level2"},
        "declared_planar": True})

    def test_refused(self):
        self.assertEqual(6, self.proc.returncode)
        self.assertFalse(self.decision()["may_start"])


# =============================================================================================
# [U56-2, ADR-109] payload/U56.sh — 새 TS attempt payload 의 C-8 게이트.
# B0-F 는 level3(geometry+Hessian, C-11 composite)에서 돈다 ⟹ 인증 fixture 도 level3.
# P1 의 level2 fixture 를 재사용하면 "레벨 불일치 거부"와 "인증 없음 거부"가 구분되지
# 않는다 — 그래서 별도 fixture 다.
# =============================================================================================
U56_FIXTURE_CERTS_LEVEL3 = json.dumps({
    "reactant": {"optimised": True, "converged": True, "n_imag": 0, "level": "level3"},
    "product": {"optimised": True, "converged": True, "n_imag": 0, "level": "level3"},
    "declared_planar": True, "_label": "[FIXTURE]"})


#: 🔴 [G-SCAN-4, §39.45(a)/§39.50] 단끝단 arm 은 **GFN2 gate 판정을 상속**해야만 돈다
#: (§39.47(a)). 판정이 없으면 U56.sh 는 DFT 를 발주하지 않는다 ⟹ 통과 경로를 시험하려면
#: 통과 판정을 명시적으로 놓아야 한다. **이 fixture 가 필요하다는 사실 자체가 배선의 증거다.**
#: 값은 §39.48(a)의 n=1(R-A) 실측: 끝점차 0.000 eV / barrier 차 0.013 eV, 문턱 0.05 의 1/4.
U56_FIXTURE_GSCAN_PASS = json.dumps({
    "fired": False, "hamiltonian": "gfn2", "tolerance_ev": 0.05,
    "delta_endpoint_ev": 0.000, "delta_barrier_ev": 0.013,
    "barrier_forward_ev": 0.486, "barrier_reverse_ev": 0.473,
    "reasons": ["[FIXTURE] §39.48(a) n=1 measured values"]})

U56_FIXTURE_GSCAN_FIRED = json.dumps({
    "fired": True, "hamiltonian": "gfn2", "tolerance_ev": 0.05,
    "delta_endpoint_ev": 0.482, "delta_barrier_ev": 0.536,
    "barrier_forward_ev": 0.856, "barrier_reverse_ev": 0.320,
    "reasons": ["[FIXTURE] §39.48(a) n=2 (R-C) measured values -- both conditions violated"]})


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _U56Run(unittest.TestCase):
    REACTION = "R-A"
    METHOD = "relaxed_scan"
    INJECT_ENDPOINTS = None          # None = 인증 기록 없음(오늘의 실제 상태)
    REACTANT_XYZ = "inputs/li_ec_radical_reactant.xyz"
    PRODUCT_XYZ = None
    EXTRA_ENV = {}
    #: 잡 디렉터리에 **실행 전** 놓을 파일 {이름: 내용}. G-SCAN 판정처럼 다른 stage 가
    #: 만들어 주는 산출물을 주입하는 통로다.
    PRE_JOB_FILES = {}

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_u56_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        mock = os.path.join(self.bin, "g16")
        with open(mock, "w") as fh:
            fh.write(MOCK_G16)
        os.chmod(mock, 0o755)
        key = "U56_%s_%s" % (self.REACTION.replace("-", ""), self.METHOD)
        self.job_dir = os.path.join(self.d, "jobs", key)
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))
        for name, body in (self.PRE_JOB_FILES or {}).items():
            with open(os.path.join(self.job_dir, name), "w") as fh:
                fh.write(body)
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": key,
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8",
                    "MOCK_MODE": "accepting",
                    "SEI_U56_REACTION": self.REACTION,
                    "SEI_U56_METHOD": self.METHOD,
                    "SEI_SOLVENT_POLICY_JSON": context.TEST_SOLVENT_POLICY_JSON,
                    "PATH": self.bin + os.pathsep + env.get("PATH", "")})
        if self.REACTANT_XYZ:
            env["SEI_U56_REACTANT_XYZ"] = os.path.join(context.PKG_ROOT,
                                                       self.REACTANT_XYZ)
        if self.PRODUCT_XYZ:
            env["SEI_U56_PRODUCT_XYZ"] = os.path.join(context.PKG_ROOT,
                                                      self.PRODUCT_XYZ)
        if self.INJECT_ENDPOINTS is not None:
            env["SEI_C8_ENDPOINTS_JSON"] = self.INJECT_ENDPOINTS
        env.update(self.EXTRA_ENV)
        self.proc = subprocess.run(
            ["bash", os.path.join(context.PKG_ROOT, "payload", "U56.sh")],
            env=env, capture_output=True, text=True, timeout=600)

    def decision(self):
        with open(os.path.join(self.job_dir, "c8_precondition.json")) as fh:
            return json.load(fh)


class TestU56RefusesWithNoCertOnRecord(_U56Run):
    """🔴 오늘의 실제 상태: endpoint_prep 산출물이 어디에도 없다. 단끝단이어도 C-8 은
    reactant 인증을 요구한다(§39.32 Candidate B: 'it halves the exposure, it does not
    remove it') — 반드시 거부, P1 과 같은 구분 exit 6."""

    INJECT_ENDPOINTS = None

    def test_refused_with_the_distinct_exit(self):
        self.assertEqual(6, self.proc.returncode,
                         self.proc.stdout[-1500:] + self.proc.stderr[-500:])

    def test_no_deck_and_no_mapping_were_generated(self):
        """거부는 덱 생성 **전** — mapping emit 도 덱의 일부이므로 함께 없어야 한다."""
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "scan.gjf")))
        self.assertFalse(os.path.exists(
            os.path.join(self.job_dir, "u56_R-A_mapping.json")))

    def test_decision_record_names_the_unknown(self):
        d = self.decision()
        self.assertFalse(d["may_start"])
        self.assertTrue(any("n_imag" in r for r in d["blocking_reasons"]))

    def test_refusal_is_surfaced_by_the_collector_as_a_result_not_a_failure(self):
        """collect_p1 의 c8_refused 규칙과 동일 — 측정했는데 안 읽는 값 금지."""
        from sei_pilot import collect as collect_mod
        from sei_pilot.state import Store
        store = Store(self.d)
        key = os.path.basename(self.job_dir)
        store.mark_done(key, {"start_epoch": 0, "end_epoch": 60, "rc": 0})
        res = collect_mod.collect_u56(store, key)
        self.assertIsNotNone(res["c8_precondition"])
        self.assertTrue(any("c8_refused" in w for w in res.get("warnings") or []),
                        "C-8 거부가 회신 warnings 에 없다")


class TestU56SingleEndedOpensOnCertifiedReactantOnly(_U56Run):
    """[H-2 satisfiability] reactant 인증만으로 단끝단 게이트가 열리고, 체인
    (scan → mapping/deck → ts_opt → IRC)이 실제로 돈다. product 인증은 요구하지
    않는다 — §39.39(e): 'A product endpoint is NOT on this list.'"""

    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRE_JOB_FILES = {"gscan_verdict.json": U56_FIXTURE_GSCAN_PASS}

    def test_chain_completes(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-800:])
        self.assertTrue(self.decision()["may_start"])

    def test_mapping_is_emitted_beside_the_deck(self):
        """§39.26(d)의 계약 그 자체: 덱(scan.gjf)이 있으면 mapping 이 그 옆에 있다."""
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "scan.gjf")))
        m = json.load(open(os.path.join(self.job_dir, "u56_R-A_mapping.json")))
        self.assertTrue(m["mapping"]["resolved"])
        self.assertEqual([["O_ether", "C_sp3"]], m["break_roles"])

    def test_scan_coordinate_comes_from_the_mapping_not_a_literal(self):
        m = json.load(open(os.path.join(self.job_dir, "u56_R-A_mapping.json")))
        i, j = m["mapping"]["break"][0]["selected"]
        section = open(os.path.join(self.job_dir,
                                    "u56_R-A_scan_section.txt")).read()
        self.assertIn("B %d %d S 12 0.1000" % (i + 1, j + 1), section)
        self.assertIn("B %d %d S 12 0.1000" % (i + 1, j + 1),
                      open(os.path.join(self.job_dir, "scan.gjf")).read())

    def test_acceptance_records_omega_as_data_with_no_verdict(self):
        """🔴 [§39.4(c) M2' / §39.56] Omega 는 **항상** 자리를 갖고, 계산되지 않았으면
        그 **이유가 문자열로** 남는다 — 침묵은 없다. 판정은 하지 않는다(C-3 / U-57:
        Omega_min 은 보정 대상이지 주장 대상이 아니다).
        ⚠ 이 실행은 MOCK_G16 로그라 실제 normal-mode 블록이 없다 — 그래서 omega 는
        None 이고 status 가 왜인지를 말한다. 실 로그에 대한 재현은
        `tests/test_omega_mode_character.py` 가 P1 의 진짜 freq 블록으로 고정한다."""
        a = json.load(open(os.path.join(self.job_dir, "ts_acceptance.json")))
        self.assertIn("exactly_one_imaginary_mode", a)
        self.assertIn("omega", a)
        self.assertIsNone(a["_omega_threshold"], "C-3: 문턱을 박지 않는다")
        self.assertTrue(a["_omega_status"], "계산 못 했으면 이유가 남아야 한다")
        self.assertNotIn("NOT IMPLEMENTED", a["_omega_status"],
                         "parser 는 이제 존재한다 — 옛 자리표시자가 남아 있으면 안 된다")

    def test_the_cap_regime_is_recorded_beside_the_attempt(self):
        """🔴 [39.59] A rate measured under one set of caps is not comparable with a rate
        measured under another. Nothing else in the record would show that if two rounds got
        averaged or trended, so the caps ride with the attempt.
        🔒 Parsed from the routes that ACTUALLY ran, not from config -- config is what we
        asked for, the emitted route is what the job used."""
        caps = json.load(open(os.path.join(self.job_dir, "active_caps.json")))
        self.assertTrue(caps["route_caps"], caps)
        # every TS/IRC-family route this run generated carries a cycle or point cap
        self.assertTrue(any("maxcycles" in v or "maxpoints" in v
                            for v in caps["route_caps"].values()), caps)
        # and the record does not pretend to know the caps it cannot see
        self.assertIn("not visible inside the payload",
                      caps["_not_observable_here"].lower())
        summary = json.load(open(os.path.join(self.job_dir, "u56_attempt.json")))
        self.assertEqual("active_caps.json", summary["active_caps"])
        self.assertTrue(summary["item_key"],
                        "the plan item key is the join back to the wall/budget caps")

    def test_attempt_summary_exists_and_leaves_the_verdict_to_review(self):
        s = json.load(open(os.path.join(self.job_dir, "u56_attempt.json")))
        self.assertEqual("R-A", s["reaction"])
        self.assertEqual("relaxed_scan", s["method"])
        self.assertEqual("level3", s["level"])
        self.assertIn("판정", s["note"])

    def test_stage_markers_carry_the_package_fingerprint(self):
        """R-12: 오염 마커 승계 방지 — coder9 방식(version.package_fingerprint)이
        새 payload 의 stage 마커에도 그대로 박힌다 (common.sh::sei_stage 경유)."""
        stages = os.path.join(self.job_dir, "stages")
        names = sorted(os.listdir(stages))
        self.assertTrue(names, "sei_stage 마커가 하나도 없다")
        for n in names:
            rec = json.load(open(os.path.join(stages, n)))
            fp = rec.get("pkg_fingerprint")
            self.assertTrue(fp and fp != "unknown",
                            "%s 에 pkg_fingerprint 가 없다/unknown — R-12 위반" % n)

    def test_collector_assembles_the_attempt(self):
        from sei_pilot import collect as collect_mod
        from sei_pilot.state import Store
        store = Store(self.d)
        key = os.path.basename(self.job_dir)
        store.mark_done(key, {"start_epoch": 0, "end_epoch": 60, "rc": 0})
        res = collect_mod.collect_u56(store, key)
        self.assertEqual("R-A", res["reaction"])
        self.assertIsNotNone(res["mapping"])
        self.assertIsNotNone(res["scan_points"])
        self.assertIsNotNone(res["ts_acceptance"])
        # [§39.42(a)/(b)] covariate 들이 회신에 실린다 — 측정했는데 안 읽는 값 금지.
        self.assertIsNotNone(res["deck_inputs"]["d_li_o_break_ang"])
        self.assertIsNotNone(res["deck_inputs"]["scan_start_d_ang"])
        self.assertTrue(any(h for h in res["chk_handoff"]))
        self.assertFalse(any("concurrent_execution" in w
                             for w in res["execution_audit"]["warnings"]))

    def test_refine_pass_is_triggered_and_recorded_on_this_degenerate_log(self):
        """mock 스캔 로그는 점 1개 → 최댓값이 범위 끝(§39.42(b) 트리거 ii) → refine
        pass 가 돌고 그 판정·산출물이 기록된다. (실 화학이 아니라 **조건부 배관**의
        발동 경로를 고정하는 테스트다 — 미발동 경로는 refine_decision 단위 테스트가
        지킨다.)"""
        sp = json.load(open(os.path.join(self.job_dir, "scan_points.json")))
        self.assertTrue(sp["refine_decision"]["decision"]["triggered"])
        self.assertIsNotNone(sp["refine"])
        self.assertIn(sp["guess_source_pass"], ("coarse", "refine"))
        section = open(os.path.join(self.job_dir,
                                    "u56_R-A_refine_section.txt")).read()
        self.assertIn("S 8 0.0250", section)
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "scan_refine.log")))

    def test_irc_chk_handoff_is_recorded_with_the_freq_stage_source(self):
        """[engineer7 §R39.15 4a + 정정] .chk 출처 = TS 잡의 **freq 단계**(수렴된 TS 의
        Hessian), guess 기하의 CalcFC 아님 — 그 문장이 기록 자체에 박혀 있어야 한다.
        기본 스위치는 calcfc: IRC route 에 rcfc 가 나가면 안 된다(미검증 경로)."""
        for d in ("forward", "reverse"):
            rec = json.load(open(os.path.join(self.job_dir,
                                              "chk_handoff_%s.json" % d)))
            self.assertIn("freq", rec["hessian_source_stage"])
            self.assertIn("NOT the CalcFC guess", rec["hessian_source_stage"])
            self.assertEqual("calcfc", rec["irc_hessian_source_config"])
            self.assertEqual("irc_%s" % d, rec["irc_route"])
            route = [l for l in open(os.path.join(self.job_dir,
                                                  "irc_%s.gjf" % d))
                     if l.startswith("#p ")][0]
            self.assertIn("calcfc", route)
            self.assertNotIn("rcfc", route)
            self.assertIn("Int(Grid=UltraFine)", route,
                          "§39.41(b): IRC 도 인증과 같은 grid — 다른 grid 는 다른 표면")


class TestU56RcfcRefusesWithoutItsHessian(unittest.TestCase):
    """🔴 [ADR-107 class / R39.15-4a] `irc=(rcfc,...)` READS the Hessian from %chk instead of
    recomputing it. If the handoff did not happen G16 does not fail loudly -- it completes on
    the WRONG curvature and reports endpoints. Silently wrong, not a crash, and the same shape
    as ADR-107's shared Lustre path.

    ⚠ COVERAGE, STATED RATHER THAN IMPLIED: this is a SOURCE-level check, not an execution
    one. The switch is read from `config/b0_reactions.json` only (`u56_2.irc_hessian_source`,
    default `calcfc`) and there is deliberately NO env override -- adding one would mean
    editing the PBS/SLURM templates, which are shape-locked against the site submit filter
    (`test_pbs_script_shape.py`), to unset it again. So the refusal branch cannot be exercised
    end to end until the lead raises the flag after a route smoke. What CAN be fixed now is
    that the branch exists and that it does not quietly fall back -- and those are the two
    ways this could go wrong silently.
    """

    def setUp(self):
        with open(os.path.join(context.PKG_ROOT, "payload", "U56.sh")) as fh:
            self.src = fh.read()

    def test_the_refusal_branch_exists_and_is_conditioned_on_the_copy(self):
        self.assertIn('[ "${HESS_SRC}" = "readfc" ] && [ "${CHK_COPIED}" != "true" ]',
                      self.src)
        self.assertIn("rcfc_requested_without_chk", self.src)

    def test_there_is_no_silent_calcfc_fallback(self):
        """🔒 Switching method mid-run would make the cost measurement -- the entire reason
        the switch exists -- unattributable. Refusing the direction is the only honest move."""
        branch = self.src[self.src.index("rcfc requested but the TS .chk was NOT copied"):]
        branch = branch[:branch.index("continue")]
        self.assertNotIn("IRC_SUFFIX=\"\"", branch)
        self.assertNotIn("HESS_SRC=", branch)

    def test_the_refusal_is_classified_as_plumbing_not_as_a_denominator(self):
        """Neither chemical nor budget: a failed Hessian handoff says nothing about the
        reaction and nothing about our caps. Pooling it would corrupt both denominators."""
        self.assertIn('"cause_class": "unknown"', self.src)

    def test_the_chk_names_the_adapter_writes_and_the_payload_copies_agree(self):
        """🔴 The switch is only as good as the two names matching. The adapter derives
        `%chk` from the input file's basename plus the per-task suffix; the payload copies the
        TS chk to `irc_<dir><suffix>.chk` and the IRC input is `irc_<dir>.gjf`. If either side
        is renamed the rcfc route reads a chk that is not there -- silently."""
        with open(os.path.join(context.PKG_ROOT, "payload", "qc_adapter.sh")) as fh:
            adapter = fh.read()
        self.assertIn('%%chk=%s%s.chk', adapter)
        self.assertIn('IRC_CHK="$D/irc_${dir}${SEI_TASK_FILE_SUFFIX:-}.chk"', self.src)
        self.assertIn('"$D/irc_${dir}.gjf"', self.src)


class TestU56PerTaskChkIsolation(_U56Run):
    """🔴 [ADR-107 클래스] array task 환경(PBS_ARRAY_INDEX)에서 %chk 가 태스크별로
    격리되고, freq 단계와 IRC 단계가 **정확히 같은 태스크의** 파일을 가리킨다.
    고정 공유 경로면 IRC 가 남의 TS 의 Hessian 을 읽고 정상 종료한다 — Lustre 는
    아무것도 중재하지 않는다."""

    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRE_JOB_FILES = {"gscan_verdict.json": U56_FIXTURE_GSCAN_PASS}
    EXTRA_ENV = {"PBS_ARRAY_INDEX": "4"}

    def test_ts_and_irc_chk_names_carry_the_same_task_suffix(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-800:])
        ts_route = open(os.path.join(self.job_dir, "ts_opt.gjf")).read()
        self.assertIn("%chk=ts_opt.t4.chk", ts_route)
        for d in ("forward", "reverse"):
            gjf = open(os.path.join(self.job_dir, "irc_%s.gjf" % d)).read()
            self.assertIn("%%chk=irc_%s.t4.chk" % d, gjf)
            rec = json.load(open(os.path.join(self.job_dir,
                                              "chk_handoff_%s.json" % d)))
            self.assertEqual("ts_opt.t4.chk", rec["source_chk"])
            self.assertEqual("irc_%s.t4.chk" % d, rec["target_chk"])
            self.assertEqual(".t4", rec["per_task_suffix"])


class TestU56Qst2StillNeedsBothEndpoints(_U56Run):
    """양끝단(QST2) attempt 는 완화되지 않는다 — product 인증 없으면 거부."""

    METHOD = "qst2"
    INJECT_ENDPOINTS = json.dumps({
        "reactant": {"optimised": True, "converged": True, "n_imag": 0,
                     "level": "level3"},
        "declared_planar": True, "_label": "[FIXTURE]"})
    PRODUCT_XYZ = "inputs/li_ec_radical_product.xyz"

    def test_refused(self):
        self.assertEqual(6, self.proc.returncode,
                         self.proc.stdout[-1500:] + self.proc.stderr[-500:])
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "ts_qst2.gjf")))


class TestU56Qst2RunsWithBothCertsAndNoFallback(_U56Run):
    """QST2 arm: 양끝단 인증이면 돌고, 🔴 **단끝단 폴백은 존재하지 않는다** — bake-off
    에서 method 를 갈아타면 비교가 오염된다(§39.39(d) read-out rule). mock 은 양성
    진동수만 내므로 인수시험은 불합격으로 **기록**되지만 ts_opt 폴백 파일은 없어야 한다."""

    METHOD = "qst2"
    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRODUCT_XYZ = "inputs/li_ec_radical_product.xyz"

    def test_qst2_ran_and_no_fallback_files_exist(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-800:])
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "ts_qst2.log")))
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "ts_opt.gjf")),
                         "QST2 arm 이 단끝단으로 폴백했다 — bake-off 오염")
        a = json.load(open(os.path.join(self.job_dir, "ts_acceptance.json")))
        self.assertIn(a["exactly_one_imaginary_mode"], (False, None))

    def test_mapping_still_emitted_for_omega_scoring(self):
        """QST2 는 스캔 좌표가 없어도 Ω 채점을 위해 mapping 은 똑같이 필요하다."""
        self.assertTrue(os.path.exists(
            os.path.join(self.job_dir, "u56_R-A_mapping.json")))
        self.assertFalse(os.path.exists(
            os.path.join(self.job_dir, "u56_R-A_scan_section.txt")))


class TestU56DeckRefusedWhenGeometryIsNotTheReaction(_U56Run):
    """[B-2 거부 방향] 게이트를 지나도 mapping 이 성립하지 않으면 덱 생성 자체가
    거부된다(exit 8) — 2원자 기하에 R-A(11원자)의 role 을 인식시키는 것은 다른 분자에
    대한 Ω 채점이다."""

    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    REACTANT_XYZ = None       # setUp 대신 아래에서 자체 기하를 만든다

    def setUp(self):
        d = tempfile.mkdtemp(prefix="sei_u56xyz_")
        self.addCleanup(shutil.rmtree, d, True)
        self._h2 = os.path.join(d, "h2.xyz")
        with open(self._h2, "w") as fh:
            fh.write("2\nnot R-A's species\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")
        type(self).REACTANT_XYZ = None
        os.environ["SEI_U56_REACTANT_XYZ"] = self._h2
        self.addCleanup(os.environ.pop, "SEI_U56_REACTANT_XYZ", None)
        _U56Run.setUp(self)

    def test_exit_8_with_a_refusal_record_and_no_deck(self):
        self.assertEqual(8, self.proc.returncode,
                         self.proc.stdout[-1500:] + self.proc.stderr[-500:])
        r = json.load(open(os.path.join(self.job_dir, "mapping_refusal.json")))
        self.assertTrue(r["refused"])
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "scan.gjf")))


# =============================================================================================
# 🔴 G-SCAN-4 (§39.45(a)) — 자금 집행 지점. 회피 비용 ~660 core-h(11원자) / ~6,400(21원자).
# =============================================================================================

def _xtb_available():
    from sei_pilot import envpaths
    return bool(envpaths.vendored("xtb", context.PKG_ROOT))


@unittest.skipUnless(_xtb_available(), "no vendored xtb on this machine")
class TestU56ProducesItsOwnGScanVerdict(_U56Run):
    """🔴 [G-SCAN-1, 39.45(a) / 39.47(a)] The single-ended arm now PRODUCES the gate's verdict
    itself, in-job, before any DFT is ordered: a GFN2 relaxed scan run BOTH ways on one grid.

    ⚠ This class replaces an earlier one that asserted the arm REFUSED for want of a verdict.
    That was the honest state of the tree when the consumer existed and the producer did not;
    it is no longer true, and a test asserting it would now be pinning a stale fact.

    🔒 In-job rather than a separate plan Item: a separate Item costs a full round trip (~3.5
    days) for a verdict that takes seconds, and the DFT spend the gate protects has not
    happened yet at that point.
    """

    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRE_JOB_FILES = {}                       # no injected verdict -- it must make its own

    def test_a_verdict_is_produced_before_any_dft_is_ordered(self):
        path = os.path.join(self.job_dir, "gscan_verdict.json")
        self.assertTrue(os.path.exists(path),
                        self.proc.stdout[-1200:] + self.proc.stderr[-400:])
        v = json.load(open(path))
        self.assertIn("fired", v)
        self.assertEqual(24, v["n_points_total"],
                         "12 coarse points in each direction, on ONE grid")

    def test_the_pass_runs_at_gfn2_and_inside_the_gfn2_budget(self):
        """39.47(a) as a measurement rather than an argument: 24 points is free on the engine
        where the guess is made, and would breach the DFT cap of 20 for ONE direction."""
        v = json.load(open(os.path.join(self.job_dir, "gscan_verdict.json")))
        self.assertEqual("gfn2", v["point_budget"]["engine"])
        self.assertEqual(512, v["point_budget"]["cap"])
        self.assertGreater(v["point_budget"]["used"], 20)

    def test_both_directions_use_the_same_grid_spanning_the_registered_1_2_angstrom(self):
        v = json.load(open(os.path.join(self.job_dir, "gscan_verdict.json")))
        plan = v["plan"]
        self.assertEqual(list(plan["forward"]), list(reversed(plan["reverse"])))
        self.assertAlmostEqual(1.2, plan["d_end_ang"] - plan["d_start_ang"], places=6,
                               msg="39.42(b) registered +1.2 A; n_points x step, not "
                                   "(n_points - 1) x step")

    def test_the_scan_is_anchored_on_the_PRE_RELAXED_distance(self):
        """🔴 [39.68(1)(2)] The certified reactant is relaxed at GFN2 under a constraint
        holding d_break, and the scan is anchored on the RESULT of that -- not on the raw
        certified distance. Anchoring on the raw one is what made frame 0 arrive still
        descending and false-fired the gate."""
        v = json.load(open(os.path.join(self.job_dir, "gscan_verdict.json")))
        self.assertTrue(v["prerelax_converged"],
                        "read from xtb's own words, not inferred from the exit code")
        self.assertIn("CONSTRAINED", v["_protocol"])

    def test_a_failed_xtb_run_yields_no_verdict_rather_than_a_firing(self):
        """🔴 A non-zero xtb exit means the scan did not finish. A partial trajectory is not a
        short one -- it is an unfinished one, and the gate has no business concluding from it.
        This shipped once: `forward_rc` was recorded and never read, so a failed forward scan
        produced a FIRED verdict off a partial log (observed: rc 128, "73 eV").
        ⟹ whichever way this machine's run lands, the contract holds: rc != 0 => no verdict,
        cause_class `protocol`, and no DFT ordered."""
        v = json.load(open(os.path.join(self.job_dir, "gscan_verdict.json")))
        failed = [c for c in (v["forward_rc"], v["reverse_rc"]) if c not in (0, None)]
        if failed:
            self.assertFalse(v["fired"])
            self.assertEqual("protocol", v["cause_class"])
            self.assertFalse(os.path.exists(os.path.join(self.job_dir, "scan.gjf")))
        else:
            self.assertIn("fired", v)
            self.assertTrue(v["frame0"]["ok"], v["frame0"]["reasons"])

    def test_the_verdict_gates_the_dft_chain(self):
        """Whichever way it lands, the DFT chain must follow it -- that is the whole point.
        Three outcomes, three behaviours: passed => DFT ordered; fired => not ordered;
        no verdict (`protocol`) => not ordered either, because an unrenderable verdict is not
        a permission."""
        v = json.load(open(os.path.join(self.job_dir, "gscan_verdict.json")))
        ordered = os.path.exists(os.path.join(self.job_dir, "scan.gjf"))
        may_proceed = (not v["fired"]) and v.get("cause_class") != "protocol"
        self.assertEqual(may_proceed, ordered)

    def test_the_pre_stage_cost_keeps_work_and_charged_apart(self):
        """🔴 [ADR-110] xtb runs single-threaded inside a G16-sized job. Recording one blended
        number would hide the packing efficiency, which is the thing worth knowing."""
        c = json.load(open(os.path.join(self.job_dir, "gscan_cost.json")))
        self.assertEqual(1, c["xtb_threads"])
        self.assertGreaterEqual(c["job_total_cores"], 1)
        self.assertIn("Do not average", c["_note"])


class TestU56WithholdsFundingWhenTheGateFires(_U56Run):
    """🔴 G-SCAN-4: 발동하면 `ts_opt+freq` 도 IRC 도 **발주하지 않는다.** 결과는 버려지지
    않고 `indeterminate, missing coordinate` 로 기록된다 — §39.39(f)가 이미 받는 **원인이
    알려진** 결과이므로 U-56b 의 분모에 들어가고 U-56a 를 오염시키지 않는다."""

    INJECT_ENDPOINTS = U56_FIXTURE_CERTS_LEVEL3
    PRE_JOB_FILES = {"gscan_verdict.json": U56_FIXTURE_GSCAN_FIRED}

    def test_run_completes_rather_than_erroring(self):
        """발동은 배관 실패가 아니라 **결과**다 — 0 으로 끝나고 기록을 남긴다."""
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-1500:] + self.proc.stderr[-500:])

    def test_no_dft_scan_no_ts_opt_no_irc(self):
        for f in ("scan.gjf", "scan.log", "ts_opt.gjf", "ts_opt.log",
                  "irc_forward.log", "irc_reverse.log"):
            self.assertFalse(os.path.exists(os.path.join(self.job_dir, f)), f)

    def test_status_is_the_known_cause_outcome(self):
        with open(os.path.join(self.job_dir, "u56_attempt.json")) as fh:
            rec = json.load(fh)
        self.assertEqual("indeterminate_missing_coordinate", rec["status"])

    def test_a_fired_gate_does_not_fall_through_to_qst2(self):
        """🔴 폴백 금지(§39.39(d) read-out 오염 방지). gate 가 발동했다고 method 를
        갈아타면 bake-off 의 비교가 통째로 오염된다."""
        for f in ("ts_qst2.gjf", "ts_qst2.log"):
            self.assertFalse(os.path.exists(os.path.join(self.job_dir, f)), f)

    def test_the_verdict_reaches_the_reply_for_gscan5_counting(self):
        """G-SCAN-5: 발동은 **세어서 보고**한다 — 한 번도 안 터지면 unreached,
        매번 터지면 틀린 것은 화학이 아니라 scan 설계다. 둘 다 판정문 없이는 알 수 없다."""
        from sei_pilot import collect as collect_mod
        from sei_pilot.state import Store
        store = Store(self.d)
        key = os.path.basename(self.job_dir)
        store.mark_done(key, {"start_epoch": 0, "end_epoch": 60, "rc": 0})
        rec = collect_mod.collect_u56(store, key)
        self.assertTrue((rec.get("gscan_verdict") or {}).get("fired"), rec)


if __name__ == "__main__":
    unittest.main()
