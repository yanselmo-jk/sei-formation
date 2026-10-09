"""linear-hopping-frog plan, Track A item 2: the IRC checkpoint-restart diagnostic builder
(critic14's `Recorrect=Never`/StepSize hypothesis, 02_METHOD_SPEC.md 39.113(e)/39.114(2)).
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_u56_ra_irc_recorrect_probe.py")
REAL_XYZ = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
HAVE_BASH = shutil.which("bash") is not None


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class BuildU56RAIrcRecorrectProbeTest(unittest.TestCase):
    def setUp(self):
        self.job_dir = tempfile.mkdtemp(prefix="sei_srcjob_")
        self.out_dir = tempfile.mkdtemp(prefix="sei_recorrect_")
        shutil.copyfile(REAL_XYZ, os.path.join(self.job_dir, "ts.xyz"))
        # chk content is opaque to this tool (it only copies bytes) -- a placeholder is fine,
        # the REAL checkpoint's binary content is not something a test should fabricate meaning
        # for; what matters here is the copy-not-mutate behaviour and the deck this tool builds.
        with open(os.path.join(self.job_dir, "irc_forward.chk"), "wb") as fh:
            fh.write(b"\x00fake-checkpoint-bytes-not-a-real-gaussian-chk\x00")

    def tearDown(self):
        shutil.rmtree(self.job_dir, ignore_errors=True)
        shutil.rmtree(self.out_dir, ignore_errors=True)

    def _run(self, extra=()):
        return subprocess.run(
            [sys.executable, TOOL, "--job-dir", self.job_dir, "--out-dir", self.out_dir]
            + list(extra),
            capture_output=True, universal_newlines=True, timeout=60)

    def test_builds_restart_deck_with_no_coordinates(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

        gjf = os.path.join(self.out_dir, "irc_recorrect_probe.gjf")
        text = open(gjf).read()
        self.assertIn("geom=check", text)
        self.assertIn("guess=read", text)
        # [§39.124 addendum, critic16 27th review batch] maxpoints=30 is now ALWAYS written --
        # a ruled ceiling, previously missing entirely (an unbounded restart was neither the
        # ruled cap nor anything anyone sized).
        self.assertIn("irc=(restart,recorrect=never,maxpoints=30)", text)
        self.assertIn("scrf=(pcm,solvent=acetone,read)", text)
        self.assertIn("eps=18.5", text)
        self.assertIn("0 2", text)
        self.assertIn("Li", text)   # gen basis still covers the real element set
        # the whole point of geom=check: nothing but a blank line between the charge/mult
        # line and the gen basis block -- no coordinate rows in between.
        self.assertIn("0 2\n\nC     0\n", text)

        # checkpoint copied, never mutated in place
        dst_chk = os.path.join(self.out_dir, "irc_forward_recorrect_probe.chk")
        self.assertTrue(os.path.exists(dst_chk))
        with open(os.path.join(self.job_dir, "irc_forward.chk"), "rb") as fh:
            self.assertEqual(fh.read(), open(dst_chk, "rb").read())

        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIn("route_syntax_status", manifest)
        self.assertIn("NEEDS VERIFICATION", manifest["route_syntax_status"])
        self.assertTrue(manifest["recorrect_never"])
        self.assertIsNone(manifest["step_size"])

    def test_step_size_option_lands_in_the_route(self):
        proc = self._run(["--step-size", "5"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_recorrect_probe.gjf")).read()
        self.assertIn("stepsize=5", text)

    def test_missing_checkpoint_is_refused_not_guessed(self):
        os.remove(os.path.join(self.job_dir, "irc_forward.chk"))
        proc = self._run()
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("no checkpoint", proc.stderr)

    def test_total_cores_defaults_to_64_not_1(self):
        """🔴 [critic16, 27th review batch] `%nprocshared=1` on every deck nobody explicitly
        overrode -- at `maxpoints=30` that is 46-87 h wall against ADR-114's 48 h cap."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_recorrect_probe.gjf")).read()
        self.assertIn("%nprocshared=64\n", text)

    def test_total_cores_is_still_overridable(self):
        proc = self._run(["--total-cores", "32"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_recorrect_probe.gjf")).read()
        self.assertIn("%nprocshared=32\n", text)

    def test_maxpoints_is_written_for_the_reverse_direction_too(self):
        with open(os.path.join(self.job_dir, "irc_reverse.chk"), "wb") as fh:
            fh.write(b"\x00fake-checkpoint-bytes-not-a-real-gaussian-chk\x00")
        proc = self._run(["--direction", "reverse"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_recorrect_probe.gjf")).read()
        self.assertIn("maxpoints=30", text)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        # [critic16] a reverse build's remaining-point estimate must use reverse's OWN
        # already-computed count (6), not forward's (20) -- 30-6=24, not 30-20=10.
        self.assertIn("~24 remaining points", manifest["estimated_cost"])
        self.assertIn("minus 6 already computed", manifest["estimated_cost"])

    def test_forward_estimated_cost_uses_forwards_own_count(self):
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = json.load(open(os.path.join(self.out_dir, "manifest.json")))
        self.assertIn("~10 remaining points", manifest["estimated_cost"])
        self.assertIn("minus 20 already computed", manifest["estimated_cost"])

    def test_rerun_into_same_out_dir_refuses_to_clobber_existing_checkpoint(self):
        """docstring claims re-running is idempotent because the SOURCE is copied, never
        mutated -- but the DESTINATION checkpoint must not be silently overwritten, since a
        prior restart may have progressed it past a freshly-copied starting point."""
        proc1 = self._run()
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        dst_chk = os.path.join(self.out_dir, "irc_forward_recorrect_probe.chk")
        with open(dst_chk, "wb") as fh:
            fh.write(b"progressed-checkpoint-bytes-from-a-real-restart")
        before = open(dst_chk, "rb").read()

        proc2 = self._run()
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)
        self.assertEqual(open(dst_chk, "rb").read(), before)

    def test_a_failed_build_leaves_no_checkpoint_for_the_corrected_retry_to_trip_over(self):
        """🔴 [critic17, 28th review batch] The old copy-then-validate order left dst_chk behind
        even when a later step (unknown level here) failed -- the corrected retry was then
        refused with a FALSE "a prior restart may have progressed it" message about a copy that
        never actually ran against anything. A failed build must leave zero state."""
        proc1 = self._run(["--level", "99"])
        self.assertNotEqual(proc1.returncode, 0)
        dst_chk = os.path.join(self.out_dir, "irc_forward_recorrect_probe.chk")
        self.assertFalse(os.path.exists(dst_chk))

        proc2 = self._run()   # corrected retry, same out-dir
        self.assertEqual(proc2.returncode, 0, proc2.stdout + proc2.stderr)

    def test_building_the_other_direction_into_the_same_out_dir_is_refused_not_silent(self):
        """🔴 [critic17, 28th review batch] `irc_recorrect_probe.gjf`/`manifest.json` are NOT
        direction-specific names (unlike the .chk) -- building reverse after forward into the
        same out-dir must not silently replace forward's deck/manifest while leaving forward's
        checkpoint orphaned under a filename `submit_stage4.pbs` no longer matches."""
        proc1 = self._run(["--direction", "forward"])
        self.assertEqual(proc1.returncode, 0, proc1.stdout + proc1.stderr)
        gjf_path = os.path.join(self.out_dir, "irc_recorrect_probe.gjf")
        before = open(gjf_path).read()

        with open(os.path.join(self.job_dir, "irc_reverse.chk"), "wb") as fh:
            fh.write(b"\x00fake-checkpoint-bytes-not-a-real-gaussian-chk\x00")
        proc2 = self._run(["--direction", "reverse"])
        self.assertNotEqual(proc2.returncode, 0)
        self.assertIn("refusing to overwrite", proc2.stderr)
        self.assertEqual(open(gjf_path).read(), before)

    def test_no_direction_keyword_is_ever_written_into_the_irc_options(self):
        """🔴 [critic16] `restart` combined with an explicit direction keyword is UNSMOKED and
        may mean 'restart the OTHER direction' on some G16 builds -- must never be added."""
        proc = self._run()
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        text = open(os.path.join(self.out_dir, "irc_recorrect_probe.gjf")).read()
        irc_line = [ln for ln in text.splitlines() if "irc=(" in ln][0]
        self.assertNotIn("forward", irc_line)
        self.assertNotIn("reverse", irc_line)


if __name__ == "__main__":
    unittest.main()
