"""F1 falsifier observables (`config/f1_required_observables.json`, ADR-099/§39.32(h)).

🔴 THE BINDING RULE, restated at the code that implements it: if the merged endpoint pilot
reports only cost and convergence, F1 has not been run. Every function here is a PURE
GEOMETRY/FREQUENCY measurement -- no job submission, no I/O -- so it can be tested against
the real shipped `.xyz` files without a QC engine.

🔴 WHAT THIS FILE DOES **NOT** PROVIDE: true point-group detection (a Schoenflies symbol).
That is registered elsewhere as PRODUCTION work and is deliberately NOT implemented anywhere
in this package (`guards.SYMMETRY_COVERAGE`). `f1_required_observables.json`'s "point_group"
item asks for the point group "as data" -- what this module actually supplies is
`guards.symmetric_placement_flags`, a NARROWER fingerprint with a stated, incomplete
coverage. **Do not read `symmetric_fingerprint` below as a point-group answer.** It is the
same honest substitution `guards.py` already makes everywhere else in this codebase.

Roles, not indices: EC's five ring bonds and the Li-O=C angle are found via `roles.py`'s
role perception, not by hand-picked atom numbers -- the same file works on the reactant and
the product, and on any conformer, without per-species bookkeeping.
"""

from . import xyzgraph
from .. import guards, roles


def ring_bond_lengths(atoms, tolerance=xyzgraph.BOND_TOLERANCE):
    """The five EC ring bonds -- C1-O2, C1-O5, O2-C3, C4-O5, C3-C4 in
    `f1_required_observables.json`'s labelling -- found by role pair, not by index.

    🔴 Two of the three role pairs are DELIBERATELY ambiguous in `roles.py`'s own terms (the
    carbonyl carbon has two ether-oxygen neighbours; each ether oxygen has one sp3-carbon
    neighbour) -- that ambiguity is not a defect here, it is exactly how BOTH members of each
    symmetric pair are collected instead of just one. `resolve_bond`'s own "pick one" behaviour
    would silently drop half the ring; this function reads `candidates`, not `selected`.
    """
    pairs = [("C_carbonyl", "O_ether"), ("O_ether", "C_sp3"), ("C_sp3", "C_sp3")]
    bonds = []
    warnings = []
    for role_a, role_b in pairs:
        res = roles.resolve_bond(atoms, role_a, role_b, tolerance=tolerance)
        if res["n_candidates"] == 0:
            warnings.append("🔴 ring_bond_missing: no %s-%s bond found -- this geometry does "
                            "not have an intact EC ring." % (role_a, role_b))
            continue
        for i, j in res["candidates"]:
            bonds.append({"atoms": [i, j], "roles": [role_a, role_b],
                         "distance_ang": xyzgraph.distance_ang(atoms[i], atoms[j])})
    return {
        "bonds": bonds,
        "n_bonds": len(bonds),
        "distances_ang": [b["distance_ang"] for b in bonds],
        "falsifies_if_all_equal_to": (1.399, 1.400),
        "warnings": warnings,
    }


def li_o_c_angle_deg(atoms, tolerance=xyzgraph.BOND_TOLERANCE):
    """∠Li-O=C: Li, the carbonyl oxygen, and the carbonyl carbon it double-bonds. `None` (with
    a warning) if any role is missing or the Li/O_carbonyl role each has more than one member
    -- EC has exactly one of each; more than one means this is not the species F1 expects."""
    r = roles.perceive(atoms, tolerance=tolerance)
    out = {"angle_deg": None, "warnings": [],
          "falsifies_if_stays_at_deg": 180.00,
          "external_reference_deg": "experimental ~138(2) deg (ADR-066/080)"}
    for role in ("Li", "O_carbonyl", "C_carbonyl"):
        if not r.get(role):
            out["warnings"].append(
                "🔴 angle_role_missing: no %r atom perceived -- cannot compute the angle."
                % role)
            return out
        if len(r[role]) > 1:
            out["warnings"].append(
                "🔴 angle_role_not_unique: %d %r atoms perceived (expected exactly 1) -- "
                "refusing to guess which one." % (len(r[role]), role))
            return out
    li, o_c, c_c = r["Li"][0], r["O_carbonyl"][0], r["C_carbonyl"][0]
    out["angle_deg"] = xyzgraph.angle_deg(atoms[li], atoms[o_c], atoms[c_c])
    out["atoms"] = {"Li": li, "O_carbonyl": o_c, "C_carbonyl": c_c}
    return out


def n_imaginary(freqs):
    """Count of negative (imaginary, project-wide convention) frequencies. `None` (not 0) when
    `freqs` is empty -- no frequency data is NOT a measurement of zero imaginary modes."""
    if not freqs:
        return None
    return sum(1 for f in freqs if f < 0)


def symmetric_fingerprint(atoms, centre="Li"):
    """The F1 'point_group' slot, honestly relabelled. See this module's docstring: this is
    `guards.symmetric_placement_flags`, NOT point-group detection."""
    return guards.symmetric_placement_flags(atoms, centre=centre)


def stage1_exit_structural_set(atoms):
    """🟢 FREE -- purely geometric, from stage 1's output `.xyz` alone, no job.

    ADR-099 / F1's `stage1_exit_structural_set`: point group (fingerprint) + ∠Li-O=C + max
    out-of-plane deviation, all AT STAGE-1 EXIT. `binding`: a non-C1 fingerprint here is a
    DEFECT REPORT about the route (nosymm/perturbation failed), not a fact about the molecule.
    """
    fp = symmetric_fingerprint(atoms)
    angle = li_o_c_angle_deg(atoms)
    cop = guards.coplanarity(atoms)
    return {
        "symmetric_fingerprint": fp,
        "li_o_c_angle_deg": angle,
        "max_out_of_plane_ang": cop.get("max_out_of_plane_ang"),
        "binding": ("a symmetric_fingerprint['flagged'] True here means the C-9 perturbation "
                   "did not survive stage 1 -- report this as a DEFECT in the route, not as a "
                   "property of the molecule (f1_required_observables.json)."),
    }
