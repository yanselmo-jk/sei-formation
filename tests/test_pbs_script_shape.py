"""🔴 PBS 제출 스크립트의 **형태**를 사용자 정본과 맞춘다.

실제 클러스터에서 **4건 전부** 거부됐다:
```
qsub: request rejected as filter hook 'job_submit_filter' encountere...
```
그리고 우리는 **거부 메시지도 스크립트도 못 보고 있었다** — 화면 출력이 첫 줄 66자에서
잘렸기 때문이다.

사용자가 그 클러스터에서 **실제로 돌려온 스크립트**를 줬다. 그것이 정본이다:
```sh
#!/bin/sh
#PBS -V
#PBS -q normal
#PBS -N test_0
#PBS -A vasp
#PBS -l select=12:ncpus=32:mpiprocs=32
#PBS -l walltime=48:00:00
cd $PBS_O_WORKDIR
module purge
module load intel/19.1.2 impi/19.1.2
```
⚠ **우리 박스에는 PBS 도 Gaussian 도 없다.** 여기서 검증 가능한 것은 **생성되는 텍스트의
형태**뿐이고, 실제 수용 여부는 `[UNVERIFIED — 사용자 클러스터에서만 확인 가능]` 이다.
그래서 이 파일은 "훅이 통과한다"가 아니라 **"정본과 같은 형태인가"** 만 고정한다.
"""

import inspect
import atexit
import os
import sys
import shutil
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import scheduler as sch
from sei_pilot.shellrun import FakeShell

TEMPLATES = os.path.join(context.PKG_ROOT, "sei_pilot", "templates")


# 🔴 `_script` is a module-level helper, so it cannot use `self.addCleanup`. It ran once per
#    call and left a directory behind every time — 12 per suite run. Together with the other
#    leaks this filled /tmp and **killed two builds outright** (§41.4, §44).
#    ⟹ one temp root for the whole module, removed at interpreter exit.
_PBS_TMPROOT = tempfile.mkdtemp(prefix="sei_pbs_root_")
atexit.register(shutil.rmtree, _PBS_TMPROOT, True)


def _script(**kw):
    d = tempfile.mkdtemp(dir=_PBS_TMPROOT)
    adapter = sch.PbsAdapter(FakeShell(), TEMPLATES)
    spec = sch.JobSpec(
        kw.pop("key", "probe_node"), kw.pop("command", "bash payload/probe_node.sh"),
        nodes=kw.pop("nodes", 1), cores_per_node=kw.pop("cores_per_node", 64),
        wall_h=kw.pop("wall_h", 0.23), partition=kw.pop("partition", "normal"),
        account=kw.pop("account", "etc"), job_dir=d,
        env=kw.pop("env", {"SEI_PKG_ROOT": "/pkg"}), **kw)
    with open(adapter.write_script(spec)) as fh:
        return fh.read()


def _directives(text):
    return [l for l in text.splitlines() if l.startswith("#PBS")]


class TestMatchesUserCanonicalForm(unittest.TestCase):
    def test_shebang_is_sh_like_the_canonical(self):
        self.assertTrue(_script().startswith("#!/bin/sh"))

    def test_has_dash_V(self):
        """정본에 있고 우리에게 없던 지시어. 환경 전달을 막으면 훅이 거부할 수 있다."""
        self.assertIn("#PBS -V", _directives(_script()))

    def test_directive_order_matches_canonical(self):
        """정본 순서 전체를 못박는다: -V, -q, -N, -A, -l select, -l walltime.

        🔴 예전에는 `-N` 이 `-q` 보다 앞이었고, 이 테스트가 그 상대순서를 검사하지
        않아 **인용한 정본과 실제 템플릿이 달랐다**(critic2). 테스트가 인용문과
        어긋나면 그 인용문은 문서가 아니라 장식이다.
        PBS 가 지시어 순서에 무관한 것이 일반적이라 이것이 4/4 거부의 원인일
        가능성은 낮다 — 그래도 "정본과 같다"는 주장은 사실이어야 한다.
        """
        d = _directives(_script())
        order = ["#PBS -V", "#PBS -q", "#PBS -N", "#PBS -A",
                 "#PBS -l select", "#PBS -l walltime"]
        got = [next(i for i, l in enumerate(d) if l.startswith(p)) for p in order]
        self.assertEqual(sorted(got), got,
                         "지시어 순서가 정본과 다르다: %s" % d)

    def test_select_line_shape(self):
        self.assertIn("#PBS -l select=1:ncpus=64:mpiprocs=64", _directives(_script()))

    def test_no_stdio_directives_by_default(self):
        """🔴 `-o`/`-e` 절대경로가 공유 FS 밖이면 훅이 거부한다. 정본에는 없다."""
        d = _directives(_script())
        self.assertEqual([], [l for l in d if l.startswith(("#PBS -o", "#PBS -e"))])

    def test_no_blank_lines_inside_the_directive_block(self):
        """🔴 PBS 는 첫 비지시어 줄에서 지시어 파싱을 멈춘다.

        선택적 지시어를 빈 문자열로 치환하면 빈 줄이 생기고, 그 뒤의 `#PBS` 가
        통째로 무시될 수 있다.
        """
        lines = _script().splitlines()
        last = max(i for i, l in enumerate(lines) if l.startswith("#PBS"))
        self.assertEqual([], [l for l in lines[:last] if not l.strip()],
                         "지시어 블록 안에 빈 줄이 있다")

    def test_changes_directory_to_pbs_o_workdir(self):
        """PBS 는 $HOME 에서 시작한다(SLURM 과 다르다)."""
        self.assertIn('cd "${PBS_O_WORKDIR:-.}"', _script())


class TestOptionalPieces(unittest.TestCase):
    def test_stdio_lines_can_be_enabled_and_are_relative(self):
        text = _script(emit_stdio_lines=True)
        outs = [l for l in _directives(text) if l.startswith("#PBS -o")]
        self.assertEqual(1, len(outs))
        self.assertNotIn("/", outs[0].split("-o", 1)[1],
                         "절대경로를 내면 훅이 거부할 수 있다")

    def test_modules_are_loaded_on_the_compute_node(self):
        """🔴 로그인 노드에서 찾고 계산 노드에서 안 부르면 조용히 실패한다."""
        text = _script(modules=["Gaussian/16.C01"])
        self.assertIn("module load Gaussian/16.C01", text)

    def test_module_failure_does_not_kill_the_job(self):
        text = _script(modules=["Gaussian/16.C01"])
        line = [l for l in text.splitlines() if "module load" in l][0]
        self.assertIn("||", line, "module load 실패가 잡 전체를 죽인다")

    def test_no_module_lines_when_none_detected(self):
        self.assertNotIn("module load", _script())

    def test_queue_and_account_appear(self):
        d = _directives(_script(partition="normal", account="gaussian"))
        self.assertIn("#PBS -q normal", d)
        self.assertIn("#PBS -A gaussian", d)


class TestRejectionMessageIsNotTruncated(unittest.TestCase):
    """🔴 원인은 잘려나간 뒷부분에 있었다."""

    def test_full_message_is_wrapped_not_cut(self):
        from sei_pilot import cli
        long_msg = ("qsub: request rejected as filter hook 'job_submit_filter' "
                    "encountered an error: ncpus=64 exceeds the site limit of 32 "
                    "for queue normal; please use select=N:ncpus=32")
        feas = {"checked": True, "n_ok": 0, "n_rejected": 1, "n_unknown": 0,
                "precheck_method": "qsub -h + qdel",
                "precheck_has_side_effects": True,
                "results": [{"key": "probe_node", "ok": False,
                             "message": long_msg, "remedy": None}]}
        # 화면은 66자로 **접히므로**, 접힘을 되돌린 뒤 정보 손실이 없는지 본다.
        # (자르는 것과 접는 것의 차이가 이 수정의 핵심이다.)
        lines = cli.format_feasibility(feas)
        unwrapped = "".join(l[5:] for l in lines if l.startswith(" !   "))
        for token in ("ncpus=64", "site limit of 32", "queue normal",
                      "select=N:ncpus=32"):
            self.assertIn(token, unwrapped, "거부 메시지가 잘렸다: %s" % token)

    def test_multiline_message_survives(self):
        from sei_pilot import cli
        feas = {"checked": True, "n_ok": 0, "n_rejected": 1, "n_unknown": 0,
                "precheck_method": "x", "precheck_has_side_effects": True,
                "results": [{"key": "P1", "ok": False,
                             "message": "line one\nline two ORIGIN\nline three",
                             "remedy": None}]}
        text = "\n".join(cli.format_feasibility(feas))
        self.assertIn("ORIGIN", text)
        self.assertIn("line three", text)

    def test_user_is_told_how_to_show_us_the_script(self):
        from sei_pilot import cli
        feas = {"checked": True, "n_ok": 0, "n_rejected": 1, "n_unknown": 0,
                "precheck_method": "x", "precheck_has_side_effects": True,
                "results": [{"key": "P1", "ok": False, "message": "nope",
                             "remedy": None}]}
        self.assertIn("--emit-script", "\n".join(cli.format_feasibility(feas)))


if __name__ == "__main__":
    unittest.main()


class TestRealPathDoesNotTruncate(unittest.TestCase):
    """🔴 critic2: 화면 출력은 고쳤는데 **실제 파이프라인이 지나는 지점**은 안 고쳤다.

    실제 순서는
        submission_feasibility() → adapter.test_submit(spec).to_dict() → format_feasibility()
    인데 `to_dict()` 가 `message[:400]` 으로 잘랐다. 기존 테스트 3건은 `feas` 딕셔너리를
    **손으로 만들어** `to_dict()` 를 아예 거치지 않아 이 버그를 못 잡았다.
    ⇒ 여기서는 반드시 `to_dict()` 를 거친다.
    """

    LONG = ("qsub: request rejected as filter hook 'job_submit_filter' encountered "
            "an error while validating the submission. " + ("x" * 380)
            + " ROOT_CAUSE_AT_THE_VERY_END: ncpus=64 not permitted in queue normal")

    def test_to_dict_keeps_the_whole_message(self):
        chk = sch.SubmissionCheck("probe_node", False, "qsub -h", self.LONG)
        d = chk.to_dict()
        self.assertEqual(len(self.LONG), len(d["message"]),
                         "to_dict() 가 메시지를 잘랐다")
        self.assertIn("ROOT_CAUSE_AT_THE_VERY_END", d["message"])

    def test_to_dict_reports_the_size(self):
        d = sch.SubmissionCheck("k", False, "m", self.LONG).to_dict()
        self.assertEqual(len(self.LONG), d["message_bytes"])

    def test_end_to_end_through_to_dict_and_formatter(self):
        """to_dict() → format_feasibility() 전 구간에서 원인이 살아남는가."""
        from sei_pilot import cli
        chk = sch.SubmissionCheck("probe_node", False, "qsub -h", self.LONG)
        feas = {"checked": True, "n_ok": 0, "n_rejected": 1, "n_unknown": 0,
                "precheck_method": "qsub -h + qdel",
                "precheck_has_side_effects": True,
                "results": [chk.to_dict()]}
        lines = cli.format_feasibility(feas)
        unwrapped = "".join(l[5:] for l in lines if l.startswith(" !   "))
        self.assertIn("ROOT_CAUSE_AT_THE_VERY_END", unwrapped,
                      "실제 경로에서 원인이 소실됐다")
        self.assertIn("ncpus=64 not permitted", unwrapped)


class TestEmitScriptMatchesSubmission(unittest.TestCase):
    """🔴 critic2: `--emit-script` 가 `--level` 을 무시해 **제출본과 달랐다.**

    같은 `build_spec()` 을 써도 **입력(common_env)이 다르면 출력이 갈린다.**
    디버깅 도구가 실제와 다른 것을 보여주면 그 도구는 해롭다.
    """

    def _args(self, level=None):
        class A(object):
            pass
        a = A()
        a.pkg_root = context.PKG_ROOT
        a.level = level
        a.qos = None
        a.reservation = None
        a.ncpus_per_node = None
        a._resolved_account = "etc"
        return a

    def _env_for(self, level):
        from sei_pilot import cli
        from sei_pilot.state import Store
        store = Store(tempfile.mkdtemp(prefix="sei_env_"))
        self.addCleanup(shutil.rmtree, store.workdir, True)
        return cli.build_common_env(self._args(level), store, "normal")

    def test_level_reaches_the_common_env(self):
        self.assertEqual("1", self._env_for("g2")["SEI_QC_LEVEL"])
        self.assertEqual("2", self._env_for(None)["SEI_QC_LEVEL"])

    def test_both_paths_use_the_same_builder(self):
        """제출과 emit-script 가 **같은 함수**로 common_env 를 만드는가."""
        import inspect
        from sei_pilot import cli
        src = inspect.getsource(cli)
        calls = src.count("build_common_env(args, store, part)") - src.count(
            "def build_common_env(args, store, part)")
        self.assertEqual(3, calls,
                         "common_env 를 부르는 곳이 3군데(제출/emit-script/사전검사)가 "
                         "아니다: %d" % calls)
        # 🔴 누구도 자기만의 환경 딕셔너리를 만들지 않는다.
        self.assertNotIn('env={"SEI_PKG_ROOT": args.pkg_root, '
                         '"SEI_WORKDIR": store.workdir}', src)

    def test_precheck_uses_the_same_spec_builder_as_submission(self):
        """🔴 사전검사가 실제 제출과 다른 스크립트를 검사하면 존재 이유가 없다."""
        import inspect
        from sei_pilot import cli
        src = inspect.getsource(cli.submission_feasibility)
        self.assertIn("build_spec(", src)
        self.assertNotIn("sched_mod.JobSpec(", src,
                         "사전검사가 자기만의 JobSpec 을 만든다")


class TestConfigKeysAreActuallyRead(unittest.TestCase):
    """🔴 critic2: `pbs.ncpus_per_node` / `pbs.emit_stdio_lines` 가 죽은 설정이었다.

    JSON 주석은 "여기 넣거나 플래그로 덮으라"고 했는데 코드가 읽지 않았다.
    사용자가 고쳐도 조용히 무시되고 같은 이유로 또 거부된다.
    """

    # 🔴 예전 판은 `inspect.getsource(cli.build_spec)` 에서 **문자열을 찾아** 우선순위를
    #    확인했다. [critic3 중대] 수정으로 그 로직이 `plan.ncpus_override_from_config()`
    #    로 옮겨가자 **동작은 그대로인데 테스트만 깨졌다.**
    #    ⟹ 소스 문자열이 아니라 **동작**을 본다(ADR-041: 부품 위치가 아니라 결과).
    def test_ncpus_from_config_is_used_when_flag_absent(self):
        from sei_pilot import plan as plan_mod
        from sei_pilot import config
        cfg = (config.load("sizing.json", {}).get("pbs") or {})
        class _NoFlag(object):
            ncpus_per_node = None
        got = plan_mod.ncpus_override_from_config(_NoFlag())
        want = int(cfg["ncpus_per_node"]) if cfg.get("ncpus_per_node") else None
        self.assertEqual(got, want,
                         "config/sizing.json 의 ncpus_per_node 가 읽히지 않는다")

    def test_flag_beats_config(self):
        """플래그가 설정값을 이긴다 — **값으로** 확인한다."""
        from sei_pilot import plan as plan_mod
        class _WithFlag(object):
            ncpus_per_node = 7
        self.assertEqual(plan_mod.ncpus_override_from_config(_WithFlag()), 7)

    def test_p6_is_exempt_from_the_override(self):
        """🔴 [critic3 중대] P6 의 코어 수는 **사이징 파라미터가 아니라 측정 대상**이다.

        override 가 P6 에 적용되면 1/16/64 가 전부 같아져 **S(스케일링)가 무의미**해지고,
        런타임 게이트가 `[INVALID]` 로 버려 **예산 1,944 core-h 가 통째로 헛돈다.**
        """
        from sei_pilot import plan as plan_mod
        for key in ("P6_t1", "P6_t16", "P6_t64"):
            self.assertTrue(plan_mod.item_cores_are_the_measurement(key), key)
        for key in ("P1", "P5", "P1b", "probe_node"):
            self.assertFalse(plan_mod.item_cores_are_the_measurement(key), key)

    def test_config_note_no_longer_claims_both_when_only_one_works(self):
        from sei_pilot import config
        note = (config.load("sizing.json", {}).get("pbs") or {})["_ncpus_note"]
        self.assertIn("우선순위", note)


class TestFullPathFromFeasibilityToScreen(unittest.TestCase):
    """🔴 lead/critic2 요구: `submission_feasibility()` **부터** 화면 출력까지 전 구간.

    이전 테스트들은 `feas` 딕셔너리를 손으로 만들거나 `to_dict()` 만 따로 불러서,
    `submission_feasibility()` 안에서 일어나는 일을 전혀 지나지 않았다.
    **컴포넌트는 고쳤는데 경로를 안 탄** B-3 과 같은 형태였다(세 번째 반복).
    """

    LONG_REJECT = (
        "qsub: request rejected as filter hook 'job_submit_filter' encountered an "
        "error while validating the job submission for user yanselmo. "
        + ("detail " * 55)
        + "FINAL_REASON: account 'etc' is not permitted for queue normal")

    class _RejectingAdapter(object):
        """모든 사전검사를 긴 메시지로 거부하는 가짜 어댑터."""
        PRECHECK_HAS_SIDE_EFFECTS = True
        name = "pbs"

        def __init__(self, message):
            self.message = message

        def test_submit(self, spec):
            return sch.SubmissionCheck(spec.key, False, "qsub -h", self.message)

    def _run(self):
        from sei_pilot import cli
        from sei_pilot.state import Store

        class A(object):
            pass
        args = A()
        args.pkg_root = context.PKG_ROOT
        args.workdir = tempfile.mkdtemp(prefix="sei_feas_")
        self.addCleanup(shutil.rmtree, args.workdir, True)
        args.level = None
        args.qos = None
        args.reservation = None
        args.ncpus_per_node = None
        args.account = None
        args.partition = "normal"
        args.queue = None
        args.no_precheck = False
        args.profile = "cpu"
        store = Store(args.workdir)
        env = {"scheduler": "pbs", "cores_per_node": 64, "software": {},
               "gpus": {}, "modules": [], "partitions": [], "_login": {}}
        planned = [{"key": "probe_node", "status": "planned", "nodes": 1,
                    "cores_per_node": 64, "wall_h": 0.25, "payload": "payload/x.sh",
                    "account": "etc", "account_key": "probe"}]
        adapter = self._RejectingAdapter(self.LONG_REJECT)
        orig = cli.sched_mod.make_adapter
        cli.sched_mod.make_adapter = lambda *a, **k: adapter
        try:
            feas = cli.submission_feasibility(args, FakeShell(), store, env,
                                              planned, quiet=True)
        finally:
            cli.sched_mod.make_adapter = orig
        return feas, cli.format_feasibility(feas)

    def test_message_survives_submission_feasibility(self):
        feas, _lines = self._run()
        msg = feas["results"][0]["message"]
        self.assertEqual(len(self.LONG_REJECT), len(msg),
                         "submission_feasibility 를 지나며 메시지가 잘렸다 "
                         "(%d → %d 자)" % (len(self.LONG_REJECT), len(msg)))
        self.assertIn("FINAL_REASON", msg)

    def test_message_is_longer_than_the_old_400_char_cut(self):
        """400자를 넘지 않으면 이 테스트는 예전 버그를 못 잡는다."""
        self.assertGreater(len(self.LONG_REJECT), 400)

    def test_root_cause_reaches_the_screen(self):
        _feas, lines = self._run()
        unwrapped = "".join(l[5:] for l in lines if l.startswith(" !   "))
        self.assertIn("FINAL_REASON", unwrapped,
                      "전 구간을 지나며 원인이 소실됐다")
        self.assertIn("account 'etc' is not permitted", unwrapped)

    def test_screen_tells_user_to_send_the_whole_thing(self):
        _feas, lines = self._run()
        text = "\n".join(lines)
        self.assertIn("전문", text)
        self.assertIn("--emit-script", text)


class TestEmitScriptIsByteIdenticalToSubmission(unittest.TestCase):
    """🔴 "제출본 ≡ emit 출력" — **각 경로의 진입점을 실제로 호출해서** 비교한다.

    ⚠ 이 테스트의 이전 판이 `-q` 누락(critic2 BLOCK)을 **못 잡았다.** 이유:
        `_scripts()` 가 `build_spec(..., "normal", ...)` 로 **두 '경로' 모두에
        `"normal"` 을 하드코딩**했다. 같은 함수를 같은 인자로 두 번 부른 것이라
        `default_partition()` 도 `cmd_emit_script` 의 실제 폴백도 한 번도 등장하지 않았다.
    **"같은 입력을 두 번 넣어 같은 출력이 나온다"는 항등식이지 검증이 아니다.**
    ⇒ 동일성 테스트는 **각 경로의 *입력 생성 로직*까지** 타야 한다.
    """

    class _Recording(object):
        """PbsAdapter 를 감싸 렌더링된 스크립트를 붙잡는 어댑터."""
        PRECHECK_HAS_SIDE_EFFECTS = True
        supports_dependency = True
        name = "pbs"

        def __init__(self, templates):
            self.inner = sch.PbsAdapter(FakeShell(), templates)
            self.scripts = {}

        def write_script(self, spec, deps=None):
            path = self.inner.write_script(spec, deps)
            with open(path) as fh:
                self.scripts[spec.key] = fh.read()
            return path

        def submit(self, spec, deps=None):
            self.write_script(spec)
            return "12345.pbs"

        def submit_chain(self, spec, links):
            self.write_script(spec)
            return ["12345.pbs"]

        def test_submit(self, spec):
            self.write_script(spec)
            return sch.SubmissionCheck(spec.key, True, "qsub -h", "ok")

    def _args(self, workdir, level=None, queue=None):
        """🔴 **실제 argparse 파서**로 만든다.

        손으로 속성을 채우면 기본값이 진짜와 달라지고, 그러면 이 테스트가 검증하는
        것은 실제 CLI 가 아니라 내가 상상한 CLI 다.
        """
        from sei_pilot import cli
        argv = ["submit", "--workdir", workdir, "--pkg-root", context.PKG_ROOT]
        if level:
            argv += ["--level", level]
        if queue:
            argv += ["--queue", queue]
        a = cli.build_parser().parse_args(argv)
        a.pkg_root = os.path.abspath(a.pkg_root)
        a.workdir = os.path.abspath(a.workdir)
        return a

    # 🔴 PBS 클러스터의 현실: `sinfo` 가 없어 partitions 가 **비어 있다.**
    #    이것이 -q 누락의 원인이었으므로 픽스처가 반드시 이 상태여야 한다.
    ENV = {"scheduler": "pbs", "cores_per_node": 64, "partitions": [],
           "software": {"g16": {"path": "/apps/g16/g16", "version": "g16"}},
           "gpus": {}, "modules": [], "_login": {}, "vendored": {},
           "containers": {}, "qc_module": None}

    def _emit_directives(self, level=None, queue=None, workdir=None):
        from sei_pilot import cli
        from sei_pilot.state import Store
        import io
        d = workdir
        if d is None:
            d = tempfile.mkdtemp(prefix="sei_emit_")
            self.addCleanup(shutil.rmtree, d, True)
        args = self._args(d, level=level, queue=queue)
        args.emit_script = "P1"
        store = Store(d)
        buf, orig = io.StringIO(), sys.stdout
        orig_make = cli.sched_mod.make_adapter
        rec = self._Recording(TEMPLATES)
        cli.sched_mod.make_adapter = lambda *a, **k: rec
        try:
            sys.stdout = buf
            cli.cmd_emit_script(args, shell=FakeShell(), store=store,
                                env=dict(self.ENV))
        finally:
            sys.stdout = orig
            cli.sched_mod.make_adapter = orig_make
        return rec.scripts["P1"]

    def _submit_directives(self, level=None, queue=None, workdir=None):
        from sei_pilot import cli
        from sei_pilot.state import Store
        import io
        d = workdir
        if d is None:
            d = tempfile.mkdtemp(prefix="sei_sub_")
            self.addCleanup(shutil.rmtree, d, True)
        args = self._args(d, level=level, queue=queue)
        store = Store(d)
        rec = self._Recording(TEMPLATES)
        orig_make = cli.sched_mod.make_adapter
        cli.sched_mod.make_adapter = lambda *a, **k: rec
        buf, orig = io.StringIO(), sys.stdout
        try:
            sys.stdout = buf
            cli.cmd_submit(args, shell=FakeShell(), store=store,
                           env=dict(self.ENV))
        finally:
            sys.stdout = orig
            cli.sched_mod.make_adapter = orig_make
        return rec.scripts["P1"]

    def _dirs(self, text):
        return [l for l in text.splitlines() if l.startswith("#PBS")]

    def test_queue_directive_is_present_in_the_submitted_script(self):
        """🔴 이것이 critic2 BLOCK 의 본체다 — 실제 제출본에 `-q` 가 있는가."""
        d = self._dirs(self._submit_directives())
        self.assertTrue(any(l.startswith("#PBS -q") for l in d),
                        "제출 스크립트에 `-q` 가 없다: %s" % d)

    def test_queue_directive_is_present_in_the_emitted_script(self):
        d = self._dirs(self._emit_directives())
        self.assertTrue(any(l.startswith("#PBS -q") for l in d), d)

    def test_both_paths_agree_on_the_queue(self):
        """emit 은 `-q normal` 을 보여주는데 제출본엔 없던 것이 이번 사고다."""
        def q(text):
            return [l for l in self._dirs(text) if l.startswith("#PBS -q")]
        self.assertEqual(q(self._submit_directives()), q(self._emit_directives()))

    def test_directive_blocks_are_identical(self):
        self.assertEqual(self._dirs(self._submit_directives()),
                         self._dirs(self._emit_directives()))

    def test_level_reaches_both_paths_identically(self):
        for level in (None, "g2"):
            sub = self._submit_directives(level=level)
            emit = self._emit_directives(level=level)
            for text in (sub, emit):
                self.assertIn('export SEI_QC_LEVEL="%s"' % ("1" if level else "2"),
                              text)

    def test_explicit_queue_flag_reaches_both(self):
        for get in (self._submit_directives, self._emit_directives):
            self.assertIn("#PBS -q bigmem", self._dirs(get(queue="bigmem")))

    def test_fixture_really_has_no_sinfo_partitions(self):
        """픽스처가 PBS 현실(partitions 비어 있음)을 재현하는지 자체를 지킨다."""
        self.assertEqual([], self.ENV["partitions"])

    def test_whole_script_is_byte_identical_not_just_directives(self):
        """🔴 이전 판(`test_directive_blocks_are_identical`)은 `#PBS` 줄만 비교했다 --
        "제출본 ≡ emit 출력" 이라는 주장은 스크립트 **전문**에 대한 것이었는데, 그 주장을
        실제로 검증한 적이 없었다(lead 지적, cli.py:702 KeyError 사고의 진단문). 여기서
        본문(모듈 로드/ENV export/COMMAND)까지 포함해 바이트 단위로 비교한다.

        🔴 같은 workdir 을 두 경로에 강제한다 -- 각자 자기 tempdir 을 파면 SEI_JOB_DIR/
        SEI_WORKDIR export 줄이 경로 문자열만으로 갈라져 "같은 입력인데 다른 출력"이 아니라
        "다른 입력을 넣어 놓고 다르다고 착각하는" 거짓 실패가 된다."""
        d = tempfile.mkdtemp(prefix="sei_byte_identical_")
        self.addCleanup(shutil.rmtree, d, True)
        self.assertEqual(self._submit_directives(workdir=d),
                         self._emit_directives(workdir=d))


class TestEmitScriptOnAnUnplannedItem(unittest.TestCase):
    """🔴 cli.py:702 `KeyError: 'wall_h'` — 실제 사고 재현.

    `--emit-script`는 항목의 `status`를 보지 않고 `planned`(빌드 계획 목록 전체, skip 된
    것도 포함)에서 이름으로 찾아 곧장 `build_spec`에 넘겼다. `wall_h`/`cores_per_node`/
    `reserved_core_hours` 는 `plan.py`의 `entry.update()`가 sizing 을 통과한 항목에만
    채우는 값이라, QC 엔진이 없어 `status="skipped"`인 항목(이 저장소의 실제 개발 박스가
    바로 이 상태다 -- g16 이 없다)을 emit 하면 죽었다. `cmd_submit`의 제출 루프는
    `if entry["status"] != "planned": continue` 로 이미 이 게이트를 갖고 있었다 -- emit
    에는 없었다는 것이 사고의 실체(같은 성질을 두 경로가 서로 다르게 지킨 것, cli.py:470의
    큐 사고와 같은 클래스, 이번 라운드 열 번째 사례).

    🔒 아래 `test_reproduces_the_real_incident_without_crashing`는 **수정 전 코드에서
    실제로 KeyError 를 낸다** -- 고치기 전에 이 테스트만 먼저 돌려 RED 를 확인했다
    (`git stash`/mutation 없이, cli.py 를 되돌린 사본에 대고 직접 재현). 회귀 테스트가
    "수정 전에 깨지는지"를 보증하지 못하면 검증이 아니라는 것이 이 파일 자체의 교훈
    (561줄 아래 주석, 같은 사고의 자매 사고)이라 여기서도 그 규율을 반복한다.
    """

    #: 🔴 g16 이 전혀 없다 -- 이 저장소의 실제 개발 박스 상태를 그대로 재현한다
    #:   (`software`/`qc_module`/`vendored`/`containers` 모두 비어 있어야 `check_
    #:   requirements`가 "사용 가능한 실행 수단 없음"으로 SKIP 시킨다).
    ENV = {"scheduler": "pbs", "cores_per_node": 64, "partitions": [],
           "software": {}, "gpus": {}, "modules": [], "_login": {},
           "vendored": {}, "containers": {}, "qc_module": None}

    def _args(self, workdir):
        from sei_pilot import cli
        argv = ["submit", "--workdir", workdir, "--pkg-root", context.PKG_ROOT]
        a = cli.build_parser().parse_args(argv)
        a.pkg_root = os.path.abspath(a.pkg_root)
        a.workdir = os.path.abspath(a.workdir)
        a.emit_script = "P1"          # g16 이 필요한 항목 -- 이 ENV 에서는 SKIP 된다
        return a

    def test_reproduces_the_real_incident_without_crashing(self):
        from sei_pilot import cli
        from sei_pilot.state import Store
        import io
        d = tempfile.mkdtemp(prefix="sei_emit_unplanned_")
        self.addCleanup(shutil.rmtree, d, True)
        store = Store(d)
        buf, errbuf, orig_out, orig_err = io.StringIO(), io.StringIO(), sys.stdout, sys.stderr
        try:
            sys.stdout, sys.stderr = buf, errbuf
            rc = cli.cmd_emit_script(self._args(d), shell=FakeShell(), store=store,
                                     env=dict(self.ENV))
        finally:
            sys.stdout, sys.stderr = orig_out, orig_err
        # 🔒 크래시(예외)가 아니라 정상적인 음이 아닌 정수 반환 -- 이전에는 여기서
        #    KeyError 가 이 테스트 메서드 자체를 ERROR 로 죽였다.
        self.assertIsInstance(rc, int)
        self.assertNotEqual(0, rc)
        self.assertIn("계획되지 않았다", errbuf.getvalue())
        self.assertIn("skipped", errbuf.getvalue())


# ⚠ 이 자리에 있던 이전 판 TestEmitScriptIsByteIdenticalToSubmission 을 제거했다.
#    `build_spec(..., "normal", ...)` 로 두 "경로" 모두에 큐를 하드코딩해
#    같은 함수를 두 번 부르는 항등식이었고, -q 누락을 못 잡았다(critic2 BLOCK).
#    🔴 그리고 클래스 이름이 같아 **뒤 정의가 새 판을 통째로 덮고 있었다** —
#    새 테스트는 한 번도 실행되지 않았다. 되돌린 코드에서도 33건이 전부 통과해
#    그 사실이 드러났다. 회귀 테스트는 반드시 "수정 전 코드에서 깨지는지"를 봐야 한다.



class TestNoDuplicateTestClassNames(unittest.TestCase):
    """🔴 같은 이름의 클래스가 두 번 정의되면 **뒤엣것이 앞엣것을 조용히 덮는다.**

    이번 라운드에 실제로 났다: 새 판을 기존과 같은 이름으로 붙여 낡은 정의가 새 테스트를
    통째로 덮었고, **새 테스트는 한 번도 실행되지 않았다.** 되돌린 코드에서도 전부
    통과해서야 알았다. (critic2 가 그 잔해까지 찾아냈다 — 동일 내용 중복 1건.)

    ⇒ **"테스트가 존재하지도 않는데 통과"** 는 이 프로젝트 실패 유형의 다섯 번째 변주다.
    이름 충돌은 기계가 잡을 수 있으므로 기계에 맡긴다.
    """

    @staticmethod
    def _python_files():
        """🔴 `tests/` **와** `sei_pilot/` 둘 다 본다 (lead 지시).

        중복 정의는 테스트에서만 나는 사고가 아니다 — 제품 코드에서 나면 **뒤 정의가
        앞을 덮어 함수가 통째로 사라지고**, 그건 눈으로 거의 못 잡는다.
        """
        out = []
        here = os.path.dirname(os.path.abspath(__file__))
        for name in sorted(os.listdir(here)):
            if name.startswith("test_") and name.endswith(".py"):
                out.append(os.path.join(here, name))
        for root, _dirs, files in os.walk(os.path.join(context.PKG_ROOT,
                                                       "sei_pilot")):
            for name in sorted(files):
                if name.endswith(".py"):
                    out.append(os.path.join(root, name))
        return out

    def test_scan_covers_both_trees(self):
        """검사 대상이 실제로 두 트리를 덮는지 자체를 지킨다."""
        files = self._python_files()
        self.assertTrue(any("sei_pilot" in f for f in files), "제품 코드가 빠졌다")
        self.assertTrue(any("tests" in f for f in files), "테스트가 빠졌다")
        self.assertGreater(len(files), 20)

    def test_no_module_defines_the_same_class_twice(self):
        import ast as _ast
        offenders = {}
        for path in self._python_files():
            name = os.path.relpath(path, context.REPO_ROOT)
            with open(path) as fh:
                tree = _ast.parse(fh.read(), filename=name)
            seen, dup = set(), []
            for node in tree.body:
                if isinstance(node, _ast.ClassDef):
                    if node.name in seen:
                        dup.append(node.name)
                    seen.add(node.name)
            if dup:
                offenders[name] = dup
        self.assertEqual({}, offenders,
                         "같은 이름의 테스트 클래스가 두 번 정의됐다 — "
                         "뒤엣것이 앞엣것을 덮어 일부 테스트가 실행되지 않는다")

    def test_no_module_defines_the_same_function_twice(self):
        """모듈 수준 함수도 같은 방식으로 조용히 덮인다."""
        import ast as _ast
        offenders = {}
        for path in self._python_files():
            name = os.path.relpath(path, context.REPO_ROOT)
            with open(path) as fh:
                tree = _ast.parse(fh.read(), filename=name)
            seen, dup = set(), []
            for node in tree.body:
                if isinstance(node, _ast.FunctionDef):
                    if node.name in seen:
                        dup.append(node.name)
                    seen.add(node.name)
            if dup:
                offenders[name] = dup
        self.assertEqual({}, offenders)

    def test_no_class_defines_the_same_method_twice(self):
        """🔴 메서드 중복이 가장 조용하다 — 클래스는 하나뿐이라 눈에 안 띈다."""
        import ast as _ast
        offenders = {}
        for path in self._python_files():
            name = os.path.relpath(path, context.REPO_ROOT)
            with open(path) as fh:
                tree = _ast.parse(fh.read(), filename=name)
            for node in _ast.walk(tree):
                if not isinstance(node, _ast.ClassDef):
                    continue
                seen, dup = set(), []
                for sub in node.body:
                    if isinstance(sub, _ast.FunctionDef):
                        if sub.name in seen:
                            dup.append(sub.name)
                        seen.add(sub.name)
                if dup:
                    offenders["%s::%s" % (name, node.name)] = dup
        self.assertEqual({}, offenders)


class TestQueueWaitPrecheckMatchesActualSubmission(unittest.TestCase):
    """🔴 `probe_queuewait` 는 제출 시 **개별 잡으로 쪼개진다.**

    사전검사는 항목 선언값(`nodes=85, cores_per_node=64`)으로 스펙을 만들어
    `select=85:ncpus=64` 를 시험했다. 그 형태는 **한 번도 제출되지 않는다** — 실제로는
    1/4/16 노드 × 1코어 잡 3개가 나간다(critic2).

    더 나쁜 것: `config/sizing.json` 주석에 *"85노드 요청이 거부됐다"* 고 적혀 있으니
    **사전검사가 과거에 거부당한 바로 그 형태를 재현해 다시 시험하고 있었다.**
    큐 상한이 있는 사이트면 이 항목만 "거부됨"으로 떠서 **실제로는 문제없을 3개 잡까지
    사용자가 의심하게 된다.**
    """

    ENV = {"scheduler": "pbs", "cores_per_node": 64, "partitions": [],
           "software": {}, "gpus": {}, "modules": [], "_login": {},
           "vendored": {}, "containers": {}, "qc_module": None}

    class _Rec(object):
        PRECHECK_HAS_SIDE_EFFECTS = True
        supports_dependency = True
        name = "pbs"

        def __init__(self):
            self.inner = sch.PbsAdapter(FakeShell(), TEMPLATES)
            self.seen = {}

        def write_script(self, spec, deps=None):
            path = self.inner.write_script(spec, deps)
            with open(path) as fh:
                self.seen[spec.key] = [l for l in fh
                                       if l.startswith("#PBS -l select")]
            return path

        def submit(self, spec, deps=None):
            self.write_script(spec)
            return "1.pbs"

        def submit_chain(self, spec, links):
            self.write_script(spec)
            return ["1.pbs"]

        def test_submit(self, spec):
            self.write_script(spec)
            return sch.SubmissionCheck(spec.key, True, "qsub -h", "ok")

    def _run(self):
        from sei_pilot import cli
        from sei_pilot.state import Store
        import io
        d = tempfile.mkdtemp(prefix="sei_qw_")
        self.addCleanup(shutil.rmtree, d, True)
        args = cli.build_parser().parse_args(
            ["submit", "--workdir", d, "--pkg-root", context.PKG_ROOT])
        args.pkg_root = os.path.abspath(args.pkg_root)
        args.workdir = os.path.abspath(args.workdir)
        args.no_precheck = False
        rec = self._Rec()
        orig = cli.sched_mod.make_adapter
        cli.sched_mod.make_adapter = lambda *a, **k: rec
        buf, so = io.StringIO(), sys.stdout
        try:
            sys.stdout = buf
            cli.cmd_submit(args, shell=FakeShell(), store=Store(d),
                           env=dict(self.ENV))
        finally:
            sys.stdout = so
            cli.sched_mod.make_adapter = orig
        return rec, buf.getvalue()

    def test_precheck_shape_is_one_of_the_actually_submitted_shapes(self):
        rec, _out = self._run()
        pre = rec.seen["check_probe_queuewait"]
        actual = [v for k, v in rec.seen.items() if k.startswith("probe_qw_n")]
        self.assertIn(pre, actual,
                      "사전검사가 실제로 제출되지 않는 형태를 시험한다: %s vs %s"
                      % (pre, actual))

    def test_precheck_uses_the_largest_actual_job(self):
        rec, _out = self._run()
        self.assertIn("select=16:ncpus=1", "".join(rec.seen["check_probe_queuewait"]))

    def test_the_rejected_85_node_shape_is_never_rendered(self):
        """🔴 과거 거부된 형태가 어디에서도 나가지 않는가."""
        rec, _out = self._run()
        for key, lines in rec.seen.items():
            self.assertNotIn("select=85", "".join(lines),
                             "%s 가 85노드를 요청한다" % key)

    def test_actual_jobs_respect_the_cap(self):
        from sei_pilot import cli, config
        cap = (config.load("sizing.json", {}).get("pbs") or {})["max_probe_nodes"]
        rec, _out = self._run()
        for key, lines in rec.seen.items():
            if not key.startswith("probe_qw_n"):
                continue
            n = int(key.replace("probe_qw_n", ""))
            self.assertLessEqual(n, cap)

    def test_capping_is_announced_on_screen(self):
        _rec, out = self._run()
        self.assertIn("축소", out, "축소 사실이 화면에 안 뜬다")

    def test_capping_is_recorded_for_the_report(self):
        from sei_pilot.state import Store
        rec, _out = self._run()
        # _run 이 만든 store 를 다시 못 보므로 분해 함수로 사실만 확인한다
        from sei_pilot import cli
        d = cli.queue_wait_decomposition(self.ENV)
        self.assertEqual([64], d["dropped_by_cap"])
        self.assertEqual([1, 4, 16], d["node_counts"])

    def test_decomposition_is_shared_not_duplicated(self):
        """🔴 `max_probe_nodes` 가 바뀌면 두 경로가 **함께** 따라와야 한다."""
        import inspect
        from sei_pilot import cli
        for fn in (cli.submit_entry, cli.submission_feasibility):
            self.assertIn("queue_wait_decomposition", inspect.getsource(fn),
                          "%s 가 분해를 공유하지 않는다" % fn.__name__)


class TestPrecheckFollowsTheCap(unittest.TestCase):
    """🔴 `cap` 을 바꾸면 **사전검사와 실제 제출이 함께** 따라오는가.

    lead 지적: 대표값을 사전검사 쪽에 **16으로 하드코딩**하면 `max_probe_nodes` 가
    바뀔 때 또 조용히 갈린다. *"cap 을 바꿔가며 양쪽이 함께 따라오는지 고정하라 —
    이게 (c)를 지키는 유일한 방법이다."*

    그래서 이 테스트는 `cap` 을 **16과 4로 각각 바꿔** 실제 진입점을 돌리고,
    사전검사가 만드는 spec 이 **그때그때 실제 제출 집합에 들어있는지** 본다.
    """

    ENV = {"scheduler": "pbs", "cores_per_node": 64, "partitions": [],
           "software": {}, "gpus": {}, "modules": [], "_login": {},
           "vendored": {}, "containers": {}, "qc_module": None}

    def _run_with_cap(self, cap):
        """`config.load` 를 가로채 cap 만 바꾼다 — 실제 호출 경로는 그대로 탄다."""
        from sei_pilot import cli, config
        from sei_pilot.state import Store
        import io
        Rec = TestQueueWaitPrecheckMatchesActualSubmission._Rec
        real_load = config.load

        def fake_load(name, default=None, config_dir=None):
            data = real_load(name, default, config_dir)
            if name == "sizing.json":
                data = dict(data)
                data["pbs"] = dict(data.get("pbs") or {})
                data["pbs"]["max_probe_nodes"] = cap
            return data

        d = tempfile.mkdtemp(prefix="sei_cap_")

        self.addCleanup(shutil.rmtree, d, True)
        args = cli.build_parser().parse_args(
            ["submit", "--workdir", d, "--pkg-root", context.PKG_ROOT])
        args.pkg_root = os.path.abspath(args.pkg_root)
        args.workdir = os.path.abspath(args.workdir)
        args.no_precheck = False
        rec = Rec()
        orig_make = cli.sched_mod.make_adapter
        cli.sched_mod.make_adapter = lambda *a, **k: rec
        config.load = fake_load
        cli.config.load = fake_load
        buf, so = io.StringIO(), sys.stdout
        try:
            sys.stdout = buf
            cli.cmd_submit(args, shell=FakeShell(), store=Store(d),
                           env=dict(self.ENV))
        finally:
            sys.stdout = so
            cli.sched_mod.make_adapter = orig_make
            config.load = real_load
            cli.config.load = real_load
        return rec

    def _select(self, lines):
        return "".join(lines).strip()

    def test_cap_16_precheck_matches_largest_actual(self):
        rec = self._run_with_cap(16)
        actual = dict((k, self._select(v)) for k, v in rec.seen.items()
                      if k.startswith("probe_qw_n"))
        self.assertEqual({"probe_qw_n1", "probe_qw_n4", "probe_qw_n16"},
                         set(actual))
        self.assertEqual(actual["probe_qw_n16"],
                         self._select(rec.seen["check_probe_queuewait"]))

    def test_cap_4_precheck_follows_automatically(self):
        """🔴 여기가 하드코딩을 잡는 지점 — cap=4 면 사전검사도 4여야 한다."""
        rec = self._run_with_cap(4)
        actual = dict((k, self._select(v)) for k, v in rec.seen.items()
                      if k.startswith("probe_qw_n"))
        self.assertEqual({"probe_qw_n1", "probe_qw_n4"}, set(actual),
                         "cap=4 인데 제출 집합이 안 따라왔다: %s" % sorted(actual))
        pre = self._select(rec.seen["check_probe_queuewait"])
        self.assertEqual(actual["probe_qw_n4"], pre,
                         "cap=4 인데 사전검사가 %s 를 시험한다 (16 하드코딩?)" % pre)
        self.assertNotIn("select=16", pre)

    def test_precheck_is_always_a_member_of_the_actual_set(self):
        """cap 값에 무관한 불변식."""
        for cap in (1, 4, 16):
            rec = self._run_with_cap(cap)
            actual = [self._select(v) for k, v in rec.seen.items()
                      if k.startswith("probe_qw_n")]
            pre = self._select(rec.seen["check_probe_queuewait"])
            self.assertIn(pre, actual, "cap=%d 에서 사전검사가 유령 잡을 시험한다" % cap)

    def test_only_one_precheck_job_per_item(self):
        """`qsub -h` 는 부작용이 있다 — 3개 다 시험하면 held job 위험이 3배다."""
        rec = self._run_with_cap(16)
        self.assertEqual(1, sum(1 for k in rec.seen
                                if k == "check_probe_queuewait"))


class TestQueueWaitFourPlacesFollowOneSource(unittest.TestCase):
    """🔴 `max_probe_nodes` 를 바꾸면 **네 곳이 함께** 움직이는가 (lead 요구 4).

    네 곳: ①계획 표시(nodes) ②예약 core-h ③사전검사 spec ④실제 제출 spec.
    하나라도 따로 계산하면 그 자리가 조용히 갈린다 — 실제로 ①②가 `85`(= 1+4+16+64
    **합계**)에 묶여 있었고, 🔴 **lead 가 표의 85 를 보고 "85노드가 거부됐다"는 틀린
    지시를 보냈다.** engineer 는 이 값으로 봉투를 계산한다. **오표시의 대가가 이미 났다.**
    """

    ENV = {"scheduler": "pbs", "cores_per_node": 64, "partitions": [],
           "software": {}, "gpus": {}, "modules": [], "_login": {},
           "vendored": {}, "containers": {}, "qc_module": None}

    def _all_four(self, cap):
        """cap 하나만 바꾸고 네 곳을 모두 뽑는다."""
        from sei_pilot import budget, cli, config, plan
        from sei_pilot.state import Store
        import io
        Rec = TestQueueWaitPrecheckMatchesActualSubmission._Rec
        real_load = config.load

        def fake_load(name, default=None, config_dir=None):
            data = real_load(name, default, config_dir)
            if name == "sizing.json":
                data = dict(data)
                data["pbs"] = dict(data.get("pbs") or {})
                data["pbs"]["max_probe_nodes"] = cap
            return data

        config.load = fake_load
        cli.config.load = fake_load
        plan.config.load = fake_load
        try:
            planned, _summary = plan.build_plan(
                dict(self.ENV), budget.guard_for_profile("cpu"), profile="cpu")
            entry = [p for p in planned if p["key"] == "probe_queuewait"][0]
            d = tempfile.mkdtemp(prefix="sei_four_")
            self.addCleanup(shutil.rmtree, d, True)
            args = cli.build_parser().parse_args(
                ["submit", "--workdir", d, "--pkg-root", context.PKG_ROOT])
            args.pkg_root = os.path.abspath(args.pkg_root)
            args.workdir = os.path.abspath(args.workdir)
            args.no_precheck = False
            rec = Rec()
            orig = cli.sched_mod.make_adapter
            cli.sched_mod.make_adapter = lambda *a, **k: rec
            buf, so = io.StringIO(), sys.stdout
            try:
                sys.stdout = buf
                cli.cmd_submit(args, shell=FakeShell(), store=Store(d),
                               env=dict(self.ENV))
            finally:
                sys.stdout = so
                cli.sched_mod.make_adapter = orig
        finally:
            config.load = real_load
            cli.config.load = real_load
            plan.config.load = real_load
        submitted = sorted(int(k.replace("probe_qw_n", ""))
                           for k in rec.seen if k.startswith("probe_qw_n"))
        pre = "".join(rec.seen["check_probe_queuewait"])
        return {"display_nodes": entry["nodes"],
                "reserved": entry["reserved_core_hours"],
                "submitted": submitted, "precheck": pre,
                "note": entry.get("note", ""),
                "wall_h": entry["wall_h"]}

    def test_cap16_all_four_agree(self):
        r = self._all_four(16)
        self.assertEqual([1, 4, 16], r["submitted"])
        self.assertEqual(21, r["display_nodes"], "표시가 실제 노드합과 다르다")
        self.assertIn("select=16:ncpus=1", r["precheck"])
        self.assertAlmostEqual(21 * 64 * r["wall_h"], r["reserved"], places=1)

    def test_cap4_all_four_follow(self):
        """🔴 cap 을 바꿨을 때 네 곳이 전부 따라오는가."""
        r = self._all_four(4)
        self.assertEqual([1, 4], r["submitted"])
        self.assertEqual(5, r["display_nodes"],
                         "cap=4 인데 표시가 안 따라왔다: %s" % r["display_nodes"])
        self.assertIn("select=4:ncpus=1", r["precheck"])
        self.assertAlmostEqual(5 * 64 * r["wall_h"], r["reserved"], places=1)

    def test_display_always_equals_the_actual_node_sum(self):
        """🔴 진짜 불변식 — 표시 == 실제로 제출되는 노드 합.

        (처음에는 "85 는 어떤 cap 에서도 나오면 안 된다"로 썼는데 **틀렸다**:
         상한이 64 이상이면 4개가 다 나가서 85 가 **사실**이다. 문제는 85 라는 숫자가
         아니라 **표시가 실제와 다른 것**이었다. 불변식을 그것으로 고쳤다.)
        """
        for cap in (1, 4, 16, 64):
            r = self._all_four(cap)
            self.assertEqual(sum(r["submitted"]), r["display_nodes"],
                             "cap=%s: 표시 %s ≠ 실제 노드합 %s"
                             % (cap, r["display_nodes"], sum(r["submitted"])))

    def test_reservation_shrinks_when_cap_shrinks(self):
        self.assertGreater(self._all_four(16)["reserved"],
                           self._all_four(4)["reserved"])

    def test_dropped_jobs_are_announced_not_hidden(self):
        r = self._all_four(16)
        self.assertIn("64", r["note"])
        self.assertIn("생략", r["note"])

    def test_nothing_dropped_means_no_note(self):
        r = self._all_four(64)
        self.assertEqual([1, 4, 16, 64], r["submitted"])
        self.assertEqual(85, sum(r["submitted"]))
        self.assertEqual(85, r["display_nodes"],
                         "상한이 없으면 85가 맞다 — 그때는 사실이다")
        self.assertEqual("", r["note"])

    def test_reservation_equals_scheduler_enforced_ceiling(self):
        """🔴 예약이 **스케줄러가 강제하는 상한과 같은가.**

        노드 수와 wall 이 고정이므로 실제 소비가 예약을 넘을 수 없다.
        예전 값(250)은 상한도 실측도 아니었다.
        """
        r = self._all_four(16)
        ceiling = sum(r["submitted"]) * 64 * r["wall_h"]
        self.assertAlmostEqual(ceiling, r["reserved"], places=1)
