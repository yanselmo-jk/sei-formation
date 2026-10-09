"""P1 is PERMANENTLY EXCLUDED by user ruling — what actually enforces that, and what does not.

🔴 THE INCIDENT THIS FIXES: P1 was submitted to the cluster this round despite the exclusion.
C-8 refused it and only ~0.658 core-h burned instead of 527.8 (the earlier '0.0103' quoted
here was wall-hours mislabeled as core-h, corrected 2026-08-21) — but the item reached the
cluster at all because the exclusion lived in PROSE (docs, comments) while nothing in the
plan-building code enforced it. Same shape as three other defects this round: the rule and its
enforcement in different places.

🔒 AND THE FIX IS NOT "REMOVE P1". `P1b` — the round's largest item at 5,328 core-h — carries
`depends_on=["P1"]`, and the missing-dependency check drops any item whose dependency is absent.
Deleting P1 would silently drop P1b, which is worse and invisible: the round just comes back
smaller. So these tests fix BOTH halves — P1 stays, and the thing that really stops it stays.

🔴🔴 [coder13, 2026-08-21] `endpoint_prep_product`'s ABSENCE stopped being the guard the moment
`u56_2.released` flipped true (lead/user, explicit, ADR-109 ruling 2 — R-A's own product
certification, NOT a P1 revival; plan.py's own comment at the Item makes this explicit). The
item is now LEGITIMATELY present in the plan. This is not the incident this file was written
against repeating -- that incident was an item reaching the plan/cluster with NOBODY intending
it. This is a deliberate, user-approved re-introduction via a different, reviewed path.
**The real guard was never the item's absence -- it was always that P1.sh never reads any
endpoint_prep_* job's output** (hardcoded `{"source": ...}` dicts, no `optimised`/`converged`/
`n_imag`/`level`, with that wiring EXPLICITLY deferred to a future round pending methodology
confirmation -- see `payload/P1.sh`'s own comment). That fact is unchanged by U56-2's release,
since P1.sh and U56-2's payload are different files with no data path between them. Confirmed by
grep: `endpoint_prep_product`/`endpoint_prep_reactant` appear NOWHERE in `payload/P1.sh` or
`criteria/p1.py`. Tests below now pin THAT property directly (source-level, not plan-membership),
which is the one that actually holds regardless of what else legitimately joins the plan.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import guards, plan

PKG = context.PKG_ROOT


def _plan_keys():
    return [i.key for i in plan.default_items()]


class TestTheRealGuardIsP1NeverReadingAnEndpointCertificate(unittest.TestCase):
    """🔴 What stops P1 is not its budget and not a comment: P1 is a QST2 (double-ended)
    search, so C-8 requires BOTH endpoints certified. `endpoint_prep_product`/`_reactant` now
    legitimately exist in the plan (U56-2, ADR-109 ruling 2) -- **the guard was never their
    absence, it is that P1.sh is hardcoded to never read either job's output**, deliberately
    (see the payload's own comment: real endpoint consumption is future work, pending a
    methodology ruling). That is what must hold regardless of what else the plan carries."""

    def test_p1_payload_never_reads_an_endpoint_prep_job_output(self):
        for fn in ("payload/P1.sh", "sei_pilot/criteria/p1.py"):
            text = open(os.path.join(PKG, fn), errors="replace").read()
            self.assertNotIn("endpoint_prep_product", text,
                             "%s references endpoint_prep_product's output -- P1's C-8 call "
                             "would then have a real product certificate to pass on, "
                             "re-arming P1 (permanently excluded by user ruling)" % fn)
            self.assertNotIn("endpoint_prep_reactant", text,
                             "%s references endpoint_prep_reactant's output -- same re-arming "
                             "risk on the reactant side" % fn)

    def test_p1s_own_c8_precondition_uses_unknown_fields_not_a_real_certificate(self):
        """The heredoc that calls C-8 for P1 must build `reactant`/`product` from ONLY the raw
        xyz source path, never from a parsed endpoint_prep result -- asserted against the
        actual payload text, not assumed from the comment describing it."""
        text = open(os.path.join(PKG, "payload", "P1.sh"), errors="replace").read()
        self.assertIn('reactant = {"source": r_path}', text)
        self.assertIn('product = {"source": p_path}', text)

    def test_c8_never_passes_on_a_missing_product(self):
        """`ts_precondition` is never True on missing information — the property the guard
        rests on, asserted rather than assumed."""
        good = {"optimised": True, "converged": True, "n_imag": 0, "level": "level2"}
        self.assertFalse(guards.ts_precondition(good, {})["may_start"])
        self.assertFalse(guards.ts_precondition(good, None)["may_start"])

    def test_the_refusal_is_reported_not_silent(self):
        decision = guards.ts_precondition({}, {})
        self.assertTrue(decision["warnings"])
        self.assertTrue(decision["blocking_reasons"])


class TestP1StaysInThePlanButSizedForARefusal(unittest.TestCase):
    def test_p1_and_p1b_are_both_still_planned(self):
        """🔴 The dependency is the reason P1 is not simply deleted. If this ever fails,
        check whether P1b vanished with it."""
        keys = _plan_keys()
        self.assertIn("P1", keys)
        self.assertIn("P1b", keys)

    def test_p1b_still_declares_its_dependency_on_p1(self):
        p1b = [i for i in plan.default_items() if i.key == "P1b"][0]
        self.assertIn("P1", p1b.depends_on or [],
                      "if this dependency is ever removed, P1 no longer needs to exist and "
                      "should be reconsidered rather than left sized for nothing")

    def test_p1_is_sized_for_the_refusal_not_for_the_run(self):
        """It reserved ~9,216 core-h of ceiling (64 x 48 x 3 links) against a guard, for
        something that structurally cannot spend more than a few core-h."""
        p1 = [i for i in plan.default_items() if i.key == "P1"][0]
        self.assertEqual(64.0, p1.core_hours_budget)
        self.assertEqual(1.0, p1.min_wall_h)
        self.assertLess(p1.core_hours_budget, plan.P1_TOTAL_CORE_HOURS / 50.0)

    def test_the_budget_is_generous_against_the_measured_refusal_cost(self):
        """⚠ The margin IS the safety property. Measured this round: refused 3x, 0.658 core-h
        total (37 s x 64 cores). [coder13, 2026-08-21] The earlier '0.0103' figure here was
        WALL-HOURS mislabeled as core-h (same defect 05_STATE.md records for the plan.py
        rationale string, fixed alongside this) -- true margin is 64/0.658 = 97x, not the
        ~6,200x the old figure implied; the resize decision itself is unchanged, still generous
        (engineer8's approved range was 10-50x). If C-8 ever fails to fire, a small budget
        makes the resulting run short and cheap instead of a 48-hour whole-node burn — so this
        must not be tightened toward the measured cost."""
        measured_refusal_core_h = 0.658
        self.assertGreater(plan.P1_EXCLUDED_REFUSAL_CORE_H, measured_refusal_core_h * 50)

    def test_the_exclusion_is_stated_where_a_reader_meets_the_item(self):
        """The prose-only exclusion is what let it reach the cluster. It now travels on the
        Item itself, which is what a planner and a reviewer actually read."""
        p1 = [i for i in plan.default_items() if i.key == "P1"][0]
        self.assertIn("PERMANENTLY EXCLUDED", p1.title)
        self.assertIn("PERMANENTLY EXCLUDED", p1.rationale)
        self.assertIn("P1b", p1.rationale)


if __name__ == "__main__":
    unittest.main()
