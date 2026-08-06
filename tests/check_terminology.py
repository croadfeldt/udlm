#!/usr/bin/env python3
"""Terminology guard (TERM-001): the locked vocabulary decisions, enforced across the repo's text.

Rule home: CONTRIBUTING.md § "Terminology discipline (TERM-001)" — a term retired by a ruling
does not reappear in living text; a line that documents the retirement is not a use of it.

Ported from the dcm repo's gate (same architecture: rules table, exemptions, per-line history
markers) after the retired term "gating policy" regressed into a corpus file and two flow docs
with nothing upstream to catch it. Scans tracked text files; a forbidden term fails CI UNLESS
the file+rule is exempt (the file's purpose is recording that decision) or the line explicitly
documents the change.

Rules are udlm-scoped: dcm's "resource provider" and "likeC4" rules are deliberately absent
(this registry legitimately names LikeC4 as an external interop format, and "resource
provider" appears in blessed contexts). Grow the table with the ruling that retires a term.

Evasions closed 2026-07-25 (each with the live corpus violation it exposed):
  1. LINE WRAP — a term split across two lines evaded a line-based regex. The scan now also
     tests each line joined to its successor. Caught: docs/spec/contracts/time-and-clock.md §8, where
     "the hash\\nchain" carried the retired linear-chain wording past the gate.
  2. BARE ARROW — the history marker accepted "→"/"->" anywhere on the line, so any line with
     an arrow (most of this spec's prose) was skipped wholesale. Arrows are no longer markers;
     the words that actually document a change are. Caught: tests/test-framework-specification.md
     MRKL-004, "verify hash chain" on an arrow-bearing row.
  3. HYPHENATION — "gating-policy" evaded `gating\\s+polic`. Separators are now `[-\\s]+`.
  4. BLANKET EXEMPTIONS — whole-file and whole-directory exemptions hid every rule, not the one
     the file legitimately names. Exemptions are now (file → rules), and the
     `registry/examples/` directory exemption is one file + one rule.
Known limit (deliberate): the join is pairwise, so a term spread across three lines still
evades; and matching is per-file, so a term reintroduced in a binary or untracked file is
out of scope.
"""
import re
import subprocess
import sys

# (label, compiled pattern). Matched per line, and per line joined to its successor.
RULES = [
    ("gating policy (merged into Validation Policy)",
     re.compile(r"gating[-\s]+polic(?:y|ies)", re.I)),
    ("gatekeeper policy (OPA Gatekeeper collision)",
     re.compile(r"gatekeeper[-\s]+polic(?:y|ies)", re.I)),
    ("fulfilled (lifecycle state → 'Realized')",
     re.compile(r"fulfilled[-\s]+service|been[-\s]+fulfilled|fulfilled[-\s]+at[-\s]+the[-\s]+request", re.I)),
    ("hash chain (audit is RFC 9162 Merkle, not a linear chain)",
     re.compile(r"hash[-\s]?chain", re.I)),
    ("provider_extensions (retired surface → Provider-Class SharedDataElements)",
     re.compile(r"provider_extensions", re.I)),
]

ALL = "*"

# Exemptions are (file → the rule labels that file may legitimately name). A file is exempt
# from the rules it exists to record — never from the whole table, so a DIFFERENT retired term
# regressing into an exempt file still fails.
EXEMPT = {
    # The rules table itself names every retired term by construction.
    "tests/check_terminology.py": ALL,
    # The agent context file records the two settled retirements as current-state history.
    "AGENTS.md": {"provider_extensions", "hash chain"},
    "CLAUDE.md": {"provider_extensions", "hash chain"},   # symlink mirror of AGENTS.md
    # Enforcement code REFUSING a retired surface must name it.
    "registry/tools/validate.py": {"provider_extensions"},
    # One immutable uuid-bearing revision records the superseded extension decision. Immutable
    # revisions are point-in-time records — never edited to satisfy a living-prose gate (the
    # rotation doctrine: a revision is history). Grandfathered by file+rule, not by directory:
    # every OTHER instance record is scanned.
    "docs/adr/ADR-038-scoped-resource-type-classes.md": {"provider_extensions"},
}

# Per-line exemption: the line documents the change itself. Words only — a bare arrow is
# punctuation this spec uses everywhere, not evidence that a line is recording a retirement.
HISTORY_MARKER = re.compile(
    r"formerly|previously|no longer|merged into|renamed|renames|reversed|superseded|"
    r"deprecat|was called|do not use|retire|not a linear|instead of|folded|alternativ", re.I)

TEXT_SUFFIXES = (".md", ".yaml", ".yml", ".json", ".py", ".sh")


def exempt(path, label):
    rules = EXEMPT.get(path)
    if rules is None:
        return False
    return rules == ALL or any(label.startswith(r) for r in rules)


def tracked_files():
    out = subprocess.run(["git", "ls-files"], capture_output=True, text=True, check=True)
    return [f for f in out.stdout.splitlines() if f.endswith(TEXT_SUFFIXES)]


def main():
    failures = []
    files = tracked_files()
    for path in files:
        try:
            with open(path, encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except (UnicodeDecodeError, FileNotFoundError):
            continue
        for i, line in enumerate(lines):
            nxt = lines[i + 1] if i + 1 < len(lines) else ""
            marked = bool(HISTORY_MARKER.search(line))
            # The wrapped-term scan: a marker on EITHER line documents the wrapped sentence.
            pair = ("" if marked or HISTORY_MARKER.search(nxt) or not line.strip()
                    or not nxt.strip() else line.rstrip() + " " + nxt.strip())
            for label, pat in RULES:
                if exempt(path, label):
                    continue
                if not marked and pat.search(line):
                    failures.append(f"FAIL [TERM-001] {path}:{i + 1}: uses retired term — {label}")
                elif pair and pat.search(pair):
                    failures.append(f"FAIL [TERM-001] {path}:{i + 1}: uses retired term across a "
                                    f"line wrap — {label}")
    for f in failures:
        print(f)
    print(f"{len(files)} files scanned, {len(failures)} terminology violation(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
