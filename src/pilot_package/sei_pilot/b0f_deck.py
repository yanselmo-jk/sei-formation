"""B0-F(U56-2) deck builder — role→index mapping 을 **deck 옆에** emit 하는 유일한 곳.

🔴 WHY THIS MODULE EXISTS (§39.39(h), proposer7 / ADR-109 lead 검증):
   `roles.mapping_for` / `require_mapping` 은 library 수준으로 검증돼 있었지만
   (tests/test_b0_definitions.py:522-542) **호출자가 0곳**이었다 — deck 을 만들면서
   mapping 을 옆에 쓰는 코드가 없었다. Ω(mode-overlap)와 relaxed-scan 의 스캔 좌표가
   **둘 다** 이 하나의 미작성 builder 아래에 매달려 있었고, 그것이 U56-2 의 화학적
   read-out 전체의 단일 실패점이었다. 이 모듈이 그 builder 다.

계약 (b0_reactions.json `_break_form_convention`, §39.26(d)):
  * break/form 은 **화학적 role 로만** 온다. 원자 index 는 이 모듈이 geometry 에서
    perceive 한 결과이지, config/route/payload 어디에도 박히지 않는다.
  * mapping 이 resolve 되지 않으면(`require_mapping` raise) **deck 은 만들어지지
    않는다.** mapping 없는 deck 은 Ω 채점이 불가능하고, 조용히 넘어가면 "숫자는
    나오는데 무엇에 대한 projection 인지 모르는" P1 급 사고가 된다.
  * relaxed-scan 의 스캔 좌표 = 같은 mapping 의 break 결합. 좌표 지정
    (ModRedundant `B i j S N step`)은 여기서만 만들어진다.

단위: 길이 Å (xyzgraph 관례 상속). 원자 index 는 mapping JSON 안에서는 **0-based**
(roles.py 의 관례), G16 ModRedundant 섹션 줄에서는 **1-based** — 변환은 이 파일의
`_g16_index()` 한 곳에서만 한다.
"""

import json
import os
import time

from . import config, roles, units
from .criteria import xyzgraph

#: 🔴 §39.42(b)의 개정된 사전등록 (원래 §39.39(d) "8–15" 를 proposer7 자신이 개정):
#: **coarse 12 × 0.10 Å + 조건부 refine ≤ 8 × 0.02–0.025 Å.**
#: 이 밖의 값은 config 에 있어도 거부한다 — 사전등록을 코드가 강제하지 않으면
#: config 한 줄로 조용히 다른 실험이 된다.
COARSE_STEPS_REGISTERED = 12
COARSE_STEP_ANG_REGISTERED = 0.10
REFINE_STEPS_MAX = 8
REFINE_STEP_ANG_RANGE = (0.02, 0.025)

#: 🔴 §39.47(a) — **점수 상한은 scan 이 아니라 ENGINE 에 속한다. 캡은 하나가 아니라 둘이다.**
#: DFT scan 점 하나 = 4.5 / 14 / 34 core-h, GFN2 점 하나 = ~0.001–0.006 core-h — **세 자릿수 차이**다.
#: 20 은 한 엔진에서는 진짜 비용 통제이고 다른 엔진에서는 0.05 core-h 짜리를 두 배로 늘리는 것을
#: 금지하는 것이다. 🔒 "이유가 비용인 상수는 비용과 같은 층위에 살아야 하고, 여기서 비용은
#: 엔진의 속성이다."
#:   * `TOTAL_POINTS_MAX`     = 🔴 **DFT 전용, 단방향.** 변경 없음.
#:   * `SCAN_POINTS_GFN2_MAX` = GFN2, **모든 방향·양 차원 합산, 반응당.** 비용 통제가 아니다 —
#:     20 을 GFN2 에 적용하면 §39.43 의 104점 2-D grid 와 41점 refine, 즉 hysteresis 를 실제로
#:     찾아낸 그 계산 자체를 스펙이 소급 거부하게 된다.
#: G-SCAN-1(양방향 scan)이 DFT 예산을 건드리지 않는 이유: gate 의 목적은 **DFT 시도에 돈을 댈지**
#: 판정하는 것이고 TS guess 는 GFN2 에서 만들어지므로, 판정도 거기서 공짜로 끝난다. DFT fallback
#: scan 은 이 GFN2 판정을 **상속**받아 단방향으로만 돈다(§39.47(a)).
TOTAL_POINTS_MAX = 20
SCAN_POINTS_GFN2_MAX = 512

#: 양쪽 엔진 공통. 8점 미만 프로파일은 최댓값을 자기 끝점과 구분할 수 없다 ⟹ 판정 불가.
SCAN_STEPS_MIN = 8

#: 엔진 이름 → 점수 상한. 🔴 미등록 엔진은 추측하지 않고 거부한다.
ENGINE_POINT_CAP = {"dft": TOTAL_POINTS_MAX, "gfn2": SCAN_POINTS_GFN2_MAX}

#: 🔴 §39.50(a) — G-SCAN-2 **v3** 의 허용오차. 단위 eV.
#: 유래(공격 가능하도록 명시한다): 이 프로젝트의 **선언된 민감도는 0.1 eV = 298 K 에서 rate 약 50배**
#: (§39.32(h), §0-h). 0.05 eV 는 그 **절반**이라, 경로 차이가 결론을 움직이기 한참 전에 발동한다.
#: 튜닝된 값이 아니라 **유래가 있는 선언 상수**이고 ADR-018 의 원칙 그대로다 —
#: *"분해 가능한가"가 아니라 "결론이 그 오차를 견디는가"*.
#: 🔒 proposer7 은 문턱 없는 성질을 두 번 사려다 두 번 실패했다:
#:   v1 구조 동일성   → **틀린 양**을 쟀다(무른 좌표. n=1 에서 0.35 Å 떨어졌는데 에너지는 0.000 eV).
#:   v2 refine 분해능 → **탐지하려는 병리와 반상관.** hysteresis 경로는 refine 해도 수렴하지 않는다
#:                      (R-C 격자 5배 촘촘히 → 점프는 1.4배만 감소, §39.41(b)).
#: ⟹ 대리물 속에 숨은 상수보다 명시된 상수가 낫다. **이 값을 케이스에 맞춰 튜닝하지 마라** —
#:   그 순간 반박 가능성이 사라진다. 틀렸다면 여기 한 줄을 바꾸고 유래를 다시 써라.
GSCAN2_TOLERANCE_EV = 0.05


class DeckInputError(RuntimeError):
    """Deck 입력이 성립하지 않는다(반응 미정의, 원자 수 불일치, 스캔 파라미터 창 밖).
    `roles.MappingRequiredError` 와 구분되는 이유: 저쪽은 'mapping 이 resolve 되지
    않았다'(화학 인식 실패)이고, 이쪽은 '입력 자체가 그 반응이 아니다'(배관 실패)다."""


def load_reaction(reaction_id, cfg=None):
    cfg = cfg if cfg is not None else config.load("b0_reactions.json", {})
    for r in cfg.get("reactions") or []:
        if r.get("id") == reaction_id:
            return r
    raise DeckInputError(
        "unknown reaction id %r (defined: %s)"
        % (reaction_id, ", ".join(r.get("id", "?") for r in cfg.get("reactions") or [])))


def engine_point_cap(engine):
    """엔진 이름 → 점수 상한(§39.47(a)). 미등록 엔진은 추측하지 않고 거부한다."""
    try:
        return ENGINE_POINT_CAP[engine]
    except KeyError:
        raise DeckInputError(
            "unknown scan engine %r (known: %s). 🔴 The point cap is a property of the ENGINE "
            "(§39.47(a)) -- a DFT point costs 4.5-34 core-h and a GFN2 point ~0.001-0.006, so "
            "there is no engine-agnostic default that is not wrong by three orders of magnitude."
            % (engine, ", ".join(sorted(ENGINE_POINT_CAP))))


def check_scan_point_budget(engine, n_points, what="scan"):
    """§39.47(a) 의 엔진별 점수 예산. `n_points` 의 의미가 엔진마다 다르다는 것이 요점이다:

      dft   한 방향 한 scan 의 coarse + refine (fallback scan 은 단방향으로만 돈다)
      gfn2  **한 반응의 모든 방향·양 차원 합산** (G-SCAN-1 의 역방향 scan 이 여기 들어간다)

    초과하면 raise. 🔴 엔진을 안 넘기면 더 **엄격한** DFT 캡을 받게 되어 조용히 통과하는 일이
    없다(잊었을 때의 실패 방향이 안전한 쪽이다).
    """
    cap = engine_point_cap(engine)
    if not isinstance(n_points, int) or n_points < 0:
        raise DeckInputError("n_points = %r is not a point count" % (n_points,))
    if n_points > cap:
        raise DeckInputError(
            "%s needs %d points but the %s cap is %d (§39.47(a)). Do not raise the cap to fit "
            "the run; the cap encodes what a point costs on THIS engine."
            % (what, n_points, engine, cap))
    return n_points


def scan_params(cfg=None, engine="dft"):
    """config `u56_2.scan` → dict. §39.42(b)의 개정 사전등록을 강제한다:
    coarse == 12 × 0.10 Å (guess 전용), refine ≤ 8 × [0.02, 0.025] Å (조건부),
    step 은 양수(신장)만. 총점 상한은 §39.47(a) 에 따라 **엔진**이 정한다.

    `engine` 기본값이 `"dft"` 인 이유: 기존 호출자(U56.sh 의 G16 relaxed_scan)가 전부 DFT 이고,
    잊었을 때 받게 되는 캡이 더 **엄격한** 쪽이라 조용히 허용되는 경로가 없다.
    """
    cfg = cfg if cfg is not None else config.load("b0_reactions.json", {})
    scan = (cfg.get("u56_2") or {}).get("scan") or {}
    cn = scan.get("coarse_n_steps")
    cs = scan.get("coarse_step_ang")
    rn = scan.get("refine_n_steps")
    rs = scan.get("refine_step_ang")
    trig = scan.get("refine_trigger_delta_ev")
    if cn != COARSE_STEPS_REGISTERED or not isinstance(cs, (int, float)) \
            or abs(float(cs) - COARSE_STEP_ANG_REGISTERED) > 1e-9:
        raise DeckInputError(
            "u56_2.scan coarse pass = %r x %r, but the §39.42(b) registration is EXACTLY "
            "%d x %.2f Angstrom. Fix the config; do not loosen this in code."
            % (cn, cs, COARSE_STEPS_REGISTERED, COARSE_STEP_ANG_REGISTERED))
    if not isinstance(rn, int) or not (1 <= rn <= REFINE_STEPS_MAX):
        raise DeckInputError(
            "u56_2.scan.refine_n_steps = %r is outside 1..%d (§39.42(b): '<= 8 refine')."
            % (rn, REFINE_STEPS_MAX))
    if not isinstance(rs, (int, float)) or not (REFINE_STEP_ANG_RANGE[0] - 1e-9
                                                <= float(rs)
                                                <= REFINE_STEP_ANG_RANGE[1] + 1e-9):
        raise DeckInputError(
            "u56_2.scan.refine_step_ang = %r is outside the registered %s Angstrom."
            % (rs, list(REFINE_STEP_ANG_RANGE)))
    check_scan_point_budget(engine, int(cn) + int(rn),
                            what="one %s scan direction (coarse+refine)" % engine)
    if not isinstance(trig, (int, float)) or float(trig) <= 0:
        raise DeckInputError(
            "u56_2.scan.refine_trigger_delta_ev = %r must be a positive energy in eV."
            % (trig,))
    return {"coarse_n_steps": int(cn), "coarse_step_ang": float(cs),
            "refine_n_steps": int(rn), "refine_step_ang": float(rs),
            "refine_trigger_delta_ev": float(trig),
            "engine": engine, "point_cap": engine_point_cap(engine)}


def refine_decision(scan_result, trigger_delta_ev):
    """§39.42(b)의 **조건부** refine 발동 판정. 순수 함수, 데이터로 반환(판정 기록 포함).

    발동 조건 (둘 중 하나):
      (i)  최댓값과 그 인접점 사이 |ΔE| > trigger (eV) — 격자가 최댓값을 걸터앉았을 수 있다
      (ii) 최댓값이 스캔 범위의 끝 — 범위가 짧았다 (다른 결함, 같은 증상)
    """
    energies = [p.get("energy_hartree") for p in (scan_result or {}).get("points") or []]
    out = {"triggered": False, "reasons": [], "trigger_delta_ev": float(trigger_delta_ev),
           "max_point_index": (scan_result or {}).get("max_point_index")}
    idx = out["max_point_index"]
    if not idx:
        out["reasons"].append("no scan maximum exists -- nothing to refine")
        return out
    i = idx - 1
    if idx == 1 or idx == len(energies):
        out["triggered"] = True
        out["reasons"].append(
            "maximum sits at an END of the scanned range (point %d of %d) -- the range "
            "was too short (§39.42(b) trigger ii)" % (idx, len(energies)))
    for j in (i - 1, i + 1):
        if 0 <= j < len(energies) and energies[j] is not None \
                and energies[i] is not None:
            de = abs(units.hartree_to_ev(energies[i] - energies[j]))
            if de > float(trigger_delta_ev):
                out["triggered"] = True
                out["reasons"].append(
                    "|dE| between the maximum (point %d) and point %d = %.4f eV > %.2f "
                    "(§39.42(b) trigger i)" % (idx, j + 1, de, float(trigger_delta_ev)))
    return out


def _profile_energies_hartree(profile):
    return [p.get("energy_hartree") for p in (profile or {}).get("points") or []]


#: 🔴 §39.64 — WHICH FRAME EACH DIRECTION'S BARRIER IS MEASURED FROM. Both are measured from
#: the **REACTANT END**: the forward profile's FIRST frame, the reverse profile's LAST.
#: 🔒 This is the whole content of a defect that shipped and was caught by running the gate:
#: measuring each profile from *its own first frame* puts the reverse barrier on the PRODUCT,
#: so the difference between the two barriers becomes `path dependence ± ΔE_reaction` — it
#: measures thermodynamics, not hysteresis.
#: 🔴 AND THE ERROR IS NOT ONE-SIGNED, so "at least it was conservative" is not available:
#:     R-A  |Δ| 0.013 -> 0.291   a FALSE BLOCK at 6x the threshold, on a clean path
#:     R-C  |Δ| 0.535 -> 0.170   still fires, but on a THIRD of its margin -- and R-C is the
#:                               case the gate exists to catch
#: ⚠ §39.45(a)'s prose said the reverse max was taken "from its OWN endpoint", which is
#: ambiguous in exactly the way that matters; proposer7's script had always used the reactant
#: end. When a spec is written from a working script, THE SCRIPT IS THE AUTHORITY and the prose
#: must be checked against it — nothing catches that except implementing from the sentence.
BARRIER_REFERENCE_FRAME = {"forward": 0, "reverse": -1}


def scan_barrier_ev(profile, direction="forward"):
    """A profile's apparent barrier in eV, measured from the REACTANT END (§39.64).

    `direction` selects which frame that is: `forward` -> first frame, `reverse` -> last.
    None if any energy is missing — an unjudgeable profile is not a 0.0 eV barrier.
    """
    try:
        ref = BARRIER_REFERENCE_FRAME[direction]
    except KeyError:
        raise DeckInputError(
            "unknown scan direction %r -- the barrier's reference frame is a property of the "
            "direction and there is no safe default (§39.64)" % (direction,))
    es = _profile_energies_hartree(profile)
    if not es or any(e is None for e in es):
        return None
    return units.hartree_to_ev(max(es) - es[ref])


def gscan2_decision(forward, reverse, tolerance_ev=GSCAN2_TOLERANCE_EV):
    """🔴 **G-SCAN-2 v3 (§39.50(a)).** 불연속 gate 의 1차 판정. 순수 함수.

    두 조건이 **모두** 성립하지 않으면 FIRE:
      (i)  |E(역방향 끝점) − E(정방향 첫 프레임)| < tolerance
      (ii) |barrier_정방향 − barrier_역방향|      < tolerance

    FIRE ⟹ **그 guess 위에 `ts_opt+freq` 나 IRC 를 발주하지 않는다**(G-SCAN-4). 회피 비용
    ~660 core-h(11원자) / ~6,400(21원자).

    🔴 **판정 산술은 전부 한 Hamiltonian 안에서만 일어난다(§39.50(b)).** 두 프로파일의
    `hamiltonian` 이 다르거나 없으면 판정하지 않고 `DeckInputError` 로 거부한다 — 서로 다른
    에너지 모형의 Hartree 를 빼면 **숫자는 나오는데 물리적으로 무의미**하고, 모든 로그는
    성공이라고 찍는다(C-8.1 grid seam 과 같은 부류). 인증된 반응물은 정방향 scan 이 출발하는
    **구조**만 제공하고 **에너지는 절대 제공하지 않는다**.

    🔒 구조 동일성(RMSD, `d(Li–O_break)`)은 **판정에서 빠지고 covariate 로 강등**됐다 —
    v1 이 그것으로 n=1 을 오발동시켰다(0.35 Å 떨어졌는데 에너지는 0.000 eV, 무른 좌표).
    계속 emit 하되 이 함수는 그것을 읽지 않는다.
    """
    tol = float(tolerance_ev)
    ham_f = (forward or {}).get("hamiltonian")
    ham_r = (reverse or {}).get("hamiltonian")
    if not ham_f or not ham_r or ham_f != ham_r:
        raise DeckInputError(
            "G-SCAN-2 refuses to render a verdict across Hamiltonians: forward=%r reverse=%r "
            "(§39.50(b)). Subtracting energies from two energy models PRODUCES A NUMBER and it "
            "means nothing. The certified reactant contributes the STRUCTURE the forward scan "
            "starts from, never an energy." % (ham_f, ham_r))

    out = {"fired": False, "reasons": [], "hamiltonian": ham_f,
           "tolerance_ev": tol, "tolerance_source": "§39.50(a) GSCAN2_TOLERANCE_EV",
           "delta_endpoint_ev": None, "delta_barrier_ev": None,
           "barrier_forward_ev": scan_barrier_ev(forward, "forward"),
           "barrier_reverse_ev": scan_barrier_ev(reverse, "reverse"),
           # 🟢 §39.64's free consistency check, asserted rather than trusted: clause (i)
           # compares the reverse profile's LAST frame with the forward's FIRST, and the two
           # barriers are now referenced to those SAME two frames. An implementation whose
           # clauses reference different frames is defective by construction, and saying so
           # requires no chemistry at all.
           "reference_frames": {"forward": BARRIER_REFERENCE_FRAME["forward"],
                                "reverse": BARRIER_REFERENCE_FRAME["reverse"],
                                "_meaning": "both clauses reference the reactant end: "
                                            "forward[0] and reverse[-1]"}}

    ef = _profile_energies_hartree(forward)
    er = _profile_energies_hartree(reverse)
    for label, es in (("forward", ef), ("reverse", er)):
        if len(es) < SCAN_STEPS_MIN or any(e is None for e in es):
            out["fired"] = True
            out["reasons"].append(
                "%s profile is not judgeable: %d point(s), %d missing energies (need >= %d "
                "usable points -- a shorter profile cannot place a maximum away from its own "
                "endpoints). Withholding funding is the correct direction for a dead scan."
                % (label, len(es), sum(1 for e in es if e is None), SCAN_STEPS_MIN))
    if out["fired"]:
        return out

    out["delta_endpoint_ev"] = abs(units.hartree_to_ev(er[-1] - ef[0]))
    out["delta_barrier_ev"] = abs(out["barrier_forward_ev"] - out["barrier_reverse_ev"])
    if out["delta_endpoint_ev"] >= tol:
        out["fired"] = True
        out["reasons"].append(
            "(i) the reverse scan does not return to the forward scan's own first frame: "
            "|dE| = %.4f eV >= %.4f (§39.50(a)). The two directions do not describe one path."
            % (out["delta_endpoint_ev"], tol))
    if out["delta_barrier_ev"] >= tol:
        out["fired"] = True
        out["reasons"].append(
            "(ii) the two directions disagree on the barrier: |d(barrier)| = %.4f eV >= %.4f "
            "(§39.50(a)). A guess taken from a path-dependent profile starts at the wrong "
            "geometry." % (out["delta_barrier_ev"], tol))
    if not out["fired"]:
        out["reasons"].append(
            "both G-SCAN-2 conditions hold (%.4f eV and %.4f eV, tolerance %.4f) -- no path "
            "dependence detectable at the project's declared sensitivity."
            % (out["delta_endpoint_ev"], out["delta_barrier_ev"], tol))
    return out


def mechanism_pairs(atoms, mapping, mechanism_spec):
    """🔴 [§39.62] MECHANISM COORDINATES — coordinates the mechanism uses that are NOT bonds
    being broken or formed.

    Why they exist: the spectator test asks *"is the moving atom outside the declared
    coordinate set?"*, so it is only as correct as that set. §39.41(e) measured that R-C's ring
    opening is TWO-DIMENSIONAL — Li⁺ translocates onto the breaking oxygen (d(Li–O2) 2.65 →
    1.86 Å) as part of the mechanism. If R-C declares only the C–O bond, the spectator test
    BLOCKS R-C's genuine transition state, which is the expensive error (a lost reaction, not
    lost core-hours). 🔒 General form: **an atom is a spectator only relative to a declared
    coordinate set; if the mechanism uses it, it belongs in the set.** The same 2-D finding that
    forced the scan to add a coordinate forces the mapping to add one — one fact, two
    consequences.

    Encoding, and it is deliberately the smallest one that cannot go wrong: a mechanism entry is
    a role pair `["Li", "O_ether"]`, and the SECOND role is resolved by **reusing the index
    already selected in a break/form pair carrying that role** — never by perceiving it afresh.
    🔴 That is what makes `d(Li–O_break)` mean *the breaking oxygen* rather than *some ether
    oxygen*: R-C has four O_ether candidates across two EC ligands, and a fresh perception would
    pick one by index order with no guarantee it is the one that breaks.
    ⟹ if no break/form pair carries the second role, the deck is REFUSED: a mechanism coordinate
      that does not reference the reaction's own atoms is not a mechanism coordinate.
    ⚠ Unlike break/form these pairs need NOT be bonded at the reactant geometry — Li–O_break is
      2.65 Å apart there, which is the whole point. So they are resolved by role lookup, not by
      `resolve_bond`.
    """
    out = []
    for entry in (mechanism_spec or []):
        try:
            role_a, role_b = entry
        except (TypeError, ValueError):
            raise DeckInputError(
                "mechanism entry %r is not a [role_a, role_b] pair" % (entry,))
        role_a = roles.canonical_role(role_a)
        role_b = roles.canonical_role(role_b)
        anchor_index = None
        for kind in ("break", "form"):
            for m in (mapping.get(kind) or []):
                if m.get("selected") and role_b in [roles.canonical_role(r)
                                                    for r in (m.get("roles") or [])]:
                    pos = [roles.canonical_role(r) for r in m["roles"]].index(role_b)
                    anchor_index = m["selected"][pos]
                    break
            if anchor_index is not None:
                break
        if anchor_index is None:
            raise DeckInputError(
                "mechanism coordinate %s--%s cannot be anchored: no break/form pair carries the "
                "role %r, so %r would refer to some other atom of that role rather than to the "
                "reacting one. Declare it against a role the reaction actually names."
                % (role_a, role_b, role_b, role_b))
        candidates = (roles.perceive(atoms).get(role_a) or [])
        if not candidates:
            raise DeckInputError(
                "mechanism coordinate %s--%s: no atom has role %r in this geometry"
                % (role_a, role_b, role_a))
        out.append({
            "roles": [role_a, role_b],
            "selected": (candidates[0], anchor_index),
            "n_candidates": len(candidates),
            "ambiguous": len(candidates) > 1,
            "anchored_to": ("the atom already selected as %s in the break/form mapping"
                            % role_b),
            "warnings": (["🔴 mechanism_role_ambiguous: %d atoms carry role %s; the lowest "
                          "index was taken and the full list is %s"
                          % (len(candidates), role_a, candidates)]
                         if len(candidates) > 1 else []),
        })
    return out


def coordinate_atom_indices(mapping):
    """Every atom index named by the mapping's break / form / mechanism coordinates.
    This is the set the §39.62 spectator test measures a mode against."""
    idx = set()
    for kind in ("break", "form", "mechanism"):
        for m in (mapping or {}).get(kind) or []:
            for a in (m.get("selected") or []):
                idx.add(int(a))
    return sorted(idx)


def _g16_index(i):
    """mapping 의 0-based 원자 index → G16 입력의 1-based. 변환은 여기 한 곳뿐이다."""
    return int(i) + 1


def scan_section_lines(mapping, n_steps, step_ang):
    """resolve 된 mapping 의 break 결합들 → ModRedundant 섹션 줄.

    `require_mapping` 을 **여기서 다시** 부른다 — 호출자가 잊어도 미해결 mapping 이
    스캔 좌표가 되는 일은 없다(같은 진실을 두 곳에 두지 않기 위해 검사는 roles 의
    그 함수 하나다).
    """
    roles.require_mapping(mapping)
    lines = []
    for entry in mapping.get("break") or []:
        i, j = entry["selected"]
        lines.append("B %d %d S %d %.4f"
                     % (_g16_index(i), _g16_index(j), int(n_steps), float(step_ang)))
    if not lines:
        raise DeckInputError(
            "the mapping resolved but carries no break bond -- a relaxed scan without a "
            "scan coordinate is not a scan. Check the reaction's break list.")
    return lines


def build_deck_inputs(reaction_id, xyz_path, out_dir, with_scan_section=True, cfg=None):
    """반응 1건의 deck 입력을 만든다. **mapping 파일이 deck 옆에 먼저 놓인다.**

    산출물 (out_dir):
      u56_<id>_mapping.json        role→index mapping (Ω 는 이것에 대해 채점된다)
      u56_<id>_scan_section.txt    ModRedundant 섹션 (with_scan_section=True, 즉
                                   relaxed_scan method 일 때만; QST2 는 스캔 좌표가
                                   없지만 Ω 채점을 위해 mapping 은 똑같이 필요하다)
      u56_<id>_deck_inputs.json    이 호출의 요약(provenance 포함)

    raise:
      DeckInputError               반응 미정의 / 원자 수 불일치 / 스캔 파라미터 위반
      roles.MappingRequiredError   mapping 미해결 — **deck 생성 거부.** 이때 파일은
                                   아무것도 쓰지 않는다(부분 산출물이 '만들어진 deck'
                                   으로 오독되는 것을 막는다).
    """
    reaction = load_reaction(reaction_id, cfg=cfg)
    try:
        text = open(xyz_path, errors="replace").read()
        atoms = xyzgraph.read_xyz_frames(text)[0][1]
    except (OSError, ValueError, IndexError) as exc:
        raise DeckInputError("cannot read geometry %r: %s" % (xyz_path, exc))
    if reaction.get("n_atoms") and len(atoms) != int(reaction["n_atoms"]):
        raise DeckInputError(
            "geometry %r has %d atoms but reaction %s declares %d -- this is not that "
            "reaction's species; refusing to perceive roles on the wrong molecule."
            % (xyz_path, len(atoms), reaction_id, reaction["n_atoms"]))

    mapping = roles.mapping_for(atoms, reaction.get("break") or [],
                                reaction.get("form") or [])
    roles.require_mapping(mapping)   # raise ⟹ 아래의 어떤 파일도 쓰지 않는다
    # 🔴 [§39.62] mechanism coordinates. NOT scan coordinates and NOT bonds that break --
    #    they exist so the spectator test knows which atoms the MECHANISM uses. Leaving one
    #    out makes a genuine transition state look like a spectator mode (R-C, where Li+
    #    translocates onto the breaking oxygen). Anchored to the break/form selection, so
    #    "O_break" is the oxygen that actually breaks, not merely one of that role.
    mapping["mechanism"] = mechanism_pairs(atoms, mapping, reaction.get("mechanism") or [])

    # 🔴 [§39.42(a)] d(Li–O_break) covariate — 판정 없이 데이터로 emit (C-3).
    #    두 축퇴 basin 이 이 좌표에서 0.9 Å 다를 수 있고, O_break 는 반응이 실측으로
    #    사용하는 좌표다: endpoint degeneracy 가 barrier degeneracy 를 보장하지 않는다.
    d_li_o_break = None
    scan_start_d = None
    li_idx = (mapping.get("roles") or {}).get("Li") or []
    brk = mapping.get("break") or []
    if brk and brk[0].get("selected"):
        o_idx, c_idx = brk[0]["selected"]   # break 쌍 = (role_a=O_ether, role_b)
        if li_idx:
            d_li_o_break = round(
                xyzgraph.distance_ang(atoms[li_idx[0]], atoms[o_idx]), 4)
        # 🔴 [§39.42(b)] 스캔은 **인증된 끝단 자신의 d 에서 출발**한다(1.40 가정 금지) —
        #    ModRedundant S 스캔이 현재값에서 출발하므로 구조적으로 보장되지만, 그
        #    시작값 자체를 emit 해야 검산 가능하다("Emit the start").
        scan_start_d = round(xyzgraph.distance_ang(atoms[o_idx], atoms[c_idx]), 4)

    scan_lines = None
    params = None
    if with_scan_section:
        params = scan_params(cfg=cfg)
        scan_lines = scan_section_lines(mapping, params["coarse_n_steps"],
                                        params["coarse_step_ang"])

    tag = "u56_%s" % reaction_id
    mapping_path = os.path.join(out_dir, "%s_mapping.json" % tag)
    record = {
        "reaction_id": reaction_id,
        "reaction_name": reaction.get("name"),
        "source_xyz": os.path.abspath(xyz_path),
        "n_atoms": len(atoms),
        "break_roles": reaction.get("break"),
        "form_roles": reaction.get("form"),
        "mechanism_roles": reaction.get("mechanism"),
        # the set the §39.62 spectator test measures an imaginary mode against
        "coordinate_atom_indices": coordinate_atom_indices(mapping),
        "mapping": mapping,
        "_index_convention": ("mapping 은 0-based (roles.py 관례). G16 ModRedundant "
                              "줄만 1-based 로 변환된다 (b0f_deck._g16_index)."),
        "generated_at_epoch": int(time.time()),
    }
    os.makedirs(out_dir, exist_ok=True)
    with open(mapping_path, "w") as fh:
        json.dump(record, fh, ensure_ascii=False, indent=1)

    scan_path = None
    if scan_lines is not None:
        scan_path = os.path.join(out_dir, "%s_scan_section.txt" % tag)
        with open(scan_path, "w") as fh:
            fh.write("\n".join(scan_lines) + "\n")

    summary = {
        "reaction_id": reaction_id,
        "mapping_path": mapping_path,
        "scan_section_path": scan_path,
        "scan_section_lines": scan_lines,
        "scan_params": params,
        "scan_start_d_ang": scan_start_d,
        "d_li_o_break_ang": d_li_o_break,
        "_d_li_o_break_note": ("§39.42(a) covariate -- 데이터, 판정 없음 (C-3). 시작 "
                               "기하에서의 d(Li, break 결합의 O). 축퇴 basin 이 이 "
                               "좌표에서 다르면 GFN2 에서 양쪽 다 scan 하는 것이 규칙이다 "
                               "(DFT 로 임의 승격 금지)."),
        "mapping_ambiguous": any(e.get("ambiguous")
                                 for e in (mapping.get("break") or [])
                                 + (mapping.get("form") or [])),
        "mapping_warnings": mapping.get("warnings") or [],
    }
    with open(os.path.join(out_dir, "%s_deck_inputs.json" % tag), "w") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=1)
    return summary
