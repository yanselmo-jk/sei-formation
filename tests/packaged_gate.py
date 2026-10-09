"""빌드 후 산출물 검증 관문이 돌리는 **집합을 스스로 찾는다.**

🔴 왜 자동 발견인가 — lead 지적:
> *"관문이 클래스 이름을 하나 적어 두면, 앞으로 tarball 을 여는 검사를 새로 만드는 사람은
> **관문에도 손으로 추가해야 한다. 그리고 언젠가 잊는다.**
> 우리가 방금 없앤 것이 바로 그 형태다 — **'사람이 기억해야 작동하는 보호'**."*

⟹ **이름을 적지 않는다.** `tests/` 안에서 **실제로 tarball 을 여는**(`tarfile.open`) 테스트
클래스를 AST 로 찾아 전부 돌린다. **새 클래스는 저절로 포함된다 — 잊을 것이 없다.**

## 왜 이 관문이 따로 필요한가
`make_package.sh` 는 빌드 전에 낡은 tarball 을 `.stale` 로 치운 뒤 전체 스위트를 돌린다
(교착 회피 — *"'dist 가 낡았다' 실패 → 빌드 중단 → 영원히 못 고침"*). 그래서 **tarball 을
여는 검사는 빌드 중에 반드시 skip 된다.**
```
standalone (tarball 있음)  : skipped=8
빌드 상태 (tarball 치워짐)  : skipped=22     ← 차이 14 = "빌드가 눈 감는 구간"
```
⟹ 🔒 **`tar czf` 뒤에 이 모듈을 한 번 더 돌려 그 구간을 닫는다.** [1] 의 skip 성질은 그대로 둔다.

🔴 **고장 시 넘어지는 방향(규약 18)**: 이 모듈은 **발견된 클래스가 0개면 실패**한다.
발견이 조용히 비면 관문은 *"돌 것이 없다"* 며 **통과**할 것이고, 그건 있으나 마나가 아니라
**있다고 믿게 만들어서 없는 것보다 나쁘다.**
"""

import ast
import os
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))

#: 🔴 판정 기준은 **"실제로 tarball 을 여는가"**(`tarfile.open`)다.
#:  단순히 `.tar.gz` 를 언급하는 것으로는 부족하다 — 주석·경로 문자열만 있는 클래스가 섞인다
#:  (실제로 naive 스캔은 6개를 물었고 그중 2개만 진짜였다).
#:  🔴 **여는 괄호까지** 본다. `"tarfile.open"` 만 보면 **이 토큰을 검사하는 코드 자신이
#:   걸린다** — 실제로 `TestBuildGate`(발견 로직을 검증하는 클래스)가 자기 자신을 물었다.
#:   검사기가 자기를 검사 대상으로 삼는 자기지시적 오탐이다.
OPENS_TARBALL = "tarfile.open("


def tarball_test_classes():
    """`tests/` 안에서 **인도물 tarball 을 여는** 테스트 클래스 → [(모듈, 클래스), …]"""
    found = []
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        path = os.path.join(HERE, fn)
        with open(path, encoding="utf-8") as fh:
            src = fh.read()
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.ClassDef):
                continue
            seg = ast.get_source_segment(src, node) or ""
            if OPENS_TARBALL in seg:
                found.append((fn[:-3], node.name))
    return found


def load_tests(loader, standard_tests, pattern):   # noqa: ARG001  (unittest 규약)
    """`python3 -m unittest packaged_gate` 가 이것을 부른다."""
    suite = unittest.TestSuite()
    classes = tarball_test_classes()
    if not classes:
        # 🔴 규약 18 — 발견이 비면 **실패 쪽으로 넘어진다.**
        raise AssertionError(
            "산출물 검증 관문이 돌릴 클래스를 하나도 찾지 못했다. "
            "발견 로직이 깨졌거나 tarball 검사가 전부 사라졌다 — 둘 다 조용히 넘어가면 안 된다.")
    for mod_name, cls_name in classes:
        mod = __import__(mod_name)
        suite.addTests(loader.loadTestsFromTestCase(getattr(mod, cls_name)))
    return suite
