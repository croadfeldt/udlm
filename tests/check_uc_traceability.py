#!/usr/bin/env python3
"""UC traceability gate — a flow's `UC source:` and the release register's handle column must name a
real corpus use case.

Three registers describe the same use cases and had drifted completely apart:

  registry/UDLM-0.1-SCOPE.md   the 21 RELEASE-scope use cases (the committed 0.1 surface)
  docs/flows/uc-NN-*.md        one rendered flow per release UC, each ending `UC source: <handle>`
  use-cases/**/*.yaml          the CORPUS — 149 authored scenarios, the authoritative records

The corpus is the broader register and CONTAINS the 21; the release register selects from it. But
nothing checked that, and by 2026-08 **all 23 flow citations and all 21 register handles dangled** —
zero resolved. A flow is only traceable through that one pointer: an engineer reading a flow and
wanting the authoritative scenario (success criteria, actors, refusal cases) has nowhere else to go.

  UCT-001  every `UC source: <handle>` in docs/flows/ resolves to a corpus `handle`.
  UCT-002  every handle in the release register's table resolves to a corpus `handle`.

Both rules carry a BASELINE (tests/uc_traceability_baseline.txt) because the debt is real and being
burned down deliberately — see docs/uc-scope-corpus-reconciliation.md for the row-by-row mapping.
The baseline only SHRINKS: a citation that starts resolving is removed from it, and the gate refuses
to re-add one. New flows and new register rows get no grace.

Exit 0 = every non-baselined citation resolves; 1 = at least one does not.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "tests", "uc_traceability_baseline.txt")
SCOPE = os.path.join(ROOT, "registry", "UDLM-0.1-SCOPE.md")


def corpus_handles():
    out = set()
    for f in glob.glob(os.path.join(ROOT, "use-cases", "**", "*.yaml"), recursive=True):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8"))
        except Exception:
            continue
        if isinstance(d, dict) and d.get("handle"):
            out.add(d["handle"])
    return out


def load_baseline():
    if not os.path.exists(BASELINE):
        return set()
    return {ln.strip() for ln in open(BASELINE, encoding="utf-8")
            if ln.strip() and not ln.startswith("#")}


def main():
    handles = corpus_handles()
    if not handles:
        print("FAILED — no corpus handles found; the gate would pass vacuously")
        return 1
    baseline = load_baseline()
    fails, seen, resolved = [], set(), 0

    # UCT-001 — flow citations
    for f in sorted(glob.glob(os.path.join(ROOT, "docs", "flows", "*.md"))):
        rel = os.path.relpath(f, ROOT)
        for m in re.finditer(r"UC source: `([^`]+)`", open(f, encoding="utf-8").read()):
            h = m.group(1)
            key = f"UCT-001 {os.path.basename(f)} {h}"
            seen.add(key)
            if h in handles:
                resolved += 1
                if key in baseline:
                    fails.append(f"{key}: now resolves — remove it from the baseline "
                                 f"(the baseline only shrinks)")
            elif key not in baseline:
                fails.append(f"UCT-001 {rel}: `UC source: {h}` names no corpus use case — a flow's "
                             f"one traceable pointer")

    # UCT-002 — release register handles
    for line in open(SCOPE, encoding="utf-8"):
        m = re.match(r"\|\s*(\d+)\s*\|\s*([a-z0-9][a-z0-9/._-]+)\s*\|", line)
        if not m:
            continue
        n, h = m.group(1), m.group(2)
        key = f"UCT-002 UC-{int(n):02d} {h}"
        seen.add(key)
        if h in handles:
            resolved += 1
            if key in baseline:
                fails.append(f"{key}: now resolves — remove it from the baseline")
        elif key not in baseline:
            fails.append(f"UCT-002 UDLM-0.1-SCOPE.md UC-{int(n):02d}: handle {h!r} names no corpus "
                         f"use case — the release register selects FROM the corpus")

    stale = baseline - seen
    for s in sorted(stale):
        fails.append(f"stale baseline entry (the citation no longer exists): {s}")

    print(f"uc-traceability: {len(seen)} citation(s) · {resolved} resolve · "
          f"{len(baseline)} baselined")
    if fails:
        for m in fails:
            print(f"  {m}")
        print(f"FAILED — {len(fails)} violation(s)")
        return 1
    print("OK — every non-baselined UC citation resolves to a corpus use case")
    return 0


if __name__ == "__main__":
    sys.exit(main())
