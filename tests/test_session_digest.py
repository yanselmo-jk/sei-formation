"""L3 세션 다이제스트 테스트.

🔴 ADR-004의 "실행 검증 불가" 제약이 **여기엔 적용되지 않는다** — 이 도구는 전부
로컬에서 돈다. 그래서 합성 문서 fixture로 분류 규칙을 못박고, **실제 docs/** 에도
돌려 파싱이 무너지지 않는지 본다.

이 도구의 가장 위험한 실패 모드는 "크래시"가 아니라 **조용히 빈 다이제스트**다
(문서 규약이 바뀌면 그렇게 된다). `sanity()` 가 그것을 실패로 만드는지도 검증한다.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import time
import unittest

import context  # noqa: F401

sys.path.insert(0, os.path.join(context.REPO_ROOT, "src"))

from session_digest import cli as cli_mod          # noqa: E402
from session_digest import digest as digest_mod    # noqa: E402
from session_digest import docparse as dp          # noqa: E402
from session_digest import freshness as fresh_mod  # noqa: E402
from session_digest import render as render_mod    # noqa: E402
from session_digest import snapshot as snap_mod    # noqa: E402

STATE_MD = """# Project State

**Last updated**: 2026-08-17 (Phase 1)
**Current phase**: Phase 1 — 방법론 확정 중.

> 🔴 **최우선 미해결 Q15 — PM7 5 ps 궤적으로 반응이 보이는가.** proposer 판정 중.
> `[UNRESOLVED]`

> ✅ **U-11 해소 (ADR-012).** AIMD는 검증 도구로 강등.

> 🔴 **Q20 — 주당 실투입 시간.** 사용자 확인 필요. `[UNRESOLVED]`

> ~~🟡 **R-22 — 옛 배너.** engineer 해법 대기~~ → 해소 (ADR-020)

> 🔴 **아직 안 끝난 것 — 해소되지 않았다.** `[UNRESOLVED]` 판정 중

## 확정된 것

- 아무거나

## 미확정 (`[UNRESOLVED]`)

- [x] ~~**U-01** 대상 조성~~ → ADR-001
- [~] **U-04** S2 엔진 → **ADR-006 Accepted**. 실행 방식은 c 실측 대기
- [ ] **U-06** MLIP 사용 여부 — U-05 확정 후
- [ ] **U-05** network 폭발 제어 — 지금 설계 가능
- [ ] 식별자가 없는 항목 하나

## 팀 상태

| teammate | 상태 | 현재 작업 |
|---|---|---|
| `proposer` | **RUNNING** | P0 실측 |
| `coder` | **RUNNING** | L3 구현 |

## 다음 액션

### 🔴 외부 대기
1. **RT-1 파일럿 실행** — 사용자. 임계 경로 맨 앞.

### 진행 중
2. ~~organizer: U-01 확인~~ 완료
3. **[진행 중]** proposer: U-05 정식 설계
4. coder: L4 착수
5. ✅ **engineer: RT-2 사양 완료** → ADR-028. 다음: (iii) 재견적
6. ✅ **critic: 1차 리뷰 완료** → BLOCKER 0건

## Stage gate 판정 기준

| Gate | 조건 | 상태 |
|---|---|---|
| S1→S2 | C1/C2/C3 | 미도달 |

## 알려진 미해결 위험

- **R-01** 표면 없음으로 self-limiting 부재. `[UNRESOLVED]`
- 🔴 **R-04** 단가 스프레드 8배.
- [x] ~~**R-07** 응축상~~ → 해소 (ADR-021)

## 진행 로그

| 날짜 | 이벤트 |
|---|---|
| 2026-08-16 | 팀 생성 |
| 2026-08-17 | ADR-012 확정 |
"""

ADR_MD = """# Decision Log (ADR)

## ADR-001: 조성 고정

- **Status**: Accepted
- **Date**: 2026-08-17
- **Stage**: Infra

## ADR-011: 실행 방식

- **Status**: Proposed — c 실측 대기
- **Date**: 2026-08-17
- **Stage**: S2

## ADR-002: 옛 결정

- **Status**: Superseded by ADR-011
- **Date**: 2026-08-16
- **Stage**: S1
"""


def write_docs(d, state=STATE_MD, adr=ADR_MD):
    docs = os.path.join(d, "docs")
    os.makedirs(docs, exist_ok=True)
    with open(os.path.join(docs, "05_STATE.md"), "w") as fh:
        fh.write(state)
    with open(os.path.join(docs, "01_DECISION_LOG.md"), "w") as fh:
        fh.write(adr)
    return docs


class TestParsers(unittest.TestCase):
    def test_header(self):
        h = dp.parse_header(STATE_MD)
        self.assertIn("2026-08-17", h["last_updated"])
        self.assertIn("Phase 1", h["current_phase"])

    def test_open_items_status_and_ids(self):
        items, unparsed = dp.parse_open_items(STATE_MD)
        by = dict((i["id"], i) for i in items if i["id"])
        self.assertEqual(by["U-01"]["status"], "closed")
        self.assertEqual(by["U-04"]["status"], "partial")
        self.assertEqual(by["U-06"]["status"], "open")
        self.assertEqual(unparsed, 1)          # 식별자 없는 항목을 삼키지 않는다

    def test_dependency_extraction(self):
        items, _ = dp.parse_open_items(STATE_MD)
        by = dict((i["id"], i) for i in items if i["id"])
        self.assertEqual(by["U-06"]["depends_on"], ["U-05"])
        self.assertEqual(by["U-05"]["depends_on"], [])

    def test_risks_open_vs_closed(self):
        risks = dp.parse_risks(STATE_MD)
        by = dict((r["id"], r) for r in risks)
        self.assertEqual(by["R-01"]["status"], "open")
        self.assertEqual(by["R-07"]["status"], "closed")
        self.assertTrue(by["R-04"]["urgent"])

    def test_team_and_actions(self):
        team = dp.parse_team(STATE_MD)
        self.assertEqual([t["name"] for t in team], ["proposer", "coder"])
        acts = dp.parse_next_actions(STATE_MD)
        self.assertEqual([a["status"] for a in acts],
                         ["todo", "done", "in_progress", "todo", "done", "done"])

    def test_action_owner_detection(self):
        acts = dict((a["n"], a) for a in dp.parse_next_actions(STATE_MD))
        self.assertEqual(acts[1]["owner"], "사용자")     # "— 사용자." + 외부 대기 소제목
        self.assertEqual(acts[3]["owner"], "proposer")
        self.assertEqual(acts[4]["owner"], "coder")

    def test_owner_patterns(self):
        self.assertEqual(dp.action_owner("RT-1 파일럿 실행 — 사용자."), "사용자")
        self.assertEqual(dp.action_owner("engineer: RT-2 프로브 사양"), "engineer")
        self.assertIsNone(dp.action_owner("아무 소유자 없는 액션"))
        # 소제목 문맥으로도 판정된다
        self.assertEqual(dp.action_owner("RT-1 실행", "🔴 외부 대기"), "사용자")

    def test_checkmark_prefixed_action_is_done(self):
        """🔴 lead 요청: ✅/완료 로 시작하는 줄은 [1]에 올리면 안 된다."""
        acts = dict((a["n"], a) for a in dp.parse_next_actions(STATE_MD))
        self.assertEqual(acts[5]["status"], "done")
        self.assertEqual(acts[6]["status"], "done")

    def test_followup_is_extracted_from_done_line(self):
        """'완료 → …. 다음: X' 형태에서 X만 뽑는다(실사용 서식)."""
        acts = dict((a["n"], a) for a in dp.parse_next_actions(STATE_MD))
        self.assertEqual(acts[5]["followup"], "(iii) 재견적")
        self.assertIsNone(acts[6]["followup"])       # 후속이 없으면 None

    def test_done_prefix_patterns(self):
        for txt in ("✅ 끝", "🟢 끝", "완료 — 무엇", "[완료] 무엇"):
            self.assertTrue(dp.RE_DONE_PREFIX.match(txt), txt)
        for txt in ("proposer: 진행", "🔴 급함", "U-05 설계"):
            self.assertIsNone(dp.RE_DONE_PREFIX.match(txt), txt)

    def test_resolved_banner_detection(self):
        """lead 요청 #3: 취소선/해소 블록은 [0]에서 빠져야 한다."""
        self.assertTrue(dp._is_resolved("~~🟡 R-22 옛 배너~~ → 해소"))
        self.assertTrue(dp._is_resolved("✅ 끝난 것"))
        self.assertTrue(dp._is_resolved("🟡 R-22 → 해소 (ADR-020)"))
        # 🔴 살아 있다고 선언한 블록은 '해소' 단어가 있어도 숨기지 않는다
        self.assertFalse(dp._is_resolved("🔴 해소되지 않았다. [UNRESOLVED] 판정 중"))
        self.assertFalse(dp._is_resolved("🔴 최우선 미해결 Q15"))

    def test_progress_and_gates(self):
        self.assertEqual(len(dp.parse_progress_log(STATE_MD)), 2)
        gates = dp.parse_gates(STATE_MD)
        self.assertEqual(gates[0]["state"], "미도달")

    def test_adr_status_classification(self):
        adrs = dp.parse_adrs(ADR_MD)
        by = dict((a["id"], a) for a in adrs)
        self.assertTrue(by["ADR-001"]["final"])
        self.assertTrue(by["ADR-011"]["proposed"])
        self.assertTrue(by["ADR-002"]["superseded"])

    def test_user_words_do_not_match_received_instructions(self):
        """🔴 '사용자 지시'는 이미 받은 지시다. 답변 대기로 오탐하면 [3]이 오염된다."""
        hl = dp._finish_highlight(["🔴 프로젝트 재스코핑 (사용자 지시 2026-08-17)"], 1)
        self.assertFalse(hl["needs_user"])
        hl2 = dp._finish_highlight(["🔴 주당 시간. 사용자 확인 필요. [UNRESOLVED]"], 1)
        self.assertTrue(hl2["needs_user"])

    def test_strip_md(self):
        self.assertEqual(dp.strip_md("**a** ~~b~~ `c`"), "a b c")


class TestClassification(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_dg_")
        self.docs = write_docs(self.d)
        self.state = digest_mod.build(self.docs, repo_root=self.d)
        self.b = self.state["buckets"]

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _texts(self, bucket):
        return " | ".join(e["text"] for e in self.b[bucket])

    def test_user_question_goes_to_ask_user(self):
        self.assertTrue(any("Q20" in (e["ids"] or []) for e in self.b["ask_user"]),
                        self._texts("ask_user"))

    def test_teammate_pending_goes_to_blocked_not_ask_user(self):
        """Q15는 proposer 판정 대기다 — 사람에게 물을 것이 아니다."""
        self.assertFalse(any("Q15" in (e["ids"] or []) for e in self.b["ask_user"]))
        self.assertTrue(any("Q15" in (e["ids"] or []) for e in self.b["blocked"]))

    def test_dependency_blocks_item(self):
        blocked_ids = [i for e in self.b["blocked"] for i in (e["ids"] or [])]
        self.assertIn("U-06", blocked_ids)
        entry = [e for e in self.b["blocked"] if "U-06" in (e["ids"] or [])][0]
        self.assertEqual(entry["blocked_by"], ["U-05"])

    def test_unblocked_item_is_actionable(self):
        act_ids = [i for e in self.b["act_now"] for i in (e["ids"] or [])]
        self.assertIn("U-05", act_ids)

    def test_closed_items_are_not_shown(self):
        all_ids = [i for k in ("act_now", "blocked", "ask_user")
                   for e in self.b[k] for i in (e["ids"] or [])]
        self.assertNotIn("U-01", all_ids)

    def test_proposed_adr_is_blocked(self):
        blocked_ids = [i for e in self.b["blocked"] for i in (e["ids"] or [])]
        self.assertIn("ADR-011", blocked_ids)
        self.assertNotIn("ADR-001", blocked_ids)      # Accepted 는 막힌 것이 아니다
        self.assertNotIn("ADR-002", blocked_ids)      # Superseded 도 아니다

    def test_buckets_are_mutually_exclusive(self):
        seen = {}
        for name in ("ask_user", "blocked", "act_now"):
            for e in self.b[name]:
                for i in (e["ids"] or []):
                    self.assertNotIn(i, seen,
                                     "%s 가 %s 와 %s 에 중복" % (i, seen.get(i), name))
                    seen[i] = name

    def test_user_owned_action_goes_to_ask_user_not_act_now(self):
        """🔴 임계 경로에 있는 '사용자 실행' 항목이 [1]에 묻히면 안 된다."""
        texts = " | ".join(e["text"] for e in self.b["ask_user"])
        self.assertIn("RT-1", texts)
        self.assertNotIn("RT-1", " | ".join(e["text"] for e in self.b["act_now"]))
        entry = [e for e in self.b["ask_user"] if "RT-1" in e["text"]][0]
        self.assertEqual(entry["label"], "사용자 실행")

    def test_completed_actions_are_not_in_act_now(self):
        texts = " | ".join(e["text"] for e in self.b["act_now"])
        self.assertNotIn("critic: 1차 리뷰 완료", texts)
        self.assertNotIn("RT-2 사양 완료", texts)

    def test_followup_of_done_action_survives_as_actionable(self):
        """완료 줄에 붙은 후속 작업은 살려서 [1]에 남긴다."""
        entry = [e for e in self.b["act_now"] if "재견적" in e["text"]]
        self.assertEqual(len(entry), 1, [e["text"] for e in self.b["act_now"]])
        self.assertTrue(entry[0]["followup_of_done"])
        self.assertEqual(entry[0]["owner"], "engineer")

    def test_teammate_owned_actions_carry_owner_label(self):
        labels = dict((e["text"][:12], e.get("label")) for e in self.b["act_now"])
        self.assertIn("proposer", labels.values())

    def test_resolved_banner_excluded_from_top_issues(self):
        texts = " | ".join(t["text"] for t in self.b["top_issues"])
        self.assertNotIn("옛 배너", texts)
        self.assertIn("Q15", texts + " " + " ".join(
            i for t in self.b["top_issues"] for i in (t["ids"] or [])))

    def test_in_progress_action_sorts_first(self):
        ordered = [e for e in self.b["act_now"] if "order" in e]
        self.assertEqual(ordered[0]["order"], 0)              # 진행 중이 먼저
        self.assertEqual(ordered[0]["owner"], "proposer")

    def test_id_is_not_duplicated_in_text(self):
        for name in ("ask_user", "blocked", "act_now"):
            for e in self.b[name]:
                for i in (e["ids"] or []):
                    self.assertFalse(e["text"].startswith(i),
                                     "%s 가 본문 앞에 중복: %s" % (i, e["text"][:40]))

    def test_artifacts_scan(self):
        art = self.state["artifacts"]
        self.assertIn("tests", art)
        self.assertIn("packages", art)

    def test_build_freshness_is_surfaced(self):
        """🔴 lead: tarball 이 소스보다 낡은 것을 우연히 mtime을 봐서 잡았다.
        매 세션 자동으로 드러나야 한다."""
        st = digest_mod.build(self.docs, repo_root=context.REPO_ROOT)
        info = (st["artifacts"] or {}).get("build_freshness")
        self.assertIsNotNone(info)
        self.assertIn("ok", info)

    def test_stale_build_appears_in_render(self):
        st = digest_mod.build(self.docs, repo_root=self.d)
        st["artifacts"]["packages"] = [{"name": "x.tar.gz", "size_kb": 1.0,
                                        "mtime_epoch": 0}]
        st["artifacts"]["build_freshness"] = {"ok": False, "problems": ["낡음"]}
        text = render_mod.render(st, {"first_run": True, "changes": []})
        self.assertIn("tarball 이 소스보다 낡았다", text)


class TestDiff(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_dgd_")
        self.docs = write_docs(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_first_run_then_no_change(self):
        s1 = digest_mod.build(self.docs, repo_root=self.d)
        self.assertTrue(digest_mod.diff_state(None, s1)["first_run"])
        snap_mod.save(self.d, s1)
        prev = snap_mod.load(self.d)
        s2 = digest_mod.build(self.docs, repo_root=self.d)
        d = digest_mod.diff_state(prev, s2)
        self.assertFalse(d["first_run"])
        self.assertEqual(d["changes"], [])

    def test_detects_adr_status_change_and_new_items(self):
        s1 = digest_mod.build(self.docs, repo_root=self.d)
        snap_mod.save(self.d, s1)
        new_adr = ADR_MD.replace("- **Status**: Proposed — c 실측 대기",
                                 "- **Status**: Accepted")
        new_adr += "\n## ADR-030: 새 결정\n\n- **Status**: Accepted\n"
        new_state = STATE_MD.replace("- [ ] **U-05** network 폭발 제어 — 지금 설계 가능",
                                     "- [x] ~~**U-05** network 폭발 제어~~ → ADR-030")
        new_state = new_state.replace("| 2026-08-17 | ADR-012 확정 |",
                                      "| 2026-08-17 | ADR-012 확정 |\n| 2026-08-18 | ADR-030 확정 |")
        write_docs(self.d, state=new_state, adr=new_adr)
        s2 = digest_mod.build(self.docs, repo_root=self.d)
        kinds = digest_mod.diff_state(snap_mod.load(self.d), s2)["changes"]
        texts = " | ".join(c["text"] for c in kinds)
        self.assertIn("ADR-030", texts)
        self.assertIn("ADR-011", texts)               # 상태 변경
        self.assertTrue(any(c["kind"] == "unresolved_status" for c in kinds), texts)
        self.assertTrue(any(c["kind"] == "log" for c in kinds), texts)

    def test_snapshot_roundtrip_is_json(self):
        s1 = digest_mod.build(self.docs, repo_root=self.d)
        p = snap_mod.save(self.d, s1)
        with open(p) as fh:
            loaded = json.load(fh)
        self.assertIn("adrs", loaded)
        self.assertIn("_saved_at", loaded)

    def test_snapshot_does_not_touch_docs(self):
        """🔴 docs/ 는 다른 teammate 소유다. 절대 쓰지 않는다."""
        before = dict((fn, os.stat(os.path.join(self.docs, fn)).st_mtime)
                      for fn in os.listdir(self.docs))
        s1 = digest_mod.build(self.docs, repo_root=self.d)
        snap_mod.save(self.d, s1)
        after = dict((fn, os.stat(os.path.join(self.docs, fn)).st_mtime)
                     for fn in os.listdir(self.docs))
        self.assertEqual(before, after)
        self.assertTrue(os.path.isdir(os.path.join(self.d, ".session_state")))


class TestRenderAndCli(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_dgr_")
        self.docs = write_docs(self.d)
        self.state = digest_mod.build(self.docs, repo_root=self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_render_has_all_four_sections(self):
        text = render_mod.render(self.state, {"first_run": True, "changes": []})
        for needle in ("여기서부터 시작", "[4] 지난 세션 이후",
                       "[3] 🔴 내가 답하거나 해야 하는 것",
                       "[1] 지금 당장 할 수 있는 것", "[2] 막혀 있는 것"):
            self.assertIn(needle, text)

    def test_render_is_short_by_default(self):
        """길면 안 읽는다. 기본 출력은 한 화면 안이어야 한다."""
        text = render_mod.render(self.state, {"first_run": True, "changes": []})
        self.assertLess(len(text.splitlines()), 70)

    def test_render_length_is_bounded_regardless_of_doc_size(self):
        """🔴 문서가 10배 커져도 기본 출력은 커지면 안 된다(max_items 상한이 작동).

        이것이 깨지면 문서가 자랄수록 다이제스트가 길어지고, 결국 안 읽게 된다.
        """
        big = STATE_MD
        extra = "\n".join("- [ ] **U-%d** 가짜 미확정 항목 %d" % (50 + i, i)
                           for i in range(40))
        big = big.replace("- [ ] 식별자가 없는 항목 하나",
                          "- [ ] 식별자가 없는 항목 하나\n" + extra)
        big += "\n" + "\n".join(
            "> 🔴 **가짜 이슈 %d.** `[UNRESOLVED]` Q%d" % (i, 100 + i)
            for i in range(20))
        write_docs(self.d, state=big)
        st = digest_mod.build(self.docs, repo_root=self.d)
        self.assertGreater(len(st["unresolved"]), 40)      # 실제로 커졌다
        text = render_mod.render(st, {"first_run": True, "changes": []})
        self.assertLess(len(text.splitlines()), 80, text[:500])

    def test_render_length_is_bounded_even_when_the_team_roster_grows(self):
        """🔴 [R-10] 이 절만 max_items 상한이 없었다 -- 세션이 길어질수록(팀원이 쌓일수록)
        렌더 길이가 문서 분량에 비례해 자라는 것이 정확히 이 도구의 실패 모드였다. 실제
        05_STATE.md가 15명(팀원 롤 교체 누적)까지 자라 97줄을 냈던 것을 여기서 합성으로
        고정한다 -- 문서가 다시 자라도 이 테스트가 먼저 잡는다.
        """
        extra_rows = "\n".join(
            "| `role%02d` | stopped | 종료됨, 사유 %d 텍스트가 꽤 길게 이어지는 경우도 "
            "있다 실제 로그처럼" % (i, i)
            for i in range(20))
        big = STATE_MD.replace(
            "| `coder` | **RUNNING** | L3 구현 |",
            "| `coder` | **RUNNING** | L3 구현 |\n" + extra_rows)
        write_docs(self.d, state=big)
        st = digest_mod.build(self.docs, repo_root=self.d)
        self.assertGreater(len(st["team"]), 20)   # 실제로 커졌다
        text = render_mod.render(st, {"first_run": True, "changes": []})
        self.assertLess(len(text.splitlines()), 80, text[:800])
        # 활동 중인 팀원(stopped 아님)은 상한 없이 항상 보인다
        self.assertIn("coder", text)
        self.assertIn("proposer", text)
        self.assertIn("--full", text)   # 잘렸다는 사실 자체는 숨기지 않는다

    def test_full_mode_adds_detail(self):
        short = render_mod.render(self.state, {"first_run": True, "changes": []})
        full = render_mod.render(self.state, {"first_run": True, "changes": []},
                                 full=True)
        self.assertGreater(len(full.splitlines()), len(short.splitlines()))
        self.assertIn("미해결 위험", full)

    def test_sanity_passes_on_good_docs(self):
        self.assertEqual(cli_mod.sanity(self.state), [])

    def test_sanity_fails_when_convention_breaks(self):
        """🔴 문서 규약이 바뀌어 파싱이 무너지면 **조용히 빈 다이제스트**가 아니라
        실패로 드러나야 한다. 이것이 이 도구의 가장 위험한 실패 모드다."""
        broken = STATE_MD.replace("## 미확정 (`[UNRESOLVED]`)", "## 열린 항목들")
        write_docs(self.d, state=broken)
        st = digest_mod.build(self.docs, repo_root=self.d)
        problems = cli_mod.sanity(st)
        self.assertTrue(problems)
        self.assertTrue(any("미확정" in p for p in problems))

    @staticmethod
    def _run_cli(argv):
        """CLI 출력이 테스트 로그를 덮지 않게 삼킨다."""
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = cli_mod.main(argv)
        return rc, buf.getvalue()

    def test_cli_check_returns_nonzero_on_broken_docs(self):
        write_docs(self.d, adr="# 결정 기록\n(형식 없음)\n")
        rc, out = self._run_cli(["--root", self.d, "--docs", self.docs, "--check"])
        self.assertEqual(rc, 1)
        self.assertIn("ADR", out)

    def test_cli_json_mode(self):
        rc, out = self._run_cli(["--root", self.d, "--docs", self.docs, "--json",
                                 "--no-save"])
        self.assertEqual(rc, 0)
        self.assertIn("buckets", json.loads(out)["state"])

    def test_no_save_keeps_previous_snapshot(self):
        self._run_cli(["--root", self.d, "--docs", self.docs])
        before = os.stat(snap_mod.path_for(self.d)).st_mtime_ns
        self._run_cli(["--root", self.d, "--docs", self.docs, "--no-save"])
        self.assertEqual(os.stat(snap_mod.path_for(self.d)).st_mtime_ns, before)


class TestFreshness(unittest.TestCase):
    """🔴 lead 요청 #1: 낡은 항목을 최신인 척 보여주는 것이 유일한 실패 모드다."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_dgf_")
        self.docs = write_docs(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _old_snapshot(self, days):
        st0 = digest_mod.build(self.docs, repo_root=self.d)
        old = int(time.time() - days * 86400)
        return {"section_freshness": dict(
            (k, {"hash": v["hash"], "first_seen_epoch": old,
                 "last_changed_epoch": old, "observed": True})
            for k, v in st0["section_freshness"].items())}

    def test_fresh_docs_show_no_age_label(self):
        st = digest_mod.build(self.docs, repo_root=self.d)
        for e in st["buckets"]["act_now"]:
            self.assertIsNone(e.get("age_label"), e["text"])

    def test_stale_section_marks_every_item(self):
        st = digest_mod.build(self.docs, repo_root=self.d,
                              prev_snapshot=self._old_snapshot(9))
        for e in st["buckets"]["act_now"]:
            self.assertTrue(e["stale"], e["text"])
            self.assertIn("9일", e["age_label"])
            self.assertIn("⏳", e["age_label"])

    def test_stale_banner_appears_in_render(self):
        st = digest_mod.build(self.docs, repo_root=self.d,
                              prev_snapshot=self._old_snapshot(9))
        text = render_mod.render(st, {"first_run": False, "changes": []})
        self.assertIn("「다음 액션」", text)
        self.assertIn("변경 없음", text)

    def test_no_banner_when_fresh(self):
        st = digest_mod.build(self.docs, repo_root=self.d,
                              prev_snapshot=self._old_snapshot(1))
        text = render_mod.render(st, {"first_run": False, "changes": []})
        self.assertNotIn("「다음 액션」", text)

    def test_age_is_a_lower_bound_when_unobserved(self):
        """관측 이력이 없으면 '≥N일'로 쓴다 — 아는 것보다 더 아는 척하지 않는다."""
        self.assertIsNone(fresh_mod.label(0.5))
        self.assertEqual(fresh_mod.label(3, observed=False), "≥3일 경과")
        self.assertEqual(fresh_mod.label(3, observed=True), "3일 경과")
        self.assertIn("⏳", fresh_mod.label(10, observed=True))

    def test_file_mtime_gives_age_floor_without_history(self):
        """이력이 없어도 파일 mtime 만으로 하한을 안다."""
        old = time.time() - 12 * 86400
        for fn in os.listdir(self.docs):
            os.utime(os.path.join(self.docs, fn), (old, old))
        st = digest_mod.build(self.docs, repo_root=self.d)
        self.assertGreaterEqual(st["file_age_days"]["05_STATE.md"], 11.9)
        self.assertTrue(all(e["stale"] for e in st["buckets"]["act_now"]))

    def test_changed_section_resets_the_clock(self):
        prev = self._old_snapshot(9)
        changed = STATE_MD.replace("4. coder: L4 착수", "4. coder: L5 착수")
        write_docs(self.d, state=changed)
        st = digest_mod.build(self.docs, repo_root=self.d, prev_snapshot=prev)
        info = digest_mod.section_staleness(st, "05_STATE.md", "다음 액션")
        self.assertFalse(info["stale"])

    def test_snapshot_carries_freshness_history(self):
        st = digest_mod.build(self.docs, repo_root=self.d,
                              prev_snapshot=self._old_snapshot(5))
        snap_mod.save(self.d, st)
        loaded = snap_mod.load(self.d)
        self.assertIn("section_freshness", loaded)
        st2 = digest_mod.build(self.docs, repo_root=self.d, prev_snapshot=loaded)
        info = digest_mod.section_staleness(st2, "05_STATE.md", "다음 액션")
        self.assertGreaterEqual(info["age_days"], 4.9)   # 이력이 이어졌다


class TestCountConsistency(unittest.TestCase):
    """lead 요청 #2: 같은 것을 세는데 숫자가 다르면 둘 다 못 믿게 된다."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_dgc_")
        self.docs = write_docs(self.d)
        self.state = digest_mod.build(self.docs, repo_root=self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_header_and_footer_agree(self):
        text = render_mod.render(self.state, {"first_run": True, "changes": []})
        head = [l for l in text.splitlines() if "미해결 위험 :" in l][0]
        foot = [l for l in text.splitlines() if l.startswith(" 파싱:")][0]
        n_open = sum(1 for r in self.state["risks"] if r["status"] == "open")
        n_all = len(self.state["risks"])
        self.assertIn("%d건" % n_open, head)
        self.assertIn("위험 %d(미해결 %d)" % (n_all, n_open), foot)

    def test_footer_labels_are_explicit(self):
        text = render_mod.render(self.state, {"first_run": True, "changes": []})
        foot = [l for l in text.splitlines() if l.startswith(" 파싱:")][0]
        self.assertIn("열림", foot)
        self.assertIn("미해결", foot)


class TestRiskIdsParseInEveryDocumentedEmphasisForm(unittest.TestCase):
    """🔴 [critic10] The id pattern was bold-only, so the CLOSED entries -- written exactly per
    05_STATE.md's own `- [x] ~~R-NN~~` convention -- were dropped ENTIRELY, not miscounted.
    `parse_risks` never saw them, and the risk count silently fell below the floor this file
    asserts.

    🔒 The document was patched to satisfy the parser (bold required INSIDE the strikethrough)
    with the constraint written down in prose. That works, and it is a footgun: a rule that
    lives only in a comment is enforced by whoever remembers to read it. These tests fix the
    parser's side so the rule does not have to be remembered.
    """

    DOC = ("## 알려진 미해결 위험\n"
           "- [ ] **R-1** open, bold\n"
           "- [x] ~~R-2~~ closed, PLAIN strikethrough (the documented convention)\n"
           "- [x] ~~**R-3**~~ closed, bold inside strikethrough (the workaround form)\n")

    def test_all_three_forms_are_seen(self):
        got = [(r["id"], r["status"]) for r in dp.parse_risks(self.DOC)]
        self.assertEqual([("R-1", "open"), ("R-2", "closed"), ("R-3", "closed")], got)

    def test_closed_entries_are_not_silently_dropped(self):
        """The failure mode was DROPPING, not mislabelling -- which is worse, because a
        dropped entry cannot be spotted by reading the parsed output."""
        self.assertEqual(3, len(dp.parse_risks(self.DOC)))

    def test_the_real_state_doc_still_parses_every_risk(self):
        real = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "docs", "05_STATE.md")
        with open(real, errors="replace") as fh:
            risks = dp.parse_risks(fh.read())
        self.assertGreaterEqual(len(risks), 5)
        self.assertTrue(any(r["status"] == "closed" for r in risks),
                        "closed risks must be visible, not invisible")


class TestAgainstRealDocs(unittest.TestCase):
    """실제 docs/ 로 돌린다. 내용이 아니라 **구조**만 검증해 문서 편집에 견디게 한다."""

    def setUp(self):
        self.docs = os.path.join(context.REPO_ROOT, "docs")
        if not os.path.isdir(self.docs):
            self.skipTest("docs/ 없음")
        self.state = digest_mod.build(self.docs, repo_root=context.REPO_ROOT)

    def test_real_docs_parse_sanely(self):
        self.assertEqual(cli_mod.sanity(self.state), [])

    def test_real_docs_have_adrs_and_items(self):
        self.assertGreaterEqual(len(self.state["adrs"]), 10)
        self.assertGreaterEqual(len(self.state["unresolved"]), 5)
        self.assertGreaterEqual(len(self.state["risks"]), 5)

    def test_real_render_does_not_crash_and_stays_short(self):
        text = render_mod.render(self.state, {"first_run": True, "changes": []})
        self.assertLess(len(text.splitlines()), 80)
        self.assertIn("여기서부터 시작", text)

    def test_real_docs_buckets_are_exclusive(self):
        b = self.state["buckets"]
        seen = {}
        for name in ("ask_user", "blocked", "act_now"):
            for e in b[name]:
                for i in (e["ids"] or []):
                    self.assertNotIn(i, seen, "%s 중복: %s vs %s"
                                     % (i, seen.get(i), name))
                    seen[i] = name

    def test_reading_docs_is_read_only(self):
        before = sorted((fn, os.stat(os.path.join(self.docs, fn)).st_mtime)
                        for fn in os.listdir(self.docs))
        digest_mod.build(self.docs, repo_root=context.REPO_ROOT)
        after = sorted((fn, os.stat(os.path.join(self.docs, fn)).st_mtime)
                       for fn in os.listdir(self.docs))
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
