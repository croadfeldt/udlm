#!/usr/bin/env python3
"""UC persona-vocabulary gate — every use case's scenario.actor.persona must resolve to the
canonical persona set (use-cases/PERSONAS.yaml).

Why: the persona a use case is written from was a free string enforced nowhere, and had drifted to
12 distinct values across udlm + dcm (auditor vs compliance-auditor vs compliance-officer;
storage-admin/individual-developer singletons; sovereign-tenant-admin vs tenant-admin). A consumer
told to analyze "from every stakeholder perspective" would otherwise carry its own private persona
list — the same fork DIM-001 closed for the dimension vocabulary. This gate makes the persona set a
closed, single-sourced contract so drift is caught at authoring, not lost at analysis time. Wire
into CI + signoff (mirrors DIM-001 / check_uc_dimensions.py).

A persona value is in-vocabulary if it is a canonical `personas[].id` OR a `folded_aliases` key
(which resolves to a canonical id). Exit 0 = every UC persona resolves; 1 = at least one does not
(the message names the value and, if it is a known alias, the canonical form to use instead).
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(ROOT, "use-cases", "PERSONAS.yaml")


def main():
    spec = yaml.safe_load(open(VOCAB, encoding="utf-8"))
    canonical = {p["id"] for p in spec["personas"]}
    aliases = spec.get("folded_aliases") or {}
    resolvable = canonical | set(aliases)
    fails, n = [], 0
    for path in sorted(glob.glob(os.path.join(ROOT, "use-cases", "**", "*.yaml"), recursive=True)):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        persona = (((doc.get("scenario") or {}).get("actor")) or {}).get("persona")
        if persona is None:
            continue  # not a use-case file (README, vocabulary, taxonomy)
        n += 1
        rel = os.path.relpath(path, ROOT)
        if str(persona) not in resolvable:
            fails.append(f"{rel}: persona={persona!r} is off-vocabulary — add it to "
                         f"{os.path.basename(VOCAB)} (as a persona or a folded alias) first")
    for f in fails:
        print("FAIL [PER-001] " + f)
    print(f"{n} use case(s) checked, {len(fails)} off-vocabulary persona(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
