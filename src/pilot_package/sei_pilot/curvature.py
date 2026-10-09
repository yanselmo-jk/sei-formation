"""The three curvature observables that decide U-55 — and the correlation that tests them.

U-55 asks: **is the Li+-multiligand class INTRINSICALLY hard to optimise, or was the 283 core-h an
artefact of a bad start?** That is a question about **the shape of the PES near the minimum**, i.e.
CURVATURE. A dissociation rate is KINETIC, and a kinetic proxy for a curvature property was the
wrong instrument — proposer5 withdrew its own §39.26(a) sentence after the temperature finding
exposed it.

```
PER SPECIES, from the frequency log B0-D already produces:
    nu_min                    lowest REAL frequency                       cm^-1
    n_soft                    N(nu < 50 cm^-1), the soft-mode density     count
    hessian_condition_number  lambda_max / lambda_min over REAL modes     dimensionless
```

🔴 THIS IS NOT A BETTER PROXY -- IT IS CLOSE TO THE CAUSE. A quasi-Newton optimiser's convergence
   rate is governed by the CONDITION NUMBER of the Hessian; many near-zero eigenvalues means an
   ill-conditioned Hessian means slow convergence. "Floppy" and "expensive to optimise" are
   connected through that quantity MECHANICALLY, not statistically.

```
THE TEST THAT DECIDES U-55: correlate the three against MEASURED opt cycles and core-h, over all
23 species.
    correlation holds  ->  U-55 decided, AND we gain a cheap predictor of which production species
                           will be expensive -- usable on species we have never run
    no correlation     ->  the leading hypothesis is EXCLUDED, which is also a result
```
🟢 Cost ZERO -- the eigenvalues are in every frequency log.
🟢 TEMPERATURE-INDEPENDENT, so the T_eff problem does not touch it.
🟢 Available for ALL 23, where a dissociation rate would only ever have covered the species that
   happened to come apart.

🔴 UNITS. Frequencies arrive in **cm^-1**. In mass-weighted coordinates the Hessian eigenvalue
   satisfies `lambda ∝ nu^2`, so the condition number is `(nu_max / nu_min)^2` and NOT
   `nu_max / nu_min`. Getting that wrong understates the spread by a square root and would not
   look wrong -- it would look like the answer.
"""

import math

from . import units

#: 🔴 `[ASSERTED]` -- NOT CALIBRATED, AND IT MAY NOT BE CITED AS IF IT WERE.
#: proposer5 wrote "N(nu < 50 cm^-1)" and then noted it had broken its own §39.4(c) rule two
#: sections after writing it ("do NOT hard-code a threshold this round -- that is how -100 got
#: there"). Same object: a threshold under a decision-making observable, asserted not measured.
#: ⟹ `n_soft` is reported as a CURVE over `SOFT_MODE_CURVE_CM1`; this single value is kept only
#:   as the historical label. **Until the curve exists, 50 may not be described as calibrated.**
SOFT_MODE_CM1 = 50.0
SOFT_MODE_CM1_STATUS = "[ASSERTED] not calibrated; use the n_soft curve and let the data pick x"

#: The curve. 🟢 The threshold becomes VISIBLE and the correlation analysis picks whichever x
#: actually predicts -- **that is the calibration**, measured rather than asserted.
#: Cost: counting the same list at five cutoffs.
SOFT_MODE_CURVE_CM1 = (10.0, 25.0, 50.0, 100.0, 200.0)

#: 🔒 THE PRE-REGISTERED PRIMARY. Fixed 2026-08-19, BEFORE any B0 data existed.
#:
#:   PRIMARY (decision-making)   kappa_k2  vs  opt_cycles
#:   SECONDARY (pointers only)   every other correlation in the panel
#:
#: RATIONALE, and every part of it was available before the data -- check it:
#:   * `opt_cycles`, NOT `core_hours`. proposer5's mechanism is that a quasi-Newton optimiser's
#:     convergence RATE is governed by the Hessian condition number. Cycles is the direct
#:     observable of that rate; core-hours confounds it with system size and level of theory --
#:     a real effect pointing the same way, which is U-59's trap.
#:   * k = 2, NOT k = 1 or k = 3. k=1 is dominated by the single lowest mode, which is A PRIORI
#:     the mode most contaminated by incomplete convergence -- that is the mechanism, not an
#:     observation about our numbers. k=3 discards more than the argument requires. k=2 is the
#:     minimal trim that removes the one most artefact-prone mode.
#:
#: 🔴🔴 THE 6,000x FIGURE WAS **NOT** USED TO CHOOSE k, AND MUST NOT BE CITED AS IF IT WERE.
#:   coder6 measured kappa_1 = 20,475,625 against kappa_2 = 3,365.5 -- but that came from a
#:   SYNTHETIC fixture with a DELIBERATELY INSERTED 0.4 cm^-1 mode. It demonstrates the
#:   FRAGILITY of the untrimmed statistic; it is **not evidence about our species**. Choosing k
#:   because it looked good on a constructed case is ADR-077's "a fit is not a confirmation"
#:   exactly. The rationale above stands without it.
PRE_REGISTRATION = {
    "date": "2026-08-19",
    "registered_before_any_data": True,
    "primary_predictor": "kappa_k2",
    "primary_response": "opt_cycles",
    "secondary_role": "exploratory pointers, never decision-making",
    "rationale_response": ("opt_cycles is the DIRECT observable of convergence rate, which is the "
                           "mechanism. core_hours confounds it with system size and level of "
                           "theory -- a real effect pointing the same way (U-59's trap)."),
    "rationale_trim": ("k=1 is dominated by the single lowest mode, a priori the most contaminated "
                       "by incomplete convergence. k=3 discards more than the argument requires. "
                       "k=2 is the minimal trim removing the one most artefact-prone mode."),
    "🔴 not_chosen_from_data": (
        "the 6,000x kappa_1/kappa_2 gap coder6 measured came from a SYNTHETIC fixture with a "
        "deliberately inserted 0.4 cm^-1 mode. It demonstrates the fragility of the untrimmed "
        "statistic and is NOT evidence about our species. It was NOT used to choose k, and it "
        "may not be cited as if it were -- that would be ADR-077's 'a fit is not a confirmation'."),
    "interpretation_rule": ("present only at k=1 => driven by one artefact mode, SPURIOUS. "
                            "Stable across k => real, and U-55 is genuinely decided."),
    "🔒 verdict_is_a_judgement_for": "proposer",
}

#: Trim orders for the condition number. 🔒 THE CHOICE LIVES IN THE DEFINITION, NOT IN A CONSTANT.
#: kappa_k = (nu_max / nu_(k))^2, where nu_(k) is the k-th lowest real frequency.
#: k = 1 is the untrimmed ratio.
TRIM_ORDERS = (1, 2, 3)

#: 🔴 NOT A FLOOR AND NOT AN EXCLUSION. A count of sub-5 cm^-1 modes, reported as a CONVERGENCE
#: DIAGNOSTIC. With translations and rotations projected out, a genuinely sub-1 cm^-1 internal
#: mode is essentially never physical for a bound complex (a nearly free methyl rotor is
#: ~10-30 cm^-1; a floppy Li-O torsion ~5-20), so such modes indicate AN OPTIMISATION THAT DID
#: NOT CONVERGE -- 🟢 which is U-55's own question. The thing a floor would have discarded is
#: itself a measurement of the property under study. Same shape as the MTD dissociation count:
#: RELABEL, DO NOT DISCARD.
CONVERGENCE_ARTEFACT_CM1 = 5.0


def observables(frequencies_cm1, soft_curve_cm1=SOFT_MODE_CURVE_CM1,
                trim_orders=TRIM_ORDERS):
    """The curvature observables from one species' frequency list (cm^-1).

    🔴 THERE IS NO NOISE FLOOR. It was removed: the floor only decided WHICH SINGLE NUMBER
       DOMINATED an already-fragile statistic, and one mode moving the condition number 3,600x
       means the condition number was never a robust predictor. The fix is the STATISTIC, not the
       threshold.

    ```
    nu_min_cm1                 lowest real frequency, untouched
    n_soft_curve               N(nu < x) for x in soft_curve_cm1 -- the threshold is VISIBLE and
                               the correlation picks whichever x predicts. THAT is the calibration.
    trimmed_condition_numbers  kappa_k = (nu_max / nu_(k))^2 for k in trim_orders.
                               k = 1 is untrimmed. Stability across k is the predictor's own
                               falsifier (see curvature.u55_panel).
    n_convergence_artefacts    N(nu < 5 cm^-1). 🟢 A CONVERGENCE DIAGNOSTIC, NOT PHYSICS, and not
                               discarded: a species with many of these is telling us its
                               optimisation did not converge, which is U-55's question.
    ```
    Imaginary frequencies arrive as NEGATIVE (the project-wide convention). Counted, excluded from
    the real-mode statistics. Every field is `None` when it could not be computed -- an empty list
    does not give `nu_min = 0`, which would read as an infinitely floppy species.
    """
    freqs = [f for f in (frequencies_cm1 or []) if isinstance(f, (int, float))]
    imaginary = [f for f in freqs if f < 0]
    real = sorted(f for f in freqs if f >= 0)

    out = {
        "n_frequencies": len(freqs),
        "n_imaginary": len(imaginary),
        "imaginary_cm1": [round(f, 2) for f in imaginary],
        "n_real": len(real),
        "nu_min_cm1": real[0] if real else None,
        "nu_max_cm1": real[-1] if real else None,
        "n_soft_curve": None,
        "soft_curve_thresholds_cm1": list(soft_curve_cm1),
        "n_soft": None,
        "_n_soft_status": SOFT_MODE_CM1_STATUS,
        "trimmed_condition_numbers": None,
        "trim_orders": list(trim_orders),
        "n_convergence_artefacts": None,
        "convergence_artefact_threshold_cm1": CONVERGENCE_ARTEFACT_CM1,
        "warnings": [],
        "_condition_number_definition": (
            "kappa_k = (nu_max / nu_(k))^2 over REAL modes, nu_(k) the k-th lowest. In "
            "mass-weighted coordinates lambda ∝ nu^2, so this is a SQUARE of a frequency ratio -- "
            "using the ratio itself would understate the spread by a square root."),
        "_why_trimmed": (
            "🔴 the untrimmed k=1 value is dominated by a single mode: one mode at 0.5 instead of "
            "30 cm^-1 changes it ~3,600x. Reporting k = 1,2,3 makes the fragility VISIBLE and "
            "gives the predictor a way to fail (see u55_panel's stability check)."),
        "_no_floor": (
            "🔴 no noise floor is applied. A floor only decides which single number dominates; it "
            "cannot make a fragile statistic robust. Sub-5 cm^-1 modes are COUNTED as a "
            "convergence diagnostic instead of being discarded."),
    }
    if not freqs:
        out["warnings"].append(
            "🔴 no frequencies parsed -- the curvature observables are UNAVAILABLE for this "
            "species and it must be held out of the correlation, not entered as zero.")
        return out

    if real:
        out["n_soft_curve"] = dict((x, sum(1 for f in real if f < x)) for x in soft_curve_cm1)
        out["n_soft"] = out["n_soft_curve"].get(SOFT_MODE_CM1)
        out["n_convergence_artefacts"] = sum(
            1 for f in real if f < CONVERGENCE_ARTEFACT_CM1)
        kappas = {}
        for k in trim_orders:
            if len(real) >= k and real[k - 1] > 0:
                kappas[k] = (real[-1] / real[k - 1]) ** 2
            else:
                kappas[k] = None
        out["trimmed_condition_numbers"] = kappas
        if out["n_convergence_artefacts"]:
            out["warnings"].append(
                "🟡 convergence_artefact_modes: %d real mode(s) below %.1f cm^-1. With "
                "translations and rotations projected out these are essentially never physical "
                "for a bound complex ⟹ 🔴 THIS SPECIES' OPTIMISATION LIKELY DID NOT CONVERGE. "
                "Reported as a diagnostic, NOT discarded -- it is a measurement of exactly the "
                "property U-55 asks about."
                % (out["n_convergence_artefacts"], CONVERGENCE_ARTEFACT_CM1))
    if imaginary:
        out["warnings"].append(
            "🟡 %d imaginary mode(s) present (%s cm^-1). Excluded from the real-mode statistics. "
            "🔴 For a species that is supposed to be a MINIMUM this is itself a finding -- see "
            "`imaginary_mode_verdict`."
            % (len(imaginary), [round(f, 1) for f in imaginary]))
    return out


def imaginary_mode_verdict(observables_record, expected_minimum=True, species_id=None):
    """Is an imaginary mode a defect here, or the point of the calculation?

    🔴 SAME SPECIES LIST, OPPOSITE EXPECTATION. B0-D's species are supposed to be MINIMA (zero
    imaginary modes); B0-F's transition states are supposed to have EXACTLY ONE. A single count
    shared between them cannot say which case it is looking at, and the failure it would hide is
    the one we now know to look for:

    🔒 a structure stuck on a symmetry element is generally a SADDLE, not a minimum -- and a GFN2
       optimisation does NOT leave the element (measured: every distance moved, the exact
       degeneracy did not). An imaginary frequency where none should be is the DIRECT signature.
    """
    n = (observables_record or {}).get("n_imaginary")
    out = {
        "species_id": species_id,
        "expected_minimum": bool(expected_minimum),
        "n_imaginary": n,
        "expected_n_imaginary": 0 if expected_minimum else 1,
        "verdict": None,
        "warnings": [],
        "_why_this_is_separate": (
            "a minimum and a transition state have OPPOSITE expectations about the same count. "
            "One shared field cannot report both, and the case it would hide is a species stuck "
            "on a symmetry element -- a saddle wearing a minimum's label."),
    }
    if n is None:
        out["verdict"] = None
        out["warnings"].append(
            "🔴 imaginary_mode_not_checked for %s: no frequency count available. Not 'zero'."
            % species_id)
        return out
    out["verdict"] = "as_expected" if n == out["expected_n_imaginary"] else "unexpected"
    if out["verdict"] == "unexpected" and expected_minimum:
        out["warnings"].append(
            "🔴 imaginary_mode_on_a_supposed_minimum: %s has %d imaginary mode(s) where 0 were "
            "expected. 🔴 A structure stuck on a SYMMETRY ELEMENT is generally a saddle, and a "
            "GFN2 optimisation does not leave the element. Check "
            "`symmetric_placement_fingerprint` for this species before reading the frequency as "
            "chemistry." % (species_id, n))
    elif out["verdict"] == "unexpected":
        out["warnings"].append(
            "🔴 unexpected_imaginary_count on a TS species %s: %d, expected 1."
            % (species_id, n))
    return out


def nu_to_eigenvalue_ev2(nu_cm1):
    """cm^-1 -> (eV)^2-like eigenvalue proxy, through `units` only. Reporting convenience."""
    return units.cm1_to_ev(nu_cm1) ** 2


# =============================================================================================
# 🔴 M2' — MODE CHARACTER (Omega). §39.4(c) / §39.26(d) / §39.56
# =============================================================================================
#
# 왜 이것이 필요한가, 그리고 왜 |nu_imag| 로는 안 되는가:
#   P1 의 "TS" 는 exactly-one-imaginary-frequency 를 **통과했다**(`freq.passed: true`).
#   그런데 그 모드는 -48.4 cm^-1, reduced mass 7.15 amu(Li 원자량 6.94 와 거의 같다),
#   제곱진폭의 63%가 Li 원자 하나에 있고, 의도한 C-O 결합과의 겹침 Omega = 0.022 였다.
#   d(O2-C3) = 3.18 A -- **이미 끊어져 있었다.** 즉 그 saddle 은 닫힌 고리와 열린 고리
#   사이가 아니라 **이미 열린 생성물 표면 위**에 있었고, 허수모드는 Li+ 가 배위자리
#   사이를 넘어가는 spectator 운동이었다.
#   🔒 무른 모드 + 높은 Omega = 진짜 물렁한 TS / 무른 모드 + Omega ~ 0 = 틀린 saddle.
#      **|nu_imag| 만으로는 이 둘을 가를 수 없다.** 크기가 아니라 **방향**의 문제다.
#
# 🔴 판정하지 않는다 (C-3, U-57). Omega_min 은 보정 대상이지 주장 대상이 아니다 --
#    "Do not hard-code a threshold this round. That is how -100 got there."(§39.4(c))
#    이 함수는 **수치만** 낸다.

def mode_overlap_omega(mode, geometry, pairs):
    """Omega = |proj_b(q)| / |q| -- 질량가중 허수모드가 지정된 결합 신축 좌표에 실린 비율.

    인자:
      mode      `criteria.g16.parse_normal_modes` 의 모드 1개
                (`displacements` = [(sym, dx, dy, dz), ...], G16 의 Cartesian 변위)
      geometry  **같은 orientation** 의 [(sym, x, y, z), ...] (Angstrom)
      pairs     [(i, j, label), ...] 0-based 원자 index 쌍 (§39.26(d) break/form mapping)

    반환: [{"label", "i", "j", "omega", "distance_ang", "elements"}...]  — 판정 없음.

    단위/규약:
      * 좌표·거리 Angstrom. Omega 는 무차원 [0, 1].
      * 질량은 `units.ATOMIC_MASS_AMU`(가장 흔한 동위원소, G16 기본과 같은 관례).
      * q = sqrt(m_a) * l_cart,  B = (+u/sqrt(m_i), -u/sqrt(m_j)),  u = 단위 결합벡터.
        전체 배율은 |q| 로 나누면서 사라지므로 G16 의 변위 정규화 관례에 의존하지 않는다.

    🔴 원자 index 는 mapping 에서 오고, 원소 기호가 기하와 어긋나면 raise 한다 — 두 잡의
       원자 순서가 다른데 index 로 짝지으면 조용히 다른 결합의 Omega 가 나온다.
    ⚠ G16 의 저정밀 블록은 변위를 **소수 2자리**로 찍는다. Omega 가 상쇄로 작아지는
       영역에서는 그 반올림이 상대오차로 크게 보일 수 있다 -- 값의 자릿수를 그대로
       믿지 말고, 판정이 문턱 근처면 `freq=hpmodes` 가 필요하다는 신호로 읽어라.
    """
    disp = (mode or {}).get("displacements") or []
    if not disp or len(disp) != len(geometry or []):
        raise ValueError(
            "mode has %d displacement rows but the geometry has %d atoms -- these are not "
            "the same structure and pairing them by index would silently project onto the "
            "wrong bond" % (len(disp), len(geometry or [])))
    masses = []
    for k, (sym, _x, _y, _z) in enumerate(geometry):
        if disp[k][0] != sym:
            raise ValueError(
                "atom %d is %r in the geometry and %r in the mode block -- refusing to "
                "pair them" % (k, sym, disp[k][0]))
        try:
            masses.append(units.ATOMIC_MASS_AMU[sym])
        except KeyError:
            raise ValueError("no atomic mass on record for element %r (units."
                             "ATOMIC_MASS_AMU) -- add it there, not here" % (sym,))

    q = []
    for k, (_sym, dx, dy, dz) in enumerate(disp):
        r = math.sqrt(masses[k])
        q += [r * dx, r * dy, r * dz]
    nq = math.sqrt(sum(v * v for v in q))

    out = []
    for i, j, label in pairs:
        xi, xj = geometry[i][1:], geometry[j][1:]
        d = [xi[k] - xj[k] for k in range(3)]
        dist = math.sqrt(sum(v * v for v in d))
        rec = {"label": label, "i": i, "j": j, "distance_ang": dist,
               "elements": (geometry[i][0], geometry[j][0]), "omega": None}
        if dist <= 0.0 or nq <= 0.0:
            rec["note"] = "degenerate bond vector or zero mode -- omega undefined"
            out.append(rec)
            continue
        u = [v / dist for v in d]
        b = [0.0] * (3 * len(geometry))
        for k in range(3):
            b[3 * i + k] = u[k] / math.sqrt(masses[i])
            b[3 * j + k] = -u[k] / math.sqrt(masses[j])
        nb = math.sqrt(sum(v * v for v in b))
        rec["omega"] = abs(sum(b[k] * q[k] for k in range(len(q))) / nb) / nq
        out.append(rec)
    return out


def spectator_test(mode, geometry, coordinate_atoms):
    """🔴 [§39.62] THE SPECTATOR TEST — threshold-free. BLOCK funding the IRC iff the mode's
    single most-displaced atom is OUTSIDE the declared coordinate set AND outstrips the WHOLE
    declared set put together.

        BLOCK  iff  argmax_a f(a) not in S   and   max_a f(a) > sum_{a in S} f(a)

    where f is the per-atom fraction of the mode's squared amplitude and S is the set of atoms
    named by the reaction's break/form/mechanism coordinates.

    🔒 NO THRESHOLD ANYWHERE. It compares two quantities MEASURED FROM THE SAME MODE, the same
    construction as G-SCAN v3's two directions and B+'s two start points. Ω keeps its own job
    (emitted, never adjudicated — §39.4(c), U-57 open); this test does not read Ω at all.

    🔴 WHY IT IS DELIBERATELY PERMISSIVE — the two errors do not cost the same:
        FALSE BLOCK (the mode IS the coordinate, we skip it) -> we lose a REACTION. Quiet.
        FALSE PASS  (spectator, we fund the IRC anyway)      -> ~325 core-h (11 atoms) /
                                                               ~3,120 (21 atoms), AND the same
                                                               `indeterminate` we would have
                                                               recorded anyway.
    A false pass costs MONEY; a false block costs a RESULT. ⟹ block only when the mode is
    DEMONSTRABLY a spectator, and let everything ambiguous through to the human / to a later
    calibrated U-57.

    Measured on P1's saddle (break/form atoms O2, C3), the case that motivated this:
        unweighted     sum(S) = 0.0207   max = Li 0.6314   30.6x  -> BLOCK
        mass-weighted  sum(S) = 0.0435   max = Li 0.6166   14.2x  -> BLOCK
    🟢 Same verdict under BOTH localisation definitions, so this test does not inherit the Ω
    definition defect (§39.56 corrected) — a test that survives its instrument's known bug.

    🔴 AND THE PRECONDITION, which is the part that can silently invert this test: an atom is a
    spectator ONLY RELATIVE TO A DECLARED COORDINATE SET. If the mechanism uses that atom, it
    belongs in the set. §39.41(e) measured that R-C's ring opening is TWO-DIMENSIONAL — Li⁺
    translocates onto the breaking oxygen as part of the mechanism — so R-C must declare
    `d(Li–O_break)` or this test would block R-C's GENUINE transition state, which is exactly
    the false block the asymmetry above says we cannot afford.
    ⟹ If this fires on a reaction believed to be real, THE FIRST HYPOTHESIS IS AN INCOMPLETE
      MAPPING, NOT A WRONG SADDLE. That sentence is in the reason string on purpose.

    `mass_weighted` is reported for both definitions rather than chosen, since the verdict is
    definition-independent and saying so is cheaper than asserting it.
    """
    disp = (mode or {}).get("displacements") or []
    S = set(int(a) for a in (coordinate_atoms or []))
    out = {"blocked": False, "coordinate_atoms": sorted(S), "reasons": [],
           "by_definition": {}}
    if not disp or len(disp) != len(geometry or []):
        out["reasons"].append(
            "mode and geometry do not describe the same structure (%d displacement rows vs "
            "%d atoms) -- no spectator verdict" % (len(disp), len(geometry or [])))
        return out
    if not S:
        out["reasons"].append(
            "no coordinate atoms declared -- every atom would count as a spectator, which is "
            "a statement about the mapping, not about the mode. NOT blocking.")
        return out

    verdicts = []
    for label, weighted in (("unweighted", False), ("mass_weighted", True)):
        w = []
        for k, (sym, dx, dy, dz) in enumerate(disp):
            m = units.ATOMIC_MASS_AMU.get(sym, 1.0) if weighted else 1.0
            w.append(m * (dx * dx + dy * dy + dz * dz))
        tot = sum(w)
        if not tot:
            continue
        frac = [v / tot for v in w]
        top = max(range(len(frac)), key=lambda k: frac[k])
        s_sum = sum(frac[k] for k in S if k < len(frac))
        rec = {"largest_atom_index": top, "largest_atom_element": disp[top][0],
               "largest_fraction": frac[top], "coordinate_fraction_sum": s_sum,
               "largest_is_outside_the_coordinate_set": top not in S,
               "ratio": (frac[top] / s_sum) if s_sum else None,
               "blocked": bool(top not in S and frac[top] > s_sum)}
        out["by_definition"][label] = rec
        verdicts.append(rec["blocked"])

    if not verdicts:
        out["reasons"].append("the mode has zero amplitude -- no spectator verdict")
        return out
    out["definition_independent"] = (len(set(verdicts)) == 1)
    out["blocked"] = all(verdicts)
    ref = out["by_definition"].get("mass_weighted") or out["by_definition"].get("unweighted")
    if out["blocked"]:
        out["reasons"].append(
            "SPECTATOR: atom %d (%s) carries %.4f of the mode while EVERY declared coordinate "
            "atom together carries %.4f (%.1fx). The imaginary mode is not the declared "
            "reaction coordinate's motion. 🔴 FIRST HYPOTHESIS IS AN INCOMPLETE MAPPING, NOT A "
            "WRONG SADDLE: if this reaction's mechanism uses that atom (as R-C's does -- Li⁺ "
            "translocates onto the breaking oxygen, §39.41(e)), the coordinate belongs in the "
            "break/form/mechanism list and this verdict is an artefact of leaving it out."
            % (ref["largest_atom_index"], ref["largest_atom_element"],
               ref["largest_fraction"], ref["coordinate_fraction_sum"],
               ref["ratio"] or float("inf")))
    elif not out["definition_independent"]:
        out["reasons"].append(
            "the two localisation definitions DISAGREE on this mode -- not blocking (a false "
            "block costs a reaction, a false pass costs core-hours), but the case is close "
            "enough that a human should read Ω and the localisation table.")
    else:
        out["reasons"].append(
            "not a spectator: the largest single-atom displacement is %s the declared "
            "coordinate set" % ("inside" if not ref["largest_is_outside_the_coordinate_set"]
                                else "outside, but does not outstrip"))
    return out


def mode_mass_localisation(mode, geometry):
    """모드의 제곱진폭이 원자별로 어떻게 나뉘는가 -- spectator 운동 탐지의 보조 지표.
    P1 에서는 Li 원자 하나가 63% 를 차지했다. 판정 없음, 데이터."""
    disp = (mode or {}).get("displacements") or []
    tot = sum(dx * dx + dy * dy + dz * dz for (_s, dx, dy, dz) in disp)
    if not tot:
        return []
    return [{"index": k, "element": disp[k][0],
             "amplitude_fraction": (disp[k][1] ** 2 + disp[k][2] ** 2
                                    + disp[k][3] ** 2) / tot}
            for k in range(len(disp))]


# =============================================================================================
# the correlation that decides U-55
# =============================================================================================

def _rank(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def correlate(records, predictor, response):
    """Correlate one curvature observable against one measured cost, across species.

    `records` are per-species dicts carrying the observable and the response. A record missing
    EITHER value is DROPPED AND NAMED -- never imputed, never zero-filled.

    🔴 Spearman is reported alongside Pearson because the expected relationship is monotonic but
       not linear (condition number spans orders of magnitude), and a Pearson coefficient on a
       heavy-tailed predictor is dominated by its largest point.
    """
    used, dropped = [], []
    for r in records or []:
        x, y = r.get(predictor), r.get(response)
        if isinstance(x, (int, float)) and isinstance(y, (int, float)):
            used.append((r.get("species_id"), float(x), float(y)))
        else:
            dropped.append({"species_id": r.get("species_id"),
                            "missing": [k for k, v in ((predictor, x), (response, y))
                                        if not isinstance(v, (int, float))]})
    xs = [u[1] for u in used]
    ys = [u[2] for u in used]
    pearson = _pearson(xs, ys)
    spearman = _pearson(_rank(xs), _rank(ys)) if len(xs) >= 3 else None

    out = {
        "predictor": predictor,
        "response": response,
        "n_used": len(used),
        "n_dropped": len(dropped),
        "dropped": dropped,
        "species_used": [u[0] for u in used],
        "pearson_r": pearson,
        "spearman_rho": spearman,
        "verdict": None,
        "warnings": [],
        "_no_threshold": ("🔴 no correlation threshold is hard-coded. 'Holds' vs 'excluded' is a "
                          "judgement for proposer5 against the reported n, rho and the scatter. "
                          "Hard-coding a cutoff here is how -100 cm^-1 got into M2."),
    }
    if len(used) < 3:
        out["warnings"].append(
            "🔴 correlation_not_computed: only %d species had BOTH %r and %r. A coefficient over "
            "fewer than 3 points is not a measurement." % (len(used), predictor, response))
    if dropped:
        # 🔴 The lead's instruction: a parse failure is visibly reported per species, and the
        #    count reaches the top-level summary. "n_frames is not the sample size" in a new place.
        out["warnings"].append(
            "🔴 correlation_sample_reduced: %d of %d species were DROPPED for missing values (%s). "
            "The coefficient below is over %d species, NOT the full batch -- do not quote it as "
            "if it covered all of them."
            % (len(dropped), len(dropped) + len(used),
               ", ".join(str(d["species_id"]) for d in dropped), len(used)))
    return out


def flatten_predictors(record):
    """Turn one species' observables into the flat predictor columns the correlation uses.

    🔴 `n_soft` and `kappa` are no longer ONE NUMBER EACH. The ladders are the point: they are
    what makes the threshold visible and the predictor falsifiable.
    """
    obs = record.get("curvature") or record
    out = {"nu_min_cm1": obs.get("nu_min_cm1"),
           "n_convergence_artefacts": obs.get("n_convergence_artefacts")}
    for k, v in (obs.get("trimmed_condition_numbers") or {}).items():
        out["kappa_k%s" % k] = v
    for x, v in (obs.get("n_soft_curve") or {}).items():
        out["n_soft_x%g" % x] = v
    return out


#: 🔴 THE ROLE OF THE n_soft CURVE. It SELECTS x. It does NOT validate the predictor at that x.
#: Selecting x on a dataset and then reporting its rho FROM THAT SAME DATASET is CIRCULAR -- the
#: coefficient is inflated by the selection. Validating a calibrated x needs a SECOND dataset;
#: B1 can supply one.
N_SOFT_CURVE_ROLE = {
    "role": "CALIBRATION ONLY",
    "selects": "the threshold x at which n_soft best predicts",
    "does_not": "validate the predictor at the selected x",
    "🔴 may_not_be_quoted_as": ("evidence that the predictor works. The rho at the winning x is "
                                "inflated by the selection that produced it."),
    "validation_requires": "a SECOND dataset -- B1 can supply it",
}


def kappa_stability(correlations):
    """🟢 THE PREDICTOR'S OWN FALSIFIER. Is the kappa-cost correlation stable across the trim k?

    ```
    present only at k=1        driven by ONE artefact mode  -> SPURIOUS
    stable across k = 1,2,3    real, and U-55 is genuinely decided
    ```
    Computed here rather than left to a reader, because a predictor with no way to fail is not a
    measurement. Returns `verdict: None` when there is not enough to judge -- never a default.
    """
    by_response = {}
    for c in correlations or []:
        p = c.get("predictor") or ""
        if not p.startswith("kappa_k"):
            continue
        try:
            k = int(p[len("kappa_k"):])
        except ValueError:
            continue
        by_response.setdefault(c.get("response"), {})[k] = c.get("spearman_rho")

    out = {"per_response": {}, "verdict": None, "warnings": [],
           "_rule": ("present only at k=1 -> SPURIOUS (one artefact mode). stable across "
                     "k=1,2,3 -> real. This is the predictor's own falsifier."),
           "_no_threshold": ("🔴 no cutoff is hard-coded for 'stable'. The rhos at each k are "
                             "reported and the judgement is proposer5's -- C-3's lesson.")}
    verdicts = []
    for resp, rhos in sorted(by_response.items()):
        vals = [rhos.get(k) for k in sorted(rhos)]
        present = [v for v in vals if isinstance(v, (int, float))]
        row = {"rho_by_k": dict((k, rhos[k]) for k in sorted(rhos)),
               "n_k_with_a_value": len(present),
               "abs_rho_spread": (None if len(present) < 2
                                  else max(abs(v) for v in present)
                                  - min(abs(v) for v in present))}
        out["per_response"][resp] = row
        if len(present) < 2:
            verdicts.append(None)
        else:
            verdicts.append("computed")
    if any(v is None for v in verdicts) or not verdicts:
        out["warnings"].append(
            "🔴 kappa_stability_indeterminate: fewer than two trim orders produced a coefficient, "
            "so whether the correlation is driven by a single mode CANNOT BE TOLD. Not 'stable'.")
    else:
        out["verdict"] = "computed"
    return out


def u55_panel(records):
    """All three observables against both cost responses. The U-55 read-out.

    🔴 The top-level summary carries `n_species_dropped` explicitly, because if 6 of 23 silently
       drop out then every coefficient is computed on 17 and nothing would say so.
    """
    flat = []
    for r in records or []:
        row = dict(r)
        row.update(flatten_predictors(r))
        flat.append(row)
    records = flat

    predictors = ["nu_min_cm1"]
    predictors += ["kappa_k%d" % k for k in TRIM_ORDERS]
    predictors += ["n_soft_x%g" % x for x in SOFT_MODE_CURVE_CM1]
    responses = ("opt_cycles", "core_hours")
    panel = [correlate(records, p, r) for p in predictors for r in responses]
    complete = [r for r in records or []
                if all(isinstance(r.get(k), (int, float))
                       for k in tuple(predictors) + responses)]
    incomplete = [r.get("species_id") for r in records or []
                  if r not in complete]
    out = {
        "question": ("U-55: is the Li+-multiligand class INTRINSICALLY hard to optimise, or was "
                     "the 283 core-h an artefact of a bad start?"),
        "n_species_in": len(records or []),
        "n_species_complete": len(complete),
        "n_species_dropped": len(incomplete),
        "species_dropped": incomplete,
        "correlations": panel,
        "pre_registration": dict(PRE_REGISTRATION),
        "primary": None,
        "primary_ladder_context": None,
        "primary_verdict": None,
        "🔒 primary_verdict_is_a_judgement_for": "proposer",
        # 🔴 B-5: step (2) of `_readability`'s reading order NAMES this quantity but, before this
        # field existed, did not HAND IT to the reader -- it lived only inside each species'
        # own `curvature` record elsewhere in the report, keyed by `species_id`, so following the
        # panel's own stated order meant leaving the panel to go reconstruct a per-species table
        # by hand. It is surfaced here, at the SAME level as `primary`, so step (2) is actually
        # followable from this dict alone -- same convention as `species_dropped` a few lines up.
        "n_convergence_artefacts_by_species": dict(
            (r.get("species_id"), r.get("n_convergence_artefacts")) for r in records or []),
        "species_with_convergence_artefacts": [
            r.get("species_id") for r in records or []
            if isinstance(r.get("n_convergence_artefacts"), (int, float))
            and r.get("n_convergence_artefacts") > 0],
        "kappa_stability": kappa_stability(panel),
        "predictors": list(predictors),
        "n_soft_curve_role": dict(N_SOFT_CURVE_ROLE),
        "n_correlations": len(panel),
        "headline": None,
        "warnings": [],
        "_readability": (
            "🔴 %d correlations, and ONE of them is the pre-registered PRIMARY. Reading order: "
            "(1) `primary` together with `primary_ladder_context` -- a FRAMING, not a stop-gate; "
            "(2) `n_convergence_artefacts_by_species` (summarised in "
            "`species_with_convergence_artefacts`), because many artefacts on a species mean "
            "IT did not converge, which changes what (1) means for that species; (3) everything "
            "else, only if 1-2 leave a question open. `n_soft` and `kappa` are LADDERS on "
            "purpose -- that is what makes the threshold visible and the predictor "
            "falsifiable." % len(panel)),
        "_temperature_independent": (
            "🟢 these observables are properties of the Hessian at the minimum and are "
            "TEMPERATURE-INDEPENDENT, so the MTD T_eff problem (1.41-1.70x, bias-driven, "
            "irreducible) does not touch them."),
        "_coverage": ("🟢 available for every species that produced a frequency log, where a "
                      "dissociation rate would only ever have covered the species that happened "
                      "to come apart."),
    }
    if incomplete:
        out["warnings"].append(
            "🔴 u55_panel_incomplete: %d of %d species lack at least one of the six quantities "
            "(%s). Every coefficient in this panel is computed on a REDUCED sample and its own "
            "`n_used` says how reduced." % (len(incomplete), len(records or []),
                                            ", ".join(str(s) for s in incomplete)))
    # 🔒 THE PRIMARY, SHOWN IN ITS LADDER. Never a boolean: a boolean needs a cutoff on rho, and
    #    a hard-coded cutoff here is how -100 cm^-1 got into M2. STATE THE RULE AND SHOW THE
    #    NUMBERS; DO NOT EVALUATE THE RULE.
    by_key = dict(((c["predictor"], c["response"]), c) for c in panel)
    prim = by_key.get((PRE_REGISTRATION["primary_predictor"],
                       PRE_REGISTRATION["primary_response"]))
    out["primary"] = prim
    out["primary_ladder_context"] = dict(
        (k, by_key.get(("kappa_k%d" % k, PRE_REGISTRATION["primary_response"])))
        for k in TRIM_ORDERS)
    out["_read_the_primary_in_its_ladder"] = (
        "🔴 READ `primary` AND `primary_ladder_context` TOGETHER. Not a stop-gate -- a FRAMING. "
        "The primary is never skipped and never read naked. %s"
        % PRE_REGISTRATION["interpretation_rule"])
    if prim is None:
        out["warnings"].append(
            "🔴 primary_correlation_absent: the pre-registered primary (%s vs %s) is not in the "
            "panel. Something changed the predictor set and the pre-registration no longer "
            "points at anything."
            % (PRE_REGISTRATION["primary_predictor"], PRE_REGISTRATION["primary_response"]))
    out["warnings"].extend(out["kappa_stability"]["warnings"])
    # A compact headline so the ladder does not have to be read in full to see the shape.
    best = [c for c in panel
            if isinstance(c.get("spearman_rho"), (int, float))]
    if best:
        top = max(best, key=lambda c: abs(c["spearman_rho"]))
        out["headline"] = {
            "strongest_predictor": top["predictor"],
            "response": top["response"],
            "spearman_rho": top["spearman_rho"],
            "n_used": top["n_used"],
            "🔴": ("STRONGEST != SIGNIFICANT and != CAUSAL. Picking the largest of %d "
                   "coefficients is a multiple-comparisons selection; treat this as a POINTER "
                   "into the table, never as the result." % len(panel)),
        }
    for c in panel:
        out["warnings"].extend(c["warnings"])
    return out
