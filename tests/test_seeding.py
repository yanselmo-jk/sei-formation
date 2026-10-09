"""P5 독립 시드 2회 모드 — σ_protocol 측정의 재현성.

lead 요구: "같은 종을 독립 시드로 2회 계산 … 회신 JSON에 어느 시드로 돌렸는지 기록하라."

🔴 여기서 고정하는 핵심: **시드가 같으면 기하가 같고, 다르면 다르다.**
   시드가 결과에 실제로 영향을 주지 않으면(예: 섭동이 0) σ_protocol 은 0이 나오고
   우리는 "프로토콜이 완벽히 안정적"이라는 **거짓 결론**을 회신하게 된다.
"""

import json
import os
import unittest

import context  # noqa: F401
from sei_pilot import plan, seeding

SPEC_DIR = os.path.join(context.PKG_ROOT, "inputs", "p5_species")


def _manifest():
    with open(os.path.join(SPEC_DIR, "manifest.json")) as fh:
        return json.load(fh)


def _atoms(species_id):
    spec = [s for s in _manifest()["species"] if s["id"] == species_id][0]
    with open(os.path.join(SPEC_DIR, spec["file"])) as fh:
        return seeding.read_xyz(fh.read())


class TestPerturbDeterminism(unittest.TestCase):
    def setUp(self):
        self.atoms = _atoms("ec")

    def test_same_seed_gives_identical_geometry(self):
        self.assertEqual(seeding.perturb(self.atoms, 1),
                         seeding.perturb(self.atoms, 1),
                         "같은 시드가 다른 기하를 주면 재현이 불가능하다")

    def test_different_seeds_give_different_geometry(self):
        self.assertNotEqual(seeding.perturb(self.atoms, 1),
                            seeding.perturb(self.atoms, 2))

    def test_seed_zero_is_the_unperturbed_original(self):
        """시드 0 은 원본이어야 한다 — 한 쪽 표본은 항상 우리가 준 기하다."""
        self.assertEqual([tuple(a) for a in self.atoms],
                         seeding.perturb(self.atoms, seeding.UNPERTURBED_SEED))

    def test_perturbation_actually_moves_atoms(self):
        """🔴 섭동이 0이면 σ_protocol 이 거짓으로 0이 된다."""
        moved = seeding.max_displacement_ang(
            self.atoms, seeding.perturb(self.atoms, 1))
        self.assertGreater(moved, 0.01, "원자가 사실상 움직이지 않았다")

    def test_perturbation_respects_amplitude(self):
        amp = seeding.DEFAULT_AMPLITUDE_ANG
        self.assertLessEqual(
            seeding.max_displacement_ang(self.atoms, seeding.perturb(self.atoms, 7)),
            amp + 1e-9, "진폭 상한을 넘었다")

    def test_element_symbols_are_preserved(self):
        self.assertEqual([a[0] for a in self.atoms],
                         [a[0] for a in seeding.perturb(self.atoms, 3)])

    def test_atom_count_is_preserved(self):
        self.assertEqual(len(self.atoms), len(seeding.perturb(self.atoms, 3)))


class TestPerturbationIsChemicallySane(unittest.TestCase):
    """섭동이 원자를 겹쳐 놓으면 SCF가 폭발하고, 그건 σ 가 아니라 쓰레기다."""

    def test_no_species_gets_atoms_too_close(self):
        offenders = []
        for spec in _manifest()["species"]:
            atoms = _atoms(spec["id"])
            for seed in (1, 2, 3):
                d = seeding.min_interatomic_distance_ang(
                    seeding.perturb(atoms, seed))
                if d < 0.7:
                    offenders.append((spec["id"], seed, round(d, 3)))
        self.assertEqual([], offenders,
                         "섭동 후 원자간 거리가 0.7 Å 미만 — 진폭이 과하다")


class TestSeedProvenance(unittest.TestCase):
    def setUp(self):
        self.atoms = _atoms("ec")

    def test_provenance_records_the_seed(self):
        p = seeding.provenance(1, seeding.DEFAULT_AMPLITUDE_ANG,
                               self.atoms, seeding.perturb(self.atoms, 1))
        self.assertEqual(1, p["seed"])
        self.assertTrue(p["perturbed"])
        self.assertEqual(seeding.DEFAULT_AMPLITUDE_ANG, p["amplitude_ang"])

    def test_unperturbed_provenance_reports_zero_amplitude(self):
        p = seeding.provenance(0, seeding.DEFAULT_AMPLITUDE_ANG,
                               self.atoms, self.atoms)
        self.assertFalse(p["perturbed"])
        self.assertEqual(0.0, p["amplitude_ang"])
        self.assertEqual(0.0, p["max_displacement_ang"])

    def test_provenance_carries_the_interpretation_caveat(self):
        """진폭 의존성을 밝히지 않은 σ 는 잘못 읽힌다."""
        p = seeding.provenance(1, 0.1, self.atoms, seeding.perturb(self.atoms, 1))
        self.assertIn("과소평가", p["caveat"])
        self.assertIn("과대평가", p["caveat"])

    def test_amplitude_has_a_single_source(self):
        self.assertIsInstance(seeding.DEFAULT_AMPLITUDE_ANG, float)
        self.assertGreater(seeding.DEFAULT_AMPLITUDE_ANG, 0.0)


class TestXyzRoundTrip(unittest.TestCase):
    def test_write_then_read_recovers_geometry(self):
        atoms = _atoms("h2o")
        back = seeding.read_xyz(seeding.write_xyz(atoms, "test"))
        self.assertEqual(len(atoms), len(back))
        for a, b in zip(atoms, back):
            self.assertEqual(a[0], b[0])
            for i in (1, 2, 3):
                self.assertAlmostEqual(a[i], b[i], places=6)

    def test_comment_newlines_do_not_corrupt_the_file(self):
        text = seeding.write_xyz(_atoms("h2o"), "a\nb")
        self.assertEqual(3 + 2, len(text.splitlines()))


class TestManifestDualSeedSelection(unittest.TestCase):
    def test_three_or_four_species_are_marked(self):
        """lead 지시: 대표 종 중 3~4개."""
        n = sum(1 for s in _manifest()["species"] if s.get("dual_seed"))
        self.assertIn(n, (3, 4), "dual_seed 종이 %d개 — 지시는 3~4개다" % n)

    def test_every_dual_seed_species_records_why(self):
        for s in _manifest()["species"]:
            if s.get("dual_seed"):
                self.assertTrue(s.get("dual_seed_reason"),
                                "%s 가 왜 뽑혔는지 기록이 없다" % s["id"])

    def test_selection_spans_charge_and_spin(self):
        """한 구석만 보면 σ 를 일반화할 수 없다."""
        picked = [s for s in _manifest()["species"] if s.get("dual_seed")]
        self.assertGreaterEqual(len(set(s["charge"] for s in picked)), 2,
                                "전하가 한 종류뿐이다")
        self.assertGreaterEqual(len(set(s["open_shell"] for s in picked)), 2,
                                "닫힌껍질/개각 중 한쪽만 있다")

    def test_selection_spans_size(self):
        sizes = [s["n_atoms"] for s in _manifest()["species"] if s.get("dual_seed")]
        self.assertGreaterEqual(max(sizes) - min(sizes), 8,
                                "크기 범위가 좁다 — 곡선의 한 점만 보게 된다")


class TestBudgetStillHolds(unittest.TestCase):
    """🔴 dual-seed 로 실행이 늘었다. 가드는 타협 불가다."""

    def test_p5_description_is_derived_not_hardcoded(self):
        p5 = [i for i in plan.default_items("cpu") if i.key == "P5"][0]
        n = len(_manifest()["species"])
        self.assertIn("%d종" % n, p5.title,
                      "P5 설명의 종 수가 manifest 와 어긋난다(문자열 하드코딩?)")
        self.assertIn("dual-seed", p5.title)

    def test_p5_run_count_in_description_matches_manifest(self):
        species = _manifest()["species"]
        runs = (sum(2 if s.get("dual_seed") else 1 for s in species)
                + sum(1 for s in species if s.get("cheap_level_too")))
        p5 = [i for i in plan.default_items("cpu") if i.key == "P5"][0]
        self.assertIn("%d실행" % runs, p5.title)


if __name__ == "__main__":
    unittest.main()
