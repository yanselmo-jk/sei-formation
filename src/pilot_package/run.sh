#!/bin/bash
# =====================================================================
#  SEI 파일럿 인도 패키지 — 사용자가 실행하는 유일한 스크립트
#
#  사용자가 할 일은 3가지뿐입니다:
#     1) tar xf sei_pilot_package.tar.gz
#     2) cd sei_pilot_package && ./run.sh
#     3) 끝나면 sei_pilot_work/results/sei_probe_report.<프로파일>.json 파일 1개를 회신
#
#  권장(왕복 1회 절약):  ./run.sh --dry-run   을 먼저 돌려보세요.
#     실제 제출 없이 "이 클러스터에서 무엇이 실행 가능한가"만 5분 안에 알려줍니다.
#
#  자원 상한은 스크립트 안에 하드코딩돼 있습니다.
#    CPU 패키지: 5,000 core-h / 잡당 24 h      GPU 패키지: 4 GPU-h / 24 h
#  이 상한을 넘는 잡은 **제출 자체가 되지 않습니다.**
# =====================================================================
set -u

SEI_PKG_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
export SEI_PKG_ROOT
: "${SEI_WORKDIR:=${SEI_PKG_ROOT}/sei_pilot_work}"
export SEI_WORKDIR

MODE="submit"
# 프로파일: 빌드 시 PROFILE 파일에 박히고, 없으면 cpu.
if [ -f "${SEI_PKG_ROOT}/PROFILE" ]; then
  SEI_PROFILE="$(tr -d ' \n' < "${SEI_PKG_ROOT}/PROFILE")"
else
  SEI_PROFILE="${SEI_PROFILE:-cpu}"
fi
export SEI_PROFILE
EXTRA=("--profile" "${SEI_PROFILE}")
for arg in "$@"; do
  case "$arg" in
    --dry-run|-n)   MODE="preflight" ;;
    --collect)      MODE="collect" ;;
    --status)       MODE="status" ;;
    --full)         : ;;                                   # 하위호환: 기본값이 이미 전량
    --help|-h)
      sed -n '2,20p' "$0"; exit 0 ;;
    *)              EXTRA+=("$arg") ;;
  esac
done

# --- python3 확인 (이 패키지는 표준 라이브러리만 씁니다. pip 설치 불필요) ---
PY=""
for cand in python3 python3.11 python3.9 python3.8 python3.6 python; do
  if command -v "$cand" > /dev/null 2>&1; then
    if "$cand" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3,6) else 1)' 2>/dev/null; then
      PY="$cand"; break
    fi
  fi
done
if [ -z "$PY" ]; then
  echo "[오류] python3 (>=3.6)을 찾지 못했습니다."
  echo "       모듈 시스템이 있다면  module load python  후 다시 실행해 주세요."
  echo "       (이 패키지는 표준 라이브러리만 사용하며 추가 설치가 필요 없습니다.)"
  exit 1
fi

# GPU 프로파일: nvidia-smi 가 PATH에 없는 환경(WSL 등)을 위해 탐색 경로만 넓힌다.
#
# 🔴 LD_LIBRARY_PATH 는 **일부러 건드리지 않는다.**
#    처음엔 자동 설정을 넣었으나 lead가 반증했고 나도 재확인했다:
#      env -u LD_LIBRARY_PATH python -c "import gpu4pyscf"  →  정상 import
#    `libnvJitLink.so` / `libcusolver.so` 실패를 푸는 것은 경로가 아니라
#    **`nvidia-*-cu12` 패키지 설치 자체**다(휠이 자기 경로를 들고 있다).
#    필요 없는 환경 변수 조작은 사용자 환경을 망가뜨릴 위험만 남긴다. 넣지 마라.
if [ "${SEI_PROFILE}" = "gpu" ]; then
  # 경로 목록은 config/env_paths.json 한 곳에만 있다(여기 적지 마라).
  PATH="$(PYTHONPATH="${SEI_PKG_ROOT}" "$PY" -c '
from sei_pilot import envpaths
print(envpaths.path_with_extras())' 2>/dev/null || echo "$PATH")"
  export PATH
fi

mkdir -p "${SEI_WORKDIR}"
cd "${SEI_PKG_ROOT}" || exit 1
export PYTHONPATH="${SEI_PKG_ROOT}${PYTHONPATH:+:$PYTHONPATH}"

run_py() {
  local cmd="$1"; shift
  "$PY" -m sei_pilot.cli "$cmd" \
        --workdir "${SEI_WORKDIR}" --pkg-root "${SEI_PKG_ROOT}" \
        ${EXTRA[@]+"${EXTRA[@]}"}
}

case "$MODE" in
  preflight) run_py preflight ;;
  collect)   run_py collect   ;;
  status)    run_py status    ;;
  submit)
    # 1) 먼저 계획을 보여준다. 비싼 계산을 조용히 던지지 않는다.
    run_py preflight || exit 1
    # 2) 대화형 터미널이면 15초 중단 기회를 준다. 배치/비대화형이면 그대로 진행.
    if [ -t 0 ] && [ -z "${SEI_NO_PROMPT:-}" ]; then
      echo ""
      echo ">>> 15초 후 위 계획대로 제출합니다. 중단하려면 Ctrl-C 를 누르세요."
      sleep 15 || exit 1
    fi
    run_py submit
    ;;
esac
