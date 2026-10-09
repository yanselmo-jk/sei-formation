"""🔴 이기종 노드 sizing — 로그인 노드로 계산 노드를 재지 않는가.

실제로 난 사고: dry-run 이 `core/node : 24`(로그인 노드)로 **모든 잡을 sizing** 했다.
계산 노드는 64다. 2.7배 어긋난 값으로 wall·링크 수·예약이 전부 계산됐고,
**dry-run 은 그걸 정상으로 보고했다.** 사용자가 믿고 제출하면 잡이 wall 에 잘리거나
자원이 안 맞아 왕복 1회(3.5일)를 날린다.

여기서 고정하는 것:
  1. 계산 노드 값이 있으면 **그것으로** sizing 한다 (로그인 값이 아니라)
  2. 감지값 ≠ 요청 가능값인 경우(68 코어 중 64 사용)를 변환한다
  3. 계산 노드 사양을 못 구하면 **시끄럽게** 폴백한다 (조용한 폴백이 사고 원인)
  4. 출처가 항상 함께 다닌다 — 요약만 보는 사람이 출처를 놓친다
"""

import unittest

import context  # noqa: F401
from sei_pilot import budget, cli, plan, sysprobe
from sei_pilot.shellrun import FakeShell


class _Login(object):
    """sysprobe.collect_login 을 대체해 로그인/계산 노드를 따로 준다."""

    def __init__(self, login_cores, compute_cores=None, source="pbsnodes -a"):
        # P1 이 계획되도록 QC 코드를 있는 것으로 둔다 (sizing 전파를 보려면
        # 항목이 실제로 계획돼야 한다).
        self.data = {"hostname": "login03", "modules": [],
                     "software": {"g16": {"path": "/opt/g16/g16",
                                          "version": "g16 (fake)"}},
                     "login_gpus": {}, "partitions": [],
                     "login_cpu": {"physical_cores": login_cores}}
        if compute_cores:
            self.data["compute_nodes"] = {"cores_per_node": compute_cores,
                                          "source": source}

    def __enter__(self):
        self._orig = sysprobe.collect_login
        sysprobe.collect_login = lambda *a, **k: dict(self.data)
        return self

    def __exit__(self, *exc):
        sysprobe.collect_login = self._orig


def _env(login_cores, compute_cores=None, override=None):
    with _Login(login_cores, compute_cores):
        return cli.build_env(FakeShell(), context.PKG_ROOT,
                             cores_per_node_override=override)


class TestComputeNodeWins(unittest.TestCase):
    def test_sizing_uses_compute_not_login(self):
        """🔴 이 프로젝트에서 실제로 틀렸던 바로 그 값."""
        env = _env(login_cores=24, compute_cores=64)
        self.assertEqual(64, env["cores_per_node"])
        self.assertNotEqual(24, env["cores_per_node"])

    def test_login_and_compute_are_separate_fields(self):
        """같은 필드에 뭉뚱그리면 어느 쪽 값인지 영원히 알 수 없다."""
        env = _env(login_cores=24, compute_cores=64)
        self.assertEqual(24, env["cores_per_node_login"])
        self.assertEqual(64, env["cores_per_node_compute"])

    def test_source_is_always_carried(self):
        env = _env(login_cores=24, compute_cores=64)
        self.assertIn("pbsnodes", env["cores_per_node_source"])

    def test_not_flagged_as_login_fallback_when_compute_is_known(self):
        self.assertFalse(_env(24, 64)["cores_per_node_is_login_fallback"])


class TestUsableCoresPolicy(unittest.TestCase):
    """68 core 시스템에서 64만 쓴다 — 감지값을 그대로 요청하면 잡이 안 뜬다."""

    def test_68_becomes_64(self):
        env = _env(login_cores=24, compute_cores=68)
        self.assertEqual(68, env["cores_per_node_detected"])
        self.assertEqual(64, env["cores_per_node"])

    def test_conversion_is_visible_in_the_source_label(self):
        env = _env(24, 68)
        self.assertIn("68", env["cores_per_node_source"])
        self.assertIn("64", env["cores_per_node_source"])

    def test_values_without_a_policy_entry_pass_through(self):
        self.assertEqual(64, _env(24, 64)["cores_per_node"])
        self.assertEqual(128, _env(24, 128)["cores_per_node"])

    def test_user_override_beats_the_policy(self):
        env = _env(24, 68, override=48)
        self.assertEqual(48, env["cores_per_node"])
        self.assertIn("사용자 지정", env["cores_per_node_source"])


class TestLoudFallback(unittest.TestCase):
    def test_falls_back_to_login_with_a_loud_marker(self):
        env = _env(login_cores=24, compute_cores=None)
        self.assertEqual(24, env["cores_per_node"])
        self.assertTrue(env["cores_per_node_is_login_fallback"])
        self.assertIn("🔴", env["cores_per_node_source"])

    def test_plan_text_shouts_about_the_fallback(self):
        env = _env(24, None)
        planned, summary = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                           profile="cpu")
        text = plan.format_plan_text(planned, summary, env)
        self.assertIn("--cores-per-node", text,
                      "폴백했으면 고치는 방법을 화면에 띄워야 한다")

    def test_plan_text_shows_login_value_when_they_differ(self):
        env = _env(24, 64)
        planned, summary = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                           profile="cpu")
        text = plan.format_plan_text(planned, summary, env)
        self.assertIn("24", text, "로그인 노드 값이 다르면 그 사실이 보여야 한다")


class TestSizingPropagates(unittest.TestCase):
    """core/node 하나가 wall·링크·예약에 동시에 전파된다 — 그래서 위험하다."""

    def _reserved(self, cores):
        env = _env(24, cores)
        planned, summary = plan.build_plan(env, budget.guard_for_profile("cpu"),
                                           profile="cpu")
        return summary, dict((p["key"], p) for p in planned)

    #: 🔴 이 두 테스트의 관측 대상은 **P1 이었다.** P1 이 영구 제외되면서 예산이
    #: 6,800 → 64 core-h 로 줄었고(refusal 비용으로 sizing), 그러면 어느 코어 수에서도
    #: 링크가 1개라 "코어↑ ⇒ 링크↓" 를 P1 에서는 더 이상 관측할 수 없다.
    #: ⟹ 대상을 **P1b**(5,328 core-h, 이 라운드 최대 항목)로 옮긴다. 성질 자체는 그대로고,
    #:   그것을 아직 보여주는 항목으로 바꾼 것이다 — 검사를 느슨하게 만든 것이 아니다.
    #: 🔒 P1 을 대상으로 남겨두면 "포화됐다"가 아니라 **"항목이 이제 작다"** 를 성질의
    #:   부재로 오독하게 된다.
    SIZING_SUBJECT = "P1b"

    def test_wall_time_shrinks_as_cores_grow(self):
        """🔒 의도된 변화 (§R22.9): 큰 항목은 **양쪽 다 wall 상한에 붙는다.**
        ⟹ "코어가 늘면 wall 이 준다"는 관측되지 않는다 — **포화됐다.**
        대신 남는 관측 가능한 성질 두 가지를 검사한다:
          (1) wall 은 상한을 넘지 않는다
          (2) 코어가 늘면 **링크 수가 준다** (= 같은 예산을 더 적은 조각으로 소화한다)
        🔴 이 테스트를 "코어↑ ⇒ wall↓" 로 남겨두면 포화 상태를 결함으로 오독하게 된다.
        """
        k = self.SIZING_SUBJECT
        s24, i24 = self._reserved(24)
        s64, i64 = self._reserved(64)
        cap = s64["max_wall_h_used"]
        self.assertLessEqual(i64[k]["wall_h"], cap)
        self.assertLessEqual(i24[k]["wall_h"], cap)
        self.assertGreater(i24[k]["chain_links"], i64[k]["chain_links"],
                           "코어가 늘면 같은 예산을 더 적은 링크로 소화해야 한다")

    def test_p1_is_now_too_small_to_show_the_property(self):
        """🔴 위 테스트가 왜 옮겨졌는지를 **성질로** 고정한다: P1 은 이제 refusal 비용으로
        sizing 돼 있어 어느 코어 수에서도 링크가 1개다. 누군가 P1 을 다시 크게 만들면
        (= 영구 제외를 되돌리면) 이 테스트가 RED 로 알린다."""
        _s24, i24 = self._reserved(24)
        _s64, i64 = self._reserved(64)
        self.assertEqual(1, i24["P1"]["chain_links"])
        self.assertEqual(1, i64["P1"]["chain_links"])

    def test_wrong_cores_changes_chain_link_count(self):
        """링크 수가 달라진다 = 제출 구조 자체가 달라진다. (대상은 SIZING_SUBJECT — 위 주석)"""
        _s24, i24 = self._reserved(24)
        _s64, i64 = self._reserved(64)
        k = self.SIZING_SUBJECT
        self.assertNotEqual(i24[k]["chain_links"], i64[k]["chain_links"])


if __name__ == "__main__":
    unittest.main()
