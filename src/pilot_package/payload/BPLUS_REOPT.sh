#!/bin/bash
# BPLUS_REOPT.sh — §39.124 Candidate D(i): tight re-optimisation of the EXISTING B+ mid/last
# geometries, at the TS chain's own certification convergence (C-8's tight+freq route), from
# geometries ALREADY ON DISK. No new IRC sampling, no new guess.
#
# 🔴🔴 STAGING ONLY, NOT WIRED INTO plan.py -- deliberately. This script is NOT reachable from
#    `./run.sh` and is not scheduled by any Item. Wiring a new Item is a plan.py/engineer
#    decision (ADR-110's own rule -- `cores_per_task` must be declared EXPLICITLY on any Item,
#    never `None` -- applies at THAT point, not to this file) that nobody has made yet; §1f/§R39.81
#    priced this candidate but did not release it into the live plan. Run manually, or wire it
#    once that decision lands.
#
# WHY THIS EXISTS (§39.124 finding (b), 05_STATE.md §1f): the reverse arm's B+ mid/last points
# agree to 0.000127 eV while sitting 0.17 A apart on the declared breaking bond -- because the
# reactant-side surface is close to flat at `opt=loose`. This job answers whether that 0.17 A gap
# is a genuine nearby feature or a loose-optimisation artifact, by re-converging BOTH points at
# TIGHT thresholds (matching C-8's own certification: `endpoint_opt_freq`, the same route
# `endpoint_prep.sh` stage 2 uses) and re-running the SAME comparators (`guards.bplus_agreement`,
# `guards.reactant_match`) on the tightly-converged pair.
#
# 🔴 LEVEL: the SAME level the rest of the TS chain (and B+'s own loose terminal opts) used --
#    read from `config/b0_reactions.json`'s `level.geometry_and_hessian`, exactly like
#    `payload/U56.sh` does. NOT invented here, NOT a coder choice.
# 🔴 NO C-9 PERTURBATION: unlike `endpoint_prep.sh`'s stage 1 guesses, `bplus_reverse_mid.xyz`/
#    `..._last.xyz` are ALREADY the converged output of a real loose optimisation on a real IRC
#    path point, not an idealised symmetric template -- there is nothing to kick out of a plane
#    it was never placed on by hand.
# 🔴 [ADR-114] Wall cap 48h -- trivial here: one 11-atom tight+freq optimisation per point, the
#    SAME job class B+'s own loose terminal opts already ran (measured 14.66 / 10.32 core-h at 64
#    cores per point at LOOSE convergence -- engineer13's 30.0-49.9 core-h TOTAL estimate for both
#    points at TIGHT is the 1.2-2x ratio applied to that measurement, §R39.81).
#
# Required env (no defaults invented -- an unset required var is a refusal, not a guess):
#   SEI_BPLUS_MID_XYZ       path to the existing bplus_*_mid.xyz
#   SEI_BPLUS_LAST_XYZ      path to the existing bplus_*_last.xyz
#   SEI_BPLUS_REACTANT_XYZ  path to the certified reactant (reactant_certified.xyz / the
#                           endpoint_prep tight-stage output for this reaction's reactant role)
# Optional env:
#   SEI_BPLUS_MAPPING_JSON  u56_<rxn>_mapping.json -- break/form pairs for `guards.reactant_match`
#                           (§39.124 finding (c)/candidate D(ii)). If unset, `reactant_match` is
#                           NOT computed and the gap is recorded, not silently skipped.
#   SEI_BPLUS_LABEL         free-text provenance tag (e.g. "R-A_reverse"), stored verbatim
#
# exit: 2=input/env error  3=no QC engine  4=smoke/solvent refusal  0=ran to completion
#       (chemical verdict, if any, is in bplus_reopt_verdict.json -- this script never renders one)
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
CHARGE=0
MULT=2      # same reduced-radical doublet every U56/endpoint_prep job in this package uses
LABEL="${SEI_BPLUS_LABEL:-}"

_write_terminal() {
  sei_terminal "$1" "$2" "label=${LABEL}" "level=${LVL:-}"
}

MID_XYZ="${SEI_BPLUS_MID_XYZ:-}"
LAST_XYZ="${SEI_BPLUS_LAST_XYZ:-}"
REACTANT_XYZ="${SEI_BPLUS_REACTANT_XYZ:-}"
MAPPING_JSON="${SEI_BPLUS_MAPPING_JSON:-}"

for _var_name in SEI_BPLUS_MID_XYZ SEI_BPLUS_LAST_XYZ SEI_BPLUS_REACTANT_XYZ; do
  _val="$(eval echo "\${${_var_name}:-}")"
  if [ -z "${_val}" ]; then
    echo "[BPLUS_REOPT] ${_var_name} is required and unset."
    _write_terminal "input_error" "${_var_name} unset"
    exit 2
  fi
  if [ ! -f "${_val}" ]; then
    echo "[BPLUS_REOPT] 🔴 ${_var_name} does not exist on disk: ${_val}"
    _write_terminal "input_missing" "${_var_name} not found: ${_val}"
    exit 2
  fi
done

# --- level: SAME single source of truth U56.sh uses. No hardcoding here. --------------------
LVL="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import config
lvl = (config.load("b0_reactions.json", {}).get("level") or {}).get("geometry_and_hessian")
print(lvl or "")')"
if [ -z "$LVL" ]; then
  echo "[BPLUS_REOPT] b0_reactions.json's level.geometry_and_hessian is missing -- refusing to invent a level"
  _write_terminal "input_error" "b0_reactions.json level.geometry_and_hessian is missing"
  exit 2
fi

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  echo "[BPLUS_REOPT] no QC engine available -> skip. reason: ${SEI_QC_DETAIL:-(unknown)}"
  _write_terminal "skipped" "no QC engine available (${SEI_QC_DETAIL:-unknown})"
  exit 3
fi

if ! sei_qc_smoke > "$D/smoke_result.txt" 2>&1; then
  echo "[BPLUS_REOPT] route smoke failed -> not spending on the real jobs:"
  tail -15 "$D/smoke_result.txt"
  _write_terminal "route_smoke_failed" "sei_qc_smoke failed (deck/route not validated)"
  exit 4
fi

# --- C-5 precheck: refuse before spending a single core-h on the wrong solvent. --------------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - 2>"$D/solvent_precheck.err" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import solvent
try:
    rv = json.load(open(os.path.join(
        os.environ.get("SEI_JOB_DIR") or ".", "deck_verification%s.json"
        % (os.environ.get("SEI_TASK_FILE_SUFFIX") or ""))))
except (OSError, ValueError):
    rv = None
try:
    solvent.resolve_solvent_line(solvent.load_policy(), runtime_verification=rv)
except solvent.SolventDescriptorsMissing as exc:
    sys.stderr.write(str(exc) + "\n")
    sys.exit(1)
except solvent.SolventUndecided as exc:
    sys.stderr.write(str(exc) + "\n")
    sys.exit(2)
PY
_rc=$?
if [ ${_rc} -eq 1 ]; then
  echo "[BPLUS_REOPT] 🔴 C-5: EC:EMC SMD descriptors are missing -- not silently falling back to acetonitrile."
  cat "$D/solvent_precheck.err"
  _write_terminal "solvent_descriptors_missing" "C-5 refuses to proceed with acetonitrile"
  exit 4
elif [ ${_rc} -ne 0 ]; then
  echo "[BPLUS_REOPT] 🔴 C-5: no solvent decision on record -- refusing to emit any deck."
  cat "$D/solvent_precheck.err"
  _write_terminal "solvent_refused" "C-5: no solvent decision reached this deck (solvent_policy unset)"
  exit 4
fi

# --- TIGHT reopt, one stage per point, SAME route endpoint_prep's stage 2 (certification) uses.
for _tag_src in "mid:${MID_XYZ}" "last:${LAST_XYZ}"; do
  _tag="${_tag_src%%:*}"
  _src="${_tag_src#*:}"
  sei_qc_input "$D/bplus_reopt_${_tag}.gjf" "$LVL" endpoint_opt_freq "$CHARGE" "$MULT" \
    "$_src" > "$D/bplus_reopt_${_tag}.meta.json" 2>"$D/bplus_reopt_${_tag}.meta.err"
  if [ $? -ne 0 ]; then
    echo "[BPLUS_REOPT] input generation failed for ${_tag}:"; cat "$D/bplus_reopt_${_tag}.meta.err"
    _write_terminal "input_error" "input generation failed for ${_tag}"
    exit 5
  fi
  sei_stage "bplus_reopt_${_tag}" sei_qc_run "$D" "bplus_reopt_${_tag}.gjf" "bplus_reopt_${_tag}.log"
done

# --- Read both tight logs, run the SAME comparators B+ itself uses (guards.bplus_agreement),
# --- PLUS the §39.124(c) reactant-match check, on the tightly-converged geometries. -----------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "${REACTANT_XYZ}" "${MAPPING_JSON}" "${LABEL}" \
    <<'PYVERDICT'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import g16, xyzgraph, f1_endpoint as f1
d, reactant_xyz, mapping_json, label = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]


def read(tag):
    path = os.path.join(d, "bplus_reopt_%s.log" % tag)
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return None, None, None, None
    summ = g16.summarize(text)
    n_imag = f1.n_imaginary(g16.parse_frequencies(text))
    return (g16.last_geometry(text),
            (summ.get("scf") or {}).get("final_energy_hartree"),
            (summ.get("opt") or {}).get("converged"),
            n_imag)


geom_mid, e_mid, conv_mid, nimag_mid = read("mid")
geom_last, e_last, conv_last, nimag_last = read("last")

out = {
    "label": label,
    "_purpose": ("§39.124 finding (b): does the LOOSE-optimisation 0.17 A mid/last gap on the "
                "breaking bond survive TIGHT convergence, or was it a loose-opt artifact? "
                "Answered by re-running the SAME comparator (bplus_agreement) on these two "
                "tightly-converged points."),
    "tight_stage": {
        "mid": {"converged": conv_mid, "n_imag": nimag_mid, "energy_hartree": e_mid},
        "last": {"converged": conv_last, "n_imag": nimag_last, "energy_hartree": e_last},
    },
    "tight_bplus_agreement": guards.bplus_agreement(geom_mid, geom_last, e_mid, e_last),
}

# §39.124 finding (c) / candidate D(ii): the missing reactant-match check, now also run on the
# TIGHTLY re-converged points -- not just the original loose ones. Same open-reading caveat as
# `payload/U56.sh`'s wiring: BOTH mid and last are checked, the combination rule is NOT decided
# here.
reactant_match = {"mid": None, "last": None, "_status": None}
if not reactant_xyz:
    reactant_match["_status"] = "SEI_BPLUS_REACTANT_XYZ not supplied -- not computed"
elif not mapping_json:
    reactant_match["_status"] = ("SEI_BPLUS_MAPPING_JSON not supplied -- break-bond pairs "
                                 "unavailable, not computed (Rule 18: unknown is not permission)")
else:
    try:
        mapping = json.load(open(mapping_json))
        pairs = []
        for kind in ("break", "form"):
            for e in (mapping["mapping"].get(kind) or []):
                i, j = e["selected"]
                pairs.append((int(i), int(j), "%s:%s" % (kind, e.get("role") or e.get("label"))))
        atoms_r = xyzgraph.read_xyz_frames(open(reactant_xyz, errors="replace").read())[0][1]
        reactant_match["mid"] = guards.reactant_match(geom_mid, atoms_r, pairs)
        reactant_match["last"] = guards.reactant_match(geom_last, atoms_r, pairs)
        reactant_match["_status"] = "computed against %s" % reactant_xyz
    except (OSError, KeyError, IndexError, ValueError) as exc:
        reactant_match["_status"] = ("NOT computed: %s: %s -- an unrun comparison is not a "
                                     "match" % (type(exc).__name__, exc))
out["tight_reactant_match"] = reactant_match

json.dump(out, open(os.path.join(d, "bplus_reopt_verdict.json"), "w"),
          ensure_ascii=False, indent=1)
print("[BPLUS_REOPT] tight agreement=%s | reactant_match(mid/last)=%s/%s"
      % (out["tight_bplus_agreement"].get("agreement"),
         (reactant_match["mid"] or {}).get("match"), (reactant_match["last"] or {}).get("match")))
PYVERDICT

echo "[BPLUS_REOPT] done (label=${LABEL:-none}). See bplus_reopt_verdict.json -- this script "
echo "  renders NO chemical verdict itself (Rule 18); it produces the comparator inputs."
_write_terminal "ran_to_completion" "tight reopt of both B+ points complete; verdict is data, not a status"
exit 0
