"""단위 변환 왕복 + 자원 가드 테스트.

단위 혼용(eV/Hartree/kcal)은 이 분야 버그의 최대 원인이므로 왕복을 강제 검증한다.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import plan
from sei_pilot import budget, units


class TestUnitRoundTrips(unittest.TestCase):
    def test_hartree_ev_roundtrip(self):
        for e in (0.0, 1e-5, 1.0, -123.456):
            self.assertAlmostEqual(units.ev_to_hartree(units.hartree_to_ev(e)), e, places=12)

    def test_ev_kcal_roundtrip(self):
        for e in (0.1, 1.0, -2.5):
            self.assertAlmostEqual(units.kcal_per_mol_to_ev(units.ev_to_kcal_per_mol(e)),
                                   e, places=12)

    def test_ev_kj_roundtrip(self):
        self.assertAlmostEqual(units.kj_per_mol_to_ev(units.ev_to_kj_per_mol(1.0)), 1.0, 12)

    def test_known_constants(self):
        # 1 Hartree = 27.2114 eV = 627.51 kcal/mol
        self.assertAlmostEqual(units.hartree_to_ev(1.0), 27.211386, places=5)
        self.assertAlmostEqual(units.ev_to_kcal_per_mol(units.hartree_to_ev(1.0)),
                               627.5095, places=2)
        # 1 eV = 8065.54 cm^-1
        self.assertAlmostEqual(units.cm1_to_ev(8065.544), 1.0, places=5)

    def test_p4_tolerance_is_in_hartree_not_ev(self):
        """1e-5 Ha = 0.272 meV. eV로 임계값을 착각하면 273배 틀린다."""
        self.assertAlmostEqual(units.hartree_to_mev(1e-5), 0.27211, places=4)


class TestComputeUnits(unittest.TestCase):
    def test_core_hours(self):
        self.assertAlmostEqual(units.core_hours(64, 3600), 64.0)
        self.assertAlmostEqual(units.core_hours(1, 60), 1.0 / 60.0)

    def test_node_core_conversion_roundtrip(self):
        ch = units.node_hours_to_core_hours(4.0, 64)
        self.assertAlmostEqual(ch, 256.0)
        self.assertAlmostEqual(units.core_hours_to_node_hours(ch, 64), 4.0)

    def test_drift_units(self):
        """1 Hartree 를 100원자 1 ps 에 걸쳐 잃으면 272.1 meV/atom/ps."""
        d = units.drift_mev_per_atom_per_ps(1.0, 100, 1.0)
        self.assertAlmostEqual(d, 272.11386, places=3)

    def test_drift_rejects_bad_args(self):
        self.assertRaises(ValueError, units.drift_mev_per_atom_per_ps, 1.0, 0, 1.0)


class TestResourceGuard(unittest.TestCase):
    def test_accepts_within_budget(self):
        g = budget.ResourceGuard(max_core_hours=1000)
        self.assertTrue(g.reserve("a", 400, wall_h=2))
        self.assertTrue(g.reserve("b", 600, wall_h=2))
        self.assertAlmostEqual(g.reserved_core_hours, 1000)
        self.assertEqual(g.rejected, [])

    def test_rejects_over_budget_and_records_reason(self):
        g = budget.ResourceGuard(max_core_hours=1000)
        g.reserve("a", 900, wall_h=1)
        self.assertFalse(g.reserve("b", 200, wall_h=1))
        rej = g.rejection("b")
        self.assertEqual(rej["reason"], "budget_guard")
        self.assertIn("기본 상한", rej["detail"])       # 어떤 값인지 안내가 들어간다
        self.assertAlmostEqual(g.reserved_core_hours, 900)   # 예약은 늘지 않는다

    def test_wall_guard(self):
        g = budget.ResourceGuard(max_core_hours=1e9, max_wall_h=24)
        self.assertFalse(g.reserve("long", 10, wall_h=48))
        self.assertEqual(g.rejection("long")["reason"], "wall_guard")

    def test_gpu_guard(self):
        g = budget.ResourceGuard(max_gpu_hours=1.0)
        self.assertTrue(g.reserve("p4", 0, gpu_hours=1.0, wall_h=1))
        self.assertFalse(g.reserve("p4b", 0, gpu_hours=0.5, wall_h=1))

    def test_measured_accounting(self):
        g = budget.ResourceGuard()
        g.record_measured("P1", 64, 1800)      # 64코어 x 0.5h
        self.assertAlmostEqual(g.measured_core_hours, 32.0)
        self.assertIn("P1", g.to_dict()["measured_by_item"])

    def test_profile_guards(self):
        """🔴 CPU/GPU 머신이 분리돼 패키지가 둘이고 상한도 다르다.

        🔒 **의도된 변화 (§R24.1): cpu 5,000/24h → 21,000/48h.**
        사유: "§R21 KNL 판명(κ=3.4~6.8)에 따른 재산정. 종전 값은 κ=1 단위였다."
        🔴 21,000 의 정의는 **[물리 천장]** 이지 소비 전망이 아니다(전망은 16,486).
           guard 를 전망에 걸면 `describe()` 의 "제출 자체가 되지 않는다"가 거짓이 되고,
           **신뢰받는 안전장치가 실제로는 작동하지 않는 것은 없느니만 못하다**(§R24.1).
        🔴 48 h 는 우리 자신의 캡이다. 실제 wall 상한은 `plan.resolve_wall_limit` 가
           `qstat -Qf` 에서 읽는다 — 사이트 문서값을 코드에 박지 않는다.
        gpu 는 GPU-h 4 + wall 48[ADR-114] 이 본 상한이고 core-h 는 같은 머신 CPU 기준
        계산분이다.
        """
        cpu = budget.guard_for_profile("cpu")
        self.assertEqual(cpu.max_core_hours, 21000.0)
        self.assertEqual(cpu.max_wall_h, 48.0)
        gpu = budget.guard_for_profile("gpu")
        self.assertEqual(gpu.max_gpu_hours, 4.0)
        self.assertEqual(gpu.max_wall_h, 48.0)   # [ADR-114] 24 -> 48, 사용자 직접 지시
        self.assertLess(gpu.max_core_hours, cpu.max_core_hours)

    def test_guard_exists_in_every_profile(self):
        """🔴 어떤 프로파일에서도 '상한 초과 잡은 제출 자체가 안 된다'가 유지된다."""
        for prof in ("cpu", "gpu"):
            g = budget.guard_for_profile(prof)
            self.assertGreater(g.max_core_hours, 0)
            self.assertGreater(g.max_wall_h, 0)
            self.assertFalse(g.reserve("huge", g.max_core_hours + 1, wall_h=1))
            self.assertFalse(g.reserve("long", 1.0, wall_h=g.max_wall_h + 1))

    def test_cli_override_keeps_the_guard(self):
        g = budget.guard_for_profile("cpu", max_core_hours=100.0)
        self.assertEqual(g.max_core_hours, 100.0)
        self.assertFalse(g.reserve("x", 101.0, wall_h=1))

    def test_original_value_kept_for_regression(self):
        self.assertEqual(budget.ORIGINAL_R2_6_MAX_CORE_HOURS, 2000.0)

    def test_guard_source_is_derived_from_the_actual_values(self):
        """🔴 critic MAJOR: guard_source 가 리터럴이라 max_core_hours 와 모순됐다.

        같은 사실을 두 곳에 적으면 반드시 한쪽만 갱신된다(B-1·B-2·wb97x-d3와 같은 계열).
        이제 서술은 값에서 파생되며, 이 테스트가 그 결합을 고정한다.
        """
        for prof in ("cpu", "gpu"):
            d = budget.guard_for_profile(prof).to_dict()
            self.assertIn("%.0f core-h" % d["max_core_hours"], d["guard_source"])
            self.assertIn("%.0f h wall" % d["max_wall_h"], d["guard_source"])
            self.assertIn(prof, d["guard_source"])
            self.assertEqual(d["profile"], prof)

    def test_guard_source_follows_cli_override(self):
        """재정의해도 서술이 따라와야 한다 — 이것이 리터럴이었을 때의 실패다."""
        d = budget.guard_for_profile("cpu", max_core_hours=1234.0).to_dict()
        self.assertIn("1234 core-h", d["guard_source"])
        self.assertNotIn("5000", d["guard_source"])

    def test_guard_source_has_no_stale_hardcoded_number(self):
        """🔴 회귀: 예전 리터럴('4,000 core-h / … ~3,150')이 다시 들어오면 실패한다."""
        for prof in ("cpu", "gpu"):
            src = budget.guard_for_profile(prof).to_dict()["guard_source"]
            for stale in ("4,000", "3,150", "2,000"):
                self.assertNotIn(stale, src, "%s 에 낡은 리터럴 %s" % (prof, stale))

    def test_gpu_hours_appear_only_when_nonzero(self):
        self.assertNotIn("GPU-h", budget.guard_for_profile("cpu").to_dict()["guard_source"])
        self.assertIn("4 GPU-h", budget.guard_for_profile("gpu").to_dict()["guard_source"])

    def test_guard_source_states_the_enforcement_property(self):
        """사용자가 읽는 문장이므로 '제출 자체가 안 된다'는 성질이 남아야 한다."""
        src = budget.guard_for_profile("cpu").to_dict()["guard_source"]
        self.assertIn("제출 자체가 되지 않는다", src)

    def test_estimate_core_hours(self):
        self.assertAlmostEqual(budget.estimate_core_hours(64, 2.0), 128.0)


if __name__ == "__main__":
    unittest.main()


class TestPlanAndMeasuredUseTheSameCoreHourDefinition(unittest.TestCase):
    """🔴 계획 경로와 실측 경로가 **같은 core-h 정의**를 쓰는가 (critic2 지적).

    `plan.py:size_job()` 과 array 특례가 `units.core_hours()` 를 **안 부르고**
    `total_cores * wall * links` 를 자기가 계산하고 있었다. 그 값이 그대로
    `guard.reserve(core_hours=...)` 로 들어가 **5,000 core-h 가드 판정과 화면의
    "예약 core-h" 전부의 근원**이 된다. 반면 `budget.record_measured()` 는
    `units.core_hours()` 를 정확히 부른다 — **계획값과 실측값이 서로 다른 코드 경로**였다.

    🟢 값은 소수점까지 일치했다. 🔴 그러나 `S_TO_H` 나 공식이 바뀌면 그 두 자리는
    조용히 안 따라온다. `units.py` 주석이 *"이 정의를 다른 데서 다시 쓰지 마라"* 고
    **말만** 하고 있던 자리다.
    """

    # critic2 가 대조한 3케이스. 값이 바뀌면 곧 회귀다.
    CASES = [
        {"budget": 500.0, "cpn": 32, "nodes": 1, "max_wall": 24.0,
         "expect_reserved": 500.0},
        {"budget": 1008.0, "cpn": 16, "nodes": 1, "max_wall": 1.0,
         "expect_reserved": 1008.0, "expect_links": 63},
        # 🔴 이 케이스는 내가 기대값을 틀렸다가 코드에서 배운 것이다:
        #    이상 wall = 60/256 = 0.234 h 인데 MIN_WALL_H(0.25) 하한에 걸려
        #    예약이 256 × 0.25 = **64** 가 된다. 예산보다 큰 예약이 정상이다.
        #    (코드를 내 기대에 맞추지 않았다 — 코드가 맞았다.)
        {"budget": 60.0, "cpn": 64, "nodes": 4, "max_wall": 24.0,
         "expect_reserved": 64.0},
    ]

    def test_size_job_values_are_unchanged(self):
        for c in self.CASES:
            wall, links, reserved = plan.size_job(
                c["budget"], c["cpn"], c["nodes"], c["max_wall"])
            self.assertAlmostEqual(c["expect_reserved"], reserved, places=2,
                                   msg="예약 core-h 가 바뀌었다: %s" % c)
            if "expect_links" in c:
                self.assertEqual(c["expect_links"], links, c)

    def test_size_job_agrees_with_units_definition(self):
        """계획값을 units 로 독립 재계산해 일치하는지 본다."""
        for c in self.CASES:
            wall, links, reserved = plan.size_job(
                c["budget"], c["cpn"], c["nodes"], c["max_wall"])
            total_cores = c["cpn"] * c["nodes"]
            independent = round(
                units.core_hours(total_cores, wall * units.H_TO_S) * links, 2)
            self.assertAlmostEqual(independent, reserved, places=2,
                                   msg="계획 경로가 units 정의와 다르다: %s" % c)

    def test_array_reservation_agrees_with_units(self):
        n_tasks, wall = 200, 0.025
        self.assertAlmostEqual(
            5.0, round(units.core_hours_h(n_tasks, wall), 2), places=2)

    def test_plan_does_not_compute_core_hours_itself(self):
        """🔴 정적 검사 — `plan.py` 가 core-h 산술을 다시 쓰지 않는가."""
        with open(os.path.join(context.PKG_ROOT, "sei_pilot", "plan.py")) as fh:
            code = [l for l in fh if not l.lstrip().startswith("#")]
        joined = "".join(code)
        for pattern in ("total_cores * wall * links", "n_tasks * 1 * wall"):
            self.assertNotIn(pattern, joined,
                             "plan.py 가 core-h 를 자기가 계산한다: %s" % pattern)
        self.assertIn("units.core_hours_h(", joined)

    def test_seconds_and_hours_apis_agree(self):
        """두 입력 단위판이 같은 정의를 쓰는가 (단위 혼용이 이 분야 최대 버그원)."""
        for cores, hours in ((1, 1.0), (64, 0.25), (128, 23.75), (7, 1.0 / 60.0)):
            self.assertEqual(units.core_hours_h(cores, hours),
                             units.core_hours(cores, hours * units.H_TO_S))

    def test_changing_the_definition_would_break_both_paths_together(self):
        """정의가 하나임을 못박는다 — 초 단위판이 시간판을 호출해야 한다."""
        import inspect
        src = inspect.getsource(units.core_hours)
        self.assertIn("core_hours_h", src,
                      "초 단위판이 정의를 따로 갖고 있다")
