"""[critic10 / proposer7] Name the stages that RAN, instead of a boolean about one of them.

🔴 THE DEFECT: P5's `converged` is `normal_termination AND opt.converged`, and
`normal_termination` is a bare string-presence check. In an `opt freq` job the string appears
once the OPT half finishes — so `converged` read **true on species whose freq stage had
crashed**. Every frequency job in the round died on the `EpsInf=0.0000` sentinel (§39.73), and
`converged` reported success for them.

🔒 WHY NOT JUST RENAME IT `converged_opt`: that fixes today's confusion and reproduces the same
failure the next time someone adds a third stage and forgets what the boolean covers. Naming the
stages makes a missing one unmissable whatever any boolean is called, and generalises without
another rename. (proposer7's reasoning, relayed by critic10 — adopted as given.)
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot.criteria import g16

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures",
                       "g16_p5_opt_ok_freq_crashed.log")


def _real_defect_log():
    with open(FIXTURE, errors="replace") as fh:
        return fh.read()


class TestTheRealDefectLog(unittest.TestCase):
    """Every assertion here is against verbatim lines from a species that actually ran."""

    def test_the_log_looks_successful_by_the_old_test(self):
        """🔴 This is the trap, stated first: the two things `converged` was built from are
        BOTH true on a log with no frequencies at all."""
        text = _real_defect_log()
        summary = g16.summarize(text)
        self.assertTrue(summary["normal_termination"])
        self.assertTrue((summary["opt"] or {}).get("converged"))

    def test_but_the_frequency_stage_left_nothing(self):
        self.assertEqual(0, _real_defect_log().count("Frequencies --"))

    def test_stages_completed_makes_the_gap_unmissable(self):
        r = g16.stages_completed(_real_defect_log(), route="#p opt freq")
        self.assertIn("opt", r["completed"])
        self.assertIn("scf", r["completed"])
        self.assertNotIn("freq", r["completed"])
        self.assertIn("freq", r["missing"])

    def test_the_cause_is_visible_in_the_same_log(self):
        """🔒 G16 says `IEInf=0` — equilibrium solvation, which should not consult EpsInf at
        all — right next to the EpsInf=0.0000 it then crashed on. That is why §39.73 expects
        the bracket to come back invariant and the whole thing to be plumbing, not physics."""
        text = _real_defect_log()
        self.assertIn("IEInf=0", text)
        self.assertIn("EpsInf=   0.0000", text)


class TestWhatEachFieldDoesAndDoesNotEstablish(unittest.TestCase):
    """🔴 The standing rule this came from: for every field we READ, say what it does and does
    not establish. `rc` has now lied in both directions on this cluster; so has
    `normal_termination`."""

    def test_completion_comes_from_output_evidence_never_from_the_route(self):
        """A route asking for freq establishes nothing about whether freq ran."""
        r = g16.stages_completed(" SCF Done: ...\n", route="#p opt freq")
        self.assertEqual(["freq", "opt", "thermo"], r["requested"])
        self.assertEqual(["opt"], sorted(set(r["missing"]) & {"opt"}))
        self.assertNotIn("freq", r["completed"])

    def test_a_complete_job_has_nothing_missing(self):
        """0-o.4 rule 4: the check must be satisfiable, or it is not a check."""
        text = (" SCF Done: x\n Optimization completed.\n Frequencies --  100.0\n"
                " Thermochemistry\n")
        r = g16.stages_completed(text, route="#p opt freq")
        self.assertEqual([], r["missing"])
        for stage in ("scf", "opt", "freq", "thermo"):
            self.assertIn(stage, r["completed"])

    def test_an_unrequested_stage_that_ran_is_not_missing(self):
        r = g16.stages_completed(" SCF Done: x\n Optimization completed.\n", route="#p opt")
        self.assertEqual([], r["missing"])
        self.assertNotIn("freq", r["requested"])

    def test_the_standing_check_is_written_down_where_the_misleading_fields_live(self):
        """🔒 The rule lives beside the parsers it constrains, not only in a document —
        the same reason the docparse convention failed when it lived only in prose."""
        import inspect
        doc = inspect.getdoc(g16) or ""
        for token in ("STANDING CHECK", "rc == 0", "normal_termination",
                      "OUTPUT EVIDENCE"):
            self.assertIn(token, doc, token)

    def test_the_record_says_what_it_is_read_from(self):
        r = g16.stages_completed(" SCF Done: x\n", route="#p opt")
        self.assertIn("never from the route or from an exit code", r["_note"])


if __name__ == "__main__":
    unittest.main()
