#!/usr/bin/env python3
"""Validate every Resource Type Specification against the registry meta-schema.

The definition rules (registry/SPEC-DESIGN-REQUIREMENTS.md, AGENTS.md) say every type MUST
validate against registry/resource-type-spec.schema.json — this makes that checkable instead
of manual. Run before merging any registry change:

    python3 tests/validate_registry.py

Exit 0 = all types valid. Also enforces conventions the meta-schema itself can't express:
  - $id version segment == the `version` field
  - $id spec segment  == `conforms_to`
  - ADOPT-001: every adopts[].standard string is Covered by an entry in
    registry/standards-adoption-register.md (SPEC-DESIGN hard constraint 31 — what/why/
    where/when/who for every standards decision; adoption without a registered decision
    does not merge)

Requires: pip install jsonschema pyyaml
"""
import glob
import json
import os
import re
import sys

import yaml

import jsonschema

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def main() -> int:
    meta = json.load(open(os.path.join(ROOT, "registry", "resource-type-spec.schema.json")))
    validator = jsonschema.Draft202012Validator(meta)

    failures = 0
    paths = sorted(
        glob.glob(os.path.join(ROOT, "registry", "resource-types", "*.json"))
        + glob.glob(os.path.join(ROOT, "registry", "resource-types", "*.yaml"))
    )
    for path in paths:
        rel = os.path.relpath(path, ROOT)
        if path.endswith(".yaml"):
            import yaml
            doc = yaml.safe_load(open(path))
        else:
            doc = json.load(open(path))

        errs = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        for e in errs:
            failures += 1
            loc = "/".join(map(str, e.path)) or "<root>"
            print(f"FAIL {rel} @ {loc}: {e.message}")

        # $id must encode both version axes and agree with the body (meta-schema checks the
        # pattern, not the cross-field agreement).
        m = re.match(r"^https://udlm\.dev/registry/(udlm/[0-9.]+)/[^/]+/([0-9.]+)$", doc.get("$id", ""))
        if not m:
            failures += 1
            print(f"FAIL {rel}: $id does not parse: {doc.get('$id')}")
        else:
            if m.group(1) != doc.get("conforms_to"):
                failures += 1
                print(f"FAIL {rel}: $id spec segment {m.group(1)!r} != conforms_to {doc.get('conforms_to')!r}")
            if m.group(2) != doc.get("version"):
                failures += 1
                print(f"FAIL {rel}: $id version segment {m.group(2)!r} != version {doc.get('version')!r}")

        if not errs:
            print(f"ok   {rel}  ({doc.get('resource_type')} {doc.get('version')})")

    # ADOPT-001 — every adopted standard has a register entry (constraint 31)
    register = open(os.path.join(ROOT, "registry", "standards-adoption-register.md")).read()
    covered = set()
    for line in register.splitlines():
        if "**Covers:**" in line:
            covered.update(re.findall(r"`([^`]+)`", line.split("**Covers:**", 1)[1]))
    for path in paths:
        doc = yaml.safe_load(open(path)) if path.endswith(".yaml") else json.load(open(path))
        for a in doc.get("adopts") or []:
            std = a.get("standard")
            if std and std not in covered:
                failures += 1
                print(f"FAIL [ADOPT-001] {os.path.relpath(path, ROOT)}: adopts {std!r} with no "
                      f"entry in standards-adoption-register.md — register the decision "
                      f"(what/why/where/when/who) in the same change")

    print(f"\n{len(paths)} type spec(s) checked, {failures} failure(s)")
    return 1 if failures else 0

if __name__ == "__main__":
    sys.exit(main())
