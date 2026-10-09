"""C-5 — the production solvent DECISION, and the fallback that must be impossible.

🔴 [ADR-104/105/106 — read before treating SMD below as *the* production model] SMD is the
B0-era model this module was written around and its reasoning is kept (B0 ran on it). The
USER ruling ADR-104 moves production to **PCM at a NUMERIC ε = 18.5 from B1 onward** — never
a solvent NAME. ADR-106 ([USER-DOMAIN]) closed the ε sensitivity question (SENSITIVE) and
DROPPED the scan. `resolve_solvent_line()` below is the ONE decision point every deck must
pass through (ADR-105: a per-payload precheck copied around is what produced one-of-many).

🔴 THIS IS NOT A HYPOTHETICAL FAILURE. RT-1's P1 ran, on the cluster, with the route line

    #p wB97XD/gen scrf=(smd,solvent=acetonitrile) opt=(qst2,calcfc,noeigen...

**Acetonitrile has eps = 35.7 against EC:EMC 3:7's eps ~ 18-20 -- roughly a factor of two on the
reaction field, for a charge-localising ring-opening of an ion pair.** It was presumably a pilot
placeholder and it survived into a 302 core-h production-shaped run. C-5 exists to stop that
recurring, and the only reliable way to stop a fallback is to make it unreachable.

```
    ⟹ THE BUILDER REFUSES TO EMIT A DECK when the descriptors are absent.
      It does NOT fall back to a named solvent. It does NOT pick a nearby one. It raises.
```

🔴 THE DESCRIPTOR TABLE IS EMPTY, AND EMPTY IS NOT ABSENT.
   `DESCRIPTORS` exists and is explicitly `{}` with a status field, so that nobody later reads a
   MISSING table as "no descriptors were needed". Two of the seven ARE known -- they are
   structurally determined rather than measured -- and they are recorded as known, so the gap is
   exactly five values and not seven.

🔒 ORDERING (Q2 ruling) — **SUPERSEDED by ADR-106**: the eps sensitivity scan is DROPPED.
   The user holds, from experience ([USER-DOMAIN]), that the ε sensitivity IS sensitive and
   that 18.5 is the conventional EC/EMC 3:7 value. Re-deriving that by compute is expenditure,
   not verification. (The original ruling text is kept in git history; do not re-open the scan.)

⚠ THREE TRAPS carried for whoever fills the table in. None is acted on here.
   1. G16/SMD wants the surface tension in **cal mol^-1 A^-2, NOT dyn/cm**. A value taken from a
      properties table and entered directly is wrong by a constant factor AND WILL NOT CRASH.
      🔴 The conversion factor itself is `[UNVERIFIED]` and is deliberately NOT written here.
   2. **EC melts at ~36 C -- it is a SOLID at 298 K.** Its "pure liquid" descriptors are measured
      or extrapolated at ~40 C, so volume-weighting them against EMC's 25 C values is an internal
      inconsistency, not a rounding detail.
   3. Volume-fraction weighting of SMD descriptors is **UNVALIDATED**: SMD was parameterised on
      pure solvents and Abraham alpha/beta are not obviously linear in composition.
"""

#: The seven SMD descriptors `scrf=(smd,solvent=generic)` requires (02_METHOD_SPEC §26.5).
DESCRIPTOR_NAMES = (
    "Eps", "EpsInf", "HBondAcidity", "HBondBasicity",
    "SurfaceTensionAtInterface", "CarbonAromaticity", "ElectronegativeHalogenicity",
)

#: 🟢 STRUCTURALLY DETERMINED, not measured -- derivable from the molecular formula alone, and
#: confirmed by proposer5. Neither EC nor EMC has an aromatic carbon or an electronegative
#: halogen, so both are exactly zero for either pure component AND for any mixture of them.
STRUCTURAL_DESCRIPTORS = {
    "CarbonAromaticity": 0.0,
    "ElectronegativeHalogenicity": 0.0,
}

#: 🔴 EMPTY, AND EMPTY IS NOT ABSENT. The five remaining values are literature quantities for EC
#: and EMC and are NOT written from memory. proposer5 identified the canonical source (Winget,
#: Dolney, Giesen, Cramer & Truhlar, *Minnesota Solvent Descriptor Database*) and verified the
#: citation by reading the author line out of the file -- but the PDF uses subsetted fonts with
#: custom encoding and the tables did not extract. **Whether EC and EMC are even in it is
#: `[UNVERIFIED]`.** The attempt and its failure are recorded rather than a plausible number.
DESCRIPTORS = {}

DESCRIPTOR_STATUS = (
    "[EMPTY, NOT ABSENT] 2 of 7 descriptors are structurally determined and known "
    "(CarbonAromaticity = 0, ElectronegativeHalogenicity = 0). The other 5 are literature values "
    "for EC and EMC that we do not hold: the canonical source was identified and its citation "
    "verified, but the PDF's subsetted fonts defeated table extraction and whether EC/EMC are in "
    "it is [UNVERIFIED]. 🔴 No deck is emitted without them -- see SolventDescriptorsMissing.")

#: What P1 actually did. Kept as a named constant so the test that forbids it cannot drift.
FORBIDDEN_FALLBACK = "acetonitrile"
FORBIDDEN_FALLBACK_EPS = 35.7
TARGET_EPS_RANGE = (18.0, 20.0)


class SolventDescriptorsMissing(RuntimeError):
    """Raised instead of emitting a deck. 🔴 A refusal, not a warning."""


def missing_descriptors(descriptors=None):
    """Which of the seven are still absent. Structural ones count as present."""
    have = dict(STRUCTURAL_DESCRIPTORS)
    have.update(descriptors if descriptors is not None else DESCRIPTORS)
    return [n for n in DESCRIPTOR_NAMES if n not in have]


def status(descriptors=None):
    """A reportable record of where the descriptors stand. Never raises."""
    missing = missing_descriptors(descriptors)
    return {
        "descriptor_names": list(DESCRIPTOR_NAMES),
        "known_structurally": dict(STRUCTURAL_DESCRIPTORS),
        "n_known": len(DESCRIPTOR_NAMES) - len(missing),
        "n_missing": len(missing),
        "missing": missing,
        "table_is_empty_not_absent": True,
        "status": DESCRIPTOR_STATUS,
        "can_emit_deck": not missing,
        # 🔴 ADR-106 voided the old text ("pending the eps sensitivity scan") — the scan is
        #    DROPPED and the descriptors are moot by ADR-104 (PCM needs ONE number). The refusal
        #    must not cite a blocker that no longer exists.
        "blocked_on": ("the production solvent decision (ADR-104: PCM at numeric eps=18.5 from "
                       "B1; the SMD descriptor path is moot) -- wire it through "
                       "resolve_solvent_line(), never a named solvent" if missing else None),
        "traps_for_whoever_fills_it": [
            "🔴 surface tension in cal mol^-1 A^-2, NOT dyn/cm -- wrong by a constant factor and "
            "WILL NOT CRASH. The factor itself is [UNVERIFIED] and is not written down here.",
            "🔴 EC is a SOLID at 298 K (mp ~36 C); its 'pure liquid' descriptors are ~40 C values, "
            "so weighting them against EMC's 25 C values is an internal inconsistency.",
            "🔴 volume-fraction weighting of SMD descriptors is UNVALIDATED -- SMD was "
            "parameterised on pure solvents and Abraham alpha/beta are not obviously linear in "
            "composition.",
        ],
    }


def solvent_line(descriptors=None):
    """The `scrf=` fragment for the production route. RAISES if the descriptors are absent.

    🔴 It does not fall back to a named solvent, it does not pick a nearby one, and it does not
       return an empty string that a caller might splice in. RT-1's P1 ran in acetonitrile
       (eps 35.7) against EC:EMC's eps ~ 18-20 -- roughly a factor of two on the reaction field --
       and that is what a fallback looks like in practice.
    """
    missing = missing_descriptors(descriptors)
    if missing:
        raise SolventDescriptorsMissing(
            "C-5: refusing to emit a solvent line. %d of %d SMD descriptors are absent (%s). "
            "🔴 THE FALLBACK IS NOT AVAILABLE: RT-1's P1 ran `solvent=%s` (eps %.1f) against "
            "EC:EMC 3:7's eps ~ %.0f-%.0f, and this refusal exists so that cannot recur. %s"
            % (len(missing), len(DESCRIPTOR_NAMES), ", ".join(missing),
               FORBIDDEN_FALLBACK, FORBIDDEN_FALLBACK_EPS,
               TARGET_EPS_RANGE[0], TARGET_EPS_RANGE[1], DESCRIPTOR_STATUS))
    have = dict(STRUCTURAL_DESCRIPTORS)
    have.update(descriptors if descriptors is not None else DESCRIPTORS)
    # [critic9 §5] 값은 숫자만 — 문자열이 %s 로 그대로 스플라이스되면 route 가 깨지거나
    # 임의 토큰이 실린다. 숫자가 아니면 조용히 넘기지 않고 거부한다.
    for n in DESCRIPTOR_NAMES:
        try:
            float(have[n])
        except (TypeError, ValueError):
            raise SolventDescriptorsMissing(
                "C-5: SMD descriptor %s 가 숫자가 아니다 (%r) — 기술자 테이블 값은 "
                "숫자만 받는다." % (n, have[n]))
    fields = " ".join("%s=%s" % (n, float(have[n])) for n in DESCRIPTOR_NAMES)
    return "scrf=(smd,solvent=generic,read) %s" % fields


def load_policy():
    """solvent_policy 의 단일 로더 — qc_adapter 와 endpoint_prep precheck 가 공유한다.

    우선순위: `SEI_SOLVENT_POLICY_JSON`(env, 테스트/명시적 주입 — bash 경계 너머의
    sei_qc_input 을 monkeypatch 할 수 없어서 존재한다) > config/qc_levels.json 의
    `gaussian16.solvent_policy`. ⚠ 어느 쪽이든 resolve_solvent_line() 을 통과해야만
    덱에 닿는다 — 이름 있는 용매로 가는 경로는 이 채널로도 존재하지 않는다.
    """
    import json as _json
    import os as _os
    raw = _os.environ.get("SEI_SOLVENT_POLICY_JSON")
    if raw:
        return _json.loads(raw)
    from . import config as _config
    return ((_config.load("qc_levels.json", {}).get("gaussian16") or {})
            .get("solvent_policy"))


class SolventUndecided(RuntimeError):
    """C-5 refusal: no production solvent MODEL has been wired for this deck.

    🔴 Distinct from SolventDescriptorsMissing on purpose — "the SMD table is empty" and
    "no model decision reached this deck at all" are different facts and must not share a
    message (C-2's principle: a refusal and a wrong answer must not share an exit; neither
    may two different refusals share a diagnosis).
    """


#: [P-0 / ADR-108] 후보 덱의 라벨. 코드와 출력(meta.json / smoke_levels.json / smoke
#: stdout) 양쪽에 이 문자열 그대로 실린다 — 클러스터 route smoke 가 실증하기 전까지
#: 이 덱 형식은 메모리에서 쓴 후보다.
UNVERIFIED_DECK_LABEL = "[UNVERIFIED — cluster route smoke required]"


#: [S-1/S-2] 이 실행의 route smoke 가 G16 출력에서 ε 적용을 확인했을 때의 라벨.
#: config 의 deck_verified(사람이 올리는 값, 기본 false — lead 만 올린다)와 구분된다.
VERIFIED_IN_RUN_LABEL = ("[VERIFIED-IN-RUN — this job's route smoke confirmed eps "
                         "in the G16 output]")


def runtime_verification_ok(runtime_verification, eps_requested):
    """[S-1] smoke 가 남긴 실행-내 검증 기록이 이 ε 를 실증하는가.

    조건: eps_matched 참 AND 기록의 eps_requested 가 지금 요청 ε 와 같다.
    (다른 ε 로 통과한 기록으로 이 덱을 열 수 없다 — 기록은 값에 귀속된다.)
    """
    rv = runtime_verification or {}
    try:
        return bool(rv.get("eps_matched")) and \
            float(rv.get("eps_requested")) == float(eps_requested)
    except (TypeError, ValueError):
        return False


# =============================================================================================
# 🔴 EpsInf — the sentinel that segfaulted the frequency stage (§39.73)
# =============================================================================================
#
# WHAT HAPPENED: the PCM read block supplied `eps=18.5` and nothing else. G16's **freq** stage
# -- and only freq; rough and tight optimisation never touch this path -- reads the absent
# `EpsInf` as `EpsInf=0.0000` and dies in L1110. Every frequency job this round hit it: the
# endpoint certification AND all 20 of P5's. **Zero frequencies exist anywhere in the round.**
#
# 🔒 WHY NOTHING CAUGHT IT: route smoke never computes a Hessian, so the first job to exercise
# a Hessian under `solvent=generic` was a production job. ADR-108's move to PCM-numeric escaped
# the seven-descriptor SMD problem for energies and gradients and **deferred it to the Hessian
# stage** -- which is exactly the stage C-8 depends on. A gate that runs on a cheaper path than
# the thing it certifies cannot see this class of failure.
#
# 🟢 THE FIX IS A BRACKET, NOT A LOOKUP (§39.73, same move as the eps 18.5-vs-35.7 bracket):
# run the freq stage at BOTH physically admissible extremes and see whether the answer moves.
#     EPSINF_NO_FAST_RESPONSE = 1.0   n^2 = 1: no electronic (fast) response at all
#     EPSINF_FULL_RESPONSE    = eps   fast response equals the full static response
# Those are the ENDS of the admissible range, so no value needs sourcing. If `n_imag` and the
# low-frequency spectrum are INVARIANT across them, EpsInf is irrelevant to C-8 and the blocker
# dissolves permanently with nothing measured. If they are NOT invariant, that is a real finding
# and a real n^2 has to be sourced.
# ⚠ proposer7's prediction, and the reason this is expected to be plumbing rather than physics:
# G16's own log reports `IEInf=0`, i.e. EQUILIBRIUM solvation should not consult EpsInf at all.
EPSINF_NO_FAST_RESPONSE = 1.0
#: 🔒 [USER RULING 2026-08-21] The PCM carrier solvent for `pcm_numeric` decks. A named G16
#: solvent so every non-ε parameter is real and consistent; ε itself is overridden in the
#: read block (`eps=18.5`). This is NOT the forbidden acetonitrile fallback (ADR-066/067):
#: the dielectric still comes from policy, numerically, never from the name.
PCM_CARRIER_SOLVENT = "acetone"
#: [§39.82, proposer8] The PHYSICAL working value for EC:EMC 3:7, EpsInf = n^2 = 1.93
#: [CATALOG-GRADE PROVENANCE] -- catalog refractive indices (range 1.910-1.933 across source
#: combinations), NOT primary literature. Inside the bracket [1.0, eps] by construction.
#: Used for single-value items (P5, P1b); the bracket arms stay at the interval ends.
#: 🔴 Do not let anything downstream read this as "sourced".
EPSINF_PHYSICAL_EC_EMC = 1.93
EPSINF_PHYSICAL_PROVENANCE = "[CATALOG-GRADE PROVENANCE] n^2, EC:EMC 3:7, catalog n in 1.910-1.933"


def production_solvent_signature(policy=None):
    """What a certificate must have been computed under to count as a PRODUCTION certificate:
    {"route_fragment", "extra_input_lines"} of the current policy's deck. Resolved on the
    smoke path so it never raises on an unverified deck -- this is a comparison key, not a
    permission to run. Returns None when no solvent decision exists (C-5 refusal upstream)."""
    try:
        deck = resolve_solvent_deck(policy or load_policy(), None, "smoke")
    except (SolventUndecided, SolventDescriptorsMissing, ValueError):
        return None
    return {"route_fragment": deck["route_fragment"],
            "extra_input_lines": list(deck["extra_input_lines"])}


def _opt_convergence(route):
    """'tight' | 'verytight' | 'loose' | 'default' | 'none' from a route's opt=(...) options."""
    import re as _re
    low = (route or "").lower()
    m = _re.search(r"\bopt(?:=\(?([^)\s]*)\)?)?", low)
    if not m:
        return "none"
    opts = (m.group(1) or "").split(",")
    for k in ("verytight", "tight", "loose"):
        if k in opts:
            return k
    return "default"


def production_method_signature(level_key, policy=None, cfg=None):
    """What a certificate must have been computed under: functional, real basis name,
    integration grid (from the `endpoint_opt_freq` route template) and the solvent deck.
    None when the level or the solvent decision does not exist."""
    import re as _re
    from . import config as _config
    g = (cfg if cfg is not None else _config.load("qc_levels.json", {})).get("gaussian16") or {}
    lvl = g.get(level_key) or {}
    sol = production_solvent_signature(policy)
    if not lvl or sol is None:
        return None
    tmpl = (g.get("job_types") or {}).get("endpoint_opt_freq", "")
    m = _re.search(r"Int\(Grid=([A-Za-z0-9]+)\)", tmpl)
    return {"level": level_key,
            "functional": lvl.get("functional"),
            "basis_real_name": lvl.get("basis_real_name") or lvl.get("basis"),
            "grid": (m.group(1).lower() if m else "default"),
            # [§39.105] C-8 is a claim about CONVERGENCE; the threshold is what "converged"
            # means. opt=(tight) Max-Force 1.5e-5 vs plain opt 4.5e-4 -- 30x looser.
            "opt_convergence": _opt_convergence(tmpl),
            "route_fragment": sol["route_fragment"],
            "extra_input_lines": sol["extra_input_lines"]}


def certificate_matches_production(meta, policy=None, level_key=None, cfg=None):
    """(ok, reason). `meta` = the certifying job's `endpoint_tight.meta.json`.

    🔴 [§39.92/§39.93/§39.101 + lead 2026-08-21] a `converged` certificate is a status; WHAT
    it was computed under is separate evidence. A certificate is a certificate of a MODEL
    (proposer8): functional, basis, integration grid AND solvent deck must all equal the
    production method. A level3 certificate, or one on a different grid, or one under the
    abandoned `solvent=generic` deck, must not pass the C-8 guard.
    Reasons distinguish `not_computed` (no meta at all -> run it) from `method_mismatch`
    (computed under the wrong model -> re-run it): different actions.
    """
    import re as _re
    if not meta:
        return False, "not_computed: no certifying job metadata (endpoint_tight.meta.json)"
    level_key = level_key or meta.get("level")
    sig = production_method_signature(level_key, policy, cfg)
    if sig is None:
        return False, ("method_mismatch: no production method for level=%r / no solvent decision"
                       % (level_key,))
    route = meta.get("route") or ""
    low = route.lower()
    mism = []
    if meta.get("level") != sig["level"]:
        mism.append("level %r != %r" % (meta.get("level"), sig["level"]))
    if (sig["functional"] or "").lower() not in low:
        mism.append("functional %r not in route" % sig["functional"])
    if (meta.get("basis_real_name") or "").lower() != (sig["basis_real_name"] or "").lower():
        mism.append("basis %r != %r" % (meta.get("basis_real_name"), sig["basis_real_name"]))
    gm = _re.search(r"int\(grid=([a-z0-9]+)\)", low)
    grid = gm.group(1) if gm else "default"
    if grid != sig["grid"]:
        mism.append("grid %r != %r" % (grid, sig["grid"]))
    conv = _opt_convergence(route)
    if conv != sig["opt_convergence"]:
        mism.append("opt convergence %r != %r (the threshold is what 'converged' means, §39.105)"
                    % (conv, sig["opt_convergence"]))
    if meta.get("has_ecp"):
        mism.append("has_ecp=True: effective basis differs from %r; no production ECP policy"
                    % sig["basis_real_name"])
    if sig["route_fragment"] not in route:
        mism.append("solvent route %r lacks %r" % (route, sig["route_fragment"]))
    lines = sorted(str(l).strip().lower() for l in (meta.get("solvent_extra_input_lines") or []))
    want = sorted(l.strip().lower() for l in sig["extra_input_lines"])
    if lines != want:
        mism.append("solvent read block %r != %r" % (lines, want))
    if mism:
        return False, "method_mismatch: " + "; ".join(mism)
    return True, ("method_match: level=%s %s/%s grid=%s opt=%s %s %s (charge/spin ride on the "
                  "per-species key, not checked here)"
                  % (sig["level"], sig["functional"], sig["basis_real_name"], sig["grid"],
                     sig["opt_convergence"], sig["route_fragment"], want))


def epsinf_bracket(eps):
    """The two admissible EpsInf endpoints for a given static eps (§39.73).

    Returns `[(label, value), ...]`. 🔴 These are the ENDS of the physically admissible range,
    not estimates: n^2 cannot be below 1 (no response) and equilibrium solvation cannot respond
    faster than fully (n^2 = eps). Nothing here needs a literature value.
    """
    eps_f = float(eps)
    if eps_f < 1.0:
        raise ValueError("eps = %r is below 1.0 and is not a dielectric constant" % (eps,))
    return [("no_fast_response", EPSINF_NO_FAST_RESPONSE),
            ("full_response", eps_f)]


def epsinf_invariance(result_a, result_b, low_freq_cutoff_cm1=200.0):
    """Does the C-8-relevant answer move between the two EpsInf endpoints?

    `result_*` = `{"n_imag": int, "frequencies_cm1": [...]}` from the two freq runs.

    🔴 The verdict is over what C-8 ACTUALLY READS -- `n_imag`, plus the low-frequency spectrum
    where a solvent-response term would show up first. It is NOT a claim that the two runs are
    numerically identical; that would fail on rounding and tell us nothing.
    🔒 If invariant: EpsInf is irrelevant to C-8 and the blocker dissolves with no number
    sourced. If not: a real n^2 must be sourced, and that is a finding rather than a nuisance.
    """
    out = {"invariant": None, "n_imag": [None, None], "reasons": [],
           "low_freq_cutoff_cm1": float(low_freq_cutoff_cm1),
           "constraint": "EpsInf bracket (02_METHOD_SPEC §39.73)"}
    a, b = result_a or {}, result_b or {}
    out["n_imag"] = [a.get("n_imag"), b.get("n_imag")]
    fa, fb = a.get("frequencies_cm1"), b.get("frequencies_cm1")
    if a.get("n_imag") is None or b.get("n_imag") is None or fa is None or fb is None:
        out["reasons"].append(
            "one or both EpsInf runs produced no frequencies -- the bracket cannot be read, "
            "and an unrun comparison is not an invariance result")
        return out
    if a["n_imag"] != b["n_imag"]:
        out["invariant"] = False
        out["reasons"].append(
            "🔴 n_imag differs between the EpsInf endpoints (%s vs %s) -- EpsInf changes the "
            "answer C-8 reads, so a real n^2 has to be sourced (§39.73)"
            % (a["n_imag"], b["n_imag"]))
        return out
    lo_a = sorted(f for f in fa if abs(f) <= float(low_freq_cutoff_cm1))
    lo_b = sorted(f for f in fb if abs(f) <= float(low_freq_cutoff_cm1))
    out["low_frequencies"] = [lo_a, lo_b]
    if len(lo_a) != len(lo_b):
        out["invariant"] = False
        out["reasons"].append(
            "🔴 the low-frequency spectrum has %d vs %d modes below %.0f cm^-1 -- the count "
            "itself moved, which is a larger change than any shift within it"
            % (len(lo_a), len(lo_b), low_freq_cutoff_cm1))
        return out
    out["max_low_freq_shift_cm1"] = (max(abs(x - y) for x, y in zip(lo_a, lo_b))
                                     if lo_a else 0.0)
    out["invariant"] = True
    out["reasons"].append(
        "n_imag agrees (%s) and the low-frequency spectrum matches mode for mode (largest "
        "shift %.2f cm^-1 below %.0f cm^-1) -- EpsInf does not move what C-8 reads, so no n^2 "
        "needs sourcing" % (a["n_imag"], out["max_low_freq_shift_cm1"], low_freq_cutoff_cm1))
    return out


def resolve_solvent_deck(policy=None, variant=None, purpose="production",
                         runtime_verification=None, eps_inf=None):
    """[ADR-105/108] THE single C-5 decision point. `qc_adapter.sh` is its only shell caller.

    `policy` comes from config/qc_levels.json's `gaussian16.solvent_policy`:
        {"model": null | "smd_descriptors" | "pcm_numeric",
         "epsilon": null | <number>, "deck_verified": bool}
    `variant`: None (equilibrium) | "noneq_write" | "noneq_read" — the U-27 NonEq decks.
    `purpose`: "production" | "smoke" — 🔒 미검증(pcm) 후보 덱은 **smoke 경로만** 통과한다.

    반환: {"route_fragment", "extra_input_lines", "label", "model"}
      route_fragment     : route 줄에 스플라이스되는 `scrf=` 조각
      extra_input_lines  : 좌표(및 gen 기저 블록) 뒤 `read` 추가 입력 섹션 줄들
      label              : UNVERIFIED_DECK_LABEL 또는 None

    Behaviour, in the C-5 direction (falls toward REFUSAL, never toward a named solvent):
      model null/absent  → raise SolventUndecided (acetonitrile 재발 방지, ADR-066/067/105).
      "smd_descriptors"  → solvent_line(); DESCRIPTORS 가 비어 있는 동안 여전히 거부.
      "pcm_numeric"      → 🟢 [ADR-108, 사용자 승인] ε=18.5 numeric PCM. 형식은
                           epsilon_scan_line 과 같은 메커니즘(solvent=generic + numeric ε
                           + `read`)이되, ε 는 route 줄이 아니라 **read 추가 입력 섹션**에
                           싣는다 — 그 배선이 이번에 추가된 전부다(두 번째 메커니즘 아님).
                           🔴 후보 덱은 [UNVERIFIED] 라벨을 달고, `deck_verified` 가
                           false 인 동안 **smoke 밖으로는 나가지 않는다**: 승인이 났다고
                           미검증 덱 위로 본계산 core-h 가 나가는 사고를 코드가 막는다.
    🔴 A solvent NAME is never accepted from config or policy.
    """
    policy = policy or {}
    model = policy.get("model")
    if variant and variant.endswith("_pcm"):    # noneq_write_pcm / noneq_read_pcm / eq_pcm
        # U-27 의 IEFPCM 폴백 스모크는 'SMD 가 거부될 때 다른 모델로 재시도'라는
        # 전제 위에 쓰였다. ADR-104/108 이 생산 모델 자체를 PCM 으로 옮겼으므로 이
        # 폴백의 의미가 바뀌었다 — 재사양 전까지 닫힌다 (lead 지시, P-0 §6).
        raise SolventUndecided(
            "C-5: U-27 의 *_pcm 폴백 덱(%r)은 ADR-104/108(생산=PCM ε=18.5) 아래에서 "
            "재사양이 필요하다. 이전 판은 여기서 scrf=(iefpcm,solvent=%s) 를 "
            "하드코딩했다 — 그 경로는 닫혔다." % (variant, FORBIDDEN_FALLBACK))
    if model == "smd_descriptors":
        # policy["descriptors"] 는 SMD 테이블의 미래 채움 채널이다(값은 문헌 출처와 함께
        # config/주입으로 온다). 없으면 모듈의 DESCRIPTORS({}) 로 떨어져 여전히 거부한다.
        base = solvent_line(policy.get("descriptors"))
        deck = {"route_fragment": base, "extra_input_lines": [],
                "label": None, "model": model}
        if variant in ("noneq_write", "noneq_read"):
            deck["route_fragment"] = noneq_variant(base, variant.split("_", 1)[1])
        elif variant:
            raise ValueError("unknown solvent variant: %r" % (variant,))
        return deck
    if model == "pcm_numeric":
        eps = policy.get("epsilon")
        try:
            eps_f = float(eps)
        except (TypeError, ValueError):
            eps_f = -1.0
        if eps is None or eps_f <= 0:
            raise SolventUndecided(
                "C-5: solvent_policy.model=pcm_numeric 인데 epsilon 이 없다/숫자가 "
                "아니다/비양수다 (%r). ε 는 숫자로만 온다(ADR-104) — 이름으로 온 값은 "
                "받지 않는다." % (eps,))
        if variant == "legacy_generic_epsinf":
            # [lead/user 2026-08-21] SMOKE-ONLY comparison deck: the abandoned
            # `solvent=generic` + eps + EpsInf=eps shape (the deck the converged 18.5 arm
            # ran). Exists so one H2 freq under each deck lands in the same returned tree.
            # 🔴 Never a production deck -- refuse outright outside the smoke path.
            if purpose != "smoke":
                raise SolventUndecided(
                    "C-5: legacy_generic_epsinf is a smoke-only comparison deck; production "
                    "is solvent=%s (user ruling 2026-08-21)." % PCM_CARRIER_SOLVENT)
            return {"route_fragment": "scrf=(pcm,solvent=generic,read)",
                    "extra_input_lines": ["eps=%s" % eps_f, "EpsInf=%s" % eps_f],
                    "label": "[SMOKE-ONLY legacy generic deck]", "model": model,
                    "carrier_solvent": "generic", "eps_inf": eps_f,
                    "_eps_inf_status": "smoke-only legacy comparison (EpsInf=eps)"}
        if variant in ("noneq_write", "noneq_read"):
            # U-27 의 NonEq 스모크는 SMD 전제로 쓰였다. PCM 아래의 NonEq 절차는
            # 재사양 사항이다(_pcm 폴백과 같은 이유) — 지어내서 돌리지 않는다.
            raise SolventUndecided(
                "C-5: pcm_numeric 아래의 U-27 NonEq 덱(%r)은 재사양 전까지 닫혀 있다 "
                "(SMD 전제의 절차를 PCM 으로 조용히 옮기지 않는다)." % (variant,))
        if variant:
            raise ValueError("unknown solvent variant: %r" % (variant,))
        config_verified = bool(policy.get("deck_verified"))
        # [S-1/S-2] 검증 경로 둘: (i) config deck_verified — 사람이 올린다(기본 false,
        # 코드가 자동으로 올리지 않는다), (ii) runtime — **이 실행의 smoke 가 G16 출력
        # 에서 ε 적용을 확인**한 기록. (ii) 덕분에 smoke 라운드와 본 라운드가 한 왕복에
        # 들어간다: 덱이 틀리면 smoke 에서 몇 분 만에 exit 4, 맞으면 같은 잡이 계속 간다.
        run_verified = runtime_verification_ok(runtime_verification, eps_f)
        if not (config_verified or run_verified) and purpose != "smoke":
            raise SolventUndecided(
                "C-5: pcm_numeric(eps=%s) 후보 덱은 %s 상태다 — 이 실행의 smoke 가 G16 "
                "출력에서 ε 적용을 확인하지 못했고(deck_verification 없음/불일치), config "
                "solvent_policy.deck_verified 도 false 다(올리는 것은 lead 몫). "
                "본계산 덱을 내지 않는다(smoke 경로만 통과)."
                % (eps_f, UNVERIFIED_DECK_LABEL))
        if config_verified:
            label = None
        elif run_verified:
            label = VERIFIED_IN_RUN_LABEL
        else:
            label = UNVERIFIED_DECK_LABEL      # smoke 자신이 받는 후보 덱
        # 🔒 [USER RULING, 2026-08-21, final] PCM carrier solvent is a NAMED solvent
        #    (`acetone`) with the static ε overridden numerically in the read block. Why not
        #    `solvent=generic`: `Generic` supplies a row of ZEROS for every other parameter
        #    (RSolv, EpsInf, density, ...); the freq stage is the one code path that reads
        #    EpsInf and it died on the 0.0000 sentinel (§39.73/§39.80, a full round lost).
        #    `acetone` supplies a real, internally consistent parameter set; only ε is ours.
        #    🔴 `EpsInf` is NOT emitted and the bracket experiment is CANCELLED (user ruling
        #    overrides §39.90's generic+EpsInf=1.93 recommendation). `eps_inf` is accepted
        #    and IGNORED so older callers cannot resurrect the line by accident.
        return {
            "route_fragment": "scrf=(pcm,solvent=%s,read)" % PCM_CARRIER_SOLVENT,
            "extra_input_lines": ["eps=%s" % eps_f],
            "label": label,
            "model": model,
            "carrier_solvent": PCM_CARRIER_SOLVENT,
            "eps_inf": None,
            "_eps_inf_status": ("not emitted -- solvent=%s supplies its own optical constants "
                                "(user ruling 2026-08-21); a caller passed eps_inf=%r and it "
                                "was ignored" % (PCM_CARRIER_SOLVENT, eps_inf)
                                if eps_inf is not None else
                                "not emitted -- solvent=%s supplies its own optical constants "
                                "(user ruling 2026-08-21)" % PCM_CARRIER_SOLVENT),
        }
    raise SolventUndecided(
        "C-5: 이 덱에 도달한 용매 결정이 없다 (solvent_policy.model=%r). "
        "지난 라운드 P1/P1b/P5 는 config 의 정적 'scrf=(smd,solvent=%s)'(ε %.1f)로 "
        "14,464 core-h 를 돌았다 — EC:EMC 3:7 의 ε ≈ %.0f–%.0f 에 대해. 이 거부는 "
        "그 재발 방지다(ADR-066/067/105). 결정은 config/qc_levels.json 의 "
        "gaussian16.solvent_policy 한 곳에서 한다: ADR-104/108 은 PCM ε=18.5(숫자)다."
        % (model, FORBIDDEN_FALLBACK, FORBIDDEN_FALLBACK_EPS,
           TARGET_EPS_RANGE[0], TARGET_EPS_RANGE[1]))


def resolve_solvent_line(policy=None, variant=None, purpose="production",
                         runtime_verification=None):
    """route 조각만 필요한 호출자용 얇은 래퍼 (endpoint_prep precheck, 기존 테스트).
    거부 동작은 resolve_solvent_deck 과 동일하다 — 결정은 한 곳에만 있다."""
    return resolve_solvent_deck(policy, variant, purpose,
                                runtime_verification)["route_fragment"]


def noneq_variant(scrf_line, mode):
    """`scrf=(...)` 조각에 `NonEq=write|read` 토큰을 삽입한다 (U-27 스모크용).

    이전에 실려 나간 형태(`scrf=(smd,solvent=acetonitrile,NonEq=write)`)와 같은 자리 —
    scrf 괄호 안 마지막 항목 — 에 넣는 순수 문자열 변환이다. 용매 결정 자체는
    resolve_solvent_line() 을 통과한 뒤에만 이 함수에 도달한다.
    """
    if mode not in ("write", "read"):
        raise ValueError("NonEq mode must be write|read, got %r" % (mode,))
    idx = scrf_line.find("scrf=(")
    if idx < 0:
        raise ValueError("not an scrf fragment: %r" % (scrf_line,))
    close = scrf_line.find(")", idx)
    if close < 0:
        raise ValueError("unbalanced scrf fragment: %r" % (scrf_line,))
    return scrf_line[:close] + ",NonEq=%s" % mode + scrf_line[close:]


def epsilon_scan_line(epsilon):
    """The `scrf=` fragment for ONE point of the eps sensitivity scan.

    🟢 THIS IS ALLOWED WITHOUT THE DESCRIPTORS, and it is the reason the ordering ruling works:
       the scan varies eps ALONE on already-computed geometries. It is not a production solvent
       model and must never be mistaken for one -- it carries no HBond or surface-tension terms
       at all, which is exactly why its result BOUNDS the error rather than estimating it.

    🔴 And it is still not acetonitrile: eps is set numerically, never by solvent name.
    """
    if epsilon is None or float(epsilon) <= 0:
        raise ValueError("epsilon must be a positive number, got %r" % (epsilon,))
    return {
        "line": "scrf=(smd,solvent=generic,read) Eps=%s" % float(epsilon),
        "epsilon": float(epsilon),
        "is_production_solvent_model": False,
        "why_this_is_allowed_without_descriptors": (
            "the scan varies EPS ALONE, on geometries that already exist. It measures the "
            "ELECTROSTATIC response and nothing else -- no HBond terms, no surface tension -- "
            "which is precisely why a SMALL spread BOUNDS the full response. 🔴 A LARGE spread "
            "does NOT, and escalates to re-optimisation on one reaction."),
        "🔴": ("NOT a production solvent line. Do not reuse this for a production deck: "
               "solvent.solvent_line() is the only thing that may build one, and it refuses "
               "until the descriptors exist."),
    }
