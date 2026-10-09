# Stage 0 — the MTD-pilot comparator (2026-08-25)

Runs in **PARALLEL** with S3 wave-1 (T21-se stage 1 + R-B redo), not part of its 2-attempt
count — gated by its own independent condition (does an unbiased MD comparator rediscover the
sealed T1-T4 targets on its own?) on a different pipeline stage (S2 product discovery) than
wave-1 (S3 barriers); neither result informs how the other should be read
(`02_METHOD_SPEC.md` §39.136, third addendum).

Governing documents: §39.40(d)-RESULT (the 1-seed/5ps dev-box discovery run, T1 recovered
<1ps), §39.40(e) (targets/grading/BLINDNESS), §39.42(d) (100ps sizing), §39.47(b) (final
ruling: **12 seeds × 100 ps, unbiased NVT, 1500K**).

## What this is

Plain **unbiased** xtb MD (NOT metadynamics — a structurally different route from
`sei_pilot/conformers.py`'s `xtb --metadyn`, B0-D arm 1's conformer-generation tool, a
different job for a different purpose) at the temperature ladder's top rung (1500K), 12
independent seeds, 100ps each, on R-C's reactant (`li_ec2_radical`, 21 atoms, charge 0,
multiplicity 2). Tests whether this cheap comparator alone recovers all four sealed
rediscovery targets (T1: alkyl C-O ring opening = R-A's channel; T2: carbonyl C-O ring opening
= R-B's channel; T3: C2H4 elimination; T4: CO release) — if it does, **the conditional MTD
pilot is never funded for this reaction class** (F13, §39.40(h)).

## New build: `payload/stage0_md.sh` + its own PBS wrapper

No existing src/ tooling covered this route (confirmed by search — `conformers.py`'s MTD path
is a different job; the only prior stage-0-shaped artifact was a hand-run dev-box one-off,
`data/gfn2_pes_precheck_20260820/11_md1500/`, not committed code). Built fresh, reusing the
adjacent pieces that DO apply: `conformers.uhf_from_multiplicity` (xtb wants unpaired
electrons, not 2S+1), the xtb detection pattern from `payload/P3.sh`
(`envpaths.vendored`→PATH→extra-search, tested not just found), and the SAME 12-task
`xargs -P` parallel launcher shape P3.sh already uses.

**`seed=<N>` in the `$md` xcontrol block is a real, working xtb keyword** — verified by
actually running it against this project's own vendored xtb 6.7.1 (not assumed from memory,
per this project's standing rule): two different seed values on the same starting geometry
produced measurably different trajectories (`Etot` differed, `xtb.trj` byte-diff confirmed
non-identical).

## Target-blind by design (§39.40(e)'s own BLINDNESS requirement)

*"The target list is written to a sealed file and its hash recorded in the discovery ledger
BEFORE the first run starts. The classifier is a molecular-graph comparator and contains NO
target templates."* — `stage0_md.sh`'s own post-run classifier follows this exactly: for each
trajectory frame, it computes the covalent bond graph (`sei_pilot.criteria.xyzgraph.bond_list`,
same machinery `guards.py`/`collect.py` already use elsewhere) and reports every bond
broken/formed and every fragmentation event relative to the reactant's OWN starting graph —
generically, with **no hardcoded T1-T4 atom indices anywhere in this build**. (`bond_list`'s
default excludes ionic/Li contacts, so "fragments" means covalently-connected pieces — verified
directly: the reactant itself reports as 3 starting fragments, two EC rings + Li, held together
only by ionic Li-O coordination, which is the expected starting state, not a bug.)

**The sealed T1-T4 target file now exists**, written by `proposer13` per §39.40(e)'s own
BLINDNESS rule (pre-registration, not this coder build's decision):

    src/pilot_package/config/stage0_sealed_targets_T1-T4.json
    sha256: 69ce2848ca346ccc107178104b85dcc4cb7a43212d71bb7c966f6450bbc3f2c2
    sealed: 2026-08-25T09:30:04Z UTC, before any stage-0 submission
    bound to inputs/li_ec2_radical_reactant.xyz sha256 8cdbf3e84f0efebc699f205199487616f6eed5c2c6242927a8d58ca832e29076

Both hashes independently re-verified here (`sha256sum`) against the committed files — match.
The sealed file's `match_rule` fields read directly against `stage0_md.sh`'s own output shape
(`bonds_broken_vs_reactant`/`bonds_formed_vs_reactant`/per-frame fragment formula) — confirmed
by grep against `payload/stage0_md.sh`, no translation layer needed. **Sealed — do not edit in
place**; a changed target definition is a new file + new ledger entry, never a modification of
this one. Matching `stage0_result.json`'s `events` against the sealed `targets` is still a
follow-up read after the run, not something this build does automatically.

## Cores / wall

| | cores | walltime | basis |
|---|---|---|---|
| stage 0 (12 seeds, parallel) | 12 (1 core/seed — ADR-110: explicit, never whole-node/None) | 06:00:00 | ~10 core-h total per §39.42(d)'s own estimate (12 × ~0.54-1.4h-per-100ps-worth of core-h at 1 core, embarrassingly parallel so WALL stays ~1 seed's own time, not 12×). 6h is real margin over the wider (1.4h) of the two single-thread anchors (§39.42(d)'s dev-box figure and this build's own local re-derivation on different hardware, same order of magnitude). |

12 concurrent 1-core tasks fit trivially inside a single node — no node-splitting needed
(§39.47(b): "12 seeds pack trivially").

## Deployed-package fingerprint guard (new this pass)

Same mechanism as the R-B redo's/T21-se's own copy — the `.qsub` refuses (exit 9) if
`$SEI_PKG_ROOT`'s recomputed `package_fingerprint` (via `common.sh`'s own
`sei_pkg_fingerprint()`) doesn't match the value baked in at build time (see `manifest.json`'s
own `deployed_package_fingerprint_check`). Exists because the qsub references a deployment
PATH, not a package — a stale deployment would otherwise run silently with old code. `.cmd.sh`
is untouched by this guard.

## 🔴 BEFORE submitting — same deployment-path caveat as the R-B redo

Built OFFLINE — content correctly references the remote cluster path (`SEI_JOB_DIR`/`SEI_WORKDIR`
point at `/scratch/q656a01/calculation_time_test_pilot/sei_pilot_cpu/sei_pilot_work/jobs/
stage0_mtd_comparator`), but the files themselves sit in this staging directory. Copy
`stage0_mtd_comparator.qsub` + `.cmd.sh` into `<pkg_root>/sei_pilot_work/jobs/
stage0_mtd_comparator/` on the cluster (create it if needed) before `qsub`. Verify the
deployment path is still current — see `manifest.json`'s own
`assumptions_not_independently_verified`. **The package must be the REBUILT one** (see the
top-level bundle README) — same standing requirement as every other piece of this round's
staged batch.

xtb needs no `module load` (vendored binary, detected at runtime the same way `payload/P3.sh`
already does) — nothing to check there.

## Submit

    cd <pkg_root>/sei_pilot_work/jobs/stage0_mtd_comparator/
    qsub stage0_mtd_comparator.qsub

**Do NOT run `./run.sh --submit`** — hand-staged, outside the harness's plan-item/collect
system (same reasoning as `p7_result.json`'s own precedent in
`tests/test_producer_consumer.py` — `stage0_result.json` is read directly by a human per this
README, not through the automated report pipeline; if stage 0 is ever promoted to a real plan
Item, the collector needs updating then, not now).

## AFTER the run

Read `stage0_result.json` directly. Per seed: `normal_termination` (a died seed gets an
explicit `rc: -1`/`note` marker, never a silent gap — standing rule 7), `reactant_fragments`
(the starting covalent-fragment set, for sanity-checking the classifier itself), and `events`
(every frame where the bond graph or fragment set changed vs. the reactant, with the arc time
in ps). **Match `events` against the sealed T1-T4 list once that file exists** — this build
does not do that matching itself.

`ADOPT IF T1 recovered in >= 2 of 3 seeds AND total recall >= T1+T2` / `REJECT IF T1 not
recovered in >= 2 of 3 seeds` (§39.40(e)'s pre-registered grading, unchanged by the seed-count
increase to 12 — read as "at least 2 of the first 3 seeds checked" if a partial early read is
wanted, though the full 12-seed set is what was actually ruled and staged here).
