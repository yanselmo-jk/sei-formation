# U56 diagnostics — stage 3 / stage 4 resubmit (2026-08-22)

Staged by lead per **ADR-117** after PBS job 23731675 was wall-killed
(`walltime 7244 exceeded limit 7200`). Governing documents:
`docs/01_DECISION_LOG.md` ADR-115/116/117, `docs/05_STATE.md` §1e,
`docs/03_COMPUTE_PLAN.md` §R39.79, `docs/04_REVIEW_LOG.md` 25차 배치.

## Provenance

Deck **files** copied from `cpu_machine_pilot_results/u56_diagnostics_2026-08-21/`,
which is a **read-only returned-results tree and was not modified**. Directories were
deliberately NOT copied wholesale: that would have dragged stage 3's stale mid-write
`stability_probe.chk` and ~155 MB of `Gau-*` scratch into the run directory,
reintroducing the truncated-checkpoint risk the clean-restart ruling avoids.

- stage 3: `stability_probe.gjf`, `probe_point.xyz`, `manifest.json`
- stage 4: `irc_recorrect_probe.gjf`, `manifest.json`, and
  `irc_forward_recorrect_probe.chk` — this one **is genuine input** and travelled
  byte-exact (md5 `87a378633c55f4df0021f133943cfe97`, verified after copy).

**One single edit was made to any copied deck**: stage 3's `%nprocshared` 1 → 4. Nothing else.

### probe 5 — newly built, not copied

`5_ra_crash_geometry/` was **generated here**, not copied, by the project's own existing
builder with no code changes:

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_ra_stability_probe.py \
      --geom-log <repo>/cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan/irc_forward.log \
      --total-cores 1 --out-dir <this dir>/5_ra_crash_geometry

It closes the residual gap ADR-115 leaves open. Stages 1 and 2 probed arc 1.71 and arc 6.83
— the last *converged* IRC path point. The crash happens ~20 corrector sub-iterations later,
and those trial geometries **are** on disk and converged (`irc_forward.log:21790-30456`, 20
complete `Input orientation:` blocks). `--geom-log` mode takes the log's LAST geometry, which
is the block at `:30018` — the final trial geometry before the corrector gave up, 456 lines
before the error termination at `:30457`. Verified: 11 atoms, and **different** from the
arc-6.83 probe's geometry (an identical geometry would have made the probe worthless).

🔴 **Provenance caveat — read the manifest with this in mind.** The builder's `--geom-log`
mode hardcodes `"source_kind": "certified_geometry_log"`. **This geometry is NOT certified.**
It is a crash-region corrector trial geometry from a job that error-terminated. The label is
a limitation of the existing tool, left unedited on purpose (changing the tool is a code
change this round does not need). Likewise `mo_coefficient_warnings_first_last` spans the
whole log (lines 745 → 30364, 132 warnings), not the crash region specifically; the value
nearest this geometry is the beta coefficient 38.6541 at `:30364`.

**Reading it**: STABLE closes ADR-115's residual gap and makes the falsification complete
through the actual failure point. UNSTABLE would mean the instability is confined to the
crash region that stages 1/2 could not see — which would **partly reopen ADR-115** and make
stage 4's result much harder to interpret alone. Either way the cost is ~0.7 core-h.

## Two jobs, never one

Stage 3 and stage 4 test independent, non-substitutable hypotheses (§39.114(2)). A shared
walltime budget is exactly what starved stage 4 last time. They may run concurrently and
need no ordering relative to each other.

| | cores | walltime | basis |
|---|---|---|---|
| stage 3 | 4 (from the deck's `%nprocshared=4`) | 16:00:00 | >2× over the 30 core-h ceiling at 4 cores (~7.5 h) |
| stage 4 | 1 | 30:00:00 | 1.5× over the pessimistic 20 core-h bound at 1 core |
| probe 5 | 1 (from the deck's `%nprocshared=1`) | 06:00:00 | stages 1/2 measured 0.514 / 0.728 core-h on the same 11-atom system; ~8× margin |

Both inside ADR-114's 48 h cap.

`GAUSS_NPROCSHARED` is **not** a Gaussian 16 variable (G16 uses `GAUSS_PDEF`) and is
deliberately absent from both scripts. Cores come from the deck, as every production job
on this project already does (`U56_RA_scan/irc_forward.gjf:1` = `%nprocshared=64`).

## BEFORE submitting

1. **Check cluster scratch quota.** A walltime SIGKILL commonly orphans scratch in the
   compute node's `$GAUSS_SCRDIR`, which cannot be inspected from the workstation. The
   previous kill left ~155 MB of orphaned `Gau-*` files in the returned tree alone, and a
   second kill would leave another set on the compute side. Nothing has been deleted —
   that is the user's call.
2. Confirm `module load gaussian/g16.c01.linda` is the right module name on the cluster.

## Submit

    cd <this directory>
    qsub submit_stage3.pbs
    qsub submit_stage4.pbs
    qsub submit_probe5.pbs

Three separate jobs. They are independent and may run concurrently.

**Do NOT run `./run.sh --submit`.** These are hand-submitted diagnostic decks, deliberately
outside the harness. Routing them through it risks the `extra_env`/`spec_digest` stale
branch, which runs *before* the `cause_class` check and could auto-fire `U56_RA_scan`'s
measured 336 core-h to repeat a known crash (`docs/05_STATE.md` §1d).

## AFTER the runs — mandatory checks

**Stage 4 — check this BEFORE interpreting the result at all:**

    grep -c "Recorrection delta-x convergence threshold:" 4_irc_recorrect_restart/irc_recorrect_probe.log

`irc=restart` may take its options from the checkpoint and **silently drop
`recorrect=never`**. If that line still appears, the option did not take effect and the run
says **nothing** about the integrator hypothesis — a repeat crash would then be a false
negative, not evidence. Nobody had priced this branch until critic15 found it.

**All three jobs:** if `stage3_kill.marker` / `stage4_kill.marker` / `probe5_kill.marker` exists, the job was killed
before completion — the marker names which stage and when. (The `trap ... TERM` is
best-effort: this site's PBS SIGTERM grace window is unconfirmed, `[ASSUMPTION]`.)

**Stage 3 scope caveat, whatever it returns:** `endpoint_prep_rc_reactant` is a **neutral**
Li(EC)₂ doublet (`Charge = 0 Multiplicity = 2`), as is every other job in this batch. Do
not report the result as a statement about "the cation+open-shell class" — that claim's
dataset has zero charge variance. Report it as what it is: a 21-atom neutral doublet at
334 basis functions.
