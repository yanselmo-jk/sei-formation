"""🔴 B-1 회귀 테스트 — G16 route echo 70-column 절단 결함.

배경 (`HANDOFF_CODER6.md` §B-1, `docs/05_STATE.md` §0-k): RT-1이 저장한 route 세 줄이
전부 정확히 70자에서 잘렸고, 아무 표시도 없었다.

    ts_qst2.log       len=70   '...opt=(qst2,calcfc,noeigen'      괄호 불균형
    irc_forward.log   len=70   '...irc=(calcfc,forward,maxp'      괄호 불균형
    irc_reverse.log   len=70   '...irc=(calcfc,reverse,maxp'      괄호 불균형

결정적 증거: 그 ts 로그에서 `n_frequencies=27` / `imag_freq_cm=-105.0` 이 파싱됐는데
정작 저장된 route 문자열에는 `"freq"` 가 없다 — **회신이 스스로를 반박한다.**

이 파일이 지키는 것 (전부 `criteria/g16.py` / `criteria/p5.py`):
    parse_route_echo()                  로그 전체에서 route 를 재조립하고 완결성을 회신
    route_record_from_stored_string()   이미 저장된(구형) bare route 문자열을 분류
    keyword_in_route() / require_keyword_known_absent()
    RouteTruncatedError                 애매하면 조용히 False 를 돌려주지 않고 RAISE

🔒 **회귀 절차 (coder6 §0.4)**: 아래 `_OldParseRouteBehaviourTests` 가 수정 전 코드에서
실제로 깨지는지 이 세션에서 직접 확인했다 — pristine `criteria/g16.py` 를
`src/dist/sei_pilot_cpu.tar.gz` (동결 지점, source_digest 4a484eb71ef2b36d) 에서 추출해
`old_parse_route()` 로 박아 넣었고, 그 함수는 두 번째 물리 줄(줄바꿈 이후)을 버린다 —
바로 이 결함이다. sha256 (한 번, 귀속성 확보용):
    g16.py  dbef356b90523ba12077ce917d488d35fd9677afdea9557cce8cfd92eeee2d62
    p5.py   e26508cc7815bacd288a05de5d99ac4a30306b1f823c2e9de89cb8c84c4df6f6
`old_parse_route` 아래는 그 파일에서 그대로 옮겨온 것이며(패치 삭제분과 바이트 동일,
`src/salvage/coder7_B1_g16.py.patch` 대조), 매 실행마다 tarball 을 다시 열 필요가 없도록
소스를 문자열로 얼려 두었다 — tarball 은 재빌드되면 이제 새 코드를 담으므로 더 이상
"pre-fix" 표본이 아니다.
"""

import json
import os
import re
import unittest

import context  # noqa: F401
from sei_pilot.criteria import g16, p5


# --- pristine (pre-B-1) parse_route, frozen verbatim from the tarball extract ---
# (src/salvage/coder7_B1_g16.py.patch's '-' lines; sha256 above)
_OLD_RE_ROUTE = re.compile(r"^\s*#[pPnNtT]?\s+(.*)$")


def old_parse_route(text):
    """에코된 route line. 실제로 무엇을 계산했는지의 정본."""
    for line in (text or "").splitlines():
        m = _OLD_RE_ROUTE.match(line)
        if m and len(m.group(1)) > 3:
            return ("#" + line.strip().lstrip("#")).strip()
    return None


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# G16 wraps the echoed route at a column; continuation lines carry no leading
# '#' and are followed by a dashed rule that closes the block. Modelled on the
# real fixture format used throughout test_g16_adapter.py (LOG_OK).
WRAPPED_LOG = """ Entering Gaussian System, Link 0=g16
 -------------------------------------
 #p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen
 test,maxcycles=100) freq
 -------------------------------------
 Charge =  0 Multiplicity = 2
"""

# The route line is followed IMMEDIATELY by the closing dash-rule, but the
# line itself is cut mid-token -- i.e. the LOG FILE was truncated (not just
# wrapped), a distinct and equally real failure mode (mid-write kill, partial
# copy). parse_route_echo must not confuse "block closed" with "complete".
TRUNCATED_FILE_LOG = """ Entering Gaussian System, Link 0=g16
 -------------------------------------
 #p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen
 -------------------------------------
"""

NO_TERMINATOR_LOG = " -------------------------------------\n #p wB97XD/gen sp\n" + \
    "\n".join(" continuation line %d" % i for i in range(1, 12))

NO_ROUTE_LOG = " Entering Gaussian System, Link 0=g16\n Charge =  0 Multiplicity = 2\n"


class TestOldParseRouteHadTheDefect(unittest.TestCase):
    """Proves the pre-fix function silently drops the continuation line.

    This is not testing current code; it pins the DEFECT so nobody mistakes
    "parse_route_echo exists" for "we know why it was needed".
    """

    def test_old_parse_route_drops_the_wrapped_continuation(self):
        old = old_parse_route(WRAPPED_LOG)
        self.assertNotIn("freq", old)
        self.assertNotIn("maxcycles", old)
        self.assertTrue(old.endswith("noeigen"))

    def test_old_parse_route_carries_no_completeness_marker(self):
        """The historic bug wasn't the cut alone -- it's that nothing said so."""
        old = old_parse_route(WRAPPED_LOG)
        self.assertIsInstance(old, str)  # a bare string: no way to ask "is this all of it?"

    def test_new_parser_recovers_what_the_old_one_lost(self):
        new = g16.parse_route_echo(WRAPPED_LOG)
        self.assertTrue(new["route_echoed_is_complete"])
        self.assertIn("freq", new["route_echoed"])
        self.assertIn("noeigentest,maxcycles=100", new["route_echoed"])


class TestParseRouteEcho(unittest.TestCase):
    def test_reassembles_a_wrapped_route_and_marks_it_complete(self):
        rec = g16.parse_route_echo(WRAPPED_LOG)
        self.assertEqual(
            rec["route_echoed"],
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) "
            "opt=(qst2,calcfc,noeigentest,maxcycles=100) freq")
        self.assertTrue(rec["route_echoed_is_complete"])
        self.assertTrue(rec["route_echo_parentheses_balanced"])
        self.assertTrue(rec["route_echo_terminated_by_block_rule"])
        self.assertFalse(rec["absence_of_a_keyword_may_not_be_read_from_this_route"])

    def test_a_truncated_log_file_is_marked_incomplete_despite_block_closure(self):
        """Block-closed is necessary but not sufficient -- parens must balance too."""
        rec = g16.parse_route_echo(TRUNCATED_FILE_LOG)
        self.assertTrue(rec["route_echo_terminated_by_block_rule"])
        self.assertFalse(rec["route_echo_parentheses_balanced"])
        self.assertFalse(rec["route_echoed_is_complete"])
        self.assertTrue(rec["absence_of_a_keyword_may_not_be_read_from_this_route"])

    def test_no_closing_delimiter_within_the_line_cap_is_incomplete(self):
        rec = g16.parse_route_echo(NO_TERMINATOR_LOG)
        self.assertFalse(rec["route_echoed_is_complete"])
        self.assertIn("not closed", rec["route_echo_completeness_evidence"])

    def test_no_route_at_all_is_none_not_false(self):
        """None means NOT CHECKED (no route line found); False means checked-negative."""
        rec = g16.parse_route_echo(NO_ROUTE_LOG)
        self.assertIsNone(rec["route_echoed"])
        self.assertIsNone(rec["route_echoed_is_complete"])
        self.assertTrue(rec["absence_of_a_keyword_may_not_be_read_from_this_route"])

    def test_summarize_emits_route_echoed_and_not_the_bare_route_key(self):
        s = g16.summarize(WRAPPED_LOG)
        self.assertIn("route_echoed", s)
        self.assertIn("route_echoed_is_complete", s)
        self.assertNotIn("route", s)


class TestRouteRecordFromStoredString(unittest.TestCase):
    """Classifies a route already stored (bare string) by an RT-1-era report.

    🔒 `route_echoed_is_complete` must NEVER be True here -- a bare string has
    no block context, so completeness can be REFUTED but never ESTABLISHED.
    """

    # 🔒 [R-13, lead 판정] 테스트는 사용자 소유 결과 트리(cpu_machine_pilot_results/)를
    # 읽지 않는다 — fixture 는 tests/ 안에 산다. 사용자가 트리를 재구성하자 4개가
    # 빨개진 것이 이 규칙의 이유 전부다.
    #
    # 아래 세 문자열은 RT-1 회신이 실제로 저장했던 70자 절단 route 다. 원본 아티팩트
    # (구 cpu_machine_pilot_results/sei_probe_report.cpu.json)는 트리 재구성으로 디스크에
    # 더 이상 없다. ⚠ 증거 고리가 약해졌다: 원본 파일과의 대조는 이제 불가능하고, 이
    # 문자열들의 정당성은 (i) 아래 reconstruction 테스트 — pre-B-2 템플릿을 70자에서
    # 자르면 byte-for-byte 로 이 세 줄이 나온다 — 와 (ii) HANDOFF_CODER6 §B-1 의 기록에
    # 있다. 원본이 사라진 시점에 그 고리는 이미 끊겨 있었다; freeze 는 그 사실을 명시할
    # 뿐이다. 더 강한 **현재** 사실(새 회신의 route 는 완전하고 evidence 를 갖는다)은
    # 아래 TestCurrentReplyRoutesAreComplete 가 별도 fixture 로 고정한다.
    _FROZEN_RT1_STORED_ROUTES = {
        "ts_qst2.log":
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen",
        "irc_forward.log":
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) irc=(calcfc,forward,maxp",
        "irc_reverse.log":
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) irc=(calcfc,reverse,maxp",
    }

    def _real_rt1_routes(self):
        return dict(self._FROZEN_RT1_STORED_ROUTES)

    def test_the_three_real_stored_rt1_routes_are_refuted_not_confirmed(self):
        routes = self._real_rt1_routes()
        self.assertEqual(3, len(routes))
        for name, text in routes.items():
            with self.subTest(log=name):
                self.assertEqual(70, len(text), "the historic cut is exactly 70 chars")
                rec = g16.route_record_from_stored_string(text, source=name)
                self.assertFalse(rec["route_echoed_is_complete"])
                self.assertTrue(
                    rec["absence_of_a_keyword_may_not_be_read_from_this_route"])

    def test_decisive_proof_freq_is_absent_from_the_stored_ts_route_but_was_parsed(self):
        """The report refutes its own field -- HANDOFF_CODER6 §B-1 point 3."""
        routes = self._real_rt1_routes()
        ts_route = routes["ts_qst2.log"]
        self.assertNotIn("freq", ts_route)
        verdict = g16.keyword_in_route(
            g16.route_record_from_stored_string(ts_route, source="ts_qst2.log"),
            "freq")
        self.assertIsNone(verdict, "must be UNKNOWN, not False -- freq's absence "
                          "cannot be asserted off a truncated route")

    def test_a_short_balanced_legacy_string_is_unknown_not_confirmed_complete(self):
        """Under 70 chars and balanced: not refuted, but STILL never True."""
        rec = g16.route_record_from_stored_string("#p wB97XD/def2TZVP opt freq")
        self.assertIsNone(rec["route_echoed_is_complete"])

    def test_empty_or_missing_value(self):
        for value in (None, ""):
            with self.subTest(value=value):
                rec = g16.route_record_from_stored_string(value)
                self.assertEqual(0, rec["route_echoed_line_count"])
                self.assertIsNone(rec["route_echoed_is_complete"])

    # 🔴 FROZEN HISTORICAL TEMPLATES, not read live from config/qc_levels.json.
    # These are the job_type templates EXACTLY AS THEY WERE at the time P1 actually ran
    # (i.e. before B-2 added `nosymm` to the live config -- see
    # `_nosymm_required_job_types` / `_nosymm_requirement` in qc_levels.json). This proof is
    # about a HISTORICAL FACT (what template built these three already-stored strings), so it
    # must not silently track the live config as B-2/future items keep editing it -- if it did,
    # this test would start failing for the wrong reason (the config changed) instead of the
    # right one (someone broke the reconstruction logic).
    _HISTORICAL_JOB_TYPES_PRE_B2 = {
        "ts_qst2": "#p {functional}/{basis} {solvent} opt=(qst2,calcfc,noeigentest,maxcycles=100) freq",
        "irc_forward": "#p {functional}/{basis} {solvent} irc=(calcfc,forward,maxpoints=30)",
        "irc_reverse": "#p {functional}/{basis} {solvent} irc=(calcfc,reverse,maxpoints=30)",
    }

    def test_reconstruction_from_the_historical_template_reproduces_all_three_bytefor_byte(self):
        """coder7's FOURTH proof (docs/05_STATE.md §0-k): rebuilding the requested
        route from config/qc_levels.json's job_type templates AS THEY STOOD AT THE TIME
        (frozen above -- B-2 has since added `nosymm` to the live config) and cutting at 70
        columns reproduces the three RT-1 stored strings byte-for-byte. This retires the
        [UNKNOWN] on `freq` (the template asked for it); it does NOT retire the one on
        `nosymm` (the template shows what was REQUESTED at the time, not RECEIVED)."""
        solvent = "scrf=(smd,solvent=acetonitrile)"  # G-1 (level2), the primary level P1 used
        rebuilt = {
            "ts_qst2.log": self._HISTORICAL_JOB_TYPES_PRE_B2["ts_qst2"].format(
                functional="wB97XD", basis="gen", solvent=solvent),
            "irc_forward.log": self._HISTORICAL_JOB_TYPES_PRE_B2["irc_forward"].format(
                functional="wB97XD", basis="gen", solvent=solvent),
            "irc_reverse.log": self._HISTORICAL_JOB_TYPES_PRE_B2["irc_reverse"].format(
                functional="wB97XD", basis="gen", solvent=solvent),
        }
        stored = self._real_rt1_routes()
        for name, full in rebuilt.items():
            with self.subTest(log=name):
                self.assertEqual(full[:g16.ROUTE_ECHO_WRAP_COLUMNS], stored[name])
        # and the tail that was lost is exactly what HANDOFF_CODER6 §B-1 says:
        self.assertEqual(
            "test,maxcycles=100) freq",
            rebuilt["ts_qst2.log"][g16.ROUTE_ECHO_WRAP_COLUMNS:])

    def test_the_live_config_no_longer_matches_the_frozen_pre_b2_template(self):
        """Documents WHY the historical template above is frozen rather than read live: after
        B-2, `nosymm` sits right after `#p`, so the live template no longer reproduces the
        stored (pre-B-2) RT-1 strings when cut at 70 -- that is the fix working, not a break."""
        cfg_path = os.path.join(REPO_ROOT, "src", "pilot_package", "config",
                                "qc_levels.json")
        with open(cfg_path) as fh:
            live = json.load(fh)["gaussian16"]["job_types"]["ts_qst2"]
        self.assertNotEqual(live, self._HISTORICAL_JOB_TYPES_PRE_B2["ts_qst2"])
        self.assertIn("nosymm", live)


class TestKeywordInRoute(unittest.TestCase):
    def test_present_is_true_regardless_of_completeness(self):
        rec = g16.route_record_from_stored_string(
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen")
        self.assertIs(True, g16.keyword_in_route(rec, "smd"))

    def test_absent_from_a_complete_route_is_false(self):
        rec = g16.parse_route_echo(WRAPPED_LOG)
        self.assertIs(False, g16.keyword_in_route(rec, "nosymm"))

    def test_absent_from_an_incomplete_route_is_none(self):
        rec = g16.route_record_from_stored_string(
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen")
        self.assertIsNone(g16.keyword_in_route(rec, "nosymm"))

    def test_no_route_at_all_is_none(self):
        rec = g16.parse_route_echo(NO_ROUTE_LOG)
        self.assertIsNone(g16.keyword_in_route(rec, "nosymm"))


class TestRequireKeywordKnownAbsent(unittest.TestCase):
    def test_raises_when_undetermined(self):
        rec = g16.route_record_from_stored_string(
            "#p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen")
        with self.assertRaises(g16.RouteTruncatedError):
            g16.require_keyword_known_absent(rec, "nosymm")

    def test_raises_when_the_keyword_is_actually_present(self):
        rec = g16.parse_route_echo(WRAPPED_LOG)
        with self.assertRaises(g16.RouteTruncatedError):
            g16.require_keyword_known_absent(rec, "smd")

    def test_returns_none_when_genuinely_and_verifiably_absent(self):
        rec = g16.parse_route_echo(WRAPPED_LOG)
        self.assertIsNone(g16.require_keyword_known_absent(rec, "nosymm"))

    def test_never_assert_nosymm_absent_from_the_real_p1_route(self):
        """🔒 HANDOFF_CODER6 §B-2 / docs/05_STATE.md §0-k: nosymm stays [UNKNOWN]
        for the RT-1 run. [R-13] fixture 는 위의 frozen 문자열이다 — 사용자 결과
        트리를 읽지 않는다."""
        ts_route = (TestRouteRecordFromStoredString
                    ._FROZEN_RT1_STORED_ROUTES["ts_qst2.log"])
        rec = g16.route_record_from_stored_string(ts_route, source="ts_qst2.log")
        with self.assertRaises(g16.RouteTruncatedError):
            g16.require_keyword_known_absent(rec, "nosymm")


class TestCurrentReplyRoutesAreComplete(unittest.TestCase):
    """[R-13] 더 강한 **현재** 사실: 2026-08 클러스터 회신의 세 route 는 완전하고
    completeness evidence 를 갖는다 — B-1 수정이 실제 클러스터에서 작동한 증거.

    아래 fixture 는 그 회신(sei_pilot_work/results/sei_probe_report.cpu.json 의
    pilots[0].g16)에서 **한 번 복사해 얼린 것**이다 — 테스트가 사용자 결과 트리를
    읽으면 트리 재구성마다 빨개진다(R-13 의 존재 이유). ⚠ nosymm 이 route 에 실제로
    수신됐다는 사실(B-2 의 [UNKNOWN] 을 이 회신에 한해 닫는 증거)도 여기 있다."""

    _FROZEN_CURRENT_REPLY_G16 = {
        "ts_qst2.log": {
            "route_echoed": ("#p nosymm wB97XD/gen scrf=(smd,solvent=acetonitrile) "
                             "opt=(qst2,calcfc,noeigentest,maxcycles=100) freq"),
            "route_echoed_is_complete": True,
            "route_echo_completeness_evidence":
                "reassembled 2 echoed line(s), block closed by delimiter, "
                "parentheses balanced",
        },
        "irc_forward.log": {
            "route_echoed": ("#p nosymm wB97XD/gen scrf=(smd,solvent=acetonitrile) "
                             "irc=(calcfc,forward,maxpoints=30)"),
            "route_echoed_is_complete": True,
            "route_echo_completeness_evidence":
                "reassembled 2 echoed line(s), block closed by delimiter, "
                "parentheses balanced",
        },
        "irc_reverse.log": {
            "route_echoed": ("#p nosymm wB97XD/gen scrf=(smd,solvent=acetonitrile) "
                             "irc=(calcfc,reverse,maxpoints=30)"),
            "route_echoed_is_complete": True,
            "route_echo_completeness_evidence":
                "reassembled 2 echoed line(s), block closed by delimiter, "
                "parentheses balanced",
        },
    }

    def test_all_three_routes_are_complete_with_evidence(self):
        for name, rec in self._FROZEN_CURRENT_REPLY_G16.items():
            with self.subTest(log=name):
                self.assertTrue(rec["route_echoed_is_complete"])
                self.assertIn("parentheses balanced",
                              rec["route_echo_completeness_evidence"])
                self.assertGreater(len(rec["route_echoed"]),
                                   g16.ROUTE_ECHO_WRAP_COLUMNS,
                                   "70자보다 긴 route 가 온전히 재조립됐다 — "
                                   "절단 아티팩트는 더는 생성되지 않는다")

    def test_nosymm_was_actually_received_on_this_run(self):
        """B-2 가 넣은 nosymm 이 **에코에서** 확인된다 — RT-1 의 [UNKNOWN] 과 달리
        이 회신은 요청이 아니라 수신을 증언한다."""
        for name, rec in self._FROZEN_CURRENT_REPLY_G16.items():
            with self.subTest(log=name):
                self.assertIn("#p nosymm", rec["route_echoed"])


class TestP5RouteFieldsRename(unittest.TestCase):
    """`criteria/p5.py`'s consumer side of the rename. `route` must never survive
    into a normalized row again -- that bare string is exactly what let absence
    be read off a truncated route for a full second (HANDOFF_CODER6 §B-1)."""

    def _row(self, raw):
        return p5.normalize_rows([raw])[0]

    def _base(self, **over):
        d = dict(id="s1", seed=0, n_atoms=10, charge=0, multiplicity=1,
                core_hours=1.0, wall_h=1.0, scf_cycles_max=10,
                scf_cycles_total=10, opt_cycles=1, rc=0, converged=True,
                qc_code="gaussian16", level_label="G-1")
        d.update(over)
        return d

    def test_bare_route_key_never_appears_in_a_normalized_row(self):
        row = self._row(self._base(route="#p wB97XD/gen scrf=(smd) opt=(qst2,calcfc,noeigen"))
        self.assertNotIn("route", row)

    def test_legacy_row_is_classified_and_never_marked_complete(self):
        row = self._row(self._base(route="#p wB97XD/gen scrf=(smd) opt=(qst2,calcfc,noeigen"))
        self.assertIn("route_echoed", row)
        self.assertIsNot(True, row["route_echoed_is_complete"])

    def test_current_shape_row_passes_through_unchanged(self):
        row = self._row(self._base(
            route_echoed="#p wB97XD/gen scrf=(smd) opt freq",
            route_echoed_is_complete=True,
            route_echo={"route_echo_completeness_evidence": "reassembled 1 line"}))
        self.assertEqual("#p wB97XD/gen scrf=(smd) opt freq", row["route_echoed"])
        self.assertTrue(row["route_echoed_is_complete"])
        self.assertEqual("reassembled 1 line", row["route_echo_completeness_evidence"])

    def test_row_with_neither_shape_degrades_to_no_route_stored(self):
        row = self._row(self._base())
        self.assertIsNone(row["route_echoed"])
        self.assertIsNone(row["route_echoed_is_complete"])


if __name__ == "__main__":
    unittest.main()
