#!/usr/bin/env python3
"""The normative tier names no implementation (IMP-001) — the gate Piotr's review asked for.

**Where this came from.** Six times across three review PRs on dcm-project/udlm, one reviewer made the
same structural objection and nothing in CI could see it:

  *"it is udlm we should not talk about any of the implementations (DCM)"*
  *"please do not refer to DCM. it is a data model and should not reason about the implementation"*
  *"this is DCM specific, let's remove it from here"*
  *"we should not talk about how dcm implements udlm here"*

The glossary already states the rule — *"UDLM is defined, validated, and used independently of any
implementation. Where DCM or DAV are named, they are examples, never requirements"* — and 509 lines
across 44 normative files name one anyway. A rule nothing checks is indistinguishable from a rule nobody
wrote (DR-UDLM-002).

  IMP-001  a file under docs/spec/ does not name an implementation, unless the line marks it
           NON-NORMATIVE. The exemption is the point rather than a loophole: the glossary's own
           definition of DCM is a legitimate naming, and so is "DCM realizes this — non-normative
           example". What is not legitimate is a normative sentence whose subject is an
           implementation, because a conformant peer that is not that implementation cannot read it.

**Ratchet, not a wall.** 509 existing lines are the burn-down baseline and report as WARN. A NEW
reference fails CI. The alternative — failing on all 509 — would mean either a 44-file sweep before
anything else lands, or the gate being disabled the first time it blocked someone.

**Why line-level and not file-level.** A file that legitimately names DCM once in a background note
should not become blanket-exempt for the sentence somebody adds next month.

Exit 0 = no new implementation reference; 1 = at least one.
"""
import glob
import hashlib
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPEC = os.path.join(ROOT, "docs", "spec")
BASELINE = os.path.join(ROOT, "tests", "implementation-neutrality-baseline.yaml")

# The named implementations (GLOSSARY.md). DAV is included for the same reason DCM is: the case
# study rules that "UDLM does not depend on DAV", and a spec sentence about DAV breaks that.
IMPLS = re.compile(r"\b(DCM|DAV)\b")

# A line that MARKS itself non-normative is fine. This is the sanctioned form, and it is deliberately
# generous: the goal is that a reader can tell an example from a requirement, not that the word never
# appears. `croadfeldt/dcm` and similar repo pointers are addresses, not claims about behaviour.
EXEMPT = re.compile(
    r"non-normative|informative|for example|e\.g\.|illustrat|example implementation"
    r"|reference implementation|such as|croadfeldt/|dcm-project/|github\.com"
    r"|GLOSSARY|see \[|\]\(",
    re.I)


def violations():
    out = []
    for path in sorted(glob.glob(os.path.join(SPEC, "**", "*.md"), recursive=True)):
        rel = os.path.relpath(path, ROOT)
        for i, line in enumerate(open(path, encoding="utf-8"), 1):
            if IMPLS.search(line) and not EXEMPT.search(line):
                out.append((rel, i, line.strip()[:110]))
    return out


def _key(text):
    """The baseline stores a HASH of the line, never the line.

    Storing the text made the baseline a second copy of spec content — and the estate-token gate
    caught it doing exactly that, flagging a denylisted token the baseline had copied out of a
    document. A baseline is an identity ledger, not an archive: it needs to recognise a line, not
    reproduce it."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def main():
    found = violations()
    baseline = {}
    if os.path.exists(BASELINE):
        baseline = yaml.safe_load(open(BASELINE, encoding="utf-8")) or {}
    # keyed on (file, text) rather than line number: a reference that merely MOVED within its file is
    # the same debt, and keying on the line would fail CI for an unrelated edit above it.
    known = {(v["file"], v["hash"]) for v in baseline.get("known", [])}

    new, still = [], 0
    for rel, ln, text in found:
        if (rel, _key(text)) in known:
            still += 1
        else:
            new.append((rel, ln, text))

    fixed = len(known) - still

    print(f"implementation-neutrality: {len(found)} implementation reference(s) in the normative tier "
          f"({still} baselined, {len(new)} new)")
    if fixed > 0:
        print(f"  {fixed} baseline entr(y/ies) no longer present — shrink the baseline (STALE)")
    for rel, ln, text in new:
        print(f"  FAIL [IMP-001] {rel}:{ln} — names an implementation in a normative sentence")
        print(f"       {text}")
        print(f"       If this is an example, say so on the line. If it is a requirement, it belongs "
              f"to the implementation, not the spec.")

    # self-test: both arms must behave, or this proves only that the walk ran.
    probe_hit = IMPLS.search("DCM evaluates the policy") and not EXEMPT.search("DCM evaluates the policy")
    probe_ok = EXEMPT.search("DCM realizes this (non-normative example)")
    if not probe_hit:
        print("FAIL [IMP-SELF] a bare normative reference did not trip the check")
        new.append(("self-test", 0, ""))
    if not probe_ok:
        print("FAIL [IMP-SELF] a marked non-normative reference was not exempted")
        new.append(("self-test", 0, ""))

    if new:
        print(f"FAILED — {len(new)} new implementation reference(s)")
        return 1
    print("OK — no new implementation reference in the normative tier")
    return 0


if __name__ == "__main__":
    sys.exit(main())
