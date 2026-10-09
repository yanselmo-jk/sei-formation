#!/bin/bash
# SP_LADDER.sh — one rung of the SP ladder (§39.47(c), §39.48(d)/(e), §39.49, §R39.26/§R39.28).
#
# WHAT A RUNG IS: a full transition-state search is unaffordable at production size, so the
# ladder lays DFT SINGLE POINTS on a path the cheap engine already produced and reads a barrier
# from those. `n` (SEI_SP_LADDER_N) is the rung's coordination number.
#
# 🔴 THIS PAYLOAD DOES NOT GENERATE THE PATH. It consumes one and REFUSES unless that path
#    arrives with the provenance every ruling attached to it — engine, dimensionality, a G-SCAN
#    verdict, a seed record with a PRE-REGISTERED attempt count, and a relaxation state.
#    Generating a path here would duplicate `gfn2_scan` and, worse, would let the ladder
#    quietly accept a path that never passed the gate.
#
# 🔴 THE FIRST RUNG TO RETURN IS THIS PROJECT'S FIRST SINGLE-POINT MEASUREMENT. Every per-SP
#    cost in the plan is a derived stack (an anchor / cycles x multiplier); §39.48(e) requires
#    later rungs be re-derived from the measured number, never from the stack. This payload
#    emits `per_sp_core_hours` for exactly that, plus the §R39.28 replan comparison.
#
# env (plan.py sp_ladder_items() declares these):
#   SEI_SP_LADDER_N            rung coordination number (1, 2, 3)
#   SEI_SP_LADDER_POINTS       7 by default (both endpoints + 5 centred on the GFN2 maximum)
#   SEI_SP_LADDER_POINTS_MAX   9 — the ceiling after a triggered bracket extension
#   SEI_SP_LADDER_PATH         path artefact (JSON). Absent => refuse, do not invent one.
#
# exit: 2=env/input  3=no QC code  4=smoke/solvent refused  5=path preconditions unmet
#       0=completed (the VERDICT is the collector's, not this script's)
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
N="${SEI_SP_LADDER_N:-}"
NPTS="${SEI_SP_LADDER_POINTS:-7}"
NPTS_MAX="${SEI_SP_LADDER_POINTS_MAX:-9}"

case "$N" in 1|2|3|4) ;; *)
  echo "[SP_LADDER] SEI_SP_LADDER_N must be the rung's coordination number (got '${N}')"
  exit 2 ;;
esac

# --- level: the SAME source the TS chain uses. 🔴 [§R39.24 precondition 1] The route flags
#     must be IDENTICAL to a full attempt's, or the ladder measures a ROUTE difference and
#     reports it as a METHOD difference. Sharing the generator is what enforces that — not
#     comparing two strings written in two places.
LVL="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import config
lvl = (config.load("b0_reactions.json", {}).get("level") or {}).get("geometry_and_hessian")
print(lvl or "")')"
[ -z "$LVL" ] && { echo "[SP_LADDER] b0_reactions.json level.geometry_and_hessian missing"; exit 2; }

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  echo "[SP_LADDER] no QC code available → skipped. ${SEI_QC_DETAIL:-}"
  exit 3
fi
# 🔴 Smoke before any production input (ADR-105/108). P6 skipped this and cost the round its
#    entire kappa measurement; the rule is enforced for every payload by
#    tests/test_payload_shell.py, which DERIVES it rather than listing names.
sei_qc_smoke > "$D/smoke_result.txt" 2>&1 || { echo "[SP_LADDER] route smoke failed → stop"; exit 4; }

# --- PATH PRECONDITIONS. Checked BEFORE any DFT is ordered. -----------------------------------
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$N" "${SEI_SP_LADDER_PATH:-}" <<'PYPRE'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import sp_ladder
d, n, path_file = sys.argv[1], int(sys.argv[2]), sys.argv[3]
path = None
if path_file and os.path.exists(path_file):
    try:
        path = json.load(open(path_file))
    except ValueError as exc:
        path = {"_unreadable": str(exc)}
check = sp_ladder.check_path_preconditions(path, n)
if not path_file:
    check["ok"] = False
    check["reasons"].insert(0, "SEI_SP_LADDER_PATH is unset -- the ladder consumes a path, it "
                               "does not invent one")
elif path is None:
    check["ok"] = False
    check["reasons"].insert(0, "path artefact %r does not exist" % path_file)
json.dump(check, open(os.path.join(d, "sp_ladder_preconditions.json"), "w"),
          ensure_ascii=False, indent=1)
sys.exit(0 if check["ok"] else 1)
PYPRE
then
  echo "[SP_LADDER] 🔴 path preconditions unmet — NOT spending DFT. Reasons:"
  sed 's/^/     ↳ /' "$D/sp_ladder_preconditions.json" | head -20
  echo "     cause_class=protocol: this says the ladder must not spend, NOT that the reaction"
  echo "     lacks a barrier."
  exit 5
fi

# --- Which points get a single point (§39.48(d)) ---------------------------------------------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "${SEI_SP_LADDER_PATH}" "$NPTS" <<'PYPICK'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import sp_ladder
d, path_file, npts = sys.argv[1], sys.argv[2], int(sys.argv[3])
path = json.load(open(path_file))
points = path["points"]
idx = sp_ladder.select_sp_points([p.get("energy_hartree") for p in points], npts)
if idx is None:
    json.dump({"error": "path too short to bracket a maximum"},
              open(os.path.join(d, "sp_points.json"), "w"))
    raise SystemExit(0)
for k in idx:
    g = points[k].get("geometry") or []
    with open(os.path.join(d, "sp_%02d.xyz" % k), "w") as fh:
        fh.write("%d\nSP ladder point %d (path frame, relaxation_state=%s)\n"
                 % (len(g), k, path.get("relaxation_state")))
        fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in g))
json.dump({"indices": idx, "n_points": len(idx),
           "reference_index": idx[0],
           "_reference_note": ("the barrier is measured from the PATH'S OWN first frame at "
                               "DFT. The certified reactant supplies the STRUCTURE the path "
                               "starts from and NEVER an energy -- mixing the two puts the "
                               "ends of the barrier in different relaxation states, and that "
                               "offset grows with n (§39.64/§39.71).")},
          open(os.path.join(d, "sp_points.json"), "w"), ensure_ascii=False, indent=1)
print("[SP_LADDER] single points at path indices: %s" % idx)
PYPICK

if [ ! -s "$D/sp_points.json" ] || grep -q '"error"' "$D/sp_points.json"; then
  echo "[SP_LADDER] no usable point selection — stopping without spending DFT."
  exit 5
fi

# --- The single points themselves, at the TS chain's own level -------------------------------
for _f in "$D"/sp_[0-9][0-9].xyz; do
  [ -e "$_f" ] || continue
  _tag="$(basename "${_f%.xyz}")"
  sei_qc_input "$D/${_tag}.gjf" "$LVL" sp "0" "2" "$_f" \
    > "$D/${_tag}.meta.json" 2>&1 \
    && sei_stage "sp_ladder_${_tag}" sei_qc_run "$D" "${_tag}.gjf" "${_tag}.log"
done

# --- Read-out: barrier, bracket-edge trigger, and THE per-SP cost measurement ------------------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$N" "$NPTS_MAX" <<'PYREAD'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import plan, sp_ladder
from sei_pilot.criteria import cost, g16
d, n, npts_max = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
sel = json.load(open(os.path.join(d, "sp_points.json")))

energies, stages = [], {}
for k in sel["indices"]:
    tag = "sp_%02d" % k
    try:
        text = open(os.path.join(d, "%s.log" % tag), errors="replace").read()
    except OSError:
        energies.append(None)
        continue
    summ = g16.summarize(text)
    energies.append((summ.get("scf") or {}).get("final_energy_hartree"))
    # 🔴 `rc` and `normal_termination` both lie on this cluster -- completion comes from
    #    OUTPUT EVIDENCE only (see criteria/g16.py's standing check).
    stages[tag] = g16.stages_completed(text, summ.get("route_echoed"))

recs = cost.read_stage_records(d)
total_core_h = cost.total_core_hours(recs)
per_sp = sp_ladder.per_sp_core_hours(total_core_h, len(sel["indices"]))
estimate = plan.SP_LADDER_CORE_H.get(n)
est_per_sp = (estimate / float(len(sel["indices"]))) if estimate else None

out = {
    "rung_n": n,
    "sp_indices": sel["indices"],
    "reference_index": sel["reference_index"],
    "_reference_note": sel["_reference_note"],
    "sp_energies_hartree": energies,
    "barrier_ev": sp_ladder.barrier_ev(energies),
    "bracket": sp_ladder.needs_bracket_extension(sel["indices"], energies),
    "points_max": npts_max,
    "stages_completed": stages,
    "total_core_hours": total_core_h,
    # 🔴 THE MEASUREMENT THIS RUNG EXISTS TO PRODUCE FIRST (§39.48(e)).
    "per_sp_core_hours": per_sp,
    "per_sp_core_hours_estimated": est_per_sp,
    "replan": plan.sp_ladder_replan_required(per_sp, est_per_sp),
    "_claim_discipline": ("DFT-resolved over ONE rung; SP-resolved over the ladder, CALIBRATED "
                          "AT ONE. 🔴 One calibration point measures an OFFSET and cannot show "
                          "whether that offset is CONSTANT IN n -- which is the ladder's whole "
                          "claim. It becomes a two-rung claim only after T21-se runs."),
}
json.dump(out, open(os.path.join(d, "sp_ladder_result.json"), "w"),
          ensure_ascii=False, indent=1)
print("[SP_LADDER] n=%s barrier=%s eV  per_sp=%s core-h  replan=%s"
      % (n, out["barrier_ev"], per_sp, out["replan"]["replan_required"]))
if out["bracket"].get("extend"):
    print("[SP_LADDER] 🔴 the DFT maximum sits at a bracket EDGE — this barrier is a LOWER "
          "BOUND until the bracket is extended to <= %d points (§39.48(d))." % npts_max)
if out["replan"]["replan_required"]:
    print("[SP_LADDER] 🔴 per-SP cost differs from the estimate by %.2fx — RE-PLAN the "
          "remaining rungs BEFORE submitting them (§R39.28)." % (out["replan"]["ratio"] or 0))
PYREAD

echo "[SP_LADDER] done (rung n=${N}). The verdict is the collector's."
exit 0
