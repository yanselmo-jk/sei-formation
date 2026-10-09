"""🔴 CPU/GPU 패키지 분리의 **신규 실패 모드** 회귀 테스트.

lead 지목: 이번 변경이 만드는 새 실패 모드는 두 가지다.
  (1) **프로파일이 섞이는 것** — GPU 패키지에 P1이 들어가거나 CPU 패키지에 P4가 남으면
      사용자가 엉뚱한 머신에서 엉뚱한 계산을 돌린다.
  (2) **머지에서 항목이 소실되는 것** — 두 회신을 합치다 조용히 잃으면 lead는 그걸 모른다.

두 실패 모드를 **실제로 재현하는 입력**으로 검증한다(양성 대조군 포함).
"""

import io
import json
import os
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import budget, cli, plan, report
from sei_pilot.criteria import p5 as p5_mod

# 🔒 의도된 변화 (§R22.10): P6_t1/t16/t64 = κ 앵커. **회귀가 아니다.**
#    사유: "§R21 KNL 판명(κ=3.4~6.8)에 따른 재산정. 종전 값은 κ=1 단위였다."
#    κ 는 이 프로젝트 모든 core-h 의 **단위**인데 지금 문헌 유도 [ESTIMATE] 뿐이고
#    총액을 5배 흔든다. 3항목인 이유는 PBS array 가 태스크마다 ncpus 를 못 바꾸기 때문이다.
CPU_ONLY = {"probe_node", "probe_throughput", "probe_queuewait",
            "P1", "P1b", "P5", "P6_t1", "P6_t16", "P6_t64",
            "endpoint_prep_reactant",   # 🔒 ADR-049: P3 제거 / ADR-099: endpoint_prep 신설
            # [user ruling 2026-08-21] the EpsInf bracket sibling is gone (acetone carrier deck).
            # [coder13, 2026-08-21] u56_2.released=true (lead/사용자 승인, ADR-109 ruling 2) —
            # U56-2 의 5항목 전부 CPU/G16.
            "endpoint_prep_product", "endpoint_prep_rc_reactant",
            "U56_RA_scan", "U56_RA_qst2", "U56_RB_scan"}
GPU_ONLY = {"probe_gpu_node", "P4"}


class TestProfileSeparation(unittest.TestCase):
    def _keys(self, profile):
        return set(i.key for i in plan.default_items(profile))

    def test_cpu_profile_item_set_is_exact(self):
        self.assertEqual(self._keys("cpu"), CPU_ONLY)

    def test_gpu_profile_item_set_is_exact(self):
        self.assertEqual(self._keys("gpu"), GPU_ONLY)

    def test_profiles_do_not_overlap(self):
        self.assertEqual(self._keys("cpu") & self._keys("gpu"), set())

    def test_p4_is_not_in_cpu_package(self):
        """🔴 실패 모드 (1): CPU 클러스터에 GPU 잡을 던지면 안 된다."""
        self.assertNotIn("P4", self._keys("cpu"))

    def test_p1_p5_are_not_in_gpu_package(self):
        """🔴 실패 모드 (1) 반대 방향: GPU 머신에서 24시간짜리 TS를 돌리면 안 된다."""
        for key in ("P1", "P1b", "P2", "P5"):
            self.assertNotIn(key, self._keys("gpu"), key)

    def test_every_item_declares_at_least_one_profile(self):
        for it in plan._all_items():
            self.assertTrue(it.profiles, it.key)
            for prof in it.profiles:
                self.assertIn(prof, plan.PROFILES, it.key)

    def test_all_items_are_covered_by_the_two_profiles(self):
        """어느 프로파일에도 안 들어간 항목은 **영원히 실행되지 않는다.**"""
        covered = self._keys("cpu") | self._keys("gpu")
        self.assertEqual(set(i.key for i in plan._all_items()), covered)

    def test_unknown_profile_is_rejected(self):
        self.assertRaises(ValueError, plan.default_items, "tpu")

    def test_payload_file_exists_for_every_item(self):
        """계획에만 있고 payload가 없으면 제출 후에야 발견된다(왕복 1회 낭비)."""
        for it in plan._all_items():
            path = os.path.join(context.PKG_ROOT, it.payload)
            self.assertTrue(os.path.exists(path), "%s → %s" % (it.key, it.payload))

    def test_plan_summary_carries_profile(self):
        env = {"scheduler": "none", "cores_per_node": 32, "software": {}, "gpus": {}}
        for prof in ("cpu", "gpu"):
            _p, s = plan.build_plan(env, budget.guard_for_profile(prof), profile=prof)
            self.assertEqual(s["profile"], prof)

    def test_report_filename_differs_per_profile(self):
        self.assertEqual(cli.report_filename("cpu"), "sei_probe_report.cpu.json")
        self.assertEqual(cli.report_filename("gpu"), "sei_probe_report.gpu.json")
        self.assertNotEqual(cli.report_filename("cpu"), cli.report_filename("gpu"))


def _rep(profile, pilots, failures=(), unresolved=(), host="h"):
    return {"schema_version": "1.1", "profile": profile, "hostname": host,
            "scheduler": "slurm" if profile == "cpu" else "none",
            "generated_at": "2026-08-17T0%d:00:00Z" % (1 if profile == "cpu" else 2),
            "guard": {"max_core_hours": 5000.0}, "plan": [], "plan_summary": {},
            "provenance": {"package_version": "0.1.0"},
            "cluster": {"cores_per_node": 128 if profile == "cpu" else 32},
            "throughput_probe": {"jobs_submitted": 200, "jobs_started": 200},
            "queue_wait_probe": [{"nodes": 1, "wait_s": 5}],
            "pilots": list(pilots), "failures": list(failures),
            "unresolved_for_lead": list(unresolved)}


class TestMergeLossless(unittest.TestCase):
    """🔴 실패 모드 (2): 머지에서 항목이 소실되는 것."""

    def setUp(self):
        self.cpu = _rep("cpu",
                        [{"id": "P1", "status": "pass", "core_hours_total": 900},
                         {"id": "P5", "status": "pass", "species_rows": [1, 2, 3]}],
                        failures=[{"id": "P2", "reason": "scf_failed"}],
                        unresolved=[{"item": "A"}, {"item": "B"}], host="hpc")
        self.gpu = _rep("gpu",
                        [{"id": "P4", "status": "pass", "gpu_hours_total": 0.5}],
                        failures=[],
                        unresolved=[{"item": "C"}], host="gpubox")
        self.m = report.merge_reports([self.cpu, self.gpu])

    def test_no_pilot_is_lost(self):
        ids = [p["id"] for p in self.m["pilots"]]
        self.assertEqual(sorted(ids), ["P1", "P4", "P5"])

    def test_pilot_payload_is_preserved_not_truncated(self):
        p5 = [p for p in self.m["pilots"] if p["id"] == "P5"][0]
        self.assertEqual(p5["species_rows"], [1, 2, 3])
        p4 = [p for p in self.m["pilots"] if p["id"] == "P4"][0]
        self.assertEqual(p4["gpu_hours_total"], 0.5)

    def test_every_pilot_is_tagged_with_its_profile(self):
        by = dict((p["id"], p["profile"]) for p in self.m["pilots"])
        self.assertEqual(by, {"P1": "cpu", "P5": "cpu", "P4": "gpu"})

    def test_failures_and_unresolved_are_concatenated(self):
        self.assertEqual(len(self.m["failures"]), 1)
        self.assertEqual(sorted(u["item"] for u in self.m["unresolved_for_lead"]),
                         ["A", "B", "C"])

    def test_profile_specific_blocks_are_preserved_verbatim(self):
        self.assertEqual(self.m["by_profile"]["cpu"]["cluster"]["cores_per_node"], 128)
        self.assertEqual(self.m["by_profile"]["gpu"]["cluster"]["cores_per_node"], 32)
        self.assertEqual(self.m["by_profile"]["cpu"]["hostname"], "hpc")
        self.assertEqual(self.m["by_profile"]["gpu"]["hostname"], "gpubox")

    def test_counts_match_the_sum_of_inputs(self):
        c = report.merge_counts(self.m)
        self.assertEqual(c["pilots"],
                         len(self.cpu["pilots"]) + len(self.gpu["pilots"]))
        self.assertEqual(c["failures"],
                         len(self.cpu["failures"]) + len(self.gpu["failures"]))
        self.assertEqual(c["unresolved"],
                         len(self.cpu["unresolved_for_lead"])
                         + len(self.gpu["unresolved_for_lead"]))
        self.assertEqual(c["warnings"], 0)

    def test_merged_report_passes_its_own_schema(self):
        """머지본은 모양이 다르다 — 단일 스키마를 억지로 통과시키려고 빈 필드를
        채워 넣으면 '측정했다'처럼 보인다. 그래서 머지본 규약으로 검증한다."""
        self.assertEqual(report.validate_report(self.m), [])
        self.assertEqual(report.validate_merged_report(self.m), [])

    def test_merged_validation_catches_lost_profile_block(self):
        broken = dict(self.m)
        broken["by_profile"] = {}
        self.assertTrue(report.validate_merged_report(broken))

    def test_merged_validation_catches_untagged_pilot(self):
        broken = dict(self.m, pilots=[{"id": "P1", "status": "pass"}])
        self.assertTrue(any("profile 태그" in x
                            for x in report.validate_merged_report(broken)))

    def test_duplicate_pilot_across_profiles_is_kept_and_warned(self):
        """🔴 양성 대조군: 프로파일이 섞이면 **덮어쓰지 않고 경고**해야 한다."""
        gpu_bad = _rep("gpu", [{"id": "P1", "status": "fail"}])
        m = report.merge_reports([self.cpu, gpu_bad])
        ids = [p["id"] for p in m["pilots"]]
        self.assertEqual(ids.count("P1"), 2)          # 둘 다 보존
        self.assertTrue(any("P1" in w for w in m["merge_warnings"]))

    def test_same_profile_twice_is_warned_not_silently_dropped(self):
        m = report.merge_reports([self.cpu, self.cpu])
        self.assertEqual(len(m["by_profile"]), 2)      # cpu, cpu_2
        self.assertTrue(m["merge_warnings"])

    def test_merge_of_empty_list_raises(self):
        self.assertRaises(ValueError, report.merge_reports, [])

    def test_merge_survives_missing_optional_sections(self):
        thin = {"profile": "gpu", "pilots": [{"id": "P4", "status": "pass"}]}
        m = report.merge_reports([self.cpu, thin])
        self.assertEqual(len(m["pilots"]), 3)


class TestMergeCli(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_merge_")
        self.a = os.path.join(self.d, "sei_probe_report.cpu.json")
        self.b = os.path.join(self.d, "sei_probe_report.gpu.json")
        with open(self.a, "w") as fh:
            json.dump(_rep("cpu", [{"id": "P1", "status": "pass"}]), fh)
        with open(self.b, "w") as fh:
            json.dump(_rep("gpu", [{"id": "P4", "status": "pass"}]), fh)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self, argv):
        import contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
            rc = cli.main(argv)
        return rc, buf.getvalue()

    def test_merge_command_writes_a_single_file(self):
        out = os.path.join(self.d, "merged.json")
        rc, text = self._run(["merge", self.a, self.b, "-o", out])
        self.assertEqual(rc, 0)
        with open(out) as fh:
            m = json.load(fh)
        self.assertEqual(sorted(p["id"] for p in m["pilots"]), ["P1", "P4"])
        self.assertIn("파일럿 2", text)

    def test_merge_requires_two_inputs(self):
        rc, text = self._run(["merge", self.a, "-o", os.path.join(self.d, "x.json")])
        self.assertEqual(rc, 2)
        self.assertIn("2개 이상", text)

    def test_merge_reports_unreadable_input(self):
        rc, text = self._run(["merge", self.a, os.path.join(self.d, "nope.json")])
        self.assertEqual(rc, 2)
        self.assertIn("읽지 못했다", text)


class TestP4SpeedRatioReference(unittest.TestCase):
    """🔴 lead 지시 5: 속도비의 **분모가 무엇인지**가 JSON에 명시돼야 한다.

    두 머신이 분리돼 있으므로 이 비는 'GPU : 이 머신의 CPU'이지 'GPU : HPC 노드'가 아니다.
    문서에만 적고 JSON에 없으면 받는 쪽이 그대로 8배 가정과 비교해 버린다.
    """

    def setUp(self):
        from sei_pilot.criteria import p4 as p4_mod
        self.p4 = p4_mod
        self.r = p4_mod.evaluate_p4(-500.0, -500.000001, 30.0, 300.0, 64,
                                    gpu_hours=0.5, cpu_model="AMD EPYC 7543")
        self.sr = self.r["measurements"]["speed_ratio"]

    def test_reference_machine_is_declared_in_json(self):
        self.assertEqual(self.sr["cpu_reference"]["machine"], "gpu_host_cpu")
        self.assertIn("HPC", self.sr["cpu_reference"]["caveat"])

    def test_cpu_model_and_cores_are_carried_for_normalization(self):
        self.assertEqual(self.sr["cpu_reference"]["cpu_model"], "AMD EPYC 7543")
        self.assertEqual(self.sr["cpu_reference"]["cores_used"], 64)

    def test_hpc_normalization_field_exists_and_is_required(self):
        norm = self.sr["hpc_normalization"]
        self.assertTrue(norm["required"])
        self.assertIn("cluster.cpu", norm["how"])

    def test_ratio_key_is_renamed_to_say_what_the_denominator_is(self):
        self.assertIn("ratio_gpu_per_cpu_reference", self.sr)
        self.assertEqual(self.sr["ratio_gpu_per_cpu_reference"], 10.0)

    def test_missing_timing_still_declares_the_reference(self):
        sr = self.p4.speed_ratio(None, None, 64, "X")
        self.assertIsNone(sr["ratio_gpu_per_cpu_reference"])
        self.assertEqual(sr["cpu_reference"]["cpu_model"], "X")


class TestGpuDetectionSingleSource(unittest.TestCase):
    """🔴 같은 유형 5번째: 'nvidia-smi 가 PATH에 없을 수 있다'가 py와 sh 두 곳에 적혀
    있다가 한쪽만 고쳐졌다 → planner가 GPU를 못 찾아 P4를 SKIP 했고, 그것이 회신에
    '이 머신에서 GPU-DFT 불가'로 기록됐다(= 고칠 수 있는 환경 문제의 능력값 둔갑).

    이제 경로는 config/env_paths.json **한 곳**에만 있다. 그 사실을 고정한다.
    """

    def setUp(self):
        from sei_pilot import envpaths
        self.envpaths = envpaths

    def _read(self, *parts):
        with open(os.path.join(context.PKG_ROOT, *parts)) as fh:
            return fh.read()

    def test_paths_come_from_config_not_code(self):
        cfg = self.envpaths.load()
        self.assertFalse(cfg.get("_fallback"), "env_paths.json 을 읽지 못했다")
        self.assertIn("/usr/lib/wsl/lib", self.envpaths.extra_search_paths())

    def test_no_source_file_hardcodes_the_wsl_path_twice(self):
        """🔴 근본 원인 차단: 경로가 코드/셸에 리터럴로 다시 나타나면 실패."""
        offenders = []
        for rel in ("sei_pilot/sysprobe.py", "payload/P4.sh",
                    "payload/probe_gpu_node.sh", "payload/env_common.sh", "run.sh"):
            for i, line in enumerate(self._read(*rel.split("/")).splitlines(), 1):
                if "/usr/lib/wsl/lib" in line and not line.strip().startswith("#"):
                    offenders.append("%s:%d" % (rel, i))
        self.assertEqual(offenders, [],
                         "경로가 단일 출처 밖에 하드코딩돼 있다: %s" % offenders)

    def test_resolve_tool_finds_binary_outside_path(self):
        from sei_pilot.shellrun import FakeShell
        sh = FakeShell(which_map={}, paths=["/usr/lib/wsl/lib/nvidia-smi"])
        self.assertEqual(self.envpaths.resolve_tool(sh, "nvidia-smi"),
                         "/usr/lib/wsl/lib/nvidia-smi")

    def test_resolve_tool_prefers_path(self):
        from sei_pilot.shellrun import FakeShell
        sh = FakeShell(which_map={"nvidia-smi": "/usr/bin/nvidia-smi"})
        self.assertEqual(self.envpaths.resolve_tool(sh, "nvidia-smi"),
                         "/usr/bin/nvidia-smi")

    def test_resolve_tool_returns_none_when_truly_absent(self):
        from sei_pilot.shellrun import FakeShell
        self.assertIsNone(self.envpaths.resolve_tool(FakeShell(), "nvidia-smi"))

    def test_sysprobe_detects_gpu_when_smi_is_off_path(self):
        """🔴 lead가 관측한 상황 그대로: PATH에 없고 /usr/lib/wsl/lib 에만 있다."""
        from sei_pilot import sysprobe
        from sei_pilot.shellrun import FakeShell
        sh = FakeShell(
            responses={"/usr/lib/wsl/lib/nvidia-smi --query-gpu":
                       (0, "NVIDIA GeForce RTX 4070 SUPER, 12282 MiB\n", ""),
                       "hostname -f": (0, "gpubox\n", "")},
            which_map={}, paths=["/usr/lib/wsl/lib/nvidia-smi"])
        info = sysprobe.collect_login(sh)
        self.assertTrue(info["login_gpus"]["present"])
        self.assertIn("4070", info["login_gpus"]["model"])
        self.assertEqual(info["login_gpus"]["nvidia_smi_path"],
                         "/usr/lib/wsl/lib/nvidia-smi")

    def test_planner_runs_p4_when_smi_is_off_path(self):
        """탐지가 고쳐지면 **P4가 SKIP이 아니라 RUN** 이어야 한다(최종 관심사)."""
        from sei_pilot import cli as cli_mod
        from sei_pilot.shellrun import FakeShell
        sh = FakeShell(
            responses={"/usr/lib/wsl/lib/nvidia-smi --query-gpu":
                       (0, "NVIDIA GeForce RTX 4070 SUPER, 12282 MiB\n", ""),
                       "hostname -f": (0, "gpubox\n", "")},
            which_map={"python3": "/usr/bin/python3"},
            paths=["/usr/lib/wsl/lib/nvidia-smi"])
        env = cli_mod.build_env(sh, context.PKG_ROOT)
        planned, _s = plan.build_plan(env, budget.guard_for_profile("gpu"),
                                      profile="gpu")
        items = {p["key"]: p for p in planned}
        self.assertEqual(items["P4"]["status"], "planned",
                         items["P4"].get("skip_reason"))

    def test_planner_still_skips_p4_when_there_is_really_no_gpu(self):
        """양성 대조군: 진짜 GPU가 없으면 여전히 SKIP 이어야 한다."""
        from sei_pilot import cli as cli_mod
        from sei_pilot.shellrun import FakeShell
        sh = FakeShell(responses={"hostname -f": (0, "cpuonly\n", "")},
                       which_map={"python3": "/usr/bin/python3"})
        env = cli_mod.build_env(sh, context.PKG_ROOT)
        planned, _s = plan.build_plan(env, budget.guard_for_profile("gpu"),
                                      profile="gpu")
        items = {p["key"]: p for p in planned}
        self.assertEqual(items["P4"]["status"], "skipped")

    def test_shell_helper_reads_the_same_single_source(self):
        text = self._read("payload", "env_common.sh")
        self.assertIn("envpaths", text)
        self.assertNotIn("/usr/local/nvidia/bin", text.replace("#", ""))


class TestGuardDescriptionConsistency(unittest.TestCase):
    """🔴 회신 JSON 안에서 guard 블록이 자기모순을 일으키면 안 된다.

    사용자가 "가드가 잘못 설정된 건가?" 라고 물어오는 순간 왕복 1회 = 3.5일이다.
    이 패키지의 설계 원칙은 '사용자는 판단하지 않는다' 이므로 서술이 정확해야 한다.
    """

    def _report(self, profile):
        env = {"scheduler": "none", "cores_per_node": 32, "software": {}, "gpus": {}}
        g = budget.guard_for_profile(profile)
        planned, summary = plan.build_plan(env, g, profile=profile)
        return report.build_report(
            login={"hostname": "h", "scheduler": "none"}, node_probe=None,
            plan=planned, plan_summary=summary, guard=g, pilots=[],
            throughput={}, queue_wait=[], failures=[], profile=profile)

    def test_report_guard_block_is_self_consistent(self):
        for prof in ("cpu", "gpu"):
            blk = self._report(prof)["guard"]
            self.assertIn("%.0f core-h" % blk["max_core_hours"], blk["guard_source"])
            self.assertIn(prof, blk["guard_source"])

    def test_report_guard_matches_the_profile_of_the_report(self):
        for prof in ("cpu", "gpu"):
            rep = self._report(prof)
            self.assertEqual(rep["profile"], prof)
            self.assertEqual(rep["guard"]["profile"], prof)


class TestP4SmokeLabeling(unittest.TestCase):
    """🔴 ADR-030 A10: 개발 박스 결과는 측정이 아니라 스모크다.

    속도는 A10으로 거칠게 환산할 수 있으나 **메모리 상한은 환산 불가**다
    (12.9 GB vs 80 GB는 속도가 아니라 용량). 그래서 대상 기종이 아니면 비워 둔다.
    """

    def setUp(self):
        from sei_pilot.criteria import p4 as p4_mod
        self.p4 = p4_mod

    def _res(self, gpu_model, mem="12282 MiB"):
        return self.p4.evaluate_p4(-349.9075223, -349.9075224, 62.0, 187.0, 16,
                                   max_atoms_ok=66, oom_at_atoms=None,
                                   gpu_model=gpu_model, gpu_memory_total=mem,
                                   cpu_model="AMD Ryzen 7 7800X3D")

    def test_dev_box_gpu_is_labelled_smoke(self):
        r = self._res("NVIDIA GeForce RTX 4070 SUPER")
        self.assertEqual(r["measurement_class"], "smoke")
        self.assertIn("not H100", r["measurement_label"])

    def test_target_gpu_is_labelled_measured(self):
        r = self._res("NVIDIA H100 80GB HBM3", "81559 MiB")
        self.assertEqual(r["measurement_class"], "target")
        self.assertIn("MEASURED", r["measurement_label"])

    def test_memory_ceiling_is_blanked_on_non_target_gpu(self):
        """🔴 lead 지시: 실제 GPU 머신 전까지 이 필드는 비워 둬라."""
        r = self._res("NVIDIA GeForce RTX 4070 SUPER")["measurements"]
        self.assertIsNone(r["max_atoms_completed"])
        self.assertIsNone(r["oom_at_atoms"])
        self.assertEqual(r["max_atoms_on_this_gpu"], 66)      # 원값은 버리지 않는다
        self.assertFalse(r["memory_ceiling_transferable"])
        self.assertIn("환산하지 마라", r["memory_ceiling_note"])

    def test_memory_ceiling_is_kept_on_target_gpu(self):
        r = self._res("NVIDIA H100 80GB HBM3", "81559 MiB")["measurements"]
        self.assertEqual(r["max_atoms_completed"], 66)
        self.assertTrue(r["memory_ceiling_transferable"])

    def test_unknown_gpu_is_not_guessed(self):
        r = self._res(None)
        self.assertEqual(r["measurement_class"], "unknown")
        self.assertIn("UNVERIFIED", r["measurement_label"])
        self.assertIsNone(r["measurements"]["max_atoms_completed"])

    def test_real_smoke_run_reproduces_the_expected_verdict(self):
        """실제 RTX 4070 SUPER 실행값(lead 확인)으로 판정이 pass 인지."""
        r = self._res("NVIDIA GeForce RTX 4070 SUPER")
        self.assertEqual(r["status"], "pass")
        self.assertLess(abs(r["criteria"]["energy_delta_hartree"]), 1e-5)


class TestGpuInstallHelp(unittest.TestCase):
    """설치 실패를 사용자가 왕복 없이 고칠 수 있어야 한다(lead 실측 기반)."""

    def _read(self, *parts):
        with open(os.path.join(context.PKG_ROOT, *parts)) as fh:
            return fh.read()

    def test_p4_prints_pip_command_on_import_failure(self):
        text = self._read("payload", "P4.sh")
        self.assertIn("gpu_fix_hint", text)
        self.assertIn("nvidia-nvjitlink-cu12", text)
        self.assertIn("nvidia-cusolver-cu12", text)

    def test_runsh_does_not_manipulate_ld_library_path(self):
        """🔴 lead 반증 + 내 재확인: `env -u LD_LIBRARY_PATH` 로도 import 된다.
        경로 문제가 아니라 패키지 부재였다. 불필요한 환경 변수 조작은 넣지 않는다."""
        text = self._read("run.sh")
        self.assertNotIn("export LD_LIBRARY_PATH", text)
        for line in text.splitlines():
            if "LD_LIBRARY_PATH" in line:
                self.assertTrue(line.strip().startswith("#"),
                                "주석이 아닌 곳에서 LD_LIBRARY_PATH 를 건드린다: %s" % line)

    def test_runsh_widens_path_via_the_single_source(self):
        """nvidia-smi 탐색 경로 확장은 유지하되, 경로 자체는 config 에서만 온다.

        (이전 판의 이 테스트는 run.sh 에 '/usr/lib/wsl/lib' 리터럴이 있기를 요구했다 —
         즉 **내가 방금 제거한 중복을 테스트가 요구하고 있었다.** 테스트도 같은 실패
         유형에 걸릴 수 있다는 예이므로 기록해 둔다.)
        """
        text = self._read("run.sh")
        self.assertIn('SEI_PROFILE}" = "gpu"', text)
        self.assertIn("envpaths", text)
        for line in text.splitlines():
            if "/usr/lib/wsl/lib" in line:
                self.assertTrue(line.strip().startswith("#"), line)

    def test_import_failure_is_classified_not_recorded_as_incapability(self):
        """🔴 lead: 고칠 수 있는 환경 문제가 '능력 없음'으로 둔갑하면 false negative다."""
        text = self._read("payload", "P4.sh")
        self.assertIn("gpu_failure_class", text)
        self.assertIn("likely_fixable_environment", text)
        self.assertIn("cannot open shared object file", text)

    def test_gpu_readme_has_install_recipe_and_smoke_caveat(self):
        text = self._read("README_USER.gpu.md")
        self.assertIn("gpu4pyscf-cuda12x", text)
        self.assertIn("nvidia-nvjitlink-cu12", text)
        self.assertIn("SMOKE", text)
        self.assertIn("그래도 안 되면 그대로 두셔도", text)      # 강요하지 않는다
        self.assertIn("필요 없습니다", text)                    # LD_LIBRARY_PATH 불필요


class TestP5Criteria(unittest.TestCase):
    def _rows(self, cheap_core_h=60.0):
        rows = []
        for n, chg, mult in ((3, 0, 1), (5, -1, 1), (5, 0, 2), (10, 0, 1),
                             (15, -1, 2), (21, 1, 1)):
            rows.append({"id": "s%d_%d_%d" % (n, chg, mult),
                         "level": p5_mod.LEVEL_PRIMARY, "n_atoms": n,
                         "charge": chg, "multiplicity": mult,
                         "core_hours": 0.5 * n * (2 if mult > 1 else 1),
                         "wall_h": 0.3, "scf_cycles_max": 14, "converged": True,
                         "rc": 0})
        for n in (3, 10, 21):
            rows.append({"id": "s%d_0_1" % n, "level": p5_mod.LEVEL_CHEAP,
                         "n_atoms": n, "charge": 0, "multiplicity": 1,
                         "core_hours": cheap_core_h, "wall_h": 0.2,
                         "scf_cycles_max": 10, "converged": True, "rc": 0})
        return rows

    def test_raw_rows_are_returned_not_averaged(self):
        """🔴 lead 지시: 평균을 내지 마라. 곡선 적합은 받는 쪽이 한다."""
        r = p5_mod.evaluate_p5(self._rows(), n_requested=14)
        self.assertEqual(len(r["species_rows"]), 9)
        for row in r["species_rows"]:
            for k in ("n_atoms", "charge", "multiplicity", "core_hours", "wall_h",
                      "scf_cycles_max", "converged"):
                self.assertIn(k, row)

    def test_verdict_thresholds_and_level_label(self):
        keep = p5_mod.evaluate_p5(self._rows(cheap_core_h=60.0))["budget_verdict"]
        self.assertEqual(keep["verdict"], "keep_pool")
        self.assertEqual(keep["threshold_basis"], p5_mod.LEVEL_CHEAP)
        shrink = p5_mod.evaluate_p5(self._rows(cheap_core_h=120.0))["budget_verdict"]
        self.assertEqual(shrink["verdict"], "shrink_pool")
        tier = p5_mod.evaluate_p5(self._rows(cheap_core_h=200.0))["budget_verdict"]
        self.assertEqual(tier["verdict"], "restore_tiering")

    def test_threshold_basis_is_cheap_level_not_primary(self):
        """🔴 임계는 값싼 레벨 기준이다. 고수준 값에 적용하면 판정이 뒤집힌다."""
        r = p5_mod.evaluate_p5(self._rows(cheap_core_h=60.0))["budget_verdict"]
        self.assertIn("def2-TZVP", r["threshold_basis"])
        self.assertNotIn("TZVPPD", r["threshold_basis"])
        self.assertIn("caveat", r)

    def test_open_shell_cost_ratio_is_reported(self):
        d = p5_mod.evaluate_p5(self._rows())["diagnostics"]
        prim = d["by_level"][p5_mod.LEVEL_PRIMARY]
        self.assertIsNotNone(prim["open_shell_cost_ratio"])
        self.assertGreater(prim["open_shell_cost_ratio"], 1.0)

    def test_small_molecule_level_ratio_is_separate_from_p1b(self):
        r = p5_mod.evaluate_p5(self._rows(cheap_core_h=10.0))
        ratio = r["level_cost_ratio_small_molecules"]
        self.assertTrue(ratio["per_species"])
        self.assertIn("P1b", ratio["note"])

    def test_failed_species_are_kept_not_dropped(self):
        rows = self._rows()
        rows.append({"id": "boom", "level": p5_mod.LEVEL_PRIMARY, "n_atoms": 12,
                     "charge": 0, "multiplicity": 1, "core_hours": 3.0,
                     "converged": False, "rc": 1})
        r = p5_mod.evaluate_p5(rows, n_requested=14)
        self.assertEqual(r["criteria"]["species_failed"], 1)
        self.assertTrue(any(not x["converged"] for x in r["species_rows"]))

    def test_too_few_converged_is_a_failure(self):
        rows = [dict(r, converged=False) for r in self._rows()]
        r = p5_mod.evaluate_p5(rows, n_requested=14)
        self.assertEqual(r["status"], "fail")
        self.assertTrue(r["fail_reasons"])

    def test_no_rows_is_skipped_not_pass(self):
        r = p5_mod.evaluate_p5([], n_requested=14)
        self.assertEqual(r["status"], "skipped")


if __name__ == "__main__":
    unittest.main()
