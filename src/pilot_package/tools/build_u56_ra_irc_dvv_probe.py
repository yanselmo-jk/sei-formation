#!/usr/bin/env python3
"""DVV escalation: a from-scratch reverse-arm IRC redo from `U56_RA_scan`'s certified TS
geometry, using the Damped Velocity Verlet integrator (`IRC=DVV`) -- the THIRD, backup-of-a-
backup tier, staged alongside Candidate B and the EulerPC escalation for one cluster round-trip
(user/lead logistics call), NOT a promotion: `StepSize` (Candidate B) runs and is read FIRST,
`EulerPC` second. Only submit anything built by this tool if BOTH Candidate B AND EulerPC have
already run and their own mandatory checks show they failed (02_METHOD_SPEC.md §39.130).

WHY THIS TIER IS DIFFERENT IN KIND, NOT JUST A THIRD OPTION ON THE SAME LIST: `proposer13`
checked Gaussian's own IRC documentation (gaussian.com/irc/, §39.130) -- `DVV`'s doc entry is
thin (three of six things checked are not covered by the primary source at all), but the
underlying method paper (Hratchian & Schlegel, J. Phys. Chem. A 2002, 106, 165-169 -- abstract-
level detail only, found via search, NOT the full paper, flagged accordingly) describes a
velocity-Verlet propagator with an ADAPTIVE time step, whose stated advantage is that "the
Hessian does not need to be calculated" at every step -- structurally unrelated to the
Bulirsch-Stoer/DWI corrector that both HPC (Candidate B) and EulerPC ride on and that failed at
Candidate A's Point 7 (§39.126). **This is the one tier that can actually distinguish "the
corrector itself is the problem" from "the underlying PES region is simply hard for any
reasonable path-follower"** -- if StepSize and EulerPC both fail with the same Bulirsch-Stoer
warning signature, a clean DVV pass would implicate the corrector specifically; comparable
difficulty under genuinely different machinery would point at the PES region itself instead.

THREE RUNGS, a fallback ladder usable on the cluster WITHOUT another spec round-trip -- ALL SIX
decks (3 rungs x {smoke, full}) are pre-built by this tool so nobody ever hand-edits a route
string on the cluster (a real Gaussian input syntax error is easy to introduce and expensive to
discover only after a real run):
  rung 1 (`--rung 1`, DEFAULT, preferred):  irc=(calcfc,reverse,DVV,stepsize=2,maxpoints=...)
  rung 2 (`--rung 2`, if rung 1's SMOKE errors specifically on the calcfc+DVV combination):
                                             irc=(reverse,DVV,stepsize=2,maxpoints=...)
  rung 3 (`--rung 3`, if rung 2's SMOKE ALSO errors -- 🔴 scientifically undesirable, not just
    a syntax fallback: discards this project's available analytic Hessians; worth a second look
    from the lead/user before spending the full core-h ceiling on it, not an automatic step):
                                             irc=(reverse,DVV,GradientOnly,stepsize=2,maxpoints=...)
Try rung 1's smoke first. Only move to rung 2 if rung 1's smoke ERRORS (not merely "looks odd"
-- a route-syntax rejection specifically). Same for rung 2 -> rung 3. If rung 3 is reached,
`03_COMPUTE_PLAN.md` §R39.86's own caveat applies: treat its pessimistic per-point rate
(10.9 core-h/pt) as a FLOOR, not a ceiling, for that rung, and re-smoke at rung 3 specifically
-- do NOT reuse rung 1's smoke result, the cost profile is not the same question.

TWO DELIBERATE OMISSIONS, not oversights -- do not "helpfully" add either back:
  - `recorrect=never` is OMITTED ENTIRELY at every rung (`proposer13` §39.130(2)): `ReCorrect`'s
    documented default is already `Never` for "other integrators" (DVV is neither HPC nor
    EulerPC), and DVV is a Verlet-type propagator, not a predictor-corrector method -- there is
    no "corrector" for `ReCorrect` to control in the first place. Writing it risks either a
    harmless no-op or a route-syntax rejection for a keyword that may not apply to this
    algorithm at all.
  - No `--total-cores` default other than 64, same as every tool on this work item.

MANDATORY POST-RUN CHECKS, per §39.130 (a positive-AND-negative pair, neither alone is enough):
  1. POSITIVE: the log's `GENERAL PARAMETERS` block prints `Integration scheme           = HPC`
     in EVERY log this project has produced so far (confirmed, `irc_reverse.log:166`) -- confirm
     this run's equivalent line reads something OTHER than `HPC`. The exact string DVV prints
     is `[NEEDS VERIFICATION]` -- this project has never run DVV before; read it directly from
     the smoke's own returned log, that is exactly what the smoke is for.
  2. NEGATIVE, the sharper test: grep for `Bulirsch-Stoer` anywhere in the log, expect ZERO
     occurrences. Its presence would mean DVV did NOT actually run as a distinct algorithm
     regardless of what the `Integration scheme` line claims -- the same "silently got HPC
     instead" risk named for EulerPC (§39.129 addendum), applied to the tier where it would be
     easiest to miss (rc=0, normal termination, no reason to suspect anything unless checked).
  3. `stepsize=2` is included for the paper trail but must NOT be trusted to mean the same thing
     it does for HPC/EulerPC -- DVV's adaptive stepping may honor it as a target, override it as
     a hint, or ignore it entirely (`[NEEDS VERIFICATION]`). Read the REALIZED arc-per-point
     rate directly from the log, do not assume the requested value was honored.
  4. Direct read at arc 2.0-2.3, same as every other tier, PLUS whether any corrector-style
     warning appears there at all -- its absence OR presence under genuinely different
     machinery is informative either way, not just a pass/fail gate.
  5. NO `Recorrection delta-x convergence threshold:` grep for this tier -- the keyword is
     omitted on purpose (see above), so this check does not apply here. Its absence from this
     tool's mandatory-checks list is deliberate, not a dropped check.

This is diagnostic-only: NOT wired into any plan Item, does not submit anything. Re-running into
the SAME `--out-dir` is NOT idempotent: if a deck or manifest already exists for the requested
rung/smoke combination, `build()` refuses to overwrite it.

Usage:
    python3 tools/build_u56_ra_irc_dvv_probe.py \\
        --job-dir /path/to/U56_RA_scan --out-dir /path/to/output_dir --total-cores 64 \\
        --rung 1 --smoke
    python3 tools/build_u56_ra_irc_dvv_probe.py \\
        --job-dir /path/to/U56_RA_scan --out-dir /path/to/output_dir --total-cores 64 --rung 1
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

#: 🟢 [proposer13 §39.130(3), engineer14 §R39.86] Deliberately IDENTICAL VALUE to Candidate
#: B/EulerPC's stepsize -- included "for the paper trail," NOT because DVV's adaptive stepping
#: is known to honor it the same way (`[NEEDS VERIFICATION]` -- DVV's own adaptive time-step
#: control may treat this as a target, a hint, or ignore it entirely). Do not read its presence
#: in the route as evidence it controls anything until the mandatory post-run check (realized
#: arc-per-point rate from the log) confirms it.
IRC_STEPSIZE = 2

#: 🟢 [proposer13 §39.130(2)] Deliberately OMITTED at every rung -- do not add `recorrect=never`
#: "for consistency" with Candidate B/EulerPC. `ReCorrect`'s documented default is already
#: `Never` for "other integrators" (DVV is neither HPC nor EulerPC), and DVV is a Verlet-type
#: propagator, not a predictor-corrector method -- there is no corrector for `ReCorrect` to
#: control. Writing it risks a harmless no-op at best, a route-syntax rejection at worst, for a
#: keyword combination that may not apply to this algorithm.
IRC_RECORRECT_NEVER = False

#: 🟢 [proposer13 §39.130 "same hedge level as EulerPC... stated as [ESTIMATE]"; engineer14
#: §R39.86, ceiling-only pricing, no targeted/expected figure -- explicitly not produced this
#: round because DVV's per-point cost AND point-count-per-arc are BOTH unmeasured, unlike B/
#: EulerPC where at least one axis was anchored] 100.0-1090.0 core-h ceiling (widest bracket
#: priced on this work item -- the width is the honest signal, not a defect in the estimate).
IRC_MAXPOINTS_FULL = 100

#: 🟢 [proposer13 addendum, engineer14 §R39.86 -- "endorsing the widened smoke (2-3 points, not
#: 1-2)... the only cheap way to learn whether stepsize=2 is honored at all under DVV's adaptive
#: control"] 3, the upper end of the ruled 2-3 range -- more points give a better read on
#: whether the per-point rate is stabilizing (the actual reason for widening beyond EulerPC's
#: 1-2), which needs more than the bare minimum 2 points to show a trend at all.
IRC_MAXPOINTS_SMOKE = 3

#: 🟢 [proposer13 §39.130(1)] The three-rung fallback ladder, exact IRC-option lists (order
#: matches the ruled route text exactly -- calcfc/reverse/DVV/[GradientOnly]/stepsize/
#: maxpoints). Rung 1: preferred, keeps calcfc for the initial curvature at the TS (every other
#: route in this project uses it for the same reason -- it is what tells the IRC which way
#: "reverse" points). Rung 2: drop calcfc ONLY if rung 1's smoke ERRORS specifically on the
#: calcfc+DVV combination -- let G16 apply its own default initial-direction handling. Rung 3:
#: ONLY if rung 2's smoke ALSO errors -- add GradientOnly. 🔴 [critic17, 34th review batch]
#: CITATION CORRECTED: §39.130 (and this comment, inherited from it -- proposer13 notified at
#: source) misattributed "the default for IRC=GradientOnly calculations" to DVV's own doc
#: entry; DVV's entire gaussian.com/irc/ entry is one sentence ("Use the damped velocity
#: verlet integrator [Hratchian02]") and says nothing about GradientOnly. The real, sharper
#: fact (from `GradientOnly`'s OWN entry): "Can be combined with EulerPC (the default), HPC,
#: Euler, or DVV." Rung 3's route is unaffected -- `GradientOnly` is documented to combine with
#: `DVV` regardless of which one is "the default" -- but this makes rung 3 the rung where a
#: dropped/ignored `DVV` keyword silently falls back to `GradientOnly`'s OWN default algorithm
#: (`EulerPC`) at rc=0, the exact Bulirsch-Stoer-corrector machinery this whole tier exists to
#: avoid. Checks 1/2 (Euler-predictor absence / Integration-scheme echo, Bulirsch-Stoer
#: negative test) are NOT optional at rung 3 specifically -- they are the only thing that would
#: catch this silent-wrong-algorithm failure mode there. 🔴 Rung 3 is flagged scientifically
#: undesirable, not just a syntax fallback (discards this project's available analytic
#: Hessians) -- worth a second look from the lead/user before spending real core-h on it, not
#: an automatic next step after rung 2 fails.
def _irc_opts_for_rung(rung, maxpoints):
    if rung not in (1, 2, 3):
        raise ValueError("rung must be 1, 2, or 3, got %r" % (rung,))
    opts = []
    if rung == 1:
        opts.append("calcfc")
    opts.append("reverse")
    opts.append("DVV")
    if rung == 3:
        opts.append("GradientOnly")
    opts.append("stepsize=%d" % IRC_STEPSIZE)
    opts.append("maxpoints=%d" % maxpoints)
    return opts


def _coordinate_block(atoms):
    return "\n".join("%-4s%16.8f%16.8f%16.8f" % (el, x, y, z) for el, x, y, z in atoms)


def build(job_dir, out_dir, level="3", total_cores=64, rung=1, smoke=False):
    os.makedirs(out_dir, exist_ok=True)

    ts_xyz = os.path.join(job_dir, "ts.xyz")
    if not os.path.exists(ts_xyz):
        sys.stderr.write("no %s -- need the certified TS geometry to redo the IRC from "
                         "scratch (this tool has no checkpoint to restart from)\n" % ts_xyz)
        return 2
    if rung not in (1, 2, 3):
        sys.stderr.write("--rung must be 1, 2, or 3, got %r\n" % (rung,))
        return 2

    maxpoints = IRC_MAXPOINTS_SMOKE if smoke else IRC_MAXPOINTS_FULL
    tag = "dvv_rung%d_%s" % (rung, "smoke" if smoke else "full")
    chk_name = "irc_reverse_%s.chk" % tag
    gjf_path = os.path.join(out_dir, "irc_%s.gjf" % tag)
    manifest_path = os.path.join(out_dir, "manifest_%s.json" % tag)
    # 🔴 [same convention as the rest of this reverse-arm tool family, 05_STATE.md §1f
    # carry-over 3] refuse rather than silently overwrite. Every rung/smoke combination uses a
    # DIFFERENT filename (the `tag` above) specifically so all six can be built into the SAME
    # --out-dir without any pair clobbering each other -- pre-building the whole ladder is the
    # whole point of this tool.
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

    assert not IRC_RECORRECT_NEVER   # see IRC_RECORRECT_NEVER's own comment -- must stay False
    irc_opts = _irc_opts_for_rung(rung, maxpoints)
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

    rung_note = {
        1: "preferred rung -- calcfc kept for the initial curvature at the TS",
        2: "fallback rung 2 -- calcfc DROPPED (only reach this rung if rung 1's SMOKE errored "
           "specifically on the calcfc+DVV combination)",
        3: "fallback rung 3 -- calcfc DROPPED, GradientOnly ADDED. Scientifically undesirable "
           "(discards this project's available analytic Hessians), not just a syntax fallback "
           "-- worth a second look before spending real core-h here. If reached, treat "
           "engineer14's pessimistic 10.9 core-h/pt as a FLOOR for this rung, and re-smoke "
           "specifically at rung 3 -- do not reuse rung 1's smoke result. GradientOnly's OWN "
           "documented default algorithm is EulerPC (Bulirsch-Stoer corrector, the exact "
           "machinery this whole tier exists to avoid) -- checks 1/2 (Integration-scheme "
           "echo, Bulirsch-Stoer negative test) are NOT optional at this rung specifically, "
           "they are the only thing that would catch a silently-dropped DVV keyword here.",
    }[rung]

    manifest = {
        "purpose": "diagnostic (DVV escalation, 02_METHOD_SPEC.md §39.130; 03_COMPUTE_PLAN.md "
                  "§R39.86) -- THIRD-TIER BACKUP, staged for logistics alongside Candidate B "
                  "and the EulerPC escalation, NOT a promotion: only submit if BOTH Candidate "
                  "B AND EulerPC have already run and their own mandatory checks show they "
                  "failed. NOT a production job, not wired into any plan Item, not submitted "
                  "by this script.",
        "rung": rung,
        "rung_note": rung_note,
        "smoke": smoke,
        "why_this_tier_is_a_genuine_control_not_just_a_third_option": (
            "DVV is a velocity-Verlet propagator with an adaptive time step -- structurally "
            "unrelated to the Bulirsch-Stoer/DWI corrector both HPC (Candidate B) and EulerPC "
            "ride on and that failed at Candidate A's Point 7 (§39.126). If StepSize and "
            "EulerPC both fail with the same Bulirsch-Stoer warning signature, a clean DVV "
            "pass would implicate the corrector specifically; comparable difficulty under "
            "genuinely different machinery would point at the PES region itself instead."),
        "question": (
            "rung %d, smoke (maxpoints=%d): route-syntax validation AND an early real "
            "per-point-cost read AND direct evidence of whether stepsize=2 is honored at all "
            "under DVV's adaptive control -- cannot reach arc 2.0-2.3, says nothing about the "
            "DVV hypothesis itself" % (rung, maxpoints)
            if smoke else
            "rung %d, full (maxpoints=%d): does the corrector-independent DVV propagator let "
            "the reverse IRC walk cleanly past arc 2.0-2.3, the region Candidate A's forced "
            "corrector step-contraction broke down in (§39.126)? Unlike StepSize/EulerPC, DVV "
            "shares NO machinery with the failure mechanism -- this is the tier that can "
            "distinguish a corrector-side problem from a PES-region-side one." % (rung, maxpoints)
        ),
        "mandatory_post_run_checks": [
            "POSITIVE echo: the log's GENERAL PARAMETERS block must NOT read "
            "'Integration scheme           = HPC' (every prior log in this project reads HPC "
            "-- confirmed, irc_reverse.log:166); the exact DVV string is [NEEDS VERIFICATION], "
            "read it directly from this run's own log.",
            "NEGATIVE, the sharper test: grep -a 'Bulirsch-Stoer' anywhere in the log, expect "
            "ZERO occurrences -- its presence means DVV did not actually run as a distinct "
            "algorithm regardless of what the Integration scheme line claims.",
            "stepsize=2 is on record but NOT trusted to mean the same thing as HPC/EulerPC's "
            "StepSize -- read the REALIZED arc-per-point rate directly from the log, do not "
            "assume the requested value was honored.",
            "read the log at the point(s) landing near arc 2.0-2.3 SPECIFICALLY, PLUS whether "
            "any corrector-style warning appears there at all -- its absence or presence under "
            "genuinely different machinery is informative either way.",
            "NO Recorrection delta-x convergence threshold: grep for this tier -- the keyword "
            "is omitted on purpose (proposer13 §39.130(2)), this check does not apply here; "
            "its absence from this list is deliberate, not a dropped check.",
        ],
        "source_ts_geometry": os.path.abspath(ts_xyz),
        "not_a_restart": "from-scratch IRC via calcfc-or-not (rung-dependent) from the "
                        "certified TS geometry -- no checkpoint involved",
        "recorrect_never": IRC_RECORRECT_NEVER,
        "recorrect_omitted_reason": (
            "proposer13 §39.130(2): ReCorrect's documented default is already Never for "
            "'other integrators' (DVV is neither HPC nor EulerPC); DVV is a Verlet-type "
            "propagator with no predictor-corrector cycle, so there is no corrector for "
            "ReCorrect to control. Writing recorrect=never risks a harmless no-op at best, a "
            "route-syntax rejection at worst."),
        "stepsize": IRC_STEPSIZE,
        "stepsize_f": IRC_STEPSIZE / 10.0,
        "stepsize_honored_status": (
            "[NEEDS VERIFICATION] whether the StepSize keyword even applies to DVV, and if so "
            "whether it sets an initial/target scale the adaptive scheme then overrides -- read "
            "the realized arc-per-point rate from the log, do not assume."),
        "maxpoints": maxpoints,
        "deck_file": os.path.basename(gjf_path),
        "checkpoint_file": chk_name,
        "route": route,
        "level": level_key, "level_label": lvl.get("label"),
        "charge": CHARGE, "multiplicity": MULT,
        "route_syntax_status": (
            "[NEEDS VERIFICATION] `irc=(...DVV...)` combined this way has never been "
            "route-smoked anywhere in this project. Gaussian's own documentation for DVV is "
            "thin (proposer13 §39.130: three of six checked details not covered by the "
            "primary source at all) -- a malformed rung fails at ~zero cost, same as any other "
            "route-smoke failure this project treats as informative, not silent. If THIS rung's "
            "smoke errors specifically on its own keyword combination, move to the next rung "
            "(see manifest's rung_note) rather than hand-editing this deck."),
        "estimated_cost": (
            (
                "route-syntax smoke, %d points -- 1.0-32.7 core-h [ESTIMATE] (engineer14 "
                "§R39.86, 03_COMPUTE_PLAN.md:19986-19995) -- validates syntax, buys an early "
                "real per-point-cost read, AND is the only cheap way to learn whether "
                "stepsize=2 is honored at all under DVV's adaptive control before committing "
                "the full maxpoints=100 budget"
                % maxpoints
            ) if smoke else (
                "from-scratch IRC redo, CEILING-ONLY pricing (no targeted/expected figure -- "
                "deliberately not produced, engineer14 §R39.86: DVV's per-point cost AND "
                "point-count-per-arc are BOTH unmeasured, unlike Candidate B/EulerPC where at "
                "least one axis was anchored to a shared corrector). Requested ceiling "
                "100.0-1090.0 core-h (100 points x 1.0-10.9 core-h/pt, the widest bracket "
                "priced on this work item -- the width is the honest signal, not a defect) "
                "(engineer14 §R39.86, 03_COMPUTE_PLAN.md:19973-19985)."
            )),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    tool_tag = "build_u56_ra_irc_dvv_probe"
    print("[%s] wrote %s (rung %d, %s)" % (tool_tag, gjf_path, rung,
                                           "smoke" if smoke else "full"))
    print("[%s] route: %s" % (tool_tag, route))
    print("[%s] geometry from: %s (%d atoms)" % (tool_tag, ts_xyz, len(atoms)))
    print("[%s] manifest: %s" % (tool_tag, manifest_path))
    print("[%s] NOT SUBMITTED, and route syntax NOT independently verified against a live G16 "
          "-- see manifest's route_syntax_status. THIRD-TIER BACKUP: only submit if BOTH "
          "Candidate B AND EulerPC have already failed their checks. MANDATORY: read "
          "manifest's mandatory_post_run_checks before trusting any result." % tool_tag)
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
    # reverse-arm work item multiple times] default is 64, NOT 1. Still explicitly overridable.
    ap.add_argument("--total-cores", type=int, default=64)
    ap.add_argument("--rung", type=int, default=1, choices=[1, 2, 3],
                    help="fallback ladder rung (proposer13 §39.130) -- 1 (preferred, keeps "
                         "calcfc), 2 (calcfc dropped, only if rung 1's SMOKE errors), 3 "
                         "(calcfc dropped + GradientOnly added, only if rung 2's SMOKE ALSO "
                         "errors -- scientifically undesirable, a second look first)")
    ap.add_argument("--smoke", action="store_true",
                    help="build the %d-point route-syntax/adaptive-stepping smoke instead of "
                         "the full maxpoints=%d deck for the chosen rung -- proposer13/"
                         "engineer14 both endorse running this first"
                         % (IRC_MAXPOINTS_SMOKE, IRC_MAXPOINTS_FULL))
    args = ap.parse_args(argv)
    return build(args.job_dir, args.out_dir, args.level, args.total_cores, args.rung, args.smoke)


if __name__ == "__main__":
    sys.exit(main())
