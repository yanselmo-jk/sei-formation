#!/bin/bash
# V1b — NVE drift + Δt² 스케일링. **개발박스 전용. 패키지에 들어가지 않는다.**
set -eu
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PKG="${SEI_PKG_ROOT:-$HERE/../../pilot_package}"
export SEI_PKG_ROOT="$PKG"
export SEI_XTB="$PKG/vendor/xtb/bin/xtb"
export XTBPATH="$PKG/vendor/xtb/share/xtb"
export SEI_NPROCS="${SEI_NPROCS:-8}"
exec python3 "$HERE/p2g_v1b.py" "${1:-$HERE/out_v1b}"
