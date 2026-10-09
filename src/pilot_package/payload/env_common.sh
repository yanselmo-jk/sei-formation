#!/bin/bash
# 환경 탐지 경로를 **단일 출처(config/env_paths.json)** 에서 가져온다.
# 🔴 경로를 이 파일에 적지 마라 — 그 복제가 GPU 미탐지 버그의 원인이었다.
sei_apply_extra_path() {
  local extra
  extra="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import sys
from sei_pilot import envpaths
print(":".join(envpaths.extra_search_paths()))' 2>/dev/null)"
  if [ -n "${extra}" ]; then
    export PATH="${PATH}:${extra}"
  else
    echo "[sei] 경고: config/env_paths.json 을 읽지 못했다 — 추가 탐색 경로 없이 진행한다." >&2
  fi
}
