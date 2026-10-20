#!/usr/bin/env python3
"""Every uuid field references one of the shared uuid definitions (row 098).

A uuid field in a registry schema, facet or class `$ref`s `common-elements.schema.json`
`#/$defs/uuid_v4` (an entity, definition, tenant, actor, provider or request),
`#/$defs/uuid_v7` (a time-ordered artifact: a state record, an audit-chain leaf, an event) or
`#/$defs/uuid` (v4 or v7, only where the spec does not yet fix the version). The versions come
from identifier-scheme §2.1. Before row 098 the same field was declared inline about ninety times
in five shapes, so the version a field accepted was accidental.

This gate fails on any inline uuid pattern or bare `format: uuid` outside common-elements.
Exit 0 = every uuid field references a shared definition.
"""
import glob
import json
import os
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = "registry/common-elements.schema.json"
UUID_MARK = "[0-9a-f]{8}-[0-9a-f]{4}-"


def inline_uuids(node, path=""):
    """Paths of schema nodes that declare a uuid inline."""
    found = []
    if isinstance(node, dict):
        pattern = node.get("pattern")
        if (isinstance(pattern, str) and UUID_MARK in pattern) or node.get("format") == "uuid":
            found.append(path or "/")
        for k, v in node.items():
            found += inline_uuids(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += inline_uuids(v, f"{path}/{i}")
    return found


def files():
    for pattern in ("registry/**/*.schema.json", "registry/facets/*.json", "registry/classes/**/*.yaml"):
        for f in sorted(glob.glob(os.path.join(REPO, pattern), recursive=True)):
            rel = os.path.relpath(f, REPO)
            if rel != HOME:
                yield rel


def load(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8") as fh:
        return yaml.safe_load(fh) if rel.endswith(".yaml") else json.load(fh)


def self_test():
    assert inline_uuids({"type": "string", "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"})
    assert inline_uuids({"properties": {"id": {"type": "string", "format": "uuid"}}}) == ["/properties/id"]
    assert not inline_uuids({"$ref": "common-elements.schema.json#/$defs/uuid_v4"})
    assert not inline_uuids({"type": "string", "pattern": "^[a-z]+$"})


def main():
    self_test()
    bad = []
    for rel in files():
        for path in inline_uuids(load(rel)):
            bad.append(f"{rel}:{path}")
    if bad:
        print("uuid-refs: inline uuid declarations; $ref common-elements uuid_v4, uuid_v7 or uuid instead:")
        for b in bad:
            print("  " + b)
        return 1
    print("uuid-refs: every uuid field references a shared definition")
    return 0


if __name__ == "__main__":
    sys.exit(main())
