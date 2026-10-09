"""Package identity and provenance fingerprinting.

모든 결과 JSON에는 이 모듈이 만든 provenance 블록이 붙는다.
provenance 없는 결과는 폐기 대상이다 (00_PROJECT_BRIEF.md §6).
"""

import hashlib
import os
import platform
import sys
import time

PKG_NAME = "sei_pilot_package"
PKG_VERSION = "0.1.0"

# 회신 JSON 스키마 버전.
#   1.0 = 03_COMPUTE_PLAN.md §R2-6 구성요소 C 원문
#   1.1 = 1.0 + 아래 SCHEMA_EXTENSIONS (필드 추가만. 1.0 필드는 전부 유지)
SCHEMA_VERSION = "1.1"
SCHEMA_BASE_VERSION = "1.0"

# engineer 스펙(1.0)에 없어서 coder가 추가한 필드 + 사유.
# §R2-6: "네가 보기에 필드가 빠졌으면 추가하고 그 사유를 기록하라"
SCHEMA_EXTENSIONS = [
    {
        "field": "provenance",
        "reason": "패키지 버전/파일 해시/실행 시각/파이썬 버전이 없으면 회신 JSON이 "
                  "어느 코드로 생성됐는지 알 수 없다. 재현성 요구사항.",
    },
    {
        "field": "guard",
        "reason": "core-h 하드가드에 걸려 생략된 파일럿이 있으면 engineer가 그것을 "
                  "'실패'로 오독한다. 예약/소비/생략 사유를 명시적으로 회신한다.",
    },
    {
        "field": "cluster.cpu / cluster.filesystems / cluster.scheduler_detail",
        "reason": "A1(소켓/스레드), A8(스크래치 후보가 여러 개일 때 각각의 쿼터)은 "
                  "단일 스칼라로 회신하면 정보가 손실된다.",
    },
    {
        "field": "pilots[].stages / pilots[].adapter / pilots[].warnings",
        "reason": "P1 하위 단계별 core-h 분해는 §R2-6이 요구한 값이고, adapter는 "
                  "'어느 QC 코드로 쟀는가'를 남긴다. 이것 없이는 단가를 비교할 수 없다.",
    },
    {
        "field": "pilots[].status == \"undetermined\" / pilots[].human_review_required "
                 "/ pilots[P1].detail.irc.endpoint_comparison",
        "reason": "02_METHOD_SPEC §12.3의 2층 그래프 판정에서 R2b(배위 재배열, "
                  "barrier 미지)는 pass도 fail도 아니다. fail로 적으면 §12.2의 "
                  "위음성(진짜 TS 기각)이 회신 단계에서 되살아난다. "
                  "판정 근거(R1/R2a/R2b/R3)와 두 층의 해시를 함께 실어 "
                  "규칙이 바뀌어도 재계산 없이 재판정할 수 있게 한다.",
    },
    {
        "field": "unresolved_for_lead",
        "reason": "스크립트가 끝내 측정하지 못한 항목을 명시한다. 침묵하면 lead가 "
                  "'측정됐다'고 오독한다.",
    },
    {
        "field": "throughput_probe.first_start_delay_s / submit_rate_per_min / all_done_wall_s",
        "reason": "duty cycle(A9) 모델에는 시작률뿐 아니라 제출 자체의 병목과 "
                  "전체 배수 완료 시간이 필요하다.",
    },
]

# 이 패키지가 요구하는 최소 파이썬. 클러스터의 system python3가 낡을 수 있으므로
# 표준 라이브러리만 쓰고 하한을 낮게 잡는다 (f-string 사용 → 3.6).
MIN_PYTHON = (3, 6)


def python_ok():
    return sys.version_info[:2] >= MIN_PYTHON


def package_fingerprint(root, extra_exclude=()):
    """패키지 파일 트리의 내용 해시. 코드버전 provenance용 + stage 마커의 판 식별용.

    root 아래 .py/.sh/.tmpl/.inp/.xyz 파일만 대상으로 한다 (결과물 제외).

    🔴 [MAJOR #2] 이 값은 이제 **코드 판(identity)** 이어야 한다 — sei_stage 가
    "이 마커를 만든 판과 지금 판이 같은가"를 이 값으로 판정한다. run.sh 의 기본
    workdir 이 `${SEI_PKG_ROOT}/sei_pilot_work` 라서, 잡이 남기는 .json/.xyz 가
    해시에 새어 들어오면 링크 0 과 링크 1 의 지문이 달라져 **모든 체크포인트가
    무효가 된다**(재개 능력 소실). 그래서 기본 workdir 이름은 상시 제외하고,
    비표준 workdir 은 `extra_exclude` 로 호출자가 제외한다(common.sh 가 넘긴다).
    """
    h = hashlib.sha256()
    files = []
    excluded = {"__pycache__", "work", "results", "sei_pilot_work"}
    excluded.update(extra_exclude or ())
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in excluded)
        for fn in sorted(filenames):
            if fn.endswith((".py", ".sh", ".tmpl", ".inp", ".xyz", ".json")):
                files.append(os.path.join(dirpath, fn))
    for path in sorted(files):
        rel = os.path.relpath(path, root)
        h.update(rel.encode("utf-8"))
        try:
            with open(path, "rb") as fh:
                h.update(fh.read())
        except OSError:
            h.update(b"<unreadable>")
    return h.hexdigest()[:16]


def provenance(root=None, seed=None, invocation=None):
    """결과 JSON에 박히는 provenance 블록."""
    return {
        "package_name": PKG_NAME,
        "package_version": PKG_VERSION,
        "package_fingerprint": package_fingerprint(root) if root else None,
        "schema_version": SCHEMA_VERSION,
        "schema_base_version": SCHEMA_BASE_VERSION,
        "generated_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "generated_at_epoch": int(time.time()),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "random_seed": seed,
        "invocation": invocation,
    }
