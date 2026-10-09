"""The user's B0 approval, made enforceable — and the 6 h/job tripwire, actually wired.

🔴 THE UNIT IS THE SUBJECT OF THIS FILE, not a detail.

    the approval / every document figure   REFERENCE core-h
    what `ResourceGuard` counts            KNL core-h  (`cores x wall`, `plan.size_job`)
    kappa == (KNL core-h)/(reference core-h) == 2.4     (R29.1, both sides PHYSICAL cores)

  So the two numbers that look like the answer are both wrong:
      15,000 typed into `max_core_hours`  is 15,000 KNL = 6,250 reference -> BLOCKS most of B0
      21,000 (RT-1's pilot figure)        is 21,000 KNL =  8,750 reference -> also blocks it
  and the correct figure, 36,000 KNL, is NUMERICALLY LARGER than 21,000 while being a SMALLER
  ceiling in the unit the user approved.

🔒 This is exactly the eV/Hartree class of error the project's own coding rules open with, arriving
   in core-hours. The defence is that the KNL number is DERIVED from the reference number in one
   function and can never be typed independently.
"""

import unittest

import context  # noqa: F401
from sei_pilot import budget, guards


class TestB0GuardIsTheApprovedFigure(unittest.TestCase):
    def test_the_authority_is_the_reference_figure_the_user_approved(self):
        self.assertEqual(budget.B0_APPROVED_REFERENCE_CORE_HOURS, 15000.0)

    def test_the_knl_ceiling_is_derived_not_typed(self):
        """If someone edits the KNL number alone, this fails."""
        g = budget.PROFILE_GUARDS["b0"]
        self.assertAlmostEqual(
            g["max_core_hours"],
            budget.B0_APPROVED_REFERENCE_CORE_HOURS * budget.KAPPA_PHYSICAL)
        self.assertAlmostEqual(g["max_core_hours"], 36000.0)

    def test_the_guard_names_its_own_unit(self):
        """A ceiling without its unit is the defect this file exists to prevent."""
        g = budget.PROFILE_GUARDS["b0"]
        self.assertIn("KNL core-h", g["guard_unit"])
        self.assertEqual(g["approved_reference_core_hours"], 15000.0)
        self.assertEqual(g["kappa"], 2.4)

    def test_b0_does_not_inherit_rt1s_pilot_ceiling(self):
        """🔴 21,000 belongs to RT-1 and has no authority over this batch."""
        self.assertNotEqual(budget.PROFILE_GUARDS["b0"]["max_core_hours"],
                            budget.PROFILE_GUARDS["cpu"]["max_core_hours"])
        self.assertAlmostEqual(
            budget.local_to_reference_core_hours(
                budget.PROFILE_GUARDS["cpu"]["max_core_hours"]), 8750.0,
            msg="RT-1's 21,000 KNL guard is 8,750 REFERENCE core-h -- below B0's approved "
                "ceiling, i.e. MORE restrictive, not less. Any argument about which is 'bigger' "
                "has to state the unit.")

    def test_engineer5s_priced_range_fits_under_the_guard_in_the_right_unit(self):
        """The margin, computed rather than quoted. 🔴 Rule 11: derived values are computed."""
        ceiling = budget.PROFILE_GUARDS["b0"]["max_core_hours"]
        top_knl = budget.reference_to_local_core_hours(14130.0)   # engineer5's upper bound
        self.assertLess(top_knl, ceiling)
        margin_ref = 15000.0 - 14130.0
        self.assertAlmostEqual(margin_ref, 870.0)
        self.assertAlmostEqual(margin_ref / 15000.0 * 100.0, 5.8, places=1)

    def test_the_old_pilot_guard_would_have_blocked_b0(self):
        """🔴 Stated as a measurement, because the prose reading of it went the other way."""
        self.assertLess(budget.PROFILE_GUARDS["cpu"]["max_core_hours"],
                        budget.reference_to_local_core_hours(14130.0))

    def test_kappa_is_the_physical_convention_not_the_thread_one(self):
        """kappa_thread = 1.207 exists and is the WRONG unit; using it halves the reservation."""
        self.assertEqual(budget.KAPPA_PHYSICAL, 2.4)
        self.assertNotEqual(budget.KAPPA_PHYSICAL, 1.207)

    def test_the_conversion_round_trips(self):
        for ref in (1.0, 5114.0, 14130.0, 15000.0):
            self.assertAlmostEqual(
                budget.local_to_reference_core_hours(
                    budget.reference_to_local_core_hours(ref)), ref, places=9)

    def test_the_provenance_reaches_the_guard_object_not_just_the_table(self):
        """Rule 13 — a ceiling that arrives without its unit is the defect, restated."""
        g = budget.guard_for_profile("b0")
        # Presence before value, so a dropped provenance reports FAIL rather than KeyError/ERROR.
        for key in ("approved_reference_core_hours", "guard_unit", "kappa", "not_a_raise"):
            self.assertIn(key, g.provenance,
                          "the B0 guard object lost %r on the way out of guard_for_profile -- a "
                          "ceiling reaching the reply without its unit is the defect this whole "
                          "file exists to prevent" % key)
        self.assertEqual(g.provenance["approved_reference_core_hours"], 15000.0)
        self.assertIn("KNL core-h", g.provenance["guard_unit"])
        self.assertIn("NUMERICALLY", g.provenance["not_a_raise"])

    def test_the_guard_still_rejects_over_ceiling_reservations(self):
        """The point of all this: the ceiling must actually BIND."""
        g = budget.guard_for_profile("b0")
        self.assertTrue(g.reserve("a", core_hours=30000.0))
        self.assertFalse(g.reserve("b", core_hours=10000.0),
                         "the B0 guard accepted a reservation past its ceiling")


class TestTripwireIsWiredNotMerelyRecorded(unittest.TestCase):
    """🔴 The 6 h cap bounds the case engineer5 deliberately did not price (radical-SCF risk)."""

    def test_the_b0_profile_caps_the_requested_wall_at_six_hours(self):
        """PREVENTION half: the planner requests <= 6 h, so the scheduler kills a runaway."""
        self.assertEqual(budget.B0_TRIPWIRE_WALL_H, 6.0)
        self.assertEqual(budget.PROFILE_GUARDS["b0"]["max_wall_h"], 6.0)
        self.assertEqual(budget.guard_for_profile("b0").max_wall_h, 6.0)

    def test_b0_does_not_inherit_the_48_hour_queue_wall(self):
        """R35.2b: adopted as written and NOT left to the queue's default."""
        self.assertNotEqual(budget.PROFILE_GUARDS["b0"]["max_wall_h"],
                            budget.PROFILE_GUARDS["cpu"]["max_wall_h"])

    def _log(self, started, cores=16, finished=False):
        recs = [{"link": "B0D_li_ec3_cation", "action": "run", "epoch": started,
                 "host": "node0517", "cores": cores}]
        if finished:
            recs.append({"link": "B0D_li_ec3_cation", "action": "finish",
                         "epoch": started + 60, "rc": 0})
        return recs

    def test_a_job_killed_at_the_cap_is_detected_and_its_core_h_reported(self):
        """DETECTION half: a job PBS killed writes `run` and never writes `finish`."""
        now = 1_800_000_000
        aborts = guards.detect_tripwire_aborts(
            self._log(now - 7 * 3600), cap_h=6.0, now_epoch=now)
        self.assertEqual(len(aborts), 1)
        a = aborts[0]
        self.assertEqual(a["status"], guards.TRIPWIRE_ABORTED)
        self.assertAlmostEqual(a["core_hours"], 16 * 7.0, places=3)
        self.assertTrue(a["counts_toward_spend"])
        self.assertTrue(a["core_hours_is_lower_bound"])
        self.assertEqual(a["host"], "node0517")

    def test_a_job_that_finished_is_not_an_abort(self):
        now = 1_800_000_000
        self.assertEqual(guards.detect_tripwire_aborts(
            self._log(now - 7 * 3600, finished=True), 6.0, now), [])

    def test_a_job_still_inside_the_cap_is_not_an_abort(self):
        """🔴 Failure direction: a running job is not an abort. Do not manufacture one."""
        now = 1_800_000_000
        self.assertEqual(guards.detect_tripwire_aborts(
            self._log(now - 2 * 3600), 6.0, now), [])

    def test_an_abort_without_cores_says_so_instead_of_guessing(self):
        """A payload built before R31.2a cannot be accounted for, and must say that."""
        now = 1_800_000_000
        recs = [{"link": "old", "action": "run", "epoch": now - 7 * 3600}]
        a = guards.detect_tripwire_aborts(recs, 6.0, now)[0]
        self.assertIsNone(a["core_hours"])
        self.assertIn("R31.2a", " ".join(a["warnings"]))

    def test_an_aborted_job_is_counted_in_the_spend_but_not_in_convergence(self):
        """C-13 + C-1 together: it SPENT allocation and it MEASURED no energy."""
        now = 1_800_000_000
        a = guards.detect_tripwire_aborts(self._log(now - 7 * 3600), 6.0, now)[0]
        self.assertEqual(guards.spend_core_hours([a]), a["core_hours"])
        self.assertFalse(a["converged"])
        self.assertIsNone(guards.derived_or_null({"x": a}, lambda s: 1.0)[0])

    def test_aborts_are_never_dropped_from_the_accounting(self):
        """🔴 A job that vanishes is how a ceiling is exceeded while the numbers look fine."""
        now = 1_800_000_000
        recs = (self._log(now - 7 * 3600)
                + [{"link": "other", "action": "run", "epoch": now - 9 * 3600,
                    "host": "node0518", "cores": 32}])
        aborts = guards.detect_tripwire_aborts(recs, 6.0, now)
        self.assertEqual(len(aborts), 2)
        self.assertAlmostEqual(guards.spend_core_hours(aborts), 16 * 7.0 + 32 * 9.0, places=3)


if __name__ == "__main__":
    unittest.main()
