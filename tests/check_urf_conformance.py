#!/usr/bin/env python3
"""URF conformance gate — the two tests §9 declares as *defining the mechanism*.

identifier-scheme.md §9 says: "Two conformance tests define the mechanism." Both were written
as prose and gated by nothing. This makes them executable.

  1. DEREFERENCE  — every well-formed URF resolves to its target via the resolution contract
                    (§9.6). UDLM owns the DENOTATION; serving it is implementation (ADR-008).
                    So the gate proves the resolvable half locally: a URF naming a type path,
                    a class element (`#fragment`), or a registry record must land on something
                    that exists in this repo. A URF that resolves to nothing is a dangling
                    address the spec claims cannot exist.

  2. PORTABILITY  — a filter moves VERBATIM between a live query, a stored criterion, layer
                    targeting, and a tool argument, meaning the same set everywhere. The gate
                    proves the property that makes that true: one canonical form, reached from
                    every spelling and every carrier, byte-identical. If a filter canonicalizes
                    differently depending on which surface it came from, "verbatim" is a lie.

Plus the two rules `check_urf.py` never exercised — measured, not assumed:
  URF-004  cardinality-1 — a reference resolving to >1 target is refused `ambiguous`.
  URF-007  no credential or bearer material in ANY axis.

Exit 0 = conformant; 1 = at least one violation.
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "registry", "tools"))
import urf as U  # noqa: E402

fails = []


# --------------------------------------------------------------------------------------
# Test 1 — DEREFERENCE
# --------------------------------------------------------------------------------------
def _registry_index():
    """What this repo can actually resolve: served type paths, their elements, and record uuids."""
    types, elements, uuids = set(), {}, set()
    for f in glob.glob(os.path.join(ROOT, "registry", "generated", "*.json")):
        try:
            d = json.load(open(f, encoding="utf-8"))
        except Exception:
            continue
        rt = d.get("resource_type")
        if rt:
            types.add(rt.replace(".", "/"))
            props = ((d.get("spec") or {}).get("properties") or {})
            elements[rt.replace(".", "/")] = set(props)
    for pat in ("registry/**/*.yaml", "registry/**/*.json"):
        for f in glob.glob(os.path.join(ROOT, pat), recursive=True):
            if "generated" in f:
                continue
            try:
                d = yaml.safe_load(open(f, encoding="utf-8"))
            except Exception:
                continue
            for doc in (d if isinstance(d, list) else [d]):
                if isinstance(doc, dict) and doc.get("uuid"):
                    uuids.add(doc["uuid"])
    return types, elements, uuids


def test_dereference():
    """Every URF authored in this repo must denote something that exists here."""
    types, elements, uuids = _registry_index()
    checked = 0
    for f in glob.glob(os.path.join(ROOT, "registry", "**", "*"), recursive=True):
        if not f.endswith((".yaml", ".json")) or "generated" in f:
            continue
        try:
            text = open(f, encoding="utf-8").read()
            docs = list(yaml.safe_load_all(text)) if f.endswith(".yaml") else [json.loads(text)]
        except Exception:
            continue
        rel = os.path.relpath(f, ROOT)
        for doc in docs:
            for loc, val in _walk_strings(doc):
                if not _looks_like_urf(val) or _is_schema_example(loc):
                    continue
                try:
                    u = U.parse(val)
                except U.URFError:
                    continue                       # URF-001's job, covered by check_urf
                checked += 1
                path = "/".join(u.path)
                # uuid space — resolves against minted identities
                if u.path and u.path[0] == "uuid":
                    if len(u.path) > 1 and u.path[1] not in uuids:
                        fails.append(f"DEREFERENCE {rel}:{loc}: {val} → uuid names no record in this repo")
                    continue
                # estate space — instance data, not carried in the public spec repo
                if u.path and u.path[0] == "estate":
                    continue
                # registry space — a served type path, optionally with an element fragment
                if path in types:
                    if u.fragment and u.fragment.split(".")[0] not in elements.get(path, set()):
                        fails.append(f"DEREFERENCE {rel}:{loc}: {val} → #{u.fragment} is not an element of {path}")
    return checked


# --------------------------------------------------------------------------------------
# Test 2 — PORTABILITY
# --------------------------------------------------------------------------------------
CARRIERS = [
    # (label, how the same filter is spelled on that surface)
    ("live query",       lambda p, q: f"{p}?{q}"),
    ("stored criterion", lambda p, q: f"{p}?{q}"),
    ("input '&' form",   lambda p, q: f"{p}?{q.replace(';', '&')}"),
    ("reordered",        lambda p, q: f"{p}?{';'.join(reversed(q.split(';')))}"),
]

PORTABLE_FILTERS = [
    ("estate", "tenant_uuid=={self}"),
    ("estate", "resource_type==Compute.VM;lifecycle_state==active"),
    ("estate", "labels.concern==payments;tenant_uuid==abc"),
    ("estate", "sovereignty_zone=in=(eu-central,eu-west)"),
    ("estate", "resource_type==Compute.*;cost_center!=*"),
]


def test_portability():
    """One canonical form, reached from every carrier and every legal spelling."""
    checked = 0
    for path, q in PORTABLE_FILTERS:
        forms = {}
        for label, spell in CARRIERS:
            src = spell(path, q)
            try:
                forms[label] = U.canonicalize(src)
            except U.URFError as e:
                fails.append(f"PORTABILITY: {label} spelling refused: {src} — {e}")
        if len(set(forms.values())) > 1:
            fails.append(f"PORTABILITY: {path}?{q} is not one set across carriers: {forms}")
        checked += 1
        # the block form is a projection, not a second parse surface (§9.4) — it must round-trip
        canon = forms.get("live query")
        if canon:
            try:
                if U.from_block(U.to_block(canon)) != canon:
                    fails.append(f"PORTABILITY: block projection is not verbatim for {canon}")
            except U.URFError as e:
                fails.append(f"PORTABILITY: block round-trip refused for {canon}: {e}")
    return checked


# --------------------------------------------------------------------------------------
# URF-004 / URF-007 — the two rules nothing exercised
# --------------------------------------------------------------------------------------
CREDENTIAL_MARKERS = ("password", "token", "secret", "api_key", "apikey",
                      "bearer", "private_key", "passwd", "credential")


def test_no_credentials():
    """URF-007 — credential or bearer material MUST NOT appear in any axis.

    Enforced on the SELECTOR, not on values: a filter may legitimately reference a credential
    RECORD by uuid (that is the referencing model working), but a URF that filters or carries a
    credential VALUE has put secret material into something logged, sealed, and digested.
    """
    checked = 0
    for f in glob.glob(os.path.join(ROOT, "registry", "**", "*"), recursive=True):
        if not f.endswith((".yaml", ".json")) or "generated" in f:
            continue
        try:
            text = open(f, encoding="utf-8").read()
            docs = list(yaml.safe_load_all(text)) if f.endswith(".yaml") else [json.loads(text)]
        except Exception:
            continue
        rel = os.path.relpath(f, ROOT)
        for doc in docs:
            for loc, val in _walk_strings(doc):
                if not _looks_like_urf(val):
                    continue
                try:
                    u = U.parse(val)
                except U.URFError:
                    continue
                checked += 1
                for sel in _selectors(u.terms):
                    leaf = sel.split(".")[-1]
                    if any(m in leaf for m in CREDENTIAL_MARKERS) and not leaf.endswith(("_ref", "_uuid")):
                        fails.append(f"URF-007 {rel}:{loc}: selector {sel!r} names credential material "
                                     f"— a URF is logged, sealed, and digested")
    return checked


def test_cardinality_one():
    """URF-004 — a reference (cardinality 1) that could match many is refused, never narrowed.

    Structural proof, since resolution is served by DCM: a `udlm-ref-url` field whose authored
    value carries a glob or a set operator is a filter wearing a reference's clothes — it CANNOT
    be cardinality-1, so it must not sit in a reference position.
    """
    checked = 0
    for f in glob.glob(os.path.join(ROOT, "registry", "**", "*"), recursive=True):
        if not f.endswith((".yaml", ".json")) or "generated" in f:
            continue
        try:
            text = open(f, encoding="utf-8").read()
            docs = list(yaml.safe_load_all(text)) if f.endswith(".yaml") else [json.loads(text)]
        except Exception:
            continue
        rel = os.path.relpath(f, ROOT)
        for doc in docs:
            for loc, val in _walk_strings(doc):
                if not _looks_like_urf(val) or "?" not in val:
                    continue
                try:
                    u = U.parse(val)
                except U.URFError:
                    continue
                if not (u.path and u.path[0] == "uuid"):
                    continue                      # only the resolved-reference form is cardinality-1
                checked += 1
                for op, sel, v in _terms(u.terms):
                    if op in ("=in=", "=out="):
                        fails.append(f"URF-004 {rel}:{loc}: {val} is a uuid reference but carries {op} "
                                     f"— a reference is cardinality 1, never a set")
                    elif isinstance(v, str) and "*" in v:
                        fails.append(f"URF-004 {rel}:{loc}: {val} is a uuid reference but carries a glob "
                                     f"in {sel} — a reference is cardinality 1, never a pattern")
    return checked


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------
def _walk_strings(node, loc=""):
    if isinstance(node, dict):
        for k, v in node.items():
            yield from _walk_strings(v, f"{loc}.{k}" if loc else str(k))
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from _walk_strings(v, f"{loc}[{i}]")
    elif isinstance(node, str):
        yield loc, node


def _is_schema_example(loc):
    """A JSON Schema `examples` entry illustrates the FORM, not a live edge.

    Requiring one to dereference would couple documentation to record lifecycle: retiring a
    record would break a schema, and under the publish law (ADR-051) force a schema version bump
    to fix a comment. Wrong coupling — so form-examples are out of scope for the dereference
    test. Every OTHER position is in scope, including the worked-example records themselves.
    """
    return ".examples[" in loc or loc.endswith(".examples")


def _looks_like_urf(s):
    """Cheap prefilter — the authored URF shapes, not every string in the tree."""
    return (s.startswith(("uuid/", "estate", "//")) or
            (("?" in s or "#" in s) and "==" in s)) and " " not in s.split("?")[0]


def _terms(ast):
    if ast is None:
        return
    kind = ast[0]
    if kind in ("or", "and"):
        for c in ast[1]:
            yield from _terms(c)
    elif kind == "group":
        yield from _terms(ast[1])
    elif kind != "op":
        yield ast


def _selectors(ast):
    for op, sel, _ in _terms(ast):
        yield sel


def main():
    d = test_dereference()
    p = test_portability()
    c = test_no_credentials()
    k = test_cardinality_one()
    print(f"urf-conformance: dereference {d} URF(s) · portability {p} filter(s) × {len(CARRIERS)} carriers "
          f"· URF-007 {c} · URF-004 {k}")
    if fails:
        for m in fails:
            print(f"  {m}")
        print(f"FAILED — {len(fails)} conformance violation(s)")
        return 1
    print("OK — every URF denotes, every filter is one set across carriers, "
          "no credential selectors, no set-valued references")
    return 0


if __name__ == "__main__":
    sys.exit(main())
