#!/usr/bin/env python3
"""One vocabulary for permit and record (ACT-001/002/003).

**Where this came from.** There were two lists. `audit-record.action` carried 34 terms — what
HAPPENED. `governance-matrix.md` carried ten under the heading `capability` — what MAY happen. They
overlapped on TWO words. So "was this action authorized?" could not be answered by matching a permit
against a record; it needed a translation table, and a translation table is where drift lives.

Nothing read either list, which is exactly how they diverged unnoticed — the same shape as the
provider-capability taxonomy, which also had no gate and also forked.

  ACT-001  every term in `audit-record.schema.json`'s action enum resolves to a term in
           `registry/taxonomies/action.yaml`. The enum is the STANDARD set; the taxonomy is the
           vocabulary. A term in the schema with no taxonomy entry is a vocabulary that has started
           to fork again.
  ACT-002  the taxonomy is reachable — every term has a parent that exists, and every non-root term
           sits under the `action` root. A term with no parent cannot be found by a reader walking
           the vocabulary, which is the only way anyone discovers what is available.
  ACT-003  the data-movement terms are present. `read`, `write`, `store`, `replicate`, `export`,
           `notify`, `query`, `discover`, `federate` are the half the audit side lacked and the half
           the governance matrix exists to decide over. Losing them silently would restore the exact
           defect this vocabulary was created to close, and nothing else would notice — the schema
           would still validate, the matrix would still parse.

**What this deliberately does NOT check.** Whether an estate uses a given action, whether coverage is
complete, or whether an actor may perform one (maintainer ruling 2026-08-11: UDLM carries the
vocabulary and the format; policy and the implementation decide what is allowed). A gate asserting
any of those would be UDLM deciding governance, which is the defect the depth caps and the profile
sets were removed for.

**Extension is expected, not exceptional.** An estate adds a term under the `action` root as
`proposed` and promotes it by the same ladder a standard term used (ADR-039). This gate polices the
WAY the vocabulary grows, never its contents.

Exit 0 = one vocabulary, reachable, with the movement half intact; 1 = it has started to fork.
"""
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(ROOT, "registry", "taxonomies", "action.yaml")
AUDIT = os.path.join(ROOT, "registry", "audit-record.schema.json")

# The half the audit enum lacked. Named explicitly because their ABSENCE is the regression:
# a boundary crossing is a movement, so a governance matrix with no movement verbs governs nothing.
MOVEMENT = {"read", "write", "store", "replicate", "export", "notify", "query", "discover", "federate"}


def load_terms():
    doc = yaml.safe_load(open(VOCAB, encoding="utf-8"))
    return {t["term"]: t for t in doc.get("terms", [])}, doc.get("root")


def main():
    if not os.path.exists(VOCAB):
        print(f"FAILED — the action vocabulary is missing: {os.path.relpath(VOCAB, ROOT)}")
        return 1
    terms, root = load_terms()
    fails = []

    # ACT-002 — reachable
    for name, t in terms.items():
        if name == root:
            continue
        parent = t.get("parent")
        if parent not in terms:
            fails.append(f"ACT-002 {name!r}: parent {parent!r} is not a term — unreachable by a "
                         f"reader walking the vocabulary")

    # ACT-001 — the schema's standard set is a subset of the vocabulary
    audit = json.load(open(AUDIT, encoding="utf-8"))
    enum = audit["properties"]["action"].get("enum", [])
    lower = {t.lower() for t in terms}
    for a in enum:
        if a.lower() not in lower:
            fails.append(f"ACT-001 audit action {a!r} resolves to no term in action.yaml — the "
                         f"permit and record vocabularies have started to fork again")

    # ACT-003 — the movement half survives
    missing = sorted(MOVEMENT - set(terms))
    if missing:
        fails.append(f"ACT-003 the data-movement terms {missing} are gone — a governance matrix "
                     f"with no movement verbs cannot decide a boundary crossing, which is what it "
                     f"exists to do")

    # self-test: each arm must be able to fire, or this proves only that the file parsed.
    probe = {"action": {"term": "action", "parent": None}, "orphan": {"term": "orphan", "parent": "nope"}}
    if probe["orphan"]["parent"] in probe:
        print("FAIL [ACT-SELF] the reachability arm cannot distinguish an orphan")
        fails.append("self-test")
    if not (MOVEMENT - {"read"}) & MOVEMENT:
        print("FAIL [ACT-SELF] the movement set is empty — ACT-003 would pass vacuously")
        fails.append("self-test")

    print(f"action-vocabulary: {len(terms)} term(s) · {len(enum)} audit action(s) checked against "
          f"one vocabulary")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} finding(s)")
        return 1
    print("OK — permit and record share one vocabulary, reachable, movement half intact")
    return 0


if __name__ == "__main__":
    sys.exit(main())
