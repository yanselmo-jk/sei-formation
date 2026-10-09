# coder6 → successor. B0 execution package, session of 2026-08-19.

> **A separate file from `HANDOFF_TO_LEAD.md` on purpose.** That file is coder2's and is 3,000+
> lines; appending would bury this. 🔴 **Read `HANDOFF_TO_LEAD.md` §0 and §45 first anyway** —
> everything in it still holds. This file is the delta for one session.

---

# 🔴 READ THIS FIRST — live state, what is deliberately absent, what is merely undone

> Structure copied from `01_DECISION_LOG.md`'s READ THIS FIRST block, which is the most useful
> shape in these documents. **If anything later in this file conflicts with this block, the block
> wins.**

## LIVE
```
source_digest   4a484eb71ef2b36d      ← identity. sha256 changes every rebuild; do NOT use it.
tests           1122 OK (skipped=8)   (743 at the start of this session)
[6/7] gate      8 tests OK  ·  [stamp] ✅  ·  dist/ clean, no .stale
suite wall      ~30 s on a quiet box. 32 s at load 8 is MACHINE LOAD, not a regression.
```

## 🔴🔴 DELIBERATELY ABSENT vs MERELY UNFINISHED — the distinction that will cost you if you miss it

**A successor "fixes" the first kind. Do not.**

| thing | status | 🔴 if you "fix" it |
|---|---|---|
| `b0_plan.size()` returns **null totals** | **DELIBERATE** | Unit costs are MEASURED (by B0's own first species, and by engineer5's tables). Inventing one makes every downstream total a fabrication *that the guard check then certifies*. |
| `check_against_guard()` returns `fits: None` | **DELIBERATE** | It cannot certify a batch it cannot price. Rule 18. |
| `solvent.DESCRIPTORS = {}` | **DELIBERATE** | Empty, **not absent**. Five literature values we do not hold. `solvent_line()` RAISES rather than falling back to acetonitrile — which is what RT-1's P1 actually did. |
| `acceptance.omega_threshold = null` in `b0_reactions.json` | **DELIBERATE** | C-3: do not hard-code Ω_min. `null` means *report, do not gate*. |
| `curvature` `verdict: None`, no correlation cutoff | **DELIBERATE** | "holds vs excluded" is proposer5's judgement. Hard-coding a cutoff is how −100 cm⁻¹ got into M2. |
| `arm2` extended path unwired | **DELIBERATE** | Ruling (a): arm 2 is the 3 shipped species ONLY. The extended builder stays reachable and tested for a future B1 item, and warns loudly if used. |
| point-group detection | **DELIBERATE** | Registered as PRODUCTION work. `guards.SYMMETRY_COVERAGE` declares the gap as data. |

**Merely unfinished** (see §B): composite route strings · collector wiring · payload/PBS ·
the route-truncation defect · `nosymm` · the κ₂ pre-registration · `n_soft`'s role field.

---

# §A — What was built this session

All in `src/pilot_package/sei_pilot/` unless noted. Every module has a docstring that states *why*
it exists and which incident it encodes; those are not decoration and they are shorter than this file.

```
execlog.py      executions.jsonl integrity: PFL size trigger, JSON parseability, host/cores
                (R31.2a's host+cores landed in payload/common.sh:139 — ONE mechanism, not two)
guards.py       C-1 derived_or_null · C-2 irc_verdict · C-8 ts_precondition (RAISES) ·
                C-9 coplanarity + symmetric_placement_flags + SYMMETRY_COVERAGE ·
                C-10 cost_probe_violations · C-12 fallback_decision · C-13 tripwire_record +
                detect_tripwire_aborts
readiness.py    the THREE-ROW check (binary · data_library · launch_smoke). `ready` is NEVER True
                on rows 1+2 alone.
linalg.py       ONE symmetric Jacobi eigensolver for the package (guards + conformers import it)
b0_species.py   the 23: 19 closed-shell (derived from config rules) + 4 open-shell doublets
bound.py        the bound-species rule; HOMO/SOMO on EVERY species; per-stratum partition
roles.py        chemical-role perception; role→index mapping; require_mapping() RAISES
conformers.py   xtb metadyn pipeline: xcontrol builder, xtb_health, trajectory parsing,
                dissociation classification, cutoff sensitivity sweep, quaternion RMSD, dedupe,
                DFT window promotion, temperature_report, symmetry_trace
curvature.py    U-55's observables: ν_min · n_soft CURVE · TRIMMED κ_k ladder ·
                n_convergence_artefacts · correlate/u55_panel/kappa_stability ·
                imaginary_mode_verdict
arm2.py         the null control — 3 shipped species only, measure_idealised()
orbitals.py     HOMO/SOMO + frequency parsing, per-species parse accounting, b0_species_panel
solvent.py      C-5: the builder that REFUSES; epsilon_scan_line()
b0_plan.py      item list (128 tasks), sizing (reserved vs expected), cap-binding, guard check
config/         b0_species.json · b0_reactions.json · b0_conformers.json · engine_requirements
                in env_paths.json · graph_layers.json updated to 2.75 Å
make_package.sh [0/7] disk preflight — REFUSES BEFORE the .stale move
```

## The B0 batch as it now stands
```
B0-D   23 species (19 closed-shell singlets + 4 neutral doublets), 3 arms
       arm 1  xtb --metadyn conformers (NOT ETKDG — see §C-1)   23 tasks + 23 preopt
       arm 2  THE CONTROL — 3 shipped idealised geometries only  3 tasks
       arm 3  r_high from arm 1's conformer, EMITS THE FREQUENCY LIST  23 tasks
B0-F   3 reactions × 2 methods = 6 attempts, AT COMPOSITE (C-11)
ε scan 3 reactions × 3 states × ε ∈ {3,20,90} = 27 SPs, rides on B0-F, zero new geometry work
       128 tasks total.  🔴 UNSIZED — no unit costs exist. That is correct.
```

---

# §B — 🔴 LEAD INSTRUCTIONS I DID NOT COMPLETE. These die with me otherwise.

⚠ **The lead's own list of these was stale** (our messages crossed repeatedly — 5+ times). I have
marked what is actually done, so you do not redo it.

| instruction | status |
|---|---|
| parser fixture from the real eigenvalue block | 🟢 **DONE** — `tests/fixtures/g16_eigenvalues_p1_ts.txt` + 8 trap tests |
| run `format_validation()` and paste its record | 🟢 **DONE** — record in §D below |
| HOMO vs SOMO emitted separately | 🟢 **DONE** — and it found a second bug (§D) |
| `graph_layers.json` 2.4 → 2.75 Å + provenance fix | 🟢 **DONE** — and it flipped a real verdict (§E) |
| **route-truncation defect in `criteria/g16.py`** | 🔴 **NOT DONE** |
| **`nosymm` in G16 routes as part of C-9** | 🔴 **NOT DONE** |
| κ₂ vs `opt_cycles` pre-registration in the output | 🟢 **DONE** — `curvature.PRE_REGISTRATION`, + `primary` / `primary_ladder_context` / `primary_verdict: None` |
| `n_soft(x)` role field: CALIBRATION ONLY | 🟢 **DONE** — `curvature.N_SOFT_CURVE_ROLE` |
| composite route strings · collector wiring · payload/PBS | 🔴 **NOT STARTED** |

## B-1. 🔴 The route-truncation defect (lead-verified, three independent proofs)
`criteria/g16.py:parse_route` truncates to **70 characters** and stores it **with no marker**.
```
ts_qst2.log       len=70   '#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen'
irc_forward.log   len=70   '...irc=(calcfc,forward,maxp'
irc_reverse.log   len=70   '...irc=(calcfc,reverse,maxp'
```
1. three different routes, all **exactly** 70 chars — a fixed-width cut, not coincidence
2. all three have **unbalanced parentheses** and end mid-token (`noeigen`, `maxp`)
3. 🔒 **decisive: `"freq"` does not appear in the ts route, yet `n_frequencies: 27` and
   `imag_freq_cm: −105.0` were parsed from that same log. The report refutes its own field.**

**Fix**: store the full route, or store it with `truncated: true` and the original length.
🔴 **Until then, NEVER read ABSENCE off a stored route.** The lead read `nosymm? False | freq? False`
off it for a full second before the lengths caught the eye.

## B-2. 🔴 `nosymm` — and why it is not optional
> **Gaussian detects the molecular point group and by default CONSTRAINS the optimisation to it.**

I measured that GFN2 `--opt tight` *preserves* an exact degeneracy (the symmetry-breaking gradient
is exactly zero). **For G16 the mechanism is stronger: it is not passive — G16 re-detects the point
group and actively enforces it.**

⟹ **C-9's remedy is INSUFFICIENT for Gaussian without `nosymm`.** Perturbing an atom off a symmetry
element accomplishes nothing if G16 re-detects the group within its tolerance and re-imposes it.
**Any B0/production G16 route that relies on a perturbation must carry `nosymm` explicitly.**

⚠ Write the cost reasoning at the site so nobody removes it as an optimisation: `nosymm` costs the
symmetry speedup, which is **zero for genuinely asymmetric species** — i.e. it costs nothing except
on exactly the pathological cases we do not want.

🔒 **Do NOT assert `nosymm` was absent from P1.** Mark it `[UNKNOWN — the stored route is truncated
at 70 chars]`. That is a different and more useful statement than "absent". The lead has asked the
user for the full route lines.

## B-3. 🟢 DONE — the κ₂ pre-registration, as delivered
`curvature.PRE_REGISTRATION`, in the panel output, with date `2026-08-19` and
`registered_before_any_data: True`. Both rationale strings are there. 🔴 And so is the caveat I was
asked to write in my own words:

> the 6,000× κ₁/κ₂ gap **came from a SYNTHETIC fixture with a deliberately inserted 0.4 cm⁻¹
> mode**. It demonstrates the fragility of the untrimmed statistic and is **not evidence about our
> species**. It was **not** used to choose k, and it may not be cited as if it were.

🔒 **`primary_verdict` is `None` and MUST STAY `None`.** A boolean needs a cutoff on ρ, and a
hard-coded cutoff here is how −100 cm⁻¹ got into M2. The panel **states the rule and shows the
numbers; it does not evaluate the rule.** `verdict_is_a_judgement_for: "proposer"`.
`primary_ladder_context` puts k=1/2/3 beside the primary so it is never read naked. A revert making
the verdict boolean fails a test.

## B-4. 🟢 DONE — `n_soft(x)`'s role
`curvature.N_SOFT_CURVE_ROLE`: `role: "CALIBRATION ONLY"`, selects x, does not validate, and
🔴 *"the ρ at the winning x is inflated by the selection that produced it — validating it requires
a SECOND dataset; B1 can supply one."*

## B-5. 🔴 STILL OPEN — the reading order in the panel
The lead's original step 1 (*"stop if the correlation lives only at k=1"*) was **defective in both
directions** and they withdrew it: it read as licence to skip the primary, **and** the primary can
fail without the correlation living only at k=1 (present at k=1 and k=3 but not k=2 — the gate does
not fire and the primary has failed anyway). The replacement is implemented in `_readability` and
`_read_the_primary_in_its_ladder`:
```
1  primary + primary_ladder_context TOGETHER — a FRAMING, not a stop-gate
2  n_convergence_artefacts — many => that species did not converge, changing what (1) means
3  everything else, only if 1-2 leave a question open
```

---

# §C — Decisions and findings that are NOT (or may not be) in a document

## C-1. Route/method
* **arm 1 is `xtb --metadyn`, NOT ETKDG+MMFF.** §37.2.3 rules ETKDG *undefined* for Li⁺Lₙ (MMFF94
  has no Li parameters; ETKDG is for one covalent graph, Li⁺Lₙ is non-covalent). RDKit is not
  installed on either side of the air gap, and `02_METHOD_SPEC:4554`'s claim that ASE and RDKit are
  vendored is **false against the tree** — `vendor/` holds xtb and nothing else.
* 🔴 **R-4's subject moved with the route.** The batch retires *"does the xtb-metadyn route work"*,
  NOT *"does the ETKDG route work"*. `conformers.ROUTE_ID` is the single spelling; field names carry
  it so a write-up cannot drift back.

## C-2. 🔴🔴 xtb writes `normal termination of xtb` to **STDERR**, never stdout
Measured three ways (`--version`, `--opt`, `--metadyn`), all rc=0. **A Python runner using
`capture_output=True` and testing stdout concludes EVERY xtb run failed** — silently, with rc 0 and
every result file present. `payload/P3.sh` uses `2>&1` and is unaffected, **which is exactly why the
trap survives: a shell is immune, a Python runner is not, and we are writing Python runners.**
⟹ `conformers.xtb_health()` judges on CONTENT (frames produced, energies finite) and its failure
message names the stream trap.

## C-3. 🔴 The MTD thermostat: the pre-registered decision tree had an omitted variable
```
condition             start geometry     bias      ⟨T⟩ final   T_eff/T_set   warning
MTD idealised         idealised          $metadyn   625–680 K   1.56–1.70     YES
MTD pre-optimised     GFN2 --opt tight   $metadyn   564 K       1.41          YES
plain MD pre-opt      GFN2 --opt tight   NONE       395 K       0.99          NONE
```
**The thermostat is CORRECT.** The input causes a transient (702 K → 484 K over the first 200 steps);
the **bias potential** causes the persistent excess and is intrinsic to MTD — it *is* the search
mechanism. The tree offered "input" or "thermostat"; the answer was mostly a third thing that is not
a fault. 🔒 **A pre-registered tree protects against post-hoc rationalisation, not against an omitted
variable** — second instance, after R36.3's trigger written against a variable the filesystem did
not have.
⟹ **A dissociation rate on an MTD trajectory can never be a rate at a defined temperature.** Plain
MD at a controlled temperature *does* hold its setpoint (measured). Which instrument B0-D should use
for a floppiness statistic is METHODOLOGY and was routed, not taken. (ADR-077 then made it moot by
moving U-55 to curvature.)
⚠ Also: the excess-PE arithmetic that "confirmed" 258 K used an **assumed** 0.30 eV; the **measured**
excess is **1.0495 eV** → 902 K. An exact match between an assumed input and the observation used to
assume it is a **fit, not a confirmation**.

## C-4. 🔴🔴 GFN2 `--opt tight` does NOT break symmetry
```
li_ec_cation IDEALISED   Li equidistant: 2× C@5.2497 · 2× O@4.0341 · 4× H@5.8456
li_ec_cation GFN2 OPT    Li equidistant: 2× C@5.0415 · 2× O@3.7516 · 4× H@5.6401
                         every distance moved — THE EXACT DEGENERACY DID NOT
```
⟹ arm 1's pre-optimisation fixes the *thermal transient* and **not** the symmetry. The structure
entering the MTD is still C2v, and **we are relying on MTD velocities to break it as a side effect.**
`conformers.symmetry_trace()` now MEASURES it at three checkpoints. **Nothing is perturbed** — adding
a symmetry-breaking step is methodology. 🔴 And see §B-2: for G16 a perturbation alone is not enough.

## C-5. The idealised geometries are wrong in **opposite** directions
```
li_ec_cation / li_ec_radical   d(O–Li) 1.850 Å   ∠Li–O=C 180.0°   dev +42.0°
li_ec2_cation                  d(O–Li) 2.100 Å   ∠Li–O=C  90.3°   dev −47.7°
experimental                                              ≈138°   [LITERATURE, approximate]
```
🔴 **Only the 90.3° reached §39.1(e-bis). The 180.0° — which is what P1's endpoints actually used —
was recorded nowhere.** Both are *symmetric placements* (a C2 axis and a mirror plane), which
**strengthens ADR-067**: both were drawn, neither was chosen. Now carried in every arm-2 record via
`arm2.measure_idealised()`.
🔒 Consequence: the generator has **no consistent placement rule to reuse**, which is why arm 2 is
the 3 shipped species only.

## C-6. The guard's UNIT (this one nearly went the wrong way)
```
ResourceGuard counts       KNL core-h  (cores × wall, plan.size_job:464 — no κ anywhere)
the approval is in         REFERENCE core-h
κ ≡ (KNL)/(reference) = 2.4
RT-1's 21,000 KNL  =  8,750 reference   ← BELOW the approved 15,000. MORE restrictive, not less.
B0 guard  15,000 ref × 2.4  =  36,000 KNL
```
🔴 A numerically larger figure that is a **stricter** ceiling in the approved unit is **not a raise**
(§R24.1). The defence is that the KNL number is **derived in one function** and can never be typed
independently — not the number itself.

## C-7. Other measurements
* **κ ladder**: κ₁ = 20,475,625 vs κ₂ = 3,365.5 on a fixture with one inserted 0.4 cm⁻¹ mode.
  🔴 **Synthetic. Demonstrates fragility; says nothing about our species.**
* **Covariance eigenvalues** of `li_ec_cation`'s heavy atoms: `[0.0, 3.54, 20.95]`. The zero is the
  planar degeneracy; the two smallest are **well separated**, so the plane normal is unique and we
  are **not** near the dangerous case (two *equal* smallest).
* **MTD wall time**: 5 ps on 11 atoms = 74 s at 12 threads. 🔴 **Do not extrapolate.** κ was measured
  on a G16 SCF probe; MTD is a different workload class; and the stopping rule is now discovery-rate
  based, so per-species wall time is not a constant at all.

**Believed NOT in any document**: C-2 (stderr), C-4 (GFN2 symmetry persistence), C-5's 180.0°,
C-7's eigenvalues and wall time, and the `arm2` extended-vs-shipped split. C-3 and C-6 were sent to
the lead in detail; I do not know whether they reached an ADR.

---

# §D — 🟢 The real G16 eigenvalue block, and the two bugs it found

`tests/fixtures/g16_eigenvalues_p1_ts.txt` — real cluster output, user-supplied. Provably P1's TS
species: 25 α + 24 β occupied ⟹ multiplicity 2 and 49 electrons, matching the report's declared
charge 0 / mult 2 and C₃H₄LiO₃'s electron count — **two facts it could not have been fitted to.**

`format_validation()` record, which is what closes the `[UNVERIFIED]` **for the orbital half only**:
```
orbital_format_recognised  True        orbital_lines_matched  12
n_alpha_occ  25            n_beta_occ  24
alpha_homo  -0.30464  beta_homo  -0.34581  alpha_lumo  +0.03618  beta_lumo  -0.00368
orbital_verdict  matched
frequency_verdict  not exercised by this input (no `Frequencies --` lines) — NOT a failure
```
**Four traps. Traps 1–3 the parser already survived** (`^\s*` for the 1-vs-2 leading spaces; `\s+`
for `occ.`'s two spaces vs `virt.`'s one; occupancy from the **label**, since the β LUMO is
*negative*). **Trap 4 was a real bug**: `max(all occupied)` labelled `homo_or_somo`, correct here
only because α HOMO happens to exceed β HOMO.

🔴 **And a SECOND bug, which my fix for trap 4 introduced**: `n_alpha > n_beta` ⟹ SOMO exists fires
on **every restricted (RKS) log**, because G16 prints no Beta block at all and `n_beta = 0` — so all
19 closed-shell singlets would have had a SOMO reported for a doubly-occupied orbital. **The fix for
one conflation created another.** Now requires both spin sets present.

⚠ **What this log does NOT validate — keep declared**: Gaussian's fixed-width columns let
large-magnitude values run together (`-100.12345-99.12345`); every value here separates cleanly, so
that stays `[UNVERIFIED]`. And this copy is **truncated** (12 matched lines). 🔒 **One real log
validates the format it contains and nothing else.**

---

# §E — U-67: the Li–X cutoff, and why prior verdicts are not grandfathered

```
Li-O 2.4 / Li-F 2.3 / default 2.5  [PLACEHOLDER-ESTIMATE]
   →  2.75 Å for ALL elements      [MEASURED, MLIP RDF first minimum]
```
🔴 **Not element-resolved** — the user gave Li–X generically; there is no per-element table and
nobody should assume one. The old provenance string named P1 and **P2** as the intended source, and
**P2 was deleted (ADR-033)**, so it pointed at something that does not exist.

🔴 **It flipped a verdict on the real trajectory**: 2.4 Å gave 19 intact / 1 dissociated; 2.75 Å
gives 20 / 0. A test pins **both** numbers, so if the old table ever stops flipping one, the
"recompute, do not grandfather" instruction has lost its instance and you find out.

---

# §F — 🔒 THE THREE FALSE-GREEN REVERTS, and what they mean for my other numbers

I ran ~90 revert experiments this session and reported them as "all FAIL". **Three came back green
and were my error, not the code's.** I caught all three, but that is the point of writing this down.

```
#1  block-merge fixture      [-5.0] then [-3.0]: max(merged) == max(last). The FIXTURE could not
                             distinguish correct from defective.
#2  coverage-list check      asserted substrings in " ".join(list); a disabled entry with a
                             `_removed ` prefix still satisfied it. Same family.
#3  `[] or [x]`              🔴 folds to `[x]` in Python — THE REVERT NEVER APPLIED. Different
                             animal: the experiment did not run at all.
```

**Two rules, and #3 needs the second because the first would not have caught it:**
1. **Construct the fixture so the DEFECTIVE implementation gives a DIFFERENT answer, then check
   that it does** — not merely that the correct implementation gives the right one.
2. **Verify the revert changed BEHAVIOUR, not that the file text changed.** My harness asserted the
   anchor matched exactly once and that the syntax parsed; **neither catches a semantic no-op.**

🔴 **AND THE PART YOU MUST NOT SKIP:** *earlier* green reverts in this package deserve the same
suspicion. **Do not read "all reverts FAIL" in my reports as a uniform guarantee** — it is a
guarantee about the cases I thought to construct, checked with a method I improved twice mid-session.
🔒 **A revert you hand-write is itself untested code.** Noticing that three times in one day is
uncomfortable and it is the honest state of the evidence.

The pattern for a critic to hunt: **a revert case whose "after" text is semantically equal to its
"before"** — `[] or [...]`, `x if True else y`, a disabled entry that still matches the assertion.

## 🔴🔴 F-2. THE RULE THIS SESSION EARNED AND NO DOCUMENT HOLDS

> **A fix that SPLITS ONE CONCEPT INTO TWO must be checked against the inputs where the SECOND
> CONCEPT DOES NOT EXIST.**

I hit this twice today, and the second time I *created* the bug while fixing the first:
```
split      HOMO  /  SOMO          (trap 4 — they had been one field, `homo_or_somo`)
the input  a RESTRICTED (RKS) log, where SOMO HAS NO REFERENT AT ALL — G16 prints no Beta block,
           so n_beta = 0, `n_alpha > n_beta` fires, and every closed-shell species reports a SOMO
           for a DOUBLY-OCCUPIED orbital. All 19 of B0-D's singlets. Silently: no error, no drop,
           straight into bound.py.
```
🔒 **The alpha/beta framing is exactly what makes that case invisible** — you are thinking about
which spin wins, and the case where there is only one spin channel never comes to mind.

⚠ **Your successor will split concepts; it is what this codebase keeps needing.** Others already
split this way and are worth re-checking against their own null case:
`indeterminate` vs `fail` (C-2) · `parser` vs `data` failure (orbitals) · `dissociated` vs
`fragmented` (conformers) · `reserved` vs `expected` (b0_plan) · `shipped` vs `extended` (arm2) ·
minimum vs TS expectation (`imaginary_mode_verdict`). **For each, ask: what is the input where the
second thing does not exist, and what does the code do with it?**

## Revert harness
`/tmp/revert_harness.py` — 🔴 **`/tmp` IS REAPED WITHIN A SESSION on this box** (see
`HANDOFF_TO_LEAD.md` §0.2c, which I added). It destroyed my first revert run *and* unlinked the tmux
socket that blocked `critic7`. **Keep pristine copies outside `/tmp`** — I used `~/.sei_pristine/`.

---

# §G — 🔒 What I am least sure of / would most want challenged

Ordered by how much damage it does if I am wrong.

1. 🔴 **The G16 orbital regex, on formats the one real log does not contain.** Run-together
   fixed-width values remain unverified. The whole batch's bound check consumes this parser, and a
   parse failure now *drops a species from `u_cheap`* — so the parser decides the sample size.
   The defence is that it can say "I matched nothing" and calls that a **parser** problem, never a
   data one; **that defence is the thing to attack.**
2. 🔴 **The MTD hyperparameters** (kpush/alp pairs, discovery-rate threshold 0.05, 20 ps cap) are
   `CODER-CHOSEN AND UNTUNED`. §37.2.3 named exactly these as option (ii)'s risk. B0-D's own output
   is the first evidence about whether they are adequate.
3. **`EXACT_DEGENERACY_TOL_ANG = 1e-3`** in `guards.symmetric_placement_flags`. It is a
   numerical-identity threshold, not a chemical one, and it worked on five real files — but it is a
   *fingerprint with known coverage*, not point-group detection, and it says so.
4. **`arm2`'s `extended` rule** (unwired, but present). If B1 ever needs a prospective naive-start
   measurement it needs a **declared, documented, consistent** builder — not this, which was written
   as a control's side effect.
5. **`CONVERGENCE_ARTEFACT_CM1 = 5.0`** — coder-chosen, and it now labels a *diagnostic* rather than
   gating anything, which is safer, but nothing calibrates it.
6. 🔴 **The 18-correlation table's readability.** I flagged it and the lead pre-registered a primary
   to fix the multiple-comparisons problem — but I have not built the pre-registration (§B-3), so
   **right now the panel has 18 coefficients and no declared primary.** That is the most likely
   place for someone to pick the largest number and call it a result.

**Where I have been wrong this session, so you can calibrate the rest:** I called the `.stale`
directory "an intermediate build" when it was the *delivered package that failed on the cluster* —
I inferred it from a digest mismatch when the actual question was two commands away. I also
introduced the RKS/SOMO bug *while fixing* a conflation, and shipped a `.replace("identical",
"identical")` no-op inside an assertion.

---

# §H — First five minutes, successor

```
1. Read HANDOFF_TO_LEAD.md §0 and §45. Then this file's READ THIS FIRST block.
2. python3 src/build_stamp.py check --root .     Believe nothing until it prints ✅.
3. python3 -m unittest discover -s tests -q      Expect 1115 OK. Two build_stamp FAILures are
                                                 NORMAL if you have edited src/ and not rebuilt.
4. source_digest is identity. tarball sha256 is NOT (gzip mtime).
5. 🔴 Read §B before writing anything — four lead instructions are outstanding and three of them
   are small.
6. 🔴 Read the DELIBERATELY-ABSENT table before "fixing" a null.
7. Keep revert pristine copies OUTSIDE /tmp (§F).
```

## Conventions I followed and you should keep
* **The caveat goes in the FIELD NAME, not a docstring.** A name travels into every downstream
  table; a doc does not. Instances: `dissociation_events_at_uncontrolled_effective_temperature`,
  `coplanarity_check_only`, `highest_occupied_hartree`. This mechanism was reached for four times
  independently and was right every time.
* **Two fields, never one, when a value can be a setpoint or a measurement**
  (`temperature_requested_k` / `temperature_measured_k`), or when a count means opposite things for
  two populations (`imaginary_mode_verdict`'s `expected_minimum`).
* **`None` means NOT CHECKED; `False` means checked-and-negative.** Never interchange them. Every
  gate in this package falls toward *unknown*, not toward *pass*.
* **A guard that matters RAISES.** `require_ts_precondition`, `require_mapping`,
  `assert_no_preoptimisation`, `solvent_line`. A returned flag is a thing a caller may decline to
  read, and that is how every expensive failure here happened.
* **Presence before value in assertions**, so a missing field FAILs readably instead of raising a
  KeyError — §0.2(a): an ERROR is usually a broken experiment and is weak evidence.

---

*coder6, 2026-08-19. Tree clean at `source_digest 4a484eb71ef2b36d`, 1122 tests OK, gate OK,
`[stamp] ✅`. Nothing was delivered to the user by me.*
