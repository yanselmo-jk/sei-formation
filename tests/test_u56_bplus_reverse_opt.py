"""The two B+ terminal-optimization jobs closing U-56a condition 7's reverse branch
(proposer13's §39.131 ruling, 02_METHOD_SPEC.md / 05_STATE.md §1f "CANDIDATE B RETURNED").
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_u56_bplus_reverse_opt.py")
REAL_LOG = os.path.join(context.REPO_ROOT, "pilot_tests",
                        "candidate_b_reverse_stepsize_2026-08-25", "irc_stepsize_probe.log")
HAVE_BASH = shutil.which("bash") is not None


def _orient_block(atoms):
    """atoms: [(atomic_number, x, y, z), ...]. Minimal Standard orientation block."""
    lines = [" Standard orientation:", " ---", " Center  Atomic  ...", " ---"]
    for i, (z, x, y, zz) in enumerate(atoms, 1):
        lines.append("    %d    %d    0    %.6f    %.6f    %.6f" % (i, z, x, y, zz))
    lines.append(" ---")
    return "\n".join(lines)


def _fake_irc_log(arcs):
    """A minimal synthetic IRC log: one Standard-orientation block + one
    NET REACTION COORDINATE line per requested arc value. Real enough for
    parse_irc_path_frames/bplus_sample_points, nothing else."""
    atoms = [(6, 0.0, 0.0, 0.0), (8, 1.0, 0.0, 0.0)]
    parts = []
    for arc in arcs:
        parts.append(_orient_block(atoms))
        parts.append(" NET REACTION COORDINATE UP TO THIS POINT = %.5f" % arc)
    return "\n".join(parts)


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class BuildU56BplusReverseOptTest(unittest.TestCase):
    def setUp(self):
        self.out_dir = tempfile.mkdtemp(prefix="sei_bplus_")

    def tearDown(self):
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run(self, irc_log, extra=()):
        return subprocess.run(
            [sys.executable, TOOL, "--irc-log", irc_log, "--out-dir", self.out_dir]
            + list(extra),
            capture_output=True, universal_newlines=True, timeout=60)

    def test_missing_log_is_refused_not_guessed(self):
        proc = self._run(os.path.join(self.out_dir, "does_not_exist.log"))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no ", proc.stderr)

    def test_mismatched_ruled_points_refuses_loudly(self):
        """The core safety net: a log whose own bplus_sample_points() pick disagrees with
        proposer13's ruled arc values must be REFUSED, not silently built against."""
        fake_log = os.path.join(self.out_dir, "fake.log")
        # 5 points, arcs nowhere near the ruled 2.38953/4.77975 -- guaranteed mismatch.
        with open(fake_log, "w") as fh:
            fh.write(_fake_irc_log([0.1, 0.2, 0.3, 0.4, 0.5]))
        proc = self._run(fake_log)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("cross-check FAILED", proc.stderr)
        self.assertFalse(os.path.exists(os.path.join(self.out_dir, "bplus_reverse_mid.gjf")))

    def test_too_few_points_is_refused(self):
        fake_log = os.path.join(self.out_dir, "fake_short.log")
        with open(fake_log, "w") as fh:
            fh.write(_fake_irc_log([0.1]))
        proc = self._run(fake_log)
        self.assertNotEqual(proc.returncode, 0)

    @unittest.skipUnless(os.path.exists(REAL_LOG), "returned Candidate B log not present "
                         "(running without the pilot_tests/ returned-results tree)")
    def test_the_real_returned_log_matches_proposer13s_ruled_points_exactly(self):
        """🔴🔴 The strongest regression available: the ACTUAL returned Candidate B log, not a
        fixture. proposer13 independently ran guards.bplus_sample_points() against this same
        file and reported Point 35 (arc 2.38953) / Point 70 (arc 4.77975) -- this asserts the
        tool's own cross-check would pass, not just that it CAN refuse on a mismatch."""
        from sei_pilot import guards
        from sei_pilot.criteria import g16
        with open(REAL_LOG, errors="replace") as fh:
            text = fh.read()
        frames = g16.parse_irc_path_frames(text)
        self.assertEqual(70, len(frames))
        arcs = [f["arc"] for f in frames]
        mid_idx, last_idx = guards.bplus_sample_points(arcs)
        self.assertEqual(34, mid_idx)   # Point 35, 0-based
        self.assertEqual(69, last_idx)  # Point 70, 0-based
        self.assertAlmostEqual(2.38953, arcs[mid_idx], places=5)
        self.assertAlmostEqual(4.77975, arcs[last_idx], places=5)

    @unittest.skipUnless(os.path.exists(REAL_LOG), "returned Candidate B log not present "
                         "(running without the pilot_tests/ returned-results tree)")
    def test_builds_both_decks_from_the_real_log(self):
        proc = self._run(REAL_LOG, ["--total-cores", "64"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        for tag, point_number, arc in (("mid", 35, 2.38953), ("last", 70, 4.77975)):
            gjf = os.path.join(self.out_dir, "bplus_reverse_%s.gjf" % tag)
            text = open(gjf).read()
            self.assertIn("opt=(loose,maxcycles=100)", text)
            self.assertIn("scrf=(pcm,solvent=acetone,read)", text)
            self.assertIn("0 2\n", text)
            self.assertIn("%nprocshared=64\n", text)
            # from-scratch coordinate block, not a restart
            self.assertNotIn("geom=check", text)

            manifest = json.load(open(os.path.join(self.out_dir, "manifest_%s.json" % tag)))
            self.assertEqual(manifest["point_number"], point_number)
            self.assertAlmostEqual(manifest["arc"], arc, places=5)
            self.assertIn("post_run_computation", manifest)
            self.assertIn("U56.sh", manifest["post_run_computation"])
            self.assertIn("eulerpc_dvv_status", manifest)
            self.assertIn("MOOT", manifest["eulerpc_dvv_status"])

    @unittest.skipUnless(os.path.exists(REAL_LOG), "returned Candidate B log not present")
    def test_rerun_into_same_out_dir_refuses_to_clobber(self):
        proc1 = self._run(REAL_LOG)
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        gjf_path = os.path.join(self.out_dir, "bplus_reverse_mid.gjf")
        before = open(gjf_path).read()

        proc2 = self._run(REAL_LOG)
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)
        self.assertEqual(open(gjf_path).read(), before)


if __name__ == "__main__":
    unittest.main()
