"""구성요소 C — 회신 파일 `sei_probe_report.json` 조립.

§R2-6: "이 JSON 하나만 받으면 내가 §R2-1·§R2-3·§R2-5를 전부 실측 기반으로 개정할 수
있다. 그것이 이 형식의 유일한 설계 목표다."

스키마는 §R2-6의 1.0을 **한 필드도 빼지 않고** 유지하고, 1.1에서 필드만 추가했다
(version.SCHEMA_EXTENSIONS에 추가 사유가 기록돼 있다).
"""

from . import version

REQUIRED_TOP = ["schema_version", "profile", "generated_at", "hostname", "scheduler",
                "cluster", "throughput_probe", "queue_wait_probe", "pilots",
                "failures"]
REQUIRED_CLUSTER = ["cores_per_node", "ram_gb_per_node", "nodes_total",
                    "partitions", "max_concurrent_jobs", "max_array_size",
                    "scratch", "io_bench", "software", "outbound_network", "gpus"]


def _pick_scratch(filesystems):
    """A8: 여러 후보 중 '가장 큰 쓰기 가능한 것'을 대표 scratch로 고른다."""
    best = None
    for fs in filesystems or []:
        if fs.get("avail_tb") is None:
            continue
        if not fs.get("writable", True):
            continue
        if best is None or (fs["avail_tb"] or 0) > (best["avail_tb"] or 0):
            best = fs
    if not best:
        return {"path": None, "avail_tb": None, "quota_tb": None, "fs_type": None,
                "note": "쓰기 가능한 스크래치를 찾지 못했다 (A8 미측정)"}
    return {"path": best.get("path") or best.get("mount"),
            "avail_tb": best.get("avail_tb"),
            "quota_tb": None,          # 쿼터는 사이트별 포맷 → quota_raw 참조
            "fs_type": best.get("fs_type"),
            "source": best.get("source")}


def _software_flat(software):
    """{"cp2k": {"path":..,"version":..}} → {"cp2k": "version 문자열 또는 ''"}"""
    out = {}
    for name, entry in (software or {}).items():
        out[name] = (entry or {}).get("version", "") if entry else ""
    return out


def build_report(login, node_probe, plan, plan_summary, guard, pilots,
                 throughput, queue_wait, failures, package_root=None,
                 invocation=None, seed=None, unresolved=None, profile="cpu"):
    """모든 조각 → 회신 JSON 1개. 조각이 없으면 null로 남기고 사유를 failures에 남긴다."""
    login = login or {}
    node_probe = node_probe or {}
    cpu = node_probe.get("cpu") or login.get("login_cpu") or {}
    partitions = login.get("partitions") or []
    slurm_cfg = login.get("slurm_config") or {}

    # 🔴 [MAJOR/lead 판정] `cores_per_node` 자리에는 **계산 노드에서 온 값만** 앉힌다.
    #    로그인 노드 값이 그 자리에 앉으면 소비자는 그것을 계산 노드 사양으로 읽는다.
    #    실제로 그렇게 로그인 24코어가 engineer 에게 넘어가 §R16 한 라운드가 통째로
    #    그 위에 세워졌다(ADR-034). engineer 자평:
    #      "[MEASURED] 는 '측정됐다'이지 '무엇을 측정했는지 안다'가 아니다."
    #    ⇒ 확정 못 하면 **null**. 경고 문자열은 사람만 읽지만 null 은 코드도 읽는다.
    compute_cpu = node_probe.get("cpu") or {}          # 계산 노드에서 실행된 프로브
    cores_per_node = compute_cpu.get("physical_cores") or compute_cpu.get("cpus")
    cores_source = "probe_node (계산 노드에서 실행)" if cores_per_node else None
    if not cores_per_node and partitions:
        cores_per_node = partitions[0].get("cores_per_node")
        cores_source = "scheduler partition 정보" if cores_per_node else None
    login_only_cores = None
    if not cores_per_node:
        # 로그인 노드 값밖에 없다 → 자리에 앉히지 않고 별도 키에 보존한다.
        login_only_cores = (cpu.get("physical_cores") or cpu.get("cpus")
                            or (login.get("login_cpu") or {}).get("physical_cores"))
        cores_source = None

    nodes_total = sum(p.get("nodes") or 0 for p in partitions) or None

    gpus = node_probe.get("gpus") or login.get("login_gpus") or {
        "present": False, "count": 0, "model": ""}
    if login.get("gpu_partitions"):
        gpus = dict(gpus)
        gpus["present"] = True
        gpus["slurm_gres_partitions"] = login["gpu_partitions"]

    net_node = node_probe.get("outbound_network") or {}
    net_login = login.get("outbound_network_login") or {}
    outbound = {
        "https": bool(net_node.get("https")),
        "git": bool(net_node.get("git")),
        "measured_on": "compute_node" if net_node else "not_measured",
        "login_node": {"https": bool(net_login.get("https")),
                       "git": bool(net_login.get("git")),
                       "dns": bool(net_login.get("dns"))},
        "decides": "U-09 Case A(FireWorks) vs Case B(Snakemake+파일큐). §R2-8",
    }

    report = {
        "schema_version": version.SCHEMA_VERSION,
        # 🔴 CPU 클러스터와 GPU 머신이 분리돼 있어 회신 파일이 둘이다.
        #    머지 도구가 이 필드로 두 파일을 구분한다.
        "profile": profile,
        "schema_base_version": version.SCHEMA_BASE_VERSION,
        "schema_extensions": version.SCHEMA_EXTENSIONS,
        "generated_at": None,        # provenance에서 채운다 (아래)
        "hostname": login.get("hostname", "unknown"),
        "scheduler": login.get("scheduler", "unknown"),
        "provenance": version.provenance(package_root, seed=seed,
                                         invocation=invocation),
        "run": {
            "mode": (invocation or {}).get("mode") if isinstance(invocation, dict) else None,
            "resume_count": (invocation or {}).get("resume_count") if isinstance(invocation, dict) else None,
        },
        "guard": guard.to_dict() if guard else None,
        "plan": plan,
        "plan_summary": plan_summary,
        "cluster": {
            "cores_per_node": cores_per_node,          # 🔴 미확정이면 null 이다
            "cores_per_node_source": cores_source,
            # 버리지 않는다 — 다만 위 자리에는 앉히지 않는다.
            "cores_per_node_login_fallback": login_only_cores,
            "cores_per_node_note": (
                None if cores_per_node else
                "🔴 계산 노드 코어 수 미확정. cores_per_node 는 의도적으로 null 이다. "
                "cores_per_node_login_fallback 은 **로그인 노드** 값이며 계산 노드와 "
                "다를 수 있다(실제로 24 vs 64 로 어긋난 적이 있다). "
                "이 값으로 봉투를 계산하지 마라."),
            "ram_gb_per_node": node_probe.get("ram_gb_per_node") or login.get("login_ram_gb"),
            "nodes_total": nodes_total,
            "partitions": [{"name": p.get("name"),
                            "walltime_max_h": p.get("walltime_max_h"),
                            "nodes": p.get("nodes"),
                            "cores_per_node": p.get("cores_per_node"),
                            "ram_gb_per_node": p.get("ram_gb_per_node"),
                            "is_default": p.get("is_default")}
                           for p in partitions],
            "max_concurrent_jobs": slurm_cfg.get("MaxJobCount"),
            "max_array_size": slurm_cfg.get("MaxArraySize"),
            "scratch": _pick_scratch((node_probe.get("filesystems") or [])
                                     or ((login.get("filesystems") or {}).get("candidates"))),
            "io_bench": node_probe.get("io_bench") or {
                "seq_write_mbs": None, "seq_read_mbs": None,
                "smallfile_creates_per_s": None, "note": "미측정"},
            "software": _software_flat(login.get("software")),
            "outbound_network": outbound,
            "gpus": gpus,
            # --- 1.1 확장 ---
            "cpu": cpu,
            "filesystems": (node_probe.get("filesystems")
                            or (login.get("filesystems") or {}).get("candidates") or []),
            "quota": (login.get("filesystems") or {}).get("quota"),
            "scheduler_detail": {"slurm_config": slurm_cfg,
                                 "assoc": login.get("assoc") or []},
            "modules": login.get("modules") or [],
            # 🔒 ADR-043 — `modules` 는 **키워드로 걸러낸 편의 필드**다. 부재를 주장하려면
            #    전문을 봐야 한다. 전문을 안 실으면 필터가 지운 것을 "없다"로 읽게 된다.
            "modules_raw": login.get("modules_raw"),
            "modules_raw_note": login.get("modules_raw_note"),
            "software_detail": login.get("software") or {},
            # 🔒 ADR-043 — "없다"와 "안 찾아봤다"를 받는 쪽이 구분할 수 있게 한다.
            "software_probed": login.get("software_probed"),
            "software_probe_note": login.get("software_probe_note"),
            # 🔒 ADR-050 — **있다 ≠ 써도 된다.** 탐지 결과 옆에 정책을 싣는다.
            "engine_policy": login.get("engine_policy"),
            "queues": login.get("queues"),
            "queues_raw": login.get("queues_raw"),
            "login_user": login.get("user"),
        },
        "throughput_probe": throughput or {"jobs_submitted": 0, "accepted": 0,
                                           "start_rate_per_min": None,
                                           "max_concurrent_observed": None,
                                           "status": "not_run"},
        "queue_wait_probe": queue_wait or [],
        "pilots": pilots or [],
        "failures": failures or [],
        "unresolved_for_lead": list(unresolved or []),
    }
    # 🔴 코어 수 미확정은 **회신에서 가장 비싼 미지수**다(봉투가 여기 정비례한다).
    #    사람이 표를 훑다 놓치지 않도록 unresolved 에도 반드시 올린다.
    if not cores_per_node:
        report["unresolved_for_lead"].append({
            "item": "cluster.cores_per_node",
            "severity": "blocker",
            "what": "계산 노드 코어 수 미확정 — 이 값으로 봉투를 계산하지 마라.",
            "why": ("probe_node 가 계산 노드에서 실행되지 않았거나 스케줄러에서 노드 "
                    "사양을 읽지 못했다. 로그인 노드 값(%s)은 계산 노드와 다를 수 "
                    "있다 — 실제로 24 vs 64 로 어긋나 한 라운드의 견적이 통째로 "
                    "틀린 적이 있다(ADR-034)." % login_only_cores),
            "action": ("계산 노드의 코어 수를 확인해 `./run.sh --cores-per-node <N>` 로 "
                       "다시 제출하거나, `pbsnodes -a` / `sinfo -o %c` 출력을 회신하라."),
            "value_withheld": login_only_cores,
        })
    report["generated_at"] = report["provenance"]["generated_at_utc"]
    return report


REQUIRED_MERGED_TOP = ["schema_version", "profile", "merged_from", "by_profile",
                       "pilots", "failures", "merge_warnings"]


def validate_merged_report(report):
    """머지 결과는 단일 프로파일 리포트와 **모양이 다르다.**

    단일 스키마를 억지로 통과시키려고 빈 필드를 채워 넣으면 "측정했다"처럼 보인다.
    그래서 머지본은 머지본 규약으로 검증한다.
    """
    problems = []
    for k in REQUIRED_MERGED_TOP:
        if k not in report:
            problems.append("missing merged key: %s" % k)
    bp = report.get("by_profile") or {}
    if not bp:
        problems.append("by_profile 이 비었다 — 프로파일 원본이 보존되지 않았다")
    for prof, block in bp.items():
        for k in ("cluster", "guard", "provenance"):
            if k not in block:
                problems.append("by_profile[%s] 에 %s 가 없다" % (prof, k))
    for p in report.get("pilots") or []:
        if "profile" not in p:
            problems.append("pilot %s 에 profile 태그가 없다" % p.get("id"))
    return problems


def validate_report(report):
    """스키마 최소 검증. 반환: 문제 목록(비어 있으면 통과)."""
    if (report or {}).get("profile") == "merged":
        return validate_merged_report(report)
    problems = []
    for k in REQUIRED_TOP:
        if k not in report:
            problems.append("missing top-level key: %s" % k)
    cluster = report.get("cluster") or {}
    for k in REQUIRED_CLUSTER:
        if k not in cluster:
            problems.append("missing cluster key: %s" % k)
    if not isinstance(report.get("pilots"), list):
        problems.append("pilots must be a list")
    else:
        for p in report["pilots"]:
            if "id" not in p or "status" not in p:
                problems.append("pilot entry missing id/status: %s"
                                % sorted(p.keys())[:5])
            elif p["status"] not in ("pass", "fail", "skipped", "incomplete",
                                     "undetermined"):
                problems.append("pilot %s has invalid status %r" % (p.get("id"), p["status"]))
    if not isinstance(report.get("failures"), list):
        problems.append("failures must be a list")
    return problems


def merge_reports(reports):
    """🔴 프로파일별 회신 JSON들을 **손실 없이** 하나로 합친다.

    설계 원칙: **합치면서 무엇도 버리지 않는다.**
      * 프로파일 고유 정보(cluster/guard/plan/throughput/queue_wait)는
        `by_profile[<profile>]` 아래에 **원본 그대로** 보존한다.
      * pilots/failures/unresolved 는 이어붙이되 각 항목에 `profile` 을 태깅한다.
      * 같은 파일럿 id가 두 프로파일에 있으면 **둘 다 남긴다**(덮어쓰지 않는다).
        그런 일이 생기면 `merge_warnings` 에 올린다 — 프로파일이 섞였다는 신호다.
    """
    reports = [r for r in reports if r]
    if not reports:
        raise ValueError("합칠 리포트가 없다")
    warnings = []
    by_profile = {}
    pilots = []
    failures = []
    unresolved = []
    seen_pilot = {}

    for rep in reports:
        prof = rep.get("profile") or "unknown"
        if prof in by_profile:
            warnings.append("같은 프로파일(%s) 리포트가 2개 이상이다 — 나중 것이 "
                            "by_profile 에서 덮이지 않도록 %s_2 로 보관한다" % (prof, prof))
            prof_key = prof + "_2"
        else:
            prof_key = prof
        by_profile[prof_key] = {
            "hostname": rep.get("hostname"), "scheduler": rep.get("scheduler"),
            "generated_at": rep.get("generated_at"),
            "provenance": rep.get("provenance"), "guard": rep.get("guard"),
            "cluster": rep.get("cluster"), "plan": rep.get("plan"),
            "plan_summary": rep.get("plan_summary"),
            "throughput_probe": rep.get("throughput_probe"),
            "queue_wait_probe": rep.get("queue_wait_probe"),
        }
        for p in rep.get("pilots") or []:
            item = dict(p)
            item["profile"] = prof
            pid = item.get("id")
            if pid in seen_pilot:
                warnings.append("파일럿 %s 가 %s 와 %s 양쪽에 있다 — 둘 다 보존했다. "
                                "프로파일 분리가 어긋났는지 확인하라"
                                % (pid, seen_pilot[pid], prof))
            else:
                seen_pilot[pid] = prof
            pilots.append(item)
        for f in rep.get("failures") or []:
            item = dict(f)
            item["profile"] = prof
            failures.append(item)
        for u in rep.get("unresolved_for_lead") or []:
            item = dict(u)
            item["profile"] = prof
            unresolved.append(item)

    merged = {
        "schema_version": version.SCHEMA_VERSION,
        "profile": "merged",
        "merged_from": sorted(by_profile.keys()),
        "generated_at": max(r.get("generated_at") or "" for r in reports),
        "hostname": " + ".join(str(r.get("hostname")) for r in reports),
        "scheduler": " + ".join(str(r.get("scheduler")) for r in reports),
        "provenance": version.provenance(None, invocation={"mode": "merge"}),
        "by_profile": by_profile,
        "pilots": pilots,
        "failures": failures,
        "unresolved_for_lead": unresolved,
        "merge_warnings": warnings,
        # 스키마 검증을 통과시키기 위한 대표값 (원본은 by_profile 에 그대로 있다)
        "cluster": (reports[0].get("cluster") or {}),
        "throughput_probe": next((r.get("throughput_probe") for r in reports
                                  if (r.get("throughput_probe") or {}).get("jobs_started")),
                                 reports[0].get("throughput_probe")),
        "queue_wait_probe": [e for r in reports for e in (r.get("queue_wait_probe") or [])],
        "_cluster_note": "대표값은 첫 리포트의 것이다. 프로파일별 원본은 by_profile 을 보라.",
    }
    return merged


def merge_counts(merged):
    """머지 손실 점검용 카운트 (테스트/사용자 확인)."""
    return {"profiles": len(merged.get("by_profile") or {}),
            "pilots": len(merged.get("pilots") or []),
            "failures": len(merged.get("failures") or []),
            "unresolved": len(merged.get("unresolved_for_lead") or []),
            "warnings": len(merged.get("merge_warnings") or [])}


def summarize_for_user(report):
    """사용자 콘솔용 한 화면 요약. 사용자는 이 이상 판단하지 않는다."""
    L = ["", "=" * 66, " 결과 요약 — 이 파일 1개를 회신해 주세요:", ""]
    L.append("   results/sei_probe_report.json")
    L.append("=" * 66)
    c = report.get("cluster") or {}
    L.append(" 스케줄러 %s | core/node %s | RAM %s GB | 파티션 %d개"
             % (report.get("scheduler"), c.get("cores_per_node"),
                c.get("ram_gb_per_node"), len(c.get("partitions") or [])))
    L.append(" GPU: %s | outbound HTTPS: %s"
             % ((c.get("gpus") or {}).get("present"),
                (c.get("outbound_network") or {}).get("https")))
    L.append("")
    for p in report.get("pilots") or []:
        line = "   %-5s %-10s" % (p.get("id"), p.get("status"))
        if p.get("status") == "skipped":
            line += " (%s)" % (p.get("skip_reason") or "")[:44]
        else:
            line += " core-h=%s" % p.get("core_hours_total")
            if p.get("fail_reasons"):
                line += "  <- %s" % "; ".join(p["fail_reasons"])[:60]
        L.append(line)
    fails = report.get("failures") or []
    L.append("")
    L.append(" 실패 기록 %d건 (전부 JSON의 failures[]에 있습니다)" % len(fails))
    L.append("=" * 66)
    return "\n".join(L)
