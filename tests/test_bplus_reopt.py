"""`payload/BPLUS_REOPT.sh` -- §39.124 candidate D(i): tight re-optimisation of the EXISTING
B+ mid/last geometries. Real bash execution for the refusal paths (the same environment gate
every other payload script's real run hits here -- no g16/g09/orca/qchem/psi4 on PATH, see
`test_payload_shell.py`/`test_endpoint_prep.py`'s module docstrings); the PYVERDICT heredoc
(the new §39.124(c) wiring, `guards.bplus_agreement` + `guards.reactant_match` on the tightly
re-converged pair) extracted verbatim and run in isolation against synthetic-but-realistic G16
log text, same technique `test_endpoint_prep.py`'s heredoc-in-isolation tests use (ADR-042:
build fixtures from the real generator, never a hand-imagined snippet).
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot.criteria import xyzgraph

HAVE_BASH = shutil.which("bash") is not None
SCRIPT = os.path.join(context.PKG_ROOT, "payload", "BPLUS_REOPT.sh")

with open(SCRIPT) as _fh:
    _SCRIPT_TEXT = _fh.read()


def _extract_heredoc(delim):
    m = re.search(r"<<'%s'\n(.*?)\n%s\n" % (re.escape(delim), delim), _SCRIPT_TEXT, re.S)
    assert m, "no <<'%s' heredoc found in %s" % (delim, SCRIPT)
    return m.group(1)


def _reactant_atoms():
    path = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
    with open(path, errors="replace") as fh:
        return xyzgraph.read_xyz_frames(fh.read())[0][1]


def _g16_log(atoms, energy_hartree, converged=True, freqs_cm1=(300.0, 450.0)):
    """A REALISTIC G16 opt+freq log (§39.124's own D(i) route, `endpoint_opt_freq`), built from
    the SAME atomic-number encoding `criteria.g16.Z_TO_SYMBOL` decodes -- not a hand-imagined
    format, the actual one `g16.last_geometry`/`g16.parse_frequencies` parse elsewhere."""
    z_of = {"H": 1, "Li": 3, "C": 6, "N": 7, "O": 8}
    lines = [" Entering Gaussian System, Link 0=g16",
             " Standard orientation:",
             " ---------------------------------------------------------------------",
             " Center     Atomic      Atomic             Coordinates (Angstroms)",
             " Number     Number       Type             X           Y           Z",
             " ---------------------------------------------------------------------"]
    for idx, (sym, x, y, z) in enumerate(atoms, start=1):
        lines.append("    %2d          %d           0     %11.6f %11.6f %11.6f"
                     % (idx, z_of[sym], x, y, z))
    lines.append(" ---------------------------------------------------------------------")
    lines.append(" SCF Done:  E(RwB97XD) =  %.10f     A.U. after   9 cycles" % energy_hartree)
    lines.append("         Item               Value     Threshold  Converged?")
    lines.append(" Maximum Force            0.000001     0.000015     YES")
    if converged:
        lines.append(" Optimization completed.")
        lines.append("    -- Stationary point found.")
    lines.append(" Harmonic frequencies (cm**-1), IR intensities (KM/Mole)")
    lines.append(" Frequencies --  " + "  ".join("%.4f" % f for f in freqs_cm1))
    lines.append(" Thermochemistry")
    lines.append(" Zero-point correction=                    0.100000")
    lines.append(" Sum of electronic and thermal Free Energies=  %.6f" % (energy_hartree + 0.05))
    lines.append(" Job cpu time:       0 days  0 hours  5 minutes  0.0 seconds.")
    lines.append(" Normal termination of Gaussian 16 at Sun Aug 22 12:00:00 2026.")
    return "\n".join(lines) + "\n"


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _BplusReoptRun(unittest.TestCase):
    EXTRA_ENV = {}

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_bplus_reopt_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.job_dir = os.path.join(self.d, "jobs", "bplus_reopt")
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))
        self.proc = self._run()

    def _run(self):
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": "bplus_reopt",
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8"})
        env.update(self.EXTRA_ENV)
        return subprocess.run(["bash", SCRIPT], env=env, capture_output=True,
                              text=True, timeout=120)

    def terminal_status(self):
        with open(os.path.join(self.job_dir, "terminal_status.json")) as fh:
            return json.load(fh)


class TestMissingRequiredEnvIsRefused(_BplusReoptRun):
    """🔴 No default is invented for any of the three required geometry paths -- an unset
    required var is a refusal (exit 2), not a guess. This is the REAL current-environment
    behaviour (no QC engine needed to reach it -- checked before `sei_qc_detect`)."""

    def test_exits_input_error(self):
        self.assertEqual(2, self.proc.returncode, self.proc.stdout + self.proc.stderr)
        self.assertIn("SEI_BPLUS_MID_XYZ", self.proc.stdout)

    def test_terminal_status_says_which_var(self):
        self.assertEqual("input_error", self.terminal_status()["status"])


class TestMissingGeometryFileIsRefusedDistinctly(_BplusReoptRun):
    """A declared-but-nonexistent path is a DIFFERENT refusal than an unset var (same
    `input_missing` vs `input_error` split `endpoint_prep.sh` already makes)."""

    def setUp(self):
        self.tmp_xyz = None
        super().setUp()

    def _run(self):
        self.tmp_xyz = os.path.join(tempfile.mkdtemp(prefix="sei_bplus_geom_"), "gone.xyz")
        self.EXTRA_ENV = {"SEI_BPLUS_MID_XYZ": self.tmp_xyz,
                          "SEI_BPLUS_LAST_XYZ": self.tmp_xyz,
                          "SEI_BPLUS_REACTANT_XYZ": self.tmp_xyz}
        return super()._run()

    def test_exits_input_missing(self):
        self.assertEqual(2, self.proc.returncode, self.proc.stdout + self.proc.stderr)
        self.assertEqual("input_missing", self.terminal_status()["status"])


class TestNoQcEngineBlocksAfterInputsResolve(_BplusReoptRun):
    """Once the three real geometries resolve, the next real gate hit in THIS environment is
    the one every other payload script's real run hits (no QC engine on PATH) -- exit 3."""

    def setUp(self):
        self.d0 = tempfile.mkdtemp(prefix="sei_bplus_inputs_")
        self.addCleanup(shutil.rmtree, self.d0, True)
        reactant = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
        self.mid = os.path.join(self.d0, "mid.xyz")
        self.last = os.path.join(self.d0, "last.xyz")
        shutil.copy(reactant, self.mid)
        shutil.copy(reactant, self.last)
        self.EXTRA_ENV = {"SEI_BPLUS_MID_XYZ": self.mid, "SEI_BPLUS_LAST_XYZ": self.last,
                          "SEI_BPLUS_REACTANT_XYZ": reactant}
        super().setUp()

    def test_exits_skipped(self):
        self.assertEqual(3, self.proc.returncode, self.proc.stdout + self.proc.stderr)
        self.assertEqual("skipped", self.terminal_status()["status"])


class TestNotWiredIntoThePlan(unittest.TestCase):
    """§1f/§R39.81: priced, not released. This script must not be reachable from `plan.py`'s
    item list -- wiring it is a scope decision this file explicitly declines to make."""

    def test_plan_py_does_not_reference_it(self):
        plan_py = os.path.join(context.PKG_ROOT, "sei_pilot", "plan.py")
        with open(plan_py) as fh:
            self.assertNotIn("BPLUS_REOPT", fh.read())

    def test_the_script_says_so_out_loud(self):
        self.assertIn("STAGING ONLY, NOT WIRED INTO plan.py", _SCRIPT_TEXT)


class TestPyverdictHeredocInIsolation(unittest.TestCase):
    """The new logic: tight-converged mid/last through the SAME `guards.bplus_agreement`
    comparator B+ itself uses, PLUS `guards.reactant_match` (§39.124(c)) against the certified
    reactant -- run here against realistic synthetic G16 logs, unreachable end-to-end in this
    environment (no QC engine)."""

    #: Same pair convention as `test_bplus.py::TestReactantMatch` -- O(1)-C(2) in
    #: `li_ec_radical_reactant.xyz`.
    BREAK_PAIR = [(1, 2, "break:O-C")]

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_bplus_reopt_verdict_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.reactant_atoms = _reactant_atoms()
        self.reactant_xyz = os.path.join(self.d, "reactant_certified.xyz")
        with open(self.reactant_xyz, "w") as fh:
            fh.write("%d\nreactant\n" % len(self.reactant_atoms))
            fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in self.reactant_atoms))
        self.mapping_json = os.path.join(self.d, "u56_R-A_mapping.json")
        json.dump({"mapping": {"break": [{"selected": [1, 2], "role": "O-C"}]}},
                  open(self.mapping_json, "w"))
        self.snippet = _extract_heredoc("PYVERDICT")

    def _run(self, mapping_json=None):
        args = ["python3", "-c", self.snippet, self.d, self.reactant_xyz,
               mapping_json or "", "R-A_reverse"]
        return subprocess.run(args, env=dict(os.environ, PYTHONPATH=context.PKG_ROOT,
                                             SEI_PKG_ROOT=context.PKG_ROOT),
                              capture_output=True, text=True, timeout=30)

    def _write_logs(self, mid_atoms, last_atoms, e_mid=-350.0, e_last=-350.0 + 1e-8):
        with open(os.path.join(self.d, "bplus_reopt_mid.log"), "w") as fh:
            fh.write(_g16_log(mid_atoms, e_mid))
        with open(os.path.join(self.d, "bplus_reopt_last.log"), "w") as fh:
            fh.write(_g16_log(last_atoms, e_last))

    def test_it_calls_the_real_guards_not_a_reimplementation(self):
        self.assertIn("guards.bplus_agreement(geom_mid, geom_last, e_mid, e_last)", self.snippet)
        self.assertIn("guards.reactant_match(geom_mid, atoms_r, pairs)", self.snippet)
        self.assertIn("guards.reactant_match(geom_last, atoms_r, pairs)", self.snippet)

    def test_the_gap_surviving_tight_convergence_is_recorded_as_agreement_plus_the_delta(self):
        """§39.124 finding (b) [RETRACTED, see 02_METHOD_SPEC.md's correction block -- D(i)
        itself is CANCELLED] -- kept as a plumbing check only: two DIFFERENT geometries still
        route through `bplus_agreement`/`reactant_match` correctly. `mid` is stretched well past
        the now-RULED 0.05 A distance tolerance (still under Layer C's own much looser
        bond-forming cutoff, so the graph is unchanged) -- distance clause genuinely FAILS, so
        `match` is a real `False`, not `None`. `last` has no energy supplied by this payload's
        own call (`guards.reactant_match(geom_a, atoms_r, pairs)`, positional only) -- energy
        clause unmeasured -> `match` stays `None` even with a perfect distance."""
        mid = list(self.reactant_atoms)
        # stretch O(1) away from C(2), same construction as test_bplus.py's own case -- still
        # well under BOND_TOLERANCE * (r_O + r_C), but past the RULED 0.05 A tolerance.
        mid[1] = (mid[1][0], mid[1][1], mid[1][2] + 0.2, mid[1][3])
        self._write_logs(mid, self.reactant_atoms)
        res = self._run(self.mapping_json)
        self.assertEqual(0, res.returncode, res.stdout + res.stderr)
        verdict = json.load(open(os.path.join(self.d, "bplus_reopt_verdict.json")))
        self.assertTrue(verdict["tight_bplus_agreement"]["covalent_graphs_match"])
        rm = verdict["tight_reactant_match"]
        self.assertFalse(rm["mid"]["match"], "distance clause genuinely fails past 0.05 A")
        self.assertIsNone(rm["last"]["match"], "no energy supplied -> None, not a guessed True")
        self.assertGreater(rm["mid"]["break_bonds"][0]["delta_ang"], 0.15)
        self.assertAlmostEqual(0.0, rm["last"]["break_bonds"][0]["delta_ang"], places=6)

    def test_a_genuine_bifurcation_is_an_unambiguous_reactant_mismatch(self):
        mid = list(self.reactant_atoms)
        mid[1] = (mid[1][0], mid[1][1] - 2.0, mid[1][2], mid[1][3])
        self._write_logs(mid, self.reactant_atoms)
        res = self._run(self.mapping_json)
        self.assertEqual(0, res.returncode, res.stdout + res.stderr)
        verdict = json.load(open(os.path.join(self.d, "bplus_reopt_verdict.json")))
        self.assertFalse(verdict["tight_reactant_match"]["mid"]["match"])

    def test_without_a_mapping_the_gap_is_recorded_not_silently_skipped(self):
        self._write_logs(self.reactant_atoms, self.reactant_atoms)
        res = self._run(mapping_json="")
        self.assertEqual(0, res.returncode, res.stdout + res.stderr)
        verdict = json.load(open(os.path.join(self.d, "bplus_reopt_verdict.json")))
        rm = verdict["tight_reactant_match"]
        self.assertIsNone(rm["mid"])
        self.assertIn("not computed", rm["_status"])


if __name__ == "__main__":
    unittest.main()
