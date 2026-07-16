#!/usr/bin/env python3
"""Single-source guard for the UDLM spec.

Every normative rule carries a stable ID (INF-001, ENT-006, DPO-003, PRV-009, ...).
The single-source rule (SPEC-DESIGN — "one rule, one home, one ID; reference, never
restate") says a given ID is *defined* in exactly one file; other files reference it.

This check flags:
  - COLLISION (error): the same full ID is *defined* in more than one file.
  - PREFIX SPREAD (warning): one ID family (e.g. ENT-*) is defined across multiple
    files — a family should have a single owning file, or the prefixes should be
    disjoint (the repo already did REL-* -> ERL-* for exactly this reason).

"Defined" is detected structurally: the ID appears as the first cell of a Markdown
table row -- the form these specs use to define policy rows. Prose references
("see INF-006") are not first-cell and are ignored.

Existing debt is grandfathered in BASELINE_COLLISIONS so the check is green today and
fails on any NEW collision (a ratchet). As dedup PRs land, entries are removed from the
baseline; a baseline entry that no longer collides is itself reported (keeps it honest).

Exit 0 clean, 1 on a non-baseline collision. Warnings never fail the build.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Directories that are not the normative spec surface.
SKIP_DIRS = {".git", "node_modules", "docs/internal", "tests", ".github"}

# A rule ID: an uppercase prefix (optionally hyphen-segmented, e.g. REG-DP, ADR-PROV)
# followed by -NNN. The "family" is everything before the final -NNN.
ID_RE = re.compile(r"([A-Z][A-Z0-9]{1,7}(?:-[A-Z]{1,5})*)-(\d{2,3})\b")
# Definition = first non-empty cell of a table row.
ROW_RE = re.compile(r"^\|\s*`?([A-Z][A-Z0-9]{1,7}(?:-[A-Z]{1,5})*-\d{2,3})`?\s*\|")

# Known existing duplicate definitions (the dedup-audit-2026-07-15 debt). Each is
# "ID: [file, file, ...]". New collisions NOT listed here fail the check. Burn these
# down as the Bucket-B dedup PRs land, then delete the entry.
BASELINE_COLLISIONS = {
    # ENT-* — entity-type invariants vs entity/dependency gap rules vs dependency-graph
    # rules collide across three files. Fix: disjoint prefixes (as REL-* -> ERL-* already did).
    "ENT-001": ["entities/resource-service-entities.md", "foundations/entity-types.md"],
    "ENT-002": ["entities/resource-service-entities.md", "foundations/entity-types.md"],
    "ENT-003": ["entities/resource-service-entities.md", "foundations/entity-types.md"],
    "ENT-004": ["entities/resource-service-entities.md", "foundations/entity-types.md"],
    "ENT-005": ["entities/resource-service-entities.md", "foundations/entity-types.md"],
    # INF-* — persistence policies (data-contracts) vs information-provider policies. Same
    # prefix, two unrelated meanings; renumber the information-provider family.
    "INF-001": ["contracts/information-providers-advanced.md", "design-principles/data-contracts.md"],
    "INF-003": ["contracts/information-providers-advanced.md", "design-principles/data-contracts.md"],
    "INF-004": ["contracts/information-providers-advanced.md", "design-principles/data-contracts.md"],
    "INF-006": ["contracts/information-providers-advanced.md", "design-principles/data-contracts.md"],
    "INF-007": ["contracts/information-providers-advanced.md", "design-principles/data-contracts.md"],
    # OBS-* / STO-* — observability doc reuses IDs owned by service-dependencies / storage.
    "OBS-002": ["entities/service-dependencies.md", "observability/audit-provenance-observability.md"],
    "STO-004": ["contracts/storage-providers.md", "observability/audit-provenance-observability.md"],
    # (XTA-001..004 and ENT-006 pruned 2026-07-15 — no longer collide on main.)
}


def spec_md_files():
    for root, dirs, files in os.walk(REPO):
        rel = os.path.relpath(root, REPO)
        dirs[:] = [d for d in dirs if os.path.join(rel, d).lstrip("./") not in SKIP_DIRS
                   and d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield os.path.join(root, f)


def main():
    # full_id -> set(files where defined); family -> set(files)
    defined = {}
    family_files = {}
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
            fam = ID_RE.match(full).group(1)
            defined.setdefault(full, set()).add(rel)
            family_files.setdefault(fam, set()).add(rel)

    collisions = {i: sorted(fs) for i, fs in defined.items() if len(fs) > 1}
    new_collisions = {}
    for i, fs in collisions.items():
        base = BASELINE_COLLISIONS.get(i)
        if base is None or sorted(base) != fs:
            new_collisions[i] = fs

    # A baseline entry that no longer collides — stale, should be removed.
    stale = [i for i in BASELINE_COLLISIONS if i not in collisions]

    # Prefix spread (warning only): a family defined across >1 file.
    spread = {f: sorted(fs) for f, fs in family_files.items() if len(fs) > 1}

    print(f"single-source: {len(defined)} rule IDs across the spec; "
          f"{len(collisions)} collide ({len(collisions) - len(new_collisions)} baselined).")

    for fam, fs in sorted(spread.items()):
        print(f"  [warn] family {fam}-* defined across {len(fs)} files: {', '.join(fs)}")

    if stale:
        print("\nSTALE baseline entries (no longer collide — remove from BASELINE_COLLISIONS):")
        for i in stale:
            print(f"  - {i}")

    if new_collisions:
        print("\nNEW single-source violations (same ID defined in >1 file):")
        for i, fs in sorted(new_collisions.items()):
            print(f"  ✗ {i} defined in: {', '.join(fs)}")
        print("\nFix: keep one definition, reference the ID elsewhere; or, if two "
              "families clash, renumber one to a disjoint prefix. See "
              "SPEC-DESIGN-REQUIREMENTS.md (single-source rule).")
        return 1

    print("OK — no new single-source violations.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
