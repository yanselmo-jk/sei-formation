"""신선도(staleness) 추적 — lead 요청 #1.

🔴 **이 도구의 유일한 실패 모드는 "낡은 항목을 조용히 최신인 것처럼 보여주는 것"이다.**
잘못된 확신을 주는 요약은 요약이 없는 것보다 나쁘다. 실제로 그 사고가 났다
(완료된 Phase 0~1 액션이 "지금 할 수 있는 것"으로 떴다).

이 저장소에는 **git이 없다.** 그래서 두 개의 독립 신호를 결합한다:

  (a) **파일 mtime** — 즉시 얻을 수 있는 **하한**. 파일이 5일 전에 마지막으로 바뀌었다면
      그 안의 **모든 줄은 최소 5일 이상 됐다.** 이력이 없어도 오늘 바로 쓸 수 있다.
  (b) **관측 이력** — 매 실행마다 섹션별 내용 해시를 스냅샷에 남긴다. 해시가 그대로면
      `last_changed`를 이어받고, 바뀌면 지금으로 갱신한다. 실행을 거듭할수록 정확해진다.

  나이 = max(a, b). 둘 다 **하한**이므로 나이를 과소평가하지 않는다
  (과대평가는 "확인해 보라"는 신호일 뿐이지만, 과소평가는 잘못된 확신이다).

한계(정직하게): git이 없으므로 **줄 단위** 정확한 수정 시각은 알 수 없다.
첫 실행에서는 (b)가 0이고 (a)만 유효하다. 라벨에 그 사실을 그대로 쓴다.
"""

import hashlib
import os
import time

DAY = 86400.0
DEFAULT_STALE_DAYS = 7


def _sha(text):
    return hashlib.sha1(text.encode("utf-8", "replace")).hexdigest()[:16]


def section_hashes(docs, section_index):
    """{(doc, 섹션제목): 내용해시}. 공백 변화는 무시한다(의미 없는 갱신 방지)."""
    out = {}
    for doc, secs in section_index.items():
        text = docs.get(doc, "")
        lines = text.splitlines()
        for title, (start, end) in secs.items():
            body = "\n".join(x.strip() for x in lines[start - 1:end] if x.strip())
            out["%s::%s" % (doc, title)] = _sha(body)
    return out


def file_ages(docs_dir, now=None):
    """{파일명: 나이(일)} — 나이의 **하한**."""
    now = now or time.time()
    out = {}
    if not os.path.isdir(docs_dir):
        return out
    for fn in os.listdir(docs_dir):
        if not fn.endswith(".md"):
            continue
        try:
            out[fn] = max(0.0, (now - os.stat(os.path.join(docs_dir, fn)).st_mtime) / DAY)
        except OSError:
            continue
    return out


def merge(prev_snapshot, cur_hashes, now=None):
    """이전 스냅샷의 섹션 해시와 비교해 `last_changed_epoch` 를 이어받는다."""
    now = int(now or time.time())
    prev = (prev_snapshot or {}).get("section_freshness") or {}
    out = {}
    for key, h in cur_hashes.items():
        old = prev.get(key)
        if old and old.get("hash") == h:
            out[key] = {"hash": h,
                        "first_seen_epoch": old.get("first_seen_epoch", now),
                        "last_changed_epoch": old.get("last_changed_epoch", now),
                        "observed": True}
        else:
            out[key] = {"hash": h, "first_seen_epoch": (old or {}).get("first_seen_epoch", now),
                        "last_changed_epoch": now,
                        "observed": bool(old)}
    return out


def age_days(freshness_entry, file_age, now=None):
    """관측 이력과 파일 mtime 중 **더 오래된 쪽**(=하한이 더 강한 쪽)을 쓴다."""
    now = now or time.time()
    obs = 0.0
    if freshness_entry and freshness_entry.get("observed"):
        obs = max(0.0, (now - freshness_entry["last_changed_epoch"]) / DAY)
    return max(obs, file_age or 0.0)


def label(age, stale_days=DEFAULT_STALE_DAYS, observed=False):
    """사람이 읽는 신선도 라벨. 근거가 약하면 약하다고 쓴다."""
    if age is None:
        return None
    d = int(age)
    if d < 1:
        return None                       # 오늘 바뀐 것은 표시하지 않는다(잡음)
    suffix = "" if observed else "≥"      # 관측 이력이 없으면 하한만 안다
    tag = "⏳" if d >= stale_days else ""
    return "%s%s%d일 경과" % (tag, suffix, d)
