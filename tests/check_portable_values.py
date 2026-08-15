#!/usr/bin/env python3
"""Portable-value discipline — a selectable value is not a free string (PVD-001).

ADR-037 has said since it was written that this check was *planned*, and two documents cite
`tests/check_portable_values.py` as though it existed. It did not, which is why ADR-037 was one of
four records still unrealized after the corpus audit.

**The rule.** A value chosen from a SET — provider-advertised, standardized, or
requirement-satisfiable — must be one of three things: a `data_reference` to a governed vocabulary,
a bounded codelist (`enum`, or an adopted-standard codelist), or a requirements descriptor a
provider matches. An unconstrained string for such a value is non-conformant, because two estates'
free strings are incomparable by construction — which is the same reason a governed term denotes a
floor rather than a label (ADR-036).

**It scans the CLASS surface, not the generated specs**, and that is load-bearing. A class element
declaring `values.reference_data_type` is conformant — it names a governed vocabulary — while its
`schema.type` is still `string`, because the string is the SHAPE and `values` is the GOVERNANCE.
The generated flat spec keeps the shape and drops the governance, so scanning it would report every
governed field as a violation and miss the distinction entirely.

  PVD-001  a class element is a bare string with no `enum`, no `$ref`, and no
           `values.reference_data_type`, and its name is not one the rule puts out of scope.

**Out of scope, per ADR-037.** Human names, descriptions and handles; opaque provider-reported ids;
values already constrained to an adopted format (FQDN, CIDR, RFC 3339, PURL, CWE). These are matched
by name, which is a heuristic and says so — it is why the baseline below is a TRIAGE list rather
than an exemption list.

**Ratchet.** The 62 existing candidates are baselined and reported; a new one fails. That is
ADR-037's own staging — it says PVD-001 hard-fails and PVD-002 runs as a review flag "until its
overlap catalogue is tuned" — and a gate that failed 62 pre-existing fields on day one would be
turned off rather than fixed.

**PVD-002 is not implemented here.** Detecting that a field restates an adopted standard's body
inline needs the overlap catalogue ADR-037 defers; claiming to check it would be worse than saying
so. It remains a review-sweep item.

Exit 0 = no NEW free-string selectable value.
"""
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "tests", "portable-values-baseline.yaml")

# Names the rule puts out of scope: free by nature, or already constrained by an adopted format.
# A heuristic, and the reason findings are triaged rather than trusted.
FREE = re.compile(
    r"(^|_)(name|handle|description|definition|display_name|notes?|reason|comment|label|title|"
    r"summary|text|uuid|id|version|hash|digest|url|uri|endpoint|path|email|address|serial_number|"
    r"wwn|mac|fqdn|hostname|cidr|subnet|prefix|schema_version|dn|realm|mountpoint|purl|cwe|"
    r"registry|repository|tag|criterion|jitter|timeout|time|from|at|by|to)($|_)")


def candidates():
    """Every class element that is a bare string with no governance."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "registry", "classes", "**", "*.yaml"),
                              recursive=True)):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        except Exception:
            continue
        if d.get("record_type") != "class":
            continue
        for e in d.get("elements") or []:
            name, sch = e.get("element", ""), e.get("schema") or {}
            if (e.get("values") or {}).get("reference_data_type"):
                continue                 # a governed vocabulary — the conformant form
            blob = json.dumps(sch)
            if "enum" in blob or "$ref" in blob:
                continue                 # a codelist, or a shape bound by reference
            if sch.get("type") != "string":
                continue
            if FREE.search(name):
                continue
            out.append((d["resource_type"], name))
    return out


def main():
    found = candidates()
    baseline = yaml.safe_load(open(BASELINE, encoding="utf-8")) if os.path.exists(BASELINE) else {}
    known = {(v["resource_type"], v["element"]) for v in (baseline or {}).get("known", [])}

    new = [c for c in found if c not in known]
    stale = sorted(known - set(found))

    # Self-test: the arms must discriminate, or a clean run proves only that the YAML parsed.
    st = []
    if FREE.search("partition_mechanism"):
        st.append("PVD-SELF a selectable value is being read as out-of-scope — the arm would never "
                  "fire on the fields this rule exists for")
    if not FREE.search("display_name"):
        st.append("PVD-SELF a human name is not recognised as free, so every record would be "
                  "flagged and the gate would be turned off")
    if not found:
        st.append("PVD-SELF nothing scanned — the class surface is not being read")

    print(f"portable values: {len(found)} bare-string selectable value(s) on the class surface "
          f"({len(known)} baselined, {len(new)} new)")
    for m in st:
        print(f"  FAIL [{m}")
    for rt, n in new:
        print(f"  ✗ PVD-001 {rt}.{n} is an unconstrained string for a selectable value. Make it a "
              f"`values.reference_data_type` (governed vocabulary), an `enum` (codelist), or a "
              f"requirements descriptor — two estates' free strings are incomparable")
    if stale:
        print(f"\n  {len(stale)} baselined entr(y/ies) no longer present — remove from "
              f"{os.path.relpath(BASELINE, ROOT)}:")
        for rt, n in stale[:10]:
            print(f"    - {rt}.{n}")
    if new or st:
        return 1
    print("OK — no new free-string selectable value")
    return 0


if __name__ == "__main__":
    sys.exit(main())
