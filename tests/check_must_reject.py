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


def _ownership(record):
    """OWN-002/007/008 — evaluates one type declaration on its own."""
    m = _load("registry/tools/validate.py", "_val")
    return m.check_ownership_declaration(record)


GATES = {
    "check_grant_derivation": _grant_derivation,
    "check_ownership_declaration": _ownership,
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
        if not any(rule in e for e in errors):
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
