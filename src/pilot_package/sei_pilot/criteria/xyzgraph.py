"""XYZ 기하 → 분자 그래프. 순수 파이썬(의존성 0), 순수 함수.

용도:
  1. P1 판정: IRC 양 끝점이 **서로 다른 두 극소**인지 (그래프 동형 여부로 판정)
  2. P3: gen-1 candidate 열거의 그래프 편집
  3. P2: 표적 분자 원자 인덱스 확인

단위: 좌표는 전부 **Angstrom**. 공유결합 반경도 Angstrom.
출처: Cordero et al., Dalton Trans. 2008, 2832 (공유결합 반경, Å).
"""

import math

COVALENT_RADII_ANG = {
    "H": 0.31, "Li": 1.28, "B": 0.84, "C": 0.76, "N": 0.71, "O": 0.66,
    "F": 0.57, "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11, "P": 1.07,
    "S": 1.05, "Cl": 1.02, "K": 2.03, "Ca": 1.76, "Fe": 1.32, "Ni": 1.24,
    "Cu": 1.32, "Zn": 1.22, "Br": 1.20, "I": 1.39,
}
DEFAULT_RADIUS_ANG = 1.5      # 미등록 원소 안전값
BOND_TOLERANCE = 1.25         # d < tol*(r_i+r_j) 이면 결합으로 본다

# Li 배위는 공유결합이 아니라 이온성이라 거리 기준이 애매하다.
# 배위결합을 결합으로 셀지 여부가 IRC 끝점 판정을 바꿀 수 있으므로 옵션으로 뺀다.
IONIC_LIKE = ("Li", "Na", "K", "Mg", "Ca")


def read_xyz_frames(text):
    """다중 프레임 XYZ 파싱 → [(comment, [(sym, x, y, z), ...]), ...] (Angstrom)."""
    lines = (text or "").splitlines()
    frames = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        try:
            n = int(line)
        except ValueError:
            i += 1
            continue
        comment = lines[i + 1] if i + 1 < len(lines) else ""
        atoms = []
        for j in range(i + 2, min(i + 2 + n, len(lines))):
            f = lines[j].split()
            if len(f) < 4:
                continue
            try:
                atoms.append((f[0], float(f[1]), float(f[2]), float(f[3])))
            except ValueError:
                continue
        if len(atoms) == n:
            frames.append((comment.strip(), atoms))
        i += 2 + n
    return frames


def distance_ang(a, b):
    return math.sqrt((a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2 + (a[3] - b[3]) ** 2)


def angle_deg(a, b, c):
    """The angle a-b-c in degrees, vertex at `b`. `None` if either arm has zero length
    (degenerate geometry -- an angle through a coincident point is not a measurement)."""
    v1 = (a[1] - b[1], a[2] - b[2], a[3] - b[3])
    v2 = (c[1] - b[1], c[2] - b[2], c[3] - b[3])
    n1, n2 = math.sqrt(sum(x * x for x in v1)), math.sqrt(sum(x * x for x in v2))
    if n1 == 0 or n2 == 0:
        return None
    cos_t = sum(x * y for x, y in zip(v1, v2)) / (n1 * n2)
    cos_t = max(-1.0, min(1.0, cos_t))  # guard fp drift outside [-1, 1] before acos
    return math.degrees(math.acos(cos_t))


def bond_list(atoms, tolerance=BOND_TOLERANCE, include_ionic=False):
    """결합 리스트 [(i, j)] (i<j). 거리 기준."""
    bonds = []
    n = len(atoms)
    for i in range(n):
        si = atoms[i][0]
        for j in range(i + 1, n):
            sj = atoms[j][0]
            if not include_ionic and (si in IONIC_LIKE or sj in IONIC_LIKE):
                continue
            ri = COVALENT_RADII_ANG.get(si, DEFAULT_RADIUS_ANG)
            rj = COVALENT_RADII_ANG.get(sj, DEFAULT_RADIUS_ANG)
            if distance_ang(atoms[i], atoms[j]) < tolerance * (ri + rj):
                bonds.append((i, j))
    return bonds


def adjacency(n_atoms, bonds):
    adj = dict((i, set()) for i in range(n_atoms))
    for i, j in bonds:
        adj[i].add(j)
        adj[j].add(i)
    return adj


def connected_components(n_atoms, bonds):
    adj = adjacency(n_atoms, bonds)
    seen = set()
    comps = []
    for start in range(n_atoms):
        if start in seen:
            continue
        stack, comp = [start], []
        seen.add(start)
        while stack:
            v = stack.pop()
            comp.append(v)
            for w in adj[v]:
                if w not in seen:
                    seen.add(w)
                    stack.append(w)
        comps.append(sorted(comp))
    return comps


def formula(atoms, indices=None):
    """Hill 표기 분자식 (C, H, 그다음 알파벳순)."""
    idx = range(len(atoms)) if indices is None else indices
    counts = {}
    for i in idx:
        s = atoms[i][0]
        counts[s] = counts.get(s, 0) + 1
    out = []
    for sym in ("C", "H"):
        if sym in counts:
            out.append(sym + (str(counts[sym]) if counts[sym] > 1 else ""))
    for sym in sorted(k for k in counts if k not in ("C", "H")):
        out.append(sym + (str(counts[sym]) if counts[sym] > 1 else ""))
    return "".join(out)


def graph_hash(atoms, bonds, iterations=3):
    """Weisfeiler-Lehman 1차원 색 재정의 기반 그래프 해시.

    원자 번호(원소기호)와 연결성만 사용한다. 좌표 회전/원자 순서에 불변이다.
    완전한 동형 판정은 아니지만(WL의 알려진 한계) 우리 규모의 유기 분자에서
    서로 다른 두 극소를 구분하는 데는 충분하다. **한계를 명시해 둔다.**
    """
    n = len(atoms)
    adj = adjacency(n, bonds)
    colors = [atoms[i][0] for i in range(n)]
    for _ in range(iterations):
        new = []
        for i in range(n):
            nb = sorted(colors[j] for j in adj[i])
            new.append(colors[i] + "(" + ",".join(nb) + ")")
        # 색 압축 (문자열 폭발 방지).
        # 🔴 압축 라벨은 **정렬된 색 집합**에 부여해야 한다. 처음 만난 순서로 부여하면
        #    원자 순서에 따라 해시가 달라져 동형 판정이 깨진다(테스트로 잡힌 버그).
        table = dict((c, "c%d" % i) for i, c in enumerate(sorted(set(new))))
        colors = [table[c] for c in new]
    return "|".join(sorted(colors)) + "#" + formula(atoms)


def layer_c_bonds(atoms, elements, tolerance=BOND_TOLERANCE):
    """Layer C — 공유결합 층 (02_METHOD_SPEC §12.3). **양이온은 여기 없다.**

    elements 목록에 없는 원소(= Li 등 양이온)가 관여하는 쌍은 전부 제외한다.
    """
    allowed = set(elements)
    bonds = []
    n = len(atoms)
    for i in range(n):
        if atoms[i][0] not in allowed:
            continue
        ri = COVALENT_RADII_ANG.get(atoms[i][0], DEFAULT_RADIUS_ANG)
        for j in range(i + 1, n):
            if atoms[j][0] not in allowed:
                continue
            rj = COVALENT_RADII_ANG.get(atoms[j][0], DEFAULT_RADIUS_ANG)
            if distance_ang(atoms[i], atoms[j]) < tolerance * (ri + rj):
                bonds.append((i, j))
    return bonds


def contact_cutoff_ang(cutoffs, sym_a, sym_b):
    """`{"Li-O": 2.4, ...}` 에서 쌍별 임계를 찾는다. 순서 무관, 없으면 default."""
    for key in ("%s-%s" % (sym_a, sym_b), "%s-%s" % (sym_b, sym_a)):
        if key in cutoffs:
            return cutoffs[key]
    return cutoffs.get("default", 2.5)


def layer_i_contacts(atoms, cations, cutoffs, delta_ang=0.0):
    """Layer I — 양이온-배위 원자 접촉 (거리 기준).

    delta_ang 을 주면 임계를 그만큼 흔든다(민감도 보고용, §12.4-3).
    """
    cat = set(cations)
    contacts = []
    n = len(atoms)
    for i in range(n):
        for j in range(i + 1, n):
            si, sj = atoms[i][0], atoms[j][0]
            a_is_cat, b_is_cat = si in cat, sj in cat
            if a_is_cat == b_is_cat:
                continue          # 양이온-양이온, 비양이온-비양이온은 이 층이 아니다
            cut = contact_cutoff_ang(cutoffs, si, sj) + delta_ang
            if distance_ang(atoms[i], atoms[j]) < cut:
                contacts.append((i, j))
    return contacts


def entity_count(n_atoms, layer_c, layer_i):
    """두 층을 **합친** 그래프의 연결 성분 수 = 분자 실체(entity) 수.

    `ROCO2- + Li+` (2개) → `ROCO2Li` (1개) 를 구분하는 양이며,
    R2a(회합/해리)가 이 값의 변화로 정의된다.
    """
    return len(connected_components(n_atoms, list(layer_c) + list(layer_i)))


def structures_distinct(atoms_a, atoms_b, tolerance=BOND_TOLERANCE,
                        include_ionic=False):
    """두 구조가 서로 다른 극소인가? (P1 IRC 판정의 핵심)

    `include_ionic` 이 판정을 바꾼다:
      False (기본) — Li⁺ 배위 변화만 있는 쌍은 **같은 극소**로 본다.
      True         — 배위 변화도 결합 변화로 세어 **다른 극소**로 본다.
    이 선택은 화학적 판단이며 coder가 정할 것이 아니다. lead가 proposer에게
    질의했고 회신 전까지 기본값을 유지한다. `[UNRESOLVED: IRC-CONV]`
    ⇒ 호출자는 **양쪽 규약의 결과를 모두 회신**해야 나중에 재해석이 가능하다.

    반환: (distinct: bool, info: dict)
    """
    ba = bond_list(atoms_a, tolerance, include_ionic)
    bb = bond_list(atoms_b, tolerance, include_ionic)
    ha = graph_hash(atoms_a, ba)
    hb = graph_hash(atoms_b, bb)
    fa = sorted(formula(atoms_a, c) for c in connected_components(len(atoms_a), ba))
    fb = sorted(formula(atoms_b, c) for c in connected_components(len(atoms_b), bb))
    return ha != hb, {
        "hash_a": ha[:64], "hash_b": hb[:64],
        "fragments_a": fa, "fragments_b": fb,
        "n_bonds_a": len(ba), "n_bonds_b": len(bb),
        "bond_changes": sorted(set(ba) ^ set(bb)),
        "include_ionic": include_ionic,
        "bond_tolerance": tolerance,
        "ionic_elements": list(IONIC_LIKE),
        "note": ("Li 등 이온성 배위를 결합으로 %s하고 판정했다."
                 % ("포함" if include_ionic else "제외")),
    }
