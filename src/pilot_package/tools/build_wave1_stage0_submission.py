#!/usr/bin/env python3
"""Stage 0: the MTD-pilot comparator (12 seeds x 100 ps unbiased NVT xtb MD, R-C's reactant,
1500 K -- 02_METHOD_SPEC.md §39.40(d)-RESULT/§39.42(d)/§39.47(b)) -- generates the `.qsub`/
`.cmd.sh` submission wrapper for `payload/stage0_md.sh`, build-only, same pattern as
`build_wave1_rb_submission.py` (this tool's own sibling): a fresh `sei_pilot.scheduler.JobSpec`
rendered via the SAME `PbsAdapter`/template code the harness itself uses, no `submit()`
anywhere in the path this tool calls.

WHY THIS RUNS IN PARALLEL WITH WAVE 1, NOT AS PART OF IT: stage 0 is gated by its own
independent condition (does an unbiased MD comparator rediscover the sealed T1-T4 targets on
its own?) on a DIFFERENT pipeline stage (S2 product discovery) than wave 1 (S3 barriers) --
neither's result informs how the other should be read (§39.136, third addendum). If stage 0
finds all four targets, the conditional MTD pilot is never funded for this reaction class
(F13, §39.40(h)) -- but that is a LATER read of `stage0_result.json`, not something this build
decides.

TARGET-BLIND BY DESIGN (§39.40(e)'s own BLINDNESS requirement): `payload/stage0_md.sh`'s
classifier reports every observed bond/fragmentation change relative to the reactant's own
starting graph, generically -- it does NOT hardcode T1-T4's specific atom indices (no sealed
target file exists in this project's committed files yet; writing one is a proposer13
pre-registration step, not a coder one). Matching the observed events against the sealed T1-T4
list is a follow-up read once that file exists.

🔴 [ASSUMPTION] Same caveat as `build_wave1_rb_submission.py`: `--pkg-root`/`--workdir`/
`--qc-module`(unused here, xtb needs no module load)/deployment path default to the last
confirmed-real values on record for this user's cluster. Verify before trusting if the
deployment has changed.

Usage:
    python3 tools/build_wave1_stage0_submission.py --out-dir /path/to/wave1_stage0_2026-08-25
"""

import argparse
import hashlib
import json
import os
import sys

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG_ROOT)

from sei_pilot import scheduler as sched_mod  # noqa: E402
from sei_pilot import shellrun, version  # noqa: E402
from sei_pilot.state import makedirs  # noqa: E402

#: 🟢 [02_METHOD_SPEC.md §39.47(b), final ruling] "STAGE 0 = 12 SEEDS x 100 ps, unbiased NVT
#: at the ladder's top rung." 1500K confirmed as the top rung (§39.40(d)-RESULT's own
#: 1-seed/5ps discovery run, T1 recovered <1ps).
N_SEEDS = 12
TEMP_K = 1500
TIME_PS = 100.0
REACTANT_XYZ = "inputs/li_ec2_radical_reactant.xyz"
CHARGE = 0
MULTIPLICITY = 2   # config/b0_reactions.json's R-C entry

#: 🟢 [ORIGINAL U56_RB_scan.qsub, same confirmed-real deployment data point
#: build_wave1_rb_submission.py uses -- kept identical for consistency across this round's
#: staged batch]
DEFAULT_PKG_ROOT = "/scratch/q656a01/calculation_time_test_pilot/sei_pilot_cpu"
DEFAULT_PARTITION = "normal"
DEFAULT_ACCOUNT = "gaussian"

#: 🟢 [§39.42(d): "100 ps at 21 atoms, 1 thread ~= 0.54h [MEASURED, DEV BOX]"; this build's own
#: local re-run of xtb's own self-reported estimate on a 0.05ps probe scaled to ~1.4h/100ps on
#: THIS workstation -- different hardware, same order of magnitude, both single-thread] 12
#: seeds run fully in PARALLEL (embarrassingly parallel, ADR-110: explicit 1 core/task, never
#: whole-node) -- wall stays ~1 seed's own 100ps time regardless of seed count. Cap chosen with
#: real margin over the wider (1.4h) of the two anchors -- deliberately NOT scaled up to a
#: full node's worth of parallel headroom since 12 concurrent 1-core tasks already fit
#: trivially inside it (§39.47(b): "12 seeds pack trivially").
DEFAULT_WALL_H = 6.0
DEFAULT_CORES = 12   # 1 core/seed x 12 seeds, matching N_SEEDS -- ADR-110 explicit, never None

#: [critic17, wave-1 review #3] fixed, known path (not glob/find, matches this project's own
#: provenance rule) -- the sealed T1-T4 target file, if it exists, always lives here.
SEALED_TARGETS_PATH = os.path.join(PKG_ROOT, "config", "stage0_sealed_targets_T1-T4.json")

#: 🟢 [proposer13, sealed 2026-08-25T09:30:04Z UTC, §39.40(e)] the sha256 proposer13 announced
#: at sealing time, baked in here as the EXPECTED value -- independently re-verified by coder16
#: via sha256sum before this constant was written (see wave1_2026-08-25/stage0/manifest.json's
#: own "verified_here" note). This is what makes an in-place edit of the sealed file (forbidden
#: by its own header) DETECTABLE: computing the hash from the file alone, with nothing to check
#: it against, would just report whatever is on disk NOW as if it were still the sealed value.
#: If the sealed target definitions are ever legitimately revised, this is a NEW file + a new
#: constant here, never an edit of the existing one (same rule the sealed file states of itself).
SEALED_TARGETS_SHA256_EXPECTED = (
    "69ce2848ca346ccc107178104b85dcc4cb7a43212d71bb7c966f6450bbc3f2c2")


class SealedTargetsTampered(Exception):
    """Raised when the committed sealed T1-T4 file's real hash no longer matches the hash
    baked in at build time -- i.e. someone edited a file whose own header forbids that."""


def _sealed_targets_info(expected_sha256=SEALED_TARGETS_SHA256_EXPECTED):
    """Read the sealed-target-file state FRESH at build time, from the file itself -- never
    hand-edited into the manifest afterward (that drift is exactly what critic17 caught: a
    stale builder claiming 'not sealed yet' while the staged manifest said otherwise by hand).
    Returns (info_dict_or_None, blindness_sentence). Raises SealedTargetsTampered if the file
    exists but its hash no longer matches `expected_sha256` (lead's item 6: verify against an
    expected hash, don't just report whatever is currently on disk as fact -- `expected_sha256`
    is an explicit INPUT, defaulting to the baked-in constant, so a caller/test can pass a
    different one without needing to touch the real committed file)."""
    if not os.path.exists(SEALED_TARGETS_PATH):
        return None, ("payload/stage0_md.sh's classifier is target-blind by design "
                      "(§39.40(e)'s BLINDNESS requirement) -- it does not hardcode T1-T4's "
                      "specific atom indices, which are not yet a sealed file in this "
                      "project's committed sources")
    sha256 = hashlib.sha256(open(SEALED_TARGETS_PATH, "rb").read()).hexdigest()
    if sha256 != expected_sha256:
        raise SealedTargetsTampered(
            "sealed target file %s has sha256=%s, expected %s -- this file's own header "
            "forbids editing it in place; either it was tampered with, or it was legitimately "
            "re-sealed and the expected hash (SEALED_TARGETS_SHA256_EXPECTED / "
            "--sealed-targets-sha256) needs an update citing the new seal event, never a "
            "silent overwrite." % (SEALED_TARGETS_PATH, sha256, expected_sha256))
    info = {
        "path": "src/pilot_package/config/stage0_sealed_targets_T1-T4.json",
        "sha256": sha256,
        "verified_against_expected": True,
        "note": "sha256 computed HERE, at build time, from the committed file, and checked "
               "against SEALED_TARGETS_SHA256_EXPECTED baked into this builder -- a mismatch "
               "refuses the build rather than silently reporting a tampered file as sealed. "
               "Sealer identity/timestamp are recorded in the sealed file's own header, not "
               "re-derived here to avoid a second, driftable copy of that claim.",
    }
    blindness = ("payload/stage0_md.sh's classifier is target-blind by design (§39.40(e)'s "
                "BLINDNESS requirement) -- it does not hardcode T1-T4's specific atom indices. "
                "Sealed target file recorded below (path/sha256, verified against the expected "
                "hash baked into this builder at build time).")
    return info, blindness


def build(out_dir, key="stage0_mtd_comparator", pkg_root=DEFAULT_PKG_ROOT,
         workdir=None, partition=DEFAULT_PARTITION, account=DEFAULT_ACCOUNT,
         wall_h=DEFAULT_WALL_H, cores=DEFAULT_CORES, n_seeds=N_SEEDS, temp_k=TEMP_K,
         time_ps=TIME_PS, sealed_targets_sha256=SEALED_TARGETS_SHA256_EXPECTED):
    # 🔴 [lead, wave-1 review item 6] validate the sealed target file BEFORE any write -- refuse-
    # before-clobber, same idempotency guard shape as the qsub/cmd overwrite check below.
    sealed_info, blindness_sentence = _sealed_targets_info(sealed_targets_sha256)

    os.makedirs(out_dir, exist_ok=True)
    workdir = workdir or (pkg_root + "/sei_pilot_work")
    job_dir_remote = "%s/jobs/%s" % (workdir, key)

    job_env = {
        "SEI_PKG_ROOT": pkg_root,
        "SEI_WORKDIR": workdir,
        "SEI_PARTITION": partition,
        "SEI_ITEM": key,
        "SEI_WALL_H": "%.4f" % wall_h,
        "SEI_STAGE0_N_SEEDS": str(n_seeds),
        "SEI_STAGE0_TEMP_K": str(temp_k),
        "SEI_STAGE0_TIME_PS": "%.1f" % time_ps,
        "SEI_STAGE0_REACTANT_XYZ": REACTANT_XYZ,
        "SEI_STAGE0_CHARGE": str(CHARGE),
        "SEI_STAGE0_MULTIPLICITY": str(MULTIPLICITY),
    }

    # 🔴 [local-build/remote-run path split -- same reasoning as build_wave1_rb_submission.py,
    # see that tool's own comment for the full explanation] job_dir=job_dir_remote for correct
    # SEI_JOB_DIR/CMD_FILE content; files are WRITTEN locally to --out-dir below.
    spec = sched_mod.JobSpec(
        key, "bash %s/payload/stage0_md.sh" % pkg_root,
        nodes=1, cores_per_node=cores, wall_h=wall_h, partition=partition,
        job_dir=job_dir_remote, env=job_env, modules=[],
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

    # 🔴 [lead, wave-1 review items 3/5; critic17 pre-build note] the qsub references a
    # deployment PATH, not a package -- a stale deployed package would silently ignore env vars
    # this build relies on (SEI_U56_STOP_AFTER especially). Bind THIS build's own source-tree
    # fingerprint now, assert it against the deployed tree's own recomputed fingerprint at run
    # time, refuse otherwise. Lands in the GENERATED QSUB ONLY (lead's explicit scoping -- zero
    # shared-file blast radius, common.sh wiring deferred to its own slot) -- inserted via
    # string surgery on the ALREADY-RENDERED qsub_text (the shared pbs.sh.tmpl template itself
    # is untouched, still pinned by tests/test_pbs_script_shape.py's own historical-shape
    # comparison), right after common.sh is sourced and before sei_job_main starts the payload.
    # 🔴 [critic17] REUSES `common.sh`'s own `sei_pkg_fingerprint()` (already defined by the
    # point this runs) rather than reimplementing the hash inline -- that function already
    # applies the SAME SEI_WORKDIR-relative extra_exclude common.sh's own stage-checkpoint
    # fingerprint uses, so a renamed (non-default) --workdir does not false-alarm here either.
    # cmd.sh is deliberately left UNTOUCHED by this guard -- see build_wave1_rb_submission.py's
    # own comment for why that keeps cmd.sh's byte-identity property completely undisturbed.
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
    cmd_text = ("#!/bin/bash\n# sei_pilot payload command (%s)\nset -u\n%s\n"
               % (key, spec.command))

    makedirs(out_dir)
    qsub_path = os.path.join(out_dir, key + ".qsub")
    cmd_path = os.path.join(out_dir, key + ".cmd.sh")
    if os.path.exists(qsub_path) or os.path.exists(cmd_path):
        old_qsub = open(qsub_path).read() if os.path.exists(qsub_path) else None
        old_cmd = open(cmd_path).read() if os.path.exists(cmd_path) else None
        if old_qsub != qsub_text or old_cmd != cmd_text:
            sys.stderr.write(
                "refusing to overwrite %s/%s.{qsub,cmd.sh} -- a rebuild with a DIFFERENT spec "
                "would silently change an existing staged pair. Remove the existing files or "
                "pick a new --out-dir if a clean rebuild is really wanted.\n" % (out_dir, key))
            return 5

    with open(qsub_path, "w") as fh:
        fh.write(qsub_text)
    os.chmod(qsub_path, 0o755)
    with open(cmd_path, "w") as fh:
        fh.write(cmd_text)
    os.chmod(cmd_path, 0o755)

    manifest = {
        "purpose": "Stage 0 -- MTD-pilot comparator (02_METHOD_SPEC.md §39.40(d)-RESULT/"
                  "§39.42(d)/§39.47(b)) -- runs in PARALLEL with S3 wave-1, not part of its "
                  "2-attempt count. NOT submitted by this script.",
        "n_seeds": n_seeds, "temp_k": temp_k, "time_ps": time_ps,
        "reactant_xyz": REACTANT_XYZ, "charge": CHARGE, "multiplicity": MULTIPLICITY,
        "job_key": key, "job_dir_remote": job_dir_remote,
        "target_blindness": blindness_sentence,
        "sealed_targets_file": sealed_info,
        "assumptions_not_independently_verified": {
            "pkg_root": pkg_root, "workdir": workdir,
            "_source": "same confirmed-real deployment data point as "
                      "build_wave1_rb_submission.py's own manifest -- verify before trusting "
                      "if the deployment path has changed",
        },
        "wall_h": wall_h, "cores": cores,
        "qsub_file": os.path.basename(qsub_path), "cmd_file": os.path.basename(cmd_path),
        "deployed_package_fingerprint_check": {
            "expected": expected_fingerprint,
            "note": "qsub refuses to run (exit 9) if $SEI_PKG_ROOT's own recomputed "
                   "package_fingerprint (via common.sh's sei_pkg_fingerprint(), same "
                   "workdir-aware exclusion logic it already uses) doesn't match this -- "
                   "catches a stale/mismatched deployment before it silently ignores env vars "
                   "this build relies on.",
        },
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("[build_wave1_stage0_submission] wrote %s" % qsub_path)
    print("[build_wave1_stage0_submission] wrote %s" % cmd_path)
    print("[build_wave1_stage0_submission] NOT SUBMITTED. Verify pkg_root/workdir in "
          "manifest.json before trusting this deck.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--key", default="stage0_mtd_comparator")
    ap.add_argument("--pkg-root", default=DEFAULT_PKG_ROOT)
    ap.add_argument("--workdir", default=None)
    ap.add_argument("--partition", default=DEFAULT_PARTITION)
    ap.add_argument("--account", default=DEFAULT_ACCOUNT)
    ap.add_argument("--wall-h", type=float, default=DEFAULT_WALL_H)
    ap.add_argument("--cores", type=int, default=DEFAULT_CORES)
    ap.add_argument("--n-seeds", type=int, default=N_SEEDS)
    ap.add_argument("--temp-k", type=int, default=TEMP_K)
    ap.add_argument("--time-ps", type=float, default=TIME_PS)
    ap.add_argument("--sealed-targets-sha256", default=SEALED_TARGETS_SHA256_EXPECTED,
                    help="expected sha256 of the sealed T1-T4 target file; build refuses if "
                        "the committed file's real hash doesn't match (default: the hash "
                        "baked in from proposer13's sealing announcement)")
    args = ap.parse_args(argv)
    try:
        return build(args.out_dir, args.key, args.pkg_root, args.workdir, args.partition,
                    args.account, args.wall_h, args.cores, args.n_seeds, args.temp_k,
                    args.time_ps, args.sealed_targets_sha256)
    except SealedTargetsTampered as exc:
        sys.stderr.write("[build_wave1_stage0_submission] REFUSING TO BUILD: %s\n" % exc)
        return 6


if __name__ == "__main__":
    sys.exit(main())
