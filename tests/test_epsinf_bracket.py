"""[39.73] EpsInf — the sentinel that took out every frequency job in the round.

🔴 WHAT HAPPENED: the PCM read block supplied `eps=18.5` and nothing else. G16's **freq** stage
reads the absent `EpsInf` as `EpsInf=0.0000` and aborts in L1110. Rough and tight optimisation
never touch that path, so the defect is invisible until a Hessian is computed — and route smoke
does not compute one. First Hessian under `solvent=generic` in project history was a production
job, and it took the endpoint certification AND all 20 of P5's frequency stages with it.

🔒 STRUCTURAL POINT WORTH KEEPING: ADR-108's move to PCM-numeric escaped the seven-descriptor
SMD problem for energies and gradients and DEFERRED it to the Hessian stage — which is exactly
the stage C-8 depends on. A gate that runs on a cheaper path than the thing it certifies cannot
see this class of failure.

🟢 THE FIX IS A BRACKET, NOT A LOOKUP: run the freq stage at both physically admissible extremes
(n² = 1, no fast response; n² = eps, fast response equals full) and see whether the answer moves.
No value needs sourcing unless it does.
"""

import unittest

import context  # noqa: F401
from sei_pilot import solvent


class TestTheDeckNamesACarrierSolventAndNeverEmitsEpsInf(unittest.TestCase):
    """🔒 [USER RULING 2026-08-21, final] `scrf=(pcm,solvent=acetone,read)` + `eps=18.5`.
    No EpsInf line; the bracket experiment is CANCELLED. `solvent.epsinf_bracket` /
    `epsinf_invariance` stay as pure functions (tested below) but nothing in the plan uses them.
    """
    POLICY = {"model": "pcm_numeric", "epsilon": 18.5, "deck_verified": True}

    def test_route_names_the_carrier_and_read_block_is_eps_only(self):
        deck = solvent.resolve_solvent_deck(self.POLICY)
        self.assertEqual("scrf=(pcm,solvent=acetone,read)", deck["route_fragment"])
        self.assertEqual(["eps=18.5"], deck["extra_input_lines"])
        self.assertIsNone(deck["eps_inf"])
        self.assertNotIn(solvent.FORBIDDEN_FALLBACK, deck["route_fragment"])

    def test_a_supplied_eps_inf_is_ignored_loudly(self):
        deck = solvent.resolve_solvent_deck(self.POLICY, eps_inf=1.0)
        self.assertFalse([l for l in deck["extra_input_lines"] if "EpsInf" in l])
        self.assertIn("ignored", deck["_eps_inf_status"])

    def test_no_bracket_item_in_the_plan(self):
        from sei_pilot import plan
        src = open(plan.__file__.replace(".pyc", ".py")).read()
        self.assertNotIn("epsinf_full", src)
        self.assertNotIn("SEI_QC_EPSINF", src)


class TestTheBracketNeedsNoSourcedValue(unittest.TestCase):
    def test_the_two_endpoints_are_the_ends_of_the_admissible_range(self):
        """🔒 n² cannot be below 1 (no response) and equilibrium solvation cannot respond
        faster than fully (n² = eps). Both ends are definitional, so nothing is looked up."""
        self.assertEqual([("no_fast_response", 1.0), ("full_response", 18.5)],
                         solvent.epsinf_bracket(18.5))

    def test_an_impossible_eps_is_refused(self):
        self.assertRaises(ValueError, solvent.epsinf_bracket, 0.5)


class TestInvarianceIsJudgedOnWhatC8ActuallyReads(unittest.TestCase):
    """🔴 The verdict is over `n_imag` plus the low-frequency spectrum, where a solvent-response
    term would show up first — NOT over numerical identity, which would fail on rounding and
    tell us nothing."""

    def test_matching_n_imag_and_low_frequencies_is_invariance(self):
        r = solvent.epsinf_invariance(
            {"n_imag": 0, "frequencies_cm1": [45.0, 120.0, 900.0]},
            {"n_imag": 0, "frequencies_cm1": [45.3, 120.1, 905.0]})
        self.assertTrue(r["invariant"])
        self.assertAlmostEqual(0.3, r["max_low_freq_shift_cm1"], places=6)
        self.assertIn("no n^2 needs sourcing", r["reasons"][0])

    def test_a_moving_n_imag_is_a_real_finding_not_a_nuisance(self):
        r = solvent.epsinf_invariance(
            {"n_imag": 0, "frequencies_cm1": [45.0]},
            {"n_imag": 1, "frequencies_cm1": [-30.0]})
        self.assertFalse(r["invariant"])
        self.assertIn("has to be sourced", r["reasons"][0])

    def test_a_changed_low_mode_count_is_caught(self):
        """A mode appearing or vanishing below the cutoff is a bigger change than any shift
        within it, so it is reported as its own reason rather than as a large shift."""
        r = solvent.epsinf_invariance(
            {"n_imag": 0, "frequencies_cm1": [45.0, 900.0]},
            {"n_imag": 0, "frequencies_cm1": [45.0, 150.0, 900.0]})
        self.assertFalse(r["invariant"])
        self.assertIn("count", r["reasons"][0])

    def test_a_missing_run_yields_no_verdict(self):
        """Rule 18: an unrun comparison is not an invariance result. This matters here because
        the crash being fixed is exactly what makes a run missing."""
        r = solvent.epsinf_invariance({"n_imag": 0, "frequencies_cm1": [45.0]}, {})
        self.assertIsNone(r["invariant"])
        self.assertIn("not an invariance result", r["reasons"][0])


if __name__ == "__main__":
    unittest.main()
