#!/usr/bin/env python3
"""Spec-example gate (ADR-055 — examples live in the spec, JSON Schema / OpenAPI 3.1 convention):
every resource-type spec carries at least one worked example under `spec.examples`, and every such
example VALIDATES against its own `spec` schema.

Two rules, two strengths — the industry pattern (Spectral `oas3-valid-schema-example`):

  EXG-001  an in-spec example that does NOT validate against its `spec` schema   -> HARD FAIL always.
           An example that has rotted out of conformance is worse than none; no baseline, ever.
  EXG-002  a resource-type spec with no `spec.examples` (or an empty one)         -> FAIL, unless the
           spec is in the burn-down baseline (tests/spec_examples_baseline.txt). New specs get no
           grace; the baseline only shrinks (a spec that gains an example is dropped from it, and
           the gate refuses to re-add one — presence never regresses).

`spec.examples` is the JSON Schema `examples` keyword inside the `spec` schema, so an example sits in
the document it illustrates and is checked against that same schema. Run with --check in CI.
"""
import glob
import json
import os
import pathlib
import sys

import yaml
from jsonschema import Draft202012Validator, RefResolver

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(ROOT, "tests", "spec_examples_baseline.txt")
META_BASELINE = os.path.join(ROOT, "tests", "meta_schema_examples_baseline.txt")


def load(p):
    t = open(p, encoding="utf-8").read()
    return (yaml.safe_load(t) if p.endswith((".yaml", ".yml")) else json.loads(t)) or {}


def _build_store():
    """Offline $ref store: every registry/*.schema.json under both its file URI (what a relative
    ../../common-elements.schema.json ref resolves to) and its $id — so an example that exercises a
    shared-schema $ref resolves deterministically without the network (the same STORE the fuzz gate
    uses)."""
    store = {}
    for p in sorted(glob.glob(os.path.join(ROOT, "registry", "*.schema.json"))):
        doc = json.loads(open(p, encoding="utf-8").read())
        store[pathlib.Path(p).resolve().as_uri()] = doc
        if isinstance(doc.get("$id"), str):
            store[doc["$id"]] = doc
        store[f"https://udlm.dev/registry/{os.path.basename(p)}"] = doc
    return store


STORE = _build_store()


def _validator_for(spec, spec_path):
    """A Draft2020-12 validator whose $refs resolve relative to the spec file (base_uri) against the
    local STORE — without this a common-elements $ref raises Unresolvable and aborts the run."""
    resolver = RefResolver(base_uri=pathlib.Path(spec_path).resolve().as_uri(),
                           referrer=spec, store=STORE)
    return Draft202012Validator(spec, resolver=resolver)


def resource_type_specs():
    out = []
    roots = [os.path.join(ROOT, "registry", "resource-types", "**", "*"),
             os.path.join(ROOT, "registry", "generated", "*")]
    for p in [q for pat in roots for q in glob.glob(pat, recursive=True)]:
        if p.endswith((".json", ".yaml", ".yml")):
            d = load(p)
            if d.get("resource_type") and "record_type" not in d and isinstance(d.get("spec"), dict):
                out.append((d["resource_type"], d, p))
    return sorted(out, key=lambda r: r[0])


def read_baseline(path=None):
    path = path or BASELINE
    if not os.path.isfile(path):
        return set()
    return {ln.strip() for ln in open(path, encoding="utf-8")
            if ln.strip() and not ln.startswith("#")}


def meta_schemas():
    """The registry meta-schemas (ADR-055 addendum): each may carry whole-artifact examples in
    its ROOT `examples` array — validated against the schema itself, same EXG rules."""
    out = []
    for p in sorted(glob.glob(os.path.join(ROOT, "registry", "*.schema.json"))):
        out.append((os.path.basename(p), json.loads(open(p, encoding="utf-8").read()), p))
    return out


def check_meta_schemas(fails):
    """ADR-055 addendum arm: EXG-001 (a root example must validate against its own schema — hard,
    no baseline) + EXG-002 (a meta-schema without a root example is baselined; the list only
    shrinks; new schemas ship one)."""
    baseline = read_baseline(META_BASELINE)
    missing_now = []
    for name, doc, path in meta_schemas():
        examples = doc.get("examples")
        if not examples:
            missing_now.append(name)
            if name not in baseline:
                fails.append(f"EXG-002 {name}: no root `examples` — a meta-schema ships its "
                             f"whole-artifact example inline (ADR-055 addendum)")
            continue
        validator = _validator_for(doc, path)
        for i, ex in enumerate(examples):
            for err in validator.iter_errors(ex):
                loc = "/".join(str(x) for x in err.path) or "(root)"
                fails.append(f"EXG-001 {name} examples[{i}] at {loc}: {err.message} — a "
                             f"meta-schema example must validate against its own schema")
    for name in sorted(baseline - set(missing_now)):
        fails.append(f"EXG-002 {name}: listed in meta_schema_examples_baseline.txt but now has "
                     f"an example — remove it (presence never regresses)")
    return len(meta_schemas()) - len(missing_now), len(meta_schemas()), len(missing_now), len(baseline)


def main():
    baseline = read_baseline()
    fails, missing_now = [], []
    for rt, doc, path in resource_type_specs():
        spec = doc["spec"]
        examples = spec.get("examples")
        if not examples:
            missing_now.append(rt)
            if rt not in baseline:
                fails.append(f"EXG-002 {rt}: no `spec.examples` — every spec ships a worked example "
                             f"(ADR-055); add one under spec.examples (validated against this spec)")
            continue
        validator = _validator_for(spec, path)
        for i, ex in enumerate(examples):
            for err in validator.iter_errors(ex):
                loc = "/".join(str(x) for x in err.path) or "(root)"
                fails.append(f"EXG-001 {rt} example[{i}] at {loc}: {err.message} — an in-spec example "
                             f"must validate against its own spec schema")

    # burn-down: the baseline may only shrink. A spec that now HAS an example must not be listed.
    stale = sorted(baseline - set(missing_now))
    for rt in stale:
        fails.append(f"EXG-002 {rt}: listed in spec_examples_baseline.txt but now has an example — "
                     f"remove it from the baseline (presence never regresses)")

    m_covered, m_total, m_missing, m_baselined = check_meta_schemas(fails)

    covered = sum(1 for rt, _, _ in resource_type_specs() if rt not in missing_now)
    total = len(resource_type_specs())
    for f in fails:
        print("FAIL [" + f)
    print(f"{covered}/{total} resource-type spec(s) carry a validated example; "
          f"{len(missing_now)} missing ({len(baseline)} baselined).")
    print(f"{m_covered}/{m_total} meta-schema(s) carry a validated whole-artifact example; "
          f"{m_missing} missing ({m_baselined} baselined).")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
