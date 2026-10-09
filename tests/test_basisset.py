"""동봉 `gen` 기저 — 원소 커버리지 고정 (lead 지시: "🔴 가장 잘 깨지는 지점").

`def2-TZVPPD` / `def2-TZVPD` 는 **G16 내장 키워드가 아니다.** route 에 `gen` 을 쓰고
기저 블록을 입력에 직접 넣는다. 그래서 사전검증의 성격이 바뀐다:

    내장 키워드 : "이 이름이 유효한가"
    gen        : "동봉 블록이 등장 원소를 전부 덮는가"   ← 여기를 고정한다

안 덮으면 G16은 좌표를 다 읽고 SCF 직전에 죽고, 왕복 1회(3.5일)가 날아간다.
"""

import json
import os
import unittest

import context  # noqa: F401
from sei_pilot import basisset, config

REQUIRED = {"C", "H", "O", "Li", "P", "F"}

# 동봉된 .gbs 는 4벌이다:
#   def2-TZVPPD (G-1 주) / def2-TZVPD (G-2 폴백)
#   def2-SVPD   (G-3 composite 의 값싼 층 — ADR-032)
#   def2-TZVPP  (G-4 gen 오버헤드 분리용. 내장 키워드판과 같은 기저)
BASIS_DIR = basisset.default_dir(context.PKG_ROOT)


def _levels():
    cfg = config.load("qc_levels.json", {})
    g = cfg.get("gaussian16") or {}
    # 🔴 gen 을 쓰는 **모든** 레벨을 본다. level3/level4_gen 을 빼먹으면
    #    새 기저의 원소 커버리지가 검사되지 않는다(추가한 그날 깨진다).
    return [(k, v) for k, v in sorted(g.items())
            if k.startswith("level") and isinstance(v, dict)]


class TestBundledBasisFiles(unittest.TestCase):
    def test_both_basis_files_are_bundled(self):
        for name in ("def2-TZVPPD.gbs", "def2-TZVPD.gbs"):
            path = os.path.join(BASIS_DIR, name)
            self.assertTrue(os.path.exists(path), "동봉 기저 파일 없음: %s" % path)
            self.assertGreater(os.path.getsize(path), 1000,
                               "%s 가 너무 작다 — 내려받기가 잘렸을 수 있다" % name)

    def test_every_required_element_is_present_in_every_basis(self):
        """lead 지시: {C,H,O,Li,P,F} 전부 존재하는지 assert."""
        for name in sorted(os.listdir(BASIS_DIR)):
            if not name.endswith(".gbs"):
                continue
            els = set(basisset.parse_elements(basisset.read(
                os.path.join(BASIS_DIR, name))))
            self.assertEqual(set(), REQUIRED - els,
                             "%s 가 덮지 못하는 요구 원소가 있다 (덮는 원소: %s)"
                             % (name, ", ".join(sorted(els))))

    def test_no_ecp_block(self):
        """우리 원소(Z<=15)에는 ECP가 없어야 한다. 있으면 `gen` 만으로는 부족하다."""
        for name in sorted(os.listdir(BASIS_DIR)):
            if name.endswith(".gbs"):
                self.assertFalse(
                    basisset.has_ecp(basisset.read(os.path.join(BASIS_DIR, name))),
                    "%s 에 ECP가 있다 — route 에 pseudo=read 가 필요해진다" % name)

    def test_config_levels_point_at_existing_files(self):
        """config 의 basis_file 경로가 실제로 존재해야 한다(설정과 파일의 이중 진실 방지)."""
        for key, spec in _levels():
            if (spec.get("basis") or "").lower() != "gen":
                continue
            loaded = basisset.load_for_level(spec, context.PKG_ROOT)
            self.assertIsNotNone(loaded, "%s 의 basis_file 이 비었다" % key)
            self.assertIn(spec["basis_real_name"].replace("-", ""),
                          os.path.basename(loaded["path"]).replace("-", ""),
                          "%s: basis_real_name(%s)과 파일명(%s)이 어긋난다"
                          % (key, spec["basis_real_name"], loaded["path"]))

    def test_required_element_list_in_config_matches_the_test(self):
        """설정의 elements_required 와 이 테스트가 어긋나면 둘 중 하나가 낡은 것이다."""
        pol = ((config.load("qc_levels.json", {}).get("gaussian16") or {})
               .get("basis_policy") or {})
        self.assertEqual(REQUIRED, set(pol.get("elements_required") or []),
                         "config/qc_levels.json 의 elements_required 와 테스트가 다르다")


class TestCoverageAgainstBundledInputs(unittest.TestCase):
    """🔴 동봉한 **모든 입력 분자**가 두 기저로 계산 가능해야 한다.

    새 화학종을 추가하면서 기저에 없는 원소(예: S, N)를 들여오는 것이 가장 흔한
    깨짐이다. 종을 추가한 그 순간 여기서 걸린다.
    """

    def _all_xyz(self):
        out = []
        for sub in ("inputs", os.path.join("inputs", "p5_species")):
            d = os.path.join(context.PKG_ROOT, sub)
            if not os.path.isdir(d):
                continue
            for name in sorted(os.listdir(d)):
                if name.endswith(".xyz"):
                    out.append(os.path.join(d, name))
        return out

    def test_there_are_inputs_to_check(self):
        self.assertGreater(len(self._all_xyz()), 5,
                           "검사할 입력 분자를 못 찾았다 — 경로가 바뀌었나?")

    def test_every_bundled_molecule_is_covered_by_every_gen_basis(self):
        for key, spec in _levels():
            if (spec.get("basis") or "").lower() != "gen":
                continue
            text = basisset.load_for_level(spec, context.PKG_ROOT)["text"]
            for path in self._all_xyz():
                els = basisset.elements_in_xyz(open(path).read())
                try:
                    basisset.check_coverage(els, text, context=os.path.basename(path))
                except basisset.BasisError as exc:
                    self.fail("%s(%s) 가 %s 를 덮지 못한다:\n%s"
                              % (key, spec.get("basis_real_name"),
                                 os.path.basename(path), exc))


class TestBlockGeneration(unittest.TestCase):
    def setUp(self):
        self.text = basisset.read(os.path.join(BASIS_DIR, "def2-TZVPPD.gbs"))

    def test_block_filters_to_requested_elements_only(self):
        blk = basisset.block(self.text, only=["C", "H"])
        self.assertEqual(["C", "H"], basisset.parse_elements(blk))
        self.assertEqual(2, blk.count(basisset.SEPARATOR))

    def test_block_preserves_order_of_request(self):
        self.assertEqual(["O", "Li"],
                         basisset.parse_elements(basisset.block(self.text,
                                                                only=["O", "Li"])))

    def test_block_drops_comments(self):
        self.assertNotIn("!", basisset.block(self.text, only=["H"]))

    def test_block_ends_with_separator(self):
        self.assertTrue(basisset.block(self.text, only=["H"]).rstrip().endswith("****"))

    def test_unknown_element_is_silently_absent_not_faked(self):
        """없는 원소를 요청하면 **만들어내지 않는다**(커버리지 검사가 앞에서 막는 몫)."""
        self.assertEqual([], basisset.parse_elements(
            basisset.block(self.text, only=["S"])))


class TestCoverageErrors(unittest.TestCase):
    def setUp(self):
        self.text = basisset.read(os.path.join(BASIS_DIR, "def2-TZVPD.gbs"))

    def test_missing_element_raises_and_names_it(self):
        with self.assertRaises(basisset.BasisError) as cm:
            basisset.check_coverage(["C", "S", "N"], self.text)
        msg = str(cm.exception)
        self.assertIn("S", msg)
        self.assertIn("N", msg)
        self.assertIn("inputs/basis/", msg, "고칠 곳을 알려주지 않는다")

    def test_full_coverage_returns_elements(self):
        self.assertIn("Li", basisset.check_coverage(["C", "H", "Li"], self.text))

    def test_missing_file_raises_with_actionable_message(self):
        with self.assertRaises(basisset.BasisError) as cm:
            basisset.load_for_level({"basis_file": "inputs/basis/없는파일.gbs",
                                     "label": "G-9"}, context.PKG_ROOT)
        self.assertIn("tarball", str(cm.exception))


class TestXyzElements(unittest.TestCase):
    def test_reads_symbols_and_dedups_in_order(self):
        xyz = "3\ncomment\nC 0 0 0\nH 0 0 1\nC 0 1 0\n"
        self.assertEqual(["C", "H"], basisset.elements_in_xyz(xyz))

    def test_normalises_case(self):
        xyz = "2\nc\nLI 0 0 0\nc 0 0 1\n"
        self.assertEqual(["Li", "C"], basisset.elements_in_xyz(xyz))

    def test_respects_atom_count_and_ignores_trailing_junk(self):
        xyz = "1\ncomment\nC 0 0 0\nS 9 9 9\n"
        self.assertEqual(["C"], basisset.elements_in_xyz(xyz))

    def test_bad_header_raises(self):
        with self.assertRaises(basisset.BasisError):
            basisset.elements_in_xyz("not a number\nx\n")


class TestProvenanceRecorded(unittest.TestCase):
    """출처 없는 수치는 폐기 대상이다 — 기저도 마찬가지."""

    def test_config_records_source_and_checksums(self):
        pol = ((config.load("qc_levels.json", {}).get("gaussian16") or {})
               .get("basis_policy") or {})
        self.assertIn("Basis Set Exchange", pol.get("source", ""))
        files = pol.get("files") or {}
        # G-3(SVPD, composite 의 값싼 층) 과 G-4(TZVPP, gen 페널티 분리용) 추가됨
        self.assertEqual({"def2-TZVPPD", "def2-TZVPD", "def2-SVPD", "def2-TZVPP"},
                         set(files))
        for name, meta in files.items():
            self.assertEqual(64, len(meta.get("sha256", "")),
                             "%s 의 sha256 이 없다" % name)

    def test_recorded_checksums_match_the_bundled_files(self):
        import hashlib
        pol = ((config.load("qc_levels.json", {}).get("gaussian16") or {})
               .get("basis_policy") or {})
        for name, meta in (pol.get("files") or {}).items():
            path = os.path.join(context.PKG_ROOT, meta["path"])
            got = hashlib.sha256(open(path, "rb").read()).hexdigest()
            self.assertEqual(meta["sha256"], got,
                             "%s 의 내용이 기록된 체크섬과 다르다 — 파일이 바뀌었는데 "
                             "출처 기록이 갱신되지 않았다" % name)


if __name__ == "__main__":
    unittest.main()
