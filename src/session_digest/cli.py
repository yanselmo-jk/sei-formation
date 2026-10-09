"""진입점.

    src/digest.sh                # 한 화면 다이제스트 + 스냅샷 갱신
    src/digest.sh --full         # 전체 (위험·게이트·구속조건·로그 포함)
    src/digest.sh --json         # 기계용
    src/digest.sh --no-save      # 스냅샷을 갱신하지 않고 보기만 (여러 번 봐도 diff 유지)
    src/digest.sh --check        # 파싱 건전성 점검 (CI/회귀용, 종료코드로 판정)
"""

import argparse
import json
import os
import sys

from . import digest as digest_mod
from . import render as render_mod
from . import snapshot as snap_mod

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def build_parser():
    p = argparse.ArgumentParser(prog="session_digest",
                                description="세션 상태 자동요약 (L3)")
    p.add_argument("--root", default=REPO_ROOT)
    p.add_argument("--docs", default=None, help="기본: <root>/docs")
    p.add_argument("--snap-dir", default=None)
    p.add_argument("--full", action="store_true")
    p.add_argument("--json", action="store_true")
    p.add_argument("--no-save", action="store_true",
                   help="스냅샷을 갱신하지 않는다(같은 변경분을 다시 보고 싶을 때)")
    p.add_argument("--check", action="store_true",
                   help="파싱 건전성만 점검하고 종료코드로 알린다")
    p.add_argument("--max-items", type=int, default=6)
    p.add_argument("--stale-days", type=int, default=7,
                   help="이 일수 이상 변경 없는 절의 항목에 ⏳ 표시 (기본 7)")
    return p


def sanity(state):
    """파싱이 무너졌는지 스스로 점검한다.

    문서는 다른 teammate가 계속 고치므로 **규약이 바뀌면 조용히 빈 다이제스트가
    나오는 것**이 이 도구의 가장 위험한 실패 모드다. 그것을 실패로 만든다.
    """
    problems = []
    if "05_STATE.md" not in (state.get("docs_present") or []):
        problems.append("05_STATE.md 를 찾지 못했다")
    if not state.get("adrs"):
        problems.append("ADR을 하나도 파싱하지 못했다 (01_DECISION_LOG.md 규약 변경?)")
    if not state.get("unresolved"):
        problems.append("미확정 항목을 하나도 파싱하지 못했다 (05_STATE.md '미확정' 섹션?)")
    if not (state.get("header") or {}).get("current_phase"):
        problems.append("Current phase 를 읽지 못했다")
    if not state.get("team"):
        problems.append("팀 상태 표를 읽지 못했다")
    b = state.get("buckets") or {}
    if not any(b.get(k) for k in ("act_now", "blocked", "ask_user")):
        problems.append("세 범주가 모두 비었다 — 분류가 무너졌다")
    return problems


def main(argv=None):
    args = build_parser().parse_args(argv)
    docs_dir = args.docs or os.path.join(args.root, "docs")
    prev = snap_mod.load(args.root, args.snap_dir)
    state = digest_mod.build(docs_dir, repo_root=args.root, prev_snapshot=prev,
                             stale_days=args.stale_days)

    if args.check:
        problems = sanity(state)
        if problems:
            sys.stderr.write("[digest] 파싱 건전성 실패:\n")
            for p in problems:
                sys.stderr.write("  - %s\n" % p)
            return 1
        print("[digest] OK — 미확정 %d, ADR %d, 액션 %d, 팀 %d"
              % (len(state["unresolved"]), len(state["adrs"]),
                 len(state["next_actions"]), len(state["team"])))
        return 0

    diff = digest_mod.diff_state(prev, state)

    if args.json:
        print(json.dumps({"state": state, "diff": diff},
                         ensure_ascii=False, indent=1, default=str))
    else:
        print(render_mod.render(state, diff, full=args.full,
                                max_items=args.max_items))

    if not args.no_save:
        snap_mod.save(args.root, state, args.snap_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
