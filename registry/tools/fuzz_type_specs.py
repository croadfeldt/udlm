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

  DEEP    (g) a recursive schema-instance co-walk mutates EVERY reachable path of the instance
          (nested objects, array items, combinator-branch content) against the LOCAL subschema
          governing that path: drop a locally-required key, violate a local enum/const,
          wrong-type a locally-typed value, inject an unknown key where local
          additionalProperties is false, and break local boundaries (minItems-1, minimum-1,
          maximum+1, maxLength+1, minLength-1, pattern-breaking string). Every such mutation
          must make the WHOLE instance fail validation: a mutation the whole spec still accepts
          is a finding — a locally-declared constraint that whole-spec validation does not
          enforce (e.g. a permissive alternate combinator branch that hollows it out). Paths
          with no local constraint are never flagged. The walk instance is the minimal instance
          greedily and recursively enriched with every optional property that still validates,
          so optional subtrees (e.g. the recursive storage.pool vdev tree) are reached; $refs
          are resolved through a local store (file URI + $id) so the walk is offline and
          deterministic, and ref chains/cycles are depth-capped.

No fixtures: instances are synthesized from the schemas, so new/changed types are covered the
commit they land. Exit non-zero on any ACCEPT/REJECT/OUTPUTS/DEEP failure. Wire into CI.
"""
import copy
import json
import pathlib
import re
import sys
from urllib.parse import urldefrag, urljoin

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


def _build_store():
    """Local $ref resolution store: every registry/*.schema.json under BOTH its file URI (what a
    relative ../x.schema.json ref resolves to) and its declared $id (what the absolute
    https://udlm.dev/... form resolves to). Refs resolve offline and deterministically — the
    deep walk must never depend on the network."""
    store = {}
    for p in sorted(ROOT.glob("*.schema.json")):
        doc = json.loads(p.read_text())
        store[p.as_uri()] = doc
        if isinstance(doc.get("$id"), str):
            store[doc["$id"]] = doc
    return store


STORE = _build_store()


def _resolve_pointer(doc, pointer):
    """Minimal RFC 6901 JSON-pointer walk (fragment part of a $ref)."""
    tgt = doc
    for part in [p for p in pointer.split("/") if p]:
        part = part.replace("~1", "/").replace("~0", "~")
        tgt = tgt[int(part)] if isinstance(tgt, list) else tgt[part]
    return tgt


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
    """Compile the type's spec subschema with $refs resolving relative to the type file.

    referrer is the SPEC, not the enclosing type doc: `spec` is the schema being compiled, so a
    fragment-only ref inside it ("#/$defs/vdev", storage.pool) must resolve against the spec's
    own root — against the type doc it would dangle ($defs sits under spec). The shared STORE
    makes cross-file and absolute-$id refs resolve offline."""
    spec = doc.get("spec") or {"type": "object"}
    resolver = RefResolver(base_uri=path.as_uri(), referrer=spec, store=STORE)
    return spec, Draft202012Validator(spec, resolver=resolver), resolver


def valid(validator, instance):
    return not list(validator.iter_errors(instance))


# JSON-type membership per JSON Schema semantics (bool is NOT integer/number).
_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}
_POISONS = [42, "___fuzz_wrong_type___", {"___fuzz___": True}, ["___fuzz___"], True, None]
_PATTERN_BREAKERS = ["", "¤fuzz no match¤", "___fuzz___", "zz zz zz", "!"]




class DeepWalker:
    """Section (g): recursive schema-instance co-walk. Records a mutation for every local
    constraint at every reachable instance path, then evaluates each against the WHOLE spec.
    A mutation the whole spec still accepts is a finding: the local constraint exists but
    whole-spec validation does not enforce it (a permissive alternate combinator branch, a
    mis-wired subschema). Combinator overlap that swallows a violation is reported, not
    excused — a constraint an alternate branch hollows out constrains nothing."""

    MAX_DEPTH = 24

    def __init__(self, rt, spec, validator, base_uri, instance):
        self.rt, self.spec, self.validator = rt, spec, validator
        self.root_base = urldefrag(base_uri)[0]
        self.instance = instance
        self.recorded = []       # {desc, op, path, key, value}
        self.mutations = 0
        self.findings = []

    # -- schema resolution ------------------------------------------------------------
    def _doc_for(self, base):
        return self.spec if base == self.root_base else STORE.get(base)

    def _deref(self, ref, scope, seen):
        url = urljoin(scope, ref)
        if url in seen:
            return None, scope, seen
        base, frag = urldefrag(url)
        doc = self._doc_for(base or self.root_base)
        if doc is None:
            return None, scope, seen
        try:
            return _resolve_pointer(doc, frag), (base or scope), seen + (url,)
        except (KeyError, IndexError, ValueError):
            return None, scope, seen

    def _effective(self, schema, scope, seen=()):
        """Fold $ref chains and allOf into one local dict (Synthesizer merge semantics);
        oneOf/anyOf stay in place for branch selection. Returns (merged, scope)."""
        while isinstance(schema, dict) and "$ref" in schema:
            siblings = {k: v for k, v in schema.items() if k != "$ref"}
            target, scope, seen = self._deref(schema["$ref"], scope, seen)
            if target is None:
                return None, scope
            schema = _shallow_merge_schemas(target, siblings) if siblings else target
        if not isinstance(schema, dict):
            return None, scope
        if "allOf" in schema:
            merged = {k: v for k, v in schema.items() if k != "allOf"}
            for branch in schema["allOf"]:
                eff, _ = self._effective(branch, scope, seen)
                if eff is None:
                    return None, scope
                merged = _shallow_merge_schemas(merged, eff)
            schema = merged
        return schema, scope

    def _validator_at(self, schema, scope):
        base = urldefrag(scope)[0]
        resolver = RefResolver(base_uri=base, referrer=self._doc_for(base) or schema, store=STORE)
        return Draft202012Validator(schema, resolver=resolver)

    # -- enrichment -------------------------------------------------------------------
    def enrich(self, synth):
        """Greedily add every optional property — RECURSIVELY, in declaration order
        (deterministic) — whose synthesized value keeps the WHOLE instance valid. This is what
        makes optional subtrees (the recursive storage.pool vdev tree, nested config blocks,
        combinator-branch content) reachable by the walk. An addition the whole spec rejects
        (a mutually-exclusive field, an unsatisfiable combo) is dropped, never forced."""
        self._enrich_node(self.spec, self.instance, self.root_base, 0, synth)
        return self.instance

    def _enrich_node(self, schema, value, scope, depth, synth):
        if depth > self.MAX_DEPTH:
            return
        es, scope = self._effective(schema, scope)
        if es is None:
            return
        if "oneOf" in es or "anyOf" in es:
            es = self._select_branch(es, value, scope)
            if es is None:
                return
        if isinstance(value, dict):
            props = es.get("properties") or {}
            for name, psch in props.items():
                if name in value:
                    continue
                try:
                    cand = synth.gen(psch)
                except Exception:      # unsatisfiable, or a cross-scope ref gen can't place
                    continue
                value[name] = cand
                if not valid(self.validator, self.instance):
                    del value[name]
            for name, v in list(value.items()):
                if name in props:
                    self._enrich_node(props[name], v, scope, depth + 1, synth)
        elif isinstance(value, list):
            items, prefix = es.get("items"), es.get("prefixItems")
            for i, v in enumerate(value):
                sub = prefix[i] if prefix and i < len(prefix) else items
                if isinstance(sub, dict):
                    self._enrich_node(sub, v, scope, depth + 1, synth)

    # -- the walk ---------------------------------------------------------------------
    def walk(self, schema, value, path, scope, depth=0):
        if depth > self.MAX_DEPTH:
            return
        es, scope = self._effective(schema, scope)
        if es is None:
            return
        if "oneOf" in es or "anyOf" in es:
            es = self._select_branch(es, value, scope)
            if es is None:
                return
        self._mutate_here(es, value, path)
        if isinstance(value, dict):
            props = es.get("properties") or {}
            for k, v in value.items():
                if k in props:
                    self.walk(props[k], v, path + [k], scope, depth + 1)
        elif isinstance(value, list):
            items, prefix = es.get("items"), es.get("prefixItems")
            for i, v in enumerate(value):
                sub = prefix[i] if prefix and i < len(prefix) else items
                if isinstance(sub, dict):
                    self.walk(sub, v, path + [i], scope, depth + 1)

    def _select_branch(self, es, value, scope):
        """Pick the oneOf/anyOf branch the current value actually satisfies (layered over the
        node's own keywords, like the Synthesizer) — its constraints are the local law here."""
        base = {k: v for k, v in es.items() if k not in ("oneOf", "anyOf")}
        for comb in ("oneOf", "anyOf"):
            for branch in es.get(comb, []):
                eff, bscope = self._effective(branch, scope)
                if eff is None:
                    continue
                cand = _shallow_merge_schemas(base, eff)
                try:
                    if valid(self._validator_at(cand, bscope), value):
                        return cand
                except Exception:
                    continue
        return None

    def _record(self, desc, op, path, key=None, value=None):
        self.recorded.append({"desc": desc, "op": op, "path": list(path), "key": key,
                              "value": value})

    def _mutate_here(self, es, value, path):
        # (g1) drop a locally-required key
        if isinstance(value, dict):
            for req in es.get("required", []):
                if req in value:
                    self._record(f"dropping locally-required '{req}'", "del", path, key=req)
            # (g4) unknown key where local additionalProperties is false
            if es.get("additionalProperties") is False:
                self._record("injecting unknown key", "add", path,
                             key="___fuzz_unknown_key___", value="x")
        # (g2) enum/const violation
        if "enum" in es:
            self._record("out-of-vocabulary enum value", "set", path, value="___fuzz_invalid_enum___")
        if "const" in es:
            poison = "___fuzz___" if es["const"] != "___fuzz___" else 42
            self._record("const violation", "set", path, value=poison)
        # (g3) wrong-type where a local type is declared — one mutation per mismatching JSON
        # type family (a `type: string` must reject numbers, objects, arrays, booleans, null)
        declared = es.get("type")
        declared = [declared] if isinstance(declared, str) else declared
        if declared:
            for poison in _POISONS:
                if not any(_TYPE_CHECKS.get(t, lambda v: True)(poison) for t in declared):
                    got = next(t for t, chk in _TYPE_CHECKS.items() if chk(poison))
                    self._record(f"wrong-typing (declared {'/'.join(declared)}, poisoned with {got})",
                                 "set", path, value=poison)
        # (g5) boundary violations — only where the local constraint exists
        if isinstance(value, list) and isinstance(es.get("minItems"), int) and es["minItems"] >= 1 \
                and len(value) >= es["minItems"]:
            self._record(f"minItems-1 ({es['minItems'] - 1} items)", "set", path,
                         value=value[: es["minItems"] - 1])
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if isinstance(es.get("minimum"), (int, float)):
                self._record("minimum-1", "set", path, value=es["minimum"] - 1)
            if isinstance(es.get("exclusiveMinimum"), (int, float)):
                self._record("exclusiveMinimum boundary", "set", path, value=es["exclusiveMinimum"])
            if isinstance(es.get("maximum"), (int, float)):
                self._record("maximum+1", "set", path, value=es["maximum"] + 1)
        if isinstance(value, str):
            if isinstance(es.get("maxLength"), int):
                self._record("maxLength+1", "set", path, value="x" * (es["maxLength"] + 1))
            if isinstance(es.get("minLength"), int) and es["minLength"] >= 1:
                self._record("minLength-1", "set", path, value="x" * (es["minLength"] - 1))
            if "pattern" in es:
                for breaker in _PATTERN_BREAKERS:
                    try:
                        if not re.search(es["pattern"], breaker):
                            self._record("pattern-breaking string", "set", path, value=breaker)
                            break
                    except re.error:
                        break

    # -- evaluation -------------------------------------------------------------------
    def _apply(self, m):
        if m["op"] == "set" and not m["path"]:
            return copy.deepcopy(m["value"])
        root = copy.deepcopy(self.instance)
        tgt = root
        for p in (m["path"][:-1] if m["op"] == "set" else m["path"]):
            tgt = tgt[p]
        if m["op"] == "set":
            tgt[m["path"][-1]] = copy.deepcopy(m["value"])
        elif m["op"] == "del":
            del tgt[m["key"]]
        else:  # add
            tgt[m["key"]] = m["value"]
        return root

    def evaluate(self):
        for m in self.recorded:
            mutated = self._apply(m)
            self.mutations += 1
            if valid(self.validator, mutated):
                loc = "/".join(str(p) for p in m["path"]) or "(root)"
                self.findings.append(f"{self.rt}: {m['desc']} at {loc} still validates — "
                                     f"over-permissive at that path")


def _shallow_merge_schemas(base, overlay):
    """Module-level twin of Synthesizer._shallow_merge, for the deep walk (union required,
    merge properties, overlay the rest)."""
    out = dict(base)
    for k, v in overlay.items():
        if k == "required" and k in out:
            out[k] = sorted(set(out[k]) | set(v))
        elif k == "properties" and k in out:
            out[k] = {**out[k], **v}
        else:
            out[k] = v
    return out


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

    # (g) deep mutation co-walk — every reachable path, against its LOCAL subschema. Walks the
    # minimal instance recursively enriched with every optional property that still validates,
    # so optional/recursive subtrees are covered.
    walker = DeepWalker(rt, spec, validator, path.as_uri(), copy.deepcopy(instance))
    try:
        enriched = walker.enrich(synth)
        walker.walk(spec, enriched, [], path.as_uri())
        walker.evaluate()
    except RecursionError:
        errors.append(f"{rt}: deep walk exceeded recursion limits — check for an unguarded recursive $ref")
    mutations += walker.mutations
    errors.extend(walker.findings)

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
