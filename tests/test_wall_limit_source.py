"""wall 상한을 **큐에서 읽는가** — 그리고 못 읽었을 때 조용히 넘어가지 않는가.

🔴 왜 이 파일이 필요한가:
    engineer §R22 는 `max_wall_h = 48` 을 사양으로 줬는데, **그 48 은
    `[LITERATURE — 사이트 문서]` 이지 실측이 아니다.** 문서값을 코드에 박으면 그것이
    틀렸을 때 **조용히 틀린다.**

    🔴 우리는 이미 같은 형태로 당했다: 파티션을 `sinfo`(SLURM 전용)로만 읽어서
    **PBS 클러스터에서 `#PBS -q` 지시어가 통째로 빠졌고**, 4/4 거부의 원인 후보가
    라운드 내내 분리되지 않았다.

    🔴 그리고 이 코드는 **정확히 그 상태였다**: `sysprobe` 가 `qstat -Qf <queue>` 로
    `resources_max.walltime` 을 **이미 수집해 `env["queue_info"]` 에 넣고 있었는데
    `build_plan` 이 그것을 보지 않았다.** 측정해 놓고 안 쓰는 값이 또 있었다
    (`probe_throughput` 의 `host` 유실과 같은 형태).

여기서 고정하는 성질:
  1. 큐가 상한을 말하면 **그것을 쓴다** (문서값이 아니라)
  2. 큐가 24 h 를 말하면 사양(48)이 **자동으로 24 로 접힌다**
  3. 큐를 못 읽으면 **크게 경고하고 `[UNVERIFIED]` 로 표시한다** (조용히 48 을 쓰지 않는다)
  4. 우리 캡보다 큰 값을 큐가 말해도 **우리 캡을 넘지 않는다**
"""

import unittest

import context  # noqa: F401
from sei_pilot import budget, plan

#: 🔴 실클러스터 형식 그대로. `qstat -Qf normal` 의 실제 출력 형태를 쓴다.
QSTAT_QF = """Queue: normal
    queue_type = Execution
    resources_max.ncpus = 4096
    resources_max.nodect = 64
    resources_max.walltime = 48:00:00
    enabled = True
    started = True
"""

QSTAT_QF_24H = QSTAT_QF.replace("48:00:00", "24:00:00")


def env_with_queue(text=None, partition_wall=None):
    """🔴 `queue_info` 를 손으로 짜지 않고 **진짜 파서**(`sysprobe.parse_qstat_queue`)로 만든다.

    손으로 `{"max_walltime_h": 48}` 을 넣으면 *"내가 상상한 파서 출력"* 을 검증하게 된다.
    """
    from sei_pilot import sysprobe
    env = {"cores_per_node": 64, "scheduler": "pbs"}
    if text is not None:
        qi = sysprobe.parse_qstat_queue(text)
        qi["queue"] = "normal"
        env["queue_info"] = qi
    if partition_wall is not None:
        env["partition_max_wall_h"] = partition_wall
    return env


class TestWallLimitComesFromTheQueue(unittest.TestCase):
    def test_queue_value_is_used_when_available(self):
        g = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        r = plan.resolve_wall_limit(env_with_queue(QSTAT_QF), g)
        self.assertEqual(r["max_wall_h_used"], 48.0)
        self.assertEqual(r["wall_limit_source"], "queue_measured")
        self.assertTrue(r["wall_limit_verified"])
        self.assertIn("qstat -Qf", r["wall_limit_basis"])

    def test_queue_reporting_24h_folds_the_spec_down(self):
        """🔴 lead 요구 4번: 큐가 24 h 를 말하면 사양(48)이 자동으로 접혀야 한다."""
        g = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        r = plan.resolve_wall_limit(env_with_queue(QSTAT_QF_24H), g)
        self.assertEqual(r["max_wall_h_used"], 24.0)
        self.assertEqual(r["queue_reported_max_wall_h"], 24.0)
        self.assertTrue(r["wall_limit_verified"])

    def test_our_cap_still_binds_when_queue_allows_more(self):
        """큐가 168 h 를 허용해도 우리 캡을 넘지 않는다 (ADR-004 는 우리 자신의 캡이다)."""
        g = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        r = plan.resolve_wall_limit(
            env_with_queue(QSTAT_QF.replace("48:00:00", "168:00:00")), g)
        self.assertEqual(r["max_wall_h_used"], 48.0)
        self.assertTrue(r["capped_by_us"])

    def test_unreadable_queue_is_loud_not_silent(self):
        """🔴 핵심. 못 읽으면 조용히 48 을 쓰지 않는다 — `-q` 사고의 재발 방지."""
        g = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        r = plan.resolve_wall_limit(env_with_queue(None), g)
        self.assertEqual(r["wall_limit_source"], "our_cap_unverified")
        self.assertFalse(r["wall_limit_verified"])
        self.assertIn("UNVERIFIED", r["wall_limit_basis"])
        self.assertIsNone(r["queue_reported_max_wall_h"])
        # 값 자체는 우리 캡을 쓴다 — 그러나 **검증됐다고 말하지 않는다.**
        self.assertEqual(r["max_wall_h_used"], 48.0)

    def test_explicit_argument_wins(self):
        g = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        r = plan.resolve_wall_limit(env_with_queue(QSTAT_QF), g, max_wall_h=6.0)
        self.assertEqual(r["max_wall_h_used"], 6.0)
        self.assertEqual(r["wall_limit_source"], "explicit_argument")


class TestWallLimitReachesThePlan(unittest.TestCase):
    """🔴 부품이 아니라 **계획 산출물**에서 확인한다 (ADR-041)."""

    def _plan(self, env):
        g = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        return plan.build_plan(env, g, profile="cpu")

    def test_summary_carries_the_source(self):
        _p, s = self._plan(env_with_queue(QSTAT_QF))
        self.assertEqual(s["max_wall_h_used"], 48.0)
        self.assertEqual(s["wall_limit_source"], "queue_measured")
        self.assertTrue(s["wall_limit_verified"])

    def test_plan_text_shouts_when_unverified(self):
        """사람이 보는 화면에도 나와야 한다. JSON 에만 있으면 아무도 안 본다."""
        env = env_with_queue(None)
        planned, s = self._plan(env)
        text = plan.format_plan_text(planned, s, env)
        self.assertIn("UNVERIFIED", text)
        self.assertIn("qstat -Qf", text)

    def test_plan_text_is_quiet_when_verified(self):
        """🔴 오경보는 진짜 경보를 못 믿게 만든다. 확인됐으면 경고하지 않는다."""
        env = env_with_queue(QSTAT_QF)
        planned, s = self._plan(env)
        text = plan.format_plan_text(planned, s, env)
        self.assertNotIn("UNVERIFIED", text)

    def test_24h_queue_actually_shrinks_job_walls(self):
        """🔴 출처만 기록하고 끝나면 안 된다. **잡의 wall 이 실제로 줄어야** 한다.

        🔴 처음 쓴 판은 기본 항목 집합으로 확인하려 했는데, 이 env 에는 QC 코드가 없어
        P1/P5/P1b 가 전부 생략되고 남는 프로브는 상한보다 훨씬 짧아 **48↔24 로 아무것도
        변하지 않았다.** 즉 "wall 이 안 줄었다"가 아니라 **줄어들 잡이 없었다.**
        (테스트가 틀렸던 것이지 코드가 틀린 게 아니었다.)
        ⟹ wall 상한에 실제로 눌리는 항목을 하나 넣어서 확인한다.
        """
        big = plan.Item("wall_probe_item", "wall 상한에 눌리는 항목", 99,
                        core_hours_budget=6800.0, nodes=1)
        g48 = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        g24 = budget.ResourceGuard(max_core_hours=17000.0, max_wall_h=48.0)
        p48, s48 = plan.build_plan(env_with_queue(QSTAT_QF), g48, items=[big])
        p24, s24 = plan.build_plan(env_with_queue(QSTAT_QF_24H), g24, items=[big])
        self.assertEqual(s48["max_wall_h_used"], 48.0)
        self.assertEqual(s24["max_wall_h_used"], 24.0)
        w48 = p48[0]["wall_h"]
        w24 = p24[0]["wall_h"]
        self.assertEqual(w48, 48.0)
        self.assertEqual(w24, 24.0, "큐가 24 h 를 말했는데 잡 wall 이 따라오지 않았다")
        # 🔴 그리고 잘린 wall 은 **링크 수로 보상돼야** 한다 — 예산이 조용히 사라지면 안 된다.
        self.assertGreater(p24[0]["chain_links"], p48[0]["chain_links"])


if __name__ == "__main__":
    unittest.main()
