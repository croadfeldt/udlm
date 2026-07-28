#!/usr/bin/env python3
"""Spec-completeness scoreboard (maintainer ruling 2026-07-27): every spec ships with a Use Case,
a worked example, and a flow. This reports coverage of those three for each resource-type spec and
Class artifact, so the gap is visible every CI run and at signoff.

Heuristic linkage (see LIMITATION): a spec is matched to its UC / example / flow by its
`resource_type` name appearing in `use-cases/**`, in a `registry/instances/**` record (a worked
instance), and in `docs/flows/**` respectively. This is a *signal*, not a structural link — a spec
declares none of these today. A precise, blocking gate needs that link (a `coverage:` block on the
spec, or a manifest); until then this runs as a **report** (exit 0), and the review sweep
(CONTRIBUTING.md) carries the enforcement.

  spec_coverage.py            print the scoreboard (report; exit 0)
  spec_coverage.py --strict   exit 1 if any spec lacks all three (for a future hard gate)
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load(p):
    t = open(p, encoding="utf-8").read()
    return (yaml.safe_load(t) if p.endswith((".yaml", ".yml")) else __import__("json").loads(t)) or {}


def specs():
    """(kind, resource_type, path) for every resource-type spec and Class artifact."""
    out = []
    for p in glob.glob(os.path.join(ROOT, "registry", "resource-types", "**", "*"), recursive=True):
        if p.endswith((".json", ".yaml", ".yml")):
            d = load(p)
            if d.get("resource_type") and "record_type" not in d:
                out.append(("type", d["resource_type"], p))
    for p in glob.glob(os.path.join(ROOT, "registry", "classes", "*.yaml")):
        d = load(p)
        if d.get("record_type") == "class":
            out.append(("class", d["resource_type"], p))
    return sorted(set(out))


def _corpus_text(subdir):
    blob = []
    for p in glob.glob(os.path.join(ROOT, subdir, "**", "*"), recursive=True):
        if p.endswith((".yaml", ".yml", ".json", ".md")):
            blob.append((p, open(p, encoding="utf-8").read()))
    return blob


def main():
    strict = "--strict" in sys.argv
    UC = _corpus_text("use-cases")
    EX = _corpus_text(os.path.join("registry", "instances")) + _corpus_text(os.path.join("registry", "classes"))
    FL = _corpus_text("docs/flows")
    rows, gaps = [], 0
    print(f"{'spec':42} UC  example  flow")
    for kind, rt, path in specs():
        # match on the full dotted name and its last segment (Compute.VM / VM), word-bounded
        pats = [re.escape(rt)]
        if "." in rt:
            pats.append(r"\b" + re.escape(rt.split(".")[-1]) + r"\b")
        rx = re.compile("|".join(pats))
        has_uc = any(rx.search(t) for _, t in UC)
        has_ex = kind == "class" or any(rx.search(t) for _, t in EX)   # a Class artifact is its own worked example
        has_fl = any(rx.search(t) for _, t in FL)
        if not (has_uc and has_ex and has_fl):
            gaps += 1
        rows.append((rt, has_uc, has_ex, has_fl))
        print(f"{rt:42} {'✓' if has_uc else '·'}    {'✓' if has_ex else '·'}      {'✓' if has_fl else '·'}")
    covered = sum(1 for _, u, e, f in rows if u and e and f)
    print(f"\n{covered}/{len(rows)} spec(s) fully covered (UC + example + flow); {gaps} with a gap.")
    print("(report — heuristic name-match; the review sweep enforces, a structural coverage link makes it a hard gate)")
    return 1 if (strict and gaps) else 0


if __name__ == "__main__":
    sys.exit(main())
