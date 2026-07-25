#!/usr/bin/env python3
"""Instance-fuzz gate for resource-type specs (model-validation depth, deterministic layer).

For every registry/resource-types/* definition this harness proves, per type, that the spec
schema is BOTH satisfiable and discriminating:

  ACCEPT  (a) a minimal valid instance can be synthesized from the schema itself, and validates.
          A schema no instance can satisfy is a spec bug no reviewer will catch by reading.
  REJECT  (b) dropping any required property fails validation;
          (c) violating any enum/const fails validation;
          (d) wrong-typing any top-level property with a declared type fails validation.
          A schema that accepts these is over-permissive: it will bless malformed intent.
  OUTPUTS (e) every declared output schema compiles and is itself satisfiable — outputs are the
          binding surface (data-model-core §2 [D8.3]); an unsatisfiable output schema means no
          provider observation can ever conform to it.

  STRICT  (f) unknown top-level keys are rejected — strict-by-default ruling, 2026-07-24: a
          misspelled optional property must fail validation, not silently drop intent. Every
          spec carries additionalProperties: false; extensibility routes through declared
          escape hatches (x-extensible-enum style), never through undeclared keys.

No fixtures: instances are synthesized from the schemas, so new/changed types are covered the
commit they land. Exit non-zero on any ACCEPT/REJECT/OUTPUTS failure. Wire into CI.
"""
import json
import pathlib
import re
import sys

try:
    from jsonschema import Draft202012Validator, RefResolver
except ImportError:
    sys.exit("requires: pip install jsonschema")
try:
    import yaml
except ImportError:
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
TYPES_DIR = ROOT / "resource-types"

# Candidate strings tried against `pattern` constraints, most-common shapes first.
PATTERN_CANDIDATES = [
    "example", "example-1", "example.one", "cexample/example", "Compute.VirtualMachine",
    "1.0.0", "0.1.0", "192.0.2.1", "192.0.2.0/24", "00:11:22:33:44:55",
    "123e4567-e89b-42d3-a456-426614174000", "2026-01-01T00:00:00Z", "2026-01-01",
    "example.example.com", "https://example.example.com/x", "sha256:" + "0" * 64,
    "urn:example:1", "a", "A", "1", "42",
    "P1D", "PT1H", "P1DT1H",          # ISO-8601 durations
    "100GB", "10GiB", "1TB",          # size strings
]
FORMAT_VALUES = {
    "uuid": "123e4567-e89b-42d3-a456-426614174000",
    "date-time": "2026-01-01T00:00:00Z",
    "date": "2026-01-01",
    "uri": "https://example.example.com/x",
    "hostname": "example.example.com",
    "ipv4": "192.0.2.1",
    "email": "user@example.example.com",
}


def load(path: pathlib.Path):
    text = path.read_text()
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"{path.name}: requires PyYAML for YAML specs")
        return yaml.safe_load(text)
    return json.loads(text)


class Unsatisfiable(Exception):
    pass


class Synthesizer:
    """Generate a minimal instance for a JSON Schema subtree, resolving $refs via resolver."""

    def __init__(self, resolver: RefResolver):
        self.resolver = resolver

    def gen(self, schema, depth=0):
        if depth > 30:
            raise Unsatisfiable("recursion depth exceeded")
        if schema is True or schema == {}:
            return "example"
        if schema is False:
            raise Unsatisfiable("false schema")

        if "$ref" in schema:
            url, resolved = self.resolver.resolve(schema["$ref"])
            self.resolver.push_scope(url)
            try:
                return self.gen(resolved, depth + 1)
            finally:
                self.resolver.pop_scope()

        if "const" in schema:
            return schema["const"]
        if "enum" in schema:
            return schema["enum"][0]
        if schema.get("examples"):
            return schema["examples"][0]
        if "default" in schema:
            return schema["default"]

        if "allOf" in schema:
            merged = self._merge_allof(schema, depth)
            return merged
        for comb in ("oneOf", "anyOf"):
            if comb in schema:
                last_err = None
                for branch in schema[comb]:
                    try:
                        # Branch constraints layered over the parent's own keywords.
                        base = {k: v for k, v in schema.items() if k != comb}
                        return self.gen(self._shallow_merge(base, branch), depth + 1)
                    except Unsatisfiable as e:
                        last_err = e
                raise Unsatisfiable(f"no satisfiable {comb} branch ({last_err})")

        t = schema.get("type")
        if isinstance(t, list):
            t = t[0]
        if t == "object" or (t is None and ("properties" in schema or "required" in schema)):
            return self._gen_object(schema, depth)
        if t == "array":
            n = schema.get("minItems", 1)
            item_schema = schema.get("items", {})
            items = [self.gen(item_schema, depth + 1) for _ in range(max(n, 1))]
            if schema.get("uniqueItems") and len(items) > 1:
                items = self._uniquify(items)
            return items
        if t == "string" or (t is None and ("pattern" in schema or "format" in schema)):
            return self._gen_string(schema)
        if t == "integer" or t == "number":
            lo = schema.get("minimum", schema.get("exclusiveMinimum"))
            v = 1 if lo is None else (lo + 1 if "exclusiveMinimum" in schema else lo)
            if "multipleOf" in schema:
                m = schema["multipleOf"]
                v = m * max(1, -(-v // m))  # smallest multiple >= v
            return int(v) if t == "integer" else v
        if t == "boolean":
            return True
        if t == "null":
            return None
        # No type constraint at all — a bare annotation schema.
        return "example"

    def _shallow_merge(self, base, overlay):
        out = dict(base)
        for k, v in overlay.items():
            if k in ("required",) and k in out:
                out[k] = sorted(set(out[k]) | set(v))
            elif k == "properties" and k in out:
                out[k] = {**out[k], **v}
            else:
                out[k] = v
        return out

    def _merge_allof(self, schema, depth):
        merged = {k: v for k, v in schema.items() if k != "allOf"}
        for branch in schema["allOf"]:
            if "$ref" in branch:
                url, resolved = self.resolver.resolve(branch["$ref"])
                self.resolver.push_scope(url)
                try:
                    merged = self._shallow_merge(merged, resolved)
                finally:
                    self.resolver.pop_scope()
            else:
                merged = self._shallow_merge(merged, branch)
        return self.gen(merged, depth + 1)

    def _gen_object(self, schema, depth):
        out = {}
        props = schema.get("properties", {})
        for req in schema.get("required", []):
            out[req] = self.gen(props.get(req, {}), depth + 1)
        if not out and schema.get("minProperties"):
            for k, v in list(props.items())[: schema["minProperties"]]:
                out[k] = self.gen(v, depth + 1)
        return out

    def _gen_string(self, schema):
        if "format" in schema and schema["format"] in FORMAT_VALUES:
            v = FORMAT_VALUES[schema["format"]]
            if "pattern" not in schema or re.search(schema["pattern"], v):
                return v
        if "pattern" in schema:
            for cand in PATTERN_CANDIDATES:
                if re.search(schema["pattern"], cand):
                    return self._fit_length(cand, schema)
            raise Unsatisfiable(f"no candidate matches pattern {schema['pattern']!r}")
        return self._fit_length("example", schema)

    @staticmethod
    def _fit_length(s, schema):
        lo, hi = schema.get("minLength", 0), schema.get("maxLength")
        if len(s) < lo:
            s = s + "x" * (lo - len(s))
        if hi is not None and len(s) > hi:
            raise Unsatisfiable(f"candidate exceeds maxLength {hi}")
        return s

    @staticmethod
    def _uniquify(items):
        seen, out = [], []
        for i, it in enumerate(items):
            if it in seen and isinstance(it, str):
                it = f"{it}-{i}"
            seen.append(it)
            out.append(it)
        return out


def spec_validator(doc, path):
    """Compile the type's spec subschema with $refs resolving relative to the type file."""
    spec = doc.get("spec") or {"type": "object"}
    resolver = RefResolver(base_uri=path.as_uri(), referrer=doc)
    return spec, Draft202012Validator(spec, resolver=resolver), resolver


def valid(validator, instance):
    return not list(validator.iter_errors(instance))


def fuzz_type(path):
    doc = load(path)
    rt = doc.get("resource_type", path.name)
    spec, validator, resolver = spec_validator(doc, path)
    synth = Synthesizer(resolver)
    errors = []

    # (a) satisfiability
    try:
        instance = synth.gen(spec)
    except Unsatisfiable as e:
        return [f"{rt}: UNSATISFIABLE — could not synthesize any instance ({e})"], 0
    if not valid(validator, instance):
        msgs = [e.message for e in validator.iter_errors(instance)][:3]
        return [f"{rt}: synthesized minimal instance REJECTED by its own spec — {'; '.join(msgs)}"], 0

    mutations = 0
    props = spec.get("properties", {})
    required = spec.get("required", [])

    # (b) required discrimination
    for req in required:
        mutated = {k: v for k, v in instance.items() if k != req}
        mutations += 1
        if valid(validator, mutated):
            errors.append(f"{rt}: dropping required '{req}' still validates — required not enforced")

    # (c) enum/const discrimination (top-level reachable enums)
    for name, psch in props.items():
        target = psch
        if "$ref" in target:
            try:
                _, target = resolver.resolve(target["$ref"])
            except Exception:
                continue
        if "enum" in target or "const" in target:
            mutated = dict(instance)
            mutated[name] = "___fuzz_invalid_enum___"
            mutations += 1
            if valid(validator, mutated):
                errors.append(f"{rt}: enum property '{name}' accepts out-of-vocabulary value")

    # (d) wrong-type discrimination for typed top-level properties present in the instance
    for name in list(instance.keys()):
        psch = props.get(name, {})
        t = psch.get("type")
        if not t:
            continue
        poison = 42 if t not in ("integer", "number") else {"___fuzz___": True}
        mutated = dict(instance)
        mutated[name] = poison
        mutations += 1
        if valid(validator, mutated):
            errors.append(f"{rt}: property '{name}' (type {t}) accepts wrong-typed value")

    # (f) unknown-key strictness — strict-by-default (2026-07-24 ruling): a misspelled
    # optional property must fail, not silently drop intent
    mutated = dict(instance)
    mutated["___fuzz_unknown_key___"] = "x"
    mutations += 1
    if valid(validator, mutated):
        errors.append(f"{rt}: accepts unknown top-level key — spec must declare additionalProperties: false")

    # (e) outputs satisfiability
    for oname, osch in (doc.get("outputs") or {}).items():
        try:
            oval = Draft202012Validator(osch, resolver=resolver)
            oinst = synth.gen(osch)
            mutations += 1
            if not valid(oval, oinst):
                errors.append(f"{rt}: output '{oname}' rejects its own synthesized value")
        except Unsatisfiable as e:
            errors.append(f"{rt}: output '{oname}' schema is unsatisfiable ({e})")
        except Exception as e:
            errors.append(f"{rt}: output '{oname}' schema failed to compile ({e})")

    return errors, mutations


def main():
    paths = sorted(p for p in TYPES_DIR.glob("*") if p.suffix in (".json", ".yaml", ".yml"))
    all_errors, total_mut = [], 0
    for path in paths:
        try:
            errors, mutations = fuzz_type(path)
        except Exception as e:
            errors, mutations = [f"{path.name}: harness error — {e}"], 0
        all_errors.extend(errors)
        total_mut += mutations

    print(f"fuzzed {len(paths)} types, {total_mut} mutations")
    if all_errors:
        print(f"\nFAIL — {len(all_errors)} finding(s):")
        for e in all_errors:
            print(f"  {e}")
        return 1
    print("OK — every spec is satisfiable and discriminating")
    return 0


if __name__ == "__main__":
    sys.exit(main())
