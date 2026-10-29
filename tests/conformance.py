#!/usr/bin/env python3
"""The UDLM conformance suite, record level (suite 1.0.0): run it against the records an implementation writes.

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
  payload     a head's fields (and a realized or discovered head's outputs) validate at depth against the
              class at the version the record pins; a version this registry does not serve is a warning
              (payload.unjudged): the payload cannot be judged, not judged wrong.

The schema and payload checks are named for what they check, not given rule IDs: they bind rules defined
elsewhere (the schema carries CLS-010, DEP-015, RHY-007 and the WIR rules; a class carries its elements).

Exit 0 = no failures. `--report FILE` writes the result as JSON, for the conformance declaration.
`--self-test` runs the suite over this repository's worked records (all must pass) and every must-reject case
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

SUITE_VERSION = "1.0.0"
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
         "DSP-002", "DSP-003", "DSP-004", "payload.fields", "payload.outputs"]
SCHEMA_BOUND = {"CLS-010", "DEP-015", "RHY-007", "WIR-001", "WIR-002", "WIR-003", "WIR-007"}


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


# ---------------------------------------------------------------- the suite

def run(records, rv=None, cv=None):
    """{"failures": [(rule, where, detail)], "warnings": [...], "checked": {rule: n}}."""
    rv = rv or record_validator()
    cv = cv if cv is not None else class_validators()
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
            # payload — at the class version the record pins
            rt, pinned = d.get("resource_type"), str(d.get("type_version"))
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

def self_test():
    """The worked records must pass, and every must-reject case bound to a rule this suite applies must be
    refused for that rule. A suite that cannot fail proves only that the files parsed."""
    rv, cv = record_validator(), class_validators()
    ex = load_tree([os.path.join(REG, "examples")])
    res = run(ex, rv, cv)
    problems = [f"worked record refused: {r} {w}: {d}" for r, w, d in res["failures"]]
    n_cases = 0
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
        got = {r for r, w, _d in run(ex + [(rec, os.path.basename(p))], rv, cv)["failures"] if w == os.path.basename(p)}
        if want not in got:
            problems.append(f"must-reject {os.path.basename(p)}: expected {want} ({rule}), suite raised {sorted(got) or 'nothing'}")
    for m in problems:
        print(f"  FAIL {m}")
    if problems:
        return 1
    print(f"self-test OK: {len(ex)} worked records pass; {n_cases} must-reject cases refused for their rule")
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
    if res["warnings"]:
        print(f"  {len(res['warnings'])} warning(s): records pinning a class version this registry does not serve (payload.unjudged)")
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
