#!/bin/bash
# many-task 처리량 프로브의 **태스크 1개** (array job).
# 200개가 동시에 이 스크립트를 돌린다. 각자 시작/종료 시각만 남기고 60초 잔다.
#
# 🔴 스케줄러 회계(sacct/qstat)를 쓰지 않는 이유: 사이트마다 회계 설정이 다르고
#    꺼져 있을 수도 있다. 노드가 스스로 기록한 시각이 가장 신뢰할 수 있다.
set -u
TID="${SLURM_ARRAY_TASK_ID:-${PBS_ARRAY_INDEX:-0}}"
D="${SEI_JOB_DIR}/starts"
mkdir -p "$D"
S=$(date +%s)
sleep 60
E=$(date +%s)
cat > "$D/task_${TID}.json" <<EOF
{"task_id": "${TID}", "start_epoch": ${S}, "end_epoch": ${E},
 "host": "$(hostname 2>/dev/null || echo unknown)", "jobid": "${SEI_JOBID:-none}"}
EOF
exit 0
