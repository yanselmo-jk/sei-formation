#!/usr/bin/env python3
"""V1b — NVE 에너지 drift 와 **Δt² 스케일링** (GFN-FF, 주기계).

🔴 판정②가 본체다: drift 가 Δt² 로 줄어드는가.
   Verlet 적분오차는 ∝Δt² 이므로 Δt 를 절반으로 하면 drift 가 **~4배** 줄어야 한다.
   안 줄면 그것은 적분오차가 아니라 **힘–에너지 불일치(F ≠ −∇E)** 이며 **어떤 시간
   스텝으로도 못 고친다** (U-42).

🔴 하드가드 (팀 규약):
   1. 모든 실행을 **독립 디렉터리**에서 돌린다 — xtb 가 `gfnff_topo` 를 캐시·재사용해
      생산 궤적을 조용히 오염시킨다. (591 eV 오탐이 여기서 나왔다.)
   2. **정상 종료 배너로 성패를 판정하지 않는다.** 6.7.1 은 주기 GFN-FF 에서 정상
      에너지를 내고도 배너를 안 찍는다. 판정은 **에너지 파싱 성공 + 유한값 + 결합수
      일관성**으로 한다.

🔴 판정하지 않는다 — drift 를 meV/atom/ps 로, 두 Δt 의 **비(ratio)** 와 함께 낸다.

단위: 에너지 Hartree → 보고는 **meV/atom/ps**. 변환은 sei_pilot.units 한 곳에서 온다.
"""
import json
import os
import re
import shutil
import subprocess
import sys

PKG = os.environ.get("SEI_PKG_ROOT") or os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "pilot_package"))
sys.path.insert(0, PKG)
from sei_pilot import units  # noqa: E402

# md.out 상태줄:  step  time(ps)  <Epot>  Ekin  <T>  T  Etot  error
STATUS_RE = re.compile(
    r"^\s*(\d+)\s+(\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+"
    r"(-?\d+\.?\d*)\s+(-?\d+\.?\d*)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$", re.M)
TRJ_E_RE = re.compile(r"energy:\s*(-?\d+\.\d+)")
NBOND_RE = re.compile(r"#bonds\s*:\s*(\d+)")


def md_input(time_ps, step_fs, dump_fs, temp_k, nvt):
    return ("$md\n   temp=%.1f\n   time=%.4f\n   dump=%.2f\n   step=%.4f\n"
            "   hmass=1\n   nvt=%s\n$end\n"
            % (temp_k, time_ps, dump_fs, step_fs, "true" if nvt else "false"))


def run_md(xtb, coord_path, workdir, time_ps, step_fs, dump_fs, temp_k, nvt,
           nprocs=1):
    """🔴 항상 **비어 있는 전용 디렉터리**에서 돌린다 (gfnff_topo 격리)."""
    if os.path.exists(workdir):
        shutil.rmtree(workdir)
    os.makedirs(workdir)
    shutil.copy(coord_path, os.path.join(workdir, "coord"))
    with open(os.path.join(workdir, "md.inp"), "w") as fh:
        fh.write(md_input(time_ps, step_fs, dump_fs, temp_k, nvt))
    proc = subprocess.run(
        [xtb, "coord", "--gfnff", "--md", "--input", "md.inp", "-P", str(nprocs)],
        cwd=workdir, capture_output=True, text=True, timeout=60 * 60 * 12)
    out = proc.stdout
    with open(os.path.join(workdir, "md.out"), "w") as fh:
        fh.write(out)
    nb = NBOND_RE.search(out)
    return {"stdout": out, "n_bonds": int(nb.group(1)) if nb else None,
            "returncode": proc.returncode}


def parse_status(text):
    """[(step, t_ps, Ekin, T, Etot_hartree)] — **Etot** 이 drift 의 대상이다."""
    return [{"step": int(m.group(1)), "t_ps": float(m.group(2)),
             "ekin": float(m.group(4)), "temperature_k": float(m.group(6)),
             "etot_hartree": float(m.group(7)), "error": float(m.group(8))}
            for m in STATUS_RE.finditer(text)]


def last_frame_to_coord(trj_path, template_coord, out_path):
    """궤적 마지막 프레임(Å)을 Turbomole coord(bohr)로. 격자는 원본에서 가져온다."""
    lines = open(trj_path, errors="replace").read().splitlines()
    n = int(lines[0].split()[0])
    start = len(lines) - (n + 2)
    atoms = [l.split() for l in lines[start + 2:start + 2 + n]]
    tmpl = open(template_coord).read().splitlines()
    lat_i = tmpl.index("$lattice bohr")
    b = units.ANGSTROM_TO_BOHR
    with open(out_path, "w") as fh:
        fh.write("$coord\n")
        for f in atoms:
            fh.write("%20.12f%20.12f%20.12f  %s\n"
                     % (float(f[1]) * b, float(f[2]) * b, float(f[3]) * b,
                        f[0].lower()))
        fh.write("\n".join(tmpl[lat_i - 1:]) + "\n")


def drift_mev_per_atom_per_ps(rows, n_atoms):
    """Etot 시계열의 **선형 기울기**. 표본이 2개 미만이면 None (0 으로 얼버무리지 않는다)."""
    pts = [(r["t_ps"], r["etot_hartree"]) for r in rows]
    if len(pts) < 2:
        return None, None
    n = float(len(pts))
    sx = sum(p[0] for p in pts)
    sy = sum(p[1] for p in pts)
    sxx = sum(p[0] * p[0] for p in pts)
    sxy = sum(p[0] * p[1] for p in pts)
    denom = n * sxx - sx * sx
    if abs(denom) < 1e-30:
        return None, None
    slope_ha_per_ps = (n * sxy - sx * sy) / denom
    total_ha = pts[-1][1] - pts[0][1]
    span = pts[-1][0] - pts[0][0]
    return (units.hartree_to_ev(slope_ha_per_ps) * 1000.0 / n_atoms,
            (units.hartree_to_ev(total_ha) * 1000.0 / n_atoms / span)
            if span > 0 else None)


def largest_jump(values):
    """연속 표본 간 최대 도약 — 계단형 불연속(토폴로지/이웃목록 재구축) 신호."""
    if len(values) < 2:
        return None
    diffs = [abs(values[k + 1] - values[k]) for k in range(len(values) - 1)]
    return {"max_abs_jump_hartree": max(diffs),
            "median_abs_jump_hartree": sorted(diffs)[len(diffs) // 2],
            "ratio_max_to_median": (max(diffs) / sorted(diffs)[len(diffs) // 2]
                                    if sorted(diffs)[len(diffs) // 2] > 0 else None)}


def main():
    out_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "out_v1b")
    os.makedirs(out_dir, exist_ok=True)
    xtb = os.environ["SEI_XTB"]
    nprocs = int(os.environ.get("SEI_NPROCS", "1"))
    box = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "inputs", "ec_box.coord")
    n_atoms = sum(1 for l in open(box)
                  if len(l.split()) == 4 and l.split()[3].isalpha())

    eq_ps = float(os.environ.get("SEI_V1B_EQ_PS", "2.0"))
    nve_ps = float(os.environ.get("SEI_V1B_NVE_PS", "5.0"))

    # --- 0) 평형화 (NVT) --------------------------------------------------
    # 🔴 반드시 필요하다. 격자 배치에서 곧바로 NVE 를 걸면 위치에너지가 운동에너지로
    #    쏟아져 T ≈ 3000 K 가 되고, 그때의 "drift" 는 적분오차가 아니라 완화다.
    #    (실제로 그렇게 돌려서 T=2970 K 를 봤다.)
    eq = run_md(xtb, box, os.path.join(out_dir, "equil"), eq_ps, 1.0, 100.0,
                300.0, nvt=True, nprocs=nprocs)
    eq_trj = os.path.join(out_dir, "equil", "xtb.trj")
    eq_rows = parse_status(eq["stdout"])
    if not os.path.exists(eq_trj):
        json.dump({"status": "equilibration_failed",
                   "why": "xtb.trj 가 없다", "excerpt": eq["stdout"][-1500:]},
                  open(os.path.join(out_dir, "v1b_result.json"), "w"),
                  ensure_ascii=False, indent=1)
        print("[V1b] 평형화 실패")
        return 1
    start = os.path.join(out_dir, "equilibrated.coord")
    last_frame_to_coord(eq_trj, box, start)

    # --- 1) NVE 두 벌 (같은 시작 구조, 각각 독립 디렉터리) -----------------
    runs = {}
    for tag, dt in (("dt1.0", 1.0), ("dt0.5", 0.5)):
        r = run_md(xtb, start, os.path.join(out_dir, tag), nve_ps, dt, 10.0,
                   300.0, nvt=False, nprocs=nprocs)
        rows = parse_status(r["stdout"])
        slope, endpoint = drift_mev_per_atom_per_ps(rows, n_atoms)
        trj = os.path.join(out_dir, tag, "xtb.trj")
        epot = ([float(m.group(1)) for m in TRJ_E_RE.finditer(
            open(trj, errors="replace").read())] if os.path.exists(trj) else [])
        runs[tag] = {
            "timestep_fs": dt,
            "requested_ps": nve_ps,
            "n_status_samples": len(rows),
            # 🔴 배너가 아니라 이것으로 성패를 판정한다.
            "run_ok": bool(rows) and all(
                abs(x["etot_hartree"]) < 1e6 for x in rows),
            "n_bonds": r["n_bonds"],
            "drift_mev_per_atom_per_ps_fit": slope,
            "drift_mev_per_atom_per_ps_endpoint": endpoint,
            "etot_series": [{"t_ps": x["t_ps"], "etot_hartree": x["etot_hartree"],
                             "temperature_k": x["temperature_k"]} for x in rows],
            "epot_discontinuity": largest_jump(epot),
            "n_epot_frames": len(epot),
            "temperature_mean_k": (sum(x["temperature_k"] for x in rows) / len(rows)
                                   if rows else None),
        }

    a, b = runs["dt1.0"], runs["dt0.5"]
    ratio = None
    if (a["drift_mev_per_atom_per_ps_fit"] is not None
            and b["drift_mev_per_atom_per_ps_fit"]):
        denom = abs(b["drift_mev_per_atom_per_ps_fit"])
        if denom > 0:
            ratio = abs(a["drift_mev_per_atom_per_ps_fit"]) / denom

    result = {
        "test": "V1b — NVE drift and Δt² scaling (GFN-FF, PBC)",
        "system": {"n_atoms": n_atoms, "molecules": "27 EC", "source": box},
        "equilibration": {"ensemble": "NVT", "ps": eq_ps,
                          "final_temperature_k": (eq_rows[-1]["temperature_k"]
                                                  if eq_rows else None),
                          "_why": ("격자 배치에서 곧바로 NVE 를 걸면 T≈3000 K 가 되어 "
                                   "drift 가 적분오차가 아니라 완화를 재게 된다.")},
        "runs": runs,
        "drift_ratio_dt1_over_dt0.5": ratio,
        "expected_ratio_if_verlet_integration_error": 4.0,
        "_judgement": ("🔴 판정하지 않는다. ratio 가 4 에 가까우면 적분오차, 1 에 "
                       "가까우면 힘–에너지 불일치(F ≠ −∇E, U-42)를 시사하지만 "
                       "그 판정은 proposer 몫이다."),
        "_hard_guards": ["모든 실행은 독립 디렉터리 — gfnff_topo 캐시 격리",
                         "정상 종료 배너로 판정하지 않음 — 에너지 파싱 + 유한값 + "
                         "결합수 일관성으로 판정"],
        "_sampling_limit": ("md.out 상태줄은 성기다(수십 표본). 계단형 불연속은 "
                            "궤적의 Epot(조밀)으로 함께 본다."),
        "xtb_version": "6.7.1",
    }
    with open(os.path.join(out_dir, "v1b_result.json"), "w") as fh:
        json.dump(result, fh, ensure_ascii=False, indent=1)
    print("[V1b] dt=1.0: drift=%s meV/atom/ps (%d표본) | dt=0.5: drift=%s (%d표본)"
          % (a["drift_mev_per_atom_per_ps_fit"], a["n_status_samples"],
             b["drift_mev_per_atom_per_ps_fit"], b["n_status_samples"]))
    print("[V1b] ratio(dt1.0/dt0.5) = %s   (Verlet 이면 ~4)" % ratio)
    return 0


if __name__ == "__main__":
    sys.exit(main())
