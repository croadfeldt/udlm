#!/usr/bin/env python3
"""Policy-fact vocabulary gate — the facts a policy references must be governed terms.

UDLM does not specify a policy language or engine (policy-contract §7.2a: an external engine is
"a *Provider of policy decisions*, bound by the contract, not by shared storage"). What UDLM owes an
engine is the ability to REFERENCE THE CORRECT INFORMATION — so the fact vocabulary is the
deliverable, and an ungoverned vocabulary is a broken deliverable.

It was ungoverned. The fact list lived as prose inside one field description in
`policy.schema.json`, enforced by nothing, and drifted into five disagreeing spellings across the
spec (schema `eq/ne/gte/lte` · policy-contract §2.5 `equals/not_equals/minimum/maximum` ·
layering `and/contains/not_contains` · governance-matrix `includes/minimum` · operational-models
`equals/in`). This gate is what keeps that from recurring.

Two rules:

  PFACT-001  every fact a policy record references resolves to a canonical term in
             `registry/taxonomies/policy-fact.yaml` — or to a declared OPEN subtree
             (`request-payload` admits any spec dot-path; `reserved` admits
             `reserved.<component>.<fact>`). An unresolvable fact is a policy binding to data the
             model does not carry: it can never fire, and nothing would have said so.

  PFACT-002  the taxonomy stays reachable — every term has a parent that exists, and every
             non-root term lands under exactly one of the four §2.1 source subtrees. A fact with no
             source is a fact an engine cannot bind, because the subtree IS the binding instruction.

Also prints a non-failing COVERAGE line: canonical terms no policy references. Informational — a
fact nobody consumes is a candidate for removal (the "added effectively" signal), not a failure.

Exit 0 = every referenced fact resolves; 1 = at least one does not.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(ROOT, "registry", "taxonomies", "policy-fact.yaml")
# The §2.1 match sources are the taxonomy's own direct children of the root — DERIVED, never
# restated. This was a hardcoded set of four, so adding the fifth source (`reference-graph`,
# ADR-041) made the gate reject the very terms the ADR asked for: the checker had its own copy of a
# list the vocabulary already owned, which is the defect SPEC-DESIGN §33 names.
def source_subtrees(terms, root):
    """Every direct child of the root — one match source each."""
    return {n for n, t in terms.items() if t.get("parent") == root and n != root}
# Subtrees whose members are addressed by dot-path rather than enumerated. `request-payload` admits
# any spec dot-path of the requested type (§2.1); `reserved` admits reserved.<component>.<fact>.
OPEN_SUBTREES = {"request-payload", "reserved"}


def load_vocab():
    doc = yaml.safe_load(open(VOCAB, encoding="utf-8")) or {}
    terms = {t["term"]: t for t in (doc.get("terms") or []) if isinstance(t, dict) and t.get("term")}
    return terms


def governed_prefixes(terms):
    """The dotted heads the vocabulary itself governs — `graph`, `quota`, `operation`,
    `composition`. DERIVED from the canonical terms rather than listed, so a new governed family
    is covered the moment its first term lands."""
    return {t.split(".")[0] for t in terms if "." in t}


def resolves(fact, terms):
    """A fact resolves if it is a canonical term, or sits under an OPEN subtree by dot-path.

    **The governed-prefix arm exists because the open subtree used to swallow everything.**
    `request-payload` admits ANY spec dot-path — a consumer field, a custom tag — so the old last
    line returned True for every dotted name whose head was not itself a term. Since a canonical
    term is the FULL dotted string (`graph.has_cycle`), the head never is one, and so
    `graph.has_cyle` — or `composition.unreadable_constituent`, singular — resolved as "some
    request-payload path" and the gate reported clean. A typo in a governed fact is precisely the
    case PFACT-001 exists to catch, and it was the one case it could not see.

    So: if the head names a governed family, the full fact MUST be canonical. Only a head the
    vocabulary does not govern falls through to the open surface."""
    if fact in terms:
        return True
    head = fact.split(".")[0]
    if head in OPEN_SUBTREES and head in terms:
        return True
    if "." not in fact:
        return False                      # a bare unknown name is not a spec dot-path
    if head in governed_prefixes(terms):
        return False                      # governed family, unknown member -> a typo, not a payload
    return "request-payload" in terms


def main():
    if not os.path.exists(VOCAB):
        print(f"FAILED — the policy-fact vocabulary is missing: {os.path.relpath(VOCAB, ROOT)}")
        return 1
    terms = load_vocab()
    sources = source_subtrees(terms, "policy-fact")
    fails, referenced = [], set()

    # PFACT-002 — the taxonomy is reachable and every fact has a source
    for name, t in terms.items():
        parent = t.get("parent")
        if name == "policy-fact":
            continue
        if parent is None:
            fails.append(f"PFACT-002: term '{name}' has no parent — only the root may be parentless")
            continue
        if parent not in terms:
            fails.append(f"PFACT-002: term '{name}' has dangling parent '{parent}'")
            continue
        if parent != "policy-fact":
            # walk to the source subtree
            cur, seen = parent, set()
            while cur in terms and cur not in sources and cur != "policy-fact":
                if cur in seen:
                    fails.append(f"PFACT-002: term '{name}' has a cyclic parent chain")
                    break
                seen.add(cur)
                cur = terms[cur].get("parent")
            if cur not in sources:
                fails.append(f"PFACT-002: term '{name}' does not land under any §2.1 source subtree "
                             f"({', '.join(sorted(sources))}) — an engine cannot bind a fact with "
                             f"no source, because the subtree IS the binding instruction")

    # PFACT-001 — every fact a policy references resolves
    checked = 0
    for f in glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True) + \
             glob.glob(os.path.join(ROOT, "registry", "**", "*.json"), recursive=True):
        if "taxonomies" in f or "generated" in f:
            continue
        try:
            docs = list(yaml.safe_load_all(open(f, encoding="utf-8")))
        except Exception:
            continue
        rel = os.path.relpath(f, ROOT)
        for doc in docs:
            if not (isinstance(doc, dict) and doc.get("record_type") == "policy"):
                continue
            for fact in _facts(doc.get("match")):
                checked += 1
                referenced.add(fact)
                if not resolves(fact, terms):
                    fails.append(f"PFACT-001 {rel}: policy references fact '{fact}', which is not a "
                                 f"canonical policy-fact term and sits under no open subtree")

    canonical = {n for n, t in terms.items()
                 if n != "policy-fact" and n not in sources}
    unused = sorted(canonical - referenced)
    print(f"policy-facts: {len(terms)} term(s) · {checked} reference(s) checked · "
          f"{len(unused)} term(s) referenced by no policy")
    if unused:
        print(f"  COVERAGE (informational): {', '.join(unused[:12])}"
              f"{' …' if len(unused) > 12 else ''}")
    if fails:
        for m in fails:
            print(f"  {m}")
        print(f"FAILED — {len(fails)} violation(s)")
        return 1
    print("OK — every referenced fact resolves; every term has a source subtree")
    return 0


def _facts(match):
    """Pull the referenced fact names out of a policy's match block, whatever shape it carries.

    Deliberately shape-tolerant: this gate is about the VOCABULARY, and it must keep working across
    the match block's reshaping rather than pin the schema in place from a test.
    """
    if not isinstance(match, dict):
        return
    if isinstance(match.get("facts"), list):
        for f in match["facts"]:
            if isinstance(f, str):
                yield f
    for cond in (match.get("conditions") or []):
        if isinstance(cond, dict) and isinstance(cond.get("field"), str):
            yield cond["field"]
    for key in ("all_of", "any_of"):
        for cond in (match.get(key) or []):
            if isinstance(cond, dict) and isinstance(cond.get("field"), str):
                yield cond["field"]


if __name__ == "__main__":
    sys.exit(main())
