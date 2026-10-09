"""S3 wave-1 attempt 2: R-B redo submission-wrapper builder (02_METHOD_SPEC.md §39.136(1)/(2),
03_COMPUTE_PLAN.md §R39.88/89) -- reuses `sei_pilot.scheduler`'s own PBS rendering, build-only,
no `submit()` anywhere in the path this tool calls.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_wave1_rb_submission.py")
ORIGINAL_QSUB = os.path.join(context.REPO_ROOT, "cpu_machine_pilot_results",
                             "sei_pilot_work", "jobs", "U56_RB_scan", "U56_RB_scan.qsub")
ORIGINAL_CMD = os.path.join(context.REPO_ROOT, "cpu_machine_pilot_results",
                            "sei_pilot_work", "jobs", "U56_RB_scan", "U56_RB_scan.cmd.sh")


class BuildWave1RbSubmissionTest(unittest.TestCase):
    def setUp(self):
        self.out_dir = tempfile.mkdtemp(prefix="sei_wave1_rb_")

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
            os.path.join(self.out_dir, "U56_RB_scan_wave1.qsub")))
        self.assertTrue(os.path.exists(
            os.path.join(self.out_dir, "U56_RB_scan_wave1.cmd.sh")))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "manifest.json")))

    def test_route_env_matches_the_ruled_rb_attempt(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RB_scan_wave1.qsub")).read()
        self.assertIn('export SEI_U56_REACTION="R-B"', text)
        self.assertIn('export SEI_U56_METHOD="relaxed_scan"', text)
        self.assertIn('export SEI_U56_REACTANT_ENDPOINT_KEY="endpoint_prep_reactant"', text)
        self.assertIn('export SEI_QC_LEVEL="2"', text)
        self.assertIn("select=1:ncpus=64:mpiprocs=64", text)

    def test_job_dir_env_points_at_the_remote_cluster_path_not_the_local_out_dir(self):
        """🔴 The bug this test pins: SEI_JOB_DIR/CMD_FILE must reference where the job will
        actually RUN on the cluster, not this tool's local --out-dir (a real bug caught before
        this tool shipped -- building and running happen on different filesystems here, unlike
        every other use of sei_pilot.scheduler in this project)."""
        proc = self._run(["--pkg-root", "/scratch/fake/pkg"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RB_scan_wave1.qsub")).read()
        self.assertIn('export SEI_JOB_DIR="/scratch/fake/pkg/sei_pilot_work/jobs/'
                     'U56_RB_scan_wave1"', text)
        self.assertNotIn(self.out_dir, text)
        cmd_line = [ln for ln in text.splitlines() if "sei_job_main" in ln][0]
        self.assertIn("/scratch/fake/pkg/sei_pilot_work/jobs/U56_RB_scan_wave1/"
                     "U56_RB_scan_wave1.cmd.sh", cmd_line)
        self.assertNotIn(self.out_dir, cmd_line)

    def test_byte_identical_to_the_original_returned_qsub_modulo_the_job_key(self):
        """🔴🔴 The strongest regression available: diff against the ACTUAL returned
        U56_RB_scan.qsub, not a fixture -- confirms this tool reproduces the real production
        harness's own wrapper shape exactly, not an approximation of it.

        🔴 [lead, wave-1 review items 3/5] the qsub now carries a deployed-package fingerprint
        guard the ORIGINAL harness-produced qsub never had (this tool's OWN addition, inserted
        via string surgery on the rendered qsub_text, not reused scheduler/template code -- see
        build_wave1_rb_submission.py's own comment at the guard's construction). Byte-identity
        of the REUSED harness code path is checked here on everything EXCEPT that guard block
        (stripped before comparing); the guard itself is tested separately below. cmd.sh needs
        NO such stripping -- the guard moved out of it entirely this pass (an earlier version
        lived in cmd.sh; landing it in the qsub instead resolves that tension for free), so
        cmd.sh is compared byte-for-byte, unmodified."""
        if not os.path.exists(ORIGINAL_QSUB):
            self.skipTest("returned U56_RB_scan.qsub not present (running from the tarball)")
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        mine = open(os.path.join(self.out_dir, "U56_RB_scan_wave1.qsub")).read()
        original = open(ORIGINAL_QSUB).read()
        # strip the guard block (SEI_EXPECTED_PKG_FINGERPRINT=... through its closing "fi\n") --
        # this tool's own addition, absent from the historical harness-produced qsub.
        self.assertIn("SEI_EXPECTED_PKG_FINGERPRINT=", mine)
        guard_end = mine.index("SEI_EXPECTED_PKG_FINGERPRINT=") + \
            mine[mine.index("SEI_EXPECTED_PKG_FINGERPRINT="):].index("\nfi\n") + len("\nfi\n")
        mine_without_guard = (mine[:mine.index("SEI_EXPECTED_PKG_FINGERPRINT=")]
                              + mine[guard_end:])
        mine_normalized = mine_without_guard.replace("U56_RB_scan_wave1", "U56_RB_scan")
        self.assertEqual(mine_normalized, original)

        mine_cmd = open(os.path.join(self.out_dir, "U56_RB_scan_wave1.cmd.sh")).read()
        original_cmd = open(ORIGINAL_CMD).read()
        self.assertEqual(mine_cmd.replace("U56_RB_scan_wave1", "U56_RB_scan"), original_cmd)

    def test_qsub_carries_a_deployed_package_fingerprint_guard_that_actually_refuses(self):
        """Same shape as test_build_wave1_stage0_submission.py's own copy of this test --
        extract the real guard block and RUN it (sourcing the real common.sh first, since the
        guard now calls common.sh's own sei_pkg_fingerprint() rather than reimplementing the
        hash inline), don't just assert on the string."""
        import re
        import subprocess as sp
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        qsub_text = open(os.path.join(self.out_dir, "U56_RB_scan_wave1.qsub")).read()
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        expected_fp = manifest["deployed_package_fingerprint_check"]["expected"]
        self.assertIn('SEI_EXPECTED_PKG_FINGERPRINT="%s"' % expected_fp, qsub_text)

        m = re.search(r"SEI_EXPECTED_PKG_FINGERPRINT=.*?\nfi\n", qsub_text, re.S)
        self.assertIsNotNone(m)
        guard = m.group(0)
        # source the REAL common.sh so sei_pkg_fingerprint() is genuinely defined, matching how
        # the qsub itself always sources it before this guard ever runs.
        source_common = '. "%s/payload/common.sh"\n' % context.PKG_ROOT

        mismatch = sp.run(
            ["bash", "-c", source_common + 'SEI_PKG_ROOT="/tmp"\n' + guard + "echo UNREACHABLE"],
            env=dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT),
            capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(mismatch.returncode, 9, mismatch.stdout + mismatch.stderr)
        self.assertNotIn("UNREACHABLE", mismatch.stdout)
        self.assertIn("false-alarm", mismatch.stdout + mismatch.stderr)

        match = sp.run(["bash", "-c", source_common + guard + "echo GUARD_PASSED"],
                       env=dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT,
                               SEI_WORKDIR=context.PKG_ROOT + "/sei_pilot_work"),
                       capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(match.returncode, 0, match.stdout + match.stderr)
        self.assertIn("GUARD_PASSED", match.stdout)

    def test_fresh_key_does_not_collide_with_the_original_rejected_job(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertNotEqual(manifest["job_key"], "U56_RB_scan")
        self.assertNotIn("U56_RB_scan/", manifest["job_dir_remote"])

    def test_recorrect_never_default_is_documented_not_silently_assumed(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIn("recorrect_never_default", manifest)
        self.assertIn("qc_levels.json", manifest["recorrect_never_default"])

    def test_assumptions_are_recorded_for_the_reader_to_verify(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        assumptions = manifest["assumptions_not_independently_verified"]
        self.assertIn("pkg_root", assumptions)
        self.assertIn("qc_module", assumptions)

    def test_rerun_with_identical_spec_is_a_harmless_noop(self):
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        proc2 = self._run()
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)

    def test_rerun_with_a_different_spec_refuses_to_clobber(self):
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        proc2 = self._run(["--wall-h", "5.0"])
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)

    def test_wall_h_and_cores_are_explicit_never_a_silent_default_of_1(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "U56_RB_scan_wave1.qsub")).read()
        self.assertIn("ncpus=64", text)
        self.assertNotIn("ncpus=1", text)


if __name__ == "__main__":
    unittest.main()
