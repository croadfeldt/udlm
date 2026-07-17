#!/usr/bin/env python3
"""Session-narration guard: the spec must read as timeless rationale, not a log of the day's work.

An ADR, contract, or type spec is a durable artifact. Phrases that narrate the authoring
session — "this thread", "today's work", "we just added", "in this PR", "latest addition" —
read fine in the moment and wrong six months later. This gate scans the tracked spec files for
that class of wording and fails CI with the file/line + the offending phrase, so it is caught at
review time instead of accreting.

Deliberately NARROW to avoid false positives: it does NOT flag "currently", ADR `Status:`/dates,
or "today's world / today's split / today's opaque X" (those mean *the current state*, which is
legitimate spec language). It only flags first-person / this-session / this-PR narration.

Scope: the published spec. Agent/working-context files (AGENTS.md, CLAUDE.md, README.md,
CONTRIBUTING.md) and the tests/ dir (which necessarily contains these phrases as patterns) are
excluded. Wired into .github/workflows/validate.yml alongside check_estate_tokens.
"""
import re
import subprocess
import sys

# (pattern, human label). Case-insensitive. Kept precise — each must be unambiguous narration.
PATTERNS = [
    (r"\bthis (session|thread|round)\b",                                    "authoring-session narration"),
    (r"\bin this (pr|pull request|commit|changeset|patch)\b",              "PR/commit narration"),
    (r"\btoday'?s work\b",                                                  "'today's work' narration"),
    (r"\b(we|i) just (added|merged|landed|cut|shipped|created|wrote|removed|did)\b", "first-person 'we/I just X' narration"),
    (r"\bjust (added|merged|landed|shipped|wrote) (this|it|them|the)\b",   "'just X-ed this' narration"),
    (r"\b(latest|newest) addition\b",                                      "'latest addition' narration"),
    (r"\bas of this (writing|session|thread|change|commit)\b",             "'as of this writing' narration"),
    (r"\bearlier in this (thread|session)\b",                              "session narration"),
]
COMPILED = [(re.compile(p, re.IGNORECASE), label) for p, label in PATTERNS]

# Working/meta files where a changelog-style note is acceptable, and tests/ (holds the patterns).
EXCLUDE_EXACT = {"AGENTS.md", "CLAUDE.md", "README.md", "CONTRIBUTING.md"}
EXCLUDE_PREFIX = ("tests/", "docs/internal/")
TEXT_SUFFIX = (".md", ".json", ".yaml", ".yml", ".txt")


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True).stdout
    for path in out.splitlines():
        if path in EXCLUDE_EXACT or path.startswith(EXCLUDE_PREFIX):
            continue
        if path.endswith(TEXT_SUFFIX):
            yield path


def main() -> int:
    hits = []
    files = list(tracked_files())
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                for lineno, line in enumerate(fh, 1):
                    for rx, label in COMPILED:
                        m = rx.search(line)
                        if m:
                            hits.append((path, lineno, label, m.group(0)))
        except (OSError, UnicodeDecodeError):
            continue
    for path, lineno, label, phrase in hits:
        print(f"FAIL {path}:{lineno}  {label} — \"{phrase}\"")
    print(f"\n{len(files)} spec files scanned, {len(hits)} session-narration hit(s)")
    if hits:
        print("Rewrite as timeless rationale (state the situation, not the session/PR that changed it).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
