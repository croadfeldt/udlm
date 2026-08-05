#!/usr/bin/env python3
"""Path <-> record gate (CLS-PATH-001, maintainer ruling 2026-08-04): the classes directory
mirrors the class hierarchy — `registry/classes/<family>/<segments-as-path>.yaml`, the index-file template: a base (always) or any class with children is a directory holding `_base.yaml`; a childless type/provider is a leaf file named by its own kebab-cased segment. The path RESTATES facts
the record owns (family, resource_type, parent), so this gate makes it a VERIFIED projection:
  (a) first path component == lower(family)
  (b) remaining components == the resource_type segments, kebab-cased (acronym runs merge:
      OSPatch -> ospatch, VM -> vm; word-word boundaries hyphenate: BareMetalHost ->
      bare-metal-host) — i.e. the file sits at its ancestry's path, named by its own segment
  (c) `parent`, when present, == the dotted name one segment shorter (the directory ancestry)
Exit 0 = every path is an honest projection; 1 = drift between path and record."""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = os.path.join(ROOT, "registry", "classes")


def kebab(seg):
    tokens = re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[0-9]+", seg)
    out = ""
    for i, t in enumerate(tokens):
        if i and not tokens[i - 1].isupper():
            out += "-"
        out += t.lower()
    return out or seg.lower()


_DOCS = None
def _all_docs():
    global _DOCS
    if _DOCS is None:
        _DOCS = []
        for p in glob.glob(os.path.join(CLASSES, "**", "*.yaml"), recursive=True):
            d = yaml.safe_load(open(p, encoding="utf-8")) or {}
            if d.get("record_type") == "class":
                _DOCS.append(d)
    return _DOCS


def main():
    fails, n = [], 0
    for path in sorted(glob.glob(os.path.join(CLASSES, "**", "*.yaml"), recursive=True)):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        if doc.get("record_type") != "class":
            continue
        n += 1
        rel = os.path.relpath(path, CLASSES)
        parts = rel[:-len(".yaml")].split(os.sep)
        rt, family = doc.get("resource_type", ""), doc.get("family", "")
        segs = [kebab(s) for s in rt.split(".")]
        # index-file template (maintainer ruling 2026-08-04): a BASE is always a directory with
        # _base.yaml (childless bases included — Job); a type/provider class is a leaf file named
        # by its own segment until it has children, then it too becomes <segment>/_base.yaml.
        has_children = any(c.get("parent") == rt for c in _all_docs())
        indexed = doc.get("class") == "base" or has_children
        # family-segment dedup (maintainer ruling 2026-08-05): when the first name segment
        # equals the family (Access.* under family Access), the directory is not repeated —
        # the family dir IS that segment's dir.
        eff = segs[1:] if segs and segs[0] == family.lower() else segs
        want = [family.lower()] + eff + ["_base"] if indexed else [family.lower()] + eff
        if parts != want:
            fails.append(f"{rel}: path says {'/'.join(parts)!r}, expected {'/'.join(want)!r} "
                         f"(family={family}, resource_type={rt}, "
                         f"{'indexed — base tier or has children' if indexed else 'leaf'})")
        parent = doc.get("parent")
        expect_parent = ".".join(rt.split(".")[:-1]) or None
        if (parent or None) != expect_parent:
            fails.append(f"{rel}: parent={parent!r} != ancestry {expect_parent!r} — the directory "
                         f"ancestry and the declared parent must agree")
    for f in fails:
        print("FAIL [CLS-PATH-001] " + f)
    print(f"{n} class(es) checked, {len(fails)} path/record drift(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
