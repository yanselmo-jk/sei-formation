"""Stage 0: MTD-pilot comparator submission-wrapper builder (02_METHOD_SPEC.md
§39.40(d)-RESULT/§39.42(d)/§39.47(b)) -- build-only, mirrors
test_build_wave1_rb_submission.py's own conventions.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_wave1_stage0_submission.py")


class BuildWave1Stage0SubmissionTest(unittest.TestCase):
    def setUp(self):
        self.out_dir = tempfile.mkdtemp(prefix="sei_wave1_stage0_")

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
            os.path.join(self.out_dir, "stage0_mtd_comparator.qsub")))
        self.assertTrue(os.path.exists(
            os.path.join(self.out_dir, "stage0_mtd_comparator.cmd.sh")))
        self.assertTrue(os.path.exists(os.path.join(self.out_dir, "manifest.json")))

    def test_ruled_parameters_are_explicit_in_the_env(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "stage0_mtd_comparator.qsub")).read()
        self.assertIn('export SEI_STAGE0_N_SEEDS="12"', text)
        self.assertIn('export SEI_STAGE0_TEMP_K="1500"', text)
        self.assertIn('export SEI_STAGE0_TIME_PS="100.0"', text)
        self.assertIn('export SEI_STAGE0_REACTANT_XYZ="inputs/li_ec2_radical_reactant.xyz"',
                      text)
        self.assertIn('export SEI_STAGE0_MULTIPLICITY="2"', text)

    def test_cores_are_explicit_never_none_or_whole_node(self):
        """ADR-110: explicit cores_per_task on every xtb item."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "stage0_mtd_comparator.qsub")).read()
        self.assertIn("ncpus=12", text)

    def test_job_dir_env_points_at_the_remote_path_not_local_out_dir(self):
        proc = self._run(["--pkg-root", "/scratch/fake/pkg2"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "stage0_mtd_comparator.qsub")).read()
        self.assertIn('export SEI_JOB_DIR="/scratch/fake/pkg2/sei_pilot_work/jobs/'
                     'stage0_mtd_comparator"', text)
        self.assertNotIn(self.out_dir, text)

    def test_target_blindness_is_documented_in_manifest(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIn("target_blindness", manifest)
        self.assertIn("T1-T4", manifest["target_blindness"])

    def test_sealed_targets_file_is_computed_fresh_from_the_real_file_not_hand_edited(self):
        """🔴 [critic17, wave-1 review #3] The staged manifest once carried a hand-edited
        sealed_targets_file/target_blindness pair that a fresh run of this same builder could
        not reproduce -- source behind artifact, the inverse of the staleness pattern this
        project already fights. Pin it: a fresh run must independently compute the same sha256
        this test computes itself (never trust a value only the builder claims)."""
        import hashlib
        sealed_path = os.path.join(context.PKG_ROOT, "config",
                                   "stage0_sealed_targets_T1-T4.json")
        self.assertTrue(os.path.exists(sealed_path),
                        "sealed target file missing -- this test needs the real committed one")
        expected_sha256 = hashlib.sha256(open(sealed_path, "rb").read()).hexdigest()

        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIsNotNone(manifest["sealed_targets_file"])
        self.assertEqual(manifest["sealed_targets_file"]["sha256"], expected_sha256)
        self.assertTrue(manifest["sealed_targets_file"]["verified_against_expected"])
        self.assertIn("verified against the expected hash", manifest["target_blindness"])

    def test_qsub_carries_a_deployed_package_fingerprint_guard_that_actually_refuses(self):
        """🔴 [lead, wave-1 review items 3/5] A stale deployed package would silently ignore
        env vars this build relies on. Lands in the GENERATED QSUB (lead's explicit scoping),
        right after common.sh is sourced, reusing common.sh's own sei_pkg_fingerprint()
        (critic17's pre-build note: matches its workdir-aware extra_exclude, avoiding a
        renamed-workdir false alarm). Pin BOTH the producer (the guard block's shape/value in
        the generated qsub) AND the consumer's actual behaviour (critic17's own lesson: a
        string-only assertion looks identical whether or not the guard logic really works) --
        extract the real guard block and RUN it (sourcing the real common.sh first, since the
        guard calls its sei_pkg_fingerprint()) against a mismatched vs. a real SEI_PKG_ROOT."""
        import re
        import subprocess as sp

        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        qsub_text = open(os.path.join(self.out_dir, "stage0_mtd_comparator.qsub")).read()
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        expected_fp = manifest["deployed_package_fingerprint_check"]["expected"]
        self.assertIn('SEI_EXPECTED_PKG_FINGERPRINT="%s"' % expected_fp, qsub_text)

        m = re.search(r"SEI_EXPECTED_PKG_FINGERPRINT=.*?\nfi\n", qsub_text, re.S)
        self.assertIsNotNone(m, "could not extract the guard block from the real qsub")
        guard = m.group(0)
        source_common = '. "%s/payload/common.sh"\n' % context.PKG_ROOT

        mismatch = sp.run(
            ["bash", "-c", source_common + 'SEI_PKG_ROOT="/tmp"\n' + guard + "echo UNREACHABLE"],
            env=dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT),
            capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(mismatch.returncode, 9, mismatch.stdout + mismatch.stderr)
        self.assertIn("FATAL", mismatch.stderr + mismatch.stdout)
        self.assertNotIn("UNREACHABLE", mismatch.stdout)
        self.assertIn("false-alarm", mismatch.stdout + mismatch.stderr)

        real_pkg_root = context.PKG_ROOT
        match = sp.run(["bash", "-c", source_common + guard + "echo GUARD_PASSED"],
                       env=dict(os.environ, SEI_PKG_ROOT=real_pkg_root,
                               SEI_WORKDIR=real_pkg_root + "/sei_pilot_work"),
                       capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(match.returncode, 0, match.stdout + match.stderr)
        self.assertIn("GUARD_PASSED", match.stdout)

    def test_refuses_to_build_if_the_sealed_file_no_longer_matches_the_expected_hash(self):
        """🔴 [lead, wave-1 review item 6] An in-place edit of the sealed file (forbidden by its
        own header) must be DETECTED, not silently reported as still-sealed. Forces a mismatch
        via --sealed-targets-sha256 (an explicit input) rather than touching the real committed
        file -- the wrong expected value stands in for 'the real file drifted from what was
        sealed'."""
        proc = self._run(["--sealed-targets-sha256", "0" * 64])
        self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
        self.assertIn("REFUSING TO BUILD", proc.stderr)
        self.assertIn("sha256=", proc.stderr)
        self.assertFalse(os.path.exists(
            os.path.join(self.out_dir, "stage0_mtd_comparator.qsub")),
            "must refuse BEFORE writing any file, not after")

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


class Stage0MdScriptTest(unittest.TestCase):
    """End-to-end: the payload script itself, run for real against the vendored xtb binary
    (a tiny probe, not a real 100ps/12-seed run) -- the strongest check available that this
    isn't just a shell-syntax exercise."""

    XTB = os.path.join(context.PKG_ROOT, "vendor", "xtb", "bin", "xtb")

    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix="sei_stage0_run_")
        self.job_dir = os.path.join(self.workdir, "jobs", "stage0_test")
        os.makedirs(self.job_dir, exist_ok=True)

    def tearDown(self):
        shutil.rmtree(self.workdir, ignore_errors=True)

    @unittest.skipUnless(os.path.exists(XTB), "vendored xtb binary not present")
    def test_two_tiny_seeds_run_and_produce_a_target_blind_result(self):
        env = dict(os.environ)
        env.update({
            "SEI_PKG_ROOT": context.PKG_ROOT,
            "SEI_JOB_DIR": self.job_dir,
            "SEI_WORKDIR": self.workdir,
            "SEI_TOTAL_CORES": "2",
            "SEI_STAGE0_N_SEEDS": "2",
            "SEI_STAGE0_TIME_PS": "0.05",
        })
        proc = subprocess.run(
            ["bash", os.path.join(context.PKG_ROOT, "payload", "stage0_md.sh")],
            env=env, capture_output=True, universal_newlines=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        result_path = os.path.join(self.job_dir, "stage0_result.json")
        self.assertTrue(os.path.exists(result_path))
        result = json.load(open(result_path))
        self.assertEqual(result["n_seeds_requested"], 2)
        self.assertEqual(result["n_seeds_normal_termination"], 2)
        for seed in result["per_seed"]:
            self.assertTrue(seed["normal_termination"], seed)
            # target-blind: reactant's own fragments, no hardcoded T1-T4 atom indices anywhere
            self.assertIn("reactant_fragments", seed)
            self.assertIn("_target_blind_note", seed)


if __name__ == "__main__":
    unittest.main()
