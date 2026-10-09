"""테스트에서 패키지를 import 할 수 있게 경로를 잡는다.

패키지는 `src/pilot_package/` 에 그대로 인도 형태로 들어 있다.
(설치 절차 없이 tar 풀고 바로 도는 것이 요구사항이므로 setup.py는 없다.)
"""

import os
import sys

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(TESTS_DIR)
PKG_ROOT = os.path.join(REPO_ROOT, "src", "pilot_package")

if PKG_ROOT not in sys.path:
    sys.path.insert(0, PKG_ROOT)

# 🔴 [FIXTURE — 결정의 입력이 될 수 없다, ADR-098/100] 덱 *구조* 를 검증하는 테스트용
# solvent_policy. ADR-105 배선 이후 sei_qc_input 은 solvent.resolve_solvent_line() 을
# 통과해야만 덱을 낼 수 있다 — 실제 config 의 model 은 null(전면 거부)이므로, 구조
# 테스트는 이 [FIXTURE] 값을 SEI_SOLVENT_POLICY_JSON 으로 주입해 방출 경로를 연다.
# 값 7개는 물리적 의미가 없다(단지 "테이블이 가득 찼다"는 상태를 만든다).
# 🔴 [FIXTURE] C-8 게이트(payload/P1.sh, C-8-1)의 테스트용 끝단 인증 주입.
# 실제 인증은 endpoint_prep 산출물에서 와야 하며(다음 라운드 배선), 이 값은 오직
# "게이트를 지난 뒤의 경로(QST2/C-12)" 를 시험하기 위해 존재한다. declared_planar 는
# 동봉 guess 가 실제로 heavy-atom 평면이라 C-9 절이 막는 것을 [FIXTURE] 로 선언 해제.
TEST_C8_ENDPOINTS_JSON = (
    '{"reactant": {"optimised": true, "converged": true, "n_imag": 0,'
    ' "level": "level2"},'
    ' "product": {"optimised": true, "converged": true, "n_imag": 0,'
    ' "level": "level2"},'
    ' "declared_planar": true, "_label": "[FIXTURE]"}')

TEST_SOLVENT_POLICY_JSON = (
    '{"model": "smd_descriptors", "descriptors": {'
    '"Eps": 18.5, "EpsInf": 2.0, "HBondAcidity": 0.0, "HBondBasicity": 0.5,'
    '"SurfaceTensionAtInterface": 60.0, "CarbonAromaticity": 0.0,'
    '"ElectronegativeHalogenicity": 0.0}, "_label": "[FIXTURE]"}')
