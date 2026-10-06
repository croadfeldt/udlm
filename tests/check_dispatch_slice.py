#!/usr/bin/env python3
"""Dispatch is zero trust; the requested record is the receipt (DSP-002/003/004).

A provider receives nothing by default (DSP-001). The requested record's `dispatch` block records
exactly what crossed: the elements of the class the provider binds (DSP-002) plus each path a
policy granted (DSP-003), minus each path a policy stripped. This gate holds the receipt to the
rule (data-roles.md §3):

  DSP-002  every admitted path is an element of the record's class (the served flat spec's `spec`
           properties, by first path segment) — unless a grant names it. A class element declared
           with a non-execution `role` is not required and may not be admitted without a grant.
  DSP-003  every grant names a policy that appears in the record's `policies[]` with decision
           `allow`; a stripped path is not also admitted.
  DSP-004  a requested record carries `dispatch` (records written before ruling 081 are declared
           debt in tests/dispatch_slice_baseline.txt, which only shrinks).

Scans registry/examples/** and registry/instances/**. Self-tests an admitted path outside the
class with no grant, a grant whose policy is absent, and a stripped-and-admitted path, so the gate
cannot pass vacuously. Bindable from tests/check_must_reject.py as `judge(record, index)`.
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = [os.path.join(ROOT, "registry", "examples"), os.path.join(ROOT, "registry", "instances")]
BASELINE = os.path.join(ROOT, "tests", "dispatch_slice_baseline.txt")


def load_index():
    """resource_type -> (execution element names, non-execution element names) from the served specs."""
    idx = {}
    for p in glob.glob(os.path.join(ROOT, "registry", "generated", "*.json")):
        d = json.load(open(p, encoding="utf-8"))
        props = (d.get("spec") or {}).get("properties") or {}
        roles = d.get("element_roles") or {}  # a compiled spec may carry element roles; absent = execution
        execution = {k for k in props if roles.get(k, "execution") == "execution"}
        idx[d.get("resource_type")] = (execution, set(props) - execution)
    # Provider Classes are not served as flat specs (generate_class_specs serves Types and orderable
    # Bases), yet a record may bind one. Its element set is its parent's plus what it declares.
    import yaml
    provider_classes = []
    for p in glob.glob(os.path.join(ROOT, "registry", "classes", "**", "*.yaml"), recursive=True):
        try:
            d = yaml.safe_load(open(p, encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        if d.get("record_type") == "class" and d.get("class") == "provider":
            provider_classes.append(d)
    for d in sorted(provider_classes, key=lambda c: c["resource_type"].count(".")):
        parent_exe, parent_ctl = idx.get(d.get("parent"), (set(), set()))
        own = d.get("elements") or []
        exe = {e["element"] for e in own if e.get("role", "execution") == "execution"}
        ctl = {e["element"] for e in own if e.get("role", "execution") != "execution"}
        idx[d["resource_type"]] = ((parent_exe | exe) - ctl, (parent_ctl | ctl) - exe)
    return idx


def head(path):
    for i, ch in enumerate(path):
        if ch in ".[":
            return path[:i]
    return path


def judge(rec, index, where=""):
    # A caller may hand over the entity VIEW (tests/check_must_reject.py does): judge its requested
    # snapshot, with the view's envelope, as the requested record.
    if "states" in rec and "requested" in (rec.get("states") or {}):
        snap = rec["states"]["requested"] or {}
        rec = {**{k: v for k, v in rec.items() if k != "states"}, **snap, "record_type": "requested_record"}
    if rec.get("record_type") != "requested_record":
        return []
    where = where or rec.get("handle") or rec.get("record_uuid")
    disp = rec.get("dispatch")
    if disp is None:
        return [f"DSP-004 {where}: requested record carries no `dispatch` receipt"]
    fails = []
    execution, control = index.get(rec.get("resource_type"), (set(), set()))
    granted = {g.get("path"): g for g in disp.get("granted") or []}
    stripped = {s.get("path") for s in disp.get("stripped") or []}
    allowed_policies = {p.get("policy") for p in rec.get("policies") or [] if p.get("decision") == "allow"}
    for path in disp.get("admitted") or []:
        h = head(path)
        if path in granted or h in granted:
            continue
        if h in control:
            fails.append(f"DSP-002 {where}: admitted `{path}` is a non-execution element of {rec.get('resource_type')} and no policy granted it")
        elif h not in execution:
            fails.append(f"DSP-002 {where}: admitted `{path}` is not an element of {rec.get('resource_type')} and no policy granted it")
        if path in stripped:
            fails.append(f"DSP-003 {where}: `{path}` is both admitted and stripped")
    for path, g in granted.items():
        if g.get("policy") not in allowed_policies:
            fails.append(f"DSP-003 {where}: grant of `{path}` names policy {g.get('policy')!r}, which is not in policies[] with decision allow")
    return fails


def _docs(path):
    try:
        if path.endswith(".json"):
            d = json.load(open(path, encoding="utf-8"))
            return [d] if isinstance(d, dict) else []
        return [d for d in yaml.safe_load_all(open(path, encoding="utf-8")) if isinstance(d, dict)]
    except Exception:
        return []


def baseline():
    if not os.path.exists(BASELINE):
        return set()
    return {ln.strip() for ln in open(BASELINE, encoding="utf-8") if ln.strip() and not ln.startswith("#")}


def key(finding):
    code, rest = finding.split(" ", 1)
    subject = rest.split("`")[1] if "`" in rest else rest.split(":", 1)[0]
    return f"{code} {rest.split(':', 1)[0]} {subject}" if "`" in rest else f"{code} {subject}"


def self_test():
    index = {"Machine.VM": ({"cpu", "memory", "networks"}, {"cost_attribution"})}
    refused = {"record_type": "requested_record", "resource_type": "Machine.VM", "handle": "r",
               "status": {"state": "pending", "conditions": [{"type": "refused", "status": "True"}]},
               "dispatch": {"provider": "estate/control-plane", "admitted": [], "granted": [], "stripped": []}}
    if judge(refused, index, "self-test"):
        print("FAIL self-test: a refused request's empty receipt (DSP-004, row 091) was flagged")
        return 1
    good = {"record_type": "requested_record", "resource_type": "Machine.VM", "handle": "t",
            "policies": [{"policy": "lab/policy/placement-facts", "decision": "allow"}],
            "dispatch": {"provider": "p", "admitted": ["cpu.count", "memory.size", "placement.location_ref"],
                         "granted": [{"path": "placement.location_ref", "policy": "lab/policy/placement-facts"}], "stripped": []}}
    assert judge(good, index) == [], judge(good, index)
    bad = json.loads(json.dumps(good)); bad["dispatch"]["granted"] = []
    assert any(f.startswith("DSP-002") for f in judge(bad, index)), "ungranted path outside the class must fail"
    bad = json.loads(json.dumps(good)); bad["policies"] = []
    assert any(f.startswith("DSP-003") for f in judge(bad, index)), "grant without an allowing policy must fail"
    bad = json.loads(json.dumps(good)); bad["dispatch"]["admitted"].append("cost_attribution")
    assert any("non-execution" in f for f in judge(bad, index)), "admitting a non-execution element must fail"
    bad = json.loads(json.dumps(good)); bad["dispatch"]["stripped"] = [{"path": "cpu.count", "policy": "x"}]
    assert any("both admitted and stripped" in f for f in judge(bad, index)), "admitted-and-stripped must fail"
    assert judge({"record_type": "requested_record", "resource_type": "Machine.VM", "handle": "t"}, index)[0].startswith("DSP-004")


def main():
    self_test()
    index = load_index()
    findings = []
    n = 0
    for root in SCAN:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            if os.sep + "must-reject" + os.sep in p or os.sep + "classes" + os.sep in p:
                continue
            rel = os.path.relpath(p, ROOT)
            for i, d in enumerate(_docs(p)):
                if d.get("record_type") == "requested_record":
                    n += 1
                    findings += judge(d, index, f"{rel}#{i}")
    known = baseline()
    keys = {key(f): f for f in findings}
    new = [f for k, f in keys.items() if k not in known]
    stale = sorted(k for k in known if k not in keys)
    for k, f in sorted(keys.items()):
        print(("WARN(baseline) " if k in known else "FAIL ") + f)
    for k in stale:
        print(f"STALE-BASELINE {k} — no longer fails; remove it from tests/dispatch_slice_baseline.txt")
    print(f"\n{n} requested record(s), {len(findings)} finding(s): {len(findings) - len(new)} baselined, {len(new)} new, {len(stale)} stale")
    return 1 if new or stale else 0


if __name__ == "__main__":
    sys.exit(main())
