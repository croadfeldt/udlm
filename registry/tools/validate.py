#!/usr/bin/env python3
"""Valid-by-construction gate. Validates:
  - registry/resource-types/*  against  resource-type-spec.schema.json   (TYPE definitions)
  - registry/instances/*       against  realized-entity.schema.json      (INSTANCE records)
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


def load(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(text)
    return json.loads(text)


def validate_dir(subdir: str, validator, label) -> int:
    failures = 0
    base = ROOT / subdir
    if not base.exists():
        return 0
    for path in sorted(base.glob("*")):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(path)
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


def main() -> int:
    failures = 0
    print("== resource types ==")
    failures += validate_dir(
        "resource-types", TYPE_VALIDATOR,
        lambda d: f"{d['resourceType']} v{d['version']} (conformsTo {d['conformsTo']})")
    print("== instances ==")
    failures += validate_dir(
        "instances", INSTANCE_VALIDATOR,
        lambda d: f"{d['resourceType']} instance {d['uuid'][:8]} [{d['lifecycleState']}]")
    print(f"\n{'FAILED' if failures else 'ALL VALID'} — {failures} invalid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
