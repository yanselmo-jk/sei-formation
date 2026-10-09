"""동봉 Gaussian 기저 파일(`gen`) 처리 — 파싱 · 원소 커버리지 검사 · 블록 생성.

🔴 왜 이 모듈이 필요한가
------------------------
ADR-029의 기저 `def2-TZVPPD` 는 **Gaussian16 내장 키워드가 아니다**(`def2TZVPPD` 라고
써도 G16은 모른다). 그래서 route 에 `gen` 을 쓰고 좌표 뒤에 기저 블록을 직접 붙인다.

그러면 사전검증의 성격이 바뀐다:
  - 내장 키워드일 때 : "이 이름이 유효한가"  (문자열 검사)
  - `gen` 일 때      : "동봉한 블록이 **이 분자에 등장하는 원소를 전부 덮는가**"

후자를 안 잡으면 G16은 입력을 다 읽고 SCF 직전에
`Atomic number out of range` / `basis functions not found` 로 죽는다. 왕복 1회(3.5일)
안에 그걸 발견하면 그 왕복은 통째로 날아간다. **그래서 입력을 쓰기 전에 검사한다.**

형식 가정 (BSE gaussian94):
    !주석
    <원소기호>     0
    S   3   1.00
        <지수>   <계수>
        ...
    ****
ECP 는 def2 계열에서 Z<=36 원소에 필요 없다(우리 원소: H,Li,C,O,F,P). ECP 블록이
들어오면 `has_ecp` 로 드러내되 처리는 하지 않는다 — 조용히 버리지 않기 위해서다.
"""

import os
import re

SEPARATOR = "****"
# "El     0" 형태의 원소 머리줄. 계수 줄(숫자로 시작)과 각운동량 줄(S/P/D/SP ...)을
# 잘못 잡지 않도록 '기호 + 공백 + 0' 을 통째로 못 박는다.
_ELEMENT_HEAD = re.compile(r"^\s*([A-Z][a-z]?)\s+0\s*$")


class BasisError(Exception):
    """기저 파일이 없거나, 요구 원소를 덮지 못할 때. **삼키지 말 것.**"""


def default_dir(pkg_root=None):
    root = pkg_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "inputs", "basis")


def read(path):
    with open(path) as fh:
        return fh.read()


def _strip_comments(text):
    return "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("!"))


def parse_elements(text):
    """기저 파일이 정의하는 원소 기호 목록(등장 순서, 중복 제거)."""
    out = []
    for line in _strip_comments(text).splitlines():
        m = _ELEMENT_HEAD.match(line)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def has_ecp(text):
    """ECP 블록이 섞여 있는가. (있으면 `gen` 만으로는 부족하고 `pseudo=read` 가 필요하다.)

    ⚠ 처음에 "원소줄 다음 줄이 `<기호> <정수> <정수>`" 로 잡으려다 각운동량 줄
    (`S    3   1.00`)을 전부 ECP로 오탐했다. gaussian94 형식의 ECP 머리줄은
    `Li-ECP     2     10` 처럼 **`-ECP` 토큰**을 반드시 포함하므로 그걸로 판정한다.
    """
    return bool(re.search(r"\bECP\b", _strip_comments(text), re.I))


def split_blocks(text):
    """`****` 로 구분된 원소별 블록을 [(원소, 본문)] 로 자른다."""
    out = []
    for chunk in _strip_comments(text).split(SEPARATOR):
        lines = [l for l in chunk.splitlines() if l.strip()]
        if not lines:
            continue
        m = _ELEMENT_HEAD.match(lines[0])
        if m:
            out.append((m.group(1), "\n".join(lines)))
    return out


def block(text, only=None):
    """`.gjf` 좌표 뒤에 붙일 기저 블록(주석 제거, 각 원소 블록이 `****` 로 끝남).

    `only` 를 주면 **그 원소들만** 내보낸다.
    🔴 왜 걸러내나: 분자에 없는 원소의 기저까지 넣었을 때 G16이 이를 무시하는지
    거부하는지 우리는 **확인하지 못했다**(문서·실행 모두 없음). 걸러내는 쪽은
    확실히 유효하므로 불확실한 쪽을 택하지 않는다. 입력도 작아진다.
    """
    blocks = split_blocks(text)
    if only is not None:
        want = list(dict.fromkeys(only))
        by_el = dict(blocks)
        blocks = [(e, by_el[e]) for e in want if e in by_el]
    return "".join("%s\n%s\n" % (body, SEPARATOR) for _, body in blocks)


def load_for_level(level_spec, pkg_root=None):
    """레벨 정의(dict)의 `basis_file` 을 읽는다. 내장 키워드 레벨이면 None."""
    rel = level_spec.get("basis_file")
    if not rel:
        return None
    root = pkg_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = rel if os.path.isabs(rel) else os.path.join(root, rel)
    if not os.path.exists(path):
        raise BasisError(
            "동봉 기저 파일이 없다: %s\n"
            "  ↳ 이 레벨(%s / %s)은 `gen` 을 쓰므로 파일이 반드시 있어야 한다.\n"
            "  ↳ 패키지가 손상됐거나 tarball 이 낡았다. 다시 풀어라."
            % (path, level_spec.get("label", "?"), level_spec.get("basis_real_name", "?")))
    return {"path": path, "text": read(path)}


def check_coverage(needed, text, context=""):
    """`needed` 원소를 기저가 전부 덮는지. 못 덮으면 BasisError 를 **던진다**.

    반환: 덮는 원소 목록. (조용히 True/False 를 돌려주면 호출부가 무시하기 쉽다.)
    """
    have = parse_elements(text)
    have_set = set(have)
    missing = [e for e in dict.fromkeys(needed) if e not in have_set]
    if missing:
        raise BasisError(
            "🔴 동봉 기저가 등장 원소를 덮지 못한다%s\n"
            "  ↳ 없는 원소: %s\n"
            "  ↳ 기저가 덮는 원소: %s\n"
            "  ↳ 이대로 두면 G16이 좌표를 다 읽고 SCF 직전에 죽는다.\n"
            "  ↳ 고칠 곳: inputs/basis/ 의 .gbs 파일에 해당 원소 블록을 추가하라\n"
            "     (Basis Set Exchange, format=gaussian94, 같은 기저 이름으로 받으면 된다).\n"
            "  ↳ 원소 목록을 바꾼 것이라면 config/qc_levels.json 의 "
            "gaussian16.basis_policy.elements_required 도 같이 고쳐라."
            % (" (%s)" % context if context else "", ", ".join(missing), ", ".join(have)))
    return have


def elements_in_xyz(text):
    """xyz 본문에서 등장 원소 기호(중복 제거, 등장 순서)."""
    lines = text.splitlines()
    try:
        n = int(lines[0].split()[0])
    except (IndexError, ValueError):
        raise BasisError("xyz 첫 줄에서 원자 수를 읽지 못했다")
    out = []
    for line in lines[2:2 + n]:
        f = line.split()
        if not f:
            continue
        sym = f[0][:1].upper() + f[0][1:2].lower()
        if sym not in out:
            out.append(sym)
    return out
