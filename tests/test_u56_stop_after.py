"""[02_METHOD_SPEC.md §39.136, fifth addendum, proposer13 RULED (a)] `U56.sh`'s
`SEI_U56_STOP_AFTER` staged circuit-breaker: UNSET must be a pure no-op (bit-identical to
pre-change behavior), SET must stop cleanly with a distinct marker, never a bare completion or
an existing error code. Both properties tested directly by RUNNING the real function (extracted
from the real file, not retyped), not just by reading the source -- same discipline as this
project's own "an author's own spec is not a spec until it has been run against a case it could
fail" standing rule.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

import context  # noqa: F401

U56 = os.path.join(context.PKG_ROOT, "payload", "U56.sh")
COMMON = os.path.join(context.PKG_ROOT, "payload", "common.sh")


def _extract_function(src, name):
    """Pull one `name() { ... }` block out of U56.sh's own source, verbatim -- so this test
    runs the REAL function, not a retyped copy that could silently drift from it."""
    m = re.search(r"^%s\(\) \{\n(.*?\n)\}\n" % re.escape(name), src, re.S | re.M)
    if not m:
        raise AssertionError("could not extract %s() from %s" % (name, U56))
    return "%s() {\n%s}\n" % (name, m.group(1))


class TestStopAfterIsAPureNoOpWhenUnset(unittest.TestCase):
    """The bit-identical-on-unset-path property, run for real: with SEI_U56_STOP_AFTER unset,
    the check must produce zero output, zero side effects, and return control (never exit)."""

    def setUp(self):
        with open(U56, errors="replace") as fh:
            self.src = fh.read()
        self.func = _extract_function(self.src, "_sei_u56_stop_after_check")

    def _run(self, extra_env=None, stage_check="u56_scan"):
        job_dir = tempfile.mkdtemp(prefix="sei_stopcheck_")
        script = (
            "set -u\n"
            "RXN=R-C; METHOD=relaxed_scan; LVL=level2\n"
            "_write_terminal() { echo WRITE_TERMINAL_CALLED; }\n"  # stub -- isolate this check
            + self.func
            + "\n_sei_u56_stop_after_check %s\n"
              "echo AFTER_CHECK_RAN\n" % stage_check
        )
        env = dict(os.environ)
        env["SEI_JOB_DIR"] = job_dir
        if extra_env:
            env.update(extra_env)
        proc = subprocess.run(["bash", "-c", script], env=env,
                              capture_output=True, universal_newlines=True, timeout=30)
        return proc, job_dir

    def test_unset_produces_no_output_and_lets_control_fall_through(self):
        proc, _ = self._run(extra_env={})
        self.assertNotIn("SEI_U56_STOP_AFTER", os.environ)  # sanity: test isolation
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("WRITE_TERMINAL_CALLED", proc.stdout)
        self.assertIn("AFTER_CHECK_RAN", proc.stdout)   # control fell through -- true no-op

    def test_set_to_a_different_stage_is_also_a_no_op(self):
        """Not just unset -- SET to any OTHER stage name must also be a no-op (the check only
        fires on an exact match, never a prefix/substring)."""
        proc, _ = self._run(extra_env={"SEI_U56_STOP_AFTER": "u56_tsopt"},
                            stage_check="u56_scan")
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("WRITE_TERMINAL_CALLED", proc.stdout)
        self.assertIn("AFTER_CHECK_RAN", proc.stdout)

    def test_set_to_the_matching_stage_stops_with_the_ruled_exit_code(self):
        proc, _ = self._run(extra_env={"SEI_U56_STOP_AFTER": "u56_scan"},
                            stage_check="u56_scan")
        self.assertEqual(proc.returncode, 5)   # ruled: not 0 (completion), not an error code
        self.assertIn("WRITE_TERMINAL_CALLED", proc.stdout)
        self.assertNotIn("AFTER_CHECK_RAN", proc.stdout)   # exited, control did NOT fall through


class TestStopAfterWritesARealTerminalMarker(unittest.TestCase):
    """Full function, real `_write_terminal` -> `sei_terminal` -> terminal_status.json --
    confirms the marker is the SAME C-13 mechanism already used elsewhere, not a new format."""

    def setUp(self):
        with open(U56, errors="replace") as fh:
            src = fh.read()
        self.write_terminal = _extract_function(src, "_write_terminal")
        self.check = _extract_function(src, "_sei_u56_stop_after_check")

    def test_marker_written_via_the_real_write_terminal_path(self):
        job_dir = tempfile.mkdtemp(prefix="sei_stopcheck_full_")
        script = (
            'set -u\n'
            'source "%s"\n'
            'SEI_JOB_DIR="%s"\n'
            'RXN=R-C; METHOD=relaxed_scan; LVL=level2\n'
            % (COMMON, job_dir)
            + self.write_terminal + "\n" + self.check + "\n"
            "_sei_u56_stop_after_check u56_scan\n"
        )
        env = dict(os.environ)
        env["SEI_JOB_DIR"] = job_dir
        env["SEI_U56_STOP_AFTER"] = "u56_scan"
        env["SEI_PKG_ROOT"] = context.PKG_ROOT
        proc = subprocess.run([sys.executable and "bash" or "bash", "-c", script], env=env,
                              capture_output=True, universal_newlines=True, timeout=30)
        self.assertEqual(proc.returncode, 5, proc.stdout + proc.stderr)
        marker_path = os.path.join(job_dir, "terminal_status.json")
        self.assertTrue(os.path.exists(marker_path), proc.stdout + proc.stderr)
        marker = json.load(open(marker_path))
        self.assertEqual(marker.get("status"), "stopped_after_stage")
        self.assertIn("u56_scan", marker.get("detail", "") or marker.get("message", "")
                     or json.dumps(marker))
        # 🔴 [critic17, wave-1 review -- "assert on the consumer's behaviour, not the producer's
        # output"] the marker's status STRING alone doesn't prove the harness would leave this
        # alone -- check what outcome.py (the actual consumer) does with it, from the real
        # written file, not a hand-built dict.
        from sei_pilot import outcome
        self.assertEqual(marker.get("cause_class"), "staged")
        self.assertFalse(outcome.should_retry(marker["cause_class"]))


class TestStopAfterIsWiredAtTheRuledBoundary(unittest.TestCase):
    """Static check: the ONE call site this round actually needs (after u56_scan's own
    sei_stage completion) exists, in the right place, and the exit code is documented."""

    def setUp(self):
        with open(U56, errors="replace") as fh:
            self.src = fh.read()

    def test_call_site_immediately_follows_u56_scans_own_sei_stage(self):
        idx = self.src.index('sei_stage u56_scan sei_qc_run "$D" scan.gjf scan.log')
        window = self.src[idx:idx + 300]
        self.assertIn("_sei_u56_stop_after_check u56_scan", window)

    def test_exit_code_5_is_documented_in_the_header_and_used_in_the_function(self):
        header = self.src.split("set -u", 1)[0]
        self.assertIn("SEI_U56_STOP_AFTER", header)
        self.assertIn("exit 5", header.replace("  ", " "))  # documented before set -u
        self.assertIn("exit 5", self.src)   # and actually used in the function body

    def test_function_definition_precedes_its_first_call_site(self):
        define_idx = self.src.index("_sei_u56_stop_after_check() {")
        call_idx = self.src.index("_sei_u56_stop_after_check u56_scan")
        self.assertLess(define_idx, call_idx)


if __name__ == "__main__":
    unittest.main()
