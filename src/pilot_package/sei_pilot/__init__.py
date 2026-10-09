"""sei_pilot — SEI 파일럿 인도 패키지 (03_COMPUTE_PLAN.md §R2-6).

의존성: **파이썬 표준 라이브러리만.** numpy도 쓰지 않는다.
이유: 계산 노드가 air-gapped이고(ADR-004 / §R2-8 Case B) 사이트의 system python이
맨몸일 수 있다. pip install이 필요한 순간 이 패키지는 실패한다.
"""

from .version import PKG_VERSION, SCHEMA_VERSION   # noqa: F401
