"""수집 단계 — 잡이 남긴 아티팩트를 읽어 판정하고 회신 JSON 조각을 만든다.

원칙:
  * **여기서 예외를 던지지 않는다.** 파일이 없다/깨졌다는 정상적인 결과다.
    한 파일럿의 실패가 다른 파일럿을 죽이면 안 된다(§R2-6 D-6).
  * 판정은 criteria/ 의 순수 함수가 한다. 이 모듈은 파일 I/O와 조립만 한다.
  * 잡이 아직 안 끝났으면 status="incomplete" 로 남긴다. "fail"과 구분한다.
"""

import json
import os
import re

from . import execlog
from .criteria import cost, g16, p1, p1b, p3, p4, p5

#: [MEASURED] RT-1c 개발 박스 기준값 (16 스레드 Ryzen 7800X3D). κ 의 분모다.
P6_REFERENCE_WALL_S = 177.3
from . import probes, sysprobe


def _read(path, limit=4000000):
    try:
        with open(path, "r", errors="replace") as fh:
            return fh.read(limit)
    except OSError:
        return None


def _read_json(path):
    txt = _read(path)
    if txt is None:
        return None
    try:
        return json.loads(txt)
    except ValueError:
        return None


def _first_existing(job_dir, names):
    for n in names:
        p = os.path.join(job_dir, n)
        if os.path.exists(p):
            return p
    return None


def _glob_suffix(job_dir, suffix):
    if not os.path.isdir(job_dir):
        return []
    return [os.path.join(job_dir, f) for f in sorted(os.listdir(job_dir))
            if f.endswith(suffix)]


def job_status(store, key):
    """제출/완료/실패 마커 → (status, marker_payload)

    🔴 [array 분기 사고] array 태스크는 마커를 `<key>.t<N>.{done,failed}.json` 으로
    태스크별로 남긴다(common.sh). base 마커가 없으면 태스크 마커를 **집계**한다 —
    지난 라운드에는 22태스크가 base 마커 하나를 공유해 `P5.done.json` 과
    `P5.failed.json` 이 **둘 다** 존재했다.
    """
    done = store.read_marker(key, "done")
    if done:
        return "done", done.get("payload") or {}
    failed = store.read_marker(key, "failed")
    if failed:
        return "failed", failed.get("payload") or {}
    task_states = store.task_marker_states(key)
    if task_states:
        return _aggregate_task_status(store, key, task_states)
    if store.is_submitted(key):
        return "incomplete", (store.read_marker(key, "submitted") or {}).get("payload") or {}
    return "not_submitted", {}


def _aggregate_task_status(store, key, task_states):
    """태스크 마커 집계 → (status, 합성 payload). 규칙은 state.Store 의 것과 같다:
    done = n_tasks 전부 done · failed = 전 태스크 종결 + 실패 존재 · 그 외 incomplete.
    payload 의 start/end 는 태스크 전체의 span 이다(wall_h 는 항목 수준 경과 시간)."""
    n = store.expected_task_count(key)
    payloads = []
    for tid, kind in sorted(task_states.items()):
        m = store.read_marker("%s.t%d" % (key, tid), kind) or {}
        p = m.get("payload") or {}
        if p:
            payloads.append(p)
    starts = [p.get("start_epoch") for p in payloads if p.get("start_epoch")]
    ends = [p.get("end_epoch") for p in payloads if p.get("end_epoch")]
    merged = {
        "aggregated_from_task_markers": True,
        "n_tasks_expected": n,
        "n_tasks_done": sum(1 for k in task_states.values() if k == "done"),
        "n_tasks_failed": sum(1 for k in task_states.values() if k == "failed"),
        "start_epoch": min(starts) if starts else None,
        "end_epoch": max(ends) if ends else None,
        "total_cores": (payloads[0].get("total_cores") if payloads else None),
    }
    if n and merged["n_tasks_done"] >= int(n):
        return "done", merged
    if n and len(task_states) >= int(n) and merged["n_tasks_failed"]:
        return "failed", merged
    return "incomplete", merged


def _read_jsonl(path):
    out = []
    txt = _read(path)
    for line in (txt or "").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def execution_audit(job_dir, expected_run_lines=None):
    """이중 실행 감사 (critic B-1 항목 3).

    체인 링크가 앞 링크의 완료를 못 보고 같은 단계를 다시 돌면 결과가 덮어써진다.
    그 사실이 회신 JSON에 **반드시** 드러나게 한다. 정상 재개(skip)와 구분한다.

    Also carries the `executions.jsonl` INTEGRITY audit (R36.3 / R31.2d). It is bolted onto this
    existing function on purpose: extending an existing mechanism instead of writing a second one
    that could drift from it (R31.2a's own stated reason for the shape of the `host`/`cores` fix).

    🔴 [ADR-091] THIS FUNCTION IS NOT CALLED FROM EVERY COLLECTOR, AND THAT CLAIM ONCE STOOD HERE
    AS THE DESIGN RATIONALE ITSELF -- FALSELY. The true count, checked by reading each payload
    script directly (not by counting call sites, which is how the false claim survived review):
    ```
    CALLS (7)      collect_p1 / collect_p1b / collect_p3 / collect_p5 / collect_p6 /
                   collect_endpoint_prep (ADR-099) / collect_u56 (U56-2, ADR-109) -- each
                   payload sources common.sh and uses sei_stage, so
                   stage_events.jsonl/executions.jsonl genuinely exist in that job_dir.
    DOES NOT (4)   collect_p4          -- P4.sh does not source common.sh / use sei_stage.
                                          No stage_events.jsonl or executions.jsonl is ever
                                          produced for this job_dir; there is nothing to audit.
                   collect_node_probe  -- a raw one-shot node probe, not a staged job chain.
                   collect_throughput  -- has ITS OWN per-task telemetry
                                          (`starts/task_${TID}.json`), which is the very pattern
                                          this function's fallback text already points readers to
                                          for that purpose. A second audit here would be the
                                          "two mechanisms" failure this function's own docstring
                                          warns against, not a fix.
                   collect_queue_wait  -- reads `started.json` per probe width; no per-task chain
                                          exists to double-execute.
    ```
    ⟹ If you add a 10th collector, or extend one of the four "DOES NOT" collectors' payload to
    start using `sei_stage`, call this function from it AND move it out of the "DOES NOT" list
    above -- a stale exemption here is exactly how the original false "every collector" claim was
    created and went unchecked for a full round.
    """
    exec_path = os.path.join(job_dir, "executions.jsonl")
    integrity = execlog.audit(exec_path, expected_run_lines=expected_run_lines)
    execs = _read_jsonl(exec_path)
    events = _read_jsonl(os.path.join(job_dir, "stage_events.jsonl"))
    runs = {}
    skips = {}
    for e in events:
        st = e.get("stage")
        if e.get("event") == "run":
            runs[st] = runs.get(st, 0) + 1
        elif e.get("event") == "skip_done":
            skips[st] = skips.get(st, 0) + 1
    duplicated = sorted(k for k, v in runs.items() if v > 1)
    links_run = [e.get("link") for e in execs if e.get("action") == "run"]
    links_skipped = [e.get("link") for e in execs if e.get("action") == "skip_done"]
    warnings = []
    if duplicated:
        warnings.append(
            "🔴 double_execution: 단계 %s 가 2회 이상 실행됐다. 같은 job_dir에 "
            "덮어써졌으므로 회신된 결과는 '마지막 실행'의 것이다. "
            "CREST/NEB-TS는 완전 결정론적이지 않아 다른 TS로 수렴했을 수 있고, "
            "core-h도 중복 소모됐다." % ", ".join(duplicated))
    # 🔴 [A-2, array 분기 사고 / §6 lead 판정] stage 기반 감사만으로는 부족했다: P5 는
    #    sei_stage 에 도달하기 전에 죽어 stage_events 가 없었고, links_executed 에 "P5"
    #    가 22번 있는데도 duplicate_execution=false 로 회신됐다.
    #    경고 조건은 **"같은 logical key 의 실행 구간 [run, finish] 이 서로 다른 host
    #    에서 실제로 겹친다"** 다 — "다른 host 에서 2회"만 보면 정당한 체인 재개(실패
    #    후 다른 노드에서 이어받기, 비중첩)가 오탐이 된다(critic9 재현, ADR-092 의
    #    67% 오탐 이력). finish 가 없는 run 은 종료 시각 미상이므로 **보수적으로 열린
    #    구간(∞)** 으로 취급한다 — 이번 라운드의 P1b(3 run, finish 0)가 정확히 그
    #    형태로 겹침 판정된다.
    runs_by_logical = {}
    for e in execs:
        if e.get("action") != "run":
            continue
        lg = e.get("logical") or e.get("link")
        runs_by_logical.setdefault(lg, []).append(e)
    # run→finish 쌍은 **link 단위**로 순서 짝짓기 (한 link 는 순차 실행이므로 k번째
    # run 은 k번째 finish 와 짝이다). A-2 의 구간과 A-3 의 core-h 하한이 같은 짝을 쓴다.
    intervals_by_logical = {}   # lg -> [(start, end|None, host, cores)]
    links = {}
    for e in execs:
        lk = e.get("link")
        rec = links.setdefault(lk, {"runs": [], "finishes": [],
                                    "logical": e.get("logical") or lk})
        if e.get("action") == "run":
            rec["runs"].append(e)
        elif e.get("action") == "finish":
            rec["finishes"].append(e.get("epoch") or 0)
    core_h_floor = 0.0
    n_runs_without_finish = 0
    for lk, rec in links.items():
        runs_sorted = sorted(rec["runs"], key=lambda x: x.get("epoch") or 0)
        finishes = sorted(rec["finishes"])
        for i, r in enumerate(runs_sorted):
            start = r.get("epoch") or 0
            end = finishes[i] if i < len(finishes) else None
            intervals_by_logical.setdefault(rec["logical"], []).append(
                (start, end, r.get("host"), r.get("cores") or 1))
            if end is None:
                n_runs_without_finish += 1
            else:
                core_h_floor += max(0, end - start) / 3600.0 * (r.get("cores") or 1)
    multi_host = {}
    for lg, ivs in intervals_by_logical.items():
        overlapping_hosts = set()
        n_overlaps = 0
        for i in range(len(ivs)):
            for j in range(i + 1, len(ivs)):
                a, b = ivs[i], ivs[j]
                if not a[2] or not b[2] or a[2] == b[2]:
                    continue                      # 같은 host / host 미상은 대상 아님
                a_end = a[1] if a[1] is not None else float("inf")
                b_end = b[1] if b[1] is not None else float("inf")
                if a[0] < b_end and b[0] < a_end:  # 실제 시간 겹침만
                    n_overlaps += 1
                    overlapping_hosts.update((a[2], b[2]))
        if n_overlaps:
            multi_host[lg] = {"n_run_lines": len(ivs),
                              "n_overlapping_pairs": n_overlaps,
                              "hosts": sorted(overlapping_hosts)}
    if multi_host:
        warnings.append(
            "🔴 concurrent_execution: 같은 logical key 의 실행 구간이 서로 다른 host "
            "에서 **시간상 겹쳤다**: %s. array 태스크가 키를 공유해 같은 작업을 동시에 "
            "돌렸다는 뜻이고, 이 job_dir 의 산출물은 어느 실행의 것인지 특정할 수 없다. "
            "(finish 가 없는 run 은 종료 미상 → 보수적으로 겹침 취급)"
            % "; ".join("%s=%d회@%s" % (k, v["n_run_lines"], ",".join(v["hosts"]))
                        for k, v in sorted(multi_host.items())))
    # 🔴 [A-3] 위의 run→finish 짝에서 얻는 core-h **하한**. stage 마커는 파일 하나를
    #    태스크들이 덮어쓰면 중복 소모가 통째로 사라진다(P1b: 보고 322.1 vs 실측
    #    2,605.5 core-h [MEASURED, qstat -x obittime]). 이 값은 executions.jsonl
    #    (append, 태스크당 1쌍)에서 오므로 덮어쓰기에 면역이다. finish 가 없는 run
    #    (외부 종료/wall-kill)은 0 으로 잡히므로 어디까지나 **하한**이고,
    #    n_runs_without_finish 가 0 이 아니면 실소모는 이보다 크다 — 실제 P1b 사례:
    #    finish 0줄이라 하한은 0 이었고 실측은 3 × 64 × 13.5706 h = 2,605.5 였다.
    return {
        "links_executed": links_run,
        "links_skipped_idempotent": links_skipped,
        "stage_run_counts": runs,
        "stage_skip_counts": skips,
        "duplicate_execution": bool(duplicated),
        "duplicated_stages": duplicated,
        "concurrent_logical_runs": multi_host,
        "core_hours_floor_from_executions": round(core_h_floor, 3),
        "n_runs_without_finish": n_runs_without_finish,
        "log_integrity": integrity,
        "hosts_observed": integrity.get("hosts"),
        "warnings": warnings + list(integrity.get("warnings") or []),
    }


#: 🔴 CODER-DECLARED, not a measurement (execlog.SIZE_TRIGGER_FRACTION 과 같은 지위).
#: run→finish 하한은 stage 밖 오버헤드(smoke, python 글루)를 포함하므로 건강한 잡도
#: stage 합보다 조금 크다. 1.2배를 넘으면 stage 마커가 소실/덮어쓰기됐다는 신호로 본다.
CORE_HOURS_UNDERCOUNT_RATIO = 1.2
#: [critic9 MAJOR #3] 비율 단독으로는 작은 총액에서 오탐한다 (total=2.0 에 정상
#: 오버헤드 0.5 core-h 만으로 ratio 1.25 — P5 의 싼 종/P1b hco3 에서 수학적으로 가능).
#: 그래서 **비율 AND 절대 갭** 두 조건이다. 10 core-h 도 CODER-DECLARED 값이다:
#: 건강한 smoke+글루 오버헤드(수 core-h)보다 크고, 실제 사고의 갭(622 이상)보다 훨씬 작다.
CORE_HOURS_UNDERCOUNT_MIN_GAP = 10.0


def core_hours_accounting_warnings(core_hours_total, audit):
    """[A-3] stage 합계가 executions.jsonl 하한보다 작으면 경고 목록을 돌려준다.

    지난 라운드 P1b: stage 마커를 3태스크가 공유·덮어써 회신 `core_hours_total` 이
    322.1 인데 실소모 하한은 944 core-h(3×64코어×4.92h)였다. guard/사이징이 이 숫자를
    근거로 판단하므로 과소계상은 조용한 예산 초과 경로다.
    """
    out = []
    floor = (audit or {}).get("core_hours_floor_from_executions")
    unfinished = (audit or {}).get("n_runs_without_finish") or 0
    total = core_hours_total or 0.0
    if (floor and floor > total * CORE_HOURS_UNDERCOUNT_RATIO
            and floor - total > CORE_HOURS_UNDERCOUNT_MIN_GAP):
        out.append(
            "🔴 core_hours_undercount: stage 기반 core_hours_total=%.1f 이 "
            "executions.jsonl 의 run→finish 하한 %.1f core-h 보다 작다 (기준 %.1f배 "
            "AND 갭 > %.0f core-h). stage 마커가 태스크 간 덮어쓰기로 소실됐을 가능성이 "
            "크다 — 예산·사이징에 %.1f 를 쓰지 말고 하한 이상으로 읽어라." % (
                total, floor, CORE_HOURS_UNDERCOUNT_RATIO,
                CORE_HOURS_UNDERCOUNT_MIN_GAP, total))
    if unfinished:
        out.append(
            "🔴 core_hours_incomplete: finish 줄이 없는 run 이 %d건이다(wall-kill 또는 "
            "노드 사망). 이 실행들의 소모는 **어느 숫자에도 잡혀 있지 않다** — "
            "core_hours_total 도, run→finish 하한도 실소모보다 작다." % unfinished)
    return out


def _g16_last_geometry_xyz(job_dir, log_name):
    """G16 로그의 마지막 orientation 블록 → xyz 문자열.

    G16은 ORCA처럼 IRC 궤적 xyz 파일을 따로 쓰지 않는다. 로그가 유일한 출처다.
    """
    text = _read(os.path.join(job_dir, log_name))
    if not text:
        return None
    geom = g16.last_geometry(text)
    if not geom:
        return None
    lines = ["%d" % len(geom), "last geometry from %s" % log_name]
    for s, x, y, z in geom:
        lines.append("%-3s %14.8f %14.8f %14.8f" % (s, x, y, z))
    return "\n".join(lines) + "\n"


def _skeleton(pid, status, reason=None):
    return {"id": pid, "status": status, "skip_reason": reason,
            "core_hours_total": 0.0, "breakdown": {}, "criteria": {},
            "wall_h": None, "fail_reasons": [reason] if reason else []}


# --------------------------------------------------------------------------
# 파일럿별 수집
# --------------------------------------------------------------------------
def _p1_level_used(job_dir):
    """P1 이 실제로 쓴 레벨. payload 가 ts_method.json 에 남긴다."""
    try:
        with open(os.path.join(job_dir, "ts_method.json")) as fh:
            return json.load(fh).get("level")
    except (OSError, ValueError):
        return None


def collect_p1(store, key="P1"):
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        return _skeleton("P1", "skipped" if st == "not_submitted" else "incomplete",
                         "잡이 %s 상태" % st)
    recs = cost.read_stage_records(job_dir)
    bd = cost.breakdown_core_hours(recs, p1.STAGES)
    adapter = (_read_json(os.path.join(job_dir, "adapter.json")) or {})
    code = adapter.get("qc_code") or ""
    if code.startswith("gaussian"):
        # 🔴 G16 경로: 진동수는 ts_opt 로그 안에(opt+freq 한 잡), IRC 끝점은
        #    각 IRC 로그의 **마지막 orientation 블록**에서 뽑는다.
        # 🔴 [B-3 동류] payload 는 TS 로그를 `ts_qst2.log` 또는 (폴백 시) `ts_opt.log`
        #    로 남기는데 여기는 `tsopt.log` 를 찾고 있었다 — **존재하지 않는 이름**이다.
        #    어느 경로를 탔는지는 payload 가 ts_method.json 에 적으므로 그걸 정본으로
        #    쓰고, 이름 목록은 폴백으로만 둔다.
        ts_log = ((_read_json(os.path.join(job_dir, "ts_method.json")) or {})
                  .get("log"))
        cands = ([ts_log] if ts_log else []) + ["ts_qst2.log", "ts_opt.log", "tsopt.log"]
        ts_log_path = _first_existing(job_dir, cands)
        freq_text = _read(ts_log_path) if ts_log_path else None
        opt_text = freq_text
        fwd_xyz = _g16_last_geometry_xyz(job_dir, "irc_forward.log")
        rev_xyz = _g16_last_geometry_xyz(job_dir, "irc_reverse.log")
        # 🔴 [ADR-090/ADR-092, C-2] C-2 needs the TRUE per-direction termination
        # status, IRC point count, and endpoint energy -- NOT the synthetic
        # single-frame xyz above (that one is deliberately last-frame-only, for
        # the topology check; reusing its frame count would make `n_points`
        # always 1 and C-2 silently unsatisfiable forever). Read the raw logs
        # directly and let `p1.evaluate_p1` build the C-2 detail from them.
        irc_fwd_text = _read(os.path.join(job_dir, "irc_forward.log"))
        irc_rev_text = _read(os.path.join(job_dir, "irc_reverse.log"))
        irc_fwd_g16 = g16.summarize(irc_fwd_text) if irc_fwd_text else None
        irc_rev_g16 = g16.summarize(irc_rev_text) if irc_rev_text else None
        irc_fwd_n_points = (len(g16.parse_geometries(irc_fwd_text))
                            if irc_fwd_text else None)
        irc_rev_n_points = (len(g16.parse_geometries(irc_rev_text))
                            if irc_rev_text else None)
    else:
        freq_path = _first_existing(job_dir, ["freq.out", "freq.log", "p1_freq.out"])
        opt_path = _first_existing(job_dir, ["tsopt.out", "ts_opt.out"])
        freq_text = _read(freq_path) if freq_path else None
        opt_text = _read(opt_path) if opt_path else None
        ircf = _first_existing(job_dir, ["irc_forward.xyz", "irc_F.xyz"])
        ircr = _first_existing(job_dir, ["irc_reverse.xyz", "irc_B.xyz"])
        fwd_xyz = _read(ircf) if ircf else None
        rev_xyz = _read(ircr) if ircr else None
        # 🔴 Non-Gaussian: no G16 termination/energy telemetry exists for this
        # path today, so C-2 correctly falls toward indeterminate rather than
        # toward permission (Rule 18) until an equivalent parser exists for it.
        irc_fwd_g16 = irc_rev_g16 = None
        irc_fwd_n_points = irc_rev_n_points = None
    res = p1.evaluate_p1(
        freq_text=freq_text,
        irc_forward_xyz=fwd_xyz,
        irc_reverse_xyz=rev_xyz,
        wall_h=cost.job_wall_hours(payload),
        breakdown_core_h=bd,
        opt_out_text=opt_text,
        # 🔴 어느 레벨의 Hessian 으로 판정했는지. ADR-032 로 값싼 기저 Hessian 이
        #    될 수 있어졌으므로, 창(M2)과 함께 반드시 기록한다.
        hessian_level=_p1_level_used(job_dir),
        irc_forward_g16=irc_fwd_g16,
        irc_reverse_g16=irc_rev_g16,
        irc_forward_n_points=irc_fwd_n_points,
        irc_reverse_n_points=irc_rev_n_points,
    )
    res["stage_rc"] = cost.stage_status(recs)
    res["adapter"] = adapter
    res["smoke_levels"] = _read_json(os.path.join(job_dir, "smoke_levels.json"))
    if code.startswith("gaussian"):
        res["g16"] = dict(
            (name, g16.summarize(_read(os.path.join(job_dir, name)) or ""))
            for name in (os.path.basename(ts_log_path or ""), "irc_forward.log",
                         "irc_reverse.log")
            if name and os.path.exists(os.path.join(job_dir, name)))
        res["ts_log_used"] = os.path.basename(ts_log_path or "") or None
        if not ts_log_path:
            res.setdefault("warnings", []).append(
                "TS 로그를 찾지 못했다 — 진동수 판정이 불가능하다. "
                "payload 가 어느 이름으로 남겼는지 ts_method.json 을 보라.")
        # 🔴 [ADR-090 item 6, C-12] `payload/P1.sh`'s guards.fallback_decision verdict --
        # whether QST2 was ACCEPTED or the single-ended fallback FIRED, and why. Measured
        # but unread is the same as not measured (§39.0): this makes the decision visible in
        # the artefact, not just on disk in the job_dir.
        c12 = _read_json(os.path.join(job_dir, "ts_qst2_fallback_decision.json"))
        if c12 is not None:
            res["c12_fallback_decision"] = c12
            if c12.get("fallback_fires"):
                res.setdefault("warnings", []).append(
                    "🔴 c12_fallback_fired: QST2's result did not pass the acceptance test "
                    "(%s) -- fell back to a single-ended TS search. See "
                    "c12_fallback_decision for the full record."
                    % ", ".join(c12.get("failed_checks") or c12.get("unevaluated_checks")
                                or ["no acceptance test supplied"]))
    # [C-8-1] TS 전제조건 게이트의 결정 기록 — 거부는 실패가 아니라 **결과**다
    # (endpoint_prep 의 solvent_descriptors_missing 과 같은 지위). 회신에 안 실으면
    # "측정했는데 아무도 안 읽은 값"의 재발이다.
    c8 = _read_json(os.path.join(job_dir, "c8_precondition.json"))
    if c8 is not None:
        res["c8_precondition"] = c8
        if not c8.get("may_start"):
            res.setdefault("warnings", []).append(
                "🔴 c8_refused: TS 탐색이 시작 전에 거부됐다 — 양끝단이 같은 level 의 "
                "수렴 극소(n_imag=0)로 인증되지 않았다 (%d개 사유, "
                "pilots[P1].c8_precondition 참조). 이 거부는 C-8 이 작동한 결과이지 "
                "화학적 실패가 아니다." % len(c8.get("blocking_reasons") or []))
    res.update(p1_degradation(job_dir, res.get("breakdown") or bd))
    res["cost_bias"] = p1_cost_bias(res)
    # 🔒 engineer 사전 확약 트립와이어 — **계산이 필요한 안전장치는 발동하지 않는다.**
    res["longest_stage"] = cost.longest_stage(recs)
    # 🔴 [critic3] 그런데 **필드만 채우는 것도 절반짜리였다.**
    #    세 줄 위 `degraded_reasons` 는 `warnings[]` 에도 싣는다 —
    #    *"필드는 코드가 읽고 warnings 는 사람이 읽는다. 둘 다 필요하다."*
    #    트립와이어는 그 패턴을 안 따라서, **발동해도 사람이 `pilots[].longest_stage` 를
    #    따로 뒤져야** 했다. ⟹ *"사람이 뒤져야 하는 안전장치"* 를 절반만 없앤 셈이다.
    #    🔴 그리고 이건 가상의 엣지케이스가 아니다: `[ESTIMATE]` 최악 칸이 47.8 h 로
    #    트립와이어(40 h)에 **여유 0.2 h** 뿐이라 **이번 제출에서 실제로 발동할 수 있다.**
    if (res.get("longest_stage") or {}).get("exceeds_tripwire"):
        res.setdefault("warnings", []).append(res["longest_stage"]["note"])
    # 🔴 lead 요구: `degraded` 필드만이 아니라 **사람이 읽는 warnings[] 에도** 실어라.
    #    필드는 코드가 읽고 warnings 는 사람이 읽는다 — 둘 다 필요하다.
    if res.get("degraded_reasons"):
        res.setdefault("warnings", []).extend(res["degraded_reasons"])
    res["execution_audit"] = execution_audit(job_dir)
    if res["execution_audit"]["warnings"]:
        res.setdefault("warnings", []).extend(res["execution_audit"]["warnings"])
    if st == "failed":
        res["status"] = "fail"
        res.setdefault("fail_reasons", []).append("job_marker=failed")
    return res


#: 🔒 §R24.3 — P1 단가의 편향 두 항. **부호가 반대라 부분 상쇄한다.**
#: 🔴 이걸 안 실으면 다음 사람이 "P1 단가 = S3 생산 단가"로 그대로 옮겨 쓴다.
P1_COST_BIAS_TERMS = [
    {"source": "crest_skipped", "direction": "under",
     "magnitude_pct": [-15.0, -5.0], "label": "[ESTIMATE]",
     "why": "conformer 표집을 건너뛰면 그 비용이 단가에서 빠진다 ⟹ **과소평가**."},
    {"source": "hessian_recomputed_per_irc", "direction": "over",
     "magnitude_pct": [10.0, 25.0], "label": "[ESTIMATE]",
     "why": "IRC route 가 `irc=(calcfc,…)` 라 방향마다 Hessian 을 새로 계산한다(총 4회). "
            "생산 S3 는 %chk 공유 + `rcfc` 로 2회까지 줄일 수 있다 ⟹ **과대평가**. "
            "🔴 이번 판에는 rcfc 를 넣지 않았다 — G16 이 개발 박스에 없어 검증 불가이고, "
            "실패하면 IRC 가 죽어 P1 의 판정 입력(종점 2개)이 통째로 사라진다."},
]

#: 🔴 실측이 아니라 **route 문자열에서 센 값**이다. `[DERIVED — route]`
#:  ts_qst2 의 calcfc 1 + 그 freq 1 + irc_forward 1 + irc_reverse 1 = 4
P1_HESSIAN_COUNT = 4


def valid_any(tasks):
    return any(t.get("valid") for t in tasks)


def collect_p6(store, keys=None):
    """κ 앵커 3태스크 → κ·S. 🔴 **ADR-048 하드 게이트가 여기 있다.**

    P6 는 array 코어 버그로 **죽지 않는다.** P5/P1b 는 1코어를 받으면 wall 이 747 h 가 되어
    시끄럽게 즉사하지만, P6 는 `%nprocshared=16` 을 1코어 위에 오버서브스크립션해서
    **정상 종료한다.** 그러면 "16스레드 측정점"이 회신에 실리고 **κ 가 16배 틀린다.**
    ⟹ **데이터처럼 보이는 쓰레기.** 이번 라운드 내내 싸운 실패 부류의 정점이다.

    🔒 그래서 판정하지 않는다: `declared == requested == nprocshared` 가 아니면
    그 태스크를 **`[INVALID]` 로 표시하고 κ·S 산출에서 제외한다.**

    🔴 [ADR-091/ADR-092] 이 함수는 `execution_audit`를 전혀 부르지 않았다 --
    `payload/P6.sh` 가 다른 4개 collector 와 같은 `common.sh`/`sei_stage` 를 쓰므로
    `stage_events.jsonl`/`executions.jsonl` 은 실제로 남는데, 아무도 읽지 않았다.
    κ 는 5개월 일정의 단일 임계 경로 변수이므로 중복 실행/손상 로그를 P1 의
    core-h 총액보다 **약하게** 지키는 것은 앞뒤가 바뀐 것이다. 이제 태스크마다
    감사하고 `valid` 를 그 결과에 **게이트**한다(단순 보고가 아니다).
    """
    keys = keys or ["P6_t1", "P6_t16", "P6_t64"]
    tasks = []
    for key in keys:
        st, _payload = job_status(store, key)
        job_dir = store.job_dir(key)
        rec = _read_json(os.path.join(job_dir, "p6_anchor.json")) or {}
        declared = rec.get("declared_threads")
        requested = rec.get("requested_threads")
        try:
            nprocshared = int(rec.get("actual_nprocshared"))
        except (TypeError, ValueError):
            nprocshared = None
        agree = (declared is not None and declared == requested == nprocshared)
        # 🔴 [ADR-091/ADR-092] κ IS the single dominant variable of the 5-month
        # schedule (`weeks(κ,N) = 4.0κ(100/N) + 9.5 + 3.0·n_recomp`), and this
        # anchor task DID write `stage_events.jsonl`/`executions.jsonl` (P6.sh
        # sources `common.sh` and uses `sei_stage`, same as P1/P1b/P3/P5) --
        # `collect_p6` simply never read them before. The ONLY prior check
        # (ADR-048's thread-count agreement above) says nothing about whether
        # the wall_s came from one clean run. critic8's adversarial case:
        # `anchor_t16` run TWICE in `stage_events.jsonl` -> the number on disk
        # is silently "whichever run finished last", not a measurement.
        audit = execution_audit(job_dir)
        integrity_bad = bool(
            audit.get("duplicate_execution")
            or (audit.get("log_integrity") or {}).get("unparseable_count"))
        entry = {
            "id": key, "status": st,
            "declared_threads": declared,
            "requested_threads": requested,
            "nprocshared": nprocshared,
            "cores_observed": rec.get("cores_observed"),
            "wall_s": rec.get("wall_s"),
            "execution_audit": audit,
            # 🔴 GATED, not merely reported (unlike collect_p1's audit today --
            # a separate open item critic8 flagged; here κ's stakes justify
            # gating immediately rather than deferring it).
            "valid": bool(agree and st == "done" and rec.get("rc") == 0
                         and not integrity_bad),
        }
        if not agree:
            entry["invalid_reason"] = (
                "[INVALID] 선언/요청/%%nprocshared 가 일치하지 않는다 "
                "(declared=%s requested=%s nprocshared=%s). 🔴 이 태스크는 κ·S 산출에서 "
                "**제외한다.** 스레드 수가 어긋난 채 정상 종료하면 그 측정점은 "
                "'데이터처럼 보이는 쓰레기'다 — ADR-048."
                % (declared, requested, nprocshared))
        elif integrity_bad:
            entry["invalid_reason"] = (
                "[INVALID] execution_audit 가 이 앵커 태스크의 무결성을 문제 삼았다 "
                "(duplicate_execution=%s, unparseable_lines=%s). 🔴 κ 는 5개월 일정의 "
                "단일 임계 경로 변수다 — 중복 실행되거나 손상된 로그 위의 wall_s 를 "
                "그대로 κ 로 쓰지 않는다. ADR-091/ADR-092."
                % (audit.get("duplicate_execution"),
                   (audit.get("log_integrity") or {}).get("unparseable_count")))
        tasks.append(entry)
    valid = [t for t in tasks if t["valid"] and t.get("wall_s")]
    by_thread = dict((t["declared_threads"], t["wall_s"]) for t in valid)
    statuses = [t["status"] for t in tasks]
    if all(st == "not_submitted" for st in statuses):
        agg_status = "skipped"
    elif any(st == "incomplete" for st in statuses):
        agg_status = "incomplete"
    elif valid_any(tasks):
        agg_status = "pass"
    else:
        agg_status = "fail"
    out = {"id": "P6", "status": agg_status, "tasks": tasks,
           "n_valid": len(valid), "n_invalid": len(tasks) - len(valid),
           "kappa": None, "speedup_16_to_64": None,
           "reference_wall_s_16thread_devbox": P6_REFERENCE_WALL_S,
           "reference_note": ("[MEASURED] 개발 박스 177.3 s @ 16 스레드 Ryzen 7800X3D "
                              "(RT-1c). **같은 계·같은 잡타입일 때만** 비교가 성립한다.")}
    if by_thread.get(16):
        out["kappa"] = round(by_thread[16] / P6_REFERENCE_WALL_S, 3)
        out["kappa_label"] = ("[MEASURED — 이 계·이 잡타입]. 🔴 다른 워크로드로 "
                              "일반화하지 마라. G16 이 아닌 코드에는 적용되지 않는다.")
    if by_thread.get(16) and by_thread.get(64):
        out["speedup_16_to_64"] = round(by_thread[16] / by_thread[64], 3)
        out["speedup_note"] = ("S = w16/w64. 생산 팩킹 이득은 4/S 다(§R22.3). "
                               "S < 1 이면 64 스레드가 더 느리다는 뜻이고 그 자체가 결론이다.")
    if out["n_invalid"]:
        out["warnings"] = [t["invalid_reason"] for t in tasks if not t["valid"]
                           and t.get("invalid_reason")]
    return out


def p1_cost_bias(res):
    """P1 단가를 S3 생산 단가로 옮길 때의 편향. **방향과 크기를 함께 준다.**"""
    terms = []
    for t in P1_COST_BIAS_TERMS:
        if t["source"] == "crest_skipped" and res.get("crest_skipped") is not True:
            continue
        terms.append(dict(t))
    lo = sum(t["magnitude_pct"][0] for t in terms)
    hi = sum(t["magnitude_pct"][1] for t in terms)
    return {
        "hessian_count": P1_HESSIAN_COUNT,
        "hessian_count_source": "[DERIVED — config/qc_levels.json 의 route 문자열에서 셈]",
        "terms": terms,
        "net_pct_range": [round(lo, 1), round(hi, 1)],
        "note": ("🔴 **이 단가를 S3 생산 단가로 그대로 옮겨 쓰지 마라.** 두 항의 부호가 "
                 "반대라 부분 상쇄하지만 0 은 아니다. 8배 스프레드 앞에서 판정을 바꾸지는 "
                 "않는다(engineer §R24.3)."),
    }


def p1_degradation(job_dir, breakdown=None):
    """🔴 **"조용한 성공"을 데이터로 만든다** (ADR-044 / proposer §37).

    CREST 가 없으면 P1 은 **실패하지 않는다.** conformer 표집을 건너뛴 채 `pass` 로 돌아온다.
    ⟹ 우리가 core-h 를 주고 사는 **TS 단가가 과소평가된 채 회신**되고, 받는 쪽은 그것을
    완전한 TS 워크플로 단가로 읽는다. **rc 도 status 도 이 사실을 말해주지 않는다.**

    🔴 이 세션에서 같은 형태가 네 번째다(B-3 / `to_dict()` 400자 컷 / `host` 유실 / 이번 CREST):
    **"시끄러운 실패"인 줄 알았던 것이 실은 "조용한 성공"이었다.**
    그래서 `status` 를 바꾸는 대신 **`degraded` 라는 별도 축**을 만든다 — 실패가 아니라
    **"덜 갖춘 성공"** 이기 때문이다. 판정과 무결성은 서로 다른 질문이다.
    """
    st = _read_json(os.path.join(job_dir, "crest_status.json")) or {}
    skipped = st.get("crest_skipped")
    if skipped is None:
        # 🔴 payload 가 파일을 안 남겼다 = 이 판이 아니거나 잡이 그 전에 죽었다.
        #    `false`(=건너뛰지 않았다)로 채우면 **없는 보증**을 만들어낸다(ADR-036).
        return {"crest_skipped": None, "degraded": None,
                "degraded_reasons": [],
                "degraded_note": "crest_status.json 이 없다 — conformer 표집 수행 여부를 "
                                 "**모른다.** '수행했다'로 읽지 마라."}
    reasons = []
    if skipped:
        reasons.append(
            "crest_absent: conformer 표집을 건너뛰었다. 🔴 이 실행의 TS 단가는 conformer "
            "탐색 비용을 **포함하지 않으므로 과소평가**다 (engineer [ESTIMATE]: TS "
            "워크플로의 5~15%). S3 단가 견적에 그대로 대입하지 마라.")
    return {"crest_skipped": bool(skipped),
            # 🔴 [critic3 사소] payload 가 남기는데 아무도 안 싣던 값. **어느 CREST 를
            #    썼는지**는 재현에 필요하다(동봉본 vs 사이트 설치본은 버전이 다를 수 있다).
            "crest_path": st.get("crest_path"),
            "degraded": bool(reasons),
            "degraded_reasons": reasons,
            "degraded_note": ("이 파일럿은 성공했지만 **일부 단계를 갖추지 못한 채** 성공했다. "
                              "status='pass' 와 무관한 축이다.") if reasons else None}


def collect_p1b(store, key="P1b"):
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        return _skeleton("P1b", "skipped" if st == "not_submitted" else "incomplete",
                         "잡이 %s 상태" % st)
    recs = cost.read_stage_records(job_dir)
    bd = cost.breakdown_core_hours(recs)
    # 🔴 payload 는 이제 단계 이름을 `p1b_stagewise_L<n>_<stage>` 로 남긴다.
    #    값싼 레벨이 level1(TZVPD) → level3(SVPD) 로 바뀌었기 때문이다
    #    (ADR-032 composite 의 값싼 층은 SVPD 다).
    levels = {"level3": {}, "level2": {}}
    for lvl, slot in (("level3", "3"), ("level2", "2")):
        for stage in p1b.STAGES:
            name = "p1b_stagewise_L%s_%s" % (slot, stage)
            entry = {"core_hours": bd.get(name)}
            log = _first_existing(job_dir, [
                os.path.join("steps", "stagewise_L%s_%s" % (slot, stage), "job.log"),
                "%s.log" % name, "%s.out" % name])
            if log:
                text = _read(log)
                if log.endswith(".log"):        # Gaussian
                    scf = g16.parse_scf(text)
                    entry["scf"] = {"converged": scf["converged"],
                                    "max_cycles": scf["max_cycles"],
                                    "total_cycles": scf["total_cycles"],
                                    "cycles": scf["cycles"]}
                    entry["termination"] = g16.parse_termination(text)
                else:                            # ORCA
                    entry["scf"] = p1b.parse_orca_scf_cycles(text)
            levels[lvl][stage] = entry
    res = p1b.evaluate_p1b(levels["level3"], levels["level2"])
    res["stagewise_levels"] = {"cheap": "level3 (G-3, def2-SVPD)",
                               "high": "level2 (G-1, def2-TZVPPD)"}

    # --- RT-1b: 레벨 단가비 5수 (engineer §R16.6) ---------------------------
    # 🔴 `r` 이 총액을 8배로 벌리는 단일 최대 미지수다. 여기가 그걸 좁히는 곳이다.
    steps_dir = os.path.join(job_dir, "steps")
    steps, energies = {}, {}
    for tag in sorted(os.listdir(steps_dir)) if os.path.isdir(steps_dir) else []:
        if tag.startswith("stagewise_"):
            continue
        entry = {"core_hours": bd.get("p1b_%s" % tag)}
        log = os.path.join(steps_dir, tag, "job.log")
        if os.path.exists(log):
            text = _read(log)
            summ = g16.summarize(text)
            entry["converged"] = bool(summ["normal_termination"])
            entry["failure_reason"] = summ["failure_reason"]
            entry["scf_max_cycles"] = summ["scf"]["max_cycles"]
            entry["free_energy_hartree"] = g16.parse_free_energy(text)
            entry["scf_energy_hartree"] = summ["scf"].get("final_energy_hartree")
        steps[tag] = entry
    # ΔG(composite − 전량고수준): composite 는 값싼 G + 고수준 SP 의 전자에너지 치환.
    for tag, entry in steps.items():
        if "_A_cheap_optfreq" in tag:
            sid = tag.split("_A_cheap_optfreq")[0]
            energies.setdefault(sid, {})["g_cheap"] = entry.get("free_energy_hartree")
            energies[sid]["e_cheap"] = entry.get("scf_energy_hartree")
        elif "_C_high_sp_on_cheap" in tag:
            sid = tag.split("_C_high_sp_on_cheap")[0]
            energies.setdefault(sid, {})["e_high_sp"] = entry.get("scf_energy_hartree")
        elif "_B_high_optfreq" in tag:
            sid = tag.split("_B_high_optfreq")[0]
            energies.setdefault(sid, {})["g_full_high"] = entry.get("free_energy_hartree")
    dg_rows = []
    for sid, e in sorted(energies.items()):
        # composite G = 값싼 레벨 G  −  값싼 전자에너지  +  고수준 SP 전자에너지
        gc = None
        if (e.get("g_cheap") is not None and e.get("e_cheap") is not None
                and e.get("e_high_sp") is not None):
            gc = e["g_cheap"] - e["e_cheap"] + e["e_high_sp"]
        dg_rows.append({"id": sid, "g_composite_hartree": gc,
                        "g_full_high_hartree": e.get("g_full_high")})
    res["rt1b"] = p1b.rt1b_summary(steps, dg_rows)
    res["rt1b"]["raw_steps"] = steps

    # --- [U-27] G16 NonEq 스모크 -------------------------------------------
    # 🔴 실패해도 P1b 를 죽이지 않는다. undetermined 로 남기고 넘어간다 —
    #    "루트가 안 된다"는 것 자체가 회신할 정보다(그게 이 스모크의 목적이다).
    u27 = _read_json(os.path.join(job_dir, "u27_noneq.json"))
    if u27 is None:
        u27 = {"unresolved_id": "U-27", "route_accepted": None,
               "nonequilibrium_supported": None,
               "status": "undetermined",
               "why": ("u27_noneq.json 이 없다 — 스모크가 실행되기 전에 잡이 끊겼거나 "
                       "QC 코드가 없어 P1b 가 일찍 종료했다.")}
    else:
        u27["status"] = ("ok" if u27.get("route_accepted")
                         else "undetermined")
    res["u27_noneq"] = u27
    res["execution_audit"] = execution_audit(job_dir)
    if res["execution_audit"]["warnings"]:
        res.setdefault("warnings", []).extend(res["execution_audit"]["warnings"])
    res["core_hours_total"] = round(sum(v for v in bd.values()), 3)
    # 🔴 [A-3] stage 합계는 태스크 간 마커 덮어쓰기에 취약하다 — executions.jsonl
    #    하한과 대조해 과소계상을 시끄럽게 만든다 (지난 라운드: 322.1 vs ≥944).
    acct = core_hours_accounting_warnings(res["core_hours_total"],
                                          res["execution_audit"])
    if acct:
        res.setdefault("warnings", []).extend(acct)
    res["breakdown"] = bd
    res["wall_h"] = cost.job_wall_hours(payload)
    return res


def collect_p3(store, key="P3"):
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        return _skeleton("P3", "skipped" if st == "not_submitted" else "incomplete",
                         "잡이 %s 상태" % st)
    enum = _read_json(os.path.join(job_dir, "p3_enumeration.json")) or {}
    attempts = _read_json(os.path.join(job_dir, "p3_attempts.json")) or []
    if isinstance(attempts, dict):
        attempts = attempts.get("attempts", [])
    recs = cost.read_stage_records(job_dir)
    bd = cost.breakdown_core_hours(recs)
    res = p3.evaluate_p3(
        per_reactant_counts=enum.get("per_reactant_counts") or [],
        attempts=attempts,
        enumeration_mode=enum.get("mode", "unknown"),
        enumeration_completed=bool(enum.get("completed")),
        enumeration_core_hours=bd.get("enumerate"),
        wall_h=cost.job_wall_hours(payload),
        pool_size=enum.get("pool_size"),
    )
    res["breakdown"] = bd
    res["execution_audit"] = execution_audit(job_dir)
    if res["execution_audit"]["warnings"]:
        res.setdefault("warnings", []).extend(res["execution_audit"]["warnings"])
    if st == "failed":
        res["status"] = "fail"
        res.setdefault("fail_reasons", []).append("job_marker=failed")
    return res


def _merge_p5_task_results(job_dir):
    """`p5_task_results.t<N>.json` 들을 p5_results.json 과 같은 형태로 병합한다.

    seed_pairs("짝이 갖춰졌는가")는 태스크 하나가 알 수 없는 교차-태스크 사실이므로
    여기서 계산한다. σ_protocol 은 여기서도 계산하지 않는다(§R2-6 — 받는 쪽 몫).
    """
    from .criteria import p5 as p5_mod
    rows, n_requested, dual = [], None, []
    if not os.path.isdir(job_dir):
        return {}
    task_files = sorted(f for f in os.listdir(job_dir)
                        if re.match(r"^p5_task_results\.t\d+\.json$", f))
    for fn in task_files:
        rec = _read_json(os.path.join(job_dir, fn)) or {}
        rows.extend(rec.get("rows") or [])
        n_requested = n_requested or rec.get("n_requested")
        dual = dual or rec.get("dual_seed_species") or []
    if not task_files:
        return {}
    pairs = {}
    for r in rows:
        if r.get("level") == p5_mod.LEVEL_PRIMARY:
            pairs.setdefault(r.get("id"), []).append(r.get("seed"))
    seed_pairs = dict((k, {"seeds": sorted(v), "complete": len(set(v)) >= 2})
                      for k, v in pairs.items() if k in dual)
    return {"rows": rows, "n_requested": n_requested,
            "dual_seed_species": dual, "seed_pairs": seed_pairs,
            "_merged_from_task_files": len(task_files),
            "_sigma_note": ("σ_protocol 계산은 하지 않았다. 같은 id·같은 level 의 "
                            "seed 0/1 두 행을 비교하면 된다. complete=false 인 종은 "
                            "한쪽이 죽은 것이므로 σ 를 내지 마라.")}


def collect_p5_freq_recovery(store, key="P5_freq_recovery", p5_key="P5"):
    """[§39.103 / §R39.65] Merge `p5_freq_task_results.t<N>.json`, assemble
    `u_cheap = u_opt (round 1, from P5's task results) + u_freq (this round)` per row, labelled
    `assembled` with BOTH halves' provenance (§39.61(c)). Convicted rows: u_freq reported,
    u_cheap EXCLUDED (u_opt biased low). Skipped rows listed with cause, never in any
    denominator. Chemistry stays UNCERTIFIED here -- this function never certifies."""
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        out = _skeleton("P5_freq_recovery", "skipped" if st == "not_submitted" else "incomplete",
                        "잡이 %s 상태" % st)
        return out
    rows = []
    for fn in sorted(os.listdir(job_dir)) if os.path.isdir(job_dir) else []:
        if re.match(r"^p5_freq_task_results(\.t\d+)?\.json$", fn):
            rows.extend((_read_json(os.path.join(job_dir, fn)) or {}).get("rows") or [])
    # round-1 opt costs, by tag
    p5_dir = store.job_dir(p5_key)
    r1 = (_read_json(os.path.join(p5_dir, "p5_results.json")) or _merge_p5_task_results(p5_dir)
          or {}).get("rows") or []
    # [critic12, 2026-08-21] join on `level_label` ("G-1"/"G-2", a config `label` field that
    # does not drift), never on the human-facing `level` string -- round-1 rows written before
    # critic10's stale-string fix carry the pre-fix wordy label, which matches neither today's
    # LEVEL_CHEAP nor LEVEL_PRIMARY, so a string comparison here silently mis-tags EVERY legacy
    # row (confirmed against the real returned tree: every row fell into the `else` branch).
    u_opt, u_opt_unmapped = {}, []
    for r in r1:
        slot = p5.level_key_from_g_label(r.get("level_label"))
        if slot is None:
            u_opt_unmapped.append("%s_s%s (level_label=%r)" % (r.get("id"), r.get("seed"),
                                                                r.get("level_label")))
            continue
        tag = "%s_s%s_L%s" % (r.get("id"), r.get("seed"), slot)
        u_opt[tag] = r.get("core_hours")
    p5_payload = job_status(store, p5_key)[1] or {}
    assembled, skipped, refused, warnings = [], [], [], []
    for r in rows:
        tag = r.get("tag")
        if r.get("status") != "ready":
            skipped.append({"tag": tag, "reason": r.get("reason"), "cause": r.get("cause")})
            continue
        uo, uf = u_opt.get(tag), r.get("u_freq_core_h")
        sym_biased = r.get("u_opt_symmetry_biased")
        entry = {"tag": tag, "level": r.get("level"), "nbasis": r.get("nbasis"),
                 "u_opt_core_h_round1": uo, "u_freq_core_h_round2": uf,
                 "n_imag": r.get("n_imag"),
                 "imaginary_frequencies_cm1": r.get("imaginary_frequencies_cm1"),
                 "n_imag_interpretation_rule": r.get("n_imag_interpretation_rule"),
                 "stored_point_group": r.get("stored_point_group"),
                 "nosymm_verified": r.get("nosymm_verified"),
                 "u_opt_symmetry_biased": sym_biased,
                 "u_opt_symmetry_biased_note": r.get("u_opt_symmetry_biased_note"),
                 "force_max_ratio_freq_over_stored_opt": r.get("force_max_ratio_freq_over_stored_opt"),
                 "normal_termination": r.get("normal_termination"),
                 "chemical_outputs_status": r.get("chemical_outputs_status")}
        if r.get("geometry_refused"):
            entry["u_cheap_core_h"] = None
            entry["u_cheap_status"] = "EXCLUDED: u_opt_from_trapped_geometry (§39.100(b)); u_freq clean"
            entry["u_cheap_usable_for_sizing"] = False
            refused.append(entry)
        elif uo is not None and uf is not None and r.get("normal_termination"):
            entry["u_cheap_core_h"] = round(uo + uf, 5)
            entry["u_cheap_status"] = "assembled"
            # [§39.108(a)] two DIFFERENT flags: geometry_refused (chemistry, above) blocks the
            # row entirely; u_opt_symmetry_biased (cost, ~14/17 rows) blocks SIZING use only --
            # the row is still assembled and reported, just not usable to size future work yet.
            entry["u_cheap_usable_for_sizing"] = (sym_biased is False)
            entry["u_cheap_provenance"] = {
                "u_opt": {"round": "P5 round 1 (generic deck, default grid, symmetry on)",
                          "jobid": (p5_payload.get("job_ids") or [None])[0],
                          "submit_epoch": p5_payload.get("submit_epoch")},
                "u_freq": {"round": "P5_freq_recovery (acetone, UltraFine, nosymm)",
                           "jobid": (payload.get("job_ids") or [None])[0],
                           "submit_epoch": payload.get("submit_epoch")},
                "_caveat": ("§39.61(c): assembled from two rounds/decks -- a total no single "
                            "configuration would reproduce; both halves at 64 threads (§R39.65)")}
            assembled.append(entry)
        else:
            entry["u_cheap_core_h"] = None
            entry["u_cheap_status"] = ("incomplete: %s" % ("freq did not terminate normally"
                                                            if not r.get("normal_termination")
                                                            else "missing u_opt or u_freq"))
            assembled.append(entry)
    recs = cost.read_stage_records(job_dir)
    n_ok = sum(1 for e in assembled if e.get("u_cheap_status") == "assembled")
    n_sizing_biased = sum(1 for e in assembled if e.get("u_cheap_usable_for_sizing") is False)
    if u_opt_unmapped:
        warnings.append("🔴 %d round-1 P5 row(s) had a `level_label` that does not match either "
                        "config level today -- u_opt for those species/seeds is UNAVAILABLE, not "
                        "silently mis-tagged: %s"
                        % (len(u_opt_unmapped), ", ".join(u_opt_unmapped)))
    if skipped:
        warnings.append("🔴 %d row(s) skipped: no converged stored geometry (cause: opt_unconverged) "
                        "-- NOT measured, must not sit in any denominator; not EpsInf casualties; "
                        "a longer wall is the wrong fix (§39.103(3)): %s"
                        % (len(skipped), ", ".join(x["tag"] for x in skipped)))
    if refused:
        warnings.append("🔴 %d convicted symmetry-trapped row(s): u_freq valid, chemistry and "
                        "u_cheap REFUSED (§39.98/§39.100): %s"
                        % (len(refused), ", ".join(x["tag"] for x in refused)))
    if n_sizing_biased:
        # [§39.108(a)] different row set from `refused` above -- conviction (structure wrong,
        # 3 rows) vs symmetry-biased cost (optimisation cheap by an unmeasured |G|, ~14 rows).
        # They overlap and neither contains the other; u_freq stays clean on all of them.
        # [critic12, 10차 배치] the excluded set is `sym_biased is not False` -- True (known
        # symmetry-biased) AND None (unknown/unparsed point group) both land here, conservatively
        # excluded from sizing either way, but they are DIFFERENT CLAIMS and the text must say so.
        biased_true = [e["tag"] for e in assembled
                      if e.get("u_cheap_usable_for_sizing") is False and e.get("u_opt_symmetry_biased") is True]
        biased_unknown = [e["tag"] for e in assembled
                          if e.get("u_cheap_usable_for_sizing") is False and e.get("u_opt_symmetry_biased") is None]
        parts = []
        if biased_true:
            parts.append("%d confirmed u_opt_symmetry_biased=True: %s"
                         % (len(biased_true), ", ".join(biased_true)))
        if biased_unknown:
            parts.append("%d with UNKNOWN stored point group (conservatively excluded, not "
                         "confirmed biased): %s" % (len(biased_unknown), ", ".join(biased_unknown)))
        warnings.append("🟡 %d assembled row(s) NOT usable for SIZING until §39.107's calibration "
                        "probes measure the correction (§39.100(b), §39.108(a)) -- u_cheap is "
                        "still computed and reported for all of them: %s"
                        % (n_sizing_biased, "; ".join(parts)))
    warnings.append("⚠ EXPECTATION (§39.103(4)): the force check is a JOINT test of solvent+grid+"
                    "symmetry; many rows may read indeterminate -- do not read a low reproduce-"
                    "rate as a finding about acetone. Chemical outputs are UNCERTIFIED until lead "
                    "collapses them (§39.82(b)).")
    return {"id": "P5_freq_recovery", "status": st,
            "core_hours_total": round(cost.total_core_hours(recs) or 0.0, 3),
            "breakdown": cost.breakdown_core_hours(recs),
            "wall_h": cost.job_wall_hours(payload),
            "n_rows": len(rows), "n_assembled": n_ok, "n_refused": len(refused),
            "n_skipped": len(skipped), "n_sizing_biased": n_sizing_biased,
            "u_cheap_rows": assembled, "refused_rows": refused, "skipped_rows": skipped,
            "rows_raw": rows,
            "warnings": warnings, "criteria": {}, "fail_reasons": []}


def collect_p5(store, key="P5"):
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        return _skeleton("P5", "skipped" if st == "not_submitted" else "incomplete",
                         "잡이 %s 상태" % st)
    data = _read_json(os.path.join(job_dir, "p5_results.json")) or {}
    if not data:
        # 🔴 [array 분기 사고] array 실행에서는 태스크마다 p5_task_results.t<N>.json 을
        #    남긴다(고정 경로 p5_results.json 을 22태스크가 덮어쓰던 것의 수정).
        #    병합과 seed_pairs 계산은 여기서 한다 — payload 의 어느 태스크도
        #    "내가 마지막"임을 알 수 없기 때문이다.
        data = _merge_p5_task_results(job_dir)
    recs = cost.read_stage_records(job_dir)
    res = p5.evaluate_p5(raw_rows=data.get("rows") or [],
                         core_hours=cost.total_core_hours(recs) or None,
                         wall_h=cost.job_wall_hours(payload),
                         n_requested=data.get("n_requested"))
    res["breakdown"] = cost.breakdown_core_hours(recs)
    # 🔴 [critic3 치명적-1] payload 가 `p5_results.json` 에 남기는 dual-seed 메타를
    #    **아무도 읽지 않고 있었다**(rows/n_requested 만 꺼냈다).
    #    `seed_pairs` 는 어느 종이 시드 쌍을 **완성했는지**(complete)를 말한다 —
    #    한쪽 시드가 죽으면 σ_protocol 을 낼 수 없는데, 그 사실이 회신에 없으면
    #    받는 쪽이 **불완전한 쌍으로 σ 를 계산**한다. 그건 조용히 틀리는 값이다.
    res["dual_seed_species"] = data.get("dual_seed_species")
    res["seed_pairs"] = data.get("seed_pairs")
    res["sigma_note"] = data.get("_sigma_note")
    if res.get("seed_pairs"):
        incomplete = sorted(k for k, v in res["seed_pairs"].items()
                            if not v.get("complete"))
        if incomplete:
            res.setdefault("warnings", []).append(
                "🔴 시드 쌍이 완성되지 않은 종: %s — 이 종들은 σ_protocol 비교가 "
                "불가능하다(한쪽 시드가 실패했거나 실행되지 않았다). **불완전한 쌍으로 "
                "σ 를 계산하지 마라.**" % ", ".join(incomplete))
    # 🔴 [critic10] WALL-KILL MARKERS. A scheduler kill leaves a "run" event with no "finish",
    #    which is indistinguishable from a species that never started -- so the loss silently
    #    entered the denominator as if it had been measured ("P5: 20/22" read as a flat 22).
    #    The payload now writes a marker before it dies; reading it is the other half.
    res["wall_markers"] = [m for m in
                           (_read_json(os.path.join(job_dir, f))
                            for f in sorted(os.listdir(job_dir))
                            if f.startswith("wall_exhausted") and f.endswith(".json"))
                           if m] if os.path.isdir(job_dir) else []
    for _m in res["wall_markers"]:
        res.setdefault("warnings", []).append(
            "🔴 p5_wall_%s: the run stopped on its wall budget (last species: %s, elapsed "
            "%.2f h). 🔴 Species after that point were NOT ATTEMPTED -- they are not failures "
            "and must not sit in the denominator as if they had been measured."
            % (_m.get("status"), _m.get("last_species"), _m.get("elapsed_h") or 0.0))
    res["execution_audit"] = execution_audit(job_dir)
    if res["execution_audit"]["warnings"]:
        res.setdefault("warnings", []).extend(res["execution_audit"]["warnings"])
    # 🔴 [A-3] stage 합계 vs executions.jsonl 하한 대조 (P1b 와 같은 이유).
    acct = core_hours_accounting_warnings(res.get("core_hours_total"),
                                          res["execution_audit"])
    if acct:
        res.setdefault("warnings", []).extend(acct)
    if st == "failed":
        res["status"] = "fail"
        res.setdefault("fail_reasons", []).append("job_marker=failed")
    return res


def collect_p4(store, key="P4"):
    # 🔴 [ADR-091] no `execution_audit(job_dir)` here, ON PURPOSE: `payload/P4.sh` sources
    # `env_common.sh`, not `common.sh` -- it never calls `sei_stage`, so no
    # `stage_events.jsonl`/`executions.jsonl` is ever written for this job_dir. There is
    # nothing to audit. See `execution_audit`'s docstring for the full 5-vs-4 accounting.
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        return _skeleton("P4", "skipped" if st == "not_submitted" else "incomplete",
                         "잡이 %s 상태" % st)
    r = _read_json(os.path.join(job_dir, "p4_result.json")) or {}
    # 🔴 속도비의 분모(=이 GPU 머신의 CPU) 정체를 회신에 싣기 위해 GPU 노드 프로브에서
    #    CPU 모델을 가져온다. 없으면 None으로 남긴다(모르는 것을 지어내지 않는다).
    gpu_probe_cpu = sysprobe.parse_lscpu(
        _read(os.path.join(store.job_dir("probe_gpu_node"), "lscpu.txt")) or "")
    res = p4.evaluate_p4(
        e_gpu_hartree=r.get("e_gpu_hartree"), e_cpu_hartree=r.get("e_cpu_hartree"),
        gpu_wall_s=r.get("gpu_wall_s"), cpu_wall_s=r.get("cpu_wall_s"),
        cpu_cores=r.get("cpu_cores"), max_atoms_ok=r.get("max_atoms_ok"),
        oom_at_atoms=r.get("oom_at_atoms"), gpu_model=r.get("gpu_model"),
        gpu_hours=r.get("gpu_hours"), grad_gpu=r.get("grad_gpu"),
        grad_cpu=r.get("grad_cpu"),
        cpu_model=r.get("cpu_model") or gpu_probe_cpu.get("model_name"),
        gpu_memory_total=r.get("gpu_memory_total"))
    res["level"] = r.get("level")
    res["name_preflight"] = r.get("name_preflight") or r.get("name_preflight_error")
    res["wall_h"] = cost.job_wall_hours(payload)
    res["software"] = r.get("software")
    if st == "failed":
        res["status"] = "fail"
        res.setdefault("fail_reasons", []).append("job_marker=failed")
    return res


# --------------------------------------------------------------------------
# 프로브 수집
# --------------------------------------------------------------------------
def collect_node_probe(store, key="probe_node"):
    """계산 노드에서 수집한 원시 출력 → cluster 블록 보강 (A1/A8/IO/Q2/GPU).

    🔴 [ADR-091] no `execution_audit` here, ON PURPOSE: a one-shot raw node probe, not a
    staged job chain -- `probe_node.sh` never calls `sei_stage`. See `execution_audit`'s
    docstring for the full 5-vs-4 accounting.
    """
    job_dir = store.job_dir(key)
    st, _payload = job_status(store, key)
    raw = _read_json(os.path.join(job_dir, "node_probe.json")) or {}
    out = {"status": st, "source": "compute_node"}
    lscpu = _read(os.path.join(job_dir, "lscpu.txt"))
    out["cpu"] = sysprobe.parse_lscpu(lscpu or "")
    # 🔒 §R23.1 — lscpu 가 Flags 를 안 실으면 /proc/cpuinfo 폴백을 쓴다.
    if not out["cpu"].get("flags"):
        cpuflags = _read(os.path.join(job_dir, "cpuflags.txt")) or ""
        if ":" in cpuflags:
            flags = cpuflags.split(":", 1)[1].split()
            if flags and "읽지" not in cpuflags:
                out["cpu"]["flags"] = flags
                out["cpu"]["flags_source"] = "/proc/cpuinfo"
                out["cpu"]["isa"] = sysprobe.classify_isa(flags)
    out["cpu"].setdefault("flags_source", "lscpu" if out["cpu"].get("flags") else None)
    free = _read(os.path.join(job_dir, "free.txt"))
    out["ram_gb_per_node"] = sysprobe.parse_free(free or "", unit="b")
    if out["ram_gb_per_node"] is None:
        out["ram_gb_per_node"] = sysprobe.parse_meminfo(
            _read(os.path.join(job_dir, "meminfo.txt")) or "")
    df = _read(os.path.join(job_dir, "df.txt"))
    out["filesystems"] = sysprobe.parse_df(df or "")
    out["io_bench"] = sysprobe.io_rates_from_raw(raw.get("io"))
    net = _read(os.path.join(job_dir, "network.txt"))
    # 🔴 파일이 없으면 None으로 남긴다. 빈 문자열을 파싱해 '네트워크 없음'으로
    #    보고하면 '측정 못 함'과 '측정했더니 막혀 있음'을 구분할 수 없다 (U-09 판정 입력).
    out["outbound_network"] = sysprobe.parse_network_probe(net) if net else None
    nsmi = _read(os.path.join(job_dir, "nvidia_smi.txt"))
    out["gpus"] = sysprobe.parse_nvidia_smi(nsmi or "")
    out["env_paths"] = raw.get("env_paths")
    out["quota_raw"] = _read(os.path.join(job_dir, "quota.txt"))
    return out


def collect_throughput(store, key="probe_throughput"):
    # 🔴 [ADR-091] no `execution_audit(job_dir)` here, ON PURPOSE: this collector already reads
    # its own PER-TASK telemetry below (`starts/task_${TID}.json`) -- exactly the pattern
    # `execution_audit`'s own fallback text points OTHER collectors to. Adding a second audit
    # mechanism here would be the "two mechanisms writing overlapping telemetry" failure that
    # function's docstring warns against, not a fix. See its docstring for the full accounting.
    job_dir = store.job_dir(key)
    sub = store.read_marker(key, "submitted") or {}
    subp = sub.get("payload") or {}
    starts_dir = os.path.join(job_dir, "starts")
    starts, ends, hosts = [], [], []
    n_task_files = 0
    if os.path.isdir(starts_dir):
        for fn in sorted(os.listdir(starts_dir)):
            rec = _read_json(os.path.join(starts_dir, fn)) or {}
            n_task_files += 1
            if rec.get("start_epoch"):
                starts.append(rec["start_epoch"])
            if rec.get("end_epoch"):
                ends.append(rec["end_epoch"])
            # 🔴 payload 는 task 마다 host 를 남긴다(probe_throughput.sh).
            #    예전에는 여기서 그것을 **읽고 버렸다** — probes.host_metrics 참조.
            hosts.append(rec.get("host"))
    n_sub = subp.get("n_tasks")
    submitted_epochs = [subp.get("submit_epoch")] * (n_sub or 0) \
        if subp.get("submit_epoch") else []
    m = probes.throughput_metrics(submitted_epochs, starts, ends,
                                  n_submitted_attempts=n_sub,
                                  accepted=subp.get("accepted"))
    m.update(probes.host_metrics(hosts, n_tasks=n_task_files))
    m["status"] = job_status(store, key)[0]
    m["note"] = ("max_concurrent_observed는 제출량(=%s)에 의해 위에서 잘릴 수 있다. "
                 "관측치가 제출량과 같으면 그것은 클러스터 상한이 아니라 하한이다."
                 % n_sub)
    return m


def collect_queue_wait(store, node_counts=(1, 4, 16, 64), prefix="probe_qw_n"):
    # 🔴 [ADR-091] no `execution_audit` here, ON PURPOSE: `payload/probe_queuewait.sh` itself
    # does nothing but sleep -- `started.json` is written elsewhere at submission time, not via
    # `sei_stage`, so no per-task chain exists here to double-execute. See `execution_audit`'s
    # docstring for the full 5-vs-4 accounting.
    entries = []
    for n in node_counts:
        key = "%s%d" % (prefix, n)
        sub = store.read_marker(key, "submitted") or {}
        subp = sub.get("payload") or {}
        started = _read_json(os.path.join(store.job_dir(key), "started.json")) or {}
        entries.append(probes.queue_wait_entry(
            nodes=n,
            submitted_epoch=subp.get("submit_epoch"),
            started_epoch=started.get("start_epoch"),
            partition=subp.get("partition"),
            rejected=bool(subp.get("rejected")),
        ))
    return entries


#: 🔴 [ADR-099] Terminal status tokens `endpoint_prep.sh` may write, kept distinct on purpose:
#: a wall-clock abort (`stage1_budget_exhausted`/`stage2_budget_exhausted`) is an EXECUTION
#: fact and must NEVER be read as `not_converged`, a CHEMICAL fact -- C-2's principle, a
#: fourth instance (f1_required_observables.json's `_also_required_by_other_constraints`).
ENDPOINT_PREP_BUDGET_STATUSES = ("stage1_budget_exhausted", "stage2_budget_exhausted")


def collect_endpoint_prep(store, key):
    """ADR-099's two-stage endpoint preparation, ONE endpoint (`key` is e.g. "P1_endpoint_
    reactant"/"P1_endpoint_product"). Surfaces the F1 falsifier observables
    (`config/f1_required_observables.json`) -- 🔴 reporting only cost and convergence here
    would mean F1 has NOT been run, per that file's own binding rule.
    """
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        out = _skeleton("endpoint_prep", "skipped" if st == "not_submitted" else "incomplete",
                        "잡이 %s 상태" % st)
        out["id"] = key
        return out
    recs = cost.read_stage_records(job_dir)
    terminal = _read_json(os.path.join(job_dir, "terminal_status.json")) or {}
    status = terminal.get("status")
    # [A-1f] stage 이름이 role 접미사를 품는다 (endpoint_rough_<role> — 마커 충돌의
    # 12번째 인스턴스 선행 차단). role 은 terminal 이 정본, 없으면 key 꼬리에서 유도.
    role = terminal.get("role") or key.rsplit("_", 1)[-1]
    bd = cost.breakdown_core_hours(
        recs, ("endpoint_rough_%s" % role,
               # [§39.41 이중 시작점] ALT rough stage 의 core-h 가 합계에서 빠지면
               # R-11(예산 모델 밖의 소비)의 수집판이 된다.
               "endpoint_rough_alt_%s" % role,
               "endpoint_tight_%s" % role))
    out = {
        "id": key,
        "status": status,
        "role": terminal.get("role"),
        "terminal_note": terminal.get("note"),
        # [§39.41] 이중 시작점 선택 기록 — 어느 basin 이 stage 2 로 갔는지.
        "start_selection": _read_json(os.path.join(job_dir, "start_selection.json")),
        # [§39.42(a)] 입력 기하의 provenance sidecar (다중 seed 프로토콜 기록 등).
        "input_provenance": [_read_json(os.path.join(job_dir, f))
                             for f in sorted(os.listdir(job_dir))
                             if f.startswith("input_provenance.")]
                            if os.path.isdir(job_dir) else [],
        "core_hours_total": round(sum(bd.values()), 3) if bd else 0.0,
        "breakdown": bd,
        "wall_h": cost.job_wall_hours(payload),
        # 🔴 the field a reader must check before trusting ANY convergence-shaped field below.
        "budget_exhausted": status in ENDPOINT_PREP_BUDGET_STATUSES,
        "perturbation_provenance": _read_json(
            os.path.join(job_dir, "perturbation_provenance.json")),
        # [§39.41 이중 시작점] ALT guess 의 C-9 kick 기록 — 단일 시작점이면 None.
        "perturbation_provenance_alt": _read_json(
            os.path.join(job_dir, "perturbation_provenance_alt.json")),
        "stage1_exit_structural_set": _read_json(
            os.path.join(job_dir, "stage1_exit_structural_set.json")),
        "f1_observables": _read_json(os.path.join(job_dir, "f1_observables.json")),
        "execution_audit": execution_audit(job_dir),
    }
    if out["execution_audit"]["warnings"]:
        out.setdefault("warnings", []).extend(out["execution_audit"]["warnings"])
    if status == "converged":
        # [engineer9 §R39.63 / proposer8 §39.70, 2026-08-21] pre-registered READING RULE for a
        # cold re-certification: compare covalent graphs against the previously certified
        # geometry BEFORE reading n_imag. A disagreement is `indeterminate (cold-start basin
        # confound)` -- two cold starts can land in different basins (§39.41, §39.42(a)) --
        # never "the surface moved". Resolve with a warm start from the stored checkpoint.
        out["reading_rule"] = (
            "BEFORE reading n_imag: §39.70 covalent-graph comparison vs the previously certified "
            "geometry (jobs/<key>.reset.*/ or the 18.5 arm). Graphs disagree => record "
            "'indeterminate, cause: cold-start basin confound' and resolve with a warm start; "
            "do NOT conclude the solvent surface moved.")
    if out["f1_observables"] is None and status not in (
            None, "skipped", "input_error", "solvent_descriptors_missing",
            "solvent_refused",   # ADR-105: 용매 결정 자체가 없어 거부된 경우 (구분된 토큰)
            "route_smoke_failed",  # [S-1] route/덱 실증 실패 — 본계산 전 정지 (거부=결과)
            "blocked_on_decision") and status not in ENDPOINT_PREP_BUDGET_STATUSES:
        out.setdefault("warnings", []).append(
            "🔴 f1_not_run: status=%r but f1_observables.json is missing -- per "
            "f1_required_observables.json's own binding rule, a result reporting only cost "
            "and convergence has NOT run F1, whatever this status token says." % status)
    if st == "failed":
        out["status"] = out["status"] or "fail"
        out.setdefault("fail_reasons", []).append("job_marker=failed")
    return out


def collect_u56(store, key):
    """U56-2 attempt (payload/U56.sh) 1건의 수집. `key` = U56_RA_scan 등.

    🔴 판정의 경계 (§39.39(f)): U-56a 를 닫는 것은 `pass` 인 완주뿐이고, 그 판정은
    사람이 붙는 리뷰 단계 몫이다 — 여기는 (i) C-8/mapping 게이트의 결정 기록,
    (ii) scan/TS/IRC 아티팩트, (iii) 인수시험(acceptance) **데이터**, (iv) 단계별
    core-h 를 실어 나른다. `status` 는 payload 의 배관 상태 토큰이지 화학 verdict 가
    아니다(C-10 의 경계와 같은 이유로 이름을 나눈다).
    U56.sh 는 common.sh 를 source 하고 sei_stage 를 쓴다 ⟹ `execution_audit` 호출
    (ADR-091 규칙: stage_events/executions 텔레메트리가 실존하는 collector 만 부른다).
    """
    st, payload = job_status(store, key)
    job_dir = store.job_dir(key)
    if st in ("not_submitted", "incomplete"):
        out = _skeleton("u56", "skipped" if st == "not_submitted" else "incomplete",
                        "잡이 %s 상태" % st)
        out["id"] = key
        return out
    recs = cost.read_stage_records(job_dir)
    attempt = _read_json(os.path.join(job_dir, "u56_attempt.json")) or {}
    bd = cost.breakdown_core_hours(
        recs, ("u56_scan", "u56_scan_refine", "u56_tsopt", "u56_qst2",
               "u56_irc_forward", "u56_irc_reverse"))
    rxn = attempt.get("reaction")
    out = {
        "id": key,
        "status": attempt.get("status"),
        "reaction": rxn,
        "method": attempt.get("method"),
        "level": attempt.get("level"),
        "core_hours_total": round(sum(bd.values()), 3) if bd else 0.0,
        "breakdown": bd,
        "wall_h": cost.job_wall_hours(payload),
        "c8_precondition": _read_json(os.path.join(job_dir, "c8_precondition.json")),
        "endpoint_certs": _read_json(os.path.join(job_dir, "endpoint_certs.json")),
        "mapping": (_read_json(os.path.join(job_dir, "u56_%s_mapping.json" % rxn))
                    if rxn else None),
        "mapping_refusal": _read_json(os.path.join(job_dir, "mapping_refusal.json")),
        # [§39.42(a)/(b)] d(Li-O_break) covariate + scan_start_d 는 deck_inputs 에 있다.
        "deck_inputs": (_read_json(os.path.join(job_dir,
                                                "u56_%s_deck_inputs.json" % rxn))
                        if rxn else None),
        "scan_points": _read_json(os.path.join(job_dir, "scan_points.json")),
        # refine 판정 원본 (scan_points 에도 병합돼 있으나, 병합 실패 시에도 판정
        # 기록 자체는 회신에 남아야 한다 — §39.42(b) 트리거는 사전등록의 일부다).
        "refine_decision": _read_json(os.path.join(job_dir, "refine_decision.json")),
        # 🔴 [ADR-110] The GFN2 pre-stage's own cost, with work and charged kept APART: it
        # runs single-threaded inside a G16-sized job, so packing efficiency is visibly low
        # and that is the deliberate price of not spending a round trip on a seconds-long
        # verdict. Averaging the two fields would hide exactly that.
        "gscan_cost": _read_json(os.path.join(job_dir, "gscan_cost.json")),
        # 🔴 [G-SCAN-5, §39.45(a)] gate 의 발동은 **세어서 보고**한다. 한 번도 안 터지면
        # 그 gate 는 unreached 이고(§0-o.4 rule 2), 매번 터지면 틀린 것은 화학이 아니라
        # scan 설계다. 둘 다 판정문 없이는 알 수 없으므로 판정문 자체가 회신에 실린다.
        "gscan_verdict": _read_json(os.path.join(job_dir, "gscan_verdict.json")),
        "ts_acceptance": _read_json(os.path.join(job_dir, "ts_acceptance.json")),
        # 🔴 [§39.62] The spectator test's verdict AND its firings, for the same reason
        # G-SCAN-5 counts its own: a gate nobody ever sees fire is unreached, and one that
        # always fires means the mapping is wrong rather than the chemistry.
        # 🔴 [§39.63] The bracket check runs FIRST and is the gate with a demonstrated hit.
        # Its firings AND its inapplicable cases are both counted: a gate that is never
        # applicable must not read as a gate that never fires.
        "bracket_check": _read_json(os.path.join(job_dir, "bracket_check.json")),
        "spectator_test": _read_json(os.path.join(job_dir, "spectator_test.json")),
        # 🔴 [§39.59] The cap regime this attempt ran under. A rate measured under one set of
        # caps is not comparable with a rate measured under another, and nothing else in the
        # record would reveal that if two rounds were averaged or trended.
        "active_caps": _read_json(os.path.join(job_dir, "active_caps.json")),
        "chk_handoff": [_read_json(os.path.join(job_dir, "chk_handoff_%s.json" % dd))
                        for dd in ("forward", "reverse")],
        # 🔴 A direction refused because rcfc was requested without its Hessian. Recorded
        # separately from the IRC's own outcome: it is plumbing, and pooling it with either
        # the chemical or the budget denominator would corrupt both.
        "irc_refusals": [r for r in
                         (_read_json(os.path.join(job_dir, "irc_%s.refusal.json" % dd))
                          for dd in ("forward", "reverse")) if r],
        # 🔴 [C-2.1, 39.53] HOW each IRC ended. A path that stopped on its step budget (or was
        # cut by a wall/budget cap) reached no minimum and certifies nothing -- and that
        # outcome is a BUDGET-class `indeterminate`, which must never be pooled with the
        # chemical ones when `p` (and hence the 1/p sizing multiplier) is computed.
        # 🔴 [§39.55(b)/§39.70] B+ per direction. C-2 consumes `bplus.agreement`; this is the
        # record a human reads, including WHICH minima the two terminal optimisations reached
        # and whether the comparison was made at all.
        # 🔴 [§39.48(e)] The SP ladder's read-out, including the per-SP cost that REPLACES the
        # derived stack every later rung is currently priced from, and the §R39.28 replan
        # comparison that must be read BEFORE the remaining rungs are submitted.
        "sp_ladder": _read_json(os.path.join(job_dir, "sp_ladder_result.json")),
        "sp_ladder_preconditions": _read_json(
            os.path.join(job_dir, "sp_ladder_preconditions.json")),
        # 🔴 WHICH path points got a single point, and WHICH ONE the barrier is referenced to.
        # Not decoration: `reference_index` plus its note are the record that the barrier was
        # measured from the path's own first frame rather than from the certified reactant's
        # energy -- the §39.64/§39.71 invariant. A reader cannot check that without this.
        "sp_points": _read_json(os.path.join(job_dir, "sp_points.json")),
        "bplus": dict((dd, _read_json(os.path.join(job_dir, "bplus_%s.json" % dd)))
                      for dd in ("forward", "reverse")),
        "irc_completion": dict(
            (dd, _read_json(os.path.join(job_dir, "irc_completion_%s.json" % dd)))
            for dd in ("forward", "reverse")),
        "execution_audit": execution_audit(job_dir),
    }
    if out["execution_audit"]["warnings"]:
        out.setdefault("warnings", []).extend(out["execution_audit"]["warnings"])
    # 🔴 [critic10, Rule 13] "the field is read by code, warnings[] is read by a human. Both
    # are required." Every sibling refusal in this function does this (mapping_refusal,
    # c8_refused); the IRC refusals did not, so a run where BOTH directions refused for want
    # of their Hessian looked clean to anyone skimming warnings[].
    for _r in out.get("irc_refusals") or []:
        out.setdefault("warnings", []).append(
            "🔴 irc_refused(%s): %s -- no IRC was run in this direction, so C-2 cannot "
            "establish anything from it. cause_class=%s (plumbing: neither the chemical nor "
            "the budget denominator)."
            % (_r.get("direction"), _r.get("reason"), _r.get("cause_class")))
    c8 = out["c8_precondition"]
    if c8 and not c8.get("may_start"):
        # 측정했는데 안 읽는 값 금지: 거부는 회신 warnings 로도 올라간다 (collect_p1 의
        # c8_refused 와 같은 규칙).
        out.setdefault("warnings", []).append(
            "c8_refused: %s 의 TS 탐색이 C-8 에서 거부됐다 -- 이것은 게이트의 정상 "
            "동작이며 실패가 아니다. blocking_reasons 는 c8_precondition 에 있다." % key)
    if out["mapping_refusal"]:
        out.setdefault("warnings", []).append(
            "mapping_refused: role→index mapping 이 resolve 되지 않아 덱 생성이 "
            "거부됐다 (§39.26(d)) -- Ω 채점 불가 상태로는 아무것도 내지 않는 것이 맞다.")
    if st == "failed":
        out["status"] = out["status"] or "fail"
        out.setdefault("fail_reasons", []).append("job_marker=failed")
    return out
