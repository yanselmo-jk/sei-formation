"""자원 하드가드.

🔴 이 패키지는 **남의 클러스터**에서 돈다. 폭주하면 우리가 아니라 사용자가 다친다.
따라서 제출 전에 예약(reservation) 원장을 만들고, 총합이 상한을 넘으면
**우선순위가 낮은 항목부터 제출 자체를 하지 않는다.**

가드 값은 이 파일 한 곳에만 있다. 다른 곳에 하드코딩 금지.

가드 이력 (숫자를 바꾸려면 근거가 있어야 한다):
  * §R2-6 D-7 원안       : 2,000 core-h
  * §11.5 개정 (engineer): **4,000 core-h** — P1b(+400)와 P2 환원상태 3 ps 증량(+800)을
    승인해 패키지 총량이 3,150 core-h가 됐기 때문. 전용 봉투 5.8 M의 0.05%.
  * lead 승인 (2026-08-17): 4,000 채택. **가드 자체는 유지** — 남의 클러스터에서
    폭주하는 사고를 막는 것이 목적이며, 그 목적은 4,000에서도 그대로 달성된다.
  * wall 24 h 는 변경 없음 (ADR-004) — 단 이것은 실측 이전의 **가정**이었다.
  * [ADR-114, 2026-08-21, 사용자 직접 지시] wall 상한 **24 h -> 48 h**. ADR-052(사용자
    직접 확인, `normal` 큐 = 48 h)가 이미 실측을 냈고 `plan.EXPECTED_QUEUE_WALL_H`는
    그때 맞춰졌으나 이 파일의 `DEFAULT_MAX_WALL_H`는 갱신되지 않았다 — 같은 사실을
    두 곳에 적었는데 한쪽만 갱신된 사례. `PROFILE_GUARDS["cpu"]`는 §R24.1(KNL 재산정)
    때 이미 48h로 바뀌어 있었으므로 실제 CPU 계획 경로는 영향 없다. GPU 프로파일(24h,
    별도 물리 머신, 스케줄러 큐 없음)과 U56_ENDPOINT_21ATOM_WALL_H(engineer7 가격
    결정, 우연히 같은 24라는 숫자일 뿐)는 이 지시의 대상이 아니다 — 손대지 않았다.

2,000이었다면 P1(단가 스프레드 8배를 줄이는 유일한 수단)이 예산에 들어가지 못했다.
그 계산은 tests/test_plan_report_e2e.py 에 회귀 테스트로 남겨 두었다.
"""

from . import units

DEFAULT_MAX_CORE_HOURS = 5000.0     # cpu 프로파일 기본. P5 추가 반영(아래 PROFILE_GUARDS).
DEFAULT_MAX_WALL_H = 48.0           # [ADR-114, 사용자 직접 지시] 클러스터 wall 상한
                                     # 48 h. ADR-004(24h)의 실측 이전 가정을 대체.
DEFAULT_MAX_GPU_HOURS = 4.0         # P4는 ~1 GPU-h. 4배 여유.

# §R2-6 D-7 원안 값. 회귀 테스트에서 "이 값이면 P1이 잘린다"를 고정하는 데만 쓴다.
ORIGINAL_R2_6_MAX_CORE_HOURS = 2000.0

#: 🔴 프로파일별 가드. CPU 클러스터와 GPU 머신이 물리적으로 분리돼 있어
#: 패키지가 둘이고, 각각의 상한도 다르다.
#:   cpu — P5(330) 추가 후 **예약 총량 3,941 core-h**(128 core/node 기준)로 3,800을
#:         넘었다 ⟹ lead 지시 3에 따라 **5,000으로 상향**. 사용자 문구도 함께 고쳤다.
#:         🔴 "상한 초과 잡은 제출 자체가 안 된다"는 성질은 그대로다.
#:   gpu — GPU-h 4 + wall 48[ADR-114]. core-h는 P4의 **같은 머신 CPU 기준 계산**분만 든다.
PROFILE_GUARDS = {
    # 🔒 §R24.1 — 21,000 은 **[물리 천장]** 이지 소비 전망이 아니다(전망은 16,486).
    #    🔴 종전 5,000 / 24 h 는 `κ=1` 단위였다. §R21 에서 계산 노드가 KNL(Xeon Phi 7250)로
    #    판명돼 κ=3.4~6.8 이 되면서 재산정했다 — **회귀가 아니라 의도된 변화다.**
    #    🔴 wall 48 은 `[LITERATURE — 사이트 문서]` 이므로 실제로는 큐에서 읽는다
    #    (`plan.resolve_wall_limit`). 여기 값은 **우리 자신의 캡**이다.
    # [ADR-114, 2026-08-21, 사용자 직접 지시] gpu 의 wall 도 24 -> 48 로 올린다 — 사용자
    # 지시가 "GPU 머신은 별도 정책"이라는 coder13 의 최초 판단을 명시적으로 뒤집었다.
    "cpu": {"max_core_hours": 21000.0, "max_wall_h": 48.0, "max_gpu_hours": 0.0},
    "gpu": {"max_core_hours": 60.0, "max_wall_h": 48.0, "max_gpu_hours": 4.0},
    # 🔴 B0 — THE USER'S APPROVAL, MADE ENFORCEABLE. See B0_GUARD below for the derivation;
    #    this entry is filled in programmatically so a KNL number can never be typed here
    #    without the reference number it came from.
    "b0": None,
}

# =============================================================================================
# B0 — the user-approved ceiling, expressed in the unit the approval was given in
# =============================================================================================
#
# 🔴🔴 THE UNIT IS THE WHOLE PROBLEM HERE. Read this before changing any number below.
#
#   The approval, the plan and every document figure are in REFERENCE core-h.
#   This ledger (`ResourceGuard`) counts `cores x wall_h` on the MACHINE THE JOB RUNS ON,
#   i.e. KNL core-h. `plan.size_job` computes `reserved = cores x wall x links` and no kappa
#   appears anywhere in `units.py` or `plan.py`.
#
#       kappa == (KNL core-h) / (reference core-h)          R29.1, and BOTH sides are
#                                                            PHYSICAL-core counts
#       15,000 reference core-h  x  2.4  =  36,000 KNL core-h
#
# 🔴 SO THE TWO NUMBERS THAT LOOK LIKE THE ANSWER ARE BOTH WRONG:
#      `max_core_hours = 15000`  would be 15,000 KNL core-h = 6,250 reference core-h, which
#                                 BLOCKS most of B0 (engineer5's range tops out at 14,130 ref).
#      `max_core_hours = 21000`  is RT-1's pilot figure, in KNL core-h = 8,750 reference core-h.
#                                 🔴 It is MORE restrictive than the approval, not less.
#
# 🔒 THIS IS NOT A RAISE (§R24.1). 36,000 > 21,000 numerically and is a SMALLER ceiling in the
#    unit the user approved: RT-1's 21,000 was a PILOT's physical ceiling for a different batch
#    and has no authority over B0. The authority is `B0_APPROVED_REFERENCE_CORE_HOURS`, and the
#    KNL figure is DERIVED from it here rather than typed, so the two can never drift.
#
#: 🔒 THE AUTHORITY. The user approved this figure, in REFERENCE core-h. Do not edit to fit a
#: plan -- §R24.1: "suspect the specification before raising the guard." If B0 does not fit,
#: the plan is wrong and it goes back to the lead and then to the user.
B0_APPROVED_REFERENCE_CORE_HOURS = 15000.0

#: kappa = (KNL core-h)/(reference core-h). R29.1's operative planning value, the SMT-gain=0
#: pessimistic bound of the 1.9-2.4 range. [ESTIMATE, DERIVED from MEASURED kappa_thread=1.207.]
#: 🔴 kappa_thread = 1.207 exists and is the WRONG UNIT for these budgets -- it compares equal
#: THREAD counts over unequal PHYSICAL core counts. Using it here would understate the reservation
#: by a factor of two.
#: 🔒 CLOSED by the user (R36.2): no further compute-speed investigation. 2.4 is permanent.
KAPPA_PHYSICAL = 2.4

#: 🔒 R35.2b, proposer5's explicit number, adopted as written and NOT left to the queue's 48 h.
#: Three arms means three chances per species at an unbounded run, the same shape as
#: li_ec2_cation's 283 core-h. This is the cap that bounds the worst case engineer5 deliberately
#: did NOT price (radical-SCF convergence risk).
B0_TRIPWIRE_WALL_H = 6.0


def reference_to_local_core_hours(reference_core_hours, kappa=KAPPA_PHYSICAL):
    """reference core-h -> KNL core-h. The ONE place this conversion is written."""
    return float(reference_core_hours) * float(kappa)


def local_to_reference_core_hours(local_core_hours, kappa=KAPPA_PHYSICAL):
    """KNL core-h -> reference core-h. For reporting a reservation in the approval's unit."""
    return float(local_core_hours) / float(kappa)


def b0_guard_spec(kappa=KAPPA_PHYSICAL):
    """The B0 profile guard, DERIVED from the approved reference figure. Never typed."""
    return {
        "max_core_hours": reference_to_local_core_hours(
            B0_APPROVED_REFERENCE_CORE_HOURS, kappa),
        "max_wall_h": B0_TRIPWIRE_WALL_H,
        "max_gpu_hours": 0.0,
        "guard_unit": "KNL core-h (cores x wall, the unit this ledger counts)",
        "approved_reference_core_hours": B0_APPROVED_REFERENCE_CORE_HOURS,
        "kappa": kappa,
        "authority": ("user approval of the B0 gate batch, 5,000-15,000 REFERENCE core-h. "
                      "The reference figure is the authority; the KNL figure is derived."),
        "not_a_raise": ("🔴 36,000 KNL core-h > RT-1's 21,000 NUMERICALLY, and is a SMALLER "
                        "ceiling in the approved unit (21,000 KNL = 8,750 reference). RT-1's "
                        "figure was a pilot's physical ceiling for a different batch."),
    }


PROFILE_GUARDS["b0"] = b0_guard_spec()


def guard_for_profile(profile, max_core_hours=None, max_wall_h=None,
                      max_gpu_hours=None):
    """프로파일 기본값 위에 CLI 재정의를 얹는다. 상한의 **존재**는 어떤 경우에도 유지된다."""
    base = dict(PROFILE_GUARDS.get(profile) or PROFILE_GUARDS["cpu"])
    base["profile"] = profile
    if max_core_hours is not None:
        base["max_core_hours"] = float(max_core_hours)
    if max_wall_h is not None:
        base["max_wall_h"] = float(max_wall_h)
    if max_gpu_hours is not None:
        base["max_gpu_hours"] = float(max_gpu_hours)
    # 🔴 A profile may carry PROVENANCE alongside its limits (B0 does: the approved reference
    #    figure, kappa, the unit, and why the derived KNL number is not a raise). Those keys are
    #    not constructor arguments, but they must NOT be dropped -- a ceiling that reaches the
    #    reply without its unit is the defect this provenance exists to prevent (Rule 13:
    #    a judgement-triggering value reaches the artefact, not just the code).
    limits = ("max_core_hours", "max_wall_h", "max_gpu_hours", "profile")
    provenance = dict((k, v) for k, v in base.items() if k not in limits)
    guard = ResourceGuard(**dict((k, v) for k, v in base.items() if k in limits))
    guard.provenance = provenance
    return guard


class BudgetExceeded(Exception):
    pass


class ResourceGuard:
    """core-h / GPU-h / wall 예약 원장.

    reserve()는 성공 시 True, 상한 초과로 거절 시 False를 돌려준다.
    **예외를 던지지 않는 이유**: 예산 초과는 예외가 아니라 정상적인 결과이며,
    거절된 항목은 skip 사유로 회신 JSON에 실려야 하기 때문이다.
    """

    def __init__(self, max_core_hours=DEFAULT_MAX_CORE_HOURS,
                 max_wall_h=DEFAULT_MAX_WALL_H,
                 max_gpu_hours=DEFAULT_MAX_GPU_HOURS, profile=None):
        self.max_core_hours = float(max_core_hours)
        self.max_wall_h = float(max_wall_h)
        self.max_gpu_hours = float(max_gpu_hours)
        self.profile = profile
        #: Where this ceiling came from and IN WHAT UNIT. Empty for the historical profiles,
        #: populated for B0. Travels into the reply with the guard.
        self.provenance = {}
        self.reservations = []      # [{id, core_hours, gpu_hours, wall_h}]
        self.rejected = []          # [{id, core_hours, reason}]
        self.measured = {}          # id -> core_hours (사후 실측)

    # --- 예약 ---
    @property
    def reserved_core_hours(self):
        return sum(r["core_hours"] for r in self.reservations)

    @property
    def reserved_gpu_hours(self):
        return sum(r["gpu_hours"] for r in self.reservations)

    @property
    def remaining_core_hours(self):
        return self.max_core_hours - self.reserved_core_hours

    def reserve(self, item_id, core_hours=0.0, gpu_hours=0.0, wall_h=0.0):
        if wall_h > self.max_wall_h:
            self.rejected.append({
                "id": item_id, "core_hours": core_hours, "gpu_hours": gpu_hours,
                "reason": "wall_guard",
                "detail": "requested wall %.2f h > guard %.2f h "
                          "(잡을 체인 분할하거나 --max-wall-h 로 올려라)"
                          % (wall_h, self.max_wall_h),
            })
            return False
        if self.reserved_core_hours + core_hours > self.max_core_hours + 1e-9:
            self.rejected.append({
                "id": item_id, "core_hours": core_hours, "gpu_hours": gpu_hours,
                "reason": "budget_guard",
                "detail": "core-h %.1f + 기예약 %.1f > 상한 %.1f "
                          "(기본 상한은 %.0f. --max-core-hours 로 조정 가능하나, "
                          "올리기 전에 03_COMPUTE_PLAN §11.5의 총량 산정을 다시 보라)."
                          % (core_hours, self.reserved_core_hours, self.max_core_hours,
                             DEFAULT_MAX_CORE_HOURS),
            })
            return False
        if self.reserved_gpu_hours + gpu_hours > self.max_gpu_hours + 1e-9:
            self.rejected.append({
                "id": item_id, "core_hours": core_hours, "gpu_hours": gpu_hours,
                "reason": "gpu_budget_guard",
                "detail": "GPU-h %.2f + 기예약 %.2f > 상한 %.2f"
                          % (gpu_hours, self.reserved_gpu_hours, self.max_gpu_hours),
            })
            return False
        self.reservations.append({
            "id": item_id, "core_hours": float(core_hours),
            "gpu_hours": float(gpu_hours), "wall_h": float(wall_h),
        })
        return True

    def is_reserved(self, item_id):
        return any(r["id"] == item_id for r in self.reservations)

    def rejection(self, item_id):
        for r in self.rejected:
            if r["id"] == item_id:
                return r
        return None

    # --- 사후 실측 ---
    def record_measured(self, item_id, n_cores, wall_seconds):
        ch = units.core_hours(n_cores, wall_seconds)
        self.measured[item_id] = self.measured.get(item_id, 0.0) + ch
        return ch

    @property
    def measured_core_hours(self):
        return sum(self.measured.values())

    def describe(self):
        """🔴 서술 문자열을 **값에서 파생**시킨다.

        예전에는 `"4,000 core-h / 24 h wall …"` 이 리터럴로 박혀 있었고, 가드가
        프로파일별(cpu 5,000 / gpu 60)로 바뀌자 **같은 JSON 안에서 max_core_hours(정확)와
        guard_source(부정확)가 서로 모순**됐다(critic MAJOR).
        같은 사실을 두 곳에 적으면 반드시 한쪽만 갱신된다 — 그래서 한 곳에서 만든다.
        """
        parts = ["%s 프로파일" % self.profile if self.profile else "기본 가드",
                 "%.0f core-h" % self.max_core_hours,
                 "%.0f h wall/잡" % self.max_wall_h]
        if self.max_gpu_hours:
            parts.append("%.0f GPU-h" % self.max_gpu_hours)
        return ("%s. 근거: 03_COMPUTE_PLAN.md §R2-6 D-7 + §11.5, "
                "ADR-114(wall 상한). 상한을 넘는 잡은 제출 자체가 되지 않는다."
                % " / ".join(parts))

    def to_dict(self):
        return {
            "max_core_hours": self.max_core_hours,
            "max_wall_h": self.max_wall_h,
            "max_gpu_hours": self.max_gpu_hours,
            "profile": self.profile,
            "guard_source": self.describe(),
            "core_hours_reserved": round(self.reserved_core_hours, 2),
            "gpu_hours_reserved": round(self.reserved_gpu_hours, 3),
            "core_hours_measured": round(self.measured_core_hours, 2),
            "reservations": [dict(r) for r in self.reservations],
            "skipped_for_budget": [dict(r) for r in self.rejected],
            "measured_by_item": {k: round(v, 3) for k, v in sorted(self.measured.items())},
        }


def estimate_core_hours(n_cores, wall_h):
    """제출 전 예상치. wall 상한을 다 쓴다고 **보수적으로** 가정한다."""
    return units.core_hours(n_cores, wall_h * units.H_TO_S)
