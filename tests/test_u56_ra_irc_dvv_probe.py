"""DVV escalation: the from-scratch reverse-arm DVV IRC redo builder, third-tier backup
(proposer13's §39.130 ruling, engineer14's §R39.86 pricing, 02_METHOD_SPEC.md /
03_COMPUTE_PLAN.md) -- a three-rung fallback ladder, all six deck/smoke variants pre-built.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_u56_ra_irc_dvv_probe.py")
REAL_XYZ = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
HAVE_BASH = shutil.which("bash") is not None


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class BuildU56RAIrcDvvProbeTest(unittest.TestCase):
    def setUp(self):
        self.job_dir = tempfile.mkdtemp(prefix="sei_srcjob_")
        self.out_dir = tempfile.mkdtemp(prefix="sei_dvv_")
        shutil.copyfile(REAL_XYZ, os.path.join(self.job_dir, "ts.xyz"))

    def tearDown(self):
        shutil.rmtree(self.job_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run(self, extra=()):
        return subprocess.run(
            [sys.executable, TOOL, "--job-dir", self.job_dir, "--out-dir", self.out_dir]
            + list(extra),
            capture_output=True, universal_newlines=True, timeout=60)

    def test_rung1_full_keeps_calcfc_no_gradientonly_no_recorrect(self):
        proc = self._run()   # default rung=1, full
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_dvv_rung1_full.gjf")).read()
        self.assertIn("irc=(calcfc,reverse,DVV,stepsize=2,maxpoints=100)", text)
        self.assertNotIn("recorrect", text.lower())
        self.assertNotIn("GradientOnly", text)

        manifest = json.load(open(os.path.join(self.out_dir, "manifest_dvv_rung1_full.json")))
        self.assertEqual(manifest["rung"], 1)
        self.assertFalse(manifest["smoke"])
        self.assertFalse(manifest["recorrect_never"])
        self.assertIn("recorrect_omitted_reason", manifest)
        self.assertEqual(manifest["maxpoints"], 100)
        self.assertEqual(len(manifest["mandatory_post_run_checks"]), 5)
        checks_text = " ".join(manifest["mandatory_post_run_checks"])
        self.assertIn("Integration scheme", checks_text)
        self.assertIn("Bulirsch-Stoer", checks_text)
        self.assertIn("NO Recorrection", checks_text)

    def test_rung2_drops_calcfc(self):
        proc = self._run(["--rung", "2"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_dvv_rung2_full.gjf")).read()
        self.assertIn("irc=(reverse,DVV,stepsize=2,maxpoints=100)", text)
        self.assertNotIn("calcfc", text)

    def test_rung3_drops_calcfc_adds_gradientonly(self):
        proc = self._run(["--rung", "3"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_dvv_rung3_full.gjf")).read()
        self.assertIn("irc=(reverse,DVV,GradientOnly,stepsize=2,maxpoints=100)", text)
        self.assertNotIn("calcfc", text)

        manifest = json.load(open(os.path.join(self.out_dir, "manifest_dvv_rung3_full.json")))
        self.assertIn("FLOOR", manifest["rung_note"])
        self.assertIn("re-smoke", manifest["rung_note"])

    def test_smoke_uses_maxpoints_3_not_100(self):
        proc = self._run(["--smoke"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_dvv_rung1_smoke.gjf")).read()
        self.assertIn("maxpoints=3", text)
        self.assertNotIn("maxpoints=100", text)

        manifest = json.load(open(os.path.join(self.out_dir, "manifest_dvv_rung1_smoke.json")))
        self.assertTrue(manifest["smoke"])
        self.assertEqual(manifest["maxpoints"], 3)

    def test_all_six_rung_smoke_combinations_coexist_in_one_out_dir(self):
        """Pre-building the whole ladder is the whole point -- nobody hand-edits a route
        string on the cluster."""
        for rung in (1, 2, 3):
            for extra in ([], ["--smoke"]):
                proc = self._run(["--rung", str(rung)] + extra)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        files = os.listdir(self.out_dir)
        gjf_files = sorted(f for f in files if f.endswith(".gjf"))
        self.assertEqual(len(gjf_files), 6)
        manifest_files = sorted(f for f in files if f.startswith("manifest_") and
                                f.endswith(".json"))
        self.assertEqual(len(manifest_files), 6)

    def test_total_cores_defaults_to_64_not_1(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_dvv_rung1_full.gjf")).read()
        self.assertIn("%nprocshared=64\n", text)

    def test_missing_ts_xyz_is_refused_not_guessed(self):
        os.remove(os.path.join(self.job_dir, "ts.xyz"))
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no ", proc.stderr)

    def test_invalid_rung_is_refused(self):
        proc = self._run(["--rung", "4"])
        self.assertNotEqual(proc.returncode, 0)

    def test_rerun_same_rung_smoke_combo_refuses_to_clobber(self):
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        gjf_path = os.path.join(self.out_dir, "irc_dvv_rung1_full.gjf")
        before = open(gjf_path).read()

        proc2 = self._run()
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)
        self.assertEqual(open(gjf_path).read(), before)

    def test_a_failed_build_leaves_no_deck_for_the_corrected_retry_to_trip_over(self):
        proc1 = self._run(["--level", "99"])
        self.assertNotEqual(proc1.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "irc_dvv_rung1_full.gjf")))

        proc2 = self._run()   # corrected retry, same out-dir
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)


if __name__ == "__main__":
    unittest.main()
