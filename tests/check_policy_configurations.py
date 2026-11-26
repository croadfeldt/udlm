#!/usr/bin/env python3
"""Policy-configuration gate — the relationships between a policy, its configurations and a profile.

A policy holds logic and a policy configuration holds one deployment's values for it
(policy-contract §9, POL-011). Each schema checks its own record. Neither can check the other, and
the three rules below are all about the other record:

  POL-012  a configuration's `configures` resolves to exactly one policy, at the version it pins,
           and that policy is not retired. The schema requires the pin; only a resolver can say the
           pin lands on something.
  POL-013  a configuration's `parameters` satisfy the pinned policy's `parameter_schema`, it
           supplies no parameter the policy does not declare, and a policy that declares none
           takes none. A misspelled parameter would otherwise be carried and never read.
  POL-015  a configuration of a `proposed` policy is itself `proposed`: provisional logic runs in
           shadow mode and applies nowhere until the policy is `active`.
  POL-014  a profile turns a policy configuration on or off and holds no values for it: a
           `contains[]` entry that resolves to a policy is refused (a policy alone decides
           nothing), and so is one that resolves to a configuration and carries `settings`
           (a value would have two homes).

One more check moved here with the field it reads: schedule clauses belong on a configuration of
a `validation` or `orchestration_flow` policy (ADR-053). The type is the policy's and the clauses
are the configuration's, so it takes both records to say.

A pin is compared with the version this repository ships. A deployment that keeps older versions
resolves an older pin against those; this gate judges the worked examples, where one version of
each record exists.

`evaluate(record, index)` judges ONE record against an index of the shipped records, which is the
shape tests/check_must_reject.py binds. `--self-test` runs a refusal for every rule in memory.

Exit 0 = every configuration and profile entry holds; 1 = at least one does not.
"""
import glob
import importlib.util
import os
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN = os.path.join(ROOT, "registry", "examples", "*.yaml")
SCHEDULED_TYPES = ("validation", "orchestration_flow")

_spec = importlib.util.spec_from_file_location("urf", os.path.join(ROOT, "registry", "tools", "urf.py"))
URF = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(URF)


def _index(records):
    """handle or `uuid/<v4>` -> the policy and policy_configuration records that answer to it."""
    idx = {}
    for rec in records:
        if not isinstance(rec, dict) or rec.get("record_type") not in ("policy", "policy_configuration"):
            continue
        for key in (rec.get("handle"), f"uuid/{rec.get('uuid')}" if rec.get("uuid") else None):
            if key:
                idx.setdefault(key, []).append(rec)
    return idx


def load_records():
    out = []
    for path in sorted(glob.glob(SCAN)):
        for doc in yaml.safe_load_all(open(path, encoding="utf-8")):
            if isinstance(doc, dict):
                out.append(doc)
    return out


def load_index():
    return _index(load_records())


def _resolve(ref, index):
    """(targets, pin) for a URF reference, or (None, reason) when it does not parse."""
    try:
        u = URF.parse(ref)
    except Exception as e:  # the URF gate reports grammar; here an unparsable reference resolves to nothing
        return None, str(e)
    return index.get("/".join(u.path), []), u.pin


def _configuration(rec, index):
    errs = []
    who = rec.get("handle") or (rec.get("uuid") or "?")[:8]
    ref = rec.get("configures")
    if not isinstance(ref, str):
        return errs  # the schema requires it; nothing to resolve
    targets, pin = _resolve(ref, index)
    if targets is None:
        return [f"POL-012 {who}: `configures: {ref}` is not a reference ({pin})"]
    policies = [t for t in targets if t.get("record_type") == "policy"]
    if len(policies) != 1:
        what = ("resolves to nothing" if not targets else
                "resolves to a policy configuration, not a policy" if not policies else
                f"resolves to {len(policies)} policies")
        return [f"POL-012 {who}: `configures: {ref}` {what}. A configuration configures exactly one policy"]
    policy = policies[0]
    if pin and not pin.startswith("sha256:") and pin != policy.get("version"):
        errs.append(f"POL-012 {who}: pins {policy.get('handle')} at {pin}, and the policy is at "
                    f"{policy.get('version')}. The pin names a version that is not there")
    if (policy.get("status") or {}).get("state") == "retired":
        errs.append(f"POL-012 {who}: pins {policy.get('handle')}, which is retired. A retired policy "
                    f"cannot be configured")
    state = (rec.get("status") or {}).get("state")
    if (policy.get("status") or {}).get("state") == "proposed" and state in ("active", "deprecated"):
        errs.append(f"POL-015 {who}: is {state} and pins {policy.get('handle')}, which is proposed. Provisional "
                    f"logic runs in shadow mode only, so its configurations are proposed until the policy is active")

    schema, params = policy.get("parameter_schema"), rec.get("parameters")
    if schema is None:
        if params:
            errs.append(f"POL-013 {who}: supplies parameters {sorted(params)}, and {policy.get('handle')} "
                        f"declares none. They would be carried and never read")
    else:
        params = params or {}
        declared = set((schema.get("properties") or {}))
        for name in sorted(set(params) - declared):
            errs.append(f"POL-013 {who}: supplies `{name}`, which {policy.get('handle')} does not declare "
                        f"(it declares {sorted(declared)}). An undeclared parameter is never read")
        for e in sorted(Draft202012Validator(schema).iter_errors(params), key=lambda e: e.json_path):
            errs.append(f"POL-013 {who}: parameters do not satisfy {policy.get('handle')}'s "
                        f"parameter_schema at {e.json_path}: {e.message[:120]}")

    if rec.get("schedule") and policy.get("policy_type") not in SCHEDULED_TYPES:
        errs.append(f"ADR-053 {who}: schedule clauses on a configuration of a "
                    f"{policy.get('policy_type')!r} policy. A schedule governs WHEN a change may run, "
                    f"so it belongs with a `validation` or `orchestration_flow` policy")
    return errs


def _profile(rec, index):
    errs = []
    who = rec.get("handle") or (rec.get("uuid") or "?")[:8]
    for i, entry in enumerate(rec.get("contains") or []):
        ref = (entry or {}).get("ref")
        if not isinstance(ref, str):
            continue
        targets, _ = _resolve(ref, index)
        if not targets:
            continue  # another kind of artifact, or one this repository does not ship
        if any(t.get("record_type") == "policy" for t in targets):
            errs.append(f"POL-014 {who}: contains[{i}] `{ref}` is a policy. A profile turns a policy "
                        f"configuration on or off; a policy alone has no values and decides nothing")
        elif entry.get("settings"):
            errs.append(f"POL-014 {who}: contains[{i}] `{ref}` carries settings {sorted(entry['settings'])} "
                        f"for a policy configuration. The configuration holds its own values; a second "
                        f"home for one could disagree with the first")
    return errs


def evaluate(record, index):
    """Judge ONE record. Returns error strings; empty means it holds."""
    if not isinstance(record, dict):
        return []
    if record.get("record_type") == "policy_configuration":
        return _configuration(record, index)
    if record.get("record_type") == "profile":
        return _profile(record, index)
    return []


def self_test():
    """Each rule refuses its own negative, and a correct pair passes: a gate that cannot fail proves nothing."""
    policy = {"record_type": "policy", "uuid": "11111111-1111-4111-8111-111111111111", "handle": "t/gate",
              "version": "2.0.0", "policy_type": "validation",
              "parameter_schema": {"type": "object", "required": ["zones"],
                                   "properties": {"zones": {"type": "array", "items": {"type": "string"}}}}}
    bare = {"record_type": "policy", "uuid": "22222222-2222-4222-8222-222222222222", "handle": "t/bare",
            "version": "1.0.0", "policy_type": "placement"}
    good = {"record_type": "policy_configuration", "handle": "t/cfg", "configures": "t/gate@2.0.0",
            "parameters": {"zones": ["a"]}}
    trial = {"record_type": "policy", "uuid": "33333333-3333-4333-8333-333333333333", "handle": "t/trial",
             "version": "1.0.0", "policy_type": "validation", "status": {"state": "proposed"}}
    shadow = {"record_type": "policy_configuration", "handle": "t/shadow", "configures": "t/trial@1.0.0",
              "status": {"state": "proposed"}}
    index = _index([policy, bare, good, trial, shadow])
    cases = [
        ("a correct configuration", good, None),
        ("a proposed configuration of a proposed policy", shadow, None),
        ("an active configuration of a proposed policy", {**shadow, "status": {"state": "active"}}, "POL-015"),
        ("pin to a version that is not there", {**good, "configures": "t/gate@1.0.0"}, "POL-012"),
        ("reference that resolves to nothing", {**good, "configures": "t/missing@1.0.0"}, "POL-012"),
        ("reference to a configuration", {**good, "configures": "t/cfg@1.0.0"}, "POL-012"),
        ("missing required parameter", {**good, "parameters": {}}, "POL-013"),
        ("undeclared parameter", {**good, "parameters": {"zones": ["a"], "zone": "a"}}, "POL-013"),
        ("parameters for a policy that declares none",
         {**good, "configures": "t/bare@1.0.0", "parameters": {"zones": ["a"]}}, "POL-013"),
        ("schedule on a placement policy",
         {"record_type": "policy_configuration", "handle": "t/s", "configures": "t/bare@1.0.0",
          "schedule": [{"kind": "window"}]}, "ADR-053"),
        ("profile entry that names a policy",
         {"record_type": "profile", "handle": "t/p", "contains": [{"ref": "t/gate", "state": "required"}]},
         "POL-014"),
        ("profile entry with settings for a configuration",
         {"record_type": "profile", "handle": "t/p",
          "contains": [{"ref": "t/cfg", "state": "required", "settings": {"zones": ["b"]}}]}, "POL-014"),
        ("profile entry that turns a configuration on",
         {"record_type": "profile", "handle": "t/p", "contains": [{"ref": "t/cfg", "state": "required"}]}, None),
    ]
    fails = []
    for name, rec, want in cases:
        errs = evaluate(rec, index)
        if want is None and errs:
            fails.append(f"self-test: {name} was refused: {errs[0]}")
        elif want and not any(e.startswith(want) for e in errs):
            fails.append(f"self-test: {name} was not refused by {want} (got {errs[:1]})")
    return fails, len(cases)


def main():
    if "--self-test" in sys.argv:
        fails, n = self_test()
        for f in fails:
            print(f"  {f}")
        print(f"FAILED — {len(fails)} of {n} self-test case(s)" if fails
              else f"OK — {n} self-test case(s): every rule refuses its negative")
        return 1 if fails else 0
    records = load_records()
    index = _index(records)
    fails, n_cfg, n_prof = [], 0, 0
    for rec in records:
        n_cfg += rec.get("record_type") == "policy_configuration"
        n_prof += rec.get("record_type") == "profile"
        fails.extend(evaluate(rec, index))
    n_policy = sum(1 for r in records if r.get("record_type") == "policy")
    configured = set()
    for r in records:
        if r.get("record_type") == "policy_configuration" and isinstance(r.get("configures"), str):
            targets, _ = _resolve(r["configures"], index)
            configured.update(t.get("uuid") for t in targets or [] if t.get("record_type") == "policy")
    idle = sorted(r.get("handle") or r.get("uuid") for r in records
                  if r.get("record_type") == "policy" and r.get("uuid") not in configured)
    print(f"policy-configurations: {n_cfg} configuration(s) over {n_policy} policy record(s); "
          f"{n_prof} profile(s) read")
    if idle:
        # informational: a policy nobody configures decides nothing, which is legal for a shipped policy
        print(f"  not configured by any example: {', '.join(idle)}")
    for f in fails:
        print(f"  {f}")
    if fails:
        print(f"FAILED — {len(fails)} finding(s)")
        return 1
    print("OK — every configuration pins one policy and satisfies its parameters; "
          "no profile entry holds a policy's values")
    return 0


if __name__ == "__main__":
    sys.exit(main())
