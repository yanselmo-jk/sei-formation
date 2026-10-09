#!/bin/bash
# P5 — 소분자 opt+freq **단가 곡선** (5~21원자 × 전하 −1/0/+1 × 닫힌껍질/개각), Gaussian16.
#
# 🔴 종별 원자료를 그대로 남긴다. 평균을 내지 않는다 — 곡선 적합은 받는 쪽이 한다.
# 🔴 P1과 독립이다. P1이 실패해도 P5는 돈다(서로 다른 계다).
#
# 🔴🔴 array 분기 (이번 라운드가 이것 하나로 무너졌다):
#    plan.py 는 P5 를 `array=(1,22)` 로 제출한다 — **실행 1건 = array 태스크 1개**.
#    그런데 이전 판의 이 스크립트는 태스크 index 를 읽지 않고 22개 태스크 전원이
#    전체 목록을 돌았다: 같은 tasks.tsv 를 고정 경로에 22번 `>` 로 쓰고 읽어
#    대부분 빈/부분 파일을 읽었고, species/ 는 비었고 rows 는 [] 였다.
#    ⟹ 이제 태스크 목록은 sei_pilot.plan._p5_runs() **한 곳**에서 오고(예산과 같은
#      열거 — tasks.tsv 18줄 vs 예산 22태스크 어긋남의 재발 방지), 각 태스크는
#      SEI_ARRAY_TASK_ID(=probe_throughput.sh 의 패턴, common.sh 가 계산)로
#      **자기 index 분량만** 돌린다. 태스크별 산출물은 접미사 .t<N> 으로 가른다.
set -u
# 🔴 잡 템플릿은 이 스크립트를 **새 bash 프로세스**로 띄운다 → 셸 함수는 상속되지
#    않는다. sei_stage 를 쓰려면 여기서 직접 source 해야 한다(두 번 source 해도 안전).
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
SPEC_DIR="${SEI_PKG_ROOT}/inputs/p5_species"
TID="${SEI_ARRAY_TASK_ID:-}"
SFX="${SEI_TASK_FILE_SUFFIX:-}"

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  # 🔴 사유를 구분해 남긴다. 예전에는 전부 rc=3 으로 뭉개져 원인을 알 수 없었다.
  echo "[P5] QC 코드를 쓸 수 없다 → 생략"
  echo "  사유: ${SEI_QC_DETAIL:-(미상)}"
  echo "  시도한 모듈: ${SEI_QC_MODULE:-(없음)}"
  echo "  상세는 ${SEI_JOB_DIR}/adapter${SFX}.json 에 있다"
  exit 3
fi
sei_qc_smoke > "$D/smoke_result${SFX}.txt" 2>&1 || { echo "[P5] route 검증 실패 → 중단"; exit 4; }

mkdir -p "$D/species"
# 🔴 태스크 목록은 plan._p5_runs() 단일 출처. TID 가 있으면 그 index 의 실행 1건만,
#    없으면(스케줄러 없이 손으로 돌릴 때) 전체를 돌린다. 시드 섭동 기하는 태스크별
#    디렉터리(geom.t<N>/)에 만들고, 어느 시드였는지 p5_seeds.t<N>.json 에 남긴다.
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$TID" "$SFX" > "$D/tasks${SFX}.tsv" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import seeding
from sei_pilot.plan import _p5_runs
d, tid, sfx = sys.argv[1], sys.argv[2], sys.argv[3]
runs = _p5_runs()
if not runs:
    sys.stderr.write("P5: manifest 를 읽지 못했다 — 태스크 목록이 비었다\n")
    sys.exit(2)
if tid:
    idx = int(tid)
    if not (1 <= idx <= len(runs)):
        # 🔴 index 초과는 조용히 0건 실행이 아니라 시끄러운 실패다. array 크기와
        #    plan._p5_runs() 가 어긋났다는 뜻이고, 그 어긋남 자체가 회신할 정보다.
        sys.stderr.write("P5: array index %d 가 실행 목록 크기 %d 를 벗어난다 — "
                         "plan 의 array=(1,N) 과 _p5_runs() 가 어긋났다\n"
                         % (idx, len(runs)))
        sys.exit(2)
    runs = [runs[idx - 1]]
spec_dir = os.path.join(os.environ["SEI_PKG_ROOT"], "inputs", "p5_species")
gdir = os.path.join(d, "geom%s" % sfx)
os.makedirs(gdir, exist_ok=True)
prov = {}
for r in runs:
    original = seeding.read_xyz(open(os.path.join(spec_dir, r["file"])).read())
    atoms = seeding.perturb(original, r["seed"])
    rel = "geom%s/%s_s%d.xyz" % (sfx, r["id"], r["seed"])
    open(os.path.join(d, rel), "w").write(seeding.write_xyz(
        atoms, "%s seed=%d" % (r["id"], r["seed"])))
    prov["%s_s%d" % (r["id"], r["seed"])] = seeding.provenance(
        r["seed"], seeding.DEFAULT_AMPLITUDE_ANG, original, atoms)
    print("\t".join([r["id"], rel, str(r["charge"]), str(r["multiplicity"]),
                     str(r["level"]), str(r["seed"])]))
json.dump(prov, open(os.path.join(d, "p5_seeds%s.json" % sfx), "w"),
          ensure_ascii=False, indent=1)
PY
then
  echo "[P5] 태스크 목록 생성 실패 (index/manifest 불일치) → 중단"
  exit 5
fi

run_one() {   # $1=id $2=기하파일(D 기준 상대) $3=charge $4=mult $5=level $6=seed
  local sid="$1" f="$2" chg="$3" mult="$4" lvl="$5" seed="$6"
  # ⚠ `local a=.. b=$a` 는 set -u 에서 깨진다. 분리한다 (P1b u27_try 의 교훈과 동일).
  local tag="${sid}_s${seed}_L${lvl}"
  local w="$D/species/${tag}"
  mkdir -p "$w"
  cp "$D/${f}" "$w/mol.xyz"
  sei_qc_input "$w/job.gjf" "$lvl" opt_freq "$chg" "$mult" "$w/mol.xyz" \
    > "$w/meta.json" || return 1
  sei_stage "p5_${tag}" sei_qc_run "$w" job.gjf job.log
}

# 🔴 실행 1건 = 줄 1개 (level 이 줄에 명시된다 — 값싼 레벨을 같은 줄에 얹던
#    cheap 플래그 방식은 plan 의 태스크 열거와 어긋나는 원인이었다).
# 🔴 [critic10] WALL TRIPWIRE. P5.t21/t22 were killed by the scheduler mid-species and left
#    a "run" event with NO "finish" event -- unlike t20, same species, which recorded a real
#    crash honestly. P5 had no per-species budget check and no SIGTERM trap, so a wall kill was
#    INDISTINGUISHABLE FROM A JOB THAT NEVER STARTED, and "P5: 20/22" silently read as a flat
#    22-species denominator instead of "20 measured + 2 unrecoverable on the same already-known
#    problem species".
# 🔒 Copied from endpoint_prep.sh's existing pattern rather than invented: PBS sends SIGTERM
#    before SIGKILL, so the trap gets one chance to write the marker before the process dies.
P5_WALL_BUDGET_H="${SEI_P5_WALL_BUDGET_H:-${SEI_WALL_BUDGET_H:-}}"
P5_T0="$(date +%s)"
_p5_write_marker() {
  cat > "$D/wall_exhausted${SFX}.json" <<EOF
{"status": "$1", "note": "$2", "elapsed_h": $(awk "BEGIN{printf \"%.4f\", ($(date +%s)-${P5_T0})/3600.0}"),
 "wall_budget_h": ${P5_WALL_BUDGET_H:-null}, "last_species": "${_P5_CURRENT:-none}",
 "_why": "🔴 A wall kill leaves a 'run' event with no 'finish'. Without this marker that is indistinguishable from a species that never started, and the failure silently enters the denominator as if it had been measured."}
EOF
}
# 🔴 The trap fires on the scheduler's SIGTERM -- the one chance to say what happened.
trap '_p5_write_marker wall_exhausted "SIGTERM from the scheduler while running ${_P5_CURRENT:-unknown}"; exit 9' TERM

while IFS=$'\t' read -r sid f chg mult lvl seed; do
  [ -z "${sid:-}" ] && continue
  # Budget check BEFORE launching -- do not start a species we cannot finish.
  if [ -n "${P5_WALL_BUDGET_H}" ]; then
    if awk "BEGIN{exit !((($(date +%s)-${P5_T0})/3600.0) >= ${P5_WALL_BUDGET_H})}"; then
      echo "[P5] 🔴 wall budget ${P5_WALL_BUDGET_H} h exhausted before ${sid} — not starting it."
      _P5_CURRENT="$sid" _p5_write_marker "wall_budget_exhausted" \
        "stopped before launching ${sid}; remaining species were not attempted"
      break
    fi
  fi
  _P5_CURRENT="$sid"
  run_one "$sid" "$f" "$chg" "$mult" "$lvl" "$seed"
  _P5_CURRENT=""
done < "$D/tasks${SFX}.tsv"
trap - TERM

# --- 결과 취합: 종별 원자료 (평균 내지 않는다) ---
# 🔴 array 태스크는 자기 실행분의 row 만 p5_task_results.t<N>.json 에 남긴다 —
#    고정 경로 p5_results.json 을 22태스크가 마지막 승자로 덮어쓰던 것의 수정.
#    태스크 간 병합(seed_pairs 포함)은 수집 단계(collect_p5)가 한다.
#    TID 없이(수동) 돌리면 이전과 같은 p5_results.json 을 그대로 낸다.
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$SPEC_DIR" "$TID" "$SFX" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16, p5
from sei_pilot import units
d, spec_dir, tid, sfx = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
man = json.load(open(os.path.join(spec_dir, "manifest.json")))
by_id = dict((s["id"], s) for s in man["species"])
LEVEL = {"1": p5.LEVEL_CHEAP, "2": p5.LEVEL_PRIMARY}
rows = []
try:
    lines = [l.split("\t") for l in
             open(os.path.join(d, "tasks%s.tsv" % sfx)).read().splitlines()
             if l.strip()]
except OSError:
    lines = []
for sid, _f, _chg, _mult, lvl, seed in lines:
    tag = "%s_s%s_L%s" % (sid, seed, lvl)
    seed = int(seed)
    meta = by_id.get(sid, {})
    core_h = wall_h = rc = None
    try:
        st = json.load(open(os.path.join(d, "stages", "p5_%s.json" % tag)))
        core_h = units.core_hours(st.get("total_cores", 1), st.get("wall_s", 0))
        wall_h = (st.get("wall_s", 0) or 0) / 3600.0
        rc = st.get("rc")
    except (OSError, ValueError):
        pass
    try:
        text = open(os.path.join(d, "species", tag, "job.log"),
                    errors="replace").read()
    except OSError:
        text = ""
    s = g16.summarize(text)
    rows.append({
        "id": sid, "seed": seed, "level": LEVEL[lvl],
        "n_atoms": meta.get("n_atoms"),
        "charge": meta.get("charge"), "multiplicity": meta.get("multiplicity"),
        "core_hours": round(core_h, 5) if core_h is not None else None,
        "wall_h": round(wall_h, 5) if wall_h is not None else None,
        "scf_cycles_max": s["scf"]["max_cycles"],
        "scf_cycles_total": s["scf"]["total_cycles"],
        "opt_cycles": s["opt"]["cycles"], "rc": rc,
        # 🔴 [critic10] `converged` IS OPT-ONLY, and always was -- `normal_termination` is a
        #    bare string-presence check that fires once the OPT half finishes, so this read
        #    TRUE on species whose freq stage had crashed (measured: Optimization completed x1,
        #    Normal termination x1, `Frequencies --` x0, EpsInf=0.0000 + L1110 trace).
        #    The name is kept so downstream comparisons stay valid; `stages_completed` below is
        #    what makes the gap unmissable, and it does so without needing another rename the
        #    next time a stage is added.
        "converged": bool(s["normal_termination"] and s["opt"]["converged"]),
        "_converged_means": "opt stage only -- read `stages_completed.missing` for the rest",
        "stages_completed": g16.stages_completed(text, s.get("route_echoed")),
        # B-1: `route` (bare string, RT-1's 70-column truncation defect) is gone
        # from g16.summarize(). Carry `route_echoed` + its completeness flag
        # straight through so criteria/p5.py's normalize_rows sees the CURRENT
        # shape, not the legacy fallback path.
        "qc_code": "gaussian16", "route_echoed": s.get("route_echoed"),
        "route_echoed_is_complete": s.get("route_echoed_is_complete"),
        "route_echo": s.get("route_echo"),
        "level_label": (json.load(open(os.path.join(d, "species", tag, "meta.json")))
                        .get("level_label") if os.path.exists(
                            os.path.join(d, "species", tag, "meta.json")) else None),
        "failure_reason": s["failure_reason"],
        "g16_cpu_seconds": (s["timings"] or {}).get("cpu_seconds"),
        "note": meta.get("description"),
    })

# 🔴 시드 출처를 결과와 **같은 파일에** 싣는다. 시드 없는 σ 는 해석 불가다.
try:
    seeds = json.load(open(os.path.join(d, "p5_seeds%s.json" % sfx)))
except (OSError, ValueError):
    seeds = {}
for r in rows:
    r["seed_provenance"] = seeds.get("%s_s%d" % (r["id"], r["seed"]))

dual = [s["id"] for s in man["species"] if s.get("dual_seed")]
if tid:
    # array 태스크: 자기 몫만. 병합·seed_pairs 는 collect_p5 가 한다.
    json.dump({"task_id": int(tid), "rows": rows,
               "n_requested": len(man["species"]), "dual_seed_species": dual},
              open(os.path.join(d, "p5_task_results%s.json" % sfx), "w"),
              ensure_ascii=False, indent=1)
    print("P5 task %s rows:" % tid, len(rows),
          "converged:", sum(1 for r in rows if r["converged"]))
else:
    # 수동/비-array 실행: 이전과 같은 단일 p5_results.json.
    # σ_protocol 은 **여기서 계산하지 않는다** — 원자료를 그대로 넘기고 적합은 받는
    # 쪽이 한다(§R2-6). 다만 "짝이 갖춰졌는가"는 받는 쪽이 알아야 하므로 그것만 표시.
    pairs = {}
    for r in rows:
        if r["level"] == p5.LEVEL_PRIMARY:
            pairs.setdefault(r["id"], []).append(r["seed"])
    seed_pairs = dict((k, {"seeds": sorted(v), "complete": len(set(v)) >= 2})
                      for k, v in pairs.items() if k in dual)
    json.dump({"rows": rows, "n_requested": len(man["species"]),
               "dual_seed_species": dual, "seed_pairs": seed_pairs,
               "_sigma_note": ("σ_protocol 계산은 하지 않았다. 같은 id·같은 level 의 "
                               "seed 0/1 두 행을 비교하면 된다. complete=false 인 종은 "
                               "한쪽이 죽은 것이므로 σ 를 내지 마라.")},
              open(os.path.join(d, "p5_results.json"), "w"),
              ensure_ascii=False, indent=1)
    print("P5 rows:", len(rows), "converged:", sum(1 for r in rows if r["converged"]))
    print("시드 쌍 완성:", sum(1 for v in seed_pairs.values() if v["complete"]),
          "/", len(dual))
PY

# --- [§39.80(g)(i)] terminal_status from PARSED CONTENT, per task. ---------------------
# 20/20 P5 done markers said rc=0 last round while every freq stage had died on the EpsInf
# sentinel; the marker is now written from the logs' own termination, not the wrapper's rc.
if [ -f "$D/wall_exhausted${SFX}.json" ]; then
  _st="$(grep -o '"status": *"[^"]*"' "$D/wall_exhausted${SFX}.json" | head -1 | cut -d'"' -f4)"
  sei_terminal "${_st:-wall_exhausted}" "see wall_exhausted${SFX}.json" "task=${TID:-all}"
else
  _logs=()
  while IFS=$'\t' read -r sid _f _c _m lvl seed; do
    [ -z "${sid:-}" ] && continue
    _logs+=("$D/species/${sid}_s${seed}_L${lvl}/job.log")
  done < "$D/tasks${SFX}.tsv"
  sei_terminal_from_logs "task=${TID:-all}" -- "${_logs[@]}"
fi
exit 0
