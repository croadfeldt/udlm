#!/usr/bin/env python3
"""Composition hammer: the catalog-item semantic checks proven against GENERATED graphs.

registry/tools/validate.py carries the cross-field checks JSON Schema cannot express
(check_catalog_item: component_id uniqueness, sibling depends_on/binding resolution, cycle
rejection, binding⊆depends_on ordering, and (e) binding-output type-safety against the
producer type's declared outputs). This hammer imports validate.py as a module and drives
those checks with constituent graphs generated in memory from the registry — adversarial
graphs that MUST error, and legal producer→consumer pairs over every REAL declared output
that MUST pass clean. No fixtures on disk; deterministic only.

  ADVERSARIAL (must error, with the expected message)
    (a) a binding to an output the producer's resource_type does not declare
    (b) a binding whose from_component is missing from depends_on
    (c) dependency cycles — 2-node and 3-node
    (d) a depends_on / from_component naming no sibling constituent
  LEGAL (must pass schema + semantic checks clean)
    (e) for EVERY registry type with >=1 declared output: a two-constituent item binding
        the type's first output into a consumer — the whole real binding surface, exercised

Also emitted (informational, never fails): the types with ZERO declared outputs — nothing
can ever bind to them, the thin-outputs surface of the registry.

Exit non-zero on any adversarial graph accepted or any legal graph rejected. Wire into CI.
"""
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

spec = importlib.util.spec_from_file_location("udlm_validate", ROOT / "registry" / "tools" / "validate.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)


def det_uuid(n: int) -> str:
    """Deterministic RFC 9562 v4-shaped uuid for generated records (version nibble 4,
    variant 8) — no randomness, stable across runs."""
    return f"00000000-0000-4000-8000-{n:012x}"


def item(constituents, n=0):
    """A schema-valid catalog item around the generated constituent graph."""
    return {
        "record_type": "catalog_item",
        "uuid": det_uuid(n),
        "handle": "cexample/catalog/composition-hammer",
        "conforms_to": "udlm/0.1",
        "name": "CompositionHammer.Generated",
        "version": "1.0.0",
        "tenant_uuid": det_uuid(999999),
        "constituents": constituents,
    }


def constituent(cid, rtype="Compute.Container", depends_on=(), bindings=()):
    c = {
        "component_id": cid,
        "resource_type": rtype,
        "provided_by": "self",
        "failure_effect": "required",
    }
    if depends_on:
        c["depends_on"] = list(depends_on)
    if bindings:
        c["bindings"] = list(bindings)
    return c


def binding(src, output, to_field="spec.injected_input"):
    return {"from_component": src, "output": output, "to_field": to_field}


def run(doc):
    """(schema_errors, semantic_errors) for a generated item — schema first, exactly like
    validate.py's dispatch (semantic checks run only on schema-valid documents)."""
    schema_errors = [e.message for e in V.CATALOG_VALIDATOR.iter_errors(doc)]
    semantic = V.check_catalog_item(doc) if not schema_errors else []
    return schema_errors, semantic


def main():
    failures, graphs = [], 0
    outputs_index = V._type_outputs_index()

    def expect_error(label, doc, needle):
        nonlocal graphs
        graphs += 1
        schema_errors, semantic = run(doc)
        if schema_errors:
            failures.append(f"{label}: generated graph is schema-invalid (hammer bug, not a "
                            f"finding): {schema_errors[0]}")
            return
        if not any(needle in msg for msg in semantic):
            failures.append(f"{label}: expected an error containing {needle!r}, got "
                            f"{semantic or ['(accepted clean)']}")

    def expect_clean(label, doc):
        nonlocal graphs
        graphs += 1
        schema_errors, semantic = run(doc)
        for msg in schema_errors[:3]:
            failures.append(f"{label}: legal graph rejected by the schema — {msg}")
        for msg in semantic:
            failures.append(f"{label}: legal graph rejected by semantic checks — {msg}")

    # a real producer type with a known first output, for the adversarial graphs
    producer_type = "Compute.Container"
    real_output = sorted(outputs_index[producer_type])[0] if outputs_index.get(producer_type) else "endpoint"

    # (a) binding to an undeclared output of a known type -> must error
    expect_error(
        "(a) undeclared output",
        item([constituent("producer", producer_type),
              constituent("consumer", depends_on=["producer"],
                          bindings=[binding("producer", "___not_a_declared_output___")])], 1),
        "is not a declared output")

    # (b) binding whose from_component is missing from depends_on -> must error
    expect_error(
        "(b) binding outside depends_on",
        item([constituent("producer", producer_type),
              constituent("consumer",
                          bindings=[binding("producer", real_output)])], 2),
        "missing from depends_on")

    # (c) dependency cycles -> must error (2-node and 3-node)
    expect_error(
        "(c) 2-node cycle",
        item([constituent("a", depends_on=["b"]),
              constituent("b", depends_on=["a"])], 3),
        "cycle")
    expect_error(
        "(c) 3-node cycle",
        item([constituent("a", depends_on=["b"]),
              constituent("b", depends_on=["c"]),
              constituent("c", depends_on=["a"])], 4),
        "cycle")

    # (d) unknown sibling reference -> must error (depends_on and from_component forms)
    expect_error(
        "(d) unknown depends_on sibling",
        item([constituent("only", depends_on=["ghost"])], 5),
        "does not resolve to a sibling")
    expect_error(
        "(d) unknown binding sibling",
        item([constituent("producer", producer_type),
              constituent("consumer", depends_on=["producer"],
                          bindings=[binding("ghost", real_output)])], 6),
        "does not resolve to a sibling")

    # duplicate component_id -> must error (the uniqueness leg of the same check set)
    expect_error(
        "(a') duplicate component_id",
        item([constituent("twin"), constituent("twin")], 7),
        "duplicate component_id")

    # (e) LEGAL: for every registry type with >=1 output, a two-constituent item binding its
    # first declared output -> must pass schema + semantic checks clean
    n = 100
    with_outputs = {rt: outs for rt, outs in sorted(outputs_index.items()) if outs}
    for rt, outs in with_outputs.items():
        first = sorted(outs)[0]
        expect_clean(
            f"(e) legal pair over {rt}.{first}",
            item([constituent("producer", rt),
                  constituent("consumer", rt, depends_on=["producer"],
                              bindings=[binding("producer", first)])], n))
        n += 1

    zero_output = sorted(rt for rt, outs in outputs_index.items() if not outs)
    print(f"hammered {graphs} generated catalog graphs "
          f"({len(with_outputs)} legal producer→consumer pairs over real declared outputs)")
    print(f"thin-outputs surface — {len(zero_output)} type(s) with ZERO declared outputs, "
          f"nothing can ever bind to them (informational):")
    for rt in zero_output:
        print(f"  {rt}")

    if failures:
        print(f"\nFAIL — {len(failures)} finding(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("\nOK — every adversarial graph rejected with the expected error; every legal pair clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
