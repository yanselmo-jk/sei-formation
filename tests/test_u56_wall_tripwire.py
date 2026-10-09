"""[critic14, linear-hopping-frog Track A] U56.sh had no SIGTERM trap / wall tripwire, unlike
P5.sh/endpoint_prep.sh -- a wall-cap kill (ADR-114, 48h) would die before any
`_write_terminal`/`sei_terminal_from_logs` call, landing back on `outcome: absent` (the exact
state the terminal_status fix removes) which is never retried, so the item silently stalls.

Static source check, same pattern as `test_p5_wall_tripwire.py` (which is itself a static
check, not a live-kill test) -- the project's own precedent for this exact feature.
"""

import os
import re
import unittest

import context  # noqa: F401

U56 = os.path.join(context.PKG_ROOT, "payload", "U56.sh")


class TestU56HasAWallTripwire(unittest.TestCase):
    def setUp(self):
        with open(U56, errors="replace") as fh:
            self.src = fh.read()

    def test_a_sigterm_trap_exists(self):
        self.assertIn("trap '_write_terminal \"wall_exhausted\"", self.src)
        self.assertIn("' TERM", self.src)

    def test_the_marker_names_the_stage_that_was_running(self):
        self.assertIn("U56_CURRENT_STAGE", self.src)

    def test_the_trap_is_armed_before_any_qc_stage_and_disarmed_after_the_last_one(self):
        """A trap armed too late or disarmed too early is worse than none -- it looks safe."""
        trap_on = self.src.index("trap '_write_terminal \"wall_exhausted\"")
        first_stage = min(m.start() for m in re.finditer(r"sei_stage ", self.src))
        trap_off = self.src.index("trap - TERM")
        last_stage = max(m.start() for m in re.finditer(r"sei_stage ", self.src))
        self.assertLess(trap_on, first_stage, "trap armed after the first sei_stage call")
        self.assertGreater(trap_off, last_stage, "trap disarmed before the last sei_stage call")

    def test_every_sei_stage_call_is_preceded_by_a_current_stage_assignment(self):
        """Otherwise the trap's marker says 'unknown' for a stage that WAS identifiable."""
        # every `sei_stage <name>` call site in this payload sets U56_CURRENT_STAGE on the
        # line(s) immediately before it (allowing intervening blank lines/comments).
        lines = self.src.splitlines()
        offenders = []
        for i, line in enumerate(lines):
            if re.match(r"\s*(&&\s*)?sei_stage ", line):
                window = "\n".join(lines[max(0, i - 3):i])
                if "U56_CURRENT_STAGE=" not in window:
                    offenders.append((i + 1, line.strip()))
        self.assertEqual([], offenders)

    def test_the_marker_says_why_it_exists(self):
        self.assertIn("outcome: absent", self.src)


if __name__ == "__main__":
    unittest.main()
