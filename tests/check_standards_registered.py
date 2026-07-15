#!/usr/bin/env python3
"""Completeness audit: standards cited in the spec that have no register row.

`ADOPT-001` (validate_registry.py) gates JSON `adopts[].standard` strings. But a standard can be
adopted in *prose* — "the error envelope adopts RFC 9457" — with no `adopts[]` entry, so it escapes
that gate. That is exactly how RFC 9457 went unregistered until the 2026-07 standards-change audit.

This check scans the spec prose for standard citations (RFC / AEP identifiers) and lists any that the
register (`registry/standards-adoption-register.md`) does not mention. It is **report-only** (exit 0):
plenty of RFCs are cited informatively, not adopted, so this is a review aid, not a hard gate — the human
decides which listed items are real gaps to register (per adopted-standards.md §8, the change runbook).

Promote to a gate later by curating INFORMATIVE_OK (citations known not to need a register row).
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# A standard is "accounted for" if it is in the adoption register (a decision) OR the standards
# catalog (the reference list). Both are homes; only a standard in neither is a gap.
ACCOUNTED_DOCS = [
    os.path.join(REPO, "registry", "standards-adoption-register.md"),
    os.path.join(REPO, "reference", "standards-catalog.md"),
]

# Spec directories whose prose citations are in scope.
SCOPE = ["contracts", "foundations", "governance", "entities", "observability",
         "lifecycle", "design-principles", "registry"]

# Match RFC/AEP citations, but NOT when they are the tail of an ADR id (ADR-AEP-001 is an ADR, not a standard).
CITE_RE = re.compile(r"(?<!ADR-)\b(RFC\s?\d{3,5}|AEP-\d+)\b")

# Citations known to be informative-only (no adoption) — curate as false positives appear.
INFORMATIVE_OK = set()


def norm(tok):
    return tok.replace("RFC ", "RFC").replace("RFC", "RFC ").strip()


def main():
    accounted = ""
    for path in ACCOUNTED_DOCS:
        try:
            accounted += "\n" + open(path, encoding="utf-8").read()
        except OSError:
            pass
    if not accounted:
        print("neither the register nor the catalog was found")
        return 0
    acct_norm = accounted.replace("RFC ", "RFC")  # tolerate "RFC 9457" / "RFC9457"

    cited = {}  # normalized token -> set(files)
    for d in SCOPE:
        base = os.path.join(REPO, d)
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            for f in files:
                if not f.endswith(".md"):
                    continue
                path = os.path.join(root, f)
                rel = os.path.relpath(path, REPO)
                if path in ACCOUNTED_DOCS:  # don't scan the register/catalog themselves
                    continue
                try:
                    text = open(path, encoding="utf-8").read()
                except (OSError, UnicodeDecodeError):
                    continue
                for m in CITE_RE.finditer(text):
                    cited.setdefault(norm(m.group(1)), set()).add(rel)

    missing = {}
    for tok, files in cited.items():
        if tok in INFORMATIVE_OK:
            continue
        if tok.replace("RFC ", "RFC") not in acct_norm and tok not in accounted:
            missing[tok] = sorted(files)

    print(f"standards-registered: {len(cited)} distinct RFC/AEP citations in the spec; "
          f"{len(missing)} in neither the register nor the catalog.")
    if missing:
        print("\nCited but not in the register (review — is each an adoption to register, "
              "or informative-only?):")
        for tok, files in sorted(missing.items()):
            shown = ", ".join(files[:4]) + (f" (+{len(files) - 4} more)" if len(files) > 4 else "")
            print(f"  ? {tok:10s} — {shown}")
        print("\nTo register a real adoption, follow adopted-standards.md §8 (the change runbook).")
    else:
        print("OK — every cited standard is in the register or catalog.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
