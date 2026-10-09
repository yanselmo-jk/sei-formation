#!/bin/bash
# V1 — GFN-FF PBC 정합성 단위시험. **개발박스 전용. 패키지에 들어가지 않는다.**
#
# 🔴 왜: grimme-lab/xtb Issue #1118 이 **v6.7.1(= 우리가 사용자에게 동봉해 보내는 바로 그
#    버전)** 에서 GFN-FF PBC 의 unwrap/에너지 drift 를 보고했고 미해결이다.
#    "될 것"이라 가정하지 않는다.
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="${SEI_PKG_ROOT:-$HERE/../../pilot_package}"
export SEI_PKG_ROOT="$PKG"
export SEI_XTB="$PKG/vendor/xtb/bin/xtb"
export XTBPATH="$PKG/vendor/xtb/share/xtb"
OUT="${1:-$HERE/out}"
mkdir -p "$OUT"
echo "[V1] xtb: $("$SEI_XTB" --version 2>&1 | grep -o 'version [0-9.]*' | head -1)"
PYTHONPATH="$PKG" python3 "$HERE/p2g_boxes.py" "$OUT"
PYTHONPATH="$PKG" python3 "$HERE/p2g_v1.py" "$OUT"
echo "[V1] 결과: $OUT/v1_result.json"
