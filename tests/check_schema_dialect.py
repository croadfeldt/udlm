#!/usr/bin/env python3
"""WIR-030 — every schema declares JSON Schema Draft 2020-12.

`CONFORMANCE.md` §6 requires it of a conformant implementation, and it is the one wire requirement
that is checkable here without a peer to talk to: the schemas ARE the artifact. All 20 comply today;
nothing has ever verified that, so nothing would notice a new schema arriving on an older dialect.

The failure is quiet rather than loud, which is why it wants a gate. A Draft-07 schema mostly works:
it parses, it validates the easy cases, and it silently ignores `$defs`, `unevaluatedProperties`, and
`dependentSchemas` — so a constraint the author wrote is simply not applied, and everything passes.

  SCD-001  a schema under registry/ declares `$schema` and it is the 2020-12 dialect.

**A missing `$schema` is a failure, not a skip.** Without it a validator picks a default, and which
default depends on the library — so the same document validates differently in two implementations,
which is precisely the interoperability the wire-compatibility checklist exists to protect.

Exit 0 = every schema declares the dialect; 1 = at least one does not.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIALECT = "https://json-schema.org/draft/2020-12/schema"


def check(doc, rel):
    """One schema document. Bindable per #434's convention."""
    declared = doc.get("$schema")
    if not declared:
        return [f"SCD-001 {rel}: declares no `$schema`. A validator then picks a default, and which "
                f"default depends on the library — the same document validates differently in two "
                f"implementations, which is the interoperability this exists to protect."]
    if declared.rstrip("#") != DIALECT:
        return [f"SCD-001 {rel}: declares {declared!r}, not Draft 2020-12. An older dialect silently "
                f"ignores $defs, unevaluatedProperties and dependentSchemas, so a constraint the "
                f"author wrote is never applied and everything passes."]
    return []


def main():
    fails, n = [], 0
    for p in sorted(glob.glob(os.path.join(ROOT, "registry", "**", "*.schema.json"), recursive=True)):
        n += 1
        rel = os.path.relpath(p, ROOT)
        try:
            doc = json.load(open(p, encoding="utf-8"))
        except Exception as e:
            fails.append(f"SCD-001 {rel}: not parseable as JSON — {e}")
            continue
        fails += check(doc, rel)

    # self-test: both arms, or the gate only proves the walk ran
    if not check({}, "probe"):
        print("FAIL [SCD-SELF] a schema with no $schema was accepted")
        fails.append("self-test")
    if not check({"$schema": "http://json-schema.org/draft-07/schema#"}, "probe"):
        print("FAIL [SCD-SELF] an older dialect was accepted")
        fails.append("self-test")
    if check({"$schema": DIALECT}, "probe"):
        print("FAIL [SCD-SELF] the correct dialect was refused")
        fails.append("self-test")

    print(f"schema-dialect: {n} schema(s) checked for Draft 2020-12")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} schema(s) on the wrong dialect")
        return 1
    print("OK — every schema declares Draft 2020-12")
    return 0


if __name__ == "__main__":
    sys.exit(main())
