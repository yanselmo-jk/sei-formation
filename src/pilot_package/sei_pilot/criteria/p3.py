"""P3 판정 — EC 라디칼 1개 gen-1 자동 탐색 완주.

§R2-6 판정 기준: 열거 완료, xTB TS 시도 >= 50건 종료.
회신: 🔴 **반응체당 candidate 수(분포 포함)**, 시도 1건당 core-h, 수렴률.
(R-06: "반응체당 150개"는 순수 추정이며 3배 틀리면 S2 견적이 3배 틀린다.)

🔴 해석상 주의 — 반드시 회신 JSON에 함께 실린다:
   ADR-006이 잠정 채택한 S2-A(열거-후-여과 CRN, fragment-recombine + species pool)의
   fanout과, 이 파일럿이 쓰는 열거 모드의 fanout은 **같은 수가 아니다.**
   * enumeration_mode = "libe_pool_recombine" : S2-A와 동형. 이 값이 S2 견적에 직접 들어간다.
   * enumeration_mode = "b2f2_graph_edit"     : YARP류 그래프 편집. **S2-A 견적에 직접
     대입하면 안 된다.** 이 모드에서 신뢰할 수 있는 회신은 xTB 시도 1건당 단가와
     수렴률(엔진 무관)이다.
   어느 모드가 돌았는지 스크립트가 기록하고, 오독 방지 문구를 JSON에 넣는다.
"""

MIN_ATTEMPTS = 50


def _percentile(sorted_vals, q):
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def candidate_distribution(per_reactant_counts):
    """반응체당 candidate 수 분포. 평균만 회신하면 꼬리를 잃는다."""
    vals = sorted(float(v) for v in (per_reactant_counts or []))
    if not vals:
        return {"n_reactants": 0, "mean": None, "median": None,
                "p10": None, "p90": None, "min": None, "max": None,
                "histogram": {}, "raw_counts": []}
    hist = {}
    for v in vals:
        # log-ish 버킷 (분포의 꼬리를 보기 위함)
        b = "0" if v == 0 else ("1-9" if v < 10 else
                                ("10-49" if v < 50 else
                                 ("50-199" if v < 200 else
                                  ("200-999" if v < 1000 else ">=1000"))))
        hist[b] = hist.get(b, 0) + 1
    return {
        "n_reactants": len(vals),
        "mean": round(sum(vals) / len(vals), 2),
        "median": round(_percentile(vals, 0.5), 2),
        "p10": round(_percentile(vals, 0.10), 2),
        "p90": round(_percentile(vals, 0.90), 2),
        "min": vals[0], "max": vals[-1],
        "histogram": hist,
        "raw_counts": [int(v) for v in vals][:500],
    }


def attempt_stats(attempts):
    """attempts = [{"wall_s":..,"cores":..,"converged":bool,"rc":int}, ...]"""
    from .. import units
    n = len(attempts or [])
    if n == 0:
        return {"n_attempts": 0, "core_hours_total": 0.0,
                "core_hours_per_attempt": None, "convergence_rate": None,
                "n_converged": 0, "n_crashed": 0}
    ch = 0.0
    conv = 0
    crashed = 0
    for a in attempts:
        ch += units.core_hours(a.get("cores", 1) or 1, a.get("wall_s", 0) or 0)
        if a.get("converged"):
            conv += 1
        if (a.get("rc") or 0) != 0:
            crashed += 1
    return {
        "n_attempts": n,
        "core_hours_total": round(ch, 4),
        "core_hours_per_attempt": round(ch / n, 5),
        "n_converged": conv,
        "n_crashed": crashed,
        "convergence_rate": round(conv / float(n), 4),
    }


def evaluate_p3(per_reactant_counts, attempts, enumeration_mode,
                enumeration_completed, enumeration_core_hours=None,
                wall_h=None, pool_size=None):
    dist = candidate_distribution(per_reactant_counts)
    stats = attempt_stats(attempts)
    reasons = []
    if not enumeration_completed:
        reasons.append("enumeration_did_not_complete")
    if stats["n_attempts"] < MIN_ATTEMPTS:
        reasons.append("xtb_ts_attempts %d < %d" % (stats["n_attempts"], MIN_ATTEMPTS))
    passed = bool(enumeration_completed) and stats["n_attempts"] >= MIN_ATTEMPTS

    if enumeration_mode == "libe_pool_recombine":
        interp = ("S2-A(ADR-006)와 동형 열거. candidate 분포를 S2 fanout 견적에 "
                  "직접 쓸 수 있다.")
    else:
        interp = ("🔴 이 candidate 분포는 YARP류 그래프 편집(b2f2) fanout이다. "
                  "S2-A(fragment-recombine + pool) fanout과 같지 않으므로 S2 견적에 "
                  "직접 대입하지 마라. 이 실행에서 엔진 무관하게 신뢰할 수 있는 값은 "
                  "'시도 1건당 core-h'와 '수렴률'이다.")

    return {
        "id": "P3",
        "status": "pass" if passed else "fail",
        "core_hours_total": round((enumeration_core_hours or 0.0)
                                  + stats["core_hours_total"], 4),
        "wall_h": wall_h,
        "criteria": {
            "enumeration_completed": bool(enumeration_completed),
            "xtb_ts_attempts": stats["n_attempts"],
            "xtb_ts_attempts_required": MIN_ATTEMPTS,
        },
        "measurements": {
            "enumeration_mode": enumeration_mode,
            "species_pool_size": pool_size,
            "candidates_per_reactant": dist,
            "xtb_attempts": stats,
            "enumeration_core_hours": enumeration_core_hours,
        },
        "interpretation_note": interp,
        "fail_reasons": reasons,
    }
