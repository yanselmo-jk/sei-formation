#!/bin/bash
# L4 배치 통합 계획기/검증기 — 배치를 제출하기 전에 이것으로 검증하라.
#
#   ./src/batch.sh show                    확정 왕복 구조(7회)와 RT-3 내부 DAG
#   ./src/batch.sh validate items.json     이 배치가 구조를 깨는지 판정
#   ./src/batch.sh drift                   config ↔ 문서(§R8.5) 어긋남 점검
#
# 종료코드 1 = 계획 불성립(ERROR). 문서는 읽기만 한다.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${HERE}${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m batch_planner "$@" --root "$(dirname "$HERE")"
