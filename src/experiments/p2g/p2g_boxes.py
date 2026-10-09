#!/usr/bin/env python3
"""P2g 상자 생성 — V1(순수 EC)과 V2(LiPF6/EC) 두 개. 사양은 config/p2g.json."""
import json
import os
import sys

HERE = os.environ.get("SEI_PKG_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pilot_package"))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sei_pilot import config                      # noqa: E402
import make_ec_box as box                         # noqa: E402

# 분자량 (g/mol). 원소 질량 합이며 지어낸 값이 아니다.
MW = {"li.xyz": 6.94, "pf6_anion.xyz": 144.96, "ec.xyz": 88.062}


def main():
    d = sys.argv[1]
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "p2g.json")))
    spec = os.path.join(HERE, "inputs", "p5_species")
    # V1 전용 입력은 실험 디렉터리에 있다(패키지 밖).
    p2g_in = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                          "inputs")

    # --- V1: 순수 EC 상자 ---
    v1 = cfg["v1_translation_invariance"]
    os.makedirs(os.path.join(d, "v1"), exist_ok=True)
    atoms, b = box.build(os.path.join(spec, "ec.xyz"), int(v1["box_n_side"]))
    box.write_coord(os.path.join(d, "v1", "coord"), atoms, b)

    # --- V2: LiPF6 / EC 혼합 상자 (셀 총전하 0) ---
    comp = cfg["v2_li_ec_rdf"]["composition"]
    counts = [(os.path.join(p2g_in, "li.xyz"), int(comp["n_li"]), MW["li.xyz"]),
              (os.path.join(spec, "pf6_anion.xyz"), int(comp["n_pf6"]),
               MW["pf6_anion.xyz"]),
              (os.path.join(spec, "ec.xyz"), int(comp["n_ec"]), MW["ec.xyz"])]
    atoms2, b2 = box.build_mixture("", [(f, n, m) for f, n, m in counts])
    os.makedirs(os.path.join(d, "v2"), exist_ok=True)
    box.write_coord(os.path.join(d, "v2", "coord"), atoms2, b2)

    md = cfg["v2_li_ec_rdf"]
    with open(os.path.join(d, "v2", "md.inp"), "w") as fh:
        fh.write("$md\n   temp=%.1f\n   time=%.1f\n   dump=%.1f\n   step=%.1f\n"
                 "   hmass=1\n   nvt=true\n$end\n"
                 % (md["temperature_k"], md["picoseconds"], md["dump_fs"],
                    md["timestep_fs"]))

    meta = {"v1": {"n_atoms": len(atoms), "box_ang": round(b, 4),
                   "n_molecules": int(v1["box_n_side"]) ** 3},
            "v2": {"n_atoms": len(atoms2), "box_ang": round(b2, 4),
                   "n_li": comp["n_li"], "n_pf6": comp["n_pf6"],
                   "n_ec": comp["n_ec"], "net_charge": 0,
                   "picoseconds": md["picoseconds"]},
            "_start_geometry": ("단순 격자 배치(무작위 회전 없음). MD 시작점으로는 "
                                "충분하나 **인공적**이며, 첫 수 ps 는 완화 구간이다."),
            "_composition_decision": comp["_decision"]}
    with open(os.path.join(d, "boxes.json"), "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=1)
    print("[P2g] V1 %d atoms / box %.2f A | V2 %d atoms / box %.2f A"
          % (len(atoms), b, len(atoms2), b2))


if __name__ == "__main__":
    main()
