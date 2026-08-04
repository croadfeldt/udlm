#!/usr/bin/env python3
"""Address resolution for the scoped-Class hierarchy (ADR-038 / class-address grammar P0).

An address names an element as seen from a Class, in either of the two ADR-038 notations — they are
the same coordinate and resolve identically:
  - **dot / compact**:  `Compute.VM#cpu`                              (segments dotted; element after `#`)
  - **URL** (preferred): `https://udlm.dev/class/Compute/VM#cpu`      (segments slashed; element as fragment)
The URL form follows OData/Redfish addressing (`@odata.id`) and the ADR-038 `https://<authority>/Compute/VM`
convention; any authority is accepted on input (federated addressing), and the canonical URL is emitted.

Resolution walks the inheritance chain to the *owning* Class (the nearest scope, self→Base, that
declares the element) and its effective schema — the coordinate the ADR-054 projection axis traverses,
and what query, impact, and RBAC scope against. One resolver, both notations.

  resolve(address) -> {"address", "url", "authority", "via_class", "owning_class", "scope",
                       "element", "schema", "inherited": bool}   (raises KeyError on unknown Class/element)
  CLI:  resolve_class_address.py Compute.VM#cpu https://udlm.dev/class/Process/OSPatch#idempotency

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
    for path in sorted(glob.glob(os.path.join(CLASSES, "**", "*.yaml"), recursive=True)):
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


def _parse_address(address):
    """(authority, class_name, element) from either notation. class_name is always the dotted form."""
    if "#" not in address:
        raise KeyError(f"not a class address (missing '#<element>'): {address!r}")
    head, element = address.rsplit("#", 1)
    if head.startswith("http://") or head.startswith("https://"):
        rest = head.split("://", 1)[1]
        authority, _, path = rest.partition("/")
        segs = [s for s in path.split("/") if s and s not in ("registry", "class", "udlm")
                and not s[0].isdigit()]  # drop registry/class/udlm/<spec-version> scaffolding
        if not segs:
            raise KeyError(f"URL address names no Class path: {address!r}")
        return authority, ".".join(segs), element
    return None, head, element  # dot notation — segments already dotted


def canonical_url(class_name, element, authority="udlm.dev"):
    return f"https://{authority}/class/{'/'.join(class_name.split('.'))}#{element}"


def resolve(address, by_name=None):
    by_name = by_name or load_classes()
    authority, cls_name, element = _parse_address(address)
    chain = _chain(cls_name, by_name)  # self → Base; raises on unknown Class
    for depth, cls in enumerate(chain):
        for el in cls.get("elements") or []:
            if el["element"] == element:
                return {
                    "address": f"{cls_name}#{element}",                       # canonical dot form
                    "url": canonical_url(cls_name, element, authority or "udlm.dev"),  # canonical URL form
                    "authority": authority,                                   # None for a local dot address
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
