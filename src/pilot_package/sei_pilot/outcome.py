"""Parsed-content outcome of a job, for the state markers (§39.80(g) clause (i), ADR-113).

`rc` is the WRAPPER's exit code and payloads deliberately exit 0 on a chemistry failure
(failure-as-data, §39.69(d)). On this cluster rc has been seen wrong in BOTH directions
(rc=0 on a segfaulted freq stage; rc=1 on converged P5 rows). So every payload writes a
`terminal_status[.tN].json` whose `status` is read from PARSED CONTENT, and this module maps
that status onto the cause-class taxonomy the project already uses (`guards.py`:
chemical | budget | protocol | engine | unknown).

Retry rule (lead ruling, 2026-08-21): the harness may auto-resubmit a finished item ONLY when
its cause class is plumbing-shaped (`protocol`, `engine`, `unknown`) -- nothing chemically
informative happened. `chemical` and `budget` are real completed answers, even when negative;
resubmitting them unchanged burns core-h for zero new information.
"""

import json
import os
import sys

from . import state

SUCCESS = "success"

#: terminal_status -> cause class. 🔴 An unlisted status is `unknown` (and therefore retried),
#: so a payload that invents a new status string without adding it here gets a loud retry,
#: not a silent skip. `absent` (payload wrote no terminal_status at all -- probes, legacy
#: markers) is deliberately NOT in the taxonomy and is never retried: it carries no verdict.
CAUSE_BY_STATUS = {
    "converged": SUCCESS,
    # payloads whose deliverable is a MEASUREMENT (timings, probes), not a convergence verdict
    "completed": SUCCESS,
    "not_converged": "chemical",
    "engine_failure": "engine",
    # [§39.87, proposer8] a defect the run cannot fix: same deck -> same crash, forever. G16
    # names the cause in one line and dies at the same point every time. Retrying is a loop
    # that spends budget while manufacturing the appearance of effort. NEVER retried.
    "input_defect": "deterministic",
    "input_error": "protocol",
    "solvent_refused": "protocol",
    "smoke_failed": "protocol",
    "route_smoke_failed": "protocol",
    "input_missing": "protocol",
    "skipped": "protocol",                   # no QC engine available on the node
    "solvent_descriptors_missing": "protocol",
    "stage1_budget_exhausted": "budget",
    "stage2_budget_exhausted": "budget",
    "wall_exhausted": "budget",
    "wall_budget_exhausted": "budget",
    # --- U56.sh (§39.39(d) TS attempts) -- coder's own fix, ADR-114 follow-up. This payload's
    # deliverable is a CANDIDATE + its supporting measurements, not a pass/fail verdict (that
    # is the collection stage's job, §39.39(f) -- see u56_attempt.json's own note). The statuses
    # below are the payload's honest self-report of WHERE it stopped, never a chemistry verdict.
    "ts_candidate_produced": SUCCESS,          # ran to completion; same shape as "completed"
    "gscan_protocol_indeterminate": "protocol",  # frame0 reference frame unsettled (§39.68(3))
    "indeterminate_missing_coordinate": "chemical",  # G-SCAN-4 fired: measured PES hysteresis
    "scan_not_converged": "chemical",          # relaxed scan produced no usable maximum
    "saddle_outside_endpoint_bracket": "chemical",   # §39.66 bracket check refused
    "spectator_mode_not_the_coordinate": "chemical",  # §39.62 spectator test fired
    "irc_refused_no_direction_ran": "unknown",  # every IRC direction refused, mixed causes
    "ts_opt_no_geometry": "engine",            # TS opt/QST2 ran but yielded no final geometry
    "endpoint_geometry_missing": "protocol",   # no certified endpoint geometry on record
    "c8_precondition_refused": "protocol",     # C-8 gate refused before any deck was built
    "mapping_unresolved": "protocol",          # §39.26(d) role->index mapping unresolved
    "gfn2_prestage_unavailable": "protocol",   # xtb missing or G-SCAN verdict not produced
    # [§39.138/§39.139, proposer13 ruling, wave-1] U56.sh's SEI_U56_STOP_AFTER circuit breaker
    # (payload/U56.sh:86) -- a DELIBERATE, human-gated pause, never a retry target: no chemistry
    # verdict, no procedure defect, no numerical failure, no budget cap fired, and nothing
    # "unknown" about it (it is fully recorded and understood). Also never pooled into either
    # U-56b denominator (chemical/budget) -- a mid-attempt checkpoint isn't a concluded outcome.
    "stopped_after_stage": "staged",
}
RETRY_CLASSES = ("protocol", "engine", "unknown")

#: Log sentinels that name a DETERMINISTIC failure -- not necessarily a deck defect (most are:
#: G16 says what is wrong with the deck), but the boundary this tuple actually enforces is
#: narrower: the SAME input, run again, fails IDENTICALLY every time. [critic14] The IRC
#: corrector-integration sentinel below is the first member that names a numerical/integrator
#: failure at a geometry the protocol legitimately requested, not a deck problem -- it qualifies
#: on the "same deck -> same crash" test, not on "the deck itself is wrong" (§39.87/lead ruling
#: 2026-08-21). Matched before the generic engine test. Add to this tuple when a new one is
#: diagnosed --
#: the EpsInf sentinel cost this project one full round (§39.73/§39.80).
INPUT_DEFECT_SENTINELS = (
    "EpsInf not defined for this solvent",
    "Unrecognized",            # route keyword
    "is not a valid",
    "Unknown method",
    "basis set not found",
    "Illegal",
    "syntax error",
    # [critic14 / lead ruling 2026-08-21, linear-hopping-frog Track A] IRC corrector
    # integration dying on a real, deterministic geometry the protocol requested (measured on
    # U56_RA_scan/U56_RA_qst2's real IRC logs, both directions, both jobs -- NOT a wall/budget
    # kill: wall used was 1.8-5.3 h against a 48 h cap). Same deck, same numerical path, same
    # crash every time -> never auto-retried (§39.87), unlike `engine` which WOULD
    # auto-resubmit on the next build for zero new information (critic14 measured 449 core-h
    # of exactly that risk). G16's own spelling, verbatim: "exceded", not "exceeded".
    "Maximum number of corrector steps exceded",
)
NO_VERDICT = ("absent", "unparsable", "", None)


#: Worst-first order for aggregating an ARRAY item's per-task outcomes into one class.
#: `deterministic` dominates (never retry), then the "real answer" classes, then plumbing.
#: 🔴 [critic17, wave-1 review -- the one-line CAUSE_BY_STATUS fix alone is NOT sufficient]
#: `staged` MUST also be listed here, positioned ahead of SUCCESS: aggregate_cause() falls
#: through to "unknown" (a RETRY class) for any class missing from this tuple, so a `staged`-only
#: item would get auto-retried one level up from the bug this class exists to fix; and a mixed
#: item (one task staged, another succeeded) must report `staged`, not `success` -- a job whose
#: staged stage never ran is not a completed answer just because a sibling task finished.
#: 🔴 [proposer13, §39.140] Exact position ruled: deterministic -> budget -> staged -> chemical
#: -> engine -> protocol -> unknown -> success -> absent. Ahead of success (forced -- see above)
#: AND ahead of chemical/engine/protocol/unknown, behind deterministic/budget. Reasoning: a
#: human who sees `staged` investigates the item fully (that IS what the label means -- come
#: look and decide) and will discover any co-occurring real failure in the process; a human who
#: sees `chemical`/`engine` reads it as an ordinary already-understood failure and has no reason
#: to look further, which is exactly how a co-occurring staged sibling would go unnoticed while
#: cost keeps accumulating on a pending decision. Letting `staged` mask a REAL failure
#: (deterministic/budget) loses less than the reverse, since only one direction is
#: self-correcting once someone actually opens the item.
CLASS_SEVERITY = ("deterministic", "budget", "staged", "chemical", "engine", "protocol",
                  "unknown", SUCCESS, "absent")


def aggregate_cause(classes):
    classes = [c for c in classes if c]
    if not classes:
        return "absent"
    for c in CLASS_SEVERITY:
        if c in classes:
            return c
    return "unknown"


def cause_class(status):
    if status in NO_VERDICT:
        return "absent"
    return CAUSE_BY_STATUS.get(status, "unknown")


def should_retry(cause):
    return cause in RETRY_CLASSES


def record(status, note="", **extra):
    out = {"status": status, "note": note, "cause_class": cause_class(status)}
    for k, v in extra.items():
        try:
            out[k] = float(v) if isinstance(v, str) and v.replace(".", "", 1).isdigit() else v
        except (TypeError, ValueError):
            out[k] = v
    return out


def write(path, status, note="", **extra):
    rec = record(status, note, **extra)
    state._atomic_write(path, json.dumps(rec, ensure_ascii=False, indent=1))
    return rec


def status_from_g16_logs(texts):
    """Aggregate many G16 logs into ONE terminal status, from termination evidence only.

    input_defect    a FAILED log names a deterministic deck defect (INPUT_DEFECT_SENTINELS)
                    -- never retried (§39.87). Sentinels are only consulted after the log has
                    already failed the termination test.
    engine_failure  any log carries an `Error termination`, has no `Normal termination`, or
                    is missing a stage its route requested (the EpsInf sentinel, SCF death,
                    segfault, truncated log, opt that stopped -- all "the engine stopped").
                    🔴 `Error termination` is checked EXPLICITLY: a multi-stage log prints
                    `Normal termination` after the opt half and then dies in freq (the real
                    P5 logs do exactly this), so `normal_termination` alone reads True.
                    SCF/opt non-convergence lands here too -- consistent with
                    `guards.ENGINE_FAILURE_KINDS`, which already files scf_not_converged as
                    engine, not chemistry.
    converged       all logs normal, all requested stages present.
    🔴 This function never returns `not_converged`: a NEGATIVE CHEMISTRY verdict (n_imag != 0,
    wrong product, ...) needs the payload's own criteria, not a termination banner. Payloads
    that can make that call write it themselves via `sei_terminal not_converged ...`.
    Empty input -> engine_failure ("no log at all" is plumbing, not chemistry).
    """
    from .criteria import g16
    texts = list(texts)
    if not texts:
        return "engine_failure", "no QC log produced"
    for t in texts:
        s = g16.summarize(t)
        if "Error termination" in (t or "") or not s["normal_termination"]:
            # [critic11] sentinels are consulted ONLY on an already-failed log -- same order
            # as g16.parse_termination. "Illegal symmetry operation ignored" appears in
            # converged logs; unguarded it filed a good result as a deck defect.
            for sent in INPUT_DEFECT_SENTINELS:
                if sent in (t or ""):
                    return "input_defect", ("deterministic: %r in a failed log -- same deck, "
                                            "same crash" % sent)
            return "engine_failure", "%s: %s" % (s["failure_reason"] or "error_termination",
                                                 (s["failure_message"] or "")[:120])
        st = g16.stages_completed(t, s.get("route_echoed"))
        if st["missing"]:
            return "engine_failure", "requested stage(s) left no evidence: %s" % ",".join(st["missing"])
    return "converged", ""


def main(argv):
    cmd = argv[0] if argv else ""
    if cmd == "write":
        path, status, note = argv[1], argv[2], argv[3] if len(argv) > 3 else ""
        extra = dict(a.split("=", 1) for a in argv[4:] if "=" in a)
        write(path, status, note, **extra)
        return 0
    if cmd == "from-logs":
        # from-logs PATH [k=v ...] -- LOG ...   (a LOG that does not exist reads as empty ->
        # engine_failure: "never produced" is plumbing, and must not vanish from the count)
        path = argv[1]
        rest = argv[2:]
        sep = rest.index("--") if "--" in rest else len(rest)
        extra = dict(a.split("=", 1) for a in rest[:sep] if "=" in a)
        logs = rest[sep + 1:]
        texts = []
        for lg in logs:
            try:
                texts.append(open(lg, errors="replace").read())
            except OSError:
                texts.append("")
        status, note = status_from_g16_logs(texts)
        write(path, status, note, n_logs=len(logs), **extra)
        print("[outcome] %s <- %d log(s): %s %s" % (os.path.basename(path), len(logs), status, note))
        return 0
    sys.stderr.write("usage: outcome write PATH STATUS [NOTE] [k=v..] | from-logs PATH [k=v..] -- LOG..\n")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
