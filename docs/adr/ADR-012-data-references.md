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

## Options considered

- **YAML anchors / merge keys** — rejected as the *model* mechanism (kept as an authoring convenience): they are per-file, parse-time textual expansion that leaves no trace in the stored data — no cross-file reuse, no governance, no integrity. A reference is persistent, cross-file, and validated.
- **Inline the data** — rejected: drift. The whole point is one governed source.
- **Name-keyed reference** (point by handle/label) — rejected: the name is not authoritative, so a reused name silently rebinds (finding #1). Name is carried as advisory only.
- **A new "fragment" record type** — rejected: Reference Data Layers already are exactly this (governed, versioned, lifecycle-managed shared data). Reuse, don't duplicate (whole-system reuse).
- **Object reference `{ref_uuid, ref_name, reference_data_type}`, uuid-authoritative, resolved to a typed reference-data layer, integrity-checked** — **chosen.**

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** the reference object shape, `reference_data_type` on the layer, and the reference-data layer records themselves.
- **Policy (DCM):** the assembly engine that resolves references and injects reference data into the payload at render time; profile-governed review of who may author reference-data layers.
- **Provider:** authors nothing new here yet; the deferred provider-capability application (§5) lets a provider reference shared capability data rather than restating it.

## Consequences

- `layer.schema.json` gains `reference_data_type` (required for `reference_data` layers); `data-reference.schema.json` defines the canonical object shape for reuse by any schema that offers a field as `oneOf [inline, data_reference]`.
- `validate.py` gains `check_data_references` (wired into layer + realized-entity validation), enforcing referential integrity across the registry — dangling/mistyped/dishonest references do not merge.
- Reference data changes propagate by version: change the governed layer once, every referencing record picks it up on the next assembly — the reuse win, with an audit trail (each reference names the exact uuid).
- Worked examples: `example-reference-data-network-zone.yaml` (the governed dataset) + `example-layer-referencing.yaml` (a consumer binding it by reference).
