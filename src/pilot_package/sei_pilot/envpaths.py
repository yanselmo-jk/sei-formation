"""환경 탐지 경로 — **단일 출처** (config/env_paths.json).

🔴 왜 생겼나: `nvidia-smi` 가 PATH에 없는 환경(WSL: `/usr/lib/wsl/lib`)이라는 **같은 사실**이
`payload/P4.sh` 와 `sei_pilot/sysprobe.py` **두 곳에** 적혀 있었고, P4.sh만 고쳐졌다.
그 결과 **planner는 "GPU 없음"으로 판단해 P4를 SKIP** 했는데 실제로는 GPU가 있었다
— 고칠 수 있는 환경 문제가 "이 머신은 GPU-DFT 불가"라는 **능력 측정값으로 둔갑**한다.
(같은 유형 5번째: B-1 SEI_KEY / B-2 stride / wb97x-d3 / guard_source / 이번 건.)

⇒ 경로 목록을 **어디에도 다시 적지 않는다.** py는 이 모듈을, sh는 `payload/env_common.sh`
   를 통해 같은 JSON을 읽는다.
"""

import os

from . import config as config_mod

FALLBACK = {"extra_search_paths": [], "gpu_tools": ["nvidia-smi"],
            "qc_env_vars": ["g16root", "GAUSS_EXEDIR", "GAUSS_SCRDIR"],
            "qc_binaries": ["g16", "g09"], "_fallback": True}


def load(config_dir=None):
    return config_mod.load("env_paths.json", FALLBACK, config_dir)


def extra_search_paths(config_dir=None):
    return list(load(config_dir).get("extra_search_paths") or [])


def path_with_extras(base=None, config_dir=None):
    """PATH 문자열에 추가 경로를 덧붙인 값(중복 없이)."""
    base = base if base is not None else os.environ.get("PATH", "")
    parts = [p for p in base.split(os.pathsep) if p]
    for extra in extra_search_paths(config_dir):
        if extra not in parts:
            parts.append(extra)
    return os.pathsep.join(parts)


def qc_env_vars(config_dir=None):
    return list(load(config_dir).get("qc_env_vars") or [])


def qc_binaries(config_dir=None):
    return list(load(config_dir).get("qc_binaries") or [])


def gaussian_paths_from_env(env=None, config_dir=None):
    """`$g16root` / `$GAUSS_EXEDIR` 등에서 G16 실행 파일 후보 디렉터리를 만든다.

    🔴 Gaussian은 모듈/`g16.profile` 로 환경을 잡는 경우가 많아 **PATH에 g16이 없어도
    설치돼 있을 수 있다.** 그 경우를 놓치면 P1/P1b/P5가 통째로 SKIP된다
    (ORCA 전제였을 때 실제로 그렇게 될 뻔했다).
    """
    env = env if env is not None else os.environ
    out = []
    for var in qc_env_vars(config_dir):
        val = env.get(var)
        if not val:
            continue
        for cand in (val, os.path.join(val, "g16"), os.path.join(val, "g09"),
                     os.path.join(val, "bin")):
            if cand not in out:
                out.append(cand)
    return out


def resolve_qc(shell, config_dir=None, env=None):
    """G16(우선) → G09 실행 파일을 찾는다. PATH → 추가경로 → $g16root 계열."""
    for name in qc_binaries(config_dir):
        found = resolve_tool(shell, name, config_dir)
        if found:
            return name, found
        for d in gaussian_paths_from_env(env, config_dir):
            cand = os.path.join(d, name)
            if shell.exists(cand):
                return name, cand
    return None, None


PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def vendored(name, pkg_root=None, config_dir=None):
    """동봉 바이너리 경로와 필요한 환경변수. 없으면 None.

    🔴 xtb 가 사용자 클러스터에 없어 P3(조합 폭발 계수)가 통째로 SKIP 됐다.
    정적 링크 바이너리를 동봉해 되살린다(LGPL. 출처·체크섬은 PROVENANCE.json).
    """
    spec = (load(config_dir).get("vendored_tools") or {}).get(name)
    if not spec:
        return None
    root = pkg_root or PKG_ROOT
    path = os.path.join(root, spec["rel_path"])
    if not os.path.exists(path):
        return None
    env = dict((k, os.path.join(root, v)) for k, v in (spec.get("env") or {}).items())
    return {"path": path, "env": env, "provenance": spec.get("provenance")}


def resolve_tool(shell, name, config_dir=None, pkg_root=None, prefer_vendored=True):
    """**동봉본 → PATH → 추가 경로** 순으로 실행 파일을 찾는다. 없으면 None.

    동봉본을 먼저 보는 이유: 클러스터에 없는 도구를 되살리려고 실은 것이므로,
    시스템에 오래된 버전이 있어도 **우리가 검증한 것**을 쓰는 편이 재현성에 낫다.
    """
    if prefer_vendored:
        v = vendored(name, pkg_root, config_dir)
        if v:
            return v["path"]
    found = shell.which(name)
    if found:
        return found
    for d in extra_search_paths(config_dir):
        cand = os.path.join(d, name)
        if shell.exists(cand):
            return cand
    return None


# --- module 시스템을 통한 QC 탐지 -------------------------------------------
# 🔴 왜 필요한가: 실제 클러스터에서 P1/P5/P1b 가 **전부 SKIP** 됐다.
#    사유는 "사용 가능한 실행 수단 없음: g16, g09, ...". 우리 탐지가 `command -v` 와
#    `$g16root` 계열뿐이었는데, **HPC 에서 Gaussian 은 거의 항상 `module load` 뒤에
#    나타난다.** 사용자 정본 스크립트도 `module purge && module load ...` 를 쓴다.
#
# 🔴 그리고 찾는 것만으로는 부족하다 — **잡 스크립트가 계산 노드에서 그 module 을
#    실제로 load 해야 한다.** 로그인 노드에서 찾아 놓고 계산 노드에서 안 부르면
#    또 조용히 실패한다. (JobSpec.modules → 템플릿의 MODULE_LINES 가 그 몫이다.)
#
# [UNVERIFIED — 사용자 클러스터에서만 확인 가능]

MODULE_NAME_HINTS = ("gaussian", "g16", "g09")


def configured_gaussian_modules(config_dir=None):
    """설정에 적힌 (기본, 폴백목록). 🔴 이름을 코드에 박지 않는다."""
    spec = load(config_dir).get("gaussian_modules") or {}
    return spec.get("default"), list(spec.get("fallbacks") or [])


def module_candidates(available, hints=MODULE_NAME_HINTS, config_dir=None):
    """`module avail` 결과에서 QC 후보 모듈 이름을 고른다(긴 이름 우선).

    `Gaussian/16`, `gaussian/16.C01`, `g16` 같은 사이트별 표기를 모두 받는다.
    """
    out = []
    for name in available or []:
        low = name.lower()
        if any(h in low for h in hints):
            out.append(name)
    # 🔴 설정의 기본값을 맨 앞, 폴백을 그 다음에 둔다(사용자 확정 순서).
    #    `module avail` 에 안 보여도 시도한다 — 우리가 못 본 모듈일 수 있다.
    default, fallbacks = configured_gaussian_modules(config_dir)
    ordered = ([default] if default else []) + list(fallbacks)
    rest = sorted((n for n in out if n not in ordered),
                  key=lambda n: (n.count("/") == 0, [-ord(c) for c in n]))
    return [n for n in ordered if n in out or n == default] + rest



def resolve_qc_via_module(shell, available, config_dir=None, extra_names=(),
                          preferred=None):
    """`module load <cand>` 후 QC 실행 파일이 나타나는지 시험한다.

    반환: {"module": 이름, "binary": 이름, "path": 경로} 또는 None.
    🔴 시도한 것과 실패 사유를 함께 돌려주어, 못 찾았을 때 **다음에 무엇을 물어야
       할지**가 회신에 남게 한다.
    """
    tried = []
    cands = list(module_candidates(available)) + list(extra_names)
    if preferred:
        # 사용자가 고른 것을 맨 앞에. 목록에 없어도 시도한다(우리가 못 본 모듈일 수 있다).
        cands = [preferred] + [c for c in cands if c != preferred]
    for mod in cands:
        for binname in qc_binaries(config_dir):
            cmd = ("bash -lc 'module load %s >/dev/null 2>&1; "
                   "command -v %s'" % (mod, binname))
            res = shell.run(cmd, timeout_s=60)
            path = (res.out or "").strip().splitlines()
            path = path[-1].strip() if path else ""
            tried.append({"module": mod, "binary": binname,
                          "found": bool(path), "path": path or None})
            if path:
                return {"module": mod, "binary": binname, "path": path,
                        "tried": tried}
    return {"module": None, "binary": None, "path": None, "tried": tried}
