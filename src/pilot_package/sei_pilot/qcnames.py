"""범함수·기저 **이름 사전검증**.

🔴 왜 이 모듈이 생겼나 (lead가 실행으로 잡은 BLOCKER):
`XC = "wb97x-d3"` 는 **오타가 아니라 그럴듯하게 틀린 이름**이었다. pyscf에 그런 범함수가
없는데도 문자열로는 완벽히 그럴듯해서 정적 검토(critic)도, 우리 테스트도 못 잡았다.
SCF를 시작하고 나서야 `NotImplementedError` 로 터졌다 — **계산 자원과 왕복 1회를 태운 뒤.**

원칙: **이름은 계산 전에 검증한다. 실패하면 유효한 후보를 함께 출력한다**
(사용자가 왕복 없이 고칠 수 있어야 한다).

이 모듈 자체는 **표준 라이브러리만** 쓴다. pyscf 검증은 지연 import이며,
pyscf가 없는 환경(= CPU 패키지)에서도 import 가능해야 한다.
"""

#: 우리 박스(pyscf 2.14.0)에서 `libxc.parse_xc()` 로 **실제 확인한** 이름들.
#: 🔴 "그럴듯한 이름"을 추측해서 넣지 마라. 확인한 것만 넣는다.
KNOWN_GOOD_XC = (
    "wb97x-v",       # ADR-029 생산 레벨과 동일 — P4의 기본 선택
    "wb97x-d",
    "wb97x-d3bj",
    "wb97m-v",
    "wb97m-d3bj",
    "b3lyp",
    "pbe0",
    "pbe",
)

#: 흔히 틀리는 이름 → 실제 이름. 실패 메시지에서 바로 지목한다.
XC_ALIASES = {
    "wb97x-d3": "wb97x-d3bj 또는 wb97x-v (pyscf에 'wb97x-d3'는 없다)",
    "wb97xd": "wb97x-d",
    "wb97x_v": "wb97x-v",
    "ωb97x-v": "wb97x-v",
    "wb97xv": "wb97x-v",
}

KNOWN_GOOD_BASIS = ("def2-svp", "def2-tzvp", "def2-tzvppd", "def2-qzvp",
                    "6-31g*", "cc-pvdz", "cc-pvtz")


class NameError_(Exception):
    """이름 검증 실패. 메시지에 후보 목록이 들어 있다."""


def _fmt(candidates):
    return ", ".join(candidates)


def validate_pyscf_xc(xc, probe_elements=("C",)):
    """pyscf 범함수 이름 검증. 반환 (ok, message).

    pyscf가 없으면 `(None, 사유)` — **모르는 것을 통과로 처리하지 않는다.**
    """
    del probe_elements
    try:
        from pyscf.dft import libxc
    except Exception as exc:                     # pyscf 부재
        return None, "pyscf 없음 — 이름 검증 불가 (%s)" % type(exc).__name__
    try:
        libxc.parse_xc(xc)
        return True, "ok"
    except Exception as exc:
        hint = XC_ALIASES.get((xc or "").strip().lower())
        good = [c for c in KNOWN_GOOD_XC if _parses(libxc, c)]
        msg = ("범함수 이름이 유효하지 않다: %r (%s)\n"
               "  → 이 pyscf에서 확인된 유효 후보: %s" % (xc, exc, _fmt(good)))
        if hint:
            msg += "\n  → 아마 이것을 의도했을 것이다: %s" % hint
        return False, msg


def _parses(libxc, name):
    try:
        libxc.parse_xc(name)
        return True
    except Exception:
        return False


def validate_pyscf_basis(basis, element="C"):
    """pyscf 기저 이름 검증(원소 하나로 로드해 본다)."""
    try:
        from pyscf import gto
    except Exception as exc:
        return None, "pyscf 없음 — 이름 검증 불가 (%s)" % type(exc).__name__
    try:
        gto.basis.load(basis, element)
        return True, "ok"
    except Exception as exc:
        good = []
        for c in KNOWN_GOOD_BASIS:
            try:
                gto.basis.load(c, element)
                good.append(c)
            except Exception:
                pass
        return False, ("기저 이름이 유효하지 않다: %r (원소 %s, %s)\n"
                       "  → 이 pyscf에서 확인된 유효 후보: %s"
                       % (basis, element, exc, _fmt(good)))


def preflight_pyscf(xc, basis, elements=("C", "H", "O", "Li")):
    """본 계산 **전에** 부르는 관문. 실패하면 즉시 예외를 던진다.

    반환: 검증 결과 dict (회신 JSON에 그대로 실린다 — 무엇을 검증했는지 남긴다).
    """
    out = {"xc": xc, "basis": basis, "checked_elements": list(elements),
           "xc_valid": None, "basis_valid": None, "messages": []}
    ok, msg = validate_pyscf_xc(xc)
    out["xc_valid"] = ok
    out["messages"].append("xc: " + msg)
    if ok is False:
        raise NameError_(msg)

    for el in elements:
        ok_b, msg_b = validate_pyscf_basis(basis, el)
        if ok_b is False:
            out["basis_valid"] = False
            out["messages"].append("basis(%s): %s" % (el, msg_b))
            raise NameError_(msg_b)
        if out["basis_valid"] is None:
            out["basis_valid"] = ok_b
    out["messages"].append("basis: ok (%s)" % ", ".join(elements))
    return out
