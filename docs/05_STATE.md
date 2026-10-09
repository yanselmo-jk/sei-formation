# Project State

**Last updated**: 2026-08-25 (end of day). 🟢🟢 **ADR-118: U-56a IS CLOSED** — Candidate B (StepSize
f=0.20 from-scratch reverse IRC) walked 70 points to arc 4.78 with zero corrector warnings; its B+
opts agreed (4.197e-4 eV) and matched the certified reactant (1.3324e-4 Å / 2.673e-4 eV, §39.132
backfill); condition 7's reverse branch closed (§39.133, critic17-confirmed cold) and all eight
§39.32(g) conditions now read MET (per-condition provenance table in ADR-118). EulerPC/DVV tiers
MOOT (§39.131(4)), never run. Review batches 30-42, one continuous day.

**Current phase**: Phase 1 → **S3 WAVE-1 BUNDLE BUILT, VERIFIED, TARRED — awaiting user scp+deploy+qsub**
(`pilot_tests/wave1_2026-08-25.tar.gz`: the 3 staged pieces + the FRESH package tarball, which MUST be
deployed first — all three qsubs carry a fingerprint guard, exit 9 on a stale deployment). Wave 1 = 2
pre-registered attempts (T21-se stage-1 circuit-breaker `SEI_U56_STOP_AFTER=u56_scan`, cap 1,428
core-h, cap-without-finishing = stop-and-rescope; R-B redo full chain 303-355 core-h) + stage 0 MTD
comparator in parallel (NOT an attempt — denominator stays clean). Package rebuilt
(`b94510460851012e`/`a550fa5105cd7070`, 118 files), suite **1817/1817 fully green** (R-10 FIXED at the
renderer — bounded by construction, verified flat at 200 synthetic roster entries). Session additions:
6th outcome class `staged` (§39.138-140 — deliberate circuit-breaker stop: no retry, not success, not
in U-56b denominators, severity position EARLY per §39.140; the 44차 "inverted implementation" finding
was AMENDED by critic17's own 46차 correction — a mid-flight measurement of a moving tree, the
delivered code never carried the inversion; the surviving real finding is that the originally-mandated
tests couldn't discriminate the ruling from its inverse, fixed at test_outcome_retry.py:314-315);
`recorrect=never` wired into ALL FOUR IRC templates (incl. rcfc); sealed T1-T4 targets (§39.137,
sha256 69ce2848..., blindness verified); deployed-package fingerprint guards in all generated qsubs;
freeze-verify convention adopted (tree freezes during a critic verification pass — standing rule).
Review batches 43-46 (critic17): final verdict OK, clear to tar (46차 includes the record amendment
above). Still open, non-gating: point-group
emit wiring; qst2 core-h extraction discrepancy; `common.sh` opt-in fingerprint mechanism (own slot
next code round). 🟢 ADR-115: R-A's wavefunction-instability
hypothesis FALSIFIED, residual gap closed by probe5 (§1e). Integrator hypothesis: positive-but-
incomplete support from stage4 (§39.125), inconclusive from candidate A (§39.126, artifact not signal).
🟢 ADR-116:
Track B items 5/6 RULED (accept `U56_RA_scan`, reject `U56_RA_qst2`, reject `U56_RB_scan`); item 7
still open, never gated on this diagnostic. 🔴🔴 **U-56a is OPEN** — an earlier same-day claim that it
was closed is RETRACTED (ADR-116, caught by critic15): condition 1 of eight is met, **condition 7 is
not**, and **stage 4 DOES gate it**. 🔴 ADR-117: the kill was a SUBMISSION failure; §R39.79's resubmit
recipe was NO-GO and now carries four corrections — **do not submit any earlier form of it**, see §1e. Live package `a7b668127d052e33` (one comment-only diff on top, batched not rebuilt — §1d).
🔴 **P1 is permanently OUT by user ruling** (ADR-112, mislabeled saddle) — confirmed still true with
`endpoint_prep_product` back in the plan (P1.sh structurally never reads endpoint output, §2).
**Read `deck_verification.json` before quoting any `r`/unit cost** (ADR-108 reading rule) — note that
no `deck_verification.json` exists for the hand-submitted diagnostic decks, by design (§1e).
🟢 **R-9 RULED AND PRICED, 2026-08-22** (§§39.124 / R39.81, by `proposer12` + `engineer13`, both
since stopped): the reverse-arm requirement now has a protocol, a program-evaluable acceptance
criterion, a sequencing rule and a cost — see §1f. **U-56a remains OPEN**; nothing here closes it.
Cost is NOT the binding constraint (worst realistic path ~194 core-h against ~8,240 core-h of
remaining margin). 🔴 **A spec-vs-code gap in condition 7 itself was found** (§39.124(1)(c)): the
reverse-endpoint-matches-certified-reactant check the ruled text requires does not exist in
`guards.py` — a real `src/` change is now pending, which is the trigger §4 RESUME (6) was waiting for.
🔴 **Ruling the R-9 triage surfaced three MORE defects** (§1f, lead, by reading the tool candidate A
depends on): proposer12's `maxpoints=30` ruling has **no implementation path** — the restart route
never writes `maxpoints`, relying on the same silent checkpoint inheritance the project already
refuses to trust for `recorrect=never`; and the tool's `total_cores=1` default would reproduce
ADR-117 a **third** time — **framing corrected by critic16: not an ADR-117 mismatch but an ADR-114
48 h WALL-CAP breach** (46-87 h at 1 core vs 0.7-1.4 h at the 64 priced). 🔴🔴🔴 **critic16's 26차
배치 verdict is BLOCK**: §39.124(1)(b)'s flatness finding is FALSIFIED — it measured the B+ *start*
geometries and reported them as optimised endpoints (real separation **0.0003 Å**, not 0.17 Å), which
voids candidate D(i)'s 30.0-49.9 core-h rationale and the docstring/test rationale coder15 already
shipped. 🔴🔴 **`guards.reactant_match()` can never return `True` — as implemented U-56a could
NEVER close** (§2); proposer12 has since ruled the unblocking tolerance (0.05 Å, `last` only) and
🟢🟢 **R-9 is CLOSED** (critic16 final verdict): ruling, pricing and code all
verified, `reactant_match(last)` returns `True` for the first time. 🔴 **This closes the reverse-arm
WORK ITEM, not U-56a** — and the clause has **no live producer**, so it is skipped on every production
path that exists today. Three carry-overs outside R-9 (§1f). 🟢 **R-9 has otherwise CONVERGED**: D(i) withdrawn
(its 30-49.9 core-h cancelled with the finding it was priced against), candidates A/B sequenced and
priced at ~181 core-h worst case (~2.2% of margin), acceptance criterion split across both condition-7
branches. Nothing is scheduled, so nothing is burning. **Stage 3/4 remain the critical path.**

<!-- 🔴 Keep the Last updated / Current phase lines within the document's first 12 lines —
     src/session_digest/docparse.py:99 scans only text.splitlines()[:12]. Breaking this fails
     make_package.sh's build gate. Do not duplicate these two lines elsewhere in the file. -->

---

## COMPACTION NOTE (2026-08-20)

This document previously ran ~4,100 lines as a chronological session log, recording every
correction-of-a-correction in full narrative form (e.g. a budget figure or a design ruling
changing three times in one afternoon, each swing described at length). That log served its
purpose live but is not useful as a reference. **It has been rewritten below to state only the
CURRENT, FINAL position of each item**, with terse provenance notes where the *reason* a position
changed is itself worth keeping (a real scientific finding, not bookkeeping churn). The full
blow-by-blow history — every ADR, every ruling, every self-correction — remains intact and
unedited in `01_DECISION_LOG.md`, `02_METHOD_SPEC.md`, `03_COMPUTE_PLAN.md`, and `04_REVIEW_LOG.md`.
Nothing was deleted from those documents; only this state-tracking file was condensed.

---

## 1. THE NEXT ROUND — designed, priced, not yet submitted

```
cut U56-2 (3× 11-atom TS attempts + endpoint certs)   ceiling ~7,810   (rcfc-dependent, see below;
                                                                        6,530 base + 1,280 R-A
                                                                        Option-A calibration IRC —
                                                                        the earlier ~6,145 here was
                                                                        T21-se's number copy-pasted
                                                                        in, engineer8 caught it §R39.40)
P1b (re-run)                                           5,328
P5  (re-run)                                            3,128
sp_ladder (3 rungs, n=1/2/3; n=4 later — released:false, gated, see §"What's in flight")   307
stage 0 (12 seeds × 100 ps MTD comparator)                33
P-U2′ (ν measurement, unconditional)                       1
rcfc route smoke (Hessian-reuse verification)             60
──────────────────────────────────────────────────────────
NOTE: these 7 lines don't sum exactly to the total below (engineer8 traced the total to
03_COMPUTE_PLAN.md §R39.33 directly, not to this table — a small untabulated remainder exists,
non-blocking, safe direction). U56-2 AND sp_ladder are both behind `released:false` gates in
config/b0_reactions.json — the code never flips these, only lead/user can. If both stay false,
neither actually joins the submitted batch despite being listed here.
TOTAL                                                ~17,200 / 21,000 guard   (~18% margin)
```

🔴 **T21-se's ceiling figures below (7,169, and the 931-core-h B+ estimate at §"What's in flight")
are RETRACTED by engineer8** — both were built on an atom-count cube law (S₂₁, §R24.1) that
proposer7's §39.72 P5 read showed is the wrong shape: the real cost driver is cation+open-shell
chemistry with a genuine interaction term (measured ×15.2 vs ×6.4 predicted from independent
factors), not atom count. **T21-se's true cost is UNKNOWN, and unknown in the direction the cube
law underestimated, not just uncertain in magnitude** — same shape as the earlier IRC-anchor
problem one size class up. No replacement number exists yet (proposer7's 4 data points are all
10–11 atoms, none is R-C's actual 21-atom cation-radical reactant — substituting the ×15.2 factor
directly would repeat the same mistake in the other direction). **Do not use any current T21-se
ceiling for a wave-1 go/no-go until a real 21-atom cation+open-shell attempt produces measured
cost.** 🟢 **This round is UNAFFECTED**: cut U56-2 (~7,810) is priced entirely at 11 atoms — none
of it uses S₂₁. Nothing here holds up submission.
**`rcfc` is a PRECONDITION for cut U56-2's own ~7,810 ceiling above** (unaffected by the T21-se
retraction — this item is 11-atom only). The 60 core-h smoke in this round exists to verify the
`rcfc` route works. T21-se/wave-1 sizing is a separate, later question and now has no valid ceiling
at all pending the real measurement described above.

**The MTD pilot is deliberately NOT in this round.** Stage 0 (the unbiased comparator) gates it —
if stage 0 finds all four rediscovery targets on its own, the pilot does not run for this reaction
class at all (F13, §39.40(h)). The pilot's own cost, if triggered, is now cheap (~33–78 core-h at
12×100ps) — see `03_COMPUTE_PLAN.md` §R39 series for the full pricing chain.

**Known forward collision, not yet needing a decision**: MTD pilot + a full 3-attempt S3 wave 1
cannot share a round (ceilings overflow). Choice when it matters: wave 1 at 2 attempts sharing a
round with the pilot, or 3 attempts with the pilot deferred a round. Not actionable until wave 1 is
actually being built (needs U56-2 released + this round's reply + `deck_verification.json`).

### What's in flight right now
`coder11` (opus) has DELIVERED: G-SCAN-2 v3 (discontinuity gate), Ω emission + a threshold-free
spectator-funding test (§3), C-2.1/C-2.2/condition-7 (IRC completion gate, branches a/b coded, B+
terminal-opt piece itself not yet built — current behaviour correctly refuses truncated paths
rather than passing them), CHEMICAL/BUDGET/UNKNOWN/MIXED indeterminate classification + active-cap
recording, and the GFN2 bidirectional scan producer (built and verified by execution — no
constrained-scan machinery existed in this codebase before). Suite at 1444 tests, 2 freeze-signal
failures only.

🟢 **The GFN2 producer's first real run caught a live defect in G-SCAN-2 itself, before it shipped
— caught by running the thing, not by review.** Clause (ii) (barrier agreement) computed each
profile's barrier from ITS OWN first frame — correct for the forward profile (reactant) but wrong
for the reverse one (whose first frame is the PRODUCT). This made clause (ii) measure reaction
energy (ΔG_rxn) disguised as path-dependence, firing harder on more exothermic reactions — and it
fired a FALSE BLOCK on R-A, which proposer7 had independently measured as clean (no hysteresis).
False block is the costly direction by the gate's own design (loses a whole reaction, not just
core-h). Fix (one line, confirmed correct by proposer7): measure BOTH barriers from the REACTANT
end — forward's first frame AND reverse's LAST frame — reproducing proposer7's own §39.48(a) n=1
value to grid resolution. **proposer7 separately confirmed its own R-C validation table was NOT
affected** (already used the reactant end correctly, only the prose was ambiguous) — the fix was
NOT one-signed either: it had been false-blocking R-A AND eating R-C's margin from 10.7× down to
3.4× ("at least it was conservative" was never true). Fixed and wired.

🔴🔴 **A second, more uncomfortable finding landed the same pass: WITH THE MECHANISM COORDINATE
DECLARED CORRECTLY, THE SPECTATOR TEST NO LONGER CATCHES P1.** proposer7 scanned R-B (never
scanned before, exactly the risk coder11 had flagged) and found Li migrates onto the breaking
oxygen in ALL THREE reactions (R-A, R-B, R-C), not just R-C as previously assumed — the earlier
11-vs-21-atom asymmetry had been inferred from the hysteresis result, which answers a different
question. All three reactions now correctly declare the coordinate — and with it declared, P1's Li
motion is no longer classified as spectator motion, so the spectator test PASSES P1. Recorded as a
test, not a comment, deliberately, so a future reader can't miss it.
**What actually catches P1 now: a "bracket check"** — geometry only, no mode, no Ω, no threshold.
🟢 **RESOLVED (§39.63→§39.65→§39.66, proposer7): the earlier "R-A only, R-B/R-C need a certified
product" limit is SUPERSEDED.** Live ruling, three parts:
1. 🟢 **LANDED — Direction-aware one-sided check, ALL THREE ARMS, TODAY, certified-reactant-only**
   (§39.66, supersedes §39.65's breaking-only version): BREAK coordinate refuses if the saddle
   distance is SHORTER than the certified reactant's; FORM coordinate refuses if LONGER. Verified
   on P1 with certified-reactant numbers only, refused — Li–O2 (the mechanism/form coordinate) at
   3.980 Å at the saddle vs reactant 2.489 (product 1.803), 1.491 Å past the reactant, exactly the
   side a reactant-only bound can catch; no product/GFN2/calibration needed, coverage gap closed. A
   third independent route to the P1 verdict alongside mode character and the break-coordinate
   bracket (O2–C3: 3.184 Å outside [1.405, 2.503] — but this breaking-bond half ALONE does not
   catch P1, since a reactant-only bound can't see an overshoot past the product; credit belongs to
   the form coordinate specifically, pinned as `test_the_breaking_bond_half_alone_does_NOT_catch_p1`
   so if it ever goes green the two routes have been conflated). Direction is DERIVED from the
   GFN2 forward trajectory the pre-stage already produces (`derive_direction`), verified against
   the real log against proposer7's measured signs — never declared. Non-monotonic coordinates get
   `applicable: false, non_monotonic`, counted, never silently dropped.
2. **Two-sided check — R-A only** (the one arm with a certified product). Unchanged.
3. **Deferred, product side for R-B/R-C**: bracket against a GFN2-scan product end, calibrated
   against R-A's measured GFN2-vs-DFT product offset (per coordinate KIND, never pooled; applied
   to R-B only if its GFN2 and IRC products agree by molecular graph — else `awaiting_calibration`
   indefinitely, by design not failure). coder11's ALREADY-CORRECT hard prohibition ("do not
   substitute a raw GFN2 product distance in the meantime") stays exactly as written — it is
   proposer7's correction, implemented, not a bug: coder11's original pre-correction CLAIM was
   that a raw-GFN2 bracket is merely "weaker but safe," which proposer7 showed can be backwards
   (false-blocks if GFN2's product distance is shorter than DFT's), so the prohibition is the
   conservative state and must not be lifted before the measured offset lands (lead sent then
   RETRACTED a same-day message that inverted this — corrected within the same round, coder11
   never acted on the bad version). **Not blocking**: part 1 already covers all three arms today;
   part 3 is an improvement, cuttable if the round is squeezed. Part 1 is NOT cuttable.

🟢 **Infrastructure bug found while wiring**: `test_guard_reach.py`'s heredoc detector matched only
the literal `<<'PY'` delimiter — since a shell script can't nest two heredocs sharing one
delimiter, every renamed block added this session (`PYIRC`/`PYCAPS`/`PYSPEC`/`PYBRACKET`) was
invisible to the unreached-code guard. Fixed at the root (`<<'PY[A-Z0-9_]*'`) — same "a guard
doesn't cover its own scope" shape recurring.

**Landed since**: `rcfc` switch made safe — real gap was `chk_handoff_*.json`'s `copied` flag being
recorded but never read (a failed Hessian handoff would silently run G16 `readfc` on the wrong
checkpoint); fixed to refuse that IRC direction with `cause_class: "unknown"`, no silent fallback
to `calcfc`. GFN2 pre-stage wired end-to-end in the payload (real xtb, both directions, verdict
before any DFT spend), suite green. Direction-aware bracket check (§39.66) implemented through the
coverage answer; coder11's part-3 prohibition confirmed correct as written, kept in place (see §3
above).

🔴 **coder11 self-retracted an earlier "clean R-A PASS" report — it was not a result.** That run used
a hand-picked scan range (1.45–2.65 Å); with the range the shipped code actually computes (from the
reactant's own d(break)), the same code FIRES on R-A (Δ 0.45 eV). Root cause: the pre-stage's first
frame is still descending when the scan starts at the reactant's own geometry (0.383 eV drop
between points 1–2), and since §39.64 references both gate clauses to the reactant end, an
unsettled first frame corrupts both barriers at once (forward barrier misread 0.019 eV vs 0.471).
Two obvious repairs are both traps: a free GFN2 re-optimization of the reactant leaves the
ring-closed basin entirely (same class as the kicked-seed problem, ADR-067); a constrained
optimization keeps the basin but degenerates the reverse profile (Δ 73 eV). **Not a test-fixture
artifact**: production's reactant is DFT-optimized, not a GFN2 minimum either, so the same
first-frame lag applies there too. Shipped: pre-stage runs with NO invented pre-relaxation (the only
protocol adding no unratified step); verdict record carries `_protocol_status` stating the verdict
must not be read as a chemical result until the protocol is ruled; the gate still governs the DFT
chain, so **R-A's single-ended arm does not proceed today** — the safe direction while open, though
possibly a false block if proposer7's original n=1 PASS is the true answer. Three concrete questions
routed to proposer7: which geometry the scan starts from, what range, whether the first frame needs
its own convergence criterion. `gscan2_decision` moved from deferred to `EXPECTED_REACHED` (forced
by the reach test); cost recorded with work/charged kept apart per ADR-110.

🟢 **RULED (§39.68, proposer7)** — three parts, none a tuned constant:
1. Starting geometry: the C-8-certified (DFT) reactant, then a **CONSTRAINED** GFN2 relaxation
   holding d_break at the certified value. NEVER a free relaxation — a free GFN2 `--opt` of the
   reduced radical leaves the ring-closed basin entirely (same class as the kicked-seed problem,
   §39.42(a)/ADR-067). The constraint's whole job is preserving the basin.
2. Range: +1.2 Å (§39.42(b) already ruled this magnitude — that part was correct), but **anchored
   on the PRE-RELAXED d**, not the raw certified d. coder11's implementation used +1.1 Å anchored
   on the raw distance — the anchor point was proposer7's own omission, uncaught until now, and
   after step 1 the two differ.
3. Frame 0 gets its own criterion: (i) its constrained optimization must report CONVERGED, read
   from xtb's own output, never inferred; (ii) the profile must not DESCEND from frame 0 to frame
   1. **If either fails: verdict is `indeterminate`, NEVER fire** — a gate that blocks because its
   own reference frame was unfinished is reporting on itself, not the reaction. New `cause_class:
   "PROTOCOL"` (§4/§240 above) for exactly this.
   Validation: proposer7 re-audited their own original §39.48(a) R-A measurement under this lens
   and found it was RIGHT FOR A REASON THEY HADN'T VERIFIED — frame 0 happened to converge by luck
   (absorbed the full 0.453 eV relaxation, settled to 0.0003 eV, profile then rises monotonically).
   The ruling retroactively explains why that number worked, not just fixes coder11's finding.
   Explicitly NOT decided by this: coder11's 73 eV constrained-protocol result — flagged as likely
   a broken run/parse, not evidence against the selected protocol; to be diagnosed separately.

🟢 **LANDED.** All three parts implemented; suite green (Ran 1479, failures 2 freeze-signal only).
Diagnosis of the 73 eV, as proposer7 asked: **it was a broken run, and coder11's own code rendered
a verdict off it anyway** — `forward_rc`/`reverse_rc` (xtb's exit codes) were recorded but never
read, so a non-zero exit (the scan never finished) still produced a `fired` verdict off whatever
partial `xtbscan.log` was on disk. Same "measured but unread" shape as the rcfc `copied` flag and
the `cores_observed` gap (R-3) — this time in code coder11 wrote today. Fixed: non-zero exit ⟹ no
verdict, `cause_class: protocol`, no DFT ordered. **The constrained protocol (part 1) is NOT
eliminated** — its only disqualifying evidence was this number, and the number was never a
chemistry result. A second self-found bug landed in the same pass: the span was computed as
`n_points × step` instead of `(n_points − 1) × step`, silently registering a different span than
§39.42(b) ruled — fixed. Payload now distinguishes three outcomes, all three tested: passed → DFT
ordered; fired → not ordered; no verdict → not ordered either (an unrenderable verdict is not a
permission).
🔴 **rc=128 was mis-attributed, then correctly diagnosed and ruled — record the final state, not
the first guess.** coder11 first called it "environment-specific" (a comparison run that used a
slightly different starting distance, 1.3997 vs the payload's 1.4009, silently did the work in that
conclusion). Re-checked by actually reading xtb's fatal-error stack: **`scf: Self consistent charge
iterator did not converge`** — a normal outcome for a stretched open-shell radical hitting a
geometry where the SCF won't converge, not a broken invocation. `gfn2_scan.parse_failure()` now
records the cause from the INNERMOST stack frame (not the outermost "geometry optimization failed",
which would send a reader to the optimiser instead of the electronic structure).

🟢 **RULED (§39.69, proposer7): fifth cause class, `engine`.** Defined by prescription, boundary
stated so it doesn't grow into meaning nothing: **`engine`** = the calculation could not be
COMPLETED for numerical reasons internal to the electronic-structure method, AT A GEOMETRY THE
PROTOCOL LEGITIMATELY REQUESTED. Prescription: change how the electronic structure is set up or
converged (SCF settings, initial guess, guess propagation between frames, level) — not "fix the
caps" (BUDGET), not "fix the method" (CHEMICAL), not "fix the procedure" (PROTOCOL — the procedure
ran exactly as ruled; folding this in would poison PROTOCOL's own "our rules are wrong" meaning).
IN: SCF non-convergence, basis linear dependence, integration-grid failures. OUT: out-of-memory
(BUDGET, we chose the memory), a malformed deck (PROTOCOL, we built it), a geometry the protocol
should never have requested (PROTOCOL) — that last clause is what makes the boundary decidable.

🔴 **The 186-frame finding: coder11's concern ("will recur at production scale, ordinary outcome
for a stretched radical") does NOT hold as stated.** proposer7 checked every GFN2 scan run to date
— R-A/R-B/R-C(fwd/rev/fine)/Li(EC)₃, 186 frames total at 11/21/31 atoms, ZERO SCF warnings, all
normal termination, including R-A over the SAME coordinate range that failed for coder11. **⟹ the
failure is PATH-SENSITIVE, not a property of the surface or system size** — consistent with a
0.0012 Å difference in starting distance moving where the trajectory landed. This sharpens the
prescription rather than weakening the class: check whether each constrained scan step inherits the
previous frame's wavefunction or restarts the SCF from scratch — a scan restarting at every point is
far more likely to strand one. Honest limit stated by proposer7: 186 frames from one operator, one
set of starting structures — bounds the rate loosely (95% upper ≈1.6%/frame), refutes "ordinary",
does NOT establish "rare," and says nothing about DFT (a different, harder SCF problem).

🟢 **Partial profiles: retained, never discarded** (ADR-027's never-prune-the-completeness-datum
principle, plus §39.51(a)'s success-conditioned-denominator concern — if aborted scans vanish, the
record of "where scans succeed" is conditioned on having succeeded). Record the partial profile, the
frame index it stopped at, the constrained value there, and the innermost cause.

🔴 **Guess-propagation hypothesis TESTED AND FALSIFIED** (coder11, by execution, not review): copying
the pre-relax's `xtbrestart` into the scan dir made no difference (rc 0 either way, 12 frames);
§39.68's protocol standalone → rc 0; the payload's own computed anchor (1.401820, not typed)
standalone → rc 0; `XTBPATH` checked and valid. **The abort does not reproduce standalone, 3/3,
including with the payload's exact anchor — but it reproduces inside the payload.** ⟹ it is the
payload's runtime environment doing something to xtb, not the inputs, protocol, or a missing guess.
Both coder11's original "ordinary outcome" framing AND the guess-propagation fallback are now
refuted; honest state is an UNDIAGNOSED environment-dependent abort. Not blocking, not silent — the
run reports `engine`, renders no verdict, orders no DFT, cause string names the innermost frame,
which is the correct behaviour for an undiagnosed failure. Candidate for whoever picks it up: the
process environment the job passes down (`SEI_TOTAL_CORES`, mock-`g16` PATH, solvent/endpoint
injection vars) — `common.sh`/`qc_adapter.sh` checked for OMP/MKL/stack exports, none found, so not
the obvious one. **R-A's arm is unblocked as far as the protocol goes**; whether it actually
proceeds now depends on this undiagnosed environment issue, not on any remaining ambiguity about
what §39.68 requires.
🟢 **Worth recording next to the retraction** (coder11's own framing, endorsed): proposer7 audited
its own §39.48(a) R-A row under this same lens and found frame 0 happened to converge by luck too
— both proposer7 and coder11 shipped a correct number for an unchecked reason, on the same
coordinate, within the same day. Not just a fix — a matched pair of self-caught errors.

🟢 **§39.70 LANDED — all three parts implemented, suite green (Ran 1500, failures 2 freeze-signal
only).** (1) Comparator replaced: identical covalent graphs (`xyzgraph.layer_c_bonds`, cations
already excluded) + energies within the optimizer's own convergence tolerance — the tolerance is
NOT defaulted inside the function, must come from the run's own record or the verdict is `None`
with the reason stated (a default there would be exactly the imported constant the ruling removed).
Verified: a test moving ONLY the cation 0.35 Å still returns agreement, since the covalent graph is
untouched — the exact case the old comparator called "threshold sensitive, no verdict" on. (2)
Arc-length midpoint verified on the real P1 IRC: 30 points, arc 0.076→7.825, midpoint is INDEX 14,
not the "20th of 30" an index reading gives — the arc is genuinely non-uniform in index on real
data, which is the rule's whole justification. Pinned against real spacing (fixture with
provenance), not a synthetic ramp. proposer7's not-the-earliest-point reasoning is in the code
comment and pinned by its own test. (3) Level DFT recorded; engineer8's bundling advice does NOT
apply (was conditional on GFN2, not built).
🟢 **§39.71's energy tolerance LANDED**: `guards.BPLUS_ENERGY_TOLERANCE_EV = 1.0e-3`, derivation
AND both measured brackets kept beside the constant (max force × max displacement × 3N ≈ 1.4e-3 eV;
same-basin brackets 5e-4 eV (11-atom, 6 seeds) / 5e-5 eV (21-atom, 5 seeds); different-basin (a
coordination isomer, IDENTICAL covalent graph) 0.686 eV — constant sits between them, 4 tests pin
it against the data not the argument). 🔴 **Honestly NOT constant-free**, and the comment says so
outright: §39.70's "optimizer's own convergence criterion" wording presumed an engine that
converges on energy, and G16 doesn't (no energy row in its convergence table) — every input is
still a number G16 itself prints, but flatness (ignoring 3N's size-dependence) was CHOSEN, not
implied, and a future reader shouldn't have to rediscover that gap. The different-basin bracket is
why dropping clause (ii) (coder11's earlier suggestion) was refused: that pair has an identical
covalent graph and would have read as agreement under clause (i) alone — a real false-connection
risk, not a hypothetical. `g16.opt_energy_resolution_hartree` (this morning's now-rejected option
(a)) deleted rather than left lying around, comment names why and where the tolerance comes from
instead.
🟢 **LANDED — B+'s terminal optimizations are wired. Condition 7 branch (b) is now executable
end to end.** Start points: the LAST path point + the ARC-LENGTH MIDPOINT from the IRC's own `NET
REACTION COORDINATE` (never by index, never the earliest point). Level: the TS chain's own DFT
level via the existing `endpoint_opt_rough` route (loose is correct — need the basin, not a
precise geometry — and it already carries the UltraFine grid keeping this on the TS chain's
surface). Verdict feeds `bplus_<dir>.json` → C-2's `bplus.agreement` → condition 7 branch (b). The
three non-obvious constraints are written into the PAYLOAD itself, not just implemented silently —
each is something a later reader would otherwise "improve": not the earliest point (risks a
terminal opt rolling back over the saddle into the wrong basin, a spurious disagreement); not GFN2
even though nearly free (GFN2 merges exactly the Li-coordination basins B+ exists to distinguish —
false agreement is the one error B+ is for); no fallback (unavailable start points give no verdict,
"an unrun comparison is not an agreement"). `parse_irc_path_frames` was still in the deferred
bucket — the reach test caught it unprompted the moment the payload called it, moved to
`EXPECTED_REACHED` along with both B+ helpers, exactly the mechanism working as designed.
🟡 **Coverage limit stated plainly (in the test docstring, not just here)**: source-level checks
only. The only real IRC logs this project ever had are gone from the returned tree (§1a finding
6), so the full path — real IRC → two start geometries → two optimizations → verdict — has never
run on real data. What's pinned are the three properties that would be wrong QUIETLY (level, start
points, no-fallback), not an end-to-end real-data confirmation.

🟢 **RULED (§39.70/§39.71, proposer7) — all three questions, the first by DISSOLVING the bind
rather than picking a side.**
1. **Comparator CHANGED, not chosen between.** coder11's `None`-never-`True` bind was real:
   conservative leaves B+ undetermined on exactly the Li-rearrangement cases R-A/R-C exist for;
   permissive establishes a connection on a flippable verdict. Diagnosis: §39.48(b) recurring — a
   structural test can't separate a soft-coordinate displacement from a reaction-relevant one, and
   the Layer-I Li-contact cutoff (`config/graph_layers.json`, `[PLACEHOLDER-ESTIMATE]`) is that same
   soft coordinate promoted to a decision. **New comparator: identical covalent graphs (cation
   contacts excluded) + energies agreeing within the optimizer's own convergence criterion.** Nothing
   imported — a graph isomorphism and a number the program already converged to. The Li cutoff leaves
   the decision path, becomes a reported covariate instead. coder11's `None`-never-`True` rule
   survives for genuine ambiguity (graphs agree, energies don't, or vice versa) — it now fires on a
   much smaller set. His reasoning was right; the input to it was wrong.
2. **IRC points: last point + MIDPOINT BY REACTION COORDINATE** (arc length, Gaussian's own `NET
   REACTION COORDINATE` per point), NOT by index — well-defined at any point count, including the
   short IRCs C-2.2 makes common; not a fraction-shaped constant in disguise. Explicitly NOT the
   earliest point (would maximize sensitivity but risks a terminal opt starting too near the saddle
   rolling back over it into the other basin, producing a spurious disagreement) — that reasoning
   goes in the code comment so nobody "improves" it to point 1 later.
3. **Level: DFT, same as the TS chain — GFN2 ruled scientifically INADEQUATE, not just less
   accurate.** The narrower framing (confirming a basin, not measuring a barrier) sharpened the
   objection rather than weakening it: basin structure is exactly what GFN2 is documented to get
   wrong for Li-coordinated complexes (§39.38(d)/U-55 — near-degenerate coordination isomers
   separated by less than any cheap surface's error). The failure has a direction: GFN2 merging two
   DFT basins → false agreement → establishes a connection that isn't there (the exact failure B+
   exists to prevent) — not hypothetical, §39.42(a) measured 5/6 kick seeds landing in one GFN2 basin
   at 21 atoms; GFN2 splitting a real basin only produces a false (safe) disagreement. Changing the
   comparator does NOT fix this — which minimum the optimizer walks into is a property of the
   surface, not the comparator. engineer8's ~+12% estimate stands (DFT confirmed).
🟡 **Offered to engineer8, not recommended, not yet decided**: an optional GFN2 pre-filter (GFN2
pair first; different basins → skip DFT, return `None` free; same basin → still pay DFT since GFN2
agreement is untrustworthy). Saves only on the disagreement branch, which returns indeterminate
either way; disagreement rate unmeasured so no expected saving quotable yet; adds a stage and a new
`engine`-class failure mode. proposer7's own framing: "if it does not clear a wide margin, drop it."

**engineer8's numbers, logged §R39.38 (03_COMPUTE_PLAN.md)**: DFT B+ opts (confirmed base design) —
T11-se 97 core-h/attempt STANDS. 🔴 **T21-se 931 core-h/attempt RETRACTED by engineer8** (§R39.41)
— it was derived via the same atom-count cube law (S₂₁) proposer7's §39.72 showed is the wrong
shape (see §1's retraction note); T21-se's true B+ cost is unknown until a real 21-atom
cation+open-shell measurement exists. Not currently blocking anything (B+ terminal opts aren't
wired yet regardless). GFN2 proxy priced too for reference despite being ruled inadequate as the
base design (~0.008/~0.13 core-h pessimistic-widened at T11-se/T21-se, T21-se side now equally
suspect) — the T11-se-side conclusion (B+ at GFN2 would be negligible) still stands since T11-se's
own number is unaffected. Two engineering notes, not yet acted on: (1) the guard ceiling currently
folds the
opts into IRC's 1,536 core-h/direction cap (480 IRC + 465 opts = 945 under it) — this already fits
the confirmed DFT design, so no action needed unless the pre-filter above ever gets built; (2)
ADR-110-shaped risk flagged directly to coder11: if the 4 opts go out as separate tasks at the
default whole-node convention, the `min_wall_h=0.5h` floor would charge a 128 core-h ceiling for
~0.03–~930 core-h of real work depending on level — bundle into one job, declare `cores_per_task`
explicitly (1–4, not `None`/64). Free fix, apply when wiring.

🔴 **STALE AS OF 2026-08-22 — HISTORICAL, DO NOT READ AS LIVE STATUS.** The paragraph below
describes the team as it stood ~2026-08-20: every agent it names (`coder11`, `engineer8`,
`proposer7`, `critic10`) is on §4's **retired/burned, do not reuse** list, and the work it queues
has since landed or been superseded (§39.70/§39.71 shipped; Track A was closed by `coder14`).
**This block has already caused one real error** — a session handover brief was written from it and
presented these four as the currently-active team, two rounds after they stopped. Kept, not deleted,
because the queue itself is a record of what was outstanding at the time. **For live team status
read §4's roster table; for the current work read §1f.** Retained verbatim below:

**Queued next** *(as of ~2026-08-20)*: coder11 implementing §39.70/§39.71 (comparator, points, level); engineer8 evaluating
the optional GFN2 pre-filter; investigate guess-propagation-between-frames for the `engine`/SCF
finding; part 3's measured-offset fix (once R-A's GFN2/DFT product offset is available); condition-7
RMSD check; SP ladder; the xtb-Item cores rule (ADR-110); critic10 review of the GFN2 pre-stage +
retraction (routed, in progress — prior batch already reviewed, verdict OK, see §4/04_REVIEW_LOG.md).
`critic10` reviews source as checkpoints land (`U56-2` verdict: OK, confirmed by direct
re-execution, not inherited from a report; now reviewing the accumulated batch: barrier-agreement
fix, heredoc regex fix, rcfc switch safety fix). `proposer7` owns method spec, ruled Ω stays
emit-only (no hard-coded threshold — U-57 remains open) — funding is gated by the bracket check
instead (§3). `engineer8` (sonnet, replacing engineer7) has read the full handover and holds idle,
correctly not re-litigating anything already settled — see §4 team roster.

---

## 1a. THE RE-RUN — RETURNED, results being analyzed (2026-08-20T09:04:06Z)

Source: `cpu_machine_pilot_results/sei_pilot_work/results/sei_probe_report.cpu.json` +
per-task files under `jobs/`. Guard: 20,065.39 reserved / 21,000. Top-level pilot rollup:

```
P1b                    PASS*         590.844 core-h  (budget 5,328) — 4/4 tasks done rc=0.
                                     *Same EpsInf bug killed all 8 freq steps — P1b's actual
                                     deliverable (r_composite, r_high) is STILL UNMEASURED despite
                                     the pass flag. See §1a finding 5b.
P5                     INCOMPLETE    rollup shows 0.0 core-h (SUSPECT, see below) — 20/22 tasks
                                     done rc=0 per-task; t21/t22 (both li_ec2_cation) MISSING:
                                     no done marker, no p5_task_results, no failures[] entry either
endpoint_prep_reactant NOT_CONVERGED 41.636 core-h  (budget 384) — stopped early, not budget-exhausted
P1 (cost-probe slot)   fail          ~0 core-h (37s wall) — correctly refused by C-8 precondition
                                     (endpoints not certified). NOT a re-run of the excluded TS
                                     chemistry — the gate working as intended. Reserved 9,216
                                     core-h in the guard accounting despite structurally spending
                                     ~0 every time (flagged to engineer8 — worth not reserving full
                                     ceiling for a slot that can't spend it).
P6 (t1/t16/t64)        fail          all 3 refused fast: `solvent_refused (C-5)` — RESOLVED AND
                                     FIXED: `payload/P6.sh` never called `sei_qc_smoke` (P1b.sh/
                                     P5.sh both did) — never retrofitted with ADR-105/108's
                                     smoke-then-production pattern. This round produced ZERO κ
                                     data because of it (κ is the schedule's dominant variable —
                                     cost written into the fix's own comment, not just the mechanism
                                     fixed). 🟢 LANDED, generalized: a test now asserts EVERY
                                     production payload smokes, not just P6, so the next payload
                                     added can't skip it unnoticed.
```

🟢 **Both open questions RESOLVED by critic10, traced to source (04_REVIEW_LOG.md), not
inferred — do not treat "P5: 20/22" as final, see corrected framing below:**
1. P6-vs-P1b/P5 divergence explained above (P6.sh missing `sei_qc_smoke`), confirmed against the
   real artefact (`P6_t1/anchor.meta.err`'s `SolventUndecided` text matches `solvent.py`'s raise
   statement word-for-word).
2. **P5.t21/t22: a genuine wall-clock kill, no tripwire in `P5.sh`** (unlike `endpoint_prep.sh`'s
   explicit per-stage budget checks). Confirmed via `executions.jsonl` having a "run" event but NO
   "finish" event for exactly these two — critic10 explicitly avoided the mtime trap (§0-p.5) and
   used this instead. t20 (same species, different seed/level) is NOT part of the gap — it finished
   with a real, correctly-recorded crash (`converged: false`, done marker present); t20 needed 6.72
   of 7.76h just to crash, consistent with t21/t22 running longer and getting cut off. Genuinely
   unrecoverable from what's on disk without PBS accounting (`qstat -x -f`) to rule out a node
   failure — bundled with an already-open ask for a different incident.
   🟢 **LANDED**: per-species wall-budget check before each launch; SIGTERM trap (PBS sends it
   before SIGKILL, one chance) writes `wall_exhausted.json`; `break` not `continue` (species after
   the stop were NOT ATTEMPTED, a different thing from failing); `collect_p5` reads the markers and
   promotes them to `warnings[]` with an explicit statement that unattempted species must not sit
   in the denominator as if measured. Producer AND consumer landed together — a marker nobody reads
   would have reproduced the exact defect class this round keeps finding. Copied from
   `endpoint_prep.sh`'s existing pattern rather than invented.
   **Corrected framing for any P5-derived figure**: 20 measured (mix of converged + honestly-failed)
   + 2 unrecoverable on the SAME already-flagged problem species (`li_ec2_cation`) — not a flat
   22-item denominator.

🟢 **proposer7's follow-up read, resolves part of the above and adds three material findings —
verified by lead independently, not taken on report:**
1. **ADR-108's reading rule DISCHARGED for this round**: `deck_verification.json` shows `Eps =
   18.500000` (G16's own fixed-width SCRF output format, not our input echo) — the PCM deck was
   APPLIED, not just accepted at face value. `r`/`r_composite`/P5 unit costs from THIS round are
   valid. Confirms P1b/P5 really did run real decks (why P6 differed is resolved above by critic10).
2. **ADR-107's array-dispatch fix HELD on real hardware**: P5 and P1b both show per-task adapters
   and per-task deck verification — last round's VOID defect did not recur.
3. 🔴 **C-8 fired for real and saved the round's worst possible spend**: P1 was refused 3× on
   real hardware (missing convergence/n_imag on record, coplanar-guess detection) — **~2 core-h
   burned instead of 527.8**. First real-hardware confirmation the gate works as designed.
4. 🔴🔴 **P1 reached the cluster at all despite being PERMANENTLY EXCLUDED by user ruling.**
   🟢 **RESOLVED — the "guard" already exists, in the right place**: `endpoint_prep_product` (P1's
   required C-8 precondition) was deliberately removed from the plan when P1 was ruled out, so C-8
   structurally CANNOT ever pass for P1 — this isn't "hasn't failed to fire yet," the input that
   would let it pass was deleted on purpose. Lead's first instinct (remove P1 from the plan
   entirely) was WRONG and retracted: P1b (this round's single LARGEST item, 5,328 core-h) has
   `depends_on=["P1"]` (`plan.py:639`), and the missing_dep check drops any item whose dependency
   isn't present — deleting P1 would silently drop P1b from every future round. engineer8 traced
   the real issue instead: P1's Item is sized as if it might really run
   (`core_hours_budget=6,800, min_wall_h=48.0`, whole-node → 9,216 core-h reserved, ~43% of the
   guard) when it structurally can only ever spend a C-8 refusal's cost (measured: 0.658 core-h,
   37s × 64 cores). **Approved fix, routed to coder11**: keep the P1 Item (satisfies P1b's dependency), shrink
   its budget/wall to ~50–100 core-h / 1–2h (10–50× measured cost, generous margin) instead of
   6,800/48h — recovers ~9,080–9,150 core-h of ceiling, and shrinks the blast radius rather than
   growing it if C-8 ever somehow fails to fire.
   🟢 **LANDED**: coder11 verified the guard before relying on it (checked `guards.ts_precondition`
   directly rather than trusting the claim — P1 is QST2/double-ended, needs a certified product,
   `endpoint_prep_product` only exists inside the still-gated `u56_2_items`, so C-8 refuses every
   time by construction). Resized to 64 core-h / 1h whole-node.
   🔴 **CORRECTED (engineer9, 2026-08-21): the margin was mislabeled ~6,200× — that number used
   0.0103, which is WALL-HOURS, not core-h.** Charged cost is 0.658 core-h (37s × 64 cores); true
   margin is 64/0.658 = **97×**, not 6,200×. The resize decision itself is unchanged and still
   correct (97× is still generous) — same defect shape this project keeps finding: correct number,
   wrong label. Record the 97× figure going forward, not 6,200×; the margin-is-the-safety-property
   principle stands regardless. **9,151.61 core-h recovered** (round reserved 20,065→10,913.39,
   reconciles exactly: 20,065.39 − 9,151.61 + 384.00 = 11,297.39), landing inside
   engineer8's predicted range as an independent confirmation. Exclusion written onto the Item
   itself (title+rationale), not just prose elsewhere. `endpoint_prep_product`'s absence — the real
   guard — pinned by its own test (`test_p1_excluded_sizing.py`, 8 tests) with a failure message
   naming the exact danger (re-adding it silently re-arms P1). Four other suites that used P1 as
   their "big item" example (`test_heterogeneous_sizing`, `test_plan_report_e2e`) repointed to
   P1b (now the round's largest item) with a negative pin asserting P1 no longer shows the
   property — so re-inflating P1 later goes red instead of silently passing again.
   🔴 **Freeze baseline moved 2→4** (`TestPackagedReadmeMatchesCode` ×2): source README's spec
   block correctly updated to match live code (17653→10917, 20065→10913); `dist/` correctly left
   untouched per ADR-086 freeze. Both are freeze signals of the same kind as the two existing
   `test_build_stamp` ones — expected, not a regression, do NOT "fix" without a rebuild decision.
   🟢 **ANSWERED: NOT YET rebuild-ready** (critic10, explicit itemized call, not a rubber stamp —
   04_REVIEW_LOG.md). Confirmed OK/fixed by direct execution: U56-2, G-SCAN-2 v3,
   Ω/spectator/bracket, C-2.1/C-2.2/condition-7, R-5 through R-8, docparse (re-verified after its
   second widening). Gaps before rebuild: (a) 4 diagnosed-not-yet-fixed items can't be reviewed
   until they land in source (P6 smoke call, P5 tripwire, level-label/rc/converged-field trio, the
   EpsInf fix itself — `test_epsinf_bracket.py` exists on disk but not yet reported landed); (b)
   4 unopened test files needing a pass (`test_sp_ladder.py`, `test_p1_excluded_sizing.py` — the P1
   resize that just moved the freeze baseline, unverified whether the 2 new README-parity failures
   are the expected kind of red vs real drift, `test_epsinf_bracket.py`, `test_bplus.py` — already
   on hold separately); (c) confirm B+'s pause is actually gated the same `released:false` way as
   U56-2/sp_ladder rather than assumed. Proceeding on this gate.
   🟢 **Checklist progress (critic10)**: (b)'s B+ item CLEARED — B+ isn't `released:false`-gated,
   it has ZERO external callers (`test_guard_reach.py`'s `DEFERRED_NO_CONSUMER_YET` bucket, same
   reach-enforcement that caught `gscan2_decision` before its producer existed) — no payload calls
   it, so "unreachable" is at least as safe as "reachable but flagged off," confirmed not assumed.
   SP ladder's release-gate mechanism itself CONFIRMED correct (matches U56-2/S-2 exactly).
   🟢 **Gap CLOSED**: `payload/SP_LADDER.sh` still doesn't exist, but the test is no longer a bare
   existence check — coder11 wrote it as the INVARIANT `released ⟹ payload exists` instead, green
   today, goes red only at the moment it matters. Reasoning worth keeping: "a permanently red test
   is one people learn to skip, which is how the gap it guards gets through anyway." A second test
   records the missing payload as a known, stated gap rather than something that looks like
   boilerplate or an oversight. P1 resize CONFIRMED correct, numbers reconciled directly
   (20065 frozen vs 10913–10917 source, ~9,150 core-h drop matches the comment's own claim).
   🟢 **EpsInf fix and `stages_completed` fix both VERIFIED (critic10, direct execution)**:
   `epsinf_bracket`/`epsinf_invariance` confirmed as a genuine two-endpoint bracket wired end to
   end (`solvent.py`→`qc_adapter.sh`'s `SEI_QC_EPSINF`), no silent default anywhere; `9/9` and
   `8/8` tests green; full suite 1549/4 (matches coder11's own report). Remaining, confirmed by
   grep not assumed: level-label fix (`LEVEL_PRIMARY`/`LEVEL_CHEAP` still stale), P6.sh's smoke
   call, P5.sh's tripwire, SP_LADDER.sh gap. `rc` needs no fix (already established
   informational-only). `test_bplus.py` on hold.
5. 🔴🔴 **The endpoint certification FAILED — U-56a's prerequisite 1 is NOT satisfied.**
   🟢 **ROOT CAUSE CONFIRMED, RULED (§39.73, proposer7).** `endpoint_prep_reactant`: stage 1 (rough)
   converged clean; stage 2 (tight+freq) crashed INSIDE `l1110.exe` (the Hessian/frequency module,
   signal 11) right after "NEqPCM: Using equilibrium solvation... EpsInf not defined for this
   solvent." Confirmed mechanism: the PCM read block supplies only `eps=18.5`, no `EpsInf`; rough's
   IDENTICAL read block never touches this code path (no freq stage) — `freq` is the ONLY stage
   that reads `EpsInf`. 🔴 **CORRECTED (§39.74, proposer7 self-caught): NOT the first
   Hessian-under-`solvent=generic` job** — see finding 5a below, this hit ALL of P5's 20 frequency
   stages too, same round, same sentinel. Structural point stands: ADR-108's move to PCM-numeric
   escaped the 7-descriptor SMD problem for energies/gradients only — it DEFERRED the same problem
   to the Hessian stage, exactly the stage C-8 requires.
   **Ruling: bracket it, don't source a number** (3rd use of this move, after the ε 18.5-vs-35.7
   bracket and hyperparameter pairs). Run tight/freq at `EpsInf=1.0` and `EpsInf=18.5` (the full
   physically admissible range, no lookup needed). If n_imag/low-frequency spectrum are INVARIANT,
   EpsInf is irrelevant to C-8 and the blocker dissolves permanently, un-sourced — pre-registered
   prediction (G16's own log says `IEInf=0`, equilibrium solvation shouldn't use EpsInf at all, so
   this reads as a plumbing defect wearing a physics costume). If NOT invariant, that's a real
   finding and `n²` needs sourcing (refractive index — universally tabulated, does not reopen
   §39.26(b)'s Abraham-descriptor blocker). Routed to coder11, priority (unblocks U-56a).
   🟢 **PART LANDED**: `solvent.py::resolve_solvent_deck(..., eps_inf=)` emits `EpsInf=<v>` into
   the read section; `epsinf_bracket(eps)` returns the two endpoints
   `[("no_fast_response", 1.0), ("full_response", eps)]`; `epsinf_invariance(a, b)` compares what
   C-8 actually reads (n_imag + low-frequency spectrum, a mode appearing/vanishing reported as its
   own reason, not folded into "a shift") rather than numerical identity. EpsInf deliberately NOT
   defaulted anywhere — a missing value now says so explicitly in the record
   (`_eps_inf_status: "🔴 ABSENT..."`) rather than silently crashing later. +11 tests.
   🟢 **RESOLVED (engineer8, §R39.43 priced, approved)**: build (a) — inside `endpoint_prep.sh`
   and P5's freq re-run, both — with the collapse switch shaped EXACTLY like the existing release
   gates (`u56_2.released`/`sp_ladder.released`: default ON/doubled, flips to single-run only on
   explicit lead/user action, code never auto-collapses). (a) and (b) cost the SAME core-h (both
   pay for one measurement once) — the real difference is schedule, not price: (b) as a standalone
   probe pays this site's small-job queue-wait tax (measured), (a) rides free inside an
   already-submitted batch. Priced: endpoint ≈40–130 core-h extra (trivial against 384 budget); P5
   ≈800–2,600 core-h extra (25–85% of P5's original 3,128 budget, ON TOP of the freq re-run it
   already needs — this is the number that made the design choice matter). Auto-collapse rejected
   deliberately: risks turning a one-time measurement into either a permanent silent tax (never
   collapses, nobody checks) or an under-verified single-run (collapses on a false-positive
   invariance read) — both failure directions already on this project's record elsewhere.
   Structural note for implementation: run the two EpsInf values as SEPARATE PARALLEL tasks, not
   one job computing both serially, so `endpoint_prep_reactant`'s 6h wall cap and P5's array
   convention both stay intact.
   🟢 **LANDED**: `endpoint_prep_reactant_epsinf_full` shipped as a parallel SIBLING Item (not a
   longer job, not an array — following the P6/ADR-107 lesson that arrays run the whole work list
   on every task), copying the base Item's sizing rather than restating it so the 6h cap/384
   core-h budget can't drift between the pair. `epsinf_bracket.collapsed = false`,
   release-gate-shaped, code never flips it. Round reserved: 10,913.39 → **11,297.39** (+384, one
   endpoint arm). Rippled correctly into 4 registries that assert the exact item set (accounts
   mapping ×3, cpu profile set, README item list/totals) — README also gained a user-facing row
   explaining why the same calculation runs twice, so a package reader doesn't have to infer it
   from an item name.
   🔴 **General rule confirmed from this same job**: `executions.jsonl` reports `rc=0` despite the
   internal segfault — **`rc` may never be used as a QC-stage health signal, content parsing only**
   (§39.69(d) already ruled non-zero-exit⇒no-verdict; this is the mirror case, zero-exit≠success).
   Same conclusion reached independently by critic10 on P5 (see below) — `rc=1` on all 20 rows
   including the 17 that converged. `rc` is noise in BOTH directions on this cluster.
5a. 🔴🔴🔴 **§39.74 (proposer7, urgent self-correction) — the EpsInf bug took P5's ENTIRE frequency
   batch, not just the endpoint cert.** Every P5 species log shows the identical signature: 17/22
   "Stationary point found" (optimizations succeeded), 20/22 "Error termination" at the SAME
   sentinel ("EpsInf not defined... Error termination via Lnk1e in l1110.exe"), **ZERO `Frequencies
   --` lines anywhere in the batch.** Consequences:
   - **§39.72's P5 cost figures (Li ×2.8, open-shell ×2.3, interaction ×15.2) are OPT-ONLY FLOORS,
     not opt+freq magnitudes** — direction very likely robust (an optimizer struggles on the same
     systems a Hessian does) but must not be quoted as opt+freq cost. Relayed to engineer8.
   - 🟢 **`converged: true` silently-narrow-meaning bug — FIXED and VERIFIED (critic10, reproduced
     independently against the real log, not from coder11's report).** Mechanism:
     `jobs/P5/species/h2o_s0_L2/job.log` shows opt's own "Normal termination" at line 1458, then
     freq errors at line 1740 (the EpsInf sentinel) — `g16.summarize()`'s `normal_termination` was
     a PRESENCE check anywhere in the log, not whole-route-completion. Fix (proposer7's shape, "put
     the discriminating fact in the cell"): a `stages_completed`/`stages_missing` field, e.g.
     `completed=[opt,scf], missing=[freq,thermo]` for the crashed case — critic10 reproduced this
     exact split against the real log. `converged` itself is unchanged (still means opt-converged),
     but the missing-stages list makes the gap unmissable regardless. +8 tests (`stages_completed`),
     green.
     🟢🟢 **RULED (§39.78, proposer7, written into 02_METHOD_SPEC.md first): `u_cheap` is
     unambiguously complete opt+freq — this round its denominator is EMPTY.** What the statistic
     is FOR settles the definition: `N₁ = min(600, remaining/(u_measured × r_composite))` asks what
     species we can AFFORD, and affording means obtaining THERMOCHEMISTRY — zero-point + thermal
     corrections, which come only from the freq stage. An opt-only cost is not a cheaper estimate
     of `u_cheap`; it is a DIFFERENT quantity. Report: `u_cheap: null, reason: "no species completed
     freq (EpsInf sentinel, §39.73)"`, and a NEW named quantity `u_opt` (optimization-only cost)
     reports the real number under its own name, never conflated with `u_cheap`. A labeled null next
     to a populated `u_opt` cannot be misread as "P5 lost its cost data" — the earlier worry only
     applies to an UNLABELED absence. `u_opt` also retroactively names what §39.74 already required:
     the cation/open-shell factors (×2.8/×2.3/×15.2) were always opt-only magnitudes with no correct
     name to be quoted under — now they have one.
     🔴 **Condition before the re-run**: once freq lands on the stored geometries, `u_cheap` will be
     ASSEMBLED (opt from this round + freq from later, same geometry/level per `stages_completed`)
     — legitimate, but must say so explicitly, carrying both halves' round/cap provenance plus a
     distinguishing flag (§39.61(c)); a species optimized under one wall cap and frequency-run
     under another has a total no single configuration would reproduce.
   - 🟢 **Net good news: one root cause, one fix (§39.73's EpsInf bracket) recovers BOTH** — the
     optimized geometries already exist in the tree, so once the bracket experiment confirms
     invariance, a re-run only needs to redo the freq half. **P5 is half-collected, not void.**
   - Sharpens rather than weakens §39.73's ruling: the pre-registered invariance prediction is now
     backed by 21 jobs across 4 size classes, 3 charge states, both levels, all dying at the
     identical sentinel — "the signature of a value being read and not used," per proposer7, not
     real physical dependence. And the smoke-doesn't-cover-every-stage point sharpens too: "a route
     smoke that does not exercise every stage the route contains is not a route smoke" —
     `deck_verification.json`'s `[VERIFIED-IN-RUN]` label says nothing about the Hessian path.
   - 🔒 **Durable lesson, proposer7's own words, worth keeping**: *"A mechanism that fully explains
     the case in front of you tells you nothing about its scope — scope is a separate question and
     needs its own evidence."* Caught via a contradiction sitting inside proposer7's own two
     sections (§39.72 had already quoted P5's route containing `freq`), found by one grep run only
     because of that internal contradiction, not by anyone else flagging it.

5b. 🔴🔴 **§39.75 (proposer7) — the SAME EpsInf bug killed P1b's frequencies too, and P1b's actual
   deliverable is still unmeasured despite its PASS flag.** Exact scope, confirmed per-step: 8/8
   `freq`-containing steps died (Error termination, zero frequencies); all 10 `sp`/`force` steps
   fine; 2 `opt5` steps errored but for a DIFFERENT, unrelated reason (a deliberate 5-cycle probe
   hitting its own maxcycles — not the EpsInf sentinel). Confirmed on three items now (endpoint
   cert, P5, P1b): **freq dies, everything else lives** — single points, gradients, and
   optimizations (including finding their stationary points) are all fine.
   🔴🔴 **P1b's whole point was measuring `r_composite`/`r_high`** (the level-cost ratios B1's
   sizing rule consumes, `None` since ADR-088 pending exactly this measurement) — **both remain
   unmeasured.** "PASS 4/4, 590.8 core-h" describes execution completing, not the deliverable
   existing — a 4th item this round whose success flag and delivered quantity disagree (after the
   endpoint cert, P5, and the now-withdrawn "surviving constant" claim above).
   🔴 **`r_composite`'s bias has a KNOWN DIRECTION, not just added uncertainty**: `r_composite =
   (A+C)/A` where A (cheap opt+freq) is missing its Hessian, so A is measured too SMALL, so
   `r_composite` comes out too LARGE, so **any B1 sizing that uses it comes out SMALLER than the
   truth warrants** — conservative on budget, but wrong in the direction that quietly shrinks the
   science, not a safe-either-way error bar. `r_high`'s bias is undetermined (both legs lose
   different Hessian fractions). Routed to engineer8 with this framing intact.
   🔒 **Second self-correction on the SAME batch, same afternoon, same error SHAPE**: proposer7's
   own words — *"I checked whether the numbers were internally consistent, not whether they were
   the quantity claimed."* Worth keeping as the analysis-side twin of coder11's "measured but
   unread" pattern — a number can be correctly computed and still not be what it's labeled as.
   🟢 **Still net good news — "half-collected" holds**: everything except Hessian/freq survives
   (every sp/gradient/optimization cost, every cycle count, every converged geometry). **One
   EpsInf fix now recovers FOUR items simultaneously**: the endpoint cert, P5's 20 freq stages,
   P1b's 8, and `r_composite`/`r_high` themselves — all from geometries already in the tree, no
   re-optimization needed. The earlier "which to work first" question dissolves: it looked like
   four separate problems only because each item reported its own success flag independently of
   what it had actually delivered — which is this whole round's thesis, arriving at four items at
   once.

🟢 **critic10's confirmation of the other two P5 integrity items (§39.72 finding 4), traced to
source, both confirmed real and confirmed UNRELATED to the P6/deck_verified trace — three separate
bugs, not one:**
- **Level label**: `criteria/p5.py:28-29` hardcoded `LEVEL_PRIMARY = "wB97X-V/def2-TZVPPD/SMD"` as
  a string constant, never derived from the real route — checked against a real row, functional
  really disagreed (wB97X-V vs actual wB97XD), not just formatting; solvent label stale too (SMD
  vs actual PCM — this predates and is unrelated to the user's 2026-08-20 PCM-fixed reconfirmation
  above, just an old hardcoded string never updated). These constants doubled as dict keys for the
  cheap/primary cost-ratio calc (`p5.py:172-177`) — same wrong key used both times, so that
  arithmetic was internally self-consistent, not corrupted, but the label was wrong wherever read
  as ground truth.
  🟢 **LANDED AND VERIFIED (critic10, independent)**: labels now derived from `route_echoed`
  rather than a hardcoded string. Turned out worse than "stale" mid-fix: the labels didn't just
  disagree, they named a functional the config doesn't even define. coder11's own new test caught
  a second hole while fixing the first: an unrecognized level key was emitting a plausible-looking
  but wrong string (`?/?/PCM(...)`) instead of failing loud — fixed in the same pass. Suite 1570/4
  (same known freeze-signal set).

🟢 **Full checklist status (critic10, 04_REVIEW_LOG.md)**: level-label, P6 smoke, P5 tripwire, and
the SP-ladder-invariant test all independently verified correct. Process note, not a defect: the
"every production payload smokes" test is a fixed enumeration of 6 payloads, not a dynamic scan of
`payload/*.sh` — a 7th payload needing the pattern later wouldn't be caught automatically. Remaining
at the time: `payload/SP_LADDER.sh` itself unwritten, P5's `diagnostics()` cost-filter question
(methodology, tracked separately), `test_bplus.py` (on hold).

🟢🟢 **EXPLICIT REBUILD-READY CALL (critic10): YES.** Re-ran the full suite fresh once more (1574/4,
same known freeze-signal set, no new failures) before answering. On `SP_LADDER.sh` specifically,
asked directly whether it blocks — it does NOT: `sp_ladder.released` defaults false, nothing sets
it, gated items excluded from `_all_items()` while false (the missing payload is inert in shipped
source today, not just untested); the gap isn't silent (`test_sp_ladder.py`'s invariant test goes
red the instant anyone flips the flag without the file — caught by construction); same shape/
precedent as U56-2, already treated the same way; `test_bplus.py` is zero-external-callers, one
step further out, cannot affect shipped behavior regardless. Stated what WOULD have changed the
answer (a code-settable flag, or an unverified guard test) — neither holds. **`dist/` freeze may
lift per the standing rule (freeze lifts after review passes, not before) — condition now met.**
🟢🟢 **REBUILD DONE.** User authorized directly ("rebuild 지금 돌려"). First attempt collided with
coder11's in-progress `SP_LADDER.sh` write (test gate failed on the same known freeze-signal set,
rolled back safely per the build script's own stale-artifact design — no data lost, old dist/
restored automatically). `payload/SP_LADDER.sh` LANDED in the same window (see below) — the last
Item in the package naming a payload that didn't exist. Retried once coder11 confirmed done:
**succeeded cleanly.** `source_digest c0280111f00cd8e4`, package-verification gate (8 tests) passed,
`build_stamp check` ✅ (tarball matches current source). New `dist/sei_pilot_cpu.tar.gz` (19M, 11
items) and `dist/sei_pilot_gpu.tar.gz` (411K, 2 items) live as of 2026-08-20 19:21.
🟢 **Independently re-verified (critic10)**: `source_digest` matches exactly, `n_files=103` (up
from 94, consistent with today's new files), `test_build_stamp`+`test_readme_matches_code` run
directly (37/37 OK, freeze signals cleared), full suite **Ran 1579, OK, skipped 14, ZERO
failures** — the first fully-green full-suite run all session.

🔴🔴 **CONVENTION RETIRED, IN THESE WORDS (coder11): "4 is normal, they are freeze signals, do not
fix them" is NO LONGER TRUE. The known-red count is 0, confirmed twice (coder11 + critic10,
independently, caches cleared).** Every entry above narrating "failures 4 (known freeze signals)"
describes THAT POINT IN TIME, before this rebuild — do not carry that expectation forward. From
here, **ANY red is a real finding**, including a reappearing `test_build_stamp` (which would now
mean source moved since the rebuild, not that dist is deliberately stale). This is the mirror
image of the earlier "the count grew 2→4, don't panic" note — a stale expectation of red is now
the risk, not a stale expectation of green.
🟡 **RIDER (coder11, stated proactively before it caused a false alarm)**: "any red is a real
finding" needs one exception spelled out — `test_build_stamp` going red IMMEDIATELY AFTER a source
edit, with no rebuild since, is expected (source has moved past `dist/` again, exactly the signal
it's designed to give). The real finding is a `test_build_stamp` red with NO intervening source
change, or ANY red in a different test. Currently red for exactly this expected reason: coder11
edited `guards.py`/`criteria/p5.py` implementing §39.77/§39.78 after the rebuild — 2 reds, both
`test_build_stamp`, nothing else. Rebuild whenever convenient; nothing is blocked on it.

🟢 **§39.77/§39.78 BOTH IMPLEMENTED (coder11)**. Suite Ran 1593, failures 2 (the expected
`test_build_stamp` pair above), skipped 14.
§39.77's recording, on converged IRCs only: `bplus_confirmed` (agrees) / `bplus_refuted`
(disagrees — verdict stays `ok`, the IRC still wins) / `bplus_not_run` (a missed calibration
opportunity, made visible rather than silently absent). Truncated IRCs get no calibration record
at all (no ground truth exists there to check against). Direction of authority pinned by its own
test (`test_a_refuted_bplus_does_not_change_a_converged_verdict`) so nobody can wire it backwards
later without a red test catching it.
§39.78: `u_cheap`/`u_opt` both landed; `verdict()`'s `representative_statistic` string also
relabeled to say outright it's opt-only (closing a second place the wrong reading could enter,
beyond just the new field names). A row with NO `stages_completed` record counts in NEITHER
numerator (unknown is not false), and that count is itself reported. The assembled-total condition
(once EpsInf lands) is implemented as an `assembled: true` flag plus a requirement that both
halves' round/cap provenance travel with it.
**Queue**: everything now needs an actual cluster round, not more code — EpsInf invariance, B+
end-to-end, SP ladder end-to-end. Nothing currently blocked.

🟢 **`payload/SP_LADDER.sh` LANDED (coder11)** — the last missing-payload gap closed. Design:
CONSUMES a path, does not generate one (would duplicate `gfn2_scan`, and would let the ladder
quietly accept a path that never passed the G-SCAN gate — a payload that produces its own input
can always satisfy its own preconditions). Refuses loudly rather than accepting an ungated path:
1-D paths refused at n≥2 (§39.48(c)), a fired G-SCAN verdict refused, <3 kick seeds refused, a
seed record missing attempt-count fields refused (a spread over only surviving seeds is a
success-conditioned statistic). Every refusal is `cause_class: protocol` stating outright "the
ladder must not spend," never "no barrier" — refusals are recorded as data before any DFT is
ordered, not raised as errors. Barrier reference is the path's own first frame at DFT (never the
reactant's energy), route comes from the SAME generator the TS chain uses (drift made structurally
impossible, not just tested-against). Emits `per_sp_core_hours` — this project's first standalone
single-point measurement — and runs the §R39.28 replan comparison itself. Own producer/consumer
test caught coder11's own unread `sp_points.json`/`reference_index` an hour after writing it — same
defect class cited all day, now read by `collect_u56`.
🟡 **Honest edge of the package, three items exist but were never exercised on real data**: EpsInf
invariance (comparator + both plan items exist, the answer needs a real round), B+ end-to-end
(wired, never run against a real IRC — the logs are gone), SP ladder end-to-end (payload exists, no
real path artefact to run it on yet). coder11's own framing: "more code will not move them; a round
will." Nothing in the team's queue is currently blocked on further code — the next real progress on
these three needs an actual cluster round.

🔴 **Finding, B+'s first real review (critic10)**: B+ runs UNCONDITIONALLY on every IRC direction,
never gated on whether the IRC actually needed it (`completion.truncated`). Confirmed this does NOT
produce a wrong verdict (branch a ignores `bplus` entirely once convergence already applies).

🟢🟢 **RULED (§39.77, proposer7, written into 02_METHOD_SPEC.md before the message — standing fix
for the scrollback-loss problem, read the section if any relay ever loses detail again): there is
NO calibration case to identify, because gating consultation on truncation is fine but discarding
the VERDICT on converged IRCs is wrong.** The "waste" is not waste:
```
IRC converged AND B+ agrees     -> B+ was right, on a case where we COULD check
IRC converged AND B+ disagrees  -> B+'s METHOD is wrong here — only knowable because ground truth existed
IRC truncated                   -> B+ is load-bearing AND uncheckable — no ground truth exists
```
Keeping B+ results only where they were CONSULTED (i.e. only truncated IRCs) is the
success-conditioned denominator in its purest form: we would only ever store B+ verdicts on cases
with no ground truth to check them against. **B+ is ALWAYS computed and ALWAYS recorded; whether
it is CONSULTED depends on the branch** — compute-and-record vs consult are different acts (3rd
use of that separation, after C-10.1 for cost probes and Ω). On a converged IRC the IRC WINS
outright, B+ never overrides it — a disagreement impugns B+'s method, not the IRC. This corrects
proposer7's own §39.55(c), which had scoped calibration to R-A only because that was the only case
nameable at the time — the residual is now bounded on every converged IRC ever measured, not just
R-A's. Affordable because C-2.2 makes truncation the common outcome, so converged IRCs (and B+'s
actual per-attempt trigger rate) should be rare in aggregate — currently validated on ZERO
reactions, so each converged IRC is a rare chance to check a method with no track record yet.
🟢 **RESOLVED — engineer8's flat/100%-of-attempts reading was RIGHT; the "× P(IRC converges)" line
was proposer7's own error, corrected in place in `02_METHOD_SPEC.md`** (wrong paragraph left
visible, never deleted, per standing practice). Root cause named precisely: `P(IRC converges)`
belongs to a DIFFERENT quantity — the calibration YIELD (how many attempts B+ can actually be
checked against ground truth on), not the trigger rate. proposer7 attached a real number to the
wrong noun while ruling about that exact noun — §39.76 (agreement-is-not-identity) recurring a
THIRD time today, this one caught by engineer8 reading the spec before pricing off it rather than
by proposer7 re-reading their own work (today's spec errors: 3 caught downstream, 0 caught by the
author — noted as a reason to keep the "write the spec, let others read before acting" practice
rather than trying to self-check harder, not a reason to distrust the practice).
🟢 **Pricing guidance**: B+'s terminal optimizations start from IRC path points — near a minimum on
a converged path, mid-descent on a truncated one — so B+ is actually CHEAPER on converged IRCs.
Anchoring the flat per-attempt figure on the truncated-case cost (the more expensive scenario) is
conservative, the right direction for a guard ceiling.
🟢 **CLOSED (engineer8, §R39.44)**: T11-se's 97 core-h/attempt stands exactly as priced, now
confirmed UNCONDITIONAL (runs on both branches, no gate) rather than conditional — no reprice
needed, only the "when it runs" framing changed. (T21-se's separate 931 core-h figure remains
RETRACTED on unrelated grounds — the atom-count cube-law problem from §1's earlier note — this
resolution doesn't revive it.)
- **`rc` quirk**: confirmed as real Linda-wrapped-Gaussian behavior (worker cleanup can set
  nonzero exit after a clean "Normal termination"), not a bug in this project's code — h2o's row
  has `rc=1` AND `converged=true` simultaneously, about as simple a convergence case as exists.
  Checked whether dangerous: `rc` is only ever passed through (`p5.py:81`), never gated on
  anywhere in the P5 pipeline — `converged` is computed independently from log content. Hazard for
  a future human/code assuming `rc==0`⇒success, not currently active corruption.
6. 🔴 **The previous round's P1 raw evidence (`ts_qst2.log`, `irc_forward.log`, `irc_reverse.log`,
   `ts.xyz`, `stages/`) is GONE — overwritten by this round's re-use of the same job-key directory,
   not deleted by anyone this session.** Every published number (Ω=0.022, the −48.4 cm⁻¹ mode,
   d(O2–C3)=3.184 Å, the C-2.1/C-2.2 maxpoints pair, §39.70's 30 arc lengths) stays reproducible
   ONLY because coder11 had already stored verbatim fixtures with provenance
   (`tests/fixtures/g16_*_p1_*.{log,txt}`) earlier today — but the full IRC path GEOMETRIES were
   never fixture'd (only tails/marker lines), so **B+'s path-frame extraction has lost its only
   real test subject** until/unless a fresh real IRC lands. Worth being aware this job-tree reuses
   directory names across rounds — a future re-submission under the same job keys will do this
   again to whatever is in there at the time.

Also routed: proposer7 for the chemistry read on the 20 successful P5 species + P1b's 4 (now also
working the L1110 crash, higher priority); engineer8 for the real spend reconciliation once the P5
rollup question is settled.

🟢 **proposer7's chemistry read of the 20 real P5 species — §39.72, done, two durable planning
findings + a taxonomy confirmation + two integrity flags for critic10:**
1. 🔴🔴 **Cost driver is the cation and open shell, not atom count — and they INTERACT.** Measured
   on same-size pairs: +1 Li⁺ alone ×2.8, +1 unpaired electron alone ×2.3, BOTH together ×15.2
   (independent factors predict only ×6.4 — a real ×2.4 interaction). **`N^x` is the wrong shape
   for E21/T21-se — do not cube-law them** (routed to engineer8). R-C's reactant is cation+
   open-shell+21-atoms simultaneously; the closed-shell li_ec2_cation ALONE already cost 429.55
   core-h and didn't converge in 49 cycles. U-55 (Li-complex expense) is now a measurement, not a
   suspicion.
2. 🔴🔴 **`u_measured` is a DISTRIBUTION, not a point — ~5× spread across seeds of the SAME
   species at the SAME level** (ec ×4.4, ec_radical_anion ×5.4), wider than the level ratio r
   itself (1.0–1.25). `N₁ = min(600, remaining/(u_measured × r_composite))` needs to account for
   this — extends ADR-087's no-pooling-across-strata rule to no-pooling-across-seeds-within-a-
   species either (routed to engineer8). The lever: cost tracks `opt_cycles` almost exactly, which
   tracks starting-conformer distance from the minimum — first real measurement of what B0-D arm 1
   (conformer quality) is worth in core-h. proposer7 caught their own first-pass error here (pooled
   r=2.890 for ec, corrected to seed-0 r=1.074) — same self-correction discipline as elsewhere
   today.
3. 🟢 **`engine`-class confirmed on real DFT data, hours after being ruled for GFN2.** 3 apparent
   non-convergences were actually TWO different failures: 2/20 genuine SCF-never-converged
   (`engine`, `scf_max=129` = G16's default limit+1) vs li_ec2_cation's optimizer wandering
   (`scf_max=14` fine, `opt=49` — U-55's floppy-PES signature, prescription is conformer quality,
   NOT SCF settings). A single `not_converged` label would have merged them and pointed at the
   wrong lever.
4. 🟢 **Two integrity flags — CONFIRMED by critic10, both traced to source, see §1a finding 5a
   above** (level label hardcoded at `criteria/p5.py:28-29` never derived from route; `rc` quirk
   confirmed as real Linda-Gaussian behavior, not gated on anywhere so not currently dangerous).
5. 🔴🔴 **WITHDRAWN (§39.75, proposer7 self-correction #2 on this same batch)**: the seed-0 `r`
   values above are ALSO opt-only ratios, not the opt+freq ratio B1's sizing rule actually needs —
   they are not confirmation of anything. Do not cite them as such. See §1a finding 5b below for
   the full scope (this affects P1b's r_composite/r_high directly, not just this one claim).

---

## 1b. THE EpsInf BRACKET ROUND — CANCELLED BY USER RULING, 2026-08-21. Superseded by §1c.

🔴🔴 **The entire EpsInf bracket investigation below (§39.73–§39.97) is CANCELLED.** User ruling,
direct and final: use `scrf=(pcm,solvent=acetone,read)` + `eps=18.5`, never an explicit `EpsInf`
value, never `solvent=generic`. Reason given: this is standard, extensively-used practice. The
section below is kept as history (it's real, verified work — the root-cause diagnosis, the
harness/retry-policy fixes it produced, the nosymm/C-9 audit finding — all of that survives and is
summarized in §1c) but the BRACKET QUESTION ITSELF (does the EpsInf value matter) is moot: acetone
supplies a real, internally-consistent parameter set, there is no value left to bracket. See §1c
for the current, active state.

Source: same `results/sei_probe_report.cpu.json` path, `jobs/endpoint_prep_reactant*`. This round
was meant to answer §39.73's bracket question: does the L1110 segfault (missing `EpsInf`) reflect
a real physical dependency, or is it a plumbing defect (proposer7's pre-registered prediction:
plumbing, invariant)? Team respawned to work it: proposer8, coder12, engineer9, critic11.

```
endpoint_prep_reactant (EpsInf=1.0)        not_converged  — jobid 23673264, timestamp
                                            Thu Aug 20 10:28:35 2026, same "EpsInf not defined"
                                            crash as YESTERDAY's pre-fix log
endpoint_prep_reactant_epsinf_full (=18.5) converged       — jobid 23693528, timestamp
                                            Thu Aug 20 21:05:09 2026, n_imag==0, real
                                            C-8.2/C-8.3 certificate — genuinely NEW
```

🔴🔴 **UNVERIFIED (lead's first pass, not yet confirmed by the team): the EpsInf=1.0 arm looks
like it was NEVER actually resubmitted this round.** `state/endpoint_prep_reactant.done.json`
carries the OLD epoch (1787189319) matching yesterday's original submission, and
`endpoint_tight.log`'s crash content is byte-identical to the pre-fix log (still shows
`EpsInf=0.0000`, still hits the same sentinel) — consistent with the harness's "already has a done
marker" check skipping resubmission rather than forcing a fresh run when the item's config (the new
`SEI_QC_EPSINF` value) changed. If confirmed, **this is NOT a completed 2-point bracket** — only
one genuinely new data point exists (EpsInf=18.5, converges), and the invariance question is still
open. Do not conclude the bracket prediction succeeded OR failed from this data as it stands.

Routed: proposer8 to verify independently and hold off on any invariance conclusion; coder12 to
find and (if confirmed a real gap) fix the resubmission-skip logic, and determine whether it needs
to force-rerun on config changes rather than just check a done-marker's presence — same defect
SHAPE as everything found yesterday (a status marker trusted without checking whether what it
marks as done is still what would be produced now); critic11 to independently verify the staleness
claim from raw files, not inherit lead's read; engineer9 to do routine cost reconciliation on what
DID genuinely run (P1/P1b/P5/P6/endpoint_prep_reactant/..._epsinf_full) and price the epsinf_full
arm's real cost against the ≈40-130 core-h estimate, plus check whether P6 (fixed yesterday) shows
real κ data this time.

🟢 **CONFIRMED (coder12, decisive evidence, independent of lead's read)**: the rendered
`jobs/endpoint_prep_reactant/endpoint_prep_reactant.qsub` has NO `SEI_QC_EPSINF` line at all — the
item was never even RENDERED with the new config, not just old-looking. The sibling's qsub has
`export SEI_QC_EPSINF="18.5"` at line 36. `endpoint_tight.log` for the base item is the pre-fix
crash (Leave Link timestamps match yesterday exactly); the sibling's log shows
`Eps=18.5000, EpsInf=18.5000` and converges. **The bracket has ONE point (EpsInf=18.5), not two —
invariance cannot be read from this round.**

**Root cause**: `cli.py`'s submit loop did `if store.is_done(key): skip` — a pure marker-PRESENCE
check, nothing compared the marker against the current plan entry. The only re-run path was manual
`--rerun KEY`, which nobody invoked because nobody knew the item's spec had changed. Same defect
shape as everything found yesterday: a status marker trusted without checking it still describes
what would be produced now. (A precedent one level down already existed:
`payload/common.sh::sei_stage` checks a `pkg_fingerprint` on stage checkpoints — item-level markers
had no equivalent.)

**Fix landed**: `state.py::spec_digest(entry)` — sha256[:16] over computation-defining plan fields
(`key, payload, extra_env, nodes, array, chain_links, cores_per_node, gpus`; deliberately NOT
account/partition/pkg-root, which change WHERE not WHAT). `Store.done_spec_status()` →
`match | stale | unknown`. `submit_entry` writes the digest into the submitted marker; at submit
time: `stale` → `reset_item` (markers moved to `.reset.<epoch>`, never deleted) + loud print +
AUTO-RESUBMIT; `unknown` (every marker currently on disk, since none predate this fix) → still
skipped, prints a warning to use `--rerun` manually — deliberately NOT auto-rerun, since the
existing workdir's P1b/P5/P6/probe markers pre-date digests and auto-rerunning them would burn
thousands of core-h. `tests/test_done_spec_digest.py` (4 tests). Full suite 1597, 2 failures = the
expected `test_build_stamp` freeze signals (source changed, `dist/` untouched, per ADR-086).

🟡 **Policy point flagged by coder12, engineer9 asked for a cost-safety read**: `stale →
auto-resubmit` is coder12's choice (the item's core-h is already reserved/printed by preflight, and
the opposite failure is exactly what just cost this round) — not yet independently checked for
cost-exposure edge cases. critic11 separately reviewing for correctness.

**Action required, not urgent**: `endpoint_prep_reactant` needs a manual `./run.sh ... --rerun
endpoint_prep_reactant` to actually get the real EpsInf=1.0 data point (cost: the reserved 384
core-h / 6h wall, same as the sibling). Every other item on disk will also print the "unknown,
use --rerun if config changed" warning on next submission — expected, not a new problem.

🔴🔴🔴 **ESCALATED (proposer8, §39.80 in 02_METHOD_SPEC.md, ~200 lines, full detail there) — the
scope is much larger than the base item alone. Now recorded as ADR-113 (01_DECISION_LOG.md).**

1. **Decisive evidence, stronger than the timestamp match**: `endpoint_prep_reactant`'s rendered
   `.gjf` deck has NO `EpsInf` line at all (not even the wrong value) — proves it was never even
   RENDERED with the new config, let alone run.
2. **Scope escalation**: this round only actually ran THREE things — the new
   `endpoint_prep_reactant_epsinf_full` key, `P1` (retried, failed again for its own reason, rc=6),
   `P6_t1/t16/t64` (retried, now done). EVERYTHING carrying a yesterday done-marker was silently
   skipped: the base endpoint item, all 20 `P5` tasks, all 4 `P1b` tasks, the probes. Yesterday's
   stated "one fix recovers four items" recovery has NOT STARTED.
3. **Second, independent defect**: `results/plan.json`'s `extra_env` is `{}` for `P5`/`P1b`/`P6_t*`
   — only the two `endpoint_prep_*` items ever got `SEI_QC_EPSINF` wiring at all. Even a correctly
   forced P5 re-run today would reproduce all 17 sentinel crashes, because the fix was only wired
   into `endpoint_prep.sh`, never `P5.sh`/`P1b.sh`. Routed to coder12, must land before any P5/P1b
   recovery round.
4. **Bracket question: genuinely UNTESTED, neither confirmed nor refuted.** One converged data
   point (EpsInf=18.5: n_imag=0, E=−349.620897959 Hartree, G=−349.578085 Hartree, lowest three real
   frequencies 77.0220/106.9681/151.7485 cm⁻¹, recorded as the pre-registered comparison reference)
   is consistent with invariance, strong dependence, and everything between. What it DOES confirm:
   supplying any admissible EpsInf removes the crash, a C-8.2/C-8.3 certificate is obtainable, and
   §39.73's "freq is the only stage that reads EpsInf" mechanism claim survives a second check
   (`NEqPCM` appears 0× in rough logs, both arms, nonzero only in tight). What it does NOT confirm:
   independence from the value chosen.
5. **Re-run spec, fresh-key/no-`--force` clauses APPROVED and UNCHANGED**: low arm goes out under a
   FRESH key (`endpoint_prep_reactant_epsinf_unity`), never the base key, never `--force`.
   🟢🟢 **SUPERSEDED (§39.81, proposer8, withdrawing their OWN earlier clause before it shipped) —
   design (A) "both arms full re-run, 130 core-h" is REPLACED by design (C): both arms are
   FREQ-ONLY jobs from the stored `endpoint_tight.chk` checkpoint (the geometry the 18.5 arm
   already certified), ~5-10 core-h total, not 130.** Not just cheaper — MORE sensitive: a
   full-reopt design's noise floor is optimizer instability (§39.80(d) measured 5.6 meV between two
   independent rough-stage runs, LARGER than the effect the experiment exists to bound — that
   design could only ever return "not resolved," misread as "invariant"). Fixed-geometry floor is
   SCF convergence, ~1e-8 Hartree — criteria tighten to n_imag identical, |ΔE|≤1e-7 Ha, |Δν|≤0.1
   cm⁻¹ across all 27 modes (~4 orders of magnitude tighter). Justification: C-8.2/C-8.3 certifies
   a GEOMETRY, not a trajectory, so "does EpsInf change n_imag/spectrum at the certified structure"
   IS the question with nothing else varying — confirmed by line number that EpsInf is read only at
   Hessian construction (rough stage: 0 occurrences of `NEqPCM`; tight stage: read at the step-1
   `calcfc` and at `freq`, never during the 4 intervening Berny cycles) — energy/gradient are
   EpsInf-blind, so a point stationary at 18.5 is stationary at 1.0. `pkg_fingerprint` confound also
   removed by construction (both arms generated by the same package, same round, same checkpoint).
   `readfc` FORBIDDEN in both arms (would compare a stored Hessian against itself). Both arms seed
   from the SAME checkpoint density (open-shell doublet, UHF non-unique) — the existing 18.5 output
   is NOT reused as-is for exactly this reason, run fresh alongside the new arm.
   **Free residual check, no extra job**: compare the two arms' printed force matrices — identical
   to precision ⟹ gradient confirmed EpsInf-blind at this geometry, residual closed (measured, not
   argued); NOT identical ⟹ premise wrong, fall back to design (A), pay the 130 core-h — a
   pre-registered escape hatch with its own fallback named in advance. **Free plumbing check**: new
   18.5 arm must reproduce the EXISTING in-job numbers exactly (77.0220 cm⁻¹, −349.620897959
   Hartree) or no verdict may be read from either arm.
   🟢 **Scheduling (§39.83, proposer8): design (C) is blocked on the SAME coder work as P5's design
   (B) — one build serves both.** Both need: a freq-only route type in `sei_qc_input` (today only
   `opt_freq`), start geometry from a stored converged log/checkpoint, and the opt/freq stage
   split. Refusing design (A) as a "quick" shortcut even though it needs no coder work and is
   available today — NOT on cost, on the same noise-floor argument above; kept only as a
   contingency line if (C)'s force-matrix check fails. Self-correction folded in: the two EXISTING
   job directories (crashed base arm, certified 18.5 arm) are confounded by THREE separate builds,
   not one — §39.80(d)'s 5.6 meV rough-stage delta is weaker evidence than its own caveat claimed,
   downgraded. Design (C) is immune by construction (one build, one round, one checkpoint).
   🟢 **Priced (engineer9, §R39.47): CONFIRMED 7.9-9.3 core-h for both arms** (measured basis, not
   rescaled — freq/Hessian 2.27 [MEASURED], SCF re-convergence 0.04-0.71 [ESTIMATE, 1-19 cycles],
   setup+smoke+wrapper ~1.7 [MEASURED]) — 1.2% of the pair's existing reservation. New measurement:
   the tight stage's SCFs ran 19→14→10→5→1 cycles across its 5 solves; 3 separate SCFs AT THE SAME
   converged geometry agree to 1e-9 Hartree (100× tighter than the 1e-7 criterion) — same
   node/thread count, cross-job/cross-node unmeasured. This makes the "free plumbing check" above
   the actual CROSS-JOB REPRODUCIBILITY MEASUREMENT, not just a sanity check — must be read BEFORE
   the U-vs-F comparison; if arm F can't hit 1e-7, report the achievable floor, do NOT loosen the
   criterion after seeing the data.
   🔴🔴 **Two silent implementation traps found (engineer9), both would quietly undo the saving**:
   (1) shipping design (C) as a flag on the EXISTING `endpoint_prep.sh` would silently become
   design (A)'s price — that payload's rough stage resumes only on a matching `pkg_fingerprint`,
   which won't match (already 3 different builds involved), so `sei_stage` re-runs the rough
   optimization with NO ERROR, just a `rerun_stale_fingerprint` log line, turning ~4 core-h/arm
   into ~62 core-h/arm. Design (C) MUST be a genuinely separate payload with no rough stage at all.
   (2a) whole-node sizing would reserve ~30× the actual work (3rd occurrence of this exact shape:
   xtb anchor ADR-110, B+ terminal opts, now this) — declare `cores_per_task` explicitly. (2b) both
   arms MUST run at the SAME thread count — not cosmetic: Gaussian's parallel reductions are
   deterministic per thread count but not necessarily across counts, so a mismatch could manufacture
   a fake difference at exactly the magnitude the criterion tests. This is also why the 16-thread
   packing validation (already approved) stays a fully SEPARATE job, never combined with the
   bracket.
6. **New pattern named: "DESIGNED-BUT-NOT-RUN, REPORTED AS PLANNED."** Nothing in the returned
   artefacts distinguishes "this ran and produced X" from "this was silently skipped and X is
   stale" — `plan.json` says `"status": "planned"`, `"skip_reason": null`, rollup `n_skipped = 0`.
   Zero-cost mechanical prevention for future multi-arm experiments: assert each arm's done-marker
   epoch is later than the round's submit epoch, AND assert the arm's own rendered deck actually
   contains the value that defines the arm — the second assertion is the strong one (a timestamp
   can be argued about, an absent value in the input file cannot).
7. **ADR-113 records the two-clause harness-contract fix**: clause (ii) — configuration fingerprint
   comparison (`spec_digest`, coder12's fix, LANDED) — and clause (i) — done marker must be written
   from PARSED CONTENT, not the wrapper's exit code (routed to coder12, NOT yet landed). Both
   required: clause (ii) alone still loses a same-config resubmission that crashes again the same
   way (it would mark itself done and be correctly-but-uselessly matched as not-stale forever).

🟢 **Independent verification (critic11, 04_REVIEW_LOG.md): FIX-THEN-RUN.** Confirmed staleness
directly (missing `EpsInf` line in the deck, `submit_epoch` predating the round), confirmed
`plan.json`'s `extra_env.SEI_QC_EPSINF="1.0"` WAS set correctly (the PLAN was right, only execution
didn't reflect it — useful for isolating which layer broke), read `cli.py`'s fallthrough directly
rather than trusting a description. Suite 1597/2 (expected `test_build_stamp` pair), no regression.
**Operational point, now a checklist requirement**: the already-returned `endpoint_prep_reactant`
item will NOT self-heal from the spec_digest fix — its marker predates the digest field, so
`done_spec_status` reads `unknown` (deliberately conservative — skip, not auto-rerun) and a plain
next submission would skip it AGAIN. Must be handled via the fresh-key sibling approach (below) or
an explicit `--rerun`, not left as something a human has to remember. Also found the same defect
PATTERN latent in `cli.py`'s `probe_queuewait` subkey loop (~lines 781-806) — separate skip logic
bypassing `spec_digest` entirely, not currently triggering, routed to coder12 as non-blocking.

🔴 **Digest bug found (critic11), while answering coder12's own questions**:
`SPEC_DIGEST_FIELDS` includes `cores_per_node`, which for whole-node DFT items
(`cores_per_task=None`, includes `endpoint_prep_reactant`) is a LIVE cluster probe result (node
core-count mode), not static config — it can shift run-to-run (a drained node, a different visible
login node), spuriously marking a genuinely-completed item `stale` and auto-resubmitting it for a
reason unrelated to the actual computation. Not wrong results, wasted core-h. Routed to coder12:
exclude `cores_per_node` from the digest, or make it conditional. Other 3 questions confirmed safe.

🟢 **engineer9's cost-safety read on `stale → auto-resubmit`, §R39.46 in 03_COMPUTE_PLAN.md: SAFE
on cost grounds, traced to source not description.** Confirmed structurally, not incidentally: an
item's core-h ceiling is reserved by `guard.reserve()` (unconditional, in `plan.py::build_plan()`,
which never consults marker state) BEFORE `store.is_done()` is even consulted (only inside
`cmd_submit`'s loop) — an auto-resubmit cannot push a round past a guard that round already passed.
Three exposures found, none the one asked about:
- 🔴 **A (same as critic11's `cores_per_node` finding, sharpened)**: latent, not live this round
  (every current marker predates the digest field, stays `unknown`/skip-only) — but ARMS next
  round: if node-detection returns a different value on a resume, EVERY item's digest flips at
  once, the ENTIRE workdir auto-resubmits (~1,700 core-h on this workdir: P1b 595 + P5 1,003 + P6 6
  + endpoints 108, plus a full round of calendar, no prompt). A one-item flip is a plan edit; an
  all-items flip is an environment artefact — that distinction is free to compute. Fix options:
  drop `cores_per_node` from the digest, or cap the blast radius (refuse auto-resubmit past N items
  going stale in one pass, require `--rerun`).
- 🔴🔴 **B — the serious one, a FALSE NEGATIVE, live TODAY, not latent.** `SEI_QC_LEVEL` (the
  `--level g1|g2` flag, the theory level every payload runs at) lives in `common_env`
  (`cli.py:697`), NOT in `entry["extra_env"]`, NOT in `SPEC_DIGEST_FIELDS`. `./run.sh --level g2`
  against a `g1`-done workdir returns `match` on every item, skips everything, assembles a report
  claiming g2 results that are actually g1. Same hole covers `SEI_QC_MODULE`/`SEI_QC_LOGIN_PATH`.
  **This saves core-h while corrupting the answer** — same failure class already caught once
  (`criteria/p5.py`'s hardcoded level label). Routed to coder12 urgent, and to critic11 directly
  for a dedicated check, since a finding that "presents as a saving" is exactly what survives a
  review looking for over-spend rather than wrong answers.
- 🟡 **C**: `chain_links` (in the digest, derived from budget/wall) flips the digest only when a
  wall-cap change happens to alter the rounded link count — non-monotone coverage, and contradicts
  the digest's own docstring naming wall-rounding as WHERE/HOW that must not invalidate. Minor,
  logged, not blocking.
- 🟡 **Evidence-preservation gap, separate from all three**: `reset_item` already protects markers
  (rename, never delete) and stage checkpoints (`pkg_fingerprint`-gated resume cuts A's price when
  no rebuild intervened) — but NOT the job directory itself, which gets overwritten on resubmit,
  the exact mechanism that destroyed P1's IRC logs. Fix: rename `jobs/<key>` before an
  auto-resubmit too, same pattern as the markers. Routed to coder12.
No objection to `stale → auto-resubmit` itself on cost grounds — B is the one to close before
calling this settled.

🟢 **B CONFIRMED by critic11, direct execution, not description**: literally demonstrated
`g1 vs g2 digest, same entry object: True` — `SEI_QC_LEVEL` never enters `entry` at all (`plan.py`'s
`qc_level` param only feeds the summary dict, never a per-item field), so `spec_digest(entry)`
structurally cannot see it regardless of what the digest function does. Confirmed real physics
content, not scheduling: `P1.sh:21`/`P1b.sh:240`/`P6.sh:29` all read `SEI_QC_LEVEL` directly to pick
theory level. Checked systematically for a third instance (enumerated every `SEI_...` env key in
`cli.py`) — none found beyond `SEI_QC_LEVEL`/`SEI_QC_MODULE`/`SEI_QC_LOGIN_PATH`; the WHERE/HOW keys
(`PKG_ROOT`/`WORKDIR`/`PARTITION`/`ITEM`/`WALL_H`) correctly excluded. **VERDICT: BLOCK** — do not
resubmit with a different `--level` against an existing workdir until this lands. Logged separately
for later, not urgent: `spec_digest` only sees `entry`'s shallow fields, so a config FILE's contents
changing (e.g. `qc_levels.json` edited) without any entry string key changing also wouldn't be
caught — stage-level `pkg_fingerprint` catches this within a job, but nothing catches it at the
top-level `is_done` skip decision.

🟢 **Rulings landed 2026-08-21 on coder12's follow-up questions (also folded into ADR-113)**:
- **Clause (ii) scope, coder12's pushback CORRECT**: `pkg_fingerprint` stays OUT of the
  auto-resubmit-triggering `spec_digest` (would force-rerun every done item on any package edit —
  thousands of core-h per rebuild); it IS still recorded in the marker, but only as raw material
  for the manual analysis-side confound check (§39.80(h)), never as an auto-trigger.
- **Clause (i) retry-policy trap, resolved by reusing existing infrastructure**: payloads
  deliberately `exit 0` on a genuine `not_converged` chemistry result (§39.69(d), failure-as-data)
  — a naive "retry on any non-converged outcome" rule would auto-resubmit every legitimate negative
  chemistry result forever, burning core-h for zero new information. RULED: the done marker's
  `outcome` field reuses the SAME cause_class taxonomy (chemical/budget/protocol/engine/unknown);
  auto-resubmit only on the plumbing-shaped classes (protocol/engine/unknown), NEVER on
  chemical/budget (a real completed answer). coder12's approved-now, no-ADR-needed visibility work:
  embed `outcome` in the done marker + skip-line print, and add `terminal_status.json` emission to
  P5/P1b (which currently only write per-task files, no top-level verdict record).
- **Re-queue design, approved**: EpsInf low arm ships as a second sibling from
  `epsinf_bracket_items`, not via `--rerun` on the base key (avoids overwriting the crash evidence).
- 🟢🟢 **SUPERSEDED (§39.82, proposer8): P5 and P1b need NO bracket at all — different shape from
  §39.81's "one species first" framing above.** Core insight: a Hessian's core-h cost does not
  depend on EpsInf's VALUE (same molecule/basis/grid/derivative passes) — so a doubled P5 cost-run
  is GUARANTEED to agree by construction. **"A measurement that cannot fail is not a control, it
  is a tax."** Ruling: P5/P1b run at a SINGLE value. Their COST deliverables (`u_cheap`, `r_composite`,
  `r_high`) are usable immediately (EpsInf-invariant by construction). Their CHEMICAL deliverables
  (n_imag, ZPE, thermal corrections, any free energy) are stamped with the EpsInf value used and
  stay UNCERTIFIED by default — collapses to certified only on explicit lead action, once BOTH the
  endpoint bracket AND the spot-check below return invariant (the gate moves from the RUN to the
  READOUT — same shape as engineer8's original release-gate pattern, relocated to what it protects).
  engineer8's two structural points kept verbatim: bundle the bracket inside a batch already being
  submitted (this site's queue wait inverts with size), run the two values as separate parallel
  tasks, never one serial job (6h wall cap is tight against a serial double Hessian).
  🔴🔴 **"Base" is NEITHER 18.5 nor 1.0 — both are bracket ENDPOINTS, not solvents.** Choosing 18.5
  because "it's the value that converged" is SURVIVORSHIP BIAS: the other arm never even ran, there
  is no evidence it converges worse, there is no evidence about it at all — a physical parameter
  selected on the outcome of a crashed run. **Ruled: base = the physical value, EpsInf = n².**
  🟢 **SOURCED (§39.84, proposer8, one search round, no compute — closed rather than left open
  since an `[UNVERIFIED PROVENANCE]` tag surviving multiple rounds becomes de facto acceptance)**:
  **EpsInf = 1.93 ± 0.02** (range 1.910–1.933 across source combinations; the spec's pre-existing
  1.95 was ~1% high, immaterial in every current use). Tag: `[CATALOG-GRADE PROVENANCE]`, NOT
  primary literature — supplier aggregates (ChemicalBook/ChemBK/LookChem), EC entry carries no
  temperature at all. Two internally-inconsistent data points found in search (backwards
  temperature dependence) were seen and deliberately NOT used. Own earlier Lorentz-Lorenz-vs-bare-
  average caveat (§39.82(d)) RETRACTED as immaterial once measured: difference ≤0.0011, three
  orders of magnitude below the inter-catalog spread (0.023) — correct in principle, irrelevant in
  magnitude. New systematic named, not yet acted on: pure EC is SOLID at 298K (mp 34-38°C), so any
  pure-EC refractive index at 20-25°C is necessarily a supercooled/extrapolated value — only a
  measurement on the actual 3:7 mixture at 298K fixes this, no better catalogue can. Deliberately
  stopped at catalog-grade rather than going to primary literature: if the bracket returns
  invariant, EpsInf enters nothing and 1.93/1.95/18.5/1.0 are all equally right; if dependent,
  catalog-grade isn't good enough AND the fix isn't a better pure-component number anyway (it's a
  mixture measurement) — further pure-component sourcing is wasted either way. Same
  "design so the value doesn't need to be known yet" move as §39.73(c), applied one level up to the
  sourcing task itself. Still inside the bracket interval [1.0, 18.5] by construction — not a
  coincidence, it's why the bracket was specified on the interval. **Unconditional
  requirement**: every C-8 certificate must record the EpsInf value it was computed at.
  **Consequence accepted openly**: the already-certified 18.5 endpoint result is now a PROVISIONAL
  certificate — a valid bracket arm, not the production number — unless the bracket itself returns
  invariant, in which case it stands unchanged. "The invariance test paying for itself: ~5-10 core-h
  decides whether a 65.9 core-h certificate holds."
  **Spot-check species, sharpened**: selection rule (survives a species-list change) = maximize
  reaction-field coupling — net charge first, then diffuse/polarizable density, then soft
  low-frequency modes; a neutral rigid molecule is the weakest possible probe. Chosen:
  **`ec_radical_anion`** (anion, open-shell doublet, soft ring modes, IS the S1 reduction
  intermediate — a null result is directly reusable, not a proxy). Fallback if pricing exceeds
  ~20 core-h: **`hco3_anion`** in P1b (charge −1, 5 atoms, geometry already stored — cheapest
  charged probe on the board). Pricing routed to engineer9, result pending.
  **New corroboration folded in from §39.75(a)**: P1b's 10 `sp`/`force` steps all terminated
  normally; all 8 steps containing `freq` died — single points live, gradients live, optimizations
  live, every Hessian died. Reinforces §39.81's mechanism claim (EpsInf read only at Hessian
  construction) independently.
  **P1b's scope** now RULED alongside P5 (same reasoning, same conclusion: single value, no
  bracket, readout-gated) — no longer open.

🟢 **Cost reconciliation (engineer9, §R39.45 in 03_COMPUTE_PLAN.md), independently confirms the
staleness finding from the cost side**: `endpoint_prep_reactant`'s single run/finish pair is
2026-08-20T00:48–01:28Z, **8 hours before the previous package was even generated** — cannot be a
product of this round. Actual spend this round: ~72.83 core-h total (0.64% of the 11,297.39
reservation) — P1 refused again (4th consecutive, 0.658 core-h), P6_t1/16/64 retried and done,
`endpoint_prep_reactant_epsinf_full` genuinely ran (65.867 core-h: rough 51.62 + tight 4.14 + freq
2.27 + overhead 7.84). **engineer8's 40-130 core-h endpoint-arm estimate CONFIRMED** (measured
65.87, within band, first `[MEASURED]` value for that `[ESTIMATE]`).
🔴 **Key cost insight**: 65.87/2.27 = 29× — a full re-run redoes rough+tight from scratch when only
the Hessian (freq) stage depends on EpsInf. Completing THIS bracket (the missing EpsInf=1.0 arm)
costs 2.27 core-h freq-only from the already-stored `endpoint_tight.chk` (10.5MB, on disk) vs 65.9
as a fresh full job — cheapest open decision on the board once proposer8 rules whether a
freq-only-reusing-a-differently-optimized-geometry bracket is scientifically valid (routed).
🟢 **P6 real κ = 1.619** (cluster/dev-box slowdown, G16 DFT chain only, NOT xtb/GFN2) — first
measured value for this planning constant, 3/3 valid ADR-048 gate passes. Separately: **whole-node
64-thread G16 appears to cost ~2.45× the core-h of 16-thread packing for identical work** (single
anchor point, opt/freq unmeasured at 16 threads) — engineer9 wants one more ~24 core-h validation
before recommending anything plan-wide, approved to proceed with that check.
🔴 **Corrected 05_STATE.md's own P1-margin figure**: was reporting ~6,200× using a WALL-HOURS
number as if it were core-h — see the correction inline at P1's resize entry above (true margin
97×, decision unchanged).
Two coder12 items: `endpoint_prep_reactant_epsinf_full` (this round's most valuable result, a real
C-8 certificate) is completely ABSENT from `pilots[]` in the rollup despite being in `plan` and
`guard.reservations` — same "measured but unread" class, reporting side this time; `probe_qw_n64`
never returned (job dir exists, no execution record) — largest queue wait actually measured is 16
nodes at 56s, any 64-node scheduling assumption is unmeasured. Two more resize approvals: P6
(24h→2h cap, recovers ~1,782 core-h) and U56-2's endpoint certs (keep ~130 core-h/endpoint margin,
NOT tightened to the n=1 measurement since the only other endpoint attempt crashed — recovers
~760). **No failure rate available from this round** (n=1 endpoint success, not 100%) — nothing
should be planned assuming 100%.

---

## 1c. THE ACETONE SWITCH — current, active state (2026-08-21)

🟢 **User ruling, final**: production PCM deck is `scrf=(pcm,solvent=acetone,read)` + `eps=18.5`,
no explicit `EpsInf`. Landed by coder12 through the single C-5 decision point
(`solvent.resolve_solvent_deck`, everything routes through `qc_adapter.sh`) — covers P5, P1b, P6,
`endpoint_prep`, U56-2, SP ladder, verified end-to-end against the real deck generator. `eps_inf`
argument accepted and explicitly ignored (loud `_eps_inf_status`) so it can't quietly resurface.
Bracket code fully removed: no `SEI_QC_EPSINF`, no `epsinf_full` sibling item, no
`epsinf_bracket`/`collapsed` config, collector/README/provisional-certificate fields all cleaned
up. Round reserved: 9,515.39 → **9,131.39**.

🟢 **Root cause, confirmed (proposer8, §39.90) — kept, not cancelled with the bracket**:
`solvent=generic` was never a water fallback, it was a row of ALL ZEROS (RSolv, molar volume,
thermal expansion, density, Abraham descriptors, `EpsInf` — all 0). The freq/Hessian stage was the
only code path that ever consumed one of those zeros (`EpsInf`), which is why only freq crashed.
Checked whether the OTHER zeros were silently used anywhere: they are not (cavity comes from UFF
atomic radii × 1.100, no cavitation/dispersion/repulsion terms present) — **no prior B0 result
computed under `solvent=generic` was corrupted**, stated precisely as *"the zeros are inert for
THIS specific setup: electrostatics-only PCM on a scaled-VdW cavity"* — reopens if cavity type or
non-electrostatic terms ever change.

🟢 **First freq-containing route smoke, now permanent** (proposer8+engineer9's H2 test, built into
`qc_adapter.sh::sei_qc_smoke` by coder12): after the existing `sp` smoke, an H2 `freq` runs at both
levels automatically at the head of every payload — fails the smoke (payload stops before
production) on Error termination, records `NEqPCM:` lines, the `Solvent :` block, `n_frequencies`,
`epsinf_sentinel_seen` into `deck_verification.json.freq_smoke`. Closes the exact gap that let the
original crash through (§39.73(b): "a route smoke that doesn't exercise every stage isn't a route
smoke") — seconds of compute, zero added latency, runs on every future submission automatically.

🟢 **Endpoint re-certification, settled (~10.4 core-h, one job, two Link1 steps)**: the OLD
certificate (computed under `solvent=generic`/`EpsInf=18.5`) is SUPERSEDED, not final — different
deck shape (zeros vs acetone's real parameters), not equivalent. Re-cert ladder, read in order,
each rung consulted only if the previous is inconclusive: rung 1 freq-only on the stored geometry
(measures whether it's still stationary on the acetone surface — via same-quantity Cartesian-force
comparison against the ORIGINAL optimization's own forces, never a mismatched internal-coordinate
threshold — a real bug engineer9 caught that would have false-refused every certificate, and
~25% of P5's audit rows, by comparing two different force quantities); rung 2 (bundled into the
same job, +5.9 core-h) warm-started re-optimization on the acetone surface if rung 1 is
inconclusive; rung 3 (~42-66 core-h, NOT pre-run, surfaced as a finding not retried) only if a
covalent-graph basin check at rung 2 shows the structure moved to a different species. Warm start
preferred over cold on SCIENTIFIC grounds, not just cost: a cold restart from the packaged guess is
the option with a documented failure mode THIS SESSION (§39.89's nosymm/C-9 finding below), while
warm start preserves basin identity, which is what U56-2 actually needs. This item GATES
`u56_2.released` — schedule early, don't discover late.

🟢 **§39.89 finding, unrelated to EpsInf, survives the cancellation**: ALL 22 P5 decks are missing
`nosymm` (the endpoint deck has it) — same C-9/ADR-066 pathology that killed P1. One row caught
directly: `li_ec_radical_s0_L2` converged to a perfectly planar structure (0.0000 Å heavy-atom
deviation, Li-O-C angle exactly 180.00°) sitting on its own pre-registered falsifier. Fix: add
`nosymm`+`Int(Grid=UltraFine)` to P5 decks for FUTURE runs; do NOT re-optimize existing converged
geometries (would destroy the audit value) — instead, P5's freq-only recovery (already planned for
cost measurement) doubles as a free `n_imag` audit of every existing geometry, with the same
force-comparison fix applied per-row (validity flagged per row, not thrown out wholesale).
P5's converged geometries must not be reused as chemical structures by anything downstream until
this audit exists — a geometry is itself a chemical claim.

🟢 **Live cost sheet (engineer9, final as of this note)**:
```
smoke, now automatic on every payload    ~0.3 core-h   (folded into existing smoke stage)
endpoint re-cert, rungs 1+2, one job     ~10.4 core-h  GATES u56_2.released — schedule EARLY
  rung 3, only if basin check fails      ~42-66        NOT pre-run
16-thread packing validation             ~24           needs a payload change, optional
P5 freq-only recovery, 17 rows (of 22 attempted;
  5 non-recoverable rows are a separate,
  future optimization problem, not EpsInf)  ~92-152    doubles as the C-9 audit
──────────────────────────────────────────────────
whole remaining programme                 ~127-247 core-h  ≈ 1% of the 21,000 guard
```
Ceilings landed/pending: P6 wall 24h→2h (−1,782, LANDED), U56-2 11-atom endpoint certs 6h→3h
(−384, gated on `u56_2.released`), U56-2 21-atom cert UNCHANGED (no measurement exists at that
size, do not shave). **Round A recipe**: rebuild the package, then
`./run.sh --submit --rerun endpoint_prep_reactant` (add `--rerun P5 --rerun P1b` only if lifting
the P5 hold — their sentinel is gone with the acetone deck, but confirm before including).
`--rerun` archives old dirs to `jobs/<key>.reset.<epoch>`, never destroys. Do NOT `--rerun
endpoint_prep_reactant_epsinf_full` — no longer a plan item, its directory stays as historical
evidence only.

🟢 **Round A: RETURNED, PASSED (2026-08-21, real cluster).** User ran
`./run.sh --submit --rerun endpoint_prep_reactant` on the rebuilt package
(`a0b7da68f6be7b8d`) and brought back `sei_pilot_work/jobs/endpoint_prep_reactant/`. Verified
directly from the raw log, not from `terminal_status.json` alone: `endpoint_tight.gjf` carries
`nosymm ... scrf=(pcm,solvent=acetone,read) ... freq`, `endpoint_tight.log` shows all real
frequencies positive (lowest 77.0255 cm⁻¹) → n_imag=0, "Stationary point found", clean Normal
termination. `terminal_status.json`: `"status": "converged"`, note explicitly cites the C-8.2/C-8.3
certificate. `smoke_result.txt`: `smoke_eps_verification=ok (eps=18.5, ...)`. Cost: 64 cores ×
0.911h wall = **58.3 core-h** (inside the 384 core-h budget cap, inside the ~42-66 core-h rung-3
estimate). `state/endpoint_prep_reactant.done.json`: `outcome: converged`, `cause_class: success`,
`pkg_fingerprint` matches. Old (pre-fix) job dir preserved intact at
`jobs/endpoint_prep_reactant.reset.1787267829/` per the `--rerun` archive contract — nothing
destroyed. **U56-2's R-A endpoint prerequisite is now certified under the acetone deck.** Routed to
proposer9 (scientific cert sign-off), critic12 (independent re-verification from raw files), and
engineer10 (cost reconciliation against the live sheet below) — none of this note should be treated
as a substitute for their independent checks landing in `02_METHOD_SPEC.md`/`04_REVIEW_LOG.md`.

🔒 **Four durable rules from today's investigation, worth keeping regardless of the cancellation**:
a rule cited by NAME is not a rule applied — cite the criterion, not the verdict; a mechanism being
true doesn't make a criterion built on it well-formed; metadata describes a calculation, only the
structure describes a molecule; name the scaling variable, verify it moves as expected — and
verify the SET is uniform in it.

---

## 1d. U56-2 BATCH RETURNED (2026-08-21) — real TS candidates, real bugs, plan approved by user

The 5-item batch (§1c) came back. `endpoint_prep_product` and `endpoint_prep_rc_reactant` (E21)
certified cleanly (n_imag=0). The three TS-attempt items (`U56_RA_scan`, `U56_RA_qst2`,
`U56_RB_scan`) ran to completion (rc=0, real TS candidates produced with `ts_acceptance.json`,
`bracket_check.json`, etc.) but **misreported as `outcome: absent`** in `state/*.done.json` —
`payload/U56.sh` never writes a final `terminal_status.json` (bug, fix in progress).

🔴 **Real finding, user-led**: raw `.log` inspection (not the summary JSONs) shows `U56_RA_scan` and
`U56_RA_qst2`'s IRC both die the same way — deep in the Bulirsch-Stoer corrector integration,
`Delta-x Convergence NOT Met` → Gaussian's own clean `Error termination via Lnk1e` (a segfault
backtrace follows, but AFTER the clean exit — likely shutdown debris, not the cause). Root driver:
recurring `**** Warning!!: The largest beta/alpha MO coefficient` (should be O(1), seen at 32-39),
present even in the certified endpoints, growing across the IRC path (32.49→38.65). `U56_RB_scan`
shows the same warning but its IRC reaches clean `Normal termination` instead — separate question,
not yet explained.

🟢 **Basis-set question resolved and independently verified**: `wB97XD/gen` at `"level": "level3"`
(def2-SVPD) throughout this batch is CORRECT per C-11's ruling (`config/b0_reactions.json`) —
composite protocol, geometry/Hessian at level3/def2-SVPD, single-point refinement at level2/def2-
TZVPPD reserved for a later stage not yet run. `inputs/basis/def2-SVPD.gbs` and `def2-TZVPPD.gbs`
diffed byte-for-byte against a live fetch from basissetexchange.org (all 6 elements: H,Li,C,O,F,P) —
identical, genuine BSE exports, not hand-edited.

Full findings + approved next-step plan (Track A: coder fixes + a cheap `stable=opt` SCF-instability
diagnostic; Track B: proposer rulings on method disagreement, held until the diagnostic returns):
`/home/yanselmo/.claude/plans/linear-hopping-frog.md`. Team spawned: coder14 (Track A), critic14
(verification, opus — replaced critic13 same round, model switch), proposer10 (prepping Track B,
rulings held pending diagnostic data).

🔴 **Plan corrections from critic14's independent verification (04_REVIEW_LOG.md, 16차 배치) — the
§1d text above is now partly SUPERSEDED, kept for history**:
- **`U56_RB_scan`'s IRC is NOT `truncated`** — both `irc_completion_*.json` say `truncated: false`;
  it genuinely reached a PES minimum in both directions. `criteria/g16.py:401`'s string match
  ("Minimum found on this side of the path") doesn't match this G16 version's real output ("PES
  minimum detected on this side of the pathway") — a real parser bug, never checked against a real
  log before (every `minimum_found:True` in the test suite was a hand-built dict). Consequence:
  RB_scan was mis-tagged BUDGET-class and dropped from the chemical denominator; likely good news
  once fixed. Routed to coder14 to fix the string match.
- **cause_class ruling (lead, landed)**: `RA_scan`/`RA_qst2`'s error-terminated IRC (both directions,
  both attempts) gets **`cause_class: deterministic`**, not `engine` and not the payload's current
  default `success`. `deterministic` already exists in `outcome.py` as the highest-severity,
  never-retry class — this qualifies on the taxonomy's own terms (same deck, same deterministic G16
  algorithm, will fail identically on rerun) regardless of what proposer eventually rules about WHY.
  Chosen specifically to block a real cost trap critic14 found: tagging this `engine` would have
  auto-resubmitted RA_scan(336)+RA_qst2(113) = **449 core-h** for free on the next `pkg_fingerprint`
  change with nothing about the SCF/IRC actually fixed (`cli.py:628`'s retry-class auto-resubmit).
  🔴 **Addendum (critic14, adopted): this ruling had a real gap, now closed.** `state.
  SPEC_DIGEST_FIELDS` doesn't cover payload-script CONTENT, only its name — so once `payload/U56.sh`
  is actually fixed (e.g. `IRC(Recorrect=Never)`), the digest wouldn't change, the item would never
  legitimately go stale, and `./run.sh` would keep silently skipping it forever with a now-false
  "결정론적 입력 결함, 재시도 금지" message (same shape as the EpsInf-skip incident this project
  already hit once at a different layer). **Fix, routed to coder14**: put the IRC integrator settings
  on the U56 Item's `extra_env` (which IS covered by spec_digest) instead of hardcoding them in the
  payload body — changing them then legitimately staleness-triggers a re-arm through the existing
  path, no new design needed. Also on record: critic14 notes "same deck → same crash, forever" has
  never actually been verified by a rerun (the trailing segfault looks like Linda-shutdown debris,
  which CAN vary run-to-run; this project has one prior counterexample, a GFN2 job assumed
  deterministic that didn't reproduce 3/3) — treat as a working assumption, not a confirmed fact, in
  any future writeup.
- 🟢 **RULED, §39.114(1) (proposer10; renumbered from §39.111 — collided with proposer9's earlier
  same-day §39.110-112, fixed by critic14/proposer10, originals at those numbers are proposer9's and
  untouched; §39.113 is proposer10's separate preliminary TS read-out, not this)**: C-2 branch (b)
  gate moves from "why the IRC stopped" to "how far apart the B+ start
  points are." RA_scan forward (21 points, arc 6.83, B+ gap 3.41) stands as reported; reverse (6
  points, arc 1.71, B+ gap 1.02, still near the saddle) downgrades to `low_confidence` — not
  disqualifying alone, but not load-bearing alone either. No tuned threshold number yet (same
  discipline as §39.71), flagged as future work once more truncated-IRC cases exist. 🔴
  **Implementation requirement, not optional**: the downgrade must land in the SAME field
  `guards.py:200` actually reads for branch (b) (`bplus.get("agreement") is True`) — a sibling
  `confidence` field nobody reads would silently defeat this ruling (critic14 caught this before
  coder14 built it; same "measured but not read" shape as three prior bugs this project already
  found). Also: the arc-length counts above use G16's raw Point Number (saddle included); whichever
  parser feeds the gate (`parse_irc_path_frames`) excludes the saddle (20/5) — state whatever
  threshold eventually gets pinned in that parser's own counting convention, not this ruling's.
- 🟢 **RULED, §39.114(2) (renumbered from §39.111)**: Track A item 2 builds BOTH `stable=opt` and
  critic14's `IRC(Recorrect=Never)`/StepSize restart — different questions, neither substitutes for
  the other. `stable=opt` runs at TWO geometries (arc ~1.7, coefficient ~32; and arc ~6.83, the last
  point before the crash, coefficient ~38.7) to tell whether any instability is a broad back-half
  feature or terminal-region-specific. Cost/scheduling only becomes a lead/engineer call if budget later forces
  dropping one test — not forcing that now.
- 🔴 **RULED (lead)**: `deterministic`'s cost protection has a bypass — coder14's fix for
  §39.113(d) (declaring `SEI_U56_PRODUCT_ENDPOINT_KEY` on `U56_RA_scan` so the bracket check can run
  two-sided) is an `extra_env` change, and `extra_env` IS a `spec_digest` field — so it makes the item
  `stale` against the returned `state/U56_RA_scan.submitted.json`, and `cli.py`'s stale-branch runs
  BEFORE the cause_class check, never consulting `deterministic` at all. Next `./run.sh` would
  auto-resubmit the whole item (336 core-h, measured) to repeat a known crash (~74 core-h wasted
  before dying again). **Ruling: hold that `extra_env` change** (reverted for now) until the actual
  IRC fix (Recorrect=Never/StepSize, still being diagnosed) is ready — re-add both together so one
  eventual resubmit buys the bracket-check symmetry AND an actual fix, not a repeat of the same crash
  for zero new information. Costs nothing to wait.
- 🟢 **RULED, §39.115 (proposer10)**: a THIRD `stable=opt` target — `endpoint_prep_rc_reactant`'s
  (E21, 21-atom) tight-stage geometry. critic14 independently re-derived its beta-MO-coefficient
  values (71.0/67.0/78.9/71.3) — the largest magnitude anywhere in the returned tree, ~2× RA_scan's
  failing plateau, and it belongs to an ALREADY-CERTIFIED job (n_imag=0, C-8 passed), not a crashed
  one. **Flagged escalation-priority**: a positive result here isn't routine Track B batching — it
  would raise a live question about whether C-8's n_imag+normal-termination criteria are sufficient
  for this whole class of cation+open-shell system, touching R-C's already-relied-upon precondition.
  Cost explicitly NOT assumed cheap — engineer11 spawned specifically to price this one for real,
  since the S21/T21-se cube-law cost anchor was retracted earlier (§R39.41) and there's no valid
  21-atom unit cost to scale from.
- 🟢 **RULED, §39.116 (proposer10)**: `U56_RB_scan`'s "minimum found" IRC completion is NOT a real
  connection — critic14 flagged it tagged `budget` despite a clean self-declared stop (289s wall, no
  cap hit — factually wrong regardless of chemistry); proposer10 checked the actual geometry and
  found the declared saddle and the declared "minimum" one step later are essentially the SAME
  geometry (breaking C–O bond 4.1330→4.1339 Å), forces already tiny everywhere in the log — reads as
  G16's minimum-detection criterion firing trivially on an extremely flat region around R-B's soft
  (−84.3 cm⁻¹) mode, not a real distinct basin. **Excluded from both the `budget` and `CHEMICAL`
  sides of the U-56b 1/p denominator** until further work resolves what it actually shows. Tag name
  settled: `protocol` (not a new class — matches §39.68(3)'s existing definition, "says something
  about our procedure, not the chemistry or caps"; `unknown` rejected because it would lose the
  prescription for a systematic, fixable issue). critic14 independently re-verified the geometry
  finding with a rotation-invariant method (centroid-removed RMSD + full pairwise-distance set) —
  confirms it, tightened the number (max pairwise-distance change 0.0203 Å, not the looser figure
  first quoted).
- 🟢 **RULED, §39.117 (proposer10) — R-B's THIRD independent problem.** `bracket_check.json` shows
  the declared breaking bond is already fully severed AT the saddle: reactant 1.4317 Å → saddle
  4.1348 Å (+2.7 Å past the reactant, not a loose contact), Li's migration also already substantially
  complete (1.79 Å). This is the bracket check's own predicted blind spot (§39.65/66), confirmed
  live: the reactant-only one-sided check catches an UNDERSHOOT but structurally cannot catch this
  OVERSHOOT-past-product on the break side (no certified product exists for this arm) — same
  pathology CLASS as ADR-112/P1, on the opposite side of the gate's coverage. **R-B's candidate now
  has THREE independent legs against it** (Li-dominated mode / §39.116's non-distinct minimum /
  this overshoot), each from a different method — Track B item 6's lean strengthens further toward
  rejection, still formally held pending the SCF/integrator diagnostic. **Prioritization note, not a
  ruling**: the deferred product-side calibration for R-B (§1, previously listed as "cuttable if
  squeezed") just went from closing a theoretical gap to being the specific check that would have
  flagged this exact candidate — worth re-weighing against a real catch, not a hypothetical one, next
  time cost/scope gets discussed.

🟢 **Track A CLOSED (critic14, OK verdict, 2026-08-21).** Three rounds of build→verify closed every
finding. What this round actually caught, for the record: three defects that would have silently
changed results (an IRC minimum sentinel this G16 version never prints; an engine-class crash
recorded as a wall/budget kill; C-2 branch (b) opening on any truncation instead of B+ start-point
separation), two cost defects (a `deterministic`-marked item a payload-internal deck change could
never legitimately re-arm; a housekeeping env key that would have re-armed a 336 core-h resubmit
through the stale-spec door before the real fix existed), the missing SIGTERM trap that would have
reproduced `outcome: absent` at 3,072 core-h, and R-B's third independent problem (§39.117) found
entirely from data already on disk, no new spend.

🟢 **REBUILT AND INDEPENDENTLY VERIFIED (critic14, 24차 배치).** `package_fingerprint
a7b668127d052e33`, `source_digest 0fcb8c2bcb8f7bde`, 108 files. Extracted the actual tarball bytes
(not source) and confirmed `payload/U56.sh`/`guards.py`/`config/qc_levels.json`/`outcome.py`/
`criteria/g16.py`/`plan.py` all carry today's rulings in what would actually ship. Full suite 1685
tests, 0 failures — the 4 freeze signals cleared as expected. **Checked the auto-resubmit risk from
the fingerprint change itself**: enumerated all 39 done markers in the returned tree, **0 would
auto-resubmit** (36 `absent`, 3 `success`, neither a retry class); 4 `failed` markers do retry
(P1/P1_c1/P1_c2/probe_qw_capped, bounded, ~2-3 core-h, intended behaviour). Minor asymmetry noted, not
blocking: `absent` never retries from the `done` branch but does retry from the `failed` branch,
despite a comment claiming "same rule" — narrow blast radius (those same 4 items), not urgent.
**Current/live package: `a7b668127d052e33`.** Diagnostics (4 small `stable=opt`/restart jobs,
~1-55 core-h combined, priced by engineer11) are separate hand-submit decks, not part of this
package.

- ~~C-2 branch (b) is currently too permissive (routed to proposer10, unresolved)~~ SUPERSEDED above:
  as coded
  (`guards.py:200`), branch (b) opens on `completion.truncated` + B+ agreement alone —  `truncated`
  is also true for an engine crash, not just `maxpoints_reached` as §39.55(d)'s comment seems to
  intend. RA_scan's crashed-both-directions IRC still gets `bplus_forward/reverse.json:
  agreement:true`, so C-2 as coded would currently accept a crashed path as "connection established."
  Extra wrinkle: RA_scan reverse only reached 5 points before dying; its two B+ start points are only
  ~1.0 arc-length apart (close to the saddle), the exact separation risk §39.70(2) warned about, with
  no enforced minimum gap.
- Background for the two RULED items above — **the diagnostic hypothesis was contested before proposer10's ruling**:
  critic14 found real counter-evidence against "SCF instability causes the crash" — all 66 SCF cycles
  in the failing IRC actually converged, zero basis functions were rejected at G16's linear-dependence
  cutoff, the certified `endpoint_prep_product` log carries the SAME warning magnitude as RA's failing
  plateau (so the coefficient doesn't discriminate pass/fail), RB_scan terminates fine with the same
  warning at a much lower magnitude, and the coefficient plateaus rather than monotonically growing
  (correction to this doc's earlier "drifts upward" framing — it oscillates 32-38 then plateaus). The
  actual death-point diagnostics (55.7° angle between gradients, already-tiny forces, corrector
  delta-x 0.063 vs 0.010 threshold) look more like an IRC integrator/flat-valley issue than an
  electronic-structure one. critic14's counter-proposal: a checkpoint restart with `IRC(Recorrect=
  Never)` or a different `StepSize` may be a more direct test than the originally-planned `stable=opt`
  wavefunction check. coder14 is holding item 2's build until proposer10 rules on which diagnostic to
  build.

---

🔵 **SUPERSEDED IN PART by §1e (2026-08-22)**: everything above that reads "held pending the
SCF/integrator diagnostic" is now resolved or reassigned — the diagnostic returned partially,
ADR-115 falsified the wavefunction hypothesis, ADR-116 ruled Track B items 5 and 6, and item 7 was
never substantively gated on it. Kept unedited above as history.

---

## 1e. U56 DIAGNOSTICS — PARTIALLY RETURNED (2026-08-22). Two of four stages ran; the two that ran answered their question

PBS job 23731675, submitted by hand via the ad-hoc `submit_diagnostics.pbs` (NOT `payload/U56.sh`),
`select=1:ncpus=1:mpiprocs=1`, `walltime=02:00:00`, all four decks sequential in one job.
**Killed**: `=>> PBS: job killed: walltime 7244 exceeded limit 7200`.

| stage | what | outcome |
|---|---|---|
| 1 `1_point4_arc1.71` | R-A IRC forward, arc 1.70908, beta-MO coeff 33.38 | **Normal termination**, 30m49s / 1 core = 0.514 core-h. Wavefunction **STABLE**, lowest eigenvalue +0.1419360, `<S**2>` 0.7549 |
| 2 `2_point19_arc6.83` | R-A IRC forward, arc 6.83462 — last converged point before the crash, coeff 38.87 | **Normal termination**, 43m41s / 1 core = 0.728 core-h. Wavefunction **STABLE**, lowest eigenvalue +0.1842609, `<S**2>` 0.7546 |
| 3 `3_rc_reactant_21atom` | R-C reactant certificate (E21, 21-atom cation-radical), coeff 71-79, §39.115 escalation-priority | **KILLED mid-SCF at Cycle 8** of the *initial* SCF. No science result — SCF was converging normally (Cycle 7 DIIS error 1.19e-4, decreasing). Must re-run. |
| 4 `4_irc_recorrect_restart` | `irc=(restart,recorrect=never)` from `U56_RA_scan/irc_forward.chk` | **NEVER STARTED.** Deck and its `.chk` intact and uncorrupted. |

🟢 **ADR-115 — the wavefunction-instability hypothesis for R-A's IRC crash is FALSIFIED** on the
criterion each deck's own pre-submission `manifest.json` declared. `EigRej = -1` at every probed
geometry; spin contamination negligible. Convergent with critic14's zero-spend counter-evidence from
§1d. **Residual gap, stated not hidden**: arc 6.83 is the last *converged* point; the crash happens
~20 failed corrector sub-iterations later reaching for Point 21 (gradient angle 31° → 59°), and those
divergent trial geometries were not probed. 🔴 **CORRECTED by critic15**: the original claim that they
"were never converged to anything probeable" is **false** — `irc_forward.log:21790-30456` holds 20
complete `Input orientation:` blocks (last at `:30018`), each with a converged `SCF Done`, zero
convergence failures, and `tools/build_u56_ra_stability_probe.py` already parses this log. **The gap
is closable for ~0.7 core-h — an open option, not a requirement.** Also, `stable=opt` tests only
internal (same-reference) UHF-type instability — which is exactly what the criterion asked for.
🟢 **A loophole nobody had checked closes in ADR-115's favour**: the probes ran from a fresh guess and
could have found a different SCF solution than the IRC carried; they did not — probe vs IRC energies
agree to **2e-9 / 2.6e-8 Hartree**, same solution.
**Falsifying one hypothesis does not confirm the other** (§39.114(2)): the integrator hypothesis is
now the only one left with positive support and has **never been positively tested**. Do not cite
ADR-115 as if it confirmed the integrator explanation.

🟢 **MO-coefficient reading, adopted (§39.119)**: the recurring 32-39 / 71-79 coefficient warnings
read as a **diffuse-basis (def2-SVPD) representation artifact approaching but not crossing linear
dependence**, not a chemistry signal. `EigKep` shrinks with size (4.2-4.5e-5 at 173 basis functions →
1.06e-5 at 334). Falsifiers on record. **Does NOT change C-8's criteria** — well-supported at
11 atoms, unproven at 21, which is exactly stage 3's job.

🟢 **Route smoke, partial**: stages 1/2 terminating normally clears `stable=opt` from the decks'
`route_syntax_status: NEEDS VERIFICATION` **for the stage 1/2/3 route only**. Stage 4's
`irc=(restart,recorrect=never)` + `geom=check guess=read` route is **still unsmoked**.

🔴 **ADR-117 — the kill was a SUBMISSION failure, not a prediction failure.** §R39.78 (engineer11's
own pricing, on record beforehand) priced item 3 alone at 3-30 core-h, wrote "at 1 core: 3-30h wall",
and recommended 4-8 cores. The submitting script consulted none of it. Standing rule 6, recurring
"measured but not read" class. The *method* is validated: items 1+2 priced 0.8-4.8 core-h, measured
**1.242 core-h**. Item 3 revised to **~2.2-17 core-h [ESTIMATE]** (from 3-30) on a measured
~341 s/SCF-cycle rate; the 2-10× `stable=opt` multiplier is untouched — 8 pre-stability-test SCF
cycles carry zero signal on it.

### 🔴🔴🔴 U-56a IS OPEN — an earlier same-day closure claim is RETRACTED

ADR-116 originally noted U-56a as closed, keyed to `endpoint_prep_product`'s certification.
**Retracted the same day, before any downstream action**, caught by critic15 and re-verified by lead
against the primary sources. ADR-109 Decision 1 (`01_DECISION_LOG.md:9047`) defines U-56a as *"has
ONE TS **search** met all eight §39.39(b) conditions end to end"* — endpoint certification is
condition **1** of eight. **Condition 7** (`02_METHOD_SPEC.md:11519-11525`) requires the IRC to pass
C-2 in **both** directions by convergence OR `maxpoints`+B+. Measured: `irc_completion_forward.json`
and `irc_completion_reverse.json` both read `normal_termination: false`, `maxpoints_reached: false`,
`truncated: true` — **neither branch is satisfied**. `05_STATE.md:520`'s "prerequisite 1" wording,
and §2's "this is what actually closes U-56a", both meant *the last remaining prerequisite*, not the
whole gate. The harness agrees (`U56_RA_scan/u56_attempt.json`: the C-2 IRC verdict decides U-56a).

**Current true position**: `U56_RA_scan` is now the **sole surviving candidate** (ADR-116 items 5/6
rejected the other two). Condition 1 met, **condition 7 not met**.
- **Stage 4 DOES gate U-56a.**
- **Stage 4 alone is NOT sufficient** — the **reverse** arm is at `low_confidence` (§39.113(1),
  B+ start points only ~1.0 arc-length apart) and needs a longer or redone IRC to lift it. **This
  second requirement was invisible in every project document until this retraction.** It is not
  scheduled, not priced, and not built. Treat it as the next real planning item after stage 3/4.
- Error direction: a falsely-passed stage gate unblocking S3 production — not core-h. §39.32(g)
  closes with an explicit prohibition against exactly this, citing P1's 302 core-h that count in
  neither direction.
- **Lead's own failure, recorded not buried**: ratified a teammate's inference without reading
  ADR-109's text, one turn after citing engineer12 for the same "measured but not read" class.
  Standing rule 6 binds the lead's rulings too.

---

### Resubmit — DECIDED, awaiting user execution. Both stages MUST RUN.

Two **separate** PBS jobs, never re-bundled (§39.114(2): independent, non-substitutable hypotheses;
a shared wall budget is what just killed stage 4). They may run concurrently, no ordering needed.

- **stage 3**: 4 cores, `walltime=16:00:00`. Sized off the *original* 3-30 core-h ceiling, not the
  tightened figure — margin is not cut against an untested extrapolation past cycle 8.
  **Restart CLEAN, not from `stability_probe.chk`** — confirmed correct by critic15 for a better
  reason than file size: the SCF was at RMSDP 1.77e-4 against a 1e-8 target, so **there is no
  converged density to reuse at all.**
- **stage 4**: 1 core, `walltime=30:00:00`. Resubmit exactly as staged; its `.chk` was copied at
  deck-build time (`2026-08-21T11:44:37Z`) and the killed job never entered its directory.
- Both inside ADR-114's 48 h cap.

🔴🔴 **DEFECT IN §R39.79's SCRIPT SKELETON — caught by lead before submission. DO NOT SUBMIT IT
UNMODIFIED.** Both staged decks carry `%nprocshared=1` on line 1 (verified directly in
`3_rc_reactant_21atom/stability_probe.gjf` and `4_irc_recorrect_restart/irc_recorrect_probe.gjf`;
each `manifest.json` independently records `"nprocshared": 1`). In G16 an explicit `%nprocshared`
Link0 line **overrides** the `GAUSS_NPROCSHARED` env default the skeleton exports. As written, stage 3
would reserve 4 cores, run on 1, and blow through a 16 h wall sized for 4 cores against a ~30 h
1-core worst case — **the identical failure this ADR exists to prevent, one layer down.** Two
acceptable paths, user picks (ADR-117):
1. **Preferred**: copy the deck **FILES** (`.gjf` + `probe_point.xyz` + `manifest.json` only — NOT
   the directories) to a fresh **writable** dir outside `cpu_machine_pilot_results/`, set
   `%nprocshared=4` in stage 3's copy, submit from there. Stage 4's `.chk` is genuine input and must
   travel **byte-exact** (md5 `87a378633c55f4df0021f133943cfe97`). The returned tree stays untouched
   (standing restriction); record the copy path here when done.
2. **Zero-touch fallback**: submit stage 3 as staged at `ncpus=1` with `walltime=45:00:00` (inside
   the 48 h cap). Identical core-h, ~4× the wall-clock latency.

🔴 **FOUR CORRECTIONS from critic15 (`04_REVIEW_LOG.md` 25차 배치) — the recipe was NO-GO as first
written; all four are landed above and in ADR-117:**
- **Delete the `GAUSS_NPROCSHARED=4` export line** (do not merely comment it out). It is **not a G16
  variable at all** — G16 uses `GAUSS_PDEF`; `grep -rn "GAUSS_" src/ tools/` yields only
  `GAUSS_EXEDIR`/`GAUSS_SCRDIR`, and production sets cores in the deck (`irc_forward.gjf:1` =
  `%nprocshared=64`). Left in, it silently hands 1 core to whoever later trusts the env instead.
- **Fallback walltime 32 h → 45 h.** 32/30 = 1.07× margin where the primary got >2×.
- **Copy FILES, not directories** — a directory copy drags stage 3's stale mid-write `.chk` and
  ~155 MB scratch into the run dir, reintroducing the exact risk clean-restart avoids.
- **Mandatory post-run check on stage 4, before interpreting it**: grep the new log for
  `Recorrection delta-x convergence threshold:`. `irc=restart` may take its options from the
  checkpoint and **silently drop `recorrect=never`**; the run would then reproduce the identical
  crash and be misread as "the integrator hypothesis is dead too". If that line still appears, the
  option did not take effect and **the result carries no information.** Nobody had priced this branch.

🟢 **STAGED AND READY, 2026-08-22 — user chose path 1 (copy + 4 cores).** Run directory:
`u56_diagnostics_resubmit_2026-08-22/` (outside `cpu_machine_pilot_results/`; the returned tree was
read but **not modified** — verified after staging: its stage-3 deck still reads `%nprocshared=1`).
Contents: stage-3 `stability_probe.gjf` / `probe_point.xyz` / `manifest.json`; stage-4
`irc_recorrect_probe.gjf` / `manifest.json` / `irc_forward_recorrect_probe.chk` (copied byte-exact,
md5 `87a378633c55f4df0021f133943cfe97` re-verified after the copy); `submit_stage3.pbs`,
`submit_stage4.pbs`, `submit_probe5.pbs`, `README.md`. **Exactly one deck edit was made: stage 3's
`%nprocshared` 1 → 4.**
No `.chk` and no `Gau-*` scratch were copied into stage 3. Both scripts pass `sh -n`; neither
contains any `GAUSS_*` assignment or export. Submit with `qsub submit_stage3.pbs`,
`qsub submit_stage4.pbs` and `qsub submit_probe5.pbs` — three separate jobs, never bundled. `README.md` in that directory carries the
before/after checklist, including the mandatory `Recorrection delta-x convergence threshold:` grep on
stage 4 and the neutral-doublet scope caveat on stage 3.
🟢 **PROBE 5 ADDED to this round, 2026-08-22, user-approved — it closes ADR-115's residual gap.**
`5_ra_crash_geometry/` was **generated**, not copied, by the project's existing
`tools/build_u56_ra_stability_probe.py` in `--geom-log` mode against
`U56_RA_scan/irc_forward.log`, with **no code changes**. That mode takes the log's LAST geometry —
the `Input orientation:` block at `:30018`, the final corrector trial geometry before the IRC gave
up, 456 lines before the error termination at `:30457`. This is the true crash geometry that stages
1/2 could not reach. Verified: 11 atoms, and **different** from the arc-6.83 probe's geometry (an
identical one would have made the probe worthless). 1 core, `walltime=06:00:00`, ~0.7 core-h
[ESTIMATE] against stages 1/2's measured 0.514 / 0.728 core-h on the same system — ~8× wall margin.
🔴 **Provenance caveat**: the builder's `--geom-log` mode hardcodes
`"source_kind": "certified_geometry_log"` in the manifest. **This geometry is NOT certified** — it is
a crash-region trial geometry from an error-terminated job. Tool limitation, deliberately left
unedited (a tool fix is a code change this round does not need). Its
`mo_coefficient_warnings_first_last` likewise spans the whole log (lines 745 → 30364, 132 warnings),
not the crash region; the value nearest this geometry is beta 38.6541 at `:30364`.
**Reading it**: STABLE completes ADR-115's falsification through the actual failure point. UNSTABLE
would confine the instability to the region stages 1/2 could not see, **partly reopening ADR-115**
and making stage 4 much harder to interpret alone.

🔴 **User must check cluster scratch quota before submitting** — the compute node's `$GAUSS_SCRDIR`
cannot be inspected from the workstation, and the previous SIGKILL left ~155 MB orphaned in the
returned tree alone. Nothing deleted; that remains the user's call.
🔴 **`./run.sh --submit` stays forbidden for these decks.**

🟢 **Verified OK by critic15, no action**: 16 h/4 cores and 30 h/1 core both safely margined
(≈1.05 core-h/point re-derived; ≤10 points ≈ 11 core-h; a repeat crash costs the measured 13.4
core-h and still fits). `%mem=4GB` adequate — stage 3 ran 8 cycles at 334 basis functions with
`.int`/`.d2e` at **0 bytes** (fully direct, no spill). Recipe is **CLEAR** of the
`plan.py`/`spec_digest`/`cause_class` stale-branch trap — it invokes no `sei_pilot` entry point.
ADR-104/106/108 clear: all three probe logs report `Eps= 18.500000`, identical to production.

🟢 **Stay hand-submitted; do NOT move to `payload/U56.sh`** (ADR-117). Today's root cause was never a
payload limitation, and wiring these in as real Items would add surface to the `extra_env`/
`spec_digest` stale-resubmit path §1d fenced off — the one that runs *before* the `cause_class` check
and could auto-fire `U56_RA_scan`'s measured 336 core-h to repeat a known crash. Harden the ad-hoc
script instead: one stage per job, plus `trap ... TERM` writing a kill marker. That trap is
**best-effort, `[ASSUMPTION]`-flagged** — this site's PBS SIGTERM grace window is unconfirmed.

**Scratch — flagged, NOT deleted** (standing restriction; user's call): stage 3's directory holds
~155 MB of orphaned SCF scratch (157,253,632 B `Gau-53946.rwf` + `.d2e`/`.int`/`.skr`/`.inp`); the
whole diagnostics tree is ~176 MB. This covers only the **returned** copy — the compute-node
`$GAUSS_SCRDIR` cannot be checked from here and a SIGKILL commonly orphans scratch there too. Check
cluster scratch quota before resubmitting.

**Budget**: no `deck_verification.json` exists for these ad-hoc decks — checked, correct by design
(hand-submitted decks bypass the harness), so ADR-108's reading rule has no input here. Consumed
**~2.01 core-h measured**; pessimistic resubmit ceiling ~50 core-h. Guard 12,709.39 / 21,000 (60.5%)
→ at most ~12,761 / 21,000 (60.8%). Not meaningful.

### RESUBMIT RETURNED, 2026-08-25 — all three jobs clean, no kill. Facts only, lead has NOT ruled on
### what this means for ADR-115/U-56a condition 7/R-9 sequencing — that is proposer's call.

User scp'd `u56_diagnostics_resubmit_2026-08-22/` back complete (submitted 2026-08-24, per PBS
`.o*` timestamps). **All three PBS jobs**: `rc=0`, `Normal termination of Gaussian 16`, **no
`*_kill.marker` file in any of the three subdirs** — first clean full return this diagnostics round.

| job | PBS id | cpu/elapsed | vs walltime cap | headline (facts, not verdict) |
|---|---|---|---|---|
| stage3 (`3_rc_reactant_21atom`) | 23749146 | 6h45m03s / 1h41m18s (4 cores) | 16:00:00 cap, ~10.6% used | `stability_probe.log:1457`: **"The wavefunction is stable under the perturbations considered."** — the 21-atom R-C reactant cert, `[MEASURED]`. |
| stage4 (`4_irc_recorrect_restart`) | 23749148 | 8m13s / 8m12s (1 core) | 30:00:00 cap, ~0.5% used | Mandatory sanity check (§1e recipe step 6) run: `grep -ac "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log` → **0** — the silent-drop failure mode did NOT occur; restored-checkpoint route echo confirms `Redo corrector integration= Never`. Restart resumed at **Point 21** (`NET REACTION COORDINATE = 7.17521`, consistent with forward's pre-crash n=20), reached **Point 22** (arc 7.73821 in the summary table — table shows a 23rd row at the same arc value while `Total number of points: 22` is also printed; this discrepancy is unexplained by the lead, flagged not resolved), then: `"Maximum number of steps reached. Calculation of FORWARD path complete."` **NOT `maxpoints=30`'s ceiling** (only 22 of 30 points used) and **not a "PES minimum detected" phrase either** — full text is exactly `"Maximum number of steps reached."`, `[NEEDS VERIFICATION]` what G16 cap this refers to and whether it constitutes the categorically-stronger PES-minimum evidence proposer12's §1f ruling 1 was betting maxpoints=30 on, or something weaker. **This is the load-bearing read for whether the integrator hypothesis is now positively supported** — lead is explicitly NOT ruling on it. |
| probe5 (`5_ra_crash_geometry`) | 23749118 | 43m49s / 43m49s (1 core) | 06:00:00 cap, ~12.2% used | `stability_probe.log:1034`: **"The wavefunction is stable under the perturbations considered."** — at the **actual crash geometry** (`irc_forward.log:30018`'s last Input orientation), the exact residual gap ADR-115 named as unprobed. `[MEASURED]`. |

**Scratch**: not re-checked by the lead this pass — `.chk`/`.rwf` sizes look consistent with prior
runs (`stability_probe.chk` 19,099,648 B stage3 / 5,869,568 B probe5), nothing flagged as orphaned in
the returned tree. Compute-node `$GAUSS_SCRDIR` still unverified (same caveat as before).

🟢 **RULED, 2026-08-25** (`proposer13`, §39.125 in `02_METHOD_SPEC.md`):
1. Probe5 **closes ADR-115's residual gap in substance** (bracketing only — only the last of ~20
   divergent trial geometries was probed, not all; energy vs `irc_forward.log:30347` agrees to 1e-9
   Hartree, same SCF solution, independently closing the "different basin" loophole for probe5 too).
2. Stage4's `"Maximum number of steps reached"` is **genuine positive evidence for the integrator
   hypothesis** — Point 21 (arc 7.17521, gradient angle 55.7°, inside the shared 51.8-59.4° failure
   band that killed both original arms) converged in ONE pass with zero corrector failures, where the
   original died over ~20 failed sub-iterations. Verdict: **positive, targeted, but incomplete**
   support — not confirmed, not ambiguous. The run stopping 2 points early (22/30, not the ceiling, not
   a literal PES-minimum message) reads as a **tool-vintage artifact**: this exact deck predates the
   2026-08-22 fix that made `maxpoints` explicit in the restart route, so it ran on
   checkpoint-inherited `maxpoints=30` that was printed but apparently not binding on this
   invocation's step count — `[NEEDS VERIFICATION]`, no G16 install to confirm the mechanism. New
   unpriced caveat: Point 22's step size jumped 65% vs the established ~0.34 rate — possible
   `recorrect=never` accuracy tradeoff, `[NEEDS VERIFICATION]`. (The earlier "23 rows vs 22 points"
   discrepancy the lead flagged is resolved, not a bug: row 1 is the saddle at arc 0.0, rows 2-23 are
   the 22 real points, matching the existing saddle-excluded convention.)
3. **R-9's stage-4-first sequencing rule (§39.124(4)) resolves to PROCEED to candidate A** — stage 4
   hit the "succeeds" branch cleanly (zero repeats of the shared failure signature). The rule is now
   discharged as a wait-gate (its job was to decide before/after seeing stage4; that decision is made)
   but stays on record as methodology. Flagged for whoever builds candidate A: since candidate A would
   build from the **current** `src/` (post-fix, `maxpoints=30` written explicitly), its run may reach a
   more conclusive stop than stage4 did — **confirm the built `.gjf`'s route states `maxpoints=30`
   explicitly before submitting, don't assume it inherited correctly.**

`[UNRESOLVED]`: the G16 mechanism behind stage4's early stop; the step-22 step-size anomaly's cause;
the ~19 unprobed intermediate trial geometries (closed by bracketing only, not exhaustively).

🟢 **DONE, 2026-08-25**: candidate A staged at `candidate_a_reverse_2026-08-25/` (project root),
NOT submitted. `coder16` built it (`--direction reverse --total-cores 64`, fresh out-dir); `critic17`'s
30th batch found one BLOCKER (README's mandatory post-run check was missing `-a` — same binary-file
grep trap as above, meaning the check could not fail either way) plus a miscited line range in the pbs
comment, both fixed and independently re-verified (md5, maxpoints=30 explicit, 64 cores in gjf+pbs,
walltime math re-derived from the reaction's own measured rate). Bundled as
`candidate_a_reverse_2026-08-25.tar.gz` for the user to scp+qsub, same pattern as the original
resubmit. critic17's 31st batch: **OK, SUBMIT-READY** — re-verified both fixes against the files
(not the report), payload (gjf/chk/manifest) untouched by the doc-only fix, and independently
re-hashed the actual tarball's contents against disk (all 5 files identical, checkpoint still
`7b4557b0...`) — the archive that gets scp'd is confirmed to carry the fixed files.

### CANDIDATE A RETURNED, 2026-08-25 — clean, fast, and a genuine G16 minimum call. Facts only, NOT
### ruled — this bears directly on proposer12's own `>=4.27` acceptance floor (§39.124(3)) and needs
### proposer13 (or whoever picks it up) to read it, not the lead.

User scp'd `candidate_a_reverse_2026-08-25/` back with the run's output added. PBS job 23757537:
`rc=0`, no kill marker, **65 seconds** wall (`start 02:29:47Z` → `end 02:30:54Z`) — vastly under the
8h cap and the ~46-87 core-h / 0.72-1.36h estimate (that estimate assumed running most of the way to
`maxpoints=30`; this run stopped almost immediately). Mandatory sanity check
(`grep -ac "Recorrection delta-x convergence threshold:" irc_recorrect_probe.log`) → **0** —
`recorrect=never` took effect, not silently dropped.

The IRC restart resumed at the stored **Point 6** (`NET REACTION COORDINATE = 2.00908`), took **one**
new step to **Point 7** (`NET REACTION COORDINATE = 2.12546`, gradient magnitude `0.0000445`), and hit:

```
PES minimum detected on this side of the pathway.
Calculation of REVERSE path complete.
Reaction path calculation complete.
```

This is the **literal "PES minimum detected" message** — the categorically-strong evidence class
proposer12's original `maxpoints=30` ruling (§1f ruling 1) was betting on, distinct from stage4's
ambiguous "Maximum number of steps reached" (§39.125(2)). Total 7 points, 32 gradient calcs, 1 Hessian
calc — nowhere near the 30-point ceiling.

🔴 **The number that needs a ruling, not a lead guess**: total arc-length reached is **2.12546** —
**below** proposer12's own `arc_length_reached_reverse_new >= 4.27` acceptance floor (§39.124(3), an
`[ESTIMATE]` set as the arithmetic midpoint of an insufficient case at 1.71 and a sufficient case at
6.83). critic16's 26th-batch review of that floor explicitly asked "is its stated review trigger
concrete enough to actually fire later" — this may be exactly that trigger. Two readings the lead is
declining to pick between: (a) proposer12's own stated reasoning was that a genuine G16-declared
minimum is *categorically stronger* than clearing the arc floor, in which case this passes outright
and the floor was only ever a fallback for an ambiguous stop; or (b) a minimum this close to the
restart point (only 0.116 Å-scale arc beyond the already-stored Point 6) is short enough to raise the
same "can't distinguish real minimum from a flat/artifact stop" concern finding (b) raised elsewhere
in R-9 — worth cross-checking against the actual PES shape, not just the declared message, before
treating condition 7's reverse branch as satisfied.

🔴 **RULED, 2026-08-25** (`proposer13`, §39.126): **condition 7's reverse branch is NOT satisfied —
clean fail, not a coin flip.** Re-derived Ruling 3's distinctness test directly (max pairwise
interatomic-distance change, Point 6 vs Point 7, all 55 atom pairs): **0.0121 Å — below even the
confirmed `RB_scan` artifact anchor (0.0203-0.0228 Å)**. So branch (a) (declared-minimum-outranks-
floor) fails on its own distinctness conjunct, falling to branch (b), which independently fails both
clauses (n_frames=7<10, arc=2.12546<4.27). **The decisive new fact**: only **ONE** `SCF Done` in the
whole log, at Point 6 — **no fresh ab initio evaluation ever ran at Point 7's own geometry.** The
"minimum detected" call and its `0.0000445` gradient both come from a Bulirsch-Stoer/DWI corrector fit
that the log itself flags one line earlier: `"WARNING: Bulirsch-Stoer Method is not Converging"` (11
cycles/1536 steps, 5e-5 truncation error still present). **The apparent minimum is an artifact of an
unconverged corrector fit, not an independently-verified electronic-structure result.**

- **The `>=4.27` floor is untouched** — this case fails on `n_frames<10` regardless of the floor's
  value, so it isn't the calibration test critic16 flagged; that trigger is still pending.
- **R-9 does NOT need reopening** — the acceptance criterion caught this cleanly on its first real
  test against ambiguous data; a correct reject, not a defect.
- **New candidate mechanism for Track B item 7**: this is a second, distinct artifact-producing
  mechanism (corrector non-convergence) alongside `RB_scan`'s soft-mode flatness — both produce the
  same "looks like a minimum, isn't" shape from different causes.
**U-56a condition 7 (reverse branch) stays OPEN.**

🟢 **CANDIDATE B FULLY SPECIFIED AND PRICED, 2026-08-25** (`proposer13` §39.127 + `engineer14` §R39.82/83,
converged in 2 round trips, no lead adjudication needed):

- **`StepSize`, not `EulerPC`** — §39.126's finding (Point 7's corrector force-contracted to 34% of
  nominal step over 11 BS cycles before giving up) is a step-too-large-for-local-curvature signature,
  not an algorithm-family problem. `EulerPC` reserved as escalation only if `StepSize` also fails.
- **`f=0.25`** (fraction of the nominal 0.342 sqrt(amu)·bohr step) — chosen because it sits below the
  corrector's own measured natural contraction scale (0.116/0.336 ≈ 0.35); `f=0.5` doesn't clear that
  bar, `f=0.1` isn't motivated by anything measured and roughly doubles cost for no gain.
- **`recorrect=never` carried forward**, amending the original §1f menu (which predates knowing
  `recorrect=never` works) — a pure default-recorrection test would just re-hit the already-solved
  arc-1.7-2.0 failure before ever reaching the new arc-2.1 problem `f=0.25` targets.
- **Route**: `irc=(calcfc,reverse,recorrect=never,stepsize=<f×0.342 converted to whatever unit the G16
  `stepsize=` keyword takes>,maxpoints=55)` — **`stepsize=` value is NOT a number yet, it needs correct
  unit conversion**, and **`maxpoints` MUST be ≥55 explicit** (at f=0.25 the arc/frame rate is ~0.0854,
  needing ~50 points to clear the arc≥4.27 floor — the project's usual default of 30 would silently
  truncate this run before it could ever succeed, the third near-miss of this exact failure class on
  this one work item per critic16/critic17/engineer14).
- **`--total-cores 64` explicit, no default** — same ADR-114 wall-cap requirement as candidate A.
- **Mandatory post-run check**: read the log specifically at the point(s) landing near arc 2.0-2.3 (not
  just the final summary table) — the exact region candidate A's f=1.0 attempt broke down in. A clean
  single-pass corrector step there is the real positive signal; a repeat "Bulirsch-Stoer... not
  Converging" warning at the smaller step means escalate to `EulerPC` or a finer `f`, not declare
  success.
- **Optional 1-2 point route-syntax smoke** endorsed (near-zero cost) but explicitly cannot validate the
  hypothesis itself (never reaches arc 2.0-2.3) — insurance against a malformed keyword string only.
- **Cost** (`engineer14` §R39.83): **99.8-188.8 core-h** one attempt, **199.6-377.6 core-h** worst case
  with one retry — 1.2-4.6% of the ~8,238 core-h margin, not binding. Wall **1.6-2.9h** (retry
  3.1-5.9h), trivially inside ADR-114's 48h cap. ADR-117-class risk rated MODERATE (unsmoked route
  combination) but **no silent-override mechanism exists this time** — a from-scratch redo has no
  checkpoint to silently inherit stale options from, unlike candidate A/stage4.
- **No builder tool exists yet** for a from-scratch IRC redo (the existing tool is restart-only, reads
  `geom=check guess=read` from a `.chk` — Candidate B needs a fresh IRC from the certified TS geometry
  instead). **This is real new code**, flagged to `coder16` next.
- Ruled unchanged, answered directly by proposer13: the `arc≥4.27`/`n_frames≥10` acceptance floor
  applies to Candidate B exactly as it did to candidate A — mechanism-agnostic by design.

🔴 **CORRECTED, 2026-08-25** (`proposer13` §39.128): G16's `StepSize` keyword is integer-only, so the
ruled `f=0.25` (`stepsize=2.5`) isn't buildable as written. `coder16`'s first build rounded UP to
`stepsize=3` (`f=0.30`, kept `maxpoints=55` fixed) — **superseded, do not use.** proposer13 ruled
**`stepsize=2` (`f=0.20`), `maxpoints=70`** instead: the `f=0.25` criterion was never "hit 0.25
exactly," it was "stay below the ~0.35 measured natural contraction scale, taking the free margin
since cost is non-binding" — `f=0.20` leaves 3x the safety margin `f=0.30` does (0.15 vs 0.05 below
0.35), and `maxpoints` was always the free/padded number, not a real constraint, so raise it (`~62.5`
points needed at `f=0.20`, `+10%` margin → `70`) rather than spend the margin on the physically
measured quantity. Cost re-derived from first principles by `engineer14` (§R39.84, not just scaled): 63 points needed
(`4.27/(0.3415×0.20)=62.5`), `maxpoints=70` gives 11.1% padding. **Confirmed: 121.0-228.7 core-h
targeted (63 pts), 134.4-254.1 core-h ceiling (70 pts, use as the deck's budget line)** — matches
proposer13's extrapolation almost exactly (linear-in-points math, so scaling and direct recompute
agree). Wall 1.9-3.6h targeted / 2.1-4.0h ceiling at 64 cores, >12x margin under ADR-114's 48h cap
even pessimistic. Guard impact 6.2% of margin worst case w/ retry — not binding. engineer14 also
caught and fixed a 4% slip in its own §R39.82/83 (said "~52 pts" for f=0.25, formula gives 50) —
doesn't affect anything already scheduled, superseded regardless.

🟢 **DONE, 2026-08-25**: rebuilt against `stepsize=2`/`maxpoints=70`. `critic17`'s 32nd batch initially
BLOCKed on a stale-vs-ruling mismatch (crossed with the rebuild) plus three real nits — wrong `StepSize`
unit label (corrected to "0.01 Cartesian bohr/step", not mass-weighted — this reaction's own log shows
`Step size = 0.100 bohr` route-echoed separately from `Integration on MW PES will use step size of
0.3421 sqrt(amu)*bohr`, the actual mass-weighted conversion); a stepsize-honoured check added to README
(route-echo grep alone can't distinguish honoured from parsed-and-ignored); the `Recorrection delta-x`
mandatory check restored (dropped by mistake even though this route also carries `recorrect=never`
forward). All fixed; 33rd batch: **OK, BLOCK lifted** — critic17 independently rebuilt from `src/` and
confirmed the staged deck is byte-identical to a fresh build (not hand-patched to look right). Bundled
as `candidate_b_reverse_stepsize_2026-08-25.tar.gz`. **Not yet run** — awaiting the user.

🟢 **EULERPC ESCALATION SPECIFIED AND PRICED, 2026-08-25** (`proposer13` §39.129 + `engineer14` §R39.85,
one round trip) — **user-requested staging alongside Candidate B** (one cluster round-trip), NOT a
promotion: StepSize still runs and is read first.

- **Route**: `irc=(calcfc,reverse,EulerPC,recorrect=never,stepsize=2,maxpoints=100)` — fresh from the
  certified TS, same as B. `recorrect=never` confirmed valid for EulerPC against Gaussian's own IRC
  keyword page (fetched, quoted, not recalled); `stepsize=2` kept identical to B deliberately so a
  pass/fail is attributable to the predictor swap alone (single-variable change).
- 🔴 **Material correction to §39.127's framing** (proposer13, sourced to gaussian.com/irc/): **EulerPC
  is NOT a fully different integrator — it swaps only the predictor and feeds the SAME Bulirsch-
  Stoer/DWI corrector that failed at Candidate A's Point 7.** If the pathology is corrector-side (the
  observed symptoms are), EulerPC is a *weaker* second bet than §39.127 implied — could even stress the
  shared corrector more (cruder predictor → more corrector work). Staged anyway per the user's
  logistics call; expectation calibrated down, sequencing unchanged.
- **`maxpoints=100`** — ~60% above the nominal-rate minimum (~62.5 pts), a deliberately wider hedge
  than B's 10% because EulerPC's realized arc-per-point is doubly unmeasured (`[ESTIMATE]`).
- **Cost** (§R39.85): 121.0-459.9 core-h targeted / **192.0-730.0 core-h ceiling** (deck budget line);
  pessimistic per-point tail widened to 7.3 core-h/pt (explicit 2x judgment call, unanchored — the
  shared-corrector finding cuts both ways on cost). Wall **3.0-11.3h at ceiling — ~4.2x margin under
  ADR-114's 48h cap, the narrowest on this work item** (everything else >12x); worst case smoke+2
  retries ~22.7h, ~2.1x. Combined worst case with B: ~12.1% of remaining guard margin, not binding.
- **Smoke endorsed for THIS tier** (unlike B): the keyword combination itself is unverified; 1-2 point
  smoke at 1.9-14.6 core-h before the full run.
- 🔴 **New foot-gun class named (4th "silently didn't get what was requested" flavor)**: a malformed
  `EulerPC` keyword could silently fall back to G16's default HPC. Mandatory post-run check: grep the
  log for an actual Euler-predictor echo, not just rc=0. Plus the standing checks (Recorrection
  delta-x grep, arc-2.0-2.3 direct read, and — new for this tier — whether the BS non-convergence
  warning recurs, the direct test of the shared-corrector finding).
- **Third tier named, not specced: `DVV` (Damped Velocity Verlet)** — per the same doc fetch, a
  genuinely different integration scheme from both HPC and EulerPC (what §39.127 thought EulerPC was).
  Two `[NEEDS VERIFICATION]` caveats: calcfc-compatibility, and whether `recorrect` is even a live
  concept for it. Unpriced; staging it alongside is a lead/user logistics decision.
- critic17 asked (by proposer13) to independently verify the gaussian.com/irc/ quotes before this is
  treated as settled.

🟢 **DVV THIRD TIER SPECIFIED AND PRICED, 2026-08-25** (`proposer13` §39.130 + `engineer14` §R39.86 —
completing the user-requested all-tiers bundle):
- **Route ladder** (smoke decides the rung, on-cluster, no extra round trip): preferred
  `irc=(calcfc,reverse,DVV,stepsize=2,maxpoints=100)`; if the smoke errors on the Hessian combination,
  drop `calcfc`; if that also errors, add `GradientOnly` — flagged scientifically undesirable (discards
  available Hessians), a second-look item before spending its ceiling, not an automatic fallback.
- **`recorrect=never` OMITTED for DVV** — documented default is already Never for non-HPC/EulerPC
  integrators, and DVV likely has no corrector-step concept to control.
- **Cost** (§R39.86): **100.0-1090.0 core-h ceiling, ceiling-only, no targeted figure** — deliberate:
  two compounding unmeasured axes (genuinely different machinery, no step-count guarantee). Smoke
  widened to 2-3 points (tests whether `stepsize=2` even means anything under DVV's adaptive control,
  not just syntax). Rung-3 caveat: if `GradientOnly` becomes necessary, treat 10.9 core-h/pt as a floor
  and re-smoke — don't reuse rung 1's smoke result.
- **Combined worst case, all three tiers to ceiling** (unlikely sequencing): ~426-2,074 core-h +
  smokes, ~25% of remaining guard margin — clear, arithmetic shown in §R39.86.
- All three tiers (B/StepSize → EulerPC → DVV) now specified and priced; build routed to `coder16`.

🟢 **THREE-TIER BUNDLE BUILT, REVIEWED, TARRED — 2026-08-25.** `coder16` built two new sibling tools
(`build_u56_ra_irc_eulerpc_probe.py`, `build_u56_ra_irc_dvv_probe.py`; +19 tests, suite 1766 with the
same 3 known failures) and staged `candidate_b2_eulerpc_2026-08-25/` (smoke+full decks) and
`candidate_b3_dvv_2026-08-25/` (all 6 rung×smoke/full decks pre-built so nobody hand-edits a route
string on the cluster), plus a top-level `README_BUNDLE.md` (submission ladder, per-tier failure
definitions, smoke-first policy). `critic17`'s 34th batch: **OK** — all 8 deck routes byte-identical to
fresh rebuilds, all cost/wall margins re-derived and reproducing, gaussian.com/irc/ quotes
independently re-fetched (two verbatim-confirmed; one misattribution caught: "DVV is the GradientOnly
default" was EulerPC's line — corrected in §39.130 by proposer13 and in the tool comment by coder16,
and it SHARPENS the rung-3 caveat: GradientOnly's own default is EulerPC, so rung 3 is exactly where a
dropped `DVV` keyword silently runs the avoided corrector at rc=0; checks 1/2 made explicitly
non-optional at rung 3). Two further user-facing fixes landed post-review (the vacuous-if-zero-points
clause on tier 2's Check 1; rung-3 emphasis). Bundle: **`sei_reverse_arm_bundle_2026-08-25.tar.gz`**
(README_BUNDLE.md + all three tier dirs, 34 files). **Not yet run** — awaiting the user; submission
order B → (fail) → EulerPC smoke → full → (fail) → DVV ladder.
🔵 **Relocated 2026-08-25 (user request)**: all staging dirs, tarballs and `README_BUNDLE.md` moved
from the project root into **`pilot_tests/`** — every root-relative path in §1e/§1f above now reads
`pilot_tests/<same name>`. Tar contents unaffected (relative paths); tool tests re-run after the move,
37/37 OK.

### CANDIDATE B RETURNED, 2026-08-25 — ran the FULL 70-point ceiling, cleared the arc floor, ZERO
### corrector warnings. Facts only, lead has NOT ruled — routed to proposer13.

PBS 23758798: `rc=0`, Normal termination, no kill marker, ~56 min wall (05:22:53Z→06:18:35Z) vs 14h
cap. All mandatory checks pass:
- Stepsize honoured: banner reads `Step size = 0.020 bohr` / `Integration on MW PES will use step
  size of 0.0684 sqrt(amu)*bohr` — exactly the ruled f=0.20 values, not the default.
- `grep -ac "Recorrection delta-x convergence threshold:"` → **0** (`recorrect=never` took effect).
- **`WARNING: Bulirsch-Stoer Method is not Converging` appears ZERO times in the whole log** — the
  arc-2.0-2.3 region where candidate A's f=1.0 attempt broke down was passed cleanly (70/70 points,
  no corrector complaint anywhere).
- Termination: **`Maximum number of steps reached`** at exactly **70 points** (the `maxpoints=70`
  ceiling), **arc reached 4.77975 ≥ the 4.27 floor**, n_frames=70 ≥ 10. NOT a declared PES minimum —
  a ceiling-truncated walk, energy still (slowly) descending at the far end (-0.02594 at arc 4.78,
  ~0.4-0.5 mHa/point tail slope by the summary table).

🟢 **RULED, 2026-08-25** (`proposer13` §39.131, full-log re-derivation):
1. **StepSize hypothesis CONFIRMED** — direct positive evidence, not absence-of-evidence: every one
   of the 70 points (including the arc-2.0-2.3 region that killed f=1.0 twice) converged in 2-3 BS
   cycles with predictor/corrector agreement ≥97.98%, the tightest measured anywhere in this project.
2. **Condition 7 branch (b)**: n_frames=70✓, arc 4.78✓ (0.51 margin); third conjunct (B+ agreement)
   unmeasured. B+ points derived from `guards.bplus_sample_points()`'s own algorithm: **mid=Point 35
   (arc 2.38953), last=Point 70 (arc 4.77975)**. **Two jobs needed**: loose opts from Points 35 and
   70 (same route family as the original `bplus_reverse_mid/last`), then compute `bplus.agreement` +
   `reactant_match(last)` at 0.05 Å — reactant_match is part of branch (b)'s AND-block per Ruling 2,
   reuses the Point-70 job, no third job.
3. **Wandering guard passed**: energy strictly monotonic across all 71 rows (tail slope ~19x flatter
   than near-TS — basin-approach shape); the rotation-invariant Ruling-3 distance metric to the
   certified reactant shrinks monotonically (0.616→0.487→0.305 Å at points 30/50/70). The known-
   unreliable break-bond proxy wiggles (1.4279→1.4324 Å), consistent with critic16's prior "poor
   progress proxy" finding, and is not load-bearing.
4. **EulerPC and DVV tiers ruled MOOT** (stood-down, not retracted — specs stay on record as
   contingency): both hedge the corrector-non-convergence mode, which did not recur; a B+ failure
   would be a basin-connectivity question neither tier answers differently.

**Remaining path to closing condition 7's reverse branch: the two B+ optimisation jobs.** Routed to
engineer14 (pricing) + coder16 (build) in one pass.

🟢 **B+ CLOSING JOBS STAGED AND CLEARED, 2026-08-25** (`engineer14` §R39.87, `coder16` build,
`critic17` batches 36-41 — five review rounds, decks untouched through all of them, mtime-verified):
- `pilot_tests/bplus_reverse_new_2026-08-25/` — two loose opts from candidate B's Points 35/70
  (arc 2.38953/4.77975, both independently re-derived from `guards.bplus_sample_points()` by tool,
  coder16 AND critic17). Route byte-identical to the original `bplus_reverse_mid.gjf` family. Priced
  10.32-14.66 core-h reserved/job (`[MEASURED]` bracket from the original B+ logs), wall ~10-14 min at
  64 cores, 2h caps. Tarred: `pilot_tests/bplus_reverse_new_2026-08-25.tar.gz`. **Not yet run.**
- 🔴 **§39.132 ruled** (proposer13): reactant_match's energy clause NOT droppable (distance-only would
  pass a Li-coordination isomer — the measured 0.686 eV/same-graph hazard). No re-cert needed either:
  `reactant_cert.energy_hartree = -349.620897014` `[MEASURED, from endpoint_tight.log]` — the cert's
  own cited certification log, verified independently three times (proposer13, coder16, critic17).
  Backfill applies to the WORKING COPY at gate time, never `cpu_machine_pilot_results/`. The
  previously-documented `SEI_C8_ENDPOINTS_JSON` "workaround" is a test-fixture channel the gate never
  reads — that wrong claim is now corrected at its source (`U56.sh` comments) too.
- **Reading rules baked into the README**: locate the cert log by PROVENANCE (`reactant_source` field),
  never find/glob (five near-identical `endpoint_tight.log` siblings; the ε∞ one is 2.571e-5 eV away);
  record measured `energy_delta_ev`, not just the boolean — the tight-vs-loose systematic (-4.13e-4 eV)
  consumes 41.3% of the 1e-3 tolerance, so above ~4e-4-but-under-1e-3 reads MARGINAL → proposer
  review. Dry run on the ORIGINAL B+ outputs with backfill applied: agreement=True,
  reactant_match(mid/last)=True/True at exactly the known systematic (0.000413 eV) — pipeline sound.
- **Line-drift class retired**: the README's PYBPLUS extraction is now delimiter-anchored awk +
  `ast.parse` sanity check (line numbers drifted twice in one session from unrelated comment edits);
  hardcoded line-number citations purged from the README and the new U56.sh comments.
- **Standing, non-blocking**: package diverged from `src/` across 10 files (every builder this work
  item produced) — `make_package.sh` rebuild + verification is REQUIRED before anything ships from
  the package; R-10 still red.
- 🔴 **Session lesson, recorded at critic17's suggestion**: three defects today were authoritative-
  sounding cross-references nobody had followed end-to-end (the §39.130 misquoted doc line, the
  inherited SEI_C8_ENDPOINTS_JSON workaround, the drifted sed range) — each one grep from being
  checked. The fourth instance retired the mechanism (delimiter-anchored extraction) instead of
  patching the instance; prefer that shape.

### B+ JOBS RETURNED, 2026-08-25 — both clean. Lead's arithmetic below is PRELIMINARY; the ruling
### belongs to proposer13 via the documented README pipeline, routed.

PBS 23759811 (mid) / 23759816 (last): both `rc=0`, Normal termination, `Stationary point found`
(1 each), no kill markers, ~7-8 min wall each — inside every estimate. Final SCF energies:
- `bplus_reverse_mid.log`:  **-349.620902617** Ha (14 cycles)
- `bplus_reverse_last.log`: **-349.620887192** Ha (13 cycles)
- certified reactant (§39.132 backfill value): -349.620897014 Ha

Lead's preliminary deltas `[MEASURED, arithmetic only — no graph/distance clauses checked, no
pipeline run]`:
- mid vs last (the `bplus.agreement` energy clause): **4.197e-4 eV** — under the 1.0e-3 tolerance.
- last vs certified reactant (the `reactant_match` energy clause): **+2.673e-4 eV** — under 1.0e-3
  AND below the ~4e-4 marginal threshold; note it is SMALLER than the tight-vs-loose systematic
  (-4.13e-4), and on the opposite sign — an observation for proposer13 to interpret, not the lead.
- mid vs certified reactant: -1.525e-4 eV.

NOT yet done: covalent-graph clause, break-bond distance clause, the actual PYBPLUS pipeline with
the §39.132 backfill, and the ruling on whether U-56a condition 7's reverse branch closes. Routed to
`proposer13` (rule via the README's own documented procedure) with `critic17` verification to follow.

---

## 1f. R-9 — THE REVERSE ARM: RULED AND PRICED, 2026-08-22. Nothing submitted; U-56a still OPEN.

Sources: `02_METHOD_SPEC.md` §39.124 (proposer12) and `03_COMPUTE_PLAN.md` §R39.81 (engineer13), both
read directly by lead before this summary was written — not taken from either agent's own report.
Both agents have delivered and stopped. This closes R-9's *planning* status only: **it is ruled and
priced, but not scheduled, not built, and not submitted.**

### Cause of `low_confidence`, re-derived from primary sources

proposer12 re-derived the figure rather than restating it: the B+ mid/last gap is **1.02199** arc
units (the "~1.0" every prior document carried, now confirmed to four decimals), from a reverse arm
that reached **6 points / 1.70584 arc** before dying. Code trace (`guards.py:48-70,161-336`):
`parse_irc_path_frames` excludes the saddle, so `n = 5`; `5 < BPLUS_LOW_CONFIDENCE_MIN_POINTS (10)`
downgrades `bplus_agreement_effective` from `True` to `"low_confidence"` **before** the branch that
would set `connection_established_via`. So for the reverse arm that field is not "set but weak" —
it is **literally absent**. The forward arm (n = 20) does set it. 🔴 The reverse arm also did **not**
stop at `maxpoints`: `irc_reverse.gjf` requested `maxpoints=30` and the run died at point 6 with a
real `Error termination via Lnk1e`.

### Three findings that were not on record before

- **(a) Both arms die with the SAME measured signature.** Gradient-angle series: forward climbs
  31.4°→52.0° then oscillates in a 55.1-59.4° band; reverse jumps to 48.9°/59.7° on its *first*
  failed sub-iteration and oscillates in a 51.8-58.9° band. Same Bulirsch-Stoer corrector diagnostic,
  same terminal message, same ~52-59° band. New observation; the reverse arm starts already inside
  the failure band.
- **(b) 🔴🔴 RETRACTED 2026-08-22 BY critic16 (26차 배치, C1) — IT MEASURED THE WRONG FILES
  AND IS FALSIFIED.** It claimed the two terminal optimizations sit **0.17 Å apart** on the break bond
  yet agree to 0.000127 eV, concluding the reactant-side surface is "too flat for the comparator to
  tell." **`bplus_reverse_mid.xyz` / `bplus_reverse_last.xyz` are not the optimised endpoints — they
  are the B+ START points**, and say so in their own comment line (`B+ start (mid, path point 2,
  arc 0.68385)`); `payload/U56.sh:1044-1047` writes them from raw IRC path frames *before* the
  optimisation runs. Each is byte-for-geometry identical to its own `.gjf` input block (max
  displacement **0.0000 Å**). Read from the `.log` files with the project's own parser, the
  **optimised** endpoints are mid **1.4145 Å**, last **1.4148 Å** against certified reactant
  **1.4143 Å** — **0.0003 Å apart, not 0.17 Å** — and across all 55 pairwise internal distances
  mid-vs-last agree to **0.0091 Å**. 🟢 **The comparator was DISCRIMINATING, not failing to.**
  critic16 applied §39.76's own test: the start points are 0.17 Å apart *by construction* (that is
  what `bplus_sample_points` is for), so the quoted evidence had **zero** discriminating power for the
  claim it supported. 🟢 **What is actually left**: the only real difference from the certified
  reactant is a **≤0.47 Å displacement of Li**, the one soft cation coordinate `bplus_agreement`
  deliberately excludes — a proposer question about an excluded coordinate, not a flatness question.
  🔴 **Consequence: candidate D(i) was made mandatory at 30.0-49.9 core-h to settle a gap that does
  not exist.** Cancel or re-scope; routed by the lead to proposer12 (and engineer13 for the budget
  line). Also void: this finding was the stated justification for `guards.reactant_match()`'s
  docstring and `tests/test_bplus.py`'s rationale, both already shipped by coder15.
- **(c) 🔴🔴 A spec-vs-code gap in condition 7 itself.** §39.32(g) condition 7's ruled text requires
  *"in both branches the reverse endpoint must match the certified reactant."* `grep` for
  `certified_reactant|reactant_certified` across `guards.py` and `collect.py` returns **nothing** —
  `bplus_agreement()` compares `mid` against `last` only, and never reads `reactant_certified.xyz`.
  proposer12 explicitly did **not** rule which reading is correct, and stated that **no protocol may
  be certified as "fixed" while this gap is unaddressed.**
  🔴 **Its worked example is VOID** (critic16 C1): the claim that a literal both-points reading would
  reject `mid` (0.197 Å out) while `last` passes (0.022 Å) used the START-point numbers. On the
  optimised endpoints the deltas are **0.0002 Å (mid)** and **0.0005 Å (last)** — under every reading,
  **both pass**. The reading question is real as a spec question but **has no consequence on this
  data**, and must stop being described as the thing that could reject `mid`.
  🟢 **critic16 RULED the reading** (P3, which §39.124 declined to give): *"both branches"* means the
  two **establishment branches** just enumerated (convergence, `maxpoints`+B+) — **not** the two B+
  start points. "Endpoint" is singular and `mid` is by construction a *mid*point; and `mid`'s whole
  job is detecting a bifurcation *between* the samples, which requires it to be allowed to differ.
  ⟹ **Condition 7 constrains `last` only — and constrains it in the CONVERGENCE branch too, which
  today has no check at all.** Running the check on both points is harmless as *reporting*; it must
  never be combined into a verdict requiring both.

### Candidates — three live, one rejected in both its variants

- **D — 🔴 (i) WITHDRAWN 2026-08-22; (ii) stands and is mandatory.**
  ~~(i) Re-optimize the *existing* `bplus_reverse_mid/last.xyz` at **tight** convergence to settle
  whether (b)'s 0.17 Å gap is a real feature or a loose-optimization artifact — 30.0-49.9 core-h.~~
  **Withdrawn permanently**: finding (b) was falsified (critic16 C1), so there is no 0.17 Å gap and no
  job to price. engineer13 re-verified independently against the logs' final `Standard orientation`
  blocks before retracting the figure. **Nothing lost scientifically** — the question it would have
  answered was already answered by reading the existing logs correctly, at zero cost.
  (ii) Implement the reactant-match check named in finding (c) — **~0 core-h**, pure post-processing
  on files already on disk, now with proposer12's sourced `REACTANT_MATCH_TOLERANCE_ANG = 0.05` Å
  (`last` only) to implement against. Explicitly **not gated** on A/B, on stage 4, or on any ceiling.
- **A — mirror stage 4's fix onto the reverse arm**: restart `irc_reverse.chk` (verified intact,
  10,342,400 B) with `irc=(restart,recorrect=never)`. **17.3-32.7 core-h** at engineer13's 9-point
  sizing; ≤~87 core-h at the `maxpoints=30` cap actually ruled. Wall 16-31 min at 64 cores.
- **B — fresh IRC redo from the TS with a genuinely different corrector** (`StepSize` or `EulerPC`),
  motivated by (a)'s *oscillating* (limit-cycle) rather than runaway failure — a distinct mechanism
  from what `recorrect=never` addresses. **25.0-47.2 core-h** per attempt, up to **94.4** if a second
  attempt is needed, plus a recommended **2-4 core-h** one-point route smoke.
- **C — REJECTED, both variants.** (i) Re-picking mid/last from the same 6-point path cannot
  manufacture arc-length that does not exist. (ii) 🔴 Sourcing a farther point from the existing
  G-SCAN-2 scan would **import Track B item 7's unratified mapping protocol into U-56a's gate** —
  that protocol's own barriers span 0.0216 eV to ~73 eV depending on unresolved choices. **Do not use
  G-SCAN-2 geometries to source B+ points until item 7 is ruled.**

### Acceptance criterion (program-evaluable)

```
n_frames_reverse_new (saddle excluded) >= 10          # already ruled §39.114(1)(3), applied not re-derived
AND bplus.agreement is True at that path's own mid/last pair
    (covalent_graphs_match AND energy_delta_ev <= 0.001)
AND arc_length_reached_reverse_new >= 4.27            # NEW, proposer12's own clause
```
🟡 **4.27 is `[ESTIMATE]`, interim** — the arithmetic midpoint of the one known-insufficient case
(1.71) and the one known-sufficient case (6.83, forward, same reaction). §39.114(1) declined to invent
a principled floor and proposer12 did not override that; this is a placeholder flagged for review, to
be superseded once more measured truncated-IRC cases exist. Its only job is to stop a smaller step
size from clearing the frame count while covering **less** real distance than today's failure.
🟡 **Self-test result, stated honestly**: satisfying both clauses brings the reverse arm's residual
risk down to **parity with forward's already-accepted level, not to zero** — R-1/R-2 remain (B+ can
only catch a bifurcation *between* its two sampled points, never past the last one). **Report it that
way when it closes; do not report it as "resolved."**

### Sequencing — ruled, and it is an inference constraint, not a scheduling preference

**Stage 4 (forward) runs first; its result is read before any core-h is committed to the reverse
restart.** Because of finding (a), candidate A and stage 4 are **not independent draws** on the
integrator question — same signature, same molecule, same mechanism.
- Stage 4 succeeds → try **A** on reverse (high prior it also works).
- Stage 4 repeat-crashes → skip A, go straight to **B** (a genuinely different fix), rather than
  spending core-h to re-confirm a failure already demonstrated on the same mechanism.

ADR-117 keeps stage 4 and any reverse job as separate PBS jobs for **wall-budget isolation** — that
ruling is unaffected and still stands. The correlation above is in *inference* space, not resources.
🔴 Candidate A inherits stage 4's own hazard: `irc=restart` may silently drop `recorrect=never` from
the checkpoint. **The same mandatory post-run grep for `Recorrection delta-x convergence threshold:`
applies to the reverse job**, and the reverse restart route is **unsmoked** (verified for forward only).

### Cost is not the binding constraint

```
Cheapest realistic path   (D + A succeeds first try)          47.3  -  82.6  core-h
Most expensive realistic  (D + B fails once, 2nd attempt)    126.4 - 194.2  core-h
```
Consumed after the staged resubmit: **~12,761 / 21,000**, leaving **~8,240 core-h** of margin. The
worst realistic path is ~2.4% of that, and every wall figure is far inside ADR-114's 48 h cap.
🟢 **Every core-h figure traces to this exact 11-atom reaction's own measured per-point rate**
(0.341-0.342 arc/frame — independently identical across BOTH arms, 0.34117 reverse / 0.34173 forward;
1.92-3.63 core-h/point), never a scaled guess. **This does not repeat the T21-se extrapolation
failure.** engineer13 requested no re-cut on cost grounds.

### `maxpoints` — the one disagreement, resolved by the proposer with the engineer deferring

engineer13 sized candidate A at `maxpoints=15` (a cost-conscious target). proposer12 ruled
**`maxpoints=30`**, matching the original reverse route's own cap, on two scientific grounds: (1) a
genuine G16 `PES minimum detected on this side` stop is **categorically stronger evidence** than
clearing an interim floor and falling back to B+, and a run allowed to continue has a real chance at
it; (2) the 0.341 arc/frame rate was measured under the **original** corrector settings — nothing
guarantees `recorrect=never` preserves it, and under-sizing costs a full round trip (~3.5 calendar
days, the one cost axis the core-h analysis did not price). `maxpoints` is a ceiling, not a target —
the run still stops on its own conditions. **engineer13 independently agreed and withdrew the tighter
sizing.** No lead adjudication was needed on this; the two settled it directly, which is the pairing
working as designed.

### What this does NOT do

- **It does not close U-56a.** Condition 7 still fails on the reverse arm today. Nothing has run.
- **It does not close finding (b) or (c)** — candidate D exists precisely to address them, and
  proposer12's criterion explicitly does not cover either.
- 🔴 **It creates a real `src/` change for the first time this round**: finding (c)'s missing
  reactant-match check, plus candidate D(ii)'s comparison script. proposer12 routed both to
  coder/critic and stated D(ii) "should not wait on A/B's cost ceiling." §4 RESUME (6) said not to
  respawn coder *until there is a real code change to make* — **that condition is now met.** Whether
  to pull coder in now is a lead/user call, but this is a trigger, not an absence of one.

### R-9 TRIAGE — lead ruling, 2026-08-22, and three NEW defects found while ruling it

proposer12 left three unresolved items. Ruling below. 🔴 **Ruling item 1 required opening the
tool candidate A depends on, and that surfaced three defects nobody had looked for** — recorded
first because two of them bear on rulings already made.

#### 🔴 NEW (lead, by reading `build_u56_ra_irc_recorrect_probe.py` + the original decks)

1. 🟢 **Candidate A needs NO new tool work.** engineer13's §R39.81 called it "new tool work, one line
   different from the forward version." It is not: the tool is already fully direction-parameterised
   (`--direction {forward,reverse}`, `build(direction=...)` reads `irc_%s.chk`, names the output
   checkpoint and title line per direction). Candidate A's deck can be built **today, with a flag.**
   Verified independently: `irc_reverse.chk` is 10,342,400 B, byte-identical in size to
   `irc_forward.chk`, as proposer12 reported.
2. 🔴🔴 **proposer12's `maxpoints=30` ruling has NO implementation path in this tool, and the
   mechanism it would have to rely on is the one this project already refuses to trust.** The tool
   builds `irc_opts = ["restart"]` (+ `recorrect=never`, + optional `stepsize`) — **`maxpoints` is
   never written into the route at all**, nor is the direction keyword. On `irc=restart` G16 takes
   both from the checkpoint. The original `U56_RA_scan/irc_reverse.gjf:4` reads
   `irc=(calcfc,reverse,maxpoints=30)`, so the inherited value *would* be 30 — i.e. proposer12's
   ruling happens to be satisfied **by accident, via silent inheritance.** But §1e's fourth
   correction exists precisely because `irc=restart` **may silently drop** an option it takes from
   the checkpoint — that is why the `Recorrection delta-x convergence threshold:` grep is mandatory.
   **The project is simultaneously distrusting this inheritance path for `recorrect=never` and
   depending on it for `maxpoints=30`.** Both cannot be right. Fix is trivial (state `maxpoints`
   explicitly in the restart route) but it is a real `src/` change, and until it lands the
   `maxpoints=30` ruling is **unimplemented and unverifiable as written** — a decision that exists
   only in prose. Same "measured but unread" family, one layer further out: *ruled but unwired*.
   🔴 **critic16 CONFIRMED this by running the builder** (C3) and added two things the trivial fix does
   NOT cover: (i) **do not blindly add the direction keyword too** — `irc_reverse.chk` holds a
   single-direction run so bare `restart` resumes the right branch, whereas adding `reverse` to a
   `restart` route is unsmoked here and on some G16 builds reads as *"now do the other direction from
   the saddle"*, silently starting a new FORWARD walk and burning the round trip (`[의심]`, no G16
   available to settle it); (ii) **`maxpoints=30` on a restart is ambiguous between "30 total" and
   "30 more"** — state which was assumed in the manifest so the returned log can falsify it. Verify
   by reading the restart log's first `NET REACTION COORDINATE` (must resume at ≈1.706, not 0.34) and
   the break bond (must be ≈1.41, not increasing) before interpreting anything.
3. 🔴 **The tool's `total_cores=1` default is a live hazard — but the lead's FRAMING was wrong and
   critic16's is sharper (C4).** The lead called it "an ADR-117 repeat pre-loaded in the defaults."
   🟢 **It is not an ADR-117 deck/allocation mismatch**: the staged stage 4 is *self-consistent* at
   1 core (`submit_stage4.pbs` `select=1:ncpus=1` + deck `%nprocshared=1`). The real exposure is
   **wall clock, and it breaks a different rule** — candidate A at `maxpoints=30` is 24 remaining
   points × 1.92-3.63 core-h/pt, i.e. **0.7-1.4 h at the 64 cores engineer13 priced, but 46-87 h at
   the tool's default 1 core**, whose pessimistic branch **exceeds ADR-114's 48 h cap**. That is the
   same wall-kill that produced ADR-117 (PBS 23731675, `walltime 7244 exceeded limit 7200`),
   reachable purely from a default. → Build candidate A with explicit `--total-cores 64` **and** a
   matching `select=1:ncpus=64`, or make `--total-cores` required with no default.
4. 🟡 **Minor, but a standing-rule-1 violation**: the manifest's `estimated_cost` string is hardcoded
   to forward's arithmetic ("maxpoints=30 minus 20 already computed and stored"). Run with
   `--direction reverse` it emits that same string, where the true figure is 30 minus **6** = 24
   remaining points. A cost number describing the wrong route, written automatically.

#### Ruling on proposer12's three items

🔴 **Item 1 — SUPERSEDED 2026-08-22, same day, before anything was built. Lead's earlier
"BUILD NOW, SUBMIT GATED" ruling is WITHDRAWN and its rationale was partly circular.**

The withdrawn ruling justified building candidate A's deck immediately on the grounds that *"building
it now is what exposed three defects at zero cost."* **That is not what happened.** The three defects
(the unwired `maxpoints`, the `total_cores=1` default, the wrong-direction cost string) were found by
**reading** `build_u56_ra_irc_recorrect_probe.py` and the original decks — no deck was ever built. The
value had already been extracted before any build, so the build could not be justified by it. What
survived was only the round-trip saving (~3.5 calendar days, one `RT-N`), which is a real but much
weaker argument than the one actually written down. Self-check failed on the lead's own ruling in the
same round it was issued: *"if this reasoning were wrong, would the conclusion look any different?"* —
it would not have, which is the §39.76 "agreement is not identity" defect applied to an argument
rather than a number. Recorded, not buried, per §1e's precedent for the lead's own errors.

**The replacing distinction (lead, and it is the better one): "fix the tool's bugs" and "build or
submit candidate A's deck" are SEPARABLE, and only the first is unblocked.**

**Current true state of candidate A — nothing is in flight:**
- **Nobody has built candidate A's deck.** It does not exist. The tool supports `--direction reverse`
  today, so building it remains cheap whenever it is authorized — but it is not authorized now.
- **The three tool fixes are pending `critic16`'s verdict**, not pending stage 3/4. They are ordinary
  `src/` bug fixes; fixing them builds and submits nothing.
- **Submission stays gated on stage 4's result** per §39.124(4) — unchanged, and this is the one part
  that was never in question. It is an inference constraint (candidate A and stage 4 are correlated
  draws on the same integrator hypothesis), not a scheduling preference.
🟢 The practical consequence of the split: the `total_cores=1` defect can be fixed **before**
anyone is in a position to trip over it, which is the outcome that actually matters — it is dormant
only for as long as no reverse deck is built, and it would otherwise fire on the first build.

**Items 2 + 3 — to `critic16` NOW; `coder15` AFTER critic's verdict.** Both items are
**author-originated and author-verified**: proposer12 wrote the `arc_length >= 4.27` threshold *and*
its own self-test, and found the `guards.py` gap *and* declined to rule which reading of it is
correct. §4's standing engineering rule 6 is explicit — *"an author's own spec is not a spec until it
has been run against a case it could fail, or read by whoever has to implement it"* — and §39.76
records a proposer failing its own authored control twice in one afternoon after having authored it.
This is the project's most expensively-learned lesson and it applies here unmodified.
- **critic is read-only and costs zero core-h.** There is no budget argument for deferring it.
- **Ordering matters**: if critic finds the 4.27 floor or the condition-7 reading wrong, coder would
  otherwise have implemented the wrong thing. Rule 5 applied to labour instead of core-h.
- **No conflict with §4 RESUME (6)** — that rule constrains *coder*, not critic. And the coder
  trigger it was waiting for now genuinely exists (findings 2-3 above plus D(ii) plus the condition-7
  check), so it no longer blocks coder either; sequencing does.
- `critic16` on **opus** per standing instruction (7).
- **coder15's worklist is now bounded and known**: D(ii)'s reactant-match check, findings 2-4's tool
  fixes (explicit `maxpoints`, explicit cores, direction-correct cost string), and whatever critic
  returns on the condition-7 reading. **Not gated on stage 3/4** — that gates candidate A's
  *submission*, never its build.

### critic16's 26차 배치 — verdict **BLOCK**. What else it changed, and what survived.

Read in full by lead from `04_REVIEW_LOG.md:8506` before any of it was recorded here. Its two
headline results (C1, C2) are folded into the findings above and into §2. The rest:

**Also broken (fix before candidate A is built or D(i) funded):**
- 🔴🔴 **C2 — `guards.reactant_match()` can NEVER return `True`, so condition 7's reactant half is a
  gate that cannot open.** See §2; this is the U-56a-level consequence.
- 🔴 **M1 — §39.124(3)'s criterion is prose-only; "program-evaluable" is not yet true.**
  `grep -rn "4\.27" src/ tests/` returns only unrelated hits, and `irc_completion_*.json` carries **no
  arc field at all**. `arc_length_reached_reverse_new` names a quantity nothing emits. It is
  computable (`g16.parse_irc_arc_lengths`, `criteria/g16.py:268`) but is not computed — the same
  *ruled but unwired* family as the `maxpoints` finding. → Emit arc length into
  `irc_completion_*.json`.
- 🔴 **M2 — `maxpoints=30`'s FIRST justification cites §39.116 for the opposite of what §39.116
  ruled.** §39.124's addendum called a self-declared `PES minimum detected on this side` stop
  "categorically stronger evidence," citing `U56_RB_scan`'s stop as precedent. §39.116(b)-(c) ruled
  that exact stop an **artefact** (declared minimum 0.0009 Å from the saddle; *"do not count this arm
  as C-2 connection-established evidence"*), and both `U56_RB_scan` arms stopped at **1 point**, arc
  0.183/0.223. The precedent cited as the strongest case is the project's own worked example of the
  weakest. 🟢 **The `maxpoints=30` ruling itself SURVIVES** on its second reason and on P1 below —
  only its first justification falls.
- 🔴 **M3 — a live risk for candidate A that no document named.** §39.116's artefact mechanism is a
  fixed force-threshold minimum test firing on a flat coordinate, and the reverse terminal region
  **is** low-gradient (max force 1.6-3.3×10⁻⁴ au at both B+ points). So candidate A's *best* outcome —
  an early `PES minimum detected` — is exactly the outcome §39.116 says can be an artefact, and
  §39.124(3) has **no branch for it** (three AND-ed clauses, all written for the truncated/B+ branch).
  → A declared minimum counts only if structurally distinct from the preceding path point; report the
  delta, do not invent a threshold.
- 🔴 **M4 — the criterion conflicts with §39.32(g) branch (a) and nothing says which governs.**
  Condition 7 establishes connection by **EITHER** convergence **OR** `maxpoints`+B+. §39.124(3) is a
  single AND-block. A reverse restart converging to a genuine, structurally distinct minimum at
  n = 8 / arc 3.9 satisfies branch (a) and **fails** §39.124(3) as written. → Scope the criterion
  explicitly to branch (b).
- 🟡 **M5 — the hardcoded cost string is wrong for FORWARD too**, not just reverse: *"~29 remaining
  points at most (maxpoints=30 minus 20 …)"* — and 30 − 20 = 10, not 29. The headline contradicts its
  own parenthetical. Standing rule 1 violated three ways in one string.
- 🟡 **N1** — `shutil.copyfile(src_chk, dst_chk)` has no overwrite guard while the docstring claims
  *"re-running is idempotent"*: re-running into an out-dir where the probe already ran **silently
  overwrites the progressed checkpoint**, destroying the run's IRC path. **N2** — `bplus_sample_points`
  picked reverse `mid` by a margin of 0.0037 arc units, effectively a coin flip between path points 2
  and 3 (not load-bearing, since C1 shows both optimise to the same place). **N3** — decks built from
  `src/` carry fingerprint `f15cce8bfb4ed4e2`, not the live package `a7b678…`/`a7b638…` — state it in
  any handoff.

**🟢 What SURVIVED review (negative results, reported as required):**
- **P1 — the 4.27 floor is reachable, and critic16 checked it the way it could have failed.** The
  concern was that the reverse arm travels far less break-bond distance than forward (0.31 Å vs
  ≈1.0 Å), so a forward-calibrated floor could reject a *successful* reverse run. Tested with a
  mass-weighted Kabsch superposition in G16's own arc units, validated against the log: the reverse
  path totals **≥6.47 arc units** (forward's measured total: 6.83), so 4.27 is ~66% of the arm's own
  path length and comfortably reachable. 🟢 **By-product: `maxpoints=15` WOULD have undershot** —
  9 new points × 0.3415 = 3.07, total 4.78, clearing the floor while stopping ~1.7 arc units short of
  the actual minimum. **proposer12's `maxpoints=30` over engineer13's 15 is independently vindicated,
  on a ground neither of them stated.** Second by-product: the break bond is a poor progress proxy
  here — at point 5 it has already reached the reactant's value while ≥73% of the path remains.
- **P2 — `[ESTIMATE]` is the right label; the review trigger was not concrete enough.** 6.83 is not a
  measurement of sufficiency, it is where forward happened to crash. At 0.3415 arc/frame the clause is
  algebraically `n ≥ 12.5`, i.e. 25% margin over the frame count — fine, because its **only** stated
  job is candidate B's changed step size. → Trigger made checkable: *"supersede when a third measured
  truncated-IRC arc exists, or when any reverse arm reaches a structurally distinct minimum."*
- **P4 — the gradient-angle signature reproduces exactly AND has a real negative control.** Both arms
  die in their oscillating bands on the same terminal message; but `U56_RA_qst2` crashed with the
  **same message** in a completely different band (forward ≈17.4-17.9°, reverse ≈13-23°). So the
  *message* has zero discriminating power (3 of 4 crashed arms share it) while the *band* has real
  power. **§39.124(4)'s stage-4-first sequencing keeps its basis.**
- **P5 — every other load-bearing figure re-derived and reproduced**: reverse arc 1.70584 / 5 frames,
  forward 6.83462 / 20, B+ gap 1.02199, `energy_delta_ev` 1.268e-4, both `.chk` at 10,342,400 B, both
  B+ optimisations genuinely converged. The reverse restart deck carries the **correct** solvent
  (`scrf=(pcm,solvent=acetone,read)` + `eps=18.5`, byte-identical to `irc_reverse.gjf`) — C-5 not at
  risk.

**Could not verify (named, not hidden)**: G16 restart semantics (whether `maxpoints` on a restart is
total or additional; whether adding `reverse` resumes or restarts) — no G16 on this machine or in the
project; both resolved by post-run checks at zero cost. Also unverified: whether `irc=restart` will in
fact inherit `maxpoints` — C3's explicit-statement fix removes the dependency instead of settling it.

🔴 **PROCESS FAILURE, recorded not buried**: the lead ruled "critic16 NOW; coder15 AFTER critic's
verdict," and **that ordering did not hold** — coder15 landed `guards.reactant_match()`, its
`payload/U56.sh` wiring and `tests/test_bplus.py` at mtime 15:22, before the review began. critic16
reviewed as-found rather than as-planned. The damage is bounded and specific: **the function reads the
RIGHT geometries** (`U56.sh:1080-1081` passes `g16.last_geometry(log)`, not the `.xyz`) — the code is
correct — but its docstring and the test's rationale bake in the premise C1 falsifies, and the
`None`-never-`True` behaviour C2 flags was defended by that same premise. Exactly the failure mode the
ordering existed to prevent, at exactly the scale it was expected to have.

### R-9 CONVERGED — the corrections landed, 2026-08-22. Verified by lead against the owned documents.

All figures below re-read from `02_METHOD_SPEC.md` §39.124's correction block and
`03_COMPUTE_PLAN.md` §R39.81's closing section directly, not from any agent's summary.

**proposer12 — retractions and three new rulings:**
- 🟢 **Finding (b) and its worked example: struck.** The retraction is proposer12's own, not imposed.
- 🟢 **M2 struck**: the §39.116 mis-citation is removed. `maxpoints=30` **survives on reason 2 alone**
  (the pre-crash arc/point rate may not hold under `recorrect=never`, so a generous cap avoids risking
  an extra round trip), plus critic16's arc re-derivation — `maxpoints=15` would have stopped ~1.7 arc
  units short of where B+'s own optimization landed. Right answer, for a reason neither of them had
  stated.
- 🟢 **Ruling 1 — `REACTANT_MATCH_TOLERANCE_ANG = 0.05` Å on the declared break bond, `last` only.**
  Sourced **two independent ways**, which is why proposer12 ruled a number here having declined to
  invent one for the arc floor: (i) the measured bracket — same-basin 0.0002-0.0005 Å vs the one
  different-basin case at 1.70-1.75 Å, a ~3,400× gap whose interior placement barely matters, with
  0.05 Å near the log-space centre (√(0.0005 × 1.7) ≈ 0.029 Å); (ii) G16's own printed loose-opt
  `Maximum Displacement` threshold of 0.010000 Bohr = 0.00529 Å per atom, so 0.05 Å is ~10× the
  single-atom convergence noise. `[ESTIMATE]`, but with two real anchors rather than a bracket alone.
- 🟢 **Ruling 2 — the acceptance criterion is scoped to branch (b) explicitly, and branch (a) is a
  separate, simpler pass.** IF branch (a) (normal termination + `minimum_found` + ruling 3's
  distinctness check) THEN condition 7 is satisfied outright for that direction — real convergence is
  always stronger than B+, matching `guards.py`'s existing *"THE IRC WINS HERE"* rule — and it need
  not clear the arc floor or frame count, which exist only because branch (b) has no ground truth.
  ELSE apply the full AND-block with the reactant-match check on `last` only. **This closes M4.**
- 🟢 **Ruling 3 — a declared minimum counts as branch (a) only if structurally distinct from the
  immediately preceding IRC point.** No new threshold invented: reuse §39.116(d)'s already-measured
  rotation-invariant max pairwise heavy-atom distance change and **report the delta**. Reading rule
  from anchors already on record — below ~0.05 Å is artifact-suspicious and needs a human read
  (§39.116's confirmed artifact measured 0.0203-0.0228 Å). **This closes M3**, and it qualifies the
  `maxpoints=30` addendum directly: an early self-declared minimum during candidate A is **not
  automatically better evidence** — only if it passes this check, else fall through to branch (b).

**engineer13 — D(i) withdrawn, R-9 pricing closed:**
- 🟢 **D(i) is CANCELLED — "full stop; not paused, not re-scoped"** (proposer12's own words), and its
  30.0-49.9 core-h retracted with the finding it was priced against. engineer13 re-verified
  independently against the logs' own final `Standard orientation` blocks rather than accepting the
  retraction, then asked whether to **re-target** D(i) at critic16's residual (the ≤0.47 Å Li
  displacement) instead of dropping it. **Declined, and the reason is a design principle, not a
  budget call**: §39.70 deliberately excludes cation-coordination contacts from B+'s comparator and
  treats Li's position as a **reported covariate, not a decision input** — because soft Li motion
  within a shared coordination environment is not diagnostic of "different basin" (the same reasoning
  that made the spectator test necessary, ADR-112). **Nothing in §39.124(3) reads a Li-displacement
  number, so a dedicated job would feed no pass/fail call that exists.** A job with no consumer does
  not get funded because its number is interesting. 🔴 `payload/BPLUS_REOPT.sh` stays fully dead —
  coder15 instructed, do not revive it. **Nothing was lost scientifically**: the question D(i) would
  have answered was already answered by reading the existing logs correctly, at zero cost.
- 🟡 **Zero-cost residual, not urgent**: if the ≤0.47 Å Li figure is not already in
  `bplus_reverse.json`'s `covariates` block, record it there as a reported value — no new job, no new
  core-h. That satisfies C-3's *"report, don't decide"* treatment of this coordinate **without
  inventing a use for it it does not have.** Routed to coder15.
- **D(ii) stands**, ~0 core-h, now with a sourced tolerance to implement against.
- **Final R-9 total**: worst realistic case **~181 core-h** (A to its ~87 core-h `maxpoints=30`
  ceiling + B needing two attempts at ~94.4), **~2.2% of the 8,240 core-h guard margin.** Budget is
  not binding — unchanged conclusion, now with D(i) gone.
- **Build candidate A against proposer12's `maxpoints=30` ceiling, with explicit `--total-cores 64`.**

🟢 **The one genuinely good outcome of this round**: the most expensive item on the board (D(i),
mandatory, 30-49.9 core-h) was **cancelled because someone read the files correctly**, and the
tolerance that had been blocked on *"no measured bracket exists"* was unblocked by data this project
had **already paid for**. Both came from re-derivation, not new compute.

### R-9 FINAL PIECE — `reactant_match` verified working, three closers outstanding (2026-08-22)

🟢 **`guards.reactant_match()` now actually returns `True`** — critic16 verified by execution, not
by reading: the energy values reproduce exactly and `reactant_match(last)` returned `True` for the
first time in this project's history. **The gate that could never open, now opens.** The implemented
form is proposer12's final one: a **three-way** combination, not a plain AND — `True` only when both
the 0.05 Å break-bond clause and the energy clause pass; `False` only when both definitely fail; a
**split or an unmeasured clause is `None`**, reusing `bplus_agreement`'s own genuine-ambiguity rule. A
covalent-graph bifurcation is checked first and is the only route to `False` without both clauses
failing together. Four rounds of critic review stand behind it.

🟢🟢 **R-9 IS CLOSED — critic16's final verdict, 2026-08-22.** All three closers execution-verified
(1737 tests, 4 unrelated failures), independently confirmed by lead in source beforehand. Ruling,
pricing and code are all verified. 🔴 **"R-9 closed" means the reverse-arm WORK ITEM is closed — it
does NOT close U-56a, and it does not mean the reactant-match clause binds in production (it does
not, see carry-over 1 below).** The three closers:

1. 🔴🔴 **The opt-in check reads a FAILURE as a PASS** (`guards.py:283,298,333`). The clause is
   opt-in by design, and the comment at `guards.py:278-279` states the intended semantics **exactly
   right**: *"If the caller does not supply it at all (**the key is absent, not merely `None`-valued**),
   this clause is SKIPPED entirely."* **The code does the other thing**: `reactant_match_last =
   d.get("reactant_match")` followed by `if reactant_match_last is not None`, which **cannot
   distinguish an absent key from a `None`-valued one.** And `payload/U56.sh:1122,1145-1148` sets
   `reactant_match["last"] = None` on **exactly its error path** ("NOT computed: … an unrun comparison
   is not a match"). So the one real failure mode produces a supplied-but-`None`, the check treats it
   as never-opted-in, the clause is skipped, and **condition 7 passes without its reactant-match half
   ever having run.** Fix: test key presence (`"reactant_match" in d`), so an explicit `None` reads as
   *opted in but unmeasured* → must not pass. 🔴 The aggravating factor: **the comment gave a
   reviewer false assurance**, describing the correct behaviour the code did not implement — worse
   than an unannotated bug. Same family as ADR-113 (*"done" means only the wrapper exited*).
   🟢 **FIXED and verified**: `guards.py:290` now sets `reactant_match_supplied = "reactant_match" in d`
   and both branch gates (`:306`, `:342`) consult that flag instead of the `is not None` test.
2. 🟡 **No live consumer yet.** `reactant_match` is computed and recorded but nothing in the shipped
   pipeline consults it for a verdict — register it in `tests/test_guard_reach.py`'s
   `DEFERRED_NO_CONSUMER_YET` bucket (the existing mechanism, alongside `minimum_distinctness`).
   🟢 **DONE, and the resulting statement is more important than the bookkeeping** — read it before
   trusting the fix above. `reactant_match` sits in `EXPECTED_REACHED` because `U56.sh` genuinely
   calls it; what is missing is a **PRODUCER**, not a consumer, and `tests/test_guard_reach.py:282-294`
   now records exactly that: *"`irc_direction_ok`'s §39.124 Ruling 2/A1 reactant-match consult … has
   NO LIVE PRODUCER TODAY — `evaluate_p1`, the only caller reaching this function, does not supply the
   key (P1 has no mapping/reactant wiring and is permanently excluded, ADR-112), so **the clause is
   skipped on every production path that currently exists.**"* 🔴 **Do not read "`reactant_match(last)`
   returns `True`" as "the gate now checks the reactant match in production." It does not.** The
   function is implemented, tested and reached; nothing in a live production path feeds it. Wiring a
   real producer (e.g. into a future U-56 verdict function) is named as a **separate, unscoped item**.
3. 🟡 **The three builder defects get fixed now** that critic16 has verified them — `total_cores`
   (the load-bearing one: the ADR-114 48 h wall-cap breach), the unwired `maxpoints`, and the
   wrong-direction cost string. 🟢 **All three FIXED and verified**: default is now `total_cores=64`,
   `irc_opts.append("maxpoints=%d" % IRC_RESTART_MAXPOINTS)` writes the ruled 30 explicitly, and
   `_estimated_cost_text(direction)` computes the string from the direction. 🟢 **And the direction
   keyword was correctly LEFT ALONE** — the code carries an explicit comment against adding
   `irc_opts.append(direction)`, which is what critic16's C3 warned could silently start a new
   FORWARD walk. 🔴 **Fixing is not building**: candidate A's deck stays unbuilt and its submission
   stays gated behind stage 4.

### 🔴 THREE CARRY-OVERS — outside R-9, tracked so closing R-9 does not bury them

R-9 is closed. These three are **not** part of it and remain open:

1. 🔴 **`reactant_match` has NO LIVE PRODUCER.** The clause is implemented, tested, reached and now
   capable of returning `True` — but `evaluate_p1` is the only caller reaching `irc_direction_ok` and
   it does not supply the key (P1 has no mapping/reactant wiring, permanently excluded, ADR-112), so
   **the clause is skipped on every production path that currently exists**
   (`tests/test_guard_reach.py:282-294`). **This is the binding gap in condition 7's reactant half**,
   and it is the single easiest fact in this round to misreport as a win. Wiring a producer (e.g.
   into a future U-56 verdict function) is unscoped.
2. 🔴 **`minimum_distinctness` is unwired** — ruling 3's branch-(a) artefact test exists as a function
   and sits in `DEFERRED_NO_CONSUMER_YET`. Until it is wired, a declared `PES minimum detected` stop
   during candidate A has **no automated check** against §39.116's artefact mode, which M3 identified
   as candidate A's *best*-outcome hazard.
3. 🟢 **CLOSED, 2026-08-24** (`coder16` + `critic17`, review 28th/29th batches). `shutil.copyfile`'s
   idempotency claim was false — `build_u56_ra_irc_recorrect_probe.py` copied unconditionally while
   the docstring claimed *"re-running is idempotent."* Same false-assurance shape as the opt-in bug
   (a docstring asserting a safety property the code did not have). Fixed in two rounds:
   (a) first pass added an exists-guard on `dst_chk` (refuse, exit 5, rather than clobber);
   (b) critic17's 28th batch found that pass copied BEFORE level/solvent/basis validation (a failed
   build self-locked the out-dir with a false "a prior restart may have progressed it" message) and
   that the guard covered only the `.chk`, not the fixed-name `irc_recorrect_probe.gjf`/
   `manifest.json` — building the other direction into the same out-dir silently clobbered those,
   which `submit_stage4.pbs`'s fixed deck filename would then have run as the wrong direction with no
   warning. Both fixed: copy deferred until after validation succeeds; the upfront exists-guard now
   covers all three paths (chk/gjf/manifest) together. critic17's 29th batch verified both by
   execution (rc=2 empty-dir on a failed build + clean retry; rc=5 on cross-direction rebuild, byte-
   identical deck, no orphan files) — **OK, no rework, no BLOCKER.** critic17's one nit (claimed the
   failed-build test never runs the corrected retry) was a false positive — lead re-ran
   `test_a_failed_build_leaves_no_checkpoint_for_the_corrected_retry_to_trip_over` directly and
   confirmed `tests/test_u56_ra_irc_recorrect_probe.py:146-147` already runs and asserts the retry;
   passes as written, no change needed. 🔴 **Operational note carried
   forward, not a code defect**: the guard now also refuses a rebuild into any out-dir that already
   holds a deck/manifest, including the currently-populated `4_irc_recorrect_restart/` — when
   candidate A is eventually built, it must go into a fresh out-dir (with the pbs pointed at it) or
   have the old files deliberately removed first. 🔴 **Packaging gate still open, not yet a blocker**:
   this tool is not in the shipped tarball (`test_build_stamp` names it) — `src/make_package.sh` must
   be re-run and the hash verified before candidate A is ever built from a *deployed* package;
   candidate A's own build stays gated behind stage 4 regardless, so this does not block anything
   today.

### Track B item 7 — a concrete next step named, not resolved

proposer12 did not attempt to resolve it (ADR-116: not resolvable on present data). What would
resolve it: an **external anchor** rather than another self-consistency run — a short 2-D relaxed scan
over **both** the C-O break coordinate **and** the Li-O(ether) distance for R-A, checked against the
already-accepted `U56_RA_scan` TS (Ω = 0.839, ω = -1153.2 cm⁻¹, independently verified). Whichever
Li-coordinate treatment reproduces that known fixed point is the one the mapping protocol should
declare. Unpriced — a scheduling item, not a ruling.

---

## 2. U-56 — the S3 gate, split and its current status

> 🔴🔴🔴 **2026-08-22, critic16 C2 (26차 배치) — CONDITION 7'S REACTANT-MATCH HALF IS A GATE THAT
> CANNOT OPEN. `guards.reactant_match()` can never return `True`, so as currently implemented U-56a
> can NEVER close — including today, where the reverse endpoint matches the certified reactant to
> 0.0005 Å on the ruled coordinate.**
>
> `guards.py:539-585`: `match` is set to `False` only when the covalent graphs differ; in the
> graph-agreeing branch it is left `None`. **There is no path to `True`.** The project's own test
> asserts this for two *identical* geometries (`tests/test_bplus.py:113-117`:
> `"graph agreement alone must not become True (finding (b))"`) — and critic16 ran the suite to
> confirm (32 tests, OK). 🔴 The `None` was **defended by finding (b), which C1 falsifies** (§1f), so
> the justification for the behaviour is gone even though the behaviour itself still ships.
>
> **The stated blocker to setting a tolerance was "no measured bracket exists." One exists now**, from
> this reaction's own already-paid runs, in exactly the two-sided form `BPLUS_ENERGY_TOLERANCE_EV`
> itself was derived in:
> ```
> SAME basin (measured)       optimised reverse mid/last vs certified reactant   Δ(break bond) 0.0002 / 0.0005 Å
> DIFFERENT basin (measured)  optimised forward mid/last vs certified reactant   Δ(break bond) 1.748 / 1.700 Å
> ⟹ ~3,400× separation. Any tolerance in 0.01-0.5 Å passes what it must and separates what it must.
> ```
> 🟢 **PARTIALLY RESOLVED, same day.** proposer12 ruled the tolerance:
> **`REACTANT_MATCH_TOLERANCE_ANG = 0.05` Å on the declared break bond, applying to `last` only**
> (§1f ruling 1) — sourced twice over, from the measured bracket above *and* from G16's own printed
> loose-optimization `Maximum Displacement` threshold (0.00529 Å/atom, so 0.05 Å is ~10× single-atom
> convergence noise). 🟢 **LANDED AND VERIFIED BY EXECUTION
> (critic16): `reactant_match(last)` returned `True` for the first time in this project's history,
> energies reproducing exactly. The gate half that could never open, opens.**
> 🟢 **The opt-in bug that let a FAILURE read as a PASS is FIXED** (`guards.py:290` now tests
> key presence; both branch gates consult it) — lead-verified in source; critic16's final
> execution-verification still outstanding.
> 🔴 **BUT THE CLAUSE STILL DOES NOT BIND IN PRODUCTION, AND THIS IS THE THING TO CARRY FORWARD**: it
> has **no live PRODUCER**. `evaluate_p1` is the only caller reaching `irc_direction_ok` and it does
> not supply the `reactant_match` key (P1 has no mapping/reactant wiring and is permanently excluded,
> ADR-112), so **the reactant-match clause is skipped on every production path that currently
> exists** (`tests/test_guard_reach.py:282-294`). **Do not read "`reactant_match(last)` returns
> `True`" as "the gate now checks the reactant match."** The half that could never open, can now
> open — but nothing in production is yet asking it to. Wiring a real producer is a **separate,
> unscoped item** and is now the binding gap in this half of condition 7.
> 🔴 **Still entirely open regardless**: condition 7 binds `last` in the **convergence** branch too,
> which has **no check at all** — proposer12's ruling 2 defines that branch's pass, but nothing
> implements it yet.


`U-56a` (binary feasibility gate for starting S3 production) and `U-56b` (per-attempt success
rate, a planning input measured during S3 wave 1) are SEPARATE quantities (ADR-109, user-ruled).
**U-56a hangs on R-A only** (the 11-atom endpoint), not on P1 or on R-C.

- P1 is **permanently excluded** by user ruling and can never be revived as a measurement path.
- P1's own historical "TS" is now known to be a mislabeled saddle — see ADR-112. Its cost figures
  (527.822 core-h total, 260.000 core-h of that in a truncated IRC) are accurate measurements *of
  the wrong job* and must never be used as an anchor for ring-opening TS costs.
- The gate instrument is `U56-2`: 4 single-ended TS attempts / 3 endpoint certifications
  (§39.39(d)), cut to 3 attempts (all 11-atom) this round — the 21-atom attempt (T21-se) was cut
  and deferred to S3 wave 1, not deleted (its purpose survives as the Δ_shell shell-conditioning
  correction, see §3).
- **Calendar reality, on the record**: at n=3 production attempts, a wave-1 futility stop can only
  detect a catastrophic success rate (95% upper bound on p is 0.632 at 0/3). Separating p=0.2 from
  p=0.5 needs ~15–20 production attempts ≈ 5–10 rounds. This is a calendar fact, not something a
  rule can shortcut — flagged to the user, no response required, just known.
- **"≤3 attempts submitted" is not "≤3 barriers completed"** — these are different numbers and
  must be tracked separately once real attempts start returning results.

🟢 **`u56_2.released` FLIPPED true, 2026-08-21, user-approved.** R-A/R-B's shared reactant cert
(above) triple-verified (proposer9 + critic12 + engineer10) before the flip. Config edit only, code
never self-flips this (`test_code_never_flips_the_release_flag` still green). This admits all 5
`u56_2_items()` into the CPU plan at once (no partial release exists in code — `plan.py:396-507`):
`endpoint_prep_product` (R-A product cert, 11-atom, 192/384 core-h reserved, GATE-CRITICAL — this is
what actually closes U-56a), `endpoint_prep_rc_reactant` (E21/R-C reactant, 21-atom, 1536/1536
reserved at ceiling, cost UNMEASURED — not gate-critical, riding along), `U56_RA_scan`/`U56_RA_qst2`/
`U56_RB_scan` (TS attempts, 700/450/700 reserved — these are C-8-gated at runtime and will refuse
near-instantly for ~0 real spend if their endpoint isn't certified when they run, same shape as P1's
97× margin; the 1,850 core-h figure is a reservation ceiling, not an expected-spend estimate — do not
conflate the two when reporting). New whole-CPU-plan reserved total: **12,709.39 / 21,000 core-h
guard (60.5%)**. Rebuilt package (superseded once, see below): `package_fingerprint ebc9c92f90026415`, `source_digest
4953dce25d98f9b3`, 1639/1639 tests green (fully, not just the known freeze pair — confirmed by two
independent full-suite runs, coder13 and critic12). **SUPERSEDED, 2026-08-21**: critic12 found P1's
plan.py rationale string still said "endpoint_prep_product was removed" (stale) and, while fixing it,
coder13 found a second stale figure in the same string — the wall-hours-mislabeled-as-core-h bug
(already corrected in this doc, §1c) had never landed in the code string or in
`test_p1_excluded_sizing.py`'s docstring/threshold. Both fixed (rationale text, docstring, threshold
now >50×, matches the corrected 97× figure), critic12 independently re-verified the arithmetic
(37×64/3600=0.658 core-h, 64/0.658=97.3×). Rebuilt again, same clean gates, 1639/1639 green.
**Current/live: `package_fingerprint 8ae3630c2e100307`, `source_digest 9d5d7117faf5ec89`.** Use THIS
fingerprint, not the earlier one — the earlier one has the stale-rationale bug (cosmetic/prose only,
does not affect submission correctness, but this is the fingerprint that's actually current). **Verified independently (critic12, direct
source trace): flipping this does NOT re-arm P1.** `payload/P1.sh`/`criteria/p1.py` never reference
any `endpoint_prep_*` output — P1's own C-8 call is hardcoded to bare `{"source": path}` dicts with
no `optimised`/`converged`/`n_imag` fields, which `guards.endpoint_report` unconditionally blocks on;
this is structural, independent of `u56_2.released`'s value by construction. P1's permanent-exclusion
ruling stands untouched. **Submission recipe (already executed by user, 2026-08-21)**: package
`8ae3630c2e100307` copied to cluster, `./run.sh --submit` run — **job is on the real cluster now,
awaiting return.**

🔴 **ADR-114, landed AFTER the above package was built — not yet in any package the user has run.**
Standing user ruling: cluster wall cap is 48 h, not 24 h, applies everywhere without per-item
review. `budget.py`'s `DEFAULT_MAX_WALL_H` 24.0→48.0 (was actually dead/unreached in the live CPU
path already using 48 h via `PROFILE_GUARDS["cpu"]`, per coder13's trace — a latent-not-live fix).
`plan.py`'s `U56_ENDPOINT_21ATOM_WALL_H` (E21) also bumped 24.0→48.0 per the user's explicit
no-exceptions instruction; `U56_ENDPOINT_21ATOM_CORE_H` (1536.0, the actual cost ceiling)
deliberately left unchanged — inert either way since 1536 core-h at 64 cores exhausts at 24 h
regardless of the wall cap. GPU profile's 24 h (unrelated machine, no queue) explicitly untouched.
Full ADR + a lead-added addendum (correcting the ADR's own stale "E21 not touched" claim against
the actual landed code) in `01_DECISION_LOG.md`. **Not yet packaged, not yet full-suite verified
this session, not yet critic-checked — next session's first job before trusting/shipping it.**

---

## 3. Major scientific findings this round (in force, not historical curiosities)

**ADR-112 — P1's "TS" is not the reaction's saddle.** Ω (mode overlap with the intended C–O bond)
= 0.022, essentially zero; the bond is already broken (3.184 Å) at the "TS"; the imaginary mode is
Li⁺ hopping between coordination sites on the already-open product surface (63% of the mode's
squared amplitude is on the Li atom alone). Confirmed independently 3 times (proposer7's log read,
lead's log read, engineer7's independent Ω computation). Consequence: P1's IRC cost anchor is
irrelevant to ring-opening IRC pricing in either direction — do not use it, and do not increase IRC
budgets on its evidence (that just walks further down the wrong path).

**Ω is now the required screening variable for every TS attempt** (not `|ν_imag|`, which cannot
distinguish a genuinely floppy TS from a spectator mode). Ω is now **implemented and wired**
(`sei_pilot/curvature.py::mode_overlap_omega`, `payload/U56.sh` always emits it, no threshold —
U-57 calibration not needed since real cases so far are unambiguous). This closes the exact blind
spot that let P1's failure go undetected for two rounds — before this, zero production paths
computed Ω at all.

**ADR-111 + addendum — the IRC completion gate (C-2/condition 7).** A truncated IRC (stopped by
`maxpoints`, still descending, no plateau) can satisfy C-2's literal wording while connecting the
TS to nothing. Fixed: an IRC's termination reason is emitted as data; a max-points termination only
counts as connection-established if **B+** agrees — two terminal optimisations per direction, from
two different points on the truncated path, must land on the same minimum (no threshold — the two
points are on the same descending branch by construction). R-A additionally gets ONE real converged
IRC (Option A) in the same run, calibrating B+ against ground truth for the one reaction where both
exist. Risk accepted knowingly: B+ can miss a bifurcation past the last sampled point; if R-A's
calibration later disagrees with its own B+ result, that round's other attempts become
retroactively `indeterminate` (~2,300 core-h at risk, discovered after submission) — judged the
right bet against permanently losing a production attempt every round otherwise.

**Δ_shell (shell-conditioning correction) does not saturate and depends on an unmeasurable input.**
Measured 0.366 eV (n=1→2), 0.190 eV (n=2→3) — decelerating but not converged, and the reaction's
own thermodynamic sign flips between n=1 and n=2 (single-ligand clusters are not small versions of
the real system). This collides with U-65 (experimental Li⁺(EC) coordination number does not
converge — already disqualified as a validation target). Fix (adopted, cost 0, reuses the F-1
declared-uncertainty-axis pattern from U-72's K_sp treatment): report a shell-averaged rate with
spread rather than picking one n. A full DFT TS attempt at n=3 is **not submittable** (ceiling
exceeds guard alone) — Δ_shell can only ever be DFT-measured at n=1,2. Affordable extension: a DFT
single-point energy ladder along the free GFN2 path (no TS optimisation/Hessian/IRC), self-
calibrated against the real n=1,2 attempts.

**A 33× cost-accounting error was found and fixed (ADR-110).** A shipped xtb cost anchor
(`config/b0_conformers.json`) billed 12 threads for a job that could use ~4 (thread scaling
saturates there) — same failure shape as ADR-107 (array task duplication): a job that completed
normally and looked like an ordinary measurement was actually "arithmetic about capacity nobody
used." **Binding rule going forward: every xtb Item must declare `cores_per_task` explicitly** (a
small integer matching the real `-P` thread count and any `xargs` concurrency) — `None`/whole-node
is forbidden for xtb Items specifically (NOT for DFT/G16 Items, where a whole-node job genuinely
uses its cores, so work≈charged there by construction). One declared-cores field alone swings a
guard ceiling by up to 16×.

**Indeterminate verdicts are tagged CHEMICAL/BUDGET/UNKNOWN/MIXED, and `1/p` may only be computed
from the chemical class — IMPLEMENTED** (`guards.classify_indeterminate`, wired into `U56.sh` and
the reply). Tight caps can manufacture budget-class `indeterminate`s (hit `maxpoints`/wall-cap/
`maxcycles`) that look identical to chemistry-class ones (Ω below floor, B+ disagreement) if
pooled — inflating S3's measured cost for reasons that are the team's own purchasing decisions. A
large budget class means the caps are wrong (engineering fix); a large chemical class means the
pipeline is wrong (stop and fix the method). A missing completion record is its own `unknown`
class, never forced into either real one. 🟢 **R-5 FIXED**: `classify_indeterminate` no longer
substring-mines prose for its class — the clauses emit structured cause tags directly, string
matching survives only as a fallback for free-text callers (critic10 found it, coder11 fixed at
root, two new tests pin `cause_class` independent of message wording).

**Five classes now** (§39.59(c) base three + two added this round, each justified by a DISTINCT
PRESCRIPTION — the test the taxonomy is built on: does folding this into an existing class send
someone to the wrong lever?): **CHEMICAL** (the reaction didn't resolve → fix the method),
**BUDGET** (a cap stopped it → loosen the cap), **PROTOCOL** (§39.68 — our procedure was wrong →
fix the procedure; e.g. the GFN2 pre-stage's frame-0 convergence check), **`engine`** (§39.69 —
the calculation couldn't complete for numerical reasons internal to the electronic-structure
method AT A GEOMETRY THE PROTOCOL LEGITIMATELY REQUESTED → change SCF setup/convergence/guess
propagation; IN: SCF non-convergence, basis linear dependence, integration-grid failures; OUT:
out-of-memory→BUDGET, malformed deck→PROTOCOL, a geometry the protocol shouldn't have
requested→PROTOCOL — that clause is what makes the boundary decidable), and **`unknown`** (a
missing completion record, never forced into a real class). None may feed `1/p`'s denominator
except CHEMICAL. **Queued addition**: record which caps were active alongside each measurement —
a `p` measured under one cap regime isn't comparable to one measured under a looser regime later,
and without this nothing would show it if the two got pooled.

**Ω itself stays emit-only** (no calibrated threshold, U-57 open) — but a SEPARATE, threshold-free
**spectator test** now gates funding: block iff the mode's single most-displaced atom is outside
the reaction's declared coordinate set AND its share exceeds the summed share of atoms that ARE in
the set (compares two quantities from the same mode, no constant). Blocks P1's saddle 30.6×
unweighted / 14.3× mass-weighted — under both Ω definitions. Deliberately permissive: a false
block loses a whole reaction attempt, a false pass only loses core-h and still surfaces as
`indeterminate` downstream — so an unmeasured mode, unparseable mapping, or geometry mismatch all
PASS rather than block. **Reactions now declare a `mechanism` coordinate list** — R-C (genuinely
2-D, Li translocates as part of its real mechanism) declares `[["Li","O_ether"]]`; R-A/R-B
deliberately do NOT (at 11 atoms Li has nowhere to go, so its motion there IS spectator motion —
exactly how P1's saddle was caught). Declaring the coordinate everywhere would silently disarm the
test on the cases it exists to catch.
A real implementation bug was caught while wiring the raw Ω calculation (separate from the
spectator test): a shortcut definition (no mass weighting, un-normalised displacement) agrees with
the correct one on C/O bonds (masses close enough that weighting nearly cancels) but diverges ~20%
on Li-involving bonds — exactly the coordinate class Ω exists to catch. Both values are now pinned
as tests, the wrong one only as a negative case production can never return.

---

## 4. Team roster and standing rules

## 팀 상태 (Team Status)
> Machine-parsed by `src/session_digest/docparse.py::parse_team` — keep this as a table with
> exactly `name | status | task` columns. Content in English per the language policy; only the
> Korean substring in the heading is load-bearing for the parser.

| teammate | status | task |
|---|---|---|
| coder14 | stopped | Track A CLOSED — terminal_status fix, IRC parser fixes, guards.py arc-length gate, SIGTERM trap, both diagnostic tools (4 decks), citation hygiene+uniqueness test, package rebuild. Stopped 2026-08-21, end of day. |
| proposer10 | stopped | Rulings §39.113-117 (C-2 branch-b gate, diagnostic design, 3rd stable=opt target, R-B minimum tag, R-B 3rd problem). Track B items 5/6/7 (final R-A/R-B/GSCAN2 verdicts) still OPEN, held pending diagnostic results. Stopped 2026-08-21, end of day. |
| engineer11 | stopped | Priced all 4 diagnostics (§R39.78, ~1-55 core-h combined). Stopped 2026-08-21, end of day. |
| critic14 | stopped | 4 review rounds (04_REVIEW_LOG.md 16-24차), rebuild independently verified (package `a7b668127d052e33`, 0 auto-resubmit risk). Stopped 2026-08-21, end of day. |
| proposer11 | stopped | Ruled §39.118-123 on the returned diagnostics: wavefunction hypothesis FALSIFIED (residual gap named), MO-coefficient artifact reading, stage 3 MUST RUN, stage 4 MUST RUN and promoted, Track B items 5/6 ruled, item 7 still open. 🔴 Its "U-56a confirmed closed" conclusion was RETRACTED the same day (ADR-116 / §1e, caught by critic15) — U-56a is OPEN. Delivered 2026-08-22, stopped. |
| critic15 | stopped | Review 25차 배치: re-derived every load-bearing figure from raw logs (all reproduce); found the ADR-116 U-56a false-closure BLOCKER, three resubmit-recipe defects, the unpriced stage-4 `recorrect=never` silent-drop branch, and the zero-charge-variance scoping flaw. Delivered 2026-08-22, stopped. |
| engineer12 | stopped | §R39.79: PBS 23731675 root-caused as a SUBMISSION failure, §R39.78 re-scored against measured reality, two-separate-job resubmit sizing, clean-restart ruling, hand-submitted-and-hardened recommendation, budget impact. Delivered 2026-08-22, stopped. |
| proposer12 | stopped | §39.124 (R-9, reverse arm): cause re-derived from primary sources (gap 1.02199 arc, n=5 < 10, `connection_established_via` literally absent); candidates A/B/D ruled, C rejected in both variants; acceptance criterion + new `arc_length >= 4.27` `[ESTIMATE]` clause; stage-4-first sequencing on inference grounds; `maxpoints=30` ruled over engineer13's 15. Found the condition-7 spec-vs-code gap (no reactant-match check in `guards.py`) and the reverse-B+ flatness caveat. Named an external anchor for Track B item 7. Delivered 2026-08-22, stopped. |
| critic16 | stopped | 26차 배치 **BLOCK**: falsified §39.124(1)(b) at the source (it measured B+ START geometries as optimised endpoints; real separation 0.0003 Å, not 0.17 Å), voiding D(i)'s 30.0-49.9 core-h and the shipped docstring/test rationale; found `guards.reactant_match()` could never return `True` (U-56a could never close) and supplied the measured 0.0005 Å / 1.70 Å bracket that unblocked the tolerance; confirmed all three lead tool defects while correcting the lead's framing of one (ADR-114 wall-cap breach, not ADR-117 mismatch); ruled condition 7's reading; vindicated `maxpoints=30` and the 4.27 floor on grounds nobody had stated. Then 27차: execution-verified all three closers and ruled **R-9 CLOSED**, with the `shutil.copyfile` guard tracked separately as a non-blocker. Delivered 2026-08-22, stopped. |
| coder15 | stopped | D(ii), delivered. `guards.reactant_match()` + `U56.sh` wiring + `tests/test_bplus.py` 🔴 landed 15:22 **before critic16's review, against the ruled ordering** (code read the right geometries; its docstring/test rationale baked in the since-falsified finding (b)). Then proposer12's `REACTANT_MATCH_TOLERANCE_ANG = 0.05` Å (`last` only) in final three-way form, then all three closers: the `"reactant_match" in d` opt-in fix (a failure had been reading as a pass), the no-PRODUCER documentation, and the three builder defects (`total_cores=64`, explicit `maxpoints=30`, direction-aware cost string) — direction keyword correctly left alone. 1737 tests, 4 unrelated failures. D(i)/`BPLUS_REOPT.sh` fully dead. Delivered 2026-08-22, stopped. |
| engineer13 | stopped | §R39.81 (R-9 pricing): measured anchor re-derived from this reaction's own logs (0.341-0.342 arc/frame, identical across both arms; 1.92-3.63 core-h/point) — no extrapolation, does not repeat the T21-se failure. D 30.0-49.9, A 17.3-32.7, B 25.0-47.2 (up to 94.4 with a retry) core-h; realistic paths 47.3-82.6 / 126.4-194.2 against ~8,240 core-h margin. Confirmed cost is NOT binding, requested no re-cut, and independently withdrew its `maxpoints=15` sizing in favour of proposer12's 30. Delivered 2026-08-22, stopped. |
| critic17 | stopped | Batches 28-46: every reverse-arm and wave-1 build reviewed. Headline catches: `-a` grep BLOCKER, §39.130 misquote, fixture-channel workaround, wrong-sibling hazard, nosymm 16/16 audit, §39.133 cold confirmation, stopped_after_stage retry-loop BLOCKER, staged aggregate cases. 46차: amended own 44차 finding (race artefact, delivered code never violated §39.140). SHUT DOWN 2026-08-25 (session end; successor = critic18). |
| coder16 | stopped | Delivered the entire reverse-arm + wave-1 build arc: idempotency fix through candidate A/B/EulerPC/DVV/B+ tools to the wave-1 slate (T21-se stage-1 + R-B + stage 0), stage-limit flag, staged class wiring, fingerprint guards, R-10 renderer fix, sealed-file support; two package rebuilds, final `b94510460851012e`; suite 1738→1817 fully green. SHUT DOWN 2026-08-25 (session end; successor = coder17). |
| proposer13 | stopped | §39.125-140 + §39.137 sealed targets: eleven-plus rulings from the returned diagnostics through condition-7 closure to the full wave-1 scope and the staged taxonomy. SHUT DOWN 2026-08-25 (session end; successor = proposer14). |

**HANDOFF NOTES from critic17 (recorded verbatim-in-substance by the lead at shutdown, 2026-08-25)**:
(1) 🔴 Anyone citing review batch 44: the 46차 amendment RETRACTS its CLASS_SEVERITY finding (race
artefact — the delivered code never violated §39.140); the surviving lesson is only that
order-insensitive assertions can't discriminate a ruling from its inverse. (2) `staged` has never
fired at runtime — T21-se stage 1 is its first real halt; read the returned `terminal_status.json`'s
`cause_class` directly, don't infer from tests. (3) A fingerprint-guard refusal: check the two named
false-alarm causes in the message first; removing the guard is never the fix. (4) T21-se
cap-without-finishing = STOP AND RE-SCOPE per `attempts_manifest.json` slot 1 — read before sizing any
follow-up. (5) Stage 0's blindness holds only while every code reference to
`stage0_sealed_targets_T1-T4.json` stays a comment — any future `open()` breaks pre-registration
retroactively. (6) Standing limitation: critic17 verified artefacts against cited rulings, never
independently re-derived §39.136's science or §R39.88-91's budget.
| engineer14 | stopped | §R39.82-87: priced candidate B (f-table, then re-derived at f=0.20/maxpoints=70: 134.4-254.1 core-h ceiling), EulerPC (192.0-730.0, named the silent-HPC-fallback foot-gun), DVV (100.0-1090.0 ceiling-only, honest no-targeted-figure), the B+ closers (10.32-14.66 core-h reserved/job, `[MEASURED]` bracket); §R39.82-90: all reverse-arm + wave-1 pricing, guard reconciliation (margin 8,290.61; stale U56-2 table line; ~2,974 core-h locked-but-recoverable). SHUT DOWN 2026-08-25 (user decision; successor = engineer15). |

**Retired 2026-08-21, all clean handoffs**: `proposer9`→`proposer10`, `engineer10`→`engineer11`
(new spawn, not a replacement — engineer10 had already stopped earlier), `critic12`→`critic13`
(model-switch)→`critic14` (Opus, user directive), `coder13`→`coder14` (model-switch). See
`01_DECISION_LOG.md`/this file's history for each predecessor's final deliverables.
**Retired/burned, do not reuse**: proposer7/8/9, engineer7/8/9/10, critic9/10/11/12/13,
coder9/10/11/12/13, and everything from earlier rounds (proposer4–6, engineer4–6, coder2/6/7/8,
critic3/7/8).

**RESUME — read this first (updated 2026-08-22)**: (1) The diagnostics were submitted and came
back PARTIAL — see §1e. Stages 1/2 answered their question (ADR-115); stages 3/4 still need running.
(2) **The resubmit is decided but NOT executed** — it is waiting on the user, and §R39.79's script
skeleton must NOT be submitted unmodified (the `%nprocshared=1` defect, §1e). (3) Track B items 5/6
are RULED (ADR-116); item 7 is open but was never gated on this diagnostic — do not report it as
pending-on-diagnostics. (4) **U-56a is OPEN** — the same-day closure claim was retracted (ADR-116, §1e). **Stage 4 gates it,
and stage 4 alone is not enough**: the reverse arm needs a longer/redone IRC to lift `low_confidence`,
which is unscheduled and unpriced.
(5) One tiny comment-only diff (`cli.py`, the absent-asymmetry note) still sits on top of the live
package `a7b668127d052e33`, intentionally not rebuilt — batch it with whatever the next real code
change produces, don't rebuild for it alone. (6) Don't respawn coder until there is a real code
change to make; nothing in ADR-115/116/117 requires one — the resubmit is a hand-run shell script,
not a `src/` change. (7) All model spawns should explicitly set `model: "sonnet"` except critic,
which the user wants on opus — standing instruction since 2026-08-21, don't ask again unless they
change it.

**Language policy (user directive, 2026-08-20)**: all team output (SendMessage content, document
sections) and all lead↔team communication is in English. Lead's direct replies to the user stay in
the user's own language (Korean).

**Verifying a teammate is actually spawned/idle**: use `tmux list-panes -a -F '#{pane_id}
#{pane_title}'` and `tmux capture-pane -p -t %N`, not `ListAgents` (unreliable in this build's
earlier version) — a live teammate has its own pane; an `idle_notification` message means it *was*
idle at that instant, but it can pick up queued work again immediately, so re-check the pane before
treating it as safe to terminate. A tmux pane being gone does not by itself prove the underlying
process is gone either — cross-check with `ps aux` when it matters (used to confirm coder9/critic9
were fully gone, not just pane-closed).

**Standing engineering rules earned this session** (each caught a real defect at least once;
none were caught by the author's own care — always by a peer, or by running the thing):
1. **Unit-in-the-cell**: every cost figure states what it measures in the same cell — reference vs
   raw-KNL core-h, dev-box vs KNL (with the κ conversion attached), `work` vs `charged` core-h, and
   the job/route the number actually describes. A number divorced from its route measures an
   unknown job (this is exactly how both the 33× xtb anchor and P1's void IRC anchor happened).
2. **Declare cores explicitly on xtb Items** (never `None`) — the load-bearing half of ADR-110.
3. **Assert field presence, don't rely on defaults** — an over-report gets refused by the guard and
   investigated; an under-report passes silently and surfaces later as an allocation surprise. The
   more dangerous direction, and the one with no test behind it by default.
4. **Hierarchical-with-overlap**: buy the expensive method once where affordable, run the cheap
   method on the same case, let the overlap calibrate. Used 3+ times this round (SP ladder, B+/R-A
   calibration, the deferred maxpoints-by-|ν_imag| idea).
5. **Gate-before-you-pay**: a free comparison against a number the previous pipeline stage already
   emits, placed immediately before the expensive stage (reverse-scan gate, Ω gate, IRC-completion
   gate) — zero implementation cost, each avoids hundreds to thousands of core-h per firing.
6. **An author's own spec is not a spec until it has been run against a case it could fail** (or
   read by whoever has to implement it) — the only control this round that would have caught every
   self-authored defect (G-SCAN-2's original wording, a Δ_shell matched-method violation, a biased
   5-point sampling design, an unread route string). The other five rules are static labels; this
   one requires actually executing or independently re-deriving the thing.
7. **Report success/completion rates with their real denominator, never pool survivors with a
   silently-shrunk attempt count** — hit 3 times this round in different guises (seed-death
   dropping out of a spread calculation, a gate that selects for path agreement contaminating its
   own noise estimate, packing efficiency conflated with failure rate). Fix pattern each time:
   pre-register the attempt list before dispatch (payload/P3.sh's existing pattern), record an
   explicit failure marker rather than a missing file.

**Never delete files without the user's permission** — standing restriction from when the user
handed over the lead role mid-session; outlives that window. Never modify or delete anything under
`cpu_machine_pilot_results/` (returned cluster results tree) — read-only, reference only. Tests may
never read the user's results tree (R-13); the lead reading it directly for one-time verification
is fine and has been done repeatedly this session — that is not what R-13 forbids.

---

## 5. Open items (not urgent, tracked so they aren't rediscovered)

## 알려진 미해결 위험 (Known Risks)
> Machine-parsed by `src/session_digest/docparse.py::parse_risks` — keep bold `**R-NN**` ids and
> `- [ ] **R-NN**` open / `- [x] ~~**R-NN**~~ ...` closed format (bold id required INSIDE the
> strikethrough — `parse_risks`'s id regex is bold-only and won't see a plain `~~R-NN~~`; this
> exact mismatch silently dropped R-5..R-8 once, caught by critic10 and lead independently, see
> 04_REVIEW_LOG.md). Content in English.

- [ ] **R-1** B+'s bifurcation check only catches a branch splitting BETWEEN its two sampled
      points on the IRC path — a branch past the last sampled point is invisible to it. Only
      R-A's real converged-IRC calibration bounds this, and only for that one reaction.
- [ ] **R-2** If R-A's calibration IRC later disagrees with its own B+ verdict, every non-gate
      attempt already submitted that round becomes retroactively `indeterminate` — discovered
      after submission, not before. Accepted deliberately (§3), not hidden.
- [ ] **R-3** The P6 gate (`collect.py`'s `agree` check) excludes `cores_observed`, the only
      kernel-measured value, from its validity decision — structurally the same hole as ADR-107.
      κ=1.218 is confirmed unaffected today; the gap bites on the next P6 re-run if unfixed.
- [ ] **R-4** Δ_shell's shell-averaging fix assumes the solvation shell interconverts slowly
      relative to the reaction, so a static average over n is meaningful — this assumption is
      untested and is the point proposer7 named as the one to attack.
- [x] ~~**R-5**~~ **FIXED**: `classify_indeterminate` mis-tagged a B+ bifurcation disagreement as
      `budget` instead of `chemical` (substring-matched `"truncated"` in prose before checking
      B+-specific structured fields — critic10, direct execution). Fixed at the root: the clauses
      now emit structured cause tags and the class is derived from those; the string classifier
      survives only as a fallback for callers passing free text. Two tests added: one pins
      `cause_class == "chemical"` for the bifurcation case, one asserts the class does not depend
      on message wording (closes the exact gap that let it ship — the old test asserted only
      `status`). Confirmed by coder11, suite green (Ran 1477, failures 2 freeze-signal only,
      skipped 14).
- [x] ~~**R-6**~~ **FIXED**: `gfn2_scan.parse_scan_log` could silently drop a whole frame on a
      mismatched atom count (critic10, reproduced by execution). Fixed: advances by what was
      actually READ, not the declared count, plus a `DESYNCHRONISED` warning.
- [x] ~~**R-7**~~ **FIXED**: `collect_u56` now promotes `irc_refusals` to `warnings[]` per Rule 13;
      STATUS also says so explicitly when no direction ran.
- [x] ~~**R-9**~~ 🟢 **CLOSED 2026-08-22** (critic16 final verdict; §1f). The reverse-arm work item
      went from *unscheduled, unpriced, unbuilt* to ruled, priced and code-verified in one round:
      D(i) cancelled outright (its 30.0-49.9 core-h was priced against a finding that had measured the
      wrong files), `REACTANT_MATCH_TOLERANCE_ANG = 0.05` Å ruled from data already on disk, the
      acceptance criterion split across both condition-7 branches, and candidates A/B sequenced and
      priced at ~181 core-h worst case (~2.2% of margin). 🔴 **Closing R-9 does NOT close U-56a**
      (condition 7 still fails on the reverse arm today; nothing has run), and three carry-overs
      remain outside it — see §1f: no live producer for `reactant_match`, `minimum_distinctness`
      unwired, and the false idempotency claim to fix before candidate A is built.
- [x] ~~**R-8**~~ **FIXED, and critic10 under-scoped the original finding.** critic10 judged the bad
      `"break"` default unreachable (an earlier gate refuses on a missing verdict file) — but the
      default applies PER KEY, and a healthy run legitimately derives "no direction" for a
      non-monotonic coordinate, so "could not derive it" and "it's broken" were indistinguishable
      by construction: reachable on a clean run, not just a corrupted one. Fixed both halves:
      default is now `None` and COUNTED (not silently defaulted), and the payload's broad `except`
      around the whole derivation loop is gone, so a verdict missing a forward profile says so
      instead of silently yielding an empty map. Cost stated plainly by coder11: `None` loses the
      one-sided bound on that coordinate, so P1 wouldn't be caught through it in that failure mode
      either — the gain is the loss is now visible in a tally, not a silent pass.
- [ ] **R-10** `session_digest`'s two real-docs tests broke, found while reviewing coder16's
      2026-08-24 delivery (unrelated to it — pre-existing, not caused by this round's edits):
      (1) `test_real_docs_parse_sanely` failed because `docparse.py`'s `re.match(r"\*\*Current
      phase\*\*...")` requires the marker at line START, and `05_STATE.md`'s summary paragraph had
      drifted so `**Current phase**:` sat mid-line — **FIXED by the lead, 2026-08-24**: split onto
      its own line (see line ~6 of this file). (2) `test_real_render_does_not_crash_and_stays_short`
      still fails: rendered digest is 85 lines, over the 80-line cap — **NOT fixed**, needs a coder
      to look at `session_digest`'s render/truncation logic vs. how much this doc (roster + open
      items) has grown; not scoped further by the lead, per the standing rule against inventing
      implementation scope.

🔒 **Standing check, coder11's own request to record**: three separate "measured but unread" bugs
surfaced in code coder11 wrote THIS SAME ROUND — the rcfc `copied` flag, the GFN2 pre-stage's
`forward_rc`/`reverse_rc`, and the direction map's silent-empty default. Not a coincidence, and not
something a test catches by itself (a test asserts a field's *value*, not that anyone *reads* it).
**For every field added to a record, name its consumer, or say in the comment that there is none
yet.**

🔒 **Companion standing check (coder11), the mirror direction**: `rc=0` hid the L1110 segfault;
`rc=1` sits on 17 P5 rows that genuinely converged — zero-exit establishes nothing either, just as
non-zero-exit alone establishes nothing without content (§39.69(d)). **For every field READ, say
what it does and does not establish** — the companion to "for every field added, name its
consumer" above. 🟢 **LANDED in code, not just this document**: recorded in `criteria/g16.py`'s
module docstring, beside the parsers it constrains (same reasoning as why the docparse convention
failed living only in prose) — states all four measured cases together (`rc==0` hid a segfault;
`rc!=0` sits on converged rows; `normal_termination` reads true on opt alone with zero
frequencies; a route asking for `freq` establishes nothing about what ran) plus the rule: **stage
completion is read from output evidence only.** A test asserts the rule text is present, so it
can't be quietly dropped.

🔒 **REPORTED ≠ ROUTED (coder11, self-audit, not code)**: found two questions marked "routed" in
own status reports (B+'s calibration exemption, P5's cost-denominator question) that were never
actually sent to proposer7 — only mentioned to lead/critic10, who don't rule methodology. Cause
named precisely: treated *"I have told someone about it"* as equivalent to *"it is routed"* — they
are different acts, and the difference is whether the recipient can actually decide. **Worse than
an open question**: an open question is visibly open and gets chased; a question everyone believes
is in flight is tracked by nobody. Both now genuinely sent (§39.77/§39.78 above are the answers).
Going forward: "routed to X" means a message exists and which one; if only mentioned, say "flagged,
not yet routed." Same shape as `measured but unread`/`agreement is not identity` — a status word
doing less work than its plain meaning implies, this time in reporting rather than code or
analysis. 🔒 **proposer7's addition, explicitly not letting this land as coder11's failure alone**:
"a question everyone believes is in flight is invisible, and it stays invisible because every
participant's model of it is consistent — the rollup says 'routed' and the recipient list is never
compared against the ruling authority." The P5 question specifically appeared in SIX status reports
before the audit caught it — proposer7's own words: "the failure is not his — six reports carried
it and no reader asked who was meant to rule it, including me."

🔒 **A RELAYED CLAIM NEEDS THE SAME CHECK AS AN ORIGINATED ONE (coder11)**: propagated a since-
retracted paragraph from a lead relay (the B+ "cost × P(IRC converges)" line, see §39.77/§39.79
above) to engineer8 without checking it against the spec first — "I check what I send against what
is actually ruled when the claim is mine; I did not when I was passing someone else's along."
Fourth instance of a status/claim word doing less work than it appears to. Sent an explicit
retraction once caught (even after engineer8 had already independently resolved it directly with
proposer7) — worth sending anyway rather than skipping it as redundant, since the recipient can't
tell in advance whether it already resolved.

🔒 **§39.76 (proposer7) — AGREEMENT IS NOT IDENTITY, the analysis-side twin of the above.**
*Validating a number against itself or its neighbors instead of against its definition.* Two
instances THIS SAME AFTERNOON, on proposer7's own output: §39.74 verified a MECHANISM against an
artefact and asserted a SCOPE the artefact couldn't support ("first job ever to need a Hessian");
§39.75 verified some ratios were mutually CONSISTENT and asserted they were THE QUANTITY
`r_composite` names (an opt-only ratio, cited as confirming an opt+freq one). **Consistency is
evidence about a number's precision, never evidence about what the number measures.** Test to
apply: *"if this number were NOT the quantity I'm claiming, would it look any different?"* — if NO,
the agreement has zero discriminating power and is circular; if YES, it's real evidence. The same
principle was already written down in this project's own §39.29(e) (on an earlier 0.30 eV error) —
proposer7 failed it twice in one afternoon after having authored it, which is itself the finding:
**a control that has to be remembered is not a control** (4th independent route to this conclusion
this round, alongside: the check must not originate with the author · unit-in-the-cell · the
question must arrive with a cheap answer attached).
**Paired with `measured but unread`**: same defect at two stations — `measured but unread` is
coder11's execution-side version (a value exists, nobody looks at it); `agreement is not identity`
is the analysis-side version (a value IS looked at, what it measures is assumed). Both share the
only remedy that's repeated all round: **put the discriminating fact in the cell next to the
number** (a `stages_completed: [...]` field would have made §39.75 unmissable regardless of what
the boolean is called; a `converged` field alone cannot, even renamed, if the next stage added
later isn't reflected in it). This is the shape of fix relayed to critic10 for the `converged`
field, not just a rename.

## 미확정 (Open Items)
> Machine-parsed by `src/session_digest/docparse.py::parse_open_items` — keep the checkbox format
> (`- [ ]` open / `- [~]` partial / `- [x]` closed) and bold `**U-NN**` ids. Content in English.

- [ ] **U-56b** — success-rate calendar: separating p=0.2 from p=0.5 needs ~15–20 production
      attempts ≈ 5–10 rounds; no rule shortcuts this, flagged to the user, no response needed yet.
- [ ] **U-65** — experimental Li⁺(EC) coordination number does not converge; collides with
      Δ_shell's shell-averaging fix (§3) which assumes shell-exchange is slow relative to reaction
      — that assumption is itself untested.
- [ ] **U-57** — Ω threshold calibration; not currently needed (real cases are unambiguous) but
      remains open for future marginal cases.
- [~] **U-56** — split into U-56a (gate, hangs on R-A only) / U-56b (rate, measured during S3
      wave 1) per ADR-109; U-56a's instrument (U56-2) is BUILT (coder14 closed Track A; critic15 verdict OK) and
      remains behind its `released:false` gate. U-56a is OPEN on **condition 7**, which now needs
      stage 4 (forward) AND R-9's reverse-arm work (§1f) — not just the instrument.
- [ ] **U-58** — reaction-energy error can be bounded via thermodynamic cycles; barrier (ΔG‡)
      error cannot, by any method currently in the pipeline. Still open.
- [~] **U-54** — whether a proven production-size TS method exists; partially answered this round
      (B+ + Ω-gating gives a working instrument for the 11-atom gate case) but not yet demonstrated
      at 21-atom production size, since T21-se is deferred to S3 wave 1.

- **P6 gate scope gap** (κ=1.218's own validity gate): `collect.py`'s `agree` check compares three
  self-declared values and excludes `cores_observed` (the only kernel-measured one) — same
  ADR-107 hole shape. **κ=1.218 itself is confirmed safe** (lead verified all three real P6 runs
  have all four values agreeing) — this is a fix for the NEXT time P6 is re-run, not urgent now.
  Fix touches both `collect.py` and `P6.sh`'s note-generation (the rule text is also baked into the
  artefact without `cores_observed`, so fixing only the code re-diverges from the artefact).
- **U56-2 minor cleanup before `released=true`**: `b0_reactions.json`'s docstring still says "4
  attempts" (cosmetic); no test drives `U56.sh`'s `resolve()` end-to-end (every C-8 test injects a
  fixture instead) — recommended to close once before release, not blocking now.
- **`crest_status.json`** in P1's job directory has never been opened — might show the CREST
  omission (which exposes T11-qst2's cost anchor) is a reporting gap rather than a missing stage.
  Two-minute check, unclaimed.
- **Per-reaction `maxpoints` sizing from measured `|ν_imag|`** — mechanism plausible, deliberately
  not adopted; needs 2 genuinely completed IRCs to calibrate an exponent that doesn't exist yet.
- **Bundled cluster-data ask for the user, not urgent**: P3's packing efficiency + the older ≥944
  core-h floor question (`qstat -x -f 23631761[]` or site accounting) — ask once for both together
  whenever cluster access is next convenient, not two separate asks.
- **R-A/R-B become the project's first real anchor pair** once R-A's attempt lands — re-derive
  every DFT TS cost row from actual results rather than the current estimate stack (engineer8's
  first real task). Report per-reaction, never pooled; if R-A/R-B disagree by >~2×, that
  disagreement is itself the first measurement of reaction-to-reaction spread, a quantity every
  current anchor silently assumes is small.

---

## 6. Durable facts from earlier rounds (compacted from history)

- **The array task-dispatch defect (ADR-107)**: P1b and P5 array jobs ran their *entire* work list
  on *every* task instead of one task per index, racing on shared paths. Root-caused, fixed, fix
  locked behind `tests/test_array_task_split.py` (reproduces the actual concurrency, not just the
  symptom). Cost of the incident: ≥944 core-h measured floor, real total higher (unrecoverable from
  the returned tree — would need PBS accounting to pin down exactly, not asked of the user yet).
- **Solvent history**: production solvent is PCM ε=18.5 (EC:EMC 3:7 conventional value, user-ruled
  domain knowledge, ADR-104/106) from B1 onward, and from B0 too since ADR-108 superseded the
  B0-stays-SMD half of ADR-104. 🔴 **User re-confirmed directly, 2026-08-20, absolute and standing
  until they say otherwise: SMD is no longer used AT ALL, PCM ε=18.5 is FIXED — do not change
  either without explicit future user instruction.** A round accidentally ran in acetonitrile ε=35.7
  (ADR-105) and every chemical value from it is void — cost figures from that round were still
  usable, since ε doesn't change core-h. `deck_verification.json` must be read before trusting any
  cost figure quoted from a PCM-deck round — the reading rule exists because a silently-ignored PCM
  block yields a low-biased (looks-usable) cost (ADR-108). Note: P5's stale `level` label reading
  "SMD" (criteria/p5.py:28-29, being fixed per §1a finding 5a/critic10) was ALREADY wrong before
  this reconfirmation — the actual route has always run PCM this round; the label bug never meant
  SMD was actually used.
- **Build/freeze discipline (ADR-057, ADR-086)**: `dist/` (the shipped tarball) is frozen while
  `src/` moves ahead; verification must extract and run the actual tarball, not just read source.
  The test suite encodes the freeze as intentionally-red tests (`test_build_stamp` etc.) — never
  "fix" these by reverting the source change that made them red; they clear together at the next
  authorized rebuild. If the freeze-signal failure count changes, that is a new event to report,
  not silently absorb.
- **Provenance labelling discipline**: every number carries `[MEASURED]` / `[ESTIMATE]` /
  `[LITERATURE]` / `[UNVERIFIED PROVENANCE]` / `[FIXTURE]` / `[USER-DOMAIN]` / `[MEASURED, FLOOR]`.
  A missing label doesn't produce a visible gap — it produces a silent mislabel on whatever token
  looks most authoritative, which is worse. See `06_GLOSSARY.md` for the full label table.
- **A guard has four properties, not two**: existence, correctness, REACH (is it actually called),
  and SATISFIABILITY (can it ever pass/fail as designed). This round added a fifth: SCOPE — a guard
  can have all four and still cover only half of what its name claims (found repeatedly: the
  UltraFine grid check covering only 2 of 8 routes, C-2 not distinguishing a truncated IRC from a
  connected one, the P6 gate's cores_observed exclusion).
