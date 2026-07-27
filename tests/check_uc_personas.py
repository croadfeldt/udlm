#!/usr/bin/env python3
"""UC persona-vocabulary gate — every use case's persona references must resolve to the canonical
persona set (use-cases/PERSONAS.yaml).

Two fields are checked (same resolution: a canonical `personas[].id` OR a `folded_aliases` key):
  - PER-001  scenario.actor.persona      — the persona that drives the use case (required)
  - PER-002  scenario.perspectives[]     — the additional personas the UC must be analyzed FROM
                                           (optional; the multi-perspective lenses beyond the actor)

Why: the persona a use case is written from / evaluated from was a free string enforced nowhere,
and would otherwise let each consumer carry its own private list — the same fork DIM-001 closed for
the dimension vocabulary. This gate makes the persona set a closed, single-sourced contract.

Also prints a non-failing COVERAGE line: canonical personas that appear on NO use case (as actor or
perspective) in this repo. A persona nobody views from is a candidate for removal — the "added
effectively" signal (a persona is only real if a use case exercises it). Informational for now.

Exit 0 = every persona reference resolves; 1 = at least one does not.
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

    def canon(v):  # resolve a value to its canonical id (alias-aware), or None if unresolvable
        return v if v in canonical else aliases.get(v)

    fails, n = [], 0
    seen = set()  # canonical personas exercised somewhere (actor or perspective)
    for path in sorted(glob.glob(os.path.join(ROOT, "use-cases", "**", "*.yaml"), recursive=True)):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        scenario = doc.get("scenario") or {}
        actor = (scenario.get("actor") or {}).get("persona")
        if actor is None:
            continue  # not a use-case file (README, vocabulary, taxonomy)
        n += 1
        rel = os.path.relpath(path, ROOT)
        # PER-001 — the driving persona
        if str(actor) not in resolvable:
            fails.append(f"[PER-001] {rel}: actor.persona={actor!r} off-vocabulary — add it to "
                         f"{os.path.basename(VOCAB)} (persona or alias) first")
        else:
            seen.add(canon(str(actor)))
        # PER-002 — the additional perspectives
        for p in (scenario.get("perspectives") or []):
            if str(p) not in resolvable:
                fails.append(f"[PER-002] {rel}: perspective {p!r} off-vocabulary — add it to "
                             f"{os.path.basename(VOCAB)} (persona or alias) first")
            else:
                seen.add(canon(str(p)))
    for f in fails:
        print("FAIL " + f)
    uncovered = sorted(canonical - seen)
    print(f"{n} use case(s) checked, {len(fails)} unresolved persona reference(s)")
    if uncovered:
        print(f"COVERAGE (informational): {len(uncovered)} persona(s) on no use case here — "
              + ", ".join(uncovered))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
