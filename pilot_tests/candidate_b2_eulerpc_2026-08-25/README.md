# EulerPC escalation — backup tier, staged alongside Candidate B (2026-08-25)

🔴 **THIS IS A BACKUP TIER, NOT A PROMOTION.** `StepSize` (Candidate B,
`candidate_b_reverse_stepsize_2026-08-25/`) still runs and is read FIRST, unconditionally.
Staged here for logistics only — the user wants both ready in one cluster round-trip — not
because EulerPC is expected to work better, or even as well. **Only submit anything in this
directory if Candidate B has already run and its own mandatory checks (its README) show it
failed.** If Candidate B's checks pass, this directory should not be submitted at all.

Governing documents: `docs/01_DECISION_LOG.md` ADR-115/116/117, `02_METHOD_SPEC.md` §39.124
(original candidate menu), §39.125/§39.126 (stage 4 / Candidate A results), §39.127/§39.128
(Candidate B spec), §39.129 (this tier's spec, proposer13), `03_COMPUTE_PLAN.md` §R39.85
(engineer14's pricing), `05_STATE.md` §1f "EULERPC ESCALATION SPECIFIED AND PRICED".

## Why this is a WEAKER second bet than it might look

`proposer13` checked Gaussian's own IRC keyword documentation directly (`gaussian.com/irc/`,
quoted not recalled) before ruling this route: **`EulerPC` does NOT replace HPC's corrector —
it only swaps the predictor.** The walk still runs through the exact same Bulirsch-Stoer/DWI
corrector that emitted `WARNING: Bulirsch-Stoer Method is not Converging` at Candidate A's
Point 7 (§39.126). If the pathology is corrector-side (which the observed symptoms — the BS
warning, the escalating cycle count, the DWI-internal gradient std-dev blowup — are specifically
about, not the predictor), a cruder predictor feeding the same corrector is not obviously going
to fix it, and could plausibly stress the corrector *more* (a worse initial guess typically
needs more, not fewer, corrector recorrection cycles). This is a real, sourced correction to how
§39.127 originally framed `EulerPC` as "a different integrator" — it isn't fully independent.

## Ruled parameters (not this coder's choice — proposer13 §39.129 / engineer14 §R39.85)

| parameter | value | why |
|---|---|---|
| predictor | `EulerPC` (swapped from HPC's default) | the only variable changed relative to Candidate B |
| `stepsize` | **2 — IDENTICAL to Candidate B** | single-variable-change discipline (§39.129(3)): if this tier is ever run, only the predictor changed vs. B, so a pass/repeat-failure result is attributable to the predictor/corrector combination alone, not confounded with a simultaneous step-size change |
| `recorrect=never` | carried forward, same as B | confirmed valid for `EulerPC` too against Gaussian's own doc (`ReCorrect` "Controls testing-and-recomputing for the correction step of **HPC and EulerPC** IRCs") — dropping it would re-run into the already-solved oscillating failure |
| `maxpoints` | 100 (explicit) — a WIDER hedge than B's 70 | ~62.5-point nominal minimum (same as B, identical stepsize) + ~60% margin, not B's ~10%, because EulerPC's realized arc-per-point is doubly unmeasured: a cruder predictor may need more corrector contraction per point AND no per-point rate exists for this algorithm on this reaction at all |
| direction | reverse | same still-open U-56a condition 7 branch |
| cores | 64 (explicit) | same requirement as every tool on this work item |
| smoke | **recommended and built**, unlike Candidate B | this tier's keyword COMBINATION itself (not just its outcome) is entirely unverified — a malformed combination fails fast at near-zero cost |

## Provenance

Built with a new sibling tool (`src/pilot_package/tools/build_u56_ra_irc_eulerpc_probe.py` —
structurally close to Candidate B's `build_u56_ra_irc_stepsize_probe.py`, kept as a separate
tool rather than a mode flag on it, same separation judgment as the restart-vs-from-scratch
split between the recorrect and stepsize tools):

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_ra_irc_eulerpc_probe.py \
      --job-dir cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan \
      --out-dir candidate_b2_eulerpc_2026-08-25 \
      --total-cores 64 --smoke

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_ra_irc_eulerpc_probe.py \
      --job-dir cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan \
      --out-dir candidate_b2_eulerpc_2026-08-25 \
      --total-cores 64

Geometry: `U56_RA_scan/ts.xyz`, the same certified TS Candidate B uses. Verified numerically
identical (all 11 atoms × 3 coordinates, programmatic float comparison) between this tier's
`.gjf` and Candidate B's own coordinate block.

**Route explicitly states `EulerPC`, `stepsize=2`, `recorrect=never`, `maxpoints=100` (full) /
`maxpoints=2` (smoke)** — verified in both `.gjf` files, all hardcoded ruled constants (smoke
vs. full selected by one explicit `--smoke` flag, never a silent default). Smoke and full write
to DIFFERENT filenames (`irc_eulerpc_smoke.*` / `irc_eulerpc_probe.*`) specifically so both can
be staged in the same directory without either clobbering the other.

## Cores / wall

| | cores | walltime | basis |
|---|---|---|---|
| smoke (1-2 pts, `maxpoints=2`) | 64 | 01:00:00 | 1.9-14.6 core-h [ESTIMATE] (engineer14 §R39.85) → ~0.03-0.23h wall — 1h is a >4x margin, generous for a syntax-check job with unknown startup overhead |
| full (`maxpoints=100`) | 64 | 40:00:00 | targeted/expected (63 pts) 121.0-459.9 core-h → 1.9-7.1h; requested ceiling (100 pts) 192.0-730.0 core-h → 3.0-11.3h wall (engineer14 §R39.85, confirmed, not extrapolated). 40h is a ~3.5x margin over the pessimistic 11.3h ceiling, same discipline as elsewhere on this work item, staying under ADR-114's 48h cap with ~8h to spare |

**Narrowest wall margin on this work item so far** (engineer14's own flag, not this coder's):
~4.2x at the pessimistic ceiling against ADR-114's 48h cap itself, vs. >12x everywhere else
(Candidates A and B). Not a blocker — still clears the cap with real margin — but do not stack
a same-day retry of the full job behind other 48h-class jobs without checking total elapsed
wall-clock first. Worst case (smoke + 2 full-ceiling retry attempts): ~22.7h, ~2.1x margin —
narrower still, flagged for whoever schedules a retry.

`GAUSS_NPROCSHARED` is **not** a Gaussian 16 variable and is deliberately absent from both
scripts, same convention as every other staged deck in this project.

## Sequencing — read in this order, do not skip steps

1. **Candidate B runs and is read first**, unconditionally (its own README).
2. If (and only if) Candidate B's checks show it failed: run `submit_eulerpc_smoke.pbs`, read
   the checks below on `irc_eulerpc_smoke.log`.
3. If the smoke's route-syntax/echo checks pass: run `submit_eulerpc_full.pbs`.
4. Read the full run against all four mandatory checks below before drawing any conclusion.

## BEFORE submitting anything

1. Confirm `module load gaussian/g16.c01.linda` is still the right module name on the cluster.
2. Check cluster scratch quota (same standing note as every earlier staged batch).
3. Confirm Candidate B has actually run and failed its checks — do not submit this tier on a
   schedule, only on evidence.

## Submit

    cd <this directory>
    qsub submit_eulerpc_smoke.pbs      # only after Candidate B fails its checks
    # ... read irc_eulerpc_smoke.log, confirm the syntax/echo checks below pass ...
    qsub submit_eulerpc_full.pbs

**Do NOT run `./run.sh --submit`** — same reasoning as every earlier staged batch: these are
hand-staged diagnostic decks, deliberately outside the harness.

## AFTER the run — mandatory checks, all four, none substitutes for the others

**Use `-a` on every check below, not plain `grep -c`.** G16 logs are inconsistently
binary-flagged from run to run (some ASCII, some not) — plain `grep` on a binary-flagged file
gives **no output at all**, not even `0`, regardless of whether the pattern is present. A blank
result is NOT "0 matches" — it means `-a` was dropped and the check must be rerun before being
trusted either way.

**Check 1 — Euler-predictor echo, confirm EulerPC actually ran, not a silent fallback to HPC**
(engineer14's own catch, §R39.85 — a 4th flavor of this project's "silently didn't get what was
requested" failure class). `[NEEDS VERIFICATION]`: this project has no G16 install and has
never run `EulerPC` before, so the POSITIVE echo string for the Euler predictor cannot be
confirmed from documentation alone — do not guess it. At minimum, confirm HPC's OWN predictor
echo does **not** appear (its presence would mean EulerPC silently fell back to HPC — the same
symptom shape as Candidate B's own result, mislabeled as an EulerPC failure):

    grep -a "Using LQA Reaction Path Following" irc_eulerpc_probe.log

If this string appears anywhere in the IRC section, `EulerPC` did not take effect. Compare the
actual parameter banner against Candidate B's own returned log side by side — Candidate B's log
is the first confirmed HPC/LQA reference point this project has for what the "normal" banner
looks like; whatever EulerPC's log prints INSTEAD of `Using LQA Reaction Path Following` at the
equivalent point in the IRC section is the practical way to confirm the predictor differs,
absent a documented reference string.

🔴 **This negative test is only meaningful if the log shows at least one COMPLETED IRC point**
(`critic17`, 34th review batch): the LQA echo appears roughly once per computed point (measured:
6 occurrences in the original 6-point reverse log, 1 in Candidate A's single-new-point restart)
— a run that dies before completing point 1 also shows zero occurrences, for an unrelated
reason (nothing computed yet, not "EulerPC correctly avoided HPC's predictor"). Confirm the log
reached at least one real point (e.g. an `SCF Done` or a `Point Number` line) before reading a
zero count here as a pass.

**Check 2 — was `recorrect=never` actually honored**:

    grep -ac "Recorrection delta-x convergence threshold:" irc_eulerpc_probe.log

Expect `0` (same standard as Candidate B and Candidate A's own returned log). A nonzero count
means `recorrect=never` did not take effect and a repeat crash would be a false negative.

**Check 3 — read the log at the point(s) landing near arc 2.0-2.3 SPECIFICALLY, not just the
final summary table** — Candidate A's own breakdown region, same as Candidate B.

**Check 4 — tier-specific: does the corrector warning recur** (`proposer13`, §39.129 — the
direct test of the shared-corrector finding this whole tier's framing rests on):

    grep -a "WARNING: Bulirsch-Stoer Method is not Converging" irc_eulerpc_probe.log

A clean pass at arc 2.0-2.3 with no recurrence is the direct positive signal the predictor swap
helped. A repeat warning here — even under a different predictor — is direct evidence the
pathology is corrector-side, not predictor-side, since the ONLY variable changed vs. Candidate B
was the predictor. **Read this before claiming EulerPC "worked" or "didn't work" for a reason
distinct from Candidate B's own result.**

If `eulerpc_smoke_kill.marker` or `eulerpc_full_kill.marker` exists, the corresponding job was
killed before completion (the `trap ... TERM` is best-effort; this site's PBS SIGTERM grace
window is unconfirmed, `[ASSUMPTION]`).

## Third tier, named but NOT staged here: `DVV`

`proposer13` (§39.129) separately named `IRC=DVV` (Damped Velocity Verlet) as a genuinely
different integration scheme — confirmed from the same doc fetch to NOT share HPC/EulerPC's
corrector at all, unlike this tier. Two `[NEEDS VERIFICATION]` caveats named there (calcfc
compatibility, whether `recorrect` is even a live concept for it) and it is entirely unpriced.
Not staged in this round — a separate lead/user decision if wanted alongside this batch.
