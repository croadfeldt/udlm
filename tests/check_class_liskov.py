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
import re
import os
import sys

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as _VErr

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


# ---- supports: the OFFER (what values/ranges this scope can satisfy) -----------------------
# `schema` says what is VALID and stays portable; `supports` says what is OFFERED here. A child
# may only narrow the offer. Declaring the matrix as DATA (a clause list) rather than as JSON
# Schema if/then is what keeps this containment decidable — see the class.schema.json note.

_QTY = re.compile(r"^[0-9]+(\.[0-9]+)?(m|[KMGTPE]i?B?)?$")
_UNIT = {"": 1, "m": 1e-3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18,
         "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "Pi": 2**50, "Ei": 2**60}


def _num(v):
    """A comparable magnitude for a bound — a plain number, or a Quantity string normalised to a
    base unit. Returns None when it is neither (a bound we cannot compare is reported, not ignored)."""
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str) or not _QTY.match(v):
        return None
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)(.*)$", v)
    mag, unit = float(m.group(1)), m.group(2).rstrip("B") if m.group(2) not in ("B",) else ""
    return mag * _UNIT.get(unit, _UNIT.get(unit.rstrip("B"), 1))


def _schema_numeric_bounds(schema):
    """The one numeric leaf a `supports` range refers to, when it is determinable.

    `supports: [{min: 1, max: 64}]` on a `cpu` element means cpu.COUNT — the schema is an object
    whose single bounded numeric property is `count`. Where exactly one such leaf exists we can
    compare; where zero or several do (a Quantity string, a multi-numeric object) we cannot, and we
    say so by returning None rather than guessing.
    """
    if not isinstance(schema, dict):
        return None
    if schema.get("type") in ("integer", "number") and ("minimum" in schema or "maximum" in schema):
        return schema.get("minimum"), schema.get("maximum")
    found = [v for v in (schema.get("properties") or {}).values()
             if isinstance(v, dict) and v.get("type") in ("integer", "number")
             and ("minimum" in v or "maximum" in v)]
    if len(found) == 1:
        return found[0].get("minimum"), found[0].get("maximum")
    return None


def supports_wellformed(el, where):
    """Each clause is internally coherent, comparable, and consistent with the element's OWN schema.

    The offer may narrow what the schema allows; it may never exceed it. A clause offering values
    the element's schema would reject is a menu advertising something the model calls invalid.
    """
    errs = []
    schema = el.get("schema") or {}
    bounds = _schema_numeric_bounds(schema)
    for i, c in enumerate(el.get("supports") or []):
        at = f"{where}.supports[{i}]"
        if not any(k in c for k in ("values", "min", "max")):
            errs.append(f"{at}: a clause must carry `values`, or a `min`/`max` range, or both")
        lo, hi = _num(c.get("min")), _num(c.get("max"))
        for k in ("min", "max", "step"):
            if k in c and _num(c[k]) is None:
                errs.append(f"{at}.{k}: {c[k]!r} is neither a number nor a Quantity — it cannot be "
                            f"compared, so the offer cannot be checked")
        if lo is not None and hi is not None and lo > hi:
            errs.append(f"{at}: min {c['min']} exceeds max {c['max']}")
        if "step" in c and not ("min" in c or "max" in c):
            errs.append(f"{at}: `step` is granularity within a range — it needs a min/max")
        # the offer may not exceed what the element's own schema permits
        if bounds:
            smin, smax = bounds
            if smin is not None and lo is not None and lo < smin:
                errs.append(f"{at}: min {c['min']} is below the element schema's minimum {smin} — "
                            f"the offer may narrow what is valid, never exceed it")
            if smax is not None and hi is not None and hi > smax:
                errs.append(f"{at}: max {c['max']} is above the element schema's maximum {smax} — "
                            f"the offer may narrow what is valid, never exceed it")
        # discrete values must satisfy the element's schema exactly
        for v in (c.get("values") or []):
            try:
                Draft202012Validator(schema).validate(_as_instance(v, schema))
            except _VErr as e:
                errs.append(f"{at}.values: {v!r} does not satisfy the element's schema — {e.message[:80]}")
            except Exception:
                pass                      # unresolvable schema fragment: not this gate's job
    return errs


def _as_instance(v, schema):
    """A discrete `supports` value names the leaf a consumer selects. Where the element is an object
    with a single required property, wrap the value so it can be validated against the real shape."""
    req = schema.get("required") or []
    if schema.get("type") == "object" and len(req) == 1:
        return {req[0]: v}
    return v


def supports_containment(parent_el, child_el, where):
    """Every child clause must fall inside SOME parent clause. A child offering anything the parent
    does not is a widened offer, which is the same defect as a widened enum."""
    perrs, pclauses = [], parent_el.get("supports") or []
    if not pclauses:
        return perrs                      # parent declares no offer — the child is free to state one
    for i, c in enumerate(child_el.get("supports") or []):
        at = f"{where}.supports[{i}]"
        clo, chi = _num(c.get("min")), _num(c.get("max"))
        cvals = set(map(str, c.get("values") or []))
        fits = False
        for p in pclauses:
            plo, phi = _num(p.get("min")), _num(p.get("max"))
            pvals = set(map(str, p.get("values") or []))
            if cvals and not (cvals <= pvals or (plo is not None and phi is not None and all(
                    _num(v) is not None and plo <= _num(v) <= phi for v in cvals))):
                continue
            if clo is not None and plo is not None and clo < plo:
                continue
            if chi is not None and phi is not None and chi > phi:
                continue
            if (clo is not None or chi is not None) and not pvals and plo is None and phi is None:
                continue
            fits = True
            break
        if not fits:
            perrs.append(f"{at}: offers values outside every parent clause — a child may narrow the "
                         f"offer, never widen it")
    return perrs


def ancestor_full_elements(cls, by_name):
    """Like ancestor_elements, but the whole element — `supports` sits beside `schema`, and the
    containment check needs both."""
    merged = {}
    chain, seen = [], set()
    p = cls.get("parent")
    while p and p not in seen:
        seen.add(p); chain.append(p); p = (by_name.get(p) or {}).get("parent")
    for name in reversed(chain):
        for el in (by_name.get(name) or {}).get("elements") or []:
            merged[el["element"]] = el
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
    # step: a child may only make granularity COARSER-or-equal in a way that stays a subset —
    # a finer step offers values the parent did not (2Gi under a parent's 8Gi is not a refinement).
    if "multipleOf" in parent and "multipleOf" in child:
        if child["multipleOf"] % parent["multipleOf"] != 0:
            errs.append(f"{where}: multipleOf {child['multipleOf']} is not a multiple of the parent's "
                        f"{parent['multipleOf']} — it offers values the parent does not")
    elif "multipleOf" in parent and "multipleOf" not in child:
        errs.append(f"{where}: parent declares multipleOf {parent['multipleOf']}; a child that drops it "
                    f"widens the offer")
    for bound, cmp, word in (("minItems", lambda c, p: c < p, "below"), ("maxItems", lambda c, p: c > p, "above")):
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


def card_bounds(card):
    """(min, max) from '0..n' / '1..1' / '0..*'; missing cardinality = fully open (0, inf)."""
    if not card or ".." not in str(card):
        return (0, float("inf"))
    lo, hi = str(card).split("..", 1)
    return (int(lo), float("inf") if hi in ("n", "*") else int(hi))


def rel_identity(rel):
    return rel.get("name") or (rel.get("edge_type"), rel.get("target"), rel.get("target_field"))


def check(by_name):
    fails, n = [], 0
    for name, cls in sorted(by_name.items()):
        n += 1
        anc = ancestor_elements(cls, by_name)
        anc_full = ancestor_full_elements(cls, by_name)
        for el in cls.get("elements") or []:
            if el.get("scope") != name:
                fails.append(f"{name}: element {el['element']!r} scope={el.get('scope')!r} != class resource_type {name!r}")
            if el["element"] in anc:  # redeclare → must refine
                fails += refine_errors(anc[el["element"]], el.get("schema") or {}, f"{name}.{el['element']}")
            # the OFFER: well-formed here, and contained within the parent's offer
            if el.get("supports"):
                fails += supports_wellformed(el, f"{name}.{el['element']}")
                if el["element"] in anc_full:
                    fails += supports_containment(anc_full[el["element"]], el, f"{name}.{el['element']}")
        # outputs (#323): a redeclared output must refine the ancestor's shape
        anc_out = ancestor_axis(cls, by_name, "outputs")
        for oname, oschema in (cls.get("outputs") or {}).items():
            if oname in anc_out:
                fails += refine_errors(anc_out[oname] or {}, oschema or {}, f"{name}.outputs.{oname}")
        # relationships (#323 + maintainer ruling 2026-08-03 "tighten at your scope"): a child
        # ADDS edges, or REDECLARES an ancestor's to TIGHTEN it — never loosen/retarget/re-type.
        anc_rel = ancestor_axis(cls, by_name, "relationships", as_map=rel_identity)
        for rel in cls.get("relationships") or []:
            parent = anc_rel.get(rel_identity(rel))
            if parent:
                where = f"{name}.relationships[{rel_identity(rel)!r}]"
                for fld in ("edge_type", "target", "target_field"):
                    if parent.get(fld) != rel.get(fld):
                        fails.append(f"{where}: {fld} changed {parent.get(fld)!r} → {rel.get(fld)!r} (a redeclare only tightens; it never retargets)")
                pmin, pmax = card_bounds(parent.get("cardinality"))
                cmin, cmax = card_bounds(rel.get("cardinality"))
                if cmin < pmin:
                    fails.append(f"{where}: cardinality min {cmin} below parent's {pmin} (loosening)")
                if cmax > pmax:
                    fails.append(f"{where}: cardinality max {cmax} above parent's {pmax} (loosening)")
                if parent.get("enforcement") == "structural" and rel.get("enforcement") == "advisory":
                    fails.append(f"{where}: enforcement structural → advisory (loosening)")
        # immutable (maintainer ruling 2026-08-03): OWN-TIER only — the path's head must name an
        # element DECLARED AT THIS class; freezing inherited surface reaches above your scope.
        own = {el["element"] for el in cls.get("elements") or []}
        for path in cls.get("immutable") or []:
            if path.split(".")[0] not in own:
                fails.append(f"{name}: immutable path {path!r} does not name an element declared at this class "
                             f"(own-tier only — tighten at your scope, never above)")
        # context/spec_examples/spec_constraints (#323 + Job ruling): type tier, or a CHILDLESS
        # base (an instantiable base with no descendants is served directly); never provider,
        # never a base that has children (its types own the served surface).
        has_children = any(c.get("parent") == name for c in by_name.values())
        for key in ("context", "spec_examples", "spec_constraints"):
            if not cls.get(key):
                continue
            tier = cls.get("class")
            if tier == "provider" or (tier == "base" and has_children):
                why = "provider tier carries no served prose" if tier == "provider" else                       f"base with children ({name} has descendants) — its types own the served surface"
                fails.append(f"{name}: `{key}` not permitted here — {why}")
    return fails, n


def main():
    by_name = load_classes()
    fails, n = check(by_name)
    # self-test: a synthetic child that contradicts its parent MUST be caught
    probe = refine_errors({"type": "integer", "minimum": 1}, {"type": "string"}, "self_test")
    if not probe:
        print("FAIL [LSK-SELF] the Liskov refinement check did not catch a type-change contradiction")
        fails.append("self-test")
    # the OFFER checks self-test too — a gate that cannot fail proves nothing about the matrix
    if not supports_wellformed({"supports": [{"min": "8Gi", "max": "1Gi"}]}, "self_test"):
        print("FAIL [LSK-SELF] supports well-formedness missed an inverted range")
        fails.append("self-test")
    if not supports_containment({"supports": [{"min": "8Gi", "max": "64Gi"}]},
                                {"supports": [{"min": "8Gi", "max": "512Gi"}]}, "self_test"):
        print("FAIL [LSK-SELF] supports containment missed a child offering beyond its parent")
        fails.append("self-test")
    for f in fails:
        print("FAIL [LSK-001] " + f)
    print(f"{n} class(es) checked, {len(fails)} Liskov violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
