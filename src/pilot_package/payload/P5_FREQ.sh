#!/bin/bash
# P5_FREQ — P5 freq-only RECOVERY: one Hessian per stored converged P5 geometry.
#
# [§39.74/§39.78] P5's freq half died on the EpsInf sentinel (20/20); u_cheap's denominator is
# EMPTY until a Hessian exists per row. [§39.89] the stored optimisations are NOT repeated --
# re-optimising would spend the opt budget again and destroy the C-9 audit value.
# [§39.103 proposer8 / §R39.65 engineer9] per row: `freq` at the row's own level, production
# deck (acetone, nosymm, UltraFine), cores_per_task=64 (round 1's basis). Outputs per row:
#   n_imag (C-9 audit), point group of the stored geometry, the freq job's Cartesian forces
#   vs THAT ROW's own final optimisation forces (never a threshold), ZPE/thermal (UNCERTIFIED),
#   u_freq core-h. Convicted symmetry-trapped rows (criteria/p5.GEOMETRY_REFUSED_TAGS) run
#   for u_freq only -- chemistry refused. Rows with no converged geometry are SKIPPED with
#   cause (the input does not exist; a longer wall is the wrong fix).
# 🔴 array: one row = one task (SEI_ARRAY_TASK_ID), rows from config/p5_freq_recovery.json.
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
TID="${SEI_ARRAY_TASK_ID:-}"
SFX="${SEI_TASK_FILE_SUFFIX:-}"
P5_DIR="${SEI_P5_SOURCE_DIR:-${SEI_WORKDIR}/jobs/P5}"

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  echo "[P5_FREQ] QC 코드를 쓸 수 없다 → 생략 (${SEI_QC_DETAIL:-미상})"
  sei_terminal "skipped" "no QC engine available" "task=${TID:-all}"
  exit 3
fi
sei_qc_smoke > "$D/smoke_result${SFX}.txt" 2>&1 || {
  echo "[P5_FREQ] route smoke 실패 → 중단"; sei_terminal "route_smoke_failed" "see smoke_result${SFX}.txt" "task=${TID:-all}"; exit 4; }

mkdir -p "$D/rows"
# --- row selection + stored-geometry extraction (one python, writes row${SFX}.json) ----------
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$TID" "$SFX" "$P5_DIR" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import config
from sei_pilot.criteria import g16, p5
d, tid, sfx, p5_dir = sys.argv[1:5]
cfg = config.load("p5_freq_recovery.json", {})
rows = cfg.get("rows") or []
sel = rows if not tid else ([rows[int(tid) - 1]] if 1 <= int(tid) <= len(rows) else [])
if not sel:
    sys.stderr.write("array index %s outside 1..%d\n" % (tid, len(rows)))
    sys.exit(5)
out = []
for r in sel:
    tag = r["tag"]
    w = os.path.join(d, "rows", tag)
    os.makedirs(w, exist_ok=True)
    log = os.path.join(p5_dir, "species", tag, "job.log")
    rec = dict(r, stored_log=log, geometry_refused=p5.geometry_refused(tag))
    try:
        text = open(log, errors="replace").read()
    except OSError:
        text = ""
    s = g16.summarize(text)
    geom = g16.last_geometry(text) if text else None
    if not (s["opt"]["converged"] and geom):
        rec.update(status="skipped", reason="no_converged_geometry",
                   cause="opt_unconverged" if text else "stored_log_missing",
                   _note="[§39.103(3)] the input does not exist -- NOT an EpsInf casualty; "
                         "U-55 floppy-PES, prescription is conformer quality, not a longer wall")
        out.append(rec); continue
    with open(os.path.join(w, "mol.xyz"), "w") as fh:
        fh.write("%d\nstored P5 geometry %s (from %s)\n" % (len(geom), tag, log))
        fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
    rec.update(status="ready",
               stored_point_group=g16.parse_point_group(text),
               stored_final_forces=g16.parse_cartesian_forces(text),
               stored_route_echoed=s.get("route_echoed"),
               stored_scf_energy_hartree=(s.get("scf") or {}).get("final_energy_hartree"))
    out.append(rec)
json.dump(out, open(os.path.join(d, "row%s.json" % sfx), "w"), ensure_ascii=False, indent=1)
PY
then
  echo "[P5_FREQ] row selection failed"; sei_terminal "input_error" "row selection failed" "task=${TID:-all}"; exit 5
fi

# --- run the Hessian for each ready row ----------------------------------------------------
_logs=()
while IFS=$'\t' read -r tag status lvl chg mult; do
  [ -z "${tag:-}" ] && continue
  w="$D/rows/$tag"
  if [ "$status" != "ready" ]; then
    echo "[P5_FREQ] $tag: skipped (no converged geometry)"; continue
  fi
  echo "[P5_FREQ] === $tag (level $lvl, q=$chg, m=$mult) ==="
  sei_qc_input "$w/job.gjf" "$lvl" freq "$chg" "$mult" "$w/mol.xyz" > "$w/meta.json" 2>"$w/meta.err" \
    || { echo "  ! input generation failed"; cat "$w/meta.err"; continue; }
  sei_stage "p5freq_${tag}" sei_qc_run "$w" job.gjf job.log
  _logs+=("$w/job.log")
done < <(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import json, sys
for r in json.load(open(sys.argv[1])):
    print("\t".join([r["tag"], r["status"], str(r["level"]), str(r["charge"]), str(r["multiplicity"])]))
' "$D/row${SFX}.json")

# --- per-row readout (p5_freq_task_results${SFX}.json) --------------------------------------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$SFX" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import units
from sei_pilot.criteria import g16
d, sfx = sys.argv[1:3]
rows = json.load(open(os.path.join(d, "row%s.json" % sfx)))
out = []
for r in rows:
    if r["status"] != "ready":
        out.append(r); continue
    tag = r["tag"]; w = os.path.join(d, "rows", tag)
    try:
        text = open(os.path.join(w, "job.log"), errors="replace").read()
    except OSError:
        text = ""
    s = g16.summarize(text)
    try:
        st = json.load(open(os.path.join(d, "stages", "p5freq_%s.json" % tag)))
        u_freq = units.core_hours(st.get("total_cores", 1), st.get("wall_s", 0))
    except (OSError, ValueError):
        u_freq = None
    freqs = g16.parse_frequencies(text)
    forces = g16.parse_cartesian_forces(text)
    ref = r.get("stored_final_forces") or {}
    # [§39.97(b)] forces vs THAT ROW's own final optimisation forces -- no threshold here;
    # the ratio is the datum, the reader judges. Three deck variables changed at once
    # (solvent generic->acetone, grid default->UltraFine, symmetry on->nosymm), so a
    # disagreement says "something in the deck moved the gradient", not which thing.
    force_ratio = (forces["max_hartree_per_bohr"] / ref["max_hartree_per_bohr"]
                   if forces and ref.get("max_hartree_per_bohr") else None)
    refused = bool(r.get("geometry_refused"))
    # [§39.108(a)] a SEPARATE flag from `geometry_refused` -- conviction is a chemistry claim
    # about the STRUCTURE; this is a cost claim about the OPTIMISATION that produced u_opt.
    # §39.100(b) measured a symmetry-constrained opt runs cheap by |G| (4.38x C2V order-4,
    # 2.07x CS order-2, n=2) -- the FACTOR is not yet known (pending the §39.107 calibration
    # probes), so this records the BIAS, never an invented correction.
    stored_pg = r.get("stored_point_group")
    if stored_pg is None:
        sym_biased, sym_note = None, "unknown: stored point group not parsed"
    elif stored_pg == "C1":
        sym_biased, sym_note = False, "C1 stored geometry -- u_opt not symmetry-saved"
    else:
        sym_biased = True
        sym_note = ("u_opt ran in point group %s -- SYMMETRY-CONSTRAINED, biased LOW by an "
                    "unmeasured factor (§39.100(b) hypothesis |G|=2-8, pending §39.107 probes). "
                    "Blocks u_opt/u_cheap for SIZING; does not block u_freq (this row's freq "
                    "runs nosymm, no saving inherited)." % stored_pg)
    # [§39.108(b)] record every imaginary frequency's VALUE and the qualitative reading rule
    # WITH the data -- no magnitude threshold invented here (same emit-only shape as Omega,
    # §3): these geometries are converged to DEFAULT tolerance (max force 4.5e-4, 30x looser
    # than tight/§39.105), so a small residual gradient can push a soft mode through zero in
    # either direction.
    imag_freqs = [f for f in freqs if f < 0] if freqs else []
    n_imag = len(imag_freqs) if freqs else None
    n_imag_rule = ("n_imag>0 with a LARGE |v_imag| -> trapping, high confidence. "
                  "n_imag>0 with a SMALL |v_imag| -> INDETERMINATE, not evidence of trapping "
                  "(residual gradient at DEFAULT convergence can manufacture or hide a soft "
                  "mode). n_imag==0 -> WEAKER evidence of 'not trapped' than the converse is "
                  "of 'trapped' -- the same residual can MASK a small imaginary mode. No "
                  "|v_imag| cutoff is defined; read the values themselves.")
    # [§39.108(d)] production deck carries nosymm -> G16 should report C1 for EVERY row
    # regardless of the stored geometry's own symmetry. This field VERIFIES THE KEYWORD TOOK
    # EFFECT; it is not a molecular datum and must not be compared against stored_point_group
    # as though the two described the same thing (one verifies a keyword, one describes a
    # structure that may legitimately be symmetric).
    freq_pg = g16.parse_point_group(text)
    nosymm_verified = None if freq_pg is None else (freq_pg == "C1")
    rec = dict(r)
    rec.update({
        "normal_termination": s["normal_termination"],
        "error_termination": "Error termination" in text,
        "stages_completed": g16.stages_completed(text, s.get("route_echoed")),
        "route_echoed": s.get("route_echoed"),
        "u_freq_core_h": round(u_freq, 5) if u_freq is not None else None,
        "n_imag": n_imag,
        "frequencies_cm1": freqs,
        "imaginary_frequencies_cm1": imag_freqs,
        "n_imag_interpretation_rule": n_imag_rule,
        "freq_point_group": freq_pg,
        "nosymm_verified": nosymm_verified,
        "nosymm_verified_note": ("verifies the `nosymm` KEYWORD took effect (expect C1 on every "
                                 "row regardless of geometry) -- NOT comparable to "
                                 "stored_point_group, which describes the molecule"),
        "freq_forces": forces,
        "force_max_ratio_freq_over_stored_opt": force_ratio,
        "force_check": ("not_measured" if force_ratio is None else "recorded -- joint test of "
                        "solvent+grid+symmetry; read per §39.103(4), do not threshold here"),
        "thermo_hartree": g16.parse_zpe_and_thermal(text),
        "free_energy_hartree": g16.parse_free_energy(text),
        "u_opt_symmetry_biased": sym_biased,
        "u_opt_symmetry_biased_note": sym_note,
        # [§39.82(b)] chemistry is UNCERTIFIED by default; lead collapses it, never code.
        "chemical_outputs_status": ("REFUSED: geometry symmetry-trapped (§39.98/§39.100) -- "
                                    "u_freq is a valid cost datum, every chemical output is not"
                                    if refused else
                                    "UNCERTIFIED (§39.82(b)): computed on a stored geometry "
                                    "optimised under a different deck; n_imag here is the C-9 "
                                    "audit datum, ZPE/thermal are not yet certified"),
        "n_imag_role": ("informational -- row already convicted by energy/geometry; the remedy "
                        "is a C1 re-optimisation (§39.98(d))" if refused else "C-9 audit datum"),
        "u_cheap_eligibility": ("EXCLUDED: u_opt_from_trapped_geometry (symmetry-constrained opt "
                                "biased low, §39.100(b)); u_freq alone is clean" if refused else
                                "eligible for ASSEMBLY, but u_opt_symmetry_biased -- see note, not "
                                "usable for SIZING until §39.107's probes correct it" if sym_biased
                                else "eligible: assemble u_opt (round 1) + u_freq (this round)"),
    })
    out.append(rec)
json.dump({"rows": out, "_provenance": {"deck": "production (acetone, nosymm, UltraFine)",
           "source": "stored P5 geometries, round 1; opt NOT repeated (§39.89)"}},
          open(os.path.join(d, "p5_freq_task_results%s.json" % sfx), "w"),
          ensure_ascii=False, indent=1)
print("[P5_FREQ] rows:", len(out), "ready:", sum(1 for r in out if r["status"] == "ready"),
      "n_imag==0:", sum(1 for r in out if r.get("n_imag") == 0))
PY

# [§39.80(g)(i)] terminal status from the Hessian logs themselves (skipped rows carry no log)
if [ "${#_logs[@]}" -eq 0 ]; then
  sei_terminal "skipped" "no row in this task had a converged stored geometry" "task=${TID:-all}"
else
  sei_terminal_from_logs "task=${TID:-all}" -- "${_logs[@]}"
fi
exit 0
