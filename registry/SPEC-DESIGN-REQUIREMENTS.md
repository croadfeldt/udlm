# UDLM Spec Design Requirements

The rubric every UDLM **Resource Type Specification** is designed to. **Hard constraints** are
normative (MUST); those marked **[enforced]** are checked by `tools/validate.py` /
`tools/compat-check.py` and should run in CI. **Design principles** are review discipline (SHOULD).
Each hard constraint cites the UDLM contract it derives from.

## Hard constraints (MUST)

### Format & validity
1. **JSON Schema 2020-12** is the normative model — the format for all entity-type definitions
   (`contracts/schema-sharing.md`).
2. Authorable in **JSON or YAML**, 1:1 — same document, same meta-schema. **[enforced]**
3. **Valid-by-construction** — validates against `resource-type-spec.schema.json` or it is not a
   conformant spec. **[enforced]**
4. **Structural schema** — every field typed, `additionalProperties` controlled; no untyped blobs.

### Identity & naming
5. **UUIDv4** identity, immutable for the type's life; Handles are mutable/rebindable, References are
   typed cross-doc pointers (`contracts/identifier-scheme.md`). **[enforced: format]**
6. **Vendor-neutral `Category.Type` name**, e.g. `Compute.VirtualMachine`
   (`entities/resource-type-hierarchy.md`). **[enforced: pattern]**

### Versioning — two axes
7. **`conformsTo: udlm/<MAJOR.MINOR>`** — SPEC-axis binding (apiVersion); same MAJOR = wire-compatible
   (`CONFORMANCE.md` §9). **[enforced: pattern]**
8. **`version: MAJOR.MINOR.REVISION`** — ENTITY axis; immutable once published; any change publishes a
   new version (`foundations/layering-and-versioning.md`). **[enforced: pattern]**
9. **Semver semantics**: additive → MINOR, breaking → MAJOR, docs → REVISION. **[enforced: compat-check]**
10. A **MAJOR** bump deprecates the predecessor and MUST carry `migration_guidance`; a deprecation
    window precedes retirement (universal deprecation model + K8s deprecation policy).
11. **Version-pinned references** — profiles (E1) and realized instances (E5) pin the exact version used.

### Lifecycle & ownership
12. Conforms to the **four states** Intent → Requested → Realized → Discovered (`foundations/four-states.md`).
13. **`spec` = desired state** (Intent/Requested, consumer-authored); **`outputs` = observed state**
    (Realized/Discovered, provider-authored). Never blurred (the K8s spec/status discipline).
14. **Realization is the authoritative system of record** for realized data — the basis of sovereignty
    and audit (`entities/resource-service-entities.md`).

### Portability & provider-neutrality
15. The spec is the contract **any** provider of the type MUST satisfy; providers
    naturalize → realize → denaturalize (`contracts/provider-contract.md`).
16. **Any deviation from full portability MUST be explicitly declared** via `portability`. **[enforced: enum]**
17. No provider-specific fields in the universal spec — those ride declared extension points.

### Relationships
18. Relationships are **first-class and typed** (`depends_on`/`binds_to`/`references`/`contained_by`),
    target **resource types** (never provider-specific refs), and form **acyclic** composite DAGs
    (`entities/service-dependencies.md`, `entities/composite-service-model.md`). **[enforced: shape]**

### Interop & data discipline
19. **Wire-compatible** — any conformant peer can deserialize, scope-resolve, reference, and validate
    it; independent extensions stay interoperable via the schema-sharing protocol
    (`contracts/identifier-scheme.md`, `contracts/schema-sharing.md`).
20. **Data, not logic** — a spec carries values + declarative constraints; *executable* rules are
    Policy, *static* values are Layers (`foundations/layering-and-versioning.md` §1a).
21. **No embedded expressions** — a spec carries *declarative* constraints only (JSON Schema
    `if/then` · `dependentSchemas` · `enum` · bounds + markers like `createOnly`); it embeds **no**
    expression language or executable behavior. Transformation/enrichment is Policy, applied by DCM;
    the contract layer stays deterministic + reproducible (`design-principles/core-tenets.md` T2/T3).

### Adopted standards — provenance & licensing
22. **Source provenance** — every type or field whose vocabulary is **adopted** from an external
    standard (the *adopt* disposition, `design-principles/adopted-standards.md`) MUST record the
    source: the standard's name, version/edition, and canonical URL, in the `adopts[]` reference
    (`registry/provider-adopted-standards.schema.json`) or a field-level `x-standard` pointer. A
    definition that borrows elements with no recorded source is invalid.
23. **License compatibility** — before adopting, the source's license MUST be checked against the
    UDLM project license (Apache-2.0) and the verdict recorded with the source. **Referencing** a
    standard's *vocabulary* (field/element names — facts, not copyrightable) is always permitted,
    whatever the source license. **Copying** a source's schema text, enum bodies, or normative prose
    into the UDLM tree (an *absorb*) is permitted ONLY from an Apache-2.0-compatible license;
    copyleft / file-scoped sources (GPL, LGPL, MPL) MAY be **referenced by name** but their text or
    files MUST NOT be vendored into UDLM (`governance/registry-governance.md`, IP hygiene). This is
    why the disposition default is *adopt-by-reference*: it is both schema-rev-decoupled **and**
    license-clean.

## Design principles (SHOULD)
- **Minimal core, extensible at the edges** — don't over-model; add types via schema-sharing.
- **Decouple the model from any runtime/controller** — the model outlives the engine that realizes it.
- **Typed outputs are the only cross-entity binding surface** (E2); flag `sensitive` outputs.
- **Profiles narrow, never widen** the base contract (E1).
- **Field-level provenance** — every assembled field records the layer/policy that set it (E4).
- **Reproducible** — spec + inputs deterministically yields the same Requested/effective state.
- **One concept per field**; cross-field/conditional constraints expressed **declaratively** in JSON
  Schema (`if`/`then`, `dependentSchemas`, `enum`), never an embedded expression language. Cross-entity
  data flow is a declarative typed binding (`targetField` → output); any real transformation/computation
  is **Policy**, applied by DCM — never in the spec (T2/T4).

---
_E1–E5 reference the enhancement opportunities surfaced from dcm-project/enhancements#55
(constraint profiles, typed outputs, conditional constraints, layered-overlay provenance,
instance↔version pinning). This rubric will tighten as the standards survey + OSAC research land._
