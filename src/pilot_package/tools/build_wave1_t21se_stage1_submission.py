#!/usr/bin/env python3
"""S3 wave-1, attempt 1: T21-se STAGE 1 ONLY (R-C, 21-atom, single-ended relaxed scan) -- the
staged/circuit-breaker protocol (02_METHOD_SPEC.md §39.136 addendum; 03_COMPUTE_PLAN.md
§R39.88 §3/§R39.89/§R39.91): stage 1 (the relaxed scan) is submitted ALONE. Stages 2-5
(refine/ts_opt/IRC/B+) are genuinely unpriced (§R39.89: "T21-se stages 2-5 remain genuinely
unpriced -- no number exists for them and none should be manufactured") and are sized and
built ONLY after stage 1's real result returns -- a human decision gate, not an automatic
continuation. If stage 1 hits its wall cap without finishing, the pre-registered decision
(wave1_2026-08-25/attempts_manifest.json, slot 1) is STOP AND RE-SCOPE, not resubmit bigger.

WHY THIS IS THE FIRST-EVER PRODUCTION SUBMISSION OF R-C's U56 SCAN: `U56_RC_scan` was never
wired into `plan.py` -- see that file's own comment at line 527-528: "U56_RC_scan (T21-se)는
여기 없다 -- §39.41(d) 컷... S3 wave 1로 이동, 삭제 아님" (cut for cost reasons, moved to S3
wave 1, not deleted). This tool follows the SAME construction pattern as
`build_wave1_rb_submission.py` (its own sibling, read that tool's docstring for the full
reasoning on why this replicates `sei_pilot.scheduler`'s own PbsAdapter rendering rather than
re-implementing deck-building): a `sei_pilot.scheduler.JobSpec` shaped exactly like what
`cli.py`'s `build_common_env`/`build_spec` would produce for a `U56_RC_scan`-class Item, using
`payload/U56.sh`'s EXISTING R-A/R-B code paths (R-C is already a valid `SEI_U56_REACTION` value
-- `payload/U56.sh` validates against `R-A|R-B|R-C`, confirmed by grep, not assumed) -- no new
deck-building logic, no new plan.py Item (same scoped decision as R-B's tool: reuse the
harness's own wrapper generation without touching the release-gate/guard-reservation state
machine).

STAGE-1-ONLY MECHANISM: `SEI_U56_STOP_AFTER=u56_scan` (proposer13's §39.136 fifth-addendum
ruling, landed in `payload/U56.sh` this round) -- U56.sh runs its scan stage exactly as it
would for a full attempt, then stops cleanly (status `stopped_after_stage`, cause_class
`staged` per §39.138/§39.139, never auto-retried) instead of continuing to ts_opt/IRC. This is
an ADDITIVE flag on the SAME payload every other U56 attempt uses, not a separate script.

WALL CAP / COST -- point-density-adjusted circuit breaker, NOT a cost prediction (engineer14,
§R39.89/§R39.91): R-C's DFT scan needs fine spacing near the GFN2-measured discontinuity
(d(O2-C3)~1.7-1.8 Angstrom) that R-A's coarser grid didn't need -- a POINT-COUNT question, not
an atom-count one. R-A's own scan+refine used 22 points for 142.07 core-h (6.46 core-h/point,
MEASURED). R-C's own point count is CONFIRMED at ~40-41 (§R39.91: "R-C point count now
CONFIRMED ~40-41 (matches my point-density-adjusted option (ii) almost exactly: 41/22 = 1.86x
vs my estimated 1.86x)") -- USING THE CONFIRMED FIGURE: wall cap 22.3h, worst-case exposure
1,428 core-h at 64 cores (1428/22.3 = 64.04, matching R-A/R-B's own core count). This is an
UPPER-BOUND circuit breaker sized off a point-count ratio, not a forecast of real spend (R-A's
own real spend, 294.65 core-h, was far below its 700 core-h reservation ceiling -- §R39.90 §1).

🔴 [ASSUMPTION] `--pkg-root`/`--workdir`/`--qc-module`/`--qc-login-path` default to the SAME
confirmed-real values `build_wave1_rb_submission.py` uses (the only known-good deployment/
QC-detection data point on record for this user's cluster) -- verify before trusting if the
deployment path or QC module has changed.

This is diagnostic-staging only: NOT wired into any plan Item, does not submit anything.

Usage:
    python3 tools/build_wave1_t21se_stage1_submission.py --out-dir /path/to/wave1_t21se_2026-08-25
"""

import argparse
import json
import os
import sys

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG_ROOT)

from sei_pilot import scheduler as sched_mod  # noqa: E402
from sei_pilot import shellrun, version  # noqa: E402
from sei_pilot.state import makedirs  # noqa: E402

#: 🟢 [plan.py:452/527-528, traced directly] R-C's own ruled method: single-ended relaxed
#: scan (T21-se) -- the same method R-A/R-B already validated, not a new one. Job key follows
#: plan.py's own reserved-but-never-wired name (`U56_RC_scan`, see its comment at line 527-528).
REACTION = "R-C"
METHOD = "relaxed_scan"
REACTANT_ENDPOINT_KEY = "endpoint_prep_rc_reactant"   # plan.py:452, the R-C 21-atom endpoint

#: 🟢 [same confirmed-real deployment/QC-detection data point build_wave1_rb_submission.py
#: uses -- the only one on record for this user's cluster]
DEFAULT_PKG_ROOT = "/scratch/q656a01/calculation_time_test_pilot/sei_pilot_cpu"
DEFAULT_WORKDIR = DEFAULT_PKG_ROOT + "/sei_pilot_work"
DEFAULT_QC_MODULE = "gaussian/g16.c01.linda"
DEFAULT_QC_LOGIN_PATH = "/apps/commercial/G16/g16.linda.c01/g16"
DEFAULT_QC_LEVEL = "2"   # G-1, wB97XD/def2-TZVPPD -- matches R-A/R-B's own level
DEFAULT_PARTITION = "normal"
DEFAULT_ACCOUNT = "gaussian"

#: 🟢 [03_COMPUTE_PLAN.md §R39.91, "Final slate"] "R-C point count now CONFIRMED ~40-41 ...
#: wall cap 22.3h, worst-case exposure 1,428 core-h [ESTIMATE, point-count-ratio-adjusted
#: circuit-breaker, not a cost prediction]." 1428/22.3 = 64.04 cores -> 64, matching R-A/R-B.
DEFAULT_WALL_H = 22.3
DEFAULT_CORES = 64

#: 🔴 [proposer13, §39.136 fifth addendum; payload/U56.sh's own `_sei_u56_stop_after_check`]
#: the staged-circuit-breaker mechanism this whole tool exists to exercise -- stops cleanly
#: after the scan stage, status `stopped_after_stage` (cause_class `staged`, never retried,
#: §39.138/§39.139), instead of continuing into stages this round did not authorize pricing for.
STOP_AFTER_STAGE = "u56_scan"


def build(out_dir, key="U56_RC_scan_wave1", pkg_root=DEFAULT_PKG_ROOT,
         workdir=None, qc_module=DEFAULT_QC_MODULE, qc_login_path=DEFAULT_QC_LOGIN_PATH,
         qc_level=DEFAULT_QC_LEVEL, partition=DEFAULT_PARTITION, account=DEFAULT_ACCOUNT,
         wall_h=DEFAULT_WALL_H, cores=DEFAULT_CORES, stop_after_stage=STOP_AFTER_STAGE):
    os.makedirs(out_dir, exist_ok=True)
    workdir = workdir or (pkg_root + "/sei_pilot_work")
    job_dir_remote = "%s/jobs/%s" % (workdir, key)

    # 🟢 [cli.py:770-787 build_common_env / 790-807 qc_env_for_jobs, same fields
    # build_wave1_rb_submission.py already traced -- reused unchanged here]
    common_env = {
        "SEI_PKG_ROOT": pkg_root,
        "SEI_WORKDIR": workdir,
        "SEI_PARTITION": partition,
        "SEI_QC_LEVEL": qc_level,
    }
    qc_env = {}
    if qc_module:
        qc_env["SEI_QC_MODULE"] = qc_module
    if qc_login_path:
        qc_env["SEI_QC_LOGIN_PATH"] = qc_login_path

    job_env = dict(common_env)
    job_env.update(qc_env)
    job_env["SEI_ITEM"] = key
    job_env["SEI_WALL_H"] = "%.4f" % wall_h
    job_env["SEI_U56_REACTION"] = REACTION
    job_env["SEI_U56_METHOD"] = METHOD
    job_env["SEI_U56_REACTANT_ENDPOINT_KEY"] = REACTANT_ENDPOINT_KEY
    if stop_after_stage:
        job_env["SEI_U56_STOP_AFTER"] = stop_after_stage

    # 🔴 [local-build/remote-run path split -- same reasoning as build_wave1_rb_submission.py]
    spec = sched_mod.JobSpec(
        key, "bash %s/payload/U56.sh" % pkg_root,
        nodes=1, cores_per_node=cores, wall_h=wall_h, partition=partition,
        job_dir=job_dir_remote,
        env=job_env, modules=[qc_module] if qc_module else [],
        emit_stdio_lines=False, account=account, logical_key=key)

    template_dir = os.path.join(PKG_ROOT, "sei_pilot", "templates")
    adapter = sched_mod.PbsAdapter(shellrun.Shell(), template_dir, flavor="pbspro")

    resource = "#PBS -l select=%d:ncpus=%d:mpiprocs=%d" % (
        spec.nodes, spec.cores_per_node, spec.cores_per_node)
    extra = {"RESOURCE_LINE": resource, "MODULE_LINES": spec.module_block()}
    if spec.partition:
        extra["PARTITION_LINE"] = "#PBS -q %s" % spec.partition
    if spec.account:
        extra["ACCOUNT_LINE"] = "#PBS -A %s" % spec.account
    qsub_text = sched_mod.squeeze_directive_blanks(
        sched_mod.render_script(adapter._template("pbs.sh.tmpl"), spec, extra))

    # 🔴 [lead, wave-1 review items 3/5 -- generated qsub only, common.sh wiring deferred]
    # deployed-package fingerprint guard, same shape/reasoning as build_wave1_rb_submission.py's
    # own copy -- see that tool's comment. This IS the item SEI_U56_STOP_AFTER most needs: a
    # stale deployed U56.sh has no idea what SEI_U56_STOP_AFTER means and would silently run
    # stages 2-5 unauthorized. Reuses common.sh's own sei_pkg_fingerprint() (workdir-aware
    # extra_exclude, critic17's pre-build note), inserted right after common.sh is sourced.
    expected_fingerprint = version.package_fingerprint(PKG_ROOT)
    anchor = '. "${SEI_PKG_ROOT}/payload/common.sh"\n'
    if anchor not in qsub_text:
        raise RuntimeError("pbs.sh.tmpl's common.sh source line not found where expected -- "
                           "the fingerprint guard's insertion point assumption is stale")
    fingerprint_guard = (
        "SEI_EXPECTED_PKG_FINGERPRINT=\"%s\"\n"
        "SEI_ACTUAL_PKG_FINGERPRINT=\"$(sei_pkg_fingerprint)\"\n"
        "if [ \"$SEI_ACTUAL_PKG_FINGERPRINT\" != \"$SEI_EXPECTED_PKG_FINGERPRINT\" ]; then\n"
        "  echo \"[FATAL] deployed package fingerprint "
        "($SEI_ACTUAL_PKG_FINGERPRINT) != expected ($SEI_EXPECTED_PKG_FINGERPRINT) at "
        "$SEI_PKG_ROOT. Two known false-alarm causes, check these BEFORE assuming a real "
        "mismatch: (1) SEI_WORKDIR renamed away from the default sei_pilot_work under a "
        "non-default --workdir, (2) a stray .py/.sh/.tmpl/.inp/.xyz/.json file was added "
        "directly under the package root outside sei_pilot_work/. If neither applies, "
        "SEI_U56_STOP_AFTER would be silently ignored by old code and stages 2-5 "
        "(unauthorized, unpriced) would run. Rebuild+redeploy the package, then resubmit. "
        "Refusing to run.\" >&2\n"
        "  exit 9\n"
        "fi\n" % expected_fingerprint)
    qsub_text = qsub_text.replace(anchor, anchor + fingerprint_guard, 1)

    makedirs(out_dir)
    qsub_path = os.path.join(out_dir, key + ".qsub")
    cmd_path = os.path.join(out_dir, key + ".cmd.sh")
    new_qsub_text = qsub_text
    new_cmd_text = ("#!/bin/bash\n# sei_pilot payload command (%s)\nset -u\n%s\n"
                    % (key, spec.command))
    if os.path.exists(qsub_path) or os.path.exists(cmd_path):
        old_qsub = open(qsub_path).read() if os.path.exists(qsub_path) else None
        old_cmd = open(cmd_path).read() if os.path.exists(cmd_path) else None
        if old_qsub != new_qsub_text or old_cmd != new_cmd_text:
            sys.stderr.write(
                "refusing to overwrite %s/%s.{qsub,cmd.sh} -- a rebuild with a DIFFERENT spec "
                "would silently change an existing staged pair. Remove the existing files or "
                "pick a new --out-dir if a clean rebuild is really wanted.\n" % (out_dir, key))
            return 5

    with open(qsub_path, "w") as fh:
        fh.write(new_qsub_text)
    os.chmod(qsub_path, 0o755)
    with open(cmd_path, "w") as fh:
        fh.write(new_cmd_text)
    os.chmod(cmd_path, 0o755)

    manifest = {
        "purpose": "S3 wave-1 attempt 1: T21-se STAGE 1 ONLY (R-C, single-ended relaxed scan, "
                  "21 atoms) -- staged/circuit-breaker protocol (02_METHOD_SPEC.md §39.136 "
                  "addendum; 03_COMPUTE_PLAN.md §R39.88 §3/§R39.89/§R39.91). Stages 2-5 are "
                  "genuinely unpriced and NOT built by this tool -- a human decision gate on "
                  "stage 1's real result comes first. NOT submitted by this script.",
        "reaction": REACTION, "method": METHOD,
        "reactant_endpoint_key": REACTANT_ENDPOINT_KEY,
        "job_key": key,
        "job_dir_remote": job_dir_remote,
        "stage_limit": {
            "mechanism": "SEI_U56_STOP_AFTER=%s" % stop_after_stage if stop_after_stage else None,
            "note": "payload/U56.sh stops cleanly right after its own u56_scan sei_stage call "
                   "(status stopped_after_stage, cause_class staged per §39.138/§39.139 -- "
                   "never auto-retried) instead of continuing to refine/ts_opt/IRC/B+.",
        },
        "wall_cap_basis": "03_COMPUTE_PLAN.md §R39.91: R-C's confirmed ~40-41 scan points "
                         "(1.86x R-A's 22-point anchor) -> 22.3h wall / 1,428 core-h "
                         "point-count-ratio-adjusted circuit breaker, NOT a cost prediction. "
                         "If stage 1 hits this cap without finishing, the pre-registered "
                         "decision (attempts_manifest.json slot 1) is STOP AND RE-SCOPE, not "
                         "resubmit with a bigger cap.",
        "reused_from": "same production harness that built U56_RA_scan/U56_RB_scan "
                       "(payload/U56.sh via sei_pilot.scheduler.PbsAdapter.write_script) -- "
                       "R-C is an existing valid SEI_U56_REACTION value in U56.sh already, no "
                       "new deck-building logic",
        "assumptions_not_independently_verified": {
            "pkg_root": pkg_root, "workdir": workdir, "qc_module": qc_module,
            "qc_login_path": qc_login_path,
            "_source": "same confirmed-real deployment/QC-detection data point "
                      "build_wave1_rb_submission.py's own manifest uses -- verify before "
                      "trusting if the deployment path or QC module has changed",
        },
        "deployed_package_fingerprint_check": {
            "expected": expected_fingerprint,
            "note": "qsub refuses to run (exit 9) if $SEI_PKG_ROOT's own recomputed "
                   "package_fingerprint (via common.sh's sei_pkg_fingerprint(), same "
                   "workdir-aware exclusion logic it already uses) doesn't match this -- "
                   "catches a stale deployment before it silently ignores SEI_U56_STOP_AFTER "
                   "and runs stages 2-5 unauthorized.",
        },
        "wall_h": wall_h, "cores": cores,
        "qsub_file": os.path.basename(qsub_path),
        "cmd_file": os.path.basename(cmd_path),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("[build_wave1_t21se_stage1_submission] wrote %s" % qsub_path)
    print("[build_wave1_t21se_stage1_submission] wrote %s" % cmd_path)
    print("[build_wave1_t21se_stage1_submission] STAGE 1 ONLY (SEI_U56_STOP_AFTER=%s) -- "
          "stages 2-5 need a separate build after this stage's real result returns."
          % stop_after_stage)
    print("[build_wave1_t21se_stage1_submission] NOT SUBMITTED. Verify pkg_root/workdir/"
          "qc_module/qc_login_path in manifest.json's assumptions_not_independently_verified "
          "before trusting this deck -- see this tool's own docstring.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--key", default="U56_RC_scan_wave1")
    ap.add_argument("--pkg-root", default=DEFAULT_PKG_ROOT)
    ap.add_argument("--workdir", default=None, help="default: <pkg-root>/sei_pilot_work")
    ap.add_argument("--qc-module", default=DEFAULT_QC_MODULE)
    ap.add_argument("--qc-login-path", default=DEFAULT_QC_LOGIN_PATH)
    ap.add_argument("--qc-level", default=DEFAULT_QC_LEVEL)
    ap.add_argument("--partition", default=DEFAULT_PARTITION)
    ap.add_argument("--account", default=DEFAULT_ACCOUNT)
    ap.add_argument("--wall-h", type=float, default=DEFAULT_WALL_H)
    ap.add_argument("--cores", type=int, default=DEFAULT_CORES)
    ap.add_argument("--stop-after-stage", default=STOP_AFTER_STAGE,
                    help="value for SEI_U56_STOP_AFTER; empty string disables the stage limit "
                        "(NOT recommended for this round -- stages 2-5 are unpriced)")
    args = ap.parse_args(argv)
    return build(args.out_dir, args.key, args.pkg_root, args.workdir, args.qc_module,
                args.qc_login_path, args.qc_level, args.partition, args.account,
                args.wall_h, args.cores, args.stop_after_stage)


if __name__ == "__main__":
    sys.exit(main())
