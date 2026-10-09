"""[§39.4(c) M2' / §39.26(d) / §39.56] Omega — 허수모드의 **성격** 판정용 수치.

🔴 이 파일이 존재하는 이유는 P1 이다. P1 의 "TS" 는 exactly-one-imaginary-frequency 검사를
**통과했고**(`freq.passed: true`), 두 라운드 동안 아무 게이트에도 안 걸렸다. 그런데 그 모드는
Li+ 가 배위자리 사이를 넘어가는 spectator 운동이었고, 의도한 C-O 결합은 그 기하에서 **이미
3.18 A 로 끊어져 있었다.** 크기(|nu_imag|)로는 "무른 진짜 TS"와 "틀린 saddle"을 가를 수 없다 —
방향이 문제이기 때문이다. Omega 가 그 방향이다.

⚠ 판정은 하지 않는다(C-3 / U-57): Omega_min 은 보정 대상이지 주장 대상이 아니다. 이 테스트는
**수치가 재현되는지**만 고정한다.
"""

import math
import os
import unittest

import context  # noqa: F401
from sei_pilot import curvature
from sei_pilot.criteria import g16

FIXTURE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "fixtures", "g16_normal_modes_p1_ts.log")

#: P1 TS 기하의 원자 순서(로그의 orientation 블록 그대로), 0-based:
#: 0 C · 1 O · 2 C · 3 C · 4 O · 5 O · 6-9 H · 10 Li
#: §39.56 이 이름 붙인 결합들. label 은 1-based 표기(문서와 맞추기 위함).
PAIRS = [(1, 2, "O2-C3"), (1, 0, "O2-C1"), (4, 3, "O5-C4"), (10, 5, "Li-O6")]


def _omega_unweighted(mode, geometry, i, j):
    """The shortcut definition -- deliberately WRONG, kept only as a negative case.

    🔴 NOT the specification. §39.4(c) requires `Omega = |proj_b(q)| / |q|` with q the
    MASS-WEIGHTED mode (`q = sqrt(m) * l_cart`) and b the mass-weighted B-row
    (`+-u / sqrt(m)`), the projection being taken along the NORMALISED b.

    This helper reproduces what produced §39.56's original 0.036, and it deviates in TWO
    ways, which is why "unweighted" alone does not reproduce it:
      (1) no masses anywhere, and
      (2) the projection is the raw displacement DIFFERENCE along u -- i.e. b is not
          normalised (|b| = sqrt(2) for a bond), so every value comes out sqrt(2) larger
          than the plain unweighted-with-normalised-b form.
    It lives in the test file and never in `sei_pilot/`, so production has no switch that
    can select it.
    """
    disp = mode["displacements"]
    d = [geometry[i][1 + k] - geometry[j][1 + k] for k in range(3)]
    r = math.sqrt(sum(v * v for v in d))
    u = [v / r for v in d]
    dv = [disp[i][1 + k] - disp[j][1 + k] for k in range(3)]
    q = [c for (_s, dx, dy, dz) in disp for c in (dx, dy, dz)]
    nq = math.sqrt(sum(v * v for v in q))
    return abs(sum(dv[k] * u[k] for k in range(3))) / nq


def _parsed():
    with open(FIXTURE, errors="replace") as fh:
        return g16.parse_normal_modes(fh.read())


class TestNormalModeParserAgainstTheRealLog(unittest.TestCase):
    """파서를 기억으로 짓지 않았다는 것을 고정한다 — 이 프로젝트가 가진 **유일한** 실
    normal-mode 블록에 대고 맞춘 값이다."""

    def test_all_modes_are_read(self):
        p = _parsed()
        self.assertEqual(11, len(p["geometry"]))
        self.assertEqual(27, len(p["modes"]), "11원자 비선형 => 3N-6 = 27")
        self.assertEqual([], p["warnings"], p["warnings"])

    def test_exactly_one_imaginary_mode_and_its_measured_values(self):
        p = _parsed()
        imag = g16.imaginary_modes(p)
        self.assertEqual(1, len(imag))
        self.assertAlmostEqual(-48.4416, imag[0]["freq_cm1"], places=4)
        self.assertAlmostEqual(7.1479, imag[0]["reduced_mass_amu"], places=4)

    def test_geometry_comes_from_the_orientation_that_precedes_the_modes(self):
        """🔴 변위는 그 orientation 계에서 정의된다 — 다른 블록의 좌표와 섞으면 결합
        방향이 회전한 채로 projection 이 계산되고, 숫자는 나오고 조용히 틀린다."""
        p = _parsed()
        self.assertEqual([a[0] for a in p["geometry"]],
                         [d[0] for d in p["modes"][0]["displacements"]])


class TestOmegaReproducesTheMeasuredValues(unittest.TestCase):
    """§39.56 의 실측 재현. 🔒 값을 맞추려고 정의를 조정하지 않았다 — M2'(§39.4(c))의
    `Omega = |proj_b(q)| / |q|`, q = 질량가중 허수모드, 를 그대로 구현한 결과다."""

    def setUp(self):
        p = _parsed()
        self.rows = curvature.mode_overlap_omega(
            g16.imaginary_modes(p)[0], p["geometry"], PAIRS)
        self.by = dict((r["label"], r) for r in self.rows)

    def test_the_intended_break_coordinate_carries_almost_none_of_the_mode(self):
        """의도한 alkyl C-O 파괴 좌표: Omega = 0.022. **이것이 P1 의 판정이다.**"""
        self.assertAlmostEqual(0.022, self.by["O2-C3"]["omega"], places=3)

    def test_the_intended_bond_is_already_broken_at_that_geometry(self):
        """d(O2-C3) = 3.18 A — 닫힌 고리와 열린 고리 **사이**가 아니라 이미 열린
        생성물 표면 위의 saddle 이었다."""
        self.assertAlmostEqual(3.184, self.by["O2-C3"]["distance_ang"], places=3)

    def test_the_other_candidate_coordinates_are_no_better(self):
        self.assertAlmostEqual(0.008, self.by["O2-C1"]["omega"], places=3)
        self.assertAlmostEqual(1.226, self.by["O2-C1"]["distance_ang"], places=3)
        self.assertAlmostEqual(0.002, self.by["O5-C4"]["omega"], places=3)
        self.assertAlmostEqual(1.423, self.by["O5-C4"]["distance_ang"], places=3)

    def test_li_o6_is_the_mass_weighted_value_not_the_unweighted_shortcut(self):
        """🔴 RESOLVED (proposer7, 2026-08-20): §39.56 first published 0.036 for this bond.
        That number came from an UNWEIGHTED projection -- raw Cartesian displacements, no
        masses. §39.4(c) specifies the MASS-WEIGHTED form, which gives 0.0298.

        🔒 Why only this row moved, and why that matters more than the number:
        mass weighting nearly cancels between atoms of SIMILAR mass -- C 12.011 vs O 15.999
        is a sqrt-ratio of 1.15 -- so the three C/O bonds agree to 3 decimals under either
        definition and the shortcut looked correct. Li 6.941 vs O 15.999 is a sqrt-ratio of
        1.52, and there the two forms diverge by ~20 %.
        ⟹ THE UNWEIGHTED FORM MIS-MEASURES OMEGA EXACTLY FOR COORDINATES INVOLVING THE LIGHT
          SPECTATOR CATION -- which is the class Omega exists to detect. The error is
          invisible on every C/O bond and decisive on the one that matters.
        Today's verdict does not move (0.022 vs O(1) for a real reaction coordinate), but
        U-57 exists for near-floor cases, and that is where a 20 % definition error decides.
        """
        self.assertAlmostEqual(1.747, self.by["Li-O6"]["distance_ang"], places=3)
        self.assertAlmostEqual(0.0298, self.by["Li-O6"]["omega"], places=4)

    def test_the_unweighted_shortcut_is_pinned_as_a_negative_case(self):
        """🔴 NEGATIVE CASE, on purpose. This reproduces the WRONG definition and asserts
        production does not return it. If anyone ever re-introduces the unweighted shortcut,
        `mode_overlap_omega` starts returning 0.0361 here and this test goes RED."""
        p = _parsed()
        unweighted = _omega_unweighted(g16.imaginary_modes(p)[0], p["geometry"], 10, 5)
        self.assertAlmostEqual(0.0361, unweighted, places=4,
                               msg="the shortcut itself must still reproduce 0.036 -- "
                                   "otherwise this negative case has stopped guarding "
                                   "anything")
        self.assertNotAlmostEqual(unweighted, self.by["Li-O6"]["omega"], places=3)
        # and it is INDISTINGUISHABLE on a C/O bond -- which is why it went unnoticed
        self.assertAlmostEqual(
            _omega_unweighted(g16.imaginary_modes(p)[0], p["geometry"], 1, 2),
            self.by["O2-C3"]["omega"], places=3)

    def test_the_mode_sits_on_a_spectator_cation(self):
        p = _parsed()
        loc = curvature.mode_mass_localisation(g16.imaginary_modes(p)[0], p["geometry"])
        top = max(loc, key=lambda r: r["amplitude_fraction"])
        self.assertEqual("Li", top["element"])
        self.assertAlmostEqual(0.63, top["amplitude_fraction"], places=2)


class TestOmegaRefusesMismatchedInputs(unittest.TestCase):
    """🔴 두 잡의 원자 순서가 다른데 index 로 짝지으면 **다른 결합의 Omega** 가 조용히
    나온다. 그럴 바엔 raise 한다 (conformers.rmsd 가 같은 이유로 같은 선택을 한다)."""

    def test_atom_count_mismatch_raises(self):
        p = _parsed()
        self.assertRaises(ValueError, curvature.mode_overlap_omega,
                          g16.imaginary_modes(p)[0], p["geometry"][:-1], PAIRS)

    def test_element_order_mismatch_raises(self):
        p = _parsed()
        geom = list(p["geometry"])
        geom[0], geom[1] = geom[1], geom[0]
        self.assertRaises(ValueError, curvature.mode_overlap_omega,
                          g16.imaginary_modes(p)[0], geom, PAIRS)


class TestSpectatorTest(unittest.TestCase):
    """🔴 [39.62] The gate is the SPECTATOR TEST, not Omega. Threshold-free: block iff the
    single most-displaced atom is OUTSIDE the declared coordinate set AND outstrips the whole
    set together.

    Deliberately permissive, because the two errors do not cost the same:
      FALSE BLOCK (the mode IS the coordinate) -> a lost REACTION, quiet and expensive.
      FALSE PASS  (spectator, IRC funded)      -> ~325 core-h (11 atoms) / ~3,120 (21 atoms),
                                                  and the SAME `indeterminate` either way.
    """

    def setUp(self):
        self.p = _parsed()
        self.mode = g16.imaginary_modes(self.p)[0]

    def test_p1_saddle_is_blocked_under_both_localisation_definitions(self):
        """Li carries ~63 % of the mode; O2 + C3 together carry ~2 %. 30.6x unweighted,
        14.3x mass-weighted -- the verdict does not depend on the definition, so this test
        does not inherit the Omega definition defect that 39.56 had to correct."""
        r = curvature.spectator_test(self.mode, self.p["geometry"], [1, 2])
        self.assertTrue(r["blocked"])
        self.assertTrue(r["definition_independent"])
        for label, expected_ratio in (("unweighted", 30.6), ("mass_weighted", 14.3)):
            rec = r["by_definition"][label]
            self.assertEqual("Li", rec["largest_atom_element"])
            self.assertTrue(rec["largest_is_outside_the_coordinate_set"])
            self.assertAlmostEqual(expected_ratio, rec["ratio"], places=1)

    def test_the_reason_names_an_incomplete_mapping_as_the_first_hypothesis(self):
        """🔴 If this fires on a reaction we believe is real, the mapping is the suspect --
        not the saddle. A gate that misdirects the diagnosis costs more than it saves."""
        r = curvature.spectator_test(self.mode, self.p["geometry"], [1, 2])
        self.assertTrue(any("INCOMPLETE MAPPING" in x for x in r["reasons"]), r["reasons"])

    def test_declaring_the_moving_atom_flips_the_verdict(self):
        """🔴 THE PRECONDITION, as a test. An atom is a spectator only RELATIVE TO a declared
        coordinate set. This is why R-C must declare d(Li-O_break): 39.41(e) measured that its
        ring opening is two-dimensional, so with only the C-O bond declared this test would
        block R-C's GENUINE transition state."""
        r = curvature.spectator_test(self.mode, self.p["geometry"], [1, 2, 10])
        self.assertFalse(r["blocked"])

    def test_an_empty_coordinate_set_never_blocks(self):
        """Every atom would be a spectator -- that is a statement about the mapping, not the
        mode, and blocking on it would be the expensive error."""
        r = curvature.spectator_test(self.mode, self.p["geometry"], [])
        self.assertFalse(r["blocked"])

    def test_a_mismatched_mode_and_geometry_do_not_produce_a_verdict(self):
        r = curvature.spectator_test(self.mode, self.p["geometry"][:-1], [1, 2])
        self.assertFalse(r["blocked"])
        self.assertTrue(any("same structure" in x for x in r["reasons"]))


class TestMechanismCoordinatesAreDeclarable(unittest.TestCase):
    """[39.62] `mechanism` entries put atoms the MECHANISM uses into the coordinate set even
    when no bond between them breaks or forms. Anchored to the break/form selection, so
    `d(Li-O_break)` means the oxygen that actually breaks."""

    def _atoms(self):
        from sei_pilot.criteria import xyzgraph
        path = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
        with open(path, errors="replace") as fh:
            return xyzgraph.read_xyz_frames(fh.read())[0][1]

    def test_the_second_role_reuses_the_break_selection(self):
        from sei_pilot import b0f_deck, roles
        atoms = self._atoms()
        mapping = roles.mapping_for(atoms, [["O_ether", "C_sp3"]], [])
        pairs = b0f_deck.mechanism_pairs(atoms, mapping, [["Li", "O_ether"]])
        self.assertEqual(1, len(pairs))
        o_index = mapping["break"][0]["selected"][0]
        self.assertEqual(o_index, pairs[0]["selected"][1],
                         "the mechanism coordinate must point at the BREAKING oxygen, not "
                         "at some other atom carrying the same role")

    def test_an_unanchorable_role_is_refused_rather_than_guessed(self):
        from sei_pilot import b0f_deck, roles
        atoms = self._atoms()
        mapping = roles.mapping_for(atoms, [["O_ether", "C_sp3"]], [])
        self.assertRaises(b0f_deck.DeckInputError, b0f_deck.mechanism_pairs,
                          atoms, mapping, [["Li", "O_carbonyl"]])

    def test_all_three_reactions_declare_the_li_coordinate(self):
        """🔴 [39.63, MEASURED — overturns the earlier 11-vs-21-atom asymmetry] Li migrates
        onto the BREAKING oxygen in all three: R-A -0.75, R-B -0.85, R-C -0.79 Angstrom.
        The earlier belief that only the 21-atom case needed it came from the HYSTERESIS
        result, which answers a different question: hysteresis asks whether a sequential 1-D
        scan can FOLLOW the motion (yes at 11 atoms), the mechanism list asks whether the
        motion is PART OF THE REACTION (yes everywhere).
        🔒 The uncomfortable consequence, recorded rather than hidden: with Li declared, P1's
        saddle is NOT a spectator by 39.62's definition and that test passes it. The test that
        catches P1 is the BRACKET CHECK (see test_p1_saddle_is_refused_by_the_bracket_check)."""
        from sei_pilot import config
        cfg = config.load("b0_reactions.json", {})
        for r in cfg["reactions"]:
            self.assertEqual([["Li", "O_ether"]], r.get("mechanism"), r["id"])
            self.assertIn("MEASURED", r.get("_mechanism_why", ""), r["id"])

    def test_a_correct_mapping_makes_p1_pass_the_spectator_test(self):
        """🔴 Stated as a test because it is the part that is easy to forget: once Li is
        declared, the spectator test does NOT catch P1. Giving 39.62's test credit for P1
        would leave us believing a saddle like it cannot get through again."""
        p = _parsed()
        mode = g16.imaginary_modes(p)[0]
        self.assertFalse(curvature.spectator_test(mode, p["geometry"], [1, 2, 10])["blocked"])


if __name__ == "__main__":
    unittest.main()
