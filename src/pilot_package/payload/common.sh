#!/bin/bash
# sei_pilot_package — 모든 계산 잡이 source 하는 공통 층.
#
# 책임:
#   1. 멱등성: **논리 키**(SEI_LOGICAL_KEY) 완료 마커가 있으면 아무것도 하지 않고 종료.
#      🔴 체인 링크(P1, P1_c1, ...)는 key가 다르지만 같은 작업이다. 링크별 key로
#      검사하면 링크 1이 링크 0의 완료를 못 보고 **전체 워크플로를 다시 돈다**
#      (critic B-1: core-h 2배 + 비결정론적 재실행이 최종 결과를 덮어씀).
#   2. 단계 체크포인트: sei_stage 가 이미 성공한 단계를 건너뛴다. 링크 0이 wall에
#      잘려도 링크 1이 **이어받는다** (self-chaining 약속이 실제로 성립하게 만든다).
#   3. 계측: 시작/종료 epoch, 코어 수, 호스트 → core-h 계산 가능하게.
#   4. 실패 격리: payload가 죽어도 마커를 남기고 rc 0으로 끝낸다.
#   5. 감사: 모든 실행/건너뜀을 executions.jsonl, stage_events.jsonl 에 append.
#      ⇒ 이중 실행이 일어났다면 회신 JSON에 반드시 드러난다.
#   6. 판정은 여기서 하지 않는다. 판정은 수집 단계(python)가 아티팩트를 읽고 한다.
#
# 요구 환경변수: SEI_PKG_ROOT SEI_WORKDIR SEI_KEY SEI_JOB_DIR SEI_TOTAL_CORES
#                (SEI_LOGICAL_KEY 없으면 SEI_KEY 로 대체)
#
# 🔴 **두 번 source 해도 안전해야 한다.** 잡 템플릿이 한 번 source 하고, payload 도
#    스스로 한 번 source 한다. 후자가 필요한 이유:
#      템플릿은 `sei_job_main bash "<key>.cmd.sh"` 로 payload 를 **새 프로세스**에
#      띄운다 → 셸 함수는 상속되지 않는다 → payload 안의 sei_stage 가 전부
#      `command not found` 로 죽는다(단계 체크포인트·core-h 분해가 통째로 소실).
#      테스트의 가짜 payload 는 스스로 source 하고 있어서 이 격차가 안 보였다.
#    payload 가 스스로 source 하는 쪽을 정답으로 둔다 — `export -f` 와 달리
#    payload 를 손으로 직접 돌릴 때도(디버깅) 똑같이 동작하기 때문이다.

# ⚠ 이 가드 변수는 **일부러 export 하지 않는다.** export 하면 자식 bash(=payload)가
#   "이미 source 됨"으로 오판해 함수 정의를 건너뛰고, 고치려던 버그가 그대로 남는다.
if [ -n "${SEI_COMMON_SOURCED:-}" ]; then
  return 0 2>/dev/null || true
fi
SEI_COMMON_SOURCED=1

SEI_KEY="${SEI_KEY:-manual}"          # 손으로 돌릴 때(set -u)도 죽지 않게
SEI_LOGICAL_KEY="${SEI_LOGICAL_KEY:-${SEI_KEY}}"

# 🔴 array 태스크 정체성 (이번 라운드의 사고 그 자체).
#    잡 템플릿은 SEI_KEY/SEI_LOGICAL_KEY/SEI_JOB_DIR 를 **array 전체에 같은 값**으로
#    export 한다. 그래서 P1b 3태스크·P5 22태스크가 같은 논리 키, 같은 stage 마커,
#    같은 started.json 을 공유했고 — 서로의 완료 마커를 보고 건너뛰거나(태스크 유실),
#    같은 G16 job.chk/job.log 에 동시에 썼다(결과 전멸).
#    ⟹ 태스크 index 를 읽어(probe_throughput.sh:8 과 같은 패턴 — 두 번째 메커니즘을
#      만들지 않는다) 키를 태스크 단위로 가른다. 마커는 state/<key>.t<N>.<kind>.json
#      이 되고, 멱등성·재개가 태스크 단위로 성립한다.
#    ⚠ SEI_TASK_KEYS_APPLIED 가드: payload 가 common.sh 를 다시 source 할 때(자식
#      프로세스, 의도된 동작) 접미사가 두 번 붙는 것을 막는다. export 되므로 상속된다.
SEI_ARRAY_TASK_ID="${SLURM_ARRAY_TASK_ID:-${PBS_ARRAY_INDEX:-}}"
if [ -n "${SEI_ARRAY_TASK_ID}" ] && \
   [ "${SEI_TASK_KEYS_APPLIED:-}" != "${SEI_ARRAY_TASK_ID}" ]; then
  SEI_KEY="${SEI_KEY}.t${SEI_ARRAY_TASK_ID}"
  SEI_LOGICAL_KEY="${SEI_LOGICAL_KEY}.t${SEI_ARRAY_TASK_ID}"
  SEI_TASK_KEYS_APPLIED="${SEI_ARRAY_TASK_ID}"
  SEI_TASK_FILE_SUFFIX=".t${SEI_ARRAY_TASK_ID}"
fi
SEI_TASK_FILE_SUFFIX="${SEI_TASK_FILE_SUFFIX:-}"
SEI_TASK_KEYS_APPLIED="${SEI_TASK_KEYS_APPLIED:-}"
export SEI_KEY SEI_LOGICAL_KEY SEI_ARRAY_TASK_ID SEI_TASK_KEYS_APPLIED \
       SEI_TASK_FILE_SUFFIX

sei_state_dir() { echo "${SEI_WORKDIR}/state"; }

sei_append_jsonl() {   # $1=파일  $2=한 줄 JSON
  mkdir -p "$(dirname "$1")"
  printf '%s\n' "$2" >> "$1"
}

sei_write_marker() {   # $1=kind(done|failed) $2=rc $3=start $4=end $5=reason $6=key
  local kind="$1" rc="$2" start="$3" end="$4" reason="${5:-}" key="${6:-$SEI_LOGICAL_KEY}"
  local f outcome cause ts
  f="$(sei_state_dir)/${key}.${kind}.json"
  mkdir -p "$(sei_state_dir)"
  # 🔴 [§39.80(g) clause (i), visibility half] `rc` is the WRAPPER's exit code and payloads
  #    deliberately exit 0 on not_converged (failure-as-data, §39.69(d)). So the marker carries
  #    the payload's own PARSED verdict (terminal_status[.tN].json -> "status") as `outcome`,
  #    so a `done` marker can never again hide a segfaulted/not_converged job behind rc=0.
  #    "absent" = the payload wrote no terminal_status file (probes, older payloads).
  #    Retry semantics on outcome are NOT decided here (pending ADR) -- this only records it.
  ts="${SEI_JOB_DIR}/terminal_status${SEI_TASK_FILE_SUFFIX:-}.json"
  outcome="absent"; cause="absent"
  if [ -f "$ts" ]; then
    outcome="$(grep -o '"status": *"[^"]*"' "$ts" 2>/dev/null | head -1 | cut -d'"' -f4)"
    outcome="${outcome:-unparsable}"
    cause="$(grep -o '"cause_class": *"[^"]*"' "$ts" 2>/dev/null | head -1 | cut -d'"' -f4)"
    cause="${cause:-unknown}"
  fi
  cat > "${f}.tmp.$$" <<EOF
{"key": "${key}",
 "status": "${kind}",
 "epoch": ${end},
 "reason": "${reason}",
 "detail": "rc=${rc}",
 "log_excerpt": "",
 "severity": "error",
 "payload": {"start_epoch": ${start}, "end_epoch": ${end}, "rc": ${rc},
             "total_cores": ${SEI_TOTAL_CORES:-1}, "nodes": ${SEI_NODES:-1},
             "host": "$(hostname 2>/dev/null || echo unknown)",
             "outcome": "${outcome}", "cause_class": "${cause}",
             "pkg_fingerprint": "$(sei_pkg_fingerprint)",
             "link_key": "${SEI_KEY}", "logical_key": "${SEI_LOGICAL_KEY}",
             "jobid": "${SEI_JOBID:-none}", "scheduler": "${SEI_SCHEDULER:-unknown}"}}
EOF
  mv -f "${f}.tmp.$$" "${f}"
}

# [MAJOR #2] 이 패키지 판(build)의 지문. 마커에 박아 "어느 판의 코드가 만들었는가"를
# 남긴다 — src/build_stamp.py 의 source_digest 는 패키지에 실려 오지 않으므로, 패키지가
# 이미 갖고 있는 동일 목적의 식별자(sei_pilot.version.package_fingerprint — provenance
# 블록이 쓰는 그것)를 쓴다. 새 메커니즘이 아니다. 잡당 1회만 계산한다(export 캐시).
sei_pkg_fingerprint() {
  if [ -z "${SEI_PKG_FINGERPRINT:-}" ]; then
    SEI_PKG_FINGERPRINT="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import version
root = os.environ["SEI_PKG_ROOT"]
# workdir 이 pkg 안에 있으면(기본값이 그렇다) 그 최상위 디렉터리를 해시에서 제외한다 —
# 잡 산출물이 지문에 새면 링크마다 지문이 달라져 체크포인트가 전부 무효가 된다.
extra = []
wd = os.environ.get("SEI_WORKDIR") or ""
if wd:
    rel = os.path.relpath(os.path.abspath(wd), os.path.abspath(root))
    if not rel.startswith(".."):
        extra.append(rel.split(os.sep)[0])
print(version.package_fingerprint(root, extra))' 2>/dev/null || echo unknown)"
    export SEI_PKG_FINGERPRINT
  fi
  printf '%s' "${SEI_PKG_FINGERPRINT}"
}

# 하위 단계별 core-h 분해(P1 요구사항) + **체크포인트**.
# 사용: sei_stage crest  <실행할 명령...>
#   - stages/<name>.json 이 rc=0 **이고 같은 판(fingerprint)의 것**이면 건너뛴다 (재개).
#     🔴 [MAJOR #2] rc=0 만 보던 예전 판은 오염된 마커(깨진 판의 코드가 남긴 것) 위에
#     새 코드를 재제출하면 "이미 완료"로 읽고 오염값을 승계했다 — R-9(state/ 의 거짓
#     done)와 같은 결함의 한 층 아래. fingerprint 필드가 없는 옛 마커는 **불일치로
#     취급**한다(이번 라운드의 오염 마커가 전부 여기 걸린다). 재실행은 조용히 하지
#     않는다 — 로그와 stage_events 에 크게 남긴다.
#   - 건너뜀/실행 사실을 stage_events.jsonl 에 남긴다 (이중 실행 감사).
sei_stage() {
  local stage="$1"; shift
  local s e rc marker fp old_fp
  marker="${SEI_JOB_DIR}/stages/${stage}.json"
  mkdir -p "${SEI_JOB_DIR}/stages"
  fp="$(sei_pkg_fingerprint)"
  if [ -f "$marker" ] && grep -q '"rc": 0' "$marker" 2>/dev/null; then
    old_fp="$(grep -o '"pkg_fingerprint": "[^"]*"' "$marker" 2>/dev/null | cut -d'"' -f4)"
    if [ "${old_fp}" = "${fp}" ]; then
      echo "[sei] stage ${stage}: 이미 완료됨 → 건너뜀 (체크포인트 재개, 판 일치 ${fp})"
      sei_append_jsonl "${SEI_JOB_DIR}/stage_events.jsonl" \
        "{\"stage\": \"${stage}\", \"event\": \"skip_done\", \"epoch\": $(date +%s), \"link\": \"${SEI_KEY}\"}"
      return 0
    fi
    echo "[sei] 🔴 stage ${stage}: rc=0 마커가 있으나 **다른 판의 것** (마커=${old_fp:-<없음>} 현재=${fp}) → 승계하지 않고 다시 실행한다"
    sei_append_jsonl "${SEI_JOB_DIR}/stage_events.jsonl" \
      "{\"stage\": \"${stage}\", \"event\": \"rerun_stale_fingerprint\", \"epoch\": $(date +%s), \"link\": \"${SEI_KEY}\", \"marker_fingerprint\": \"${old_fp}\", \"current_fingerprint\": \"${fp}\"}"
  fi
  sei_append_jsonl "${SEI_JOB_DIR}/stage_events.jsonl" \
    "{\"stage\": \"${stage}\", \"event\": \"run\", \"epoch\": $(date +%s), \"link\": \"${SEI_KEY}\"}"
  s=$(date +%s)
  "$@"
  rc=$?
  e=$(date +%s)
  cat > "${marker}.tmp.$$" <<EOF
{"stage": "${stage}", "rc": ${rc}, "start_epoch": ${s}, "end_epoch": ${e},
 "wall_s": $((e - s)), "total_cores": ${SEI_TOTAL_CORES:-1}, "link": "${SEI_KEY}",
 "pkg_fingerprint": "${fp}"}
EOF
  mv -f "${marker}.tmp.$$" "${marker}"
  return $rc
}

# 🔴 [§39.80(g)(i)] terminal_status 는 payload 가 PARSED CONTENT 로 쓴다. 두 형태:
#   sei_terminal STATUS NOTE [k=v ...]           -- 상태를 payload 가 이미 안다
#   sei_terminal_from_logs [k=v ...] LOG ...      -- G16 로그들에서 판정한다
#     (engine_failure | not_converged | converged — sei_pilot/outcome.py 가 단일 정의)
# 파일: ${SEI_JOB_DIR}/terminal_status${SEI_TASK_FILE_SUFFIX}.json — array 태스크별로 가른다.
sei_terminal() {
  PYTHONPATH="${SEI_PKG_ROOT}" python3 -m sei_pilot.outcome write \
    "${SEI_JOB_DIR}/terminal_status${SEI_TASK_FILE_SUFFIX:-}.json" "$@"
}
sei_terminal_from_logs() {
  PYTHONPATH="${SEI_PKG_ROOT}" python3 -m sei_pilot.outcome from-logs \
    "${SEI_JOB_DIR}/terminal_status${SEI_TASK_FILE_SUFFIX:-}.json" "$@"
}

# 단계 체크포인트를 강제로 무효화한다(부분 성공을 성공으로 오인하는 경우에 쓴다).
sei_invalidate_stage() {
  rm -f "${SEI_JOB_DIR}/stages/$1.json"
}

# 🔴 이중 방어. 위의 "payload 가 직접 source" 가 1차 방어(정적 테스트로 강제)이고,
#    이건 2차 방어다 — 새 payload 를 추가하면서 source 를 빠뜨려도 **런타임에는**
#    함수가 살아 있게 한다. bash 가 아닌 셸에서는 export -f 가 없으므로 무시한다.
#    (자식이 bash 인 경우에만 전달된다. 그게 우리 잡 템플릿의 실행 방식이다.)
for _sei_fn in sei_state_dir sei_append_jsonl sei_write_marker sei_stage \
               sei_invalidate_stage sei_pkg_fingerprint sei_terminal sei_terminal_from_logs; do
  export -f "$_sei_fn" 2>/dev/null || true
done
unset _sei_fn

sei_job_main() {
  local start end rc
  mkdir -p "${SEI_JOB_DIR}"
  # 사이트 고유 환경(module load 등)을 끼워 넣는 유일한 지점.
  if [ -f "${SEI_PKG_ROOT}/modules.conf" ]; then
    # shellcheck disable=SC1090
    source "${SEI_PKG_ROOT}/modules.conf" || echo "[sei] modules.conf 로드 실패(무시하고 진행)"
  fi
  # 🔴 논리 키로 검사한다. 체인 링크가 앞 링크의 완료를 보고 즉시 종료하는 지점.
  if [ -z "${SEI_ALWAYS_RUN:-}" ] && \
     [ -f "$(sei_state_dir)/${SEI_LOGICAL_KEY}.done.json" ]; then
    echo "[sei] ${SEI_KEY}: 논리 키 ${SEI_LOGICAL_KEY} 완료 마커 존재 → 건너뜀 (멱등 재개)"
    sei_append_jsonl "${SEI_JOB_DIR}/executions.jsonl" \
      "{\"link\": \"${SEI_KEY}\", \"logical\": \"${SEI_LOGICAL_KEY}\", \"action\": \"skip_done\", \"epoch\": $(date +%s)}"
    return 0
  fi
  start=$(date +%s)
  echo "[sei] ${SEI_KEY} start epoch=${start} host=$(hostname 2>/dev/null) cores=${SEI_TOTAL_CORES:-1}"
  # 🔴 array 태스크는 started 파일도 태스크별로 가른다(started.t<N>.json). 고정 경로
  #    started.json 을 22태스크가 `>` 로 덮어쓰던 것이 이번 라운드 (b)목록의 한 줄이다.
  echo "{\"key\": \"${SEI_KEY}\", \"logical_key\": \"${SEI_LOGICAL_KEY}\", \"start_epoch\": ${start}, \"host\": \"$(hostname 2>/dev/null || echo unknown)\", \"jobid\": \"${SEI_JOBID:-none}\"}" \
       > "${SEI_JOB_DIR}/started${SEI_TASK_FILE_SUFFIX:-}.json"
  # R31.2a: `host` and `cores` go on THIS append. Do NOT add a second mechanism.
  #   started.json (above) is a FIXED PATH written with `>` -- concurrent array tasks on different
  #   hosts erase each other, so it cannot carry per-task telemetry. This append is `>>`, is
  #   concurrency-safe by construction, and already carries a per-task `epoch`.
  #   The production-shape availability fraction f (5-month condition (ii)) is measured ONLY here.
  sei_append_jsonl "${SEI_JOB_DIR}/executions.jsonl" \
    "{\"link\": \"${SEI_KEY}\", \"logical\": \"${SEI_LOGICAL_KEY}\", \"action\": \"run\", \"epoch\": ${start}, \"host\": \"$(hostname 2>/dev/null || echo unknown)\", \"cores\": ${SEI_TOTAL_CORES:-1}}"

  "$@"
  rc=$?

  end=$(date +%s)
  echo "[sei] ${SEI_KEY} end epoch=${end} rc=${rc} wall_s=$((end - start))"
  if [ "$rc" -eq 0 ]; then
    sei_write_marker done "$rc" "$start" "$end" "" "${SEI_LOGICAL_KEY}"
    # 앞 링크가 남긴 실패 마커를 지운다 — 이어받아 성공했는데 영구히 "failed"로
    # 오분류되는 것을 막는다(critic M-2).
    rm -f "$(sei_state_dir)/${SEI_LOGICAL_KEY}.failed.json"
    [ "${SEI_KEY}" != "${SEI_LOGICAL_KEY}" ] && \
      sei_write_marker done "$rc" "$start" "$end" "" "${SEI_KEY}"
  else
    # 논리 키에도 실패를 남긴다(뒤 링크가 성공하면 위에서 지워진다).
    sei_write_marker failed "$rc" "$start" "$end" "payload_nonzero_exit" "${SEI_LOGICAL_KEY}"
    [ "${SEI_KEY}" != "${SEI_LOGICAL_KEY}" ] && \
      sei_write_marker failed "$rc" "$start" "$end" "payload_nonzero_exit" "${SEI_KEY}"
  fi
  sei_append_jsonl "${SEI_JOB_DIR}/executions.jsonl" \
    "{\"link\": \"${SEI_KEY}\", \"logical\": \"${SEI_LOGICAL_KEY}\", \"action\": \"finish\", \"epoch\": ${end}, \"rc\": ${rc}}"
  return 0   # 실패 격리: 체인의 다음 링크와 collector는 계속 간다.
}
