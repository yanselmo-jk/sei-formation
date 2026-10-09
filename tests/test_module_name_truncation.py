"""Regression for the module-name truncation that lost the entire Gaussian run.

🔴 WHAT HAPPENED (real incident, RT-1 on the cluster):
`sysprobe.parse_module_avail` reduced `gaussian/g16.c01.linda` to `gaussian/g16.c01.lin`,
a module that does not exist. Every Gaussian job died in ~6 s with

    ModuleCmd_Load.c(208):ERROR:105: Unable to locate a modulefile for 'gaussian/g16.c01.lin'

⟹ P1, P1b, P5 and all three P6 anchors failed. **κ, S and the TS unit cost: all unmeasured.**

🔴 The cause was `str.rstrip("(default)")`, which strips a CHARACTER SET, not a suffix.
🔴 Why it survived review: on the real cluster this line altered 13 tokens and **10 of those
were altered correctly** — they genuinely ended in `(default)`. Only the three
`gaussian/*.linda` entries were corrupted, and the corruption produced a **plausible name.**

The fixture below is **verbatim from the cluster reply** (`cluster.modules_raw` of
`sei_probe_report.cpu.json`). It is not hand-written: hand-written fixtures would have
encoded what we imagined the cluster prints.
"""

import unittest

import context  # noqa: F401
from sei_pilot import sysprobe

#: Verbatim from the cluster reply. Do not "tidy" this text.
CLUSTER_MODULE_TEXT = """cray-fftw_impi/3.3.6.2(default)
cray-impi/1.1.4(default)
gcc/7.2.0(default)    intel/19.0.5(default) pgi/19.1
impi/18.0.3            impi/oneapi_21.2       openmpi/3.1.0(default)
impi/19.0.5(default)   mvapich2/2.3.1
conda/pytorch_1.0            lammps/3Mar20(default)
gromacs/2016.4               python/3.9.5(default)
gromacs/2024.5(default)      R/3.6.2
cfx/v201               fluent/v191            gaussian/g16.a03
cfx/v202               fluent/v192            gaussian/g16.a03.linda
cfx/v212               fluent/v195            gaussian/g16.b01.linda
cfx/v221               fluent/v201            gaussian/g16.c01.linda
cmake/3.17.4(default) ImageMagick/7.0.8-20  vtune/17.0.5"""


class TestModuleNameIsNotTruncated(unittest.TestCase):
    def parsed(self):
        return sysprobe.parse_module_avail(CLUSTER_MODULE_TEXT)

    def test_linda_suffix_survives(self):
        """🔴 The exact failure: `.linda` must not become `.lin`."""
        got = self.parsed()
        self.assertIn("gaussian/g16.c01.linda", got,
                      "the real module name was lost — jobs will fail with rc=3")
        self.assertNotIn("gaussian/g16.c01.lin", got,
                         "a module name that does not exist was produced")

    def test_all_linda_variants_survive(self):
        got = self.parsed()
        for name in ("gaussian/g16.a03.linda", "gaussian/g16.b01.linda",
                     "gaussian/g16.c01.linda"):
            self.assertIn(name, got)

    def test_plain_name_without_suffix_is_untouched(self):
        self.assertIn("gaussian/g16.a03", self.parsed())

    def test_legitimate_default_marker_is_still_stripped(self):
        """🔴 Do not regress the 10 cases the old code got right.

        The marker really is appended by `module avail`; removing it is correct.
        """
        got = self.parsed()
        # 🔴 must be a module that the keyword filter actually emits — my first attempt
        #    asserted on `cray-fftw`, which the filter drops entirely, so the test failed
        #    for a reason unrelated to the bug.
        for name in ("gcc/7.2.0", "intel/19.0.5", "python/3.9.5"):
            self.assertIn(name, got)
            self.assertNotIn(name + "(default)", got)

    def test_helper_removes_suffix_not_character_set(self):
        f = sysprobe.strip_module_markers
        self.assertEqual(f("gaussian/g16.c01.linda"), "gaussian/g16.c01.linda")
        self.assertEqual(f("intel/19.1.2(default)"), "intel/19.1.2")
        # the shape that caused the incident: trailing chars that are all in the set
        self.assertEqual(f("some/module.ltd"), "some/module.ltd")
        self.assertEqual(f("x/adfelut"), "x/adfelut")


class TestFixIsNotLindaSpecific(unittest.TestCase):
    """🔴 A fix that special-cases `linda` would be the SAME class of error as the bug.

    lead: *"The name is an input to the check, not a substitute for it. A fixture with only
    `c01.linda` would pass with a fix that special-cases `linda`."*

    So this asserts the **general** property: only the documented markers are removed, and any
    other trailing text survives — including text made entirely of characters from the old
    `rstrip("(default)")` character set, which is exactly what used to be eaten.
    """

    def test_all_ten_legitimate_default_markers_are_stripped(self):
        """All 10 real `(default)` tokens from the cluster must still be cleaned."""
        got = sysprobe.parse_module_avail(CLUSTER_MODULE_TEXT)
        for name in ("cray-fftw_impi/3.3.6.2", "cray-impi/1.1.4", "gcc/7.2.0",
                     "intel/19.0.5", "openmpi/3.1.0", "impi/19.0.5",
                     "lammps/3Mar20", "python/3.9.5", "gromacs/2024.5",
                     "cmake/3.17.4"):
            self.assertIn(name, got, "legitimate (default) strip regressed: %s" % name)
            self.assertNotIn(name + "(default)", got)

    def test_arbitrary_suffixes_built_from_the_old_charset_survive(self):
        """🔴 The old bug ate any trailing run of chars from { ( d e f a u l t ) }.

        `linda` was merely one instance. These synthetic names are all made of that charset,
        so a `linda`-specific fix would still corrupt them.
        """
        f = sysprobe.strip_module_markers
        for name in ("vendor/tool.linda", "vendor/tool.default", "vendor/tool.ault",
                     "vendor/tool.fated", "vendor/tool.deft", "vendor/tool.ude",
                     "vendor/x.lua", "vendor/x.el"):
            self.assertEqual(f(name), name,
                             "%s was altered — the fix is charset-based, not suffix-based" % name)

    def test_only_documented_markers_are_removed(self):
        f = sysprobe.strip_module_markers
        for marker in sysprobe.MODULE_MARKERS:
            self.assertEqual(f("mod/1.0" + marker), "mod/1.0")
        # stacked markers are handled, but nothing else is
        self.assertEqual(f("mod/1.0(default)(L)"), "mod/1.0")
        self.assertEqual(f("mod/1.0(beta)"), "mod/1.0(beta)")
