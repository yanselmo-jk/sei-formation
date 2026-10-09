"""항목 → PBS `-A` 계정 해석 — **단일 출처는 config/accounts.json**.

🔴 왜 전역 `--account` 하나로는 안 되나
--------------------------------------
이 클러스터의 계정은 프로젝트 단위가 아니라 **소프트웨어 단위**다(사용자 확인):

    Gaussian → `gaussian`,  xTB → `etc`,  VASP → `vasp`,  probing → `etc`

전역 값 하나를 전파하면 **어떤 값을 넣어도 항목의 절반이 틀린다.** 그리고 계정이 틀리면
PBS 는 제출 자체를 거부한다 — 10개 항목이 전부 거부되면 왕복 1회(3.5일)가 그대로 날아간다.

⚠ 계정 문자열을 `plan.py` 의 Item 에 박지 않는다. Item 은 *어떤 소프트웨어인가*(`account_key`)
만 들고 있고, 문자열은 여기서 한 번 해석된다. (같은 진실이 두 곳에 있어 한쪽만 갱신되는
사고가 이 프로젝트에서 다섯 번 났다.)
"""

from . import config as config_mod

FALLBACK = {
    "map": {"probe": {"account": "etc", "confirmed": True}},
    "default_key": "probe",
    "queue_default": "normal",
    "_fallback": True,
}


def load(config_dir=None):
    return config_mod.load("accounts.json", FALLBACK, config_dir)


def default_queue(config_dir=None):
    return load(config_dir).get("queue_default") or None


def parse_overrides(values):
    """`--account` 인자들을 (전역값, {소프트웨어: 계정}) 으로 나눈다.

    `--account gaussian=myproj` → 매핑 덮어쓰기
    `--account myproj`          → 전 항목 덮어쓰기(계정이 하나뿐인 사이트용)
    """
    global_value, per_key = None, {}
    for raw in values or []:
        for part in str(raw).split(","):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                k, v = part.split("=", 1)
                per_key[k.strip()] = v.strip()
            else:
                global_value = part
    return global_value, per_key


class Resolver(object):
    """항목 key → 계정. 무엇이 미확인인지도 함께 들고 있는다."""

    def __init__(self, config_dir=None, global_override=None, overrides=None):
        cfg = load(config_dir)
        self.map = dict(cfg.get("map") or {})
        self.default_key = cfg.get("default_key") or "probe"
        self.global_override = global_override
        self.overrides = dict(overrides or {})
        self.unknown_override_keys = [k for k in self.overrides if k not in self.map]

    def entry(self, account_key):
        return self.map.get(account_key) or self.map.get(self.default_key) or {}

    def account_for(self, account_key):
        """계정 문자열. 우선순위: 전역 덮어쓰기 > 소프트웨어별 덮어쓰기 > 설정."""
        if self.global_override:
            return self.global_override
        if account_key in self.overrides:
            return self.overrides[account_key]
        return self.entry(account_key).get("account") or None

    def is_confirmed(self, account_key):
        """🔴 추정으로 넣은 계정인지. 추정이면 **조용히 넘어가지 않고 화면에 띄운다.**"""
        if self.global_override or account_key in self.overrides:
            return True                      # 사용자가 직접 준 값
        return bool(self.entry(account_key).get("confirmed"))

    def note(self, account_key):
        return self.entry(account_key).get("note") or ""

    def unconfirmed_used(self, account_keys):
        """실제로 쓰이는 것 중 미확인인 소프트웨어 목록(중복 제거, 순서 유지)."""
        out = []
        for k in account_keys:
            if not self.is_confirmed(k) and k not in out:
                out.append(k)
        return out

    def warnings(self, account_keys):
        """dry-run 에 띄울 경고 줄. 없으면 빈 목록."""
        lines = []
        for k in self.unconfirmed_used(account_keys):
            lines.append(
                "  🔴 %s 항목은 `-A %s` 를 씁니다 (**미확인 — 저희 추정입니다**). %s"
                % (k, self.account_for(k), self.note(k)))
            lines.append("     다르면:  ./run.sh --account %s=<계정이름>" % k)
        for k in self.unknown_override_keys:
            lines.append("  ⚠ `--account %s=...` 의 '%s' 는 알려진 소프트웨어가 아닙니다 "
                         "(알려진 값: %s)" % (k, k, ", ".join(sorted(self.map))))
        return lines
