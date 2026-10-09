"""진입점. `run.sh`가 이것만 부른다.

서브커맨드
  preflight  로그인 노드에서 5분 내. 환경 검사 + 계획 출력. **제출 없음.**
  submit     preflight 후 실제 제출 + collector 잡을 afterany로 미리 체인
  collect    잡 아티팩트 수집 → results/sei_probe_report.json
  status     마커 현황

멱등성: submit을 몇 번 다시 돌려도 완료/제출된 항목은 다시 제출되지 않는다.
48 h wall(ADR-114)에 잘려도 `./run.sh` 재실행이 이어서 진행한다.
"""

import argparse
import json
import os
import sys
import time

from . import budget as budget_mod
from . import collect as collect_mod
from . import plan as plan_mod
# 🔴 큐 대기 프로브의 노드 분해는 plan.py 가 소유한다 — 표시·예약·사전검사·
#    실제 제출 **네 곳**이 같은 함수를 봐야 한다(순환 import 방지 위해 plan 쪽).
from .plan import QUEUE_WAIT_NODE_COUNTS, queue_wait_decomposition
from . import report as report_mod
from . import scheduler as sched_mod
from . import accounts as accounts_mod
from . import outcome as outcome_mod
from . import config, envpaths, sysprobe, version
from .shellrun import Shell
from .state import Store, spec_digest, physics_env

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
THROUGHPUT_N_TASKS = 200


# --------------------------------------------------------------------------
def detect_containers(pkg_root, shell):
    """동봉된 Apptainer .sif 탐지 (§R2-6 D-3: 컨테이너 우선).

    🔴 현 시점 이 패키지에는 .sif가 **동봉돼 있지 않다.** 우리 개발 환경에
    apptainer가 없어 빌드할 수 없었기 때문이다(README 참조).
    사용자가 containers/ 에 .sif를 넣고 manifest.json을 채우면 자동으로 쓰인다.
    """
    cdir = os.path.join(pkg_root, "containers")
    runtime = shell.which("apptainer") or shell.which("singularity")
    if not runtime or not os.path.isdir(cdir):
        return {}
    manifest_path = os.path.join(cdir, "manifest.json")
    mapping = {}
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as fh:
                mapping = json.load(fh)
        except (OSError, ValueError):
            mapping = {}
    out = {}
    for tool, sif in mapping.items():
        path = sif if os.path.isabs(sif) else os.path.join(cdir, sif)
        if os.path.exists(path):
            out[tool] = {"sif": path, "runtime": runtime}
    return out


def detect_vendored(pkg_root, names=("xtb",)):
    """동봉 바이너리 탐지. 파일이 없으면 조용히 비운다(패키지가 가벼울 수도 있다)."""
    out = {}
    for n in names:
        v = envpaths.vendored(n, pkg_root)
        if v:
            out[n] = v["path"]
    return out


def build_env(shell, pkg_root, queue_hint=None, cores_per_node_override=None,
              args_ns=None):
    """계획 수립에 필요한 환경 사실만 모은다 (로그인 노드, 5분 이내).

    🔴 **로그인 노드 사양으로 계산 노드 잡을 sizing 하면 안 된다.**
    사용자 실측: 로그인 24 core / 계산 68 core(64 사용) — **2.7배 차이**.
    그 값으로 wall·links·core-h 예약을 계산하면 잡이 wall에 잘리거나 자원이 어긋나
    왕복 1회(3.5일)를 날린다. 그래서 출처를 분리해 라벨과 함께 들고 다닌다.
    """
    login = sysprobe.collect_login(shell, queue_hint=queue_hint)
    scheduler = sched_mod.detect(shell)
    login["scheduler"] = scheduler

    partitions = login.get("partitions") or []
    login_cpu = login.get("login_cpu") or {}
    cores_login = login_cpu.get("physical_cores") or login_cpu.get("cpus")

    # --- 계산 노드 사양 (출처별로 따로 본다) ---
    cores_compute, source = None, None
    for p in partitions:                     # SLURM: sinfo %c 가 계산 노드 값이다
        if p.get("cores_per_node"):
            cores_compute = max(cores_compute or 0, p["cores_per_node"])
            source = "sinfo(partition)"
    cn = login.get("compute_nodes") or {}
    if not cores_compute and cn.get("cores_per_node"):   # PBS: pbsnodes
        cores_compute = cn["cores_per_node"]
        source = cn.get("source", "pbsnodes")

    # 🔴 감지값이 곧 요청 가능한 값은 아니다. 68 core 시스템에서 64 만 쓰는 것처럼
    #    사이트 정책으로 일부가 빠져 있을 수 있고, 감지값 그대로 요청하면 잡이
    #    **영원히 스케줄되지 않는다**(자원 부족으로 큐에 머문다).
    #    변환표는 config/sizing.json 한 곳에서 온다.
    cores_detected = cores_compute
    usable_note = None
    if cores_compute:
        table = ((config.load("sizing.json", {}).get("usable_cores") or {})
                 .get("map") or {})
        mapped = table.get(str(int(cores_compute)))
        if mapped and int(mapped) != int(cores_compute):
            usable_note = ("감지 %d → 요청 %d (사이트 정책, config/sizing.json)"
                           % (cores_compute, int(mapped)))
            cores_compute = int(mapped)

    if cores_per_node_override:
        cores_per_node = int(cores_per_node_override)
        source = "--cores-per-node (사용자 지정)"
    elif cores_compute:
        cores_per_node = cores_compute
        if usable_note:
            source = "%s / %s" % (source, usable_note)
    else:
        cores_per_node = cores_login
        source = "🔴 로그인 노드 값 (계산 노드 사양을 조회하지 못했다)"

    # 🔴 **바이너리를 찾았더라도 module 탐지를 항상 시도한다.**
    #    예전에는 `if not software["g16"]` 조건이 걸려 있어서, 로그인 PATH 에 g16 이
    #    보이면 module 탐지를 건너뛰었다. 그 결과 잡 스크립트에 `module load` 가
    #    안 들어갔고 **계산 노드에서 P1/P1b/P5 가 전부 rc=3 으로 죽었다.**
    #    모듈은 계산 노드용으로 만들어진 것이므로 있으면 그것을 쓴다.
    qc_module = None
    try:
        qc_module = envpaths.resolve_qc_via_module(
            shell, login.get("modules") or [],
            preferred=getattr(args_ns, "gaussian_module", None)
            if args_ns is not None else None)
    except Exception as exc:                     # 탐지 실패가 전체를 죽이면 안 된다
        qc_module = {"module": None, "error": "%s: %s"
                     % (type(exc).__name__, exc)}

    walls = [p["walltime_max_h"] for p in partitions if p.get("walltime_max_h")]
    env = {
        "hostname": login.get("hostname"),
        "scheduler": scheduler,
        "cores_per_node_login": cores_login,
        "cores_per_node_compute": cores_compute,
        "cores_per_node_detected": cores_detected,
        "cores_per_node_usable_note": usable_note,
        # 🔴 [MAJOR/lead 판정] 폴백 값은 **다른 키에 보존**한다. 버리지도 않고,
        #    `cores_per_node` 자리에 앉히지도 않는다. 회신 JSON 에서 그 자리는
        #    null 이 된다(아래 report 경로). 이유:
        #      로그인 24코어를 계산 노드 값으로 넘겨 engineer 가 §R16 한 라운드를
        #      통째로 그 위에 쓴 사고가 실제로 있었다(ADR-034).
        #      "[MEASURED] 는 '측정됐다'이지 '무엇을 측정했는지 안다'가 아니다."
        #    경고 문자열은 **사람만** 읽는다. null 은 **코드도** 읽는다.
        "cores_per_node_login_fallback": (
            cores_login if (not cores_compute and not cores_per_node_override)
            else None),
        "cores_per_node_source": source,
        "cores_per_node_is_login_fallback": bool(
            not cores_compute and not cores_per_node_override),
        "queue_info": login.get("queue_info"),
        # 🔒 §R24.2(1) — 큐 **전체**. `long` 이 있으면 wall 문제가 비용 0 으로 사라진다.
        "queues": login.get("queues"),
        "compute_nodes": cn,
        "software": login.get("software"),
        "software_probed": login.get("software_probed"),
        # 🔴 [생산자→소비자 검사가 잡은 것] 아래는 **이번 라운드에 내가 만들어 놓고
        #    아무도 안 읽던 값들**이다. ADR-043(module 전문)·ADR-050(엔진 정책)의
        #    존재 이유 그 자체인데 회신에 실리지 않고 있었다.
        #    **내가 고치던 병을 내가 그대로 저질렀다.**
        "software_probe_note": login.get("software_probe_note"),
        "engine_policy": login.get("engine_policy"),
        "modules_raw": login.get("modules_raw"),
        "modules_raw_note": login.get("modules_raw_note"),
        "queues_raw": login.get("queues_raw"),
        "login_user": login.get("user"),
        "modules": login.get("modules"),
        # 🔴 module 시스템을 통한 QC 탐지. 실제 클러스터에서 P1/P5/P1b 가 전부 SKIP
        #    된 원인이 여기였다 — HPC 의 Gaussian 은 `module load` 뒤에만 보인다.
        "qc_module": qc_module,
        "containers": detect_containers(pkg_root, shell),
        # 🔴 동봉 도구(vendor/). 클러스터에 없는 것을 되살린다.
        "vendored": detect_vendored(pkg_root),
        "gpus": (login.get("login_gpus") or {}),
        "cores_per_node": cores_per_node,
        "partition_max_wall_h": max(walls) if walls else None,
        "partitions": partitions,
        "_login": login,
    }
    if login.get("gpu_partitions"):
        env["gpus"] = dict(env["gpus"])
        env["gpus"]["present"] = True
    return env


def account_candidates(env):
    """sacctmgr assoc 에서 계정 후보를 뽑는다.

    🔴 대부분의 학술·국가 HPC는 `--account` 를 요구한다. 없으면 **모든 제출이 거부**되고
    왕복 1회(3.5일)가 통째로 날아간다. 사용자에게 묻기 전에 우리가 알아낸다.
    """
    accounts, qos = [], []
    for row in (env.get("_login") or {}).get("assoc") or []:
        acc = (row.get("account") or "").strip()
        if acc and acc not in accounts:
            accounts.append(acc)
        q = (row.get("qos") or "").strip()
        for item in q.split(","):
            item = item.strip()
            if item and item not in qos:
                qos.append(item)
    cfg = (env.get("_login") or {}).get("slurm_config") or {}
    enforce = str(cfg.get("AccountingStorageEnforce") or "")
    return {
        "accounts": accounts,
        "qos": qos,
        "enforce_raw": enforce,
        # 'associations' 가 포함되면 계정이 **강제**된다
        "account_required": ("associations" in enforce.lower()
                             or "safe" in enforce.lower()),
        "auto_selectable": accounts[0] if len(accounts) == 1 else None,
    }


def account_resolver(args, env=None):
    """항목별 계정 해석기. 🔴 계정 문자열의 출처는 config/accounts.json 한 곳뿐이다.

    전역 자동탐지(sacctmgr 후보 1개)는 **소프트웨어 매핑이 없는 사이트**를 위한
    하위호환 경로로만 남는다. 이 클러스터에서는 매핑이 이긴다.
    """
    global_value, per_key = accounts_mod.parse_overrides(getattr(args, "account", None))
    return accounts_mod.Resolver(global_override=global_value, overrides=per_key)


def resolve_account(args, env, verbose=True):
    """(하위호환) 전역 계정 1개를 쓰는 경로. 항목별 값은 account_resolver 를 쓴다."""
    info = account_candidates(env)
    globals_, _per = accounts_mod.parse_overrides(getattr(args, "account", None))
    if globals_:
        return globals_, info
    if info["auto_selectable"]:
        if verbose:
            print("  * 계정 자동 선택: %s (sacctmgr 에서 유일)" % info["auto_selectable"])
        return info["auto_selectable"], info
    if len(info["accounts"]) > 1 and verbose:
        print("  ! 계정이 여러 개다: %s" % ", ".join(info["accounts"]))
        print("    → 어느 것으로 제출할지 우리가 고를 수 없다. "
              "`./run.sh --account=<이름>` 으로 지정하라.")
    elif info["account_required"] and verbose:
        print("  ! 이 클러스터는 계정을 요구하는데(AccountingStorageEnforce=%s) "
              "후보를 찾지 못했다." % info["enforce_raw"])
        print("    → `sacctmgr -nP show assoc user=$USER format=Account,Partition,QOS`")
    return None, info


def resolve_partition(env, args=None):
    """(큐 이름, 출처) — 🔴 **`None` 을 쉽게 내주지 않는다.**

    사고 경위: `env["partitions"]` 는 **`sinfo` 로만** 채워지는데(sysprobe.py:432)
    `sinfo` 는 **SLURM 전용**이다. 대상은 PBS 전용 클러스터라 항상 비어 있었고,
    이 함수가 `None` 을 돌려줘 **모든 제출 스크립트에서 `#PBS -q` 가 통째로 빠졌다.**
    사용자 정본에는 `#PBS -q normal` 이 분명히 있다.

    🔴 **PBS 에서 `sinfo` 가 없는 것은 정상이다.** 큐 출처를 `sinfo` 하나에 걸어 둔 것이
    결함이었다. 사용자가 직접 알려준 값(`config/accounts.json` 의 `queue_default`)을
    최종 폴백으로 둔다. 그래도 없으면 **조용히 빼지 않고 크게 경고한다.**
    """
    if args is not None:
        if getattr(args, "partition", None):
            return args.partition, "--partition (사용자 지정)"
        if getattr(args, "queue", None):
            return args.queue, "--queue (사용자 지정)"
    for p in env.get("partitions") or []:
        if p.get("is_default"):
            return p["name"], "sinfo (기본 파티션)"
    parts = env.get("partitions") or []
    if parts:
        return parts[0]["name"], "sinfo (첫 파티션)"
    fallback = accounts_mod.default_queue()
    if fallback:
        return fallback, "config/accounts.json 의 queue_default (사용자 확인값)"
    return None, None


def default_partition(env, args=None):
    """--partition > --queue > sinfo > config 기본 큐. 값만 돌려준다."""
    return resolve_partition(env, args)[0]


def partition_warning_lines():
    """🔴 큐를 정하지 못했을 때의 경고 **문구 한 벌**. 판정은 호출부가 한다.

    합친 이유: 예전에는 이 문구가 두 곳에 있었다 — 여기(호출처 0인 죽은 함수)와
    `format_feasibility()` 안의 인라인 사본. **실제로 화면에 뜨는 것은 인라인 쪽**이었고
    두 문구가 미묘하게 달랐다(`-q 가 들어가지 않습니다` vs `-q 가 없습니다`).
    나중에 한쪽만 고치면 **어느 쪽이 사용자에게 보이는지 알 수 없어진다** —
    `envpaths.py` 주석이 "같은 유형 5번째"라 부른 바로 그 패턴이다(critic2 지적).
    """
    return [
        " " + "!" * 70,
        " ! 🔴 큐(파티션)를 정하지 못했습니다 — 제출 스크립트에 `-q` 가 없습니다.",
        " !   큐 지정을 요구하는 사이트에서는 **전 항목이 거부**됩니다.",
        " !   → ./run.sh --queue <큐이름>",
        " " + "!" * 70,
    ]



# --------------------------------------------------------------------------
def submission_feasibility(args, shell, store, env, planned, quiet=False):
    """🔴 **제출 없이** 스케줄러가 받아줄지 확인한다 (`sbatch --test-only`).

    dry-run 이 소프트웨어 존재만 보고 스케줄러 수용 여부를 안 보면,
    "계정 없음"으로 전 항목이 거부되는 실패를 **왕복 1회 뒤에야** 알게 된다.
    그것이 정확히 이 패키지가 막으려던 손실이다.
    """
    kind = env.get("scheduler")
    if kind == sched_mod.NONE:
        return {"checked": False, "reason": "배치 스케줄러가 없다(셸 실행)",
                "results": []}
    if getattr(args, "no_precheck", False):
        return {"checked": False,
                "reason": "--no-precheck 로 사용자가 껐다. 🔴 계정·큐 문제가 있으면 "
                          "실제 제출에서야 드러난다.",
                "results": []}
    adapter = sched_mod.make_adapter(kind, shell,
                                     os.path.join(args.pkg_root, "sei_pilot",
                                                  "templates"),
                                     workdir=store.workdir, store=store)
    account, acct_info = resolve_account(args, env, verbose=not quiet)
    part = default_partition(env, args)
    results = []
    for entry in planned:
        if entry["status"] != "planned":
            continue
        # 🔴 사전검사는 **실제 제출과 같은 스크립트**를 검사해야 한다.
        #    예전에는 여기서 JobSpec 을 따로 만들어 module 블록도, `--ncpus-per-node`
        #    도, `SEI_QC_LEVEL` 도 빠졌다. 그러면 사전검사가 통과해도 실제 제출이
        #    거부될 수 있고(그 반대도), **사전검사의 존재 이유가 사라진다.**
        #    (critic2 가 --emit-script 에서 찾은 것과 같은 결함의 더 큰 판이다.)
        args._resolved_account = account
        kw = {}
        if entry["key"] == "probe_queuewait":
            # 🔴 이 항목은 제출 시 개별 잡으로 **쪼개진다.** 항목 선언값(85×64)으로
            #    사전검사하면 **한 번도 제출되지 않는 형태**를 시험하는 것이고,
            #    하필 그것이 과거에 거부당한 형태다. 실제로 나갈 **가장 큰 잡**을 본다.
            decomp = queue_wait_decomposition(env)
            if not decomp["node_counts"]:
                continue
            kw = {"nodes": max(decomp["node_counts"]),
                  "cores_per_node": decomp["cores_per_node"]}
        spec = build_spec(store, entry, env, build_common_env(args, store, part),
                          part, args, key="check_" + entry["key"], command="true",
                          **kw)
        results.append(adapter.test_submit(spec).to_dict())
    n_bad = sum(1 for r in results if r["ok"] is False)
    n_unknown = sum(1 for r in results if r["ok"] is None)
    return {"checked": True, "scheduler": kind, "account_used": account,
            # 🔴 무엇으로 검사했고 부작용이 있었는지 정직하게 남긴다.
            "precheck_method": (results[0]["method"] if results else None),
            "precheck_has_side_effects": bool(
                getattr(adapter, "PRECHECK_HAS_SIDE_EFFECTS", False)),
            "account_info": acct_info, "partition_used": part,
            "partition_source": resolve_partition(env, args)[1],
            "n_ok": sum(1 for r in results if r["ok"] is True),
            "n_rejected": n_bad, "n_unknown": n_unknown, "results": results}


def format_feasibility(feas):
    L = []
    if not feas.get("checked"):
        L.append(" 제출 사전검사 : 생략 (%s)" % feas.get("reason"))
        return L
    L.append("")
    label = ("실제 제출 없음" if not feas.get("precheck_has_side_effects")
             else "⚠ 보류 제출 후 삭제 방식 — 완전 무부작용 아님")
    L.append(" 제출 사전검사 (%s): 수용 %d · 거부 %d · 확인불가 %d"
             % (label, feas["n_ok"], feas["n_rejected"], feas["n_unknown"]))
    if feas.get("precheck_method"):
        L.append("   방법: %s" % feas["precheck_method"])
    if feas.get("account_used"):
        L.append("   계정: %s   큐/파티션: %s"
                 % (feas["account_used"], feas.get("partition_used")))
    # 🔴 큐의 **출처**를 보여준다. `-q` 가 조용히 빠져 전 항목이 거부된 적이 있다.
    if feas.get("partition_source"):
        L.append("   큐 출처: %s" % feas["partition_source"])
    if feas.get("partition_used") is None and feas.get("checked"):
        L.extend(partition_warning_lines())        # 🔴 문구는 한 곳에서만 온다
    if feas["n_rejected"]:
        seen = set()
        L.append(" " + "!" * 70)
        L.append(" ! 🔴 스케줄러가 거부했다 — 지금 제출하면 전부 실패한다.")
        for r in feas["results"]:
            if r["ok"] is False and r["message"][:120] not in seen:
                seen.add(r["message"][:120])
                L.append(" !   [%s]" % r["key"])
                # 🔴 **자르지 마라.** 예전에는 `splitlines()[0][:66]` 으로 첫 줄 66자만
                #    찍었고, 실제 클러스터에서 PBS 필터 훅 메시지가
                #    "... filter hook 'job_submit_filter' encountere..." 에서 끊겼다.
                #    **원인은 잘려나간 뒷부분에 있었다.** 스케줄러 원문은 전문을 낸다.
                for line in r["message"].splitlines():
                    for chunk in _wrap(line, 66):
                        L.append(" !   %s" % chunk)
                if r.get("remedy"):
                    for chunk in _wrap("→ " + r["remedy"], 66):
                        L.append(" !   %s" % chunk)
        L.append(" !")
        L.append(" ! 이 메시지 전문을 그대로 회신해 주세요. 잘라서 보내면 원인을")
        L.append(" ! 다시 물어야 하고 왕복이 한 번 더 늘어납니다.")
        L.append(" ! 우리가 보내는 스크립트 전문을 보시려면:")
        L.append(" !   ./run.sh --emit-script <항목이름>      (예: probe_node)")
        L.append(" " + "!" * 70)
    return L


def _wrap(text, width):
    """긴 줄을 자르지 않고 **접는다**. 잘라내면 원인이 사라진다."""
    text = (text or "").rstrip()
    if not text:
        return [""]
    return [text[i:i + width] for i in range(0, len(text), width)] or [""]


def describe_level(level_name):
    """계획 출력에 실을 '레벨' 한 줄. 값은 config 에서 온다(하드코딩 금지)."""
    slot = qc_level_slot(level_name)
    lvl = ((config.load("qc_levels.json", {}).get("gaussian16") or {})
           .get("level%s" % slot) or {})
    return ("%s (%s / %s%s)"
            % (lvl.get("label", "?"), lvl.get("functional", "?"),
               lvl.get("basis_real_name") or lvl.get("basis", "?"),
               ", 동봉 기저" if (lvl.get("basis") or "") == "gen" else ""))


def cmd_emit_script(args, shell=None, store=None, env=None):
    """🔴 제출 스크립트 **전문**을 그대로 찍는다.

    왜: 실제 클러스터에서 PBS 필터 훅이 4/4 를 거부했는데, 우리는 거부 메시지도
    스크립트도 못 보고 있었다. 이걸 붙여넣으면 **왕복 1회로 원인이 확정된다.**
    """
    # 🔴 주입 가능해야 한다. 내부에서 진짜 Shell() 을 만들면 이 진입점 자체를
    #    FakeShell 로 테스트할 방법이 없고, 그러면 "제출본 ≡ emit 출력" 을 **진짜
    #    진입점 호출로** 검증할 수 없다. 테스트가 불가능한 구조 자체가 결함이다.
    shell = shell or Shell()
    store = store or Store(args.workdir)
    env = env if env is not None else build_env(
        shell, args.pkg_root,
        cores_per_node_override=getattr(args, "cores_per_node", None),
        queue_hint=getattr(args, "queue", None) or args.partition,
        args_ns=args)
    guard = budget_mod.guard_for_profile(args.profile)
    planned, _summary = plan_mod.build_plan(
        env, guard, profile=args.profile,
        qc_level=describe_level(getattr(args, "level", None)),
        account_resolver=account_resolver(args))
    want = args.emit_script
    entry = next((p for p in planned if p["key"] == want), None)
    if entry is None:
        sys.stderr.write("알 수 없는 항목: %s\n  ↳ 쓸 수 있는 값: %s\n"
                         % (want, ", ".join(p["key"] for p in planned)))
        return 2
    # 🔴 submit_entry() 는 `status != "planned"` 인 항목을 조용히 건너뛴다(아래
    #    cmd_submit 의 제출 루프). sizing(wall_h/cores_per_node/reserved_core_hours 등,
    #    plan.py 의 entry.update() 가 채우는 값들)은 그 항목에만 계산된다 -- "planned" 가
    #    아닌 entry 에는 애초에 채워지지 않는다. emit-script 가 이 게이트 없이 곧장
    #    build_spec 에 넘기면 build_spec 이 없는 키를 읽다 KeyError 로 죽는다.
    #    🔒 이건 증상이다. 원인은 emit 과 submit 이 "sizing 을 통과한 항목만 스크립트를
    #    만든다"는 같은 성질을 다른 경로로 지키고 있었다는 것 -- 위 470번째 줄의 큐 사고와
    #    같은 클래스(제출과 emit 이 서로 다른 경로로 entry 를 다뤄 갈라진 사고, 두 번째).
    #    ⟹ 여기서 크래시 대신 submit 과 같은 이유로 같은 사유를 보여준다.
    if entry["status"] != "planned":
        sys.stderr.write(
            "항목 %r 은 계획되지 않았다 (status=%s) -- sizing 이 되지 않아 emit 할 스크립트가 "
            "없다.\n  ↳ 사유: %s\n  ↳ emit-script 는 --submit 이 실제로 제출할 항목만 보여줄 "
            "수 있다.\n" % (want, entry["status"], entry.get("skip_reason") or "(사유 없음)"))
        return 3
    kind = env.get("scheduler")
    adapter = sched_mod.make_adapter(kind, shell,
                                     os.path.join(args.pkg_root, "sei_pilot",
                                                  "templates"),
                                     workdir=store.workdir, store=store)
    # 🔴 실제 제출과 **같은 함수**로 큐를 정한다. 자기만의 폴백을 두었더니
    #    emit 은 `-q normal` 을 보여주는데 제출본에는 `-q` 가 없었다.
    part = default_partition(env, args)
    args._resolved_account = resolve_account(args, env, verbose=False)[0]
    spec = build_spec(store, entry, env,
                      build_common_env(args, store, part), part, args)
    path = adapter.write_script(spec)
    print("# ---- %s (%s) : %s ----" % (want, kind, path))
    print("# 🔴 이 전문을 그대로 회신해 주세요. 스케줄러가 거부하면 원인이 여기 있습니다.")
    with open(path) as fh:
        sys.stdout.write(fh.read())
    cmd_file = os.path.join(spec.job_dir, spec.key + ".cmd.sh")
    if os.path.exists(cmd_file):
        print("\n# ---- %s.cmd.sh (잡이 실행할 명령) ----" % spec.key)
        with open(cmd_file) as fh:
            sys.stdout.write(fh.read())
    return 0


def cmd_preflight(args, shell=None, store=None, env=None, quiet=False):
    shell = shell or Shell()
    store = store or Store(args.workdir)
    env = env or build_env(shell, args.pkg_root,
                           queue_hint=getattr(args, "queue", None),
                           cores_per_node_override=getattr(args, "cores_per_node", None),
                           args_ns=args)
    guard = budget_mod.guard_for_profile(args.profile, args.max_core_hours,
                                         args.max_wall_h, args.max_gpu_hours)
    # 🔒 [critic3 치명적-2] **게이트가 보는 큐 == 제출이 가는 큐.**
    #    예전에는 sizing 이 `qstat -Qf` 전체에서 가장 긴 큐(`long`)의 wall 을 가정하고,
    #    실제 제출은 `resolve_partition()` 이 고른 다른 큐(`normal`)로 나갔다.
    #    ⟹ 게이트가 "안전"이라 한 잡이 wall-kill 된다. 두 경로를 여기서 묶는다.
    submit_queue = default_partition(env, args)
    planned, summary = plan_mod.build_plan(env, guard, profile=args.profile,
                                       qc_level=describe_level(
                                           getattr(args, 'level', None)),
                                       account_resolver=account_resolver(args),
                                       submit_queue=submit_queue,
                                       ncpus_override=plan_mod.ncpus_override_from_config(args))
    text = plan_mod.format_plan_text(planned, summary, env)
    feas = submission_feasibility(args, shell, store, env, planned, quiet=quiet)
    summary["submission_check"] = feas
    if not quiet:
        print(text)
        print("\n".join(format_feasibility(feas)))
        # 🔒 §R26.4 — 게이트가 실패하면 **여기서 크게 말한다.** 제출 차단은 cmd_submit 에서.
        if not summary["sizing_gates"]["passed"]:
            print(plan_mod.format_gate_failures(planned, summary["sizing_gates"]))
    store.write_result("plan.json", {"plan": planned, "summary": summary,
                                     "env_hostname": env.get("hostname"),
                                     "scheduler": env.get("scheduler")})
    # 어떤 단계에서 죽어도 회신할 파일이 항상 존재하게 한다.
    write_report(args, store, env, planned, summary, guard, partial=True)
    return env, planned, summary, guard


def cmd_submit(args, shell=None, store=None, env=None):
    shell = shell or Shell()
    store = store or Store(args.workdir)
    # [A-1e] --rerun: 지정된 항목의 상태 마커를 옆으로 치운다(삭제 아님). done 은
    # --force 로도 뚫리지 않으므로(성공 항목 실수 재실행 방지) 이것이 유일한 정규 경로다.
    for _key in (getattr(args, "rerun", None) or []):
        # [lead 2026-08-21] jobs/<key>/ 도 옆으로 치운다 -- 재실행이 이전 실행의 유일한
        # 물리적 증거를 덮어쓰지 않게(§39.80 의 분석이 그 디렉터리 위에 서 있다).
        moved = store.reset_item(_key, archive_job_dir=True)
        if moved:
            print("[rerun] %s: 마커·jobs/ %d개를 <이름>.reset.<epoch> 으로 치웠다 (삭제 아님) — "
                  "이 항목은 이번 실행에서 다시 제출된다:" % (_key, len(moved)))
            for _m in moved:
                print("         %s" % _m)
            print("         ↳ 이전 산출물은 jobs/%s.reset.<epoch>/ 에 보존됐다. 패키지가 바뀌지 "
                  "않았고 인프라 실패(노드 사망 등)만이었다면 `cp -r jobs/%s.reset.<epoch>/stages "
                  "jobs/%s/` 로 완료된 stage 부터 재개할 수 있다." % (_key, _key, _key))
        else:
            print("[rerun] %s: 치울 마커가 없다 (이미 미실행 상태)" % _key)
    run_no = store.bump_run_counter()
    env, planned, summary, guard = cmd_preflight(args, shell, store, env)

    # 🔒 §R26.4 — 게이트 3개 중 하나라도 실패하면 **제출하지 않는다.**
    #    🔴 engineer 지시: "하나라도 실패하면 제출하지 말고 4-튜플 표를 그대로 보내라.
    #    숫자를 맞추려고 예산이나 guard 를 조정하지 마라 — 그게 §R24.1 에서 기각한 거래다."
    #    가장 위험한 실패는 (a)다: P6 의 스레드 수가 어긋나도 **잡은 정상 종료하고**
    #    κ 가 16배 틀린 값이 회신에 실린다(ADR-048). 사람이 알아챌 방법이 없다.
    # 🔒 lead 판정 — **위반 항목만 막는다. 전량 차단은 틀린 실패 모드다.**
    #    24 h 큐 시나리오에서 위반은 P1b 하나뿐이고 P5·P1·P6 는 정상이다.
    #    전부 막으면 **사용자가 왕복 하나(3.5일)를 쓰고 아무것도 못 받는다** — 그게
    #    이번 라운드 내내 피하려던 결과다.
    #    ⟹ 항목 단위 위반: 그 항목만 빠진다(build_plan 이 이미 표시했다).
    #      전역 위반(총 천장 > 가드): 회계가 어긋난 것이므로 전체를 멈춘다.
    gates = summary.get("sizing_gates") or {"passed": True}
    if not gates["passed"]:
        print(plan_mod.format_gate_failures(planned, gates))
    if gates.get("blocks_everything") and not getattr(args, "ignore_sizing_gates", False):
        print("  🔴 총 천장이 가드를 넘습니다 — 회계가 어긋난 상태라 **전체를 멈춥니다.**")
        print("  (검토 후에도 진행해야 한다면 --ignore-sizing-gates 를 명시해야 합니다.)")
        return []

    kind = env.get("scheduler")
    if args.profile == plan_mod.PROFILE_GPU and not args.use_scheduler:
        # 🔴 GPU 머신은 배치 스케줄러가 없을 가능성이 높고, 있더라도 GPU 잡을
        #    엉뚱한 큐에 던지면 안 된다. 기본은 셸(nohup)이며 --use-scheduler로 해제.
        if kind != sched_mod.NONE:
            print("  * GPU 프로파일: 스케줄러(%s)가 감지됐으나 기본값대로 셸로 실행한다 "
                  "(--use-scheduler 로 변경)" % kind)
        kind = sched_mod.NONE
    adapter = sched_mod.make_adapter(kind, shell,
                                     os.path.join(args.pkg_root, "sei_pilot", "templates"),
                                     workdir=store.workdir, store=store)
    part = default_partition(env, args)
    account, _acct_info = resolve_account(args, env)
    args._resolved_account = account
    common_env = build_common_env(args, store, part)
    # [ADR-113] physics keys the harness (not the item) sets -- part of every digest below.
    physics = physics_env(dict(common_env, **qc_env_for_jobs(env)))
    current_fp = version.package_fingerprint(args.pkg_root, (
        [os.path.relpath(store.workdir, args.pkg_root).split(os.sep)[0]]
        if not os.path.relpath(store.workdir, args.pkg_root).startswith("..") else []))
    all_job_ids = []
    print("\n[submit] 스케줄러=%s  파티션=%s  (실행 #%d)" % (kind, part, run_no))

    for entry in planned:
        key = entry["key"]
        if entry["status"] != "planned":
            continue
        if store.is_done(key):
            # 🔴 [ADR-113 / §39.80(g)] done 마커는 "무언가 끝났다"지 "지금 계획된 그 계산이
            #    성공했다"가 아니다. 두 절을 모두 검사한다:
            #    (ii) spec_digest — 제출 시 저장한 것과 현재 계획이 같은 계산인가
            #    (i)  outcome/cause_class — payload 가 parsed content 로 쓴 판정이 plumbing
            #         실패(protocol|engine|unknown)면 재제출, 화학/예산 결과면 재제출 금지
            digest = spec_digest(entry, physics)
            status, old = store.done_spec_status(key, digest, physics_keys=sorted(physics))
            done_payload = store.outcome_payload(key, "done")
            outcome = done_payload.get("outcome")
            cause = done_payload.get("cause_class") or outcome_mod.cause_class(outcome)
            if status == "stale":
                moved = store.reset_item(key, archive_job_dir=True)
                entry["submission"] = {"action": "resubmitted_stale_spec",
                                       "marker_digest": old, "plan_digest": digest}
                print("  ! %-16s 🔴 done 마커가 있으나 **다른 spec 의 것** (마커=%s 현재=%s) "
                      "→ 승계하지 않는다. 마커·jobs/ 디렉터리 %d개를 .reset.<epoch> 으로 "
                      "치우고 다시 제출한다" % (key, old, digest, len(moved)))
            elif (outcome_mod.should_retry(cause)
                  and done_payload.get("pkg_fingerprint")
                  and done_payload.get("pkg_fingerprint") != current_fp
                  and not entry.get("array")):
                # [engineer9 §R39.50] (1) a plumbing outcome is retried ONLY when the build has
                # changed since the marker was written -- "something changed that could
                # plausibly fix it"; an unchanged build re-spends ~1,000 core-h (P5, measured)
                # against ~0 expected yield. (2) ARRAY items never auto-resubmit: one bad task
                # re-runs all 20 (646x amplification, measured) -- print and require --rerun.
                moved = store.reset_item(key, archive_job_dir=True)
                entry["submission"] = {"action": "resubmitted_plumbing_outcome",
                                       "outcome": outcome, "cause_class": cause,
                                       "marker_pkg_fingerprint": done_payload.get("pkg_fingerprint"),
                                       "current_pkg_fingerprint": current_fp}
                print("  ! %-16s 🔴 done 마커의 outcome=%s (cause_class=%s: plumbing) 이고 "
                      "빌드가 바뀌었다(%s→%s) → 재제출한다. 이전 실행 %d개를 .reset.<epoch> 으로 보존"
                      % (key, outcome, cause, done_payload.get("pkg_fingerprint"), current_fp,
                         len(moved)))
            else:
                entry["submission"] = {"action": "skipped_done", "spec_status": status,
                                       "outcome": outcome, "cause_class": cause}
                if status == "unknown" and old and old != digest:
                    print("  - %-16s 이미 완료 → 건너뜀 — ⚠ digest 불일치(%s≠%s)지만 이번 실행에서 "
                          "탐지된 G16 module/path 키 집합이 제출 때와 달라 '바뀐 계산'으로 읽지 "
                          "않는다. 탐지를 확인한 뒤 다시 실행하거나 `--rerun %s`"
                          % (key, old, digest, key))
                elif status == "unknown":
                    print("  - %-16s 이미 완료 → 건너뜀 (멱등 재개) — ⚠ 마커에 spec_digest 가 "
                          "없어 현재 계획과 같은 계산인지 확인 불가. 이 항목의 설정(extra_env "
                          "등)이 바뀌었다면 `--rerun %s`" % (key, key))
                else:
                    print("  - %-16s 이미 완료 → 건너뜀 (멱등 재개, spec 일치 %s)" % (key, digest))
                if cause not in (outcome_mod.SUCCESS, "absent"):
                    why = ("array 항목은 자동 재제출하지 않는다(태스크 1개 때문에 전부 재실행)"
                           if entry.get("array") else
                           "결정론적 입력 결함 — 같은 덱은 같은 crash, 재시도 금지 (§39.87)"
                           if cause == "deterministic" else
                           "빌드(pkg_fingerprint)가 그대로라 재시도해도 같은 결과"
                           if outcome_mod.should_retry(cause) else
                           "같은 설정의 재실행은 새 정보를 주지 않는다")
                    print("      ⚠ %s 의 done 마커 outcome=%s (cause_class=%s) — 끝났지만 성공이 "
                          "아니다. %s; 자동 재제출 안 함. 원하면 `--rerun %s`"
                          % (key, outcome, cause, why, key))
                continue
        # 🔴 **실패한 항목은 재시도 대상이다.**
        #    예전에는 `is_submitted` 만 봐서, 실패한 잡도 "이미 제출됨"으로 건너뛰었다.
        #    실클러스터에서 P1/P1b/P5 가 rc=3 으로 죽은 뒤 `./run.sh` 를 다시 쳐도
        #    **아무 일도 일어나지 않았을 것이다**(--force 를 써야 했고, 그건 사용자가
        #    알 수 없다). done/failed/submitted 세 상태를 구분한다.
        if store.is_failed(key) and not args.force:
            # 🔴 [critic11] a payload that exits NON-ZERO after writing its terminal status
            #    (endpoint_prep.sh exit 7 on budget caps, 2/4/5 on input/solvent refusals)
            #    lands HERE, not in the done branch -- and this branch used to retry
            #    unconditionally, so "budget never retries" was not enforced for real caps.
            #    chemical / budget / deterministic -> no retry (real completed answers, or a
            #    defect that reproduces identically).
            # 🔴 [critic14] NOT "same taxonomy, same rule" as the done branch above for every
            #    class -- `absent` in particular is handled OPPOSITELY on purpose here: the
            #    done branch (`cause not in (SUCCESS, "absent")`, above) never flags/retries an
            #    absent-outcome DONE marker, but a FAILED marker with cause_class `absent`
            #    falls through to the retry print below, since `absent` is not in this tuple.
            #    Both are individually defensible (a done-but-unverdicted run vs. a genuinely
            #    failed run that never got far enough to write a terminal status), but they are
            #    not the same rule -- do not "fix" this asymmetry by adding `absent` here
            #    without checking why the done branch excludes it first.
            fpl = store.outcome_payload(key, "failed")
            fcause = fpl.get("cause_class") or outcome_mod.cause_class(fpl.get("outcome"))
            if fcause in ("chemical", "budget", "deterministic"):
                entry["submission"] = {"action": "skipped_failed", "outcome": fpl.get("outcome"),
                                       "cause_class": fcause}
                print("  - %-16s 지난번 실패(outcome=%s, cause_class=%s) → 같은 입력의 재시도는 "
                      "같은 결과라 재시도하지 않는다. 원하면 `--rerun %s`"
                      % (key, fpl.get("outcome"), fcause, key))
                continue
            print("  - %-16s 지난번 실패(cause_class=%s) → 다시 시도합니다" % (key, fcause))
            store.clear_failed(key)     # 안 지우면 다음 실행에서 이중 제출된다
        elif store.is_submitted(key) and not args.force:
            # [A-1e] qdel 등 외부 종료는 payload 가 마커를 못 남겨 submitted 만 남는다
            # — '진행 중'과 마커만으로 구분 불가. 스케줄러에 jobid 를 직접 물어
            # 탐지·보고까지만 한다. 🔴 자동 재제출은 하지 않는다 (lead 결정 사항).
            sub_payload = (store.read_marker(key, "submitted") or {}).get("payload") or {}
            jids = sub_payload.get("job_ids") or \
                ([sub_payload["job_id"]] if sub_payload.get("job_id") else [])
            known = [adapter.job_known(j) for j in jids]
            if jids and known and all(k is False for k in known):
                print("  ! %-16s 제출됐으나 스케줄러에 없음(외부 종료 추정: job %s). "
                      "done/failed 마커도 없다 — 자동 재제출하지 않는다. "
                      "다시 돌리려면 `--rerun %s`" % (key, ",".join(map(str, jids)), key))
            else:
                print("  - %-16s 이미 제출됨(진행 중) → 건너뜀 (--force로 재제출)" % key)
            continue
        ids = submit_entry(adapter, store, entry, env, common_env, part, args)
        all_job_ids.extend(ids)
        entry.setdefault("submission", {"action": "submitted"})["job_ids"] = ids

    # 🔴 [§39.80(g)] plan.json 은 preflight 가 썼고, 거기엔 "planned / skip_reason null" 만
    #    있었다 — 건너뛴 항목이 회신 어디에도 "안 돌았다"고 적히지 않았다. 제출 결정을
    #    항목별로 덧써서 다시 쓴다. n_skipped_done 은 사람이 먼저 볼 숫자다.
    summary["n_skipped_done"] = sum(
        1 for e in planned if (e.get("submission") or {}).get("action") == "skipped_done")
    store.write_result("plan.json", {"plan": planned, "summary": summary,
                                     "env_hostname": env.get("hostname"),
                                     "scheduler": env.get("scheduler")})

    # collector: 모든 잡이 어떻게 끝나든(afterany) 결과를 모아 JSON을 쓴다.
    collector_ids = submit_collector(adapter, store, all_job_ids, common_env, part, args)
    if kind == sched_mod.NONE:
        adapter.start_worker()
        print("  * 스케줄러가 없어 nohup 순차 워커를 시작했다.")

    print("\n[submit] 제출된 잡 %d개 (+collector %d)" % (len(all_job_ids), len(collector_ids)))
    print("[submit] 예약 core-h %.1f / 상한 %.1f"
          % (summary["reserved_core_hours"], guard.max_core_hours))
    print("""
다음에 할 일 (이게 전부입니다):
  1) 잡이 끝날 때까지 기다립니다. collector 잡이 자동으로 결과를 모읍니다.
  2) 혹시 collector가 실패했으면 `./run.sh --collect` 를 한 번 실행합니다.
  3) %s/results/%s 파일 하나만 회신해 주세요.
""" % (store.workdir, report_filename(args.profile)))
    return all_job_ids


# lead 지시: "`--level g2` 로 폴백 레벨을 쓸 수 있게 하라."
# 🔴 사용자·문서가 쓰는 이름(G-1/G-2)과 내부 슬롯(level2/level1)의 변환은 **여기 한 곳**뿐이다.
#    config/qc_levels.json 의 `label` 이 그 대응의 근거이고, 아래 표는 그것을 읽는다.
def qc_level_slot(level_name):
    """`g1`/`g2` (또는 None) → payload 가 쓰는 슬롯 번호 문자열."""
    if not level_name:
        return "2"                     # 기본 = 주 레벨(G-1 = level2)
    want = str(level_name).strip().lower().replace("-", "")
    spec = (config.load("qc_levels.json", {}).get("gaussian16") or {})
    for slot in ("1", "2"):
        label = (spec.get("level%s" % slot) or {}).get("label", "")
        if label.lower().replace("-", "") == want:
            return slot
    raise SystemExit(
        "알 수 없는 레벨: %s\n  ↳ 쓸 수 있는 값: %s\n  ↳ 정의: config/qc_levels.json"
        % (level_name,
           ", ".join(sorted((spec.get("level%s" % s) or {}).get("label", "?").lower()
                            for s in ("1", "2")))))


def build_common_env(args, store, part):
    """모든 잡에 내려가는 공통 환경변수. **제출과 `--emit-script` 가 공유한다.**

    🔴 예전에는 `cmd_submit` 안에 인라인으로 있었고 `cmd_emit_script` 는 자기만의
    딕셔너리를 만들었다. 결과: `--level g2` 로 제출하면 `SEI_QC_LEVEL="1"` 이 들어가는데
    `--emit-script` 출력에는 **그 줄이 아예 없었다**(critic2 재현).
    같은 `build_spec()` 을 쓰더라도 **입력이 다르면 출력이 갈린다** —
    "디버깅 도구가 실제와 다른 것을 보여준다"는 최악의 실패다.
    ⇒ 조립을 여기 한 곳으로 모은다. 키를 추가할 때도 한 곳만 고치면 된다.
    """
    return {
        "SEI_PKG_ROOT": args.pkg_root,
        "SEI_WORKDIR": store.workdir,
        "SEI_PARTITION": part or "",
        # 🔴 계산 레벨은 여기서 **한 번만** 정해져 모든 payload 로 내려간다.
        #    payload 마다 기본값을 따로 두면 --level 이 일부에만 먹는다.
        "SEI_QC_LEVEL": qc_level_slot(getattr(args, "level", None)),
    }


def qc_env_for_jobs(env):
    """QC 탐지 결과를 잡으로 내려보낸다.

    🔴 `SEI_QC_MODULE` 이 없으면 payload 는 module 을 되살릴 수 없고, 실패 사유도
    "absent" 로만 남는다. `SEI_QC_LOGIN_PATH` 는 **로그인에서 본 경로가 계산 노드에도
    있는지**를 잡이 직접 확인해 회신에 남기게 한다([UNVERIFIED] 를 없애는 값이다).
    """
    qm = env.get("qc_module") or {}
    out = {}
    if qm.get("module"):
        out["SEI_QC_MODULE"] = qm["module"]
    login_path = ((env.get("software") or {}).get("g16")
                  or (env.get("software") or {}).get("g09") or {})
    if isinstance(login_path, dict) and login_path.get("path"):
        out["SEI_QC_LOGIN_PATH"] = login_path["path"]
    elif qm.get("path"):
        out["SEI_QC_LOGIN_PATH"] = qm["path"]
    return out


def build_spec(store, entry, env, common_env, part, args, key=None,
               nodes=None, cores_per_node=None, wall_h=None, command=None):
    """제출용 JobSpec 을 만든다. **제출과 `--emit-script` 가 같은 코드를 쓴다.**

    🔴 별도 경로로 만들면 사용자가 보는 스크립트와 실제 제출되는 스크립트가
    달라진다 — 그건 이 프로젝트에서 반복된 "같은 진실이 두 곳에" 의 최악 형태다
    (디버깅 자체가 거짓말이 된다).
    """
    key = key or entry["key"]
    job_env = dict(common_env)
    job_env.update(qc_env_for_jobs(env))
    job_env["SEI_ITEM"] = key
    job_env["SEI_WALL_H"] = "%.4f" % (wall_h or entry.get("wall_h", 1.0))
    # 🔴 항목별 env (예: endpoint_prep.sh 의 SEI_ENDPOINT_ROLE) -- 공통 env 다음,
    #    아무도 이걸 지나 뒤에서 덮어쓰지 않도록 여기서 한 번만 합친다.
    job_env.update(entry.get("extra_env") or {})
    # 🔴 로그인 노드에서 확인된 module 을 **계산 노드에서도 load** 한다.
    #    찾아 놓고 안 부르면 조용히 실패한다(P1/P5/P1b SKIP 원인 계열).
    job_modules = [m for m in [(env.get("qc_module") or {}).get("module")] if m]
    cpn = cores_per_node or entry["cores_per_node"]
    # 🔴 우선순위: `--ncpus-per-node` > `config/sizing.json` 의 pbs.ncpus_per_node
    #    > 감지값. 예전에는 JSON 값을 **아무도 읽지 않았다** — 주석은 "여기 넣거나
    #    플래그로 덮으라"고 했는데 거짓이었고, 사용자가 JSON 을 고쳐도 조용히 무시돼
    #    ncpus 문제로 또 거부됐을 것이다(critic2).
    pbs_cfg = config.load("sizing.json", {}).get("pbs") or {}
    ncpus_override = plan_mod.ncpus_override_from_config(args)
    # 🔴 [critic3 중대] P6 는 스레드 수를 **재는** 항목이라 override 를 적용하지 않는다.
    #    적용하면 1/16/64 가 전부 같은 값이 되어 S(스케일링)가 무의미해지고,
    #    런타임 게이트가 [INVALID] 로 버려 **예산 1,944 core-h 가 통째로 헛돈다.**
    if ncpus_override and not plan_mod.item_cores_are_the_measurement(key):
        cpn = int(ncpus_override)
    return sched_mod.JobSpec(
        key, command or ("bash %s/%s" % (args.pkg_root, entry["payload"])),
        nodes=nodes or entry["nodes"], cores_per_node=cpn,
        wall_h=wall_h or entry["wall_h"], partition=part,
        array=entry.get("array"), gpus=entry.get("gpus") or 0,
        job_dir=store.job_dir(key), env=job_env, modules=job_modules,
        emit_stdio_lines=bool(pbs_cfg.get("emit_stdio_lines")),
        account=(entry.get("account") or getattr(args, "_resolved_account", None)),
        qos=args.qos, reservation=args.reservation)


def submit_entry(adapter, store, entry, env, common_env, part, args):
    """항목 1개 제출. 실패해도 예외를 던지지 않는다(부분 실패 격리)."""
    key = entry["key"]
    ids = []

    if key == "probe_queuewait":
        # 🔴 분해는 queue_wait_decomposition() 한 곳에서 온다 — 사전검사와 공유한다.
        decomp = queue_wait_decomposition(env)
        if decomp["dropped_by_cap"]:
            print("  ! probe_queuewait: %s node 요청은 생략한다 (상한 %d, "
                  "config/sizing.json). 큐 상한 미상이라 축소했다 — 회신에 남는다."
                  % (decomp["dropped_by_cap"], decomp["cap"]))
            store.mark_failed("probe_qw_capped", "node_count_capped",
                              "요청 %s node 를 상한 %d 로 축소했다. 큐 상한을 모르는 "
                              "상태에서 거부되면 측정이 0 이 되기 때문이다."
                              % (decomp["dropped_by_cap"], decomp["cap"]),
                              severity="info")
        for n in decomp["dropped_too_large_for_cluster"]:
            store.mark_failed("probe_qw_n%d" % n, "cluster_too_small",
                              "요청 %d node > 클러스터 최대 %s node"
                              % (n, decomp["cluster_max_nodes"]), severity="info")
        for n in decomp["node_counts"]:
            sub_key = "probe_qw_n%d" % n
            if store.is_done(sub_key):
                continue
            if store.is_failed(sub_key) and not args.force:
                store.clear_failed(sub_key)          # 실패한 것은 다시 시도한다
            elif store.is_submitted(sub_key) and not args.force:
                continue
            spec = build_spec(store, entry, env, common_env, part, args,
                              key=sub_key, nodes=n,
                              cores_per_node=decomp["cores_per_node"],
                              wall_h=max(1.0 / 60.0, entry["wall_h"]),
                              command=("bash %s/payload/probe_queuewait.sh"
                                       % args.pkg_root))
            submit_epoch = int(time.time())
            jid = adapter.submit(spec)
            if jid is None:
                store.mark_failed(sub_key, "submit_rejected",
                                  "스케줄러가 %d node 잡을 거부했다" % n)
                continue
            store.mark_submitted(sub_key, {"job_id": jid, "submit_epoch": submit_epoch,
                                           "nodes": n, "partition": part})
            ids.append(jid)
            print("  + %-16s job=%s (%d node)" % (sub_key, jid, n))
        return ids

    spec = build_spec(store, entry, env, common_env, part, args)
    submit_epoch = int(time.time())
    links = entry.get("chain_links", 1)
    if links > 1:
        ids = adapter.submit_chain(spec, links)
    else:
        jid = adapter.submit(spec)
        ids = [jid] if jid else []
    if not ids:
        store.mark_failed(key, "submit_rejected", "제출 명령이 실패했다")
        print("  ! %-16s 제출 실패 (failures[]에 기록)" % key)
        return []
    if links > 1 and len(ids) < links:
        # 🔴 체인 중간부터 제출이 거부됐다(사이트 QoS 등). 조용히 넘어가면
        #    "계획된 core-h의 일부만 쓰고 중단"이 회신 JSON 어디에도 안 남는다(critic M-1).
        store.mark_failed(key, "chain_partial_submit",
                          "%d/%d 링크만 제출됨 — 나머지는 스케줄러가 거부했다. "
                          "이 항목은 계획된 자원의 일부만 쓰고 끝난다."
                          % (len(ids), links), severity="warning")
    payload = {"job_ids": ids, "submit_epoch": submit_epoch, "partition": part,
               "nodes": entry["nodes"], "chain_links": links,
               "links_submitted": len(ids),
               "spec_digest": spec_digest(
                   entry, physics_env(dict(common_env, **qc_env_for_jobs(env)))),
               "physics_keys": sorted(physics_env(dict(common_env, **qc_env_for_jobs(env))))}
    if entry.get("array"):
        n_tasks = entry["array"][1] - entry["array"][0] + 1
        payload["n_tasks"] = n_tasks
        payload["accepted"] = n_tasks       # 제출이 수락됐다 = 배열 전체 수락
    store.mark_submitted(key, payload)
    print("  + %-16s job=%s x%d links, %.2f h, %.0f core-h"
          % (key, ids[0], links, entry["wall_h"], entry.get("reserved_core_hours", 0)))
    return ids


def submit_collector(adapter, store, dep_ids, common_env, part, args):
    key = "collector"
    cmd = ("cd %s && %s -m sei_pilot.cli collect --workdir %s --pkg-root %s"
           % (args.pkg_root, sys.executable or "python3", store.workdir, args.pkg_root))
    spec = sched_mod.JobSpec(key, cmd, nodes=1, cores_per_node=1, wall_h=0.25,
                             # collector 는 QC 코드를 쓰지 않는다 → probe 계정.
                             partition=part,
                             account=(account_resolver(args).account_for("probe")
                                      or getattr(args, "_resolved_account", None)),
                             qos=args.qos, reservation=args.reservation,
                             job_dir=store.job_dir(key),
                             env=dict(common_env, PYTHONPATH=args.pkg_root,
                                      SEI_ALWAYS_RUN="1"))
    jid = adapter.submit(spec, deps=dep_ids if adapter.supports_dependency else None)
    if jid:
        store.mark_submitted(key, {"job_ids": [jid], "deps": dep_ids})
        return [jid]
    store.mark_failed(key, "collector_submit_failed",
                      "collector 제출 실패 — 사용자가 ./run.sh --collect 를 직접 돌려야 한다",
                      severity="warning")
    return []


def cmd_collect(args, shell=None, store=None, env=None):
    shell = shell or Shell()
    store = store or Store(args.workdir)
    # 계획/환경은 preflight가 저장해 둔 것을 재사용하되, 없으면 다시 수집한다.
    env = env or build_env(shell, args.pkg_root,
                           queue_hint=getattr(args, "queue", None),
                           cores_per_node_override=getattr(args, "cores_per_node", None),
                           args_ns=args)
    guard = budget_mod.guard_for_profile(args.profile, args.max_core_hours,
                                         args.max_wall_h, args.max_gpu_hours)
    planned, summary = plan_mod.build_plan(env, guard, profile=args.profile,
                                       qc_level=describe_level(
                                           getattr(args, 'level', None)),
                                       account_resolver=account_resolver(args))
    path = write_report(args, store, env, planned, summary, guard, partial=False)
    print("[collect] 회신 파일: %s" % path)
    return path


def report_filename(profile):
    """🔴 CPU/GPU 회신 파일을 다른 이름으로 낸다. 두 개를 받아 머지할 것이기 때문이다."""
    return "sei_probe_report.%s.json" % profile


def write_report(args, store, env, planned, summary, guard, partial=False):
    login = env.get("_login") or {}
    gpu_profile = getattr(args, "profile", plan_mod.PROFILE_CPU) == plan_mod.PROFILE_GPU
    probe_key = "probe_gpu_node" if gpu_profile else "probe_node"
    node_probe = collect_mod.collect_node_probe(store, probe_key) if not partial else None

    pilots = []
    unresolved = []
    if not partial:
        if gpu_profile:
            pilots = [collect_mod.collect_p4(store)]
            throughput = {"jobs_submitted": 0, "accepted": 0,
                          "status": "not_applicable_gpu_profile"}
            queue_wait = []
        else:
            pilots = [collect_mod.collect_p1(store),
                      collect_mod.collect_p1b(store),
                      collect_mod.collect_p3(store),
                      collect_mod.collect_p5(store),
                      # 🔒 ADR-048 — κ 앵커. 게이트가 collect_p6 안에 있다.
                      collect_mod.collect_p6(store),
                      # 🔴 ADR-099 -- endpoint_prep_reactant 는 plan.py 의 항목이고
                      #    (같은 key), 여기 없으면 producer 는 있는데 아무도 회신에 담지
                      #    않는 반대쪽 결함이 된다(lead: "correct, tested, unreached").
                      collect_mod.collect_endpoint_prep(store, "endpoint_prep_reactant")]
            # 🔒 [ADR-109] U56-2 항목의 collector 는 release 게이트와 **같은 스위치**를
            #    본다 — 항목이 계획에 들어가는 라운드에만 회신에도 실린다. producer 와
            #    consumer 가 다른 스위치를 보면 "producer 는 있는데 회신에 없는" 결함이
            #    (endpoint_prep 가 한 번 그랬듯) 다시 생긴다.
            if plan_mod.p5_freq_recovery_released():
                # producer and consumer behind the SAME switch (ADR-109 pattern)
                pilots.append(collect_mod.collect_p5_freq_recovery(store))
            if plan_mod.u56_2_released():
                pilots += [
                    collect_mod.collect_endpoint_prep(store, "endpoint_prep_product"),
                    collect_mod.collect_endpoint_prep(store, "endpoint_prep_rc_reactant"),
                    collect_mod.collect_u56(store, "U56_RA_scan"),
                    collect_mod.collect_u56(store, "U56_RA_qst2"),
                    collect_mod.collect_u56(store, "U56_RB_scan"),
                    # U56_RC_scan (T21-se) 은 §39.41(d) 컷 — S3 wave 1 로 이동.
                ]
            throughput = collect_mod.collect_throughput(store)
            queue_wait = collect_mod.collect_queue_wait(store, QUEUE_WAIT_NODE_COUNTS)
    else:
        for e in planned:
            pilots.append({"id": e["key"], "status": "skipped" if e["status"] == "skipped"
                           else "incomplete",
                           "skip_reason": e.get("skip_reason"),
                           "core_hours_total": 0.0, "criteria": {},
                           "fail_reasons": []})
        throughput = {"jobs_submitted": 0, "accepted": 0, "status": "not_run"}
        queue_wait = []

    # 계획 단계에서 생략된 파일럿의 사유를 pilots[]에 반영 (engineer가 '실패'로
    # 오독하지 않도록).
    skip_map = dict((e["key"], e.get("skip_reason")) for e in planned
                    if e["status"] == "skipped")
    for p in pilots:
        if p.get("id") in skip_map and p.get("status") in ("skipped", "incomplete"):
            p["status"] = "skipped"
            p["skip_reason"] = skip_map[p["id"]]

    failures = store.all_failures()
    for f in failures:
        if not f.get("log_excerpt"):
            f["log_excerpt"] = store.tail_log(f.get("key", ""), 800)

    unresolved += collect_unresolved(env, planned, guard, node_probe, pilots)

    rep = report_mod.build_report(
        login=login, node_probe=node_probe, plan=planned, plan_summary=summary,
        guard=guard, pilots=pilots, throughput=throughput, queue_wait=queue_wait,
        failures=failures, package_root=args.pkg_root,
        invocation={"mode": "partial" if partial else "collect",
                    "argv": sys.argv[1:], "resume_count": store.run_count},
        seed=args.seed, unresolved=unresolved,
        profile=getattr(args, "profile", plan_mod.PROFILE_CPU))
    problems = report_mod.validate_report(rep)
    if problems:
        rep.setdefault("failures", []).append(
            {"id": "report", "stage": "validate", "reason": "schema_problems",
             "log_excerpt": "; ".join(problems)[:1500], "severity": "warning"})
    path = store.write_result(report_filename(rep["profile"]), rep)
    if not partial:
        print(report_mod.summarize_for_user(rep))
    return path


def collect_unresolved(env, planned, guard, node_probe, pilots=None):
    """스크립트가 끝내 측정하지 못한 것 + 판정 대기 중인 규약 = lead가 여전히 눈이 먼 항목."""
    out = []
    # [A-5, lead 판정] C-10 위반은 "판정 대기 중인 규약" 그 자체다 — pilots[*] 안에
    # 중첩된 c10_note 는 최상위 요약만 보는 사람이 영영 못 만난다(이번 회신 실측:
    # unresolved_for_lead == [] 인데 c10_note 는 pilots[0] 안에 있었다). 판정 로직은
    # 건드리지 않는다: 이미 있는 "lead 대기" 신호를 이미 있는 "lead 가 읽는" 채널에
    # 잇는 배선이다. 🔴 이게 없으면 다음 사람이 "P1 fail" 을 화학적 실패로 읽고
    # U-56 이 "미측정"에서 유령 0/1 로 바뀐다.
    for p in pilots or []:
        if p.get("c10_cost_probe_violations"):
            out.append({
                "item": "🔴 C-10 위반 기록됨 (%s) — 비용 프로브에 화학 판정이 실려 있다"
                        % p.get("id"),
                "why": "; ".join(p["c10_cost_probe_violations"]),
                "action": ("판정 보류 중인 규약이다: 이 파일럿의 pass/fail 을 화학적 "
                           "판정으로 읽지 마라 (C-10.1: 화학은 조건이지 판정이 아니다). "
                           "상세는 pilots[%s].c10_note." % p.get("id")),
            })
    # IRC 끝점 판정(02_METHOD_SPEC §12.3 R1~R3)에서 사람이 봐야 하는 것만 올린다.
    for p in pilots or []:
        if p.get("id") != "P1":
            continue
        ec = ((p.get("detail") or {}).get("irc") or {}).get("endpoint_comparison")
        if not ec:
            continue
        if ec.get("human_review_required"):
            out.append({
                "item": "🔴 IRC 끝점 판정 불가 (R2b, 배위 재배열 barrier 미지)",
                "why": "공유결합 층도 실체 수도 같고 Li 배위만 재배열됐다. "
                       "tau=%s eV 규칙을 적용할 barrier가 없어 **병합도 분리도 하지 "
                       "않았다**(§12.5: 조용히 기각하면 위음성이 뒷문으로 돌아온다)."
                       % ec.get("tau_eV"),
                "action": "사람 검토 큐(§9.3)로. P1 파일럿은 이 barrier를 계산하지 "
                          "않으므로 여기 걸리는 것 자체는 정상이다.",
            })
        if (ec.get("threshold_sensitivity") or {}).get("threshold_sensitive"):
            out.append({
                "item": "🔴 Li 접촉 임계에 판정이 종속됨 (Layer I)",
                "why": "임계를 ±%s Å 흔들면 끝점 판정이 뒤집힌다. 현재 임계는 "
                       "문헌 통상값 [PLACEHOLDER-ESTIMATE]이다."
                       % (ec.get("threshold_sensitivity") or {}).get("delta_ang"),
                "action": "P1 구조/P2 궤적의 Li-X RDF 첫 최소로 임계를 실측해 "
                          "config/graph_layers.json 을 갱신할 것 (§12.4-3).",
            })
        if ec.get("config_is_fallback"):
            out.append({
                "item": "graph_layers.json 을 읽지 못해 내장 fallback 사용",
                "why": "판정 파라미터가 패키지 설정과 다를 수 있다.",
                "action": "config/graph_layers.json 동봉 여부 확인.",
            })
        if ec.get("endpoint_distinct_C_only") is False and ec.get("distinct"):
            out.append({
                "item": "이 TS는 공유결합 변화가 아니라 Li 배위/회합 변화다",
                "why": "규칙 %s 로 distinct 판정됐다. 공유결합 층만 보던 옛 규약이면 "
                       "기각됐을 반응이며, ADR-003 축(b)(LiF/Li2CO3/ROCO2Li) 계열이 "
                       "여기 해당한다." % ec.get("merge_rule_applied"),
                "action": "정보용. 조치 불필요.",
            })
    if not env.get("cores_per_node"):
        out.append({"item": "A1 cores_per_node",
                    "why": "sinfo/lscpu 어느 쪽에서도 코어 수를 얻지 못했다"})
    if env.get("scheduler") == sched_mod.NONE:
        out.append({"item": "A2/A3 파티션·동시 job 상한",
                    "why": "배치 스케줄러가 감지되지 않았다. 처리량/큐대기 프로브 전부 무효"})
    if not (node_probe or {}).get("outbound_network"):
        out.append({"item": "Q2 계산 노드 outbound 네트워크",
                    "why": "probe_node 잡의 결과가 없다. U-09 Case A/B 판정 불가 → "
                           "Case B(air-gapped) 기본 가정을 유지하라"})
    for r in (guard.to_dict().get("skipped_for_budget") or []):
        out.append({"item": r["id"],
                    "why": "예산 가드로 미실행: %s" % r.get("detail"),
                    "action": "lead 판정 필요 — engineer §11.5는 상한 4,000을 요구한다"})
    for e in planned:
        if e["status"] == "skipped" and "가드" not in (e.get("skip_reason") or "") \
                and "budget" not in (e.get("skip_reason") or ""):
            entry = {"item": e["key"], "why": e.get("skip_reason")}
            # 🔴 무엇을 보내면 되는지 함께 낸다. 없으면 왕복 1회를 더 써야 안다.
            if e.get("fallback_hint"):
                entry["action"] = e["fallback_hint"]
            out.append(entry)
    return out


def cmd_merge(args):
    """CPU/GPU 회신 JSON 2개를 손실 없이 하나로 합친다 (lead가 손으로 합치지 않도록)."""
    paths = list(args.inputs or [])
    if len(paths) < 2:
        sys.stderr.write("merge 에는 회신 JSON 2개 이상이 필요하다\n"
                         "  예: merge results/sei_probe_report.cpu.json "
                         "results/sei_probe_report.gpu.json -o merged.json\n")
        return 2
    reports = []
    for path in paths:
        try:
            with open(path) as fh:
                reports.append(json.load(fh))
        except (OSError, ValueError) as exc:
            sys.stderr.write("읽지 못했다: %s (%s)\n" % (path, exc))
            return 2
    merged = report_mod.merge_reports(reports)
    counts = report_mod.merge_counts(merged)
    out = args.out or "sei_probe_report.merged.json"
    with open(out, "w") as fh:
        json.dump(merged, fh, ensure_ascii=False, indent=2, default=str)
    print("[merge] %s  ← %s" % (out, ", ".join(paths)))
    print("[merge] 프로파일 %d · 파일럿 %d · 실패 %d · 미해결 %d"
          % (counts["profiles"], counts["pilots"], counts["failures"],
             counts["unresolved"]))
    for w in merged.get("merge_warnings") or []:
        print("[merge] ⚠ %s" % w)
    problems = report_mod.validate_report(merged)
    if problems:
        print("[merge] ⚠ 스키마 점검: %s" % "; ".join(problems)[:300])
    return 0


def cmd_status(args, shell=None, store=None):
    store = store or Store(args.workdir)
    print("workdir: %s (실행 %d회)" % (store.workdir, store.run_count))
    keys = set()
    for fn in os.listdir(store.state_dir):
        if fn.endswith(".json"):
            keys.add(fn.rsplit(".", 2)[0])
    for k in sorted(keys):
        st, _ = collect_mod.job_status(store, k)
        print("  %-18s %s" % (k, st))
    return 0


# --------------------------------------------------------------------------
def build_parser():
    p = argparse.ArgumentParser(
        prog="sei_pilot",
        description="SEI 파일럿 인도 패키지 (03_COMPUTE_PLAN.md §R2-6)")
    p.add_argument("command",
                   choices=["preflight", "submit", "collect", "status", "merge"])
    p.add_argument("inputs", nargs="*", default=None,
                   help="merge: 합칠 회신 JSON 경로들")
    p.add_argument("-o", "--out", default=None, help="merge 출력 경로")
    p.add_argument("--workdir", default=os.environ.get("SEI_WORKDIR", "./sei_pilot_work"))
    # 🔴 게이트를 끄는 스위치는 **명시적이어야** 한다. 기본은 항상 차단이다.
    p.add_argument("--ignore-sizing-gates", action="store_true",
                   help="🔴 사양 게이트 실패에도 제출한다. 게이트가 막는 것은 "
                        "'조용히 틀린 측정'이므로 켜기 전에 4-튜플 표를 확인하라.")
    p.add_argument("--pkg-root", default=os.environ.get("SEI_PKG_ROOT", PKG_ROOT))
    p.add_argument("--max-core-hours", type=float, default=None,
                   help="core-h 하드가드 재정의 (기본: 프로파일별 값)")
    p.add_argument("--max-wall-h", type=float, default=None)
    p.add_argument("--profile", default=os.environ.get("SEI_PROFILE",
                                                      plan_mod.PROFILE_CPU),
                   choices=list(plan_mod.PROFILES),
                   help="cpu = HPC 클러스터 패키지 / gpu = GPU 머신 패키지")
    p.add_argument("--gaussian-module", default=os.environ.get("SEI_GAUSSIAN_MODULE"),
                   metavar="NAME",
                   help="Gaussian 모듈 이름을 직접 지정합니다. 미지정 시 "
                        "config/env_paths.json 의 gaussian_modules.default 를 쓰고, "
                        "로드되지 않으면 같은 파일의 fallbacks 를 순서대로 시도합니다.")
    p.add_argument("--emit-script", default=None, metavar="ITEM",
                   help="해당 항목의 제출 스크립트 전문을 그대로 출력하고 끝냅니다. "
                        "스케줄러가 거부할 때 우리가 정확히 무엇을 보내는지 "
                        "확인하는 용도입니다. (예: --emit-script probe_node)")
    p.add_argument("--ncpus-per-node", type=int, default=None,
                   help="PBS `select=...:ncpus=` 에 넣을 값. 사이트가 이 값을 "
                        "제한하는 경우 지정하세요(기본: 감지된 코어 수).")
    p.add_argument("--level", default=None, metavar="G1|G2",
                   help="P1(TS 완주)의 계산 레벨. 기본 G1(wB97XD/def2-TZVPPD), "
                        "폴백 G2(def2-TZVPD)는 더 싸고 회신이 빠릅니다. "
                        "P1b/P5 는 단가'비'를 재는 것이 목적이라 이 값과 무관하게 "
                        "두 레벨을 모두 돕니다.")
    p.add_argument("--max-gpu-hours", type=float, default=None)
    p.add_argument("--partition", default=None)
    p.add_argument("--account", "-A", action="append", metavar="[SW=]NAME",
                   default=([os.environ["SEI_ACCOUNT"]]
                            if os.environ.get("SEI_ACCOUNT") else None),
                   help="SLURM --account / PBS -A. 🔴 이 클러스터는 계정이 "
                        "**소프트웨어 단위**입니다: gaussian / xtb / probe. "
                        "예) --account gaussian=myproj (여러 번 지정 가능). "
                        "소프트웨어 없이 이름만 주면 전 항목에 적용됩니다.")
    p.add_argument("--qos", default=os.environ.get("SEI_QOS"))
    p.add_argument("--queue", default=None,
                   help="PBS 큐 이름 (--partition 과 같은 뜻. PBS 사용자를 위한 별칭)")
    p.add_argument("--cores-per-node", type=int, default=None,
                   help="🔴 계산 노드의 코어 수. 로그인 노드와 사양이 다른 "
                        "이기종 클러스터에서 지정하라(예: --cores-per-node 64)")
    p.add_argument("--reservation", default=None)
    p.add_argument("--no-precheck", action="store_true",
                   help="제출 사전검사를 끈다(PBS는 보류 제출 방식이라 부작용이 있다). "
                        "🔴 끄면 계정·큐 문제를 실제 제출에서야 알게 된다")
    p.add_argument("--seed", type=int, default=20260817,
                   help="재현성용 난수 시드. 결과 JSON에 기록된다.")
    p.add_argument("--use-scheduler", action="store_true",
                   help="GPU 프로파일에서도 감지된 배치 스케줄러를 쓴다(기본은 셸)")
    p.add_argument("--rerun", action="append", default=[], metavar="ITEM",
                   help="이 항목(이름 지정, 반복 가능)의 상태 마커를 옆으로 치우고"
                        "(<이름>.reset.<epoch> 로 이름 변경 — 삭제 아님) 다시 제출 "
                        "대상으로 만든다. 🔴 done 마커는 --force 로도 뚫리지 않는다: "
                        "성공한 항목의 실수 재실행(core-h 재소모)을 막기 위해, 완료 "
                        "항목의 재실행은 반드시 이 플래그로 이름을 지정해서만 한다. "
                        "jobs/<항목>/stages/ 체크포인트는 유지된다(건강한 재개는 공짜).")
    p.add_argument("--force", action="store_true",
                   help="이미 제출된 항목도 다시 제출한다 (기본은 멱등 건너뛰기)")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    if not version.python_ok():
        sys.stderr.write("이 패키지는 python >= %d.%d 가 필요하다 (감지: %s)\n"
                         % (version.MIN_PYTHON + (sys.version.split()[0],)))
        return 2
    args.pkg_root = os.path.abspath(args.pkg_root)
    args.workdir = os.path.abspath(args.workdir)
    # 🔴 레벨 이름은 **여기서** 검증한다. 제출 시점까지 미루면 오타가 dry-run 을
    #    통과해 버리고, 사용자는 잡을 던지고 나서야 알게 된다.
    if getattr(args, "level", None) is not None:
        qc_level_slot(args.level)      # 틀리면 후보와 함께 SystemExit
    if getattr(args, "emit_script", None):
        return cmd_emit_script(args)
    if args.command == "preflight":
        cmd_preflight(args)
    elif args.command == "submit":
        cmd_submit(args)
    elif args.command == "collect":
        cmd_collect(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "merge":
        return cmd_merge(args)
    return 0


if __name__ == "__main__":
    sys.exit(main())
