"""[39.55(b)] B+ — two terminal optimisations per IRC direction, and whether they agree.

B+ is what lets condition 7 be satisfied by branch (b): an IRC that stopped on `maxpoints` can
still ESTABLISH its connection if terminal optimisations from two points on the same descending
branch reach the same minimum. If they reach different minima, a bifurcation lies between them
and the attempt is `indeterminate` -- never a chemical fail (ADR-066).

🔴 The thing these tests exist to keep honest: 39.55(b) calls B+ threshold-free. That is true
of its DESIGN -- two start points on one branch -- but NOT of the comparator that decides "same
minimum", whose Layer-I cutoff is a Li-contact distance this project has already seen a verdict
flip on. A connection established by a number that could have gone the other way is not
established, so a threshold-sensitive comparison yields `None`, never `True`.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import guards, units
from sei_pilot.criteria import g16, xyzgraph


def _reactant():
    path = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
    with open(path, errors="replace") as fh:
        return xyzgraph.read_xyz_frames(fh.read())[0][1]


#: 🔴 [§39.71] The tolerance is now a RULED, DERIVED constant in eV
#: (`guards.BPLUS_ENERGY_TOLERANCE_EV`), so these tests use the shipped default rather than
#: passing one in. An earlier version of this file supplied its own, from the period when
#: §39.70 called for "the optimiser's own convergence criterion" -- a criterion G16 does not
#: have. Passing a test-local tolerance now would test a number nobody ships.


class TestBPlusComparator(unittest.TestCase):
    """🔴 [§39.70] The comparator is (i) identical COVALENT graphs, cation contacts EXCLUDED,
    and (ii) energies agreeing within the optimiser's own convergence criterion.

    It replaced a reuse of `criteria.endpoints.classify_endpoints`, and the reason is the
    point: that comparator's Layer-I cutoff IS a Li-contact distance, so it returned "threshold
    sensitive, no verdict" on exactly the Li-rearrangement cases B+ exists for. §39.48(b) in a
    new place -- a structural test cannot separate a soft-coordinate displacement from a
    reaction-relevant one, and the cutoff is that soft coordinate promoted to a decision.
    """

    def test_same_valley_agrees(self):
        a = _reactant()
        r = guards.bplus_agreement(a, list(a), -350.0, -350.0 + 1e-9)
        self.assertTrue(r["agreement"])
        self.assertTrue(r["covalent_graphs_match"])

    def test_the_li_contact_is_reported_but_never_decided_on(self):
        """🔒 The cutoff keeps its [PLACEHOLDER-ESTIMATE] status AS DATA -- which is where a
        placeholder belongs -- and leaves the decision path entirely."""
        r = guards.bplus_agreement(_reactant(), _reactant(), -350.0, -350.0)
        self.assertIn("layer_I_cutoffs_ang", r["covariates"])
        self.assertIn("EXCLUDED", r["covariates"]["_note"])

    def test_moving_only_the_cation_does_not_break_agreement(self):
        """🟢 THE CASE THE OLD COMPARATOR COULD NOT ANSWER. Displace Li alone and the covalent
        graph is unchanged, so two optimisations that differ only in cation position still read
        as the same valley -- provided the energies agree."""
        a = _reactant()
        li = [k for k, at in enumerate(a) if at[0] == "Li"]
        self.assertTrue(li, "fixture must contain the cation this test is about")
        b = list(a)
        k = li[0]
        b[k] = (a[k][0], a[k][1] + 0.35, a[k][2], a[k][3])
        r = guards.bplus_agreement(a, b, -350.0, -350.0 + 5e-7)
        self.assertTrue(r["covalent_graphs_match"])
        self.assertTrue(r["agreement"], r["reasons"])

    def test_half_agreement_is_no_verdict_not_a_guess(self):
        """🟢 The conservative rule survives where it is still needed: graphs agree but
        energies do not (or the reverse) => genuine ambiguity => None, never True."""
        a = _reactant()
        r = guards.bplus_agreement(a, list(a), -350.0, -349.9)
        self.assertIsNone(r["agreement"])
        self.assertIn("genuine ambiguity", r["reasons"][-1])

    def test_without_a_tolerance_clause_ii_cannot_run_and_there_is_no_verdict(self):
        """🔴 Clause (ii) is not optional: without it, clause (i) alone calls two coordination
        isomers the same basin -- measured at 0.686 eV apart with an identical covalent graph.
        So an absent tolerance yields no verdict rather than falling back to the graph."""
        a = _reactant()
        r = guards.bplus_agreement(a, list(a), -350.0, -350.0, energy_tolerance_ev=None)
        self.assertIsNone(r["agreement"])
        self.assertIn("clause (i) alone would call two coordination isomers the same basin",
                      r["reasons"][-1])

    def test_a_missing_energy_yields_no_verdict(self):
        a = _reactant()
        r = guards.bplus_agreement(a, list(a), -350.0, None)
        self.assertIsNone(r["agreement"])


class TestBPlusLiDisplacementCovariate(unittest.TestCase):
    """[§39.124 D(i) cancellation, proposer12] D(i) (a dedicated job to characterise Li-
    coordinate displacement between B+ mid/last) was CANCELLED outright -- its named substitute,
    zero new core-h: record the displacement as a `bplus_agreement` covariate, same C-3
    "report, never decide" treatment as the existing Layer-I cutoff covariate.
    """

    def test_the_displacement_is_reported_regardless_of_agreement_verdict(self):
        a = _reactant()
        li = [k for k, at in enumerate(a) if at[0] == "Li"]
        self.assertTrue(li, "fixture must contain the cation this test is about")
        b = list(a)
        k = li[0]
        b[k] = (a[k][0], a[k][1] + 0.35, a[k][2], a[k][3])
        r = guards.bplus_agreement(a, b, -350.0, -350.0 + 5e-7)
        self.assertAlmostEqual(0.35, r["covariates"]["li_displacement_ang"], places=6)
        self.assertIn("never a decision input", r["covariates"]["_li_displacement_note"])

    def test_no_li_in_the_system_is_reported_not_silently_omitted(self):
        atoms = [("C", 0.0, 0.0, 0.0), ("O", 1.4, 0.0, 0.0)]
        r = guards.bplus_agreement(atoms, list(atoms), -350.0, -350.0)
        self.assertIsNone(r["covariates"]["li_displacement_ang"])
        self.assertIn("no Li atom", r["covariates"]["_li_displacement_note"])

    def test_it_does_not_change_the_agreement_verdict_itself(self):
        """C-3: reported, never decided on -- a large Li displacement must not flip `agreement`
        by itself, exactly like the Layer-I cutoff it sits beside."""
        a = _reactant()
        li = [k for k, at in enumerate(a) if at[0] == "Li"]
        b = list(a)
        k = li[0]
        b[k] = (a[k][0], a[k][1] + 5.0, a[k][2], a[k][3])   # a large, deliberately silly kick
        r = guards.bplus_agreement(a, b, -350.0, -350.0 + 5e-7)
        self.assertGreater(r["covariates"]["li_displacement_ang"], 4.9)
        self.assertTrue(r["covalent_graphs_match"], "Li is excluded from the Layer-C graph")
        self.assertTrue(r["agreement"], "the covariate must not itself decide agreement")


class TestReactantMatch(unittest.TestCase):
    """[§39.124 finding (c), corrected by critic16, tolerance RULED by proposer12] The missing
    half of condition 7: a B+ point checked against the CERTIFIED REACTANT itself, not just
    against the other B+ point (`bplus_agreement` above).

    🔴 [critic16, 04_REVIEW_LOG.md 26th batch] proposer12's original "0.17 A mid / 0.022 A last"
    premise was measured on the RAW B+ start geometries (pre-optimisation, byte-identical to the
    `.gjf` input) -- not the optimised endpoints these functions actually compare. The optimised
    reverse-arm pair matches the reactant to 0.0002-0.0005 A; a genuinely different basin
    (optimised forward-arm B+ points, which sit near the product) differs by 1.70-1.75 A. That is
    the real bracket -- see the module-level comment above `guards.reactant_match`.
    🟢 [§39.124 Ruling 1, corrected A4 then C2] THREE-WAY combination, NOT a plain AND, both
    tolerances defaulted to RULED constants (`REACTANT_MATCH_TOLERANCE_ANG` = 0.05 A,
    `BPLUS_ENERGY_TOLERANCE_EV` = 0.001 eV, reused): `True` only when BOTH the distance and
    energy clauses PASS; `False` only when BOTH definitely FAIL; a SPLIT (one passes, one fails)
    or either simply unmeasured is `None` -- the SAME "genuine ambiguity" rule
    `bplus_agreement`'s own clause (i)/(ii) split already uses, applied a second time.
    🔒 [critic16, then proposer12 A1] Condition 7 binds the `last` B+ point ONLY (not `mid`, not
    both) -- these tests exercise the function on either point interchangeably since the function
    itself does not know or care which one it was called on; a caller enforcing condition 7 must
    consult `last`.
    """

    #: O(1)-C(2) in `li_ec_radical_reactant.xyz`, ~1.40 A -- the same coordinate class (a ring
    #: C-O bond) §39.124's real numbers are about (reactant 1.4143 A).
    BREAK_PAIR = [(1, 2, "break:O-C")]
    #: Real ruled reactant energy is Hartree-scale; only the DELTA matters for the energy clause,
    #: so any anchor works as long as point/reactant are perturbed from the SAME value -- this
    #: mirrors `TestEnergyToleranceAgainstItsMeasuredBrackets`'s own convention in this file.
    E_REACTANT = -349.620897014

    def test_identical_geometry_and_energy_is_a_real_true(self):
        """🟢 THE STRUCTURAL FIX: with both ruled defaults and both real inputs, `match` reaches
        `True` -- previously impossible before the tolerance existed."""
        a = _reactant()
        r = guards.reactant_match(a, list(a), self.BREAK_PAIR,
                                  energy_point_hartree=self.E_REACTANT,
                                  energy_reactant_hartree=self.E_REACTANT)
        self.assertTrue(r["covalent_graphs_match"])
        self.assertTrue(r["match"], r["reasons"])
        self.assertAlmostEqual(0.0, r["break_bonds"][0]["delta_ang"], places=6)

    def test_missing_energy_leaves_match_none_even_with_a_perfect_distance(self):
        """Distance alone is not sufficient (Ruling 1/A4) -- an unmeasured energy must not let
        a perfect geometric match through."""
        a = _reactant()
        r = guards.reactant_match(a, list(a), self.BREAK_PAIR)
        self.assertTrue(r["covalent_graphs_match"])
        self.assertIsNone(r["match"], "energy clause unmeasured -> None, never a guessed True")

    def test_a_split_distance_fail_energy_pass_is_genuine_ambiguity_not_a_guessed_false(self):
        """🔴🔴 [§39.124 Ruling 1, corrected C2, proposer12's own final form] `False` requires
        BOTH clauses to fail -- a SPLIT (distance fails, energy passes) is `bplus_agreement`'s
        own "genuine ambiguity" rule applied a second time, exactly the same shape as its own
        clause (i)/(ii) split: `None`, never a guessed `False`. An EARLIER, WRONG draft of this
        function returned `False` on any single clause failure -- struck."""
        a = _reactant()
        b = list(a)
        # Move O(1) past the RULED 0.05 A tolerance -- still well inside Layer C's own (much
        # looser) bond-forming cutoff, so the graph is unchanged.
        b[1] = (a[1][0], a[1][1], a[1][2] + 0.2, a[1][3])
        r = guards.reactant_match(b, a, self.BREAK_PAIR,
                                  energy_point_hartree=self.E_REACTANT,
                                  energy_reactant_hartree=self.E_REACTANT)
        self.assertTrue(r["covalent_graphs_match"])
        self.assertGreater(r["break_bonds"][0]["delta_ang"], 0.15)
        self.assertIsNone(r["match"], "a split must not resolve to False")

    def test_both_clauses_failing_is_a_real_false(self):
        """The OTHER half of the three-way rule: BOTH distance and energy definitely fail ⟹
        `False`, not `None` -- an unambiguous non-match, not a data gap."""
        a = _reactant()
        b = list(a)
        b[1] = (a[1][0], a[1][1], a[1][2] + 0.2, a[1][3])
        r = guards.reactant_match(b, a, self.BREAK_PAIR,
                                  energy_point_hartree=self.E_REACTANT,
                                  energy_reactant_hartree=(self.E_REACTANT
                                                          + units.ev_to_hartree(0.686)))
        self.assertTrue(r["covalent_graphs_match"])
        self.assertFalse(r["match"])

    def test_a_coordination_isomer_energy_gap_alone_is_a_split_not_a_guessed_false(self):
        """🔴 [§39.124 Ruling 1, A4, corrected C2] A perfect distance match with an energy gap
        at the measured coordination-isomer separation (0.686 eV, §39.42(a)) is a SPLIT (distance
        passes, energy fails) -- `None`, per the ruled three-way logic, NOT `False`. This is the
        exact case the energy clause exists to catch from a bare `AND`/pass verdict, but the
        ruled combination rule stops it at "ambiguous", not "confidently wrong"."""
        a = _reactant()
        r = guards.reactant_match(a, list(a), self.BREAK_PAIR,
                                  energy_point_hartree=self.E_REACTANT,
                                  energy_reactant_hartree=(self.E_REACTANT
                                                          + units.ev_to_hartree(0.686)))
        self.assertTrue(r["covalent_graphs_match"])
        self.assertFalse(r["energy_delta_ev"] <= guards.BPLUS_ENERGY_TOLERANCE_EV)
        self.assertIsNone(r["match"])
        self.assertNotEqual(True, r["match"], "distance alone must not call this a match")

    def test_a_genuine_bifurcation_is_an_unambiguous_non_match_regardless_of_energy(self):
        """Pull the bond past the bond-forming cutoff entirely -- a real graph change needs no
        distance or energy tolerance to reject, even with a perfectly matching energy."""
        a = _reactant()
        b = list(a)
        b[1] = (a[1][0], a[1][1] - 2.0, a[1][2], a[1][3])
        r = guards.reactant_match(b, a, self.BREAK_PAIR,
                                  energy_point_hartree=self.E_REACTANT,
                                  energy_reactant_hartree=self.E_REACTANT)
        self.assertFalse(r["covalent_graphs_match"])
        self.assertFalse(r["match"])

    def test_a_missing_geometry_yields_no_match_not_a_guess(self):
        a = _reactant()
        r = guards.reactant_match(None, a, self.BREAK_PAIR)
        self.assertIsNone(r["match"])
        self.assertIn("unrun comparison", r["reasons"][0])

    def test_mismatched_atom_counts_refuse(self):
        a = _reactant()
        r = guards.reactant_match(a[:-1], a, self.BREAK_PAIR)
        self.assertIsNone(r["match"])
        self.assertIn("not the same system", r["reasons"][0])

    def test_no_pairs_supplied_is_recorded_not_silent(self):
        a = _reactant()
        r = guards.reactant_match(a, list(a), [],
                                  energy_point_hartree=self.E_REACTANT,
                                  energy_reactant_hartree=self.E_REACTANT)
        self.assertEqual([], r["break_bonds"])
        self.assertTrue(any("no break/form pairs supplied" in x for x in r["reasons"]))
        self.assertIsNone(r["match"], "distance clause unmeasurable -> None, not a guessed pass")

    def test_element_mismatch_at_a_declared_pair_raises_rather_than_silently_pairing(self):
        """Same guard `curvature.mode_overlap_omega` has, for the same reason: pairing by index
        across geometries whose atom order silently differs would project onto the wrong bond."""
        a = _reactant()
        swapped = list(a)
        swapped[1], swapped[2] = swapped[2], swapped[1]
        with self.assertRaises(ValueError):
            guards.reactant_match(swapped, a, self.BREAK_PAIR)


class TestBPlusStartPoints(unittest.TestCase):
    """🔴 [§39.70] The LAST point and the MIDPOINT BY ARC LENGTH -- never by index, and never
    the earliest point."""

    def test_the_midpoint_is_taken_on_the_reaction_coordinate_not_the_index(self):
        """A uniformly spaced arc and a badly non-uniform one pick different indices; only the
        arc-length rule is stable across both."""
        self.assertEqual((5, 10), guards.bplus_sample_points([0.1 * i for i in range(11)]))
        self.assertEqual((2, 4), guards.bplus_sample_points([0.0, 0.05, 0.4, 0.9, 1.0]))

    def test_it_never_returns_the_earliest_point(self):
        """🔴 A terminal optimisation started too near the saddle can ROLL BACK OVER IT into
        the other basin -- a spurious disagreement. Maximising separation is exactly the wrong
        instinct here, so this is pinned rather than left to a comment."""
        mid, last = guards.bplus_sample_points([0.0, 0.5, 1.0, 1.5, 2.0])
        self.assertGreater(mid, 0)
        self.assertLess(mid, last)

    def test_too_few_points_gives_nothing(self):
        self.assertIsNone(guards.bplus_sample_points([0.3]))
        self.assertIsNone(guards.bplus_sample_points([]))

    def test_against_the_real_p1_irc_log(self):
        """30 points, arc 0.076 -> 7.825. The arc midpoint is index 14, NOT the index midpoint
        and NOT the '20th of 30' an index-based reading would have given -- the arc is not
        uniform in index, which is the whole reason for the rule."""
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures",
                            "g16_irc_arc_lengths_p1.txt")
        with open(path, errors="replace") as fh:
            arc = g16.parse_irc_arc_lengths(fh.read())
        self.assertEqual(30, len(arc))
        mid, last = guards.bplus_sample_points(arc)
        self.assertEqual(29, last)
        self.assertEqual(14, mid)
        # 🔴 index 14, NOT the "20th of 30" an index-based reading gives, and not the index
        #    midpoint either -- the arc is not uniform in index, which is the rule's reason.
        self.assertLess(abs(arc[mid] - arc[-1] / 2.0), 0.2)


class TestBPlusFeedsConditionSevenBranchB(unittest.TestCase):
    """The output is shaped for `irc_direction_ok`'s `bplus` input, so a truncated IRC with
    agreement in both directions satisfies condition 7 branch (b) -- and one without it does
    not. These two are the whole contract between B+ and C-2."""

    E_TS = -350.0

    def _direction(self, agreement):
        return {"normal_termination": True, "n_points": 31,
                "energy_hartree": self.E_TS - 0.02,
                "completion": {"truncated": True, "minimum_found": False,
                               "termination_reason": "maxpoints"},
                "bplus": {"agreement": agreement}}

    def test_agreement_in_both_directions_establishes_the_connection(self):
        v = guards.irc_verdict(self._direction(True), self._direction(True), self.E_TS)
        self.assertEqual("ok", v["status"])

    def test_an_undetermined_bplus_does_not_establish_it(self):
        """🔴 `None` must behave like "not run", not like "agreed". This is the case a
        threshold-sensitive comparison produces, and it is the one most likely to be read as a
        pass by accident."""
        v = guards.irc_verdict(self._direction(None), self._direction(True), self.E_TS)
        self.assertEqual("indeterminate", v["status"])
        self.assertTrue(any("B+ was not run" in f for f in v["forward_failures"]), v)

    def test_a_disagreement_is_chemical_not_budget(self):
        v = guards.irc_verdict(self._direction(False), self._direction(True), self.E_TS)
        self.assertEqual("chemical", v["cause_class"])


class TestConditionSevenReactantMatchBindsBothBranches(unittest.TestCase):
    """[§39.124 Ruling 2, corrected A1] The reactant-match clause is joined by AND OUTSIDE the
    branch-(a)/branch-(b) EITHER/OR -- it binds BOTH branches, on the direction's own `last`
    endpoint. `guards.irc_direction_ok` consults an OPT-IN `direction["reactant_match"]` field
    (a pre-computed `guards.reactant_match()` result): ABSENT entirely preserves today's old
    behaviour (P1, the only live caller, has no mapping/reactant wiring and is permanently
    excluded -- retroactively hard-failing it is not this fix's job); PRESENT makes the clause
    real and binding, for either branch.
    """

    E_TS = -350.0
    MATCH_TRUE = {"match": True}
    MATCH_FALSE = {"match": False}
    MATCH_NONE = {"match": None}

    def _branch_b_direction(self, bplus_agreement=True, reactant_match=None):
        d = {"normal_termination": True, "n_points": 31,
             "energy_hartree": self.E_TS - 0.02,
             "completion": {"truncated": True, "minimum_found": False,
                            "termination_reason": "maxpoints"},
             "bplus": {"agreement": bplus_agreement}}
        if reactant_match is not None:
            d["reactant_match"] = reactant_match
        return d

    def _branch_a_direction(self, reactant_match=None):
        d = {"normal_termination": True, "n_points": 31,
             "energy_hartree": self.E_TS - 0.2,
             "completion": {"truncated": False, "minimum_found": True}}
        if reactant_match is not None:
            d["reactant_match"] = reactant_match
        return d

    # --- branch (a): convergence -------------------------------------------------------------

    def test_branch_a_with_no_reactant_match_supplied_is_unchanged(self):
        """Old behaviour preserved when the key is absent entirely -- not the same as a
        computed `None` verdict."""
        ok, fails, detail = guards.irc_direction_ok(self._branch_a_direction(), self.E_TS)
        self.assertIn("a: both directions converged", detail["connection_established_via"])

    def test_branch_a_with_a_real_reactant_match_true_establishes_the_connection(self):
        ok, fails, detail = guards.irc_direction_ok(
            self._branch_a_direction(self.MATCH_TRUE), self.E_TS)
        self.assertIn("a: both directions converged", detail["connection_established_via"])

    def test_branch_a_with_a_reactant_match_false_refuses_despite_convergence(self):
        """🔒 THE CASE RULING 2/A1 EXISTS FOR: a clean convergence to the WRONG minimum must
        still fail condition 7."""
        ok, fails, detail = guards.irc_direction_ok(
            self._branch_a_direction(self.MATCH_FALSE), self.E_TS)
        self.assertNotIn("connection_established_via", detail)
        self.assertTrue(any("does not (yet) verifiably MATCH" in f for f in fails), fails)

    def test_branch_a_with_a_reactant_match_none_does_not_establish_it(self):
        """`None` (measured but undetermined) must behave like `False` here, not like `True` --
        Rule 18: unknown is not permission."""
        ok, fails, detail = guards.irc_direction_ok(
            self._branch_a_direction(self.MATCH_NONE), self.E_TS)
        self.assertNotIn("connection_established_via", detail)

    def test_branch_a_with_the_key_present_but_the_bare_value_none_still_refuses(self):
        """🔴🔴 [critic16, 27th review batch] THE ACTUAL BUG, pinned: `payload/U56.sh`'s own
        error path sets `reactant_match["last"] = None` -- the BARE value `None`, not
        `{"match": None}` -- when the computation itself failed. An earlier version of the opt-
        in check used `d.get("reactant_match")` alone, which cannot tell that apart from the key
        being absent, and silently established the connection anyway. Fixed to `"reactant_match"
        in d` for presence; presence-with-`None` must FAIL exactly like presence-with-`False`."""
        d = {"normal_termination": True, "n_points": 31, "energy_hartree": self.E_TS - 0.2,
            "completion": {"truncated": False, "minimum_found": True},
            "reactant_match": None}   # bare None -- the exact shape U56.sh's failure path emits
        ok, fails, detail = guards.irc_direction_ok(d, self.E_TS)
        self.assertNotIn("connection_established_via", detail)
        self.assertTrue(any("does not (yet) verifiably MATCH" in f for f in fails), fails)

    # --- branch (b): maxpoints + B+ agreement -------------------------------------------------

    def test_branch_b_with_no_reactant_match_supplied_is_unchanged(self):
        ok, fails, detail = guards.irc_direction_ok(self._branch_b_direction(), self.E_TS)
        self.assertIn("b: maxpoints", detail["connection_established_via"])

    def test_branch_b_with_a_real_reactant_match_true_still_establishes_it(self):
        ok, fails, detail = guards.irc_direction_ok(
            self._branch_b_direction(reactant_match=self.MATCH_TRUE), self.E_TS)
        self.assertIn("b: maxpoints", detail["connection_established_via"])

    def test_branch_b_with_a_reactant_match_false_refuses_despite_bplus_agreement(self):
        ok, fails, detail = guards.irc_direction_ok(
            self._branch_b_direction(reactant_match=self.MATCH_FALSE), self.E_TS)
        self.assertNotIn("connection_established_via", detail)
        self.assertTrue(any("does not (yet) verifiably MATCH" in f for f in fails), fails)

    def test_branch_b_with_the_key_present_but_the_bare_value_none_still_refuses(self):
        """🔴🔴 [critic16, 27th review batch] Same bug, branch (b) -- `U56.sh`'s error path sets
        `reactant_match["last"] = None` (bare) on the truncated/B+-agreement side too."""
        d = self._branch_b_direction(bplus_agreement=True)
        d["reactant_match"] = None
        ok, fails, detail = guards.irc_direction_ok(d, self.E_TS)
        self.assertNotIn("connection_established_via", detail)
        self.assertTrue(any("does not (yet) verifiably MATCH" in f for f in fails), fails)

    def test_the_raw_reactant_match_record_is_always_carried_in_detail(self):
        """Compute-and-record vs. consult stay separate acts, same as `bplus` -- a reader must
        be able to see what was supplied even when it did not decide anything."""
        _, _, detail = guards.irc_direction_ok(
            self._branch_a_direction(self.MATCH_FALSE), self.E_TS)
        self.assertEqual(self.MATCH_FALSE, detail["reactant_match_last"])


class TestMinimumDistinctness(unittest.TestCase):
    """[§39.116(d), generalised by §39.124 Ruling 3, corrected A2] Is a declared IRC minimum a
    REAL, distinct structure, or a repeat of `U56_RB_scan`'s confirmed artifact (the IRC's own
    stopping criterion firing trivially on a flat coordinate ~0.02 A from the saddle)?

    🔴 [A2] The floor is an ABSOLUTE 0.025 A (not the original 0.05 A -- proposer12 found that
    sat just BELOW one real run's own healthy step band, 0.054-0.0605 A, defeating the check on
    exactly the case it protects) PLUS a self-calibrating relative check against the run's own
    median consecutive-point delta, preferred where available.
    """

    def _atoms(self, *offsets):
        """A tiny synthetic 3-atom set, one coordinate offset per atom (dx from a fixed base)."""
        base = [("C", 0.0, 0.0, 0.0), ("O", 1.4, 0.0, 0.0), ("H", 0.0, 1.0, 0.0)]
        return [(sym, x + dx, y, z) for (sym, x, y, z), dx in zip(base, offsets)]

    def test_identical_geometries_are_zero_delta_and_flagged_suspicious(self):
        """Zero structural change from the preceding point is the MOST extreme case the check
        exists to catch -- must be flagged, not waved through."""
        a = self._atoms(0.0, 0.0, 0.0)
        r = guards.minimum_distinctness(a, list(a))
        self.assertAlmostEqual(0.0, r["delta_ang"])
        self.assertTrue(r["suspicious"])

    def test_a_delta_below_the_absolute_floor_is_suspicious(self):
        a = self._atoms(0.0, 0.0, 0.0)
        b = self._atoms(0.01, 0.0, 0.0)      # 0.01 A < 0.025 A floor
        r = guards.minimum_distinctness(a, b)
        self.assertLess(r["delta_ang"], guards.MINIMUM_DISTINCTNESS_FLOOR_ANG)
        self.assertTrue(r["suspicious"])

    def test_a_delta_above_the_absolute_floor_with_no_run_data_is_not_suspicious(self):
        a = self._atoms(0.0, 0.0, 0.0)
        b = self._atoms(0.5, 0.0, 0.0)       # well clear of 0.025 A
        r = guards.minimum_distinctness(a, b)
        self.assertFalse(r["suspicious"])
        self.assertIsNone(r["median_consecutive_delta_ang"])

    def test_a_delta_clearing_the_absolute_floor_can_still_be_suspicious_relative_to_the_run(self):
        """🔴 THE CASE A2's FIX EXISTS FOR: a delta that clears the fixed floor but sits under
        half this run's own median step is still flagged -- the self-calibrating check catches
        what a bare constant cannot."""
        a = self._atoms(0.0, 0.0, 0.0)
        b = self._atoms(0.028, 0.0, 0.0)     # clears the 0.025 A floor, under half the median
        r = guards.minimum_distinctness(a, b, consecutive_deltas_ang=[0.06, 0.059, 0.061, 0.058])
        self.assertGreater(r["delta_ang"], guards.MINIMUM_DISTINCTNESS_FLOOR_ANG)
        self.assertAlmostEqual(0.0595, r["median_consecutive_delta_ang"], places=4)
        self.assertLess(r["delta_ang"], 0.5 * r["median_consecutive_delta_ang"])
        self.assertTrue(r["suspicious"], r)

    def test_a_single_prior_delta_does_not_degrade_into_a_meaningless_self_comparison(self):
        """🔴 [corrected C1, critic16] THE CONFIRMED FAILURE MODE: `U56_RB_scan` has exactly ONE
        post-saddle point. A naive median-of-1 would use that single delta as its own yardstick,
        making the relative test `delta < 0.5 * delta` -- structurally never true, silently
        disabling exactly the signal §39.116(d) needs. `MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS`
        (3) means this case gets ONLY the absolute floor, honestly reported as skipped rather
        than a degenerate always-false relative check."""
        a = self._atoms(0.0, 0.0, 0.0)
        b = self._atoms(0.02, 0.0, 0.0)      # below the 0.025 A absolute floor
        r = guards.minimum_distinctness(a, b, consecutive_deltas_ang=[0.02])
        self.assertIsNone(r["median_consecutive_delta_ang"], "relative check must be SKIPPED")
        self.assertEqual(1, r["n_prior_deltas"])
        self.assertTrue(r["suspicious"], "the absolute floor alone must still catch this")

    def test_the_absolute_floor_stays_active_even_with_plenty_of_prior_deltas(self):
        """🔴 [corrected C1, critic16] OR, never if/else: a uniformly-degenerate path (small
        median AND small tested delta) must still be caught by the absolute floor even when
        >=3 prior deltas exist -- an EARLIER, WRONG draft used if/else and would have let a
        relative-only check wave this through (0.005 A clears half of an 0.008 A median)."""
        a = self._atoms(0.0, 0.0, 0.0)
        b = self._atoms(0.005, 0.0, 0.0)     # below the 0.025 A absolute floor
        r = guards.minimum_distinctness(
            a, b, consecutive_deltas_ang=[0.008, 0.0079, 0.0081, 0.008])
        self.assertIsNotNone(r["median_consecutive_delta_ang"], "relative check DID run")
        self.assertTrue(r["suspicious"], "the absolute floor must still fire")

    def test_missing_geometry_yields_no_measurement_not_a_guess(self):
        r = guards.minimum_distinctness(None, self._atoms(0.0, 0.0, 0.0))
        self.assertIsNone(r["delta_ang"])
        self.assertIsNone(r["suspicious"])

    def test_mismatched_atom_count_yields_no_measurement(self):
        a = self._atoms(0.0, 0.0, 0.0)
        self.assertIsNone(guards.structural_distinctness(a, a[:-1]))

    def test_structural_distinctness_is_rotation_and_translation_invariant(self):
        """Interatomic distances alone -- shifting the WHOLE second structure must not register
        as a change."""
        a = self._atoms(0.0, 0.0, 0.0)
        shifted = [(sym, x + 10.0, y + 5.0, z - 3.0) for sym, x, y, z in a]
        self.assertAlmostEqual(0.0, guards.structural_distinctness(a, shifted), places=9)


class TestIRCPathFrames(unittest.TestCase):
    """[39.70] Pairing each IRC path point with ITS geometry — the input B+ selects two of.

    🔴 The geometry is the orientation block PRECEDING the point's `NET REACTION COORDINATE`
    marker, not the last block in the file. An IRC log contains orientation blocks that are not
    path points, so pairing by file order attaches the wrong structure to a point -- silently,
    and B+ would then optimise from a geometry that is not on the path at all.

    ⚠ COVERAGE, STATED: the only real IRC logs this project ever had
    (`jobs/P1/irc_{forward,reverse}.log`) are no longer in the returned tree -- they were read
    earlier today and are gone. The verbatim fixtures kept here are TAILS and marker lines, not
    whole paths, so the geometry pairing below is exercised on a synthetic log. That is a real
    gap, not a stylistic one, and it is written down rather than papered over.
    """

    SYNTHETIC = """
                          Input orientation:
 ---------------------------------------------------------------------
 Center     Atomic      Atomic             Coordinates (Angstroms)
 Number     Number       Type             X           Y           Z
 ---------------------------------------------------------------------
      1          6           0        0.000000    0.000000    0.000000
      2          8           0        0.000000    0.000000    1.400000
 ---------------------------------------------------------------------
   NET REACTION COORDINATE UP TO THIS POINT =    0.10000
                          Input orientation:
 ---------------------------------------------------------------------
 Center     Atomic      Atomic             Coordinates (Angstroms)
 Number     Number       Type             X           Y           Z
 ---------------------------------------------------------------------
      1          6           0        0.000000    0.000000    0.000000
      2          8           0        0.000000    0.000000    1.900000
 ---------------------------------------------------------------------
   NET REACTION COORDINATE UP TO THIS POINT =    0.60000
"""

    def test_each_point_gets_the_geometry_that_precedes_its_marker(self):
        pts = g16.parse_irc_path_frames(self.SYNTHETIC)
        self.assertEqual(2, len(pts))
        self.assertAlmostEqual(0.1, pts[0]["arc"])
        self.assertAlmostEqual(0.6, pts[1]["arc"])
        self.assertAlmostEqual(1.4, pts[0]["geometry"][1][3], places=6)
        self.assertAlmostEqual(1.9, pts[1]["geometry"][1][3], places=6)

    def test_a_marker_with_no_preceding_block_yields_no_geometry_not_a_wrong_one(self):
        """Rule 18 again: better an explicit None than the previous point's structure."""
        pts = g16.parse_irc_path_frames(
            "   NET REACTION COORDINATE UP TO THIS POINT =    0.10000\n")
        self.assertEqual(1, len(pts))
        self.assertIsNone(pts[0]["geometry"])

    def test_a_block_is_not_reused_for_two_points(self):
        text = self.SYNTHETIC + ("   NET REACTION COORDINATE UP TO THIS POINT =    0.90000\n")
        pts = g16.parse_irc_path_frames(text)
        self.assertEqual(3, len(pts))
        self.assertIsNone(pts[2]["geometry"],
                          "the third marker has no block of its own and must not inherit one")


class TestEnergyToleranceAgainstItsMeasuredBrackets(unittest.TestCase):
    """🔴 [§39.71] The tolerance is a DERIVED CONSTANT and the ruling says so out loud: §39.70
    called for "the optimiser's own convergence criterion", which presumes an engine that
    converges on ENERGY, and **G16 does not** -- four rows in its table, none of them energy.
    The criterion was written from xtb's behaviour and applied to a G16 stage (the C-8.1 grid
    seam's class: a criterion carried across a boundary it does not survive).

    What survives is that **every input is a number G16 itself prints**:
        max force 4.5e-4 Ha/bohr x max displacement 1.8e-3 bohr ~ 8e-7 Ha per coordinate,
        x 3N (63 at 21 atoms) ~ 5e-5 Ha ~ 1.4e-3 eV  ->  ruled flat at ~1e-3 eV.

    These tests pin it against the two MEASURED quantities that bracket it, so a future change
    has to move past real data rather than past an argument.
    """

    SAME_BASIN_SPREAD_EV = 5.0e-4        # 11 atoms, 6 kick seeds (19_seed_n1) -- the largest
    DIFFERENT_BASIN_EV = 0.686           # 21 atoms, the sixth seed (10_seed_basins)

    def test_the_largest_measured_same_basin_spread_still_agrees(self):
        a = _reactant()
        d = units.ev_to_hartree(self.SAME_BASIN_SPREAD_EV)
        self.assertTrue(guards.bplus_agreement(a, list(a), -350.0, -350.0 + d)["agreement"])

    def test_a_measured_different_basin_pair_is_not_agreement(self):
        """🔴 THE CASE CLAUSE (ii) EXISTS FOR, and why dropping it was refused: this pair has
        the SAME covalent graph and sits 0.686 eV apart. Clause (i) alone would call it
        agreement and establish a connection that is not there."""
        a = _reactant()
        d = units.ev_to_hartree(self.DIFFERENT_BASIN_EV)
        r = guards.bplus_agreement(a, list(a), -350.0, -350.0 + d)
        self.assertNotEqual(True, r["agreement"])
        self.assertTrue(r["covalent_graphs_match"],
                        "same covalent graph is the whole point of this case")

    def test_the_tolerance_sits_between_its_two_brackets(self):
        """~2x above the largest measured same-basin spread, ~700x below the measured
        different-basin separation. If either bracket moves past it, this goes red."""
        self.assertGreater(guards.BPLUS_ENERGY_TOLERANCE_EV, self.SAME_BASIN_SPREAD_EV)
        self.assertLess(guards.BPLUS_ENERGY_TOLERANCE_EV, self.DIFFERENT_BASIN_EV / 100.0)

    def test_the_derivation_and_the_brackets_are_recorded_where_the_constant_is(self):
        """A derived constant whose derivation lives elsewhere is a magic number with a
        footnote. Both the arithmetic and the measured brackets sit beside it."""
        import inspect
        src = inspect.getsource(guards)
        head = src[:src.index("BPLUS_ENERGY_TOLERANCE_EV = ")]
        for token in ("4.5e-4", "1.8e-3", "0.686 eV", "NOT CONSTANT-FREE"):
            self.assertIn(token, head, token)


class TestTheWiringInThePayload(unittest.TestCase):
    """B+ is now wired: two terminal optimisations per IRC direction, at the TS chain's own
    DFT level, from the last path point and the arc-length midpoint.

    ⚠ COVERAGE, STATED PLAINLY: these are SOURCE-level checks. The only real IRC logs this
    project had are gone from the returned tree, so the end-to-end path (real IRC -> two start
    geometries -> two optimisations -> verdict) has never been exercised on real data. What is
    pinned here are the properties that would be wrong quietly: the level, the start points,
    and the absence of a fallback.
    """

    def setUp(self):
        with open(os.path.join(context.PKG_ROOT, "payload", "U56.sh"), errors="replace") as fh:
            self.src = fh.read()

    def test_the_terminal_optimisations_run_at_the_dft_level_not_gfn2(self):
        """🔴 GFN2 merges exactly the Li-coordination basins B+ exists to tell apart
        (§39.38(d)/U-55), so a GFN2 terminal opt produces FALSE AGREEMENT -- the one error this
        test is for. The route must be the TS chain's own `$LVL`."""
        self.assertIn('sei_qc_input "$D/bplus_${dir}_${_bp}.gjf" "$LVL" endpoint_opt_rough',
                      self.src)
        self.assertIn("NOT GFN2", self.src)

    def test_both_start_points_are_generated_and_neither_is_the_earliest(self):
        self.assertIn("bplus_sample_points", self.src)
        self.assertIn("arc-length midpoint", self.src)
        self.assertIn("ROLL BACK OVER IT", self.src,
                      "the reason not to take the earliest point must travel with the code")

    def test_an_unavailable_start_point_yields_no_verdict_rather_than_a_pass(self):
        self.assertIn("an unrun comparison is not an agreement", self.src)

    def test_reactant_match_is_wired_for_both_bplus_points(self):
        """[§39.124 finding (c)] The missing check now runs, on BOTH mid and last -- mid as
        diagnostic data, `last` as what condition 7 actually binds (Ruling 2/A1)."""
        self.assertIn("guards.reactant_match(\n        geom_a, atoms_r, pairs,", self.src)
        self.assertIn("guards.reactant_match(\n        geom_b, atoms_r, pairs,", self.src)
        self.assertIn('certs.get("reactant_xyz")', self.src)
        self.assertIn("reactant_match", self.src)
        self.assertIn("binds", self.src)

    def test_reactant_match_energy_clause_is_wired_with_the_certified_reactants_own_energy(self):
        """[§39.124 Ruling 1, corrected A4, critic16 B1] Distance alone is insufficient
        (coordination isomers) -- the payload must feed the reactant's OWN converged energy, not
        skip the clause. AND that energy must be a STRUCTURED field copied from
        `endpoint_prep.sh`'s own certification output, never a cross-job log re-parse at gate
        time (critic16, explicit)."""
        self.assertIn('(certs.get("reactant_cert") or {}).get("energy_hartree")', self.src)
        self.assertIn("energy_point_hartree=e_a, energy_reactant_hartree=r_energy", self.src)
        self.assertIn("energy_point_hartree=e_b, energy_reactant_hartree=r_energy", self.src)
        # 🔴 The `resolve()` function -- NOT this heredoc -- is where the field is copied
        # through from `f1_observables.json`; assert against the real source, not a guess.
        self.assertIn('"energy_hartree": f1.get("energy_hartree")', self.src)

    def test_resolve_does_not_re_parse_the_endpoint_log_for_energy(self):
        """[critic16 B1, explicit] "do not implement it as a cross-job log grep at gate time" --
        `g16.parse_scf` must not appear in `resolve()`'s own log-reading block (only
        `g16.last_geometry`, already there for the geometry)."""
        start = self.src.index("def resolve(role, endpoint_key, xyz_override):")
        end = self.src.index("\nr_cert, r_xyz, r_src, planar = resolve(")
        resolve_src = self.src[start:end]
        self.assertNotIn("g16.parse_scf", resolve_src)
        self.assertIn("g16.last_geometry", resolve_src)

    def test_the_verdict_reaches_the_reply(self):
        with open(os.path.join(context.PKG_ROOT, "sei_pilot", "collect.py"),
                  errors="replace") as fh:
            collect_src = fh.read()
        self.assertIn('"bplus": dict(', collect_src)
        self.assertIn('bplus_%s.json', collect_src)


if __name__ == "__main__":
    unittest.main()
