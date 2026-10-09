"""HOMO/SOMO and frequency parsing — load-bearing for the whole B0 batch.

🔴 The bound-species check now runs on EVERY species (23/23), and a species whose highest
   occupied orbital cannot be read is held OUT of the u_cheap statistics. ⟹ **this parser decides
   the sample size.**

🔴🔴 AND THE FORMAT IS `[UNVERIFIED]`: G16 is not installed here, so the patterns were written
   from documentation and have never seen a real log. **That is exactly how round trip #1 died** —
   an ORCA parser applied to Gaussian logs, producing plausible output nobody could question.
   ⟹ the tests below do NOT assert that the format is right. They assert that the module can say
   **"I matched nothing"** and that this is reported as a PARSER failure, never as a data failure.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import orbitals, units

#: [UNVERIFIED — the documented shape, not output we have seen.] Labelled here as well as in the
#: module so a reader of the tests cannot mistake it for a captured fixture.
FIXTURES = os.path.join(context.REPO_ROOT, "tests", "fixtures")

FAKE_CLOSED = """
 Alpha  occ. eigenvalues --  -19.12345 -10.23456   -1.02938
 Alpha  occ. eigenvalues --   -0.51234
 Alpha virt. eigenvalues --    0.12345   0.23456
 Frequencies --    31.2000   44.0000   55.0000
 Frequencies --   780.0000  1200.0000  1810.0000
"""

FAKE_OPEN = """
 Alpha  occ. eigenvalues --  -19.10000  -1.00000  -0.40000
 Alpha virt. eigenvalues --    0.10000
 Beta  occ. eigenvalues --  -19.09000  -0.98000
 Beta virt. eigenvalues --   -0.20000   0.15000
 Frequencies --    22.0000   90.0000  400.0000
"""

#: A real-looking log from a DIFFERENT program. The RT#1 shape.
ORCA_SHAPED = """
   NO   OCC          E(Eh)            E(eV)
    0   2.0000     -19.123456      -520.240
    1   2.0000      -1.029380       -28.011
VIBRATIONAL FREQUENCIES
   6:      -450.12 cm**-1
"""


class TestItCanSayItMatchedNothing(unittest.TestCase):
    """🔴 The single most important property, given the format is unverified."""

    def test_a_log_from_another_program_is_a_PARSER_failure_not_a_data_failure(self):
        h = orbitals.highest_occupied(ORCA_SHAPED)
        self.assertEqual(h["failure_kind"], "parser",
                         "an ORCA-shaped log was reported as a DATA failure -- that is round "
                         "trip #1 exactly: the species would be recorded as 'no orbitals'")
        self.assertFalse(h["format_recognised"])
        self.assertIsNone(h["highest_occupied_hartree"])

    def test_the_parser_failure_names_itself_as_the_problem(self):
        p = orbitals.parse(ORCA_SHAPED)
        joined = " ".join(p["warnings"])
        self.assertIn("orbital_format_not_recognised", joined)
        self.assertIn("PARSER problem, not a data problem", joined)
        self.assertIn("do not record the species as 'no orbitals'", joined)

    def test_it_prints_the_shape_it_expected_so_a_reader_can_compare(self):
        p = orbitals.parse(ORCA_SHAPED)
        self.assertIn("eigenvalues", p["expected_line_shape"])
        self.assertIn("[UNVERIFIED]", p["format_status"])

    def test_an_empty_log_is_not_evidence_the_format_is_wrong(self):
        p = orbitals.parse("")
        self.assertFalse(p["format_recognised"])
        self.assertIn("NOT evidence that the format is wrong", " ".join(p["warnings"]))

    def test_a_recognised_format_with_no_occupied_levels_is_a_DATA_failure(self):
        """The other side of the same distinction."""
        h = orbitals.highest_occupied(" Alpha virt. eigenvalues --    0.12345\n")
        self.assertTrue(h["format_recognised"])
        self.assertEqual(h["failure_kind"], "data")
        self.assertIn("DATA problem in this log, not a parser problem", " ".join(h["warnings"]))

    def test_the_unverified_scope_is_the_orbital_block_only(self):
        """🔴 An over-broad warning gets ignored, and then the real one goes with it.

        The frequency half DELEGATES to `criteria.g16.parse_frequencies`, which parsed a real
        Gaussian 16 log on the cluster (RT-1 round 1). Only the eigenvalue block is unverified.
        """
        self.assertIn("[UNVERIFIED]", orbitals.FORMAT_STATUS)
        self.assertIn("ORBITALS ONLY", orbitals.FORMAT_STATUS)
        self.assertIn("[MEASURED-PROVENANCE]", orbitals.FREQUENCY_FORMAT_STATUS)
        self.assertNotIn("[UNVERIFIED]", orbitals.FREQUENCY_FORMAT_STATUS)

    def test_the_frequency_provenance_names_the_real_log_it_came_from(self):
        st = orbitals.FREQUENCY_FORMAT_STATUS
        self.assertIn("ts_qst2.log", st)
        self.assertIn("-105.0", st)

    def test_format_validation_reports_both_statuses_separately(self):
        v = orbitals.format_validation(FAKE_CLOSED)
        self.assertIn("ORBITALS ONLY", v["orbital_format_status"])
        self.assertIn("[MEASURED-PROVENANCE]", v["frequency_format_status"])
        self.assertIn("UKS", v["_closes"])


class TestHighestOccupied(unittest.TestCase):
    def test_closed_shell_homo_is_the_highest_alpha_occupied(self):
        h = orbitals.highest_occupied(FAKE_CLOSED, multiplicity=1)
        self.assertAlmostEqual(h["homo_hartree"], -0.51234)
        self.assertAlmostEqual(h["highest_occupied_ev"], units.hartree_to_ev(-0.51234), places=9)
        self.assertIsNone(h["somo_hartree"],
                          "a RESTRICTED log has no Beta block and every orbital is DOUBLY "
                          "occupied -- reporting a SOMO here is what `n_alpha > n_beta` alone "
                          "does when n_beta is 0")
        self.assertFalse(h["is_unrestricted"])
        self.assertEqual(h["derived_multiplicity"], 1)

    def test_open_shell_homo_is_the_higher_of_alpha_and_beta(self):
        """🔴 Taking alpha alone would be wrong for a beta-rich species, and silently so."""
        h = orbitals.highest_occupied(FAKE_OPEN, multiplicity=2)
        self.assertAlmostEqual(h["homo_hartree"], -0.40000)
        self.assertEqual(h["homo_spin"], "alpha")
        self.assertAlmostEqual(h["spin_resolved"]["beta_homo_hartree"], -0.98000)

    def test_the_homo_can_be_beta_while_the_somo_stays_alpha(self):
        """🔴 THE BUG THE REAL LOG EXPOSED. These are different orbitals."""
        text = FAKE_OPEN.replace("-0.98000", "-0.10000")
        h = orbitals.highest_occupied(text, multiplicity=2)
        self.assertAlmostEqual(h["homo_hartree"], -0.10000)
        self.assertEqual(h["homo_spin"], "beta")
        self.assertAlmostEqual(h["somo_hartree"], -0.40000,
                               msg="the SOMO must remain the unpaired ALPHA orbital even when a "
                                   "doubly-occupied beta level sits above it")
        self.assertIn("homo_is_not_the_somo", " ".join(h["warnings"]))

    def test_energies_are_hartree_and_converted_only_through_units(self):
        h = orbitals.highest_occupied(FAKE_CLOSED, 1)
        self.assertAlmostEqual(h["highest_occupied_ev"] / h["highest_occupied_hartree"],
                               units.HARTREE_TO_EV, places=9)

    def test_only_the_last_block_is_used(self):
        """A log holds several blocks (opt steps, then freq); mixing them interleaves geometries.

        🔴 The earlier block's HOMO is deliberately HIGHER than the last block's. A fixture where
        the last block also happens to hold the maximum cannot see this defect at all -- my first
        version was exactly that, and merging all blocks passed it.
        """
        two = (" Alpha  occ. eigenvalues --  -1.00000\n"
               " Frequencies --  100.0\n"
               " Alpha  occ. eigenvalues --  -5.00000\n")
        self.assertAlmostEqual(
            orbitals.highest_occupied(two)["highest_occupied_hartree"], -5.00000,
            msg="the HOMO came from an EARLIER block -- orbitals from a mid-optimisation "
                "geometry are being mixed with the converged one")

    def test_the_last_block_wins_even_when_earlier_ones_are_longer(self):
        many = (" Alpha  occ. eigenvalues --  -2.0 -1.5 -1.0\n"
                " Frequencies --  100.0\n"
                " Alpha  occ. eigenvalues --  -9.0\n")
        self.assertAlmostEqual(
            orbitals.highest_occupied(many)["highest_occupied_hartree"], -9.0)


class TestThereIsOnlyOneFrequencyParser(unittest.TestCase):
    def test_it_delegates_to_the_existing_g16_parser(self):
        """🔒 Two parsers for one format is the shape that has cost this project repeatedly."""
        from sei_pilot.criteria import g16
        self.assertEqual(orbitals.frequencies(FAKE_CLOSED), g16.parse_frequencies(FAKE_CLOSED))

    def test_it_reads_the_frequencies(self):
        self.assertEqual(orbitals.frequencies(FAKE_CLOSED),
                         [31.2, 44.0, 55.0, 780.0, 1200.0, 1810.0])


class TestSampleSizeIsVisible(unittest.TestCase):
    """🔴 'If 6 of 23 silently drop out, u_cheap is computed on 17 and nothing says so.'"""

    def _records(self):
        return [
            orbitals.species_record("good_a", FAKE_CLOSED, 1),
            orbitals.species_record("good_b", FAKE_OPEN, 2),
            orbitals.species_record("parser_broke", ORCA_SHAPED, 1),
            orbitals.species_record("no_freqs", " Alpha  occ. eigenvalues --  -0.5\n", 1),
        ]

    def test_the_two_failure_kinds_are_reported_separately(self):
        s = orbitals.batch_parse_summary(self._records())
        self.assertEqual(s["dropped_orbital_parser_failure"], ["parser_broke"])
        self.assertEqual(s["dropped_frequency_parse_failure"], ["parser_broke", "no_freqs"])

    def test_the_usable_count_is_the_sample_size_and_says_so(self):
        s = orbitals.batch_parse_summary(self._records())
        self.assertEqual(s["n_species"], 4)
        self.assertEqual(s["n_usable"], 2)
        self.assertEqual(s["n_dropped"], 2)
        self.assertIn("NOT on `n_species`", s["_sample_size_note"])
        self.assertIn("batch_sample_reduced", " ".join(s["warnings"]))

    def test_a_parser_failure_is_shouted_about_separately(self):
        """🔴🔴 THE PARSER, NOT THE DATA — they have opposite prescriptions."""
        s = orbitals.batch_parse_summary(self._records())
        joined = " ".join(s["warnings"])
        self.assertIn("orbital_PARSER_failed", joined)
        self.assertIn("THE PARSER, NOT THE DATA", joined)

    def test_a_clean_batch_produces_no_warnings(self):
        s = orbitals.batch_parse_summary([orbitals.species_record("a", FAKE_CLOSED, 1)])
        self.assertEqual(s["n_dropped"], 0)
        self.assertEqual(s["warnings"], [])

    def test_a_species_record_marks_itself_unusable_rather_than_half_present(self):
        r = orbitals.species_record("x", ORCA_SHAPED, 1)
        self.assertFalse(r["usable"])
        self.assertIsNone(r["highest_occupied_hartree"])
        self.assertEqual(r["n_frequencies"], 0)


class TestFormatValidationExistsToCloseTheUnverified(unittest.TestCase):
    def test_it_reports_both_parsers_on_a_real_log(self):
        v = orbitals.format_validation(FAKE_CLOSED)
        self.assertTrue(v["orbital_format_recognised"])
        self.assertEqual(v["frequency_lines_found"], 6)
        self.assertEqual(v["orbital_verdict"], "matched")
        self.assertEqual(v["frequency_verdict"], "matched")

    def test_it_fails_loudly_on_a_log_it_cannot_read(self):
        v = orbitals.format_validation(ORCA_SHAPED)
        self.assertFalse(v["orbital_format_recognised"])
        self.assertIn("MATCHED NOTHING", v["orbital_verdict"])

    def test_an_eigenvalue_only_input_is_not_reported_as_a_frequency_FAILURE(self):
        """🔴 Two independent parsers, two verdicts.

        A combined verdict said "AT LEAST ONE PARSER MATCHED NOTHING" on the real eigenvalue
        block -- correct about frequencies, misleading about orbitals, and it read as a failure of
        the thing that had just succeeded.
        """
        path = os.path.join(FIXTURES, "g16_eigenvalues_p1_ts.txt")
        if not os.path.exists(path):
            self.skipTest("real G16 fixture absent")
        with open(path) as fh:
            v = orbitals.format_validation(fh.read())
        self.assertEqual(v["orbital_verdict"], "matched")
        self.assertIn("NOT a failure", v["frequency_verdict"])

    def test_it_says_what_it_closes(self):
        v = orbitals.format_validation(FAKE_CLOSED)
        self.assertIn("[UNVERIFIED]", v["_closes"])
        self.assertIn("[MEASURED]", v["_closes"])


class TestSampleSizeSurvivesTheWholeChain(unittest.TestCase):
    """🔴 FOUR DIFFERENT DENOMINATORS, each dropping species for its own reason."""

    CLEAN = " Alpha  occ. eigenvalues --  -0.5\n Frequencies --  31.2 44.0 800.0\n"
    UNBOUND = " Alpha  occ. eigenvalues --   0.02\n Frequencies --  31.2 44.0 800.0\n"

    def _species(self):
        from sei_pilot import b0_species
        return b0_species.all_species()[:6]

    def _panel(self, logs, costs=None):
        from sei_pilot import orbitals as o
        sp = self._species()
        default = dict((s["id"], {"opt_cycles": 20, "core_hours": 4.0, "converged": True})
                       for s in sp)
        default.update(costs or {})
        return o.b0_species_panel(sp, logs, default)

    def test_a_clean_batch_has_one_denominator_and_no_warning_about_it(self):
        sp = self._species()
        r = self._panel(dict((s["id"], self.CLEAN) for s in sp))
        self.assertEqual(len(set(r["sample_sizes"].values())), 1)
        self.assertNotIn("sample_sizes_differ", " ".join(r["warnings"]))

    def test_a_parser_failure_shrinks_every_downstream_denominator_and_says_which(self):
        sp = self._species()
        logs = dict((s["id"], self.CLEAN) for s in sp)
        logs[sp[0]["id"]] = "NOT A GAUSSIAN LOG"
        r = self._panel(logs)
        sizes = r["sample_sizes"]
        self.assertEqual(sizes["n_species_requested"], 6)
        self.assertEqual(sizes["n_parsed_usable"], 5)
        joined = " ".join(r["warnings"])
        self.assertIn("THE PARSER, NOT THE DATA", joined)
        self.assertIn("sample_sizes_differ", joined)

    def test_an_unbound_species_leaves_u_cheap_but_is_not_a_parse_failure(self):
        """🔴 Three different reasons to lose a species, and they must not merge."""
        sp = self._species()
        logs = dict((s["id"], self.CLEAN) for s in sp)
        logs[sp[0]["id"]] = self.UNBOUND
        r = self._panel(logs)
        self.assertEqual(r["sample_sizes"]["n_parsed_usable"], 6,
                         "an UNBOUND species parsed perfectly well -- it must not be counted as "
                         "a parse failure")
        self.assertEqual(r["sample_sizes"]["n_in_u_cheap_statistics"], 5)
        self.assertIn(sp[0]["id"], r["bound_partition"]["excluded_unbound"])

    def test_a_missing_cost_drops_only_the_correlation(self):
        sp = self._species()
        logs = dict((s["id"], self.CLEAN) for s in sp)
        r = self._panel(logs, costs={sp[0]["id"]: {"opt_cycles": None, "core_hours": None,
                                                   "converged": True}})
        self.assertEqual(r["sample_sizes"]["n_parsed_usable"], 6)
        self.assertEqual(r["sample_sizes"]["n_in_u55_correlation"], 5)

    def test_the_four_denominators_are_named_as_not_interchangeable(self):
        sp = self._species()
        r = self._panel(dict((s["id"], self.CLEAN) for s in sp))
        self.assertIn("not interchangeable", r["_read_the_sample_sizes"])
        self.assertIn("n_frames is not the sample size", r["_read_the_sample_sizes"])


class TestAgainstTheRealG16EigenvalueBlock(unittest.TestCase):
    """🟢 THE `[UNVERIFIED]`-CLOSING TEST. Real Gaussian 16 output, supplied by the user.

    Provably RT-1's P1 TS species: 25 alpha + 24 beta occupied => multiplicity 2 and 49 electrons,
    which match the report's declared charge 0 / mult 2 and C3H4LiO3's electron count — two facts
    the block could not have been fitted to.

    🔴 It carries FOUR traps. Two would have silently halved the parse, one breaks any sign-based
    occupancy classifier, and one was a REAL BUG in this module (HOMO vs SOMO).
    """

    def _text(self):
        import os
        path = os.path.join(FIXTURES, "g16_eigenvalues_p1_ts.txt")
        if not os.path.exists(path):
            self.skipTest("real G16 fixture absent")
        with open(path) as fh:
            return fh.read()

    def test_trap1_beta_lines_are_not_lost_to_differing_leading_whitespace(self):
        """' Alpha' has ONE leading space, '  Beta' has TWO. ^Alpha|^Beta drops every Beta line."""
        p = orbitals.parse(self._text())
        self.assertEqual(len(p["beta_occ_hartree"]), 24,
                         "the Beta lines were lost -- a pattern anchored on a single leading "
                         "space matches every Alpha line and no Beta line, giving 25 of 49 "
                         "orbitals with NO error")

    def test_trap2_occupied_lines_are_not_lost_to_the_double_space(self):
        """'occ.' takes TWO spaces, 'virt.' takes ONE. A literal space returns a LUMO as the HOMO."""
        p = orbitals.parse(self._text())
        self.assertEqual(len(p["alpha_occ_hartree"]), 25)
        self.assertLess(max(p["alpha_occ_hartree"]), 0.0)
        self.assertGreater(max(p["alpha_virt_hartree"]), 0.0)

    def test_trap3_a_negative_virtual_is_still_a_virtual(self):
        """🔴 The beta LUMO is -0.00368. Occupancy comes from the LABEL, never the sign."""
        p = orbitals.parse(self._text())
        self.assertAlmostEqual(min(p["beta_virt_hartree"]), -0.00368, places=5)
        self.assertNotIn(-0.00368, p["beta_occ_hartree"],
                         "a NEGATIVE VIRTUAL orbital was classified as occupied -- a sign-based "
                         "classifier would do exactly this, and reduced species can have a "
                         "positive SOMO")
        h = orbitals.highest_occupied(self._text(), 2)
        self.assertIn("never the sign", h["occupancy_source"])

    def test_trap4_homo_and_somo_are_emitted_separately(self):
        """🔴 THE REAL BUG THIS LOG FOUND. They coincide HERE by luck."""
        h = orbitals.highest_occupied(self._text(), multiplicity=2)
        self.assertAlmostEqual(h["homo_hartree"], -0.30464, places=5)
        self.assertAlmostEqual(h["somo_hartree"], -0.30464, places=5)
        self.assertAlmostEqual(h["spin_resolved"]["beta_homo_hartree"], -0.34581, places=5)
        self.assertNotIn("homo_or_somo_hartree", h,
                         "the conflated field is back -- HOMO and SOMO are different objects")

    def test_trap4_the_beta_higher_case_is_where_max_would_be_wrong(self):
        """🔴 Constructed so the DEFECTIVE behaviour gives a DIFFERENT answer (my own rule).

        beta HOMO above alpha SOMO: `max(all occupied)` returns a DOUBLY OCCUPIED orbital.
        """
        text = (" Alpha  occ. eigenvalues --  -1.00000  -0.50000\n"
                "  Beta  occ. eigenvalues --  -0.90000\n")
        h = orbitals.highest_occupied(text, multiplicity=2)
        self.assertAlmostEqual(h["somo_hartree"], -0.50000, places=5)
        self.assertAlmostEqual(h["homo_hartree"], -0.50000, places=5)
        text2 = (" Alpha  occ. eigenvalues --  -1.00000  -0.90000\n"
                 "  Beta  occ. eigenvalues --  -0.50000\n")
        h2 = orbitals.highest_occupied(text2, multiplicity=2)
        self.assertAlmostEqual(h2["somo_hartree"], -0.90000, places=5,
                               msg="the SOMO must be the unpaired alpha orbital, NOT the highest "
                                   "occupied level -- here the beta HOMO sits above it")
        self.assertAlmostEqual(h2["homo_hartree"], -0.50000, places=5)
        self.assertIn("homo_is_not_the_somo", " ".join(h2["warnings"]))

    def test_the_derived_multiplicity_matches_the_declared_one(self):
        h = orbitals.highest_occupied(self._text(), multiplicity=2)
        self.assertEqual(h["derived_multiplicity"], 2)
        self.assertEqual(h["spin_resolved"]["n_alpha_occ"]
                         + h["spin_resolved"]["n_beta_occ"], 49)
        self.assertEqual(h["warnings"], [])

    def test_a_declared_multiplicity_that_contradicts_the_orbitals_is_flagged(self):
        h = orbitals.highest_occupied(self._text(), multiplicity=1)
        self.assertIn("multiplicity_mismatch", " ".join(h["warnings"]))

    def test_the_run_together_column_case_stays_unverified(self):
        """⚠ One real log validates the format it CONTAINS and nothing else."""
        with open(os.path.join(FIXTURES, "PROVENANCE.md")) as fh:
            prov = fh.read()
        self.assertIn("run-together", prov.lower())
        self.assertIn("remains `[UNVERIFIED]`", prov)
        self.assertIn("validates the format it contains and nothing else", prov)


if __name__ == "__main__":
    unittest.main()
