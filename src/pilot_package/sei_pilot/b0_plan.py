"""B0's item list and sizing.

🔴 RESERVATION AND EXPECTED CONSUMPTION ARE TWO SEPARATE NUMBERS AND ARE NEVER ONE.
```
    reserved   cores x wall x links, the PHYSICAL CEILING the scheduler must admit    (guard binds)
    expected   what we think we will actually spend                                   (planning)
```
The distinction is §R24.1's and it matters twice over here:
  * the MTD stage is sized against its `max_time_ps` CAP, because with a discovery-rate stopping
    rule the per-species wall time is not a constant and a forecast would be a fabrication;
  * so if the headline became the ceiling, B0 would look 3-4x more expensive than it is and the
    margin decision would be made on the wrong figure.

🔴 UNITS, AND THEY DIFFER BETWEEN THE TWO AUDIENCES.
```
    the user's approval, and every document figure   REFERENCE core-h
    this ledger and the scheduler                    KNL core-h   ( = reference x kappa, 2.4 )
```
Both are reported for every total. `budget.reference_to_local_core_hours` is the only conversion.

🔴 IF THE CEILING-SIZED RESERVATION EXCEEDS THE GUARD, DO NOT RAISE THE GUARD.
   §R24.1: suspect the specification first. `check_against_guard` reports the breach and names the
   available fixes as the LEAD's to choose (lower `max_time_ps`, drop an arm, or go back to the
   user) -- it does not pick one, and it does not adjust anything.

🔒 The guard is read from `budget.b0_guard_spec()`, never from a number in a document -- including
   one in a message. That is the instruction and it is also the only way the two cannot drift.
"""

from . import arm2, b0_species, budget, config

#: Stage ids. One spelling, used in the item list and in the accounting.
STAGE_MTD = "mtd"
STAGE_PREOPT = "preopt"
STAGE_DFT_CHEAP = "dft_cheap_optfreq"
STAGE_DFT_HIGH = "dft_high_optfreq"
STAGE_TS = "ts_attempt"
STAGE_EPS = "epsilon_sp"


def _conf(cfg=None):
    return cfg if cfg is not None else config.load("b0_conformers.json")


def mtd_ceiling_wall_h(cfg=None):
    """The MTD stage's CEILING, from the stopping rule's cap. Not a forecast.

    🔴 `max_time_ps` is a physical bound on the run, not an estimate of it. The discovery-rate
       rule normally stops earlier; how much earlier is what B0-D's first species measures.
    """
    sr = _conf(cfg)["metadynamics"]["_stopping_rule"]
    return {"cap_ps": sr["max_time_ps"],
            "threshold": sr["discovery_rate_threshold"],
            "rule": sr["rule"],
            "_is_a_ceiling_not_a_forecast": (
                "sized against the cap because a discovery-rate stopping rule has no constant "
                "wall time. §R24.1's ceiling/consumption distinction.")}


def cap_binding_report(per_species_stops):
    """How often the 20 ps cap TERMINATED a run instead of the discovery-rate rule.

    🔴 If the cap fires often the stopping rule is mis-tuned, and 🔒 **a truncation that is not
       reported looks exactly like convergence**. This is wired to the same records the sizing
       uses, so the two cannot disagree.

    `per_species_stops` = [{"species_id", "stopped_by": "discovery_rate"|"cap", "time_ps"}].
    """
    stops = list(per_species_stops or [])
    by_cap = [s for s in stops if s.get("stopped_by") == "cap"]
    by_rule = [s for s in stops if s.get("stopped_by") == "discovery_rate"]
    unknown = [s for s in stops if s.get("stopped_by") not in ("cap", "discovery_rate")]
    n = len(stops)
    out = {
        "n_species": n,
        "n_stopped_by_cap": len(by_cap),
        "n_stopped_by_discovery_rate": len(by_rule),
        "n_stopped_by_unknown": len(unknown),
        "species_stopped_by_cap": [s.get("species_id") for s in by_cap],
        "cap_binding_fraction": (None if not n else len(by_cap) / float(n)),
        "warnings": [],
        "_why_it_matters": (
            "🔴 the cap is a SAFETY BOUND, not the intended stopping condition. If it terminates "
            "most species the discovery-rate rule is mis-tuned, and a truncated search looks "
            "exactly like a converged one in the output."),
    }
    if by_cap:
        out["warnings"].append(
            "🔴 mtd_cap_bound: the %d ps cap terminated %d of %d species (%s). Those searches were "
            "TRUNCATED, not converged, and their conformer ensembles are lower bounds on what a "
            "longer run would have found."
            % (mtd_ceiling_wall_h()["cap_ps"], len(by_cap), n,
               ", ".join(str(s.get("species_id")) for s in by_cap)))
    if unknown:
        out["warnings"].append(
            "🔴 mtd_stop_reason_unknown for %d species (%s). A run whose stopping reason was not "
            "recorded cannot be told from a truncated one."
            % (len(unknown), ", ".join(str(s.get("species_id")) for s in unknown)))
    return out


def items(cfg=None):
    """The B0 item list. Counts are DERIVED from the definitions, never typed."""
    species = b0_species.all_species()
    arm2_scope = arm2.build_all(species)
    reactions = config.load("b0_reactions.json")
    methods = reactions["methods"]
    eps = reactions["epsilon_scan"]

    n_species = len(species)
    n_arm2 = arm2_scope["n_species"]
    n_ts = len(reactions["reactions"]) * len(methods)
    n_eps = (len(reactions["reactions"]) * len(eps["states"])
             * len(eps["epsilon_values"]))

    return [
        {"stage": STAGE_PREOPT, "arm": 1, "n_tasks": n_species,
         "note": "GFN2 pre-optimisation before the MTD. Arm 1 only."},
        {"stage": STAGE_MTD, "arm": 1, "n_tasks": n_species,
         "note": "xtb metadynamics, sized at the %s ps cap (a CEILING, not a forecast)"
                 % mtd_ceiling_wall_h(cfg)["cap_ps"]},
        {"stage": STAGE_DFT_CHEAP, "arm": 1, "n_tasks": n_species,
         "note": "composite-level opt+freq on the promoted conformer window"},
        {"stage": STAGE_DFT_CHEAP, "arm": 2, "n_tasks": n_arm2,
         "note": "THE CONTROL: the 3 shipped idealised geometries only (ruling (a)). "
                 "The other %d species are arm-1-only and that is not missing data."
                 % arm2_scope["n_arm1_only"]},
        {"stage": STAGE_DFT_HIGH, "arm": 3, "n_tasks": n_species,
         "note": "r_high, from ARM 1's conformer. Emits the FREQUENCY LIST, not just the energy "
                 "(restores the cross-basis comparison U-60 lost)."},
        {"stage": STAGE_TS, "arm": None, "n_tasks": n_ts,
         "note": "%d reactions x %d methods, AT COMPOSITE (C-11)"
                 % (len(reactions["reactions"]), len(methods))},
        {"stage": STAGE_EPS, "arm": None, "n_tasks": n_eps,
         "note": "epsilon scan on ALREADY-COMPUTED geometries. Adds zero new geometry work."},
    ]


def size(unit_core_hours, cfg=None):
    """Totals from a per-stage unit cost. Returns RESERVED and EXPECTED as separate numbers.

    `unit_core_hours` = {stage: {"reserved": float, "expected": float}} in **KNL core-h per task**.
    🔴 A stage missing from the mapping is NOT assumed free -- it is reported as unpriced, and the
       totals are marked incomplete. An unpriced stage silently costed at zero is how a budget
       comes in over.
    """
    rows, unpriced = [], []
    total_res = total_exp = 0.0
    for item in items(cfg):
        u = (unit_core_hours or {}).get(item["stage"])
        if not u:
            if item["stage"] not in unpriced:
                unpriced.append(item["stage"])
            rows.append(dict(item, reserved_core_hours=None, expected_core_hours=None))
            continue
        res = float(u["reserved"]) * item["n_tasks"]
        exp = float(u["expected"]) * item["n_tasks"]
        total_res += res
        total_exp += exp
        rows.append(dict(item, reserved_core_hours=res, expected_core_hours=exp))

    out = {
        "rows": rows,
        "n_tasks_total": sum(i["n_tasks"] for i in items(cfg)),
        "complete": not unpriced,
        "_unit_costs_are_not_invented": (
            "🔴 THIS FUNCTION DOES NOT SUPPLY UNIT COSTS AND MUST NOT. They are MEASURED -- by "
            "B0's own first species for the MTD and DFT stages, and by engineer5 for the rest. "
            "An invented unit cost would make every total downstream a fabrication wearing a "
            "number's clothes, and the guard check would then certify it."),
        "unpriced_stages": unpriced,
        "reserved_core_hours_knl": total_res if not unpriced else None,
        "expected_core_hours_knl": total_exp if not unpriced else None,
        "reserved_core_hours_reference": (
            None if unpriced else budget.local_to_reference_core_hours(total_res)),
        "expected_core_hours_reference": (
            None if unpriced else budget.local_to_reference_core_hours(total_exp)),
        "kappa": budget.KAPPA_PHYSICAL,
        "warnings": [],
        "_two_numbers": (
            "🔴 RESERVED is the physical ceiling the guard binds on; EXPECTED is what we think we "
            "will spend. They are never one number. If B0's headline became the ceiling the batch "
            "would look 3-4x more expensive than it is."),
    }
    if unpriced:
        out["warnings"].append(
            "🔴 sizing_incomplete: stage(s) %s have no unit cost, so BOTH totals are null rather "
            "than a partial sum. A partial total reads as a total." % ", ".join(unpriced))
    return out


def check_against_guard(sizing):
    """Does the CEILING-sized reservation fit under the B0 guard?

    🔴 Reads `budget.b0_guard_spec()`, never a number from a document. If it does not fit, this
       REPORTS and NAMES THE FIXES AS THE LEAD'S -- it does not adjust anything, and §R24.1 says
       the guard is never raised to fit.
    """
    spec = budget.b0_guard_spec()
    ceiling = spec["max_core_hours"]
    reserved = sizing.get("reserved_core_hours_knl")
    out = {
        "guard_core_hours_knl": ceiling,
        "guard_reference_core_hours": spec["approved_reference_core_hours"],
        "guard_source": "budget.b0_guard_spec()",
        "reserved_core_hours_knl": reserved,
        "fits": None,
        "headroom_core_hours_knl": None,
        "headroom_reference_core_hours": None,
        "warnings": [],
        "_never_raise": (
            "🔴 §R24.1: if the reservation does not fit, the SPECIFICATION is suspected, not the "
            "guard. The available fixes -- lower max_time_ps, drop an arm, or return to the user "
            "-- are the lead's to choose. This function picks none of them."),
    }
    if reserved is None:
        out["warnings"].append(
            "🔴 guard_check_not_performed: the sizing is incomplete, so whether B0 fits is "
            "UNKNOWN. Not 'fits'.")
        return out
    out["fits"] = reserved <= ceiling
    out["headroom_core_hours_knl"] = ceiling - reserved
    out["headroom_reference_core_hours"] = budget.local_to_reference_core_hours(ceiling - reserved)
    if not out["fits"]:
        out["warnings"].append(
            "🔴 b0_exceeds_guard: ceiling-sized reservation %.0f KNL core-h (%.0f reference) "
            "against a guard of %.0f KNL (%.0f reference approved by the user). %s"
            % (reserved, budget.local_to_reference_core_hours(reserved), ceiling,
               spec["approved_reference_core_hours"], out["_never_raise"]))
    return out
