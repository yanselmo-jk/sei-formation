#!/bin/bash
# P4 — GPU4PySCF 단일점 + gradient vs **같은 머신의 CPU**. §R2-6에서 최우선(P0급).
#   판정: 에너지 차 < 1e-5 Hartree.  회신: GPU:CPU 속도비, 메모리 상한 원자 수.
#
# 🔴 이름 사전검증이 먼저다 (lead가 실행으로 잡은 BLOCKER):
#    `wb97x-d3` 는 pyscf에 없는 범함수인데 문자열로는 그럴듯해 정적 검토를 통과했고,
#    SCF를 시작하고 나서야 NotImplementedError 로 터졌다. 이제 **계산 전에** 막는다.
set -u
D="${SEI_JOB_DIR}"

# nvidia-smi 가 PATH에 없을 수 있다. 경로는 config/env_paths.json 단일 출처.
source "${SEI_PKG_ROOT}/payload/env_common.sh"
sei_apply_extra_path

PYTHONPATH="${SEI_PKG_ROOT}${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$D" "${SEI_PKG_ROOT}" <<'PY' > "$D/p4.log" 2>&1
import json, os, subprocess, sys, time
sys.path.insert(0, sys.argv[2])
from sei_pilot import qcnames

d, root = sys.argv[1], sys.argv[2]

# 🔴 레벨 선택 근거를 결과에 그대로 싣는다.
#    범함수: ADR-029 생산 레벨(wB97X-V)과 **일치**시킨다 — P4의 목적이
#            "생산 레벨 계산이 GPU에서 얼마나 빠른가" 이기 때문이다.
#    기저:   생산은 def2-TZVPPD 지만 P4는 def2-TZVP 로 잰다. diffuse 함수가
#            12~80 GB GPU에서 **메모리 상한 측정을 왜곡**하기 때문(lead 지시).
XC, BASIS = "wb97x-v", "def2-tzvp"
CHARGE, SPIN = 0, 1                 # spin = 2S = 1 (doublet 환원 라디칼)

out = {
    "software": {},
    "gpu_model": None,
    "level": {
        "xc": XC, "basis": BASIS,
        "production_basis": "def2-TZVPPD",
        "note": "🔴 P4는 def2-TZVP로 쟀고 생산 레벨은 def2-TZVPPD다. diffuse 함수는 "
                "GPU 메모리 상한 측정을 왜곡하므로 제외했다. 속도비를 생산 레벨로 "
                "환산할 때 이 차이를 반드시 반영하라(기저 함수 수가 다르다).",
        "xc_matches_production": True,
        "production_xc_source": "ADR-029",
    },
}


def gpu_name():
    """🔴 GPU 모델명은 반드시 채운다 — 어떤 GPU에서 잰 수치인지 모르면 속도비가 무의미하다.
    (lead 관측: 이전 실행에서 null 로 나왔다. nvidia-smi가 PATH에 없는 환경이 있다.)"""
    from sei_pilot import envpaths
    cands = ["nvidia-smi"] + [os.path.join(d, "nvidia-smi")
                              for d in envpaths.extra_search_paths()]
    for exe in cands:
        try:
            txt = subprocess.check_output(
                [exe, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                universal_newlines=True, stderr=subprocess.STDOUT).strip()
            if txt:
                first = txt.splitlines()[0]
                out["gpu_memory_total"] = first.split(",")[-1].strip()
                out["gpu_count"] = len(txt.splitlines())
                return first.split(",")[0].strip()
        except Exception:
            continue
    try:
        import cupy
        props = cupy.cuda.runtime.getDeviceProperties(0)
        name = props["name"]
        return name.decode() if isinstance(name, bytes) else str(name)
    except Exception:
        return None


out["gpu_model"] = gpu_name()

# --- 0) 🔴 이름 사전검증. 실패하면 여기서 끝낸다(SCF를 시작하지 않는다) ---
try:
    out["name_preflight"] = qcnames.preflight_pyscf(XC, BASIS,
                                                    elements=("C", "H", "O", "Li"))
except qcnames.NameError_ as exc:
    out["name_preflight_error"] = str(exc)
    out["fatal"] = ("범함수/기저 이름 검증 실패 — 본계산을 시작하지 않았다. "
                    "위 후보 중 하나로 payload/P4.sh 의 XC/BASIS 를 고쳐라.")
    json.dump(out, open(os.path.join(d, "p4_result.json"), "w"),
              ensure_ascii=False, indent=1)
    print(str(exc))
    sys.exit(5)
except Exception as exc:
    out["name_preflight"] = {"error": "%s: %s" % (type(exc).__name__, exc)}


def load_xyz(path):
    lines = open(path).read().splitlines()
    n = int(lines[0].split()[0])
    return "\n".join(lines[2:2 + n])


geom = load_xyz(os.path.join(root, "inputs", "li_ec_radical_reactant.xyz"))

# --- 1) CPU 기준값 (🔴 **이 GPU 머신의 CPU**. HPC 노드가 아니다) ---
try:
    import pyscf
    from pyscf import dft, gto
    out["software"]["pyscf"] = pyscf.__version__
    mol = gto.M(atom=geom, basis=BASIS, charge=CHARGE, spin=SPIN, verbose=0)
    out["n_basis_functions"] = int(mol.nao)
    t0 = time.time()
    mf = dft.UKS(mol)
    mf.xc = XC
    e_cpu = mf.kernel()
    g_cpu = mf.nuc_grad_method().kernel()
    out["cpu_wall_s"] = time.time() - t0
    out["e_cpu_hartree"] = float(e_cpu)
    out["grad_cpu"] = [float(x) for x in g_cpu.ravel()]
    out["cpu_cores"] = int(os.environ.get("SEI_TOTAL_CORES", 1))
    out["cpu_reference_machine"] = "gpu_host"
    try:
        for line in open("/proc/cpuinfo"):
            if line.lower().startswith("model name"):
                out["cpu_model"] = line.split(":", 1)[1].strip()
                break
    except OSError:
        pass
except Exception as exc:                     # 실패는 데이터다
    out["cpu_error"] = "%s: %s" % (type(exc).__name__, exc)

# --- 2) GPU ---
try:
    import gpu4pyscf
    from gpu4pyscf import dft as gdft
    from pyscf import gto as ggto
    out["software"]["gpu4pyscf"] = getattr(gpu4pyscf, "__version__", "unknown")
    mol = ggto.M(atom=geom, basis=BASIS, charge=CHARGE, spin=SPIN, verbose=0)
    t0 = time.time()
    mf = gdft.UKS(mol)
    mf.xc = XC
    e_gpu = mf.kernel()
    g_gpu = mf.nuc_grad_method().kernel()
    out["gpu_wall_s"] = time.time() - t0
    out["e_gpu_hartree"] = float(e_gpu)
    arr = g_gpu.get() if hasattr(g_gpu, "get") else g_gpu
    out["grad_gpu"] = [float(x) for x in arr.ravel()]
    out["gpu_hours"] = out["gpu_wall_s"] / 3600.0
except Exception as exc:
    out["gpu_error"] = "%s: %s" % (type(exc).__name__, exc)
    # 🔴 사용자가 복사해서 붙이면 끝나야 한다(lead 실측: 라이브러리를 하나씩 쫓게 된다).
    #    단 "인터넷 없는 노드가 기본 가정"은 유지된다 — 실패해도 위 gpu_error 가
    #    "이 머신에서 GPU-DFT 불가"라는 **측정 결과**로 남는다.
    # 🔴 "고칠 수 있는 환경 문제"가 "이 머신은 GPU-DFT 불가"라는 **능력 측정값으로
    #    둔갑하는 것**을 막는다(lead: false negative). 두 경우는 결론이 정반대다.
    msg = str(exc)
    fixable = any(k in msg for k in ("libnvJitLink", "libcusolver", "libcublas",
                                     "libcusparse", "libcufft", "libcurand",
                                     "libcudart", "libnvrtc",
                                     "cannot open shared object file"))
    out["gpu_failure_class"] = ("likely_fixable_environment" if fixable
                                else ("module_not_installed"
                                      if isinstance(exc, ImportError) else "other"))
    out["gpu_fix_hint"] = {
        "symptom": "gpu4pyscf import 실패 (libnvJitLink.so / libcusolver.so 등)",
        "pip": ("pip install nvidia-nvjitlink-cu12 nvidia-cusolver-cu12 "
                "nvidia-cublas-cu12 nvidia-cusparse-cu12 nvidia-cufft-cu12 "
                "nvidia-curand-cu12 nvidia-cuda-runtime-cu12 nvidia-cuda-nvrtc-cu12"),
        "why": "이 오류는 라이브러리를 **하나씩** 알려주기 때문에 여러 번 시도하다 "
               "포기하기 쉽다. 위 패키지를 한 번에 설치하면 대개 끝난다.",
        "note": "🔴 설치가 정말 불가능한 환경이면 그대로 두어도 된다 — 그때는 "
                "'이 머신에서 GPU-DFT 불가'가 **진짜 답**이다. 다만 위 설치로 풀리는 "
                "경우와 구분되어야 하므로 gpu_failure_class 를 함께 보라.",
        "ld_library_path": "불필요하다. 경로 문제가 아니라 패키지 부재다(실측 확인).",
    }
    print("\n[P4] gpu4pyscf 를 쓸 수 없다 (분류: %s)." % out["gpu_failure_class"])
    if fixable:
        print("  ↳ 고칠 수 있는 환경 문제로 보인다. 이걸 실행해 보라:")
        print("    " + out["gpu_fix_hint"]["pip"])
        print("  ↳ 그래도 안 되면 그대로 두어도 된다 — 그 자체가 답이다.")

# --- 3) 메모리 상한 원자 수 ---
# 🔴 시간 가드: 계를 키우며 스캔하므로 큰 GPU에서는 이 단계가 끝없이 길어질 수 있다.
#    P4의 GPU-h 예산(1 h)을 넘기지 않도록 스캔 자체에 벽시계 상한을 둔다.
MEMSCAN_BUDGET_S = float(os.environ.get("SEI_P4_MEMSCAN_BUDGET_S", 1200))
if "e_gpu_hartree" in out:
    try:
        from gpu4pyscf import dft as gdft
        from pyscf import gto as ggto
        base = [l for l in geom.splitlines() if l.strip()]
        ok, oom = len(base), None
        scan_t0 = time.time()
        for rep in (2, 3, 4, 6):
            if time.time() - scan_t0 > MEMSCAN_BUDGET_S:
                out["memscan_stopped"] = (
                    "시간 예산 %.0f s 초과로 스캔을 중단했다. max_atoms_ok 는 "
                    "**하한**이며 실제 상한은 더 클 수 있다." % MEMSCAN_BUDGET_S)
                break
            atoms = []
            for k in range(rep):
                for l in base:
                    f = l.split()
                    atoms.append("%s %s %s %.4f" % (f[0], f[1], f[2],
                                                    float(f[3]) + 12.0 * k))
            try:
                mol = ggto.M(atom="\n".join(atoms), basis=BASIS, charge=0,
                             spin=rep % 2, verbose=0)
                mf = gdft.UKS(mol)
                mf.xc = XC
                mf.max_cycle = 3
                mf.kernel()
                ok = len(atoms)
            except Exception as exc:
                oom = len(atoms)
                out["oom_error"] = "%s: %s" % (type(exc).__name__, str(exc)[:200])
                break
        out["max_atoms_ok"] = ok
        out["oom_at_atoms"] = oom
    except Exception as exc:
        out["memscan_error"] = "%s: %s" % (type(exc).__name__, exc)

json.dump(out, open(os.path.join(d, "p4_result.json"), "w"),
          ensure_ascii=False, indent=1)
print(json.dumps({k: v for k, v in out.items() if not k.startswith("grad")},
                 ensure_ascii=False, indent=1))
PY
rc=$?
[ -f "$D/p4_result.json" ] || \
  echo '{"gpu_error":"python3 실행 자체가 실패했다 (p4.log 참조)"}' > "$D/p4_result.json"
exit $rc
