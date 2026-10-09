"""파일럿 자동 판정 로직 테스트.

**여기가 이 패키지에서 가장 중요한 테스트다.** 사용자는 판단하지 않는다 —
판정이 틀리면 우리는 잘못된 숫자를 받고도 그것을 모른다.
"""

import os
import unittest

import context  # noqa: F401
from sei_pilot import probes
from sei_pilot import config as config_mod
from sei_pilot.criteria import (cost, endpoints, p1, p1b, p3, p4,
                                xyzgraph)

INPUTS = os.path.join(context.PKG_ROOT, "inputs")

ORCA_FREQ_GOOD = """
-----------------------
VIBRATIONAL FREQUENCIES
-----------------------

   0:         0.00 cm**-1
   1:         0.00 cm**-1
   2:         0.00 cm**-1
   3:         0.00 cm**-1
   4:         0.00 cm**-1
   5:         0.00 cm**-1
   6:      -452.31 cm**-1  ***imaginary mode***
   7:       112.44 cm**-1
   8:       331.02 cm**-1

------------
NORMAL MODES
------------
"""

ORCA_FREQ_TWO_IMAG = ORCA_FREQ_GOOD.replace("   7:       112.44", "   7:      -230.10")
ORCA_FREQ_TINY_IMAG = ORCA_FREQ_GOOD.replace("-452.31", "-38.20")


def _xyz(path):
    with open(os.path.join(INPUTS, path)) as fh:
        return fh.read()


class TestP1Frequencies(unittest.TestCase):
    def test_parse_orca(self):
        f = p1.parse_orca_frequencies(ORCA_FREQ_GOOD)
        self.assertEqual(len(f), 9)
        self.assertIn(-452.31, f)

    def test_exactly_one_imaginary_in_window_passes(self):
        r = p1.evaluate_freq(p1.parse_orca_frequencies(ORCA_FREQ_GOOD))
        self.assertTrue(r["passed"])
        self.assertEqual(r["imag_freq_count"], 1)
        self.assertAlmostEqual(r["imag_freq_cm"], -452.3, places=1)

    def test_two_imaginary_fails(self):
        r = p1.evaluate_freq(p1.parse_orca_frequencies(ORCA_FREQ_TWO_IMAG))
        self.assertFalse(r["passed"])
        self.assertEqual(r["imag_freq_count"], 2)
        self.assertIn("multiple_imaginary_modes(2개)", r["reasons"])

    def test_imaginary_outside_window_fails(self):
        """-38 cm^-1 은 진짜 TS 모드가 아니라 수치 잡음/저주파 회전이다."""
        r = p1.evaluate_freq(p1.parse_orca_frequencies(ORCA_FREQ_TINY_IMAG))
        self.assertFalse(r["passed"])
        self.assertTrue(any("out_of_window" in x for x in r["reasons"]))

    def test_no_imaginary_is_a_minimum_not_a_ts(self):
        r = p1.evaluate_freq([100.0, 200.0])
        self.assertFalse(r["passed"])
        self.assertTrue(any("no_imaginary_mode" in x for x in r["reasons"]))

    def test_empty_output(self):
        r = p1.evaluate_freq([])
        self.assertFalse(r["passed"])
        self.assertIn("no_frequencies_parsed", r["reasons"])

    def test_generic_i_suffix_parser(self):
        f, kind = p1.parse_frequencies("mode 1: 450.2i cm-1")
        self.assertEqual(kind, "generic")
        self.assertEqual(f, [-450.2])

    def test_convergence_steps(self):
        text = "GEOMETRY OPTIMIZATION CYCLE   1\nGEOMETRY OPTIMIZATION CYCLE   17\n"
        self.assertEqual(p1.parse_convergence_steps(text), 17)


class TestP1IRC(unittest.TestCase):
    def test_distinct_endpoints_pass(self):
        """폐환 라디칼 ↔ 개환 라디칼은 서로 다른 극소여야 한다."""
        r = p1.evaluate_irc(_xyz("li_ec_radical_reactant.xyz"),
                            _xyz("li_ec_radical_product.xyz"))
        self.assertTrue(r["irc_endpoints_distinct"])
        self.assertTrue(r["passed"])
        self.assertTrue(r["bond_changes"])

    def test_identical_endpoints_fail(self):
        same = _xyz("li_ec_radical_reactant.xyz")
        r = p1.evaluate_irc(same, same)
        self.assertFalse(r["passed"])
        self.assertTrue(any("identical" in x for x in r["reasons"]))

    def test_missing_trajectory(self):
        r = p1.evaluate_irc("", None)
        self.assertFalse(r["passed"])
        self.assertIn("irc_trajectory_missing_or_unparsable", r["reasons"])

    # ---- 02_METHOD_SPEC §12.3: 2층 그래프 + 속도론적 병합 ----

    def _xyz_text(self, atoms, comment="test"):
        return "%d\n%s\n" % (len(atoms), comment) + "\n".join(
            "%-3s %12.6f %12.6f %12.6f" % a for a in atoms) + "\n"

    def _move_li(self, dy):
        atoms = xyzgraph.read_xyz_frames(_xyz("li_ec_radical_reactant.xyz"))[0][1]
        return [(s, x, y + dy, z) if s == "Li" else (s, x, y, z)
                for s, x, y, z in atoms]

    def _li_at(self, pos):
        """Li만 지정 위치로 옮긴다. 공유결합 층은 그대로이므로 R2/R3 시험용."""
        atoms = xyzgraph.read_xyz_frames(_xyz("li_ec_radical_reactant.xyz"))[0][1]
        return [((s,) + tuple(pos)) if s == "Li" else (s, x, y, z)
                for s, x, y, z in atoms]

    # Li 가 카보닐 O(원래 자리) ↔ 고리 에스터 O 로 호핑한 쌍.
    # 공유결합 층 동일 + 실체 수 동일(둘 다 1) + Layer I 만 다름 = 정확히 R2b.
    LI_HOP_POS = (-3.03, 0.986, 0.0)

    def test_R1_covalent_change_is_distinct(self):
        r = p1.evaluate_irc(_xyz("li_ec_radical_reactant.xyz"),
                            _xyz("li_ec_radical_product.xyz"))
        ec = r["endpoint_comparison"]
        self.assertEqual(ec["merge_rule_applied"], "R1")
        self.assertEqual(r["verdict"], "distinct")
        self.assertTrue(r["passed"])
        self.assertTrue(ec["endpoint_distinct_C_only"])

    def test_R2a_ion_pair_formation_is_distinct(self):
        """🔴 §12.1의 핵심: `ROCO2- + Li+` → `ROCO2Li` 를 기각하면 안 된다.

        공유결합 층은 동일하고 Li 배위만 생기지만 **실체 수가 2 → 1** 로 변한다.
        옛 규약(공유결합만)이었다면 '같은 극소'로 기각됐을 반응이다.
        """
        far = self._move_li(4.5)      # Li 를 떼어 놓는다 (접촉 없음 → 실체 2개)
        near = self._move_li(0.0)     # 원래 위치 (Li-O 배위 → 실체 1개)
        r = p1.evaluate_irc(self._xyz_text(far), self._xyz_text(near))
        ec = r["endpoint_comparison"]
        self.assertFalse(ec["endpoint_distinct_C_only"])     # 옛 규약이면 기각됐다
        self.assertTrue(ec["entity_count_change"])
        self.assertEqual(ec["entity_count_forward"], 2)
        self.assertEqual(ec["entity_count_reverse"], 1)
        self.assertEqual(ec["merge_rule_applied"], "R2a")
        self.assertEqual(r["verdict"], "distinct")
        self.assertTrue(r["passed"])

    def test_R2b_without_barrier_is_undetermined_not_rejected(self):
        """🔴 §12.5: barrier를 모르면 병합도 분리도 하지 않는다. 조용한 기각 금지."""
        a = self._move_li(0.0)
        b = self._li_at(self.LI_HOP_POS)   # 응집체 내 Li 호핑 (실체 수 불변)
        r = p1.evaluate_irc(self._xyz_text(a), self._xyz_text(b))
        ec = r["endpoint_comparison"]
        self.assertEqual(ec["merge_rule_applied"], "R2b-unknown_barrier")
        self.assertEqual(r["verdict"], "undetermined")
        self.assertFalse(r["passed"])
        self.assertTrue(r["human_review_required"])
        self.assertFalse(ec["entity_count_change"])
        self.assertFalse(ec["endpoint_distinct_C_only"])
        self.assertTrue(ec["endpoint_distinct_with_Li"])
        # 판정 불가는 '기각'이 아니다 — P1 전체 상태도 fail이 아니어야 한다
        p1res = p1.evaluate_p1(ORCA_FREQ_GOOD, self._xyz_text(a), self._xyz_text(b),
                               wall_h=5.0, breakdown_core_h={"freq": 1.0})
        self.assertEqual(p1res["status"], "undetermined")
        self.assertTrue(p1res["human_review_required"])

    def test_kinetic_merge_below_tau_is_same_node(self):
        a = self._move_li(0.0)
        b = self._li_at(self.LI_HOP_POS)
        ec = endpoints.classify_endpoints(a, b, barrier_fwd_eV=0.04,
                                          barrier_rev_eV=0.03)
        self.assertEqual(ec["merge_rule_applied"], "R2b-merged")
        self.assertEqual(ec["verdict"], "same")
        self.assertAlmostEqual(ec["tau_eV"], 0.1)

    def test_kinetic_merge_above_tau_is_distinct(self):
        a = self._move_li(0.0)
        b = self._li_at(self.LI_HOP_POS)
        ec = endpoints.classify_endpoints(a, b, barrier_fwd_eV=0.35,
                                          barrier_rev_eV=0.02)
        self.assertEqual(ec["merge_rule_applied"], "R2b-distinct")
        self.assertEqual(ec["verdict"], "distinct")

    def test_R3_identical_is_same(self):
        same = _xyz("li_ec_radical_reactant.xyz")
        r = p1.evaluate_irc(same, same)
        self.assertEqual(r["endpoint_comparison"]["merge_rule_applied"], "R3")
        self.assertEqual(r["verdict"], "same")
        self.assertFalse(r["passed"])

    def test_all_evidence_is_recorded_for_reinterpretation(self):
        """§12.4-2: 판정 근거를 남겨 규칙이 바뀌어도 재계산 없이 재판정한다."""
        r = p1.evaluate_irc(_xyz("li_ec_radical_reactant.xyz"),
                            _xyz("li_ec_radical_product.xyz"))
        ec = r["endpoint_comparison"]
        for k in ("endpoint_distinct_C_only", "endpoint_distinct_with_Li",
                  "entity_count_change", "entity_count_forward",
                  "entity_count_reverse", "barrier_fwd_eV", "barrier_rev_eV",
                  "merge_rule_applied", "hash_c_forward", "hash_ci_forward",
                  "layer_I_cutoffs_ang", "threshold_sensitivity", "rule_source"):
            self.assertIn(k, ec)
        self.assertIn("§12.3", ec["rule_source"])

    def test_threshold_sensitivity_is_reported(self):
        """§12.4-3: Li 접촉 임계 ±0.2 Å 에서 판정이 뒤집히는지 반드시 보고한다."""
        a = self._move_li(0.0)
        b = self._move_li(4.5)
        ec = endpoints.classify_endpoints(a, b)
        ts = ec["threshold_sensitivity"]
        self.assertAlmostEqual(ts["delta_ang"], 0.2)
        self.assertEqual(len(ts["variants"]), 2)
        self.assertIn("threshold_sensitive", ts)

    def test_cutoffs_come_from_config_file_not_code(self):
        """ADR-001: 화학 파라미터는 코드가 아니라 데이터다."""
        cfg = config_mod.graph_layers()
        self.assertFalse(cfg.get("_fallback"), "설정 파일을 못 읽었다")
        self.assertIn("graph_layers.json", cfg["_source"])
        self.assertIn("Li-O", cfg["layer_I"]["contact_cutoff_ang"])
        self.assertIn("PLACEHOLDER", cfg["layer_I"]["_provenance"])   # 실측 전임을 명시
        self.assertAlmostEqual(cfg["kinetic_merge"]["tau_eV"], 0.1)

    def test_custom_config_changes_the_verdict(self):
        """설정을 바꾸면 판정이 바뀐다 = 진짜로 데이터로 분리돼 있다."""
        a = self._move_li(0.0)
        b = self._move_li(4.5)
        tight = {"layer_C": {"elements": ["C", "H", "O", "F", "P"],
                             "bond_tolerance": 1.25},
                 "layer_I": {"cations": ["Li"],
                             "contact_cutoff_ang": {"default": 0.5},
                             "sensitivity_delta_ang": 0.0},
                 "kinetic_merge": {"tau_eV": 0.1}}
        ec = endpoints.classify_endpoints(a, b, cfg=tight)
        # 임계가 0.5 Å면 Li는 어느 쪽에서도 접촉이 없다 → 실체 수 불변 → R3
        self.assertEqual(ec["merge_rule_applied"], "R3")
        self.assertEqual(ec["verdict"], "same")

    def test_uses_last_frame_of_each_direction(self):
        multi = _xyz("li_ec_radical_reactant.xyz") + _xyz("li_ec_radical_product.xyz")
        r = p1.evaluate_irc(multi, _xyz("li_ec_radical_reactant.xyz"))
        self.assertEqual(r["n_frames_forward"], 2)
        self.assertTrue(r["irc_endpoints_distinct"])   # 마지막 프레임=개환


#: A synthetic pair of IRC directions that satisfy C-2 (ADR-090/092): both
#: terminated normally, both have >= guards.IRC_MIN_POINTS points, and both
#: descend by more than guards.IRC_MIN_DESCENT_EV from a shared TS energy.
_C2_TS_HARTREE = -350.000000
#: 🔴 [C-2.1/C-2.2, §39.53] A clean IRC must now say HOW it ended. `minimum_found` is what
#: makes these fixtures a PASS; the real P1 run printed `maxpoints` instead and would not
#: pass -- which is the whole point of the clause and the honest price of adding it.
_C2_CLEAN_COMPLETION = {"normal_termination": True, "maxpoints_reached": False,
                        "minimum_found": True, "path_calculation_complete": True,
                        "termination_reason": "minimum_found", "truncated": False}
_C2_FORWARD_G16 = {"normal_termination": True,
                   "irc_completion": _C2_CLEAN_COMPLETION,
                   "scf": {"final_energy_hartree": -350.010000}}   # ~0.27 eV descent
_C2_REVERSE_G16 = {"normal_termination": True,
                   "irc_completion": _C2_CLEAN_COMPLETION,
                   "scf": {"final_energy_hartree": -350.020000}}   # ~0.54 eV descent


class TestP1Overall(unittest.TestCase):
    def test_pass(self):
        """🔴 ADR-090/092: an overall `pass` now ALSO requires C-2 (the IRC actually
        establishing a path), not just topology + frequency + wall. Supplying
        realistic per-direction G16 termination/energy data is what makes this a
        `pass` rather than `undetermined` -- omitting it is exactly the gap this
        review closed, and the test with it (below) pins the closed gap."""
        r = p1.evaluate_p1(ORCA_FREQ_GOOD,
                           _xyz("li_ec_radical_reactant.xyz"),
                           _xyz("li_ec_radical_product.xyz"),
                           wall_h=5.0,
                           breakdown_core_h={"crest": 10, "ts_guess": 300,
                                             "ts_opt": 400, "irc": 200, "freq": 90},
                           irc_forward_g16=_C2_FORWARD_G16,
                           irc_reverse_g16=_C2_REVERSE_G16,
                           irc_forward_n_points=30, irc_reverse_n_points=30,
                           irc_e_ts_hartree=_C2_TS_HARTREE)
        self.assertEqual(r["status"], "pass")
        self.assertAlmostEqual(r["core_hours_total"], 1000.0)
        self.assertEqual(r["criteria"]["imag_freq_count"], 1)
        self.assertTrue(r["criteria"]["irc_c2_may_render_chemical_verdict"])

    def test_c2_unmet_downgrades_a_topologically_distinct_pass_to_undetermined(self):
        """🔴 THE critic8-constructed adversarial case (ADR-092): a short IRC (below
        `guards.IRC_MIN_POINTS`) whose endpoints merely LOOK topologically distinct
        must not earn a chemical `pass` -- and, just as important, it must not
        earn a `fail` either. 'The TS is wrong' and 'the IRC did not run' must not
        share an exit code (C-2)."""
        r = p1.evaluate_p1(ORCA_FREQ_GOOD,
                           _xyz("li_ec_radical_reactant.xyz"),
                           _xyz("li_ec_radical_product.xyz"),
                           wall_h=5.0,
                           breakdown_core_h={"crest": 10, "ts_guess": 300,
                                             "ts_opt": 400, "irc": 200, "freq": 90},
                           irc_forward_g16=_C2_FORWARD_G16,
                           irc_reverse_g16=_C2_REVERSE_G16,
                           # below guards.IRC_MIN_POINTS=5 -- the adversarial case
                           irc_forward_n_points=2, irc_reverse_n_points=2,
                           irc_e_ts_hartree=_C2_TS_HARTREE)
        self.assertTrue(r["criteria"]["irc_endpoints_distinct"],
                        "the topology check itself must still say distinct, or this "
                        "is not testing the gap C-2 closes")
        self.assertEqual(r["status"], "undetermined")
        self.assertNotEqual(r["status"], "fail")
        self.assertNotEqual(r["status"], "pass")
        self.assertFalse(r["criteria"]["irc_c2_may_render_chemical_verdict"])

    def test_c2_data_omitted_entirely_is_undetermined_not_a_silent_pass(self):
        """🔴 Rule 18: no G16 termination/energy data supplied at all (e.g. a
        non-Gaussian run, or a caller that has not been updated) must fall toward
        UNKNOWN, never toward permission -- this is the exact shape of the
        r_composite/cost_ratios and P1.sh incidents, applied to C-2."""
        r = p1.evaluate_p1(ORCA_FREQ_GOOD,
                           _xyz("li_ec_radical_reactant.xyz"),
                           _xyz("li_ec_radical_product.xyz"),
                           wall_h=5.0,
                           breakdown_core_h={"crest": 10, "ts_guess": 300,
                                             "ts_opt": 400, "irc": 200, "freq": 90})
        self.assertEqual(r["status"], "undetermined")
        self.assertFalse(r["criteria"]["irc_c2_may_render_chemical_verdict"])

    def test_wall_over_limit_fails(self):
        r = p1.evaluate_p1(ORCA_FREQ_GOOD,
                           _xyz("li_ec_radical_reactant.xyz"),
                           _xyz("li_ec_radical_product.xyz"),
                           wall_h=25.0, breakdown_core_h={"freq": 1.0})
        self.assertEqual(r["status"], "fail")
        self.assertTrue(any("wall_time_exceeded" in x for x in r["fail_reasons"]))


class TestC10CostProbeViolationsDiagnosis(unittest.TestCase):
    """🔴 ADR-090 item 7 / ADR-091, C-10 (MAJOR): `guards.cost_probe_violations` had zero
    callers. Its own docstring names `evaluate_p1`'s shape as THE incident: "RT-1's P1
    rendered [a chemical pass/fail] and the round was spent." Wired as DIAGNOSIS ONLY here
    -- see criteria/p1.py's own comment for why nothing is gated by it yet."""

    def _result(self, wall_h=5.0):
        return p1.evaluate_p1(ORCA_FREQ_GOOD,
                              _xyz("li_ec_radical_reactant.xyz"),
                              _xyz("li_ec_radical_product.xyz"),
                              wall_h=wall_h,
                              breakdown_core_h={"crest": 10, "ts_guess": 300,
                                                "ts_opt": 400, "irc": 200, "freq": 90},
                              irc_forward_g16=_C2_FORWARD_G16,
                              irc_reverse_g16=_C2_REVERSE_G16,
                              irc_forward_n_points=30, irc_reverse_n_points=30,
                              irc_e_ts_hartree=_C2_TS_HARTREE)

    def test_the_violations_list_is_present_and_non_empty(self):
        """P1 is, by design, a chemistry-verdict pilot -- C-10 fires on every result
        regardless of pass/fail/undetermined, which is the point being reported, not hidden."""
        r = self._result()
        self.assertIn("c10_cost_probe_violations", r)
        self.assertTrue(r["c10_cost_probe_violations"])

    def test_a_pass_result_still_reports_the_violation(self):
        r = self._result()
        self.assertEqual(r["status"], "pass")
        self.assertTrue(r["c10_cost_probe_violations"])
        self.assertIn("c10_note", r)

    def test_the_note_is_not_folded_into_fail_reasons(self):
        """🔒 A `pass` carrying a `fail_reasons` entry would read as gating -- it must not."""
        r = self._result()
        self.assertEqual(r["status"], "pass")
        self.assertEqual(r["fail_reasons"], [],
                         "C-10's diagnosis must not appear in fail_reasons on a pass")

    def test_the_guard_is_reached_from_evaluate_p1_not_reimplemented(self):
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(p1))
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr == "cost_probe_violations":
                    calls.add(True)
        self.assertTrue(calls, "criteria/p1.py must call guards.cost_probe_violations, not "
                              "reimplement an equivalent check")


class TestCostBreakdown(unittest.TestCase):
    def test_breakdown(self):
        recs = [{"stage": "crest", "wall_s": 3600, "total_cores": 8, "rc": 0},
                {"stage": "irc", "wall_s": 1800, "total_cores": 64, "rc": 1}]
        bd = cost.breakdown_core_hours(recs, p1.STAGES)
        self.assertAlmostEqual(bd["crest"], 8.0)
        self.assertAlmostEqual(bd["irc"], 32.0)
        self.assertEqual(bd["ts_opt"], 0.0)     # 실행되지 않은 단계는 0으로 명시
        self.assertEqual(cost.stage_status(recs)["irc"], 1)

    def test_job_wall_hours(self):
        self.assertAlmostEqual(
            cost.job_wall_hours({"start_epoch": 0, "end_epoch": 7200}), 2.0)
        self.assertIsNone(cost.job_wall_hours(None))
        self.assertIsNone(cost.job_wall_hours({"start_epoch": "x"}))


class TestP1b(unittest.TestCase):
    def test_ratio_and_pathology(self):
        l1 = {"sp": {"core_hours": 10, "scf": {"max_cycles": 12, "converged": True}},
              "gradient": {"core_hours": 12}, "hessian": {"core_hours": 100},
              "opt5": {"core_hours": 50}}
        l2 = {"sp": {"core_hours": 35, "scf": {"max_cycles": 40, "converged": True}},
              "gradient": {"core_hours": 42}, "hessian": {"core_hours": 500},
              "opt5": {"core_hours": 175}}
        r = p1b.evaluate_p1b(l1, l2)
        self.assertEqual(r["status"], "pass")
        self.assertAlmostEqual(r["cost_ratio_by_stage"]["sp"], 3.5)
        self.assertAlmostEqual(r["cost_ratio_by_stage"]["hessian"], 5.0)
        self.assertTrue(r["criteria"]["diffuse_scf_pathology"])
        self.assertTrue(any("diffuse_scf_pathology" in w for w in r["warnings"]))

    def test_no_pathology(self):
        l1 = {"sp": {"core_hours": 10, "scf": {"max_cycles": 12, "converged": True}}}
        l2 = {"sp": {"core_hours": 30, "scf": {"max_cycles": 15, "converged": True}}}
        r = p1b.evaluate_p1b(l1, l2)
        self.assertFalse(r["criteria"]["diffuse_scf_pathology"])
        self.assertAlmostEqual(r["cost_ratio_unweighted_mean"], 3.0)

    def test_scf_cycle_parsing(self):
        s = p1b.parse_orca_scf_cycles("SCF CONVERGED AFTER  15 CYCLES\n"
                                      "SCF CONVERGED AFTER  9 CYCLES\n")
        self.assertEqual(s["max_cycles"], 15)
        self.assertTrue(s["converged"])
        self.assertFalse(p1b.parse_orca_scf_cycles("SCF NOT CONVERGED")["converged"])

    def test_missing_level2_still_reports(self):
        r = p1b.evaluate_p1b({"sp": {"core_hours": 10}}, {})
        # 비율을 하나도 못 얻으면 P1b는 목적을 달성하지 못한 것이므로 fail이다.
        self.assertEqual(r["status"], "fail")
        self.assertIsNone(r["cost_ratio_by_stage"]["sp"])
        self.assertTrue(any("stage_missing" in w for w in r["warnings"]))


class TestCostRatiosC1(unittest.TestCase):
    """🔴 ADR-088/ADR-090, C-1: `p1b.cost_ratios()` never read `converged` -- it
    decided "missing" purely from `core_hours is None`. `guards.py`'s own
    docstring cites the exact resulting number as C-1's reason to exist:
    "r_composite = 1.0365 was published over a 283 core-h non-convergence."
    These fixtures use the REAL incident numbers (lead's re-derivation), not
    constructed ones -- and, per coder6's family (i) warning, ALSO include a
    genuinely-converged case so the guard is shown to compute a real number,
    not merely to always return None."""

    def test_the_real_r_composite_incident_is_now_null_not_1_0365(self):
        steps = {
            "li_ec2_cation_A_cheap_optfreq": {"core_hours": 282.7378, "converged": False},
            "li_ec2_cation_C_high_sp_on_cheap": {"core_hours": 10.3289, "converged": True},
        }
        rows = p1b.cost_ratios(steps)
        row = next(r for r in rows if r["id"] == "li_ec2_cation")
        self.assertIsNone(row["r_composite"],
                          "the ADR-065 incident number (1.0365) must not reappear")
        self.assertEqual(row["r_composite_provenance"]["reason"], "non_convergent_input")
        self.assertEqual(row["r_composite_provenance"]["steps"], ["A"])
        self.assertIn("A", row["non_converged"])

    def test_the_real_r_high_incident_is_now_null_not_0_3816(self):
        steps = {
            "li_ec_cation_A_cheap_optfreq": {"core_hours": 5.0311, "converged": True},
            "li_ec_cation_B_high_optfreq": {"core_hours": 1.9200, "converged": False},
        }
        rows = p1b.cost_ratios(steps)
        row = next(r for r in rows if r["id"] == "li_ec_cation")
        self.assertIsNone(row["r_high"],
                          "the ADR-065 incident number (0.3816) must not reappear")
        self.assertEqual(row["r_high_provenance"]["reason"], "non_convergent_input")
        self.assertEqual(row["r_high_provenance"]["steps"], ["B"])

    def test_a_genuinely_converged_pair_still_computes_a_real_ratio(self):
        """🔒 coder6 family (i): a guard that only ever returns None cannot be
        told apart from a guard that works. This fixture must produce a NUMBER."""
        steps = {
            "s1_A_cheap_optfreq": {"core_hours": 10.0, "converged": True},
            "s1_C_high_sp_on_cheap": {"core_hours": 2.86, "converged": True},
        }
        rows = p1b.cost_ratios(steps)
        row = rows[0]
        self.assertAlmostEqual(row["r_composite"], 1.286)
        self.assertTrue(row["r_composite_provenance"]["ok"])
        self.assertEqual(row["non_converged"], [])

    def test_missing_core_hours_and_non_convergence_are_DISTINCT_reasons(self):
        """🔴 The lead's explicit constraint: collapsing 'missing' and
        'did not converge' into one reason re-creates the bug in the reader."""
        missing_steps = {
            "s2_A_cheap_optfreq": {"core_hours": 10.0, "converged": True},
            # B entirely absent -> "missing", not "non_convergent"
        }
        row = p1b.cost_ratios(missing_steps)[0]
        self.assertIsNone(row["r_high"])
        self.assertEqual(row["r_high_provenance"]["reason"], "missing_core_hours")
        self.assertIn("B", row["missing"])
        self.assertNotIn("B", row["non_converged"])

        non_conv_steps = {
            "s3_A_cheap_optfreq": {"core_hours": 10.0, "converged": True},
            "s3_B_high_optfreq": {"core_hours": 4.0, "converged": False},
        }
        row2 = p1b.cost_ratios(non_conv_steps)[0]
        self.assertIsNone(row2["r_high"])
        self.assertEqual(row2["r_high_provenance"]["reason"], "non_convergent_input")
        self.assertNotIn("B", row2["missing"])
        self.assertIn("B", row2["non_converged"])

    def test_present_but_unconverged_core_hours_is_missing_not_non_convergent(self):
        """🔴 The lead's own flagged edge case: a step with core_hours=None AND
        converged=False must classify as MISSING (data-absence checked first),
        not as non-convergent -- collapsing the two the other way is just as
        wrong as the original bug, only in the opposite direction."""
        steps = {
            "li_ec2_cation_A_cheap_optfreq": {"core_hours": 282.7378, "converged": False},
            "li_ec2_cation_B_high_optfreq": {"core_hours": None, "converged": False},
        }
        row = p1b.cost_ratios(steps)[0]
        self.assertIsNone(row["r_high"])
        self.assertEqual(row["r_high_provenance"]["reason"], "missing_core_hours")
        self.assertIn("B", row["missing"])

    def test_guards_unconverged_inputs_is_the_single_source_not_a_second_rule(self):
        """Reach, not just correctness: `cost_ratios` must actually CALL
        `guards.unconverged_inputs`, not a hand-rolled equivalent."""
        import ast
        import inspect
        tree = ast.parse(inspect.getsource(p1b))
        calls = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("unconverged_inputs", "derived_or_null"):
                    calls.add(node.func.attr)
        self.assertIn("unconverged_inputs", calls,
                     "p1b.py must call a guards.py convergence function, not "
                     "reimplement one")


# 🔴 P2/P2ext/p2_scaling 테스트(CP2K AIMD 에너지 표류, s(t) 스핀 국재화, 노드 스케일링)를
#    여기서 **제거했다.** 파일럿에서 그 항목들이 사라졌기 때문이다
#    (ADR-015 §7 "개발기 AIMD = 0" → 판정의 소비자 소멸).
#    되살릴 필요가 생기면 HANDOFF_TO_LEAD.md §9 에 무엇을 왜 지웠는지 적어 뒀다.
#    CP2K 는 FIST(고전 MD) 가용성 확인용으로만 남았고, 그건 판정 로직이 없어
#    criteria 모듈이 필요 없다(collect.collect_p2f 가 직접 본다).

class TestP3(unittest.TestCase):
    def test_distribution(self):
        d = p3.candidate_distribution([1, 5, 10, 50, 100, 200, 1000])
        self.assertEqual(d["n_reactants"], 7)
        self.assertAlmostEqual(d["median"], 50.0)
        self.assertEqual(d["max"], 1000)
        self.assertIn(">=1000", d["histogram"])

    def test_empty_distribution(self):
        d = p3.candidate_distribution([])
        self.assertIsNone(d["mean"])

    def test_attempt_stats(self):
        atts = [{"wall_s": 36, "cores": 1, "converged": True, "rc": 0},
                {"wall_s": 72, "cores": 1, "converged": False, "rc": 0},
                {"wall_s": 36, "cores": 1, "converged": False, "rc": 1}]
        s = p3.attempt_stats(atts)
        self.assertAlmostEqual(s["core_hours_total"], 0.04, places=4)
        self.assertAlmostEqual(s["convergence_rate"], 1 / 3.0, places=4)
        self.assertEqual(s["n_crashed"], 1)

    def test_evaluate_requires_50_attempts(self):
        atts = [{"wall_s": 10, "cores": 1, "converged": True, "rc": 0}] * 49
        r = p3.evaluate_p3([120], atts, "b2f2_graph_edit", True)
        self.assertEqual(r["status"], "fail")
        r2 = p3.evaluate_p3([120], atts + atts, "b2f2_graph_edit", True)
        self.assertEqual(r2["status"], "pass")

    def test_engine_mismatch_warning_is_present(self):
        """b2f2 fanout을 S2-A 견적에 그대로 넣으면 안 된다는 경고가 반드시 실린다."""
        r = p3.evaluate_p3([120], [], "b2f2_graph_edit", True)
        self.assertIn("S2-A", r["interpretation_note"])
        r2 = p3.evaluate_p3([120], [], "libe_pool_recombine", True)
        self.assertIn("직접 쓸 수 있다", r2["interpretation_note"])


class TestP4(unittest.TestCase):
    def test_energy_within_tolerance(self):
        a = p4.energy_agreement(-500.1234567, -500.1234517)
        self.assertTrue(a["within_tol"])

    def test_energy_outside_tolerance(self):
        a = p4.energy_agreement(-500.1234567, -500.1230000)
        self.assertFalse(a["within_tol"])

    def test_missing_reference(self):
        a = p4.energy_agreement(None, -500.0)
        self.assertFalse(a["within_tol"])

    def test_speed_ratio(self):
        s = p4.speed_ratio(30.0, 240.0, 64)
        self.assertAlmostEqual(s["ratio_gpu_per_node"], 8.0)

    def test_evaluate(self):
        r = p4.evaluate_p4(-500.0, -500.000001, 30.0, 300.0, 64,
                           max_atoms_ok=200, oom_at_atoms=300, gpu_hours=0.5)
        self.assertEqual(r["status"], "pass")
        self.assertAlmostEqual(r["measurements"]["speed_ratio"]["ratio_gpu_per_node"], 10.0)


class TestProbes(unittest.TestCase):
    def test_throughput_metrics(self):
        starts = [100, 100, 160, 220]
        ends = [160, 160, 220, 280]
        m = probes.throughput_metrics([90] * 4, starts, ends, 4, 4)
        self.assertEqual(m["accepted"], 4)
        self.assertEqual(m["first_start_delay_s"], 10.0)
        self.assertEqual(m["max_concurrent_observed"], 2)
        self.assertEqual(m["all_done_wall_s"], 190.0)

    def test_max_concurrent_endings_before_starts(self):
        self.assertEqual(probes.max_concurrent([0, 10, 20], [10, 20, 30]), 1)
        self.assertEqual(probes.max_concurrent([0, 1, 2], [10, 11, 12]), 3)

    def test_start_rate_lower_bound_when_simultaneous(self):
        m = probes.throughput_metrics([0] * 5, [50] * 5, [110] * 5, 5, 5)
        self.assertTrue(m["start_rate_is_lower_bound"])
        self.assertEqual(m["start_rate_per_min"], 5.0)

    def test_queue_wait_entry_states(self):
        e = probes.queue_wait_entry(64, 1000, 1600)
        self.assertEqual(e["status"], "started")
        self.assertEqual(e["wait_s"], 600.0)
        e2 = probes.queue_wait_entry(64, 1000, None)
        self.assertEqual(e2["status"], "still_queued")
        self.assertIsNone(e2["wait_s"])         # 0으로 만들지 않는다
        e3 = probes.queue_wait_entry(64, 1000, None, rejected=True)
        self.assertEqual(e3["status"], "rejected")

    def test_summarize_queue_wait(self):
        entries = [probes.queue_wait_entry(1, 0, 60), probes.queue_wait_entry(64, 0, 600),
                   probes.queue_wait_entry(16, 0, None)]
        s = probes.summarize_queue_wait(entries)
        self.assertEqual(s["n_started"], 2)
        self.assertEqual(s["max_wait_s"], 600.0)


class TestXyzGraph(unittest.TestCase):
    def test_bond_detection_and_formula(self):
        atoms = xyzgraph.read_xyz_frames(_xyz("li_ec_radical_reactant.xyz"))[0][1]
        bonds = xyzgraph.bond_list(atoms)
        self.assertEqual(len(atoms), 11)
        self.assertIn((1, 2), bonds)          # 고리 O-C 결합이 존재
        comps = xyzgraph.connected_components(len(atoms), bonds)
        self.assertEqual(sorted(xyzgraph.formula(atoms, c) for c in comps),
                         ["C3H4O3", "Li"])

    def test_ring_opening_changes_graph(self):
        a = xyzgraph.read_xyz_frames(_xyz("li_ec_radical_reactant.xyz"))[0][1]
        b = xyzgraph.read_xyz_frames(_xyz("li_ec_radical_product.xyz"))[0][1]
        self.assertNotIn((1, 2), xyzgraph.bond_list(b))   # 개환됨
        distinct, info = xyzgraph.structures_distinct(a, b)
        self.assertTrue(distinct)
        self.assertEqual(info["n_bonds_a"] - info["n_bonds_b"], 1)

    def test_angle_deg_right_angle(self):
        origin, a, b = ("X", 0, 0, 0), ("X", 1, 0, 0), ("X", 0, 1, 0)
        self.assertAlmostEqual(xyzgraph.angle_deg(a, origin, b), 90.0)

    def test_angle_deg_straight_line(self):
        origin, a, b = ("X", 0, 0, 0), ("X", 1, 0, 0), ("X", -1, 0, 0)
        self.assertAlmostEqual(xyzgraph.angle_deg(a, origin, b), 180.0)

    def test_angle_deg_degenerate_arm_is_none(self):
        """A zero-length arm (coincident atoms) is not a measurement, not 0 degrees."""
        p = ("X", 0, 0, 0)
        self.assertIsNone(xyzgraph.angle_deg(p, p, ("X", 1, 0, 0)))

    def test_graph_hash_is_order_invariant(self):
        atoms = xyzgraph.read_xyz_frames(_xyz("li_ec_radical_reactant.xyz"))[0][1]
        shuffled = list(reversed(atoms))
        h1 = xyzgraph.graph_hash(atoms, xyzgraph.bond_list(atoms))
        h2 = xyzgraph.graph_hash(shuffled, xyzgraph.bond_list(shuffled))
        self.assertEqual(h1, h2)


if __name__ == "__main__":
    unittest.main()


class TestP5GeometryRefusalList(unittest.TestCase):
    def test_convicted_rows(self):
        from sei_pilot.criteria import p5
        for tag in ("ec_radical_anion_s0_L2", "li_ec_cation_s0_L2", "li_ec_radical_s0_L2"):
            self.assertTrue(p5.geometry_refused(tag), tag)
        self.assertFalse(p5.geometry_refused("h2o_s0_L2"))
        # convicted but NEVER CONVERGED -> skipped set (no geometry to refuse), §39.103(2)
        self.assertFalse(p5.geometry_refused("li_ec2_cation_s0_L2"))
