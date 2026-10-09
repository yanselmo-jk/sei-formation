"""P3용 gen-1 반응 candidate 열거 (참조 구현).

🔴 **범위 경고 — 반드시 읽어라.**
ADR-006이 잠정 채택한 S2 엔진은 S2-A(열거-후-여과 CRN: fragment-recombine + species
pool)이며 **아직 조건부(P0 미확정)** 다. 여기 구현한 것은 그 엔진이 아니라,
파일럿 P3가 "시도 1건당 xTB 단가와 수렴률"을 재기 위해 필요한 **후보 생성기**다.

모드:
  * `b2f2_graph_edit` (기본) — YARP류 그래프 편집(결합 m개 절단 + n개 생성, m,n<=2).
    규칙이 문헌에 정의돼 있고 분자 그래프만으로 결정되므로 재현 가능하다.
    🔴 이 모드의 candidate 수를 **S2-A fanout 견적에 직접 대입하지 마라.**
  * `libe_pool_recombine` — species pool이 주어졌을 때 pool 위 화학양론 균형 조합.
    (pool 파일이 패키지에 동봉된 경우에만 활성. 현재 미동봉.)

방법론을 새로 정하지 않는다. 이 모듈이 만드는 숫자는 **단가 측정용**이며,
S2 견적에 쓰려면 lead/proposer의 판정이 필요하다.
"""

from .criteria.xyzgraph import bond_list, connected_components, formula

# 원소별 최대 결합수(가전자 규칙 단순화). 라디칼을 다루므로 상한만 건다.
MAX_VALENCE = {"H": 1, "C": 4, "N": 4, "O": 2, "F": 1, "Li": 1, "P": 6, "S": 6}


def _degrees(n_atoms, bonds):
    deg = [0] * n_atoms
    for i, j in bonds:
        deg[i] += 1
        deg[j] += 1
    return deg


def enumerate_b2f2(atoms, max_break=2, max_form=2, include_ionic=False):
    """결합 <=2개 절단 + <=2개 생성 조합 열거 → candidate 목록.

    반환: [{"break": [(i,j)...], "form": [(i,j)...], "fragments": [...]}]
    가지치기:
      * 절단만 하고 생성이 없으면 = 단순 해리 (허용, 별도 표시)
      * 원자가 초과 생성은 버린다
      * 절단·생성이 동일한 결합쌍이면 항등 반응이므로 버린다
    """
    n = len(atoms)
    bonds = bond_list(atoms, include_ionic=include_ionic)
    bond_set = set(bonds)
    non_bonds = [(i, j) for i in range(n) for j in range(i + 1, n)
                 if (i, j) not in bond_set]
    # 수소 원자 사이의 새 결합(H2 생성)은 남기되, Li 배위는 제외(이온성)
    if not include_ionic:
        ionic = set(i for i in range(n) if atoms[i][0] in ("Li", "Na", "K"))
        non_bonds = [(i, j) for (i, j) in non_bonds if i not in ionic and j not in ionic]

    out = []
    break_sets = [[]]
    for b in bonds:
        break_sets.append([b])
    if max_break >= 2:
        for a in range(len(bonds)):
            for b in range(a + 1, len(bonds)):
                break_sets.append([bonds[a], bonds[b]])

    form_sets = [[]]
    for nb in non_bonds:
        form_sets.append([nb])
    if max_form >= 2:
        for a in range(len(non_bonds)):
            for b in range(a + 1, len(non_bonds)):
                form_sets.append([non_bonds[a], non_bonds[b]])

    for brk in break_sets:
        for frm in form_sets:
            if not brk and not frm:
                continue
            if len(frm) > len(brk) + 1:
                # 결합을 만들기만 하는 조합은 gen-1에서 폭발하므로 제한
                continue
            new_bonds = [b for b in bonds if b not in set(brk)] + list(frm)
            deg = _degrees(n, new_bonds)
            if any(deg[i] > MAX_VALENCE.get(atoms[i][0], 4) for i in range(n)):
                continue
            comps = connected_components(n, new_bonds)
            out.append({
                "break": [list(b) for b in brk],
                "form": [list(f) for f in frm],
                "n_fragments": len(comps),
                "fragments": sorted(formula(atoms, c) for c in comps),
                "kind": ("dissociation" if not frm else
                         ("isomerization" if len(comps) == 1 else "rearrangement")),
            })
    return out


def dedupe_by_product(candidates):
    """생성물 조성이 같은 candidate를 묶는다 (열거 수 vs 고유 생성물 수는 다른 숫자다)."""
    seen = {}
    for c in candidates:
        key = "+".join(c["fragments"])
        seen.setdefault(key, []).append(c)
    return seen


def build_candidate_geometry(atoms, candidate, break_push=1.6, form_target=1.55):
    """candidate(그래프 편집) → **거친** 생성물 좌표 추측 (Angstrom).

    절단할 결합은 두 원자를 결합축 방향으로 벌리고, 생성할 결합은 두 원자를
    목표 거리까지 당긴다. 최적화 전 추측일 뿐이며, xTB opt가 실제 극소를 만든다.
    (여기서 나오는 구조를 그대로 에너지에 쓰면 안 된다.)
    """
    import math
    pos = [[a[1], a[2], a[3]] for a in atoms]
    syms = [a[0] for a in atoms]

    def unit(i, j):
        v = [pos[j][k] - pos[i][k] for k in range(3)]
        n = math.sqrt(sum(x * x for x in v)) or 1.0
        return [x / n for x in v], n

    for i, j in candidate.get("break", []):
        u, _n = unit(i, j)
        for k in range(3):
            pos[i][k] -= 0.5 * break_push * u[k]
            pos[j][k] += 0.5 * break_push * u[k]
    for i, j in candidate.get("form", []):
        u, n = unit(i, j)
        shift = (n - form_target) / 2.0
        for k in range(3):
            pos[i][k] += shift * u[k]
            pos[j][k] -= shift * u[k]
    return [(syms[i], pos[i][0], pos[i][1], pos[i][2]) for i in range(len(atoms))]


def to_xyz(atoms, comment=""):
    lines = ["%d" % len(atoms), comment]
    for s, x, y, z in atoms:
        lines.append("%-3s %12.6f %12.6f %12.6f" % (s, x, y, z))
    return "\n".join(lines) + "\n"


def sample_candidates(candidates, n):
    """candidate 목록에서 n개를 **고르게** 뽑는다 (앞쪽만 뽑으면 한 종류만 걸린다)."""
    if n >= len(candidates):
        return list(candidates)
    step = len(candidates) / float(n)
    return [candidates[int(i * step)] for i in range(n)]


def enumerate_for_reactant(atoms, mode="b2f2_graph_edit", **kw):
    if mode != "b2f2_graph_edit":
        raise ValueError("지원하지 않는 열거 모드: %s "
                         "(libe_pool_recombine 는 pool 파일이 필요하며 현재 미동봉)" % mode)
    cands = enumerate_b2f2(atoms, **kw)
    groups = dedupe_by_product(cands)
    return {
        "mode": mode,
        "n_candidates": len(cands),
        "n_unique_products": len(groups),
        "candidates": cands,
        "note": "n_candidates는 그래프 편집 조합 수, n_unique_products는 생성물 조성 "
                "기준 고유 수다. S2 fanout 논의에서 둘을 섞지 마라.",
    }
