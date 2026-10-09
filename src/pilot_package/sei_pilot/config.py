"""설정 로더 — 화학 파라미터는 코드가 아니라 데이터다 (ADR-001).

`config/*.json` 을 읽어 dict로 돌려준다. 파일이 없거나 깨져 있으면 **조용히
기본값으로 넘어가지 않고** 그 사실을 호출자가 알 수 있게 표시한다
(파라미터가 바뀐 줄 모르고 계산하는 것이 가장 비싼 실패다).
"""

import json
import os

CONFIG_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config")

_CACHE = {}

# 설정 파일을 못 읽었을 때 쓰는 최소 fallback. 값은 config/graph_layers.json 과
# 동일해야 하며, 사용 시 `_fallback: True` 가 붙어 회신 JSON에 드러난다.
GRAPH_LAYERS_FALLBACK = {
    "layer_C": {"elements": ["C", "H", "O", "F", "P", "N", "S"],
                "bond_tolerance": 1.25},
    "layer_I": {"cations": ["Li", "Na", "K", "Mg", "Ca"],
                "contact_cutoff_ang": {"Li-O": 2.4, "Li-F": 2.3, "default": 2.5},
                "sensitivity_delta_ang": 0.2},
    "kinetic_merge": {"tau_eV": 0.1, "unknown_barrier_policy": "undetermined"},
    "_fallback": True,
    "_fallback_reason": None,
}


def load(name, fallback=None, config_dir=None):
    key = (config_dir or CONFIG_DIR, name)
    if key in _CACHE:
        return _CACHE[key]
    path = os.path.join(config_dir or CONFIG_DIR, name)
    try:
        with open(path) as fh:
            cfg = json.load(fh)
        cfg["_source"] = path
    except (OSError, ValueError) as exc:
        if fallback is None:
            raise
        cfg = dict(fallback)
        cfg["_fallback"] = True
        cfg["_fallback_reason"] = "%s: %s" % (type(exc).__name__, exc)
        cfg["_source"] = path + " (읽기 실패 → 내장 fallback 사용)"
    _CACHE[key] = cfg
    return cfg


def graph_layers(config_dir=None):
    """IRC 끝점 판정용 2층 그래프 설정 (02_METHOD_SPEC §12.3)."""
    return load("graph_layers.json", GRAPH_LAYERS_FALLBACK, config_dir)


def clear_cache():
    _CACHE.clear()
