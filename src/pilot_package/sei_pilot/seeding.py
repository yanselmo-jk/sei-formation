"""독립 시드 기하 섭동 — P5의 `σ_protocol` 측정용.

🔴 왜 기하를 흔드나
------------------
lead 요구: "같은 종을 **독립 시드로 2회** 계산해 프로토콜 자체의 산포(σ_protocol)를
재라." 그런데 Gaussian 의 opt+freq 에는 **난수가 없다.** 같은 입력을 두 번 돌리면
(수치 잡음을 빼면) 같은 답이 나오고, 그건 σ_protocol 이 아니라 σ_machine 이다.

⇒ 독립성은 **시작 기하**에서 와야 한다. 같은 화학종을 서로 다른 시작점에서 최적화해
   나온 결과의 차이가 곧 "프로토콜이 시작점에 얼마나 민감한가"이고, 그게 우리가
   재려던 양이다. 시드는 그 시작점을 재현 가능하게 만든다.

⚠ 이 방식의 한계를 분명히 해 둔다 (회신 JSON에도 실린다):
   - 섭동 진폭이 작으면 같은 극소로 되돌아가 σ 를 **과소평가**한다.
   - 크면 결합이 끊겨 다른 화학종이 되어 σ 를 **과대평가**한다.
   - 즉 여기서 나온 σ_protocol 은 "이 진폭에서의" 값이다. 진폭은 설정값이며
     기본값은 아래 DEFAULT_AMPLITUDE_ANG 한 곳에만 있다.

`random.Random(seed)` 는 stdlib 이고 파이썬 버전 간 재현성이 보장된다
(Mersenne Twister, 3.x 전 구간 동일). numpy 를 쓰지 않는 이유이기도 하다.
"""

import math
import random

# 🔴 [CHOICE — 근거 약함] 결합을 끊지 않으면서 다른 초기 구조가 되도록 고른 값.
#    전형적인 결합 길이(1.0~1.5 Å)의 10 % 미만. 실측 근거는 없다.
#    이 값이 σ_protocol 의 크기를 직접 좌우하므로 회신에 반드시 함께 싣는다.
DEFAULT_AMPLITUDE_ANG = 0.10

# 시드 0 은 "섭동 없음"으로 예약한다 — 원본 기하가 항상 한 쪽 표본이 되게.
UNPERTURBED_SEED = 0


def perturb(atoms, seed, amplitude_ang=DEFAULT_AMPLITUDE_ANG):
    """`atoms` = [(기호, x, y, z), ...] 를 시드에 따라 등방 섭동한다 (단위: Å).

    seed == UNPERTURBED_SEED 이면 원본을 그대로 돌려준다.
    각 원자를 반지름 amplitude_ang 인 구 안에서 균일하게 뽑은 벡터만큼 옮긴다.
    """
    if seed == UNPERTURBED_SEED:
        return [tuple(a) for a in atoms]
    rng = random.Random(seed)
    out = []
    for sym, x, y, z in atoms:
        # 구 내부 균일 표본: 방향은 균일, 반지름은 r = R * u^(1/3)
        theta = math.acos(2.0 * rng.random() - 1.0)
        phi = 2.0 * math.pi * rng.random()
        r = amplitude_ang * (rng.random() ** (1.0 / 3.0))
        out.append((sym,
                    x + r * math.sin(theta) * math.cos(phi),
                    y + r * math.sin(theta) * math.sin(phi),
                    z + r * math.cos(theta)))
    return out


def max_displacement_ang(a, b):
    """두 기하의 원자별 최대 변위(Å). 섭동이 실제로 걸렸는지 확인용."""
    return max((math.sqrt((p[1] - q[1]) ** 2 + (p[2] - q[2]) ** 2 + (p[3] - q[3]) ** 2)
                for p, q in zip(a, b)), default=0.0)


def min_interatomic_distance_ang(atoms):
    """최단 원자간 거리(Å). 섭동이 원자를 겹쳐 놓지 않았는지 확인용."""
    best = float("inf")
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            d = math.sqrt(sum((atoms[i][k] - atoms[j][k]) ** 2 for k in (1, 2, 3)))
            best = min(best, d)
    return best if best < float("inf") else 0.0


def read_xyz(text):
    lines = text.splitlines()
    n = int(lines[0].split()[0])
    out = []
    for line in lines[2:2 + n]:
        f = line.split()
        if f:
            out.append((f[0], float(f[1]), float(f[2]), float(f[3])))
    return out


def write_xyz(atoms, comment=""):
    body = "".join("%-3s %14.8f %14.8f %14.8f\n" % a for a in atoms)
    return "%d\n%s\n%s" % (len(atoms), comment.replace("\n", " "), body)


def provenance(seed, amplitude_ang, original, perturbed):
    """회신 JSON에 그대로 실을 재현 정보. **시드 없는 결과는 폐기 대상이다.**"""
    return {
        "seed": seed,
        "perturbed": seed != UNPERTURBED_SEED,
        "amplitude_ang": amplitude_ang if seed != UNPERTURBED_SEED else 0.0,
        "rng": "python stdlib random.Random(seed), Mersenne Twister",
        "max_displacement_ang": round(max_displacement_ang(original, perturbed), 5),
        "min_interatomic_distance_ang": round(
            min_interatomic_distance_ang(perturbed), 5),
        "caveat": ("σ_protocol 은 이 진폭에서의 값이다. 진폭이 작으면 같은 극소로 "
                   "돌아가 과소평가, 크면 결합이 끊겨 과대평가된다."),
    }
