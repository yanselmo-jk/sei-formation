"""L4 배치 통합 — 왕복(RT) 계획 모델.

목적(§R3.4 L4): **왕복 횟수를 늘리는 배치를 만들지 못하게 막는다.**
왕복 1회 = 달력 3.5일(§R2-2)이고, 🔴 **RT-3을 쪼개면 1.5~2.0주를 잃는다**(§R8.5).

이 도구는 **계획기/검증기**다. 파이프라인을 실행하지 않는다 —
U-22(레벨 선택)가 열려 있고 단가가 전부 `[ESTIMATE]`이므로(ADR-004) 실행기를 지금 짜면
파라미터를 추정으로 박게 된다. lead 판정: (A)안.
"""

import json
import os

CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")
RT_PLAN = "rt_plan.json"


class WorkItem(object):
    """배치에 넣으려는 작업 하나.

    needs_return=True 는 **"이 작업이 끝난 결과를 사람이 보고 다음을 정해야 한다"**는 뜻이다.
    그것이 곧 왕복 1회이며, RT 안에 그런 항목이 2개 이상이면 그 RT는 쪼개진다.
    """

    FIELDS = ("id", "title", "rt", "stage", "depends_on", "core_hours", "wall_h",
              "needs_return", "writes", "owner", "note")

    def __init__(self, **kw):
        unknown = sorted(set(kw) - set(self.FIELDS))
        if unknown:
            raise ValueError("알 수 없는 작업 항목 필드: %s (오타는 조용히 무시하면 "
                             "계획에서 통째로 빠진다)" % ", ".join(unknown))
        self.id = kw.get("id")
        self.title = kw.get("title", "")
        self.rt = kw.get("rt")
        self.stage = kw.get("stage")
        self.depends_on = list(kw.get("depends_on") or [])
        self.core_hours = float(kw.get("core_hours") or 0.0)
        self.wall_h = float(kw.get("wall_h") or 0.0)
        self.needs_return = bool(kw.get("needs_return"))
        self.writes = kw.get("writes")          # ledger | working_network | None
        self.owner = kw.get("owner")
        self.note = kw.get("note", "")
        if not self.id:
            raise ValueError("작업 항목에 id가 없다")

    def to_dict(self):
        return dict((f, getattr(self, f)) for f in self.FIELDS)


class RTPlan(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.roundtrips = cfg.get("roundtrips") or []
        self.by_id = dict((r["id"], r) for r in self.roundtrips)
        self.targets = cfg.get("targets") or {}
        self.rt3_dag = cfg.get("rt3_dag") or {}
        self.rules = cfg.get("data_structure_rules") or {}

    # --- 조회 ---
    def order(self, rt_id):
        for i, r in enumerate(self.roundtrips):
            if r["id"] == rt_id:
                return i
        return None

    def must_not_split(self, rt_id):
        return bool((self.by_id.get(rt_id) or {}).get("must_not_split"))

    def split_penalty_weeks(self, rt_id):
        return (self.by_id.get(rt_id) or {}).get("split_penalty_weeks")

    @property
    def target_roundtrips(self):
        return int(self.targets.get("roundtrips", len(self.roundtrips)))

    @property
    def roundtrip_days(self):
        return float(self.targets.get("roundtrip_calendar_days", 3.5))

    @property
    def max_wall_h(self):
        return float(self.targets.get("max_wall_h_per_job", 24.0))

    def dag_stage_ids(self):
        return [s["id"] for s in (self.rt3_dag.get("stages") or [])]

    def dag_critical_path_days(self):
        """RT-3 내부 DAG의 임계 경로(일). 병렬 단계는 겹친다."""
        stages = dict((s["id"], s) for s in (self.rt3_dag.get("stages") or []))
        memo = {}

        def finish(sid):
            if sid in memo:
                return memo[sid]
            s = stages[sid]
            start = max([finish(d) for d in s.get("depends_on") or []] or [0.0])
            memo[sid] = start + float(s.get("days", 0.0))
            return memo[sid]

        return round(max([finish(s) for s in stages] or [0.0]), 3)


def load_plan(config_dir=None, filename=RT_PLAN):
    path = os.path.join(config_dir or CONFIG_DIR, filename)
    with open(path) as fh:
        cfg = json.load(fh)
    cfg["_source_path"] = path
    return RTPlan(cfg)


def load_work_items(path):
    with open(path) as fh:
        data = json.load(fh)
    items = data.get("items") if isinstance(data, dict) else data
    return [WorkItem(**it) for it in (items or [])]
