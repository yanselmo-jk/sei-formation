"""Gaussian 16 출력 파서 — 순수 함수.

🔴 **ORCA 파서를 재사용하지 않는다.** 출력 형식이 완전히 다르다(lead 지시).
ORCA는 `VIBRATIONAL FREQUENCIES` 블록에 `n: -450.12 cm**-1`, G16은
`Frequencies --  -450.1234  112.4  331.0` 형태로 한 줄에 최대 3개씩 나온다.

[UNVERIFIED] 우리는 Gaussian16을 갖고 있지 않다. 아래 패턴은 G16 출력 규약 기준이며,
**사용자 클러스터에서 수초짜리 route 사전검증(smoke)이 최초 검증**이다.
그래서 파싱 실패를 조용히 넘기지 않고 전부 표시한다.

🔴🔴 STANDING CHECK — FOR EVERY FIELD WE **READ**, SAY WHAT IT DOES AND DOES NOT ESTABLISH.
(The complement of "for every field we ADD, name its consumer". The two catch opposite
failures: that one catches fields nobody reads; this one catches fields that ARE read, for
something they cannot actually establish.)
Measured on this cluster, both directions, in one round:
```
rc == 0                 HID an L1110 segfault -- the job aborted and still exited zero
rc != 0                 sits on 17 P5 rows that CONVERGED
normal_termination      a bare string-presence check. In an `opt freq` job it is true once the
                        OPT half finishes, so it read TRUE on species with ZERO frequencies
route says `freq`       says what was ASKED for. Establishes nothing about what ran.
```
⟹ `rc` is never a QC-stage health signal in either direction, and neither is
`normal_termination` on a multi-stage job. **Stage completion is read from OUTPUT EVIDENCE
only** -- see `stages_completed`, which exists because of exactly this.
🔒 §39.69(d)'s "non-zero exit ⇒ no verdict" covers one direction; this is the other one, and it
is the more dangerous of the two because it fails toward *believing a result*.
"""

import re

#: 원자번호 → 기호. G16의 orientation 블록은 원자번호로 찍는다.
Z_TO_SYMBOL = {
    1: "H", 2: "He", 3: "Li", 4: "Be", 5: "B", 6: "C", 7: "N", 8: "O", 9: "F",
    10: "Ne", 11: "Na", 12: "Mg", 13: "Al", 14: "Si", 15: "P", 16: "S",
    17: "Cl", 18: "Ar", 19: "K", 20: "Ca", 26: "Fe", 28: "Ni", 29: "Cu",
    30: "Zn", 35: "Br", 53: "I",
}

RE_FREQ = re.compile(r"^\s*Frequencies\s*--\s*(.+)$")
RE_SCF = re.compile(r"^\s*SCF Done:\s+E\(([^)]*)\)\s*=\s*(-?\d+\.\d+)"
                    r"\s+A\.U\.\s+after\s+(\d+)\s+cycles", re.I)
RE_ORIENT = re.compile(r"(Standard orientation|Input orientation)\s*:")
RE_ATOM_ROW = re.compile(r"^\s*\d+\s+(\d+)\s+(?:-?\d+\s+)?"
                         r"(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$")
RE_CHARGE_MULT = re.compile(r"Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=\s*(\d+)")
RE_CPU_TIME = re.compile(r"Job cpu time:\s*(\d+)\s*days?\s*(\d+)\s*hours?\s*"
                         r"(\d+)\s*minutes?\s*([\d.]+)\s*seconds", re.I)
RE_ELAPSED = re.compile(r"Elapsed time:\s*(\d+)\s*days?\s*(\d+)\s*hours?\s*"
                        r"(\d+)\s*minutes?\s*([\d.]+)\s*seconds", re.I)
RE_ROUTE = re.compile(r"^\s*#[pPnNtT]?\s+(.*)$")

#: 🔴 G16 특유의 조용한 실패. `%mem` 부족은 성능 저하가 아니라 **죽음**으로 나타난다.
MEMORY_ERROR_HINTS = ("galloc", "could not allocate memory",
                      "Out-of-memory error", "insufficient memory")
#: route line 자체가 거부된 경우 (범함수/기저 이름 오류가 여기로 나온다)
ROUTE_ERROR_HINTS = ("Unrecognized", "is not a valid", "Unknown method",
                     "basis set not found", "Illegal", "syntax error")


def parse_termination(text):
    """정상 종료 여부 + 오류 원문.

    G16은 실패해도 exit code가 애매한 경우가 있어 **로그 문자열이 정본**이다.
    """
    if not text:
        return {"normal": False, "reason": "log_empty", "message": ""}
    normal = "Normal termination of Gaussian" in text
    if normal:
        return {"normal": True, "reason": None, "message": ""}
    msg = ""
    for m in re.finditer(r"Error termination.*", text):
        msg = m.group(0)[:300]
    if not msg:
        tail = [ln for ln in text.strip().splitlines()[-15:] if ln.strip()]
        msg = " | ".join(tail)[-300:]
    reason = "error_termination"
    if any(h.lower() in text.lower() for h in MEMORY_ERROR_HINTS):
        reason = "memory"
    elif any(h.lower() in text.lower() for h in ROUTE_ERROR_HINTS):
        reason = "route_rejected"
    return {"normal": False, "reason": reason, "message": msg}


def parse_frequencies(text):
    """`Frequencies --` 줄들 → cm^-1 리스트 (마지막 freq 계산분).

    G16은 허수진동수를 **음수**로 인쇄한다(ORCA와 같은 관례).
    한 줄에 최대 3개가 들어가고, 계산이 여러 번이면 마지막 묶음만 쓴다.
    """
    if not text:
        return []
    groups = []
    cur = []
    seen_any = False
    for line in text.splitlines():
        m = RE_FREQ.match(line)
        if m:
            seen_any = True
            for tok in m.group(1).split():
                try:
                    cur.append(float(tok))
                except ValueError:
                    pass
        elif seen_any and cur and ("Thermochemistry" in line
                                   or "Zero-point correction" in line):
            groups.append(cur)
            cur = []
            seen_any = False
    if cur:
        groups.append(cur)
    return groups[-1] if groups else []


def parse_scf(text):
    """`SCF Done:` → 에너지·사이클 목록."""
    energies, cycles, methods = [], [], []
    for line in (text or "").splitlines():
        m = RE_SCF.match(line)
        if m:
            methods.append(m.group(1))
            energies.append(float(m.group(2)))
            cycles.append(int(m.group(3)))
    return {"energies_hartree": energies, "cycles": cycles,
            "method_tags": methods,
            "max_cycles": max(cycles) if cycles else None,
            "total_cycles": sum(cycles) if cycles else None,
            "final_energy_hartree": energies[-1] if energies else None,
            "converged": bool(energies)}


def parse_geometries(text):
    """모든 orientation 블록 → [[(sym,x,y,z), ...], ...] (Angstrom)."""
    lines = (text or "").splitlines()
    out = []
    i = 0
    while i < len(lines):
        if RE_ORIENT.search(lines[i]):
            atoms = []
            j = i + 1
            # 헤더 몇 줄을 건너뛴 뒤 원자 행이 나온다
            while j < len(lines) and not RE_ATOM_ROW.match(lines[j]):
                if "----" not in lines[j] and not lines[j].strip():
                    break
                j += 1
            while j < len(lines):
                m = RE_ATOM_ROW.match(lines[j])
                if not m:
                    break
                z = int(m.group(1))
                atoms.append((Z_TO_SYMBOL.get(z, "X%d" % z),
                              float(m.group(2)), float(m.group(3)),
                              float(m.group(4))))
                j += 1
            if atoms:
                out.append(atoms)
            i = j
        else:
            i += 1
    return out


def last_geometry(text):
    geoms = parse_geometries(text)
    return geoms[-1] if geoms else []


#: 🔴 Normal-mode 블록. 기본(저정밀) 형식은 한 블록에 최대 3개 모드를 싣고 변위를
#: **소수 2자리**로 찍는다:
#:     Frequencies --    -48.4416                36.6608                96.6906
#:     Red. masses --      7.1479                 6.4933                 4.2088
#:     ...
#:      Atom  AN      X      Y      Z        X      Y      Z        X      Y      Z
#:         1   6    -0.11   0.02  -0.03     0.03   0.02  -0.12     0.00   0.02  -0.04
#: ⚠ `freq=hpmodes` 는 **다른** 형식(`Frequencies ---`, 5개씩, 좌표당 한 줄)을 추가로
#: 찍는다. 그 형식은 여기서 파싱하지 않고 **경고로 드러낸다** — 조용히 잘못 읽는 것보다
#: 낫다. [VERIFIED — 실 로그: cpu_machine_pilot_results/.../jobs/P1/ts_qst2.log]
RE_MODE_FREQ = re.compile(r"^\s*Frequencies\s*--\s+(-?\d.*)$")
RE_MODE_REDMASS = re.compile(r"^\s*Red\.\s*masses\s*--\s+(.+)$")
RE_MODE_ATOMHDR = re.compile(r"^\s*Atom\s+AN\s+X\s+Y\s+Z")
RE_MODE_ROW = re.compile(r"^\s*(\d+)\s+(\d+)\s+((?:\s*-?\d+\.\d+){3,})\s*$")


def parse_normal_modes(text):
    """마지막 freq 계산의 normal mode → 기하 + 모드 목록.

    반환:
      {"geometry": [(sym,x,y,z), ...],            # 변위와 **같은 orientation** 의 기하
       "modes": [{"index", "freq_cm1", "reduced_mass_amu",
                  "displacements": [(sym, dx, dy, dz), ...]}, ...],
       "warnings": [...]}

    🔴 기하는 `last_geometry` 가 아니라 **모드 블록 바로 앞의 orientation** 을 쓴다.
    변위 벡터는 그 orientation 계에서 정의되므로, 다른 블록의 좌표와 섞으면 결합 방향이
    회전한 채로 projection 이 계산된다 — 숫자는 나오고 조용히 틀린다.
    🔴 판정하지 않는다(C-3). 여기서 나오는 것은 전부 데이터다.
    """
    lines = (text or "").splitlines()
    warnings = []
    if any(l.lstrip().startswith("Frequencies ---") for l in lines):
        warnings.append(
            "this log contains a `freq=hpmodes` high-precision block (`Frequencies ---`) "
            "which this parser does NOT read; the low-precision (2-decimal) block is used "
            "instead. If Omega precision matters, read the hpmodes block.")
    # 마지막 freq 계산의 시작 = 마지막 'Frequencies --' 들의 첫 번째 블록
    freq_idx = [i for i, l in enumerate(lines) if RE_MODE_FREQ.match(l)]
    if not freq_idx:
        return {"geometry": [], "modes": [], "warnings": warnings + ["no `Frequencies --` block"]}
    # 같은 freq 계산에 속한 블록들: 첫 모드 번호가 1 로 다시 시작하는 지점부터
    start = freq_idx[0]
    for i in freq_idx:
        # 블록 헤더의 모드 번호 줄(주파수 줄 2줄 위)이 '1' 로 시작하면 새 freq 계산이다
        head = lines[i - 2].split() if i >= 2 else []
        if head and head[0] == "1":
            start = i
    geoms = [g for g in parse_geometries("\n".join(lines[:start]))]
    geometry = geoms[-1] if geoms else []

    modes = []
    i = start
    while i < len(lines):
        m = RE_MODE_FREQ.match(lines[i])
        if not m:
            i += 1
            if i - start > 0 and modes and not any(RE_MODE_FREQ.match(l)
                                                   for l in lines[i:i + 40]):
                break
            continue
        freqs = [float(v) for v in m.group(1).split()]
        red = []
        j = i + 1
        while j < len(lines) and not RE_MODE_ATOMHDR.match(lines[j]):
            mr = RE_MODE_REDMASS.match(lines[j])
            if mr:
                red = [float(v) for v in mr.group(1).split()]
            j += 1
        j += 1                                   # Atom/AN 헤더 다음 줄부터 원자 행
        cols = [[] for _ in freqs]
        while j < len(lines):
            mrow = RE_MODE_ROW.match(lines[j])
            if not mrow:
                break
            vals = [float(v) for v in mrow.group(3).split()]
            z = int(mrow.group(2))
            sym = Z_TO_SYMBOL.get(z, "X%d" % z)
            for k in range(len(freqs)):
                if 3 * k + 2 < len(vals):
                    cols[k].append((sym, vals[3 * k], vals[3 * k + 1], vals[3 * k + 2]))
            j += 1
        for k, f in enumerate(freqs):
            modes.append({"index": len(modes) + 1, "freq_cm1": f,
                          "reduced_mass_amu": red[k] if k < len(red) else None,
                          "displacements": cols[k]})
        i = j
    if geometry and modes and len(modes[0]["displacements"]) != len(geometry):
        warnings.append(
            "geometry has %d atoms but the mode block carries %d -- refusing to pair them "
            "would be safer than reporting an overlap computed on mismatched indices"
            % (len(geometry), len(modes[0]["displacements"])))
    return {"geometry": geometry, "modes": modes, "warnings": warnings}


#: Gaussian's per-point IRC arc length. [VERIFIED against the delivered P1 IRC logs:
#: "   NET REACTION COORDINATE UP TO THIS POINT =    0.07572"]
RE_IRC_ARC = re.compile(r"NET REACTION COORDINATE UP TO THIS POINT\s*=\s*(-?\d+\.\d+)")


def parse_irc_arc_lengths(text):
    """Per-point `NET REACTION COORDINATE`, in order — the axis B+ picks its midpoint on.

    🔴 Arc length, NOT index. A midpoint by index is a fraction of however many points the run
    happened to produce, which is a constant in disguise once C-2.2 makes short IRCs common;
    the middle of the reaction coordinate is the middle whatever the point count.
    """
    return [float(v) for v in RE_IRC_ARC.findall(text or "")]


# NOTE: `opt_energy_resolution_hartree` lived here. It read G16's last
# `Predicted change in Energy` and existed only to serve §39.70(ii) option (a),
# which was REJECTED: that figure is a within-run prediction for the NEXT step,
# not the resolution at which two independent optimisations agree. The ruling
# (§39.71) derives the tolerance from G16's printed force/displacement thresholds
# instead -- see `guards.BPLUS_ENERGY_TOLERANCE_EV`. Deleted rather than left
# lying around, so nobody wires the rejected option by finding it.

#: 🔴 [critic10 / proposer7] WHICH STAGES ACTUALLY RAN — not a boolean about one of them.
#:
#: THE DEFECT THIS REPLACES: P5's `converged` was `normal_termination AND opt.converged`, and
#: `normal_termination` is a bare string-presence check. In an `opt freq` job the string is
#: present once the OPT half finishes, so `converged` read **true on species whose freq stage
#: had crashed** -- measured: `Optimization completed` x1, `Normal termination` x1,
#: `Frequencies --` **x0**, with `EpsInf=0.0000` and an L1110 stack trace in the same log.
#: 🔒 WHY NOT JUST RENAME IT `converged_opt`: that fixes today's confusion and reproduces the
#: failure the next time someone adds a third stage and forgets what the boolean covers. Naming
#: the stages that ran makes a missing one unmissable regardless of what any boolean is called,
#: and it generalises without another rename.
STAGE_EVIDENCE = (
    ("scf", "SCF Done"),
    ("opt", "Optimization completed"),
    ("freq", "Frequencies --"),
    ("thermo", "Thermochemistry"),
)

#: Route keywords that REQUEST a stage. Used only to say what was ASKED for -- the answer to
#: "did it run" always comes from output evidence, never from the request.
STAGE_REQUESTED_BY = {"opt": ("opt",), "freq": ("freq",), "thermo": ("freq",)}


def stages_completed(text, route=None):
    """Which computational stages left evidence in this log, and which were asked for.

    Returns `{"completed": [...], "requested": [...], "missing": [...], "evidence": {...}}`.

    🔴 `missing` is the field that matters: a stage the route requested and the output does not
    show. `normal_termination` cannot express that -- it fires on the first stage to finish.
    🔒 "Did it run" is answered ONLY from output evidence. The route says what was asked for;
    it never establishes what happened (the same discipline as `rc`, which this project has now
    seen lie in both directions).
    """
    t = text or ""
    evidence = dict((name, (mark in t)) for name, mark in STAGE_EVIDENCE)
    completed = [name for name, seen in evidence.items() if seen]
    route_text = (route or "")
    if not route_text:
        echo = parse_route_echo(t)
        route_text = echo.get("route_echoed") or ""
    low = route_text.lower()
    requested = sorted(set(
        stage for stage, keys in STAGE_REQUESTED_BY.items()
        if any(k in low for k in keys)))
    return {
        "completed": sorted(completed),
        "requested": requested,
        "missing": sorted(s for s in requested if not evidence.get(s)),
        "evidence": evidence,
        "_note": ("`completed` is read from OUTPUT evidence, never from the route or from an "
                  "exit code. `requested` is read from the route and establishes nothing about "
                  "what ran. A non-empty `missing` means the job stopped part-way even if it "
                  "printed `Normal termination`."),
    }


def parse_irc_path_frames(text):
    """IRC path points as `[{"arc": <net reaction coordinate>, "geometry": [...]}, ...]`.

    🔴 Each point's geometry is the orientation block that PRECEDES its
    `NET REACTION COORDINATE` line, not the last block in the file. An IRC log contains
    orientation blocks that are not path points (the starting structure, and the extra
    geometries a step's optimisation visits), so pairing by position in the file rather than by
    "the most recent block before this marker" would attach the wrong structure to the point --
    silently, and B+ would then optimise from a geometry that is not on the path.

    Returns points in path order. B+ selects two of them with `guards.bplus_sample_points`.
    """
    lines = (text or "").splitlines()
    out = []
    pending = None
    i = 0
    while i < len(lines):
        if RE_ORIENT.search(lines[i]):
            atoms = []
            j = i + 1
            while j < len(lines) and not RE_ATOM_ROW.match(lines[j]):
                if "----" not in lines[j] and not lines[j].strip():
                    break
                j += 1
            while j < len(lines):
                m = RE_ATOM_ROW.match(lines[j])
                if not m:
                    break
                z = int(m.group(1))
                atoms.append((Z_TO_SYMBOL.get(z, "X%d" % z), float(m.group(2)),
                              float(m.group(3)), float(m.group(4))))
                j += 1
            if atoms:
                pending = atoms
            i = j
            continue
        m = RE_IRC_ARC.search(lines[i])
        if m:
            out.append({"arc": float(m.group(1)), "geometry": pending})
            pending = None
        i += 1
    return out


def imaginary_modes(parsed):
    """freq < 0 인 모드만. G16 은 허수진동수를 음수로 찍는다."""
    return [m for m in (parsed or {}).get("modes") or [] if (m.get("freq_cm1") or 0) < 0]


#: 🔴 [C-2.1, §39.53] How an IRC ENDED, as data. G16 prints this itself:
#:     " Maximum number of steps reached."        <- the step budget ran out
#:     " Reaction path calculation complete."     <- printed in BOTH cases, so it is NOT
#:                                                   evidence that a minimum was reached
#:     " Minimum found on this side of the path." <- an actual minimum
#: [VERIFIED against cpu_machine_pilot_results/.../jobs/P1/irc_{forward,reverse}.log, where
#:  both directions printed "Maximum number of steps reached." AND "Normal termination", i.e.
#:  a run that satisfied every clause C-2 had at the time while having connected NOTHING.]
IRC_MAXPOINTS_MARK = "Maximum number of steps reached"
IRC_MINIMUM_MARK = "Minimum found on this side of the path"
#: 🔴 [linear-hopping-frog plan, Track A item 3, coder] `IRC_MINIMUM_MARK` above was NEVER
#: verified against a real log (only the maxpoints marker was, per the note above it) -- and
#: on this cluster's G16 it does not appear at all. `U56_RB_scan/irc_{forward,reverse}.log`
#: (both directions, real returned data) print this text instead when a minimum is found:
#:     " PES minimum detected on this side of the pathway."
#: Without this alternate, a GENUINE early minimum reads as
#: `termination_reason: "normal_termination_without_a_minimum_marker"` -- indistinguishable
#: from "clean exit, nothing established" even though G16 explicitly said it found one. This
#: is exactly what made U56_RB_scan's clean, short (1-point, arc 0.183 A) IRC look puzzling:
#: not a mis-detected truncation (`truncated` was already correctly `False` -- `maxpoints` was
#: not hit and `normal_termination` was `True`), but a real minimum G16 announced in words this
#: parser did not recognise.
IRC_MINIMUM_MARK_ALT = "PES minimum detected on this side of the pathway"
IRC_PATH_COMPLETE_MARK = "Reaction path calculation complete"


def parse_irc_completion(text):
    """How the IRC stopped -- data only, no verdict (the verdict is `guards.irc_verdict`).

    Returns:
      {"normal_termination", "maxpoints_reached", "minimum_found", "error_terminated",
       "path_calculation_complete", "termination_reason", "truncated"}

    🔴 `truncated` is the load-bearing field: an IRC that stopped because it ran out of STEPS
       (or was cut by a wall/budget cap, which leaves no marker at all) did not reach a minimum.
       It establishes NOTHING about what the transition state connects, and the money after it
       (the terminal optimisation) must not be spent on that basis.
    ⚠ A wall-clock or budget kill leaves NO G16 marker -- the log simply stops. That case shows
       up as `normal_termination = False` with `maxpoints_reached = False`, and it is truncation
       just the same. Both are BUDGET-class causes, not chemical ones.
    """
    t = text or ""
    # 🔴 the key is `normal`, NOT `normal_termination` -- reading the wrong key returns None,
    #    which this function would then have called "truncated" on a perfectly clean run.
    term = parse_termination(t)
    normal = term.get("normal")
    maxpoints = IRC_MAXPOINTS_MARK in t
    minimum = IRC_MINIMUM_MARK in t or IRC_MINIMUM_MARK_ALT in t
    # 🔴 [critic14, linear-hopping-frog Track A item 3] `normal is not True` used to be read as
    #    ONE shape ("log ends without a G16 termination line -- wall-clock/budget kill"), but
    #    that is wrong whenever the log DOES carry a real G16 marker -- `Error termination`,
    #    printed on U56_RA_scan/U56_RA_qst2's crashed IRC logs (corrector-integration failure,
    #    not a wall/budget cut: wall used was 1.8-5.3 h against a 48 h cap). An engine death
    #    described as "no marker" reads as plumbing-with-no-evidence when the evidence is right
    #    there in the log. Distinguish the two shapes; both still leave `truncated = True`.
    error_terminated = "Error termination" in t
    out = {
        "normal_termination": normal,
        "maxpoints_reached": maxpoints,
        "minimum_found": minimum,
        # 🔴 [critic14, lead ruling 2026-08-21] emitted as its OWN field, not just folded into
        #    `termination_reason`'s prose -- `guards.irc_direction_ok` tags a crashed IRC
        #    `engine` (§39.69) off THIS field, never by substring-mining the reason string
        #    (the same discipline this project already applies to `cause_tags` elsewhere:
        #    a real B+ bifurcation and a plain step-budget stop both begin "IRC was TRUNCATED
        #    (...)", and deriving class from prose bucketed that wrong once already).
        "error_terminated": error_terminated,
        "path_calculation_complete": IRC_PATH_COMPLETE_MARK in t,
        "_note": ("`Reaction path calculation complete.` is printed for a maxpoints stop TOO "
                  "-- it is not evidence of a minimum. Read `minimum_found`."),
    }
    if maxpoints:
        out["termination_reason"] = "maxpoints"
    elif error_terminated:
        out["termination_reason"] = "error_termination (%s)" % (term.get("message") or "")[:160]
    elif normal is not True:
        out["termination_reason"] = ("no_marker (log ends without a G16 termination line -- "
                                     "wall-clock or budget kill leaves exactly this shape)")
    elif minimum:
        out["termination_reason"] = "minimum_found"
    else:
        out["termination_reason"] = "normal_termination_without_a_minimum_marker"
    out["truncated"] = bool(maxpoints or (normal is not True))
    return out


#: G16 UKS 가 SCF 마다 찍는 스핀 오염 줄:
#: " S**2 before annihilation     0.7539,   after     0.7500"
RE_S2_ANNIHILATION = re.compile(
    r"S\*\*2 before annihilation\s+(-?\d+\.\d+),?\s+after\s+(-?\d+\.\d+)")


def parse_s2(text):
    """⟨S²⟩ (annihilation 전/후) — §39.42(a) 요구 emission 의 파서.

    🔴 숫자만 반환한다, 판정 없음 (C-3): doublet 의 청정값은 0.75 이지만 어디까지가
    "심한 오염"인지는 여기서 정하지 않는다. UKS 참조가 오염된 "endpoint" 는 우리가
    인증했다고 생각한 종이 아닐 수 있고, 이 값이 없으면 체인의 어느 것도 그것을
    알아차리지 못한다.
    """
    vals = [{"before": float(m.group(1)), "after": float(m.group(2))}
            for m in RE_S2_ANNIHILATION.finditer(text or "")]
    return {"values": vals,
            "last": vals[-1] if vals else None,
            "n_records": len(vals),
            "_clean_doublet_reference": 0.75}


def parse_relaxed_scan(text):
    """relaxed scan 로그(opt=modredundant + `B i j S N step`) → 스캔 점 목록.

    한 점 = 제약 최적화 1회의 수렴("Optimization completed") 시점. 그 점의 에너지는
    직전 마지막 `SCF Done:`, 기하는 그 시점까지의 마지막 orientation 블록이다.

    🔴 반환값의 지위: 최고점은 **rigid path 의 최대점이지 saddle 이 아니다**
    (§39.39(d) U56-1 실패 모드 (i)). 후속 opt=(ts,calcfc)+freq 가 그것을 판정한다 —
    이 파서는 TS guess 를 고르는 배관이지 화학 판정이 아니다.
    ⚠ [UNVERIFIED — 실 스캔 로그 미확보] 이 형태('SCF Done' → orientation →
    'Optimization completed' 반복)는 G16 opt 로그의 일반 형태에서 유도했고 mock 으로
    고정했다. 첫 실 클러스터 스캔 로그가 오면 fixture 로 잡아 재검증하라 (S-1 의
    evidence_lines 규칙과 같은 순서: 실물 → 규칙, 추측 → 규칙 금지).
    """
    lines = (text or "").splitlines()
    points = []
    last_scf = None
    last_geom = None
    i, n = 0, len(lines)
    while i < n:
        line = lines[i]
        m = RE_SCF.match(line)
        if m:
            last_scf = float(m.group(2))
            i += 1
            continue
        if RE_ORIENT.search(line):
            atoms = []
            j = i + 1
            while j < n and not RE_ATOM_ROW.match(lines[j]):
                if "----" not in lines[j] and not lines[j].strip():
                    break
                j += 1
            while j < n:
                mm = RE_ATOM_ROW.match(lines[j])
                if not mm:
                    break
                z = int(mm.group(1))
                atoms.append((Z_TO_SYMBOL.get(z, "X%d" % z), float(mm.group(2)),
                              float(mm.group(3)), float(mm.group(4))))
                j += 1
            if atoms:
                last_geom = atoms
            i = j
            continue
        if "Optimization completed" in line:
            # 스캔 점 1개 종결. "Stationary point found" 는 같은 점의 두 번째 표지라
            # 트리거로 쓰지 않는다(이중 계수 방지).
            points.append({"point_index": len(points) + 1,
                           "energy_hartree": last_scf,
                           "geometry": list(last_geom or [])})
            last_scf = None      # 다음 점은 자기 SCF 를 새로 가져야 한다
        i += 1

    with_e = [p for p in points if p["energy_hartree"] is not None]
    max_pt = max(with_e, key=lambda p: p["energy_hartree"]) if with_e else None
    return {
        "n_points": len(points),
        "n_points_with_energy": len(with_e),
        "points": points,
        "max_point_index": max_pt["point_index"] if max_pt else None,
        "max_energy_hartree": max_pt["energy_hartree"] if max_pt else None,
        "warnings": ([] if len(with_e) == len(points) else
                     ["🔴 scan_points_without_energy: %d of %d converged scan points have "
                      "no parsed SCF energy -- the maximum below ignores them and may be "
                      "wrong. Read the raw log." % (len(points) - len(with_e), len(points))]),
    }


def parse_opt_status(text):
    """최적화 수렴 여부 + 사이클 수."""
    if not text:
        return {"converged": False, "cycles": None, "stationary_point": False}
    conv = ("Optimization completed" in text
            or "Stationary point found" in text)
    n = len(re.findall(r"Step number\s+\d+", text)) or None
    return {"converged": bool(conv),
            "cycles": n,
            "stationary_point": "Stationary point found" in text}


def parse_timings(text):
    """`Job cpu time` / `Elapsed time` → 초. G16이 자기 계측을 준다."""
    def _sec(m):
        if not m:
            return None
        d, h, mi, s = m.groups()
        return int(d) * 86400 + int(h) * 3600 + int(mi) * 60 + float(s)
    return {"cpu_seconds": _sec(RE_CPU_TIME.search(text or "")),
            "elapsed_seconds": _sec(RE_ELAPSED.search(text or ""))}


def parse_charge_mult(text):
    m = RE_CHARGE_MULT.search(text or "")
    if not m:
        return {"charge": None, "multiplicity": None}
    return {"charge": int(m.group(1)), "multiplicity": int(m.group(2))}


# --- route echo: THE 70-COLUMN TRUNCATION DEFECT (B-1) -----------------------
#
# 🔴 RT-1 stored three routes that were **cut at exactly 70 characters with no
#    marker**, and downstream code then read ABSENCE off them.
#
#    ts_qst2.log       len=70  '...opt=(qst2,calcfc,noeigen'      unbalanced '('
#    irc_forward.log   len=70  '...irc=(calcfc,forward,maxp'      unbalanced '('
#    irc_reverse.log   len=70  '...irc=(calcfc,reverse,maxp'      unbalanced '('
#
#    Four independent proofs that this is a fixed-width cut, not the real route:
#      1. three DIFFERENT routes, all EXACTLY 70 chars
#      2. all three end mid-token ('noeigen', 'maxp') with unbalanced parens
#      3. 🔒 decisive: `freq` does not appear in the ts route, yet n_frequencies=27
#         and imag_freq_cm=-105.0 were parsed FROM THAT SAME LOG.
#         **The report refutes its own field.**
#      4. [MEASURED, coder7] rebuilding the requested route from
#         config/qc_levels.json's job_type templates and cutting it at 70 chars
#         reproduces ALL THREE stored strings BYTE-FOR-BYTE. The ts tail that was
#         lost is exactly 'test,maxcycles=100) freq' (94 -> 70).
#
#    CAUSE: Gaussian wraps its echoed route at this column inside the dashed
#    block; the old parse_route() returned ONLY THE FIRST PHYSICAL LINE and
#    stored it under the bare name "route". Nothing marked it.
#
# ⟹ The fix is BOTH halves:
#    (a) reassemble the continuation lines, so we store the FULL route; and
#    (b) 🔴 emit a completeness field ALONGSIDE it, and make asking
#        "is keyword X absent?" RAISE when completeness is not established.
#        (b) is the half that matters: (a) can silently regress, (b) cannot.
#
#: [MEASURED] RT-1, three routes, all cut here. Reproduced from the templates.
ROUTE_ECHO_WRAP_COLUMNS = 70

#: The echoed route block is delimited by a run of dashes. Reassembly stops there.
RE_ROUTE_BLOCK_END = re.compile(r"^\s*-{4,}\s*$")

#: Hard cap on continuation lines, so a log with no closing delimiter cannot
#: swallow the whole file into "the route". Hitting the cap => NOT complete.
ROUTE_ECHO_MAX_LINES = 8


class RouteTruncatedError(RuntimeError):
    """Raised when a caller asks a truncated/unverified route a question that
    only a COMPLETE route can answer (i.e. "is this keyword absent?").

    🔴 This RAISES rather than returning a flag on purpose. A returned flag is a
    thing a caller may decline to read, and reading absence off the truncated
    RT-1 route is exactly how `nosymm? False | freq? False` was believed.
    """


def _balanced(s):
    """Parentheses balance of a route fragment. None if there is nothing to check."""
    if s is None:
        return None
    depth = 0
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth < 0:
                return False
    return depth == 0


def parse_route_echo(text):
    """Reassemble the echoed route and REPORT ITS COMPLETENESS as data.

    Returns a record whose field names carry the caveat (a name travels into
    every downstream table; a docstring does not):

        route_echoed                          str|None   full reassembled text
        route_echoed_is_complete              True|False|None
        route_echoed_line_count               int
        route_echoed_char_length              int|None
        route_echoed_first_line_char_length   int|None
        route_echo_parentheses_balanced       bool|None
        route_echo_terminated_by_block_rule   bool|None
        route_echo_wrap_columns_assumed       int
        route_echo_completeness_evidence      str
        absence_of_a_keyword_may_not_be_read_from_this_route   bool

    🔴 `route_echoed_is_complete` is None when NOTHING WAS CHECKED (no route
    found at all) and False when it was checked and came back negative. They are
    never interchanged.
    """
    rec = {
        "route_echoed": None,
        "route_echoed_is_complete": None,
        "route_echoed_line_count": 0,
        "route_echoed_char_length": None,
        "route_echoed_first_line_char_length": None,
        "route_echo_parentheses_balanced": None,
        "route_echo_terminated_by_block_rule": None,
        "route_echo_wrap_columns_assumed": ROUTE_ECHO_WRAP_COLUMNS,
        "route_echo_completeness_evidence": "no route line found in this log",
        "absence_of_a_keyword_may_not_be_read_from_this_route": True,
    }
    lines = (text or "").splitlines()
    start = None
    for i, line in enumerate(lines):
        m = RE_ROUTE.match(line)
        if m and len(m.group(1)) > 3:
            start = i
            break
    if start is None:
        return rec

    first = ("#" + lines[start].strip().lstrip("#")).strip()
    parts = [first]
    terminated = False
    for line in lines[start + 1:start + 1 + ROUTE_ECHO_MAX_LINES]:
        if RE_ROUTE_BLOCK_END.match(line) or not line.strip():
            terminated = True
            break
        parts.append(line.strip())
    # G16 wraps at a column, not at a token boundary: 'noeigen' + 'test' must
    # rejoin as 'noeigentest'. A line that was cut mid-token has no trailing
    # space, so glue those two directly instead of inserting one.
    joined = first
    for p in parts[1:]:
        if not p:
            continue
        if len(joined) >= ROUTE_ECHO_WRAP_COLUMNS and not joined.endswith(" "):
            joined = joined + p
        else:
            joined = joined + " " + p

    balanced = _balanced(joined)
    rec["route_echoed"] = joined
    rec["route_echoed_line_count"] = len([p for p in parts if p])
    rec["route_echoed_char_length"] = len(joined)
    rec["route_echoed_first_line_char_length"] = len(first)
    rec["route_echo_parentheses_balanced"] = balanced
    rec["route_echo_terminated_by_block_rule"] = terminated

    if not terminated:
        rec["route_echoed_is_complete"] = False
        rec["route_echo_completeness_evidence"] = (
            "the echoed route block was not closed by a delimiter within %d lines"
            % ROUTE_ECHO_MAX_LINES)
    elif balanced is False:
        rec["route_echoed_is_complete"] = False
        rec["route_echo_completeness_evidence"] = (
            "unbalanced parentheses after reassembly (len=%d) - the echo is cut"
            % len(joined))
    else:
        rec["route_echoed_is_complete"] = True
        rec["route_echo_completeness_evidence"] = (
            "reassembled %d echoed line(s), block closed by delimiter, "
            "parentheses balanced" % rec["route_echoed_line_count"])
    rec["absence_of_a_keyword_may_not_be_read_from_this_route"] = (
        rec["route_echoed_is_complete"] is not True)
    return rec


def route_record_from_stored_string(value, source="stored report field"):
    """Classify a route string that was ALREADY STORED by an older run.

    🔴 `route_echoed_is_complete` is **never True** here, by construction. A bare
    stored string carries no block context, so completeness cannot be
    established from it - only REFUTED (unbalanced parens, or a length at the
    wrap column). Everything else is None = NOT CHECKED, not "fine".

    This is the function that must be used on `cpu_machine_pilot_results/`:
    those three routes were written by the defective parser.
    """
    rec = {
        "route_echoed": value,
        "route_echoed_is_complete": None,
        "route_echoed_line_count": 1 if value else 0,
        "route_echoed_char_length": len(value) if isinstance(value, str) else None,
        "route_echoed_first_line_char_length": (
            len(value) if isinstance(value, str) else None),
        "route_echo_parentheses_balanced": _balanced(value if isinstance(value, str) else None),
        "route_echo_terminated_by_block_rule": None,
        "route_echo_wrap_columns_assumed": ROUTE_ECHO_WRAP_COLUMNS,
        "route_echo_completeness_evidence": (
            "%s: a bare stored string has no block context; completeness can be "
            "refuted but never established" % source),
        "absence_of_a_keyword_may_not_be_read_from_this_route": True,
    }
    if not isinstance(value, str) or not value:
        rec["route_echoed_line_count"] = 0
        rec["route_echo_completeness_evidence"] = "%s: no route stored" % source
        return rec
    if rec["route_echo_parentheses_balanced"] is False:
        rec["route_echoed_is_complete"] = False
        rec["route_echo_completeness_evidence"] = (
            "%s: unbalanced parentheses at len=%d - TRUNCATED"
            % (source, len(value)))
    elif len(value) >= ROUTE_ECHO_WRAP_COLUMNS:
        rec["route_echoed_is_complete"] = False
        rec["route_echo_completeness_evidence"] = (
            "%s: len=%d reaches the %d-column echo wrap - TRUNCATED"
            % (source, len(value), ROUTE_ECHO_WRAP_COLUMNS))
    return rec


def keyword_in_route(record, keyword):
    """True / False / None for "does this route carry `keyword`?".

    🔴 **None means CANNOT BE DETERMINED**, and it is returned whenever the
    keyword is not found in a route whose completeness is not established.
    Finding it is positive evidence regardless of truncation; NOT finding it in a
    truncated route is no evidence at all.
    """
    text = (record or {}).get("route_echoed")
    if not isinstance(text, str) or not text:
        return None
    if keyword.lower() in text.lower():
        return True
    if (record or {}).get("route_echoed_is_complete") is True:
        return False
    return None


def require_keyword_known_absent(record, keyword, context=""):
    """RAISE unless the route is complete AND the keyword is genuinely absent.

    🔴 This exists so that "keyword X was not used" can never be asserted off a
    truncated route again. Callers that only want to KNOW should call
    `keyword_in_route` and handle None.
    """
    verdict = keyword_in_route(record, keyword)
    if verdict is None:
        raise RouteTruncatedError(
            "cannot assert `%s` is absent%s: %s (route_echoed_is_complete=%r, "
            "len=%r). Mark it [UNKNOWN - the stored route is truncated], which "
            "is a different and more useful statement than \"absent\"."
            % (keyword, (" (%s)" % context) if context else "",
               (record or {}).get("route_echo_completeness_evidence"),
               (record or {}).get("route_echoed_is_complete"),
               (record or {}).get("route_echoed_char_length")))
    if verdict is True:
        raise RouteTruncatedError(
            "`%s` IS PRESENT in the route%s - it is not absent."
            % (keyword, (" (%s)" % context) if context else ""))
    return None


def parse_route(text):
    """에코된 route line. 실제로 무엇을 계산했는지의 정본.

    🔴 Returns the **fully reassembled** route (all echoed continuation lines),
    not just the first physical line. See the B-1 block above.
    ⚠ A bare string cannot carry its own completeness - callers that need to
    reason about ABSENCE must use `parse_route_echo()` and its record.
    """
    return parse_route_echo(text)["route_echoed"]


def summarize(text):
    """한 계산의 표준 요약. 회신 JSON에 그대로 실린다."""
    term = parse_termination(text)
    _route_echo = parse_route_echo(text)
    scf = parse_scf(text)
    opt = parse_opt_status(text)
    tim = parse_timings(text)
    return {
        "code": "gaussian16",
        "normal_termination": term["normal"],
        "failure_reason": term["reason"],
        "failure_message": term["message"],
        # 🔴 TWO FIELDS, NEVER ONE. `route_echoed` alone was read as authoritative
        #    for a full second by the lead ("nosymm? False | freq? False") off a
        #    string that had been cut at column 70. The companion field is not
        #    decoration - it is the field that makes the first one readable.
        "route_echoed": _route_echo["route_echoed"],
        "route_echoed_is_complete": _route_echo["route_echoed_is_complete"],
        "route_echo": _route_echo,
        "charge_multiplicity": parse_charge_mult(text),
        "scf": {k: scf[k] for k in ("max_cycles", "total_cycles",
                                    "final_energy_hartree", "converged")},
        "opt": opt,
        "timings": tim,
        "n_frequencies": len(parse_frequencies(text)),
        # 🔴 [C-2.1] present ONLY when this log actually is an IRC. `None` on a non-IRC log
        #    is correct and load-bearing: C-2 then reports "how the path ended was not
        #    measured" rather than silently treating an unknown as a permission (Rule 18).
        "irc_completion": (parse_irc_completion(text)
                           if (text and (IRC_PATH_COMPLETE_MARK in text
                                         or IRC_MAXPOINTS_MARK in text
                                         or IRC_MINIMUM_MARK in text
                                         or IRC_MINIMUM_MARK_ALT in text))
                           else None),
    }


#: [S-1] G16 출력에서 유전상수를 찾는 **후보 패턴들**. 🔴 우리는 이 클러스터의 G16 이
#: PCM 유전상수를 정확히 어떤 문자열로 찍는지 확인하지 못했다 — 지어내지 않는다.
#: 그래서 (i) 관대한 후보 패턴 여러 개로 스캔하고, (ii) **매치된 줄 원문을 그대로
#: 회신에 싣고**, (iii) 못 찾으면 거부한다. 첫 실 클러스터 로그가 이 패턴을 검증한다.
RE_DIELECTRIC_CANDIDATES = (
    re.compile(r"(?i)dielectric\s+constant[^0-9]*([0-9]+\.[0-9]+)"),
    re.compile(r"(?i)\beps\s*=?\s*([0-9]+\.[0-9]+)"),
    re.compile(r"(?i)\bepsilon\s*=?\s*([0-9]+\.[0-9]+)"),
)


def parse_scrf_dielectric(text):
    """[S-1] 로그에서 유전상수 후보값 전부와 그 줄 원문을 수집한다.

    ⚠ 순환 증거 위험을 그대로 기록한다: G16 이 `read` 추가 입력 섹션을 **에코**하면
    입력의 `eps=18.5` 줄 자체가 매치될 수 있다 — 에코는 '적용됐다'의 증거가 아니다.
    그래서 값만 돌려주지 않고 evidence_lines(원문)를 함께 실어, 사람이 매치가
    입력 에코인지 G16 자신의 SCRF 설정 출력인지 볼 수 있게 한다.
    """
    values, lines = [], []
    for raw in (text or "").splitlines():
        for pat in RE_DIELECTRIC_CANDIDATES:
            m = pat.search(raw)
            if m:
                try:
                    values.append(float(m.group(1)))
                except ValueError:
                    continue
                if raw.strip() not in lines:
                    lines.append(raw.strip())
                break
    return {
        "values": values,
        "evidence_lines": lines[:10],
        "n_matches": len(values),
        "_echo_caveat": ("매치에는 read 입력 섹션의 에코가 포함될 수 있다 — "
                         "evidence_lines 원문으로 판단하라. 패턴 자체가 "
                         "[UNVERIFIED — cluster route smoke required] 후보다."),
    }


def parse_cartesian_forces(text):
    """Last `Cartesian Forces:  Max <x> RMS <y>` (Hartree/Bohr). None when absent.

    [§39.97(b)/§39.103] the per-row instrument of the freq-from-stored-geometry recovery: the
    freq job's forces are compared with THAT ROW's own final optimisation forces, never with a
    threshold -- agreement is what makes a row's n_imag a verdict rather than a number.
    """
    hits = re.findall(r"Cartesian Forces:\s+Max\s+([0-9.]+)\s+RMS\s+([0-9.]+)", text or "")
    if not hits:
        return None
    return {"max_hartree_per_bohr": float(hits[-1][0]), "rms_hartree_per_bohr": float(hits[-1][1]),
            "n_records": len(hits)}


def parse_point_group(text):
    """Last `Full point group  <PG>` G16 detected. None when absent. [§39.103] the primary
    symmetry-trap diagnostic for stored P5 geometries (C2V/CS rows vs C1)."""
    hits = re.findall(r"Full point group\s+(\S+)", text or "")
    return hits[-1] if hits else None


def parse_zpe_and_thermal(text):
    """Hartree. {"zpe", "thermal_enthalpy_corr", "thermal_free_energy_corr"} or None each."""
    def _last(pat):
        h = re.findall(pat, text or "")
        return float(h[-1]) if h else None
    return {"zpe_hartree": _last(r"Zero-point correction=\s*(-?\d+\.\d+)"),
            "thermal_enthalpy_corr_hartree": _last(r"Thermal correction to Enthalpy=\s*(-?\d+\.\d+)"),
            "thermal_free_energy_corr_hartree": _last(r"Thermal correction to Gibbs Free Energy=\s*(-?\d+\.\d+)")}


def parse_free_energy(text):
    """Gibbs 자유에너지 (**Hartree**). freq 를 돌린 로그에만 있다.

    Gaussian 출력:
        `Sum of electronic and thermal Free Energies=          -341.498512`

    🔴 단위를 이름에 박는다. 이 프로젝트에서 eV / Hartree / kcal 혼용이 최대
    버그 원인이고, 자유에너지는 특히 kcal·mol⁻¹ 로 적힌 표와 섞이기 쉽다.
    없으면 **None** — 0.0 을 돌려주면 ΔG 가 조용히 거대해진다.
    """
    if not text:
        return None
    hits = re.findall(
        r"Sum of electronic and thermal Free Energies=\s*(-?\d+\.\d+)", text)
    return float(hits[-1]) if hits else None
