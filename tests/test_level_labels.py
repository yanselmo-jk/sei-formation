"""[critic10] Level labels must describe what actually ran.

🔴 They were literals and all three fields of both were wrong:
```
was  wB97X-V/def2-TZVPPD/SMD     config says wB97XD, and the solvent is PCM eps 18.5
was  wB97X-D3/def2-TZVP/SMD      config says wB97XD / def2-TZVPD
now  wB97XD/def2-TZVPPD/PCM(eps=18.5)
now  wB97XD/def2-TZVPD/PCM(eps=18.5)
```
🔴 The `/SMD` is the part that matters, and it is not cosmetic. This project spent **14,464
core-h** on runs whose solvent was not what the label said (acetonitrile, eps 35.7 — ADR-066/067),
and ADR-108 then moved production to PCM eps 18.5. These strings go OUT, into the reply a human
reads. A label saying SMD after that is the same confusion written into the output.

🔒 The fix is derivation, not correction: a literal cannot help but drift, and correcting it
would only reset the clock on the next drift.
"""

import unittest

import context  # noqa: F401
from sei_pilot import config
from sei_pilot.criteria import p5


class TestLabelsAreDerivedFromTheSingleSource(unittest.TestCase):
    def setUp(self):
        self.g = config.load("qc_levels.json")["gaussian16"]

    def test_each_field_matches_config(self):
        for key, label in (("level2", p5.LEVEL_PRIMARY), ("level1", p5.LEVEL_CHEAP)):
            block = self.g[key]
            self.assertIn(block["functional"], label, key)
            self.assertIn(block["basis_real_name"], label, key)

    def test_the_solvent_in_the_label_is_the_solvent_in_the_policy(self):
        """🔴 THE ONE THAT COST 14,464 core-h. The label's solvent is read from the same
        `solvent_policy` the deck reads, so it cannot name a solvent the run did not use."""
        policy = self.g["solvent_policy"]
        self.assertEqual("pcm_numeric", policy["model"],
                         "if the policy changes, this test should be the first thing to say so")
        self.assertIn("PCM(eps=%s)" % policy["epsilon"], p5.LEVEL_PRIMARY)
        self.assertNotIn("SMD", p5.LEVEL_PRIMARY)
        self.assertNotIn("SMD", p5.LEVEL_CHEAP)

    def test_the_old_literals_are_gone(self):
        """Pinned by value: these exact strings appeared in shipped replies and must not
        return by anyone 'restoring' a constant."""
        for stale in ("wB97X-V/def2-TZVPPD/SMD", "wB97X-D3/def2-TZVP/SMD"):
            self.assertNotEqual(stale, p5.LEVEL_PRIMARY)
            self.assertNotEqual(stale, p5.LEVEL_CHEAP)

    def test_the_two_levels_are_distinguishable(self):
        """They are used as dict KEYS to match rows by level — if they ever collapse to one
        string the cost ratio silently compares a level with itself."""
        self.assertNotEqual(p5.LEVEL_PRIMARY, p5.LEVEL_CHEAP)


class TestSolventLabelReflectsEachPolicy(unittest.TestCase):
    def test_pcm_numeric_carries_its_epsilon(self):
        self.assertEqual("PCM(eps=18.5)",
                         p5._solvent_label({"model": "pcm_numeric", "epsilon": 18.5}))

    def test_smd_is_still_nameable_if_the_policy_ever_says_so(self):
        self.assertEqual("SMD", p5._solvent_label({"model": "smd_descriptors"}))

    def test_an_undecided_policy_says_so_rather_than_guessing(self):
        """🔴 Rule 18 in the label layer: an unset policy must not print as though a solvent
        had been chosen. `null` is C-5's refusal state, not a default."""
        self.assertEqual("solvent-undecided", p5._solvent_label({"model": None}))
        self.assertEqual("solvent-undecided", p5._solvent_label(None))

    def test_a_missing_epsilon_is_visible_rather_than_omitted(self):
        self.assertEqual("PCM(eps=?)", p5._solvent_label({"model": "pcm_numeric"}))


class TestFallbackCannotMasqueradeAsAMeasurement(unittest.TestCase):
    def test_an_unresolvable_label_is_marked(self):
        """If config were unreadable at import, the label must announce that rather than
        printing a plausible-looking level string."""
        self.assertIn("[LABEL-UNRESOLVED]", p5._safe_label("nope", "x/[LABEL-UNRESOLVED]"))


if __name__ == "__main__":
    unittest.main()
