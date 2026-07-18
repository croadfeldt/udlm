#!/usr/bin/env python3
"""Classify the change between two versions of a Resource Type Specification and enforce that
the declared `version` bump is >= the required bump (registry/VERSIONING.md). JSON + YAML native.

Usage: compat-check.py <old.{json,yaml}> <new.{json,yaml}>
Exit 0 = declared bump is sufficient; 1 = under-declared (breaking change as non-major, etc.)."""
import json
import sys
import pathlib

try:
    import yaml
except ImportError:
    yaml = None

RANK = {"revision": 0, "minor": 1, "major": 2}


def load(arg: str):
    path = pathlib.Path(arg)
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(text)
    return json.loads(text)


def walk(schema, prefix=""):
    """Yield (path, node) for every property in a nested JSON-Schema spec fragment."""
    for name, node in (schema.get("properties") or {}).items():
        path = f"{prefix}.{name}" if prefix else name
        yield path, node
        if isinstance(node, dict) and node.get("type") == "object":
            yield from walk(node, path)


def field_index(spec):
    out = {}
    req = set()

    def collect(schema, prefix=""):
        if not isinstance(schema, dict):
            return
        for name in (schema.get("required") or []):
            req.add(f"{prefix}.{name}" if prefix else name)
        for name, node in (schema.get("properties") or {}).items():
            path = f"{prefix}.{name}" if prefix else name
            out[path] = node
            collect(node, path)
        # Schema combinators: index each branch's fields at the SAME path. A field
        # expressed as "inline shape OR data_reference" (the ADR-012 pattern) keeps its
        # inner fields addressable, so wrapping an existing shape in a new oneOf branch is
        # additive (MINOR), not a field removal (MAJOR). Without this, any type adopting a
        # data_reference oneOf false-fails the compat gate.
        for key in ("oneOf", "anyOf", "allOf"):
            for branch in (schema.get(key) or []):
                collect(branch, prefix)

    collect(spec)
    return out, req


def classify(old, new):
    reasons = {"major": [], "minor": []}
    o_fields, o_req = field_index(old.get("spec", {}))
    n_fields, n_req = field_index(new.get("spec", {}))

    for path in o_fields:
        if path not in n_fields:
            reasons["major"].append(f"removed spec field '{path}'")
    for path in n_fields:
        if path not in o_fields:
            reasons["minor"].append(f"added spec field '{path}'")
    for path in (n_req - o_req):
        if path in o_fields:
            reasons["major"].append(f"field '{path}' became required")

    for path in set(o_fields) & set(n_fields):
        o, n = o_fields[path], n_fields[path]
        if isinstance(o, dict) and isinstance(n, dict):
            oe, ne = o.get("enum"), n.get("enum")
            if oe and ne:
                if set(oe) - set(ne):
                    reasons["major"].append(f"narrowed enum on '{path}'")
                elif set(ne) - set(oe):
                    reasons["minor"].append(f"widened enum on '{path}'")
            for bound, worse in (("minimum", lambda a, b: b > a), ("maximum", lambda a, b: b < a)):
                if bound in o and bound in n and o[bound] != n[bound]:
                    (reasons["major"] if worse(o[bound], n[bound]) else reasons["minor"]).append(
                        f"changed {bound} on '{path}'")

    o_out, n_out = set(old.get("outputs", {})), set(new.get("outputs", {}))
    reasons["major"] += [f"removed output '{o}'" for o in (o_out - n_out)]
    reasons["minor"] += [f"added output '{o}'" for o in (n_out - o_out)]

    def rels(d):
        # edge_type is the current field (ADR-026); `kind` is the pre-rename name, tolerated
        # so an old-vs-new compare across the rename doesn't read every edge as removed+added.
        return {(r.get("edge_type", r.get("kind")), r["target"]) for r in d.get("relationships", [])}
    reasons["major"] += [f"removed relationship {r}" for r in (rels(old) - rels(new))]
    reasons["minor"] += [f"added relationship {r}" for r in (rels(new) - rels(old))]

    for key in ("entity_type", "portability"):
        if old.get(key) != new.get(key):
            reasons["major"].append(f"changed {key}: {old.get(key)} -> {new.get(key)}")

    if reasons["major"]:
        return "major", reasons
    if reasons["minor"]:
        return "minor", reasons
    return "revision", reasons


def declared_bump(old_v, new_v):
    o = [int(x) for x in old_v.split(".")]
    n = [int(x) for x in new_v.split(".")]
    if n[0] != o[0]:
        return "major"
    if n[1] != o[1]:
        return "minor"
    return "revision"


def main() -> int:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    old, new = load(sys.argv[1]), load(sys.argv[2])
    required, reasons = classify(old, new)
    declared = declared_bump(old["version"], new["version"])
    # Pre-1.0 relaxation (semver 0.x; UDLM 1.0 not yet cut): a 0.x type is not yet
    # backward-compat-committed, so a breaking (MAJOR-classified) change is permitted under a MINOR
    # bump until 1.0. The classification is still computed and printed so the break stays VISIBLE and
    # can be denoted in migration_guidance; only the enforced bar is relaxed. Once a type reaches 1.x
    # the full MAJOR bar applies again.
    pre_1_0 = int(str(new["version"]).split(".")[0]) == 0
    enforced = "minor" if (pre_1_0 and required == "major") else required
    note = "   [pre-1.0: MAJOR relaxed to MINOR]" if enforced != required else ""
    print(f"{old['resource_type']}: {old['version']} -> {new['version']}")
    print(f"  required bump: {required.upper()}   declared bump: {declared.upper()}{note}")
    for level in ("major", "minor"):
        for r in reasons[level]:
            print(f"    [{level}] {r}")
    if RANK[declared] < RANK[enforced]:
        print(f"\nFAIL: a {enforced} change must bump at least the {enforced} component "
              f"(declared {old['version']} -> {new['version']}).")
        return 1
    if enforced != required:
        print("\nOK (pre-1.0): a MAJOR-classified change is allowed under a MINOR bump until 1.0 — "
              "denote it in migration_guidance if it is a real incompatibility.")
        return 0
    print("\nOK: declared version bump is sufficient.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
