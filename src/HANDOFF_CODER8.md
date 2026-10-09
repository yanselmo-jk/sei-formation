# coder8 → successor. ADR-090 §5 (the guard-reach round), session of 2026-08-19.

> **A separate file from `HANDOFF_TO_LEAD.md` and `HANDOFF_CODER6.md`, on purpose** — same reason
> coder6 gave: those files are long, and appending buries this. 🔴 **Read
> `HANDOFF_TO_LEAD.md` §0 and §45, and `HANDOFF_CODER6.md`'s READ-THIS-FIRST block, first anyway** —
> everything in them still holds except the two rows coder6 marked NOT DONE, which this file
> closes out (B-1, B-2, B-5 are now DONE; see below). This file is the delta for one more session.

---

# 🔴 READ THIS FIRST — live state, what is deliberately absent, what is merely undone

## LIVE
```
source_digest   12c793d774e87d08      ← CURRENT identity, built by me, verified by the lead
                                          independently against the same tree.
tests           1232 OK (skipped=8)   (1204 at the ADR-090 handoff below; +28 this extension)
[stamp]         ✅ GREEN               tarball matches source
cpu items       10 (was 9)             endpoint_prep_reactant added, reachable from ./run.sh
```
🔴 **Everything below the next divider (LIVE block's old contents, §A-§D) describes the
ADR-090 guard-reach round and is now HISTORICAL** — `source_digest 2042753e1537ee64` no longer
exists on disk. It is kept verbatim because §A-§D's FINDINGS (H-1 through H-6) are still true and
still the most reusable part of this file. Only the digest/test-count/provenance at the top were
stale; see **§E below** for what changed since.

🔴 **PROVENANCE, RECORDED SO IT IS NOT RECONSTRUCTED WRONGLY**: I ran `bash src/make_package.sh`
once, mid-round, while the ADR-086 parallel-work window was open, believing (correctly, per ADR-086)
that the rebuild was released to me. **The lead ALSO ran it, separately, after two of their own
release messages crossed my idle without me acting on them.** The two `sha256`s in every report from
both of us are identical, which means there was only **one** actual bake — gzip embeds mtime, so two
independent runs seconds apart produce different sha256 even over identical content. Whichever of us
you believe built it, the artefact on disk is consistent and verified by both. **Do not read "two
people ran the build" as "there were two builds."** There was one; we each confirmed it independently.

## 🔴🔴 DELIBERATELY ABSENT vs MERELY UNFINISHED — the distinction that will cost you if you miss it

**A successor "fixes" the first kind. Do not.** Everything in coder6's own table (`b0_plan.size()`
nulls, `check_against_guard`'s `fits: None`, `solvent.DESCRIPTORS = {}`, `acceptance.omega_threshold
= null`, `curvature` verdict `None`, `arm2` extended path, point-group detection) **still holds,
unchanged.** New rows this session:

| thing | status | 🔴 if you "fix" it |
|---|---|---|
| `guards.require_ts_precondition` has NO caller | **DELIBERATE, and load-bearing** | It is in `tests/test_guard_reach.py`'s `BLOCKED_ON_DECISION` bucket, not `KNOWN_OPEN_DEFECTS`, ON PURPOSE. Wiring it onto `payload/P1.sh`'s live QST2 launch **halts P1 entirely** — the shipped `inputs/li_ec_radical_{reactant,product}.xyz` declare themselves "GUESS GEOMETRY (idealized, not optimized)" in their own header, and no pre-optimisation step exists anywhere in the pipeline to give the guard real data. This is not an oversight; it is a scope decision routed to `proposer6` (spawned for exactly this — see §B below). **Do not wire it before that ruling lands.** `test_blocked_on_decision_guards_are_not_wired_onto_a_live_path` will fail loudly if you do, and that failure is the point, not a bug in the test. |
| `evaluate_p1`'s `c10_cost_probe_violations` reports but never gates | **DELIBERATE** | `guards.cost_probe_violations` fires on **every** P1 result unconditionally, because P1 is, by construction, a chemistry-verdict pilot and C-10 was adopted on the premise that P1 is a cost probe — the constraint and the artefact disagree about what P1 *is*. Folding the violation into `fail_reasons` would make a genuine `pass` read as gated when nothing gates it. Reported as `c10_note`, deliberately not mixed into `fail_reasons`. Also routed to `proposer6` — it is the SAME underlying "what is P1?" question as the row above, not a separate one. |
| `tests/` does not ship in either tarball | **OPEN, packaging-scope, NOT an oversight** | Confirmed by both the lead and me independently (`tar tzf ... \| grep -c '/tests/'` → `0`). This means `tests/test_guard_reach.py` — this round's actual mechanism for catching an unreached guard — **does not travel with the artefact the user runs.** The reach test protects the *repo*, not the *delivery*. Whether tests should ship is a packaging decision the lead is ruling on after critic8's pass. **Do not move `tests/` into the package yourself.** |
| `require_nosymm_if_needed` has no caller | **DELIBERATE (category B), same as coder6's arm2/point-group rows** | `guards.NOSYMM_BLOCKING_ENTRY` names it: blocked on B0 collector wiring (NOT STARTED). The production route TEMPLATES already carry `nosymm` (`config/qc_levels.json`'s `_nosymm_required_job_types`) — that part is live. The GUARD that would confirm a completed G16 log actually preserved it is not wired, because nothing reads back a completed TS-search/IRC log yet. |
| `perturb_out_of_plane`, `tripwire_record`, `detect_tripwire_aborts`, `spend_core_hours`, `derived_or_null` have no caller | **DELIBERATE (category B)** | All B0 collector wiring, NOT STARTED, same as coder6's arm2 row. `derived_or_null` specifically: the actual C-1 incident (`cost_ratios`) needed a two-reason design (missing vs non-convergent) that this generic single-reason helper doesn't provide, so `cost_ratios` calls `guards.unconverged_inputs` directly instead. `derived_or_null` is not wrong, it is just not what the one incident we had needed. |

**Merely unfinished** (see §B): item 9 in full (composite route strings · B0 collector wiring ·
`payload/PBS`'s 6h PREVENTION half — the DETECTION half was confirmed already wired by critic8) ·
whatever `proposer6` returns on items 5/7's "what is P1?" question · packaging scope for `tests/`.

---

# §A — What was built this session

All in `src/pilot_package/` unless noted. This session's job was **ADR-090 §5**: the guard-reach
round. Nine items; all landed except item 5 (correctly escalated, not wired) and item 9 (correctly
deferred).

```
B-1 (finished, was coder6's B-1)   route-truncation: parse_route_echo/route_record_from_stored_
                                    string/keyword_in_route/require_keyword_known_absent, all in
                                    criteria/g16.py. Propagated the route -> route_echoed rename to
                                    THREE consumers coder7's partial patch had NOT reached
                                    (payload/P1b.sh, payload/P5.sh, payload/qc_adapter.sh) --
                                    latent KeyErrors the suite could never have caught (P5 skips
                                    without g16 on this box). 25 new tests, tests/test_route_
                                    truncation_b1.py.
ADR-087                            bound.py::partition() -- removed the pooled convergence_rate/
                                    n_converged/convergence_denominator ENTIRELY (not renamed, not
                                    caveated) after grepping for real consumers and finding none.
B-2                                nosymm added to the 5 TS-search/IRC job_type templates in
                                    config/qc_levels.json (_nosymm_required_job_types, single
                                    source), placed at column 3 so it survives B-1's 70-column
                                    truncation. guards.require_nosymm_if_needed +
                                    NosymmRequirementUnmet, reusing g16.keyword_in_route so an
                                    incomplete route raises rather than reading as "absent".
B-5                                curvature.u55_panel gets n_convergence_artefacts_by_species +
                                    species_with_convergence_artefacts -- step (2) of its OWN
                                    stated reading order named a quantity the panel never handed
                                    the reader.
C-2 (ADR-090/092 item 1)           guards.irc_verdict actually called from criteria/p1.py::
                                    evaluate_p1. `not c2_ok` forces `undetermined` regardless of
                                    the topology verdict (same or distinct) -- the actual fix for
                                    critic8's adversarial 2-frame case. Renamed the colliding dict
                                    key irc_verdict -> irc_topology_verdict (the exact ADR-092 trap).
                                    Found and fixed a second, independent defect while wiring this:
                                    collect._g16_last_geometry_xyz's synthetic 1-frame xyz would
                                    have pinned n_points == 1 forever if reused for C-2's point
                                    count -- collect_p1 now counts real orientation blocks via
                                    g16.parse_geometries() on the raw log instead (ADR-093).
C-1 (ADR-088, item 2)              criteria/p1b.py::cost_ratios() routes through guards.
                                    unconverged_inputs, not a hand-rolled rule. Missing-data and
                                    non-convergent-input are kept as two DISTINCT reasons.
kappa integrity (ADR-091/092,      collect_p6 now calls execution_audit per anchor task and GATES
  item 3)                          `valid` on it (stronger than the other 4 collectors' report-
                                    only treatment, because kappa is the schedule's single critical
                                    path). Reproduces critic8's exact adversarial double-execution
                                    case.
THE REACH TEST (item 4)            tests/test_guard_reach.py, new file. AST Call detection, never
                                    grep/name-occurrence (ADR-092's own instrument fell to that
                                    class once). Four-then-five-bucket forced classification of
                                    every public guards.py function; extended to scan payload/*.sh's
                                    <<'PY' heredocs by AST too, since C-12's fix lives there.
C-12 (item 6)                      payload/P1.sh's QST2->single-ended fallback routed through
                                    guards.fallback_decision via the EXISTING python3 - <<'PY'
                                    bridge (no new mechanism). Real bash + real g16 PATH shim end-
                                    to-end test (tests/test_p1_c12_fallback.py) reproduces the
                                    incident itself (normal termination + 0 imaginary modes -> the
                                    fallback now fires) alongside a positive control and the
                                    legacy-still-works case.
C-10 (ADR-091, item 7, MAJOR)      guards.cost_probe_violations called from evaluate_p1, scoped to
                                    DIAGNOSIS ONLY -- see the DELIBERATELY-ABSENT row above.
item 5 zero-risk deliverable       tests/test_guards.py::test_the_actual_shipped_p1_inputs_raise +
                                    the BLOCKED_ON_DECISION bucket in test_guard_reach.py. Guard
                                    NOT wired onto any live path.
```

---

# §B — What is not finished, and why

| item | status |
|---|---|
| **item 5** (C-8, `require_ts_precondition` -> `payload/P1.sh`) | **ESCALATED to `proposer6`, not mine to decide.** Two independent C-8 violations on the current pipeline: (1) the shipped endpoint geometries are unoptimised by the pipeline's own admission ("GUESS GEOMETRY"), and (2) even optimistically, `payload/P1.sh`'s CREST step refines `reactant.xyz` ONLY (`cp crest_best.xyz reactant.xyz`) — `product.xyz` is never touched, so the two endpoints are prepared at DIFFERENT levels regardless of whether either is optimised, which C-8's "at the SAME level" clause forbids independently. Do not fix either without the ruling. |
| **item 7's deeper question** | Not really "item 7" — it turned out to be the SAME underlying question as item 5: *what is P1?* If P1 is a cost probe, C-8 doesn't gate a cost measurement and C-10 forbids the chemical verdict it currently carries. If P1 is a chemical claim, C-8 must halt it and C-10 doesn't apply to it. Both items resolve the moment that is decided and not before. Routed to `proposer6` together with item 5. |
| **item 9 — NOT STARTED** | composite route strings · B0 collector wiring · `payload/PBS`'s 6h tripwire PREVENTION half (the DETECTION half — a PBS-killed job writing `run` and never `finish` — was already confirmed wired by critic8's earlier pass; do not re-verify it, verify the PREVENTION half: `≤6h` wall REQUESTED). |
| **`tests/` packaging scope** | Confirmed (both lead and me, independently) that neither tarball contains `tests/`. This means the reach test — this round's actual defence — doesn't ship with the artefact the user runs on the cluster. Not a bug; a scope question for the lead, pending critic8's pass. |

---

# §C — Findings not (or not fully) written elsewhere

🔒 **Subsections below are numbered `H-1` … `H-6`, not `C-1` … `C-6`, on purpose.** `C-N` is
reserved for the `02_METHOD_SPEC.md` constraints (`C-1` = derived-quantity nulling, `C-2` = IRC
indeterminate-not-fail, `C-8` = TS precondition, `C-9` = coplanarity, `C-10` = cost-probe verdict
smuggling, `C-12` = fallback acceptance, `C-13` = tripwire abort). This is the **fourth** notation
collision logged on this project (after `E1/E2/E3`, `C-N` vs `B-N`, `B0/B1` vs `B-1/B-2`) — the
user hit two of the earlier ones in conversation and could not follow. **Do not reintroduce a
`C-`-prefixed subsection numbering anywhere in this document set; the prefix is not free to reuse.**

## H-1. 🔒 THE 5-MUTATION-CLASS CHECKLIST — the most reusable thing from this session

The lead pushed back hard, correctly, on an early revert experiment: reverting a file to pristine
and getting `AttributeError`/`ImportError` only proves a test **touches** new code, not that it
would catch a **subtly wrong** implementation (§0.2(a): ERROR usually means the experiment changed
the wrong thing, or in this case, changed too much). The fix that held up: mutate the file **without
changing its public API**, one change at a time, restore, repeat. Five mutation classes covered
every case I hit this session:

```
1. constant change        (a threshold, a column count, a wrap width)
2. boolean-flip            (an `is_complete` field forced True/False regardless of input)
3. early-return / short-circuit  (a RAISE replaced with a bare `return None`)
4. logic-skip               (a loop body replaced with `break` on the first iteration --
                             e.g. "skip the continuation-line join")
5. silent-leak               (a field the fix was supposed to remove re-added alongside the new ones)
```

Each mutation must produce a **FAIL**, not an ERROR — a FAIL means the test actually exercised the
logic and found it wrong; an ERROR usually means you broke something structural instead of
subtly wrong. I used this on B-1's `test_route_truncation_b1.py` (5 mutations, all FAIL, one caught
in `test_guards.py` too via cascading dependency) and it is worth running on ANY test file whose
only verification so far has been a full-revert AttributeError. It costs about ten minutes per file.

## H-2. 🔴🔴 ADR-093's shape, generalised: a reach test can pass on a DEAD input

The finding the lead made ADR-093 out of: `collect._g16_last_geometry_xyz` deliberately keeps only
the LAST orientation block of a G16 log (correct for the topology/endpoint comparison it exists
for). Reusing its frame count as C-2's `n_points` would have made `n_points` **always equal 1**,
which is permanently below `guards.IRC_MIN_POINTS = 5` — C-2 would then have been WIRED, REACHED,
and TESTED, and STILL structurally unable to ever pass. The direction is safe (everything falls to
`indeterminate`, never a false pass) but the failure mode is subtle: **the repair a future reader
reaches for is "C-2 is too strict, relax the threshold,"** which converts a fail-safe into a real
hole while the reach test stays green throughout.

**The generalised lesson, for whatever guard you wire next**: existence, correctness, reach, and now
a **fourth property — satisfiability**. When you wire a guard, build ONE positive fixture that
actually PASSES it, not only negative fixtures that correctly refuse. A guard that can only ever
say `None`/`False` is indistinguishable, by its own test suite, from a broken one. I did this
unprompted for C-1 (the genuinely-converged `cost_ratios` fixture) before the lead named it as a
rule — it's what caught the dead-input case in the first place. Do it on purpose next time, not by
instinct.

## H-3. 🔴 ADR-092's own instrument fell to the class it was hunting

The lead's first guard-reach sweep (`grep -rn "\bNAME\b" | grep -v guards.py | wc -l`) certified
`guards.irc_verdict` as `WIRED (3)`. It was not — the only match was `p1.py:283`'s dict KEY
`"irc_verdict": ir.get("verdict")`, a same-spelled string, not a call. Two rounds later, the SAME
sweep's `coplanarity` claim turned out to be wrong too, for a different reason: the two matches
outside `guards.py` were **docstring mentions** in `linalg.py`, not calls either. **Two of three
positive claims in a 16-row table were wrong, and both errors pointed the same direction — "this one
is wired" when it was not.** Neither error ever said "unwired" about something that was actually
reached. That direction (errors read as safety, never as danger) is the same one §0-h documents for
a different instrument; it is now confirmed on a second one. If you build a third reach-style check
in this codebase, assume its false positives will also read as safety, and design a way to catch that
specifically — a pure name-occurrence check cannot see the difference between a call and a mention,
full stop, no matter how carefully the regex is tuned. Use `ast.Call`, always.

## H-4. The subTest arithmetic quirk (small, but cost a round-trip)

`unittest`'s summary line (`FAILED (failures=X, errors=Y)`) counts each **failed `self.subTest()`
iteration** separately, while `Ran N tests` counts only test **methods**. A test file with three
subTest loops can legitimately report `failures=3, errors=26` while `Ran 25 tests` — this is not a
miscount, it's how the stdlib reports subTest failures. I should have flagged this myself the first
time I reported raw numbers instead of letting the lead reconcile it; recording it here so the next
person doesn't have to rediscover the reconciliation.

## H-5. The stale-backup false negative (my own mistake, recorded because coder6's §F asked for this)

Doing the revert-experiment discipline (§0.2c/§0.4), I once copied a backup of the ALREADY-FIXED
file onto itself while intending to restore the PRISTINE (pre-fix) version — a naming confusion
between two backup directories I'd made minutes apart. The result looked like a clean "revert" (no
diff shown as an error) but the subsequent test run showed all green — which I could have wrongly
read as "the revert didn't apply" or worse, "the test doesn't discriminate." I caught it by running
`diff -q` against the INTENDED pristine source before trusting the green result, per coder6's own
rule. **The lesson, restated because it bit me even while actively trying to follow it**: printing
the pristine sha256 once at the top (as instructed) is necessary but not sufficient — you also have
to verify, each time, which of your OWN backup copies you are restoring FROM, not just that a
restore happened. Keep pristine and "current fixed" backups in clearly, boringly named subdirectories
(I used `~/.sei_pristine_coder8/current_fixedN/` incrementally; a naming scheme less prone to
off-by-one confusion would be better — name by WHAT was fixed, not a counter).

## H-6. Provenance: verify what you are reading is what you think you are reading, twice this round

Beyond the build-provenance crossing (see LIVE block above), this whole session was thick with
crossed messages — the lead sent reorderings that arrived after I'd already acted on the previous
order, more than once, and the lead's own ADRs record this explicitly (ADR-090's own "process
defect" section). **The thing that actually worked, every time**: before accepting a claim about the
tree's state ("this isn't built," "this test count is wrong"), re-measure it myself, right then,
and report the fresh number rather than defending or accepting the stale one. This cost a few
minutes each time and never once produced a wrong report. It is cheaper than it looks.

---

# §D — First five minutes, successor

```
1. Read HANDOFF_TO_LEAD.md §0 and §45, then HANDOFF_CODER6.md's READ-THIS-FIRST block, then this
   file's LIVE block. Believe none of the three about CURRENT state -- only this file's LIVE block
   and a fresh measurement are current; the other two are historical.
2. python3 src/build_stamp.py check --root .    Expect ✅ (green as of this handoff).
3. python3 -m unittest discover -s tests -q     Expect 1204 OK, skipped=8, zero failures.
4. tests/test_guard_reach.py is the map of what's wired, what's deferred (with a reason), what's a
   known defect, and what's BLOCKED_ON_DECISION. Read its four dicts before touching guards.py OR
   before assuming any guard is either wired or safe to leave unwired -- do not trust prose,
   including this file, over that file; it is designed to go stale-and-loud, not stale-and-silent.
5. Do NOT wire `require_ts_precondition` onto payload/P1.sh's live path. Check whether `proposer6`
   has ruled first -- if BLOCKED_ON_DECISION still contains it, the ruling has not landed.
6. Keep revert/mutation pristine copies OUTSIDE /tmp (this box reaps it mid-session) and verify
   which backup you are restoring FROM before trusting a green result (§H-5 above).
7. If you add a NEW guards.py function or a NEW collect_* function, test_guard_reach.py's own
   forced-classification tests will fail until you put it in exactly one bucket. That failure is
   the mechanism working, not a bug to work around.
```

---

# §E — Extension: ADR-099, the endpoint two-stage build (same session, after §A-§D)

`proposer6`'s C-8 ruling landed (Q2: same-level rough+tight, thresholds only) and the lead asked
for the two-stage endpoint-optimisation scaffolding this round's escalated item 5 had been
waiting on. This closes the loop §B above described as "resolves the moment [what is P1?] is
decided" — it does not; it answers a DIFFERENT, narrower question (how do endpoints get
certified before a TS search), which is why item 5 (`require_ts_precondition` → `payload/P1.sh`)
is **still** in `test_guard_reach.py`'s `BLOCKED_ON_DECISION` bucket, unchanged. Do not read this
section as item 5 being resolved — it is not.

## E-1. What was built

```
config/qc_levels.json      job_types.endpoint_opt_rough / endpoint_opt_freq (both nosymm, both in
                            _nosymm_required_job_types). _endpoint_two_stage block: budget_h=6.0,
                            budget_core_h=384.0 (cumulative, per endpoint), rationale for same-
                            level rough recorded in _rough_level_status.
criteria/xyzgraph.py       angle_deg(a, b, c) -- new, verified against real shipped .xyz (180.0°
                            on the hand-drawn guess, matching the documented baseline).
criteria/f1_endpoint.py    new file. Pure functions for config/f1_required_observables.json's
                            emit-list: ring_bond_lengths (roles.py's `candidates`, not `selected`
                            -- collects BOTH symmetry-equivalent bonds), li_o_c_angle_deg (refuses
                            with a warning on ambiguous role match -- found, not constructed: the
                            ring-opened product genuinely has two O_carbonyl candidates),
                            n_imaginary (None, not 0, on empty input), symmetric_fingerprint
                            (explicitly labelled NOT point-group detection, wraps
                            guards.symmetric_placement_flags), stage1_exit_structural_set (all
                            three, purely geometric, no job).
payload/endpoint_prep.sh   new file. ONE PBS job runs BOTH stages internally (file-read handoff,
                            not a second resource request -- 2 jobs total across both endpoints,
                            not 3). Order: TIGHT_LEVEL/ROUGH_LEVEL (same value, no I/O) ->
                            sei_qc_detect -> C-5 solvent precheck -> C-9 perturbation (ONCE,
                            before stage 1) -> stage 1 -> budget check (stage1_budget_exhausted)
                            -> free stage1-exit structural set -> stage 2 -> budget check
                            (stage2_budget_exhausted) -> F1 observables -> converged/not_converged
                            on n_imag==0. Neither budget-exhaustion status is ever non_converged.
collect.py                 collect_endpoint_prep(store, key) -- reads terminal_status.json, stage
                            records, perturbation_provenance.json, stage1_exit_structural_set.json,
                            f1_observables.json, runs execution_audit(). Wired into cli.py's
                            write_report pilots list (see E-4).
plan.py / cli.py           Item.extra_env (new mechanism -- see E-4) and one new Item,
                            endpoint_prep_reactant, priority 71, explicit_wall_h=6.0 (P6's
                            mechanism, not size_job()'s core-h->wall inversion -- size_job()'s
                            frozen 500.0/1008.0/5.0 reference values were never touched).
README_USER.cpu.md         new row + SPEC-BLOCK updated FROM code_truth()'s computed values
                            (17063 expected / 19475 reserved), not hand-typed.
tests                      test_f1_endpoint.py, test_endpoint_prep.py (real bash + isolated
                            heredoc extraction, no real g16 needed -- the QC-engine gate blocks
                            first in this environment, same as every other payload script here).
```

## E-2. 🔴 The grid omission — caught by the lead, not by me, and how

My FIRST draft of `endpoint_opt_rough` was `opt=(loose,maxcycles=200)` with **no**
`Int(Grid=UltraFine)`. `proposer6`'s ruling said the grid is explicit in BOTH stages ("a coarser
grid is a different surface and reintroduces the basin error through a door nobody watches") — I
had it right in `endpoint_opt_freq` and simply left it off `endpoint_opt_rough`, the exact "it's
only a rough opt" omission the ruling's own rationale warns about. **The lead caught it by reading
the config file directly, not by running a test** — no test existed yet that would have caught
it; `test_endpoint_route_parity.py` (below) did not exist at the time of the mistake. I fixed it
(`maxcycles=100` also — I had `200`, ruling says `100`) the same round I received the correction.
**The lesson for whoever reads this next**: writing the same fact (a grid keyword) into two
sibling route strings by hand, one at a time, is exactly the shape of defect a per-token parity
test exists to make structurally impossible — see E-3.

## E-3. `test_endpoint_route_parity.py` — written by the LEAD, not me

🔒 **Record this so provenance is not reconstructed wrongly, the same discipline as the LIVE
block's build-provenance note above.** After catching E-2's omission, the lead wrote
`tests/test_endpoint_route_parity.py` (4 tests, ADR-101) themselves and ran the 5-mutation-class
discrimination sweep on it independently (M1 = the real historical defect, grid dropped from
rough; M2 = basis diverged; M3 = nosymm dropped; M4 = a positive control making the two routes
identical) — all four FAILED, not ERRORed, confirming the test discriminates. I later re-ran M1
myself (grid-drop) as a second, independent confirmation before reporting the round closed; my
own sha256-verified restore matched the lead's. **This file is not mine** — do not attribute it
to me in a future summary, and do not "improve" it without checking whose reasoning it encodes
first (it guards a PROPERTY — surface tokens outside `opt=(...)`/`freq` must be identical — not a
literal string, on purpose, so a future divergence in grid/basis/solvent is structurally caught
regardless of token order).

## E-4. `extra_env` — a genuinely new mechanism, and why it had no home before

Wiring `endpoint_prep_reactant` needed `SEI_ENDPOINT_ROLE=reactant` set for THIS job only.
`build_common_env()` (`cli.py`) is deliberately shared by every job — putting a per-item value
there leaks it everywhere. No per-item env mechanism existed. Added `Item.extra_env` (a dict,
default empty), threaded through `plan.py`'s `entry` dict, merged into `job_env` in `cli.py`'s
`build_spec()` after the common/QC env, before nothing overwrites it. One new field, one new
merge point, no new file.

## E-5. 🔴 The budget-number coincidence — real, but NOT structural, do not derive from it

`endpoint_prep_reactant` declares `core_hours_budget=384.0` (informational, and what
`endpoint_prep.sh`'s OWN internal cumulative stage1+stage2 check, `SEI_ENDPOINT_BUDGET_CORE_H`,
actually enforces). The SCHEDULER's physical reservation ceiling is a SEPARATE number,
`cores_per_node × explicit_wall_h(6.0)`, which the lead verified equals `384.0` EXACTLY on the
real cluster (64 requested cores × 6h). **This is an arithmetic coincidence of this cluster's
core count, not a designed relationship** — on a 128-core site (a real test fixture in this repo
produces exactly this) the two numbers separate 2× (768 vs 384). **Do not write code, a test, or
a future doc line that assumes `core_hours_budget` and `cores_per_node × wall` are the same
number by construction** — they are declared independently, coincide on THIS cluster's core
count, and will not coincide everywhere. If you add a second endpoint item (product) or change
this cluster's `cores_per_node`, re-check this by hand; nothing currently asserts the two stay
equal, and nothing should — asserting it would be encoding the coincidence as a requirement.

## E-6. 🔴 ADR-102 — the producer→plan instrumentation gap, general form, NOT built

The lead named the specific case fixed this round ("a collector whose producer is in no plan
item" — `collect_endpoint_prep` existed with nothing invoking `endpoint_prep.sh`) and I
mutation-checked that THIS item's wiring discriminates (removed the `collect_endpoint_prep` call
from `write_report`'s pilots list; `test_plan_report_e2e.py`'s pilots-id-list assertion FAILed,
not ERRORed; restored byte-identical, sha256-verified). **That closes the gap for THIS item only.**
It does **not** generalise: a FUTURE payload script could be added with a `collect_*` function and
no `Item(...)` entry (or the reverse — a plan `Item` with no matching `collect_*` call in
`write_report`), and nothing in the test suite would object, the same way nothing objected to
`endpoint_prep.sh` for however long it sat unreached. `tests/test_producer_consumer.py` checks
that every collected FIELD is read somewhere and every payload ARTIFACT is read by ITS OWN
collector — it does not check that every `collect_*` function is CALLED from `write_report`, or
that every `Item` in `plan.py` has a matching `collect_*` call. **This is registered here as
ADR-102, an open instrumentation gap, on the lead's explicit instruction not to build it now** —
whoever picks it up next should write a structural test (AST-based, following `test_guard_reach.py`'s
own convention, not name-occurrence) enumerating `plan.py`'s `Item.key`s against `write_report`'s
`collect_mod.collect_*` calls, in both directions.

---

*coder8, 2026-08-19. Tree clean at `source_digest 12c793d774e87d08`, 1232 tests OK (skipped=8),
`[stamp] ✅`. Built by me, verified by the lead independently against the same tree. ADR-090 §5
round closed on items 1-4, 6-8 (item 5 remains ESCALATED, item 9 remains NOT STARTED, both
unchanged by this extension). ADR-099's endpoint two-stage scaffolding built and landed this same
session: `endpoint_prep_reactant` is reachable from `./run.sh`, deliverable to the user. ADR-101's
route-parity test is the lead's, not mine. ADR-102 (producer→plan instrumentation, general form)
is open, flagged, and deliberately not built.*
