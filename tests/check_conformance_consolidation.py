#!/usr/bin/env python3
"""§6 must not be shorter than the conformance lists it consolidates.

`CONFORMANCE.md` §6 says it consolidates the MUSTs of the contract documents it links. Five of those
documents carry their own section titled "Validation rules (conformance checks)", opening "A
conformant implementation MUST:" — an explicit, authoritative list.

They disagreed. Errors listed nine and §6 carried four; Retries listed seven and §6 carried five;
Rate limits listed seven and §6 carried four. The missing ones were not narration — among them the
403-over-404 existence-hiding posture, without which every refusal is an existence oracle. An
implementation conforming to §6 as it stood would have shipped one and believed itself compliant.

  CNS-001  the §6 area for a contract document carries at least as many requirements as that
           document's own conformance list.

**A requirement stated in two source documents is numbered once.** `retry_after_seconds` appears in
both `retry-semantics.md` and `rate-limit-and-backpressure.md`; `WIR-021` owns it, and a second row
under Rate limits would be a second definition of one requirement. Those cross-references are listed
explicitly in `CROSS_REFERENCED` below, so an area whose count is legitimately short is accounted for
by name rather than by a tolerance.

**This is a floor check, not a coverage check, and the difference matters.** It compares counts. It
cannot tell whether the rows cover the right requirements — the Errors gap was found by reading, and
nothing mechanical would have found it. What this catches is the *regression*: a source document
gains a conformance bullet and §6 does not. That is the failure mode a one-time audit cannot prevent,
and it is worth a gate precisely because the audit is expensive to repeat.

A spurious failure is possible — splitting one bullet into two trips it without changing what is
required. The correct response is to re-read the area, which is the behaviour wanted anyway; the fix
is never to raise the number to match.

Exit 0 = every area meets its floor; 1 = at least one is short.
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# area heading in §6 -> the contract document whose conformance list it consolidates.
# Only documents carrying an explicit conformance section appear; the others have no floor to meet.
AREAS = {
    "Identifiers": "docs/spec/contracts/identifier-scheme.md",
    "Time": "docs/spec/contracts/time-and-clock.md",
    "Errors": "docs/spec/contracts/error-model.md",
    "Retries": "docs/spec/contracts/retry-semantics.md",
    "Rate limits": "docs/spec/contracts/rate-limit-and-backpressure.md",
    "Events": "docs/spec/contracts/event-catalog.md",
}
# A requirement stated in TWO source documents is numbered ONCE — a second row would be a second
# definition of one requirement, which is the drift the rule registry exists to prevent. Where that
# leaves an area's count below its source list, the cross-reference is recorded here with the id that
# does own it, so the shortfall is accounted for rather than absorbed by a fudge factor.
CROSS_REFERENCED = {
    ("Rate limits", "WIR-021"): "rate-limit-and-backpressure.md restates 'Honor retry_after_seconds', "
                                "which retry-semantics.md owns and WIR-021 numbers.",
}
# Two documents name their own conformance list differently: most use "Validation rules
# (conformance checks)", event-catalog.md uses "System Policies". Matching only the first left
# Events unchecked, and §6 was carrying 3 of that document's 7 rules when nothing was watching.
_SECTION = re.compile(r"^#+\s*[\d.]*\s*(Validation rules \(conformance checks\)|System Policies)\s*$", re.M)
_ROW = re.compile(r"^\| `(WIR-[\d.]+)` \|")


def area_rows():
    s = open(os.path.join(ROOT, "CONFORMANCE.md"), encoding="utf-8").read()
    i = s.index("## 6. Wire-compatibility checklist")
    j = s.index("## 8", i)
    out, area = {}, None
    for line in s[i:j].split("\n"):
        if line.startswith("### "):
            area = line[4:].split(" (")[0].strip()
        m = _ROW.match(line)
        if m:
            out.setdefault(area, []).append(m.group(1))
    return out


def source_requirements(rel):
    """The bullets of a document's own conformance list. A link-list bullet (`- [RFC …`) is a
    reference, not a requirement."""
    path = os.path.join(ROOT, rel)
    if not os.path.exists(path):
        return None
    t = open(path, encoding="utf-8").read()
    m = _SECTION.search(t)
    if not m:
        return None
    nxt = t.find("\n## ", m.end())
    body = t[m.end():nxt if nxt > 0 else len(t)]
    bullets = [l for l in body.split("\n")
               if l.strip().startswith("- ") and not l.strip().startswith("- [")]
    # a document may state its conformance list as a rule TABLE rather than bullets
    rows = [l for l in body.split("\n") if re.match(r"^\| `[A-Z][A-Z0-9-]+-\d{3}` \|", l.strip())]
    return bullets or rows


def main():
    rows = area_rows()
    fails, checked = [], 0
    for area, rel in sorted(AREAS.items()):
        reqs = source_requirements(rel)
        if reqs is None:
            fails.append(f"CNS-001 {area}: {rel} has no 'Validation rules (conformance checks)' "
                         f"section — either it was renamed, or this mapping is stale")
            continue
        checked += 1
        xrefs = [k for k in CROSS_REFERENCED if k[0] == area]
        have = len(rows.get(area, [])) + len(xrefs)
        if have < len(reqs):
            fails.append(f"CNS-001 {area}: §6 carries {have} requirement(s); "
                         f"{os.path.basename(rel)}'s own conformance list states {len(reqs)}. "
                         f"Re-read the area — the fix is a missing requirement, never a raised count")

    # self-test: the comparison must be able to fail, or the gate only proves the walk ran
    if not (len(source_requirements("docs/spec/contracts/error-model.md") or []) > 0):
        print("FAIL [CNS-SELF] the source-list parser found nothing where a list exists")
        fails.append("self-test")

    print(f"conformance-consolidation: {checked} area(s) checked against their source's own "
          f"conformance list")
    for area, rel in sorted(AREAS.items()):
        reqs = source_requirements(rel) or []
        x = [k[1] for k in CROSS_REFERENCED if k[0] == area]
        note = f"  (+{len(x)} owned elsewhere: {', '.join(x)})" if x else ""
        print(f"  {area:14s} §6 {len(rows.get(area, [])):2d}  source {len(reqs):2d}{note}")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} area(s) shorter than the list they consolidate")
        return 1
    print("OK — no area is shorter than the conformance list it consolidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
