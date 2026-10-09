#!/usr/bin/env python3
"""V1 — GFN-FF 주기계 **평행이동 불변성** 시험 (xtb Issue #1118).

같은 물리 배치를 셀 안에서 옮겨 놓았을 뿐인데 에너지가 달라지면, 그 엔진으로 하는
PBC MD 는 신뢰할 수 없다. 이건 **필요조건**이다.

🔴 판정하지 않는다 — `invariant: true|false` 와 편차 크기만 낸다.
"""
import json
import os
import re
import subprocess
import sys

HERE = os.environ.get("SEI_PKG_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pilot_package"))
sys.path.insert(0, HERE)
from sei_pilot import config, units  # noqa: E402

E_RE = re.compile(r"TOTAL ENERGY\s+(-?\d+\.\d+)")
# 🔴 GFN-FF 는 좌표를 셀 안으로 랩한 **뒤** 공유결합 토폴로지를 만든다. 그 과정에
#    최소상 규약이 없으면 셀 경계를 가로지르는 분자가 조각난다. 그 사실이 출력에
#    그대로 찍힌다 — 우리 박스에서 물 분자가 17.01 / 1.01 로 쪼개지는 것을 봤다.
#    ⇒ "에너지가 다르다"가 아니라 **왜 다른지**를 회신에 싣는다.
FRAG_RE = re.compile(r"# atoms in fragment 1/2:\s+(\d+)\s+(\d+)")
NBOND_RE = re.compile(r"#bonds\s*:\s*(\d+)")
NMOL_RE = re.compile(r"#nmol\s*:\s*(\d+)")


def read_coord(path):
    lines = open(path).read().splitlines()
    lat = float(lines[lines.index("$lattice bohr") + 1].split()[0])
    return lines, lat


def shifted(lines, lat, frac):
    """모든 원자를 frac*a 만큼 옮기고 셀 안으로 **랩** 한다.

    ⚠ 랩 없이도 같은 결과가 나오는지 우리 박스에서 확인했다(xtb 가 내부에서 랩한다).
      그래서 이 차이는 우리 쪽 랩 버그가 아니다.
    """
    out = []
    for line in lines:
        p = line.split()
        if len(p) == 4 and p[3].isalpha():
            c = [(float(v) + frac * lat) % lat for v in p[:3]]
            out.append("%20.12f%20.12f%20.12f  %s" % (c[0], c[1], c[2], p[3]))
        else:
            out.append(line)
    return "\n".join(out) + "\n"


def energy(xtb, path, cwd):
    proc = subprocess.run([xtb, os.path.basename(path), "--gfnff", "--sp"],
                          cwd=cwd, capture_output=True, text=True, timeout=1800)
    m = E_RE.search(proc.stdout)
    nb = NBOND_RE.search(proc.stdout)
    nm = NMOL_RE.search(proc.stdout)
    fr = FRAG_RE.search(proc.stdout)
    # 🔴 xtb 6.7.1 은 주기계 GFN-FF 단일점에서 에너지를 정상 생성하고도
    #    `gfnff_setup: Could not read topology file` 경고를 내며 **normal termination
    #    배너를 찍지 않는다.** 그 배너만 보고 실패로 판정하면 멀쩡한 결과를 버린다.
    #    ⇒ 배너는 배너대로 기록하되, 성공 판정은 **에너지 생성 + abnormal 없음**으로 한다.
    text = proc.stdout
    return {
        "energy_hartree": float(m.group(1)) if m else None,
        "normal_termination_banner": "normal termination" in text,
        "abnormal_termination": "abnormal termination" in text,
        "topology_file_warning": "Could not read topology file" in text,
        "run_ok": (m is not None) and ("abnormal termination" not in text),
        # 🔴 토폴로지 지표. 같은 배치인데 결합 수가 달라지면 그게 원인이다.
        "n_bonds": int(nb.group(1)) if nb else None,
        "n_molecules_detected": int(nm.group(1)) if nm else None,
        "fragment_split": ([int(fr.group(1)), int(fr.group(2))] if fr else None),
        "excerpt": proc.stdout[-800:],
    }


def main():
    d = sys.argv[1]
    w = os.path.join(d, "v1")
    cfg = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "p2g.json")))["v1_translation_invariance"]
    xtb = os.environ["SEI_XTB"]
    lines, lat = read_coord(os.path.join(w, "coord"))

    rows, ref, ref_bonds = [], None, None
    for frac in cfg["shift_fractions"]:
        # 🔴 각 이동을 **독립 디렉터리**에서 돌린다. xtb 는 GFN-FF 토폴로지를
        #    `gfnff_topo` 에 캐시해 다음 실행에서 재사용하는데, 같은 디렉터리에서
        #    돌리면 2회차부터 **1회차의 토폴로지**를 쓴다 — 우리가 재려던 것(위치에
        #    따라 토폴로지가 어떻게 달라지는가)이 통째로 가려진다.
        #    (실제로 처음엔 그렇게 돌려서 `#bonds` 가 1회차에만 찍혔다.)
        name = "shift_%03d" % int(round(frac * 100))
        sub = os.path.join(w, name)
        os.makedirs(sub, exist_ok=True)
        with open(os.path.join(sub, "coord"), "w") as fh:
            fh.write(shifted(lines, lat, frac))
        r = energy(xtb, os.path.join(sub, "coord"), sub)
        e = r["energy_hartree"]
        if ref is None and e is not None:
            ref = e
        if ref_bonds is None:
            ref_bonds = r["n_bonds"]
        rows.append({
            "shift_fraction_of_cell": frac,
            "energy_hartree": e,
            "delta_hartree": (None if (e is None or ref is None) else e - ref),
            "delta_ev": (None if (e is None or ref is None)
                         else units.hartree_to_ev(e - ref)),
            "run_ok": r["run_ok"],
            "normal_termination_banner": r["normal_termination_banner"],
            "topology_file_warning": r["topology_file_warning"],
            "n_bonds": r["n_bonds"],
            "n_molecules_detected": r["n_molecules_detected"],
            "bonds_differ_from_reference": (
                None if (r["n_bonds"] is None or ref_bonds is None)
                else r["n_bonds"] != ref_bonds),
            "excerpt": "" if r["run_ok"] else r["excerpt"],
        })

    # 🔴 원자당으로 본다. 총량 기준은 큰 상자를 자동으로 실패시킨다.
    n_atoms = sum(1 for l in lines
                  if len(l.split()) == 4 and l.split()[3].isalpha())
    tol_pa = float(cfg["tolerance_hartree_per_atom"])
    deltas = [abs(r["delta_hartree"]) for r in rows
              if r["delta_hartree"] is not None]
    max_pa = (max(deltas) / n_atoms) if (deltas and n_atoms) else None
    invariant = max_pa is not None and max_pa <= tol_pa
    out = {
        "test": "V1 translation invariance (GFN-FF, PBC)",
        "issue": "grimme-lab/xtb #1118 (v6.7.1, 미해결)",
        "xtb_version_file": "xtb_version.txt",
        "v1_translation_invariant": invariant,
        "max_abs_deviation_hartree": (max(deltas) if deltas else None),
        "max_abs_deviation_ev": (units.hartree_to_ev(max(deltas))
                                 if deltas else None),
        "max_abs_deviation_hartree_per_atom": max_pa,
        "n_atoms": n_atoms,
        "tolerance_hartree_per_atom": tol_pa,
        "rows": rows,
        # 🔴 기전까지 낸다. "에너지가 다르다"만으로는 proposer 가 판단할 수 없다.
        "topology_changes_with_position": any(
            r.get("bonds_differ_from_reference") for r in rows),
        "n_bonds_by_shift": dict((str(r["shift_fraction_of_cell"]), r["n_bonds"])
                                 for r in rows),
        "_what_this_means": ("불변이 아니면 같은 물리 배치가 셀 안 위치에 따라 다른 "
                             "에너지를 준다는 뜻이다. 기전은 **결합 수가 함께 바뀌는지**로 "
                             "드러난다: GFN-FF 는 좌표를 셀 안으로 랩한 **뒤** 공유결합 "
                             "토폴로지를 만드는데, 그 과정에 최소상 규약이 없으면 셀 경계를 "
                             "가로지르는 분자가 조각난다(우리 박스에서 물 분자가 "
                             "17.01/1.01 amu 로 쪼개지는 것을 직접 봤다)."),
        "all_runs_ok": all(r["run_ok"] for r in rows),
        "_termination_note": ("xtb 6.7.1 은 주기계 GFN-FF 단일점에서 에너지를 정상 "
                              "생성하고도 `gfnff_setup: Could not read topology file` "
                              "경고와 함께 normal-termination 배너를 찍지 않는다. "
                              "배너만 보고 실패로 판정하면 멀쩡한 결과를 버린다 — "
                              "그래서 성공 판정은 '에너지 생성 + abnormal 없음'이다."),
        "_isolation": ("각 이동은 독립 디렉터리에서 돌렸다 — xtb 의 `gfnff_topo` "
                       "캐시가 앞 실행의 토폴로지를 재사용하는 것을 막기 위해서다."),
        "_cache_pitfall": ("🔴 각 이동은 독립 디렉터리에서 돌렸다. 같은 디렉터리에서 "
                           "연속 실행하면 xtb 가 `gfnff_topo` 를 재사용해 **591 eV 짜리 "
                           "가짜 편차**가 나온다 — 우리가 실제로 그 함정에 한 번 빠졌다. "
                           "이 시험을 고칠 때 격리를 없애지 마라."),
        "_scope_limit": ("🔴 이건 **단일점 설정**의 불변성이다. MD 중 drift 와 같은 "
                         "현상인지는 이 시험만으로 단정할 수 없다 — 그건 V2 의 몫이다. "
                         "판정은 proposer 몫이다."),
    }
    with open(os.path.join(d, "v1_result.json"), "w") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    print("[P2g] V1 invariant=%s  max|Δ|=%s Eh"
          % (invariant, out["max_abs_deviation_hartree"]))


if __name__ == "__main__":
    main()
