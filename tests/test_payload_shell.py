"""🔴 payload 셸을 **실제로 실행**하는 회귀 테스트 (critic B-1).

왜 필요한가: 기존 162~179개 테스트는 제출 로직(job id, afterany 플래그)만 검증하고
**bash payload를 한 번도 실행하지 않았다.** 그래서 "체인 링크 2개 × payload 무체크포인트"
상호작용 — 즉 링크 1이 전체 워크플로를 처음부터 다시 도는 버그 — 를 원리적으로 잡을 수
없었다. 여기서는 스케줄러 대신 우리가 링크 스크립트를 순서대로 실행해 그 상호작용을 본다.

검증 대상:
  1. 링크 0이 완료되면 링크 1은 **아무것도 다시 계산하지 않는다** (논리 키 멱등성)
  2. 링크 0이 중간에 죽으면 링크 1이 **끝난 단계는 건너뛰고 이어받는다** (단계 체크포인트)
  3. 이중 실행이 실제로 일어나면 그 사실이 **감사 기록에 남는다**
"""

import os
import re
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import collect as collect_mod
from sei_pilot import scheduler as sch
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

TEMPLATES = os.path.join(context.PKG_ROOT, "sei_pilot", "templates")
HAVE_BASH = shutil.which("bash") is not None

# 비싼 QC 단계를 흉내 내는 payload. 실행될 때마다 카운터 파일에 한 줄씩 남긴다.
FAKE_PAYLOAD = r"""#!/bin/bash
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"

stage_a() { echo "A" >> "${SEI_JOB_DIR}/ran_a.txt"; return 0; }
stage_b() {
  echo "B" >> "${SEI_JOB_DIR}/ran_b.txt"
  # SEI_FAIL_B=1 이면 링크 0에서 죽는 상황을 흉내 낸다
  [ "${SEI_FAIL_B:-0}" = "1" ] && return 3
  return 0
}

sei_stage a stage_a || exit 1
sei_stage b stage_b || exit 1
exit 0
"""


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class TestChainIdempotency(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_shell_")
        self.store = Store(self.d)
        self.job_dir = self.store.job_dir("P1")
        self.payload = os.path.join(self.d, "fake_payload.sh")
        with open(self.payload, "w") as fh:
            fh.write(FAKE_PAYLOAD)
        os.chmod(self.payload, 0o755)
        self.adapter = sch.LocalAdapter(FakeShell(), TEMPLATES, workdir=self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _spec(self, key, logical="P1"):
        return sch.JobSpec(
            key, "bash %s" % self.payload, nodes=1, cores_per_node=1, wall_h=0.5,
            job_dir=self.job_dir, logical_key=logical,
            env={"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d})

    def _run(self, script, env_extra=None):
        env = dict(os.environ)
        env.update(env_extra or {})
        return subprocess.run(["bash", script], env=env, capture_output=True,
                              universal_newlines=True)

    def _count(self, name):
        path = os.path.join(self.job_dir, name)
        if not os.path.exists(path):
            return 0
        with open(path) as fh:
            return len([x for x in fh.read().splitlines() if x.strip()])

    def test_link1_does_not_recompute_after_link0_success(self):
        """🔴 B-1의 '가장 흔한 실패 모드': 링크 0이 정상 종료했는데 afterany 로 뜬
        링크 1이 CREST부터 IRC까지 전부 다시 도는 문제."""
        s0 = self.adapter.write_script(self._spec("P1"))
        s1 = self.adapter.write_script(self._spec("P1_c1"))

        self._run(s0)
        self.assertEqual(self._count("ran_a.txt"), 1)
        self.assertEqual(self._count("ran_b.txt"), 1)
        self.assertTrue(self.store.is_done("P1"))

        self._run(s1)                      # afterany 로 그대로 실행된다
        self.assertEqual(self._count("ran_a.txt"), 1, "링크 1이 A를 다시 돌았다")
        self.assertEqual(self._count("ran_b.txt"), 1, "링크 1이 B를 다시 돌았다")

        audit = collect_mod.execution_audit(self.job_dir)
        self.assertIn("P1_c1", audit["links_skipped_idempotent"])
        self.assertFalse(audit["duplicate_execution"])

    def test_link1_resumes_from_checkpoint_when_link0_died(self):
        """링크 0이 B에서 죽으면 링크 1은 A를 건너뛰고 B만 다시 한다."""
        s0 = self.adapter.write_script(self._spec("P1"))
        s1 = self.adapter.write_script(self._spec("P1_c1"))

        self._run(s0, {"SEI_FAIL_B": "1"})          # B 실패
        self.assertEqual(self._count("ran_a.txt"), 1)
        self.assertEqual(self._count("ran_b.txt"), 1)
        self.assertTrue(self.store.is_failed("P1"))
        self.assertFalse(self.store.is_done("P1"))

        self._run(s1)                                # 이번엔 성공
        self.assertEqual(self._count("ran_a.txt"), 1, "완료된 단계 A를 다시 돌았다")
        self.assertEqual(self._count("ran_b.txt"), 2, "실패한 단계 B를 이어받지 않았다")
        self.assertTrue(self.store.is_done("P1"))

        audit = collect_mod.execution_audit(self.job_dir)
        self.assertEqual(audit["stage_run_counts"].get("b"), 2)
        self.assertEqual(audit["stage_skip_counts"].get("a"), 1)
        # A는 한 번만 실행됐으므로 이중 실행 경고는 B에 대해서만 뜬다
        self.assertIn("b", audit["duplicated_stages"])
        self.assertNotIn("a", audit["duplicated_stages"])

    def test_failed_marker_is_cleared_when_a_later_link_succeeds(self):
        """critic M-2: 링크 0 실패 후 링크 1 성공인데 영구히 'failed'로 남는 문제."""
        s0 = self.adapter.write_script(self._spec("P1"))
        s1 = self.adapter.write_script(self._spec("P1_c1"))
        self._run(s0, {"SEI_FAIL_B": "1"})
        self.assertTrue(self.store.is_failed("P1"))
        self._run(s1)
        self.assertFalse(self.store.is_failed("P1"), "실패 마커가 지워지지 않았다")
        status, _payload = collect_mod.job_status(self.store, "P1")
        self.assertEqual(status, "done")

    def test_double_execution_is_recorded_when_it_happens(self):
        """체크포인트를 잃은 상태(단계 마커 삭제)에서 재실행되면 감사에 남아야 한다."""
        s0 = self.adapter.write_script(self._spec("P1"))
        self._run(s0)
        # 완료 마커와 단계 마커를 지워 '이중 실행'을 강제로 만든다
        os.remove(os.path.join(self.store.state_dir, "P1.done.json"))
        for fn in os.listdir(os.path.join(self.job_dir, "stages")):
            os.remove(os.path.join(self.job_dir, "stages", fn))
        self._run(s0)

        audit = collect_mod.execution_audit(self.job_dir)
        self.assertTrue(audit["duplicate_execution"])
        self.assertTrue(any("double_execution" in w for w in audit["warnings"]))
        self.assertEqual(self._count("ran_a.txt"), 2)

    def test_logical_key_is_exported_into_the_job_script(self):
        script = self.adapter.write_script(self._spec("P1_c1"))
        text = open(script).read()
        self.assertIn('export SEI_KEY="P1_c1"', text)
        self.assertIn('export SEI_LOGICAL_KEY="P1"', text)

    def test_submit_chain_gives_every_link_the_same_logical_key(self):
        specs = []

        class RecordingAdapter(sch.LocalAdapter):
            def submit(self_inner, spec, deps=None):
                specs.append(spec)
                return sch.LocalAdapter.submit(self_inner, spec, deps)

        a = RecordingAdapter(FakeShell(), TEMPLATES, workdir=self.d)
        a.submit_chain(self._spec("P1"), 3)
        self.assertEqual([s.key for s in specs], ["P1", "P1_c1", "P1_c2"])
        self.assertEqual({s.logical_key for s in specs}, {"P1"})


class TestEveryQcPayloadSmokesFirst(unittest.TestCase):
    """🔴 Any payload that generates a QC input must validate the route FIRST.

    THE INCIDENT: `P6.sh` never called `sei_qc_smoke`. Every other production payload did; P6
    was simply never retrofitted when ADR-105/108 introduced the pattern. Its anchors went
    straight to production on an unvalidated deck and produced **zero usable kappa data** —
    kappa being the single dominant variable of the five-month schedule.

    🔒 THE RULE IS DERIVED, NOT ENUMERATED. An earlier version of this check listed six
    payloads by name; critic10 pointed out that a seventh would not be caught, which is the
    same defect the check exists to prevent, one level up. Scanning `payload/*.sh` means a new
    payload is covered the moment it is added — nobody has to remember to extend a list.
    """

    def _payloads(self):
        d = os.path.join(context.PKG_ROOT, "payload")
        for name in sorted(os.listdir(d)):
            if not name.endswith(".sh"):
                continue
            with open(os.path.join(d, name), errors="replace") as fh:
                text = fh.read()
            # 🔒 The library that DEFINES the helpers is not a payload that runs a job.
            #    Detected by the definition, not by filename — same reason as above.
            if "sei_qc_smoke() {" in text:
                continue
            yield name, text

    def test_generating_qc_input_implies_smoking_first(self):
        offenders = []
        for name, text in self._payloads():
            if "sei_qc_input" in text and "sei_qc_smoke" not in text:
                offenders.append(name)
        self.assertEqual([], offenders,
                         "these payloads generate a QC input without validating the route "
                         "first: %s. P6.sh did exactly this and cost the round its entire "
                         "kappa measurement." % offenders)

    def test_the_smoke_precedes_the_first_production_input(self):
        """Smoking AFTER generating production input would satisfy a naive check while
        establishing nothing — the deck would already have been used."""
        for name, text in self._payloads():
            if "sei_qc_input" in text and "sei_qc_smoke" in text:
                self.assertLess(text.index("sei_qc_smoke"), text.index("sei_qc_input"), name)

    def test_the_scan_actually_sees_the_payloads(self):
        """🔴 0-o.4 rule 2: a check that silently matches nothing passes forever. This is the
        reach property of the check itself — the exact failure the heredoc regex had."""
        names = [n for n, _t in self._payloads()]
        self.assertGreaterEqual(len(names), 6, names)
        self.assertIn("P6.sh", names)
        self.assertNotIn("qc_adapter.sh", names)


if __name__ == "__main__":
    unittest.main()


# --- 🔴 회귀: 실제 payload 가 sei_stage 를 쓸 수 있는가 -------------------------
#
# 이 버그가 왜 여기까지 살아남았나: 위 FAKE_PAYLOAD 는 **스스로 common.sh 를 source**
# 한다. 그런데 진짜 payload(P1/P1b/P2/P3/P5)는 하나도 그러지 않는다. 잡 템플릿은
#     source common.sh ; sei_job_main bash "<key>.cmd.sh"
# 인데, `bash <file>` 은 **새 프로세스**라 셸 함수를 물려받지 못한다.
# ⇒ 실제 클러스터에서는 전 payload 가 `sei_stage: command not found` 로 죽고,
#    단계 체크포인트·core-h 분해가 통째로 사라진다. 테스트는 초록불이었다.
#
# 교훈: 가짜 payload 가 진짜 payload 보다 **환경을 더 잘 갖추고 있으면** 테스트는
#       거짓 통과한다. 아래 두 테스트는 그 격차 자체를 못 박는다.

PAYLOAD_NO_SOURCE = r"""#!/bin/bash
set -u
sei_stage a true || exit 1
echo ok > "${SEI_JOB_DIR}/reached_end.txt"
exit 0
"""


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class TestPayloadGetsCommonFunctions(unittest.TestCase):
    """진짜 payload 처럼 common.sh 를 source 하지 않는 스크립트도 sei_stage 를 써야 한다."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_fn_")
        self.store = Store(self.d)
        self.job_dir = self.store.job_dir("P1")
        self.payload = os.path.join(self.d, "no_source_payload.sh")
        with open(self.payload, "w") as fh:
            fh.write(PAYLOAD_NO_SOURCE)
        os.chmod(self.payload, 0o755)
        self.adapter = sch.LocalAdapter(FakeShell(), TEMPLATES, workdir=self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self):
        spec = sch.JobSpec(key="P1", logical_key="P1", command="bash %s" % self.payload,
                           job_dir=self.job_dir, nodes=1, cores_per_node=1,
                           wall_h=0.25, env={"SEI_PKG_ROOT": context.PKG_ROOT,
                                             "SEI_WORKDIR": self.d})
        script = self.adapter.write_script(spec)
        return subprocess.run(["bash", script], capture_output=True, text=True,
                              timeout=120)

    def test_sei_stage_is_available_to_a_payload_that_does_not_source_common(self):
        proc = self._run()
        self.assertNotIn("sei_stage: command not found",
                         proc.stdout + proc.stderr,
                         "payload 가 sei_stage 를 못 본다 — 잡 템플릿이 `bash <file>` 로 "
                         "새 프로세스를 띄우기 때문. common.sh 함수가 전달돼야 한다.")
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "stages", "a.json")),
                        "단계 체크포인트가 기록되지 않았다 = 재개 능력이 없다")
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "reached_end.txt")))


class TestRealPayloadsCanCallSeiStage(unittest.TestCase):
    """정적 불변식: sei_stage 를 쓰는 payload 는 그 정의에 닿는 경로가 있어야 한다."""

    def test_every_payload_using_sei_stage_can_reach_its_definition(self):
        pdir = os.path.join(context.PKG_ROOT, "payload")
        offenders = []
        for name in sorted(os.listdir(pdir)):
            if not name.endswith(".sh") or name == "common.sh":
                continue
            text = open(os.path.join(pdir, name)).read()
            uses = any(line.strip().startswith("sei_stage ")
                       for line in text.splitlines())
            if uses and "payload/common.sh" not in text:
                offenders.append(name)
        self.assertEqual([], offenders,
                         "이 payload 들은 sei_stage 를 쓰면서 common.sh 를 source 하지 "
                         "않는다. 잡 템플릿이 새 bash 프로세스로 띄우므로 함수가 없다.")


class TestPayloadsOnlyCallFunctionsThatExist(unittest.TestCase):
    """🔴 P1.sh 가 ORCA 시절 함수 `sei_orca_header` 를 계속 부르고 있었다.

    qc_adapter.sh 를 Gaussian16 으로 **재작성**하면서 그 함수는 사라졌는데 P1.sh 만
    포팅에서 빠졌다. P1 은 최우선 항목(1,000 core-h)인데 첫 줄에서
    `command not found` 로 죽었을 것이다 — 그리고 이 실패는 잡이 노드에 올라가
    큐를 기다린 **뒤에야** 드러난다(왕복 1회 = 3.5일).

    셸에는 컴파일러가 없으니 이 검사가 컴파일러 역할을 한다.
    """

    ROOT = os.path.join(context.PKG_ROOT, "payload")

    def _defined(self):
        names = set()
        for name in os.listdir(self.ROOT):
            if name.endswith(".sh"):
                with open(os.path.join(self.ROOT, name)) as fh:
                    for line in fh:
                        m = re.match(r"^\s*(sei_[A-Za-z0-9_]+)\s*\(\)", line)
                        if m:
                            names.add(m.group(1))
        return names

    def _called(self, path):
        out = set()
        with open(path) as fh:
            for line in fh:
                stripped = line.strip()
                if stripped.startswith("#"):
                    continue
                for m in re.finditer(r"(?<![\w.$/-])(sei_[A-Za-z0-9_]+)", stripped):
                    name = m.group(1)
                    # 변수 참조(${SEI_...})나 정의 자체는 호출이 아니다
                    # `sei_pilot` 은 파이썬 패키지 이름이지 셸 함수가 아니다
                    # (payload 안 heredoc 의 `from sei_pilot import ...`).
                    if (name.isupper() or name == "sei_pilot"
                            or re.match(r"^\s*%s\s*\(\)" % name, stripped)):
                        continue
                    out.add(name)
        return out

    def test_no_payload_calls_an_undefined_sei_function(self):
        defined = self._defined()
        self.assertIn("sei_stage", defined, "common.sh 를 못 읽었다")
        offenders = {}
        for name in sorted(os.listdir(self.ROOT)):
            if not name.endswith(".sh"):
                continue
            missing = sorted(self._called(os.path.join(self.ROOT, name)) - defined)
            if missing:
                offenders[name] = missing
        self.assertEqual({}, offenders,
                         "존재하지 않는 sei_* 함수를 부르는 payload 가 있다. "
                         "어댑터를 갈아끼우면서 포팅이 빠진 것이다.")

    def test_the_orca_era_helper_is_really_gone(self):
        """포팅 누락을 놓쳤던 바로 그 이름 — 다시 들어오면 여기서 걸린다."""
        for name in os.listdir(self.ROOT):
            if name.endswith(".sh"):
                with open(os.path.join(self.ROOT, name)) as fh:
                    self.assertNotIn("sei_orca_header", fh.read(),
                                     "%s 에 ORCA 시절 헬퍼가 남아 있다" % name)
