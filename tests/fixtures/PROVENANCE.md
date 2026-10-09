# Test fixtures — REAL OUTPUT, generated, never hand-written

🔴 Why these are files and not Python dicts (§44.5, ADR-042):
A hand-written fixture encodes the output I *imagine* a tool produces. This project has already
shipped tests that were green while asserting a module name that did not exist. Every fixture here
was produced by actually running the tool, on this machine, and is stored verbatim.

## `xtb_metadyn_li_ec_cation.trj` / `.inp`

```
produced by  src/pilot_package/vendor/xtb/bin/xtb   (the VENDORED binary, not a system one)
             xtb version 6.7.1 (edcfbbe), statically linked x86-64
command      xtb start.xyz --gfn 2 --chrg 1 --uhf 0 --metadyn --input mtd.inp
start        src/pilot_package/inputs/p5_species/li_ec_cation.xyz   (11 atoms, Li+(EC))
env          XTBPATH=<pkg>/vendor/xtb/share/xtb, isolated working directory
date         2026-08-19
result       normal termination · 20 frames in xtb.trj · 5 ps at 400 K
wall         74 s on the dev box at 12 threads
```

🔴 **Two things observed in this run that the pipeline must handle, and that no fixture I invented
would have contained:**

1. **`thermostating problem` was printed, T reached 658 K against a requested 400 K, and xtb still
   reported `normal exit of md()` and `normal termination of xtb`.** The banner is not a health
   signal. This is the same shape as §0.2b-3 (xtb omits the banner for good periodic GFN-FF
   results) arriving from the opposite direction: here the banner is present and something IS
   wrong. ⟹ health is judged on the parsed content, never on the banner.
2. **The trajectory's comment line carries the energy**, in Hartree:
   ` energy: -20.574765099713 gnorm: 0.179165023803 xtb: 6.7.1 (edcfbbe)`
   — so per-frame energies are available without a separate single-point.

⚠ **Do not regenerate this file to "make it cleaner".** Its imperfections (the thermostat
excursion, frame 14's transient Li–O stretch to 2.688 Å past the 2.4 Å contact cutoff) are the
cases the classifier has to get right.

## 🔴🔴 Addendum, measured 2026-08-19 — the success banner is on STDERR

```
xtb 6.7.1, vendored binary, three invocations:
    --version                     rc=0   banner in stdout: NO    banner in stderr: YES
    --gfn 2 --opt normal (EC)     rc=0   banner in stdout: NO    banner in stderr: YES
    --metadyn (Li+(EC))           rc=0   banner in stdout: NO    banner in stderr: YES
```
**`normal termination of xtb` is written to STDERR, never stdout.** A Python runner using
`subprocess.run(..., capture_output=True)` and testing `"normal termination" in stdout` concludes
that EVERY xtb run failed — silently, because `rc` is 0 and every result file is present. A shell
pipeline using `2>&1` never sees this, which is why the shipped `payload/P3.sh` is unaffected and
why the trap survives unnoticed.

🔒 `conformers.xtb_health()` therefore judges on CONTENT — frames produced, energies parsed and
finite — and records the banner and the exit status as diagnostics only. This is the same lesson as
HANDOFF §0.2b-3 (xtb omits the banner for good periodic GFN-FF single points) arriving from a third
direction: **the banner is not a health signal in either direction, on either stream.**

## `xtb_T_trace_*.txt` — the thermostat diagnostic, 2026-08-19

Three MD runs on `Li+(EC)`, **identical `$md` block** (5 ps, 1 fs, temp=400 K, hmass=4), differing
only in the two variables under test. Same vendored xtb 6.7.1, `OMP_NUM_THREADS=4`.

```
condition            start geometry     bias potential   <T> final    T_eff/T_set   warning
MTD idealised        idealised          $metadyn ON        625-680 K     1.56-1.70    YES
MTD pre-optimised    GFN2 --opt tight   $metadyn ON        564 K         1.41         YES
plain MD pre-opt     GFN2 --opt tight   NONE               395 K         0.99         NONE
```
(The two `<T> final` figures for the idealised MTD are two separate runs of the same
configuration — MD is not bit-reproducible here. The spread is itself information.)

### 🔴 The conclusion, and it is not the one the pre-registered decision tree allowed for

The tree was **"pre-optimise: if the overshoot disappears the input caused it; if it persists it IS
the thermostat."** Neither branch is right, because a **third variable exists and is specific to
metadynamics**:

```
THE THERMOSTAT IS CORRECT.   Plain MD from the optimised structure holds 395 K against a 400 K
                             setpoint (-5 K) with ZERO thermostat warnings.
THE INPUT contributes        a large TRANSIENT: <T> over the first 200 steps is 702 K from the
                             idealised start against 484 K from the optimised one.
THE BIAS POTENTIAL           contributes the PERSISTENT excess: 564 K (MTD) vs 395 K (no MTD),
                             from the SAME optimised geometry. ~+170 K.
```
🔒 **A metadynamics bias potential does work on the system by construction — it is the search
mechanism.** Elevated temperature is therefore intrinsic to MTD, not a defect, and **"tune the
setpoint or the coupling time" would have been the wrong prescription applied to a thermostat that
is demonstrably working.**

### 🔴 What this changes about the DISSOCIATION RATE
A dissociation rate counted on an MTD trajectory is **not a rate at a defined temperature and
cannot be made into one by fixing the input or the thermostat** — the elevated T is the search
mechanism operating. 🟢 Plain MD at a controlled temperature *does* hold its setpoint (measured
above), so a defined-temperature floppiness measurement is available and cheap. **Which instrument
B0-D should use for the floppiness statistic is a methodology decision, not a coder decision.**

### ⚠ And the excess-potential-energy arithmetic was a fit, not a prediction
```
ASSUMED   excess PE 0.30 eV, 11 atoms, n_df 27  ->  dT = 258 K   == the observed 258.8 K, exactly
MEASURED  E(idealised) - E(GFN2 optimised) = -20.575515 - (-20.614082) Ha = 1.0495 eV
                                            ->  dT = 902 K,  3.5x the observed overshoot
```
🔴 The exact agreement came from an ASSUMED input, so it tested the assumption rather than the
hypothesis (Rule 22). The measured excess is ~3.5x larger, which is consistent with a thermostat
actively removing energy — but that is an explanation offered after the fact. **The experiment is
what decided this, not the arithmetic.**

## `g16_eigenvalues_p1_ts.txt` — REAL Gaussian 16 output, supplied by the user 2026-08-19

The orbital eigenvalue block from RT-1's P1 `ts_qst2.log`, produced on the cluster by
`/apps/commercial/G16/g16.linda.c01/g16` on node4622.

🟢 **Provably the P1 TS species — three independent facts agree, none of which could be fitted:**
```
n_alpha_occ 25 · n_beta_occ 24   -> multiplicity 2   matches the report's charge 0 / mult 2
25 + 24 = 49 electrons           -> charge 0 for     C3H4LiO3 = 3(6)+4(1)+3+3(8) = 49
C3H4LiO3                          is the IRC endpoint fragment in pilots[0].detail.irc
```

### 🔴 Four traps in the real format. Two would have silently halved the parse.
```
1  LEADING WHITESPACE DIFFERS BY SPIN:  ' Alpha' (one space) vs '  Beta' (two).
   A pattern anchored ^Alpha|^Beta, or using a single '^ ', matches every Alpha line and NO Beta
   line -> 25 of 49 orbitals, a clean-looking HOMO, and NO ERROR.        Defence: ^\\s*
2  'occ.' TAKES TWO SPACES, 'virt.' TAKES ONE.  A single literal space misses every OCCUPIED line
   and matches only the virtuals -> it returns a HOMO that is actually a LUMO.  Defence: \\s+
3  THE BETA LUMO IS NEGATIVE: -0.00368.  Occupancy MUST come from the occ./virt. LABEL and never
   from the sign. Matters most for reduced species, whose SOMO can genuinely be positive.
4  HOMO != SOMO, and they COINCIDE HERE BY LUCK.
   alpha HOMO -0.30464 > beta HOMO -0.34581, so max() is right on this log.
   In a strongly spin-polarised species the beta HOMO can sit ABOVE the alpha SOMO, and max()
   then returns a DOUBLY OCCUPIED orbital and calls it the SOMO.
```
🔴 Trap 4 was a **real bug in `orbitals.highest_occupied`**, which returned `max(all occupied)`
under the name `homo_or_somo`. Found by this log, not by review. Both quantities are now emitted
separately and nothing is called "homo_or_somo".

### Verified values (parser output against this block)
```
n_alpha_occ 25 · n_beta_occ 24 · derived multiplicity 2 · total electrons 49
alpha_homo -0.30464 · beta_homo -0.34581 · alpha_lumo +0.03618 · beta_lumo -0.00368
```

### ⚠ What this log does NOT validate — keep declared
* **Fixed-width run-together values.** Gaussian's columns let large-magnitude eigenvalues abut
  without a separator (`-100.12345-99.12345`). Every value here separates cleanly, so that case
  remains `[UNVERIFIED]`. **One real log validates the format it contains and nothing else.**
* This copy is **TRUNCATED** (12 matched lines). The full log's last alpha virtual (44.62393,
  alone on its line) and the 4-value last beta occ line are not present here, so the
  variable-values-per-line case is only partly covered.

## `g16_normal_modes_p1_ts.log`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/P1/ts_qst2.log` (the returned
  P1 pilot tree, 2026-08-20). Verbatim slice — the last `Input orientation:` block before
  the frequency section through the end of the normal-mode listing. Nothing edited.
* **Why**: the source is 50k+ lines and lives outside the package; the test must run from
  the packaged tree. A header naming the source and the byte range is prepended.
* **What it fixes**: `criteria.g16.parse_normal_modes` + `curvature.mode_overlap_omega`
  against the ONLY real normal-mode block this project has. §39.56's measurement —
  exactly one imaginary mode at -48.4416 cm^-1, reduced mass 7.1479 amu, 63% of the
  squared amplitude on one Li atom, Omega(O2-C3) = 0.022 with d = 3.184 A — is the
  evidence that P1's "TS" was not the ring-opening saddle at all.
* 🔴 **The displacements in the low-precision block carry only 2 decimals.** Omega values
  computed from it are reproducible but not high-precision; `freq=hpmodes` would be
  required if a verdict ever sat near a threshold. Here it does not (0.022 vs O(1)).

## `g16_irc_forward_maxpoints_p1.log`, `g16_irc_reverse_maxpoints_p1.log`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/P1/irc_{forward,reverse}.log`
  (returned P1 pilot tree, 2026-08-20). Verbatim tails, nothing edited.
* **What they fix**: `criteria.g16.parse_irc_completion` + C-2.2. Both directions printed
  `Maximum number of steps reached.` AND `Normal termination of Gaussian 16` — a run that
  satisfied every clause C-2 had at the time (both terminated normally, 31 points each,
  descent 0.143/0.147 eV) while reaching no minimum. The energy was still falling at a
  steady rate at the last point, so the path stopped on its STEP BUDGET, not at a minimum.
* 🔴 This is the evidence for the cause-class split: that outcome is BUDGET-class, not
  chemical, and pooling the two corrupts `1/p`.

## `xtb_relaxed_scan_r_a.log`, `xtb_relaxed_scan_r_a.inp`

* **Produced by EXECUTION**, dev box, 2026-08-20 (RT-1 discipline — the format was measured,
  not remembered; this project had no xtb constrained-scan machinery before).
* Command: `xtb r.xyz --opt --input scan.inp --chrg 0 --uhf 1 --gfn 2 -P 1`, rc = 0,
  `r.xyz` = `inputs/li_ec_radical_reactant.xyz`, `scan.inp` constrains `d(2,3)` and scans it
  over 1.45–2.65 Å in 12 points. Both files are verbatim.
* **What it fixes**: `gfn2_scan.parse_scan_log`. `xtbscan.log` is a multi-frame XYZ whose
  comment line reads ` energy: <E_hartree> xtb: 6.7.1 (edcfbbe)` — 12 frames of 11 atoms.
* 🔴 These are GFN2 energies in **Hartree**. They may only be compared with other GFN2
  energies (§39.50(b): no gate arithmetic across Hamiltonians).

## `xtb_relaxed_scan_r_a_reverse.log`

* **Produced by EXECUTION**, dev box, 2026-08-20. The G-SCAN-1 reverse direction of the run
  above: started from the forward scan's FINAL frame, same grid backwards
  (`xtb r.xyz --opt --input scan.inp --chrg 0 --uhf 1 --gfn 2 -P 1`, rc = 0, 12 points).
* **What it fixes**: the end-to-end G-SCAN-2 verdict on R-A. The two profiles are mirror
  images (forward last = reverse first to 4 decimals), |ΔE_endpoint| = 0.0003 eV.
* 🔴 It is also the regression that caught §39.64's defect: with each barrier measured from
  its OWN first frame, |Δbarrier| = 0.313 eV and the gate FALSE-BLOCKED this clean path.
  Measured from the reactant end (forward[0], reverse[-1]) it is 0.0216 eV and passes.

## `g16_irc_arc_lengths_p1.txt`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/P1/irc_forward.log`, the 30
  `NET REACTION COORDINATE UP TO THIS POINT` lines, extracted with grep. Nothing edited.
* **What it fixes**: §39.70's rule that B+ takes its second start point at the **arc-length
  midpoint**, not an index midpoint. On this real path the arc midpoint is index 14 — neither
  the index midpoint nor the "20th of 30" an index-based reading suggests, because the arc is
  not uniform in index. That non-uniformity is the rule's entire justification, so it is
  pinned against real spacing rather than a synthetic ramp.

## `g16_p5_opt_ok_freq_crashed.log`

* **Source**: `cpu_machine_pilot_results/.../jobs/P5/species/ec_s0_L2/job.log` (returned tree).
  Verbatim lines, extracted with grep, nothing edited.
* **What it fixes**: `g16.stages_completed`. This log is the defect in one place — the opt half
  completed AND printed `Normal termination of Gaussian`, while `Frequencies --` appears **zero
  times** because L1110 aborted on `EpsInf= 0.0000` (§39.73). P5's `converged` field, being
  `normal_termination AND opt.converged`, therefore read **true** on a species with no
  frequencies at all.
* 🔴 The same log carries `NEqPCM: Using equilibrium solvation (IEInf=0, ...)` — G16 saying it
  should not be consulting EpsInf, which is why §39.73 expects the bracket to come back
  invariant and the whole thing to be a plumbing defect rather than physics.

## `g16_irc_forward_minimum_u56rb.log`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RB_scan/irc_forward.log`
  (returned U56-2 pilot tree, 2026-08-21). Lines 2600-3075 (the tail), verbatim, nothing edited.
* **What it fixes**: `criteria.g16.IRC_MINIMUM_MARK` (`"Minimum found on this side of the
  path"`) was never verified against a real log and does not occur anywhere in the returned
  tree. This cluster's G16 prints `"PES minimum detected on this side of the pathway."`
  instead — a GENUINE minimum after only 1 point (arc 0.18324), previously misread as
  `termination_reason: "normal_termination_without_a_minimum_marker"`.
* 🔴 `truncated` was ALREADY correct (`False`) on this log either way — only `minimum_found`/
  `termination_reason` were the false negative.

## `g16_irc_forward_error_termination_u56ra.log`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan/irc_forward.log`
  (returned U56-2 pilot tree, 2026-08-21). Lines 29874-30474 (the tail), verbatim, nothing
  edited.
* **What it fixes**: `criteria.g16.parse_irc_completion` used to label EVERY `normal is not
  True` case as `"no_marker (... wall-clock or budget kill ...)"`, even when the log carries a
  REAL G16 marker. This log dies mid corrector-integration (`Delta-x Convergence NOT Met` /
  `Maximum number of corrector steps exceded.`) with an explicit `Error termination via Lnk1e`
  line, followed by a Linda-shutdown segfault backtrace (secondary debris, not the root cause).
  Wall used was 1.8-5.3h against a 48h cap — not a wall/budget kill.
* 🔴 Also feeds `outcome.INPUT_DEFECT_SENTINELS` (`"Maximum number of corrector steps exceded"`,
  G16's real spelling) — same deck, same corrector-integration crash every time -> classified
  `deterministic`, never auto-retried (lead's ruling, 2026-08-21).

## `g16_irc_forward_point5_u56ra.log`, `g16_irc_forward_point20_u56ra.log`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan/irc_forward.log`
  (returned U56-2 pilot tree, 2026-08-21). Lines 4444-4975 and 21350-21790 respectively,
  verbatim, nothing edited.
* **What they feed**: `tools/build_u56_ra_stability_probe.py`'s two ruled `stable=opt` targets
  (02_METHOD_SPEC.md §39.114(2)) — IRC path point 5 (arc 1.70908, nearby beta MO-coefficient
  warning 33.4, first target) and point 20 (arc 6.83462, warning 38.9, the LAST point actually
  computed before the corrector integration dies, second target). Each fixture is trimmed to
  contain exactly the one orientation block `parse_irc_path_frames` needs for that point.

## `g16_endpoint_tight_rc_reactant.log`

* **Source**: `cpu_machine_pilot_results/sei_pilot_work/jobs/endpoint_prep_rc_reactant/
  endpoint_tight.log` (returned U56-2 pilot tree, 2026-08-21). WHOLE file (11567 lines),
  verbatim, nothing edited — `last_geometry()` needs the LAST orientation block near EOF, and
  both the first (~line 897) and last (~line 9416) MO-coefficient warnings are needed too, so
  no trimming was attempted.
* **What it feeds**: `tools/build_u56_ra_stability_probe.py`'s third `stable=opt` target
  (02_METHOD_SPEC.md §39.115) — this ALREADY-CERTIFIED (n_imag=0, C-8 passed) 21-atom reactant
  shows the LARGEST MO-coefficient magnitude anywhere in the returned tree (71.0/67.0 ->
  78.9/71.3, alpha/beta), roughly double `U56_RA_scan`'s failing plateau, on a job that did NOT
  crash — priced/read as a separate, escalation-priority line item (a certificate already
  relied on, not an open candidate).
