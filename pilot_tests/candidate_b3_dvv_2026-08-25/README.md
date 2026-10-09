# DVV escalation — third-tier backup, staged alongside Candidate B and EulerPC (2026-08-25)

🔴 **THIS IS A THIRD-TIER BACKUP, NOT A PROMOTION.** `StepSize` (Candidate B,
`candidate_b_reverse_stepsize_2026-08-25/`) runs and is read FIRST. The `EulerPC` escalation
(`candidate_b2_eulerpc_2026-08-25/`) runs SECOND, only if Candidate B fails. **This tier runs
THIRD, only if BOTH Candidate B and EulerPC have already run and failed their own mandatory
checks.** If either B or EulerPC's checks pass, nothing in this directory should be submitted.

Governing documents: `docs/01_DECISION_LOG.md` ADR-115/116/117, `02_METHOD_SPEC.md` §39.124-129
(prior tiers), §39.130 (this tier's spec, `proposer13`), `03_COMPUTE_PLAN.md` §R39.86
(`engineer14`'s pricing), `05_STATE.md` §1f.

## Why DVV is a genuinely different KIND of backup, not just a third option on a list

`proposer13` checked Gaussian's own IRC documentation for DVV specifically (thin: three of six
things checked are not covered by the primary source at all) and found the underlying method
paper's abstract (Hratchian & Schlegel, *J. Phys. Chem. A* **2002**, *106*, 165-169 — abstract
only, found via search, **not the full paper**, flagged accordingly): DVV is a velocity-Verlet
propagator with an **adaptive time step**, whose stated advantage is that "the Hessian does not
need to be calculated" at every step. **It shares NO machinery with the Bulirsch-Stoer/DWI
corrector that both HPC (Candidate B) and EulerPC ride on** — the exact subsystem that failed at
Candidate A's Point 7 (§39.126). This is the one tier that can actually distinguish two
different explanations: if `StepSize` and `EulerPC` both fail with the same `Bulirsch-Stoer`
warning signature, a **clean DVV pass would implicate the corrector specifically**; comparable
difficulty under genuinely different machinery would point at the **PES region itself** instead.

## The three-rung fallback ladder — ALL SIX decks pre-built, nobody hand-edits a route on the cluster

| rung | route (`irc=(...)`) | when to use it |
|---|---|---|
| 1 (preferred) | `calcfc,reverse,DVV,stepsize=2,maxpoints=...` | try this first |
| 2 (fallback) | `reverse,DVV,stepsize=2,maxpoints=...` | ONLY if rung 1's **smoke** errors specifically on the `calcfc`+`DVV` combination |
| 3 (fallback) | `reverse,DVV,GradientOnly,stepsize=2,maxpoints=...` | ONLY if rung 2's **smoke** ALSO errors |

🔴 **Rung 3 is scientifically undesirable, not just a syntax fallback** (`proposer13`,
§39.130): it discards this project's available analytic Hessians. If the ladder falls this far,
that is worth a second look from the lead/user before spending the full core-h ceiling on it —
not an automatic next step.

🔴 **Rung 3's own silent-wrong-algorithm risk, sharper than at rungs 1/2** (`critic17`, 34th
review batch): `GradientOnly`'s own documented default algorithm is `EulerPC` — the exact
Bulirsch-Stoer-corrector machinery this whole tier exists to avoid (Gaussian's own doc, quoted:
`GradientOnly` "Can be combined with `EulerPC` (the default), `HPC`, `Euler`, or `DVV`"). If the
`DVV` keyword is ever dropped or silently ignored at rung 3, the run does not fail loudly — it
silently becomes an `EulerPC` run (`rc=0`, normal termination) with no obvious symptom unless
checked for. **Checks 1 and 2 below are NOT optional at rung 3 — they are the only thing that
catches this specific failure mode.**

Each rung has its own smoke (`maxpoints=3`) and full (`maxpoints=100`) deck — **6 files total**,
all pre-built by `src/pilot_package/tools/build_u56_ra_irc_dvv_probe.py`, so nothing on the
cluster ever requires manually editing a Gaussian route string (a real syntax error is easy to
introduce this way and expensive to discover only after a real run):

| file | rung | mode |
|---|---|---|
| `irc_dvv_rung1_smoke.gjf` / `submit_dvv_r1_smoke.pbs` | 1 | smoke |
| `irc_dvv_rung1_full.gjf` / `submit_dvv_r1_full.pbs` | 1 | full |
| `irc_dvv_rung2_smoke.gjf` / `submit_dvv_r2_smoke.pbs` | 2 | smoke |
| `irc_dvv_rung2_full.gjf` / `submit_dvv_r2_full.pbs` | 2 | full |
| `irc_dvv_rung3_smoke.gjf` / `submit_dvv_r3_smoke.pbs` | 3 | smoke |
| `irc_dvv_rung3_full.gjf` / `submit_dvv_r3_full.pbs` | 3 | full |

## Two deliberate omissions, not oversights

- **`recorrect=never` is OMITTED at every rung** (`proposer13` §39.130(2)): `ReCorrect`'s
  documented default is already `Never` for "other integrators" (DVV is neither HPC nor
  EulerPC), and DVV is a Verlet-type propagator, not a predictor-corrector method — there is no
  corrector for `ReCorrect` to control. Writing it risks a harmless no-op at best, a
  route-syntax rejection at worst. **Do not add it "for consistency" with the other two decks.**
- **No targeted/expected cost figure** (`engineer14` §R39.86) — deliberately, not an oversight:
  DVV's per-point cost AND point-count-per-arc are BOTH unmeasured, unlike Candidate B/EulerPC
  where at least one axis was anchored to the shared corrector. Only a ceiling is priced, and a
  wide one — the width itself is the honest signal.

## Provenance

Built with a new sibling tool
(`src/pilot_package/tools/build_u56_ra_irc_dvv_probe.py`):

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_ra_irc_dvv_probe.py \
      --job-dir cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan \
      --out-dir candidate_b3_dvv_2026-08-25 \
      --total-cores 64 --rung <1|2|3> [--smoke]

(run 6 times, once per rung × mode combination). Geometry: same certified TS (`ts.xyz`) as
Candidate B and EulerPC. Routes verified directly in the built `.gjf` files, exact match to
§39.130's ruled ladder text:

    rung 1: irc=(calcfc,reverse,DVV,stepsize=2,maxpoints=100)
    rung 2: irc=(reverse,DVV,stepsize=2,maxpoints=100)
    rung 3: irc=(reverse,DVV,GradientOnly,stepsize=2,maxpoints=100)

(smoke variants identical except `maxpoints=3`).

## Cores / wall

| | cores | walltime | basis |
|---|---|---|---|
| any smoke (3 pts) | 64 | 02:00:00 | 1.0-32.7 core-h [ESTIMATE] (engineer14 §R39.86) → ~0.5h pessimistic — 2h is a >4x margin |
| any full (`maxpoints=100`) | 64 | 44:00:00 | ceiling-only 100.0-1090.0 core-h → 1.6-17.0h wall (engineer14 §R39.86, the widest bracket priced on this whole work item). 44h is the MOST margin available under ADR-114's 48h cap (~2.6x over the pessimistic 17.0h ceiling) — narrower than every other job here BY NECESSITY, not a corner cut; a larger safety factor is not available without exceeding the cap outright |

**Rung 3's full run specifically**: `engineer14`'s own caveat — treat the pessimistic
10.9 core-h/pt as a **floor**, not a ceiling, for this rung (removing Hessian/curvature
guidance typically means MORE steps needed, not fewer). Real cost could exceed the bracket
above. Re-check `irc_dvv_rung3_smoke.log`'s own per-point timing before trusting the 44h
walltime, and reconsider whether this rung is worth running at all before submitting — do not
mechanically reuse rung 1's smoke result or timing for this decision.

`GAUSS_NPROCSHARED` is **not** a Gaussian 16 variable and is deliberately absent from every
script, same convention as every other staged deck in this project.

## Sequencing — read in this order, do not skip steps

1. Candidate B runs and is read first (its own README).
2. EulerPC runs and is read second, only if B failed (its own README).
3. **Only if both failed**: run `submit_dvv_r1_smoke.pbs`, read the checks below.
4. If rung 1's smoke **errors** (syntax rejection specifically): run `submit_dvv_r2_smoke.pbs`.
5. If rung 2's smoke **also errors**: stop and reconsider (rung 3 is scientifically
   undesirable, §39.130) before running `submit_dvv_r3_smoke.pbs`.
6. Once a rung's smoke **succeeds**, run that same rung's `_full.pbs`.
7. Read the full run against all mandatory checks below before drawing any conclusion.

## BEFORE submitting anything

1. Confirm `module load gaussian/g16.c01.linda` is still the right module name on the cluster.
2. Check cluster scratch quota (same standing note as every earlier staged batch).
3. Confirm Candidate B AND EulerPC have both already run and failed their checks.

## Submit

    cd <this directory>
    qsub submit_dvv_r1_smoke.pbs        # only after B and EulerPC both fail their checks
    # ... read irc_dvv_rung1_smoke.log; if it errored on calcfc+DVV, try rung 2's smoke instead ...
    qsub submit_dvv_r1_full.pbs         # once the matching rung's smoke succeeds

**Do NOT run `./run.sh --submit`** — same reasoning as every earlier staged batch: these are
hand-staged diagnostic decks, deliberately outside the harness.

## AFTER the run — mandatory checks

**Use `-a` on every check below, not plain `grep -c`/`grep`.** G16 logs are inconsistently
binary-flagged from run to run — plain `grep` on a binary-flagged file gives **no output at
all**, not even `0`, regardless of whether the pattern is present. A blank result is NOT "0
matches" — it means `-a` was dropped and the check must be rerun before being trusted either way.

**Check 1 — POSITIVE echo: confirm DVV actually ran, not a silent fallback to HPC.** Every log
this project has produced so far prints `Integration scheme           = HPC` in the
`GENERAL PARAMETERS` block (confirmed, `irc_reverse.log:166`). The exact string DVV prints is
`[NEEDS VERIFICATION]` — this project has never run DVV before; read it directly from the
smoke's own returned log:

    grep -a "Integration scheme" irc_dvv_rung<N>_smoke.log

Confirm it reads something **other than** `HPC`.

**Check 2 — NEGATIVE, the sharper test:**

    grep -a "Bulirsch-Stoer" irc_dvv_rung<N>_smoke.log   # (or _full.log)

Expect **zero** occurrences anywhere. Its presence means DVV did NOT actually run as a distinct
algorithm regardless of what the `Integration scheme` line claims — the same "silently got HPC
instead" risk named for EulerPC (§39.129 addendum), applied to the tier where it would be
easiest to miss (`rc=0`, normal termination, no reason to suspect anything unless checked).

**Check 3 — `stepsize=2` is on record but NOT trusted to mean the same thing it does for
HPC/EulerPC.** `[NEEDS VERIFICATION]` whether the keyword even applies to DVV's adaptive
stepping, and if so whether it sets a target the adaptive scheme then overrides. **Read the
REALIZED arc-per-point rate directly from the log** — do not assume the requested value was
honored. Under DVV's adaptive control, even the parameter banner itself (if one is printed) may
not mean what it does for HPC — the smoke exists partly to learn what it looks like at all.

**Check 4 — read the log at the point(s) landing near arc 2.0-2.3 SPECIFICALLY**, Candidate A's
own breakdown region, same as every other tier, **PLUS whether any corrector-style warning
appears there at all** — its absence or presence under genuinely different machinery is
informative either way, not just a pass/fail gate.

**Check 5 — there is NO `Recorrection delta-x convergence threshold:` check for this tier.**
The keyword is omitted on purpose (see above) — its absence from this list is deliberate, not a
dropped check. Do not add it back or flag its absence as a gap.

If `dvv_r<N>_smoke_kill.marker` or `dvv_r<N>_full_kill.marker` exists, the corresponding job was
killed before completion (the `trap ... TERM` is best-effort; this site's PBS SIGTERM grace
window is unconfirmed, `[ASSUMPTION]`).

## Why this tier is worth staging even though it may never run

Not a restatement of "bundle everything" — if `StepSize` and `EulerPC` both fail with the same
`Bulirsch-Stoer` warning, that leaves genuinely ambiguous whether the corrector itself is the
problem or the underlying PES region is simply hard for any reasonable path-follower. `DVV`,
sharing none of the suspect machinery, is the one candidate that can actually distinguish those
two explanations. This is the scientific reason to have it ready in the same round-trip,
independent of the logistics motivation (§39.130).
