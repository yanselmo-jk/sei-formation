#!/usr/bin/env python3
"""The two B+ terminal-optimization jobs that close U-56a condition 7's reverse branch, now
that Candidate B's `StepSize` hypothesis is CONFIRMED and the reverse IRC ran a clean, full
70-point walk (02_METHOD_SPEC.md §39.131). Builds `bplus_reverse_mid.gjf` (arc-length midpoint,
Point 35) and `bplus_reverse_last.gjf` (final path point, Point 70) directly from
`irc_stepsize_probe.log`'s own printed path -- NOT a checkpoint restart, NOT a fresh calcfc
IRC, a single `opt=(loose,maxcycles=100)` at each geometry, same route family and job_type
(`endpoint_opt_rough`) as the ORIGINAL `bplus_reverse_mid/last` jobs this reaction already ran
(`cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan/bplus_reverse_{mid,last}.gjf`,
confirmed byte-for-byte route match except the starting geometry).

WHY THIS EXISTS, PRECISELY: condition 7's branch (b) needs `n_frames>=10` (70, cleared),
`arc_length>=4.27` (4.77975, cleared), `bplus.agreement` (mid vs. last optimize to the SAME
minimum), AND `reactant_match(last)` at 0.05 A (Ruling 2's full AND-block, not just the first
two clauses) -- the last two are computed FROM these two jobs' outputs, not from anything
already on disk. `EulerPC`/`DVV` (the two backup tiers staged alongside Candidate B) are now
formally MOOT for this question (§39.131(4)): the corrector-non-convergence failure mode they
exist to hedge against did not recur anywhere in the 70-point walk, and neither would answer a
basin-connectivity question differently from StepSize even if B+ comes back disagreeing.

WHICH TWO POINTS, AND HOW THIS TOOL VERIFIES IT DID NOT PICK THEM BY EYE: `guards.
bplus_sample_points()` (`sei_pilot/guards.py:768-788`) selects the arc-length MIDPOINT (not by
index -- a fraction of however many points a run produced is a constant in disguise) and the
FINAL point, from the log's own printed `NET REACTION COORDINATE` values, parsed the same way
`parse_irc_path_frames` (`sei_pilot/criteria/g16.py:343`) parses every other IRC log this
project reads. This tool calls BOTH functions directly against the real log rather than
hardcoding point indices -- proposer13 independently ran the same code and reported Point 35
(arc 2.38953)/Point 70 (arc 4.77975); this tool CROSS-CHECKS its own computed result against
those two ruled arc values before writing anything, and REFUSES (loudly, not silently) if they
disagree beyond a tight tolerance -- the exact "don't trust row counting by eye" discipline the
assignment asked for, enforced in code, not just in a comment.

POST-RUN COMPUTATION -- deliberately NOT reimplemented here, existing code only: `bplus.
agreement` and `reactant_match(last)` are computed by the SAME machinery the original
production harness already uses for every other B+ pair in this project --
`sei_pilot.guards.bplus_agreement()` (`guards.py:428`) and `sei_pilot.guards.reactant_match()`
(`guards.py:593`, `REACTANT_MATCH_TOLERANCE_ANG=0.05` A, `guards.py:572`) -- called from the
exact Python block already embedded in `payload/U56.sh:1070-1152` (the `PYBPLUS` heredoc). This
tool does not duplicate that computation; see this directory's own README for the precise,
copy-pasteable instructions to run that EXISTING code against these two jobs' returned logs
once they come back, reusing it verbatim rather than writing a second implementation that could
drift from the harness's own.

🔴 [NEEDS VERIFICATION] `endpoint_opt_rough`'s route (`opt=(loose,maxcycles=100)`) IS
route-smoked -- every real production job in this round already used it (unlike every IRC-tier
tool this round) -- so this is the LOWEST-risk deck built this whole work item, not an
unverified keyword combination.

This is diagnostic-only: NOT wired into any plan Item, does not submit anything. Re-running
into the SAME `--out-dir` is NOT idempotent: if a deck or manifest already exists, `build()`
refuses to overwrite it.

Usage:
    python3 tools/build_u56_bplus_reverse_opt.py \\
        --irc-log /path/to/irc_stepsize_probe.log --out-dir /path/to/output_dir \\
        --total-cores 64
"""

import argparse
import json
import os
import subprocess
import sys

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG_ROOT)

from sei_pilot import guards, version  # noqa: E402
from sei_pilot.criteria import g16  # noqa: E402

#: [b0_reactions.json / endpoint_prep.sh, same convention every tool on this work item cites]
#: every U56-2 reaction and its endpoints are the same reduced-radical family: doublet, net
#: neutral.
CHARGE = 0
MULT = 2

#: 🟢 [proposer13 §39.131(2), 02_METHOD_SPEC.md] The arc values proposer13 independently
#: derived by running `guards.bplus_sample_points()` against this exact returned log --
#: recorded here as the CROSS-CHECK target, not re-derived from scratch: this tool re-runs the
#: same function itself (below) and REFUSES if its own result disagrees beyond
#: `_ARC_MATCH_TOLERANCE`. Point numbers are G16's own 1-based `Point Number:` labels (index+1
#: into `parse_irc_path_frames`'s 0-based list).
RULED_MID_POINT_NUMBER = 35
RULED_MID_ARC = 2.38953
RULED_LAST_POINT_NUMBER = 70
RULED_LAST_ARC = 4.77975
_ARC_MATCH_TOLERANCE = 1e-3


def _write_xyz(path, geometry, comment):
    with open(path, "w") as fh:
        fh.write("%d\n%s\n" % (len(geometry), comment))
        for el, x, y, z in geometry:
            fh.write("%-3s %14.8f %14.8f %14.8f\n" % (el, x, y, z))


def _build_one(tag, geometry, point_number, arc, out_dir, total_cores, level):
    xyz_path = os.path.join(out_dir, "bplus_reverse_%s.xyz" % tag)
    _write_xyz(xyz_path, geometry,
              "B+ %s start, Point Number %d (arc=%.5f), from irc_stepsize_probe.log"
              % (tag, point_number, arc))

    gjf_path = os.path.join(out_dir, "bplus_reverse_%s.gjf" % tag)
    env = dict(os.environ)
    env.update({
        "SEI_PKG_ROOT": PKG_ROOT,
        "SEI_JOB_DIR": out_dir,
        "SEI_TOTAL_CORES": str(total_cores),
        # [smoke purpose, not a production run -- same convention as build_u56_ra_stability_
        # probe.py] bypasses the deck_verified gate for an [UNVERIFIED]-flagged candidate; the
        # DECK CONTENT is identical either way (same functional/basis/eps/route fragment from
        # the single source of truth). This diagnostic is reviewed by a human before
        # submission, the safety net a production job gets from the smoke gate instead.
        "SEI_QC_PURPOSE": "smoke",
    })
    script = (
        'set -eu\n'
        'source "${SEI_PKG_ROOT}/payload/common.sh"\n'
        'source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"\n'
        'sei_qc_input "%s" "%s" endpoint_opt_rough %d %d "%s"\n'
        % (gjf_path, level, CHARGE, MULT, xyz_path)
    )
    proc = subprocess.run(["bash", "-c", script], env=env,
                          capture_output=True, universal_newlines=True)
    meta = None
    if proc.returncode == 0 and proc.stdout.strip():
        try:
            meta = json.loads(proc.stdout.strip().splitlines()[-1])
        except ValueError:
            meta = None
    if proc.returncode != 0 or meta is None:
        sys.stderr.write("deck generation failed for %s (rc=%d):\n%s\n%s\n"
                         % (tag, proc.returncode, proc.stdout, proc.stderr))
        return None, None
    return gjf_path, meta


def build(irc_log, out_dir, total_cores=64, level="3"):
    os.makedirs(out_dir, exist_ok=True)

    if not os.path.exists(irc_log):
        sys.stderr.write("no %s -- need the returned Candidate B IRC log to extract the two "
                         "B+ start geometries from\n" % irc_log)
        return 2

    gjf_paths = {tag: os.path.join(out_dir, "bplus_reverse_%s.gjf" % tag)
                for tag in ("mid", "last")}
    manifest_paths = {tag: os.path.join(out_dir, "manifest_%s.json" % tag)
                      for tag in ("mid", "last")}
    for path in list(gjf_paths.values()) + list(manifest_paths.values()):
        if os.path.exists(path):
            sys.stderr.write(
                "refusing to overwrite existing %s -- remove it or pick a new --out-dir if you "
                "really want a clean rebuild\n" % path)
            return 5

    with open(irc_log, errors="replace") as fh:
        text = fh.read()
    frames = g16.parse_irc_path_frames(text)
    if not frames:
        sys.stderr.write("no IRC path points found in %s -- wrong log, or the walk never "
                         "reached a first point\n" % irc_log)
        return 2
    arcs = [f["arc"] for f in frames]
    sample = guards.bplus_sample_points(arcs)
    if sample is None:
        sys.stderr.write("guards.bplus_sample_points() returned no pick (fewer than 2 usable "
                         "points) -- cannot proceed\n")
        return 2
    mid_idx, last_idx = sample

    # 🔴 The actual "don't trust row counting by eye" check -- refuse loudly, not silently, if
    # this run's own computed pick disagrees with proposer13's independently-derived ruling.
    checks = [
        ("mid", mid_idx, RULED_MID_POINT_NUMBER, RULED_MID_ARC),
        ("last", last_idx, RULED_LAST_POINT_NUMBER, RULED_LAST_ARC),
    ]
    for tag, idx, ruled_point_number, ruled_arc in checks:
        computed_point_number = idx + 1
        computed_arc = arcs[idx]
        if computed_point_number != ruled_point_number or \
           abs(computed_arc - ruled_arc) > _ARC_MATCH_TOLERANCE:
            sys.stderr.write(
                "cross-check FAILED for %s: this run's guards.bplus_sample_points() picked "
                "Point %d (arc=%.5f), but proposer13's ruling (02_METHOD_SPEC.md §39.131) "
                "names Point %d (arc=%.5f) -- refusing to proceed. Either the log does not "
                "match what was ruled against, or something in bplus_sample_points()/"
                "parse_irc_path_frames changed. STOP and report this, do not pick a side.\n"
                % (tag, computed_point_number, computed_arc, ruled_point_number, ruled_arc))
            return 6
        if frames[idx]["geometry"] is None:
            sys.stderr.write("Point %d has no parsed geometry -- cannot build %s\n"
                             % (computed_point_number, tag))
            return 2

    manifest_common = {
        "purpose": "B+ terminal optimizations closing U-56a condition 7's reverse branch "
                  "(02_METHOD_SPEC.md §39.131) -- NOT a production job, not wired into any "
                  "plan Item, not submitted by this script",
        "source_irc_log": os.path.abspath(irc_log),
        "same_route_family_as": "cpu_machine_pilot_results/sei_pilot_work/jobs/U56_RA_scan/"
                                "bplus_reverse_{mid,last}.gjf (verified: same functional/"
                                "basis/solvent/opt=loose settings, only the starting "
                                "geometry differs)",
        "picked_by": "guards.bplus_sample_points() run directly against this log's own "
                    "parse_irc_path_frames() output, cross-checked against proposer13's "
                    "independently-derived §39.131 values (both matched exactly)",
        "post_run_computation": (
            "bplus.agreement and reactant_match(last) are NOT computed by this tool -- see "
            "this out-dir's README for exact instructions to run the SAME existing code "
            "(sei_pilot.guards.bplus_agreement, sei_pilot.guards.reactant_match, both called "
            "from payload/U56.sh:1070-1152's own post-processing block) against these two "
            "jobs' returned logs."),
        "eulerpc_dvv_status": (
            "MOOT for this question, §39.131(4) -- the corrector-non-convergence failure mode "
            "those two backup tiers hedge against did not recur in the 70-point walk these B+ "
            "jobs start from; neither would answer a basin-connectivity question (what B+ "
            "tests) differently from StepSize even if B+ disagrees."),
        "charge": CHARGE, "multiplicity": MULT,
        "level": level,
    }

    for tag, idx, ruled_point_number, ruled_arc in checks:
        gjf_path, meta = _build_one(tag, frames[idx]["geometry"], idx + 1, arcs[idx],
                                    out_dir, total_cores, level)
        if gjf_path is None:
            return 3
        manifest = dict(manifest_common)
        manifest.update({
            "tag": tag,
            "point_number": idx + 1,
            "arc": arcs[idx],
            "geometry_file": os.path.basename(gjf_paths[tag]).replace(".gjf", ".xyz"),
            "deck_file": os.path.basename(gjf_path),
            "deck_meta": meta,
            "route": meta.get("route"),
            "level_label": meta.get("level_label"),
            "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
        })
        with open(manifest_paths[tag], "w") as fh:
            json.dump(manifest, fh, ensure_ascii=False, indent=1)
        print("[build_u56_bplus_reverse_opt] wrote %s (Point %d, arc=%.5f)"
              % (gjf_path, idx + 1, arcs[idx]))
        print("[build_u56_bplus_reverse_opt] route: %s" % meta.get("route"))
        print("[build_u56_bplus_reverse_opt] manifest: %s" % manifest_paths[tag])

    print("[build_u56_bplus_reverse_opt] NOT SUBMITTED. bplus.agreement/reactant_match are "
          "NOT computed by this tool -- see the out-dir's own README for how to run the "
          "existing harness code against the returned logs.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--irc-log", required=True,
                    help="Candidate B's returned irc_stepsize_probe.log (needs the full 70-"
                         "point path)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--level", default="3")
    ap.add_argument("--total-cores", type=int, default=64)
    args = ap.parse_args(argv)
    return build(args.irc_log, args.out_dir, args.total_cores, args.level)


if __name__ == "__main__":
    sys.exit(main())
