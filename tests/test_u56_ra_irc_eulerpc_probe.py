"""EulerPC escalation: the from-scratch reverse-arm EulerPC IRC redo builder (proposer13's
§39.129 ruling, engineer14's §R39.85 pricing, 02_METHOD_SPEC.md / 03_COMPUTE_PLAN.md) -- a
backup tier staged alongside Candidate B, sharing its stepsize/recorrect but swapping the
predictor to EulerPC and widening the maxpoints hedge.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_u56_ra_irc_eulerpc_probe.py")
REAL_XYZ = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
HAVE_BASH = shutil.which("bash") is not None


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class BuildU56RAIrcEulerpcProbeTest(unittest.TestCase):
    def setUp(self):
        self.job_dir = tempfile.mkdtemp(prefix="sei_srcjob_")
        self.out_dir = tempfile.mkdtemp(prefix="sei_eulerpc_")
        shutil.copyfile(REAL_XYZ, os.path.join(self.job_dir, "ts.xyz"))

    def tearDown(self):
        shutil.rmtree(self.job_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run(self, extra=()):
        return subprocess.run(
            [sys.executable, TOOL, "--job-dir", self.job_dir, "--out-dir", self.out_dir]
            + list(extra),
            capture_output=True, universal_newlines=True, timeout=60)

    def test_builds_full_deck_with_maxpoints_100(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        gjf = os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")
        text = open(gjf).read()
        self.assertNotIn("geom=check", text)
        self.assertNotIn("guess=read", text)
        self.assertIn(
            "irc=(calcfc,reverse,EulerPC,recorrect=never,stepsize=2,maxpoints=100)", text)
        self.assertIn("scrf=(pcm,solvent=acetone,read)", text)
        self.assertIn("eps=18.5", text)
        self.assertIn("0 2\n", text)
        self.assertIn("Li", text)

        manifest = json.load(open(os.path.join(self.out_dir, "manifest_eulerpc_probe.json")))
        self.assertFalse(manifest["smoke"])
        self.assertIn("route_syntax_status", manifest)
        self.assertIn("NEEDS VERIFICATION", manifest["route_syntax_status"])
        self.assertTrue(manifest["not_a_restart"])
        self.assertEqual(manifest["direction"], "reverse")
        self.assertTrue(manifest["recorrect_never"])
        self.assertTrue(manifest["eulerpc"])
        self.assertEqual(manifest["stepsize"], 2)
        self.assertEqual(manifest["maxpoints"], 100)
        self.assertEqual(len(manifest["mandatory_post_run_checks"]), 4)
        checks_text = " ".join(manifest["mandatory_post_run_checks"])
        self.assertIn("Euler-predictor echo", checks_text)
        self.assertIn("Recorrection delta-x convergence threshold", checks_text)
        self.assertIn("arc 2.0-2.3", checks_text)
        self.assertIn("Bulirsch-Stoer Method is not Converging", checks_text)

    def test_smoke_flag_builds_a_separate_maxpoints_2_deck(self):
        proc = self._run(["--smoke"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        gjf = os.path.join(self.out_dir, "irc_eulerpc_smoke.gjf")
        text = open(gjf).read()
        self.assertIn(
            "irc=(calcfc,reverse,EulerPC,recorrect=never,stepsize=2,maxpoints=2)", text)

        manifest = json.load(open(os.path.join(self.out_dir, "manifest_eulerpc_smoke.json")))
        self.assertTrue(manifest["smoke"])
        self.assertEqual(manifest["maxpoints"], 2)

    def test_smoke_and_full_can_coexist_in_the_same_out_dir(self):
        """Different filenames by design -- staging both side by side is the whole point."""
        proc_smoke = self._run(["--smoke"])
        self.assertEqual(proc_smoke.returncode, 0, proc_smoke.stdout + proc_smoke.stderr)
        proc_full = self._run()
        self.assertEqual(proc_full.returncode, 0, proc_full.stdout + proc_full.stderr)

        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "irc_eulerpc_smoke.gjf")))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")))
        self.assertTrue(os.path.exists(
            os.path.join(self.out_dir, "manifest_eulerpc_smoke.json")))
        self.assertTrue(os.path.exists(
            os.path.join(self.out_dir, "manifest_eulerpc_probe.json")))

    def test_total_cores_defaults_to_64_not_1(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")).read()
        self.assertIn("%nprocshared=64\n", text)

    def test_total_cores_is_still_overridable(self):
        proc = self._run(["--total-cores", "32"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")).read()
        self.assertIn("%nprocshared=32\n", text)

    def test_missing_ts_xyz_is_refused_not_guessed(self):
        os.remove(os.path.join(self.job_dir, "ts.xyz"))
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no ", proc.stderr)

    def test_stepsize_matches_candidate_b_and_recorrect_never_present(self):
        """🔴 [proposer13 §39.129(3)] single-variable-change discipline -- stepsize must be
        IDENTICAL to Candidate B's, and recorrect=never must carry forward unchanged."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")).read()
        self.assertIn("stepsize=2", text)
        self.assertIn("recorrect=never", text)
        self.assertIn("EulerPC", text)

    def test_rerun_into_same_out_dir_refuses_to_clobber_existing_deck(self):
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        gjf_path = os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")
        before = open(gjf_path).read()

        proc2 = self._run()
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)
        self.assertEqual(open(gjf_path).read(), before)

    def test_a_failed_build_leaves_no_deck_for_the_corrected_retry_to_trip_over(self):
        proc1 = self._run(["--level", "99"])
        self.assertNotEqual(proc1.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "irc_eulerpc_probe.gjf")))

        proc2 = self._run()   # corrected retry, same out-dir
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)


if __name__ == "__main__":
    unittest.main()
