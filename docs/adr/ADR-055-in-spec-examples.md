# UDLM ADR-055: Worked examples live in the spec — adopt the JSON Schema / OpenAPI `examples` keyword

**Status:** Proposed (croadfeldt upstream) — 0.1 work; 1.0 conferred by engineering acceptance
(#217); decided 2026-07-28
**Date:** 2026-07-28
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited
once with what it settles. Rule-36 (`registry/type-base-standard.md` — every type ships a worked
example) — the requirement this makes concrete; its `G4` example-currency gate has stood **deferred
"pending the D8 example-bar ruling"**, which this closes. ADR-051 (identity = a spec's normative
bytes; the digest and the publish law) — this adds one non-normative surface it must exclude.
The spec-completeness gate (`registry/tools/spec_coverage.py`, rule-36 story) — its `examples` leg
now resolves here.

## Context

Rule-36 has always said a type ships with a worked example, but never said **where the example
lives** — so `G4` (is the example current?) was parked pending a "D8 example-bar" ruling, and in
practice examples scattered: some inline-absent, some only in external `registry/instances/`
fixtures, some as composite catalog-item constituents that aren't standalone instances of the type
at all. An example that lives away from its spec drifts from it silently, and there was no gate to
catch a stale one. The question is the standard one every schema ecosystem has already answered:
where does a worked example go, and how is it kept honest?

## Decision

**Adopt the JSON Schema / OpenAPI 3.1 `examples` convention by reference (tenet T5), unchanged.**
The industry answer is uniform — the example lives **in the spec, co-located with the schema, and is
validated against that schema in CI**:

1. **The example lives at `spec.examples`** — the JSON Schema `examples` keyword (an array), a sibling
   of `spec.properties`, inside the very schema it illustrates. Not a side instance file, not prose,
   not a catalog constituent. One home, the same for every resource type.
2. **Every spec carries at least one** (rule-36 made concrete). Enforced by `EXG-002` with a
   burn-down baseline: new specs get no grace; the existing gap shrinks and never regresses.
3. **Every in-spec example must validate against its own `spec` schema** — `EXG-001`, a hard gate with
   no baseline, ever. This is Spectral's `oas3-valid-schema-example` rule, UDLM-side: a rotted example
   is worse than none. Together `EXG-001`+`EXG-002` **close the deferred D8 / G4 ruling** — the
   example bar is "a schema-valid example in the spec, CI keeps it current."
4. **`spec.examples` is non-normative, so it is excluded from the identity digest** (ADR-051
   `IDENTITY_EXCLUDED_FIELDS` / `_strip_nonnormative`). JSON Schema defines `examples` as an
   annotation with **no effect on validation** — a worked example illustrates the contract, it is not
   the contract. Refreshing an example is therefore digest-invariant: no version bump, no manifest
   churn. (Same treatment, same reason, as `coverage` — the other documentation surface.)

**External-only worked examples collapse back into the spec** and are validated there; the spec is the
canonical home. Existing fixtures that serve other roles (reference-data layers, tenants, composite
catalog items) stay — they are not a type's worked example.

## The standards, and what each settles here

| Standard | The rule it contributes | Realized here as |
|---|---|---|
| JSON Schema 2020-12 | `examples` is an array annotation on a schema, not validated by the schema itself and with no effect on validation | `spec.examples`; excluded from the identity digest (Decision 4) |
| OpenAPI 3.1 | Examples are co-located with the schema/media they illustrate — inline, never a side file | Decision 1 (in-spec, one home) |
| Spectral (`oas3-valid-schema-example`) | An in-spec example is linted against its own schema in CI; a non-conforming example fails the build | `EXG-001`, `tests/check_spec_examples.py` |

## Data · Policy · Provider

- **Data (UDLM):** the `spec.examples` location, the two gate rules, and the identity exclusion — the
  portable, checkable shape. One authoritative example per type; edge cases welcome as further array
  entries.
- **Policy (DCM):** a profile may raise the bar (e.g. require a negative/edge example alongside the
  happy path) — the floor is one valid example; profiles ratchet up.
- **Provider:** unaffected — examples are authoring-side documentation, never part of naturalization.

## Consequences

Rule-36's example clause is now enforceable, not aspirational; the parked D8/G4 ruling is closed; and
the spec-completeness gate's `examples` leg resolves against `spec.examples` (self-contained, no
side-file bookkeeping). The 48 specs without an example are baselined and burn down family-by-family;
each in-spec example is CI-validated the day it lands and every day after.
