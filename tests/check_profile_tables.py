#!/usr/bin/env python3
"""Guard extension: profile value tables must live only in a setting's one home.

The single-source guard (check_single_source.py) catches a duplicate rule-ID, but a duplicated
*value table* — a `minimal | dev | standard | prod | fsi | sovereign` table of settings — has no ID,
so it slips through. That is how the interaction-credential lifetime (A5) came to be defined twice and
drift. ADR-015 (settings & config bundles) says a profile-governed setting is defined once, in its
owning bundle; everywhere else references it.

This check finds every **profile table** (a Markdown table row carrying >=3 profile names) and flags any
that sits in a doc the profile-settings index (registry/profile-settings-index.md) does not name as a
setting owner. The index is the allowlist: a profile table in an un-indexed doc is either a new setting
to add to the index, or a duplicate to collapse to a reference.

Report-only (exit 0) while the dedup PRs land and remove the existing duplicates; promote to a gate once
the surface is clean.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(REPO, "registry", "profile-settings-index.md")

PROFILES = ["minimal", "dev", "standard", "prod", "fsi", "sovereign"]
SCOPE = ["contracts", "foundations", "governance", "entities", "observability",
         "lifecycle", "design-principles", "registry"]
# The master scaling table + the index itself legitimately enumerate profiles.
ALWAYS_OK = {"design-principles/design-priorities.md", "registry/profile-settings-index.md"}
# A doc path referenced in the index (e.g. governance/credentials.md).
DOCPATH_RE = re.compile(r"\b((?:contracts|foundations|governance|entities|observability|lifecycle|"
                        r"design-principles|registry)/[A-Za-z0-9_.-]+\.md)\b")


def _cells(line):
    return [c.strip().strip("`").lower() for c in line.split("|")]


def count_profile_tables(lines):
    """A profile table has >=3 profile names as column headers OR as first-column row labels.
    Catches both the column-style (| setting | minimal | dev | ...) and the row-style
    (| minimal | ... | / | dev | ... |) — the latter is the A5 case."""
    count, i, n = 0, 0, len(lines)
    while i < n:
        if not lines[i].lstrip().startswith("|"):
            i += 1
            continue
        # gather the contiguous table block
        j = i
        rows = []
        while j < n and lines[j].lstrip().startswith("|"):
            rows.append(_cells(lines[j]))
            j += 1
        # header cells (row 0) and first-column labels (all rows), minus separator rows
        header = set(rows[0]) if rows else set()
        first_col = {r[1] for r in rows if len(r) > 1 and not set(r[1]) <= set("-: ")}
        if sum(p in header for p in PROFILES) >= 3 or sum(p in first_col for p in PROFILES) >= 3:
            count += 1
        i = j
    return count


def main():
    owners = set(ALWAYS_OK)
    try:
        for m in DOCPATH_RE.finditer(open(INDEX, encoding="utf-8").read()):
            owners.add(m.group(1))
    except OSError:
        print("profile-settings index not found — cannot resolve setting owners")
        return 0

    found = {}  # rel -> count of profile-table rows
    for d in SCOPE:
        base = os.path.join(REPO, d)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith(".md"):
                    continue
                rel = os.path.relpath(os.path.join(root, f), REPO)
                try:
                    lines = open(os.path.join(root, f), encoding="utf-8").read().splitlines()
                except (OSError, UnicodeDecodeError):
                    continue
                n = count_profile_tables(lines)
                if n:
                    found[rel] = n

    unindexed = {r: c for r, c in found.items() if r not in owners}
    print(f"profile-tables: {len(found)} docs contain a profile value table; "
          f"{len(unindexed)} are not named as a setting owner in the index.")
    for rel in sorted(found):
        tag = "owner" if rel in owners else "REVIEW"
        print(f"  [{tag}] {rel} — {found[rel]} profile row(s)")
    if unindexed:
        print("\nProfile tables in docs the index does not list as owners — for each: add it to "
              "registry/profile-settings-index.md as a setting home, or collapse it to a reference "
              "to the setting's existing home (ADR-015 / SPEC-DESIGN §33).")
    else:
        print("OK — every profile table sits in an indexed setting home.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
