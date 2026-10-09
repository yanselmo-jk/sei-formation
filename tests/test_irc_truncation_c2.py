"""[C-2.1 / C-2.2, 39.53] A truncated IRC certifies nothing, and `indeterminate` carries a cause.

Two constraints are fixed here, both found on the DELIVERED P1 data:

  C-2.1  the IRC's termination reason is emitted as DATA. G16 prints it itself; nobody read it.
  C-2.2  a run that stopped on its STEP BUDGET (or was cut by a wall/budget cap) is
         `indeterminate`, never `pass`. C-2 exists to certify "this transition state connects
         two distinct minima"; a path that reached no minimum cannot certify that, however
         tidily it terminated.

The regression, verbatim from the returned tree: BOTH directions printed
`Maximum number of steps reached.` AND `Normal termination of Gaussian 16`, ran 31 points and
descended 0.143 / 0.147 eV -- passing every clause C-2 had at the time. The energy was still
falling at a steady rate at the last point, so the path ran out of budget rather than arriving
anywhere.

And the second, separable point: that outcome is a BUDGET-class `indeterminate`. Pooling it with
CHEMICAL-class ones drags the measured success rate `p` down for reasons that are our own
purchasing decisions, inflates `1/p` (the wave-1 sizing multiplier), and makes S3 read as more
expensive than it is -- whereupon the natural response, tightening caps, makes it worse.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import guards
from sei_pilot.criteria import g16

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def _log(direction):
    with open(os.path.join(FIXTURES, "g16_irc_%s_maxpoints_p1.log" % direction),
              errors="replace") as fh:
        return fh.read()


class TestTerminationReasonIsRead(unittest.TestCase):
    def test_the_real_p1_irc_stopped_on_its_step_budget_in_both_directions(self):
        for d in ("forward", "reverse"):
            c = g16.parse_irc_completion(_log(d))
            self.assertEqual("maxpoints", c["termination_reason"], d)
            self.assertTrue(c["truncated"], d)
            self.assertFalse(c["minimum_found"], d)

    def test_normal_termination_is_true_at_the_same_time(self):
        """🔴 THE TRAP: `Normal termination` and `Maximum number of steps reached` are BOTH
        printed. Reading only the first is what let a path that connected nothing through."""
        for d in ("forward", "reverse"):
            c = g16.parse_irc_completion(_log(d))
            self.assertTrue(c["normal_termination"], d)
            self.assertTrue(c["path_calculation_complete"], d)

    def test_path_calculation_complete_is_not_evidence_of_a_minimum(self):
        c = g16.parse_irc_completion(_log("forward"))
        self.assertTrue(c["path_calculation_complete"])
        self.assertFalse(c["minimum_found"])
        self.assertIn("not evidence", c["_note"])

    def test_real_early_minimum_is_recognised_not_misread_as_no_marker(self):
        """🔴 [linear-hopping-frog, Track A item 3] The real, returned `U56_RB_scan` IRC logs
        (both directions) print `Normal termination`, hit neither `maxpoints` nor a wall/budget
        cut, and G16 itself says it found a minimum after just 1 point -- but in words this
        parser did not recognise (`PES minimum detected on this side of the pathway.`, not the
        `Minimum found on this side of the path` this module had assumed and never verified
        against a real log). Before the fix this real, genuine minimum silently read as
        `termination_reason: "normal_termination_without_a_minimum_marker"` -- indistinguishable
        from an unexplained early stop. `truncated` was ALREADY correct (`False`) either way;
        only `minimum_found`/`termination_reason` were the false negative."""
        with open(os.path.join(FIXTURES, "g16_irc_forward_minimum_u56rb.log"),
                  errors="replace") as fh:
            text = fh.read()
        c = g16.parse_irc_completion(text)
        self.assertTrue(c["normal_termination"])
        self.assertFalse(c["maxpoints_reached"])
        self.assertTrue(c["minimum_found"])
        self.assertEqual(c["termination_reason"], "minimum_found")
        self.assertFalse(c["truncated"])

    def test_a_wall_or_budget_kill_leaves_no_marker_and_still_counts_as_truncated(self):
        """A killed job simply stops. No G16 marker, no `Normal termination` -- and it is
        truncation just the same."""
        c = g16.parse_irc_completion(" IRC point 12 ... \n Energy= -350.1\n")
        self.assertTrue(c["truncated"])
        self.assertFalse(c["maxpoints_reached"])
        self.assertIn("no_marker", c["termination_reason"])

    def test_real_error_termination_is_not_mislabeled_no_marker(self):
        """🔴 [critic14] The REAL `U56_RA_scan`/`U56_RA_qst2` IRC logs die mid corrector
        integration (`Maximum number of corrector steps exceded.`) with an explicit G16
        `Error termination via Lnk1e in .../l123.exe` marker -- wall used was 1.8-5.3 h against
        a 48 h cap, so this is NOT a wall/budget kill. Before the fix, `normal is not True`
        alone produced the generic "no_marker (... wall-clock or budget kill ...)" text on this
        exact real log, describing a genuine engine death as an unexplained silent stop."""
        with open(os.path.join(FIXTURES, "g16_irc_forward_error_termination_u56ra.log"),
                  errors="replace") as fh:
            text = fh.read()
        c = g16.parse_irc_completion(text)
        self.assertFalse(c["normal_termination"])
        self.assertFalse(c["maxpoints_reached"])
        self.assertTrue(c["truncated"])
        self.assertIn("error_termination", c["termination_reason"])
        self.assertNotIn("no_marker", c["termination_reason"])
        self.assertTrue(c["error_terminated"])

    def test_summarize_only_carries_the_record_for_a_log_that_is_an_irc(self):
        """Rule 18: unknown is not permission. A non-IRC log leaves the field None, and C-2
        then says it could not measure the ending rather than assuming a minimum."""
        self.assertIsNotNone(g16.summarize(_log("forward"))["irc_completion"])
        self.assertIsNone(g16.summarize(" Normal termination of Gaussian 16 \n")
                          ["irc_completion"])


class TestC2RefusesTheTruncatedPath(unittest.TestCase):
    E_TS = -350.000000

    def _direction(self, text, descent_hartree=0.02):
        return {"normal_termination": True, "n_points": 31,
                "energy_hartree": self.E_TS - descent_hartree,
                "completion": g16.parse_irc_completion(text)}

    def test_the_delivered_p1_irc_would_now_be_indeterminate(self):
        """The honest price of the clause, stated as a test rather than as prose."""
        v = guards.irc_verdict(self._direction(_log("forward")),
                               self._direction(_log("reverse")), self.E_TS)
        self.assertEqual("indeterminate", v["status"])
        self.assertFalse(v["may_render_chemical_verdict"])
        self.assertTrue(any("TRUNCATED" in f for f in v["forward_failures"]), v)

    def test_it_is_classified_as_a_budget_cause_not_a_chemical_one(self):
        v = guards.irc_verdict(self._direction(_log("forward")),
                               self._direction(_log("reverse")), self.E_TS)
        self.assertEqual("budget", v["cause_class"])

    def test_a_missing_completion_record_is_unknown_not_a_silent_pass(self):
        bare = {"normal_termination": True, "n_points": 31,
                "energy_hartree": self.E_TS - 0.02}
        v = guards.irc_verdict(bare, bare, self.E_TS)
        self.assertEqual("indeterminate", v["status"])
        self.assertEqual("unknown", v["cause_class"])

    def test_a_converged_path_still_passes(self):
        """The clause must not make C-2 unsatisfiable -- 0-o.4's rule 4."""
        done = {"normal_termination": True, "n_points": 31,
                "energy_hartree": self.E_TS - 0.02,
                "completion": {"truncated": False, "minimum_found": True,
                               "termination_reason": "minimum_found"}}
        v = guards.irc_verdict(done, done, self.E_TS)
        self.assertEqual("ok", v["status"])
        self.assertIsNone(v["cause_class"])
        self.assertTrue(v["may_render_chemical_verdict"])


class TestCondition7BranchB(unittest.TestCase):
    """[39.32(g) condition 7, final form in 39.55(d)] The connection may be established by
    EITHER (a) convergence in both directions, or (b) `maxpoints` + B+ agreement in both.

    🔴 An earlier amendment (39.53) said "must terminate on convergence" full stop. That would
    have forbidden B+ outright and forced Option A on every gate attempt -- which would have
    taken a 21-atom attempt out of submittability and killed the matched pair that buys
    Delta_shell. These tests exist so that wording cannot come back by accident.

    ⚠ B+ itself (two terminal optimisations per direction) is NOT built yet. What is fixed here
    is that C-2 ACCEPTS branch (b) when the agreement record is present, and still refuses a
    truncated path when it is absent -- i.e. today's behaviour is "the arm does not run", not
    "the gate quietly passes".
    """

    E_TS = -350.000000

    def _direction(self, agreement=None):
        d = {"normal_termination": True, "n_points": 31,
             "energy_hartree": self.E_TS - 0.02,
             "completion": {"truncated": True, "minimum_found": False,
                            "termination_reason": "maxpoints"}}
        if agreement is not None:
            d["bplus"] = {"agreement": agreement}
        return d

    def test_maxpoints_plus_bplus_agreement_establishes_the_connection(self):
        v = guards.irc_verdict(self._direction(True), self._direction(True), self.E_TS)
        self.assertEqual("ok", v["status"], v)
        self.assertIn("b: maxpoints", v["forward"]["connection_established_via"])

    def test_bplus_disagreement_is_a_bifurcation_and_stays_indeterminate(self):
        v = guards.irc_verdict(self._direction(False), self._direction(True), self.E_TS)
        self.assertEqual("indeterminate", v["status"])
        self.assertTrue(any("B+ DISAGREED" in f for f in v["forward_failures"]), v)

    def test_a_bplus_disagreement_is_CHEMICAL_not_budget(self):
        """🔴 [critic10] THE BUG THIS PINS: the class was string-mined from the failure
        message, and every truncated-path message begins "IRC was TRUNCATED (...)" whether the
        tail says "B+ DISAGREED" or "B+ was not run" -- so a real bifurcation was bucketed as
        BUDGET. That drops it out of the 1/p CHEMICAL denominator and prescribes "the caps are
        too tight, spend more" for a broken method: the opposite response.
        🔒 The class is now derived from STRUCTURED tags the clauses emit, never from the prose
        the same function built one line earlier. The previous test asserted only `status`,
        which is exactly how this shipped unnoticed."""
        v = guards.irc_verdict(self._direction(False), self._direction(True), self.E_TS)
        self.assertEqual("chemical", v["cause_class"])

    def test_classification_does_not_depend_on_message_wording(self):
        """Reword the prose and the class must not move -- it is read off the tags."""
        v = guards.irc_verdict(self._direction(False), self._direction(True), self.E_TS)
        self.assertIn("chemical", v["forward"]["cause_tags"])
        self.assertIn("budget", guards.irc_verdict(
            self._direction(), self._direction(), self.E_TS)["forward"]["cause_tags"])

    def test_maxpoints_without_bplus_is_still_refused(self):
        v = guards.irc_verdict(self._direction(), self._direction(), self.E_TS)
        self.assertEqual("indeterminate", v["status"])
        self.assertTrue(any("B+ was not run" in f for f in v["forward_failures"]), v)

    def test_branch_a_is_labelled_too(self):
        d = {"normal_termination": True, "n_points": 31,
             "energy_hartree": self.E_TS - 0.02,
             "completion": {"truncated": False, "minimum_found": True,
                            "termination_reason": "minimum_found"}}
        v = guards.irc_verdict(d, d, self.E_TS)
        self.assertIn("a: both directions converged",
                      v["forward"]["connection_established_via"])


class TestBranchBArcLengthSeparationGate(unittest.TestCase):
    """[§39.114(1), proposer10] Branch (b) must not trust a bare B+ `agreement: True` when the
    IRC never got far from the saddle. Real numbers from `U56_RA_scan` (both real arms, per
    02_METHOD_SPEC.md §39.114(1)'s own re-derivation from the raw logs): forward reached ~20-21
    points (arc 6.83, B+ start points 3.41 apart) -- "clearly enough"; reverse reached ~5-6
    points (arc 1.71, B+ start points only 1.02 apart) -- "clearly not". `guards.py` never sees
    the arc length directly, only `n_points` -- which is exactly what `BPLUS_LOW_CONFIDENCE_
    MIN_POINTS` is defined against (§39.114(1)'s own convention note)."""

    E_TS = -350.000000

    def _direction(self, n_points, agreement=True):
        return {"normal_termination": True, "n_points": n_points,
                "energy_hartree": self.E_TS - 0.02,
                "completion": {"truncated": True, "minimum_found": False,
                              "termination_reason": "maxpoints"},
                "bplus": {"agreement": agreement}}

    def test_the_well_separated_real_forward_arm_stays_true(self):
        """RA_scan forward: 20 points (parse_irc_path_frames convention, saddle excluded)."""
        d = self._direction(20)
        detail = guards.irc_direction_ok(d, self.E_TS)[2]
        self.assertIs(detail["bplus_agreement_effective"], True)
        self.assertIn("b: maxpoints", detail["connection_established_via"])

    def test_the_close_together_real_reverse_arm_downgrades(self):
        """RA_scan reverse: 5 points (parse_irc_path_frames convention, saddle excluded)."""
        d = self._direction(5)
        ok, fails, detail = guards.irc_direction_ok(d, self.E_TS)
        self.assertEqual("low_confidence", detail["bplus_agreement_effective"])
        self.assertNotIn("connection_established_via", detail)
        self.assertFalse(ok)
        self.assertIn("unknown", detail["cause_tags"])
        self.assertTrue(any("too close to the saddle" in f for f in fails), fails)

    def test_low_confidence_is_not_disagreement_and_not_budget(self):
        """This is a THIRD outcome -- not chemical (no disagreement measured), not budget
        (the existing n_points<5 floor is a separate, harder requirement)."""
        d = self._direction(5)
        detail = guards.irc_direction_ok(d, self.E_TS)[2]
        self.assertNotIn("chemical", detail["cause_tags"])
        self.assertNotIn("budget", detail["cause_tags"])

    def test_raw_bplus_record_is_never_mutated(self):
        """[critic14] compute-and-record vs. consult stay separate acts -- a caller reading the
        raw `bplus` dict must still see the true measurement, never the downgraded one."""
        d = self._direction(5)
        guards.irc_direction_ok(d, self.E_TS)
        self.assertIs(d["bplus"]["agreement"], True)

    def test_agreement_false_or_missing_is_unaffected_by_the_point_count(self):
        """The gate only ever downgrades a True -- it must not invent a new False or None."""
        for n in (3, 20):
            d = self._direction(n, agreement=False)
            self.assertIs(guards.irc_direction_ok(d, self.E_TS)[2]["bplus_agreement_effective"],
                          False)
            d = self._direction(n, agreement=None)
            self.assertIsNone(
                guards.irc_direction_ok(d, self.E_TS)[2]["bplus_agreement_effective"])


class TestCrashedIrcTagsEngineNotUnknown(unittest.TestCase):
    """[critic14/lead ruling 2026-08-21] `engine` (§39.69: numerical failure at a legitimately
    requested geometry -- change the SCF/numerics, not the caps or the method) never appeared
    in the U-56b tally because a crashed IRC and a genuine unmeasured case both tagged
    `unknown`. `criteria.g16.parse_irc_completion`'s `error_terminated` field (computed from
    real log content, never from `termination_reason`'s prose) now distinguishes them."""

    E_TS = -350.000000

    def test_a_real_error_terminated_log_tags_engine(self):
        with open(os.path.join(FIXTURES, "g16_irc_forward_error_termination_u56ra.log"),
                  errors="replace") as fh:
            completion = g16.parse_irc_completion(fh.read())
        self.assertTrue(completion["error_terminated"])
        # energy_hartree supplied so the (unrelated) "energy missing" clause does not also
        # fire "unknown" for a different reason and confound this specific assertion.
        d = {"normal_termination": False, "n_points": 20,
            "energy_hartree": self.E_TS - 0.02, "completion": completion}
        ok, fails, detail = guards.irc_direction_ok(d, self.E_TS)
        self.assertFalse(ok)
        self.assertIn("engine", detail["cause_tags"])
        self.assertNotIn("unknown", detail["cause_tags"])

    def test_a_genuinely_unmeasured_case_still_tags_unknown(self):
        """A wall/budget kill (no G16 marker at all) is NOT an engine failure -- must not be
        swept into the new class just because it also has `normal_termination is not True`."""
        completion = g16.parse_irc_completion(" IRC point 12 ... \n Energy= -350.1\n")
        self.assertFalse(completion["error_terminated"])
        # [critic14] energy_hartree supplied so the UNRELATED "energy missing" clause cannot
        # also append "unknown" on its own -- without this, assertIn("unknown", ...) would
        # hold regardless of what the first (normal_termination) clause did.
        d = {"normal_termination": False, "n_points": 3,
            "energy_hartree": self.E_TS - 0.02, "completion": completion}
        detail = guards.irc_direction_ok(d, self.E_TS)[2]
        self.assertIn("unknown", detail["cause_tags"])
        self.assertNotIn("engine", detail["cause_tags"])


class TestAGenuineShortMinimumIsProtocolNotBudgetOrChemical(unittest.TestCase):
    """[§39.116(d), proposer10 RULING] `U56_RB_scan`'s real IRC: 1 point, 289 s, G16's own `PES
    minimum detected on this side of the pathway.` -- but proposer10 read the ACTUAL geometry
    and found the "minimum" is the SADDLE to within ~0.02 Å (max pairwise interatomic distance
    change 0.0203 A forward / 0.0228 A reverse, critic14's independent rotation-invariant
    measurement) -- the IRC's own stopping criterion fired trivially on a flat coordinate, not
    evidence of a real distinct basin. `n_points < IRC_MIN_POINTS` alone used to tag this
    `budget` (backwards for a self-declared-complete run); an EARLIER version of this fix (now
    superseded, per critic14's own correction of their own first suggestion) tagged it
    `chemical` instead, which is ALSO wrong -- `chemical` asserts a chemical fact was measured,
    and none was. Ruled OUT of BOTH sides of the 1/p denominator; tag is `protocol` (§39.68(3):
    the run says something about OUR PROCEDURE -- the IRC stopping criterion -- not the
    chemistry or the caps)."""

    E_TS = -350.000000

    def test_real_rb_scan_short_minimum_tags_protocol_not_budget_or_chemical(self):
        with open(os.path.join(FIXTURES, "g16_irc_forward_minimum_u56rb.log"),
                  errors="replace") as fh:
            completion = g16.parse_irc_completion(fh.read())
        self.assertTrue(completion["minimum_found"])
        d = {"normal_termination": True, "n_points": 1,
            "energy_hartree": self.E_TS - 0.02, "completion": completion}
        ok, fails, detail = guards.irc_direction_ok(d, self.E_TS)
        self.assertFalse(ok)   # still fails IRC_MIN_POINTS -- that requirement is unchanged
        self.assertIn("protocol", detail["cause_tags"])
        self.assertNotIn("budget", detail["cause_tags"])
        self.assertNotIn("chemical", detail["cause_tags"])

    def test_the_aggregate_verdict_class_is_exactly_protocol_not_mixed(self):
        """[critic14's trap] `_class_from_tags` returns `mixed` the instant a SECOND distinct
        tag is present for either direction -- a test that only checks `assertIn("protocol", ..)`
        cannot see that. Feed the real shape through the PUBLIC `irc_verdict` path (both
        directions, same real pattern) and assert the aggregate class itself."""
        with open(os.path.join(FIXTURES, "g16_irc_forward_minimum_u56rb.log"),
                  errors="replace") as fh:
            completion = g16.parse_irc_completion(fh.read())
        d = {"normal_termination": True, "n_points": 1,
            "energy_hartree": self.E_TS - 0.02, "completion": completion}
        v = guards.irc_verdict(d, d, self.E_TS)
        self.assertEqual("protocol", v["cause_class"], v)

    def test_a_short_path_with_no_minimum_still_tags_budget(self):
        """The fix is conditioned on `minimum_found`, not on `n_points` alone -- a short path
        that did NOT reach a minimum is still a real budget/truncation concern."""
        completion = {"truncated": True, "minimum_found": False,
                     "termination_reason": "maxpoints", "error_terminated": False}
        d = {"normal_termination": True, "n_points": 2,
            "energy_hartree": self.E_TS - 0.02, "completion": completion}
        detail = guards.irc_direction_ok(d, self.E_TS)[2]
        self.assertIn("budget", detail["cause_tags"])
        self.assertNotIn("chemical", detail["cause_tags"])
        self.assertNotIn("protocol", detail["cause_tags"])


class TestBPlusIsRecordedEvenWhereItIsNotConsulted(unittest.TestCase):
    """🔴 [§39.77] B+ is ALWAYS computed and ALWAYS recorded; whether it is CONSULTED depends
    on the branch. Compute-and-record and consult are different acts, and fusing them is the
    same defect C-10.1 separated for cost probes and §39.62 separated for Ω.

    🔴 WHY IT MATTERS, and it is not tidiness: a converged IRC is **the only place B+ can ever
    be checked** — there is ground truth. On a truncated IRC B+ is load-bearing and
    UNCHECKABLE. So keeping B+ verdicts only where they were consulted would leave our record
    of B+'s reliability conditioned on the cases with no ground truth: **we would only ever
    store verdicts we cannot check.** The success-conditioned denominator in its purest form.
    """

    E_TS = -350.0
    CONVERGED = {"truncated": False, "minimum_found": True,
                 "termination_reason": "minimum_found"}

    def _direction(self, agreement=None):
        d = {"normal_termination": True, "n_points": 31,
             "energy_hartree": self.E_TS - 0.02, "completion": self.CONVERGED}
        if agreement is not None:
            d["bplus"] = {"agreement": agreement}
        return d

    def test_a_refuted_bplus_does_not_change_a_converged_verdict(self):
        """🔴 DIRECTION OF AUTHORITY: the IRC wins. B+ never overrides a converged IRC — a
        disagreement impugns B+, because the IRC is the ground truth B+ is measured against.
        If this ever goes red, someone has wired the authority backwards."""
        v = guards.irc_verdict(self._direction(False), self._direction(True), self.E_TS)
        self.assertEqual("ok", v["status"])
        self.assertTrue(v["may_render_chemical_verdict"])

    def test_but_the_refutation_is_recorded(self):
        v = guards.irc_verdict(self._direction(False), self._direction(True), self.E_TS)
        cal = v["forward"]["bplus_calibration"]
        self.assertEqual("bplus_refuted", cal["outcome"])
        self.assertTrue(cal["checkable"])
        self.assertTrue(cal["irc_is_ground_truth"])

    def test_agreement_is_recorded_too_not_only_failures(self):
        """A record of only the disagreements would be its own conditioned denominator."""
        v = guards.irc_verdict(self._direction(True), self._direction(True), self.E_TS)
        self.assertEqual("bplus_confirmed", v["forward"]["bplus_calibration"]["outcome"])

    def test_a_missed_calibration_opportunity_is_visible(self):
        """B+ not running on a checkable case is different from a case that was never
        checkable, and the record must tell them apart."""
        v = guards.irc_verdict(self._direction(), self._direction(), self.E_TS)
        self.assertEqual("bplus_not_run", v["forward"]["bplus_calibration"]["outcome"])

    def test_a_truncated_direction_is_not_a_calibration_case(self):
        """No ground truth there — B+ is load-bearing and unchecked, which is the whole
        asymmetry."""
        trunc = {"normal_termination": True, "n_points": 31,
                 "energy_hartree": self.E_TS - 0.02,
                 "completion": {"truncated": True, "minimum_found": False,
                                "termination_reason": "maxpoints"},
                 "bplus": {"agreement": True}}
        v = guards.irc_verdict(trunc, trunc, self.E_TS)
        self.assertEqual("ok", v["status"])
        self.assertIsNone(v["forward"].get("bplus_calibration"))


class TestIndeterminateCauseClass(unittest.TestCase):
    """🔴 `1/p` may ONLY be computed over the CHEMICAL denominator. A large BUDGET class means
    the caps are wrong (an engineering fix); a large CHEMICAL class means the method is wrong
    (stop and fix it). Opposite responses -- so they must stay distinguishable."""

    def test_each_class(self):
        self.assertIsNone(guards.classify_indeterminate([]))
        self.assertEqual("budget", guards.classify_indeterminate(
            ["IRC was TRUNCATED (maxpoints)"]))
        self.assertEqual("chemical", guards.classify_indeterminate(
            ["the IRC connected the reactant to itself"]))
        self.assertEqual("unknown", guards.classify_indeterminate(
            ["no IRC completion record -- how the path ENDED was not measured"]))

    def test_mixed_is_kept_mixed_rather_than_forced_into_one_bucket(self):
        self.assertEqual("mixed", guards.classify_indeterminate(
            ["IRC was TRUNCATED (maxpoints)", "the IRC connected the reactant to itself"]))


if __name__ == "__main__":
    unittest.main()
