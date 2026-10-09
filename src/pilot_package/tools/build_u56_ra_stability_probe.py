#!/usr/bin/env python3
"""One-off diagnostic: cheap `stable=opt` wavefunction-stability tests at real geometries
(linear-hopping-frog plan, Track A item 2; targets fixed by 02_METHOD_SPEC.md §39.114(2)/§39.115).

WHY: `U56_RA_scan`/`U56_RA_qst2`'s IRC corrector integration dies deep in the path, and every
SCF cycle along the way (and in several OTHER, unrelated jobs at other magnitudes) carries a
`**** Warning!!: The largest {alpha,beta} MO coefficient is ...` warning. A normalised MO
coefficient should be O(1). `stable=opt` (Gaussian's built-in stability test) tells apart (a) a
genuine wavefunction instability (a lower-energy SCF solution exists) from (b) a numerics/basis
artifact -- CHEAPLY: single point, no opt/freq, same method/basis/solvent as production.

FALSIFIABILITY (02_METHOD_SPEC.md 39.113(e), stated explicitly per proposer10's request): finding
an internal instability (G16 reports the wavefunction unstable and reoptimises to a LOWER energy)
supports real open-shell/near-degeneracy physics needing systematic reoptimization. Finding NO
instability (the SCF is already a genuine local minimum in orbital space) FALSIFIES "unstable
wavefunction" as the explanation and points entirely to the IRC integrator/numerics -- consistent
with what the raw corrector-failure log text already suggests (Delta-x Convergence NOT Met /
Maximum number of corrector steps exceded, not an SCF-convergence-failure message).

THREE build targets, per 39.114(2)/39.115 (run all three -- they answer different questions):
  1. `--irc-log U56_RA_scan/irc_forward.log --point-index 4`  (G16 "Point Number 5", arc~1.71,
     coefficient~33 -- where the coefficient first stabilises after its initial rise)
  2. `--irc-log U56_RA_scan/irc_forward.log --point-index 19` (G16 "Point Number 20", arc~6.83,
     coefficient~38.7 -- the LAST point actually computed before the crash)
  3. `--geom-log endpoint_prep_rc_reactant/endpoint_tight.log` (21-atom, ALREADY-CERTIFIED
     C-8 reactant, coefficient~71-79 -- the highest magnitude in the whole returned tree, on a
     job that PASSED, not one that crashed -- priced/read SEPARATELY per §39.115, different cost
     class and different stakes: a certificate already relied on, not an open candidate)

🔴 [NEEDS VERIFICATION, critic14] The `stable=opt` keyword itself has never been route-smoked:
`sei_qc_smoke` (qc_adapter.sh) only ever builds `sp` and `freq`/`freq_smoke_legacy_generic`
job_types. What every real production job this round DID verify is the functional/basis/solvent
FRAGMENT (`wB97XD/gen ... scrf=(pcm,solvent=acetone,read)`, def2-SVPD, eps=18.5) -- a real but
partial guarantee that says nothing about `stable=opt` specifically. Same unsmoked-keyword state
as `build_u56_ra_irc_recorrect_probe.py`'s restart route -- read both results with this in mind,
not just the more obviously novel-looking one.

This is diagnostic-only. It is NOT wired into any plan Item, does not touch the harness's
submission/state machinery, and does not submit anything -- it only builds a real, reviewable
.gjf the user can inspect and submit by hand. Re-running this script is idempotent.

Usage:
    python3 tools/build_u56_ra_stability_probe.py --irc-log .../irc_forward.log \\
        --point-index 19 --out-dir /path/to/output_dir_point20
    python3 tools/build_u56_ra_stability_probe.py --geom-log .../endpoint_tight.log \\
        --out-dir /path/to/output_dir_rc_reactant

Cost estimate (printed, never silent): a single-point `stable=opt`, 11 or 21 atoms,
wB97XD/def2-SVPD -- comparable to one SCF-heavy point of the production scan (seconds to a few
minutes on one core), negligible against the ~660-6,400 core-h a full DFT scan/IRC costs.
"""

import argparse
import json
import os
import re
import subprocess
import sys

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG_ROOT)

from sei_pilot import version  # noqa: E402
from sei_pilot.criteria import g16  # noqa: E402

#: [b0_reactions.json / endpoint_prep.sh] every U56-2 reaction AND its endpoints are the same
#: reduced-radical family: doublet, net neutral (charge 0, the extra electron is the reduction) --
#: true for the 11-atom R-A/R-B species and the 21-atom R-C species alike (endpoint_prep.sh hard-
#: codes the same CHARGE=0/MULT=2 for every role). Cited, not re-derived, to avoid importing plan
#: machinery this standalone tool has no other reason to depend on.
CHARGE = 0
MULT = 2

MO_WARNING_RE = r"largest (alpha|beta) MO coefficient is\s+([0-9.D+-]+)"


def _find_nearby_warning(text, before_line_no):
    """Best-effort: the last MO-coefficient warning value BEFORE the chosen point's line.

    Documentation only -- not used to pick the point, only to record what was true near it.
    """
    lines = text.splitlines()
    last = None
    for i, line in enumerate(lines[:before_line_no]):
        m = re.search(MO_WARNING_RE, line)
        if m:
            last = {"line": i + 1, "kind": m.group(1),
                    "value": float(m.group(2).replace("D", "E"))}
    return last


def _write_xyz(path, geometry, comment):
    with open(path, "w") as fh:
        fh.write("%d\n%s\n" % (len(geometry), comment))
        for el, x, y, z in geometry:
            fh.write("%-3s %14.8f %14.8f %14.8f\n" % (el, x, y, z))


def _pick_from_irc_log(irc_log_path, point_index):
    """Returns (geometry, source_dict) for an IRC path point, or (None, error_dict)."""
    with open(irc_log_path, errors="replace") as fh:
        text = fh.read()
    frames = g16.parse_irc_path_frames(text)
    if not frames:
        return None, {"error": "no IRC path points found in %s -- wrong log, or the corrector "
                               "integration never reached a first point" % irc_log_path}
    if not (0 <= point_index < len(frames)):
        return None, {"error": "point-index %d out of range (log has %d path points, 0..%d)"
                               % (point_index, len(frames), len(frames) - 1)}
    frame = frames[point_index]
    if not frame["geometry"]:
        return None, {"error": "path point %d has no parsed geometry" % point_index}
    line_no = None
    marker = "%.5f" % frame["arc"]
    for i, line in enumerate(text.splitlines()):
        if "NET REACTION COORDINATE" in line and marker in line:
            line_no = i + 1
            break
    warning = _find_nearby_warning(text, line_no) if line_no else None
    return frame["geometry"], {
        "source_kind": "irc_path_point",
        "source_log": os.path.abspath(irc_log_path),
        "irc_path_point_index": point_index,
        "irc_arc_length": frame["arc"],
        "nearby_mo_coefficient_warning": warning,
        "xyz_comment": ("U56_RA stability probe -- IRC forward path point %d (arc=%.5f), from %s"
                        % (point_index, frame["arc"], os.path.basename(irc_log_path))),
    }


def _pick_from_geom_log(geom_log_path):
    """Returns (geometry, source_dict) for a plain optimisation/freq log's LAST geometry."""
    with open(geom_log_path, errors="replace") as fh:
        text = fh.read()
    geom = g16.last_geometry(text)
    if not geom:
        return None, {"error": "no geometry parsed from %s" % geom_log_path}
    warnings = [{"line": i + 1, "kind": m.group(1), "value": float(m.group(2).replace("D", "E"))}
                for i, line in enumerate(text.splitlines())
                for m in [re.search(MO_WARNING_RE, line)] if m]
    return geom, {
        "source_kind": "certified_geometry_log",
        "source_log": os.path.abspath(geom_log_path),
        "mo_coefficient_warnings_first_last": (
            [warnings[0], warnings[-1]] if warnings else None),
        "n_mo_coefficient_warnings": len(warnings),
        "xyz_comment": ("U56 stability probe -- last geometry of %s"
                        % os.path.basename(geom_log_path)),
    }


def build(out_dir, irc_log=None, point_index=None, geom_log=None, total_cores=1, level="3"):
    os.makedirs(out_dir, exist_ok=True)
    if geom_log:
        geometry, source = _pick_from_geom_log(geom_log)
    else:
        geometry, source = _pick_from_irc_log(irc_log, point_index)
    if geometry is None:
        sys.stderr.write("%s\n" % source["error"])
        return 2

    xyz_path = os.path.join(out_dir, "probe_point.xyz")
    _write_xyz(xyz_path, geometry, source.pop("xyz_comment"))

    gjf_path = os.path.join(out_dir, "stability_probe.gjf")
    env = dict(os.environ)
    env.update({
        "SEI_PKG_ROOT": PKG_ROOT,
        "SEI_JOB_DIR": out_dir,
        "SEI_TOTAL_CORES": str(total_cores),
        # [smoke purpose, not a production run] this bypasses the deck_verified gate
        # (config/qc_levels.json's solvent_policy.deck_verified) -- the DECK CONTENT is
        # identical either way (same functional/basis/eps/route fragment from the single
        # source of truth); "smoke" only controls whether an [UNVERIFIED] candidate deck is
        # allowed through without a fresh route smoke. This diagnostic is reviewed by a human
        # before submission, which is the safety net a production job would get from the
        # smoke gate instead.
        "SEI_QC_PURPOSE": "smoke",
    })
    script = (
        'set -eu\n'
        'source "${SEI_PKG_ROOT}/payload/common.sh"\n'
        'source "${SEI_PKG_ROOT}/payload/qc_adapter.sh"\n'
        'sei_qc_input "%s" "%s" stability_test %d %d "%s"\n'
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
        sys.stderr.write("deck generation failed (rc=%d):\n%s\n%s\n"
                         % (proc.returncode, proc.stdout, proc.stderr))
        return proc.returncode or 1

    manifest = {
        "purpose": "diagnostic (Track A item 2, 02_METHOD_SPEC.md 39.114(2)/39.115) -- NOT a "
                  "production job, not wired into any plan Item, not submitted by this script",
        "question": "genuine wavefunction/SCF instability vs. IRC-integrator/numerics artifact",
        "falsifiability": (
            "an internal instability (G16 reports the wavefunction unstable, reoptimises to a "
            "LOWER energy) supports real open-shell/near-degeneracy physics needing systematic "
            "reoptimization. NO instability (already a genuine local minimum in orbital space) "
            "FALSIFIES 'unstable wavefunction' and points to the IRC integrator/numerics instead "
            "(02_METHOD_SPEC.md 39.113(e))."),
        "source": source,
        "geometry_file": os.path.basename(xyz_path),
        "deck_file": os.path.basename(gjf_path),
        "deck_meta": meta,
        "charge": CHARGE, "multiplicity": MULT,
        "level": meta.get("level"), "level_label": meta.get("level_label"),
        "job_type": "stability_test",
        "route": meta.get("route"),
        "route_syntax_status": (
            "[NEEDS VERIFICATION, critic14] `stable=opt` has never been route-smoked -- "
            "sei_qc_smoke only ever builds sp/freq job_types. The functional/basis/solvent "
            "fragment WAS verified (every real production job this round used it), but the "
            "`stable=opt` keyword itself was not. Same unsmoked-keyword state as "
            "build_u56_ra_irc_recorrect_probe.py's restart route -- a malformed route fails at "
            "~zero cost either way."),
        "estimated_cost": "single point, stable=opt, %d atoms, wB97XD/def2-SVPD, no opt/freq -- "
                          "seconds to a few minutes on 1 core; negligible against the "
                          "~660-6,400 core-h a full DFT scan/IRC for this reaction costs"
                          % len(geometry),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(os.path.join(out_dir, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("[build_u56_ra_stability_probe] wrote %s" % gjf_path)
    print("[build_u56_ra_stability_probe] route: %s" % meta.get("route"))
    print("[build_u56_ra_stability_probe] source: %s" % source)
    print("[build_u56_ra_stability_probe] manifest: %s"
          % os.path.join(out_dir, "manifest.json"))
    print("[build_u56_ra_stability_probe] NOT SUBMITTED -- this only builds the deck. Submit "
          "%s on the real cluster by hand (single Gaussian16 run, ~1 core, minutes)." % gjf_path)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--irc-log",
                     help="path to an IRC log (e.g. U56_RA_scan/irc_forward.log); use with "
                          "--point-index")
    src.add_argument("--geom-log",
                     help="path to a plain opt/freq log (e.g. "
                          "endpoint_prep_rc_reactant/endpoint_tight.log) -- uses its LAST "
                          "geometry, no --point-index")
    ap.add_argument("--point-index", type=int, default=None,
                    help="0-based index into --irc-log's own path points (required with "
                         "--irc-log). §39.114(2) targets: 4 (G16 point 5, arc~1.71) and 19 "
                         "(G16 point 20, arc~6.83, the last point before the crash)")
    ap.add_argument("--out-dir", required=True, help="directory to write the deck + manifest")
    ap.add_argument("--total-cores", type=int, default=1)
    ap.add_argument("--level", default="3",
                    help="qc_levels.json level key (default 3 = G-3/def2-SVPD, the geometry+"
                         "Hessian level these jobs actually ran at)")
    args = ap.parse_args(argv)
    if args.irc_log and args.point_index is None:
        ap.error("--point-index is required with --irc-log")
    return build(args.out_dir, irc_log=args.irc_log, point_index=args.point_index,
                geom_log=args.geom_log, total_cores=args.total_cores, level=args.level)


if __name__ == "__main__":
    sys.exit(main())
