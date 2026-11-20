#!/usr/bin/env python3
"""Named-walk gate (DEP-019): every step in registry/walks.yaml is proven against the classes.

A named walk restates facts the classes own: that a class declares a relationship by a name, with an
edge type, to a target; that a class holds a reference in a field; that two classes state the same
value. A restatement drifts unless something compares it, so this gate does, against the served
specs in registry/generated/. A consumer that reads the walk file can then trust it without loading
a class.

What it refuses:

  shape         the file does not match registry/walk-registry.schema.json
  class         a step names a class that is not registered
  chain         a step reads from a class no earlier step reaches
  relationship  the class does not declare that relationship, declares it with another edge type, or
                not to that target; a forward step set leaves one of the relationship's targets out
                (a new subject class must enter the walk or be left out on purpose)
  ambiguity     one class reaches one target class by two relationships of the same edge type. An
                observed edge names no relation (RHY-007), so a consumer could not tell them apart
  field         a field path does not resolve on the class, a field_reference does not land on a
                Reference, or a join does not compare two strings in every pair it names
  identifier    an identifier_join's criteria are not applicability criteria, or it compares a
                basis the criteria do not offer, or an identifier field is not a string
  key scheme    target_key_scheme is not a correlation_ids scheme
  answer        a walk yields no affected record, or a service step does not read from one

Usage: check_walks.py            judge registry/walks.yaml
       check_walks.py --self-test  break the walk in each of the ways above and require a refusal
Exit 0 = clean; 1 = at least one violation.
"""
import copy
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "registry")
sys.path.insert(0, os.path.join(REG, "tools"))
import refstore  # noqa: E402  the shared offline $ref store

REFERENCE = "common-elements.schema.json#/$defs/Reference"


def load_specs():
    """Served class specs by class name: the effective elements, outputs and relationships."""
    specs = {}
    for path in sorted(glob.glob(os.path.join(REG, "generated", "*.json"))):
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        if isinstance(doc, dict) and doc.get("resource_type"):
            specs[doc["resource_type"]] = doc
    return specs


def key_schemes():
    with open(os.path.join(REG, "state-record.schema.json"), encoding="utf-8") as fh:
        schema = json.load(fh)
    return set(schema["$defs"]["correlation_ids"]["items"]["properties"]["scheme"]["enum"])


def covers(base, cls):
    """A Base name stands for its Types: `Machine` covers `Machine.VM`."""
    return cls == base or cls.startswith(base + ".")


def overlap(a, b):
    return covers(a, b) or covers(b, a)


def known(cls, specs):
    return cls in specs or any(covers(cls, name) for name in specs)


def deref(node):
    """Follow a `$ref` into a registry schema. Every registry schema sits in registry/."""
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 8:
        ref = node["$ref"]
        name, _, pointer = ref.partition("#")
        base = os.path.basename(name)
        if not base:
            return node
        path = os.path.join(REG, base)
        if not os.path.exists(path):
            return node
        with open(path, encoding="utf-8") as fh:
            target = json.load(fh)
        for part in [p for p in pointer.split("/") if p]:
            target = target.get(part) if isinstance(target, dict) else None
            if target is None:
                return node
        node, seen = target, seen + 1
    return node


def is_reference(node):
    return isinstance(node, dict) and (
        str(node.get("$ref", "")).endswith(REFERENCE) or node.get("format") == "udlm-ref-url")


def branches(node):
    """A schema node and every alternative it offers (oneOf, anyOf, allOf), refs followed."""
    out, todo = [], [node]
    while todo:
        cur = todo.pop()
        if not isinstance(cur, dict):
            continue
        out.append(cur)
        if "$ref" in cur and not is_reference(cur):
            target = deref(cur)
            if target is not cur:
                todo.append(target)
        for key in ("oneOf", "anyOf", "allOf"):
            todo.extend(cur.get(key) or [])
    return out


def resolve(spec, path):
    """The schema nodes a record path lands on, or [] when it resolves to nothing."""
    head, *rest = path.split(".")
    if head == "fields":
        nodes = [{"type": "object", "properties": (spec.get("spec") or {}).get("properties") or {}}]
    else:
        nodes = [{"type": "object", "properties": spec.get("outputs") or {}}]
    for segment in rest:
        each = segment.endswith("[]")
        name = segment[:-2] if each else segment
        found = []
        for node in nodes:
            for alt in branches(node):
                child = (alt.get("properties") or {}).get(name)
                if child is None:
                    continue
                if each:
                    for arr in branches(child):
                        if isinstance(arr.get("items"), dict):
                            found.append(arr["items"])
                else:
                    found.append(child)
        nodes = found
        if not nodes:
            return []
    return nodes


def is_string(nodes):
    """Every node the path lands on is a plain string. An alternative that is sometimes an object
    (an inline value or a reference to one) is not a value two records can be matched on."""
    return bool(nodes) and all(isinstance(deref(node), dict) and deref(node).get("type") == "string"
                               for node in nodes)


def judge(registry, specs, schemes, validate_shape=True):
    """Every violation in one walk registry, as readable lines."""
    fails = []
    if validate_shape:
        import warnings
        with warnings.catch_warnings():        # RefResolver is deprecated upstream; the shared store uses it
            warnings.simplefilter("ignore", DeprecationWarning)
            from jsonschema import Draft202012Validator, RefResolver
        with open(os.path.join(REG, "walk-registry.schema.json"), encoding="utf-8") as fh:
            schema = json.load(fh)
        resolver = RefResolver(base_uri=schema["$id"], referrer=schema, store=refstore.build_store())
        errors = sorted(Draft202012Validator(schema, resolver=resolver).iter_errors(registry),
                        key=lambda e: list(e.absolute_path))
        for err in errors:
            where = "/".join(str(p) for p in err.absolute_path) or "(root)"
            fails.append(f"shape: {where}: {err.message[:160]}")
        if errors:
            return fails

    names = [w["walk"] for w in registry["walks"]]
    for name in sorted({n for n in names if names.count(n) > 1}):
        fails.append(f"shape: walk {name!r} is declared twice")

    for walk in registry["walks"]:
        tag = f"walk {walk['walk']!r}"
        if not known(walk["start"], specs):
            fails.append(f"class: {tag} starts from {walk['start']!r}, which is not a registered class")
        reached = [walk["start"]]          # classes a step may read from
        affected = []                      # classes some step yields as affected
        step_names = [s["step"] for s in walk["steps"]]
        for name in sorted({n for n in step_names if step_names.count(n) > 1}):
            fails.append(f"shape: {tag} declares step {name!r} twice")
        forward = {}                       # (declared_on, relation) -> classes forward steps reach

        for step in walk["steps"]:
            at = f"{tag} step {step['step']!r}"
            classes = [step["from"], *step["to"]] + ([step["declared_on"]] if "declared_on" in step else [])
            missing = [c for c in classes if not known(c, specs)]
            for cls in missing:
                fails.append(f"class: {at} names {cls!r}, which is not a registered class")
            if not any(overlap(step["from"], r) for r in reached):
                fails.append(f"chain: {at} reads from {step['from']!r}, which no earlier step reaches")
            if step["yields"] == "service" and not any(overlap(step["from"], a) for a in affected):
                fails.append(f"answer: {at} yields a service but does not read from an affected class; "
                             f"a service restates the affected set and adds nothing to it")
            if not missing:
                if step["via"] == "relationship":
                    fails += judge_relationship(step, at, specs, schemes, forward)
                elif step["via"] == "field_reference":
                    fails += judge_field_reference(step, at, specs)
                elif step["via"] == "identifier_join":
                    fails += judge_identifier_join(step, at, specs)
                else:
                    fails += judge_join(step, at, specs)
            reached += step["to"]
            if step["yields"] == "affected":
                affected += step["to"]

        for (holder, relation), reached_targets in sorted(forward.items()):
            declared = [r["target"] for r in specs[holder].get("relationships") or []
                        if r.get("name") == relation]
            for target in declared:
                if not any(overlap(target, c) for c in reached_targets):
                    fails.append(f"relationship: {tag} follows {holder}.{relation} but no step reaches its "
                                 f"declared target {target!r}; add it to a step or the walk misses that class")
        if not affected:
            fails.append(f"answer: {tag} yields no affected record, so it has no affected set")
    return fails


def judge_relationship(step, at, specs, schemes, forward):
    fails = []
    holder, relation = step["declared_on"], step["relation"]
    if holder not in specs:
        return [f"relationship: {at}: {holder!r} is a family name, not a class that declares relationships"]
    every = specs[holder].get("relationships") or []
    named = [r for r in every if r.get("name") == relation]
    if not named:
        return [f"relationship: {at}: {holder} declares no relationship named {relation!r}"]
    for rel in named:
        if rel["edge_type"] != step["edge_type"]:
            fails.append(f"relationship: {at}: {holder}.{relation} is declared {rel['edge_type']!r}, "
                         f"the walk says {step['edge_type']!r}")
    targets = [r["target"] for r in named]
    if step["read"] == "forward":
        if not covers(holder, step["from"]):
            fails.append(f"relationship: {at} is read forward, so it must read from {holder!r}, "
                         f"not {step['from']!r}")
        for cls in step["to"]:
            if not any(covers(t, cls) for t in targets):
                fails.append(f"relationship: {at}: {holder}.{relation} does not declare {cls!r} as a target")
        forward.setdefault((holder, relation), []).extend(step["to"])
        concerned = step["to"]
    else:
        if not any(covers(t, step["from"]) for t in targets):
            fails.append(f"relationship: {at}: {holder}.{relation} does not declare {step['from']!r} "
                         f"as a target, so it cannot be read in reverse from it")
        for cls in step["to"]:
            if not covers(holder, cls):
                fails.append(f"relationship: {at} is read in reverse, so it reaches {holder!r}, not {cls!r}")
        concerned = [step["from"]]
    for cls in concerned:
        for rel in every:
            if (rel.get("name") != relation and rel["edge_type"] == step["edge_type"]
                    and overlap(rel["target"], cls)):
                other = rel.get("name") or "an unnamed relationship"
                fails.append(f"ambiguity: {at}: {holder} also reaches {rel['target']!r} by {other} with edge "
                             f"type {rel['edge_type']!r}. An observed edge names no relation (RHY-007), so "
                             f"it could not be told apart from {relation!r}")
    scheme = step.get("target_key_scheme")
    if scheme and scheme not in schemes:
        fails.append(f"key scheme: {at}: {scheme!r} is not a correlation_ids scheme")
    return fails


def judge_field_reference(step, at, specs):
    holder = step["declared_on"]
    if holder not in specs:
        return [f"field: {at}: {holder!r} is a family name, not a class that declares fields"]
    fails = []
    nodes = resolve(specs[holder], step["field"])
    if not nodes:
        fails.append(f"field: {at}: {step['field']} does not resolve on {holder}")
    elif not any(is_reference(alt) for node in nodes for alt in branches(node)):
        fails.append(f"field: {at}: {holder} {step['field']} is not a Reference, so it points at no record")
    for cls in step["to"]:
        if not covers(holder, cls):
            fails.append(f"field: {at} is read in reverse, so it reaches {holder!r}, not {cls!r}")
    return fails


def judge_join(step, at, specs):
    fails = []
    compared = step.get("match") or [{"from_field": step["from_field"], "to_field": step["to_field"]}]
    pairs = []
    for pair in compared:
        pairs += [(step["from"], pair["from_field"])] + [(cls, pair["to_field"]) for cls in step["to"]]
    for side in ("from_field", "to_field"):
        paths = [pair[side] for pair in compared]
        for path in sorted({p for p in paths if paths.count(p) > 1}):
            fails.append(f"field: {at}: {path} is compared twice, so one of the pairs says nothing")
    for cls, path in pairs:
        if cls not in specs:
            fails.append(f"field: {at}: {cls!r} is a family name; a join needs a class that declares the field")
            continue
        nodes = resolve(specs[cls], path)
        if not nodes:
            fails.append(f"field: {at}: {path} does not resolve on {cls}")
        elif not is_string(nodes):
            fails.append(f"field: {at}: {cls} {path} is not a string, so two records cannot state the same value")
    return fails


def judge_identifier_join(step, at, specs):
    fails = []
    holder = step["from"]
    if holder not in specs:
        return [f"field: {at}: {holder!r} is a family name; a join needs a class that declares the field"]
    nodes = [deref(n) for n in resolve(specs[holder], step["criteria"])]
    if not nodes:
        return [f"field: {at}: {step['criteria']} does not resolve on {holder}"]
    offered = set()
    for node in nodes:
        props = node.get("properties") or {} if isinstance(node, dict) else {}
        basis, criterion = deref(props.get("basis") or {}), deref(props.get("criterion") or {})
        if not (basis.get("enum") and criterion.get("type") == "string"):
            fails.append(f"identifier: {at}: {holder} {step['criteria']} is not a list of applicability criteria "
                         f"(a `basis` codelist and a `criterion` string)")
            continue
        offered |= set(basis["enum"])
    for ident in step["identifiers"]:
        if offered and ident["basis"] not in offered:
            fails.append(f"identifier: {at}: compares basis {ident['basis']!r}, which {holder} "
                         f"{step['criteria']} does not offer")
        for cls in step["to"]:
            if cls not in specs:
                fails.append(f"field: {at}: {cls!r} is a family name; a join needs a class that declares the field")
                continue
            got = resolve(specs[cls], ident["to_field"])
            if not got:
                fails.append(f"field: {at}: {ident['to_field']} does not resolve on {cls}")
            elif not is_string(got):
                fails.append(f"identifier: {at}: {cls} {ident['to_field']} is not a string, so it states no identifier")
    return fails


def self_test(registry, specs, schemes):
    """Break the real walk one way at a time. A gate that never refuses proves nothing."""
    def step(reg, name):
        return next(s for w in reg["walks"] for s in w["steps"] if s["step"] == name)

    def rename_relation(reg, sp):
        step(reg, "packages")["relation"] = "impacted_by"

    def wrong_edge_type(reg, sp):
        step(reg, "documents")["edge_type"] = "depends_on"

    def drop_declared_target(reg, sp):
        step(reg, "described_assets")["to"].remove("BMC")

    def undeclared_target(reg, sp):
        step(reg, "described_assets")["to"].append("Workload")

    def forward_from_wrong_class(reg, sp):
        step(reg, "images")["from"] = "SoftwarePackage"

    def reverse_from_non_target(reg, sp):
        step(reg, "documents")["from"] = "Vulnerability"

    def second_relation_to_one_target(reg, sp):
        sp["VexStatement"]["relationships"].append(
            {"edge_type": "references", "target": "Vulnerability", "name": "fixes"})

    def unknown_class(reg, sp):
        step(reg, "containers")["to"] = ["Pod"]

    def unreachable_from(reg, sp):
        step(reg, "containers")["from"] = "Volume"

    def join_field_missing(reg, sp):
        step(reg, "containers")["to_field"] = "fields.image.sha"

    def join_on_non_string(reg, sp):
        step(reg, "containers")["to_field"] = "fields.image"

    def join_pair_missing_on_one_class(reg, sp):
        step(reg, "devices")["match"][2]["to_field"] = "outputs.firmware"

    def join_pair_compared_twice(reg, sp):
        step(reg, "devices")["match"][1]["to_field"] = "fields.identity.manufacturer"

    def join_in_both_forms(reg, sp):
        step(reg, "devices").update(from_field="fields.version", to_field="outputs.firmware_version")

    def join_on_one_pair(reg, sp):
        del step(reg, "devices")["match"][1:]

    def identifier_criteria_missing(reg, sp):
        step(reg, "named_packages")["criteria"] = "fields.applicability[].products[]"

    def identifier_criteria_not_criteria(reg, sp):
        step(reg, "named_packages")["criteria"] = "fields.references[]"

    def identifier_field_missing(reg, sp):
        step(reg, "named_packages")["identifiers"][1]["to_field"] = "fields.cpe_name"

    def identifier_basis_not_offered(reg, sp):
        crit = sp["Vulnerability"]["spec"]["properties"]["applicability"]["items"]["properties"]["affects"]
        crit["items"] = {"type": "object", "properties": {"basis": {"type": "string", "enum": ["purl"]},
                                                          "criterion": {"type": "string"}}}

    def reference_field_missing(reg, sp):
        step(reg, "workloads")["field"] = "fields.constituents[].container"

    def field_is_not_a_reference(reg, sp):
        step(reg, "workloads")["field"] = "fields.constituents[].host"

    def unknown_key_scheme(reg, sp):
        step(reg, "packages")["target_key_scheme"] = "cve_number"

    def no_affected_step(reg, sp):
        for s in reg["walks"][0]["steps"]:
            if s["yields"] == "affected":
                s["yields"] = "evidence"

    def service_not_from_affected(reg, sp):
        step(reg, "containers")["yields"] = "evidence"

    def bad_shape(reg, sp):
        step(reg, "containers")["relation"] = "runs"

    def duplicate_step(reg, sp):
        reg["walks"][0]["steps"].append(copy.deepcopy(step(reg, "workloads")))

    cases = [rename_relation, wrong_edge_type, drop_declared_target, undeclared_target,
             forward_from_wrong_class, reverse_from_non_target, second_relation_to_one_target,
             unknown_class, unreachable_from, join_field_missing, join_on_non_string,
             join_pair_missing_on_one_class, join_pair_compared_twice, join_in_both_forms, join_on_one_pair,
             identifier_criteria_missing, identifier_criteria_not_criteria, identifier_field_missing,
             identifier_basis_not_offered,
             reference_field_missing, field_is_not_a_reference, unknown_key_scheme, no_affected_step,
             service_not_from_affected, bad_shape, duplicate_step]
    bad = 0
    clean = judge(registry, specs, schemes)
    if clean:
        print("FAIL self-test: the walk file as written is refused:", clean[0])
        bad += 1
    for case in cases:
        reg, sp = copy.deepcopy(registry), copy.deepcopy(specs)
        case(reg, sp)
        refused = judge(reg, sp, schemes)
        label = case.__name__.replace("_", " ")
        if refused:
            print(f"ok   self-test: {label} -> {refused[0][:110]}")
        else:
            print(f"FAIL self-test: {label} was accepted")
            bad += 1
    print(f"check_walks --self-test: {len(cases)} breakage(s) tried, {bad} failure(s)")
    return 1 if bad else 0


def main():
    with open(os.path.join(REG, "walks.yaml"), encoding="utf-8") as fh:
        registry = yaml.safe_load(fh)
    specs, schemes = load_specs(), key_schemes()
    if "--self-test" in sys.argv:
        return self_test(registry, specs, schemes)
    fails = judge(registry, specs, schemes)
    for line in fails:
        print("FAIL", line)
    steps = sum(len(w["steps"]) for w in registry.get("walks") or [])
    print(f"named walks: {len(registry.get('walks') or [])} walk(s), {steps} step(s) proven against "
          f"{len(specs)} class spec(s); {len(fails)} violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
