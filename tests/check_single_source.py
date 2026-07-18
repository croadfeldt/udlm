#!/usr/bin/env python3
"""Single-source guard for UDLM rule IDs — registry-backed.

Every normative rule carries a stable ID (ENT-006, PRV-009, DPO-003, ...). The convention
(registry/rule-id-naming.md, ADR-028) is: **one prefix = one rule family = one home file.**
A rule is *defined* by an ID-first Markdown table row (`| `PFX-NNN` | ... |`); every other
mention is a citation. The single source of truth for which prefix lives where is
`registry/rule-id-registry.yaml` (validated against rule-id-registry.schema.json).

This check reads that registry and, across the normative spec surface (tests/, .github/,
docs/internal/ excluded), FAILS on:
  - UNREGISTERED  — a prefix is defined in the docs but absent from the registry.
  - OUT-OF-HOME   — a prefix is defined in a file other than its registered `home`
                    (unless that file is grandfathered in the prefix's `baseline_spread`).
  - ID-COLLISION  — the same full ID is defined in >1 file (the sharpest out-of-home case).
  - REGISTRY      — the registry itself is malformed (schema-invalid, duplicate prefix,
                    or a `home` path that does not exist).

A `baseline_spread` entry that no longer contains a definition is reported STALE (non-failing)
so it gets removed — the check ratchets toward zero debt. Exit 0 clean, 1 on any failure.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTRY = os.path.join(REPO, "registry", "rule-id-registry.yaml")
SCHEMA = os.path.join(REPO, "registry", "rule-id-registry.schema.json")

# Directories that are not the normative spec surface.
SKIP_DIRS = {".git", "node_modules", "docs/internal", "tests", ".github"}

# Definition = first non-empty cell of a table row is a rule ID (optionally hyphen-segmented).
ROW_RE = re.compile(r"^\|\s*`?([A-Z][A-Z0-9]{1,7}(?:-[A-Z]{1,5})*-\d{2,3})`?\s*\|")
# The leading prefix of a full ID (REG-DP-002 -> REG; ENT-006 -> ENT).
LEAD_RE = re.compile(r"^[A-Z][A-Z0-9]{1,5}")


def load_registry():
    """Return (entries, errors). Validates against the schema when jsonschema is available."""
    errors = []
    try:
        import yaml
    except ImportError:
        return None, ["pyyaml required to load the rule-id registry"]
    try:
        reg = yaml.safe_load(open(REGISTRY, encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        return None, [f"cannot load {os.path.relpath(REGISTRY, REPO)}: {e}"]

    try:
        import json
        from jsonschema import Draft202012Validator
        schema = json.load(open(SCHEMA, encoding="utf-8"))
        for err in sorted(Draft202012Validator(schema).iter_errors(reg), key=lambda e: list(e.path)):
            loc = "/".join(str(p) for p in err.path) or "(root)"
            errors.append(f"registry schema: {loc}: {err.message}")
    except ImportError:
        pass  # jsonschema optional locally; CI installs it

    entries = (reg or {}).get("prefixes", [])
    seen = set()
    for e in entries:
        pfx = e.get("prefix")
        if pfx in seen:
            errors.append(f"registry: duplicate prefix '{pfx}'")
        seen.add(pfx)
        home = e.get("home")
        if home and not os.path.exists(os.path.join(REPO, home)):
            errors.append(f"registry: prefix '{pfx}' home '{home}' does not exist")
        for f in e.get("baseline_spread", []):
            if not os.path.exists(os.path.join(REPO, f)):
                errors.append(f"registry: prefix '{pfx}' baseline_spread '{f}' does not exist")
    return entries, errors


def spec_md_files():
    for root, dirs, files in os.walk(REPO):
        rel = os.path.relpath(root, REPO)
        dirs[:] = [d for d in dirs if os.path.join(rel, d).lstrip("./") not in SKIP_DIRS
                   and d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(root, f)


def main():
    entries, reg_errors = load_registry()
    if entries is None:
        for e in reg_errors:
            print(f"  ✗ {e}")
        return 1

    home = {e["prefix"]: e["home"] for e in entries}
    baseline = {e["prefix"]: set(e.get("baseline_spread", [])) for e in entries}

    # full_id -> set(files); prefix -> file -> set(numbers)
    defined = {}
    prefix_files = {}
    for path in spec_md_files():
        rel = os.path.relpath(path, REPO)
        try:
            lines = open(path, encoding="utf-8").read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for line in lines:
            m = ROW_RE.match(line)
            if not m:
                continue
            full = m.group(1)
            pfx = LEAD_RE.match(full).group(0)
            defined.setdefault(full, set()).add(rel)
            prefix_files.setdefault(pfx, set()).add(rel)

    unregistered = sorted(p for p in prefix_files if p not in home)

    out_of_home = []          # (prefix, file)
    used_baseline = set()     # (prefix, file) baselines that actually matched
    for pfx, files in prefix_files.items():
        if pfx not in home:
            continue
        for f in sorted(files):
            if f == home[pfx]:
                continue
            if f in baseline.get(pfx, set()):
                used_baseline.add((pfx, f))
            else:
                out_of_home.append((pfx, f))

    collisions = {i: sorted(fs) for i, fs in defined.items() if len(fs) > 1}
    # An id-collision is a NEW failure only if it isn't fully covered by baselines/home.
    new_collisions = {}
    for i, fs in collisions.items():
        pfx = LEAD_RE.match(i).group(0)
        allowed = {home.get(pfx)} | baseline.get(pfx, set())
        if any(f not in allowed for f in fs):
            new_collisions[i] = fs

    stale = sorted((pfx, f) for pfx, bs in baseline.items() for f in bs
                   if (pfx, f) not in used_baseline)

    print(f"rule-id single-source: {len(home)} registered prefix(es); "
          f"{len(defined)} rule IDs across the normative surface; "
          f"{len(collisions)} collide ({len(collisions) - len(new_collisions)} baselined).")

    if stale:
        print("\nSTALE baseline_spread (no definition there anymore — remove from the registry):")
        for pfx, f in stale:
            print(f"  - {pfx}: {f}")

    fail = False
    for e in reg_errors:
        print(f"  ✗ {e}"); fail = True
    if unregistered:
        print("\nUNREGISTERED prefixes (add to registry/rule-id-registry.yaml before use):")
        for p in unregistered:
            print(f"  ✗ {p}-* defined in: {', '.join(sorted(prefix_files[p]))}")
        fail = True
    if out_of_home:
        print("\nOUT-OF-HOME definitions (a prefix defined outside its registered home):")
        for pfx, f in sorted(out_of_home):
            print(f"  ✗ {pfx}-* defined in {f}; home is {home[pfx]}")
        fail = True
    if new_collisions:
        print("\nID-COLLISIONS (same ID defined in >1 file, not grandfathered):")
        for i, fs in sorted(new_collisions.items()):
            print(f"  ✗ {i} defined in: {', '.join(fs)}")
        fail = True

    if fail:
        print("\nFix: define each rule in its prefix's home only; cite by ID elsewhere. To add a "
              "family, register the prefix first. To resolve a clash, renumber one family to a "
              "disjoint prefix (REL-* -> ERL- precedent). See registry/rule-id-naming.md.")
        return 1

    print("OK — every rule-ID prefix is registered and single-homed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
