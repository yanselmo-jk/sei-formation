"""B0-D's 19 species, B0-F's 3 reactions, role->index mapping, and the bound-species rule.

These are the objects the rulings of 2026-08-19 defined. The tests pin them so that a later edit
to the generating rules cannot silently change the batch.

🔴 The role tests run against the REAL `inputs/li_ec_radical_*.xyz`, and the expected role
   assignment is taken from `02_METHOD_SPEC.md` §39.4(g)'s hand-verified bond table -- not from
   what this code happens to produce. Rule 22: an expected value derived from our own code tests
   only that the code has not changed.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import b0_species, bound, config, roles, seeding, units

INPUTS = os.path.join(context.PKG_ROOT, "inputs")


def _read_xyz(name):
    with open(os.path.join(INPUTS, name)) as fh:
        return seeding.read_xyz(fh.read())


# =============================================================================================
# B0-D — the 19
# =============================================================================================

class TestB0DSpeciesSet(unittest.TestCase):
    """🔴 The ruling was '19 species, bare Li+ IN, Li(PF6)3(2-) OUT'. Pin all three claims."""

    def setUp(self):
        self.sp = b0_species.enumerate_species()
        self.ids = [s["id"] for s in self.sp]

    def test_there_are_exactly_nineteen(self):
        self.assertEqual(len(self.sp), 19,
                         "the ruling said 19; the rules now generate %d" % len(self.sp))

    def test_the_exact_id_set_is_pinned(self):
        self.assertEqual(sorted(self.ids), sorted([
            "li_cation",
            "li_ec_cation", "li_emc_cation", "li_pf6_neutral",
            "li_ec2_cation", "li_ec_emc_cation", "li_ec_pf6_neutral",
            "li_emc2_cation", "li_emc_pf6_neutral", "li_pf62_anion",
            "li_ec3_cation", "li_ec2_emc_cation", "li_ec2_pf6_neutral",
            "li_ec_emc2_cation", "li_ec_emc_pf6_neutral", "li_ec_pf62_anion",
            "li_emc3_cation", "li_emc2_pf6_neutral", "li_emc_pf62_anion",
        ]))

    def test_bare_li_is_in(self):
        """The n = 0 reference state for every ligand-exchange energy. Free, and load-bearing."""
        self.assertIn("li_cation", self.ids)
        bare = [s for s in self.sp if s["n_ligands"] == 0]
        self.assertEqual(len(bare), 1)
        self.assertEqual(bare[0]["charge"], 1)

    def test_the_dianion_is_out_and_its_reason_travels_with_it(self):
        """🔴 A removed option travelling without its removal reason has cost two revisions."""
        self.assertNotIn("li_pf63_anion2", self.ids)
        self.assertFalse([s for s in self.sp if s["charge"] <= -2])
        exc = b0_species.excluded_species()
        self.assertEqual(len(exc), 1)
        self.assertIn("NOT A BOUND SPECIES", exc[0]["reason"])
        self.assertIn("DIFFERENT failure", exc[0]["reason"])

    def test_the_multiset_arithmetic_is_what_it_claims(self):
        counts = dict((n, sum(1 for s in self.sp if s["n_ligands"] == n)) for n in (0, 1, 2, 3))
        self.assertEqual(counts, {0: 1, 1: 3, 2: 6, 3: 9},
                         "1+3+6+10 = 20 multisets, minus the one exclusion at n=3 = 19")

    def test_charge_is_computed_from_composition_never_typed(self):
        """A new ligand must not be able to inherit a wrong charge by copy-paste."""
        for s in self.sp:
            n_pf6 = s["composition"].get("PF6", 0)
            self.assertEqual(s["charge"], 1 - n_pf6,
                             "%s: charge %d but %d PF6" % (s["id"], s["charge"], n_pf6))

    def test_every_member_is_a_closed_shell_singlet(self):
        for s in self.sp:
            self.assertEqual(s["multiplicity"], 1, s["id"])

    def test_every_species_carries_the_bound_check_not_only_the_anions(self):
        """🟢 BROADENED BY RULING. This test previously pinned `charge < 0` and was WRONG.

        proposer5 rejected its own earlier framing: `charge < 0` is a PROXY, and the property
        wanted is "is the highest occupied orbital BOUND?". 🔴 The classic unbound case in our
        chemistry is a RADICAL ANION -- gas-phase EC has a NEGATIVE adiabatic electron affinity,
        which is why ADR-029 insists on diffuse functions -- so the open-shell stratum's NEUTRAL
        doublets are exactly where SOMO boundness is live, and `charge < 0` skips every one.
        """
        for s in b0_species.all_species():
            self.assertTrue(s["bound_check_required"],
                            "%s (charge %+d, mult %d) is not bound-checked. Reading the "
                            "HOMO/SOMO is free -- it is in every log."
                            % (s["id"], s["charge"], s["multiplicity"]))

    def test_the_neutral_open_shell_species_are_checked_which_charge_lt_0_would_skip(self):
        neutral_doublets = [s for s in b0_species.open_shell_species()
                            if s["charge"] == 0 and s["multiplicity"] == 2]
        self.assertEqual(len(neutral_doublets), 4)
        for s in neutral_doublets:
            self.assertTrue(s["bound_check_required"], s["id"])

    def test_the_coder_extension_is_labelled_as_one_in_the_config(self):
        """🔴 The ruling named ONE species; applying the rule to all anions is my extension.

        It must be visible as an extension in the data, not buried in code, so proposer5 can
        narrow it in one place if they want it narrowed.
        """
        note = config.load("b0_species.json")["bound_species_rule"]["_applies_to_note"]
        self.assertIn("CODER EXTENSION", note)
        self.assertIn("FLAGGED FOR CONFIRMATION", note)

    def test_the_set_is_derived_not_typed(self):
        """Two copies of one truth is the shape that has cost this project six rounds."""
        with open(os.path.join(context.PKG_ROOT, "sei_pilot", "b0_species.py")) as fh:
            src = fh.read()
        self.assertNotIn("li_ec_emc_pf6", src,
                         "a species id is typed into the derivation module -- the list and the "
                         "rule are now two sources of one truth")


class TestOpenShellStratum(unittest.TestCase):
    """🔴 19 -> 23. The 19 are all closed-shell and HALF THE PRODUCTION POOL IS OPEN-SHELL."""

    def test_there_are_four_open_shell_members_and_twenty_three_in_total(self):
        self.assertEqual(len(b0_species.open_shell_species()), 4)
        self.assertEqual(len(b0_species.all_species()), 23)
        self.assertEqual(len(b0_species.enumerate_species()), 19)

    def test_they_are_neutral_doublets(self):
        for s in b0_species.open_shell_species():
            self.assertEqual(s["charge"], 0, s["id"])
            self.assertEqual(s["multiplicity"], 2, s["id"])

    def test_they_supply_the_reactants_all_three_b0f_reactions_need(self):
        """🟢 'All three needed conformer-searched open-shell reactants regardless.'"""
        ids = set(s["id"] for s in b0_species.all_species())
        for r in config.load("b0_reactions.json")["reactions"]:
            self.assertIn(r["reactant_species"], ids,
                          "%s's reactant %r is in neither stratum -- the reaction is unrunnable, "
                          "which is exactly the R-C blocker"
                          % (r["id"], r["reactant_species"]))

    def test_one_of_them_is_production_sized(self):
        big = [s for s in b0_species.open_shell_species()
               if s["n_atoms"] and 20 <= s["n_atoms"] <= 30]
        self.assertTrue(big, "no open-shell member is production-sized (20-30 atoms)")

    def test_every_species_is_tagged_with_its_stratum(self):
        for s in b0_species.all_species():
            self.assertIn(s["stratum"], ("closed_shell", "open_shell"), s["id"])
        groups = b0_species.by_stratum()
        self.assertEqual(len(groups["closed_shell"]), 19)
        self.assertEqual(len(groups["open_shell"]), 4)

    def test_the_config_says_why_the_stratum_exists(self):
        note = config.load("b0_species.json")["open_shell_stratum"]["_doc"]
        self.assertIn("failure mode", note)
        self.assertIn("stable=opt", note)

    def test_the_never_pool_rule_is_recorded_where_the_data_is(self):
        rule = config.load("b0_species.json")["open_shell_stratum"]["_reporting_rule"]
        self.assertIn("NEVER POOLED", rule)


class TestStrataAreReportedSeparately(unittest.TestCase):
    """🔴 'u_cheap MUST be reported SEPARATELY for the closed- and open-shell strata.'"""

    def _recs(self):
        cs = {"id": "li_ec_cation", "charge": 1, "bound_check_required": True}
        os_ = {"id": "li_ec_radical", "charge": 0, "bound_check_required": True}
        return [
            {"species_id": "li_ec_cation", "stratum": "closed_shell", "converged": True,
             "bound": bound.classify(cs, homo_energy_hartree=-0.30)},
            {"species_id": "li_ec2_cation", "stratum": "closed_shell", "converged": True,
             "bound": bound.classify(cs, homo_energy_hartree=-0.28)},
            {"species_id": "li_ec_radical", "stratum": "open_shell", "converged": False,
             "bound": bound.classify(os_, homo_energy_hartree=-0.10)},
            {"species_id": "li_ec2_radical", "stratum": "open_shell", "converged": True,
             "bound": bound.classify(os_, homo_energy_hartree=-0.09)},
        ]

    def test_each_stratum_gets_its_own_denominator_and_rate(self):
        p = bound.partition(self._recs())
        # Presence before value: a pooled result must FAIL readably, not KeyError (§0.2(a)).
        self.assertEqual(sorted(p["per_stratum"]), ["closed_shell", "open_shell"],
                         "the strata were not kept apart -- u_cheap and the convergence rate "
                         "would be pooled across two different populations, and the difference "
                         "between them is the measurement production needs")
        self.assertEqual(p["per_stratum"]["closed_shell"]["denominator"], 2)
        self.assertEqual(p["per_stratum"]["open_shell"]["denominator"], 2)
        self.assertAlmostEqual(p["per_stratum"]["closed_shell"]["convergence_rate"], 1.0)
        self.assertAlmostEqual(p["per_stratum"]["open_shell"]["convergence_rate"], 0.5)

    def test_no_pooled_rate_survives_to_hide_the_open_shell_difference(self):
        """🔴 ADR-087: a pooled `convergence_rate` used to live at the top level (0.75 for
        this fixture) directly below a note promising the rate is never pooled. It is now
        GONE under every name (`convergence_rate`, `n_converged`, `convergence_denominator`)
        -- not caveated. `per_stratum` is the only place a rate is computed, and it correctly
        keeps the open-shell stratum's 0.5 visible and distinct from closed-shell's 1.0."""
        p = bound.partition(self._recs())
        self.assertIn("open_shell", p["per_stratum"],
                      "there is no open-shell row to compare against")
        for pooled_name in ("convergence_rate", "n_converged", "convergence_denominator"):
            self.assertNotIn(pooled_name, p,
                             "%r must not exist at the top level (ADR-087)" % pooled_name)
        self.assertAlmostEqual(p["per_stratum"]["closed_shell"]["convergence_rate"], 1.0)
        self.assertAlmostEqual(p["per_stratum"]["open_shell"]["convergence_rate"], 0.5)

    def test_the_never_pool_instruction_travels_in_the_output(self):
        p = bound.partition(self._recs())
        self.assertIn("NEVER POOLED", p["_per_stratum_note"])


class TestADR087PooledFieldRemovedNotCaveated(unittest.TestCase):
    """🔴 ADR-087. `bound.partition()` shipped a pooled `convergence_rate` ten lines below
    `_per_stratum_note`'s own claim that the rate is "reported PER STRATUM and NEVER POOLED"
    -- the report refuted its own field, and a `_denominator_note` sitting on the SAME field
    but explaining a DIFFERENT axis (exclusions, not pooling) made it look vetted.

    🔒 Fixture choice matters (coder6's family (i), `HANDOFF_CODER6.md` §F): a 19/19 + 4/4
    fixture gives BOTH strata rate 1.0, so it cannot tell a correct (per-stratum) reading
    apart from a defective (pooled) one -- they'd agree by coincidence. The lead's own repro,
    19 closed-shell all converged + 0 of 4 open-shell converged, is used here on purpose:
    pooled = 19/23 = 0.826..., per-stratum = 1.0 / 0.0. Only THIS fixture distinguishes them.
    """

    def _recs(self):
        cs = {"id": "x", "charge": 0, "bound_check_required": True}
        os_ = {"id": "y", "charge": 0, "bound_check_required": True}
        recs = []
        for i in range(19):
            recs.append({"species_id": "cs_%d" % i, "stratum": "closed_shell",
                        "converged": True, "bound": bound.classify(cs, homo_energy_hartree=-0.3)})
        for i in range(4):
            recs.append({"species_id": "os_%d" % i, "stratum": "open_shell",
                        "converged": False, "bound": bound.classify(os_, homo_energy_hartree=-0.1)})
        return recs

    def test_this_fixture_is_the_discriminating_one(self):
        """Guard on the guard: fail loudly if this fixture stops being 19/19 + 0/4."""
        recs = self._recs()
        cs = [r for r in recs if r["stratum"] == "closed_shell"]
        os_ = [r for r in recs if r["stratum"] == "open_shell"]
        self.assertEqual((len(cs), sum(1 for r in cs if r["converged"])), (19, 19))
        self.assertEqual((len(os_), sum(1 for r in os_ if r["converged"])), (4, 0))

    def test_no_field_at_the_top_level_equals_the_dead_stratum_hiding_pooled_rate(self):
        """The pooled figure that used to hide the open-shell wipeout was 19/23 = 0.8260869565.
        Nothing in the return value may equal it -- under the old name or a new one."""
        p = bound.partition(self._recs())
        pooled_would_be = 19 / 23.0
        for key, value in p.items():
            if isinstance(value, float):
                self.assertNotAlmostEqual(
                    value, pooled_would_be,
                    msg="top-level field %r == the pooled rate the open-shell stratum's "
                        "complete failure would hide behind" % key)

    def test_per_stratum_shows_the_open_shell_wipeout_the_pooled_rate_would_have_hidden(self):
        p = bound.partition(self._recs())
        self.assertAlmostEqual(p["per_stratum"]["closed_shell"]["convergence_rate"], 1.0)
        self.assertAlmostEqual(p["per_stratum"]["open_shell"]["convergence_rate"], 0.0)

    def test_pooled_field_names_are_entirely_absent(self):
        p = bound.partition(self._recs())
        for pooled_name in ("convergence_rate", "n_converged", "convergence_denominator"):
            self.assertNotIn(pooled_name, p)


# =============================================================================================
# B0-F — the 3 reactions
# =============================================================================================

class TestB0FReactionSet(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load("b0_reactions.json")
        self.rx = self.cfg["reactions"]

    def test_three_reactions_two_methods_six_attempts(self):
        self.assertEqual(len(self.rx), 3)
        self.assertEqual(len(self.cfg["methods"]), 2)
        self.assertEqual(len(self.rx) * len(self.cfg["methods"]), 6)

    def test_exactly_one_reaction_is_production_sized_giving_two_of_six_attempts(self):
        """§39.13(a)#4: 2 of the 6 attempts must be production-sized (20-30 atoms)."""
        big = [r for r in self.rx if r["production_sized"]]
        self.assertEqual(len(big), 1)
        self.assertEqual(big[0]["id"], "R-C")
        self.assertTrue(20 <= big[0]["n_atoms"] <= 30, big[0]["n_atoms"])
        self.assertEqual(len(big) * len(self.cfg["methods"]), 2)

    def test_ra_and_rb_share_a_reactant_and_differ_only_in_the_coordinate(self):
        """🔴 R-B IS THE DESIGN: two real saddles on one PES."""
        ra = [r for r in self.rx if r["id"] == "R-A"][0]
        rb = [r for r in self.rx if r["id"] == "R-B"][0]
        self.assertEqual(ra["reactant_species"], rb["reactant_species"])
        self.assertNotEqual(ra["break"], rb["break"])
        self.assertEqual(ra["break"], [["O_ether", "C_sp3"]])
        self.assertEqual(rb["break"], [["O_ether", "C_carbonyl"]])

    def test_all_three_are_neutral_doublets(self):
        for r in self.rx:
            self.assertEqual(r["charge"], 0, r["id"])
            self.assertEqual(r["multiplicity"], 2, r["id"])

    def test_the_bake_off_runs_at_composite_not_level2(self):
        """🔴 C-11. P1 ran level2 throughout and never exercised the production protocol."""
        lv = self.cfg["level"]
        self.assertEqual(lv["geometry_and_hessian"], "level3")
        self.assertEqual(lv["single_point"], "level2")

    def test_omega_threshold_is_null_and_says_why(self):
        """🔴 C-3: do NOT hard-code Omega_min. `null` means report, do not gate."""
        acc = self.cfg["acceptance"]
        self.assertIsNone(acc["omega_threshold"])
        self.assertIn("DO NOT HARD-CODE", acc["_omega_threshold_note"])

    def test_acceptance_checks_exist_because_the_fallback_keys_on_them(self):
        """C-12: RT-1's fallback keyed on the exit status and therefore never fired."""
        self.assertTrue(self.cfg["acceptance"]["checks"])
        self.assertIn("NOT ON THE EXIT STATUS", self.cfg["acceptance"]["_doc"])

    def test_the_tripwire_is_six_hours_not_the_queue_default(self):
        self.assertEqual(self.cfg["tripwire"]["per_job_wall_h"], 6.0)
        self.assertIn("TRIPWIRE-ABORTED", self.cfg["tripwire"]["on_abort"])

    def test_break_lists_are_roles_that_the_perceiver_actually_knows(self):
        """A role nobody can perceive is a deck that can never be built."""
        for r in self.rx:
            for pair in r["break"] + r["form"]:
                for role in pair:
                    self.assertIn(roles.canonical_role(role), roles.ROLE_DEFINITIONS,
                                  "%s names role %r, which roles.perceive cannot assign"
                                  % (r["id"], role))


class TestArmThreeEmitsFrequencies(unittest.TestCase):
    """🟢 Arm 3 partially repairs U-60, which was recorded as unrecoverable."""

    def setUp(self):
        self.arm3 = config.load("b0_species.json")["arm3"]

    def test_the_frequency_list_is_required_not_just_the_energy(self):
        self.assertTrue(self.arm3["must_emit_frequency_list"])
        self.assertIn("CROSS-BASIS FREQUENCY COMPARISON",
                      self.arm3["_must_emit_frequency_list_why"])
        self.assertIn("U-60", self.arm3["_must_emit_frequency_list_why"])

    def test_the_honest_limit_travels_with_it(self):
        """⚠ Real modes, not the imaginary one the M2 window governs."""
        limit = self.arm3["_honest_limit"]
        self.assertIn("REAL modes", limit)
        self.assertIn("not the identical measurement", limit.lower())

    def test_it_records_why_the_harder_case_is_the_more_useful_one(self):
        note = self.arm3["_why_it_is_still_the_useful_case"]
        self.assertIn("most basis-sensitive", note)
        self.assertIn("refuted", note)

    def test_the_same_conformer_requirement_is_recorded_with_its_reason(self):
        """🔴 li_ec_cation r_high = 0.38 came from both levels starting from a bad guess."""
        self.assertIn("0.38", self.arm3["_why_same_start"])


class TestEpsilonScanRidesOnB0F(unittest.TestCase):
    """🟢 No separate tranche. engineer5 CHECKED the cost rather than assuming it: ZERO."""

    def setUp(self):
        self.cfg = config.load("b0_reactions.json")
        self.eps = self.cfg["epsilon_scan"]

    def test_it_brackets_the_two_pure_components(self):
        """🔴 THE DESIGN POINT: the true mixture value MUST lie between the pure components.

        ⟹ we do not need the correct mixed ε to BOUND the error of not knowing it.
        """
        self.assertEqual(self.eps["epsilon_values"], [3.0, 20.0, 90.0])
        self.assertIn("EMC", self.eps["_epsilon_meaning"]["3.0"])
        self.assertIn("EC", self.eps["_epsilon_meaning"]["90.0"])
        self.assertIn("MUST LIE BETWEEN", self.eps["_the_design_point"])

    def test_twenty_seven_single_points_on_already_computed_geometries(self):
        n = (len(self.cfg["reactions"]) * len(self.eps["states"])
             * len(self.eps["epsilon_values"]))
        self.assertEqual(n, 27)
        self.assertEqual(sorted(self.eps["states"]), ["product", "reactant", "ts"])

    def test_the_decision_threshold_is_recorded_with_the_scan(self):
        self.assertEqual(self.eps["decision_threshold_ev"], 0.05)

    def test_the_asymmetry_of_the_sp_only_bound_is_stated(self):
        """🔴 A SMALL spread bounds the full response; a LARGE one does not."""
        limits = " ".join(self.eps["_limits_to_carry_in_the_output"])
        self.assertIn("A SMALL spread BOUNDS the full response; a LARGE one DOES NOT", limits)
        self.assertIn("re-optimisation", limits)

    def test_the_cds_residual_is_declared_not_claimed_covered(self):
        limits = " ".join(self.eps["_limits_to_carry_in_the_output"])
        self.assertIn("CDS", limits)
        self.assertIn("surface tension", limits)
        self.assertIn("must not be claimed to be", limits)

    def test_the_ordering_ruling_is_recorded_where_the_scan_is(self):
        self.assertIn("BEFORE anyone sources SMD descriptors", self.eps["_run_it_first"])


class TestArmOneCoversOpenShell(unittest.TestCase):
    def setUp(self):
        self.cfg = config.load("b0_conformers.json")

    def test_arm_one_declares_the_open_shell_extension(self):
        self.assertIn("open_shell", self.cfg)
        self.assertIn("--uhf 1", self.cfg["open_shell"]["_doc"])

    def test_the_uhf_convention_is_written_down_where_it_is_used(self):
        """xtb counts unpaired electrons; Gaussian counts 2S+1. Confusing them is SILENT."""
        note = self.cfg["open_shell"]["uhf_from_multiplicity"]
        self.assertIn("multiplicity - 1", note)
        self.assertIn("SILENTLY", note)

    def test_the_gfn2_open_shell_limitation_is_flagged_unverified(self):
        """🔴 Do not claim GFN2 samples radical conformers as well as closed-shell ones."""
        caveat = self.cfg["open_shell"]["_gfn2_open_shell_caveat"]
        self.assertIn("[UNVERIFIED", caveat)
        self.assertIn("never sets the", caveat)


# =============================================================================================
# role -> index mapping
# =============================================================================================

class TestRolePerceptionOnTheRealFiles(unittest.TestCase):
    """Expected assignment from §39.4(g)'s hand-verified bond table, not from this code."""

    def setUp(self):
        self.atoms = _read_xyz("li_ec_radical_reactant.xyz")
        self.r = roles.perceive(self.atoms)

    def test_the_ring_is_perceived_as_the_spec_describes_it(self):
        # Presence before value: a role that vanishes must report as FAIL, not KeyError/ERROR.
        # §0.2(a) -- an ERROR usually means the experiment broke and is weak evidence either way.
        expected = {"C_carbonyl": [0], "O_ether": [1, 4], "C_sp3": [2, 3],
                    "O_carbonyl": [5], "Li": [10]}
        for role in sorted(expected):
            self.assertIn(role, self.r,
                          "role %r was not assigned to any atom of the reactant" % role)
        self.assertEqual(dict((k, self.r[k]) for k in expected), expected)

    def test_li_proximity_does_not_change_any_role(self):
        """🔴 Li sits 1.85 A from the carbonyl O. Counting that contact as a bond would give that
        oxygen two neighbours and it would be perceived as an ETHER oxygen.
        """
        moved = [(s, x, y, z) if s != "Li" else (s, x, y + 40.0, z)
                 for s, x, y, z in self.atoms]
        far = roles.perceive(moved)
        for role in ("C_carbonyl", "O_ether", "C_sp3", "O_carbonyl"):
            self.assertEqual(far.get(role), self.r.get(role),
                             "moving Li 40 A away changed the %s assignment (near=%r far=%r) -- "
                             "roles are being perceived on a graph that counts the ionic contact"
                             % (role, self.r.get(role), far.get(role)))

    def test_the_product_shows_the_ring_opened(self):
        """O2 loses its second C neighbour and stops being an ether oxygen. That is the reaction."""
        prod = roles.perceive(_read_xyz("li_ec_radical_product.xyz"))
        self.assertEqual(prod.get("O_ether"), [4])
        self.assertEqual(prod.get("O_carbonyl"), [1, 5])


class TestBondResolutionSurfacesAmbiguity(unittest.TestCase):
    def setUp(self):
        self.atoms = _read_xyz("li_ec_radical_reactant.xyz")

    def test_ra_resolves_to_the_alkyl_c_o(self):
        m = roles.resolve_bond(self.atoms, "O_ether", "C_sp3")
        self.assertIn((1, 2), m["candidates"])
        self.assertIn((4, 3), m["candidates"])
        self.assertEqual(m["selected"], (1, 2))

    def test_rb_resolves_to_the_carbonyl_c_o_and_is_a_different_bond(self):
        a = roles.resolve_bond(self.atoms, "O_ether", "C_sp3")["selected"]
        b = roles.resolve_bond(self.atoms, "O_ether", "C_carbonyl")["selected"]
        self.assertNotEqual(a, b,
                            "R-A and R-B resolved to the SAME bond -- the bake-off's central "
                            "comparison (two real saddles on one PES) would be a duplicate run")

    def test_two_candidates_are_reported_as_ambiguous_not_silently_chosen(self):
        """🔴 The mirror-equivalent pair is only equivalent in the idealised drawing.

        Once Li coordinates asymmetrically or C-9's kick has been applied they are different
        bonds, and picking one by list order would be picking a reaction coordinate by accident.
        """
        m = roles.resolve_bond(self.atoms, "O_ether", "C_sp3")
        self.assertTrue(m["ambiguous"])
        self.assertEqual(m["n_candidates"], 2)
        self.assertTrue(m["tie_break"])
        self.assertIn("role_pair_ambiguous", " ".join(m["warnings"]))

    def test_an_impossible_role_pair_is_unresolved_not_substituted(self):
        m = roles.resolve_bond(self.atoms, "O_ether", "Li")
        self.assertIsNone(m["selected"])
        self.assertEqual(m["n_candidates"], 0)
        self.assertIn("CANNOT be built", " ".join(m["warnings"]))

    def test_the_alkyl_alias_resolves_to_the_same_bond_as_sp3(self):
        """The spec says both 'alkyl C-O' and 'C(sp3)'. They are one role."""
        self.assertEqual(roles.resolve_bond(self.atoms, "O_ether", "C_alkyl")["selected"],
                         roles.resolve_bond(self.atoms, "O_ether", "C_sp3")["selected"])


class TestMappingIsRequired(unittest.TestCase):
    def setUp(self):
        self.atoms = _read_xyz("li_ec_radical_reactant.xyz")

    def test_a_mapping_is_produced_for_every_reaction_in_the_config(self):
        for r in config.load("b0_reactions.json")["reactions"]:
            if r["n_atoms"] != 11:
                continue    # R-C's geometry is built by the pipeline, not shipped
            m = roles.mapping_for(self.atoms, r["break"], r["form"])
            self.assertTrue(m["resolved"], "%s: %s" % (r["id"], m["warnings"]))
            roles.require_mapping(m)

    def test_no_mapping_raises_rather_than_warns(self):
        """🔴 'A deck without its mapping cannot be scored.' Raise, do not return a flag.

        Written as an explicit try/except rather than `assertRaises` so that a guard which has
        been softened reports a FAIL with a readable message, instead of whatever incidental
        exception the un-guarded code path happens to throw next (§0.2(a)).
        """
        for absent in (None, {}, {"resolved": False, "warnings": ["x"]}):
            try:
                roles.require_mapping(absent)
            except roles.MappingRequiredError:
                continue
            except Exception as exc:      # noqa: BLE001 -- the point is to name what happened
                self.fail("require_mapping(%r) raised %s instead of MappingRequiredError -- the "
                          "guard is gone and an unrelated error is standing in for it"
                          % (absent, type(exc).__name__))
            self.fail("require_mapping(%r) RETURNED. A deck without its mapping cannot be "
                      "scored, and a returned flag is a thing a caller may decline to read."
                      % (absent,))

    def test_an_unresolved_mapping_raises(self):
        m = roles.mapping_for(self.atoms, [["O_ether", "Li"]], [])
        self.assertFalse(m["resolved"])
        self.assertRaises(roles.MappingRequiredError, roles.require_mapping, m)

    def test_the_mapping_carries_its_own_definitions_and_the_ionic_caveat(self):
        m = roles.mapping_for(self.atoms, [["O_ether", "C_sp3"]], [])
        self.assertIn("O_ether", m["role_definitions"])
        self.assertTrue(m["ionic_contacts_excluded"])
        self.assertIn("1.85", m["_ionic_note"])


# =============================================================================================
# the bound-species rule
# =============================================================================================

ANION = {"id": "li_pf62_anion", "charge": -1, "bound_check_required": True}
CATION = {"id": "li_ec2_cation", "charge": 1, "bound_check_required": False}
#: 🔒 `bound_check_required: False` is now reachable ONLY by narrowing the config rule.
#: Kept as a fixture so the narrowing path stays tested.


class TestBoundSpeciesRule(unittest.TestCase):
    def test_a_positive_homo_is_unbound_and_is_not_a_convergence_failure(self):
        """🔴 The distinction the whole rule exists for."""
        c = bound.classify(ANION, homo_energy_hartree=+0.0182)
        self.assertEqual(c["status"], bound.STATUS_UNBOUND)
        self.assertFalse(c["is_bound"])
        self.assertFalse(c["included_in_u_cheap_statistics"])
        self.assertFalse(c["counts_as_convergence_failure"],
                         "an unbound species was counted as a protocol failure -- that inflates "
                         "every budget derived from B0-D")
        self.assertIn("NOT counted as a convergence failure", " ".join(c["warnings"]))

    def test_a_negative_homo_is_bound_and_stays_in_the_statistics(self):
        c = bound.classify(ANION, homo_energy_hartree=-0.0741)
        self.assertEqual(c["status"], bound.STATUS_BOUND)
        self.assertTrue(c["included_in_u_cheap_statistics"])

    def test_an_unread_diagnostic_is_none_and_holds_the_species_out(self):
        """🔴 Rule 18. An unread diagnostic must not certify a species as bound."""
        c = bound.classify(ANION, homo_energy_hartree=None)
        self.assertIsNone(c["is_bound"])
        self.assertEqual(c["status"], bound.STATUS_NOT_CHECKED)
        self.assertFalse(c["included_in_u_cheap_statistics"])
        self.assertIn("bound_check_not_performed", " ".join(c["warnings"]))

    def test_a_cation_is_not_claimed_bound_but_stays_in_the_statistics(self):
        c = bound.classify(CATION)
        self.assertIsNone(c["is_bound"], "saying 'bound' for a cation claims a test we never ran")
        self.assertTrue(c["included_in_u_cheap_statistics"])
        self.assertEqual(c["warnings"], [])

    def test_the_homo_is_reported_in_both_hartree_and_ev(self):
        """Units on every physical quantity, converted only through `units`."""
        c = bound.classify(ANION, homo_energy_hartree=-0.1)
        self.assertAlmostEqual(c["homo_energy_ev"], units.hartree_to_ev(-0.1), places=9)


class TestPartitionKeepsTheThreeGroupsApart(unittest.TestCase):
    def _recs(self):
        return [
            {"species_id": "li_ec_cation", "converged": True,
             "bound": bound.classify(CATION)},
            {"species_id": "li_ec3_cation", "converged": False,
             "bound": bound.classify(CATION)},
            {"species_id": "li_pf62_anion", "converged": False,
             "bound": bound.classify(ANION, homo_energy_hartree=+0.02)},
            {"species_id": "li_emc3_cation", "status": "TRIPWIRE-ABORTED",
             "converged": False, "bound": bound.classify(CATION)},
            {"species_id": "li_ec_pf62_anion", "converged": True,
             "bound": bound.classify(ANION, homo_energy_hartree=None)},
        ]

    def test_the_denominator_excludes_unbound_aborted_and_unchecked(self):
        p = bound.partition(self._recs())
        self.assertEqual(p["excluded_unbound"], ["li_pf62_anion"])
        self.assertEqual(p["tripwire_aborted"], ["li_emc3_cation"])
        self.assertEqual(p["excluded_bound_check_not_performed"], ["li_ec_pf62_anion"])
        # 🔴 ADR-087: no top-level `convergence_denominator`/`n_converged`/`convergence_rate`.
        # The equivalent figures now live only in `in_u_cheap_statistics` (the denominator) and
        # `per_stratum` (numerator + rate, within a stratum -- these fixtures carry no
        # `stratum` key, so they all land in the single "unspecified" bucket).
        self.assertEqual(len(p["in_u_cheap_statistics"]), 2)
        self.assertEqual(p["per_stratum"]["unspecified"]["denominator"], 2)
        self.assertEqual(p["per_stratum"]["unspecified"]["n_converged"], 1)
        self.assertAlmostEqual(p["per_stratum"]["unspecified"]["convergence_rate"], 0.5)

    def test_an_unbound_species_does_not_drag_the_rate_down(self):
        """🔴 The failure mode in the direction that would flatter a budget."""
        recs = self._recs()
        naive = sum(1 for r in recs if r.get("converged")) / float(len(recs))
        p = bound.partition(recs)
        self.assertNotAlmostEqual(p["per_stratum"]["unspecified"]["convergence_rate"], naive,
                                  msg="the rate is being computed over everything, so an unbound "
                                      "species and a wall-clock abort are being read as protocol "
                                      "failures")

    def test_an_empty_set_gives_no_strata_not_a_zero_rate(self):
        p = bound.partition([])
        self.assertEqual(p["per_stratum"], {},
                         "a rate over an empty set reported as 0.0 is a measurement of zero, "
                         "not an absence of measurement (ADR-036) -- an empty stratum table, "
                         "not a zero-valued rate, is the correct absence-marker here")

    def test_no_pooled_fields_survive_at_the_top_level(self):
        """🔴 ADR-087, direct guard: these three names must never reappear at this level,
        under any name -- a revert that resurrects them under `convergence_rate` OR renames it
        to something equally readable as a pooled rate must fail this."""
        p = bound.partition(self._recs())
        for pooled_name in ("convergence_rate", "n_converged", "convergence_denominator"):
            self.assertNotIn(pooled_name, p)


if __name__ == "__main__":
    unittest.main()
