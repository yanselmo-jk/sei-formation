"""ADR-090 item 4 -- THE REACH TEST.

A guard's EXISTENCE, its CORRECTNESS, and its REACH are three separate properties
(ADR-090), and this project was only ever measuring the first two: `bound.py::partition()`,
`p1b.py::cost_ratios()`, `payload/P1.sh`'s fallback, and `p1.py::evaluate_irc` were each
correct in isolation, each tested in isolation, each cited its own historical incident --
and each shipped with zero callers, because no test anywhere asserted a guard is REACHED
from the code it protects. This file is that assertion, built once, as the template for
every guard this project adds from here on.

🔴 [ADR-092] Detection is by AST `Call`, never by name-occurrence (grep or substring). The
sweep that FOUND this whole class of defect fell to it: `criteria/p1.py:283`'s dict KEY
`"irc_verdict": ir.get("verdict")` was matched as if it were a call to `guards.irc_verdict`,
which certified an unreached, unenforced C-2 as "wired". `TestExpectedReachedGuardsAreActually
Called.test_a_dict_key_with_the_same_spelling_does_not_count_as_a_call` pins exactly that
trap so it cannot reopen silently.

Mechanism (i): every guards.py entry-point function has >= 1 real external caller, or a
named, reasoned entry in one of the exemption buckets below (ADR-090 ruling item 3: category
(B) gets a named blocking entry; category (A) is a defect and stays visible via `skipTest`
rather than a passing assertion that would hide it).

Mechanism (ii) (ADR-091): `execution_audit` reaches EXACTLY the 5 collectors that produce
`stage_events.jsonl`/`executions.jsonl` telemetry, measured the same way `collect.py`'s own
docstring now claims -- so the two cannot silently diverge again the way `collect.py:89`'s
"every collector" claim once did.
"""

import ast
import os
import re
import unittest

import context  # noqa: F401

PKG = context.PKG_ROOT
SEI_PILOT_DIR = os.path.join(PKG, "sei_pilot")
PAYLOAD_DIR = os.path.join(PKG, "payload")
GUARDS_PATH = os.path.join(SEI_PILOT_DIR, "guards.py")
COLLECT_PATH = os.path.join(SEI_PILOT_DIR, "collect.py")

#: `<<'PY' ... PY` heredocs. ADR-090 ruling item 4: this IS the shell bridge -- C-8's
#: precondition and C-12's fallback are wired through it, not a new mechanism.
#: 🔴 Matches `<<'PY'` AND its disambiguated variants (`<<'PYBRACKET'`, `<<'PYIRC'`, ...).
#: A shell script cannot nest two heredocs sharing one delimiter, so a payload that runs
#: several Python blocks MUST rename some of them -- and an earlier version of this pattern
#: matched only the bare `PY`, which made every renamed block INVISIBLE to the reach check.
#: 🔒 That is this file's own failure mode turned on itself: a guard against unreached code
#: that silently stops seeing some of the code. The delimiter convention is "starts with PY".
_HEREDOC_PY_RE = re.compile(r"<<'(PY[A-Z0-9_]*)'\n(.*?)\n\1\n", re.S)


def _iter_py_files(root, exclude=()):
    exclude = set(os.path.abspath(p) for p in exclude)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for fn in filenames:
            if not fn.endswith(".py"):
                continue
            path = os.path.abspath(os.path.join(dirpath, fn))
            if path not in exclude:
                yield path


def _called_names(path):
    """Every name invoked as a real `ast.Call` in this file -- `obj.NAME(...)` or bare
    `NAME(...)`. Never a string, a dict key, or any other name-shaped occurrence (ADR-092)."""
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Attribute):
                names.add(f.attr)
            elif isinstance(f, ast.Name):
                names.add(f.id)
    return names


def _guards_functions():
    with open(GUARDS_PATH) as fh:
        tree = ast.parse(fh.read())
    return [n.name for n in tree.body
           if isinstance(n, ast.FunctionDef) and not n.name.startswith("_")]


def _called_names_in_heredocs(sh_path):
    """Every name invoked as a real `ast.Call` inside this shell script's `<<'PY'` heredoc
    blocks (ADR-090 ruling item 4's bridge). A heredoc that fails to parse as Python is a
    real defect in the script, not something to swallow -- it raises here, same as `guards`'
    own "an ERROR is a broken experiment, not a clean miss" convention."""
    with open(sh_path) as fh:
        text = fh.read()
    names = set()
    for _delim, block in _HEREDOC_PY_RE.findall(text):
        tree = ast.parse(block, filename=sh_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                f = node.func
                if isinstance(f, ast.Attribute):
                    names.add(f.attr)
                elif isinstance(f, ast.Name):
                    names.add(f.id)
    return names


def _external_callers_of(name):
    """Every `.py` file under `sei_pilot/` (production source, NOT `tests/`, and not
    `guards.py` itself) whose AST actually calls `name` -- PLUS every `payload/*.sh` whose
    embedded `<<'PY'` heredoc does, since that heredoc bridge is how a guard reaches a shell
    payload (ADR-090 ruling item 4). Grep alone cannot tell a call from a name occurrence
    inside a heredoc either -- the same AST discipline applies there."""
    hits = [p for p in _iter_py_files(SEI_PILOT_DIR, exclude={GUARDS_PATH})
           if name in _called_names(p)]
    if os.path.isdir(PAYLOAD_DIR):
        for fn in sorted(os.listdir(PAYLOAD_DIR)):
            if fn.endswith(".sh"):
                path = os.path.join(PAYLOAD_DIR, fn)
                if name in _called_names_in_heredocs(path):
                    hits.append(path)
    return hits


#: Internal helpers of another guards.py entry point -- their reach is judged THROUGH that
#: entry point, not independently. Forcing an external caller onto one of these produces a
#: false positive that teaches people to ignore this test (HANDOFF §0.2b-6 / ADR-091's
#: explicit warning about `guards.heavy_atoms`).
INTERNAL_HELPERS = {
    "classify_indeterminate": ("helper of irc_verdict -- splits an `indeterminate` into its "
                               "CHEMICAL / BUDGET / UNKNOWN cause class so that 1/p is only "
                               "ever computed over the chemical denominator; reached through "
                               "irc_verdict, not independently"),
    "scan_barrier_ev": ("helper of gscan2_decision (each direction's apparent barrier, "
                        "measured from that profile's OWN first frame) -- its reach is "
                        "judged through gscan2_decision"),
    "irc_direction_ok": "helper of irc_verdict (one IRC direction's clauses)",
    "heavy_atoms": "helper of coplanarity (ADR-091: do not force a caller onto this one)",
    "coplanarity": ("helper of perturb_out_of_plane and ts_precondition/"
                    "require_ts_precondition -- NOT independently 'wired' despite ADR-092's "
                    "inventory listing it as such; verified by AST here to have zero direct "
                    "external callers. Its real entry points (perturb_out_of_plane, "
                    "require_ts_precondition) are tracked below on their own merits."),
    "endpoint_report": "helper of ts_precondition (one endpoint's C-8 clauses)",
    "ts_precondition": ("helper of require_ts_precondition -- that RAISING wrapper's own "
                        "docstring says 'call this from any code path that actually submits "
                        "a TS search', not the bare decision function"),
    "single_ended_ts_precondition": ("helper of require_single_ended_ts_precondition -- "
                                     "same wrapper/decision split as ts_precondition, for "
                                     "the single-ended (reactant-only) C-8 of §39.32 "
                                     "Candidate B / §39.39(e)"),
}

#: 🔴 [ADR-090 ruling item 3] Category (B): legitimately deferred, zero consumer ANYWHERE
#: (not even a wrong one) -- each entry names the blocking NOT-STARTED work.
DEFERRED_NO_CONSUMER_YET = {
    # 🔴 B+ itself (the two terminal optimisations) is NOT wired into the payload yet -- this
    # decides whether two ALREADY-OPTIMISED endpoints agree, and C-2 consumes its output via
    # `bplus.agreement`. Until the payload runs those optimisations, `agreement` is only ever
    # set by fixtures, which is why the class it produces had to be pinned by test.
    "tripwire_record": "B0 collector wiring (ADR-090 item 9)",
    "detect_tripwire_aborts": "B0 collector wiring (ADR-090 item 9)",
    "spend_core_hours": "B0 collector wiring (ADR-090 item 9)",
    "derived_or_null": ("a generic single-reason null-on-nonconvergence helper; C-1's actual "
                        "incident (cost_ratios) needed a two-reason design (missing vs "
                        "non-convergent) and calls unconverged_inputs directly instead -- no "
                        "other current call site needs the generic single-reason form"),
    "require_nosymm_if_needed": "B-2's guard; blocking entry below, in guards.py itself",
    "nosymm_required_job_types": "helper of require_nosymm_if_needed, same blocking entry",
    # 🔴 [G-SCAN, §39.45(a)/§39.50] 불연속 gate 의 판정 함수. 정확하고 테스트돼 있으나
    #    **생산 호출자가 0곳**이다 — 판정을 만들어야 할 GFN2 양방향 사전 stage 가 아직
    #    없기 때문이다(coder10 인계 항목). `payload/U56.sh` 는 이미 그 판정문
    #    (`gscan_verdict.json`)을 **요구**하고, 없으면 단끝단 arm 을 발주하지 않고 거부한다
    #    (§39.47(a): DFT scan 은 GFN2 판정을 상속받아야 하며, 상속할 판정이 없는 guess 는
    #    ungated 다). ⟹ 지금 상태는 "gate 가 조용히 통과시킨다"가 아니라 "arm 이 안 돈다"이고,
    #    그것이 옳은 실패 방향이다. 사전 stage 가 붙는 순간 이 항목은 EXPECTED_REACHED 로
    #    옮겨야 하고, 이 테스트가 그때 RED 로 알려준다.
    # 🔴 [§39.124 Ruling 3/A2, coder15] `minimum_distinctness`/`structural_distinctness`
    # implement the RULED formula (absolute 0.025 A floor + self-calibrating relative check
    # against a run's own median consecutive-point delta) for "is a declared IRC minimum real,
    # or a repeat of §39.116(d)'s stopping-criterion artifact". Zero production callers:
    # `irc_direction_ok`'s branch (a) has no path-frame/preceding-point geometry input today
    # (it only ever received SCALAR direction data -- n_points, energy, completion, bplus/
    # reactant_match dicts, never raw IRC path frames), so there is nowhere to wire an
    # auto-decision from without a larger, separate plumbing change nobody has scoped yet.
    # Ruling 3 itself only asks for a HUMAN READ on a suspicious delta, not an automatic gate --
    # implemented, tested, and ready for whoever wires the path-frame input through.
    "minimum_distinctness": ("§39.124 Ruling 3/A2 -- no caller supplies path-frame geometry to "
                             "`irc_direction_ok` yet; a human-in-the-loop check per the ruling's "
                             "own text, not an automatic gate"),
    "structural_distinctness": "helper of minimum_distinctness, same blocking entry",
}

#: 🔴 Category (A): KNOWN, ALREADY-DOCUMENTED, OPEN defects -- queued by ADR-090 §5, not yet
#: fixed. Declared here (never a silent pass) so this file stays the live map of what remains.
KNOWN_OPEN_DEFECTS = {
}

#: 🔴🔴 A FIFTH BUCKET, DELIBERATELY DISTINCT FROM `KNOWN_OPEN_DEFECTS`: wiring this guard is
#: not an implementation task, it is a METHODOLOGY/SCOPE decision above a coder's pay grade,
#: and `KNOWN_OPEN_DEFECTS` reads as "just wire it" -- the next person who reads that bucket
#: WILL wire it and halt the pilot. `require_ts_precondition` on the actual shipped
#: `inputs/li_ec_radical_{reactant,product}.xyz` (whose own header says "GUESS GEOMETRY
#: (idealized, not optimized)") RAISES EVERY TIME, because no pre-optimisation step exists
#: anywhere in `payload/P1.sh` to give it real `optimised`/`converged`/`n_imag` data --
#: confirmed live in `tests/test_guards.py::test_the_actual_shipped_p1_inputs_raise`.
#: 🔴 SECOND, INDEPENDENT VIOLATION: P1.sh's CREST step refines `reactant.xyz` ONLY
#: (`cp crest_best.xyz reactant.xyz`) -- `product.xyz` is never touched, so even an
#: optimistic reading has the two endpoints prepared at DIFFERENT levels, which C-8's "at
#: the SAME level" clause forbids independently of whether either is optimised.
#: Escalated to the lead (proposer + engineer scope: is a pre-optimisation stage the right
#: remedy, at what level, does B0-F still fit the approved core-h reference). DO NOT WIRE
#: THIS ONTO P1's LIVE LAUNCH PATH until that ruling lands.
#: 🟢 [C-8-1] THAT RULING LANDED (lead, 2026-08-20): wire it; the refusal on today's
#: inputs is the intended behaviour (P1 recommended out of this round; endpoint_prep
#: reactant+product produce the certification a future round will feed it). The paragraph
#: above is kept as the record of WHY this sat unwired for two rounds.
BLOCKED_ON_DECISION = {
    # [C-8-1] `require_ts_precondition` moved OUT of this bucket: the ruling this bucket was
    # waiting for LANDED (lead, 2026-08-20 -- "wire it; P1 refusing on today's inputs is the
    # correct behaviour; P1 is recommended out of this round"). It is now wired onto
    # payload/P1.sh's live QST2 launch path and tracked in EXPECTED_REACHED below.
}

#: Confirmed reached, verified by this file's own AST check below -- asserted POSITIVELY so
#: a revert (or a future refactor that quietly drops the call) is caught immediately.
#: 🔴 [§39.63] `bracket_check` reaches production through `payload/U56.sh`'s heredoc bridge
#: (ADR-090 ruling item 4), which `_external_callers_of` counts as a caller.
EXPECTED_REACHED = {
    # 🟢 MOVED HERE from DEFERRED_NO_CONSUMER_YET once its producer was built: the GFN2
    # bidirectional pre-stage in `payload/U56.sh` now renders the verdict in-job before any
    # DFT is ordered. This test is what forced the move -- exactly its purpose.
    "gscan2_decision": ("payload/U56.sh's <<'PYGSCAN' heredoc, run BEFORE the DFT scan chain "
                        "(39.45(a) G-SCAN-1 / 39.47(a): the gate runs at GFN2 where the guess "
                        "is made and where 24 points cost nothing)"),
    "classify_engine_failure": ("payload/U56.sh's <<'PYGSCAN' heredoc -- maps a parsed xtb "
                                "failure kind onto the §39.69 `engine` class, or None so the "
                                "caller falls back to `unknown` rather than sweeping an "
                                "unrecognised failure into a class it has not earned"),
    "parse_irc_path_frames": ("payload/U56.sh's <<'PYBPLUSPICK' heredoc -- pairs each IRC "
                              "path point with the orientation block preceding its marker, so "
                              "B+ optimises from a geometry that is actually on the path"),
    "bplus_agreement": ("payload/U56.sh's <<'PYBPLUS' heredoc -- renders the B+ verdict from "
                        "the two terminal optimisations; C-2 then consumes `bplus.agreement` "
                        "for condition 7 branch (b)"),
    "reactant_match": ("payload/U56.sh's <<'PYBPLUS' heredoc, called once for `mid` and once "
                       "for `last` -- §39.124 finding (c): the missing half of condition 7 "
                       "('the reverse endpoint must match the certified reactant'), which "
                       "`bplus_agreement` above never checked because it only ever compares "
                       "the two B+ points against EACH OTHER. WHICH point condition 7 binds is "
                       "RULED (§39.124 Ruling 2/A1): `last` only -- `mid` is still computed as "
                       "diagnostic data but must not be ANDed into the verdict. 🟢 BOTH "
                       "tolerances are now ruled (`REACTANT_MATCH_TOLERANCE_ANG`=0.05 A, "
                       "`BPLUS_ENERGY_TOLERANCE_EV` reused) and `match` DOES reach `True` in "
                       "production (critic16, 04_REVIEW_LOG.md 27th batch, verified by "
                       "execution against the real returned reverse-arm data: 0.0005 A / "
                       "4.13e-4 eV, both within tolerance)."),
    "bplus_sample_points": ("payload/U56.sh's <<'PYBPLUSPICK' heredoc -- picks the two IRC "
                            "path points (last + arc-length midpoint) the optimisations start "
                            "from"),
    "bracket_check": ("payload/U56.sh's <<'PYBRACKET' heredoc, run BEFORE the spectator test "
                      "and before any IRC is ordered (39.63: it is the cheapest gate and the "
                      "only one with a demonstrated hit -- P1's saddle had the breaking bond "
                      "at 3.184 A against a certified bracket of [1.405, 2.503]). "
                      "⚠ It is INAPPLICABLE on a single-ended arm with no certified product "
                      "(R-B by design, 39.39(d)); that case is recorded and counted rather "
                      "than treated as a pass, so 'never applicable' cannot masquerade as "
                      "'never fires'."),
    "require_ts_precondition": ("payload/P1.sh's <<'PY' heredoc, BEFORE the QST2 input is "
                                "generated (C-8-1, lead ruling landing ADR-090 item 5) -- "
                                "reached via the shell bridge, same shape as "
                                "fallback_decision. ⚠ H-2 satisfiability: on today's inputs "
                                "(no endpoint certification record exists anywhere) this "
                                "gate REFUSES every time, by design -- the wiring that lets "
                                "it pass (reading endpoint_prep's outputs) is next-round "
                                "methodology scope. The positive fixture lives at guard "
                                "level (tests/test_guards.py GOOD)."),
    "perturb_out_of_plane": ("payload/endpoint_prep.sh's <<'PY' heredoc, once, before stage 1 "
                            "(C-9, ADR-099) -- reached via the shell bridge, same shape as "
                            "fallback_decision below"),
    "unconverged_inputs": "criteria/p1b.py::cost_ratios (C-1, ADR-088)",
    "irc_verdict": ("criteria/p1.py::evaluate_p1 (C-2, ADR-090/092). 🔴 [critic16, 27th review "
                    "batch] `irc_direction_ok`'s §39.124 Ruling 2/A1 reactant-match consult "
                    "(the `direction[\"reactant_match\"]` opt-in field, guards.py:~267-350) has "
                    "NO LIVE PRODUCER TODAY -- `evaluate_p1`, the only caller reaching this "
                    "function, does not supply the key (P1 has no mapping/reactant wiring and "
                    "is permanently excluded, ADR-112), so the clause is skipped on every "
                    "production path that currently exists. Recorded here explicitly rather "
                    "than left implicit, per critic16's instruction, since `irc_direction_ok` "
                    "itself IS reached (via `irc_verdict`) and cannot also carry its own "
                    "DEFERRED_NO_CONSUMER_YET entry -- this sub-feature's producer gap lives in "
                    "this reason string instead. Implemented and tested (tests/test_bplus.py "
                    "`TestConditionSevenReactantMatchBindsBothBranches`); wiring a real producer "
                    "(e.g. into a future U-56 verdict function) is a separate, unscoped item."),
    "symmetric_placement_flags": "conformers.py::symmetry_trace (pre-existing)",
    "fallback_decision": ("payload/P1.sh's <<'PY' heredoc, right after the QST2 stage "
                          "(C-12, ADR-090 item 6) -- reached via the shell bridge, not a "
                          "sei_pilot/*.py caller; see test_p1_c12_fallback.py for the "
                          "real-bash end-to-end proof"),
    "require_single_ended_ts_precondition": (
        "payload/U56.sh's C-8 <<'PY' heredoc, BEFORE any deck is generated (U56-2, "
        "ADR-109/§39.39(e): the single-ended TS attempt is gated on the CERTIFIED reactant "
        "endpoint only -- the product is an IRC output, not an input). Reached via the same "
        "shell bridge as require_ts_precondition; the refusal/open behaviour is pinned by "
        "test_c8_gate.py's U56 classes."),
    "cost_probe_violations": ("criteria/p1.py::evaluate_p1 (C-10, ADR-090 item 7/ADR-091, "
                             "MAJOR) -- wired as DIAGNOSIS ONLY, see the field's own comment "
                             "in criteria/p1.py: does not remove/rename/gate anything, "
                             "reports the violation as `c10_cost_probe_violations` / "
                             "`c10_note`. Whether P1 should stop reporting a chemical "
                             "status at all is a separate, larger scope decision."),
}


class TestEveryGuardsFunctionIsAccountedFor(unittest.TestCase):
    """No public guards.py function may be silently unclassified. A NEW function with no
    entry in any bucket is a FAILURE here, not an oversight waiting for next round's critic."""

    def test_every_public_function_is_in_exactly_one_bucket(self):
        buckets = [INTERNAL_HELPERS, DEFERRED_NO_CONSUMER_YET, KNOWN_OPEN_DEFECTS,
                  BLOCKED_ON_DECISION, EXPECTED_REACHED]
        for name in _guards_functions():
            hits = [b for b in buckets if name in b]
            self.assertEqual(
                len(hits), 1,
                "%r is in %d bucket(s) (need exactly 1) -- classify it in "
                "test_guard_reach.py before it can silently ship unreached "
                "(this IS ADR-090's finding)" % (name, len(hits)))


class TestExpectedReachedGuardsAreActuallyCalled(unittest.TestCase):
    """🔴 ADR-092: detection is by `ast.Call`, never a name-occurrence sweep -- that sweep
    is exactly what mistook a same-spelled dict KEY for a call and certified `irc_verdict`
    as wired when `criteria/p1.py` did not even import `guards`."""

    def test_each_expected_reached_guard_has_a_real_external_caller(self):
        for name, where in EXPECTED_REACHED.items():
            with self.subTest(guard=name):
                hits = _external_callers_of(name)
                self.assertTrue(hits,
                               "%r is supposed to be reached (%s) but no external .py "
                               "file's AST calls it" % (name, where))

    def test_a_dict_key_with_the_same_spelling_does_not_count_as_a_call(self):
        """The exact ADR-092 trap, pinned so it cannot silently reopen: p1.py's renamed
        topology-verdict key must coexist with a REAL call to `guards.irc_verdict`, and the
        detector must tell the two apart."""
        p1_path = os.path.join(SEI_PILOT_DIR, "criteria", "p1.py")
        with open(p1_path) as fh:
            text = fh.read()
        self.assertIn("irc_topology_verdict", text,
                      "the ADR-092 rename should still be in place")
        tree = ast.parse(text)
        real_calls = [n for n in ast.walk(tree)
                     if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                     and n.func.attr == "irc_verdict"]
        self.assertTrue(real_calls,
                        "guards.irc_verdict must be an actual ast.Call in p1.py, not just "
                        "a same-spelled string somewhere in the file")


class TestDeferredAndKnownDefectGuardsStayVisible(unittest.TestCase):
    """Category (B)/(A) guards must remain genuinely unreached in the CURRENT tree. If one
    silently GAINS a caller, its bucket entry is stale -- either it was fixed (move it to
    EXPECTED_REACHED) or something now calls it WRONGLY (a live defect this test cannot
    itself judge, but must not hide by staying silent)."""

    def test_deferred_guards_have_no_external_caller_yet(self):
        for name, reason in DEFERRED_NO_CONSUMER_YET.items():
            with self.subTest(guard=name):
                hits = _external_callers_of(name)
                self.assertFalse(hits,
                                "%r (%s) now HAS an external caller (%s) -- this bucket "
                                "entry is stale; move it to EXPECTED_REACHED if the wiring "
                                "was done correctly" % (name, reason, hits))

    def test_known_open_defects_are_still_open(self):
        for name, reason in KNOWN_OPEN_DEFECTS.items():
            with self.subTest(guard=name):
                hits = _external_callers_of(name)
                self.assertFalse(hits,
                                "%r (%s) now HAS a caller (%s) -- if it was wired correctly, "
                                "move it to EXPECTED_REACHED; if it exists and gets the guard "
                                "WRONG that is a live defect this file cannot itself catch"
                                % (name, reason, hits))

    def test_blocked_on_decision_guards_are_not_wired_onto_a_live_path(self):
        """🔒 The whole point of this bucket: it must NEVER silently become reached. If it
        does, someone wired a methodology decision onto a live path without the ruling that
        was explicitly escalated -- worse than a plain unwired defect, because it looks done."""
        for name, reason in BLOCKED_ON_DECISION.items():
            with self.subTest(guard=name):
                hits = _external_callers_of(name)
                self.assertFalse(hits,
                                "%r (%s) now HAS a caller (%s) -- this was ESCALATED, not "
                                "queued; do not wire it onto a live path without the ruling "
                                "landing first (move to EXPECTED_REACHED only once it has)"
                                % (name, reason, hits))


class TestExecutionAuditReachesExactlyTheExpectedCollectors(unittest.TestCase):
    """🔴 ADR-091: `collect.py:89` once claimed `execution_audit` runs "from every
    collector" -- false, originally 4 of 9, then 5 of 9 with `collect_p6` (ADR-092), then 6 of
    10 with `collect_endpoint_prep` (ADR-099), now 7 of 11 with `collect_u56` (U56-2, ADR-109
    -- `U56.sh` sources common.sh/sei_stage the same as the other six). This measures the
    TRUE set by AST so the docstring's own accounting table cannot silently diverge from the
    code again."""

    EXPECTED_CALLERS = frozenset(
        ["collect_p1", "collect_p1b", "collect_p3", "collect_p5", "collect_p6",
        "collect_endpoint_prep", "collect_u56"])
    EXPECTED_NON_CALLERS = frozenset(
        ["collect_p4", "collect_node_probe", "collect_throughput", "collect_queue_wait"])

    def _collect_functions_calling_execution_audit(self):
        with open(COLLECT_PATH) as fh:
            tree = ast.parse(fh.read())
        out = set()
        for node in tree.body:
            if not (isinstance(node, ast.FunctionDef) and node.name.startswith("collect_")):
                continue
            for n in ast.walk(node):
                if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                        and n.func.id == "execution_audit"):
                    out.add(node.name)
                    break
        return out

    def test_exactly_the_expected_collectors_call_execution_audit(self):
        self.assertEqual(self._collect_functions_calling_execution_audit(),
                         set(self.EXPECTED_CALLERS))

    def test_the_four_non_callers_are_still_non_callers(self):
        actual = self._collect_functions_calling_execution_audit()
        for name in self.EXPECTED_NON_CALLERS:
            with self.subTest(collector=name):
                self.assertNotIn(name, actual,
                                 "%r now calls execution_audit -- update collect.py's "
                                 "accounting docstring AND this test's buckets together, "
                                 "or the two will drift the way ADR-091 found them drifted"
                                 % name)

    def test_all_named_collectors_exist_as_functions(self):
        """Guard the guard: if a collector is renamed or removed, this test must notice
        rather than silently checking nothing."""
        with open(COLLECT_PATH) as fh:
            tree = ast.parse(fh.read())
        defined = set(n.name for n in tree.body if isinstance(n, ast.FunctionDef))
        for name in self.EXPECTED_CALLERS | self.EXPECTED_NON_CALLERS:
            self.assertIn(name, defined)


if __name__ == "__main__":
    unittest.main()
