#!/usr/bin/env python3
"""EulerPC escalation: a from-scratch reverse-arm IRC redo from `U56_RA_scan`'s certified TS
geometry, swapping HPC's predictor for `EulerPC` while keeping `stepsize=2`/`recorrect=never`
identical to Candidate B (`build_u56_ra_irc_stepsize_probe.py`) -- a BACKUP tier, staged
alongside Candidate B for one cluster round-trip (user/lead logistics call), NOT a promotion:
`StepSize` (Candidate B) still runs and is read FIRST. Only submit this if Candidate B's own
mandatory checks show it failed (02_METHOD_SPEC.md §39.127/§39.129).

WHY, AND WHY THIS IS A WEAKER SECOND BET THAN §39.127 ORIGINALLY IMPLIED: `proposer13` checked
Gaussian's own IRC keyword documentation directly (gaussian.com/irc/, §39.129) rather than
relying on memory -- `EulerPC` does **NOT** replace HPC's corrector, it only replaces HPC's
predictor (the initial per-point guess) with a cruder, first-order Euler step, while feeding
that guess into the EXACT SAME Bulirsch-Stoer/DWI corrector that emitted `WARNING: Bulirsch-
Stoer Method is not Converging` at Candidate A's Point 7 (§39.126). If the pathology is
corrector-side (which the observed symptoms -- the BS non-convergence warning, the escalating
cycle count, the DWI-internal gradient std-dev blowup -- are specifically about, not the
predictor), a cruder predictor feeding the same corrector is not obviously going to fix it, and
could plausibly stress the same corrector MORE (a worse initial guess typically needs more, not
fewer, corrector recorrection cycles). `recorrect=never` IS a valid, meaningful option for
`EulerPC` too (confirmed against the same doc page, `ReCorrect` "Controls testing-and-
recomputing for the correction step of HPC and EulerPC IRCs") -- carried forward for the same
reason as Candidate B: dropping it would re-run into the already-solved oscillating failure.

`stepsize=2` is kept IDENTICAL to Candidate B on purpose, not re-tuned -- a single-variable-
change discipline (§39.129(3)): if this tier is ever run, the only variable that changes
relative to Candidate B is the predictor algorithm, so a result (pass or repeat-failure) is
interpretable as being about the predictor/corrector combination, not confounded with a
simultaneous step-size change. `maxpoints=100` is a deliberately WIDER hedge than Candidate B's
`maxpoints=70` (~60% margin over the ~62.5-point nominal-rate minimum vs. B's ~10%) because
EulerPC's realized arc-per-point is doubly unmeasured: (a) a cruder predictor may need more
corrector contraction per point than the LQA predictor `StepSize` uses, and (b) no per-point
cost or success rate exists for this algorithm on this reaction at all.

🔴 MANDATORY POST-RUN CHECKS, all four (§39.129, engineer14's addendum in the same section) --
none of these substitute for the others:
  1. Euler-predictor echo -- confirm EulerPC actually ran, not a silent fallback to HPC. HPC's
     own predictor echoes `Using LQA Reaction Path Following.` in every log this project has
     read so far; the equivalent Euler-predictor string is `[NEEDS VERIFICATION]` -- this
     project has no G16 install and has never run EulerPC before, so the POSITIVE string cannot
     be confirmed from documentation alone. At minimum, confirm `Using LQA Reaction Path
     Following.` does NOT appear (its presence would mean EulerPC silently fell back to HPC --
     the same symptom shape as Candidate B's own result, mislabeled).
  2. `Recorrection delta-x convergence threshold:` grep (expect 0 -- confirms recorrect=never
     took effect here too; never assume it carries over from a different keyword combination).
  3. Direct read at arc 2.0-2.3 -- Candidate A's own breakdown region, same as Candidate B.
  4. Tier-specific: does `WARNING: Bulirsch-Stoer Method is not Converging` recur there? This is
     the direct test of §39.129's central finding (shared corrector) -- read BEFORE claiming
     EulerPC "worked" or "didn't work" for a reason distinct from Candidate B's own result.

🔴 [NEEDS VERIFICATION] `irc=(calcfc,reverse,EulerPC,recorrect=never,stepsize=...,maxpoints=...)`
combined this way has never been route-smoked anywhere in this project -- unlike Candidate B,
this tier's keyword combination itself (not just its outcome) is entirely unverified, which is
why (unlike Candidate B) a route-syntax smoke IS recommended here (`--smoke`, `maxpoints=2`) --
run and check it BEFORE the full `maxpoints=100` deck.

This is diagnostic-only: NOT wired into any plan Item, does not submit anything. Re-running into
the SAME `--out-dir` is NOT idempotent: if the deck or manifest already exist, `build()` refuses
to overwrite them (remove them or pick a new `--out-dir` for a deliberate clean rebuild).

Usage:
    python3 tools/build_u56_ra_irc_eulerpc_probe.py \\
        --job-dir /path/to/U56_RA_scan --out-dir /path/to/output_dir --total-cores 64 --smoke
    python3 tools/build_u56_ra_irc_eulerpc_probe.py \\
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

#: [b0_reactions.json / endpoint_prep.sh, same convention this reverse-arm tool family already
#: cites] every U56-2 reaction and its endpoints are the same reduced-radical family: doublet,
#: net neutral.
CHARGE = 0
MULT = 2

#: 🟢 [proposer13 §39.129, 02_METHOD_SPEC.md] Direction/recorrect are unchanged from Candidate B
#: (`build_u56_ra_irc_stepsize_probe.py`) -- this tier's ONLY route difference from B is the
#: EulerPC predictor keyword and the wider maxpoints hedge below. Not parameterized, this tool
#: is scoped to exactly the ruled escalation, not a generic redo builder.
IRC_DIRECTION = "reverse"
IRC_RECORRECT_NEVER = True
IRC_EULERPC = True

#: 🟢 [proposer13 §39.129(3)] Deliberately IDENTICAL to Candidate B's `IRC_STEPSIZE`, not
#: re-tuned -- single-variable-change discipline: if EulerPC is ever run, the only thing that
#: changed relative to B is the predictor algorithm, so a pass/repeat-failure result is
#: attributable to the predictor/corrector combination alone. See
#: build_u56_ra_irc_stepsize_probe.py's own IRC_STEPSIZE comment for the unit-label correction
#: (0.01 CARTESIAN bohr/step, not Bohr*amu^(1/2) -- critic17, 32nd review batch) and the f=0.20
#: margin reasoning; both apply unchanged here since the value itself is unchanged.
IRC_STEPSIZE = 2

#: 🟢 [proposer13 §39.129(2), engineer14 §R39.85 -- confirmed, no revision] ~60% margin over the
#: ~62.5-point nominal-rate minimum (same 4.27/(0.3415*0.20) arc-floor calc as Candidate B,
#: identical stepsize), roughly 6x B's own +10% margin fraction -- deliberately wider because
#: EulerPC's realized arc-per-point is doubly unmeasured (cruder predictor may force more
#: corrector contraction per point than B's LQA predictor, AND no per-point rate exists for this
#: algorithm on this reaction at all). A judgment call, not a measurement -- proposer13's own
#: figure, not re-derived by this coder. 100 - 63 (the same nominal-rate estimate as B, since
#: stepsize is unchanged) = 37 points / 58.7% margin (engineer14 §R39.85, confirmed).
IRC_MAXPOINTS_FULL = 100

#: 🟢 [proposer13 §39.129 "Recommend a cheap 1-2 point route-syntax smoke... for this tier
#: specifically"; engineer14 §R39.85 independently endorses the same, for a second reason (an
#: early real per-point-cost read)] Unlike Candidate B (where a smoke could never reach the arc
#: 2.0-2.3 region that matters), THIS tier's keyword combination itself
#: (EulerPC+recorrect=never+stepsize+maxpoints together) has never run anywhere in this project
#: -- a malformed combination failing fast at near-zero cost is worth the ~2 extra minutes of
#: calendar time. `--smoke` selects this value instead of IRC_MAXPOINTS_FULL; still an explicit,
#: ruled constant either way, never a silent default.
IRC_MAXPOINTS_SMOKE = 2

#: Derived, not ruled -- same formula as Candidate B (4.27 / (0.3415 * f)), evaluated at this
#: tool's f=0.20 (identical stepsize to B, so the same nominal point estimate applies --
#: engineer14 §R39.85 confirms this explicitly: "same arc-floor calc as §R39.84"). Documentation
#: only, not the number G16 actually enforces (IRC_MAXPOINTS_FULL/_SMOKE are).
IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR = 63


def _coordinate_block(atoms):
    return "\n".join("%-4s%16.8f%16.8f%16.8f" % (el, x, y, z) for el, x, y, z in atoms)


def build(job_dir, out_dir, level="3", total_cores=64, smoke=False):
    os.makedirs(out_dir, exist_ok=True)

    ts_xyz = os.path.join(job_dir, "ts.xyz")
    if not os.path.exists(ts_xyz):
        sys.stderr.write("no %s -- need the certified TS geometry to redo the IRC from "
                         "scratch (this tool has no checkpoint to restart from)\n" % ts_xyz)
        return 2

    maxpoints = IRC_MAXPOINTS_SMOKE if smoke else IRC_MAXPOINTS_FULL
    tag = "eulerpc_smoke" if smoke else "eulerpc_probe"
    chk_name = "irc_reverse_%s.chk" % tag
    gjf_path = os.path.join(out_dir, "irc_%s.gjf" % tag)
    manifest_path = os.path.join(out_dir, "manifest_%s.json" % tag)
    # 🔴 [same convention as build_u56_ra_irc_stepsize_probe.py / build_u56_ra_irc_recorrect_
    # probe.py's idempotency fix, 05_STATE.md §1f carry-over 3] refuse rather than silently
    # overwrite a previously-built deck/manifest. Smoke and full decks use DIFFERENT filenames
    # (the `tag` above) specifically so both can be built into the SAME --out-dir without either
    # clobbering the other -- staging them side by side is the whole point of this tool.
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

    # 🟢 [proposer13 §39.129(1)] exact ordering from the ruled route text:
    # irc=(calcfc,reverse,EulerPC,recorrect=never,stepsize=2,maxpoints=100)
    irc_opts = ["calcfc", IRC_DIRECTION]
    if IRC_EULERPC:
        irc_opts.append("EulerPC")
    if IRC_RECORRECT_NEVER:
        irc_opts.append("recorrect=never")
    irc_opts.append("stepsize=%d" % IRC_STEPSIZE)
    irc_opts.append("maxpoints=%d" % maxpoints)
    route = ("#p nosymm %s/%s %s irc=(%s) Int(Grid=UltraFine)"
            % (lvl.get("functional", "?"), lvl.get("basis", "?"), solvent_fragment,
               ",".join(irc_opts)))

    with open(gjf_path, "w") as fh:
        fh.write("%%nprocshared=%d\n" % total_cores)
        fh.write("%mem=4GB\n")
        fh.write("%%chk=%s\n" % chk_name)
        fh.write(route + "\n\n")
        fh.write("sei_pilot irc_reverse_%s %s\n\n" % (tag, level_key))
        fh.write("%d %d\n" % (CHARGE, MULT))
        fh.write(_coordinate_block(atoms) + "\n\n")
        if basis_block:
            fh.write(basis_block + "\n")
        if solvent_lines:
            fh.write("\n".join(solvent_lines) + "\n\n")

    manifest = {
        "purpose": "diagnostic (EulerPC escalation, 02_METHOD_SPEC.md §39.129; "
                  "03_COMPUTE_PLAN.md §R39.85) -- BACKUP TIER, staged for logistics alongside "
                  "Candidate B, NOT a promotion: only submit if Candidate B's own mandatory "
                  "checks show it failed. NOT a production job, not wired into any plan Item, "
                  "not submitted by this script.",
        "smoke": smoke,
        "question": ("route-syntax validation only (maxpoints=2) -- cannot reach arc 2.0-2.3, "
                    "says nothing about the EulerPC hypothesis itself" if smoke else
                    "does swapping HPC's predictor for EulerPC (recorrect=never and stepsize=2 "
                    "unchanged from Candidate B) let the reverse IRC walk cleanly past arc "
                    "2.0-2.3? EulerPC shares HPC's own Bulirsch-Stoer/DWI corrector (confirmed "
                    "from Gaussian's documentation, §39.129) -- a repeat non-convergence "
                    "warning there would be direct evidence the pathology is corrector-side, "
                    "not predictor-side, since the ONLY variable changed vs. Candidate B is "
                    "the predictor."),
        "mandatory_post_run_checks": [
            "Euler-predictor echo: confirm EulerPC actually ran, not a silent fallback to HPC "
            "-- the positive Euler-predictor string is [NEEDS VERIFICATION] (no G16 install, "
            "never run before); at minimum confirm 'Using LQA Reaction Path Following.' (HPC's "
            "own predictor echo) does NOT appear.",
            "Recorrection delta-x convergence threshold: grep -ac, expect 0.",
            "read the log at the point(s) landing near arc 2.0-2.3 SPECIFICALLY, not just the "
            "final summary table -- Candidate A's own breakdown region.",
            "tier-specific: does 'WARNING: Bulirsch-Stoer Method is not Converging' recur near "
            "arc 2.0-2.3 -- the direct test of the shared-corrector finding (§39.129); read "
            "before claiming EulerPC worked or did not work for a reason distinct from "
            "Candidate B's own result.",
        ],
        "source_ts_geometry": os.path.abspath(ts_xyz),
        "not_a_restart": "from-scratch IRC via calcfc from the certified TS geometry -- no "
                        "checkpoint involved, unlike build_u56_ra_irc_recorrect_probe.py",
        "single_variable_change_vs_candidate_b": (
            "direction, recorrect=never, and stepsize are all IDENTICAL to Candidate B -- the "
            "only route difference is the EulerPC predictor keyword and the wider maxpoints "
            "hedge, so a pass/repeat-failure result is attributable to the predictor/corrector "
            "combination alone, not confounded with a simultaneous step-size change "
            "(§39.129(3))."),
        "direction": IRC_DIRECTION,
        "recorrect_never": IRC_RECORRECT_NEVER,
        "eulerpc": IRC_EULERPC,
        "stepsize": IRC_STEPSIZE,
        "stepsize_f": IRC_STEPSIZE / 10.0,
        "maxpoints": maxpoints,
        "deck_file": os.path.basename(gjf_path),
        "checkpoint_file": chk_name,
        "route": route,
        "level": level_key, "level_label": lvl.get("label"),
        "charge": CHARGE, "multiplicity": MULT,
        "route_syntax_status": (
            "[NEEDS VERIFICATION] `irc=(calcfc,reverse,EulerPC,recorrect=never,stepsize=...,"
            "maxpoints=...)` combined this way has never been route-smoked anywhere in this "
            "project -- unlike Candidate B, this tier's keyword COMBINATION itself is entirely "
            "unverified (not just its outcome), which is why a syntax smoke is recommended "
            "before the full run. No known silent-override mechanism applies (no checkpoint to "
            "inherit a stale option from), but EulerPC could in principle be silently ignored "
            "and fall back to G16's default HPC without erroring -- see "
            "mandatory_post_run_checks[0]."),
        "estimated_cost": (
            (
                "route-syntax smoke, %d points -- 1.9-14.6 core-h [ESTIMATE] (engineer14 "
                "§R39.85, 03_COMPUTE_PLAN.md:19832-19841) -- validates syntax AND buys an early "
                "real per-point-cost read before committing the full maxpoints=100 budget"
                % maxpoints
            ) if smoke else (
                "from-scratch IRC redo, ~%d points expected to clear the arc>=4.27 floor "
                "(StepSize=%d unchanged from Candidate B, f=%.2f -- "
                "IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR, NOT maxpoints=%d, which is a wider "
                "safety hedge, not the target count) at a WIDENED 1.92-7.3 core-h/pt bracket "
                "[MEASURED anchor at the optimistic end, ESTIMATE -- 2x arbitrary widening at "
                "the pessimistic end for the cruder-predictor/more-corrector-work risk, "
                "engineer14 §R39.85] -- targeted/expected 121.0-459.9 core-h (63 points), "
                "requested ceiling 192.0-730.0 core-h (100 points, full maxpoints=100 budget "
                "consumed) -- engineer14 §R39.85 (03_COMPUTE_PLAN.md:19817-19842), CONFIRMED "
                "against proposer13's own §39.129(2) derivation, no revision needed"
                % (IRC_STEPSIZE_ESTIMATED_POINTS_TO_FLOOR, IRC_STEPSIZE, IRC_STEPSIZE / 10.0,
                   maxpoints)
            )),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    tool_tag = "build_u56_ra_irc_eulerpc_probe"
    print("[%s] wrote %s" % (tool_tag, gjf_path))
    print("[%s] route: %s" % (tool_tag, route))
    print("[%s] geometry from: %s (%d atoms)" % (tool_tag, ts_xyz, len(atoms)))
    print("[%s] manifest: %s" % (tool_tag, manifest_path))
    print("[%s] NOT SUBMITTED, and route syntax NOT independently verified against a live G16 "
          "-- see manifest's route_syntax_status. BACKUP TIER: only submit if Candidate B's own "
          "checks show it failed. MANDATORY: read manifest's mandatory_post_run_checks before "
          "trusting any result." % tool_tag)
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job-dir", required=True,
                    help="U56_RA_scan's job dir (needs ts.xyz -- the certified TS geometry, "
                         "no checkpoint required)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--level", default="3")
    # 🔴 [critic16/critic17, carried over -- the same tool defect class has now hit this
    # reverse-arm work item multiple times] default is 64, NOT 1 -- at maxpoints=100 (the
    # widest maxpoints on this work item) a 1-core run would be far past ADR-114's 48h cap.
    # Still explicitly overridable.
    ap.add_argument("--total-cores", type=int, default=64)
    ap.add_argument("--smoke", action="store_true",
                    help="build the 1-2 point (maxpoints=%d) route-syntax smoke instead of the "
                         "full maxpoints=%d deck -- proposer13/engineer14 both recommend "
                         "running this FIRST for this tier specifically (unlike Candidate B)"
                         % (IRC_MAXPOINTS_SMOKE, IRC_MAXPOINTS_FULL))
    args = ap.parse_args(argv)
    return build(args.job_dir, args.out_dir, args.level, args.total_cores, args.smoke)


if __name__ == "__main__":
    sys.exit(main())
