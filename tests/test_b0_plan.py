"""B0's item list, sizing and guard check.

🔴 THE TWO NUMBERS ARE THE SUBJECT. `reserved` is the physical ceiling the scheduler must admit;
   `expected` is what we think we will spend. They are never one number, and the MTD stage is
   sized against its 20 ps CAP because a discovery-rate stopping rule has no constant wall time --
   §R24.1's ceiling/consumption distinction, applied where a forecast would have been a fabrication.

🔴 AND THERE ARE NO UNIT COSTS YET. That is the honest state: they are MEASURED, not invented, so
   `size()` returns null totals rather than a partial sum and `check_against_guard` returns
   `fits: None` rather than `True`.
"""

import unittest

import context  # noqa: F401
from sei_pilot import b0_plan, budget


class TestItemList(unittest.TestCase):
    def setUp(self):
        self.items = b0_plan.items()
        self.by = {}
        for i in self.items:
            self.by.setdefault(i["stage"], []).append(i)

    def test_counts_are_derived_from_the_definitions_not_typed(self):
        self.assertEqual(self.by[b0_plan.STAGE_MTD][0]["n_tasks"], 23)
        self.assertEqual(self.by[b0_plan.STAGE_DFT_HIGH][0]["n_tasks"], 23)
        self.assertEqual(self.by[b0_plan.STAGE_TS][0]["n_tasks"], 6)
        self.assertEqual(self.by[b0_plan.STAGE_EPS][0]["n_tasks"], 27)

    def test_arm_two_is_three_tasks_and_says_the_rest_is_not_missing_data(self):
        arm2_rows = [i for i in self.items if i["arm"] == 2]
        self.assertEqual(len(arm2_rows), 1)
        self.assertEqual(arm2_rows[0]["n_tasks"], 3)
        self.assertIn("not missing data", arm2_rows[0]["note"])

    def test_arm_three_emits_frequencies_not_just_energies(self):
        self.assertIn("FREQUENCY LIST", self.by[b0_plan.STAGE_DFT_HIGH][0]["note"])
        self.assertIn("U-60", self.by[b0_plan.STAGE_DFT_HIGH][0]["note"])

    def test_the_ts_stage_runs_at_composite(self):
        self.assertIn("COMPOSITE", self.by[b0_plan.STAGE_TS][0]["note"])

    def test_the_epsilon_scan_adds_no_geometry_work(self):
        self.assertIn("zero new geometry work", self.by[b0_plan.STAGE_EPS][0]["note"])

    def test_the_mtd_row_says_it_is_a_ceiling(self):
        self.assertIn("CEILING, not a forecast", self.by[b0_plan.STAGE_MTD][0]["note"])


class TestMtdIsSizedAtItsCapNotAForecast(unittest.TestCase):
    def test_the_cap_is_the_stopping_rules_own_cap(self):
        c = b0_plan.mtd_ceiling_wall_h()
        self.assertEqual(c["cap_ps"], 20.0)
        self.assertIn("DISCOVERY RATE", c["rule"])

    def test_it_declares_itself_a_ceiling(self):
        self.assertIn("ceiling", b0_plan.mtd_ceiling_wall_h()["_is_a_ceiling_not_a_forecast"])
        self.assertIn("R24.1", b0_plan.mtd_ceiling_wall_h()["_is_a_ceiling_not_a_forecast"])


class TestCapBindingIsReported(unittest.TestCase):
    """🔒 A truncation that is not reported looks exactly like convergence."""

    def test_cap_terminated_species_are_named(self):
        r = b0_plan.cap_binding_report([
            {"species_id": "a", "stopped_by": "discovery_rate", "time_ps": 6.0},
            {"species_id": "b", "stopped_by": "cap", "time_ps": 20.0},
            {"species_id": "c", "stopped_by": "cap", "time_ps": 20.0}])
        self.assertEqual(r["n_stopped_by_cap"], 2)
        self.assertEqual(r["species_stopped_by_cap"], ["b", "c"])
        self.assertAlmostEqual(r["cap_binding_fraction"], 2 / 3.0)
        self.assertIn("TRUNCATED, not converged", " ".join(r["warnings"]))

    def test_no_cap_binding_produces_no_warning(self):
        r = b0_plan.cap_binding_report([{"species_id": "a", "stopped_by": "discovery_rate"}])
        self.assertEqual(r["n_stopped_by_cap"], 0)
        self.assertEqual(r["warnings"], [])

    def test_an_unrecorded_stop_reason_is_flagged_not_assumed_converged(self):
        r = b0_plan.cap_binding_report([{"species_id": "a"}])
        self.assertEqual(r["n_stopped_by_unknown"], 1)
        self.assertIn("cannot be told from a truncated one", " ".join(r["warnings"]))

    def test_an_empty_set_gives_none_not_zero_fraction(self):
        self.assertIsNone(b0_plan.cap_binding_report([])["cap_binding_fraction"])


class TestSizingKeepsTwoNumbers(unittest.TestCase):
    def _units(self, reserved=10.0, expected=3.0):
        return dict((s, {"reserved": reserved, "expected": expected})
                    for s in (b0_plan.STAGE_PREOPT, b0_plan.STAGE_MTD,
                              b0_plan.STAGE_DFT_CHEAP, b0_plan.STAGE_DFT_HIGH,
                              b0_plan.STAGE_TS, b0_plan.STAGE_EPS))

    def test_reserved_and_expected_are_separate_and_differ(self):
        s = b0_plan.size(self._units())
        self.assertTrue(s["complete"])
        self.assertGreater(s["reserved_core_hours_knl"], s["expected_core_hours_knl"])
        self.assertAlmostEqual(s["reserved_core_hours_knl"], 128 * 10.0)
        self.assertAlmostEqual(s["expected_core_hours_knl"], 128 * 3.0)

    def test_both_totals_are_reported_in_both_units(self):
        """🔴 The approval is in REFERENCE core-h; the scheduler counts KNL."""
        s = b0_plan.size(self._units())
        self.assertAlmostEqual(
            s["reserved_core_hours_reference"],
            s["reserved_core_hours_knl"] / budget.KAPPA_PHYSICAL)
        self.assertEqual(s["kappa"], 2.4)

    def test_an_unpriced_stage_nulls_BOTH_totals_rather_than_partially_summing(self):
        """🔴 A partial total reads as a total."""
        u = self._units()
        del u[b0_plan.STAGE_TS]
        s = b0_plan.size(u)
        self.assertFalse(s["complete"])
        self.assertIsNone(s["reserved_core_hours_knl"])
        self.assertIsNone(s["expected_core_hours_knl"])
        self.assertEqual(s["unpriced_stages"], [b0_plan.STAGE_TS])
        self.assertIn("sizing_incomplete", " ".join(s["warnings"]))

    def test_it_refuses_to_supply_unit_costs_itself(self):
        """🔴 An invented unit cost is a fabrication wearing a number's clothes."""
        s = b0_plan.size({})
        self.assertIn("MUST NOT", s["_unit_costs_are_not_invented"])
        self.assertIn("MEASURED", s["_unit_costs_are_not_invented"])
        self.assertIsNone(s["reserved_core_hours_knl"])


class TestGuardCheckReadsTheGuardNotADocument(unittest.TestCase):
    def _sized(self, reserved_total):
        return {"reserved_core_hours_knl": reserved_total}

    def test_the_ceiling_comes_from_budget_not_a_literal(self):
        c = b0_plan.check_against_guard(self._sized(1000.0))
        self.assertEqual(c["guard_source"], "budget.b0_guard_spec()")
        self.assertEqual(c["guard_core_hours_knl"],
                         budget.b0_guard_spec()["max_core_hours"])
        self.assertEqual(c["guard_reference_core_hours"], 15000.0)

    def test_a_fitting_reservation_reports_headroom_in_both_units(self):
        c = b0_plan.check_against_guard(self._sized(30000.0))
        self.assertTrue(c["fits"])
        self.assertAlmostEqual(c["headroom_core_hours_knl"], 6000.0)
        self.assertAlmostEqual(c["headroom_reference_core_hours"], 2500.0)

    def test_a_breach_reports_and_refuses_to_adjust_anything(self):
        """🔴 §R24.1: suspect the specification, never raise the guard."""
        c = b0_plan.check_against_guard(self._sized(40000.0))
        self.assertFalse(c["fits"])
        self.assertIn("b0_exceeds_guard", " ".join(c["warnings"]))
        self.assertIn("lead's to choose", c["_never_raise"])
        # and it must not have mutated the guard
        self.assertEqual(budget.b0_guard_spec()["max_core_hours"], 36000.0)

    def test_an_incomplete_sizing_gives_fits_none_not_true(self):
        """🔴 Rule 18. 'Unknown' must not fall toward 'fits'."""
        c = b0_plan.check_against_guard({"reserved_core_hours_knl": None})
        self.assertIsNone(c["fits"])
        self.assertIn("guard_check_not_performed", " ".join(c["warnings"]))
        self.assertIn("Not 'fits'", " ".join(c["warnings"]))


if __name__ == "__main__":
    unittest.main()
