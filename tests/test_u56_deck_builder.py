"""[U56-2 B-2] sei_pilot/b0f_deck.py — role→index mapping 을 덱 옆에 emit 하는 builder.

§39.39(h)의 단일 실패점 해소를 고정한다: `roles.mapping_for`/`require_mapping` 은
library 수준으로 검증돼 있었지만(tests/test_b0_definitions.py) **emit 하는 호출자가
0곳**이었다. 이 파일은 (i) emit 가 실제로 일어나고, (ii) mapping 미해결이면 **아무
파일도 만들지 않고 raise** 하며, (iii) 스캔 좌표가 mapping 에서(그리고 오직 거기서만)
1-based 로 변환되어 나오고, (iv) 스캔 파라미터가 §39.39(d)의 사전등록 창(8–15) 밖이면
config 값이어도 거부된다는 것을 고정한다.
"""

import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import b0f_deck, roles

PKG = context.PKG_ROOT
REACTANT_XYZ = os.path.join(PKG, "inputs", "li_ec_radical_reactant.xyz")


class _Tmp(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_b0f_")
        self.addCleanup(shutil.rmtree, self.d, True)


class TestMappingIsEmittedBesideTheDeckInputs(_Tmp):
    def test_build_writes_mapping_and_scan_section(self):
        s = b0f_deck.build_deck_inputs("R-A", REACTANT_XYZ, self.d)
        m = json.load(open(s["mapping_path"]))
        self.assertTrue(m["mapping"]["resolved"])
        self.assertEqual("R-A", m["reaction_id"])
        # index 규약이 파일 안에 명시돼 있다 — 0-based mapping / 1-based G16.
        self.assertIn("0-based", m["_index_convention"])
        self.assertTrue(os.path.exists(s["scan_section_path"]))
        self.assertTrue(os.path.exists(
            os.path.join(self.d, "u56_R-A_deck_inputs.json")))

    def test_scan_line_is_one_based_and_matches_the_selected_bond(self):
        s = b0f_deck.build_deck_inputs("R-A", REACTANT_XYZ, self.d)
        m = json.load(open(s["mapping_path"]))
        i, j = m["mapping"]["break"][0]["selected"]
        self.assertEqual(["B %d %d S 12 0.1000" % (i + 1, j + 1)],
                         s["scan_section_lines"])

    def test_covariates_are_emitted_as_data(self):
        """[§39.42(a)/(b)] d(Li–O_break) covariate + 스캔 시작 d('Emit the start') —
        숫자만, 판정 없음 (C-3)."""
        s = b0f_deck.build_deck_inputs("R-A", REACTANT_XYZ, self.d)
        self.assertIsInstance(s["d_li_o_break_ang"], float)
        self.assertGreater(s["d_li_o_break_ang"], 0.5)
        self.assertIsInstance(s["scan_start_d_ang"], float)
        # 시작 d = 끝단 자신의 결합 길이 (합리적 범위 sanity, 1.40 하드코딩 아님)
        self.assertTrue(1.0 < s["scan_start_d_ang"] < 2.5, s["scan_start_d_ang"])
        self.assertIn("covariate", s["_d_li_o_break_note"])

    def test_qst2_variant_emits_mapping_without_a_scan_section(self):
        s = b0f_deck.build_deck_inputs("R-A", REACTANT_XYZ, self.d,
                                       with_scan_section=False)
        self.assertIsNone(s["scan_section_path"])
        self.assertTrue(os.path.exists(s["mapping_path"]))

    def test_ra_and_rb_resolve_to_different_bonds_on_the_same_reactant(self):
        """R-B 가 존재하는 이유 그 자체(§39.26(d)): 같은 반응물, 다른 좌표."""
        sa = b0f_deck.build_deck_inputs("R-A", REACTANT_XYZ, self.d)
        sb = b0f_deck.build_deck_inputs("R-B", REACTANT_XYZ, self.d)
        ma = json.load(open(sa["mapping_path"]))["mapping"]["break"][0]["selected"]
        mb = json.load(open(sb["mapping_path"]))["mapping"]["break"][0]["selected"]
        self.assertNotEqual(sorted(ma), sorted(mb))

    def test_ambiguity_is_carried_not_silenced(self):
        """R-A 의 (O_ether, C_sp3) 는 EC 고리에서 2개가 매칭된다(roles.py 의 명시 사례).
        builder 는 그것을 숨기지 않고 summary 에 실어야 한다."""
        s = b0f_deck.build_deck_inputs("R-A", REACTANT_XYZ, self.d)
        m = json.load(open(s["mapping_path"]))
        amb = [e["ambiguous"] for e in m["mapping"]["break"]]
        self.assertEqual(s["mapping_ambiguous"], any(amb))
        if any(amb):
            self.assertTrue(s["mapping_warnings"])


class TestRefusalWritesNothing(_Tmp):
    def test_unresolved_mapping_raises_and_emits_no_files(self):
        """🔴 계약의 거부 방향: mapping 이 성립하지 않으면 **아무 파일도 없다** —
        부분 산출물이 '만들어진 deck'으로 오독되는 경로를 없앤다."""
        bad = os.path.join(self.d, "h2.xyz")
        with open(bad, "w") as fh:
            fh.write("2\nno such roles\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")
        self.assertRaises(b0f_deck.DeckInputError,
                          b0f_deck.build_deck_inputs, "R-A", bad, self.d)
        self.assertEqual([], [f for f in os.listdir(self.d) if f.startswith("u56_")])

    def test_atom_count_mismatch_is_a_deck_input_error(self):
        bad = os.path.join(self.d, "h2.xyz")
        with open(bad, "w") as fh:
            fh.write("2\nwrong species\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")
        try:
            b0f_deck.build_deck_inputs("R-C", bad, self.d)
        except b0f_deck.DeckInputError as exc:
            self.assertIn("21", str(exc))
        else:
            self.fail("21원자 반응에 2원자 기하가 통과했다")

    def test_role_unresolved_on_the_right_species_raises_mapping_error(self):
        """원자 수는 맞지만 role 쌍이 없는 경우 — require_mapping 의 raise 가
        builder 를 통과해 나온다(같은 진실, 한 곳)."""
        atoms_ok = os.path.join(self.d, "fake11.xyz")
        # 11개의 H — 원자 수는 R-A 와 같지만 O_ether/C_sp3 role 이 없다.
        with open(atoms_ok, "w") as fh:
            fh.write("11\n11 hydrogens, no carbonate roles\n")
            for k in range(11):
                fh.write("H 0.0 0.0 %.1f\n" % (0.8 * k))
        self.assertRaises(roles.MappingRequiredError,
                          b0f_deck.build_deck_inputs, "R-A", atoms_ok, self.d)
        self.assertFalse([f for f in os.listdir(self.d) if f.startswith("u56_")])

    def test_unknown_reaction_id_is_refused(self):
        self.assertRaises(b0f_deck.DeckInputError,
                          b0f_deck.build_deck_inputs, "R-Z", REACTANT_XYZ, self.d)


class TestScanRegistrationIsEnforcedAgainstConfig(_Tmp):
    """§39.42(b)의 개정 사전등록('12 coarse + ≤8 refine, ≤20')은 config 한 줄로
    바꿀 수 없다 — 코드가 강제한다."""

    def _cfg(self, **over):
        import copy
        from sei_pilot import config as cfg_mod
        cfg = copy.deepcopy(cfg_mod.load("b0_reactions.json", {}))
        cfg["u56_2"]["scan"].update(over)
        return cfg

    def test_defaults_match_the_amended_registration(self):
        p = b0f_deck.scan_params()
        self.assertEqual(12, p["coarse_n_steps"])
        self.assertAlmostEqual(0.10, p["coarse_step_ang"])
        self.assertLessEqual(p["refine_n_steps"], b0f_deck.REFINE_STEPS_MAX)
        self.assertTrue(b0f_deck.REFINE_STEP_ANG_RANGE[0]
                        <= p["refine_step_ang"]
                        <= b0f_deck.REFINE_STEP_ANG_RANGE[1])
        self.assertGreater(p["refine_trigger_delta_ev"], 0.0)

    def test_coarse_pass_is_exactly_the_registered_12_x_010(self):
        for over in ({"coarse_n_steps": 11}, {"coarse_n_steps": 15},
                     {"coarse_step_ang": 0.05}, {"coarse_step_ang": None}):
            self.assertRaises(b0f_deck.DeckInputError,
                              b0f_deck.scan_params, self._cfg(**over))

    def test_refine_pass_stays_inside_its_window(self):
        for over in ({"refine_n_steps": 9}, {"refine_n_steps": 0},
                     {"refine_step_ang": 0.05}, {"refine_step_ang": 0.01},
                     {"refine_trigger_delta_ev": 0}):
            self.assertRaises(b0f_deck.DeckInputError,
                              b0f_deck.scan_params, self._cfg(**over))


class TestRefineDecision(unittest.TestCase):
    """§39.42(b)의 **조건부** refine 발동 — (i) 최댓값 인접 |ΔE| > 0.05 eV,
    (ii) 최댓값이 범위 끝. R-A 처럼 깨끗한 격자는 발동하지 않아야 한다(항상 돌면
    트리거의 존재 이유가 사라진다)."""

    def _scan(self, energies):
        pts = [{"point_index": i + 1, "energy_hartree": e, "geometry": [("H", 0, 0, 0)]}
               for i, e in enumerate(energies)]
        with_e = [p for p in pts if p["energy_hartree"] is not None]
        mx = max(with_e, key=lambda p: p["energy_hartree"]) if with_e else None
        return {"points": pts, "max_point_index": mx["point_index"] if mx else None}

    def test_clean_interior_maximum_does_not_trigger(self):
        # 인접 격차 ~0.013 eV (R-A 실측의 형태) < 0.05 → 발동 없음
        e = [-76.50, -76.49, -76.4895, -76.49, -76.50]
        dec = b0f_deck.refine_decision(self._scan(e), 0.05)
        self.assertFalse(dec["triggered"], dec)

    def test_steep_neighbour_gap_triggers(self):
        # 최댓값-인접 |ΔE| = 0.01 Eh ≈ 0.27 eV > 0.05 → 발동 (트리거 i)
        e = [-76.50, -76.49, -76.48, -76.49, -76.50]
        dec = b0f_deck.refine_decision(self._scan(e), 0.05)
        self.assertTrue(dec["triggered"])
        self.assertTrue(any("trigger i" in r for r in dec["reasons"]))

    def test_maximum_at_range_end_triggers(self):
        e = [-76.50, -76.499, -76.498]     # 단조 증가 → 최댓값이 끝점
        dec = b0f_deck.refine_decision(self._scan(e), 0.05)
        self.assertTrue(dec["triggered"])
        self.assertTrue(any("END" in r for r in dec["reasons"]))

    def test_no_maximum_means_no_refine(self):
        dec = b0f_deck.refine_decision({"points": [], "max_point_index": None}, 0.05)
        self.assertFalse(dec["triggered"])


class TestScanParserPlumbing(unittest.TestCase):
    """criteria/g16.py::parse_relaxed_scan — 최고점 선택의 배관.
    ⚠ 형태는 [UNVERIFIED — 실 스캔 로그 미확보] (파서 docstring); 여기서는 mock 형태의
    로그로 배관(점 분리·최고점·에너지 없는 점의 경고)을 고정한다."""

    def _log(self, energies):
        parts = []
        for k, e in enumerate(energies):
            parts.append(" SCF Done:  E(RwB97XD) =  %.9f     A.U. after   5 cycles" % e)
            parts.append(" Standard orientation:")
            parts.append(" " + "-" * 69)
            parts.append(" Center     Atomic      Atomic             Coordinates (Angstroms)")
            parts.append(" Number     Number       Type             X           Y           Z")
            parts.append(" " + "-" * 69)
            parts.append("      1          8           0     0.0    0.0    %.1f" % k)
            parts.append("      2          1           0     0.0    0.0    1.0")
            parts.append(" " + "-" * 69)
            parts.append(" Optimization completed.")
            parts.append("    -- Stationary point found.")
        return "\n".join(parts) + "\n"

    def test_points_and_maximum(self):
        from sei_pilot.criteria import g16
        scan = g16.parse_relaxed_scan(self._log([-76.40, -76.35, -76.38]))
        self.assertEqual(3, scan["n_points"])
        self.assertEqual(2, scan["max_point_index"])
        self.assertAlmostEqual(-76.35, scan["max_energy_hartree"])
        # "Stationary point found" 가 두 번째 트리거로 이중 계수되지 않는다.
        self.assertEqual(3, scan["n_points_with_energy"])
        self.assertEqual([], scan["warnings"])

    def test_point_without_its_own_scf_is_flagged(self):
        from sei_pilot.criteria import g16
        text = self._log([-76.40]) + " Optimization completed.\n"
        scan = g16.parse_relaxed_scan(text)
        self.assertEqual(2, scan["n_points"])
        self.assertEqual(1, scan["n_points_with_energy"])
        self.assertTrue(scan["warnings"])

    def test_empty_log_yields_no_points(self):
        from sei_pilot.criteria import g16
        scan = g16.parse_relaxed_scan("")
        self.assertEqual(0, scan["n_points"])
        self.assertIsNone(scan["max_point_index"])


# =============================================================================================
# §39.47(a) 엔진별 점수 상한 · §39.50(a) G-SCAN-2 v3
# =============================================================================================

class TestScanPointCapBelongsToTheEngine(unittest.TestCase):
    """§39.47(a): 점수 상한은 scan 이 아니라 **엔진**에 속한다. DFT 점 하나 = 4.5–34 core-h,
    GFN2 점 하나 = ~0.001–0.006 — 세 자릿수 차이라 하나의 캡이 둘을 모두 섬길 수 없다.
    🔴 이 테스트가 고정하는 실제 사고: 엔진 구분 없는 20 은 G-SCAN-1 이 요구하는 GFN2
    양방향 스캔(12+12=24)을 **우리 코드가 거부**하게 만든다 — hysteresis 를 실제로 찾아낸
    바로 그 계산(§39.43 의 104점 2-D grid, 41점 refine)을 스펙이 소급 거부하는 형태다."""

    def test_bidirectional_gfn2_scan_is_allowed(self):
        # G-SCAN-1 의 양방향 = 24점. DFT 캡(20)이었다면 거부됐다.
        self.assertEqual(24, b0f_deck.check_scan_point_budget("gfn2", 24))
        self.assertEqual(104, b0f_deck.check_scan_point_budget("gfn2", 104))   # §39.43 2-D grid
        self.assertEqual(512, b0f_deck.engine_point_cap("gfn2"))

    def test_dft_cap_is_unchanged_at_20_one_direction(self):
        self.assertEqual(20, b0f_deck.engine_point_cap("dft"))
        self.assertRaises(b0f_deck.DeckInputError,
                          b0f_deck.check_scan_point_budget, "dft", 24)

    def test_unknown_engine_is_refused_not_defaulted(self):
        self.assertRaises(b0f_deck.DeckInputError, b0f_deck.engine_point_cap, "mopac")

    def test_forgetting_the_engine_fails_towards_the_stricter_cap(self):
        """엔진을 안 넘기면 **더 엄격한** DFT 캡을 받는다 — 잊었을 때 조용히 통과하는
        경로가 없다(실패 방향이 안전한 쪽)."""
        self.assertEqual("dft", b0f_deck.scan_params()["engine"])
        self.assertEqual(20, b0f_deck.scan_params()["point_cap"])
        self.assertEqual(512, b0f_deck.scan_params(engine="gfn2")["point_cap"])


class TestGScan2V3(unittest.TestCase):
    """🔴 **G-SCAN-2 v3 (§39.50(a))** — 정/역 프로파일의 에너지 2종 비교.

    ⚠ 아래 프로파일은 **합성**이다: §39.48(a)가 발표한 두 델타(끝점차·barrier차)를 재현하도록
    구성했을 뿐, 절대 에너지는 실측이 아니다. gate 가 소비하는 것이 정확히 그 두 수다.
    실측 출처: §39.48(a) 표 (GFN2, dev box, 2026-08-20).
    """

    BASE_HARTREE = -41.6837

    def _profile(self, evs, hamiltonian="gfn2"):
        from sei_pilot import units
        return {"hamiltonian": hamiltonian,
                "points": [{"point_index": i + 1,
                            "energy_hartree": self.BASE_HARTREE + units.ev_to_hartree(v)}
                           for i, v in enumerate(evs)]}

    def _pair(self, barrier_f_ev, barrier_r_ev, delta_endpoint_ev, product_ev):
        """🔴 [§39.64] 두 barrier 는 **반응물 쪽 끝**에서 잰다 — 정방향은 첫 프레임,
        역방향은 **마지막** 프레임. 역방향 프로파일은 생성물에서 출발해 반응물로 돌아오므로
        그 마지막 점이 반응물 쪽이다.
        🔒 각 프로파일을 '자기 첫 프레임' 기준으로 재면 역방향 barrier 가 **생성물** 위에
        얹혀서, 두 barrier 의 차이가 `경로 의존성 ± ΔE_반응` 이 된다 — 열역학을 재게 된다.
        그 결함은 실제로 shipped 됐고 R-A 를 6배 문턱으로 오발동시켰다."""
        fwd = [0.0, 0.1, 0.2, 0.3, barrier_f_ev, 0.3, 0.2, 0.1, 0.0,
               -0.1, -0.2, product_ev]
        rmax = delta_endpoint_ev + barrier_r_ev
        rev = [product_ev, product_ev + 0.01, product_ev + 0.02, product_ev + 0.05,
               rmax - 0.20, rmax - 0.05, rmax, rmax - 0.15, rmax - 0.30,
               delta_endpoint_ev + 0.10, delta_endpoint_ev + 0.05, delta_endpoint_ev]
        assert abs(max(rev) - rmax) < 1e-9, "fixture invalid: reverse max must be interior"
        assert abs(max(fwd) - barrier_f_ev) < 1e-9, "fixture invalid: forward max"
        return self._profile(fwd), self._profile(rev)

    # --- §39.48(a) 의 세 실측 케이스 ------------------------------------------------------
    def test_n1_passes_and_the_structural_test_would_have_blocked_it(self):
        """n=1 (R-A, 11원자): 0.000 / 0.013 ⟹ PASS, 문턱의 1/4.
        🔒 v1(구조 동일성)은 이 경로를 **오발동으로 막았다** — 끝점이 0.35 Å 떨어져 있지만
        에너지로는 0.000 eV 다(무른 좌표). 정당한 시도를 차단하는 방향의 오류였다."""
        f, r = self._pair(0.486, 0.473, 0.000, -0.322)
        d = b0f_deck.gscan2_decision(f, r)
        self.assertFalse(d["fired"], d["reasons"])
        self.assertAlmostEqual(0.000, d["delta_endpoint_ev"], places=3)
        self.assertAlmostEqual(0.013, d["delta_barrier_ev"], places=3)

    def test_n2_fires(self):
        """n=2 (R-C, 21원자): 0.482 / 0.536 ⟹ FIRE, 문턱의 ~10배."""
        f, r = self._pair(0.856, 0.320, 0.482, 0.200)
        d = b0f_deck.gscan2_decision(f, r)
        self.assertTrue(d["fired"])
        self.assertAlmostEqual(0.482, d["delta_endpoint_ev"], places=3)
        self.assertAlmostEqual(0.536, d["delta_barrier_ev"], places=3)
        self.assertEqual(2, len(d["reasons"]))     # 두 조건 모두 위반

    def test_n3_fires(self):
        """n=3 (Li(EC)3, 31원자): 0.448 / 0.817 ⟹ FIRE, 문턱의 ~9배."""
        f, r = self._pair(1.255, 0.438, 0.448, 0.200)
        d = b0f_deck.gscan2_decision(f, r)
        self.assertTrue(d["fired"])
        self.assertAlmostEqual(0.448, d["delta_endpoint_ev"], places=3)
        self.assertAlmostEqual(0.817, d["delta_barrier_ev"], places=3)

    # --- AND 조건의 경계: 한 축만 넘어도 FIRE -----------------------------------------------
    def test_and_condition_boundary_each_axis_separately(self):
        tol = b0f_deck.GSCAN2_TOLERANCE_EV
        self.assertAlmostEqual(0.05, tol)
        cases = [(0.049, 0.049, False), (0.051, 0.000, True), (0.000, 0.051, True)]
        for d_end, d_bar, want_fire in cases:
            f, r = self._pair(0.486, 0.486 - d_bar, d_end, -0.322)
            d = b0f_deck.gscan2_decision(f, r)
            self.assertEqual(want_fire, d["fired"],
                             "endpoint %.3f barrier %.3f -> %r" % (d_end, d_bar, d))

    # --- §39.50(b): Hamiltonian 을 가로지르는 뺄셈은 판정 자체를 거부한다 --------------------
    def test_cross_hamiltonian_subtraction_is_refused_not_judged(self):
        """🔴 GFN2 와 DFT 의 Hartree 를 빼면 **숫자는 나오는데** 물리적으로 무의미하고,
        모든 로그는 성공이라고 찍는다. 판정하지 않고 거부한다."""
        f, r = self._pair(0.486, 0.473, 0.000, -0.322)
        r_dft = dict(r, hamiltonian="dft")
        self.assertRaises(b0f_deck.DeckInputError, b0f_deck.gscan2_decision, f, r_dft)
        no_key = dict((k, v) for k, v in r.items() if k != "hamiltonian")
        self.assertRaises(b0f_deck.DeckInputError, b0f_deck.gscan2_decision, f, no_key)
        for missing in ({"hamiltonian": None}, {"hamiltonian": ""}):
            self.assertRaises(b0f_deck.DeckInputError,
                              b0f_deck.gscan2_decision, f, dict(r, **missing))

    def test_unjudgeable_profile_fires_rather_than_passing_silently(self):
        f, r = self._pair(0.486, 0.473, 0.000, -0.322)
        short = self._profile([0.0, 0.1, 0.2])                  # 8점 미만 = 죽은 scan
        self.assertTrue(b0f_deck.gscan2_decision(f, short)["fired"])
        holed = dict(r)
        holed["points"] = [dict(p) for p in r["points"]]
        holed["points"][3]["energy_hartree"] = None             # 에너지 결측
        self.assertTrue(b0f_deck.gscan2_decision(f, holed)["fired"])

    def test_both_barriers_are_measured_from_the_reactant_end(self):
        """🔴 [§39.64] 정방향은 첫 프레임, 역방향은 **마지막** 프레임 — 둘 다 반응물 쪽이다.
        각 프로파일의 '자기 첫 프레임' 을 쓰면 역방향 barrier 가 생성물 위에 얹혀서 두
        barrier 의 차이에 ΔE_반응 이 섞인다."""
        f, r = self._pair(0.856, 0.320, 0.482, -0.322)
        d = b0f_deck.gscan2_decision(f, r)
        self.assertAlmostEqual(0.856, d["barrier_forward_ev"], places=3)
        self.assertAlmostEqual(0.320, d["barrier_reverse_ev"], places=3)

    def test_the_two_clauses_reference_the_same_two_frames(self):
        """🟢 [§39.64] 공짜 정합성 검사, **화학 지식이 전혀 필요 없다**: clause (i) 은
        역방향 마지막 프레임과 정방향 첫 프레임을 비교한다. 두 barrier 도 이제 **같은 두
        프레임**을 기준으로 한다. 서로 다른 프레임을 참조하는 구현은 정의상 결함이다."""
        f, r = self._pair(0.486, 0.473, 0.000, -0.322)
        d = b0f_deck.gscan2_decision(f, r)
        self.assertEqual(0, d["reference_frames"]["forward"])
        self.assertEqual(-1, d["reference_frames"]["reverse"])
        # clause (i) 이 실제로 그 두 프레임을 썼는지 직접 대조한다
        ef = [p["energy_hartree"] for p in f["points"]]
        er = [p["energy_hartree"] for p in r["points"]]
        from sei_pilot import units
        self.assertAlmostEqual(abs(units.hartree_to_ev(er[-1] - ef[0])),
                               d["delta_endpoint_ev"], places=9)

    def test_an_unknown_direction_has_no_safe_default(self):
        self.assertRaises(b0f_deck.DeckInputError,
                          b0f_deck.scan_barrier_ev, self._profile([0.0, 0.1]), "sideways")

    def test_the_measured_r_a_pair_passes_end_to_end(self):
        """🔴 실측 회귀: dev box 에서 xtb 6.7.1 로 실제 돌린 R-A 양방향 scan(각 12점).
        옛 기준(각자 첫 프레임)으로는 |Δbarrier| = 0.313 eV 로 **오발동**했다 —
        깨끗한 경로를 막는 방향, 즉 비싼 쪽 오류다. §39.64 기준에서는 통과한다."""
        import os
        from sei_pilot import gfn2_scan
        fx = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
        fwd = gfn2_scan.read_log(os.path.join(fx, "xtb_relaxed_scan_r_a.log"))
        rev = gfn2_scan.read_log(os.path.join(fx, "xtb_relaxed_scan_r_a_reverse.log"))
        d = b0f_deck.gscan2_decision(fwd, rev)
        self.assertFalse(d["fired"], d["reasons"])
        self.assertLess(d["delta_endpoint_ev"], 0.001)
        self.assertAlmostEqual(0.0216, d["delta_barrier_ev"], places=3)


if __name__ == "__main__":
    unittest.main()
