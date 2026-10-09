"""L4 진입점.

    src/batch.sh show                     확정 왕복 구조와 RT-3 DAG를 본다
    src/batch.sh validate <items.json>    이 배치가 구조를 깨는지 판정 (종료코드로도)
    src/batch.sh drift                    config ↔ 문서(§R8.5) 어긋남 점검
    src/batch.sh validate ... --json      기계용

종료코드: 0 통과 / 1 error / 0(warn은 통과로 두되 화면에 남긴다)
"""

import argparse
import json
import os
import sys

from . import model as model_mod
from . import plan as plan_mod
from . import validate as V

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
W = 78


def build_parser():
    p = argparse.ArgumentParser(prog="batch_planner",
                                description="L4 배치 통합 계획기/검증기")
    p.add_argument("command", choices=["show", "validate", "drift"])
    p.add_argument("items", nargs="?", default=None, help="작업 항목 JSON")
    p.add_argument("--root", default=REPO_ROOT)
    p.add_argument("--config-dir", default=None)
    p.add_argument("--json", action="store_true")
    return p


def _rule(ch="="):
    return ch * W


def render_show(plan):
    L = [_rule(), " 확정 왕복 구조 (%d회) — %s" % (plan.target_roundtrips,
                                              plan.cfg.get("_source", "")), _rule()]
    for r in plan.roundtrips:
        flags = []
        if r.get("must_not_split"):
            flags.append("🔴 분할 금지")
        if r.get("cuttable") is True:
            flags.append("🟢 절단 가능")
        elif r.get("cuttable") == "partial":
            flags.append("🟡 축소 가능")
        L.append(" %-5s W%-3s %-28s %s" % (r["id"], r.get("week"), r.get("title", "")[:28],
                                           " ".join(flags)))
        L.append("        내용: %s" % ", ".join(r.get("contents") or [])[:66])
        L.append("        회신: %s" % (r.get("return_artifact") or "-")[:60])
    L.append("")
    L.append(" RT-3 내부 DAG (단일 제출, 사용자 개입 sbatch 1회)")
    for s in (plan.rt3_dag.get("stages") or []):
        dep = ", ".join(s.get("depends_on") or []) or "—"
        L.append("   %-14s %4.1f일  ←  %s" % (s["id"], s.get("days", 0), dep))
    L.append("   %-14s %4.1f일  (선언값 %.1f일)"
             % ("임계경로", plan.dag_critical_path_days(),
                plan.rt3_dag.get("total_days", 0)))
    L.append("")
    L.append(" 자료구조 규칙 (02_METHOD_SPEC §23.1 — 정확성 요구)")
    for f in (plan.rules.get("forbidden") or []):
        L.append("   ✗ %s" % f["rule"])
        L.append("     %s" % f["why"][:70])
    L.append(_rule("-"))
    return "\n".join(L)


def render_validate(plan, items, summary):
    L = [_rule(), " 배치 계획 검증 — 작업 %d건 / 왕복 %d회 (확정 구조 %d회)"
         % (summary["n_items"], summary["n_roundtrips_used"],
            summary["target_roundtrips"]), _rule()]
    L.append(" %-6s %-4s %-24s %6s %8s %6s" % ("RT", "주", "제목", "작업", "core-h", "회신점"))
    for e in summary["per_rt"]:
        L.append(" %-6s W%-3s %-24s %6d %8.0f %6d%s"
                 % (e["id"], e["week"], (e["title"] or "")[:24], e["n_items"],
                    e["core_hours"], e["return_points"],
                    "  🔴분할금지" if e["must_not_split"] else ""))
    L.append("")
    L.append(" 달력: 왕복 %d회 x %.1f일 = %.1f일%s"
             % (summary["n_roundtrips_used"], plan.roundtrip_days,
                summary["calendar_days_roundtrips"],
                ("  + 구조 위반 대가 %.1f주" % summary["calendar_penalty_weeks"])
                if summary["calendar_penalty_weeks"] else ""))
    L.append(" 총 core-h: %.0f" % summary["total_core_hours"])
    L.append("")

    findings = summary["findings"]
    if not findings:
        L.append(" ✅ 위반 없음 — 이 배치는 확정 왕복 구조를 유지한다.")
    for f in findings:
        icon = {"error": "🔴 ERROR", "warn": "🟡 WARN ", "info": "   INFO "}[f["severity"]]
        L.append(" %s [%s] %s" % (icon, f["rule"], f["message"]))
        if f["items"]:
            L.append("            항목: %s" % ", ".join(str(x) for x in f["items"])[:60])
        L.append("            근거: %s" % f["source"])
    L.append(_rule("-"))
    L.append(" 판정: %s" % {"error": "🔴 계획 불성립 — 위 ERROR를 고치기 전에 제출하지 마라",
                           "warn": "🟡 성립하나 대가가 있다",
                           "info": "🟢 통과"}[summary["verdict"]])
    L.append(_rule("-"))
    return "\n".join(L)


def render_drift(plan, drift):
    L = [_rule(), " config ↔ 문서(§R8.5) 드리프트 점검", _rule()]
    L.append(" config : %s" % plan.cfg.get("_source_path"))
    L.append(" 문서 행 : %d개 파싱" % len(drift["doc_rows"]))
    if drift["ok"]:
        L.append(" ✅ 일치 — config 가 문서를 정확히 반영한다.")
    else:
        for p in drift["problems"]:
            L.append(" 🔴 %s: %s" % (p["kind"], p["detail"]))
        L.append("")
        L.append(" ⚠ config 가 낡았을 가능성이 높다. 문서가 기준이다.")
    L.append(_rule("-"))
    return "\n".join(L)


def main(argv=None):
    args = build_parser().parse_args(argv)
    plan = model_mod.load_plan(args.config_dir)

    if args.command == "show":
        print(json.dumps(plan.cfg, ensure_ascii=False, indent=1) if args.json
              else render_show(plan))
        return 0

    if args.command == "drift":
        path = os.path.join(args.root, "docs", "03_COMPUTE_PLAN.md")
        try:
            with open(path, errors="replace") as fh:
                text = fh.read()
        except OSError:
            sys.stderr.write("문서를 읽지 못했다: %s\n" % path)
            return 1
        drift = plan_mod.check_drift(plan, text)
        print(json.dumps(drift, ensure_ascii=False, indent=1) if args.json
              else render_drift(plan, drift))
        return 0 if drift["ok"] else 1

    if not args.items:
        sys.stderr.write("validate 에는 작업 항목 JSON 경로가 필요하다\n")
        return 2
    try:
        items = model_mod.load_work_items(args.items)
    except (OSError, ValueError) as exc:
        sys.stderr.write("작업 항목을 읽지 못했다: %s\n" % exc)
        return 2
    summary = plan_mod.summarize(plan, items)
    print(json.dumps(summary, ensure_ascii=False, indent=1, default=str)
          if args.json else render_validate(plan, items, summary))
    return 1 if summary["verdict"] == V.ERROR else 0


if __name__ == "__main__":
    sys.exit(main())
