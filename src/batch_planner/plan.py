"""배치 요약·달력 산정 + 문서 드리프트 점검.

계획기의 산출은 두 가지다:
  1. **이 배치가 왕복 몇 회이고 달력 며칠인가** (숫자로)
  2. **구조를 깨는 항목은 무엇이고 그 대가는 얼마인가** (validate.py)

드리프트 점검: `config/rt_plan.json` 은 문서에서 옮겨 적은 데이터다.
문서(§R8.5 표)가 바뀌면 이 파일이 조용히 낡는다 — L3에서 배운 실패 모드와 같다.
그래서 문서를 다시 파싱해 **RT id 집합이 어긋나면 알린다.**
"""

import re

from . import validate as V


def summarize(plan, items):
    """RT별 집계 + 달력 추정."""
    used = [r for r in plan.roundtrips if any(i.rt == r["id"] for i in items)]
    per_rt = []
    for r in used:
        inside = [i for i in items if i.rt == r["id"]]
        per_rt.append({
            "id": r["id"], "week": r.get("week"), "title": r.get("title"),
            "n_items": len(inside),
            "core_hours": round(sum(i.core_hours for i in inside), 1),
            "max_wall_h": round(max([i.wall_h for i in inside] or [0.0]), 2),
            "return_points": sum(1 for i in inside if i.needs_return),
            "must_not_split": bool(r.get("must_not_split")),
            "cuttable": r.get("cuttable"),
        })
    findings = V.validate(plan, items)
    extra_rt = sum(max(0, e["return_points"] - 1) for e in per_rt)
    penalty_weeks = sum(f["calendar_cost_weeks"] or 0.0 for f in findings)
    return {
        "n_roundtrips_used": len(used),
        "target_roundtrips": plan.target_roundtrips,
        "per_rt": per_rt,
        "total_core_hours": round(sum(i.core_hours for i in items), 1),
        "n_items": len(items),
        "extra_return_points": extra_rt,
        "calendar_days_roundtrips": round(len(used) * plan.roundtrip_days, 1),
        "calendar_penalty_weeks": round(penalty_weeks, 2),
        "rt3_dag_critical_path_days": plan.dag_critical_path_days(),
        "rt3_dag_declared_days": (plan.rt3_dag or {}).get("total_days"),
        "findings": findings,
        "verdict": V.worst_severity(findings),
    }


# --------------------------------------------------------------------------
RE_RT_ROW = re.compile(r"^\|\s*(\d)\s*\|\s*W(\d+)\s*\|\s*(.+?)\s*\|")


def _strip_md(text):
    """표 셀의 굵게/코드 표기를 벗긴다. `| **7** | **W18** |` 도 읽어야 한다."""
    t = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    t = re.sub(r"`([^`]*)`", r"\1", t)
    return t


def parse_rt_table(compute_plan_text):
    """§R8.5 의 왕복 구조 표를 문서에서 다시 읽는다 (드리프트 점검용).

    표 형식: `| 1 | W2 | 파일럿 패키지 ... | ❌ |`
    """
    rows = []
    in_section = False
    for line in (compute_plan_text or "").splitlines():
        if line.startswith("### R8.5"):
            in_section = True
            continue
        if in_section and line.startswith("### ") and "R8.5" not in line:
            break
        if not in_section:
            continue
        m = RE_RT_ROW.match(_strip_md(line.strip()))
        if m:
            rows.append({"id": "RT-%s" % m.group(1), "week": int(m.group(2)),
                         "title": m.group(3).strip()})
    return rows


def check_drift(plan, compute_plan_text):
    """config 와 문서가 어긋났는지. 어긋나면 **config 가 낡은 것**으로 본다."""
    doc_rows = parse_rt_table(compute_plan_text)
    problems = []
    if not doc_rows:
        problems.append({"kind": "doc_table_not_found",
                         "detail": "§R8.5 왕복 구조 표를 문서에서 찾지 못했다 "
                                   "(문서 구조가 바뀌었을 수 있다)"})
        return {"ok": False, "problems": problems, "doc_rows": doc_rows}
    doc_ids = [r["id"] for r in doc_rows]
    cfg_ids = [r["id"] for r in plan.roundtrips]
    if doc_ids != cfg_ids:
        problems.append({"kind": "rt_set_mismatch",
                         "detail": "문서 %s vs config %s" % (doc_ids, cfg_ids)})
    doc_weeks = dict((r["id"], r["week"]) for r in doc_rows)
    for r in plan.roundtrips:
        if r["id"] in doc_weeks and r.get("week") != doc_weeks[r["id"]]:
            problems.append({"kind": "week_mismatch",
                             "detail": "%s: 문서 W%s vs config W%s"
                                       % (r["id"], doc_weeks[r["id"]], r.get("week"))})
    return {"ok": not problems, "problems": problems, "doc_rows": doc_rows}
