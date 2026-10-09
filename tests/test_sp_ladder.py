"""[39.47(c), 39.48(d)/(e), R39.26, R39.28] The SP ladder's plan Items and its replan trigger.

A full transition-state search is unaffordable at production size, so the ladder lays DFT single
points on a GFN2 path. What these tests fix is mostly the DISCIPLINE around a number nobody has
measured yet: the per-SP cost is a derived stack (an anchor / cycles x multiplier), and the first
rung to return is this project's first single-point measurement.
"""

import json
import os
import unittest

import context  # noqa: F401
from sei_pilot import config, plan


class TestRungsAndCosts(unittest.TestCase):
    def test_three_rungs_at_the_priced_costs(self):
        items = plan.sp_ladder_items()
        self.assertEqual(["sp_ladder_n1", "sp_ladder_n2", "sp_ladder_n3"],
                         [i.key for i in items])
        self.assertEqual([10.0, 70.0, 227.0], [i.core_hours_budget for i in items])
        self.assertEqual(307.0, sum(i.core_hours_budget for i in items))

    def test_n4_is_absent_and_that_is_deliberate(self):
        """🔴 39.48(c): a 2-D scan is a PRECONDITION for n=4, and it does not exist. 1-D
        inflates the barrier by 0.00 / 0.10 / 0.21 eV at n = 1 / 2 / 3, so an n=4 rung without
        one would spend 522 core-h to produce a number wrong by an unmeasured amount."""
        self.assertNotIn("sp_ladder_n4", [i.key for i in plan.sp_ladder_items()])
        self.assertIn("n = 4 IS DELIBERATELY ABSENT", plan.sp_ladder_items.__doc__)

    def test_cores_are_declared_not_defaulted(self):
        """🔴 [ADR-110] `cores_per_task=None` means "the whole node" and would charge a
        ceiling against cores the work never uses. These really are 64-core G16 single points,
        so work ~= charged -- and DECLARING it is what makes that claim checkable."""
        for item in plan.sp_ladder_items():
            self.assertEqual(64, item.cores_per_task, item.key)

    def test_every_rung_carries_the_estimate_status_and_the_replan_trigger(self):
        """A cost that is a derived stack must say so where a reader meets it, not only in a
        document. The first rung IS the measurement that replaces it."""
        for item in plan.sp_ladder_items():
            self.assertIn("[ESTIMATE", item.rationale, item.key)
            self.assertIn("re-derived from it", item.rationale, item.key)
            self.assertIn("PRE-REGISTERED", item.rationale, item.key)


class TestThePayloadExistsBeforeTheGateCanOpen(unittest.TestCase):
    """🔴 [critic10] `sp_ladder_items()` names `payload/SP_LADDER.sh` and **the file does not
    exist**. Neither existing check catches it: the cross-item scan walks `_all_items()`, which
    correctly excludes the ladder while the gate is off, and this file calls `sp_ladder_items()`
    directly — bypassing the gate but never asserting the payload is there.

    🔒 So the gap is invisible in exactly the window where it is safe, and becomes a submission
    failure the moment someone flips `released`. U56-2's sibling test already asserts this for
    its own payloads; the ladder simply never got the same line.
    🔒 Written as the INVARIANT rather than as a bare existence check: `released => payload
    exists`. A test that simply fails until someone writes the file would sit red for as long
    as the ladder is unbuilt, and a permanently red test is one people learn to skip — which
    is how the gap it guards gets through anyway. This form is green today, and goes red at
    exactly the moment it matters: the first attempt to release without a payload.
    """

    def test_releasing_the_ladder_requires_its_payload_to_exist(self):
        missing = [i.payload for i in plan.sp_ladder_items()
                   if not os.path.exists(os.path.join(context.PKG_ROOT, i.payload))]
        if plan.sp_ladder_released():
            self.assertEqual([], missing,
                             "the ladder is RELEASED but these payloads do not exist: %s. The "
                             "release gate must not be the only thing between an empty payload "
                             "and a submission." % missing)
        else:
            self.assertTrue(True)

    def test_the_payload_now_exists(self):
        """🟢 It did not, and the invariant above was the only thing standing between an empty
        payload and a submission. Closed."""
        self.assertTrue(os.path.exists(os.path.join(context.PKG_ROOT, "payload",
                                                    "SP_LADDER.sh")))

    def test_the_payload_refuses_to_invent_a_path(self):
        """🔴 The ladder CONSUMES a path; it must never generate one. Generating here would
        duplicate `gfn2_scan` and let a path that never passed the G-SCAN gate through."""
        with open(os.path.join(context.PKG_ROOT, "payload", "SP_LADDER.sh"),
                  errors="replace") as fh:
            src = fh.read()
        self.assertIn("does not invent one", src)
        self.assertIn("DOES NOT GENERATE THE PATH", src)

    def test_the_payload_smokes_before_production(self):
        with open(os.path.join(context.PKG_ROOT, "payload", "SP_LADDER.sh"),
                  errors="replace") as fh:
            src = fh.read()
        self.assertLess(src.index("sei_qc_smoke"), src.index("sei_qc_input"))

    def test_the_missing_payload_is_recorded_as_a_known_gap(self):
        """🔴 Today `payload/SP_LADDER.sh` does not exist. Recorded here as DATA so it cannot
        be mistaken for an oversight, and so the release precondition above has a stated
        reason to exist rather than looking like defensive boilerplate."""
        missing = [i.payload for i in plan.sp_ladder_items()
                   if not os.path.exists(os.path.join(context.PKG_ROOT, i.payload))]
        self.assertEqual([], missing,
                         "🟢 this gap is CLOSED -- SP_LADDER.sh now exists. If it reappears, "
                         "the release invariant above is the live guard.")


class TestReleaseGate(unittest.TestCase):
    """🔒 Same S-2 pattern as `u56_2`: built and tested every round, joined only when the flag
    says so, and the code never sets the flag."""

    def test_the_ladder_is_not_in_the_plan_by_default(self):
        self.assertFalse(plan.sp_ladder_released())
        self.assertFalse([i for i in plan.default_items()
                          if i.key.startswith("sp_ladder")])

    def test_the_items_are_still_built_and_therefore_still_tested(self):
        self.assertEqual(3, len(plan.sp_ladder_items()))

    def test_no_code_path_sets_the_release_flag(self):
        """The flag is lead/user's to set. A code path that raises it would make the gate
        decorative -- the same check `u56_2`'s gate carries."""
        src_dir = os.path.join(context.PKG_ROOT, "sei_pilot")
        for dirpath, _dirs, files in os.walk(src_dir):
            for fn in files:
                if not fn.endswith(".py"):
                    continue
                with open(os.path.join(dirpath, fn), errors="replace") as fh:
                    text = fh.read()
                self.assertNotIn('"released": True', text, fn)
                self.assertNotIn("'released': True", text, fn)

    def test_the_config_records_why_the_cost_is_an_estimate(self):
        cfg = config.load("b0_reactions.json", {})
        sp = cfg["sp_ladder"]
        self.assertIs(False, sp["released"])
        self.assertIn("ESTIMATE", sp["_cost_status"])
        self.assertIn("never sets it", sp["_released_note"])


class TestReplanTrigger(unittest.TestCase):
    """🔴 [R39.28] The trigger fires BEFORE the remaining rungs are submitted. Without it a 5x
    cost error ends n=3/n=4 in silent budget exhaustion -- ~749 core-h for nothing, plus a
    round trip. 3x is derived (half the distance to the nearer cliff: n=4 breaches at 5.9x,
    n=3 at 13.5x), not chosen."""

    def test_inside_the_window_does_not_replan(self):
        self.assertFalse(plan.sp_ladder_replan_required(1.5, 1.0)["replan_required"])
        self.assertFalse(plan.sp_ladder_replan_required(1.0, 2.9)["replan_required"])

    def test_at_or_over_the_trigger_replans(self):
        self.assertTrue(plan.sp_ladder_replan_required(3.0, 1.0)["replan_required"])
        self.assertTrue(plan.sp_ladder_replan_required(6.0, 1.0)["replan_required"])

    def test_it_is_symmetric_in_direction(self):
        """🔴 A cost far BELOW the estimate is also a reason to re-plan: the estimate is then
        wrong in a way that need not stay conservative at the next rung up. An asymmetric
        trigger would only catch the expensive half of being wrong."""
        self.assertTrue(plan.sp_ladder_replan_required(1.0, 5.0)["replan_required"])
        self.assertAlmostEqual(5.0, plan.sp_ladder_replan_required(1.0, 5.0)["ratio"])

    def test_a_missing_measurement_forces_a_replan_rather_than_passing(self):
        """Rule 18: unknown is not permission. The first rung exists to supply this number, so
        its absence is the one thing that must not read as "within tolerance"."""
        for measured, estimated in ((None, 1.0), (1.0, None), (0.0, 1.0)):
            r = plan.sp_ladder_replan_required(measured, estimated)
            self.assertTrue(r["replan_required"], (measured, estimated))
            self.assertIn("not a passed check", r["reason"])

    def test_the_derivation_travels_with_the_verdict(self):
        r = plan.sp_ladder_replan_required(1.2, 1.0)
        self.assertIn("5.9x", r["_derivation"])
        self.assertEqual(3.0, r["trigger"])


if __name__ == "__main__":
    unittest.main()
