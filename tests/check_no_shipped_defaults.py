#!/usr/bin/env python3
"""UDLM ships no defaults — a base or type class states what is VALID, never what is CHOSEN.

Maintainer ruling (2026-08-07): *"We should not be setting defaults as part of UDLM. We should have
the mechanism that allows for that, but no defaults in the base or type classes. If an opinionated
implementation wants to do that, fine — but then we also need the mechanism to do that, e.g. layers
and/or policies, maybe as part of a profile."*

**The mechanism already exists and is better than a baked-in default.** A `base`/`core` layer
contributes values to the assembled payload and **every field records the layer uuid that set it**
(layering-and-versioning); a profile carries `settings`. So a layer-supplied default is *attributable*
— you can ask whose decision it was, and policy can override it traceably. A default baked into a
type has **no provenance**: it appears in every estate that ever used the type, with no record of who
chose it and no way to tell an intended value from an inherited one.

The defaults found when this landed show why it matters — `Data.Database.version: "latest"`,
`Storage.FileShare.protocol: "smb"`, `Storage.Volume.volume_mode: "filesystem"`. Each is one
organisation's opinion shipped to every consumer of a portable type.

  NDF-001  no `default` anywhere in a `base` or `type` class element schema.

A **provider** class is exempt by design: a provider IS an opinionated implementation, and declaring
what it does when unasked is its job.

BASELINE: the 46 sites present at landing are listed in tests/no_shipped_defaults_baseline.txt and
burn down separately — removing them touches 27 class files and is its own reviewable change. The
baseline only SHRINKS: a removed default that reappears fails, and a baseline line whose default is
gone must be deleted or the gate fails. New classes get no grace.

Exit 0 = no un-baselined default; 1 = at least one.
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "tests", "no_shipped_defaults_baseline.txt")
ROOTS = [os.path.join(ROOT, "registry", "classes"),
         os.path.join(ROOT, "registry", "examples", "classes")]


def default_sites(schema, path=""):
    if isinstance(schema, dict):
        if "default" in schema:
            yield path or "(top)", schema["default"]
        for k, v in schema.items():
            yield from default_sites(v, f"{path}.{k}" if path else k)
    elif isinstance(schema, list):
        for v in schema:
            yield from default_sites(v, path)


def main():
    baseline = set()
    if os.path.exists(BASELINE):
        baseline = {ln.strip() for ln in open(BASELINE, encoding="utf-8")
                    if ln.strip() and not ln.startswith("#")}
    found, fails = set(), []
    for root in ROOTS:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            d = yaml.safe_load(open(p, encoding="utf-8")) or {}
            if d.get("record_type") != "class":
                continue
            if d.get("class") not in ("base", "type"):
                continue          # a provider IS an opinionated implementation — exempt by design
            for el in (d.get("elements") or []):
                for path, value in default_sites(el.get("schema") or {}):
                    key = f"{d['resource_type']} {el['element']} {path}"
                    found.add(key)
                    if key not in baseline:
                        fails.append(f"NDF-001 {key} = {json.dumps(value)[:40]} — UDLM ships no "
                                     f"defaults; supply it from a layer or profile, where it carries "
                                     f"provenance")
    for stale in sorted(baseline - found):
        fails.append(f"stale baseline entry (the default is gone — remove the line): {stale}")

    print(f"no-shipped-defaults: {len(found)} default site(s) in base/type classes, "
          f"{len(baseline)} baselined")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} violation(s)")
        return 1
    print("OK — no un-baselined default in a base or type class")
    return 0


if __name__ == "__main__":
    sys.exit(main())
