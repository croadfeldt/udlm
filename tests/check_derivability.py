#!/usr/bin/env python3
"""Derivability gate (DRV-001): is the value derivable? If so, is it required to store it here?

Rule home: registry/SPEC-DESIGN-REQUIREMENTS.md § "Derivability — don't store what the model
computes" (DRV-001).

Maintainer ruling (2026-07-25, from the Automation.Job run-history finding): values derivable
from other model records — run instances, relationships, provenance — must not be stored as
independent facts, because a stored copy of a derivable value is a drift waiting to happen
(the compute-never-store rule: derived shape, nature, portability are the precedents).

This gate is deliberately narrow and mechanical: it reads NAMES, not semantics. A field whose
name is shaped like a history/recency fact or an aggregation must either
(a) declare its classification — description contains 'DERIVED' (with the source named) or
'OBSERVED' (a provider-watched fact not derivable from model records) — or
(b) not exist on the type at all (the run-scoped pattern: instance facts live on instances).
Everything subtler — spec fields duplicating relationship-derivable data, counts that are
intent versus observation — is the cleanliness review's derivability question (judgment), not
this gate (mechanism).

Scope, and the two limits it buys (2026-07-25 hardening):
  - HISTORY/RECENCY names (last_*, latest_*, previous_*, runs_*, history_*, *_history,
    *_completed) are checked on BOTH `outputs` and `spec`. A history fact is never intent, so
    a spec field shaped like one is a stored derivable by construction. Caught nothing on the
    current corpus — it is the forward guard.
  - AGGREGATION names (total_*, num_*, count_*, sum_*, avg_*, average_*, current_*, *_count,
    *_total, *_sum, *_average, *_avg) are checked on `outputs` ONLY. In a spec an aggregate
    name can be legitimate intent (a requested replica count), so flagging it there would be a
    false positive; in outputs it is a realized reading that must say where it comes from.
    Caught four live undeclared readings (occupant_count, allocated_count, free_count,
    managed_cluster_count) that the original `^(last_|runs_|total_|history_|previous_)|_completed$`
    pattern missed entirely.
  - The `outputs-exempt:` note no longer excuses a DECLARED output. Its job is to explain why a
    realizable type declares NO outputs (check_type_standard G1); as a blanket file-level
    escape it let an exempt type add any history-shaped output for free.
Known limits (deliberate): names only — a derivable value under a neutral name
(`occupancy`, `usage`) is the reviewer's call, not the gate's; and only type specs under
registry/resource-types are read.
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "registry" / "tools"))
from fuzz_type_specs import load  # noqa: E402

TYPES = pathlib.Path(__file__).resolve().parent.parent / "registry" / "resource-types"

# History / recency shapes — a point-in-time fact about what already happened.
HISTORY = re.compile(r"^(last_|latest_|previous_|prior_|runs_|history_)|(_history|_completed)$", re.I)
# Aggregation shapes — a rollup over records the model already holds.
AGGREGATE = re.compile(r"^(total_|num_|count_|sum_|avg_|average_|current_)|"
                       r"(_count|_total|_sum|_average|_avg)$", re.I)


def undeclared(schema):
    desc = (schema or {}).get("description", "") or ""
    return "DERIVED" not in desc and "OBSERVED" not in desc


def main():
    failures = []
    n = 0
    for p in sorted(TYPES.rglob("*")):
        if p.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(p)
        n += 1
        rt = doc.get("resource_type", p.name)
        for name, schema in (doc.get("outputs") or {}).items():
            shape = ("history/aggregation-shaped" if HISTORY.search(name)
                     else "aggregation-shaped" if AGGREGATE.search(name) else None)
            if shape and undeclared(schema):
                failures.append(
                    f"FAIL [DRV-001] {rt}: output '{name}' is {shape} — declare DERIVED (with "
                    f"source) or OBSERVED, or move it to the instance type")
        spec_props = ((doc.get("spec") or {}).get("properties")
                      if isinstance(doc.get("spec"), dict) else None) or {}
        for name, schema in spec_props.items():
            if HISTORY.search(name) and undeclared(schema):
                failures.append(
                    f"FAIL [DRV-001] {rt}: spec field '{name}' is history-shaped — a history fact "
                    f"is not intent; derive it from the instance records, or declare DERIVED/OBSERVED")
    for f in failures:
        print(f)
    print(f"{n} types checked, {len(failures)} derivability violation(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
