"""[§39.78] Two named unit costs, and the missing one is allowed to be missing.

🔴 `u_cheap` is what B1's sizing rule consumes: `N1 = min(600, remaining / (u_measured *
r_composite))` asks how many species we can AFFORD, and affording a species means obtaining its
THERMOCHEMISTRY — a free energy needs zero-point and thermal corrections, which come ONLY from
the frequency stage. **An opt-only cost is not a cheaper estimate of it; it is a different
quantity**, and publishing it under this name is `AGREEMENT IS NOT IDENTITY` (§39.76).

🔒 This round every P5 frequency stage died on the EpsInf sentinel, so u_cheap's denominator is
EMPTY. The ruling is not to keep the opt-only number under the wrong name, and not to let the
statistic vanish unlabelled — it is to give the right number its own name (`u_opt`) and let the
absent one be absent, loudly.
"""

import unittest

import context  # noqa: F401
from sei_pilot.criteria import p5

L = p5.LEVEL_CHEAP


def _row(sid, core_h, freq_ran, level=None):
    stages = ({"completed": ["opt", "scf", "freq", "thermo"], "missing": []} if freq_ran
              else {"completed": ["opt", "scf"], "missing": ["freq", "thermo"]})
    return {"id": sid, "level": level or L, "multiplicity": 1, "converged": True,
            "core_hours": core_h, "stages_completed": stages}


class TestTheTwoQuantitiesAreSeparate(unittest.TestCase):
    def test_u_cheap_counts_only_species_that_completed_freq(self):
        rows = p5.normalize_rows([_row("a", 40.0, False), _row("b", 70.0, True)])
        u = p5.unit_costs(rows)
        self.assertEqual(70.0, u["u_cheap_core_hours"])
        self.assertEqual(1, u["u_cheap_n"])

    def test_u_opt_counts_the_optimisations_and_is_a_different_number(self):
        rows = p5.normalize_rows([_row("a", 40.0, False), _row("b", 70.0, True)])
        u = p5.unit_costs(rows)
        self.assertEqual(55.0, u["u_opt_core_hours"])
        self.assertEqual(2, u["u_opt_n"])
        self.assertNotEqual(u["u_cheap_core_hours"], u["u_opt_core_hours"],
                            "if these ever coincide it is arithmetic, not identity")


class TestAnEmptyDenominatorIsLabelledNotLost(unittest.TestCase):
    """🔴 The objection this answers: a vanished statistic reads as 'P5 lost its cost data'.
    That reading is only available if the absence is UNLABELLED."""

    def setUp(self):
        self.u = p5.unit_costs(p5.normalize_rows(
            [_row("a", 40.0, False), _row("b", 60.0, False)]))

    def test_u_cheap_is_null_with_its_reason(self):
        self.assertIsNone(self.u["u_cheap_core_hours"])
        self.assertIn("EMPTY denominator", self.u["u_cheap_reason"])
        self.assertIn("EpsInf", self.u["u_cheap_reason"])

    def test_u_opt_is_populated_beside_it(self):
        """The pairing is what makes the absence unmisreadable."""
        self.assertEqual(50.0, self.u["u_opt_core_hours"])

    def test_both_carry_their_definitions(self):
        self.assertIn("opt+freq", self.u["u_cheap_definition"])
        self.assertIn("NOT u_cheap", self.u["u_opt_definition"])


class TestUnknownIsNotFalse(unittest.TestCase):
    """🔴 Rule 18 again: a row with no `stages_completed` record does not establish that freq
    did NOT run. It is counted in neither numerator rather than assumed absent."""

    def test_a_row_without_a_stage_record_is_excluded_from_u_cheap_and_flagged(self):
        rows = p5.normalize_rows([{"id": "x", "level": L, "multiplicity": 1,
                                   "converged": True, "core_hours": 50.0}])
        u = p5.unit_costs(rows)
        self.assertIsNone(u["u_cheap_core_hours"])
        self.assertEqual(1, u["n_stage_record_missing"])
        self.assertIn("UNKNOWN rather than false", u["_unknown_note"])


class TestAssembledTotalsMustDeclareThemselves(unittest.TestCase):
    """🔴 [§39.78 condition] Once the EpsInf fix lands, u_cheap will be ASSEMBLED — an
    optimisation measured now plus a frequency measured later on the stored geometry. That sum
    is legitimate (same geometry, same level) but is NOT an end-to-end measurement: the halves
    may run under different caps, giving a total no single configuration would reproduce."""

    def test_the_flag_exists_and_defaults_to_false(self):
        u = p5.unit_costs(p5.normalize_rows([_row("a", 40.0, True)]))
        self.assertIs(False, u["assembled"])

    def test_the_requirement_travels_with_the_record(self):
        u = p5.unit_costs(p5.normalize_rows([_row("a", 40.0, True)]))
        for token in ("assembled: true", "cap record", "not a single-run measurement"):
            self.assertIn(token, u["_assembly_note"])


class TestTheVerdictLabelNoLongerImpliesOptPlusFreq(unittest.TestCase):
    def test_the_statistic_says_it_is_opt_only(self):
        v = p5.verdict(p5.normalize_rows([_row("a", 40.0, False)]))
        self.assertIn("opt-only", v["representative_statistic"])
        self.assertIn("NOT the complete opt+freq cost", v["representative_statistic"])


if __name__ == "__main__":
    unittest.main()
