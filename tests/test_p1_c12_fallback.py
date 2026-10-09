"""🔴 ADR-090 item 6, C-12 — `payload/P1.sh`'s QST2 -> single-ended fallback, run FOR REAL.

THE INCIDENT this fixes (guards.fallback_decision's own docstring, verbatim): the old rule
fired the fallback ONLY if QST2 FAILED TO TERMINATE NORMALLY (`grep -q "Normal termination"`).
QST2 CONVERGED -- to a saddle of the wrong coordinate -- so the fallback never fired and 302
core-h bought a wrong answer (§39.13(a)).

🔴 Real bash + a real `g16` PATH shim, not a Python mock (coder6's convention, already used by
`test_u27_noneq.py` for the same family of incident on `P1b.sh`) -- a mock encodes the failure
mode we already imagined, and P1.sh's own bridge to `guards.fallback_decision` is exactly the
kind of shell/Python boundary a hand-written fixture would let slip past unexercised.

🔴 THREE modes, not one -- a single accepting mock cannot distinguish "the fix works" from
"nothing was checked":
  ACCEPTED       QST2 terminates normally with exactly 1 imaginary mode -> fallback must NOT fire
  WRONG_SADDLE   QST2 terminates normally with 0 imaginary modes (THE INCIDENT SHAPE) -> fallback
                 MUST fire, which the OLD status-only check could never do
  ABNORMAL       QST2 does not terminate normally (the case the OLD check DID catch) -> fallback
                 must STILL fire, so the fix has not regressed the case it used to handle
"""

import json
import os
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401

HAVE_BASH = shutil.which("bash") is not None

#: A route line drives the job type; the mock brands its Standard-orientation geometry from
#: whatever atom lines it is handed on stdin, matching the real .gjf shape P1.sh generates.
MOCK_G16 = r"""#!/bin/bash
inp="$(cat)"
route="$(printf '%s' "$inp" | grep -m1 '^#')"
lower="$(printf '%s' "$route" | tr 'A-Z' 'a-z')"

is_qst2=0
printf '%s' "$lower" | grep -q 'qst2' && is_qst2=1

echo " Entering Gaussian System, Link 0=g16"
echo "$route"

if [ "$is_qst2" = "1" ] && [ "${MOCK_QST2_MODE:-accepted}" = "abnormal" ]; then
  echo " Error termination via Lnk1e in /opt/g16/l301.exe"
  exit 1
fi

echo " Standard orientation:"
echo " ---------------------------------------------------------------------"
echo " Center     Atomic      Atomic             Coordinates (Angstroms)"
echo " Number     Number       Type             X           Y           Z"
echo " ---------------------------------------------------------------------"
printf '%s' "$inp" | awk '/^[A-Z][a-z]? +-?[0-9]/{printf "      %d          8           0     %s    %s    %s\n", ++n, $2, $3, $4}'
echo " ---------------------------------------------------------------------"
echo " SCF Done:  E(RwB97XD) =  -76.400000000     A.U. after   9 cycles"
echo "         Item               Value     Threshold  Converged?"
echo " Maximum Force            0.000010     0.000450     YES"
echo " Optimization completed."
echo " Harmonic frequencies (cm**-1), IR intensities (KM/Mole)"
if [ "$is_qst2" = "1" ] && [ "${MOCK_QST2_MODE:-accepted}" = "wrong_saddle" ]; then
  # 🔴 THE INCIDENT SHAPE: normal termination, but NO imaginary mode at all -- QST2
  # converged to a minimum-ish stationary point, not a genuine first-order saddle.
  echo " Frequencies --   30.0000  60.0000  90.0000"
else
  echo " Frequencies --   -450.1234  60.0000  90.0000"
fi
echo " Sum of electronic and thermal Free Energies=        -76.350000"
echo " Job cpu time:       0 days  0 hours  1 minutes  0.0 seconds."
echo " Normal termination of Gaussian 16 at Sun Aug 17 12:00:00 2026."
exit 0
"""


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _P1Run(unittest.TestCase):
    MOCK_QST2_MODE = "accepted"

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_p1c12_")
        self.bin = os.path.join(self.d, "bin")
        os.makedirs(self.bin)
        mock = os.path.join(self.bin, "g16")
        with open(mock, "w") as fh:
            fh.write(MOCK_G16)
        os.chmod(mock, 0o755)
        self.job_dir = os.path.join(self.d, "jobs", "P1")
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))
        self.proc = self._run()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self):
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": "P1",
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8",
                    "MOCK_QST2_MODE": self.MOCK_QST2_MODE,
                    # ADR-105: 용매 결정 없이는 덱이 나오지 않는다(smoke 에서 전면
                    # 거부). 이 스위트는 C-12 폴백 *경로* 를 검증하므로 [FIXTURE]
                    # 정책을 주입해 방출 경로를 연다.
                    "SEI_SOLVENT_POLICY_JSON": context.TEST_SOLVENT_POLICY_JSON,
                    # [C-8-1] TS 전제조건 게이트가 QST2 앞에 배선됐다 — 인증 기록이
                    # 없으면 P1 은 exit 6 으로 거부한다(그게 게이트의 목적이고, 그
                    # 거부 자체는 test_c8_gate.py 가 지킨다). 이 스위트의 목적은
                    # C-12 폴백이므로 [FIXTURE] 끝단 인증을 주입해 게이트를 지난다.
                    # 판정은 여전히 guard 가 한다 — 데이터 주입이지 우회가 아니다.
                    "SEI_C8_ENDPOINTS_JSON": context.TEST_C8_ENDPOINTS_JSON,
                    "PATH": self.bin + os.pathsep + env.get("PATH", "")})
        return subprocess.run(
            ["bash", os.path.join(context.PKG_ROOT, "payload", "P1.sh")],
            env=env, capture_output=True, text=True, timeout=600)

    def ts_method(self):
        with open(os.path.join(self.job_dir, "ts_method.json")) as fh:
            return json.load(fh)

    def fallback_decision(self):
        with open(os.path.join(self.job_dir, "ts_qst2_fallback_decision.json")) as fh:
            return json.load(fh)


class TestQst2GenuinelyAccepted(_P1Run):
    """🟢 POSITIVE CONTROL — a genuine TS candidate (1 imaginary mode) must NOT trigger the
    fallback. Without this mode, a test that only ever fires the fallback would look identical
    to a fix that always fires it -- coder6's family (i)."""

    MOCK_QST2_MODE = "accepted"

    def test_p1_exits_zero(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-2000:])

    def test_fallback_did_not_fire(self):
        d = self.fallback_decision()
        self.assertTrue(d["accepted"], d)
        self.assertFalse(d["fallback_fires"], d)
        self.assertEqual(d["n_imaginary_modes_observed"], 1)

    def test_ts_method_stayed_qst2(self):
        self.assertEqual(self.ts_method()["method"], "qst2")
        self.assertEqual(self.ts_method()["log"], "ts_qst2.log")
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "ts_opt.log")))


class TestQst2WrongSaddleFiresTheFallback(_P1Run):
    """🔴 THE REGRESSION, reproduced for real: QST2 terminates NORMALLY (the old check would
    have accepted this) but with ZERO imaginary modes -- converged, to the wrong kind of
    stationary point. The acceptance test, not the exit status, must catch this."""

    MOCK_QST2_MODE = "wrong_saddle"

    def test_p1_exits_zero(self):
        """A fired fallback is not a script failure -- it is the correct, cheap recovery."""
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-2000:])

    def test_fallback_fired_and_says_why(self):
        d = self.fallback_decision()
        self.assertFalse(d["accepted"], d)
        self.assertTrue(d["fallback_fires"], d)
        self.assertEqual(d["n_imaginary_modes_observed"], 0)
        self.assertIn("exactly_one_imaginary_mode", d["failed_checks"])
        self.assertTrue(d["exit_ok"],
                        "the primary method exited CLEANLY -- exit_ok=True is exactly the "
                        "incident's shape, and it must not have decided anything")

    def test_ts_method_switched_to_the_fallback(self):
        tm = self.ts_method()
        self.assertEqual(tm["method"], "ts_opt_from_reactant_fallback")
        self.assertEqual(tm["log"], "ts_opt.log")
        self.assertTrue(os.path.exists(os.path.join(self.job_dir, "ts_opt.log")))


class TestQst2AbnormalTerminationStillFiresTheFallback(_P1Run):
    """🔒 The case the OLD status-only check DID handle correctly must still work -- the fix
    must not have regressed the one case it used to catch."""

    MOCK_QST2_MODE = "abnormal"

    def test_p1_exits_zero(self):
        self.assertEqual(0, self.proc.returncode,
                         self.proc.stdout[-2000:] + self.proc.stderr[-2000:])

    def test_fallback_fired(self):
        d = self.fallback_decision()
        self.assertTrue(d["fallback_fires"], d)
        self.assertFalse(d["exit_ok"])
        self.assertIn("normal_termination", d["failed_checks"])

    def test_ts_method_switched_to_the_fallback(self):
        self.assertEqual(self.ts_method()["method"], "ts_opt_from_reactant_fallback")


if __name__ == "__main__":
    unittest.main()
