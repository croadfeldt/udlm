#!/usr/bin/env python3
"""Short names are input handles, never identity; instantiability belongs to the Base (CLS-007, CLS-008).

Home: docs/spec/foundations/class-tiers.md (ADR-069). A class MAY declare one `short_name` — modelled
on Kubernetes shortNames — that is resolved to the canonical `resource_type` on input and is NEVER
written into a stored reference. This gate fails on:

  CLS-007  a short_name that does not match the resource_type pattern;
           a short_name equal (case-insensitively) to any canonical class name or to another short_name;
           a short_name appearing where only a canonical name may: `$id`, `parent`, an element `scope`,
           a relationship `target`.
  CLS-008  `instantiable` on a Type or Provider Class (it is meaningful on a Base only).

Exit 0 = clean; 1 = at least one violation. Self-tests a synthetic collision so a gate that cannot fail
proves nothing. Wire into CI + signoff (scripts/ci-steps.py derives signoff from validate.yml).
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASS_ROOTS = [os.path.join(ROOT, "registry", "classes"),
               os.path.join(ROOT, "registry", "examples", "classes")]
NAME = re.compile(r"^[A-Z][A-Za-z0-9]+(\.[A-Z][A-Za-z0-9]+){0,2}$")


def load_classes():
    docs = []
    for root in CLASS_ROOTS:
        for path in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
            if doc.get("record_type") == "class":
                docs.append((os.path.relpath(path, ROOT), doc))
    return docs


def check(docs):
    fails = []
    canonical = {d["resource_type"] for _, d in docs}
    shorts = {}  # lower(short) -> (short, owner, path)
    for path, d in docs:
        name = d["resource_type"]
        short = d.get("short_name")
        if d.get("instantiable") is not None and d.get("class") != "base":
            fails.append(f"CLS-008 {path}: `instantiable` on a {d.get('class')} Class ({name}); it belongs to a Base only")
        if short is None:
            continue
        if not NAME.match(short):
            fails.append(f"CLS-007 {path}: short_name {short!r} does not match the resource_type pattern")
        low = short.lower()
        if low in {c.lower() for c in canonical}:
            fails.append(f"CLS-007 {path}: short_name {short!r} collides with a canonical class name")
        if low in shorts:
            fails.append(f"CLS-007 {path}: short_name {short!r} already claimed by {shorts[low][1]} ({shorts[low][2]})")
        else:
            shorts[low] = (short, name, path)
    # stored-canonical: no short name in any stored reference field
    short_set = {s.lower() for s in shorts}
    for path, d in docs:
        refs = []
        if d.get("parent"):
            refs.append(("parent", d["parent"]))
        for el in d.get("elements") or []:
            if el.get("scope"):
                refs.append((f"elements[{el.get('element')}].scope", el["scope"]))
        for rel in d.get("relationships") or []:
            if rel.get("target"):
                refs.append((f"relationships[{rel.get('edge_type')}].target", rel["target"]))
        m = re.search(r"/class/([A-Za-z0-9.]+)/", d.get("$id") or "")
        if m:
            refs.append(("$id", m.group(1)))
        for where, value in refs:
            if str(value).lower() in short_set and value not in canonical:
                fails.append(f"CLS-007 {path}: {where} = {value!r} is a short name; stored references carry the canonical name")
    return fails


def self_test():
    probe = [
        ("probe/a.yaml", {"record_type": "class", "class": "base", "resource_type": "ProbeAlpha", "short_name": "PA"}),
        ("probe/b.yaml", {"record_type": "class", "class": "base", "resource_type": "ProbeBeta", "short_name": "pa"}),
        ("probe/c.yaml", {"record_type": "class", "class": "type", "resource_type": "ProbeAlpha.Thing",
                          "parent": "PA", "instantiable": False, "elements": [], "relationships": []}),
    ]
    got = check(probe)
    want = ["already claimed", "is a short name", "CLS-008"]
    missing = [w for w in want if not any(w in f for f in got)]
    return [f"self-test did not catch: {m}" for m in missing]


def main():
    fails = self_test()
    docs = load_classes()
    fails += check(docs)
    for f in fails:
        print("FAIL [" + (f.split()[0] if f.startswith("CLS") else "CLS-SELF") + "] " + f)
    n_short = sum(1 for _, d in docs if d.get("short_name"))
    print(f"{len(docs)} class(es) checked, {n_short} short name(s), {len(fails)} violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
