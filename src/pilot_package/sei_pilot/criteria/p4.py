"""P4 판정 — GPU4PySCF 단일점 + gradient (P1과 동일 계).

§R2-6 판정 기준: CPU 기준값과 에너지 차 < 1e-5 Ha.
회신: H100 1장 : 1 node 속도비, 메모리 상한 원자 수.

우선순위: **P0급 최우선** (§R2-6 우선순위 변경, §R2-7).
Q1(GPU 직접 접근)이 yes면 유효 봉투가 ~2배가 되고 임계 경로가 2~3주 짧아진다.

단위 주의: 에너지는 **Hartree**로 비교한다. eV로 바꿔 비교하지 마라
(1e-5 Ha = 0.27 meV. eV 기준으로 옮기면 임계값을 273배 틀리기 쉽다).
"""

ENERGY_TOL_HARTREE = 1e-5

#: 🔴 ADR-030 가정 A10 — 개발 박스(RTX 4070 SUPER)에서 나온 값은 **측정이 아니라 스모크**다.
#: 속도는 A10으로 거칠게 환산할 수 있으나 **메모리 상한은 환산 불가**다
#: (12.9 GB vs 80 GB는 속도가 아니라 **용량**이며, 상한은 비선형으로 커진다).
TARGET_GPU_HINTS = ("H100", "A100", "H200", "GH200")
SMOKE_GPU_HINTS = ("RTX", "GeForce", "Quadro", "TITAN", "MX")


def gpu_class(gpu_model):
    """회신 값이 '측정'인지 '스모크'인지 판정한다. 모르면 unknown — 추측하지 않는다."""
    if not gpu_model:
        return "unknown"
    name = str(gpu_model)
    if any(h.lower() in name.lower() for h in TARGET_GPU_HINTS):
        return "target"
    if any(h.lower() in name.lower() for h in SMOKE_GPU_HINTS):
        return "smoke"
    return "unknown"


def energy_agreement(e_gpu_hartree, e_cpu_hartree, tol=ENERGY_TOL_HARTREE):
    if e_gpu_hartree is None or e_cpu_hartree is None:
        return {"delta_hartree": None, "within_tol": False,
                "reason": "missing_reference_or_gpu_energy"}
    d = float(e_gpu_hartree) - float(e_cpu_hartree)
    return {"delta_hartree": d, "abs_delta_hartree": abs(d),
            "tol_hartree": tol, "within_tol": abs(d) <= tol}


def gradient_agreement(g_gpu, g_cpu, tol_hartree_per_bohr=1e-4):
    """gradient 최대 성분 차. 에너지만 맞고 gradient가 틀리는 경우가 실제로 있다."""
    if not g_gpu or not g_cpu or len(g_gpu) != len(g_cpu):
        return {"max_abs_diff": None, "within_tol": None,
                "reason": "gradient_missing_or_shape_mismatch"}
    diffs = [abs(float(a) - float(b)) for a, b in zip(g_gpu, g_cpu)]
    mx = max(diffs) if diffs else None
    return {"max_abs_diff_hartree_per_bohr": mx,
            "tol_hartree_per_bohr": tol_hartree_per_bohr,
            "within_tol": (mx is not None and mx <= tol_hartree_per_bohr)}


def speed_ratio(gpu_wall_s, cpu_wall_s, cpu_cores, cpu_model=None,
                reference="gpu_host_cpu"):
    """GPU 1장 : CPU 속도비.

    🔴 **분모가 무엇인지가 이 숫자의 전부다.**
    CPU 클러스터와 GPU 머신이 물리적으로 분리돼 있어(사용자 환경) 기준 계산을
    **같은 GPU 머신의 CPU**로 돌린다. 따라서 이 비는 "GPU 1장 : **이 머신의** CPU"이며
    **"GPU 1장 : HPC 노드"가 아니다.** 그 환산은 CPU 패키지가 잰 HPC 노드 사양으로
    사후에 해야 하고, 그러라고 여기에 분모의 정체를 전부 적어 둔다.
    """
    if not gpu_wall_s or not cpu_wall_s:
        return {"ratio_gpu_per_cpu_reference": None, "reason": "missing_timing",
                "cpu_reference": {"machine": reference, "cores_used": cpu_cores,
                                  "cpu_model": cpu_model}}
    ratio = round(float(cpu_wall_s) / float(gpu_wall_s), 2)
    return {
        "gpu_wall_s": round(float(gpu_wall_s), 2),
        "cpu_reference_wall_s": round(float(cpu_wall_s), 2),
        "ratio_gpu_per_cpu_reference": ratio,
        # 하위호환: 기존 키도 남기되 의미가 바뀌었음을 이름 옆 caveat으로 알린다
        "ratio_gpu_per_node": ratio,
        "cpu_reference": {
            "machine": reference,
            "cores_used": cpu_cores,
            "cpu_model": cpu_model,
            "caveat": "🔴 이 속도비의 분모는 **GPU 머신에 달린 CPU**이지 "
                      "HPC 클러스터 노드의 CPU가 아니다. 두 머신이 분리돼 있어 "
                      "동일 조건 비교가 이 방법뿐이다.",
        },
        "hpc_normalization": {
            "required": True,
            "how": "CPU 패키지 회신의 cluster.cpu(모델·물리코어수)와 위 cpu_reference를 "
                   "비교해 환산하라. 두 CPU의 코어당 성능이 다르면 이 비를 그대로 "
                   "HPC 대비 비로 쓰면 안 된다.",
            "inputs_available_here": {"cpu_model": cpu_model,
                                      "cores_used": cpu_cores},
        },
        "note": "engineer의 §R2-7 가정은 8배(보수적). 실측치가 이보다 크면 "
                "봉투 재계산 이득이 그만큼 커진다 — 단 위 환산을 거친 뒤에 비교하라. "
                "대상 기종이 아니면 ADR-030 가정 A10(H100 ≈ 2 x RTX 4070 SUPER)로 "
                "거칠게만 환산하고 [SMOKE] 로 표기하라.",
    }


def evaluate_p4(e_gpu_hartree, e_cpu_hartree, gpu_wall_s, cpu_wall_s, cpu_cores,
                max_atoms_ok=None, oom_at_atoms=None, gpu_model=None,
                gpu_hours=None, grad_gpu=None, grad_cpu=None, cpu_model=None,
                gpu_memory_total=None):
    ea = energy_agreement(e_gpu_hartree, e_cpu_hartree)
    ga = gradient_agreement(grad_gpu, grad_cpu)
    sr = speed_ratio(gpu_wall_s, cpu_wall_s, cpu_cores, cpu_model)
    klass = gpu_class(gpu_model)
    reasons = []
    if not ea["within_tol"]:
        reasons.append("energy_mismatch(delta=%s Ha, tol=%g)"
                       % (ea.get("delta_hartree"), ENERGY_TOL_HARTREE))
    if sr.get("ratio_gpu_per_cpu_reference") is None:
        reasons.append("speed_ratio_not_measured")
    passed = bool(ea["within_tol"])
    return {
        "id": "P4",
        "status": "pass" if passed else "fail",
        "gpu_hours_total": gpu_hours,
        "criteria": {
            "energy_delta_hartree": ea.get("delta_hartree"),
            "energy_tol_hartree": ENERGY_TOL_HARTREE,
            "energy_within_tol": ea["within_tol"],
            "gradient_within_tol": ga.get("within_tol"),
        },
        "measurement_class": klass,
        "measurement_label": {
            "target": "[MEASURED — target GPU]",
            "smoke": "[SMOKE — not H100]",
            "unknown": "[UNVERIFIED GPU — 모델명을 확인하라]",
        }[klass],
        "measurements": {
            "speed_ratio": sr,
            "gpu_model": gpu_model,
            "gpu_memory_total": gpu_memory_total,
            # 🔴 ADR-030 A10: 메모리 상한은 **환산 불가**다. 대상 GPU가 아니면 비워 둔다.
            "max_atoms_completed": max_atoms_ok if klass == "target" else None,
            "oom_at_atoms": oom_at_atoms if klass == "target" else None,
            "max_atoms_on_this_gpu": max_atoms_ok,
            "oom_at_atoms_on_this_gpu": oom_at_atoms,
            "memory_ceiling_transferable": klass == "target",
            "memory_ceiling_note":
                ("이 GPU가 대상 기종이므로 메모리 상한을 그대로 쓴다."
                 if klass == "target" else
                 "🔴 이 값은 **이 GPU(%s, %s)에서만** 유효하다. 대상 기종(H100 80 GB)으로 "
                 "환산하지 마라 — 속도와 달리 용량은 A10 같은 비율로 옮길 수 없다. "
                 "실제 GPU 머신에서 다시 재기 전까지 상한은 미측정이다."
                 % (gpu_model, gpu_memory_total)),
            "gradient": ga,
        },
        "fail_reasons": reasons,
    }
