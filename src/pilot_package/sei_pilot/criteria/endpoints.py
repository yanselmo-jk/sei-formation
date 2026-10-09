"""IRC 끝점 동일성 판정 — 2층 그래프 + 속도론적 병합 (02_METHOD_SPEC §12.3).

🔴 왜 이 규칙인가 (proposer §12.1, 이 판단을 코드가 바꾸면 안 된다):
   ADR-003 축(b) 검증 성분 4종 중 최소 3종(LiF, Li₂CO₃, ROCO₂Li)이 **Li 배위로
   정의되는 종**이다. Li를 결합에서 빼면 `ROCO₂⁻ + Li⁺` 와 `ROCO₂Li` 의 그래프가
   같아져서 **이온쌍 형성 단계가 통째로 기각된다.**
   ⇒ Li 제외 판정은 ADR-003 축(b)를 만드는 반응들을 선택적으로 죽인다.

   반대로 Li를 무조건 포함하면 CN 4↔5 호흡 같은 배위 요동이 별개 반응이 된다.
   그러나 그 위양성은 싸다 — 빠르고 가역이라 미세동역학에서 즉시 평형화되고
   DRC가 구조적으로 ~0이라 선별에서 자동 탈락한다. **위음성이 명백히 더 비싸다.**

판정 순서 (위에서부터):
   R1  Layer C 가 다르다                      → distinct  (진짜 결합 생성·절단)
   R2a Layer C 동일, 실체(entity) 수가 변함    → distinct  (회합/해리. ROCO₂Li·LiF·Li₂CO₃)
   R2b Layer C 동일, 실체 수 동일, Layer I 다름 → **속도론**:
         양방향 barrier < τ  → same (병합)
         한쪽이라도 ≥ τ      → distinct
         barrier 미지        → **undetermined** (병합도 분리도 하지 않는다. 사람 검토)
   R3  두 층 모두 동일                         → same

τ = 0.1 eV ≈ 4 k_BT @300 K. conformer 병합 규약(§6.1) 및 0.1 eV 감도 한계(§9)와 같은 값.

단위: 좌표 Angstrom, barrier **eV**. (kcal/mol을 그대로 넣지 마라 — units.py 참조)
"""

from .. import config as config_mod
from . import xyzgraph as xg

DISTINCT = "distinct"
SAME = "same"
UNDETERMINED = "undetermined"


def _layers(atoms, cfg, delta_ang=0.0):
    lc = cfg.get("layer_C") or {}
    li = cfg.get("layer_I") or {}
    bonds_c = xg.layer_c_bonds(atoms, lc.get("elements") or [],
                               lc.get("bond_tolerance", xg.BOND_TOLERANCE))
    contacts_i = xg.layer_i_contacts(atoms, li.get("cations") or [],
                                     li.get("contact_cutoff_ang") or {},
                                     delta_ang=delta_ang)
    return bonds_c, contacts_i


def _verdict(atoms_a, atoms_b, cfg, barrier_fwd_eV, barrier_rev_eV, delta_ang=0.0):
    """R1~R3 판정 1회. 반환 (verdict, rule, facts)."""
    ca, ia = _layers(atoms_a, cfg, delta_ang)
    cb, ib = _layers(atoms_b, cfg, delta_ang)

    hash_c_a = xg.graph_hash(atoms_a, ca)
    hash_c_b = xg.graph_hash(atoms_b, cb)
    hash_ci_a = xg.graph_hash(atoms_a, list(ca) + list(ia))
    hash_ci_b = xg.graph_hash(atoms_b, list(cb) + list(ib))

    n_ent_a = xg.entity_count(len(atoms_a), ca, ia)
    n_ent_b = xg.entity_count(len(atoms_b), cb, ib)

    facts = {
        "endpoint_distinct_C_only": hash_c_a != hash_c_b,
        "endpoint_distinct_with_Li": hash_ci_a != hash_ci_b,
        "entity_count_forward": n_ent_a,
        "entity_count_reverse": n_ent_b,
        "entity_count_change": n_ent_a != n_ent_b,
        "n_layer_c_bonds_forward": len(ca),
        "n_layer_c_bonds_reverse": len(cb),
        "n_layer_i_contacts_forward": len(ia),
        "n_layer_i_contacts_reverse": len(ib),
        "layer_c_changes": sorted(set(ca) ^ set(cb))[:20],
        "layer_i_changes": sorted(set(ia) ^ set(ib))[:20],
        "hash_c_forward": hash_c_a[:64], "hash_c_reverse": hash_c_b[:64],
        "hash_ci_forward": hash_ci_a[:64], "hash_ci_reverse": hash_ci_b[:64],
        "barrier_fwd_eV": barrier_fwd_eV,
        "barrier_rev_eV": barrier_rev_eV,
    }

    # R1
    if facts["endpoint_distinct_C_only"]:
        return DISTINCT, "R1", facts
    # R2a
    if facts["entity_count_change"]:
        return DISTINCT, "R2a", facts
    # R2b
    if facts["endpoint_distinct_with_Li"]:
        tau = (cfg.get("kinetic_merge") or {}).get("tau_eV", 0.1)
        facts["tau_eV"] = tau
        if barrier_fwd_eV is None or barrier_rev_eV is None:
            # 🔴 조용히 기각하면 §12.2의 위음성이 뒷문으로 돌아온다.
            return UNDETERMINED, "R2b-unknown_barrier", facts
        if max(barrier_fwd_eV, barrier_rev_eV) < tau:
            return SAME, "R2b-merged", facts
        return DISTINCT, "R2b-distinct", facts
    # R3
    return SAME, "R3", facts


def classify_endpoints(atoms_a, atoms_b, barrier_fwd_eV=None, barrier_rev_eV=None,
                       cfg=None):
    """IRC 양 끝 구조가 서로 다른 극소인가.

    반환 dict가 그대로 회신 JSON의 `endpoint_comparison` 이 된다.
    임계 민감도(±delta)까지 함께 계산해 **판정이 임계에 종속되는지**를 드러낸다.
    """
    cfg = cfg or config_mod.graph_layers()
    verdict, rule, facts = _verdict(atoms_a, atoms_b, cfg,
                                    barrier_fwd_eV, barrier_rev_eV)

    delta = ((cfg.get("layer_I") or {}).get("sensitivity_delta_ang") or 0.0)
    sensitivity = {"delta_ang": delta, "variants": [], "flips": 0}
    for d in (-delta, +delta):
        if not delta:
            break
        v, r, _f = _verdict(atoms_a, atoms_b, cfg, barrier_fwd_eV, barrier_rev_eV,
                            delta_ang=d)
        flipped = (v != verdict)
        sensitivity["variants"].append(
            {"delta_ang": d, "verdict": v, "rule": r, "flipped": flipped})
        sensitivity["flips"] += 1 if flipped else 0
    sensitivity["threshold_sensitive"] = sensitivity["flips"] > 0

    li_cfg = cfg.get("layer_I") or {}
    out = {
        "verdict": verdict,
        "merge_rule_applied": rule,
        "distinct": verdict == DISTINCT,
        "human_review_required": verdict == UNDETERMINED,
        "rule_source": "02_METHOD_SPEC.md §12.3 (proposer 회신, lead 승인)",
        "method": "2층 그래프(Layer C 공유결합 / Layer I 양이온 배위) + "
                  "Weisfeiler-Lehman 해시. WL은 완전한 동형 판정이 아니다(한계 명시).",
        "config_source": cfg.get("_source"),
        "config_is_fallback": bool(cfg.get("_fallback")),
        "layer_I_cutoffs_ang": li_cfg.get("contact_cutoff_ang"),
        "layer_I_cutoff_provenance": li_cfg.get("_provenance"),
        "threshold_sensitivity": sensitivity,
    }
    out.update(facts)
    out["interpretation"] = _explain(verdict, rule, facts)
    return out


def _explain(verdict, rule, facts):
    if rule == "R1":
        return ("R1: 공유결합 층이 달라졌다(진짜 결합 생성·절단). "
                "Li 배위 변화와 무관하게 서로 다른 극소다.")
    if rule == "R2a":
        return ("R2a: 공유결합 층은 같으나 분자 실체 수가 %d → %d 로 변했다(회합/해리). "
                "ROCO2Li·LiF·Li2CO3 형성이 여기 해당하며, ADR-003 축(b)의 핵심이다."
                % (facts["entity_count_forward"], facts["entity_count_reverse"]))
    if rule == "R2b-unknown_barrier":
        return ("🔴 R2b 판정 불가: 실체 수가 같은 배위 재배열인데 상호전환 barrier를 "
                "모른다. τ 규칙을 적용할 수 없으므로 **병합도 분리도 하지 않는다.** "
                "사람 검토 큐로 보내야 한다(§12.4-4, §12.5). "
                "P1 파일럿은 이 barrier를 계산하지 않으므로 여기 걸리는 것이 정상이다.")
    if rule == "R2b-merged":
        return ("R2b: 배위 재배열이고 양방향 barrier가 모두 τ=%.2f eV 미만이라 "
                "속도론적으로 구별되는 화학종이 아니다 → 한 노드로 병합."
                % facts.get("tau_eV", 0.1))
    if rule == "R2b-distinct":
        return ("R2b: 배위 재배열이나 barrier가 τ=%.2f eV 이상이라 별개 극소로 둔다."
                % facts.get("tau_eV", 0.1))
    return ("R3: 두 층 모두 동일하다 → 같은 극소. IRC가 양쪽에서 같은 곳으로 "
            "굴러떨어졌다는 뜻이며, TS가 그 반응의 TS가 아니거나 IRC가 너무 짧다.")
