"""🔴 범함수·기저 **이름 사전검증** 회귀 테스트.

배경: lead가 실행으로 BLOCKER를 잡았다 — `XC = "wb97x-d3"` 는 pyscf에 없는 이름인데
문자열로는 완벽히 그럴듯해서 **정적 검토(critic)도 우리 테스트도 못 잡았고**,
SCF를 시작하고 나서야 `NotImplementedError` 로 터졌다.

이 테스트의 핵심은 **원래 실패 모드를 재현하는 입력**(`wb97x-d3`)을 쓰는 것이다.
pyscf가 있는 환경에서는 진짜로 검증하고, 없으면 그 사실을 명시적으로 skip 한다
(**pyscf가 없다고 통과로 처리하지 않는다** — 그것이 이 버그를 놓친 방식이다).
"""

import os
import re
import sys
import unittest

import context  # noqa: F401
from sei_pilot import qcnames

PKG = context.PKG_ROOT
HAVE_PYSCF = True
try:
    from pyscf.dft import libxc  # noqa: F401
except Exception:
    HAVE_PYSCF = False


class TestNameTablesAreHonest(unittest.TestCase):
    def test_bad_name_is_not_in_the_known_good_list(self):
        """🔴 회귀: 이 이름이 목록에 다시 들어오면 안 된다."""
        self.assertNotIn("wb97x-d3", qcnames.KNOWN_GOOD_XC)

    def test_alias_table_points_the_bad_name_at_real_ones(self):
        hint = qcnames.XC_ALIASES["wb97x-d3"]
        self.assertIn("wb97x-v", hint)
        self.assertIn("wb97x-d3bj", hint)

    def test_production_functional_is_in_the_good_list(self):
        """P4는 생산 레벨(ADR-029 wB97X-V)과 범함수를 일치시킨다."""
        self.assertIn("wb97x-v", qcnames.KNOWN_GOOD_XC)

    def test_missing_pyscf_returns_none_not_true(self):
        """🔴 검증 불가를 '통과'로 처리하면 이 버그가 그대로 돌아온다."""
        ok, msg = qcnames.validate_pyscf_xc("anything", )
        self.assertIn(ok, (True, False, None))
        if not HAVE_PYSCF:
            self.assertIsNone(ok)
            self.assertIn("pyscf 없음", msg)


@unittest.skipUnless(HAVE_PYSCF, "pyscf 없음 — 이름 검증을 실제로 확인할 수 없다")
class TestAgainstRealPyscf(unittest.TestCase):
    def test_the_original_blocker_is_detected(self):
        ok, msg = qcnames.validate_pyscf_xc("wb97x-d3")
        self.assertFalse(ok)
        self.assertIn("유효하지 않다", msg)

    def test_failure_message_lists_valid_candidates(self):
        """사용자가 왕복 없이 고칠 수 있어야 한다(lead 요구)."""
        _ok, msg = qcnames.validate_pyscf_xc("wb97x-d3")
        self.assertIn("유효 후보", msg)
        self.assertIn("wb97x-v", msg)
        self.assertIn("아마 이것을 의도했을 것이다", msg)

    def test_fixed_name_passes(self):
        self.assertEqual(qcnames.validate_pyscf_xc("wb97x-v")[0], True)

    def test_basis_names_used_by_p4_and_production(self):
        for basis in ("def2-tzvp", "def2-tzvppd"):
            self.assertEqual(qcnames.validate_pyscf_basis(basis, "C")[0], True, basis)

    def test_bad_basis_is_detected_with_candidates(self):
        ok, msg = qcnames.validate_pyscf_basis("def2-tzvp-nonexistent", "C")
        self.assertFalse(ok)
        self.assertIn("유효 후보", msg)

    def test_preflight_blocks_before_any_scf(self):
        self.assertRaises(qcnames.NameError_, qcnames.preflight_pyscf,
                          "wb97x-d3", "def2-tzvp")

    def test_preflight_passes_for_the_fixed_pair_and_records_what_it_checked(self):
        rec = qcnames.preflight_pyscf("wb97x-v", "def2-tzvp",
                                      elements=("C", "H", "O", "Li"))
        self.assertTrue(rec["xc_valid"])
        self.assertTrue(rec["basis_valid"])
        self.assertEqual(rec["checked_elements"], ["C", "H", "O", "Li"])

    def test_every_known_good_name_actually_parses(self):
        """🔴 목록에 '그럴듯한 추측'을 넣지 않았는지 실제로 확인한다."""
        for xc in qcnames.KNOWN_GOOD_XC:
            self.assertEqual(qcnames.validate_pyscf_xc(xc)[0], True, xc)


class TestPayloadUsesValidatedNames(unittest.TestCase):
    """payload 파일에 박힌 이름 자체를 검사한다 — 코드가 아니라 **셸에 들어 있다.**"""

    def _p4(self):
        with open(os.path.join(PKG, "payload", "P4.sh")) as fh:
            return fh.read()

    def test_p4_does_not_use_the_broken_functional(self):
        self.assertNotIn('"wb97x-d3"', self._p4())

    def test_p4_uses_production_functional(self):
        m = re.search(r'XC,\s*BASIS\s*=\s*"([^"]+)",\s*"([^"]+)"', self._p4())
        self.assertIsNotNone(m, "P4.sh 에서 XC/BASIS 정의를 찾지 못했다")
        xc, basis = m.group(1), m.group(2)
        self.assertEqual(xc, "wb97x-v")          # ADR-029 생산 레벨과 일치
        self.assertEqual(basis, "def2-tzvp")     # 메모리 상한 왜곡 방지(lead 지시)
        self.assertIn(xc, qcnames.KNOWN_GOOD_XC)

    def test_p4_calls_preflight_before_scf(self):
        text = self._p4()
        i_pre = text.index("preflight_pyscf")
        i_scf = text.index("mf.kernel()")
        self.assertLess(i_pre, i_scf, "이름 검증이 SCF보다 뒤에 있다")

    def test_p4_records_basis_discrepancy_with_production(self):
        """🔴 P4는 def2-tzvp, 생산은 def2-TZVPPD. 안 적으면 나중에 잘못 환산한다."""
        text = self._p4()
        self.assertIn("production_basis", text)
        self.assertIn("def2-TZVPPD", text)

    def test_p4_fills_gpu_model_from_multiple_sources(self):
        """lead 관측: gpu_model 이 null 로 나왔다. nvidia-smi가 PATH에 없는 환경이 있다.

        경로는 config/env_paths.json 단일 출처에서 오므로 P4.sh 에 리터럴이 있으면 안 된다
        (그 복제가 5번째 같은 유형 버그의 원인이었다).
        """
        text = self._p4()
        self.assertIn("envpaths.extra_search_paths()", text)
        self.assertIn("import cupy", text)
        for line in text.splitlines():
            if "/usr/lib/wsl/lib" in line:
                self.assertTrue(line.strip().startswith("#"), line)

    def test_smoke_uses_the_real_route_generator(self):
        """🔴 smoke 는 **실제로 쓸 route** 를 검증해야 한다.

        (예전 ORCA판은 BP86/def2-SVP만 돌려 생산 키워드를 한 번도 보지 않았다.
         G16 재작성판도 같은 원칙을 지킨다 — sei_qc_input 으로 진짜 입력을 만든다.)
        """
        with open(os.path.join(PKG, "payload", "qc_adapter.sh")) as fh:
            text = fh.read()
        smoke = text[text.index("sei_qc_smoke()"):]
        self.assertIn("sei_qc_input", smoke, "smoke가 실제 입력 생성기를 쓰지 않는다")
        self.assertNotIn("BP86", smoke)
        self.assertIn("smoke_L", smoke)
        self.assertIn("Normal termination", smoke)   # G16 성공 판정
        self.assertIn("config/qc_levels.json", smoke)  # 고칠 곳을 알려준다

    def test_levels_are_config_not_hardcoded_in_shell(self):
        """🔴 `wb97x-d3` 사건의 교훈: 이름을 셸에 박지 않는다."""
        with open(os.path.join(PKG, "payload", "qc_adapter.sh")) as fh:
            text = fh.read()
        for name in ("wB97XD", "def2TZVP", "wB97X-V", "def2-TZVPPD"):
            for line in text.splitlines():
                if name in line:
                    self.assertTrue(line.strip().startswith("#"),
                                    "레벨 이름이 셸에 하드코딩됐다: %s" % line)


if __name__ == "__main__":
    sys.exit(unittest.main())
