"""세션 다이제스트 조립 — "여기서부터 시작" (L3, 03_COMPUTE_PLAN §R3.4).

🔴 이 도구의 목적은 **요약이 아니다.** 산발적으로 접속하는 사람이
"내가 어디까지 했더라"를 다시 읽는 시간을 없애는 것이다. 그래서 문서를 줄이는 대신
**세 개의 서로 다른 행동 범주로 분리**한다:

    ① 지금 당장 할 수 있는 것   (막힌 것이 없다. 앉으면 바로 시작)
    ② 막혀 있는 것             (무엇이 풀려야 움직이는지 함께)
    ③ 내가 답해야 하는 것       (사람만 답할 수 있는 질문 — 이게 팀 전체를 막고 있다)

그리고 ④ **지난 세션 이후 바뀐 것**을 낸다. 재오리엔테이션 세금의 본체가
"그동안 뭐가 바뀌었지?"이기 때문이다(§R3.1 [ESTIMATE] 15~20%).
"""

import os
import re
import sys
import time

from . import docparse as dp
from . import freshness as fresh

DOC_STATE = "05_STATE.md"
DOC_ADR = "01_DECISION_LOG.md"


def load_docs(docs_dir):
    out = {}
    if not os.path.isdir(docs_dir):
        return out
    for fn in sorted(os.listdir(docs_dir)):
        if fn.endswith(".md"):
            try:
                with open(os.path.join(docs_dir, fn), errors="replace") as fh:
                    out[fn] = fh.read()
            except OSError:
                continue
    return out


def build(docs_dir, repo_root=None, prev_snapshot=None, now=None,
          stale_days=fresh.DEFAULT_STALE_DAYS):
    """문서 → 구조화 상태(dict). 렌더링/스냅샷이 이것만 본다.

    prev_snapshot 을 주면 섹션 신선도(마지막 변경 이후 경과일)를 함께 계산한다.
    """
    now = now or time.time()
    docs = load_docs(docs_dir)
    state_text = docs.get(DOC_STATE, "")
    adr_text = docs.get(DOC_ADR, "")

    items, unparsed = dp.parse_open_items(state_text)
    adrs = dp.parse_adrs(adr_text)
    st = {
        "docs_dir": docs_dir,
        "docs_present": sorted(docs.keys()),
        "header": dp.parse_header(state_text),
        "unresolved": items,
        "unresolved_unparsed": unparsed,
        "risks": dp.parse_risks(state_text),
        "team": dp.parse_team(state_text),
        "next_actions": dp.parse_next_actions(state_text),
        "gates": dp.parse_gates(state_text),
        "progress": dp.parse_progress_log(state_text),
        "highlights": dp.parse_highlights(state_text),
        "adrs": adrs,
        "coder_constraints": dp.parse_coder_constraints(docs),
        "doc_sizes": dict((k, len(v.splitlines())) for k, v in docs.items()),
        "artifacts": scan_artifacts(repo_root) if repo_root else {},
    }
    # --- 신선도 (lead 요청 #1) ---
    ranges = dict((name, dp.section_ranges(body)) for name, body in docs.items())
    st["section_ranges"] = ranges
    st["file_age_days"] = fresh.file_ages(docs_dir, now)
    st["section_freshness"] = fresh.merge(prev_snapshot,
                                          fresh.section_hashes(docs, ranges), now)
    st["stale_days"] = stale_days
    st["now_epoch"] = int(now)
    st["buckets"] = classify(st)
    _attach_ages(st, now)
    return st


def _attach_ages(st, now):
    """각 항목에 '그 줄이 속한 절이 마지막으로 바뀐 뒤 며칠'을 붙인다."""
    for bucket in ("ask_user", "blocked", "act_now", "top_issues"):
        for e in st["buckets"].get(bucket) or []:
            doc, _, lineno = (e.get("source") or "").partition(":")
            if not lineno.isdigit():
                continue
            title = dp.section_of_line(st["section_ranges"].get(doc) or {},
                                       int(lineno))
            key = "%s::%s" % (doc, title)
            fr = st["section_freshness"].get(key)
            age = fresh.age_days(fr, (st["file_age_days"] or {}).get(doc), now)
            e["age_days"] = round(age, 1)
            e["age_label"] = fresh.label(age, st["stale_days"],
                                         observed=bool(fr and fr.get("observed")))
            e["stale"] = age >= st["stale_days"]
            e["section"] = title


def section_staleness(st, doc, needle):
    """특정 절(예: '다음 액션')이 며칠째 변경 없는가. 배너 경고용."""
    ranges = (st.get("section_ranges") or {}).get(doc) or {}
    for title in ranges:
        if needle in title:
            fr = (st.get("section_freshness") or {}).get("%s::%s" % (doc, title))
            age = fresh.age_days(fr, (st.get("file_age_days") or {}).get(doc),
                                 st.get("now_epoch"))
            return {"section": title, "age_days": round(age, 1),
                    "observed": bool(fr and fr.get("observed")),
                    "stale": age >= st.get("stale_days", fresh.DEFAULT_STALE_DAYS)}
    return None


def scan_artifacts(repo_root):
    """작업 산출물 상태 — '코드가 어디까지 되어 있나'를 문서 없이 확인한다."""
    out = {"package": None, "packages": [], "tests": None}
    dist_dir = os.path.join(repo_root, "src", "dist")
    if os.path.isdir(dist_dir):
        for fn in sorted(os.listdir(dist_dir)):
            if not fn.endswith(".tar.gz"):
                continue
            stat = os.stat(os.path.join(dist_dir, fn))
            out["packages"].append({"name": fn,
                                    "size_kb": round(stat.st_size / 1024.0, 1),
                                    "mtime_epoch": int(stat.st_mtime)})
        if out["packages"]:
            out["package"] = out["packages"][0]
    # 🔴 빌드 신선도 — tarball 이 소스보다 낡았는지. lead가 mtime을 우연히 봐서 잡은
    #    실패 모드를 매 세션 자동으로 드러낸다.
    try:
        sys.path.insert(0, os.path.join(repo_root, "src"))
        import build_stamp
        ok, problems = build_stamp.check(repo_root,
                                         os.path.join(repo_root, "src", "dist"))
        out["build_freshness"] = {"ok": ok, "problems": problems[:6]}
    except Exception as exc:
        out["build_freshness"] = {"ok": None,
                                  "problems": ["점검 불가: %s" % type(exc).__name__]}

    tests_dir = os.path.join(repo_root, "tests")
    if os.path.isdir(tests_dir):
        n_files, n_tests = 0, 0
        for fn in sorted(os.listdir(tests_dir)):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            n_files += 1
            try:
                with open(os.path.join(tests_dir, fn), errors="replace") as fh:
                    n_tests += sum(1 for ln in fh if ln.strip().startswith("def test_"))
            except OSError:
                pass
        out["tests"] = {"files": n_files, "test_functions": n_tests}
    return out


# --------------------------------------------------------------------------
def _open_ids(state):
    """아직 안 닫힌 U-NN 집합. 선행조건 판정에 쓴다."""
    return set(i["id"] for i in state["unresolved"]
               if i["id"] and i["status"] in ("open", "partial"))


def classify(state):
    """③ 사람이 답할 것 → ② 막힌 것 → ① 지금 할 수 있는 것 순으로 배타 분류.

    한 항목이 두 범주에 동시에 들어가지 않게 한다. 겹치면 "지금 할 수 있는 것"의
    신뢰도가 떨어지고, 그러면 이 도구를 안 보게 된다.
    """
    open_ids = _open_ids(state)
    ask_user, blocked, act_now = [], [], []

    # --- 문서 상단 하이라이트 ---------------------------------------------
    # 🔴 우선순위를 명시한다. 이 순서가 틀리면 "사람이 답할 것"에 teammate 대기 항목이
    #    섞여 들어가고([3]이 오염되면 이 도구를 안 보게 된다), 반대로 진짜 질문이 묻힌다.
    #      1) 이미 해소됨            → 아무 데도 안 넣는다
    #      2) 사람만 답할 수 있음     → ③ ask_user
    #      3) teammate 판정/회신 대기 → ② blocked
    #      4) 열린 질문(주인 불명)    → ③ ask_user (기본값을 사람으로 둔다: 방치 방지)
    for h in state["highlights"]:
        if h["resolved"]:
            continue
        entry = {"source": "05_STATE.md:%d" % h["line"], "ids": h["questions"],
                 "text": _trim(_dedup_id(h["text"], h["questions"])),
                 "urgent": h["urgent"]}
        waiting = any(w in h["text"] for w in dp.WAITING_WORDS)
        if h["needs_user"]:
            ask_user.append(entry)
        elif h["unresolved_tag"] and waiting:
            entry["blocked_by"] = ["teammate 판정"]
            blocked.append(entry)
        elif h["unresolved_tag"] and h["questions"]:
            ask_user.append(entry)

    # --- 미확정 U-NN
    for it in state["unresolved"]:
        if it["status"] == "closed":
            continue
        ref = "05_STATE.md:%d" % it["line"]
        unmet = [d for d in it["depends_on"] if d in open_ids and d != it["id"]]
        ids = [it["id"]] if it["id"] else []
        entry = {"source": ref, "ids": ids,
                 "text": _trim(_dedup_id(it["text"], ids)), "urgent": it["urgent"]}
        if it["needs_user"]:
            ask_user.append(entry)
        elif unmet:
            entry["blocked_by"] = unmet
            blocked.append(entry)
        elif it["waiting"]:
            entry["blocked_by"] = ["다른 teammate 회신"]
            blocked.append(entry)
        else:
            act_now.append(entry)

    # --- 다음 액션
    for na in state["next_actions"]:
        if na["status"] == "done" and not na.get("followup"):
            continue                       # 완료 항목은 [1]에 올리지 않는다
        # 완료 줄이면 후속 작업 부분만 남긴다
        txt = na["followup"] if (na["status"] == "done" and na.get("followup")) \
            else na["text"]
        # 본문이 이미 "[진행 중]"으로 시작하면 라벨과 중복되므로 벗긴다
        txt = re.sub(r"^\[[^\]]{1,10}\]\s*", "", txt)
        owner = na.get("owner")
        entry = {"source": "05_STATE.md:%d" % na["line"], "ids": [],
                 "text": _trim(txt), "urgent": na["urgent"],
                 "label": owner or ("진행 중" if na["status"] == "in_progress"
                                    else "예정"),
                 "followup_of_done": na["status"] == "done",
                 "owner": owner,
                 "order": 0 if na["status"] == "in_progress" else 1}
        if owner == "사용자":
            # 🔴 사람이 직접 해야 하는 액션은 [1]에 묻으면 안 된다. 임계 경로가 여기 있다.
            entry["label"] = "사용자 실행"
            ask_user.append(entry)
        else:
            act_now.append(entry)

    # --- 조건부(Proposed) ADR = 확정 아님 ⇒ 그 위에 쌓는 일은 막혀 있다
    for a in state["adrs"]:
        if a["proposed"] and not a["superseded"]:
            blocked.append({
                "source": "%s:%d" % (DOC_ADR, a["line"]),
                "ids": [a["id"]],
                "text": _trim("%s (Status: %s)" % (a["title"], a["status"])),
                "blocked_by": ["ADR 확정"],
                "urgent": False,
            })

    def _key(e):
        return (e.get("order", 1), 0 if e.get("urgent") else 1)
    act_now.sort(key=_key)
    blocked.sort(key=lambda e: 0 if e.get("urgent") else 1)
    ask_user.sort(key=lambda e: 0 if e.get("urgent") else 1)
    return {"ask_user": ask_user, "blocked": blocked, "act_now": act_now,
            "top_issues": top_issues(state)}


def top_issues(state, limit=2):
    """지금 프로젝트를 좌우하는 최상위 미해결 이슈 — 돌아온 사람이 먼저 볼 것."""
    out = []
    for h in state["highlights"]:
        if h["resolved"] or not h["urgent"]:
            continue
        out.append({"source": "05_STATE.md:%d" % h["line"], "ids": h["questions"],
                    "text": _trim(_dedup_id(h["text"], h["questions"]), 140)})
    return out[:limit]


def _dedup_id(text, ids):
    """본문이 이미 'U-05 ...' 로 시작하면 앞에 id를 또 붙이지 않는다."""
    t = text.strip()
    for i in ids or []:
        if i and t.startswith(i):
            return t[len(i):].lstrip(" :—-")
    return t


def _trim(text, n=150):
    text = text.strip()
    return text if len(text) <= n else text[:n - 1] + "…"


# --------------------------------------------------------------------------
def diff_state(prev, cur):
    """지난 세션 스냅샷 대비 변경분. 이것이 재오리엔테이션 세금의 본체다."""
    if not prev:
        return {"first_run": True, "changes": []}
    changes = []

    def index(state, key, idkey="id"):
        out = {}
        for x in state.get(key, []) or []:
            k = x.get(idkey)
            if k:
                out[k] = x
        return out

    # ADR: 신규 / 상태 변경
    p_adr, c_adr = index(prev, "adrs"), index(cur, "adrs")
    for k in sorted(set(c_adr) - set(p_adr)):
        changes.append({"kind": "adr_new", "id": k,
                        "text": "%s %s (%s)" % (k, c_adr[k]["title"],
                                                c_adr[k]["status"])})
    for k in sorted(set(c_adr) & set(p_adr)):
        if (p_adr[k].get("status") or "") != (c_adr[k].get("status") or ""):
            changes.append({"kind": "adr_status", "id": k,
                            "text": "%s: %s → %s" % (k, p_adr[k]["status"],
                                                     c_adr[k]["status"])})

    # 미확정 항목: 신규 / 상태 변경(특히 closed 로 바뀐 것)
    p_u, c_u = index(prev, "unresolved"), index(cur, "unresolved")
    for k in sorted(set(c_u) - set(p_u)):
        changes.append({"kind": "unresolved_new", "id": k,
                        "text": "%s 신규: %s" % (k, _trim(c_u[k]["text"], 90))})
    for k in sorted(set(c_u) & set(p_u)):
        if p_u[k]["status"] != c_u[k]["status"]:
            changes.append({"kind": "unresolved_status", "id": k,
                            "text": "%s: %s → %s" % (k, p_u[k]["status"],
                                                     c_u[k]["status"])})

    # 위험: 신규 / 해소
    p_r, c_r = index(prev, "risks"), index(cur, "risks")
    for k in sorted(set(c_r) - set(p_r)):
        changes.append({"kind": "risk_new", "id": k,
                        "text": "%s 신규: %s" % (k, _trim(c_r[k]["text"], 90))})
    for k in sorted(set(c_r) & set(p_r)):
        if p_r[k]["status"] != c_r[k]["status"]:
            changes.append({"kind": "risk_status", "id": k,
                            "text": "%s: %s → %s" % (k, p_r[k]["status"],
                                                     c_r[k]["status"])})

    # 진행 로그 신규 항목
    p_log = set((x["date"], x["event"]) for x in prev.get("progress", []) or [])
    for x in cur.get("progress", []) or []:
        if (x["date"], x["event"]) not in p_log:
            changes.append({"kind": "log", "id": None,
                            "text": "%s %s" % (x["date"], _trim(x["event"], 100))})

    # 문서 분량 변화 (누가 크게 고쳤는지)
    for name, n in sorted((cur.get("doc_sizes") or {}).items()):
        old = (prev.get("doc_sizes") or {}).get(name)
        if old is not None and abs(n - old) >= 20:
            changes.append({"kind": "doc_size", "id": name,
                            "text": "%s %+d줄 (%d → %d)" % (name, n - old, old, n)})
    return {"first_run": False, "changes": changes}
