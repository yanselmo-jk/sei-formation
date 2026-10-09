"""🔴 Gaussian16 어댑터·파서 회귀 테스트.

배경: 사용자 클러스터에 **orca/qchem/psi4 가 하나도 없고 gaussian16 이 있다**(lead 확인).
ORCA 전제였다면 P1·P1b·P5 **세 파일럿이 전부 SKIP** 되어 CPU 패키지가 프로브만 남는다.

G16은 출력 형식이 ORCA와 완전히 달라 **파서를 재사용할 수 없다.** 우리는 Gaussian을
갖고 있지 않으므로, **실제 G16 로그 형식을 문자열로 박아 회귀 고정**한다.
(형식 자체가 틀렸을 가능성은 남으며, 그것은 사용자 클러스터의 route smoke 가 판정한다.)
"""

import json
import os
import re
import subprocess
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import config as config_mod
from sei_pilot import envpaths, plan
from sei_pilot.criteria import g16
from sei_pilot.shellrun import FakeShell

PKG = context.PKG_ROOT

# 실제 G16 로그의 핵심 조각들 (형식 기준)
LOG_OK = """ Entering Gaussian System, Link 0=g16
 %nprocshared=8
 %mem=16GB
 -------------------------------------
 #p wB97XD/def2TZVP scrf=(smd,solvent=acetonitrile) opt freq
 -------------------------------------
 Charge =  0 Multiplicity = 2
                          Input orientation:
 ---------------------------------------------------------------------
 Center     Atomic      Atomic             Coordinates (Angstroms)
 Number     Number       Type             X           Y           Z
 ---------------------------------------------------------------------
      1          6           0        0.000000    1.190000    0.000000
      2          8           0       -1.132000    0.368000    0.000000
      3          3           0        0.000000    4.240000    0.000000
 ---------------------------------------------------------------------
 SCF Done:  E(UwB97XD) =  -349.907522401     A.U. after   12 cycles
 Step number   1 out of a maximum of 100
 SCF Done:  E(UwB97XD) =  -349.917522401     A.U. after    9 cycles
 Step number   2 out of a maximum of 100
                         Standard orientation:
 ---------------------------------------------------------------------
 Center     Atomic      Atomic             Coordinates (Angstroms)
 Number     Number       Type             X           Y           Z
 ---------------------------------------------------------------------
      1          6           0        0.010000    1.200000    0.000000
      2          8           0       -1.140000    0.360000    0.000000
      3          3           0        0.000000    4.300000    0.000000
 ---------------------------------------------------------------------
    Stationary point found.
 Optimization completed.
 Frequencies --   -452.3100   112.4400   331.0200
 Frequencies --    512.7700   688.1000   901.5000
 Zero-point correction=                           0.075000
 Job cpu time:       0 days  1 hours 12 minutes 30.0 seconds.
 Elapsed time:       0 days  0 hours  9 minutes 45.0 seconds.
 Normal termination of Gaussian 16 at Sun Aug 17 18:00:00 2026.
"""

LOG_ROUTE_ERROR = """ Entering Gaussian System, Link 0=g16
 #p wB97X-V/def2-TZVPPD sp
 Unrecognized functional name wB97X-V.
 Error termination via Lnk1e in /opt/g16/l301.exe at Sun Aug 17 18:00:00 2026.
"""

LOG_MEMORY_ERROR = """ Entering Gaussian System, Link 0=g16
 #p wB97XD/def2TZVP opt
 galloc:  could not allocate memory
 Error termination via Lnk1e in /opt/g16/l502.exe.
"""


class TestG16Parsers(unittest.TestCase):
    def test_normal_termination(self):
        t = g16.parse_termination(LOG_OK)
        self.assertTrue(t["normal"])
        self.assertIsNone(t["reason"])

    def test_route_error_is_classified(self):
        """🔴 범함수 이름이 틀리면 'route_rejected' 로 분류돼야 한다."""
        t = g16.parse_termination(LOG_ROUTE_ERROR)
        self.assertFalse(t["normal"])
        self.assertEqual(t["reason"], "route_rejected")
        self.assertIn("Error termination", t["message"])

    def test_memory_error_is_classified_separately(self):
        """🔴 G16은 %mem 부족 시 조용히 느려지는 게 아니라 galloc 으로 죽는다."""
        t = g16.parse_termination(LOG_MEMORY_ERROR)
        self.assertEqual(t["reason"], "memory")

    def test_empty_log_is_not_success(self):
        self.assertFalse(g16.parse_termination("")["normal"])

    def test_frequencies_three_per_line(self):
        """G16은 한 줄에 최대 3개씩 찍는다(ORCA와 형식이 다르다)."""
        f = g16.parse_frequencies(LOG_OK)
        self.assertEqual(len(f), 6)
        self.assertAlmostEqual(f[0], -452.31)
        self.assertAlmostEqual(f[-1], 901.50)

    def test_imaginary_frequency_is_negative(self):
        f = g16.parse_frequencies(LOG_OK)
        self.assertEqual(sum(1 for x in f if x < 0), 1)

    def test_scf_energies_and_cycles(self):
        scf = g16.parse_scf(LOG_OK)
        self.assertEqual(scf["cycles"], [12, 9])
        self.assertEqual(scf["max_cycles"], 12)
        self.assertAlmostEqual(scf["final_energy_hartree"], -349.917522401)
        self.assertTrue(scf["converged"])

    def test_geometry_atomic_numbers_map_to_symbols(self):
        geoms = g16.parse_geometries(LOG_OK)
        self.assertEqual(len(geoms), 2)
        self.assertEqual([a[0] for a in geoms[0]], ["C", "O", "Li"])

    def test_last_geometry_is_the_final_one(self):
        last = g16.last_geometry(LOG_OK)
        self.assertAlmostEqual(last[0][1], 0.010000)      # Standard orientation
        self.assertAlmostEqual(last[2][3], 0.0)

    def test_opt_status(self):
        opt = g16.parse_opt_status(LOG_OK)
        self.assertTrue(opt["converged"])
        self.assertTrue(opt["stationary_point"])
        self.assertEqual(opt["cycles"], 2)

    def test_timings_are_parsed(self):
        t = g16.parse_timings(LOG_OK)
        self.assertAlmostEqual(t["cpu_seconds"], 3600 + 12 * 60 + 30)
        self.assertAlmostEqual(t["elapsed_seconds"], 9 * 60 + 45)

    def test_charge_multiplicity(self):
        cm = g16.parse_charge_mult(LOG_OK)
        self.assertEqual((cm["charge"], cm["multiplicity"]), (0, 2))

    def test_route_echo(self):
        self.assertIn("wB97XD/def2TZVP", g16.parse_route(LOG_OK))

    def test_summarize_shape(self):
        s = g16.summarize(LOG_OK)
        # B-1: the bare `route` field is gone (RT-1 stored it truncated at 70
        # columns with no marker, and absence was read off it). It is replaced
        # by `route_echoed` (full reassembled text) + `route_echoed_is_complete`
        # (never silently absent-by-omission) + the full `route_echo` record.
        for k in ("code", "normal_termination", "route_echoed",
                  "route_echoed_is_complete", "route_echo", "scf", "opt",
                  "timings"):
            self.assertIn(k, s)
        self.assertNotIn("route", s,
                         "B-1: bare `route` must not reappear -- it is the field "
                         "that was read as authoritative off a 70-column cut.")
        self.assertEqual(s["code"], "gaussian16")


class TestG16Detection(unittest.TestCase):
    def test_g16_found_via_env_var_when_not_on_path(self):
        """🔴 Gaussian은 모듈/`g16.profile` 로 잡히는 경우가 많아 PATH에 없을 수 있다."""
        sh = FakeShell(which_map={}, paths=["/opt/gaussian/g16/g16"])
        name, path = envpaths.resolve_qc(sh, env={"g16root": "/opt/gaussian"})
        self.assertEqual(name, "g16")
        self.assertEqual(path, "/opt/gaussian/g16/g16")

    def test_path_takes_precedence(self):
        sh = FakeShell(which_map={"g16": "/usr/bin/g16"})
        self.assertEqual(envpaths.resolve_qc(sh, env={})[0], "g16")

    def test_g09_is_a_fallback(self):
        sh = FakeShell(which_map={"g09": "/usr/bin/g09"})
        self.assertEqual(envpaths.resolve_qc(sh, env={})[0], "g09")

    def test_absent_returns_none(self):
        self.assertEqual(envpaths.resolve_qc(FakeShell(), env={}), (None, None))

    def test_qc_codes_put_gaussian_first(self):
        """🔴 사용자 클러스터에는 g16 만 있다. 탐지 순서가 우선순위다."""
        self.assertEqual(plan.QC_CODES[0], "g16")
        self.assertIn("g09", plan.QC_CODES)

    def test_env_var_list_is_single_source(self):
        self.assertIn("g16root", envpaths.qc_env_vars())
        with open(os.path.join(PKG, "payload", "qc_adapter.sh")) as fh:
            text = fh.read()
        for line in text.splitlines():
            if "g16root" in line:
                self.assertTrue(line.strip().startswith("#"),
                                "환경변수 목록이 셸에 중복됐다: %s" % line)


class TestQcLevelsConfig(unittest.TestCase):
    def setUp(self):
        self.cfg = config_mod.load("qc_levels.json", {})

    def test_config_loads(self):
        self.assertFalse(self.cfg.get("_fallback"))
        self.assertIn("gaussian16", self.cfg)

    def test_all_job_types_needed_by_payloads_exist(self):
        jt = self.cfg["gaussian16"]["job_types"]
        for needed in ("sp", "force", "freq", "opt5", "opt_freq",
                       "ts_opt", "irc_forward", "irc_reverse"):
            self.assertIn(needed, jt, needed)

    def test_ts_route_has_calcfc_and_noeigentest(self):
        """G16 TS 최적화는 초기 Hessian 없이는 잘 안 붙는다."""
        route = self.cfg["gaussian16"]["job_types"]["ts_opt"]
        self.assertIn("ts", route)
        self.assertIn("calcfc", route)
        self.assertIn("noeigentest", route)
        self.assertIn("freq", route)

    def test_fresh_irc_routes_default_to_recorrect_never_with_explicit_maxpoints(self):
        """🟢 [§39.136(2), S3 wave-1] recorrect=never is now the PRODUCTION default for every
        fresh (non-restart) IRC job, project-wide -- proven fix for the corrector-oscillation
        crash that killed both R-A arms under the original (default-recorrection) setting,
        confirmed at DEFAULT step size (stage4, §39.125). maxpoints stays explicit, unchanged."""
        jt = self.cfg["gaussian16"]["job_types"]
        for job_type in ("irc_forward", "irc_reverse"):
            with self.subTest(job_type=job_type):
                route = jt[job_type]
                self.assertIn("recorrect=never", route)
                self.assertIn("maxpoints=", route)
                self.assertIn("calcfc", route)

    def test_rcfc_irc_routes_ALSO_default_to_recorrect_never(self):
        """🔴 [critic17, wave-1 review #2] The corrector-oscillation failure mode is a property
        of the corrector, not of where the Hessian came from -- an earlier scoping choice that
        left `irc_forward_rcfc`/`irc_reverse_rcfc` out of §39.136(2)'s fix was wrong and has
        been reverted. The rcfc switch is off today (`irc_hessian_source=calcfc`), so this test
        is the only thing standing between whoever flips it and the default corrector that
        killed both R-A arms."""
        jt = self.cfg["gaussian16"]["job_types"]
        for job_type in ("irc_forward_rcfc", "irc_reverse_rcfc"):
            with self.subTest(job_type=job_type):
                route = jt[job_type]
                self.assertIn("recorrect=never", route)
                self.assertIn("maxpoints=", route)
                self.assertIn("rcfc", route)

    def test_every_route_that_relies_on_the_c9_perturbation_carries_nosymm(self):
        """🔴 B-2 (HANDOFF_CODER6 §B-2 / docs/05_STATE.md §0-k): G16 actively re-detects and
        re-imposes the molecular point group, so C-9's out-of-plane perturbation alone is
        insufficient without `nosymm` in the route. `_nosymm_required_job_types` is the single
        source (`guards.nosymm_required_job_types` reads the same key) -- this test guards the
        template text itself, so an edit to the JSON that drops the keyword is caught here even
        if nothing calls `guards.require_nosymm_if_needed` on that particular route yet."""
        gauss = self.cfg["gaussian16"]
        required = gauss["_nosymm_required_job_types"]
        self.assertEqual(
            sorted(required),
            sorted(["ts_opt", "ts_qst2", "ts_opt_from_guess", "irc_forward", "irc_reverse",
                    "endpoint_opt_rough", "endpoint_opt_freq",
                    # [U56-2 B-1] relaxed scan starts FROM the certified endpoint and
                    # drives the break coordinate -- §39.39(b) condition 2 (nosymm on
                    # every route from the perturbation onward) applies in full.
                    "relaxed_scan",
                    # [engineer7 §R39.15 4a] the rcfc (read-Hessian-from-chk) IRC
                    # variants continue FROM a TS -- same rule as irc_forward/reverse.
                    "irc_forward_rcfc", "irc_reverse_rcfc",
                    # [§39.89, proposer8 2026-08-21] all 22 P5 decks lacked nosymm; one row
                    # (li_ec_radical_s0_L2) converged exactly planar -- P1's C-9 pathology
                    # in P5. Future decks only; stored geometries are not re-optimised.
                    "opt", "opt_freq", "freq", "opt5"]))
        for job_type in required:
            with self.subTest(job_type=job_type):
                self.assertIn("nosymm", gauss["job_types"][job_type])

    def test_nosymm_sits_right_after_the_route_marker_not_buried_mid_route(self):
        """A `nosymm` placed deep inside a long route is exactly what a 70-column truncation
        (B-1) could cut before reaching -- keep it where a short prefix still carries it."""
        route = self.cfg["gaussian16"]["job_types"]["ts_qst2"]
        self.assertTrue(route.startswith("#p nosymm "), route)

    def test_no_level_is_an_unjustified_placeholder(self):
        """🔴 이 테스트의 원래 목적은 "근거 없는 레벨이 조용히 쓰이는 것"을 막는 것이다.

        예전에는 level2 가 PLACEHOLDER 였고 그 사실을 assert 했다. lead 가 레벨을
        확정(G-1/G-2)했으므로 이제는 **어떤 레벨도 미해결로 남아 있지 않을 것**을
        assert 한다. 목적은 그대로고 지켜야 할 상태만 바뀌었다.
        """
        for key in ("level1", "level2"):
            lvl = self.cfg["gaussian16"][key]
            status = lvl.get("_status", "")
            self.assertNotIn("PLACEHOLDER", status, "%s 가 아직 자리표시자다" % key)
            self.assertNotIn("UNRESOLVED", status)
            self.assertNotIn("_forbidden", lvl,
                             "%s 에 사용 금지 표시가 남아 있다" % key)
            self.assertTrue(status.startswith("✅"),
                            "%s 의 확정 여부가 명시돼 있지 않다: %r" % (key, status))

    def test_both_levels_record_who_confirmed_them(self):
        """출처 없는 레벨은 폐기 대상이다."""
        for key in ("level1", "level2"):
            self.assertIn("lead", self.cfg["gaussian16"][key]["_status"])

    def test_levels_are_labelled_g1_and_g2(self):
        self.assertEqual("G-1", self.cfg["gaussian16"]["level2"]["label"])
        self.assertEqual("G-2", self.cfg["gaussian16"]["level1"]["label"])

    def test_slot_mapping_interpretation_is_recorded(self):
        """🔴 lead 는 G-1/G-2 로 말했고 우리 구조는 level1/level2 다. 그 매핑은
        내가 정한 해석이므로 설정에 남아 있어야 한다(조용히 정하지 않는다)."""
        self.assertIn("매핑은 내가 정했다", self.cfg["_interpretation"])

    def test_top_level_status_records_resolution(self):
        self.assertIn("RESOLVED", self.cfg["_status"])
        self.assertIn("gen", self.cfg["_status"])

    def test_gen_basis_files_are_named_in_config(self):
        for key, expect in (("level1", "def2-TZVPD"), ("level2", "def2-TZVPPD")):
            lvl = self.cfg["gaussian16"][key]
            self.assertEqual("gen", lvl["basis"])
            self.assertEqual(expect, lvl["basis_real_name"])
            self.assertIn("inputs/basis/", lvl["basis_file"])

    def test_memory_policy_exists(self):
        pol = self.cfg["resource_policy"]
        self.assertGreater(pol["mem_fraction_of_node"], 0)
        self.assertLess(pol["mem_fraction_of_node"], 1)


@unittest.skipUnless(os.path.exists("/bin/bash"), "bash 없음")
class TestGjfGeneration(unittest.TestCase):
    """입력 생성기를 **실제로 실행**해 .gjf 형식을 검증한다(우리 박스에서 가능)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_gjf_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.xyz = os.path.join(self.d, "mol.xyz")
        with open(self.xyz, "w") as fh:
            fh.write("2\ntest\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")

    def _gen(self, level="1", job="opt_freq", charge="0", mult="1", ram="128"):
        script = ('source "%s/payload/qc_adapter.sh"; '
                  'sei_qc_input "%s/out.gjf" %s %s %s %s "%s"'
                  % (PKG, self.d, level, job, charge, mult, self.xyz))
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_JOB_DIR=self.d,
                   SEI_TOTAL_CORES="8", SEI_NODE_RAM_GB=ram,
                   # ADR-105: 용매 결정 없이는 덱이 나오지 않는다. 이 클래스는 덱
                   # *구조* 를 검증하므로 [FIXTURE] 정책을 주입해 방출 경로를 연다.
                   SEI_SOLVENT_POLICY_JSON=context.TEST_SOLVENT_POLICY_JSON)
        res = subprocess.run(["bash", "-c", script], env=env,
                             capture_output=True, universal_newlines=True)
        with open(os.path.join(self.d, "out.gjf")) as fh:
            return fh.read(), res

    def test_gjf_structure_is_gaussian_not_orca(self):
        text, _res = self._gen()
        lines = text.splitlines()
        self.assertTrue(lines[0].startswith("%nprocshared="))
        self.assertTrue(any(l.startswith("%mem=") for l in lines))
        self.assertTrue(any(l.startswith("#p ") for l in lines))
        self.assertNotIn("* xyzfile", text)          # ORCA 문법이 아니다
        self.assertNotIn("%pal", text)

    def test_blank_line_title_blank_charge_mult_layout(self):
        """G16 입력은 빈 줄 → title → 빈 줄 → 'charge mult' 순서가 **필수**다."""
        text, _r = self._gen(charge="-1", mult="2")
        lines = text.splitlines()
        i = next(i for i, l in enumerate(lines) if l.startswith("#p "))
        self.assertEqual(lines[i + 1].strip(), "")
        self.assertNotEqual(lines[i + 2].strip(), "")     # title
        self.assertEqual(lines[i + 3].strip(), "")
        self.assertEqual(lines[i + 4].split(), ["-1", "2"])

    def test_coordinates_follow_charge_line(self):
        """좌표는 charge/mult 줄 **바로 다음**에 온다 (그 뒤에 gen 기저 블록이 붙는다)."""
        text, _r = self._gen(charge="-1", mult="2")
        lines = text.splitlines()
        i = next(i for i, l in enumerate(lines) if l.split() == ["-1", "2"])
        self.assertRegex(lines[i + 1], r"^[A-Z][a-z]?\s+-?\d")

    def test_gen_basis_block_follows_the_coordinates(self):
        """🔴 def2-TZVPPD 는 G16 내장 키워드가 아니다 → route 는 `gen`, 기저는 좌표 뒤.

        순서가 틀리면 G16은 좌표를 다 읽고 SCF 직전에 죽는다 — 왕복 1회가 날아간다.
        """
        text, _r = self._gen()
        lines = text.splitlines()
        route = next(l for l in lines if l.startswith("#p "))
        self.assertIn("/gen", route, "route 에 gen 이 없다")
        i_cm = next(i for i, l in enumerate(lines) if l.split() == ["0", "1"])
        # charge/mult 다음 빈 줄이 좌표의 끝이다.
        i_blank = next(i for i in range(i_cm + 1, len(lines))
                       if not lines[i].strip())
        self.assertGreater(i_blank - i_cm, 1, "좌표가 하나도 없다")
        self.assertRegex(lines[i_blank + 1], r"^[A-Z][a-z]?\s+0\s*$",
                         "좌표 뒤 빈 줄 다음에 기저 블록('원소 0')이 와야 한다")
        self.assertIn("****", text)

    def test_only_elements_present_in_the_molecule_are_emitted(self):
        """분자에 없는 원소의 기저까지 넣었을 때 G16 동작을 우리는 확인하지 못했다."""
        text, _r = self._gen()
        block = text.split("\n\n")[-2]
        els = set(re.findall(r"^([A-Z][a-z]?)\s+0\s*$", block, re.M))
        self.assertTrue(els)
        self.assertNotIn("P", els)
        self.assertNotIn("F", els)

    def test_input_ends_with_a_blank_line(self):
        text, _r = self._gen()
        self.assertTrue(text.endswith("\n\n"))            # 마지막 빈 줄

    def test_nproc_comes_from_env(self):
        text, _r = self._gen()
        self.assertIn("%nprocshared=8", text)

    def test_mem_is_derived_from_measured_node_ram(self):
        """🔴 G16은 %mem 부족 시 죽는다. 프로브의 실측 RAM에서 유도한다."""
        text, _r = self._gen(ram="128")
        self.assertIn("%mem=89GB", text)                  # 128 * 0.7
        text2, _r2 = self._gen(ram="0")
        self.assertIn("%mem=4GB", text2)                  # 미측정 시 보수적

    def test_route_comes_from_config(self):
        text, _r = self._gen(job="ts_opt")
        self.assertIn("opt=(ts,calcfc,noeigentest", text)
        self.assertIn("freq", text)

    def test_unknown_job_type_fails_loudly(self):
        script = ('source "%s/payload/qc_adapter.sh"; '
                  'sei_qc_input "%s/x.gjf" 1 nonsense 0 1 "%s"'
                  % (PKG, self.d, self.xyz))
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_JOB_DIR=self.d)
        res = subprocess.run(["bash", "-c", script], env=env,
                             capture_output=True, universal_newlines=True)
        self.assertNotEqual(res.returncode, 0)
        self.assertIn("알 수 없는 job_type", res.stderr)

    def test_meta_json_records_route_and_level_status(self):
        _text, res = self._gen()
        meta = json.loads(res.stdout)
        self.assertIn("route", meta)
        self.assertIn("mem_gb", meta)
        self.assertIn("level_status", meta)


if __name__ == "__main__":
    unittest.main()


class TestFallbackHints(unittest.TestCase):
    """도구가 없어 생략될 때 **무엇을 보내면 되는지**가 회신에 남아야 한다.

    "사용 가능한 실행 수단 없음"만 적으면 lead가 그것을 알아내는 데 왕복 1회를 더 쓴다.
    """

    def setUp(self):
        from sei_pilot import budget
        env = {"scheduler": "none", "cores_per_node": 8, "software": {},
               "gpus": {}, "modules": []}
        self.items = dict((e["key"], e) for e in
                          plan.build_plan(env, budget.guard_for_profile("cpu"),
                                          profile="cpu")[0])

    # P2f 힌트 테스트는 P2f 제거와 함께 삭제했다(HANDOFF §17).

    def test_tool_absence_skips_carry_a_reason(self):
        """🔒 ADR-049 로 P3 가 빠졌다.

        🔴 정직하게 적는다: 처음엔 *"생략 가능한 모든 항목은 `fallback_hint` 를 가진다"* 로
        일반화해서 썼는데 **그건 한 번도 참인 적이 없었다.** `fallback_hint` 를 가진 항목은
        P3 뿐이었고(동봉 xtb 안내), P3 가 빠진 지금은 0 개다.
        내가 없는 규칙을 만들어낸 것이므로 **실제로 성립하는 불변식**으로 되돌린다:
        도구 부재로 생략된 항목은 **빈 사유로 사라지지 않는다.**
        (사유가 비면 사용자가 원인을 알아내는 데 왕복 1회(3.5일)가 더 든다.)
        """
        skipped_for_tools = [(k, it) for k, it in self.items.items()
                             if it.get("status") == "skipped"
                             and "실행 수단" in (it.get("skip_reason") or "")]
        self.assertTrue(skipped_for_tools, "이 환경에서는 도구 부재 생략이 있어야 한다")
        for key, it in skipped_for_tools:
            self.assertTrue(it["skip_reason"].strip(),
                            "%s 가 사유 없이 생략됐다" % key)

    def test_hints_reach_unresolved_for_lead(self):
        from sei_pilot import cli as cli_mod
        from sei_pilot import budget
        env = {"scheduler": "none", "cores_per_node": 8, "software": {},
               "gpus": {}, "modules": [], "_login": {}}
        g = budget.guard_for_profile("cpu")
        planned, _s = plan.build_plan(env, g, profile="cpu")
        out = cli_mod.collect_unresolved(env, planned, g, None, [])
        # 🔒 ADR-049 로 P3 가 빠졌다. 지키는 성질: **생략이 lead 에게 도달한다.**
        self.assertTrue(out, "생략된 항목이 있는데 unresolved_for_lead 가 비었다")
        self.assertTrue(any(u.get("item") for u in out))
