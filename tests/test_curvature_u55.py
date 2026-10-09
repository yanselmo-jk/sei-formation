"""U-55's curvature observables, and the correlation that decides it.

🔴 WHY THIS REPLACED A RATE. U-55 asks whether the Li+-multiligand class is INTRINSICALLY hard to
   optimise — a question about **the shape of the PES near the minimum**. A dissociation rate is
   KINETIC, and proposer5 withdrew its own §39.26(a) sentence once the temperature finding showed
   the rate could never be measured at a defined temperature anyway.

🔒 The replacement is not a better proxy — it is close to the cause. A quasi-Newton optimiser's
   convergence rate is governed by the Hessian's CONDITION NUMBER, so "floppy" and "expensive to
   optimise" are connected through that quantity mechanically rather than statistically.

🔴 THE UNIT TRAP THIS FILE GUARDS: lambda ∝ nu^2, so the condition number is (nu_max/nu_min)^2 and
   NOT nu_max/nu_min. The wrong one understates the spread by a square root and looks like an
   answer.
"""

import unittest

import context  # noqa: F401
from sei_pilot import conformers, curvature


class TestTheObservables(unittest.TestCase):
    FREQS = [31.2, 44.0, 55.0, 780.0, 1200.0, 1810.0]
    WITH_ARTEFACT = [0.4] + FREQS

    def test_nu_min_is_the_lowest_real_frequency_with_no_floor_applied(self):
        """🔴 THE FLOOR IS GONE. A 0.4 cm^-1 mode is reported, not silently excluded."""
        o = curvature.observables(self.WITH_ARTEFACT)
        self.assertAlmostEqual(o["nu_min_cm1"], 0.4)
        self.assertFalse(hasattr(curvature, "NOISE_FLOOR_CM1"),
                         "the noise floor is back. It only decided WHICH SINGLE NUMBER dominated "
                         "an already-fragile statistic; the fix was the statistic.")

    def test_n_soft_is_a_curve_so_the_threshold_is_visible(self):
        """🟢 The correlation picks whichever x predicts, and THAT is the calibration."""
        o = curvature.observables(self.FREQS)
        self.assertEqual(sorted(o["n_soft_curve"]), [10.0, 25.0, 50.0, 100.0, 200.0])
        self.assertEqual(o["n_soft_curve"][50.0], 2)
        self.assertEqual(o["n_soft_curve"][100.0], 3)
        self.assertEqual(o["n_soft_curve"][10.0], 0)

    def test_the_single_soft_threshold_is_marked_asserted_not_calibrated(self):
        """🔴 proposer5 broke its own §39.4(c) rule setting it, and said so."""
        self.assertIn("[ASSERTED]", curvature.SOFT_MODE_CM1_STATUS)
        self.assertIn("not calibrated", curvature.SOFT_MODE_CM1_STATUS)
        self.assertIn("[ASSERTED]", curvature.observables(self.FREQS)["_n_soft_status"])

    def test_the_condition_number_is_a_trimmed_ladder_not_one_number(self):
        o = curvature.observables(self.FREQS)
        self.assertEqual(sorted(o["trimmed_condition_numbers"]), [1, 2, 3])
        real = sorted(self.FREQS)
        for k in (1, 2, 3):
            self.assertAlmostEqual(o["trimmed_condition_numbers"][k],
                                   (real[-1] / real[k - 1]) ** 2, places=6)

    def test_the_ladder_makes_the_fragility_visible(self):
        """🔴 THE WHOLE REASON FOR TRIMMING: one artefact mode moves k=1 by orders of magnitude."""
        clean = curvature.observables(self.FREQS)["trimmed_condition_numbers"]
        dirty = curvature.observables(self.WITH_ARTEFACT)["trimmed_condition_numbers"]
        self.assertGreater(dirty[1] / clean[1], 1000.0,
                           "one 0.4 cm^-1 mode should move the UNTRIMMED value enormously")
        self.assertAlmostEqual(dirty[2], clean[1], places=3,
                               msg="trimming one mode should recover the clean k=1 value")

    def test_the_squared_definition_survives(self):
        """🔴 lambda ∝ nu^2. The unsquared ratio understates the spread by a square root."""
        o = curvature.observables(self.FREQS)
        ratio = o["nu_max_cm1"] / o["nu_min_cm1"]
        self.assertAlmostEqual(o["trimmed_condition_numbers"][1], ratio ** 2, places=6)
        self.assertIn("SQUARE of a frequency ratio", o["_condition_number_definition"])

    def test_sub_five_modes_are_a_convergence_diagnostic_not_discarded(self):
        """🟢 RELABEL, DO NOT DISCARD -- the same shape as the MTD dissociation count."""
        o = curvature.observables(self.WITH_ARTEFACT)
        self.assertEqual(o["n_convergence_artefacts"], 1)
        joined = " ".join(o["warnings"])
        self.assertIn("OPTIMISATION LIKELY DID NOT CONVERGE", joined)
        self.assertIn("NOT discarded", joined)

    def test_it_records_that_no_floor_is_applied(self):
        self.assertIn("no noise floor is applied", curvature.observables(self.FREQS)["_no_floor"])

    def test_imaginary_modes_are_excluded_and_counted(self):
        o = curvature.observables([-105.0] + self.FREQS)
        self.assertEqual(o["n_imaginary"], 1)
        self.assertAlmostEqual(o["nu_min_cm1"], 31.2,
                               msg="an imaginary mode leaked into nu_min -- it is negative and "
                                   "would become the minimum")

    def test_an_empty_frequency_list_gives_none_not_zero(self):
        o = curvature.observables([])
        self.assertIsNone(o["nu_min_cm1"])
        self.assertIsNone(o["n_soft_curve"])
        self.assertIsNone(o["trimmed_condition_numbers"])
        self.assertIn("held out of the correlation, not entered as zero", " ".join(o["warnings"]))


class TestImaginaryModeExpectationIsDirectional(unittest.TestCase):
    """🔴 SAME SPECIES LIST, OPPOSITE EXPECTATION. A minimum wants 0; a TS wants exactly 1."""

    def test_an_imaginary_mode_on_a_supposed_minimum_is_flagged(self):
        o = curvature.observables([-90.0, 40.0, 900.0])
        v = curvature.imaginary_mode_verdict(o, expected_minimum=True, species_id="li_ec_cation")
        self.assertEqual(v["verdict"], "unexpected")
        joined = " ".join(v["warnings"])
        self.assertIn("imaginary_mode_on_a_supposed_minimum", joined)
        self.assertIn("stuck on a SYMMETRY ELEMENT", joined)

    def test_the_same_count_is_correct_for_a_transition_state(self):
        o = curvature.observables([-90.0, 40.0, 900.0])
        v = curvature.imaginary_mode_verdict(o, expected_minimum=False, species_id="R-A")
        self.assertEqual(v["verdict"], "as_expected")
        self.assertEqual(v["warnings"], [])

    def test_a_clean_minimum_passes(self):
        v = curvature.imaginary_mode_verdict(curvature.observables([40.0, 900.0]),
                                             expected_minimum=True, species_id="x")
        self.assertEqual(v["verdict"], "as_expected")

    def test_a_ts_with_no_imaginary_mode_is_flagged_too(self):
        v = curvature.imaginary_mode_verdict(curvature.observables([40.0, 900.0]),
                                             expected_minimum=False, species_id="R-A")
        self.assertEqual(v["verdict"], "unexpected")

    def test_an_unavailable_count_is_none_not_zero(self):
        v = curvature.imaginary_mode_verdict({}, expected_minimum=True, species_id="x")
        self.assertIsNone(v["verdict"])
        self.assertIn("Not 'zero'", " ".join(v["warnings"]))


class TestTheCorrelation(unittest.TestCase):
    def _recs(self, n=8, noisy=False):
        out = []
        for i in range(n):
            out.append({"species_id": "s%d" % i,
                        "hessian_condition_number": 10.0 * (i + 1) ** 2,
                        "nu_min_cm1": 200.0 / (i + 1),
                        "n_soft": i,
                        "opt_cycles": (37 - i * 3) if noisy else (10 + 4 * i),
                        "core_hours": (5.0 + 2.0 * i)})
        return out

    def test_a_monotonic_relationship_is_detected_by_spearman(self):
        c = curvature.correlate(self._recs(), "hessian_condition_number", "core_hours")
        self.assertEqual(c["n_used"], 8)
        self.assertGreater(c["spearman_rho"], 0.95)

    def test_spearman_is_reported_alongside_pearson(self):
        """The predictor spans orders of magnitude; Pearson is dominated by its largest point."""
        c = curvature.correlate(self._recs(), "hessian_condition_number", "core_hours")
        self.assertIsNotNone(c["pearson_r"])
        self.assertIsNotNone(c["spearman_rho"])
        self.assertNotAlmostEqual(c["pearson_r"], c["spearman_rho"], places=3)

    def test_an_anticorrelation_is_not_reported_as_agreement(self):
        c = curvature.correlate(self._recs(noisy=True), "hessian_condition_number", "opt_cycles")
        self.assertLess(c["spearman_rho"], -0.95)

    def test_a_species_missing_a_value_is_dropped_and_named_never_imputed(self):
        recs = self._recs()
        recs[2]["hessian_condition_number"] = None
        recs[5].pop("core_hours")
        c = curvature.correlate(recs, "hessian_condition_number", "core_hours")
        self.assertEqual(c["n_used"], 6)
        self.assertEqual(c["n_dropped"], 2)
        self.assertEqual(sorted(d["species_id"] for d in c["dropped"]), ["s2", "s5"])
        self.assertIn("correlation_sample_reduced", " ".join(c["warnings"]))
        self.assertIn("NOT the full batch", " ".join(c["warnings"]))

    def test_too_few_points_gives_none_and_says_so(self):
        c = curvature.correlate(self._recs(n=2), "n_soft", "core_hours")
        self.assertIsNone(c["spearman_rho"])
        self.assertIn("correlation_not_computed", " ".join(c["warnings"]))

    def test_no_pass_fail_threshold_is_hard_coded(self):
        """🔴 C-3's lesson: hard-coding a cutoff now is how -100 cm^-1 got into M2."""
        c = curvature.correlate(self._recs(), "n_soft", "core_hours")
        self.assertIsNone(c["verdict"])
        self.assertIn("judgement for proposer5", c["_no_threshold"])


class TestTheU55Panel(unittest.TestCase):
    def _recs(self, n=6):
        return [{"species_id": "s%d" % i,
                 "curvature": curvature.observables(
                     [6.0 + i, 30.0 + 2 * i, 70.0 + i, 900.0 + 10 * i]),
                 "opt_cycles": 12 + 5 * i, "core_hours": 3.0 + 1.5 * i} for i in range(n)]

    def test_it_covers_the_ladders_against_two_responses(self):
        p = curvature.u55_panel(self._recs())
        self.assertEqual(len(p["correlations"]), 18)   # (1 nu_min + 3 kappa + 5 n_soft) x 2
        preds = set(c["predictor"] for c in p["correlations"])
        self.assertIn("kappa_k1", preds)
        self.assertIn("kappa_k3", preds)
        self.assertIn("n_soft_x50", preds)
        self.assertEqual(sorted(set(c["response"] for c in p["correlations"])),
                         ["core_hours", "opt_cycles"])

    def test_kappa_stability_is_computed_not_left_to_a_reader(self):
        """🟢 The predictor's own falsifier: present only at k=1 means one artefact mode."""
        p = curvature.u55_panel(self._recs())
        st = p["kappa_stability"]
        self.assertIn("core_hours", st["per_response"])
        self.assertEqual(sorted(st["per_response"]["core_hours"]["rho_by_k"]), [1, 2, 3])
        self.assertIn("SPURIOUS", st["_rule"])
        self.assertIn("no cutoff is hard-coded", st["_no_threshold"])

    def test_the_primary_is_pre_registered_with_its_date_and_rationale(self):
        """🔒 A commitment belongs in the ARTEFACT, not in prose someone must be trusted about."""
        pr = curvature.u55_panel(self._recs())["pre_registration"]
        self.assertEqual(pr["date"], "2026-08-19")
        self.assertTrue(pr["registered_before_any_data"])
        self.assertEqual(pr["primary_predictor"], "kappa_k2")
        self.assertEqual(pr["primary_response"], "opt_cycles")
        self.assertIn("confounds", pr["rationale_response"])
        self.assertIn("minimal trim", pr["rationale_trim"])

    def test_the_6000x_figure_is_recorded_as_NOT_having_chosen_k(self):
        """🔴 It came from a SYNTHETIC fixture with a deliberately inserted mode.

        Using it to pick k would be ADR-077's "a fit is not a confirmation". The caveat lives in
        the pre-registration record itself so it travels with the commitment.
        """
        pr = curvature.u55_panel(self._recs())["pre_registration"]
        note = pr["🔴 not_chosen_from_data"]
        self.assertIn("SYNTHETIC", note)
        self.assertIn("NOT used to choose k", note)
        self.assertIn("not a confirmation", note)

    def test_the_primary_is_shown_IN_its_ladder_not_naked(self):
        p = curvature.u55_panel(self._recs())
        self.assertEqual(p["primary"]["predictor"], "kappa_k2")
        self.assertEqual(sorted(p["primary_ladder_context"]), [1, 2, 3])
        for k in (1, 2, 3):
            self.assertEqual(p["primary_ladder_context"][k]["predictor"], "kappa_k%d" % k)
        self.assertIn("never read naked", p["_read_the_primary_in_its_ladder"])

    def test_the_primary_verdict_is_NOT_a_boolean(self):
        """🔴 A boolean needs a cutoff on rho, and a hard-coded cutoff is how -100 got into M2.

        State the rule and show the numbers; do not evaluate the rule.
        """
        p = curvature.u55_panel(self._recs())
        self.assertIsNone(p["primary_verdict"])
        self.assertEqual(p["🔒 primary_verdict_is_a_judgement_for"], "proposer")
        self.assertIn("SPURIOUS", p["pre_registration"]["interpretation_rule"])

    def test_a_missing_primary_is_shouted_about(self):
        """If the predictor set ever changes, the pre-registration stops pointing at anything."""
        import types
        recs = self._recs()
        p = curvature.u55_panel(recs)
        self.assertIsNotNone(p["primary"])
        # simulate the predictor vanishing
        saved = curvature.PRE_REGISTRATION["primary_predictor"]
        curvature.PRE_REGISTRATION["primary_predictor"] = "kappa_k99"
        try:
            p2 = curvature.u55_panel(recs)
            self.assertIsNone(p2["primary"])
            self.assertIn("primary_correlation_absent", " ".join(p2["warnings"]))
        finally:
            curvature.PRE_REGISTRATION["primary_predictor"] = saved

    def test_the_n_soft_curve_is_labelled_calibration_only(self):
        """🔴 Selecting x on a dataset then quoting its rho FROM THAT DATASET is circular."""
        role = curvature.u55_panel(self._recs())["n_soft_curve_role"]
        self.assertEqual(role["role"], "CALIBRATION ONLY")
        self.assertIn("validate", role["does_not"],
                      "the role field no longer says what the curve does NOT do")
        self.assertIn("inflated by the selection", role["🔴 may_not_be_quoted_as"])
        self.assertIn("SECOND dataset", role["validation_requires"])

    def test_the_reading_order_puts_the_primary_first_not_a_stop_gate(self):
        p = curvature.u55_panel(self._recs())
        self.assertIn("pre-registered PRIMARY", p["_readability"])
        note = p["_read_the_primary_in_its_ladder"]
        self.assertIn("Not a stop-gate", note)
        self.assertIn("FRAMING", note)
        self.assertIn("never skipped", note)

    def test_the_headline_warns_it_is_a_pointer_not_a_result(self):
        """🔴 Picking the largest of 18 coefficients is a multiple-comparisons selection."""
        p = curvature.u55_panel(self._recs())
        self.assertIn("strongest_predictor", p["headline"])
        self.assertIn("multiple-comparisons", p["headline"]["🔴"])

    def test_the_readability_note_says_to_read_stability_first(self):
        p = curvature.u55_panel(self._recs())
        self.assertIn("Reading order", p["_readability"])
        self.assertIn("n_convergence_artefacts", p["_readability"])

    def _recs_with_one_artefact_species(self):
        """s0's lowest real mode is 0.5 cm^-1 (< CONVERGENCE_ARTEFACT_CM1 = 5.0): step (2) of
        the reading order exists precisely to flag species like this one."""
        recs = self._recs()
        recs[0] = {"species_id": "s0",
                   "curvature": curvature.observables([0.5, 30.0, 70.0, 900.0]),
                   "opt_cycles": 12, "core_hours": 3.0}
        return recs

    def test_n_convergence_artefacts_by_species_is_surfaced_at_panel_level(self):
        """🔴 B-5 (HANDOFF_CODER6 §B-5 / docs/05_STATE.md §0-k): step (2) of `_readability`'s
        own stated reading order NAMES `n_convergence_artefacts` but, before this field
        existed, the panel never HANDED it to the reader -- it lived only inside each species'
        own `curvature` record elsewhere in the report. A reader following the panel's own
        instructions had to leave the panel to reconstruct this by hand. It must be directly
        readable from `u55_panel`'s own output, at the same level as `primary`."""
        p = curvature.u55_panel(self._recs_with_one_artefact_species())
        by_species = p["n_convergence_artefacts_by_species"]
        self.assertEqual(by_species["s0"], 1)
        for i in range(1, 6):
            self.assertEqual(by_species["s%d" % i], 0)

    def test_species_with_convergence_artefacts_is_the_step_2_shortlist(self):
        """A reader should not have to filter `n_convergence_artefacts_by_species` themselves
        for the common case -- the panel does it once, here."""
        p = curvature.u55_panel(self._recs_with_one_artefact_species())
        self.assertEqual(p["species_with_convergence_artefacts"], ["s0"])

    def test_zero_artefact_species_do_not_appear_in_the_shortlist(self):
        p = curvature.u55_panel(self._recs())
        self.assertEqual(p["species_with_convergence_artefacts"], [])
        self.assertEqual(len(p["n_convergence_artefacts_by_species"]), 6)

    def test_dropped_species_reach_the_TOP_LEVEL_summary(self):
        """🔴 If 6 of 23 silently drop out, every coefficient is on 17 and nothing says so."""
        recs = self._recs()
        recs[0]["curvature"] = curvature.observables([])
        recs[1]["core_hours"] = None
        p = curvature.u55_panel(recs)
        self.assertEqual(p["n_species_in"], 6)
        self.assertEqual(p["n_species_complete"], 4)
        self.assertEqual(p["n_species_dropped"], 2)
        self.assertEqual(sorted(p["species_dropped"]), ["s0", "s1"])
        self.assertIn("u55_panel_incomplete", " ".join(p["warnings"]))

    def test_the_question_it_answers_is_stated_in_its_own_output(self):
        p = curvature.u55_panel(self._recs())
        self.assertIn("U-55", p["question"])
        self.assertIn("artefact of a bad start", p["question"])

    def test_temperature_independence_is_recorded_because_it_is_the_reason_for_the_switch(self):
        p = curvature.u55_panel(self._recs())
        self.assertIn("TEMPERATURE-INDEPENDENT", p["_temperature_independent"])
        self.assertIn("1.41-1.70", p["_temperature_independent"])

    def test_coverage_advantage_over_a_rate_is_recorded(self):
        p = curvature.u55_panel(self._recs())
        self.assertIn("happened to come apart", p["_coverage"])


class TestDissociationIsRelabelledNotDeleted(unittest.TestCase):
    """🟢 The count survives as SEARCH HYGIENE. 🔴 Its label changes, in the FIELD NAME."""

    def _structures(self):
        import os
        path = os.path.join(context.REPO_ROOT, "tests", "fixtures",
                            "xtb_metadyn_li_ec_cation.trj")
        if not os.path.exists(path):
            self.skipTest("fixture absent")
        with open(path) as fh:
            return [f["atoms"] for f in conformers.parse_trajectory(fh.read())]

    def test_the_caveat_is_in_the_field_name_not_only_in_a_doc(self):
        """🔴 A field name travels into every downstream table; a doc does not."""
        self.assertIn("uncontrolled_effective_temperature", conformers.DISSOCIATION_FIELD)
        h = conformers.dissociation_hygiene(self._structures(), 1,
                                            temperature_measured_k=489.0,
                                            temperature_requested_k=400.0)
        self.assertIn(conformers.DISSOCIATION_FIELD, h)

    def test_it_declares_it_is_not_a_floppiness_measurement(self):
        h = conformers.dissociation_hygiene(self._structures(), 1, temperature_measured_k=489.0)
        self.assertFalse(h["is_a_floppiness_measurement"])
        self.assertEqual(h["purpose"], "search hygiene")
        self.assertIn("curvature.u55_panel", h["floppiness_is_measured_by"])

    def test_the_label_names_the_irreducible_temperature_problem(self):
        self.assertIn("IRREDUCIBLE", conformers.DISSOCIATION_LABEL)
        self.assertIn("NOT a floppiness measurement", conformers.DISSOCIATION_LABEL)

    def test_counting_without_a_measured_temperature_is_flagged(self):
        h = conformers.dissociation_hygiene(self._structures(), 1)
        self.assertIn("NO measured temperature", " ".join(h["warnings"]))

    def test_the_underlying_classification_split_is_unchanged(self):
        """🔒 dissociated vs fragmented, and unclassifiable held out, are unaffected."""
        h = conformers.dissociation_hygiene(self._structures(), 1, temperature_measured_k=489.0)
        self.assertEqual(h["n_structures"], 20)
        self.assertEqual(h["intact"] + h[conformers.DISSOCIATION_FIELD]
                         + h["fragmented"] + h["unclassified"], 20)
        self.assertIsNotNone(h["usable_fraction"])


class TestTheMeasuredLiXCutoffChangedAVerdict(unittest.TestCase):
    """🔴 U-67 CLOSED at 2.75 Å [MEASURED, MLIP RDF first minimum], widening Li–O by 0.35 Å.

    🔴 EVERY Layer-I verdict computed under the old 2.4 Å table is provisional and must be
    RECOMPUTED, not grandfathered. This test shows the flip is real rather than theoretical, on
    the real metadynamics trajectory.
    """

    def _structures(self):
        import os
        path = os.path.join(context.REPO_ROOT, "tests", "fixtures",
                            "xtb_metadyn_li_ec_cation.trj")
        if not os.path.exists(path):
            self.skipTest("fixture absent")
        with open(path) as fh:
            return [f["atoms"] for f in conformers.parse_trajectory(fh.read())]

    def test_the_cutoff_is_the_measured_value_not_the_placeholder(self):
        from sei_pilot import config
        li = config.graph_layers()["layer_I"]
        self.assertEqual(li["contact_cutoff_ang"]["Li-O"], 2.75)
        self.assertIn("[MEASURED]", li["_provenance"])
        self.assertNotIn("[PLACEHOLDER-ESTIMATE]", li["_provenance"].split("SUPERSEDES")[0])

    def test_it_is_not_element_resolved_and_says_so(self):
        """🔴 The user gave Li–X generically. Nobody may assume a per-element table exists."""
        from sei_pilot import config
        li = config.graph_layers()["layer_I"]
        self.assertIn("GENERICALLY", li["_not_element_resolved"])
        self.assertEqual(len(set(li["contact_cutoff_ang"].values())), 1)

    def test_the_provenance_records_that_the_old_source_no_longer_exists(self):
        """The old string named P1 and P2 — and P2 was deleted (ADR-033)."""
        from sei_pilot import config
        self.assertIn("P2 WAS DELETED",
                      config.graph_layers()["layer_I"]["_provenance"])

    def test_a_verdict_actually_flips_on_the_real_trajectory(self):
        """🔴 Not theoretical. 2.4 Å gave 19 intact / 1 dissociated; 2.75 Å gives 20 / 0."""
        structures = self._structures()
        now = conformers.dissociation_hygiene(structures, 1, temperature_measured_k=489.0)
        self.assertEqual(now["intact"], 20)
        self.assertEqual(now[conformers.DISSOCIATION_FIELD], 0)
        # and the old table would have called one of them dissociated
        old = {"layer_I": {"cations": ["Li"],
                           "contact_cutoff_ang": {"Li-O": 2.4, "default": 2.5},
                           "sensitivity_delta_ang": 0.2}}
        n_diss = sum(1 for st in structures
                     if conformers.classify_complex(st, 1, layers=old)["classification"]
                     == conformers.CLASS_DISSOCIATED)
        self.assertEqual(n_diss, 1,
                         "the old 2.4 Å table no longer flips any verdict -- if that is true the "
                         "'recompute, do not grandfather' instruction has lost its instance")

    def test_the_invalidation_notice_travels_in_the_config(self):
        from sei_pilot import config
        self.assertIn("MUST BE RECOMPUTED",
                      config.graph_layers()["layer_I"]["_invalidates"])


class TestSymmetryTraceIsInstrumentationNotAssumption(unittest.TestCase):
    """🔒 ORDERED AS INSTRUMENTATION. Nothing is perturbed; whether symmetry broke is MEASURED.

    🔴 The defect it closes: arm 1's GFN2 pre-optimisation does NOT break the symmetry (measured —
    every distance moved, the exact degeneracy did not), so we were relying on the MTD's random
    velocities as a SIDE EFFECT with nothing recording whether it happened.
    """

    def _ideal(self):
        import os
        from sei_pilot import seeding
        with open(os.path.join(context.PKG_ROOT, "inputs", "p5_species",
                               "li_ec_cation.xyz")) as fh:
            return seeding.read_xyz(fh.read())

    def _broken(self):
        return [(s, x + (0.13 if i % 2 else -0.21), y - 0.08 * i, z + 0.06 * i)
                for i, (s, x, y, z) in enumerate(self._ideal())]

    def test_it_measures_all_three_checkpoints(self):
        self.assertEqual(conformers.SYMMETRY_CHECKPOINTS,
                         ("preopt_input", "post_mtd_conformer", "final_dft_geometry"))

    def test_a_persisting_symmetry_is_reported_as_a_failed_reliance(self):
        t = conformers.symmetry_trace(
            {"preopt_input": self._ideal(), "post_mtd_conformer": self._ideal(),
             "final_dft_geometry": self._ideal()}, species_id="li_ec_cation")
        self.assertFalse(t["symmetry_broke"])
        joined = " ".join(t["warnings"])
        self.assertIn("symmetry_persisted", joined)
        self.assertIn("DID NOT HOLD", joined)
        self.assertIn("generally a SADDLE", joined)

    def test_a_broken_symmetry_is_recorded_as_broken(self):
        t = conformers.symmetry_trace(
            {"preopt_input": self._ideal(), "post_mtd_conformer": self._ideal(),
             "final_dft_geometry": self._broken()}, species_id="li_ec_cation")
        self.assertTrue(t["symmetry_broke"])
        self.assertEqual(t["warnings"], [])

    def test_missing_checkpoints_give_none_not_broke(self):
        """🔴 Rule 18: 'cannot be told' must not fall toward 'it broke'."""
        t = conformers.symmetry_trace({"preopt_input": self._ideal()}, species_id="x")
        self.assertIsNone(t["symmetry_broke"])
        self.assertIn("Not 'it broke'", " ".join(t["warnings"]))

    def test_nothing_symmetric_at_the_start_is_not_a_breaking_failure(self):
        t = conformers.symmetry_trace(
            {"preopt_input": self._broken(), "final_dft_geometry": self._broken()},
            species_id="x")
        self.assertFalse(t["symmetry_broke"])
        self.assertIn("NOT because breaking failed", " ".join(t["warnings"]))

    def test_it_declares_it_perturbs_nothing(self):
        t = conformers.symmetry_trace({"preopt_input": self._ideal(),
                                       "final_dft_geometry": self._ideal()}, species_id="x")
        self.assertIn("NOTHING IS PERTURBED", t["_is_instrumentation_only"])
        self.assertIn("METHODOLOGY change and is not taken", t["_is_instrumentation_only"])

    def test_it_points_at_the_imaginary_mode_as_the_direct_signature(self):
        t = conformers.symmetry_trace({"preopt_input": self._ideal(),
                                       "final_dft_geometry": self._ideal()}, species_id="x")
        self.assertIn("imaginary_mode_verdict", t["_what_a_persisting_flag_means"])


if __name__ == "__main__":
    unittest.main()
