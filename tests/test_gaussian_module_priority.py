"""🔴 Gaussian 탐지: **모듈이 바이너리보다 먼저** (실클러스터에서 대가를 치른 순서).

실제로 난 일 (사용자 회신 `cpu_machine_pilot_results/`):
```
plan.json        : tools.g16 = {'how': 'binary', 'detail': '/apps/commercial/G16/g16/g16'}
계산 노드 인벤토리: software.g16 = ''          ← 없다
계산 노드 모듈    : gaussian/g16.a03, .a03.lin, .b01.lin, .c01.lin   ← 있다
결과             : P1 / P1b / P5 전부 rc=3 ("QC 코드 없음")
```
로그인 PATH 에 바이너리가 보여 `binary` 로 잡혔고 ⟹ 잡 스크립트에 `module load` 줄이
**안 들어갔다.** 계산 노드에는 그 경로가 없었다.

**모듈은 계산 노드에서 동작하도록 사이트가 만들어 둔 것**이고, 로그인 PATH 의 경로는
로그인 노드에서만 유효할 수 있다. 그래서 우선순위를 뒤집었다.
"""

# 🔴 HISTORICAL NOTE — describes a PAST defect, already fixed. Not current behaviour.
#    (The module docstring above also describes the *earlier* login-vs-compute incident.)
#    Corrected after the RT-1 cluster failure (2026-08-18):
#    these fixtures USED TO carry `gaussian/g16.c01.lin` etc. — the names our own
#    `rstrip("(default)")` bug produced. `module avail` on the cluster actually lists
#    `gaussian/g16.c01.linda` (and .a03.linda, .b01.linda, plus a plain .a03).
#    🔴 So the tests were green while encoding a module name that does not exist:
#    the fixture had frozen the bug's output as the expected truth.
#    Ground truth now comes from the cluster reply (cluster.modules_raw); see
#    tests/test_module_name_truncation.py, whose fixture is verbatim from that reply.

import json
import os
import shutil
import unittest

import context  # noqa: F401
from sei_pilot import envpaths, plan

# 실클러스터에서 실제로 보인 모듈 목록
REAL_MODULES = ["gcc/11.2", "intel/19.1.2",
                "gaussian/g16.a03", "gaussian/g16.a03.linda",
                "gaussian/g16.b01.linda", "gaussian/g16.c01.linda"]
REAL_BINARY = "/apps/commercial/G16/g16/g16"


class TestModuleBeatsBinary(unittest.TestCase):
    def _env(self, **over):
        env = {"vendored": {}, "containers": {},
               "software": {"g16": {"path": REAL_BINARY}},
               "qc_module": {"module": "gaussian/g16.c01.linda", "binary": "g16",
                             "path": REAL_BINARY},
               "modules": REAL_MODULES}
        env.update(over)
        return env

    def test_module_is_chosen_over_binary(self):
        how, detail = plan.resolve_tool(self._env(), plan.QC_CODES)
        self.assertEqual("module(verified)", how,
                         "바이너리를 먼저 골랐다 — 계산 노드에서 또 죽는다")
        self.assertIn("gaussian/g16", detail)

    def test_binary_is_still_used_when_no_module(self):
        """모듈이 없으면 바이너리라도 쓴다 — 폴백을 없앤 것이 아니다."""
        how, detail = plan.resolve_tool(self._env(qc_module=None), plan.QC_CODES)
        self.assertEqual("binary", how)
        self.assertEqual(REAL_BINARY, detail)

    def test_vendored_still_wins_for_xtb(self):
        """xtb 는 동봉본이 최우선이어야 한다(재현성). 순서를 뒤집다 깨면 안 된다."""
        env = self._env(vendored={"xtb": "/pkg/vendor/xtb/bin/xtb"})
        self.assertEqual("vendored", plan.resolve_tool(env, ["xtb"])[0])

    def test_nothing_available_reports_module_attempts(self):
        env = self._env(software={}, qc_module={"tried": [
            {"module": "gaussian/g16.c01.linda", "binary": "g16", "found": False}]})
        ok, reason, _tools = plan.check_requirements(
            type("I", (), {"requires": [("any", plan.QC_CODES)]})(), env)
        self.assertFalse(ok)
        self.assertIn("module", reason[0])


class TestNewestModuleFirst(unittest.TestCase):
    """4개 중 **가장 오래된 a03** 을 고르던 정렬을 고쳤다."""

    def test_newest_looking_module_comes_first(self):
        cands = envpaths.module_candidates(REAL_MODULES)
        self.assertEqual("gaussian/g16.c01.linda", cands[0],
                         "가장 최신으로 보이는 것을 먼저 시도해야 한다: %s" % cands)

    def test_all_gaussian_modules_are_candidates(self):
        cands = envpaths.module_candidates(REAL_MODULES)
        self.assertEqual(4, len(cands), cands)
        self.assertNotIn("gcc/11.2", cands)

    def test_user_preference_goes_first(self):
        """`--gaussian-module` 이 목록에 없어도 시도한다 (우리가 못 본 모듈일 수 있다)."""
        class _Shell(object):
            def __init__(self):
                self.calls = []

            def run(self, cmd, timeout_s=None):
                self.calls.append(cmd)
                class R(object):
                    ok = False
                    out = ""
                    err = ""
                    rc = 1
                return R()

        sh = _Shell()
        envpaths.resolve_qc_via_module(sh, REAL_MODULES,
                                       preferred="gaussian/g16.b01.linda")
        self.assertIn("gaussian/g16.b01.linda", sh.calls[0])


class TestJobsReceiveTheModule(unittest.TestCase):
    """🔴 찾은 모듈이 **잡 환경까지** 내려가는가. 안 가면 계산 노드에서 또 죽는다."""

    def test_module_and_login_path_are_exported(self):
        from sei_pilot import cli
        env = {"qc_module": {"module": "gaussian/g16.c01.linda", "path": REAL_BINARY},
               "software": {"g16": {"path": REAL_BINARY}}}
        got = cli.qc_env_for_jobs(env)
        self.assertEqual("gaussian/g16.c01.linda", got["SEI_QC_MODULE"])
        self.assertEqual(REAL_BINARY, got["SEI_QC_LOGIN_PATH"])

    def test_no_module_means_no_export(self):
        from sei_pilot import cli
        self.assertNotIn("SEI_QC_MODULE",
                         cli.qc_env_for_jobs({"qc_module": {}, "software": {}}))

    def test_module_detection_is_attempted_even_when_binary_found(self):
        """🔴 이것이 이번 사고의 직접 원인이었다 — 바이너리를 찾으면 건너뛰었다."""
        import inspect
        from sei_pilot import cli
        src = inspect.getsource(cli.build_env)
        self.assertNotIn('if not (login.get("software") or {}).get("g16"):', src,
                         "바이너리를 찾으면 module 탐지를 건너뛴다")
        self.assertIn("resolve_qc_via_module", src)


class TestFailureModesAreDistinguished(unittest.TestCase):
    """🔴 예전에는 전부 rc=3 으로 뭉개져 원인을 알 수 없었다."""

    def test_adapter_distinguishes_the_four_cases(self):
        with open(os.path.join(context.PKG_ROOT, "payload",
                               "qc_adapter.sh")) as fh:
            text = fh.read()
        for case in ("module_load_failed", "module_command_missing",
                     "loaded_but_binary_absent", "loaded_but_not_runnable",
                     "absent"):
            self.assertIn(case, text, "실패 사유 %s 를 구분하지 않는다" % case)

    def test_adapter_records_whether_login_path_exists_on_compute_node(self):
        """`/apps/.../g16` 이 계산 노드에 있는지 **우리는 모른다** → 잡이 확인한다."""
        with open(os.path.join(context.PKG_ROOT, "payload",
                               "qc_adapter.sh")) as fh:
            text = fh.read()
        self.assertIn("login_binary_exists_on_compute_node", text)

    def test_payloads_print_the_reason(self):
        for name in ("P1.sh", "P1b.sh", "P5.sh"):
            with open(os.path.join(context.PKG_ROOT, "payload", name)) as fh:
                text = fh.read()
            self.assertIn("SEI_QC_DETAIL", text, "%s 가 사유를 안 찍는다" % name)


class TestProbeNodeChecksAfterModuleLoad(unittest.TestCase):
    """🔴 인벤토리가 **로드 전** 상태만 봐서 계산 노드에서 '없음'으로 보였다."""

    def test_probe_tests_module_load(self):
        with open(os.path.join(context.PKG_ROOT, "payload",
                               "probe_node.sh")) as fh:
            text = fh.read()
        self.assertIn("g16_before_module", text)
        self.assertIn("module_ok", text)
        self.assertIn("SEI_QC_LOGIN_PATH", text)

    def test_summary_carries_the_gaussian_block(self):
        with open(os.path.join(context.PKG_ROOT, "tools",
                               "node_probe_summary.py")) as fh:
            text = fh.read()
        self.assertIn("gaussian_probe.txt", text)
        self.assertIn('"gaussian"', text)


class TestAgainstTheRealClusterReport(unittest.TestCase):
    """실제 회신 데이터로 **고친 코드가 이번엔 다른 판단을 하는지** 확인한다."""

    REPORT = os.path.join(context.REPO_ROOT, "cpu_machine_pilot_results",
                          "sei_probe_report.cpu.json")

    def setUp(self):
        if not os.path.exists(self.REPORT):
            self.skipTest("실클러스터 회신 파일 없음")
        with open(self.REPORT) as fh:
            self.report = json.load(fh)

    def test_report_confirms_modules_existed_on_the_compute_node(self):
        mods = [m for m in (self.report["cluster"]["modules"] or [])
                if "gauss" in m.lower()]
        self.assertEqual(4, len(mods), mods)

    def test_with_those_modules_we_now_choose_module_not_binary(self):
        env = {"vendored": {}, "containers": {},
               "software": {"g16": {"path": REAL_BINARY}},
               "qc_module": {"module": "gaussian/g16.c01.linda", "binary": "g16",
                             "path": REAL_BINARY},
               "modules": self.report["cluster"]["modules"]}
        self.assertEqual("module(verified)",
                         plan.resolve_tool(env, plan.QC_CODES)[0])


if __name__ == "__main__":
    unittest.main()


class TestRerunRetriesFailedButSkipsDone(unittest.TestCase):
    """🔴 **2,130 core-h 가 걸린 재실행 의미** — 실패는 다시, 완료는 건너뜀.

    실클러스터 회신 상태:
    ```
    done   : probe_node, probe_throughput, probe_queuewait, P3   (500 core-h 포함)
    failed : P1, P1b, P5  (rc=3)   ← 이것만 다시 돌아야 한다
    ```
    🔴 예전 논리는 `is_submitted` 만 봐서 **실패한 항목도 "이미 제출됨"으로 건너뛰었다.**
    사용자가 `./run.sh` 를 다시 쳐도 **아무 일도 일어나지 않았을 것이다.**
    (`--force` 를 써야 했는데, 그건 사용자가 알 수 없고 다른 부작용도 있다.)
    """

    def _store(self):
        import tempfile
        from sei_pilot.state import Store
        st = Store(tempfile.mkdtemp(prefix="sei_rerun_"))
        self.addCleanup(shutil.rmtree, st.workdir, True)
        st.mark_done("P3", {"rc": 0})
        for k in ("P1", "P1b", "P5"):
            st.mark_submitted(k, {"job_id": "1"})
            st.mark_failed(k, "payload_nonzero_exit", "rc=3")
        st.mark_submitted("running_item", {"job_id": "2"})
        return st

    def test_report_state_is_what_we_think(self):
        st = self._store()
        self.assertTrue(st.is_done("P3"))
        self.assertTrue(st.is_failed("P1"))
        self.assertTrue(st.is_submitted("P1"))

    def test_cli_logic_retries_failed_and_skips_done(self):
        """cli.cmd_submit 의 분기 순서를 소스에서 확인한다."""
        import inspect
        from sei_pilot import cli
        src = inspect.getsource(cli.cmd_submit)
        i_done = src.index("store.is_done(key)")
        i_failed = src.index("store.is_failed(key)")
        i_sub = src.index("store.is_submitted(key)")
        self.assertLess(i_done, i_failed, "완료 검사가 먼저여야 한다")
        self.assertLess(i_failed, i_sub,
                        "🔴 실패 검사가 제출 검사보다 **먼저**여야 한다 — "
                        "아니면 실패한 항목이 '이미 제출됨'으로 건너뛰어진다")

    def test_failed_marker_is_cleared_on_retry(self):
        """🔴 안 지우면 잡이 도는 중에 재실행 시 **이중 제출**된다."""
        import inspect
        from sei_pilot import cli
        self.assertIn("clear_failed", inspect.getsource(cli.cmd_submit))
        st = self._store()
        self.assertTrue(st.clear_failed("P1"))
        self.assertFalse(st.is_failed("P1"))
        self.assertTrue(st.is_submitted("P1"), "제출 마커까지 지우면 안 된다")

    def test_done_item_is_never_retried_even_with_force(self):
        """P3(500 core-h)를 헛되이 다시 태우지 않는다."""
        import inspect
        from sei_pilot import cli
        src = inspect.getsource(cli.cmd_submit)
        done_block = src[src.index("store.is_done(key)"):
                         src.index("store.is_failed(key)")]
        self.assertNotIn("args.force", done_block,
                         "완료 항목이 --force 로 재제출된다")

    def test_queue_wait_subjobs_follow_the_same_rule(self):
        import inspect
        from sei_pilot import cli
        src = inspect.getsource(cli.submit_entry)
        self.assertIn("store.is_failed(sub_key)", src)
        self.assertIn("clear_failed(sub_key)", src)


class TestConfiguredGaussianModule(unittest.TestCase):
    """The module name comes from ONE place (`config/env_paths.json`), not from code or payload.

    🔴 This docstring previously read *"the user-confirmed value `gaussian/g16.c01.lin`"*.
    Both halves were wrong and the second is the more dangerous one:
      1. the name was the truncated one our own `rstrip("(default)")` bug produced;
      2. **it claimed external confirmation for a value that originated with us.**
    We showed the user a name we had generated and recorded their agreement as independent
    confirmation. 🔒 A confirmation is independent only if the value did not originate here.

    ⚠ What this class actually checks is the *single source of truth* property — that the name
    is read from config and is tried first. It does **not** establish that the name is correct;
    only loading the module and finding the binary does that (see `payload/qc_adapter.sh`).
    """

    def test_default_is_the_confirmed_module(self):
        default, fallbacks = envpaths.configured_gaussian_modules()
        self.assertEqual("gaussian/g16.c01.linda", default)
        self.assertEqual(3, len(fallbacks))

    def test_default_comes_first_in_candidates(self):
        self.assertEqual("gaussian/g16.c01.linda",
                         envpaths.module_candidates(REAL_MODULES)[0])

    def test_default_is_tried_even_if_not_in_module_avail(self):
        """`module avail` 파싱이 실패해도 확정값은 시도한다."""
        self.assertIn("gaussian/g16.c01.linda", envpaths.module_candidates([]))

    def test_module_name_is_not_hardcoded_in_code(self):
        """🔴 이름은 config 에만 있어야 한다."""
        for rel in ("sei_pilot/envpaths.py", "sei_pilot/cli.py",
                    "payload/qc_adapter.sh"):
            with open(os.path.join(context.PKG_ROOT, rel)) as fh:
                code = [l for l in fh
                        if not l.lstrip().startswith(("#", "//"))]
            self.assertNotIn("g16.c01", "".join(code),
                             "%s 에 모듈 이름이 박혀 있다" % rel)
