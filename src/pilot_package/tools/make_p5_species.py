#!/usr/bin/env python3
"""P5용 대표 소분자 세트 생성기 — **결정론적**.

목적(lead 지시 2): pool thermo 단가를 **단일 숫자가 아니라 크기별 곡선**으로 재려면
축을 덮는 대표 종이 필요하다.

  * 원자수: ~5 / ~10 / ~15 / ~20 / ~25   (pool 실측 상한 22원자)
  * 전하:   −1 / 0 / +1
  * 스핀:   닫힌껍질 / 개각(라디칼)      ← 개각은 비용 대략 2배. 반드시 포함

좌표 단위는 전부 **Angstrom**. 이상화 기하이며 **최적화된 값이 아니다** —
P5가 하는 일이 opt+freq이므로 출발점이면 충분하다. 그러나 결합길이·겹침은
`tests/test_p5_species.py` 가 검증한다(SCF가 즉사하는 구조를 보내지 않기 위함).

⚠ 화학종 선택은 SEI 화학(ADR-001 EC:EMC + LiPF6)에서 실제로 나오는 것들로 골랐다.
단가 측정이 목적이므로 **여기서 나오는 에너지는 쓰지 않는다.**
"""

import json
import math
import os
import sys

# --- 기본 단분자 (이상화 기하) ---------------------------------------------
H2O = [("O", 0.000, 0.000, 0.119), ("H", 0.000, 0.763, -0.477),
       ("H", 0.000, -0.763, -0.477)]

CO2 = [("C", 0.0, 0.0, 0.0), ("O", 0.0, 0.0, 1.160), ("O", 0.0, 0.0, -1.160)]

C2H4 = [("C", 0.000, 0.000, 0.668), ("C", 0.000, 0.000, -0.668),
        ("H", 0.000, 0.923, 1.238), ("H", 0.000, -0.923, 1.238),
        ("H", 0.000, 0.923, -1.238), ("H", 0.000, -0.923, -1.238)]

#: 메톡시 라디칼 CH3O• — 개각(doublet) 소형 대표
CH3O = [("C", 0.000, 0.000, 0.000), ("O", 0.000, 0.000, 1.370),
        ("H", 1.020, 0.000, -0.360), ("H", -0.510, 0.883, -0.360),
        ("H", -0.510, -0.883, -0.360)]

#: 탄산수소 이온 HCO3⁻ — 음이온 소형 대표 (SEI 가수분해 갈래)
HCO3 = [("C", 0.000, 0.000, 0.000), ("O", 0.000, 1.250, 0.000),
        ("O", 1.150, -0.680, 0.000), ("O", -1.180, -0.700, 0.000),
        ("H", -1.900, -0.050, 0.000)]

#: PF6⁻ 팔면체 — 음이온 중형, P 포함(기저 스케일링이 다르다)
PF6 = [("P", 0.0, 0.0, 0.0), ("F", 1.6, 0.0, 0.0), ("F", -1.6, 0.0, 0.0),
       ("F", 0.0, 1.6, 0.0), ("F", 0.0, -1.6, 0.0),
       ("F", 0.0, 0.0, 1.6), ("F", 0.0, 0.0, -1.6)]

#: EC (ethylene carbonate) — inputs/li_ec_radical_reactant.xyz 와 동일 기하
EC = [("C", 0.000, 1.190, 0.000), ("O", -1.132, 0.368, 0.000),
      ("C", -0.699, -0.963, 0.000), ("C", 0.699, -0.963, 0.000),
      ("O", 1.132, 0.368, 0.000), ("O", 0.000, 2.390, 0.000),
      ("H", -1.049, -1.443, 0.880), ("H", -1.049, -1.443, -0.880),
      ("H", 1.049, -1.443, 0.880), ("H", 1.049, -1.443, -0.880)]

#: EMC (ethyl methyl carbonate)
EMC = [("C", 0.000, 0.000, 0.000), ("O", 0.000, 1.200, 0.000),
       ("O", -1.150, -0.700, 0.000), ("O", 1.150, -0.700, 0.000),
       ("C", -2.400, 0.050, 0.000), ("C", 2.400, 0.050, 0.000),
       ("C", 3.600, -0.850, 0.000),
       ("H", -3.250, -0.620, 0.000), ("H", -2.450, 0.680, 0.890),
       ("H", -2.450, 0.680, -0.890), ("H", 2.450, 0.680, 0.890),
       ("H", 2.450, 0.680, -0.890), ("H", 4.500, -0.300, 0.000),
       ("H", 3.620, -1.480, 0.890), ("H", 3.620, -1.480, -0.890)]


def translate(atoms, dx=0.0, dy=0.0, dz=0.0):
    return [(s, x + dx, y + dy, z + dz) for s, x, y, z in atoms]


def li_at(x, y, z):
    return [("Li", x, y, z)]


# --- 대표 종 정의 -----------------------------------------------------------
# (id, atoms, charge, multiplicity, 설명)
def species():
    ec2 = EC + translate(EC, 0.0, 0.0, 4.2)          # EC 이량체(적층)
    return [
        ("h2o", H2O, 0, 1, "H2O — 미량 수분(HF 자기촉매 갈래의 출발점)"),
        ("co2", CO2, 0, 1, "CO2 — ADR-003 검증 가스종"),
        ("hco3_anion", HCO3, -1, 1, "HCO3- — 음이온 소형, 가수분해 갈래"),
        ("ch3o_radical", CH3O, 0, 2, "CH3O• — 개각 소형 (비용 ~2배 축)"),
        ("c2h4", C2H4, 0, 1, "C2H4 — ADR-003 검증 가스종"),
        ("pf6_anion", PF6, -1, 1, "PF6- — 음이온 + P (기저 스케일링이 다르다)"),
        ("ec", EC, 0, 1, "EC — 주 용매"),
        ("ec_radical_anion", EC, -1, 2, "EC•- — 환원 1단계. 개각 + 음이온"),
        ("li_ec_cation", EC + li_at(0.0, 4.24, 0.0), 1, 1, "Li+(EC) — 양이온 착물"),
        ("li_ec_radical", EC + li_at(0.0, 4.24, 0.0), 0, 2, "Li(EC)• — 환원 착물, 개각"),
        ("emc", EMC, 0, 1, "EMC — 공용매 (15원자)"),
        ("emc_radical_anion", EMC, -1, 2, "EMC•- — 15원자 개각 음이온"),
        ("ec_dimer", ec2, 0, 1, "EC 이량체 (20원자) — LEDC 전구체 크기대"),
        ("li_ec2_cation", ec2 + li_at(0.0, 2.4, 2.1), 1, 1,
         "Li+(EC)2 — 21원자, pool 상한(22) 근처"),
    ]


#: 값싼 레벨로도 돌려 **소분자에서의 단가비**를 얻을 종
#: (P1b는 40~80원자 TS에서 쟀다. 소분자에서 비율이 다를 수 있다.)
CHEAP_LEVEL_SUBSET = ("co2", "ec", "emc", "li_ec2_cation")


def to_xyz(atoms, comment):
    lines = ["%d" % len(atoms), comment]
    for s, x, y, z in atoms:
        lines.append("%-3s %12.6f %12.6f %12.6f" % (s, x, y, z))
    return "\n".join(lines) + "\n"


def min_distance(atoms):
    best = 1e9
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            d = math.sqrt(sum((atoms[i][k] - atoms[j][k]) ** 2 for k in (1, 2, 3)))
            best = min(best, d)
    return best


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "inputs", "p5_species")
    if not os.path.isdir(out_dir):
        os.makedirs(out_dir)
    manifest = []
    for sid, atoms, charge, mult, desc in species():
        dmin = min_distance(atoms)
        if dmin < 0.9:
            raise SystemExit("겹친 원자: %s (min %.3f A)" % (sid, dmin))
        fn = sid + ".xyz"
        with open(os.path.join(out_dir, fn), "w") as fh:
            fh.write(to_xyz(atoms, "%s | charge=%d mult=%d | %s | idealized, NOT optimized"
                            % (sid, charge, mult, desc)))
        manifest.append({"id": sid, "file": fn, "n_atoms": len(atoms),
                         "charge": charge, "multiplicity": mult,
                         "open_shell": mult > 1, "description": desc,
                         "cheap_level_too": sid in CHEAP_LEVEL_SUBSET,
                         "min_interatomic_distance_ang": round(dmin, 3)})
    meta = {
        "_doc": "P5 대표 소분자 세트 (opt+freq 단가 곡선용).",
        "_generator": "tools/make_p5_species.py (결정론적)",
        "_levels": {
            "primary": "wB97X-V/def2-TZVPPD/SMD  (ADR-029 기본값)",
            "cheap": "wB97X-D3/def2-TZVP/SMD     (소분자 단가비 측정용)"},
        "_note": "이상화 기하이며 최적화된 값이 아니다. 여기서 나오는 에너지는 쓰지 않는다 — 목적은 단가 측정이다.",
        "species": manifest,
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    sizes = sorted(set(m["n_atoms"] for m in manifest))
    print("wrote %d species → %s" % (len(manifest), out_dir))
    print("  원자수 분포: %s" % sizes)
    print("  전하: %s / 개각: %d종"
          % (sorted(set(m["charge"] for m in manifest)),
             sum(1 for m in manifest if m["open_shell"])))


if __name__ == "__main__":
    main()
