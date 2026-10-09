"""계획 수립 / 제출 / 수집 / 회신 JSON — 가짜 SLURM 클러스터 위 end-to-end.

🔴 우리 박스에는 스케줄러도 QC 코드도 GPU도 없다(ADR-004). 그래서 클러스터를
FakeShell로 **모사**한다. 여기서 검증되는 것:
  * 소프트웨어 유무에 따른 조건부 자기 생략(graceful skip)이 맞는가
  * 예산 가드가 어떤 항목을 어떤 순서로 자르는가 (2,000 vs 4,000)
  * 멱등 재제출이 실제로 건너뛰는가
  * 회신 JSON이 §R2-6 스키마를 만족하는가
검증되지 **않는** 것: sbatch가 우리 스크립트를 실제로 받아들이는가.
"""

import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import budget, cli, plan, report
from sei_pilot import scheduler as sch
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

SINFO = "cpu*|1-00:00:00|400|257000|128\ndebug|30:00|4|257000|128\n"
LSCPU = ("CPU(s):                  128\nThread(s) per core:      2\n"
         "Core(s) per socket:      32\nSocket(s):               2\n"
         "Model name:              AMD EPYC 7543\n")
SCONTROL = "MaxArraySize            = 1001\nMaxJobCount             = 20000\n"
DF = ("Filesystem Type 1-blocks Used Available Capacity Mounted on\n"
      "srv:/l lustre 1000000000000000 1 900000000000000 1% /scratch\n")


def fake_cluster(with_cp2k=True, with_xtb=True, with_orca=True, with_gpu=False):
    which = {"sbatch": "/usr/bin/sbatch", "squeue": "/usr/bin/squeue",
             "python3": "/usr/bin/python3", "curl": "/usr/bin/curl"}
    if with_cp2k:
        which["cp2k.psmp"] = "/opt/cp2k/cp2k.psmp"
    if with_xtb:
        which["xtb"] = "/opt/xtb/xtb"
    if with_orca:
        which["orca"] = "/opt/orca/orca"
    if with_gpu:
        which["nvidia-smi"] = "/usr/bin/nvidia-smi"

    responses = {
        "hostname -f": (0, "login1.cluster.example\n", ""),
        # 제출 사전검사(부작용 없음). 실제 sbatch 와 구분해 둔다.
        "sbatch --test-only": (0, "sbatch: Job 1 to start at ...\n", ""),
        "sacctmgr": (0, "proj_a|cpu|normal|100|cpu=1000\n", ""),
        "lscpu": (0, LSCPU, ""),
        "free -b": (0, "Mem: 270000000000 1 2\n", ""),
        "sinfo -h -o %P|%l|%D|%m|%c": (0, SINFO, ""),
        "sinfo -h -o %P|%G": (0, "cpu*|(null)\n", ""),
        "scontrol show config": (0, SCONTROL, ""),
        "df": (0, DF, ""),
        "sbatch": (0, "12345\n", ""),
        "curl": (0, "000", ""),          # air-gapped: outbound 실패
        "getent hosts": (1, "", ""),
    }
    # module avail 은 실제로 설치된 것만 보여준다 (모듈 fallback 경로 검증용)
    mods = []
    if with_cp2k:
        mods.append("cp2k/2024.1")
    if with_orca:
        mods.append("orca/6.0.0")
    responses["bash -lc 'module avail"] = (0, "", " ".join(mods) + "\n")
    if with_gpu:
        responses["nvidia-smi --query-gpu"] = (0, "NVIDIA H100 80GB HBM3, 81559 MiB\n", "")
        responses["sinfo -h -o %P|%G"] = (0, "cpu*|(null)\ngpu|gpu:h100:4\n", "")
    return FakeShell(responses=responses, which_map=which, paths=["/scratch"])


def make_args(workdir, max_core_hours=2000.0):
    return cli.build_parser().parse_args(
        ["preflight", "--workdir", workdir, "--pkg-root", context.PKG_ROOT,
         "--max-core-hours", str(max_core_hours)])


def make_gpu_args(workdir):
    return cli.build_parser().parse_args(
        ["preflight", "--workdir", workdir, "--pkg-root", context.PKG_ROOT,
         "--profile", "gpu"])


class TestJobSizing(unittest.TestCase):
    def test_wall_derived_from_budget(self):
        """🔴 core-h 예산에서 wall을 역산 → 스케줄러가 상한을 물리적으로 강제한다."""
        wall, links, reserved = plan.size_job(1000.0, cores_per_node=128,
                                              nodes=1, max_wall_h=24)
        self.assertAlmostEqual(wall, 1000.0 / 128, places=3)
        self.assertEqual(links, 1)
        self.assertAlmostEqual(reserved, 1000.0, places=1)

    def test_chain_when_wall_capped(self):
        """작은 노드(16코어)에서는 24 h로도 예산을 못 쓰므로 체인이 걸린다."""
        wall, links, reserved = plan.size_job(1000.0, cores_per_node=16,
                                              nodes=1, max_wall_h=24)
        self.assertAlmostEqual(wall, 24.0)
        self.assertEqual(links, 3)                 # 16*24=384 -> 3 링크
        self.assertAlmostEqual(reserved, 1152.0)   # 예약은 실제 최대 소비량으로 잡는다

    def test_min_wall_floor(self):
        wall, links, reserved = plan.size_job(1.0, 128, 1, 24)
        self.assertAlmostEqual(wall, plan.MIN_WALL_H)

    def test_zero_budget_item(self):
        wall, links, reserved = plan.size_job(0.0, 128, 1, 24)
        self.assertEqual(reserved, 0.0)


class TestPlanning(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_plan_")
        self.shell = fake_cluster()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _plan(self, max_core_hours=2000.0, profile="cpu", **cluster_kw):  # noqa: D401
        shell = fake_cluster(**cluster_kw) if cluster_kw else self.shell
        env = cli.build_env(shell, context.PKG_ROOT)
        g = budget.ResourceGuard(max_core_hours=max_core_hours,
                                 max_gpu_hours=4.0)
        planned, summary = plan.build_plan(env, g, profile=profile)
        return env, {p["key"]: p for p in planned}, summary, g

    def test_env_detection(self):
        env, _p, _s, _g = self._plan()
        self.assertEqual(env["scheduler"], sch.SLURM)
        self.assertEqual(env["cores_per_node"], 128)
        self.assertAlmostEqual(env["partition_max_wall_h"], 24.0)

    def test_full_stack_present_runs_core_pilots(self):
        """승인 예산(21,000 [물리 천장])에서는 모든 핵심 항목이 계획된다.

        🔒 의도된 변화 (§R24.1): 5,000 → 21,000. 사유: "§R21 KNL 판명(κ=3.4~6.8)에 따른
        재산정. 종전 값은 κ=1 단위였다." 21,000 은 **소비 전망(16,486)이 아니라 천장**이다.
        """
        _env, items, _s, _g = self._plan(21000.0)
        for key in ("probe_node", "probe_throughput", "probe_queuewait",
                    "P1"):
            self.assertEqual(items[key]["status"], "planned", key)

    def test_guard_2000_cannot_fit_probes_plus_P1P2P3(self):
        """🔴 가드가 좁으면 P1(단가 스프레드를 줄이는 유일한 수단)이 밀려난다.

        P2 계열 제거로 총량이 줄었으므로 경계값도 함께 내려갔다. 지키려는 성질은
        같다: **좁은 가드에서 P1 이 생략되고, 승인 가드에서는 들어온다.**"""
        # 🔴 대상이 P1 에서 P1b 로 바뀌었다. P1 은 영구 제외되면서 refusal 비용
        #    (64 core-h)으로 sizing 됐고, 그래서 좁은 가드에서도 **밀려나지 않는다** —
        #    성질이 사라진 게 아니라 P1 이 더 이상 큰 항목이 아닌 것이다.
        #    이 라운드의 최대 항목은 P1b(5,328 core-h)이고, 지키려는 성질
        #    ("좁은 가드에서 큰 항목이 생략되고, 승인 가드에서는 들어온다")은 그대로다.
        _env, items, summary, _g = self._plan(800.0)
        self.assertEqual(items["P1b"]["status"], "skipped")
        self.assertIn("budget_guard", items["P1b"]["skip_reason"])
        _env2, items2, _s2, _g2 = self._plan(21000.0)
        self.assertEqual(items2["P1b"]["status"], "planned")

    def test_p1_is_no_longer_squeezed_out_because_it_is_no_longer_big(self):
        """🔴 위 테스트가 왜 P1b 로 옮겨졌는지를 성질로 고정한다. P1 은 영구 제외 상태이고
        refusal 비용으로만 sizing 돼 있어 800 core-h 가드에서도 들어온다.
        누군가 P1 을 다시 크게 만들면(= 제외를 되돌리면) 이 테스트가 RED 로 알린다."""
        _env, items, _summary, _g = self._plan(800.0)
        self.assertEqual(items["P1"]["status"], "planned")

    def test_missing_software_skips_with_reason_not_failure(self):
        # 🔒 가드는 재산정본(21,000 [물리 천장])을 쓴다 — 이 테스트가 보려는 것은
        #    **소프트웨어 부재로 인한 생략**이지 예산 부족이 아니다. 기본값(2,000)으로
        #    두면 P1 이 budget_guard 로 빠져서 **엉뚱한 이유로 통과/실패한다.**
        _env, items, _s, _g = self._plan(21000.0, with_cp2k=False, with_xtb=False)
        # 그러나 P1은 살아 있다 (부분 실패 격리)
        self.assertEqual(items["P1"]["status"], "planned")

    def test_bundled_xtb_still_wins_over_an_absent_cluster_xtb(self):
        """🔴 원래 이 테스트는 P3 로 이 성질을 지켰다. **ADR-049 로 P3 가 계획에서
        빠졌으므로(이미 측정됨) 성질 자체를 직접 검사한다** — 테스트를 지우지 않는다.

        지키는 것: 클러스터에 xtb 가 없어도 **동봉본이 이긴다.** 동봉 이유는
        재현성이고(우리가 검증한 6.7.1), 순서가 뒤집히면 조용히 다른 버전이 쓰인다.
        """
        shell = fake_cluster(with_xtb=False)
        env = cli.build_env(shell, context.PKG_ROOT)
        kind, detail = plan.resolve_tool(env, ["xtb"])
        self.assertEqual(kind, "vendored",
                         "클러스터에 xtb 가 없는데 동봉본이 선택되지 않았다: %s" % detail)

    def test_absent_everywhere_is_reported_not_silently_assumed(self):
        """동봉본까지 없으면 조용히 넘어가지 말고 **사유와 함께** 실패해야 한다."""
        shell = fake_cluster(with_xtb=False)
        env = cli.build_env(shell, context.PKG_ROOT)
        env["vendored"] = {}                  # 동봉본도 없는 상황
        kind, detail = plan.resolve_tool(env, ["xtb"])
        self.assertIsNone(kind)
        self.assertTrue(detail, "부재 사유가 비어 있다 — 왕복 하나를 더 쓰게 된다")

    def test_gpu_absent_skips_p4(self):
        _env, items, _s, _g = self._plan(profile="gpu")
        self.assertEqual(items["P4"]["status"], "skipped")
        self.assertIn("GPU", items["P4"]["skip_reason"])

    def test_gpu_present_runs_p4(self):
        _env, items, _s, _g = self._plan(profile="gpu", with_gpu=True)
        self.assertEqual(items["P4"]["status"], "planned")

    def test_guard_2000_drops_items_and_says_so(self):
        """가드로 잘린 항목은 조용히 사라지지 않는다 — 사유와 해결 명령이 함께 남는다."""
        _env, items, summary, g = self._plan(2000.0)
        self.assertLessEqual(summary["reserved_core_hours"], 2000.0)
        dropped = [d["id"] for d in summary["guard"]["skipped_for_budget"]]
        self.assertTrue(set(["P1", "P1b", "P5"]) & set(dropped))
        for key in dropped:
            self.assertIn("budget_guard", items[key]["skip_reason"])

    def test_guard_21000_runs_everything_on_the_approved_cluster_shape(self):
        """🔒 §R24.1 재산정본에서 CPU 프로파일 전체가 돈다 (P6 κ 앵커 포함).

        🔴 이 테스트가 지키는 것: **가드가 항목을 조용히 SKIP 하지 않는다.**
        재산정 중 실제로 P1b(가장 값진 측정)가 천장 초과로 소리 없이 빠지는 것을
        이 형태의 검사로 잡았다.

        ⚠ [MAJOR#1/C-8-2 이후] 전제 명시: "전부 돈다"는 **승인된 클러스터 형태
        (64 core/node, README SPEC-BLOCK 의 전제)** 위의 사실이다. 이 파일의 128-core
        가상 fixture 에서는 P1b(4번째 태스크 +590 core-h)가
        21,000 천장을 570 초과해 **시끄럽게** 빠진다 — 그 사실은 아래
        test_128core_fixture_overflow_is_loud_not_silent 가 별도로 지킨다.
        (128-core 사이트에서의 패키지 축소 여부는 lead 판정 대기 — 예산을 줄여 fixture
        를 통과시키는 것은 §R24.1 이 기각한 거래다.)
        """
        # 승인 형태 harness 는 test_readme_matches_code.code_truth() 하나뿐이어야 한다
        # (64 core/node + normal 48h + PBS) — 같은 진실을 두 곳에 쓰지 않는다.
        from test_readme_matches_code import code_truth
        truth = code_truth()
        for key in ("P1", "P1b", "P5", "P6_t1", "P6_t16", "P6_t64",
                    "endpoint_prep_reactant"):
            self.assertIn(key, truth["items"], key)
        self.assertLessEqual(truth["reserved"], truth["guard_core_hours"])

    def test_128core_fixture_overflow_is_loud_not_silent(self):
        """128-core 가상 사이트에서는 천장 초과가 나는데, **조용히 사라지면 안 된다** —
        skip 사유와 guard 기록이 함께 남아야 한다(이 테스트가 원래 지키던 그 성질)."""
        _env, items, summary, _g = self._plan(21000.0)
        dropped = [d["id"] for d in summary["guard"]["skipped_for_budget"]]
        for key in dropped:
            self.assertIn("budget_guard", items[key]["skip_reason"],
                          "%s 가 사유 없이 빠졌다" % key)
        self.assertLessEqual(summary["reserved_core_hours"], 21000.0)

    def test_default_guard_runs_the_whole_approved_package(self):
        """🔴 프로파일 기본 가드에서 승인된 항목이 전부 계획돼야 한다.

        ⚠ 전제는 승인된 클러스터 형태(64 core/node, normal 48h) — 위 21000 테스트와
        같은 harness(code_truth)를 쓴다. 이 파일의 128-core/24h SLURM fixture 위에서는
        P1b 가 §R26.1 게이트/천장에 걸린다 — 그 loudness 는 별도 테스트가 지킨다."""
        from test_readme_matches_code import code_truth
        truth = code_truth()
        for key in ("probe_node", "probe_throughput", "probe_queuewait",
                    "P1", "P1b", "P5"):
            self.assertIn(key, truth["items"], key)
        self.assertLessEqual(truth["reserved"], truth["guard_core_hours"])

    def test_hard_guard_never_exceeded_in_any_config(self):
        for cap in (500.0, 1000.0, 2000.0, 4000.0, 5000.0):
            _env, _items, summary, _g = self._plan(cap)
            self.assertLessEqual(summary["reserved_core_hours"], cap)

    def test_priority_order_is_information_per_core_hour(self):
        _env, items, _s, _g = self._plan(4000.0)
        order = sorted(items.values(), key=lambda x: x["priority"])
        self.assertEqual([o["key"] for o in order][:4],
                         ["probe_node", "probe_throughput", "probe_queuewait",
                          "P1"])

    def test_plan_text_warns_about_dropped_items(self):
        env, _items, summary, _g = self._plan(2000.0)
        planned, summary2 = plan.build_plan(env, budget.ResourceGuard(2000.0))
        text = plan.format_plan_text(planned, summary2, env)
        # 🔒 §R27 — 문구가 바뀌었다. 이제 **4-튜플 표와 "사양을 의심하라"** 를 낸다.
        #    🔴 예전 판은 `--max-core-hours <더 큰 값>` 을 권했는데, 그것이 §R24.1 이
        #    기각한 거래(물리적 상한을 예상치로 격하)로 가는 문이었다.
        self.assertIn("자원 가드가 거부한 항목", text)
        self.assertIn("가드를 올리기 전에 사양을 의심", text)
        self.assertIn("천장", text)
        self.assertIn("절단 순서", text)
        self.assertIn("결과 JSON 에 남습니다", text)

    def test_no_scheduler_skips_queue_probes(self):
        shell = FakeShell(responses={"hostname -f": (0, "wsl\n", "")}, which_map={})
        env = cli.build_env(shell, context.PKG_ROOT)
        planned, _s = plan.build_plan(env, budget.ResourceGuard())
        items = {p["key"]: p for p in planned}
        self.assertEqual(items["probe_throughput"]["status"], "skipped")
        self.assertEqual(items["probe_node"]["status"], "planned")  # 노드 프로브는 가능


class TestSubmitIdempotency(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_sub_")
        self.args = make_args(self.d, 21000.0)   # 🔒 §R24.1 [물리 천장]
        self.args.command = "submit"

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_submit_then_resubmit_skips(self):
        shell = fake_cluster()
        store = Store(self.d)
        ids = cli.cmd_submit(self.args, shell=shell, store=store)
        self.assertTrue(len(ids) >= 6)
        self.assertTrue(store.is_submitted("P1"))
        # 🔴 사전검사(--test-only)는 제출이 아니다. 세지 않는다.
        def _real_submits(sh):
            return [c for c in sh.log if str(c["cmd"]).startswith("sbatch")
                    and "--test-only" not in str(c["cmd"])]
        n_sbatch = len(_real_submits(shell))

        shell2 = fake_cluster()
        ids2 = cli.cmd_submit(self.args, shell=shell2, store=Store(self.d))
        self.assertEqual(ids2, [])          # 전부 건너뜀
        n_sbatch2 = len(_real_submits(shell2))
        self.assertEqual(n_sbatch2, 1)      # collector만 다시 제출된다
        self.assertGreater(n_sbatch, n_sbatch2)

    def test_queue_wait_respects_the_node_cap(self):
        """🔴 큐 상한을 모르면 **낮게 잡는다.**

        실제 클러스터에서 `probe_queuewait` 가 **85노드**를 요청해 PBS 필터 훅에
        거부됐고, 큐 대기 측정이 통째로 0 이 됐다. **거부되면 측정 자체가 없다.**
        그래서 `config/sizing.json` 의 `pbs.max_probe_nodes` 로 상한을 둔다.
        """
        from sei_pilot import config
        cap = (config.load("sizing.json", {}).get("pbs") or {})["max_probe_nodes"]
        store = Store(self.d)
        cli.cmd_submit(self.args, shell=fake_cluster(), store=store)
        for n in (1, 4, 16, 64):
            if n <= cap:
                self.assertTrue(store.is_submitted("probe_qw_n%d" % n), n)
            else:
                self.assertFalse(store.is_submitted("probe_qw_n%d" % n), n)

    def test_capping_is_recorded_not_silent(self):
        """축소했다는 사실이 회신에 남아야 한다 — 조용히 줄이면 '측정 안 됨'과 구별 불가."""
        store = Store(self.d)
        cli.cmd_submit(self.args, shell=fake_cluster(), store=store)
        self.assertTrue(store.is_failed("probe_qw_capped"))
        marker = store.read_marker("probe_qw_capped", "failed")
        self.assertEqual("info", marker["severity"])
        self.assertIn("축소", marker["detail"] + marker.get("reason", ""))

    def test_queue_wait_skips_too_large_node_count(self):
        """클러스터가 2노드뿐이면 4노드 잡은 제출하지 않고 사유를 남긴다.

        (상한(max_probe_nodes)보다 **작은** 클러스터에서도 이 경로가 살아 있는지 본다.)
        """
        shell = fake_cluster()
        shell.responses["sinfo -h -o %P|%l|%D|%m|%c"] = (0, "cpu*|1-00:00:00|2|257000|128\n", "")
        store = Store(self.d)
        cli.cmd_submit(self.args, shell=shell, store=store)
        self.assertTrue(store.is_submitted("probe_qw_n1"))
        self.assertFalse(store.is_submitted("probe_qw_n4"))
        self.assertTrue(store.is_failed("probe_qw_n4"))
        self.assertEqual(store.read_marker("probe_qw_n4", "failed")["severity"], "info")

    def test_submit_failure_is_isolated(self):
        """한 잡의 제출 거부가 나머지를 죽이지 않는다."""
        calls = {"n": 0}

        def flaky(cmd):
            calls["n"] += 1
            if calls["n"] == 1:
                return (1, "", "sbatch: error: QOSMaxSubmitJobPerUserLimit")
            return (0, "999\n", "")
        shell = fake_cluster()
        # 사전검사(`sbatch --test-only`)는 통과시키고, **실제 제출만** 흔들리게 한다.
        # (preflight 가 이제 --test-only 를 호출하므로 구분하지 않으면 픽스처가 어긋난다)
        shell.responses["sbatch --test-only"] = (0, "Job 1 to start\n", "")
        shell.responses["sbatch"] = flaky
        store = Store(self.d)
        ids = cli.cmd_submit(self.args, shell=shell, store=store)
        self.assertTrue(len(ids) > 0)
        self.assertTrue(len(store.all_failures()) >= 1)

    def test_chain_links_recorded(self):
        """작은 노드에서는 P1이 체인으로 나간다 (사용자 2차 개입 없이).

        🔴 계획 단계에서 확인한다. **제출까지 가지 않는 이유**: 12 h wall + 16 core 에서는
        P1b array 의 태스크 예산이 `cores × max_wall` 을 넘어 링크가 2 이상이 되고,
        §R26.4 게이트 (b) 가 **제출 전체를 막는다.** 그게 설계된 동작이다
        (`test_sizing_gate_blocks_submission` 이 그쪽을 지킨다).
        """
        shell = fake_cluster()
        shell.responses["sinfo -h -o %P|%l|%D|%m|%c"] = (0, "cpu*|12:00:00|400|64000|16\n", "")
        env = cli.build_env(shell, context.PKG_ROOT)
        g = budget.guard_for_profile("cpu")
        items = {p["key"]: p for p in plan.build_plan(env, g, profile="cpu")[0]}
        # 🔴 P1 이 아니라 P1b 를 본다: P1 은 refusal 비용으로 sizing 돼 어떤 노드에서도
        #    링크가 1개다(영구 제외). 체인 동작을 아직 보여주는 항목은 P1b 다.
        self.assertGreater(items["P1b"]["chain_links"], 1)
        self.assertEqual(1, items["P1"]["chain_links"],
                         "P1 이 다시 체인으로 나간다면 예산이 되살아난 것이다")

    def test_sizing_gate_blocks_only_the_violating_item(self):
        """🔒 lead 판정 — 게이트는 **위반 항목만** 막는다.

        🔴 처음 판은 *"게이트 실패 시 아무것도 제출하지 않는다"* 였는데 **틀린 실패 모드**였다:
        24 h/12 h 큐에서 위반은 P1b 하나뿐이고 P1·P5·P6 는 정상인 **독립 측정**이다.
        전부 막으면 **사용자가 왕복 하나(3.5일)를 쓰고 아무것도 못 받는다.**
        ⟹ 위반 항목만 빠지고 나머지는 제출된다. (전역 위반 = 총 천장 > 가드 인 경우만
        전체를 멈춘다 — 그건 회계가 어긋난 것이므로 다른 문제다.)
        """
        shell = fake_cluster()
        shell.responses["sinfo -h -o %P|%l|%D|%m|%c"] = (0, "cpu*|12:00:00|400|64000|16\n", "")
        store = Store(self.d)
        ids = cli.cmd_submit(self.args, shell=shell, store=store)
        self.assertTrue(ids, "위반 항목 하나 때문에 전부 막혔다")
        self.assertIsNone(store.read_marker("P1b", "submitted"),
                          "게이트를 위반한 P1b 가 제출됐다")


class TestReportAssembly(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_rep_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _collect(self, shell=None):
        args = make_args(self.d, 21000.0)   # 🔒 §R24.1 [물리 천장]
        args.command = "collect"
        store = Store(self.d)
        return cli.cmd_collect(args, shell=shell or fake_cluster(), store=store), store

    def test_report_is_written_and_valid_even_with_no_results(self):
        path, _store = self._collect()
        with open(path) as fh:
            rep = json.load(fh)
        self.assertEqual(report.validate_report(rep), [])
        self.assertEqual(rep["schema_version"], "1.1")
        self.assertEqual(rep["schema_base_version"], "1.0")
        # [coder13, 2026-08-21] u56_2.released=true (lead/사용자 승인) — 5항목 추가.
        self.assertEqual([p["id"] for p in rep["pilots"]],
                         ["P1", "P1b", "P3", "P5", "P6", "endpoint_prep_reactant",
                          "endpoint_prep_product", "endpoint_prep_rc_reactant",
                          "U56_RA_scan", "U56_RA_qst2", "U56_RB_scan"])
        for p in rep["pilots"]:
            self.assertIn(p["status"], ("skipped", "incomplete"))

    def test_schema_1_0_required_fields_present(self):
        path, _ = self._collect()
        rep = json.load(open(path))
        for k in report.REQUIRED_TOP:
            self.assertIn(k, rep)
        for k in report.REQUIRED_CLUSTER:
            self.assertIn(k, rep["cluster"])

    def test_provenance_recorded(self):
        path, _ = self._collect()
        rep = json.load(open(path))
        prov = rep["provenance"]
        self.assertTrue(prov["package_fingerprint"])
        self.assertTrue(prov["generated_at_utc"].endswith("Z"))
        self.assertIsNotNone(prov["random_seed"])

    def test_unresolved_items_are_reported_not_hidden(self):
        path, _ = self._collect()
        rep = json.load(open(path))
        items = [u["item"] for u in rep["unresolved_for_lead"]]
        self.assertTrue(any("Q2" in i for i in items))

    def test_collects_real_pilot_artifacts(self):
        """잡이 남긴 아티팩트를 실제로 읽어 판정까지 가는지."""
        store = Store(self.d)
        jd = store.job_dir("P1")
        os.makedirs(os.path.join(jd, "stages"), exist_ok=True)
        for stage, wall in (("crest", 360), ("ts_guess", 3600), ("ts_opt", 7200),
                            ("irc", 3600), ("freq", 1800)):
            with open(os.path.join(jd, "stages", stage + ".json"), "w") as fh:
                json.dump({"stage": stage, "rc": 0, "wall_s": wall,
                           "total_cores": 64}, fh)
        inputs = os.path.join(context.PKG_ROOT, "inputs")
        shutil.copy(os.path.join(inputs, "li_ec_radical_reactant.xyz"),
                    os.path.join(jd, "irc_forward.xyz"))
        shutil.copy(os.path.join(inputs, "li_ec_radical_product.xyz"),
                    os.path.join(jd, "irc_reverse.xyz"))
        with open(os.path.join(jd, "freq.out"), "w") as fh:
            fh.write("VIBRATIONAL FREQUENCIES\n   6:      -452.31 cm**-1\n"
                     "   7:       112.44 cm**-1\nNORMAL MODES\n")
        store.mark_submitted("P1", {})
        store.mark_done("P1", {"start_epoch": 0, "end_epoch": 3600 * 5})

        path, _ = self._collect()
        rep = json.load(open(path))
        p1 = [p for p in rep["pilots"] if p["id"] == "P1"][0]
        # 🔴 ADR-090/092, C-2: this fixture's `irc_forward.xyz`/`irc_reverse.xyz` are
        # single-frame endpoint files (copied straight from `inputs/`), not a real
        # multi-point IRC trajectory, and no G16 termination/energy telemetry is
        # supplied (this is the non-Gaussian branch -- no `adapter.json`). C-2 is
        # therefore correctly UNABLE to certify a chemical verdict (below
        # `guards.IRC_MIN_POINTS`), so the overall status is `undetermined`, not
        # `pass` -- it was `pass` before C-2 was wired in, which is exactly the gap
        # this review closed (a topology-only "distinct" verdict is not enough).
        self.assertEqual(p1["status"], "undetermined")
        self.assertFalse(p1["criteria"]["irc_c2_may_render_chemical_verdict"])
        # (360+3600+7200+3600+1800) s x 64 core / 3600 = 294.4 core-h
        self.assertAlmostEqual(p1["core_hours_total"], 294.4, places=1)
        self.assertEqual(sorted(p1["breakdown"]), ["crest", "freq", "irc",
                                                   "ts_guess", "ts_opt"])
        self.assertTrue(p1["criteria"]["irc_endpoints_distinct"])
        # 🔴 IRC 규약 선택이 재해석 가능한 형태로 회신에 실린다 (lead 지시)
        ec = p1["detail"]["irc"]["endpoint_comparison"]
        self.assertEqual(ec["merge_rule_applied"], "R1")
        self.assertIn("§12.3", ec["rule_source"])
        self.assertIn("layer_I_cutoffs_ang", ec)
        self.assertFalse(ec["config_is_fallback"])

    # 🔴 P2/P2ext 의 s(t) 3 ps 판정 테스트를 **제거했다.**
    #    파일럿에서 그 항목이 사라졌기 때문이다(ADR-015 §7 → 판정의 소비자 소멸).
    #    되살릴 때 필요한 것은 HANDOFF_TO_LEAD.md §9 에 적어 뒀다.
    #    P2f 는 판정이 아니라 가용성 확인이라 대응 테스트가 필요 없다
    #    (collect_p2f 가 "돌았는가 / MD step 수"만 본다).

    def test_failures_are_carried_into_report(self):
        store = Store(self.d)
        store.mark_failed("P2", "scf_failed", "발산", "SCF run NOT converged")
        path, _ = self._collect()
        rep = json.load(open(path))
        self.assertTrue(any(f["reason"] == "scf_failed" for f in rep["failures"]))

    def test_summarize_for_user_mentions_return_file(self):
        path, _ = self._collect()
        text = report.summarize_for_user(json.load(open(path)))
        self.assertIn("sei_probe_report.json", text)


if __name__ == "__main__":
    unittest.main()
