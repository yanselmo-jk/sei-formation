"""GFN2-xTB relaxed scans — the PRODUCER of the discontinuity gate's verdict (§39.45, §39.47).

🔴 WHY THIS MODULE EXISTS. `b0f_deck.gscan2_decision` could render a verdict but nothing could
   produce its input: this package had no xtb constrained-scan machinery at all (`payload/P3.sh`
   uses `--path`, which is a different tool). So `payload/U56.sh` refused the single-ended arm
   outright — correct, but it meant the arm did not run.

🔒 WHY THE GATE RUNS HERE AND NOT ON THE DFT SCAN (§39.47(a)): the gate's PURPOSE is to decide
   whether to fund the DFT attempt, and the TS guess is generated at GFN2, so the bidirectional
   check runs where the guess is made — which is where it is free. A DFT scan has the same
   hysteresis pathology but does not give a different ANSWER about how many coordinates the
   reaction needs, and running it twice would cost 2x and breach `TOTAL_POINTS_MAX = 20`
   (DFT, one direction). The DFT fallback scan INHERITS this verdict and runs one direction.

🔴 UNITS. Lengths Angstrom, energies HARTREE (xtb's own unit — `xtbscan.log` prints
   ` energy: <E_hartree> xtb: ...`). Conversions go through `units`, never inline.
🔴 HAMILTONIAN. Everything this module produces is GFN2. It is tagged as such on the way out so
   that `gscan2_decision` can refuse to subtract it from anything else (§39.50(b)).

⚠ FORMAT PROVENANCE: the `$constrain`/`$scan` input block and the `xtbscan.log` trajectory shape
  were established BY EXECUTION on the dev box (xtb 6.7.1), not from memory — see
  `tests/fixtures/xtb_relaxed_scan_r_a.{inp,log}` and their PROVENANCE entry. A cluster-side
  re-check rides the next submission's smoke, since a vendored binary on a different machine is
  a different claim (the same rule that made the KNL `$wall` check its own item).
"""

import os
import re

#: xtb's own default is 0.5 Hartree/Bohr^2-ish for `force constant=`; it is xtb's documented
#: default for constrained optimisation and is NOT a number this project derived. Named here so
#: that if it ever needs changing there is one place and this sentence is next to it.
CONSTRAIN_FORCE_CONSTANT = 0.5

RE_ENERGY = re.compile(r"energy:\s*(-?\d+\.\d+)")


def scan_input(pair_1based, r_start_ang, r_end_ang, n_points,
               force_constant=CONSTRAIN_FORCE_CONSTANT):
    """The xtb `--input` block for ONE relaxed scan along ONE distance.

    `pair_1based` is (i, j) in xtb's 1-based atom numbering. 🔴 The mapping stores 0-based
    indices (`roles.py` convention); convert with `+1` at the call site and nowhere else — the
    same discipline `b0f_deck._g16_index` applies for Gaussian.

    A scan from a LARGER to a SMALLER distance is a legitimate input and is exactly what
    G-SCAN-1's reverse direction needs, so the direction is NOT validated here (unlike the DFT
    deck, where a negative step would silently be a different experiment).
    """
    i, j = int(pair_1based[0]), int(pair_1based[1])
    if i == j or i < 1 or j < 1:
        raise ValueError("scan pair %r is not two distinct 1-based atom indices"
                         % (pair_1based,))
    if int(n_points) < 2:
        raise ValueError("a scan needs at least 2 points, got %r" % (n_points,))
    return ("$constrain\n"
            "  force constant=%s\n"
            "  distance: %d, %d, auto\n"
            "$scan\n"
            "  1: %.4f, %.4f, %d\n"
            "$end\n"
            % (force_constant, i, j, float(r_start_ang), float(r_end_ang), int(n_points)))


def constrain_input(pair_1based, distance_ang, force_constant=CONSTRAIN_FORCE_CONSTANT):
    """`--input` block that HOLDS one distance and relaxes everything else. No `$scan`.

    🔴 WHY A CONSTRAINED PRE-RELAXATION AND NOT A FREE ONE. The gate measures both of its
    clauses from the reactant end (§39.64), so that frame must be a converged GFN2 structure --
    but a FREE GFN2 optimisation of a reduced radical does not stay in the reactant basin.
    Measured on R-A: a free `--opt` leaves the ring-closed basin outright, after which the
    scan starts from an already-opened structure and the forward barrier reads ~15 eV. That is
    the same class of problem as §39.42(a)'s kicked seeds and ADR-067's n_imag = 5 -- an
    idealised guess relaxed without a leash goes somewhere else.
    ⟹ hold the breaking coordinate at the reactant's own value, let the rest relax.
    """
    i, j = int(pair_1based[0]), int(pair_1based[1])
    return ("$constrain\n"
            "  force constant=%s\n"
            "  distance: %d, %d, %.4f\n"
            "$end\n" % (force_constant, i, j, float(distance_ang)))


def parse_scan_log(text, hamiltonian="gfn2"):
    """`xtbscan.log` → the profile shape `b0f_deck.gscan2_decision` consumes.

    Format (measured, xtb 6.7.1):
        <n_atoms>
         energy: -20.935733838156 xtb: 6.7.1 (edcfbbe)
        C   x y z
        ...                                    <- repeated once per scan point

    Returns `{"hamiltonian", "points": [{"point_index", "energy_hartree", "geometry"}],
              "n_points", "warnings"}`.
    🔴 A frame whose energy line cannot be read keeps its place with `energy_hartree = None`
    rather than being dropped: a profile silently missing its maximum is worse than one that
    reports a hole, and the gate already treats a hole as unjudgeable.
    """
    lines = (text or "").splitlines()
    points, warnings = [], []
    i = 0
    while i < len(lines):
        head = lines[i].strip()
        if not head.isdigit():
            i += 1
            continue
        n = int(head)
        if i + 1 + n >= len(lines) + 1 and i + 1 >= len(lines):
            warnings.append("truncated frame at line %d" % (i + 1))
            break
        comment = lines[i + 1] if i + 1 < len(lines) else ""
        m = RE_ENERGY.search(comment)
        if not m:
            warnings.append("frame %d has no `energy:` on its comment line"
                            % (len(points) + 1))
        geometry = []
        for k in range(i + 2, min(i + 2 + n, len(lines))):
            f = lines[k].split()
            if len(f) < 4:
                break
            try:
                geometry.append((f[0], float(f[1]), float(f[2]), float(f[3])))
            except ValueError:
                break
        if len(geometry) != n:
            warnings.append("frame %d declared %d atoms but %d were readable"
                            % (len(points) + 1, n, len(geometry)))
        points.append({"point_index": len(points) + 1,
                       "energy_hartree": float(m.group(1)) if m else None,
                       "geometry": geometry})
        # 🔴 [critic10] ADVANCE BY WHAT WAS ACTUALLY READ, NOT BY THE DECLARED COUNT.
        # Using the declared `n` after a short frame lands the cursor INSIDE the next frame's
        # body rather than on its header, and the scanner then skips that whole frame -- a
        # complete, well-formed scan point disappears with no warning naming the loss. A
        # wall-clock kill or a partially flushed `xtbscan.log` produces exactly that shape, and
        # this profile decides whether a real DFT attempt gets funded.
        step = 2 + len(geometry)
        if len(geometry) != n:
            nxt = lines[i + step].strip() if i + step < len(lines) else ""
            if not nxt.isdigit():
                warnings.append(
                    "🔴 parsing may have DESYNCHRONISED at frame %d: it declared %d atoms, %d "
                    "were readable, and the next line is not a frame header. Points after this "
                    "one may be missing entirely -- treat this profile as unusable rather than "
                    "short." % (len(points), n, len(geometry)))
        i += step
    return {"hamiltonian": hamiltonian, "points": points, "n_points": len(points),
            "warnings": warnings}


def frame_xyz(point, comment=""):
    """One scan point → xyz text, for starting the next job from it."""
    g = point.get("geometry") or []
    return ("%d\n%s\n" % (len(g), comment)
            + "".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in g))


def distance_ang(geometry, i, j):
    """d(i, j) in Angstrom from a 0-based-indexed geometry list."""
    a, b = geometry[i], geometry[j]
    return sum((a[k + 1] - b[k + 1]) ** 2 for k in range(3)) ** 0.5


def bidirectional_plan(geometry, pair_0based, n_points, step_ang):
    """The two scan endpoints for G-SCAN-1, on ONE grid.

    Forward runs from the reactant's own d(break) outwards by `n_points` steps; reverse runs
    the SAME endpoints backwards, started from the forward scan's final frame.
    🔴 [§39.68(1)] `geometry` must be the **PRE-RELAXED** structure, not the raw certified one:
    after the constrained GFN2 relaxation the two distances differ, and the scan has to start
    where the structure actually is. Anchoring on the raw certified distance was an unruled
    choice of mine and it is what made frame 0 arrive still descending.
    🔴 Same grid in both directions is not a detail — it is what makes the two profiles
    comparable point by point (G-SCAN-3) rather than two unrelated calculations.
    """
    i, j = pair_0based
    d0 = distance_ang(geometry, i, j)
    # 🔴 [§39.68(2)] TOTAL EXTENSION IS n_points x step (12 x 0.10 = +1.2 A), not
    # (n_points - 1) x step. §39.42(b) registered "+1.2 A"; an off-by-one here silently
    # registers a different experiment, which is the exact failure the window enforcement
    # exists to prevent.
    d1 = d0 + float(step_ang) * int(n_points)
    return {"pair_1based": (i + 1, j + 1), "d_start_ang": d0, "d_end_ang": d1,
            "n_points": int(n_points), "step_ang": float(step_ang),
            "forward": (d0, d1), "reverse": (d1, d0)}


def derive_direction(profile, pair_0based):
    """🔴 [§39.66] Is this coordinate BREAKING or FORMING along the path? **DERIVED from the
    scan we already run, never declared.**

    A declared direction field can be mis-declared, and a mis-declared direction inverts the
    one-sided bracket check into a machine for refusing good reactions. A measured one cannot
    be mis-declared -- it is read off the trajectory.

    Returns "break" (distance rises monotonically), "form" (falls monotonically), or None.
    🔴 None = NON-MONOTONIC = no well-defined direction. The caller must record
    `applicable: false, non_monotonic` and COUNT it, not silently drop the coordinate. All
    three B0-F reactions are monotonic on their Li coordinate today (2.50->1.75, 2.75->1.80,
    2.49->1.64), but that is a measurement, not a guarantee for reactions nobody has run.
    ⚠ Deriving the direction at GFN2 and applying it to a DFT saddle IS cross-engine. It
    transfers a SIGN, not a magnitude -- stated rather than hidden (§39.50(b) forbids
    subtracting energies across Hamiltonians; this carries no energy at all).
    """
    i, j = pair_0based
    ds = [distance_ang(p["geometry"], i, j)
          for p in (profile or {}).get("points") or [] if p.get("geometry")]
    if len(ds) < 2:
        return None
    rises = all(b > a for a, b in zip(ds, ds[1:]))
    falls = all(b < a for a, b in zip(ds, ds[1:]))
    if rises:
        return "break"
    if falls:
        return "form"
    return None


def direction_agrees_with_endpoints(direction, reactant_ang, product_ang):
    """🟢 [§39.66] Free cross-check where BOTH endpoints are certified (R-A only today): the
    derived direction must agree with the sign of (product - reactant).

    Disagreement means the scan and the certified endpoints describe different reactions --
    worth knowing on its own, and cheap because both numbers already exist. Returns None when
    the check cannot be made rather than a silent True.
    """
    if direction is None or reactant_ang is None or product_ang is None:
        return None
    return (product_ang > reactant_ang) == (direction == "break")


#: xtb's own words, read rather than inferred (§39.68(3)(i)). [VERIFIED by execution.]
OPT_CONVERGED_MARK = "GEOMETRY OPTIMIZATION CONVERGED"


def prerelax_converged(opt_output_text):
    """Did the constrained pre-relaxation converge? Read from xtb's output, never inferred
    from a zero exit code -- xtb returns 0 on a run that stopped without converging."""
    return OPT_CONVERGED_MARK in (opt_output_text or "")


def frame0_check(profile, converged):
    """🔴 [§39.68(3)] FRAME 0'S OWN CRITERION. Neither part is a tuned constant:
        (i)  the constrained pre-relaxation must report CONVERGED (xtb says so; do not infer)
        (ii) the profile must NOT DESCEND from frame 0 to frame 1

    🔴🔴 FAILURE IS `indeterminate`, NEVER `fired`. An unsettled frame 0 produces a FALSE FIRE
    -- measured on R-A: 0.4530 eV against a true 0.0216 -- because §39.64 references BOTH gate
    clauses to that frame. **A gate that blocks because its own reference was unfinished is
    reporting on itself, and it must say so rather than blaming the reaction.**
    ⟹ cause class `protocol`: a fact about our procedure, not about the chemistry. Folding it
    into the chemical tally would corrupt U-56b exactly as budget-truncated nulls would.
    """
    out = {"ok": True, "converged": bool(converged), "descends_at_frame1": None,
           "reasons": [], "cause_class": "protocol"}
    if not converged:
        out["ok"] = False
        out["reasons"].append(
            "the constrained pre-relaxation did not report `%s` -- frame 0 is not a settled "
            "structure, and both gate clauses are measured from it (§39.68(3)(i))"
            % OPT_CONVERGED_MARK)
    es = [p.get("energy_hartree") for p in (profile or {}).get("points") or []]
    if len(es) >= 2 and es[0] is not None and es[1] is not None:
        out["descends_at_frame1"] = bool(es[1] < es[0])
        if out["descends_at_frame1"]:
            from . import units as _units
            out["ok"] = False
            out["reasons"].append(
                "the profile DESCENDS from frame 0 to frame 1 by %.4f eV -- frame 0 was still "
                "relaxing, so it is not the reactant reference the gate needs (§39.68(3)(ii))"
                % abs(_units.hartree_to_ev(es[1] - es[0])))
    else:
        out["ok"] = False
        out["reasons"].append("fewer than two readable frames -- frame 0 cannot be checked")
    if out["ok"]:
        out["reasons"].append("frame 0 converged and the profile does not descend from it")
    return out


def total_points(*profiles):
    """Points summed over every profile — what §39.47(a)'s GFN2 cap is counted against
    (`SCAN_POINTS_GFN2_MAX`, all directions and both dimensions, per reaction)."""
    return sum((p or {}).get("n_points") or 0 for p in profiles)


#: xtb prints a numbered fatal-error stack. The innermost frame (`-1-`) is the actual cause.
#: [VERIFIED on a real failure: rc 128 with
#:  "-1- scf: Self consistent charge iterator did not converge"]
RE_XTB_ERROR_FRAME = re.compile(r"^\s*-\d+-\s*(.+?)\s*$", re.M)


def parse_failure(output_text):
    """Why an xtb run aborted — the innermost frame of its fatal-error stack, plus a coarse
    kind. 🔴 `rc != 0` alone says a run failed; it does not say whether the ENGINE failed to
    converge on a hard geometry or whether we handed it something broken, and those have
    different owners. Recording the reason is what makes the difference visible.

    Returns `{"aborted", "cause", "kind"}` with `kind` in
    `scf_not_converged | geometry_optimization_failed | other | none`.
    """
    t = output_text or ""
    if "abnormal termination" not in t and "[ERROR]" not in t:
        return {"aborted": False, "cause": None, "kind": "none"}
    frames = RE_XTB_ERROR_FRAME.findall(t)
    cause = frames[-1] if frames else "unattributed (no numbered error frame in the output)"
    low = cause.lower()
    if "self consistent charge" in low or "scf" in low:
        kind = "scf_not_converged"
    elif "optimi" in low:
        kind = "geometry_optimization_failed"
    else:
        kind = "other"
    return {"aborted": True, "cause": cause, "kind": kind,
            "stack": frames[-6:] if frames else []}


def read_log(path, hamiltonian="gfn2"):
    if not os.path.exists(path):
        return {"hamiltonian": hamiltonian, "points": [], "n_points": 0,
                "warnings": ["%s does not exist -- the scan produced no trajectory" % path]}
    with open(path, errors="replace") as fh:
        return parse_scan_log(fh.read(), hamiltonian=hamiltonian)
