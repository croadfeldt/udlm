#!/usr/bin/env python3
"""The collapse check — a selection must fall inside the offer it was selected from.

A Provider Class declares what it OFFERS (`supports`: values, ranges, grouped clauses) and what it
REQUIRES (elements marked `optional: false`). A request is that document with each range collapsed
to ONE selected value — or nothing, where the element is optional. Layers and policies perform the
collapse; the convergence loop runs until every range has become a value.

This gate checks the collapse actually landed inside the offer. Without it the offer is
documentation: a provider could declare 1-64 vCPUs and a record could claim 4096 with nothing
objecting.

It is also what makes **placement eligibility computable rather than asserted**. `request-realization`
says placement narrows to providers "whose declared capability and capacity satisfy the request";
that sentence is only true if the satisfying can be evaluated. This is the evaluation.

  OFR-001  a selected value satisfies at least one support clause whose `when` matches the other
           selections. A value can be individually offered and still be an invalid COMBINATION —
           512Gi is real under memory-optimized and not under general — and that is the case worth
           catching, because nothing else would.
  OFR-002  every element the class marks `optional: false` is present in the selection. An optional
           element may collapse to nothing; a required one may not.

**Linkage.** An instance names its portable type in `resource_type` (two segments — it IS a
Compute.VM) and pins the spec it was realized against in `type_ref`, the `$id` of that spec. After
placement that spec is the Provider Class, so `type_ref` is the existing carrier and no new field is
needed. An instance whose `type_ref` names no known class is skipped, not failed — pinning a served
type spec rather than a Provider Class is legitimate and common.

Exit 0 = every selection sits inside its offer; 1 = at least one does not.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASS_ROOTS = [os.path.join(ROOT, "registry", "classes"),
               os.path.join(ROOT, "registry", "examples", "classes")]
INSTANCE_ROOTS = [os.path.join(ROOT, "registry", "instances"),
                  os.path.join(ROOT, "registry", "examples")]

_QTY = re.compile(r"^[0-9]+(\.[0-9]+)?(m|[KMGTPE]i?B?)?$")
_UNIT = {"": 1, "m": 1e-3, "K": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18,
         "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "Pi": 2**50, "Ei": 2**60}


def _num(v):
    """A comparable magnitude — a number, or a Quantity string normalised. None when neither."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str) or not _QTY.match(v):
        return None
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)(.*)$", v)
    unit = m.group(2)
    unit = "" if unit == "B" else unit.rstrip("B")
    return float(m.group(1)) * _UNIT.get(unit, 1)


def load_classes():
    by_id, by_name = {}, {}
    for root in CLASS_ROOTS:
        for p in glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True):
            d = yaml.safe_load(open(p, encoding="utf-8")) or {}
            if d.get("record_type") == "class":
                by_name[d.get("resource_type")] = d
                if d.get("$id"):
                    by_id[d["$id"]] = d
    return by_id, by_name


def _selected(inst):
    """The collapsed values. `requested` is the converged selection; fall back to intent/realized so
    a partially-progressed record is still checkable."""
    states = inst.get("states") or {}
    for name in ("requested", "realized", "intent"):
        fields = ((states.get(name) or {}).get("fields") or {})
        if fields:
            return name, fields
    return None, {}


def _leaf(value, schema):
    """A support clause names the leaf a consumer selects. Where the element is an object with one
    required property, the selection is that property's value."""
    req = (schema or {}).get("required") or []
    if isinstance(value, dict) and len(req) == 1 and req[0] in value:
        return value[req[0]]
    return value


def clause_admits(clause, value, selections):
    """Does this clause admit `value`, given the other selections? `when` is equality only."""
    for k, want in (clause.get("when") or {}).items():
        if str(selections.get(k)) != str(want):
            return False
    if "values" in clause and any(str(v) == str(value) for v in clause["values"]):
        return True
    lo, hi, val = _num(clause.get("min")), _num(clause.get("max")), _num(value)
    if val is None or (lo is None and hi is None):
        return False
    if lo is not None and val < lo:
        return False
    if hi is not None and val > hi:
        return False
    step = _num(clause.get("step"))
    if step and lo is not None and abs(((val - lo) / step) - round((val - lo) / step)) > 1e-9:
        return False
    return True


def check_instance(inst, cls, where):
    errs = []
    state, fields = _selected(inst)
    if state is None:
        return errs
    flat = {k: _leaf(v, {}) for k, v in fields.items()}
    for el in cls.get("elements") or []:
        name = el["element"]
        # OFR-002 — a required element may not collapse to nothing
        if el.get("optional") is False and name not in fields:
            errs.append(f"OFR-002 {where}: {cls['resource_type']} requires {name!r}, and the "
                        f"{state} selection does not carry it")
            continue
        if name not in fields or not el.get("supports"):
            continue
        value = _leaf(fields[name], el.get("schema") or {})
        # OFR-001 — the value must satisfy a clause whose `when` matches the OTHER selections
        if not any(clause_admits(c, value, flat) for c in el["supports"]):
            ctx = {k: v for k, v in flat.items() if k != name}
            errs.append(f"OFR-001 {where}: {name}={value!r} is outside every clause "
                        f"{cls['resource_type']} offers for it (given {ctx or 'no other selections'}) "
                        f"— the collapse landed outside the offer")
    return errs


def main():
    by_id, by_name = load_classes()
    fails, checked, skipped = [], 0, 0
    for root in INSTANCE_ROOTS:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            rel = os.path.relpath(p, ROOT)
            for inst in docs:
                if not isinstance(inst, dict) or "states" not in inst:
                    continue
                cls = by_id.get(inst.get("type_ref")) or by_name.get(inst.get("resource_type"))
                if not cls:
                    skipped += 1
                    continue
                checked += 1
                fails += check_instance(inst, cls, rel)

    # self-test: the gate must be able to fail, and the COMBINATION case is the one that matters
    probe_cls = {"resource_type": "T", "elements": [
        {"element": "memory", "optional": True, "schema": {},
         "supports": [{"min": "8Gi", "max": "384Gi", "when": {"family": "general"}},
                      {"min": "8Gi", "max": "768Gi", "when": {"family": "memory-optimized"}}]}]}
    combo = check_instance({"states": {"requested": {"fields": {"memory": "512Gi", "family": "general"}}}},
                           probe_cls, "self_test")
    if not combo:
        print("FAIL [OFR-SELF] the gate admitted a value valid under ANOTHER group — the matrix is decorative")
        fails.append("self-test")
    ok = check_instance({"states": {"requested": {"fields": {"memory": "512Gi", "family": "memory-optimized"}}}},
                        probe_cls, "self_test")
    if ok:
        print("FAIL [OFR-SELF] the gate refused a value its own clause admits")
        fails.append("self-test")

    print(f"offer-collapse: {checked} selection(s) checked against a declared offer, "
          f"{skipped} with no class pinned")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} selection(s) outside the offer")
        return 1
    print("OK — every selection sits inside the offer it was selected from")
    return 0


if __name__ == "__main__":
    sys.exit(main())
