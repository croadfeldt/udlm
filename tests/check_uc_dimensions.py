#!/usr/bin/env python3
"""UC dimension-vocabulary gate — every use case's scenario.dimensions.* value must be in the
declared vocabulary (use-cases/DIMENSION-VOCABULARY.yaml).

Why: the dimension fields were free strings enforced nowhere in-repo, and the DAV engine's
private vocabulary silently quarantined off-list values — ~86% of the corpus, undetected until
the 2026-07-28 sweep (F1). This gate makes the vocabulary a closed, single-sourced contract so
drift is caught at authoring, not lost at analysis time. Wire into CI + signoff.

Exit 0 = every UC's dimensions are in-vocabulary; 1 = at least one off-vocabulary value (the
message names the value, the dimension, and — if it is a known folded alias — the canonical
form to use instead).
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VOCAB = os.path.join(ROOT, "use-cases", "DIMENSION-VOCABULARY.yaml")


def main():
    spec = yaml.safe_load(open(VOCAB, encoding="utf-8"))
    allowed = {k: set(v) for k, v in spec["dimensions"].items()}
    aliases = spec.get("folded_aliases") or {}
    fails, n = [], 0
    for path in sorted(glob.glob(os.path.join(ROOT, "use-cases", "*", "*.yaml"))):
        base = os.path.basename(path)
        if not base[0].isdigit():
            continue  # skip README / vocab / non-case files
        n += 1
        rel = os.path.relpath(path, ROOT)
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        dims = ((doc.get("scenario") or {}).get("dimensions")) or {}
        for dim, val in dims.items():
            if dim not in allowed:
                fails.append(f"{rel}: unknown dimension {dim!r} — not in {os.path.basename(VOCAB)}")
                continue
            if str(val) not in allowed[dim]:
                hint = aliases.get(dim, {}).get(str(val))
                tip = f" — use {hint!r} (folded alias)" if hint else \
                      f" — add it to {os.path.basename(VOCAB)} first if it is a real new value"
                fails.append(f"{rel}: {dim}={val!r} is off-vocabulary{tip}")
    for f in fails:
        print("FAIL [DIM-001] " + f)
    print(f"{n} use case(s) checked, {len(fails)} off-vocabulary value(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
