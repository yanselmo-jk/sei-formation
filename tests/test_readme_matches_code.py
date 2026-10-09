"""동봉 README 의 수치가 **코드와 어긋나면 RED.**

🔴 왜 생겼나: 인도 직전에 lead 가 tarball 을 풀어 **사용자가 실제로 받는 파일**을 읽었더니
README 가 코드와 전 항목 불일치였다.
```
                  README        실제 코드
core-h 상한       5,000         21,000
wall 상한         24 시간        48 시간
총 계산량         2,694.8       ~19,000
항목표            P3 있음        P3 없음(ADR-049)
                  P6 없음        P6_t1/t16/t64 있음  ← κ 측정, RT-1 의 존재 이유
```
🔴 **부품(`budget.py`/`plan.py`)은 critic3 가 검증한 대로 맞았다. 사람이 읽고 행동하는 면이
틀렸다.** ADR-041("부품은 맞고 조립선이 값을 떨어뜨린다")의 **사용자 대면판**이다.

🔴 **왜 이게 비싼가**: 사용자는 README 를 보고 **할당량을 신청**한다.
*"5,000 상한"* 을 읽고 19,000 이 예약되면 제출을 중단하거나, 더 나쁘게는
**할당 신청을 4배 작게 낸다.**

🔒 그리고 이건 **규약으로 못 지킨다** — 사용자가 이미 한 번 *"README 를 업데이트해"* 라고
지적했고, 그때 갱신된 문서가 **그 뒤에 정해진 재실행 사양을 따라오지 못했다.**
⟹ **구조가 규약을 이긴다**: 문서를 코드에 묶는다.

⚠ 그리고 이 검사 **자신이 검사망 안에 있는지** 먼저 확인했다(ADR-041 재발 방지):
`test_spec_block_is_actually_parsed` 가 **블록을 못 찾으면 실패**하므로, 누가 SPEC-BLOCK 을
지우면 이 검사가 조용히 통과하는 대신 RED 가 된다.
"""

import os
import re
import unittest

import context  # noqa: F401
from sei_pilot import budget, plan, sysprobe

README = os.path.join(context.PKG_ROOT, "README_USER.cpu.md")

#: 🔒 README 가 전제하는 클러스터 사양. **실측값이다**(RT-1 회신):
#:  계산 노드 Xeon Phi 7250 = 68 core 감지 → 64 요청, `normal` 큐 48 h(ADR-052 사용자 확인).
CLUSTER_CORES_PER_NODE = 64
CLUSTER_QSTAT = ("Queue: normal\n    resources_max.walltime = 48:00:00\n"
                 "    enabled = True\n    started = True\n")

#: 🔴 낡은 리터럴 재유입 거부. 전부 **실제로 README 에 박혀 있던 틀린 값들**이다.
STALE_LITERALS = {
    "5,000 core-hour": "옛 guard (κ=1 단위). 지금은 21,000 [물리 천장]",
    "2,694.8": "옛 총 계산량. 지금은 ~19,000",
    "**24 시간**": "옛 wall 상한. 지금은 48 시간(ADR-052 사용자 확인)",
}


def read_readme():
    with open(README, encoding="utf-8") as fh:
        return fh.read()


def spec_block(text):
    """README 의 기계 검증 블록 → dict. **없으면 예외**(이 검사가 조용히 통과하지 않게)."""
    m = re.search(r"SPEC-BLOCK-START.*?```(.*?)```", text, re.S)
    if not m:
        raise AssertionError(
            "README 에 SPEC-BLOCK 이 없다 — 이 검사가 검증할 대상이 사라졌다. "
            "블록을 지우려면 이 테스트도 함께 지워야 한다(조용히 통과하면 안 된다).")
    out = {}
    for line in m.group(1).splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def code_truth():
    """**코드에서** 계산한 사실. README 가 이것과 맞아야 한다."""
    q = sysprobe.parse_qstat_all_queues(CLUSTER_QSTAT)
    env = {"cores_per_node": CLUSTER_CORES_PER_NODE, "scheduler": "pbs", "queues": q,
           "software": {"g16": {"path": "/apps/commercial/G16/g16/g16"}},
           "vendored": {}, "containers": {},
           "qc_module": {"module": "gaussian/g16.c01.lin"}}
    g = budget.guard_for_profile("cpu")
    planned, _summary = plan.build_plan(env, g, profile="cpu", submit_queue="normal")
    live = [e for e in planned if e["status"] == "planned"]
    return {
        "guard_core_hours": g.max_core_hours,
        "guard_wall_h": g.max_wall_h,
        "items": [e["key"] for e in live],
        "reserved": sum(e["reserved_core_hours"] for e in live),
        "expected": sum(e.get("expected_core_hours") or 0 for e in live),
    }


class TestReadmeMatchesCode(unittest.TestCase):
    """🔴 README 는 사용자가 **할당량을 신청할 때 보는 문서**다. 틀리면 비싸다."""

    def test_spec_block_is_actually_parsed(self):
        """🔴 **이 검사 자신이 검사망 안에 있는가.**

        SPEC-BLOCK 이 사라지면 나머지 검사가 **조용히 통과**할 수 있다 —
        그건 우리가 여덟 번 기록한 '조용한 실패'를 검사기 자신이 저지르는 것이다.
        """
        block = spec_block(read_readme())
        for key in ("core_hours_guard", "wall_guard_h", "items",
                    "expected_total_core_hours", "reserved_total_core_hours"):
            self.assertIn(key, block, "SPEC-BLOCK 에 %s 가 없다" % key)

    def test_guard_values_match(self):
        block, truth = spec_block(read_readme()), code_truth()
        self.assertEqual(int(block["core_hours_guard"]), int(truth["guard_core_hours"]),
                         "README 의 core-h 상한이 코드와 다르다 — 사용자가 이 값으로 "
                         "할당량을 신청한다")
        self.assertEqual(int(block["wall_guard_h"]), int(truth["guard_wall_h"]),
                         "README 의 wall 상한이 코드와 다르다")

    def test_item_list_matches(self):
        """🔴 P3 가 남아 있거나 P6 가 빠지면 여기서 걸린다 — 둘 다 실제로 일어났다."""
        block, truth = spec_block(read_readme()), code_truth()
        listed = [x.strip() for x in block["items"].split(",") if x.strip()]
        self.assertEqual(sorted(listed), sorted(truth["items"]),
                         "README 항목표가 실제 계획과 다르다")

    def test_totals_match_within_rounding(self):
        block, truth = spec_block(read_readme()), code_truth()
        self.assertAlmostEqual(float(block["reserved_total_core_hours"]),
                               truth["reserved"], delta=1.0,
                               msg="README 의 예약 합계가 코드와 다르다")
        self.assertAlmostEqual(float(block["expected_total_core_hours"]),
                               truth["expected"], delta=1.0,
                               msg="README 의 예상 소비가 코드와 다르다")

    def test_p6_is_explained_not_just_listed(self):
        """🔴 P6 는 **무엇을 재는지**가 적혀 있어야 한다.

        사용자가 "이건 뭔지 모르겠으니 빼자"고 판단하면 **κ 가 미측정으로 남고, 그러면
        나머지 측정값이 전부 '몇 배 단위인지 모르는 숫자'가 된다.**
        """
        text = read_readme()
        self.assertIn("P6_t1", text)
        self.assertIn("스레드", text)
        for token in ("κ", "빼지 마세요"):
            self.assertIn(token, text, "P6 의 목적/경고가 README 에 없다")

    def test_wall_mismatch_instruction_present(self):
        """🔴 48 h 가 아닐 때 **무엇을 해야 하는지**가 있어야 한다.

        dry-run 이 경고를 띄워도, 그 경고가 무슨 뜻이고 무엇을 해야 하는지 문서가
        받아주지 않으면 사용자는 그냥 제출한다.
        """
        text = read_readme()
        self.assertIn("48", text)
        self.assertIn("제출하지 마시고", text)
        self.assertIn("UNVERIFIED", text)

    def test_no_stale_literals(self):
        """🔴 낡은 값 재유입 거부. 전부 **실제로 박혀 있던** 틀린 값이다."""
        text = read_readme()
        for lit, why in STALE_LITERALS.items():
            self.assertNotIn(lit, text, "README 에 낡은 값 %r 가 있다 (%s)" % (lit, why))

    def test_removed_item_is_not_advertised(self):
        """P3 는 ADR-049 로 계획에서 빠졌다 — README 가 그것을 광고하면 안 된다."""
        block = spec_block(read_readme())
        self.assertNotIn("P3", block["items"])



class TestPackagedReadmeMatchesCode(unittest.TestCase):
    """🔴 **검사는 소스를 지키는데 사용자는 사본을 받는다** (lead 발견).

    ```
    검사 대상 : src/pilot_package/README_USER.cpu.md      ← mv 이전
    make_package.sh:47-48  mv README_USER.cpu.md → README_USER.md ; rm -f README_USER.*.md
    사용자    : tarball 안 sei_pilot_cpu/README_USER.md   ← mv 이후
    ```
    ⟹ 복사·개명 단계가 깨지면 **소스 검사는 초록인 채 사용자는 틀린 문서를 받는다.**

    ⚠ **정확히 적는다**: 지금 노출된 것이 아니라 **방어선이 얇은 것**이다.
    `make_package.sh:5` 의 `set -eu` 가 명령 실패는 잡는다(이번 disk-full 사고도 그것이 잡아
    빌드가 죽었고, **깨진 tarball 이 나간 것이 아니다**). 남는 위험은 `cp` 가 exit 0 을 내며
    부분 실패하는 경로와, 향후 리팩터로 `set -e` 가 깨지는 경우다.
    🔴 그리고 `build_stamp.py` 에는 **tarball 을 열어 대조하는 경로가 아예 없었다.**

    🔴 이 검사만으로는 부족하다 — `make_package.sh` 안에서는 tarball 이 `.stale` 로 치워져
    있어 **skip 된다**(교착 회피를 위해 의도적으로 그렇다).
    ⟹ **`tar czf` 뒤에 이 검사를 따로 한 번 더 돌린다**(같은 파일의 `TestBuildGate` 참조).
    **무엇을 검사할지(이 클래스)와 언제 검사할지(그 관문)는 함께 있어야 보호가 된다.**
    """

    MEMBER = "sei_pilot_cpu/README_USER.md"

    def packaged_readme(self):
        import tarfile
        path = os.path.join(os.path.dirname(context.PKG_ROOT), "dist",
                            "sei_pilot_cpu.tar.gz")
        if not os.path.exists(path):
            self.skipTest("tarball 이 없다 (빌드 전 게이트에서는 정상 — 교착 회피)")
        with tarfile.open(path) as tf:
            fh = tf.extractfile(self.MEMBER)
            if fh is None:
                self.fail("인도물에 %s 가 없다 — 개명 단계가 깨졌다" % self.MEMBER)
            return fh.read().decode("utf-8")

    def test_packaged_readme_matches_code(self):
        """🔴 **사용자가 받는 문서**가 코드와 맞는가. 소스가 아니라 인도물이다."""
        block, truth = spec_block(self.packaged_readme()), code_truth()
        self.assertEqual(int(block["core_hours_guard"]), int(truth["guard_core_hours"]))
        self.assertEqual(int(block["wall_guard_h"]), int(truth["guard_wall_h"]))
        self.assertEqual(sorted(x.strip() for x in block["items"].split(",")),
                         sorted(truth["items"]))
        self.assertAlmostEqual(float(block["reserved_total_core_hours"]),
                               truth["reserved"], delta=1.0)
        self.assertAlmostEqual(float(block["expected_total_core_hours"]),
                               truth["expected"], delta=1.0)

    def test_packaged_readme_has_no_stale_literals(self):
        text = self.packaged_readme()
        for lit, why in STALE_LITERALS.items():
            self.assertNotIn(lit, text, "인도물 README 에 낡은 값 %r (%s)" % (lit, why))

    def test_packaged_readme_keeps_the_action_instructions(self):
        """P6 경고와 wall 불일치 지침이 **인도물에** 있는가."""
        text = self.packaged_readme()
        self.assertIn("빼지 마세요", text)
        self.assertIn("제출하지 마시고", text)

    def test_packaged_and_source_readme_are_identical(self):
        """🔴 개명 단계가 내용을 바꾸지 않았는가 — 바이트 단위."""
        with open(README, encoding="utf-8") as fh:
            source = fh.read()
        self.assertEqual(self.packaged_readme(), source,
                         "인도물 README 가 소스와 다르다 — 복사/개명 단계가 깨졌다")


class TestBuildGate(unittest.TestCase):
    """🔴 **관문 자신이 검사망 안에 있는가.**

    위 `TestPackagedReadmeMatchesCode` 는 빌드 중에는 `skip` 된다. 그래서 `make_package.sh`
    가 **`tar czf` 뒤에** 그 검사를 한 번 더 돌린다. 그 관문이 사라지면
    **검사는 남아 있는데 인도물이 만들어지는 순간에는 아무도 안 본다** — 이 프로젝트가
    반복한 형태 그대로다. ⟹ 관문의 **존재와 순서**를 고정한다.
    """

    def script(self):
        path = os.path.join(os.path.dirname(context.PKG_ROOT), "make_package.sh")
        with open(path, encoding="utf-8") as fh:
            return fh.read()

    def test_gate_exists_and_runs_after_packaging(self):
        text = self.script()
        self.assertIn("packaged_gate", text, "빌드 후 산출물 검증 관문이 없다")
        i_tar = text.index("tar czf")
        i_gate = text.index("packaged_gate")
        self.assertLess(i_tar, i_gate,
                        "관문이 tar czf 보다 앞에 있다 — 그러면 검사할 산출물이 없다")

    def test_gate_does_not_hardcode_class_names(self):
        """🔴 **이름을 적으면 다음 사람이 잊는다.**

        관문이 클래스 이름을 손으로 나열하면, tarball 을 여는 검사를 새로 만든 사람이
        **관문에도 추가해야 하고 언젠가 잊는다.** 그게 우리가 없애려는
        *"사람이 기억해야 작동하는 보호"* 다. ⟹ 관문은 **발견 모듈만** 부른다.
        """
        import packaged_gate
        # 🔴 **호출 줄만** 본다. 실패 사유 문구에 이름이 등장하는 것은 문서이지 배선이 아니다
        #    (처음엔 파일 전체를 봐서 사유 문구에 걸렸다 — 검사가 과했다).
        invocations = [ln for ln in self.script().splitlines()
                       if "-m unittest" in ln]
        self.assertTrue(invocations, "관문의 unittest 호출을 찾지 못했다")
        for line in invocations:
            for _mod, cls in packaged_gate.tarball_test_classes():
                self.assertNotIn(cls, line,
                                 "관문 호출이 클래스 이름 %s 를 하드코딩했다 — "
                                 "발견에 맡겨라(다음 사람이 잊는다)" % cls)

    def test_discovery_finds_every_tarball_opening_class(self):
        """🔴 발견이 **조용히 비거나 빠뜨리면** 관문은 '돌 것이 없다'며 통과한다.

        규약 18: **통과 쪽으로 넘어지는 관문은 없는 것보다 나쁘다.**
        그래서 발견 결과를 독립적으로 한 번 더 센다.
        """
        import ast as _ast
        import packaged_gate
        found = set(packaged_gate.tarball_test_classes())
        self.assertTrue(found, "tarball 을 여는 검사를 하나도 못 찾았다")
        expected = set()
        tests_dir = os.path.dirname(os.path.abspath(__file__))
        for fn in sorted(os.listdir(tests_dir)):
            if not (fn.startswith("test_") and fn.endswith(".py")):
                continue
            with open(os.path.join(tests_dir, fn), encoding="utf-8") as fh:
                src = fh.read()
            for node in _ast.parse(src).body:
                if isinstance(node, _ast.ClassDef) and \
                        packaged_gate.OPENS_TARBALL in \
                        (_ast.get_source_segment(src, node) or ""):
                    expected.add((fn[:-3], node.name))
        self.assertEqual(found, expected,
                         "관문이 도는 집합과 실제 tarball 검사 집합이 다르다")

    def test_known_tarball_checks_are_in_the_gate(self):
        """🔴 이미 사고를 겪고 만든 검사가 관문 안에 있는가 — 이름으로 못 박는다.

        `TestM2DecisionReachesTheTarball` 은 **lead 가 낡은 추출본을 보고 오판한 사고**
        때문에 생긴 것이다. 관문이 그것을 안 돌면 **빌드는 이미 한 번 일어난 사고 유형을
        자기 산출물에서 못 본다.**
        """
        import packaged_gate
        names = {c for _m, c in packaged_gate.tarball_test_classes()}
        self.assertIn("TestM2DecisionReachesTheTarball", names)
        self.assertIn("TestPackagedReadmeMatchesCode", names)

    def test_marker_makes_stamp_check_fail(self):
        """표시가 있으면 `check` 가 반드시 실패한다 — 사람들이 이미 돌리는 게이트다."""
        import json as _json
        import shutil
        import subprocess
        import sys as _sys
        import tempfile
        repo = os.path.dirname(os.path.dirname(context.PKG_ROOT))
        dist = os.path.join(os.path.dirname(context.PKG_ROOT), "dist")
        if not os.path.exists(os.path.join(dist, "BUILD_STAMP.json")):
            self.skipTest("dist 가 없다")
        tmp = tempfile.mkdtemp(prefix="sei_marker_")
        self.addCleanup(shutil.rmtree, tmp, True)
        for f in os.listdir(dist):
            if f.endswith(".json") or f.endswith(".sha256"):
                shutil.copy(os.path.join(dist, f), tmp)
            elif f.endswith(".tar.gz"):
                shutil.copy(os.path.join(dist, f), tmp)
        with open(os.path.join(tmp, "VERIFICATION_FAILED.json"), "w") as fh:
            _json.dump({"reason": "테스트가 주입한 표시"}, fh)
        r = subprocess.run(
            [_sys.executable, os.path.join(repo, "src", "build_stamp.py"),
             "check", "--root", repo, "--dist", tmp],
            capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0,
                            "표시가 있는데 check 가 ✅ 를 냈다 — 표시를 못 보고 지나칠 수 있다")
        self.assertIn("산출물 검증에 실패", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
