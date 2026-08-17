#!/usr/bin/env python3
"""The spec says what the model IS, not what it was (NARR-001).

Twelve schema descriptions and one spec document explained an absence by narrating the change that
produced it — "this schema previously carried its own copy", "no longer a required stored field",
"it is deliberately NOT the removed predicate vocabulary". Every one told a reader about a state
they never encountered and cannot act on.

**The line, which is not "never mention the past".**

    "There is no X; use Y."          SPEC — a reader looking for X needs the route.
    "There is no X because we        HISTORY — git holds it, and an ADR holds why the
     removed it in favour of Y."     alternative lost.

The first changes what someone does. The second explains a decision already made, and its home is
the decision record's alternatives-considered section (maintainer ruling 2026-08-17: if it does not
directly affect the outcome or inform an ADR, it does not belong in the spec).

  NARR-001  a registry schema description or a `docs/spec/` document uses a past-state phrase —
            `previously`, `used to be`, `formerly`, `was/has been removed`, `no longer a required`,
            `the removed`, `renamed from`.

**What is NOT a hit, and the distinction is by phrase rather than by judgement.** A runtime
condition that happens to use the same words is fine and common: `group.member_removed` describes an
event, "a provider that no longer exists" describes a state at rehydration, "a major version it
previously published" describes what a peer did. None of these narrate a change to the model, so the
patterns are anchored to the FORM that does — a past-tense claim about the specification itself.
`it previously` and `previously declared` are deliberately absent: both appear in runtime
descriptions ("a major version it previously published", "a previously declared intent can be
replayed"), and a pattern that cannot tell those from spec history would push authors to reword
correct descriptions of live behaviour. Only the verbs that take the SPEC as their subject are
matched.

Exit 0 = the spec describes the model, not its history.
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Anchored to phrases that make a past-tense claim ABOUT THE SPEC. "no longer exists" (a runtime
# state) is deliberately absent; "no longer a required" (a field that changed) is present.
NARRATION = re.compile(
    r"\b(previously carried|previously lived|previously citable|previously lacked|"
    r"used to be|formerly known|formerly called|"
    r"was removed|has been removed(?! from)|the removed \w+|no longer a required|"
    r"no longer required|renamed from|this used to|in an earlier version)\b", re.I)

SKIP_PREFIX = ("docs/adr/", "docs/dr/", "docs/internal/", "tests/", "docs/research/")


def hits():
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "registry", "*.schema.json"))):
        rel = os.path.relpath(f, ROOT)
        for n, line in enumerate(open(f, encoding="utf-8").read().splitlines(), 1):
            m = NARRATION.search(line)
            if m:
                out.append((rel, n, m.group(0), line.strip()[:110]))

    tracked = subprocess.run(["git", "ls-files", "docs/spec", "registry"],
                             capture_output=True, text=True, cwd=ROOT).stdout.split()
    for rel in tracked:
        if not rel.endswith(".md") or rel.startswith(SKIP_PREFIX):
            continue
        try:
            lines = open(os.path.join(ROOT, rel), encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for n, line in enumerate(lines, 1):
            m = NARRATION.search(line)
            if m:
                out.append((rel, n, m.group(0), line.strip()[:110]))
    return out


def main():
    found = hits()

    # Self-test: the arm must fire on the sentences that were removed, and must NOT fire on the
    # runtime uses that were kept — a gate that flagged those would push authors to reword correct
    # descriptions of live behaviour.
    st = []
    for was_removed in ("This schema previously carried its own copy",
                        "no longer a required stored field",
                        "It is deliberately NOT the removed predicate vocabulary"):
        if not NARRATION.search(was_removed):
            st.append(f"NARR-SELF no arm fires on removed narration: {was_removed[:52]}")
    for kept in ("A member has been removed from a grouping",
                 "replaying intent against a provider that no longer exists does not degrade",
                 "has deprecated a major UDLM version it previously published",
                 "a previously declared intent can be replayed against current tenancy",
                 "An entry that no longer spreads is reported stale"):
        if NARRATION.search(kept):
            st.append(f"NARR-SELF a runtime description is flagged: {kept[:52]}")

    print(f"spec change narration: registry schemas + docs/spec scanned; {len(found)} finding(s)")
    for m in st:
        print(f"  FAIL [{m}")
    for rel, n, frag, line in found:
        print(f"  ✗ NARR-001 {rel}:{n} — {frag!r}")
        print(f"      {line}")
    if found or st:
        if found:
            print("\nSay what the model is. If a reader needs the route, give it — \"there is no X; "
                  "use Y\". Why the alternative lost belongs in the decision record.")
        return 1
    print("OK — the spec describes the model, not its history")
    return 0


if __name__ == "__main__":
    sys.exit(main())
