"""CREST 부재가 **조용한 성공**으로 지나가지 않는가 (ADR-044 / proposer §37).

🔴 왜 이게 필요한가 — engineer 의 진단이 방향을 반대로 짚었고 proposer 가 코드를 읽고 정정했다:
    engineer §R21.5(b)④: *"P1 에 crest 스테이지가 있다 ⟹ rc≠0 이 한 번 더 난다"*
    → **틀렸다.** `payload/P1.sh` 의 crest 는 `if [ -n "$CREST" ]` 로 가드돼 있어
      없으면 **우아하게 생략**된다. rc 는 0 이다.
    🔴 **진짜 위험은 정반대다:**
      *"CREST 가 없으면 P1 은 실패하지 않고 **conformer 표집을 건너뛴 채 'pass' 로
        돌아온다.**"*
    ⟹ 우리가 core-h 를 주고 사는 **TS 단가가 과소평가된 채** 회신되고, 받는 쪽은 그것을
      완전한 TS 워크플로 단가로 읽는다. `status` 도 `rc` 도 그 사실을 말하지 않는다.

🔴 **이 세션에서 같은 형태가 네 번째다**(B-3 / `to_dict()` 400자 컷 / `host` 유실 / 이번 CREST):
    **"시끄러운 실패"인 줄 알았던 것이 실은 "조용한 성공"이었다.**

🔴 픽스처를 손으로 짜지 않는다(ADR-042):
    `crest_status.json` 을 파이썬 문자열로 지어내면 **"내가 상상한 payload 출력"** 을
    검증하게 된다 — 그리고 그것이 정확히 B-3 가 통과했던 방식이다.
    ⟹ **`payload/P1.sh` 에서 그 파일을 쓰는 `printf` 줄을 그대로 뽑아 `bash` 로 실행**해
      픽스처를 만든다. payload 가 형식을 바꾸면 이 테스트가 깨진다 — 그게 목적이다.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import cli, collect
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

P1_SH = os.path.join(context.PKG_ROOT, "payload", "P1.sh")


def payload_crest_status_lines():
    """`P1.sh` 에서 `crest_status.json` 을 쓰는 줄을 **소스에서 뽑는다.**"""
    with open(P1_SH, encoding="utf-8") as fh:
        src = fh.read()
    lines = [ln.strip() for ln in src.splitlines()
             if "crest_status.json" in ln and ln.strip().startswith("printf")]
    return lines


def make_crest_status(job_dir, skipped):
    """payload 의 진짜 `printf` 줄을 bash 로 실행해 픽스처를 만든다."""
    lines = payload_crest_status_lines()
    assert len(lines) == 2, ("P1.sh 가 crest_status.json 을 쓰는 줄이 2개가 아니다: %r"
                             % lines)
    wanted = "true" if skipped else "false"
    line = next(ln for ln in lines if '"crest_skipped": %s' % wanted in ln)
    # payload 는 `$D` 와 `${CREST}` 를 쓴다. 그 두 변수만 주고 그대로 실행한다.
    script = 'D=%s\nCREST=%s\n%s\n' % (
        job_dir, "/opt/crest/crest" if not skipped else "", line)
    proc = subprocess.Popen(["bash", "-c", script],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = proc.communicate()
    assert proc.returncode == 0, (out, err)
    return os.path.join(job_dir, "crest_status.json")


class TestPayloadWritesCrestStatus(unittest.TestCase):
    def test_payload_has_both_branches(self):
        lines = payload_crest_status_lines()
        self.assertEqual(len(lines), 2)
        self.assertTrue(any('"crest_skipped": true' in ln for ln in lines))
        self.assertTrue(any('"crest_skipped": false' in ln for ln in lines))

    def test_generated_fixture_is_valid_json(self):
        d = tempfile.mkdtemp(prefix="sei_crest_")
        try:
            rec = json.load(open(make_crest_status(d, skipped=True)))
            self.assertIs(rec["crest_skipped"], True)
            self.assertIsNone(rec["crest_path"])
            rec2 = json.load(open(make_crest_status(d, skipped=False)))
            self.assertIs(rec2["crest_skipped"], False)
            self.assertEqual(rec2["crest_path"], "/opt/crest/crest")
        finally:
            shutil.rmtree(d, ignore_errors=True)


class TestCrestAbsenceIsReportedAsDegraded(unittest.TestCase):
    """🔴 진입점: `collect_p1` → 회신 JSON 의 P1 항목."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_p1deg_")
        self.store = Store(self.d)
        self.jd = self.store.job_dir("P1")
        os.makedirs(self.jd, exist_ok=True)
        # 🔴 Store 의 진짜 API 로 마커를 만든다(내가 상상한 write_marker 가 아니라).
        self.store.mark_submitted("P1", {"jobid": "1"})
        self.store.mark_done("P1", {"start_epoch": 1, "end_epoch": 3600})

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_missing_crest_marks_degraded_true(self):
        make_crest_status(self.jd, skipped=True)
        res = collect.collect_p1(self.store)
        self.assertIs(res["crest_skipped"], True)
        self.assertIs(res["degraded"], True)
        self.assertTrue(res["degraded_reasons"])
        self.assertIn("crest_absent", res["degraded_reasons"][0])
        # 🔴 사람이 읽는 warnings[] 에도 실려야 한다 (lead 요구).
        self.assertTrue(any("crest_absent" in w for w in res.get("warnings", [])))

    def test_degradation_says_the_cost_is_underestimated(self):
        """🔴 문구가 핵심이다. '건너뛰었다'만 적으면 받는 쪽이 비용 영향을 모른다."""
        make_crest_status(self.jd, skipped=True)
        res = collect.collect_p1(self.store)
        reason = res["degraded_reasons"][0]
        self.assertIn("과소평가", reason)
        self.assertIn("S3", reason)

    def test_present_crest_is_not_degraded(self):
        """🔴 오경보 금지. 정상 실행에 degraded 를 달면 다음부터 아무도 안 믿는다."""
        make_crest_status(self.jd, skipped=False)
        res = collect.collect_p1(self.store)
        self.assertIs(res["crest_skipped"], False)
        self.assertIs(res["degraded"], False)
        self.assertEqual(res["degraded_reasons"], [])

    def test_no_status_file_is_unknown_not_false(self):
        """🔴 ADR-036. 파일이 없으면 '건너뛰지 않았다'가 아니라 **모른다** 다.

        `False` 로 채우면 **없는 보증**을 만들어낸다 — 옛 판으로 돈 잡이나 일찍 죽은
        잡을 '완전한 TS 워크플로'로 읽게 된다.
        """
        res = collect.collect_p1(self.store)          # crest_status.json 없음
        self.assertIsNone(res["crest_skipped"])
        self.assertIsNone(res["degraded"])
        self.assertIn("모른다", res["degraded_note"])

    def test_degraded_does_not_turn_a_pass_into_a_fail(self):
        """🔴 degraded 는 실패가 아니라 **'덜 갖춘 성공'** 이다. 축이 다르다.

        status 를 fail 로 바꾸면 진짜 실패와 구분이 사라지고, 그러면 재실행 로직
        (`failed` 는 재시도한다)이 **멀쩡한 1,000 core-h 짜리 잡을 다시 돌린다.**

        🔴 처음 쓴 판은 `status != "fail"` 을 단언했는데, 이 픽스처의 P1 은 Gaussian 로그가
        없어 **원래부터 fail** 이다(진동수 미파싱·IRC 부재). 즉 degraded 와 무관한 이유로
        fail 이었고, 그 단언은 **degraded 의 효과를 전혀 검사하지 못했다.**
        ⟹ **대조 실험으로 바꾼다: crest 유무만 바꾸고 status 가 같은지 본다.**
        """
        make_crest_status(self.jd, skipped=True)
        degraded_res = collect.collect_p1(self.store)
        make_crest_status(self.jd, skipped=False)
        normal_res = collect.collect_p1(self.store)
        self.assertEqual(degraded_res["status"], normal_res["status"],
                         "crest 유무가 status 를 바꿨다 — degraded 는 판정 축이 아니다")
        self.assertIs(degraded_res["degraded"], True)
        self.assertIs(normal_res["degraded"], False)


class TestDegradedReachesTheReportJson(unittest.TestCase):
    """조립선 끝(디스크의 회신 JSON)까지 도달하는지 — `host` 유실과 같은 유형 차단."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_p1deg_rep_")
        store = Store(self.d)
        jd = store.job_dir("P1")
        os.makedirs(jd, exist_ok=True)
        store.mark_submitted("P1", {"jobid": "1"})
        store.mark_done("P1", {"start_epoch": 1, "end_epoch": 3600})
        make_crest_status(jd, skipped=True)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_report_json_carries_degraded(self):
        args = cli.build_parser().parse_args(
            ["collect", "--workdir", self.d, "--pkg-root", context.PKG_ROOT])
        shell = FakeShell(responses={"hostname -f": (0, "testbox\n", "")},
                          which_map={})
        path = cli.cmd_collect(args, shell=shell, store=Store(self.d))
        with open(path) as fh:
            rep = json.load(fh)
        p1 = next(p for p in rep["pilots"] if p["id"] == "P1")
        self.assertIs(p1["degraded"], True)
        self.assertIs(p1["crest_skipped"], True)


if __name__ == "__main__":
    unittest.main()
