#!/usr/bin/env python3
"""Model-vocabulary guard: prose examples must speak the schema-enforced vocabulary.

How model drift creeps in: the machine-readable layer — the JSON Schemas and the ~30
resource-type specs — is validated by tests/validate_registry.py, so it stays coherent. The
YAML/JSON *examples embedded in the narrative .md docs* are validated by nothing, so they drift
from the schema freely. That is exactly how entity-relationships.md kept describing a six-type
`relationship_type` / `nature` edge model for months after the authoritative model became the
two-tier `kind` + `relation` shape that realized-entity.schema.json + every type spec already use.

This gate closes that gap for the relationship/edge vocabulary — the surface that drifted — by
reading the SAME authority the registry does (the `kind` enum straight out of
realized-entity.schema.json) and scanning fenced code blocks in the docs for:
  1. RETIRED edge fields   — `relationship_type(s):`, `relationship_nature:`, edge-field `nature:`
  2. INVALID `kind:` values — any `kind:` whose value is not in the schema enum

It only looks INSIDE ``` fences (where a field name is a data claim, not prose), so prose that
discusses "the nature of a relationship" is never flagged. Extend RETIRED_FIELDS as more of the
model is consolidated. Wired into .github/workflows/validate.yml alongside the other guards.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "registry", "realized-entity.schema.json")

# Retired edge fields → what to use instead. Add a row when a field name is consolidated away.
# Leading `^\s*(?:-\s*)?` so a YAML list item (`  - relationship_type: ...`) is matched too.
_P = r"^\s*(?:-\s*)?"
RETIRED_FIELDS = [
    (re.compile(_P + r"relationship_types?\s*:"),   "use `kind` (+ `strength`) and a declared `relation` name"),
    (re.compile(_P + r"relationship_nature\s*:"),   "nature is derived from `kind` — drop the field (see entity-relationships.md §6)"),
    (re.compile(_P + r"nature\s*:\s*(<?\s*)?(constituent|operational|informational)"),
                                                    "nature is derived from `kind`, not a stored field — drop it (§6)"),
]
KIND_LINE = re.compile(r"^\s*(?:-\s*)?kind\s*:\s*(.+?)\s*(?:#.*)?$")
FENCE = re.compile(r"^\s*```")

EXCLUDE_EXACT = {"AGENTS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md"}
EXCLUDE_PREFIX = ("tests/", "docs/internal/")
TEXT_SUFFIX = (".md",)


def live_kind_enum():
    """The authoritative edge-kind vocabulary, read from the schema the registry validates against."""
    try:
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        enum = schema["properties"]["dependencies"]["items"]["properties"]["kind"]["enum"]
        return set(enum)
    except (OSError, KeyError, ValueError):
        # Fallback keeps the guard working if the schema shape moves; validate_registry catches that.
        return {"depends_on", "references", "contained_by", "binds_to"}


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True, cwd=REPO).stdout
    for path in out.splitlines():
        if path in EXCLUDE_EXACT or path.startswith(EXCLUDE_PREFIX):
            continue
        if path.endswith(TEXT_SUFFIX):
            yield path


def kind_value_ok(raw, enum):
    """Judge only *edge* kinds. `kind:` is overloaded — it also names object/artifact kinds
    (`kind: ResourceIntent`), which are CamelCase and out of scope here. An edge kind is a
    lowercase snake_case token; flag one only when it isn't a live enum member."""
    v = raw.strip().strip("\"'")
    if not v or v.startswith("<") or "|" in v or "," in v or v.startswith("["):
        return True
    if not re.fullmatch(r"[a-z][a-z0-9_]*", v):   # CamelCase / non-snake → object kind, out of scope
        return True
    return v in enum


def main() -> int:
    enum = live_kind_enum()
    hits = []
    files = list(tracked_files())
    for path in files:
        try:
            with open(os.path.join(REPO, path), encoding="utf-8") as fh:
                in_fence = False
                for lineno, line in enumerate(fh, 1):
                    if FENCE.match(line):
                        in_fence = not in_fence
                        continue
                    if not in_fence:
                        continue
                    for rx, hint in RETIRED_FIELDS:
                        if rx.match(line):
                            hits.append((path, lineno, f"retired edge field — {hint}", line.strip()))
                    m = KIND_LINE.match(line)
                    if m and not kind_value_ok(m.group(1), enum):
                        hits.append((path, lineno, f"`kind` value not in schema enum {sorted(enum)}", line.strip()))
        except (OSError, UnicodeDecodeError):
            continue
    for path, lineno, label, text in hits:
        print(f"FAIL {path}:{lineno}  {label}\n      → {text}")
    print(f"\n{len(files)} docs scanned against the live edge-kind enum {sorted(enum)}; {len(hits)} vocabulary drift hit(s)")
    if hits:
        print("Bring the example into line with the authoritative model (data-model-core §4, common-elements §9).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
