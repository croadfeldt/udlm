#!/usr/bin/env python3
"""Every shipped entity folds into a valid view (EVW-001).

The entity view is the read model computed from an entity's per-state records
(registry/ENTITY-VIEW.md, ruling 071): registry/tools/entity_view.py folds the latest record of
each state into the shape registry/entity-view.schema.json describes. Nothing stores the view, so
nothing validated it — and a record field the view carries but the view schema does not declare
(a reference head, say) surfaced first in a consumer's parity test, not here. This gate folds
every entity whose records ship under registry/examples/ and registry/instances/ and validates the
result against the view schema.

  EVW-001  the view built from an entity's shipped records validates against entity-view.schema.json.

Self-tests that a view with an undeclared snapshot key fails, so the gate cannot pass vacuously.
"""
import glob
import json
import os
import sys

import yaml

try:
    import jsonschema
    from referencing import Registry, Resource
except ImportError:
    sys.exit("requires: pip install jsonschema referencing pyyaml")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "registry", "tools"))
import entity_view  # noqa: E402

SCAN = [os.path.join(ROOT, "registry", "examples"), os.path.join(ROOT, "registry", "instances")]


def validator():
    reg_dir = os.path.join(ROOT, "registry")
    store = Registry()
    docs = {}
    for name in ("entity-view.schema.json", "state-record.schema.json", "common-elements.schema.json", "policy.schema.json"):
        d = json.load(open(os.path.join(reg_dir, name), encoding="utf-8"))
        docs[name] = d
        res = Resource.from_contents(d)
        store = store.with_resource(d["$id"], res).with_resource(name, res)
    return jsonschema.Draft202012Validator(docs["entity-view.schema.json"], registry=store)


def records():
    out = []
    for root in SCAN:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            if os.sep + "must-reject" + os.sep in p or os.sep + "classes" + os.sep in p:
                continue
            try:
                docs = [d for d in yaml.safe_load_all(open(p, encoding="utf-8")) if isinstance(d, dict)]
            except Exception:
                continue
            for d in docs:
                if entity_view.is_state_record(d):
                    d["_path"] = os.path.relpath(p, ROOT)
                    out.append(d)
    return out


def strip(view):
    return {k: v for k, v in view.items() if not k.startswith("_")}


def main():
    v = validator()
    # self-test: an undeclared key on a snapshot must fail
    probe = {"uuid": "2f7c9a41-8e3d-4b6a-9c15-7d2e4f8a1b03", "tenant_uuid": "75ccf4ff-3e8d-4963-bc51-459ae1014cb7",
             "conforms_to": "udlm/0.1", "resource_type": "Machine.VM", "type_version": "2.0.0",
             "lifecycle_state": "Intent", "states": {"intent": {"fields": {}, "bogus": 1}}}
    if not list(v.iter_errors(probe)):
        print("FAILED — self-test: a view with an undeclared snapshot key validated")
        return 1
    recs = records()
    views = entity_view.build_views(recs)
    fails = []
    for uuid, view in sorted(views.items()):
        if not entity_view.is_state_record(next((r for r in recs if r.get("entity_uuid") == uuid), {})):
            continue
        for e in v.iter_errors(strip(view)):
            loc = "/".join(map(str, e.absolute_path)) or "<root>"
            fails.append(f"EVW-001 {view.get('_path')} entity {uuid} @ {loc}: {e.message[:160]}")
    for f in fails:
        print("FAIL " + f)
    n = sum(1 for view in views.values() if any(r.get("entity_uuid") == view.get("uuid") for r in recs))
    print(f"{n} entit(y|ies) folded from {len(recs)} shipped records, {len(fails)} invalid view(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
