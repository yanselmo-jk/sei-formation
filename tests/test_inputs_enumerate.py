"""동봉 입력 구조의 무결성 + gen-1 열거기 테스트.

동봉 구조가 깨져 있으면 사용자의 클러스터에서 1,000 core-h가 쓰레기를 만든다.
우리가 QC 계산으로 검증할 수는 없지만, **그래프와 기하의 온전성**은 검증할 수 있다.
"""

import json
import math
import os
import unittest

import context  # noqa: F401
from sei_pilot import enumerate_gen1 as eg
from sei_pilot.criteria import xyzgraph as xg

INPUTS = os.path.join(context.PKG_ROOT, "inputs")
PKG = context.PKG_ROOT


def load(name):
    with open(os.path.join(INPUTS, name)) as fh:
        return xg.read_xyz_frames(fh.read())[0][1]


class TestShippedStructures(unittest.TestCase):
    def test_reactant_is_intact_ec_ring_with_li(self):
        atoms = load("li_ec_radical_reactant.xyz")
        self.assertEqual(len(atoms), 11)
        self.assertEqual(sorted(a[0] for a in atoms),
                         sorted(["C"] * 3 + ["O"] * 3 + ["H"] * 4 + ["Li"]))
        bonds = xg.bond_list(atoms)
        comps = xg.connected_components(len(atoms), bonds)
        self.assertEqual(sorted(xg.formula(atoms, c) for c in comps),
                         ["C3H4O3", "Li"])
        # 고리: 유기부의 결합 수가 원자 수와 같아야 고리가 하나 있다 (C3O3 고리 + C=O + 4 C-H)
        organic = [c for c in comps if len(c) > 1][0]
        n_in_ring_component = len(organic)
        n_bonds = len([b for b in bonds])
        self.assertEqual(n_bonds, n_in_ring_component)   # 고리 1개 = 결합수 == 원자수

    def test_product_is_ring_opened(self):
        atoms = load("li_ec_radical_product.xyz")
        bonds = xg.bond_list(atoms)
        comps = xg.connected_components(len(atoms), bonds)
        organic = [c for c in comps if len(c) > 1][0]
        self.assertEqual(len(bonds), len(organic) - 1)   # 고리 없음 = 나무 구조

    def test_no_atom_overlap(self):
        for name in ("li_ec_radical_reactant.xyz", "li_ec_radical_product.xyz"):
            atoms = load(name)
            dmin = min(xg.distance_ang(atoms[i], atoms[j])
                       for i in range(len(atoms)) for j in range(i + 1, len(atoms)))
            self.assertGreater(dmin, 0.9, name)          # 결합거리보다 짧으면 오류

    def test_li_coordinates_carbonyl_oxygen(self):
        atoms = load("li_ec_radical_reactant.xyz")
        li = [a for a in atoms if a[0] == "Li"][0]
        d = min(xg.distance_ang(li, a) for a in atoms if a[0] == "O")
        self.assertGreater(d, 1.5)
        self.assertLess(d, 2.5)          # Li+-O 배위 거리 범위


# 🔴 P2f(CP2K FIST 스모크) 제거와 함께 SPC/E 물상자·FIST 템플릿 테스트를 지웠다.
#    proposer §30 이 λ_out 을 고전 MD 대신 G16 비평형 PCM 으로 얻는 경로를 찾아
#    P2f 의 소비자가 사라졌다. 되살릴 때 필요한 것은 HANDOFF §17.

class TestEnumerator(unittest.TestCase):
    def setUp(self):
        self.atoms = load("li_ec_radical_reactant.xyz")

    def test_enumeration_is_deterministic(self):
        r1 = eg.enumerate_for_reactant(self.atoms)
        r2 = eg.enumerate_for_reactant(self.atoms)
        self.assertEqual(r1["n_candidates"], r2["n_candidates"])
        self.assertGreater(r1["n_candidates"], 50)     # P3 판정에 쓸 만큼은 나온다

    def test_valence_respected(self):
        r = eg.enumerate_for_reactant(self.atoms)
        bonds = xg.bond_list(self.atoms)
        for c in r["candidates"][:200]:
            new = [b for b in bonds if list(b) not in c["break"]] + \
                  [tuple(f) for f in c["form"]]
            deg = {}
            for i, j in new:
                deg[i] = deg.get(i, 0) + 1
                deg[j] = deg.get(j, 0) + 1
            for idx, d in deg.items():
                self.assertLessEqual(d, eg.MAX_VALENCE.get(self.atoms[idx][0], 4))

    def test_unique_products_fewer_than_candidates(self):
        r = eg.enumerate_for_reactant(self.atoms)
        self.assertLess(r["n_unique_products"], r["n_candidates"])

    def test_candidate_geometry_actually_breaks_the_bond(self):
        cand = {"break": [[1, 2]], "form": []}
        geom = eg.build_candidate_geometry(self.atoms, cand)
        self.assertGreater(xg.distance_ang(geom[1], geom[2]),
                           xg.distance_ang(self.atoms[1], self.atoms[2]))
        self.assertNotIn((1, 2), xg.bond_list(geom))

    def test_candidate_geometry_forms_the_bond(self):
        cand = {"break": [], "form": [[6, 9]]}       # 서로 먼 두 H를 붙인다
        geom = eg.build_candidate_geometry(self.atoms, cand)
        self.assertAlmostEqual(xg.distance_ang(geom[6], geom[9]), 1.55, places=2)

    def test_sampling_is_spread_not_prefix(self):
        cands = list(range(1000))
        picked = eg.sample_candidates(cands, 10)
        self.assertEqual(len(picked), 10)
        self.assertGreater(max(picked), 800)         # 앞쪽만 뽑지 않는다

    def test_unsupported_mode_raises(self):
        self.assertRaises(ValueError, eg.enumerate_for_reactant,
                          self.atoms, mode="libe_pool_recombine")

    def test_to_xyz_roundtrip(self):
        text = eg.to_xyz(self.atoms, "test")
        back = xg.read_xyz_frames(text)[0][1]
        self.assertEqual(len(back), len(self.atoms))
        self.assertAlmostEqual(back[0][1], self.atoms[0][1], places=5)


if __name__ == "__main__":
    unittest.main()
