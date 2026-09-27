#!/usr/bin/env python3
"""The map from intent to realized is provenance, checked as a diff (TRN-001/002/003).

A resource is four records (four-states.md §2.7). The question an auditor asks across them — what
changed between intent and realized, and who did it — is answered by the references on the records
and the per-field provenance on each, held to one rule (audit-provenance-observability.md §2.5):

  TRN-001  every leaf that differs between a record and the record it references is attributed:
           a `provenance` entry at that path (or an ancestor / descendant path) on the referencing
           record, whose `previous_value`, when present, equals the referenced record's value. A
           realized record additionally attributes every leaf of `outputs` as `outputs.<path>`.
  TRN-002  a reference to a sealed record carries its head (`intent_ref_head` / `requested_ref_head`
           equal to the referenced record's `integrity.head`); absent when the referenced record is
           unsealed.
  TRN-003  a reference resolves: to a record of the right kind, with the same entity_uuid, present
           in the shipped record sets.

Leaf paths are dot paths; an array of objects is indexed (`networks[0].network_ref`); an array of
scalars is one leaf. Scans registry/examples/** and registry/instances/** (must-reject fixtures
skipped; their nested `record` is judged by its own gate). Known debt in shipped examples lives in
tests/transition_provenance_baseline.txt, which only shrinks: a baselined line that stops failing
is reported stale until removed, and a new failure is never added there.

Self-tests a synthetic pair (an unattributed change, a wrong previous_value, a missing head, a
reference to the wrong kind) so a gate that cannot fail proves nothing.
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = [os.path.join(ROOT, "registry", "examples"), os.path.join(ROOT, "registry", "instances")]
BASELINE = os.path.join(ROOT, "tests", "transition_provenance_baseline.txt")
REFS = {"requested_record": ("intent_ref", "intent_ref_head", "intent_record"),
        "realized_record": ("requested_ref", "requested_ref_head", "requested_record")}


def leaves(value, prefix=""):
    """dot-path -> leaf value. Objects descend with '.', arrays of objects with '[i]'; anything
    else (scalars, arrays of scalars, empty containers) is a leaf."""
    out = {}
    if isinstance(value, dict) and value:
        for k, v in value.items():
            out.update(leaves(v, f"{prefix}.{k}" if prefix else str(k)))
    elif isinstance(value, list) and value and all(isinstance(x, dict) for x in value):
        for i, v in enumerate(value):
            out.update(leaves(v, f"{prefix}[{i}]"))
    else:
        out[prefix] = value
    return out


def norm(v):
    return json.loads(json.dumps(v, sort_keys=True))


def related(prov_path, change_path):
    """A provenance entry at P attributes a change at C when P == C or one is inside the other."""
    if prov_path == change_path:
        return True
    return (change_path.startswith(prov_path + ".") or change_path.startswith(prov_path + "[")
            or prov_path.startswith(change_path + ".") or prov_path.startswith(change_path + "["))


def judge(rec, by_uuid, where):
    """TRN findings for one record, given the records it may reference."""
    fails = []
    kind = rec.get("record_type")
    if kind not in REFS:
        return fails
    ref_key, head_key, want_kind = REFS[kind]
    ref = rec.get(ref_key)
    if not ref:
        return fails  # the schema requires the reference; that gate speaks first
    src = by_uuid.get(ref)
    if src is None:
        return [f"TRN-003 {where}: {ref_key} {ref} resolves to no shipped record"]
    if src.get("record_type") != want_kind:
        fails.append(f"TRN-003 {where}: {ref_key} {ref} is a {src.get('record_type')}, not a {want_kind}")
    if src.get("entity_uuid") != rec.get("entity_uuid"):
        fails.append(f"TRN-003 {where}: {ref_key} {ref} belongs to entity {src.get('entity_uuid')}, not {rec.get('entity_uuid')}")

    src_head = (src.get("integrity") or {}).get("head")
    have_head = rec.get(head_key)
    if src_head and have_head != src_head:
        fails.append(f"TRN-002 {where}: {head_key} {'missing' if not have_head else have_head} — referenced record is sealed with head {src_head}")
    if not src_head and have_head:
        fails.append(f"TRN-002 {where}: {head_key} present but the referenced record is unsealed")

    prov = rec.get("provenance") or {}
    before, after = leaves(src.get("fields") or {}), leaves(rec.get("fields") or {})
    changed = sorted(p for p in set(before) | set(after)
                     if p not in before or p not in after or norm(before[p]) != norm(after[p]))
    for path in changed:
        entries = [(pp, e) for pp, es in prov.items() if related(pp, path) for e in (es or [])]
        if not entries:
            fails.append(f"TRN-001 {where}: `{path}` differs from the referenced {want_kind} with no provenance entry")
            continue
        if path in before:
            claimed = [e.get("previous_value") for pp, e in entries if pp == path and "previous_value" in e]
            if claimed and not any(norm(c) == norm(before[path]) for c in claimed):
                fails.append(f"TRN-001 {where}: `{path}` previous_value {claimed[0]!r} != referenced value {before[path]!r}")
    if kind == "realized_record":
        for path, value in sorted(leaves(rec.get("outputs") or {}, "outputs").items()):
            if value in ({}, []):
                continue  # an empty container publishes nothing to attribute
            if not any(related(pp, path) for pp in prov):
                fails.append(f"TRN-001 {where}: output `{path}` has no provenance entry")
    return fails


def _docs(path):
    try:
        if path.endswith(".json"):
            d = json.load(open(path, encoding="utf-8"))
            return [d] if isinstance(d, dict) else []
        return [d for d in yaml.safe_load_all(open(path, encoding="utf-8")) if isinstance(d, dict)]
    except Exception:
        return []


def load():
    """(record, where) for every state record shipped, and the uuid index over them."""
    recs = []
    for root in SCAN:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)
                        + glob.glob(os.path.join(root, "**", "*.json"), recursive=True)):
            if os.sep + "must-reject" + os.sep in p or os.sep + "classes" + os.sep in p:
                continue
            rel = os.path.relpath(p, ROOT)
            for i, d in enumerate(_docs(p)):
                if d.get("record_type") in ("intent_record", "requested_record", "realized_record", "discovered_record"):
                    recs.append((d, f"{rel}#{i}"))
    by_uuid = {}
    for d, _ in recs:
        by_uuid.setdefault(d.get("record_uuid"), d)
    return recs, by_uuid


def baseline():
    if not os.path.exists(BASELINE):
        return set()
    return {ln.strip() for ln in open(BASELINE, encoding="utf-8") if ln.strip() and not ln.startswith("#")}


def key(finding):
    """The stable part of a finding for the baseline: code, location, subject (not the values)."""
    head = finding.split(":", 1)[0]  # "TRN-001 path#i"
    subject = finding.split("`")[1] if "`" in finding else finding.split(":", 1)[1].strip().split(" ")[0]
    return f"{head} {subject}"


def self_test():
    intent = {"record_type": "intent_record", "entity_uuid": "e", "record_uuid": "i1",
              "fields": {"cpu": {"count": 4}, "memory": {"size": "16Gi"}, "networks": [{"name": "eth0"}]},
              "integrity": {"algorithm": "sha256-jcs", "head": "sha256:" + "a" * 64, "previous": None}}
    good = {"record_type": "requested_record", "entity_uuid": "e", "record_uuid": "r1", "intent_ref": "i1",
            "intent_ref_head": intent["integrity"]["head"],
            "fields": {"cpu": {"count": 4, "sockets": 1}, "memory": {"size": "32Gi"}, "networks": [{"name": "eth0", "vlan": "v20"}]},
            "provenance": {"cpu.sockets": [{"source": {"kind": "policy", "id": "p"}, "timestamp": "t"}],
                           "memory.size": [{"source": {"kind": "policy", "id": "p"}, "timestamp": "t", "previous_value": "16Gi"}],
                           "networks[0].vlan": [{"source": {"kind": "layer", "id": "l"}, "timestamp": "t"}]}}
    by = {"i1": intent}
    assert judge(good, by, "good") == [], judge(good, by, "good")
    bad = json.loads(json.dumps(good)); bad["provenance"].pop("cpu.sockets")
    assert any(f.startswith("TRN-001") and "cpu.sockets" in f for f in judge(bad, by, "bad")), "unattributed change must fail"
    bad = json.loads(json.dumps(good)); bad["provenance"]["memory.size"][0]["previous_value"] = "8Gi"
    assert any("previous_value" in f for f in judge(bad, by, "bad")), "wrong previous_value must fail"
    bad = json.loads(json.dumps(good)); bad.pop("intent_ref_head")
    assert any(f.startswith("TRN-002") for f in judge(bad, by, "bad")), "missing head must fail"
    bad = json.loads(json.dumps(good)); bad["entity_uuid"] = "other"
    assert any(f.startswith("TRN-003") for f in judge(bad, by, "bad")), "wrong entity must fail"
    realized = {"record_type": "realized_record", "entity_uuid": "e", "record_uuid": "z1", "requested_ref": "r1",
                "requested_ref_head": None, "fields": good["fields"], "outputs": {"ip": "192.0.2.1"}, "provenance": {}}
    by2 = {"r1": good}
    assert any("outputs.ip" in f for f in judge(realized, by2, "realized")), "unattributed output must fail"
    realized["provenance"] = {"outputs.ip": [{"source": {"kind": "provider", "id": "x"}, "timestamp": "t"}]}
    assert judge(realized, by2, "realized") == [], judge(realized, by2, "realized")


def main():
    self_test()
    recs, by_uuid = load()
    if not recs:
        print("FAILED — no state records found; the gate would pass vacuously")
        return 1
    findings = []
    for d, where in recs:
        findings += judge(d, by_uuid, where)
    known = baseline()
    keys = {key(f): f for f in findings}
    new = [f for k, f in keys.items() if k not in known]
    stale = sorted(k for k in known if k not in keys)
    for k, f in sorted(keys.items()):
        print(("WARN(baseline) " if k in known else "FAIL ") + f)
    for k in stale:
        print(f"STALE-BASELINE {k} — no longer fails; remove it from tests/transition_provenance_baseline.txt")
    print(f"\n{len(recs)} state records, {len(findings)} finding(s): {len(findings) - len(new)} baselined, "
          f"{len(new)} new, {len(stale)} stale")
    return 1 if new or stale else 0


if __name__ == "__main__":
    sys.exit(main())
