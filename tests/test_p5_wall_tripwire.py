"""[critic10] A wall kill must leave a marker — otherwise it is invisible in the denominator.

🔴 WHAT HAPPENED: P5.t21/t22 were killed by the scheduler mid-species and left a `run` event
with **no `finish` event** — unlike t20, the same species, which recorded a real crash honestly.
P5 had no per-species budget check and no SIGTERM trap, so a wall kill was indistinguishable
from a species that never started, and "P5: 20/22" read as a flat 22-species denominator rather
than "20 measured + 2 unrecoverable on the same already-known problem species".

🔒 The pattern is copied from `endpoint_prep.sh`, not invented: PBS sends SIGTERM before
SIGKILL, so the trap gets exactly one chance to say what happened.
"""

import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import collect as collect_mod
from sei_pilot.state import Store

P5 = os.path.join(context.PKG_ROOT, "payload", "P5.sh")


class TestThePayloadCanSayItWasKilled(unittest.TestCase):
    def setUp(self):
        with open(P5, errors="replace") as fh:
            self.src = fh.read()

    def test_a_sigterm_trap_exists(self):
        """Without it the process dies silently and the round loses the distinction between
        'killed' and 'never ran'."""
        self.assertIn("trap '_p5_write_marker wall_exhausted", self.src)
        self.assertIn("' TERM", self.src)

    def test_the_budget_is_checked_before_launching_a_species(self):
        """🔴 Checking after the fact cannot help: the point is not to start a species we
        cannot finish. `break`, not `continue` — the remaining species were not attempted and
        must not be recorded as attempts."""
        self.assertIn("wall budget", self.src)
        self.assertIn("not starting it", self.src)
        self.assertIn("were not attempted", self.src)

    def test_the_marker_names_the_species_that_was_running(self):
        self.assertIn('"last_species"', self.src)
        self.assertIn("_P5_CURRENT", self.src)

    def test_the_marker_says_why_it_exists(self):
        """A marker whose purpose is undocumented gets deleted by the next person tidying up."""
        self.assertIn("indistinguishable from a species that never started", self.src)


class TestTheCollectorReadsIt(unittest.TestCase):
    """🔒 The producer/consumer half. A marker nobody reads is the defect this project keeps
    finding — writing it and never surfacing it would reproduce exactly that."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_p5w_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.job = os.path.join(self.d, "jobs", "P5")
        os.makedirs(self.job)
        os.makedirs(os.path.join(self.d, "state"))
        with open(os.path.join(self.job, "wall_exhausted.t21.json"), "w") as fh:
            json.dump({"status": "wall_exhausted", "last_species": "li_ec2_cation",
                       "elapsed_h": 11.93, "wall_budget_h": 12.0}, fh)
        with open(os.path.join(self.job, "p5_results.json"), "w") as fh:
            json.dump({"rows": [], "n_requested": 22}, fh)
        self.store = Store(self.d)
        self.store.mark_done("P5", {"start_epoch": 0, "end_epoch": 60, "rc": 0})

    def test_the_marker_reaches_the_reply(self):
        res = collect_mod.collect_p5(self.store, "P5")
        self.assertEqual(1, len(res["wall_markers"]))
        self.assertEqual("li_ec2_cation", res["wall_markers"][0]["last_species"])

    def test_it_is_promoted_to_a_human_readable_warning(self):
        """Rule 13 again: the field is read by code, warnings[] is read by a human."""
        res = collect_mod.collect_p5(self.store, "P5")
        joined = " ".join(res.get("warnings") or [])
        self.assertIn("p5_wall_wall_exhausted", joined)
        self.assertIn("must not sit in the denominator", joined)

    def test_no_marker_means_no_warning(self):
        """0-o.4 rule 4: the check must be able to pass, or it says nothing when it fires."""
        os.remove(os.path.join(self.job, "wall_exhausted.t21.json"))
        res = collect_mod.collect_p5(self.store, "P5")
        self.assertEqual([], res["wall_markers"])
        self.assertFalse([w for w in (res.get("warnings") or []) if "p5_wall_" in w])


class TestP6NowSmokesBeforeProduction(unittest.TestCase):
    """🔴 [critic10] P6 never called `sei_qc_smoke` — P1b, P5, P1, endpoint_prep and U56 all
    do, before their first production input. P6 was simply never retrofitted when ADR-105/108
    introduced the pattern, and the cost was this round's ENTIRE kappa measurement: the anchors
    ran on an unvalidated deck and produced zero usable data. kappa is the single dominant
    variable of the 5-month schedule."""

    def test_p6_smokes_before_it_generates_its_input(self):
        with open(os.path.join(context.PKG_ROOT, "payload", "P6.sh"), errors="replace") as fh:
            src = fh.read()
        self.assertIn("sei_qc_smoke", src)
        self.assertLess(src.index("sei_qc_smoke"), src.index("sei_qc_input"),
                        "the smoke must run BEFORE the production input is generated")

    # NOTE: the general form of this check ("every payload that generates QC input must smoke
    # first") lived here as a fixed six-name list. 🔴 critic10 spent real effort failing to
    # FIND it -- nothing about this filename suggests it -- and pointed out that a fixed
    # enumeration would not catch a seventh payload. Both were right, and both are the same
    # defect I keep fixing elsewhere: a check that covers the instances someone remembered.
    # It now lives in `test_payload_shell.py` (the file about payload shells) and DERIVES the
    # rule by scanning `payload/*.sh` instead of listing names.


if __name__ == "__main__":
    unittest.main()
