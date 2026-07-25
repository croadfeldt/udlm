#!/usr/bin/env python3
"""Terminology guard: enforce the locked vocabulary decisions across the registry's prose.

Ported from the dcm repo's gate (same architecture: rules table, whole-file exemptions,
per-line history markers) after the retired term "gating policy" regressed into a corpus file
and two flow docs with nothing upstream to catch it — the mirror repo's gate was the only
line of defense. Scans tracked text files; a forbidden term fails CI UNLESS the file's
purpose is recording decisions/history or the line explicitly documents the change.

Rules are udlm-scoped: dcm's "resource provider" and "likeC4" rules are deliberately absent
(this registry legitimately names LikeC4 as an external interop format, and "resource
provider" appears in blessed contexts). Grow the table with the ruling that retires a term.
"""
import re
import subprocess
import sys

# (label, compiled pattern). Matched per line.
RULES = [
    ("gating policy (merged into Validation Policy)",
     re.compile(r"gating\s+polic(?:y|ies)", re.I)),
    ("gatekeeper policy (OPA Gatekeeper collision)",
     re.compile(r"gatekeeper\s+polic(?:y|ies)", re.I)),
    ("fulfilled (lifecycle state → 'Realized')",
     re.compile(r"fulfilled\s+service|been\s+fulfilled|fulfilled\s+at\s+the\s+request", re.I)),
    ("hash chain (audit is RFC 9162 Merkle, not a linear chain)",
     re.compile(r"hash[- ]chain", re.I)),
    ("provider_extensions (retired surface → Provider-Class SharedDataElements)",
     re.compile(r"provider_extensions", re.I)),
]

# Whole-file exemptions: purpose is recording decisions/history.
EXEMPT_FILES = {
    "AGENTS.md",
    "CLAUDE.md",                       # mirror of AGENTS.md
    "tests/check_terminology.py",
    "registry/tools/validate.py",      # enforcement code REFUSING retired surfaces must name them
    "registry/VERSIONING.md",          # surface-change log names retired surfaces as history
    "registry/renames.yaml",           # the rename map exists to name old things
}

# Immutable uuid-bearing revisions are point-in-time records — never edited to satisfy a
# living-prose gate (the rotation doctrine: a revision is history).
EXEMPT_PREFIXES = ("registry/instances/",)

# Per-line exemption: the line documents the change itself.
HISTORY_MARKER = re.compile(
    r"formerly|previously|no longer|merged into|renamed|renames|reversed|superseded|"
    r"deprecat|was called|do not use|retire|not a linear|instead of|folded|alternativ|→|->", re.I)

TEXT_SUFFIXES = (".md", ".yaml", ".yml", ".json", ".py")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines()
            if f.endswith(TEXT_SUFFIXES) and f not in EXEMPT_FILES
            and not f.startswith(EXEMPT_PREFIXES)]


def main():
    failures = []
    files = tracked_files()
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for lineno, line in enumerate(lines, 1):
            if HISTORY_MARKER.search(line):
                continue
            for label, pat in RULES:
                if pat.search(line):
                    failures.append(f"FAIL [TERM-001] {path}:{lineno}: uses retired term — {label}")
    for f in failures:
        print(f)
    print(f"{len(files)} files scanned, {len(failures)} terminology violation(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
