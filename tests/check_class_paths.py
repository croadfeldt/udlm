#!/usr/bin/env python3
"""Path <-> record gate (CLS-PATH-001, maintainer ruling 2026-08-04): the classes directory
mirrors the class hierarchy — `registry/classes/<family>/<segments-as-path>.yaml`, a class file
inside its parent's directory, named by its own (kebab-cased) segment. The path RESTATES facts
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
        want = [family.lower()] + [kebab(s) for s in rt.split(".")]
        if parts != want:
            fails.append(f"{rel}: path says {'/'.join(parts)!r}, record says {'/'.join(want)!r} "
                         f"(family={family}, resource_type={rt})")
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
