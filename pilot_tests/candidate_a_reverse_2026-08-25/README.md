# Candidate A — reverse-arm `recorrect=never` IRC restart (2026-08-25)

Staged after `proposer13`'s ruling (`docs/02_METHOD_SPEC.md` §39.125(3)) that stage 4's clean
pass through the shared corrector-failure signature resolves R-9's stage-4-first sequencing
rule to "proceed to candidate A." Governing documents: `docs/01_DECISION_LOG.md` ADR-115/116/117,
`02_METHOD_SPEC.md` §39.124 (proposer12's ruling), §39.125 (proposer13's unblock),
`03_COMPUTE_PLAN.md` §R39.81 (engineer13's pricing), `05_STATE.md` §1e/§1f.

## What this is

Mirror of stage 4's forward `recorrect=never` restart, pointed at `U56_RA_scan`'s
**reverse**-direction checkpoint (`irc_reverse.chk`) instead of forward's. Tests whether the
integrator-tolerance hypothesis that passed cleanly on the forward arm (stage 4,
§39.125(2)) also holds on the reverse arm, at the same measured gradient-angle failure
signature (51.8-59.4° band, both arms).

## Provenance

Built here, not copied, by this project's own `build_u56_ra_irc_recorrect_probe.py`
(idempotency-fixed 2026-08-24, `05_STATE.md` §1f carry-over 3, both critic17 follow-up
findings also closed):

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_ra_irc_recorrect_probe.py \
      --job-dir cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan \
      --out-dir candidate_a_reverse_2026-08-25 \
      --direction reverse --total-cores 64

Checkpoint copy verified byte-identical to the source (md5 `7b4557b055f95d1ece2fb05851f8e037`,
both source and copy); source `irc_reverse.chk` under `cpu_machine_pilot_results/` (read-only
reference tree) was not modified.

**Route explicitly states `maxpoints=30`** — verified in `irc_recorrect_probe.gjf`, not assumed
by checkpoint inheritance. This is the specific ambiguity proposer13 flagged (§39.125(2)):
stage 4's deck predated the maxpoints-explicit fix and never carried the keyword in its own
route text; this deck (built from current `src/`) does.

## Cores / wall

| | cores | walltime | basis |
|---|---|---|---|
| candidate A | 64 (from the deck's own `%nprocshared=64`, verified) | 08:00:00 | 0.72-1.36h pessimistic ceiling (46.1-87.1 core-h / 64 cores, §R39.81's full maxpoints=30/24-new-point outer bound) — 8h cap is a ~5.9x margin, generous for the unsmoked-reverse-direction risk, trivially inside ADR-114's 48h cap |

`GAUSS_NPROCSHARED` is **not** a Gaussian 16 variable and is deliberately absent from the
script, same convention as stage3/stage4.

## BEFORE submitting

1. Confirm `module load gaussian/g16.c01.linda` is still the right module name on the cluster.
2. Check cluster scratch quota (same standing note as the earlier stage3/4/probe5 batch).

## Submit

    cd <this directory>
    qsub submit_candidate_a.pbs

**Do NOT run `./run.sh --submit`** — same reasoning as the stage3/4/probe5 batch
(`u56_diagnostics_resubmit_2026-08-22/README.md`): this is a hand-staged diagnostic deck,
deliberately outside the harness.

## AFTER the run — mandatory check

Same silent-override risk stage 4 carried (§R39.81's own flag, critic15's original catch):

    grep -ac "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log

**Use `-a`, not plain `grep -c`.** G16 logs are binary-flagged (hit directly reading stage4's
own log, §39.125's own note) — plain `grep` on a binary-flagged file gives **no output at all**,
not even `0`, regardless of whether the pattern is present or absent. A blank result is NOT
"0 matches" — it means `-a` was dropped and the check must be rerun correctly before it is
trusted either way. If the count IS `0`, `recorrect=never` took effect. If that line still
appears (count > 0), `recorrect=never` did not take effect and the run says nothing about the
integrator hypothesis on the reverse arm — treat a repeat crash as a false negative, not
evidence.

If `candidate_a_kill.marker` exists, the job was killed before completion (the `trap ... TERM`
is best-effort; this site's PBS SIGTERM grace window is unconfirmed, `[ASSUMPTION]`).

Also check whether the run reaches a genuine stopping condition — a real `maxpoints=30`
exhaustion or a declared PES minimum — rather than stage 4's ambiguous "Maximum number of
steps reached" stop, which proposer13 traced to the pre-fix deck's missing explicit
`maxpoints` keyword (§39.125(2)); this deck should not carry that same ambiguity, but it is a
prediction, not yet a measurement (§39.125, "What remains [UNRESOLVED]").
