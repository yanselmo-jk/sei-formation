"""지난 세션 스냅샷 저장/로드.

**문서를 건드리지 않는다.** `docs/`는 다른 teammate 소유이므로 읽기 전용이며,
스냅샷은 별도 디렉터리(`.session_state/`)에만 쓴다.

스냅샷은 diff에 필요한 최소 필드만 담는다(전문을 저장하면 파일이 커지고,
diff가 문서 표현 변화에 흔들린다).
"""

import json
import os
import time

DEFAULT_DIR = ".session_state"
SNAP_NAME = "last_digest.json"

KEEP_KEYS = ("adrs", "unresolved", "risks", "progress", "doc_sizes", "header")
#: 신선도 이력. 실행을 거듭할수록 정확해지므로 반드시 이어받아야 한다.
PASSTHROUGH_KEYS = ("section_freshness",)


def _slim(state):
    out = {}
    for k in KEEP_KEYS:
        v = state.get(k)
        if isinstance(v, list):
            out[k] = [dict((kk, vv) for kk, vv in item.items()
                           if kk in ("id", "status", "title", "text", "date",
                                     "event", "line"))
                      for item in v]
        else:
            out[k] = v
    for k in PASSTHROUGH_KEYS:
        if state.get(k) is not None:
            out[k] = state[k]
    out["_saved_at"] = int(time.time())
    return out


def path_for(root, snap_dir=None):
    return os.path.join(snap_dir or os.path.join(root, DEFAULT_DIR), SNAP_NAME)


def load(root, snap_dir=None):
    p = path_for(root, snap_dir)
    try:
        with open(p) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return None


def save(root, state, snap_dir=None):
    p = path_for(root, snap_dir)
    d = os.path.dirname(p)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    tmp = p + ".tmp"
    with open(tmp, "w") as fh:
        json.dump(_slim(state), fh, ensure_ascii=False, indent=1)
    os.replace(tmp, p)
    return p
