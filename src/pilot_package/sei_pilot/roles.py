"""Chemical-role perception, and the role -> atom-index MAPPING that every deck must carry.

🔴 WHY THIS EXISTS (lead ruling, 2026-08-19, adding to the coder's own demand):
   B0-F's break/form lists are given **by chemical role, not by atom index** --
   `R-A breaks O(ether)-C(sp3)`, `R-B breaks O(ether)-C(carbonyl)`. Roles are what a chemist can
   state and what transfers to a species nobody has drawn yet; indices are an artefact of the file.
   ⟹ **The builder must emit the role->index mapping alongside each deck, and that mapping is what
      the mode-overlap Omega is computed against. A DECK WITHOUT ITS MAPPING CANNOT BE SCORED.**
   `require_mapping()` enforces that; it raises rather than returning a flag.

🔴 AND WHY AMBIGUITY IS SURFACED RATHER THAN RESOLVED.
   In EC's ring there are TWO (O_ether, C_sp3) bonds -- O2-C3 and O5-C4 -- equivalent by the
   mirror symmetry of the idealised drawing and NOT equivalent once Li coordinates asymmetrically
   or once C-9's out-of-plane kick has been applied. A resolver that silently returns "the first
   one" would be picking a reaction coordinate by list order. So `resolve_bond` returns EVERY
   candidate, records the tie-break it used, and sets `ambiguous` when there was a choice to make.
   🔒 This is the same defect shape as P1: a method converged to *a* saddle and nothing recorded
   that it was not the intended one.

SPLIT OF CONCERNS, deliberate:
    perception (which atom plays which role)   -> HERE, an algorithm, testable against real files
    reaction definitions (which roles break)   -> config/b0_reactions.json, DATA per ADR-001
A configurable perception DSL was considered and rejected: it would be a language nobody can
verify, standing in front of chemistry that is short enough to read.

Units: Angstrom throughout, inherited from `criteria.xyzgraph`.
"""

from .criteria import xyzgraph

#: Roles perceived from the COVALENT graph. Li is excluded from bonding by
#: `xyzgraph.bond_list(include_ionic=False)`, which matters: with Li at 1.85 A from the carbonyl
#: oxygen, counting the Li contact as a bond would give that O two neighbours and it would be
#: perceived as an ether oxygen. 🔴 The role of an atom must not depend on where the cation sits.
ROLE_DEFINITIONS = {
    "O_carbonyl": "oxygen with exactly one covalent neighbour, and that neighbour is carbon",
    "O_ether":    "oxygen with exactly two covalent neighbours, both carbon",
    "C_carbonyl": "carbon bonded to at least one O_carbonyl",
    "C_sp3":      "carbon bearing at least one hydrogen and not a C_carbonyl",
    "C_alkyl":    "alias of C_sp3, kept because the spec says 'the alkyl C-O'",
    "Li":         "the lithium centre",
    "H":          "hydrogen",
}

#: 🔒 `C_alkyl` and `C_sp3` are the SAME role under two names because the specification uses both
#: words for one thing ("ring-opening via the ALKYL C-O", "break O(ether)-C(sp3)"). Resolving them
#: to one set here is cheaper than hoping every future writer picks the same word.
ROLE_ALIASES = {"C_alkyl": "C_sp3", "O_ester": "O_ether", "C_carbonyl_C": "C_carbonyl"}


def canonical_role(role):
    return ROLE_ALIASES.get(role, role)


def perceive(atoms, tolerance=xyzgraph.BOND_TOLERANCE):
    """`atoms` -> {role: [atom indices]}. Deterministic, sorted.

    Returns only roles that matched at least one atom, so a caller asking for a role that is not
    present gets a KeyError-free, explicit "0 candidates" from `resolve_bond` rather than a
    silently empty selection.
    """
    bonds = xyzgraph.bond_list(atoms, tolerance=tolerance, include_ionic=False)
    adj = xyzgraph.adjacency(len(atoms), bonds)
    sym = [a[0] for a in atoms]

    def neigh_syms(i):
        return sorted(sym[j] for j in adj[i])

    roles = {}

    def add(role, idx):
        roles.setdefault(role, []).append(idx)

    o_carbonyl = set()
    for i, s in enumerate(sym):
        if s != "O":
            continue
        ns = neigh_syms(i)
        if len(ns) == 1 and ns[0] == "C":
            o_carbonyl.add(i)
            add("O_carbonyl", i)
        elif len(ns) == 2 and ns == ["C", "C"]:
            add("O_ether", i)

    for i, s in enumerate(sym):
        if s == "Li":
            add("Li", i)
        elif s == "H":
            add("H", i)
        elif s == "C":
            if any(j in o_carbonyl for j in adj[i]):
                add("C_carbonyl", i)
            elif any(sym[j] == "H" for j in adj[i]):
                add("C_sp3", i)

    for role in roles:
        roles[role].sort()
    return roles


def resolve_bond(atoms, role_a, role_b, tolerance=xyzgraph.BOND_TOLERANCE):
    """Find the bond between an atom of `role_a` and an atom of `role_b`.

    Returns a mapping dict. 🔴 `selected` is None when there are zero candidates -- the deck
    cannot be built and the caller must not guess. `ambiguous` is True whenever more than one
    candidate existed, EVEN IF they are symmetry-equivalent, because the resolver cannot prove
    equivalence and a claim it cannot prove is exactly what this project keeps paying for.
    """
    role_a, role_b = canonical_role(role_a), canonical_role(role_b)
    roles = perceive(atoms, tolerance=tolerance)
    bonds = xyzgraph.bond_list(atoms, tolerance=tolerance, include_ionic=False)
    a_set, b_set = set(roles.get(role_a) or []), set(roles.get(role_b) or [])

    candidates = []
    for i, j in bonds:
        if (i in a_set and j in b_set) or (j in a_set and i in b_set):
            first = i if i in a_set else j
            second = j if first == i else i
            candidates.append((first, second))
    candidates.sort()

    out = {
        "roles": [role_a, role_b],
        "candidates": candidates,
        "n_candidates": len(candidates),
        "selected": candidates[0] if candidates else None,
        "ambiguous": len(candidates) > 1,
        "tie_break": ("lowest atom index of the %s atom, then of its partner" % role_a
                      if len(candidates) > 1 else None),
        "role_counts": dict((r, len(v)) for r, v in sorted(roles.items())),
        "warnings": [],
    }
    if not candidates:
        out["warnings"].append(
            "🔴 role_pair_unresolved: no bond between a %s and a %s exists in this geometry "
            "(role counts %s). The deck CANNOT be built -- do not substitute a nearby bond."
            % (role_a, role_b, out["role_counts"]))
    elif out["ambiguous"]:
        out["warnings"].append(
            "🔴 role_pair_ambiguous: %d bonds match (%s -- %s): %s. One was chosen by index order "
            "and the full candidate list is recorded. If these are NOT symmetry-equivalent the "
            "choice picks the reaction coordinate, and Omega will be scored against it."
            % (len(candidates), role_a, role_b, candidates))
    return out


def mapping_for(atoms, break_pairs=(), form_pairs=(), tolerance=xyzgraph.BOND_TOLERANCE):
    """The full role->index mapping that ships beside a deck.

    `break_pairs` / `form_pairs` are lists of two-role lists, exactly as `b0_reactions.json`
    states them. The returned dict is what Omega is computed against.
    """
    roles = perceive(atoms, tolerance=tolerance)
    out = {
        "n_atoms": len(atoms),
        "roles": roles,
        "role_definitions": dict(ROLE_DEFINITIONS),
        "break": [resolve_bond(atoms, a, b, tolerance) for a, b in break_pairs],
        "form": [resolve_bond(atoms, a, b, tolerance) for a, b in form_pairs],
        "bond_tolerance": tolerance,
        "ionic_contacts_excluded": True,
        "_ionic_note": ("perceived on the COVALENT graph only. With Li at ~1.85 A from the "
                        "carbonyl O, counting that contact as a bond would make the carbonyl "
                        "oxygen look like an ether oxygen."),
        "warnings": [],
        "resolved": True,
    }
    for entry in out["break"] + out["form"]:
        out["warnings"].extend(entry["warnings"])
        if entry["selected"] is None:
            out["resolved"] = False
    return out


class MappingRequiredError(RuntimeError):
    """Raised when a deck would be emitted or scored without its role->index mapping."""


def require_mapping(mapping):
    """🔴 A deck without its mapping cannot be scored. Raise, do not warn.

    Lead's ruling, and it is the C-8 pattern again: a returned flag is a thing a caller may
    decline to read, and Omega computed against the wrong pair of atoms is a number that looks
    exactly like a right one.
    """
    if not mapping:
        raise MappingRequiredError(
            "no role->index mapping was supplied. A deck without its mapping cannot be scored: "
            "Omega is defined as the projection of the imaginary mode onto the bonds the EDGE "
            "says should change, and without the mapping there is no such set of bonds.")
    if not mapping.get("resolved"):
        raise MappingRequiredError(
            "the role->index mapping did not resolve every requested bond: %s"
            % "; ".join(mapping.get("warnings") or ["unknown reason"]))
    return mapping
