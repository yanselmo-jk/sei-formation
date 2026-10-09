#!/usr/bin/env python3
"""One-off diagnostic: restart U56_RA_scan's crashed forward IRC from its OWN checkpoint with
`Recorrect=Never` (or a different `StepSize`), to test critic14's integrator-tolerance
hypothesis (02_METHOD_SPEC.md 39.113(e)/39.114(2)) -- CHEAPLY, by reusing the existing
`irc_forward.chk` rather than any new DFT work beyond the restart itself.

WHY: the real corrector-integration death (`Delta-x Convergence NOT Met` / `Maximum number of
corrector steps exceded`) names an IRC-integrator failure, not an SCF-convergence failure (zero
`Convergence failure` lines, zero basis linear-dependence rejections in the real log). This is
currently the BETTER-SUPPORTED hypothesis for why the path died, and it is directly, cheaply
testable: restart from the last successfully-computed point (already in the checkpoint) with the
failing recorrection step turned off. It does NOT substitute for the `stable=opt` tests
(build_u56_ra_stability_probe.py) -- they answer different, non-substitutable questions; run both
(39.114(2)).

🔴 [NEEDS VERIFICATION] `IRC(Restart)` + `Geom=Check Guess=Read` to continue an IRC job from its
own checkpoint is standard, long-documented Gaussian syntax -- but this project has no G16
install to smoke-test THIS specific route combination against (the usual route-smoke-before-
production discipline this codebase otherwise always applies). 🔴 [critic14] Do NOT read this as
"less verified than `stability_test`'s route" -- `sei_qc_smoke` (qc_adapter.sh) only ever builds
`sp` and `freq`/`freq_smoke_legacy_generic` job_types; `stability_test` (`stable=opt`) has never
been route-smoked EITHER, only its functional/basis/solvent FRAGMENT was (via the sp/freq
smokes, which is a real but partial guarantee -- it says nothing about the `stable=opt` keyword
itself). Both diagnostic decks in this batch are in the SAME state: a new keyword, unsmoked, and
a malformed route fails at ~zero cost either way, same as any other route-smoke failure this
project already treats as informative, not silent -- read BOTH results with this caveat, not
just this one.

This is diagnostic-only: NOT wired into any plan Item, does not submit anything. The source .chk
is copied, never mutated -- but re-running into the SAME `--out-dir` is NOT idempotent: if the
destination checkpoint, deck (`irc_recorrect_probe.gjf`), or manifest already exist, `build()`
refuses to overwrite any of them (a prior restart may have progressed the checkpoint past the
freshly-copied starting point, or a prior build with a DIFFERENT `--direction` may have written
that deck/manifest -- `irc_recorrect_probe.gjf`'s name is not direction-specific) rather than
silently clobbering. This check runs before any fallible step (level/solvent/basis lookup), and
the checkpoint copy itself is deferred until every such step has succeeded, so a run that fails
validation leaves no state behind for a corrected retry to trip over. Remove the existing
destination or pick a new `--out-dir` for a deliberate clean restart.

Usage:
    python3 tools/build_u56_ra_irc_recorrect_probe.py \\
        --job-dir /path/to/U56_RA_scan --out-dir /path/to/output_dir
    python3 tools/build_u56_ra_irc_recorrect_probe.py \\
        --job-dir /path/to/U56_RA_scan --out-dir /path/to/output_dir --step-size 5
"""

import argparse
import json
import os
import shutil
import sys

PKG_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PKG_ROOT)

from sei_pilot import basisset, config, version  # noqa: E402
from sei_pilot import solvent as solvent_mod  # noqa: E402

CHARGE = 0
MULT = 2

#: 🟢 [§39.124 addendum, proposer12 ruling, engineer13 concurred] `maxpoints=30`, matching the
#: ORIGINAL forward AND reverse routes' own cap (both `irc_forward.gjf`/`irc_reverse.gjf` used
#: 30) -- NOT a target, a ceiling the restart still stops short of on its own conditions.
#: proposer12's own reasoning: (1) a genuine G16-declared PES minimum on this restart is
#: categorically stronger evidence than clearing an interim floor and falling back to B+; (2)
#: the pre-crash arc/frame rate was measured under the ORIGINAL corrector settings -- nothing
#: guarantees `recorrect=never` preserves it, and under-sizing costs a full ~3.5-day round trip.
#: engineer13 independently agreed and withdrew a tighter (15) sizing -- NOT a coder choice,
#: NOT tunable per invocation (unlike `--step-size`, which IS a live experimental variable).
IRC_RESTART_MAXPOINTS = 30

#: 🔴 [critic16, 27th review batch] Points ALREADY computed and stored before each direction's
#: original crash -- for the `estimated_cost` string only (how many MORE points this restart can
#: buy before hitting `IRC_RESTART_MAXPOINTS`). Direction-specific: using forward's count for a
#: reverse build silently mis-estimated the remaining budget by more than 3x (30-20=10 vs the
#: true 30-6=24). SOURCE: `02_METHOD_SPEC.md` §39.124 -- forward `n=20` (parse_irc_path_frames
#: convention, saddle excluded, §39.124 finding, re-derived directly from `irc_forward.log`);
#: reverse reached 6 points (idx 0-5, saddle included) before dying, §39.124(1)'s own arc table.
IRC_ALREADY_COMPUTED_POINTS = {"forward": 20, "reverse": 6}


def _estimated_cost_text(direction):
    """🔴 [critic16, 27th review batch] DIRECTION-AWARE -- an earlier version of this string
    used forward's own point count (20) regardless of which direction was actually being built,
    understating a reverse restart's remaining budget by more than 3x (30-20=10 vs the true
    30-6=24). `argparse`'s own `choices=["forward", "reverse"]` means the "unknown direction"
    branch below should be unreachable in practice; it stays honest rather than guessing if it
    is ever reached some other way (a direct `build()` call, not through `main()`)."""
    already = IRC_ALREADY_COMPUTED_POINTS.get(direction)
    if already is None:
        return ("restart of an existing IRC from checkpoint -- remaining-point budget unknown "
                "for direction %r (not in IRC_ALREADY_COMPUTED_POINTS)" % (direction,))
    return ("restart of an existing IRC from checkpoint, ~%d remaining points at most "
           "(maxpoints=%d minus %d already computed and stored) -- a small fraction of the "
           "~660 core-h a fresh scan+IRC for this reaction costs"
           % (IRC_RESTART_MAXPOINTS - already, IRC_RESTART_MAXPOINTS, already))


def build(job_dir, out_dir, direction="forward", recorrect_never=True, step_size=None,
         level="3", total_cores=64):
    os.makedirs(out_dir, exist_ok=True)

    src_chk = os.path.join(job_dir, "irc_%s.chk" % direction)
    ts_xyz = os.path.join(job_dir, "ts.xyz")
    if not os.path.exists(src_chk):
        sys.stderr.write("no checkpoint at %s -- nothing to restart from\n" % src_chk)
        return 2
    if not os.path.exists(ts_xyz):
        sys.stderr.write("no %s -- need it for the gen basis element-coverage check "
                         "(molecule identity, not geometry -- geom=check reads the actual "
                         "geometry from the checkpoint)\n" % ts_xyz)
        return 2

    # 🔴 [critic17, 28th review batch] Checked (and refused) BEFORE any of the fallible steps
    # below (level lookup, solvent resolution, basis coverage) -- a run that fails validation
    # must leave no state behind, or the corrected retry gets refused with a FALSE "a prior
    # restart may have progressed it" message about output nothing ever ran against. `gjf_path`/
    # `manifest.json` are direction-INDEPENDENT names (unlike `chk_name`): building "reverse"
    # into an out-dir that already holds "forward"'s deck/manifest would otherwise silently
    # replace them while `chk_name` still names forward's now-orphaned checkpoint -- exactly the
    # mismatch `submit_stage4.pbs` (fixed `irc_recorrect_probe.gjf` filename) would run without
    # any warning. Checking all three here, together, closes both gaps with one guard.
    chk_name = "irc_%s_recorrect_probe.chk" % direction
    dst_chk = os.path.join(out_dir, chk_name)
    gjf_path = os.path.join(out_dir, "irc_recorrect_probe.gjf")
    manifest_path = os.path.join(out_dir, "manifest.json")
    for existing in (dst_chk, gjf_path, manifest_path):
        if os.path.exists(existing):
            sys.stderr.write(
                "refusing to overwrite existing %s -- a prior build (possibly a different "
                "--direction) may have progressed or relied on it; remove it or pick a new "
                "--out-dir if you really want a clean restart\n" % existing)
            return 5

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

    # 🔴 [§39.124 addendum] `maxpoints` was NEVER written into this route before -- an unbounded
    # (G16-default) restart is neither the ruled ceiling nor anything anyone sized. Always
    # included, not conditional: this is a ruled constant, not an experimental knob (unlike
    # `recorrect_never`/`step_size` above). 🔴 [critic16] Deliberately NOT adding a `direction`
    # keyword here (e.g. `irc_opts.append(direction)`) -- `restart` combined with an explicit
    # direction keyword is UNSMOKED and may, on some G16 builds, mean "restart the OTHER
    # direction" instead of continuing this one. Bare `restart` on a single-direction checkpoint
    # resumes correctly; do not "improve" this.
    irc_opts = ["restart"]
    if recorrect_never:
        irc_opts.append("recorrect=never")
    if step_size is not None:
        irc_opts.append("stepsize=%d" % step_size)
    irc_opts.append("maxpoints=%d" % IRC_RESTART_MAXPOINTS)
    route = ("#p nosymm %s/%s %s geom=check guess=read irc=(%s) Int(Grid=UltraFine)"
            % (lvl.get("functional", "?"), lvl.get("basis", "?"), solvent_fragment,
               ",".join(irc_opts)))

    with open(ts_xyz, errors="replace") as fh:
        ts_text = fh.read()
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

    # Copy only now that every fallible step above has succeeded -- a run that dies on a bad
    # level/solvent/basis leaves NO dst_chk behind, so a corrected retry never trips the guard
    # above over a copy that itself was never at risk of being progressed.
    shutil.copyfile(src_chk, dst_chk)   # never mutate the source, and never clobber a dest

    with open(gjf_path, "w") as fh:
        fh.write("%%nprocshared=%d\n" % total_cores)
        fh.write("%mem=4GB\n")
        fh.write("%%chk=%s\n" % chk_name)
        fh.write(route + "\n\n")
        fh.write("sei_pilot irc_%s_recorrect_probe %s\n\n" % (direction, level_key))
        fh.write("%d %d\n\n" % (CHARGE, MULT))   # geom=check: NO coordinate block
        if basis_block:
            fh.write(basis_block + "\n")
        if solvent_lines:
            fh.write("\n".join(solvent_lines) + "\n\n")

    manifest = {
        "purpose": "diagnostic (Track A item 2, 02_METHOD_SPEC.md 39.113(e)/39.114(2)) -- NOT a "
                  "production job, not wired into any plan Item, not submitted by this script",
        "question": "does turning off the failing corrector recorrection step (or changing the "
                   "step size) let the IRC walk past the geometry where it died -- the "
                   "integrator-tolerance hypothesis, competing with build_u56_ra_stability_"
                   "probe.py's wavefunction-instability hypothesis. NEITHER substitutes for the "
                   "other (39.114(2)): a successful restart shows the crash is numerically "
                   "avoidable but does not by itself rule out a real electronic-structure quirk "
                   "worth knowing about for other jobs in this class.",
        "source_checkpoint": os.path.abspath(src_chk),
        "source_ts_geometry_for_element_coverage_only": os.path.abspath(ts_xyz),
        "direction": direction,
        "recorrect_never": recorrect_never,
        "step_size": step_size,
        "deck_file": os.path.basename(gjf_path),
        "checkpoint_file": chk_name,
        "route": route,
        "level": level_key, "level_label": lvl.get("label"),
        "charge": CHARGE, "multiplicity": MULT,
        "route_syntax_status": (
            "[NEEDS VERIFICATION] `irc=(restart,...)` + `geom=check guess=read` is standard "
            "documented Gaussian IRC-restart syntax, but this project has no G16 install to "
            "smoke-test THIS combination against (unlike stability_test's route, which reuses "
            "the exact functional/basis/solvent fragment every real production job this round "
            "already exercised). A malformed route fails at ~zero cost, same as any other route-"
            "smoke failure this project treats as informative, not silent -- read the result "
            "with this caveat."),
        "estimated_cost": _estimated_cost_text(direction),
        "provenance": version.provenance(root=PKG_ROOT, invocation=" ".join(sys.argv)),
    }
    with open(manifest_path, "w") as fh:
        json.dump(manifest, fh, ensure_ascii=False, indent=1)

    print("[build_u56_ra_irc_recorrect_probe] wrote %s" % gjf_path)
    print("[build_u56_ra_irc_recorrect_probe] route: %s" % route)
    print("[build_u56_ra_irc_recorrect_probe] checkpoint copied from %s -> %s"
          % (src_chk, dst_chk))
    print("[build_u56_ra_irc_recorrect_probe] manifest: %s" % manifest_path)
    print("[build_u56_ra_irc_recorrect_probe] NOT SUBMITTED, and route syntax NOT independently "
          "verified against a live G16 -- see manifest.json's route_syntax_status before relying "
          "on this beyond a cheap try.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--job-dir", required=True,
                    help="U56_RA_scan's job dir (needs irc_<direction>.chk and ts.xyz)")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--direction", default="forward", choices=["forward", "reverse"])
    ap.add_argument("--no-recorrect-never", dest="recorrect_never", action="store_false",
                    help="omit Recorrect=Never (use with --step-size to test that alone)")
    ap.add_argument("--step-size", type=int, default=None,
                    help="G16 IRC StepSize (0.01 Bohr units) -- omit to use G16's default; "
                         "proposer10's second candidate variable (39.114(2))")
    ap.add_argument("--level", default="3")
    # 🔴 [critic16, 27th review batch] Default was 1 -- silently wrote `%nprocshared=1` into
    # every deck nobody explicitly overrode. At `maxpoints=IRC_RESTART_MAXPOINTS` (30) that is
    # 46-87 h wall against ADR-114's 48 h cap (single-threaded on an 11-atom TS-chain-level job).
    # 64 matches this project's standard per-task core count for this job class (U56.sh/
    # endpoint_prep.sh's own default, `${SEI_TOTAL_CORES:-1}` set by the plan/scheduler, not a
    # bare script default of 1).
    ap.add_argument("--total-cores", type=int, default=64)
    args = ap.parse_args(argv)
    return build(args.job_dir, args.out_dir, args.direction, args.recorrect_never,
                args.step_size, args.level, args.total_cores)


if __name__ == "__main__":
    sys.exit(main())
