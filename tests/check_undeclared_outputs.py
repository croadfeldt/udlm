#!/usr/bin/env python3
"""Outputs on a record are checked against the class that declares them (UDO-001..003, row 136).

A class declares its outputs (the contract records are checked against) or declares `outputs_exempt`
(nothing to check). A realized or discovered record may carry outputs the class did not declare: they
are kept but unpromised — nothing may bind to them — and counted here so a recurring one is promoted
into the class rather than left as a stray.

  UDO-001  a record of an `outputs_closed` class carries an undeclared output          -> FAIL
  UDO-002  a dependency's `bound_field` names an output the class does not declare       -> FAIL
  UDO-003  an undeclared output on an open class                                         -> count, reported
"""
import glob
import json
import os
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLES = os.path.join(REPO, "registry", "examples")


def served():
    """resource_type -> (declared output names, outputs_closed, outputs_exempt)."""
    out = {}
    for f in glob.glob(os.path.join(REPO, "registry", "generated", "*.json")):
        d = json.load(open(f, encoding="utf-8"))
        rt = d.get("resource_type")
        if not rt:
            continue
        outs = d.get("outputs") or {}
        names = set(outs.keys()) if isinstance(outs, dict) else {o.get("name") for o in outs if isinstance(o, dict)}
        out[rt] = (names, bool(d.get("outputs_closed")), bool(d.get("outputs_exempt")))
    return out


def records():
    for f in sorted(glob.glob(os.path.join(EXAMPLES, "*.yaml"))):
        try:
            docs = list(yaml.safe_load_all(open(f, encoding="utf-8")))
        except Exception:
            continue
        for d in docs:
            if isinstance(d, dict) and str(d.get("record_type", "")).endswith("_record") and d.get("resource_type"):
                yield os.path.relpath(f, REPO), d


def main():
    classes = served()
    fails, counts = [], {}
    n = 0
    for rel, rec in records():
        rt = rec["resource_type"]
        if rt not in classes:
            continue
        declared, closed, exempt = classes[rt]
        n += 1
        outs = rec.get("outputs")
        if isinstance(outs, dict) and not exempt:
            for k in outs:
                if k not in declared:
                    if closed:
                        fails.append(f"UDO-001 {rel}: {rt} is outputs_closed and the record carries undeclared output {k!r}")
                    else:
                        counts[(rt, k)] = counts.get((rt, k), 0) + 1
        for dep in rec.get("dependencies") or []:
            bf = dep.get("bound_field") if isinstance(dep, dict) else None
            if isinstance(bf, str) and bf.startswith("outputs."):
                name = bf.split(".", 1)[1].split(".", 1)[0]
                if exempt or name not in declared:
                    fails.append(f"UDO-002 {rel}: bound_field {bf!r} names an output {rt} does not declare")
    for f in fails:
        print("FAIL", f)
    for (rt, k), c in sorted(counts.items()):
        print(f"  UDO-003 {rt}.{k}: undeclared output on {c} record(s) — unpromised; promote it into the class if it keeps appearing")
    print(f"undeclared outputs: {n} record(s) checked; {len(fails)} failure(s); {len(counts)} undeclared output name(s) counted")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
