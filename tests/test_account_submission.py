"""🔴 HPC 계정(`--account`) + 제출 사전검사 회귀 테스트.

lead 관측: **`--partition` 은 있는데 `--account` 가 없었다.** 대부분의 학술·국가 HPC는
`#SBATCH --account=<project>` 를 요구하고, 없으면 sbatch가 **모든 제출을 거부**한다.
⟹ CPU 패키지 10개 항목 **전부**가 시작조차 못 하고 왕복 1회(3.5일)가 통째로 날아간다.

🔴 그리고 **`--dry-run` 이 이걸 못 잡았다** — 소프트웨어 존재만 보고 스케줄러 수용 여부는
보지 않았기 때문이다. 왕복을 아끼려고 만든 장치가 정작 이 실패에는 무력했다.
그래서 `sbatch --test-only`(부작용 0) 사전검사를 넣었고, 이 파일이 그것을 고정한다.
"""

import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import budget, cli, plan
from sei_pilot import scheduler as sch
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

TEMPLATES = os.path.join(context.PKG_ROOT, "sei_pilot", "templates")
SINFO = "cpu*|1-00:00:00|400|257000|128\n"

ACCOUNT_ERROR = ("sbatch: error: Batch job submission failed: "
                 "Invalid account or account/partition combination specified")


def cluster(test_only_ok=True, accounts=("proj_a",), enforce="associations,limits",
            error=ACCOUNT_ERROR):
    def sbatch_test(_cmd):
        return (0, "sbatch: Job 12345 to start at ...\n", "") if test_only_ok \
            else (1, "", error)
    assoc = "\n".join("%s|cpu|normal|100|cpu=1000" % a for a in accounts)
    return FakeShell(
        responses={
            "hostname -f": (0, "login1\n", ""),
            "lscpu": (0, "CPU(s): 128\nSocket(s): 2\nCore(s) per socket: 32\n", ""),
            "free -b": (0, "Mem: 270000000000 1 2\n", ""),
            "sinfo -h -o %P|%l|%D|%m|%c": (0, SINFO, ""),
            "sinfo -h -o %P|%G": (0, "cpu*|(null)\n", ""),
            "scontrol show config": (0, "MaxArraySize = 1001\n"
                                        "AccountingStorageEnforce = %s\n" % enforce, ""),
            "sacctmgr": (0, assoc, ""),
            "sbatch --test-only": sbatch_test,
            "sbatch": (0, "999\n", ""),
            "df": (0, "F T 1 1 1 1 /s\n", ""), "curl": (0, "000", ""),
        },
        which_map={"sbatch": "/b/sbatch", "squeue": "/b/squeue", "orca": "/o",
                   "cp2k": "/c", "xtb": "/x", "python3": "/p"})


class TestJobSpecAccountFields(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_acct_")

    def tearDown(self):
        # 🔴 이 파일에는 tearDown 이 **하나도 없었다.** 테스트마다 임시 디렉터리를 하나씩
        #    남겨서, 스위트를 수백 번 돌리는 동안 `/tmp` 에 `sei_acct_*` 가 쌓였다.
        #    ⟹ 🔴 **`/tmp` 가 100% 차서 `make_package.sh` 의 스테이징 `cp` 가 실패하고
        #      빌드가 죽었다**("No space left on device"). 코드 결함이 아니라 **테스트가
        #      환경을 오염시켜 빌드를 막은** 형태다.
        #    ⚠ 그리고 그때 `dist/` 는 이미 `.stale.*` 로 옮겨진 뒤였다 — 빌드가 중간에
        #      죽으면 **인도본이 제자리에 없는 상태**가 된다(복구는 `.stale` 에서 하면 된다).
        shutil.rmtree(self.d, ignore_errors=True)

    def _spec(self, **kw):
        kw.setdefault("job_dir", self.d)
        return sch.JobSpec("P1", "true", nodes=1, cores_per_node=8, wall_h=1.0, **kw)

    def test_slurm_emits_account_line(self):
        a = sch.SlurmAdapter(FakeShell(), TEMPLATES)
        text = open(a.write_script(self._spec(account="proj_a"))).read()
        self.assertIn("#SBATCH --account=proj_a", text)

    def test_slurm_emits_qos_and_reservation(self):
        a = sch.SlurmAdapter(FakeShell(), TEMPLATES)
        text = open(a.write_script(self._spec(qos="normal",
                                              reservation="maint"))).read()
        self.assertIn("#SBATCH --qos=normal", text)
        self.assertIn("#SBATCH --reservation=maint", text)

    def test_absent_account_emits_no_line(self):
        """값이 없으면 줄 자체를 생략한다(빈 --account= 는 즉시 거부된다)."""
        a = sch.SlurmAdapter(FakeShell(), TEMPLATES)
        text = open(a.write_script(self._spec())).read()
        self.assertNotIn("--account", text)
        self.assertNotIn("--qos", text)

    def test_pbs_emits_account_line(self):
        a = sch.PbsAdapter(FakeShell(), TEMPLATES, flavor="pbspro")
        text = open(a.write_script(self._spec(account="proj_a"))).read()
        self.assertIn("#PBS -A proj_a", text)

    def test_chain_links_inherit_account(self):
        """체인 링크가 계정을 잃으면 2번째 링크부터 거부된다."""
        specs = []

        class Rec(sch.SlurmAdapter):
            def submit(self_inner, spec, deps=None):
                specs.append(spec)
                return "1"

        Rec(FakeShell(), TEMPLATES).submit_chain(
            self._spec(account="proj_a", qos="normal"), 3)
        self.assertEqual([s.account for s in specs], ["proj_a"] * 3)
        self.assertEqual([s.qos for s in specs], ["normal"] * 3)


class TestAccountDetection(unittest.TestCase):
    def _env(self, **kw):
        return cli.build_env(cluster(**kw), context.PKG_ROOT)

    def test_single_account_is_auto_selected(self):
        info = cli.account_candidates(self._env(accounts=("proj_a",)))
        self.assertEqual(info["accounts"], ["proj_a"])
        self.assertEqual(info["auto_selectable"], "proj_a")
        self.assertTrue(info["account_required"])

    def test_multiple_accounts_are_not_guessed(self):
        """🔴 여러 개면 **고르지 않는다** — 잘못 고르면 조용히 남의 예산을 쓴다."""
        info = cli.account_candidates(self._env(accounts=("proj_a", "proj_b")))
        self.assertEqual(sorted(info["accounts"]), ["proj_a", "proj_b"])
        self.assertIsNone(info["auto_selectable"])

    def test_enforcement_flag_is_read(self):
        self.assertTrue(cli.account_candidates(
            self._env(enforce="associations"))["account_required"])
        self.assertFalse(cli.account_candidates(
            self._env(enforce="none"))["account_required"])

    def test_cli_account_overrides_detection(self):
        args = cli.build_parser().parse_args(["preflight", "--account", "mine"])
        acct, _info = cli.resolve_account(args, self._env(accounts=("proj_a",)),
                                          verbose=False)
        self.assertEqual(acct, "mine")

    def test_resolve_returns_none_when_ambiguous(self):
        args = cli.build_parser().parse_args(["preflight"])
        acct, info = cli.resolve_account(args,
                                         self._env(accounts=("a", "b")),
                                         verbose=False)
        self.assertIsNone(acct)
        self.assertEqual(len(info["accounts"]), 2)


class TestSubmissionFeasibility(unittest.TestCase):
    """🔴 dry-run 이 '이 클러스터에서 실행 가능한가'를 **진짜로** 답하는지."""

    def _run(self, shell, account=None):
        d = tempfile.mkdtemp(prefix="sei_feas_")
        self.addCleanup(shutil.rmtree, d, True)   # 🔴 위와 같은 이유 — 정리하지 않으면 쌓인다
        argv = ["preflight", "--workdir", d, "--pkg-root", context.PKG_ROOT]
        if account:
            argv += ["--account", account]
        args = cli.build_parser().parse_args(argv)
        env = cli.build_env(shell, context.PKG_ROOT)
        planned, _s = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                      profile="cpu")
        return cli.submission_feasibility(args, shell, Store(d), env, planned,
                                          quiet=True)

    def test_rejection_is_detected_without_submitting(self):
        feas = self._run(cluster(test_only_ok=False))
        self.assertTrue(feas["checked"])
        self.assertGreater(feas["n_rejected"], 0)
        self.assertEqual(feas["n_ok"], 0)
        self.assertEqual(feas["results"][0]["method"], "sbatch --test-only")

    def test_remedy_text_tells_the_user_what_to_do(self):
        feas = self._run(cluster(test_only_ok=False))
        remedy = feas["results"][0]["remedy"]
        self.assertIn("--account", remedy)
        self.assertIn("sacctmgr", remedy)

    def test_partition_error_gets_its_own_remedy(self):
        feas = self._run(cluster(test_only_ok=False,
                                 error="sbatch: error: invalid partition specified"))
        self.assertIn("--partition", feas["results"][0]["remedy"])

    def test_acceptance_is_reported(self):
        feas = self._run(cluster(test_only_ok=True), account="proj_a")
        self.assertGreater(feas["n_ok"], 0)
        self.assertEqual(feas["n_rejected"], 0)
        self.assertEqual(feas["account_used"], "proj_a")

    def test_no_scheduler_skips_the_check_honestly(self):
        feas = self._run(FakeShell(responses={"hostname -f": (0, "wsl\n", "")}))
        self.assertFalse(feas["checked"])
        self.assertIn("스케줄러", feas["reason"])

    def test_test_only_never_actually_submits(self):
        """🔴 사전검사가 진짜 잡을 던지면 그 자체가 사고다."""
        sh = cluster(test_only_ok=True)
        self._run(sh, account="proj_a")
        real = [c for c in sh.log
                if str(c["cmd"]).startswith("sbatch") and "--test-only" not in str(c["cmd"])]
        self.assertEqual(real, [], "사전검사가 실제 sbatch 를 호출했다: %s" % real)

    def test_render_shows_a_loud_warning_block(self):
        feas = self._run(cluster(test_only_ok=False))
        text = "\n".join(cli.format_feasibility(feas))
        self.assertIn("스케줄러가 거부했다", text)
        self.assertIn("지금 제출하면 전부 실패한다", text)

    def test_render_is_quiet_when_everything_is_fine(self):
        feas = self._run(cluster(test_only_ok=True), account="proj_a")
        text = "\n".join(cli.format_feasibility(feas))
        self.assertNotIn("거부했다", text)
        self.assertIn("수용", text)


class TestUserDocs(unittest.TestCase):
    def test_cpu_readme_explains_multi_node_hpc_and_account(self):
        with open(os.path.join(context.PKG_ROOT, "README_USER.cpu.md")) as fh:
            text = fh.read()
        self.assertIn("--account", text)
        self.assertIn("로그인 노드", text)
        self.assertIn("--dry-run", text)


if __name__ == "__main__":
    unittest.main()
