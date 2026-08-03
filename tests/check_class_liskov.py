#!/usr/bin/env python3
"""Liskov gate for scoped-Class artifacts (ADR-038): a child Class extends its parent by ADD or
REFINE, never CONTRADICT — a Provider Class *is-a* Type Class *is-a* Base Class.

Each Class (registry/classes/*.yaml) with a `parent` is checked against the merged element set of
its ancestors. An element the child REDECLARES (same `element` name as an ancestor) MUST refine
(narrow) the ancestor's shape; a NEW element name is always an allowed add. Contradiction — a type
change, an enum that adds values the parent didn't allow, a numeric bound looser than the parent's,
or dropping a `required` the parent had — is a hard failure. Every element's `scope` must equal its
owning Class's `resource_type` (the scope IS the portability position, ADR-038 §3).

A precise JSON-Schema subtype check is undecidable in general; this enforces the common, decidable
refinement rules that catch real contradictions. Exit 0 = every child refines-or-adds; 1 = at least
one contradiction. Wire into CI + signoff.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = os.path.join(ROOT, "registry", "classes")


def load_classes():
    by_name = {}
    for path in sorted(glob.glob(os.path.join(CLASSES, "**", "*.yaml"), recursive=True)):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        if doc.get("record_type") == "class":
            by_name[doc["resource_type"]] = doc
    return by_name


def ancestor_elements(cls, by_name):
    """Merged {element_name: schema} from all ancestors (nearest ancestor wins on a redeclare)."""
    merged = {}
    chain, seen = [], set()
    p = cls.get("parent")
    while p and p not in seen:
        seen.add(p)
        chain.append(p)
        p = (by_name.get(p) or {}).get("parent")
    for name in reversed(chain):  # Base first, so nearer ancestors override
        for el in (by_name.get(name) or {}).get("elements") or []:
            merged[el["element"]] = el.get("schema") or {}
    return merged


def refine_errors(parent, child, where):
    """Rules that make `child` a legal refinement of `parent` (both JSON-Schema fragments)."""
    errs = []
    pt, ct = parent.get("type"), child.get("type")
    if pt and ct and pt != ct:
        errs.append(f"{where}: type changed {pt!r} → {ct!r} (a refinement may not change type)")
    if "enum" in parent:
        widened = set(child.get("enum", [])) - set(parent["enum"])
        if "enum" not in child or widened:
            errs.append(f"{where}: enum must narrow the parent's; adds {sorted(widened) or 'nothing (missing enum)'}")
    for bound, cmp, word in (("minimum", lambda c, p: c < p, "below"), ("maximum", lambda c, p: c > p, "above")):
        if bound in parent and bound in child and cmp(child[bound], parent[bound]):
            errs.append(f"{where}: {bound} {child[bound]} is {word} the parent's {parent[bound]} (looser, not a refinement)")
    dropped = set(parent.get("required", [])) - set(child.get("required", []))
    if dropped:
        errs.append(f"{where}: drops required {sorted(dropped)} the parent declared (a refinement may add required, never drop)")
    # recurse into redeclared sub-properties
    for k, csub in (child.get("properties") or {}).items():
        psub = (parent.get("properties") or {}).get(k)
        if psub:
            errs += refine_errors(psub, csub, f"{where}.{k}")
    return errs


def ancestor_axis(cls, by_name, axis, as_map=None):
    """Merged ancestor view of a non-element axis. as_map: fn(item)->key for list axes."""
    merged = {}
    chain, seen = [], set()
    p = cls.get("parent")
    while p and p not in seen:
        seen.add(p)
        chain.append(p)
        p = (by_name.get(p) or {}).get("parent")
    for name in reversed(chain):
        val = (by_name.get(name) or {}).get(axis)
        if isinstance(val, dict):
            merged.update(val)
        elif isinstance(val, list) and as_map:
            for item in val:
                merged[as_map(item)] = item
    return merged


def rel_identity(rel):
    return rel.get("name") or (rel.get("edge_type"), rel.get("target"), rel.get("target_field"))


def visible_elements(cls, by_name):
    names = set(ancestor_elements(cls, by_name))
    names.update(el["element"] for el in cls.get("elements") or [])
    return names


def check(by_name):
    fails, n = [], 0
    for name, cls in sorted(by_name.items()):
        n += 1
        anc = ancestor_elements(cls, by_name)
        for el in cls.get("elements") or []:
            if el.get("scope") != name:
                fails.append(f"{name}: element {el['element']!r} scope={el.get('scope')!r} != class resource_type {name!r}")
            if el["element"] in anc:  # redeclare → must refine
                fails += refine_errors(anc[el["element"]], el.get("schema") or {}, f"{name}.{el['element']}")
        # outputs (#323): a redeclared output must refine the ancestor's shape
        anc_out = ancestor_axis(cls, by_name, "outputs")
        for oname, oschema in (cls.get("outputs") or {}).items():
            if oname in anc_out:
                fails += refine_errors(anc_out[oname] or {}, oschema or {}, f"{name}.outputs.{oname}")
        # relationships (#323): a child ADDS; redeclaring an ancestor's identity contradicts
        anc_rel = ancestor_axis(cls, by_name, "relationships", as_map=rel_identity)
        for rel in cls.get("relationships") or []:
            if rel_identity(rel) in anc_rel:
                fails.append(f"{name}: relationship {rel_identity(rel)!r} redeclares an ancestor's — "
                             f"a child adds relationships, never redeclares (narrowing a published contract is breaking, ADR-045)")
        # immutable (#323): each path's head segment must resolve to a visible element
        visible = visible_elements(cls, by_name)
        for path in cls.get("immutable") or []:
            if path.split(".")[0] not in visible:
                fails.append(f"{name}: immutable path {path!r} does not resolve to an element visible in the chain")
        # context (#323): type tier only (schema also enforces; kept here so the gate is self-sufficient)
        if cls.get("context") and cls.get("class") != "type":
            fails.append(f"{name}: `context` on a {cls.get('class')}-tier Class — context is type-tier prose only")
    return fails, n


def main():
    by_name = load_classes()
    fails, n = check(by_name)
    # self-test: a synthetic child that contradicts its parent MUST be caught
    probe = refine_errors({"type": "integer", "minimum": 1}, {"type": "string"}, "self_test")
    if not probe:
        print("FAIL [LSK-SELF] the Liskov refinement check did not catch a type-change contradiction")
        fails.append("self-test")
    for f in fails:
        print("FAIL [LSK-001] " + f)
    print(f"{n} class(es) checked, {len(fails)} Liskov violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
