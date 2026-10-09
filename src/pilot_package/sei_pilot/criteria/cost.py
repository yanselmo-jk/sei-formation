"""하위 단계별 core-h 분해 — payload가 남긴 stages/*.json 을 읽어 계산한다.

§R2-6 P1의 회신 요구사항: breakdown {crest, ts_guess, ts_opt, irc, freq}.
단가 스프레드 8배를 3배로 줄이는 것이 이 숫자의 목적이므로,
**어느 단계가 지배적인지**가 총합보다 중요하다.
"""

import json
import os

from .. import units


def read_stage_records(job_dir):
    """<job_dir>/stages/*.json → [{stage, wall_s, total_cores, rc}, ...]"""
    d = os.path.join(job_dir, "stages")
    out = []
    if not os.path.isdir(d):
        return out
    for fn in sorted(os.listdir(d)):
        if not fn.endswith(".json"):
            continue
        try:
            with open(os.path.join(d, fn)) as fh:
                out.append(json.load(fh))
        except (OSError, ValueError):
            continue
    return out


def breakdown_core_hours(stage_records, stage_names=None):
    """단계 → core-h. stage_names를 주면 없는 단계는 0.0으로 채운다(누락 구분용)."""
    bd = {}
    for rec in stage_records:
        name = rec.get("stage", "unknown")
        wall_s = float(rec.get("wall_s", 0) or 0)
        cores = float(rec.get("total_cores", 1) or 1)
        bd[name] = round(bd.get(name, 0.0) + units.core_hours(cores, wall_s), 4)
    if stage_names:
        for name in stage_names:
            bd.setdefault(name, 0.0)
    return bd


#: 🔒 engineer 사전 확약 (§R22.6 / ADR-049) — **최장 스테이지가 이 값을 넘으면 (C) 계 축소 발동.**
#: `[ESTIMATE]` 최악 칸이 47.8 h(여유 0.2 h)라 트립와이어가 얇다.
LONGEST_STAGE_TRIPWIRE_H = 40.0


def longest_stage(stage_records, tripwire_h=LONGEST_STAGE_TRIPWIRE_H):
    """가장 오래 걸린 단계 — **트립와이어와 대조 가능한 단일 값으로** 낸다.

    🔴 왜 파생값을 따로 싣는가: 이 값은 `breakdown` 에서 계산해 낼 수 있다. 그런데
    **계산이 필요한 안전장치는 발동하지 않는 안전장치다.** 이 프로젝트에서 "값은 있는데
    아무도 안 본" 사례가 **여섯 번** 났다(B-3 / 400자 컷 / emit 분기 / host / 큐 wall /
    P5 seed). 일곱 번째를 자초하지 않는다.

    🔒 용도: engineer 사전 확약 — **최장 스테이지 실측 > 40 h 이면 P1 계 축소(C)를 발동**한다.
    그 판정은 `[ESTIMATE]` 최악 칸이 47.8 h(48 h 상한에 여유 0.2 h)여서 얇다.
    ⟹ **실측이 오면 자동으로 대조되어야 하고, 사람이 breakdown 을 뒤지게 두면 안 된다.**
    """
    best = None
    for rec in stage_records or []:
        wall_s = float(rec.get("wall_s", 0) or 0)
        if best is None or wall_s > best["wall_s"]:
            best = {"stage": rec.get("stage", "unknown"), "wall_s": wall_s,
                    "total_cores": rec.get("total_cores")}
    if best is None:
        return {"stage": None, "wall_h": None, "exceeds_tripwire": None,
                "tripwire_h": tripwire_h,
                "note": "단계 기록이 없다 — **트립와이어를 판정할 수 없다**(미측정)."}
    wall_h = best["wall_s"] / 3600.0
    return {
        "stage": best["stage"],
        "wall_h": round(wall_h, 4),
        "total_cores": best["total_cores"],
        "tripwire_h": tripwire_h,
        "exceeds_tripwire": bool(wall_h > tripwire_h),
        "note": ("🔴 최장 단계가 %.2f h 로 트립와이어 %.0f h 를 넘었다 ⟹ **engineer 사전 확약에 "
                 "따라 P1 계 축소(C)를 proposer 에게 올려야 한다.** 체인 링크를 늘려도 "
                 "구제되지 않는다 — 단일 단계는 쪼개지지 않기 때문이다."
                 % (wall_h, tripwire_h)) if wall_h > tripwire_h else
                ("최장 단계 %.2f h < 트립와이어 %.0f h. (C) 미발동."
                 % (wall_h, tripwire_h)),
    }


def total_core_hours(stage_records):
    return round(sum(breakdown_core_hours(stage_records).values()), 4)


def stage_status(stage_records):
    """단계별 rc. 어느 단계에서 죽었는지 회신하기 위함."""
    return dict((r.get("stage", "unknown"), int(r.get("rc", -1))) for r in stage_records)


def job_wall_hours(marker_payload):
    """common.sh가 남긴 done/failed 마커의 start/end epoch → wall h."""
    if not marker_payload:
        return None
    try:
        s = float(marker_payload["start_epoch"])
        e = float(marker_payload["end_epoch"])
    except (KeyError, TypeError, ValueError):
        return None
    return round((e - s) * units.S_TO_H, 4)
