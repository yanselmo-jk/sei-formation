#!/bin/bash
# GPU 머신 환경 프로브. CPU 클러스터와 **다른 기계**이므로 따로 잰다.
#   - GPU: 모델/메모리/개수/드라이버·CUDA 버전
#   - CPU: 이 머신의 core 수 (🔴 P4 속도비의 **분모**가 이것이다)
#   - python 스택: gpu4pyscf / pyscf / cupy 존재 여부
#   - 스크래치·네트워크: HPC와 정책이 다를 수 있다
set -u
source "${SEI_PKG_ROOT}/payload/env_common.sh"
sei_apply_extra_path          # nvidia-smi 경로(단일 출처)
D="${SEI_JOB_DIR}"
mkdir -p "$D"

lscpu                > "$D/lscpu.txt"   2>&1
free -b              > "$D/free.txt"    2>&1
cat /proc/meminfo    > "$D/meminfo.txt" 2>&1
uname -a             > "$D/uname.txt"   2>&1
df -PT -B1 "${TMPDIR:-/tmp}" "$HOME" > "$D/df.txt" 2>&1

nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap \
           --format=csv,noheader > "$D/nvidia_smi.txt" 2>&1
nvidia-smi                       > "$D/nvidia_smi_full.txt" 2>&1
nvcc --version                   > "$D/nvcc.txt" 2>&1

{
  if getent hosts pypi.org > /dev/null 2>&1; then echo "dns=ok"; else echo "dns=fail"; fi
  if command -v curl > /dev/null 2>&1; then
    code=$(curl -sS -m 12 -o /dev/null -w "%{http_code}" https://pypi.org/simple/ 2>/dev/null)
    echo "https=${code:-fail}"
  else echo "https=no_client"; fi
  echo "git=absent"
} > "$D/network.txt" 2>&1

# python 스택 — P4가 실제로 돌 수 있는지 미리 본다 (본계산 전 값싼 확인)
python3 - > "$D/pystack.json" 2>"$D/pystack.err" <<'PY'
import json, importlib
out = {}
for mod in ("pyscf", "gpu4pyscf", "cupy", "numpy", "torch"):
    try:
        m = importlib.import_module(mod)
        out[mod] = getattr(m, "__version__", "unknown")
    except Exception as exc:
        out[mod] = "ABSENT (%s)" % type(exc).__name__
try:
    import cupy
    out["cuda_devices"] = int(cupy.cuda.runtime.getDeviceCount())
except Exception as exc:
    out["cuda_devices"] = "unknown (%s)" % type(exc).__name__
print(json.dumps(out, indent=1))
PY

python3 "${SEI_PKG_ROOT}/tools/node_probe_summary.py" "$D" 0 0 0 0 0 0 \
  2>> "$D/summary.err" || \
  printf '%s\n' '{"io": null, "note": "GPU 프로파일에서는 I/O 벤치를 생략한다"}' \
    > "$D/node_probe.json"
exit 0
