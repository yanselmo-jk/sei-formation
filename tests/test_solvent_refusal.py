"""C-5 — the builder that refuses, and the fallback that must be impossible.

🔴 NOT HYPOTHETICAL. RT-1's P1 ran on the cluster with
   `#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen...`
   — eps 35.7 against EC:EMC 3:7's ~18–20, roughly a factor of two on the reaction field, for a
   charge-localising ring-opening of an ion pair. It was a pilot placeholder that survived into a
   302 core-h production-shaped run.

🔒 The only reliable way to stop a fallback is to make it unreachable. These tests assert the
   refusal, not a warning.
"""

import unittest

import context  # noqa: F401
from sei_pilot import solvent


class TestItRefusesRatherThanFallingBack(unittest.TestCase):
    def test_it_raises_with_the_table_as_shipped(self):
        self.assertRaises(solvent.SolventDescriptorsMissing, solvent.solvent_line)

    def test_the_refusal_names_the_actual_incident(self):
        try:
            solvent.solvent_line()
        except solvent.SolventDescriptorsMissing as exc:
            msg = str(exc)
        else:
            self.fail("a deck was emitted with no descriptors")
        self.assertIn("acetonitrile", msg)
        self.assertIn("35.7", msg)
        self.assertIn("THE FALLBACK IS NOT AVAILABLE", msg)

    def test_it_never_returns_a_named_solvent(self):
        """A returned empty string is a fallback too — a caller would splice it in."""
        for bad in (None, {}, {"Eps": 20.0}):
            self.assertRaises(solvent.SolventDescriptorsMissing, solvent.solvent_line, bad)

    def test_a_partial_table_still_refuses(self):
        partial = {"Eps": 19.0, "EpsInf": 2.0, "HBondAcidity": 0.0}
        self.assertRaises(solvent.SolventDescriptorsMissing, solvent.solvent_line, partial)

    def test_a_complete_table_emits_generic_and_never_a_solvent_name(self):
        """Positive control — it must be satisfiable, or it is a wall rather than a guard."""
        full = {"Eps": 19.0, "EpsInf": 2.02, "HBondAcidity": 0.0,
                "HBondBasicity": 0.55, "SurfaceTensionAtInterface": 45.0}
        line = solvent.solvent_line(full)
        self.assertIn("solvent=generic", line)
        self.assertNotIn(solvent.FORBIDDEN_FALLBACK, line)
        for name in solvent.DESCRIPTOR_NAMES:
            self.assertIn(name, line)


class TestEmptyIsNotAbsent(unittest.TestCase):
    """🔴 Nobody may later read a MISSING table as 'no descriptors needed'."""

    def test_the_table_exists_and_is_empty(self):
        self.assertEqual(solvent.DESCRIPTORS, {})
        self.assertIn("[EMPTY, NOT ABSENT]", solvent.DESCRIPTOR_STATUS)

    def test_the_two_structural_descriptors_are_recorded_as_known(self):
        """🟢 The gap is exactly five values, not seven — derivable, not measured."""
        st = solvent.status()
        self.assertEqual(st["n_known"], 2)
        self.assertEqual(st["n_missing"], 5)
        self.assertEqual(st["known_structurally"]["CarbonAromaticity"], 0.0)
        self.assertEqual(st["known_structurally"]["ElectronegativeHalogenicity"], 0.0)

    def test_status_never_raises_and_says_it_cannot_emit(self):
        st = solvent.status()
        self.assertFalse(st["can_emit_deck"])
        self.assertTrue(st["table_is_empty_not_absent"])
        # ADR-106 voided the old blocker text ("pending the eps sensitivity scan") --
        # the scan is DROPPED [USER-DOMAIN] and the refusal must not cite a dead blocker.
        self.assertIn("ADR-104", st["blocked_on"])
        self.assertNotIn("eps sensitivity scan", st["blocked_on"])

    def test_the_source_failure_is_recorded_not_a_plausible_number(self):
        self.assertIn("[UNVERIFIED]", solvent.DESCRIPTOR_STATUS)
        self.assertIn("subsetted fonts", solvent.DESCRIPTOR_STATUS)


class TestTheThreeTrapsTravelWithTheTable(unittest.TestCase):
    def test_all_three_are_carried_in_the_status_record(self):
        traps = " ".join(solvent.status()["traps_for_whoever_fills_it"])
        self.assertIn("cal mol^-1 A^-2, NOT dyn/cm", traps)
        self.assertIn("WILL NOT CRASH", traps)
        self.assertIn("SOLID at 298 K", traps)
        self.assertIn("UNVALIDATED", traps)

    def test_the_unverified_conversion_factor_is_not_written_down(self):
        """🔴 The factor itself is [UNVERIFIED]; encoding it would be the trap, not the warning."""
        import inspect
        src = inspect.getsource(solvent)
        self.assertIn("is [UNVERIFIED] and is not written down here", src)


class TestTheEpsilonScanLineIsNotAProductionSolvent(unittest.TestCase):
    """🟢 Why the ordering ruling works: the scan needs no descriptors."""

    def test_it_builds_without_any_descriptors(self):
        r = solvent.epsilon_scan_line(20.0)
        self.assertIn("Eps=20.0", r["line"])
        self.assertIn("solvent=generic", r["line"])

    def test_it_never_names_a_solvent(self):
        for eps in (3.0, 20.0, 90.0):
            self.assertNotIn(solvent.FORBIDDEN_FALLBACK, solvent.epsilon_scan_line(eps)["line"])

    def test_it_declares_it_is_not_a_production_solvent_model(self):
        r = solvent.epsilon_scan_line(20.0)
        self.assertFalse(r["is_production_solvent_model"])
        self.assertIn("Do not reuse this for a production deck", r["🔴"])

    def test_it_states_the_asymmetry_of_what_it_bounds(self):
        """🔴 A SMALL spread bounds the full response; a LARGE one does not."""
        why = solvent.epsilon_scan_line(20.0)["why_this_is_allowed_without_descriptors"]
        self.assertIn("SMALL spread BOUNDS", why)
        self.assertIn("A LARGE spread does NOT", why)

    def test_a_nonsense_epsilon_is_refused(self):
        for bad in (None, 0, -5):
            self.assertRaises(ValueError, solvent.epsilon_scan_line, bad)


if __name__ == "__main__":
    unittest.main()
