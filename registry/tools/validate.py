#!/usr/bin/env python3
"""Valid-by-construction gate. Validates:
  - registry/resource-types/*  against  resource-type-spec.schema.json        (TYPE definitions)
  - registry/instances/*       against  realized-entity.schema.json           (INSTANCE records)
                        or against  dcm-group.schema.json                     (DCMGroup records)
                        or against  catalog-item.schema.json                  (Composite Service catalog items)
  - registry/providers/*       against  provider-adopted-standards.schema.json (provider support matrices)
Instance dispatch: `record_type` is the dispatch key going forward (catalog_item → catalog
schema); legacy discriminators remain — a document with a top-level `group_class` is a
DCMGroup; one with `resource_type` is a realized entity (data-model-core §5 — Tenants ARE
DCMGroups). Catalog items additionally get semantic checks JSON Schema cannot express
(component_id uniqueness, sibling depends_on/binding resolution, cycle rejection,
binding⊆depends_on ordering).
Loads JSON and YAML natively. Exit non-zero if anything is invalid. Wire into CI."""
import json
import sys
import pathlib

try:
    from jsonschema import Draft202012Validator
except ImportError:
    sys.exit("requires: pip install jsonschema")
try:
    import yaml
except ImportError:
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
TYPE_VALIDATOR = Draft202012Validator(json.loads((ROOT / "resource-type-spec.schema.json").read_text()))
INSTANCE_VALIDATOR = Draft202012Validator(json.loads((ROOT / "realized-entity.schema.json").read_text()))
GROUP_VALIDATOR = Draft202012Validator(json.loads((ROOT / "dcm-group.schema.json").read_text()))
PROVIDER_VALIDATOR = Draft202012Validator(json.loads((ROOT / "provider-adopted-standards.schema.json").read_text()))
CATALOG_VALIDATOR = Draft202012Validator(json.loads((ROOT / "catalog-item.schema.json").read_text()))
POLICY_VALIDATOR = Draft202012Validator(json.loads((ROOT / "policy.schema.json").read_text()))
LAYER_VALIDATOR = Draft202012Validator(json.loads((ROOT / "layer.schema.json").read_text()))
AUDIT_RECORD_VALIDATOR = Draft202012Validator(json.loads((ROOT / "audit-record.schema.json").read_text()))
COMMIT_LOG_VALIDATOR = Draft202012Validator(json.loads((ROOT / "commit-log-entry.schema.json").read_text()))
AUDIT_LEAF_VALIDATOR = Draft202012Validator(json.loads((ROOT / "audit-leaf.schema.json").read_text()))


def _type_outputs_index():
    """resource_type -> set(declared output names). The typed-outputs surface a catalog-item
    binding resolves against (data-model-core §2 [D8.3])."""
    index = {}
    for path in (ROOT / "resource-types").glob("*"):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(path)
        index[doc["resource_type"]] = set((doc.get("outputs") or {}).keys())
    return index


def load(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(text)
    return json.loads(text)


def validate_dir(subdir: str, pick) -> int:
    """pick(doc) -> (validator, label_fn[, checks_fn]) — per-document dispatch.
    checks_fn(doc) -> [error strings] runs semantic checks JSON Schema cannot express;
    any returned error makes the document invalid."""
    failures = 0
    base = ROOT / subdir
    if not base.exists():
        return 0
    for path in sorted(base.glob("*")):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(path)
        picked = pick(doc)
        validator, label = picked[0], picked[1]
        checks = picked[2] if len(picked) > 2 else None
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        semantic = checks(doc) if checks and not errors else []
        if errors or semantic:
            failures += 1
            print(f"FAIL {path.name}")
            for err in errors[:5]:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                print(f"   - {loc}: {err.message}")
            for msg in semantic:
                print(f"   - {msg}")
        else:
            print(f"ok   {path.name}  — {label(doc)}")
    return failures


def check_catalog_item(doc):
    """Semantic checks for Composite Service catalog items — the cross-field constraints
    JSON Schema cannot express (catalog-item.schema.json description; composite-service-model.md
    §2.3/§10 registration rejection rules):
      (a) component_id unique within the item
      (b) every depends_on / bindings.from_component resolves to a sibling component_id
      (c) the depends_on graph is acyclic (CMP-002 ordering derives from it)
      (d) a binding's from_component appears in that constituent's depends_on
          (data movement implies ordering)."""
    errors = []
    constituents = doc.get("constituents", [])

    # (a) component_id uniqueness
    ids = [c.get("component_id") for c in constituents]
    seen = set()
    for cid in ids:
        if cid in seen:
            errors.append(f"constituents: duplicate component_id '{cid}' — must be unique within the item")
        seen.add(cid)
    id_set = set(ids)

    # (b) sibling resolution + (d) binding ⊆ depends_on
    for c in constituents:
        cid = c.get("component_id", "?")
        deps = c.get("depends_on", [])
        for dep in deps:
            if dep not in id_set:
                errors.append(f"constituent '{cid}': depends_on '{dep}' does not resolve to a sibling component_id")
        for b in c.get("bindings", []):
            src = b.get("from_component")
            if src not in id_set:
                errors.append(f"constituent '{cid}': binding from_component '{src}' does not resolve to a sibling component_id")
            elif src not in deps:
                errors.append(f"constituent '{cid}': binding from_component '{src}' missing from depends_on — data movement implies ordering")

    # (c) cycle detection — DFS, 3-color
    graph = {c.get("component_id"): [d for d in c.get("depends_on", []) if d in id_set]
             for c in constituents}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in graph}

    def dfs(node, path):
        color[node] = GRAY
        for dep in graph.get(node, []):
            if color[dep] == GRAY:
                cycle = path[path.index(dep):] + [dep] if dep in path else [node, dep]
                errors.append("constituents: depends_on cycle " + " -> ".join(cycle))
                return True
            if color[dep] == WHITE and dfs(dep, path + [dep]):
                return True
        color[node] = BLACK
        return False

    for cid in graph:
        if color[cid] == WHITE and dfs(cid, [cid]):
            break  # one reported cycle is enough

    # (e) binding output type-safety: a binding's `output` must be a DECLARED output of the
    #     producer constituent's resource_type (data-model-core §2 [D8.3] typed outputs).
    #     Skip gracefully if the type is not in the registry; FAIL if the type is known and the
    #     output is not one of its declared output names.
    type_outputs = _type_outputs_index()
    rt_of = {c.get("component_id"): c.get("resource_type") for c in constituents}
    for c in constituents:
        cid = c.get("component_id", "?")
        for b in c.get("bindings", []):
            src, out = b.get("from_component"), b.get("output")
            src_type = rt_of.get(src)
            if src_type in type_outputs and out not in type_outputs[src_type]:
                declared = sorted(type_outputs[src_type]) or ["(none declared)"]
                errors.append(
                    f"constituent '{cid}': binding output '{src}.{out}' is not a declared output of "
                    f"{src_type} (declared: {', '.join(declared)})")

    return errors


def pick_instance(doc):
    """Dispatch: `record_type` first (catalog_item ⇒ catalog item, + semantic checks);
    legacy keys — `group_class` ⇒ DCMGroup; `resource_type` ⇒ realized entity."""
    if isinstance(doc, dict) and doc.get("record_type") == "catalog_item":
        return (CATALOG_VALIDATOR,
                lambda d: f"catalog item {d['name']} v{d['version']} {d['uuid'][:8]} ({len(d['constituents'])} constituents)",
                check_catalog_item)
    if isinstance(doc, dict) and doc.get("record_type") == "policy":
        return POLICY_VALIDATOR, lambda d: f"policy {d['name']} ({d['policy_type']}) {d['uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "layer":
        return LAYER_VALIDATOR, lambda d: f"layer {d['name']} ({d['layer_type']}) {d['uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "audit_record":
        return AUDIT_RECORD_VALIDATOR, lambda d: f"audit_record {d['action']} {d['record_uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "commit_log_entry":
        return COMMIT_LOG_VALIDATOR, lambda d: f"commit_log_entry seq={d['sequence']} {d['action']} {d['entry_uuid'][:8]}"
    if isinstance(doc, dict) and doc.get("record_type") == "audit_leaf":
        return AUDIT_LEAF_VALIDATOR, lambda d: f"audit_leaf idx={d['leaf_index']} {d['stage']} {d['leaf_uuid'][:8]}"
    if isinstance(doc, dict) and "group_class" in doc:
        return GROUP_VALIDATOR, lambda d: f"DCMGroup {d['group_class']} {d['uuid'][:8]} [{d.get('status', {}).get('state', '?')}]"
    return INSTANCE_VALIDATOR, lambda d: f"{d['resource_type']} instance {d['uuid'][:8]} [{d['lifecycle_state']}]"


def main() -> int:
    failures = 0
    print("== resource types ==")
    failures += validate_dir(
        "resource-types",
        lambda doc: (TYPE_VALIDATOR,
                     lambda d: f"{d['resource_type']} v{d['version']} (conforms_to {d['conforms_to']})"))
    print("== instances (realized entities + DCMGroups + catalog items) ==")
    failures += validate_dir("instances", pick_instance)
    print("== providers (adopted-standard support) ==")
    failures += validate_dir(
        "providers",
        lambda doc: (PROVIDER_VALIDATOR,
                     lambda d: f"{d['provider']['name']} — {', '.join(s['standard'] for s in d['adopted_standard_support'])}"))
    print(f"\n{'FAILED' if failures else 'ALL VALID'} — {failures} invalid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
