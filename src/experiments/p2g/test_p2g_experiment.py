"""P2g — xtb GFN-FF 주기계 검증 (V1 PBC 불변성 + V2 Li–O RDF).

🔴 V1 은 우리 박스에서 **실제로 돌려 답이 나왔다**(동봉 xtb 6.7.1):
   **불변이다** — 최대 편차 1.6e-7 Eh/atom.

⚠ 여기에 큰 함정이 있었다. 처음에는 **591 eV 편차**가 나와 Issue #1118 을 재현한 줄
알았다. 원인은 xtb 가 아니라 우리였다: xtb 는 GFN-FF 토폴로지를 `gfnff_topo` 에
캐시하고 다음 실행에서 재사용하는데, 모든 이동을 **같은 디렉터리**에서 연속 실행해
2회차부터 1회차의 토폴로지가 이동된 좌표에 적용됐다. 독립 디렉터리로 격리하니
편차가 4.2e-5 Eh 로 떨어졌다.
⇒ 그래서 `test_each_shift_runs_in_its_own_directory` 가 그 격리를 고정한다.
   **이 테스트를 지우면 가짜 BLOCKER 를 회신하게 된다.**

RDF 는 **해석해로 검증한다** — 균일 분포에서 g(r) → 1 이어야 한다. 규격화가 틀리면
봉우리 위치는 맞아도 배위수가 조용히 틀리고, 배위수는 proposer 판정의 입력이다.
"""

import json
import math
import os
import random
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import config

sys.path.insert(0, os.path.join(context.PKG_ROOT, "tools"))
import p2g_v1 as v1mod       # noqa: E402
import p2g_v2 as v2mod       # noqa: E402


class TestConfigIsTheSingleSource(unittest.TestCase):
    def test_config_exists_and_has_both_tests(self):
        cfg = config.load("p2g.json", {})
        self.assertIn("v1_translation_invariance", cfg)
        self.assertIn("v2_li_ec_rdf", cfg)

    def test_no_numbers_hardcoded_in_the_payload(self):
        with open(os.path.join(context.PKG_ROOT, "payload", "P2g.sh")) as fh:
            code = [l for l in fh if not l.lstrip().startswith("#")]
        for bad in ("50.0", "313", "0.50", "1e-6"):
            self.assertNotIn(bad, "".join(code),
                             "payload 에 수치 %s 가 박혔다 — config/p2g.json 이 출처다"
                             % bad)

    def test_cache_pitfall_is_documented(self):
        """🔴 우리가 실제로 빠졌던 함정 — 기록이 없으면 다음 사람이 다시 빠진다."""
        v1 = config.load("p2g.json", {})["v1_translation_invariance"]
        self.assertIn("gfnff_topo", v1["_cache_pitfall"])
        self.assertIn("591", v1["_cache_pitfall"])

    def test_tolerance_is_per_atom_not_total(self):
        """총량 기준은 큰 상자를 자동으로 실패시킨다."""
        v1 = config.load("p2g.json", {})["v1_translation_invariance"]
        self.assertIn("tolerance_hartree_per_atom", v1)
        self.assertNotIn("tolerance_hartree", v1)

    def test_issue_reference_is_recorded(self):
        """🔴 왜 이 시험을 하는지가 사라지면 다음 사람이 지운다."""
        v1 = config.load("p2g.json", {})["v1_translation_invariance"]
        self.assertIn("1118", v1["_doc"])
        self.assertIn("6.7.1", v1["_doc"])

    def test_composition_decision_is_flagged_for_lead(self):
        """전하 중성 처리는 지시에 없던 것이라 내가 정했다 — 그 사실이 남아야 한다."""
        comp = config.load("p2g.json", {})["v2_li_ec_rdf"]["composition"]
        self.assertIn("coder 결정", comp["_decision"])
        self.assertEqual(0, comp["n_li"] - comp["n_pf6"],
                         "Li+ 와 PF6- 수가 달라 셀이 중성이 아니다")
        self.assertEqual(4 * comp["n_li"], comp["n_ec"], "EC:Li = 4:1 이 아니다")

    def test_estimate_is_labelled_as_measured_on_this_box(self):
        v2 = config.load("p2g.json", {})["v2_li_ec_rdf"]
        self.assertIn("MEASURED", v2["_estimate_basis"])


class TestBudgetFitsTheGuard(unittest.TestCase):
    def test_p2g_is_within_the_guard(self):
        from sei_pilot import budget, plan
        items = plan.default_items("cpu")
        total = sum(i.core_hours_budget for i in items)
        guard = budget.guard_for_profile("cpu")
        self.assertLessEqual(total, guard.max_core_hours,
                             "P2g 추가로 가드를 넘었다 — lead 에게 보고해야 한다")

    def test_p2g_budget_covers_the_measured_estimate(self):
        """🔴 실측(7.4 core-h)보다 작으면 wall 에 잘려 궤적이 안 나온다."""
        from sei_pilot import plan
        item = [i for i in plan.default_items("cpu") if i.key == "P2g"][0]
        self.assertGreaterEqual(item.core_hours_budget, 7.4)

    def test_p2g_uses_the_xtb_account(self):
        from sei_pilot import plan
        item = [i for i in plan.default_items("cpu") if i.key == "P2g"][0]
        self.assertEqual("xtb", item.account_key)


COORD = """$coord
%s$periodic 3
$lattice bohr
%16.8f%16.8f%16.8f
%16.8f%16.8f%16.8f
%16.8f%16.8f%16.8f
$end
"""


def _coord_text(atoms, lat):
    body = "".join("%20.12f%20.12f%20.12f  %s\n" % (a[1], a[2], a[3], a[0])
                   for a in atoms)
    return COORD % (body, lat, 0, 0, 0, lat, 0, 0, 0, lat)


class TestTranslationHelper(unittest.TestCase):
    """평행이동 + 랩이 좌표를 정확히 다루는가 (우리 쪽 버그를 배제하는 부분)."""

    def setUp(self):
        self.lat = 10.0
        self.atoms = [("c", 1.0, 2.0, 3.0), ("o", 9.0, 9.0, 9.0)]
        self.lines = _coord_text(self.atoms, self.lat).splitlines()

    def _parse(self, text):
        return [(p[3], float(p[0]), float(p[1]), float(p[2]))
                for p in (l.split() for l in text.splitlines())
                if len(p) == 4 and p[3].isalpha()]

    def test_zero_shift_is_identity(self):
        got = self._parse(v1mod.shifted(self.lines, self.lat, 0.0))
        for a, b in zip(self.atoms, got):
            self.assertEqual(a[0], b[0])
            for k in (1, 2, 3):
                self.assertAlmostEqual(a[k], b[k], places=9)

    def test_shift_wraps_into_the_cell(self):
        got = self._parse(v1mod.shifted(self.lines, self.lat, 0.5))
        for _sym, x, y, z in got:
            for v in (x, y, z):
                self.assertGreaterEqual(v, 0.0)
                self.assertLess(v, self.lat)

    def test_full_lattice_shift_returns_the_same_positions(self):
        """격자벡터 1개만큼은 **완전히 동일**해야 한다. 아니면 우리 랩이 틀린 것이다."""
        got = self._parse(v1mod.shifted(self.lines, self.lat, 1.0))
        for a, b in zip(self.atoms, got):
            for k in (1, 2, 3):
                self.assertAlmostEqual(a[k], b[k], places=9)

    def test_lattice_block_is_preserved(self):
        text = v1mod.shifted(self.lines, self.lat, 0.3)
        self.assertIn("$periodic 3", text)
        self.assertIn("$lattice bohr", text)


class TestShiftsAreIsolated(unittest.TestCase):
    """🔴 각 이동이 **독립 디렉터리**에서 도는가 (가짜 BLOCKER 방지)."""

    def test_v1_creates_a_subdirectory_per_shift(self):
        with open(os.path.join(context.PKG_ROOT, "tools", "p2g_v1.py")) as fh:
            src = fh.read()
        self.assertIn("os.makedirs(sub", src,
                      "이동별 디렉터리를 만들지 않는다 — gfnff_topo 캐시가 재사용된다")
        self.assertIn("gfnff_topo", src, "왜 격리하는지 설명이 없다")


class TestRdfAgainstAnalyticCase(unittest.TestCase):
    """🔴 균일 분포에서 g(r) → 1. 규격화가 틀리면 배위수가 조용히 틀린다."""

    def setUp(self):
        rng = random.Random(20260817)
        self.box = 20.0
        frames = []
        for _ in range(12):
            atoms = [("Li", rng.uniform(0, self.box), rng.uniform(0, self.box),
                      rng.uniform(0, self.box)) for _ in range(4)]
            atoms += [("O", rng.uniform(0, self.box), rng.uniform(0, self.box),
                       rng.uniform(0, self.box)) for _ in range(200)]
            frames.append(atoms)
        self.res = v2mod.rdf(frames, self.box)

    def test_g_of_r_approaches_one_for_a_random_gas(self):
        g = self.res["g"]
        tail = [v for r, v in zip(self.res["r_ang"], g) if r > 3.0]
        mean = sum(tail) / len(tail)
        self.assertAlmostEqual(1.0, mean, delta=0.15,
                               msg="균일 분포인데 g(r) 평균이 %.3f — 규격화가 틀렸다"
                                   % mean)

    def test_coordination_number_matches_the_ideal_gas_value(self):
        """CN(r) = (4/3)πr³ρ 여야 한다."""
        rho = 200 / self.box ** 3
        for r_target in (2.0, 4.0):
            k = min(range(len(self.res["r_ang"])),
                    key=lambda i: abs(self.res["r_ang"][i] - r_target))
            ideal = 4.0 / 3.0 * math.pi * r_target ** 3 * rho
            self.assertAlmostEqual(
                ideal, self.res["cumulative_coordination"][k],
                delta=max(0.3, 0.25 * ideal),
                msg="r=%.1f Å 에서 CN 이 이상기체 값과 다르다" % r_target)

    def test_minimum_image_is_applied(self):
        """최소상 규약이 없으면 r > L/2 에서 g 가 무너진다."""
        half = self.box / 2.0
        near = [v for r, v in zip(self.res["r_ang"], self.res["g"])
                if half - 1.0 < r < half]
        if near:
            self.assertGreater(sum(near) / len(near), 0.5)


class TestRdfPeakDetection(unittest.TestCase):
    def test_finds_peak_and_the_following_minimum(self):
        n = int(v2mod.R_MAX_ANG / v2mod.BIN_WIDTH_ANG)
        r = [(k + 0.5) * v2mod.BIN_WIDTH_ANG for k in range(n)]
        g = [math.exp(-((x - 2.0) ** 2) / 0.02) for x in r]
        cn = [0.0] * n
        peak, minimum, _cn = v2mod.first_peak_and_cn(
            {"r_ang": r, "g": g, "cumulative_coordination": cn})
        self.assertAlmostEqual(2.0, peak, delta=0.06)
        self.assertGreater(minimum, peak)

    def test_empty_histogram_returns_none_not_zero(self):
        """봉우리가 없으면 None 이다. 0.0 으로 내면 '거리 0 Å'로 읽힌다."""
        n = 10
        peak, _m, _c = v2mod.first_peak_and_cn(
            {"r_ang": [0.1 * k for k in range(n)], "g": [0.0] * n,
             "cumulative_coordination": [0.0] * n})
        self.assertIsNone(peak)


class TestCollectorHandlesMissingArtifacts(unittest.TestCase):
    def setUp(self):
        from sei_pilot.state import Store
        self.d = tempfile.mkdtemp(prefix="sei_p2g_")
        self.store = Store(self.d)
        self.job_dir = self.store.job_dir("P2g")
        os.makedirs(os.path.join(self.d, "state"), exist_ok=True)
        with open(os.path.join(self.d, "state", "P2g.done.json"), "w") as fh:
            json.dump({"key": "P2g", "status": "done",
                       "payload": {"start_epoch": 0, "end_epoch": 60, "rc": 0,
                                   "total_cores": 1, "nodes": 1}}, fh)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _collect(self):
        from sei_pilot import collect as collect_mod
        return collect_mod.collect_p2g(self.store)

    def test_missing_results_are_explained_not_silent(self):
        res = self._collect()
        self.assertEqual("missing", res["v1"]["status"])
        self.assertIn("why", res["v1"])
        self.assertIn("why", res["v2"])

    def test_v1_failure_is_carried_through_verbatim(self):
        with open(os.path.join(self.job_dir, "v1_result.json"), "w") as fh:
            json.dump({"v1_translation_invariant": False,
                       "max_abs_deviation_ev": 591.06}, fh)
        res = self._collect()
        self.assertFalse(res["v1"]["v1_translation_invariant"])
        self.assertAlmostEqual(591.06, res["v1"]["max_abs_deviation_ev"])

    def test_collector_does_not_pass_judgement(self):
        """🔴 우리는 판정하지 않는다 — 그 사실이 회신에 명시돼야 한다."""
        self.assertIn("판정하지 않는다", self._collect()["_no_verdict"])


class TestVendoredXtbCanDoPeriodicGfnff(unittest.TestCase):
    """🔴 동봉 xtb 가 주기계 GFN-FF 를 실제로 도는가 (양성 대조군).

    안 되면 V1/V2 가 전부 'xtb 없음'처럼 조용히 비어 나온다.
    """

    def setUp(self):
        from sei_pilot import envpaths
        self.v = envpaths.vendored("xtb", context.PKG_ROOT)
        if not self.v:
            self.skipTest("동봉 xtb 없음")
        self.d = tempfile.mkdtemp(prefix="sei_xtbp_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_periodic_single_point_terminates_normally(self):
        # 좌표는 셀 안에 둔다 — 밖에 두면 xtb 가 랩하면서 분자를 쪼갠다
        # (실제로 물 분자가 17.01 / 1.01 amu 로 갈라지는 것을 봤다).
        atoms = [("o", 5.0, 5.0, 5.0), ("h", 6.81, 5.0, 5.0),
                 ("h", 4.55, 6.75, 5.0)]
        with open(os.path.join(self.d, "coord"), "w") as fh:
            fh.write(_coord_text(atoms, 18.9))
        env = dict(os.environ, **self.v["env"])
        proc = subprocess.run([self.v["path"], "coord", "--gfnff", "--sp"],
                              cwd=self.d, env=env, capture_output=True,
                              text=True, timeout=300)
        # 🔴 `normal termination` 배너로 판정하지 않는다 — xtb 6.7.1 은 주기계
        #    GFN-FF 단일점에서 에너지를 정상 생성하고도 배너를 안 찍는다
        #    (`gfnff_setup: Could not read topology file` 경고와 함께).
        #    배너로 판정하면 멀쩡한 결과를 전부 버린다.
        self.assertIn("TOTAL ENERGY", proc.stdout,
                      proc.stdout[-1500:] + proc.stderr[-500:])
        self.assertNotIn("abnormal termination", proc.stdout)


if __name__ == "__main__":
    unittest.main()
