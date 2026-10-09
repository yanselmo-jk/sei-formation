"""§39.80(g) clause (i) / ADR-113: done markers are written from PARSED CONTENT and the
resubmit decision follows the cause-class taxonomy, never the wrapper's rc.

Real-log shapes reproduced here: the P5/endpoint crash prints `Normal termination` after the
opt half and then `Error termination ... l1110.exe` in freq -- so `normal_termination` alone
reads True on the very crash this exists for.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import outcome, state

PKG = context.PKG_ROOT
PAYLOAD_DIR = os.path.join(PKG, "payload")

ROUTE = " #p wb97xd/def2svp opt freq scrf=(pcm,solvent=generic,read)\n ----\n"
LOG_CRASH = (ROUTE + " Optimization completed.\n -- Stationary point found.\n"
             " Normal termination of Gaussian 16 at Thu Aug 20 09:57:06 2026.\n"
             " NEqPCM:  Using equilibrium solvation (IEInf=0, Eps=  18.5000, EpsInf=   0.0000)\n"
             " EpsInf not defined for this solvent.\n"
             " Error termination via Lnk1e in /apps/G16/l1110.exe at Thu Aug 20 09:57:43 2026.\n")
LOG_OK = (ROUTE + " SCF Done:  E(UwB97XD) =  -349.620897959\n"
          " Optimization completed.\n -- Stationary point found.\n"
          " Harmonic frequencies (cm**-1)\n Frequencies --     77.0220   106.9681   151.7485\n"
          " - Thermochemistry -\n Zero-point correction=  0.074564\n"
          " Normal termination of Gaussian 16 at Thu Aug 20 21:05:09 2026.\n")


class CauseClassTest(unittest.TestCase):
    def test_taxonomy_and_retry(self):
        self.assertEqual(outcome.cause_class("converged"), outcome.SUCCESS)
        self.assertEqual(outcome.cause_class("not_converged"), "chemical")
        self.assertEqual(outcome.cause_class("engine_failure"), "engine")
        self.assertEqual(outcome.cause_class("stage2_budget_exhausted"), "budget")
        self.assertEqual(outcome.cause_class("solvent_refused"), "protocol")
        self.assertEqual(outcome.cause_class("some_new_status"), "unknown")
        self.assertEqual(outcome.cause_class("input_defect"), "deterministic")
        self.assertFalse(outcome.should_retry("deterministic"))
        self.assertEqual(outcome.cause_class(None), "absent")
        for c in ("protocol", "engine", "unknown"):
            self.assertTrue(outcome.should_retry(c), c)
        for c in ("chemical", "budget", outcome.SUCCESS, "absent"):
            self.assertFalse(outcome.should_retry(c), c)

    def test_stopped_after_stage_is_staged_and_never_retried(self):
        """🔴 [critic17, wave-1 review -- the blocker] U56.sh's SEI_U56_STOP_AFTER circuit
        breaker writes status `stopped_after_stage`. Before this fix it fell through
        CAUSE_BY_STATUS to `unknown`, which IS in RETRY_CLASSES -- the harness would auto-
        resubmit a deliberate stop forever. §39.138/§39.139 (proposer13): new class `staged`,
        excluded from RETRY_CLASSES."""
        self.assertEqual(outcome.cause_class("stopped_after_stage"), "staged")
        self.assertFalse(outcome.should_retry(outcome.cause_class("stopped_after_stage")))
        self.assertFalse(outcome.should_retry("staged"))

    def test_real_crash_shape_is_deterministic_input_defect(self):
        """The EpsInf sentinel names the defect -> never retried (§39.87)."""
        st, note = outcome.status_from_g16_logs([LOG_CRASH])
        self.assertEqual(st, "input_defect", note)
        seg = LOG_CRASH.replace(" EpsInf not defined for this solvent.\n", "")
        self.assertEqual(outcome.status_from_g16_logs([seg])[0], "engine_failure")
        # [critic11] a sentinel word in a CONVERGED log is not a defect
        ok = LOG_OK.replace(" Optimization completed.\n",
                            " Illegal symmetry operation ignored (harmless).\n Optimization completed.\n")
        self.assertEqual(outcome.status_from_g16_logs([ok])[0], "converged")
        self.assertEqual(outcome.status_from_g16_logs([LOG_OK])[0], "converged")
        # one dead log among good ones taints the task
        self.assertEqual(outcome.status_from_g16_logs([LOG_OK, LOG_CRASH])[0], "input_defect")
        # a log that was never produced is plumbing, not chemistry
        self.assertEqual(outcome.status_from_g16_logs([""])[0], "engine_failure")
        self.assertEqual(outcome.status_from_g16_logs([])[0], "engine_failure")

    def test_freq_requested_but_absent_is_engine(self):
        st, _ = outcome.status_from_g16_logs([ROUTE + " Optimization completed.\n"
                                              " Normal termination of Gaussian 16 at x.\n"])
        self.assertEqual(st, "engine_failure")

    def test_never_returns_a_chemistry_verdict(self):
        """n_imag != 0 etc. is the payload's call (sei_terminal not_converged), not a banner's."""
        st, _ = outcome.status_from_g16_logs([LOG_OK.replace("77.0220", "-120.0")])
        self.assertEqual(st, "converged")   # termination-wise clean; chemistry judged elsewhere

    def test_real_irc_corrector_death_is_deterministic_not_engine(self):
        """[critic14 / lead ruling 2026-08-21] The REAL U56_RA_scan IRC crash (corrector
        integration dies on a real geometry the protocol requested, same deck -> same crash
        every time) must classify `deterministic`, never `engine` -- `engine` would
        auto-resubmit on the next package build for zero new information (critic14 measured
        449 core-h of exactly that risk across U56_RA_scan + U56_RA_qst2)."""
        fixture = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures",
                               "g16_irc_forward_error_termination_u56ra.log")
        with open(fixture, errors="replace") as fh:
            text = fh.read()
        st, note = outcome.status_from_g16_logs([text])
        self.assertEqual(st, "input_defect", note)
        self.assertEqual(outcome.cause_class(st), "deterministic")
        self.assertFalse(outcome.should_retry(outcome.cause_class(st)))


class ResetArchivesEvidenceTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = state.Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_archive_job_dir_moves_evidence_aside(self):
        jd = self.store.job_dir("ep")
        open(os.path.join(jd, "endpoint_tight.log"), "w").write("evidence")
        self.store.mark_done("ep")
        moved = self.store.reset_item("ep", archive_job_dir=True)
        self.assertIn("jobs/ep/", moved)
        self.assertFalse(os.path.exists(os.path.join(jd, "endpoint_tight.log")))
        arch = [f for f in os.listdir(self.store.jobs_dir) if f.startswith("ep.reset.")]
        self.assertEqual(len(arch), 1)
        self.assertTrue(os.path.exists(os.path.join(self.store.jobs_dir, arch[0],
                                                    "endpoint_tight.log")))
        # default (--rerun path) still leaves the directory for healthy resume
        jd2 = self.store.job_dir("ep")
        open(os.path.join(jd2, "x"), "w").write("x")
        self.store.mark_done("ep")
        self.store.reset_item("ep")
        self.assertTrue(os.path.exists(os.path.join(jd2, "x")))


PAYLOAD_TMPL = r"""#!/bin/bash
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
work() { %s; return 0; }
sei_job_main work
"""


@unittest.skipUnless(shutil.which("bash"), "bash 없음")
class MarkerFromParsedContentTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = state.Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, body, key="ep"):
        job_dir = self.store.job_dir(key)
        script = os.path.join(self.d, "p.sh")
        open(script, "w").write(PAYLOAD_TMPL % body)
        env = dict(os.environ, SEI_PKG_ROOT=PKG, SEI_WORKDIR=self.d, SEI_KEY=key,
                   SEI_LOGICAL_KEY=key, SEI_JOB_DIR=job_dir)
        r = subprocess.run(["bash", script], env=env, capture_output=True, universal_newlines=True)
        self.assertEqual(r.returncode, 0, r.stderr + r.stdout)
        return self.store.read_marker(key, "done")["payload"]

    def test_sei_terminal_status_and_class_land_in_marker(self):
        p = self._run('sei_terminal engine_failure "l1110 died" role=reactant')
        self.assertEqual((p["rc"], p["outcome"], p["cause_class"]), (0, "engine_failure", "engine"))

    def test_sei_terminal_from_logs(self):
        log = os.path.join(self.d, "job.log")
        open(log, "w").write(LOG_CRASH)
        p = self._run('sei_terminal_from_logs task=1 -- "%s"' % log)
        self.assertEqual((p["outcome"], p["cause_class"]), ("input_defect", "deterministic"))

    def test_no_terminal_file_is_absent_not_unknown(self):
        p = self._run("true")
        self.assertEqual((p["outcome"], p["cause_class"]), ("absent", "absent"))
        self.assertFalse(outcome.should_retry(p["cause_class"]))


class EveryProductionPayloadWritesTerminalStatusTest(unittest.TestCase):
    """A marker nobody writes is the defect class this round keeps finding. Every payload that
    runs a QC engine must end by writing terminal_status via sei_terminal*."""
    PRODUCTION = ("P1b.sh", "P5.sh", "P6.sh", "endpoint_prep.sh", "U56.sh")

    def test_all(self):
        for name in self.PRODUCTION:
            text = open(os.path.join(PAYLOAD_DIR, name)).read()
            self.assertTrue("sei_terminal" in text,
                            "%s writes no terminal_status -> its done marker would say "
                            "outcome=absent and a crash would become a permanent done" % name)


if __name__ == "__main__":
    unittest.main()


class SubmitLoopRetryPolicyTest(unittest.TestCase):
    """ADR-113 in cmd_submit: done+chemical/budget -> skip; done+engine/protocol/unknown ->
    resubmit (evidence archived); stale spec -> resubmit; plan.json says which happened."""

    def setUp(self):
        from test_plan_report_e2e import make_args
        self.d = tempfile.mkdtemp(prefix="sei_retry_")
        self.args = make_args(self.d, 21000.0)
        self.args.command = "submit"

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _first_round(self):
        from test_plan_report_e2e import fake_cluster
        from sei_pilot import cli
        store = state.Store(self.d)
        cli.cmd_submit(self.args, shell=fake_cluster(), store=store)
        return store

    def _second_round(self):
        from test_plan_report_e2e import fake_cluster
        from sei_pilot import cli
        import json
        store = state.Store(self.d)
        sh = fake_cluster()
        cli.cmd_submit(self.args, shell=sh, store=store)
        plan = json.load(open(os.path.join(store.results_dir, "plan.json")))
        return store, dict((e["key"], e.get("submission") or {}) for e in plan["plan"]), plan

    def _finish(self, store, key, outcome_status, fp="old_build_0000"):
        cause = outcome.cause_class(outcome_status)
        store.mark_done(key, {"rc": 0, "outcome": outcome_status, "cause_class": cause,
                              "pkg_fingerprint": fp})

    def test_policy(self):
        store = self._first_round()
        self.assertTrue(store.is_submitted("P5"))
        self.assertTrue(store.is_submitted("P1b") and store.is_submitted("P6_t1")
                        and store.is_submitted("P6_t16"))
        self._finish(store, "P6_t1", "not_converged")       # chemical -> keep
        self._finish(store, "P6_t16", "engine_failure")     # engine + build changed -> resubmit
        self._finish(store, "P6_t64", "stage2_budget_exhausted")  # budget -> keep
        # P5: array + deterministic defect -> NEVER auto-resubmits, even with a new build
        self._finish(store, "P5", "input_defect")
        open(os.path.join(store.job_dir("P6_t16"), "anchor.log"), "w").write("evidence")
        # stale spec: rewrite P1b's submitted marker with a digest of a different plan
        sub = store.read_marker("P1b", "submitted")
        sub["payload"]["spec_digest"] = "0000000000000000"
        state._atomic_write(store._marker("P1b", "submitted"), __import__("json").dumps(sub))
        self._finish(store, "P1b", "converged")

        store, sub, plan = self._second_round()
        self.assertEqual(sub["P6_t1"]["action"], "skipped_done")
        self.assertEqual(sub["P6_t64"]["action"], "skipped_done")
        self.assertEqual(sub["P6_t16"]["action"], "resubmitted_plumbing_outcome")
        self.assertEqual(sub["P5"]["action"], "skipped_done")
        self.assertTrue(store.is_done("P5"))
        self.assertEqual(sub["P1b"]["action"], "resubmitted_stale_spec")
        self.assertTrue(store.is_submitted("P6_t16") and not store.is_done("P6_t16"))
        self.assertTrue(store.is_submitted("P1b") and not store.is_done("P1b"))
        # evidence archived, not destroyed
        arch = [f for f in os.listdir(store.jobs_dir) if f.startswith("P6_t16.reset.")]
        self.assertEqual(len(arch), 1)
        self.assertTrue(os.path.exists(os.path.join(store.jobs_dir, arch[0], "anchor.log")))
        self.assertGreaterEqual(plan["summary"]["n_skipped_done"], 3)

    def test_engine_outcome_with_same_build_is_not_retried(self):
        from sei_pilot import version
        store = self._first_round()
        fp = version.package_fingerprint(self.args.pkg_root, [])
        # same build as the marker -> nothing changed that could fix it -> skip
        self._finish(store, "P6_t16", "engine_failure", fp=fp)
        store, sub, _ = self._second_round()
        self.assertEqual(sub["P6_t16"]["action"], "skipped_done")


class ArrayAggregateAndFailedGateTest(unittest.TestCase):
    """critic11: arrays write only per-task markers; budget caps exit non-zero (failed path)."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = state.Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_array_outcome_is_aggregated_from_task_markers(self):
        self.store.mark_submitted("P5", {"job_ids": ["1"], "n_tasks": 3})
        for tid, st in ((1, "converged"), (2, "input_defect"), (3, "engine_failure")):
            self.store.mark_done("P5.t%d" % tid, {"rc": 0, "outcome": st,
                                                  "cause_class": outcome.cause_class(st),
                                                  "pkg_fingerprint": "b1"})
        self.assertTrue(self.store.is_done("P5"))
        pl = self.store.outcome_payload("P5", "done")
        self.assertEqual(pl["cause_class"], "deterministic")     # worst wins
        self.assertEqual(pl["tasks"], {1: "success", 2: "deterministic", 3: "engine"})
        self.assertEqual(pl["pkg_fingerprint"], "b1")
        self.assertFalse(outcome.should_retry(pl["cause_class"]))

    def test_aggregate_order(self):
        self.assertEqual(outcome.aggregate_cause(["success", "engine", "budget"]), "budget")
        self.assertEqual(outcome.aggregate_cause(["success", "absent"]), "success")
        self.assertEqual(outcome.aggregate_cause([]), "absent")

    def test_staged_aggregates_correctly_not_just_should_retry_in_isolation(self):
        """🔴 [critic17, wave-1 review -- "the one-line fix is not sufficient"] Asserting
        should_retry("staged") is False is not enough: aggregate_cause() has its OWN lookup
        (CLASS_SEVERITY), separate from CAUSE_BY_STATUS/RETRY_CLASSES, and silently fell
        through to "unknown" for any class missing from that tuple. Executed, not assumed:
        a `staged`-only item must aggregate to `staged` (not `unknown` -> retried), and a
        mixed item (one task staged, one succeeded) must ALSO aggregate to `staged` (not
        `success` -- a job whose staged stage never ran is not a completed answer just
        because a sibling task finished)."""
        self.assertEqual(outcome.aggregate_cause(["staged"]), "staged")
        self.assertFalse(outcome.should_retry(outcome.aggregate_cause(["staged"])))
        self.assertEqual(outcome.aggregate_cause(["staged", "success"]), "staged")
        self.assertEqual(outcome.aggregate_cause(["success", "staged"]), "staged")
        # 🔴 [proposer13, §39.140] exact ruled position: deterministic -> budget -> staged ->
        # chemical -> engine -> protocol -> unknown -> success -> absent. Only deterministic/
        # budget dominate staged; staged itself dominates chemical/engine/protocol/unknown (a
        # human investigating a `staged` item will find any co-occurring ordinary failure --
        # the reverse isn't true, which is why staged masking those is the safer direction).
        self.assertEqual(outcome.aggregate_cause(["staged", "budget"]), "budget")
        self.assertEqual(outcome.aggregate_cause(["staged", "deterministic"]), "deterministic")
        self.assertEqual(outcome.aggregate_cause(["staged", "chemical"]), "staged")
        self.assertEqual(outcome.aggregate_cause(["staged", "engine"]), "staged")
        self.assertEqual(outcome.aggregate_cause(["staged", "protocol"]), "staged")
        self.assertEqual(outcome.aggregate_cause(["staged", "unknown"]), "staged")

    def test_failed_path_respects_budget_and_deterministic(self):
        """cmd_submit: a failed marker with a budget/deterministic cause is NOT retried."""
        from test_plan_report_e2e import make_args, fake_cluster
        from sei_pilot import cli
        import json
        args = make_args(self.d, 21000.0); args.command = "submit"
        cli.cmd_submit(args, shell=fake_cluster(), store=self.store)
        key = "endpoint_prep_reactant"
        self.assertTrue(self.store.is_submitted(key))
        rec = self.store.mark_failed(key, "payload_nonzero_exit", "rc=7")
        rec["payload"] = {"rc": 7, "outcome": "stage2_budget_exhausted", "cause_class": "budget"}
        state._atomic_write(self.store._marker(key, "failed"), json.dumps(rec))
        self.store.mark_failed("P6_t1", "payload_nonzero_exit", "rc=4")   # no outcome -> retry
        cli.cmd_submit(args, shell=fake_cluster(), store=state.Store(self.d))
        plan = json.load(open(os.path.join(self.store.results_dir, "plan.json")))
        sub = dict((e["key"], e.get("submission") or {}) for e in plan["plan"])
        self.assertEqual(sub[key]["action"], "skipped_failed")
        self.assertTrue(state.Store(self.d).is_failed(key))        # marker left in place
        self.assertEqual(sub["P6_t1"]["action"], "submitted")
