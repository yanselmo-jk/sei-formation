"""[39.45 / 39.47] The GFN2 relaxed-scan producer — the discontinuity gate's missing input.

🔴 This module's format knowledge was obtained BY EXECUTION (xtb 6.7.1, dev box), not from
memory: the package had no xtb constrained-scan machinery at all before this (`payload/P3.sh`
uses `--path`, a different tool). The fixtures are verbatim output of a real run, and their
PROVENANCE entry records the exact command.

🔒 Everything here is GFN2, in HARTREE, and is tagged as such so that `gscan2_decision` can
refuse to subtract it from a DFT energy (39.50(b)).
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import b0f_deck, gfn2_scan

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
SCAN_LOG = os.path.join(FIXTURES, "xtb_relaxed_scan_r_a.log")
SCAN_INP = os.path.join(FIXTURES, "xtb_relaxed_scan_r_a.inp")


class TestScanInputMatchesWhatActuallyRan(unittest.TestCase):
    def test_the_generated_block_matches_the_executed_one(self):
        """The fixture .inp is the block that produced the fixture .log with rc = 0. The
        generated block differs from it only in float formatting, and the generated form was
        itself executed (rc = 0, 12 points) before this test was written."""
        generated = gfn2_scan.scan_input((2, 3), 1.45, 2.65, 12)
        with open(SCAN_INP) as fh:
            executed = fh.read()
        norm = lambda t: [" ".join(l.replace(",", " ").split())
                          for l in t.strip().splitlines()]
        self.assertEqual(len(norm(executed)), len(norm(generated)))
        for a, b in zip(norm(executed), norm(generated)):
            if a.startswith("1:"):
                self.assertEqual([float(x) for x in a.split()[1:]],
                                 [float(x) for x in b.split()[1:]])
            else:
                self.assertEqual(a, b)

    def test_a_reverse_scan_is_a_legitimate_input(self):
        """🔴 G-SCAN-1 needs the SAME grid run backwards, so a descending range must NOT be
        rejected -- unlike the DFT deck, where a negative step is a different experiment."""
        block = gfn2_scan.scan_input((2, 3), 2.65, 1.45, 12)
        self.assertIn("2.6500, 1.4500", block)

    def test_degenerate_inputs_are_refused(self):
        self.assertRaises(ValueError, gfn2_scan.scan_input, (2, 2), 1.4, 2.6, 12)
        self.assertRaises(ValueError, gfn2_scan.scan_input, (0, 3), 1.4, 2.6, 12)
        self.assertRaises(ValueError, gfn2_scan.scan_input, (2, 3), 1.4, 2.6, 1)


class TestTrajectoryParser(unittest.TestCase):
    def setUp(self):
        self.p = gfn2_scan.read_log(SCAN_LOG)

    def test_every_point_is_read_with_its_energy_and_geometry(self):
        self.assertEqual(12, self.p["n_points"])
        self.assertEqual([], self.p["warnings"])
        self.assertEqual("gfn2", self.p["hamiltonian"])
        for pt in self.p["points"]:
            self.assertIsNotNone(pt["energy_hartree"])
            self.assertEqual(11, len(pt["geometry"]))

    def test_energies_are_hartree_from_the_comment_line(self):
        self.assertAlmostEqual(-20.935733838156,
                               self.p["points"][0]["energy_hartree"], places=9)
        self.assertAlmostEqual(-20.948012188295,
                               self.p["points"][-1]["energy_hartree"], places=9)

    def test_the_constrained_distance_tracks_the_requested_range(self):
        first = gfn2_scan.distance_ang(self.p["points"][0]["geometry"], 1, 2)
        last = gfn2_scan.distance_ang(self.p["points"][-1]["geometry"], 1, 2)
        self.assertAlmostEqual(1.45, first, places=1)
        self.assertAlmostEqual(2.65, last, places=1)

    def test_a_frame_with_an_unreadable_energy_keeps_its_place(self):
        """🔴 A profile silently missing its maximum is worse than one reporting a hole --
        the gate already treats a hole as unjudgeable and withholds funding."""
        text = ("2\n energy: -1.5 xtb: 6.7.1\nH 0 0 0\nH 0 0 1\n"
                "2\n no energy here\nH 0 0 0\nH 0 0 1.1\n")
        p = gfn2_scan.parse_scan_log(text)
        self.assertEqual(2, p["n_points"])
        self.assertIsNone(p["points"][1]["energy_hartree"])
        self.assertTrue(p["warnings"])

    def test_a_short_frame_does_not_swallow_the_NEXT_frame(self):
        """🔴 [critic10, reproduced] The advance step used the DECLARED atom count, so a frame
        that declared more atoms than it carried left the cursor inside the NEXT frame's body.
        That complete, well-formed frame was then skip-scanned and dropped ENTIRELY, with no
        warning naming the loss -- and this profile decides whether a real DFT attempt gets
        funded. A wall-clock kill or a partially flushed log produces exactly this shape."""
        text = ("3\n energy: -1.0 xtb: 6.7.1\nH 0 0 0\nH 0 0 1\n"      # declares 3, has 2
                "2\n energy: -2.0 xtb: 6.7.1\nH 0 0 0\nH 0 0 1\n")     # complete
        p = gfn2_scan.parse_scan_log(text)
        self.assertEqual(2, p["n_points"], "the second frame must survive")
        self.assertEqual([-1.0, -2.0],
                         [x["energy_hartree"] for x in p["points"]])
        self.assertTrue(any("declared 3 atoms but 2" in w for w in p["warnings"]))

    def test_a_desynchronising_frame_says_the_profile_may_be_incomplete(self):
        """When the recovery lands somewhere that is not a frame header, the parser says the
        profile may be missing points rather than reporting a short one as if it were whole."""
        text = "4\n energy: -1.0 xtb: 6.7.1\nH 0 0 0\nH 0 0 1\nnot a header at all\n"
        p = gfn2_scan.parse_scan_log(text)
        self.assertTrue(any("DESYNCHRONISED" in w for w in p["warnings"]), p["warnings"])

    def test_a_missing_log_is_reported_not_invented(self):
        p = gfn2_scan.read_log(os.path.join(FIXTURES, "does_not_exist.log"))
        self.assertEqual(0, p["n_points"])
        self.assertTrue(p["warnings"])


class TestFailureIsRecordedWithItsCause(unittest.TestCase):
    """🔴 `rc != 0` says a run failed; it does not say WHO failed. An SCF that will not
    converge on a stretched open-shell radical is a normal outcome of this chemistry; a broken
    input is ours. Same exit code, different owners -- so the cause is parsed and recorded.

    ⚠ The text below is the innermost frame of a REAL abort observed in the payload (rc 128),
    which is what turned "the constrained protocol produces 73 eV" into "the forward scan
    never finished".
    """

    ABORT = """
########################################################################
[ERROR] Program stopped due to fatal error
-7- Geometry optimization failed
-3- optimizer_relax: SCF not converged, aborting...
-1- scf: Self consistent charge iterator did not converge
########################################################################
abnormal termination of xtb
"""

    def test_an_scf_failure_is_named_as_such(self):
        f = gfn2_scan.parse_failure(self.ABORT)
        self.assertTrue(f["aborted"])
        self.assertEqual("scf_not_converged", f["kind"])
        self.assertIn("Self consistent charge", f["cause"])

    def test_the_innermost_frame_is_the_cause_not_the_outermost(self):
        """xtb's stack runs outermost-first; `-7- Geometry optimization failed` is the symptom
        and `-1- scf: ...` is the cause. Reporting the symptom would send the reader to the
        optimiser instead of to the electronic structure."""
        self.assertNotIn("Geometry optimization failed",
                         gfn2_scan.parse_failure(self.ABORT)["cause"])

    def test_a_clean_run_reports_no_failure(self):
        f = gfn2_scan.parse_failure("normal termination of xtb")
        self.assertFalse(f["aborted"])
        self.assertEqual("none", f["kind"])

    def test_an_abort_with_no_frames_is_still_an_abort(self):
        f = gfn2_scan.parse_failure("[ERROR] Program stopped due to fatal error\n")
        self.assertTrue(f["aborted"])
        self.assertIn("unattributed", f["cause"])


class TestBidirectionalPlanAndBudget(unittest.TestCase):
    def test_both_directions_use_the_same_grid(self):
        p = gfn2_scan.read_log(SCAN_LOG)
        plan = gfn2_scan.bidirectional_plan(p["points"][0]["geometry"], (1, 2), 12, 0.10)
        self.assertEqual(plan["forward"], (plan["d_start_ang"], plan["d_end_ang"]))
        self.assertEqual(plan["reverse"], (plan["d_end_ang"], plan["d_start_ang"]))
        self.assertEqual((2, 3), plan["pair_1based"],
                         "the mapping is 0-based and xtb is 1-based; the conversion happens "
                         "in exactly one place")

    def test_the_bidirectional_pass_fits_the_gfn2_budget_and_would_not_fit_the_dft_one(self):
        """🔴 39.47(a): the cap belongs to the ENGINE. 24 points is free at GFN2 and would
        breach the DFT cap of 20 -- which is why the gate runs where the guess is made."""
        p = gfn2_scan.read_log(SCAN_LOG)
        total = gfn2_scan.total_points(p, p)
        self.assertEqual(24, total)
        self.assertEqual(total, b0f_deck.check_scan_point_budget("gfn2", total))
        self.assertRaises(b0f_deck.DeckInputError,
                          b0f_deck.check_scan_point_budget, "dft", total)

    def test_a_frame_round_trips_to_xyz(self):
        p = gfn2_scan.read_log(SCAN_LOG)
        text = gfn2_scan.frame_xyz(p["points"][-1], "forward final frame")
        self.assertTrue(text.startswith("11\n"))
        self.assertEqual(13, len(text.strip().splitlines()))


class TestDirectionIsDerivedNotDeclared(unittest.TestCase):
    """🔴 [39.66] The one-sided bracket check needs to know whether a coordinate BREAKS or
    FORMS, and a declared field can be mis-declared -- which would invert the check into a
    machine for refusing good reactions. So it is read off the trajectory we already have.
    """

    def setUp(self):
        self.fwd = gfn2_scan.read_log(SCAN_LOG)

    def test_the_break_coordinate_reads_as_break_and_the_li_contact_as_form(self):
        """Reproduces the measured signs: the C-O distance rises along the path, and Li
        migrates ONTO the breaking oxygen so its distance falls."""
        self.assertEqual("break", gfn2_scan.derive_direction(self.fwd, (1, 2)))
        self.assertEqual("form", gfn2_scan.derive_direction(self.fwd, (10, 1)))

    def test_a_non_monotonic_coordinate_has_no_direction(self):
        """🔴 None is a real answer, not a failure to compute one. The caller must record
        `applicable: false, non_monotonic` and COUNT it rather than dropping the coordinate."""
        prof = {"points": [{"geometry": [("H", 0, 0, 0), ("H", 0, 0, d)]}
                           for d in (1.0, 1.4, 1.1, 1.6)]}
        self.assertIsNone(gfn2_scan.derive_direction(prof, (0, 1)))

    def test_a_profile_too_short_to_have_a_trend_has_no_direction(self):
        self.assertIsNone(gfn2_scan.derive_direction({"points": []}, (0, 1)))

    def test_the_free_cross_check_against_certified_endpoints(self):
        """🟢 [39.66] Where BOTH endpoints are certified (R-A today), the derived direction
        must agree with the sign of (product - reactant). Disagreement means the scan and the
        endpoints describe different reactions -- worth knowing on its own, and free."""
        self.assertTrue(gfn2_scan.direction_agrees_with_endpoints("break", 1.405, 2.503))
        self.assertTrue(gfn2_scan.direction_agrees_with_endpoints("form", 2.489, 1.803))
        self.assertFalse(gfn2_scan.direction_agrees_with_endpoints("form", 1.405, 2.503))
        self.assertIsNone(gfn2_scan.direction_agrees_with_endpoints(None, 1.4, 2.5),
                          "an unmakeable check returns None, never a silent True")


if __name__ == "__main__":
    unittest.main()
