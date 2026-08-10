#!/usr/bin/env python3
"""Promotion is a ROUND TRIP, or it is a rumour (ING-017/018/019).

A composition record is a composition nobody is offering — ingested from a diagram, converted, or
authored by a consumer for themselves. It becomes an offer by being PROMOTED into a class through a
governed process. This gate checks the three things that make that promotion real rather than
asserted:

  ING-017  a CANONICAL record names the class it became (`promoted_to`), and that class names the
           record it came from (`promoted_from`). BOTH halves. A one-way pointer is how a promotion
           that never happened still looks like one from whichever side you read first.
  ING-018  the record SURVIVES promotion — a class whose `promoted_from` resolves to nothing has
           either consumed its source or is citing a record that was deleted, and both make a
           re-ingest of the same diagram look like a brand-new composition.
  ING-019  a composition synthesized from an external artifact is `discovered-derived`, never
           `declared`. An importer is not a human, however clean the mapping was.

**Not checked here, and why.** ING-016 ("never offered") needs no gate: the schema sets
`additionalProperties: false` and declares no `supports`, so an offered composition cannot be
expressed. Structural refusal beats a check that has to be remembered. ING-020 (which values are
choices) is a judgement — the whole reason promotion is governed rather than computed — and a gate
claiming to verify it would be asserting that a human decision has a right answer.

**Bindable (#434).** `evaluate(record, index)` judges ONE record against the resolved estate, so a
must-reject case is handed to it directly. The tree walk is a thin loop over it.

Exit 0 = every promotion is a round trip; 1 = at least one is not.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_ROOTS = [os.path.join(ROOT, "registry", "examples"),
              os.path.join(ROOT, "registry", "instances"),
              os.path.join(ROOT, "registry", "classes")]

# A URF reference ends in the identity it names; we match on the trailing segment(s) rather than
# parsing the whole grammar, which check_urf.py already owns. One gate, one job.
def _tail(ref):
    return (ref or "").rstrip("/").split("/")[-1]


def load_index():
    """Two indexes: compositions by uuid AND by handle-tail, classes by resource_type. must-reject
    cases are excluded — they are inputs a case hands in deliberately, never part of the estate."""
    comps, classes = {}, {}
    for root in SCAN_ROOTS:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            if "must-reject" in p.split(os.sep):
                continue
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            for d in docs:
                if not isinstance(d, dict):
                    continue
                rel = os.path.relpath(p, ROOT)
                if d.get("record_type") == "composition":
                    d.setdefault("_path", rel)
                    comps[d.get("uuid")] = d
                    if d.get("handle"):
                        comps.setdefault(_tail(d["handle"]), d)
                elif d.get("record_type") == "class":
                    d.setdefault("_path", rel)
                    classes[d.get("resource_type")] = d
    return {"compositions": comps, "classes": classes}


def evaluate(record, index):
    """Judge ONE record — a composition or a class. Returns error strings; empty means it holds."""
    errs = []
    comps, classes = index.get("compositions", {}), index.get("classes", {})

    if record.get("record_type") == "composition":
        who = record.get("handle") or (record.get("uuid") or "?")[:8]
        state, target = record.get("state"), record.get("promoted_to")

        # ING-017 — the far half. (The near half, promoted_to present iff CANONICAL, is a schema
        # conditional; re-checking it here would be a second home for one rule.)
        if state == "CANONICAL" and target:
            cls = classes.get(_tail(target))
            if cls is None:
                errs.append(f"ING-017 {who}: CANONICAL and promoted_to names {_tail(target)!r}, "
                            f"which resolves to no class — a promotion into something that does "
                            f"not exist is an outcome nobody can verify")
            else:
                back = cls.get("promoted_from")
                if not back:
                    errs.append(f"ING-017 {who}: promoted into {cls.get('resource_type')}, which "
                                f"does not name a promoted_from — the round trip is one-way, so "
                                f"from the class side this promotion never happened")
                elif _tail(back) not in (record.get("uuid"), _tail(record.get("handle") or "")):
                    errs.append(f"ING-017 {who}: promoted into {cls.get('resource_type')}, which "
                                f"names a DIFFERENT source ({_tail(back)}) — two records each "
                                f"believe they became the same class")

        # ING-019 — an importer is not a human.
        prov = record.get("provenance") or {}
        if prov.get("arrival") in ("ingested_likec4", "converted_calm") and prov.get("origin") != "discovered-derived":
            errs.append(f"ING-019 {who}: arrival {prov.get('arrival')!r} with origin "
                        f"{prov.get('origin')!r} — content synthesized from an external artifact is "
                        f"discovered-derived; presenting it as declared claims a human wrote it")

    elif record.get("record_type") == "class":
        src = record.get("promoted_from")
        if src and _tail(src) not in comps:
            errs.append(f"ING-018 {record.get('resource_type')}: promoted_from names "
                        f"{_tail(src)!r}, which resolves to no composition record — the source must "
                        f"survive promotion, or a re-ingest of the same artifact looks brand new")
    return errs


def main():
    index = load_index()
    pool = list(index["compositions"].values()) + list(index["classes"].values())
    seen, fails, checked = set(), [], 0
    for rec in pool:
        key = id(rec)
        if key in seen:
            continue
        seen.add(key)
        if rec.get("record_type") == "class" and not rec.get("promoted_from"):
            continue                       # the ordinary case: authored deliberately as an offer
        checked += 1
        fails += evaluate(rec, index)

    # self-test: each arm must fire on a planted violation, or this gate only proves the walk ran.
    probe = {"compositions": {"c1": {"uuid": "c1", "record_type": "composition"}},
             "classes": {"T.A": {"resource_type": "T.A", "record_type": "class"}}}
    arms = {
        "ING-017": evaluate({"record_type": "composition", "uuid": "c1", "handle": "h",
                             "state": "CANONICAL", "promoted_to": "udlm://class/T.A"}, probe),
        "ING-018": evaluate({"record_type": "class", "resource_type": "T.B",
                             "promoted_from": "udlm://composition/ghost"}, probe),
        "ING-019": evaluate({"record_type": "composition", "uuid": "c2", "handle": "h2",
                             "state": "PROPOSED",
                             "provenance": {"arrival": "ingested_likec4", "origin": "declared"}}, probe),
    }
    for rule, got in arms.items():
        if not any(rule in e for e in got):
            print(f"FAIL [PROM-SELF] {rule} did not fire on a planted violation")
            fails.append("self-test")

    print(f"composition-promotion: {checked} promotion-bearing record(s) judged against "
          f"ING-017/018/019 ({len({id(v) for v in index['compositions'].values()})} "
          f"composition(s) in the estate)")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} promotion defect(s)")
        return 1
    print("OK — every promotion is a round trip")
    return 0


if __name__ == "__main__":
    sys.exit(main())
