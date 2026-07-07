#!/usr/bin/env python3
"""Valid-by-construction gate. Validates:
  - registry/resource-types/*  against  resource-type-spec.schema.json        (TYPE definitions)
  - registry/instances/*       against  realized-entity.schema.json           (INSTANCE records)
                        or against  dcm-group.schema.json                     (DCMGroup records)
  - registry/providers/*       against  provider-adopted-standards.schema.json (provider support matrices)
Instance dispatch: a document with a top-level `group_class` is a DCMGroup; one with
`resource_type` is a realized entity (data-model-core §5 — Tenants ARE DCMGroups).
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


def load(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(text)
    return json.loads(text)


def validate_dir(subdir: str, pick) -> int:
    """pick(doc) -> (validator, label_fn) — per-document dispatch."""
    failures = 0
    base = ROOT / subdir
    if not base.exists():
        return 0
    for path in sorted(base.glob("*")):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(path)
        validator, label = pick(doc)
        errors = sorted(validator.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            failures += 1
            print(f"FAIL {path.name}")
            for err in errors[:5]:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                print(f"   - {loc}: {err.message}")
        else:
            print(f"ok   {path.name}  — {label(doc)}")
    return failures


def pick_instance(doc):
    """Dispatch: `group_class` ⇒ DCMGroup; `resource_type` ⇒ realized entity."""
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
    print("== instances (realized entities + DCMGroups) ==")
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
