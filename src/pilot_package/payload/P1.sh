#!/bin/bash
# P1 — EC+Li+ 환원 라디칼 ring-opening TS 1건 완주 (**Gaussian16**).
#   단계: (crest) → ts_search(QST2) → [폴백 ts_opt] → freq 는 TS 단계에 포함 → irc 양방향
#   각 단계의 core-h는 sei_stage 가 stages/*.json 에 남긴다 (§R2-6 회신 요구사항).
#
# 자동 판정은 여기서 하지 않는다. 수집 단계(python)가 로그와 IRC 궤적을 읽고
# "허수진동 정확히 1개(-2000~-100 cm^-1) + IRC가 서로 다른 두 극소" 를 판정한다.
#
# 🔴 [내 결정 — proposer 확인 요망] ORCA 판은 NEB-TS(양끝단)를 썼는데 G16에는 NEB가
#    없다. 가장 가까운 양끝단 대응인 **QST2**로 포팅했고, 실패하면 반응물 기하에서
#    단끝단 opt=(ts,calcfc) 로 폴백한다. 어느 경로를 탔는지 ts_method.json 에 남는다.
#    P1의 목적은 "TS 1건 완주 단가"이므로 두 경로 모두 목적은 만족하지만 **단가는
#    경로에 따라 다르다** — 회신을 읽을 때 반드시 함께 보라.
set -u
# 🔴 잡 템플릿은 이 스크립트를 **새 bash 프로세스**로 띄운다 → 셸 함수는 상속되지
#    않는다. sei_stage 를 쓰려면 여기서 직접 source 해야 한다(두 번 source 해도 안전).
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
NP="${SEI_TOTAL_CORES:-1}"
LVL="${SEI_QC_LEVEL:-2}"      # 기본 = 주 레벨(G-1). --level g2 면 1이 넘어온다.
CHARGE=0
MULT=2      # 환원 라디칼 (doublet)

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  # 🔴 사유를 구분해 남긴다. 예전에는 전부 rc=3 으로 뭉개져 원인을 알 수 없었다.
  echo "[P1] QC 코드를 쓸 수 없다 → 생략"
  echo "  사유: ${SEI_QC_DETAIL:-(미상)}"
  echo "  시도한 모듈: ${SEI_QC_MODULE:-(없음)}"
  echo "  상세는 ${SEI_JOB_DIR}/adapter.json 에 있다"
  exit 3
fi
if ! sei_qc_smoke > "$D/smoke_result.txt" 2>&1; then
  echo "[P1] QC smoke 테스트 실패 → 본계산을 돌리지 않는다 (사용자 자원 보호)"
  cat "$D/smoke_result.txt"
  exit 4
fi

cp "${SEI_PKG_ROOT}/inputs/li_ec_radical_reactant.xyz" "$D/reactant.xyz"
cp "${SEI_PKG_ROOT}/inputs/li_ec_radical_product.xyz"  "$D/product.xyz"

# --- (선택) CREST conformer 표집 ---
# xtb 와 마찬가지로 동봉본 → PATH 순으로 찾는다. 없으면 단계를 생략한다(실패 아님).
CREST="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import envpaths
from sei_pilot.shellrun import Shell
print(envpaths.resolve_tool(Shell(), "crest") or "")' 2>/dev/null)"
if [ -n "${CREST}" ]; then
  sei_stage crest bash -c "cd '$D' && '${CREST}' reactant.xyz --gfn2 --chrg $CHARGE --uhf 1 -T $NP > crest.out 2>&1 && cp crest_best.xyz reactant.xyz"
  printf '{"crest_skipped": false, "crest_path": "%s"}\n' "${CREST}" > "$D/crest_status.json"
else
  # 🔴 ADR-044 / proposer §37: 여기가 "조용한 성공"이 나는 자리다.
  #    CREST 가 없으면 P1 은 **실패하지 않고** conformer 표집을 건너뛴 채 'pass' 로
  #    돌아온다. 그러면 우리가 core-h 를 주고 사는 TS 단가가 **과소평가된 채** 회신되고,
  #    받는 쪽은 그것을 완전한 TS 워크플로 단가로 읽는다.
  #    ⟹ rc 를 바꾸지 않는다(실패가 아니다). **대신 그 사실을 데이터로 남긴다.**
  echo "[P1] 🔴 crest 없음 → conformer 표집 생략. 이 실행은 degraded 다."
  echo "     ↳ 회신되는 TS 단가는 conformer 탐색 비용을 포함하지 않는다"
  echo "       (engineer [ESTIMATE]: TS 워크플로의 5~15%)."
  printf '{"crest_skipped": true, "crest_path": null}\n' > "$D/crest_status.json"
fi

# --- C-8 게이트: TS 탐색은 양끝단이 같은 level 의 수렴 극소(n_imag=0)가 아니면 ---
# --- **시작을 거부**한다 (lead 판정 C-8-1, ADR-090 item 5 의 ruling 착지). ---
# 🔴 이 게이트는 오늘 상태(끝단 인증 기록 없음 — 헤더 스스로 "GUESS GEOMETRY" 를
#    선언하는 입력)에서 **반드시 거부한다. 그게 옳은 동작이다** — RT-1 은 정확히 이
#    입력으로 302 core-h 를 태워 아티팩트 판정을 샀다(ADR-066). 조건을 느슨하게 해서
#    통과시키지 마라. ⚠ [H-2 satisfiability] 이 경로가 통과하려면 끝단 인증 기록
#    (endpoint_prep 의 산출물)을 읽는 배선이 필요한데, 그것은 방법론 확인이 필요한
#    다음 라운드 작업이다(lead 지시: 이번엔 거부 게이트까지만) — 즉 지금 이 게이트는
#    구조적으로 거부만 한다. 기존 guards.require_ts_precondition 을 부른다(새 판정
#    로직 없음), 브리지는 C-12 fallback_decision 과 같은 <<'PY' heredoc 형태다.
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/reactant.xyz" "$D/product.xyz" "$LVL" \
     "$D/c8_precondition.json" 2>"$D/c8_precondition.err" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import xyzgraph
r_path, p_path, level, out_path = sys.argv[1:5]
# 🔴 끝단 인증 기록이 아직 어디에도 없다 — optimised/converged/n_imag/level 전부
#    미지(unknown)다. Unknown is not permission (Rule 18): 이 dict 로는 guard 가
#    반드시 거부한다. 값을 지어 넣지 않는다.
# ⚠ SEI_C8_ENDPOINTS_JSON: 테스트 전용 데이터 주입 채널 (SEI_SOLVENT_POLICY_JSON 과
#    같은 이유 — bash 경계 너머의 이 heredoc 을 monkeypatch 할 수 없다). 판정은
#    여전히 guard 가 한다: 이 채널은 결정을 우회하지 않고 **입력 데이터**만 바꾼다.
#    잡 템플릿이 잡 시작 시 unset 하므로 실 클러스터 잡에는 닿지 않는다. 미래의
#    endpoint_prep 산출물 소비 배선이 이 자리를 대체한다(다음 라운드, 방법론 확인 후).
reactant = {"source": r_path}
product = {"source": p_path}
declared_planar = False
endpoints_source = "none_on_record"
inj = os.environ.get("SEI_C8_ENDPOINTS_JSON")
if inj:
    d = json.loads(inj)
    reactant.update(d.get("reactant") or {})
    product.update(d.get("product") or {})
    declared_planar = bool(d.get("declared_planar"))
    endpoints_source = "SEI_C8_ENDPOINTS_JSON [FIXTURE] -- test injection, not a certification"
geometry = xyzgraph.read_xyz_frames(open(r_path, errors="replace").read())[0][1]
level_key = level if str(level).startswith("level") else ("level%s" % level)
try:
    decision = guards.require_ts_precondition(
        reactant, product, required_level=level_key, geometry=geometry,
        declared_planar=declared_planar)
except guards.TSPreconditionError as exc:
    exc.decision["endpoints_source"] = endpoints_source
    json.dump(exc.decision, open(out_path, "w"), ensure_ascii=False, indent=1)
    sys.stderr.write("%s\n" % exc)
    sys.exit(1)
decision["endpoints_source"] = endpoints_source
json.dump(decision, open(out_path, "w"), ensure_ascii=False, indent=1)
PY
then
  echo "[P1] 🔴 C-8: TS 탐색 시작을 거부한다 — 양끝단이 같은 level 의 수렴 극소(n_imag=0)로 인증되지 않았다."
  echo "     사유 전문: $D/c8_precondition.json (요약은 아래)"
  sed 's/^/     ↳ /' "$D/c8_precondition.err" 2>/dev/null | head -10
  echo "     ↳ 끝단 인증은 endpoint_prep_{reactant,product} 가 만든다. P1 이 그 산출물을"
  echo "       읽는 배선은 다음 라운드(방법론 확인 필요) — 이번 라운드의 P1 거부는 의도다."
  exit 6
fi

# --- ts_search: QST2 (반응물 → 생성물 양끝단). freq 는 route 에 포함된다. ---
TS_METHOD="qst2"
TS_LOG="$D/ts_qst2.log"
if SEI_QC_XYZ2="$D/product.xyz" \
   sei_qc_input "$D/ts_qst2.gjf" "$LVL" ts_qst2 "$CHARGE" "$MULT" "$D/reactant.xyz" \
     > "$D/ts_qst2.meta.json" 2>"$D/ts_qst2.meta.err"; then
  sei_stage ts_qst2 sei_qc_run "$D" ts_qst2.gjf ts_qst2.log
else
  echo "[P1] QST2 입력 생성 실패:"; cat "$D/ts_qst2.meta.err"
  TS_METHOD="input_failed"
fi

# 🔴 [ADR-090 item 6, C-12] QST2 -> 단끝단 폴백. THE INCIDENT this fixes:
# `qc_levels.json:_ts_method`'s OLD rule fired the fallback ONLY on abnormal termination
# (a bare `grep "Normal termination"`, exactly like the old `if !` line below used to be) --
# QST2 CONVERGED, to a saddle of the wrong coordinate, so the fallback never fired and 302
# core-h bought a wrong answer (§39.13(a)). The decision is now made by
# `guards.fallback_decision`, via the SAME `python3 - <<'PY'` bridge this script already
# uses four times elsewhere -- the shell does NOT restate the rule, it asks Python and obeys
# the answer (ADR-090 ruling item 4). `exit_ok` (normal termination) is recorded and does
# NOT decide; the ACCEPTANCE test does.
FALLBACK_DECISION_JSON="$D/ts_qst2_fallback_decision.json"
FALLBACK_VERDICT="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$TS_LOG" "$FALLBACK_DECISION_JSON" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import g16
log_path, out_path = sys.argv[1], sys.argv[2]
try:
    text = open(log_path, errors="replace").read()
except OSError:
    text = ""
summ = g16.summarize(text)
freqs = g16.parse_frequencies(text)
n_imag = sum(1 for f in freqs if f < 0) if freqs else 0
# 🔴 THE ACCEPTANCE TEST -- not the exit status. A TS candidate that terminated cleanly but
# is not a genuine first-order saddle (0 or >1 imaginary modes) is exactly the "converged to
# the wrong coordinate" shape of the incident; catching THAT is the point of C-12 here.
acceptance = {
    "normal_termination": summ.get("normal_termination"),
    "opt_converged": (summ.get("opt") or {}).get("converged"),
    "exactly_one_imaginary_mode": (n_imag == 1) if freqs else None,
}
decision = guards.fallback_decision(exit_ok=summ.get("normal_termination"),
                                    acceptance=acceptance)
decision["n_imaginary_modes_observed"] = n_imag
decision["n_frequencies_parsed"] = len(freqs)
json.dump(decision, open(out_path, "w"), ensure_ascii=False, indent=1)
print("fires" if decision["fallback_fires"] else "accepted")
PY
)"
if [ "${FALLBACK_VERDICT}" = "fires" ]; then
  echo "[P1] QST2 결과가 인수 시험(C-12)을 통과하지 못했다 → 단끝단 opt=(ts,calcfc) 로 폴백"
  echo "     ↳ 근거: ${FALLBACK_DECISION_JSON}"
  TS_METHOD="ts_opt_from_reactant_fallback"
  TS_LOG="$D/ts_opt.log"
  sei_qc_input "$D/ts_opt.gjf" "$LVL" ts_opt_from_guess "$CHARGE" "$MULT" \
    "$D/reactant.xyz" > "$D/ts_opt.meta.json" 2>&1 \
    && sei_stage ts_opt sei_qc_run "$D" ts_opt.gjf ts_opt.log
fi

cat > "$D/ts_method.json" <<EOF
{"method": "${TS_METHOD}", "log": "$(basename "$TS_LOG")", "level": "level${LVL}",
 "note": "ORCA 판의 NEB-TS 를 G16 QST2 로 포팅. 폴백은 단끝단. 단가는 경로마다 다르다."}
EOF

# --- TS 기하 추출 (수집 단계와 P1b 가 쓴다) ---
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$TS_LOG" "$D" <<'PY'
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
log, d = sys.argv[1], sys.argv[2]
try:
    text = open(log, errors="replace").read()
except OSError:
    text = ""
geom = g16.last_geometry(text)
if geom:
    open(os.path.join(d, "ts.xyz"), "w").write(
        "%d\nP1 TS (from %s)\n" % (len(geom), os.path.basename(log))
        + "".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
    print("TS 기하 %d원자 추출" % len(geom))
else:
    print("🔴 TS 기하를 추출하지 못했다 — IRC 단계를 건너뛴다")
PY

if [ ! -f "$D/ts.xyz" ]; then
  echo "[P1] TS 기하 없음 → IRC 생략. 여기까지의 단가는 stages/ 에 남아 있다."
  exit 5
fi

# --- irc: 양방향 (판정 입력 2) ---
for dir in forward reverse; do
  sei_qc_input "$D/irc_${dir}.gjf" "$LVL" "irc_${dir}" "$CHARGE" "$MULT" "$D/ts.xyz" \
    > "$D/irc_${dir}.meta.json" 2>&1 || continue
  sei_stage "irc_${dir}" sei_qc_run "$D" "irc_${dir}.gjf" "irc_${dir}.log"
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/irc_${dir}.log" "$D/irc_${dir}.xyz" <<'PY'
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
log, out = sys.argv[1], sys.argv[2]
try:
    text = open(log, errors="replace").read()
except OSError:
    sys.exit(0)
frames = g16.parse_geometries(text)
if frames:
    with open(out, "w") as fh:
        for fr in frames:
            fh.write("%d\nIRC frame\n" % len(fr))
            fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in fr))
PY
done

echo "[P1] 완료 (TS 경로=${TS_METHOD}). 판정은 수집 단계가 한다."
exit 0
