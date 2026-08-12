#!/usr/bin/env python3
"""A definition tier is never described as a lifecycle state (TIER-001).

ADR-033 rules that `Pattern → Template → System` is **two definitions and one instance**, and that a
System is *"the only one of the three carrying `states`"*. `docs/flows/template-assembly.md` taught
the opposite end-to-end — its title, its tier list, both mermaid diagrams and a "State" column all
mapped the three tiers onto Intent → Requested → Realized. A reader following the flow docs got the
model the ADR had retired.

**Why the conflation is wrong rather than merely imprecise**, which is what makes it worth a gate:

  - A Pattern may refine into a NARROWER PATTERN before reaching a Template, and refinement chains
    are walked, never flattened (DRV-001). States are 1:1 and ordered within one record — they could
    not have nested, so the mapping forbids a shape the model allows.
  - One Pattern yields many Templates and one Template many Systems. A state ladder is 1:1 within a
    record; a one-to-many arrow cannot be a state transition.

Both are structural, so a document asserting the mapping is not making a stylistic choice — it is
describing a model that could not work.

  TIER-001  a definition tier (`Pattern`, `Template`) is equated with a lifecycle state
            (`Intent`, `Requested`) — `Pattern = Intent`, `Template (Requested)`,
            `type-level Intent`, `Pattern/Intent`, and the table-cell form where a tier row carries
            a bare state in its next cell.

**Deliberately narrow.** Sentences where the two appear near each other legitimately are common and
must not fire: *"a Template is realized into a System, and that arrow is Intent → Requested →
Realized"* is the CORRECT telling and names both. So this matches only the EQUATING forms — an
`=`, a parenthetical gloss, a slash-pair, or a table row — never mere proximity.

**ADRs are exempt.** A decision record narrates the reading it retired; that is its job, and
`ADR-033` has to be able to say what it rejected.

Exit 0 = no document equates a definition tier with a state.
"""
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TIERS = r"(?:Pattern|Template)"
STATES = r"(?:Intent|Requested|Realized)"

PATTERNS = [
    # Pattern = Intent   /   Pattern / Template / System = Intent / Requested / Realized
    (re.compile(rf"\b{TIERS}\b[^.\n|]{{0,40}}=\s*\**{STATES}\b"), "equated with ="),
    # Pattern/Intent   —   a slash pair naming a tier and a state as one thing
    (re.compile(rf"\b{TIERS}\s*/\s*\**{STATES}\b"), "slash-paired as one thing"),
    (re.compile(rf"\b{STATES}\s*/\s*\**{TIERS}\b"), "slash-paired as one thing"),
    # type-level Intent  —  the specific gloss the flow doc used for a Pattern
    (re.compile(r"\btype-level\s+\**Intent\b", re.IGNORECASE), "a definition glossed as a state"),
    # Template (Requested)  /  Pattern · Intent  —  a tier with a state as its gloss
    (re.compile(rf"\b{TIERS}\b\s*[(·]\s*\**{STATES}\b"), "a state given as the tier's gloss"),
    # a table row: | **Template** | ... | Requested |   — the "State" column form
    (re.compile(rf"^\|\s*\**{TIERS}\**\s*\|[^|\n]*\|\s*\**{STATES}\**\s*(?:\([^)]*\))?\s*\|"),
     "a tier row carrying a state in a table cell"),
    # A mermaid node label: Template<br/>orderable definition<br/>Requested. Caught by the
    # self-test, not by review — the diagram form carried the mapping twice and matched none of the
    # prose arms, which is exactly the surface a reader trusts most and a grep sees least.
    (re.compile(rf"\b{TIERS}<br\s*/?>[^\"\]]{{0,60}}<br\s*/?>\s*{STATES}\b"),
     "a mermaid node labelling a definition tier with a state"),
    # "the assembly's Requested state" / "it is the Requested state"
    (re.compile(rf"\bassembly's\s+\**{STATES}\**\s+state\b"), "an assembly tier called a state"),
]

# A decision record must be able to describe the reading it retired.
EXCLUDE_PREFIX = ("docs/adr/", "tests/", "docs/internal/")
EXCLUDE_EXACT = {"AGENTS.md", "CLAUDE.md"}


def tracked():
    out = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True,
                         check=True, cwd=REPO).stdout
    for p in out.splitlines():
        if p in EXCLUDE_EXACT or p.startswith(EXCLUDE_PREFIX):
            continue
        yield p


def main():
    hits, scanned = [], 0
    for rel in tracked():
        scanned += 1
        try:
            lines = open(os.path.join(REPO, rel), encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            for pat, why in PATTERNS:
                m = pat.search(line)
                if m:
                    hits.append((rel, n, why, m.group(0).strip(), line.strip()[:120]))
                    break

    # Self-test: the arms must fire on the exact sentences that were shipped, and must NOT fire on
    # the correct telling — which names a tier and a state in one breath and is the whole point.
    st = []
    was_shipped = [
        "- **Template** — that design resolved into a concrete, orderable definition. It is the assembly's **Requested** state.",
        "    TMP[\"Template<br/>orderable definition<br/>Requested\"]:::t",
        "(Pattern / Template / System = Intent / Requested / Realized)",
        "(Pattern/Intent → Requested → Realized, UUID-stable across destruction).",
        "| **Template** | \"FSI/prod\" — Kubernetes | Requested | every blank pinned |",
        "It is **type-level Intent** (design-time), and it lives in Knowledge.",
    ]
    for probe in was_shipped:
        if not any(p.search(probe) for p, _ in PATTERNS):
            st.append(f"TIER-SELF no arm fires on a shipped conflation: {probe[:70]}")
    correct = [
        "A Template is **realized** into a System, and that arrow alone is `Intent → Requested → Realized`.",
        "A Pattern and a Template are both definitions; only a System carries Intent, Requested and Realized.",
        "| **System** | \"acme-prod\" | instance — carries Intent · Requested · Realized | output |",
    ]
    for probe in correct:
        m = [why for p, why in PATTERNS if p.search(probe)]
        if m:
            st.append(f"TIER-SELF an arm fires on the CORRECT telling ({m[0]}): {probe[:70]}")

    print(f"tier/state conflation: {scanned} document(s) scanned")
    for m in st:
        print(f"  FAIL [{m}")
    for rel, n, why, frag, line in hits:
        print(f"  ✗ TIER-001 {rel}:{n} — {frag!r} {why}")
        print(f"      {line}")
    if hits or st:
        if hits:
            print("\nADR-033: Pattern and Template are DEFINITIONS; a System is the instance and the "
                  "only one carrying `states`. The mapping forbids two shapes the model allows — a "
                  "refinement chain deeper than three, and one definition yielding many instances.")
        return 1
    print("OK — no document equates a definition tier with a lifecycle state")
    return 0


if __name__ == "__main__":
    sys.exit(main())
