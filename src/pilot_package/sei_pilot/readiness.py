"""The THREE-ROW availability check, applied to every external code without exception.

    row 1   binary          the executable exists and is executable
    row 2   data_library    the code's data / parameter / pseudopotential library is present
    row 3   launch_smoke    a minimal job actually RAN TO COMPLETION on a COMPUTE NODE

🔴 WHY ALL THREE, AND WHY ROW 3 IS NOT OPTIONAL.
   This project has twice shipped a name it had never loaded.
     · `software.g16` was empty and all nine items were planned anyway, because availability had
       been inferred from a string in a `module avail` listing (Rule 20, 05_STATE).
     · `vasp_std 6.4.3 present at /home01/q656a01/local/bin/vasp_std` sat inside a block headed
       "settled [MEASURED] -- do not re-run these", hours after we established that PRESENT is not
       CAN COMPUTE (ADR-073/074, Rule 28).
   `command -v g16` proves a name is on PATH. A wrapper script, an expired licence, a broken Linda
   install and a binary built for the wrong ISA all pass row 1 and fail row 3.
   🔴 So `ready` is NEVER True on rows 1 and 2 alone. It is `None` -- not checked.

🔴 AND WHY ROW 2 EXISTS SEPARATELY.
   We wrote the data-library row for CP2K (`$CP2K_DATA_DIR`, U-46) as a COMMENT in `sysprobe.py`,
   never implemented it, and never carried it to VASP at all -- where the equivalent is the POTCAR
   library, and where nobody had looked. A code whose binary runs and whose basis/pseudopotential
   library is absent fails at the first real job, after the queue wait.

FAILURE DIRECTION (Rule 18): every row is True / False / None, and `None` means NOT CHECKED.
`False` means checked and negative. They are never interchanged, and `ready` degrades to `None`
the moment any row is unchecked -- a readiness verdict that falls toward READY is worse than no
verdict, because it manufactures confidence about a code nobody ran.
"""

import os

from . import config

ROW_BINARY = "binary"
ROW_DATA = "data_library"
ROW_SMOKE = "launch_smoke"
ROWS = (ROW_BINARY, ROW_DATA, ROW_SMOKE)

#: What each row does and does not establish. Rule 20: state the PROPERTY a check establishes,
#: not the NAME of the thing it ran on.
ROW_SEMANTICS = {
    ROW_BINARY: {
        "establishes": "an executable file of this name is resolvable and has the execute bit",
        "does_not_establish": (
            "that it runs, that it is licensed, that it was built for this ISA, or that it is "
            "the code rather than a wrapper. `command -v` is a PROXY and has already been read "
            "as a measurement twice."),
    },
    ROW_DATA: {
        "establishes": "the code's data / parameter / pseudopotential library is present and "
                       "contains the entries this project needs",
        "does_not_establish": "that the entries are the RIGHT variant, unless the variant was "
                              "checked by name (e.g. Li_sv, not merely 'a Li POTCAR')",
    },
    ROW_SMOKE: {
        "establishes": "this code produced a parseable result on a COMPUTE NODE (ADR-041), "
                       "which is the only row that establishes CAN COMPUTE",
        "does_not_establish": "🔴 WHAT IT COSTS. Availability and cost are separate questions and "
                              "conflating them is on the record in both directions -- 'binary "
                              "present therefore cost known' (R35.9) and 'runs therefore cost "
                              "known' (R36.6).",
    },
}


def requirements(cfg=None):
    """The per-engine requirement table from `config/env_paths.json`. Single source."""
    cfg = cfg if cfg is not None else config.load("env_paths.json")
    return (cfg or {}).get("engine_requirements") or {}


def row(name, ok, evidence=None, note=None):
    """Build one row. `ok` must be True, False or None -- nothing else is accepted.

    🔴 A truthy-but-not-True value (0, "", "no") would be silently coerced by a caller and this is
    exactly the class of value ADR-036 is about. Refuse it loudly instead.
    """
    if ok is not True and ok is not False and ok is not None:
        raise ValueError("row %r: ok must be True/False/None, got %r. `null` means NOT CHECKED "
                         "and `False` means CHECKED AND NEGATIVE; they are different answers "
                         "(ADR-036)." % (name, ok))
    sem = ROW_SEMANTICS.get(name, {})
    return {
        "row": name,
        "checked": ok is not None,
        "ok": ok,
        "evidence": evidence,
        "note": note,
        "establishes": sem.get("establishes"),
        "does_not_establish": sem.get("does_not_establish"),
    }


def check_binary(path_or_none):
    """Row 1 from a resolved path. `None` in means NOT PROBED, not 'absent'."""
    if path_or_none is None:
        return row(ROW_BINARY, None, note="not probed")
    ok = bool(path_or_none) and os.path.isfile(path_or_none) and os.access(path_or_none, os.X_OK)
    return row(ROW_BINARY, ok, evidence={"path": path_or_none})


def check_data_library(spec, root=None, env=None):
    """Row 2 against one engine's `data_library` spec from `env_paths.json`.

    Resolution order: every named env var, then a literal `path`. Required entries are looked for
    BY NAME -- "the directory exists" is not the property (a POTCAR tree missing Li_sv passes a
    directory test and fails the first job).
    """
    if not spec:
        return row(ROW_DATA, None, note="no data-library requirement declared for this engine")
    env = os.environ if env is None else env
    tried = []
    base = None
    for var in spec.get("env_vars") or []:
        val = env.get(var)
        tried.append({"env_var": var, "value": val})
        if val and os.path.isdir(val):
            base = val
            break
    if base is None and spec.get("path"):
        tried.append({"path": spec["path"]})
        if os.path.isdir(spec["path"]):
            base = spec["path"]

    # Package-relative files (our own `gen` basis decks) are a separate, independently-missable
    # half of "the data this code needs".
    pkg_missing = []
    if root:
        for rel in spec.get("also_required_files") or []:
            if not os.path.isfile(os.path.join(root, rel)):
                pkg_missing.append(rel)

    if base is None:
        if not (spec.get("env_vars") or spec.get("path")):
            return row(ROW_DATA, None, evidence={"tried": tried},
                       note="requirement declares no location to look in")
        return row(ROW_DATA, False, evidence={"tried": tried, "resolved": None},
                   note="the data/parameter library was not found at any declared location")

    wanted = list(spec.get("required_files") or []) + list(spec.get("required_elements") or [])
    try:
        present = set(os.listdir(base))
    except OSError as exc:
        return row(ROW_DATA, False, evidence={"resolved": base, "error": str(exc)})
    missing = [w for w in wanted
               if w not in present and not os.path.exists(os.path.join(base, w))]
    ok = not missing and not pkg_missing
    return row(ROW_DATA, ok,
               evidence={"tried": tried, "resolved": base, "required": wanted,
                         "missing": missing, "package_files_missing": pkg_missing})


def check_launch_smoke(result):
    """Row 3. `result` is the smoke outcome, or `None` when the smoke was never run.

    Accepts a dict with `ran_on_compute_node` and `parsed_result`. 🔴 A smoke that ran on the
    LOGIN node does not satisfy this row (ADR-041): the login node has different hardware and a
    different module environment, and `24` was once read as the cluster's core count because of
    exactly that.
    """
    if result is None:
        return row(ROW_SMOKE, None, note="not run")
    r = result or {}
    if r.get("ran_on_compute_node") is not True:
        return row(ROW_SMOKE, False, evidence=r,
                   note="🔴 the smoke did not run on a compute node -- a login-node result does "
                        "not establish that the code runs where the work runs (ADR-041)")
    return row(ROW_SMOKE, bool(r.get("parsed_result") is True), evidence=r)


def evaluate(engine, binary_path=None, smoke=None, root=None, env=None, cfg=None):
    """All three rows for one engine. Returns the readiness record that goes in the reply."""
    spec = requirements(cfg).get(engine) or {}
    rows = [
        check_binary(binary_path),
        check_data_library(spec.get("data_library"), root=root, env=env),
        check_launch_smoke(smoke),
    ]
    by_name = dict((r["row"], r) for r in rows)
    unchecked = [r["row"] for r in rows if r["ok"] is None]
    negative = [r["row"] for r in rows if r["ok"] is False]

    if negative:
        ready = False
    elif unchecked:
        # 🔴 Rows 1 and 2 passing does NOT make an engine ready. This is the line that would have
        #    stopped `vasp_std present` from being recorded as settled.
        ready = None
    else:
        ready = True

    out = {
        "engine": engine,
        "rows": rows,
        "ready": ready,
        "rows_unchecked": unchecked,
        "rows_negative": negative,
        "requirement_source": "config/env_paths.json :: engine_requirements",
        "warnings": [],
    }
    if ready is None:
        out["warnings"].append(
            "🔴 readiness_unknown for %s: row(s) %s were NOT CHECKED, so this engine is not "
            "established as usable. 🔴 Rows binary+data_library passing is NOT readiness -- "
            "PRESENT != CAN COMPUTE (ADR-073/074). Do not plan work against this engine on the "
            "strength of a name in a list." % (engine, ", ".join(unchecked)))
    if ready is False:
        out["warnings"].append(
            "🔴 readiness_failed for %s: row(s) %s came back negative. %s"
            % (engine, ", ".join(negative),
               "; ".join(filter(None, (by_name[n].get("note") for n in negative)))))
    return out


def availability_does_not_imply_cost(engine):
    """The sentence that has to travel with every readiness verdict.

    🔒 Kept as a function so it cannot be paraphrased into something weaker at a call site. The
    conflation has been made in BOTH directions on the record: "binary present therefore cost
    known" (R35.9) and "the user runs VASP often therefore cost known" (R36.6).
    """
    return ("readiness for %s answers CAN IT RUN. It does not answer WHAT IT COSTS. No VASP "
            "core-h has ever been measured on this cluster (U-69) and no readiness row can "
            "change that." % engine)
