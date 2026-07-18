#!/usr/bin/env python3
"""Single-source guard for *named concept definitions* (not rule IDs).

Companion to check_single_source.py. That guard enforces "one rule-ID, one home" on rule
rows (INF-001, DPO-003, …). This one covers the case that guard cannot see: a named framework
*re-defined* in prose in a second file while its canonical home is elsewhere — exactly how the
Design Priority Order framework ended up spelled out in both design-priorities.md (its home) and
foundations.md, in *different words* (so a text-match guard would miss it too).

The robust signal is structural, not textual. A concept has one home file. Any OTHER file may
*reference* the concept — a short pointer section that links to the home — but must not
*re-define* it. A re-definition is detected by an enumerated body under the concept's heading:
a numbered list or a Markdown table. A one-line orientation + link (the conceded form) is fine.

To register a concept: add a CANONICAL row (concept name, heading regex, home file). To
grandfather a known-but-not-yet-fixed restatement, add a (concept, file) pair to BASELINE — the
check stays green and ratchets (a baseline pair that no longer restates is reported as stale so
it gets removed). Exit 0 clean, 1 on a new restatement.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_DIRS = {".git", "node_modules", "docs/internal", "tests", ".github"}

# concept -> where it is DEFINED, and the heading that introduces a (re)definition of it.
CANONICAL = [
    {
        "concept": "Design Priority Order",
        "heading": re.compile(r"design priority order\b", re.I),
        "home": "design-principles/design-priorities.md",
    },
]

# Known restatements, grandfathered so the check is green today and ratchets on anything NEW.
# Burn these down as the fixing PRs land; a stale entry (no longer restating) is reported.
BASELINE = {
    # foundations.md restated the DPO framework as a numbered list. Cleared by croadfeldt/udlm#147
    # (collapsed to a one-line pointer). Remove this entry once #147 is on main.
    ("Design Priority Order", "foundations/foundations.md"),
}

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
NUMBERED_ITEM = re.compile(r"^\s*\d+\.\s+\S")
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$")


def spec_md_files():
    for root, dirs, files in os.walk(REPO):
        rel = os.path.relpath(root, REPO)
        dirs[:] = [d for d in dirs
                   if os.path.join(rel, d).lstrip("./") not in SKIP_DIRS and d not in SKIP_DIRS]
        for f in files:
            if f.endswith(".md"):
                yield os.path.relpath(os.path.join(root, f), REPO)


def sections(lines):
    """Yield (heading_text, level, body_lines) for every heading in the file."""
    cur = None
    for line in lines:
        m = HEADING_RE.match(line)
        if m:
            if cur:
                yield cur[0], cur[1], cur[2]
            cur = (m.group(2), len(m.group(1)), [])
        elif cur:
            cur[2].append(line)
    if cur:
        yield cur[0], cur[1], cur[2]


def body_is_enumerated(body):
    """A re-definition: the section spells the concept out as a numbered list or a table
    (>=2 rows, i.e. header + at least one data row), rather than a one-line pointer."""
    table_rows = sum(1 for ln in body if TABLE_ROW.match(ln))
    if table_rows >= 2:
        return True
    return any(NUMBERED_ITEM.match(ln) for ln in body)


def main() -> int:
    violations, matched_baseline = [], set()
    for rel in spec_md_files():
        try:
            lines = open(os.path.join(REPO, rel), encoding="utf-8").read().splitlines()
        except (OSError, UnicodeDecodeError):
            continue
        for concept in CANONICAL:
            if rel == concept["home"]:
                continue
            for heading, _level, body in sections(lines):
                if concept["heading"].search(heading) and body_is_enumerated(body):
                    pair = (concept["concept"], rel)
                    if pair in BASELINE:
                        matched_baseline.add(pair)
                    else:
                        violations.append((concept["concept"], rel, concept["home"]))

    stale = sorted(BASELINE - matched_baseline)

    print(f"definition-single-source: {len(CANONICAL)} registered concept(s); "
          f"{len(violations)} new restatement(s), {len(matched_baseline)} baselined.")
    if stale:
        print("\nSTALE baseline entries (no longer restating — remove from BASELINE):")
        for concept, rel in stale:
            print(f"  - {concept} @ {rel}")
    if violations:
        print("\nNEW definition restatements (concept re-defined outside its home):")
        for concept, rel, home in violations:
            print(f"  ✗ '{concept}' is defined in {home}; {rel} restates it "
                  f"(enumerated body under its heading). Replace with a one-line pointer + link.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
