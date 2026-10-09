"""Integrity audit for `executions.jsonl`, the ONLY per-task telemetry channel.

Why this module exists (03_COMPUTE_PLAN R31.2a / R31.2b / R31.2d / R36.3):

  `executions.jsonl` is appended to with `>>` from every array task, on every host. It is the
  single source for the production-shape availability fraction `f` (5-month condition (ii)) once
  R31.2a's `host`/`cores` fields land. `started.json` is NOT -- it is a fixed path written with
  `>`, so concurrent array tasks on different hosts erase each other.

  The append is atomic on this site's Lustre *because the file stays inside the first PFL extent*
  (0-4 MB => stripe_count 1 => single OST). That is a property of the file's SIZE, not of the
  directory, and R36.3 records that the original pre-registered trigger ("IF stripe_count > 1")
  was written against a variable this filesystem does not have in that form.

  Rewritten trigger (R36.3), which this module evaluates ON EVERY COLLECT:

      IF the log file approaches 4 MB (nearing the first PFL extent boundary)
      OR any line fails to parse as JSON
      THEN switch host-recording to per-task files (starts/task_${TID}.json,
           probe_throughput.sh's already-used pattern) for ALL subsequent array submissions.

  A single malformed line is sufficient. There is no severity threshold and no judgement call at
  trigger time -- that was fixed in advance, on purpose (R31.2d).

FAILURE DIRECTION (Rule 18 -- decided before the code was written):
  When the log is absent or unreadable, `fallback_trigger_fired` is **None**, never False.
  `False` reads downstream as "checked, and fine". `None` reads as "not checked". A gate that
  falls toward PASS is worse than no gate, and `exceeds_tripwire: None` is the precedent.

🔴 DO NOT route this file through `collect._read()`. That helper truncates at 4,000,000 bytes,
   which is *below* the 4 MiB boundary this module exists to watch: it would silently cut the log
   at the exact size where the answer starts to matter, and `_read_jsonl` would then discard the
   resulting partial last line without a word. This module does its own unbounded, streaming I/O.
"""

import json
import os

#: Lustre PFL first extent on this site (R36.3). Below this the file lives on ONE OST and
#: concurrent O_APPEND of a short line is atomic. Above it the file is striped and the
#: append-atomicity guarantee we are relying on is no longer established.
PFL_FIRST_EXTENT_BYTES = 4 * 1024 * 1024  # 4 MiB

#: 🔴 DECIDED BY CODER, NOT BY THE SPEC. R36.3 says "approaches 4 MB" and gives no number.
#: 0.75 is a declared choice, not a measurement. It is reported in the audit output
#: (`size_trigger_bytes`) so a reader can see the threshold that produced the verdict rather
#: than having to find it in the source.
SIZE_TRIGGER_FRACTION = 0.75

#: At most this many unparseable line numbers are listed. The COUNT is always exact -- the list
#: is capped only so a pathological log cannot balloon the reply JSON.
MAX_REPORTED_BAD_LINES = 20

#: The pre-registered remedy. Kept as text next to the trigger so the two cannot drift apart.
FALLBACK_REMEDY = (
    "switch host-recording to per-task files (starts/task_${TID}.json, the pattern "
    "probe_throughput.sh already uses) for ALL subsequent array submissions"
)


def size_trigger_bytes():
    return int(PFL_FIRST_EXTENT_BYTES * SIZE_TRIGGER_FRACTION)


def _blank(path, reason):
    """Everything unknown. 🔴 Note `fallback_trigger_fired: None` -- see the module docstring."""
    return {
        "path": path,
        "exists": False,
        "unreadable_reason": reason,
        "size_bytes": None,
        "pfl_first_extent_bytes": PFL_FIRST_EXTENT_BYTES,
        "size_trigger_bytes": size_trigger_bytes(),
        "lines_total": None,
        "lines_parsed": None,
        "unparseable_count": None,
        "unparseable_line_numbers": None,
        "observed_run_lines": None,
        "expected_run_lines": None,
        "line_count_matches": None,
        "hosts": None,
        "n_distinct_hosts": None,
        "runs_missing_host_field": None,
        "runs_missing_cores_field": None,
        "fallback_trigger_fired": None,
        "fallback_trigger_reasons": None,
        "fallback_remedy": FALLBACK_REMEDY,
        "warnings": [],
    }


def audit(path, expected_run_lines=None):
    """Audit one `executions.jsonl`.

    `expected_run_lines` is the number of "run" appends the submitter expects (one per array
    task). Pass it ONLY from a caller that knows the array size exactly. When it is None the
    result carries `line_count_matches: None` -- "not checked", not "fine".
    🔴 Do not feed this a species count or any other near-miss proxy. R31.2d's check establishes
    "every task that started left a line"; a proxy establishes something else with the same name,
    which is Rule 20 and this project has paid for it twice.
    """
    if not os.path.isfile(path):
        return _blank(path, "file does not exist")
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        return _blank(path, "stat failed: %s" % exc)

    lines_total = 0
    parsed = []
    bad_lines = []
    try:
        # Unbounded, streaming. See the module docstring for why `collect._read` is not used.
        with open(path, "r", errors="replace") as fh:
            for idx, raw in enumerate(fh, start=1):
                stripped = raw.strip()
                if not stripped:
                    continue
                lines_total += 1
                try:
                    parsed.append(json.loads(stripped))
                except ValueError:
                    bad_lines.append(idx)
    except OSError as exc:
        return _blank(path, "read failed: %s" % exc)

    runs = [r for r in parsed if isinstance(r, dict) and r.get("action") == "run"]
    hosts = sorted(set(r["host"] for r in runs
                       if isinstance(r.get("host"), str) and r["host"]))
    missing_host = sum(1 for r in runs if not r.get("host"))
    missing_cores = sum(1 for r in runs if r.get("cores") is None)

    line_count_matches = None
    if expected_run_lines is not None:
        line_count_matches = (len(runs) == int(expected_run_lines))

    reasons = []
    if size >= size_trigger_bytes():
        reasons.append(
            "executions.jsonl is %d bytes, at or past %d (%.0f%% of the %d-byte Lustre PFL first "
            "extent). Past the extent boundary the file is striped across OSTs and the "
            "append-atomicity this telemetry depends on is no longer established."
            % (size, size_trigger_bytes(), SIZE_TRIGGER_FRACTION * 100, PFL_FIRST_EXTENT_BYTES))
    if bad_lines:
        reasons.append(
            "%d line(s) of executions.jsonl do not parse as JSON (first at line %d). One "
            "malformed line is sufficient to fire this trigger -- no severity threshold, "
            "pre-registered in R31.2d." % (len(bad_lines), bad_lines[0]))
    if line_count_matches is False:
        reasons.append(
            "executions.jsonl carries %d 'run' append(s) but %d task(s) were expected. A missing "
            "line means a task's telemetry was lost, which is the concurrency failure this check "
            "exists to detect." % (len(runs), int(expected_run_lines)))

    fired = bool(reasons)
    warnings = []
    if fired:
        # Rule 13: a judgement-triggering value must reach the final artefact AND warnings[].
        # The field is read by code; warnings[] is read by a human. Both are required.
        warnings.append(
            "🔴 execlog_fallback_trigger FIRED -- %s ⟹ pre-registered remedy: %s."
            % (" | ".join(reasons), FALLBACK_REMEDY))
    if runs and missing_host:
        warnings.append(
            "🔴 %d of %d 'run' appends carry no `host` field. Either the job ran a payload built "
            "before R31.2a, or hostname(1) failed on those nodes. The availability fraction f "
            "cannot be computed from a log with missing hosts -- do not average over what is "
            "there." % (missing_host, len(runs)))

    return {
        "path": path,
        "exists": True,
        "unreadable_reason": None,
        "size_bytes": size,
        "pfl_first_extent_bytes": PFL_FIRST_EXTENT_BYTES,
        "size_trigger_bytes": size_trigger_bytes(),
        "lines_total": lines_total,
        "lines_parsed": len(parsed),
        "unparseable_count": len(bad_lines),
        "unparseable_line_numbers": bad_lines[:MAX_REPORTED_BAD_LINES],
        "observed_run_lines": len(runs),
        "expected_run_lines": (None if expected_run_lines is None
                               else int(expected_run_lines)),
        "line_count_matches": line_count_matches,
        "hosts": hosts,
        "n_distinct_hosts": len(hosts) if runs else None,
        "runs_missing_host_field": missing_host,
        "runs_missing_cores_field": missing_cores,
        "fallback_trigger_fired": fired,
        "fallback_trigger_reasons": reasons,
        "fallback_remedy": FALLBACK_REMEDY,
        "warnings": warnings,
    }
