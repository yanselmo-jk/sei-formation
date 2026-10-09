#!/usr/bin/env python3
"""Candidate B: a from-scratch reverse-arm IRC redo from `U56_RA_scan`'s certified TS geometry,
with a quartered `StepSize` and `recorrect=never` carried forward -- NOT a checkpoint restart
(`build_u56_ra_irc_recorrect_probe.py` is the restart tool; it does not apply here, there is no
checkpoint to restart from for this candidate, proposer12's own text, 02_METHOD_SPEC.md §39.124(2)).

WHY: Candidate A (the reverse-arm restart, `recorrect=never` only) got past the original
oscillating-gradient-angle failure cleanly, then ran into a DIFFERENT failure at its very next new
point: the Bulirsch-Stoer corrector took 11 cycles / 1536 sub-steps, still warned non-convergence,
and was forced to contract its accepted step to ~35% of nominal before the run self-terminated at
a "PES minimum" that failed this project's own distinctness test (§39.126 -- zero fresh SCF at the
declared point, everything downstream of a corrector fit the log itself flagged unreliable). That
is the signature of a fixed step too large for the local curvature, not an algorithm-family
problem -- `proposer13` ruled `StepSize` (not `EulerPC`) at `f=0.25` (quarter the nominal step) as
the mechanistically-matched fix (02_METHOD_SPEC.md §39.127), with `recorrect=never` carried
forward rather than dropped (dropping it would re-run into the ALREADY-SOLVED oscillating failure
before ever reaching the new problem near arc 2.0-2.3 this run exists to test).

🔴 MANDATORY POST-RUN READ, not just the final summary table (`proposer13`, §39.127): read the log
specifically at the point(s) landing near **arc 2.0-2.3** -- the exact region Candidate A's
`f=1.0` (nominal step) attempt broke down in. A clean, single-pass corrector step there (analogous
to Candidate A's own Point 6 restart step, §39.126) is the direct positive signal the `StepSize`
hypothesis is right. A repeat `WARNING: Bulirsch-Stoer Method is not Converging` at this smaller
step shows the underlying PES feature is more severe than a step-size fix alone can resolve --
escalate to `EulerPC` (or a finer `f`) rather than treating the run as inconclusive-but-acceptable.

🔴 [NEEDS VERIFICATION] `irc=(calcfc,reverse,recorrect=never,stepsize=...,maxpoints=...)` combined
this way has never been route-smoked on this project's cluster -- same standing limitation as
every other unsmoked IRC-keyword combination this round (`build_u56_ra_irc_recorrect_probe.py`'s
restart route, `build_u56_ra_stability_probe.py`'s `stable=opt`). No known SILENT-override
mechanism applies here specifically (unlike a checkpoint restart, there is no `.chk` to inherit a
stale option from) -- a malformed route fails at ~zero cost, same as every other route-smoke
failure this project treats as informative, not silent.

This is diagnostic-only: NOT wired into any plan Item, does not submit anything. Re-running into
the SAME `--out-dir` is NOT idempotent: if the deck or manifest already exist, `build()` refuses
to overwrite them (remove them or pick a new `--out-dir` for a deliberate clean rebuild) --
matching this project's own standing rule against a docstring asserting a safety property the
code does not have (the exact defect class already found and fixed once in the restart tool,
`05_STATE.md` §1f carry-over 3).

Usage:
    python3 tools/build_u56_ra_irc_stepsize_probe.py \\
        --job-dir /path/to/U56_RA_scan --out-dir /path/to/output_dir --total-cores 64
"""

import argparse
import json
import os
import sys

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG_ROOT)

from sei_pilot import basisset, config, version  # noqa: E402
from sei_pilot import solvent as solvent_mod  # noqa: E402
from sei_pilot.criteria import xyzgraph  # noqa: E402

#: [b0_reactions.json / endpoint_prep.sh, same convention build_u56_ra_stability_probe.py already
#: cites] every U56-2 reaction and its endpoints are the same reduced-radical family: doublet, net
#: neutral.
CHARGE = 0
MULT = 2

#: 🟢 [proposer13 §39.127, 02_METHOD_SPEC.md] `StepSize` over `EulerPC` -- the failure signature
#: (a forced step-contraction to ~35% of nominal, not an oscillating limit-cycle) picks a smaller
#: FIXED step, not a different integrator family. `recorrect=never` carries FORWARD (not dropped
#: for a "pure" StepSize test) -- both arms already passed the original oscillating-failure region
#: cleanly under it (stage 4, Candidate A); a default-recorrection Candidate B would re-encounter
#: that ALREADY-SOLVED failure at ~arc 1.7-2.0 before ever reaching the new problem near arc 2.1
#: that motivates changing the step size at all. Direction is `reverse` -- this candidate exists
#: specifically for U-56a condition 7's still-open reverse branch (§39.126); not parameterized,
#: this tool is scoped to exactly the ruled candidate, not a generic redo builder.
IRC_DIRECTION = "reverse"
IRC_RECORRECT_NEVER = True

#: 🟢 [proposer13 §39.128, 02_METHOD_SPEC.md -- SUPERSEDES this coder's own earlier §39.127-only
#: read, `stepsize=3`/`maxpoints=55`, kept in history via git/review log, not restated here] G16's
#: IRC `StepSize` keyword takes an integer in units of 0.01 CARTESIAN bohr per predictor step
#: -- 🔴 [critic17, 32nd review batch] NOT `0.01 Bohr*amu^(1/2)` as this comment (and §39.128,
#: which inherited the label from here) originally said: the reaction's own log shows G16
#: printing the SUPPLIED step in plain bohr (`Step size = 0.100 bohr` at the default N=10) and
#: only THEN, separately, converting it to the mass-weighted quantity actually used for
#: integration (`Integration on MW PES will use step size of 0.3421 sqrt(amu)*bohr`) -- two
#: different numbers/units for two different stages, not one figure in two names. `f = N/10` is
#: unaffected either way (both numbers scale together), so no ruled number changes, only this
#: label. (Same unit convention this project's own restart tool documents for its `--step-size`
#: CLI argument, `build_u56_ra_irc_recorrect_probe.py` -- that comment inherited the same
#: imprecise label and should be read with this correction too, though it is not wrong about
#: `f`.) G16's own default is `StepSize=10` (0.10 units) -- confirmed against BOTH arms' own
#: measured arc/frame rate at that default (0.341-0.342 arc/frame, §R39.81/82). §39.127's ruled
#: `f=0.25` x `StepSize=10` = 2.5 -- exactly between two
#: integers, not buildable as written. §39.127's criterion was never "f=0.25 as a target" -- it was
#: "stay below the corrector's own measured natural contraction scale (~0.35, Point 7's forced
#: 0.336->0.116 contraction), take the free margin since cost is confirmed non-binding." `f=0.30`
#: (stepsize=3, this coder's first pick) leaves only 0.05 margin below that scale; `f=0.20`
#: (stepsize=2) leaves 0.15 -- THREE TIMES the margin, at zero extra cost. §39.128's ruling:
#: `maxpoints` (below) is the number that was free to move (this coder's own margin-padded
#: estimate, not a physical or budget constraint) -- raise IT, don't widen the step and spend the
#: margin the whole point of picking f<0.35 was meant to buy.
IRC_STEPSIZE = 2

#: 🟢 [proposer13 §39.128] Explicit, NOT this project's usual `maxpoints=30` default. Points
#: needed to clear the `arc>=4.27` floor at `StepSize=2` (f=0.20): rate = 0.3415 * 0.20 = 0.0683
#: arc/point; 4.27 / 0.0683 ~= 62.5 points, minimum. Same +10% margin fraction proposer13 applied
#: going from f=0.25's ~50-point minimum to their own ruled 55: 62.5 * 1.10 ~= 68.75 -> 70 (round
#: number, proposer13's own figure, not re-derived by this coder). Stays well under engineer14's
#: informational soft ceiling of 200 (§R39.82 §4).
IRC_MAXPOINTS = 70

#: Derived, not ruled -- N(f) = 4.27 / (0.3415 * f) raw points to clear the arc floor
#: (§R39.82/83's own formula), evaluated at this tool's actual f=0.20 (StepSize=2). 4.27 /
#: (0.3415 * 0.20) = 62.52 -> ~63. Documentation only -- `IRC_MAXPOINTS` (the cap G16 actually
#: enforces) is the number that matters for the route; this is just for an honest "how many
#: points do we actually expect" estimate, so the manifest doesn't conflate the safety cap with
#: the targeted count.
IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR = 63


def _coordinate_block(atoms):
    return "\n".join("%-4s%16.8f%16.8f%16.8f" % (el, x, y, z) for el, x, y, z in atoms)


def build(job_dir, out_dir, level="3", total_cores=64):
    os.makedirs(out_dir, exist_ok=True)

    ts_xyz = os.path.join(job_dir, "ts.xyz")
    if not os.path.exists(ts_xyz):
        sys.stderr.write("no %s -- need the certified TS geometry to redo the IRC from "
                         "scratch (this tool has no checkpoint to restart from)\n" % ts_xyz)
        return 2

    chk_name = "irc_reverse_stepsize_probe.chk"
    gjf_path = os.path.join(out_dir, "irc_stepsize_probe.gjf")
    manifest_path = os.path.join(out_dir, "manifest.json")
    # 🔴 [same convention as build_u56_ra_irc_recorrect_probe.py's idempotency fix, 05_STATE.md
    # §1f carry-over 3] refuse rather than silently overwrite a previously-built deck/manifest --
    # this tool writes a fresh %chk directive (G16 creates that checkpoint itself when the job
    # actually runs; this script never writes chk bytes), so the deck/manifest are the only state
    # this script itself could clobber.
    for existing in (gjf_path, manifest_path):
        if os.path.exists(existing):
            sys.stderr.write(
                "refusing to overwrite existing %s -- remove it or pick a new --out-dir if you "
                "really want a clean rebuild\n" % existing)
            return 5

    with open(ts_xyz, errors="replace") as fh:
        ts_text = fh.read()
    frames = xyzgraph.read_xyz_frames(ts_text)
    if not frames:
        sys.stderr.write("no geometry parsed from %s\n" % ts_xyz)
        return 2
    atoms = frames[0][1]

    cfg = config.load("qc_levels.json", {})
    spec = cfg.get("gaussian16") or {}
    level_key = level if str(level).startswith("level") else ("level%s" % level)
    lvl = spec.get(level_key) or {}
    if not lvl:
        sys.stderr.write("unknown level: %s\n" % level)
        return 2

    try:
        deck = solvent_mod.resolve_solvent_deck(solvent_mod.load_policy(), None, "smoke")
    except (solvent_mod.SolventUndecided, solvent_mod.SolventDescriptorsMissing) as exc:
        sys.stderr.write("solvent_refused: %s\n" % exc)
        return 4
    solvent_fragment = deck["route_fragment"]
    solvent_lines = deck["extra_input_lines"]

    els = basisset.elements_in_xyz(ts_text)
    basis_block = None
    if (lvl.get("basis") or "").lower() == "gen":
        try:
            loaded = basisset.load_for_level(lvl, PKG_ROOT)
            basisset.check_coverage(els, loaded["text"],
                                    context="%s, molecule=%s" % (lvl.get("label", "?"), ts_xyz))
            basis_block = basisset.block(loaded["text"], only=els)
        except basisset.BasisError as exc:
            sys.stderr.write("%s\n" % exc)
            return 3

    irc_opts = ["calcfc", IRC_DIRECTION]
    if IRC_RECORRECT_NEVER:
        irc_opts.append("recorrect=never")
    irc_opts.append("stepsize=%d" % IRC_STEPSIZE)
    irc_opts.append("maxpoints=%d" % IRC_MAXPOINTS)
    route = ("#p nosymm %s/%s %s irc=(%s) Int(Grid=UltraFine)"
            % (lvl.get("functional", "?"), lvl.get("basis", "?"), solvent_fragment,
               ",".join(irc_opts)))

    with open(gjf_path, "w") as fh:
        fh.write("%%nprocshared=%d\n" % total_cores)
        fh.write("%mem=4GB\n")
        fh.write("%%chk=%s\n" % chk_name)
        fh.write(route + "\n\n")
        fh.write("sei_pilot irc_reverse_stepsize_probe %s\n\n" % level_key)
        fh.write("%d %d\n" % (CHARGE, MULT))
        fh.write(_coordinate_block(atoms) + "\n\n")
        if basis_block:
            fh.write(basis_block + "\n")
        if solvent_lines:
            fh.write("\n".join(solvent_lines) + "\n\n")

    manifest = {
        "purpose": "diagnostic (Candidate B, 02_METHOD_SPEC.md §39.127; 03_COMPUTE_PLAN.md "
                  "§R39.82/83) -- NOT a production job, not wired into any plan Item, not "
                  "submitted by this script",
        "question": "does a quartered StepSize (recorrect=never carried forward) let the reverse "
                   "IRC walk cleanly past arc 2.0-2.3, the region Candidate A's forced corrector "
                   "step-contraction and non-converging Bulirsch-Stoer fit broke down in "
                   "(§39.126)? A clean single-pass corrector step there confirms the StepSize "
                   "hypothesis; a repeat non-convergence warning means the PES feature needs "
                   "EulerPC or a finer step, not more of the same fix.",
        "mandatory_post_run_check": (
            "read the log at the point(s) landing near arc 2.0-2.3 SPECIFICALLY, not just the "
            "final summary table (proposer13 §39.127) -- that is Candidate A's own breakdown "
            "region."),
        "source_ts_geometry": os.path.abspath(ts_xyz),
        "not_a_restart": "from-scratch IRC via calcfc from the certified TS geometry -- no "
                        "checkpoint involved, unlike build_u56_ra_irc_recorrect_probe.py",
        "direction": IRC_DIRECTION,
        "recorrect_never": IRC_RECORRECT_NEVER,
        "stepsize": IRC_STEPSIZE,
        "stepsize_f": IRC_STEPSIZE / 10.0,
        "maxpoints": IRC_MAXPOINTS,
        "deck_file": os.path.basename(gjf_path),
        "checkpoint_file": chk_name,
        "route": route,
        "level": level_key, "level_label": lvl.get("label"),
        "charge": CHARGE, "multiplicity": MULT,
        "route_syntax_status": (
            "[NEEDS VERIFICATION] `irc=(calcfc,reverse,recorrect=never,stepsize=...,"
            "maxpoints=...)` combined this way has never been route-smoked on this project's "
            "cluster. No known silent-override mechanism applies (no checkpoint to inherit a "
            "stale option from) -- a malformed route fails at ~zero cost, same as any other "
            "route-smoke failure this project treats as informative, not silent."),
        "estimated_cost": (
            "from-scratch IRC redo, ~%d points expected to clear the arc>=4.27 floor "
            "(StepSize=%d, f=%.2f -- IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR, NOT maxpoints=%d, "
            "which is a safety cap with margin, not the target count) at 1.92-3.63 core-h/pt "
            "[MEASURED anchor, ESTIMATE scaling] -- targeted/expected 121.0-228.7 core-h (63 "
            "points, most likely actual cost), requested ceiling 134.4-254.1 core-h (70 points, "
            "full maxpoints=70 budget consumed) -- engineer14's CONFIRMED re-derivation from "
            "first principles (§R39.84, 03_COMPUTE_PLAN.md:19716-19769), superseding proposer13's "
            "own earlier extrapolation in §39.128 (which turned out to land within rounding of "
            "this figure, confirmed not corrected)"
            % (IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR, IRC_STEPSIZE, IRC_STEPSIZE / 10.0,
               IRC_MAXPOINTS)),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("[build_u56_ra_irc_stepsize_probe] wrote %s" % gjf_path)
    print("[build_u56_ra_irc_stepsize_probe] route: %s" % route)
    print("[build_u56_ra_irc_stepsize_probe] geometry from: %s (%d atoms)" % (ts_xyz, len(atoms)))
    print("[build_u56_ra_irc_stepsize_probe] manifest: %s" % manifest_path)
    print("[build_u56_ra_irc_stepsize_probe] NOT SUBMITTED, and route syntax NOT independently "
          "verified against a live G16 -- see manifest.json's route_syntax_status. MANDATORY: "
          "read the returned log near arc 2.0-2.3 specifically, not just the summary table.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job-dir", required=True,
                    help="U56_RA_scan's job dir (needs ts.xyz -- the certified TS geometry, "
                         "no checkpoint required)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--level", default="3")
    # 🔴 [critic16/critic17, carried over from build_u56_ra_irc_recorrect_probe.py -- the same
    # tool defect class has now hit this reverse-arm work item twice already] default is 64, NOT
    # 1 -- at maxpoints=70 a 1-core run would be well past ADR-114's 48h cap (worse: more points
    # than either the recorrect-probe tool's 24 or this tool's own §39.127-superseded 55). Still
    # explicitly overridable.
    ap.add_argument("--total-cores", type=int, default=64)
    args = ap.parse_args(argv)
    return build(args.job_dir, args.out_dir, args.level, args.total_cores)


if __name__ == "__main__":
    sys.exit(main())
