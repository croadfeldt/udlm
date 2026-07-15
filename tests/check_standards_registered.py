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
REGISTER = os.path.join(REPO, "registry", "standards-adoption-register.md")

# Spec directories whose prose citations are in scope.
SCOPE = ["contracts", "foundations", "governance", "entities", "observability",
         "lifecycle", "design-principles", "registry"]

CITE_RE = re.compile(r"\b(RFC\s?\d{3,5}|AEP-\d+)\b")

# Citations known to be informative-only (no adoption) — curate as false positives appear.
INFORMATIVE_OK = set()


def norm(tok):
    return tok.replace("RFC ", "RFC").replace("RFC", "RFC ").strip()


def main():
    try:
        register = open(REGISTER, encoding="utf-8").read()
    except OSError:
        print("register not found")
        return 0
    reg_norm = register.replace("RFC ", "RFC")  # tolerate "RFC 9457" / "RFC9457"

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
                if rel == os.path.relpath(REGISTER, REPO):
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
        if tok.replace("RFC ", "RFC") not in reg_norm and tok not in register:
            missing[tok] = sorted(files)

    print(f"standards-registered: {len(cited)} distinct RFC/AEP citations in the spec; "
          f"{len(missing)} not found in the register.")
    if missing:
        print("\nCited but not in the register (review — is each an adoption to register, "
              "or informative-only?):")
        for tok, files in sorted(missing.items()):
            shown = ", ".join(files[:4]) + (f" (+{len(files) - 4} more)" if len(files) > 4 else "")
            print(f"  ? {tok:10s} — {shown}")
        print("\nTo register a real adoption, follow adopted-standards.md §8 (the change runbook).")
    else:
        print("OK — every cited standard has a register row.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
