"""B0-D's species set, DERIVED from `config/b0_species.json`'s rules -- never typed out.

    CLOSED-SHELL stratum   Li+ Ln, n = 0..3, L in {EC, EMC, PF6-}, mixed ligands, order irrelevant
                           1 + 3 + 6 + 10 = 20 multisets, minus one exclusion = 19, all singlets
    OPEN-SHELL stratum     4 neutral doublets, ENUMERATED IN CONFIG rather than by rule
                           ------------------------------------------------------------
    TOTAL                  23

🔴 WHY THE OPEN-SHELL STRATUM EXISTS. The 19 are all closed-shell singlets, and HALF THE
   PRODUCTION POOL IS OPEN-SHELL -- every reduced species in S1/S2 is a radical. B0-D is supposed
   to answer "how expensive and how convergent is this class?", and open-shell SCF convergence is
   a distinct, well-known failure mode (spin contamination, symmetry-broken solutions, multiple
   SCF minima) that ADR-029 already writes `stable=opt` for. Sampling only the closed-shell half
   could not see the failure mode most likely to bite production.

🔴 AND THE TWO STRATA ARE NEVER POOLED. `u_cheap` is reported separately for each, because the
   DIFFERENCE between them is itself a measurement nothing else in the plan makes.

⚠ The open-shell members are LISTED in config, not generated. That is deliberate and is the one
   place a list is right: they are not a closed combinatorial family (they were chosen to double
   as B0-F's reactants), so a rule would be a rule invented to justify a list.

🔒 Why a rule and not a list: a typed list and the rule that generates it are two copies of one
truth, and every time this project has kept two copies one of them has gone stale. The count 19
and the exact id set are pinned by `tests/test_b0_species.py`, so the rule cannot drift silently
either.

🔴 The exclusion is DATA, with its reason attached. `Li(PF6)3(2-)` is out because it is very
likely not a bound species at this size, and a non-convergence caused by unboundedness is a
DIFFERENT failure from the one B0-D exists to measure. Recording the reason beside the rule is
what stops it being re-added later as an apparent oversight.
"""

import itertools

from . import config

CONFIG_NAME = "b0_species.json"


def spec(cfg=None):
    return cfg if cfg is not None else config.load(CONFIG_NAME)


def _composition_id(comp, centre="li"):
    """Deterministic id: `li` / `li_ec` / `li_ec2_emc` / `li_pf6_2` ..."""
    if not comp:
        return centre
    parts = [centre]
    for lig in sorted(comp):
        n = comp[lig]
        parts.append(lig.lower() if n == 1 else "%s%d" % (lig.lower(), n))
    return "_".join(parts)


def _charge_suffix(net):
    if net > 0:
        return "cation" if net == 1 else "cation%d" % net
    if net < 0:
        return "anion" if net == -1 else "anion%d" % (-net)
    return "neutral"


def enumerate_species(cfg=None):
    """The 19 CLOSED-SHELL species. Deterministic, sorted by (n_ligands, id).

    🔴 This is one STRATUM, not the batch. Use `all_species()` for what B0-D actually runs.

    Each entry carries everything a deck builder needs and nothing it has to infer:
    charge and multiplicity are COMPUTED from the ligand composition, not typed, so a new ligand
    cannot silently inherit the wrong charge.
    """
    cfg = spec(cfg)
    ligands = cfg["ligands"]
    centre = cfg["centre"]
    excluded = dict((_frozen(e["composition"]), e) for e in cfg.get("exclusions") or [])

    out = []
    names = sorted(ligands)
    for n in cfg["n_ligands"]:
        for combo in itertools.combinations_with_replacement(names, n):
            comp = {}
            for lig in combo:
                comp[lig] = comp.get(lig, 0) + 1
            key = _frozen(comp)
            if key in excluded:
                continue
            net = centre["charge"] + sum(ligands[l]["charge"] * k for l, k in comp.items())
            sid = _composition_id(comp, centre["element"].lower())
            entry = {
                "id": "%s_%s" % (sid, _charge_suffix(net)) if n else "li_cation",
                "centre": centre["element"],
                "composition": comp,
                "n_ligands": n,
                "charge": net,
                "multiplicity": cfg["multiplicity"],
                "n_atoms": None,
            }
            entry["stratum"] = "closed_shell"
            entry.update(bound_check_fields(entry, cfg))
            out.append(entry)
    out.sort(key=lambda e: (e["n_ligands"], e["id"]))
    return out


def open_shell_species(cfg=None):
    """The 4 neutral doublets. Listed in config; see the module docstring for why."""
    cfg = spec(cfg)
    block = cfg.get("open_shell_stratum") or {}
    out = []
    for m in block.get("members") or []:
        comp = dict(m.get("composition") or {})
        entry = {
            "id": m["id"],
            "centre": cfg["centre"]["element"],
            "composition": comp,
            "n_ligands": sum(comp.values()),
            "charge": block["charge"],
            "multiplicity": block["multiplicity"],
            "n_atoms": m.get("n_atoms"),
            "stratum": "open_shell",
            "note": m.get("_note"),
        }
        entry.update(bound_check_fields(entry, cfg))
        out.append(entry)
    return out


def all_species(cfg=None):
    """🔴 WHAT B0-D ACTUALLY RUNS: both strata, tagged. 23 species."""
    return enumerate_species(cfg) + open_shell_species(cfg)


def by_stratum(cfg=None):
    """Grouped, because `u_cheap` must be reported per stratum and NEVER pooled."""
    out = {}
    for s in all_species(cfg):
        out.setdefault(s["stratum"], []).append(s)
    return out


def _frozen(comp):
    return tuple(sorted((k, int(v)) for k, v in (comp or {}).items()))


def bound_check_fields(entry, cfg=None):
    """Whether this species needs the bound-species diagnostic, and what it is.

    🔴 `applies_to: net_charge < 0` is a CODER EXTENSION of a ruling that named one species; it is
    declared in the config with that label, not hidden here. Reading the HOMO is free (it is
    already in the log) so applying it to every anion costs nothing and cannot be forgotten for
    one member.
    """
    cfg = spec(cfg)
    rule = cfg["bound_species_rule"]
    # 🟢 BROADENED BY RULING: EVERY species, not `charge < 0`.
    #    `charge < 0` was a PROXY; the property wanted is "is the highest occupied orbital BOUND?".
    # 🔴 The classic unbound case in OUR chemistry is a RADICAL ANION -- gas-phase EC has a
    #    NEGATIVE adiabatic electron affinity (why ADR-029 insists on diffuse functions) -- so the
    #    open-shell stratum's NEUTRAL doublets are exactly where SOMO boundness is the live
    #    question, and `charge < 0` would have skipped every one of them.
    #    Reading it is free: it is in every log.
    required = (rule.get("applies_to") == "every species") or entry["charge"] < 0
    return {
        "bound_check_required": required,
        "bound_diagnostic": rule["diagnostic"] if required else None,
        "bound_check_rule": rule["unbound_when"] if required else None,
    }


def excluded_species(cfg=None):
    """The exclusions, WITH their reasons. Never return the bare list."""
    return list(spec(cfg).get("exclusions") or [])


def summary(cfg=None):
    sp = all_species(cfg)
    return {
        "n_species": len(sp),
        "n_closed_shell": len(enumerate_species(cfg)),
        "n_open_shell": len(open_shell_species(cfg)),
        "_strata_note": ("🔴 u_cheap is reported PER STRATUM and never pooled. The difference "
                         "between them is itself a measurement -- 'does open-shell cost more and "
                         "converge worse?' -- and nothing else in the plan makes it."),
        "n_excluded": len(excluded_species(cfg)),
        "by_n_ligands": dict((n, sum(1 for s in sp if s["n_ligands"] == n))
                             for n in sorted(set(s["n_ligands"] for s in sp))),
        "by_charge": dict((c, sum(1 for s in sp if s["charge"] == c))
                          for c in sorted(set(s["charge"] for s in sp))),
        "by_multiplicity": dict((m, sum(1 for s in sp if s["multiplicity"] == m))
                                for m in sorted(set(s["multiplicity"] for s in sp))),
        "bound_check_required": [s["id"] for s in sp if s["bound_check_required"]],
        "excluded": [{"id": e["id"], "reason": e["reason"]}
                     for e in excluded_species(cfg)],
        "source": "config/b0_species.json (rules) -> sei_pilot/b0_species.py (derivation)",
    }
