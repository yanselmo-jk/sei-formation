#!/bin/bash
# P6 — κ 앵커 + G16 스레드 스케일링 (§R22.10).
#
# 🔴 이 잡이 사는 것 세 가지:
#   1. **κ 실측** — 이 프로젝트의 모든 core-h 는 지금 `[ESTIMATE] κ=3.4~6.8` 이라는
#      **단위**를 달고 있고, 그 단위가 총액을 5배 흔든다. 지금 근거는 비양자화학
#      문헌 1건(기상·해양 MPI 코드)에서 유도한 값뿐이다.
#   2. **S (16→64 스레드 speedup)** — 생산 팩킹 이득 `4/S` 를 정한다(§R22.3).
#   3. **G16 64 스레드의 실효성** — 64 가 16 보다 느리면 그 자체가 결론이다.
#
# 🔴 비교 기준을 새로 만들지 않는다. §R16.10 RT-1c 가 이미 지정했고 기준값이 있다:
#      [MEASURED] 개발 박스 CPU wall 177.3 s @ 16 스레드 (Ryzen 7800X3D)
#    ⟹ **같은 계·같은 레벨·같은 잡타입**이어야 비교가 성립한다. 아래 값을 바꾸지 마라.
#
# 스레드 수는 잡 스펙에서 온다(`SEI_TOTAL_CORES`). 항목 P6_t1 / P6_t16 / P6_t64 가
# 각각 ncpus=1/16/64 로 제출되고, 이 스크립트는 **하나뿐이다** — 세 벌로 복제하면
# 다음 수정에서 갈린다.
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
NP="${SEI_TOTAL_CORES:-1}"

# 🔒 §R22.10(a)(b) — 계와 잡타입을 여기서 고정한다.
SYSTEM_XYZ="${SEI_PKG_ROOT}/inputs/li_ec_radical_reactant.xyz"
CHARGE=0
MULT=2          # 환원 라디칼 (doublet, UKS)
JOB_TYPE="sp"   # RT-1c 기준값과 같은 잡타입
LVL="${SEI_QC_LEVEL:-2}"

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  echo "[P6] QC 코드를 쓸 수 없다 → 생략"
  echo "  사유: ${SEI_QC_DETAIL:-(미상)}"
  echo "  시도한 모듈: ${SEI_QC_MODULE:-(없음)}"
  exit 3
fi

# 🔴 [critic10] P6 NEVER CALLED `sei_qc_smoke`. P1b.sh, P5.sh, P1.sh, endpoint_prep.sh and
#    U56.sh all run it before their first production input; P6 was simply never retrofitted
#    with the smoke-then-production pattern when ADR-105/108 introduced it.
#    🔴 THE COST WAS THIS ROUND'S ENTIRE kappa MEASUREMENT: the anchor jobs went straight to
#    production on an unvalidated deck and produced ZERO usable kappa data. kappa is the single
#    dominant variable of the 5-month schedule, so this is a real loss, not a wasted 8 seconds.
#    🔒 Same shape as the defects this round keeps turning up: the pattern existed, was correct,
#    and simply did not reach here.
sei_qc_smoke > "$D/smoke_result.txt" 2>&1 || { echo "[P6] route 검증 실패 → 중단"; exit 4; }

cp "$SYSTEM_XYZ" "$D/system.xyz"

# 🔴 스레드 수를 **G16 입력(%nprocshared)과 환경변수 양쪽에** 맞춘다.
#    어댑터가 %nprocshared 를 SEI_TOTAL_CORES 에서 만든다. 둘이 갈리면 측정이 무의미하다.
export OMP_NUM_THREADS="$NP"
export MKL_NUM_THREADS="$NP"

if ! sei_qc_input "$D/anchor.gjf" "$LVL" "$JOB_TYPE" "$CHARGE" "$MULT" "$D/system.xyz" \
      > "$D/anchor.meta.json" 2>"$D/anchor.meta.err"; then
  echo "[P6] 입력 생성 실패:"; cat "$D/anchor.meta.err"; exit 4
fi

sei_stage "anchor_t${NP}" sei_qc_run "$D" anchor.gjf anchor.log
RC=$?

# 🔴🔴 ADR-048 하드 게이트 — **P6 는 array 코어 버그로 죽지 않는다. 그게 더 나쁘다.**
#    P5/P1b 는 1코어를 받으면 wall 이 747 h/3,072 h 가 되어 **시끄럽게 즉사**한다.
#    그런데 P6 는 `%nprocshared=16` 을 1코어 위에 **오버서브스크립션**해서 **정상 종료한다.**
#    ⟹ "16스레드 측정점"이 회신에 실리고 **κ 가 16배 틀린다. S 는 통째로 무의미해진다.**
#    ⟹ **데이터처럼 보이는 쓰레기.** 그래서 요청값이 아니라 **실측값**을 싣고, 어긋나면
#      판단하지 말고 **버린다**(`[INVALID]`).
#
#    선언값은 항목 키에서 온다(P6_t16 → 16). 요청값은 잡 스펙(SEI_TOTAL_CORES)에서 온다.
#    셋(선언·요청·관측)이 모두 같아야만 유효한 측정점이다.
DECLARED="$(printf '%s' "${SEI_KEY:-}" | sed -n 's/^P6_t\([0-9]\+\)$/\1/p')"
ACTUAL_NPROC="$(grep -i -m1 '^%nprocshared' "$D/anchor.gjf" 2>/dev/null | cut -d= -f2)"
# 관측: 이 프로세스가 **실제로 쓸 수 있는** 코어 수. cgroup/affinity 를 반영한다.
NPROC_OBSERVED="$( (nproc 2>/dev/null) || echo "" )"
NPROC_ALL="$( (nproc --all 2>/dev/null) || echo "" )"
WALL_S="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" <<'PY'
import json, os, sys
d = sys.argv[1]
p = os.path.join(d, "stages")
best = None
for fn in sorted(os.listdir(p)) if os.path.isdir(p) else []:
    if fn.startswith("anchor_t") and fn.endswith(".json"):
        try:
            best = json.load(open(os.path.join(p, fn))).get("wall_s")
        except (OSError, ValueError):
            pass
print(best if best is not None else "")
PY
)"

cat > "$D/p6_anchor.json" <<EOF
{"declared_threads": ${DECLARED:-null},
 "requested_threads": ${NP},
 "cores_observed": ${NPROC_OBSERVED:-null},
 "cores_observed_all": ${NPROC_ALL:-null},
 "actual_nprocshared": "${ACTUAL_NPROC:-unknown}",
 "omp_num_threads": "${OMP_NUM_THREADS}",
 "_gate_note": "🔴 ADR-048: declared == requested == nprocshared 가 아니면 이 태스크는 [INVALID] 다. κ·S 산출에서 제외하라. 판단하지 말고 버려라.",
 "wall_s": ${WALL_S:-null},
 "rc": ${RC},
 "system": "li_ec_radical_reactant.xyz",
 "charge": ${CHARGE}, "multiplicity": ${MULT},
 "job_type": "${JOB_TYPE}", "level": "level${LVL}",
 "reference_note": "비교 기준 = [MEASURED] 개발 박스 177.3 s @ 16 스레드 Ryzen 7800X3D (RT-1c). 같은 계·같은 잡타입일 때만 유효하다.",
 "kappa_note": "🔴 κ 는 t16 결과로만 계산하라. t1/t64 는 스케일링 S 용이다. 그리고 κ 는 [MEASURED]가 되지만 '이 계·이 잡타입에서'라는 조건이 붙는다 — 다른 워크로드로 일반화하지 마라."}
EOF
echo "[P6] 스레드 ${NP} 완료 (rc=${RC}, wall=${WALL_S:-?} s)"
# [§39.80(g)(i)] κ anchor is a MEASUREMENT, but its single G16 log still has a termination.
sei_terminal_from_logs "threads=${NP}" -- "$D/anchor.log"
exit 0
