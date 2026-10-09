"""다이제스트 렌더링 — 한 화면(80칸) 안에 끝나야 한다.

길면 안 읽는다. 안 읽으면 L3의 35~50 인간-h 절감이 0이 된다.
기본 출력은 **한 화면**이고, 상세는 `--full` 로만 나온다.
"""

W = 78


def _rule(ch="="):
    return ch * W


def _wrap(text, indent=6, width=W):
    """한글이 섞여 있어 정확한 폭 계산이 어렵다 → 보수적으로 문자 수 기준."""
    out = []
    line = ""
    for word in str(text).split():
        if len(line) + len(word) + 1 > width - indent:
            out.append(line)
            line = word
        else:
            line = (line + " " + word).strip()
    if line:
        out.append(line)
    pad = " " * indent
    return [pad + x for x in out] or [pad]


def _bullet(entry, mark="•"):
    ids = ",".join(entry.get("ids") or [])
    label = entry.get("label")
    head = "%s%s%s" % ("🔴 " if entry.get("urgent") else "",
                       "[%s] " % label if label else "",
                       ids and ids + " " or "")
    body = head + entry.get("text", "")
    lines = _wrap(body, indent=6)
    lines[0] = "   %s %s" % (mark, lines[0].strip())
    if entry.get("age_label"):
        lines[0] = lines[0] + "  (%s)" % entry["age_label"]
    extra = []
    if entry.get("blocked_by"):
        extra.append("      ↳ 막는 것: %s" % ", ".join(entry["blocked_by"]))
    if entry.get("source"):
        extra.append("      ↳ %s" % entry["source"])
    return lines + extra


def render(state, diff, full=False, max_items=6):
    L = []
    hdr = state.get("header") or {}
    L.append(_rule())
    L.append(" 여기서부터 시작 — SEI 프로젝트 세션 다이제스트")
    L.append(_rule())
    L.append(" 문서 기준일 : %s" % (hdr.get("last_updated") or "?"))
    L.append(" 현재 단계   : %s" % (hdr.get("current_phase") or "?"))

    art = state.get("artifacts") or {}
    if art.get("packages") or art.get("tests"):
        pkgs = art.get("packages") or []
        tst = art.get("tests") or {}
        L.append(" 산출물      : %s%s"
                 % (", ".join("%s %sKB" % (p["name"].replace("sei_pilot_", "")
                                           .replace(".tar.gz", ""), p["size_kb"])
                              for p in pkgs) or "패키지 없음",
                    "  테스트 %s개" % tst.get("test_functions") if tst else ""))
        fresh_info = art.get("build_freshness") or {}
        if fresh_info.get("ok") is False:
            L.append(" 🔴 빌드      : tarball 이 소스보다 낡았다 — 지금 인도하면 최신 수정이")
            L.append("                패키지에 들어가지 않는다. src/make_package.sh 를 다시 돌려라.")
        elif fresh_info.get("ok") is True:
            L.append(" 빌드        : ✅ tarball 이 현재 소스와 일치")
    risks = [r for r in state.get("risks") or [] if r["status"] == "open"]
    L.append(" 미해결 위험 : %d건 (🔴 %d건)"
             % (len(risks), sum(1 for r in risks if r["urgent"])))
    L.append("")

    tops = (state.get("buckets") or {}).get("top_issues") or []
    if tops:
        L.append(" [0] 지금 프로젝트를 좌우하는 것")
        for t in tops:
            ids = ",".join(t.get("ids") or [])
            L += _wrap("- %s%s" % (ids and ids + " " or "", t["text"]), indent=6)
        L.append("")

    # ④ 지난 세션 이후 바뀐 것 — 재오리엔테이션 세금의 본체이므로 맨 위에 둔다
    L.append(" [4] 지난 세션 이후 바뀐 것")
    if diff.get("first_run"):
        L.append("      (첫 실행 — 비교할 스냅샷이 없다. 다음 실행부터 변경분이 나온다)")
    elif not diff.get("changes"):
        L.append("      변경 없음. 지난번에 보던 상태 그대로다.")
    else:
        for c in diff["changes"][: (999 if full else max_items)]:
            L += _wrap("- " + c["text"], indent=6)
        if not full and len(diff["changes"]) > max_items:
            L.append("      … 외 %d건 (--full)" % (len(diff["changes"]) - max_items))
    L.append("")

    b = state.get("buckets") or {}
    # 🔴 낡은 절 경고 — 이 도구의 유일한 실패 모드(낡은 것을 최신인 척)를 막는 장치
    for warn_line in _staleness_banner(state):
        L.append(warn_line)

    # ③ 사람만 답할 수 있는 것 — 팀 전체를 막고 있으므로 행동 항목 중 첫 번째
    L.append(" [3] 🔴 내가 답하거나 해야 하는 것 (%d) — 이게 팀을 막고 있다"
             % len(b.get("ask_user") or []))
    if not b.get("ask_user"):
        L.append("      없음. 지금은 사람 답변 대기가 없다.")
    for e in (b.get("ask_user") or [])[: (999 if full else max_items)]:
        L += _bullet(e, "▶")
    L.append("")

    # ① 지금 당장 할 수 있는 것
    L.append(" [1] 지금 당장 할 수 있는 것 (%d)" % len(b.get("act_now") or []))
    if not b.get("act_now"):
        L.append("      없음 — 전부 막혀 있거나 사람 답변 대기다. [3]부터 보라.")
    for e in (b.get("act_now") or [])[: (999 if full else max_items)]:
        L += _bullet(e, "→")
    L.append("")

    # ② 막혀 있는 것
    blocked = b.get("blocked") or []
    L.append(" [2] 막혀 있는 것 (%d)" % len(blocked))
    for e in blocked[: (999 if full else max_items)]:
        L += _bullet(e, "×")
    if not full and len(blocked) > max_items:
        L.append("      … 외 %d건 (--full)" % (len(blocked) - max_items))
    L.append("")

    # 팀 상태 (누가 무엇을 들고 있나)
    # 🔴 [R-10 fix] 이 절은 유일하게 max_items 상한이 없었다 -- 세션이 길어질수록(팀원이
    #    쌓일수록) 렌더 길이가 문서 분량에 비례해 자라는 것이 정확히 이 도구의 실패
    #    모드다("길면 안 읽는다"). 지금 활동 중(working/idle 등, stopped 아닌 상태)인
    #    팀원은 항상 전부 보여준다 -- 재오리엔테이션에 가장 필요한 정보이고 보통 수가
    #    작다. stopped 팀원은 다른 절과 같은 max_items 상한 + "--full" 탈출구를 쓴다.
    team = state.get("team") or []
    if team:
        active = [t for t in team if t.get("status") != "stopped"]
        stopped = [t for t in team if t.get("status") == "stopped"]
        shown_stopped = stopped if full else stopped[:max_items]
        L.append(" 팀 (%d, stopped %d)" % (len(team), len(stopped)))
        for t in active + shown_stopped:
            L.append("   %-9s %s" % (t["name"], t["status"][:40]))
            if t["task"]:
                L += _wrap(t["task"][:120], indent=8)
        if not full and len(stopped) > len(shown_stopped):
            L.append("      … stopped %d건 더 (--full)"
                     % (len(stopped) - len(shown_stopped)))
        L.append("")

    if full:
        L += _render_full(state)

    # 하단: 파싱 신뢰도. 조용히 놓친 것이 있으면 여기서 드러난다.
    warn = []
    if state.get("unresolved_unparsed"):
        warn.append("식별자 없는 미확정 항목 %d건" % state["unresolved_unparsed"])
    missing = [d for d in ("05_STATE.md", "01_DECISION_LOG.md")
               if d not in (state.get("docs_present") or [])]
    if missing:
        warn.append("문서 없음: %s" % ", ".join(missing))
    all_risks = state.get("risks") or []
    n_open = sum(1 for r in all_risks if r["status"] == "open")
    L.append(_rule("-"))
    L.append(" 파싱: 미확정 %d(열림 %d) · 위험 %d(미해결 %d) · ADR %d · 액션 %d%s"
             % (len(state.get("unresolved") or []),
                sum(1 for u in state.get("unresolved") or []
                    if u["status"] in ("open", "partial")),
                len(all_risks), n_open,
                len(state.get("adrs") or []), len(state.get("next_actions") or []),
                ("  ⚠ " + "; ".join(warn)) if warn else ""))
    L.append(_rule("-"))
    return "\n".join(L)


def _staleness_banner(state):
    """「다음 액션」 절이 오래 안 바뀌었으면 [1]을 믿지 말라고 먼저 말한다."""
    from . import digest as digest_mod
    out = []
    info = digest_mod.section_staleness(state, "05_STATE.md", "다음 액션")
    if info and info["stale"]:
        out.append(" ⚠ 「%s」 절이 %s%.0f일째 변경 없음 — 아래 [1] 항목이 이미 끝난 일일 수"
                   % (info["section"], "" if info["observed"] else "최소 ",
                      info["age_days"]))
        out.append("   있다. 문서를 먼저 갱신하라. (낡은 항목을 최신인 척 보여주는 것이"
                   " 이 도구의 유일한 실패 모드다)")
        out.append("")
    return out


def _render_full(state):
    L = []
    risks = [r for r in state.get("risks") or [] if r["status"] == "open"]
    if risks:
        L.append(" 미해결 위험 (%d)" % len(risks))
        for r in risks:
            L += _wrap("%s%s %s" % ("🔴 " if r["urgent"] else "", r["id"],
                                    r["text"][:120]), indent=6)
        L.append("")
    gates = state.get("gates") or []
    if gates:
        L.append(" 게이트")
        for g in gates:
            L.append("      %-10s %s" % (g["gate"], g["state"][:50]))
        L.append("")
    cons = state.get("coder_constraints") or []
    if cons:
        L.append(" 구현 구속조건 (%d) — 코드가 반드시 지켜야 하는 것" % len(cons))
        for c in cons[:15]:
            L += _wrap("[%s:%d] %s" % (c["doc"], c["line"], c["text"][:110]),
                       indent=6)
        L.append("")
    prog = state.get("progress") or []
    if prog:
        L.append(" 최근 진행 로그")
        for p in prog:
            L += _wrap("%s  %s" % (p["date"], p["event"][:110]), indent=6)
        L.append("")
    return L
