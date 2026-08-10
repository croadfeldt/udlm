#!/usr/bin/env python3
"""Every case in registry/examples/must-reject/ must actually be refused.

The valid examples prove the model accepts the right things. They say nothing about whether it
refuses the wrong ones, and a gate that cannot fail proves only that its code runs. This executes
the other half.

It fails in **two directions**, which is the whole value:

  MRJ-001  a case the named gate ACCEPTS — the model stopped refusing something it should.
  MRJ-002  a case whose gate or rule cannot be resolved — the case has drifted away from the thing
           it was written against and is no longer proving anything. A case that quietly stops
           applying is worse than no case, because the count still looks healthy.

Each case names its own gate; there is no manifest. A manifest is a second list that drifts from
the first, and a self-describing case cannot disagree with itself.

**Adding a gate to the dispatch below is deliberate.** A gate is bound here by naming the callable
that evaluates ONE record, so a case can be handed to it directly without writing files into the
tree mid-run. Gates that only scan the whole repository are not bindable this way — that is a
limitation worth knowing rather than working around with temp files, which leave debris on failure.

Exit 0 = every case is refused for the reason it claims; 1 = at least one is not.
"""
import glob
import importlib.util
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CASES = os.path.join(ROOT, "registry", "examples", "must-reject")


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(ROOT, path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _grant_derivation(record):
    """GRD-001. The record is the holder; its edges are resolved against the shipped estate, so a
    case only has to supply the offending record rather than restate the whole worked set."""
    m = _load("tests/check_grant_derivation.py", "_grd")
    instances = m.load_instances()
    rec = dict(record)
    rec.setdefault("_path", "must-reject case")
    instances[rec["uuid"]] = rec
    _, fails = m.derive(instances, m.load_type_flags())
    return fails


def _group_invariants(record):
    """GRP-INV-001/002/005/006 — judged against the shipped estate, so a case supplies only the
    offending record. This is the bindable shape #434 asks for: evaluate(record, index)."""
    m = _load("tests/check_group_invariants.py", "_grp")
    return m.evaluate(record, m.load_index())


def _catalog_item(record):
    """CMP-002 and the other composite cross-field rules — already per-record, already citing its
    rule. Bindable with no change to the gate."""
    m = _load("registry/tools/validate.py", "_val2")
    return m.check_catalog_item(record)


def _schema(record):
    """Schema validation as a bindable gate. Many requirements — uuid canonical form, the v4 version
    nibble and variant bits — are enforced by a `pattern` rather than by any semantic check, so a
    case against one has nothing to call unless schema validation is itself bindable.

    The case names the schema, because a bare record cannot always say which one governs it."""
    import jsonschema
    name = record.pop("__schema__", None)
    if not name:
        return ["case must name the governing schema in `record.__schema__`"]
    path = os.path.join(ROOT, "registry", name)
    if not os.path.exists(path):
        return [f"case names schema {name!r}, which does not exist"]
    from referencing import Registry, Resource
    reg = Registry()
    for p in glob.glob(os.path.join(ROOT, "registry", "*.schema.json")):
        d = json.load(open(p, encoding="utf-8"))
        r = Resource.from_contents(d, default_specification=jsonschema.Draft202012Validator.ID_OF
                                   and __import__("referencing.jsonschema", fromlist=["DRAFT202012"]).DRAFT202012)
        reg = reg.with_resource(os.path.basename(p), r)
        if d.get("$id"):
            reg = reg.with_resource(d["$id"], r)
    schema = json.load(open(path, encoding="utf-8"))
    v = jsonschema.Draft202012Validator(schema, registry=reg)
    return [f"WIR schema: {e.json_path} — {e.message[:110]}" for e in v.iter_errors(record)]


def _class_constituents(record):
    """CMP-010/011 — the composite cross-field rules PLUS namespace resolution (a constituent's
    resource_type must resolve to a registered Class or a flat type). Superset of
    check_catalog_item, which is why a resolution case names this one."""
    m = _load("registry/tools/validate.py", "_val3")
    return m.check_class_constituents(record)


def _composition_promotion(record):
    """ING-017/018/019 — promotion as a round trip. Bindable because the gate exposes
    evaluate(record, index) over the resolved estate, the same convention the invariant gate set."""
    m = _load("tests/check_composition_promotion.py", "_promo")
    return m.evaluate(record, m.load_index())


def _fulfillment_conditions(record):
    """FUL-001/002/003 — a blocked member must be actionable. Bindable via evaluate(record, index)."""
    m = _load("tests/check_fulfillment_conditions.py", "_ful")
    return m.evaluate(record, m.load_index())


def _ownership(record):
    """OWN-002/007/008 — evaluates one type declaration on its own."""
    m = _load("registry/tools/validate.py", "_val")
    return m.check_ownership_declaration(record)


GATES = {
    "check_grant_derivation": _grant_derivation,
    "check_ownership_declaration": _ownership,
    "check_group_invariants": _group_invariants,
    "check_catalog_item": _catalog_item,
    "schema": _schema,
    "check_class_constituents": _class_constituents,
    "check_composition_promotion": _composition_promotion,
    "check_fulfillment_conditions": _fulfillment_conditions,
}


def main():
    files = sorted(glob.glob(os.path.join(CASES, "*.yaml")))
    fails, checked = [], 0
    for path in files:
        rel = os.path.relpath(path, ROOT)
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        spec = doc.get("must_reject") or {}
        gate, rule = spec.get("gate"), spec.get("rule")
        if gate not in GATES:
            fails.append(f"MRJ-002 {rel}: names gate {gate!r}, which this runner cannot bind — "
                         f"bindable: {', '.join(sorted(GATES))}")
            continue
        if not rule or not spec.get("because"):
            fails.append(f"MRJ-002 {rel}: a case must name the rule it violates and say why")
            continue
        checked += 1
        errors = GATES[gate](doc.get("record") or {})
        if not errors:
            fails.append(f"MRJ-001 {rel}: {gate} ACCEPTED it. The case claims {rule} refuses this; "
                         f"either the model stopped refusing it, or the case no longer provokes it.")
            continue
        if gate == "schema":
            # Schema validation reports a failing JSON path, never a rule ID — it cannot know which
            # requirement a pattern encodes. So a schema-gated case names the path that must fail and
            # is checked against that. Same standard, different evidence: it still has to be refused
            # for the stated reason rather than for any reason at all.
            want = spec.get("expect_path")
            if not want:
                fails.append(f"MRJ-002 {rel}: a schema-gated case must name `expect_path` — the path "
                             f"that has to fail. Without it the case proves only that SOMETHING was "
                             f"refused, which is how a case passes for the wrong reason.")
            elif not any(want in e for e in errors):
                fails.append(f"MRJ-002 {rel}: refused, but not at {want} — got {errors[0][:90]!r}. "
                             f"The case is passing for the wrong reason, which is not passing.")
        elif not any(rule in e for e in errors):
            fails.append(f"MRJ-002 {rel}: refused, but not by {rule} — got {errors[0][:90]!r}. "
                         f"The case is passing for the wrong reason, which is not passing.")

    # self-test: the runner must be able to report an acceptance, or it only proves the loop ran
    if _ownership({"resource_type": "P", "ownership_model": "shareable"}):
        print("FAIL [MRJ-SELF] a valid declaration was reported as refused")
        fails.append("self-test")

    print(f"must-reject: {checked} of {len(files)} case(s) executed against a bound gate")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} case(s) not refused as claimed")
        return 1
    print("OK — every case is refused, by the rule it names")
    return 0


if __name__ == "__main__":
    sys.exit(main())
