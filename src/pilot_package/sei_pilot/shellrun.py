"""외부 명령 실행 경계 — **이 프로젝트에서 subprocess를 부르는 유일한 모듈.**

이유: 우리는 SLURM/PBS/클러스터가 있는 환경에서 이 코드를 실행 검증할 수 없다(ADR-004).
따라서 스케줄러 호출과 판정 로직이 뒤엉키면 아무것도 검증할 수 없다.
모든 외부 호출을 Shell 객체 하나로 모으고, 테스트는 FakeShell을 주입한다.
"""

import os
import shutil
import subprocess
import time


class CmdResult(object):
    __slots__ = ("cmd", "rc", "out", "err", "duration_s", "timed_out")

    def __init__(self, cmd, rc, out, err, duration_s=0.0, timed_out=False):
        self.cmd = cmd
        self.rc = rc
        self.out = out
        self.err = err
        self.duration_s = duration_s
        self.timed_out = timed_out

    @property
    def ok(self):
        return self.rc == 0 and not self.timed_out

    def __repr__(self):
        return "CmdResult(rc=%r, cmd=%r)" % (self.rc, self.cmd)


class Shell(object):
    """실제 subprocess 실행기."""

    def __init__(self, default_timeout_s=60, cwd=None, env=None):
        self.default_timeout_s = default_timeout_s
        self.cwd = cwd
        self.env = env
        self.log = []          # 실행 이력 (provenance/디버깅용)

    def run(self, cmd, timeout_s=None, cwd=None, check=False, input_text=None):
        """cmd: 리스트 또는 문자열(문자열이면 shell=True).

        타임아웃/미설치 명령은 예외가 아니라 rc!=0 인 CmdResult로 돌려준다.
        (프로브 대상 명령의 절반은 그 클러스터에 없는 것이 정상이다.)
        """
        timeout_s = self.default_timeout_s if timeout_s is None else timeout_s
        shell = isinstance(cmd, str)
        t0 = time.time()
        try:
            p = subprocess.Popen(
                cmd, shell=shell, cwd=cwd or self.cwd, env=self.env,
                stdin=subprocess.PIPE if input_text is not None else None,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            try:
                out, err = p.communicate(input=input_text, timeout=timeout_s)
                res = CmdResult(cmd, p.returncode, out or "", err or "",
                                time.time() - t0, False)
            except subprocess.TimeoutExpired:
                p.kill()
                out, err = p.communicate()
                res = CmdResult(cmd, 124, out or "", err or "",
                                time.time() - t0, True)
        except (OSError, ValueError) as exc:
            res = CmdResult(cmd, 127, "", "%s: %s" % (type(exc).__name__, exc),
                            time.time() - t0, False)
        self.log.append({"cmd": cmd, "rc": res.rc, "duration_s": round(res.duration_s, 3)})
        if check and not res.ok:
            raise RuntimeError("command failed: %r rc=%s err=%s" % (cmd, res.rc, res.err[:400]))
        return res

    def which(self, name):
        return shutil.which(name)

    def exists(self, path):
        return os.path.exists(path)

    def read_text(self, path, max_bytes=200000):
        try:
            with open(path, "r", errors="replace") as fh:
                return fh.read(max_bytes)
        except OSError:
            return None


class FakeShell(Shell):
    """테스트용. 명령 prefix → (rc, stdout, stderr) 매핑.

    매칭 규칙: 등록된 key 중 명령 문자열의 prefix인 것 가운데 **가장 긴 것**.
    등록되지 않은 명령은 rc=127 (미설치)로 취급한다 — 실제 클러스터에서 가장 흔한 경우.
    """

    def __init__(self, responses=None, which_map=None, files=None, paths=None):
        Shell.__init__(self)
        self.responses = dict(responses or {})
        self.which_map = dict(which_map or {})
        self.files = dict(files or {})
        self.paths = set(paths or [])
        self.submitted = []

    @staticmethod
    def _key(cmd):
        return cmd if isinstance(cmd, str) else " ".join(cmd)

    def run(self, cmd, timeout_s=None, cwd=None, check=False, input_text=None):
        key = self._key(cmd)
        best = None
        for pref in self.responses:
            if key.startswith(pref) and (best is None or len(pref) > len(best)):
                best = pref
        if best is None:
            res = CmdResult(cmd, 127, "", "command not found (FakeShell)", 0.0, False)
        else:
            spec = self.responses[best]
            if callable(spec):
                spec = spec(key)
            rc, out, err = spec
            res = CmdResult(cmd, rc, out, err, 0.0, False)
        self.log.append({"cmd": key, "rc": res.rc, "duration_s": 0.0})
        if check and not res.ok:
            raise RuntimeError("command failed: %r" % (key,))
        return res

    def which(self, name):
        return self.which_map.get(name)

    def exists(self, path):
        return path in self.paths or path in self.files

    def read_text(self, path, max_bytes=200000):
        return self.files.get(path)
