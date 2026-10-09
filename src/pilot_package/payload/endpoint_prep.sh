#!/bin/bash
# endpoint_prep.sh — ADR-099 two-stage endpoint preparation, ONE endpoint per PBS job.
#   STAGE 1  endpoint_opt_rough  -- cheap, get into the basin
#   STAGE 2  endpoint_opt_freq   -- tight opt + freq FROM stage 1's converged geometry,
#                                   the C-8/C-8.1-8.3 certification
# Two of these jobs run in PARALLEL per attempt (one per endpoint: reactant, product) --
# see config/qc_levels.json's `_endpoint_two_stage`. The stage1->stage2 handoff inside THIS
# script is a file read, not a resource request, so it is 2 jobs total, not 3.
#
# 🔴 C-9's out-of-plane perturbation is applied ONCE, HERE, BEFORE stage 1 -- not between the
#    stages, and is NOT re-applied at stage 2 (ADR-099). Re-kicking a geometry stage 1 already
#    converged would displace it off a real minimum -- if stage-1 exit is STILL on the element
#    despite the kick (i.e. nosymm was lost, B-2), the correct response is stage 2's OWN CalcFC
#    imaginary eigenvector, a MEASURED direction, not another random kick (not automated here --
#    see this package's C-8 escalation; the diagnosis is emitted so it CAN be acted on).
#
# 🔴 `nosymm` is carried by BOTH job_type route templates (config/qc_levels.json's
#    `_nosymm_required_job_types`) -- it, not same-vs-cheaper level, is what actually prevents
#    a symmetric stage 1 from silently certifying the wrong structure. With `nosymm` + CalcFC +
#    an honest freq at stage 2, a structure still on the symmetry element gives n_imag >= 1 and
#    C-8.3 blocks it -- a symmetric stage 1 costs a restart at TIGHT price, not correctness.
#    `nosymm` is still required on stage 1 too, because: (i) the failure is silent only if
#    `nosymm` is missing on BOTH stages, and stage 1 is far the easier one to forget -- "it's
#    only a rough opt" is exactly the sentence that omits it; (ii) perturbing late throws away
#    stage 1's work, re-doing it inside stage 2 at tight thresholds; (iii) without `nosymm` on
#    stage 1, G16 undoes the perturbation at step 1 (B-2) -- so it may as well not exist.
#
# ✅ Q2 RULED (proposer6, §39.38): rough runs at the SAME functional/basis/solvent/grid as
#    tight -- ONLY the convergence thresholds move. A cheaper rough surface can order
#    near-degenerate coordination isomers (U-55) differently; stage 1 would then SELECT a
#    basin on the wrong surface and stage 2 would certify honestly INSIDE it -- n_imag==0
#    true, every internal check consistent, the wrong-minimum error invisible to all of them.
#    See qc_levels.json `_endpoint_two_stage._rough_level_status` for the full rationale.
#
# 🔴 Opt=Loose/Opt=Tight's NUMERIC thresholds are never hardcoded anywhere in this package --
#    G16 selects them from the keyword and prints the ACTIVE criteria in its own log. Do not
#    let a documentation number in through that gap (this script only ever passes the keyword).
#
# 🔴 A wall-clock abort during EITHER stage is an EXECUTION fact and is NEVER recorded as
#    `non_converged` (a CHEMICAL fact) -- C-2's principle, a fourth instance. The two abort
#    tokens (`stage1_budget_exhausted` / `stage2_budget_exhausted`) are kept distinct so a
#    reader can tell which internal stage was running at kill.
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
NP="${SEI_TOTAL_CORES:-1}"
CHARGE=0
MULT=2      # reduced radical (doublet), same species as payload/P1.sh
SEED="${SEI_ENDPOINT_SEED:-1}"
BUDGET_H="${SEI_ENDPOINT_BUDGET_H:-6.0}"
BUDGET_CORE_H="${SEI_ENDPOINT_BUDGET_CORE_H:-384.0}"
ROLE="${SEI_ENDPOINT_ROLE:-}"

_write_terminal() {
  # $1=status  $2=note  -- [§39.80(g)(i)] cause_class comes from sei_pilot/outcome.py
  sei_terminal "$1" "$2" "role=${ROLE}" "budget_h=${BUDGET_H}" "budget_core_h=${BUDGET_CORE_H}"
}

case "$ROLE" in
  reactant) SRC="${SEI_PKG_ROOT}/inputs/li_ec_radical_reactant.xyz" ;;
  product)  SRC="${SEI_PKG_ROOT}/inputs/li_ec_radical_product.xyz" ;;
  *)
    echo "[endpoint_prep] SEI_ENDPOINT_ROLE=reactant|product 가 필요하다 (받은 값: '${ROLE}')"
    _write_terminal "input_error" "SEI_ENDPOINT_ROLE must be reactant or product"
    exit 2 ;;
esac
# 🔴 [U56-2/ADR-109] 입력 기하 override — R-C reactant(li_ec2_radical, 21원자)의 기하는
#    패키지에 실려 있지 않다(arm 1 MTD 산출물이 공급한다; tests/test_b0_definitions.py 의
#    "built by the pipeline, not shipped"). 항목(plan.py)이 이 채널로 경로를 선언하고,
#    파일이 없으면 **구분된 상태로 시끄럽게 거부**한다 — 11원자 기하를 21원자 종에
#    대신 쓰거나 기하를 지어 넣는 것이 이 프로젝트가 계속 대가를 치른 실패 모양이다.
if [ -n "${SEI_ENDPOINT_INPUT_XYZ:-}" ]; then
  case "${SEI_ENDPOINT_INPUT_XYZ}" in
    /*) SRC="${SEI_ENDPOINT_INPUT_XYZ}" ;;
    *)  SRC="${SEI_PKG_ROOT}/${SEI_ENDPOINT_INPUT_XYZ}" ;;   # 상대경로는 패키지 기준
  esac
fi
if [ ! -f "${SRC}" ]; then
  echo "[endpoint_prep] 🔴 입력 기하가 없다: ${SRC}"
  echo "     (SEI_ENDPOINT_INPUT_XYZ 로 지정된 파일이 아직 만들어지지 않았다면, 이 항목은"
  echo "      그 공급 단계가 끝난 뒤에만 돌 수 있다 — 0 core-h 로 거부한다.)"
  _write_terminal "input_missing" "input geometry not found: ${SRC}"
  exit 2
fi
# 🔴 [§39.41 / lead 2026-08-20] 이중 시작점: packaged guess 가 GFN2 실측으로 0.59 eV
#    위 basin 인 사례(R-A product)가 나왔다 — ALT 시작점이 선언되면 stage 1 을 **둘 다**
#    돌리고 낮은 basin 을 stage 2(인증)에 넘긴다. 선언됐는데 파일이 없으면 조용히
#    한쪽만 돌지 않고 거부한다(반쪽 실행이 '이중 시작점 검사 통과'로 오독된다).
ALT_SRC=""
if [ -n "${SEI_ENDPOINT_ALT_INPUT_XYZ:-}" ]; then
  case "${SEI_ENDPOINT_ALT_INPUT_XYZ}" in
    /*) ALT_SRC="${SEI_ENDPOINT_ALT_INPUT_XYZ}" ;;
    *)  ALT_SRC="${SEI_PKG_ROOT}/${SEI_ENDPOINT_ALT_INPUT_XYZ}" ;;
  esac
  if [ ! -f "${ALT_SRC}" ]; then
    echo "[endpoint_prep] 🔴 ALT 입력 기하가 선언됐는데 없다: ${ALT_SRC}"
    _write_terminal "input_missing" "declared ALT input geometry not found: ${ALT_SRC}"
    exit 2
  fi
fi
# 입력 기하의 provenance sidecar(<입력>.provenance.json — §39.42(a) 다중 seed 프로토콜
# 기록 등)가 있으면 결과 옆으로 복사한다: collector 가 회신에 싣는다.
for _side in "${SRC%.xyz}.provenance.json" "${ALT_SRC:+${ALT_SRC%.xyz}.provenance.json}"; do
  [ -n "${_side}" ] && [ -f "${_side}" ] && \
    cp "${_side}" "$D/input_provenance.$(basename "${_side}")" 2>/dev/null
done

# --- LEVEL: ✅ RULED (Q2, proposer6 §39.38) -- rough runs at the SAME level as tight; only
# the convergence thresholds move (opt=loose,maxcycles=100 vs opt=tight,calcfc,maxcycles=200 --
# see the two route TEMPLATES in qc_levels.json's job_types, not a branch here). No separate
# rough_level config key exists; there is nothing left to be pending on. ---------------------
TIGHT_LEVEL="${SEI_ENDPOINT_TIGHT_LEVEL:-3}"   # level3, the production geometry layer (SETTLED, §39.32(c))
ROUGH_LEVEL="$TIGHT_LEVEL"

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  echo "[endpoint_prep] QC 코드를 쓸 수 없다 → 생략. 사유: ${SEI_QC_DETAIL:-(미상)}"
  _write_terminal "skipped" "no QC engine available (${SEI_QC_DETAIL:-unknown})"
  exit 3
fi

# --- route smoke: 다른 payload 와 같은 preflight (P-0/S-1 이후 특히 중요하다 — ---------
# --- smoke 가 ε 실증(deck_verification)을 만들고, 그것이 아래 precheck 와 본계산의 ---
# --- pcm 게이트를 연다. smoke 없이는 pcm_numeric 아래에서 이 항목이 영구 거부다.) ---
if ! sei_qc_smoke > "$D/smoke_result.txt" 2>&1; then
  echo "[endpoint_prep] route smoke 실패 → 본계산을 돌리지 않는다:"
  tail -15 "$D/smoke_result.txt"
  _write_terminal "route_smoke_failed" "sei_qc_smoke failed (deck/route not validated)"
  exit 4
fi

# --- C-5 PRECHECK: refuse before spending a single core-h on the wrong solvent. -------------
# 🔴 [ADR-105 wired] `sei_qc_input` 은 이제 `solvent.resolve_solvent_line()`(단일 결정
#    지점)을 통과한다 — 이 precheck 는 **같은 함수**를 미리 물어 stage 1 제출 전에
#    구분된 terminal_status 로 멈추기 위한 것이다(같은 결정의 조기 조회이지, ADR-105 가
#    금지한 'payload 마다 복사된 두 번째 precheck 규칙'이 아니다 — 규칙은 한 곳에 있다).
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
  echo "[endpoint_prep] 🔴 C-5: EC:EMC SMD descriptors 가 없다 -- acetonitrile 로 대체하지 않는다."
  cat "$D/solvent_precheck.err"
  _write_terminal "solvent_descriptors_missing" "C-5 refuses to proceed with acetonitrile"
  exit 4
elif [ ${_rc} -ne 0 ]; then
  echo "[endpoint_prep] 🔴 C-5: 용매 결정이 없다(solvent_policy 미결정) -- 어떤 덱도 내지 않는다."
  cat "$D/solvent_precheck.err"
  _write_terminal "solvent_refused" "C-5: no solvent decision reached this deck (solvent_policy unset)"
  exit 4
fi

# --- C-9: perturb the guess out of plane, ONCE, before stage 1. -----------------------------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$SRC" "$D/guess.xyz" "$D/perturbation_provenance.json" "$SEED" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import xyzgraph
src, out_xyz, out_prov, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
atoms = xyzgraph.read_xyz_frames(open(src, errors="replace").read())[0][1]
kicked, prov = guards.perturb_out_of_plane(atoms, seed=seed)
with open(out_xyz, "w") as fh:
    fh.write("%d\nADR-099 perturbed guess (seed=%d)\n" % (len(kicked), seed))
    fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in kicked))
json.dump(prov, open(out_prov, "w"), ensure_ascii=False, indent=1, default=str)
PY

# --- (이중 시작점) ALT guess 에도 같은 C-9 perturbation, 같은 seed. --------------------------
if [ -n "${ALT_SRC}" ]; then
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$ALT_SRC" "$D/guess_alt.xyz" "$D/perturbation_provenance_alt.json" "$SEED" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import xyzgraph
src, out_xyz, out_prov, seed = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
atoms = xyzgraph.read_xyz_frames(open(src, errors="replace").read())[0][1]
kicked, prov = guards.perturb_out_of_plane(atoms, seed=seed)
with open(out_xyz, "w") as fh:
    fh.write("%d\nADR-099 perturbed ALT guess (seed=%d)\n" % (len(kicked), seed))
    fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in kicked))
json.dump(prov, open(out_prov, "w"), ensure_ascii=False, indent=1, default=str)
PY
fi

# --- STAGE 1: rough / loose optimisation. ----------------------------------------------------
sei_qc_input "$D/endpoint_rough.gjf" "$ROUGH_LEVEL" endpoint_opt_rough "$CHARGE" "$MULT" \
  "$D/guess.xyz" > "$D/endpoint_rough.meta.json" 2>"$D/endpoint_rough.meta.err"
if [ $? -ne 0 ]; then
  echo "[endpoint_prep] stage 1 입력 생성 실패:"; cat "$D/endpoint_rough.meta.err"
  _write_terminal "input_error" "stage 1 (rough) input generation failed"
  exit 5
fi
# 🔴 [A-1f] stage 이름에 role 을 넣는다 (P6.sh 의 `anchor_t${NP}` 패턴). 지금은 role 이
#    reactant 하나지만, product 끝단이 이미 다음 스코프다 — role 없는 고정 이름인 채로
#    두 role 을 한 array 로 합치면 P1b/P5 와 같은 마커 충돌(12번째 인스턴스)이 된다.
# 🔒 그리고 product 를 추가할 때는 **array 로 합치지 마라. P6_t1/t16/t64 처럼 별도
#    Item 2개로 내라.** 이유는 plan.py:317-323 에 이미 적혀 있다: "항목 N개면
#    계획·사전검사·제출·emit·회신이 기존 경로를 그대로 타고 새 분기가 0" — 이 프로젝트가
#    이미 도달한 결론이다. (lead 지시, A-1f)
sei_stage "endpoint_rough_${SEI_ENDPOINT_ROLE}" sei_qc_run "$D" endpoint_rough.gjf endpoint_rough.log

# --- (이중 시작점) STAGE 1-ALT: 같은 route, ALT guess. 낮은 basin 이 stage 2 로 간다. --------
if [ -n "${ALT_SRC}" ]; then
  sei_qc_input "$D/endpoint_rough_alt.gjf" "$ROUGH_LEVEL" endpoint_opt_rough "$CHARGE" "$MULT" \
    "$D/guess_alt.xyz" > "$D/endpoint_rough_alt.meta.json" 2>"$D/endpoint_rough_alt.meta.err"
  if [ $? -ne 0 ]; then
    echo "[endpoint_prep] stage 1-ALT 입력 생성 실패:"; cat "$D/endpoint_rough_alt.meta.err"
    _write_terminal "input_error" "stage 1 (rough, ALT start) input generation failed"
    exit 5
  fi
  sei_stage "endpoint_rough_alt_${SEI_ENDPOINT_ROLE}" sei_qc_run "$D" endpoint_rough_alt.gjf endpoint_rough_alt.log
fi

# --- BUDGET CHECK after stage 1. Do not start stage 2 on too little remaining budget. --------
STAGE1_CORE_H="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import cost
print(cost.total_core_hours(cost.read_stage_records(os.environ["SEI_JOB_DIR"])))')"
if PYTHONPATH="${SEI_PKG_ROOT}" python3 -c "
import sys
core_h, budget = float('${STAGE1_CORE_H}'), ${BUDGET_CORE_H}
sys.exit(0 if core_h >= budget else 1)"; then
  echo "[endpoint_prep] 🔴 stage 1 만으로 예산(${BUDGET_CORE_H} core-h)을 소진했다 -- stage 2 를 시작하지 않는다."
  _write_terminal "stage1_budget_exhausted" "cumulative core-h ${STAGE1_CORE_H} >= budget ${BUDGET_CORE_H} after stage 1"
  exit 7
fi

# --- Stage-1 exit: (이중 시작점이면) 낮은 basin 선택 + FREE F1 structural set. ----------------
# 🔴 선택은 같은 route/레벨의 stage-1 수렴 에너지 비교다 — 두 후보가 같은 표면 위에
#    있으므로 비교 가능(§39.38(b)). 선택 기록(start_selection.json)은 항상 남는다.
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/endpoint_rough.log" "${ALT_SRC:+$D/endpoint_rough_alt.log}" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import units
from sei_pilot.criteria import g16, f1_endpoint as f1

d = os.environ["SEI_JOB_DIR"]
logs = [("packaged", sys.argv[1])]
if len(sys.argv) > 2 and sys.argv[2]:
    logs.append(("alt_scan_open", sys.argv[2]))

cands = []
for label, log in logs:
    try:
        text = open(log, errors="replace").read()
    except OSError:
        text = ""
    geom = g16.last_geometry(text)
    e = g16.parse_scf(text)["final_energy_hartree"]
    cands.append({"start": label, "log": os.path.basename(log),
                  "final_scf_hartree": e, "has_geometry": bool(geom),
                  "_geom": geom})

usable = [c for c in cands if c["has_geometry"] and c["final_scf_hartree"] is not None]
selection = {
    "candidates": [dict((k, v) for k, v in c.items() if k != "_geom") for c in cands],
    "n_starts": len(cands),
    "selected": None,
    "delta_ev_between_starts": None,
    "_rule": ("이중 시작점(§39.41, 0.59 eV basin 사례): 같은 stage-1 route 의 수렴 "
              "에너지가 낮은 쪽이 stage 2(인증)로 간다. 단일 시작점이면 그대로 통과."),
}
if len(usable) == 2:
    e0, e1 = usable[0]["final_scf_hartree"], usable[1]["final_scf_hartree"]
    selection["delta_ev_between_starts"] = round(abs(units.hartree_to_ev(e0 - e1)), 4)
chosen = min(usable, key=lambda c: c["final_scf_hartree"]) if usable else None
if chosen:
    selection["selected"] = chosen["start"]
    with open(os.path.join(d, "stage1_exit.xyz"), "w") as fh:
        fh.write("%d\nstage 1 exit (start=%s)\n" % (len(chosen["_geom"]), chosen["start"]))
        fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in chosen["_geom"]))
    json.dump(f1.stage1_exit_structural_set(chosen["_geom"]),
              open(os.path.join(d, "stage1_exit_structural_set.json"), "w"),
              ensure_ascii=False, indent=1, default=str)
else:
    json.dump({"reason": "no stage-1 candidate produced a usable geometry+energy -- "
                         "stage 1 did not run or did not converge on any start"},
              open(os.path.join(d, "stage1_exit_structural_set.json"), "w"))
json.dump(selection, open(os.path.join(d, "start_selection.json"), "w"),
          ensure_ascii=False, indent=1)
PY
if [ ! -f "$D/stage1_exit.xyz" ]; then
  echo "[endpoint_prep] stage 1 기하 추출 실패 (수렴하지 않았을 수 있다) -- stage 2 생략."
  _write_terminal "not_converged" "stage 1 produced no usable geometry"
  exit 0
fi

# --- STAGE 2: tight opt + freq from stage 1's converged geometry -- the certification. -------
sei_qc_input "$D/endpoint_tight.gjf" "$TIGHT_LEVEL" endpoint_opt_freq "$CHARGE" "$MULT" \
  "$D/stage1_exit.xyz" > "$D/endpoint_tight.meta.json" 2>"$D/endpoint_tight.meta.err"
if [ $? -ne 0 ]; then
  echo "[endpoint_prep] stage 2 입력 생성 실패:"; cat "$D/endpoint_tight.meta.err"
  _write_terminal "input_error" "stage 2 (tight) input generation failed"
  exit 5
fi
sei_stage "endpoint_tight_${SEI_ENDPOINT_ROLE}" sei_qc_run "$D" endpoint_tight.gjf endpoint_tight.log

# --- BUDGET CHECK after stage 2 (cumulative across BOTH stages). ----------------------------
TOTAL_CORE_H="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import cost
print(cost.total_core_hours(cost.read_stage_records(os.environ["SEI_JOB_DIR"])))')"
if PYTHONPATH="${SEI_PKG_ROOT}" python3 -c "
import sys
core_h, budget = float('${TOTAL_CORE_H}'), ${BUDGET_CORE_H}
sys.exit(0 if core_h >= budget else 1)"; then
  echo "[endpoint_prep] 🔴 stage 2 를 포함해 예산(${BUDGET_CORE_H} core-h)을 소진했다."
  _write_terminal "stage2_budget_exhausted" "cumulative core-h ${TOTAL_CORE_H} >= budget ${BUDGET_CORE_H} after stage 2"
  exit 7
fi

# --- F1 observables at convergence (angle, ring bonds, n_imag, symmetric fingerprint). -------
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/endpoint_tight.log" "$D/f1_observables.json" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16, f1_endpoint as f1
log, out_json = sys.argv[1], sys.argv[2]
try:
    text = open(log, errors="replace").read()
except OSError:
    text = ""
summ = g16.summarize(text)
geom = g16.last_geometry(text)
freqs = g16.parse_frequencies(text)
# [§39.42(a)] <S^2> — 두 stage 모두, annihilation 전/후, 숫자만 (C-3, 판정 없음).
# stage 1 은 (이중 시작점이면) 선택된 시작점의 로그를 읽는다.
sel = {}
try:
    sel = json.load(open(os.path.join(os.path.dirname(out_json),
                                      "start_selection.json")))
except (OSError, ValueError):
    sel = {}
rough_log = "endpoint_rough_alt.log" if sel.get("selected") == "alt_scan_open" \
    else "endpoint_rough.log"
try:
    rough_text = open(os.path.join(os.path.dirname(out_json), rough_log),
                      errors="replace").read()
except OSError:
    rough_text = ""
out = {
    "normal_termination": summ.get("normal_termination"),
    "opt_converged": (summ.get("opt") or {}).get("converged"),
    # 🔴 [§39.124 Ruling 1, corrected A4, critic16 B1] REQUIRED EMISSION: the converged energy
    # at THIS stage (tight opt+freq, the certification level) -- `guards.reactant_match`'s
    # energy clause needs the certified reactant's OWN energy, and before this field existed
    # there was NOWHERE for a downstream reader to get it without re-parsing this log a second
    # time from a different job's directory (critic16: "do not implement it as a cross-job log
    # grep at gate time"). Recorded here, once, at the source; U56.sh's cert resolver copies it
    # into `endpoint_certs.json`'s `reactant_cert`/`product_cert` -- never re-derived downstream.
    "energy_hartree": (summ.get("scf") or {}).get("final_energy_hartree"),
    "n_imag_at_convergence": f1.n_imaginary(freqs),
    "s2_stage1_rough": g16.parse_s2(rough_text)["last"],
    "s2_stage2_tight": g16.parse_s2(text)["last"],
    "_s2_note": ("§39.42(a) REQUIRED EMISSION: <S^2> before/after annihilation, both "
                 "stages, numbers only -- doublet 청정값 0.75, 판정은 하지 않는다 (C-3). "
                 "오염된 UKS 참조의 'endpoint' 는 인증했다고 생각한 종이 아닐 수 있다."),
    "start_selection": (dict((k, v) for k, v in sel.items() if k != "candidates")
                        if sel else None),
    "n_imag_entering_tight_stage": None,
    "_n_imag_entering_tight_stage_status": (
        "[UNVERIFIED -- not implemented] f1_required_observables.json says this is FREE from "
        "stage 2's own initial CalcFC Hessian (computed at step 1, before anything moves), but "
        "parsing G16's initial-Hessian eigenvalues out of the log (as opposed to the FINAL "
        "freq block this parser already reads) has not been verified against a real log. Do "
        "not fill this in without one."),
    "angle_li_o_c": None,
    "ring_bond_lengths": None,
    "symmetric_fingerprint_at_convergence": None,
}
if geom:
    out["angle_li_o_c"] = f1.li_o_c_angle_deg(geom)
    out["ring_bond_lengths"] = f1.ring_bond_lengths(geom)
    out["symmetric_fingerprint_at_convergence"] = f1.symmetric_fingerprint(geom)
json.dump(out, open(out_json, "w"), ensure_ascii=False, indent=1, default=str)
PY

# 🔴 [§39.80(g)(i)] THREE outcomes, not two. The EpsInf-sentinel segfault (l1110, signal 11)
#    used to be filed as `not_converged` -- a chemistry word for an engine death -- and that is
#    how a plumbing crash became a permanent, never-retried `done`. Engine death is classified
#    from the log's termination, not from the wrapper's rc.
PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import outcome
d = json.load(open(sys.argv[1]))
# 🔴 not `normal_termination`: a multi-stage log prints it after the opt half and then dies in
#    freq, so that flag reads True on the exact crash this branch exists for (§39.74).
st, _ = outcome.status_from_g16_logs([open(sys.argv[2], errors="replace").read()])
if st == "engine_failure":
    sys.exit(2)
sys.exit(0 if (d.get("opt_converged") and d.get("n_imag_at_convergence") == 0) else 1)
' "$D/f1_observables.json" "$D/endpoint_tight.log"
case $? in
  0)
    echo "[endpoint_prep] 완료 (role=${ROLE}). n_imag=0 -- C-8 인증 통과."
    _write_terminal "converged" "n_imag == 0 at the tight/freq stage, C-8.2/C-8.3 certificate"
    exit 0 ;;
  2)
    echo "[endpoint_prep] 🔴 stage 2 의 G16 이 비정상 종료했다 (role=${ROLE}) -- engine failure, 화학 판정 아님."
    _write_terminal "engine_failure" "stage 2 (tight/freq) log has no Normal termination -- engine died; no C-8 verdict"
    exit 0 ;;
  *)
    echo "[endpoint_prep] 완료했으나 인증 실패 (role=${ROLE}) -- n_imag != 0 이거나 수렴하지 않았다."
    _write_terminal "not_converged" "did not meet C-8.2/C-8.3 (n_imag == 0) at the tight/freq stage"
    exit 0 ;;
esac
