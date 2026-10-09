#!/bin/bash
# U56.sh — U56-2 (ADR-109 / §39.39(d)) TS attempt, ONE reaction x ONE method per plan Item.
#   relaxed_scan : scan(opt=modredundant, coordinate FROM the role→index mapping)
#                  → opt=(ts,calcfc)+freq → IRC forward/reverse      (single-ended)
#   qst2         : QST2(calcfc)+freq → IRC forward/reverse           (double-ended, R-A only)
#
# 🔴 P1 은 영구 제외다(ADR-109 전문). 이 스크립트는 P1.sh 의 *형태*(C-8 heredoc 브리지,
#    IRC 추출)를 복사 원형으로 쓰되 P1 이 아니다: level 은 B0-F composite 의
#    geometry+Hessian 레벨(config/b0_reactions.json `level`), 끝단은 endpoint_prep 의
#    **실제 인증 산출물**에서 오고, QST2 arm 에는 단끝단 폴백이 **없다** — bake-off 에서
#    method 를 갈아타면 비교 자체가 오염된다(§39.39(d) read-out rule). 폴백 대신
#    인수시험 결과를 데이터로 남긴다.
#
# 항목당 env (plan.py u56_2_items() 가 선언):
#   SEI_U56_REACTION              R-A | R-B | R-C
#   SEI_U56_METHOD                relaxed_scan | qst2
#   SEI_U56_REACTANT_ENDPOINT_KEY reactant 인증을 만든 plan 항목 key (jobs/<key>/ 를 읽는다)
#   SEI_U56_PRODUCT_ENDPOINT_KEY  product 인증 항목 key -- qst2 는 필수(없으면 exit 1),
#                                 relaxed_scan 은 선택(선언되면 bracket check 양방향 half 를
#                                 켠다, §39.113(d); 없어도 단끝단 진행은 그대로 된다)
# 테스트/디버그 채널 (잡 템플릿이 잡 시작 시 unset — 우회 불가):
#   SEI_C8_ENDPOINTS_JSON         인증 데이터 주입 (판정은 여전히 guard 가 한다)
#   SEI_U56_REACTANT_XYZ / SEI_U56_PRODUCT_XYZ   기하 파일 대체 (인증 로그가 없을 때만)
#   SEI_U56_STOP_AFTER            [§39.136 다섯째 addendum, RULED (a)] 미설정 시 순수
#                                 no-op(모든 줄이 이전과 동일 순서로 실행) -- 설정 시 그
#                                 스테이지의 정상 완료+정상 산출물 기록 **직후**, 정상 완주도
#                                 오류도 아닌 명시적 마커(exit 5)로 정지한다. 현재 `u56_scan`
#                                 한 곳에만 연결됨(T21-se stage 1 circuit-breaker 전용, 다른
#                                 스테이지 경계는 필요해질 때 한 줄로 추가).
#
# exit: 2=입력/env 오류  3=QC 없음  4=smoke/용매 거부  5=SEI_U56_STOP_AFTER 에 의한 의도적
#       정지(§39.136)  6=C-8 거부(덱 생성 전)  8=mapping 미해결(덱 생성 거부, §39.26(d))
#       0=완주(판정은 수집 단계)
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"
D="${SEI_JOB_DIR}"
RXN="${SEI_U56_REACTION:-}"
METHOD="${SEI_U56_METHOD:-}"
CHARGE=0
MULT=2      # 세 반응 모두 환원 라디칼 doublet (b0_reactions.json)

# 🔴 [terminal_status fix, §39.80(g)(i)] endpoint_prep.sh 의 `_write_terminal` 과 같은
#    모양이다. 이 payload 는 C-2/IRC pass 판정을 내리지 않는다(그건 수집 단계 몫,
#    u56_attempt.json 의 note 그대로) -- 여기서는 payload 자신이 아는 것(어디까지 갔고
#    어디서 멈췄는지)만 정직하게 적는다. 이게 없으면 rc=0 완주 잡도 harness 의
#    state 마커에서 outcome=absent, cause_class=absent 로 읽혀 실제로 일어난 일을 숨긴다.
_write_terminal() {
  sei_terminal "$1" "$2" "reaction=${RXN}" "method=${METHOD}" "level=${LVL:-}"
}

# 🟢 [02_METHOD_SPEC.md §39.136, fifth addendum, proposer13 RULED (a) over a standalone
#    bypass builder] T21-se's staged/circuit-breaker protocol needs to submit stage 1 (scan)
#    ALONE and stop -- deciding stage 2+ only after reading stage 1's real result -- without
#    risking this project's own most expensively-repeated lesson ("a number divorced from its
#    route measures an unknown job", the same failure class the T21-se cube-law retraction
#    itself is an instance of). Running scan through THIS SAME CODE, rather than a separate
#    builder that could drift from it, makes the measured cost the production-chain anchor BY
#    CONSTRUCTION, not something to verify.
#
#    UNSET (default, the only case that matters for R-B or any other already-validated
#    attempt): `_sei_u56_stop_after_check` is a pure, additive early-exit test -- when the
#    stage name does not match, it is a no-op `return 0` and every line that ran before this
#    change still runs in the same order. This is what makes "bit-identical on the unset
#    path" a property of the code SHAPE, not just a test result -- critic17 must verify this
#    directly (diff against a known-good prior run, or a code-level no-op proof) BEFORE this
#    modified harness is used for R-B or anything else (§39.136 fifth addendum's own
#    sequencing requirement).
#
#    SET to a stage name: called only AFTER that stage's own normal completion and own normal
#    output-writing (same files/format/location any run would use) -- exits with a distinct,
#    unambiguous marker via the SAME `_write_terminal` C-13 mechanism already used elsewhere
#    in this file for "reached here, wrote what I have, stopped" (wall_exhausted, etc.), exit
#    code 5 -- not a bare `exit 0` (could be misread as full completion) and not an existing
#    error code.
#
#    🔴 Only wired at ONE boundary right now (`u56_scan`, immediately after stage 1's own
#    stage-checkpoint call) -- that is the only stage this round's ruling actually needs
#    staged submission for (T21-se stage 1). The check itself is stage-name-generic and takes
#    one line to wire at any other stage-checkpoint boundary in this file (u56_scan_refine/
#    u56_tsopt/u56_qst2/u56_irc/u56_bplus) whenever a future round actually needs to stop
#    there -- not wired speculatively ahead of that need.
_sei_u56_stop_after_check() {
  [ "${SEI_U56_STOP_AFTER:-}" = "$1" ] || return 0
  echo "[U56] SEI_U56_STOP_AFTER=$1 -- stopping here by request (staged circuit-breaker, §39.136)"
  _write_terminal "stopped_after_stage" \
    "deliberate stop after stage '$1' per SEI_U56_STOP_AFTER -- not an error, not full completion"
  exit 5
}

# 🔴 [critic14, linear-hopping-frog Track A] WALL TRIPWIRE, copied from P5.sh's existing
#    pattern (§ "wall_exhausted") rather than invented. U56.sh has NO SIGTERM trap and no
#    wall-clock check -- unlike P5.sh/endpoint_prep.sh -- and the payload's own comment further
#    down already says the wall cap (ADR-114, 48h) is not visible inside the payload, which
#    leaves this trap as the only available mechanism. Without it, an attempt killed at the
#    cap dies before it can reach any `_write_terminal`/`sei_terminal_from_logs` call, lands
#    back on `outcome: absent` -- the exact state this whole fix removes -- and `absent` is
#    never retried (outcome.py), so the item silently stalls forever. Didn't bite this round
#    only because U56_RA_scan used 5.3h of 48; the 21-atom R-C attempt sits closest to the cap.
#    PBS sends SIGTERM before SIGKILL, so this is the one chance to write the marker.
trap '_write_terminal "wall_exhausted" "SIGTERM from the scheduler while running ${U56_CURRENT_STAGE:-unknown}"; exit 9' TERM

case "$RXN" in R-A|R-B|R-C) ;; *)
  echo "[U56] SEI_U56_REACTION=R-A|R-B|R-C 가 필요하다 (받은 값: '${RXN}')"
  _write_terminal "input_error" "SEI_U56_REACTION must be R-A|R-B|R-C, got '${RXN}'"
  exit 2 ;;
esac
case "$METHOD" in relaxed_scan|qst2) ;; *)
  echo "[U56] SEI_U56_METHOD=relaxed_scan|qst2 가 필요하다 (받은 값: '${METHOD}')"
  _write_terminal "input_error" "SEI_U56_METHOD must be relaxed_scan|qst2, got '${METHOD}'"
  exit 2 ;;
esac

# --- level: B0-F composite 의 geometry+Hessian 레벨. config 단일 출처, 하드코딩 금지. ---
LVL="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import config
lvl = (config.load("b0_reactions.json", {}).get("level") or {}).get("geometry_and_hessian")
print(lvl or "")')"
if [ -z "$LVL" ]; then
  echo "[U56] b0_reactions.json 의 level.geometry_and_hessian 이 없다 — 레벨을 지어 넣지 않는다"
  _write_terminal "input_error" "b0_reactions.json level.geometry_and_hessian is missing"
  exit 2
fi

sei_qc_detect
if [ "${SEI_QC}" = "none" ]; then
  echo "[U56] QC 코드를 쓸 수 없다 → 생략. 사유: ${SEI_QC_DETAIL:-(미상)}"
  _write_terminal "skipped" "no QC engine available (${SEI_QC_DETAIL:-unknown})"
  exit 3
fi
# route smoke — S-1 의 ε 실증(deck_verification)이 여기서 만들어져 본계산 pcm 게이트를 연다.
if ! sei_qc_smoke > "$D/smoke_result.txt" 2>&1; then
  echo "[U56] route smoke 실패 → 본계산을 돌리지 않는다:"
  tail -15 "$D/smoke_result.txt"
  _write_terminal "route_smoke_failed" "sei_qc_smoke failed (deck/route not validated)"
  exit 4
fi

# --- 끝단 인증 해석: endpoint_prep 산출물(f1_observables/terminal/meta)을 읽어 cert 를 ---
# --- 만들고, 인증 로그의 수렴 기하를 시작 기하로 추출한다. §39.39(h)의 "회신 전 배선". ---
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$RXN" "$METHOD" "$LVL" \
     2>"$D/endpoint_resolve.err" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
from sei_pilot import solvent as solvent_mod

d, rxn, method, level = sys.argv[1:5]
workdir = os.environ.get("SEI_WORKDIR") or ""

def read_json(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None

def resolve(role, endpoint_key, xyz_override):
    """(cert dict, 기하 xyz 경로 or None, source 설명, declared_planar)"""
    cert = {}
    geom_path = None
    source = []
    ep_dir = os.path.join(workdir, "jobs", endpoint_key) if endpoint_key else None
    if ep_dir and os.path.isdir(ep_dir):
        f1 = read_json(os.path.join(ep_dir, "f1_observables.json")) or {}
        meta = read_json(os.path.join(ep_dir, "endpoint_tight.meta.json")) or {}
        terminal = read_json(os.path.join(ep_dir, "terminal_status.json")) or {}
        if f1:
            # 🔴 값을 지어 넣지 않는다: 없는 필드는 None 그대로 → guard 가 거부한다.
            cert = {
                "optimised": (f1.get("normal_termination") is True
                              and f1.get("opt_converged") is True) or None,
                "converged": f1.get("opt_converged"),
                "n_imag": f1.get("n_imag_at_convergence"),
                "level": meta.get("level"),
                # 🔴 [§39.124 Ruling 1, corrected A4, critic16 B1] the reactant-match energy
                # clause's data source -- a STRUCTURED field emitted by `endpoint_prep.sh` at
                # certification time, copied through here, NEVER re-derived by re-parsing a
                # log from a different job's directory at gate time (critic16, explicit: "do
                # not implement it as a cross-job log grep"). `None` on an older cert that
                # predates this field is the correct, honest answer (Rule 18). 🔴 [critic17,
                # 37th review batch] `SEI_C8_ENDPOINTS_JSON` (below) is NOT a remedy for that
                # case -- see the corrected note further down in this file's own `PYBPLUS`
                # block (search this file for "does NOT backfill" -- not a line number, which
                # has already drifted once from a comment edit exactly like this one) for why,
                # and do not re-add a pointer to it here.
                "energy_hartree": f1.get("energy_hartree"),
                "source": "%s/f1_observables.json (endpoint_prep certificate, "
                          "terminal=%s)" % (ep_dir, terminal.get("status")),
            }
            source.append("cert:endpoint_prep(%s)" % endpoint_key)
            # 🔴 [§39.92/§39.93/§39.101, lead 2026-08-21] the certificate must have been
            #    computed under the CURRENT production METHOD (level, functional, basis, grid,
            #    solvent deck) -- the one this U56-2 search runs at. Anything else (level3,
            #    default grid, the abandoned `solvent=generic` deck, a bracket arm) is refused
            #    here by blanking n_imag -- the guard never accepts None -- reason on record.
            ok, why = solvent_mod.certificate_matches_production(meta, level_key=level)
            cert["solvent_config"] = why
            cert["solvent_route"] = meta.get("route")
            if not ok:
                cert["n_imag"] = None
                cert["optimised"] = None
                cert["refused"] = why
                source.append("cert:REFUSED(%s)" % why.split(":")[0])
        log = os.path.join(ep_dir, "endpoint_tight.log")
        if os.path.exists(log):
            geom = g16.last_geometry(open(log, errors="replace").read())
            if geom:
                geom_path = os.path.join(d, "%s_certified.xyz" % role)
                with open(geom_path, "w") as fh:
                    fh.write("%d\ncertified %s endpoint (from %s)\n"
                             % (len(geom), role, log))
                    fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
                source.append("geometry:endpoint_tight.log")
    declared_planar = False
    inj = os.environ.get("SEI_C8_ENDPOINTS_JSON")
    if inj:
        data = json.loads(inj)
        cert = dict(cert or {})
        cert.update(data.get(role) or {})
        declared_planar = bool(data.get("declared_planar"))
        source.append("cert:SEI_C8_ENDPOINTS_JSON [FIXTURE] -- test injection, "
                      "not a certification")
    if geom_path is None and xyz_override:
        if os.path.exists(xyz_override):
            geom_path = xyz_override
            source.append("geometry:SEI_U56_%s_XYZ override (%s) -- NOT the certified "
                          "geometry" % (role.upper(), xyz_override))
    return cert, geom_path, source, declared_planar

r_cert, r_xyz, r_src, planar = resolve(
    "reactant", os.environ.get("SEI_U56_REACTANT_ENDPOINT_KEY"),
    os.environ.get("SEI_U56_REACTANT_XYZ"))
p_cert, p_xyz, p_src = {}, None, []
# 🔴 [§39.113(d), proposer -- housekeeping] resolve the product cert whenever the item DECLARES
#    one, not only for qst2. relaxed_scan does not NEED a product to start (single-ended), but
#    the bracket check below runs its two-sided half only when a product cert is on record --
#    without this, two attempts at the SAME reaction (scan vs qst2) got evaluated on unequal
#    footing. Still OPTIONAL for scan: only qst2 refuses below if none resolves.
if method == "qst2" or os.environ.get("SEI_U56_PRODUCT_ENDPOINT_KEY"):
    p_cert, p_xyz, p_src, planar2 = resolve(
        "product", os.environ.get("SEI_U56_PRODUCT_ENDPOINT_KEY"),
        os.environ.get("SEI_U56_PRODUCT_XYZ"))
    planar = planar or planar2

record = {"reaction": rxn, "method": method, "required_level": level,
          "reactant_cert": r_cert, "reactant_xyz": r_xyz, "reactant_source": r_src,
          "product_cert": p_cert or None, "product_xyz": p_xyz,
          "product_source": p_src or None, "declared_planar": planar}
json.dump(record, open(os.path.join(d, "endpoint_certs.json"), "w"),
          ensure_ascii=False, indent=1)
if r_xyz is None:
    sys.stderr.write("no reactant geometry source: endpoint_prep log absent/unparsable "
                     "and no override. Refusing -- a TS attempt cannot start from a "
                     "geometry that does not exist.\n")
    sys.exit(1)
if method == "qst2" and p_xyz is None:
    sys.stderr.write("qst2 needs a product geometry and none exists on record.\n")
    sys.exit(1)
PY
then
  echo "[U56] 끝단 기하/인증 해석 실패:"
  sed 's/^/     ↳ /' "$D/endpoint_resolve.err" 2>/dev/null | head -8
  _write_terminal "endpoint_geometry_missing" "no certified endpoint geometry on record for this reaction/method"
  exit 6
fi

# --- C-8 게이트: 덱 생성 **전**. relaxed_scan 은 단끝단 C-8(§39.32 Candidate B), ---
# --- qst2 는 양끝단 C-8. 인증 안 된 끝단이면 여기서 exit 6 — P1 과 같은 구분 코드. ---
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" 2>"$D/c8_precondition.err" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import xyzgraph

d = sys.argv[1]
rec = json.load(open(os.path.join(d, "endpoint_certs.json")))
geometry = xyzgraph.read_xyz_frames(
    open(rec["reactant_xyz"], errors="replace").read())[0][1]
try:
    if rec["method"] == "relaxed_scan":
        decision = guards.require_single_ended_ts_precondition(
            rec["reactant_cert"], required_level=rec["required_level"],
            geometry=geometry, declared_planar=rec["declared_planar"])
    else:
        decision = guards.require_ts_precondition(
            rec["reactant_cert"], rec["product_cert"] or {},
            required_level=rec["required_level"], geometry=geometry,
            declared_planar=rec["declared_planar"])
except guards.TSPreconditionError as exc:
    exc.decision["endpoints_source"] = rec["reactant_source"]
    json.dump(exc.decision, open(os.path.join(d, "c8_precondition.json"), "w"),
              ensure_ascii=False, indent=1)
    sys.stderr.write("%s\n" % exc)
    sys.exit(1)
decision["endpoints_source"] = rec["reactant_source"]
json.dump(decision, open(os.path.join(d, "c8_precondition.json"), "w"),
          ensure_ascii=False, indent=1)
PY
then
  echo "[U56] 🔴 C-8: TS 탐색 시작을 거부한다 — 끝단이 이 레벨의 인증된 극소가 아니다."
  echo "     사유 전문: $D/c8_precondition.json"
  sed 's/^/     ↳ /' "$D/c8_precondition.err" 2>/dev/null | head -10
  _write_terminal "c8_precondition_refused" "C-8 refused before deck generation -- endpoint(s) not a certified minimum at this level"
  exit 6
fi

# --- B-2: deck builder — role→index mapping 을 덱 **옆에** emit. 미해결이면 덱 생성 ---
# --- 자체가 거부된다(exit 8, 구분 코드): mapping 없는 덱은 Ω 채점 불가(§39.26(d)). ---
REACTANT_XYZ="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import json, os, sys
print(json.load(open(os.path.join(os.environ["SEI_JOB_DIR"], "endpoint_certs.json")))["reactant_xyz"])')"
WITH_SCAN="True"; [ "$METHOD" = "qst2" ] && WITH_SCAN="False"
if ! PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$RXN" "$REACTANT_XYZ" "$D" "$WITH_SCAN" \
     2>"$D/deck_builder.err" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import b0f_deck, roles

rxn, xyz, d, with_scan = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "True"
try:
    summary = b0f_deck.build_deck_inputs(rxn, xyz, d, with_scan_section=with_scan)
except roles.MappingRequiredError as exc:
    json.dump({"refused": True, "reason": str(exc), "reaction": rxn,
               "constraint": "§39.26(d): a deck without its mapping cannot be scored"},
              open(os.path.join(d, "mapping_refusal.json"), "w"),
              ensure_ascii=False, indent=1)
    sys.stderr.write("%s\n" % exc)
    sys.exit(1)
except b0f_deck.DeckInputError as exc:
    json.dump({"refused": True, "reason": str(exc), "reaction": rxn},
              open(os.path.join(d, "mapping_refusal.json"), "w"),
              ensure_ascii=False, indent=1)
    sys.stderr.write("%s\n" % exc)
    sys.exit(1)
print(json.dumps(summary, ensure_ascii=False))
PY
then
  echo "[U56] 🔴 mapping/deck 입력 거부 — 덱을 만들지 않는다 (사유: $D/mapping_refusal.json)"
  sed 's/^/     ↳ /' "$D/deck_builder.err" 2>/dev/null | head -6
  _write_terminal "mapping_unresolved" "role->index mapping unresolved (§39.26(d)) -- no deck built"
  exit 8
fi

TS_LOG=""
STATUS="ts_candidate_produced"
if [ "$METHOD" = "relaxed_scan" ]; then
  # ============================================================================
  # 🔴 G-SCAN-4 (§39.45(a)) — 불연속 gate 의 **자금 집행 지점**.
  # 여기 아래의 DFT scan / ts_opt / freq / IRC 가 돈이 나가는 곳이다. 발동 시 회피 비용
  # ~660 core-h(11원자) / ~6,400(21원자).
  #
  # 🔒 판정은 여기서 하지 않는다. §39.47(a): gate 의 목적은 **DFT 시도에 돈을 댈지** 정하는
  #    것이고 TS guess 는 GFN2 에서 만들어지므로, 판정도 GFN2 에서 공짜로 끝난다.
  #    **DFT scan 은 그 GFN2 판정을 상속받아 단방향으로만 돈다.** 여기서 양방향 DFT scan 을
  #    돌리는 것은 (a) 비용을 두 배로 만들고 (b) `TOTAL_POINTS_MAX = 20`(DFT·단방향)을
  #    깨뜨리며 (c) hysteresis 는 엔진의 성질이 아니라 relaxed scan 과 반응 차원수의
  #    성질이라 GFN2 가 이미 답을 준 질문을 DFT 로 다시 사는 것이다.
  #
  # 🔴 판정이 **없으면 진행하지 않는다.** ungated guess 위에 DFT 를 발주하는 것은
  #    gate 를 만든 이유 자체를 무효로 만든다("한 번도 안 터지면 unreached", G-SCAN-5).
  #    ⚠ 이 판정을 만드는 GFN2 사전 stage 는 **아직 없다**(coder10 인계 항목,
  #    §39.47(a) 의 "no cheap surface" 예외와는 다른 사안 — 여기서는 GFN2 경로가
  #    존재해야 마땅한데 자동화가 미완인 것이다). 그때까지 이 arm 은 시끄럽게 거부한다.
  # ============================================================================
  # ==========================================================================
  # 🔴 [G-SCAN-1, §39.45(a)] THE GFN2 BIDIRECTIONAL PRE-STAGE — the gate's PRODUCER.
  # Runs the relaxed scan BOTH ways on ONE grid at GFN2 and renders the verdict here,
  # BEFORE any DFT is ordered. §39.47(a): the gate decides whether to fund the DFT
  # attempt and the TS guess is made at GFN2, so the check runs where it is free —
  # 24 points against a cap of 512, versus a DFT cap of 20 for ONE direction.
  # 🔒 In-job rather than a separate plan Item on purpose: a separate Item would cost a
  # full round trip (~3.5 days) to get a verdict that takes seconds, and the DFT spend
  # this gate protects (~660 core-h at 11 atoms, ~6,400 at 21) has not happened yet when
  # it runs. The idle cores during the xtb seconds are the price and they are recorded.
  # ==========================================================================
  if [ ! -f "$D/gscan_verdict.json" ] && [ ! -f "${SEI_JOB_DIR}/gscan_verdict.json" ]; then
    eval "$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$SEI_PKG_ROOT" <<'PYXTB'
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
PYXTB
)"
    if [ -z "${SEI_XTB:-}" ] || ! "${SEI_XTB}" --version > "$D/xtb_version.txt" 2>&1; then
      echo "[U56] 🔴 xtb unavailable — cannot produce the G-SCAN verdict, so the"
      echo "     single-ended arm is NOT ordered. An ungated guess is exactly what this"
      echo "     gate exists to prevent; running the DFT anyway would spend the money the"
      echo "     gate protects on a guess nobody checked."
      _write_terminal "gfn2_prestage_unavailable" "xtb unavailable -- G-SCAN pre-stage verdict could not be produced, DFT not ordered"
      exit 9
    fi
    export SEI_XTB
    GS0=$(date +%s)
    PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "$RXN" "$REACTANT_XYZ" "$CHARGE" "$MULT" <<'PYGSCAN'
import json, os, subprocess, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import b0f_deck, gfn2_scan, guards
from sei_pilot.criteria import xyzgraph

d, rxn, reactant_xyz, charge, mult = sys.argv[1:6]
xtb = os.environ["SEI_XTB"]
params = b0f_deck.scan_params(engine="gfn2")
record = json.load(open(os.path.join(d, "u56_%s_mapping.json" % rxn)))
breaks = [e["selected"] for e in (record["mapping"].get("break") or []) if e.get("selected")]
if not breaks:
    raise SystemExit("no resolved break bond -- the mapping gate should have caught this")
i, j = breaks[0]
atoms = xyzgraph.read_xyz_frames(open(reactant_xyz, errors="replace").read())[0][1]
plan = gfn2_scan.bidirectional_plan(atoms, (i, j), params["coarse_n_steps"],
                                    params["coarse_step_ang"])

def run(tag, start_xyz, lo, hi):
    w = os.path.join(d, "gscan_%s" % tag)
    os.makedirs(w, exist_ok=True)
    with open(os.path.join(w, "start.xyz"), "w") as fh:
        fh.write(start_xyz)
    with open(os.path.join(w, "scan.inp"), "w") as fh:
        fh.write(gfn2_scan.scan_input(plan["pair_1based"], lo, hi, plan["n_points"]))
    # 🔴 [ADR-110] xtb is single-threaded here BY DECLARATION, not by default: the job's
    #    core count reflects the G16 work, not this, and the two must not be conflated.
    rc = subprocess.call([xtb, "start.xyz", "--opt", "--input", "scan.inp",
                          "--chrg", charge, "--uhf", str(int(mult) - 1),
                          "--gfn", "2", "-P", "1"],
                         cwd=w, stdout=open(os.path.join(w, "scan.out"), "w"),
                         stderr=subprocess.STDOUT)
    prof = gfn2_scan.read_log(os.path.join(w, "xtbscan.log"))
    prof["rc"] = rc
    prof["xtb_threads"] = 1
    # 🔴 WHY it failed, not just THAT it failed. An SCF that will not converge on a stretched
    #    open-shell radical is a normal, expected outcome of this chemistry; a broken input is
    #    ours. `rc != 0` cannot tell them apart and they have different owners.
    try:
        prof["failure"] = gfn2_scan.parse_failure(
            open(os.path.join(w, "scan.out"), errors="replace").read())
    except OSError:
        prof["failure"] = {"aborted": rc not in (0, None), "cause": None, "kind": "other"}
    return prof

# 🔴 [§39.68(1)] STARTING GEOMETRY: the C-8-certified (DFT) reactant, then a **CONSTRAINED**
# GFN2 relaxation holding d_break at the certified value.
# 🔴 NEVER FREE. Measured: a free GFN2 `--opt` of the reduced radical LEAVES the ring-closed
# basin outright, after which the scan starts from an already-opened structure and the forward
# barrier reads ~15 eV. Same class as §39.42(a)'s kicked seeds and ADR-067's n_imag = 5 -- an
# idealised guess relaxed without a leash goes somewhere else. The constraint's whole job is to
# preserve the basin while the rest of the structure settles.
# 🔴 [§39.68(2)] The scan is then anchored on the **PRE-RELAXED** d, not the raw certified one:
# after this step the two differ, and the scan must start where the structure actually is.
# Anchoring on the raw distance is what made frame 0 arrive still descending (-0.383 eV between
# points 1 and 2), which false-fired the gate at 0.4530 eV against a true 0.0216.
prerelax = os.path.join(d, "gscan_prerelax")
os.makedirs(prerelax, exist_ok=True)
with open(os.path.join(prerelax, "start.xyz"), "w") as fh:
    fh.write(open(reactant_xyz, errors="replace").read())
with open(os.path.join(prerelax, "relax.inp"), "w") as fh:
    fh.write(gfn2_scan.constrain_input(plan["pair_1based"], plan["d_start_ang"]))
pre_rc = subprocess.call([xtb, "start.xyz", "--opt", "--input", "relax.inp",
                          "--chrg", charge, "--uhf", str(int(mult) - 1),
                          "--gfn", "2", "-P", "1"],
                         cwd=prerelax, stdout=open(os.path.join(prerelax, "opt.out"), "w"),
                         stderr=subprocess.STDOUT)
try:
    pre_out = open(os.path.join(prerelax, "opt.out"), errors="replace").read()
except OSError:
    pre_out = ""
# 🔴 read xtb's own words; a zero exit code is not convergence (§39.68(3)(i))
pre_converged = gfn2_scan.prerelax_converged(pre_out)
relaxed_path = os.path.join(prerelax, "xtbopt.xyz")
if pre_converged and os.path.exists(relaxed_path):
    start_text = open(relaxed_path, errors="replace").read()
    relaxed_atoms = xyzgraph.read_xyz_frames(start_text)[0][1]
    plan = gfn2_scan.bidirectional_plan(relaxed_atoms, (i, j), params["coarse_n_steps"],
                                        params["coarse_step_ang"])
else:
    start_text = open(reactant_xyz, errors="replace").read()

fwd = run("forward", start_text, *plan["forward"])
if fwd["points"]:
    rev = run("reverse", gfn2_scan.frame_xyz(fwd["points"][-1],
                                             "forward scan final frame"), *plan["reverse"])
else:
    rev = {"hamiltonian": "gfn2", "points": [], "n_points": 0,
           "warnings": ["forward scan produced no trajectory"], "rc": None}

total = gfn2_scan.total_points(fwd, rev)
out = {"plan": plan, "n_points_total": total,
       "prerelax_rc": pre_rc, "prerelax_converged": pre_converged,
       "_protocol": "§39.68: certified reactant -> CONSTRAINED GFN2 relax at d_break -> scan "
                    "anchored on the PRE-RELAXED d, +1.2 A over 12 points, both directions",
       "_protocol_status_unused": ("🔴 UNRESOLVED: the starting geometry and any pre-relaxation are "
                            "NOT ratified, and the verdict depends on them. Measured on R-A, "
                            "same code: raw geometry -> fired (dE 0.45 eV); free --opt first "
                            "-> fired (forward barrier ~15 eV, the optimisation leaves the "
                            "ring-closed basin); constrained --opt at d_reactant -> fired "
                            "(dE 73 eV); a hand-picked 1.45-2.65 A range on the raw geometry "
                            "-> PASSES at dBarrier 0.0216, reproducing §39.48(a)'s n=1 value. "
                            "This run used NO invented pre-relaxation. Do not read the verdict "
                            "as a chemical result until the protocol is ruled."),
       "point_budget": {"engine": "gfn2", "cap": b0f_deck.SCAN_POINTS_GFN2_MAX,
                        "used": total},
       "forward_rc": fwd.get("rc"), "reverse_rc": rev.get("rc"),
       "xtb_threads": 1}
# 🔴🔴 [§39.68(3)] FRAME 0'S OWN CRITERION, CHECKED BEFORE ANY VERDICT IS RENDERED.
# If frame 0 is not settled, both clauses are measured from a moving reference and the gate
# FALSE-FIRES. That is the gate reporting on ITSELF, so it must say so rather than blame the
# reaction: `indeterminate`, cause class `protocol`, never `fired`.
frame0 = gfn2_scan.frame0_check(fwd, pre_converged)
out["frame0"] = frame0
# 🔴 A NON-ZERO xtb RETURN CODE MEANS THE RUN FAILED -- render NO verdict from it.
# This is the "measured but unread" shape caught in my own code: `forward_rc`/`reverse_rc`
# were recorded and never checked, so a failed forward scan still produced a fired verdict
# from whatever partial `xtbscan.log` was on disk (observed: rc 128 with a 73 eV "result").
# A partial trajectory is not a short one -- it is an unfinished one, and the gate has no
# business drawing a conclusion from it.
bad_rc = [(t, p) for t, p in (("forward", fwd.get("rc")), ("reverse", rev.get("rc")))
          if p not in (0, None)]
if bad_rc:
    causes = []
    for tag, prof in (("forward", fwd), ("reverse", rev)):
        f = prof.get("failure") or {}
        if f.get("aborted"):
            causes.append("%s: %s (%s)" % (tag, f.get("cause"), f.get("kind")))
    # 🔴 [§39.69] `engine`: the calculation could not be COMPLETED for numerical reasons
    #    internal to the electronic-structure method, at a geometry the protocol legitimately
    #    requested. Not chemical (says nothing about a barrier), not budget (not our caps),
    #    not protocol (the procedure ran exactly as ruled). An UNRECOGNISED failure kind falls
    #    back to `unknown` rather than being swept into `engine`.
    kinds = [((prof.get("failure") or {}).get("kind")) for prof in (fwd, rev)]
    engine_class = None
    for k in kinds:
        engine_class = engine_class or guards.classify_engine_failure(k)
    frame0 = {"ok": False, "cause_class": engine_class or "unknown",
              "failure_kinds": [k for k in kinds if k and k != "none"],
              "engine_failure": causes or None,
              # 🔴 [§39.69(3)] RETAIN AND REPORT, NEVER DISCARD. Where the scan died is itself
              #    the datum that sizes the problem (ADR-027: never prune the thing you compute
              #    completeness from), and dropping aborted scans would make our record of
              #    "where scans succeed" conditioned on success -- the success-conditioned
              #    denominator again, one layer down.
              "partial_profile": {
                  tag: {"frames_completed": prof.get("n_points"),
                        "stopped_after_frame": prof.get("n_points"),
                        "last_constrained_value_ang": (
                            gfn2_scan.distance_ang(prof["points"][-1]["geometry"],
                                                   i, j)
                            if prof.get("points")
                            and prof["points"][-1].get("geometry") else None),
                        "innermost_cause": (prof.get("failure") or {}).get("cause")}
                  for tag, prof in (("forward", fwd), ("reverse", rev))},
              "reasons": ["🔴 xtb aborted: %s -- the scan did not finish, so nothing measured "
                          "from it describes the reaction. %s"
                          % (", ".join("%s rc=%s" % (t, c) for t, c in bad_rc),
                             " | ".join(causes) or "no cause frame in the output")]}
    out["frame0"] = frame0
try:
    b0f_deck.check_scan_point_budget("gfn2", total, what="the bidirectional G-SCAN pass")
    if not frame0["ok"]:
        verdict = {"fired": False, "indeterminate": True, "cause_class": "protocol",
                   "reasons": (["🔴 NO VERDICT -- the gate's own reference frame is not "
                                "settled, so this says nothing about the reaction"]
                               + frame0["reasons"])}
    else:
        verdict = b0f_deck.gscan2_decision(fwd, rev)
except b0f_deck.DeckInputError as exc:
    verdict = {"fired": True,
               "reasons": ["G-SCAN could not render a verdict (%s) -- withholding DFT "
                           "funding is the correct direction when the check itself did "
                           "not run" % exc]}
out.update(verdict)
out["profiles"] = {"forward": fwd, "reverse": rev}
json.dump(out, open(os.path.join(d, "gscan_verdict.json"), "w"),
          ensure_ascii=False, indent=1)
print("[U56] G-SCAN: fired=%s  dE_endpoint=%s  dBarrier=%s  points=%d"
      % (out.get("fired"), out.get("delta_endpoint_ev"),
         out.get("delta_barrier_ev"), total))
PYGSCAN
    GS1=$(date +%s)
    cat > "$D/gscan_cost.json" <<EOF
{"wall_s": $((GS1-GS0)), "xtb_threads": 1, "job_total_cores": ${SEI_TOTAL_CORES:-1},
 "_note": "🔴 [ADR-110] work_core_h uses the xtb THREAD count; charged_core_h uses the JOB's cores. They differ here by design: this pre-stage runs inside a G16-sized job, so the packing efficiency is visibly low and that is the price of not spending a round trip on a verdict that takes seconds. Do not average the two."}
EOF
  fi

  GSCAN_VERDICT="$D/gscan_verdict.json"
  [ -f "$GSCAN_VERDICT" ] || GSCAN_VERDICT="${SEI_JOB_DIR}/gscan_verdict.json"
  if [ ! -f "$GSCAN_VERDICT" ]; then
    echo "[U56] 🔴 G-SCAN 판정 파일이 없다 ($D/gscan_verdict.json 또는 ${SEI_JOB_DIR}/) —"
    echo "     단끝단 arm 을 **발주하지 않는다.** §39.47(a): DFT scan 은 GFN2 gate 판정을"
    echo "     상속받아야 하고, 상속할 판정이 없으면 그 guess 는 ungated 다."
    echo "     ↳ 필요한 것: GFN2 양방향 relaxed scan + b0f_deck.gscan2_decision 사전 stage."
    _write_terminal "gfn2_prestage_unavailable" "gscan_verdict.json missing -- DFT scan not ordered (ungated guess)"
    exit 9
  fi
  GSCAN_FIRED="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$GSCAN_VERDICT" <<'PY'
import json, sys
try:
    v = json.load(open(sys.argv[1]))
except (OSError, ValueError) as exc:
    sys.stderr.write("gscan_verdict.json 을 읽을 수 없다: %s\n" % exc)
    print("unreadable"); sys.exit(0)
if v.get("cause_class") == "protocol" and not v.get("fired"):
    print("protocol")
else:
    print("fired" if v.get("fired") else "pass")
PY
)"
  if [ "$GSCAN_FIRED" = "protocol" ]; then
    # 🔴 [§39.68(3)] NO VERDICT: the gate's own reference frame was not settled, so this says
    #    nothing about the reaction. Distinct from a firing, and distinct from a pass.
    echo "[U56] 🔴 G-SCAN rendered NO VERDICT — its own reference frame was not settled."
    echo "     This is a fact about our PROCEDURE, not about the chemistry (cause_class=protocol)."
    sed 's/^/     ↳ /' "$GSCAN_VERDICT" | head -12
    STATUS="gscan_protocol_indeterminate"
  elif [ "$GSCAN_FIRED" != "pass" ]; then
    echo "[U56] 🔴 G-SCAN-4 발동 ($GSCAN_FIRED) — ts_opt+freq / IRC 를 **발주하지 않는다.**"
    sed 's/^/     ↳ /' "$GSCAN_VERDICT" | head -20
    echo "     이 시도는 'indeterminate, missing coordinate' 로 기록된다 — §39.39(f)가"
    echo "     이미 받는 **원인이 알려진** 결과이므로 U-56b 의 분모에는 들어가고"
    echo "     U-56a 를 오염시키지 않는다."
    STATUS="indeterminate_missing_coordinate"
  fi
fi
if [ "$METHOD" = "relaxed_scan" ]; then
 if [ "$STATUS" = "ts_candidate_produced" ]; then
  # --- scan: 좌표는 builder 가 만든 ModRedundant 섹션에서만 온다. ---
  if ! SEI_QC_MODREDUNDANT_FILE="$D/u56_${RXN}_scan_section.txt" \
       sei_qc_input "$D/scan.gjf" "$LVL" relaxed_scan "$CHARGE" "$MULT" "$REACTANT_XYZ" \
       > "$D/scan.meta.json" 2>"$D/scan.meta.err"; then
    echo "[U56] scan 입력 생성 실패:"; cat "$D/scan.meta.err"; exit 4
  fi
  U56_CURRENT_STAGE=u56_scan
  sei_stage u56_scan sei_qc_run "$D" scan.gjf scan.log
  _sei_u56_stop_after_check u56_scan

  # --- coarse 파싱 + §39.42(b) **조건부** refine 판정. coarse 는 guess 전용이다 —
  # --- 0.05 Å 격자가 최댓값을 0.10 eV 낮게 낸 실측이 refine pass 의 존재 이유다. ---
  REFINE_VERDICT="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/scan.log" "$D" "$RXN" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import b0f_deck
from sei_pilot.criteria import g16
log, d, rxn = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    text = open(log, errors="replace").read()
except OSError:
    text = ""
coarse = g16.parse_relaxed_scan(text)
params = b0f_deck.scan_params()
dec = b0f_deck.refine_decision(coarse, params["refine_trigger_delta_ev"])
json.dump({"decision": dec, "params": params},
          open(os.path.join(d, "refine_decision.json"), "w"),
          ensure_ascii=False, indent=1)
if not (dec["triggered"] and coarse["max_point_index"]):
    print("no_refine")
    sys.exit(0)
# refine 시작점 = 최댓값 **앞** coarse 점 (최댓값이 1번이면 그 점 자신) — 8 × 0.025 Å
# 가 최댓값 양옆(±0.075 Å 이상)을 덮는다.
idx = max(1, dec["max_point_index"] - 1)
geom = coarse["points"][idx - 1]["geometry"]
if not geom:
    print("no_refine")
    sys.exit(0)
with open(os.path.join(d, "refine_start.xyz"), "w") as fh:
    fh.write("%d\nU56 refine start (coarse point %d)\n" % (len(geom), idx))
    fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
record = json.load(open(os.path.join(d, "u56_%s_mapping.json" % rxn)))
lines = b0f_deck.scan_section_lines(record["mapping"], params["refine_n_steps"],
                                    params["refine_step_ang"])
with open(os.path.join(d, "u56_%s_refine_section.txt" % rxn), "w") as fh:
    fh.write("\n".join(lines) + "\n")
print("refine")
PY
)"
  if [ "${REFINE_VERDICT}" = "refine" ]; then
    echo "[U56] §39.42(b) refine pass 발동 — 사유: $D/refine_decision.json"
    if ! SEI_QC_MODREDUNDANT_FILE="$D/u56_${RXN}_refine_section.txt" \
         sei_qc_input "$D/scan_refine.gjf" "$LVL" relaxed_scan "$CHARGE" "$MULT" \
         "$D/refine_start.xyz" > "$D/scan_refine.meta.json" 2>"$D/scan_refine.meta.err"; then
      echo "[U56] refine scan 입력 생성 실패:"; cat "$D/scan_refine.meta.err"; exit 4
    fi
    U56_CURRENT_STAGE=u56_scan_refine
    sei_stage u56_scan_refine sei_qc_run "$D" scan_refine.gjf scan_refine.log
  fi

  # --- 병합 + TS guess: coarse ∪ refine 의 전역 최고점. 🔴 이것은 rigid-path 최대점이지
  # --- saddle 이 아니다 — 다음의 opt=(ts,calcfc)+freq 가 판정한다(§39.39(d) (i)). ---
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16

d = sys.argv[1]

def parse(name):
    try:
        text = open(os.path.join(d, name), errors="replace").read()
    except OSError:
        return None
    return g16.parse_relaxed_scan(text)

def summary(scan):
    if not scan:
        return None
    return {"n_points": scan["n_points"],
            "n_points_with_energy": scan["n_points_with_energy"],
            "max_point_index": scan["max_point_index"],
            "max_energy_hartree": scan["max_energy_hartree"],
            "energies_hartree": [p["energy_hartree"] for p in scan["points"]],
            "warnings": scan["warnings"]}

coarse = parse("scan.log")
refine = parse("scan_refine.log")
try:
    dec = json.load(open(os.path.join(d, "refine_decision.json")))
except (OSError, ValueError):
    dec = None

best = None
for pass_name, scan in (("coarse", coarse), ("refine", refine)):
    if scan and scan["max_point_index"]:
        cand = scan["points"][scan["max_point_index"] - 1]
        if cand["geometry"] and (best is None
                                 or cand["energy_hartree"] > best[1]["energy_hartree"]):
            best = (pass_name, cand)

out = {"coarse": summary(coarse), "refine": summary(refine),
       "refine_decision": dec,
       "guess_source_pass": best[0] if best else None,
       "guess_point_index": best[1]["point_index"] if best else None,
       "guess_energy_hartree": best[1]["energy_hartree"] if best else None}
json.dump(out, open(os.path.join(d, "scan_points.json"), "w"),
          ensure_ascii=False, indent=1)
if best:
    geom = best[1]["geometry"]
    with open(os.path.join(d, "ts_guess.xyz"), "w") as fh:
        fh.write("%d\nU56 scan maximum (%s pass, point %d) -- rigid-path max, NOT a "
                 "saddle\n" % (len(geom), best[0], best[1]["point_index"]))
        fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
    print("scan 최고점 = %s pass point %d" % (best[0], best[1]["point_index"]))
PY
  if [ ! -f "$D/ts_guess.xyz" ]; then
    echo "[U56] scan 이 수렴점을 내지 못했다 — 시도 결과로 기록하고 종료 (U-56b 분모)"
    STATUS="scan_not_converged"
  else
    U56_CURRENT_STAGE=u56_tsopt
    sei_qc_input "$D/ts_opt.gjf" "$LVL" ts_opt_from_guess "$CHARGE" "$MULT" \
      "$D/ts_guess.xyz" > "$D/ts_opt.meta.json" 2>&1 \
      && sei_stage u56_tsopt sei_qc_run "$D" ts_opt.gjf ts_opt.log
    TS_LOG="$D/ts_opt.log"
  fi
 fi
else
  # --- qst2 (R-A 전용): 🔴 폴백 없음 — bake-off 에서 method 를 갈아타면 비교가 오염된다. ---
  PRODUCT_XYZ="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import json, os
print(json.load(open(os.path.join(os.environ["SEI_JOB_DIR"], "endpoint_certs.json")))["product_xyz"])')"
  if SEI_QC_XYZ2="$PRODUCT_XYZ" \
     sei_qc_input "$D/ts_qst2.gjf" "$LVL" ts_qst2 "$CHARGE" "$MULT" "$REACTANT_XYZ" \
       > "$D/ts_qst2.meta.json" 2>"$D/ts_qst2.meta.err"; then
    U56_CURRENT_STAGE=u56_qst2
    sei_stage u56_qst2 sei_qc_run "$D" ts_qst2.gjf ts_qst2.log
    TS_LOG="$D/ts_qst2.log"
  else
    echo "[U56] QST2 입력 생성 실패:"; cat "$D/ts_qst2.meta.err"
    STATUS="input_error"
  fi
fi

# --- 인수 시험을 **데이터로** 기록 (C-12 의 acceptance 형태, 단 폴백은 없다). ---------
if [ -n "$TS_LOG" ]; then
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$TS_LOG" "$D" "$RXN" <<'PY'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import b0f_deck, curvature
from sei_pilot.criteria import g16
log, d, rxn = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    text = open(log, errors="replace").read()
except OSError:
    text = ""
summ = g16.summarize(text)
freqs = g16.parse_frequencies(text)
n_imag = sum(1 for f in freqs if f < 0) if freqs else 0

# 🔴 [§39.4(c) M2' / §39.56] Omega — **항상** 계산해서 싣는다, 판정은 없다(C-3, U-57).
# P1 의 "TS" 는 exactly-one-imaginary-frequency 를 통과했고 두 라운드 동안 아무 게이트에도
# 안 걸렸다. 그 모드는 Li+ 의 spectator 운동(진폭의 63%가 Li 하나)이었고 의도한 C-O 결합은
# 이미 3.18 A 로 끊어져 있었다 -- Omega = 0.022. **크기(|nu_imag|)로는 무른 진짜 TS 와
# 틀린 saddle 을 가를 수 없다. 방향이 문제다.**
omega_rows, omega_status, localisation = None, None, None
try:
    parsed = g16.parse_normal_modes(text)
    imag = g16.imaginary_modes(parsed)
    record = json.load(open(os.path.join(d, "u56_%s_mapping.json" % rxn)))
    pairs = []
    for kind in ("break", "form"):
        for e in (record["mapping"].get(kind) or []):
            i, j = e["selected"]
            pairs.append((int(i), int(j), "%s:%s" % (kind, e.get("role") or e.get("label"))))
    for e in (record["mapping"].get("mechanism") or []):
        i, j = e["selected"]
        pairs.append((int(i), int(j), "mechanism:%s" % "-".join(e.get("roles") or [])))
    if not imag:
        omega_status = "no imaginary mode in this log -- Omega is undefined, not zero"
    elif not pairs:
        omega_status = "the mapping carries no break/form bond -- nothing to project onto"
    else:
        omega_rows = curvature.mode_overlap_omega(imag[0], parsed["geometry"], pairs)
        localisation = sorted(curvature.mode_mass_localisation(imag[0], parsed["geometry"]),
                              key=lambda r: -r["amplitude_fraction"])[:3]
        omega_status = ("computed against the mapping's break/form bonds; "
                        "NO VERDICT (C-3, U-57: Omega_min is to be calibrated, not asserted)")
        if parsed.get("warnings"):
            omega_status += " | parser warnings: %s" % "; ".join(parsed["warnings"])
except (OSError, ValueError, KeyError, IndexError) as exc:
    omega_status = "Omega NOT computed: %s: %s" % (type(exc).__name__, exc)

json.dump({
    "normal_termination": summ.get("normal_termination"),
    "opt_converged": (summ.get("opt") or {}).get("converged"),
    "n_imaginary_modes_observed": n_imag,
    "exactly_one_imaginary_mode": (n_imag == 1) if freqs else None,
    "imaginary_mode_cm1": (imag[0]["freq_cm1"] if omega_rows else None),
    "imaginary_mode_reduced_mass_amu": (imag[0]["reduced_mass_amu"] if omega_rows else None),
    "omega": omega_rows,
    "mode_localisation_top3": localisation,
    "_omega_status": omega_status,
    "_omega_threshold": None,
    "endpoint_rmsd": None,
    "_endpoint_rmsd_status": ("[NOT COMPUTED -- covariate required by §39.39(d) before "
                              "any method COMPARISON is read; computable later from the "
                              "stored *_certified.xyz + IRC endpoints. Not silent: the "
                              "read-out rule blocks on it, not this payload."),
}, open(os.path.join(d, "ts_acceptance.json"), "w"), ensure_ascii=False, indent=1)

# 🔴 [§39.62] THE SPECTATOR TEST -- this is the gate, and Omega is NOT it. Threshold-free:
# block iff the single most-displaced atom is OUTSIDE the declared coordinate set AND
# outstrips the whole set together. P1's saddle: Li carried 63% of the mode while O2+C3
# together carried 2%, i.e. the imaginary mode was a cation hop on an ALREADY-OPEN ring.
# 🔒 Deliberately permissive: a false block loses a REACTION, a false pass loses ~325 core-h
# (11 atoms) / ~3,120 (21 atoms) and records the same `indeterminate` we would have anyway.
spec = {"blocked": False, "reasons": ["not evaluated"]}
try:
    if omega_rows:
        spec = curvature.spectator_test(
            imag[0], parsed["geometry"],
            b0f_deck.coordinate_atom_indices(record["mapping"]))
    else:
        spec = {"blocked": False,
                "reasons": ["no usable imaginary mode / mapping -- NOT blocking; "
                            "an unmeasured mode is not evidence of a spectator"]}
except (ValueError, KeyError) as exc:
    spec = {"blocked": False,
            "reasons": ["spectator test could not run (%s: %s) -- NOT blocking"
                        % (type(exc).__name__, exc)]}
json.dump(spec, open(os.path.join(d, "spectator_test.json"), "w"),
          ensure_ascii=False, indent=1)
PY
  # --- TS 기하 추출 → IRC 양방향 (P1 과 같은 판정-없는 배관). ---
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
        "%d\nU56 TS candidate (from %s)\n" % (len(geom), os.path.basename(log))
        + "".join("%-3s %14.8f %14.8f %14.8f\n" % g for g in geom))
PY
  # --- 🔴 [§39.63] BRACKET CHECK — the FIRST gate on the candidate, and the cheapest.
  #     Geometry only: each breaking bond's distance at the saddle must lie strictly between
  #     the two certified endpoints' values. P1's "TS" had d(O2-C3) = 3.184 A against a
  #     bracket of [1.405, 2.503] -- the bond it was supposed to be breaking was ALREADY
  #     BROKEN, past the product. No mode, no Omega, no threshold.
  PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$TS_LOG" "$D" "$RXN" <<'PYBRACKET'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import g16, xyzgraph
log, d, rxn = sys.argv[1], sys.argv[2], sys.argv[3]

def geom(path):
    try:
        return xyzgraph.read_xyz_frames(open(path, errors="replace").read())[0][1]
    except (OSError, ValueError, IndexError):
        return None

def dist(g, i, j):
    return sum((g[i][k + 1] - g[j][k + 1]) ** 2 for k in range(3)) ** 0.5

out = {"applicable": False, "refused": False, "reasons": []}
try:
    certs = json.load(open(os.path.join(d, "endpoint_certs.json")))
    record = json.load(open(os.path.join(d, "u56_%s_mapping.json" % rxn)))
    saddle = g16.last_geometry(open(log, errors="replace").read())
    reactant = geom(certs.get("reactant_xyz") or "")
    product = geom(certs.get("product_xyz") or "")
    # 🔴 [§39.66] break + form + mechanism, each with a DERIVED direction. Widening the input
    #    is only safe because the check now knows which kind each coordinate is; with a
    #    breaking-bond-only rule, every forming coordinate would refuse by construction.
    bonds = []
    for kind in ("break", "form", "mechanism"):
        for e in (record["mapping"].get(kind) or []):
            if e.get("selected"):
                bonds.append((e["selected"], "%s:%s" % (kind, "-".join(e.get("roles") or []))))
    # direction comes from the GFN2 forward profile this run already produced -- measured,
    # never declared, so it cannot be mis-declared (§39.66).
    # 🔴 [critic10] The derivation is NOT wrapped in one broad except. A failure here used to
    #    leave `directions` empty, and an empty map gave every coordinate -- including forming
    #    ones -- break semantics. The invariant "gscan_verdict.json always carries profiles"
    #    holds across two separate code blocks and is not enforced anywhere, so it is treated
    #    as an assumption to check rather than a guarantee.
    directions = {}
    from sei_pilot import gfn2_scan
    try:
        verdict = json.load(open(os.path.join(d, "gscan_verdict.json")))
    except (OSError, ValueError) as exc:
        out["reasons"].append("could not read gscan_verdict.json for the scan directions "
                              "(%s) -- coordinates without a derived direction get NO "
                              "one-sided bound and are counted" % exc)
        verdict = {}
    fwd_profile = (verdict.get("profiles") or {}).get("forward") or {}
    if not fwd_profile.get("points"):
        out["reasons"].append("the G-SCAN verdict carries no forward profile -- no direction "
                              "can be derived, so no one-sided bound is applied (counted, "
                              "never defaulted to `break`)")
    for (i2, j2), lbl in bonds:
        directions[lbl] = gfn2_scan.derive_direction(fwd_profile, (i2, j2))
    if not (saddle and reactant and bonds):
        out["reasons"].append("missing saddle geometry, reactant geometry or break bonds")
    else:
        # 🔴 [§39.65] The ONE-SIDED half runs on EVERY arm -- every arm has a certified
        #    reactant. The two-sided half runs only where a product is certified; where it is
        #    not (R-B by design, §39.39(d): its product is the claim under test) the product
        #    side is `awaiting_calibration` and is COUNTED, not silently absent.
        # ⚠ Do NOT substitute a raw GFN2 product distance here. "A GFN2 bracket is looser" is
        #    UNVERIFIED and may be backwards -- a shorter GFN2 product distance makes the
        #    bracket TIGHTER and this check false-blocks. §39.65(3)'s free calibration (R-A
        #    holds both a certified and a GFN2 product distance) measures the offset first.
        out["applicable"] = True
        keys = [lbl for _sel, lbl in bonds]
        out.update(guards.bracket_check(
            dict((lbl, dist(saddle, i, j)) for (i, j), lbl in bonds),
            dict((lbl, dist(reactant, i, j)) for (i, j), lbl in bonds),
            (dict((lbl, dist(product, i, j)) for (i, j), lbl in bonds)
             if product else None),
            labels=keys, directions=directions))
        out["directions"] = directions
except (OSError, ValueError, KeyError, IndexError) as exc:
    out["reasons"].append("bracket check could not run (%s: %s) -- NOT refusing"
                          % (type(exc).__name__, exc))
json.dump(out, open(os.path.join(d, "bracket_check.json"), "w"),
          ensure_ascii=False, indent=1)
PYBRACKET
  BRACKET_REFUSED="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/bracket_check.json" <<'PYBR'
import json, sys
try:
    r = json.load(open(sys.argv[1]))
    print("refuse" if (r.get("applicable") and r.get("refused")) else "pass")
except (OSError, ValueError):
    print("pass")
PYBR
)"
  if [ "$BRACKET_REFUSED" = "refuse" ]; then
    echo "[U56] 🔴 BRACKET CHECK refused this candidate — a breaking bond's saddle distance"
    echo "     lies OUTSIDE the interval its own certified endpoints define. NOT ordering the IRC."
    sed 's/^/     ↳ /' "$D/bracket_check.json" | head -16
    STATUS="saddle_outside_endpoint_bracket"
  fi
  SPECTATOR_BLOCK="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/spectator_test.json" <<'PYSPEC'
import json, sys
try:
    print("block" if json.load(open(sys.argv[1])).get("blocked") else "pass")
except (OSError, ValueError):
    print("pass")
PYSPEC
)"
  if [ "$STATUS" = "saddle_outside_endpoint_bracket" ]; then
    :   # already refused by the cheaper, geometry-only gate above
  elif [ "$SPECTATOR_BLOCK" = "block" ]; then
    # 🔴 §39.62: the imaginary mode is demonstrably not the declared coordinate's motion.
    #    Funding the IRC on it buys the same `indeterminate` at ~325 / ~3,120 core-h.
    echo "[U56] 🔴 SPECTATOR TEST fired — the imaginary mode is not the declared reaction"
    echo "     coordinate's motion. NOT ordering the IRC."
    sed 's/^/     ↳ /' "$D/spectator_test.json" | head -14
    echo "     🔴 FIRST HYPOTHESIS: the mapping is INCOMPLETE, not that the saddle is wrong."
    echo "     If this reaction's mechanism uses that atom, declare it in `mechanism` and re-run."
    STATUS="spectator_mode_not_the_coordinate"
  elif [ -f "$D/ts.xyz" ]; then
    # --- IRC Hessian 출처 스위치 (engineer7 §R39.15 4a / lead 2026-08-20) ------------------
    # 🔒 기본 calcfc. readfc(rcfc route)는 dev box 에 G16 이 없어 미검증 — 다음 제출의
    #    route smoke 통과 후 lead 가 config(u56_2.irc_hessian_source)를 올린다.
    IRC_SUFFIX=""
    HESS_SRC="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 -c '
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import config
print((config.load("b0_reactions.json", {}).get("u56_2") or {})
      .get("irc_hessian_source") or "calcfc")')"
    [ "${HESS_SRC}" = "readfc" ] && IRC_SUFFIX="_rcfc"

    # --- .chk 이관: TS 잡의 chk 를 IRC 의 %chk 이름으로 복사한다. 두 조건이 짝이다: -----
    # 🔴 (1) PER-TASK 경로 — %chk 파일명에 SEI_TASK_FILE_SUFFIX 가 물려 있다(qc_adapter).
    #        고정 공유 경로면 IRC 가 남의 TS 의 Hessian 을 읽고 **정상 종료한다**(ADR-107
    #        의 조용한-오답 형태 그대로, Lustre 는 아무것도 중재하지 않는다).
    # 🔴 (2) 출처 = **freq 단계의 Hessian** — `opt=(ts,calcfc) freq` 한 잡의 chk 는 마지막
    #        freq(수렴된 TS)가 최종 덮어쓴 상태다. guess 기하의 CalcFC Hessian 을 읽으면
    #        IRC 가 틀린 곡률에서 출발해 끝까지 완주하고 endpoint 를 정상 보고한다.
    #    calcfc(기본)에서는 G16 이 이 파일을 읽지 않지만 이관은 항상 해 둔다 — 스위치를
    #    켜는 순간 배관이 이미 검증돼 있어야 하기 때문(R-12 의 재제출 규율과 같은 방향).
    TS_CHK="$D/$(basename "${TS_LOG%.log}")${SEI_TASK_FILE_SUFFIX:-}.chk"
    for dir in forward reverse; do
      IRC_CHK="$D/irc_${dir}${SEI_TASK_FILE_SUFFIX:-}.chk"
      CHK_COPIED=false
      if [ -f "${TS_CHK}" ]; then
        cp "${TS_CHK}" "${IRC_CHK}" && CHK_COPIED=true
      fi
      cat > "$D/chk_handoff_${dir}.json" <<EOF
{"source_chk": "$(basename "${TS_CHK}")", "target_chk": "$(basename "${IRC_CHK}")",
 "copied": ${CHK_COPIED}, "hessian_source_stage": "freq block of the TS job (final chk state), NOT the CalcFC guess Hessian",
 "irc_route": "irc_${dir}${IRC_SUFFIX}", "per_task_suffix": "${SEI_TASK_FILE_SUFFIX:-}",
 "irc_hessian_source_config": "${HESS_SRC}"}
EOF
      # 🔴 [ADR-107 class / §R39.15-4a] THE rcfc SWITCH MUST NOT RUN ON A MISSING HESSIAN.
      #    `irc=(rcfc,...)` READS the Hessian from %chk instead of recomputing it. If the
      #    handoff did not happen, G16 does not fail loudly -- it reads whatever chk it finds
      #    (or none) and produces an IRC that runs to completion on the WRONG curvature and
      #    reports endpoints. Silently wrong, not a crash. Same shape as ADR-107's shared
      #    Lustre path, and the reason the copy is per-task in the first place.
      # 🔒 We do NOT quietly fall back to calcfc: switching method mid-run makes the cost
      #    measurement (the whole point of the switch) unattributable. Refuse the direction
      #    and say why.
      if [ "${HESS_SRC}" = "readfc" ] && [ "${CHK_COPIED}" != "true" ]; then
        echo "[U56] 🔴 irc_${dir}: rcfc requested but the TS .chk was NOT copied"
        echo "     (source ${TS_CHK}). Refusing this direction — an rcfc IRC without its"
        echo "     Hessian completes normally on the WRONG curvature. No silent calcfc fallback."
        cat > "$D/irc_${dir}.refusal.json" <<EOF
{"direction": "${dir}", "reason": "rcfc_requested_without_chk",
 "irc_hessian_source_config": "${HESS_SRC}",
 "expected_chk": "$(basename "${IRC_CHK}")", "source_chk": "$(basename "${TS_CHK}")",
 "cause_class": "unknown",
 "_why": "plumbing, not chemistry and not budget: the Hessian handoff did not happen. Do not pool this with either denominator."}
EOF
        continue
      fi
      sei_qc_input "$D/irc_${dir}.gjf" "$LVL" "irc_${dir}${IRC_SUFFIX}" "$CHARGE" "$MULT" "$D/ts.xyz" \
        > "$D/irc_${dir}.meta.json" 2>&1 || continue
      IRC_RAN="${IRC_RAN:-0}"
      IRC_RAN=$((IRC_RAN+1))
      RAN_IRC_LOGS="${RAN_IRC_LOGS:-} $D/irc_${dir}.log"
      U56_CURRENT_STAGE="u56_irc_${dir}"
      sei_stage "u56_irc_${dir}" sei_qc_run "$D" "irc_${dir}.gjf" "irc_${dir}.log"

      # ================= B+ (§39.55(b), §39.70) — TWO terminal optimisations ==============
      # 🔴 WHY IT EXISTS: an IRC that stopped on `maxpoints` establishes nothing on its own
      #    (C-2.2). B+ is the cheaper alternative to forcing a converged IRC everywhere:
      #    optimise from TWO points on the same descending branch and see whether they reach
      #    the same minimum. Agreement in both directions satisfies condition 7 branch (b).
      # 🔴 START POINTS: the LAST path point and the ARC-LENGTH MIDPOINT -- never by index
      #    (a fraction of however many points a run produced is a constant in disguise, and
      #    C-2.2 makes short IRCs common), and NEVER the earliest point: a terminal
      #    optimisation started too near the saddle CAN ROLL BACK OVER IT into the other basin
      #    and produce a SPURIOUS DISAGREEMENT. Do not "improve" this to point 1.
      # 🔴 LEVEL: the same DFT level as the TS chain, via `$LVL`. NOT GFN2 -- the job is to
      #    identify which minimum the path leads to ON THE SURFACE THE TS SEARCH RAN ON, and
      #    GFN2 is documented to merge exactly the Li-coordination basins at issue here
      #    (§39.38(d)/U-55), which would produce FALSE AGREEMENT -- the one error B+ exists to
      #    prevent. `endpoint_opt_rough` is reused rather than a new job_type: loose is right
      #    (we need the basin, not a precise geometry) and it already carries the UltraFine
      #    grid that keeps this on the TS chain's surface (C-8.1).
      BPLUS_PTS="$(PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/irc_${dir}.log" "$D" "${dir}" <<'PYBPLUSPICK'
import os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import g16
log, d, direction = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    text = open(log, errors="replace").read()
except OSError:
    print("no_log"); raise SystemExit(0)
pts = g16.parse_irc_path_frames(text)
pick = guards.bplus_sample_points([p["arc"] for p in pts])
if not pick:
    print("too_few_points"); raise SystemExit(0)
mid, last = pick
if not (pts[mid]["geometry"] and pts[last]["geometry"]):
    print("no_geometry"); raise SystemExit(0)
for tag, idx in (("mid", mid), ("last", last)):
    g = pts[idx]["geometry"]
    with open(os.path.join(d, "bplus_%s_%s.xyz" % (direction, tag)), "w") as fh:
        fh.write("%d\nB+ start (%s, path point %d, arc %.5f)\n"
                 % (len(g), tag, idx + 1, pts[idx]["arc"]))
        fh.write("".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in g))
print("ok")
PYBPLUSPICK
)"
      if [ "$BPLUS_PTS" = "ok" ]; then
        for _bp in mid last; do
          U56_CURRENT_STAGE="u56_bplus_${dir}_${_bp}"
          sei_qc_input "$D/bplus_${dir}_${_bp}.gjf" "$LVL" endpoint_opt_rough "$CHARGE" "$MULT" \
            "$D/bplus_${dir}_${_bp}.xyz" > "$D/bplus_${dir}_${_bp}.meta.json" 2>&1 \
            && sei_stage "u56_bplus_${dir}_${_bp}" sei_qc_run "$D" \
                 "bplus_${dir}_${_bp}.gjf" "bplus_${dir}_${_bp}.log"
        done
      else
        echo "[U56] B+ ${dir}: start points unavailable (${BPLUS_PTS}) — no B+ verdict."
      fi
      PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" "${dir}" "${BPLUS_PTS}" "$RXN" <<'PYBPLUS'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot import guards
from sei_pilot.criteria import g16, xyzgraph
d, direction, pick_status, rxn = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]

def read(tag):
    path = os.path.join(d, "bplus_%s_%s.log" % (direction, tag))
    try:
        text = open(path, errors="replace").read()
    except OSError:
        return None, None, None
    summ = g16.summarize(text)
    return (g16.last_geometry(text),
            (summ.get("scf") or {}).get("final_energy_hartree"),
            g16.stages_completed(text, summ.get("route_echoed")))

geom_a, e_a, st_a = read("mid")
geom_b, e_b, st_b = read("last")
if pick_status != "ok":
    out = {"agreement": None, "reasons": ["B+ start points unavailable (%s) -- no verdict; "
                                          "an unrun comparison is not an agreement"
                                          % pick_status]}
else:
    out = guards.bplus_agreement(geom_a, geom_b, e_a, e_b)
out["direction"] = direction
out["start_points"] = {"mid": "arc-length midpoint", "last": "final path point"}
out["stages"] = {"mid": st_a, "last": st_b}
out["_level_note"] = ("terminal optimisations run at the TS chain's own DFT level "
                      "(endpoint_opt_rough route, UltraFine grid) -- NOT GFN2, which merges "
                      "the Li-coordination basins this test exists to tell apart")

# 🔴 [§39.124 finding (c)] Condition 7's own text: "in both branches the reverse endpoint
# must match the certified reactant." `guards.bplus_agreement` above never reads
# `reactant_certified.xyz` -- this is that missing check.
# 🔒 [§39.124 Ruling 2, corrected A1] WHICH POINT condition 7 binds is RULED: `last` ONLY --
# "in both branches" names the two establishment branches (convergence / maxpoints+B+), not the
# two B+ sample points, and "the reverse endpoint" is singular while `mid` is a midpoint by
# construction. Both are still computed and stored here (mid is useful diagnostic data), but a
# reader implementing condition 7 itself must consult `reactant_match["last"]` ONLY and must
# never AND it with `reactant_match["mid"]`.
# 🟢 [§39.124 Ruling 1, corrected A4] BOTH ruled tolerances now apply by DEFAULT
# (`guards.REACTANT_MATCH_TOLERANCE_ANG` = 0.05 A, `guards.BPLUS_ENERGY_TOLERANCE_EV` reused) --
# not passed explicitly here, so a future re-derivation of either constant is picked up
# automatically rather than needing an edit in two places. The reactant's own converged energy
# (`endpoint_certs.json`'s `reactant_cert.energy_hartree`, a STRUCTURED field `endpoint_prep.sh`
# emits at certification time and this script's `resolve()` copies through -- critic16 B1: not
# a cross-job log re-parse at gate time) is what makes the energy clause actually evaluable
# here. `None` on an older cert that predates this field is the correct, honest answer (Rule
# 18). 🔴 [critic17, 36th review batch] CORRECTED: `SEI_C8_ENDPOINTS_JSON` does NOT backfill
# an already-returned cert -- it is read only inside the certification block THIS SAME FILE
# writes (`U56.sh:167`, a fresh certification during a live harness run), and whatever comes
# through it is stamped `[FIXTURE] -- test injection, not a certification` (`:173`; `P1.sh:86`
# names it a test-only injection channel; `local.sh.tmpl`/`pbs.sh.tmpl` unset it before a real
# job runs). Setting it and re-running this block against an existing job dir does nothing,
# silently -- do not route this gate's real verdict through it. The actual fix for a `None`
# caused by a missing `energy_hartree`: re-certify the reactant through a fresh
# `endpoint_prep.sh` run so `endpoint_certs.json` carries a real value, not an env var.
reactant_match = {"mid": None, "last": None, "_status": None}
try:
    certs = json.load(open(os.path.join(d, "endpoint_certs.json")))
    # 🔴 [critic16, "also still open"] `reactant_xyz` as RECORDED may be an absolute path from
    # a different `SEI_WORKDIR` root (a job tree copied/moved between runs) -- prefer the
    # job-local file THIS run's own `resolve()` would have written (deterministic name,
    # `<role>_certified.xyz`, always in this same job dir `d`) and fall back to the recorded
    # path only if that file is not actually here (e.g. an `SEI_U56_REACTANT_XYZ` override,
    # which keeps its own external path deliberately -- see `resolve()`'s xyz_override branch).
    r_xyz_local = os.path.join(d, "reactant_certified.xyz")
    r_xyz = r_xyz_local if os.path.exists(r_xyz_local) else certs.get("reactant_xyz")
    r_energy = (certs.get("reactant_cert") or {}).get("energy_hartree")
    mapping = json.load(open(os.path.join(d, "u56_%s_mapping.json" % rxn)))
    pairs = []
    for kind in ("break", "form"):
        for e in (mapping["mapping"].get(kind) or []):
            i, j = e["selected"]
            pairs.append((int(i), int(j), "%s:%s" % (kind, e.get("role") or e.get("label"))))
    atoms_r = xyzgraph.read_xyz_frames(open(r_xyz, errors="replace").read())[0][1]
    reactant_match["mid"] = guards.reactant_match(
        geom_a, atoms_r, pairs, energy_point_hartree=e_a, energy_reactant_hartree=r_energy)
    reactant_match["last"] = guards.reactant_match(
        geom_b, atoms_r, pairs, energy_point_hartree=e_b, energy_reactant_hartree=r_energy)
    reactant_match["_status"] = "computed against %s (energy: %r)" % (r_xyz, r_energy)
except (OSError, KeyError, IndexError, ValueError) as exc:
    reactant_match["_status"] = ("NOT computed: %s: %s -- an unrun comparison is not a match"
                                 % (type(exc).__name__, exc))
out["reactant_match"] = reactant_match

json.dump(out, open(os.path.join(d, "bplus_%s.json" % direction), "w"),
          ensure_ascii=False, indent=1)
print("[U56] B+ %s: agreement=%s reactant_match(mid/last)=%s/%s"
      % (direction, out.get("agreement"),
         (reactant_match["mid"] or {}).get("match"), (reactant_match["last"] or {}).get("match")))
PYBPLUS
      # --- C-2.1 (39.53): emit HOW the path ended, as data. G16 prints it; nobody read it.
      #     The delivered P1 run stopped on `Maximum number of steps reached.` in BOTH
      #     directions while ALSO printing `Normal termination` -- it passed every clause
      #     C-2 had at the time and had connected nothing. No verdict here; C-2.2 lives in
      #     guards.irc_verdict and the collector renders it.
      PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D/irc_${dir}.log" "$D/irc_completion_${dir}.json" <<'PYIRC'
import json, os, sys
sys.path.insert(0, os.environ["SEI_PKG_ROOT"])
from sei_pilot.criteria import g16
log, out = sys.argv[1], sys.argv[2]
try:
    text = open(log, errors="replace").read()
except OSError:
    text = ""
json.dump(g16.parse_irc_completion(text), open(out, "w"), ensure_ascii=False, indent=1)
PYIRC
    done
    # 🔴 [critic10] If EVERY direction refused, the per-direction `continue` left STATUS
    #    untouched and the attempt read as though the IRC had run. Say it once, here.
    if [ "${IRC_RAN:-0}" = "0" ]; then
      echo "[U56] 🔴 no IRC direction ran — every one was refused (see irc_*.refusal.json)."
      STATUS="irc_refused_no_direction_ran"
    else
      # 🔴 [critic14 finding B / lead ruling 2026-08-21] THE IRC LOG DECIDES terminal_status
      #    when it ran -- content parsing, never a guessed STATUS string (same principle as
      #    endpoint_prep.sh). A corrector-integration death ("Maximum number of corrector
      #    steps exceded.", now in outcome.INPUT_DEFECT_SENTINELS) reads as `input_defect` ->
      #    cause_class `deterministic`: same deck, same crash, never auto-retried (§39.87) --
      #    NOT `success` (STATUS below still says `ts_candidate_produced`, which stays true: a
      #    candidate WAS produced) and NOT `engine` (which auto-resubmits on the next build for
      #    zero new information -- critic14 measured 449 core-h of exactly that risk).
      # 🔴 [critic14] `&&`, not an unconditional set-after: `sei_terminal_from_logs` can exit
      #    non-zero and write NOTHING (e.g. a python import failure) -- `set -u` alone does not
      #    stop the script, so an unconditional flag here would skip the fallback write below
      #    on exactly the run where the log-derived write never happened, landing back on
      #    `outcome: absent` -- the exact state this whole fix exists to remove.
      sei_terminal_from_logs "reaction=${RXN}" "method=${METHOD}" "level=${LVL}" -- ${RAN_IRC_LOGS} \
        && IRC_TERMINAL_WRITTEN=1
    fi
  else
    echo "[U56] TS 기하를 추출하지 못했다 → IRC 생략. 여기까지의 단가는 stages/ 에 남는다."
    STATUS="ts_opt_no_geometry"
  fi
fi

# 🔴 all real QC stages are done -- the wall tripwire's job is finished. Disarm it (P5.sh's
#    same pattern) so a SIGTERM during the bookkeeping below (which only reads/writes small
#    JSON files, never a multi-hour QC stage) does not overwrite a real classification that
#    may already be on disk with a spurious `wall_exhausted`.
trap - TERM

# --- 🔴 [§39.59] WHICH CAPS WERE ACTIVE. A `p` measured under one cap regime and a `p`
#     measured under a looser one are NOT comparable, and a cause class alone does not say
#     which regime produced it. Without this, two rounds' rates could be averaged or trended
#     with nothing in the record to show they should not have been.
#     🔒 Recorded from the ROUTES THAT ACTUALLY RAN (the emitted .gjf), not from config --
#     the config value is what we asked for, the route echo is what the job used.
PYTHONPATH="${SEI_PKG_ROOT}" python3 - "$D" <<'PYCAPS'
import json, os, re, sys
d = sys.argv[1]
caps = {"route_caps": {}, "total_cores": os.environ.get("SEI_TOTAL_CORES"),
        "_source": "parsed from the .gjf route lines this run actually generated"}
for fn in sorted(os.listdir(d)):
    if not fn.endswith(".gjf"):
        continue
    try:
        text = open(os.path.join(d, fn), errors="replace").read()
    except OSError:
        continue
    route = "".join(l for l in text.splitlines() if l.strip().startswith("#"))
    found = dict((k, int(v)) for k, v in re.findall(
        r"(maxpoints|maxcycles|maxstep)\s*=\s*(\d+)", route, re.I))
    if found:
        caps["route_caps"][fn[:-4]] = found
caps["_not_observable_here"] = (
    "wall cap and the per-item core-hour budget are NOT visible inside the payload: PBS/SLURM "
    "set walltime as a scheduler directive without exporting it, and the job templates are "
    "shape-locked against the site's submit filter (tests/test_pbs_script_shape.py), so adding "
    "an export is not a free change. Both live on the plan Item -- join on the item key in "
    "u56_attempt.json rather than re-deriving them here.")
json.dump(caps, open(os.path.join(d, "active_caps.json"), "w"),
          ensure_ascii=False, indent=1)
PYCAPS

# 🔴 [terminal_status fix] the STATUS this script has been refining branch by branch above
#    IS what U56.sh itself knows -- write it, honestly, instead of leaving terminal_status
#    empty on a real rc=0 completion. The C-2/IRC pass verdict is still NOT decided here
#    (that stays the collection stage's job, u56_attempt.json's own note below) -- this only
#    reports how far the attempt got and where/why it stopped.
# 🔴 SKIP this generic write if an IRC direction actually ran: `IRC_TERMINAL_WRITTEN` (set
#    above) means terminal_status.json was already written FROM the IRC log's own content
#    (input_defect/engine_failure/converged), which is more honest than this STATUS string --
#    writing again here would silently overwrite that real classification with `success`.
if [ -z "${IRC_TERMINAL_WRITTEN:-}" ]; then
  _write_terminal "$STATUS" "reached end of U56.sh with status=${STATUS} -- C-2/IRC pass verdict is a collection-stage decision, see u56_attempt.json/ts_acceptance.json/bracket_check.json/spectator_test.json"
fi

cat > "$D/u56_attempt.json" <<EOF
{"reaction": "${RXN}", "method": "${METHOD}", "level": "${LVL}",
 "status": "${STATUS}",
 "item_key": "${SEI_KEY:-unknown}",
 "active_caps": "active_caps.json",
 "mapping": "u56_${RXN}_mapping.json",
 "ts_log": "$(basename "${TS_LOG:-none}")",
 "note": "판정(C-2 IRC verdict, U-56a pass)은 수집/리뷰 단계가 한다 — §39.39(f): pass 가 아닌 완주는 U-56b 분모에만 든다."}
EOF
echo "[U56] 완료 (reaction=${RXN} method=${METHOD} status=${STATUS}). 판정은 수집 단계가 한다."
exit 0
