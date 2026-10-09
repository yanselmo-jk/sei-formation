#!/usr/bin/env python3
"""S3 wave-1, attempt 2: R-B redo (single-ended relaxed scan -> ts_opt -> IRC fwd/rev), the
FULL production chain, via the SAME production harness machinery that already ran
`U56_RA_scan`/`U56_RB_scan` -- NOT a new deck-building tool (02_METHOD_SPEC.md §39.136(1)/(2),
03_COMPUTE_PLAN.md §R39.88/89).

WHY THIS IS A REDO, NOT A NEW BUILD: `U56_RB_scan`'s candidate was REJECTED (ADR-116, three
independent legs: mode character, non-distinct minimum, break-bond overshoot), but R-B's
CHEMISTRY was not -- the rejection was of one search method's output, not the reaction
(§39.136(1)). R-B's own original chain already used the now-validated single-ended relaxed-scan
method (confirmed directly from its own route line, `scan.gjf`: `opt=(modredundant,...)`, no
QST2 anywhere) -- this redo reuses that SAME method, current `src/` conventions, a fresh job
key/directory (never touching the original rejected `U56_RB_scan` job dir).

HOW THIS DIFFERS FROM EVERY OTHER TOOL BUILT THIS ROUND: `U56_RA_scan`/`U56_RB_scan` were never
built by a standalone deck-building script -- they ran through the real production harness (a
generated `.qsub`/`.cmd.sh` pair invoking `payload/U56.sh`, which builds the actual scan/ts_opt/
IRC `.gjf` decks itself AT RUNTIME on the compute node via `qc_adapter.sh`). Re-implementing
that deck-building logic here would risk drifting from the validated production path. Instead,
this tool constructs a `sei_pilot.scheduler.JobSpec` with EXACTLY the shape
`sei_pilot.cli.build_spec()` would produce for a `U56_RB_scan`-class plan Item (traced directly
from `sei_pilot/plan.py`'s own `U56_RB_scan` Item definition and `cli.py`'s `build_common_env`/
`build_spec`), then calls the SAME `PbsAdapter.write_script()` the harness itself uses --
build-only, no `submit()` call anywhere in this tool or the code path it calls. This was a
scoped decision (team-lead, not this coder's own guess): reuse the harness's own submission-
wrapper generation directly via `sei_pilot.scheduler`, WITHOUT adding a new Item to `plan.py`
(which would touch the release-gate/guard-reservation state machine) and WITHOUT running
`./run.sh --emit-script` (which requires a live cluster QC-engine probe this workstation cannot
perform).

RULED PRODUCTION DEFAULT NOW WIRED (§39.136(2), landed in `config/qc_levels.json` in the same
pass as this tool): `irc_forward`/`irc_reverse` now carry `recorrect=never` as the project-wide
default for every fresh IRC job -- this redo picks it up automatically via `qc_adapter.sh`,
nothing to set here. `StepSize=2`/`f=0.20` is deliberately NOT adopted as a blanket default --
escalate a SPECIFIC direction only if that direction's own IRC shows a `Bulirsch-Stoer... not
Converging` warning (a post-run read, not something this build can pre-decide).

🔴 [ASSUMPTION] `--pkg-root`/`--workdir` default to the exact absolute paths recorded in the
ORIGINAL `U56_RB_scan.qsub` (`/scratch/q656a01/calculation_time_test_pilot/sei_pilot_cpu[/
sei_pilot_work]`) -- the only confirmed-real deployment location on record for this user's
cluster. `SEI_QC_MODULE`/`SEI_QC_LOGIN_PATH` default to that same qsub's own recorded values
(the last confirmed-working QC-engine detection on this cluster) since this tool has no live
cluster to re-probe. **If the rebuilt package is deployed at a different path, or the QC module
name has changed, these four values must be overridden via CLI flags before this deck is
trusted** -- the generated `.qsub` is only as good as these inputs, and this tool cannot verify
them independently.

This is diagnostic-staging only: NOT wired into any plan Item, does not submit anything.
Re-running into the SAME `--out-dir` is NOT idempotent by default -- `write_script`/
`write_cmd_file` overwrite unconditionally (this mirrors the harness's own emit-script
behavior, which is itself idempotent by DESIGN -- re-emitting the identical spec produces byte-
identical output); this tool adds one guard beyond that: refuse if the target files already
exist with DIFFERENT content, so an accidental re-run with a changed spec does not silently
replace what may already be in flight.

Usage:
    python3 tools/build_wave1_rb_submission.py --out-dir /path/to/wave1_rb_redo_2026-08-25
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

#: 🟢 [sei_pilot/plan.py:514-526, `U56_RB_scan` Item -- traced directly, not re-derived]
#: R-B's own ruled method: single-ended relaxed scan, reactant cert shared with R-A.
REACTION = "R-B"
METHOD = "relaxed_scan"
REACTANT_ENDPOINT_KEY = "endpoint_prep_reactant"

#: 🟢 [ORIGINAL `U56_RB_scan.qsub`, confirmed-real values from this user's own returned
#: cluster script -- the only known-good deployment/QC-detection data point on record]
DEFAULT_PKG_ROOT = "/scratch/q656a01/calculation_time_test_pilot/sei_pilot_cpu"
DEFAULT_WORKDIR = DEFAULT_PKG_ROOT + "/sei_pilot_work"
DEFAULT_QC_MODULE = "gaussian/g16.c01.linda"
DEFAULT_QC_LOGIN_PATH = "/apps/commercial/G16/g16.linda.c01/g16"
DEFAULT_QC_LEVEL = "2"   # G-1, wB97XD/def2-TZVPPD -- matches U56_RA_scan/U56_RB_scan's own level
DEFAULT_PARTITION = "normal"
DEFAULT_ACCOUNT = "gaussian"

#: 🟢 [engineer14 §R39.88/89, 03_COMPUTE_PLAN.md] R-A's own full end-to-end chain (scan through
#: B+ forward, plus a possibly-crashing reverse arm) took 10h56m wall in the original
#: U56_RB_scan.qsub (SEI_WALL_H=10.9375) and completed within it (all stages' .log files
#: present in the returned tree -- not wall-killed). Reused unchanged here: same reaction
#: class, same job shape, and §39.136(2)'s recorrect=never default is confirmed no cost
#: pushback (§R39.89) -- if anything cheaper in the no-crash case, never more expensive.
DEFAULT_WALL_H = 10.9375
DEFAULT_CORES = 64


def build(out_dir, key="U56_RB_scan_wave1", pkg_root=DEFAULT_PKG_ROOT,
         workdir=None, qc_module=DEFAULT_QC_MODULE, qc_login_path=DEFAULT_QC_LOGIN_PATH,
         qc_level=DEFAULT_QC_LEVEL, partition=DEFAULT_PARTITION, account=DEFAULT_ACCOUNT,
         wall_h=DEFAULT_WALL_H, cores=DEFAULT_CORES):
    os.makedirs(out_dir, exist_ok=True)
    workdir = workdir or (pkg_root + "/sei_pilot_work")
    job_dir_remote = "%s/jobs/%s" % (workdir, key)   # the path AS THE CLUSTER WILL SEE IT

    # 🟢 [cli.py:770-787 build_common_env, traced field-for-field] common env every job gets.
    common_env = {
        "SEI_PKG_ROOT": pkg_root,
        "SEI_WORKDIR": workdir,
        "SEI_PARTITION": partition,
        "SEI_QC_LEVEL": qc_level,
    }
    # 🟢 [cli.py:790-807 qc_env_for_jobs, traced field-for-field]
    qc_env = {}
    if qc_module:
        qc_env["SEI_QC_MODULE"] = qc_module
    if qc_login_path:
        qc_env["SEI_QC_LOGIN_PATH"] = qc_login_path

    job_env = dict(common_env)
    job_env.update(qc_env)
    job_env["SEI_ITEM"] = key
    job_env["SEI_WALL_H"] = "%.4f" % wall_h
    # 🟢 [plan.py:523-524, U56_RB_scan Item's own extra_env, unchanged]
    job_env["SEI_U56_REACTION"] = REACTION
    job_env["SEI_U56_METHOD"] = METHOD
    job_env["SEI_U56_REACTANT_ENDPOINT_KEY"] = REACTANT_ENDPOINT_KEY

    # 🔴 job_dir MUST be the REMOTE cluster path here, not this tool's local --out-dir -- it
    # feeds SEI_JOB_DIR/STDOUT/STDERR/CMD_FILE inside the rendered script (render_script's own
    # substitution dict). This tool runs on a workstation with no cluster filesystem, so the
    # generated files still need to be WRITTEN locally to --out-dir -- see below, where the
    # write target is deliberately NOT spec.job_dir (the normal write_script()/write_cmd_file()
    # behavior), by construction, not by accident.
    spec = sched_mod.JobSpec(
        key, "bash %s/payload/U56.sh" % pkg_root,
        nodes=1, cores_per_node=cores, wall_h=wall_h, partition=partition,
        job_dir=job_dir_remote,
        env=job_env, modules=[qc_module] if qc_module else [],
        emit_stdio_lines=False, account=account, logical_key=key)

    template_dir = os.path.join(PKG_ROOT, "sei_pilot", "templates")
    adapter = sched_mod.PbsAdapter(shellrun.Shell(), template_dir, flavor="pbspro")

    # 🔴 [local-build/remote-run path split] Cannot call adapter.write_script()/write_cmd_file()
    # directly -- both write to spec.job_dir by construction (correct when build and run happen
    # on the same filesystem, which is the harness's normal case and not this tool's). This
    # replicates PbsAdapter.write_script()'s OWN resource-line/extras construction (the only
    # part duplicated -- rendering itself still goes through the SAME render_script() +
    # squeeze_directive_blanks() + template file the harness uses), redirecting the write
    # target to --out-dir while keeping every EXPORTED path in the script content correct for
    # where the job will actually run.
    resource = "#PBS -l select=%d:ncpus=%d:mpiprocs=%d" % (
        spec.nodes, spec.cores_per_node, spec.cores_per_node)
    extra = {"RESOURCE_LINE": resource, "MODULE_LINES": spec.module_block()}
    if spec.partition:
        extra["PARTITION_LINE"] = "#PBS -q %s" % spec.partition
    if spec.account:
        extra["ACCOUNT_LINE"] = "#PBS -A %s" % spec.account
    qsub_text = sched_mod.squeeze_directive_blanks(
        sched_mod.render_script(adapter._template("pbs.sh.tmpl"), spec, extra))

    # 🔴 [lead, wave-1 review items 3/5 -- landed in the GENERATED QSUB ONLY, lead's explicit
    # scoping] same deployed-package fingerprint guard as build_wave1_stage0_submission.py's
    # own -- see that tool's comment for the full reasoning (reuses common.sh's own
    # `sei_pkg_fingerprint()`, inserted via string surgery on the rendered qsub_text right
    # after common.sh is sourced, shared template itself untouched). Landing it in the qsub
    # rather than cmd.sh (an earlier version of this guard lived in cmd.sh) resolves last
    # round's flagged tension for free: cmd.sh is now IDENTICAL to what the harness would
    # produce, so the byte-identical-to-the-real-historical-U56_RB_scan.cmd.sh regression test
    # needs no special-casing at all -- only the qsub gets one now (see that test's own note).
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
        "directly under the package root outside sei_pilot_work/. If neither applies, this is "
        "a genuine stale/wrong deployment -- rebuild+redeploy the package, then resubmit. "
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
    # 🔴 [idempotency guard] refuse a re-run that would silently change an existing,
    # possibly-already-staged/reviewed pair -- same convention as every other tool this round.
    if os.path.exists(qsub_path) or os.path.exists(cmd_path):
        old_qsub = open(qsub_path).read() if os.path.exists(qsub_path) else None
        old_cmd = open(cmd_path).read() if os.path.exists(cmd_path) else None
        if old_qsub != new_qsub_text or old_cmd != new_cmd_text:
            sys.stderr.write(
                "refusing to overwrite %s/%s.{qsub,cmd.sh} -- a rebuild with a DIFFERENT spec "
                "would silently change an existing staged pair. Remove the existing files or "
                "pick a new --out-dir if a clean rebuild is really wanted.\n" % (out_dir, key))
            return 5
        # identical content -- re-emitting is a harmless no-op.

    with open(qsub_path, "w") as fh:
        fh.write(new_qsub_text)
    os.chmod(qsub_path, 0o755)
    with open(cmd_path, "w") as fh:
        fh.write(new_cmd_text)
    os.chmod(cmd_path, 0o755)

    manifest = {
        "purpose": "S3 wave-1 attempt 2: R-B redo (single-ended relaxed scan -> ts_opt -> "
                  "IRC fwd/rev), full production chain (02_METHOD_SPEC.md §39.136(1)/(2); "
                  "03_COMPUTE_PLAN.md §R39.88/89) -- NOT submitted by this script.",
        "reaction": REACTION, "method": METHOD,
        "reactant_endpoint_key": REACTANT_ENDPOINT_KEY,
        "job_key": key,
        "job_dir_remote": job_dir_remote,
        "reused_from": "same production harness that built U56_RA_scan/U56_RB_scan "
                       "(payload/U56.sh via sei_pilot.scheduler.PbsAdapter.write_script, the "
                       "same code path build_spec()/cmd_emit_script use) -- not a new "
                       "deck-building tool",
        "assumptions_not_independently_verified": {
            "pkg_root": pkg_root, "workdir": workdir, "qc_module": qc_module,
            "qc_login_path": qc_login_path,
            "_source": "ORIGINAL U56_RB_scan.qsub's own recorded values -- the only "
                      "confirmed-real deployment/QC-detection data point on record; verify "
                      "before trusting if the deployment path or QC module has changed",
        },
        "recorrect_never_default": "picked up automatically from config/qc_levels.json's "
                                  "irc_forward/irc_reverse templates (§39.136(2), landed in "
                                  "the same pass as this tool) -- nothing to set here",
        "deployed_package_fingerprint_check": {
            "expected": expected_fingerprint,
            "note": "qsub refuses to run (exit 9) if $SEI_PKG_ROOT's own recomputed "
                   "package_fingerprint (via common.sh's sei_pkg_fingerprint(), same "
                   "workdir-aware exclusion logic it already uses) doesn't match this -- "
                   "catches a stale/mismatched deployment before it silently ignores env vars "
                   "this build relies on (SEI_U56_STOP_AFTER included, though this R-B redo "
                   "does not set it).",
        },
        "wall_h": wall_h, "cores": cores,
        "qsub_file": os.path.basename(qsub_path),
        "cmd_file": os.path.basename(cmd_path),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("[build_wave1_rb_submission] wrote %s" % qsub_path)
    print("[build_wave1_rb_submission] wrote %s" % cmd_path)
    print("[build_wave1_rb_submission] job key: %s (fresh -- does not touch the original "
          "rejected U56_RB_scan job dir)" % key)
    print("[build_wave1_rb_submission] NOT SUBMITTED. Verify pkg_root/workdir/qc_module/"
          "qc_login_path in manifest.json's assumptions_not_independently_verified before "
          "trusting this deck -- see this tool's own docstring.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--key", default="U56_RB_scan_wave1",
                    help="fresh job key -- must not collide with the original U56_RB_scan")
    ap.add_argument("--pkg-root", default=DEFAULT_PKG_ROOT)
    ap.add_argument("--workdir", default=None,
                    help="default: <pkg-root>/sei_pilot_work")
    ap.add_argument("--qc-module", default=DEFAULT_QC_MODULE)
    ap.add_argument("--qc-login-path", default=DEFAULT_QC_LOGIN_PATH)
    ap.add_argument("--qc-level", default=DEFAULT_QC_LEVEL)
    ap.add_argument("--partition", default=DEFAULT_PARTITION)
    ap.add_argument("--account", default=DEFAULT_ACCOUNT)
    ap.add_argument("--wall-h", type=float, default=DEFAULT_WALL_H)
    ap.add_argument("--cores", type=int, default=DEFAULT_CORES)
    args = ap.parse_args(argv)
    return build(args.out_dir, args.key, args.pkg_root, args.workdir, args.qc_module,
                args.qc_login_path, args.qc_level, args.partition, args.account,
                args.wall_h, args.cores)


if __name__ == "__main__":
    sys.exit(main())
