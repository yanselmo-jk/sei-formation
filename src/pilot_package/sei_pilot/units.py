"""단위 변환 — 이 프로젝트의 모든 물리량 변환은 여기 한 곳에서만 정의된다.

규칙 (프로젝트 전역):
  * 변수명에 단위를 박는다: `barrier_eV`, `energy_hartree`, `core_hours`.
  * 변환 상수를 다른 파일에 하드코딩하지 않는다. 반드시 이 모듈을 import 한다.

출처:
  CODATA 2018 (NIST). Hartree energy = 27.211386245988 eV.
  1 cm^-1 = 1.239841984e-4 eV  (= h*c/e * 100)
  1 eV = 96.48533212 kJ/mol = 23.060548 kcal/mol
  1 Bohr = 0.529177210903 Angstrom
"""

# --- 에너지 ---------------------------------------------------------------
HARTREE_TO_EV = 27.211386245988
EV_TO_HARTREE = 1.0 / HARTREE_TO_EV
EV_TO_KJ_PER_MOL = 96.48533212
EV_TO_KCAL_PER_MOL = 23.060547830619026
CM1_TO_EV = 1.239841984e-4
EV_TO_MEV = 1000.0

# --- 원자 질량 (amu) -------------------------------------------------------
#: 🔴 **가장 흔한 동위원소** 질량이다 — G16 의 기본값과 같은 관례(평균 원자량이 아니다).
#: 질량가중 normal mode(Ω, §39.4(c) M2′)에 쓰인다. 평균 원자량을 쓰면 Li 처럼 동위원소가
#: 갈리는 원소에서 √m 이 어긋나 projection 이 조용히 달라진다.
#: ⚠ G16 이 `freq=readisotopes` 등으로 다른 질량을 쓰면 이 표는 그 로그에 맞지 않는다 —
#: 그때는 로그가 찍는 질량을 읽어야 하고, 이 표를 고치는 게 아니다.
ATOMIC_MASS_AMU = {
    "H": 1.00782503207, "D": 2.0141017778, "He": 4.00260325415,
    "Li": 7.01600455, "B": 11.0093054, "C": 12.0, "N": 14.0030740048,
    "O": 15.9949146196, "F": 18.99840322, "Na": 22.9897692809,
    "Mg": 23.985041700, "Al": 26.98153863, "Si": 27.9769265325,
    "P": 30.97376163, "S": 31.97207100, "Cl": 34.96885268,
    "K": 38.96370668, "Ca": 39.96259098, "Fe": 55.9349375,
    "Ni": 57.9353429, "Cu": 62.9295975, "Zn": 63.9291422,
    "Br": 78.9183371, "I": 126.904473,
}

# --- 길이 -----------------------------------------------------------------
BOHR_TO_ANGSTROM = 0.529177210903
ANGSTROM_TO_BOHR = 1.0 / BOHR_TO_ANGSTROM

# --- 시간 -----------------------------------------------------------------
FS_TO_PS = 1e-3
PS_TO_FS = 1e3
S_TO_H = 1.0 / 3600.0
H_TO_S = 3600.0


def hartree_to_ev(e_hartree):
    return e_hartree * HARTREE_TO_EV


def ev_to_hartree(e_ev):
    return e_ev * EV_TO_HARTREE


def ev_to_kcal_per_mol(e_ev):
    return e_ev * EV_TO_KCAL_PER_MOL


def kcal_per_mol_to_ev(e_kcal):
    return e_kcal / EV_TO_KCAL_PER_MOL


def ev_to_kj_per_mol(e_ev):
    return e_ev * EV_TO_KJ_PER_MOL


def kj_per_mol_to_ev(e_kj):
    return e_kj / EV_TO_KJ_PER_MOL


def cm1_to_ev(nu_cm1):
    """진동수(cm^-1) → eV. 허수진동수는 관례상 음수로 들어온다."""
    return nu_cm1 * CM1_TO_EV


def hartree_to_mev(e_hartree):
    return e_hartree * HARTREE_TO_EV * EV_TO_MEV


# --- 계산 자원 -------------------------------------------------------------
def core_hours_h(n_cores, wall_hours):
    """core-hour = 코어 수 × wall(**시간**). 🔴 **core-h 의 유일한 정의.**

    시간 단위판을 따로 두는 이유: 계획 경로(`plan.py`)는 wall 을 **시간**으로 들고
    있는데 초 단위 API 만 있으면 `wall*3600*(1/3600)` 왕복이 생겨 마지막 비트가
    달라진다. 그러면 "계획값 == 실측값" 검사가 부동소수 문제로 흔들린다.
    ⇒ 정의는 여기 하나, 초 단위판이 이것을 호출한다.

    ⚠ `plan.py:size_job()` 과 array 특례가 예전에는 `total_cores * wall * links` 를
    **자기가 계산**했다. 값은 같았지만(critic2 가 소수점까지 대조) `S_TO_H` 나 이 공식이
    바뀌면 그 두 자리는 조용히 안 따라온다 — 우리가 여섯 번 데인 형태가 이미 있던 자리다.
    """
    return float(n_cores) * float(wall_hours)


def core_hours(n_cores, wall_seconds):
    """초 단위 입력판. 정의는 `core_hours_h` 하나뿐이다."""
    return core_hours_h(n_cores, float(wall_seconds) * S_TO_H)


def node_hours(n_nodes, wall_seconds):
    return float(n_nodes) * float(wall_seconds) * S_TO_H


def node_hours_to_core_hours(nh, cores_per_node):
    return float(nh) * float(cores_per_node)


def core_hours_to_node_hours(ch, cores_per_node):
    if not cores_per_node:
        raise ValueError("cores_per_node must be > 0")
    return float(ch) / float(cores_per_node)


# --- AIMD 드리프트 판정용 --------------------------------------------------
def drift_mev_per_atom_per_ps(delta_e_hartree, n_atoms, elapsed_ps):
    """보존량 변화(Hartree) → meV/atom/ps.

    P2 판정 기준(§R2-6): < 1 meV/atom/ps.
    CP2K의 .ener 파일은 a.u.(Hartree) 단위이므로 여기서 변환한다.
    """
    if n_atoms <= 0 or elapsed_ps <= 0:
        raise ValueError("n_atoms and elapsed_ps must be > 0")
    return hartree_to_mev(delta_e_hartree) / (n_atoms * elapsed_ps)
