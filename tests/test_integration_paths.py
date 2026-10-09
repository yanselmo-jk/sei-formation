"""🔴 **통합 경로**를 실제로 실행하는 회귀 테스트 (critic FIX-THEN-RUN, B-3/B-4).

critic 지적을 그대로 옮긴다:
    "컴포넌트 단위 테스트는 전부 통과했지만 **통합 경로 자체가 한 번도 실행되지 않아**
     놓쳤다. 520개가 통과하는데 두 BLOCKER 가 살아 있었다."

그래서 여기서는 **테스트를 늘리지 않고 경로를 실행한다**:

  B-3  Gaussian 로그 원문 → collect_p1 → evaluate_p1 → status
       (전에는 IRC 만 G16 으로 옮기고 freq 는 ORCA 파서를 부르고 있었다 = '부분 이식'.
        P1 이 1,000 core-h 를 태우고 진짜 TS 를 찾아도 회신은 무조건 fail 이었다.)

  B-4  목(mock) cp2k 를 PATH 에 두고 P2f 를 **실제로 실행**
       (전에는 `SEI_CP2K_BIN` 이라는 어디서도 설정되지 않는 이름을 봐서 CP2K 가 있어도
        항상 exit 3. 개발 박스에 CP2K 가 없어 테스트가 **우연히 정답과 같은 결과**를
        내고 있었다 — **양성 대조군이 없는 테스트는 검증이 아니다.**)

  MAJOR 계산 노드 코어 수 미확정 → 회신의 cores_per_node 가 **null** 인가
       (경고 문자열은 사람만 읽는다. null 은 코드도 읽는다.)
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401
from sei_pilot import collect as collect_mod
from sei_pilot import report as report_mod
from sei_pilot.state import Store

HAVE_BASH = shutil.which("bash") is not None

# 실제 Gaussian 16 `opt=(ts,calcfc) freq` 로그의 골격. 판정에 쓰이는 줄만 남겼다.
G16_TS_LOG = """ Entering Gaussian System, Link 0=g16
 #p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(ts,calcfc,noeigentest) freq

 Standard orientation:
 ---------------------------------------------------------------------
 Center     Atomic      Atomic             Coordinates (Angstroms)
 Number     Number       Type             X           Y           Z
 ---------------------------------------------------------------------
      1          6           0        0.000000    0.000000    0.000000
      2          8           0        1.230000    0.000000    0.000000
      3          1           0       -0.550000    0.940000    0.000000
 ---------------------------------------------------------------------

 SCF Done:  E(RwB97XD) =  -341.123456789     A.U. after   12 cycles

         Item               Value     Threshold  Converged?
 Maximum Force            0.000012     0.000450     YES
 Optimization completed.

 Harmonic frequencies (cm**-1), IR intensities (KM/Mole)
 Frequencies --   -450.1234   112.4000   305.7000
 Frequencies --    620.1000   900.2000  1100.5000

 Sum of electronic and thermal Free Energies=       -341.098765

 Job cpu time:       0 days  1 hours 30 minutes  0.0 seconds.
 Normal termination of Gaussian 16 at Sun Aug 17 12:00:00 2026.
"""


def _irc_log(z_shift):
    """IRC 로그 — 마지막 orientation 블록만 판정에 쓰인다."""
    return """ #p wB97XD/gen irc=(calcfc,forward,maxpoints=30)

 Standard orientation:
 ---------------------------------------------------------------------
 Center     Atomic      Atomic             Coordinates (Angstroms)
 Number     Number       Type             X           Y           Z
 ---------------------------------------------------------------------
      1          6           0        0.000000    0.000000    0.000000
      2          8           0        %.6f    0.000000    0.000000
      3          1           0       -0.550000    0.940000    0.000000
 ---------------------------------------------------------------------

 SCF Done:  E(RwB97XD) =  -341.150000000     A.U. after   10 cycles
 Normal termination of Gaussian 16.
""" % z_shift


class TestGaussianLogReachesP1Verdict(unittest.TestCase):
    """🔴 B-3: Gaussian 로그가 P1 판정까지 **끝까지** 도달하는가."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_int_")
        self.store = Store(self.d)
        self.job_dir = self.store.job_dir("P1")
        self._write("ts_qst2.log", G16_TS_LOG)
        self._write("irc_forward.log", _irc_log(1.23))
        self._write("irc_reverse.log", _irc_log(2.90))   # 확실히 다른 극소
        self._write("ts_method.json",
                    json.dumps({"method": "qst2", "log": "ts_qst2.log",
                                "level": "level2"}))
        self._write("adapter.json", json.dumps({"qc_code": "gaussian16"}))
        # 잡이 정상 종료했다는 상태 마커
        state = os.path.join(self.d, "state")
        os.makedirs(state, exist_ok=True)
        with open(os.path.join(state, "P1.done.json"), "w") as fh:
            json.dump({"key": "P1", "status": "done",
                       "payload": {"start_epoch": 0, "end_epoch": 3600, "rc": 0,
                                   "total_cores": 8, "nodes": 1}}, fh)
        os.makedirs(os.path.join(self.job_dir, "stages"), exist_ok=True)
        with open(os.path.join(self.job_dir, "stages", "ts_qst2.json"), "w") as fh:
            json.dump({"stage": "ts_qst2", "rc": 0, "wall_s": 3600,
                       "total_cores": 8}, fh)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _write(self, name, text):
        with open(os.path.join(self.job_dir, name), "w") as fh:
            fh.write(text)

    def test_frequencies_are_parsed_from_the_gaussian_log(self):
        """전에는 여기서 ([], 'none') 이 나왔고 그래서 판정이 무조건 fail 이었다."""
        res = collect_mod.collect_p1(self.store)
        freq = res["detail"]["freq"]
        self.assertGreater(freq["n_frequencies"], 0,
                           "Gaussian 로그에서 진동수를 못 읽었다 (B-3 재발)")
        self.assertEqual(1, freq["imag_freq_count"])
        self.assertAlmostEqual(-450.1, freq["imag_freq_cm"], places=1)

    def test_parser_used_is_reported_as_gaussian(self):
        res = collect_mod.collect_p1(self.store)
        self.assertEqual("gaussian", res["detail"]["freq_parser"])

    def test_status_is_not_a_false_fail(self):
        """🔴 진짜 TS 인데 fail 로 회신되면 이 패키지의 존재 이유가 무너진다."""
        res = collect_mod.collect_p1(self.store)
        self.assertNotIn("no_frequencies_parsed",
                         json.dumps(res, ensure_ascii=False),
                         "진동수를 못 읽었다는 사유가 남아 있다")
        self.assertNotEqual("fail", res["status"],
                            "허수진동 1개 + 서로 다른 IRC 끝점인데 fail 이다: %s"
                            % res.get("criteria"))

    def test_ts_log_name_is_resolved_from_ts_method_json(self):
        """payload 는 ts_qst2.log 를 쓰는데 수집부는 tsopt.log 를 찾고 있었다."""
        res = collect_mod.collect_p1(self.store)
        self.assertEqual("ts_qst2.log", res["ts_log_used"])

    def test_fallback_log_name_also_works(self):
        os.remove(os.path.join(self.job_dir, "ts_method.json"))
        os.rename(os.path.join(self.job_dir, "ts_qst2.log"),
                  os.path.join(self.job_dir, "ts_opt.log"))
        res = collect_mod.collect_p1(self.store)
        self.assertEqual("ts_opt.log", res["ts_log_used"])

    def test_missing_ts_log_is_reported_not_silently_failed(self):
        os.remove(os.path.join(self.job_dir, "ts_qst2.log"))
        os.remove(os.path.join(self.job_dir, "ts_method.json"))
        res = collect_mod.collect_p1(self.store)
        self.assertIsNone(res["ts_log_used"])
        self.assertTrue(any("TS 로그" in w for w in res.get("warnings") or []))

    def test_hessian_basis_provenance_survives_the_path(self):
        """M2 창의 출처(어느 기저 Hessian 인가)가 회신까지 도달하는가."""
        res = collect_mod.collect_p1(self.store)
        self.assertEqual("gen", res["imag_window"]["hessian_basis"])

    def test_c12_fallback_decision_reaches_the_report_when_present(self):
        """🔴 ADR-090 item 6: `payload/P1.sh` writes `ts_qst2_fallback_decision.json` --
        measured but unread is the same as not measured. This pins the READ side
        (`test_p1_c12_fallback.py` pins the real-bash WRITE side)."""
        decision = {"exit_ok": True, "accepted": False, "fallback_fires": True,
                   "failed_checks": ["exactly_one_imaginary_mode"], "unevaluated_checks": []}
        with open(os.path.join(self.job_dir, "ts_qst2_fallback_decision.json"), "w") as fh:
            json.dump(decision, fh)
        res = collect_mod.collect_p1(self.store)
        self.assertEqual(res["c12_fallback_decision"], decision)
        self.assertTrue(any("c12_fallback_fired" in w for w in res.get("warnings") or []))

    def test_no_fallback_decision_file_leaves_the_field_absent_not_a_crash(self):
        """No file (e.g. a non-Gaussian run, or a P1.sh predating this fix) must not raise."""
        res = collect_mod.collect_p1(self.store)
        self.assertNotIn("c12_fallback_decision", res)
        self.assertEqual("level2", res["imag_window"]["hessian_level"])


# 🔴 P2f 실행 테스트(목 cp2k 양성 대조군)는 P2f 제거와 함께 삭제했다.
#    양성 대조군이라는 **방법**은 유효하다 — CP2K 를 되살릴 때 HANDOFF §17 의
#    MOCK_CP2K 를 그대로 다시 쓰면 된다.


class TestUnresolvedCoresAreNullNotGuessed(unittest.TestCase):
    """🔴 MAJOR: 계산 노드 코어 수를 확정 못 하면 **null** 이어야 한다.

    로그인 24코어가 계산 노드 값으로 넘어가 engineer 의 §R16 한 라운드가 통째로
    그 위에 세워진 사고가 있었다(ADR-034). 경고 문자열은 사람만 읽는다.
    """

    KW = dict(plan=[], plan_summary={}, guard=None, pilots=[], throughput=None,
              queue_wait=[], failures=[])

    def _report(self, node_probe, partitions=()):
        return report_mod.build_report(
            login={"login_cpu": {"physical_cores": 24},
                   "partitions": list(partitions)},
            node_probe=node_probe, **self.KW)

    def test_cores_per_node_is_null_when_only_login_is_known(self):
        rep = self._report({})
        self.assertIsNone(rep["cluster"]["cores_per_node"],
                          "로그인 노드 값이 계산 노드 자리에 앉았다")

    def test_the_login_value_is_preserved_elsewhere(self):
        """버리지는 않는다 — 다만 그 자리에 앉히지 않는다."""
        self.assertEqual(24, self._report({})["cluster"]
                         ["cores_per_node_login_fallback"])

    def test_unresolved_entry_is_raised_as_blocker(self):
        rep = self._report({})
        items = [u for u in rep["unresolved_for_lead"]
                 if u.get("item") == "cluster.cores_per_node"]
        self.assertEqual(1, len(items))
        self.assertEqual("blocker", items[0]["severity"])
        self.assertIn("봉투를 계산하지 마라", items[0]["what"])

    def test_note_explains_why_it_is_null(self):
        note = self._report({})["cluster"]["cores_per_node_note"]
        self.assertIn("의도적으로 null", note)

    def test_compute_probe_value_is_used_when_available(self):
        rep = self._report({"cpu": {"physical_cores": 64}})
        self.assertEqual(64, rep["cluster"]["cores_per_node"])
        self.assertIn("probe_node", rep["cluster"]["cores_per_node_source"])
        self.assertEqual([], [u for u in rep["unresolved_for_lead"]
                              if u.get("item") == "cluster.cores_per_node"])

    def test_partition_value_is_accepted_as_compute_side(self):
        rep = self._report({}, partitions=[{"cores_per_node": 128}])
        self.assertEqual(128, rep["cluster"]["cores_per_node"])
        self.assertIsNone(rep["cluster"]["cores_per_node_note"])

    def test_cp2k_layer_is_not_wired_into_the_package(self):
        """CP2K 층이 **패키지에 배선돼 있지 않은가.**

        🔒 ADR-050 로 의미가 바뀌었다. 사용자 원문:
            *"만약 정말 필요하다면 CP2K 를 추가해도 좋아."*
        ⟹ CP2K 는 이제 **금지가 아니라 조건부 허용**이다. 그러나 조건(U-46 =
        `$CP2K_DATA_DIR` 확인 게이트)이 아직 통과되지 않았으므로 **배선하지 않는다.**
        🔴 게이트 없이 돌리면 CP2K 는 죽지 않고 **조용히 기본값으로 다른 계산을 한다**
        (proposer §37). 그러면 단가는 재는데 **엉뚱한 계산의 단가**다.
        ⟹ P7 스크립트는 `src/experiments/p7_cp2k/` 에 완성돼 있고, 게이트가 통과되면
        `payload/` 로 옮기면 된다. **부분 배선이 가장 나쁘다** — 그래서 전부 아니면 전무다.
        """
        pdir = os.path.join(context.PKG_ROOT, "payload")
        self.assertFalse(os.path.exists(os.path.join(pdir, "cp2k_common.sh")))
        self.assertFalse(os.path.exists(os.path.join(pdir, "P2f.sh")))
        leftovers = []
        for name in sorted(os.listdir(pdir)):
            # probe_* 는 예외다 — 🔴 CP2K **유무 보고**는 일부러 남겼다.
            #    축 3 DFT MD 폴백(proposer §27.3c)에서 되살릴 때 필요하다.
            if not name.endswith(".sh") or name.startswith("probe_"):
                continue
            with open(os.path.join(pdir, name)) as fh:
                code = [l for l in fh if not l.lstrip().startswith("#")]
            if any("cp2k" in l.lower() for l in code):
                leftovers.append(name)
        self.assertEqual([], leftovers,
                         "payload 코드에 CP2K 참조가 남았다 — 게이트(U-46) 통과 전에는 "
                         "배선하지 않는다(ADR-050 조건부 허용).")


if __name__ == "__main__":
    unittest.main()
