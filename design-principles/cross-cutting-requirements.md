# UDLM Design Principles — Cross-Cutting Requirements

UDLM is a **substrate**, not just a schema. Beyond the four-state lifecycle, every Resource Type
Specification and every conformant realization must serve a set of cross-cutting requirements that
DCM — the canonical operationalizer — holds as **hard** requirements: **auditability, observability,
an explicit dependency graph, and sovereignty.** These are design principles, not options; they
shape how specs are authored and how providers realize them.

This sits alongside the existing foundational requirements — the four-state lifecycle
(`foundations/four-states.md`), layering & versioning (`foundations/layering-and-versioning.md`),
the provider/policy contracts, and the per-entity authoring rubric
(`registry/SPEC-DESIGN-REQUIREMENTS.md`).

---

## P0 — Lifecycle is the spine *(existing)*
The four states **Intent → Requested → Realized → Discovered** are distinct, typed, immutable
records — never collapsed into one reconciled object. Every principle below hangs off this: audit
chains the transitions, observability compares Discovered against Requested, the dependency graph
orders realization, and sovereignty governs where each state may live. (`foundations/four-states.md`)

## P1 — Auditability by construction
**DCM requirement:** `AUD-001` (every modification produces a synchronous Commit Log entry *before*
success; a write failure aborts — no silent unaudited change), `AUD-002` (append-only, immutable
while retention is live), a tamper-evident **Merkle hash-chain** (RFC 9162 / CT v2.0), and audit
records that **survive at least as long as any referenced resource**.

- **Reproducible validation.** Every artifact pins the exact type-version it validated against — the
  JSON Schema `$id` encodes both version axes — and there is **no runtime late-binding**
  (`$dynamicRef` is forbidden). A record must be re-validatable years later against the same contract.
- **Field-level provenance.** Every assembled field records the layer / policy / actor / provider
  that set it — the *same* per-field provenance DCM's audit chain consumes (see G3).
- **Interpretability across retention.** Tombstones (`supersededBy`): never delete a field within a
  major version, so historical Realized/Discovered records stay interpretable for their full
  retention lifetime.
- **Change-by-replacement.** `createOnly`/immutable fields force replace → supersession, recorded as
  a new entity in the chain rather than an in-place mutation.

## P2 — Observability as a base obligation
**DCM requirement:** provider-contract **§7** — observability (metrics, logs, telemetry) is a *base*
provider obligation; DCM MAY be the authoritative telemetry arbiter; observed dependencies are
**provider-introspected, post-realization**.

- **Declared vs observed.** Relationships and outputs are declared in the spec so DCM can reconcile
  the provider-introspected reality against the declared contract — drift on **data and topology**.
- **Typed, not opaque.** Realized/observed signals are schema-typed outputs, never an opaque `status`.
- **Offline-capable.** Output/telemetry schemas resolve offline (bundling, P4) for disconnected sites.

## P3 — Explicit, typed dependency graph
**DCM requirement:** `RDG-001` — the realization MUST validate the dependency graph is a **DAG**
before acknowledging; circular dependencies are rejected (422); rehydration runs in dependency
order, compensation in reverse.

- **Edges are first-class, typed, and version-pinned.** Reference a target by versioned `$id` +
  `targetField` (a specific realized output), never by bare name or provider-specific ref.
- **M:N, cross-scope.** Support real topologies — including edges that cross tenant/sovereignty
  scope, so they are visible and governable rather than hidden.
- **Integrity propagation.** Maturity/stability propagates across edges — a stable entity may not
  depend on an alpha one.
- **Acyclic, validated at submission** — not discovered at realization time.

## P4 — Sovereignty is structural, not advisory
**DCM requirement:** the **Governance Matrix** unifies authorization, sovereignty, and data-boundary
control into one substrate; *"scoring cannot be used to route around data sovereignty or regulatory
boundaries"*; sovereignty zones + data classifications (sovereign / classified / PHI) are **hard**
boundaries.

- **Immutable sovereignty fields.** `sovereignty_zone` / `data_classification` / jurisdiction are
  `createOnly` — a realized entity **cannot silently leave its zone**; any change forces replace +
  re-evaluation through the Matrix.
- **Offline closure.** A type's full dependency closure bundles into one self-contained artifact
  (JSON Schema Compound Document) so **air-gapped / sovereign providers validate and rehydrate
  without phoning home.**
- **No central runtime.** Validation, conversion, conflict-detection, and cascade are **evaluable
  data** any host runs offline — never a dependency on a reachable central authority.
- **Boundary-crossing is visible.** Cross-scope edges (P3) make any dependency that crosses a
  sovereignty boundary explicit and enforceable by the Matrix.

---

## Cross-cutting guardrails

- **G1 — Data, not logic; decouple from runtime.** A spec carries values + declarative constraints;
  *executable* rules are Policy, *static* values are Layers. Conversion, validation, defaulting, and
  cascade are expressed as evaluable data, **never as a required running controller** (the dominant
  Kubernetes anti-pattern). The model outlives the engine that realizes it.
- **G2 — No embedded expressions; the contract layer is deterministic.** The portable data model
  carries **no embedded expression language** — determinism and reproducibility are *structural*, not
  policed (a single impure expression would break tamper-evident audit `AUD-002` and sovereignty P4).
  Definition and validation use only *declarative* constructs (JSON Schema `if/then` ·
  `dependentSchemas` · `enum` · bounds + markers like `createOnly`); **transformation/enrichment is
  Policy, applied by DCM** and recorded in the audit log (`core-tenets.md` T2/T3).
- **G3 — Contract, not parallel implementation.** UDLM defines the *data contract* for provenance,
  dependencies, and policy inputs; **DCM operationalizes it** (the Merkle audit log, the DAG engine,
  the Governance Matrix). One model — never a competing UDLM-side implementation.
- **G4 — Universal definitions.** Entity-type families *organize*; they do not *bound*. Definitions
  are free to use across realizations (`foundations/entity-type-families.md`).

## Enforcement
Per-entity: valid-by-construction (meta-schema) + `compat-check` (versioning) gate the authoring
rubric. Cross-cutting: partly tooling (e.g. forbid `$dynamicRef`; `createOnly` change ⇒ major;
hermetic-expression check) and partly provider conformance + review (`CONFORMANCE.md`).
