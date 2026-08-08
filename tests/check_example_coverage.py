#!/usr/bin/env python3
"""Every worked example says what it proves — and the gaps are visible.

A worked example that parses proves the parser works. Rule 36 requires one per type, so the repo has
plenty; nothing said what any of them demonstrated, which meant nobody could answer "is this rule
exercised anywhere?" without reading all of them and guessing.

Each example carries a comment header naming the rules it demonstrates:

    # asserts: TEN-001, GRP-INV-001
    # proves: a tenant IS a Grouping.Tenant, and its membership derives rather than being stored

**Why a comment and not a field.** Every instance schema is `additionalProperties: false` at the top
level and inside `metadata`, so an example cannot carry an extra key without amending 17 schemas —
which would put corpus bookkeeping into the wire contract every peer implements. The citation is
about the *artifact*, not the *record*; it belongs beside the record, not in it.

  ECV-001  a cited rule ID resolves to a real rule family — one registered in the rule-ID registry,
           or one a gate defines. A citation to a rule that cannot exist is worse than none, because
           it reads as coverage.
  ECV-002  an annotated example states what it proves, not only which rule. The prose is the half a
           reader uses; a bare ID restates the filename.

**Two families of ID, both real.** Normative rules are registered (`registry/rule-id-registry.yaml`);
gate-local IDs (`OFR-001`, `GRD-001`, `MRJ-001`) are defined by the check that raises them and are
not, because the registry governs the normative surface. Both are accepted here, and a prefix
belonging to neither is a typo.

A multi-segment family (`GRP-INV-001`) is matched on its leading segment, which is what
`check_single_source` already does — the registry schema forbids registering the full prefix, so the
leading segment is the registered family by default rather than by decision. That is a governance
hole; this gate follows the repository's actual behaviour rather than enforcing a stricter rule it
would be alone in applying.

Annotation is a **ratchet, not a wall**. Un-annotated examples are counted and listed, never failed:
the backlog burns down, and meanwhile the count is the honest coverage number nobody had. New
examples should arrive annotated — that is a review question, not something this gate can know.

Exit 0 = every annotation is well-formed; 1 = at least one is not.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(ROOT, "registry", "examples")
REGISTRY = os.path.join(ROOT, "registry", "rule-id-registry.yaml")

_ASSERTS = re.compile(r"^#\s*asserts:\s*(.+)$", re.M)
_PROVES = re.compile(r"^#\s*proves:\s*(.+)$", re.M)
_RULE = re.compile(r"^([A-Z][A-Z0-9]{1,5}(?:-[A-Z]+)?)-\d{3}$")


def registered_prefixes():
    d = yaml.safe_load(open(REGISTRY, encoding="utf-8")) or {}
    return {p["prefix"] for p in d.get("prefixes") or []}


def gate_defined_prefixes():
    """Prefixes a gate raises but the registry does not govern — the registry covers the normative
    surface, and a gate-local rule is not part of it."""
    out = set()
    for path in glob.glob(os.path.join(ROOT, "tests", "*.py")) + \
            glob.glob(os.path.join(ROOT, "registry", "tools", "*.py")):
        for m in re.finditer(r"\b([A-Z][A-Z0-9]{1,5})-\d{3}\b", open(path, encoding="utf-8").read()):
            out.add(m.group(1))
    return out


def main():
    prefixes = registered_prefixes() | gate_defined_prefixes()
    files = [p for p in sorted(glob.glob(os.path.join(EXAMPLES, "*.yaml")))]
    annotated, bare, fails, cited = [], [], [], set()

    for p in files:
        rel = os.path.relpath(p, ROOT)
        head = "".join(open(p, encoding="utf-8").readlines()[:6])
        m = _ASSERTS.search(head)
        if not m:
            bare.append(rel)
            continue
        annotated.append(rel)
        rules = [r.strip() for r in m.group(1).split(",") if r.strip()]
        if not rules:
            fails.append(f"ECV-002 {rel}: `asserts:` is empty")
        for r in rules:
            mm = _RULE.match(r)
            if not mm:
                fails.append(f"ECV-001 {rel}: {r!r} is not a rule ID")
                continue
            lead = mm.group(1).split("-")[0]
            if mm.group(1) not in prefixes and lead not in prefixes:
                fails.append(f"ECV-001 {rel}: prefix {mm.group(1)!r} of {r} is not registered — "
                             f"a citation to a rule that cannot exist reads as coverage")
                continue
            cited.add(r)
        if not _PROVES.search(head):
            fails.append(f"ECV-002 {rel}: cites {', '.join(rules)} but does not say what it proves. "
                         f"The prose is the half a reader uses.")

    # self-test: the gate must be able to reject a bad citation, or it only proves the loop ran
    if _RULE.match("NOTARULE") or _RULE.match("xyz-001"):
        print("FAIL [ECV-SELF] the rule-ID pattern accepted a non-rule")
        fails.append("self-test")

    print(f"example-coverage: {len(annotated)} of {len(files)} example(s) annotated, "
          f"{len(cited)} distinct rule(s) demonstrated")
    for rel in bare:
        print(f"  (unannotated) {rel}")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} malformed annotation(s)")
        return 1
    print("OK — every annotation is well-formed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
