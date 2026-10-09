"""B0-D arm 1 — the conformer ensemble, from xtb metadynamics.

    MTD  ->  optimise every frame  ->  classify  ->  RMSD dedupe  ->  promote a GFN2 WINDOW to DFT

🔴 THE ROUTE IS `xtb --metadyn`, NOT ETKDG+MMFF. §37.2.3 option (ii), whose pre-registered
   activation condition ("only if the CREST binary does not run on KNL") is satisfied in the
   stronger form: CREST does not exist to be run. §37.2.3 also rules ETKDG+MMFF94 *undefined* for
   this class -- MMFF94 has no Li parameters and ETKDG generates conformers of one COVALENT
   molecular graph, while Li+Ln is a non-covalent complex.
   ⚠ R-4's meaning moved with the route. Every field this module emits says `xtb_metadyn`, and
     `ROUTE_ID` is the single spelling, so a write-up cannot drift back to "ETKDG".

🔴 THREE THINGS THAT ARE NOT NEGOTIABLE, each because the alternative deletes a measurement.

  1. DISSOCIATION IS COUNTED, NEVER DISCARDED. A non-covalent complex can come apart under MTD.
     The dissociation rate IS a direct measurement of how floppy the cluster is, which is B0-D's
     actual question -- discarding those frames deletes the answer and, worse, biases the survivors
     toward the rigid ones, which is the distribution we already believed.
  2. `arm1-best`, `arm1-ensemble` and `arm2` ARE THREE SEPARATE FIGURES.
         arm1-best     vs arm2        ->  "was the guess bad?"
         arm1-ensemble vs arm1-best   ->  "what does the conformer search buy?"   ( = R-4 )
     Same runs, no extra cost. Collapsing them loses R-4 entirely.
  3. THE WHOLE GFN2 WINDOW GOES TO DFT AND DFT RE-RANKS (§37.2.4-2). Taking the single lowest
     GFN2 conformer would let xTB set the ΔG ordering; §16.1-B2 forbids xTB deciding which
     SPECIES get DFT, and while choosing a conformer inside a species is not species selection,
     that only holds if the final ranking is DFT's.

🔴 FAILURE DIRECTION (Rule 18): every classification that could not be made is `None`, never a
   default. An unclassified frame is held out of the statistics rather than counted as intact.

Units: energies **Hartree** on the wire (xtb prints Hartree), compared in **eV** through `units`.
Lengths **Angstrom**. RMSD **Angstrom**.
"""

import math
import re

from . import config, linalg, units
from .criteria import xyzgraph

CONFIG_NAME = "b0_conformers.json"

#: 🔒 ONE spelling of the route, used in every emitted field name. The lead's instruction: R-4 now
#: retires "does the xtb-metadyn route work", NOT "does the ETKDG route work", and the field names
#: are what stops a write-up drifting back.
ROUTE_ID = "xtb_metadyn"

CLASS_INTACT = "intact"
CLASS_DISSOCIATED = "ligand_dissociated"
CLASS_FRAGMENTED = "ligand_fragmented"
CLASS_UNKNOWN = None

#: `energy: -20.574765099713 gnorm: 0.179165023803 xtb: 6.7.1 (edcfbbe)`
#: Verified against real output, not written from memory -- see tests/fixtures/PROVENANCE.md.
_ENERGY_RE = re.compile(r"energy:\s*(-?\d+\.\d+)")


def spec(cfg=None):
    return cfg if cfg is not None else config.load(CONFIG_NAME)


# =============================================================================================
# xcontrol input
# =============================================================================================

def metadyn_input(cfg=None):
    """The xcontrol deck for `xtb --metadyn --input <file>`, built from config.

    🔴 Every parameter comes from `config/b0_conformers.json`. None is written here, because a
    hyperparameter in code is a hyperparameter nobody reports, and §37.2.3's warning about
    re-implementing CREST badly is specifically about these numbers.
    """
    m = spec(cfg)["metadynamics"]
    return (
        "$md\n"
        "   time=%s\n"
        "   step=%s\n"
        "   temp=%s\n"
        "   dump=%s\n"
        "   shake=%d\n"
        "   hmass=%d\n"
        "$metadyn\n"
        "   save=%d\n"
        "   kpush=%s\n"
        "   alp=%s\n"
        "$end\n"
        % (m["md_time_ps"], m["md_step_fs"], m["md_temp_k"], m["md_dump_fs"],
           int(m["shake"]), int(m["hmass"]), int(m["save"]), m["kpush"], m["alp"]))


def metadyn_argv(xtb_path, start_xyz, charge, uhf, input_path, cfg=None):
    """The exact argv. Verified by running it; see tests/fixtures/PROVENANCE.md.

    `uhf` is the number of UNPAIRED ELECTRONS, not the multiplicity -- xtb's `--uhf` differs from
    Gaussian's multiplicity by one, and mixing them up is silent (it changes the electronic state
    without an error).
    """
    return [xtb_path, start_xyz, "--gfn", str(spec(cfg)["metadynamics"]["gfn"]),
            "--chrg", str(int(charge)), "--uhf", str(int(uhf)),
            "--metadyn", "--input", input_path]


def uhf_from_multiplicity(multiplicity):
    """xtb wants unpaired electrons; Gaussian wants 2S+1. Convert in ONE place."""
    if multiplicity is None or int(multiplicity) < 1:
        raise ValueError("multiplicity must be >= 1, got %r" % (multiplicity,))
    return int(multiplicity) - 1


# =============================================================================================
# run health -- judged on CONTENT, never on the banner
# =============================================================================================

#: 🔴🔴 MEASURED ON THE VENDORED BINARY, 2026-08-19: xtb 6.7.1 writes `normal termination of xtb`
#: to **STDERR**, never to stdout. Confirmed on three different invocations (`--version`,
#: `--opt`, `--metadyn`), all rc=0, all with the banner absent from stdout and present on stderr.
#: 🔴 Any code that captures the two streams SEPARATELY and looks for the banner in stdout will
#:    conclude that EVERY xtb run failed, including perfect ones -- and it will do so silently,
#:    because rc is 0 and the results are all there. A shell using `2>&1` never sees this.
#:    (The shipped `payload/P3.sh` uses `2>&1`, so it is not affected. The next person to write a
#:    Python runner with `capture_output=True` would have been.)
XTB_SUCCESS_BANNER = "normal termination of xtb"
XTB_BANNER_STREAM = "stderr"

#: Warnings xtb emits WHILE reporting success. Diagnostics, not verdicts.
XTB_SOFT_WARNINGS = ("thermostating problem", "Could not read topology file")


def xtb_health(stdout="", stderr="", returncode=None, frames=None):
    """Did this xtb run produce usable output? Judged on CONTENT.

    🔴 THE BANNER IS NOT THE CRITERION, in either direction:
      * absent from stdout means nothing -- it is written to stderr (see XTB_BANNER_STREAM)
      * present means little -- the real metadynamics run below printed `thermostating problem`
        with the temperature at 658 K against a requested 400 K and still terminated "normally"
      * and §0.2b-3 records the opposite case: xtb omits the banner entirely for periodic GFN-FF
        single points that produced perfectly good energies.
    ⟹ the criterion is "frames were produced and their energies are finite". The banner and the
      exit status are RECORDED as diagnostics.
    """
    combined = (stdout or "") + "\n" + (stderr or "")
    frames = frames or []
    n_energies = sum(1 for f in frames if f.get("energy_hartree") is not None)
    finite = all(_is_finite(f.get("energy_hartree")) for f in frames
                 if f.get("energy_hartree") is not None)
    usable = bool(frames) and n_energies > 0 and finite

    out = {
        "usable": usable,
        "criterion": "frames produced AND their energies parsed finite -- NOT the banner",
        "n_frames": len(frames),
        "n_energies_parsed": n_energies,
        "all_energies_finite": finite if n_energies else None,
        "returncode": returncode,
        "banner_seen": XTB_SUCCESS_BANNER in combined,
        "banner_stream_note": ("xtb 6.7.1 writes the success banner to %s; searching stdout "
                               "alone reports failure on every run" % XTB_BANNER_STREAM),
        "soft_warnings": [w for w in XTB_SOFT_WARNINGS if w in combined],
        "warnings": [],
    }
    if out["soft_warnings"]:
        out["warnings"].append(
            "🟡 xtb reported %s while terminating normally. Recorded, not treated as failure -- "
            "but a thermostat excursion changes the temperature the ensemble was sampled at, "
            "which is an input to every population this arm produces."
            % ", ".join(out["soft_warnings"]))
    if not usable:
        out["warnings"].append(
            "🔴 xtb_run_unusable: %d frame(s), %d energy(ies) parsed. 🔴 Before concluding the "
            "run failed, check that the caller is not looking for the success banner in stdout -- "
            "it is written to %s." % (len(frames), n_energies, XTB_BANNER_STREAM))
    return out


def _is_finite(x):
    return x is not None and x == x and abs(x) != float("inf")


# =============================================================================================
# temperature -- TWO fields, never one
# =============================================================================================

#: The MD table xtb prints:  `step  time(ps)  <Epot>  Ekin  <T>.  T.  Etot`
#: Verified against real output; `<T>` and `T` are printed with a TRAILING PERIOD.
_MD_ROW = re.compile(
    r"^\s*(\d+)\s+([\d.]+)\s+(-?[\d.]+)\s+([\d.]+)\s+([\d.]+)\.\s+([\d.]+)\.\s+(-?[\d.]+)\s*$")


def parse_temperature(md_stdout):
    """<T> and instantaneous T from an xtb MD/MTD log. Returns Kelvin.

    🔴 `temperature_requested` and `temperature_measured` are TWO FIELDS AND NEVER ONE.
       An MD engine does not deliver the temperature you asked for, and THE DIRECTION IS
       ENGINE-SPECIFIC: xtb metadynamics runs HOT (measured T_eff/T_set = 1.22-1.70 here),
       G16 ADMP is expected to run COLD (~0.5x, U-53, unmeasured). A single `temperature` field
       records the SETPOINT and nobody would ever know.
    🔴 T_eff IS NOT A CONSTANT and must not become a stored correction factor: it was measured at
       1.70 from an idealised start and 1.22-1.41 from an optimised one, same setpoint, same $md
       block. Measure it per run.
    """
    running, instant = [], []
    for line in (md_stdout or "").splitlines():
        m = _MD_ROW.match(line)
        if m and int(m.group(1)) > 0:
            running.append(float(m.group(5)))
            instant.append(float(m.group(6)))
    return {
        "n_rows": len(running),
        "running_mean_first_k": running[0] if running else None,
        "running_mean_final_k": running[-1] if running else None,
        "instantaneous_max_k": max(instant) if instant else None,
    }


def temperature_report(requested_k, md_stdout):
    """The two required fields, plus the ratio, plus what it does and does not license."""
    t = parse_temperature(md_stdout)
    measured = t["running_mean_final_k"]
    out = {
        "temperature_requested_k": requested_k,
        "temperature_measured_k": measured,
        "t_eff_over_t_set": (None if not (measured and requested_k) else measured / requested_k),
        "trace": t,
        "warnings": [],
        "_measured_is_required": ("🔴 two fields, never one. A single `temperature` records the "
                                  "setpoint. xtb MTD runs HOT; G16 ADMP is expected to run COLD; "
                                  "the direction is engine-specific and neither is assumable."),
    }
    if measured is None:
        out["warnings"].append(
            "🔴 temperature_not_measured: no MD table rows were parsed, so the temperature this "
            "trajectory was actually sampled at is UNKNOWN. Any population or rate taken from it "
            "is at an undefined temperature.")
    elif requested_k and abs(measured - requested_k) > 0.1 * requested_k:
        out["warnings"].append(
            "🟡 temperature_off_setpoint: requested %.0f K, measured %.0f K (x%.2f). 🔒 For a "
            "METADYNAMICS run this is EXPECTED, not a defect -- the bias potential does work on "
            "the system by construction. It was verified that the thermostat itself is correct: "
            "plain MD from the same optimised geometry holds 395 K against a 400 K setpoint. "
            "🔴 But a RATE counted on this trajectory is not a rate at a defined temperature."
            % (requested_k, measured, measured / requested_k))
    return out


# =============================================================================================
# trajectory parsing
# =============================================================================================

def parse_trajectory(text):
    """`xtb.trj` -> [{"index", "atoms", "energy_hartree", "energy_ev"}].

    Energies come from the frame comment line, so no extra single point is needed.
    🔴 A frame whose comment has no parseable energy keeps `energy_hartree: None` and is NOT
       dropped -- a frame that exists is evidence even if its energy did not parse.
    """
    out = []
    for i, (comment, atoms) in enumerate(xyzgraph.read_xyz_frames(text)):
        m = _ENERGY_RE.search(comment or "")
        e = float(m.group(1)) if m else None
        out.append({
            "index": i,
            "atoms": atoms,
            "energy_hartree": e,
            "energy_ev": None if e is None else units.hartree_to_ev(e),
            "comment": comment,
        })
    return out


# =============================================================================================
# dissociation / fragmentation classification
# =============================================================================================

def _contact_cutoff(cation, donor, table):
    return table.get("%s-%s" % (cation, donor), table.get("default", 2.5))


def classify_complex(atoms, n_ligands_expected=None, cation="Li", layers=None,
                     cutoff_shift_ang=0.0):
    """Is this structure still the complex we started from?

    Returns a dict with `classification` in {intact, ligand_dissociated, ligand_fragmented, None}.

    Two DIFFERENT events, never in one bucket:
      * `ligand_fragmented`  a covalent bond broke -- the number of covalent fragments changed
      * `ligand_dissociated` a ligand drifted off the cation but is chemically intact

    🔴 Fragmentation is tested FIRST and wins, because a fragmented ligand's pieces may each still
       sit near the cation and would otherwise read as intact.
    🔴 `cutoff_shift_ang` exists because `layer_I.contact_cutoff_ang` is flagged
       `[PLACEHOLDER-ESTIMATE]` in its own provenance and carries a MANDATORY rule: report how
       many classifications flip when the threshold moves by +/- `sensitivity_delta_ang`. That
       obligation is inherited by any number computed from it -- see `sensitivity_sweep`.
    """
    layers = layers if layers is not None else config.graph_layers()
    li_layer = layers["layer_I"]
    table = li_layer["contact_cutoff_ang"]

    idx_cation = [i for i, a in enumerate(atoms) if a[0] == cation]
    bonds = xyzgraph.bond_list(atoms, include_ionic=False)
    comps = xyzgraph.connected_components(len(atoms), bonds)
    ligand_comps = [c for c in comps if not all(i in idx_cation for i in c)]

    out = {
        "classification": CLASS_UNKNOWN,
        "cation": cation,
        "n_cation_atoms": len(idx_cation),
        "n_ligand_fragments": len(ligand_comps),
        "n_ligands_expected": n_ligands_expected,
        "cutoff_shift_ang": cutoff_shift_ang,
        "coordinated_fragments": None,
        "uncoordinated_fragments": None,
        "min_contact_ang": None,
        "warnings": [],
    }
    if not idx_cation:
        out["warnings"].append(
            "🔴 classification_impossible: no %s atom in this structure. Held OUT of the "
            "statistics rather than counted as intact." % cation)
        return out

    coordinated, uncoordinated, closest = [], [], None
    for comp in ligand_comps:
        best = None
        for j in comp:
            for i in idx_cation:
                d = xyzgraph.distance_ang(atoms[i], atoms[j])
                cut = _contact_cutoff(cation, atoms[j][0], table) + cutoff_shift_ang
                margin = d - cut
                if best is None or margin < best[0]:
                    best = (margin, d)
        if best is None:
            continue
        closest = best[1] if closest is None else min(closest, best[1])
        (coordinated if best[0] <= 0 else uncoordinated).append(sorted(comp))

    out["coordinated_fragments"] = len(coordinated)
    out["uncoordinated_fragments"] = len(uncoordinated)
    out["min_contact_ang"] = closest

    if n_ligands_expected is not None and len(ligand_comps) != n_ligands_expected:
        out["classification"] = CLASS_FRAGMENTED
    elif uncoordinated:
        out["classification"] = CLASS_DISSOCIATED
    else:
        out["classification"] = CLASS_INTACT
    return out


#: 🔴 THE LABEL IS PART OF THE MEASUREMENT. proposer5 withdrew "dissociation rate as a floppiness
#: measurement": U-55 asks about the SHAPE OF THE PES NEAR THE MINIMUM (curvature), and a rate is
#: KINETIC. The count SURVIVES as SEARCH HYGIENE -- we must know how much MTD output was
#: dissociated garbage -- but it is no longer a floppiness measurement and must not be read as one.
#: 🔴 The caveat lives in the FIELD NAME, not only in a doc, because a field name travels into
#: every downstream table and a doc does not.
DISSOCIATION_FIELD = "dissociation_events_at_uncontrolled_effective_temperature"

DISSOCIATION_LABEL = (
    "dissociation events at an uncontrolled effective temperature (T_eff/T_set measured at "
    "1.41-1.70x, bias-driven and IRREDUCIBLE -- the bias potential IS the search mechanism). "
    "🔴 SEARCH HYGIENE ONLY. This is NOT a floppiness measurement and must not be read as one: "
    "U-55 is a question about curvature and is answered by curvature.u55_panel().")


def dissociation_hygiene(structures, n_ligands_expected=None, cation="Li", layers=None,
                         temperature_measured_k=None, temperature_requested_k=None):
    """How much of this MTD output was dissociated garbage. 🔴 Search hygiene, NOT floppiness.

    The counts are the same ones `classify_complex` produces; what changes is the NAME and the
    caveat that travels with them. See `DISSOCIATION_FIELD`.
    """
    verdicts = [classify_complex(s, n_ligands_expected, cation, layers)["classification"]
                for s in (structures or [])]
    counts = _counts(verdicts)
    n = len(verdicts)
    return {
        DISSOCIATION_FIELD: counts.get(CLASS_DISSOCIATED, 0),
        "fragmented": counts.get(CLASS_FRAGMENTED, 0),
        "intact": counts.get(CLASS_INTACT, 0),
        "unclassified": counts.get("unclassified", 0),
        "n_structures": n,
        "usable_fraction": (None if not n
                            else counts.get(CLASS_INTACT, 0) / float(n)),
        "temperature_requested_k": temperature_requested_k,
        "temperature_measured_k": temperature_measured_k,
        "purpose": "search hygiene",
        "is_a_floppiness_measurement": False,
        "floppiness_is_measured_by": "curvature.u55_panel (nu_min, n_soft, condition number)",
        "label": DISSOCIATION_LABEL,
        "warnings": ([] if temperature_measured_k is not None else [
            "🔴 dissociation counted with NO measured temperature. The count is search hygiene "
            "either way, but without `temperature_measured_k` nobody can even state the "
            "conditions it was counted under."]),
    }


def sensitivity_sweep(structures, n_ligands_expected=None, cation="Li", layers=None):
    """Re-classify at cutoff -/+ `sensitivity_delta_ang` and REPORT HOW MANY VERDICTS FLIP.

    🔴 Mandatory, not optional. `config/graph_layers.json`'s own `_sensitivity_rule` says so, and
    its `_provenance` marks the cutoffs `[PLACEHOLDER-ESTIMATE: measurement required]`. A
    dissociation rate quoted without this is a number resting on a placeholder with no flag.
    """
    layers = layers if layers is not None else config.graph_layers()
    delta = layers["layer_I"].get("sensitivity_delta_ang", 0.2)
    base = [classify_complex(s, n_ligands_expected, cation, layers, 0.0)["classification"]
            for s in structures]
    flips = {}
    for shift in (-delta, +delta):
        moved = [classify_complex(s, n_ligands_expected, cation, layers,
                                  shift)["classification"] for s in structures]
        flips["%+.2f" % shift] = sum(1 for a, b in zip(base, moved) if a != b)
    return {
        "delta_ang": delta,
        "n_structures": len(structures),
        "n_flipped": flips,
        "base_counts": _counts(base),
        "cutoff_provenance": layers["layer_I"].get("_provenance"),
        "note": ("🔴 the Li-X contact cutoffs are [PLACEHOLDER-ESTIMATE]. Any dissociation rate "
                 "computed from them is provisional until they are replaced by the measured "
                 "Li-X RDF first minimum (§12.4-3)."),
    }


def _counts(values):
    out = {}
    for v in values:
        key = "unclassified" if v is None else v
        out[key] = out.get(key, 0) + 1
    return out


# =============================================================================================
# RMSD and dedupe
# =============================================================================================

def rmsd(a, b):
    """Optimally superimposed RMSD in Angstrom, by the quaternion method (Coutsias et al.).

    🔴 NO atom-order matching and NO permutation search: every conformer here comes from ONE
       trajectory of ONE species, so the atom ordering is shared by construction. Feeding this
       two independently built structures would compare atom i with atom i and be meaningless --
       a real hazard if someone later reuses it for arm1-vs-arm2.
    🔴 Mirror images are NOT recognised as duplicates. Stated rather than assumed away.
    """
    if len(a) != len(b):
        raise ValueError("rmsd needs equal atom counts, got %d and %d" % (len(a), len(b)))
    n = len(a)
    if n == 0:
        return 0.0
    for i in range(n):
        if a[i][0] != b[i][0]:
            raise ValueError(
                "rmsd: atom %d is %r in one structure and %r in the other. These are not the "
                "same species in the same order, and this function does no matching."
                % (i, a[i][0], b[i][0]))

    ca = [sum(s[k] for s in a) / n for k in (1, 2, 3)]
    cb = [sum(s[k] for s in b) / n for k in (1, 2, 3)]
    p = [[a[i][k + 1] - ca[k] for k in range(3)] for i in range(n)]
    q = [[b[i][k + 1] - cb[k] for k in range(3)] for i in range(n)]

    r = [[sum(p[i][x] * q[i][y] for i in range(n)) for y in range(3)] for x in range(3)]
    # Symmetric 4x4 key matrix; its largest eigenvalue is the optimal correlation.
    xx, xy, xz = r[0]
    yx, yy, yz = r[1]
    zx, zy, zz = r[2]
    k = [
        [xx + yy + zz, yz - zy,        zx - xz,        xy - yx],
        [yz - zy,      xx - yy - zz,   xy + yx,        zx + xz],
        [zx - xz,      xy + yx,        -xx + yy - zz,  yz + zy],
        [xy - yx,      zx + xz,        yz + zy,        -xx - yy + zz],
    ]
    lmax = linalg.largest_eigenvalue(k)
    g = sum(sum(v * v for v in p[i]) + sum(v * v for v in q[i]) for i in range(n))
    val = (g - 2.0 * lmax) / n
    return math.sqrt(max(val, 0.0))


def dedupe(candidates, cfg=None):
    """Collapse duplicates. `candidates` = [{"atoms", "energy_hartree", ...}], any order.

    Returns `(unique, mapping)`. Kept in ascending energy so `unique[0]` is the GFN2 minimum.
    🔴 A candidate with no energy is never dropped; it sorts last and is kept as its own entry,
       because "we could not read its energy" is not "it is a duplicate".
    """
    d = spec(cfg)["dedupe"]
    rms_thr, e_thr_ev = d["rmsd_threshold_ang"], d["energy_threshold_ev"]

    ordered = sorted(candidates,
                     key=lambda c: (c.get("energy_hartree") is None,
                                    c.get("energy_hartree") or 0.0))
    unique, duplicates_of = [], {}
    for cand in ordered:
        match = None
        for u in unique:
            if (cand.get("energy_hartree") is not None
                    and u.get("energy_hartree") is not None):
                de = abs(units.hartree_to_ev(
                    cand["energy_hartree"] - u["energy_hartree"]))
                if de > e_thr_ev:
                    continue
            else:
                continue
            if rmsd(cand["atoms"], u["atoms"]) <= rms_thr:
                match = u
                break
        if match is None:
            unique.append(cand)
        else:
            duplicates_of.setdefault(match["index"], []).append(cand["index"])
    return unique, {
        "n_in": len(candidates),
        "n_unique": len(unique),
        "duplicates_of": duplicates_of,
        "rmsd_threshold_ang": rms_thr,
        "energy_threshold_ev": e_thr_ev,
        "_thresholds_are_coder_chosen": True,
        "_note": ("§37.2.3: the risk in re-implementing CREST is not the physics (GFN2 sampling "
                  "is the same) -- it is exactly these dedupe/convergence hyperparameters. They "
                  "are reported with every ensemble for that reason."),
    }


# =============================================================================================
# promotion to DFT
# =============================================================================================

def select_for_dft(unique, cfg=None):
    """EVERY conformer inside the GFN2 window. Not the lowest one.

    §37.2.4-2, verbatim in effect: promote every conformer inside a GFN2 window of <= 0.13 eV to
    DFT and RE-RANK AT DFT. 🔴 That is what closes the route by which xTB could set the ΔG
    ordering, and it is the condition under which this stays inside §16.1-B2.
    """
    window_ev = spec(cfg)["dft_promotion"]["gfn2_window_ev"]
    scored = [c for c in unique if c.get("energy_hartree") is not None]
    unscored = [c for c in unique if c.get("energy_hartree") is None]
    out = {
        "window_ev": window_ev,
        "rerank_at": spec(cfg)["dft_promotion"]["rerank_at"],
        "selected": [],
        "n_selected": 0,
        "n_unique": len(unique),
        "gfn2_minimum_hartree": None,
        "warnings": [],
        "_ordering_note": ("🔴 the GFN2 ordering here is a SELECTION only. The reported ordering "
                           "is DFT's. If any code downstream ranks by `energy_hartree` from this "
                           "module it has reintroduced the §16.1-B2 problem."),
    }
    if unscored:
        out["warnings"].append(
            "🔴 %d conformer(s) have no GFN2 energy and cannot be placed in the window. They are "
            "PROMOTED anyway rather than dropped -- an unreadable energy is not evidence that a "
            "conformer is high-lying." % len(unscored))
    if scored:
        e_min = min(c["energy_hartree"] for c in scored)
        out["gfn2_minimum_hartree"] = e_min
        out["selected"] = [c for c in scored
                           if units.hartree_to_ev(c["energy_hartree"] - e_min) <= window_ev]
    out["selected"] = out["selected"] + unscored
    out["n_selected"] = len(out["selected"])
    return out


# =============================================================================================
# the three figures R-4 needs
# =============================================================================================

def arm_comparison(arm1_ensemble_core_h, arm1_best_core_h, arm2_core_h,
                   arm1_n_conformers=None):
    """The THREE separate figures. 🔴 Collapsing any two of them loses R-4.

        arm1_best     vs arm2       ->  "was the guess bad?"
        arm1_ensemble vs arm1_best  ->  "what does the conformer search buy?"   ( = R-4 )

    Every ratio goes through C-1's discipline: a missing input yields `None`, never a number.
    """
    def ratio(num, den):
        if num is None or den in (None, 0):
            return None
        return num / float(den)

    return {
        "route": ROUTE_ID,
        "_route_note": ("🔴 R-4 now retires 'does the %s conformer route work'. It does NOT "
                        "retire 'does the ETKDG route work' -- that route was withdrawn as "
                        "undefined for this species class before any of it ran." % ROUTE_ID),
        "arm1_ensemble_core_h": arm1_ensemble_core_h,
        "arm1_best_core_h": arm1_best_core_h,
        "arm2_core_h": arm2_core_h,
        "arm1_n_conformers": arm1_n_conformers,
        "guess_penalty_ratio": ratio(arm2_core_h, arm1_best_core_h),
        "_guess_penalty_meaning": ("arm2 / arm1-best. How much of RT-1's cost was the bad guess. "
                                   ">1 means the idealised geometry cost more."),
        "conformer_search_cost_ratio": ratio(arm1_ensemble_core_h, arm1_best_core_h),
        "_conformer_search_meaning": ("arm1-ensemble / arm1-best = R-4. What the search costs "
                                      "relative to keeping only its winner."),
        "_do_not_collapse": ("🔴 arm 1 is an ENSEMBLE and arm 2 is ONE STRUCTURE. Comparing the "
                             "ensemble total against arm 2 would conflate 'the guess was bad' "
                             "with 'we ran N conformers', and no later analysis can separate "
                             "them again."),
    }


#: The three points at which symmetry is measured. 🔒 ORDERED BY THE LEAD as INSTRUMENTATION, not
#: methodology: nothing is perturbed and no symmetry-breaking step is added.
SYMMETRY_CHECKPOINTS = ("preopt_input", "post_mtd_conformer", "final_dft_geometry")


def symmetry_trace(geometries_by_checkpoint, centre="Li", species_id=None):
    """Did the symmetry actually break, and WHERE? A measurement, not an assumption.

    🔴 THE DEFECT THIS CLOSES. Arm 1 pre-optimises at GFN2 before the MTD, and it was believed
       that this dealt with the input pathology. MEASURED, it does not:
```
        li_ec_cation IDEALISED   Li equidistant: 2x C@5.2497 · 2x O@4.0341 · 4x H@5.8456
        li_ec_cation GFN2 OPT    Li equidistant: 2x C@5.0415 · 2x O@3.7516 · 4x H@5.6401
                                 every distance moved -- THE EXACT DEGENERACY DID NOT
```
       The gradient along the symmetry-breaking coordinate is exactly zero, so a tight
       optimisation relaxes everything except the one thing that matters and stays on the element.
       ⟹ the structure entering the MTD is still symmetric, and **we were relying on the MTD's
         random velocities to break it as a SIDE EFFECT, with nothing recording whether it
         happened.** This records it.

    🟢 If the conformers break symmetry reliably, a reliance becomes a verified fact for free.
       If they do not, B0 has found a real defect in the production route before production --
       which is what a gate batch is for.
    """
    from . import guards

    trace, prev = {}, None
    for point in SYMMETRY_CHECKPOINTS:
        atoms = (geometries_by_checkpoint or {}).get(point)
        if atoms is None:
            trace[point] = {"measured": False, "flagged": None,
                            "note": "geometry not supplied at this checkpoint"}
            continue
        f = guards.symmetric_placement_flags(atoms, centre=centre)
        trace[point] = {"measured": True, "flagged": f["flagged"],
                        "n_degenerate_sets": len(f["degenerate_sets"]),
                        "degenerate_sets": f["degenerate_sets"]}
        prev = point

    measured = [p for p in SYMMETRY_CHECKPOINTS if trace[p]["measured"]]
    first, last = (measured[0] if measured else None), (measured[-1] if measured else None)
    out = {
        "species_id": species_id,
        "centre": centre,
        "checkpoints": trace,
        "n_measured": len(measured),
        "symmetry_broke": None,
        "warnings": [],
        "_is_instrumentation_only": (
            "🔒 NOTHING IS PERTURBED HERE. This measures whether the symmetry broke; adding a "
            "symmetry-breaking step is a METHODOLOGY change and is not taken."),
        "_what_a_persisting_flag_means": (
            "🔴 a structure stuck on a symmetry element is generally a SADDLE, not a minimum. If "
            "the flag survives to `final_dft_geometry`, expect an imaginary mode there -- see "
            "curvature.imaginary_mode_verdict, which is the direct signature."),
    }
    if len(measured) < 2:
        out["warnings"].append(
            "🔴 symmetry_trace_incomplete for %s: %d of %d checkpoints measured, so whether the "
            "symmetry broke CANNOT BE TOLD. Not 'it broke'."
            % (species_id, len(measured), len(SYMMETRY_CHECKPOINTS)))
        return out

    began, ended = trace[first]["flagged"], trace[last]["flagged"]
    if began is None or ended is None:
        out["warnings"].append(
            "🔴 symmetry_trace_indeterminate for %s: a checkpoint returned None (no centre atom "
            "present). Not 'it broke'." % species_id)
        return out
    out["symmetry_broke"] = bool(began and not ended)
    if began and ended:
        out["warnings"].append(
            "🔴 symmetry_persisted for %s: the exact-distance degeneracy is STILL PRESENT at "
            "`%s` (%d set(s)). 🔴 The reliance on MTD velocities to break it DID NOT HOLD for "
            "this species. %s"
            % (species_id, last, trace[last]["n_degenerate_sets"],
               out["_what_a_persisting_flag_means"]))
    elif not began:
        out["warnings"].append(
            "🟢 symmetry_absent_at_start for %s: nothing to break at `%s`. `symmetry_broke` is "
            "False because no breaking was required, NOT because breaking failed."
            % (species_id, first))
    return out
