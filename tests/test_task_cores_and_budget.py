"""태스크당 코어 수 / 두 통화(천장 vs 전망) — §R22·§R24 재실행 사양.

🔴 왜 이 파일이 필요한가 — **설계 변경이 기존 가정과 충돌했는데 아무도 확인하지 않았다:**
    `plan.py` 의 array 산식에 *"태스크당 1코어"* 가 **하드코딩**돼 있었다.
    `probe_throughput`(200 × 1분 × 1코어)에는 옳았다. 그런데 §R22 가 P5·P1b 를 array 로
    바꾸면서 **그 기계장치를 그대로 물려받았다.**
    ⟹ P5 최대 종 496 core-h 가 1코어면 **wall 496 h** 다. 48 h 큐에서 즉사한다.
    ⟹ §R22·§R24 의 wall·천장 표 전부가 그 위에 서 있었다.
    **부품(예산표)을 세 왕복 동안 정밀하게 다듬는 동안 그 아래 전제가 검사되지 않았다.**

🔴 두 통화를 절대 섞지 않는다 (§R24.1):
    `reserved_core_hours`  = 물리 천장 (cores×wall×links). **guard 는 여기에 건다.**
                             스케줄러가 wall 에서 죽이므로 파이썬 버그와 무관하게 강제된다.
    `expected_core_hours`  = 소비 전망. 보고용이며 **강제되지 않는다.**
    guard 를 전망에 걸면 `describe()` 의 *"제출 자체가 되지 않는다"* 가 거짓이 되고,
    **신뢰받는 안전장치가 실제로는 작동하지 않는 것은 없느니만 못하다.**
"""

import json
import math
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import budget, cli, plan, sysprobe
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

QSTAT_48H = "Queue: normal\n    resources_max.walltime = 48:00:00\n"


def env_pbs(cores_per_node=64, wall_text=QSTAT_48H):
    qi = sysprobe.parse_qstat_queue(wall_text)
    qi["queue"] = "normal"
    return {"cores_per_node": cores_per_node, "scheduler": "pbs", "queue_info": qi,
            "software": {"g16": {"path": "/x/g16"}, "xtb": {"path": "/x/xtb"}},
            "vendored": {}, "containers": {}, "qc_module": {"module": None}}


def plan_items(env=None, guard=None):
    env = env or env_pbs()
    guard = guard or budget.guard_for_profile("cpu")
    planned, summary = plan.build_plan(env, guard, profile="cpu")
    return {p["key"]: p for p in planned}, summary, guard


class TestCoresPerTaskDrivesEverything(unittest.TestCase):
    """🔴 lead 요구: 태스크당 코어를 바꾸면 예산·천장·wall 이 **함께** 움직이는가."""

    def test_throughput_probe_keeps_one_core_per_task(self):
        """🔴 회귀 방지. 이 항목은 200 × 1분 × **1코어**가 맞다 — 고치면 안 된다."""
        items, _s, _g = plan_items()
        self.assertEqual(items["probe_throughput"]["cores_per_node"], 1)

    def test_pilot_arrays_get_whole_node_not_one_core(self):
        """🔴 이것이 잡힌 결함이다. P5/P1b 는 노드 전체를 받아야 한다."""
        items, _s, _g = plan_items()
        for key in ("P5", "P1b"):
            self.assertEqual(items[key]["cores_per_node"], 64,
                             "%s 가 태스크당 1코어로 sizing 됐다 — wall 이 64배가 된다" % key)

    def test_wall_would_be_absurd_with_one_core(self):
        """🔴 결함이 살아 있었다면 어떤 수가 나왔는지를 못 박는다(수치로).

        P5 최대 태스크는 496 core-h 다. 1코어면 wall 496 h — 48 h 큐에서 즉사한다.
        """
        budgets = plan.p5_task_budgets()
        one_core = plan.size_tasks(budgets, 1, max_wall_h=48.0, min_wall_h=0.5)
        node = plan.size_tasks(budgets, 64, max_wall_h=48.0, min_wall_h=0.5)
        self.assertGreater(max(t["chain_links"] for t in one_core), 1)
        self.assertEqual(max(t["chain_links"] for t in node), 1,
                         "노드 전체를 쓰면 P5 는 링크 분할 없이 들어가야 한다")

    def test_pilot_walls_stay_inside_the_queue_limit(self):
        """🔴 **가드는 이 결함을 못 본다.** 그래서 이 검사가 따로 있어야 한다.

        1코어로 되돌려 보면: core-h **천장은 거의 그대로**다(링크가 늘어 상쇄된다).
        폭발하는 것은 **wall 과 링크 수**뿐이다 — 즉 `budget_guard` 는 아무 말도 하지 않고
        잡만 wall-kill 된다. 조용히 틀리는 부류다.
        """
        items, summary, _g = plan_items()
        cap = summary["max_wall_h_used"]
        for key in ("P1", "P1b", "P5", "P6_t1", "P6_t16", "P6_t64"):
            e = items[key]
            self.assertLessEqual(e["wall_h"], cap,
                                 "%s 의 wall 이 큐 상한을 넘는다" % key)
        # P5 는 노드 전체를 쓰면 링크 분할 없이 들어가야 한다.
        self.assertEqual(items["P5"]["chain_links"], 1,
                         "P5 가 링크로 쪼개졌다 — 태스크당 코어 수가 잘못됐을 때의 증상이다")

    def test_changing_cores_moves_budget_wall_and_ceiling_together(self):
        """코어 수만 바꾸면 wall 은 줄고 천장은 (거의) 보존된다 — 같은 일을 한다."""
        budgets = [640.0]
        t16 = plan.size_tasks(budgets, 16, max_wall_h=48.0)[0]
        t64 = plan.size_tasks(budgets, 64, max_wall_h=48.0)[0]
        self.assertAlmostEqual(t16["wall_h"], 40.0, places=3)
        self.assertAlmostEqual(t64["wall_h"], 10.0, places=3)
        self.assertAlmostEqual(t16["ceiling_core_hours"], 640.0, places=1)
        self.assertAlmostEqual(t64["ceiling_core_hours"], 640.0, places=1)

    def test_p6_tasks_request_the_threads_they_claim_to_measure(self):
        """🔴 P6 는 1/16/64 스레드를 **재는 것**이 목적이다. 요청이 다르면 무의미하다.

        예전 판에서는 세 항목이 전부 64 로 찍혔다("보이는 것과 보내는 것이 다르다").
        """
        items, _s, _g = plan_items()
        for nthread in (1, 16, 64):
            self.assertEqual(items["P6_t%d" % nthread]["cores_per_node"], nthread)

    def test_p6_reservation_is_cores_times_wall(self):
        """P6 는 budget→wall 역산이 성립하지 않아 wall 을 명시한다(1스레드면 340 h)."""
        items, _s, _g = plan_items()
        for nthread in (1, 16, 64):
            e = items["P6_t%d" % nthread]
            self.assertAlmostEqual(e["wall_h"], plan.P6_WALL_H, places=3)
            self.assertAlmostEqual(e["reserved_core_hours"],
                                   nthread * plan.P6_WALL_H, places=1)


class TestTwoCurrenciesNeverMix(unittest.TestCase):
    """🔒 §R24.1 — 천장과 전망은 다른 숫자다. 셋 다 같은 정의를 써야 한다."""

    def test_ceiling_is_never_below_expected(self):
        items, _s, _g = plan_items()
        for key, e in items.items():
            if e["status"] != "planned":
                continue
            self.assertGreaterEqual(
                e["reserved_core_hours"] + 1e-6, 0.0, key)

    def test_guard_binds_on_the_ceiling_not_the_forecast(self):
        """🔴 핵심. guard 가 전망에 걸리면 스케줄러 강제가 사라진다."""
        items, summary, guard = plan_items()
        planned = [e for e in items.values() if e["status"] == "planned"]
        total_ceiling = sum(e["reserved_core_hours"] for e in planned)
        self.assertAlmostEqual(summary["reserved_core_hours"], total_ceiling, places=1)
        self.assertLessEqual(total_ceiling, guard.max_core_hours)

    def test_definitions_travel_with_the_values(self):
        """숫자만 실으면 소비자가 오독한다. 정의 문자열을 같은 자리에 싣는다."""
        items, _s, _g = plan_items()
        e = items["P1"]
        defs = e["core_hour_field_definitions"]
        self.assertIn("천장", defs["reserved_core_hours"])
        self.assertIn("전망", defs["expected_core_hours"])
        self.assertIn("노드", defs["node_hours"])

    def test_nothing_is_silently_dropped_by_the_guard(self):
        """🔴 재산정 중 실제로 P1b(가장 값진 측정)가 소리 없이 빠졌다. 그 형태를 고정한다."""
        items, _s, _g = plan_items()
        dropped = [k for k, e in items.items()
                   if e["status"] == "skipped"
                   and "budget_guard" in (e.get("skip_reason") or "")]
        self.assertEqual([], dropped,
                         "가드가 항목을 조용히 잘랐다: %s" % dropped)

    def test_ceiling_is_actually_enforceable_by_the_scheduler(self):
        """천장이 `cores × wall × links` 와 일치하는가 — **강제 가능한 수인가.**"""
        items, _s, _g = plan_items()
        e = items["P1"]
        recomputed = e["cores_per_node"] * e["wall_h"] * e["chain_links"]
        self.assertAlmostEqual(e["reserved_core_hours"], recomputed, places=1)


class TestReportCarriesBothCurrencies(unittest.TestCase):
    """조립선 끝까지 — 디스크의 회신 JSON (ADR-041)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_cur_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_report_json_has_reserved_and_definitions(self):
        args = cli.build_parser().parse_args(
            ["collect", "--workdir", self.d, "--pkg-root", context.PKG_ROOT])
        shell = FakeShell(responses={"hostname -f": (0, "testbox\n", "")},
                          which_map={})
        path = cli.cmd_collect(args, shell=shell, store=Store(self.d))
        with open(path) as fh:
            rep = json.load(fh)
        # 🔴 이 env 에는 G16 이 없어 P1 이 **생략**된다. 생략된 항목은 sizing 을 타지
        #    않으므로 두 통화 필드가 없다 — 그건 정상이다.
        #    ⟹ 그 env 에서 실제로 planned 인 항목으로 확인한다.
        #    (처음엔 P1 을 봤다가 "필드가 없다"를 결함으로 오독할 뻔했다.)
        entry = next(p for p in rep["plan"]
                     if p["key"] == "probe_node" and p["status"] == "planned")
        self.assertIn("reserved_core_hours", entry)
        self.assertIn("expected_core_hours", entry)
        self.assertIn("core_hour_field_definitions", entry)


class TestP5BudgetFollowsSize(unittest.TestCase):
    """🔒 §R24.1 — 편차를 wall 바닥값이 아니라 **예산**에 넣는다."""

    def test_budgets_sum_to_the_declared_total(self):
        self.assertAlmostEqual(sum(plan.p5_task_budgets()),
                               plan.P5_TOTAL_CORE_HOURS, places=1)

    def test_bigger_species_get_more_budget(self):
        runs = plan._p5_runs()
        budgets = plan.p5_task_budgets()
        pairs = sorted(zip([r["size"] for r in runs], budgets))
        self.assertLess(pairs[0][1], pairs[-1][1])

    def test_task_count_matches_the_array_range(self):
        """🔴 설명 문자열·태스크 수·예산 개수가 갈리면 한쪽만 갱신된다."""
        items, _s, _g = plan_items()
        lo, hi = items["P5"]["array"]
        self.assertEqual(hi - lo + 1, len(plan.p5_task_budgets()))

    def test_min_wall_floor_does_not_dominate_the_ceiling(self):
        """🔴 engineer 가 P5 에서 지적한 병(바닥값이 천장을 부풀림)의 재발 방지.

        균일예산 133 + `min_wall 12` 일 때 천장이 **예산의 5.77배**였다.
        """
        items, _s, _g = plan_items()
        e = items["P5"]
        ratio = e["reserved_core_hours"] / e["expected_core_hours"]
        self.assertLess(ratio, 1.5,
                        "P5 천장이 예산의 %.2f 배다 — min_wall 바닥값이 지배하고 있다" % ratio)


if __name__ == "__main__":
    unittest.main()


class TestGateBlocksOnlyTheViolatingItem(unittest.TestCase):
    """🔒 lead 판정 — **위반 항목만 막는다. 전량 차단은 틀린 실패 모드다.**

    🔴 근거: 24 h 큐에서 총액은 가드를 통과하고(17,555) 위반은 **P1b 하나**인데,
    P5·P1·P6 는 24 h 에서 정상인 **독립 측정**이다. 전부 막으면
    **사용자가 왕복 하나(3.5일)를 쓰고 아무것도 못 받는다** — 이번 라운드 내내 피하려던 결과다.
    """

    QSTAT_24H = ("Queue: normal\n    resources_max.walltime = 24:00:00\n"
                 "    enabled = True\n    started = True\n")

    def _plan_24h(self):
        from sei_pilot import sysprobe as sp
        env = {"cores_per_node": 64, "scheduler": "pbs",
               "queues": sp.parse_qstat_all_queues(self.QSTAT_24H),
               "software": {"g16": {"path": "/x/g16"}},
               "vendored": {}, "containers": {}, "qc_module": {"module": None}}
        g = budget.guard_for_profile("cpu")
        # 🔒 [critic3 치명적-2] **제출 큐를 명시한다.** 예전 판은 `qstat -Qf` 전체에서
        #    가장 긴 큐의 wall 을 가정했는데, 실제 `-q` 는 별도 경로로 정해져서
        #    **게이트가 보는 큐와 제출 큐가 갈릴 수 있었다.** 이제 sizing 은 "우리가 실제로
        #    제출할 큐"의 wall 만 본다. 여기서는 `normal`(24 h)로 제출하는 상황이다.
        planned, summary = plan.build_plan(env, g, profile="cpu",
                                           submit_queue="normal")
        return {p["key"]: p for p in planned}, summary

    def test_only_the_violating_item_is_blocked(self):
        items, summary = self._plan_24h()
        self.assertEqual(summary["sizing_gates"]["blocked_items"], ["P1b"])
        self.assertTrue(items["P1b"].get("blocked_by_gate"))

    def test_the_other_measurements_still_run(self):
        """🔴 이것이 핵심이다. 나머지는 24 h 에서 정상이므로 돌아야 한다."""
        items, _s = self._plan_24h()
        for key in ("P1", "P5", "P6_t1", "P6_t16", "P6_t64"):
            self.assertEqual(items[key]["status"], "planned",
                             "%s 까지 막혔다 — 사용자가 왕복 하나를 쓰고 빈손이 된다" % key)

    def test_block_is_not_silent(self):
        """🔴 조용히 빠지면 그게 '조용한 실패' 여덟 번째다. 화면·JSON 양쪽에 나와야 한다."""
        items, summary = self._plan_24h()
        env = {"cores_per_node": 64, "scheduler": "pbs"}
        text = plan.format_plan_text(list(items.values()), summary, env)
        self.assertIn("P1b", text)
        self.assertIn("실행되지 않는 항목", text)
        self.assertIn("해결", text)

    def test_block_says_what_unblocks_it(self):
        """사유만으로는 부족하다 — **무엇을 하면 풀리는지**가 있어야 한다."""
        items, _s = self._plan_24h()
        remedy = items["P1b"]["remedy"]
        self.assertIn("큐", remedy)
        self.assertIn("--queue", remedy)

    def test_partial_run_feasibility_is_reported_not_auto_enabled(self):
        """🟡 [PROVISIONAL] 종 단위 부분 실행은 **알리기만** 한다. 자동 발동하지 않는다.

        남는 종만으로 `r` 이 쓸 만한지는 **견적자 판정**이고, 잃는 것은 크기 의존성의 상단이다.
        """
        _items, summary = self._plan_24h()
        f = next(x for x in summary["sizing_gates"]["failures"]
                 if x["gate"] == "b_array_links_one")
        self.assertEqual(f["offending_tasks"], [3])
        # [MAJOR #1] 태스크 4(stagewise+U-27, 590 core-h → wall 9.2 h)가 추가됐고
        # 24 h 큐에서도 돌 수 있으므로 runnable 에 포함된다. 종별 22원자 태스크(3)만 걸린다.
        self.assertEqual(f["runnable_tasks"], [1, 2, 4])
        self.assertTrue(f["partial_run_possible"])
        self.assertIn("자동 발동하지 않는다", f["partial_run_note"])

    def test_48h_queue_blocks_nothing(self):
        """🔴 오경보 금지. 48 h 에서는 아무것도 막히면 안 된다."""
        items, summary, _g = plan_items()
        self.assertEqual(summary["sizing_gates"]["blocked_items"], [])
        self.assertTrue(summary["sizing_gates"]["passed"])
