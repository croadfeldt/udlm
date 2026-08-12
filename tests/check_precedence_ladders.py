#!/usr/bin/env python3
"""No document invents a third ordering ladder (LAD-001).

There are exactly **two** ordering axes, they are independent, and every layer carries both:

    precedence   WHERE in the merge order — who overrides whom
                 base ▸ core ▸ intermediate ▸ service ▸ request ▸ policy   (`precedence_class`)
    domain       WHOSE authority sets it
                 system ▸ platform ▸ tenant ▸ resource_type ▸ entity       (`policy_domain`)

They vary independently and the corpus proves it: `base` appears at both `platform` and
`resource_type` authority, `intermediate` at both `platform` and `tenant`.

**How this went wrong, which is why the gate is narrow rather than absent.** ADR-015 set out to
merge three vocabularies into one and proposed a seventh-tier line —
`base ▸ module ▸ profile ▸ org ▸ domain ▸ tenant ▸ resource` — that FUSED the two axes. It could not
be built: a flattened line cannot express `base`-order-with-`tenant`-authority, so the unification
would have lost information rather than removed duplication. Meanwhile `profile-resolution.md` §1
carried a fourth, shorter ladder (`resource_type → tenant → group → platform`) that is neither axis.
So a decision whose entire purpose was "one vocabulary, not three" left four in the tree.

  LAD-001  a document states an ordered tier sequence — `a ▸ b ▸ c`, `a → b → c` — over ordering
           vocabulary, whose members are not exactly one of the two declared axes. A sequence
           MIXING members of both axes is the specific failure, because that is the fusion.

**Deliberately narrow.** Naming the tiers is fine and constant: prose says "a core layer overrides a
base layer" all the time. This fires only on an ORDERED SEQUENCE of three or more, which is the form
that reads as a ladder definition. ADRs are exempt — a record narrating the ladder it rejected is
doing its job.

Exit 0 = no document defines an ordering ladder that is not one of the two.
"""
import glob
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMMON = os.path.join(ROOT, "registry", "common-elements.schema.json")
LAYER = os.path.join(ROOT, "registry", "layer.schema.json")

# A sequence of >=3 tier-ish words joined by ladder arrows. Backticks and bold are stripped first,
# so `base` ▸ **core** ▸ intermediate reads the same as base ▸ core ▸ intermediate.
SEQ = re.compile(r"([a-z_]+(?:\s*(?:▸|→|->|›)\s*[a-z_]+){2,})")
STRIP = re.compile(r"[`*]")

EXCLUDE_PREFIX = ("docs/adr/", "docs/dr/", "tests/", "docs/internal/")
EXCLUDE_EXACT = {"AGENTS.md", "CLAUDE.md"}


def axes():
    """The two declared axes, read from their single homes — never restated here, which is the
    defect this gate exists to prevent, one level up."""
    dom = json.load(open(COMMON, encoding="utf-8"))["$defs"]["policy_domain"]["enum"]
    prec = json.load(open(LAYER, encoding="utf-8"))["properties"]["precedence_class"]["enum"]
    return {"domain": set(dom), "precedence": set(prec)}


def tracked():
    out = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True,
                         check=True, cwd=ROOT).stdout
    for p in out.splitlines():
        if p in EXCLUDE_EXACT or p.startswith(EXCLUDE_PREFIX):
            continue
        yield p


def classify(members, ax):
    """Which axis a sequence belongs to: 'domain', 'precedence', 'mixed', or None if it is not
    ordering vocabulary at all (an ordinary prose arrow chain — most of what SEQ matches)."""
    d = len(members & ax["domain"])
    p = len(members & ax["precedence"])
    if d and p:
        return "mixed"
    if d and d >= 2:
        return "domain"
    if p and p >= 2:
        return "precedence"
    return None


def main():
    ax = axes()
    fails, scanned, seqs = [], 0, 0

    for rel in tracked():
        scanned += 1
        try:
            lines = open(os.path.join(ROOT, rel), encoding="utf-8").read().splitlines()
        except OSError:
            continue
        for n, raw in enumerate(lines, 1):
            line = STRIP.sub("", raw)
            for m in SEQ.finditer(line):
                members = {w.strip() for w in re.split(r"▸|→|->|›", m.group(1))}
                kind = classify(members, ax)
                if kind is None:
                    continue
                seqs += 1
                if kind == "mixed":
                    fails.append(
                        f"LAD-001 {rel}:{n} — {m.group(1).strip()!r} fuses the two axes "
                        f"(precedence: {sorted(members & ax['precedence'])}, "
                        f"domain: {sorted(members & ax['domain'])}). They vary independently, so a "
                        f"flattened line cannot express one axis's tier at another's authority.")
                    continue
                extra = members - ax[kind]
                if extra:
                    fails.append(
                        f"LAD-001 {rel}:{n} — {m.group(1).strip()!r} reads as the {kind} ladder but "
                        f"names {sorted(extra)}, which is not on it. The two axes are declared in "
                        f"common-elements (`policy_domain`) and layer.schema.json "
                        f"(`precedence_class`); a third ladder is a fourth vocabulary.")

    # Self-test: each arm on a planted case, and the axes must have actually loaded.
    st = []
    if not (ax["domain"] and ax["precedence"]):
        st.append("LAD-SELF an axis loaded empty — every check would be vacuous")
    if classify({"base", "core", "tenant"}, ax) != "mixed":
        st.append("LAD-SELF a fused sequence is not detected as mixed")
    if classify({"base", "core", "intermediate"}, ax) != "precedence":
        st.append("LAD-SELF the precedence ladder is not recognised")
    if classify({"resource_type", "tenant", "group"}, ax) != "domain":
        st.append("LAD-SELF a domain-ish ladder with a foreign tier is not recognised as domain "
                  "— the extra-member arm would never fire")
    if classify({"read", "write", "delete"}, ax) is not None:
        st.append("LAD-SELF an ordinary prose arrow chain is read as a ladder")

    print(f"precedence ladders: {scanned} document(s), {seqs} ordering sequence(s) checked "
          f"against the two declared axes")
    for m in st:
        print(f"  FAIL [{m}")
    for m in fails:
        print(f"  ✗ {m}")
    if fails or st:
        return 1
    print("OK — every ordering ladder is one of the two declared axes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
