"""The BOUND-SPECIES rule for a cost/convergence probe.

🔒 THE RULE (lead relaying proposer5, 2026-08-19), generalised from the `Li(PF6)2(-)` instance:
   **A COST/CONVERGENCE PROBE MUST CONTAIN ONLY BOUND SPECIES.
     AN UNBOUND SPECIES MEASURES THE BASIS SET, NOT THE PROTOCOL.**

Why it needs code rather than a note. B0-D's product is a DISTRIBUTION -- the cost and the
convergence rate of the Li+Ln class. Three things can end a run without a result and they have
NOTHING in common downstream:

    converged == false      the protocol failed on a real species     -> in the convergence rate
    TRIPWIRE-ABORTED        the run hit the wall-time cap             -> spend yes, rate no (C-13)
    unbound                 there is no species there to converge to  -> NEITHER; it is a result
                                                                          ABOUT THE SPECIES

🔴 The third one is the new hazard and it is easy to get wrong in the direction that flatters us:
   an anion whose extra electron is not bound will fail to converge, or converge to a diffuse
   basis-set artefact, and counting that as a protocol failure would make the pool look harder
   than it is -- inflating every budget derived from B0-D. Counting it as a success is worse.
   ⟹ it is reported, and it is EXCLUDED FROM THE STATISTICS ON BOTH SIDES.

DIAGNOSTIC: the energy of the HIGHEST OCCUPIED ORBITAL -- HOMO for a closed shell, SOMO for an
open shell. A POSITIVE value means the electron sits in a discretised continuum state whose energy
is a property of the basis set, not of the molecule. Reading it is free -- it is in every log.

🔴 IT IS RUN ON EVERY SPECIES, NOT ONLY THE ANIONS. `charge < 0` was a PROXY for the property we
   actually want, and proposer5 rejected it: the classic unbound case in OUR chemistry is a
   RADICAL ANION, and gas-phase EC has a NEGATIVE adiabatic electron affinity (which is why
   ADR-029 insists on diffuse functions). The open-shell stratum's NEUTRAL doublets are exactly
   where SOMO boundness is the live question -- and `charge < 0` would have skipped every one.

🔴 FAILURE DIRECTION (Rule 18): `is_bound` is None when the HOMO was not read. Not True.
   An unread diagnostic must not certify a species as bound.

Units: the HOMO energy is in **Hartree** on the wire (that is what G16 prints). Converted through
`units` only for reporting; no threshold in this module depends on the conversion.
"""

from . import config, units

CONFIG_NAME = "b0_species.json"

#: Statuses this module can assign. `unbound` is deliberately NOT one of the convergence statuses.
STATUS_BOUND = "bound"
STATUS_UNBOUND = "unbound"
STATUS_NOT_CHECKED = "not_checked"


def rule(cfg=None):
    cfg = cfg if cfg is not None else config.load(CONFIG_NAME)
    return cfg["bound_species_rule"]


def classify(species, homo_energy_hartree=None, cfg=None):
    # `homo_energy_hartree` is the HIGHEST OCCUPIED orbital energy: HOMO (closed shell) or
    # SOMO (open shell). One argument, because it is one physical quantity.
    """Is this species bound? Returns a record for the reply.

    `species` needs `id`, `charge` and `bound_check_required` (as produced by
    `b0_species.enumerate_species`).
    """
    r = rule(cfg)
    required = bool(species.get("bound_check_required"))
    out = {
        "species_id": species.get("id"),
        "charge": species.get("charge"),
        "bound_check_required": required,
        "homo_energy_hartree": homo_energy_hartree,
        "homo_energy_ev": (None if homo_energy_hartree is None
                           else units.hartree_to_ev(homo_energy_hartree)),
        "criterion": r["unbound_when"],
        "is_bound": None,
        "status": STATUS_NOT_CHECKED,
        "counts_as_convergence_failure": False,
        "included_in_u_cheap_statistics": True,
        "warnings": [],
    }
    if not required:
        # Reachable only if the config's `applies_to` is narrowed back from "every species".
        # Kept so a narrowing stays a one-line config change rather than a code change.
        out["status"] = STATUS_NOT_CHECKED
        out["note"] = ("bound check not required by the current config rule (%r) for a species "
                       "of charge %s" % (r.get("applies_to"), species.get("charge")))
        return out

    if homo_energy_hartree is None:
        # 🔴 Required and not read. It must NOT sit in the statistics on an unread diagnostic.
        out["included_in_u_cheap_statistics"] = False
        out["warnings"].append(
            "🔴 bound_check_not_performed for %s: the check is REQUIRED and the highest-occupied "
            "orbital energy (HOMO/SOMO) was not read. The species is held OUT of the u_cheap "
            "statistics rather than assumed bound -- an unread diagnostic does not certify "
            "anything. 🔴 Reading it is FREE: it is in every log." % species.get("id"))
        return out

    bound = not (homo_energy_hartree > 0)
    out["is_bound"] = bound
    out["status"] = STATUS_BOUND if bound else STATUS_UNBOUND
    out["included_in_u_cheap_statistics"] = bound
    if not bound:
        out["warnings"].append(
            "🔴 unbound_species: %s has a highest-occupied orbital at %+.6f Ha (%+.3f eV) > 0, "
            "so the electron is not bound and the result measures the BASIS SET, not the "
            "protocol. This is a RESULT ABOUT THE SPECIES: it is reported, it is EXCLUDED from "
            "the u_cheap statistics, and 🔴 it is NOT counted as a convergence failure."
            % (species.get("id"), homo_energy_hartree,
               units.hartree_to_ev(homo_energy_hartree)))
    return out


def partition(records):
    """Split probe records into the three groups that must never be averaged together.

    `records` are dicts carrying `species_id`, `bound` (a `classify` result), `converged` and
    `status`. Returns the groups plus PER-STRATUM denominators, so a reader cannot compute a
    convergence rate over the wrong set by accident.

    🔴 ADR-087: this function used to ALSO return a pooled `convergence_rate` /
    `n_converged` / `convergence_denominator` at the top level, ten lines below a note
    saying the rate is "reported PER STRATUM and NEVER POOLED" -- the report refuted its
    own field. `_denominator_note` sat right beside the pooled field and explained a
    DIFFERENT axis (what is excluded), so the pooled number looked vetted when it was not
    (the adjacency pattern from `docs/05_STATE.md` §0-h).
    ⟹ The fix is NOT another caveat (one was already there and did not work). **There is no
    pooled convergence rate anywhere in this return value, under any name.** `per_stratum`
    is the ONLY place a rate is computed. This is a deliberate decision about what the top
    level exposes, not an oversight: a reader who wants a pooled figure must sum
    `per_stratum[*]["n_converged"]` and `per_stratum[*]["denominator"]` themselves --
    a deliberate act, not a field sitting at hand under an inviting name.
    """
    in_stats, unbound, unchecked, aborted = [], [], [], []
    for rec in records or []:
        b = rec.get("bound") or {}
        if rec.get("status") == "TRIPWIRE-ABORTED":
            aborted.append(rec)
        elif b.get("status") == STATUS_UNBOUND:
            unbound.append(rec)
        elif b.get("bound_check_required") and b.get("status") == STATUS_NOT_CHECKED:
            unchecked.append(rec)
        else:
            in_stats.append(rec)

    per_stratum = {}
    for rec in in_stats:
        st = rec.get("stratum") or "unspecified"
        g = per_stratum.setdefault(st, {"species": [], "n_converged": 0})
        g["species"].append(rec.get("species_id"))
        if rec.get("converged") is True:
            g["n_converged"] += 1
    for st, g in per_stratum.items():
        g["denominator"] = len(g["species"])
        g["convergence_rate"] = (None if not g["species"]
                                 else g["n_converged"] / float(len(g["species"])))

    return {
        "in_u_cheap_statistics": [r.get("species_id") for r in in_stats],
        "per_stratum": per_stratum,
        "_per_stratum_note": (
            "🔴 u_cheap and the convergence rate are reported PER STRATUM and NEVER POOLED. The "
            "19 closed-shell singlets and the 4 open-shell doublets are different populations, "
            "and open-shell SCF has its own failure modes (spin contamination, symmetry-broken "
            "solutions, multiple minima). 🟢 The DIFFERENCE between the strata is itself a "
            "measurement production needs and nothing else in the plan makes."),
        "excluded_unbound": [r.get("species_id") for r in unbound],
        "excluded_bound_check_not_performed": [r.get("species_id") for r in unchecked],
        "tripwire_aborted": [r.get("species_id") for r in aborted],
        # 🔴 ADR-087: NO pooled `convergence_rate` / `n_converged` / `convergence_denominator`
        # at this level, under any name -- see the docstring above. `per_stratum[*]` carries
        # its own `denominator` / `n_converged` / `convergence_rate`, each within ONE stratum.
        "_no_pooled_convergence_rate_here_note": (
            "🔴 ADR-087: a pooled rate used to live at this level (19 closed-shell + 4 "
            "open-shell averaged into one number) directly below a note promising it never "
            "would. It is GONE, not caveated -- read `per_stratum` instead. The denominator "
            "exclusions this section applies (unbound species and tripwire aborts are in "
            "NEITHER a numerator nor a denominator: an unbound species has nothing to "
            "converge to, and an abort measures difficulty, not convergence, C-13) still "
            "hold and are visible in `excluded_unbound` / `tripwire_aborted` above."),
        "_rate_is_none_when": "no species qualified in a stratum -- a rate over an empty set is not 0.0",
    }
