#!/usr/bin/env python3
"""Model-vocabulary guard: prose examples must speak the schema-enforced vocabulary.

How model drift creeps in: the machine-readable layer — the JSON Schemas and the ~30
resource-type specs — is validated by tests/validate_registry.py, so it stays coherent. The
YAML/JSON *examples embedded in the narrative .md docs* are validated by nothing, so they drift
from the schema freely. That is exactly how entity-relationships.md kept describing a six-type
`relationship_type` / `nature` edge model for months after the authoritative model became the
two-tier `edge_type` + `relation` shape that realized-entity.schema.json + every type spec use.

This gate closes that gap for the relationship/edge vocabulary — the surface that drifted — by
reading the SAME authority the registry does (the `edge_type` enum straight out of
realized-entity.schema.json) and scanning fenced code blocks in the docs for:
  1. RETIRED edge fields   — `relationship_type(s):`, `relationship_nature:`, edge-field `nature:`,
                             and the edge field `kind:` (retired for edges → `edge_type`, ADR-026)
  2. INVALID `edge_type:` values — any `edge_type:` whose value is not in the schema enum

Field checks look INSIDE ``` fences (where a field name is a data claim, not prose), so prose
that discusses "the nature of a relationship" is never flagged. The retired-`kind` check is
value-scoped (only edge values depends_on|contained_by|binds_to|references) so the separate
provenance `source.kind` is never flagged. A narrow PROSE scan (added with the P3 sweep,
2026-07-23) additionally flags unambiguous retired snake_case tokens in running text — the
`kind`→`edge_type` prose escape was the type specimen (repo-cleanliness Q2); common words like
`kind` stay fence-only, identifiers like `dependency_type` cannot false-positive in prose.
Extend RETIRED_FIELDS as the model consolidates. Wired into .github/workflows/validate.yml
alongside the other guards.
"""
import json
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(REPO, "registry", "realized-entity.schema.json")

# Leading `^\s*(?:-\s*)?` so a YAML list item (`  - relationship_type: ...`) is matched too.
_P = r"^\s*(?:-\s*)?"
_EDGE = r"(depends_on|contained_by|binds_to|references)"
RETIRED_FIELDS = [
    (re.compile(_P + r"relationship_types?\s*:"),   "use `edge_type` (+ `strength`) and a declared `relation` name"),
    (re.compile(_P + r"relationship_nature\s*:"),   "nature is derived from `edge_type` — drop the field (entity-relationships.md §6)"),
    (re.compile(_P + r"nature\s*:\s*(<?\s*)?(constituent|operational|informational)"),
                                                    "nature is derived from `edge_type`, not a stored field — drop it (§6)"),
    # edge-field `kind:` is retired → `edge_type` (ADR-026). Value-scoped so source.kind is safe.
    (re.compile(_P + r"kinds?\s*:\s*[\[<]?\s*" + _EDGE),
                                                    "the edge field `kind` is retired — use `edge_type` (ADR-026)"),
    (re.compile(_P + r"dependency_type\s*:"),       "use `strength` (hard|soft); `conditional` is a construction "
                                                    "predicate, not a strength (service-dependencies.md §4)"),
    # Stored shape is retired: Atomic/Composite is derived (`has_constituents`), not an `entity_type`
    # field (ADR-027 addendum, 2026-07-20). Value-scoped so unrelated *_entity_type fields are safe.
    (re.compile(_P + r"entity_type\s*:\s*(<?\s*)?(Atomic|Composite)\b"),
                                                    "the shape is derived (`has_constituents`) — not a stored "
                                                    "`entity_type` field (ADR-027 addendum)"),
]

# Prose scan (outside fences): these snake_case tokens are unambiguous even in running text —
# a mention means the doc still explains the model in retired vocabulary. Lines that say
# "retired" are skipped (tombstones and retirement notes legitimately name the old field),
# and ADRs are excluded wholesale (historical records narrate the vocabulary they retired).
PROSE_RETIRED = re.compile(r"\b(relationship_types?|relationship_nature|dependency_type)\b")
PROSE_SKIP = re.compile(r"retired", re.IGNORECASE)
PROSE_EXCLUDE_PREFIX = ("docs/adr/",)
EDGE_TYPE_LINE = re.compile(r"^\s*(?:-\s*)?edge_type\s*:\s*(.+?)\s*(?:#.*)?$")
FENCE = re.compile(r"^\s*```")

EXCLUDE_EXACT = {"AGENTS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md"}
EXCLUDE_PREFIX = ("tests/", "docs/internal/")
TEXT_SUFFIX = (".md",)


def live_edge_type_enum():
    """The authoritative edge_type vocabulary, read from the schema the registry validates against."""
    try:
        with open(SCHEMA, encoding="utf-8") as fh:
            schema = json.load(fh)
        enum = schema["properties"]["dependencies"]["items"]["properties"]["edge_type"]["enum"]
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


def edge_type_value_ok(raw, enum):
    """`edge_type:` should hold a live enum member. Placeholders (<...>), unions (a|b), and
    lists ([a]) are skipped; a lowercase snake token must be in the enum."""
    v = raw.strip().strip("\"'")
    if not v or v.startswith("<") or "|" in v or "," in v or v.startswith("["):
        return True
    if not re.fullmatch(r"[a-z][a-z0-9_]*", v):
        return True
    return v in enum


def main() -> int:
    enum = live_edge_type_enum()
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
                        if (not path.startswith(PROSE_EXCLUDE_PREFIX)
                                and PROSE_RETIRED.search(line)
                                and not PROSE_SKIP.search(line)):
                            m = PROSE_RETIRED.search(line)
                            hits.append((path, lineno,
                                         f"retired field `{m.group(1)}` in prose — the doc still "
                                         "explains the model in retired vocabulary", line.strip()))
                        continue
                    for rx, hint in RETIRED_FIELDS:
                        if rx.match(line):
                            hits.append((path, lineno, f"retired edge field — {hint}", line.strip()))
                    m = EDGE_TYPE_LINE.match(line)
                    if m and not edge_type_value_ok(m.group(1), enum):
                        hits.append((path, lineno, f"`edge_type` value not in schema enum {sorted(enum)}", line.strip()))
        except (OSError, UnicodeDecodeError):
            continue
    for path, lineno, label, text in hits:
        print(f"FAIL {path}:{lineno}  {label}\n      → {text}")
    print(f"\n{len(files)} docs scanned against the live edge_type enum {sorted(enum)}; {len(hits)} vocabulary drift hit(s)")
    if hits:
        print("Bring the example into line with the authoritative model (data-model-core §4, common-elements §9).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
