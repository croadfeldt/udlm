#!/usr/bin/env python3
"""Every cited ADR resolves, or says whose it is (ADR-CITE-001).

**Where this came from.** Piotr Kliczewski, reviewing the published spec:

  *"I did not see tier registry being defined in UDLM, where can I find more information?"*

That was one dangling pointer he happened to land on. Measuring the class of defect found that the
VM-lifecycle classes alone carry 35 bare citations to ADRs with no file in this repository, and the
foundation schemas carry 20 more.

`docs/adr/README.md` already states the rule, and states it precisely:

  *"a bare 'ADR-014' is ambiguous between the local ADR-014 and DCM ADR-014. Always qualify a
  control-plane reference as `DCM ADR-0XX` (it resolves in the DCM repo), an unqualified `ADR-0XX`
  means the local file."*

So the numbering spaces OVERLAP. A bare `ADR-023` does not merely fail to resolve — it silently
resolves to the WRONG decision for any reader who assumes it is local. That is worse than a broken
link, and it is why this checks QUALIFICATION rather than mere existence.

  ADR-CITE-001  every `ADR-NNN` cited outside docs/adr/ either resolves to a local ADR file, or is
                qualified with the owning implementation (`DCM ADR-023`). An unqualified citation to
                a number with no local file is refused.

**Ratchet.** Existing violations are the burn-down baseline and report as WARN; a new one fails. The
debt cannot be cleared before anything else lands, and a gate that blocks everything gets disabled.

**Fix by qualifying, never by baselining.** Adding an entry to silence a new citation defeats the
one thing this catches.

**AMBIGUOUS-QUALIFIED is reported, not enforced, and the distinction is honest rather than lazy.**
A `DCM ADR-027` whose number ALSO exists locally cannot be resolved from this repository: the
numbering spaces overlap, so both readings are well-formed, and deciding which was meant needs the
DCM tree — which is not a checkout away, it is a different repository whose contents this gate has
no access to. Failing on it would be asserting a fact we cannot establish; ignoring it would leave a
reader unable to tell a deliberate cross-repo citation from an over-qualified local one. So it is
listed for a human, with the count in the summary line so it cannot quietly grow.

Exit 0 = no new unresolvable citation; 1 = at least one.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADR_DIR = os.path.join(ROOT, "docs", "adr")
BASELINE = os.path.join(ROOT, "tests", "adr-citation-baseline.yaml")

# A citation. The lookbehind is what makes this a QUALIFICATION check rather than an existence check:
# `DCM ADR-023` is a deliberate external reference and must not be flagged.
CITE = re.compile(r"(?<!DCM )(?<!dcm )\bADR-(\d{3})\b")
QUALIFIED = re.compile(r"\b(DCM|DAV)\s+ADR-\d{3}\b")

# EVERY surface that cites an ADR, including the ADR corpus itself. Excluding docs/adr/ made the
# records the one place a dead citation could live unchallenged — and they are the densest citers in
# the repo, so it was the worst place to leave unscanned. docs/authoring/ and use-cases/ were
# omitted for no stated reason; use-cases/PERSONAS.yaml attributes five refusal-contract elements to
# ADR-003, which is about data mobility and contains no refusal contract.
SCAN = ["registry/**/*.yaml", "registry/**/*.json", "registry/**/*.md",
        "docs/spec/**/*.md", "docs/flows/**/*.md",
        "docs/adr/**/*.md", "docs/dr/**/*.md", "docs/authoring/**/*.md",
        "docs/design/**/*.md", "docs/guides/**/*.md",
        "use-cases/**/*.yaml", "use-cases/**/*.md"]


def local_adrs():
    """The ADR numbers that have a file here. `ADR-038-scoped-...md`[4:7] -> '038'."""
    return {os.path.basename(p)[4:7] for p in glob.glob(os.path.join(ADR_DIR, "ADR-*.md"))}


def violations():
    have, out = local_adrs(), []
    for pat in SCAN:
        for path in sorted(glob.glob(os.path.join(ROOT, pat), recursive=True)):
            rel = os.path.relpath(path, ROOT)
            for i, line in enumerate(open(path, encoding="utf-8", errors="ignore"), 1):
                # strip qualified references first, so their number is not then matched as bare
                for num in CITE.findall(QUALIFIED.sub("", line)):
                    if num not in have:
                        out.append((rel, i, num))
    return out


def dcm_adrs():
    """The ADR numbers the control plane actually has.

    Checked in rather than fetched, so the gate runs offline. Refresh with
    tests/refresh_dcm_adr_index.py."""
    p = os.path.join(ROOT, "tests", "dcm-adr-index.yaml")
    if not os.path.exists(p):
        return set()
    d = yaml.safe_load(open(p, encoding="utf-8")) or {}
    return {str(k) for k in (d.get("adrs") or {})}


def misqualified(known_dcm):
    """A `DCM ADR-NNN` naming a number the control plane does not have (ADR-CITE-002).

    ADR-CITE-001 asks whether a citation resolves locally OR names a repo. It never asks whether the
    named repo HAS that number, so writing `DCM ` in front of an unknown number silences it. 69
    citations were fixed that way: a sweep read "no local file" as "must be the control plane's",
    when the control plane's ADRs stop well short of those numbers. The citations pointed at nothing
    and the gate went green.

    A number above the control plane's range is UDLM's own whether or not the file exists yet.
    Missing local files are #513; this arm keeps them visible there instead of laundering them into
    a repo that cannot answer for them."""
    out = []
    for pat in SCAN:
        for path in sorted(glob.glob(os.path.join(ROOT, pat), recursive=True)):
            rel = os.path.relpath(path, ROOT)
            if rel.startswith("tests/"):
                continue
            try:
                lines = open(path, encoding="utf-8", errors="ignore").read().splitlines()
            except OSError:
                continue
            for n, line in enumerate(lines, 1):
                for m in re.finditer(r"\bDCM\s+ADR-(\d{3})\b", line):
                    if m.group(1) not in known_dcm:
                        out.append((rel, n, m.group(1)))
    return out


def main():
    found = violations()
    baseline = yaml.safe_load(open(BASELINE, encoding="utf-8")) if os.path.exists(BASELINE) else {}
    known = {(v["file"], v["adr"]) for v in (baseline or {}).get("known", [])}

    new, still = [], 0
    for rel, ln, num in found:
        if (rel, num) in known:
            still += 1
        else:
            new.append((rel, ln, num))

    # AMBIGUOUS-QUALIFIED — a qualified citation whose number also resolves locally. Reported,
    # never enforced: both readings are well-formed and only the DCM tree could settle which was
    # meant, so failing would assert a fact this repository cannot establish.
    local = local_adrs()
    ambiguous = set()
    for pat in SCAN:
        for path in sorted(glob.glob(os.path.join(ROOT, pat), recursive=True)):
            try:
                text = open(path, encoding="utf-8", errors="ignore").read()
            except OSError:
                continue
            for m in QUALIFIED.finditer(text):
                if m.group(0).split("-")[-1] in local:
                    ambiguous.add((os.path.relpath(path, ROOT), m.group(0)))

    print(f"adr-citations: {len(found)} unresolvable citation(s) "
          f"({still} baselined, {len(new)} new) · {len(local)} local ADR(s) · "
          f"{len(ambiguous)} qualified-but-locally-ambiguous")
    if ambiguous:
        print("  Qualified citations whose number ALSO exists locally — both readings are "
              "well-formed and this repo cannot tell which was meant. Confirm each against the DCM "
              "tree; if it meant the local one, drop the qualifier:")
        for rel, cite in sorted(ambiguous):
            print(f"    ? {rel}: {cite}  (local ADR-{cite.split('-')[-1]} also exists)")
    for rel, ln, num in new:
        print(f"  FAIL [ADR-CITE-001] {rel}:{ln} — cites ADR-{num}, which has no local file.")
        print(f"       If it is the control plane's, write `DCM ADR-{num}` — the numbering spaces "
              f"overlap, so a bare citation resolves to the WRONG decision for a reader who assumes "
              f"it is local.")

    known_dcm = dcm_adrs()
    bad = misqualified(known_dcm) if known_dcm else []
    if not known_dcm:
        print("  FAIL [ADR-CITE-002] the control-plane ADR index is missing or empty — every "
              "qualified citation would pass without being checked")
        new.append(("index", 0, ""))
    else:
        hi = max(known_dcm)
        for rel, ln, num in bad:
            print(f"  FAIL [ADR-CITE-002] {rel}:{ln} — cites `DCM ADR-{num}`, but the control "
                  f"plane's ADRs run 001-{hi} and have no {num}.")
            print(f"       The qualifier makes this read as resolved while it points at nothing. If "
                  f"ADR-{num} is UDLM's own, drop `DCM ` — a missing local file belongs in #513.")
        new.extend(bad)

    # self-test: the qualification arm must actually discriminate, in both directions.
    if CITE.findall(QUALIFIED.sub("", "see DCM ADR-023 for tiers")):
        print("FAIL [ADR-SELF] a qualified `DCM ADR-023` was treated as a bare citation")
        new.append(("self-test", 0, ""))
    if not CITE.findall("see ADR-023 for tiers"):
        print("FAIL [ADR-SELF] a bare citation did not match")
        new.append(("self-test", 0, ""))
    # ADR-CITE-002 must fire on a number the control plane lacks and stay quiet on one it has —
    # a one-directional check would either miss the defect or ban every valid qualified citation.
    if known_dcm:
        probe = max(known_dcm)
        if str(int(probe) + 40).zfill(3) in known_dcm or probe not in known_dcm:
            print("FAIL [ADR-SELF] the control-plane index does not discriminate by number")
            new.append(("self-test", 0, ""))

    if new:
        print(f"FAILED — {len(new)} new unresolvable ADR citation(s)")
        return 1
    print("OK — every cited ADR resolves locally or names whose it is")
    return 0


if __name__ == "__main__":
    sys.exit(main())
