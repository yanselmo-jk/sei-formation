#!/bin/bash
# P7 — CP2K DFT MD 의 `s/step` (후보 B 발동 판정용). §R23.3 + lead 판정으로 편승.
#
# 🔴 이 잡의 최대 위험은 **실패가 아니다**:
#      "$CP2K_DATA_DIR 가 없으면 CP2K 는 죽는 게 아니라 **조용히 기본값으로 다른 계산을
#       한다.** 그러면 단가는 재긴 재는데 **엉뚱한 계산의 단가**다." (proposer §37)
#    ⟹ 그래서 이 스크립트는 **재기 전에 환경을 확인해 회신에 박아 넣고**, 확인이 안 되면
#      측정을 하지 않는다. 잘못된 숫자보다 없는 숫자가 낫다.
#
# 🔴 그리고 `METHOD XTB` 확인의 목적은 "쓸 수 있나"가 **아니라** "쓰면 안 되는 걸 확인"이다:
#    CP2K 내장 xTB 는 GFN1 이라 축 2(동봉 xtb GFN2)와 **독립이 아니다.**
#    ⟹ 이 결과를 보고 CP2K-XTB 경로를 만들지 마라(proposer 명시).
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
D="${SEI_JOB_DIR}"
NP="${SEI_TOTAL_CORES:-1}"

CP2K=""
for cand in cp2k.psmp cp2k.popt cp2k.sopt cp2k; do
  p="$(command -v "$cand" 2>/dev/null || true)"
  if [ -n "$p" ]; then CP2K="$p"; break; fi
done

# --- 1) 환경 감사. 측정보다 **먼저** 한다. ---
{
  echo "== which =="
  echo "${CP2K:-(없음)}"
  echo "== version banner (libint/libxc/ELPA 컴파일 옵션이 여기 찍힌다) =="
  [ -n "$CP2K" ] && "$CP2K" --version 2>&1 | head -40
  echo "== CP2K_DATA_DIR =="
  echo "CP2K_DATA_DIR=${CP2K_DATA_DIR:-(unset)}"
  ls "${CP2K_DATA_DIR:-/nonexistent}" 2>&1 | head -30
} > "$D/cp2k_env.txt" 2>&1

if [ -z "$CP2K" ]; then
  echo "[P7] CP2K 를 찾지 못했다 → 측정 생략 (실패 아님)"
  printf '{"status": "cp2k_absent", "measured": false, "s_per_step": null}\n' \
    > "$D/p7_result.json"
  exit 3
fi

# 🔴 DATA_DIR 이 없으면 **측정하지 않는다.** 조용히 다른 계산을 재는 것을 막는 유일한 지점.
if [ -z "${CP2K_DATA_DIR:-}" ] || [ ! -d "${CP2K_DATA_DIR}" ]; then
  echo "[P7] 🔴 CP2K_DATA_DIR 이 없다 → **측정하지 않는다**"
  echo "     이유: 기저·pseudopotential 파일을 못 찾으면 CP2K 는 죽지 않고 기본값으로"
  echo "           다른 계산을 한다. 그 단가는 우리가 물은 질문의 답이 아니다."
  printf '{"status": "data_dir_missing", "measured": false, "s_per_step": null, "cp2k": "%s"}\n' \
    "$CP2K" > "$D/p7_result.json"
  exit 5
fi

# --- 2) METHOD XTB 빌드 포함 여부 (독립성 판정용. 쓰려는 게 아니다) ---
printf '&FORCE_EVAL\n &DFT\n  &QS\n   METHOD XTB\n  &END\n &END\n&END\n' > "$D/xtbchk.inp"
"$CP2K" -i "$D/xtbchk.inp" --check > "$D/cp2k_xtb_check.txt" 2>&1 || true

# --- 3) s/step 측정 ---
if [ ! -f "${SEI_PKG_ROOT}/inputs/p7_cp2k/md.inp" ]; then
  echo "[P7] 입력이 동봉되지 않았다 → 환경 감사만 회신한다"
  printf '{"status": "input_missing", "measured": false, "s_per_step": null}\n' \
    > "$D/p7_result.json"
  exit 6
fi
cp "${SEI_PKG_ROOT}/inputs/p7_cp2k/"* "$D/" 2>/dev/null || true
sei_stage cp2k_md bash -c "cd '$D' && OMP_NUM_THREADS=1 mpirun -np ${NP} '${CP2K}' -i md.inp -o md.out"
RC=$?

PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$RC" <<'PY'
import json, os, re, sys
d, rc = sys.argv[1], int(sys.argv[2])
try:
    text = open(os.path.join(d, "md.out"), errors="replace").read()
except OSError:
    text = ""
# CP2K 는 "MD| Time per MD step [s]" 를 찍는다. 없으면 None 으로 둔다 — 추정하지 않는다.
m = re.findall(r"Time per MD step.*?([0-9.]+)", text)
steps = len(re.findall(r"MD\| Step number", text))
out = {"status": "ok" if rc == 0 else "cp2k_failed",
       "measured": bool(m), "rc": rc,
       "s_per_step": float(m[-1]) if m else None,
       "n_steps_seen": steps,
       "data_dir": os.environ.get("CP2K_DATA_DIR"),
       "note": ("🔴 s/step 은 이 계·이 노드(KNL)·이 코어수에서의 값이다. "
                "다른 계로 일반화하지 마라. 그리고 CP2K_DATA_DIR 확인을 통과한 "
                "실행만 measured=true 다.")}
json.dump(out, open(os.path.join(d, "p7_result.json"), "w"), ensure_ascii=False, indent=1)
print("[P7] s/step =", out["s_per_step"], "steps =", steps)
PY
exit 0
