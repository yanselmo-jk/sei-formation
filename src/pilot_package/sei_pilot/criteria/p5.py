"""P5 판정 — 소분자 opt+freq **단가 곡선**.

왜 필요한가 (lead 지시 / engineer RUNBOOK §R15): ADR-026(LIBE 포기) + ADR-028(계층화 폐기)로
**전 pool thermo(2,142종 × opt+freq)가 계당 최대 비용 항목**이 됐는데 그 단가가 어디서도
측정되지 않았다. P1은 40~80원자 TS 워크플로를, P1b는 그 위의 레벨 비율을 잰다.
**5~25원자 소분자 opt+freq는 미측정이다.**

🔴 **단일 숫자를 내지 않는다.** pool에는 크기 분포가 있으므로 평균 한 개는 어차피 틀린다.
종별 원자료 `(원자수, 전하, 스핀다중도, core-h, wall, SCF 반복수, 수렴 여부)`를 **그대로**
회신하고, 곡선 적합은 받는 쪽(engineer)이 한다. 여기서 계산하는 요약값은 전부
`diagnostics`(참고용)이며 원자료가 정본이다.

자동 판정 (engineer §R13.2, **값싼 레벨 60 core-h 가정 기준**):
    <= 90        → pool 그대로
    90 ~ 150     → pool 축소
    > 150        → 계층화 부활
⚠ 이 임계는 **값싼 레벨** 기준이다. 고수준(ADR-029 기본 레벨) 값에 그대로 적용하지 않고,
   판정에 `threshold_basis` 라벨을 달아 어느 레벨 기준인지 항상 드러낸다.
"""

import math

from . import g16

VERDICT_KEEP_MAX = 90.0
VERDICT_SHRINK_MAX = 150.0

# =============================================================================================
# 🔴 [critic10] LEVEL LABELS — DERIVED FROM CONFIG, NEVER HARDCODED
# =============================================================================================
# These were literals, and all three fields of both were WRONG:
#     was `wB97X-V/def2-TZVPPD/SMD`   config says wB97XD, and the solvent is PCM eps 18.5
#     was `wB97X-D3/def2-TZVP/SMD`    config says wB97XD/def2-TZVPD
# 🔴 The `/SMD` is the part that matters. This project spent **14,464 core-h** on runs whose
# solvent was not what the label said (acetonitrile eps 35.7, ADR-066/067), and ADR-108 moved
# production to PCM eps 18.5. A reply that says "SMD" after that is the same confusion written
# into the output -- and these strings go OUT, into the reply a human reads.
# 🔒 So they are derived from the single sources that already exist (`qc_levels.json`'s level
# blocks and its `solvent_policy`) rather than restated here. A literal cannot help but drift;
# a derivation cannot drift without the config changing under it.
# ⚠ They remain the dict KEYS used to match rows by level, and both sides (payload/P5.sh and
# this module) read them from here -- so internal consistency is preserved by construction.

def _solvent_label(policy):
    """How the level's solvent should be NAMED in a reply. Reads the same decision the deck
    reads, so a label can never describe a solvent the run did not use."""
    model = (policy or {}).get("model")
    if model == "pcm_numeric":
        eps = (policy or {}).get("epsilon")
        return "PCM(eps=%s)" % eps if eps is not None else "PCM(eps=?)"
    if model == "smd_descriptors":
        return "SMD"
    return "solvent-undecided"


def level_label(level_key, cfg=None):
    """`"level1"|"level2"|"level3"` -> the human-facing label for that level.

    🔴 Every field comes from config. If a functional, basis or solvent decision changes, the
    label changes with it -- which is the whole point.
    """
    from .. import config as _config
    cfg = cfg if cfg is not None else _config.load("qc_levels.json")
    g = cfg.get("gaussian16") or {}
    block = g.get(level_key)
    # 🔴 An unknown level, or one missing its functional/basis, must NOT render as
    #    `?/?/PCM(eps=18.5)` -- that is a plausible-looking level string with two holes in it,
    #    and it would travel into a reply looking like a description of a real level.
    #    Refuse, and let the caller's fallback mark it. (Rule 18, in the label layer.)
    if not block or not block.get("functional") or not (block.get("basis_real_name")
                                                        or block.get("basis")):
        raise KeyError(
            "no usable level block for %r in qc_levels.json -- refusing to render a label "
            "with placeholders in it" % (level_key,))
    return "%s/%s/%s" % (block["functional"],
                         block.get("basis_real_name") or block.get("basis"),
                         _solvent_label(g.get("solvent_policy")))


def level_key_from_g_label(g_label, cfg=None):
    """`"G-1"/"G-2"` (case/hyphen-insensitive, as written into every row's own `level_label`
    field by `qc_adapter.sh` from config, never hardcoded) -> `"1"|"2"`, the payload's internal
    level slot. `None` if it cannot be resolved (missing config block or unrecognised label).

    🔴 [critic12, 2026-08-21] THE ONE PLACE to join a row against a level, going forward.
    `level_label` is STABLE across a label-string fix (it is a config `label` field, not the
    human-facing `functional/basis/solvent` string this module derives) -- a round-1 P5 row
    written before critic10's stale-string fix still carries the RIGHT `level_label`, because
    that field was never the thing that drifted. Comparing round-1 data against TODAY's
    `LEVEL_PRIMARY`/`LEVEL_CHEAP` strings (both derived from CURRENT config) silently fails on
    every legacy row whose `level` field is the pre-fix stale string -- same shape as
    `cli.py::qc_level_slot`, which does this exact G-N -> slot lookup for `--level` CLI input;
    duplicated here (not imported) because `cli.py` imports `collect.py`, which is this
    function's caller -- an import the other way would be circular.
    """
    from .. import config as _config
    cfg = cfg if cfg is not None else _config.load("qc_levels.json", {})
    want = str(g_label or "").strip().lower().replace("-", "")
    if not want:
        return None
    g = cfg.get("gaussian16") or {}
    for slot in ("1", "2"):
        label = (g.get("level%s" % slot) or {}).get("label", "")
        if label.lower().replace("-", "") == want:
            return slot
    return None


def _safe_label(level_key, fallback):
    try:
        return level_label(level_key)
    except Exception:                                    # config unreadable at import time
        return fallback


#: 🔒 Derived at import from config. The fallbacks are marked so that a label which somehow
#: reached a reply without config can never be mistaken for a description of what ran.
LEVEL_PRIMARY = _safe_label("level2", "level2/[LABEL-UNRESOLVED]")
LEVEL_CHEAP = _safe_label("level1", "level1/[LABEL-UNRESOLVED]")


def _median(xs):
    xs = sorted(xs)
    if not xs:
        return None
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


def _route_fields(r):
    """Two fields, never one: the route text AND whether it is complete.

    Accepts both the current shape (`route_echoed` + `route_echoed_is_complete`,
    written by `g16.summarize`) and the LEGACY shape (a bare `route` string from
    an RT-1-era report, which is the shape that carried the 70-column defect).
    """
    if "route_echoed" in (r or {}):
        return {"route_echoed": r.get("route_echoed"),
                "route_echoed_is_complete": r.get("route_echoed_is_complete"),
                "route_echo_completeness_evidence": (
                    (r.get("route_echo") or {}).get(
                        "route_echo_completeness_evidence"))}
    rec = g16.route_record_from_stored_string(
        r.get("route"), source="legacy `route` field in a returned report")
    return {"route_echoed": rec["route_echoed"],
            "route_echoed_is_complete": rec["route_echoed_is_complete"],
            "route_echo_completeness_evidence":
                rec["route_echo_completeness_evidence"]}


def normalize_rows(raw_rows):
    """payload가 쓴 종별 결과 → 정규화된 행. **버리지 않는다.**

    실패(미수렴/크래시)한 종도 `converged: false` 로 남긴다 — 실패율 자체가 정보다.

    🔴 [critic10] `converged` 는 **opt 단계만** 말한다. `normal_termination` 이 문자열 존재
    검사라 opt 가 끝나는 순간 True 가 되고, 그래서 **freq 가 크래시한 종에서도 True** 였다
    (실측: Optimization completed x1, Normal termination x1, `Frequencies --` x0,
    같은 로그에 EpsInf=0.0000 과 L1110 스택트레이스). 이름은 유지한다 — 과거 회신과의 비교가
    깨지지 않게. 진실은 `stages_completed.missing` 이 말한다.
    ⚠ 결과적으로 아래 비용 통계의 `converged` 필터는 **freq 가 죽은 종도 포함**한다. 그 종의
    core-h 는 부분값이다. 필터를 바꾸는 것은 "이 비용 통계가 무엇의 비용인가"를 바꾸는
    일이라 여기서 조용히 하지 않는다 — 드러내고 판단을 받는다.
    """
    out = []
    for r in raw_rows or []:
        row = {
            "id": r.get("id"),
            "level": r.get("level"),
            "n_atoms": r.get("n_atoms"),
            "charge": r.get("charge"),
            "multiplicity": r.get("multiplicity"),
            "open_shell": bool(r.get("multiplicity", 1) and r["multiplicity"] > 1),
            "core_hours": r.get("core_hours"),
            "wall_h": r.get("wall_h"),
            "scf_cycles_max": r.get("scf_cycles_max"),
            "scf_cycles_total": r.get("scf_cycles_total"),
            "opt_cycles": r.get("opt_cycles"),
            # 🔴 [critic10] OPT-ONLY. `normal_termination` fires once the opt half finishes,
            #    so this is true on species whose freq stage crashed. Kept under its own name
            #    so historical comparisons stay valid; `stages_completed` carries the truth.
            "converged": bool(r.get("converged")),
            "stages_completed": r.get("stages_completed"),
            "rc": r.get("rc"),
            "note": r.get("note"),
            # 🔴 [critic3 치명적-1] 아래 7개가 **여기서 통째로 사라지고 있었다.**
            #    payload 는 전부 기록하는데(`P5.sh:106-123`) 이 정규화기가 복사하지 않아
            #    최종 회신 JSON 에서 소실됐다 — "측정해 놓고 안 쓰는 값" **여섯 번째**다
            #    (B-3 / 400자 컷 / emit 분기 / host / queue wall / **이번**).
            #
            #    🔴 특히 `seed` 가 없으면 **dual-seed 종이 무의미해진다**: 그 종들은
            #    core-h 를 **2배** 써서 같은 계를 두 시드로 돌린 것이고, 목적은
            #    σ_protocol(프로토콜 재현성) 비교다. seed 가 없으면 **어느 행이 0 이고
            #    어느 행이 1 인지 회신만으로 알 수 없어 그 비교 자체가 불가능하다.**
            #    ⟹ 2배 비용을 쓰고 목적을 잃는다.
            #    🔴 `failure_reason` 유실도 별개로 심각하다 — 미수렴 **원인**이 최종
            #    리포트에서 사라지면 다음 왕복에 같은 질문을 다시 해야 한다.
            "seed": r.get("seed"),
            "seed_provenance": r.get("seed_provenance"),
            "failure_reason": r.get("failure_reason"),
            "g16_cpu_seconds": r.get("g16_cpu_seconds"),
            "qc_code": r.get("qc_code"),
            # 🔴 B-1: the bare `route` field is GONE. RT-1 stored three routes cut
            #    at column 70 under that name, and absence was read off them.
            #    A route now always travels with its completeness. A LEGACY row
            #    (`route`, from a returned RT-1-era report) is classified by
            #    `route_record_from_stored_string`, which can REFUTE completeness
            #    but never establish it.
            **_route_fields(r),
            "level_label": r.get("level_label"),
        }
        out.append(row)
    return out


def diagnostics(rows):
    """참고용 요약. 🔴 원자료를 대체하지 않는다.

    - 크기 구간별 중앙값 (평균이 아니라 중앙값 — 실패 종의 0/과대값에 덜 흔들린다)
    - 개각 vs 닫힌껍질 비
    - log-log 기울기 (core-h ~ N^p 의 p). 점이 3개 미만이면 계산하지 않는다.
    """
    ok = [r for r in rows if r["converged"] and (r["core_hours"] or 0) > 0
          and (r["n_atoms"] or 0) > 0]
    by_level = {}
    for r in ok:
        by_level.setdefault(r["level"], []).append(r)

    out = {"_caveat": "참고용 요약이다. 곡선 적합은 원자료(species_rows)로 하라.",
           "by_level": {}}
    for level, rs in sorted(by_level.items()):
        buckets = {}
        for r in rs:
            n = r["n_atoms"]
            b = "<=5" if n <= 5 else ("6-10" if n <= 10 else
                                      ("11-15" if n <= 15 else
                                       ("16-20" if n <= 20 else ">20")))
            buckets.setdefault(b, []).append(r["core_hours"])
        openish = [r["core_hours"] for r in rs if r["open_shell"]]
        closed = [r["core_hours"] for r in rs if not r["open_shell"]]
        slope = None
        if len(rs) >= 3:
            xs = [math.log(r["n_atoms"]) for r in rs]
            ys = [math.log(r["core_hours"]) for r in rs]
            mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
            sxx = sum((x - mx) ** 2 for x in xs)
            if sxx > 0:
                slope = round(sum((xs[i] - mx) * (ys[i] - my)
                                  for i in range(len(xs))) / sxx, 3)
        out["by_level"][level] = {
            "n_converged": len(rs),
            "median_core_hours": round(_median([r["core_hours"] for r in rs]), 4),
            "median_by_size_bucket": dict(
                (k, round(_median(v), 4)) for k, v in sorted(buckets.items())),
            "median_open_shell": round(_median(openish), 4) if openish else None,
            "median_closed_shell": round(_median(closed), 4) if closed else None,
            "open_shell_cost_ratio": (round(_median(openish) / _median(closed), 3)
                                      if openish and closed and _median(closed) else None),
            "loglog_slope_core_h_vs_n_atoms": slope,
        }
    return out


def level_cost_ratio(rows):
    """같은 종을 두 레벨로 돌린 경우의 단가비 (소분자에서의 비율).

    P1b는 40~80원자 TS에서 쟀다. **소분자에서 다를 수 있어** 따로 잰다.
    """
    by_id = {}
    for r in rows:
        if r["converged"] and (r["core_hours"] or 0) > 0:
            by_id.setdefault(r["id"], {})[r["level"]] = r["core_hours"]
    ratios = {}
    for sid, per_level in sorted(by_id.items()):
        if LEVEL_PRIMARY in per_level and LEVEL_CHEAP in per_level:
            ratios[sid] = round(per_level[LEVEL_PRIMARY] / per_level[LEVEL_CHEAP], 3)
    med = _median(list(ratios.values())) if ratios else None
    return {"per_species": ratios,
            "median_ratio": round(med, 3) if med is not None else None,
            "levels": {"numerator": LEVEL_PRIMARY, "denominator": LEVEL_CHEAP},
            "note": "P1b(큰 계)의 비율과 다르면 pool thermo 견적에 P1b 값을 쓰면 안 된다."}


def _completed_freq(row):
    """Did this species' FREQUENCY stage actually run? Read from output evidence
    (`stages_completed`), never from `converged` -- which is opt-only (critic10)."""
    st = row.get("stages_completed") or {}
    completed = st.get("completed")
    if completed is None:
        return None                      # 🔴 unknown, NOT False: an unmeasured stage record
    return "freq" in completed           #    is not evidence that freq did not run


def unit_costs(rows, basis_level=None):
    """🔴 [§39.78] TWO NAMED QUANTITIES, and the missing one is allowed to be missing.

    `u_cheap`  the COMPLETE opt+freq cost. This is what B1's sizing rule consumes:
               `N1 = min(600, remaining / (u_measured * r_composite))` asks how many species
               we can AFFORD, and affording a species means obtaining its THERMOCHEMISTRY --
               a free energy needs zero-point and thermal corrections, which come ONLY from
               the frequency stage.
               🔴 AN OPT-ONLY COST IS NOT A CHEAPER ESTIMATE OF IT. It is a different
               quantity, and publishing it under this name is `AGREEMENT IS NOT IDENTITY`
               (§39.76) -- a number under a name that means something else.
    `u_opt`    the optimisation-only cost, under its OWN name. Real and useful; never u_cheap.
               🟢 It is also the name proposer7's cation/open-shell factors (x2.8, x2.3, x15.2,
               §39.74) were missing -- they are opt-only magnitudes and had nothing correct to
               be quoted under.

    🔒 WHY `u_cheap: null` IS THE RIGHT ANSWER THIS ROUND rather than keeping the opt-only
    number under its name: every P5 frequency stage died on the EpsInf sentinel (§39.73), so
    u_cheap's denominator is EMPTY. An unlabelled absence reads as "P5 lost its cost data";
    `u_cheap: null` WITH ITS REASON, printed beside a populated `u_opt`, cannot be misread.
    Name both quantities and let the missing one be missing, loudly.
    """
    basis = basis_level or LEVEL_CHEAP
    at_level = [r for r in rows if r["level"] == basis and (r["core_hours"] or 0) > 0]
    complete = [r for r in at_level if _completed_freq(r) is True]
    opt_only = [r for r in at_level if r.get("converged")]
    unknown = [r for r in at_level if _completed_freq(r) is None]

    out = {
        "basis_level": basis,
        "u_cheap_core_hours": (_median([r["core_hours"] for r in complete])
                               if complete else None),
        "u_cheap_definition": "complete opt+freq cost per species (what B1 sizing consumes)",
        "u_cheap_n": len(complete),
        "u_opt_core_hours": (_median([r["core_hours"] for r in opt_only])
                             if opt_only else None),
        "u_opt_definition": "optimisation-only cost per species -- NOT u_cheap",
        "u_opt_n": len(opt_only),
        "n_stage_record_missing": len(unknown),
    }
    if not complete:
        out["u_cheap_reason"] = (
            "no species completed its frequency stage, so this quantity has an EMPTY "
            "denominator. It is absent, not lost -- `u_opt` beside it is populated and is a "
            "different quantity. (This round: every freq stage aborted on the EpsInf=0.0000 "
            "sentinel, §39.73.)")
    if unknown:
        out["_unknown_note"] = (
            "%d row(s) carry no `stages_completed` record, so whether freq ran is UNKNOWN "
            "rather than false -- they are counted in neither numerator." % len(unknown))
    # 🔴 [§39.78 condition] An assembled u_cheap -- optimisation measured in one round, its
    #    frequency measured in a later one on the stored geometry -- is LEGITIMATE (same
    #    geometry, same level, which `stages_completed` records) but is NOT an end-to-end
    #    measurement, and it must say so. The two halves may have run under different caps,
    #    giving a total NO SINGLE CONFIGURATION WOULD REPRODUCE. If it ever disagrees with an
    #    end-to-end number, this provenance is the only thing that lets anyone find out why.
    out["assembled"] = False
    out["_assembly_note"] = (
        "🔴 If u_cheap is ever formed by adding a frequency measured in a LATER round to an "
        "optimisation measured earlier, set `assembled: true` and carry BOTH halves' round id "
        "and cap record (§39.61(c)). An assembled total is not a single-run measurement.")
    return out


def verdict(rows, basis_level=LEVEL_CHEAP):
    """engineer §R13.2 3분기. **어느 레벨 기준인지 항상 라벨을 단다.**"""
    ok = [r for r in rows if r["level"] == basis_level and r["converged"]
          and (r["core_hours"] or 0) > 0]
    if not ok:
        return {"verdict": "not_measured", "threshold_basis": basis_level,
                "representative_core_hours": None,
                "reason": "기준 레벨(%s)에서 수렴한 종이 없다" % basis_level}
    rep = _median([r["core_hours"] for r in ok])
    if rep <= VERDICT_KEEP_MAX:
        v, note = "keep_pool", "pool 그대로 (<= %g core-h/종)" % VERDICT_KEEP_MAX
    elif rep <= VERDICT_SHRINK_MAX:
        v, note = "shrink_pool", ("pool 축소 필요 (%g~%g core-h/종)"
                                  % (VERDICT_KEEP_MAX, VERDICT_SHRINK_MAX))
    else:
        v, note = "restore_tiering", ("계층화 부활 (> %g core-h/종). ADR-028 재개봉"
                                      % VERDICT_SHRINK_MAX)
    return {
        "verdict": v,
        "threshold_basis": basis_level,
        "representative_core_hours": round(rep, 3),
        # 🔴 [critic10 / §39.78] `converged` is OPT-ONLY. This statistic therefore describes
        #    the optimisation cost, and it says so rather than implying opt+freq. The two
        #    named quantities live in `unit_costs()`; this label exists so the verdict's own
        #    basis cannot be misread as the complete cost B1 sizing consumes.
        "representative_statistic": ("median over species whose OPTIMISATION converged at the "
                                     "basis level -- opt-only, NOT the complete opt+freq cost "
                                     "(see unit_costs(): u_cheap vs u_opt)"),
        "thresholds": {"keep_max": VERDICT_KEEP_MAX, "shrink_max": VERDICT_SHRINK_MAX},
        "note": note,
        "caveat": "🔴 임계는 값싼 레벨 60 core-h 가정에서 나왔다. 고수준 값에 그대로 "
                  "적용하지 마라 — 임계 재산정은 lead/engineer가 한다.",
    }


def evaluate_p5(raw_rows, core_hours=None, wall_h=None, n_requested=None):
    rows = normalize_rows(raw_rows)
    # 🔴 [§39.78] Both named unit costs travel in the reply. `u_cheap` may be null; that is a
    #    labelled absence beside a populated `u_opt`, not missing data.
    n_ok = sum(1 for r in rows if r["converged"])
    reasons = []
    if not rows:
        reasons.append("결과 행이 없다(계산이 하나도 안 돌았다)")
    if n_requested and n_ok < max(3, int(0.5 * n_requested)):
        reasons.append("수렴 종 %d/%d — 절반 미만이라 곡선을 그릴 수 없다"
                       % (n_ok, n_requested))
    passed = bool(rows) and not reasons
    unit = unit_costs(rows)
    return {
        "unit_costs": unit,
        "id": "P5",
        "status": "pass" if passed else ("fail" if rows else "skipped"),
        "core_hours_total": core_hours,
        "wall_h": wall_h,
        "criteria": {
            "species_requested": n_requested,
            "species_converged": n_ok,
            "species_failed": len(rows) - n_ok,
        },
        # 🔴 정본. 받는 쪽이 이걸로 곡선을 적합한다.
        "species_rows": rows,
        "diagnostics": diagnostics(rows),
        "level_cost_ratio_small_molecules": level_cost_ratio(rows),
        "budget_verdict": verdict(rows),
        "fail_reasons": reasons,
    }



#: 🔴 [§39.98/§39.100, proposer8 2026-08-21] P5 rows whose CONVERGED GEOMETRY is symmetry-trapped
#: (no nosymm, no C-9 kick in that round's deck): Li-O=C 180.00 deg, heavy atoms coplanar to
#: 0.0000 A, 0.086-0.82 eV above the C1 seed of the same species. Their COST rows stand; their
#: structures must never be used as a chemical starting point by anything downstream (freq-only
#: recovery may still read them for the n_imag audit -- that is what convicts them).
GEOMETRY_REFUSED_TAGS = (
    "ec_radical_anion_s0_L2",   # 0.82 eV above its own C1 seed
    "li_ec_cation_s0_L2",       # Li-O=C 180.00 deg, planarity 0.0000 A
    "li_ec_radical_s0_L2",      # Li-O=C 180.00 deg, planarity 0.0000 A
    # li_ec2_cation_s0_L2 is convicted too but NEVER CONVERGED -> it is in the skipped set
    # (config/p5_freq_recovery.json _skipped_rows), not here: there is no geometry to refuse.
)


def geometry_refused(tag):
    """True when a stored P5 geometry may not seed any chemistry (see GEOMETRY_REFUSED_TAGS)."""
    return tag in GEOMETRY_REFUSED_TAGS
