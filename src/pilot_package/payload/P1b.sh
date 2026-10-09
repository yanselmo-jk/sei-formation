#!/bin/bash
# P1b — 레벨 단가비 **5수** (engineer §R16.6 RT-1b 흡수), Gaussian16.
#
# 🔴 왜 이게 중요한가: 총액을 벌리는 가장 넓은 미지수가 `r`(레벨 단가 배수)이고
#    **1.19 M ~ 9.49 M (8배)** 를 만든다. 계획을 다듬어서는 좁혀지지 않는다 —
#    300 core-h 의 계산만이 좁힌다(engineer 가 정지 선언하며 남긴 유일한 요청).
#
# 재는 5수:
#   1. u_cheap      — 값싼 레벨(G-3 def2-SVPD) opt+freq 단가            [A]
#   2. r_high       — 전량 고수준(G-1 def2-TZVPPD) opt+freq / A         [B]
#   3. r_composite  — (A + C) / A,  C = G-1 SP on A 기하                [C]  🔴 ADR-032
#   4. gen 페널티   — 같은 기저를 gen 경로 vs 내장 키워드로              [D]
#   5. SCF 실패율   — diffuse 수렴 병리 (기존 §11.5 단계별 측정에서 나온다)
#   + ΔG(composite − 전량고수준) 3종 산포 (추가 비용 0, proposer U-30 의 직접 답)
#
# 🔴 판정은 하지 않는다. ADR-032 규칙(|ΔG| < 0.05 eV 채택 …)은 **받는 쪽**이 적용한다.
#    우리는 원자료만 넘긴다.
set -u
# 🔴 잡 템플릿은 이 스크립트를 **새 bash 프로세스**로 띄운다 → 셸 함수는 상속되지
#    않는다. sei_stage 를 쓰려면 여기서 직접 source 해야 한다(두 번 source 해도 안전).
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
SPEC_DIR="${SEI_PKG_ROOT}/inputs/p5_species"
# 🔴🔴 array 분기: plan.py 는 P1b 를 `array=(1,3)` — **태스크 1개 = 종 1개**(§R22.8,
#    r_composite=(A+C)/A 는 종 안에서 완결) — 로 제출하는데, 이전 판의 이 스크립트는
#    태스크 index 를 읽지 않아 3개 태스크 전원이 3종 전부를 돌았다: 같은 steps/<tag>/
#    job.chk·job.log 에 G16 3개가 동시에 썼고(322 MB rwf ×3, Normal termination 0건),
#    A 의 cheap geometry 가 완성되기 전에 C 가 소비됐다. TID 로 자기 종만 돌린다.
TID="${SEI_ARRAY_TASK_ID:-}"
SFX="${SEI_TASK_FILE_SUFFIX:-}"

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  # 🔴 사유를 구분해 남긴다. 예전에는 전부 rc=3 으로 뭉개져 원인을 알 수 없었다.
  echo "[P1b] QC 코드를 쓸 수 없다 → 생략"
  echo "  사유: ${SEI_QC_DETAIL:-(미상)}"
  echo "  시도한 모듈: ${SEI_QC_MODULE:-(없음)}"
  echo "  상세는 ${SEI_JOB_DIR}/adapter${SFX}.json 에 있다"
  exit 3
fi
sei_qc_smoke > "$D/smoke_result${SFX}.txt" 2>&1 || { echo "[P1b] route 검증 실패 → 중단"; exit 4; }

# --- 대상 3종: 크기 구간을 덮는다 (engineer 사양: 5 / 12 / 22 원자 근처) ---
#     🔴 종 선택은 manifest 에서 **유도**한다. 여기에 id 를 박으면 종을 바꿀 때
#        두 곳을 고쳐야 하고, 그러면 한쪽만 갱신된다.
#     🔴 전체 목록은 태스크별 파일(targets_all.t<N>.tsv)에 쓴다 — 내용은 결정론적으로
#        같지만, 고정 경로를 여러 태스크가 `>` 로 동시에 쓰면 부분 파일을 읽는다
#        (지난 라운드 P5 tasks.tsv 사고와 같은 형태).
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$SPEC_DIR" > "$D/targets_all${SFX}.tsv" <<'PY'
import json, sys
species = json.load(open(sys.argv[1] + "/manifest.json"))["species"]
seen = []
for want in (5, 12, 22):
    cands = [s for s in species if s["id"] not in seen]
    best = min(cands, key=lambda s: (abs(s["n_atoms"] - want), s["n_atoms"]))
    seen.append(best["id"])
    print("\t".join([best["id"], best["file"], str(best["charge"]),
                     str(best["multiplicity"]), str(best["n_atoms"])]))
PY
N_TARGETS=$(grep -c . "$D/targets_all${SFX}.tsv")
# [MAJOR #1] 태스크 배치: 1..N_TARGETS = 종별 측정 / N_TARGETS+1 = stagewise + U-27
#            (종별 태스크에 얹으면 3,072=64×48h 의 wall 여유 0% 위에 G16 최대 14회가
#             올라간다 — lead 판정으로 4번째 태스크로 분리, 예산 590 [ESTIMATE]).
EXTRAS_TID=$((N_TARGETS + 1))
if [ -n "$TID" ]; then
  if [ "$TID" -lt 1 ] || [ "$TID" -gt "$EXTRAS_TID" ]; then
    # 🔴 index 초과는 조용히 0건 실행이 아니라 시끄러운 실패다 — array=(1,N) 과
    #    대상 목록이 어긋났다는 뜻이고, 그 어긋남 자체가 회신할 정보다.
    echo "[P1b] array index ${TID} 가 태스크 수 ${EXTRAS_TID} (종 ${N_TARGETS} + extras 1) 를 벗어난다 → 중단"
    exit 5
  fi
  if [ "$TID" = "$EXTRAS_TID" ]; then
    : > "$D/targets${SFX}.tsv"      # extras 태스크는 종별 측정을 하지 않는다
  else
    sed -n "${TID}p" "$D/targets_all${SFX}.tsv" > "$D/targets${SFX}.tsv"
  fi
else
  cp "$D/targets_all${SFX}.tsv" "$D/targets${SFX}.tsv"
fi
echo "[P1b] 대상 종 (task ${TID:-all}/${EXTRAS_TID}):"; cat "$D/targets${SFX}.tsv"

run_step() {   # $1=tag $2=level $3=job $4=chg $5=mult $6=xyz절대경로
  local tag="$1" lvl="$2" job="$3" chg="$4" mult="$5" xyz="$6"
  local w="$D/steps/$tag"
  mkdir -p "$w"
  cp "$xyz" "$w/mol.xyz"
  sei_qc_input "$w/job.gjf" "$lvl" "$job" "$chg" "$mult" "$w/mol.xyz" \
    > "$w/meta.json" 2> "$w/meta.err" || { echo "  ! $tag 입력 생성 실패"; return 1; }
  sei_stage "p1b_${tag}" sei_qc_run "$w" job.gjf job.log
}

# 로그에서 최종 기하를 뽑아 다음 단계의 입력으로 넘긴다.
extract_geom() {   # $1=단계태그 $2=출력xyz
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/steps/$1/job.log" "$2" <<'PY'
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
try:
    text = open(sys.argv[1], errors="replace").read()
except OSError:
    sys.exit(1)
geom = g16.last_geometry(text)
if not geom:
    sys.exit(1)
open(sys.argv[2], "w").write(
    "%d\nP1b optimised geometry\n" % len(geom)
    + "".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
PY
}

while IFS=$'\t' read -r sid f chg mult nat; do
  [ -z "${sid:-}" ] && continue
  echo "[P1b] === $sid ($nat 원자, q=$chg, m=$mult) ==="
  SRC="${SPEC_DIR}/${f}"

  # [A] 값싼 레벨 opt+freq — u_cheap. composite 의 기하·Hessian 이 여기서 나온다.
  run_step "${sid}_A_cheap_optfreq" 3 opt_freq "$chg" "$mult" "$SRC"

  # [C] 고수준 SP on A 기하 — composite 의 두 번째 항.
  if extract_geom "${sid}_A_cheap_optfreq" "$D/${sid}_cheapgeom.xyz"; then
    run_step "${sid}_C_high_sp_on_cheap" 2 sp "$chg" "$mult" "$D/${sid}_cheapgeom.xyz"
  else
    echo "  ! A 의 최종 기하를 못 뽑았다 → C 생략 (r_composite 계산 불가로 기록된다)"
  fi

  # [B] 전량 고수준 opt+freq — r_high. 가장 비싸다.
  run_step "${sid}_B_high_optfreq" 2 opt_freq "$chg" "$mult" "$SRC"

  # [D] gen 오버헤드: **같은 기저(def2-TZVPP)** 를 gen 경로와 내장 키워드로 각 1회 SP.
  #     🔴 engineer 원문은 '내장 def2TZVPP vs gen def2TZVPPD' 였는데 그 비교는
  #        gen 오버헤드와 diffuse 비용을 **섞는다**. 같은 기저로 gen 만 분리하고,
  #        diffuse 는 gen 안에서 따로 뺀다(G-1 SP / G-4gen SP). 요청한 '분리'가
  #        그렇게 해야 실제로 이뤄진다.
  GEOM="$D/${sid}_cheapgeom.xyz"; [ -f "$GEOM" ] || GEOM="$SRC"
  run_step "${sid}_D_gen_sp"     level4_gen     sp "$chg" "$mult" "$GEOM"
  run_step "${sid}_D_builtin_sp" level4_builtin sp "$chg" "$mult" "$GEOM"
done < "$D/targets${SFX}.tsv"

# --- 종별이 아닌 나머지(단계별 단가비 + U-27 스모크)는 **전용 태스크(EXTRAS_TID)** ---
# 🔴 전 태스크가 돌리면 geom.xyz / u27*/ / u27_noneq.json 고정 경로가 충돌하고,
#    종별 태스크에 얹으면 wall 여유 0% 위에 얹는 것이다(lead 판정, MAJOR #1).
#    TID 없이(수동) 돌리면 이전과 같이 전부 돈다.
# [§39.80(g)(i)] terminal_status per task from the species steps' OWN logs (A/C/B/D), not rc.
_p1b_terminal_species() {
  local _logs=() sid _f _c _m _n
  while IFS=$'\t' read -r sid _f _c _m _n; do
    [ -z "${sid:-}" ] && continue
    for _w in "$D"/steps/"${sid}"_*/; do
      [ -d "$_w" ] && _logs+=("${_w}job.log")
    done
  done < "$D/targets${SFX}.tsv"
  sei_terminal_from_logs "task=${TID:-all}" -- "${_logs[@]}"
}
if [ -n "$TID" ] && [ "$TID" != "$EXTRAS_TID" ]; then
  echo "[P1b] task ${TID}: 종별 측정만 담당 → 단계별/U-27 은 task ${EXTRAS_TID} 가 한다"
  echo "[P1b] 완료. 비율 계산은 수집 단계가 한다."
  _p1b_terminal_species
  exit 0
fi

# --- 단계별 단가비 (기존 §11.5 측정: SP/grad/Hessian/opt5) ---
# TS 기하 위에서 두 레벨의 **단계별** 비율. 위의 5수와 목적이 다르다
# (이건 "어느 단계가 비싼가", 위는 "어느 레벨이 비싼가").
TSGEOM="${SEI_WORKDIR}/jobs/P1/ts.xyz"
[ -f "$TSGEOM" ] || TSGEOM="${SEI_PKG_ROOT}/inputs/li_ec_radical_reactant.xyz"
cp "$TSGEOM" "$D/geom.xyz"
echo "geometry_source=$TSGEOM" > "$D/geom_source.txt"
for lvl in 3 2; do
  for jt in sp force freq opt5; do
    run_step "stagewise_L${lvl}_${jt}" "$lvl" "$jt" 0 2 "$D/geom.xyz"
  done
done

# ---------------------------------------------------------------------------
# [U-27] G16 비평형 PCM(`NonEq`) 스모크 — **1종 1회.**
#
# 🔴 재는 것은 λ_out 값이 아니라 **"이 루트가 G16 에서 도는가"** 다.
#    되면 λ_out 전체가 G16 단일점만으로 끝나고(proposer §30.1), 안 되면 IEFPCM 로
#    λ_out 만 분리한다. 지금 확인하지 않으면 사용자 회신 뒤 **왕복 1회(3.5일)를 더** 쓴다.
# 🔴 λ_out **본계산은 구현하지 않는다** — S1 파이프라인이고 착수 금지다.
# 🔴 실패해도 P1b 전체를 죽이지 않는다. undetermined 로 떨어뜨리고 계속 간다.
#
# 절차(전부 단일점/최적화 1건, 새 코드 없음):
#   ① 중성 N 평형 SMD 최적화 (NonEq=write) → .chk 에 반응장 저장
#   ② 같은 기하 환원종 R, NonEq=read       → G_R^vert
#   ③ 같은 기하 환원종 R 평형 SMD          → G_R^eq
u27_try() {   # $1=suffix("" 또는 "_pcm")  → 성공 0
  local sfx="$1"
  local w="$D/u27${sfx}"          # ⚠ `local a=.. b=$a` 는 set -u 에서 깨진다. 분리한다.
  mkdir -p "$w"
  cp "$U27_SRC" "$w/mol.xyz"

  sei_qc_input "$w/step1.gjf" "$U27_LVL" "opt_noneq_write${sfx}" \
    "$U27_CHG" "$U27_MULT" "$w/mol.xyz" > "$w/step1.meta.json" 2>&1 || return 1
  sei_stage "u27${sfx}_1_write" sei_qc_run "$w" step1.gjf step1.log
  grep -q "Normal termination" "$w/step1.log" 2>/dev/null || return 1

  # ①의 최적화 기하와 .chk 를 ②③이 그대로 쓴다.
  # 🔴 NonEq=read 는 **같은 basename 의 .chk** 를 읽는다 → 복사해 이름을 맞춘다.
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$w/step1.log" "$w/opt.xyz" <<'PY'
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
geom = g16.last_geometry(open(sys.argv[1], errors="replace").read())
if not geom:
    sys.exit(1)
open(sys.argv[2], "w").write("%d\nU-27 neutral optimised\n" % len(geom)
    + "".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
PY
  [ -f "$w/opt.xyz" ] || return 1

  for st in 2 3; do
    local job="sp_noneq_read${sfx}"; [ "$st" = "3" ] && job="sp_eq${sfx}"
    sei_qc_input "$w/step${st}.gjf" "$U27_LVL" "$job" \
      "$U27_CHG_RED" "$U27_MULT_RED" "$w/opt.xyz" > "$w/step${st}.meta.json" 2>&1 \
      || return 1
    cp -f "$w/step1.chk" "$w/step${st}.chk" 2>/dev/null || true
    sei_stage "u27${sfx}_${st}" sei_qc_run "$w" "step${st}.gjf" "step${st}.log"
  done
  grep -q "Normal termination" "$w/step2.log" 2>/dev/null || return 1
  return 0
}

# 🔴 대상은 **크기로 고르지 않는다.** 절차가 '중성 N → 환원종 R' 인데 P1b 의 3종은
#    하나도 중성이 아니고(음이온을 또 환원하면 −2), 더 작은 중성종 h2o 는 H2O⁻ 가
#    결합하지 않아 SCF 발산이 'NonEq 실패'로 오독된다 — **측정하려는 것과 다른 이유로
#    실패하는 것**이다. 기준 종은 manifest 의 `u27_reference` 플래그 한 곳에서 온다.
#    새 입력 파일은 만들지 않는다(이미 동봉된 종이다).
read -r U27_ID U27_F U27_CHG U27_MULT < <(
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$SPEC_DIR" <<'PY'
import json, sys
sp = json.load(open(sys.argv[1] + "/manifest.json"))["species"]
ref = [s for s in sp if s.get("u27_reference")] or [s for s in sp if s["charge"] == 0]
s = ref[0]
print("%s %s %s %s" % (s["id"], s["file"], s["charge"], s["multiplicity"]))
PY
)
U27_SRC="${SPEC_DIR}/${U27_F}"
U27_LVL="${SEI_QC_LEVEL:-2}"
U27_CHG_RED=$((U27_CHG - 1))
# 🔴 [가정] 환원종 다중도는 닫힌껍질↔이중항 뒤집기로 잡는다. 종에 따라 틀릴 수 있고,
#    틀리면 SCF 가 수렴하지 않는다 — 그 사실도 회신에 남는다(우리가 고르지 않는다).
U27_MULT_RED=$([ "$U27_MULT" = "1" ] && echo 2 || echo 1)
echo "[P1b] U-27 NonEq 스모크: ${U27_ID} (q ${U27_CHG}→${U27_CHG_RED}, m ${U27_MULT}→${U27_MULT_RED})"

U27_MODE="smd"; U27_OK=0
if u27_try ""; then U27_OK=1; else
  echo "[P1b] U-27: SMD+NonEq 실패 → IEFPCM 폴백 시도"
  U27_MODE="iefpcm"
  u27_try "_pcm" && U27_OK=1
fi

PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$U27_ID" "$U27_MODE" "$U27_OK" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
d, sid, mode, ok = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
def rd(sfx, n):
    p = os.path.join(d, "u27" + sfx, "step%d.log" % n)
    try:
        return open(p, errors="replace").read()
    except OSError:
        return ""
sfx = "" if mode == "smd" else "_pcm"
pcm_refused_pre_launch = False
if sfx == "_pcm" and not os.path.exists(os.path.join(d, "u27_pcm", "step1.log")):
    # 🔴 [ADR-105] _pcm 폴백이 덱을 내기 전에 C-5 로 거부됐다(재사양 대기) —
    #    G16 텍스트가 존재하는 것은 SMD 시도뿐이므로 실패 기록은 그쪽에서 싣는다.
    #    "실패도 데이터다"가 빈 발췌로 퇴화하지 않게 한다.
    pcm_refused_pre_launch = True
    sfx = ""
logs = dict((n, rd(sfx, n)) for n in (1, 2, 3))
e_vert = g16.summarize(logs[2])["scf"].get("final_energy_hartree")
e_eq = g16.summarize(logs[3])["scf"].get("final_energy_hartree")
first_bad = next((n for n in (1, 2, 3)
                  if "Normal termination" not in logs[n]), None)
out = {
    "unresolved_id": "U-27",
    "question": "G16 에서 NonEq 가 SMD 와 결합해 정상 동작하는가",
    "species": sid,
    "solvent_model_used": mode if ok else None,
    "route_accepted": bool(ok),
    "nonequilibrium_supported": bool(ok),
    "smd_worked": mode == "smd" and ok,
    "iefpcm_fallback_needed": mode == "iefpcm",
    # [ADR-105] *_pcm 덱은 재사양 전까지 C-5 가 거부한다 — 시도됐으나 발사 전 거부면 True.
    "pcm_attempt_refused_pre_launch": pcm_refused_pre_launch,
    # B-1: `route` was the pre-fix bare-string field (truncated at 70 columns with
    # no marker, RT-1). `route_echoed` is the reassembled route from the same
    # summarize() call; see sei_pilot/criteria/g16.py's parse_route_echo().
    "routes": dict(("step%d" % n, (g16.summarize(logs[n]) or {}).get("route_echoed"))
                   for n in (1, 2, 3)),
    # 🔴 값은 참고용이다. 우리는 "돌았는가"만 판정한다. 물리 판정은 proposer 몫.
    "lambda_out_hartree_indicative": (
        (e_vert - e_eq) if (e_vert is not None and e_eq is not None) else None),
    "_value_caveat": ("이 값은 루트가 돌았다는 증거일 뿐이다. 물리적 타당성 판정은 "
                      "proposer 몫이며, 환원종 다중도는 우리가 가정한 값이다."),
    "failed_at_step": first_bad,
    "g16_excerpt": ("\n".join((logs.get(first_bad) or "").splitlines()[-15:])
                    if first_bad else ""),
}
json.dump(out, open(os.path.join(d, "u27_noneq.json"), "w"),
          ensure_ascii=False, indent=1)
print("[P1b] U-27:", "OK (%s)" % mode if ok else "실패 (step %s)" % first_bad)
PY

echo "[P1b] 완료. 비율 계산은 수집 단계가 한다."
# The extras task (stagewise unit costs + U-27) is a MEASUREMENT: its opt5 step is a deliberate
# maxcycles probe that errors by design, so its logs must not be classified as engine death.
# Manual (no TID) runs do both halves; the species verdict wins there.
if [ -z "$TID" ]; then _p1b_terminal_species
elif [ "${U27_OK:-0}" = "1" ]; then
  sei_terminal "completed" "stagewise + U-27 measurement task; per-step verdicts are in the step logs" "task=${TID}"
else
  # [critic11] U-27 failed in BOTH variants: classify from its own logs (engine/input defect),
  # not "completed" -- the failure must reach the file the retry policy reads.
  sei_terminal_from_logs "task=${TID}" "u27_failed=1" -- "$D"/u27*/step*.log
fi
exit 0
