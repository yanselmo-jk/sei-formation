"""🔴 array job 태스크 분기 — 이번 라운드(2026-08 클러스터 회신)를 무너뜨린 사고의 회귀 고정.

실측된 사고 (cpu_machine_pilot_results/sei_pilot_work, 읽기 전용 증거):
  * plan.py 는 P5 를 array=(1,22), P1b 를 array=(1,3) 으로 제출했고 렌더된 스크립트에
    `#PBS -J` 가 실제로 들어갔다. 그런데 payload 는 PBS_ARRAY_INDEX 를 읽지 않아
    **모든 태스크가 전체 목록을 돌았다.**
  * P1b: 3태스크가 같은 steps/<tag>/job.chk·job.log 에 동시에 썼다(G16 rwf 3개,
    Normal termination 0건). stage 13개 중 7개가 3회씩 실행됐다.
  * P5: 22태스크가 같은 tasks.tsv 를 `>` 로 덮어쓰며 읽어 대부분 0회 루프,
    species/ 비어 있음, rows [].
  * 같은 논리 키 공유로 state/P5.done.json 과 state/P5.failed.json 이 **둘 다** 생겼다.

여기의 각 테스트는 **사고를 재현하는 입력**(PBS_ARRAY_INDEX 가 설정된 환경)을 그대로
쓴다 — 수정 전 코드라면 실패했을 형태로.
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import collect as collect_mod
from sei_pilot import plan as plan_mod
from sei_pilot import scheduler as sch
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store
from test_u27_noneq import MOCK_G16

TEMPLATES = os.path.join(context.PKG_ROOT, "sei_pilot", "templates")
HAVE_BASH = shutil.which("bash") is not None

# 비싼 QC 를 흉내 내는 payload — 실행될 때마다 카운터에 한 줄 남긴다.
COUNTING_PAYLOAD = r"""#!/bin/bash
set -u
source "${SEI_PKG_ROOT}/payload/common.sh"
echo "ran key=${SEI_KEY}" >> "${SEI_JOB_DIR}/ran.txt"
exit 0
"""


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class TestCommonShTaskIdentity(unittest.TestCase):
    """common.sh 가 array index 로 키·마커·started 를 태스크 단위로 가르는가."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_arr_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.store = Store(self.d)
        self.job_dir = self.store.job_dir("P5")
        self.payload = os.path.join(self.d, "counting.sh")
        with open(self.payload, "w") as fh:
            fh.write(COUNTING_PAYLOAD)
        os.chmod(self.payload, 0o755)
        adapter = sch.LocalAdapter(FakeShell(), TEMPLATES, workdir=self.d)
        spec = sch.JobSpec("P5", "bash %s" % self.payload, nodes=1,
                           cores_per_node=1, wall_h=0.5, job_dir=self.job_dir,
                           env={"SEI_PKG_ROOT": context.PKG_ROOT,
                                "SEI_WORKDIR": self.d})
        self.script = adapter.write_script(spec)

    def _run(self, tid):
        env = dict(os.environ, PBS_ARRAY_INDEX=str(tid))
        return subprocess.run(["bash", self.script], env=env,
                              capture_output=True, text=True, timeout=120)

    def _ran_count(self):
        p = os.path.join(self.job_dir, "ran.txt")
        if not os.path.exists(p):
            return 0
        return len([l for l in open(p).read().splitlines() if l.strip()])

    def test_the_incident_a_finished_task_must_not_silence_the_next_one(self):
        """🔴 사고 재현 입력: 같은 스크립트, index 만 다른 두 태스크.

        수정 전에는 둘이 같은 SEI_LOGICAL_KEY("P5")를 공유해 — 태스크 1 이 남긴
        done 마커를 태스크 2 가 '내 완료 마커'로 읽고 **아무것도 하지 않았다**
        (또는 동시에 돌며 같은 산출물에 썼다). 태스크 2 는 반드시 실행돼야 한다.
        """
        self._run(1)
        self.assertEqual(1, self._ran_count())
        self._run(2)
        self.assertEqual(2, self._ran_count(), "task 2 가 task 1 의 마커에 막혔다")

    def test_markers_are_per_task_not_shared(self):
        """사고의 물증이 state/P5.done.json + state/P5.failed.json 공존이었다 —
        이제 마커는 P5.t<N>.done.json 으로 갈라진다."""
        self._run(1)
        self._run(2)
        st = os.listdir(self.store.state_dir)
        self.assertIn("P5.t1.done.json", st)
        self.assertIn("P5.t2.done.json", st)
        self.assertNotIn("P5.done.json", st)

    def test_started_json_is_per_task(self):
        """started.json 은 고정 경로 `>` 쓰기라 태스크들이 서로 지웠다(R31.2a)."""
        self._run(1)
        self._run(2)
        self.assertTrue(os.path.exists(
            os.path.join(self.job_dir, "started.t1.json")))
        self.assertTrue(os.path.exists(
            os.path.join(self.job_dir, "started.t2.json")))

    def test_executions_jsonl_carries_distinct_task_keys(self):
        self._run(1)
        self._run(2)
        links = [json.loads(l)["link"] for l in
                 open(os.path.join(self.job_dir, "executions.jsonl"))
                 if '"run"' in l]
        self.assertEqual(["P5.t1", "P5.t2"], links)

    def test_rerun_of_a_finished_task_is_idempotent(self):
        self._run(1)
        self._run(1)
        self.assertEqual(1, self._ran_count(), "완료된 태스크가 다시 돌았다")

    def test_double_source_does_not_double_suffix(self):
        """payload 가 common.sh 를 다시 source 해도(의도된 동작) .t1.t1 이 되지 않는다."""
        self._run(1)
        links = [json.loads(l)["link"] for l in
                 open(os.path.join(self.job_dir, "executions.jsonl"))]
        self.assertNotIn("P5.t1.t1", links)
        self.assertIn("P5.t1", links)

    def test_non_array_run_is_byte_identical_to_before(self):
        env = dict(os.environ)
        env.pop("PBS_ARRAY_INDEX", None)
        env.pop("SLURM_ARRAY_TASK_ID", None)
        subprocess.run(["bash", self.script], env=env, capture_output=True,
                       text=True, timeout=120)
        self.assertIn("P5.done.json", os.listdir(self.store.state_dir))
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "started.json")))


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _ArrayPayloadRun(unittest.TestCase):
    """mock g16 을 PATH 에 놓고 진짜 payload 를 array index 와 함께 돌린다
    (test_u27_noneq 의 목을 재사용 — 두 번째 목을 만들지 않는다)."""

    PAYLOAD = "P1b.sh"
    KEY = "P1b"

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_arrp_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        mock = os.path.join(self.bin, "g16")
        with open(mock, "w") as fh:
            fh.write(MOCK_G16)
        os.chmod(mock, 0o755)
        self.job_dir = os.path.join(self.d, "jobs", self.KEY)
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))

    def run_payload(self, tid=None):
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": self.KEY,
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8",
                    "MOCK_MODE": "accepting",
                    "SEI_SOLVENT_POLICY_JSON": context.TEST_SOLVENT_POLICY_JSON,
                    "PATH": self.bin + os.pathsep + env.get("PATH", "")})
        if tid is not None:
            env["PBS_ARRAY_INDEX"] = str(tid)
            # 잡 템플릿이 실제로 하는 일: common.sh 를 payload 전에 한 번 source 하지만,
            # 여기서는 payload 를 직접 실행한다(payload 가 스스로 source 한다 — 동일 경로).
        return subprocess.run(
            ["bash", os.path.join(context.PKG_ROOT, "payload", self.PAYLOAD)],
            env=env, capture_output=True, text=True, timeout=600)


class TestP1bTaskSplit(_ArrayPayloadRun):
    PAYLOAD = "P1b.sh"
    KEY = "P1b"

    def _steps(self):
        p = os.path.join(self.job_dir, "steps")
        return sorted(os.listdir(p)) if os.path.isdir(p) else []

    def test_task1_runs_exactly_one_species_and_no_stagewise_no_u27(self):
        """🔴 사고 재현 입력: PBS_ARRAY_INDEX=1. 수정 전에는 이 입력에서 3종 전부 +
        stagewise + U-27 이 돌았다(그래서 3태스크가 같은 파일에 동시에 썼다)."""
        proc = self.run_payload(tid=1)
        self.assertEqual(0, proc.returncode, proc.stdout[-1500:] + proc.stderr[-800:])
        steps = self._steps()
        species = set(t.split("_A_cheap_optfreq")[0] for t in steps
                      if "_A_cheap_optfreq" in t)
        self.assertEqual(1, len(species), "task 1 이 종 1개 초과를 돌았다: %s" % steps)
        self.assertFalse(any(t.startswith("stagewise_") for t in steps),
                         "stagewise 는 마지막 태스크 몫이다")
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "u27_noneq.json")),
                         "U-27 은 마지막 태스크 몫이다")

    def test_species_task3_has_no_extras_either(self):
        """[MAJOR #1] 3,072 core-h = 64×48h 는 wall 여유 0% — 종별 태스크 3 에 extras 를
        얹지 않는다(lead 판정). extras 는 전용 태스크 4 의 몫이다."""
        proc = self.run_payload(tid=3)
        self.assertEqual(0, proc.returncode, proc.stdout[-1500:] + proc.stderr[-800:])
        steps = self._steps()
        self.assertTrue(any("_A_cheap_optfreq" in t for t in steps))
        self.assertFalse(any(t.startswith("stagewise_") for t in steps))
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "u27_noneq.json")))

    def test_dedicated_task4_carries_the_stagewise_and_u27_extras_only(self):
        proc = self.run_payload(tid=4)
        self.assertEqual(0, proc.returncode, proc.stdout[-1500:] + proc.stderr[-800:])
        steps = self._steps()
        self.assertTrue(any(t.startswith("stagewise_") for t in steps))
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "u27_noneq.json")))
        self.assertFalse(any("_A_cheap_optfreq" in t for t in steps),
                         "extras 태스크가 종별 측정을 돌렸다 — 예산 경계 위반")

    def test_two_tasks_touch_disjoint_step_directories(self):
        """사고의 핵심: 같은 steps/<tag>/job.chk 에 G16 여러 개가 동시에 썼다.
        태스크별 실행이 서로소인 디렉터리만 만지면 그 충돌은 구조적으로 불가능하다."""
        self.run_payload(tid=1)
        after_t1 = set(self._steps())
        self.run_payload(tid=2)
        t2_new = set(self._steps()) - after_t1
        self.assertTrue(t2_new, "task 2 가 아무것도 만들지 않았다")
        self.assertFalse(after_t1 & t2_new)

    def test_out_of_range_index_fails_loudly_not_silently_empty(self):
        proc = self.run_payload(tid=9)
        self.assertEqual(5, proc.returncode)
        self.assertIn("벗어난다", proc.stdout + proc.stderr)


class TestP5TaskSplit(_ArrayPayloadRun):
    PAYLOAD = "P5.sh"
    KEY = "P5"

    def test_task_runs_exactly_its_single_run_from_the_plan_enumeration(self):
        """🔴 사고 재현 입력: PBS_ARRAY_INDEX=5. 수정 전에는 22태스크 전원이 전체
        tasks.tsv 를 돌았다(그리고 tsv 자체가 18줄로 예산 22태스크와 어긋났다).
        이제 태스크 5 는 plan._p5_runs()[4] 딱 하나만 돌린다 — 같은 열거."""
        runs = plan_mod._p5_runs()
        self.assertEqual(22, len(runs), "manifest 유도 실행 수가 바뀌었다")
        proc = self.run_payload(tid=5)
        self.assertEqual(0, proc.returncode, proc.stdout[-1500:] + proc.stderr[-800:])
        expect = runs[4]
        tag = "%s_s%d_L%d" % (expect["id"], expect["seed"], expect["level"])
        species = os.listdir(os.path.join(self.job_dir, "species"))
        self.assertEqual([tag], species,
                         "task 5 의 실행이 plan 열거와 다르다: %s != [%s]" % (species, tag))
        rec = json.load(open(os.path.join(self.job_dir, "p5_task_results.t5.json")))
        self.assertEqual(5, rec["task_id"])
        self.assertEqual(1, len(rec["rows"]))
        self.assertEqual(expect["id"], rec["rows"][0]["id"])

    def test_out_of_range_index_fails_loudly(self):
        proc = self.run_payload(tid=23)
        self.assertEqual(5, proc.returncode)
        self.assertIn("어긋났다", proc.stdout + proc.stderr)

    def test_two_tasks_write_disjoint_outputs_and_collector_merges_them(self):
        self.run_payload(tid=1)
        self.run_payload(tid=2)
        files = os.listdir(self.job_dir)
        self.assertIn("p5_task_results.t1.json", files)
        self.assertIn("p5_task_results.t2.json", files)
        self.assertNotIn("p5_results.json", files,
                         "array 태스크가 고정 경로 집계 파일을 썼다 — 사고의 형태 그대로")
        merged = collect_mod._merge_p5_task_results(self.job_dir)
        self.assertEqual(2, len(merged["rows"]))
        ids = sorted(r["id"] for r in merged["rows"])
        runs = plan_mod._p5_runs()
        self.assertEqual(sorted([runs[0]["id"], runs[1]["id"]]), ids)


class TestStoreTaskAggregation(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_agg_")
        self.addCleanup(shutil.rmtree, self.d, True)
        self.store = Store(self.d)

    def _submit(self, key, n_tasks):
        self.store.mark_submitted(key, {"n_tasks": n_tasks})

    def _task_marker(self, key, tid, kind):
        if kind == "done":
            self.store.mark_done("%s.t%d" % (key, tid),
                                 {"start_epoch": 0, "end_epoch": 60, "rc": 0})
        else:
            self.store.mark_failed("%s.t%d" % (key, tid), "payload_nonzero_exit")

    def test_done_requires_all_tasks(self):
        self._submit("P5", 3)
        self._task_marker("P5", 1, "done")
        self._task_marker("P5", 2, "done")
        self.assertFalse(self.store.is_done("P5"))
        self._task_marker("P5", 3, "done")
        self.assertTrue(self.store.is_done("P5"))

    def test_failed_only_when_every_task_is_terminal(self):
        """🔴 아직 도는 태스크가 있는데 failed 로 판정하면 cli 가 재제출해
        **돌고 있는 태스크와 이중 실행**된다 — 이번 라운드의 병 그대로."""
        self._submit("P1b", 3)
        self._task_marker("P1b", 1, "failed")
        self.assertFalse(self.store.is_failed("P1b"),
                         "태스크 2/3 이 종결되기 전에 failed 로 판정했다")
        self._task_marker("P1b", 2, "done")
        self._task_marker("P1b", 3, "done")
        self.assertTrue(self.store.is_failed("P1b"))

    def test_clear_failed_removes_task_failure_markers_too(self):
        self._submit("P1b", 2)
        self._task_marker("P1b", 1, "failed")
        self._task_marker("P1b", 2, "done")
        self.assertTrue(self.store.is_failed("P1b"))
        self.store.clear_failed("P1b")
        self.assertFalse(self.store.is_failed("P1b"))

    def test_job_status_aggregates_and_carries_the_span(self):
        self._submit("P5", 2)
        self.store.mark_done("P5.t1", {"start_epoch": 100, "end_epoch": 160})
        self.store.mark_done("P5.t2", {"start_epoch": 130, "end_epoch": 220})
        st, payload = collect_mod.job_status(self.store, "P5")
        self.assertEqual("done", st)
        self.assertTrue(payload["aggregated_from_task_markers"])
        self.assertEqual(100, payload["start_epoch"])
        self.assertEqual(220, payload["end_epoch"])

    def test_job_status_incomplete_while_a_task_is_missing(self):
        self._submit("P5", 3)
        self.store.mark_done("P5.t1", {"start_epoch": 0, "end_epoch": 1})
        st, payload = collect_mod.job_status(self.store, "P5")
        self.assertEqual("incomplete", st)
        self.assertEqual(1, payload["n_tasks_done"])


class TestExecutionAuditCatchesTheIncident(unittest.TestCase):
    """[A-2] 실제 회신의 executions.jsonl 형태(P1b: 같은 logical, 3 hosts, finish 0줄)를
    그대로 넣는다. 수정 전 execution_audit 는 stage 중복만 봐서
    `duplicate_execution: false` 로 회신했다 — 그 침묵이 사고를 감사에서 숨겼다."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_aud_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _write_execs(self, lines):
        with open(os.path.join(self.d, "executions.jsonl"), "w") as fh:
            for l in lines:
                fh.write(json.dumps(l) + "\n")

    def test_same_logical_on_multiple_hosts_raises_a_warning_without_stage_events(self):
        # 실측 재현: jobs/P1b/executions.jsonl 의 3줄 (epoch/host 실값)
        self._write_execs([
            {"link": "P1b", "logical": "P1b", "action": "run",
             "epoch": 1787127429, "host": "node2661", "cores": 64},
            {"link": "P1b", "logical": "P1b", "action": "run",
             "epoch": 1787127473, "host": "node2660", "cores": 64},
            {"link": "P1b", "logical": "P1b", "action": "run",
             "epoch": 1787127473, "host": "node2662", "cores": 64},
        ])
        audit = collect_mod.execution_audit(self.d)
        self.assertIn("P1b", audit["concurrent_logical_runs"])
        self.assertEqual(3, audit["concurrent_logical_runs"]["P1b"]["n_run_lines"])
        self.assertTrue(any("concurrent_execution" in w for w in audit["warnings"]),
                        "서로 다른 host 의 같은 logical run 이 경고 없이 지나갔다")
        self.assertEqual(3, audit["n_runs_without_finish"])

    def test_distinct_task_keys_do_not_false_positive(self):
        """수정 후의 정상 array 실행(태스크별 키)은 경고를 내면 안 된다."""
        self._write_execs([
            {"link": "P5.t1", "logical": "P5.t1", "action": "run",
             "epoch": 100, "host": "node1", "cores": 64},
            {"link": "P5.t2", "logical": "P5.t2", "action": "run",
             "epoch": 100, "host": "node2", "cores": 64},
            {"link": "P5.t1", "logical": "P5.t1", "action": "finish",
             "epoch": 200, "rc": 0},
            {"link": "P5.t2", "logical": "P5.t2", "action": "finish",
             "epoch": 220, "rc": 0},
        ])
        audit = collect_mod.execution_audit(self.d)
        self.assertEqual({}, audit["concurrent_logical_runs"])
        self.assertFalse(any("concurrent_execution" in w for w in audit["warnings"]))

    def test_sequential_chain_resume_on_one_host_does_not_warn(self):
        self._write_execs([
            {"link": "P1", "logical": "P1", "action": "run",
             "epoch": 100, "host": "node1", "cores": 64},
            {"link": "P1", "logical": "P1", "action": "finish", "epoch": 200, "rc": 1},
            {"link": "P1_c1", "logical": "P1", "action": "run",
             "epoch": 300, "host": "node1", "cores": 64},
            {"link": "P1_c1", "logical": "P1", "action": "finish", "epoch": 400, "rc": 0},
        ])
        audit = collect_mod.execution_audit(self.d)
        self.assertEqual({}, audit["concurrent_logical_runs"])

    def test_sequential_chain_resume_on_a_different_host_does_not_warn(self):
        """[§6, critic9 재현 케이스] P1 이 nodeA 에서 실패하고 13.9시간 뒤 nodeB 에서
        P1_c1 로 재개 — 완전 비중첩. 수정 전에는 "다른 host 2회"만 보고 오탐했다.
        경고는 '다른 host' 가 아니라 **'동시'** 를 뜻해야 한다."""
        self._write_execs([
            {"link": "P1", "logical": "P1", "action": "run",
             "epoch": 100, "host": "nodeA", "cores": 64},
            {"link": "P1", "logical": "P1", "action": "finish", "epoch": 200, "rc": 1},
            {"link": "P1_c1", "logical": "P1", "action": "run",
             "epoch": 50000, "host": "nodeB", "cores": 64},
            {"link": "P1_c1", "logical": "P1", "action": "finish",
             "epoch": 50100, "rc": 0},
        ])
        audit = collect_mod.execution_audit(self.d)
        self.assertEqual({}, audit["concurrent_logical_runs"],
                         "비중첩 체인 재개가 concurrent 로 오탐됐다")
        self.assertFalse(any("concurrent_execution" in w for w in audit["warnings"]))

    def test_truly_overlapping_intervals_on_two_hosts_warn(self):
        """finish 가 있는 경우에도 구간이 실제로 겹치면 경고한다."""
        self._write_execs([
            {"link": "P5", "logical": "P5", "action": "run",
             "epoch": 100, "host": "node1", "cores": 64},
            {"link": "P5", "logical": "P5", "action": "run",
             "epoch": 150, "host": "node2", "cores": 64},
            {"link": "P5", "logical": "P5", "action": "finish", "epoch": 300, "rc": 0},
            {"link": "P5", "logical": "P5", "action": "finish", "epoch": 320, "rc": 0},
        ])
        audit = collect_mod.execution_audit(self.d)
        self.assertIn("P5", audit["concurrent_logical_runs"])
        self.assertTrue(any("concurrent_execution" in w for w in audit["warnings"]))


class TestCoreHoursFloor(unittest.TestCase):
    """[A-3] P1b 회신은 core_hours_total=322.1 을 실었지만 실소모 하한은
    3태스크 × 64코어 × 4.92h = 944 core-h 였다 — stage 마커 공유·덮어쓰기 때문."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_chf_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _audit_with_three_finished_tasks(self):
        wall_s = int(4.92 * 3600)
        lines = []
        for i, host in enumerate(("node2660", "node2661", "node2662"), start=1):
            lines.append({"link": "P1b.t%d" % i, "logical": "P1b.t%d" % i,
                          "action": "run", "epoch": 1000, "host": host, "cores": 64})
            lines.append({"link": "P1b.t%d" % i, "logical": "P1b.t%d" % i,
                          "action": "finish", "epoch": 1000 + wall_s, "rc": 0})
        with open(os.path.join(self.d, "executions.jsonl"), "w") as fh:
            for l in lines:
                fh.write(json.dumps(l) + "\n")
        return collect_mod.execution_audit(self.d)

    def test_floor_reproduces_the_944_core_hours(self):
        audit = self._audit_with_three_finished_tasks()
        self.assertAlmostEqual(944.6, audit["core_hours_floor_from_executions"],
                               delta=1.0)
        self.assertEqual(0, audit["n_runs_without_finish"])

    def test_stage_total_below_the_floor_warns(self):
        audit = self._audit_with_three_finished_tasks()
        warns = collect_mod.core_hours_accounting_warnings(322.1, audit)
        self.assertTrue(any("core_hours_undercount" in w for w in warns),
                        "322.1 < 944 인데 경고가 없다 — 사고의 침묵 그대로")

    def test_healthy_totals_do_not_warn(self):
        audit = self._audit_with_three_finished_tasks()
        self.assertEqual([], collect_mod.core_hours_accounting_warnings(900.0, audit))

    def test_small_totals_with_normal_overhead_do_not_false_positive(self):
        """[critic9 MAJOR #3] total=2.0 에 정상 오버헤드 0.5 core-h → ratio 1.25 지만
        절대 갭이 작아(0.5 < 10) 오탐하지 않는다 — 비율 AND 갭 두 조건."""
        with open(os.path.join(self.d, "executions.jsonl"), "w") as fh:
            fh.write(json.dumps({"link": "P5.t1", "logical": "P5.t1",
                                 "action": "run", "epoch": 0,
                                 "host": "n1", "cores": 5}) + "\n")
            fh.write(json.dumps({"link": "P5.t1", "logical": "P5.t1",
                                 "action": "finish", "epoch": 1800,
                                 "rc": 0}) + "\n")   # 5코어 × 0.5h = 2.5 core-h
        audit = collect_mod.execution_audit(self.d)
        self.assertEqual([], collect_mod.core_hours_accounting_warnings(2.0, audit))

    def test_runs_without_finish_flag_incomplete_accounting(self):
        # 실측 재현: 이번 회신의 P1b 는 run 3줄, finish 0줄 (wall-kill)
        with open(os.path.join(self.d, "executions.jsonl"), "w") as fh:
            for host in ("node2660", "node2661", "node2662"):
                fh.write(json.dumps({"link": "P1b", "logical": "P1b",
                                     "action": "run", "epoch": 1000,
                                     "host": host, "cores": 64}) + "\n")
        audit = collect_mod.execution_audit(self.d)
        warns = collect_mod.core_hours_accounting_warnings(322.1, audit)
        self.assertTrue(any("core_hours_incomplete" in w for w in warns))


if __name__ == "__main__":
    unittest.main()
