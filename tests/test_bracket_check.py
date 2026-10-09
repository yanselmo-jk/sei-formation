"""[39.63] The bracket check — the first gate on a TS candidate, and the one that catches P1.

Each breaking bond's distance AT THE SADDLE must lie strictly between the two certified
endpoints' values for that bond. No threshold: both endpoint values are C-8-certified numbers
we already hold, and "between" is not tunable.

🔴 It is the CHEAPEST gate and the only one with a demonstrated hit, so it runs FIRST. It also
makes a stronger statement than the spectator test: not "the mode looks wrong" but "the bond
this saddle is supposed to be breaking is already broken, past the product". Geometry only --
no vibrational analysis, no mode, no Omega.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import curvature, guards
from sei_pilot.criteria import g16

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "g16_normal_modes_p1_ts.log")

#: 39.63's measured values for P1's intended break, d(O2-C3), in Angstrom.
P1_REACTANT_ANG = 1.405
P1_PRODUCT_ANG = 2.503


class TestBracketCheckCatchesP1(unittest.TestCase):
    def test_p1_saddle_is_refused_by_the_bracket_check(self):
        r = guards.bracket_check({"O2-C3": 3.184},
                                 {"O2-C3": P1_REACTANT_ANG}, {"O2-C3": P1_PRODUCT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertTrue(r["refused"])
        self.assertIn("beyond the product", r["reasons"][0])
        self.assertFalse(r["bonds"][0]["two_sided_ok"])

    def test_the_saddle_distance_comes_from_the_real_log_not_a_literal(self):
        """The 3.184 A above is not a number someone typed -- it is what the delivered P1
        transition state's own geometry says."""
        with open(FIXTURE, errors="replace") as fh:
            parsed = g16.parse_normal_modes(fh.read())
        rows = curvature.mode_overlap_omega(
            g16.imaginary_modes(parsed)[0], parsed["geometry"], [(1, 2, "O2-C3")])
        self.assertAlmostEqual(3.184, rows[0]["distance_ang"], places=3)
        self.assertGreater(rows[0]["distance_ang"], P1_PRODUCT_ANG,
                           "the bond is already broken PAST the product at this 'saddle'")

    def test_a_saddle_inside_the_bracket_passes(self):
        """0-o.4 rule 4: the gate must be satisfiable, or it is not a gate."""
        r = guards.bracket_check({"O2-C3": 1.9},
                                 {"O2-C3": P1_REACTANT_ANG}, {"O2-C3": P1_PRODUCT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertFalse(r["refused"])
        self.assertTrue(r["bonds"][0]["two_sided_ok"])

    def test_behind_the_reactant_is_refused_by_the_one_sided_half(self):
        r = guards.bracket_check({"O2-C3": 1.2},
                                 {"O2-C3": P1_REACTANT_ANG}, {"O2-C3": P1_PRODUCT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertTrue(r["refused"])
        self.assertIn("SHORTER than the certified reactant", r["reasons"][0])

    def test_p1_is_caught_by_the_mechanism_coordinate_with_the_reactant_alone(self):
        """🔴 [39.66] THE COVERAGE FIX. With directions derived, the one-sided half catches P1
        on ALL THREE arms using certified-reactant numbers only -- no certified product, no
        GFN2 bracket, no calibration. P1's Li-O2 FORMS along the path and sits 3.980 A at the
        saddle against a reactant at 2.489: 1.491 A past the reactant, on the exact side a
        reactant-only bound can see (and more than twice the break coordinate's violation)."""
        r = guards.bracket_check(
            {"O2-C3": 3.184, "Li-O2": 3.980, "Li-O6": 1.747},
            {"O2-C3": 1.405, "Li-O2": 2.489, "Li-O6": 1.709},
            directions={"O2-C3": "break", "Li-O2": "form", "Li-O6": "break"})
        self.assertTrue(r["refused"])
        self.assertTrue(any("FORMS along the path" in x for x in r["reasons"]), r["reasons"])

    def test_the_breaking_bond_half_alone_does_NOT_catch_p1(self):
        """🔒 [39.66] Keep the credit where it belongs. On the BREAK coordinate P1 overshoots
        past the PRODUCT (3.184 vs 2.503), which a reactant-only bound cannot see. The hit
        belongs to the mechanism/FORM coordinate specifically -- if this ever turns red, the
        two routes have been blurred and someone will trust the wrong one."""
        r = guards.bracket_check({"O2-C3": 3.184}, {"O2-C3": P1_REACTANT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertFalse(r["refused"])

    def test_a_non_monotonic_coordinate_is_counted_not_dropped(self):
        r = guards.bracket_check({"x": 2.0}, {"x": 1.4}, directions={"x": None})
        self.assertFalse(r["refused"])
        self.assertEqual(["x"], r["non_monotonic"])
        self.assertFalse(r["bonds"][0]["applicable"])
        self.assertIsNone(r["bonds"][0]["one_sided_ok"])

    def test_the_direction_is_what_makes_widening_the_input_safe(self):
        """🔴 [39.66] INVERTED from the earlier anti-widening test, which pinned the right
        hazard with the wrong remedy. A forming coordinate given a BREAK direction still
        refuses by construction -- so the guard is not "keep the input narrow" but "give each
        coordinate its derived direction". Both halves are pinned here."""
        forming = {"Li-O": 2.0}, {"Li-O": 2.65}
        self.assertTrue(guards.bracket_check(*forming,
                                             directions={"Li-O": "break"})["refused"],
                        "a forming coordinate mislabelled BREAK must still refuse")
        self.assertFalse(guards.bracket_check(*forming,
                                              directions={"Li-O": "form"})["refused"],
                         "with its correct direction the same coordinate passes")

    def test_an_absent_direction_gets_no_one_sided_bound_and_is_counted(self):
        """🔴 [critic10] An absent direction must be `None`, never `"break"`. Defaulting to
        break gives a FORMING coordinate break semantics: on P1's own numbers Li-O2 (reactant
        2.489, saddle 3.980) would PASS silently -- the exact coordinate 39.66 exists to catch
        it with. `None` costs the bound on that coordinate, but the loss is COUNTED."""
        r = guards.bracket_check({"Li-O2": 3.980}, {"Li-O2": 2.489})
        self.assertFalse(r["refused"])
        self.assertEqual(["Li-O2"], r["non_monotonic"])
        self.assertIn("absent", r["bonds"][0]["direction_source"])
        # and with the direction actually derived, it refuses
        self.assertTrue(guards.bracket_check({"Li-O2": 3.980}, {"Li-O2": 2.489},
                                             directions={"Li-O2": "form"})["refused"])

    # NOTE: an earlier `test_the_contract_is_BREAKING_bonds_and_orientation_therefore_matters`
    # lived here. It pinned the right hazard with the wrong remedy -- it relied on an absent
    # direction defaulting to `break`, which is precisely the default critic10 showed is
    # dangerous. Its content is now covered twice over, and better:
    #   `test_the_direction_is_what_makes_widening_the_input_safe`  (mislabelled -> refuses)
    #   `test_an_absent_direction_gets_no_one_sided_bound_and_is_counted`  (absent -> counted)
    # Deleted rather than adapted, so nobody re-derives the old contract from a stale test.


class TestOneSidedHalfCoversEveryArm(unittest.TestCase):
    """🔴 [39.65] Every arm has a certified REACTANT, so the one-sided half runs everywhere
    using certified numbers only: the saddle's breaking-bond distance must not be SHORTER than
    the reactant's. A "transition state" with the bond MORE FORMED than the reactant is not on
    a bond-breaking path at all.

    🔴 IT DOES NOT INHERIT THE P1 HIT. P1 failed on the PRODUCT side, and the tests below say
    so explicitly so that nobody reads the one-sided half as covering that case.
    """

    def test_shorter_than_the_reactant_is_refused(self):
        r = guards.bracket_check({"O2-C3": 1.2}, {"O2-C3": P1_REACTANT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertTrue(r["refused"])
        self.assertIn("SHORTER than the certified reactant", r["reasons"][0])
        self.assertFalse(r["bonds"][0]["one_sided_ok"])

    def test_the_one_sided_half_alone_does_NOT_catch_p1(self):
        """🔒 The uncomfortable half of 39.65, as a test rather than a caveat: with no
        certified product, P1's saddle PASSES. The demonstrated hit belongs to the two-sided
        half only, and an arm running without a product does not have it."""
        r = guards.bracket_check({"O2-C3": 3.184}, {"O2-C3": P1_REACTANT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertFalse(r["refused"])
        self.assertTrue(r["bonds"][0]["one_sided_ok"])
        self.assertIsNone(r["bonds"][0]["two_sided_ok"])

    def test_the_missing_product_side_is_counted_as_awaiting_calibration(self):
        """🔒 Not a bare "not applicable": 39.65(3)'s free calibration lands in the same round
        (R-A holds both a certified and a GFN2 product distance for this coordinate), and the
        two strings say different things to whoever reads the reply."""
        r = guards.bracket_check({"O2-C3": 1.9}, {"O2-C3": P1_REACTANT_ANG},
                                 directions={"O2-C3": "break"})
        self.assertEqual("awaiting_calibration", r["product_side_status"])
        self.assertEqual("awaiting_calibration", r["bonds"][0]["product_side"])
        self.assertTrue(any("must not be read as though it did" in x for x in r["reasons"]))

    def test_a_two_sided_arm_reports_that_it_actually_checked_the_product_side(self):
        r = guards.bracket_check({"O2-C3": 1.9}, {"O2-C3": P1_REACTANT_ANG},
                                 {"O2-C3": P1_PRODUCT_ANG}, directions={"O2-C3": "break"})
        self.assertEqual("checked", r["product_side_status"])
        self.assertTrue(r["bonds"][0]["two_sided_ok"])

    def test_no_bonds_at_all_does_not_read_as_a_pass(self):
        r = guards.bracket_check({}, {}, {})
        self.assertTrue(r["refused"])
        self.assertIn("establishes nothing", r["reasons"][0])

    def test_a_partly_bracketed_arm_reports_awaiting_calibration(self):
        r = guards.bracket_check({"a": 1.9, "b": 1.9}, {"a": 1.4, "b": 1.4}, {"a": 2.5},
                                 directions={"a": "break", "b": "break"})
        self.assertEqual("awaiting_calibration", r["product_side_status"])
        self.assertTrue(r["bonds"][0]["two_sided_ok"])
        self.assertIsNone(r["bonds"][1]["two_sided_ok"])

    def test_every_declared_bond_is_checked_not_just_the_first(self):
        r = guards.bracket_check({"a": 1.9, "b": 9.0},
                                 {"a": 1.4, "b": 1.4}, {"a": 2.5, "b": 2.5},
                                 directions={"a": "break", "b": "break"})
        self.assertTrue(r["refused"])
        self.assertEqual(2, len(r["bonds"]))
        self.assertTrue(r["bonds"][0]["two_sided_ok"])
        self.assertFalse(r["bonds"][1]["two_sided_ok"])


if __name__ == "__main__":
    unittest.main()
