# S3 wave-1, attempt 1 — T21-se STAGE 1 ONLY (2026-08-25)

Staged after the user's GO on the S3 wave-1 slate (`docs/02_METHOD_SPEC.md` §39.136 + all five
addenda, final scope: **2 attempts** — this one and R-B redo; slots 3-4 empty by design).
Governing documents: §39.136 addendum (staged/circuit-breaker protocol), §39.136 fifth addendum
(proposer13's ruling on the stage-limit mechanism, option (a)), §39.138/§39.139 (the `staged`
outcome class), `03_COMPUTE_PLAN.md` §R39.88 §3/§R39.89/§R39.91 (engineer14's pricing).

## What this is — STAGE 1 (the relaxed scan) ONLY, not the full T21-se chain

R-C (`Li+(EC)2•−`, 21 atoms), single-ended relaxed scan — the first stage of the 3-job
scan → `ts_opt`+freq → IRC split that already validated for R-A/R-B. **Stages 2-5
(refine/`ts_opt`/IRC/B+) are NOT built here** — `03_COMPUTE_PLAN.md` §R39.89 is explicit: "T21-se
stages 2-5 remain genuinely unpriced — no number exists for them and none should be
manufactured." This tool builds exactly the one stage this round priced and authorized.

## Why R-C never ran through the production harness before

`U56_RC_scan` was cut from `plan.py` for cost reasons before ever running — see that file's own
comment at line 527-528: "U56_RC_scan (T21-se)는 여기 없다 — §39.41(d) 컷... S3 wave 1로 이동,
삭제 아님" (moved to S3 wave 1, not deleted). This is the first real submission of R-C's scan.
Same construction pattern as `build_wave1_rb_submission.py` (its sibling, read that tool's
docstring for the full reasoning): a `JobSpec` shaped like what the harness's own
`cli.py:build_spec()` would build, `payload/U56.sh`'s EXISTING code path (R-C is already a
valid `SEI_U56_REACTION` value — confirmed by grep of `payload/U56.sh`'s own validation case,
not assumed), no new deck-building logic, no new `plan.py` Item.

## The stage-limit mechanism — SEI_U56_STOP_AFTER=u56_scan

`payload/U56.sh` (this round's Q2 addition, proposer13's §39.136 fifth-addendum ruling, option
(a): an additive, no-op-by-default flag on the existing payload, not a standalone bypass
builder) stops CLEANLY right after its own `u56_scan` stage completes, writing status
`stopped_after_stage` — never a bare completion, never an existing error code (exit 5,
previously unused). `sei_pilot/outcome.py` classifies this `staged` (§39.138/§39.139): not a
retry target (protocol/engine/unknown), not a completed answer (chemical/budget/success), and
per this round's denominator rule, never pooled into either size stratum's numerator/
denominator — a mid-attempt checkpoint isn't a concluded outcome.

Verified end-to-end, not just read from source: `tests/test_u56_stop_after.py` extracts the
real function from `U56.sh` and RUNS it (unset = true no-op, wrong stage = no-op, matching
stage = exit 5 + real `terminal_status.json` via the actual `_write_terminal`→`sei_terminal`
path, with `cause_class: "staged"` and `should_retry` confirmed `False` against the real
written marker) — critic17's own review found and closed a gap here where an earlier version of
this test only checked the marker's status STRING, which would have looked identical whether or
not the consumer (the retry harness) actually handled it correctly.

**This mechanism is a hard sequencing gate, not just a review nicety**: it must not be used
until its own bit-identical-unset-path proof and the outcome-class fix both passed independent
verification (critic17) — both have, see the top-level bundle README's rebuild record.

## Wall cap — a point-density-adjusted circuit breaker, not a cost prediction

R-C's DFT scan needs fine spacing near the GFN2-measured discontinuity
(d(O2-C3) ≈ 1.7-1.8 Å) that R-A's coarser grid didn't need — a POINT-COUNT question, not an
atom-count one (`03_COMPUTE_PLAN.md` §R39.89). R-A's own scan+refine used 22 points for 142.07
core-h (6.46 core-h/point, MEASURED). R-C's point count is CONFIRMED ~40-41 (§R39.91: "matches
my point-density-adjusted option (ii) almost exactly: 41/22 = 1.86x vs my estimated 1.86x").

| | cores | walltime | basis |
|---|---|---|---|
| T21-se stage 1 (scan) | 64 (`select=1:ncpus=64:mpiprocs=64`, matches R-A/R-B) | 22:18:00 (22.3h) | §R39.91: 22.3h wall / 1,428 core-h worst-case exposure — an UPPER-BOUND circuit breaker sized off the confirmed point-count ratio (1.86x R-A's anchor), NOT a forecast of real spend (R-A's own real spend, 294.65 core-h, was far below its 700 core-h ceiling — §R39.90 §1). 1428/22.3 = 64.04 cores, matching R-A/R-B's own count. |

Cost exposure: 1,428 core-h worst-case = 17.2% of the ~8,290.61 core-h reserved-basis margin
(§R39.90) — see the top-level bundle README for the combined wave-1 total.

**If stage 1 hits this wall cap without finishing, the pre-registered decision
(`wave1_2026-08-25/attempts_manifest.json`, slot 1) is STOP AND RE-SCOPE, not resubmit with a
bigger cap.**

## Deployed-package fingerprint guard

Same mechanism as the R-B redo's own copy (see that `README.md`'s own section) — the `.qsub`
refuses (exit 9) if `$SEI_PKG_ROOT`'s recomputed `package_fingerprint` (via `common.sh`'s own
`sei_pkg_fingerprint()`) doesn't match `b94510460851012e`. This is the item `SEI_U56_STOP_AFTER`
most needs: a stale deployed `U56.sh` has no idea what that env var means and would silently
run stages 2-5 — unauthorized, unpriced, and exactly the failure mode the whole staged protocol
exists to prevent.

## 🔴 BEFORE submitting

Same caveats as the R-B redo's own README (deployment path/QC module verification,
`assumptions_not_independently_verified` in `manifest.json`) — not repeated here. Package
rebuild status: DONE, see the top-level bundle README.

## Submit

    cd <pkg_root>/sei_pilot_work/jobs/U56_RC_scan_wave1/
    qsub U56_RC_scan_wave1.qsub

**Do NOT run `./run.sh --submit`** — hand-staged, outside the harness's plan-item/collect
system, same reasoning as every other piece of this round's staged batch.

## AFTER the run — the decision gate, not a continuation

1. Read `terminal_status.json` — expect `status: stopped_after_stage`, `cause_class: staged`
   (confirm it did NOT silently continue past the scan stage — that would mean a stale package
   was deployed and the fingerprint guard above somehow didn't catch it; treat that as a
   protocol-class failure, not a chemistry result).
2. Read the scan's own artifacts (`scan.log` etc.) — did it find a usable maximum along the
   coordinate, within the 22.3h/1,428 core-h envelope?
3. **Human decision gate**: only after (1)-(2) are read does anyone decide whether/how to build
   stages 2-5 (refine/`ts_opt`/IRC/B+) — a SEPARATE build, genuinely unpriced until this stage's
   real result exists (§R39.89). This tool does not, and should not, make that call.
4. Record the real outcome against slot 1 in `wave1_2026-08-25/attempts_manifest.json` — never a
   silently-dropped slot if this attempt fails, times out, or is withdrawn (standing rule 7).
