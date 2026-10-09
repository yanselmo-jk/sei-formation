"""HOMO/SOMO parsing — the diagnostic that is now load-bearing for the whole B0 batch.

Since the bound-species check was broadened to EVERY species (23/23), a species whose highest
occupied orbital energy cannot be read is held OUT of the u_cheap statistics. ⟹ **this parser
decides the sample size**, and a silent failure here shrinks every downstream number without
saying so.

🔴 THE TWO HALVES OF THIS MODULE HAVE DIFFERENT EVIDENCE. Do not read one caveat over both.

```
FREQUENCIES   🟢 [MEASURED-PROVENANCE]. `frequencies()` DELEGATES to
              `criteria.g16.parse_frequencies`, which parsed a REAL Gaussian 16 log on the
              cluster (RT-1 round 1, pilots[0].g16["ts_qst2.log"]): route line, charge/
              multiplicity, SCF block, opt block, timings and n_frequencies = 27 all came back
              coherent, with imag_freq_count 1 at -105.0 cm^-1.
ORBITALS      🔴 [UNVERIFIED]. `RE_EIGEN` below is written from the documented format and has
              NEVER been run against a real log. G16 is not installed on this machine and the
              RAW LOGS WERE NOT RETURNED -- only the parsed JSON.
```
⚠ An over-broad warning gets ignored, and then the real one goes with it. The `[UNVERIFIED]`
   applies to the EIGENVALUE BLOCK ONLY.

🔴 AND THE LOG THAT WOULD HAVE CLOSED IT EXISTED. That RT-1 run was **multiplicity 2** -- a UKS
   calculation, whose log carries `Alpha  occ. eigenvalues` AND `Beta  occ. eigenvalues` blocks.
   That is precisely the alpha/beta branch of `highest_occupied()`, the riskiest thing in this
   file. **The log that would have validated the hardest case was produced and discarded.**

🔴 THIS IS THE EXACT SHAPE OF ROUND TRIP #1's FAILURE: an ORCA parser was applied to Gaussian
   logs, produced plausible output, and nobody could tell. The defence is not confidence in the
   patterns -- it is that this module can say **"I matched nothing"** and distinguish it from
   **"there were no orbitals"**.

```
    parser matched some lines, no HOMO extractable   -> a DATA problem
    parser matched NO lines at all                   -> 🔴 a PARSER problem, and it says so
```
`format_validation()` exists to be run on the first real G16 log, and `parse()` reports
`format_recognised` on every call so the distinction reaches the artefact rather than a log file.

UNITS: Gaussian prints orbital eigenvalues in **Hartree**. Converted to eV only through `units`.
"""

import re

from . import units
from .criteria import g16

#: 🔴 [UNVERIFIED — documented Gaussian 16 output format, never run against a real log here.]
#: Expected shape:
#:     `Alpha  occ. eigenvalues --  -19.12345 -10.23456   -1.02938`
#:     `Alpha virt. eigenvalues --    0.12345   0.23456`
#: and for an open shell the same with `Beta`.
RE_EIGEN = re.compile(
    r"^\s*(Alpha|Beta)\s+(occ\.|virt\.)\s+eigenvalues\s*--\s*(.+)$")

#: What a matched line looks like, carried in the output so a reader can compare it against a real
#: log without opening the source.
EXPECTED_LINE_SHAPE = "Alpha  occ. eigenvalues --  -19.12345 -10.23456   -1.02938"

#: 🔴 SCOPE: THE EIGENVALUE BLOCK ONLY. The frequency half is separately evidenced -- see
#: FREQUENCY_FORMAT_STATUS.
FORMAT_STATUS = ("[UNVERIFIED] documented G16 eigenvalue-block format; G16 is not installed on "
                 "the development box, the RT-1 raw logs were not returned, and this pattern has "
                 "never seen a real log. Round trip #1 died on an ORCA parser applied to Gaussian "
                 "logs, so `format_recognised` is reported on every call and a parser failure is "
                 "never reported as a data failure. 🔴 Applies to ORBITALS ONLY.")

#: 🟢 The other half, and it is NOT unverified.
FREQUENCY_FORMAT_STATUS = (
    "[MEASURED-PROVENANCE] criteria.g16.parse_frequencies parsed a real Gaussian 16 log on the "
    "cluster (RT-1 round 1, pilots[0].g16['ts_qst2.log']: n_frequencies 27, imag_freq_count 1 at "
    "-105.0 cm^-1, alongside a coherent route/SCF/opt/timings parse). `frequencies()` delegates "
    "to it and inherits that provenance.")


def parse(text):
    """Orbital eigenvalues from a G16 log. Returns Hartree.

    🔴 `format_recognised` is False when NO eigenvalue line matched at all. That is a PARSER
       problem, not a chemistry problem, and the two have opposite prescriptions.
    🔴 Only the LAST block is used: a log may contain several (opt steps, then the final freq
       job), and mixing them would interleave orbitals from different geometries.
    """
    out = {
        "alpha_occ_hartree": [],
        "alpha_virt_hartree": [],
        "beta_occ_hartree": [],
        "beta_virt_hartree": [],
        "n_lines_matched": 0,
        "format_recognised": False,
        "format_status": FORMAT_STATUS,
        "expected_line_shape": EXPECTED_LINE_SHAPE,
        "warnings": [],
    }
    if not text:
        out["warnings"].append(
            "🔴 orbital_parse_no_input: empty log. `format_recognised` is False because nothing "
            "was examined -- this is NOT evidence that the format is wrong.")
        return out

    blocks, cur, in_block = [], {}, False
    for line in text.splitlines():
        m = RE_EIGEN.match(line)
        if m:
            out["n_lines_matched"] += 1
            if not in_block:
                cur, in_block = {}, True
            key = "%s_%s" % (m.group(1).lower(),
                             "occ" if m.group(2).startswith("occ") else "virt")
            vals = []
            for tok in m.group(3).split():
                try:
                    vals.append(float(tok))
                except ValueError:
                    pass
            cur.setdefault(key, []).extend(vals)
        elif in_block:
            blocks.append(cur)
            cur, in_block = {}, False
    if in_block:
        blocks.append(cur)

    out["format_recognised"] = out["n_lines_matched"] > 0
    if not out["format_recognised"]:
        out["warnings"].append(
            "🔴 orbital_format_not_recognised: NO eigenvalue line matched in a log of %d "
            "character(s). 🔴 This is a PARSER problem, not a data problem -- do not record the "
            "species as 'no orbitals'. Expected a line shaped like %r. %s"
            % (len(text), EXPECTED_LINE_SHAPE, FORMAT_STATUS))
        return out

    last = blocks[-1] if blocks else {}
    for spin in ("alpha", "beta"):
        for kind in ("occ", "virt"):
            out["%s_%s_hartree" % (spin, kind)] = list(last.get("%s_%s" % (spin, kind)) or [])
    return out


def highest_occupied(text, multiplicity=None):
    """The HOMO and, separately, the SOMO. 🔴 THEY ARE DIFFERENT OBJECTS.

    ```
    HOMO   max(alpha_homo, beta_homo)          the highest occupied level of EITHER spin
    SOMO   alpha[n_alpha - 1]  when n_alpha > n_beta   the orbital with NO beta partner
    ```
    🔴 THIS WAS A REAL BUG, FOUND ON A REAL LOG. The earlier version returned `max(all occupied)`
       and labelled it "homo_or_somo". On RT-1's P1 log that is right BY LUCK -- the alpha HOMO
       (-0.30464) happens to sit above the beta HOMO (-0.34581). **In a strongly spin-polarised
       species the beta HOMO can sit above the alpha HOMO, and "the higher" then returns a DOUBLY
       OCCUPIED orbital and calls it the SOMO.** Both are emitted, named separately, and nothing
       is called "homo_or_somo" any more.

    🔴 OCCUPANCY COMES FROM THE `occ.`/`virt.` LABEL AND NEVER FROM THE SIGN. The same real log
       carries a NEGATIVE virtual (beta LUMO = -0.00368), so a sign-based classifier would call it
       occupied. That matters most where we are least covered: a reduced species whose SOMO can
       genuinely be positive.

    `highest_occupied_hartree` is the quantity the BOUND check consumes -- "is the highest
    occupied orbital bound?" is about the HOMO, whichever spin it belongs to.
    """
    p = parse(text)
    a_occ, b_occ = p["alpha_occ_hartree"], p["beta_occ_hartree"]
    a_homo = max(a_occ) if a_occ else None
    b_homo = max(b_occ) if b_occ else None
    occ = list(a_occ) + list(b_occ)

    out = {
        "highest_occupied_hartree": None,
        "highest_occupied_ev": None,
        "homo_hartree": None,
        "somo_hartree": None,
        "somo_definition": ("alpha[n_alpha - 1] when n_alpha > n_beta -- the orbital with no beta "
                            "partner. None for a closed shell, which HAS no SOMO."),
        "spin_resolved": {"alpha_homo_hartree": a_homo, "beta_homo_hartree": b_homo,
                          "n_alpha_occ": len(a_occ), "n_beta_occ": len(b_occ)},
        "derived_multiplicity": (len(a_occ) - len(b_occ) + 1) if (a_occ or b_occ) else None,
        "declared_multiplicity": (None if multiplicity is None else int(multiplicity)),
        "is_open_shell": (None if multiplicity is None else int(multiplicity) > 1),
        "format_recognised": p["format_recognised"],
        "n_occupied_parsed": len(occ),
        "failure_kind": None,
        "occupancy_source": ("the occ./virt. LABEL, never the sign -- a real log carries a "
                             "NEGATIVE virtual orbital"),
        "warnings": list(p["warnings"]),
    }
    if not p["format_recognised"]:
        out["failure_kind"] = "parser"
        return out
    if not occ:
        out["failure_kind"] = "data"
        out["warnings"].append(
            "🔴 orbital_no_occupied_levels: the format WAS recognised (%d line(s) matched) but no "
            "occupied eigenvalue was extracted. That is a DATA problem in this log, not a parser "
            "problem." % p["n_lines_matched"])
        return out

    out["homo_hartree"] = max(v for v in (a_homo, b_homo) if v is not None)
    out["highest_occupied_hartree"] = out["homo_hartree"]
    out["highest_occupied_ev"] = units.hartree_to_ev(out["homo_hartree"])
    out["homo_spin"] = ("alpha" if (b_homo is None or (a_homo is not None and a_homo >= b_homo))
                        else "beta")
    # 🔴 A SOMO EXISTS ONLY IF BOTH SPIN SETS ARE PRESENT.
    #    A RESTRICTED (RKS) log prints ONLY `Alpha occ.` lines and they are DOUBLY occupied --
    #    there is no Beta block at all. Testing `n_alpha > n_beta` alone then fires on every
    #    closed-shell species (n_beta = 0) and reports a SOMO for a doubly-occupied orbital.
    #    Caught by the real-log fixture work, not by review.
    out["is_unrestricted"] = bool(a_occ and b_occ)
    if not out["is_unrestricted"]:
        out["derived_multiplicity"] = 1 if a_occ else None
        out["somo_note"] = ("no Beta block -- this is a RESTRICTED calculation, every orbital is "
                            "doubly occupied and there is no SOMO")
    if out["is_unrestricted"] and len(a_occ) > len(b_occ):
        out["somo_hartree"] = a_occ[-1]
        out["somo_ev"] = units.hartree_to_ev(a_occ[-1])
        out["n_singly_occupied"] = len(a_occ) - len(b_occ)
        if out["somo_hartree"] != out["homo_hartree"]:
            out["warnings"].append(
                "🟡 homo_is_not_the_somo for this species: HOMO = %+.6f Ha (%s spin) but SOMO = "
                "%+.6f Ha. They are different orbitals and must not be substituted for one "
                "another -- the beta HOMO lying above the alpha SOMO means the highest occupied "
                "level is DOUBLY occupied."
                % (out["homo_hartree"], out["homo_spin"], out["somo_hartree"]))
    if (out["declared_multiplicity"] is not None
            and out["derived_multiplicity"] is not None
            and out["declared_multiplicity"] != out["derived_multiplicity"]):
        out["warnings"].append(
            "🔴 multiplicity_mismatch: the deck declared %d but the orbital counts imply %d "
            "(n_alpha_occ %d, n_beta_occ %d). One of them is wrong and the electronic state is "
            "not what was asked for."
            % (out["declared_multiplicity"], out["derived_multiplicity"],
               len(a_occ), len(b_occ)))
    return out


def frequencies(text):
    """The frequency list, in cm^-1.

    🔒 DELEGATES to `criteria.g16.parse_frequencies`. There is exactly ONE frequency parser in
    this package and this is not a second one -- two parsers for one format is the shape that has
    cost this project repeatedly.
    """
    return g16.parse_frequencies(text)


# =============================================================================================
# per-species parse accounting -- the sample size, made visible
# =============================================================================================

def species_record(species_id, log_text, multiplicity=None):
    """Everything B0 needs from one species' log, plus WHY anything is missing."""
    ho = highest_occupied(log_text, multiplicity)
    freqs = frequencies(log_text)
    rec = {
        "species_id": species_id,
        "highest_occupied_hartree": ho["highest_occupied_hartree"],
        "highest_occupied_ev": ho["highest_occupied_ev"],
        "homo_hartree": ho["homo_hartree"],
        "somo_hartree": ho.get("somo_hartree"),
        "derived_multiplicity": ho.get("derived_multiplicity"),
        "orbital_failure_kind": ho["failure_kind"],
        "orbital_format_recognised": ho["format_recognised"],
        "frequencies_cm1": freqs,
        "n_frequencies": len(freqs),
        "frequency_parse_ok": bool(freqs),
        "usable": ho["highest_occupied_hartree"] is not None and bool(freqs),
        "warnings": list(ho["warnings"]),
    }
    if not freqs:
        rec["warnings"].append(
            "🔴 frequency_parse_empty for %s: no `Frequencies --` line was found. The three "
            "curvature observables are UNAVAILABLE and this species cannot enter the U-55 "
            "correlation." % species_id)
    return rec


def batch_parse_summary(records):
    """🔴 THE SAMPLE SIZE, AT THE TOP LEVEL.

    The lead's instruction: *"if 6 of 23 silently drop out, u_cheap is computed on 17 and nothing
    says so."* This makes that impossible to miss, and it separates the two failure kinds because
    they have opposite prescriptions:
        `parser` failures  -> fix the parser; the data may be fine
        `data` failures    -> the run is the problem; the parser is fine
    """
    recs = list(records or [])
    usable = [r for r in recs if r.get("usable")]
    parser_fail = [r["species_id"] for r in recs if r.get("orbital_failure_kind") == "parser"]
    data_fail = [r["species_id"] for r in recs if r.get("orbital_failure_kind") == "data"]
    freq_fail = [r["species_id"] for r in recs if not r.get("frequency_parse_ok")]
    out = {
        "n_species": len(recs),
        "n_usable": len(usable),
        "n_dropped": len(recs) - len(usable),
        "dropped_orbital_parser_failure": parser_fail,
        "dropped_orbital_data_failure": data_fail,
        "dropped_frequency_parse_failure": freq_fail,
        "usable_species": [r["species_id"] for r in usable],
        "warnings": [],
        "_sample_size_note": (
            "🔴 EVERY per-species statistic downstream -- u_cheap, the convergence rate, the U-55 "
            "correlation -- is computed on `n_usable`, NOT on `n_species`. Quote the former."),
    }
    if out["n_dropped"]:
        out["warnings"].append(
            "🔴 batch_sample_reduced: %d of %d species are UNUSABLE (%s). Every downstream "
            "statistic is over %d species, not %d."
            % (out["n_dropped"], out["n_species"],
               ", ".join(sorted(set(parser_fail + data_fail + freq_fail))),
               out["n_usable"], out["n_species"]))
    if parser_fail:
        out["warnings"].append(
            "🔴🔴 orbital_PARSER_failed on %d species (%s). 🔴 THE PARSER, NOT THE DATA. The G16 "
            "orbital format is %s Fix the parser before reading anything into these species."
            % (len(parser_fail), ", ".join(parser_fail), FORMAT_STATUS))
    return out


def format_validation(log_text):
    """Run this on the FIRST real G16 log. It is the only thing that closes `[UNVERIFIED]`.

    🔒 ADR-041: the check runs at the entry point on real output, not on a fixture we wrote.
    Returns a record intended to be pasted into the reply so the format claim stops being an
    assumption for everyone afterwards.
    """
    p = parse(log_text)
    freqs = frequencies(log_text)
    return {
        "orbital_format_status": FORMAT_STATUS,
        "frequency_format_status": FREQUENCY_FORMAT_STATUS,
        "orbital_format_recognised": p["format_recognised"],
        "orbital_lines_matched": p["n_lines_matched"],
        "n_alpha_occ": len(p["alpha_occ_hartree"]),
        "n_beta_occ": len(p["beta_occ_hartree"]),
        "frequency_lines_found": len(freqs),
        # 🔴 TWO INDEPENDENT PARSERS, TWO VERDICTS. A single combined verdict said "AT LEAST ONE
        #    PARSER MATCHED NOTHING" on a fixture that is an eigenvalue block ALONE -- correct
        #    about the frequencies, misleading about the orbitals, and it would have read as a
        #    failure of the thing that had just succeeded. Same shape as C-2's indeterminate/fail.
        "orbital_verdict": ("matched" if p["format_recognised"]
                            else "🔴 MATCHED NOTHING -- parser problem"),
        "frequency_verdict": ("matched" if freqs else
                              "not exercised by this input (no `Frequencies --` lines present) "
                              "-- NOT a failure"),
        "verdict": ("orbitals: %s | frequencies: %s"
                    % ("matched" if p["format_recognised"] else "🔴 MATCHED NOTHING",
                       "matched" if freqs else "not exercised by this input")),
        "expected_line_shape": EXPECTED_LINE_SHAPE,
        "_closes": ("this is what turns FORMAT_STATUS from [UNVERIFIED] into [MEASURED], FOR THE "
                    "ORBITAL BLOCK ONLY -- the frequency half already has real-log provenance. "
                    "Until it has run on a real log, every HOMO/SOMO in this batch rests on a "
                    "pattern nobody has checked against the program that produced the file. "
                    "🔴 A UKS log (multiplicity > 1) is the one that matters: it exercises the "
                    "alpha/beta branch, and RT-1's own multiplicity-2 log would have done it."),
    }


def b0_species_panel(species_list, logs, cost_by_species=None):
    """End-to-end: logs -> HOMO/SOMO + frequencies -> bound check + curvature -> the U-55 panel.

    🔴 THE POINT OF THIS FUNCTION IS THAT THE SAMPLE SIZE SURVIVES THE WHOLE CHAIN. Each stage
    drops species for its own reason, and each reason is a different finding:
```
        parse failure (parser)  the format was not recognised -- fix the code
        parse failure (data)    the log is short of what it should contain
        unbound                 a RESULT about the species (C-10/bound rule), not a failure
        no cost recorded        the U-55 correlation cannot use it
```
    A single `n` at the end would hide all four.

    `logs` maps species_id -> log text. `cost_by_species` maps species_id ->
    {"opt_cycles": int, "core_hours": float}.
    """
    from . import bound, curvature

    parsed, enriched = [], []
    for sp in species_list or []:
        rec = species_record(sp["id"], (logs or {}).get(sp["id"]), sp.get("multiplicity"))
        parsed.append(rec)
        b = bound.classify(sp, homo_energy_hartree=rec["highest_occupied_hartree"])
        obs = curvature.observables(rec["frequencies_cm1"])
        cost = (cost_by_species or {}).get(sp["id"]) or {}
        # 🔴 `curvature` is the single source for the observables; `curvature.flatten_predictors`
        #    expands the kappa and n_soft LADDERS into predictor columns. Copying individual
        #    fields here would be a second, drifting copy of the same numbers -- and it was: this
        #    block held `n_soft` and `hessian_condition_number` as scalars and broke the moment
        #    those became ladders.
        entry = {
            "species_id": sp["id"],
            "stratum": sp.get("stratum"),
            "converged": cost.get("converged"),
            "bound": b,
            "opt_cycles": cost.get("opt_cycles"),
            "core_hours": cost.get("core_hours"),
            "parse": rec,
            "curvature": obs,
            "imaginary_mode": curvature.imaginary_mode_verdict(
                obs, expected_minimum=True, species_id=sp["id"]),
        }
        entry.update(curvature.flatten_predictors(entry))
        enriched.append(entry)

    imag_unexpected = [e["species_id"] for e in enriched
                       if (e["imaginary_mode"] or {}).get("verdict") == "unexpected"]
    parse_summary = batch_parse_summary(parsed)
    partition = bound.partition(enriched)
    panel = curvature.u55_panel(enriched)
    out = {
        "parse": parse_summary,
        "bound_partition": partition,
        "u55": panel,
        "species": enriched,
        "sample_sizes": {
            "n_species_requested": len(species_list or []),
            "n_parsed_usable": parse_summary["n_usable"],
            "n_in_u_cheap_statistics": len(partition["in_u_cheap_statistics"]),
            "n_in_u55_correlation": panel["n_species_complete"],
        },
        "imaginary_mode_on_supposed_minima": imag_unexpected,
        "warnings": [],
        "_read_the_sample_sizes": (
            "🔴 FOUR DIFFERENT DENOMINATORS, and they are not interchangeable. A statistic quoted "
            "against `n_species_requested` when it was computed over `n_in_u55_correlation` is "
            "the 'n_frames is not the sample size' error with more steps."),
    }
    for block in (parse_summary, partition, panel):
        out["warnings"].extend(block.get("warnings") or [])
    if imag_unexpected:
        out["warnings"].append(
            "🔴 imaginary_mode_on_supposed_minima: %s. B0-D's species are supposed to be MINIMA. "
            "🔴 A structure stuck on a SYMMETRY ELEMENT is generally a saddle and a GFN2 "
            "optimisation does not leave the element -- check each one's `symmetry_trace` before "
            "reading the frequency as chemistry." % ", ".join(imag_unexpected))
    sizes = out["sample_sizes"]
    if len(set(sizes.values())) > 1:
        out["warnings"].append(
            "🔴 sample_sizes_differ across the chain: requested %d, parsed usable %d, in u_cheap "
            "%d, in the U-55 correlation %d. Each drop has its own reason above -- quote the "
            "denominator that belongs to the number you are quoting."
            % (sizes["n_species_requested"], sizes["n_parsed_usable"],
               sizes["n_in_u_cheap_statistics"], sizes["n_in_u55_correlation"]))
    return out
