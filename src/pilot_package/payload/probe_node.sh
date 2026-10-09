#!/bin/bash
# 계산 노드 환경 프로브 (A1 / A8 / I/O / Q2 / GPU).
# 원시 출력을 그대로 저장한다 — 파싱은 수집 단계(python)가 한다.
# 이유: 셸에서 파싱하면 사이트별 포맷 차이를 디버깅할 수 없다. 원본을 회신에 남긴다.
set -u
D="${SEI_JOB_DIR}"
mkdir -p "$D"

# --- A1 ---
lscpu                > "$D/lscpu.txt"      2>&1
# 🔒 §R23.1 (G1/ISA 게이트) — CPU flags 전문. **필터링 금지.**
#    [LITERATURE] KNL = AVX-512 F·CD·ER·PF / Skylake = F·CD·DQ·BW·VL ⟹ 공통은 F+CD 뿐이다.
#    Skylake 타깃으로 빌드된 바이너리(MOPAC 등)는 **KNL 에서 illegal instruction 으로 죽는다.**
#    🔴 lscpu 가 Flags 를 안 찍는 배포판이 있어 /proc/cpuinfo 를 **함께** 남긴다
#       (둘 중 하나만 믿으면 "없다"를 "안 찾았다"와 못 구분한다 — ADR-043).
grep -m1 '^flags' /proc/cpuinfo > "$D/cpuflags.txt" 2>&1 || \
  echo "flags: (읽지 못함 — /proc/cpuinfo 접근 불가)" > "$D/cpuflags.txt"
free -b              > "$D/free.txt"       2>&1
cat /proc/meminfo    > "$D/meminfo.txt"    2>&1
uname -a             > "$D/uname.txt"      2>&1
ulimit -a            > "$D/ulimit.txt"     2>&1

# --- GPU (몰랐던 GPU 노드가 있을 수 있다) ---
nvidia-smi --query-gpu=name,memory.total --format=csv,noheader > "$D/nvidia_smi.txt" 2>&1

# --- A8 스크래치 후보 ---
SCRATCH_CANDS="${SCRATCH:-} ${WORK:-} ${TMPDIR:-/tmp} /scratch /lustre $HOME"
df -PT -B1 $SCRATCH_CANDS > "$D/df.txt" 2>&1
{ quota -s 2>&1; echo "--- lfs quota ---"; lfs quota -h "${SCRATCH:-$HOME}" 2>&1; } > "$D/quota.txt"

# --- I/O 벤치 (스크래치에서. 없으면 $TMPDIR) ---
IOD="${SCRATCH:-${TMPDIR:-/tmp}}/sei_io_$$"
mkdir -p "$IOD"
SZ=$((1024*1024*1024))   # 1 GiB
t0=$(date +%s.%N)
dd if=/dev/zero of="$IOD/big" bs=1M count=1024 conv=fdatasync 2>"$D/dd_write.txt"
t1=$(date +%s.%N)
dd if="$IOD/big" of=/dev/null bs=1M 2>"$D/dd_read.txt"
t2=$(date +%s.%N)
mkdir -p "$IOD/small"
t3=$(date +%s.%N)
for i in $(seq 1 1000); do echo x > "$IOD/small/f$i"; done
t4=$(date +%s.%N)
rm -rf "$IOD"

# --- Q2 outbound 네트워크 (🔴 U-09 Case A/B를 가른다) ---
{
  if getent hosts pypi.org > /dev/null 2>&1; then echo "dns=ok"; else echo "dns=fail"; fi
  if command -v curl > /dev/null 2>&1; then
    code=$(curl -sS -m 12 -o /dev/null -w "%{http_code}" https://pypi.org/simple/ 2>/dev/null)
    echo "https=${code:-fail}"
  elif command -v wget > /dev/null 2>&1; then
    if wget -q -T 12 -O /dev/null https://pypi.org/simple/; then echo "https=200"; else echo "https=fail"; fi
  else
    echo "https=no_client"
  fi
  if command -v git > /dev/null 2>&1; then
    if timeout 30 git ls-remote https://github.com/git/git HEAD > /dev/null 2>&1; then echo "git=ok"; else echo "git=fail"; fi
  else
    echo "git=absent"
  fi
} > "$D/network.txt" 2>&1

# --- 소프트웨어 인벤토리 (계산 노드 기준. 로그인 노드와 다를 수 있다) ---
{
  for t in cp2k cp2k.psmp cp2k.popt orca qchem psi4 xtb crest python3 mpirun apptainer singularity; do
    p=$(command -v "$t" 2>/dev/null); echo "$t=${p:-ABSENT}"
  done
  echo "--- module avail ---"
  ( module avail ) 2>&1 | head -200
} > "$D/software_node.txt" 2>&1

# --- 🔴 Gaussian: **모듈을 로드한 뒤** 계산 노드에서 실제로 보이는가 -----------
#
# 왜: 예전 인벤토리는 **로드 전** PATH 만 봤다. 그래서 계산 노드에서 `g16=ABSENT` 로
#     보였고, 로그인 노드에는 바이너리가 있어 planner 는 "있다"고 판단했다.
#     ⇒ P1/P1b/P5 가 전부 rc=3 으로 죽었다. **로드 후를 봐야 사실을 안다.**
#
# 로그인에서 본 경로가 계산 노드에도 있는지도 함께 기록한다([UNVERIFIED] 제거).
{
  echo "login_binary_path=${SEI_QC_LOGIN_PATH:-}"
  if [ -n "${SEI_QC_LOGIN_PATH:-}" ] && [ -e "${SEI_QC_LOGIN_PATH}" ]; then
    echo "login_binary_exists_here=yes"
    [ -x "${SEI_QC_LOGIN_PATH}" ] && echo "login_binary_executable=yes" \
                                  || echo "login_binary_executable=no"
  else
    echo "login_binary_exists_here=no"
  fi
  echo "g16_before_module=$(command -v g16 2>/dev/null || echo ABSENT)"
  if command -v module > /dev/null 2>&1 || type module > /dev/null 2>&1; then
    echo "module_command=present"
    for m in ${SEI_QC_MODULE:-} $( ( module avail ) 2>&1 \
             | tr ' ' '\n' | grep -iE '^gaussian(/|$)|^g16' | head -6 ); do
      [ -z "$m" ] && continue
      if ( module load "$m" > /dev/null 2>&1; command -v g16 > /dev/null 2>&1 ); then
        echo "module_ok=$m"
        echo "g16_after_module=$( module load "$m" > /dev/null 2>&1; command -v g16 )"
        break
      else
        echo "module_tried_failed=$m"
      fi
    done
  else
    echo "module_command=absent"
  fi
} > "$D/gaussian_probe.txt" 2>&1

if ! python3 "${SEI_PKG_ROOT}/tools/node_probe_summary.py" \
        "$D" "$t0" "$t1" "$t2" "$t3" "$t4" "$SZ" 2>> "$D/summary.err"; then
  printf '%s\n' '{"io": null, "note": "python3 집계 실패 — dd_*.txt 원본을 보라"}' \
    > "$D/node_probe.json"
fi
exit 0
