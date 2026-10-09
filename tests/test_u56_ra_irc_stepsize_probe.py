"""Candidate B: the from-scratch reverse-arm StepSize IRC redo builder (proposer13's §39.127
ruling, engineer14's §R39.82/83 pricing, 02_METHOD_SPEC.md / 03_COMPUTE_PLAN.md).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_u56_ra_irc_stepsize_probe.py")
REAL_XYZ = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
HAVE_BASH = shutil.which("bash") is not None


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class BuildU56RAIrcStepsizeProbeTest(unittest.TestCase):
    def setUp(self):
        self.job_dir = tempfile.mkdtemp(prefix="sei_srcjob_")
        self.out_dir = tempfile.mkdtemp(prefix="sei_stepsize_")
        shutil.copyfile(REAL_XYZ, os.path.join(self.job_dir, "ts.xyz"))

    def tearDown(self):
        shutil.rmtree(self.job_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run(self, extra=()):
        return subprocess.run(
            [sys.executable, TOOL, "--job-dir", self.job_dir, "--out-dir", self.out_dir]
            + list(extra),
            capture_output=True, universal_newlines=True, timeout=60)

    def test_builds_from_scratch_deck_with_full_coordinates(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        gjf = os.path.join(self.out_dir, "irc_stepsize_probe.gjf")
        text = open(gjf).read()
        # no restart -- full coordinate block, no geom=check/guess=read
        self.assertNotIn("geom=check", text)
        self.assertNotIn("guess=read", text)
        self.assertIn("irc=(calcfc,reverse,recorrect=never,stepsize=2,maxpoints=70)", text)
        self.assertIn("scrf=(pcm,solvent=acetone,read)", text)
        self.assertIn("eps=18.5", text)
        self.assertIn("0 2\n", text)
        self.assertIn("Li", text)   # gen basis covers the real element set
        self.assertIn("C   ", text)   # a real coordinate row, not geom=check's blank gap

        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIn("route_syntax_status", manifest)
        self.assertIn("NEEDS VERIFICATION", manifest["route_syntax_status"])
        self.assertTrue(manifest["not_a_restart"])
        self.assertEqual(manifest["direction"], "reverse")
        self.assertTrue(manifest["recorrect_never"])
        self.assertEqual(manifest["stepsize"], 2)
        self.assertEqual(manifest["maxpoints"], 70)
        self.assertIn("arc 2.0-2.3", manifest["mandatory_post_run_check"])

    def test_total_cores_defaults_to_64_not_1(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_stepsize_probe.gjf")).read()
        self.assertIn("%nprocshared=64\n", text)

    def test_total_cores_is_still_overridable(self):
        proc = self._run(["--total-cores", "32"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_stepsize_probe.gjf")).read()
        self.assertIn("%nprocshared=32\n", text)

    def test_missing_ts_xyz_is_refused_not_guessed(self):
        os.remove(os.path.join(self.job_dir, "ts.xyz"))
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no ", proc.stderr)

    def test_maxpoints_and_stepsize_are_never_left_to_a_default(self):
        """🔴 [engineer14 §R39.82 §6] whoever builds this tool must not let it default
        total_cores, maxpoints, or the corrector keyword -- all three must be explicit,
        verified-present in the emitted .gjf. No CLI flag exists to accidentally omit them --
        they are fixed, ruled constants, always written."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_stepsize_probe.gjf")).read()
        self.assertIn("stepsize=2", text)
        self.assertIn("maxpoints=70", text)
        self.assertIn("recorrect=never", text)

    def test_rerun_into_same_out_dir_refuses_to_clobber_existing_deck(self):
        """Same idempotency-safety convention as build_u56_ra_irc_recorrect_probe.py's fix
        (05_STATE.md §1f carry-over 3) -- built in from the start here, not a follow-up fix."""
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        gjf_path = os.path.join(self.out_dir, "irc_stepsize_probe.gjf")
        before = open(gjf_path).read()

        proc2 = self._run()
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)
        self.assertEqual(open(gjf_path).read(), before)

    def test_a_failed_build_leaves_no_deck_for_the_corrected_retry_to_trip_over(self):
        proc1 = self._run(["--level", "99"])
        self.assertNotEqual(proc1.returncode, 0)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "irc_stepsize_probe.gjf")))

        proc2 = self._run()   # corrected retry, same out-dir
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)


if __name__ == "__main__":
    unittest.main()
