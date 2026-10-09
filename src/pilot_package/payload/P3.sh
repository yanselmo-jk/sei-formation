#!/bin/bash
# P3 — EC 라디칼 1개의 gen-1 자동 탐색 (열거 + xTB TS 시도).
#   회신: 반응체당 candidate 수(분포), 시도 1건당 core-h, 수렴률.
#
# 🔴 열거 모드는 b2f2 그래프 편집(참조 구현)이다. ADR-006의 S2-A(fragment-recombine
#    + pool)와 **같은 fanout이 아니다.** 이 경고는 회신 JSON에도 자동으로 실린다.
#    엔진 무관하게 신뢰할 수 있는 회신은 '시도 1건당 core-h'와 '수렴률'이다.
#
# 시도는 서로 **다른** candidate에 대해 돌린다(같은 계를 60번 반복하면 수렴률이
# 의미를 잃는다). candidate 생성물 기하는 거친 추측이며 xTB opt가 극소를 만든다.
set -u
# 🔴 잡 템플릿은 이 스크립트를 **새 bash 프로세스**로 띄운다 → 셸 함수는 상속되지
#    않는다. sei_stage 를 쓰려면 여기서 직접 source 해야 한다(두 번 source 해도 안전).
source "${SEI_PKG_ROOT}/payload/common.sh"
D="${SEI_JOB_DIR}"
NP="${SEI_TOTAL_CORES:-1}"
MAX_ATTEMPTS="${SEI_P3_MAX_ATTEMPTS:-60}"     # >=50 이면 §R2-6 판정 기준 충족

# 🔴 xtb 탐지: **동봉본 → PATH → 추가경로**. 동봉본은 정적 링크지만 예상 밖 아키텍처에서
#    깨질 수 있다 → 실행을 실제로 시험하고, 실패하면 사유를 남기고 다음 수단으로 넘어간다.
#    (조용히 죽지 않는다.)
eval "$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$SEI_PKG_ROOT" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1])
from sei_pilot import envpaths
from sei_pilot.shellrun import Shell
v = envpaths.vendored("xtb", sys.argv[1])
if v:
    print('SEI_XTB=%s' % v["path"])
    for k, val in v["env"].items():
        print('export %s=%s' % (k, val))
else:
    print('SEI_XTB=%s' % (envpaths.resolve_tool(Shell(), "xtb", prefer_vendored=False) or ""))
PY
)"
XTB_SOURCE="vendored"
if [ -n "${SEI_XTB:-}" ]; then
  if ! "${SEI_XTB}" --version > "$D/xtb_version.txt" 2>&1; then
    echo "[P3] 🔴 동봉 xtb 실행 실패 (아키텍처/권한?) → 시스템 xtb 로 넘어간다"
    cat "$D/xtb_version.txt" | tail -5
    SEI_XTB="$(command -v xtb 2>/dev/null || true)"
    XTB_SOURCE="system_after_vendored_failed"
  fi
fi
[ -z "${SEI_XTB:-}" ] && { echo "[P3] xtb 없음(동봉본·시스템 모두) → 생략"; exit 3; }
export SEI_XTB
echo "{\"xtb_path\": \"${SEI_XTB}\", \"source\": \"${XTB_SOURCE}\"}" > "$D/xtb_source.json"
echo "[P3] xtb: ${SEI_XTB} (${XTB_SOURCE})"

# --- 1) 열거 + candidate 기하 생성 (우리 python. 외부 의존성 0) ---
sei_stage enumerate env PYTHONPATH="${SEI_PKG_ROOT}" SEI_JOB_DIR="$D" \
  SEI_MAX_ATTEMPTS="$MAX_ATTEMPTS" python3 - "$D" "${SEI_PKG_ROOT}" <<'PY'
import json, os, sys
sys.path.insert(0, sys.argv[2])
from sei_pilot.criteria.xyzgraph import read_xyz_frames
from sei_pilot import enumerate_gen1 as eg
d, root = sys.argv[1], sys.argv[2]
n_max = int(os.environ.get("SEI_MAX_ATTEMPTS", "60"))
atoms = read_xyz_frames(open(os.path.join(root, "inputs",
                                          "li_ec_radical_reactant.xyz")).read())[0][1]
res = eg.enumerate_for_reactant(atoms, mode="b2f2_graph_edit")
picked = eg.sample_candidates(res["candidates"], n_max)
os.makedirs(os.path.join(d, "attempts"), exist_ok=True)
tasks = []
for i, c in enumerate(picked, 1):
    w = os.path.join(d, "attempts", "a%03d" % i)
    os.makedirs(w, exist_ok=True)
    geom = eg.build_candidate_geometry(atoms, c)
    open(os.path.join(w, "product_guess.xyz"), "w").write(
        eg.to_xyz(geom, "candidate %d break=%s form=%s" % (i, c["break"], c["form"])))
    json.dump(c, open(os.path.join(w, "candidate.json"), "w"))
    tasks.append(w)
open(os.path.join(d, "tasks.txt"), "w").write("\n".join(tasks) + "\n")
res["completed"] = True
res["per_reactant_counts"] = [res["n_candidates"]]   # 반응체 1종이므로 표본 1개
res["n_attempted"] = len(picked)
res["pool_size"] = None
res.pop("candidates")           # 회신 JSON 비대화 방지 (원본은 tasks 디렉터리에 있다)
json.dump(res, open(os.path.join(d, "p3_enumeration.json"), "w"), indent=1)
print("candidates:", res["n_candidates"], "unique products:", res["n_unique_products"],
      "attempts:", len(picked))
PY

# --- 2) xTB TS 시도 (opt → RMSD-PP path). NP 코어로 병렬. ---
# [UNVERIFIED] `xtb --path` 옵션은 xtb 6.x 기준. 실패해도 수렴률 통계로 기록된다.
cat > "$D/path.inp" <<'EOF'
$path
   nrun=1
   npoint=25
   anopt=3
   kpush=0.003
   kpull=-0.015
$end
EOF
cp "${SEI_PKG_ROOT}/inputs/li_ec_radical_reactant.xyz" "$D/reactant.xyz"

cat > "$D/run_attempt.sh" <<'EOS'
#!/bin/bash
W="$1"; D="$2"
# SEI_XTB / XTBPATH 는 부모에서 export 되어 상속된다
t0=$(date +%s)
cd "$W" || exit 1
"${SEI_XTB}" product_guess.xyz --opt --chrg 0 --uhf 1 --gfn 2 -P 1 > opt.out 2>&1
rc_opt=$?
# 🔴 opt 실패 시 원본 추측 기하로 넘어가되, **그 사실을 결과에 싣는다.**
#    (여기가 `xtb` 를 그대로 써서 rc_opt=127 로 조용히 죽고, 최적화되지 않은 기하 위에서
#     수렴률을 재던 자리다. 환경 문제가 능력 측정값으로 둔갑하는 바로 그 실패다.)
opt_used=true
if [ ! -f xtbopt.xyz ]; then
  cp product_guess.xyz xtbopt.xyz
  opt_used=false
fi
"${SEI_XTB}" "$D/reactant.xyz" --path xtbopt.xyz --input "$D/path.inp" \
    --chrg 0 --uhf 1 --gfn 2 -P 1 > path.out 2>&1
rc=$?
t1=$(date +%s)
conv=false
grep -qiE "path converged|energy of TS|barrier \(kcal" path.out 2>/dev/null && conv=true
cat > result.json <<EOF
{"dir": "$W", "wall_s": $((t1-t0)), "cores": 1, "rc": $rc, "rc_opt": $rc_opt,
 "opt_applied": $opt_used, "converged": $conv}
EOF
EOS
chmod +x "$D/run_attempt.sh"

sei_stage xtb_attempts bash -c \
  "xargs -a '$D/tasks.txt' -P $NP -I{} '$D/run_attempt.sh' {} '$D'"

# --- 3) 결과 취합 ---
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" <<'PY'
import json, os, sys
d = sys.argv[1]
out = []
base = os.path.join(d, "attempts")
for name in sorted(os.listdir(base)) if os.path.isdir(base) else []:
    p = os.path.join(base, name, "result.json")
    try:
        out.append(json.load(open(p)))
    except (OSError, ValueError):
        out.append({"dir": name, "wall_s": 0, "cores": 1, "rc": -1,
                    "converged": False, "note": "result.json 없음(시도가 죽었다)"})
json.dump(out, open(os.path.join(d, "p3_attempts.json"), "w"), indent=1)
# 🔴 opt 가 실제로 적용된 시도가 몇 건인지 반드시 드러낸다. 이 수가 작으면
#    아래 수렴률은 **최적화되지 않은 기하 위에서 잰 값**이라 해석하면 안 된다.
n_no_opt = sum(1 for r in out if r.get("opt_applied") is False)
json.dump({"n_attempts": len(out), "n_opt_not_applied": n_no_opt,
           "convergence_rate_trustworthy": n_no_opt == 0,
           "note": ("opt 미적용 시도가 있으면 수렴률은 하한으로만 읽어라"
                    if n_no_opt else "")},
          open(os.path.join(d, "p3_attempt_quality.json"), "w"), ensure_ascii=False,
          indent=1)
print("attempts collected:", len(out), "| opt 미적용:", n_no_opt)
if n_no_opt:
    print("  🔴 opt 가 적용되지 않은 시도가 %d 건 — 수렴률 해석 주의" % n_no_opt)
PY
exit 0
