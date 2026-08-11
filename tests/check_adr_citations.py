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

SCAN = ["registry/**/*.yaml", "registry/**/*.json", "registry/**/*.md",
        "docs/spec/**/*.md", "docs/flows/**/*.md"]


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

    print(f"adr-citations: {len(found)} unresolvable citation(s) "
          f"({still} baselined, {len(new)} new) · {len(local_adrs())} local ADR(s)")
    for rel, ln, num in new:
        print(f"  FAIL [ADR-CITE-001] {rel}:{ln} — cites ADR-{num}, which has no local file.")
        print(f"       If it is the control plane's, write `DCM ADR-{num}` — the numbering spaces "
              f"overlap, so a bare citation resolves to the WRONG decision for a reader who assumes "
              f"it is local.")

    # self-test: the qualification arm must actually discriminate, in both directions.
    if CITE.findall(QUALIFIED.sub("", "see DCM ADR-023 for tiers")):
        print("FAIL [ADR-SELF] a qualified `DCM ADR-023` was treated as a bare citation")
        new.append(("self-test", 0, ""))
    if not CITE.findall("see ADR-023 for tiers"):
        print("FAIL [ADR-SELF] a bare citation did not match")
        new.append(("self-test", 0, ""))

    if new:
        print(f"FAILED — {len(new)} new unresolvable ADR citation(s)")
        return 1
    print("OK — every cited ADR resolves locally or names whose it is")
    return 0


if __name__ == "__main__":
    sys.exit(main())
