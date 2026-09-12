#!/usr/bin/env python3
"""An entity is stored as one record per state — never as one folded record (RHY-006).

This is the model as it was specified from the start: the four states of an entity are four
separate records, each written once by one party. For a year the instance schema said otherwise —
it folded the four into one document with one identity — and the corpus, the gates and the docs
followed the schema instead of the spec. Ruling 071 put it right. This gate is what keeps it right:
a folded record cannot be authored again without CI saying so.

  SRO-001  a document under the authored corpus carries a `states` block. That is the shape of the
           entity VIEW (registry/entity-view.schema.json), which is assembled on demand and never
           written. The one allowed exception is the worked view registry/examples/orders-db.json.
  SRO-002  a document carries `drift` or `ownership`. Drift is computed from the newest discovered
           and realized records; ownership refereed several writers on one document and a per-state
           record has one author. Neither is stored on anything.
  SRO-003  a document looks like the old instance shape — `resource_type` + `lifecycle_state` with no
           `record_type` — outside the allowed view. A per-state record says which state it is.

Scans registry/examples/** (must-reject cases included — their nested `record` is what a gate is
handed, and a folded case would teach the wrong shape), registry/instances/**, and the root
`examples` of every registry meta-schema except entity-view's. Exit 0 = clean; 1 = a folded record
exists. Self-tests a synthetic folded record so a gate that cannot fail proves nothing.
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = [os.path.join(ROOT, "registry", "examples"), os.path.join(ROOT, "registry", "instances")]
ALLOWED_VIEWS = {os.path.join("registry", "examples", "orders-db.json")}
STATE_KINDS = {"intent_record", "requested_record", "realized_record", "discovered_record"}


def _docs(path):
    try:
        if path.endswith(".json"):
            d = json.load(open(path, encoding="utf-8"))
            return [d] if isinstance(d, dict) else []
        return [d for d in yaml.safe_load_all(open(path, encoding="utf-8")) if isinstance(d, dict)]
    except Exception:
        return []


def judge(doc, where, allowed_view=False):
    """The rules over one document (a must-reject case's nested `record` is judged as itself)."""
    fails = []
    if isinstance(doc.get("record"), dict) and "must_reject" in doc:
        return judge(doc["record"], where + " (record)")
    if "states" in doc and not allowed_view:
        fails.append(f"SRO-001 {where}: carries a `states` block — that is the entity view, assembled and never "
                     f"written; store one record per state (registry/state-record.schema.json)")
    for k in ("drift", "ownership"):
        if k in doc and not allowed_view:
            fails.append(f"SRO-002 {where}: carries `{k}` — never stored on a record (RHY-006)")
    if (doc.get("resource_type") and doc.get("lifecycle_state") and doc.get("record_type") not in STATE_KINDS
            and not allowed_view and "states" not in doc):
        fails.append(f"SRO-003 {where}: looks like the retired folded instance shape (resource_type + "
                     f"lifecycle_state, no record_type) — a per-state record says which state it is")
    return fails


def scan():
    fails, n = [], 0
    for root in SCAN:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)
                        + glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
            if os.sep + "classes" + os.sep in p:
                continue
            rel = os.path.relpath(p, ROOT)
            for i, d in enumerate(_docs(p)):
                n += 1
                fails += judge(d, f"{rel}#{i}", allowed_view=rel in ALLOWED_VIEWS)
    for p in sorted(glob.glob(os.path.join(ROOT, "registry", "*.schema.json"))):
        if p.endswith("entity-view.schema.json"):
            continue
        try:
            ex = json.load(open(p, encoding="utf-8")).get("examples") or []
        except Exception:
            continue
        for i, d in enumerate(ex):
            if isinstance(d, dict):
                n += 1
                fails += judge(d, f"{os.path.relpath(p, ROOT)} examples[{i}]")
    return n, fails


def main():
    probe = judge({"uuid": "x", "resource_type": "Machine.VM", "lifecycle_state": "Realized",
                   "states": {"realized": {"fields": {}}}, "drift": {"detected": False}}, "self_test")
    fails = [] if any("SRO-001" in f for f in probe) and any("SRO-002" in f for f in probe) else ["SRO-SELF: the gate did not catch a synthetic folded record"]
    n, found = scan()
    fails += found
    for f in fails:
        print("FAIL [" + f.split()[0].rstrip(":") + "] " + f)
    print(f"{n} document(s) checked, {len(fails)} folded-record violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
