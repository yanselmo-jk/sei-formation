"""`executions.jsonl` telemetry: the `host`/`cores` append (R31.2a) and the integrity audit (R36.3).

🔴 Why this file exists, in the shape the incident had.

  `f` (the production-shape availability fraction, 5-month condition (ii)) can only be computed
  from per-task `host` records. `started.json` cannot supply them: it is a FIXED PATH written with
  `>`, so concurrent array tasks on different hosts erase each other -- 05_STATE §4 records that
  P5's 22 tasks did exactly that and condition (ii) went unmeasured as a result.
  `executions.jsonl` is appended with `>>`, is concurrency-safe by construction, already carried a
  per-task `epoch` -- and carried NO `host` and NO `cores`.
  R31.2a's ruling: add two fields to the working append. Do NOT add a second mechanism.

🔴 The tests run the DELIVERED `payload/common.sh`, not a copy of it, with `hostname` replaced by a
  PATH shim -- the same construction `test_throughput_hosts.py` uses and for the same reason
  (ADR-041/-042): a hand-written fixture verifies the payload output I IMAGINED. The one thing
  substituted is the environment.

🔴 Failure direction is itself under test (Rule 18). `fallback_trigger_fired` must be **None**, not
  False, when there is nothing to check. `False` reads downstream as "checked, and fine"; a gate
  that falls toward PASS is worse than no gate. `exceeds_tripwire: None` is the precedent, and it
  is the one gate of ours that has been tested by a real incident (§44.7).
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import collect as collect_mod
from sei_pilot import execlog
from sei_pilot.state import Store

COMMON_SH = os.path.join(context.PKG_ROOT, "payload", "common.sh")

HAVE_BASH = shutil.which("bash") is not None

#: A payload that does nothing but go through `sei_job_main`, which is the function that owns the
#: append under test. Deliberately trivial: the subject is the bookkeeping, not the work.
FAKE_PAYLOAD = r"""#!/bin/bash
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
work() { return 0; }
sei_job_main work
"""


def _shim(bin_dir, name, body):
    path = os.path.join(bin_dir, name)
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n" + body + "\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


class _TempRoot(unittest.TestCase):
    """One temp root per test, removed by addCleanup.

    🔴 §44.6: this suite filled /tmp twice and aborted two builds. Every temp dir gets an
    addCleanup, and the measured invariant is "temp-dir count before == after a full run".
    """

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_execlog_")
        self.addCleanup(shutil.rmtree, self.d, True)


@unittest.skipUnless(HAVE_BASH, "bash not available")
class TestRunAppendCarriesHostAndCores(_TempRoot):
    """🔴 THE REGRESSION. Runs the delivered common.sh and reads what it actually wrote."""

    def _run(self, host="node0517", cores=64, key="P1", always_run=False):
        pkg_root = self.d + "/pkg"
        os.makedirs(pkg_root + "/payload", exist_ok=True)
        shutil.copy(COMMON_SH, pkg_root + "/payload/common.sh")
        payload = os.path.join(self.d, "fake_payload.sh")
        with open(payload, "w") as fh:
            fh.write(FAKE_PAYLOAD)
        os.chmod(payload, 0o755)

        bin_dir = tempfile.mkdtemp(prefix="sei_execlog_shim_")
        self.addCleanup(shutil.rmtree, bin_dir, True)
        _shim(bin_dir, "hostname", 'printf "%s\\n" "$SEI_TEST_FAKE_HOST"')

        job_dir = os.path.join(self.d, "jobs", key)
        os.makedirs(job_dir, exist_ok=True)
        env = dict(os.environ)
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        env["SEI_PKG_ROOT"] = pkg_root
        env["SEI_WORKDIR"] = self.d
        env["SEI_KEY"] = key
        env["SEI_LOGICAL_KEY"] = key
        env["SEI_JOB_DIR"] = job_dir
        env["SEI_TOTAL_CORES"] = str(cores)
        env["SEI_TEST_FAKE_HOST"] = host
        # Real concurrent array tasks all start before ANY of them writes a done marker.
        # Without this the 2nd and 3rd sequential runs would take the idempotent-resume path
        # and append `skip_done` instead of `run` -- i.e. the test would be simulating a
        # RESTART, not concurrency, and would prove nothing about the property under test.
        if always_run:
            env["SEI_ALWAYS_RUN"] = "1"
        proc = subprocess.Popen(["bash", payload], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        self.assertEqual(proc.returncode, 0,
                         "payload rc=%s\nstdout=%s\nstderr=%s" % (proc.returncode, out, err))
        return job_dir

    def _run_lines(self, job_dir):
        path = os.path.join(job_dir, "executions.jsonl")
        self.assertTrue(os.path.isfile(path), "common.sh wrote no executions.jsonl at all")
        with open(path) as fh:
            recs = [json.loads(l) for l in fh if l.strip()]
        return [r for r in recs if r.get("action") == "run"]

    def test_run_append_has_host(self):
        runs = self._run_lines(self._run(host="node0517"))
        self.assertEqual(len(runs), 1)
        # Assert PRESENCE first, so a missing field is a FAIL and not a KeyError ERROR.
        # ADR-042(a): an ERROR usually means the experiment broke, and is weak evidence.
        self.assertIn("host", runs[0],
                      "the 'run' append carries no `host` -- f cannot be measured from this log")
        self.assertEqual(runs[0]["host"], "node0517")

    def test_run_append_has_cores(self):
        runs = self._run_lines(self._run(cores=64))
        self.assertIn("cores", runs[0],
                      "the 'run' append carries no `cores` -- core-h per host is unrecoverable")
        self.assertEqual(runs[0]["cores"], 64)

    def test_concurrent_tasks_all_survive_in_the_append(self):
        """🔴 The property `started.json` does NOT have, and the reason for choosing the append.

        Three tasks sharing one job dir. All three `host` values must survive.
        `started.json` keeps exactly one, because it is a truncating write.
        """
        job_dir = None
        for h in ("node0510", "node0514", "node0513"):
            job_dir = self._run(host=h, key="P5", always_run=True)
        runs = self._run_lines(job_dir)
        # Presence before value: without this a pre-fix run raises KeyError and reports as an
        # ERROR, and §0.2(a) is explicit that an ERROR is usually a broken experiment rather than
        # a detected defect. The revert measurement has to be readable to be evidence.
        missing = [i for i, r in enumerate(runs) if "host" not in r]
        self.assertEqual(missing, [],
                         "%d of %d 'run' appends carry no `host` -- concurrent per-task telemetry "
                         "is unrecoverable from this log" % (len(missing), len(runs)))
        self.assertEqual(sorted(r["host"] for r in runs),
                         ["node0510", "node0513", "node0514"])
        # And the contrast that motivated the choice, asserted rather than asserted-in-prose:
        with open(os.path.join(job_dir, "started.json")) as fh:
            started = json.load(fh)
        self.assertEqual(started["host"], "node0513",
                         "started.json is expected to hold only the LAST writer -- if this ever "
                         "changes, re-read R31.2a before moving telemetry back onto it")

    def test_host_reaches_execution_audit(self):
        """Entry-point check (ADR-041): payload -> collector, not the helper in isolation."""
        job_dir = self._run(host="node0517")
        audit = collect_mod.execution_audit(job_dir)
        self.assertIn("hosts_observed", audit,
                      "execution_audit drops the host again -- the B-3 / throughput shape")
        self.assertEqual(audit["hosts_observed"], ["node0517"])
        self.assertEqual(audit["log_integrity"]["runs_missing_host_field"], 0)
        self.assertEqual(audit["log_integrity"]["runs_missing_cores_field"], 0)


def _write_log(path, records, extra_raw_lines=()):
    with open(path, "w") as fh:
        for r in records:
            fh.write(json.dumps(r) + "\n")
        for raw in extra_raw_lines:
            fh.write(raw + "\n")


class TestFallbackTriggerFailureDirection(_TempRoot):
    """🔴 Rule 18. The trigger's value when nothing was checked must be None, never False."""

    def test_missing_log_is_none_not_false(self):
        res = execlog.audit(os.path.join(self.d, "nope.jsonl"))
        self.assertIsNone(res["fallback_trigger_fired"],
                          "a missing log reported False would read downstream as 'checked, "
                          "fine' and the trigger would pass silently forever")
        self.assertIsNone(res["lines_total"])
        self.assertFalse(res["exists"])

    def test_unchecked_line_count_is_none_not_false(self):
        p = os.path.join(self.d, "executions.jsonl")
        _write_log(p, [{"link": "P1", "action": "run", "epoch": 1, "host": "n1", "cores": 64}])
        res = execlog.audit(p)  # no expected count supplied
        self.assertIsNone(res["line_count_matches"])
        self.assertIsNone(res["expected_run_lines"])

    def test_clean_log_does_not_fire(self):
        p = os.path.join(self.d, "executions.jsonl")
        _write_log(p, [{"link": "P5", "action": "run", "epoch": i, "host": "n%d" % i,
                        "cores": 64} for i in range(3)])
        res = execlog.audit(p, expected_run_lines=3)
        self.assertFalse(res["fallback_trigger_fired"])
        self.assertEqual(res["fallback_trigger_reasons"], [])
        self.assertTrue(res["line_count_matches"])
        self.assertEqual(res["n_distinct_hosts"], 3)


class TestFallbackTriggerFires(_TempRoot):
    """The three pre-registered conditions. R31.2d: one bad line suffices, no severity threshold."""

    def _path(self):
        return os.path.join(self.d, "executions.jsonl")

    def test_one_unparseable_line_is_sufficient(self):
        p = self._path()
        _write_log(p,
                   [{"link": "P5", "action": "run", "epoch": 1, "host": "n1", "cores": 64}] * 50,
                   extra_raw_lines=['{"link": "P5", "action": "ru'])  # a torn concurrent append
        res = execlog.audit(p)
        self.assertTrue(res["fallback_trigger_fired"],
                        "a single malformed line must fire -- there is no severity threshold "
                        "and no judgement call at trigger time (R31.2d)")
        self.assertEqual(res["unparseable_count"], 1)
        self.assertEqual(res["unparseable_line_numbers"], [51])

    def test_size_near_the_pfl_extent_fires(self):
        p = self._path()
        pad = "x" * 512
        rec = {"link": "P5", "action": "run", "epoch": 1, "host": "n1", "cores": 64, "pad": pad}
        n = int(execlog.size_trigger_bytes() / len(json.dumps(rec))) + 2
        _write_log(p, [rec] * n)
        res = execlog.audit(p)
        self.assertGreaterEqual(res["size_bytes"], execlog.size_trigger_bytes())
        self.assertTrue(res["fallback_trigger_fired"])
        self.assertTrue(any("PFL" in r for r in res["fallback_trigger_reasons"]))

    def test_missing_task_line_fires(self):
        p = self._path()
        _write_log(p, [{"link": "P5", "action": "run", "epoch": i, "host": "n%d" % i,
                        "cores": 64} for i in range(19)])
        res = execlog.audit(p, expected_run_lines=22)
        self.assertFalse(res["line_count_matches"])
        self.assertTrue(res["fallback_trigger_fired"])

    def test_fired_trigger_reaches_warnings_and_the_remedy_is_stated(self):
        """🔴 Rule 13: a judgement-triggering value must reach the artefact AND warnings[].

        The field is read by code; warnings[] is read by a human. Half of that is what §40 called
        "a tripwire violating its own reason for existing".
        """
        p = self._path()
        _write_log(p, [{"link": "P5", "action": "run", "epoch": 1}],
                   extra_raw_lines=["not json at all"])
        res = execlog.audit(p)
        self.assertTrue(res["warnings"], "the trigger fired and nothing reached warnings[]")
        joined = " ".join(res["warnings"])
        self.assertIn("per-task files", joined,
                      "a fired trigger must state its PRE-REGISTERED remedy, not just the fact")
        self.assertIn("starts/task_", joined)


class TestIntegrityReachesTheCollector(_TempRoot):
    """Entry point, not the helper (ADR-041 / Rule 6)."""

    def test_execution_audit_carries_integrity_and_propagates_warnings(self):
        job_dir = os.path.join(self.d, "jobs", "P5")
        os.makedirs(job_dir)
        _write_log(os.path.join(job_dir, "executions.jsonl"),
                   [{"link": "P5", "action": "run", "epoch": 1, "host": "n1", "cores": 64}],
                   extra_raw_lines=["}{ torn"])
        audit = collect_mod.execution_audit(job_dir)
        self.assertIn("log_integrity", audit,
                      "collect.execution_audit dropped the integrity block -- the collector is "
                      "where R36.3 asked for the size assertion to live")
        self.assertTrue(audit["log_integrity"]["fallback_trigger_fired"])
        self.assertTrue(any("execlog_fallback_trigger" in w for w in audit["warnings"]),
                        "the integrity warning did not reach execution_audit()['warnings'], "
                        "which is the list every collector splices into pilots[].warnings")

    def test_missing_log_leaves_the_collector_verdict_unknown_not_clean(self):
        job_dir = os.path.join(self.d, "jobs", "P3")
        os.makedirs(job_dir)
        audit = collect_mod.execution_audit(job_dir)
        # Presence before value, so an unwired collector reports FAIL rather than KeyError/ERROR.
        self.assertIn("log_integrity", audit,
                      "collect.execution_audit has no integrity block at all -- the size "
                      "assertion R36.3 asked for is not being evaluated on this run")
        self.assertIsNone(audit["log_integrity"]["fallback_trigger_fired"])
        self.assertEqual(audit["warnings"], [])


class TestAuditDoesNotUseTheTruncatingReader(_TempRoot):
    """🔴 `collect._read()` caps at 4,000,000 bytes -- BELOW the 4 MiB PFL boundary.

    Routing this audit through it would silently truncate the log at exactly the size where the
    answer starts to matter, and `collect._read_jsonl` would then drop the resulting partial last
    line without a word. This asserts the audit sees past that cap.
    """

    def test_lines_past_the_read_cap_are_still_counted(self):
        p = os.path.join(self.d, "executions.jsonl")
        pad = "y" * 900
        rec = {"link": "P5", "action": "run", "epoch": 1, "host": "n1", "cores": 64, "pad": pad}
        line_len = len(json.dumps(rec)) + 1
        n = int(4000000 / line_len) + 25
        _write_log(p, [rec] * n)
        res = execlog.audit(p)
        self.assertEqual(res["lines_total"], n,
                         "the audit lost lines past collect._read()'s 4,000,000-byte cap")
        self.assertEqual(res["observed_run_lines"], n)
        self.assertEqual(res["unparseable_count"], 0,
                         "a truncated read would have produced a torn final line")


class TestP6IntegrityGatesKappa(_TempRoot):
    """🔴 ADR-091/ADR-092: `collect_p6` never called `execution_audit` -- kappa (the single
    dominant variable of the 5-month schedule) had WEAKER integrity protection than P1's
    core-h totals, even though `payload/P6.sh` writes the exact same telemetry every other
    collector reads. Reproduces critic8's adversarial construction: `anchor_t16` run TWICE
    in `stage_events.jsonl`, plus a malformed `executions.jsonl` line.
    """

    def _make_task(self, store, key, threads, wall_s=100.0, duplicate=False, malformed=False):
        job_dir = store.job_dir(key)
        os.makedirs(job_dir, exist_ok=True)
        with open(os.path.join(job_dir, "p6_anchor.json"), "w") as fh:
            json.dump({"declared_threads": threads, "requested_threads": threads,
                      "actual_nprocshared": threads, "wall_s": wall_s, "rc": 0}, fh)
        events = [{"stage": "anchor_t%d" % threads, "event": "run"}]
        if duplicate:
            events.append({"stage": "anchor_t%d" % threads, "event": "run"})
        _write_log(os.path.join(job_dir, "stage_events.jsonl"), events)
        exec_lines = [{"link": key, "action": "run", "epoch": 1, "host": "n1", "cores": threads}]
        _write_log(os.path.join(job_dir, "executions.jsonl"), exec_lines,
                  extra_raw_lines=(["}{ torn"] if malformed else ()))
        store.mark_submitted(key, {})
        store.mark_done(key, {"start_epoch": 0, "end_epoch": int(wall_s)})

    def test_a_clean_anchor_task_is_valid_and_carries_its_audit(self):
        store = Store(self.d)
        self._make_task(store, "P6_t16", 16, wall_s=100.0)
        res = collect_mod.collect_p6(store, keys=["P6_t16"])
        task = res["tasks"][0]
        self.assertIn("execution_audit", task,
                      "collect_p6 must carry the audit on every task, not just P1-style collectors")
        self.assertTrue(task["valid"])
        self.assertIsNotNone(res["kappa"])

    def test_the_adversarial_double_execution_case_invalidates_the_anchor(self):
        """critic8's exact construction: anchor_t16 run twice, wall_s=999999.0 standing in
        for whatever the second/overwritten run reported."""
        store = Store(self.d)
        self._make_task(store, "P6_t16", 16, wall_s=999999.0, duplicate=True)
        res = collect_mod.collect_p6(store, keys=["P6_t16"])
        task = res["tasks"][0]
        self.assertTrue(task["execution_audit"]["duplicate_execution"])
        self.assertFalse(task["valid"],
                         "a task whose stage ran twice must not be [MEASURED] -- the number on "
                         "disk is 'whichever run finished last', not a measurement")
        self.assertIn("invalid_reason", task)
        self.assertIsNone(res["kappa"],
                          "kappa must not be computed from the invalidated anchor")

    def test_a_malformed_executions_line_also_invalidates_the_anchor(self):
        store = Store(self.d)
        self._make_task(store, "P6_t16", 16, wall_s=100.0, malformed=True)
        res = collect_mod.collect_p6(store, keys=["P6_t16"])
        task = res["tasks"][0]
        self.assertGreater(task["execution_audit"]["log_integrity"]["unparseable_count"], 0)
        self.assertFalse(task["valid"])
        self.assertIsNone(res["kappa"])

    def test_adr048_thread_mismatch_and_integrity_are_reported_as_distinct_reasons(self):
        """🔴 Do not collapse ADR-048's pre-existing check with the new integrity gate --
        a reader needs to know WHICH property failed."""
        store = Store(self.d)
        job_dir = store.job_dir("P6_t16")
        os.makedirs(job_dir, exist_ok=True)
        with open(os.path.join(job_dir, "p6_anchor.json"), "w") as fh:
            json.dump({"declared_threads": 16, "requested_threads": 16,
                      "actual_nprocshared": 1, "wall_s": 100.0, "rc": 0}, fh)  # oversubscribed
        store.mark_submitted("P6_t16", {})
        store.mark_done("P6_t16", {"start_epoch": 0, "end_epoch": 100})
        res = collect_mod.collect_p6(store, keys=["P6_t16"])
        task = res["tasks"][0]
        self.assertFalse(task["valid"])
        self.assertIn("nprocshared", task["invalid_reason"])
        self.assertNotIn("execution_audit", task["invalid_reason"],
                         "ADR-048's mismatch reason must not be blamed on the integrity audit")


if __name__ == "__main__":
    unittest.main()
