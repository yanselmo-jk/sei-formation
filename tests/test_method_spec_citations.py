"""Every `§39.x` cited in `src/` must resolve to a real heading in `02_METHOD_SPEC.md`.

🔴 WHY THIS EXISTS: this exact bug class landed twice in one session. First, proposer9/
proposer10 collided on a section number. Then 02_METHOD_SPEC.md's own renumbering (§39.110→113,
§39.111→114, §39.112→115) left citations half-migrated across five files -- worse than a
dangling reference, since every OLD number still existed as a real heading pointing at an
unrelated ruling, so a reader chasing e.g. `qc_levels.json`'s `nosymm` rationale landed on a
species-naming correction and concluded the rationale was undocumented (critic14, 2026-08-21).

Scoped to `src/` only, and only citations that carry the `§` mark -- a bare `39.113` collides
with `§R39.x` (a DIFFERENT numbering series, 03_COMPUTE_PLAN.md's own) and with ordinary numeric
literals (e.g. `units.py`'s atomic mass table has a `39.96259098`). The `§` mark is what every
citation THIS project's own comments actually use, so requiring it costs no real coverage.

🔴 KNOWN LIMIT, stated so nobody over-reads a green run: this is an EXISTENCE check only --
`39.X in headings` -- not a content check. `§39.110` itself is a real, live heading (a
proposer9 species-naming correction) even though it is ALSO the number the U56-2 read-out used
to live at before the renumbering that created §39.113/114/115 -- the original collision this
whole cleanup exists because of. A citation that survives this test because its number happens
to exist COULD still point at the wrong section's content if a future renumbering repeats the
same collision shape. This test cannot see that; a human reading the cited section's title
against the citing comment's claim is still required for that.
"""

import collections
import os
import re
import unittest

import context  # noqa: F401

DOC = os.path.join(context.REPO_ROOT, "docs", "02_METHOD_SPEC.md")
SRC = context.PKG_ROOT

HEADING_RE = re.compile(r"^##\s+§?(\d+\.\d+[a-z]?)\b")
CITATION_RE = re.compile(r"§39\.(\d+[a-z]?)")


def _heading_counts():
    """{number: count} across ALL headings in the doc (39.x and otherwise), full token
    including any letter suffix as one key -- `39.2` and `39.2b` are DIFFERENT sections, not
    a duplicate of each other."""
    counts = collections.Counter()
    with open(DOC, errors="replace") as fh:
        for line in fh:
            m = HEADING_RE.match(line)
            if m:
                counts[m.group(1)] += 1
    return counts


def _headings():
    return set(_heading_counts())


def _citations():
    """[(path, line_no, cited_number), ...] for every §39.x in src/*.py/.sh/.json."""
    out = []
    for dirpath, dirnames, filenames in os.walk(SRC):
        dirnames[:] = [d for d in dirnames if d not in ("__pycache__", "vendor")]
        for fn in sorted(filenames):
            if not fn.endswith((".py", ".sh", ".json")):
                continue
            path = os.path.join(dirpath, fn)
            with open(path, errors="replace") as fh:
                for i, line in enumerate(fh, 1):
                    for m in CITATION_RE.finditer(line):
                        out.append((path, i, "39." + m.group(1)))
    return out


class TestEveryCitationResolvesToARealHeading(unittest.TestCase):
    def test_no_stale_or_invented_section_numbers(self):
        headings = _headings()
        offenders = [(os.path.relpath(p, context.REPO_ROOT), ln, num)
                    for p, ln, num in _citations() if num not in headings]
        self.assertEqual(
            [], offenders,
            "these §39.x citations in src/ do not match any heading in 02_METHOD_SPEC.md -- "
            "either the section was renumbered and the citation was missed, or the number was "
            "typed wrong. Both are worse than a dangling reference: the old/wrong number often "
            "still exists as a heading, pointing a reader at an unrelated ruling.")

    def test_the_check_actually_finds_citations(self):
        """Rule 18 / 0-o.4: a check that silently matches nothing passes forever."""
        self.assertGreater(len(_citations()), 50)

    def test_the_check_does_not_confuse_the_compute_plan_series(self):
        """§R39.x (03_COMPUTE_PLAN.md's own numbering) must never be read as a §39.x hit --
        confirmed against a real line shape this codebase actually has."""
        self.assertEqual([], CITATION_RE.findall("engineer7 §R39.15 4a"))

    def test_the_check_does_not_confuse_a_numeric_literal(self):
        """units.py's atomic mass table has `\"Ca\": 39.96259098` -- not a citation."""
        self.assertEqual([], CITATION_RE.findall('"Ca": 39.96259098,'))


class TestEveryHeadingNumberIsUnique(unittest.TestCase):
    """[critic14] The existence check above cannot catch the failure mode that actually
    happened first: two DIFFERENT sections sharing the same number (proposer9/proposer10's
    collision at §39.110, resolved by moving one of them to §39.113/114/115). A citation
    resolving to a real-but-wrong heading is invisible to "does this number exist" -- but a
    number existing TWICE is directly, cheaply decidable from the doc alone, no citation
    needed. Existence (above) + uniqueness (here) is the pair; neither alone closes the class."""

    def test_no_section_number_is_used_for_two_different_headings(self):
        counts = _heading_counts()
        dupes = {num: n for num, n in counts.items() if n > 1}
        self.assertEqual(
            {}, dupes,
            "these section numbers each head MORE THAN ONE section in 02_METHOD_SPEC.md -- "
            "any citation to one of them is ambiguous about which content it means, and the "
            "next renumbering to resolve the collision risks leaving citations pointing at "
            "the wrong one again (exactly what happened at §39.110/111/112).")

    def test_the_check_actually_finds_headings(self):
        """Rule 18 / 0-o.4: a check that silently matches nothing passes forever."""
        self.assertGreater(len(_heading_counts()), 100)

    def test_the_check_treats_a_letter_suffix_as_a_different_section(self):
        """§39.2 and §39.2b are different sections, not one section counted twice."""
        counts = collections.Counter()
        for line in ("## 39.2 Question 1\n", "## 39.2b Question 2\n"):
            m = HEADING_RE.match(line)
            counts[m.group(1)] += 1
        self.assertEqual({"39.2": 1, "39.2b": 1}, dict(counts))


if __name__ == "__main__":
    unittest.main()
