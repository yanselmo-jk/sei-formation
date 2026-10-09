"""L4 배치 통합 계획기/검증기 테스트.

이 도구의 목적은 **왕복을 늘리는 배치를 제출 전에 거부하는 것**이다.
따라서 테스트의 핵심은 "위반을 실제로 잡는가"이며, 각 규칙마다 **통과 케이스와
위반 케이스를 쌍으로** 둔다(양성 대조군 없이 "안 터졌다"는 검증이 아니다).

L3와 마찬가지로 전부 로컬에서 돈다 — ADR-004의 실행 검증 제약 밖이다.
"""

import contextlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

import context  # noqa: F401

sys.path.insert(0, os.path.join(context.REPO_ROOT, "src"))

from batch_planner import cli as cli_mod        # noqa: E402
from batch_planner import model as model_mod    # noqa: E402
from batch_planner import plan as plan_mod      # noqa: E402
from batch_planner import validate as V         # noqa: E402

CONFIG_DIR = os.path.join(context.REPO_ROOT, "src", "config")


def item(iid, rt, **kw):
    kw.setdefault("title", iid)
    return model_mod.WorkItem(id=iid, rt=rt, **kw)


def good_plan_items():
    return [
        item("P1", "RT-1", core_hours=1000, wall_h=8, needs_return=True),
        item("S1", "RT-2", core_hours=5000, wall_h=12, depends_on=["P1"]),
        item("probe", "RT-2", core_hours=6, wall_h=1, needs_return=True),
        item("disc", "RT-3", stage="discover", writes="ledger", wall_h=20,
             depends_on=["probe"]),
        item("rank", "RT-3", stage="rank", writes="working_network", wall_h=2,
             needs_return=True, depends_on=["disc"]),
    ]


class TestModel(unittest.TestCase):
    def test_config_loads_and_matches_confirmed_structure(self):
        p = model_mod.load_plan(CONFIG_DIR)
        self.assertEqual(p.target_roundtrips, 7)
        self.assertEqual([r["id"] for r in p.roundtrips],
                         ["RT-%d" % i for i in range(1, 8)])
        self.assertAlmostEqual(p.roundtrip_days, 3.5)
        self.assertAlmostEqual(p.max_wall_h, 24.0)

    def test_rt3_is_must_not_split_with_quantified_penalty(self):
        p = model_mod.load_plan(CONFIG_DIR)
        self.assertTrue(p.must_not_split("RT-3"))
        self.assertEqual(p.split_penalty_weeks("RT-3"), [1.5, 2.0])
        self.assertFalse(p.must_not_split("RT-1"))

    def test_dag_critical_path_matches_declared_days(self):
        """🔴 문서(§R8.5)는 직렬 서술이고 총 7.5일 = 단순 합이다.

        임계경로가 선언값과 어긋나면 **내가 문서에 없는 병렬성을 가정한 것**이다.
        (실제로 개발 중 그 실수를 했고 이 테스트가 그 재발을 막는다.)
        """
        p = model_mod.load_plan(CONFIG_DIR)
        self.assertAlmostEqual(p.dag_critical_path_days(),
                               p.rt3_dag["total_days"], places=3)

    def test_parallelization_is_recorded_as_an_open_question_not_assumed(self):
        p = model_mod.load_plan(CONFIG_DIR)
        qs = p.cfg.get("open_questions") or []
        q = [x for x in qs if x["id"] == "Q-RT3-PAR"]
        self.assertEqual(len(q), 1)
        self.assertEqual(q[0]["owner"], "engineer")
        self.assertIn("UNRESOLVED", q[0]["status"])

    def test_unknown_field_is_rejected_not_ignored(self):
        """오타 필드를 조용히 무시하면 그 작업이 계획에서 통째로 빠진다."""
        self.assertRaises(ValueError, model_mod.WorkItem,
                          id="x", rt="RT-1", core_hour=5)

    def test_item_without_id_is_rejected(self):
        self.assertRaises(ValueError, model_mod.WorkItem, rt="RT-1")

    def test_example_work_items_file_is_valid_and_passes(self):
        items = model_mod.load_work_items(
            os.path.join(CONFIG_DIR, "work_items.example.json"))
        p = model_mod.load_plan(CONFIG_DIR)
        s = plan_mod.summarize(p, items)
        self.assertEqual(s["verdict"], V.INFO)
        self.assertEqual(s["n_roundtrips_used"], 7)


class TestRules(unittest.TestCase):
    def setUp(self):
        self.p = model_mod.load_plan(CONFIG_DIR)

    def _rules(self, items):
        return set(f["rule"] for f in V.validate(self.p, items))

    def test_good_plan_has_no_findings(self):
        self.assertEqual(V.validate(self.p, good_plan_items()), [])

    # --- V1 ---
    def test_v1_unassigned_item(self):
        items = good_plan_items() + [item("x", None)]
        self.assertIn("V1", self._rules(items))

    def test_v1_unknown_rt(self):
        items = good_plan_items() + [item("x", "RT-99")]
        self.assertIn("V1", self._rules(items))

    # --- V2: L4의 핵심 ---
    def test_v2_rt3_split_is_rejected_with_cost(self):
        items = good_plan_items()
        items.append(item("mid", "RT-3", stage="thermo_dft", needs_return=True))
        found = [f for f in V.validate(self.p, items) if f["rule"] == "V2"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["severity"], V.ERROR)
        self.assertEqual(found[0]["calendar_cost_weeks"], 2.0)   # 대가를 숫자로
        self.assertIn("1.5~2", found[0]["message"])

    def test_v2_allows_single_return_point_in_rt3(self):
        self.assertNotIn("V2", self._rules(good_plan_items()))

    def test_v2_does_not_fire_on_splittable_rt(self):
        items = good_plan_items()
        items.append(item("a", "RT-4", needs_return=True))
        items.append(item("b", "RT-4", needs_return=True))
        self.assertNotIn("V2", self._rules(items))       # RT-4는 분할 금지가 아니다

    # --- V3 ---
    def test_v3_dependency_inversion(self):
        items = good_plan_items()
        items.append(item("late", "RT-2", depends_on=["rank"]))   # rank는 RT-3
        found = [f for f in V.validate(self.p, items) if f["rule"] == "V3"]
        self.assertTrue(found)
        self.assertIn("앞선 왕복", found[0]["message"])

    def test_v3_missing_dependency(self):
        items = good_plan_items() + [item("x", "RT-4", depends_on=["nonexistent"])]
        self.assertIn("V3", self._rules(items))

    def test_v3_same_rt_dependency_is_ok(self):
        items = good_plan_items() + [item("x", "RT-3", depends_on=["disc"])]
        self.assertNotIn("V3", self._rules(items))

    # --- V4 ---
    def test_v4_wall_limit(self):
        items = good_plan_items() + [item("long", "RT-4", wall_h=30)]
        found = [f for f in V.validate(self.p, items) if f["rule"] == "V4"]
        self.assertTrue(found)
        self.assertIn("체인", found[0]["message"])

    def test_v4_exactly_at_limit_is_ok(self):
        items = good_plan_items() + [item("edge", "RT-4", wall_h=24.0)]
        self.assertNotIn("V4", self._rules(items))

    # --- V5 ---
    def test_v5_extra_return_points_cost_calendar(self):
        items = good_plan_items()
        items += [item("r1", "RT-4", needs_return=True),
                  item("r2", "RT-4", needs_return=True),
                  item("r3", "RT-4", needs_return=True)]
        found = [f for f in V.validate(self.p, items) if f["rule"] == "V5"]
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], V.WARN)
        self.assertAlmostEqual(found[0]["calendar_cost_weeks"], 1.0, places=1)  # 2×3.5일

    # --- V6 ---
    def test_v6_roundtrip_count_within_target(self):
        self.assertNotIn("V6", self._rules(good_plan_items()))

    def test_v6_exceeding_target_is_error(self):
        small = model_mod.RTPlan(dict(model_mod.load_plan(CONFIG_DIR).cfg,
                                      targets={"roundtrips": 2,
                                               "roundtrip_calendar_days": 3.5,
                                               "max_wall_h_per_job": 24.0}))
        found = [f for f in V.validate(small, good_plan_items()) if f["rule"] == "V6"]
        self.assertTrue(found)
        self.assertIn("초과", found[0]["message"])

    # --- V7: ADR-027 자료구조 규칙 ---
    def test_v7_pruning_the_ledger_is_forbidden(self):
        items = good_plan_items()
        items.append(item("bad", "RT-3", writes="ledger",
                          title="발견 + flux 가지치기"))
        found = [f for f in V.validate(self.p, items) if f["rule"] == "V7"]
        self.assertTrue(found)
        self.assertIn("완결성", found[0]["message"])

    def test_v7_completeness_from_working_network_is_forbidden(self):
        items = good_plan_items()
        items.append(item("bad2", "RT-3", writes="working_network",
                          title="Chao1 완결성 추정"))
        self.assertIn("V7", self._rules(items))

    def test_v7_manual_clock_sync_is_forbidden(self):
        items = good_plan_items()
        items.append(item("bad3", "RT-4", note="두 시계 수동 동기화"))
        self.assertIn("V7", self._rules(items))

    def test_v7_legitimate_pruning_on_working_network_is_allowed(self):
        """가지치기 자체는 금지가 아니다 — **원장에 하는 것**이 금지다."""
        items = good_plan_items()
        items.append(item("ok", "RT-3", writes="working_network",
                          title="L2 flux 가지치기"))
        self.assertNotIn("V7", self._rules(items))

    # --- V8 ---
    def test_v8_unknown_stage_is_warned(self):
        items = good_plan_items() + [item("x", "RT-3", stage="enumrate")]
        found = [f for f in V.validate(self.p, items) if f["rule"] == "V8"]
        self.assertTrue(found)
        self.assertEqual(found[0]["severity"], V.WARN)

    def test_v8_known_stage_is_fine(self):
        items = good_plan_items() + [item("x", "RT-3", stage="enumerate")]
        self.assertNotIn("V8", self._rules(items))


class TestSummary(unittest.TestCase):
    def setUp(self):
        self.p = model_mod.load_plan(CONFIG_DIR)

    def test_calendar_and_totals(self):
        s = plan_mod.summarize(self.p, good_plan_items())
        self.assertEqual(s["n_roundtrips_used"], 3)
        self.assertAlmostEqual(s["calendar_days_roundtrips"], 10.5)   # 3 × 3.5
        self.assertAlmostEqual(s["total_core_hours"], 6006.0)
        self.assertEqual(s["verdict"], V.INFO)

    def test_penalty_is_reported_when_structure_broken(self):
        items = good_plan_items()
        items.append(item("mid", "RT-3", needs_return=True))
        s = plan_mod.summarize(self.p, items)
        self.assertEqual(s["verdict"], V.ERROR)
        self.assertAlmostEqual(s["calendar_penalty_weeks"], 2.0)


class TestDrift(unittest.TestCase):
    """config 는 문서에서 옮겨 적은 데이터다. 문서가 바뀌면 조용히 낡는다(L3의 교훈)."""

    def setUp(self):
        self.p = model_mod.load_plan(CONFIG_DIR)
        with open(os.path.join(context.REPO_ROOT, "docs", "03_COMPUTE_PLAN.md"),
                  errors="replace") as fh:
            self.doc = fh.read()

    def test_real_doc_table_parses_all_seven(self):
        rows = plan_mod.parse_rt_table(self.doc)
        self.assertEqual([r["id"] for r in rows],
                         ["RT-%d" % i for i in range(1, 8)])

    def test_bold_markup_row_is_parsed(self):
        """`| **7** | **W18** | ... |` — 굵게 표기를 못 읽어 드리프트 오탐이 났었다."""
        rows = plan_mod.parse_rt_table(
            "### R8.5\n| **7** | **W18** | **데모 1계** | 🟢 |\n### R8.6\n")
        self.assertEqual(rows, [{"id": "RT-7", "week": 18, "title": "데모 1계"}])

    def test_config_matches_the_document_today(self):
        self.assertTrue(plan_mod.check_drift(self.p, self.doc)["ok"])

    def test_drift_detected_when_week_changes(self):
        doc = self.doc.replace("| 3 | W7 |", "| 3 | W8 |")
        d = plan_mod.check_drift(self.p, doc)
        self.assertFalse(d["ok"])
        self.assertTrue(any(p["kind"] == "week_mismatch" for p in d["problems"]))

    def test_drift_detected_when_table_missing(self):
        d = plan_mod.check_drift(self.p, "# 문서에 표가 없다")
        self.assertFalse(d["ok"])
        self.assertEqual(d["problems"][0]["kind"], "doc_table_not_found")


class TestCli(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_l4_")

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    @staticmethod
    def _run(argv):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = cli_mod.main(argv)
        return rc, buf.getvalue()

    def _write(self, items):
        path = os.path.join(self.d, "items.json")
        with open(path, "w") as fh:
            json.dump({"items": [i.to_dict() for i in items]}, fh, ensure_ascii=False)
        return path

    def test_show(self):
        rc, out = self._run(["show", "--config-dir", CONFIG_DIR])
        self.assertEqual(rc, 0)
        self.assertIn("RT-3", out)
        self.assertIn("분할 금지", out)
        self.assertIn("prune_ledger", out)

    def test_validate_good_plan_exits_zero(self):
        rc, out = self._run(["validate", self._write(good_plan_items()),
                             "--config-dir", CONFIG_DIR])
        self.assertEqual(rc, 0)
        self.assertIn("위반 없음", out)

    def test_validate_broken_plan_exits_nonzero(self):
        items = good_plan_items() + [item("mid", "RT-3", needs_return=True)]
        rc, out = self._run(["validate", self._write(items),
                             "--config-dir", CONFIG_DIR])
        self.assertEqual(rc, 1)
        self.assertIn("계획 불성립", out)
        self.assertIn("V2", out)

    def test_validate_json_mode(self):
        rc, out = self._run(["validate", self._write(good_plan_items()),
                             "--config-dir", CONFIG_DIR, "--json"])
        self.assertEqual(rc, 0)
        self.assertIn("per_rt", json.loads(out))

    def test_missing_items_file_is_reported_not_crashed(self):
        rc, out = self._run(["validate", os.path.join(self.d, "nope.json"),
                             "--config-dir", CONFIG_DIR])
        self.assertEqual(rc, 2)
        self.assertIn("읽지 못했다", out)

    def test_drift_command_on_real_docs(self):
        rc, out = self._run(["drift", "--root", context.REPO_ROOT,
                             "--config-dir", CONFIG_DIR])
        self.assertEqual(rc, 0)
        self.assertIn("일치", out)


if __name__ == "__main__":
    unittest.main()
