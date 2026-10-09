"""B0-D arm 2 — THE NULL CONTROL. Idealised, unoptimised geometries, on purpose.

    arm 1  properly generated conformers (xtb metadynamics)   "what does this class cost?"
    arm 2  THE SAME SPECIES from IDEALISED geometries          "how much of that was the guess?"
    arm1-best ⊖ arm2  IS THE MEASUREMENT. Arm 2 is not redundant and must not be dropped.

🔴 ARM 2 NEVER GETS THE PRE-OPTIMISATION. Arm 1 pre-optimises at GFN2 before its metadynamics
   (it removes a 702 K -> 484 K starting transient and is better practice anyway). Applying that
   to arm 2 would destroy the only thing arm 2 measures. `assert_no_preoptimisation` exists so
   that cannot happen by accident.

🔒 THE CONTROL MUST BE THE SAME PROCEDURE, NOT AN IMITATION OF IT. This module therefore imports
   `tools/make_p5_species.py` -- the actual generator that produced RT-1's contaminated inputs --
   and uses ITS ligand coordinate blocks and ITS helpers. Nothing is retyped.

🔴 BUT THE GENERATOR CONTAINS ONLY TWO LI COMPLEXES, AND THEY WERE HAND-PLACED DIFFERENTLY.
   Measured on the shipped files:
```
     li_ec_cation / li_ec_radical   d(O_carbonyl-Li) = 1.850 A   angle Li-O=C = 180.0 deg
     li_ec2_cation                  d(O_carbonyl-Li) = 2.100 A   angle Li-O=C =  90.3 deg
     experimental                                                            ~= 138 deg
```
   There is NO general placement rule in the source to reuse -- the two complexes disagree with
   each other and are wrong in OPPOSITE DIRECTIONS from experiment. So arm 2 splits in two, and
   the split is reported per species rather than hidden:

```
     PROVENANCE "shipped"   the artefact itself, byte-for-byte. The genuine control.
     PROVENANCE "extended"  built here by a DECLARED naive rule, because no idealised geometry
                            for that species exists anywhere. 🔴 A weaker control: it measures
                            "a naive guess" rather than "the naive guess RT-1 actually made."
```
🔒 RULING (lead, 2026-08-19): **ARM 2 RUNS THE 3 SHIPPED SPECIES ONLY.** The other 20 are
   reported as arm-1-only. The reason is not sample size -- it is that the two groups answer
   DIFFERENT QUESTIONS:
```
     shipped  (3)   RETROSPECTIVE  "was RT-1's 283 core-h an artefact of the input we used?"
                    n=3 is not a small sample, it is the ENTIRE POPULATION of that question:
                    those three files are the only bad starts we ever paid for.
     extended (20)  PROSPECTIVE    "does pre-optimisation pay for itself against OUR builder?"
                    🔴 Unanswerable here: the geometries come from a builder we have no intention
                    of shipping, so arm1 - arm2 would vary because MY RULE varied, species by
                    species, and be reported in a column headed "cost of a naive start".
```
   🔴 And the decisive fact: **ADR-077 took arm 2's main job away.** U-55 is now decided by
   `curvature.u55_panel`, correlating nu_min / n_soft / condition number against ARM 1's own
   measured opt cycles and core-h. That panel needs 23 species of arm 1 and ZERO of arm 2.
   ⟹ arm 2's only remaining job is the retrospective question, and 3 species answer it completely.

⚠ What this knowingly costs: no naive-start data on any open-shell species. The naive-start
   penalty is a GEOMETRY effect, not a spin effect, and buying open-shell coverage with an
   arbitrary rule would buy a number nobody could interpret.

🔒 THE EXTENDED PATH STAYS IN THE TREE, UNWIRED AND TESTED. If B1 later needs a prospective
   naive-start measurement it will need a declared, documented, CONSISTENT builder -- and the time
   to write that is when it is the deliverable, not as a side effect of a control.
"""

import importlib.util
import os

_GEN_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                         "tools", "make_p5_species.py")

#: Where a genuine idealised geometry already exists.
IDEALISED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "inputs", "p5_species")

PROV_SHIPPED = "shipped"
PROV_EXTENDED = "extended"

#: 🔴 DECLARED NAIVE RULE for the `extended` species, and it is deliberately naive -- a control
#: built with care is not a control. Ligands are stacked along z at the generator's own 4.2 A
#: spacing (`species()` uses `translate(EC, 0, 0, 4.2)`), and Li is placed on the +y axis at the
#: z-centroid of the stack. 🔴 It does NOT reproduce either hand-placed complex, because those two
#: do not reproduce each other; `_rule_disagrees_with_shipped` records that rather than papering
#: over it.
STACK_SPACING_ANG = 4.2
LI_OFFSET_Y_ANG = 4.24     # the generator's own value for the n=1 case (`li_at(0.0, 4.24, 0.0)`)


def _generator():
    """Import the ACTUAL generator by path. `tools/` is not a package."""
    spec = importlib.util.spec_from_file_location("_sei_make_p5_species", _GEN_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def ligand_blocks():
    """The generator's OWN coordinate blocks. Not retyped, not adapted."""
    g = _generator()
    return {"EC": [tuple(a) for a in g.EC],
            "EMC": [tuple(a) for a in g.EMC],
            "PF6": [tuple(a) for a in g.PF6]}


def shipped_path(species_id):
    p = os.path.join(IDEALISED_DIR, species_id + ".xyz")
    return p if os.path.isfile(p) else None


def build(species, ligands=None):
    """An arm-2 starting geometry for one species record (from `b0_species`).

    Returns `(atoms, provenance)`. `provenance['source']` is `shipped` or `extended`, and the
    caller MUST carry it -- the two are not equally strong controls.
    """
    sid = species["id"]
    path = shipped_path(sid)
    if path:
        g = _generator()
        with open(path) as fh:
            text = fh.read()
        atoms = _read_xyz(text)
        return atoms, {
            "source": PROV_SHIPPED,
            "path": os.path.relpath(path, os.path.dirname(IDEALISED_DIR)),
            "header": text.splitlines()[1] if len(text.splitlines()) > 1 else "",
            "generator": "tools/make_p5_species.py",
            "is_the_artefact_itself": True,
            "note": ("🟢 the genuine control: the file RT-1 actually used, byte-for-byte. "
                     "Claims about 'how much of the cost was the guess' are strongest here."),
            "_generator_loaded": bool(g),
        }

    ligands = ligands or ligand_blocks()
    g = _generator()
    comp = species["composition"]
    stack, k = [], 0
    for name in sorted(comp):
        for _ in range(comp[name]):
            stack.extend(g.translate(ligands[name], 0.0, 0.0, STACK_SPACING_ANG * k))
            k += 1
    z_centroid = STACK_SPACING_ANG * (k - 1) / 2.0 if k else 0.0
    atoms = stack + g.li_at(0.0, LI_OFFSET_Y_ANG, z_centroid)
    return atoms, {
        "source": PROV_EXTENDED,
        "path": None,
        "generator": "sei_pilot/arm2.py, using tools/make_p5_species.py's ligand blocks",
        "is_the_artefact_itself": False,
        "rule": ("ligands stacked along z at %.1f A (the generator's own spacing); Li on the +y "
                 "axis at the stack's z-centroid, at the generator's own %.2f A offset"
                 % (STACK_SPACING_ANG, LI_OFFSET_Y_ANG)),
        "note": ("🔴 A WEAKER CONTROL. No idealised geometry for this species exists anywhere, so "
                 "this measures 'a naive guess' rather than 'the naive guess RT-1 actually made'. "
                 "🔴 And the two hand-placed complexes in the generator DISAGREE WITH EACH OTHER "
                 "(angle Li-O=C = 180.0 deg vs 90.3 deg, both wrong against an experimental "
                 "~138 deg), so there was no consistent rule available to reproduce."),
        # 🔴 The generator's OWN safety check (`main()` refuses anything below 0.9 A). Reused
        #    rather than reinvented, and `None` for a single atom -- a "closest pair" among one
        #    atom is not 1e9, it is undefined.
        "min_interatomic_distance_ang": (None if len(atoms) < 2
                                         else round(g.min_distance(atoms), 3)),
        "overlap_threshold_ang": 0.9,
        "_overlap_note": ("the generator refuses a structure with any pair below 0.9 A; the same "
                          "threshold is applied here, from the same source"),
    }


def _read_xyz(text):
    lines = text.splitlines()
    n = int(lines[0].split()[0])
    out = []
    for line in lines[2:2 + n]:
        f = line.split()
        if f:
            out.append((f[0], float(f[1]), float(f[2]), float(f[3])))
    return out


def to_xyz(atoms, species, provenance):
    """Write with the generator's OWN formatter and the same self-declaring header.

    🔒 The header keeps saying `idealized, NOT optimized`. That line is what let ADR-066 diagnose
    P1 at zero cost, and arm 2's whole point is to be that structure.
    """
    g = _generator()
    return g.to_xyz(atoms, "%s | charge=%d mult=%d | ARM 2 CONTROL (%s) | idealized, NOT optimized"
                    % (species["id"], species["charge"], species["multiplicity"],
                       provenance["source"]))


class PreoptimisationForbidden(RuntimeError):
    """Raised if arm 2 is handed the pre-optimisation that belongs to arm 1."""


def assert_no_preoptimisation(options):
    """🔴 Arm 2 keeps its idealised start or it stops being a control. Raise, do not warn."""
    if (options or {}).get("pre_optimise"):
        raise PreoptimisationForbidden(
            "arm 2 was given pre_optimise=True. Arm 2 is the NULL CONTROL: its whole content is "
            "that it starts from an unoptimised idealised guess. Pre-optimising it makes "
            "arm1 - arm2 a comparison of two relaxed structures and deletes the measurement.")
    return True


def build_all(species_list, shipped_only=True):
    """Arm-2 geometries. 🔒 `shipped_only=True` IS THE RULING -- the 3 genuine artefacts only.

    `shipped_only=False` reaches the extended builder. It is kept reachable and tested, but
    NOTHING IN B0 CALLS IT: see the module docstring for why a prospective naive-start
    measurement needs its own declared builder rather than a control's side effect.
    """
    records, skipped = [], []
    for sp in species_list:
        if shipped_only and not shipped_path(sp["id"]):
            skipped.append(sp["id"])
            continue
        atoms, prov = build(sp)
        rec = {"species_id": sp["id"], "n_atoms": len(atoms),
               "atoms": atoms, "provenance": prov}
        if prov["source"] == PROV_SHIPPED:
            rec["idealised_geometry"] = measure_idealised(atoms)
        records.append(rec)
    n_shipped = sum(1 for r in records if r["provenance"]["source"] == PROV_SHIPPED)
    out = {
        "records": records,
        "shipped_only": shipped_only,
        "n_species": len(records),
        "n_shipped": n_shipped,
        "n_extended": len(records) - n_shipped,
        "arm1_only_species": skipped,
        "n_arm1_only": len(skipped),
        "question_answered": ("RETROSPECTIVE: was RT-1's cost an artefact of the input we "
                              "actually used? n=%d is the ENTIRE POPULATION of that question."
                              % n_shipped),
        "u55_is_not_answered_here": ("🔴 U-55 is decided by curvature.u55_panel against ARM 1's "
                                     "own opt cycles and core-h (ADR-077). Arm 2 contributes "
                                     "nothing to it and its species count is not a limitation "
                                     "on it."),
        "warnings": [],
    }
    if skipped:
        out["warnings"].append(
            "🟢 arm2_scope_is_the_ruling: %d species run ARM 1 ONLY and have no arm-2 control, by "
            "ruling. They are NOT missing data -- the retrospective question they would answer "
            "does not exist for them (no bad start was ever paid for). %s"
            % (len(skipped), out["u55_is_not_answered_here"]))
    if not shipped_only:
        out["warnings"].append(
            "🔴 arm2_extended_path_used: `shipped_only=False` reached the extended builder. "
            "Nothing in B0 should do this -- those geometries come from a rule written as a "
            "control's side effect, and arm1 - arm2 on them measures that rule, not the guess "
            "RT-1 made.")
    return out


#: Experimental reference for the Li-O=C angle. [LITERATURE, approximate -- quoted in the spec's
#: own discussion of the idealised geometries.] Recorded so the measured values below have
#: something to be wrong against, and flagged as approximate rather than presented as a datum.
EXPERIMENTAL_LI_O_C_ANGLE_DEG = 138.0


def measure_idealised(atoms):
    """The measured pathology of an idealised complex, carried WITH the data.

    🔴 Recorded because it was not written down. Only `li_ec2_cation`'s 90.3 deg reached
       §39.1(e-bis); `li_ec_cation` and `li_ec_radical` sit at 180.0 deg -- wrong in the OPPOSITE
       direction from experiment -- and P1's endpoints ran on that undocumented geometry.

    🟢 And it STRENGTHENS ADR-067 rather than complicating it. ADR-067 diagnosed the 283 core-h as
       an over-symmetric start with symmetry-breaking gradients exactly zero. 180.0 deg is ALSO a
       symmetric placement -- Li collinear with the C=O axis is Li on a symmetry element, just a
       different one. Both shipped complexes are pathologically symmetric in two different ways,
       and neither was chosen: they were drawn.
    """
    import math

    from . import roles
    from .criteria import xyzgraph

    r = roles.perceive(atoms)
    out = {
        "li_o_c_angle_deg": None,
        "li_o_distance_ang": None,
        "experimental_angle_deg": EXPERIMENTAL_LI_O_C_ANGLE_DEG,
        "_experimental_label": "[LITERATURE, approximate]",
        "deviation_from_experiment_deg": None,
        "note": ("🔴 a symmetric placement in either direction: 90.3 deg and 180.0 deg both put Li "
                 "on a symmetry element. Neither was chosen -- they were drawn."),
    }
    if not r.get("Li") or not r.get("O_carbonyl"):
        return out
    li = r["Li"][0]
    bonds = xyzgraph.bond_list(atoms, include_ionic=False)
    angles, dists = [], []
    for oc in r["O_carbonyl"]:
        cs = [j for i, j in bonds if i == oc] + [i for i, j in bonds if j == oc]
        if not cs:
            continue
        c = cs[0]
        v1 = [atoms[li][t] - atoms[oc][t] for t in (1, 2, 3)]
        v2 = [atoms[c][t] - atoms[oc][t] for t in (1, 2, 3)]
        n1 = math.sqrt(sum(x * x for x in v1))
        n2 = math.sqrt(sum(x * x for x in v2))
        if n1 <= 0 or n2 <= 0:
            continue
        dot = sum(x * y for x, y in zip(v1, v2))
        angles.append(math.degrees(math.acos(max(-1.0, min(1.0, dot / (n1 * n2))))))
        dists.append(n1)
    if angles:
        # The Li-coordinating carbonyl oxygen is the nearest one.
        k = min(range(len(dists)), key=lambda i: dists[i])
        out["li_o_c_angle_deg"] = round(angles[k], 2)
        out["li_o_distance_ang"] = round(dists[k], 3)
        out["deviation_from_experiment_deg"] = round(
            angles[k] - EXPERIMENTAL_LI_O_C_ANGLE_DEG, 2)
    return out
