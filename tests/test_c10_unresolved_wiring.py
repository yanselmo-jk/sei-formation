"""[A-5] C-10 위반 → `unresolved_for_lead` 배선.

사고 (이번 회신 실측): `pilots[0].c10_cost_probe_violations` 는 기록됐는데
`cli.collect_unresolved()` 가 그것을 한 줄도 안 봐서 `unresolved_for_lead == []` 로
회신됐다 — report.py 가 그 필드를 "판정 대기 중인 규약 = lead 가 여전히 눈이 먼 항목"
으로 정의하고 있는데도. 이대로면 다음 사람이 "P1 fail" 을 화학적 실패로 읽고 U-56 이
"미측정"에서 유령 0/1 로 바뀐다. 판정 로직(현행 유지 A)은 건드리지 않는다 — 배선만.
"""

import unittest

import context  # noqa: F401
from sei_pilot import budget, cli


class _Guard(object):
    def to_dict(self):
        return {}


def _unresolved(pilots):
    env = {"cores_per_node": 64, "scheduler": "pbs"}
    node_probe = {"outbound_network": {"ok": True}}
    return cli.collect_unresolved(env, [], budget.guard_for_profile("cpu"),
                                  node_probe, pilots=pilots)


class TestC10ReachesTheLeadChannel(unittest.TestCase):
    def test_the_incident_a_recorded_violation_reached_no_summary_channel(self):
        """사고 재현 입력: 이번 회신의 P1 형태 그대로 — c10 위반이 기록돼 있다.
        수정 전에는 이 입력에서 unresolved_for_lead 가 비었다."""
        pilots = [{
            "id": "P1", "status": "fail",
            "c10_cost_probe_violations": [
                "status pass/fail carries a chemical verdict on a cost probe"],
            "c10_note": "...",
        }]
        out = _unresolved(pilots)
        c10 = [e for e in out if "C-10" in (e.get("item") or "")]
        self.assertEqual(1, len(c10), "C-10 위반이 lead 채널에 오르지 않았다: %r" % out)
        self.assertIn("P1", c10[0]["item"])
        self.assertIn("chemical verdict", c10[0]["why"])
        self.assertIn("화학적", c10[0]["action"])

    def test_no_violation_no_entry(self):
        pilots = [{"id": "P1", "status": "pass", "c10_cost_probe_violations": []},
                  {"id": "P5", "status": "pass"}]
        out = _unresolved(pilots)
        self.assertEqual([], [e for e in out if "C-10" in (e.get("item") or "")])

    def test_every_pilot_with_a_violation_is_listed_not_only_p1(self):
        """배선은 pilots[*] 전체를 본다 — P1 전용 루프에 끼워 넣으면 다음 위반이
        다른 파일럿에서 또 침묵한다."""
        pilots = [{"id": "P5", "c10_cost_probe_violations": ["x"]},
                  {"id": "P1b", "c10_cost_probe_violations": ["y"]}]
        out = _unresolved(pilots)
        items = [e["item"] for e in out if "C-10" in e["item"]]
        self.assertEqual(2, len(items))
        self.assertTrue(any("P5" in i for i in items))
        self.assertTrue(any("P1b" in i for i in items))


if __name__ == "__main__":
    unittest.main()
