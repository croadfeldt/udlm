#!/usr/bin/env python3
"""Every enum value a record schema mints is snake_case (row 120; naming-conventions §4).

Row 103 made class enum values snake_case and gate G9 holds classes to it. The record schemas
(registry/*.schema.json) mint vocabularies too: license compatibility, portability, condition types,
natural-key schemes, the seal algorithm. This gate refuses a hyphenated value in any of them. Values
spelled in UPPER_CASE or Capitalized (audit actions, the four states, curation states) are conventions
of their own and are not checked here.

One exception, by exact match (LEGACY below): a spelling a sealed record already carries and can never
change. Row 121 keeps the pre-row-120 seal algorithm `sha256-jcs` legal, because a sealed record is never
re-sealed. The list only shrinks: an entry the schemas no longer carry is reported stale.

Exit 0 = no record-schema enum value is hyphenated, except a LEGACY spelling, and LEGACY has no stale entry.
"""
import glob
import json
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HYPHENATED = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)+$")
# (schema file, JSON path, value) -> why the old spelling must stay legal. Never a new vocabulary value.
LEGACY = {
    ("registry/state-record.schema.json", "/$defs/integrity/properties/algorithm", "sha256-jcs"):
        "row 121: records sealed before row 120 carry it and are never re-sealed (ADR-051)",
}


def hyphenated(node, path=""):
    out = []
    if isinstance(node, dict):
        for key in ("enum", "x-extensible-enum"):
            values = node.get(key)
            if isinstance(values, list):
                out += [(path, v) for v in values if isinstance(v, str) and HYPHENATED.match(v)]
        for k, v in node.items():
            out += hyphenated(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            out += hyphenated(v, f"{path}/{i}")
    return out


def self_test():
    assert hyphenated({"enum": ["ok_value", "bad-value"]}) == [("", "bad-value")]
    assert not hyphenated({"enum": ["ok_value", "UPPER_CASE", "Capitalized"]})
    assert all(HYPHENATED.match(v) for _, _, v in LEGACY), "a LEGACY entry that is not hyphenated needs no exception"


def main():
    self_test()
    bad, seen = [], set()
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "*.schema.json"))):
        rel = os.path.relpath(f, REPO)
        with open(f, encoding="utf-8") as fh:
            for path, v in hyphenated(json.load(fh)):
                if (rel, path, v) in LEGACY:
                    seen.add((rel, path, v))
                    continue
                bad.append(f"{rel}:{path}: {v!r} is hyphenated; UDLM mints snake_case values (row 103, 120)")
    for entry in sorted(set(LEGACY) - seen):
        bad.append(f"{entry[0]}:{entry[1]}: LEGACY entry {entry[2]!r} is no longer in the schema; remove it (the list only shrinks)")
    for b in bad:
        print(b)
    print(f"record-values: {len(bad)} hyphenated enum value(s) in the record schemas")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
