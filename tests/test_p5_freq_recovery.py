"""P5 freq-only recovery (§39.103 proposer8 / §R39.65 engineer9): ONE Hessian per stored
converged P5 geometry at production settings. Gated `released:false` like U56-2/sp_ladder."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import config, plan, state, collect
from sei_pilot.criteria import g16, p5

PKG = context.PKG_ROOT
RETURNED = os.path.join(PKG, "..", "..", "cpu_machine_pilot_results", "sei_pilot_work")


class ConfigAndItemTest(unittest.TestCase):
    def test_rows_match_engineer9_table(self):
        cfg = config.load("p5_freq_recovery.json", {})
        rows = cfg["rows"]
        self.assertEqual(17, len(rows))
        self.assertAlmostEqual(651.8, sum(r["task_budget_core_h"] for r in rows), places=1)
        by = dict((r["tag"], r) for r in rows)
        self.assertEqual(205.6, by["emc_s0_L2"]["task_budget_core_h"])
        self.assertEqual(6.4, by["h2o_s0_L2"]["task_budget_core_h"])   # floor
        self.assertEqual(64, cfg["cores_per_task"])
        self.assertEqual(0.25, cfg["min_wall_h"])
        # skipped set and rows are disjoint; li_ec2_cation is skipped, not refused
        skipped = set(cfg["_skipped_rows"]["tags"])
        self.assertFalse(skipped & set(by))
        self.assertIn("li_ec2_cation_s0_L2", skipped)
        self.assertFalse(p5.geometry_refused("li_ec2_cation_s0_L2"))
        for t in ("ec_radical_anion_s0_L2", "li_ec_cation_s0_L2", "li_ec_radical_s0_L2"):
            self.assertTrue(p5.geometry_refused(t), t)
            self.assertIn(t, by)        # convicted rows still RUN (u_freq is a valid datum)

    def test_gate_default_off_and_code_never_flips(self):
        self.assertFalse(plan.p5_freq_recovery_released())
        self.assertEqual([], plan.p5_freq_recovery_items())
        src = open(plan.__file__.replace(".pyc", ".py")).read()
        self.assertNotIn('["released"] = True', src)

    def test_item_shape_when_released(self):
        items = plan.p5_freq_recovery_items.__wrapped__() if hasattr(
            plan.p5_freq_recovery_items, "__wrapped__") else None
        # force the gate for the shape check only
        orig = plan.p5_freq_recovery_released
        plan.p5_freq_recovery_released = lambda cfg=None: True
        try:
            items = plan.p5_freq_recovery_items()
        finally:
            plan.p5_freq_recovery_released = orig
        self.assertEqual(1, len(items))
        it = items[0]
        self.assertEqual("P5_freq_recovery", it.key)
        self.assertEqual((1, 17), it.array)
        self.assertEqual(17, len(it.task_budgets))
        self.assertEqual(64, it.cores_per_task)
        self.assertEqual("payload/P5_FREQ.sh", it.payload)
        self.assertAlmostEqual(651.8, it.core_hours_budget, places=1)
        self.assertTrue(os.path.exists(os.path.join(PKG, it.payload)))


class ParsersOnRealLogTest(unittest.TestCase):
    LOG = os.path.join(RETURNED, "jobs", "P5", "species", "ec_s0_L2", "job.log")

    @unittest.skipUnless(os.path.exists(LOG), "returned tree not present")
    def test_forces_point_group(self):
        t = open(self.LOG, errors="replace").read()
        f = g16.parse_cartesian_forces(t)
        self.assertAlmostEqual(0.000148010, f["max_hartree_per_bohr"])
        self.assertAlmostEqual(0.000035757, f["rms_hartree_per_bohr"])
        self.assertEqual("C2V", g16.parse_point_group(t))
        self.assertIsNone(g16.parse_zpe_and_thermal(t)["zpe_hartree"])   # freq died

    @unittest.skipUnless(os.path.exists(os.path.join(RETURNED, "jobs",
                         "endpoint_prep_reactant_epsinf_full", "endpoint_tight.log")),
                         "returned tree not present")
    def test_thermo_on_converged_log(self):
        t = open(os.path.join(RETURNED, "jobs", "endpoint_prep_reactant_epsinf_full",
                              "endpoint_tight.log"), errors="replace").read()
        th = g16.parse_zpe_and_thermal(t)
        self.assertAlmostEqual(0.074564, th["zpe_hartree"])
        self.assertEqual("C1", g16.parse_point_group(t))


@unittest.skipUnless(shutil.which("bash") and os.path.isdir(RETURNED), "bash/returned tree 없음")
class PayloadRowSelectionOnReturnedTreeTest(unittest.TestCase):
    """Run the payload's row-selection python against the REAL returned P5 tree (no G16)."""

    def _select(self, tid):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = open(os.path.join(PKG, "payload", "P5_FREQ.sh")).read()
        a = src.index("<<'PY'\n") + len("<<'PY'\n")
        b = src.index("\nPY\n", a)
        py = src[a:b]
        env = dict(os.environ, SEI_PKG_ROOT=PKG)
        r = subprocess.run(["python3", "-", d, str(tid), ".t%d" % tid,
                            os.path.join(RETURNED, "jobs", "P5")],
                           input=py, env=env, capture_output=True, universal_newlines=True)
        self.assertEqual(0, r.returncode, r.stderr)
        return json.load(open(os.path.join(d, "row.t%d.json" % tid)))[0], d

    def test_ready_row_extracts_geometry_forces_pg(self):
        cfg = config.load("p5_freq_recovery.json", {})
        tid = [i for i, r in enumerate(cfg["rows"], 1) if r["tag"] == "ec_s0_L2"][0]
        rec, d = self._select(tid)
        self.assertEqual("ready", rec["status"])
        self.assertEqual("C2V", rec["stored_point_group"])
        self.assertAlmostEqual(0.000148010, rec["stored_final_forces"]["max_hartree_per_bohr"])
        xyz = open(os.path.join(d, "rows", "ec_s0_L2", "mol.xyz")).read().splitlines()
        self.assertEqual(int(xyz[0]), len(xyz) - 2)
        self.assertFalse(rec["geometry_refused"])

    def test_convicted_row_is_ready_but_flagged(self):
        cfg = config.load("p5_freq_recovery.json", {})
        tid = [i for i, r in enumerate(cfg["rows"], 1) if r["tag"] == "li_ec_radical_s0_L2"][0]
        rec, _ = self._select(tid)
        self.assertEqual("ready", rec["status"])
        self.assertTrue(rec["geometry_refused"])

    def test_index_out_of_range_is_loud(self):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        src = open(os.path.join(PKG, "payload", "P5_FREQ.sh")).read()
        a = src.index("<<'PY'\n") + len("<<'PY'\n"); b = src.index("\nPY\n", a)
        r = subprocess.run(["python3", "-", d, "99", ".t99", os.path.join(RETURNED, "jobs", "P5")],
                           input=src[a:b], env=dict(os.environ, SEI_PKG_ROOT=PKG),
                           capture_output=True, universal_newlines=True)
        self.assertEqual(5, r.returncode)


@unittest.skipUnless(shutil.which("bash") and os.path.isdir(RETURNED), "bash/returned tree 없음")
class PayloadReadoutOnRealLogTest(unittest.TestCase):
    """Run the payload's per-row READOUT python (§39.108) against a real freq-containing log,
    standalone, no G16 needed. Uses a real ec_s0_L2 P5 row (C2V, from the returned tree) paired
    with a real freq-containing log (the acetone endpoint job, C1) to exercise the three §39.108
    additions without inventing any log content."""

    ENDPOINT_LOG = os.path.join(RETURNED, "jobs", "endpoint_prep_reactant_epsinf_full",
                                "endpoint_tight.log")

    def _readout(self, row):
        d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, d, True)
        os.makedirs(os.path.join(d, "rows", row["tag"]), exist_ok=True)
        shutil.copy(self.ENDPOINT_LOG, os.path.join(d, "rows", row["tag"], "job.log"))
        json.dump([row], open(os.path.join(d, "row.json"), "w"))
        src = open(os.path.join(PKG, "payload", "P5_FREQ.sh")).read()
        marker = "# --- per-row readout"
        a = src.index("<<'PY'\n", src.index(marker)) + len("<<'PY'\n")
        b = src.index("\nPY\n", a)
        r = subprocess.run(["python3", "-", d, ""], input=src[a:b], env=dict(os.environ, SEI_PKG_ROOT=PKG),
                           capture_output=True, universal_newlines=True)
        self.assertEqual(0, r.returncode, r.stderr)
        return json.load(open(os.path.join(d, "p5_freq_task_results.json")))["rows"][0]

    def _base_row(self, tag, point_group, refused=False):
        return {"tag": tag, "status": "ready", "level": "2", "charge": 0, "multiplicity": 1,
                "geometry_refused": refused, "stored_point_group": point_group,
                "stored_final_forces": {"max_hartree_per_bohr": 1e-4, "rms_hartree_per_bohr": 1e-5}}

    def test_non_c1_stored_geometry_is_symmetry_biased(self):
        out = self._readout(self._base_row("fake_c2v_row", "C2V"))
        self.assertIs(True, out["u_opt_symmetry_biased"])
        self.assertIn("SYMMETRY-CONSTRAINED", out["u_opt_symmetry_biased_note"])
        self.assertIn("not usable for SIZING", out["u_cheap_eligibility"])

    def test_c1_stored_geometry_is_not_symmetry_biased(self):
        out = self._readout(self._base_row("fake_c1_row", "C1"))
        self.assertIs(False, out["u_opt_symmetry_biased"])
        self.assertEqual("eligible: assemble u_opt (round 1) + u_freq (this round)",
                         out["u_cheap_eligibility"])

    def test_refused_row_still_reports_symmetry_bias_separately(self):
        # [§39.108(a)] the two flags overlap but neither contains the other.
        out = self._readout(self._base_row("fake_convicted_row", "C2V", refused=True))
        self.assertIs(True, out["u_opt_symmetry_biased"])
        self.assertIn("u_opt_from_trapped_geometry", out["u_cheap_eligibility"])

    def test_n_imag_interpretation_rule_travels_with_the_data(self):
        out = self._readout(self._base_row("fake_row", "C1"))
        self.assertIn("v_imag", out["n_imag_interpretation_rule"])
        self.assertIsInstance(out["imaginary_frequencies_cm1"], list)
        self.assertEqual(out["n_imag"], len(out["imaginary_frequencies_cm1"]))
        self.assertTrue(all(f < 0 for f in out["imaginary_frequencies_cm1"]))

    def test_nosymm_verified_reads_the_freq_jobs_own_point_group(self):
        # the endpoint log's freq step is a real C1 result (see test_thermo_on_converged_log).
        out = self._readout(self._base_row("fake_row2", "C2V"))
        self.assertEqual("C1", out["freq_point_group"])
        self.assertIs(True, out["nosymm_verified"])
        self.assertIn("NOT comparable to stored_point_group", out["nosymm_verified_note"])


class CollectorAssemblyTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.store = state.Store(self.d)

    def _row(self, tag, **over):
        r = {"tag": tag, "status": "ready", "level": "2", "nbasis": 100, "geometry_refused": False,
             "u_freq_core_h": 2.0, "n_imag": 0, "normal_termination": True,
             "stored_point_group": "C1", "u_opt_symmetry_biased": False,
             "force_max_ratio_freq_over_stored_opt": 1.1,
             "chemical_outputs_status": "UNCERTIFIED"}
        r.update(over)
        return r

    def test_assembled_refused_skipped(self):
        # round-1 P5 costs. [critic12] level_label ("G-1"/"G-2"), NOT the wordy `level` string
        # -- real round-1 rows carry the PRE-FIX stale wordy label, which the join must not
        # depend on. G-1 = level2 = primary (config/qc_levels.json), matching `_L2` tags below.
        p5d = self.store.job_dir("P5")
        json.dump({"rows": [{"id": "h2o", "seed": 0, "level_label": "G-1", "core_hours": 1.5},
                            {"id": "li_ec_radical", "seed": 0, "level_label": "G-1",
                             "core_hours": 134.06}]},
                  open(os.path.join(p5d, "p5_results.json"), "w"))
        self.store.mark_submitted("P5", {"job_ids": ["1.pbs"], "submit_epoch": 1})
        # round-2
        d = self.store.job_dir("P5_freq_recovery")
        rows = [self._row("h2o_s0_L2"),
                self._row("li_ec_radical_s0_L2", geometry_refused=True, n_imag=1,
                          stored_point_group="C2V", u_opt_symmetry_biased=True),
                {"tag": "li_ec2_cation_s0_L2", "status": "skipped",
                 "reason": "no_converged_geometry", "cause": "opt_unconverged"}]
        json.dump({"rows": rows}, open(os.path.join(d, "p5_freq_task_results.t1.json"), "w"))
        self.store.mark_submitted("P5_freq_recovery", {"job_ids": ["2.pbs"], "submit_epoch": 2,
                                                       "n_tasks": 1})
        self.store.mark_done("P5_freq_recovery.t1", {"rc": 0, "outcome": "converged"})
        out = collect.collect_p5_freq_recovery(self.store)
        self.assertEqual((1, 1, 1), (out["n_assembled"], out["n_refused"], out["n_skipped"]))
        a = out["u_cheap_rows"][0]
        self.assertEqual("assembled", a["u_cheap_status"])
        self.assertAlmostEqual(3.5, a["u_cheap_core_h"])
        self.assertIn("u_opt", a["u_cheap_provenance"])
        r = out["refused_rows"][0]
        self.assertIsNone(r["u_cheap_core_h"])
        self.assertIn("u_opt_from_trapped_geometry", r["u_cheap_status"])
        self.assertEqual(2.0, r["u_freq_core_h_round2"])      # u_freq still reported
        self.assertEqual("opt_unconverged", out["skipped_rows"][0]["cause"])
        self.assertTrue(any("denominator" in w for w in out["warnings"]))
        self.assertTrue(any("UNCERTIFIED" in w for w in out["warnings"]))

    def test_sizing_biased_warning_distinguishes_confirmed_from_unknown(self):
        # [critic12, 10차 배치] u_cheap_usable_for_sizing is False for BOTH sym_biased=True
        # (confirmed non-C1) and sym_biased=None (unparsed point group) -- the warning TEXT must
        # not claim "=True" for a row that is actually unknown.
        p5d = self.store.job_dir("P5")
        json.dump({"rows": [{"id": "confirmed", "seed": 0, "level_label": "G-1", "core_hours": 1.0},
                            {"id": "unknown", "seed": 0, "level_label": "G-1", "core_hours": 1.0}]},
                  open(os.path.join(p5d, "p5_results.json"), "w"))
        self.store.mark_submitted("P5", {"job_ids": ["1"], "submit_epoch": 1})
        d = self.store.job_dir("P5_freq_recovery")
        rows = [self._row("confirmed_s0_L2", stored_point_group="C2V", u_opt_symmetry_biased=True),
                self._row("unknown_s0_L2", stored_point_group=None, u_opt_symmetry_biased=None)]
        json.dump({"rows": rows}, open(os.path.join(d, "p5_freq_task_results.t1.json"), "w"))
        self.store.mark_submitted("P5_freq_recovery", {"job_ids": ["2"], "submit_epoch": 2,
                                                       "n_tasks": 1})
        self.store.mark_done("P5_freq_recovery.t1", {"rc": 0, "outcome": "converged"})
        out = collect.collect_p5_freq_recovery(self.store)
        self.assertEqual(2, out["n_sizing_biased"])
        w = [x for x in out["warnings"] if "NOT usable for SIZING" in x][0]
        self.assertIn("1 confirmed u_opt_symmetry_biased=True: confirmed_s0_L2", w)
        self.assertIn("1 with UNKNOWN stored point group", w)
        self.assertIn("unknown_s0_L2", w)
        # the confirmed row's tag must not appear inside the "UNKNOWN" clause and vice versa
        unknown_clause = w.split("UNKNOWN stored point group")[1]
        self.assertNotIn("confirmed_s0_L2", unknown_clause)


@unittest.skipUnless(os.path.isdir(os.path.join(RETURNED, "jobs", "P5")), "returned tree 없음")
class CollectorRealTreeLevelJoinTest(unittest.TestCase):
    """[critic12, 2026-08-21] regression for the real bug: collect_p5_freq_recovery's u_opt join
    used to compare round-1 rows' WORDY `level` string against today's config-derived
    LEVEL_PRIMARY/LEVEL_CHEAP -- real round-1 rows carry the PRE-FIX stale wordy label, which
    matches neither, so every row fell into the `else` branch (always tagged `_L2`, silently
    dropping every true L1 row and colliding L1/L2 costs under one key). Built from the REAL
    returned P5 tree, not a mock that already assumes the fix."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.d, True)
        self.store = state.Store(self.d)
        p5d = self.store.job_dir("P5")
        for fn in os.listdir(os.path.join(RETURNED, "jobs", "P5")):
            if fn.startswith("p5_task_results"):
                shutil.copy(os.path.join(RETURNED, "jobs", "P5", fn), os.path.join(p5d, fn))
        self.store.mark_submitted("P5", {"job_ids": ["real"], "submit_epoch": 1})

    def _freq_row(self, tag):
        return {"tag": tag, "status": "ready", "level": "2" if tag.endswith("L2") else "1",
                "nbasis": 100, "geometry_refused": False, "u_freq_core_h": 1.0, "n_imag": 0,
                "normal_termination": True, "stored_point_group": "C1",
                "u_opt_symmetry_biased": False,
                "force_max_ratio_freq_over_stored_opt": 1.0, "chemical_outputs_status": "x"}

    def test_dual_level_species_get_distinct_correct_u_opt(self):
        # real values, from cpu_machine_pilot_results/.../jobs/P5/p5_task_results.t*.json:
        # ec seed0: G-1 (level2, primary) 8.83556 core-h; G-2 (level1, cheap) 8.23111 core-h.
        rows = [self._freq_row("ec_s0_L1"), self._freq_row("ec_s0_L2"),
                self._freq_row("emc_s0_L1"), self._freq_row("emc_s0_L2"),
                self._freq_row("co2_s0_L1"), self._freq_row("co2_s0_L2")]
        d = self.store.job_dir("P5_freq_recovery")
        json.dump({"rows": rows}, open(os.path.join(d, "p5_freq_task_results.t1.json"), "w"))
        self.store.mark_submitted("P5_freq_recovery", {"job_ids": ["2"], "submit_epoch": 2,
                                                        "n_tasks": 1})
        self.store.mark_done("P5_freq_recovery.t1", {"rc": 0, "outcome": "converged"})
        out = collect.collect_p5_freq_recovery(self.store)
        by_tag = dict((e["tag"], e) for e in out["u_cheap_rows"])
        self.assertAlmostEqual(8.23111, by_tag["ec_s0_L1"]["u_opt_core_h_round1"], places=4)
        self.assertAlmostEqual(8.83556, by_tag["ec_s0_L2"]["u_opt_core_h_round1"], places=4)
        self.assertAlmostEqual(12.81778, by_tag["emc_s0_L1"]["u_opt_core_h_round1"], places=4)
        self.assertAlmostEqual(16.05333, by_tag["emc_s0_L2"]["u_opt_core_h_round1"], places=4)
        self.assertAlmostEqual(1.6, by_tag["co2_s0_L1"]["u_opt_core_h_round1"], places=4)
        self.assertAlmostEqual(1.58222, by_tag["co2_s0_L2"]["u_opt_core_h_round1"], places=4)
        # every row here has a real, distinct u_opt -- none is None (the pre-fix symptom) and
        # L1 != L2 for the same species (the pre-fix collision).
        for tag in ("ec", "emc", "co2"):
            self.assertNotEqual(by_tag["%s_s0_L1" % tag]["u_opt_core_h_round1"],
                                by_tag["%s_s0_L2" % tag]["u_opt_core_h_round1"])
            self.assertIsNotNone(by_tag["%s_s0_L1" % tag]["u_opt_core_h_round1"])


if __name__ == "__main__":
    unittest.main()
