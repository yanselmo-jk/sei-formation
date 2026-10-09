"""The three-row availability check -- binary · data_library · launch_smoke.

🔴 THE INCIDENT THIS ENCODES, twice over.

  1. `software.g16` came back EMPTY and all nine RT-1 items were planned anyway (`n_skipped: 0`),
     because availability had been inferred from a gaussian-ish string in a `module avail`
     listing. Rule 20: the check that ran established "a name is in a list"; the property claimed
     was "G16 will run inside the job".
  2. `vasp_std 6.4.3 present at /home01/q656a01/local/bin/vasp_std` sat inside a 05_STATE block
     headed "settled [MEASURED] -- do not re-run these", HOURS after ADR-073/074 established that
     PRESENT != CAN COMPUTE. Rule 28: finality words in a heading suppress further reading, which
     is why stale claims survive longest there.

  And the row that was written and never implemented: CP2K's `$CP2K_DATA_DIR` (U-46) exists only
  as a COMMENT in `sysprobe.py`, and was never carried to VASP -- where the equivalent is the
  POTCAR library and nobody had looked at all.

🔴 The single most important assertion in this file is
   `test_binary_and_data_alone_are_never_ready`. If it ever goes green with `ready is True`, the
   check has been reduced back to the thing that failed.
"""

import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import readiness

ENV_PATHS = os.path.join(context.PKG_ROOT, "config", "env_paths.json")

GOOD_SMOKE = {"ran_on_compute_node": True, "parsed_result": True}


class _TempRoot(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_ready_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _exe(self, name):
        p = os.path.join(self.d, name)
        with open(p, "w") as fh:
            fh.write("#!/bin/sh\nexit 0\n")
        os.chmod(p, 0o755)
        return p


class TestRequirementTableIsTheSingleSource(unittest.TestCase):
    def test_every_allowed_engine_has_all_three_rows_declared(self):
        """🔴 EVERY external code, not just the one we remembered."""
        with open(ENV_PATHS) as fh:
            cfg = json.load(fh)
        req = cfg["engine_requirements"]
        for engine in ("g16", "vasp_std", "xtb", "cp2k", "lammps"):
            self.assertIn(engine, req, "%s has no three-row requirement declared" % engine)
            self.assertIn("binary_names", req[engine])
            self.assertIn("data_library", req[engine],
                          "%s has no data-library row -- that is the row we wrote for CP2K as a "
                          "comment and never carried anywhere" % engine)
            self.assertIn("launch_smoke", req[engine])

    def test_vasp_data_row_names_the_potcar_library_and_the_variant(self):
        """🔴 'a POTCAR directory exists' is not the property. Li_sv is."""
        req = readiness.requirements()["vasp_std"]["data_library"]
        self.assertEqual(req["kind"], "potcar_dir")
        self.assertIn("Li_sv", req["required_elements"])
        self.assertIn("[MEASURED]", req["path_source"])

    def test_the_table_is_loaded_from_config_not_hardcoded(self):
        self.assertTrue(readiness.requirements())
        with open(ENV_PATHS) as fh:
            self.assertIn("engine_requirements", json.load(fh))


class TestReadyRequiresAllThreeRows(_TempRoot):
    def test_binary_and_data_alone_are_never_ready(self):
        """🔴🔴 THE REGRESSION. `vasp_std present` must not read as usable."""
        potcar = os.path.join(self.d, "PBE_64")
        os.makedirs(potcar)
        for el in ("Li_sv", "C", "H", "O", "P", "F"):
            os.makedirs(os.path.join(potcar, el))
        res = readiness.evaluate(
            "vasp_std", binary_path=self._exe("vasp_std"), smoke=None,
            cfg={"engine_requirements": {"vasp_std": {"data_library": {
                "kind": "potcar_dir", "path": potcar,
                "required_elements": ["Li_sv", "C", "H", "O", "P", "F"]}}}})
        self.assertIs(res["rows"][0]["ok"], True)
        self.assertIs(res["rows"][1]["ok"], True)
        self.assertIsNone(res["ready"],
                          "binary present + POTCARs present was reported as READY. That is "
                          "exactly the inference ADR-073/074 overturned.")
        self.assertEqual(res["rows_unchecked"], ["launch_smoke"])

    def test_unknown_readiness_says_so_in_warnings(self):
        """Rule 13 -- a judgement-triggering value reaches the artefact AND warnings[]."""
        potcar = os.path.join(self.d, "PBE_64")
        os.makedirs(potcar)
        os.makedirs(os.path.join(potcar, "Li_sv"))
        res = readiness.evaluate(
            "vasp_std", binary_path=self._exe("vasp_std"),
            cfg={"engine_requirements": {"vasp_std": {"data_library": {
                "kind": "potcar_dir", "path": potcar,
                "required_elements": ["Li_sv"]}}}})
        self.assertIsNone(res["ready"])
        joined = " ".join(res["warnings"])
        self.assertIn("readiness_unknown", joined)
        self.assertIn("PRESENT != CAN COMPUTE", joined)

    def test_all_three_rows_positive_is_ready(self):
        """Positive control: the check must be passable."""
        data = os.path.join(self.d, "share")
        os.makedirs(data)
        open(os.path.join(data, "param_gfn2-xtb.txt"), "w").close()
        res = readiness.evaluate(
            "xtb", binary_path=self._exe("xtb"), smoke=GOOD_SMOKE,
            cfg={"engine_requirements": {"xtb": {"data_library": {
                "kind": "param_dir", "path": data,
                "required_files": ["param_gfn2-xtb.txt"]}}}})
        self.assertIs(res["ready"], True)
        self.assertEqual(res["warnings"], [])

    def test_a_missing_data_library_makes_evaluate_false(self):
        """🔴 ADDED AFTER A REVERT EXPERIMENT CAME BACK GREEN.

        Replacing `check_data_library(...)` inside `evaluate()` with a hardcoded
        `row(ROW_DATA, True)` broke NOTHING in this file: every data-library test called the
        helper directly, and the only `evaluate()` test that touched row 2 asserted it was True --
        which the stub also satisfied. The row was wired in and untested, which is how the CP2K
        data row spent a whole project as a comment. This is the assembly-line test (ADR-041).
        """
        res = readiness.evaluate(
            "vasp_std", binary_path=self._exe("vasp_std"), smoke=GOOD_SMOKE,
            cfg={"engine_requirements": {"vasp_std": {"data_library": {
                "kind": "potcar_dir", "path": os.path.join(self.d, "no_such_potcar_dir"),
                "required_elements": ["Li_sv"]}}}})
        self.assertIs(res["ready"], False,
                      "the binary ran and the POTCAR library is absent, and evaluate() called it "
                      "ready -- row 2 is not actually wired into the verdict")
        self.assertEqual(res["rows_negative"], ["data_library"])
        self.assertIsNotNone(res["rows"][1]["evidence"],
                             "row 2 reported no evidence of having looked anywhere")

    def test_a_present_but_incomplete_library_makes_evaluate_false(self):
        """The variant case, through the entry point: directory there, Li_sv missing."""
        potcar = os.path.join(self.d, "PBE_64")
        os.makedirs(os.path.join(potcar, "C"))
        res = readiness.evaluate(
            "vasp_std", binary_path=self._exe("vasp_std"), smoke=GOOD_SMOKE,
            cfg={"engine_requirements": {"vasp_std": {"data_library": {
                "kind": "potcar_dir", "path": potcar,
                "required_elements": ["Li_sv", "C"]}}}})
        self.assertIs(res["ready"], False)
        self.assertEqual(res["rows"][1]["evidence"]["missing"], ["Li_sv"])

    def test_a_negative_row_makes_it_false_not_unknown(self):
        res = readiness.evaluate("xtb", binary_path=os.path.join(self.d, "absent"),
                                 smoke=GOOD_SMOKE)
        self.assertIs(res["ready"], False)
        self.assertIn("binary", res["rows_negative"])


class TestDataLibraryRow(_TempRoot):
    def _spec(self, path, **kw):
        d = {"kind": "potcar_dir", "path": path}
        d.update(kw)
        return d

    def test_directory_present_but_a_required_element_missing_is_false(self):
        """🔴 The failure a directory-existence test cannot see."""
        potcar = os.path.join(self.d, "PBE_64")
        os.makedirs(potcar)
        for el in ("C", "H", "O"):
            os.makedirs(os.path.join(potcar, el))
        r = readiness.check_data_library(
            self._spec(potcar, required_elements=["Li_sv", "C", "H", "O", "P", "F"]))
        self.assertIs(r["ok"], False)
        self.assertEqual(r["evidence"]["missing"], ["Li_sv", "P", "F"])

    def test_absent_directory_is_false_not_none(self):
        r = readiness.check_data_library(self._spec(os.path.join(self.d, "nope")))
        self.assertIs(r["ok"], False)

    def test_no_declared_requirement_is_none_not_true(self):
        """🔴 'no requirement declared' must not read as 'requirement satisfied'."""
        self.assertIsNone(readiness.check_data_library(None)["ok"])
        self.assertIsNone(readiness.check_data_library({"kind": "env_dir"})["ok"])

    def test_env_var_resolution_is_tried_and_recorded(self):
        data = os.path.join(self.d, "cp2kdata")
        os.makedirs(data)
        for f in ("BASIS_MOLOPT", "GTH_POTENTIALS"):
            open(os.path.join(data, f), "w").close()
        r = readiness.check_data_library(
            {"kind": "env_dir", "env_vars": ["CP2K_DATA_DIR"],
             "required_files": ["BASIS_MOLOPT", "GTH_POTENTIALS"]},
            env={"CP2K_DATA_DIR": data})
        self.assertIs(r["ok"], True)
        self.assertEqual(r["evidence"]["resolved"], data)

    def test_our_own_shipped_basis_decks_are_a_separate_half(self):
        """G16's data row is TWO things: the site's $GAUSS_EXEDIR and OUR gen basis files."""
        site = os.path.join(self.d, "exedir")
        os.makedirs(site)
        r = readiness.check_data_library(
            {"kind": "env_dir", "env_vars": ["GAUSS_EXEDIR"],
             "also_required_files": ["inputs/basis/def2-SVPD.gbs"]},
            root=self.d, env={"GAUSS_EXEDIR": site})
        self.assertIs(r["ok"], False)
        self.assertEqual(r["evidence"]["package_files_missing"],
                         ["inputs/basis/def2-SVPD.gbs"])

    def test_the_real_package_ships_the_gen_basis_decks(self):
        r = readiness.check_data_library(
            {"kind": "env_dir", "env_vars": ["GAUSS_EXEDIR"],
             "also_required_files": ["inputs/basis/def2-SVPD.gbs",
                                     "inputs/basis/def2-TZVPPD.gbs"]},
            root=context.PKG_ROOT, env={"GAUSS_EXEDIR": self.d})
        self.assertEqual(r["evidence"]["package_files_missing"], [])


class TestLaunchSmokeRow(unittest.TestCase):
    def test_not_run_is_none(self):
        self.assertIsNone(readiness.check_launch_smoke(None)["ok"])

    def test_a_login_node_smoke_does_not_count(self):
        """ADR-041: the login node is different hardware with a different module environment.

        `24` was once read as this cluster's core count because it was measured on login03.
        """
        r = readiness.check_launch_smoke({"ran_on_compute_node": False, "parsed_result": True})
        self.assertIs(r["ok"], False)
        self.assertIn("login-node", r["note"])

    def test_ran_but_produced_nothing_parseable_is_false(self):
        r = readiness.check_launch_smoke({"ran_on_compute_node": True, "parsed_result": False})
        self.assertIs(r["ok"], False)


class TestRowsStateTheirOwnSemantics(unittest.TestCase):
    """Rule 20 -- a check must state the PROPERTY it establishes, not the name it ran on."""

    def test_every_row_declares_what_it_does_not_establish(self):
        for name in readiness.ROWS:
            sem = readiness.ROW_SEMANTICS[name]
            self.assertTrue(sem["establishes"])
            self.assertTrue(sem["does_not_establish"])

    def test_the_binary_row_says_it_is_a_proxy(self):
        self.assertIn("PROXY", readiness.ROW_SEMANTICS[readiness.ROW_BINARY]
                      ["does_not_establish"].upper())

    def test_the_smoke_row_refuses_to_imply_cost(self):
        """🔴 Conflated in BOTH directions on the record: R35.9 and R36.6."""
        self.assertIn("COST", readiness.ROW_SEMANTICS[readiness.ROW_SMOKE]
                      ["does_not_establish"].upper())
        msg = readiness.availability_does_not_imply_cost("vasp_std")
        self.assertIn("CAN IT RUN", msg)
        self.assertIn("WHAT IT COSTS", msg)

    def test_ok_must_be_tristate_not_truthy(self):
        """ADR-036 -- `0`/`''` read downstream as measurements. Refuse them at construction."""
        for bad in (0, "", "no", 1):
            self.assertRaises(ValueError, readiness.row, readiness.ROW_BINARY, bad)


if __name__ == "__main__":
    unittest.main()
