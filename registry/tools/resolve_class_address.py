#!/usr/bin/env python3
"""Dotted-address resolution for the scoped-Class hierarchy (ADR-038 / realization-plan P0).

An address `<ClassName>#<element>` (e.g. `Compute.VM#cpu`) resolves to the element as seen from that
Class — walking the inheritance chain to find the *owning* Class (the nearest scope, self→Base, that
declares the element) and its effective schema. This is the coordinate the ADR-054 projection axis
traverses, and what query, impact, and RBAC scope against — one resolver, reused.

  resolve(address) -> {"address", "via_class", "owning_class", "scope", "element", "schema",
                       "inherited": bool}   (raises KeyError on an unknown Class / element)
  CLI:  resolve_class_address.py Compute.VM#cpu Process.OSPatch#idempotency   (JSON per address)

Resolution rules:
- The element is looked up from the addressed Class upward; the *nearest* declaring Class owns it
  (a descendant that refines an element owns the refined shape at its scope — Liskov guarantees it
  narrows, never contradicts).
- `inherited` is true when the owning Class is an ancestor of the addressed Class (the common case:
  `Compute.VM#cpu` is owned by the `Compute` Base Class).
- An element the addressed Class cannot see (declared on neither it nor an ancestor) is a KeyError —
  the same dangling-reference discipline data references use (invalid edges resolve deterministically).
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = os.path.join(ROOT, "classes")


def load_classes():
    by_name = {}
    for path in sorted(glob.glob(os.path.join(CLASSES, "*.yaml"))):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        if doc.get("record_type") == "class":
            by_name[doc["resource_type"]] = doc
    return by_name


def _chain(name, by_name):
    """[self, parent, …, Base] — self first, then ancestors."""
    order, seen = [], set()
    while name and name not in seen:
        seen.add(name)
        cls = by_name.get(name)
        if not cls:
            raise KeyError(f"unknown Class {name!r}")
        order.append(cls)
        name = cls.get("parent")
    return order


def resolve(address, by_name=None):
    by_name = by_name or load_classes()
    if "#" not in address:
        raise KeyError(f"not a class address (expected <ClassName>#<element>): {address!r}")
    cls_name, element = address.split("#", 1)
    chain = _chain(cls_name, by_name)  # self → Base; raises on unknown Class
    for depth, cls in enumerate(chain):
        for el in cls.get("elements") or []:
            if el["element"] == element:
                return {
                    "address": address,
                    "via_class": cls_name,
                    "owning_class": cls["resource_type"],
                    "scope": el.get("scope"),
                    "element": element,
                    "schema": el.get("schema"),
                    "values": el.get("values"),
                    "inherited": depth > 0,
                }
    raise KeyError(f"{address}: element {element!r} not declared on {cls_name} or any ancestor")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        sys.exit("usage: resolve_class_address.py <ClassName>#<element> [...]")
    by_name = load_classes()
    fail = 0
    for a in args:
        try:
            print(json.dumps(resolve(a, by_name), ensure_ascii=False))
        except KeyError as e:
            print(f"UNRESOLVED {e}", file=sys.stderr); fail = 1
    return fail


if __name__ == "__main__":
    sys.exit(main())
