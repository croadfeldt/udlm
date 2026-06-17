#!/usr/bin/env python3
"""Valid-by-construction gate: validate every Resource Type Specification in the registry
against the meta-schema (registry/resource-type-spec.schema.json). Loads JSON and YAML
natively. Exit non-zero if any entry is invalid. Wire into CI."""
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
META = json.loads((ROOT / "resource-type-spec.schema.json").read_text())
VALIDATOR = Draft202012Validator(META)


def load(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(text)
    return json.loads(text)


def main() -> int:
    failures = 0
    for path in sorted((ROOT / "resource-types").glob("*")):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        doc = load(path)
        errors = sorted(VALIDATOR.iter_errors(doc), key=lambda e: list(e.path))
        if errors:
            failures += 1
            print(f"FAIL {path.name}")
            for err in errors[:5]:
                loc = "/".join(str(p) for p in err.path) or "(root)"
                print(f"   - {loc}: {err.message}")
        else:
            print(f"ok   {path.name}  — {doc['resourceType']} v{doc['version']} "
                  f"(conformsTo {doc['conformsTo']})")
    print(f"\n{'FAILED' if failures else 'ALL VALID'} — {failures} invalid")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
