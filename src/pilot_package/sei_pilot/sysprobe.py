"""구성요소 A — 환경 프로브 (§R2-6).

측정 대상 = **우리가 볼 수 없는 것 전부** (A1/A2/A3/A8, I/O, 소프트웨어 인벤토리,
Q2 outbound 네트워크, 클러스터 GPU 유무).

설계: 명령 실행(부작용)과 출력 파싱(순수 함수)을 분리한다.
파싱 함수는 전부 문자열 → dict 이므로 스케줄러 없는 우리 박스에서 테스트 가능하다.
계산 노드에서 수집한 원시 출력은 파일로 저장되고, 같은 파서가 수집 단계에서 다시 읽는다.
"""

import os
import re

from . import envpaths

# 소프트웨어 인벤토리 대상. §R2-6 표의 목록 + 파일럿 실행에 실제로 필요한 것들.
#: 🔴 ADR-043 — **프로브 목록은 그 자체가 회신 데이터다.**
#:  실클러스터 회신에서 `software` 키가 19개였고 `mopac` 이 없었다. engineer 는 그것을
#:  **"MOPAC 부재 확정"** 으로 읽고 축 3(PM7)을 탈락시킬 뻔했다 — 실제로는 **찾아본 적이
#:  없었다.** `[NOT MEASURED]` 를 `[MEASURED — 부정]` 으로 읽은 것이다.
#:  ⟹ 목록에 없는 것은 **설치돼 있어도 회신에 안 나온다.** 그래서 두 가지를 한다:
#:    ① 물어볼 것을 미리 넣는다(아래) ② **프로브 목록 자체를 회신에 싣는다**(`_probed`).
SOFTWARE_TARGETS = [
    "cp2k", "cp2k.psmp", "cp2k.popt", "cp2k.sopt", "orca", "g16", "g09", "vasp_std",
    "qchem", "xtb", "crest", "psi4", "python3", "mpirun", "srun",
    "apptainer", "singularity", "docker", "nvidia-smi", "module",
    # 🔒 ADR-043 로 추가된 것들. 대안 엔진·MD 도구.
    # 🔴 ADR-050(사용자 직접 결정): 허용 집합은 {g16, vasp, lammps, xtb} + **조건부 cp2k** 다.
    #    아래 이름들은 **허용된다는 뜻이 아니라 "찾아봤다"는 기록**이다(ADR-043).
    #    `EXCLUDED_ENGINES` 가 어느 것이 배제됐는지 말한다 — 목록에서 지우지 않는 이유는,
    #    지우면 다음 라운드에 누군가 다시 후보로 올리고 "안 찾아봤다"가 반복되기 때문이다.
    "mopac", "mopac2016", "MOPAC2016.exe", "nwchem", "dftb+", "lammps", "lmp",
    "plumed", "obabel", "gmx",
]

#: 🔒 ADR-050 — 사용자 원문:
#:   *"MOPAC 은 배제하고, Gaussian, VASP, LAMMPS, xTB 로 패키지를 한정해.
#:     만약 정말 필요하다면 CP2K 를 추가해도 좋아."*
ALLOWED_ENGINES = ("g16", "g09", "vasp_std", "lammps", "lmp", "xtb", "crest")
#: 조건부 허용 — *"정말 필요하다면"*. 게이트(U-46 = `$CP2K_DATA_DIR` 확인) 통과 시에만 쓴다.
CONDITIONAL_ENGINES = ("cp2k", "cp2k.psmp", "cp2k.popt", "cp2k.sopt")
#: 🔴 배제된 것. **탐지는 계속한다**(있는지 아는 것과 쓰는 것은 다르다).
EXCLUDED_ENGINES = {
    "mopac": "ADR-050 — 사용자가 명시적으로 배제. 축 3(PM7 replica)이 이것에 걸려 있었다.",
    "mopac2016": "ADR-050 — 위와 같음.",
    "MOPAC2016.exe": "ADR-050 — 위와 같음.",
    # 🔴 ReaxFF 는 **LAMMPS 와 별개로** 사용자가 이전에 명시적으로 배제했다.
    #    **LAMMPS 허용 ≠ ReaxFF 허용.** 이 구분은 흐려지기 쉬우니 코드에 박아 둔다.
    "reaxff": "사용자가 이전에 명시적으로 배제. 🔴 LAMMPS 가 허용됐다고 해서 "
              "ReaxFF 가 허용된 것이 아니다 — 별개 결정이다.",
}


def engine_policy(name):
    """이 엔진을 **써도 되는가**. 탐지 결과와 별개다(있어도 못 쓸 수 있다)."""
    if name in EXCLUDED_ENGINES:
        return {"allowed": False, "conditional": False,
                "reason": EXCLUDED_ENGINES[name]}
    if name in CONDITIONAL_ENGINES:
        return {"allowed": True, "conditional": True,
                "reason": "ADR-050 — 조건부 허용(*'정말 필요하다면'*). "
                          "게이트(U-46: $CP2K_DATA_DIR 확인) 통과 시에만."}
    if name in ALLOWED_ENGINES:
        return {"allowed": True, "conditional": False, "reason": "ADR-050 허용 집합"}
    return {"allowed": None, "conditional": False,
            "reason": "허용 집합에 대한 판정이 없다 — 계산 엔진이 아니거나 미판정."}

# 버전 조회 명령 [UNVERIFIED: 사이트별로 --version 플래그가 다를 수 있다]
VERSION_FLAG = {
    "xtb": "--version", "crest": "--version", "orca": "",  # orca는 인자 없이 배너
    "cp2k": "--version", "cp2k.psmp": "--version", "cp2k.popt": "--version",
    "psi4": "--version", "python3": "--version", "mpirun": "--version",
    "apptainer": "--version", "singularity": "--version", "qchem": "-v",
}


# --------------------------------------------------------------------------
# 순수 파서
# --------------------------------------------------------------------------
#: 🔒 §R23.1 — ISA 게이트(G1). **공통집합이 아닌 명령을 쓴 바이너리는 KNL 에서
#: illegal instruction 으로 죽는다.** `[LITERATURE]` KNL(Xeon Phi 7250) = AVX-512 F·CD·ER·PF /
#: Skylake-SP = F·CD·DQ·BW·VL ⟹ **공통은 F+CD 뿐.** Skylake 타깃 빌드는 KNL 에서 못 돈다.
AVX512_KNL_ONLY = ("avx512er", "avx512pf")
AVX512_SKYLAKE_ONLY = ("avx512dq", "avx512bw", "avx512vl")


def classify_isa(flags):
    """CPU flags → 어떤 바이너리가 이 노드에서 도는가.

    🔴 이것을 프로브하지 않으면 **알 수 없다.** §R21.10 의 MOPAC 과 정확히 같은 구조의
    구멍이었다 — `cluster.cpu` 에 `flags` 키가 아예 없었다.
    """
    fl = set(f.lower() for f in (flags or []))
    if not fl:
        return {"probed": False, "note": "flags 를 읽지 못했다 — [NOT MEASURED]"}
    knl = [f for f in AVX512_KNL_ONLY if f in fl]
    skl = [f for f in AVX512_SKYLAKE_ONLY if f in fl]
    return {
        "probed": True,
        "avx2": "avx2" in fl,
        "avx512f": "avx512f" in fl,
        "avx512_knl_only": knl,
        "avx512_skylake_only": skl,
        "looks_like_knl": bool(knl) and not skl,
        # x86-64 마이크로아키텍처 레벨: v3 = AVX2+FMA, v4 = AVX-512 F+BW+DQ+VL
        "x86_64_v3_ok": ("avx2" in fl and "fma" in fl),
        "x86_64_v4_ok": all(f in fl for f in ("avx512f", "avx512bw",
                                              "avx512dq", "avx512vl")),
        "build_note": ("🔴 KNL 로 보인다 ⟹ 소스 빌드 시 `-xMIC-AVX512`(Intel) / "
                       "`-march=knl`(gcc) 를 쓰고 `-xCORE-AVX512` / "
                       "`-march=skylake-avx512` 를 쓰지 마라. 후자는 여기서 죽는다. "
                       "x86-64-v3(AVX2+FMA)까지는 안전하다."
                       if (knl and not skl) else
                       "AVX-512 KNL 전용 플래그가 없다 — KNL 이 아닐 수 있다."),
    }


def parse_lscpu(text):
    """A1: core/node, 소켓, 스레드, **그리고 ISA flags**."""
    out = {"cpus": None, "sockets": None, "cores_per_socket": None,
           "threads_per_core": None, "model_name": None, "physical_cores": None,
           "flags": None, "isa": None}
    if not text:
        return out
    kv = {}
    for line in text.splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            kv[k.strip()] = v.strip()
    def _i(k):
        try:
            return int(kv[k])
        except (KeyError, ValueError):
            return None
    out["cpus"] = _i("CPU(s)")
    out["sockets"] = _i("Socket(s)")
    out["cores_per_socket"] = _i("Core(s) per socket")
    out["threads_per_core"] = _i("Thread(s) per core")
    out["model_name"] = kv.get("Model name")
    # 🔒 §R23.1 — `flags` 전문. **필터링 금지**(engineer 명시). 없으면 None = [NOT MEASURED].
    flags_line = kv.get("Flags")
    out["flags"] = flags_line.split() if flags_line else None
    out["isa"] = classify_isa(out["flags"])
    # 물리 코어 수 = 소켓 x 소켓당 코어. HT가 켜져 있으면 CPU(s)와 다르다.
    if out["sockets"] and out["cores_per_socket"]:
        out["physical_cores"] = out["sockets"] * out["cores_per_socket"]
    else:
        out["physical_cores"] = out["cpus"]
    return out


#: `free` 출력 1단위가 몇 바이트인가. 우리는 항상 `free -b`로 호출한다.
FREE_UNIT_BYTES = {"b": 1.0, "k": 1024.0, "m": 1024.0 ** 2, "g": 1024.0 ** 3}


def parse_free(text, unit="b"):
    """`free -<unit>` 출력 → RAM GB (십진 GB, 1 GB = 1e9 B).

    단위는 출력에서 알 수 없으므로 **호출자가 명시**한다. 추측하지 않는다
    (RAM을 1024배 틀리게 보고하는 것이 이 분야의 전형적 버그다).
    """
    if not text:
        return None
    scale = FREE_UNIT_BYTES.get(unit, 1.0)
    for line in text.splitlines():
        if line.lower().startswith("mem:"):
            parts = line.split()
            try:
                total = float(parts[1])
            except (IndexError, ValueError):
                return None
            return round(total * scale / 1e9, 1)
    return None


def parse_meminfo(text):
    """/proc/meminfo fallback → RAM GB."""
    if not text:
        return None
    m = re.search(r"^MemTotal:\s+(\d+)\s+kB", text, re.M)
    if not m:
        return None
    return round(int(m.group(1)) * 1024 / 1e9, 1)


def parse_slurm_walltime(s):
    """SLURM 시간 표기 → 시간(float). 'infinite'/'UNLIMITED' → None(=무제한)."""
    if s is None:
        return None
    s = s.strip()
    if not s or s.lower() in ("infinite", "unlimited", "n/a", "none"):
        return None
    days = 0
    if "-" in s:
        d, s = s.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            days = 0
    parts = s.split(":")
    try:
        nums = [float(p) for p in parts]
    except ValueError:
        return None
    if len(nums) == 3:
        h, m, sec = nums
    elif len(nums) == 2:      # MM:SS
        h, m, sec = 0.0, nums[0], nums[1]
    elif len(nums) == 1:      # 분 단위
        h, m, sec = 0.0, nums[0], 0.0
    else:
        return None
    return days * 24 + h + m / 60.0 + sec / 3600.0


def parse_sinfo_partitions(text):
    """`sinfo -h -o '%P|%l|%D|%m|%c'` → A2 파티션 목록.

    %P 파티션(기본 파티션은 '*' 접미), %l 시간상한, %D 노드수, %m MB/node, %c CPU/node
    """
    parts = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or "|" not in line:
            continue
        f = [x.strip() for x in line.split("|")]
        while len(f) < 5:
            f.append("")
        name = f[0]
        default = name.endswith("*")
        entry = {
            "name": name.rstrip("*"),
            "is_default": default,
            "walltime_max_h": parse_slurm_walltime(f[1]),
            "walltime_raw": f[1],
            "nodes": _int_or_none(f[2]),
            "ram_gb_per_node": (round(_int_or_none(f[3]) * 1.048576e-3, 1)
                                if _int_or_none(f[3]) else None),  # MiB -> GB
            "cores_per_node": _int_or_none(f[4]),
        }
        parts.append(entry)
    return parts


def parse_sinfo_gres(text):
    """`sinfo -h -o '%P|%G'` → 클러스터 GPU 유무 (§R2-6: '몰랐던 GPU 노드가 있을 수 있다')."""
    gpu_partitions = []
    for line in (text or "").splitlines():
        if "|" not in line:
            continue
        name, gres = [x.strip() for x in line.split("|", 1)]
        if gres and gres.lower() not in ("(null)", "null", "n/a", ""):
            if "gpu" in gres.lower():
                gpu_partitions.append({"partition": name.rstrip("*"), "gres": gres})
    return gpu_partitions


def parse_scontrol_config(text):
    """A3: MaxJobCount, MaxArraySize, MaxSubmitJobs 등."""
    out = {}
    for key in ("MaxJobCount", "MaxArraySize", "MaxSubmitJobsPerUser",
                "MaxJobCountPerUser", "DefMemPerNode", "SchedulerType",
                # 🔴 계정 강제 여부. 'associations' 가 켜져 있으면 --account 없이는
                #    모든 제출이 거부된다.
                "AccountingStorageEnforce", "AccountingStorageType"):
        m = re.search(r"^%s\s*=\s*(\S+)" % key, text or "", re.M)
        if m:
            out[key] = m.group(1)
    for k in ("MaxJobCount", "MaxArraySize"):
        if k in out:
            out[k] = _int_or_none(out[k]) or out[k]
    return out


#: 🔴 이기종 클러스터: **로그인 노드와 계산 노드의 사양이 다르다.**
#: 사용자 실측 — 로그인 24 core / 계산 68 core(64 사용). 2.7배 차이다.
#: 로그인 값으로 sizing 하면 wall·links·core-h 예약이 전부 어긋나 잡이 잘린다.
RE_PBS_NCPUS = re.compile(r"resources_available\.ncpus\s*=\s*(\d+)")
RE_PBS_NODE = re.compile(r"^([^\s=]+)\s*$")
RE_PBS_MEM = re.compile(r"resources_available\.mem\s*=\s*(\d+)([kmg]b)", re.I)


def parse_pbsnodes(text):
    """`pbsnodes -a` → 노드별 ncpus/mem. **계산 노드의 진짜 사양**.

    반환: {"nodes": [{name, ncpus, mem_gb}], "cores_per_node": 최빈값, "n_nodes": N}
    최빈값을 쓰는 이유: 이기종 클러스터에서 한 노드만 보고 정하면 틀린다.
    """
    nodes = []
    cur = None
    for line in (text or "").splitlines():
        if line and not line[0].isspace() and "=" not in line:
            if cur:
                nodes.append(cur)
            cur = {"name": line.strip(), "ncpus": None, "mem_gb": None}
            continue
        if cur is None:
            continue
        m = RE_PBS_NCPUS.search(line)
        if m:
            cur["ncpus"] = int(m.group(1))
        m = RE_PBS_MEM.search(line)
        if m:
            val, unit = float(m.group(1)), m.group(2).lower()
            factor = {"kb": 1e-6, "mb": 1e-3, "gb": 1.0}[unit]
            cur["mem_gb"] = round(val * factor * 1.073741824, 1)
    if cur:
        nodes.append(cur)
    cpus = [n["ncpus"] for n in nodes if n.get("ncpus")]
    mode = None
    if cpus:
        counts = {}
        for c in cpus:
            counts[c] = counts.get(c, 0) + 1
        mode = max(sorted(counts), key=lambda c: (counts[c], c))
    return {"nodes": nodes[:50], "n_nodes": len(nodes), "cores_per_node": mode,
            "distinct_core_counts": sorted(set(cpus))}


def parse_qstat_queue(text):
    """`qstat -Qf <queue>` → 큐의 자원 상한(있으면)."""
    out = {}
    for key, pat in (("max_walltime_h", r"resources_max\.walltime\s*=\s*(\S+)"),
                     ("max_ncpus", r"resources_max\.ncpus\s*=\s*(\d+)"),
                     ("max_nodect", r"resources_max\.nodect\s*=\s*(\d+)"),
                     ("enabled", r"enabled\s*=\s*(\S+)"),
                     ("started", r"started\s*=\s*(\S+)")):
        m = re.search(pat, text or "")
        if m:
            out[key] = m.group(1)
    if "max_walltime_h" in out:
        out["max_walltime_h"] = parse_slurm_walltime(out["max_walltime_h"])
    return out


def parse_qstat_all_queues(text):
    """`qstat -Qf` (인자 없이) → 큐 **전체** 목록과 각 상한.

    🔴 §R24.2(1): *"큐 하나 보고 24 h 라 단정하지 마라."* 이 사이트에는
    `exclusive / normal / long / debug / flat / commercial` 이 있고 **`long` 이 존재한다**
    `[LITERATURE — 사이트 문서]`. walltime 이 가장 긴 큐로 P1/P1b 를 보내면
    **비용 0 으로 wall 문제가 사라진다.** 이것이 1순위 해법이다.

    🔴 그리고 이것은 이 패키지가 이미 한 번 밟은 함정의 반대편이다: 파티션을
    `sinfo`(SLURM 전용) **한 곳에서만** 읽어 PBS 에서 `-q` 가 통째로 빠졌다.
    이번엔 **하나만 보고 결론내지 않는다.**
    """
    queues = []
    current = None
    for line in (text or "").splitlines():
        m = re.match(r"^Queue:\s*(\S+)", line)
        if m:
            if current:
                queues.append(current)
            current = {"queue": m.group(1)}
            continue
        if current is None:
            continue
        for key, pat in (("max_walltime_h", r"resources_max\.walltime\s*=\s*(\S+)"),
                         ("max_ncpus", r"resources_max\.ncpus\s*=\s*(\d+)"),
                         ("max_nodect", r"resources_max\.nodect\s*=\s*(\d+)"),
                         ("enabled", r"enabled\s*=\s*(\S+)"),
                         ("started", r"started\s*=\s*(\S+)")):
            mm = re.search(pat, line)
            if mm:
                current[key] = mm.group(1)
    if current:
        queues.append(current)
    for q in queues:
        if "max_walltime_h" in q:
            q["max_walltime_h"] = parse_slurm_walltime(q["max_walltime_h"])
    return queues


def longest_wall_queue(queues, require_enabled=True):
    """walltime 상한이 가장 긴 **사용 가능한** 큐. 없으면 None.

    🔴 `enabled = False` 인 큐를 고르면 제출이 거부된다 — 그것도 조용히 왕복 하나를 태운다.
    """
    cands = []
    for q in queues or []:
        if q.get("max_walltime_h") is None:
            continue
        if require_enabled and str(q.get("enabled", "True")).lower() == "false":
            continue
        if require_enabled and str(q.get("started", "True")).lower() == "false":
            continue
        cands.append(q)
    if not cands:
        return None
    return max(cands, key=lambda q: q["max_walltime_h"])


def parse_sacctmgr_assoc(text):
    """`sacctmgr -n -P show assoc user=$USER format=Account,Partition,QOS,MaxJobs,GrpTRES`."""
    rows = []
    for line in (text or "").splitlines():
        if "|" not in line:
            continue
        f = [x.strip() for x in line.split("|")]
        while len(f) < 5:
            f.append("")
        rows.append({"account": f[0], "partition": f[1], "qos": f[2],
                     "max_jobs": _int_or_none(f[3]), "grp_tres": f[4]})
    return rows


def parse_df(text):
    """`df -PT -B1 <paths>` → 파일시스템 항목. A8."""
    rows = []
    lines = (text or "").splitlines()
    for line in lines[1:]:
        f = line.split()
        if len(f) < 7:
            continue
        try:
            size_b, used_b, avail_b = float(f[2]), float(f[3]), float(f[4])
        except ValueError:
            continue
        rows.append({
            "device": f[0], "fs_type": f[1],
            "size_tb": round(size_b / 1e12, 3),
            "used_tb": round(used_b / 1e12, 3),
            "avail_tb": round(avail_b / 1e12, 3),
            "mount": f[6], "path": f[6],
        })
    return rows


def parse_quota(text):
    """`quota -s` / `lfs quota` 출력에서 사용량·상한을 best-effort로 뽑는다.

    포맷이 사이트마다 다르다 → 실패하면 raw 문자열을 그대로 회신한다.
    (파싱 실패를 조용히 0으로 만들지 않는 것이 요점이다.)
    """
    if not text or not text.strip():
        return {"parsed": False, "raw": ""}
    m = re.search(r"(\d+)\s+(\d+)\s+(\d+)", text)
    if not m:
        return {"parsed": False, "raw": text[:1000]}
    return {"parsed": True, "raw": text[:1000],
            "used": int(m.group(1)), "soft": int(m.group(2)), "hard": int(m.group(3)),
            "unit": "unknown(사이트별 상이 — raw 확인 필요)"}


def parse_nvidia_smi(text):
    """`nvidia-smi --query-gpu=name,memory.total --format=csv,noheader` 파싱."""
    gpus = []
    for line in (text or "").splitlines():
        line = line.strip()
        if not line or "," not in line:
            continue
        name, mem = [x.strip() for x in line.split(",", 1)]
        gpus.append({"model": name, "memory": mem})
    return {"present": bool(gpus), "count": len(gpus),
            "model": gpus[0]["model"] if gpus else "",
            "memory": gpus[0]["memory"] if gpus else "",
            "all": gpus}


#: Markers `module avail` appends to a module name. Removed as SUFFIXES, never as char sets.
MODULE_MARKERS = ("(default)", "(D)", "(L)")


def strip_module_markers(token):
    """Remove trailing `module avail` markers from a module name.

    🔴 THIS FUNCTION EXISTS BECAUSE OF A REAL, TOTAL SCIENCE LOSS.

    The old code was::

        tok = tok.rstrip("(default)").strip(":,")

    `str.rstrip("(default)")` does **not** strip the literal suffix. It strips any trailing
    character that appears in the SET ``{ ( d e f a u l t ) }``. So::

        "gaussian/g16.c01.linda"
                             a   -> in set -> stripped
                            d    -> in set -> stripped
                           n     -> not in set -> stop
        => "gaussian/g16.c01.lin"      a module that does not exist

    Every Gaussian job on the cluster then died with
    ``Unable to locate a modulefile for 'gaussian/g16.c01.lin'`` (rc=3):
    P1, P1b, P5 and all three P6 anchors. **κ, S and the TS unit cost were all lost.**

    🔴 Why review did not catch it: of the 13 tokens this line altered on the real cluster,
    **10 were altered correctly** — they really did end in ``(default)``. Only the three
    ``gaussian/*.linda`` entries were corrupted, and the corruption produced a
    **perfectly plausible module name**. The output looked right because it *was* right
    almost everywhere.
    """
    tok = (token or "").strip()
    changed = True
    while changed:                      # a name may carry more than one marker
        changed = False
        for marker in MODULE_MARKERS:
            if tok.endswith(marker):
                tok = tok[:-len(marker)]
                changed = True
    return tok.strip().strip(":,")


def parse_module_avail(text, keywords=None):
    """`module avail` (stderr로 나온다) → 관심 모듈 목록.

    출력이 다열(multi-column)이고 사이트마다 장식이 달라 토큰 단위로 훑는다.
    """
    # 🔴 ADR-043 — 이 화이트리스트가 `mopac` 을 회신에서 지웠다. **목록에 없는 것은
    #    설치돼 있어도 안 나온다.** 지금은 편의 필드일 뿐이고 전문은 `modules_raw` 에 있다.
    #    그래도 목록은 넓혀 둔다(다음에 물을 것들을 미리 포함).
    keywords = keywords or ("cp2k", "orca", "vasp", "qchem", "gaussian", "xtb",
                            "crest", "psi4", "python", "anaconda", "miniconda",
                            "apptainer", "singularity", "cuda", "openmpi",
                            "intel", "mkl", "gcc", "pyscf",
                            "mopac", "nwchem", "dftb", "lammps", "gromacs",
                            "plumed", "openbabel", "quantum", "espresso", "amber",
                            "namd", "molpro", "turbomole", "cmake", "impi")
    found = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("-") or line.startswith("="):
            continue
        for tok in line.split():
            low = tok.lower()
            if any(k in low for k in keywords):
                tok = strip_module_markers(tok)
                if tok and tok not in found:
                    found.append(tok)
    return found


def parse_network_probe(text):
    """계산 노드에서 돌린 network 프로브 스크립트 출력 파싱 (Q2).

    형식: 'https=200', 'git=ok', 'dns=ok' 같은 key=value 줄.
    """
    out = {"https": False, "git": False, "dns": False, "raw": (text or "")[:2000]}
    for line in (text or "").splitlines():
        if "=" not in line:
            continue
        k, v = [x.strip().lower() for x in line.split("=", 1)]
        if k == "https":
            out["https"] = v.startswith("2") or v.startswith("3")
            out["https_code"] = v
        elif k == "git":
            out["git"] = (v == "ok")
        elif k == "dns":
            out["dns"] = (v == "ok")
    return out


def io_rates_from_raw(raw):
    """probe_node.sh가 쓴 원시 타이밍 → 대역폭.

    raw: {"seq_write_bytes":..,"seq_write_s":..,"seq_read_bytes":..,"seq_read_s":..,
          "smallfile_count":..,"smallfile_s":..}
    """
    out = {"seq_write_mbs": None, "seq_read_mbs": None,
           "smallfile_creates_per_s": None}
    if not raw:
        return out
    try:
        if raw.get("seq_write_s"):
            out["seq_write_mbs"] = round(float(raw["seq_write_bytes"]) / 1e6
                                         / float(raw["seq_write_s"]), 1)
        if raw.get("seq_read_s"):
            out["seq_read_mbs"] = round(float(raw["seq_read_bytes"]) / 1e6
                                        / float(raw["seq_read_s"]), 1)
        if raw.get("smallfile_s"):
            out["smallfile_creates_per_s"] = round(float(raw["smallfile_count"])
                                                   / float(raw["smallfile_s"]), 1)
    except (TypeError, ValueError, ZeroDivisionError):
        pass
    out["note"] = ("read는 페이지 캐시를 비울 수 없어 과대평가일 수 있다 "
                   "(권한 없이 drop_caches 불가). write 값이 더 신뢰할 만하다.")
    return out


def _int_or_none(s):
    try:
        return int(str(s).strip())
    except (TypeError, ValueError):
        return None


# --------------------------------------------------------------------------
# 수집기 (부작용 있음 — shell 주입)
# --------------------------------------------------------------------------
def software_inventory(shell, targets=None):
    """which + 버전. 없는 것은 빈 문자열이 아니라 null 로 남긴다(구분 필요).

    🔴 ADR-043: **부재를 보고할 때는 "프로브 대상이었는지"를 함께 보고한다.**
    `null` 은 *"찾아봤는데 없다"* 를 뜻하고, **키 자체가 없으면 *"안 찾아봤다"*** 다.
    이 둘을 구분하지 못해 engineer 가 MOPAC 을 "부재 확정"으로 판정할 뻔했다.
    ⟹ `_probed` 키에 **이번에 실제로 조회한 이름 목록**을 함께 싣는다. 받는 쪽이
    `name in inv["_probed"]` 로 두 경우를 코드로 구분할 수 있다.
    """
    # 🔴 이 딕셔너리는 **순수 매핑**으로 유지한다(name -> entry|None).
    #    프로브 목록은 `collect_login` 이 `software_probed` 로 따로 싣는다 —
    #    여기에 `_probed` 같은 특수 키를 섞었더니 하위 소비자(`report._software_flat`)가
    #    전부 깨졌다. **"같은 자리에 다른 종류를 넣지 마라."**
    names = list(targets or SOFTWARE_TARGETS)
    inv = {}
    for name in names:
        path = shell.which(name)
        if not path:
            inv[name] = None
            continue
        flag = VERSION_FLAG.get(name, "--version")
        cmd = ("%s %s" % (path, flag)).strip()
        res = shell.run(cmd, timeout_s=20)
        blob = (res.out or "") + (res.err or "")
        first = ""
        for line in blob.splitlines():
            if line.strip():
                first = line.strip()[:160]
                break
        inv[name] = {"path": path, "version": first or "unknown"}
    return inv


def collect_login(shell, scratch_candidates=None, queue_hint=None):
    """로그인 노드에서 5분 안에 끝나는 수집분 (§R2-6: dry-run에서도 이것만 돈다)."""
    info = {}
    info["hostname"] = shell.run("hostname -f", timeout_s=10).out.strip() or "unknown"
    info["user"] = os.environ.get("USER") or os.environ.get("LOGNAME") or "unknown"

    lscpu = shell.run("lscpu", timeout_s=20)
    info["login_cpu"] = parse_lscpu(lscpu.out if lscpu.ok else "")

    free = shell.run("free -b", timeout_s=10)
    ram = parse_free(free.out) if free.ok else None
    if ram is None:
        ram = parse_meminfo(shell.read_text("/proc/meminfo") or "")
    info["login_ram_gb"] = ram

    # A2 파티션
    sinfo = shell.run(["sinfo", "-h", "-o", "%P|%l|%D|%m|%c"], timeout_s=30)
    info["partitions"] = parse_sinfo_partitions(sinfo.out) if sinfo.ok else []

    # 클러스터 GPU 유무
    gres = shell.run(["sinfo", "-h", "-o", "%P|%G"], timeout_s=30)
    info["gpu_partitions"] = parse_sinfo_gres(gres.out) if gres.ok else []
    # 🔴 nvidia-smi 가 PATH에 없는 환경이 있다(WSL: /usr/lib/wsl/lib).
    #    경로 목록은 config/env_paths.json 단일 출처에서 온다 — 여기 적지 마라.
    nsmi_bin = envpaths.resolve_tool(shell, "nvidia-smi")
    if nsmi_bin:
        nsmi = shell.run("%s --query-gpu=name,memory.total --format=csv,noheader"
                         % nsmi_bin, timeout_s=20)
        info["login_gpus"] = parse_nvidia_smi(nsmi.out) if nsmi.ok else {
            "present": False, "count": 0, "model": "", "all": [],
            "note": "nvidia-smi 는 있으나 실행이 실패했다: %s" % (nsmi.err or "")[:120]}
        info["login_gpus"]["nvidia_smi_path"] = nsmi_bin
    else:
        info["login_gpus"] = {"present": False, "count": 0, "model": "", "all": [],
                              "note": "nvidia-smi 를 찾지 못했다(PATH + %s)"
                                      % ", ".join(envpaths.extra_search_paths())}

    # A3 동시 job 상한
    cfg = shell.run("scontrol show config", timeout_s=30)
    info["slurm_config"] = parse_scontrol_config(cfg.out) if cfg.ok else {}
    assoc = shell.run(["sacctmgr", "-n", "-P", "show", "assoc",
                       "user=" + info["user"],
                       "format=Account,Partition,QOS,MaxJobs,GrpTRES"], timeout_s=30)
    info["assoc"] = parse_sacctmgr_assoc(assoc.out) if assoc.ok else []

    # 🔴 계산 노드 사양 (PBS). 로그인 노드와 다를 수 있고, 실제로 달랐다.
    info["compute_nodes"] = {}
    if shell.which("pbsnodes"):
        pn = shell.run("pbsnodes -a", timeout_s=60)
        if pn.ok:
            info["compute_nodes"] = parse_pbsnodes(pn.out)
            info["compute_nodes"]["source"] = "pbsnodes -a"
    if shell.which("qstat"):
        # 🔒 §R24.2(1) — **전체 큐를 먼저 읽는다.** 하나만 보고 24 h 라 단정하지 않는다.
        qall = shell.run(["qstat", "-Qf"], timeout_s=45)
        if qall.ok and qall.out.strip():
            info["queues"] = parse_qstat_all_queues(qall.out)
            info["queues_raw"] = qall.out
        for q in (queue_hint, "normal", "batch"):
            if not q:
                continue
            qq = shell.run(["qstat", "-Qf", q], timeout_s=30)
            if qq.ok and qq.out.strip():
                info["queue_info"] = parse_qstat_queue(qq.out)
                info["queue_info"]["queue"] = q
                break

    # A8 스크래치 후보
    info["filesystems"] = detect_filesystems(shell, scratch_candidates)

    # 소프트웨어 인벤토리
    info["software"] = software_inventory(shell)
    # 🔒 ADR-043 — **"없다"와 "안 찾아봤다"를 받는 쪽이 구분할 수 있게 한다.**
    #    `software[name] is None` = 찾아봤는데 없음 / `name not in software_probed` = 미조회.
    info["software_probed"] = list(SOFTWARE_TARGETS)
    # 🔒 ADR-050 — 탐지 결과 옆에 **정책**을 함께 싣는다.
    #    🔴 "있다"와 "써도 된다"는 다른 질문이다. 둘을 한 필드에 섞으면
    #    다음 사람이 "설치돼 있으니 쓰자"로 읽는다.
    info["engine_policy"] = dict(
        (name, engine_policy(name)) for name in SOFTWARE_TARGETS)
    info["software_probe_note"] = (
        "🔴 `software` 에 없는 이름은 **부재가 아니라 미조회**다. 부재를 주장하려면 "
        "그 이름이 `software_probed` 에 있는지 먼저 확인하라. "
        "(실제 사고: `mopac` 이 목록에 없어 회신에 안 나왔고, 그것을 'MOPAC 부재 확정'으로 "
        "읽어 축 3 을 탈락시킬 뻔했다.)")
    # 🔴 ADR-043 — 예전에는 `| head -400` 로 잘랐다. 실클러스터 회신의 modules 가 32개뿐이었고
    #    orca/lammps/gromacs/QE 가 하나도 없었다. Nurion 급 기계에 없을 리 없다 ⟹ **부분
    #    목록이었고, 그것을 부재 증거로 쓸 뻔했다.** 절단을 없애고 **전문을 raw 로 싣는다.**
    mavail = shell.run("bash -lc 'module avail 2>&1'", timeout_s=90)
    mtext = (mavail.out or "") + (mavail.err or "")
    info["modules"] = parse_module_avail(mtext) if mavail.rc != 127 else []
    info["modules_raw"] = mtext if mavail.rc != 127 else None
    info["modules_raw_note"] = (
        "🔴 `modules` 는 키워드로 걸러낸 **편의 필드**다. 그 목록에 없다고 부재의 근거로 "
        "쓰지 마라 — 걸러진 것일 수 있다. 부재를 주장하려면 `modules_raw`(전문)를 보라. "
        "raw 가 null 이면 `module` 명령 자체가 없었다는 뜻이다.")

    # Q2: 로그인 노드 기준 (계산 노드 기준은 probe_node 잡이 따로 잰다)
    info["outbound_network_login"] = probe_network(shell)
    return info


def detect_filesystems(shell, candidates=None):
    """A8: 스크래치 후보 경로 탐지 + 용량/쿼터."""
    env_names = ["SCRATCH", "WORK", "TMPDIR", "PSCRATCH", "LOCAL_SCRATCH", "HOME"]
    paths = []
    for name in env_names:
        v = os.environ.get(name)
        if v and v not in [p["path"] for p in paths]:
            paths.append({"path": v, "source": "$" + name})
    for extra in (candidates or ["/scratch", "/lustre", "/work", "/tmp"]):
        if shell.exists(extra) and extra not in [p["path"] for p in paths]:
            paths.append({"path": extra, "source": "well-known"})

    out = []
    for p in paths:
        res = shell.run(["df", "-PT", "-B1", p["path"]], timeout_s=20)
        rows = parse_df(res.out) if res.ok else []
        entry = dict(p)
        entry.update(rows[0] if rows else {"fs_type": None, "avail_tb": None})
        entry["writable"] = os.access(p["path"], os.W_OK) if os.path.isdir(p["path"]) else False
        out.append(entry)

    q = shell.run("quota -s", timeout_s=20)
    quota = parse_quota((q.out or "") + (q.err or "")) if q.rc != 127 else {"parsed": False, "raw": "quota 명령 없음"}
    for e in out:
        if e.get("fs_type") == "lustre":
            lq = shell.run(["lfs", "quota", "-h", e["path"]], timeout_s=20)
            if lq.ok:
                e["lfs_quota_raw"] = lq.out[:800]
    return {"candidates": out, "quota": quota}


def probe_network(shell, urls=None):
    """Q2 outbound. curl → wget → python urllib 순으로 시도.

    🔴 이 결과가 U-09(FireWorks vs Snakemake+파일큐)를 가른다 (§R2-8).
    """
    urls = urls or ["https://pypi.org/simple/", "https://github.com"]
    out = {"https": False, "git": False, "dns": False, "method": None, "details": []}
    dns = shell.run("getent hosts pypi.org", timeout_s=15)
    out["dns"] = dns.ok and bool(dns.out.strip())
    for url in urls:
        if shell.which("curl"):
            r = shell.run(["curl", "-sS", "-m", "12", "-o", "/dev/null",
                           "-w", "%{http_code}", url], timeout_s=25)
            code = (r.out or "").strip()
            out["details"].append({"url": url, "tool": "curl", "code": code, "rc": r.rc})
            if r.ok and code[:1] in ("2", "3"):
                out["https"] = True
                out["method"] = "curl"
        elif shell.which("wget"):
            r = shell.run(["wget", "-q", "-T", "12", "-O", "/dev/null", url], timeout_s=25)
            out["details"].append({"url": url, "tool": "wget", "rc": r.rc})
            if r.ok:
                out["https"] = True
                out["method"] = "wget"
    if shell.which("git"):
        r = shell.run("git ls-remote https://github.com/git/git HEAD", timeout_s=30)
        out["git"] = r.ok and bool((r.out or "").strip())
        out["details"].append({"tool": "git", "rc": r.rc})
    return out
