#!/usr/bin/env python3
"""Every part of the spec says how stable it is (STB-001..003).

`registry/stability.yaml` lists every class, every record schema and every spec document with
one of three words (UDLM-1.0-LOCKDOWN.md §1 ruling 4; VERSIONING.md "Stability marker"):

  stable        carries the 1.0 promise — nothing removed, renamed or narrowed inside 1.x
  experimental  may change in a minor without deprecation; not part of the 1.0 claim
  reference     a document that states no rule, so there is nothing to promise

  STB-001  a class, record schema or spec document exists and has no row       -> FAIL
  STB-002  a row names a part that does not exist, or names one twice         -> FAIL
  STB-003  a row's value is not one of the three words                         -> FAIL

The manifest is the single source. A new class, schema or document is not done until it has a
row, which is how an unmarked part is kept from riding into 1.0 by accident.
"""
import glob
import os
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFEST = os.path.join(REPO, "registry", "stability.yaml")
VALUES = {"stable", "experimental", "reference"}


def inventory():
    parts = {}
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "classes", "**", "*.yaml"), recursive=True)):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        if isinstance(d, dict) and d.get("resource_type"):
            parts["class:" + d["resource_type"]] = os.path.relpath(f, REPO)
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "*.schema.json"))):
        parts["schema:" + os.path.basename(f)] = os.path.relpath(f, REPO)
    for f in sorted(glob.glob(os.path.join(REPO, "docs", "spec", "**", "*.md"), recursive=True)):
        parts["doc:" + os.path.relpath(f, os.path.join(REPO, "docs", "spec"))] = os.path.relpath(f, REPO)
    # The two contracts that live outside docs/spec and bind every peer.
    for rel in ("CONFORMANCE.md", "registry/VERSIONING.md"):
        parts["doc:" + rel] = rel
    return parts


def main():
    fails = []
    doc = yaml.safe_load(open(MANIFEST, encoding="utf-8")) or {}
    rows = doc.get("parts") or []
    parts = inventory()
    seen = {}
    for r in rows:
        key = r.get("part")
        val = r.get("stability")
        if key in seen:
            fails.append(f"STB-002 {key}: listed twice")
        seen[key] = val
        if key not in parts:
            fails.append(f"STB-002 {key}: names nothing in the registry or docs/spec")
        if val not in VALUES:
            fails.append(f"STB-003 {key}: stability {val!r} is not one of {sorted(VALUES)}")
    for key, path in parts.items():
        if key not in seen:
            fails.append(f"STB-001 {key} ({path}): no row in registry/stability.yaml")
    counts = {v: sum(1 for x in seen.values() if x == v) for v in sorted(VALUES)}
    for f in fails:
        print("FAIL", f)
    print(f"stability: {len(parts)} part(s) in the inventory, {len(seen)} row(s) — "
          + ", ".join(f"{v} {n}" for v, n in counts.items()) + f"; {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
