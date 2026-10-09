"""배치 계획 검증 규칙 V1~V8 — **왕복을 늘리는 배치를 거부한다.**

각 규칙은 (id, severity, 메시지, 근거문서)를 낸다.
severity: `error`(계획 불성립) / `warn`(성립하나 대가가 있다) / `info`.

🔴 설계 원칙: **왜 안 되는지와 얼마를 잃는지를 함께 낸다.** "위반입니다"만 말하면
사람은 규칙을 우회한다. `RT-3을 쪼개면 1.5~2.0주`처럼 대가를 숫자로 보여야 지켜진다.
"""

ERROR = "error"
WARN = "warn"
INFO = "info"


def _v(rid, severity, msg, src, items=None, cost=None):
    return {"rule": rid, "severity": severity, "message": msg, "source": src,
            "items": items or [], "calendar_cost_weeks": cost}


def validate(plan, items):
    """모든 규칙을 돌린다. 예외를 던지지 않고 위반 목록을 돌려준다."""
    out = []
    out += v1_assigned(plan, items)
    out += v2_rt3_single_submission(plan, items)
    out += v3_dependency_order(plan, items)
    out += v4_wall_limit(plan, items)
    out += v5_user_actions(plan, items)
    out += v6_roundtrip_count(plan, items)
    out += v7_ledger_not_pruned(plan, items)
    out += v8_dag_stage_known(plan, items)
    return out


def v1_assigned(plan, items):
    """모든 작업은 정확히 하나의 RT에 속해야 한다. 미배정은 조용히 사라진다."""
    bad = [i.id for i in items if not i.rt]
    unknown = [i.id for i in items if i.rt and i.rt not in plan.by_id]
    out = []
    if bad:
        out.append(_v("V1", ERROR, "RT 미배정 작업 %d건 — 배치에서 조용히 누락된다"
                      % len(bad), "§R8.5", bad))
    if unknown:
        out.append(_v("V1", ERROR, "정의되지 않은 RT를 참조: %s"
                      % ", ".join(sorted(set(i.rt for i in items
                                             if i.rt not in plan.by_id))),
                      "config/rt_plan.json", unknown))
    return out


def v2_rt3_single_submission(plan, items):
    """🔴 L4의 핵심 규칙.

    `must_not_split` RT 안에 **사람 회신이 필요한 작업이 2건 이상**이면 그 RT는
    실질적으로 쪼개진다(중간 회신마다 왕복 1회). RT-3은 그 대가가 1.5~2.0주다.
    """
    out = []
    for rt in plan.roundtrips:
        if not rt.get("must_not_split"):
            continue
        inside = [i for i in items if i.rt == rt["id"]]
        returns = [i for i in inside if i.needs_return]
        if len(returns) > 1:
            pen = plan.split_penalty_weeks(rt["id"])
            cost = pen[1] if pen else None
            out.append(_v(
                "V2", ERROR,
                "%s 는 단일 제출이어야 하는데 사람 회신 필요 작업이 %d건이다 "
                "(%s). 회신 지점마다 왕복이 생겨 DAG가 쪼개진다.%s"
                % (rt["id"], len(returns), ", ".join(i.id for i in returns),
                   (" 대가: %g~%g주" % tuple(pen)) if pen else ""),
                "§R8.5 / ADR-019", [i.id for i in returns], cost))
    return out


def v3_dependency_order(plan, items):
    """선행 작업이 뒤 RT에 있으면 계획이 성립하지 않는다."""
    where = dict((i.id, i.rt) for i in items)
    out = []
    for i in items:
        for dep in i.depends_on:
            if dep not in where:
                out.append(_v("V3", ERROR,
                              "%s 의 선행 작업 %s 가 계획에 없다" % (i.id, dep),
                              "-", [i.id]))
                continue
            a, b = plan.order(where[dep]), plan.order(i.rt)
            if a is None or b is None:
                continue
            if a > b:
                out.append(_v("V3", ERROR,
                              "%s(%s) 가 선행 작업 %s(%s) 보다 앞선 왕복에 있다"
                              % (i.id, i.rt, dep, where[dep]), "§R8.5", [i.id]))
    return out


def v4_wall_limit(plan, items):
    """ADR-004: 잡 하나가 24 h를 넘으면 스케줄러가 죽인다 → 체인 분할이 필요하다."""
    bad = [i for i in items if i.wall_h > plan.max_wall_h]
    if not bad:
        return []
    return [_v("V4", ERROR,
               "wall 상한 %.0f h 초과 작업 %d건 — 체인(afterany) 분할이 필요하다"
               % (plan.max_wall_h, len(bad)), "ADR-004",
               ["%s(%.1fh)" % (i.id, i.wall_h) for i in bad])]


def v5_user_actions(plan, items):
    """RT 하나당 사용자 개입은 `sbatch` 1회. 그 이상이면 왕복을 숨긴 것이다."""
    out = []
    limit = int(plan.targets.get("user_actions_per_rt", 1))
    for rt in plan.roundtrips:
        inside = [i for i in items if i.rt == rt["id"]]
        if not inside:
            continue
        returns = [i for i in inside if i.needs_return]
        if len(returns) > limit and not rt.get("must_not_split"):
            out.append(_v("V5", WARN,
                          "%s 에 사람 회신 지점이 %d개다(권장 %d). 왕복이 %d회 늘어난다 "
                          "= 달력 +%.1f일"
                          % (rt["id"], len(returns), limit, len(returns) - limit,
                             (len(returns) - limit) * plan.roundtrip_days),
                          "§R2-6 설계원칙 1", [i.id for i in returns],
                          round((len(returns) - limit) * plan.roundtrip_days / 7.0, 2)))
    return out


def v6_roundtrip_count(plan, items):
    """실제로 쓰이는 왕복 수가 확정 구조(7회)를 넘는지."""
    used = sorted(set(i.rt for i in items if i.rt in plan.by_id),
                  key=lambda r: plan.order(r))
    target = plan.target_roundtrips
    if len(used) > target:
        return [_v("V6", ERROR,
                   "왕복 %d회 사용 — 확정 구조 %d회를 초과한다 (달력 +%.1f일)"
                   % (len(used), target, (len(used) - target) * plan.roundtrip_days),
                   "§R8.5", used,
                   round((len(used) - target) * plan.roundtrip_days / 7.0, 2))]
    return []


def v7_ledger_not_pruned(plan, items):
    """🔴 발견 원장은 append-only. 가지치기 작업이 원장에 쓰면 완결성 지표가 죽는다."""
    rules = (plan.rules or {})
    forbidden = dict((f["rule"], f["why"]) for f in rules.get("forbidden") or [])
    out = []
    for i in items:
        if i.writes == "ledger" and _looks_like_pruning(i):
            out.append(_v("V7", ERROR,
                          "%s 가 발견 원장에 가지치기성 쓰기를 한다. %s"
                          % (i.id, forbidden.get("prune_ledger", "")),
                          "02_METHOD_SPEC §23.1 / ADR-027", [i.id]))
        if i.writes == "working_network" and _looks_like_completeness(i):
            out.append(_v("V7", ERROR,
                          "%s 가 작업 network에서 완결성 지표를 계산한다. %s"
                          % (i.id, forbidden.get("completeness_from_working_network", "")),
                          "02_METHOD_SPEC §23.1 / ADR-027", [i.id]))
        if _looks_like_manual_sync(i):
            out.append(_v("V7", ERROR,
                          "%s 가 두 시계를 손으로 동기화한다. %s"
                          % (i.id, forbidden.get("manual_clock_sync", "")),
                          "02_METHOD_SPEC §23.1", [i.id]))
    return out


PRUNE_WORDS = ("prune", "가지치기", "cutoff", "절단", "filter", "여과")
COMPLETENESS_WORDS = ("chao1", "chao", "good-turing", "완결성", "capture-recapture",
                      "포획-재포획", "포획–재포획", "ĉ")
SYNC_WORDS = ("수동 동기화", "manual sync", "clock sync", "시계 동기화")


def _blob(i):
    return " ".join(str(x) for x in (i.id, i.title, i.stage, i.note)).lower()


def _looks_like_pruning(i):
    return any(w in _blob(i) for w in PRUNE_WORDS)


def _looks_like_completeness(i):
    return any(w in _blob(i) for w in COMPLETENESS_WORDS)


def _looks_like_manual_sync(i):
    return any(w in _blob(i) for w in SYNC_WORDS)


def v8_dag_stage_known(plan, items):
    """RT-3 작업의 stage는 DAG에 정의된 것이어야 한다(오타 = 의존성 누락)."""
    known = set(plan.dag_stage_ids())
    bad = [i.id for i in items
           if i.rt == "RT-3" and i.stage and i.stage not in known]
    if not bad:
        return []
    return [_v("V8", WARN,
               "RT-3 DAG에 없는 stage를 참조: %s (정의: %s)"
               % (", ".join(bad), ", ".join(sorted(known))),
               "§R8.5 rt3_dag", bad)]


def worst_severity(findings):
    if any(f["severity"] == ERROR for f in findings):
        return ERROR
    if any(f["severity"] == WARN for f in findings):
        return WARN
    return INFO
