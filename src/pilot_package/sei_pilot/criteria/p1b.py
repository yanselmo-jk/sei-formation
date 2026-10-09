"""P1b 판정 — 두 level of theory의 **단계별** 단가비 실측.

근거: 03_COMPUTE_PLAN.md §11.5.
  level 1 = wB97X-D / def2-TZVP
  level 2 = wB97X-V / def2-TZVPPD   (LIBE 호환 level. 02_METHOD_SPEC §1.4)
전체 워크플로를 두 번 돌리지 않는다. P1이 만든 **동일 기하** 위에서
SP / gradient / Hessian 각 1회 + opt 5 step만 양쪽으로 돌려 단계별 비율을 얻는다
(3,500 → 400 core-h).

🔴 이 비율이 실제로 중요한 곳은 S1이 아니라 **S2-A의 2,000 species thermo**다.
   ×3.5면 480 k(배정 내), ×5면 685 k로 S2 배정을 넘는다 (§11.5 추가소견).

판정(스크립트 내장):
  * 단계별 비율 보고
  * scf_converged 플래그
  * level 2의 SCF 반복수가 level 1의 **2배 초과**면 warning `diffuse_scf_pathology`
    (진짜 위험은 총 단가가 아니라 diffuse 함수의 SCF 수렴 병리다)
"""

import re

from .. import guards

SCF_PATHOLOGY_FACTOR = 2.0
STAGES = ("sp", "gradient", "hessian", "opt5")


def parse_orca_scf_cycles(text):
    """ORCA SCF 수렴 사이클 수 목록.
    [UNVERIFIED 형식] 'SCF CONVERGED AFTER  15 CYCLES'
    """
    if not text:
        return {"converged": None, "cycles": [], "max_cycles": None}
    cycles = [int(m.group(1)) for m in
              re.finditer(r"SCF CONVERGED AFTER\s+(\d+)\s+CYCLES", text)]
    not_conv = bool(re.search(r"SCF NOT CONVERGED|SCF.*failed to converge", text, re.I))
    return {"converged": (bool(cycles) and not not_conv),
            "cycles": cycles,
            "max_cycles": max(cycles) if cycles else None,
            "total_cycles": sum(cycles) if cycles else None}


def evaluate_p1b(level1, level2, level1_name="wB97X-D/def2-TZVP",
                 level2_name="wB97X-V/def2-TZVPPD"):
    """level1/level2: {stage: {"core_hours": x, "scf": {...}}}

    반환: 단계별 비율 + 경고. 단계 하나가 실패해도 나머지 비율은 보고한다.
    """
    ratios = {}
    warnings = []
    for stage in STAGES:
        a = (level1 or {}).get(stage) or {}
        b = (level2 or {}).get(stage) or {}
        ch_a = a.get("core_hours")
        ch_b = b.get("core_hours")
        if ch_a and ch_b and ch_a > 0:
            ratios[stage] = round(float(ch_b) / float(ch_a), 3)
        else:
            ratios[stage] = None
            if ch_a is None or ch_b is None:
                warnings.append("stage_missing:%s" % stage)

    scf1 = ((level1 or {}).get("sp") or {}).get("scf") or {}
    scf2 = ((level2 or {}).get("sp") or {}).get("scf") or {}
    c1 = scf1.get("max_cycles")
    c2 = scf2.get("max_cycles")
    pathology = bool(c1 and c2 and c2 > SCF_PATHOLOGY_FACTOR * c1)
    if pathology:
        warnings.append("diffuse_scf_pathology(level2 SCF %s cycles > %gx level1 %s)"
                        % (c2, SCF_PATHOLOGY_FACTOR, c1))
    if scf2.get("converged") is False:
        warnings.append("level2_scf_not_converged")
    if scf1.get("converged") is False:
        warnings.append("level1_scf_not_converged")

    known = [v for v in ratios.values() if v]
    overall = round(sum(known) / len(known), 3) if known else None
    # 판정: 비율을 하나라도 얻었으면 pass. 실패는 '비율을 못 얻은 것'이다.
    passed = bool(known) and scf1.get("converged") is not False
    return {
        "id": "P1b",
        "status": "pass" if passed else "fail",
        "levels": {"level1": level1_name, "level2": level2_name},
        "cost_ratio_by_stage": ratios,
        "cost_ratio_unweighted_mean": overall,
        "scf": {"level1": scf1, "level2": scf2},
        "criteria": {"scf_converged_level1": scf1.get("converged"),
                     "scf_converged_level2": scf2.get("converged"),
                     "diffuse_scf_pathology": pathology},
        "warnings": warnings,
        "interpretation_note":
            "이 비율은 S2-A thermo 예산에 직접 들어간다. "
            "engineer 판정선: <=3.5x 이면 S2 배정 내, 5x 이면 초과(§11.8).",
    }


# ---------------------------------------------------------------------------
# RT-1b — 레벨 단가비 5수 (engineer §R16.6). P1b 가 흡수했다.
#
# 🔴 이 블록이 존재하는 이유: `r`(레벨 단가 배수)이 총액을 **1.19 M ~ 9.49 M (8배)**
#    로 벌리는 단일 최대 미지수이고, 계획을 다듬어서는 좁혀지지 않는다.
#    특히 `r_composite` 하나가 ADR-032(composite 채택) 판정을 가른다.
#
# 🔴 여기서 **판정하지 않는다.** ADR-032 규칙(|ΔG| < 0.05 eV 채택 / 0.05~0.1 채택+σ_r
#    상향 / ≥ 0.1 불가)은 받는 쪽이 적용한다. 우리는 수와 그 출처만 만든다.
# ---------------------------------------------------------------------------

# ADR-032 사전 확약 규칙의 경계값 (eV). **적용은 우리가 하지 않는다** — 회신에
# 함께 실어 받는 쪽이 같은 규칙을 쓰게 하려는 것이다.
ADR032_DG_ACCEPT_EV = 0.05
ADR032_DG_ACCEPT_WITH_SIGMA_EV = 0.10


def _ratio(numer, denom):
    """비율. 분모가 없거나 0이면 **None** — 0 이나 1 로 얼버무리지 않는다."""
    if not denom or numer is None:
        return None
    return round(float(numer) / float(denom), 4)


def _guarded_ratio(label, parts, compute):
    """One ratio, gated on BOTH data-presence and convergence -- and the two
    reasons for a `None` are kept SEPARATE, never collapsed into one.

    🔴 [ADR-088/ADR-090, C-1] `cost_ratios()` used to decide "missing" purely
    from `core_hours is None` and never read `converged` at all -- so
    `r_composite = 1.0365` was published over `li_ec2_cation`'s 283 core-h
    NON-CONVERGENCE (ADR-065), because that step's core-h WAS present. The
    convergence check is `guards.unconverged_inputs` (C-1's single source),
    not a second hand-rolled rule.

    `parts` = {step_label: (core_hours_value_or_None, step_entry_dict)}.
    Returns `(value, provenance)`. `value` is `None` whenever EITHER a step's
    core-h is missing OR any present step did not converge -- never averaged,
    never guessed, never silently dropped.
    """
    missing = [label for label, (v, _e) in parts.items() if v is None]
    if missing:
        return None, {
            "ok": False,
            "reason": "missing_core_hours",
            "steps": missing,
            "note": ("%s: step(s) %s have no recorded core-h -- not yet run, or the "
                     "log was not found. This is a DATA-ABSENCE reason, distinct from "
                     "non-convergence below." % (label, ", ".join(missing))),
        }
    # 🔴 Route through guards.unconverged_inputs -- the single definition of
    # "converged" this project uses, not a second one hand-rolled here.
    steps_for_guard = dict((k, e) for k, (_v, e) in parts.items())
    bad = guards.unconverged_inputs(steps_for_guard)
    if bad:
        return None, {
            "ok": False,
            "reason": "non_convergent_input",
            "steps": bad,
            "note": ("%s: step(s) %s report core-h but did NOT converge "
                     "(converged != True). A ratio over a non-convergence is not a "
                     "measurement of anything -- ADR-065, where r_composite = 1.0365 "
                     "was published over a 283 core-h non-convergence. This is a "
                     "CONVERGENCE reason, distinct from missing data above."
                     % (label, ", ".join(bad))),
        }
    return compute(), {"ok": True, "reason": None, "steps": [],
                       "note": "%s: every input step present and converged." % label}


def cost_ratios(steps):
    """단계별 core-h 딕셔너리에서 5수를 만든다.

    `steps` = {태그: {"core_hours": float|None, "converged": bool, ...}}
    태그 규약은 payload/P1b.sh 가 만든다:
        <id>_A_cheap_optfreq / <id>_B_high_optfreq /
        <id>_C_high_sp_on_cheap / <id>_D_gen_sp / <id>_D_builtin_sp

    🔴 [C-1] every ratio below is gated on `converged`, not merely on
    `core_hours is not None` -- see `_guarded_ratio`.
    """
    ids = sorted(set(t.rsplit("_", 0)[0].split("_A_")[0]
                     for t in steps if "_A_cheap_optfreq" in t))
    out = []
    for sid in ids:
        def entry(suffix):
            return steps.get("%s_%s" % (sid, suffix)) or {}
        a_e, b_e, c_e = entry("A_cheap_optfreq"), entry("B_high_optfreq"), entry("C_high_sp_on_cheap")
        gen_e, builtin_e = entry("D_gen_sp"), entry("D_builtin_sp")
        a, b, c = a_e.get("core_hours"), b_e.get("core_hours"), c_e.get("core_hours")
        gen, builtin = gen_e.get("core_hours"), builtin_e.get("core_hours")

        r_high, r_high_prov = _guarded_ratio(
            "r_high", {"A": (a, a_e), "B": (b, b_e)}, lambda: _ratio(b, a))
        # composite = 값싼 opt+freq + 고수준 SP. 분모는 값싼 것 하나.
        r_composite, r_composite_prov = _guarded_ratio(
            "r_composite", {"A": (a, a_e), "C": (c, c_e)},
            lambda: _ratio((a + c), a))
        gen_penalty, gen_penalty_prov = _guarded_ratio(
            "gen_penalty", {"D_gen": (gen, gen_e), "D_builtin": (builtin, builtin_e)},
            lambda: _ratio(gen, builtin))

        row = {
            "id": sid,
            "u_cheap_core_h": a,
            "r_high": r_high,
            "r_high_provenance": r_high_prov,
            "r_composite": r_composite,
            "r_composite_provenance": r_composite_prov,
            "gen_penalty": gen_penalty,
            "gen_penalty_provenance": gen_penalty_prov,
            "_gen_penalty_meaning": ("같은 기저(def2-TZVPP)를 gen 경로 vs 내장 키워드로 "
                                     "넣었을 때의 배수. diffuse 비용은 여기 안 섞여 있다."),
            "missing": [k for k, v in (("A", a), ("B", b), ("C", c),
                                       ("D_gen", gen), ("D_builtin", builtin))
                        if v is None],
            # 🔴 [C-1] present-but-non-convergent steps, kept separate from `missing`.
            "non_converged": sorted(set(
                r_high_prov.get("steps", []) if r_high_prov.get("reason") == "non_convergent_input" else []
            ) | set(
                r_composite_prov.get("steps", []) if r_composite_prov.get("reason") == "non_convergent_input" else []
            ) | set(
                gen_penalty_prov.get("steps", []) if gen_penalty_prov.get("reason") == "non_convergent_input" else []
            )),
        }
        if row["missing"]:
            row["note"] = ("측정이 빠진 단계가 있어 일부 비율이 None 이다. "
                           "None 을 1.0 으로 대치하지 마라 — 그 순간 총액 추정이 "
                           "조용히 낙관 쪽으로 틀어진다.")
        if row["non_converged"]:
            row.setdefault("note", "")
            row["note"] = (row["note"] + " " if row["note"] else "") + (
                "🔴 단계 %s 는 core-h 는 있지만 수렴하지 않았다 -- 그 단계가 분모/분자인 "
                "비율은 None 이다 (ADR-065/C-1)." % ", ".join(row["non_converged"]))
        out.append(row)
    return out


def delta_g_composite_vs_full(rows):
    """ΔG(composite − 전량 고수준) 목록. 단위 **eV**.

    `rows` = [{"id":…, "g_composite_hartree":…, "g_full_high_hartree":…}]
    🔴 두 값 중 하나라도 없으면 그 종은 `None` 으로 남긴다. 채워 넣지 않는다.
    """
    from .. import units
    out = []
    for r in rows:
        gc, gf = r.get("g_composite_hartree"), r.get("g_full_high_hartree")
        d = (units.hartree_to_ev(gc - gf) if (gc is not None and gf is not None)
             else None)
        out.append({"id": r.get("id"),
                    "delta_g_ev": round(d, 6) if d is not None else None,
                    "abs_delta_g_ev": round(abs(d), 6) if d is not None else None,
                    "g_composite_hartree": gc, "g_full_high_hartree": gf})
    return out


def rt1b_summary(steps, dg_rows=None):
    """회신 JSON 에 실을 RT-1b 블록. **판정 결과는 넣지 않는다.**"""
    ratios = cost_ratios(steps)
    dg = delta_g_composite_vs_full(dg_rows or [])
    known = [r["abs_delta_g_ev"] for r in dg if r["abs_delta_g_ev"] is not None]
    return {
        "purpose": ("`r`(레벨 단가 배수)이 총액을 8배로 벌리는 단일 최대 미지수다. "
                    "계획으로는 좁혀지지 않고 이 측정만이 좁힌다(engineer §R16.6)."),
        "per_species": ratios,
        "delta_g_composite_vs_full": dg,
        "delta_g_spread_ev": (round(max(known) - min(known), 6)
                              if len(known) > 1 else None),
        "adr032_rule": {
            "accept_below_ev": ADR032_DG_ACCEPT_EV,
            "accept_with_raised_sigma_below_ev": ADR032_DG_ACCEPT_WITH_SIGMA_EV,
            "_who_applies": "🔴 받는 쪽이 적용한다. 우리는 판정하지 않는다.",
            "_n_species_measured": len(known),
        },
        "definitions": {
            "u_cheap_core_h": "G-3 (wB97XD/def2-SVPD/SMD) opt+freq 1건의 core-h",
            "r_high": "G-1 전량 고수준 opt+freq / u_cheap",
            "r_composite": "(G-3 opt+freq + G-1 SP on G-3 기하) / G-3 opt+freq",
            "gen_penalty": "gen 경로 SP / 내장 키워드 SP (같은 기저 def2-TZVPP)",
            "diffuse_penalty": "별도 항목 — G-1 SP / G-4gen SP (둘 다 gen)",
        },
    }
