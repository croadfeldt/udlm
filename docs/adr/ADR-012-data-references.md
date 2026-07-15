# UDLM ADR-012: Data references — the object-reference shape for shared data

**Status:** Proposed
**Date:** 2026-07-14
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `foundations/layering-and-versioning.md` §3.7 (Reference Data Layers — the shared, governed datasets a reference points at; DCM ADR-012 is the assembly model); ADR-008 (the UDLM/DCM boundary this decision splits along); `docs/research/minimal-custom-surface-and-graph-resilience.md` findings #1/#2 (uid-authoritative + advisory-name; deterministic invalid-edge detection — the direct grounding); `registry/layer.schema.json` + `registry/data-reference.schema.json` (the shapes this fixes); `registry/tools/validate.py` `check_data_references` (the enforcement).

## Context

Two things already exist: **layers** compose a payload base→overlay (a standard base plus per-data-center/rack/segment deviations — `intermediate` layers, §3.4), and **Reference Data Layers** (§3.7) hold shared, governed, versioned datasets (`network_zone`, `os_image`, `vm_size`, `location`, …) that many records draw from. What was missing was the **in-field reference shape**: how a field says "use *that* governed dataset" instead of inlining a copy. Inlining drifts; a name-keyed pointer silently rebinds when a name is reused. This settles the shape and its integrity.

## Decision

### 1. A data reference is an object: `{ ref_uuid, ref_name?, reference_data_type? }`

Modelled on the Kubernetes ObjectReference / ownerReference idiom. **`ref_uuid` is authoritative** — resolution uses only the uuid. **`ref_name` is advisory** — human-readable, carried for legibility, never the resolution key. `reference_data_type` is the kind the reference expects. This is finding #1 applied verbatim: uid authoritative, name advisory, a stale uid is a *dangling* reference, never a silent rebind onto a same-named record. Shape: `registry/data-reference.schema.json` (`$defs/data_reference`).

### 2. A reference resolves to an active reference-data layer of the matching type

A data reference MUST resolve to an **active** `layer` with `layer_type: reference_data` whose `reference_data_type` **equals** the reference's declared `reference_data_type`. The type is a real match axis — it stops a field from binding a `network_zone` where an `os_image` was meant. `reference_data_type` is now a first-class field on the layer record, required for reference-data layers (`layer.schema.json`).

### 3. Integrity is enforced deterministically — invalid edges fail, never linger

`check_data_references` (`validate.py`) scans every record for embedded references and fails on: a dangling `ref_uuid` (resolves to nothing), a target that is not an active reference-data layer, a `reference_data_type` mismatch, or an advisory `ref_name` that has drifted from the resolved target. A wrong advisory name is a hard failure, not a warning — resolution uses the uuid, but the recorded name must stay honest (an authoring honesty gate). This is finding #2: constrain the reference topology and machine-detect invalid edges deterministically, rather than letting them resolve silently.

### 4. Boundary (ADR-008)

The reference **shape**, the resolve-to-matching-reference-data-layer **rule**, and the integrity constraints are **UDLM** — a peer reads and resolves them identically (resolution is deterministic given the data). **DCM's assembly engine** does the runtime work: injecting the resolved dataset into the assembled payload at render time (§3.7 — reference data is looked up and injected, not merged like an overlay).

### 5. Where it applies — layer fields now, provider capability next

A field in any layer's `fields` may be a data reference today. The same shape is the intended home for the provider capability blocks (e.g. a shared `topology_capability` becomes a `reference_data_type: topology_capability` layer that a provider capability references by `{ref_uuid, ref_name}` instead of inlining) — deferred until the provider schema lands its sovereignty changes (PR #83) so the two do not collide.

### 6. Referenced entities are immutable; lineage is a single, explicit mechanism

A referenced entity is config like any other, so it is **immutable**: any change mints a **new record (new `uuid` + new `version`)** and never edits the old one (the decision-record "never edit, supersede" discipline). Because `ref_uuid` targets a specific record, a reference pins an **exact, reproducible, immutable version** — and an existing reference to an older version stays valid forever (only a **retired** target is refused; a merely superseded one is not — it is surfaced, not broken).

**Lineage is explicit — one mechanism, no second.** A new version declares `supersedes: [uuid, …]`, the uuid(s) it replaces (absent = a lineage root). This is the *only* lineage source; `handle` is advisory display and is never consulted for lineage. Change-impact is derived from this DAG plus the reverse reference index: `impact_report()` prints, advisory (never failing), every reference pinned to a version that has since been superseded — e.g. *a library embedded in a container image that references it, after the library is bumped*. Lineage integrity is enforced: each `supersedes` uuid must resolve to a reference-data layer of the same `reference_data_type` with a strictly lower version.

**Why explicit, not emergent.** Emergent lineage (group by `handle`, order by `version`) is tempting — zero authoring burden — but it is **structurally incomplete**: it cannot express a fork (one version splits into two), a merge (two collapse into one), or a rename (the `handle` changes), and it *mis*-chains silently on handle reuse (the advisory-axis risk this model already refused for resolution, finding #1). A mechanism with permanent holes cannot be *the* mechanism, and running it *alongside* explicit `supersedes` would be two sources of truth for one fact — the anti-pattern. So lineage is fully explicit: a uuid DAG expresses every shape (linear, fork, merge, rename), is authoritative, and matches how UDLM already models lineage (`decision-record.supersedes`) and every other relationship (`depends_on`, bindings) — explicit and uuid-based. The cost is authoring the link on each new version; the payoff is completeness and one truth.

## Options considered

- **YAML anchors / merge keys** — rejected as the *model* mechanism (kept as an authoring convenience): they are per-file, parse-time textual expansion that leaves no trace in the stored data — no cross-file reuse, no governance, no integrity. A reference is persistent, cross-file, and validated.
- **Inline the data** — rejected: drift. The whole point is one governed source.
- **Name-keyed reference** (point by handle/label) — rejected: the name is not authoritative, so a reused name silently rebinds (finding #1). Name is carried as advisory only.
- **A new "fragment" record type** — rejected: Reference Data Layers already are exactly this (governed, versioned, lifecycle-managed shared data). Reuse, don't duplicate (whole-system reuse).
- **Emergent lineage** (group by `handle`, order by `version`; no explicit link) — rejected: structurally incomplete (no fork/merge/rename) and mis-chains on handle reuse (advisory-axis, finding #1). Cannot be *the* mechanism.
- **Hybrid — emergent by default, explicit `supersedes` for the edge cases** — rejected as the anti-pattern: two lineage sources for one fact, which can disagree and force reconciliation. If emergent can't be complete, go fully explicit.
- **Object reference `{ref_uuid, ref_name, ref_version, reference_data_type}`, uuid-authoritative, pinning an immutable version, resolved to a typed reference-data layer, integrity-checked; lineage a single explicit `supersedes` DAG** — **chosen.**

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** the reference object shape, `reference_data_type` on the layer, and the reference-data layer records themselves.
- **Policy (DCM):** the assembly engine that resolves references and injects reference data into the payload at render time; profile-governed review of who may author reference-data layers.
- **Provider:** authors nothing new here yet; the deferred provider-capability application (§5) lets a provider reference shared capability data rather than restating it.

## Consequences

- `layer.schema.json` gains `reference_data_type` (required for `reference_data` layers); `data-reference.schema.json` defines the canonical object shape for reuse by any schema that offers a field as `oneOf [inline, data_reference]`.
- `validate.py` gains `check_data_references` (wired into layer + realized-entity validation), enforcing referential integrity across the registry — dangling/mistyped/dishonest references do not merge.
- Reference data is immutable: a change is a new record (new uuid + version), never an edit. A reference pins the exact version; existing references stay valid (only a retired target is refused).
- `layer.schema.json` gains `supersedes` (the single explicit lineage link); `data-reference.schema.json` gains `ref_version` (advisory version pin, honesty-checked). `validate.py` gains `check_layer_lineage` (supersedes integrity) and `impact_report()` (advisory change-impact map derived from the supersedes DAG + reverse reference index — "which references are pinned to a now-superseded version").
- Reference data changes propagate by version: change the governed layer once, referrers pin the version they were built against, and impact analysis lists who is behind — the reuse win with a lineage audit trail.
- Worked examples: `example-reference-data-network-zone.yaml` (v1) + `-v2.yaml` (a new immutable version that `supersedes` v1) + `example-layer-referencing.yaml` (a consumer pinned to v1, surfaced by the impact report).
