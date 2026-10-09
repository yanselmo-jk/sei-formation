"""S3 wave-1 attempt 1: T21-se STAGE 1 ONLY submission-wrapper builder (02_METHOD_SPEC.md
§39.136 addendum; 03_COMPUTE_PLAN.md §R39.88 §3/§R39.89/§R39.91) -- mirrors
test_build_wave1_rb_submission.py's own conventions (same sibling tool, same harness reuse
shape).
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_wave1_t21se_stage1_submission.py")


class BuildWave1T21seStage1SubmissionTest(unittest.TestCase):
    def setUp(self):
        self.out_dir = tempfile.mkdtemp(prefix="sei_wave1_t21se_")

    def tearDown(self):
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run(self, extra=()):
        return subprocess.run(
            [sys.executable, TOOL, "--out-dir", self.out_dir] + list(extra),
            capture_output=True, universal_newlines=True, timeout=60)

    def test_builds_qsub_and_cmd_sh(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertTrue(os.path.exists(
            os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")))
        self.assertTrue(os.path.exists(
            os.path.join(self.out_dir, "U56_RC_scan_wave1.cmd.sh")))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "manifest.json")))

    def test_route_env_matches_the_ruled_t21se_attempt(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")).read()
        self.assertIn('export SEI_U56_REACTION="R-C"', text)
        self.assertIn('export SEI_U56_METHOD="relaxed_scan"', text)
        self.assertIn('export SEI_U56_REACTANT_ENDPOINT_KEY="endpoint_prep_rc_reactant"', text)
        self.assertIn('export SEI_QC_LEVEL="2"', text)
        self.assertIn("select=1:ncpus=64:mpiprocs=64", text)

    def test_stage_limit_flag_is_set_by_default(self):
        """🔴 The whole point of this tool: stage 1 must stop itself, not run the full chain.
        Default behaviour (no --stop-after-stage override) must set the flag."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")).read()
        self.assertIn('export SEI_U56_STOP_AFTER="u56_scan"', text)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertEqual(manifest["stage_limit"]["mechanism"], "SEI_U56_STOP_AFTER=u56_scan")

    def test_wall_cap_matches_the_ruled_point_density_adjusted_figure(self):
        """03_COMPUTE_PLAN.md §R39.91: 22.3h wall / 1,428 core-h at 64 cores
        (1428/22.3 = 64.04 -> 64, matching R-A/R-B's own core count)."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")).read()
        self.assertIn("#PBS -l walltime=22:18:00", text)   # 22.3h
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertEqual(manifest["wall_h"], 22.3)
        self.assertEqual(manifest["cores"], 64)
        self.assertIn("§R39.91", manifest["wall_cap_basis"])
        self.assertIn("1,428", manifest["wall_cap_basis"])

    def test_job_dir_env_points_at_the_remote_cluster_path_not_the_local_out_dir(self):
        proc = self._run(["--pkg-root", "/scratch/fake/pkg3"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")).read()
        self.assertIn('export SEI_JOB_DIR="/scratch/fake/pkg3/sei_pilot_work/jobs/'
                     'U56_RC_scan_wave1"', text)
        self.assertNotIn(self.out_dir, text)

    def test_fresh_key_does_not_collide_with_r_a_or_r_b(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertNotIn(manifest["job_key"], ("U56_RA_scan", "U56_RB_scan", "U56_RA_qst2"))

    def test_recorrect_never_and_rcfc_defaults_are_picked_up_automatically(self):
        """No env var to set here -- config/qc_levels.json's irc_forward/irc_reverse (and their
        rcfc variants) already carry recorrect=never project-wide; this tool inherits it."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        # stage 1 never reaches IRC, but confirm the tool makes no attempt to override/disable
        # the project-wide default via extra_env (it shouldn't set any IRC-related env at all).
        text = open(os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")).read()
        self.assertNotIn("RECORRECT", text.upper().replace("SEI_U56_STOP_AFTER", ""))

    def test_rerun_with_different_spec_refuses_to_clobber(self):
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        proc2 = self._run(["--wall-h", "3.0"])
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)

    def test_rerun_with_identical_spec_is_a_harmless_noop(self):
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        proc2 = self._run()
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)

    def test_stage_2_5_are_not_built_here_documented_not_silent(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIn("genuinely unpriced", manifest["purpose"])
        self.assertIn("STOP AND RE-SCOPE", manifest["wall_cap_basis"])

    def test_qsub_carries_a_deployed_package_fingerprint_guard_that_actually_refuses(self):
        """Same shape as the R-B/stage0 tools' own copy of this test -- extract the real guard
        block (lands in the qsub, right after common.sh is sourced, per lead's explicit
        scoping) and RUN it, don't just assert on the string (critic17's own lesson this
        round). The guard calls common.sh's own sei_pkg_fingerprint(), so source the real
        common.sh first."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        qsub_text = open(os.path.join(self.out_dir, "U56_RC_scan_wave1.qsub")).read()
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        expected_fp = manifest["deployed_package_fingerprint_check"]["expected"]
        self.assertIn('SEI_EXPECTED_PKG_FINGERPRINT="%s"' % expected_fp, qsub_text)

        m = re.search(r"SEI_EXPECTED_PKG_FINGERPRINT=.*?\nfi\n", qsub_text, re.S)
        self.assertIsNotNone(m)
        guard = m.group(0)
        source_common = '. "%s/payload/common.sh"\n' % context.PKG_ROOT

        mismatch = subprocess.run(
            ["bash", "-c", source_common + 'SEI_PKG_ROOT="/tmp"\n' + guard + "echo UNREACHABLE"],
            env=dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT),
            capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(mismatch.returncode, 9, mismatch.stdout + mismatch.stderr)
        self.assertNotIn("UNREACHABLE", mismatch.stdout)
        self.assertIn("false-alarm", mismatch.stdout + mismatch.stderr)

        match = subprocess.run(
            ["bash", "-c", source_common + guard + "echo GUARD_PASSED"],
            env=dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT,
                    SEI_WORKDIR=context.PKG_ROOT + "/sei_pilot_work"),
            capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(match.returncode, 0, match.stdout + match.stderr)
        self.assertIn("GUARD_PASSED", match.stdout)


if __name__ == "__main__":
    unittest.main()
