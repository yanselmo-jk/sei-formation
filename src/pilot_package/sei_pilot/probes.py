"""many-task 처리량 프로브 + 큐 대기 프로브의 **분석**부.

engineer 원문(§R2-6): "합쳐서 ~4 node-h면 끝나는데 이 둘이 duty cycle과 왕복 모델을
실측으로 바꿔준다. 비용 대비 정보량이 이 패키지에서 가장 높다. 절대 빼지 마라."

측정 방식이 **스케줄러 비의존**이라는 점이 핵심:
  * 제출 시각은 우리가 로컬에서 기록한다 (submitted.json)
  * 시작 시각은 **잡이 노드에서 직접 기록한다** (started.json, common.sh)
  * 종료 시각은 완료 마커에 있다
⇒ sacct/qstat 파싱이 전혀 필요 없다. 사이트별 회계 설정 차이에 영향받지 않는다.
"""


def throughput_metrics(submitted, started, finished, n_submitted_attempts=None,
                       accepted=None):
    """
    submitted: [epoch, ...]  (우리가 제출한 시각들)
    started:   [epoch, ...]  (노드가 기록한 시작 시각들)
    finished:  [epoch, ...]  (완료 마커의 종료 시각들)
    """
    submitted = sorted(float(x) for x in (submitted or []))
    started = sorted(float(x) for x in (started or []))
    finished = sorted(float(x) for x in (finished or []))
    n_sub = n_submitted_attempts if n_submitted_attempts is not None else len(submitted)
    acc = accepted if accepted is not None else len(submitted)

    out = {
        "jobs_submitted": n_sub,
        "accepted": acc,
        "rejected": max(0, n_sub - acc),
        "jobs_started": len(started),
        "jobs_finished": len(finished),
        "start_rate_per_min": None,
        "submit_rate_per_min": None,
        "max_concurrent_observed": None,
        "first_start_delay_s": None,
        "all_done_wall_s": None,
    }
    if submitted and len(submitted) > 1:
        span = submitted[-1] - submitted[0]
        out["submit_rate_per_min"] = round(len(submitted) / (span / 60.0), 2) \
            if span > 0 else None
    if started:
        span = started[-1] - started[0]
        # span=0 (전부 동시 시작) 이면 '분당 시작률'은 하한만 말할 수 있다.
        out["start_rate_per_min"] = (round(len(started) / (span / 60.0), 2)
                                     if span > 0 else float(len(started)))
        out["start_rate_is_lower_bound"] = (span == 0)
        if submitted:
            out["first_start_delay_s"] = round(started[0] - submitted[0], 1)
    if finished and submitted:
        out["all_done_wall_s"] = round(finished[-1] - submitted[0], 1)
    out["max_concurrent_observed"] = max_concurrent(started, finished)
    return out


def max_concurrent(starts, ends):
    """스윕 라인. 동시 실행 최대치 = 실효 동시성 상한의 **하한 관측치**.

    주의: 잡 수(200)가 상한보다 적으면 이 값은 클러스터 상한이 아니라 우리 제출량이다.
    그 구분을 호출자가 하도록 값만 돌려준다.
    """
    if not starts:
        return None
    events = [(float(t), 1) for t in starts] + [(float(t), -1) for t in (ends or [])]
    # 같은 시각이면 종료(-1)를 먼저 처리해 과대평가를 막는다.
    events.sort(key=lambda x: (x[0], x[1]))
    cur = mx = 0
    for _, d in events:
        cur += d
        mx = max(mx, cur)
    return mx


#: `hostname` 이 실패했을 때 payload 가 적는 값. 노드 이름이 아니므로 **세지 않는다.**
UNKNOWN_HOST = "unknown"


def host_metrics(hosts, n_tasks=None):
    """array task 들이 기록한 hostname → **동시 점유 노드 수의 실측 하한.**

    🔴 왜 이게 있는가: 이 값들은 **원래 측정돼 있었다.** `probe_throughput.sh` 가 task 마다
    `{"host": "$(hostname)"}` 를 남겼는데, **집계기가 `start_epoch`/`end_epoch` 만 꺼내고
    `host` 를 버렸다.** 그래서 회신 JSON 에 안 실렸고, 그것을 본 사람이 *"측정이 안 됐다"* 고
    읽었다. 부품(payload)은 맞았고 **조립선이 값을 떨어뜨린** ADR-041 유형이다
    (B-3 / `to_dict()` 400자 컷에 이은 세 번째).

    🔴 해석 규칙 — 이 숫자 하나로 두 가지를 말할 수 있고 **셋째는 말할 수 없다**:
      * 유니크 호스트 수 = **그 순간 우리가 점유한 노드 수** `[MEASURED]`
      * `normal` 이 노드 독점(exclusive)이면 그것이 곧 **동시 노드 수의 하한**
      * 🔴 **"상시 그만큼 받는다"는 보장이 아니다.** 그건 `qstat -Qf normal` + 할당량의 몫이다.
    그리고 **유니크 수가 task 수보다 훨씬 작으면 PBS 가 팩킹한 것이고, 그때는
    독점 정책 가정 자체가 반증된다** (과금 모델이 바뀌므로 그 또한 큰 소득이다).

    🔴 `n_hosts` 는 기록이 하나도 없으면 **`0` 이 아니라 `None`** 이다(ADR-036).
    `0` 으로 두면 "노드를 0대 받았다"로 **코드가** 읽는다. *경고는 사람만 읽고 `null` 은
    코드도 읽는다.*
    """
    names = [str(h) for h in (hosts or []) if h and str(h) != UNKNOWN_HOST]
    hist = {}
    for h in names:
        hist[h] = hist.get(h, 0) + 1
    n_tasks = len(hosts or []) if n_tasks is None else n_tasks
    out = {
        "n_hosts": len(hist) or None,
        "hosts_unique": sorted(hist),
        "hosts_histogram": hist,
        #: 🔴 부재를 부재로 보고하기 위한 필드. "0대"와 "안 쟀다"를 구분한다.
        "tasks_with_host": len(names),
        "tasks_without_host": max(0, int(n_tasks) - len(names)),
        "tasks_per_host_max": max(hist.values()) if hist else None,
    }
    if not hist:
        out["hosts_note"] = ("task 로그에 hostname 이 하나도 없다 — 이 패키지가 host 를 "
                             "기록하기 전 판이거나 starts/ 가 비었다. **노드 수 0 이 아니라 "
                             "미측정이다.**")
    else:
        out["hosts_note"] = (
            "유니크 호스트 %d / task %d. 이것은 그 순간 점유한 노드 수의 [MEASURED] 값이며, "
            "큐가 노드 독점이면 동시 노드 수의 **하한**이다. 🔴 '상시 그만큼 받는다'는 "
            "보장이 아니다(qstat -Qf + 할당량 필요). 유니크 수가 task 수보다 크게 작으면 "
            "스케줄러가 task 를 노드에 팩킹한 것이고, 그때는 독점 정책 가정이 반증된다."
            % (len(hist), n_tasks))
    return out


def queue_wait_entry(nodes, submitted_epoch, started_epoch, partition=None,
                     rejected=False, wall_limit_reached=False):
    """큐 대기 1건. 시작하지 못한 잡은 wait_s=None + status로 남긴다(0으로 만들지 마라)."""
    if rejected:
        status = "rejected"
    elif started_epoch is None:
        status = "still_queued" if not wall_limit_reached else "timed_out_waiting"
    else:
        status = "started"
    wait_s = (round(float(started_epoch) - float(submitted_epoch), 1)
              if (started_epoch is not None and submitted_epoch is not None) else None)
    return {"nodes": nodes, "partition": partition, "status": status,
            "submitted_epoch": submitted_epoch, "started_epoch": started_epoch,
            "wait_s": wait_s}


def summarize_queue_wait(entries):
    started = [e for e in entries or [] if e.get("status") == "started"]
    if not started:
        return {"n_started": 0, "median_wait_s": None, "max_wait_s": None}
    waits = sorted(e["wait_s"] for e in started)
    mid = waits[len(waits) // 2]
    return {"n_started": len(started), "median_wait_s": mid,
            "max_wait_s": waits[-1], "min_wait_s": waits[0]}
