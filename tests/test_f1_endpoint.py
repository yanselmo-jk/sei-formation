"""F1 falsifier observables (`config/f1_required_observables.json`, ADR-099/§39.32(h)).

🔴 Fixtures are the REAL shipped `inputs/li_ec_radical_{reactant,product}.xyz` (ADR-042 /
coder6's convention), not hand-built atom lists -- a hand-built list verifies the geometry I
IMAGINE the ring has, not the one the real file has.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot.criteria import f1_endpoint as f1
from sei_pilot.criteria import xyzgraph

INPUTS = os.path.join(context.PKG_ROOT, "inputs")


def _read_xyz(name):
    with open(os.path.join(INPUTS, name)) as fh:
        return xyzgraph.read_xyz_frames(fh.read())[0][1]


class TestRingBondLengths(unittest.TestCase):
    def test_five_bonds_found_on_the_real_reactant_file(self):
        r = f1.ring_bond_lengths(_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertEqual(r["n_bonds"], 5)
        self.assertEqual(r["warnings"], [])

    def test_the_hand_drawn_guess_reproduces_the_documented_falsifier_value(self):
        """🔴 THE REGRESSION this observable exists to catch: the guess's own ring bonds are
        equal at 1.399/1.400 A (f1_required_observables.json's own falsifies_if value) --
        pinned here so a later change to the shipped file or the role perception is caught."""
        r = f1.ring_bond_lengths(_read_xyz("li_ec_radical_reactant.xyz"))
        for d in r["distances_ang"]:
            self.assertAlmostEqual(d, 1.4, delta=0.0025)

    def test_both_symmetry_equivalent_candidates_are_collected_not_just_one(self):
        """🔒 roles.resolve_bond would silently return only ONE of the two ambiguous
        C_carbonyl-O_ether / O_ether-C_sp3 bonds -- this function must use `candidates`, not
        `selected`, or the ring comes back with 3 bonds instead of 5."""
        r = f1.ring_bond_lengths(_read_xyz("li_ec_radical_reactant.xyz"))
        role_pairs = [tuple(b["roles"]) for b in r["bonds"]]
        self.assertEqual(role_pairs.count(("C_carbonyl", "O_ether")), 2)
        self.assertEqual(role_pairs.count(("O_ether", "C_sp3")), 2)
        self.assertEqual(role_pairs.count(("C_sp3", "C_sp3")), 1)

    def test_a_missing_ring_role_is_reported_not_silently_dropped(self):
        atoms = [("C", 0, 0, 0), ("H", 1, 0, 0)]  # no ring at all
        r = f1.ring_bond_lengths(atoms)
        self.assertEqual(r["n_bonds"], 0)
        self.assertTrue(r["warnings"])


class TestLiOCAngle(unittest.TestCase):
    def test_the_hand_drawn_guess_reproduces_180_degrees(self):
        """🔴 Pins the documented baseline (STATE §0-g / f1_required_observables.json's own
        falsifies_if value) -- the angle F1 exists to watch move away from this."""
        out = f1.li_o_c_angle_deg(_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertAlmostEqual(out["angle_deg"], 180.0, places=1)
        self.assertEqual(out["warnings"], [])

    def test_ring_opened_product_correctly_refuses_rather_than_guessing(self):
        """🔴 REAL FINDING, not a hypothetical: ring-opening breaks one O-C bond, so the
        oxygen that WAS the ether oxygen now has only one carbon neighbour too -- the product
        genuinely has TWO 'exactly one C neighbour' oxygens (`O_carbonyl`'s own definition),
        and there is no honest way to pick which one is "the" C=O without more information
        than a bond-count role perception carries. Refusing (None + a named warning) is the
        correct behaviour here, not a bug to work around by guessing."""
        out = f1.li_o_c_angle_deg(_read_xyz("li_ec_radical_product.xyz"))
        self.assertIsNone(out["angle_deg"])
        self.assertIn("angle_role_not_unique", " ".join(out["warnings"]))

    def test_missing_role_is_none_with_a_warning_not_a_crash(self):
        atoms = [("C", 0, 0, 0), ("H", 1, 0, 0)]  # no Li, no carbonyl
        out = f1.li_o_c_angle_deg(atoms)
        self.assertIsNone(out["angle_deg"])
        self.assertTrue(out["warnings"])


class TestNImaginary(unittest.TestCase):
    def test_counts_negative_frequencies(self):
        self.assertEqual(f1.n_imaginary([-105.0, 50.0, 60.0]), 1)
        self.assertEqual(f1.n_imaginary([10.0, 20.0]), 0)

    def test_empty_is_none_not_zero(self):
        """🔴 Rule 18: no frequency data read is not a measurement of zero imaginary modes."""
        self.assertIsNone(f1.n_imaginary([]))
        self.assertIsNone(f1.n_imaginary(None))


class TestSymmetricFingerprintIsHonestlyLabelled(unittest.TestCase):
    def test_it_is_the_guards_fingerprint_not_a_point_group(self):
        fp = f1.symmetric_fingerprint(_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertFalse(fp["is_point_group_detection"])
        self.assertIn("coverage", fp)

    def test_the_raw_guess_is_flagged_on_the_real_file(self):
        """Positive control: the shipped, un-perturbed guess sits on a symmetry element."""
        fp = f1.symmetric_fingerprint(_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertTrue(fp["flagged"])

    def test_a_perturbed_geometry_can_clear_the_flag(self):
        """The other direction of the positive control -- the check must be passable."""
        from sei_pilot import guards
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        kicked, prov = guards.perturb_out_of_plane(atoms, seed=7)
        self.assertTrue(prov["applied"])
        fp = f1.symmetric_fingerprint(kicked)
        self.assertFalse(fp["flagged"])


class TestStage1ExitStructuralSet(unittest.TestCase):
    def test_all_three_components_present(self):
        out = f1.stage1_exit_structural_set(_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertIn("symmetric_fingerprint", out)
        self.assertIn("li_o_c_angle_deg", out)
        self.assertIsNotNone(out["max_out_of_plane_ang"])

    def test_it_is_free_no_job_needed(self):
        """Confirms the function signature: geometry in, no QC engine, no I/O."""
        import inspect
        sig = inspect.signature(f1.stage1_exit_structural_set)
        self.assertEqual(list(sig.parameters), ["atoms"])


if __name__ == "__main__":
    unittest.main()
