"""U56.sh terminal_status fix (Track A item 1, linear-hopping-frog plan).

Before this fix, U56.sh never called `sei_terminal`/`sei_terminal_from_logs` on any exit
path -- a real rc=0 completion that produced `u56_attempt.json` with
`status: "ts_candidate_produced"` still left `terminal_status.json` empty, so the harness's
own state marker read `outcome: absent, cause_class: absent` (misleading: real work happened).

This does not decide the C-2/IRC pass verdict (that stays the collection stage's job, per
U56.sh's own note in u56_attempt.json) -- it only checks that the payload honestly reports
where it stopped, on every exit path, using its own status vocabulary.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import outcome

PAYLOAD = os.path.join(context.PKG_ROOT, "payload", "U56.sh")
HAVE_BASH = shutil.which("bash") is not None


class NewStatusTaxonomyTest(unittest.TestCase):
    """The new U56-only statuses land in the shared taxonomy, not as unclassified 'unknown'."""

    def test_completion_status_is_success_not_retried(self):
        self.assertEqual(outcome.cause_class("ts_candidate_produced"), outcome.SUCCESS)
        self.assertFalse(outcome.should_retry(outcome.cause_class("ts_candidate_produced")))

    def test_gate_refusals_are_protocol_and_retried_on_a_new_build(self):
        for status in ("endpoint_geometry_missing", "c8_precondition_refused",
                       "mapping_unresolved", "gfn2_prestage_unavailable",
                       "gscan_protocol_indeterminate"):
            self.assertEqual(outcome.cause_class(status), "protocol", status)
            self.assertTrue(outcome.should_retry("protocol"))

    def test_measured_negative_findings_are_chemical_not_retried(self):
        for status in ("indeterminate_missing_coordinate", "scan_not_converged",
                       "saddle_outside_endpoint_bracket", "spectator_mode_not_the_coordinate"):
            self.assertEqual(outcome.cause_class(status), "chemical", status)
            self.assertFalse(outcome.should_retry("chemical"))

    def test_ts_opt_no_geometry_is_engine(self):
        self.assertEqual(outcome.cause_class("ts_opt_no_geometry"), "engine")

    def test_no_irc_direction_ran_is_unknown_not_dropped(self):
        self.assertEqual(outcome.cause_class("irc_refused_no_direction_ran"), "unknown")
        self.assertTrue(outcome.should_retry("unknown"))


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class U56WritesTerminalStatusOnEveryExitTest(unittest.TestCase):
    """Runs the real payload on its cheapest failure paths (no QC engine needed) and checks
    terminal_status.json instead of trusting a report."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_u56_term_")
        self.job_dir = os.path.join(self.d, "jobs", "U56_test")
        os.makedirs(self.job_dir)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, env_extra):
        env = dict(os.environ)
        env.update({
            "SEI_PKG_ROOT": context.PKG_ROOT,
            "SEI_WORKDIR": self.d,
            "SEI_JOB_DIR": self.job_dir,
            "SEI_KEY": "U56_test",
            "SEI_TOTAL_CORES": "1",
        })
        env.update(env_extra)
        return subprocess.run(["bash", PAYLOAD], env=env, capture_output=True,
                              universal_newlines=True, timeout=60)

    def _terminal(self):
        path = os.path.join(self.job_dir, "terminal_status.json")
        self.assertTrue(os.path.exists(path), "U56.sh wrote no terminal_status.json at all")
        return json.load(open(path))

    def test_invalid_reaction_writes_terminal_status(self):
        proc = self._run({"SEI_U56_REACTION": "not-a-reaction", "SEI_U56_METHOD": "qst2"})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        rec = self._terminal()
        self.assertEqual(rec["status"], "input_error")
        self.assertEqual(rec["cause_class"], "protocol")
        self.assertNotEqual(rec["cause_class"], "absent")

    def test_invalid_method_writes_terminal_status(self):
        proc = self._run({"SEI_U56_REACTION": "R-A", "SEI_U56_METHOD": "not-a-method"})
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        rec = self._terminal()
        self.assertEqual(rec["status"], "input_error")
        self.assertEqual(rec["cause_class"], "protocol")


class IrcTerminalWrittenFlagIsConditionalTest(unittest.TestCase):
    """[critic14] `sei_terminal_from_logs` can exit non-zero and write NOTHING (demonstrated:
    a broken PYTHONPATH gives rc=1, no file). `IRC_TERMINAL_WRITTEN=1` must only be set when
    that call actually succeeded (`&&`), never unconditionally on the next line -- an
    unconditional set would skip the fallback write below on exactly the run where the
    log-derived write never happened, landing back on `outcome: absent` (the state this whole
    fix removes). Static source check: a live repro would need to break ONLY the
    `sei_terminal_from_logs` invocation without breaking every other SEI_PKG_ROOT-dependent
    call in the same script, which isn't independently triggerable from outside."""

    def test_the_flag_is_set_with_and_not_unconditionally(self):
        with open(PAYLOAD, errors="replace") as fh:
            src = fh.read()
        idx = src.index("sei_terminal_from_logs ")
        # the next occurrence of IRC_TERMINAL_WRITTEN=1 after the call must be on the SAME
        # logical line (joined by `&&`, allowing a line-continuation backslash), not a bare
        # assignment on its own line.
        window = src[idx:idx + 400]
        self.assertRegex(window, r"sei_terminal_from_logs[^\n]*\\?\n?\s*&&\s*IRC_TERMINAL_WRITTEN=1",
                         "IRC_TERMINAL_WRITTEN=1 must be `&&`-gated on sei_terminal_from_logs "
                         "succeeding, not set unconditionally on the next line")
        self.assertNotRegex(
            window, r"sei_terminal_from_logs[^\n]*\n\s*IRC_TERMINAL_WRITTEN=1\s*\n",
            "found an UNCONDITIONAL IRC_TERMINAL_WRITTEN=1 right after sei_terminal_from_logs "
            "-- this must be `&&`-gated (see class docstring)")


if __name__ == "__main__":
    unittest.main()
