"""[U-27] G16 비평형 PCM(`NonEq`) 스모크 — **경로를 실행해서** 검증한다.

critic 구속: "②가 실패해도 P1b 가 사는지 **경로 실행으로** 봐달라."
그래서 목(mock) `g16` 을 PATH 에 놓고 `payload/P1b.sh` 를 **끝까지 돌린다.**

두 가지 목을 쓴다 — 🔴 **양성 대조군과 음성 대조군을 모두 둔다.**
  ACCEPTING : 어떤 route 든 정상 종료 → SMD+NonEq 가 되는 클러스터
  REJECTING : route 에 `smd` + `noneq` 가 같이 있으면 거부 → IEFPCM 폴백이 도는가
  HOSTILE   : 어떤 NonEq 도 거부 → **U-27 이 실패해도 P1b 가 사는가**

(하나만 두면 "되는 것"과 "탐지 로직이 늘 참을 돌려주는 것"을 구별할 수 없다.
 이번 라운드의 B-4 가 정확히 그래서 살아남았다.)
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401

HAVE_BASH = shutil.which("bash") is not None

MOCK_G16 = r"""#!/bin/bash
# 목 g16 — 표준입력으로 .gjf 를 받아 로그를 표준출력으로 낸다(진짜 g16 과 같은 호출 방식).
inp="$(cat)"
route="$(printf '%s' "$inp" | grep -m1 '^#')"
nat="$(printf '%s' "$inp" | awk '/^[A-Z][a-z]? +-?[0-9]/{n++} END{print n+0}')"
lower="$(printf '%s' "$route" | tr 'A-Z' 'a-z')"

reject=0
case "$MOCK_MODE" in
  rejecting) printf '%s' "$lower" | grep -q 'smd' && printf '%s' "$lower" | grep -q 'noneq' && reject=1 ;;
  hostile)   printf '%s' "$lower" | grep -q 'noneq' && reject=1 ;;
esac

echo " Entering Gaussian System, Link 0=g16"
echo "$route"
if [ "$reject" = "1" ]; then
  echo " Unrecognized SCRF keyword combination."
  echo " Error termination via Lnk1e in /opt/g16/l301.exe"
  exit 1
fi
echo " Standard orientation:"
echo " ---------------------------------------------------------------------"
echo " Center     Atomic      Atomic             Coordinates (Angstroms)"
echo " Number     Number       Type             X           Y           Z"
echo " ---------------------------------------------------------------------"
i=0
printf '%s' "$inp" | awk '/^[A-Z][a-z]? +-?[0-9]/{printf "      %d          8           0     %s    %s    %s\n", ++n, $2, $3, $4}'
echo " ---------------------------------------------------------------------"
echo " SCF Done:  E(RwB97XD) =  -76.400000000     A.U. after   9 cycles"
echo "         Item               Value     Threshold  Converged?"
echo " Maximum Force            0.000010     0.000450     YES"
echo " Optimization completed."
echo " Harmonic frequencies (cm**-1), IR intensities (KM/Mole)"
echo " Frequencies --   1600.0000  3700.0000  3800.0000"
echo " Sum of electronic and thermal Free Energies=        -76.350000"
echo " Job cpu time:       0 days  0 hours  1 minutes  0.0 seconds."
echo " Normal termination of Gaussian 16 at Sun Aug 17 12:00:00 2026."
exit 0
"""


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _P1bRun(unittest.TestCase):
    MODE = "accepting"

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_u27_")
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        mock = os.path.join(self.bin, "g16")
        with open(mock, "w") as fh:
            fh.write(MOCK_G16)
        os.chmod(mock, 0o755)
        self.job_dir = os.path.join(self.d, "jobs", "P1b")
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))
        self.proc = self._run()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self):
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": "P1b",
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8",
                    "MOCK_MODE": self.MODE,
                    # ADR-105: 용매 결정 없이는 덱이 나오지 않는다(smoke 에서 전면
                    # 거부). 이 스위트는 U-27 *경로* 를 검증하므로 [FIXTURE] 정책을
                    # 주입해 방출 경로를 연다.
                    "SEI_SOLVENT_POLICY_JSON": context.TEST_SOLVENT_POLICY_JSON,
                    "PATH": self.bin + os.pathsep + env.get("PATH", "")})
        return subprocess.run(
            ["bash", os.path.join(context.PKG_ROOT, "payload", "P1b.sh")],
            env=env, capture_output=True, text=True, timeout=600)

    def u27(self):
        with open(os.path.join(self.job_dir, "u27_noneq.json")) as fh:
            return json.load(fh)


class TestNonEqAccepted(_P1bRun):
    """양성 대조군 — SMD+NonEq 가 되는 클러스터."""

    MODE = "accepting"

    def test_p1b_exits_zero(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-2000:])

    def test_route_is_accepted_and_smd_is_the_model_used(self):
        u = self.u27()
        self.assertTrue(u["route_accepted"])
        self.assertTrue(u["nonequilibrium_supported"])
        self.assertEqual("smd", u["solvent_model_used"])
        self.assertTrue(u["smd_worked"])
        self.assertFalse(u["iefpcm_fallback_needed"])

    def test_the_three_routes_are_recorded(self):
        routes = self.u27()["routes"]
        self.assertIn("NonEq=write", routes["step1"])
        self.assertIn("NonEq=read", routes["step2"])
        self.assertNotIn("NonEq", routes["step3"])   # ③은 평형이다

    def test_indicative_lambda_is_present_but_flagged_as_not_a_verdict(self):
        u = self.u27()
        self.assertIsNotNone(u["lambda_out_hartree_indicative"])
        self.assertIn("proposer", u["_value_caveat"])

    def test_smallest_species_was_used(self):
        """범위 고정: 대상 1종. 크기가 아니라 **중성 + 환원종이 결합 상태**인 것을 고른다."""
        self.assertEqual("ec", self.u27()["species"])

    def test_rt1b_measurements_still_happened(self):
        """U-27 을 얹었다고 본래 5수가 밀려나면 안 된다."""
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "steps")))
        tags = os.listdir(os.path.join(self.job_dir, "steps"))
        self.assertTrue(any("_A_cheap_optfreq" in t for t in tags))
        self.assertTrue(any("_C_high_sp_on_cheap" in t for t in tags))
        self.assertTrue(any("_D_gen_sp" in t for t in tags))


class TestSmdRejectedIefpcmFallback(_P1bRun):
    """SMD+NonEq 만 거부 → IEFPCM 폴백 경로.

    🔴 [ADR-104/105 이후 의미가 바뀌었다] 이전 판의 IEFPCM 폴백은
    `scrf=(iefpcm,solvent=acetonitrile,...)` 을 **하드코딩**했다 — C-5 가 금지하는
    이름-용매 경로의 마지막 생존자. resolve_solvent_line() 은 *_pcm 변형을
    ADR-104 아래 재사양 전까지 거부한다. 그래서 지금 이 시나리오의 올바른 결과는
    "폴백이 iefpcm 으로 돈다"가 아니라 **"폴백 시도가 C-5 로 거부되고, 그 사실이
    기록되고, P1b 는 죽지 않는다"** 다. (재사양은 lead/proposer 판정 대기 — 이
    docstring 이 그 흔적이다.)
    """

    MODE = "rejecting"

    def test_p1b_still_exits_zero(self):
        self.assertEqual(0, self.proc.returncode)

    def test_fallback_attempt_is_refused_not_run_in_a_named_solvent(self):
        u = self.u27()
        self.assertFalse(u["route_accepted"])
        self.assertIsNone(u["solvent_model_used"])
        self.assertFalse(u["smd_worked"])
        self.assertTrue(u["iefpcm_fallback_needed"],
                        "폴백을 시도했는데 그 사실이 회신에 없다")

    def test_no_acetonitrile_deck_was_emitted_anywhere(self):
        """이전 판이라면 u27_pcm/step1.gjf 에 acetonitrile 이 박혀 나갔다 — 재발 방지."""
        for root, _dirs, files in os.walk(self.job_dir):
            for fn in files:
                if fn.endswith(".gjf"):
                    with open(os.path.join(root, fn), errors="replace") as fh:
                        self.assertNotIn("acetonitrile", fh.read(),
                                         "%s 에 이름-용매 덱이 나갔다" % fn)


class TestAllNonEqRejected(_P1bRun):
    """🔴 음성 대조군 — 어떤 NonEq 도 거부. **U-27 이 실패해도 P1b 가 살아야 한다.**"""

    MODE = "hostile"

    def test_p1b_does_not_die(self):
        self.assertEqual(0, self.proc.returncode,
                         "U-27 실패가 P1b 전체를 죽였다")

    def test_verdict_is_negative_not_missing(self):
        u = self.u27()
        self.assertFalse(u["route_accepted"])
        self.assertFalse(u["nonequilibrium_supported"])
        self.assertIsNone(u["solvent_model_used"])

    def test_failure_records_the_step_and_g16_text(self):
        """실패도 데이터다 — 어디서 왜 죽었는지 없으면 회신이 쓸모없다."""
        u = self.u27()
        self.assertEqual(1, u["failed_at_step"])
        self.assertIn("Unrecognized SCRF", u["g16_excerpt"])

    def test_rt1b_measurements_survive_the_u27_failure(self):
        """🔴 U-27 은 부가물이다. 실패해도 본래 목적(단가비)은 남아야 한다."""
        tags = os.listdir(os.path.join(self.job_dir, "steps"))
        self.assertTrue(any("_A_cheap_optfreq" in t for t in tags))
        self.assertTrue(any("stagewise_" in t for t in tags))


class TestCollectorTreatsFailureAsUndetermined(unittest.TestCase):
    """수집부는 U-27 실패를 `undetermined` 로 받는다 (fail 이 아니다)."""

    def setUp(self):
        from sei_pilot.state import Store
        self.d = tempfile.mkdtemp(prefix="sei_u27c_")
        self.store = Store(self.d)
        self.job_dir = self.store.job_dir("P1b")
        os.makedirs(os.path.join(self.d, "state"), exist_ok=True)
        with open(os.path.join(self.d, "state", "P1b.done.json"), "w") as fh:
            json.dump({"key": "P1b", "status": "done",
                       "payload": {"start_epoch": 0, "end_epoch": 60, "rc": 0,
                                   "total_cores": 2, "nodes": 1}}, fh)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _collect(self):
        from sei_pilot import collect as collect_mod
        return collect_mod.collect_p1b(self.store)

    def test_missing_file_is_undetermined_with_a_reason(self):
        res = self._collect()
        self.assertEqual("undetermined", res["u27_noneq"]["status"])
        self.assertIn("why", res["u27_noneq"])

    def test_negative_result_is_undetermined_not_absent(self):
        with open(os.path.join(self.job_dir, "u27_noneq.json"), "w") as fh:
            json.dump({"unresolved_id": "U-27", "route_accepted": False,
                       "nonequilibrium_supported": False}, fh)
        self.assertEqual("undetermined", self._collect()["u27_noneq"]["status"])

    def test_positive_result_is_ok(self):
        with open(os.path.join(self.job_dir, "u27_noneq.json"), "w") as fh:
            json.dump({"unresolved_id": "U-27", "route_accepted": True,
                       "nonequilibrium_supported": True}, fh)
        self.assertEqual("ok", self._collect()["u27_noneq"]["status"])


if __name__ == "__main__":
    unittest.main()
