# S3 wave-1 bundle (2026-08-25)

Everything in this directory is **staged, not submitted** — the user hand-submits, per this
project's standing rule that expensive jobs are never run silently. Governing document:
`docs/02_METHOD_SPEC.md` §39.136 and its five addenda (final scope, ruled by the user: **2
attempts** — T21-se stage 1 and R-B redo — plus stage 0, which runs in parallel and is NOT one
of the 2 attempts). Compute pricing: `docs/03_COMPUTE_PLAN.md` §R39.88/89/90/91.

## What's in here

| dir | what | attempt? | status |
|---|---|---|---|
| `t21se_stage1/` | T21-se (R-C, 21-atom) — **STAGE 1 ONLY** (the relaxed scan), staged/circuit-breaker protocol | wave-1 attempt, slot 1 | STAGED, not submitted |
| `rb_redo/` | R-B (11-atom) — full chain (scan→`ts_opt`→IRC fwd/rev), a REDO of the rejected `U56_RB_scan` search method (chemistry not rejected, ADR-116) | wave-1 attempt, slot 2 | STAGED, not submitted |
| `stage0/` | 12-seed × 100ps unbiased NVT MD comparator, blind rediscovery of the sealed T1-T4 targets | NOT a wave-1 attempt — runs in parallel, gates a different pipeline stage (S2) | STAGED, not submitted |
| `attempts_manifest.json` | rule-7 pre-registration of the 2 wave-1 attempt slots — read this FIRST | — | current |

Each subdirectory has its own `README.md` (build rationale, cost basis with section citations,
submit instructions, what to read after the run) and `manifest.json` (machine-readable
provenance). This file is the cross-reference / submission-order layer only — it does not
repeat what's already in the sub-READMEs.

## Denominator discipline (standing rule 7 / §39.136 third addendum)

T21-se (21-atom) and R-B (11-atom) are DIFFERENT size strata (§39.39(f)/ADR-087's never-pool
rule) — each is its own n=1, never combined. **Wave 1 produces NO usable rate signal in either
stratum** (n=1 each: 1 − 0.05^(1/1) = 0.95, cannot rule out even p=0.9 from a single attempt).
Its honest deliverables are (a) T21-se's long-overdue cost measurement and (b) one real
chemistry data point for R-B — neither is a rate. See `attempts_manifest.json`'s own
`_reading_rule` for the full statement; do not report either slot's outcome as evidence about a
rate.

A sixth outcome class, `staged` (§39.138/§39.139), now exists alongside the project's
5-class taxonomy (chemical/budget/protocol/engine/unknown) specifically for T21-se stage 1's
deliberate circuit-breaker stop — never a retry target, never pooled into either stratum's
numerator/denominator (a mid-attempt checkpoint isn't a concluded outcome). See
`attempts_manifest.json`'s `_6th_class_note`.

## Cost, against the reconciled reserved-basis margin (§R39.90, 8,290.61 core-h)

| | core-h | % of margin |
|---|---|---|
| T21-se stage 1 (worst-case circuit breaker, not a prediction) | 1,428 | 17.2% |
| R-B redo (measured anchor range) | 303-355 | 3.7-4.3% |
| Stage 0 (parallel, not a wave-1 attempt) | 33-78 | 0.4-0.9% |
| **Wave 1 + stage 0, combined** | **1,764-1,861** | **21.3-22.4%** |

Comfortably fits — smaller than every prior slate priced this round (§R39.91: dropping the 2
unresolved worst-case 11-atom slots removed 710 core-h). Both wave-1 slots' individual cost
bases are cited with section numbers in their own READMEs, not repeated here (Rule 1: "a number
divorced from its route measures an unknown job").

## Package rebuild — DONE, all three staged pairs regenerated against it

This round landed in `src/`: the Q2 stage-limit flag (`SEI_U56_STOP_AFTER`, `payload/U56.sh`),
the R-10 session-digest renderer fix, `recorrect=never` on `irc_forward`/`irc_reverse` AND their
`_rcfc` variants (`config/qc_levels.json`), the `staged` outcome class
(`sei_pilot/outcome.py`), the deployed-package fingerprint guard (all three build tools), and
the sealed-target-hash verification in the stage-0 builder. All of it landed together, ONE
combined rebuild ran after (per lead's sequencing: "R-10 fix + Q2 stage-limit flag land in
src/ → ONE rebuild → critic17 combined verification"):

```
package_fingerprint : b94510460851012e
source_digest       : a550fa5105cd7070
files / tarballs     : 118 / 2
full test suite      : 1817 tests, 0 failures (OK, skipped=14)
```

All three staged `.qsub` files' deployed-package fingerprint guards (right after `common.sh` is
sourced, reusing its own `sei_pkg_fingerprint()` — lands in the generated qsub only, per lead's
explicit scoping; `common.sh` itself is untouched) were regenerated AFTER this rebuild and carry
this exact fingerprint (`grep SEI_EXPECTED_PKG_FINGERPRINT` any of the three `.qsub` files to
confirm) — **if the deployed package's own recomputed fingerprint ever
stops matching `b94510460851012e`, every one of these three jobs refuses to run (exit 9) rather
than silently executing under stale code.**

## Verification status — what's confirmed and by whom

- **critic17's 43rd-batch review** (`docs/04_REVIEW_LOG.md`) covered the package (bit-identical
  unset-path proof for `SEI_U56_STOP_AFTER`, fingerprint independently recomputed from the
  extracted tarball, full suite green) and found 1 blocker + 3 real defects in this round's
  work-in-progress state. **All 4 are now fixed and locally tested** (see below) — this is the
  state ready for critic17's FINAL recheck pass on the combined round, not yet independently
  re-verified by them.
- Blocker (`stopped_after_stage` falling through to `unknown`/retryable): fixed via proposer13's
  `staged` ruling (§39.138/§39.139), landed in both `CAUSE_BY_STATUS` AND `CLASS_SEVERITY`
  (critic17's own follow-up catch: the first fix alone left `aggregate_cause` still broken) —
  tested against the CONSUMER's behavior (`should_retry`/`aggregate_cause`), not just the
  producer's status string, per critic17's explicit lesson.
- `irc_*_rcfc` `recorrect=never`: landed, tested, confirmed inert today (switch is off,
  `irc_hessian_source=calcfc`).
- Stage-0 manifest hand-edit drift: root-caused to my own hand-edit landing right before the
  sealed file's proper delivery — fixed by moving hash computation AND verification-against-an-
  expected-value into the builder itself (`build_wave1_stage0_submission.py`), tested that it
  refuses to build on a hash mismatch, before any file write.
- Deployed-package fingerprint guard: per the lead's explicit scoping (generated qsub only,
  zero shared-file blast radius, `common.sh` wiring deferred to its own slot) and critic17's
  pre-build note (reuse `common.sh`'s own `sei_pkg_fingerprint()` so a renamed `--workdir`
  doesn't false-alarm; name the two known false-alarm causes in the refusal message), added to
  all three build tools -- T21-se needed it most, a stale `U56.sh` deployment has no idea what
  `SEI_U56_STOP_AFTER` means and would silently run stages 2-5, unauthorized and unpriced.
  Landing it in the qsub (not `.cmd.sh`, where an earlier version of this guard briefly lived)
  resolved last round's flagged byte-identity tension for free: R-B's `.cmd.sh` is now IDENTICAL
  to the original historical harness output, no special-casing needed; only the qsub's own
  regression test strips the guard block before comparing (`tests/test_build_wave1_rb_submission.py`).

**Sequencing gate, unchanged and still binding**: per proposer13's §39.136 fifth addendum, the
`SEI_U56_STOP_AFTER` bit-identical-unset-path verification must complete and pass, independently,
before `U56.sh` in its modified form is used for anything — critic17's 43rd batch already
confirmed this for the pre-fix state; the `staged`-class fix above does not touch the unset
path (verified: `tests/test_u56_stop_after.py`'s unset/wrong-stage no-op tests are unchanged and
still pass), so the original bit-identical proof still stands, but critic17 should confirm that
reading independently before this bundle is treated as fully cleared.

## Sealed T1-T4 target file (proposer13's pre-registration, §39.40(e))

Delivered and verified this round: `src/pilot_package/config/stage0_sealed_targets_T1-T4.json`,
sha256 `69ce2848ca346ccc107178104b85dcc4cb7a43212d71bb7c966f6450bbc3f2c2`, sealed
2026-08-25T09:30:04Z UTC, bound to the reactant's own hash. `stage0/manifest.json`'s
`sealed_targets_file` block and `stage0/README.md` both point at it. The stage-0 builder now
verifies the committed file's hash against an expected value baked in at build time
(`SEALED_TARGETS_SHA256_EXPECTED` / `--sealed-targets-sha256`) and REFUSES to build if they
don't match — an in-place edit of the sealed file (forbidden by its own header) is now
detectable, not silently reported as still-sealed.

## Submission order

No hard dependency between the three pieces — they can be submitted independently, or all at
once, subject to critic17's final sign-off above. Suggested order if doing them one at a time:

1. **Stage 0** first if there's any appetite to let its result inform whether the conditional
   MTD pilot is worth designing before wave 1 returns (§39.40(h)) — though §39.136 third
   addendum is explicit that neither result should be read as informing the other's
   interpretation; this is a scheduling convenience, not a scientific dependency.
2. **R-B redo** — cheapest (303-355 core-h), full chain, fastest to a real classified outcome.
3. **T21-se stage 1** — largest single exposure (1,428 core-h worst-case), and its own result
   gates whether stages 2-5 are ever built at all; nothing else in this bundle depends on it.

## What "fails" means, per piece — so a null/negative result isn't misread as this bundle broke

- **T21-se stage 1**: `stopped_after_stage`/`staged` is the EXPECTED, successful outcome of a
  circuit breaker doing its job — it is not a failure. A wall-cap kill before the scan stage
  finishes IS the failure case, and per `attempts_manifest.json` slot 1, the pre-registered
  response is STOP AND RE-SCOPE, not a bigger resubmit.
- **R-B redo**: any of the 5 (6, counting `staged`, though R-B never sets `SEI_U56_STOP_AFTER`)
  outcome classes is a valid, recordable result per standing rule 7 — a `chemical`-class
  rejection (e.g. another mode-character failure) is real information, not a bundle defect.
- **Stage 0**: a per-seed died run gets an explicit `rc: -1`/note marker (never a silent gap);
  `ADOPT`/`REJECT` against the sealed targets is the pre-registered grading (§39.40(e)),
  `REJECT` is a valid, useful result (it means the conditional MTD pilot stays justified for
  this reaction class), not a failure of this build.
- **Any of the three refusing to run via the fingerprint guard (exit 9)**: means the deployed
  package doesn't match what was staged — a deployment/process problem, not a chemistry result.
  Rebuild+redeploy, don't reinterpret the (nonexistent) output as a verdict.

## After all three return

Record each slot's real `outcome_class` in `attempts_manifest.json` (never leave `null` silently
— standing rule 7's denominator discipline starts at staging, not analysis). Read stage 0's
`stage0_result.json` against the sealed T1-T4 list (a human/analyst step, deliberately not
automated by the target-blind classifier itself).
