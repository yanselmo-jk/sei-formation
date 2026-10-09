"""멱등·재개 상태 저장소.

HPC 잡은 wall-time에 잘리고 노드는 죽는다. `./run.sh` 재실행이 **이미 끝난 것을
건너뛰고 이어서 하는 것**이 기본 동작이어야 한다 (§R2-6 D-5).

구현: 공유 파일시스템 위의 마커 파일. 데몬 없음, DB 없음(§R2-8 Case B).
쓰기는 전부 tmp 파일 + os.replace 로 원자적. 잡이 중간에 죽어도 반쪽 JSON이 남지 않는다.

디렉터리 배치:
  <workdir>/
    state/            마커 (<key>.done.json, <key>.failed.json, <key>.submitted.json)
    jobs/<key>/       잡 스크립트, stdout/stderr, 잡이 쓰는 결과 파일
    results/          최종 sei_probe_report.json
"""

import errno
import hashlib
import json
import os
import re
import time


def _atomic_write(path, text):
    d = os.path.dirname(path)
    if d:
        makedirs(d)
    tmp = path + ".tmp.%d" % os.getpid()
    with open(tmp, "w") as fh:
        fh.write(text)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


#: Plan-entry fields that define WHAT a submission computes. Anything outside this
#: tuple (account string, partition, pkg-root path, wall rounding) changes WHERE/HOW
#: it runs, not what it produces, so it must not invalidate a done marker.
#: 🔴 NOT here, on purpose (critic11 / engineer9, 2026-08-21): `cores_per_node` is a LIVE
#: cluster probe (node core-count mode) for whole-node items and shifts with the visible
#: node pool; `chain_links` is wall-cap rounding. Either would mark finished 384-5,328 core-h
#: items "stale" with nothing about the chemistry changed.
#: `cores_per_task` (the Item's OWN declaration, None or int) is in: for P6 it IS the
#: measurement (1/16/64 threads). `cores_per_node` (probed) is out -- see above.
SPEC_DIGEST_FIELDS = ("key", "payload", "extra_env", "nodes", "array", "gpus", "cores_per_task")

#: Job-environment keys that select PHYSICS but are set by the harness, not per item
#: (`--level g1|g2` -> SEI_QC_LEVEL; the G16 build actually loaded). 🔴 engineer9: without
#: these, `./run.sh --level g2` against a workdir of g1 done markers returns `match` on every
#: item, skips everything, and the report claims g2 results that are g1 -- a FALSE MATCH that
#: corrupts an answer, worse than a false stale that wastes core-h.
PHYSICS_ENV_KEYS = ("SEI_QC_LEVEL", "SEI_QC_MODULE", "SEI_QC_LOGIN_PATH")


def physics_env(job_env):
    return dict((k, job_env[k]) for k in PHYSICS_ENV_KEYS if job_env.get(k))


def spec_digest(entry, physics=None):
    """Short sha256 of the plan entry's computation-defining fields.

    🔴 [2026-08-21, EpsInf bracket round] `endpoint_prep_reactant` gained
    `SEI_QC_EPSINF=1.0` in `extra_env`, but its `done` marker from the pre-fix round was
    still on disk, so `cmd_submit` skipped it as "이미 완료" and the EpsInf=1.0 arm of the
    bracket was never run. A done marker certifies that *some* computation finished,
    not that the computation the CURRENT plan describes did. This digest is stored in the
    `submitted` marker and compared before the skip — same shape as `sei_stage`'s
    pkg_fingerprint check in payload/common.sh, one level up.
    """
    sub = {k: entry.get(k) for k in SPEC_DIGEST_FIELDS}
    sub["_physics_env"] = dict(physics or {})
    blob = json.dumps(sub, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def makedirs(path):
    try:
        os.makedirs(path)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise
    return path


class Store(object):
    def __init__(self, workdir):
        self.workdir = os.path.abspath(workdir)
        self.state_dir = os.path.join(self.workdir, "state")
        self.jobs_dir = os.path.join(self.workdir, "jobs")
        self.results_dir = os.path.join(self.workdir, "results")
        for d in (self.state_dir, self.jobs_dir, self.results_dir):
            makedirs(d)

    # --- 경로 ---
    def job_dir(self, key):
        return makedirs(os.path.join(self.jobs_dir, key))

    def _marker(self, key, kind):
        return os.path.join(self.state_dir, "%s.%s.json" % (key, kind))

    # --- array 태스크 마커 ---
    # 🔴 [array 분기 사고] common.sh 는 array 태스크의 논리 키를 `<key>.t<N>` 으로
    #    가른다(같은 키를 공유하면 먼저 끝난 태스크의 done 마커를 보고 나머지가
    #    전부 건너뛴다 — 태스크 유실). 그래서 항목 수준 상태는 태스크 마커를
    #    **집계**해야 한다. 집계 규칙:
    #      done   = 제출된 n_tasks 전부에 done 마커가 있다
    #      failed = 전 태스크가 종결(done|failed) 마커를 남겼고 그중 실패가 있다
    #               (⚠ 아직 마커 없는 태스크가 있는 동안 failed 로 판정하면 cli 가
    #                재제출해 **돌고 있는 태스크와 이중 실행**된다 — 그 병 그대로다)
    def task_marker_states(self, key):
        """{tid(int): "done"|"failed"} — done 이 failed 를 이긴다(재시도 성공)."""
        pat = re.compile(r"^%s\.t(\d+)\.(done|failed)\.json$" % re.escape(key))
        out = {}
        try:
            names = os.listdir(self.state_dir)
        except OSError:
            return out
        for fn in sorted(names):
            m = pat.match(fn)
            if not m:
                continue
            tid, kind = int(m.group(1)), m.group(2)
            if kind == "done" or tid not in out:
                out[tid] = kind
        return out

    def expected_task_count(self, key):
        """제출 마커의 n_tasks (array 가 아니면 None)."""
        sub = self.read_marker(key, "submitted") or {}
        return (sub.get("payload") or {}).get("n_tasks")

    # --- 마커 ---
    def is_done(self, key):
        if os.path.exists(self._marker(key, "done")):
            return True
        n = self.expected_task_count(key)
        if not n:
            return False
        states = self.task_marker_states(key)
        return len([t for t, k in states.items() if k == "done"]) >= int(n)

    def done_spec_status(self, key, digest, physics_keys=None):
        """("match"|"stale"|"unknown", stored_digest) for a done item.

        `physics_keys`: the PHYSICS_ENV_KEYS actually PRESENT this invocation. The submitted
        marker stores the set that was present when the digest was written; if the two sets
        differ, a digest mismatch is `unknown`, never `stale`. 🔴 engineer9: an ABSENT
        detection must never look like a CHANGED computation -- `g16` missing from the login
        PATH on one invocation would otherwise flip every item's digest at once and
        auto-resubmit the whole workdir. Comparing SETS (not requiring all keys) keeps the
        mechanism alive on clusters that legitimately have no module system.

        stale   = same key set, digest differs -> the done marker is a DIFFERENT computation.
        unknown = marker predates digests (no field), or the detected key set changed.
        """
        sub = (self.read_marker(key, "submitted") or {}).get("payload") or {}
        old = sub.get("spec_digest")
        if not old:
            return "unknown", None
        if old == digest:
            return "match", old
        stored_keys = sub.get("physics_keys")
        if physics_keys is not None and stored_keys is not None \
                and sorted(stored_keys) != sorted(physics_keys):
            return "unknown", old
        return "stale", old

    def outcome_payload(self, key, kind="done"):
        """The marker payload the retry policy reads -- base marker, or for ARRAY items an
        AGGREGATE of the per-task markers (`<key>.tN.<kind>.json`).

        🔴 [critic11, 2026-08-21] nothing writes a base `<key>.done.json` for arrays (bash
        `sei_write_marker` writes per-task markers under the task logical key), so reading
        the base marker alone returned `{}` -> outcome `absent` -> every array crash read as
        "done, nothing to see". Aggregation mirrors `is_done`/`is_failed`.
        Returns {"outcome", "cause_class", "pkg_fingerprint", "tasks": {tid: cause}}.
        """
        from . import outcome as outcome_mod
        base = (self.read_marker(key, kind) or {}).get("payload") or {}
        if base or not self.expected_task_count(key):
            return base
        tasks, outcomes, fps = {}, [], set()
        for tid, k in sorted(self.task_marker_states(key).items()):
            if k != kind:
                continue
            pl = (self.read_marker("%s.t%d" % (key, tid), kind) or {}).get("payload") or {}
            c = pl.get("cause_class") or outcome_mod.cause_class(pl.get("outcome"))
            tasks[tid] = c
            outcomes.append("t%d=%s" % (tid, pl.get("outcome")))
            if pl.get("pkg_fingerprint"):
                fps.add(pl["pkg_fingerprint"])
        if not tasks:
            return {}
        return {"outcome": ",".join(outcomes),
                "cause_class": outcome_mod.aggregate_cause(tasks.values()),
                "pkg_fingerprint": fps.pop() if len(fps) == 1 else None,
                "tasks": tasks}

    def is_submitted(self, key):
        return os.path.exists(self._marker(key, "submitted"))

    def is_failed(self, key):
        if os.path.exists(self._marker(key, "failed")):
            return True
        n = self.expected_task_count(key)
        if not n:
            return False
        states = self.task_marker_states(key)
        # 전 태스크 종결 + 실패 존재일 때만 (위 docstring 의 이중 실행 경고 참조)
        return (len(states) >= int(n)
                and any(k == "failed" for k in states.values()))

    def clear_failed(self, key):
        """실패 마커를 지운다. **재제출 직전에** 부른다.

        🔴 안 지우면: 재제출 후 잡이 아직 도는 중에 `./run.sh` 를 또 치면 `failed` 가
        남아 있어 **또 제출된다**(이중 제출). 마커가 상태의 유일한 근거이므로
        상태를 바꿀 때 함께 갱신해야 한다.
        """
        removed = False
        try:
            os.remove(self._marker(key, "failed"))
            removed = True
        except OSError:
            pass
        # array 태스크의 실패 마커도 함께 지운다 — 안 지우면 재제출 후 잡이 도는
        # 중에 ./run.sh 를 또 칠 때 is_failed 가 계속 참이라 **또 제출된다**
        # (단일 잡에서 base 마커를 지우는 이유와 정확히 같은 이유).
        for tid, kind in self.task_marker_states(key).items():
            if kind == "failed":
                self._unlink(self._marker("%s.t%d" % (key, tid), "failed"))
                removed = True
        return removed

    def reset_item(self, key, archive_job_dir=False):
        """[A-1e] 항목 하나를 '안 돈 것'으로 되돌린다 — **삭제가 아니라 이름 변경**.

        done/failed/submitted + 태스크 마커(<key>.tN.*) 전부를 `<이름>.reset.<epoch>`
        로 옆으로 치운다. 🔴 이 경로가 존재하는 이유: done 마커는 `--force` 로도
        뚫리지 않는데(성공한 항목의 실수 재실행 = core-h 재소모 사고), 위조 done
        (rc=0 으로 빠져나간 array 태스크가 찍은 것)에 막힌 항목을 사용자가 마커 파일을
        손으로 지우는 것 말고는 되살릴 방법이 없었다.
        ⚠ jobs/<key>/stages/ 의 단계 체크포인트는 건드리지 않는다 — 건강한 재개는
        공짜여야 하고, 다른 판(build)의 오염 마커는 fingerprint 불일치가 걸러낸다.
        `archive_job_dir=True` (자동 재제출 경로: spec 이 바뀌었거나 outcome 이 plumbing
        실패): jobs/<key>/ 전체를 `jobs/<key>.reset.<epoch>` 로 옆으로 치운다 — 이전
        실행이 **유일한 물리적 증거**일 수 있고(§39.80 의 분석은 그 디렉터리 위에 서
        있다), 다른 spec 아래 만들어진 stage 체크포인트를 새 spec 이 승계해서도 안 된다.
        """
        moved = []
        ts = int(time.time())
        pat = re.compile(r"^%s(\.t\d+)?\.(done|failed|submitted)\.json$"
                         % re.escape(key))
        try:
            names = sorted(os.listdir(self.state_dir))
        except OSError:
            return moved
        for fn in names:
            if not pat.match(fn):
                continue
            src = os.path.join(self.state_dir, fn)
            dst = "%s.reset.%d" % (src, ts)
            try:
                os.replace(src, dst)
                moved.append(fn)
            except OSError:
                pass
        if archive_job_dir:
            jd = os.path.join(self.jobs_dir, key)
            if os.path.isdir(jd):
                try:
                    os.replace(jd, "%s.reset.%d" % (jd, ts))
                    moved.append("jobs/%s/" % key)
                except OSError:
                    pass
        return moved

    def mark_done(self, key, payload=None):
        rec = {"key": key, "status": "done", "epoch": int(time.time()),
               "payload": payload or {}}
        _atomic_write(self._marker(key, "done"), json.dumps(rec, indent=1, sort_keys=True))
        # done 이 찍히면 failed 마커는 무의미하므로 제거 (재시도 성공 케이스)
        self._unlink(self._marker(key, "failed"))
        return rec

    def mark_submitted(self, key, payload=None):
        rec = {"key": key, "status": "submitted", "epoch": int(time.time()),
               "payload": payload or {}}
        _atomic_write(self._marker(key, "submitted"), json.dumps(rec, indent=1, sort_keys=True))
        return rec

    def mark_failed(self, key, reason, detail=None, log_excerpt=None, severity="error"):
        """실패는 예외가 아니라 데이터다. 삼키지 말고 분류해서 기록한다."""
        rec = {"key": key, "status": "failed", "epoch": int(time.time()),
               "reason": reason, "detail": detail,
               "log_excerpt": (log_excerpt or "")[-2000:], "severity": severity}
        _atomic_write(self._marker(key, "failed"), json.dumps(rec, indent=1, sort_keys=True))
        return rec

    def read_marker(self, key, kind):
        path = self._marker(key, kind)
        if not os.path.exists(path):
            return None
        try:
            with open(path) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def all_failures(self):
        out = []
        for fn in sorted(os.listdir(self.state_dir)):
            if fn.endswith(".failed.json"):
                try:
                    with open(os.path.join(self.state_dir, fn)) as fh:
                        out.append(json.load(fh))
                except (OSError, ValueError):
                    pass
        return out

    @staticmethod
    def _unlink(path):
        try:
            os.unlink(path)
        except OSError:
            pass

    # --- 실행 횟수 (재개 카운터) ---
    def bump_run_counter(self):
        path = os.path.join(self.state_dir, "run_count")
        n = 0
        try:
            with open(path) as fh:
                n = int(fh.read().strip() or "0")
        except (OSError, ValueError):
            n = 0
        n += 1
        _atomic_write(path, str(n))
        return n

    @property
    def run_count(self):
        try:
            with open(os.path.join(self.state_dir, "run_count")) as fh:
                return int(fh.read().strip() or "0")
        except (OSError, ValueError):
            return 0

    # --- 잡이 남긴 구조화 결과 읽기 ---
    def read_job_json(self, key, filename):
        path = os.path.join(self.jobs_dir, key, filename)
        try:
            with open(path) as fh:
                return json.load(fh)
        except (OSError, ValueError):
            return None

    def write_result(self, filename, obj):
        path = os.path.join(self.results_dir, filename)
        _atomic_write(path, json.dumps(obj, indent=2, sort_keys=False, default=str))
        return path

    def tail_log(self, key, n_bytes=2000):
        """잡 stdout/stderr 꼬리. failures[].log_excerpt 용."""
        chunks = []
        jd = os.path.join(self.jobs_dir, key)
        if not os.path.isdir(jd):
            return ""
        for fn in sorted(os.listdir(jd)):
            if fn.endswith((".out", ".err", ".log")):
                try:
                    with open(os.path.join(jd, fn), "r", errors="replace") as fh:
                        data = fh.read()
                    if data.strip():
                        chunks.append("--- %s ---\n%s" % (fn, data[-n_bytes:]))
                except OSError:
                    pass
        return "\n".join(chunks)[-(n_bytes * 2):]


def claim(path):
    """원자적 claim (§R2-8 Case B 파일큐 규약).

    같은 태스크를 두 워커가 동시에 집는 것을 막는다. O_CREAT|O_EXCL 사용.
    성공 시 True, 이미 누가 집었으면 False.
    """
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            return False
        raise
    with os.fdopen(fd, "w") as fh:
        fh.write("%d %d\n" % (os.getpid(), int(time.time())))
    return True
