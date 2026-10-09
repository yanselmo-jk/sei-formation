#!/bin/bash
# 세션을 열 때 이것부터 실행하라 — "여기서부터 시작" 다이제스트 (L3).
#
#   ./src/digest.sh              한 화면. 지난 세션 이후 바뀐 것 + 할 것/막힌 것/답할 것
#   ./src/digest.sh --full       전체 (위험·게이트·구현 구속조건·최근 로그)
#   ./src/digest.sh --no-save    스냅샷 갱신 없이 보기만
#   ./src/digest.sh --json       기계용
#   ./src/digest.sh --check      파싱 건전성 점검 (문서 규약이 바뀌면 실패한다)
#
# docs/ 는 **읽기만** 한다. 스냅샷은 .session_state/ 에만 쓴다.
set -u
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export PYTHONPATH="${HERE}${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m session_digest --root "$(dirname "$HERE")" "$@"
