#!/usr/bin/env python3
"""The UDLM conformance suite, record level (suite 1.1.0): run it against the records an implementation writes.

CONFORMANCE.md §8 requires an implementation to run the suite to self-certify and to record its version
(`conformance_test_suite_version`, §4.1). The 1.0 bar (ruling 2, UDLM-1.0-LOCKDOWN.md) is record level: the
records an implementation produces must satisfy every rule a record can be judged by, alone or with the
records beside it. The wire-level checklist of §6 is the 1.x half.

Give it a directory of records (YAML, multi-document allowed, or JSON) and it applies, to every state record
it finds (intent, requested, realized, discovered):

  schema      a stream head validates against registry/state-record.schema.json; a superseded record is
              history and is judged by its chain only (SCHEMA-002). The schema carries CLS-010, DEP-015,
              RHY-007, WIR-001/002/003/007 and the other record-shape rules.
  INT-001/002 a declared integrity head recomputes from the record's bytes and its claimed `previous`, and a
              superseding record's `previous` is the head of the record it supersedes.
  TRN-001/002/003  the transition from a referenced record is attributed, the reference carries its head,
              and it resolves to a record of the right kind and entity.
  FUL-001/002/003  a fulfillment condition is a governed one, a blocked one names its blocker, and the chain
              of blockers can be walked to a root.
  DSP-002/003/004  a requested record carries a dispatch receipt, and what it admits is the class's
              execution elements or explicitly granted.
  REL-002     a head carries, for every relationship its class marks structural, as many edges as the class's
              cardinality allows. Templates that share a name are one relation and are counted together. An
              edge with no relation name (a discovered record's) counts by its target's class, read from the
              records beside it; where a target is not among them the count cannot be judged, and that is a
              warning (REL-002.unjudged), not a failure.
  payload     a head's fields (and a realized or discovered head's outputs) validate at depth against the
              class at the version the record pins; a version this registry does not serve is a warning
              (payload.unjudged): the payload cannot be judged, not judged wrong.

The schema and payload checks are named for what they check, not given rule IDs: they bind rules defined
elsewhere (the schema carries CLS-010, DEP-015, RHY-007 and the WIR rules; a class carries its elements).

Exit 0 = no failures. `--report FILE` writes the result as JSON, for the conformance declaration.
`--self-test` runs the suite over this repository's worked records (all must pass), checks that every rule
the suite applies has at least one must-reject case, and runs every must-reject case
bound to a rule the suite applies (each must be refused for the rule it names).

Usage:
  python3 tests/conformance.py RECORD_DIR [RECORD_DIR ...] [--report FILE]
  python3 tests/conformance.py --self-test
"""
import argparse
import glob
import json
import os
import subprocess
import sys
import warnings

import jsonschema
import yaml

SUITE_VERSION = "1.1.0"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "registry")
sys.path.insert(0, os.path.join(REG, "tools"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import entity_view  # noqa: E402
import integrity_chain as IC  # noqa: E402
import check_transition_provenance as TRN  # noqa: E402
import check_fulfillment_conditions as FUL  # noqa: E402
import check_dispatch_slice as DSP  # noqa: E402

STATE_KINDS = ("intent_record", "requested_record", "realized_record", "discovered_record")
RULES = ["schema", "INT-001", "INT-002", "TRN-001", "TRN-002", "TRN-003", "FUL-001", "FUL-002", "FUL-003",
         "DSP-002", "DSP-003", "DSP-004", "REL-002", "payload.fields", "payload.outputs"]
SCHEMA_BOUND = {"CLS-010", "DEP-015", "RHY-007", "WIR-001", "WIR-002", "WIR-003", "WIR-007"}
EDGE_KINDS = ("requested_record", "realized_record", "discovered_record")   # an intent record carries no edges
UNJUDGED = {"payload.unjudged": "records pinning a class version this registry does not serve",
            "REL-002.unjudged": "records with an edge whose target is not among the records given"}


# ---------------------------------------------------------------- loading

def docs_in(path):
    try:
        with open(path, encoding="utf-8") as fh:
            if path.endswith(".json"):
                d = json.load(fh)
                return [d] if isinstance(d, dict) else []
            return [d for d in yaml.safe_load_all(fh) if isinstance(d, dict)]
    except Exception:
        return []


def load_tree(roots, skip_must_reject=True):
    """[(record, where)] for every state record under the roots."""
    out = []
    for root in roots:
        files = [root] if os.path.isfile(root) else sorted(
            glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)
            + glob.glob(os.path.join(root, "**", "*.json"), recursive=True))
        for p in files:
            if skip_must_reject and os.sep + "must-reject" + os.sep in p:
                continue
            for i, d in enumerate(docs_in(p)):
                if d.get("record_type") in STATE_KINDS:
                    out.append((d, f"{os.path.relpath(p)}#{i}" if i else os.path.relpath(p)))
    return out


# ---------------------------------------------------------------- the registry the records are judged against

def record_validator():
    store = jsonschema.validators.Draft202012Validator.META_SCHEMA and __import__("referencing").Registry()
    from referencing import Resource
    docs = {}
    for name in ("state-record.schema.json", "common-elements.schema.json", "policy.schema.json",
                 "entity-view.schema.json", "data-reference.schema.json"):
        p = os.path.join(REG, name)
        if not os.path.exists(p):
            continue
        d = json.load(open(p, encoding="utf-8"))
        docs[name] = d
        res = Resource.from_contents(d)
        store = store.with_resource(d["$id"], res).with_resource(name, res)
    return jsonschema.Draft202012Validator(docs["state-record.schema.json"], registry=store)


def class_validators():
    """resource_type -> (version, fields validator, outputs validator), from the served class specs."""
    import pathlib
    out = {}
    for p in sorted(glob.glob(os.path.join(REG, "generated", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        if not d.get("resource_type"):
            continue
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            from jsonschema import RefResolver   # the served specs' relative $refs resolve from their file
            res = RefResolver(base_uri=pathlib.Path(p).resolve().as_uri(), referrer=d)
            fv = jsonschema.Draft202012Validator(d.get("spec") or {"type": "object"}, resolver=res)
            ov = jsonschema.Draft202012Validator({"type": "object", "additionalProperties": False,
                                                  "properties": d.get("outputs") or {}}, resolver=res)
        out[d["resource_type"]] = (d.get("version"), fv, ov)
    return out


def class_relations():
    """resource_type -> (version, [relation]), from the served class specs. Templates that share a `name` are
    one relation with alternative targets (REL-002); a template with no name is a relation by itself."""
    out = {}
    for p in sorted(glob.glob(os.path.join(REG, "generated", "*.json"))):
        d = json.load(open(p, encoding="utf-8"))
        if not d.get("resource_type"):
            continue
        rels = {}
        for t in d.get("relationships") or []:
            key = t.get("name") or (t.get("edge_type"), t.get("target"), t.get("target_field"))
            rel = rels.setdefault(key, {"name": t.get("name"), "edge_type": t.get("edge_type"), "targets": [],
                                        "cardinality": t.get("cardinality", "0..n"),
                                        "structural": t.get("enforcement") == "structural"})
            rel["targets"].append(t.get("target"))
        out[d["resource_type"]] = (d.get("version"), list(rels.values()))
    return out


def _is_a(cls, target):
    return cls == target or cls.startswith(f"{target}.")


def relation_findings(record, relations, class_of):
    """REL-002 on one record: ([what is wrong], [what could not be judged]). `class_of(edge)` is the class of
    the edge's target, or None where the target is not among the records given.

    An edge that names its `relation` counts toward that relation. An edge that names none counts toward
    the relation that declares its target's class. Where the target's class is not known, or two relations
    declare it, the edge may belong to any relation of its edge type and is counted for none of them."""
    fails, unjudged = [], []
    edges = [e for e in record.get("dependencies") or [] if isinstance(e, dict)]
    for rel in relations:
        if not rel["structural"]:
            continue
        low, _, high = str(rel["cardinality"]).partition("..")
        low, high = int(low), (None if high == "n" else int(high))
        known = unknown = 0
        for e in edges:
            if e.get("relation"):
                known += e["relation"] == rel["name"]
                continue
            if e.get("edge_type") != rel["edge_type"]:
                continue
            cls = class_of(e)
            declaring = [] if cls is None else [r for r in relations if r["edge_type"] == e["edge_type"]
                                                and any(_is_a(cls, t) for t in r["targets"])]
            if cls is None or (len(declaring) > 1 and any(r is rel for r in declaring)):
                unknown += 1
            elif declaring and declaring[0] is rel:
                known += 1
        what = (f"relation `{rel['name']}`" if rel["name"] else f"the `{rel['edge_type']}` relation") + \
            f" to {' or '.join(rel['targets'])} is structural with cardinality {rel['cardinality']}"
        if high is not None and known > high:
            fails.append(f"{what}; this record carries {known} such edges")
        elif known + unknown < low:
            fails.append(f"{what}; this record carries {'none' if not known else known}")
        elif unknown and (known < low or (high is not None and known + unknown > high)):
            unjudged.append(f"{what}; {known} edge(s) counted and {unknown} more of that edge type name a target "
                            f"that is not among these records")
    return fails, unjudged


# ---------------------------------------------------------------- the suite

def run(records, rv=None, cv=None, cr=None):
    """{"failures": [(rule, where, detail)], "warnings": [...], "checked": {rule: n}}."""
    rv = rv or record_validator()
    cv = cv if cv is not None else class_validators()
    cr = cr if cr is not None else class_relations()
    class_by_entity, classes_by_key = {}, {}
    for d, _ in records:
        if d.get("entity_uuid") and d.get("resource_type"):
            class_by_entity.setdefault(d["entity_uuid"], d["resource_type"])
        for c in d.get("correlation_ids") or []:
            if isinstance(c, dict) and d.get("resource_type"):
                classes_by_key.setdefault((c.get("scheme"), c.get("value")), set()).add(d["resource_type"])

    def class_of(edge):
        """The class of an edge's target: by its identity, else by a natural key exactly one class answers to."""
        if edge.get("target_uuid") in class_by_entity:
            return class_by_entity[edge["target_uuid"]]
        key = edge.get("target_key") or {}
        named = classes_by_key.get((key.get("scheme"), key.get("value")), ())
        return next(iter(named)) if len(named) == 1 else None
    fails, warns, checked = [], [], {r: 0 for r in RULES}
    by_uuid = {}
    for d, _ in records:
        by_uuid.setdefault(d.get("record_uuid"), d)
    superseded = {u for d, _ in records for u in (d.get("supersedes") or [])}
    views = entity_view.build_views([d for d, _ in records])
    ful_index = {}
    for u, v in views.items():
        ful_index[u] = v
        if v.get("handle"):
            ful_index.setdefault(FUL._tail(v["handle"]), v)
    dsp_index = DSP.load_index()

    for d, where in records:
        head = d.get("record_uuid") not in superseded
        # schema — heads only; a superseded record is history, judged by its chain
        if head:
            checked["schema"] += 1
            for e in rv.iter_errors(d):
                loc = "/".join(map(str, e.path)) or "<root>"
                fails.append(("schema", where, f"{loc}: {e.message[:200]}"))
        # INT-001/002
        if isinstance(d.get("integrity"), dict):
            checked["INT-001"] += 1
            ok, detail = IC.verify(d)
            if not ok:
                fails.append(("INT-001", where, detail))
            for prior in d.get("supersedes") or []:
                checked["INT-002"] += 1
                p = by_uuid.get(prior)
                want = ((p or {}).get("integrity") or {}).get("head")
                if p is not None and want and d["integrity"].get("previous") != want:
                    fails.append(("INT-002", where, f"integrity.previous {d['integrity'].get('previous')} is not the head "
                                                    f"of the record it supersedes ({want})"))
        # TRN-001/002/003
        if d.get("record_type") in TRN.REFS:
            for r in ("TRN-001", "TRN-002", "TRN-003"):
                checked[r] += 1
            for f in TRN.judge(d, by_uuid, where):
                fails.append((f.split()[0], where, f.split(" ", 2)[-1]))
        if head:
            # FUL-001/002/003
            for r in ("FUL-001", "FUL-002", "FUL-003"):
                checked[r] += 1
            for f in FUL.evaluate(d, ful_index):
                fails.append((f.split()[0], where, f.split(" ", 2)[-1]))
            # DSP-002/003/004
            if d.get("record_type") == "requested_record":
                for r in ("DSP-002", "DSP-003", "DSP-004"):
                    checked[r] += 1
                for f in DSP.judge(d, dsp_index, where):
                    fails.append((f.split()[0], where, f.split(" ", 2)[-1]))
            rt, pinned = d.get("resource_type"), str(d.get("type_version"))
            # REL-002 — the structural relationships of the class at the version the record pins. A version
            # this registry does not serve is reported once, below, as payload.unjudged.
            if d.get("record_type") in EDGE_KINDS and rt in cr and str(cr[rt][0]) == pinned \
                    and any(r["structural"] for r in cr[rt][1]):
                checked["REL-002"] += 1
                wrong, unknown = relation_findings(d, cr[rt][1], class_of)
                fails += [("REL-002", where, m) for m in wrong]
                warns += [("REL-002.unjudged", where, m) for m in unknown]
            # payload — at the class version the record pins
            if rt in cv and str(cv[rt][0]) == pinned:
                _, fv, ov = cv[rt]
                if isinstance(d.get("fields"), dict):
                    checked["payload.fields"] += 1
                    for e in fv.iter_errors(d["fields"]):
                        fails.append(("payload.fields", where, f"fields/{'/'.join(map(str, e.path))}: {e.message[:200]}"))
                if d.get("record_type") in ("realized_record", "discovered_record") and isinstance(d.get("outputs"), dict):
                    checked["payload.outputs"] += 1
                    for e in ov.iter_errors(d["outputs"]):
                        fails.append(("payload.outputs", where, f"outputs/{'/'.join(map(str, e.path))}: {e.message[:200]}"))
            elif rt:
                warns.append(("payload.unjudged", where, f"{rt} {pinned}: this registry serves "
                                                f"{cv[rt][0] if rt in cv else 'no such class'}; payload not judged"))
    return {"failures": fails, "warnings": warns, "checked": checked}


def udlm_ref():
    try:
        return subprocess.run(["git", "-C", ROOT, "rev-parse", "HEAD"], capture_output=True, text=True,
                              check=True).stdout.strip()
    except Exception:
        return "unknown"


# ---------------------------------------------------------------- self-test

def _relation_self_test():
    """REL-002 counts what it should: the cases a must-reject file cannot show, because they pass."""
    one = {"name": "describes", "edge_type": "references", "targets": ["Image", "Machine"], "cardinality": "1..1",
           "structural": True}
    lists = {"name": "contains", "edge_type": "references", "targets": ["Package"], "cardinality": "0..n",
             "structural": False}
    many = {"name": None, "edge_type": "references", "targets": ["Key"], "cardinality": "1..n", "structural": True}
    classes = {"i": "Image", "vm": "Machine.VM", "p": "Package", "k": "Key"}

    def judge(relations, *edges):
        fails, unjudged = relation_findings({"dependencies": [dict(e, edge_type=e.get("edge_type", "references"))
                                                              for e in edges]},
                                            relations, lambda e: classes.get(e.get("target_uuid")))
        return "fail" if fails else "unjudged" if unjudged else "pass"

    cases = [
        ("one subject among packages", judge([one, lists], {"target_uuid": "i"}, {"target_uuid": "p"}), "pass"),
        ("a subclass of a declared target is that target", judge([one, lists], {"target_uuid": "vm"}), "pass"),
        ("an edge that names the relation needs no lookup", judge([one, lists], {"relation": "describes"}), "pass"),
        ("no subject", judge([one, lists], {"target_uuid": "p"}), "fail"),
        ("two subjects", judge([one, lists], {"target_uuid": "i"}, {"target_uuid": "vm"}), "fail"),
        ("two subjects, both named", judge([one, lists], {"relation": "describes"}, {"relation": "describes"}), "fail"),
        ("an edge of another edge type is not counted", judge([one, lists], {"target_uuid": "i", "edge_type": "depends_on"}), "fail"),
        ("a target that is not among the records", judge([one, lists], {"target_uuid": "elsewhere"}), "unjudged"),
        ("one subject and a target that is not among the records",
         judge([one, lists], {"target_uuid": "i"}, {"target_uuid": "elsewhere"}), "unjudged"),
        ("an unnamed relation, one or more", judge([many], {"target_uuid": "k"}, {"target_uuid": "k"}), "pass"),
        ("an unnamed relation, none", judge([many]), "fail"),
        ("an example relation is never enforced", judge([dict(one, structural=False)]), "pass"),
    ]
    return [f"REL-002 self-test, {name}: expected {want}, got {got}" for name, got, want in cases if got != want]


def self_test():
    """The worked records must pass, and every must-reject case bound to a rule this suite applies must be
    refused for that rule. A suite that cannot fail proves only that the files parsed."""
    rv, cv, cr = record_validator(), class_validators(), class_relations()
    ex = load_tree([os.path.join(REG, "examples")])
    res = run(ex, rv, cv, cr)
    problems = [f"worked record refused: {r} {w}: {d}" for r, w, d in res["failures"]]
    problems += _relation_self_test()
    n_cases, covered = 0, set()
    for p in sorted(glob.glob(os.path.join(REG, "examples", "must-reject", "*.yaml"))):
        case = yaml.safe_load(open(p, encoding="utf-8")) or {}
        mr, rec = case.get("must_reject") or {}, case.get("record")
        if not isinstance(rec, dict) or rec.get("record_type") not in STATE_KINDS:
            continue
        rule = mr.get("rule")
        want = "schema" if (mr.get("gate") == "schema" or rule in SCHEMA_BOUND) else rule
        if want not in RULES:
            continue
        n_cases += 1
        got = {r for r, w, _d in run(ex + [(rec, os.path.basename(p))], rv, cv, cr)["failures"]
               if w == os.path.basename(p)}
        if want not in got:
            hint = ""
            if want.startswith("payload."):
                rt, pinned = rec.get("resource_type"), str(rec.get("type_version"))
                if rt in cv and str(cv[rt][0]) != pinned:
                    hint = (f" — it pins {rt} {pinned} but this registry serves {cv[rt][0]}, so the payload was not"
                            f" judged; repin the case to {cv[rt][0]}")
            problems.append(f"must-reject {os.path.basename(p)}: expected {want} ({rule}), suite raised "
                            f"{sorted(got) or 'nothing'}{hint}")
        else:
            covered.add(want)
    # Coverage (WP7d, #434): every rule this suite applies has at least one case it must refuse. A rule
    # with no case could stop refusing and nothing would notice, which is the failure the corpus exists for.
    uncovered = [r for r in RULES if r not in covered]
    problems += [f"rule {r} has no must-reject case: add one to registry/examples/must-reject/" for r in uncovered]
    for m in problems:
        print(f"  FAIL {m}")
    if problems:
        return 1
    print(f"self-test OK: {len(ex)} worked records pass; {n_cases} must-reject cases refused for their rule; "
          f"all {len(RULES)} rules covered")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("roots", nargs="*")
    ap.add_argument("--report")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        return self_test()
    if not args.roots:
        ap.error("give at least one directory of records, or --self-test")
    records = load_tree(args.roots)
    res = run(records)
    heads = len(records) - len({u for d, _ in records for u in (d.get("supersedes") or [])})
    print(f"UDLM conformance suite {SUITE_VERSION} (udlm {udlm_ref()[:12]}): {len(records)} state records, {heads} heads")
    by_rule = {}
    for r, w, dtl in res["failures"]:
        by_rule.setdefault(r, []).append((w, dtl))
    for r in RULES:
        n = len(by_rule.get(r, []))
        print(f"  {r:16} {'FAIL' if n else 'pass'}  {res['checked'][r]} checked{f', {n} failed' if n else ''}")
        for w, dtl in by_rule.get(r, [])[:10]:
            print(f"             {w}: {dtl}")
    for kind, says in UNJUDGED.items():
        n = sum(1 for r, _w, _d in res["warnings"] if r == kind)
        if n:
            print(f"  {n} warning(s): {says} ({kind})")
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            json.dump({"suite": "udlm-conformance", "suite_version": SUITE_VERSION, "udlm_ref": udlm_ref(),
                       "roots": args.roots, "records": len(records), "heads": heads, "checked": res["checked"],
                       "failures": [{"rule": r, "where": w, "detail": dtl} for r, w, dtl in res["failures"]],
                       "warnings": [{"rule": r, "where": w, "detail": dtl} for r, w, dtl in res["warnings"]]},
                      fh, indent=2)
    return 1 if res["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
