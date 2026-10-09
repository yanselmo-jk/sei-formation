"""`probe_throughput` 의 hostname 이 **회신 JSON 까지 도달하는가** — 조립선 전 구간.

🔴 이 파일이 생긴 이유 (ADR-041 의 세 번째 사례):
    `payload/probe_throughput.sh` 는 task 마다 `{"host": "$(hostname)"}` 를 **처음부터
    남기고 있었다.** 그런데 `collect_throughput()` 이 `start_epoch`/`end_epoch` 만 꺼내고
    **`host` 를 읽고 버렸다.** 그래서 실클러스터 회신 JSON 에 host 가 한 글자도 없었고,
    그것을 본 사람이 *"측정이 안 됐다"* 고 읽었다.
    **부품(payload)은 맞았고 조립선(collector)이 값을 떨어뜨렸다** — B-3(Gaussian 파서는
    맞는데 collect 가 ORCA 파서를 부름), `to_dict()` 400자 컷과 **같은 형태**다.
    크래시도 없었고 회신 JSON 도 정상 형태였다. **조용히 틀리는 부류다.**

🔴 그래서 이 테스트는 **부품에서 시작하지 않는다**(ADR-041):
    진짜 payload 스크립트 실행  →  `cli.cmd_collect`  →  **디스크에 쓰인 회신 JSON**
    을 열어서 확인한다. `probes.host_metrics()` 만 직접 부르는 테스트는 이 결함을
    **정의상 잡을 수 없다** — 그 함수는 그때도 맞았을 것이기 때문이다.

🔴 픽스처를 손으로 만들지 않는다(ADR-042 부수 규칙):
    `task_*.json` 을 파이썬으로 지어내면 **"내가 상상한 payload 출력"** 을 검증하게 된다.
    그래서 **패키지에 들어 있는 `payload/probe_throughput.sh` 를 그대로 실행**한다.
    바꾸는 것은 스크립트가 아니라 **환경**뿐이다:
      * `sleep`    → 즉시 반환 (스크립트의 `sleep 60` 을 60초 기다리지 않으려고)
      * `hostname` → 우리가 지정한 이름 (여러 노드에 흩어진 상황을 만들려고)
    둘 다 PATH 앞단의 shim 이다. **스크립트 본문은 인도본 그대로다.**
"""

import json
import os
import shutil
import stat
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import cli, probes
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

PAYLOAD = os.path.join(context.PKG_ROOT, "payload", "probe_throughput.sh")


def _shim(bin_dir, name, body):
    path = os.path.join(bin_dir, name)
    with open(path, "w") as fh:
        fh.write("#!/bin/sh\n" + body + "\n")
    os.chmod(path, os.stat(path).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return path


def run_real_payload(job_dir, task_id, host):
    """**인도본 `probe_throughput.sh` 를 실제로 실행한다.**

    반환: 그 task 가 남긴 `starts/task_<id>.json` 경로.
    스크립트를 수정하지 않고 `sleep`/`hostname` 만 PATH shim 으로 갈아끼운다.
    """
    bin_dir = tempfile.mkdtemp(prefix="sei_shim_")
    try:
        _shim(bin_dir, "sleep", "exit 0")
        _shim(bin_dir, "hostname", 'printf "%s\\n" "$SEI_TEST_FAKE_HOST"')
        env = dict(os.environ)
        env["PATH"] = bin_dir + os.pathsep + env.get("PATH", "")
        env["SEI_JOB_DIR"] = job_dir
        env["PBS_ARRAY_INDEX"] = str(task_id)
        env["SEI_TEST_FAKE_HOST"] = host
        env.pop("SLURM_ARRAY_TASK_ID", None)
        proc = subprocess.Popen(["bash", PAYLOAD], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = proc.communicate()
        if proc.returncode != 0:
            raise AssertionError("payload rc=%s\nstdout=%s\nstderr=%s"
                                 % (proc.returncode, out, err))
        return os.path.join(job_dir, "starts", "task_%s.json" % task_id)
    finally:
        shutil.rmtree(bin_dir, ignore_errors=True)


class TestRealPayloadRecordsHost(unittest.TestCase):
    """먼저 확인: **payload 는 원래부터 host 를 남긴다.** 결함은 그 뒤에 있었다."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_thr_pl_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_payload_writes_host_into_task_json(self):
        path = run_real_payload(self.d, 7, "node0510")
        rec = json.load(open(path))
        self.assertEqual(rec["host"], "node0510")
        self.assertEqual(rec["task_id"], "7")
        # 시각도 함께 남는다 — 집계기가 예전에 **이것만** 꺼냈다.
        self.assertTrue(rec["start_epoch"])
        self.assertTrue(rec["end_epoch"])


class TestHostReachesTheReportJson(unittest.TestCase):
    """🔴 본 회귀 테스트. 진입점(`cmd_collect`) → 디스크의 회신 JSON."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_thr_rep_")
        self.store = Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run_tasks(self, hosts):
        jd = self.store.job_dir("probe_throughput")
        for i, h in enumerate(hosts, start=1):
            run_real_payload(jd, i, h)

    def _collect(self):
        # 🔴 args 는 진짜 파서로, env 는 진짜 `build_env` 로 만든다(ADR-042 부수 규칙).
        #    가짜인 것은 **셸뿐**이다 — 우리 박스에는 스케줄러가 없고, 실제 셸을 쓰면
        #    curl 타임아웃 등으로 테스트가 수십 초 느려진다.
        args = cli.build_parser().parse_args(
            ["collect", "--workdir", self.d, "--pkg-root", context.PKG_ROOT])
        shell = FakeShell(responses={"hostname -f": (0, "testbox\n", "")},
                          which_map={})
        path = cli.cmd_collect(args, shell=shell, store=Store(self.d))
        with open(path) as fh:
            return json.load(fh)["throughput_probe"]

    def test_unique_hosts_reach_the_delivered_report(self):
        """🔴 이것이 실클러스터에서 잃어버린 바로 그 값이다."""
        self._run_tasks(["node0510", "node0514", "node0513"])
        tp = self._collect()
        # 🔴 먼저 **존재**를 단언한다. 없으면 KeyError(ERROR) 대신 FAIL 로 보고되게 하기
        #    위해서다 — ADR-042(a): ERROR 는 대개 실험이 잘못된 것이라 증거로 약하다.
        for field in ("n_hosts", "hosts_unique", "hosts_histogram"):
            self.assertIn(field, tp,
                          "회신 JSON 의 throughput_probe 에 %s 가 없다 — 집계기가 "
                          "payload 의 host 를 또 떨어뜨렸다" % field)
        self.assertEqual(tp["n_hosts"], 3)
        self.assertEqual(tp["hosts_unique"], ["node0510", "node0513", "node0514"])
        self.assertEqual(tp["tasks_with_host"], 3)
        self.assertEqual(tp["tasks_without_host"], 0)

    def test_packing_is_visible_not_hidden(self):
        """🔴 두 해석의 차이가 봉투 50배다: 8 task 가 2 노드면 **팩킹된 것**이다.

        유니크 수만 싣고 히스토그램을 빼면 "8 task 중 2 노드"인지 "2 task 만 돌았는지"를
        구분할 수 없다. 그래서 분포까지 싣는다.
        """
        self._run_tasks(["nodeA"] * 5 + ["nodeB"] * 3)
        tp = self._collect()
        self.assertEqual(tp["n_hosts"], 2)
        self.assertEqual(tp["hosts_histogram"], {"nodeA": 5, "nodeB": 3})
        self.assertEqual(tp["tasks_per_host_max"], 5)
        self.assertEqual(sum(tp["hosts_histogram"].values()), tp["tasks_with_host"])

    def test_n_hosts_is_null_not_zero_when_never_measured(self):
        """ADR-036: 폴백은 `0` 이 아니라 `null` 이다.

        `0` 이면 **코드가** "노드를 0대 받았다"로 읽는다. 경고는 사람만 읽지만
        `null` 은 코드도 읽는다.
        """
        tp = self._collect()                      # task 로그가 하나도 없음
        self.assertIsNone(tp["n_hosts"])
        self.assertNotEqual(tp["n_hosts"], 0)
        self.assertIn("미측정", tp["hosts_note"])

    def test_unknown_host_is_not_counted_as_a_node(self):
        """payload 는 `hostname` 이 실패하면 `unknown` 을 적는다. 그건 노드 이름이 아니다."""
        jd = self.store.job_dir("probe_throughput")
        run_real_payload(jd, 1, "node0510")
        # hostname 이 실패하는 노드를 흉내낸다 (payload 의 `|| echo unknown` 경로).
        run_real_payload(jd, 2, "unknown")
        tp = self._collect()
        self.assertEqual(tp["n_hosts"], 1)
        self.assertEqual(tp["hosts_unique"], ["node0510"])
        self.assertEqual(tp["tasks_with_host"], 1)
        self.assertEqual(tp["tasks_without_host"], 1,
                         "이름을 못 얻은 task 가 조용히 사라지면 안 된다")

    def test_existing_timing_metrics_still_work(self):
        """🔴 값 변화의 범위를 못 박는다: host 를 더한 것이지 기존 계량을 바꾼 것이 아니다."""
        self._run_tasks(["nodeA", "nodeB"])
        tp = self._collect()
        self.assertEqual(tp["jobs_started"], 2)
        self.assertEqual(tp["jobs_finished"], 2)
        self.assertIsNotNone(tp["max_concurrent_observed"])

    def test_note_does_not_overclaim_a_standing_allocation(self):
        """🔴 이 값은 '그 순간 점유'이지 '상시 확보'가 아니다. 그 단서가 회신에 실려야 한다.

        engineer §R21.4(c) 가 붙인 단서이고, 빠지면 다음 라운드에서 `n_hosts` 가
        `n_nodes` 상한으로 승격돼 인용된다 — ADR-034 가 막으려는 바로 그 사고다.
        """
        self._run_tasks(["nodeA", "nodeB"])
        note = self._collect()["hosts_note"]
        self.assertIn("하한", note)
        self.assertIn("보장이 아니다", note)


class TestHostMetricsUnitBehaviour(unittest.TestCase):
    """부품 단위 확인. 🔴 위 진입점 테스트를 **대체하지 않는다**(ADR-041 규칙 2)."""

    def test_empty_input_reports_absence_not_zero(self):
        m = probes.host_metrics([], n_tasks=0)
        self.assertIsNone(m["n_hosts"])
        self.assertEqual(m["hosts_unique"], [])

    def test_missing_host_field_counted_as_without_host(self):
        m = probes.host_metrics([None, "nodeA"], n_tasks=2)
        self.assertEqual(m["n_hosts"], 1)
        self.assertEqual(m["tasks_without_host"], 1)


if __name__ == "__main__":
    unittest.main()
