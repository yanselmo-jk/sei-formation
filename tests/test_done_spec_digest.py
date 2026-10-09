"""A `done` marker must not be trusted when the plan entry it marks has changed.

Regression for 2026-08-21: `endpoint_prep_reactant` gained `SEI_QC_EPSINF=1.0` in
`extra_env` but its pre-fix `done` marker made `cmd_submit` skip it, so the EpsInf=1.0
arm of the §39.73 bracket was never run.
"""
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import state


def _entry(**over):
    e = {"key": "endpoint_prep_reactant", "payload": "payload/endpoint_prep.sh",
         "extra_env": {"SEI_ENDPOINT_ROLE": "reactant"}, "nodes": 1, "array": None,
         "chain_links": 1, "cores_per_node": 64, "gpus": 0,
         "account": "acct-A", "rationale": "prose"}
    e.update(over)
    return e


class SpecDigestTest(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = state.Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_env_change_changes_digest(self):
        a = state.spec_digest(_entry())
        b = state.spec_digest(_entry(extra_env={"SEI_ENDPOINT_ROLE": "reactant",
                                                "SEI_QC_EPSINF": "1.0"}))
        self.assertNotEqual(a, b)

    def test_where_not_what_does_not_change_digest(self):
        a = state.spec_digest(_entry())
        b = state.spec_digest(_entry(account="acct-B", rationale="other", partition="x"))
        self.assertEqual(a, b)

    def test_done_status_match_stale_unknown(self):
        e = _entry()
        d = state.spec_digest(e)
        # pre-digest marker (what is on disk from every earlier round): unknown, not stale
        self.store.mark_submitted(e["key"], {"job_ids": ["1"]})
        self.store.mark_done(e["key"])
        self.assertEqual(self.store.done_spec_status(e["key"], d)[0], "unknown")
        # same spec: match
        self.store.mark_submitted(e["key"], {"job_ids": ["1"], "spec_digest": d})
        self.assertEqual(self.store.done_spec_status(e["key"], d)[0], "match")
        # plan changed: stale
        d2 = state.spec_digest(_entry(extra_env={"SEI_QC_EPSINF": "1.0"}))
        st, old = self.store.done_spec_status(e["key"], d2)
        self.assertEqual((st, old), ("stale", d))

    def test_submit_loop_reruns_stale_done(self):
        """cmd_submit's skip branch: stale done → markers moved aside, item submitted."""
        import argparse
        from sei_pilot import cli
        e = _entry()
        old_digest = state.spec_digest(_entry(extra_env={}))
        self.store.mark_submitted(e["key"], {"job_ids": ["1"], "spec_digest": old_digest})
        self.store.mark_done(e["key"])
        self.assertTrue(self.store.is_done(e["key"]))
        # Drive just the decision the loop makes, through the same two calls it uses.
        st, _ = self.store.done_spec_status(e["key"], state.spec_digest(e))
        self.assertEqual(st, "stale")
        moved = self.store.reset_item(e["key"])
        self.assertEqual(sorted(moved), ["endpoint_prep_reactant.done.json",
                                         "endpoint_prep_reactant.submitted.json"])
        self.assertFalse(self.store.is_done(e["key"]))
        self.assertTrue(any(f.startswith("endpoint_prep_reactant.done.json.reset.")
                            for f in os.listdir(self.store.state_dir)))
        self.assertIsNotNone(cli)   # import smoke: cli binds spec_digest


PAYLOAD_NOT_CONVERGED = r"""#!/bin/bash
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
work() { echo '{"status": "not_converged", "note": "x"}' > "${SEI_JOB_DIR}/terminal_status.json"; return 0; }
sei_job_main work
"""


class DoneMarkerCarriesOutcomeTest(unittest.TestCase):
    """§39.80(g)(i): rc=0 + terminal_status not_converged must show in the done marker itself."""

    def setUp(self):
        self.d = tempfile.mkdtemp()
        self.store = state.Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    @unittest.skipUnless(shutil.which("bash"), "bash 없음")
    def test_outcome_field(self):
        import subprocess
        job_dir = self.store.job_dir("ep")
        script = os.path.join(self.d, "p.sh")
        with open(script, "w") as fh:
            fh.write(PAYLOAD_NOT_CONVERGED)
        env = dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT, SEI_WORKDIR=self.d,
                   SEI_KEY="ep", SEI_LOGICAL_KEY="ep", SEI_JOB_DIR=job_dir)
        r = subprocess.run(["bash", script], env=env, capture_output=True,
                           universal_newlines=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = self.store.read_marker("ep", "done")
        self.assertIsNotNone(rec, os.listdir(self.store.state_dir))
        self.assertEqual(rec["payload"]["rc"], 0)
        self.assertEqual(rec["payload"]["outcome"], "not_converged")
        self.assertIn("pkg_fingerprint", rec["payload"])


if __name__ == "__main__":
    unittest.main()


class PhysicsEnvInDigestTest(unittest.TestCase):
    """engineer9: `--level g2` against g1 done markers must NOT read as `match`."""

    def test_level_and_build_change_digest(self):
        e = _entry()
        g1 = state.spec_digest(e, state.physics_env({"SEI_QC_LEVEL": "2", "SEI_PKG_ROOT": "/x"}))
        g2 = state.spec_digest(e, state.physics_env({"SEI_QC_LEVEL": "1", "SEI_PKG_ROOT": "/y"}))
        self.assertNotEqual(g1, g2)
        mod = state.spec_digest(e, state.physics_env({"SEI_QC_LEVEL": "2",
                                                      "SEI_QC_MODULE": "gaussian/g16.c01"}))
        self.assertNotEqual(g1, mod)
        # non-physics harness keys are ignored
        self.assertEqual(g1, state.spec_digest(e, state.physics_env(
            {"SEI_QC_LEVEL": "2", "SEI_PARTITION": "long", "SEI_WORKDIR": "/z"})))

    def test_changed_detection_set_is_unknown_never_stale(self):
        st = state.Store(tempfile.mkdtemp())
        st.mark_submitted("k", {"job_ids": ["1"], "spec_digest": "aaaa",
                                "physics_keys": ["SEI_QC_LEVEL", "SEI_QC_MODULE"]})
        st.mark_done("k")
        same = ["SEI_QC_LEVEL", "SEI_QC_MODULE"]
        self.assertEqual(st.done_spec_status("k", "bbbb", physics_keys=same)[0], "stale")
        self.assertEqual(st.done_spec_status("k", "bbbb", physics_keys=["SEI_QC_LEVEL"])[0],
                         "unknown")          # module detection vanished -> not "changed"
        self.assertEqual(st.done_spec_status("k", "aaaa", physics_keys=["SEI_QC_LEVEL"])[0],
                         "match")

    def test_live_cluster_fields_do_not_change_digest(self):
        a = state.spec_digest(_entry(cores_per_node=64, chain_links=1))
        b = state.spec_digest(_entry(cores_per_node=48, chain_links=2))
        self.assertEqual(a, b)
