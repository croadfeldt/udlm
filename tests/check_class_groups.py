#!/usr/bin/env python3
"""A class is defined once and filed under usage groups like hard links (ADR-082; CLS-010, CLS-011).

Home: docs/spec/foundations/class-tiers.md. `filed_under` is a set of usage-group terms
(registry/taxonomies/usage-group.yaml) declared on a Base Class; Types and Provider Classes inherit
it. This gate fails on:

  CLS-010  `filed_under` on a Type or Provider Class (it belongs to the Base only);
           a term that is not a canonical term of the usage-group root;
           `filed_under` on any RECORD (intent/requested/realized/discovered, or a folded example) —
           a filing is organization, never identity, and is never frozen into a sealed record.
  CLS-011  an instantiable Base of a family with a group level (Resource, Access) and no filing (link count 0).

Exit 0 = clean; 1 = at least one violation. `--self-test` runs synthetic bad cases so a gate that
cannot fail proves nothing.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASS_ROOTS = [os.path.join(ROOT, "registry", "classes"), os.path.join(ROOT, "registry", "examples", "classes")]
RECORD_ROOTS = [os.path.join(ROOT, "registry", "examples")]
TAXONOMY = os.path.join(ROOT, "registry", "taxonomies", "usage-group.yaml")
GROUPED_FAMILIES = {"Resource", "Access"}   # families with a group level (ADR-082 rows 082, 089)
RECORD_KINDS = {"intent_record", "requested_record", "realized_record", "discovered_record", "realized_entity"}


def canonical_terms(path=TAXONOMY):
    tax = yaml.safe_load(open(path, encoding="utf-8"))
    return {t["term"] for t in tax.get("terms", []) if t.get("parent") and t.get("curation_state") == "canonical"}


def _docs(root):
    for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
        if os.sep + "must-reject" + os.sep in p:
            continue
        try:
            for d in yaml.safe_load_all(open(p, encoding="utf-8")):
                if isinstance(d, dict):
                    yield os.path.relpath(p, ROOT), d
        except yaml.YAMLError:
            continue


def check(classes, records, terms):
    """classes: [(path, doc)] with record_type class; records: [(path, doc)]; terms: canonical set."""
    fails = []
    for path, d in classes:
        name = d.get("resource_type", "?")
        filed = d.get("filed_under")
        if filed is not None and d.get("class") != "base":
            fails.append(f"CLS-010 {path}: `filed_under` on a {d.get('class')} Class ({name}); it belongs to the Base only")
        for term in filed or []:
            if term not in terms:
                fails.append(f"CLS-010 {path}: {name} is filed under {term!r}, which is not a canonical usage-group term")
        if (d.get("class") == "base" and d.get("family") in GROUPED_FAMILIES and d.get("instantiable") is not False
                and not filed):
            fails.append(f"CLS-011 {path}: {name} is an instantiable {d.get('family')} Base with no filing — "
                         f"declare `filed_under` with at least one usage-group term (link count ≥ 1)")
    for path, d in records:
        kind = d.get("record_type") or ("realized_entity" if "states" in d else None)
        if kind in RECORD_KINDS and "filed_under" in d:
            fails.append(f"CLS-010 {path}: a {kind} carries `filed_under`; a filing lives on the class and "
                         f"resolves through resource_type — it is never written into a record")
    return fails


def main():
    if "--self-test" in sys.argv:
        return self_test()
    terms = canonical_terms()
    classes = [(p, d) for root in CLASS_ROOTS for p, d in _docs(root) if d.get("record_type") == "class"]
    records = [(p, d) for root in RECORD_ROOTS for p, d in _docs(root) if d.get("record_type") != "class"]
    fails = check(classes, records, terms)
    for f in fails:
        print("FAIL " + f)
    filed = sum(1 for _, d in classes if d.get("filed_under"))
    print(f"{len(classes)} class(es), {filed} filed, {len(terms)} canonical usage-group term(s), {len(fails)} violation(s)")
    return 1 if fails else 0


def self_test():
    terms = {"compute", "storage"}
    cases = [
        ("filed_under on a Type", [("t.yaml", {"record_type": "class", "class": "type", "family": "Resource",
                                                "resource_type": "A.B", "parent": "A", "filed_under": ["compute"]})], [], "CLS-010"),
        ("unknown term", [("b.yaml", {"record_type": "class", "class": "base", "family": "Resource",
                                       "resource_type": "A", "filed_under": ["nope"]})], [], "CLS-010"),
        ("unfiled instantiable Base", [("b.yaml", {"record_type": "class", "class": "base", "family": "Resource",
                                                    "resource_type": "A"})], [], "CLS-011"),
        ("filing on a record", [], [("r.yaml", {"record_type": "requested_record", "filed_under": ["compute"]})], "CLS-010"),
    ]
    bad = 0
    for label, classes, records, code in cases:
        fails = check(classes, records, terms)
        ok = any(f.startswith(code) for f in fails)
        print(("ok   " if ok else "FAIL ") + f"self-test: {label} → {code}")
        bad += not ok
    good = [("b.yaml", {"record_type": "class", "class": "base", "family": "Resource", "resource_type": "A", "filed_under": ["compute", "storage"]}),
            ("f.yaml", {"record_type": "class", "class": "base", "family": "Resource", "resource_type": "F", "instantiable": False}),
            ("t.yaml", {"record_type": "class", "class": "type", "family": "Resource", "resource_type": "A.B", "parent": "A"})]
    if check(good, [], terms):
        print("FAIL self-test: clean set flagged"); bad += 1
    else:
        print("ok   self-test: clean set passes (two filings, a folder, an inheriting Type)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
