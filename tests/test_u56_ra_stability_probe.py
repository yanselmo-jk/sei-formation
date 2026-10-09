"""linear-hopping-frog plan, Track A item 2: the `stable=opt` diagnostic deck builder.

Targets fixed by 02_METHOD_SPEC.md 39.114(2)/39.115 -- point 5 (arc~1.71), point 20 (arc~6.83,
last point before the crash), and endpoint_prep_rc_reactant's certified geometry (21 atoms,
highest MO-coefficient magnitude in the returned tree). Runs the real tool end to end against
REAL fixtures (verbatim excerpts of the actual returned logs, not synthetic ramps) and checks
the produced .gjf, not a report about it.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

TOOL = os.path.join(context.PKG_ROOT, "tools", "build_u56_ra_stability_probe.py")
FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
HAVE_BASH = shutil.which("bash") is not None


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class BuildU56RAStabilityProbeTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_stab_probe_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, extra):
        return subprocess.run([sys.executable, TOOL, "--out-dir", self.d] + list(extra),
                              capture_output=True, universal_newlines=True, timeout=60)

    def _assert_common_deck_shape(self, n_atoms):
        gjf = os.path.join(self.d, "stability_probe.gjf")
        self.assertTrue(os.path.exists(gjf))
        text = open(gjf).read()
        self.assertIn("stable=opt", text)
        # [critic14] nosymm here is a DIFFERENT reason from the C-9-perturbation family
        # (`_nosymm_required_job_types`): without it G16 can restrict the stability search to
        # symmetry-adapted rotations and miss a symmetry-lowering instability -- the false
        # negative direction proposer10's falsifiability statement depends on being absent.
        self.assertIn("nosymm", text)
        self.assertIn("wB97XD/gen", text)
        self.assertIn("scrf=(pcm,solvent=acetone,read)", text)
        self.assertIn("eps=18.5", text)
        self.assertIn("0 2", text)          # charge 0, doublet -- every U56 species
        self.assertIn("Li", text)           # gen basis block covers the real element set
        # no opt/freq keyword snuck in -- this must stay a cheap single point
        self.assertNotIn(" opt", text.lower())
        self.assertNotIn(" freq", text.lower())
        xyz = open(os.path.join(self.d, "probe_point.xyz")).read()
        self.assertEqual(int(xyz.splitlines()[0]), n_atoms)
        manifest = json.load(open(os.path.join(self.d, "manifest.json")))
        self.assertIn("provenance", manifest)
        self.assertIsNotNone(manifest["provenance"]["package_fingerprint"])
        self.assertIn("falsifiability", manifest)
        return manifest

    def test_point5_target_arc_1_71(self):
        """§39.114(2) target 1: where the MO coefficient first stabilises after its rise."""
        proc = self._run(["--irc-log",
                          os.path.join(FIXTURES, "g16_irc_forward_point5_u56ra.log"),
                          "--point-index", "0"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = self._assert_common_deck_shape(11)
        self.assertAlmostEqual(manifest["source"]["irc_arc_length"], 1.70908, places=4)
        self.assertAlmostEqual(
            manifest["source"]["nearby_mo_coefficient_warning"]["value"], 33.376559, places=3)

    def test_point20_target_arc_6_83_last_point_before_crash(self):
        """§39.114(2) target 2: the LAST point actually computed before the corrector death."""
        proc = self._run(["--irc-log",
                          os.path.join(FIXTURES, "g16_irc_forward_point20_u56ra.log"),
                          "--point-index", "0"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = self._assert_common_deck_shape(11)
        self.assertAlmostEqual(manifest["source"]["irc_arc_length"], 6.83462, places=4)
        self.assertGreater(manifest["source"]["nearby_mo_coefficient_warning"]["value"], 38)

    def test_rc_reactant_target_certified_21_atom(self):
        """§39.115: THIRD target, the already-certified 21-atom geometry -- highest MO
        coefficient magnitude in the whole returned tree (~71-79), on a job that PASSED."""
        proc = self._run(["--geom-log",
                          os.path.join(FIXTURES, "g16_endpoint_tight_rc_reactant.log")])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        manifest = self._assert_common_deck_shape(21)
        warnings = manifest["source"]["mo_coefficient_warnings_first_last"]
        self.assertGreater(warnings[0]["value"], 65)
        self.assertGreater(warnings[-1]["value"], 65)

    def test_out_of_range_point_index_is_refused_not_guessed(self):
        proc = self._run(["--irc-log",
                          os.path.join(FIXTURES, "g16_irc_forward_point5_u56ra.log"),
                          "--point-index", "99"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("out of range", proc.stderr)

    def test_point_index_required_with_irc_log(self):
        proc = self._run(["--irc-log",
                          os.path.join(FIXTURES, "g16_irc_forward_point5_u56ra.log")])
        self.assertNotEqual(proc.returncode, 0)

    def test_irc_log_and_geom_log_are_mutually_exclusive(self):
        proc = self._run(["--irc-log",
                          os.path.join(FIXTURES, "g16_irc_forward_point5_u56ra.log"),
                          "--point-index", "0",
                          "--geom-log",
                          os.path.join(FIXTURES, "g16_endpoint_tight_rc_reactant.log")])
        self.assertNotEqual(proc.returncode, 0)


if __name__ == "__main__":
    unittest.main()
