"""critic3 리뷰 치명적 2건의 회귀 테스트.

🔴 **둘 다 "조용히 틀리는" 부류다.** 크래시도 없고 회신 JSON 도 정상 형태이며,
틀렸다는 사실이 **사용자 클러스터에서 며칠 뒤에야** 드러난다.

## 치명적-1: P5 dual-seed 데이터가 통째로 샜다
`criteria/p5.py::normalize_rows()` 가 payload 가 기록한
`seed / seed_provenance / failure_reason / g16_cpu_seconds / qc_code / route / level_label`
를 복사하지 않았고, `collect_p5` 는 `dual_seed_species / seed_pairs / _sigma_note` 를
아예 읽지 않았다.
⟹ **dual-seed 종은 core-h 를 2배 써서 만든 데이터인데**, 최종 회신만으로는
**어느 행이 seed 0 이고 어느 행이 1 인지 알 수 없어 σ_protocol 비교가 불가능**했다.
**"측정해 놓고 안 쓰는 값" 여섯 번째 사례**
(B-3 / `to_dict()` 400자 컷 / `--emit-script` 분기 / `host` / 큐 wall / **이번**).

## 치명적-2: `long` 큐가 실존하면 게이트가 무력화됐다
`resolve_wall_limit()` 이 `qstat -Qf` 전체에서 **가장 긴 큐**의 wall 을 채택했는데,
실제 `-q` 는 `cli.resolve_partition()` 이라는 **완전히 별도 경로**로 정해진다.
⟹ **sizing 은 `long`(120 h)을 가정해 게이트를 통과시키고, 제출은 `-q normal`(24 h)로 나간다.**
🔴 그리고 그 무력화는 **`long` 이 실존하는 순간**, 즉 이 프로젝트가 가장 기대를 거는 바로
그 상황에서 일어난다.
"""

import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import budget, cli, collect, plan, sysprobe
from sei_pilot.criteria import p5
from sei_pilot.shellrun import FakeShell
from sei_pilot.state import Store

QSTAT_MULTI = """Queue: normal
    resources_max.walltime = 24:00:00
    enabled = True
    started = True
Queue: long
    resources_max.walltime = 120:00:00
    enabled = True
    started = True
"""


def p5_rows_with_two_seeds():
    """payload(`P5.sh`)가 실제로 쓰는 형태의 행 2개 — 같은 종, 시드 0/1."""
    base = {"id": "ec", "level": "G-1", "n_atoms": 10, "charge": 0,
            "multiplicity": 1, "wall_h": 1.0, "scf_cycles_max": 12,
            "scf_cycles_total": 30, "opt_cycles": 5, "rc": 0,
            "qc_code": "gaussian16", "route": "#p wB97XD/gen opt freq",
            "level_label": "G-1 (wB97XD/def2-TZVPPD)", "note": "EC"}
    a = dict(base, seed=0, core_hours=1.0, converged=True,
             failure_reason=None, g16_cpu_seconds=3600.0,
             seed_provenance={"seed": 0, "perturbed": False})
    b = dict(base, seed=1, core_hours=1.2, converged=False, rc=1,
             failure_reason="scf_not_converged", g16_cpu_seconds=4200.0,
             seed_provenance={"seed": 1, "perturbed": True,
                              "amplitude_ang": 0.02})
    return [a, b]


class TestP5SeedSurvivesNormalization(unittest.TestCase):
    """🔴 치명적-1."""

    def _rows(self):
        res = p5.evaluate_p5(raw_rows=p5_rows_with_two_seeds(),
                             core_hours=2.2, wall_h=1.0, n_requested=1)
        return res, (res.get("species_rows") or res.get("rows") or [])

    def test_seed_reaches_the_normalized_rows(self):
        """🔴 이것이 없으면 dual-seed 종의 2배 비용이 통째로 무의미해진다."""
        _res, rows = self._rows()
        # 🔴 먼저 **존재**를 단언한다(ADR-042(a)): 없으면 KeyError/TypeError(ERROR) 대신
        #    FAIL 로 보고되게 하기 위해서다. ERROR 는 대개 실험이 잘못된 것이라 증거로 약하다.
        for r in rows:
            self.assertIn("seed", r,
                          "정규화된 행에 seed 키가 없다 — dual-seed 종의 2배 비용이 "
                          "무의미해진다")
        self.assertEqual(sorted(r["seed"] for r in rows), [0, 1],
                         "정규화 후 seed 가 사라졌다 — 어느 행이 어느 시드인지 알 수 없다")

    def test_seed_pair_is_identifiable_for_the_same_species(self):
        """σ_protocol 은 **같은 id · 같은 level 의 seed 0/1 비교**다. 그게 되는가."""
        _res, rows = self._rows()
        pairs = {}
        for r in rows:
            pairs.setdefault((r["id"], r["level"]), []).append(r["seed"])
        self.assertEqual(sorted(pairs[("ec", "G-1")]), [0, 1])

    def test_failure_reason_is_not_lost(self):
        """🔴 미수렴 **원인**이 사라지면 다음 왕복에 같은 질문을 다시 해야 한다."""
        _res, rows = self._rows()
        failed = [r for r in rows if not r["converged"]]
        self.assertTrue(failed)
        self.assertEqual(failed[0]["failure_reason"], "scf_not_converged")

    def test_seed_provenance_and_timings_survive(self):
        _res, rows = self._rows()
        self.assertTrue(all(r.get("seed_provenance") for r in rows))
        self.assertTrue(all(r.get("g16_cpu_seconds") for r in rows))
        self.assertTrue(all(r.get("qc_code") for r in rows))


class TestWallLimitUsesTheSubmitQueue(unittest.TestCase):
    """🔴 치명적-2 — **게이트가 보는 큐 == 제출이 가는 큐.**"""

    def _env(self):
        return {"cores_per_node": 64, "scheduler": "pbs",
                "queues": sysprobe.parse_qstat_all_queues(QSTAT_MULTI),
                "software": {"g16": {"path": "/x/g16"}},
                "vendored": {}, "containers": {}, "qc_module": {"module": None}}

    def _guard(self):
        return budget.ResourceGuard(max_core_hours=21000.0, max_wall_h=48.0)

    def test_submitting_to_normal_uses_normals_wall_not_longs(self):
        """🔴 핵심. `long` 이 **존재해도** `normal` 로 제출하면 24 h 로 sizing 해야 한다."""
        r = plan.resolve_wall_limit(self._env(), self._guard(),
                                    submit_queue="normal")
        self.assertEqual(r["max_wall_h_used"], 24.0,
                         "long 큐가 있다고 그 wall 을 가져다 썼다 — 제출은 normal 로 간다")
        self.assertEqual(r["queue_selected"], "normal")
        self.assertTrue(r["queue_matches_submit"])

    def test_submitting_to_long_uses_longs_wall(self):
        r = plan.resolve_wall_limit(self._env(), self._guard(),
                                    submit_queue="long")
        # 우리 캡(48)이 여전히 상한이다 — 큐가 120 h 를 줘도 우리는 48 을 넘지 않는다.
        self.assertEqual(r["max_wall_h_used"], 48.0)
        self.assertEqual(r["queue_selected"], "long")

    def test_no_queue_selection_happens_at_all(self):
        """🔒 ADR-052 — 큐 **선택 로직 자체를 지웠다.**

        사용자: *"`long` 은 존재하지만 `normal` 이 48 h 다. `long` 은 쓰지 않고 `normal` 만."*
        ⟹ 처음엔 "고른 큐를 알리되 자동 전환은 안 한다"로 고쳤는데, lead 판정은
        **"배선하지 말고 지워라"** 였다:
        *"가장 안전한 코드는 없는 코드다. 발동 조건이 사라진 기능을 배선하는 것은
        표면적만 늘린다."*
        🔴 `long` 이 목록에 **존재해도** 아무 영향이 없어야 한다.
        """
        r = plan.resolve_wall_limit(self._env(), self._guard(),
                                    submit_queue="normal")
        self.assertIsNone(r["longer_queue_available"],
                          "큐 선택/광고 로직이 살아 있다 — ADR-052 로 지웠어야 한다")
        self.assertEqual(r["queue_selected"], "normal")

    def test_wall_that_disagrees_with_the_user_is_loud(self):
        """🔴 사용자 진술(48 h)과 클러스터가 다르면 알려야 한다.

        ADR-036: **측정할 수 있는 것을 하드코딩하지 않는다.** 48 은 "쓰는 값"이 아니라
        **"다르면 알리는 기준값"** 이다 — 사용자 말과 클러스터가 다를 수 있고 그때
        §R22/§R24 의 wall 계산 전제가 무너진다.
        """
        env = self._env()          # 이 픽스처의 normal 은 24 h 다
        r = plan.resolve_wall_limit(env, self._guard(), submit_queue="normal")
        self.assertTrue(r["queue_wall_surprise"])
        self.assertIn("24.0", r["queue_wall_surprise"])
        self.assertIn("48.0", r["queue_wall_surprise"])

    def test_no_surprise_when_the_queue_matches_the_user(self):
        """🔴 오경보 금지. 48 h 면 조용해야 한다."""
        env = self._env()
        env["queues"] = sysprobe.parse_qstat_all_queues(
            "Queue: normal\n    resources_max.walltime = 48:00:00\n"
            "    enabled = True\n    started = True\n")
        r = plan.resolve_wall_limit(env, self._guard(), submit_queue="normal")
        self.assertIsNone(r["queue_wall_surprise"])

    def test_gate_and_submission_disagreement_is_visible(self):
        """불일치가 생기면 **화면에서 크게 보여야** 한다 — 게이트가 거짓말하는 상태다."""
        env = self._env()
        planned, summary = plan.build_plan(env, self._guard(), profile="cpu",
                                           submit_queue="normal")
        summary["queue_matches_submit"] = False          # 불일치 상황을 강제
        summary["queue_selected"], summary["submit_queue"] = "long", "normal"
        text = plan.format_plan_text(planned, summary, env)
        self.assertIn("sizing 이 본 큐", text)
        self.assertIn("wall-kill", text)

    def test_24h_submit_queue_blocks_p1b_even_though_long_exists(self):
        """🔴 통합 확인: `long` 이 있어도 `normal` 로 제출하면 P1b 가 걸려야 한다.

        예전 판은 여기서 **게이트를 통과시켰고**, 제출은 24 h 로 나가 wall-kill 됐을 것이다.
        """
        planned, summary = plan.build_plan(self._env(), self._guard(),
                                           profile="cpu", submit_queue="normal")
        self.assertEqual(summary["sizing_gates"]["blocked_items"], ["P1b"])


if __name__ == "__main__":
    unittest.main()


class TestLongestStageTripwire(unittest.TestCase):
    """🔒 engineer 사전 확약 — **최장 스테이지 실측 > 40 h ⟹ P1 계 축소(C) 발동.**

    🔴 이 값은 `breakdown` 에서 계산해 낼 수 있다. 그런데 **계산이 필요한 안전장치는
    발동하지 않는 안전장치다.** 이 프로젝트에서 "값은 있는데 아무도 안 본" 사례가
    **여섯 번** 났다. 일곱 번째를 자초하지 않으려고 단일 필드로 뽑는다.

    🔴 트립와이어가 얇다: `[ESTIMATE]` 최악 칸이 **47.8 h**(48 h 상한에 여유 0.2 h)다.
    """

    def _recs(self, longest_h):
        return [{"stage": "ts_qst2", "wall_s": longest_h * 3600, "rc": 0,
                 "total_cores": 64},
                {"stage": "irc_forward", "wall_s": 3600, "rc": 0, "total_cores": 64}]

    def test_identifies_the_longest_stage(self):
        from sei_pilot.criteria import cost
        got = cost.longest_stage(self._recs(12.5))
        self.assertEqual(got["stage"], "ts_qst2")
        self.assertAlmostEqual(got["wall_h"], 12.5, places=3)

    def test_tripwire_fires_above_40h(self):
        """🔴 40 h 를 넘으면 **회신이 스스로 말해야 한다.**"""
        from sei_pilot.criteria import cost
        got = cost.longest_stage(self._recs(41.0))
        self.assertTrue(got["exceeds_tripwire"])
        self.assertIn("계 축소", got["note"])
        self.assertIn("체인 링크를 늘려도", got["note"])

    def test_tripwire_quiet_below_40h(self):
        """🔴 오경보 금지."""
        from sei_pilot.criteria import cost
        got = cost.longest_stage(self._recs(39.0))
        self.assertFalse(got["exceeds_tripwire"])

    def test_no_records_is_unknown_not_safe(self):
        """🔴 기록이 없으면 '안전'이 아니라 **판정 불가**다 (ADR-036)."""
        from sei_pilot.criteria import cost
        got = cost.longest_stage([])
        self.assertIsNone(got["exceeds_tripwire"])
        self.assertIn("판정할 수 없다", got["note"])


class TestTripwireReachesTheFinalResult(unittest.TestCase):
    """🔴 [critic3] **트립와이어가 자기 존재 이유를 어기고 있었다.**

    `collect_p1` 의 `res["longest_stage"] = …` 한 줄을 지워도 **714건 중 한 건도 안 깨졌다.**
    `longest_stage()` 단위 테스트 4건은 전부 함수를 **직접** 부르고,
    **`collect_p1()` 을 거쳐 최종 결과까지 가는지는 아무도 안 봤다.**
    ⟹ **ADR-041 이 겨냥한 바로 그 구멍이, "측정해 놓고 안 쓰는 값"을 막으려고 만든
    안전장치 자신에게서 재발했다.**

    그래서 이 테스트는 **디스크에 진짜 `stages/*.json` 을 놓고 `collect_p1()` 을 호출**한다.
    """

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_trip_")
        self.store = Store(self.d)
        self.jd = self.store.job_dir("P1")
        os.makedirs(os.path.join(self.jd, "stages"), exist_ok=True)
        self.store.mark_submitted("P1", {"jobid": "1"})
        self.store.mark_done("P1", {"start_epoch": 0, "end_epoch": 3600})

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _stage(self, name, wall_h):
        """payload 의 `sei_stage` 가 남기는 것과 같은 형태로 디스크에 놓는다."""
        with open(os.path.join(self.jd, "stages", name + ".json"), "w") as fh:
            json.dump({"stage": name, "rc": 0, "wall_s": wall_h * 3600,
                       "total_cores": 64, "link": "P1"}, fh)

    def test_longest_stage_reaches_collect_p1_output(self):
        """🔴 필드가 **최종 결과까지** 오는가 — 함수가 맞는 것과는 다른 질문이다."""
        self._stage("ts_qst2", 12.0)
        self._stage("irc_forward", 3.0)
        res = collect.collect_p1(self.store)
        self.assertIn("longest_stage", res,
                      "collect_p1 결과에 longest_stage 가 없다 — 필드가 조립선에서 사라졌다")
        self.assertEqual(res["longest_stage"]["stage"], "ts_qst2")
        self.assertAlmostEqual(res["longest_stage"]["wall_h"], 12.0, places=3)

    def test_tripwire_firing_reaches_the_human_channel(self):
        """🔴 발동하면 **`warnings[]` 에도** 실려야 한다.

        필드에만 있으면 받는 사람이 `pilots[].longest_stage` 를 따로 뒤져야 하고,
        그건 이 필드가 없애려던 바로 그 상태다.
        """
        self._stage("ts_qst2", 41.0)          # 40 h 초과
        res = collect.collect_p1(self.store)
        self.assertTrue(res["longest_stage"]["exceeds_tripwire"])
        joined = " ".join(res.get("warnings") or [])
        self.assertIn("계 축소", joined,
                      "트립와이어가 발동했는데 warnings[] 에 아무것도 없다")

    def test_no_false_alarm_below_the_tripwire(self):
        """🔴 오경보 금지 — 경고가 흔해지면 아무도 안 읽는다."""
        self._stage("ts_qst2", 20.0)
        res = collect.collect_p1(self.store)
        self.assertFalse(res["longest_stage"]["exceeds_tripwire"])
        self.assertNotIn("계 축소", " ".join(res.get("warnings") or []))

    def test_tripwire_reaches_the_report_json(self):
        """조립선 끝(디스크의 회신 JSON)까지."""
        self._stage("ts_qst2", 41.0)
        args = cli.build_parser().parse_args(
            ["collect", "--workdir", self.d, "--pkg-root", context.PKG_ROOT])
        path = cli.cmd_collect(
            args, shell=FakeShell(responses={"hostname -f": (0, "h\n", "")},
                                  which_map={}), store=Store(self.d))
        with open(path) as fh:
            rep = json.load(fh)
        p1 = next(p for p in rep["pilots"] if p["id"] == "P1")
        self.assertTrue(p1["longest_stage"]["exceeds_tripwire"])
        self.assertIn("계 축소", " ".join(p1.get("warnings") or []))
