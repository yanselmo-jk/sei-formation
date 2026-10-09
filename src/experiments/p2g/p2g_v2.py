#!/usr/bin/env python3
"""V2 — Li+(EC)4 액체 궤적에서 **Li–O RDF** 첫 봉우리와 배위수.

🔴 판정하지 않는다. 봉우리 위치가 타당한지는 proposer 몫이다. 우리는 수와 그 조건
(궤적 길이·완화 구간 버림·상자 크기)을 함께 낸다.

단위: 거리 Å, 에너지 Hartree. xtb 궤적(`xtb.trj`)은 **Å** 로 쓴다.
"""
import json
import math
import os
import sys

HERE = os.environ.get("SEI_PKG_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pilot_package"))
sys.path.insert(0, HERE)
from sei_pilot import config  # noqa: E402

BIN_WIDTH_ANG = 0.05
R_MAX_ANG = 6.0
# 🔴 첫 봉우리 뒤의 **첫 극소**까지 적분해 배위수를 낸다. 임의의 컷오프를 박지 않는다.
EQUILIBRATION_FRACTION = 0.2      # 앞 20 %는 인공적 시작점의 완화 구간으로 버린다


def read_trj(path):
    """xtb 궤적(다중 xyz) → [(frame_atoms)] . 좌표 Å."""
    frames, lines = [], open(path, errors="replace").read().splitlines()
    i = 0
    while i < len(lines):
        try:
            n = int(lines[i].split()[0])
        except (ValueError, IndexError):
            break
        atoms = []
        for l in lines[i + 2:i + 2 + n]:
            f = l.split()
            if len(f) >= 4:
                atoms.append((f[0], float(f[1]), float(f[2]), float(f[3])))
        if len(atoms) == n:
            frames.append(atoms)
        i += n + 2
    return frames


def rdf(frames, box_ang, a_sym="Li", b_sym="O"):
    nb = int(R_MAX_ANG / BIN_WIDTH_ANG)
    hist = [0.0] * nb
    n_a = n_b = 0
    for atoms in frames:
        ai = [k for k, x in enumerate(atoms) if x[0].capitalize() == a_sym]
        bi = [k for k, x in enumerate(atoms) if x[0].capitalize() == b_sym]
        n_a, n_b = len(ai), len(bi)
        for p in ai:
            for q in bi:
                d = 0.0
                for c in (1, 2, 3):
                    dx = atoms[p][c] - atoms[q][c]
                    dx -= box_ang * round(dx / box_ang)     # 최소상 규약
                    d += dx * dx
                d = math.sqrt(d)
                if d < R_MAX_ANG:
                    hist[int(d / BIN_WIDTH_ANG)] += 1.0
    if not frames or not n_a or not n_b:
        return None
    rho_b = n_b / (box_ang ** 3)
    g, cn, r_vals = [], [], []
    running = 0.0
    for k in range(nb):
        r_lo, r_hi = k * BIN_WIDTH_ANG, (k + 1) * BIN_WIDTH_ANG
        shell = 4.0 / 3.0 * math.pi * (r_hi ** 3 - r_lo ** 3)
        ideal = shell * rho_b * n_a * len(frames)
        g.append(hist[k] / ideal if ideal else 0.0)
        running += hist[k] / (n_a * len(frames))
        cn.append(running)
        r_vals.append(0.5 * (r_lo + r_hi))
    return {"r_ang": r_vals, "g": g, "cumulative_coordination": cn}


def first_peak_and_cn(res):
    g, r, cn = res["g"], res["r_ang"], res["cumulative_coordination"]
    lo = next((k for k, v in enumerate(g) if v > 0), None)
    if lo is None:
        return None, None, None
    pk = max(range(lo, len(g)), key=lambda k: g[k])
    mn = pk
    while mn + 1 < len(g) and g[mn + 1] <= g[mn]:
        mn += 1
    return r[pk], r[mn], cn[mn]


def main():
    d = sys.argv[1]
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "p2g.json")))["v2_li_ec_rdf"]
    boxes = json.load(open(os.path.join(d, "boxes.json")))
    box_ang = boxes["v2"]["box_ang"]
    trj = os.path.join(d, "v2", "xtb.trj")
    out = {"test": "V2 Li+(EC)4 liquid, Li–O RDF",
           "picoseconds_requested": cfg["picoseconds"],
           "box_ang": box_ang, "composition": boxes["v2"]}
    if not os.path.exists(trj):
        out.update({"status": "no_trajectory",
                    "why": "xtb.trj 가 없다 — MD 가 시작 전에 죽었거나 wall 에 잘렸다."})
    else:
        frames = read_trj(trj)
        keep = frames[int(len(frames) * EQUILIBRATION_FRACTION):] or frames
        res = rdf(keep, box_ang)
        peak, minimum, cn = first_peak_and_cn(res) if res else (None, None, None)
        out.update({
            "status": "ok" if res else "no_pairs",
            "n_frames_total": len(frames),
            "n_frames_used": len(keep),
            "equilibration_fraction_discarded": EQUILIBRATION_FRACTION,
            "v2_li_o_rdf_first_peak_ang": peak,
            "v2_first_minimum_ang": minimum,
            "v2_coordination_number": cn,
            "rdf": res,
            "_caveat": ("시작 배치가 단순 격자라 인공적이다. 앞 %d%% 를 버렸으나 "
                        "50 ps 가 충분한지는 우리가 판정하지 않는다."
                        % int(EQUILIBRATION_FRACTION * 100)),
        })
    with open(os.path.join(d, "v2_result.json"), "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("[P2g] V2 status=%s first_peak=%s CN=%s"
          % (out.get("status"), out.get("v2_li_o_rdf_first_peak_ang"),
             out.get("v2_coordination_number")))


if __name__ == "__main__":
    main()
