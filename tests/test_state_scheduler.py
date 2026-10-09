"""멱등 재개(마커) + 스케줄러 어댑터 테스트.

🔴 우리 환경에는 SLURM/PBS가 없다(ADR-004). 따라서 실제 제출은 FakeShell로만
검증할 수 있다. 여기서 검증하는 것은 **우리가 만든 인자와 스크립트가 옳은가**이지
"스케줄러가 그것을 받아들이는가"가 아니다. 후자는 클러스터에서만 검증된다.
"""

import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import scheduler as sch
from sei_pilot import state
from sei_pilot.shellrun import FakeShell

TEMPLATES = os.path.join(context.PKG_ROOT, "sei_pilot", "templates")


class TestStore(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_test_")
        self.store = state.Store(self.d)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_markers_and_idempotency(self):
        self.assertFalse(self.store.is_done("P1"))
        self.store.mark_submitted("P1", {"job_ids": ["1"]})
        self.assertTrue(self.store.is_submitted("P1"))
        self.assertFalse(self.store.is_done("P1"))
        self.store.mark_done("P1", {"start_epoch": 1, "end_epoch": 2})
        self.assertTrue(self.store.is_done("P1"))
        # 재실행: 마커가 남아 있으므로 건너뛴다
        store2 = state.Store(self.d)
        self.assertTrue(store2.is_done("P1"))

    def test_failure_recorded_and_cleared_on_success(self):
        self.store.mark_failed("P2", "scf_failed", "SCF 발산", "log tail")
        self.assertTrue(self.store.is_failed("P2"))
        fails = self.store.all_failures()
        self.assertEqual(len(fails), 1)
        self.assertEqual(fails[0]["reason"], "scf_failed")
        self.store.mark_done("P2")
        self.assertFalse(self.store.is_failed("P2"))
        self.assertEqual(self.store.all_failures(), [])

    def test_run_counter(self):
        self.assertEqual(self.store.run_count, 0)
        self.assertEqual(self.store.bump_run_counter(), 1)
        self.assertEqual(self.store.bump_run_counter(), 2)
        self.assertEqual(self.store.run_count, 2)

    def test_atomic_claim(self):
        p = os.path.join(self.d, "claim.lock")
        self.assertTrue(state.claim(p))
        self.assertFalse(state.claim(p))     # 두 번째 워커는 못 집는다

    def test_write_result_is_valid_json(self):
        import json
        path = self.store.write_result("x.json", {"a": 1})
        with open(path) as fh:
            self.assertEqual(json.load(fh)["a"], 1)

    def test_corrupt_marker_does_not_raise(self):
        with open(os.path.join(self.store.state_dir, "X.done.json"), "w") as fh:
            fh.write("{ not json")
        self.assertTrue(self.store.is_done("X"))
        self.assertIsNone(self.store.read_marker("X", "done"))


class TestDetection(unittest.TestCase):
    def test_detect_slurm(self):
        sh = FakeShell(which_map={"sbatch": "/usr/bin/sbatch", "squeue": "/usr/bin/squeue"})
        self.assertEqual(sch.detect(sh), sch.SLURM)

    def test_detect_pbs(self):
        sh = FakeShell(which_map={"qsub": "/usr/bin/qsub"})
        self.assertEqual(sch.detect(sh), sch.PBS)

    def test_detect_none(self):
        self.assertEqual(sch.detect(FakeShell()), sch.NONE)

    def test_slurm_preferred_over_pbs(self):
        sh = FakeShell(which_map={"sbatch": "s", "squeue": "q", "qsub": "p"})
        self.assertEqual(sch.detect(sh), sch.SLURM)

    def test_pbs_flavor(self):
        sh = FakeShell(responses={"qstat --version": (0, "pbs_version = 19.0.0", "")})
        self.assertEqual(sch.detect_pbs_flavor(sh), "pbspro")
        sh2 = FakeShell(responses={"qstat --version": (0, "Version: 6.1.2 torque", "")})
        self.assertEqual(sch.detect_pbs_flavor(sh2), "torque")


class TestJobIdParsing(unittest.TestCase):
    def test_slurm_parsable(self):
        self.assertEqual(sch.parse_slurm_jobid("12345\n"), "12345")
        self.assertEqual(sch.parse_slurm_jobid("12345;cluster\n"), "12345")

    def test_slurm_legacy(self):
        self.assertEqual(sch.parse_slurm_jobid("Submitted batch job 998877"), "998877")

    def test_slurm_garbage(self):
        self.assertIsNone(sch.parse_slurm_jobid("error: invalid partition"))
        self.assertIsNone(sch.parse_slurm_jobid(""))

    def test_pbs(self):
        self.assertEqual(sch.parse_pbs_jobid("451.head\n"), "451.head")
        self.assertIsNone(sch.parse_pbs_jobid(" \n"))


class TestRendering(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_tmpl_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _spec(self, **kw):
        kw.setdefault("job_dir", self.d)
        return sch.JobSpec("P1", "bash payload/P1.sh", **kw)

    def test_wall_hms(self):
        self.assertEqual(self._spec(wall_h=1.5).wall_hms(), "01:30:00")
        self.assertEqual(self._spec(wall_h=1 / 60.0).wall_hms(), "00:01:00")
        self.assertEqual(self._spec(wall_h=24).wall_hms(), "24:00:00")

    def test_no_unsubstituted_tokens_slurm(self):
        a = sch.SlurmAdapter(FakeShell(), TEMPLATES)
        path = a.write_script(self._spec(nodes=2, cores_per_node=64, wall_h=3,
                                         partition="cpu"))
        text = open(path).read()
        self.assertNotIn("{{", text)
        self.assertIn("#SBATCH --nodes=2", text)
        self.assertIn("#SBATCH --ntasks-per-node=64", text)
        self.assertIn("#SBATCH --time=03:00:00", text)
        self.assertIn("#SBATCH --partition=cpu", text)
        self.assertIn("sei_job_main bash", text)

    def test_command_with_and_operator_goes_to_cmd_file(self):
        """`A && B` 를 템플릿에 직접 박으면 B가 계측 밖에서 돈다 — 실제로 났던 버그."""
        a = sch.SlurmAdapter(FakeShell(), TEMPLATES)
        spec = sch.JobSpec("collector", "cd /x && python3 -m sei_pilot.cli collect",
                           job_dir=self.d)
        path = a.write_script(spec)
        text = open(path).read()
        self.assertNotIn("&&", text)
        cmd = open(os.path.join(self.d, "collector.cmd.sh")).read()
        self.assertIn("&&", cmd)

    def test_array_and_gpu_lines(self):
        a = sch.SlurmAdapter(FakeShell(), TEMPLATES)
        text = open(a.write_script(self._spec(array=(1, 200), gpus=1))).read()
        self.assertIn("#SBATCH --array=1-200", text)
        self.assertIn("#SBATCH --gres=gpu:1", text)

    def test_pbs_flavors(self):
        pro = sch.PbsAdapter(FakeShell(), TEMPLATES, flavor="pbspro")
        text = open(pro.write_script(self._spec(nodes=2, cores_per_node=32))).read()
        self.assertIn("select=2:ncpus=32", text)
        tor = sch.PbsAdapter(FakeShell(), TEMPLATES, flavor="torque")
        text = open(tor.write_script(self._spec(nodes=2, cores_per_node=32))).read()
        self.assertIn("nodes=2:ppn=32", text)

    def test_render_raises_on_missing_token(self):
        self.assertRaises(ValueError, sch.render_script, "hello {{NOPE}}", self._spec())


class TestSubmission(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_sub_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _slurm(self, ids=("101", "102", "103", "104")):
        self.counter = {"n": 0}

        def responder(cmd):
            i = self.counter["n"]
            self.counter["n"] += 1
            return (0, ids[min(i, len(ids) - 1)] + "\n", "")
        sh = FakeShell(responses={"sbatch": responder})
        return sh, sch.SlurmAdapter(sh, TEMPLATES)

    def test_submit_returns_jobid(self):
        sh, a = self._slurm()
        jid = a.submit(sch.JobSpec("P1", "true", job_dir=self.d))
        self.assertEqual(jid, "101")

    def test_dependency_flag_is_afterany(self):
        sh, a = self._slurm()
        args = a.submit_args("/tmp/x.sbatch", deps=["11", "22"])
        self.assertIn("--dependency=afterany:11:22", args)
        self.assertIn("--parsable", args)

    def test_submit_chain_links_each_to_previous(self):
        """§R2-6 D-4: wall 초과 예상 잡은 제출 시점에 체인을 미리 건다."""
        sh, a = self._slurm()
        ids = a.submit_chain(sch.JobSpec("P1", "true", job_dir=self.d), 3)
        self.assertEqual(ids, ["101", "102", "103"])
        deps = [c["cmd"] for c in sh.log]
        self.assertNotIn("--dependency", deps[0])
        self.assertIn("--dependency=afterany:101", deps[1])
        self.assertIn("--dependency=afterany:102", deps[2])

    def test_submit_failure_returns_none(self):
        sh = FakeShell(responses={"sbatch": (1, "", "sbatch: error: invalid partition")})
        a = sch.SlurmAdapter(sh, TEMPLATES)
        self.assertIsNone(a.submit(sch.JobSpec("P1", "true", job_dir=self.d)))

    def test_local_adapter_queues_in_order(self):
        sh = FakeShell()
        a = sch.LocalAdapter(sh, TEMPLATES, workdir=self.d)
        j1 = a.submit(sch.JobSpec("A", "true", job_dir=os.path.join(self.d, "A")))
        j2 = a.submit(sch.JobSpec("B", "true", job_dir=os.path.join(self.d, "B")))
        self.assertEqual([j1, j2], ["local-1", "local-2"])
        queue = open(os.path.join(self.d, "state", "local_queue")).read().splitlines()
        self.assertEqual(len(queue), 2)
        self.assertTrue(queue[0].endswith("A.sh"))
        self.assertFalse(a.supports_dependency)   # 순차 실행이 의존성을 대신한다


if __name__ == "__main__":
    unittest.main()
