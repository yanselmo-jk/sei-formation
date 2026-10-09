#!/usr/bin/env python3
"""P2g 용 주기계 상자 생성 (Turbomole `coord` 형식).

🔴 왜 xyz 가 아니라 coord 인가: **xyz 에는 격자가 없다.** xtb 의 주기계 GFN-FF 는
`$periodic` / `$lattice` 가 있는 Turbomole coord(또는 POSCAR)만 읽는다.
(우리 박스에서 동봉 xtb 6.7.1 로 실제 확인했다 — 물 2분자 주기계 SP 정상 종료.)

단위 주의: coord 파일의 좌표는 **bohr** 다. 입력 xyz 는 **Å** 다. 변환은
`sei_pilot.units` 한 곳에서 온다.
"""

import json
import os
import sys

sys.path.insert(0, os.environ.get("SEI_PKG_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pilot_package")))
from sei_pilot import units  # noqa: E402

# 실험 밀도 (문헌값. 우리가 지어낸 수치가 아니다)
DENSITY_G_CM3 = {"ec": 1.321}          # ethylene carbonate, 313 K
MOLAR_MASS_G_MOL = {"ec": 88.062}
N_AVOGADRO = 6.02214076e23


def read_xyz(path):
    with open(path) as fh:
        lines = fh.read().splitlines()
    n = int(lines[0].split()[0])
    return [(f[0], float(f[1]), float(f[2]), float(f[3]))
            for f in (l.split() for l in lines[2:2 + n]) if f]


def centre(atoms):
    n = float(len(atoms))
    cx = sum(a[1] for a in atoms) / n
    cy = sum(a[2] for a in atoms) / n
    cz = sum(a[3] for a in atoms) / n
    return [(a[0], a[1] - cx, a[2] - cy, a[3] - cz) for a in atoms]


def build_mixture(spec_dir, counts, density_g_cm3=1.35):
    """여러 종을 섞은 주기 상자. `counts` = [(xyz파일, 개수, 분자량), ...]

    🔴 배치는 단순 격자다(무작위 회전 없음). 목적이 **MD 시작점**이므로 충분하다 —
    첫 수 ps 가 구조를 풀어준다. 다만 시작점이 인공적이라는 사실은 회신에 남긴다.
    """
    import math
    items = []
    total_mass = 0.0
    for fname, n, mw in counts:
        mol = centre(read_xyz(os.path.join(spec_dir, fname) if spec_dir else fname))
        items += [mol] * n
        total_mass += n * mw
    vol_ang3 = total_mass / (density_g_cm3 * N_AVOGADRO) * 1e24
    box = vol_ang3 ** (1.0 / 3.0)
    n_side = int(math.ceil(len(items) ** (1.0 / 3.0)))
    step = box / n_side
    atoms, idx = [], 0
    for i in range(n_side):
        for j in range(n_side):
            for k in range(n_side):
                if idx >= len(items):
                    break
                ox, oy, oz = (i + 0.5) * step, (j + 0.5) * step, (k + 0.5) * step
                for sym, x, y, z in items[idx]:
                    atoms.append((sym, x + ox, y + oy, z + oz))
                idx += 1
    return atoms, box


def build(mol_xyz, n_side, species="ec"):
    """n_side^3 개 분자를 단순 격자에 놓는다. 상자 길이는 실험 밀도에서 나온다."""
    mol = centre(read_xyz(mol_xyz))
    n_mol = n_side ** 3
    vol_ang3 = (n_mol * MOLAR_MASS_G_MOL[species]
                / (DENSITY_G_CM3[species] * N_AVOGADRO) * 1e24)
    box = vol_ang3 ** (1.0 / 3.0)
    step = box / n_side
    atoms = []
    for i in range(n_side):
        for j in range(n_side):
            for k in range(n_side):
                ox, oy, oz = (i + 0.5) * step, (j + 0.5) * step, (k + 0.5) * step
                for sym, x, y, z in mol:
                    atoms.append((sym, x + ox, y + oy, z + oz))
    return atoms, box


def write_coord(path, atoms, box_ang):
    """Turbomole coord. **좌표·격자 모두 bohr 로 쓴다.**"""
    b = units.ANGSTROM_TO_BOHR
    with open(path, "w") as fh:
        fh.write("$coord\n")
        for sym, x, y, z in atoms:
            fh.write("%20.12f%20.12f%20.12f  %s\n"
                     % (x * b, y * b, z * b, sym.lower()))
        fh.write("$periodic 3\n$lattice bohr\n")
        for i in range(3):
            fh.write("%16.8f%16.8f%16.8f\n"
                     % tuple(box_ang * b if j == i else 0.0 for j in range(3)))
        fh.write("$end\n")


def main():
    mol = sys.argv[1]
    out = sys.argv[2]
    n_side = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    atoms, box = build(mol, n_side)
    write_coord(out, atoms, box)
    meta = {"n_molecules": n_side ** 3, "n_atoms": len(atoms),
            "box_ang": round(box, 6), "n_side": n_side,
            "density_g_cm3": DENSITY_G_CM3["ec"],
            "density_source": "실험 문헌값 (EC, 313 K). 우리가 지어낸 값이 아니다.",
            "format": "Turbomole coord, $periodic 3, 좌표·격자 단위 bohr",
            "why_not_xyz": "xyz 에는 격자가 없다. xtb 주기계 GFN-FF 가 못 읽는다."}
    with open(os.path.splitext(out)[0] + ".meta.json", "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("%s: %d molecules, %d atoms, box %.3f Ang"
          % (out, meta["n_molecules"], meta["n_atoms"], box))


if __name__ == "__main__":
    main()
