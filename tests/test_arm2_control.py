"""B0-D arm 2 — the null control.

🔒 A control built after the treatment tends to be built to agree with it. This was written before
   arm 1 has produced a single number, deliberately.

🔴 THE CONTROL MUST BE THE SAME PROCEDURE, NOT AN IMITATION. The tests below assert that the
   ligand coordinates come from `tools/make_p5_species.py` itself and that the three species which
   HAVE a shipped idealised geometry use that file byte-for-byte — because "I rebuilt something
   similar" is not a control, and the difference is invisible in the output.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import arm2, b0_species, seeding

IDEALISED = os.path.join(context.PKG_ROOT, "inputs", "p5_species")


class TestItUsesTheRealGenerator(unittest.TestCase):
    def test_the_ligand_blocks_are_the_generators_own(self):
        """🔴 Not retyped. Compared against the files the generator itself wrote."""
        blocks = arm2.ligand_blocks()
        for name, fn in (("EC", "ec.xyz"), ("EMC", "emc.xyz"), ("PF6", "pf6_anion.xyz")):
            with open(os.path.join(IDEALISED, fn)) as fh:
                shipped = seeding.read_xyz(fh.read())
            self.assertEqual(len(blocks[name]), len(shipped), name)
            for a, b in zip(blocks[name], shipped):
                self.assertEqual(a[0], b[0], name)
                for k in (1, 2, 3):
                    self.assertAlmostEqual(a[k], b[k], places=6, msg=name)

    def test_the_generator_module_actually_loads(self):
        """If `tools/make_p5_species.py` moves, this fails loudly rather than falling back."""
        self.assertTrue(os.path.isfile(arm2._GEN_PATH), arm2._GEN_PATH)
        self.assertTrue(arm2.ligand_blocks())


class TestShippedGeometriesAreUsedVerbatim(unittest.TestCase):
    """🔴 The three species that have a genuine artefact must use THE ARTEFACT."""

    SHIPPED = ("li_ec_cation", "li_ec2_cation", "li_ec_radical")

    def _species(self, sid):
        for s in b0_species.all_species():
            if s["id"] == sid:
                return s
        raise AssertionError("%s is no longer in the batch" % sid)

    def test_each_one_matches_its_file_atom_for_atom(self):
        for sid in self.SHIPPED:
            atoms, prov = arm2.build(self._species(sid))
            self.assertEqual(prov["source"], arm2.PROV_SHIPPED, sid)
            self.assertTrue(prov["is_the_artefact_itself"], sid)
            with open(os.path.join(IDEALISED, sid + ".xyz")) as fh:
                shipped = seeding.read_xyz(fh.read())
            self.assertEqual(atoms, shipped,
                             "%s: arm 2 did NOT use the shipped artefact. A rebuilt lookalike is "
                             "not the control -- the whole claim is 'the guess RT-1 actually "
                             "made'." % sid)

    def test_the_header_still_declares_the_geometry_unoptimised(self):
        """🔒 That line is what let ADR-066 diagnose P1 at zero cost."""
        for sid in self.SHIPPED:
            _, prov = arm2.build(self._species(sid))
            # Presence before value, so "the artefact was not used at all" reports as a readable
            # FAIL rather than a KeyError ERROR (§0.2(a)).
            self.assertIn("header", prov,
                          "%s: the arm-2 record has no `header`, which means the shipped file "
                          "was never opened -- a rebuilt lookalike is not the control" % sid)
            self.assertIn("NOT optimized", prov["header"], sid)


class TestArmTwoIsTheThreeShippedSpeciesOnly(unittest.TestCase):
    """🔒 RULING (a): the 3 genuine artefacts only; the other 20 are arm-1-only.

    Not a sample-size compromise. The two groups answer DIFFERENT QUESTIONS, and ADR-077 took
    arm 2's main job away — U-55 is decided by `curvature.u55_panel` against ARM 1's own opt
    cycles and core-h, which needs 23 species of arm 1 and zero of arm 2.
    """

    def setUp(self):
        self.res = arm2.build_all(b0_species.all_species())

    def test_only_the_three_shipped_species_are_built(self):
        self.assertTrue(self.res["shipped_only"])
        self.assertEqual(self.res["n_species"], 3)
        self.assertEqual(self.res["n_extended"], 0)
        self.assertEqual(sorted(r["species_id"] for r in self.res["records"]),
                         ["li_ec2_cation", "li_ec_cation", "li_ec_radical"])

    def test_the_other_twenty_are_named_as_arm1_only_not_dropped(self):
        self.assertEqual(self.res["n_arm1_only"], 20)
        self.assertEqual(len(self.res["arm1_only_species"]), 20)

    def test_they_are_not_reported_as_missing_data(self):
        """🔴 The retrospective question does not EXIST for them — no bad start was ever paid for."""
        joined = " ".join(self.res["warnings"])
        self.assertIn("NOT missing data", joined)
        self.assertIn("arm2_scope_is_the_ruling", joined)

    def test_u55_is_explicitly_not_answered_here(self):
        self.assertIn("curvature.u55_panel", self.res["u55_is_not_answered_here"])
        self.assertIn("ADR-077", self.res["u55_is_not_answered_here"])

    def test_no_pf6_ligand_appears_in_arm2_at_all(self):
        """🟢 The LI_OFFSET_Y_ANG-on-octahedral-PF6 worry dissolves: there is no PF6 in arm 2."""
        for r in self.res["records"]:
            self.assertNotIn("pf6", r["species_id"])

    def test_the_extended_path_survives_but_warns_loudly_when_used(self):
        """🔒 Kept in the tree, unwired. B1 may need a real prospective builder later."""
        ext = arm2.build_all(b0_species.all_species(), shipped_only=False)
        self.assertEqual(ext["n_species"], 23)
        self.assertEqual(ext["n_extended"], 20)
        self.assertIn("arm2_extended_path_used", " ".join(ext["warnings"]))
        self.assertIn("measures that rule, not the guess", " ".join(ext["warnings"]))

    def test_the_reason_no_general_rule_exists_is_recorded(self):
        """🔴 The two hand-placed complexes are wrong in OPPOSITE directions from experiment."""
        note = arm2.__doc__
        self.assertIn("180.0 deg", note)
        self.assertIn("90.3 deg", note)
        self.assertIn("138", note)


class TestTheMeasuredPathologyTravelsWithTheData(unittest.TestCase):
    """🔴 The 180.0 deg was written down NOWHERE. Only the 90.3 deg reached §39.1(e-bis)."""

    def setUp(self):
        self.res = arm2.build_all(b0_species.all_species())
        self.by_id = dict((r["species_id"], r) for r in self.res["records"])

    def test_every_shipped_record_carries_its_measured_geometry(self):
        for sid in ("li_ec_cation", "li_ec2_cation", "li_ec_radical"):
            self.assertIn("idealised_geometry", self.by_id[sid],
                          "%s carries no measured geometry -- the number would live only in a "
                          "message again" % sid)

    def _geom(self, sid):
        # Presence before value, so a dropped block reports FAIL rather than KeyError (§0.2(a)).
        self.assertIn("idealised_geometry", self.by_id[sid],
                      "%s carries no measured geometry -- the 180.0 deg finding would live only "
                      "in a message again, which is how it went unrecorded the first time" % sid)
        return self.by_id[sid]["idealised_geometry"]

    def test_the_two_pathologies_are_opposite_in_sign(self):
        """🟢 +42 deg and -48 deg about an experimental ~138 deg."""
        a = self._geom("li_ec_cation")
        b = self._geom("li_ec2_cation")
        self.assertGreater(a["deviation_from_experiment_deg"], 0)
        self.assertLess(b["deviation_from_experiment_deg"], 0)
        self.assertAlmostEqual(a["li_o_c_angle_deg"], 180.0, places=1)
        self.assertAlmostEqual(b["li_o_c_angle_deg"], 90.3, places=1)

    def test_p1s_own_endpoints_used_the_undocumented_one(self):
        """li_ec_radical is R-A/R-B's reactant and P1's endpoint species."""
        self.assertAlmostEqual(self._geom("li_ec_radical")["li_o_c_angle_deg"], 180.0, places=1)

    def test_the_experimental_reference_is_labelled_approximate(self):
        """🔴 It is a literature figure, not a datum of ours."""
        g = self._geom("li_ec_cation")
        self.assertIn("approximate", g["_experimental_label"].lower())
        self.assertIn("LITERATURE", g["_experimental_label"])

    def test_the_note_says_both_are_symmetric_placements(self):
        """🟢 This STRENGTHENS ADR-067: 180 deg is also Li on a symmetry element."""
        g = self._geom("li_ec_cation")
        self.assertIn("symmetry element", g["note"])
        self.assertIn("they were drawn", g["note"])


class TestTheIdealisedGeometriesAreStillWrongInTheWayRecorded(unittest.TestCase):
    """Guard the premise. If these files were ever "fixed", arm 2 has lost its subject."""

    def _angle_and_distance(self, sid):
        import math
        from sei_pilot import roles
        from sei_pilot.criteria import xyzgraph
        with open(os.path.join(IDEALISED, sid + ".xyz")) as fh:
            a = seeding.read_xyz(fh.read())
        r = roles.perceive(a)
        li = r["Li"][0]
        oc = r["O_carbonyl"][0]
        bonds = xyzgraph.bond_list(a, include_ionic=False)
        c = ([j for i, j in bonds if i == oc] + [i for i, j in bonds if j == oc])[0]
        v1 = [a[li][t] - a[oc][t] for t in (1, 2, 3)]
        v2 = [a[c][t] - a[oc][t] for t in (1, 2, 3)]
        dot = sum(x * y for x, y in zip(v1, v2))
        n1 = math.sqrt(sum(x * x for x in v1))
        n2 = math.sqrt(sum(x * x for x in v2))
        return math.degrees(math.acos(max(-1.0, min(1.0, dot / (n1 * n2))))), n1

    def test_the_one_ligand_complex_is_linear_at_180_degrees(self):
        ang, d = self._angle_and_distance("li_ec_cation")
        self.assertAlmostEqual(ang, 180.0, places=1)
        self.assertAlmostEqual(d, 1.850, places=3)

    def test_the_two_ligand_complex_is_bent_at_90_degrees(self):
        ang, d = self._angle_and_distance("li_ec2_cation")
        self.assertAlmostEqual(ang, 90.3, places=1)
        self.assertAlmostEqual(d, 2.100, places=3)

    def test_the_two_disagree_with_each_other(self):
        """🔴 Which is why no single placement rule could reproduce both."""
        a1, _ = self._angle_and_distance("li_ec_cation")
        a2, _ = self._angle_and_distance("li_ec2_cation")
        self.assertGreater(abs(a1 - a2), 45.0,
                           "the two hand-placed complexes now agree -- if a consistent rule has "
                           "appeared, the `extended` species could use it instead")


class TestArmTwoRefusesThePreOptimisation(unittest.TestCase):
    """🔴 Arm 2 keeps its idealised start or it stops being a control."""

    def test_it_raises_rather_than_warning(self):
        self.assertRaises(arm2.PreoptimisationForbidden,
                          arm2.assert_no_preoptimisation, {"pre_optimise": True})

    def test_the_message_says_what_would_be_lost(self):
        try:
            arm2.assert_no_preoptimisation({"pre_optimise": True})
        except arm2.PreoptimisationForbidden as exc:
            self.assertIn("deletes the measurement", str(exc))
        else:
            self.fail("arm 2 accepted the pre-optimisation that belongs to arm 1")

    def test_the_absence_of_the_flag_is_fine(self):
        self.assertTrue(arm2.assert_no_preoptimisation({}))
        self.assertTrue(arm2.assert_no_preoptimisation(None))
        self.assertTrue(arm2.assert_no_preoptimisation({"pre_optimise": False}))


class TestExtendedStructuresAreSane(unittest.TestCase):
    def test_none_violates_the_generators_own_overlap_floor(self):
        """Reusing the generator's 0.9 A refusal. Checked on the EXTENDED path, which is where
        a built structure could overlap at all -- the shipped ones were checked when written."""
        for r in arm2.build_all(b0_species.all_species(), shipped_only=False)["records"]:
            d = r["provenance"].get("min_interatomic_distance_ang")
            if d is not None:
                self.assertGreaterEqual(d, r["provenance"].get("overlap_threshold_ang", 0.9),
                                        "%s has overlapping atoms -- SCF would die immediately "
                                        "and the run would measure nothing" % r["species_id"])

    def test_a_single_atom_reports_none_not_a_sentinel(self):
        """🔴 The closest pair among one atom is undefined, not 1e9 (ADR-036)."""
        bare = [s for s in b0_species.all_species() if s["id"] == "li_cation"][0]
        _, prov = arm2.build(bare)
        self.assertIsNone(prov["min_interatomic_distance_ang"])

    def test_atom_counts_match_the_declared_composition(self):
        sizes = {"EC": 10, "EMC": 15, "PF6": 7}
        for r in arm2.build_all(b0_species.all_species(), shipped_only=False)["records"]:
            sp = [s for s in b0_species.all_species() if s["id"] == r["species_id"]][0]
            expected = 1 + sum(sizes[k] * v for k, v in sp["composition"].items())
            self.assertEqual(r["n_atoms"], expected,
                             "%s: %d atoms built, %d expected from its composition"
                             % (r["species_id"], r["n_atoms"], expected))


if __name__ == "__main__":
    unittest.main()
