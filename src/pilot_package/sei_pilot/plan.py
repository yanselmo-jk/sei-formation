"""실행 계획 수립 — 어떤 프로브/파일럿을 어떤 자원으로 돌릴 것인가.

🔴 자원 상한의 강제 방식 (이 파일의 핵심 설계):
    각 항목은 **core-h 예산**을 선언한다. 노드/코어가 정해지면
        wall_h = clamp(budget / total_cores, 항목별 하한, min(24h, 파티션 상한))
    으로 wall을 **역산**하고, 부족하면 afterany 체인 링크 수를 늘린다.
    ⇒ 스케줄러가 wall에서 잡을 죽이므로 **패키지가 소비할 수 있는 core-h의 상한을
       스케줄러가 물리적으로 강제한다.** 파이썬 버그로 폭주하는 경로가 없다.

우선순위는 "core-h당 정보량" 순이다(§R2-6 / §11.5 근거를 각 항목에 적어 둔다).
가드에 걸려 잘린 항목은 조용히 사라지지 않고 skip 사유와 함께 회신 JSON에 남는다.
"""

import json
import math
import os

from . import accounts as accounts_mod
from . import budget as budget_mod
from . import solvent
from . import config
from . import units
from . import envpaths
from . import sysprobe as sysprobe_mod

PKG_ROOT = envpaths.PKG_ROOT

# 컨테이너 우선(§R2-6 D-3). 패키지에 .sif가 동봉돼 있으면 그것을 쓰고,
# 없으면 모듈 → 시스템 바이너리 → skip 순으로 내려간다.
#: 🔴 사용자 클러스터에는 orca/qchem/psi4 가 **없고 gaussian16 이 있다**(lead 확인).
#: 탐지 순서가 곧 우선순위다. g16 을 맨 앞에 둔다.
#: 실제 탐지는 envpaths.resolve_qc 가 `$g16root` 계열 환경변수까지 본다
#: (모듈로만 잡히고 PATH에 없는 경우가 흔하다).
QC_CODES = ("g16", "g09", "orca", "qchem", "psi4")


#: 🔴 사용자 환경은 CPU 클러스터와 GPU 머신이 **물리적으로 분리**돼 있다.
#: 따라서 패키지도 둘로 나뉜다. 코드는 하나이고 **항목 집합만 프로파일로 분기**한다
#: (코드를 복제하면 다음 수정에서 두 벌이 어긋난다).
PROFILE_CPU = "cpu"
PROFILE_GPU = "gpu"
PROFILES = (PROFILE_CPU, PROFILE_GPU)


class Item(object):
    def __init__(self, key, title, priority, core_hours_budget=0.0, nodes=1,
                 gpu_hours=0.0, gpus=0, payload=None, requires=None,
                 array=None, rationale="", depends_on=None, min_wall_h=None,
                 profiles=(PROFILE_CPU,), fallback_hint=None,
                 account_key="probe", cores_per_task=None, task_budgets=None,
                 explicit_wall_h=None, task_cores=None, extra_env=None):
        self.key = key
        self.title = title
        self.priority = priority
        self.core_hours_budget = float(core_hours_budget)
        self.nodes = nodes
        self.gpu_hours = float(gpu_hours)
        self.gpus = gpus
        self.payload = payload or ("payload/%s.sh" % key)
        self.requires = requires or []          # [(kind, [names])]
        self.array = array
        # 🔴 array 태스크당 코어 수. **예전에는 1 이 산식에 하드코딩돼 있었다.**
        #    `probe_throughput`(200 × 1분 × 1코어)에는 옳았지만, §R22 가 P5·P1b 를
        #    array 로 바꾸면서 그 가정을 그대로 물려받았다. 1코어로 두면 P5 최대 종
        #    750 core-h 가 **wall 750 h** 가 되어 48 h 큐에서 즉사한다.
        #    ⟹ 예산·wall·천장·`select=` 가 전부 이 값에서 파생돼야 한다.
        #: `None` = "노드 전체(cores_per_node)". 숫자면 그 값 그대로(probe_throughput = 1).
        self.cores_per_task = None if cores_per_task is None else int(cores_per_task)
        #: 태스크마다 코어 수가 다른 경우(P6: 1/16/64 스레드 스케일링). 있으면 우선한다.
        self.task_cores = list(task_cores) if task_cores else None
        #: 🔒 §R24.1 — 태스크별 예산. 균일 예산 + `min_wall_h` 바닥값으로 편차를 덮으면
        #:  물리 천장이 부풀어 오른다(P5 가 5.77배였다). 편차는 **예산에** 넣는다.
        self.task_budgets = list(task_budgets) if task_budgets else None
        #: budget→wall 역산이 성립하지 않는 항목(P6: 코어 수가 태스크마다 달라 wall 이
        #:  1스레드에서 340 h 가 된다). 이때는 wall 을 명시하고 예약을 cores×wall 로 잡는다.
        self.explicit_wall_h = explicit_wall_h
        self.rationale = rationale
        self.depends_on = depends_on or []
        # 짧은 프로브에 0.25 h 하한을 강제하면 예약이 실제 소비의 10배가 된다.
        self.min_wall_h = min_wall_h
        self.profiles = tuple(profiles)
        # 🔴 도구가 없어 생략될 때 **무엇을 보내면 되는지**를 회신에 남긴다.
        #    "사용 가능한 실행 수단 없음"만 적으면 왕복 1회를 더 써야 알 수 있다.
        self.fallback_hint = fallback_hint
        # 🔴 이 클러스터의 PBS 계정은 **소프트웨어 단위**다(사용자 확인).
        #    여기에는 *어떤 소프트웨어인가*만 적고, 실제 계정 문자열은
        #    config/accounts.json 한 곳에서 온다. 문자열을 항목에 박으면
        #    "같은 진실이 두 곳에" 사고가 또 난다.
        self.account_key = account_key
        #: 이 항목에만 필요한 잡 환경변수 (예: endpoint_prep.sh 의 SEI_ENDPOINT_ROLE).
        #: 🔴 공통 env(build_common_env)에 넣으면 **모든** 잡에 새고, payload 에 하드코딩하면
        #: 항목마다 스크립트를 복제해야 한다 -- 항목이 선언하고 build_spec 이 한 곳에서 합친다.
        self.extra_env = dict(extra_env or {})


# --------------------------------------------------------------------------
# 항목 정의. 예산 출처: 03_COMPUTE_PLAN.md §R2-6 표 + §11.5 재계산.
# --------------------------------------------------------------------------
def _p5_shape():
    """P5 설명에 들어갈 종/실행 횟수를 **manifest 에서 유도**한다.

    🔴 "14종" 을 문자열로 박아 두었더니 dual-seed 로 실행 수가 늘어도 설명은 그대로였다.
       같은 진실이 두 곳(설명 문자열 / manifest)에 있으면 한쪽만 갱신된다 — 이 프로젝트에서
       반복해서 난 실패다. 세는 쪽은 manifest 하나뿐이어야 한다.
    """
    try:
        with open(os.path.join(PKG_ROOT, "inputs", "p5_species",
                               "manifest.json")) as fh:
            species = json.load(fh)["species"]
    except (OSError, ValueError, KeyError):
        return "종 수 불명 — manifest 를 읽지 못했다"
    runs = sum(2 if s.get("dual_seed") else 1 for s in species)
    runs += sum(1 for s in species if s.get("cheap_level_too"))
    dual = sum(1 for s in species if s.get("dual_seed"))
    return ("%d종/%d실행, 크기·전하·스핀 교차, dual-seed %d종"
            % (len(species), runs, dual))


#: 🔒 §R22.9 / §R24.1 예산 확정표. **κ=6.8 비관으로 예약한다.**
#: 🔴 종전 값(P1 1,000 / P1b 700 / P5 430)은 **`κ=1` 단위였다.** 이 변경은 회귀가 아니라
#:    **의도된 재산정**이다 — 사유: "§R21 KNL 판명(κ=3.4~6.8)에 따른 재산정."
P1_TOTAL_CORE_HOURS = 6800.0
# 🔒 §R26.1 / §R27 확정 — 22원자 값 3,094 → 3,072.
#    🔴 이유(내가 코드로 재검산해 보고함): 3,094/64 = **48.34 h** 로 48 h 상한을 2% 넘는다.
#      ⟹ 링크가 2개가 되고 그 태스크의 물리 천장이 6,144(예산의 1.99배)로 튄다.
#      ⟹ P1b 전체 천장 7,810 → 총 천장 24,917 > guard 21,000 ⟹ **P1b 가 조용히 SKIP 된다.**
#      §R24.1 의 "수정 후" 표는 P1b 천장을 4,760(1.00×)으로 적었으나 **도달 불가능한 값**이다
#      (링크 절상을 무시한 값). 같은 문서 "수정 전" 표의 12,288 은 min_wall 48 을 적용한 값이다.
#    🔒 3,072 = 64 × 48 이므로 정확히 1링크가 되고 천장 = 예산 = 1.00× 가 된다. 대가 −0.7%.
#    🟢 engineer 가 §R26.1 에서 손으로 같은 결함을 찾아 같은 값(3,072)에 도달했고,
#      나는 코드를 돌려 도달했다 — **독립 수렴.** §R27 로 확정.
#    🔒 일반 규칙(§R26.1): **array 태스크 예산은 `cores × max_wall_h` 를 넘지 않는다.**
#      넘으면 링크를 늘리지 말고 **태스크를 쪼갠다.** 체이닝은 P1(직렬 의존) 전용이다 —
#      array 를 체이닝하면 천장이 계단식으로 뛴다. 그리고 **경계의 95% 를 넘는 값은 쓰지 마라.**
#: 🔒 [MAJOR #1, lead 판정] 태스크 1-3 = 종별(5/12/22 원자, 비 1:2.5:6.45 — 종전 그대로,
#: 예산 재분배 금지). 태스크 4 = **stagewise 단가비(8회) + U-27 스모크(최대 6회)** —
#: 종별 태스크에서 분리했다: 태스크 3(3,072 = 64×48h)은 wall 여유 0% 라 extras 를 얹으면
#: wall 상한에서 조용히 죽는다(이번 라운드의 실패 모양 그대로). 의존성은 lead 가 확인:
#: stagewise 는 jobs/P1/ts.xyz(depends_on=["P1"] 이 보장), U-27 은 패키지 input — 둘 다
#: 형제 태스크 산출물을 먹지 않으므로 분리해도 순서 사고가 재발하지 않는다.
#:
#: 태스크 4 예산 590.0 의 출처 [ESTIMATE]:
#:   b(N) = P5_TOTAL_CORE_HOURS × N³/Σ N³  (p5_task_budgets 와 같은 N³ 규칙,
#:          Σ 는 _p5_runs() 의 22개 실행; b = 소분자 opt+freq 1회의 κ=6.8 비관 단가)
#:   기준 원자 수는 태스크 4 의 **실제 대상 기하**다 (P1b 종 집합이 아니다):
#:     11 = inputs/li_ec_radical_reactant.xyz (stagewise 의 TS 기하 폴백; 파일 1행 실측)
#:     10 = u27_reference 종 ec (inputs/p5_species/manifest.json)
#:   stagewise L2 4회(sp/force/freq/opt5) ≤ 1×opt+freq(11) = b(11) = 71.3
#:   stagewise L3 4회(더 싼 기저, 같은 상한)              ≤ b(11) = 71.3
#:   U-27 (opt + SP 2회, 10원자)                           ≤ b(10) = 53.6
#:   합계 196.3 core-h. ⚠ 작업 믹스가 다르다: b() 는 소분자 opt+freq 단가 커브고
#:   태스크 4 는 sp/force/freq/opt5 ×2레벨 + U-27 이다 — 같은 커브가 아니므로 이 수는
#:   상한 논증이지 측정이 아니다. 🔴 과소추정이 위험한 방향(wall=budget/cores 가 짧아져
#:   wall-kill)이라 **여유 3배**(lead 지시): 196.3 × 3 ≈ 590.0. wall = 590/64 = 9.2 h.
#:   가드 검산: 19,475.4 + 590 = 20,065.4 < 21,000 (통과).
P1B_TASK_CORE_HOURS = (476.0, 1190.0, 3072.0, 590.0)
P5_TOTAL_CORE_HOURS = 2926.0
P6_TASK_CORES = (1, 16, 64)                       # κ 앵커 + 스레드 스케일링 S
#: [engineer9, 2026-08-21, approved] 24 h -> 2 h. MEASURED: slowest P6 task (t1, 1 thread)
#: finished in 42 min on the returned round; 2 h is ~2.9x that. Recovers ~1,782 core-h of
#: reservation. Same shape as P1's resize -- backed by real data, not a cube law.
P6_WALL_H = 2.0
#: 🔒 §R23 / lead 판정 — CP2K s/step 편승. 후보 B 발동 시 왕복 1회(3.5일)를 없앤다.
P7_TOTAL_CORE_HOURS = 1000.0

# ---------------------------------------------------------------------------
# 🔴 [ADR-109 / §39.39(d)] U56-2 예산 — **전부 [ESTIMATE] placeholder 다.**
#    engineer7 의 §R39 견적(21원자 endpoint 인증이 유일한 budget driver, 미가격)이
#    착지하면 이 블록만 갈아끼운다. R-11: payload 작업은 planner budget model 에
#    보여야 한다 — 그래서 숫자가 없더라도 Item 과 예산 자리는 지금 존재한다.
#    ⚠ 단위: 아래 앵커 220.8 은 **KNL core-h** (raw-KNL, §R38.4/ADR-095) 이고,
#    이 placeholder 들도 같은 관례로 적는다. ref-core-h 와 κ 명기 없이 합산 금지.
# ---------------------------------------------------------------------------
#: 11원자 endpoint 인증: 🔒 R38.5 하드 캡 384 core-h / 6 h — reactant 항목과 동일한
#: 비준값(placeholder 아님).
U56_ENDPOINT_11ATOM_CORE_H = 384.0
#: [engineer9 §R39.52, approved] 11-atom U56-2 endpoint cert WALL 6 h -> 3 h (whole node
#: => 192 core-h reserved each). MEASURED: 1.029 h wall for the converged arm, with a 1.43x
#: wall spread between two runs of the identical calculation -- 3 h is 2.9x headroom.
#: 🔴 The 21-atom cert (below) is NOT shaved: no measurement exists for that size class and
#: li_ec2_cation failed to converge in both P5 seeds (429.55 core-h in one).
#: The base `endpoint_prep_reactant` keeps 6 h (ratified hard cap, lead ruling).
U56_ENDPOINT_11ATOM_WALL_H = 3.0
#: 🔒 21원자 endpoint 인증(E21) 캡 = **1,536 core-h [ADOPTED — engineer7 §R39,
#: lead 2026-08-20], wall 48h[ADR-114, 원래 24h 로 채택].** 6h/384 를 물려받지 않는 이유(실측): li_ec2_cation(21원자,
#: closed shell, 같은 분자 -e⁻)이 282.7 core-h 를 쓰고도 미수렴(03_COMPUTE_PLAN.md:8236)
#: — 384 캡이면 거의 확실히 budget_exhausted 로 끝나고, 그 기록은 "cap 부족"이 아니라
#: "종이 실패함"으로 오독된다. §R26.1: cap 이 크면 항목을 빼는 것이지 cap 을 줄이는 게
#: 아니다.
#: 🔴 [ADR-114, 2026-08-21, 사용자 직접 지시] wall 24 -> 48. `core_hours_budget` 은
#: **의도적으로 그대로 1536.0** — lead 에게 별도로 플래그됨: `size_tasks()`(explicit_wall_h
#: 경로)는 `reserved_core_hours` 를 core_hours_budget 이 아니라 `cores x wall` 에서 매번
#: 새로 계산하므로, 이 wall 변경만으로 이 항목의 실제 guard 예약 천장이 1536 -> 3072 로
#: **자동으로** 뛴다 — 코드를 더 안 고쳐도 그렇다. 반면 payload 자신의 in-job 트립와이어
#: (`SEI_ENDPOINT_BUDGET_CORE_H`, 이 상수에서 옴)는 그대로 1536 이라 실제 계산은 더
#: 못 쓴다 — wall 만 늘면 guard 여유만 더 쓰고 실제 얻는 건 없다. 1536 을 올릴지는
#: 별도의 가격 판정이 필요해 lead 에게 넘겼다, 여기서 조용히 정하지 않는다.
U56_ENDPOINT_21ATOM_CORE_H = 1536.0
U56_ENDPOINT_21ATOM_WALL_H = 48.0
#: [ESTIMATE] 11원자 single-ended attempt = scan(coarse 12 + refine ≤8 제약 opt)
#: + opt=(ts,calcfc) + freq + 2×IRC ≈ 3 × ts_qst2 앵커 220.8 KNL core-h [MEASURED,
#: FLOOR — level2, 11원자, §39.33(e)] ≈ 662 → 700. engineer7 §R39 재가격 대기
#: (refine pass 추가 + UltraFine grid 반영 전 값).
U56_ATTEMPT_11ATOM_CORE_H = 700.0
#: [ESTIMATE] R-A QST2 attempt = QST2(calcfc)+freq+2×IRC ≈ 2 × 220.8 ≈ 442 → 450.
U56_ATTEMPT_QST2_CORE_H = 450.0
# 🔒 [C-8-2 패턴의 두 번째 취소 기록, §39.41(d) — proposer7 판정, lead 2026-08-20]
#    **T21-se(21원자 TS attempt, U56_RC_scan)는 이 라운드에서 뺐다. E21(21원자 endpoint
#    cert)은 유지한다.** 근거는 예산이 아니라 과학이다: production size 에서 d(O2–C3)
#    단독이 반응좌표가 아님을 GFN2 로 측정했다(Li⁺가 끊어지는 산소로 이동, d(Li–O2)
#    2.65→1.86 Å) — 두 TS 탐색 방법 모두 production size 에서 작동 미입증.
#    🔴 이 측정은 **S3 wave 1 로 이동한 것이지 삭제가 아니다.** 되살릴 조건: U-54 해소
#    또는 새 반응좌표(예: 2D/복합 좌표) 채택 — 그때는 U56_RC_scan 을 아래 attempt 들과
#    같은 패턴의 별도 Item 으로 복원하고 §39.41(d)를 갱신하라. U56-2 = 이제
#    **3 attempts(전부 11원자) + endpoint 인증 3건**이다.


# =============================================================================================
# 🔴 SP LADDER (§39.47(c), §39.48(d)/(e), §39.49, §R39.26, §R39.28)
# =============================================================================================
#
# WHAT IT IS: a full transition-state search is unaffordable at production size, so the ladder
# lays DFT single points on a GFN2 path and reads a barrier from those. `n` is the coordination
# number of one rung.
#
# 🔴 THE FIRST RUNG TO RETURN IS THIS PROJECT'S FIRST SINGLE-POINT MEASUREMENT. Every per-SP
# cost below is a DERIVED STACK (an anchor divided by a cycle count times a multiplier), not a
# measurement -- engineer7 flagged its own weakest number and it has not been superseded. ⟹ the
# later rungs must be RE-DERIVED FROM THE FIRST RUNG'S MEASURED COST, never from this stack
# (§39.48(e); the same rule as "measure kappa per run, never store a correction factor").
# 🟢 Why it is safe to ship on an unmeasured unit anyway: at 307 core-h against a 21,000 guard,
# the estimate can be wrong by ~25x before the round's arithmetic changes. ⚠ That margin was
# ~80x before engineer8's reprice -- it is shrinking, so the tolerance is not a standing licence.
SP_LADDER_CORE_H = {1: 10.0, 2: 70.0, 3: 227.0}          # §R39.26, raw-KNL
SP_LADDER_CEILING_CORE_H = {1: 32.0, 2: 70.0, 3: 227.0}

#: 🔴 [§R39.28] PRE-REGISTERED REPLANNING TRIGGER. If the FIRST rung's measured per-SP cost
#: differs from the estimate by >= this factor, the remaining rungs are re-planned **before
#: submission**, not after. Derived, not chosen: n=4 breaches its cap at 5.9x and n=3 at 13.5x,
#: where `links` doubles and the ceiling jumps -- 3x is half the distance to the nearer cliff.
#: Without it, a 5x error ends n=3/n=4 in silent budget exhaustion: ~749 core-h spent for
#: nothing plus a round trip.
SP_LADDER_REPLAN_TRIGGER = 3.0

#: 🔴 [§39.48(d)] Both endpoints + FIVE consecutive path points centred on the GFN2 maximum.
#: Five, not one: the DFT maximum along a GFN2 path need not sit at the GFN2 maximum, and
#: sampling a maximum on a coarse grid UNDER-estimates it -- measured at 0.10 eV in this project
#: (§39.43's 0.05 vs 0.01 A grids). A barrier biased LOW is a rate biased HIGH, which is §0-h's
#: optimistic direction, the one we have never self-corrected from.
#: If the DFT maximum lands at a bracket EDGE, extend by 2 (<= 9) -- the same coarse+triggered
#: pattern as §39.42(b), reused rather than reinvented.
SP_LADDER_POINTS = 7
SP_LADDER_POINTS_MAX = 9


def sp_ladder_released(cfg=None):
    """🔒 Same S-2 release-gate pattern as `u56_2_released`: built and tested always, joined
    into the plan only when the flag says so, and **the code never sets the flag.**"""
    cfg = cfg if cfg is not None else config.load("b0_reactions.json", {})
    return (cfg.get("sp_ladder") or {}).get("released") is True


def p5_freq_recovery_released(cfg=None):
    """🔒 Same S-2 release-gate pattern as `u56_2_released`; the code never sets the flag."""
    cfg = cfg if cfg is not None else config.load("b0_reactions.json", {})
    return (cfg.get("p5_freq_recovery") or {}).get("released") is True


def p5_freq_recovery_rows(cfg=None):
    cfg = cfg if cfg is not None else config.load("p5_freq_recovery.json", {})
    return list(cfg.get("rows") or [])


def p5_freq_recovery_items():
    """[§39.103 proposer8 / §R39.65 engineer9] ONE Hessian per stored converged P5 geometry,
    at production settings (acetone deck, nosymm, UltraFine, the row's own level). Array, one
    row per task, budgets per row from config (NBasis-based, pessimistic exponent -- NOT a
    freq/opt ratio). `cores_per_task=64` = P5 round 1's basis so `u_cheap = u_opt + u_freq`
    is assembled from ONE thread configuration. Returns [] when not released."""
    if not p5_freq_recovery_released():
        return []
    cfg = config.load("p5_freq_recovery.json", {})
    rows = list(cfg.get("rows") or [])
    budgets = tuple(float(r["task_budget_core_h"]) for r in rows)
    if not rows:
        return []
    return [Item(
        "P5_freq_recovery",
        "P5 freq-only recovery: %d stored geometries, one Hessian each (C-9 n_imag audit + u_freq)"
        % len(rows),
        73,
        core_hours_budget=sum(budgets), nodes=1,
        array=(1, len(rows)), task_budgets=budgets,
        cores_per_task=int(cfg.get("cores_per_task") or 64),
        min_wall_h=float(cfg.get("min_wall_h") or 0.25),
        payload="payload/P5_FREQ.sh",
        requires=[("any", QC_CODES)],
        account_key="gaussian",
        rationale=("§39.74/§39.78: P5's freq half died on the EpsInf sentinel; u_cheap has an "
                   "EMPTY denominator until a Hessian exists per row. Recovery reads the stored "
                   "converged geometry (opt is NOT repeated: §39.89 -- re-optimising would destroy "
                   "the C-9 audit value). Cost deliverable usable at once; chemical outputs "
                   "(n_imag, ZPE, thermal) UNCERTIFIED by default (§39.82(b)). Convicted "
                   "symmetry-trapped rows run for u_freq only (chemistry refused, §39.103)."))]


def sp_ladder_items():
    """The SP ladder's plan Items — one per rung, n = 1, 2, 3.

    🔴 n = 4 IS DELIBERATELY ABSENT, not forgotten: §39.48(c) makes a 2-D scan a PRECONDITION
    for it (hysteresis grows with n -- 1-D inflates the barrier by 0.00 / 0.10 / 0.21 eV at
    n = 1 / 2 / 3), and that scan does not exist. Adding the rung without it would consume
    522 core-h to produce a number inflated by an unmeasured amount.

    🔴 FOUR FUNDING PRECONDITIONS (§R39.24), none of which costs core-hours and each of which
    voids its rung if broken:
      1. the route flags must be IDENTICAL to a full attempt's -- otherwise the ladder measures
         a route difference and reports it as a method difference. Enforced by sharing the
         route generator, not by comparing strings in two places.
      2. each rung's path must pass the §39.45 reverse-scan verdict -- one G-SCAN per PATH, not
         per reaction, since the gate is a statement about a path.
      3. condition 8 (the solvent deck verified as APPLIED, not merely accepted) is inherited.
      4. `cores_per_task` is DECLARED (ADR-110), never defaulted to the whole node.

    🔴 AND THE BARRIER'S REFERENCE: the GFN2 path's OWN first frame, computed at DFT. The
    certified reactant supplies the STRUCTURE and never an energy -- the same invariant as
    G-SCAN-2's clause (i) (§39.64/§39.70). engineer7 found this in its own spec by applying
    proposer7's no-cross-Hamiltonian rule to it: `E(top) - E(reactant)` with a DFT-optimised
    reactant puts the two ends of the barrier in different relaxation states, and the error
    GROWS WITH n -- so it is not safe even though each rung looks fine on its own.
    """
    items = []
    for n in (1, 2, 3):
        items.append(Item(
            "sp_ladder_n%d" % n,
            "SP ladder rung n=%d: DFT single points on the GFN2 path (%d pts, +2 if the DFT "
            "maximum lands at a bracket edge)" % (n, SP_LADDER_POINTS),
            72,
            core_hours_budget=SP_LADDER_CORE_H[n], nodes=1,
            # 🔴 [ADR-110] DECLARED, not defaulted. These are G16 single points on a
            #    64-core job and they really do use the node -- work ~= charged here, unlike
            #    an xtb stage. Declaring it is what keeps that statement checkable.
            cores_per_task=64,
            payload="payload/SP_LADDER.sh",
            requires=[("any", QC_CODES)],
            account_key="gaussian",
            extra_env={"SEI_SP_LADDER_N": str(n),
                       "SEI_SP_LADDER_POINTS": str(SP_LADDER_POINTS),
                       "SEI_SP_LADDER_POINTS_MAX": str(SP_LADDER_POINTS_MAX)},
            rationale=(
                "[ESTIMATE — DERIVED STACK, NOT MEASURED] per-SP cost is an anchor / cycles x "
                "multiplier; no standalone single point has ever been measured on this "
                "project. THE FIRST RUNG TO RETURN IS THAT MEASUREMENT, and every later rung "
                "must be re-derived from it rather than from this stack (§39.48(e)). "
                "Safe to ship unmeasured only because 307 core-h against a 21,000 guard "
                "tolerates a ~25x error -- down from ~80x before engineer8's reprice, so the "
                "margin is shrinking and this is not a standing licence. "
                "🔴 PRE-REGISTERED: if rung n=1's measured per-SP cost differs from the "
                "estimate by >= %.0fx, RE-PLAN the remaining rungs BEFORE submitting them "
                "(§R39.28) -- n=4 breaches its cap at 5.9x and n=3 at 13.5x."
                % SP_LADDER_REPLAN_TRIGGER)))
    return items


def sp_ladder_replan_required(measured_per_sp_core_h, estimated_per_sp_core_h,
                              trigger=SP_LADDER_REPLAN_TRIGGER):
    """🔴 [§R39.28] Does the first rung's measured cost force a re-plan of the rest?

    Returns a record, not a bare bool -- the ratio is what a human needs and the threshold's
    derivation travels with it. Symmetric in direction: a cost far BELOW the estimate is also a
    reason to re-plan, because the estimate is then wrong in a way that may not be conservative
    at the next rung up.
    """
    out = {"replan_required": False, "ratio": None, "trigger": float(trigger),
           "measured_per_sp_core_h": measured_per_sp_core_h,
           "estimated_per_sp_core_h": estimated_per_sp_core_h,
           "_derivation": ("n=4 breaches its cap at 5.9x and n=3 at 13.5x, where `links` "
                           "doubles and the ceiling jumps; 3x is half the distance to the "
                           "nearer cliff (§R39.28)")}
    if not measured_per_sp_core_h or not estimated_per_sp_core_h:
        out["reason"] = ("cannot compare -- a missing cost is not a passed check (the first "
                         "rung exists precisely to supply this number)")
        out["replan_required"] = True
        return out
    hi, lo = sorted((float(measured_per_sp_core_h), float(estimated_per_sp_core_h)),
                    reverse=True)
    out["ratio"] = hi / lo if lo else None
    out["replan_required"] = bool(out["ratio"] and out["ratio"] >= float(trigger))
    out["reason"] = (
        "measured/estimated differ by %.2fx (>= %.0fx) -- re-plan the remaining rungs BEFORE "
        "submitting them" % (out["ratio"], trigger) if out["replan_required"]
        else "measured/estimated differ by %.2fx, inside the pre-registered %.0fx"
             % (out["ratio"], trigger))
    return out


#: 🔴 P1's sizing after its permanent exclusion (engineer8, lead-approved). NOT the cost of
#: running P1 -- the cost of C-8 REFUSING it, which is all it can ever do. Measured refusal:
#: 0.0103 core-h / 37 s. 64 core-h = one whole node for one hour, ~6,200x that.
P1_EXCLUDED_REFUSAL_CORE_H = 64.0
P1_EXCLUDED_REFUSAL_WALL_H = 1.0


def u56_2_released(cfg=None):
    """🔒 [S-2 패턴 — deck_verified 와 동일] U56-2 항목의 release 게이트.

    ADR-109: U56-2 항목은 engineer7 견적 + critic 통과 후의 **FUTURE round** 에만
    들어간다 — 비행 중 batch(예약 20,065 / guard 21,000)에는 아무것도 추가되지 않는다.
    플래그는 config/b0_reactions.json `u56_2.released` 하나뿐이고, **코드는 절대 올리지
    않는다** (올리는 것은 lead/사용자 몫; tests/test_u56_plan_items.py 가 코드 쓰기
    부재를 고정한다).
    """
    cfg = cfg if cfg is not None else config.load("b0_reactions.json", {})
    return (cfg.get("u56_2") or {}).get("released") is True


def u56_2_items():
    """U56-2 (4 attempts / 3 endpoint certs) 의 plan Items.

    🔴 array 금지 — P6 주석("항목 N개면 계획·사전검사·제출·emit·회신이 기존 경로를
    그대로 타고 새 분기가 0")과 C-8-2 취소 기록의 부활 규칙 그대로, 전부 별도 Item 이다.
    reactant 인증(R-A/R-B 공유, 11원자)은 기존 endpoint_prep_reactant 가 그 항목이다 —
    여기 중복 정의하지 않는다(3번째 cert).
    """
    return [
        # 🔒 [C-8-2 취소 기록의 부활 규칙 준수] endpoint_prep_product 부활 근거는 P1 이
        #    아니라 ADR-109 ruling 2 (B0-F R-A product cert — U56-2 의 QST2 arm 과 R-A
        #    양방향 검증이 소비자다). reactant Item 과 같은 패턴: 별도 Item, role 은
        #    SEI_ENDPOINT_ROLE 채널, 6h/384 하드 캡(11원자, R38.5 비준값).
        Item("endpoint_prep_product",
             "U56-2: R-A product endpoint 인증 (이중 시작점 rough opt -> tight opt+freq)",
             76,
             core_hours_budget=U56_ENDPOINT_11ATOM_CORE_H, nodes=1,
             cores_per_task=None,
             explicit_wall_h=U56_ENDPOINT_11ATOM_WALL_H,
             payload="payload/endpoint_prep.sh",
             requires=[("any", QC_CODES)],
             account_key="gaussian",
             # 🔴 [§39.41 / lead 경고] packaged product guess 는 GFN2 에서 scan 유래
             #    open 구조보다 **0.59 eV 위 basin** 이고 n_imag 3/5 인 채로 "converged"
             #    를 찍는다(ADR-067 4번째 사례, 이번엔 측정). ⟹ ALT 시작점을 함께
             #    선언하고 payload 가 둘 다 stage-1 rough opt 후 낮은 basin 을 stage 2
             #    에 넘긴다 — DFT 인증 1건을 시작점 하나 때문에 버리지 않는다.
             extra_env={"SEI_ENDPOINT_ROLE": "product",
                        "SEI_ENDPOINT_ALT_INPUT_XYZ":
                            "inputs/li_ec_radical_product_scanopen.xyz",
                        "SEI_ENDPOINT_BUDGET_H": "6.0",
                        "SEI_ENDPOINT_BUDGET_CORE_H": "384.0"},
             rationale="ADR-109 ruling 2: B0-F grounds, NOT a P1 revival. R-A 는 product "
                       "를 인증 없이 QST2 에 줄 수 없는(§39.39(d): 유일한 admissible "
                       "double-ended case) 반응이다."),
        Item("endpoint_prep_rc_reactant",
             "U56-2: R-C reactant endpoint 인증 (li_ec2_radical, 21원자, cap 24h/1536)",
             77,
             core_hours_budget=U56_ENDPOINT_21ATOM_CORE_H, nodes=1,
             cores_per_task=None,
             # 🔒 [engineer7 §R39 채택] 24h/1,536 — 상수 블록의 근거 주석 참조.
             explicit_wall_h=U56_ENDPOINT_21ATOM_WALL_H,
             payload="payload/endpoint_prep.sh",
             requires=[("any", QC_CODES)],
             account_key="gaussian",
             # 기하: §39.42(a) 6-seed 최저 basin (provenance sidecar 동봉,
             #    inputs/li_ec2_radical_reactant.provenance.json). 파일이 없으면 payload
             #    가 input_missing 으로 0 core-h 거부한다 — 기하 날조 금지는 그대로다.
             extra_env={"SEI_ENDPOINT_ROLE": "reactant",
                        "SEI_ENDPOINT_INPUT_XYZ": "inputs/li_ec2_radical_reactant.xyz",
                        "SEI_ENDPOINT_BUDGET_H":
                            str(U56_ENDPOINT_21ATOM_WALL_H),
                        "SEI_ENDPOINT_BUDGET_CORE_H":
                            str(U56_ENDPOINT_21ATOM_CORE_H)},
             rationale="§39.39(g)의 유일한 budget driver — engineer7 §R39 가 24h/1,536 "
                       "으로 가격했고 lead 가 채택했다(2026-08-20)."),
        Item("U56_RA_scan",
             "U56-2 attempt: R-A x relaxed_scan (single-ended) [ESTIMATE 예산]", 78,
             core_hours_budget=U56_ATTEMPT_11ATOM_CORE_H, nodes=1,
             cores_per_task=None,
             payload="payload/U56.sh",
             requires=[("any", QC_CODES)],
             depends_on=["endpoint_prep_reactant"],
             account_key="gaussian",
             extra_env={"SEI_U56_REACTION": "R-A", "SEI_U56_METHOD": "relaxed_scan",
                        "SEI_U56_REACTANT_ENDPOINT_KEY": "endpoint_prep_reactant"},
             # 🔴 [02_METHOD_SPEC.md §39.113(d), proposer -- housekeeping, Track A] R-A HAS a
             #    certified product (`endpoint_prep_product`, used by U56_RA_qst2 already) --
             #    relaxed_scan doesn't NEED it to start (single-ended), but the bracket check
             #    (payload's own §39.63/§39.65) runs the two-sided half only when a product cert
             #    is on record, so U56_RA_scan/U56_RA_qst2 (SAME reaction) were evaluated on
             #    unequal footing. U56.sh already resolves the product cert whenever
             #    `SEI_U56_PRODUCT_ENDPOINT_KEY` is declared (not qst2-only anymore, fixed
             #    already) -- but adding that key HERE is held per lead's explicit ruling
             #    2026-08-21 (option ii, critic14's finding): `extra_env` is in
             #    `state.SPEC_DIGEST_FIELDS`, so adding it now would mark this Item's spec
             #    stale and trigger an immediate whole-item resubmit (336 core-h) that would
             #    just repeat the identical IRC crash for zero new information. Land this key
             #    TOGETHER with whatever the Track B IRC-integrator fix turns out to be (its
             #    settings ALSO belong on extra_env, same reasoning) so one resubmit buys both.
             rationale="U56-1 ⊂ U56-2 (§39.39(h)): 예산이 잘려도 이 항목 하나가 U-56a "
                       "게이트를 들 수 있다 — 그래서 attempt 4개 중 우선순위가 첫째다."),
        Item("U56_RA_qst2",
             "U56-2 attempt: R-A x QST2 (double-ended, 유일 admissible) [ESTIMATE 예산]",
             79,
             core_hours_budget=U56_ATTEMPT_QST2_CORE_H, nodes=1,
             cores_per_task=None,
             payload="payload/U56.sh",
             requires=[("any", QC_CODES)],
             depends_on=["endpoint_prep_reactant", "endpoint_prep_product"],
             account_key="gaussian",
             extra_env={"SEI_U56_REACTION": "R-A", "SEI_U56_METHOD": "qst2",
                        "SEI_U56_REACTANT_ENDPOINT_KEY": "endpoint_prep_reactant",
                        "SEI_U56_PRODUCT_ENDPOINT_KEY": "endpoint_prep_product"},
             rationale="§39.39(d): 두 method 가 같은 saddle 에 도달하는지가 가장 강한 "
                       "내부-외부 검증. 🔴 폴백 없음 — method 를 갈아타면 bake-off "
                       "비교가 오염된다(payload 주석)."),
        Item("U56_RB_scan",
             "U56-2 attempt: R-B x relaxed_scan (같은 반응물, 다른 좌표) [ESTIMATE 예산]",
             80,
             core_hours_budget=U56_ATTEMPT_11ATOM_CORE_H, nodes=1,
             cores_per_task=None,
             payload="payload/U56.sh",
             requires=[("any", QC_CODES)],
             depends_on=["endpoint_prep_reactant"],
             account_key="gaussian",
             extra_env={"SEI_U56_REACTION": "R-B", "SEI_U56_METHOD": "relaxed_scan",
                        "SEI_U56_REACTANT_ENDPOINT_KEY": "endpoint_prep_reactant"},
             rationale="R-B 의 product 는 검증 대상 화학 주장이라 single-ended 만 "
                       "admissible (§39.39(d): 'the run exists to test it')."),
        # 🔴 U56_RC_scan (T21-se) 은 여기 **없다** — §39.41(d) 컷, 상수 블록의 취소
        #    기록 참조 (S3 wave 1 로 이동, 삭제 아님).
    ]


def _p5_runs():
    """P5 의 **실행 1건 = array 태스크 1개** 목록을 manifest 에서 만든다.

    실행 수는 `기본 1 + dual_seed 1 + cheap_level_too 1` 이다(=22). 세는 곳은 manifest
    하나뿐이어야 한다 — 설명 문자열과 태스크 수가 갈리면 한쪽만 갱신된다.

    🔴 [array 분기 사고의 재발 방지] payload/P5.sh 가 **이 함수와 같은 목록**으로
    태스크를 골라야 한다. 지난 라운드의 tasks.tsv 는 (종×시드) 18줄을 따로 열거해
    이 22개 예산 목록과 어긋났다 — 열거가 두 곳이면 한쪽만 갱신된다. 그래서 seed/level
    을 여기서 함께 확정하고, payload 는 이 함수를 import 해 `runs[TID-1]` 만 돌린다.
      main  = 주 레벨(level 2), 시드 0
      seed2 = 주 레벨(level 2), 시드 1 (dual_seed 종의 σ_protocol 쌍)
      cheap = 값싼 레벨(level 1), 시드 0 (단가비 분모 — 시드 산포를 섞지 않는다)
    """
    try:
        with open(os.path.join(PKG_ROOT, "inputs", "p5_species",
                               "manifest.json")) as fh:
            species = json.load(fh)["species"]
    except (OSError, ValueError, KeyError):
        return []
    runs = []
    for sp in species:
        n = sp.get("n_basis") or sp.get("n_atoms") or 1
        base = {"id": sp["id"], "size": n, "file": sp.get("file"),
                "charge": sp.get("charge"), "multiplicity": sp.get("multiplicity"),
                "n_atoms": sp.get("n_atoms")}
        runs.append(dict(base, kind="main", seed=0, level=2))
        if sp.get("dual_seed"):
            runs.append(dict(base, kind="seed2", seed=1, level=2))
        if sp.get("cheap_level_too"):
            runs.append(dict(base, kind="cheap", seed=0, level=1))
    return runs


def p5_task_budgets(total_core_hours=P5_TOTAL_CORE_HOURS):
    """🔒 §R24.1 — 태스크당 예산 = 총액 × (N_i³ / Σ N³).

    🔴 왜 균일 예산을 폐기했나: engineer 가 균일 133 을 주고 종별 편차(4배)를
    `min_wall_h = 12` **바닥값으로 덮었다.** 그러면 작은 종도 12 h 를 예약받아
    **물리 천장이 예산의 5.77배(16,896)** 가 됐고, guard 21,000 을 혼자 다 먹는다.
    ⟹ **편차는 wall 바닥값이 아니라 예산에 넣는다.** 그러면 `wall = budget/cores` 가
    정확해지고 천장 ≈ 예산이 된다(P1b·P6 가 이미 그런 이유다).

    `n_basis` 가 manifest 에 없으므로 `n_atoms³` 를 쓴다 — engineer 사양이 그렇게 지정했다
    (`"N_basis 없으면 N_atoms³"`). 🔴 이것은 `[ESTIMATE]` 다: 실제 비용은 기저함수 수의
    ~N^2.5~3 이고 원자 수는 그 대리 변수일 뿐이다.
    """
    runs = _p5_runs()
    if not runs:
        return []
    cubes = [float(r["size"]) ** 3 for r in runs]
    tot = sum(cubes) or 1.0
    return [round(total_core_hours * c / tot, 2) for c in cubes]


def default_items(profile=PROFILE_CPU):
    """프로파일에 속한 항목만 돌려준다.

    🔴 GPU 패키지에 P1이 섞이거나 CPU 패키지에 P4가 남으면 사용자가 엉뚱한 머신에서
    엉뚱한 계산을 돌린다. 그 실패 모드를 테스트로 고정한다.
    """
    if profile not in PROFILES:
        raise ValueError("알 수 없는 프로파일: %s (%s)" % (profile, "|".join(PROFILES)))
    return [it for it in _all_items() if profile in it.profiles]


def _all_items():
    # 🔒 [ADR-109] U56-2 항목은 release 게이트 뒤에 있다 — u56_2_released() 의 docstring
    #    참조. released=false(현재 상태)에서는 아래 목록이 이전 라운드와 바이트 동일하게
    #    유지되어 비행 중 batch 의 guard 산식(예약 20,065 / 21,000)이 변하지 않는다.
    released_extra = u56_2_items() if u56_2_released() else []
    # 🔒 Same S-2 release gate, separate flag: the SP ladder is built and tested every round
    #    and joins the plan only when `sp_ladder.released` says so. The code never sets it.
    released_extra = released_extra + (sp_ladder_items() if sp_ladder_released() else [])
    released_extra = released_extra + p5_freq_recovery_items()
    _items = [
        Item("probe_node", "A1/A8/IO/Q2 — 계산 노드 환경 프로브", 10,
             core_hours_budget=15.0, nodes=1, min_wall_h=0.08,
             rationale="우리가 볼 수 없는 것 전부. 로그인 노드와 계산 노드는 다르다 "
                       "(특히 Q2 네트워크와 $TMPDIR)."),
        Item("probe_throughput", "many-task 처리량 (200 x 1분)", 20,
             core_hours_budget=5.0, nodes=1, array=(1, 200), min_wall_h=1 / 60.0,
             # 🔴 이 항목만 **태스크당 1코어**다(200개 × 1분 × 1코어). 예전에는 이 1 이
             #    산식에 하드코딩돼 있었고, P5·P1b 가 array 가 되면서 그 가정을 물려받을
             #    뻔했다. 이제 **항목이 선언한다.**
             cores_per_task=1,
             requires=[("scheduler", ["slurm", "pbs"])],
             rationale="engineer: '비용 대비 정보량이 이 패키지에서 가장 높다. "
                       "절대 빼지 마라.' A9 duty cycle을 실측으로 바꾼다."),
        # nodes=85 = 1+4+16+64. 🔴 실제로는 4개 잡으로 나가지만 **예약은 합계로**
        # 잡아야 한다. 1로 잡으면 가드가 실제 소비의 1/85만 막는다(가드 무력화).
        Item("probe_queuewait", "큐 대기 실측 (1/4/16/64 node)", 30,
             core_hours_budget=250.0, nodes=85, min_wall_h=2 / 60.0,
             requires=[("scheduler", ["slurm", "pbs"])],
             rationale="§R2-2 왕복 지연 모델의 유일한 실측 입력."),
        # --- GPU 패키지 ---
        Item("probe_gpu_node", "GPU 머신 환경 프로브 (GPU/CUDA/CPU/스크래치/네트워크)", 10,
             core_hours_budget=4.0, nodes=1, min_wall_h=0.08,
             profiles=(PROFILE_GPU,),
             rationale="GPU 머신은 HPC와 다른 기계다. core/RAM/스크래치/네트워크를 "
                       "따로 재야 P4 속도비를 해석할 수 있다."),
        Item("P4", "GPU4PySCF SP+gradient vs 같은 머신 CPU", 40,
             core_hours_budget=30.0, gpu_hours=1.0, gpus=1, nodes=1,
             profiles=(PROFILE_GPU,),
             requires=[("gpu", []), ("any", ["python3"])],
             rationale="§R2-6 우선순위 변경: P4를 최우선(P0급)으로 승격. "
                       "Q1=yes면 유효 봉투 ~2배, 임계 경로 -2~3주(§R2-7). "
                       "🔴 CPU 기준값은 **같은 GPU 머신의 CPU**로 잰다(머신이 분리돼 "
                       "있어 HPC CPU와 직접 비교가 불가능하기 때문). 그 사실을 회신에 명시."),
        # 🔒 ADR-049 — **P3 는 계획에서 제거했다. 비용 때문이 아니라 이미 측정됐기 때문이다.**
        #    RT-1 에서 `pass` 했고 시도단가 0.10038 core-h · 수렴률 31.7% 를 확보했다.
        #    스레드 수 의문(κ 방증의 전제)도 코드 확인으로 닫혔다(`P3.sh` 가 `-P 1`).
        #    🔴 **측정된 것을 다시 재지 않는다.** 되살리려면 이 블록을 복원하면 된다
        #    (예산 500 / nodes 1 / requires xtb / account_key "xtb").
        # 🔴🔴 P1 IS PERMANENTLY EXCLUDED BY USER RULING, AND IT IS STILL HERE ON PURPOSE.
        #
        # WHY THE ITEM STAYS: `P1b` -- this round's single largest item at 5,328 core-h --
        # carries `depends_on=["P1"]` (below). The missing-dependency check drops any item
        # whose dependency is absent from the plan, so DELETING P1 WOULD SILENTLY DROP P1b
        # from the round. That is a worse failure than the one it would fix, and it would be
        # invisible: the round would simply come back smaller.
        #
        # WHY IT CANNOT RUN ANYWAY -- the structural guard, which is NOT this budget:
        # P1 is a QST2 (double-ended) search, so C-8 requires BOTH endpoints certified at the
        # same level, and `guards.ts_precondition` is never True on missing information. The
        # `endpoint_prep_product` Item was REMOVED when P1 was excluded, so no product
        # certificate can ever exist ⟹ C-8 refuses, every time, before any chemistry runs.
        # 🔒 That absence IS the guard. `tests/test_p1_excluded_sizing.py` pins it, because a
        #    guard that consists of something being missing is exactly the kind that gets
        #    undone by someone helpfully adding it back.
        # 🟢 MEASURED, this round, on real hardware: P1 was submitted, C-8 refused it three
        #    times, and the whole thing cost **0.0103 core-h (37 s)** instead of 527.8.
        #
        # WHY THE BUDGET SHRANK (engineer8, lead-approved): it was 6,800 core-h / 48 h /
        # whole node -- sized as if it might really run -- which RESERVED ~9,216 core-h of
        # ceiling (64 x 48 x 3 links) against the guard for something that structurally cannot
        # spend more than a few core-h. Recovers ~9,150 core-h of headroom.
        # ⚠ Sized at ~6,200x the measured refusal cost, deliberately generous: if C-8 ever
        #   fails to fire, this makes the resulting run SHORT AND CHEAP rather than a 48-hour
        #   whole-node burn. The margin is the safety property, not the size.
        Item("P1", "🔴 [PERMANENTLY EXCLUDED — C-8 refuses; kept only to satisfy P1b's "
                   "dependency] EC+Li+ 환원 라디칼 ring-opening TS 완주", 70,
             core_hours_budget=P1_EXCLUDED_REFUSAL_CORE_H, nodes=1,
             cores_per_task=None,          # 노드 전체(cores_per_node)를 쓴다
             min_wall_h=P1_EXCLUDED_REFUSAL_WALL_H,
             requires=[("any", QC_CODES)],
             account_key="gaussian",
             rationale="🔴 PERMANENTLY EXCLUDED by user ruling. The Item exists ONLY because "
                       "P1b depends on it and the missing-dependency check would drop P1b "
                       "with it. 🔴 [coder13, 2026-08-21] `endpoint_prep_product` is now "
                       "LEGITIMATELY back in the plan (U56-2/ADR-109 ruling 2, R-A's own "
                       "product cert -- NOT a P1 revival), so 'the item was removed' is no "
                       "longer the reason P1 stays blocked. The real guard: `payload/P1.sh`'s "
                       "own C-8 call is hardcoded to a bare {\"source\": path} dict, never "
                       "reads any endpoint_prep_* job's output (see test_p1_excluded_sizing.py "
                       "for the pinned proof) -- P1 cannot pass regardless of what else is in "
                       "the plan (measured this round: refused 3x, 0.658 core-h total, 37 s x "
                       "64 cores -- the earlier '0.0103' figure here was wall-hours mislabeled "
                       "as core-h, corrected). Budget sized for the refusal, ~97x its measured "
                       "cost -- generous so that a guard failure is short and cheap rather "
                       "than a 48 h burn."),
        # 🔴 ADR-099/§39.38 -- 두-스테이지 endpoint 준비, reactant 1건만. lead 지시(this
        #    round): "BUILD THE MINIMUM THAT LETS ONE JOB RUN. Nothing more" -- 병렬 두-끝단
        #    제출도, b0_plan 배선도, B0-F 도 아니다. product 끝단·병렬 제출은 이 항목이
        #    아니라 나중 스코프다(payload/endpoint_prep.sh, sei_pilot/collect.py 의
        #    collect_endpoint_prep -- 지금까지 producer 가 없던 유일한 조각이 이거였다).
        Item("endpoint_prep_reactant",
             "ADR-099 두-스테이지 endpoint 준비 (rough opt -> tight opt+freq), reactant 1건",
             71,
             core_hours_budget=384.0, nodes=1,
             cores_per_task=None,          # 노드 전체(P1과 같은 컨벤션)
             # 🔒 6h/384 core-h 는 예산에서 역산할 상한이 아니라 **비준된 하드 캡**이다
             #    (lead ruling). P6 와 같은 이유로 explicit_wall_h -- wall 이 이 항목의
             #    실제 자원 상한이고, 384 core-h 는 endpoint_prep.sh 자신의 내부
             #    stage1/stage2 누적 예산 체크(SEI_ENDPOINT_BUDGET_CORE_H)가 지킨다.
             explicit_wall_h=6.0,
             payload="payload/endpoint_prep.sh",
             requires=[("any", QC_CODES)],
             account_key="gaussian",
             # 🔒 [user ruling 2026-08-21] EpsInf bracket CANCELLED; the PCM deck names a
             #    carrier solvent (solvent.PCM_CARRIER_SOLVENT) so the freq stage no longer
             #    reads a zero EpsInf. No per-item EpsInf env anywhere.
             extra_env={"SEI_ENDPOINT_ROLE": "reactant",
                       "SEI_ENDPOINT_BUDGET_H": "6.0",
                       "SEI_ENDPOINT_BUDGET_CORE_H": "384.0"},
             rationale="engineer6 §R38.5 + proposer6 F1 + C-2/U-56 untruncated-run "
                       "precondition, 세 독립 근거가 수렴한 '실제 화학 계산 1건 완주'."),
        # 🔒 [C-8-2 취소 기록, 2026-08-20] `endpoint_prep_product` Item 은 한 번 들어왔다가
        #    **사용자 판정으로 제거됐다**: "P1 은 이번 라운드에서 빼고, 앞으로도 넣지
        #    않는다." product 끝단 인증은 P1(TS 탐색)의 C-8 전제를 채우기 위한 준비였고,
        #    P1 이 영구 제외되면 근거가 없다 — 근거 없는 384 core-h 를 계획에 남기지
        #    않는다. 되살릴 때는 reactant Item 과 같은 패턴의 **별도 Item** 으로(array
        #    금지 — A-1f 의 role 접미사와 P6 주석의 "항목 N개면 새 분기가 0"이 그 이유),
        #    role 은 SEI_ENDPOINT_ROLE 채널로. payload/endpoint_prep.sh 는 role=product
        #    를 이미 처리한다(입력 매핑·stage 접미사 모두).
        # 🔴 P1 다음, P1b 앞 (lead 지시). 전 pool thermo가 S3 TS보다 큰 항목이 됐다.
        Item("P5", "소분자 opt+freq 단가 곡선 (%s)" % _p5_shape(), 72,
             core_hours_budget=P5_TOTAL_CORE_HOURS, nodes=1,
             # 🔒 §R22.9: 실행 1건 = array 태스크 1개. 🔒 §R24.1: 예산은 크기³ 비례.
             array=(1, len(p5_task_budgets()) or 1),
             task_budgets=p5_task_budgets(),
             cores_per_task=None,          # 태스크당 노드 전체
             # 🔒 §R27 확정 (2.0 → 0.5). engineer 재검산: 최소종(3원자) opt+freq 비관
             #    180 s × κ=6.8 ÷ 병렬이득 1 = 0.34 h 이므로 0.5 h 는 여유 1.5×.
             #    0.25 는 126 core-h 를 벌고 최소종 여유를 절반으로 깎는다 — 나쁜 거래.
             #    §R24.1 은 2.0 을 줬으나 재검산 결과
             #    22 태스크 중 **15개**가 예산 < 128 core-h 라 2 h 바닥에 걸리고,
             #    그 초과분만 1,455 core-h(천장 4,381 = 예산의 1.50×)다.
             #    🔴 이것은 engineer 가 P5 에서 지적한 그 병(바닥값이 천장을 부풀림)의 축소판이다.
             #    0.5 h 면 천장 3,128(1.07×)이고, 3원자 opt+freq 에 30분이면 충분하다
             #    (P3 의 xtb 시도가 1스레드 361 s 였다).
             min_wall_h=0.5,
             requires=[("any", QC_CODES)],
             account_key="gaussian",
             rationale="🔴 ADR-026(LIBE 포기)+ADR-028(계층화 폐기)로 전 pool thermo"
                       "(2,142종)가 계당 최대 비용 항목이 됐는데 그 단가가 미측정이다. "
                       "P1은 40~80원자 TS를, P1b는 그 위 비율을 잰다 — 5~25원자 구간은 "
                       "아무도 재지 않았다. engineer RUNBOOK §R15 재계산 1순위. "
                       "P1과 독립(서로 다른 계). 예산 330→430: dual-seed 4종이 "
                       "주 레벨을 2회 돌기 때문(σ_protocol 측정)."),
        # 우선순위 75 = P1 직후. §11.5: "이 비율이 실제로 중요한 곳은 S1이 아니라
        # S2-A의 2,000 species thermo다" ⇒ 스케일링 측정보다 먼저 확보한다.
        Item("P1b", "레벨 단가비 5수 (u_cheap/r_high/r_composite/gen페널티/SCF실패)", 75,
             core_hours_budget=sum(P1B_TASK_CORE_HOURS), nodes=1,
             # 🔒 §R22.8 + MAJOR #1: 4-task array — 태스크 1-3 **종별**(5/12/22 원자),
             #    태스크 4 = stagewise + U-27 (P1B_TASK_CORE_HOURS 주석의 분리 근거 참조).
             #    🔴 "한 태스크 안에서 비(ratio)가 완결되어야 한다." r_composite=(A+C)/A 는
             #    같은 종의 측정 사이의 비이므로, 태스크 경계가 종을 가로지르면 그 값이
             #    아예 나오지 않는다 — 종별 3태스크의 경계는 절대 건드리지 마라.
             #    태스크 4 는 종별 비와 무관한 측정만 담는다.
             array=(1, len(P1B_TASK_CORE_HOURS)),
             task_budgets=list(P1B_TASK_CORE_HOURS),
             cores_per_task=None,
             min_wall_h=2.0,
             requires=[("any", QC_CODES)], depends_on=["P1"],
             account_key="gaussian",
             rationale="🔴 `r`(레벨 단가 배수)이 총액을 1.19~9.49 M (8배)로 벌리는 "
                       "단일 최대 미지수다. 계획을 다듬어서는 좁혀지지 않는다 — "
                       "이 측정만이 좁힌다(engineer §R16.6 RT-1b 흡수). 특히 "
                       "**r_composite** 하나가 ADR-032 채택 여부를 가르고, 채택되면 "
                       "스코프 절단이 불필요해진다(봉투의 37%%). "
                       "예산 400→700: 3종 × (값싼 opt+freq + 고수준 opt+freq + "
                       "고수준 SP + gen/내장 SP 2건) 이 더해졌다."),
        # 🔒 §R22.10 — P6: κ 앵커 + G16 스레드 스케일링 S. 신설.
        # 🔴 **array 가 아니라 항목 3개다.** 이유: 세 태스크의 `ncpus` 가 1/16/64 로 다른데
        #    **PBS array 는 태스크마다 select= 를 바꿀 수 없다.** array 로 만들면
        #    (a) 셋 다 64 를 요청해 예약이 1,944 → 4,608 이 되거나
        #    (b) `probe_queuewait` 처럼 전용 분해 코드를 또 만들어야 한다.
        #    (b)는 "표시와 제출이 갈리는" 그 버그를 한 번 더 만들 자리다(critic 이 거기서
        #    유령 잡을 잡았다). **항목 3개면 계획·사전검사·제출·emit·회신이 기존 경로를
        #    그대로 타고 새 분기가 0 이다.**
    ] + [
        Item("P6_t%d" % nthread,
             "κ 앵커 · G16 %d 스레드 (동일 계, 동일 잡타입)" % nthread,
             74,
             core_hours_budget=nthread * P6_WALL_H, nodes=1,
             cores_per_task=nthread,
             # 🔴 세 항목이 **payload 하나**를 공유한다. 스레드 수는 잡 스펙
             #    (`SEI_TOTAL_CORES`)에서 온다 — 스크립트를 세 벌로 복제하면 갈린다.
             payload="payload/P6.sh",
             # 🔴 budget→wall 역산이 성립하지 않는다: 1 스레드면 wall 이 340 h 가 된다.
             #    ⟹ wall 을 명시하고 예약을 cores×wall 로 잡는다(§R22.9 주의사항).
             explicit_wall_h=P6_WALL_H,
             requires=[("any", QC_CODES)],
             account_key="gaussian",
             rationale="🔴 κ 는 이 문서 모든 core-h 의 **단위**인데 지금은 비양자화학 문헌 "
                       "1건에서 유도한 [ESTIMATE] 3.4~6.8 뿐이고 총액을 5배 흔든다. "
                       "16 스레드가 κ 를 주고(개발 박스 [MEASURED] 177.3 s @ 16 스레드 "
                       "Ryzen 7800X3D 와 **같은 계·같은 잡타입**), 1↔16↔64 가 S(스케일링)를 "
                       "준다. S 는 생산 팩킹 이득 4/S 를 정한다(§R22.3). "
                       "64 가 16 보다 느리면 그 자체가 결론이다.")
        for nthread in P6_TASK_CORES
    ] + [
        # 🔴 P7(CP2K s/step)은 **넣지 않았다.** lead 가 승인했으나 구현 중에
        #    사용자 수준 제약과 충돌하는 것을 발견했다:
        #      tests/test_accounts.py:210 test_only_gaussian_and_xtb_remain
        #        "🔴 사용자 요구: 모든 DFT/반경험 방법론은 VASP·Gaussian·xtb 로"
        #      tests/test_integration_paths.py:223 test_cp2k_layer_is_fully_removed
        #    근거 ADR-037/038/039 (λ_out 재결 → CP2K 요구 소멸).
        #    ⟹ 그 테스트를 내가 지우면 **사용자 결정을 코더가 되돌리는 것**이다.
        #    스크립트는 `src/experiments/p7_cp2k/` 에 사유와 함께 보관했다. lead 판정 대기.
    ] + released_extra
    return _items


# --------------------------------------------------------------------------
# 가용성 판정
# --------------------------------------------------------------------------
def resolve_tool(env, names):
    """컨테이너 → 모듈 → 시스템 바이너리 순으로 실행 수단을 찾는다.

    반환: (kind, detail) 또는 (None, 사유)
    """
    # 🔴 동봉본이 최우선. 클러스터에 없는 도구를 되살리려고 실은 것이므로,
    #    시스템에 다른 버전이 있어도 **우리가 검증한 것**을 쓴다(재현성).
    vend = env.get("vendored") or {}
    for name in names:
        if name in vend:
            return "vendored", vend[name]
    containers = env.get("containers") or {}
    for name in names:
        if name in containers:
            return "container", containers[name]
    # 🔴 **모듈이 바이너리보다 먼저다.** (실클러스터에서 대가를 치른 순서다.)
    #
    #    사고: 로그인 노드 PATH 에 `/apps/commercial/G16/g16/g16` 이 있어 `binary` 로
    #    잡혔고, 그래서 잡 스크립트에 `module load` 줄이 **안 들어갔다.** 그런데
    #    계산 노드(node1026)의 인벤토리에서 `g16` 은 비어 있었다 →
    #    **P1/P1b/P5 가 전부 rc=3("QC 코드 없음")로 죽었다.**
    #    계산 노드에는 `gaussian/g16.*` 모듈이 4개나 있었는데 우리가 안 썼다.
    #
    #    이유: **모듈은 계산 노드에서 동작하도록 사이트가 만들어 둔 것**이고,
    #    로그인 PATH 의 경로는 로그인 노드에서만 유효할 수 있다. 그리고 Gaussian 은
    #    `g16root`/`GAUSS_EXEDIR` 환경까지 필요해서 경로만으로는 부족하다.
    qm = env.get("qc_module") or {}
    if qm.get("path") and qm.get("binary") in names:
        return "module(verified)", "%s → %s" % (qm["module"], qm["path"])
    software = env.get("software") or {}
    for name in names:
        entry = software.get(name)
        if entry:
            return "binary", entry.get("path", name)
    modules = [m.lower() for m in (env.get("modules") or [])]
    for name in names:
        base = name.split(".")[0].lower()
        for m in modules:
            if m.startswith(base):
                return "module", m
    return None, ("사용 가능한 실행 수단 없음: %s "
                  "(동봉본/컨테이너/모듈/PATH 모두 부재)" % ", ".join(names))


def check_requirements(item, env):
    """(runnable, skip_reason, tools) — 실패해도 예외를 던지지 않는다."""
    tools = {}
    for kind, names in item.requires:
        if kind == "scheduler":
            if env.get("scheduler") not in names:
                return False, ("스케줄러가 %s 가 아님(감지: %s). 이 프로브는 "
                               "배치 스케줄러 없이는 의미가 없다."
                               % ("/".join(names), env.get("scheduler")), ), tools
        elif kind == "gpu":
            gpu = env.get("gpus") or {}
            if not gpu.get("present"):
                return False, ("클러스터에서 GPU를 찾지 못했다 "
                               "(sinfo gres / nvidia-smi 모두 음성)",), tools
        elif kind == "any":
            got, detail = resolve_tool(env, names)
            if not got:
                # 🔴 "없음"만 보내면 다음에 무엇을 물어야 할지 우리가 모른다.
                #    module 시도 내역을 사유에 붙인다.
                qm = env.get("qc_module") or {}
                if qm.get("tried") and any(n in QC_CODES for n in names):
                    mods = ", ".join(sorted(set(t["module"]
                                                for t in qm["tried"]))) or "(없음)"
                    detail = ("%s | module 로도 시도했다: %s — 전부 실패. "
                              "`module avail` 에 보인 QC 후보: %s"
                              % (detail, mods,
                                 ", ".join(env.get("modules") or []) or "(없음)"))
                return False, (detail,), tools
            tools[names[0]] = {"how": got, "detail": detail}
    return True, None, tools


# --------------------------------------------------------------------------
# 계획 수립
# --------------------------------------------------------------------------
MIN_WALL_H = 0.25


QUEUE_WAIT_NODE_COUNTS = (1, 4, 16, 64)


def queue_wait_decomposition(env):
    """`probe_queuewait` 가 **실제로 제출하는** 노드 수 목록과 축소 내역.

    🔴 왜 함수로 뽑았나: `submit_entry()` 는 이 항목만 특례로 1/4/16 짜리 **개별 잡
    3개(각 1코어)** 로 쪼개 제출하는데, `submission_feasibility()` 는 항목 선언값
    (`nodes=85, cores_per_node=64`)으로 사전검사 스펙을 만들었다.
    ⇒ **사전검사가 시험한 형태(85×64=5,440코어)는 한 번도 제출되지 않고, 실제 제출되는
    3개 형태는 사전검사가 하나도 보지 않았다**(critic2).
    더 나쁜 것: `config/sizing.json` 의 주석에 *"85노드 요청이 거부됐다"* 고 적혀 있으니,
    **사전검사가 과거에 거부당한 바로 그 형태를 재현해 다시 시험하고 있었다.**
    큐 상한이 있는 사이트라면 이 항목만 "거부됨"으로 떠서, **실제로는 문제없을 3개 잡까지
    사용자가 의심하게 된다.**

    ⇒ 분해를 여기 한 곳에 두고 제출·사전검사가 공유한다. `max_probe_nodes` 가 나중에
      바뀌어도 두 경로가 함께 따라온다.
    """
    cap = int(((config.load("sizing.json", {}).get("pbs") or {})
               .get("max_probe_nodes") or 0) or 0)
    max_nodes = max([p.get("nodes") or 0 for p in env.get("partitions") or []] or [0])
    kept, dropped_cap, dropped_small = [], [], []
    for n in QUEUE_WAIT_NODE_COUNTS:
        if cap and n > cap:
            dropped_cap.append(n)
        elif max_nodes and n > max_nodes:
            dropped_small.append(n)
        else:
            kept.append(n)
    return {"node_counts": kept, "dropped_by_cap": dropped_cap,
            "dropped_too_large_for_cluster": dropped_small, "cap": cap,
            "cores_per_node": 1,
            "cluster_max_nodes": max_nodes or None}


def size_job(core_hours_budget, cores_per_node, nodes, max_wall_h, min_wall_h=None):
    """core-h 예산 → (wall_h, n_chain_links, reserved_core_h).

    wall을 예산에서 역산한다. 한 링크로 예산을 다 못 쓰면 afterany 체인을 건다.
    """
    floor = MIN_WALL_H if min_wall_h is None else float(min_wall_h)
    total_cores = max(1, int(cores_per_node) * int(nodes))
    if core_hours_budget <= 0:
        return floor, 1, 0.0
    ideal_wall = core_hours_budget / float(total_cores)
    wall = min(max(ideal_wall, floor), max_wall_h)
    links = max(1, int(math.ceil(core_hours_budget / (total_cores * wall) - 1e-9)))
    # 🔴 core-h 를 여기서 다시 계산하지 않는다. units 가 유일한 정의다.
    #    (예전에는 `total_cores * wall * links` 였다. 값은 같았지만 공식이 바뀌면
    #     이 자리는 조용히 안 따라온다 — critic2 지적.)
    reserved = units.core_hours_h(total_cores, wall) * links
    return round(wall, 4), links, round(reserved, 2)


def size_tasks(budgets, cores, max_wall_h, min_wall_h=None, explicit_wall_h=None):
    """태스크별 (wall, links, 물리천장) — **array 와 단일잡을 같은 산식으로 다룬다.**

    🔴 §R24.1 의 핵심 구분 두 가지를 여기서 만든다:
      * `expected_core_hours` = Σ 예산            — **소비 전망** (봉투·보고용)
      * `reserved_core_hours` = Σ cores×wall×links — **물리 천장** (guard 가 거는 값)
    스케줄러는 wall 에서 잡을 죽이므로 **천장은 파이썬 버그와 무관하게 강제된다.**
    guard 를 전망에 걸면 그 성질이 사라지고, `describe()` 의 *"제출 자체가 되지 않는다"* 가
    거짓이 된다 — **신뢰받는 안전장치가 실제로는 작동하지 않는 것은 없느니만 못하다**(§R24.1).

    🔴 그리고 이 함수가 §R24.1 이 지목한 결함을 구조적으로 막는다: **편차를 `min_wall_h`
    바닥값으로 덮으면 천장이 부풀어 오른다.** (P5 가 균일예산 133 + `min_wall 12` 로
    천장 5.77× 였다.) 편차는 **예산에** 넣어야 한다.

    `explicit_wall_h`: budget→wall 역산이 성립하지 않는 항목용(P6 는 태스크마다 코어가
    1/16/64 라 1스레드에서 wall 이 340 h 가 된다). 이때는 wall 을 명시하고 천장을 직접 잡는다.
    """
    budgets = list(budgets)
    if isinstance(cores, int):
        cores = [cores] * len(budgets)
    cores = [max(1, int(c)) for c in cores]
    floor = MIN_WALL_H if min_wall_h is None else float(min_wall_h)
    out = []
    for budget, ncore in zip(budgets, cores):
        if explicit_wall_h:
            wall = min(float(explicit_wall_h), float(max_wall_h))
            links = 1
        elif budget <= 0:
            wall, links = floor, 1
        else:
            wall = min(max(budget / float(ncore), floor), float(max_wall_h))
            links = max(1, int(math.ceil(budget / (ncore * wall) - 1e-9)))
        ceiling = units.core_hours_h(ncore, wall) * links
        out.append({"budget_core_hours": round(float(budget), 2),
                    "cores": ncore,
                    "wall_h": round(wall, 4),
                    "chain_links": links,
                    "ceiling_core_hours": round(ceiling, 2)})
    return out


def summarize_tasks(tasks):
    """태스크 목록 → 항목 수준 집계. **두 통화를 절대 섞지 않는다.**"""
    return {
        "n_tasks": len(tasks),
        "expected_core_hours": round(sum(t["budget_core_hours"] for t in tasks), 2),
        "reserved_core_hours": round(sum(t["ceiling_core_hours"] for t in tasks), 2),
        "wall_h": max([t["wall_h"] for t in tasks] or [0.0]),
        "chain_links": max([t["chain_links"] for t in tasks] or [1]),
        "cores_per_task": tasks[0]["cores"] if tasks else 1,
        "node_hours": round(sum(t["wall_h"] * t["chain_links"] for t in tasks), 3),
    }


#: 🔒 §R24.1 — 두 통화의 정의. **하나만 실으면 소비자가 오독한다.**
CORE_HOUR_FIELD_DEFINITIONS = {
    "reserved_core_hours": ("물리 천장 = Σ(태스크 코어 × wall × 링크). "
                            "guard 는 **이 값**에 건다. 스케줄러가 wall 에서 잡을 죽이므로 "
                            "이 상한은 파이썬 버그와 무관하게 강제된다. "
                            "🔴 우리가 쓰겠다는 양이 아니라 넘을 수 없는 천장이다."),
    "expected_core_hours": ("κ=6.8 비관 가정의 예상 소비(**전망**). 봉투·보고용이며 "
                            "**강제되지 않는다.** PBS 는 요청 wall 이 아니라 실사용을 과금하므로 "
                            "미사용분은 청구되지 않는다."),
    "node_hours": ("Σ(wall × 링크). 사이트가 노드 단위로 과금하면 이것이 과금 진실이다 "
                   "(§R22.7). core-h 는 64 코어 기준이다."),
}


#: 🔒 ADR-052 — 사용자가 확인해 준 `normal` 큐의 wall 상한. **하드코딩된 사용값이 아니라
#: "이 값과 다르면 알린다"는 기준값이다.** 실제 sizing 은 `qstat -Qf` 실측을 쓴다.
EXPECTED_QUEUE_WALL_H = 48.0


#: 🔒 lead 요구 — 차단 사유 옆에 **무엇을 하면 풀리는지**를 함께 낸다.
#: 🔴 조용히 빠지면 그게 "조용한 실패" 여덟 번째다.
REMEDY_BY_GATE = {
    "a_cores_match": ("요청 코어 수가 선언과 다르다. 계획 표의 `코어` 열을 확인하고, "
                      "`--cores-per-node <N>` 으로 계산 노드 코어 수를 명시하면 풀릴 수 있다. "
                      "🔴 이 항목(P6)은 스레드 수를 **재는** 것이므로 값이 어긋난 채로 "
                      "돌리면 결과가 무효다."),
    "b_array_links_one": ("이 array 항목의 태스크 하나가 `코어 × wall 상한` 을 넘는다. "
                          "**더 긴 큐를 쓰면 그대로 풀린다** — `qstat -Qf` 로 walltime 이 "
                          "더 긴 큐(예: `long`)가 있는지 확인하고 `--queue <이름>` 으로 "
                          "지정하라. 큐가 없다면 이 항목만 다음 왕복으로 미뤄야 한다."),
    "c_total_within_guard": ("계획 총 천장이 가드를 넘는다. 🔴 **가드를 올리기 전에 사양을 "
                             "의심하라** — 어느 항목의 천장이 전망보다 크게 부풀었는지 "
                             "4-튜플 표에서 확인하라."),
}


def ncpus_override_from_config(args=None):
    """`--ncpus-per-node` > `config/sizing.json` 의 `pbs.ncpus_per_node` > 없음.

    🔴 [critic3 중대] 이 값이 **제출 시점(`build_spec`)에만** 적용되고 있었다.
    ⟹ 계획 표와 게이트는 **덮이기 전 값**을 보고, 제출은 덮인 값으로 나갔다.
      "보이는 것과 보내는 것이 다르다" — 이 패키지에서 세 번 난 형태다.
    ⟹ **한 곳에서 계산해 계획·게이트·제출이 같은 값을 쓴다.**
    """
    pbs_cfg = config.load("sizing.json", {}).get("pbs") or {}
    val = (getattr(args, "ncpus_per_node", None) if args is not None else None) \
        or pbs_cfg.get("ncpus_per_node")
    return int(val) if val else None


def item_cores_are_the_measurement(item_or_key):
    """이 항목의 코어 수가 **사이징 파라미터가 아니라 측정 대상**인가.

    🔴 P6(κ 앵커)는 1/16/64 스레드를 **재는 것**이 목적이다. 사이트 사이징 override 가
    거기에 적용되면 셋 다 같은 코어 수로 돌아 **S(스케일링)가 통째로 무의미**해진다.
    (런타임 게이트가 `[INVALID]` 로 잡아 κ 가 틀리게 나가지는 않지만, **P6 예산
    1,944 core-h 가 통째로 헛돈다.**)
    ⟹ 이런 항목에는 override 를 적용하지 않는다.
    """
    key = getattr(item_or_key, "key", item_or_key)
    return bool(key) and str(key).startswith("P6_t")


def sizing_gates(planned, guard):
    """🔒 §R26.4 게이트 3개. **하나라도 실패하면 제출하지 않는다.**

    engineer 가 *"내가 없어도 coder2 가 기계적으로 검증할 수 있게"* 남긴 닫힌형의 실행판이다:
      (a) 모든 array 태스크의 코어 수가 요청값과 같다 — **P6 는 1/16/64 로 서로 달라야 한다**
      (b) P1b·P5 의 링크가 전부 1 — array 를 체이닝하면 천장이 계단식으로 뛴다
          (체이닝은 P1 처럼 **직렬 의존**이 있는 항목 전용이다)
      (c) Σ 천장 ≤ guard.max_core_hours

    🔴 **숫자를 맞추려고 예산이나 guard 를 조정하지 마라. 그게 §R24.1 에서 기각한 거래다.**
    실패하면 4-튜플 표를 그대로 사람에게 보여주고 멈춘다.
    """
    failures = []
    by_key = dict((e["key"], e) for e in planned)
    live = [e for e in planned if e["status"] == "planned"]

    # (a) P6 의 세 태스크가 서로 다른 코어 수를 요청하는가
    p6 = [e for e in live if e["key"].startswith("P6_t")]
    for e in p6:
        want = int(e["key"].split("_t")[1])
        got = e.get("cores_per_node")
        if got != want:
            failures.append({
                "gate": "a_cores_match", "item": e["key"],
                "detail": ("요청 코어 %s != 선언 %s. 🔴 P6 는 스레드 수를 **재는** 항목이라 "
                           "이게 어긋나면 측정이 무의미하다. 그리고 이 결함은 **잡을 죽이지 "
                           "않는다** — G16 이 오버서브스크립션으로 정상 종료하고 "
                           "'데이터처럼 보이는 쓰레기'를 회신한다 (ADR-048)." % (got, want))})
    if p6 and len(set(e.get("cores_per_node") for e in p6)) != len(p6):
        failures.append({"gate": "a_cores_match", "item": "P6",
                         "detail": "P6 태스크들이 같은 코어 수를 요청하고 있다 — "
                                   "스케일링 S 를 측정할 수 없다."})

    # (b) array 항목의 링크가 전부 1
    for e in live:
        if e.get("array") and (e.get("chain_links") or 1) > 1:
            # 🟡 [PROVISIONAL] 종 단위 부분 실행 — **구조적으로는 이미 가능하다.**
            #    P1b 의 array 는 이미 **태스크 1개 = 종 1개**이고(§R22.8: "종이 비가
            #    완결되는 최소 단위"), 위반은 특정 태스크에만 생긴다.
            #    ⟹ array 범위를 좁히면(예: 1-3 → 1-2) 나머지 종은 그대로 돈다.
            #      `r_composite=(A+C)/A` 는 **종 안에서 완결**되므로 남는 종의 비는 유효하다.
            #    🔴 **발동은 자동으로 하지 않는다.** "2종만의 r 이 8배→3배 축소에 쓸 만한가"는
            #      견적자(engineer) 판정이고, 잃는 것은 **크기 의존성의 상단**이다.
            #      ⟹ 여기서는 **어느 태스크가 걸렸는지만 알린다.**
            bad = [i for i, t in enumerate(e.get("tasks") or [], start=1)
                   if (t.get("chain_links") or 1) > 1]
            ok_tasks = [i for i in range(1, len((e.get("tasks") or [])) + 1)
                        if i not in bad]
            failures.append({
                "gate": "b_array_links_one", "item": e["key"],
                "offending_tasks": bad,
                "runnable_tasks": ok_tasks,
                "partial_run_possible": bool(ok_tasks),
                "partial_run_note": (
                    "🟡 [PROVISIONAL] 태스크 %s 만 제외하면 %s 는 그대로 실행 가능하다 "
                    "(태스크 1개 = 종 1개, 비는 종 안에서 완결된다). "
                    "🔴 자동 발동하지 않는다 — 남는 종만으로 `r` 이 쓸 만한지는 engineer "
                    "판정 사항이고, 잃는 것은 크기 의존성의 상단이다."
                    % (bad, ok_tasks)) if ok_tasks else None,
                "detail": ("array 인데 링크가 %s 다. 🔒 §R26.1: **array 태스크 예산은 "
                           "`cores × max_wall_h` 를 넘지 않는다. 넘으면 링크를 늘리지 말고 "
                           "태스크를 쪼갠다.** 체이닝은 직렬 의존이 있는 항목(P1) 전용이다 — "
                           "array 를 체이닝하면 천장이 계단식으로 뛴다.\n"
                           "         🔴 단 P1b 는 종을 가로질러 쪼갤 수 없다"
                           "(`r_composite=(A+C)/A` 가 태스크 경계에 잘린다, §R22.8). "
                           "wall 상한이 낮아서 생긴 것이라면 **더 긴 큐를 쓰는 것이 1순위 "
                           "해법이다**(§R24.2(1))." % e.get("chain_links"))})

    # (c) 총 천장이 가드 안
    total = sum(e.get("reserved_core_hours") or 0.0 for e in live)
    if total > guard.max_core_hours + 1e-6:
        failures.append({"gate": "c_total_within_guard", "item": "(합계)",
                         "detail": "Σ 천장 %.1f > guard %.1f"
                                   % (total, guard.max_core_hours)})
    # 🔒 lead 판정 — **위반 항목만 막는다. 전량 차단은 틀린 실패 모드다.**
    #    근거: 24 h 큐에서 총액은 가드를 통과하고(17,555) 위반은 P1b 한 항목뿐인데,
    #    P5·P1·P6 는 24 h 에서 정상인 **독립 측정**이다. 그것들까지 막으면
    #    🔴 **사용자가 왕복 하나(3.5일)를 쓰고 아무것도 못 받는다.**
    #    ⟹ 항목 단위 실패는 그 항목만, 전역 실패(c)만 전체를 막는다.
    blocked = sorted(set(f["item"] for f in failures
                         if f["gate"] != "c_total_within_guard"
                         and f["item"] in by_key))
    global_failure = [f for f in failures if f["gate"] == "c_total_within_guard"]
    return {"passed": not failures, "failures": failures,
            "blocked_items": blocked,
            "blocks_everything": bool(global_failure),
            "remedy": REMEDY_BY_GATE,
            "total_reserved_core_hours": round(total, 2),
            "guard_max_core_hours": guard.max_core_hours,
            "_note": ("🔒 §R26.4 게이트. 실패 시 제출하지 말고 4-튜플 표를 engineer 에게 "
                      "보내라. 숫자를 맞추려고 예산이나 guard 를 조정하지 마라.")}


def format_gate_failures(planned, gates):
    """게이트 실패를 **4-튜플 표와 함께** 사람이 읽는 형태로."""
    L = ["", "!" * 72,
         " 🔴 사양 게이트 실패 — **제출하지 않습니다** (§R26.4)", ""]
    for f in gates["failures"]:
        L.append("   [%s] %s" % (f["gate"], f["item"]))
        for line in f["detail"].splitlines():
            L.append("       " + line.strip())
    L.append("")
    L.append("   %-14s %6s %8s %6s %10s %10s"
             % ("항목", "코어", "wall_h", "링크", "천장", "전망"))
    for e in planned:
        if e["status"] != "planned" or e.get("reserved_core_hours") is None:
            continue
        L.append("   %-14s %6s %8.2f %6s %10.1f %10.1f"
                 % (e["key"], e.get("cores_per_node"), e.get("wall_h") or 0,
                    e.get("chain_links"), e["reserved_core_hours"],
                    e.get("expected_core_hours") or 0))
    L.append("   %-14s %6s %8s %6s %10.1f" % ("(합계)", "", "", "",
                                              gates["total_reserved_core_hours"]))
    L.append("")
    L.append("   🔴 숫자를 맞추려고 예산이나 guard 를 조정하지 마십시오.")
    L.append("      위 표를 그대로 보고하시면 됩니다.")
    L.append("!" * 72)
    return "\n".join(L)


def resolve_wall_limit(env, guard, max_wall_h=None, submit_queue=None):
    """wall 상한을 **큐에서 읽는다.** 문서값을 코드에 박지 않는다.

    🔴 왜: `normal` 의 48 h 는 `[LITERATURE — 사이트 문서]` 이지 실측이 아니다. 그리고
    우리는 **이미 같은 형태로 당했다** — 파티션을 `sinfo`(SLURM 전용)에서만 읽어서
    PBS 클러스터에서 `#PBS -q` 가 통째로 빠졌다. **가정한 값이 조용히 틀리는 경로다.**

    🔴 그리고 지금 이 코드가 **정확히 그 상태였다**: `sysprobe` 가 `qstat -Qf <queue>` 로
    `resources_max.walltime` 을 **이미 수집해 `env["queue_info"]` 에 넣어두는데,
    `build_plan` 은 그것을 보지 않고 `partition_max_wall_h`(=sinfo 유래, PBS 에선 항상 None)
    만 봤다.** 측정해 놓고 안 쓰는 값이 또 하나 있었다 — `host` 유실과 같은 형태다.

    우선순위: 명시 인자 > **큐 실측(`qstat -Qf`)** > 파티션(`sinfo`) > 우리 캡.
    어느 경우든 **우리 캡(guard.max_wall_h)을 넘지 않는다.**

    🔴 아무것도 못 읽으면 **조용히 우리 캡을 쓰지 않는다.** 크게 경고하고
    `[UNVERIFIED]` 로 표시한다(ADR-036: 폴백은 보이게).
    """
    cap = float(guard.max_wall_h)
    qinfo = env.get("queue_info") or {}
    measured = qinfo.get("max_walltime_h")
    measured_queue = qinfo.get("queue")
    # 🔒 §R24.2(1) — **큐 하나 보고 24 h 라 단정하지 마라.** 이 사이트에는 `long` 이 있다
    #    `[LITERATURE]`. 전체 큐 중 walltime 이 가장 긴 것(사용 가능한 것)을 고른다.
    #    비용 0 이고, 이것이 24 h 문제의 1순위 해법이다.
    #    🔴 [critic3 치명적-2] 예전 판은 여기서 **가장 긴 큐의 wall 을 그냥 채택**했다.
    #    그런데 실제 `-q` 는 `cli.resolve_partition()` 이라는 **완전히 별도 경로**로 정해진다
    #    (`--queue` > sinfo > config/accounts.json). 즉 **sizing 은 `long`(120 h)을 가정해
    #    게이트를 통과시키고, 제출은 `-q normal`(24 h)로 나갈 수 있었다.**
    #    ⟹ 게이트가 "안전하다"고 말한 잡이 **24 h 에서 wall-kill** 된다.
    #    🔴 그리고 그 무력화는 **`long` 큐가 실존하는 순간**, 즉 우리가 가장 기대를 거는
    #    바로 그 상황에서 일어난다.
    #
    #    🔒 그래서 **"게이트가 보는 큐 == 제출이 가는 큐"** 로 고정한다.
    #    더 긴 큐가 있으면 **자동으로 갈아타지 않고 알린다** — 어느 큐로 제출할지는
    #    사이트 정책(과금·접근권)이 걸린 문제라 코드가 조용히 정할 일이 아니다.
    # 🔒 ADR-052 (사용자 직접 확인) — **큐는 `normal` 하나만 쓴다.**
    #    사용자 원문: *"`long` 은 존재하지만 **`normal` 이 48 h** 야.
    #                 **`long` 큐는 사용하지 않을 거고 `normal` 만 사용**할 거야."*
    #
    #    🔴 그래서 "가장 긴 큐를 고르는" 로직을 **배선하지 않고 지웠다.**
    #    critic3 가 찾은 것: 그 로직이 고른 `queue_selected` 를 **읽는 코드가 패키지 전체에
    #    0곳**이었고, 실제 `-q` 는 `accounts.json` 의 `queue_default` 로 별도로 정해졌다.
    #    ⟹ sizing 은 `long`(120 h)을 가정해 게이트를 통과시키고 제출은 `normal` 로 나가
    #      **안전장치가 가장 필요한 순간에 꺼지는** 상태였다.
    #    ⟹ lead 판정: *"가장 안전한 코드는 없는 코드다. 발동 조건이 사라진 기능을
    #      배선하는 것은 표면적만 늘린다."*
    #
    #    🔒 **되살리는 법**(다른 사이트로 이식할 때 필요하다):
    #      `sysprobe.longest_wall_queue(env["queues"])` 로 가장 긴 큐를 고르고,
    #      **반드시 그 큐를 실제 제출 `-q` 로도 쓰라**(`cli.resolve_partition`).
    #      둘을 따로 두면 이번과 같은 발산이 다시 생긴다.
    #
    #    🟢 다만 **wall 상한은 계속 읽는다**(ADR-036: 측정 가능한 것을 하드코딩하지 않는다).
    #      사용자 말과 클러스터가 다를 수 있고, **그때 우리가 알아야 한다.**
    queues = env.get("queues") or []
    by_name = dict((q.get("queue"), q) for q in queues if q.get("queue"))
    if submit_queue and submit_queue in by_name \
            and by_name[submit_queue].get("max_walltime_h") is not None:
        measured = by_name[submit_queue]["max_walltime_h"]
        measured_queue = submit_queue
    # 🔴 사용자 진술(48 h)과 클러스터 실측이 다르면 **크게 알린다.**
    #    다르면 §R22/§R24 의 wall 계산 전제가 무너진다.
    wall_surprise = None
    if measured is not None and abs(float(measured) - EXPECTED_QUEUE_WALL_H) > 1e-6:
        wall_surprise = (
            "🔴 큐 `%s` 의 walltime 상한이 **%.1f h** 다 — 사용자가 확인해 준 값 %.1f h "
            "(ADR-052)와 다르다. §R22/§R24 의 wall 계산이 그 전제 위에 서 있으므로 "
            "**계획을 다시 보라.** 게이트가 항목을 막으면 그것이 원인일 수 있다."
            % (measured_queue or "?", float(measured), EXPECTED_QUEUE_WALL_H))
    longer_available = None      # ADR-052 로 큐 선택을 하지 않는다
    partition_wall = env.get("partition_max_wall_h")
    if max_wall_h:
        src, basis, verified = "explicit_argument", "호출자가 명시한 값", True
        limit = float(max_wall_h)
    elif measured:
        src = "queue_measured"
        basis = ("`qstat -Qf` 에서 고른 큐 `%s` 의 resources_max.walltime = %.2f h "
                 "[MEASURED] (사용 가능한 큐 중 walltime 최장)"
                 % (measured_queue or "?", float(measured)))
        verified, limit = True, float(measured)
    elif partition_wall:
        src = "partition_probe"
        basis = "스케줄러 파티션 조회 %.2f h [MEASURED]" % float(partition_wall)
        verified, limit = True, float(partition_wall)
    else:
        src = "our_cap_unverified"
        basis = ("🔴 큐의 wall 상한을 읽지 못했다(`qstat -Qf` 실패 또는 미지원). "
                 "우리 캡 %.2f h 를 쓴다 — 이것은 **사이트 상한이 아니라 우리가 정한 값**이고 "
                 "[UNVERIFIED] 다. 사이트 상한이 더 낮으면 잡이 거부되거나 잘린다. "
                 "확인 명령: `qstat -Qf <큐이름>`" % cap)
        verified, limit = False, cap
    used = min(limit, cap)
    return {
        "max_wall_h_used": used,
        "wall_limit_source": src,
        "wall_limit_basis": basis,
        "wall_limit_verified": verified,
        "queue_reported_max_wall_h": float(measured) if measured else None,
        # 🔒 [critic3 치명적-2] 이 값은 **실제 제출 큐와 같아야 한다.**
        "queue_selected": measured_queue,
        "submit_queue": submit_queue,
        "queue_matches_submit": (submit_queue is None or measured_queue == submit_queue),
        "longer_queue_available": longer_available,
        "queue_wall_surprise": wall_surprise,
        "queues_seen": [q.get("queue") for q in (env.get("queues") or [])],
        "our_cap_h": cap,
        "capped_by_us": bool(limit > cap),
    }


def build_plan(env, guard=None, items=None, cores_per_node=None, max_wall_h=None,
               qc_level=None, account_resolver=None,
               profile=PROFILE_CPU, submit_queue=None, ncpus_override=None):
    """dry-run과 실제 제출이 **같은 함수**를 쓴다. 두 경로가 갈리면 dry-run이 거짓말을 한다."""
    guard = guard or budget_mod.ResourceGuard()
    items = items if items is not None else default_items(profile)
    cpn = cores_per_node or env.get("cores_per_node") or 32
    cpn_assumed = not (cores_per_node or env.get("cores_per_node"))
    # 🔒 [critic3 중대] override 를 **계획 시점에** 반영한다. 예전에는 제출 시점에만
    #    적용돼 계획 표·게이트가 덮이기 전 값을 봤다.
    if ncpus_override is None:
        ncpus_override = ncpus_override_from_config(None)
    if ncpus_override:
        cpn = int(ncpus_override)
        cpn_assumed = False
    wall_limit = resolve_wall_limit(env, guard, max_wall_h, submit_queue)
    max_wall = wall_limit["max_wall_h_used"]

    # 계정 해석기가 없으면 설정 기본값으로 만든다(호출부가 잊어도 표가 비지 않게).
    if account_resolver is None:
        account_resolver = accounts_mod.Resolver()

    planned = []
    runnable_keys = set()
    for item in sorted(items, key=lambda x: x.priority):
        entry = {
            "key": item.key, "title": item.title, "priority": item.priority,
            "core_hours_budget": item.core_hours_budget,
            "gpu_hours_budget": item.gpu_hours,
            "nodes": item.nodes, "cores_per_node": cpn,
            "array": item.array, "gpus": item.gpus,
            "payload": item.payload, "rationale": item.rationale,
            "extra_env": dict(item.extra_env),
            "cores_per_task": item.cores_per_task,   # [ADR-113] digest field, the Item's own
            # 🔴 계정은 소프트웨어 단위다. 문자열은 config/accounts.json 에서 온다.
            "account_key": item.account_key,
            "account": account_resolver.account_for(item.account_key),
            "account_unconfirmed": not account_resolver.is_confirmed(item.account_key),
            "status": "planned", "skip_reason": None, "tools": {},
        }
        ok, reason, tools = check_requirements(item, env)
        entry["tools"] = tools
        if not ok:
            entry["status"] = "skipped"
            entry["skip_reason"] = reason[0]
            if item.fallback_hint:
                entry["fallback_hint"] = item.fallback_hint
            planned.append(entry)
            continue
        missing_dep = [d for d in item.depends_on if d not in runnable_keys]
        if missing_dep:
            entry["status"] = "skipped"
            entry["skip_reason"] = ("선행 항목 미실행: %s" % ", ".join(missing_dep))
            planned.append(entry)
            continue

        wall, links, reserved = size_job(item.core_hours_budget, cpn,
                                         item.nodes, max_wall, item.min_wall_h)
        if item.key == "probe_queuewait":
            # 🔴 표시·예약을 **실제로 제출되는 분해**에서 유도한다.
            #
            #    이전: nodes=85(=1+4+16+64 합계) × cpn × 예산역산 wall → 250 core-h.
            #    그런데 상한(max_probe_nodes)이 적용돼 **실제로는 1+4+16 = 21 노드**만
            #    나간다. 표는 85를, 예약은 그 85 기준 값을 말하고 있었다.
            #    🔴 lead 가 표의 85 를 보고 "85노드가 거부됐다"는 **틀린 지시**를 보냈다.
            #    engineer 는 이 값으로 봉투를 계산한다. 오표시의 대가가 이미 발생했다.
            #
            #    wall 도 예산에서 역산하지 않는다 — payload 는 `sleep 60` 이고 필요한
            #    것은 "큐에서 언제 시작되는가"뿐이다. 예산은 **상한**이지 목표가 아니다.
            #    ⇒ wall = min_wall_h(선언된 필요시간), 예약 = 실제 노드합 × cpn × wall.
            #    이 값은 **스케줄러가 강제하는 상한과 정확히 같다**(노드수·wall 고정).
            decomp = queue_wait_decomposition(env)
            n_nodes = sum(decomp["node_counts"])
            wall = max(item.min_wall_h or MIN_WALL_H, 1.0 / 60.0)
            links = 1
            reserved = round(units.core_hours_h(n_nodes * cpn, wall), 2)
            entry["nodes"] = n_nodes
            entry["queue_wait_decomposition"] = {
                "node_counts_submitted": decomp["node_counts"],
                "dropped_by_cap": decomp["dropped_by_cap"],
                "dropped_too_large_for_cluster":
                    decomp["dropped_too_large_for_cluster"],
                "cap": decomp["cap"],
                "_why": ("상한을 모르는 큐에 큰 잡을 던지면 거부되고 그러면 측정이 0이 "
                         "된다. 상한은 config/sizing.json 의 pbs.max_probe_nodes."),
                "_reservation_basis": (
                    "노드합 %d × %d core/node × %.4f h. 사이트가 **노드 단위로 과금**한다고 "
                    "보수적으로 가정했다. 코어 단위 과금이면 실제 소비는 이보다 %d배 작다."
                    % (n_nodes, cpn, wall, cpn)),
            }
        elif item.array:
            # 🔴 예전에는 여기서 **태스크당 1코어**가 하드코딩돼 있었다.
            #    `probe_throughput`(200 × 1분 × 1코어)에는 옳았지만, §R22 가 P5·P1b 를
            #    array 로 바꾸면서 그 가정을 그대로 물려받았다 — P5 최대 종이 1코어면
            #    wall 이 496 h 가 되어 48 h 큐에서 즉사한다.
            #    ⟹ 태스크당 코어 수를 항목이 선언하고, 예산·wall·천장·`select=` 가
            #      전부 그 값에서 파생된다.
            n_tasks = item.array[1] - item.array[0] + 1
            per_task_cores = (item.task_cores if item.task_cores
                              else (item.cores_per_task
                                    if item.cores_per_task is not None else cpn))
            budgets = (item.task_budgets if item.task_budgets
                       else [item.core_hours_budget / float(n_tasks)] * n_tasks)
            tasks = size_tasks(budgets, per_task_cores, max_wall,
                               item.min_wall_h, item.explicit_wall_h)
            agg = summarize_tasks(tasks)
            wall = agg["wall_h"]
            links = agg["chain_links"]
            reserved = agg["reserved_core_hours"]
            entry["cores_per_node"] = (per_task_cores if isinstance(per_task_cores, int)
                                       else None)
            entry["tasks"] = tasks
            entry["expected_core_hours"] = agg["expected_core_hours"]
            entry["node_hours"] = agg["node_hours"]
        else:
            job_cores = (item.cores_per_task if item.cores_per_task is not None
                         else cpn * item.nodes)
            # 🔴 P6 의 코어 수는 **측정 대상**이라 사이트 override 를 받지 않는다.
            if item_cores_are_the_measurement(item) and item.cores_per_task:
                job_cores = item.cores_per_task
            tasks = size_tasks([item.core_hours_budget], job_cores,
                               max_wall, item.min_wall_h, item.explicit_wall_h)
            agg = summarize_tasks(tasks)
            wall, links = agg["wall_h"], agg["chain_links"]
            reserved = agg["reserved_core_hours"]
            # 🔴 예약을 계산한 코어 수와 **표시·제출에 쓰는 코어 수가 갈리면 안 된다.**
            #    P6 는 1/16/64 스레드를 요청하는데 표에는 64 로 찍히고 있었다 —
            #    "보이는 것과 보내는 것이 다르다"가 이 패키지에서 세 번 났다.
            if item.cores_per_task is not None:
                entry["cores_per_node"] = item.cores_per_task
            entry["tasks"] = tasks
            entry["expected_core_hours"] = agg["expected_core_hours"]
            entry["node_hours"] = agg["node_hours"]
        entry.setdefault("expected_core_hours", item.core_hours_budget)
        entry.update({"wall_h": wall, "chain_links": links,
                      "reserved_core_hours": reserved,
                      # 🔒 §R24.1 — 두 통화를 절대 섞지 않는다. 정의를 값 옆에 싣는다.
                      "core_hour_field_definitions": CORE_HOUR_FIELD_DEFINITIONS})
        if entry.get("queue_wait_decomposition", {}).get("dropped_by_cap"):
            # 🔴 생략을 숨기지 않는다. engineer 가 "왕복 지연 모델의 유일한 실측
            #    입력"이라 한 항목이다 — 축소가 안 보이면 받는 쪽이 원래 설계대로 읽는다.
            entry["note"] = ("%s node 생략(상한 %d)"
                             % (entry["queue_wait_decomposition"]["dropped_by_cap"],
                                entry["queue_wait_decomposition"]["cap"]))

        accepted = guard.reserve(item.key, core_hours=reserved,
                                 gpu_hours=item.gpu_hours, wall_h=wall)
        if not accepted:
            rej = guard.rejection(item.key) or {}
            entry["status"] = "skipped"
            entry["skip_reason"] = "%s: %s" % (rej.get("reason"), rej.get("detail"))
            planned.append(entry)
            continue
        runnable_keys.add(item.key)
        planned.append(entry)

    summary = {
        "profile": profile,
        # 어느 레벨로 도는지 보이지 않으면 사용자가 확인할 방법이 없다.
        "qc_level": qc_level,
        "account_warnings": account_resolver.warnings(
            [p["account_key"] for p in planned]),
        "queue_default": accounts_mod.default_queue(),
        "cores_per_node_used": cpn,
        "ncpus_override_applied": ncpus_override,
        "cores_per_node_assumed": cpn_assumed,
        # 🔴 이 값의 **출처**가 무엇인지가 sizing 신뢰도의 전부다.
        "cores_per_node_source": env.get("cores_per_node_source"),
        "cores_per_node_login": env.get("cores_per_node_login"),
        "cores_per_node_compute": env.get("cores_per_node_compute"),
        "cores_per_node_is_login_fallback":
            bool(env.get("cores_per_node_is_login_fallback")),
        "max_wall_h_used": max_wall,
        # 🔴 wall 상한이 **어디서 왔는지**. 48 h 를 문서에서 베껴 박는 대신 큐에서 읽는다.
        #    출처를 안 실으면 다음 사람이 `[LITERATURE]` 를 `[MEASURED]` 로 인용한다.
        "wall_limit_source": wall_limit["wall_limit_source"],
        "queue_selected": wall_limit["queue_selected"],
        "submit_queue": wall_limit["submit_queue"],
        "queue_matches_submit": wall_limit["queue_matches_submit"],
        "longer_queue_available": wall_limit["longer_queue_available"],
        "queue_wall_surprise": wall_limit["queue_wall_surprise"],
        "wall_limit_basis": wall_limit["wall_limit_basis"],
        "wall_limit_verified": wall_limit["wall_limit_verified"],
        "queue_reported_max_wall_h": wall_limit["queue_reported_max_wall_h"],
        "n_planned": sum(1 for p in planned if p["status"] == "planned"),
        "n_skipped": sum(1 for p in planned if p["status"] == "skipped"),
        "reserved_core_hours": round(guard.reserved_core_hours, 2),
        "reserved_gpu_hours": round(guard.reserved_gpu_hours, 3),
        "guard": guard.to_dict(),
    }
    # 🔒 §R26.4 — 게이트 결과는 **계획 산출물의 일부**다(회신 JSON 에도 실린다).
    summary["sizing_gates"] = sizing_gates(planned, guard)
    # 🔒 위반 항목만 실행 대상에서 뺀다(전량 차단 금지, lead 판정).
    #    status 를 "skipped" 로 두는 이유: 기존 소비자(collect/report/제출 루프)가 전부
    #    그 값을 이해한다. **새 상태값을 만들면 그것을 모르는 경로가 조용히 생긴다** —
    #    이 패키지에서 이미 여러 번 난 형태다. 대신 `blocked_by_gate` 로 구분한다.
    gate_reasons = {}
    for f in summary["sizing_gates"]["failures"]:
        gate_reasons.setdefault(f["item"], []).append(f)
    for entry in planned:
        if entry["key"] not in summary["sizing_gates"]["blocked_items"]:
            continue
        fs = gate_reasons.get(entry["key"], [])
        entry["status"] = "skipped"
        entry["blocked_by_gate"] = True
        entry["gate_failures"] = fs
        entry["remedy"] = " / ".join(
            REMEDY_BY_GATE.get(f["gate"], "") for f in fs).strip(" /")
        entry["skip_reason"] = ("sizing_gate:%s — %s"
                                % (",".join(f["gate"] for f in fs),
                                   fs[0]["detail"].splitlines()[0] if fs else ""))
    # 🔴 예약(천장)은 그대로 둔다. 차단된 항목의 예약을 빼면 총액이 **낙관** 쪽으로
    #    움직이는데, 가드는 보수적이어야 한다. 대신 그 사실을 밝힌다.
    if summary["sizing_gates"]["blocked_items"]:
        summary["sizing_gates"]["_reservation_note"] = (
            "차단된 항목의 예약(천장)은 합계에서 빼지 않았다. 가드는 낙관 쪽으로 "
            "움직이면 안 되기 때문이다 — 실제 소비는 이보다 작다.")
    return planned, summary


def format_plan_text(planned, summary, env):
    """dry-run 리포트. 사용자가 이것만 보고 제출 여부를 판단할 수 있어야 한다."""
    L = []
    L.append("=" * 74)
    L.append(" SEI 파일럿 인도 패키지 [%s 프로파일] — 실행 계획 (dry-run)"
             % summary.get("profile", "?").upper())
    L.append("=" * 74)
    L.append(" 호스트      : %s" % env.get("hostname"))
    L.append(" 스케줄러    : %s" % env.get("scheduler"))
    L.append(" core/node   : %s   (출처: %s)"
             % (summary["cores_per_node_used"],
                summary.get("cores_per_node_source") or
                ("감지 실패 → 가정값" if summary["cores_per_node_assumed"] else "?")))
    if summary.get("cores_per_node_is_login_fallback"):
        L.append(" " + "!" * 70)
        L.append(" ! 🔴 계산 노드 사양을 조회하지 못해 **로그인 노드 값**으로 계산했다.")
        L.append(" !   이기종 클러스터라면 wall·자원 예약이 전부 어긋난다.")
        L.append(" !   → 계산 노드의 코어 수를 아신다면:  ./run.sh --cores-per-node <N>")
        L.append(" " + "!" * 70)
    elif (summary.get("cores_per_node_login")
          and summary.get("cores_per_node_compute")
          and summary["cores_per_node_login"] != summary["cores_per_node_compute"]):
        L.append("               (로그인 노드는 %s — 계산 노드 값으로 sizing 했다)"
                 % summary["cores_per_node_login"])
    L.append(" wall 상한   : %.2f h  (%s)"
             % (summary["max_wall_h_used"],
                "큐 실측" if summary.get("wall_limit_source") == "queue_measured"
                else summary.get("wall_limit_source", "?")))
    if summary.get("queue_matches_submit") is False:
        # 🔴 이 경고가 뜨면 **게이트가 거짓말을 하고 있다.** 절대 조용히 넘기지 않는다.
        L.append(" " + "!" * 70)
        L.append(" ! 🔴 sizing 이 본 큐(%s)와 실제 제출 큐(%s)가 다릅니다."
                 % (summary.get("queue_selected"), summary.get("submit_queue")))
        L.append(" !   wall 상한 판정이 실제 제출과 어긋나므로 그대로 두면 wall-kill 됩니다.")
        L.append(" " + "!" * 70)
    if summary.get("queue_wall_surprise"):
        # 🔴 사용자 진술과 클러스터가 다르다. wall 계산 전제가 무너진 상태다.
        L.append(" " + "!" * 70)
        L.append(" ! " + summary["queue_wall_surprise"])
        L.append(" " + "!" * 70)
    if summary.get("wall_limit_verified") is False:
        # 🔴 조용히 우리 캡을 쓰지 않는다. `-q` 누락이 조용히 났던 것과 같은 자리다.
        L.append(" " + "!" * 70)
        L.append(" ! 🔴 큐의 wall 상한을 **확인하지 못했다** [UNVERIFIED]")
        L.append(" !   " + summary.get("wall_limit_basis", ""))
        L.append(" !   사이트 상한이 우리 값보다 낮으면 잡이 거부되거나 잘립니다.")
        L.append(" " + "!" * 70)
    L.append(" GPU         : %s" % ("있음 (%s x%s)" % (
        (env.get("gpus") or {}).get("model"), (env.get("gpus") or {}).get("count"))
        if (env.get("gpus") or {}).get("present") else "없음"))
    L.append("")
    # 🔴 `-A` 를 표에 넣는다. 계정이 항목마다 다른 클러스터에서 **제출 전에 눈으로
    #    확인할 수 있어야** 한다 — 계정 하나 틀려서 전 항목이 거부되는 것이 지금
    #    가장 큰 인도 위험이다.
    L.append(" %-16s %-7s %-9s %5s %6s %5s %9s  %s"
             % ("ITEM", "STATUS", "-A", "NODES", "WALL", "LINK", "core-h", "비고"))
    L.append(" " + "-" * 78)
    for p in planned:
        if p["status"] == "planned":
            L.append(" %-16s %-7s %-9s %5s %6.2f %5d %9.1f  %s"
                     % (p["key"], "RUN", (p.get("account") or "-")
                        + ("*" if p.get("account_unconfirmed") else ""),
                        p["nodes"], p.get("wall_h", 0),
                        p.get("chain_links", 1), p.get("reserved_core_hours", 0),
                        # 🔴 생략된 잡을 숨기지 않는다 — 비고에 실어 화면에서 보인다.
                        ((p["title"][:24] + "  ⚠ " + p["note"])
                         if p.get("note") else p["title"][:24])))
        else:
            L.append(" %-16s %-7s %-9s %5s %6s %5s %9s  %s"
                     % (p["key"], "SKIP", (p.get("account") or "-")
                        + ("*" if p.get("account_unconfirmed") else ""),
                        "-", "-", "-", "-", (p["skip_reason"] or "")[:40]))
    L.append(" " + "-" * 78)
    if summary.get("account_warnings"):
        L.append("")
        L.append(" 계정(`-A`) 확인:")
        L.extend(summary["account_warnings"])
        L.append("   * 표시는 **미확인(저희 추정)** 이라는 뜻입니다. 나머지는 확인된 값입니다.")
    if summary.get("qc_level"):
        L.append(" 계산 레벨   : %s" % summary["qc_level"])
    L.append(" 예약 합계   : %.1f core-h / 상한 %.1f core-h,  GPU %.2f / %.2f h"
             % (summary["reserved_core_hours"],
                summary["guard"]["max_core_hours"],
                summary["reserved_gpu_hours"],
                summary["guard"]["max_gpu_hours"]))
    dropped = [r for r in summary["guard"]["skipped_for_budget"]]
    blocked = [e for e in planned if e.get("blocked_by_gate")]
    if blocked:
        # 🔴 조용히 빠지면 그게 "조용한 실패" 여덟 번째다. 화면에서도 크게 말한다.
        L.append("")
        L.append(" " + "!" * 70)
        L.append(" ! 🔴 사양 게이트로 **이번에 실행되지 않는 항목**: %s"
                 % ", ".join(e["key"] for e in blocked))
        L.append(" !   (나머지 항목은 정상 제출됩니다 — 위반 항목만 빠집니다.)")
        for e in blocked:
            L.append(" !")
            L.append(" !   [%s] %s" % (e["key"], e.get("skip_reason", "")[:100]))
            for line in (e.get("remedy") or "").split(" / "):
                if line.strip():
                    L.append(" !     → 해결: " + line.strip())
        L.append(" " + "!" * 70)
    if dropped:
        L.append("")
        L.append(" " + "!" * 70)
        # 🔒 §R27 — 가드가 거부하면 **4-튜플 표 전체 + 어느 항목이 넘겼는지**를 낸다.
        #    🔴 이유: *"반사적 반응이 '숫자를 올린다'가 아니라 '어느 항목을 의심한다'가
        #    되도록."* 예전 판은 여기서 `--max-core-hours <더 큰 값>` 을 권했는데,
        #    그것이 §R24.1 이 기각한 거래(**물리적 상한을 예상치로 격하**)로 가는 문이다.
        #    그리고 여기 박혀 있던 `~3,150 core-h` 는 이미 낡은 리터럴이었다.
        L.append(" ! 🔴 자원 가드가 거부한 항목: %s"
                 % ", ".join(d["id"] for d in dropped))
        L.append(" !   상한 %.0f core-h [물리 천장] / 이번 계획의 예약 합계 %.0f core-h"
                 % (summary["guard"]["max_core_hours"], summary["reserved_core_hours"]))
        L.append(" !")
        L.append(" !   %-14s %6s %8s %6s %10s %10s"
                 % ("항목", "코어", "wall_h", "링크", "천장", "전망"))
        for e in planned:
            if e.get("reserved_core_hours") is None:
                continue
            L.append(" !   %-14s %6s %8.2f %6s %10.1f %10.1f%s"
                     % (e["key"], e.get("cores_per_node"), e.get("wall_h") or 0,
                        e.get("chain_links"), e.get("reserved_core_hours") or 0,
                        e.get("expected_core_hours") or 0,
                        "   <-- 거부됨" if any(d["id"] == e["key"] for d in dropped)
                        else ""))
        L.append(" !")
        L.append(" !   🔴 **가드를 올리기 전에 사양을 의심하십시오** (§R24.1).")
        L.append(" !   천장 = 코어 × wall × 링크 입니다. 천장이 전망보다 훨씬 크면")
        L.append(" !   그 항목의 `min_wall_h` 바닥값이나 링크 절상이 부풀린 것입니다.")
        L.append(" !   🔒 사전 확약된 절단 순서: P7(게이트 미통과) → P3(이미 측정)")
        L.append(" !      → P6 의 1스레드 태스크 → 그 다음은 engineer/lead 판단.")
        L.append(" !   (생략 사유는 결과 JSON 에 남습니다. --max-core-hours 로 올릴 수는")
        L.append(" !    있으나, 그것은 **스케줄러가 강제하던 상한을 예상치로 격하**시킵니다.)")
        L.append(" " + "!" * 70)
    L.append("")
    return "\n".join(L)
