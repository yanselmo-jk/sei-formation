#!/bin/bash
# Stage 0 — the MTD-pilot comparator: 12 seeds x 100 ps UNBIASED NVT xtb MD at the temperature
# ladder's top rung (1500 K), on R-C's reactant (li_ec2_radical, 21 atoms).
#
# 🟢 [02_METHOD_SPEC.md §39.40(d)-RESULT/§39.40(e)/§39.42(d), final length RULED §39.47(b):
# "STAGE 0 = 12 SEEDS x 100 ps, unbiased NVT at the ladder's top rung"] NOT metadynamics --
# plain unbiased MD, structurally different from sei_pilot/conformers.py's `xtb --metadyn`
# route (B0-D arm 1, a different job for a different purpose). 100 ps = 100x T1's measured
# first-passage time (<1ps, the 1-seed dev-box discovery run, §39.42(d)). Berendsen thermostat
# (xtb's own $md default) -- this run is a DISCOVERY probe, no rate/temperature claim depends
# on the thermostat being canonical.
#
# 🔴 BLINDNESS (§39.40(e)): "the target list is written to a sealed file and its hash recorded
# in the discovery ledger BEFORE the first run starts. The classifier is a molecular-graph
# comparator and contains NO target templates." This script's own classifier (below) is
# DELIBERATELY target-blind -- it reports every bond change/fragmentation event it observes,
# generically, using the SAME covalent-graph machinery guards.py/collect.py already use
# (sei_pilot.criteria.xyzgraph). It does NOT hardcode T1-T4's specific atom indices (no sealed
# target file exists yet in this project's committed files -- that is a proposer13
# pre-registration step, not a coder one). Matching this run's observed events against the
# sealed T1-T4 list (ring-opening at two different bonds, C2H4 elimination, CO release) is a
# follow-up read once that file exists, NOT part of what this script decides.
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
D="${SEI_JOB_DIR}"
NP="${SEI_TOTAL_CORES:-1}"
N_SEEDS="${SEI_STAGE0_N_SEEDS:-12}"
TEMP_K="${SEI_STAGE0_TEMP_K:-1500}"
TIME_PS="${SEI_STAGE0_TIME_PS:-100.0}"
REACTANT_XYZ="${SEI_STAGE0_REACTANT_XYZ:-inputs/li_ec2_radical_reactant.xyz}"
CHARGE="${SEI_STAGE0_CHARGE:-0}"
MULT="${SEI_STAGE0_MULTIPLICITY:-2}"

# 🟢 [envpaths.vendored/resolve_tool, payload/P3.sh's own detection pattern -- reused
# verbatim, not re-derived] vendored -> PATH -> extra search paths. Tested for real, not just
# found: a stale/broken vendored binary falls through to the system one rather than dying.
eval "$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$SEI_PKG_ROOT" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1])
from sei_pilot import envpaths
from sei_pilot.shellrun import Shell
v = envpaths.vendored("xtb", sys.argv[1])
if v:
    print('SEI_XTB=%s' % v["path"])
    for k, val in v["env"].items():
        print('export %s=%s' % (k, val))
else:
    print('SEI_XTB=%s' % (envpaths.resolve_tool(Shell(), "xtb", prefer_vendored=False) or ""))
PY
)"
XTB_SOURCE="vendored"
if [ -n "${SEI_XTB:-}" ]; then
  if ! "${SEI_XTB}" --version > "$D/xtb_version.txt" 2>&1; then
    echo "[stage0] 🔴 vendored xtb failed to run (arch/permissions?) -> falling back to system xtb"
    cat "$D/xtb_version.txt" | tail -5
    SEI_XTB="$(command -v xtb 2>/dev/null || true)"
    XTB_SOURCE="system_after_vendored_failed"
  fi
fi
[ -z "${SEI_XTB:-}" ] && { echo "[stage0] no xtb (neither vendored nor system) -> skipping"; exit 3; }
export SEI_XTB
echo "{\"xtb_path\": \"${SEI_XTB}\", \"source\": \"${XTB_SOURCE}\"}" > "$D/xtb_source.json"
echo "[stage0] xtb: ${SEI_XTB} (${XTB_SOURCE})"

if [ ! -f "${SEI_PKG_ROOT}/${REACTANT_XYZ}" ]; then
  echo "[stage0] reactant xyz missing: ${SEI_PKG_ROOT}/${REACTANT_XYZ} -> skipping, 0 core-h"
  exit 4
fi
cp "${SEI_PKG_ROOT}/${REACTANT_XYZ}" "$D/reactant.xyz"

# 🟢 [uhf_from_multiplicity(), sei_pilot/conformers.py -- reused, not re-derived: xtb wants
# unpaired electrons, Gaussian wants 2S+1; mixing them up silently changes the electronic
# state without an error]
UHF="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c \
  "from sei_pilot.conformers import uhf_from_multiplicity as u; print(u(${MULT}))")"

mkdir -p "$D/seeds"
: > "$D/tasks.txt"
for i in $(seq 1 "$N_SEEDS"); do
  w="$D/seeds/s%02d"
  w="$(printf "$w" "$i")"
  mkdir -p "$w"
  cp "$D/reactant.xyz" "$w/start.xyz"
  # 🟢 [independently verified, not from memory: `seed=<N>` in the $md xcontrol block IS a
  # real xtb keyword -- ran it directly against this project's own vendored xtb 6.7.1, two
  # different seed values produced DIFFERENT trajectories/Etot, confirmed by diff, not assumed]
  cat > "$w/md.inp" <<EOF
\$md
   temp=${TEMP_K}
   time=${TIME_PS}
   step=0.5
   dump=100.0
   hmass=4
   shake=0
   nvt=true
   seed=${i}
\$end
EOF
  echo "$w" >> "$D/tasks.txt"
done

cat > "$D/run_seed.sh" <<'EOS'
#!/bin/bash
W="$1"; CHARGE="$2"; UHF="$3"
t0=$(date +%s)
cd "$W" || exit 1
# 🟢 [ADR-110's xtb rule, explicit per-task cores -- 1 thread, matching the dev-box anchor
# this project's own §39.42(d) wall-time figure (0.54h/100ps) was measured against; never
# whole-node/None]
OMP_NUM_THREADS=1 "${SEI_XTB}" start.xyz --gfn 2 --chrg "$CHARGE" --uhf "$UHF" \
    --input md.inp --md -P 1 > md.out 2>&1
rc=$?
t1=$(date +%s)
normal=false
grep -qi "normal termination of xtb" md.out 2>/dev/null && normal=true
cat > result.json <<EOF
{"dir": "$W", "wall_s": $((t1-t0)), "cores": 1, "rc": $rc, "normal_termination": $normal}
EOF
EOS
chmod +x "$D/run_seed.sh"

sei_stage stage0_seeds bash -c \
  "xargs -a '$D/tasks.txt' -P $NP -I{} '$D/run_seed.sh' {} '$CHARGE' '$UHF'"

# --- collect + target-blind graph-diff classification, checkpoints at 25/50/100 ps ---
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$TIME_PS" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import xyzgraph

d, time_ps = sys.argv[1], float(sys.argv[2])
CHECKPOINTS_PS = (25.0, 50.0, min(100.0, time_ps))

def bonds_at(atoms):
    # 🟢 default include_ionic=False (xyzgraph.bond_list's own default) -- Li-O coordination
    # is deliberately NOT counted as a bond here, so "fragments" means COVALENTLY connected
    # pieces (matching T1-T4's own definitions: ring-opening/C2H4-elimination/CO-release are
    # all covalent-bond events). Verified directly: the reactant itself reports as 3 fragments
    # (two EC rings + Li) under this convention, held together only by ionic Li-O contacts --
    # exactly the expected starting state, not a bug.
    return set(xyzgraph.bond_list(atoms))

def fragments_at(atoms, bonds):
    comps = xyzgraph.connected_components(len(atoms), bonds)
    return sorted(xyzgraph.formula(atoms, c) for c in comps)

seeds_dir = os.path.join(d, "seeds")
per_seed = []
for name in sorted(os.listdir(seeds_dir)) if os.path.isdir(seeds_dir) else []:
    w = os.path.join(seeds_dir, name)
    result_path = os.path.join(w, "result.json")
    try:
        result = json.load(open(result_path))
    except (OSError, ValueError):
        # 🔴 [standing rule 7] a died seed gets an explicit failure marker, never a silent gap.
        per_seed.append({"seed": name, "rc": -1, "normal_termination": False,
                         "note": "result.json missing -- this seed's task died"})
        continue
    trj_path = os.path.join(w, "xtb.trj")
    events = []
    reactant_bonds = None
    reactant_fragments = None
    first_change_ps = None
    if os.path.exists(trj_path):
        with open(trj_path, errors="replace") as fh:
            frames = xyzgraph.read_xyz_frames(fh.read())
        # dump=100.0 fs => one frame per 0.1 ps, frame 0 is the starting geometry itself.
        dump_ps = 0.1
        for idx, (comment, atoms) in enumerate(frames):
            b = bonds_at(atoms)
            frags = fragments_at(atoms, b)
            if reactant_bonds is None:
                reactant_bonds = b
                reactant_fragments = frags
                continue
            broken = sorted(reactant_bonds - b)
            formed = sorted(b - reactant_bonds)
            if (broken or formed) and first_change_ps is None:
                first_change_ps = round(idx * dump_ps, 3)
            if broken or formed or frags != reactant_fragments:
                events.append({
                    "frame": idx, "arc_ps": round(idx * dump_ps, 3),
                    "bonds_broken_vs_reactant": broken, "bonds_formed_vs_reactant": formed,
                    "fragments": frags,
                })
    checkpoint_recall = {}
    for cp in CHECKPOINTS_PS:
        checkpoint_recall["%gps" % cp] = (
            first_change_ps is not None and first_change_ps <= cp)
    per_seed.append({
        "seed": name, "rc": result.get("rc"),
        "normal_termination": result.get("normal_termination"),
        "wall_s": result.get("wall_s"),
        "reactant_fragments": reactant_fragments,
        "first_bond_change_ps": first_change_ps,
        "checkpoint_recall_any_change": checkpoint_recall,
        "n_distinct_event_frames": len(events),
        "events": events,
        "_target_blind_note": ("bond/fragment changes relative to the reactant's OWN starting "
                               "graph -- NOT matched against the sealed T1-T4 target list "
                               "(that file does not exist in this project's committed files "
                               "yet, §39.40(e)'s BLINDNESS requirement -- matching is a "
                               "follow-up read, not this script's job)"),
    })

n_normal = sum(1 for s in per_seed if s.get("normal_termination"))
summary = {
    "purpose": "Stage 0 -- MTD-pilot comparator, 12 seeds x 100 ps unbiased NVT xtb MD at "
              "1500K (§39.40(d)-RESULT/§39.47(b)) -- target-blind graph-diff classification "
              "only; matching against the sealed T1-T4 list is a separate, later read.",
    "n_seeds_requested": len(per_seed), "n_seeds_normal_termination": n_normal,
    "checkpoints_ps": list(CHECKPOINTS_PS),
    "per_seed": per_seed,
}
json.dump(summary, open(os.path.join(d, "stage0_result.json"), "w"),
          ensure_ascii=False, indent=1)
print("[stage0] seeds: %d, normal termination: %d" % (len(per_seed), n_normal))
if n_normal < len(per_seed):
    print("[stage0] 🔴 %d seed(s) did not report normal termination -- read stage0_result.json "
          "before trusting any recall figure" % (len(per_seed) - n_normal))
PY
