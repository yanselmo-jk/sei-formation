"""`payload/endpoint_prep.sh` -- ADR-099's two-stage endpoint preparation, real bash execution.

🔴 SCOPE, STATED HONESTLY: Q2 is ruled (rough = same level as tight, §39.38) -- the config
gate that used to block first is gone. What blocks a real bash run in THIS environment now is
the same thing that blocks every other payload script's real run here: no g16/g09/orca/qchem/
psi4 on PATH (`sei_qc_detect` -> "skipped", exit 3) -- see e.g. `test_payload_shell.py`. The
C-5 solvent precheck (`solvent.DESCRIPTORS` is still `{}`) and the C-9 perturbation are BOTH
still unreachable via a full run in this environment, for that reason, so they are tested in
isolation below (extracted verbatim from the shipped script, ADR-042's "build fixtures from
the real generator" convention applied to a shell-embedded heredoc). Real end-to-end coverage
of the stage1 -> budget-check -> stage2 -> budget-check -> F1-extraction pipeline needs an
environment with a real QC engine AND the real EC:EMC descriptors filled in -- see
`HANDOFF_CODER8.md`.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest

import context  # noqa: F401

HAVE_BASH = shutil.which("bash") is not None
SCRIPT = os.path.join(context.PKG_ROOT, "payload", "endpoint_prep.sh")

with open(SCRIPT) as _fh:
    _SCRIPT_TEXT = _fh.read()


def _extract_heredoc_after(marker):
    """The first `<<'PY' ... PY` block whose PRECEDING text contains `marker`. Verbatim from
    the shipped script -- a hand-retyped copy would verify the snippet I imagine, not the one
    that ships (ADR-042)."""
    idx = _SCRIPT_TEXT.index(marker)
    m = re.search(r"<<'PY'\n(.*?)\nPY\n", _SCRIPT_TEXT[idx:], re.S)
    assert m, "no heredoc found after marker %r" % marker
    return m.group(1)


@unittest.skipUnless(HAVE_BASH, "bash 없음")
class _EndpointPrepRun(unittest.TestCase):
    ROLE = "reactant"
    EXTRA_ENV = {}

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_epprep_")
        self.job_dir = os.path.join(self.d, "jobs", "endpoint")
        os.makedirs(self.job_dir)
        os.makedirs(os.path.join(self.d, "state"))
        self.proc = self._run()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def _run(self):
        env = dict(os.environ)
        env.update({"SEI_PKG_ROOT": context.PKG_ROOT, "SEI_WORKDIR": self.d,
                    "SEI_JOB_DIR": self.job_dir, "SEI_KEY": "endpoint",
                    "SEI_TOTAL_CORES": "2", "SEI_NODE_RAM_GB": "8",
                    "SEI_ENDPOINT_ROLE": self.ROLE})
        env.update(self.EXTRA_ENV)
        return subprocess.run(["bash", SCRIPT], env=env, capture_output=True,
                              text=True, timeout=120)

    def terminal_status(self):
        with open(os.path.join(self.job_dir, "terminal_status.json")) as fh:
            return json.load(fh)


class TestNoQcEngineBlocksFirst(_EndpointPrepRun):
    """🔴 REAL, exercisable TODAY: no g16/g09/orca/qchem/psi4 on PATH in this environment --
    the same gate every other payload script's real run hits here (`test_payload_shell.py`).
    Not a constructed failure."""

    def test_exits_with_the_skipped_status(self):
        self.assertEqual(3, self.proc.returncode)
        ts = self.terminal_status()
        self.assertEqual(ts["status"], "skipped")

    def test_nothing_past_the_gate_ran(self):
        """No guess.xyz, no stage logs -- confirms the gate fires BEFORE any G16 work,
        including the C-9 perturbation and the C-5 solvent precheck."""
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "guess.xyz")))
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "solvent_precheck.err")))
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "endpoint_rough.log")))


class TestInvalidRoleIsRejected(_EndpointPrepRun):
    ROLE = "not_a_real_role"

    def test_exits_with_input_error(self):
        self.assertEqual(2, self.proc.returncode)
        ts = self.terminal_status()
        self.assertEqual(ts["status"], "input_error")


class TestMissingInputGeometryIsRefusedDistinctly(_EndpointPrepRun):
    """[U56-2] SEI_ENDPOINT_INPUT_XYZ 가 가리키는 파일이 없으면 **구분된 상태
    (input_missing)로 0 core-h 거부**해야 한다 — 다른 기하 대체·기하 날조가 조용히
    일어나는 경로를 여기서 막는다. (R-C 의 실제 기하는 lead Q1 판정으로 packaging 됐다
    — test_u56_plan_items 가 그 실존·provenance 를 지킨다; 이 테스트는 결손 시의 거부
    방향을 지킨다.)"""

    ROLE = "reactant"
    EXTRA_ENV = {"SEI_ENDPOINT_INPUT_XYZ":
                 "inputs/does_not_exist_yet_supplied_by_pipeline.xyz"}

    def test_exits_with_the_distinct_input_missing_status(self):
        self.assertEqual(2, self.proc.returncode,
                         self.proc.stdout[-800:] + self.proc.stderr[-400:])
        ts = self.terminal_status()
        self.assertEqual(ts["status"], "input_missing")
        self.assertIn("does_not_exist_yet_supplied_by_pipeline.xyz", ts["note"])

    def test_nothing_past_the_gate_ran(self):
        self.assertFalse(os.path.exists(os.path.join(self.job_dir, "guess.xyz")))
        self.assertFalse(os.path.exists(
            os.path.join(self.job_dir, "endpoint_rough.log")))


#: 최소 mock G16 opt 로그 — 기하 1블록 + 최종 SCF 에너지. 선택 heredoc 의 입력 형태.
def _fake_opt_log(energy_hartree):
    return ("\n".join([
        " SCF Done:  E(RwB97XD) =  %.9f     A.U. after   9 cycles" % energy_hartree,
        " Standard orientation:",
        " " + "-" * 69,
        " Center     Atomic      Atomic             Coordinates (Angstroms)",
        " Number     Number       Type             X           Y           Z",
        " " + "-" * 69,
        "      1          8           0     0.0    0.0    0.0",
        "      2          1           0     0.0    0.0    1.0",
        " " + "-" * 69,
        " Optimization completed.",
    ]) + "\n")


class TestDualStartSelectionHeredocInIsolation(unittest.TestCase):
    """[§39.41 / 0.59 eV basin] 이중 시작점 선택 heredoc — 스크립트 원문에서 추출해
    실행한다(ADR-042). 낮은 stage-1 에너지의 basin 이 stage 2 로 가고, 선택 기록이
    남고, 단일 시작점이면 그대로 통과한다."""

    SNIPPET = _extract_heredoc_after("낮은 basin 선택")

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_dual_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _run(self, main_e, alt_e=None):
        import sys
        with open(os.path.join(self.d, "endpoint_rough.log"), "w") as fh:
            fh.write(_fake_opt_log(main_e))
        args = [os.path.join(self.d, "endpoint_rough.log")]
        if alt_e is not None:
            with open(os.path.join(self.d, "endpoint_rough_alt.log"), "w") as fh:
                fh.write(_fake_opt_log(alt_e))
            args.append(os.path.join(self.d, "endpoint_rough_alt.log"))
        env = dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT, SEI_JOB_DIR=self.d,
                   PYTHONPATH=context.PKG_ROOT)
        return subprocess.run([sys.executable, "-c", self.SNIPPET] + args,
                              env=env, capture_output=True, text=True, timeout=60)

    def _selection(self):
        with open(os.path.join(self.d, "start_selection.json")) as fh:
            return json.load(fh)

    def test_lower_basin_wins_and_the_delta_is_recorded(self):
        res = self._run(-76.40, alt_e=-76.45)
        self.assertEqual(0, res.returncode, res.stderr)
        sel = self._selection()
        self.assertEqual("alt_scan_open", sel["selected"])
        self.assertAlmostEqual(1.3606, sel["delta_ev_between_starts"], places=3)
        self.assertTrue(os.path.exists(os.path.join(self.d, "stage1_exit.xyz")))
        self.assertIn("alt_scan_open",
                      open(os.path.join(self.d, "stage1_exit.xyz")).read())

    def test_packaged_start_wins_when_it_is_lower(self):
        """양방향 대조 — 항상 ALT 를 고르는 선택기는 선택기가 아니다."""
        self._run(-76.45, alt_e=-76.40)
        self.assertEqual("packaged", self._selection()["selected"])

    def test_single_start_passes_through_unchanged(self):
        self._run(-76.40)
        sel = self._selection()
        self.assertEqual("packaged", sel["selected"])
        self.assertEqual(1, sel["n_starts"])
        self.assertIsNone(sel["delta_ev_between_starts"])

    def test_one_failed_start_falls_back_to_the_usable_one(self):
        with open(os.path.join(self.d, "endpoint_rough.log"), "w") as fh:
            fh.write(_fake_opt_log(-76.40))
        with open(os.path.join(self.d, "endpoint_rough_alt.log"), "w") as fh:
            fh.write(" Error termination via Lnk1e\n")   # 기하/에너지 없음
        import sys
        env = dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT, SEI_JOB_DIR=self.d,
                   PYTHONPATH=context.PKG_ROOT)
        subprocess.run([sys.executable, "-c", self.SNIPPET,
                        os.path.join(self.d, "endpoint_rough.log"),
                        os.path.join(self.d, "endpoint_rough_alt.log")],
                       env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual("packaged", self._selection()["selected"])


class TestSpinContaminationEmission(unittest.TestCase):
    """[§39.42(a)] ⟨S²⟩ (annihilation 전/후) — 숫자만, 판정 없음 (C-3)."""

    def test_parser_reads_the_g16_annihilation_line(self):
        from sei_pilot.criteria import g16
        text = (" S**2 before annihilation     0.7601,   after     0.7500\n"
                " unrelated\n"
                " S**2 before annihilation     0.7539,   after     0.7500\n")
        rec = g16.parse_s2(text)
        self.assertEqual(2, rec["n_records"])
        self.assertEqual({"before": 0.7539, "after": 0.75}, rec["last"])
        self.assertEqual(0.75, rec["_clean_doublet_reference"])

    def test_empty_log_yields_none_not_a_number(self):
        from sei_pilot.criteria import g16
        self.assertIsNone(g16.parse_s2("")["last"])

    def test_f1_heredoc_actually_calls_the_parser_for_both_stages(self):
        """reach 원칙(ADR-092): 이름 등장이 아니라 **호출**. f1 emission heredoc 이
        parse_s2 를 부르고 두 stage 키를 emit 한다."""
        from test_guard_reach import _called_names_in_heredocs
        self.assertIn("parse_s2", _called_names_in_heredocs(SCRIPT))
        self.assertIn("s2_stage1_rough", _SCRIPT_TEXT)
        self.assertIn("s2_stage2_tight", _SCRIPT_TEXT)


class TestF1EnergyEmission(unittest.TestCase):
    """[§39.124 Ruling 1, corrected A4, critic16 B1] The certified reactant's converged energy
    is a REQUIRED EMISSION in `f1_observables.json` -- `guards.reactant_match`'s energy clause
    has no other structured source to read it from, and critic16 was explicit: not a cross-job
    log re-parse at gate time. Extracted verbatim (ADR-042), same technique as the S^2 tests
    above."""

    SNIPPET = _extract_heredoc_after("F1 observables at convergence")

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_f1_energy_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def _run(self, energy_hartree):
        import sys
        log = os.path.join(self.d, "endpoint_tight.log")
        with open(log, "w") as fh:
            fh.write(_fake_opt_log(energy_hartree))
        out_json = os.path.join(self.d, "f1_observables.json")
        env = dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT, PYTHONPATH=context.PKG_ROOT)
        res = subprocess.run([sys.executable, "-c", self.SNIPPET, log, out_json],
                             env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, res.returncode, res.stderr)
        return json.load(open(out_json))

    def test_the_converged_energy_is_emitted(self):
        out = self._run(-349.620897014)
        self.assertAlmostEqual(-349.620897014, out["energy_hartree"], places=9)

    def test_an_empty_log_yields_none_not_a_number(self):
        import sys
        log = os.path.join(self.d, "endpoint_tight.log")
        with open(log, "w") as fh:
            fh.write(" Error termination via Lnk1e\n")
        out_json = os.path.join(self.d, "f1_observables.json")
        env = dict(os.environ, SEI_PKG_ROOT=context.PKG_ROOT, PYTHONPATH=context.PKG_ROOT)
        res = subprocess.run([sys.executable, "-c", self.SNIPPET, log, out_json],
                             env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(0, res.returncode, res.stderr)
        self.assertIsNone(json.load(open(out_json))["energy_hartree"])


class TestInputOverrideActuallySwapsTheSource(_EndpointPrepRun):
    """양성 대조군: 존재하는 절대경로면 입력 게이트를 지나 **다음** 게이트(이 환경의
    실제 차단 = QC engine 부재, exit 3)까지 간다 — 채널이 죽은 채로 통과하는 것과
    구분한다 (H-2 satisfiability)."""

    ROLE = "reactant"

    def setUp(self):
        d = tempfile.mkdtemp(prefix="sei_epxyz_")
        self.addCleanup(shutil.rmtree, d, True)
        xyz = os.path.join(d, "custom.xyz")
        with open(xyz, "w") as fh:
            fh.write("2\ncustom input via override\nH 0.0 0.0 0.0\nH 0.0 0.0 0.74\n")
        self.EXTRA_ENV = {"SEI_ENDPOINT_INPUT_XYZ": xyz}
        _EndpointPrepRun.setUp(self)

    def test_passes_the_input_gate_and_hits_the_qc_gate(self):
        self.assertEqual(3, self.proc.returncode,
                         self.proc.stdout[-800:] + self.proc.stderr[-400:])
        self.assertEqual("skipped", self.terminal_status()["status"])


class TestSolventPrecheckHeredocInIsolation(unittest.TestCase):
    """The C-5 precheck is unreachable via a real run in this environment (no QC engine on
    PATH -- see this file's module docstring). Extracted and run standalone so its own
    logic -- not just `solvent.py`'s, already covered elsewhere -- is exercised against the
    verbatim shipped snippet."""

    def _run_snippet(self):
        snippet = _extract_heredoc_after("C-5 PRECHECK")
        return subprocess.run(["python3", "-c", snippet],
                              env=dict(os.environ, PYTHONPATH=context.PKG_ROOT,
                                       SEI_PKG_ROOT=context.PKG_ROOT),
                              capture_output=True, text=True, timeout=30)

    def test_it_currently_refuses(self):
        """🔴 REAL, current state (ADR-105 wired): solvent_policy.model is null, so the ONE
        decision point refuses with SolventUndecided (snippet exit 2, the token the script
        maps to terminal_status `solvent_refused`). Not a constructed failure -- what the
        shipped script actually does today."""
        res = self._run_snippet()
        self.assertEqual(2, res.returncode)     # SolventUndecided branch, not descriptors
        self.assertIn("C-5", res.stderr)
        self.assertIn("solvent_policy", res.stderr)

    def test_the_snippet_imports_solvent_not_a_reimplementation(self):
        """ADR-105: the precheck must ask the SAME function qc_adapter asks -- an early call
        of the one decision point, never a second per-payload rule."""
        snippet = _extract_heredoc_after("C-5 PRECHECK")
        self.assertIn("from sei_pilot import solvent", snippet)
        # [S-1] 이 실행의 smoke 가 남긴 ε 실증 기록(runtime_verification)을 같은 결정
        # 지점에 넘긴다 — 두 번째 규칙이 아니라 같은 함수의 데이터 인자다.
        self.assertIn("solvent.resolve_solvent_line(solvent.load_policy(), "
                      "runtime_verification=rv)", snippet)
        self.assertNotIn("solvent.solvent_line()", snippet)


class TestPerturbationHeredocInIsolation(unittest.TestCase):
    """The C-9 perturbation heredoc, extracted verbatim and run against the real shipped
    reactant file -- unreachable via a full script run in this environment (no QC engine, see
    module docstring), so tested directly here (same reasoning as the solvent precheck above)."""

    def setUp(self):
        self.d = tempfile.mkdtemp(prefix="sei_epprep_pert_")
        self.addCleanup(shutil.rmtree, self.d, True)

    def test_perturbs_the_real_reactant_file_reproducibly(self):
        snippet = _extract_heredoc_after("C-9: perturb the guess")
        src = os.path.join(context.PKG_ROOT, "inputs", "li_ec_radical_reactant.xyz")
        out_xyz = os.path.join(self.d, "guess.xyz")
        out_prov = os.path.join(self.d, "prov.json")
        res = subprocess.run(
            ["python3", "-c", snippet, src, out_xyz, out_prov, "7"],
            env=dict(os.environ, PYTHONPATH=context.PKG_ROOT, SEI_PKG_ROOT=context.PKG_ROOT),
            capture_output=True, text=True, timeout=30)
        self.assertEqual(0, res.returncode, res.stderr)
        self.assertTrue(os.path.exists(out_xyz))
        prov = json.load(open(out_prov))
        self.assertTrue(prov["applied"])

    def test_it_calls_the_real_guard_not_a_reimplementation(self):
        snippet = _extract_heredoc_after("C-9: perturb the guess")
        self.assertIn("guards.perturb_out_of_plane", snippet)


if __name__ == "__main__":
    unittest.main()
