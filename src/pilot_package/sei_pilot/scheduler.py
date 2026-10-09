"""스케줄러 탐지 + 제출 어댑터 (SLURM / PBS·Torque / 순수 셸).

🔴 이 모듈은 우리 환경에서 실행 검증이 불가능하다(ADR-004: 스케줄러 없음).
따라서 **모든 외부 호출은 shellrun.Shell 로만** 하고, 스크립트 렌더링과 인자 조립은
순수 함수로 뽑아 테스트에서 문자열로 검증한다. 실제 sbatch/qsub 동작은
FakeShell로만 검증되며, **진짜 클러스터에서 처음 돌 때가 최초 실행 검증이다.**
그래서 --dry-run이 필수다.

[UNVERIFIED] 표시가 붙은 곳은 클러스터 방언(PBS Pro vs Torque 등)에 따라 다를 수 있어
실측 전까지 확신할 수 없는 부분이다.
"""

import os
import re

from .state import makedirs

SLURM = "slurm"
PBS = "pbs"
NONE = "none"


class JobSpec(object):
    """제출 단위. 자원 예약과 스크립트 렌더링의 유일한 입력."""

    def __init__(self, key, command, nodes=1, cores_per_node=1, wall_h=1.0,
                 partition=None, array=None, gpus=0, job_dir=None, env=None,
                 exclusive=False, logical_key=None, account=None, qos=None,
                 reservation=None, modules=None, emit_stdio_lines=False):
        self.key = key
        # 🔴 체인 링크(P1, P1_c1, ...)는 key가 서로 다르지만 **논리적으로는 같은 작업**이다.
        #    멱등성 검사는 반드시 logical_key로 해야 링크 1이 링크 0의 완료를 본다
        #    (critic B-1: 안 그러면 전체 워크플로를 처음부터 다시 돈다).
        self.logical_key = logical_key or key
        self.command = command          # 노드에서 실행할 셸 명령 (문자열)
        self.nodes = int(nodes)
        self.cores_per_node = int(cores_per_node)
        self.wall_h = float(wall_h)
        self.partition = partition
        self.array = array              # None 또는 (start, end) 튜플
        self.gpus = int(gpus)
        self.job_dir = job_dir
        self.env = dict(env or {})
        # 🔴 계산 노드에서 실행할 `module load` 목록. 로그인 노드에서 도구를 찾아
        #    두고 계산 노드에서 module 을 안 부르면 조용히 실패한다.
        self.modules = list(modules or [])
        # PBS `-o`/`-e` 를 낼 것인가. 기본 False — 절대경로가 필터 훅에 걸린다.
        self.emit_stdio_lines = bool(emit_stdio_lines)

        self.exclusive = exclusive
        # 🔴 대부분의 학술·국가 HPC는 `--account=<project>` 를 **요구**한다.
        #    없으면 sbatch 가 전 제출을 거부하고 왕복 1회(3.5일)가 통째로 날아간다.
        #    `--dry-run` 은 소프트웨어 존재만 보므로 이것을 못 잡는다 →
        #    그래서 `sbatch --test-only` 사전검사를 함께 넣었다.
        self.account = account
        self.qos = qos
        self.reservation = reservation

    def module_block(self):
        """계산 노드에서 실행할 module 명령 블록. 없으면 빈 문자열.

        🔴 로그인 노드에서 Gaussian 을 찾아 놓고 계산 노드에서 `module load` 를
        안 부르면 **조용히 실패한다.** 실제 클러스터에서 P1/P5/P1b 가 전부 SKIP 된
        원인이 이 계열이다.
        """
        if not self.modules:
            return ""
        lines = ["# 사이트 모듈 (로그인 노드 탐지 결과를 계산 노드에서 재현한다)"]
        for m in self.modules:
            lines.append("module load %s 2>/dev/null || "
                         "echo '[sei] module load %s 실패 — 계속 진행'" % (m, m))
        return "\n".join(lines)

    @property
    def total_cores(self):
        return self.nodes * self.cores_per_node

    def wall_hms(self):
        total_s = int(round(self.wall_h * 3600))
        h, rem = divmod(total_s, 3600)
        m, s = divmod(rem, 60)
        return "%02d:%02d:%02d" % (h, m, s)


def detect(shell):
    """SLURM → PBS/Torque → 순수 셸 순으로 탐지 (§R2-6 D-1)."""
    if shell.which("sbatch") and shell.which("squeue"):
        return SLURM
    if shell.which("qsub"):
        return PBS
    return NONE


def detect_pbs_flavor(shell):
    """PBS Pro (select 구문) vs Torque (nodes=N:ppn=C 구문). [UNVERIFIED]"""
    for cmd in ("qstat --version", "pbsnodes --version"):
        res = shell.run(cmd, timeout_s=15)
        blob = (res.out + res.err).lower()
        if "pbspro" in blob or "pbs_version" in blob or "openpbs" in blob:
            return "pbspro"
        if "torque" in blob:
            return "torque"
    return "pbspro"


# --------------------------------------------------------------------------
# 스크립트 렌더링 (순수 함수 — 테스트 대상)
# --------------------------------------------------------------------------
def squeeze_directive_blanks(text):
    """지시어 블록(`#PBS`/`#SBATCH`) 안의 **빈 줄을 제거**한다.

    🔴 PBS 는 **첫 비지시어 줄에서 지시어 파싱을 멈춘다.** 빈 줄이 그 사이에 끼면
    뒤따르는 `#PBS` 줄이 통째로 무시될 수 있다. 우리는 선택적 지시어를 빈 문자열로
    치환하므로 빈 줄이 실제로 생긴다.
    [UNVERIFIED — 사용자 클러스터에서만 확인 가능]
    """
    out, in_header = [], True
    for line in text.splitlines():
        if in_header:
            if (line.startswith("#!") or line.startswith("#PBS")
                    or line.startswith("#SBATCH")):
                out.append(line)
                continue
            if not line.strip():
                continue                      # 헤더 안의 빈 줄은 버린다
            in_header = False
        out.append(line)
    return "\n".join(out) + "\n"


def render_script(template_text, spec, extra=None):
    """{{KEY}} 치환. 템플릿 파일(templates/*.tmpl)에서 읽어온 텍스트에 적용."""
    job_dir = spec.job_dir or "."
    subs = {
        "JOB_NAME": "sei_" + spec.key,
        "NODES": str(spec.nodes),
        "CORES_PER_NODE": str(spec.cores_per_node),
        "TOTAL_CORES": str(spec.total_cores),
        "WALL_HMS": spec.wall_hms(),
        "JOB_DIR": job_dir,
        "STDOUT": os.path.join(job_dir, spec.key + ".out"),
        "STDERR": os.path.join(job_dir, spec.key + ".err"),
        "PARTITION_LINE": "",
        "ACCOUNT_LINE": "",
        "QOS_LINE": "",
        "RESERVATION_LINE": "",
        "ARRAY_LINE": "",
        "GPU_LINE": "",
        # 🔴 PBS `-o`/`-e` 는 기본 **생략**이다. 절대경로가 공유 FS 밖이면 필터 훅이
        #    제출을 거부한다(사용자 정본 스크립트에도 두 줄이 없다).
        "STDOUT_LINE": "",
        "STDERR_LINE": "",
        "MODULE_LINES": "",
        "COMMAND": spec.command,
        "CMD_FILE": os.path.join(job_dir, spec.key + ".cmd.sh"),
        "KEY": spec.key,
        "LOGICAL_KEY": spec.logical_key,
        "ENV_EXPORTS": "\n".join('export %s="%s"' % (k, v)
                                 for k, v in sorted(spec.env.items())),
    }
    subs.update(extra or {})
    out = template_text
    for k, v in subs.items():
        out = out.replace("{{%s}}" % k, v)
    # 미치환 토큰이 남으면 렌더링 버그다. 조용히 넘기지 않는다.
    leftover = re.findall(r"\{\{[A-Z_]+\}\}", out)
    if leftover:
        raise ValueError("unsubstituted template tokens: %s" % sorted(set(leftover)))
    return out


class Adapter(object):
    name = NONE
    supports_dependency = False
    #: 사전검사가 부작용을 갖는가. PBS만 True (아래 PbsAdapter 참조).
    PRECHECK_HAS_SIDE_EFFECTS = False

    def __init__(self, shell, template_dir, store=None):
        self.shell = shell
        self.template_dir = template_dir
        self.store = store

    def _template(self, filename):
        with open(os.path.join(self.template_dir, filename)) as fh:
            return fh.read()

    def write_cmd_file(self, spec):
        """payload 명령을 **별도 파일**로 떨군다.

        이유: 잡 스크립트에 명령을 그대로 박으면 `A && B` 같은 명령이
        `sei_job_main A && B` 로 펼쳐져 B가 계측/마커 밖에서 실행된다
        (실제로 collector에서 이 버그가 났다). 파일로 분리하면 인용 문제가 사라진다.
        """
        path = os.path.join(makedirs(spec.job_dir or "."), spec.key + ".cmd.sh")
        with open(path, "w") as fh:
            fh.write("#!/bin/bash\n# sei_pilot payload command (%s)\nset -u\n%s\n"
                     % (spec.key, spec.command))
        os.chmod(path, 0o755)
        return path

    def write_script(self, spec, deps=None):
        raise NotImplementedError

    def submit(self, spec, deps=None):
        raise NotImplementedError

    def test_submit(self, spec):
        """실제 제출 없이 스케줄러 수용 여부만 확인한다. 기본은 '확인 불가'."""
        return SubmissionCheck(spec.key, None, "unsupported",
                               "이 백엔드는 사전 검사를 지원하지 않는다")

    def job_known(self, jobid):
        """[A-1e] 스케줄러가 이 jobid 를 **지금** 알고 있는가.

        True/False/None(확인 불가). qdel 등 외부 종료된 잡은 payload 가 마커를 못
        남기므로 submitted 마커만 남는다 — 그 상태를 마커만으로는 '진행 중'과 구분할
        수 없어서 스케줄러에 직접 묻는다. 🔴 판정은 하지 않는다: 자동 재제출 금지
        (lead 결정 사항), 탐지·보고까지만.
        """
        return None

    def submit_chain(self, spec, n_links, deps=None):
        """자기 연쇄 제출 (§R2-6 D-4).

        wall 상한 초과가 예상되는 잡은 afterany 체인을 **제출 시점에 미리** 건다.
        사용자의 2차 개입을 금지하기 위함. 각 링크는 동일 스크립트이며,
        payload가 자기 완료 마커를 보고 즉시 종료하므로 멱등하다.
        """
        ids = []
        prev = list(deps or [])
        for i in range(n_links):
            link = JobSpec(spec.key if i == 0 else "%s_c%d" % (spec.key, i),
                           spec.command, spec.nodes, spec.cores_per_node,
                           spec.wall_h, spec.partition, spec.array, spec.gpus,
                           spec.job_dir, spec.env, spec.exclusive,
                           logical_key=spec.logical_key, account=spec.account,
                           qos=spec.qos, reservation=spec.reservation)
            jid = self.submit(link, deps=prev)
            if jid is None:
                break
            ids.append(jid)
            prev = [jid]
        return ids


class _JobKnownMixin(object):
    """[A-1e] job_known 의 공용 구현 골격 — 각 백엔드의 조회 명령만 다르다."""

    def _job_query_args(self, jobid):
        raise NotImplementedError

    def job_known(self, jobid):
        if not jobid:
            return None
        res = self.shell.run(self._job_query_args(str(jobid)), timeout_s=30)
        if res.rc == 127 or res.timed_out:
            return None                    # 명령 자체가 없다/응답 없다 → 확인 불가
        if res.ok and (res.out or "").strip():
            return True
        return False


class SlurmAdapter(_JobKnownMixin, Adapter):
    name = SLURM
    supports_dependency = True

    def _job_query_args(self, jobid):
        return ["squeue", "-h", "-j", jobid]

    def write_script(self, spec, deps=None):
        self.write_cmd_file(spec)
        extra = {}
        if spec.partition:
            extra["PARTITION_LINE"] = "#SBATCH --partition=%s" % spec.partition
        if spec.account:
            extra["ACCOUNT_LINE"] = "#SBATCH --account=%s" % spec.account
        if spec.qos:
            extra["QOS_LINE"] = "#SBATCH --qos=%s" % spec.qos
        if spec.reservation:
            extra["RESERVATION_LINE"] = "#SBATCH --reservation=%s" % spec.reservation
        if spec.array:
            extra["ARRAY_LINE"] = "#SBATCH --array=%d-%d" % spec.array
        if spec.gpus:
            extra["GPU_LINE"] = "#SBATCH --gres=gpu:%d" % spec.gpus
        text = render_script(self._template("slurm.sh.tmpl"), spec, extra)
        path = os.path.join(makedirs(spec.job_dir), spec.key + ".sbatch")
        with open(path, "w") as fh:
            fh.write(text)
        os.chmod(path, 0o755)
        return path

    def submit_args(self, script_path, deps=None):
        args = ["sbatch", "--parsable"]
        if deps:
            args.append("--dependency=afterany:" + ":".join(str(d) for d in deps))
        args.append(script_path)
        return args

    def submit(self, spec, deps=None):
        path = self.write_script(spec, deps)
        res = self.shell.run(self.submit_args(path, deps), timeout_s=120)
        if not res.ok:
            return None
        return parse_slurm_jobid(res.out)

    def test_submit(self, spec):
        """🔴 `sbatch --test-only` — **부작용이 전혀 없다.** 스케줄러가 거부 사유를
        그대로 알려주므로, 계정·파티션·wall 문제를 제출 전에 잡는다."""
        path = self.write_script(spec)
        res = self.shell.run(["sbatch", "--test-only", path], timeout_s=60)
        blob = ((res.out or "") + "\n" + (res.err or "")).strip()
        if res.rc == 127:
            return SubmissionCheck(spec.key, None, "sbatch --test-only",
                                   "sbatch 를 찾지 못했다")
        if res.ok:
            return SubmissionCheck(spec.key, True, "sbatch --test-only", blob)
        return SubmissionCheck(spec.key, False, "sbatch --test-only", blob,
                               _remedy_for(blob))


class PbsAdapter(_JobKnownMixin, Adapter):
    name = PBS
    supports_dependency = True

    def __init__(self, shell, template_dir, store=None, flavor="pbspro"):
        Adapter.__init__(self, shell, template_dir, store)
        self.flavor = flavor

    def write_script(self, spec, deps=None):
        self.write_cmd_file(spec)
        # [UNVERIFIED] PBS Pro의 select 구문과 Torque의 nodes/ppn 구문이 다르다.
        if self.flavor == "torque":
            resource = "#PBS -l nodes=%d:ppn=%d" % (spec.nodes, spec.cores_per_node)
        else:
            resource = "#PBS -l select=%d:ncpus=%d:mpiprocs=%d" % (
                spec.nodes, spec.cores_per_node, spec.cores_per_node)
        extra = {"RESOURCE_LINE": resource}
        # 🔴 `-o`/`-e` 를 절대경로로 주면 그 경로가 공유 FS 밖이거나 없을 때 필터 훅이
        #    제출을 거부한다. 사용자 정본 스크립트에는 두 줄이 아예 없다.
        #    ⇒ 기본은 **생략**하고, 필요할 때만 $PBS_O_WORKDIR 기준 상대경로로 준다.
        #    [UNVERIFIED — 사용자 클러스터에서만 확인 가능]
        if spec.emit_stdio_lines:
            # $PBS_O_WORKDIR 기준 **상대경로**로만 낸다. 절대경로는 훅에 걸린다.
            extra["STDOUT_LINE"] = "#PBS -o %s.out" % spec.key
            extra["STDERR_LINE"] = "#PBS -e %s.err" % spec.key
        # 계산 노드에서 실제로 module 을 로드한다. 로그인 노드에서 찾아 두고
        # 계산 노드에서 안 부르면 **조용히 실패한다**(Gaussian 미탐지의 전형).
        extra["MODULE_LINES"] = spec.module_block()
        if spec.partition:
            extra["PARTITION_LINE"] = "#PBS -q %s" % spec.partition
        if spec.account:
            extra["ACCOUNT_LINE"] = "#PBS -A %s" % spec.account
        if spec.qos:
            extra["QOS_LINE"] = "#PBS -l qos=%s" % spec.qos
        if spec.array:
            extra["ARRAY_LINE"] = "#PBS -J %d-%d" % spec.array
        if spec.gpus:
            extra["GPU_LINE"] = "#PBS -l ngpus=%d" % spec.gpus
        text = squeeze_directive_blanks(
            render_script(self._template("pbs.sh.tmpl"), spec, extra))
        path = os.path.join(makedirs(spec.job_dir), spec.key + ".qsub")
        with open(path, "w") as fh:
            fh.write(text)
        os.chmod(path, 0o755)
        return path

    def submit_args(self, script_path, deps=None):
        args = ["qsub"]
        if deps:
            args += ["-W", "depend=afterany:" + ":".join(str(d) for d in deps)]
        args.append(script_path)
        return args

    def submit(self, spec, deps=None):
        path = self.write_script(spec, deps)
        res = self.shell.run(self.submit_args(path, deps), timeout_s=120)
        if not res.ok:
            return None
        return parse_pbs_jobid(res.out)

    def _job_query_args(self, jobid):
        # `qstat <id>` 는 큐/실행 중인 잡만 안다. 끝난 잡은 모른다 — 우리 용법에는
        # 그게 맞다: "지금 스케줄러에 있는가"가 질문이다 (외부 종료 탐지, A-1e).
        return ["qstat", jobid]

    #: 🔴 PBS에는 `sbatch --test-only` 같은 **완전 무부작용** 검사가 없다.
    #: 우리가 쓰는 `qsub -h` 는 **진짜 잡을 보류 상태로 제출**한다(자원은 안 쓰지만
    #: 큐 카운터에 잡히고, 삭제가 실패하면 남는다). 그래서:
    #:   - 무엇을 하는지 결과에 명시한다 (조용히 "통과"라고 하지 않는다)
    #:   - --no-precheck 로 끌 수 있다
    #:   - 삭제 실패 시 잡 ID를 큰 소리로 알린다
    PRECHECK_HAS_SIDE_EFFECTS = True

    def test_submit(self, spec):
        """PBS: 보류(-h) 제출 후 즉시 삭제. **완전 무부작용이 아니다.**"""
        path = self.write_script(spec)
        res = self.shell.run(["qsub", "-h", path], timeout_s=60)
        blob = ((res.out or "") + "\n" + (res.err or "")).strip()
        if res.rc == 127:
            return SubmissionCheck(spec.key, None, "qsub -h", "qsub 를 찾지 못했다")
        if not res.ok:
            return SubmissionCheck(spec.key, False, "qsub -h", blob, _remedy_for(blob))
        jid = parse_pbs_jobid(res.out)
        cleanup = self.shell.run(["qdel", str(jid)], timeout_s=60) if jid else None
        msg = ("보류 제출 %s 수용됨 (⚠ 이 방식은 실제 잡을 보류로 제출했다가 삭제한다 "
               "— sbatch --test-only 처럼 완전 무부작용은 아니다)" % jid)
        if cleanup is not None and not cleanup.ok:
            msg += (" — 🔴 삭제 실패! 보류 상태로 남아 있다. `qdel %s` 를 직접 실행하라"
                    % jid)
        return SubmissionCheck(spec.key, True, "qsub -h + qdel", msg)


class LocalAdapter(Adapter):
    """스케줄러가 없을 때. nohup 백그라운드 워커 1개가 큐를 **순차** 실행한다.

    의존성은 '먼저 제출된 것이 먼저 실행된다'로 자동 충족된다
    (collector를 마지막에 제출하므로 afterany와 동등한 효과).
    동시성이 없으므로 many-task 처리량 프로브는 의미가 없어 자동 생략된다.
    """
    name = NONE
    supports_dependency = False

    def __init__(self, shell, template_dir, store=None, workdir=None):
        Adapter.__init__(self, shell, template_dir, store)
        self.workdir = workdir or "."
        self.queue_path = os.path.join(self.workdir, "state", "local_queue")
        self._n = 0

    def write_script(self, spec, deps=None):
        self.write_cmd_file(spec)
        text = render_script(self._template("local.sh.tmpl"), spec, {})
        path = os.path.join(makedirs(spec.job_dir), spec.key + ".sh")
        with open(path, "w") as fh:
            fh.write(text)
        os.chmod(path, 0o755)
        return path

    def submit(self, spec, deps=None):
        path = self.write_script(spec, deps)
        makedirs(os.path.dirname(self.queue_path))
        with open(self.queue_path, "a") as fh:
            fh.write(path + "\n")
        self._n += 1
        return "local-%d" % self._n

    def start_worker(self):
        worker = os.path.join(self.workdir, "state", "local_worker.sh")
        with open(worker, "w") as fh:
            fh.write(
                "#!/bin/bash\n"
                "# 순차 실행 워커. 스케줄러가 없는 환경의 fallback.\n"
                "set -u\n"
                "QUEUE='%s'\n"
                "while IFS= read -r script; do\n"
                "  [ -x \"$script\" ] || continue\n"
                "  \"$script\" >> \"${script%%.sh}.out\" 2>> \"${script%%.sh}.err\"\n"
                "done < \"$QUEUE\"\n" % self.queue_path)
        os.chmod(worker, 0o755)
        return self.shell.run("nohup %s > /dev/null 2>&1 &" % worker, timeout_s=10)


#: 🔴 스케줄러가 실제로 받아줄지 **제출 없이** 확인한다.
#: dry-run 이 소프트웨어 존재만 보고 스케줄러 수용 여부를 안 보면,
#: "계정 없음"으로 전 항목이 거부되는 실패를 왕복 1회 뒤에야 알게 된다.
ACCOUNT_ERROR_HINTS = ("account", "Invalid account", "association",
                       "AccountingStorageEnforce")
PARTITION_ERROR_HINTS = ("partition", "Invalid partition", "PartitionConfig")


class SubmissionCheck(object):
    """`sbatch --test-only` 등의 결과. 예외를 던지지 않는다."""

    def __init__(self, key, ok, method, message="", remedy=None):
        self.key = key
        self.ok = ok            # True 수용 / False 거부 / None 확인 불가
        self.method = method
        self.message = (message or "").strip()
        self.remedy = remedy

    def to_dict(self):
        """🔴 **메시지를 자르지 않는다.**

        예전에는 `self.message[:400]` 이었다. 화면 출력(`format_feasibility`)의
        66자 컷은 고쳤는데 **실제 파이프라인이 통과하는 이 지점**은 그대로여서,
        535자짜리 훅 메시지의 뒤 135자가 소실됐다(critic2 재현).
        스케줄러 거부 사유는 **뒤쪽에 있는 경우가 많다** — 그게 이 라운드의 요점이다.

        회신 JSON 크기가 걱정되면 자르지 말고 `message_bytes` 로 크기를 보라.
        """
        return {"key": self.key, "ok": self.ok, "method": self.method,
                "message": self.message, "message_bytes": len(self.message),
                "remedy": self.remedy}


def _remedy_for(text):
    low = (text or "").lower()
    if any(h.lower() in low for h in ACCOUNT_ERROR_HINTS):
        return ("계정(account)이 필요하다. `sacctmgr -nP show assoc user=$USER "
                "format=Account,Partition,QOS` 로 확인한 뒤 "
                "`./run.sh --account=<이름>` 으로 다시 실행하라.")
    if any(h.lower() in low for h in PARTITION_ERROR_HINTS):
        return ("파티션이 잘못됐거나 제출 권한이 없다. `sinfo -s` 로 확인한 뒤 "
                "`./run.sh --partition=<이름>` 으로 다시 실행하라.")
    if "time" in low or "walltime" in low:
        return "wall-time 이 파티션 상한을 넘는다. `--max-wall-h` 를 낮춰라."
    return None


def parse_slurm_jobid(text):
    """`sbatch --parsable` → '12345' 또는 '12345;cluster'.
    --parsable 미지원 구버전 → 'Submitted batch job 12345'."""
    text = (text or "").strip()
    if not text:
        return None
    m = re.search(r"Submitted batch job (\d+)", text)
    if m:
        return m.group(1)
    first = text.splitlines()[0].strip()
    m = re.match(r"^(\d+)(;.*)?$", first)
    if m:
        return m.group(1)
    return None


def parse_pbs_jobid(text):
    """qsub → '12345.headnode' 또는 '12345[].headnode'. 전체 문자열을 id로 쓴다."""
    text = (text or "").strip()
    if not text:
        return None
    first = text.splitlines()[0].strip()
    return first or None


def make_adapter(kind, shell, template_dir, workdir=None, store=None):
    if kind == SLURM:
        return SlurmAdapter(shell, template_dir, store)
    if kind == PBS:
        return PbsAdapter(shell, template_dir, store, flavor=detect_pbs_flavor(shell))
    return LocalAdapter(shell, template_dir, store, workdir=workdir)
