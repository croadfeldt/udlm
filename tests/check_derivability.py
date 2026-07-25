#!/usr/bin/env python3
"""Derivability gate: is the value derivable? If so, is it required to store it here?

Maintainer ruling (2026-07-25, from the Automation.Job run-history finding): values derivable
from other model records — run instances, relationships, provenance — must not be stored as
independent facts, because a stored copy of a derivable value is a drift waiting to happen
(the compute-never-store rule: derived shape, nature, portability are the precedents).

This v1 is deliberately narrow and mechanical: OUTPUT names shaped like run/history
aggregations (last_*, runs_*, *_completed, total_*, history_*, previous_*) must either
(a) declare their classification — description contains 'DERIVED' (with the source named)
or 'OBSERVED' (a provider-watched fact not derivable from model records) — or
(b) not exist on the type at all, with the doc carrying an 'outputs-exempt:' rationale
(the run-scoped pattern: instance facts live on instances). Everything subtler — spec fields
duplicating relationship-derivable data, counts that are intent versus observation — is the
cleanliness review's derivability question (judgment), not this gate (mechanism).
"""
import re
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "registry" / "tools"))
from fuzz_type_specs import load  # noqa: E402

TYPES = pathlib.Path(__file__).resolve().parent.parent / "registry" / "resource-types"
PATTERN = re.compile(r"^(last_|runs_|total_|history_|previous_)|_completed$")


def main():
    failures = []
    n = 0
    for p in sorted(TYPES.rglob("*")):
        if p.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(p)
        n += 1
        text = p.read_text()
        for name, schema in (doc.get("outputs") or {}).items():
            if PATTERN.search(name):
                desc = (schema or {}).get("description", "")
                if "DERIVED" not in desc and "OBSERVED" not in desc and "outputs-exempt:" not in text:
                    failures.append(
                        f"FAIL [DRV-001] {doc.get('resource_type', p.name)}: output '{name}' is "
                        f"history/aggregation-shaped — declare DERIVED (with source) or OBSERVED, move it to "
                        f"the instance type, or exempt the doc")
    for f in failures:
        print(f)
    print(f"{n} types checked, {len(failures)} derivability violation(s)")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
