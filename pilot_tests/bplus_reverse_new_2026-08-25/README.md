# B+ terminal optimizations — closing U-56a condition 7's reverse branch (2026-08-25)

Staged after `proposer13`'s ruling (`docs/02_METHOD_SPEC.md` §39.131) that Candidate B's
`StepSize` hypothesis is CONFIRMED: the reverse IRC ran a clean, full 70-point ceiling walk,
zero corrector warnings anywhere. Governing documents: `docs/01_DECISION_LOG.md`
ADR-115/116/117; `02_METHOD_SPEC.md` §39.124 (Ruling 2's branch-(b) AND-block, Ruling 1's
reactant-match tolerance), §39.131 (this build's spec); `05_STATE.md` §1f "CANDIDATE B
RETURNED". These are the LAST two jobs needed on this work item — everything else (`EulerPC`,
`DVV`) is now formally **MOOT** for this question (§39.131(4)), not deleted, just not needed.

## What these are

Two `opt=(loose,maxcycles=100)` terminal optimizations, same route family as the ORIGINAL
`bplus_reverse_mid/last` jobs this reaction already ran
(`cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan/bplus_reverse_{mid,last}.gjf`) —
**verified byte-identical route**, only the starting geometry differs:

- **`bplus_reverse_mid.gjf`** — starts from **Point 35** (arc 2.38953) of Candidate B's
  returned `irc_stepsize_probe.log`, the arc-length MIDPOINT of the 70-point walk.
- **`bplus_reverse_last.gjf`** — starts from **Point 70** (arc 4.77975), the final path point.

## Which two points, and how this was verified NOT to be row-counting by eye

`sei_pilot.guards.bplus_sample_points()` (`guards.py:768-788`) picks the arc-length midpoint
and the final point from the log's own printed arc values — never by index. The new tool built
for this job (`src/pilot_package/tools/build_u56_bplus_reverse_opt.py`) calls this function
**directly against the real returned log**, then **cross-checks its own result against
`proposer13`'s independently-derived §39.131 values** (Point 35/arc 2.38953, Point 70/arc
4.77975) and refuses to build anything if they disagree beyond a tight tolerance. They matched
exactly — confirmed twice, independently (proposer13's own run, and this tool's own run),
recorded in `manifest_mid.json`/`manifest_last.json`'s `picked_by` field.

## Provenance

    PYTHONPATH=src/pilot_package python3 src/pilot_package/tools/build_u56_bplus_reverse_opt.py \
      --irc-log pilot_tests/candidate_b_reverse_stepsize_2026-08-25/irc_stepsize_probe.log \
      --out-dir pilot_tests/bplus_reverse_new_2026-08-25 \
      --total-cores 64

Route verified identical (diffed directly) to the original `bplus_reverse_mid.gjf`'s own route
line: `#p nosymm wB97XD/gen scrf=(pcm,solvent=acetone,read) opt=(loose,maxcycles=100)
Int(Grid=UltraFine)`. `job_type=endpoint_opt_rough` (`config/qc_levels.json`) — the SAME,
already route-smoked job type every real production job in this project has used; this is the
**lowest-risk** deck built on this whole work item, unlike every IRC-tier tool before it.

## Cores / wall

| | cores | walltime | basis |
|---|---|---|---|
| `bplus_reverse_mid` | 64 (`%nprocshared=64`, verified) | 02:00:00 | MEASURED anchor, not an estimate — the ORIGINAL `bplus_reverse_mid.gjf` (same route/class) measured 12.51 core-h consumed / 14.66 core-h reserved (85% efficiency) at 64 cores. 2h is a >8x margin over the measured 13m45s elapsed. |
| `bplus_reverse_last` | 64 | 02:00:00 | MEASURED — original `bplus_reverse_last.gjf` measured 8.04 core-h consumed / 10.32 core-h reserved (78% efficiency). 2h is a >12x margin over the measured 9m41s elapsed. |

`GAUSS_NPROCSHARED` is **not** a Gaussian 16 variable and is deliberately absent from both
scripts, same convention as every other staged deck in this project.

**Two separate PBS scripts, not one combined one**: same one-job-per-`qsub` convention as every
other staged deck this round. These two optimizations have no sequencing dependency on each
other (unlike the smoke-then-full tiers) — independent submission/monitoring/kill markers is
the simpler, more consistent choice, not a special case.

## BEFORE submitting

1. Confirm `module load gaussian/g16.c01.linda` is still the right module name on the cluster.
2. Check cluster scratch quota (same standing note as every earlier staged batch).

## Submit

    cd <this directory>
    qsub submit_bplus_mid.pbs
    qsub submit_bplus_last.pbs

Independent jobs, may run concurrently. **Do NOT run `./run.sh --submit`** — same reasoning as
every earlier staged batch: these are hand-staged diagnostic decks, deliberately outside the
harness.

## AFTER the runs — computing `bplus.agreement` + `reactant_match(last)`

**This is deliberately NOT new code.** Condition 7 branch (b)'s remaining two conjuncts are
computed by the SAME functions the production harness already uses for every B+ pair in this
project: `sei_pilot.guards.bplus_agreement()` (`guards.py:428`) and
`sei_pilot.guards.reactant_match()` (`guards.py:593`, `REACTANT_MATCH_TOLERANCE_ANG=0.05` Å,
`guards.py:572`), called from the exact Python block already embedded in `payload/U56.sh`'s own
`PYBPLUS` heredoc (search that filename, not a line number -- see step 4 below for why) --
the same code that produced `bplus_forward.json`/`bplus_reverse.json` for every earlier B+
pair on this reaction. Reuse it verbatim, do not re-derive it:

1. **Make a WORKING COPY of `U56_RA_scan`'s job directory** — never write into
   `cpu_machine_pilot_results/` itself (read-only reference tree):

       cp -r cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan /tmp/U56_RA_scan_bplus_v2

   This copy already has the three files the computation needs (nothing to fetch):
   `u56_R-A_mapping.json`, `endpoint_certs.json`, `reactant_certified.xyz`.

2. **Backfill the reactant's converged energy into the WORKING COPY's `endpoint_certs.json`
   ONLY — never into `cpu_machine_pilot_results/` itself (read-only reference tree, standing
   rule).** `proposer13` ruled (§39.132, `02_METHOD_SPEC.md`): the energy clause is NOT
   droppable (a distance-only reading would pass a Li-coordination isomer — the project's own
   measured 0.686 eV/same-graph counterexample), but no NEW computation is needed either — the
   certified reactant's converged SCF energy already exists in
   `endpoint_prep_reactant/endpoint_tight.log`. **Independently re-verified here, not
   inherited**: `grep -a "SCF Done" .../jobs/endpoint_prep_reactant/endpoint_tight.log` — final
   converged value **-349.620897014 Hartree** (identical across the last 3 SCF evaluations in
   that log, `Charge = 0 Multiplicity = 2`, route
   `wB97XD/gen scrf=(pcm,solvent=acetone,read) opt=(tight,calcfc...` — same functional/basis/
   solvent as this reaction's whole TS chain, `grep -ac "Normal termination"` → 2). This is
   real primary-log data, sourced the same way every other field in `endpoint_certs.json`
   already is — **NOT** the `SEI_C8_ENDPOINTS_JSON` fixture-injection channel (see the warning
   below for why that channel does not apply here).

   🔴 **Wrong-sibling hazard — locate this log by PROVENANCE, never by `find`/glob.**
   `critic17` made this exact mistake on their own first pass: five near-identical
   `endpoint_tight.log` files exist under `cpu_machine_pilot_results/sei_pilot_work/jobs/`
   (`endpoint_prep_reactant`, `endpoint_prep_reactant_epsinf_full`,
   `endpoint_prep_reactant.reset.*`, `endpoint_prep_rc_reactant`, `endpoint_prep_product` —
   verified by `find ... -iname "endpoint_tight.log"`, 5 hits: the 4 WRONG siblings above plus
   the 1 correct one) — and the ε∞ sibling (`endpoint_prep_reactant_epsinf_full/
   endpoint_tight.log`, `-349.620897959` Hartree, independently re-derived here too) sits only
   **2.6e-5 eV** from the correct value — close enough to pass a casual spot-check while being
   the wrong log entirely, AND it matches the naive glob `endpoint_prep_reactant*`. Its route
   is the tell if checked directly: `scrf=(pcm,solvent=generic,read)` (independently confirmed
   here, `grep -a scrf= .../endpoint_prep_reactant_epsinf_full/endpoint_tight.log`) — NOT
   `solvent=acetone`, this reaction's real solvent, the one every other deck in this project
   uses. Do not search for `endpoint_tight.log` by filename. Instead, get the directory name
   from the WORKING COPY's own `endpoint_certs.json`, which already records it:
   `reactant_source` →
   `["cert:endpoint_prep(endpoint_prep_reactant)", "geometry:endpoint_tight.log"]` — the first
   element names the exact directory (`endpoint_prep_reactant`, not any of its siblings).
   Cross-check with `reactant_cert.solvent_config`, which must CONTAIN `eps=18.5` (the acetone
   PCM deck this reaction's whole TS chain uses) — the ε∞ sibling's own log would show a
   different solvent block if checked the same way.

   Edit the WORKING COPY's `endpoint_certs.json` (`/tmp/U56_RA_scan_bplus_v2/endpoint_certs.
   json`), adding one key inside the existing `reactant_cert` object:

       "reactant_cert": {
         ...  (leave every existing key as-is)
         "energy_hartree": -349.620897014,
         "energy_hartree_label": "[MEASURED, from endpoint_tight.log, backfilled per §39.132]"
       }

3. **Copy the two new returned logs into the working copy, under the EXACT names the harness
   code expects** (`bplus_<direction>_<tag>.log`) — this deliberately **overwrites the copy's
   own old `bplus_reverse_mid.log`/`bplus_reverse_last.log`**, since these new optimizations,
   from Candidate B's clean path, are what `proposer13`'s ruling says should be compared now,
   superseding the old crashed-path comparison:

       cp bplus_reverse_mid.log  /tmp/U56_RA_scan_bplus_v2/bplus_reverse_mid.log
       cp bplus_reverse_last.log /tmp/U56_RA_scan_bplus_v2/bplus_reverse_last.log

4. **Extract the harness's own computation code, unmodified, and run it.** Do NOT use a fixed
   `sed -n '<line>,<line>p'` range — this heredoc's exact line numbers have already drifted
   TWICE this round from unrelated comment edits elsewhere in the same file (once by 7 lines,
   once by another 3), each time silently truncating a hardcoded-line-range extraction with no
   error message. Use this `awk` extraction instead, which locates the heredoc by its own
   delimiter markers and is immune to any line-number drift anywhere else in the file:

       awk "/<<'PYBPLUS'\$/{flag=1;next}/^PYBPLUS\$/{flag=0}flag" \
         src/pilot_package/payload/U56.sh > /tmp/bplus_compute.py
       python3 -c "import ast; ast.parse(open('/tmp/bplus_compute.py').read())"  # sanity check
       SEI_PKG_ROOT=src/pilot_package python3 /tmp/bplus_compute.py \
         /tmp/U56_RA_scan_bplus_v2 reverse ok R-A

   This runs the extracted code with the same arguments the harness itself would pass
   (`direction=reverse`, `pick_status=ok` since both jobs succeeded, `rxn=R-A`). The `ast.parse`
   sanity check line is cheap insurance: if it ever raises `SyntaxError`, the extraction pulled
   the wrong text (e.g. `payload/U56.sh` gained a second block also closed by a bare `PYBPLUS`
   line) — stop and re-check by hand rather than running a truncated/wrong script.

   **Use `SEI_PKG_ROOT=`, not `PYTHONPATH=`** — the extracted code reads
   `os.environ["SEI_PKG_ROOT"]` directly (line 2, `sys.path.insert(0, ...)`) and raises
   `KeyError` immediately if it is unset, before even reaching its imports; `PYTHONPATH` alone
   is not enough (verified by running it both ways).

   This writes `/tmp/U56_RA_scan_bplus_v2/bplus_reverse.json` (same shape as every other B+
   verdict in this project) and prints a one-line summary:
   `[U56] B+ reverse: agreement=<...> reactant_match(mid/last)=<...>/<...>`.

5. **Read `bplus_reverse.json` directly — record the number, not just the boolean.** Per
   Ruling 2 (§39.124 addendum), condition 7's own text binds `reactant_match["last"]` ONLY — do
   not AND it with `reactant_match["mid"]` (mid is useful diagnostic data, not part of the
   gate). `bplus.agreement` requires `covalent_graphs_match AND energy_delta_ev <= 0.001 eV`
   between the mid/last optimized geometries (`guards.bplus_agreement`'s own criterion).

   🔴 **Do not stop at `match: true`/`false` — read `reactant_match["last"]["energy_delta_ev"]`
   itself and judge how close it sits to the 0.001 eV tolerance, not just which side of it.**
   `guards.py:572-582`'s own caveat: this comparison is inherently `tight`-optimized-reactant vs.
   `loose`-optimized B+ point, a method mismatch that already consumes real tolerance budget on
   its own, independent of whatever chemistry is being tested — the ORIGINAL pair (this
   README's own dry-run below) measures **Δ=-4.13e-4 eV** from that systematic alone, **41% of
   the 1.0e-3 eV budget consumed before any physical difference is in the number at all.**
   Reading rule: `energy_delta_ev` **comfortably below** ~4e-4 (i.e. no worse than the known
   tight/loose systematic) reads as a clean pass. A value **materially above ~4e-4 while still
   under 1.0e-3** is **MARGINAL, not clean** — the tolerance budget is being spent on something
   beyond the known method-mismatch floor, and per `guards.py`'s own stated caveat ("should not
   be leaned on that close to the tolerance in a future, closer case") this should be flagged
   for `proposer` review rather than read as a boolean pass closing condition 7 outright.

**Preview, run against the ORIGINAL `bplus_reverse_mid/last.log` as a pipeline dry-run (not
this build's own new jobs, which have not returned yet)**: with the §39.132 backfill applied,
steps 2-5 above produce `agreement: true` and `reactant_match["last"]["match"]: true`
(`energy clause PASSES: 0.000413 eV against tolerance 0.001 eV` — this is the same
tight/loose-systematic 4.13e-4 eV `guards.py:579` already records for exactly this pair, so it
reads as clean by the rule above, not marginal; `distance clause PASSES: 0.0005 Å against
tolerance 0.05 Å`) — a real, non-`None` verdict on the OLD crashed-path comparison points. This
is a pipeline check only, not a preview of what THIS build's new mid/last jobs will return
(different starting geometries, Candidate B's clean 70-point path, not the old 6-point crashed
one) — but it confirms the backfilled pipeline itself produces a real true/false answer rather
than an unresolved `None`, and leaves only **59% of the 0.001 eV budget** for whatever real
signal the NEW points' own comparison shows — exactly why the marginal-reading rule above
matters for reading the new result, not just this dry-run.

🔴 **`critic17`, 36th review batch: `SEI_C8_ENDPOINTS_JSON` does NOT backfill an
already-returned cert — do not use it for step 2 above.** It is read only inside `U56.sh`'s own
certification-WRITING block (`U56.sh:167`), reached during a live harness run through
`resolve()`, never by the isolated post-processing snippet in step 4. Setting the env var and
re-running step 4 does nothing at all, silently. Worse, `U56.sh:173` stamps anything that comes
through that channel `"[FIXTURE] -- test injection, not a certification"` (`P1.sh:86` calls it
a test-only injection channel; both `local.sh.tmpl`/`pbs.sh.tmpl` unset it before a real job
runs) — routing this gate's real verdict through it would close U-56a condition 7's reverse
branch on data explicitly labeled as NOT a certification. Step 2's direct JSON edit, sourced to
a real primary log and re-verified independently above, is not that channel and does not carry
that problem. (Two comments inside `U56.sh`'s own `PYBPLUS` block and its certification block
made the same wrong `SEI_C8_ENDPOINTS_JSON` claim this README once inherited — both fixed,
comment-only, so everyone who reads that gate's own source sees the correction, not just this
README. Line numbers deliberately not quoted here — see step 4's own note on why line numbers
in this file are not stable enough to cite.)

If either optimization job did NOT converge or errored, do not run step 4 with `pick_status=ok`
— an unrun/failed comparison is not an agreement (the harness code's own stated principle,
`guards.py`/`U56.sh` comments throughout this codebase).

## `EulerPC`/`DVV` status — MOOT for this question, independent of how B+ turns out

Per `proposer13` §39.131(4): both backup tiers hedge against the Bulirsch-Stoer corrector
non-convergence failure mode, which did not recur anywhere in Candidate B's 70-point walk. If
B+ agreement or `reactant_match` come back failing, that is a *different* question — whether
the reverse arm's terminal region connects to the same basin as the certified reactant, a
chemistry/multiple-basin question neither `EulerPC` nor `DVV` would answer differently (both
differ from `StepSize` only in which numerical integrator walks the path, not in which basin it
walks toward). Both tiers remain correctly-specified, honestly-priced contingency work,
stood down rather than retracted — not needed here, not deleted from the record.
