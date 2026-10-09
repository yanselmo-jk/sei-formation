# U-56a reverse-arm three-tier bundle — 2026-08-25

Three staged diagnostic directories, meant to travel together in **one cluster round-trip**.
NONE of them are submitted by any script here — every `.pbs` file in every directory is
hand-`qsub`'d by a person reading the checks below, one tier at a time. This file is the map;
each directory has its own README with the full detail for that tier.

```
candidate_b_reverse_stepsize_2026-08-25/   Tier 1 — StepSize (Candidate B)   RUNS FIRST, ALWAYS
candidate_b2_eulerpc_2026-08-25/            Tier 2 — EulerPC escalation      backup, only if Tier 1 fails
candidate_b3_dvv_2026-08-25/                Tier 3 — DVV escalation (3 rungs) backup, only if Tier 2 fails
```

Governing documents: `docs/01_DECISION_LOG.md` ADR-115/116/117; `02_METHOD_SPEC.md`
§39.124-130 (the full ruling chain — proposer12/13); `03_COMPUTE_PLAN.md` §R39.81-86
(engineer13/14's pricing chain); `05_STATE.md` §1e/§1f. This is the reverse arm of U-56a
condition 7, still open — R-9's own sequencing already established that forward/reverse are
correlated draws on the *original* corrector-oscillation question (settled, §39.125/126), and
everything in this bundle answers what comes next now that the original question is closed.

## Why three tiers, and why they are NOT three equally-likely options

Each tier tests a **progressively more different** hypothesis about why Candidate A's reverse
restart broke down two points past the region `recorrect=never` already fixed (a
Bulirsch-Stoer/DWI corrector that force-contracted its step and self-terminated at a declared
minimum that failed this project's own distinctness test, §39.126):

- **Tier 1 (StepSize)** — the step was too large for the local curvature; shrink it, keep the
  same predictor/corrector. The mechanistically-matched, best-anchored first bet (§39.127/128).
- **Tier 2 (EulerPC)** — swap the predictor. `proposer13` found (reading Gaussian's own
  documentation directly, not from memory) that `EulerPC` shares the EXACT SAME corrector as
  Tier 1 — it is a **weaker** second bet than originally framed, not an independent one
  (§39.129). Staged for logistics (one round-trip), not because it is expected to outperform
  Tier 1's failure mode if Tier 1 fails on a corrector-side cause.
- **Tier 3 (DVV)** — a genuinely different integrator (velocity-Verlet, adaptive step, no
  shared corrector machinery at all). This is the one tier that can actually **distinguish**
  "the corrector itself is the problem" from "the PES region is just hard for any reasonable
  path-follower" (§39.130) — the real scientific reason to have it ready, independent of the
  round-trip logistics.

**Do not read "staged together" as "equally worth running."** Tier 1 is expected to run. Tiers
2 and 3 are real, priced, ready-to-submit contingencies — not a promotion queue.

## Submission order — read this before touching any `qsub`

1. **Submit Tier 1 (Candidate B) FIRST, unconditionally.**
   `cd candidate_b_reverse_stepsize_2026-08-25/ && qsub submit_candidate_b.pbs`
2. **Read Tier 1's own README's "AFTER the run — mandatory checks" section.** Does it pass or
   fail? "Failed" concretely means: the log shows a repeat `WARNING: Bulirsch-Stoer Method is
   not Converging` near arc 2.0-2.3 (or the `Recorrection`/`stepsize` banner checks show the
   route was silently not honored, in which case the result is uninterpretable and Tier 1
   should be fixed/rebuilt and rerun, not treated as a real failure of the hypothesis).
3. **Only if Tier 1 genuinely failed**: proceed to Tier 2.
   `cd candidate_b2_eulerpc_2026-08-25/` — read that directory's own README in full, including
   its smoke-first sequencing (`submit_eulerpc_smoke.pbs` before `submit_eulerpc_full.pbs`).
4. **Read Tier 2's own README's mandatory checks** (four of them, including the Euler-predictor
   echo check for a silent HPC fallback). "Failed" means the same shared-corrector warning
   recurs, or the checks show EulerPC never actually ran.
5. **Only if Tier 2 also genuinely failed**: proceed to Tier 3.
   `cd candidate_b3_dvv_2026-08-25/` — read that directory's own README in full, including its
   three-rung fallback ladder (try rung 1's smoke; only move to rung 2 if rung 1's smoke
   *errors*; only move to rung 3 if rung 2's smoke *also* errors — rung 3 is flagged
   scientifically undesirable and deserves a second look before spending core-h on it).
6. **Read Tier 3's own README's five mandatory checks** before drawing any conclusion.

At every step: a tier "failing its checks" means the checks were read and show a real negative
result (repeat corrector warning, or a genuinely-completed-but-unhelpful run) — NOT that a job
merely finished, and NOT that a route/echo check itself came back ambiguous (fix and rerun that
tier first in that case, don't escalate past an inconclusive result).

## What "smoke first" means, and where it applies

| tier | smoke recommended? | why |
|---|---|---|
| 1 (StepSize) | **No** — deliberately skipped | a 1-2 point smoke can never reach the arc 2.0-2.3 region that tests the real hypothesis; since cost isn't binding, a full committed run costs no more in practice and gets a real answer (§39.127) |
| 2 (EulerPC) | **Yes** | this tier's keyword COMBINATION itself (not just outcome) is entirely unverified on this cluster (§39.129) |
| 3 (DVV) | **Yes, per rung** | same reason as Tier 2, MORE strongly (§R39.86) — the smoke is also the only cheap way to learn whether `stepsize=2` is honored at all under DVV's adaptive control |

## Cost/wall summary (see each directory's own README/PBS comments for full derivations)

| tier | requested ceiling | wall ceiling @ 64 cores | PBS walltime | margin vs. requested ceiling |
|---|---|---|---|---|
| 1 — StepSize | 134.4-254.1 core-h | 2.1-4.0h | 14h | ~3.5x |
| 2 — EulerPC | 192.0-730.0 core-h (+smoke 1.9-14.6) | 3.0-11.3h | 40h (full) / 1h (smoke) | ~3.5x |
| 3 — DVV | 100.0-1090.0 core-h (+smoke 1.0-32.7) | 1.6-17.0h | 44h (full) / 2h (smoke) | ~2.6x (narrowest — necessity, not a corner cut, see Tier 3's README) |

Combined worst case (all three to full ceiling, single attempt each, unlikely sequencing since
Tiers 2/3 are backups that may never run): 426.4-2,074.1 core-h + smokes (~3-47 core-h) — ~25.2%
of the ~8,238 core-h remaining guard margin at the time of pricing, comfortably not binding
(§R39.86).

## Before submitting ANYTHING in this bundle

1. Confirm `module load gaussian/g16.c01.linda` is still the right module name on the cluster.
2. Check cluster scratch quota.
3. Read the specific tier's own README before running any of its `.pbs` scripts — this file is
   a map, not a substitute for the per-tier detail (mandatory checks, exact grep commands,
   fallback-ladder rules).

**Do NOT run `./run.sh --submit`** for anything in this bundle — every deck here is hand-staged,
deliberately outside the harness (same reasoning as every prior staged batch this round).
