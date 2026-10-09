"""SP ladder — DFT single points laid on a GFN2 path (§39.47(c), §39.48(d)/(e), §39.49).

A full transition-state search is unaffordable at production size, so the ladder puts DFT single
points on a path the cheap engine already produced and reads a barrier from those. `n` is one
rung's coordination number.

🔴 WHAT THIS MODULE DOES NOT DO: it does not GENERATE the path. It consumes one, and it refuses
   unless that path arrives with the provenance every ruling this round attached to it —
   dimensionality, a G-SCAN verdict, a seed record, and a relaxation state. Generating a path
   here would duplicate `gfn2_scan` and, worse, would let the ladder quietly accept a path that
   never passed the gate.

🔴 UNITS: energies HARTREE on the way in (both engines' native unit), eV on the way out for the
   barrier. Conversions go through `units`, never inline.
"""

from . import units

#: §39.48(d): both endpoints + FIVE consecutive path points centred on the GFN2 maximum.
#: Five, not one: the DFT maximum along a GFN2 path need not sit at the GFN2 maximum, and
#: sampling a maximum on a coarse grid UNDER-estimates it — measured at 0.10 eV in this project
#: (§39.43's 0.05 vs 0.01 Å grids). A barrier biased LOW is a rate biased HIGH, which is §0-h's
#: optimistic direction, the one this project has never self-corrected from.
SP_BRACKET_POINTS = 5
SP_TOTAL_POINTS = 7
SP_TOTAL_POINTS_MAX = 9

#: Provenance a path MUST carry before the ladder will spend DFT on it. Each entry exists
#: because a ruling this round said the ladder's answer is void without it.
REQUIRED_PATH_PROVENANCE = {
    "hamiltonian": "which engine produced the path (§39.50(b): no cross-Hamiltonian arithmetic)",
    "dimensionality": ("1 or 2. §39.48(c): hysteresis grows with n (0.00 / 0.10 / 0.21 eV at "
                       "n = 1 / 2 / 3), so n >= 2 must consume a 2-D path or the barrier is "
                       "inflated by an unmeasured amount"),
    "gscan_verdict": ("§39.45: the path must have passed the discontinuity gate. A guess from a "
                      "path-dependent profile starts at the wrong geometry"),
    "seeds": ("§39.49: >= 3 kick seeds, floor test, lowest taken, with the spread and basin "
              "count reported — and n_seeds_attempted PRE-REGISTERED so it cannot shrink"),
    "relaxation_state": ("§39.64/§39.71: both ends of a barrier must come from the same "
                         "relaxation state, or the difference carries a geometry offset that "
                         "GROWS WITH n — which is the very variable the ladder measures"),
}


class PathPreconditionError(RuntimeError):
    """The path does not carry what the ladder needs. Distinct from a chemistry outcome: this
    says the ladder must not spend, not that the reaction lacks a barrier."""


def check_path_preconditions(path, n):
    """Every §39.47–§39.49 precondition on the path, checked before any DFT is ordered.

    Returns a record; `ok` False means DO NOT SPEND. 🔴 Never raises for a merely-absent field —
    the caller records the refusal as data and the reasons name what is missing, because "the
    ladder did not run and here is why" is a result and a crash is not.
    """
    out = {"ok": True, "missing": [], "reasons": [], "n": n,
           "cause_class": "protocol"}
    path = path or {}
    for key, why in sorted(REQUIRED_PATH_PROVENANCE.items()):
        if path.get(key) in (None, "", [], {}):
            out["ok"] = False
            out["missing"].append(key)
            out["reasons"].append("path is missing %r -- %s" % (key, why))

    if path.get("hamiltonian") and path["hamiltonian"] != "gfn2":
        out["ok"] = False
        out["reasons"].append(
            "path came from %r, not gfn2 -- the ladder lays DFT points on a CHEAP path by "
            "construction; a path from another engine is a different experiment"
            % path["hamiltonian"])

    # 🔴 §39.48(c): 1-D is admissible ONLY at n = 1, where hysteresis was measured at 0.003 eV.
    #    At n >= 2 a 1-D path inflates the barrier by an amount that grows with n.
    dim = path.get("dimensionality")
    if dim is not None and int(n) >= 2 and int(dim) < 2:
        out["ok"] = False
        out["reasons"].append(
            "rung n=%s consumes a %s-D path, but §39.48(c) requires 2-D at n >= 2: 1-D "
            "inflates the barrier by 0.00 / 0.10 / 0.21 eV at n = 1 / 2 / 3, and that error "
            "grows with exactly the variable this ladder measures" % (n, dim))

    verdict = path.get("gscan_verdict") or {}
    if verdict and verdict.get("fired"):
        out["ok"] = False
        out["reasons"].append(
            "the path's G-SCAN verdict FIRED -- it is path-dependent, so single points laid on "
            "it describe a path the reaction does not take (§39.45)")

    seeds = path.get("seeds") or {}
    if seeds:
        attempted = seeds.get("n_seeds_attempted")
        converged = seeds.get("n_seeds_converged")
        if attempted is None or converged is None:
            out["ok"] = False
            out["reasons"].append(
                "the seed record does not carry both n_seeds_attempted and "
                "n_seeds_converged -- a spread over only the seeds that survived is a "
                "success-conditioned statistic (§39.51(a))")
        elif attempted < 3:
            out["ok"] = False
            out["reasons"].append(
                "only %s kick seeds attempted; §39.49 requires >= 3 at every rung, because "
                "path-selection noise is a property of the SYSTEM and gets rougher with n"
                % attempted)
    if out["ok"]:
        out["reasons"].append("every path precondition is satisfied")
    return out


def select_sp_points(energies_hartree, n_points=SP_TOTAL_POINTS):
    """Which path points get a DFT single point (§39.48(d)).

    Both endpoints + `SP_BRACKET_POINTS` consecutive points centred on the GFN2 maximum.
    Returns sorted 0-based indices, or None if the path is too short to bracket a maximum.
    """
    es = [e for e in (energies_hartree or [])]
    if len(es) < 3 or any(e is None for e in es):
        return None
    top = max(range(len(es)), key=lambda k: es[k])
    half = SP_BRACKET_POINTS // 2
    lo = max(0, min(top - half, len(es) - SP_BRACKET_POINTS))
    bracket = list(range(lo, min(lo + SP_BRACKET_POINTS, len(es))))
    return sorted(set([0, len(es) - 1] + bracket))


def needs_bracket_extension(sp_indices, dft_energies_hartree):
    """🔴 [§39.48(d)] Did the DFT maximum land at an EDGE of the sampled bracket?

    If so the bracket must extend by 2 (to at most 9 points): a maximum at the edge means the
    real one may lie outside what was sampled, and a barrier read from the edge is a LOWER
    bound reported as a value. Same coarse+triggered shape as §39.42(b), reused not reinvented.
    """
    idx = list(sp_indices or [])
    es = list(dft_energies_hartree or [])
    if len(idx) != len(es) or len(idx) < 3 or any(e is None for e in es):
        return {"extend": False, "reason": "cannot judge -- missing DFT energies"}
    interior = [k for k in range(len(idx)) if idx[k] not in (idx[0], idx[-1])]
    if not interior:
        return {"extend": False, "reason": "no interior points"}
    top = max(interior, key=lambda k: es[k])
    at_edge = top in (interior[0], interior[-1])
    return {"extend": bool(at_edge),
            "dft_max_index": idx[top],
            "reason": ("the DFT maximum sits at a bracket EDGE -- the real maximum may lie "
                       "outside the sampled window, so this barrier is a LOWER BOUND until the "
                       "bracket is extended (§39.48(d))" if at_edge
                       else "the DFT maximum is interior to the sampled bracket")}


def barrier_ev(sp_energies_hartree, reference_index=0):
    """The rung's barrier, in eV, measured from the PATH'S OWN first frame.

    🔴 [§39.64/§39.71] The reference is the path's first frame computed at DFT — **not** the
    certified reactant's energy. The certified reactant supplies the STRUCTURE the path starts
    from and never an energy: mixing a DFT-optimised reactant with a path frame puts the two
    ends of the barrier in different relaxation states, and that offset GROWS WITH n — so it is
    not safe even though each rung looks fine on its own. engineer7 found this in its own spec
    by applying the no-cross-Hamiltonian rule to it.
    """
    es = list(sp_energies_hartree or [])
    if len(es) < 2 or any(e is None for e in es):
        return None
    return units.hartree_to_ev(max(es) - es[reference_index])


def per_sp_core_hours(total_core_hours, n_points):
    """The measurement the whole ladder exists to produce first (§39.48(e)).

    🔴 This project has never measured a standalone single point. Every per-SP figure in the
    plan is a derived stack, and the FIRST rung to return replaces it — later rungs must be
    re-derived from this number, never from the stack.
    """
    if not total_core_hours or not n_points:
        return None
    return float(total_core_hours) / float(n_points)
