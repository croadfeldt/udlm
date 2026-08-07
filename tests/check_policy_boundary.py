#!/usr/bin/env python3
"""Policy-engine boundary gate — UDLM carries the contract, never the predicate language.

policy-contract §7.2a: an external engine "is, in effect, a *Provider of policy decisions*, bound by
the contract, not by shared storage." That was doctrine the model did not hold to: the schema
specified the engine's comparison vocabulary (`eq/ne/in/not_in/exists/not_exists/matches/gt/lt/gte/
lte`), which is engine mechanism living in the data model — the same boundary ADR-008 keeps for
access determination and the drift ruling keeps for actions.

Being unenforced is what let it fork into five disagreeing spellings across the spec. Removing it
without a gate would simply invite it back, one convenience field at a time, so:

  PBND-001  no predicate-operator vocabulary in the policy schema. A comparison operator enum on a
            match/condition surface is the engine's language, not UDLM's.
  PBND-002  no `condition_logic` / boolean-composition surface. Composition is how predicates
            combine — also the engine's. (The removed `all_of`/`any_of` could not nest anyway:
            `$defs/condition` was flat with additionalProperties:false. It shipped as capability
            and functioned as decoration.)
  PBND-003  a policy's `match` declares FACTS, and every declared fact resolves in the policy-fact
            taxonomy. Enforced in full by tests/check_policy_facts.py; asserted here as a
            structural floor so the two gates cannot both be satisfied by an empty match.

Deliberately NOT flagged: the `output`/decision shapes. What a policy PRODUCES is UDLM's — the
schema specifies it per `policy_type` (validation -> decision, placement -> constraints,
override -> scope + expires_at) and that is the contract's other half.

Exit 0 = the boundary holds; 1 = engine mechanism has re-entered the model.
"""
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA = os.path.join(ROOT, "registry", "policy.schema.json")

# Spellings seen in the wild across the five drifted vocabularies. Matching on VALUES rather than on
# a key name, because the key is the easy thing to rename and the vocabulary is the actual smell.
OPERATOR_TOKENS = {
    "eq", "ne", "gt", "lt", "gte", "lte", "in", "not_in", "exists", "not_exists", "matches",
    "equals", "not_equals", "minimum", "maximum", "contains", "not_contains", "starts_with",
    "ends_with", "includes", "excludes", "regex", "like",
}
COMPOSITION_KEYS = {"condition_logic", "all_of", "any_of", "none_of", "not"}
# `operator` is the obvious carrier; these are the renames that would smuggle it back.
PREDICATE_KEY_HINTS = {"operator", "op", "comparator", "comparison", "predicate", "test"}

fails = []


def walk(node, path=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield path, k, v
            yield from walk(v, f"{path}.{k}" if path else k)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk(v, f"{path}[{i}]")


def check_schema():
    d = json.load(open(SCHEMA, encoding="utf-8"))
    for path, key, val in walk(d):
        # PBND-001 — an enum of comparison operators, under any key name
        if key == "enum" and isinstance(val, list):
            vals = {str(v) for v in val}
            hits = vals & OPERATOR_TOKENS
            # >=3 overlapping tokens is a comparison vocabulary; fewer may be a legitimate enum
            # that happens to share a word (e.g. a state named "in").
            if len(hits) >= 3:
                fails.append(f"PBND-001 policy.schema.json:{path}: enum is a predicate-operator "
                             f"vocabulary {sorted(hits)} — the comparison language is the engine's "
                             f"(§7.2a), not UDLM's")
        # PBND-001 — a property literally named for a comparison
        if key in PREDICATE_KEY_HINTS and isinstance(val, dict) and ("enum" in val or "type" in val):
            if ".properties" in path or path.endswith("properties"):
                fails.append(f"PBND-001 policy.schema.json:{path}.{key}: a predicate property has "
                             f"re-entered the schema — UDLM declares which FACTS a policy reads, "
                             f"never how it compares them")
        # PBND-002 — boolean composition
        if key in COMPOSITION_KEYS and (".properties" in path or path.endswith("properties")):
            fails.append(f"PBND-002 policy.schema.json:{path}.{key}: boolean composition is how "
                         f"predicates combine — also the engine's")


def check_records():
    """PBND-003 — a policy's match declares facts, structurally."""
    checked = 0
    for f in glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True):
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
            checked += 1
            m = doc.get("match")
            if not isinstance(m, dict) or not m.get("facts"):
                fails.append(f"PBND-003 {rel}: policy match declares no facts — a policy that names "
                             f"no data it reads cannot be impact-analyzed or refused when the data "
                             f"is absent")
            for legacy in COMPOSITION_KEYS | {"conditions"}:
                if isinstance(m, dict) and legacy in m:
                    fails.append(f"PBND-003 {rel}: match carries '{legacy}' — the predicate surface "
                                 f"was removed; the comparison belongs in match.rule, opaque to UDLM")
    return checked


# Surfaces that carry a predicate but are NOT the policy contract: a layer's activation condition
# and a conditional dependency's condition are evaluated by DCM's assembly engine, not by a policy
# engine. They raise the same boundary question — a predicate language living in the data model —
# but answering it is a separate ruling, not a silent sweep inside a policy PR. Neither is
# schema-backed (the only schema mention is an exclusion-reason enum VALUE,
# `activation_condition_false`), so nothing here is load-bearing today. Tracked as its own finding.
OUT_OF_SURFACE = {
    "docs/spec/foundations/layering-and-versioning.md",
    "docs/spec/foundations/layering-and-versioning-annex.md",
    "docs/spec/foundations/service-dependencies.md",
}


def check_prose():
    """The removal is not done while the docs still teach the removed vocabulary."""
    for f in glob.glob(os.path.join(ROOT, "docs", "spec", "**", "*.md"), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.replace(os.sep, "/") in OUT_OF_SURFACE:
            continue
        text = open(f, encoding="utf-8").read()
        for m in re.finditer(r"^\s*(?:-\s*)?operator:\s*([a-z_]+)", text, re.M):
            if m.group(1) in OPERATOR_TOKENS:
                line = text[:m.start()].count("\n") + 1
                fails.append(f"PBND-001 {rel}:{line}: prose example teaches `operator: {m.group(1)}` "
                             f"— the predicate vocabulary was removed from the model")
        for m in re.finditer(r"^\s*condition_logic:", text, re.M):
            line = text[:m.start()].count("\n") + 1
            fails.append(f"PBND-002 {rel}:{line}: prose example teaches `condition_logic`, a field "
                         f"the schema never had")


def main():
    check_schema()
    n = check_records()
    check_prose()
    print(f"policy-boundary: schema scanned · {n} policy record(s) · docs/spec swept")
    if fails:
        for m in fails:
            print(f"  {m}")
        print(f"FAILED — {len(fails)} boundary violation(s)")
        return 1
    print("OK — UDLM declares the facts a policy reads and the decision it produces; "
          "the comparison stays with the engine")
    return 0


if __name__ == "__main__":
    sys.exit(main())
