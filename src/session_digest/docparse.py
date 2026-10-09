"""프로젝트 문서 파서 — 전부 순수 함수 (문자열 → 구조).

파싱 대상은 **우리 팀의 문서 규약**(`00_PROJECT_BRIEF.md` §5)이다:
  * `[UNRESOLVED]` 태그, `- [ ]/[~]/[x]` 체크박스, `**U-NN**`/`**R-NN**`/`Q<n>` 식별자
  * ADR 형식 (`## ADR-NNN: 제목` + `- **Status**:`)
  * 팀 상태 표, 다음 액션 목록, 진행 로그 표

🔴 설계 원칙: **조용히 버리지 않는다.** 인식하지 못한 항목은 `unparsed`로 세어
다이제스트 하단에 건수를 보고한다. 규약이 바뀌면 그 사실이 드러나야 한다.
(문서는 다른 teammate 소유이므로 우리가 규약을 강제할 수 없다.)
"""

import re

# --- 식별자 패턴 -----------------------------------------------------------
RE_U = re.compile(r"\*\*(U-\d+[a-z\-]*)\*\*")
#: 🔴 [critic10] Risk ids, in ANY of the emphasis forms 05_STATE.md's own convention uses:
#: `**R-5**` (open) and `~~**R-5**~~` / `~~R-5~~` (closed). The pattern was bold-only, so the
#: four closed entries -- written exactly per the documented convention -- were **dropped
#: entirely**, not miscounted: `parse_risks` never saw them.
#: 🔒 The doc was patched to satisfy the parser (bold required INSIDE the strikethrough) and
#: the constraint written down in prose. That works and it is a footgun: a rule that lives only
#: in a comment is enforced by whoever remembers to read it. Widening the pattern removes the
#: rule instead of documenting it -- "written but not read", in our own tooling.
RE_R = re.compile(r"(?:\*\*|~~)+(R-\d+)(?:\*\*|~~)+|\b(R-\d+)\b(?=\*\*|~~|\s)")


def _risk_id(line):
    """The risk id on a list line, whichever emphasis wraps it."""
    m = RE_R.search(line)
    return (m.group(1) or m.group(2)) if m else None
RE_Q = re.compile(r"\b(Q\d+)\b")
RE_ADR_REF = re.compile(r"\b(ADR-\d+)\b")
RE_ADR_HEAD = re.compile(r"^##\s+(ADR-\d+)\s*:\s*(.+?)\s*$")
RE_STATUS = re.compile(r"^-\s+\*\*Status\*\*\s*:\s*(.+?)\s*$")
RE_DATE = re.compile(r"^-\s+\*\*Date\*\*\s*:\s*(.+?)\s*$")
RE_STAGE = re.compile(r"^-\s+\*\*Stage\*\*\s*:\s*(.+?)\s*$")
RE_CHECK = re.compile(r"^-\s+\[([ x~])\]\s*(.*)$")
RE_HEADING = re.compile(r"^(#{1,4})\s+(.*)$")

#: "U-05 확정 후" 처럼 **선행 조건**을 나타내는 표현
RE_DEPENDS = re.compile(r"(U-\d+[a-z\-]*|ADR-\d+|Q\d+|P\d+)\s*(?:확정|해결|판정|회신|완료)\s*(?:후|뒤|시)")
#: "판정 중", "대기", "회신 대기" 등 **대기 상태** 표현
WAITING_WORDS = ("판정 중", "판정중", "대기", "회신 전", "미회신", "확인 필요", "진행 중")
#: 사용자(인간)만 답할 수 있는 항목 표현
#: 🔴 "사용자 지시"는 **이미 받은 지시**라 여기 넣으면 안 된다(오탐으로 확인됨).
USER_WORDS = ("사용자만 답", "사용자 확인 필요", "사용자에게 확인", "사용자 답변 대기",
              "사용자가 답해야", "사용자 판단 필요", "사용자에게 물어", "사용자 승인 대기")


def strip_md(text):
    """굵게/취소선/코드 마크업을 벗겨 한 줄 요약용 평문으로."""
    t = re.sub(r"~~(.*?)~~", r"\1", text)
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", t)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    t = re.sub(r"\s+", " ", t)
    return t.strip()


def sections(text):
    """마크다운을 `## 제목` 단위로 쪼갠다 → {제목: (시작줄, [줄...])}"""
    out = {}
    cur_title = "_preamble"
    cur_start = 1
    buf = []
    for i, line in enumerate(text.splitlines(), 1):
        m = RE_HEADING.match(line)
        if m and len(m.group(1)) <= 2:
            out[cur_title] = (cur_start, buf)
            cur_title = strip_md(m.group(2))
            cur_start = i
            buf = []
        else:
            buf.append((i, line))
    out[cur_title] = (cur_start, buf)
    return out


def section_ranges(text):
    """{섹션제목: (시작줄, 끝줄)} — 신선도 추적과 '이 줄이 어느 절인가' 판정용."""
    out = {}
    cur_title, cur_start = "_preamble", 1
    last = 0
    for i, line in enumerate(text.splitlines(), 1):
        last = i
        m = RE_HEADING.match(line)
        if m and len(m.group(1)) <= 2:
            out[cur_title] = (cur_start, i - 1)
            cur_title, cur_start = strip_md(m.group(2)), i
    out[cur_title] = (cur_start, last)
    return out


def section_of_line(ranges, lineno):
    for title, (a, b) in ranges.items():
        if a <= lineno <= b:
            return title
    return None


def find_section(secs, *needles):
    """제목에 needle이 들어간 첫 섹션. 제목이 조금 바뀌어도 견디게 부분일치."""
    for title, payload in secs.items():
        low = title.lower()
        if all(n.lower() in low for n in needles):
            return payload[1]
    return []


# --- 05_STATE.md -----------------------------------------------------------
def parse_header(text):
    out = {"last_updated": None, "current_phase": None}
    for line in text.splitlines()[:12]:
        m = re.match(r"\*\*Last updated\*\*\s*:\s*(.+)", line)
        if m:
            out["last_updated"] = strip_md(m.group(1))
        m = re.match(r"\*\*Current phase\*\*\s*:\s*(.+)", line)
        if m:
            out["current_phase"] = strip_md(m.group(1))
    return out


def parse_open_items(text):
    """`## 미확정` 섹션의 U-NN 항목 → 상태/제목/선행조건.

    `- [ ]` 미해결 / `- [~]` 부분해결 / `- [x]` 해결
    항목이 여러 줄에 걸칠 수 있으므로 다음 체크박스 전까지를 본문으로 본다.
    """
    secs = sections(text)
    lines = find_section(secs, "미확정")
    items = []
    unparsed = 0
    cur = None
    for lineno, line in lines:
        m = RE_CHECK.match(line)
        if m:
            if cur:
                items.append(_finish_item(cur))
            mark = {" ": "open", "~": "partial", "x": "closed"}[m.group(1)]
            body = m.group(2)
            ids = RE_U.findall(body)
            cur = {"kind": "unresolved", "status": mark, "line": lineno,
                   "id": ids[0] if ids else None, "body": [body]}
            if not ids:
                unparsed += 1
        elif cur is not None and line.strip() and line.startswith(("  ", "\t")):
            cur["body"].append(line.strip())
        elif line.strip() and not line.startswith(">"):
            if cur:
                items.append(_finish_item(cur))
                cur = None
    if cur:
        items.append(_finish_item(cur))
    return items, unparsed


def _finish_item(cur):
    body = " ".join(cur.pop("body"))
    cur["text"] = strip_md(body)
    cur["depends_on"] = sorted(set(RE_DEPENDS.findall(body)))
    cur["adrs"] = sorted(set(RE_ADR_REF.findall(body)))
    cur["waiting"] = any(w in body for w in WAITING_WORDS)
    cur["needs_user"] = any(w in body for w in USER_WORDS)
    cur["urgent"] = "🔴" in body
    return cur


def parse_risks(text):
    """`## 알려진 미해결 위험` → R-NN. `- [x] ~~R-NN~~` 는 해소된 것."""
    secs = sections(text)
    lines = find_section(secs, "위험")
    risks = []
    cur = None
    for lineno, line in lines:
        m = re.match(r"^-\s+(\[[ x~]\]\s*)?(.*)$", line)
        rid = _risk_id(line) if m else None
        if rid:
            if cur:
                risks.append(_finish_risk(cur))
            closed = bool(m.group(1) and "x" in m.group(1))
            cur = {"id": rid, "line": lineno,
                   "status": "closed" if closed else "open", "body": [line.strip()]}
        elif cur is not None and line.startswith(("  ", "\t")) and line.strip():
            cur["body"].append(line.strip())
        elif line.strip().startswith("#"):
            break
    if cur:
        risks.append(_finish_risk(cur))
    return risks


def _finish_risk(cur):
    body = " ".join(cur.pop("body"))
    cur["text"] = strip_md(body)
    cur["urgent"] = "🔴" in body
    cur["unresolved_tag"] = "[UNRESOLVED]" in body
    return cur


def parse_team(text):
    """`## 팀 상태` 표 → teammate별 상태·현재 작업."""
    secs = sections(text)
    lines = find_section(secs, "팀 상태")
    rows = []
    cur = None
    for lineno, line in lines:
        if not line.strip().startswith("|"):
            if cur and line.strip() and not line.startswith(">"):
                cur["task"] = (cur["task"] + " " + strip_md(line.strip().rstrip("|"))).strip()
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        name = strip_md(cells[0])
        if name.lower() in ("teammate", "지위", "name"):
            continue
        cur = {"name": name, "status": strip_md(cells[1]),
               "task": strip_md(cells[2]), "line": lineno}
        rows.append(cur)
    return rows


#: 완료 표시로 시작하는 액션. 🔴 lead 지시: 문서 서식이 항상 정확할 거라 가정하지 마라.
#: 취소선(~~)뿐 아니라 ✅/🟢/"완료"로 시작하는 줄도 완료로 본다.
RE_DONE_PREFIX = re.compile(r"^\s*(?:[✅🟢☑✔]|완료\b|\[완료\])")
#: 완료 줄 뒤에 붙는 후속 작업. `... 완료 → ADR-027. 다음: X를 한다`
RE_FOLLOWUP = re.compile(r"(?:다음|후속|이어서)\s*[:：]\s*(.+)$")

#: 액션의 소유자. 누가 들고 있는지가 "내가 지금 할 수 있는가"를 가른다.
OWNERS = ("사용자", "proposer", "engineer", "coder", "critic", "organizer", "lead")


def action_owner(text, context_heading=None):
    """액션 문자열에서 소유자를 뽑는다.

    인식 형태: `RT-1 파일럿 실행 — 사용자.` / `proposer: U-05 정식 설계` /
    상위 소제목이 `외부 대기` 면 사용자 소유로 본다.
    """
    head = text[:60]
    for o in OWNERS:
        if re.search(r"(^|[\s—\-–(])%s\s*[:：.,)]" % re.escape(o), head) or \
           re.search(r"[—\-–]\s*%s\b" % re.escape(o), head):
            return o
    if context_heading and ("외부 대기" in context_heading or "사용자" in context_heading):
        return "사용자"
    return None


def parse_next_actions(text):
    """`## 다음 액션` 번호 목록. `~~취소선~~` = 완료, `[진행 중]` = 진행 중.

    소제목(`### 🔴 외부 대기`)을 문맥으로 들고 다녀 소유자 판정에 쓴다.
    """
    secs = sections(text)
    lines = find_section(secs, "다음 액션")
    out = []
    heading = None
    cur = None
    for lineno, line in lines:
        h = re.match(r"^#{3,4}\s+(.*)$", line)
        if h:
            heading = strip_md(h.group(1))
            cur = None
            continue
        m = re.match(r"^\s*(\d+)[.)]\s+(.*)$", line)
        if m:
            raw = m.group(2)
            plain = strip_md(raw)
            done = (raw.strip().startswith("~~") or "~~" in raw[:6]
                    or bool(RE_DONE_PREFIX.match(plain)))
            cur = {"n": int(m.group(1)), "line": lineno, "text": plain,
                   "status": ("done" if done else
                              ("in_progress" if "진행 중" in raw else "todo")),
                   "urgent": "🔴" in raw, "heading": heading, "raw": raw}
            out.append(cur)
        elif cur is not None and line.startswith((" ", "\t")) and line.strip():
            # 여러 줄에 걸친 액션 — 소유자가 둘째 줄에 있을 수 있다
            cur["text"] = (cur["text"] + " " + strip_md(line)).strip()
    for a in out:
        a["owner"] = action_owner(a["text"], a.get("heading"))
        # 완료 줄에 후속 작업이 붙어 있으면 그것만 뽑는다.
        # (문서가 "완료 → ... . 다음: X" 형태로 한 줄에 섞여 쓰이는 실사용 서식이다)
        a["followup"] = None
        if a["status"] == "done":
            m = RE_FOLLOWUP.search(a["text"])
            if m:
                a["followup"] = m.group(1).strip()
        a.pop("raw", None)
    return out


def parse_gates(text):
    secs = sections(text)
    lines = find_section(secs, "gate")
    out = []
    for lineno, line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 3 or set(cells[0]) <= set("-: "):
            continue
        if cells[0].lower() in ("gate",):
            continue
        out.append({"gate": strip_md(cells[0]), "state": strip_md(cells[-1]),
                    "line": lineno})
    return out


def parse_progress_log(text, limit=8):
    """`## 진행 로그` 표의 마지막 n개 = '지난 세션에 무슨 일이 있었나'."""
    secs = sections(text)
    lines = find_section(secs, "진행 로그")
    rows = []
    for lineno, line in lines:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 2 or set(cells[0]) <= set("-: "):
            continue
        if cells[0].lower().startswith(("날짜", "date")):
            continue
        rows.append({"date": strip_md(cells[0]), "event": strip_md(cells[1]),
                     "line": lineno})
    return rows[-limit:]


def parse_highlights(text):
    """문서 앞부분의 인용 블록(`>`) = lead가 올려둔 최상위 이슈."""
    out = []
    buf = []
    start = None
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith(">"):
            if start is None:
                start = i
            buf.append(line.lstrip("> ").rstrip())
        else:
            if buf:
                out.append(_finish_highlight(buf, start))
                buf, start = [], None
    if buf:
        out.append(_finish_highlight(buf, start))
    return out


#: [0]에서 제외할 '이미 끝난 것' 표시. lead 요청 #3 — 취소선 배너가 100줄 넘게 쌓여
#: [0]의 신호 대 잡음비를 떨어뜨린다.
CLOSED_MARKS = ("해소", "CLOSED", "Superseded", "해결됨")
#: 그러나 스스로 '아직 열려 있다'고 선언한 블록은 위 단어가 있어도 닫힌 것으로 보지 않는다.
#: (예: "…는 해소되지 않았다 [UNRESOLVED]") — 살아 있는 이슈를 숨기면 안 된다.
OPEN_MARKS = ("[UNRESOLVED]", "미해결", "판정 중", "판정중", "대기 중")


def _is_resolved(body):
    head = body.lstrip()
    if head.startswith(("✅", "🟢", "~~")):
        return True
    if any(w in body for w in CLOSED_MARKS) and not any(w in body for w in OPEN_MARKS):
        return True
    return False


def _finish_highlight(buf, start):
    body = " ".join(x for x in buf if x)
    return {
        "line": start,
        "text": strip_md(body),
        "resolved": _is_resolved(body),
        "urgent": body.lstrip().startswith("🔴") or "🔴" in body[:40],
        "questions": sorted(set(RE_Q.findall(body))),
        "adrs": sorted(set(RE_ADR_REF.findall(body))),
        "unresolved_tag": "[UNRESOLVED]" in body,
        "needs_user": any(w in body for w in USER_WORDS),
    }


# --- 01_DECISION_LOG.md ----------------------------------------------------
def parse_adrs(text):
    """ADR 목록 → id/제목/Status/Date/Stage. Proposed는 '아직 확정 아님'이다."""
    adrs = []
    cur = None
    for i, line in enumerate(text.splitlines(), 1):
        m = RE_ADR_HEAD.match(line)
        if m:
            if cur:
                adrs.append(cur)
            cur = {"id": m.group(1), "title": strip_md(m.group(2)), "line": i,
                   "status": None, "date": None, "stage": None}
            continue
        if cur is None:
            continue
        m = RE_STATUS.match(line)
        if m and cur["status"] is None:
            cur["status"] = strip_md(m.group(1))
        m = RE_DATE.match(line)
        if m and cur["date"] is None:
            cur["date"] = strip_md(m.group(1))
        m = RE_STAGE.match(line)
        if m and cur["stage"] is None:
            cur["stage"] = strip_md(m.group(1))
    if cur:
        adrs.append(cur)
    for a in adrs:
        st = (a["status"] or "").lower()
        a["final"] = st.startswith("accepted") and "대기" not in (a["status"] or "")
        a["proposed"] = st.startswith("proposed") or "조건부" in (a["status"] or "")
        a["superseded"] = "superseded" in st
    return adrs


# --- coder 구속조건 --------------------------------------------------------
CODER_BINDING_WORDS = ("coder 구속", "coder 구속조건", "coder에게", "coder의 1순위",
                       "구현 구속", "coder는", "coder 지시")


def parse_coder_constraints(docs):
    """여러 문서에서 '구현이 반드시 지켜야 할 것'만 뽑는다.

    docs: {파일명: 본문}
    """
    out = []
    for name, text in sorted(docs.items()):
        for i, line in enumerate(text.splitlines(), 1):
            if any(w in line for w in CODER_BINDING_WORDS):
                clean = strip_md(line.lstrip("->| "))
                if len(clean) < 8:
                    continue
                out.append({"doc": name, "line": i, "text": clean,
                            "urgent": "🔴" in line})
    return out
