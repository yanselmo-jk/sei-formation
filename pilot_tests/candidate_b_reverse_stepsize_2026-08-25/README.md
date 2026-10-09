# Candidate B — from-scratch reverse-arm StepSize IRC redo (2026-08-25)

Staged after `proposer13`'s rulings (`docs/02_METHOD_SPEC.md` §39.127, superseded on the
`StepSize`/`maxpoints` integers by §39.128) specified Candidate B following Candidate A's
rejection (§39.126). Governing documents: `docs/01_DECISION_LOG.md` ADR-115/116/117,
`02_METHOD_SPEC.md` §39.124 (original candidate menu), §39.125/§39.126 (stage 4 / Candidate A
results), §39.127 (this candidate's spec), §39.128 (integer-`StepSize` correction —
`stepsize=2`/`maxpoints=70`, not this coder's first `stepsize=3`/`maxpoints=55` draft),
`03_COMPUTE_PLAN.md` §R39.82-84 (engineer14's pricing — §R39.84 is the CONFIRMED, first-
principles re-derivation for `stepsize=2`/`maxpoints=70`, superseding §R39.82/83's f=0.25/
f=0.30 pricing rounds), `05_STATE.md` §1e/§1f.

## What this is

**NOT a checkpoint restart** (unlike stage 4 and Candidate A) — a from-scratch reverse-direction
IRC (`calcfc`) starting at the certified TS geometry, with `StepSize` reduced to a fifth of
nominal (`f=0.20`, `stepsize=2` — see below) and `recorrect=never` carried forward. Tests whether
a smaller fixed predictor step avoids the failure Candidate A hit two points past the region
`recorrect=never` alone already fixed: a Bulirsch-Stoer corrector that took 11 cycles / 1536
sub-steps, still warned non-convergence, and force-contracted its accepted step to ~35% of
nominal before self-terminating at a declared minimum that failed this project's own
distinctness test (§39.126 — zero fresh SCF at the declared point).

## Ruled parameters (not this coder's choice — proposer13 §39.127/§39.128 / engineer14 §R39.82/83)

| parameter | value | why |
|---|---|---|
| corrector fix | `StepSize`, not `EulerPC` | the failure signature (forced step-contraction to ~35% of nominal) is a fixed-step-too-large-for-local-curvature problem, not an algorithm-family one (§39.127) |
| `f` (fraction of nominal step) | 0.20 (`stepsize=2`) | §39.127's criterion was never "0.25 as a target" — it was "stay below the measured ~0.35 natural contraction scale, take the free margin since cost isn't binding." `f=0.20` leaves 3x the margin `f=0.30` would (0.15 vs. 0.05), at zero extra cost — §39.128 corrected this coder's first pick (`stepsize=3`/`f=0.30`) once `StepSize`'s integer-only constraint was found |
| `recorrect=never` | carried forward, not dropped | both arms already passed the ORIGINAL oscillating-failure region under it; a default-recorrection Candidate B would re-encounter that already-solved failure before ever reaching the new region near arc 2.1 (§39.127) |
| `maxpoints` | 70 (explicit) | ~62.5 raw points needed to clear the `arc>=4.27` floor at f=0.20, +10% margin (same fraction proposer13 used for their original 55) → 70. `maxpoints` was always proposer13's own padded estimate, not a hard constraint — §39.128 raises IT rather than widening the step and spending the margin the whole point of f=0.20 was to buy |
| direction | reverse | U-56a condition 7's reverse branch is the still-open question (§39.126) |
| cores | 64 (explicit) | engineer14 §R39.82 §6's requirement — no builder default (this exact defect class hit this work item twice already) |

## `StepSize` integer value — 2, not 3 (§39.128 corrects this coder's first pick)

G16's `StepSize` keyword takes an integer in units of 0.01 CARTESIAN bohr/step (`critic17`,
32nd review batch — NOT `0.01 Bohr·amu^(1/2)` as an earlier version of this doc said; the log
prints the supplied step in plain bohr — `Step size = 0.100 bohr` at the default N=10 — and only
then, separately, converts it to the mass-weighted quantity G16 actually integrates with
— `0.3421 sqrt(amu)·bohr`. `f = N/10` is unaffected either way; only the unit label was wrong,
no ruled number changes). The project's own default is `StepSize=10` (0.10 units), confirmed
against both arms' measured 0.341-0.342 arc/frame rate. §39.127's ruled `f=0.25` × `StepSize=10` = 2.5 — exactly between two integers,
not buildable as written. This coder's first build picked `stepsize=3` (f=0.30) to keep
`maxpoints=55` from needing to change (`stepsize=2`/f=0.20 would need ~62.5 points against a
55-point cap, exceeding it). **`proposer13` corrected this in §39.128**: the criterion was never
"stay under a fixed `maxpoints`" — it was "stay below the corrector's own measured natural
contraction scale (~0.35), and since cost is confirmed non-binding, take the larger of the two
available margins for free." `f=0.30` leaves only 0.05 margin below 0.35; `f=0.20` leaves
0.15 — three times as much. `maxpoints` was always proposer13's own margin-padded estimate for
a target f, not a hard ceiling — so it is `maxpoints` that flexes (55 → 70, +10% over the ~62.5
raw points `f=0.20` needs), not the step. Full reasoning in `build_u56_ra_irc_stepsize_probe.py`'s
`IRC_STEPSIZE`/`IRC_MAXPOINTS` comments.

## Provenance

Built here, not copied, with a NEW tool (`src/pilot_package/tools/build_u56_ra_irc_stepsize_
probe.py` — Candidate A's restart tool does not apply, there is no checkpoint for this candidate):

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_ra_irc_stepsize_probe.py \
      --job-dir cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan \
      --out-dir candidate_b_reverse_stepsize_2026-08-25 \
      --total-cores 64

Geometry: `U56_RA_scan/ts.xyz`, the certified TS (11 atoms; `ts_acceptance.json`:
`normal_termination: true`, `opt_converged: true`, exactly one imaginary mode). Verified
numerically identical (all 11 atoms, all 3 coordinates each) to the coordinate block the
ORIGINAL production `irc_reverse.gjf` used — same starting point, only the corrector settings
differ.

**Route explicitly states `maxpoints=70`, `stepsize=2`, `recorrect=never`** — verified in
`irc_stepsize_probe.gjf`, all three hardcoded ruled constants in the tool (not CLI-overridable,
not defaulted), closing the exact "correct number exists in a document but not in the submitted
deck" failure class named twice already on this work item (§R39.82 §6).

## Cores / wall

| | cores | walltime | basis |
|---|---|---|---|
| candidate B | 64 (from the deck's own `%nprocshared=64`, verified) | 14:00:00 | 2.1-4.0h pessimistic ceiling (134.4-254.1 core-h / 64 cores — engineer14's §R39.84 CONFIRMED first-principles re-derivation, not an extrapolation) — 14h cap is a ~3.5x margin, generous for the unsmoked full-route-combination risk (MODERATE per §R39.82 §5), well inside ADR-114's 48h cap (>12x margin per §R39.84) and engineer14's own informational 200-point/~11.9h soft ceiling (70 << 200) |

**Two numbers, not one** (§R39.84's own distinction, same one §R39.81 already used for
Candidate A): **targeted/expected** — 63 points, the run length actually expected if it clears
the arc floor and self-terminates rather than exhausting the cap: 121.0-228.7 core-h, 1.9-3.6h
wall. **Requested ceiling** — 70 points, `maxpoints=70`'s full budget consumed: 134.4-254.1
core-h, 2.1-4.0h wall. The deck requests the ceiling regardless (costs nothing extra unless
actually used); the PBS walltime above is sized against the ceiling.

Confirmed, not provisional: engineer14 independently re-derived this from the measured
per-point rate (`70 × 1.92-3.63 = 134.4-254.1`), not by trusting `proposer13`'s own earlier
`(70/52) × [99.8,188.8] ≈ [134,254]` extrapolation (§39.128) — the two land within rounding of
each other, confirming rather than correcting it.

`GAUSS_NPROCSHARED` is **not** a Gaussian 16 variable and is deliberately absent from the
script, same convention as every other staged deck in this project.

## Smoke test — deliberately NOT staged

`proposer13` declined engineer14's smoke-first recommendation (§R39.83): a 1-2 point smoke near
the TS cannot reach the arc 2.0-2.3 region that actually tests the hypothesis, so it would only
validate route syntax, not science — and since cost is confirmed non-binding, running the full
committed run directly costs no more in practice than smoke-then-full, with a real answer either
way. The only thing a smoke would have saved is calendar time on a route-syntax failure (~2 min
vs. ~2.1-4.0h) — a known, accepted trade, not an oversight.

## BEFORE submitting

1. Confirm `module load gaussian/g16.c01.linda` is still the right module name on the cluster.
2. Check cluster scratch quota (same standing note as the earlier staged batches).

## Submit

    cd <this directory>
    qsub submit_candidate_b.pbs

**Do NOT run `./run.sh --submit`** — same reasoning as every earlier staged batch: this is a
hand-staged diagnostic deck, deliberately outside the harness.

## AFTER the run — mandatory checks

**Read the log at the point(s) landing near arc 2.0-2.3 SPECIFICALLY, not just the final summary
table** (`proposer13`, §39.127) — that is exactly the region Candidate A's nominal-step attempt
broke down in. A clean, single-pass corrector step there is the direct positive signal the
`StepSize` hypothesis is right. A repeat `WARNING: Bulirsch-Stoer Method is not Converging` even
at this smaller step means the underlying PES feature needs `EulerPC` or a finer `f`, not a
shrug — do not read a technically-complete run as confirmation without checking this region.

**Use `-a` on every check below, not plain `grep -c`.** G16 logs are binary-flagged — plain
`grep` on a binary-flagged file gives **no output at all**, not even `0`, regardless of whether
the pattern is present. A blank result is NOT "0 matches" — it means `-a` was dropped and the
check must be rerun before being trusted either way.

**Check 1 — was `StepSize` actually honored, not just echoed** (`critic17`, 32nd review batch):
`grep -ac "stepsize"` on the route-echo line only confirms G16 saw the keyword in the input, not
that it changed the integration — it cannot distinguish "honoured" from "parsed and ignored,"
which is exactly the risk this check exists for. Check the PARAMETER BANNER instead, near the
top of the IRC section, within the first few seconds (before real core-h is spent):

    grep -a "Step size" irc_stepsize_probe.log
    grep -a "Integration on MW PES" irc_stepsize_probe.log

At `stepsize=2`, expect `Step size = 0.020 bohr` and `Integration on MW PES will use step size
of 0.0684 sqrt(amu)*bohr` (0.3421 × 0.20). If these instead read `0.100 bohr` / `0.3421
sqrt(amu)*bohr` (the DEFAULT `N=10` values — reference: the original `irc_reverse.log:165` and
`:1327-1328`), `stepsize=2` was silently ignored and the run says nothing about the `StepSize`
hypothesis. This is a from-scratch `calcfc` run, not a restart — a restart form (e.g. Candidate
A) prints the mass-weighted number directly instead (`irc_recorrect_probe.log:116`); don't be
surprised by the difference if ever comparing the two logs side by side.

**Check 2 — was `recorrect=never` actually honored** (carried forward from `recorrect=never`'s
own history on this work item — dropped from an earlier draft of this README by mistake; B
carries this keyword forward the same as stage 4/Candidate A, and a silent drop invalidates the
run the same way regardless of which candidate built it):

    grep -ac "Recorrection delta-x convergence threshold:" irc_stepsize_probe.log

Expect `0` (matches Candidate A's own returned log, where `recorrect=never` was honored). The
ORIGINAL from-scratch reverse run (default recorrection, `irc_reverse.log`) had 30 occurrences
of this line — a proven discriminator on exactly this deck type, not a hypothetical risk. If the
count is nonzero here, `recorrect=never` did not take effect and a repeat crash would be a false
negative, not evidence against the `StepSize` hypothesis.

If `candidate_b_kill.marker` exists, the job was killed before completion (the `trap ... TERM`
is best-effort; this site's PBS SIGTERM grace window is unconfirmed, `[ASSUMPTION]`).
