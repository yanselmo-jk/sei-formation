"""Blocking constraints C-1, C-2, C-8, C-9, C-10, C-12, C-13 as executable predicates.

Every function here exists because the corresponding failure ALREADY HAPPENED and cost real
core-h. The source constraints are `02_METHOD_SPEC.md` §39.12 and §39.13(e); the incidents are
ADR-064/065/066 and §39.4.

    C-1   a derived quantity is `null`, NEVER a number, when ANY input step has converged == false
    C-2   no chemical verdict from an IRC unless BOTH directions terminated normally with >= 5
          points and > 0.05 eV of descent; otherwise `indeterminate`, NEVER `fail`
    C-8   a TS search REFUSES TO START unless both endpoints are converged minima with n_imag == 0
          at the same level -- a PRECONDITION, not a warning
    C-9   never start a TS search from a guess whose heavy atoms are all coplanar unless the
          species is genuinely planar; detect the degeneracy and perturb out of plane
    C-10  a COST probe must not carry a CHEMICAL pass/fail
    C-12  a fallback is conditioned on the ACCEPTANCE TEST, never on the exit status
    C-13  a `[TRIPWIRE-ABORTED]` run reports its core-h and is NEVER discarded

🔴 FAILURE DIRECTION, decided before any of this was written (Rule 18).
   Every predicate here falls toward REFUSE / UNKNOWN, never toward PERMIT.
   `None` means "not checked". `False` means "checked, and it is not so". They are different
   answers and the code never substitutes one for the other -- that substitution is what let
   `exceeds_tripwire` and `imag_freq_count` pass on things nobody had looked at.

Units: energies in **Hartree** on the wire (that is what G16 prints), compared in **eV** through
`units`. Lengths in **Angstrom**. No conversion constant is written down in this file.
"""

import math

from . import config, linalg, seeding, units
from .criteria import endpoints, xyzgraph

# --- C-2 -----------------------------------------------------------------------------------
#: An IRC direction must descend by more than this to count as having left the saddle.
#: SOURCE: 02_METHOD_SPEC §39.12 C-2, pre-registered by proposer5. Not a coder choice.
#: 🔴 P1's directions descended by 0.00008 eV and 0.00003 eV -- three orders below this -- and the
#:    gate still rendered a chemical verdict, because it compared TOPOLOGY and the TS of a late
#:    reaction already carries the product's bond graph (§39.4(a)). Only the ENERGY can tell.
IRC_MIN_DESCENT_EV = 0.05

#: SOURCE: 02_METHOD_SPEC §39.12 C-2. P1 returned n_frames = 1 per direction.
#: 🔴 [§39.116(d), critic14] This constant's OWN premise is "fewer than this many points means
#: we didn't buy enough" -- true for a truncated path, but `U56_RB_scan` is a counterexample to
#: that premise for the DIFFERENT reason recorded where this is consulted below: a legitimately
#: COMPLETE 1-point path (G16's own stopping criterion fired, confirmed-flat geometry) still
#: fails this floor, and the cause is NOT "insufficient budget" -- see the `protocol` branch
#: right below, not `IRC_MIN_POINTS` itself, which stays correctly sourced for the truncated case.
IRC_MIN_POINTS = 5

#: 🔴 [§39.114(1), proposer10, RULED but explicitly NOT a tuned constant -- "a round number
#: chosen only to flag review", the opposite discipline from IRC_MIN_DESCENT_EV/IRC_MIN_POINTS
#: above, which ARE sourced. condition-7 branch (b) (`maxpoints`/truncation + B+ agreement
#: "establishes a connection") is unsafe when the available IRC points never got far from the
#: saddle: `U56_RA_scan` reverse crashed after ~5-6 points (arc 1.71) with its B+ start points
#: only 1.02 arc units apart -- B+'s agreement there is as likely to mean "both terminal
#: optimisations rolled back to the SAME saddle-adjacent structure" as "a real distant basin",
#: exactly the false-agreement failure mode §39.70(2) already worried about for the
#: single-earliest-point case. The SAME reaction's forward arm (~20-21 points, arc 6.83, B+ gap
#: 3.41) is "clearly enough" by the ruling's own words. The true cutoff sits somewhere between
#: 1.71 and 6.83 arc units and needs more measured truncated-IRC cases before it can be pinned
#: the way §39.71 pinned its energy tolerance against real brackets -- until then, branch (b)
#: downgrades to `low_confidence` below this many points, rather than trusting a bare `True`.
#: 🔴 Convention: this counts points the way `criteria.g16.parse_irc_path_frames` does -- the
#: saddle (point 0, arc 0) is NOT one of them. proposer10's own arc table describes the same
#: real forward arm as "21 points, idx 0-20" (saddle included); `parse_irc_path_frames` returns
#: 20 for that identical log. The two conventions differ by exactly the saddle point. This
#: constant is round enough that the off-by-one changes neither real example's verdict (20 or
#: 21 vs. 5 or 6, both nowhere near this threshold either way) -- but a future, tighter,
#: measured threshold MUST state which convention it was measured against.
BPLUS_LOW_CONFIDENCE_MIN_POINTS = 10

# --- C-9 -----------------------------------------------------------------------------------
#: Max out-of-plane deviation of the heavy atoms, in Angstrom, below which the guess is treated
#: as a planar degeneracy.
#: 🔴 CODER CHOICE, NOT FROM THE SPEC. §39.12 C-9 says "all heavy atoms coplanar" and gives no
#:    tolerance. RT-1's two endpoints had every heavy atom at EXACTLY z = 0, so any sane value
#:    catches them; this one is reported in the output (`coplanarity.tolerance_ang`) so a reader
#:    sees the threshold that produced the verdict instead of having to find it in the source.
#:
#: 🔴🔴 AND THE MORE IMPORTANT CAVEAT, MEASURED 2026-08-19: **a better tolerance on this test buys
#:    nothing, because for four of our five files IT IS THE WRONG TEST.** C-9's revised
#:    specification (proposer5) is "no atom on a SYMMETRY ELEMENT of the remaining fragment --
#:    axis, plane, or centre". Coplanarity sees only the planar case:
#:      li_ec2_cation      Li on a MIRROR PLANE, heavy atoms NOT coplanar  -> THIS TEST MISSES IT
#:      li_ec_cation etc.  Li on EC's C2 ROTATION AXIS (EC alone is C2v, axis along y) -> caught
#:                         only INCIDENTALLY, because those files also happen to be fully planar.
#:                         A collinearity on a rotation axis is not a coplanarity.
#: ⟹ do not tune this number expecting to close the gap. Full point-group detection is registered
#:   as PRODUCTION work and is deliberately not implemented here; `SYMMETRY_COVERAGE` and
#:   `symmetric_placement_flags` state the gap rather than hiding it.
COPLANAR_TOL_ANG = 0.10

#: 🔴 Same caveat as COPLANAR_TOL_ANG: this kick breaks a PLANE. It does not move an atom off a
#: ROTATION AXIS, and it is not applied at all when the plane test does not fire.
#: Out-of-plane displacement applied when a planar degeneracy is detected, in Angstrom.
#: 🔴 CODER CHOICE. Deliberately larger than `seeding.DEFAULT_AMPLITUDE_ANG` (0.10) because this
#:    displacement has a DIRECTION and a job: it must leave the mirror-symmetric subspace by more
#:    than an optimiser step, or the optimiser walks straight back into it. Reported alongside the
#:    result and reproducible from `seed_id`.
OUT_OF_PLANE_KICK_ANG = 0.25

#: Elements treated as "heavy" for the coplanarity test. Hydrogens are excluded because in RT-1's
#: files the H's sat at mirror-symmetric +/-0.880 A about a plane every heavy atom lay in --
#: including them would have hidden the degeneracy that mattered.
_LIGHT = ("H", "D", "T")

#: C-13's status token. A single spelling, referenced everywhere, so a reader grepping for it
#: finds every site.
TRIPWIRE_ABORTED = "TRIPWIRE-ABORTED"


# =============================================================================================
# C-1 -- a derived quantity is null, never a number, when any input did not converge
# =============================================================================================

def unconverged_inputs(steps):
    """Names of the steps that are NOT established as converged.

    `steps` maps a step name to a dict carrying a `converged` field.

    🔴 Membership is decided by `converged`, NEVER by the presence of a cost field. RT-1's
       `li_ec2_cation` burned 283 core-h and therefore HAD a cost; a `missing[]` computed from
       "is there a number here" declared it present and `r_composite = 1.0365` was published with
       a non-convergence in its denominator (ADR-065).
    🔴 `converged` absent or None counts as NOT converged. Unknown is not permission.
    """
    bad = []
    for name in sorted(steps or {}):
        rec = steps[name] or {}
        if rec.get("converged") is not True:
            bad.append(name)
    return bad


def derived_or_null(steps, compute):
    """`compute(steps)` if every input converged, otherwise `None` plus the reason.

    Returns `(value, provenance)`. `value` is None whenever ANY input step is unconverged --
    there is no partial credit and no "best effort" number, because a number downstream is
    indistinguishable from a measurement.
    """
    bad = unconverged_inputs(steps)
    prov = {
        "n_inputs": len(steps or {}),
        "unconverged_inputs": bad,
        "basis": "converged field, not the presence of a cost field (C-1)",
    }
    if bad:
        prov["null_reason"] = (
            "🔴 not computed: input step(s) %s did not converge. A derived quantity built on a "
            "non-convergence is not a measurement of anything -- ADR-065, where r_composite = "
            "1.0365 was published over a 283 core-h non-convergence." % ", ".join(bad))
        return None, prov
    return compute(steps), prov


# =============================================================================================
# C-2 -- IRC: `indeterminate`, never `fail`
# =============================================================================================

def irc_direction_ok(direction, e_ts_hartree):
    """One IRC direction against C-2's three clauses. Returns (ok, failures[], detail)."""
    d = direction or {}
    detail = {
        "normal_termination": d.get("normal_termination"),
        "n_points": d.get("n_points"),
        "descent_ev": None,
        "min_descent_ev": IRC_MIN_DESCENT_EV,
        "min_points": IRC_MIN_POINTS,
        # 🔴 [critic10] STRUCTURED cause tags, parallel to `fails`. The cause class is derived
        # from THESE, never from substring-matching the prose this function just built: a real
        # B+ bifurcation and a plain step-budget stop both begin "IRC was TRUNCATED (...)", so
        # string mining bucketed a CHEMICAL failure as BUDGET -- dropping it out of the 1/p
        # chemical denominator and prescribing "spend more per attempt" for a broken method.
        "cause_tags": [],
    }
    fails = []
    tags = detail["cause_tags"]
    completion = d.get("completion") or {}

    if d.get("normal_termination") is not True:
        fails.append("normal_termination is %r, not True"
                     % (d.get("normal_termination"),))
        # 🔴 [critic14] A crashed IRC (a real `Error termination` marker present -- see
        # `criteria.g16.parse_irc_completion`'s `error_terminated` field, computed from the log
        # content, never from this prose) is `engine` (§39.69: numerical failure at a geometry
        # the protocol legitimately requested -- change the SCF/numerics, not the caps or the
        # method). Without this, an engine death and a genuine "we don't know" both tagged
        # `unknown`, so `engine` never appeared in the U-56b tally at all despite existing
        # exactly for this case.
        tags.append("engine" if completion.get("error_terminated") else "unknown")

    n = d.get("n_points")
    if not isinstance(n, int) or n < IRC_MIN_POINTS:
        fails.append("n_points = %r, below the required %d" % (n, IRC_MIN_POINTS))
        # 🔴 [§39.116(d), proposer10 RULING -- supersedes an earlier `chemical` guess of mine
        #    that critic14 flagged and I should not have shipped ahead of the geometry read]
        #    A short path where G16 declared a minimum is NOT a budget failure (nothing was
        #    cut short) -- but proposer10 read the ACTUAL geometry on the real U56_RB_scan log
        #    and found the "minimum" is the SADDLE to within ~0.02 Å (max pairwise interatomic
        #    distance change 0.0203 Å forward / 0.0228 Å reverse) -- i.e. the IRC's own
        #    stopping criterion fired trivially on an intrinsically flat coordinate, not
        #    evidence of a real, distinct basin. `chemical` would assert a chemical fact was
        #    measured; NONE was -- ruled OUT of both the budget AND chemical sides of the 1/p
        #    denominator. `protocol` (§39.68(3): "the run says something about OUR PROCEDURE,
        #    not the chemistry or the caps" -- prescription "fix the procedure and re-run") is
        #    the correct class: our IRC stopping criterion is what needs examining (Track B
        #    item 7, e.g. tightened for soft-mode systems), the same shape as the unconverged-
        #    frame-0 case `protocol` was created for, one stage later. NOT `unknown`: that also
        #    excludes both denominators but carries no prescription for a systematic, fixable
        #    defect. This does NOT decide whether such a path PASSES C-2 overall (still fails
        #    IRC_MIN_POINTS above) -- only that its CAUSE is our stopping criterion, not the
        #    chemistry and not our purchasing.
        tags.append("protocol" if completion.get("minimum_found") else "budget")

    e_end = d.get("energy_hartree")
    if e_end is None or e_ts_hartree is None:
        fails.append("endpoint or TS energy missing -- descent cannot be evaluated")
        tags.append("unknown")
    else:
        descent_ev = abs(units.hartree_to_ev(e_end - e_ts_hartree))
        detail["descent_ev"] = descent_ev
        if descent_ev <= IRC_MIN_DESCENT_EV:
            fails.append("descended only %.6f eV, at or below the required %.2f eV"
                         % (descent_ev, IRC_MIN_DESCENT_EV))
            tags.append("chemical")

    # 🔴 [C-2.2, §39.53] TRUNCATION. Measured on the real P1 run: BOTH directions ran 31
    #    points, printed "Maximum number of steps reached." AND "Normal termination", and
    #    descended 0.143 / 0.147 eV -- i.e. they satisfied every clause above while the
    #    energy was STILL falling at a steady rate at the last point (-0.0068 / -0.0054 eV
    #    per point, not decaying). The path ran out of BUDGET; it did not reach a minimum.
    # 🔒 C-2 exists to certify "this TS connects two DISTINCT minima". A run that reached no
    #    minimum cannot certify that, however tidily it terminated. Without this clause the
    #    gate passes a path that connected NOTHING -- which is what happened, twice.
    detail["completion"] = completion or None
    # 🔴 [§39.32(g) condition 7, FINAL form in §39.55(d)] The CONNECTION must be ESTABLISHED,
    #    by EITHER (a) convergence, or (b) `maxpoints` + B+ agreement in this direction.
    #    🔒 (b) IS NOT A WEAKENING: it trades IRC convergence for an ADDITIONAL measurement
    #    that (a) never had to make -- two terminal optimisations from two different points on
    #    the same descending branch, which agree only if the valley between them is intact.
    #    What stays forbidden is what was always forbidden: a truncated IRC with NO endpoint
    #    established, which is exactly what P1 produced and what C-2 as written accepted.
    #    ⚠ An earlier amendment (§39.53) said "must terminate on convergence" full stop; that
    #    would have forbidden B+ outright and forced Option A on every gate attempt. Do not
    #    re-introduce it.
    bplus = d.get("bplus") or {}
    detail["bplus"] = bplus or None
    # 🔴 [§39.114(1)] Branch (b) must NOT trust a bare `agreement: True` when the available IRC
    #    points never got far from the saddle -- see BPLUS_LOW_CONFIDENCE_MIN_POINTS above for
    #    why and the real RA_scan forward/reverse numbers that split on this exact axis. This is
    #    read here, at CONSULT time, from `n` (already computed above) -- `bplus_*.json`'s own
    #    `agreement` field is NEVER mutated (compute-and-record vs. consult stay separate acts,
    #    same principle as the B+-always-recorded comment below); a caller that only reads the
    #    raw record still sees the true measurement, and this function is the one place branch
    #    (b) is actually decided.
    bplus_agreement_effective = bplus.get("agreement")
    bplus_low_confidence = (bplus_agreement_effective is True
                            and (not isinstance(n, int) or n < BPLUS_LOW_CONFIDENCE_MIN_POINTS))
    if bplus_low_confidence:
        bplus_agreement_effective = "low_confidence"
    detail["bplus_agreement_effective"] = bplus_agreement_effective
    # 🔒 [§39.77] There is NO calibration exemption and no reaction-specific gating: B+ runs on
    #    every direction, every time. The mechanism that would have needed a reaction id or a
    #    config flag does not exist, so neither do its failure modes (a hard-coded id that
    #    outlives its reason, a flag set on the wrong item).
    # 🔒 [§39.124 Ruling 2, corrected A1 -- proposer12, `02_METHOD_SPEC.md` correction block]
    #    Condition 7's reactant-match clause is joined by AND OUTSIDE the branch-(a)/branch-(b)
    #    EITHER/OR -- it binds BOTH branches, always on the direction's own `last` endpoint, not
    #    just branch (b). A converged IRC (branch a) to the WRONG minimum must still fail
    #    condition 7; without this, a clean convergence to a different conformer/coordination
    #    basin (or a bifurcation past B+'s last sampled point, R-1/R-2's own named residual risk)
    #    would pass outright.
    #    🔴🔴 [critic16, 27th review batch] OPT-IN, NOT MANDATORY, and the presence check MUST
    #    use `"reactant_match" in d`, NEVER `d.get("reactant_match")` alone -- `.get()` cannot
    #    tell "the caller never supplied this" from "the caller supplied it and it is `None`",
    #    and `payload/U56.sh`'s own error path sets EXACTLY that: `reactant_match["last"] =
    #    None` when the try/except around the computation fails. Under a bare `.get()` read,
    #    that failure-to-compute silently read as "not opted in" and PASSED condition 7 with no
    #    reactant check at all -- the exact bug this comment now documents and the code below
    #    fixes. `reactant_match` is a PRE-COMPUTED `guards.reactant_match()` result the CALLER
    #    supplies for this direction's `last` point (compute-and-record vs. consult stay
    #    separate acts, same principle as `bplus` above -- this function never touches raw
    #    geometry). If the caller does not supply the KEY at all, this clause is SKIPPED
    #    entirely -- today's only real caller (`criteria/p1.py::evaluate_p1`, P1) has no
    #    mapping/reactant wiring and P1 is permanently excluded (ADR-112); retroactively hard-
    #    failing every existing P1 call site is not this fix's job. A caller that supplies the
    #    KEY (anyone implementing condition 7 in full) gets the real, binding clause below --
    #    and a supplied-but-`None`/incomplete value FAILS it, exactly like a supplied `False`.
    reactant_match_supplied = "reactant_match" in d
    reactant_match_last = d.get("reactant_match")
    detail["reactant_match_last"] = reactant_match_last

    def _reactant_match_ok():
        return bool(reactant_match_last) and reactant_match_last.get("match") is True

    def _reactant_match_fail_reason(branch_label):
        rm_match = (reactant_match_last or {}).get("match")
        return (
            "%s, but the `last` endpoint does not (yet) verifiably MATCH the certified "
            "reactant (reactant_match.match=%r) -- §39.124 Ruling 2/A1: the reactant-match "
            "clause binds BOTH branches, not just the truncated one."
            % (branch_label, rm_match))

    if completion.get("truncated") and bplus_agreement_effective is True:
        if reactant_match_supplied and not _reactant_match_ok():
            fails.append(_reactant_match_fail_reason(
                "IRC was TRUNCATED (%s) and B+ agreed"
                % (completion.get("termination_reason") or "reason not recorded")))
            tags.append("chemical" if (reactant_match_last or {}).get("match") is False
                       else "unknown")
        else:
            detail["connection_established_via"] = "b: maxpoints + B+ agreement (§39.55(d))"
    elif completion.get("truncated") and bplus_low_confidence:
        fails.append(
            "IRC was TRUNCATED (%s) and B+ agreed, but only %r points were reached (< %d, "
            "§39.114(1)) -- too close to the saddle to trust B+ as establishing a DISTANT, "
            "independently-confirmed basin. Not disqualifying, but not yet load-bearing either."
            % (completion.get("termination_reason") or "reason not recorded", n,
               BPLUS_LOW_CONFIDENCE_MIN_POINTS))
        tags.append("unknown")
    elif completion.get("truncated"):
        disagreed = bplus.get("agreement") is False
        why = ("B+ DISAGREED (a bifurcation between its two start points)"
               if disagreed
               else "and B+ was not run, so nothing established the endpoint instead")
        fails.append(
            "IRC was TRUNCATED (%s) %s -- it stopped before reaching a minimum, so it "
            "establishes nothing about what the TS connects (C-2.2 / condition 7)"
            % (completion.get("termination_reason") or "reason not recorded", why))
        # 🔴 A B+ DISAGREEMENT IS CHEMISTRY, NOT BUDGET. The two terminal optimisations
        # started on the same descending branch and reached different minima -- that is a
        # bifurcation in the path, and the prescription is "the method or the saddle is
        # wrong", the opposite of "the caps are too tight, spend more".
        tags.append("chemical" if disagreed else "budget")
    elif completion:
        # 🔒 [§39.124 Ruling 2, A1] Branch (a) drops the frame-count/arc-length floor (those
        # exist only to substitute for the ground truth a real convergence already has) but
        # KEEPS the reactant-match check on this direction's own endpoint -- same opt-in shape
        # as branch (b) above, same reason (P1 is the only live caller today and is permanently
        # excluded; a real caller that supplies `reactant_match` gets the binding clause).
        if reactant_match_supplied and not _reactant_match_ok():
            fails.append(_reactant_match_fail_reason("IRC converged"))
            tags.append("chemical" if (reactant_match_last or {}).get("match") is False
                       else "unknown")
        else:
            detail["connection_established_via"] = "a: both directions converged (§39.55(d))"
        # 🔴🔴 [§39.77] B+ IS ALWAYS COMPUTED AND ALWAYS RECORDED; whether it is CONSULTED
        #    depends on the branch. Compute-and-record and consult are DIFFERENT ACTS, and
        #    fusing them is the same defect C-10.1 separated for cost probes and §39.62
        #    separated for Ω -- third instance.
        # 🔴 THIS IS THE ONLY PLACE B+ CAN EVER BE CHECKED. On a converged IRC there is
        #    ground truth; on a truncated one B+ is load-bearing and UNCHECKABLE. So if B+
        #    verdicts were kept only where they were consulted, our record of B+'s reliability
        #    would be conditioned on the cases with no ground truth -- we would only ever store
        #    verdicts we cannot check. That is the success-conditioned denominator in its
        #    purest form (§39.51(a)).
        # 🔴 DIRECTION OF AUTHORITY, stated so nobody reads it backwards: THE IRC WINS HERE.
        #    B+ never overrides a converged IRC. A disagreement impugns B+, not the IRC,
        #    because the IRC is the ground truth B+ is being measured against.
        if bplus:
            agreed = bplus.get("agreement")
            detail["bplus_calibration"] = {
                "checkable": True,
                "bplus_agreement": agreed,
                "irc_is_ground_truth": True,
                "outcome": ("bplus_confirmed" if agreed is True
                            else "bplus_refuted" if agreed is False
                            else "bplus_undetermined"),
                "_authority": ("the converged IRC establishes the connection; this record "
                               "measures B+ AGAINST it and never the other way round"),
                "_why_recorded": ("B+ is validated on zero reactions. A converged IRC is a "
                                 "rare chance to check it (C-2.2 makes truncation the common "
                                 "case), and discarding these would leave B+'s reliability "
                                 "record conditioned on the cases where it cannot be checked."),
            }
        else:
            detail["bplus_calibration"] = {
                "checkable": True, "bplus_agreement": None,
                "outcome": "bplus_not_run",
                "_why_recorded": ("a converged IRC is a checkable case and B+ did not run on "
                                 "it -- a missed calibration opportunity, recorded so the "
                                 "absence is visible rather than indistinguishable from a "
                                 "case that was never checkable"),
            }
    elif not completion:
        fails.append(
            "no IRC completion record -- how the path ENDED was not measured, and "
            "'normal termination' alone does not distinguish a minimum from a step-budget "
            "stop (C-2.1: emit the termination reason)")
    return (not fails), fails, detail


# =============================================================================================
# 🔴 B+ (§39.55) — two terminal optimisations per IRC direction, and whether they agree
# =============================================================================================

#: 🔴 [§39.70(ii), amended §39.71] B+'s ENERGY-AGREEMENT tolerance, in eV.
#:
#: 🔒 THIS IS A DERIVED CONSTANT AND IT IS NOT CONSTANT-FREE. §39.70 called for "the
#: optimiser's own convergence criterion", which presumes an engine that converges on ENERGY.
#: **G16 does not** -- its convergence table has four rows (max/RMS force, max/RMS displacement)
#: and none of them is an energy. The criterion was specified from xtb's behaviour and applied
#: to a G16 stage: the same class as the C-8.1 grid seam, a criterion carried across a boundary
#: it does not survive. proposer7 stated that plainly rather than letting the constant-free
#: claim stand, and so does this comment.
#: What it DOES keep is the property that matters: **every input is a number G16 itself prints.**
#:
#: DERIVATION -- G16's own printed thresholds, multiplied to give the energy scale over which
#: "converged" leaves a structure free to sit:
#:     max force 4.5e-4 Ha/bohr  x  max displacement 1.8e-3 bohr  ~  8e-7 Ha per coordinate
#:     x 3N (63 at 21 atoms)                                      ~  5e-5 Ha  ~  1.4e-3 eV
#: ⚠ The 3N factor makes this size-dependent in principle (~7e-4 eV at 11 atoms). It is ruled
#: FLAT at ~1e-3 eV rather than scaled -- recorded because the derivation says otherwise and a
#: future reader should know the flatness was chosen, not implied.
#:
#: 🟢 CHECKED AGAINST MEASUREMENT, not derived and hoped:
#:     SAME basin, independent optimisations from different starts
#:         11 atoms, 6 kick seeds  -> spread 5e-4 eV     (19_seed_n1)
#:         21 atoms, 5 kick seeds  -> spread 5e-5 eV     (10_seed_basins)
#:     DIFFERENT basin, same system -> 0.686 eV          (10_seed_basins, the sixth seed)
#: ⟹ ~2x above the largest measured same-basin spread, ~700x below the measured different-basin
#:   separation. It passes what it must pass and separates what it must separate.
#: 🔴 Do not tune it to a case. Attack the derivation or the brackets instead -- both are here.
BPLUS_ENERGY_TOLERANCE_EV = 1.0e-3


def bplus_agreement(atoms_a, atoms_b, energy_a_hartree=None, energy_b_hartree=None,
                    energy_tolerance_ev=BPLUS_ENERGY_TOLERANCE_EV, cfg=None):
    """Did the two terminal optimisations of ONE IRC direction land in the SAME valley?

    🔴 [§39.70] THE COMPARATOR, and neither half is an imported constant:
        (i)  identical COVALENT graphs -- **cation-coordination contacts excluded**
        (ii) energies agreeing within THE OPTIMISER'S OWN convergence criterion
    (i) is a graph isomorphism; (ii) is a number the program already converged to -- two
    structures that reached the same minimum agree to within that criterion by definition.

    🔒 WHY NOT `criteria.endpoints.classify_endpoints`, which this function used first: that
    comparator's Layer-I cutoff IS a Li-contact distance, and B+'s hardest cases are exactly
    the ones where two candidate minima differ in Li's position -- so it returned "threshold
    sensitive, no verdict" precisely where B+ was needed. That is §39.48(b) in a new place: a
    STRUCTURAL test cannot separate a soft-coordinate displacement from a reaction-relevant
    one (`d(Li-O)` spans 1.95-3.40 A across 0.06 eV at 11 atoms), and the Layer-I cutoff is
    that same soft coordinate promoted to a decision.
    ⟹ the Li cutoff leaves the DECISION PATH entirely and becomes a reported covariate (C-3).
    🔒 And the deeper reason the reuse was wrong even though "don't build two comparators" is a
    good rule: `classify_endpoints` asks *"are these the same coordination environment"*; B+
    asks *"did these two optimisations fall into the same valley"*. Same words, different
    quantity.

    🟢 THE CONSERVATIVE RULE SURVIVES WHERE IT IS STILL NEEDED: graphs agree but energies do
    not, or the reverse ⟹ genuine ambiguity ⟹ `None`, never `True`. It now fires on a much
    smaller and genuinely ambiguous set instead of on the whole Li-rearrangement class.

    🔴 WHY CLAUSE (ii) SURVIVES AT ALL, since dropping it was the obvious simplification:
    two COORDINATION ISOMERS can share a covalent graph and sit in different basins. That is
    measured, not hypothetical -- §39.42(a) found a 21-atom seed landing **0.686 eV** from its
    five siblings with the same covalent graph. Clause (i) alone would call that agreement.
    """
    out = {"agreement": None, "covalent_graphs_match": None, "energy_delta_ev": None,
           "energy_tolerance_ev": energy_tolerance_ev, "reasons": [],
           "covariates": {}, "constraint": "B+ comparator (02_METHOD_SPEC §39.70/§39.71)"}
    if not atoms_a or not atoms_b:
        out["reasons"].append(
            "one or both terminal optimisations produced no geometry -- B+ establishes "
            "nothing, and an unrun comparison is not an agreement")
        return out
    if len(atoms_a) != len(atoms_b):
        out["reasons"].append(
            "the two terminal optimisations have %d and %d atoms -- not the same system"
            % (len(atoms_a), len(atoms_b)))
        return out

    cfg = cfg or config.graph_layers()
    lc = (cfg.get("layer_C") or cfg.get("layer_c") or {})
    elements = lc.get("elements") or []
    bonds_a = xyzgraph.layer_c_bonds(atoms_a, elements)
    bonds_b = xyzgraph.layer_c_bonds(atoms_b, elements)
    out["covalent_graphs_match"] = (xyzgraph.graph_hash(atoms_a, bonds_a)
                                    == xyzgraph.graph_hash(atoms_b, bonds_b))
    # 🔒 The Li contact is REPORTED, never decided on (C-3). It keeps its
    #    [PLACEHOLDER-ESTIMATE] status as data, which is where a placeholder belongs.
    out["covariates"]["layer_I_cutoffs_ang"] = (cfg.get("layer_I") or {}).get(
        "contact_cutoff_ang")
    out["covariates"]["_note"] = ("cation-coordination contacts are EXCLUDED from the "
                                  "comparison and reported only -- §39.70")

    # 🔴 [§39.124 D(i) cancellation, proposer12] D(i) (a dedicated tight-reopt job to
    #    characterise Li-coordinate displacement between B+ mid/last) was CANCELLED, not
    #    re-scoped: §39.70 already treats cation-coordination as a reported covariate, never a
    #    decision input, and nothing in §39.124(3) reads a Li-displacement number -- a dedicated
    #    job would feed no pass/fail call. Its stated substitute: record the displacement here,
    #    zero new core-h, no new job, same C-3 "report, do not decide" treatment as the Layer-I
    #    cutoff immediately above. Index-paired (same molecule, same atom ordering across the
    #    two B+ optimisations, same assumption `mode_overlap_omega`'s pairing makes) -- if the
    #    Li INDICES themselves differ between the two points, that is reported rather than
    #    silently paired wrong.
    li_a = [i for i, at in enumerate(atoms_a) if at[0] == "Li"]
    li_b = [i for i, at in enumerate(atoms_b) if at[0] == "Li"]
    if li_a and li_a == li_b:
        out["covariates"]["li_displacement_ang"] = max(
            xyzgraph.distance_ang(atoms_a[i], atoms_b[i]) for i in li_a)
        out["covariates"]["_li_displacement_note"] = (
            "max displacement of any Li atom between the two B+ points, reported ONLY (C-3, "
            "§39.70) -- never a decision input")
    elif li_a or li_b:
        out["covariates"]["li_displacement_ang"] = None
        out["covariates"]["_li_displacement_note"] = (
            "Li atom indices differ between the two points (%r vs %r) -- refusing to pair by "
            "position, not computed" % (li_a, li_b))
    else:
        out["covariates"]["li_displacement_ang"] = None
        out["covariates"]["_li_displacement_note"] = "no Li atom in this system"

    if energy_a_hartree is None or energy_b_hartree is None:
        out["reasons"].append(
            "an optimised energy is missing, so the second half of the comparator cannot be "
            "evaluated -- no verdict (Rule 18: unknown is not permission)")
        return out
    out["energy_delta_ev"] = abs(units.hartree_to_ev(energy_a_hartree - energy_b_hartree))
    if not energy_tolerance_ev:
        out["reasons"].append(
            "no energy tolerance -- clause (ii) cannot be evaluated and clause (i) alone would "
            "call two coordination isomers the same basin (measured: 0.686 eV apart with the "
            "same covalent graph). No verdict.")
        return out
    energies_match = out["energy_delta_ev"] <= float(energy_tolerance_ev)

    if out["covalent_graphs_match"] and energies_match:
        out["agreement"] = True
        out["reasons"].append(
            "identical covalent graphs and energies agreeing to %.3g eV within the %.3g eV "
            "tolerance -- the two optimisations fell into the same valley, so the connection "
            "is established (§39.32(g) condition 7 branch (b))"
            % (out["energy_delta_ev"], float(energy_tolerance_ev)))
    elif not out["covalent_graphs_match"] and not energies_match:
        out["agreement"] = False
        out["reasons"].append(
            "different covalent graphs AND energies apart by %.3g eV -- a bifurcation lies "
            "between the two start points. `indeterminate`, never a chemical fail (ADR-066)."
            % out["energy_delta_ev"])
    else:
        out["reasons"].append(
            "🔴 the two halves disagree (covalent graphs %s, energies %s apart by %.3g eV "
            "against %.3g eV) -- genuine ambiguity, so no verdict rather than a guess"
            % ("match" if out["covalent_graphs_match"] else "differ",
               "match" if energies_match else "differ",
               out["energy_delta_ev"], float(energy_tolerance_ev)))
    return out


#: 🔴🔴 [critic16, 04_REVIEW_LOG.md 26th batch, correcting §39.124 finding (b)] proposer12's
#: "0.17 A mid / 0.022 A last" premise was measured on the WRONG artefact: `bplus_reverse_mid.xyz`
#: / `..._last.xyz` are the RAW B+ START geometries (`U56.sh` writes them straight from
#: `g16.parse_irc_path_frames`, BEFORE either optimisation runs -- critic16 verified byte-for-byte
#: identical to the `.gjf` input, zero displacement). The OPTIMISED endpoints (what
#: `bplus_agreement`/`reactant_match` actually consume, via `g16.last_geometry` on the `.log`) tell
#: a different story entirely -- critic16's own measurement, both from files already on disk:
#:     SAME basin   opt reverse mid/last  vs certified reactant   break-bond delta 0.0002 / 0.0005 A
#:     DIFFERENT    opt forward mid/last  vs certified reactant   break-bond delta 1.748  / 1.700  A
#:                  (raw: reactant 1.4143 A; forward mid 3.1620 A; forward last 3.1138 A)
#: ⟹ ~3,400x separation.
#: 🟢 [§39.124 Ruling 1, proposer12, second correction A5] TOLERANCE NOW RULED, two independent
#: derivations landing in the same decade:
#:   (1) bracket-center in log-space: sqrt(0.0005 x 1.7) ~= 0.029 A
#:   (2) G16's own printed loose-optimisation threshold (`Maximum Displacement` = 0.010000 Bohr =
#:       0.00529 A, PER INTERNAL/REDUNDANT COORDINATE -- corrected A5, not "per atom" as first
#:       written, which makes it a MORE direct anchor for a bond-distance tolerance): 0.05 A is
#:       ~10x that, comfortably above loose-optimisation per-coordinate noise.
#: `[ESTIMATE]`, but a better-grounded one than a bare bracket-midpoint alone; supersede if a
#: third measured case lands far from either anchor.
REACTANT_MATCH_TOLERANCE_ANG = 0.05

#: 🟡 [§39.124 Ruling 1, corrected A4, proposer12] Distance alone is NOT sufficient: two
#: COORDINATION ISOMERS can share a covalent graph AND a matching break-bond distance while
#: sitting in different basins (§39.42(a): 0.686 eV apart, same graph -- the exact risk
#: `bplus_agreement`'s own clause (ii) exists for). The reactant-match check reuses the SAME
#: energy tolerance for the SAME reason, no new constant: `certified reactant (opt=tight) vs
#: bplus_reverse_last.log (opt=loose)` measured at Delta = -4.13e-4 eV, ~1,660x below the 0.686 eV
#: coordination-isomer separation -- decisive here, but this specific comparison is NOT a
#: matched-method one (tight vs loose) and should not be leaned on that close to the tolerance in
#: a future, closer case (proposer12's own caveat).
#:
#: 🔒 [critic16, then proposer12 2nd correction A1] CONDITION-7 READING, now settled in full:
#: the reactant-match clause is joined by AND OUTSIDE the branch-(a)/branch-(b) EITHER/OR -- it
#: binds BOTH branches (convergence AND maxpoints+B+), always on the direction's OWN endpoint.
#: "in both branches" names the two ESTABLISHMENT branches, NOT the two B+ sample points; "the
#: reverse endpoint" is singular and `mid` is a midpoint by construction. ⟹ condition 7 binds
#: `last` ONLY. Reporting `mid`'s own reactant-match is still useful data (kept, both here and in
#: the payload wiring) -- it must simply never be ANDed with `last`'s into one verdict.


def reactant_match(atoms_point, atoms_reactant, break_bond_pairs,
                   energy_point_hartree=None, energy_reactant_hartree=None,
                   distance_tolerance_ang=REACTANT_MATCH_TOLERANCE_ANG,
                   energy_tolerance_ev=BPLUS_ENERGY_TOLERANCE_EV, cfg=None):
    """Does ONE B+ terminal-optimisation geometry match the CERTIFIED REACTANT?

    🔴 [§39.124 finding (c)] Condition 7's own ruled text (§39.32(g)): "in both branches the
    reverse endpoint must match the certified reactant." `bplus_agreement()` above never reads
    `reactant_certified.xyz` at all -- it compares the two B+ points ONLY against each other.
    This function is the missing half: ONE B+ point (e.g. `bplus_reverse_mid.xyz` or
    `..._last.xyz`, read as the OPTIMISED geometry via `g16.last_geometry`, never the raw B+
    start geometry) against `reactant_certified.xyz`.

    🔒 [§39.124 Ruling 2, corrected A1] WHICH POINT CONDITION 7 BINDS: `last` only, in BOTH
    branches -- see the module-level comment above this function for the full reading. `mid`'s
    own match is still computed and reported when a caller asks for it (useful diagnostic data)
    -- a caller implementing condition 7 itself must consult `last` ONLY.

    🟢 [§39.124 Ruling 1, corrected A4] TWO clauses, both required for `match = True`, mirroring
    `bplus_agreement`'s own two-clause shape and for the SAME reason (a coordination isomer can
    pass one clause alone):
      (i)  the declared break-bond distance(s) (`break_bond_pairs`, the same `(i, j, label)`
           triples `curvature.mode_overlap_omega` takes, read from `u56_<rxn>_mapping.json` by
           the caller -- NOT hard-coded here) are within `distance_tolerance_ang`
           (`REACTANT_MATCH_TOLERANCE_ANG` = 0.05 A, ruled) of the certified reactant's own.
      (ii) the energy agrees with the certified reactant's within `energy_tolerance_ev`
           (`BPLUS_ENERGY_TOLERANCE_EV`, reused, no new constant).
    A covalent-graph bifurcation (different Layer-C graph from the reactant) is an unambiguous
    non-match regardless of either tolerance -- checked first, independent of both clauses above.

    `distance_tolerance_ang`/`energy_tolerance_ev`: `None` disables that clause's contribution
    (kept overridable for exactly the same reason `bplus_agreement`'s own `energy_tolerance_ev`
    is -- a test or a future re-derivation should not have to edit this function to probe a
    different number).

    🔒 [§39.124 Ruling 1, corrected A4 then C2 -- proposer12's own final form] THREE-WAY
    combination, NOT a plain AND: `match = True` only when BOTH clauses PASS; `match = False`
    only when BOTH clauses DEFINITELY FAIL; a SPLIT (one passes, one fails) or either clause
    simply unmeasured is `match = None` -- the SAME "genuine ambiguity" rule
    `bplus_agreement`'s own clause (i)/(ii) split already uses (its own docstring: "graphs
    agree but energies do not, or the reverse => genuine ambiguity => None, never True"),
    applied a second time here. A covalent-graph bifurcation is checked FIRST and is the only
    way to reach `False` without both of the other two clauses failing together.

    🔴 Element consistency between `atoms_point` and `atoms_reactant` at each declared pair index
    is enforced (raises `ValueError` on mismatch) -- the same guard `mode_overlap_omega` applies,
    because pairing by index across geometries whose atom order silently differs would project
    onto the wrong bond and report a distance for nothing.
    """
    out = {"match": None, "covalent_graphs_match": None, "break_bonds": [], "reasons": [],
           "distance_tolerance_ang": distance_tolerance_ang,
           "energy_tolerance_ev": energy_tolerance_ev, "energy_delta_ev": None,
           "constraint": "condition 7 reactant-match (02_METHOD_SPEC §39.32(g)/§39.124), "
                         "binds the `last` B+ point only, distance AND energy (Ruling 1/2)"}
    if not atoms_point or not atoms_reactant:
        out["reasons"].append(
            "one or both geometries missing -- an unrun comparison is not a match")
        return out
    if len(atoms_point) != len(atoms_reactant):
        out["reasons"].append(
            "the point and the certified reactant have %d and %d atoms -- not the same system"
            % (len(atoms_point), len(atoms_reactant)))
        return out

    cfg = cfg or config.graph_layers()
    lc = (cfg.get("layer_C") or cfg.get("layer_c") or {})
    elements = lc.get("elements") or []
    bonds_p = xyzgraph.layer_c_bonds(atoms_point, elements)
    bonds_r = xyzgraph.layer_c_bonds(atoms_reactant, elements)
    out["covalent_graphs_match"] = (xyzgraph.graph_hash(atoms_point, bonds_p)
                                    == xyzgraph.graph_hash(atoms_reactant, bonds_r))
    if not out["covalent_graphs_match"]:
        out["match"] = False
        out["reasons"].append(
            "🔴 different covalent graphs -- an unambiguous bifurcation from the certified "
            "reactant, needing no distance tolerance to reject (§39.124(c))")
    else:
        out["reasons"].append(
            "covalent graphs agree -- not sufficient by itself: whether that also means "
            "'close enough to the reactant' depends on break_bonds AND a distance tolerance "
            "(see distance_tolerance_ang below).")

    for i, j, label in (break_bond_pairs or []):
        try:
            sym_p_i, sym_p_j = atoms_point[i][0], atoms_point[j][0]
            sym_r_i, sym_r_j = atoms_reactant[i][0], atoms_reactant[j][0]
        except IndexError:
            out["break_bonds"].append(
                {"label": label, "i": i, "j": j,
                 "note": "index out of range for this geometry -- not computed"})
            continue
        if (sym_p_i, sym_p_j) != (sym_r_i, sym_r_j):
            raise ValueError(
                "break-bond pair %r is (%s, %s) in the point and (%s, %s) in the certified "
                "reactant -- refusing to pair them (same failure mode "
                "curvature.mode_overlap_omega guards against: silently different atom order "
                "would project a distance onto the wrong bond)"
                % (label, sym_p_i, sym_p_j, sym_r_i, sym_r_j))
        d_point = xyzgraph.distance_ang(atoms_point[i], atoms_point[j])
        d_reactant = xyzgraph.distance_ang(atoms_reactant[i], atoms_reactant[j])
        out["break_bonds"].append({
            "label": label, "i": i, "j": j,
            "point_ang": d_point, "reactant_ang": d_reactant,
            "delta_ang": abs(d_point - d_reactant),
        })
    if not break_bond_pairs:
        out["reasons"].append(
            "no break/form pairs supplied -- break_bonds is empty, distances not computed "
            "(Rule 18: unknown is not permission)")

    # 🟢 [§39.124 Ruling 1, corrected A4] TWO clauses, AND'd -- distance alone cannot separate a
    # genuine match from a same-graph coordination isomer (§39.42(a): 0.686 eV apart, same
    # graph). Both are evaluated independently below, then combined; this only runs when the
    # graph already agreed (the `False` bifurcation case above already returned/decided).
    distance_ok = None
    if out["covalent_graphs_match"]:
        deltas = [bb["delta_ang"] for bb in out["break_bonds"] if "delta_ang" in bb]
        if distance_tolerance_ang is None:
            out["reasons"].append(
                "no distance_tolerance_ang supplied -- distance clause cannot be evaluated")
        elif not deltas:
            out["reasons"].append(
                "a distance_tolerance_ang was supplied but no break-bond distance was usable "
                "(no pairs, or all out of range) -- distance clause cannot be evaluated")
        else:
            worst = max(deltas)
            distance_ok = bool(worst <= distance_tolerance_ang)
            out["reasons"].append(
                "distance clause %s: worst break-bond delta %.4f A against tolerance %.4f A"
                % ("PASSES" if distance_ok else "FAILS", worst, distance_tolerance_ang))

    energy_ok = None
    if out["covalent_graphs_match"]:
        if energy_point_hartree is None or energy_reactant_hartree is None:
            out["reasons"].append(
                "an energy is missing -- energy clause cannot be evaluated (Rule 18: unknown "
                "is not permission)")
        elif not energy_tolerance_ev:
            out["reasons"].append(
                "no energy_tolerance_ev supplied -- energy clause cannot be evaluated, and "
                "clause (i) alone would call a coordination isomer a match (§39.42(a): 0.686 eV "
                "apart, same graph)")
        else:
            out["energy_delta_ev"] = abs(units.hartree_to_ev(
                energy_point_hartree - energy_reactant_hartree))
            energy_ok = bool(out["energy_delta_ev"] <= float(energy_tolerance_ev))
            out["reasons"].append(
                "energy clause %s: %.6g eV against tolerance %.3g eV"
                % ("PASSES" if energy_ok else "FAILS", out["energy_delta_ev"],
                   float(energy_tolerance_ev)))

    # 🔴🔴 [§39.124 Ruling 1, corrected A4, then C2 -- proposer12's own final, implementation-
    # ready form, checked against critic16 twice] `False` requires BOTH clauses to have
    # DEFINITELY failed -- NOT "at least one failed". A SPLIT (distance passes, energy fails, or
    # the reverse) is `bplus_agreement`'s own "genuine ambiguity" rule applied a second time
    # (`guards.py`'s own header docstring on `bplus_agreement`: "graphs agree but energies do
    # not, or the reverse => genuine ambiguity => None, never True") -- an EARLIER, WRONG draft
    # of this function returned `False` on any single clause failure, which is a DIFFERENT,
    # STRICTER rule than the one actually ruled and ships a false negative on a split.
    if out["covalent_graphs_match"]:
        if distance_ok is True and energy_ok is True:
            out["match"] = True
            out["reasons"].append("match = True: both clauses PASS")
        elif distance_ok is False and energy_ok is False:
            out["match"] = False
            out["reasons"].append("match = False: both clauses FAIL")
        else:
            out["reasons"].append(
                "match stays None: either a genuine SPLIT (one clause passes, the other fails "
                "-- ambiguous, not a guessed False) or not enough data to evaluate both clauses "
                "(distance_ok=%r, energy_ok=%r) -- unknown is not permission"
                % (distance_ok, energy_ok))
    return out


def bplus_sample_points(net_reaction_coordinates):
    """🔴 [§39.70] WHICH two IRC points the terminal optimisations start from:
    **the LAST point and the MIDPOINT BY REACTION COORDINATE (arc length)** — not by index.

    Gaussian prints `NET REACTION COORDINATE UP TO THIS POINT` per point, so the midpoint is
    well defined at ANY point count, including the short IRCs C-2.2 makes common. A fraction of
    the index count would be a constant in disguise; the middle of the arc is the middle.

    🔴 NOT THE EARLIEST POINT, even though it would maximise separation and so sensitivity:
    **a terminal optimisation started too near the saddle can roll back over it into the OTHER
    basin, producing a SPURIOUS DISAGREEMENT.** Do not "improve" this to point 1.

    Returns `(midpoint_index, last_index)` as 0-based indices, or `None` if there are fewer
    than two usable points.
    """
    s = [x for x in (net_reaction_coordinates or []) if x is not None]
    if len(s) < 2:
        return None
    half = abs(s[-1]) / 2.0
    mid = min(range(len(s) - 1), key=lambda k: abs(abs(s[k]) - half))
    return (mid, len(s) - 1)


# =============================================================================================
# 🔴 [§39.116(d), generalised by §39.124 Ruling 3/A2] Is a declared IRC minimum REAL, or a
# repeat of the confirmed §39.116(d) artifact (a fixed force threshold firing trivially on an
# intrinsically flat coordinate right next to the saddle)?
# =============================================================================================

#: 🔴 [§39.124 Ruling 3, CORRECTED A2, proposer12] The original 0.05 A floor was miscalibrated:
#: proposer12 independently re-derived the real reverse arm's own consecutive-point step sizes
#: (0.0538-0.0605 A across points 0-5, 12% spread, no trend) and found 0.05 A sits just BELOW
#: that run's own healthy mid-path band, not safely inside it -- a real success could plausibly
#: land under 0.05 A too, defeating the check on exactly the case it exists to protect.
#: 🔴 [B4, critic16/lead] An earlier draft of this rationale also claimed adaptive integrators
#: "commonly shrink [step size] approaching a stationary point" as a physical justification --
#: THIS RUN'S OWN DATA REFUTES IT (12% spread, no trend across points 0-5) and the claim is
#: struck. The fix below does not depend on it: the floor is fixed to §39.116(d)'s own
#: confirmed-artifact magnitude (0.0203-0.0228 A) with ~2x margin, a measured anchor, not a
#: mechanism story.
MINIMUM_DISTINCTNESS_FLOOR_ANG = 0.025


def structural_distinctness(atoms_a, atoms_b):
    """Max |change| in ANY pairwise interatomic distance between two geometries of the SAME atom
    count/order -- rotation- AND translation-invariant BY CONSTRUCTION (interatomic distances do
    not depend on how a structure is placed in space, so no alignment/Kabsch step is needed).

    🔴 [§39.116(d)] THE metric that showed `U56_RB_scan`'s declared "minimum" was 0.0203
    (forward) / 0.0228 (reverse) Å from its own saddle -- i.e. the IRC's stopping criterion fired
    on an artifact, not a real distinct structure. §39.124 Ruling 3 generalises it from
    minimum-vs-SADDLE (its original, single-post-saddle-point use) to minimum-vs-ANY preceding
    path point -- the same conceptual metric on a different point pair, not an identical
    re-derivation (stated so a reader does not assume a closer correspondence than exists).

    Returns `None` if the two geometries are missing or do not have the same atom count (not
    comparable) -- Rule 18: unknown is not permission, never a silent zero.
    """
    if not atoms_a or not atoms_b or len(atoms_a) != len(atoms_b):
        return None
    n = len(atoms_a)
    worst = 0.0
    for i in range(n):
        for j in range(i + 1, n):
            worst = max(worst, abs(xyzgraph.distance_ang(atoms_a[i], atoms_a[j])
                                   - xyzgraph.distance_ang(atoms_b[i], atoms_b[j])))
    return worst


#: 🔴 [§39.124 Ruling 3, corrected C1, critic16/proposer12] Minimum sample size before the
#: self-calibrating relative check is trusted at all. Below this, a "median" is degenerate --
#: the confirmed failure mode named directly: `U56_RB_scan` has exactly ONE post-saddle point,
#: so a naive median-of-available-deltas would use that single delta as its own yardstick
#: (`delta < 0.5 * delta` can never be true), silently disabling the relative check on exactly
#: the case §39.116(d) exists to catch. Below this count, ONLY the absolute floor applies.
MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS = 3


def minimum_distinctness(atoms_declared_min, atoms_preceding, consecutive_deltas_ang=None,
                         absolute_floor_ang=MINIMUM_DISTINCTNESS_FLOOR_ANG):
    """Is a declared IRC minimum structurally DISTINCT from the path point immediately before
    it, or is it "artifact-suspicious" (§39.124 Ruling 3)?

    🟢 [corrected C1, critic16/proposer12] TWO signals, combined with OR, NEVER an if/else that
    lets one stop applying once the other is available -- an if/else (an EARLIER, WRONG draft of
    this function) would have let the absolute floor stop applying entirely once >=3 prior
    deltas exist, missing a uniformly-degenerate path (e.g. one that never leaves the saddle
    region at all: a small median alongside a small tested delta would clear a RELATIVE test
    while both are objectively tiny -- exactly the class §39.116(c) warned about for other
    soft/floppy Li-coordinate TS attempts). The RULED form:
        suspicious = (delta <= absolute_floor_ang)
                     OR (len(prior_deltas) >= MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS
                         AND delta < 0.5 * median(prior_deltas))
      (i)  an ABSOLUTE FLOOR at `absolute_floor_ang` (0.025 A default) -- §39.116(d)'s own
           confirmed-artifact magnitude (0.0203-0.0228 A) with ~2x margin. ALWAYS evaluated.
      (ii) a SELF-CALIBRATING RELATIVE check, ADDITIONALLY evaluated only when at least
           `MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS` (3) prior consecutive-point deltas are
           available (`consecutive_deltas_ang` -- the caller's OWN deltas from BEFORE the step
           under test, excluding it): suspicious if the declared-minimum delta is under HALF of
           that run's OWN median -- free (the run already produces this data) and robust to
           route/system-specific step-size scale in a way no fixed constant can be. Below the
           minimum sample size, this signal is SKIPPED, not degraded to a meaningless one-point
           "median" (see `MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS`'s own docstring for the exact
           failure this prevents).

    Returns a dict, never a bare bool -- `suspicious` is the flag, `delta_ang` is the reported
    measurement (C-3: report, do not silently gate). §39.124 Ruling 3's own prescription: a
    suspicious delta needs a HUMAN READ before being counted as a real branch-(a) minimum; this
    function does not decide that on its own, and nothing in this codebase currently auto-gates
    on `suspicious` (flagged, not wired -- see guards.py's own header, no caller today supplies
    the path-frame geometry this needs).
    """
    delta = structural_distinctness(atoms_declared_min, atoms_preceding)
    out = {"delta_ang": delta, "absolute_floor_ang": absolute_floor_ang,
           "median_consecutive_delta_ang": None, "n_prior_deltas": None, "suspicious": None,
           "reasons": [],
           "constraint": "IRC minimum distinctness (§39.116(d), generalised by §39.124 Ruling 3/A2)"}
    if delta is None:
        out["reasons"].append(
            "geometries missing or atom-count mismatch -- distinctness not measurable")
        return out
    below_floor = delta <= absolute_floor_ang
    out["reasons"].append(
        "%.4f A against the %.4f A absolute floor (%s)"
        % (delta, absolute_floor_ang, "AT/BELOW -- artifact-suspicious" if below_floor
           else "clear"))
    prior_deltas = sorted(d for d in (consecutive_deltas_ang or []) if d is not None)
    out["n_prior_deltas"] = len(prior_deltas)
    below_half_median = False
    if len(prior_deltas) >= MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS:
        mid_idx = len(prior_deltas) // 2
        median = (prior_deltas[mid_idx] if len(prior_deltas) % 2
                 else (prior_deltas[mid_idx - 1] + prior_deltas[mid_idx]) / 2.0)
        out["median_consecutive_delta_ang"] = median
        below_half_median = delta < 0.5 * median
        out["reasons"].append(
            "%.4f A against half this run's own median consecutive-point delta (%.4f A, n=%d "
            "prior) (%s)"
            % (delta, 0.5 * median, len(prior_deltas),
               "BELOW -- artifact-suspicious" if below_half_median else "clear"))
    else:
        out["reasons"].append(
            "only %d prior consecutive-point delta(s) supplied (< %d) -- relative check "
            "SKIPPED, not degraded to a meaningless small-sample median (§39.124 Ruling 3 "
            "corrected C1); the absolute floor above is the only signal here"
            % (len(prior_deltas), MINIMUM_DISTINCTNESS_MIN_PRIOR_DELTAS))
    # 🔒 OR, never if/else -- see this function's own docstring for the exact case an if/else
    #    would silently miss.
    out["suspicious"] = below_floor or below_half_median
    if out["suspicious"]:
        out["reasons"].append(
            "🟡 §39.124 Ruling 3: a suspicious delta needs a HUMAN READ before being counted as "
            "a real branch-(a) minimum; if unavailable, fall through to branch (b)'s criterion")
    return out


# =============================================================================================
# 🔴 THE BRACKET CHECK (§39.63) — the FIRST gate on a TS candidate, and the cheapest
# =============================================================================================

def bracket_check(saddle_distances_ang, reactant_distances_ang, product_distances_ang=None,
                  labels=None, directions=None):
    """Where a TS candidate's BREAKING bonds sit relative to its certified endpoints (§39.63,
    §39.65). Two checks, and they are NOT interchangeable:

      ONE-SIDED (always, every arm)   the saddle distance must not be SHORTER than the
          certified REACTANT's. A "transition state" with the bond MORE FORMED than the
          reactant is not on a bond-breaking path at all. Every arm has a certified reactant,
          so this is available today and uses certified numbers only.
          🔴 IT DOES NOT CATCH P1. P1 failed on the PRODUCT side (3.184 A against a product at
          2.503). This half must never be described as though it inherited that hit.
      TWO-SIDED (only where a product is certified)   the saddle distance must lie strictly
          BETWEEN the two endpoints. This is the half with the demonstrated hit.

    🔒 NO THRESHOLD in either half: both endpoint values are C-8-certified numbers we already
    hold, and "between" / "not shorter than" are not tunable.

    🔴 WHY THE PRODUCT SIDE IS OFTEN ABSENT, AND WHY THAT IS NOT A REFUSAL: R-B is single-ended
    precisely because its product is the CHEMICAL CLAIM THE RUN EXISTS TO TEST (§39.39(d)) --
    certifying a product would assume the branching being measured. Refusing there would cost a
    REACTION, the expensive error (§39.62(b)). So the product side is recorded as
    `awaiting_calibration` and COUNTED. ⚠ That string is deliberately not a bare "not
    applicable": §39.65(3) has a free calibration landing in the same round (R-A holds BOTH a
    certified product distance and a GFN2 product-side distance from its own forward scan, and
    their difference MEASURES the GFN2-vs-DFT offset for this coordinate), after which R-B/R-C
    can bracket against a GFN2 product end widened by a MEASURED offset.
    🔴 Do NOT substitute a raw GFN2 product distance in the meantime. "A GFN2 bracket is looser"
    is UNVERIFIED and may be backwards: if GFN2's product-side distance comes out SHORTER than
    DFT's, the bracket is TIGHTER and this check false-blocks.

    ⚠ SHARED FALSE-BLOCK CHANNEL, stated rather than argued away: both halves presume the
    saddle lies on the reactant->product side of each declared coordinate, so a concerted
    mechanism that genuinely overshoots would be refused. Acceptable only because the response
    is `indeterminate` WITH A NAMED CAUSE, and because firings are COUNTED (§0-o.4 rule 2): if
    it never fires it is unreached; if it always fires the endpoints or the mapping are wrong
    rather than the chemistry.

    Distances are Angstrom, keyed alike in all dicts. A bond missing from the saddle or the
    reactant is a refusal, not a skip (Rule 18: unknown is not permission).
    """
    labels = list(labels or sorted(saddle_distances_ang or {}))
    product_distances_ang = product_distances_ang or {}
    out = {"refused": False, "bonds": [], "reasons": [],
           "product_side_status": None,
           "constraint": "bracket check (§39.63, one-sided half §39.65)"}
    n_two_sided = 0
    for key in labels:
        d_ts = (saddle_distances_ang or {}).get(key)
        d_r = (reactant_distances_ang or {}).get(key)
        d_p = product_distances_ang.get(key)
        rec = {"bond": key, "saddle_ang": d_ts, "reactant_ang": d_r, "product_ang": d_p,
               "one_sided_ok": None, "two_sided_ok": None}
        if d_ts is None or d_r is None:
            rec["note"] = ("missing saddle or reactant distance (saddle=%r reactant=%r) -- an "
                           "unmeasured coordinate is not a passed one" % (d_ts, d_r))
            out["refused"] = True
            out["reasons"].append("bracket check cannot be evaluated for %s: %s"
                                  % (key, rec["note"]))
            out["bonds"].append(rec)
            continue

        # 🔴 [§39.66] DIRECTION-AWARE. The bound a certified reactant alone can enforce
        # depends on which way the coordinate moves:
        #     BREAK  distance grows  -> refuse if the saddle is SHORTER than the reactant
        #     FORM   distance shrinks -> refuse if the saddle is LONGER  than the reactant
        # 🟢 This is what closes the coverage gap: P1's Li-O2 (a FORMING mechanism coordinate)
        # is 3.980 A at the saddle against a reactant at 2.489 -- 1.491 A past the reactant, on
        # the exact side a reactant-only bound can see. So the one-sided half catches P1 on
        # ALL THREE arms today, with certified numbers only.
        # 🔴 CREDIT WHERE IT IS DUE, and do not let this blur: the BREAKING-bond half alone
        # does NOT catch P1 -- there the saddle overshoots past the PRODUCT, which a
        # reactant-only bound cannot see. The hit belongs to the mechanism/form coordinate.
        # 🔴 [critic10] AN ABSENT DIRECTION IS `None`, NOT `"break"`. Defaulting to break gives
        # a FORMING coordinate break semantics, and a forming coordinate that has moved the
        # wrong way then passes silently -- on P1's own numbers, Li-O2 (reactant 2.489, saddle
        # 3.980) would PASS under a break default instead of being refused, and that is the
        # exact coordinate §39.66 exists to catch it with. `None` costs the one-sided bound on
        # that coordinate but the loss is COUNTED and visible, which a wrong default is not.
        supplied = (directions or {})
        direction = supplied.get(key)
        rec["direction"] = direction
        rec["direction_source"] = ("derived" if key in supplied and direction is not None
                                   else "absent -- no one-sided bound, counted")
        if direction is None:
            # 🔴 Non-monotonic: no well-defined direction, so no one-sided bound. Counted,
            #    never silently dropped -- an unmeasurable coordinate is not a passed one.
            rec["one_sided_ok"] = None
            rec["applicable"] = False
            rec["note"] = ("no usable direction (non-monotonic, or none supplied) -- no "
                           "one-sided bound for this coordinate")
            out.setdefault("non_monotonic", []).append(key)
        elif direction == "form":
            rec["one_sided_ok"] = bool(d_ts <= d_r)
            if not rec["one_sided_ok"]:
                out["refused"] = True
                out["reasons"].append(
                    "🔴 %s is %.3f A at the saddle, LONGER than the certified reactant's "
                    "%.3f A, and this coordinate FORMS along the path -- the saddle is further "
                    "from forming it than the reactant is (§39.66 one-sided, form)."
                    % (key, d_ts, d_r))
        else:
            rec["one_sided_ok"] = bool(d_ts >= d_r)
            if not rec["one_sided_ok"]:
                out["refused"] = True
                out["reasons"].append(
                    "🔴 %s is %.3f A at the saddle, SHORTER than the certified reactant's "
                    "%.3f A -- the bond is more formed than in the reactant, so this is not a "
                    "saddle on a bond-breaking path (§39.66 one-sided, break)." % (key, d_ts, d_r))

        if d_p is None:
            rec["product_side"] = "awaiting_calibration"
        else:
            n_two_sided += 1
            lo, hi = (d_r, d_p) if d_r <= d_p else (d_p, d_r)
            rec["bracket_ang"] = [lo, hi]
            rec["two_sided_ok"] = bool(lo < d_ts < hi)
            if not rec["two_sided_ok"] and rec["one_sided_ok"]:
                out["refused"] = True
                out["reasons"].append(
                    "🔴 %s is %.3f A at the saddle but the certified endpoints bracket it at "
                    "[%.3f, %.3f] -- the saddle is beyond the product. The bond this saddle is "
                    "supposed to be breaking is already broken (§39.63)."
                    % (key, d_ts, lo, hi))
        out["bonds"].append(rec)

    if not out["bonds"]:
        out["refused"] = True
        out["reasons"].append(
            "no breaking bond was checked -- with nothing to bracket, this gate establishes "
            "nothing and must not read as a pass")
    else:
        out["product_side_status"] = ("checked" if n_two_sided == len(out["bonds"])
                                      else "awaiting_calibration")
        if out["product_side_status"] == "awaiting_calibration":
            out["reasons"].append(
                "product side AWAITING CALIBRATION for %d of %d bonds -- no certified product "
                "for this arm (by design where the product is the claim under test). The "
                "one-sided half DID run; it does not catch a saddle that overshoots the "
                "product and must not be read as though it did (§39.65)."
                % (len(out["bonds"]) - n_two_sided, len(out["bonds"])))
        if not out["refused"]:
            out["reasons"].append(
                "every breaking bond passed the checks available for this arm")
    return out


#: 🔴🔴 WHY `indeterminate` MUST CARRY A CAUSE CLASS (engineer7, 2026-08-20).
#: A tight cap produces `indeterminate` verdicts for BUDGET reasons (step budget, wall cap,
#: cumulative per-endpoint budget, maxcycles) that look identical to CHEMICAL ones (mode
#: overlap below the floor, a bidirectional disagreement, an IRC that connects the wrong pair).
#: 🔒 If the two are POOLED, the measured success rate `p` falls for reasons that are our own
#: PURCHASING decisions; `1/p` (the wave-1 sizing multiplier) inflates on that; S3 reads as more
#: expensive than it is; and the natural response -- tighten the caps -- makes it worse. Every
#: step of that loop looks like a chemistry finding and none of it is one.
#: ⟹ `1/p` may ONLY be computed over the CHEMICAL-class denominator.
#: ⟹ A large BUDGET class is itself a diagnostic: the caps are wrong (spend more per attempt).
#:   A large CHEMICAL class means the method is wrong (stop and fix it). OPPOSITE responses.
INDETERMINATE_BUDGET_MARKERS = (
    "truncated", "maxpoints", "wall", "budget", "timeout", "maxcycles",
    "step budget", "cap",
)

#: "we did not measure it" is its OWN class. Folding it into either real class puts an
#: unmeasured case into a denominator that claims to know why -- the same move this whole
#: taxonomy exists to prevent.
INDETERMINATE_UNKNOWN_MARKERS = ("not measured", "no irc completion record",
                                 "reason not recorded")

#: 🔴 [§39.68(3)] `protocol` is a FOURTH real class: the run says something about OUR PROCEDURE
#: rather than about the chemistry or about our caps. An unsettled reference frame, a
#: pre-relaxation that did not converge -- these must not enter the chemical tally (they would
#: corrupt U-56b exactly as budget-truncated nulls would) and they are not a purchasing
#: decision either. The prescription is a third one again: fix the protocol and re-run.
#: 🔴 [§39.69] `engine` — the FIFTH class. Defined by its PRESCRIPTION, with the boundary
#: stated so it cannot grow until it means nothing:
#:   **the calculation could not be COMPLETED for numerical reasons internal to the
#:     electronic-structure method, AT A GEOMETRY THE PROTOCOL LEGITIMATELY REQUESTED.**
#:   IN  : SCF non-convergence · basis linear dependence · integration-grid failure
#:   OUT : out-of-memory        -> BUDGET   (we chose the memory)
#:         a malformed deck     -> PROTOCOL (we built it)
#:         a geometry the protocol should never have requested -> PROTOCOL
#: 🔒 That trailing clause is what makes the boundary DECIDABLE rather than a judgement call.
#: Why it is not folded into an existing class -- each would send a reader to the wrong lever:
#:   chemical: `p` falls for an ENGINE reason (the corruption §39.59(c) forbids), and "fix the
#:             method" does nothing for an SCF that will not converge
#:   budget:   "loosen the caps" does nothing either
#:   protocol: the procedure ran exactly as ruled -- and it would poison PROTOCOL's own
#:             diagnostic, whose whole meaning is "OUR RULES ARE WRONG"
#:   unknown:  invisible to every reading, so nobody is prompted to act
#: 🟢 Its actual lever, from §39.69(2): GUESS PROPAGATION AND CONVERGENCE PATH. 186 GFN2 frames
#: across 11/21/31 atoms show ZERO SCF warnings -- including R-A over the same coordinate range
#: that failed here -- so the failure is PATH-sensitive, not a property of the surface or of
#: system size. ⚠ Zero of 186 bounds the rate only loosely (95% upper ~1.6%/frame) and says
#: nothing about DFT, where the SCF is a harder problem. It refutes "ordinary outcome"; it does
#: not establish "rare".
INDETERMINATE_CAUSE_CLASSES = ("chemical", "budget", "protocol", "engine", "unknown", "mixed")

#: xtb / G16 failure kinds that are `engine` by the definition above. Anything not listed is
#: NOT silently engine -- an unrecognised failure stays `unknown` until someone classifies it.
ENGINE_FAILURE_KINDS = ("scf_not_converged", "basis_linear_dependence", "grid_failure")


def classify_engine_failure(kind):
    """A parsed failure kind -> `engine` or None. 🔴 None means "not classified here", not
    "harmless": the caller must fall back to `unknown` rather than inventing a class."""
    return "engine" if kind in ENGINE_FAILURE_KINDS else None


def _class_from_tags(tags):
    """Structured cause tags -> one class. `None` when there are no tags (not indeterminate,
    or a caller that supplied only free text)."""
    seen = set(t for t in (tags or []) if t)
    if not seen:
        return None
    return seen.pop() if len(seen) == 1 else "mixed"


def classify_indeterminate(reasons):
    """`indeterminate` 의 원인 계급 → "chemical" | "budget" | "mixed" | None.

    None = 사유가 없다(= indeterminate 가 아니다). 판정이 아니라 **분류**이며, 분모를
    나누기 위해서만 쓴다. 🔴 애매하면 `mixed` 로 남긴다 — 둘 중 하나로 밀어 넣는 순간
    한쪽 분모가 조용히 오염된다.
    """
    reasons = [r for r in (reasons or []) if r]
    if not reasons:
        return None
    seen = set()
    for r in reasons:
        low = r.lower()
        if any(m in low for m in INDETERMINATE_UNKNOWN_MARKERS):
            seen.add("unknown")
        elif any(m in low for m in INDETERMINATE_BUDGET_MARKERS):
            seen.add("budget")
        else:
            seen.add("chemical")
    if len(seen) > 1:
        return "mixed"
    return seen.pop()


def irc_verdict(forward, reverse, e_ts_hartree):
    """C-2. Returns a dict whose `status` is `ok` or `indeterminate` -- never `fail`.

    🔴 `fail` is reserved for CHEMISTRY. "The TS is wrong" and "the IRC did not run" have
       identical symptoms and OPPOSITE prescriptions; giving them one exit code is what turned
       RT-1's P1 into a chemical verdict it could not earn (ADR-066).
    🔴 A caller may NOT downgrade `indeterminate` to `fail`. `may_render_chemical_verdict` is the
       only field that authorises one, and it is False unless BOTH directions pass all three
       clauses.
    """
    fwd_ok, fwd_fails, fwd_detail = irc_direction_ok(forward, e_ts_hartree)
    rev_ok, rev_fails, rev_detail = irc_direction_ok(reverse, e_ts_hartree)
    ok = fwd_ok and rev_ok
    out = {
        "status": "ok" if ok else "indeterminate",
        # 🔴 [critic10] Derived from the STRUCTURED tags the clauses emitted, with the
        # string-based classifier kept only as a fallback for callers that pass their own
        # free-text reasons. Classification must not depend on message wording.
        "cause_class": (_class_from_tags(fwd_detail.get("cause_tags", [])
                                         + rev_detail.get("cause_tags", []))
                        or classify_indeterminate(fwd_fails + rev_fails)),
        "may_render_chemical_verdict": bool(ok),
        "forward": fwd_detail,
        "reverse": rev_detail,
        "forward_failures": fwd_fails,
        "reverse_failures": rev_fails,
        "constraint": "C-2 (02_METHOD_SPEC §39.12)",
        "warnings": [],
    }
    if not ok:
        # Rule 13: the field is read by code, warnings[] is read by a human. Both are required.
        out["warnings"].append(
            "🔴 irc_indeterminate: the IRC did not establish a path, so NO chemical verdict may "
            "be drawn from it in EITHER direction. forward=[%s] reverse=[%s]. This is NOT "
            "evidence that the transition state is wrong -- C-2, after ADR-066."
            % ("; ".join(fwd_fails) or "ok", "; ".join(rev_fails) or "ok"))
    return out


# =============================================================================================
# C-9 -- planar-degeneracy detection and the out-of-plane kick
# =============================================================================================

#: 🔒 WHAT THE COPLANARITY TEST DOES AND DOES NOT COVER. Emitted as DATA, not prose, so a reader
#: of a B0 report cannot infer coverage that is not there (Rule 20: state the PROPERTY the check
#: establishes, not the name of what it ran on).
SYMMETRY_COVERAGE = {
    "check_name": "heavy_atom_coplanarity_only",
    "covers": ["a fully planar heavy-atom set (the mirror plane it implies)"],
    "does_NOT_cover": [
        "proper rotation axes (Cn) -- an atom ON an axis is not detected",
        "a mirror plane of the fragment when the whole structure is NOT planar",
        "inversion centres",
        "improper axes (Sn)",
        "any symmetry element of the REMAINING fragment that C-9's revised wording names",
    ],
    "measured_gap": ("li_ec2_cation has Li on a mirror plane and heavy atoms that are NOT "
                     "coplanar: this test returns is_coplanar=False and the pathology passes."),
    "full_detection_status": ("point-group detection + perturbation is registered as PRODUCTION "
                              "work and is deliberately NOT implemented. B0 barely needs it -- "
                              "arm 1 starts from optimised conformers and arm 2 is unperturbed "
                              "ON PURPOSE -- but a check that reads as a guarantee it does not "
                              "give is what must not ship."),
}

#: Distances agreeing to within this are EXACTLY degenerate, i.e. the fingerprint of an atom
#: sitting on a symmetry element. 🔴 CODER-CHOSEN. Chemically meaningless as a length; it is a
#: numerical-identity threshold, not a tolerance on a physical quantity.
EXACT_DEGENERACY_TOL_ANG = 1e-3


def symmetric_placement_flags(atoms, centre="Li", tol_ang=EXACT_DEGENERACY_TOL_ANG):
    """CHEAP, TARGETED detection of the two pathologies we have actually observed.

    Looks for EXACT distance degeneracy from `centre` to same-element atoms. An atom sitting on a
    symmetry element of the rest is equidistant from the atoms that element exchanges, and
    equidistant to numerical identity -- which a real, relaxed structure essentially never is.

    🔴 THIS IS NOT POINT-GROUP DETECTION AND MUST NOT BE READ AS IT. It is a fingerprint with a
       known coverage (`SYMMETRY_COVERAGE`) and no completeness claim: it can miss an element that
       exchanges no same-element pair, and it says nothing about WHICH element it found.

    🔴🔴 MEASURED, AND IT IS THE POINT OF THE WHOLE ITEM: a GFN2 `--opt tight` optimisation of
       `li_ec_cation` from the idealised start STILL SHOWS THE DEGENERACY (C@5.04, O@3.75, H@5.64
       against the idealised C@5.25, O@4.03, H@5.85). **The optimiser does not break the
       symmetry**, because the gradient along the symmetry-breaking coordinate is exactly zero.
       ⟹ arm 1's pre-optimisation improves the starting energy and does NOT remove this
         pathology. Only an explicit perturbation does.
    """
    from .criteria import xyzgraph

    idx = [i for i, a in enumerate(atoms or []) if a[0] == centre]
    out = {
        "centre": centre,
        "tolerance_ang": tol_ang,
        "degenerate_sets": [],
        "flagged": None,
        "is_point_group_detection": False,
        "coverage": dict(SYMMETRY_COVERAGE),
        "warnings": [],
    }
    if not idx:
        out["warnings"].append(
            "🔴 symmetric_placement_not_checked: no %s atom present. `flagged` is None (not "
            "False) -- nothing was examined." % centre)
        return out

    c = idx[0]
    by_el = {}
    for i, a in enumerate(atoms):
        if i == c:
            continue
        by_el.setdefault(a[0], []).append((i, xyzgraph.distance_ang(atoms[c], a)))
    for el in sorted(by_el):
        pairs = sorted(by_el[el], key=lambda t: t[1])
        run = [pairs[0]]
        for prev, cur in zip(pairs, pairs[1:]):
            if abs(cur[1] - prev[1]) < tol_ang:
                run.append(cur)
            else:
                if len(run) > 1:
                    out["degenerate_sets"].append(
                        {"element": el, "n": len(run), "distance_ang": round(run[0][1], 6),
                         "atom_indices": [t[0] for t in run]})
                run = [cur]
        if len(run) > 1:
            out["degenerate_sets"].append(
                {"element": el, "n": len(run), "distance_ang": round(run[0][1], 6),
                 "atom_indices": [t[0] for t in run]})

    out["flagged"] = bool(out["degenerate_sets"])
    if out["flagged"]:
        out["warnings"].append(
            "🟡 exact_distance_degeneracy: %s is equidistant (to %g A) from %d same-element "
            "set(s): %s. That is the fingerprint of an atom sitting on a SYMMETRY ELEMENT of the "
            "rest, which C-9's revised wording forbids as a TS-search start. 🔴 This is a "
            "FINGERPRINT, not point-group detection -- see `coverage`. 🔴 And note a GFN2 "
            "optimisation does NOT remove it: the symmetry-breaking gradient is exactly zero."
            % (centre, tol_ang, len(out["degenerate_sets"]),
               ", ".join("%dx %s@%.3f" % (d["n"], d["element"], d["distance_ang"])
                         for d in out["degenerate_sets"])))
    return out


def heavy_atoms(atoms):
    return [a for a in (atoms or []) if a[0] not in _LIGHT]


def coplanarity(atoms, tolerance_ang=COPLANAR_TOL_ANG):
    """Max out-of-plane deviation of the HEAVY atoms from their own best-fit plane, in Angstrom.

    Returns a dict. `is_coplanar` is `None` -- not False -- when there are fewer than four heavy
    atoms, because three or fewer points are coplanar trivially and the question is not
    meaningful. `None` reads as "not checked"; `False` would read as "checked, and it is fine".
    """
    hv = heavy_atoms(atoms)
    out = {
        "n_heavy": len(hv),
        "tolerance_ang": tolerance_ang,
        "max_out_of_plane_ang": None,
        "is_coplanar": None,
        "normal": None,
        "note": None,
    }
    if len(hv) < 4:
        out["note"] = ("fewer than 4 heavy atoms -- coplanarity is trivially true and carries no "
                       "information about a symmetry degeneracy")
        return out

    n = float(len(hv))
    cx = sum(a[1] for a in hv) / n
    cy = sum(a[2] for a in hv) / n
    cz = sum(a[3] for a in hv) / n
    cov = [[0.0] * 3 for _ in range(3)]
    for _sym, x, y, z in hv:
        d = (x - cx, y - cy, z - cz)
        for i in range(3):
            for j in range(3):
                cov[i][j] += d[i] * d[j]

    # 🔒 ONE eigensolver for the package (sei_pilot/linalg.py). A second copy here is the
    #    "same truth in two places" shape. Jacobi handles the DEGENERATE case correctly, which is
    #    not academic: >= 4 COLLINEAR heavy atoms give two zero eigenvalues, and the routine then
    #    returns an arbitrary but orthonormal normal rather than failing. See the collinear test.
    normal, _smallest = linalg.smallest_eigenvector(cov)

    worst = max(abs((x - cx) * normal[0] + (y - cy) * normal[1] + (z - cz) * normal[2])
                for _sym, x, y, z in hv)
    out["max_out_of_plane_ang"] = worst
    out["is_coplanar"] = bool(worst <= tolerance_ang)
    out["normal"] = normal
    return out


def perturb_out_of_plane(atoms, seed, kick_ang=OUT_OF_PLANE_KICK_ANG,
                         tolerance_ang=COPLANAR_TOL_ANG):
    """Break a planar degeneracy along the best-fit plane's NORMAL, reproducibly.

    Returns `(atoms, provenance)`. If the structure is not coplanar the atoms are returned
    unchanged and `provenance['applied']` is False -- the guard does not silently move geometry
    that did not need moving.

    🔴 The displacement is signed per atom from `random.Random(seed)`, so it is reproducible from
       `seed_id` alone. `seed_id` shares its definition with `seeding.provenance` (C-4 / ADR-051):
       one definition, or the seed-split capture-recapture D1 cannot be done after the fact.
    🔴 Hydrogens move with the heavy atoms. In RT-1's endpoints the H's were already at mirror-
       symmetric +/-0.880 A; kicking only the heavy atoms would have left the mirror plane
       partially intact.
    """
    import random

    cop = coplanarity(atoms, tolerance_ang=tolerance_ang)
    prov = {
        "applied": False,
        "kick_ang": kick_ang,
        "coplanarity": cop,
        "constraint": "C-9 (02_METHOD_SPEC §39.12, after ADR-066)",
        # 🔴 B-2: this perturbation ALONE is insufficient for Gaussian, regardless of whether it
        # fires on THIS call (`applied` above). G16 does not merely fail to break a degenerate
        # guess -- it actively RE-DETECTS the point group and re-imposes it. Any G16 route built
        # from a geometry this function has touched MUST carry `nosymm` explicitly; see
        # `guards.require_nosymm_if_needed` / `config/qc_levels.json`'s
        # `_nosymm_required_job_types`. Do not read this note as satisfied by the perturbation
        # above -- it is a requirement on the ROUTE, not on the geometry.
        "route_must_carry_nosymm_or_g16_undoes_this": True,
    }
    if not cop.get("is_coplanar"):
        prov["reason"] = ("not coplanar within %.3f A (max deviation %s) -- nothing to break"
                          % (tolerance_ang, cop.get("max_out_of_plane_ang")))
        return [tuple(a) for a in (atoms or [])], prov

    rng = random.Random(seed)
    nx, ny, nz = cop["normal"]
    out = []
    for sym, x, y, z in atoms:
        # Uniform in [-kick, +kick] along the normal. A one-signed kick would translate the whole
        # molecule rigidly and leave the mirror symmetry exactly where it was.
        d = kick_ang * (2.0 * rng.random() - 1.0)
        out.append((sym, x + d * nx, y + d * ny, z + d * nz))
    prov["applied"] = True
    prov["seed_provenance"] = seeding.provenance(seed, kick_ang, atoms, out)
    prov["after"] = coplanarity(out, tolerance_ang=tolerance_ang)
    prov["reason"] = ("heavy atoms were coplanar within %.3f A (max deviation %.6f) -- a planar "
                      "guess optimises to a planar saddle and reports exactly one imaginary mode "
                      "that says nothing about the reaction (ADR-066)"
                      % (tolerance_ang, cop["max_out_of_plane_ang"]))
    return out, prov


# =============================================================================================
# B-2 -- `nosymm` is not optional for a G16 route that relies on C-9's perturbation
# =============================================================================================
#
# HANDOFF_CODER6 §B-2 / docs/05_STATE.md §0-k: Gaussian does not passively fail to break a
# degenerate starting guess -- it ACTIVELY RE-DETECTS the molecular point group and CONSTRAINS
# the optimisation to it. `perturb_out_of_plane`'s kick is measured (C-4) to survive a GFN2
# optimisation, but that says nothing about G16: perturbing an atom off a symmetry element
# accomplishes nothing if G16 re-detects the group within its own tolerance on the very first
# step and snaps back onto it. C-9's remedy is therefore INSUFFICIENT for Gaussian without
# `nosymm` carried explicitly in the route.
#
# 🔴 Do NOT hand-write the list of job_types this applies to here -- `config/qc_levels.json`'s
# `_nosymm_required_job_types` is the single source (it sits beside the actual route templates,
# so a template edit and the requirement it must satisfy cannot drift apart silently).

#: 🔴🔴 [ADR-090 ruling item 3 / ADR-090's "5th instance"] `require_nosymm_if_needed` is a
#: CATEGORY (B) GUARD, STATED AS DATA SO THE GAP CANNOT SHIP SILENT: it is correct, it is
#: tested (`tests/test_guards.py::TestNosymmRequirement`,
#: `tests/test_guard_reach.py::TestDeferredAndKnownDefectGuardsStayVisible`), and it has
#: **zero external callers** -- exactly the shape that produced `bound.py::partition()`'s
#: pooled rate, `p1b.py::cost_ratios()`'s unread `converged`, and `payload/P1.sh`'s
#: unconditional QST2 fallback, all in the SAME session this guard was written in.
#: 🔒 Written by the author of this guard, about this guard, on purpose (see B-2's own text
#: above: "the guard function exists and is tested so wiring it in later is a one-line call,
#: not a design question" -- that sentence is, almost verbatim, ADR-090's root-cause
#: description of the other four instances).
NOSYMM_BLOCKING_ENTRY = {
    "guard": "require_nosymm_if_needed",
    "category": "B -- correct, tested, deliberately not yet callable from production",
    "blocked_on": ("B0 collector wiring (ADR-090 item 9, NOT STARTED) -- the code path that "
                  "builds a real G16 .gjf for a TS-search/IRC job_type and could therefore "
                  "confirm `nosymm`'s presence against `nosymm_required_job_types()` does "
                  "not exist yet. `payload/qc_adapter.sh`'s `job_types[job_type]` templates "
                  "already carry `nosymm` (the production fix -- see "
                  "`_nosymm_required_job_types` in config/qc_levels.json), so the untested "
                  "path is: 'was the templated keyword actually preserved in whatever a "
                  "future B0 collector step reads back', not 'was it requested'."),
    "when_you_wire_it": ("call `guards.require_nosymm_if_needed(job_type, route_record)` from "
                        "whichever B0 collector step first parses a completed TS-search/IRC "
                        "G16 log with `criteria.g16.parse_route_echo`, BEFORE trusting that "
                        "log's chemistry -- the same place C-8's precondition "
                        "(`require_ts_precondition`, ADR-090 item 5) and C-12's fallback "
                        "(`fallback_decision`, ADR-090 item 6) get wired, via the SAME "
                        "existing `python3 - <<'PY'` bridge already used four times in "
                        "`payload/qc_adapter.sh` (ADR-090 ruling item 4 -- no new mechanism)."),
    "do_not": ("invent a caller just to clear this entry. A caller that exists only to "
              "satisfy a reach check and does not actually gate anything real is the "
              "'false positive that teaches people to ignore the check' HANDOFF §0.2b-6 "
              "warns about."),
}


class NosymmRequirementUnmet(RuntimeError):
    """RAISED, not returned as a flag -- same shape as `solvent.SolventDescriptorsMissing` and
    `criteria.g16.RouteTruncatedError`. A returned flag is a thing a caller may decline to read,
    and that is how `nosymm`'s status was nearly read straight off a truncated stored route."""


def nosymm_required_job_types(cfg=None):
    """The G16 job_types that MUST carry `nosymm` (B-2). Reads the single source in
    `config/qc_levels.json` rather than duplicating the list as a literal here."""
    cfg = cfg if cfg is not None else config.load("qc_levels.json")
    return list((cfg.get("gaussian16") or {}).get("_nosymm_required_job_types") or [])


def require_nosymm_if_needed(job_type, route_record, cfg=None):
    """C-9 / B-2: for a `job_type` that relies on the perturbation remedy, RAISE unless the
    route CONFIRMS `nosymm` is present. Returns `True` if confirmed present; returns `None`
    (does nothing) for a `job_type` this requirement does not apply to.

    `route_record` is whatever `criteria.g16.parse_route_echo()` (a freshly parsed log) or
    `criteria.g16.route_record_from_stored_string()` (an already-stored bare string, e.g. an
    RT-1-era report) returned -- NOT a bare route string. 🔴 This deliberately reuses B-1's
    completeness machinery: a route whose completeness is unknown must raise here exactly as it
    would for any other keyword-absence question (`criteria.g16.require_keyword_known_absent`),
    not be silently read as "nosymm is absent".
    """
    if job_type not in nosymm_required_job_types(cfg):
        return None
    from .criteria import g16 as g16_mod

    verdict = g16_mod.keyword_in_route(route_record, "nosymm")
    if verdict is True:
        return True
    if verdict is None:
        raise NosymmRequirementUnmet(
            "C-9/B-2: job_type=%r relies on the C-9 out-of-plane perturbation and requires "
            "`nosymm`, but its presence cannot be determined from this route (%s). Do not read "
            "this as ABSENT -- mark it [UNKNOWN -- the stored route is truncated] and obtain the "
            "untruncated route before asserting anything." % (
                job_type,
                (route_record or {}).get("route_echo_completeness_evidence")))
    raise NosymmRequirementUnmet(
        "C-9/B-2: job_type=%r relies on the C-9 out-of-plane perturbation and `nosymm` is "
        "CONFIRMED ABSENT from its route. Gaussian will re-detect the molecular point group and "
        "re-impose it, silently undoing the perturbation C-9 applied." % job_type)


# =============================================================================================
# C-8 -- the TS search precondition
# =============================================================================================

def endpoint_report(name, ep):
    """One endpoint against C-8. Returns (ok, blocking[], detail)."""
    ep = ep or {}
    detail = {
        "name": name,
        "optimised": ep.get("optimised"),
        "converged": ep.get("converged"),
        "n_imag": ep.get("n_imag"),
        "level": ep.get("level"),
        "symmetry": ep.get("symmetry"),
        "source": ep.get("source"),
    }
    blocking = []
    if ep.get("converged") is not True:
        blocking.append("%s: converged is %r, not True -- the endpoint is not a stationary point"
                        % (name, ep.get("converged")))
    if ep.get("optimised") is not True:
        blocking.append("%s: optimised is %r, not True. RT-1's endpoints declared "
                        "'GUESS GEOMETRY (idealized, not optimized)' in their own second line "
                        "and 302 core-h were spent anyway (ADR-066)."
                        % (name, ep.get("optimised")))
    n_imag = ep.get("n_imag")
    if n_imag is None:
        blocking.append("%s: n_imag is unknown -- no frequency calculation is on record. "
                        "Unknown is not permission." % name)
    elif n_imag != 0:
        blocking.append("%s: n_imag = %r. An endpoint with an imaginary mode is a saddle, not a "
                        "minimum, and QST2's premise is that both ends are minima."
                        % (name, n_imag))
    return (not blocking), blocking, detail


def ts_precondition(reactant, product, required_level=None, declared_planar=False,
                    geometry=None):
    """C-8 (+C-9). Returns a decision dict. `may_start` is True only if NOTHING blocks.

    🔴 This is a PRECONDITION, not a warning. A caller that reads `blocking_reasons` and submits
       anyway has reproduced the incident: RT-1's P1 was handed two idealised, unoptimised,
       Cs-planar structures, burned 302 core-h, and produced a verdict that was an artefact.
    🔴 `may_start` is never True on missing information. Both endpoints must be at the SAME
       level, because "converged at some level" is not a property of a potential energy surface.
    """
    r_ok, r_block, r_detail = endpoint_report("reactant", reactant)
    p_ok, p_block, p_detail = endpoint_report("product", product)
    blocking = list(r_block) + list(p_block)

    lv_r, lv_p = (reactant or {}).get("level"), (product or {}).get("level")
    if lv_r is None or lv_p is None:
        blocking.append("endpoint level is unknown for at least one endpoint (reactant=%r, "
                        "product=%r) -- 'converged' is meaningless without the surface it was "
                        "converged on" % (lv_r, lv_p))
    elif lv_r != lv_p:
        blocking.append("endpoints are at DIFFERENT levels (reactant=%r, product=%r). C-8 "
                        "requires both to be minima at the SAME level." % (lv_r, lv_p))
    elif required_level is not None and lv_r != required_level:
        blocking.append("endpoints are at %r but this search runs at %r. P1 ran its QST2, "
                        "frequency and both IRCs at the HIGH level while production geometry and "
                        "Hessians are at the cheap one -- it never exercised the production "
                        "protocol (C-11, §39.13(a))." % (lv_r, required_level))

    cop = None
    sym = None
    if geometry is not None:
        cop = coplanarity(geometry)
        sym = symmetric_placement_flags(geometry)
        if cop.get("is_coplanar") and not declared_planar:
            blocking.append(
                "the guess geometry's heavy atoms are coplanar to within %.3f A (max deviation "
                "%.6f) and the species is not declared planar. C-9: detect the degeneracy and "
                "perturb out of plane before starting -- a planar guess converges to a planar "
                "saddle whose single imaginary mode is the symmetry-breaking one, which is "
                "exactly the shape our acceptance gate asks for and exactly what it must not "
                "accept." % (cop["tolerance_ang"], cop["max_out_of_plane_ang"]))

    out = {
        "may_start": not blocking,
        "blocking_reasons": blocking,
        "reactant": r_detail,
        "product": p_detail,
        "required_level": required_level,
        "declared_planar": bool(declared_planar),
        # 🔴 NAMED FOR WHAT IT IS. A field called `symmetry` would be read as "symmetry checked";
        #    this test covers ONE element (the plane implied by a fully planar heavy-atom set).
        #    The name travels into every downstream table; a docstring does not.
        "coplanarity_check_only": cop,
        "symmetry_coverage": dict(SYMMETRY_COVERAGE),
        "symmetric_placement_fingerprint": sym,
        "constraint": "C-8 + C-9 (02_METHOD_SPEC §39.12, after ADR-066)",
        "warnings": [],
    }
    if blocking:
        out["warnings"].append(
            "🔴 ts_precondition_refused: the TS search WILL NOT START. %s"
            % " | ".join(blocking))
    return out


class TSPreconditionError(RuntimeError):
    """Raised by `require_ts_precondition`. A refusal, not a diagnostic."""

    def __init__(self, decision):
        self.decision = decision
        RuntimeError.__init__(
            self, "C-8: TS search refused to start -- %s"
                  % " | ".join(decision.get("blocking_reasons") or ["unknown"]))


def require_ts_precondition(*args, **kwargs):
    """`ts_precondition` that RAISES rather than returning a flag someone can ignore.

    🔴 A warning is something a caller may choose not to read. Every one of this project's
       expensive failures was a value that was written down and not read (§39.0's closing rule).
       Call this from any code path that actually submits a TS search.
    """
    decision = ts_precondition(*args, **kwargs)
    if not decision["may_start"]:
        raise TSPreconditionError(decision)
    return decision


def single_ended_ts_precondition(reactant, required_level=None, declared_planar=False,
                                 geometry=None):
    """C-8 for a SINGLE-ENDED TS search (relaxed scan → opt=ts): reactant endpoint ONLY.

    🔴 WHY A SEPARATE PREDICATE EXISTS instead of feeding `ts_precondition` a fake product:
       §39.32 Candidate B / §39.39(e) — for the single-ended method the product endpoint is an
       *output* (of the IRC), never an input, so demanding a certified product here would make
       the gate structurally unsatisfiable (a dead gate is indistinguishable from no gate), and
       fabricating a product dict to pass the two-endpoint gate would be worse (Rule 18: the
       code never substitutes an answer it does not have).
    🔴 AND WHAT IT DOES NOT RELAX: "single-ended does NOT escape C-8. The reactant must still be
       a true minimum on the same surface. It halves the exposure, it does not remove it"
       (§39.32 Candidate B, verbatim). Same clauses as `endpoint_report`, same level rule
       (stationarity is a property of a SURFACE), same C-9 coplanarity refusal on the geometry.
    """
    r_ok, blocking, r_detail = endpoint_report("reactant", reactant)
    blocking = list(blocking)

    lv_r = (reactant or {}).get("level")
    if lv_r is None:
        blocking.append("reactant level is unknown -- 'converged' is meaningless without the "
                        "surface it was converged on")
    elif required_level is not None and lv_r != required_level:
        blocking.append("reactant is certified at %r but this search runs at %r. n_imag == 0 "
                        "is a property of a surface, not of a molecule (C-8.1)."
                        % (lv_r, required_level))

    cop = None
    sym = None
    if geometry is not None:
        cop = coplanarity(geometry)
        sym = symmetric_placement_flags(geometry)
        if cop.get("is_coplanar") and not declared_planar:
            blocking.append(
                "the guess geometry's heavy atoms are coplanar to within %.3f A (max deviation "
                "%.6f) and the species is not declared planar (C-9). A planar start scans a "
                "symmetry-restricted rigid path -- exactly P1's artefact."
                % (cop["tolerance_ang"], cop["max_out_of_plane_ang"]))

    out = {
        "may_start": not blocking,
        "blocking_reasons": blocking,
        "reactant": r_detail,
        "product": None,
        "product_endpoint_rule": ("single-ended: the product endpoint is an OUTPUT of the "
                                  "IRC, not an input (§39.32 Candidate B / §39.39(e)) -- "
                                  "its absence here is by design, not an unchecked gap"),
        "required_level": required_level,
        "declared_planar": bool(declared_planar),
        "coplanarity_check_only": cop,
        "symmetry_coverage": dict(SYMMETRY_COVERAGE),
        "symmetric_placement_fingerprint": sym,
        "constraint": "C-8 single-ended (§39.32 Candidate B / §39.39(e), after ADR-066)",
        "warnings": [],
    }
    if blocking:
        out["warnings"].append(
            "🔴 ts_precondition_refused: the single-ended TS search WILL NOT START. %s"
            % " | ".join(blocking))
    return out


def require_single_ended_ts_precondition(*args, **kwargs):
    """`single_ended_ts_precondition` that RAISES (`TSPreconditionError`) — same shape and same
    reason as `require_ts_precondition`: a returned flag is a thing a caller may decline to
    read. Call this from any code path that actually submits a single-ended TS search
    (payload/U56.sh's relaxed_scan branch is the intended caller)."""
    decision = single_ended_ts_precondition(*args, **kwargs)
    if not decision["may_start"]:
        raise TSPreconditionError(decision)
    return decision


# =============================================================================================
# C-12 -- a fallback is conditioned on the acceptance test, never on the exit status
# =============================================================================================

def fallback_decision(exit_ok, acceptance):
    """Decide whether the fallback fires. `acceptance` maps a check name to True/False/None.

    🔴 THE INCIDENT: `qc_levels.json:_ts_method`'s QST2 -> single-ended fallback fired only if
       QST2 FAILED TO CONVERGE. QST2 converged -- to a saddle of the wrong coordinate -- so the
       fallback never fired and 302 core-h bought a wrong answer (§39.13(a), C-12).
    🔴 So `exit_ok` is recorded and DOES NOT DECIDE. A check that is None (not evaluated) counts
       as NOT accepted: the fallback falls toward firing, which is the cheap direction.
    """
    acceptance = acceptance or {}
    failed = sorted(k for k, v in acceptance.items() if v is False)
    unevaluated = sorted(k for k, v in acceptance.items() if v is None)
    accepted = bool(acceptance) and not failed and not unevaluated
    out = {
        "exit_ok": exit_ok,
        "exit_status_was_not_used_to_decide": True,
        "acceptance": dict(acceptance),
        "failed_checks": failed,
        "unevaluated_checks": unevaluated,
        "accepted": accepted,
        "fallback_fires": not accepted,
        "constraint": "C-12 (02_METHOD_SPEC §39.13(e))",
        "warnings": [],
    }
    if not acceptance:
        out["warnings"].append(
            "🔴 fallback_has_no_acceptance_test: no acceptance checks were supplied, so this "
            "fallback is conditioned on nothing. That is the C-12 defect in its original form -- "
            "fire the fallback rather than assume success.")
    if exit_ok and not accepted:
        out["warnings"].append(
            "🔴 converged_but_not_accepted: the primary method exited cleanly and FAILED the "
            "acceptance test (%s). This is the exact case a status-keyed fallback cannot catch. "
            "Firing the fallback." % ", ".join(failed + unevaluated))
    return out


# =============================================================================================
# C-13 -- a tripwire abort is a measurement, not waste
# =============================================================================================

def tripwire_record(task_id, core_hours, wall_h, cap_h, reason="wall-time cap"):
    """C-13. An aborted run's core-h is DATA about convergence risk. Never discard it.

    🔴 B0-D's whole purpose is the cost/convergence DISTRIBUTION of Li+Ln. An abort is a sample
       from its tail. Dropping aborts measures only the species that were easy, which is the
       distribution we already believed (§39.13(b), R35.2b).
    """
    return {
        "task_id": task_id,
        "status": TRIPWIRE_ABORTED,
        "core_hours": core_hours,
        "counts_toward_spend": True,
        "wall_h": wall_h,
        "cap_h": cap_h,
        "reason": reason,
        "converged": False,
        "constraint": "C-13 (02_METHOD_SPEC §39.13(e))",
        "note": ("an abort is a MEASUREMENT OF DIFFICULTY, which is half of what this probe is "
                 "for. Its core-h is reported and counted, and it is never dropped from the "
                 "sample."),
    }


def detect_tripwire_aborts(exec_records, cap_h, now_epoch):
    """Find jobs the wall-time cap killed, from `executions.jsonl`'s own appends.

    🔴 THE OTHER HALF OF ENFORCEMENT. Capping the REQUESTED wall (the planner's
    `max_wall_h = 6.0`) is what stops a runaway; this is what makes the runaway VISIBLE and
    ACCOUNTED. A job PBS kills at the wall writes a `run` append and never writes `finish`, so
    without this it simply disappears -- and a job that vanishes from the accounting is how a
    ceiling gets exceeded on paper while every number still looks fine.

    `exec_records` are the parsed lines of `executions.jsonl`. Each `run` append carries `epoch`,
    `host` and `cores` (R31.2a) -- which is precisely what makes the consumed core-h recoverable.

    🔴 The core-h reported is a LOWER BOUND, and says so: it is measured from the last observed
       `run` epoch to `now_epoch`, so a job killed before the collector ran is credited only with
       the time we can prove.
    """
    runs, finished = {}, set()
    for rec in exec_records or []:
        if not isinstance(rec, dict):
            continue
        link = rec.get("link")
        if rec.get("action") == "run":
            runs[link] = rec
        elif rec.get("action") in ("finish", "skip_done"):
            finished.add(link)

    out = []
    for link, rec in sorted(runs.items()):
        if link in finished:
            continue
        started = rec.get("epoch")
        if not isinstance(started, (int, float)):
            continue
        elapsed_h = (float(now_epoch) - float(started)) * units.S_TO_H
        if elapsed_h < float(cap_h):
            continue
        cores = rec.get("cores")
        core_h = None if not isinstance(cores, (int, float)) else float(cores) * elapsed_h
        entry = tripwire_record(link, core_h, round(elapsed_h, 4), float(cap_h),
                                reason="wall-time cap: started and never finished")
        entry["host"] = rec.get("host")
        entry["core_hours_is_lower_bound"] = True
        entry["detected_from"] = "executions.jsonl run-append with no matching finish"
        if core_h is None:
            entry["warnings"] = [
                "🔴 %s hit the cap but its `run` append carries no `cores`, so its core-h "
                "cannot be reconstructed. This is what the R31.2a fields exist for -- a payload "
                "built before that fix cannot be accounted for here." % link]
        out.append(entry)
    return out


def spend_core_hours(records):
    """Total core-h INCLUDING `[TRIPWIRE-ABORTED]` runs.

    🔴 Separate from any convergence statistic on purpose: an abort spends real allocation and
       must appear in the spend, while `converged == False` keeps it out of every derived
       quantity via C-1. Both are true at once and a single field cannot say both.
    """
    total = 0.0
    for r in records or []:
        ch = (r or {}).get("core_hours")
        if isinstance(ch, (int, float)):
            total += float(ch)
    return total


# =============================================================================================
# C-10 -- a cost probe may not carry a chemical pass/fail
# =============================================================================================

#: Keys whose presence in a COST probe's result means it is rendering a chemical verdict.
#: 🔴 The list is the four instances §39.4(g) R-4 names, not a guess: u_cheap, r_composite,
#:    r_high and P1 were all cost measurements that acquired chemical acceptance criteria.
CHEMICAL_VERDICT_KEYS = (
    "imag_freq_count", "irc_endpoints_distinct", "barrier_ev", "reaction_is_correct",
    "chemistry_status", "freq_passed", "endpoint_comparison",
)

#: Statuses a cost probe is allowed to report. Note what is NOT here: `pass` and `fail`.
COST_PROBE_STATUSES = ("measured", "incomplete", "not_submitted", TRIPWIRE_ABORTED)


def cost_probe_violations(result):
    """C-10. Names every way `result` is smuggling a chemical verdict into a cost probe.

    🔴 "A COST probe must not carry a CHEMICAL pass/fail. It cannot earn one, and when it renders
       one the team spends a round on it." (§39.4(g) R-4). RT-1's P1 rendered one and the round
       was spent.
    Returns a list of strings; empty means clean.
    """
    result = result or {}
    bad = []
    st = result.get("status")
    if st in ("pass", "fail"):
        bad.append("status = %r. A cost probe reports %s -- it measures core-h, not chemistry."
                   % (st, "/".join(COST_PROBE_STATUSES)))
    for key in CHEMICAL_VERDICT_KEYS:
        if key in result:
            bad.append("carries %r, which is a chemical acceptance criterion. Measure it, "
                       "report it under a clearly non-verdict name, or drop it -- but it may not "
                       "decide this probe's status." % key)
    for key in ("criteria", "fail_reasons"):
        if result.get(key):
            bad.append("carries a non-empty %r. That is the field through which P1's cost "
                       "measurement acquired a chemical pass/fail." % key)
    return bad
