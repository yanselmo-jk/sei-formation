"""P1 판정 — EC+Li+ 환원 라디칼 ring-opening TS 1건 완주.

§R2-6 자동 판정 기준 (스크립트 내부. 사용자는 판단하지 않는다):
  * 허수진동 **정확히 1개**, 그 값이 -2000 ~ -100 cm^-1
  * IRC가 **서로 다른 두 극소**를 연결
  * wall < 24 h
회신: 하위 단계별 core-h 분해(crest/ts_guess/ts_opt/irc/freq), 총 core-h, 수렴 step 수.

주의: 진동수 부호 관례 — 허수진동수를 음수로 인쇄하는 코드(ORCA, Q-Chem)와
'i' 접미로 인쇄하는 코드가 있다. 두 경우를 모두 음수로 정규화한다.
"""

import re

from .. import guards
from . import endpoints, g16
from .endpoints import classify_endpoints
from .xyzgraph import (bond_list, connected_components, formula, read_xyz_frames,
                       structures_distinct)  # noqa: F401  (structures_distinct는 하위호환)

# --- M2: 허수진동수 크기 창 (cm^-1) ---------------------------------------
#
# 🔴 ADR-032(composite 채택)로 **판정에 쓰이는 Hessian 의 기저가 바뀌었다**:
#    전량 고수준(def2-TZVPPD) → 값싼 레벨(def2-SVPD). proposer 명시:
#      "존재·개수는 기저에 둔감하나 **크기(cm⁻¹)는 민감하다** ⟹ M2 임계를 값싼 기저
#       기준으로 재보정해야 한다."
#
# ⟹ **명시적 결정 (coder, 재보정 불요 판단)**
#    창 폭이 1,900 cm⁻¹ 로 매우 넓고, 기저 변경에 따른 허수진동수 크기 변동은
#    통상 **수십 cm⁻¹** 규모다. 즉 SVPD Hessian 이 TZVPPD 대비 이 창의 **경계를
#    넘길 만큼** 달라질 여지가 작다. 그래서 숫자를 바꾸지 않는다.
#
# 🔴 그러나 이 판단에는 우리가 확인하지 못한 전제가 하나 있다: "수십 cm⁻¹" 은
#    문헌 통념이고 **우리 계에서 실측한 값이 아니다.** 판정 결과에 어느 기저의
#    Hessian 이었는지를 **항상 함께 싣는다**(IMAG_WINDOW_PROVENANCE). 그래야
#    나중에 재해석이 가능하다. 지금은 창만 있고 출처가 없는 상태였다.
#
# ⚠ 과학적 재보정이 필요하다는 판단이 서면 **proposer 가 정한다.** 임의로 숫자를
#    바꾸지 않는다. 여기를 고칠 때는 아래 provenance 도 같이 고쳐야 한다.
IMAG_WINDOW_CM1 = (-2000.0, -100.0)

IMAG_WINDOW_PROVENANCE = {
    "window_cm1": [-2000.0, -100.0],
    "recalibrated_for_cheap_basis": False,
    "decision": ("재보정 불요로 판단. 창 폭 1,900 cm⁻¹ 는 기저 변경에 따른 허수진동수 "
                 "크기 변동(통상 수십 cm⁻¹)을 충분히 덮는다."),
    "decision_by": "coder",
    "unverified_premise": ("'수십 cm⁻¹' 는 문헌 통념이며 우리 계에서 실측하지 않았다. "
                           "P1b 가 같은 계를 두 기저로 돌리므로, 그 결과로 이 전제를 "
                           "사후 검증할 수 있다."),
    "adr": "ADR-032 (composite 채택 → Hessian 이 값싼 기저에서 나온다)",
    "who_can_change": "🔴 과학적 재보정은 proposer 판정 사항이다. 임의 변경 금지.",
}
STAGES = ("crest", "ts_guess", "ts_opt", "irc", "freq")


def imag_window_provenance(hessian_level=None, hessian_basis=None):
    """판정 결과에 실을 창 + **그 판정이 어느 기저 Hessian 이었는가**.

    🔴 창만 있고 출처가 없으면 나중에 재해석이 불가능하다. 판정을 만드는 모든
    경로가 이걸 함께 실어야 한다.
    """
    out = dict(IMAG_WINDOW_PROVENANCE)
    out["hessian_level"] = hessian_level
    out["hessian_basis"] = hessian_basis
    if hessian_basis is None:
        out["warning"] = ("🔴 어느 기저의 Hessian 으로 판정했는지 확인하지 못했다 — "
                          "로그에서 route 를 못 읽었다. 판정을 그대로 신뢰하지 마라.")
    return out


def parse_orca_frequencies(text):
    """ORCA 'VIBRATIONAL FREQUENCIES' 블록 → cm^-1 리스트.

    [UNVERIFIED — ORCA 5/6 출력 형식 기준. 설치 버전에서 payload의 smoke 테스트가
     이 파서를 실제 출력으로 한 번 검증한 뒤에 본계산이 돈다.]
    형식 예: '   6:      -450.12 cm**-1  ***imaginary mode***'
    """
    if not text:
        return []
    freqs = []
    in_block = False
    for line in text.splitlines():
        if "VIBRATIONAL FREQUENCIES" in line:
            in_block = True
            freqs = []
            continue
        if in_block:
            if "NORMAL MODES" in line or "IR SPECTRUM" in line:
                in_block = False
                continue
            m = re.match(r"\s*(\d+):\s+(-?\d+\.?\d*)\s*cm\*\*-1", line)
            if m:
                freqs.append(float(m.group(2)))
    return freqs


def parse_generic_frequencies(text):
    """코드 비의존 fallback: 'i' 접미(예: 450.1i) 또는 'Frequency:' 줄."""
    if not text:
        return []
    freqs = []
    for m in re.finditer(r"(-?\d+\.\d+)\s*i\b", text):
        freqs.append(-abs(float(m.group(1))))
    for line in text.splitlines():
        if line.strip().lower().startswith("frequency:"):
            for tok in line.split()[1:]:
                try:
                    freqs.append(float(tok))
                except ValueError:
                    pass
    return freqs


def parse_frequencies(text):
    """진동수(cm^-1) 목록과 **어느 파서가 먹혔는지**.

    🔴 [B-3] 여기에 Gaussian 파서가 없어서, ORCA→G16 전환 후 P1 이 1,000 core-h 를
       태우고 진짜 TS 를 찾아도 회신이 무조건 `fail`(no_frequencies_parsed)이었다.
       IRC 경로는 G16 으로 옮겼는데 **freq 경로만 안 옮겼다** — 같은 전환의 두 경로
       중 하나만 갱신된 "부분 이식"이다.

    ⇒ 호출부(collect_p1)만 고치면 또 부분 이식이 된다. **파서 체인 자체**를 고쳐서
       누가 부르든 Gaussian 로그가 먹히게 한다.
    """
    f = parse_orca_frequencies(text)
    if f:
        return f, "orca"
    f = g16.parse_frequencies(text)
    if f:
        return f, "gaussian"
    f = parse_generic_frequencies(text)
    return f, ("generic" if f else "none")


def imaginary_modes(freqs, zero_tol_cm1=1.0):
    """허수(음수) 진동수만. |nu| < zero_tol 인 수치 잡음(병진/회전)은 제외."""
    return [f for f in freqs if f < -zero_tol_cm1]


def evaluate_freq(freqs, window=IMAG_WINDOW_CM1):
    imag = imaginary_modes(freqs)
    ok_count = (len(imag) == 1)
    in_window = bool(ok_count and window[0] <= imag[0] <= window[1])
    reasons = []
    if not freqs:
        reasons.append("no_frequencies_parsed")
    elif len(imag) == 0:
        reasons.append("no_imaginary_mode(=최소점이지 TS가 아니다)")
    elif len(imag) > 1:
        reasons.append("multiple_imaginary_modes(%d개)" % len(imag))
    elif not in_window:
        reasons.append("imag_freq_out_of_window(%.1f cm^-1, 허용 %g~%g)"
                       % (imag[0], window[0], window[1]))
    return {
        "imag_freq_count": len(imag),
        "imag_freq_cm": round(imag[0], 1) if imag else None,
        "all_imag_freq_cm": [round(x, 1) for x in imag],
        "n_frequencies": len(freqs),
        "passed": bool(ok_count and in_window),
        "reasons": reasons,
    }


def evaluate_irc(forward_xyz_text, reverse_xyz_text,
                 barrier_fwd_eV=None, barrier_rev_eV=None, cfg=None):
    """IRC 양 끝 구조가 서로 다른 극소인가 — **2층 그래프 R1~R3** (§12.3).

    입력은 각 방향 IRC 궤적의 xyz(다중 프레임). **마지막 프레임**을 끝점으로 본다.
    barrier_*_eV 는 R2b(배위 재배열)에서만 쓰이며, 모르면 판정을 `undetermined`
    로 남긴다 — **조용히 기각하지 않는다** (§12.5의 위음성 뒷문 차단).
    """
    ff = read_xyz_frames(forward_xyz_text or "")
    rr = read_xyz_frames(reverse_xyz_text or "")
    if not ff or not rr:
        return {"irc_endpoints_distinct": False, "passed": False,
                "verdict": "unparsable",
                "reasons": ["irc_trajectory_missing_or_unparsable"],
                "n_frames_forward": len(ff), "n_frames_reverse": len(rr)}
    a = ff[-1][1]
    b = rr[-1][1]
    if len(a) != len(b):
        return {"irc_endpoints_distinct": False, "passed": False,
                "verdict": "unparsable",
                "reasons": ["irc_endpoint_atom_count_mismatch"],
                "n_frames_forward": len(ff), "n_frames_reverse": len(rr)}

    ec = classify_endpoints(a, b, barrier_fwd_eV, barrier_rev_eV, cfg)

    reasons = []
    if ec["verdict"] == endpoints.SAME:
        reasons.append("irc_endpoints_identical(양쪽이 같은 극소로 굴러떨어졌다 "
                       "= TS가 그 반응의 TS가 아니거나 IRC가 너무 짧다). "
                       "규칙=%s" % ec["merge_rule_applied"])
    elif ec["verdict"] == endpoints.UNDETERMINED:
        reasons.append("irc_endpoint_undetermined(%s) — 배위 재배열의 상호전환 "
                       "barrier를 모른다. 병합도 분리도 하지 않았다. 사람 검토 필요."
                       % ec["merge_rule_applied"])
    if ec["threshold_sensitivity"].get("threshold_sensitive"):
        reasons.append("layer_I_threshold_sensitive(Li 접촉 임계 ±%.1f Å에서 판정이 "
                       "뒤집힌다 — 임계를 RDF로 실측해 확정할 것)"
                       % ec["threshold_sensitivity"]["delta_ang"])

    # 공유결합만 본 옛 규약의 결과도 남긴다(과거 회신과의 비교/재해석용).
    _distinct_c_only = ec["endpoint_distinct_C_only"]
    return {
        "irc_endpoints_distinct": bool(ec["distinct"]),
        "verdict": ec["verdict"],
        "passed": ec["verdict"] == endpoints.DISTINCT,
        "human_review_required": bool(ec["human_review_required"]),
        "reasons": reasons,
        "n_frames_forward": len(ff),
        "n_frames_reverse": len(rr),
        "endpoint_fragments_forward": sorted(
            formula(a, c) for c in connected_components(
                len(a), bond_list(a, include_ionic=True))),
        "endpoint_fragments_reverse": sorted(
            formula(b, c) for c in connected_components(
                len(b), bond_list(b, include_ionic=True))),
        "bond_changes": ec["layer_c_changes"],
        "graph_note": ec["interpretation"],
        "legacy_covalent_only_distinct": bool(_distinct_c_only),
        "endpoint_comparison": ec,
    }


def parse_convergence_steps(text):
    """수렴 step 수 (§R2-6 회신 항목). ORCA 최적화 사이클 카운트.
    [UNVERIFIED 형식] 'GEOMETRY OPTIMIZATION CYCLE   12'
    """
    if not text:
        return None
    n = None
    for m in re.finditer(r"GEOMETRY OPTIMIZATION CYCLE\s+(\d+)", text):
        n = int(m.group(1))
    return n


def _basis_from_route(text):
    """로그의 route 줄에서 기저를 읽는다. `gen` 이면 그 사실을 그대로 돌려준다."""
    if not text:
        return None
    m = re.search(r"^\s*#[pPnNtT]?\s+(\S+)", text, re.M)
    if not m or "/" not in m.group(1):
        return None
    return m.group(1).split("/", 1)[1]


def _c2_direction_detail(g16_summary, n_points):
    """One IRC direction's inputs to `guards.irc_verdict` (C-2).

    🔴 [ADR-092/C-2] `n_points` here must be the TRUE number of IRC steps the
    direction produced -- for a Gaussian log that is
    `len(g16.parse_geometries(raw_log_text))` (every orientation block), NOT
    the synthetic single-frame xyz `collect._g16_last_geometry_xyz` builds for
    the TOPOLOGY check (that helper intentionally keeps only the LAST frame,
    which is correct for comparing endpoints and would make `n_points` always
    1 -- silently unsatisfiable -- if reused here by accident.
    """
    g16_summary = g16_summary or {}
    return {
        "normal_termination": g16_summary.get("normal_termination"),
        "n_points": n_points,
        "energy_hartree": (g16_summary.get("scf") or {}).get("final_energy_hartree"),
        # 🔴 [C-2.1/C-2.2] HOW the path ended. `summarize()` fills this only for a log that
        #    really is an IRC, so a non-Gaussian or missing log leaves it None and C-2
        #    reports that it could not measure the ending -- it does not assume a minimum.
        "completion": g16_summary.get("irc_completion"),
    }


def evaluate_p1(freq_text, irc_forward_xyz, irc_reverse_xyz, wall_h,
                breakdown_core_h, opt_out_text=None, wall_limit_h=24.0,
                hessian_level=None,
                irc_forward_g16=None, irc_reverse_g16=None,
                irc_forward_n_points=None, irc_reverse_n_points=None,
                irc_e_ts_hartree=None):
    """P1 종합 판정. 반환 dict가 그대로 회신 JSON의 pilots[] 항목이 된다.

    🔴 [ADR-090/ADR-092, C-2] `guards.irc_verdict` is now consulted directly --
    it was previously named only by a same-spelled dict KEY (`"irc_verdict"`)
    that ADR-092 found was mistaken for a call during the very sweep built to
    find exactly this class of defect. That key is renamed
    `irc_topology_verdict` below so the two can never be confused again; the
    real guard's output lives at `irc_c2_verdict`.

    `irc_forward_g16`/`irc_reverse_g16` are `criteria.g16.summarize()` records
    for the two RAW IRC logs (Gaussian only; `None` for a non-Gaussian run,
    which correctly leaves C-2 unable to certify anything -- Rule 18, unknown
    is not permission). `irc_forward_n_points`/`irc_reverse_n_points` default
    to the topology check's own frame counts (`evaluate_irc`'s
    `n_frames_forward`/`n_frames_reverse`) when not given explicitly, which is
    the correct fallback for a non-Gaussian trajectory xyz (already the FULL
    path) but must be overridden by the caller for Gaussian (see
    `_c2_direction_detail`'s docstring). `irc_e_ts_hartree` likewise falls
    back to the TS log's own SCF energy (parsed via `criteria.g16.summarize`)
    when not given explicitly.
    """
    freqs, freq_parser = parse_frequencies(freq_text)
    fr = evaluate_freq(freqs)
    ir = evaluate_irc(irc_forward_xyz, irc_reverse_xyz)
    wall_ok = (wall_h is not None and wall_h < wall_limit_h)

    fwd_n = (irc_forward_n_points if irc_forward_n_points is not None
             else ir.get("n_frames_forward"))
    rev_n = (irc_reverse_n_points if irc_reverse_n_points is not None
             else ir.get("n_frames_reverse"))
    if irc_e_ts_hartree is not None:
        e_ts_hartree = irc_e_ts_hartree
    else:
        ts_g16 = g16.summarize(freq_text) if freq_text else None
        e_ts_hartree = (ts_g16.get("scf") or {}).get("final_energy_hartree") if ts_g16 else None
    c2 = guards.irc_verdict(
        _c2_direction_detail(irc_forward_g16, fwd_n),
        _c2_direction_detail(irc_reverse_g16, rev_n),
        e_ts_hartree)
    c2_ok = bool(c2["may_render_chemical_verdict"])

    reasons = list(fr["reasons"]) + list(ir["reasons"])
    if not wall_ok:
        reasons.append("wall_time_exceeded(%s h >= %g h)" % (wall_h, wall_limit_h))
    if not c2_ok:
        reasons.extend("c2_irc_%s" % w for w in list(c2["forward_failures"])
                       + list(c2["reverse_failures"]))
    passed = fr["passed"] and ir["passed"] and wall_ok and c2_ok
    # 🔴 IRC 끝점이 '판정 불가'(R2b, barrier 미지, 또는 C-2 미충족)이면 **fail이 아니다.**
    #    fail로 적으면 §12.2의 위음성(진짜 TS 기각)이 회신 단계에서 되살아난다.
    #    다른 기준이 전부 통과했을 때만 undetermined로 남긴다.
    #    🔴 [C-2] `not c2_ok` 는 위상(topology) 판정이 무엇이든 -- "distinct"든 "same"이든 --
    #    독립적으로 undetermined 를 강제한다. "TS가 틀렸다"와 "IRC가 안 돌았다"가 같은
    #    출구 코드를 공유해서는 안 된다는 C-2 자체의 규정이 바로 이 지점이다 (ADR-092).
    undetermined = (not passed and fr["passed"] and wall_ok
                    and (ir.get("verdict") == "undetermined" or not c2_ok))
    status = "pass" if passed else ("undetermined" if undetermined else "fail")
    out = {
        "id": "P1",
        "status": status,
        "human_review_required": bool(ir.get("human_review_required")),
        "core_hours_total": round(sum(breakdown_core_h.values()), 3)
                            if breakdown_core_h else 0.0,
        "breakdown": breakdown_core_h or {},
        "wall_h": wall_h,
        # 🔴 창만 있고 출처가 없으면 나중에 재해석이 불가능하다 (ADR-032 로
        #    Hessian 이 값싼 기저에서 나오게 됐다).
        "imag_window": imag_window_provenance(
            hessian_level=hessian_level,
            hessian_basis=_basis_from_route(freq_text)),
        "criteria": {
            "imag_freq_count": fr["imag_freq_count"],
            "imag_freq_cm": fr["imag_freq_cm"],
            "irc_endpoints_distinct": ir["irc_endpoints_distinct"],
            # 🔴 ADR-092: renamed from `irc_verdict` -- that spelling is what a
            # grep-based reach sweep mistook for a CALL to `guards.irc_verdict`.
            "irc_topology_verdict": ir.get("verdict"),
            "irc_rule_applied": (ir.get("endpoint_comparison") or {}).get(
                "merge_rule_applied"),
            "wall_under_limit": wall_ok,
            # 🔴 C-2, actually consulted (ADR-090/ADR-092) -- the REAL guard output,
            # distinct in name from the topology verdict above on purpose.
            "irc_c2_verdict": c2,
            "irc_c2_may_render_chemical_verdict": c2_ok,
        },
        "detail": {"freq": fr, "irc": ir, "freq_parser": freq_parser,
                   "convergence_steps": parse_convergence_steps(opt_out_text)},
        "fail_reasons": reasons,
    }
    # 🔴 [ADR-090 item 7, ADR-091, C-10, MAJOR] `guards.cost_probe_violations` had ZERO
    # callers anywhere, and its own docstring names THIS FUNCTION's shape as the incident:
    # "RT-1's P1 rendered [a chemical pass/fail] and the round was spent." Measured, not
    # acted on: P1 is left AS a chemistry-verdict pilot (that redesign -- whether P1 should
    # stop reporting `status: pass/fail` at all -- is a scope decision for the lead, not an
    # implementation one; see the coder8 report that raised item 5's equivalent question).
    # This wiring is deliberately SCOPED to DIAGNOSIS ONLY: it does not remove, rename, or
    # gate anything `out` already carries -- it names the violation as data, which is the
    # part that had zero reach before this.
    out["c10_cost_probe_violations"] = guards.cost_probe_violations(out)
    if out["c10_cost_probe_violations"]:
        # 🔴 Deliberately NOT appended to `fail_reasons` -- that list explains why THIS run's
        # pass/fail/undetermined came out the way it did, and C-10 fires on every P1 result
        # regardless of outcome (P1 is, by design, a chemistry-verdict pilot). Mixing the two
        # would make a genuine `pass` carry a `fail_reasons` entry, which reads as gating
        # when nothing here gates.
        out["c10_note"] = (
            "🔴 c10_cost_probe_carries_a_chemical_verdict (§39.4(g) R-4, ADR-090/091): %s. "
            "NOT acted on here by design -- reported as data pending a scope ruling on "
            "whether P1 should stop reporting a chemical status at all."
            % "; ".join(out["c10_cost_probe_violations"]))
    return out
