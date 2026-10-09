"""🔴 빌드 신선도 원장 테스트.

lead가 `dist/*.tar.gz`(16:49)와 `payload/qc_adapter.sh`(17:01)의 mtime을 **우연히 눈으로
비교해서** 낡은 패키지를 잡았다. 그 방식은 다음에 반복되지 않는다 — 자동화하고, 그 자동화가
**실제로 그 상황을 잡는지** 테스트한다.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

import context  # noqa: F401

sys.path.insert(0, os.path.join(context.REPO_ROOT, "src"))
import build_stamp  # noqa: E402

REPO_ROOT = context.REPO_ROOT


class TestBuildStamp(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="sei_stamp_")
        self.src = os.path.join(self.root, "src", "pilot_package")
        os.makedirs(os.path.join(self.src, "payload"))
        self.dist = os.path.join(self.root, "src", "dist")
        os.makedirs(self.dist)
        self._write("payload/a.sh", "echo a\n")
        self._write("run.sh", "echo run\n")
        with open(os.path.join(self.dist, "sei_pilot_cpu.tar.gz"), "wb") as fh:
            fh.write(b"tarball")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def _write(self, rel, text):
        path = os.path.join(self.src, rel)
        with open(path, "w") as fh:
            fh.write(text)

    def _stamp(self):
        import contextlib
        import io
        with contextlib.redirect_stdout(io.StringIO()):
            return build_stamp.main(["write", "--root", self.root,
                                     "--dist", self.dist])

    def test_fresh_build_passes(self):
        self._stamp()
        ok, problems = build_stamp.check(self.root, self.dist)
        self.assertTrue(ok, problems)

    def test_source_edit_after_build_is_detected(self):
        """🔴 lead가 겪은 바로 그 상황."""
        self._stamp()
        self._write("payload/a.sh", "echo a\n# 새 수정\n")
        ok, problems = build_stamp.check(self.root, self.dist)
        self.assertFalse(ok)
        self.assertTrue(any("낡았다" in p for p in problems))
        self.assertTrue(any("payload/a.sh" in p for p in problems))

    def test_it_names_which_files_changed(self):
        """어느 파일이 빠졌는지 지목해야 사람이 판단할 수 있다."""
        self._stamp()
        self._write("payload/b.sh", "echo b\n")
        _ok, problems = build_stamp.check(self.root, self.dist)
        self.assertTrue(any("payload/b.sh" in p for p in problems))

    def test_deleted_file_is_detected(self):
        self._stamp()
        os.remove(os.path.join(self.src, "payload/a.sh"))
        ok, problems = build_stamp.check(self.root, self.dist)
        self.assertFalse(ok)
        self.assertTrue(any("삭제됨" in p for p in problems))

    def test_missing_stamp_is_a_failure_not_a_pass(self):
        """🔴 스탬프가 없다고 통과시키면 이 장치가 무의미해진다."""
        ok, problems = build_stamp.check(self.root, self.dist)
        self.assertFalse(ok)
        self.assertTrue(any("빌드 스탬프가 없다" in p for p in problems))

    def test_touch_without_content_change_does_not_warn(self):
        """mtime이 아니라 **내용 해시**가 기준이다 — 거짓 경고는 사람이 경고를 무시하게 만든다."""
        self._stamp()
        os.utime(os.path.join(self.src, "payload/a.sh"), None)
        ok, _p = build_stamp.check(self.root, self.dist)
        self.assertTrue(ok)

    def test_profile_file_is_excluded(self):
        """빌드가 스스로 쓰는 파일은 제외한다(넣으면 매번 거짓 경고)."""
        self._write("PROFILE", "cpu\n")
        self._stamp()
        self._write("PROFILE", "gpu\n")
        ok, _p = build_stamp.check(self.root, self.dist)
        self.assertTrue(ok)

    def test_tarball_overwritten_after_stamp_is_detected(self):
        self._stamp()
        with open(os.path.join(self.dist, "sei_pilot_cpu.tar.gz"), "wb") as fh:
            fh.write(b"different-size-tarball")
        ok, problems = build_stamp.check(self.root, self.dist)
        self.assertFalse(ok)
        self.assertTrue(any("크기가 스탬프와 다르다" in p for p in problems))

    def test_stamp_file_is_json_with_provenance(self):
        self._stamp()
        with open(os.path.join(self.dist, build_stamp.STAMP)) as fh:
            stamp = json.load(fh)
        for k in ("built_at_utc", "source_digest", "per_file", "tarballs"):
            self.assertIn(k, stamp)

    def test_real_repo_dist_is_fresh(self):
        """실제 저장소: **패키지가 존재한다면** 지금 인도해도 되는 상태인가.

        🔴 clean 빌드 중에는 dist/ 가 비어 있다. 그때 이 테스트가 실패하면
        `make_package.sh` 가 (테스트 → 빌드 순서라서) **영원히 빌드되지 않는다.**
        실제로 그 순환에 걸렸고, 그래서 의미를 정확히 좁힌다:
          - tarball 없음        → skip (빌드 전/중. 판단할 대상이 없다)
          - tarball 있고 스탬프 없음 → **실패** (출처를 모르는 패키지가 인도될 수 있다)
          - 둘 다 있음          → 신선도 비교
        """
        dist = os.path.join(context.REPO_ROOT, "src", "dist")
        if not os.path.isdir(dist):
            self.skipTest("dist 없음 (빌드 전)")
        tarballs = [f for f in os.listdir(dist) if f.endswith(".tar.gz")]
        if not tarballs:
            self.skipTest("빌드된 패키지가 없다 (clean 빌드 중)")
        ok, problems = build_stamp.check(context.REPO_ROOT, dist)
        self.assertTrue(ok, "\n".join(problems))

    def test_tarball_without_stamp_is_a_failure(self):
        """출처를 모르는 패키지를 인도하면 안 된다 — skip 으로 넘기지 않는다."""
        ok, problems = build_stamp.check(self.root, self.dist)   # 스탬프 없음
        self.assertFalse(ok)
        self.assertTrue(any("빌드 스탬프가 없다" in p for p in problems))


if __name__ == "__main__":
    unittest.main()


class TestWrongRootIsNotReportedAsStale(unittest.TestCase):
    """🔴 잘못된 `--root` 를 '소스가 통째로 삭제됐다'로 보고하면 안 된다.

    실제로 `--root src`(한 단계 아래)로 호출했더니 "68개 파일 삭제됨 / tarball 이
    낡았다"는 오경보가 났다. **오경보는 진짜 경보를 믿지 않게 만들기 때문에
    낡은 tarball 보다 더 위험하다.** (lead 가 mtime 으로 판단하게 된 원인이기도 하다.)
    """

    def test_wrong_root_says_wrong_root_not_stale(self):
        import build_stamp
        dist = os.path.join(REPO_ROOT, "src", "dist")
        if not os.path.exists(os.path.join(dist, "BUILD_STAMP.json")):
            self.skipTest("빌드 산출물이 없다")
        ok, problems = build_stamp.check(os.path.join(REPO_ROOT, "src"), dist)
        text = "\n".join(problems)
        self.assertFalse(ok)
        self.assertIn("--root", text)
        self.assertNotIn("tarball 이 현재 소스보다 낡았다", text,
                         "root 오류를 staleness 로 오보하고 있다")
        self.assertIn("잘못됐을 가능성", text)

    def test_correct_root_still_verifies(self):
        import build_stamp
        dist = os.path.join(REPO_ROOT, "src", "dist")
        if not os.path.exists(os.path.join(dist, "BUILD_STAMP.json")):
            self.skipTest("빌드 산출물이 없다")
        ok, problems = build_stamp.check(REPO_ROOT, dist)
        self.assertTrue(ok, "\n".join(problems))


class TestM2DecisionReachesTheTarball(unittest.TestCase):
    """🔴 소스에 있는 것이 **tarball 안에도** 있는가.

    lead 가 낡은 추출본을 보고 "M2 결정이 없다"고 판단한 일이 있었다. 소스만 보는
    검사로는 그 격차를 못 잡는다. tarball 을 실제로 풀어서 본다.
    """

    def _member(self, name):
        import tarfile
        path = os.path.join(REPO_ROOT, "src", "dist", "sei_pilot_cpu.tar.gz")
        if not os.path.exists(path):
            self.skipTest("tarball 이 없다")
        with tarfile.open(path) as tf:
            f = tf.extractfile("sei_pilot_cpu/" + name)
            return f.read().decode()

    def test_m2_provenance_is_in_the_packaged_p1(self):
        text = self._member("sei_pilot/criteria/p1.py")
        self.assertIn("IMAG_WINDOW_PROVENANCE", text)
        self.assertIn("SVPD", text, "값싼 기저 재검토 근거가 패키지에 없다")
        self.assertIn("ADR-032", text)
        self.assertIn("proposer", text, "누가 바꿀 수 있는지가 없다")

    def test_rt1b_is_in_the_packaged_p1b(self):
        text = self._member("payload/P1b.sh")
        self.assertIn("r_composite", text)
        self.assertIn("level4_gen", text)

    def test_account_column_is_in_the_packaged_plan(self):
        self.assertIn('"-A"', self._member("sei_pilot/plan.py"))

    def test_bundled_bases_are_in_the_tarball(self):
        import tarfile
        path = os.path.join(REPO_ROOT, "src", "dist", "sei_pilot_cpu.tar.gz")
        if not os.path.exists(path):
            self.skipTest("tarball 이 없다")
        with tarfile.open(path) as tf:
            names = set(tf.getnames())
        for b in ("def2-TZVPPD", "def2-TZVPD", "def2-SVPD", "def2-TZVPP"):
            self.assertIn("sei_pilot_cpu/inputs/basis/%s.gbs" % b, names)


class TestStampRecordsContentHash(unittest.TestCase):
    """🔴 크기만으로는 **같은 트리임을 증명하지 못한다.**

    lead 가 "critic 이 리뷰한 트리와 사용자에게 가는 트리가 같음을 해시로 못박아야
    한다"고 요구했고, 그 요구가 구멍을 드러냈다 — 스탬프가 size/mtime 만 기록하고
    있었다. 소스가 바뀌어도 tarball 크기는 같을 수 있다.
    """

    def test_real_stamp_records_sha256_for_every_tarball(self):
        path = os.path.join(REPO_ROOT, "src", "dist", "BUILD_STAMP.json")
        if not os.path.exists(path):
            self.skipTest("빌드 산출물이 없다")
        with open(path) as fh:
            stamp = json.load(fh)
        tarballs = stamp.get("tarballs") or {}
        self.assertTrue(tarballs)
        for fn, meta in tarballs.items():
            self.assertEqual(64, len(meta.get("sha256") or ""),
                             "%s 에 sha256 이 없다" % fn)

    def test_recorded_hash_matches_the_file_on_disk(self):
        import hashlib
        dist = os.path.join(REPO_ROOT, "src", "dist")
        path = os.path.join(dist, "BUILD_STAMP.json")
        if not os.path.exists(path):
            self.skipTest("빌드 산출물이 없다")
        with open(path) as fh:
            stamp = json.load(fh)
        for fn, meta in (stamp.get("tarballs") or {}).items():
            with open(os.path.join(dist, fn), "rb") as fh:
                got = hashlib.sha256(fh.read()).hexdigest()
            self.assertEqual(meta["sha256"], got, fn)

    def test_content_change_of_equal_size_is_detected(self):
        """🔴 양성 대조군 — **크기가 같은데 내용만 바뀐** 경우를 잡는가.

        크기 검사만 있던 시절에는 이 조작이 통과했다.
        """
        import build_stamp
        d = tempfile.mkdtemp(prefix="sei_stamp_")
        try:
            dist = os.path.join(d, "src", "dist")
            os.makedirs(dist)
            pkg = os.path.join(d, "src", "pilot_package")
            os.makedirs(pkg)
            with open(os.path.join(pkg, "a.py"), "w") as fh:
                fh.write("x = 1\n")
            tb = os.path.join(dist, "sei_pilot_cpu.tar.gz")
            with open(tb, "wb") as fh:
                fh.write(b"AAAAAAAA")
            build_stamp.main(["write", "--root", d, "--dist", dist])
            ok, _p = build_stamp.check(d, dist)
            self.assertTrue(ok, "방금 쓴 스탬프가 곧바로 실패한다")

            with open(tb, "wb") as fh:          # 같은 크기, 다른 내용
                fh.write(b"BBBBBBBB")
            ok, problems = build_stamp.check(d, dist)
            self.assertFalse(ok, "크기가 같은 내용 변조를 못 잡았다")
            self.assertIn("sha256", "\n".join(problems))
        finally:
            shutil.rmtree(d, ignore_errors=True)
