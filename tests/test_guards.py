"""C-1, C-2, C-8, C-9, C-10, C-12, C-13 -- the blocking constraints, tested against the artefacts.

🔴 THE FIXTURES ARE NOT HAND-WRITTEN, and that is the point (§44.5).
   `inputs/li_ec_radical_{reactant,product}.xyz` are the ACTUAL files RT-1's P1 was given. They
   are read from the delivered package, verbatim. A fixture I invented would encode the input I
   IMAGINE a contaminated run has; these are the ones that really cost 302 core-h.
   The IRC numbers below are likewise the delivered ones, quoted in `02_METHOD_SPEC.md` §39.4(a).

🔴 FAILURE DIRECTION IS THE SUBJECT, not a side condition (Rule 18).
   Half of these tests assert that a guard says `None` or "refuse" when it has NOT been given
   enough information. A guard that falls toward PERMIT on missing input is worse than no guard,
   because it manufactures confidence -- and every one of these constraints exists because a
   check passed on something nobody had looked at.
"""

import json
import math
import os
import unittest

import context  # noqa: F401
from sei_pilot import guards, seeding, units
from sei_pilot.criteria import g16

INPUTS = os.path.join(context.PKG_ROOT, "inputs")

#: 🔴 VERBATIM from `02_METHOD_SPEC.md` §39.4(a), which quotes `pilots[P1].detail` of the returned
#:   RT-1 report. Not reconstructed.
P1_TS_HARTREE = -350.011388718
P1_IRC_FORWARD = {"normal_termination": True, "n_points": 1,
                  "energy_hartree": -350.011391520}
P1_IRC_REVERSE = {"normal_termination": False, "n_points": 1,
                  "energy_hartree": -350.011389969}


def _read_xyz(name):
    with open(os.path.join(INPUTS, name)) as fh:
        return seeding.read_xyz(fh.read())


def _header_line(name):
    with open(os.path.join(INPUTS, name)) as fh:
        fh.readline()
        return fh.readline().strip()


# =============================================================================================
# C-9 -- the planar degeneracy, measured on the real files
# =============================================================================================

class TestTheRealInputsAreStillTheContaminatedOnes(unittest.TestCase):
    """Guard the fixture itself. If these files are ever 'fixed', these tests stop testing.

    🔒 arm 2 of B0-D deliberately reuses these geometries as the null control -- that is the ONLY
    place they may appear, and it is why they must not be quietly replaced by better ones.
    """

    def test_headers_still_declare_they_are_not_optimised(self):
        for name in ("li_ec_radical_reactant.xyz", "li_ec_radical_product.xyz"):
            self.assertIn("GUESS GEOMETRY", _header_line(name),
                          "%s no longer declares itself a guess -- if it was replaced with an "
                          "optimised geometry, B0-D arm 2 has lost its control and these tests "
                          "have lost their subject" % name)

    def test_every_heavy_atom_is_still_at_z_zero(self):
        for name in ("li_ec_radical_reactant.xyz", "li_ec_radical_product.xyz"):
            hv = guards.heavy_atoms(_read_xyz(name))
            self.assertTrue(all(abs(a[3]) < 1e-9 for a in hv),
                            "%s: the heavy atoms are no longer exactly planar" % name)


class TestCoplanarityDetectsTheDegeneracy(unittest.TestCase):
    def test_rt1_endpoints_are_detected_as_coplanar(self):
        for name in ("li_ec_radical_reactant.xyz", "li_ec_radical_product.xyz"):
            cop = guards.coplanarity(_read_xyz(name))
            self.assertTrue(cop["is_coplanar"],
                            "%s: C-9 failed to see a Cs-planar-by-construction guess" % name)
            self.assertLess(cop["max_out_of_plane_ang"], 1e-6)

    def test_hydrogens_are_excluded_or_the_degeneracy_hides(self):
        """🔴 The H's sit at mirror-symmetric +/-0.880 A about the heavy-atom plane.

        Including them would report a 0.88 A spread and call the structure non-planar -- which is
        the wrong answer about exactly the structure the constraint was written for.
        """
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        self.assertTrue(any(a[0] == "H" and abs(a[3]) > 0.5 for a in atoms),
                        "fixture changed: the H's are no longer off-plane")
        self.assertTrue(guards.coplanarity(atoms)["is_coplanar"])

    def test_a_genuinely_puckered_structure_is_not_flagged(self):
        """Positive control the other way: the guard must not fire on everything."""
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        puckered = [(s, x, y, z + (0.30 if i % 2 else -0.30))
                    for i, (s, x, y, z) in enumerate(atoms)]
        cop = guards.coplanarity(puckered)
        self.assertFalse(cop["is_coplanar"])
        self.assertGreater(cop["max_out_of_plane_ang"], guards.COPLANAR_TOL_ANG)

    def test_four_collinear_heavy_atoms_do_not_break_the_eigensolver(self):
        """🔴 The degenerate covariance the critic was going to be asked about. Closed here.

        A LINEAR arrangement of >= 4 heavy atoms gives a covariance matrix with TWO zero
        eigenvalues, so the "smallest-eigenvalue eigenvector" is not unique. Cyclic Jacobi returns
        an arbitrary but ORTHONORMAL member of that subspace rather than failing, and the
        DEDUCTION we draw from it is still correct: a collinear set IS coplanar, in every plane
        containing the line. What must not happen is a crash, a NaN, or a False.
        """
        linear = [("C", float(i) * 1.3, 0.0, 0.0) for i in range(4)]
        cop = guards.coplanarity(linear)
        self.assertIs(cop["is_coplanar"], True)
        self.assertLess(cop["max_out_of_plane_ang"], 1e-9)
        norm = sum(c * c for c in cop["normal"]) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=9,
                               msg="the plane normal is not a unit vector on a degenerate "
                                   "covariance -- every downstream projection is then wrong")
        for c in cop["normal"]:
            self.assertEqual(c, c, "NaN in the plane normal")   # NaN != NaN

    def test_the_real_collinear_li_o_c_does_not_near_degenerate_the_covariance(self):
        """🔴 The lead's adjacency, answered by measurement rather than by argument.

        We hold a genuinely COLLINEAR Li-O=C (`li_ec_cation`, 180.0 deg). Does three collinear
        atoms inside a 7-heavy-atom molecule come near degenerating the covariance, where the
        smallest eigenvector stops being unique?

        MEASURED: eigenvalues [0.0, 3.54, 20.95]. The zero is the PLANAR degeneracy the guard is
        for, and the two SMALLEST are well separated (0.0 vs 3.54), so the plane normal is
        uniquely determined. 🟢 The dangerous case is two EQUAL smallest eigenvalues; this is not
        near it.
        """
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        hv = guards.heavy_atoms(atoms)
        n = float(len(hv))
        c = [sum(a[k] for a in hv) / n for k in (1, 2, 3)]
        cov = [[0.0] * 3 for _ in range(3)]
        for a in hv:
            d = [a[k + 1] - c[k] for k in range(3)]
            for i in range(3):
                for j in range(3):
                    cov[i][j] += d[i] * d[j]
        from sei_pilot import linalg
        vals = sorted(linalg.jacobi_eigen(cov)[0])
        self.assertLess(abs(vals[0]), 1e-9, "the planar degeneracy is gone from the fixture")
        self.assertGreater(vals[1] - vals[0], 1.0,
                           "the two smallest eigenvalues are close (%r) -- the plane normal is "
                           "no longer uniquely determined and the guard's verdict would depend "
                           "on rounding" % (vals,))
        cop = guards.coplanarity(atoms)
        self.assertIs(cop["is_coplanar"], True)

    def test_a_perfectly_symmetric_covariance_is_still_handled(self):
        """Second degeneracy: a regular tetrahedron. All three eigenvalues equal."""
        t = [("C", 1, 1, 1), ("C", 1, -1, -1), ("C", -1, 1, -1), ("C", -1, -1, 1)]
        cop = guards.coplanarity([(s, float(x), float(y), float(z)) for s, x, y, z in t])
        self.assertIs(cop["is_coplanar"], False,
                      "a tetrahedron was called planar -- the guard would then permit a TS "
                      "search it should have perturbed")
        norm = sum(c * c for c in cop["normal"]) ** 0.5
        self.assertAlmostEqual(norm, 1.0, places=9)

    def test_fewer_than_four_heavy_atoms_is_none_not_false(self):
        cop = guards.coplanarity([("O", 0, 0, 0), ("H", 1, 0, 0), ("H", 0, 1, 0)])
        self.assertIsNone(cop["is_coplanar"],
                          "3 heavy atoms are trivially coplanar; reporting False would claim a "
                          "check was made that carries no information")

    def test_plane_detection_is_orientation_independent(self):
        """The degeneracy is a property of the molecule, not of how it was written down.

        A guard that only notices `z == 0` would pass this file and miss the same molecule rotated
        -- and nothing guarantees a generated conformer arrives axis-aligned.
        """
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        ca, sa = math.cos(0.7), math.sin(0.7)
        cb, sb = math.cos(1.1), math.sin(1.1)
        rot = []
        for s, x, y, z in atoms:
            y1, z1 = ca * y - sa * z, sa * y + ca * z
            x2, z2 = cb * x - sb * z1, sb * x + cb * z1
            rot.append((s, x2, y1, z2))
        self.assertTrue(guards.coplanarity(rot)["is_coplanar"],
                        "the plane test is axis-aligned -- it would miss any rotated guess")


class TestOutOfPlaneKick(unittest.TestCase):
    def test_kick_breaks_the_plane_and_is_reproducible(self):
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        a1, p1 = guards.perturb_out_of_plane(atoms, seed=7)
        a2, _ = guards.perturb_out_of_plane(atoms, seed=7)
        self.assertTrue(p1["applied"])
        self.assertEqual(a1, a2, "the kick is not reproducible from its seed -- a result whose "
                                 "starting geometry cannot be regenerated is unusable (ADR-051)")
        self.assertFalse(p1["after"]["is_coplanar"],
                         "the kick did not actually leave the plane")

    def test_seed_provenance_shares_the_seeding_module_definition(self):
        """C-4/ADR-051: `seed_id` must have ONE definition, or D1 is impossible after the fact."""
        _, prov = guards.perturb_out_of_plane(_read_xyz("li_ec_radical_reactant.xyz"), seed=11)
        sp = prov["seed_provenance"]
        self.assertEqual(sp["seed"], 11)
        self.assertIn("Mersenne Twister", sp["rng"])
        self.assertGreater(sp["max_displacement_ang"], 0.0)

    def test_non_planar_input_is_left_untouched(self):
        atoms = [("C", 0, 0, 0), ("C", 1.5, 0, 0), ("O", 0, 1.4, 0), ("O", 0, 0, 1.4)]
        out, prov = guards.perturb_out_of_plane(atoms, seed=3)
        self.assertFalse(prov["applied"])
        self.assertEqual(out, [tuple(a) for a in atoms])

    def test_kick_is_signed_per_atom_not_a_rigid_translation(self):
        """A one-signed kick translates the molecule and preserves the mirror plane exactly."""
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        out, prov = guards.perturb_out_of_plane(atoms, seed=5)
        nx, ny, nz = prov["coplanarity"]["normal"]
        deltas = [((b[1] - a[1]) * nx + (b[2] - a[2]) * ny + (b[3] - a[3]) * nz)
                  for a, b in zip(atoms, out)]
        self.assertTrue(any(d > 0 for d in deltas) and any(d < 0 for d in deltas),
                        "every atom moved the same way -- that is a rigid translation and it "
                        "leaves the Cs subspace exactly as it was")


# =============================================================================================
# C-8 -- the TS precondition
# =============================================================================================

GOOD = {"optimised": True, "converged": True, "n_imag": 0, "level": "level3"}


class TestC9CoverageIsDeclaredNotImplied(unittest.TestCase):
    """🔴 C-9 as implemented is the WRONG TEST for four of our five files. Say so, in data.

    C-9's revised specification (proposer5): *no atom on a SYMMETRY ELEMENT of the remaining
    fragment — axis, plane, or centre*. The coplanarity test sees only the planar case:
        li_ec2_cation      Li on a MIRROR PLANE, heavy atoms NOT coplanar  -> MISSED
        li_ec_cation etc.  Li on EC's C2 ROTATION AXIS                     -> caught only
                           incidentally, because those files also happen to be fully planar
    🔒 Full point-group detection is registered as PRODUCTION work and is deliberately absent.
       What must not ship is a check that READS as a guarantee it does not give.
    """

    def test_the_field_name_says_it_is_coplanarity_only(self):
        """🔴 The name travels into every downstream table; a docstring does not."""
        dec = guards.ts_precondition(GOOD, GOOD, geometry=_read_xyz("li_ec_radical_product.xyz"))
        self.assertIn("coplanarity_check_only", dec)
        self.assertNotIn("symmetry", [k for k in dec if k == "symmetry"],
                         "a field called `symmetry` would be read as 'symmetry checked'")

    def test_the_uncovered_elements_are_emitted_as_data(self):
        cov = guards.SYMMETRY_COVERAGE
        uncovered = cov["does_NOT_cover"]
        # 🔒 Length and content, not just "the substring is somewhere in the blob". A first
        #    revert of this test passed because a disabled entry still contained the keyword --
        #    the test was checking presence in a concatenation, which any leftover satisfies.
        self.assertGreaterEqual(len(uncovered), 4,
                                "the uncovered-elements list has been trimmed to %d entries; a "
                                "reader would infer coverage that does not exist" % len(uncovered))
        for entry in uncovered:
            # 10 chars: enough to reject "n/a" / "none" / "nothing", short enough to accept a
            # legitimately terse entry like "inversion centres" (17). My first threshold was 20
            # and rejected real data -- the test's number was wrong, not the coverage list.
            self.assertGreater(len(entry), 10, "trivial entry %r in does_NOT_cover" % entry)
        joined = " ".join(uncovered).lower()
        for missing in ("rotation axes", "inversion centres", "improper axes", "mirror plane"):
            self.assertIn(missing, joined)
        self.assertIn("li_ec2_cation", cov["measured_gap"])
        self.assertNotIn("nothing", joined)

    def test_the_coverage_reaches_the_precondition_output(self):
        dec = guards.ts_precondition(GOOD, GOOD, geometry=_read_xyz("li_ec_radical_product.xyz"))
        self.assertIn("symmetry_coverage", dec)
        self.assertIn("PRODUCTION", dec["symmetry_coverage"]["full_detection_status"])

    def test_the_measured_gap_is_real_not_hypothetical(self):
        """🔴 The file coplanarity misses. Asserted against the artefact, not against prose."""
        import os
        path = os.path.join(context.PKG_ROOT, "inputs", "p5_species", "li_ec2_cation.xyz")
        with open(path) as fh:
            atoms = seeding.read_xyz(fh.read())
        self.assertIs(guards.coplanarity(atoms)["is_coplanar"], False,
                      "li_ec2_cation became coplanar -- the gap this test documents has moved")

    def test_the_constants_carry_the_caveat_that_they_parameterise_the_wrong_test(self):
        """⚠ A better tolerance on a test that cannot see the failure buys nothing."""
        import inspect
        src = inspect.getsource(guards)
        self.assertIn("THE WRONG TEST", src.upper())
        self.assertIn("do not tune this number", src)


class TestTheCheapSymmetricPlacementFingerprint(unittest.TestCase):
    """The targeted half: exact distance degeneracy. NOT point-group detection."""

    def _p5(self, name):
        import os
        with open(os.path.join(context.PKG_ROOT, "inputs", "p5_species", name)) as fh:
            return seeding.read_xyz(fh.read())

    def test_it_catches_the_file_coplanarity_misses(self):
        """🔴 li_ec2_cation: Li on a mirror plane, heavy atoms not coplanar."""
        atoms = self._p5("li_ec2_cation.xyz")
        self.assertIs(guards.coplanarity(atoms)["is_coplanar"], False)
        self.assertTrue(guards.symmetric_placement_flags(atoms)["flagged"])

    def test_it_catches_the_c2_axis_files_too(self):
        for name in ("li_ec_cation.xyz", "li_ec_radical.xyz"):
            self.assertTrue(guards.symmetric_placement_flags(self._p5(name))["flagged"], name)

    def test_it_refuses_to_claim_it_is_point_group_detection(self):
        f = guards.symmetric_placement_flags(self._p5("li_ec_cation.xyz"))
        self.assertFalse(f["is_point_group_detection"])
        self.assertIn("FINGERPRINT, not point-group detection", " ".join(f["warnings"]))
        self.assertIn("does_NOT_cover", f["coverage"])

    def test_a_structure_with_no_centre_is_none_not_false(self):
        """🔴 Rule 18: nothing examined must not read as 'examined and clean'."""
        f = guards.symmetric_placement_flags([("C", 0.0, 0.0, 0.0), ("O", 1.2, 0.0, 0.0)])
        self.assertIsNone(f["flagged"])
        self.assertIn("symmetric_placement_not_checked", " ".join(f["warnings"]))

    def test_breaking_the_symmetry_clears_the_flag(self):
        """Positive control the other way -- it must be clearable, or it is not a detector."""
        atoms = self._p5("li_ec_cation.xyz")
        moved = [(s, x + (0.137 if i % 2 else -0.211), y - 0.083 * i, z + 0.061 * i)
                 for i, (s, x, y, z) in enumerate(atoms)]
        self.assertFalse(guards.symmetric_placement_flags(moved)["flagged"])

    def test_the_warning_states_that_optimisation_does_not_remove_it(self):
        """🔴🔴 MEASURED: GFN2 --opt tight from the idealised start KEEPS the degeneracy.

        The symmetry-breaking gradient is exactly zero, so the optimiser cannot leave. ⟹ arm 1's
        pre-optimisation improves the starting energy and does NOT fix this.
        """
        f = guards.symmetric_placement_flags(self._p5("li_ec_cation.xyz"))
        self.assertIn("optimisation does NOT remove it", " ".join(f["warnings"]))


class TestTSPreconditionRefuses(unittest.TestCase):
    def test_the_rt1_endpoints_are_refused(self):
        """🔴 THE REGRESSION: this is the submission that cost 302 core-h."""
        rt1 = {"optimised": False, "converged": False, "n_imag": None, "level": "level2",
               "source": "inputs/li_ec_radical_reactant.xyz"}
        dec = guards.ts_precondition(rt1, dict(rt1), required_level="level3",
                                     geometry=_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertFalse(dec["may_start"])
        joined = " | ".join(dec["blocking_reasons"])
        for expected in ("converged", "optimised", "n_imag", "coplanar"):
            self.assertIn(expected, joined,
                          "C-8/C-9 did not name %r among the reasons it refused" % expected)

    def test_the_actual_shipped_p1_inputs_raise(self):
        """🔴 ADR-090 item 5: `inputs/li_ec_radical_{reactant,product}.xyz` are the files
        `payload/P1.sh` copies straight into the QST2 launch today. Their own header line
        says 'GUESS GEOMETRY (idealized, not optimized)' -- there is no optimisation/
        frequency step for them anywhere in the pipeline, so their true `optimised`/
        `converged`/`n_imag` state is UNKNOWN, not False. Unknown is not permission (Rule
        18): `require_ts_precondition` must still raise. Not wired to P1's live launch path
        (that is the scope decision the lead is taking to the user) -- this only pins that
        the guard, if it WERE called today, would correctly refuse."""
        unknown = {"level": "level2"}  # optimised/converged/n_imag genuinely unrecorded
        with self.assertRaises(guards.TSPreconditionError) as ctx:
            guards.require_ts_precondition(
                unknown, dict(unknown), required_level="level2",
                geometry=_read_xyz("li_ec_radical_reactant.xyz"))
        self.assertTrue(ctx.exception.decision["blocking_reasons"])

    def test_it_raises_rather_than_returning_an_ignorable_flag(self):
        with self.assertRaises(guards.TSPreconditionError) as ctx:
            guards.require_ts_precondition({"optimised": False, "converged": False,
                                            "n_imag": None, "level": "level3"}, GOOD)
        self.assertTrue(ctx.exception.decision["blocking_reasons"])

    def test_missing_n_imag_is_a_refusal_not_a_pass(self):
        ep = dict(GOOD)
        ep["n_imag"] = None
        dec = guards.ts_precondition(ep, GOOD)
        self.assertFalse(dec["may_start"],
                         "an endpoint with no frequency calculation on record was permitted -- "
                         "unknown is not permission")

    def test_one_imaginary_mode_at_an_endpoint_is_a_refusal(self):
        ep = dict(GOOD)
        ep["n_imag"] = 1
        self.assertFalse(guards.ts_precondition(ep, GOOD)["may_start"])

    def test_mismatched_endpoint_levels_are_refused(self):
        other = dict(GOOD)
        other["level"] = "level2"
        dec = guards.ts_precondition(GOOD, other)
        self.assertFalse(dec["may_start"])
        self.assertIn("DIFFERENT levels", " ".join(dec["blocking_reasons"]))

    def test_wrong_level_for_the_search_is_refused(self):
        """C-11: a bake-off at level2 measures a protocol production does not use."""
        hi = dict(GOOD)
        hi["level"] = "level2"
        dec = guards.ts_precondition(hi, dict(hi), required_level="level3")
        self.assertFalse(dec["may_start"])

    def test_a_properly_prepared_pair_is_permitted(self):
        """Positive control -- the guard must be passable, or it is not a guard but a wall."""
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        kicked, _ = guards.perturb_out_of_plane(atoms, seed=2)
        dec = guards.ts_precondition(GOOD, GOOD, required_level="level3", geometry=kicked)
        self.assertTrue(dec["may_start"], dec["blocking_reasons"])
        self.assertEqual(dec["warnings"], [])

    def test_a_genuinely_planar_species_may_be_declared_and_proceed(self):
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        self.assertFalse(guards.ts_precondition(GOOD, GOOD, geometry=atoms)["may_start"])
        self.assertTrue(guards.ts_precondition(GOOD, GOOD, geometry=atoms,
                                               declared_planar=True)["may_start"])

    def test_refusal_reaches_warnings(self):
        """Rule 13 -- the field is read by code, warnings[] is read by a human."""
        dec = guards.ts_precondition({}, {})
        self.assertTrue(dec["warnings"])
        self.assertIn("ts_precondition_refused", dec["warnings"][0])


# =============================================================================================
# C-2 -- the IRC verdict
# =============================================================================================

class TestIRCVerdict(unittest.TestCase):
    def test_the_real_p1_irc_is_indeterminate_not_fail(self):
        """🔴 THE REGRESSION, on the delivered numbers.

        R3 compared the transition state with itself and the result was read as a chemical
        failure. Both directions descended by ~80 and ~30 micro-eV.
        """
        v = guards.irc_verdict(P1_IRC_FORWARD, P1_IRC_REVERSE, P1_TS_HARTREE)
        self.assertEqual(v["status"], "indeterminate")
        self.assertNotEqual(v["status"], "fail")
        self.assertFalse(v["may_render_chemical_verdict"])
        self.assertLess(v["forward"]["descent_ev"], 1e-3)

    def test_each_of_the_three_clauses_is_actually_enforced(self):
        ok = {"normal_termination": True, "n_points": 12,
              "energy_hartree": P1_TS_HARTREE - 0.02,   # 0.02 Ha ~ 0.54 eV
              # 🔴 C-2.2: a direction that did not reach a minimum cannot pass, however
              #    tidily it terminated. Stating it is now part of being a clean fixture.
              "completion": {"truncated": False, "minimum_found": True,
                             "termination_reason": "minimum_found"}}
        self.assertEqual(guards.irc_verdict(ok, ok, P1_TS_HARTREE)["status"], "ok")

        no_term = dict(ok, normal_termination=False)
        self.assertEqual(guards.irc_verdict(no_term, ok, P1_TS_HARTREE)["status"],
                         "indeterminate")

        few = dict(ok, n_points=4)
        self.assertEqual(guards.irc_verdict(few, ok, P1_TS_HARTREE)["status"], "indeterminate")

        # Descent just under the 0.05 eV threshold, expressed in Hartree via `units` so the
        # test cannot drift from the constant it is testing.
        shallow = dict(ok, energy_hartree=P1_TS_HARTREE - units.ev_to_hartree(0.049))
        self.assertEqual(guards.irc_verdict(shallow, ok, P1_TS_HARTREE)["status"],
                         "indeterminate")

    def test_topology_alone_can_never_rescue_a_flat_irc(self):
        """§39.4(a): for a LATE TS the covalent graph cannot distinguish TS from product.

        Only the energy can, so the energy clause must be sufficient on its own to refuse.
        """
        matching_topology_but_flat = {"normal_termination": True, "n_points": 30,
                                      "energy_hartree": P1_TS_HARTREE - 1e-6}
        v = guards.irc_verdict(matching_topology_but_flat, matching_topology_but_flat,
                               P1_TS_HARTREE)
        self.assertEqual(v["status"], "indeterminate")

    def test_missing_energy_is_indeterminate(self):
        d = {"normal_termination": True, "n_points": 30}
        self.assertEqual(guards.irc_verdict(d, d, P1_TS_HARTREE)["status"], "indeterminate")

    def test_indeterminate_reaches_warnings_and_says_it_is_not_evidence(self):
        v = guards.irc_verdict(P1_IRC_FORWARD, P1_IRC_REVERSE, P1_TS_HARTREE)
        joined = " ".join(v["warnings"])
        self.assertIn("irc_indeterminate", joined)
        self.assertIn("NOT evidence", joined)


# =============================================================================================
# C-1 -- null, never a number
# =============================================================================================

class TestDerivedOrNull(unittest.TestCase):
    def test_r_composite_over_a_non_convergence_is_null(self):
        """🔴 THE REGRESSION: r_composite = 1.0365's denominator did not converge (ADR-065)."""
        steps = {
            "li_ec2_cation_A_cheap_optfreq": {"converged": False, "core_hours": 283.0},
            "li_ec2_cation_C_high_sp": {"converged": True, "core_hours": 5.1},
        }
        value, prov = guards.derived_or_null(steps, lambda s: 1.0365)
        self.assertIsNone(value)
        self.assertEqual(prov["unconverged_inputs"], ["li_ec2_cation_A_cheap_optfreq"])
        self.assertIn("1.0365", prov["null_reason"])

    def test_presence_of_a_cost_field_does_not_make_a_step_converged(self):
        """🔴 The exact confusion: 283 core-h were spent, so a cost-based check saw a value."""
        steps = {"a": {"core_hours": 283.0}}   # cost present, `converged` absent
        self.assertEqual(guards.unconverged_inputs(steps), ["a"])
        self.assertIsNone(guards.derived_or_null(steps, lambda s: 42.0)[0])

    def test_converged_none_from_a_real_producer_is_null_not_a_number(self):
        """🔴 Pinning the case that ACTUALLY EXISTS in the tree, at the lead's request.

        `criteria/p1b.py:31` returns `{"converged": None}` when there is nothing to parse. `None`
        there means "could not determine", NOT success -- so C-1's strictness is not merely
        defensible, it is required by a producer we ship. The fixture is that producer's own
        output, obtained by calling it, not a dict I wrote to look like it.
        """
        from sei_pilot.criteria import p1b
        undetermined = p1b.parse_orca_scf_cycles("")
        self.assertIsNone(undetermined["converged"],
                          "p1b.parse_orca_scf_cycles no longer returns None for empty input -- "
                          "if it now returns False, re-read this test before deleting it: the "
                          "distinction between 'not determined' and 'determined negative' is the "
                          "whole subject")
        value, prov = guards.derived_or_null({"scf": undetermined}, lambda s: 1.25)
        self.assertIsNone(value,
                          "a step whose convergence COULD NOT BE DETERMINED was treated as "
                          "converged -- unknown is not permission")
        self.assertEqual(prov["unconverged_inputs"], ["scf"])

    def test_all_converged_computes_normally(self):
        steps = {"a": {"converged": True}, "b": {"converged": True}}
        value, prov = guards.derived_or_null(steps, lambda s: 1.25)
        self.assertEqual(value, 1.25)
        self.assertEqual(prov["unconverged_inputs"], [])
        self.assertNotIn("null_reason", prov)


class TestC1AgainstTheRealClusterReport(unittest.TestCase):
    """🔴🔴 The strongest regression available: the ACTUAL returned RT-1 report.

    Not a fixture I built. `cpu_machine_pilot_results/sei_probe_report.cpu.json` is the file the
    cluster sent back, and `pilots[P1b].rt1b.raw_steps` is the block ADR-065 was derived from.
    ADR-065's finding, in one sentence: `r_composite = 1.0365` was published over a denominator
    that did not converge, and no summary field said so -- `raw_steps[].converged` is in no
    summary, so the number that WAS in a summary travelled instead.

    This asserts C-1 would have refused to publish it, on the real bytes.
    """

    REPORT = os.path.join(context.REPO_ROOT, "cpu_machine_pilot_results",
                          "sei_probe_report.cpu.json")

    def setUp(self):
        if not os.path.exists(self.REPORT):
            self.skipTest("real cluster reply not present (running from the tarball)")
        with open(self.REPORT) as fh:
            report = json.load(fh)
        self.steps = None
        for pilot in report.get("pilots") or []:
            steps = (pilot.get("rt1b") or {}).get("raw_steps")
            if steps:
                self.steps = steps
        if not self.steps:
            self.skipTest("no rt1b.raw_steps in the reply")

    def test_no_step_omits_the_converged_field(self):
        """Closes a worry I raised about C-1 being stricter than its wording.

        `unconverged_inputs` treats a MISSING `converged` as not-converged. That is only safe if
        no producer omits it on success. Checked here against the real reply rather than by
        grepping the producers -- ADR-043: absence is not established by grep.
        """
        missing = [k for k, v in self.steps.items() if "converged" not in (v or {})]
        self.assertEqual(missing, [],
                         "step(s) %s carry no `converged` field, so C-1 will null derived values "
                         "that may in fact be fine -- revisit guards.unconverged_inputs" % missing)

    def test_it_names_exactly_the_three_steps_adr065_disqualified(self):
        """🔴 Rule 21-adjacent: the expected set comes from ADR-065, not from this code."""
        self.assertEqual(
            guards.unconverged_inputs(self.steps),
            ["li_ec2_cation_A_cheap_optfreq",
             "li_ec2_cation_B_high_optfreq",
             "li_ec_cation_B_high_optfreq"])

    def test_r_composite_would_have_been_null_not_1_0365(self):
        """🔴 THE REGRESSION, on the delivered artefact."""
        value, prov = guards.derived_or_null(self.steps, lambda s: 1.0365)
        self.assertIsNone(value,
                          "C-1 published a number over a non-convergence -- this is ADR-065 "
                          "happening again on the same bytes that produced it the first time")
        self.assertIn("li_ec2_cation_A_cheap_optfreq", prov["unconverged_inputs"])

    def test_only_hco3_anion_converged_at_both_levels(self):
        """ADR-065's other reading, asserted so a future edit cannot quietly widen the sample."""
        both = sorted(set(
            k.split("_A_cheap_optfreq")[0] for k in self.steps
            if k.endswith("_A_cheap_optfreq") and self.steps[k].get("converged") is True
            and (self.steps.get(k.split("_A_cheap_optfreq")[0] + "_B_high_optfreq")
                 or {}).get("converged") is True))
        self.assertEqual(both, ["hco3_anion"])


# =============================================================================================
# C-12 -- fallbacks keyed on the acceptance test
# =============================================================================================

class TestFallbackDecision(unittest.TestCase):
    def test_converged_to_the_wrong_answer_still_fires_the_fallback(self):
        """🔴 THE REGRESSION: QST2 converged, so a status-keyed fallback never fired."""
        d = guards.fallback_decision(exit_ok=True,
                                     acceptance={"mode_overlap_omega": False,
                                                 "irc_connects_intended_minima": False})
        self.assertTrue(d["fallback_fires"])
        self.assertTrue(d["exit_ok"], "the exit status is recorded, it just does not decide")
        self.assertIn("converged_but_not_accepted", " ".join(d["warnings"]))

    def test_an_unevaluated_check_fires_the_fallback(self):
        d = guards.fallback_decision(exit_ok=True, acceptance={"omega": True, "irc": None})
        self.assertTrue(d["fallback_fires"])
        self.assertEqual(d["unevaluated_checks"], ["irc"])

    def test_no_acceptance_test_at_all_fires_and_says_so(self):
        d = guards.fallback_decision(exit_ok=True, acceptance={})
        self.assertTrue(d["fallback_fires"])
        self.assertIn("fallback_has_no_acceptance_test", " ".join(d["warnings"]))

    def test_a_genuinely_accepted_result_does_not_fire(self):
        d = guards.fallback_decision(exit_ok=True, acceptance={"omega": True, "irc": True})
        self.assertFalse(d["fallback_fires"])
        self.assertTrue(d["accepted"])

    def test_a_crash_that_passes_no_acceptance_check_still_fires(self):
        d = guards.fallback_decision(exit_ok=False, acceptance={"omega": None})
        self.assertTrue(d["fallback_fires"])


# =============================================================================================
# C-13 -- an abort is a measurement
# =============================================================================================

class TestTripwireAbort(unittest.TestCase):
    def test_abort_reports_core_hours_and_counts_toward_spend(self):
        rec = guards.tripwire_record("li_ec3_cation", core_hours=96.0, wall_h=6.0, cap_h=6.0)
        self.assertEqual(rec["status"], guards.TRIPWIRE_ABORTED)
        self.assertEqual(rec["core_hours"], 96.0)
        self.assertTrue(rec["counts_toward_spend"])

    def test_abort_is_not_converged_so_c1_still_nulls_derived_values(self):
        """The two facts must coexist: it SPENT core-h and it MEASURED no energy."""
        rec = guards.tripwire_record("x", 96.0, 6.0, 6.0)
        self.assertFalse(rec["converged"])
        self.assertIsNone(guards.derived_or_null({"x": rec}, lambda s: 1.0)[0])

    def test_aborted_runs_are_included_in_the_spend_total(self):
        recs = [{"core_hours": 5.0, "converged": True},
                guards.tripwire_record("y", 96.0, 6.0, 6.0)]
        self.assertEqual(guards.spend_core_hours(recs), 101.0)


# =============================================================================================
# C-10 -- a cost probe may not carry a chemical verdict
# =============================================================================================

class TestCostProbeHasNoChemicalVerdict(unittest.TestCase):
    def test_the_p1_shaped_result_is_rejected(self):
        """🔴 THE REGRESSION, in the shape P1 actually had."""
        bad = {"id": "P1", "status": "fail", "imag_freq_count": 1,
               "irc_endpoints_distinct": False,
               "fail_reasons": ["IRC endpoints are not distinct"],
               "core_hours_total": 302.4}
        v = guards.cost_probe_violations(bad)
        self.assertTrue(v)
        joined = " ".join(v)
        for expected in ("status", "imag_freq_count", "irc_endpoints_distinct", "fail_reasons"):
            self.assertIn(expected, joined)

    def test_pass_is_a_violation_too_not_only_fail(self):
        """A cost probe that says `pass` has earned a chemical verdict just as illegitimately."""
        self.assertTrue(guards.cost_probe_violations({"status": "pass"}))

    def test_a_clean_cost_probe_passes(self):
        clean = {"id": "B0-D", "status": "measured", "core_hours_total": 12.5,
                 "opt_cycles": 88, "converged": True,
                 "smallest_real_frequencies_cm1": [31.2, 55.0, 78.4]}
        self.assertEqual(guards.cost_probe_violations(clean), [])

    def test_tripwire_aborted_is_an_allowed_cost_probe_status(self):
        self.assertIn(guards.TRIPWIRE_ABORTED, guards.COST_PROBE_STATUSES)
        self.assertEqual(guards.cost_probe_violations(
            {"status": guards.TRIPWIRE_ABORTED, "core_hours": 96.0}), [])


# =============================================================================================
# B-2 -- `nosymm` is not optional for a G16 route that relies on C-9's perturbation
# =============================================================================================

class TestNosymmRequirement(unittest.TestCase):
    """HANDOFF_CODER6 §B-2 / docs/05_STATE.md §0-k: G16 actively re-detects and re-imposes the
    point group, so C-9's perturbation alone is insufficient -- a route that relies on it must
    carry `nosymm` explicitly, and that must be enforced by RAISING, never by a flag a caller
    can decline to read (the same shape as `solvent.SolventDescriptorsMissing`)."""

    def _complete_record(self, route_text):
        """A route whose completeness B-1's parser can actually CONFIRM (closed by the block
        delimiter, balanced parens) -- not a bare string, which is exactly the ambiguous shape
        B-1 exists to stop callers reading as if it answered an absence question."""
        return g16.parse_route_echo(
            " -------------------------------------\n %s\n"
            " -------------------------------------\n" % route_text)

    def test_the_required_job_types_come_from_the_single_source_config(self):
        """🔒 Not a literal tuple duplicated in guards.py -- config/qc_levels.json's
        `_nosymm_required_job_types` sits beside the route templates it constrains."""
        types = guards.nosymm_required_job_types()
        for expected in ("ts_opt", "ts_qst2", "ts_opt_from_guess",
                         "irc_forward", "irc_reverse"):
            self.assertIn(expected, types)

    def test_a_job_type_this_does_not_apply_to_is_a_no_op(self):
        self.assertIsNone(guards.require_nosymm_if_needed("sp", {}))

    def test_confirmed_present_returns_true(self):
        rec = self._complete_record(
            "#p nosymm wB97XD/gen opt=(ts,calcfc,noeigentest,maxcycles=100) freq")
        self.assertTrue(guards.require_nosymm_if_needed("ts_opt", rec))

    def test_confirmed_absent_raises(self):
        rec = self._complete_record(
            "#p wB97XD/gen opt=(ts,calcfc,noeigentest,maxcycles=100) freq")
        with self.assertRaises(guards.NosymmRequirementUnmet):
            guards.require_nosymm_if_needed("ts_opt", rec)

    def test_undetermined_raises_not_silently_passes(self):
        """🔴 THE trap B-2 exists for: a truncated (RT-1-shaped) route must never be read as
        'nosymm is absent' -- it must raise exactly like any other absence claim off it."""
        rec = g16.route_record_from_stored_string(
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen")
        with self.assertRaises(guards.NosymmRequirementUnmet):
            guards.require_nosymm_if_needed("ts_qst2", rec)

    def test_the_real_rt1_ts_route_raises_rather_than_asserting_nosymm_absent(self):
        """The actual stored P1 route (`cpu_machine_pilot_results/...`), reproduced verbatim
        via the fixture already pinned in `test_route_truncation_b1.py`."""
        rec = g16.route_record_from_stored_string(
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen")
        with self.assertRaises(guards.NosymmRequirementUnmet) as ctx:
            guards.require_nosymm_if_needed("ts_qst2", rec)
        self.assertIn("UNKNOWN", str(ctx.exception))

    def test_perturbation_provenance_carries_the_route_requirement(self):
        atoms = _read_xyz("li_ec_radical_reactant.xyz")
        _, prov = guards.perturb_out_of_plane(atoms, seed=7)
        self.assertTrue(prov["route_must_carry_nosymm_or_g16_undoes_this"])

    def test_the_provenance_note_is_present_even_when_no_kick_was_needed(self):
        """The requirement is on the ROUTE (job_type), not on whether THIS call perturbed
        anything -- a non-planar input still returns the note, unconditionally."""
        atoms = [("C", 0, 0, 0), ("C", 1.5, 0, 0), ("O", 0, 1.4, 0), ("O", 0, 0, 1.4)]
        _, prov = guards.perturb_out_of_plane(atoms, seed=3)
        self.assertFalse(prov["applied"])
        self.assertTrue(prov["route_must_carry_nosymm_or_g16_undoes_this"])

    def test_the_blocking_entry_names_what_it_is_blocked_on_and_what_not_to_do(self):
        """🔴 ADR-090 ruling item 3: a category-(B) guard with zero external callers must
        carry a NAMED blocking entry, not silence -- `require_nosymm_if_needed` is itself
        the 5th instance of ADR-090's class, discovered while fixing the first four."""
        entry = guards.NOSYMM_BLOCKING_ENTRY
        self.assertEqual(entry["guard"], "require_nosymm_if_needed")
        self.assertIn("B", entry["category"])
        self.assertIn("B0 collector wiring", entry["blocked_on"])
        self.assertIn("ADR-090 item 9", entry["blocked_on"])
        self.assertIn("do_not", entry)


if __name__ == "__main__":
    unittest.main()
