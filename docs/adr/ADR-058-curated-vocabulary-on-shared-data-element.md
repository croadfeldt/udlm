# UDLM ADR-058: Curated vocabulary rides on **SharedDataElement** — scope is portability, the intake ladder is standardization (no new construct)

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; completes ADR-054 (the missing half of "context is an edge, assembly is a layer"); maintainer decision 2026-07-28
**Date:** 2026-07-28
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **ADR-054** (references-context is a classified edge): moved *orthogonal context* — data **about** a resource — onto a context edge to a linked entity (an `edge_type: references` edge with a declared `relation`; nature is derived, never stored). It addressed **only** context, not vocabulary — and it did not retire `reference_data`, which marks a layer other layers reference.
- **ADR-038 §2–§3** (`SharedDataElement`, `registry/class.schema.json` `$defs.shared_data_element`): the composable unit of the Class hierarchy — "**base field, shared vocabulary, and provider extension collapse into one shape distinguished only by `scope`**," and **"the scope position IS the element's portability."** An element's `values.reference_data_type` already declares a **governed vocabulary** (not an inline enum).
- **ADR-039 + `docs/design/vocabulary-intake-ladder.md`** (the vocabulary-intake ladder): `proposed → canonical` curation + **profile-gated strictness** (homelab mint-on-write … sovereign canonical-only, unknown **refused**; near-matches never bind silently). Scope promotion is the class system's portability-improvement operation.
- **ADR-012** (data references / dual anchor): the binding a `values`-typed element uses to resolve one canonical term.

**Settles:** where a **curated vocabulary** lives once `reference_data` is no longer a `layer_type` — **and** why that placement makes portability and standardization *structural*, not optional.

## Context

`reference_data` did **double duty**. ADR-054 retired it from `layer_type` for the **context** role, but the same construct also stored **curated vocabularies** — the term sets (`os_image`, `vm_size`, `storage_tier`) a Class element binds one member of. Retiring the layer form removes that storage home, and ADR-054 is silent on it.

The first draft of this ADR proposed a *new* `Codelist` entity + `vocabulary` edge. **That was wrong** — it reinvents `SharedDataElement`, which already collapses "shared vocabulary" into the element shape and already carries the scope that gives portability. And it left the real problem unaddressed: `os_image`/`vm_size` "mean many things," so a vocabulary needs an **enforced portable position and a standardization gate** — which a loose reference-data record never had, and which the scoped-element model already provides.

## Decision (proposed)

**1. A curated vocabulary is not a new construct — it is a `SharedDataElement` with `values`.** The term set for a vocabulary kind is carried by the element that binds it (ADR-038 `values.reference_data_type`), held at a Class scope. No `Codelist` entity, no `vocabulary` edge nature. Context and vocabulary are distinct *because they use distinct existing mechanisms*: **context is an edge to a linked entity** (data *about* me — ADR-054); **vocabulary is a scoped element value-set** (which *terms my field may take* — ADR-038).

**2. Portability is the scope position — enforced, not asserted.** `os_image`/`vm_size` mean many things precisely because meaning is **scope-relative**: a term set promoted to a `Compute` (Base) or `Compute.VM` (Type) scope is portable across providers; a provider's extra terms sit at its Provider scope. Same element name, resolved by scope. Portable reliance on a term requires it be **canonical at a scope at least as general as the consumer's** — the scope position *is* the portability contract (ADR-038 §3), checkable in a diff, promoted by the governed contribution operation.

**3. Standardization is the vocabulary-intake ladder — enforced by profile.** A value binds through ADR-039: `proposed → canonical`, with **profile-gated strictness** — homelab may mint on write, sovereign/fsi is canonical-only and **refuses** an unknown term (citing the pending proposal); near-matches never bind silently. Standardization is therefore a **floor the profile sets** (ADR-007), not a hope.

**4. Term storage relocates into the scoped-element model.** Canonical terms move from standalone `reference_data` **layers** into the **scoped-element** model — anchored to the `SharedDataElement`'s declared vocabulary kind at its scope — so every vocabulary is under scope-portability (#2) and the intake ladder (#3) **by construction**. This closes the current gap where vocabularies sat in loose layers *outside* both enforcements. **`reference_data` does NOT retire** (maintainer ruling 2026-08-11, correcting this ADR). It marks a
layer that other layers reference — shared data, defined once and pointed at — and that role is
sound. What leaves is the VOCABULARY role only: a term is matched against, never merged, so it was
never layer-shaped. The terms now live in `registry/vocabulary-term.schema.json`, keyed to
(`vocabulary_kind`, `scope`); `reference_data` keeps the role it was actually doing.

## Alternatives considered (and why not)

- **A new `Codelist` entity + `vocabulary` edge** (this ADR's first draft) — **rejected**: reinvents `SharedDataElement`, the exact "one shape for base field / shared vocabulary / provider extension" construct ADR-038 built; adds a parallel construct ADR-054's through-line forbids.
- **Keep `reference_data` as a non-layer record kind for vocabularies** — **rejected**: leaves vocabularies *outside* the scope-portability + intake-ladder enforcement (the very gap this ADR closes) and keeps a bespoke store next to the element that already owns the vocabulary.

## Data · Policy · Provider · the substrate and its control plane boundary

- **Data (UDLM):** the `SharedDataElement` (name · scope · schema · `values.reference_data_type` · `proposed|canonical`), the canonical terms at scope, the dual anchor. Portable record shape.
- **Policy (the control plane):** the intake ladder (match/mint, strictness by profile), membership + scope-portability validation, promotion.
- **Provider:** naturalizes its native terms into/out of the element at its Provider scope; owns its extension set's source of truth.
- **Peer test (ADR-008):** UDLM defines the element shape, `scope`-as-portability, and the `proposed|canonical` contract (a peer MUST honor); the control plane runs the ladder and enforces strictness (a peer MAY differ).

## Open questions for engineering (what this ADR tees up)

1. **Term storage shape** — do canonical terms live as reference-data records *keyed to* `(vocabulary_kind, scope)`, or inline in the Class artifact at the element's scope? (Recommend keyed records — keeps large vocabularies out of the Class artifact, preserves independent curation.)
2. **`values.reference_data_type` naming** — the field still says `reference_data`; rename to `vocabulary` / `vocabulary_kind` once the layer sense is gone? (Recommend yes, in the migration.)
3. **Migration order** — schemas → relocate current term sets to scope-keyed records → `class.schema`/type-spec field rename → validator/generator → examples. One program (this is #189's true size), gated on this ruling.

## Consequences

- **No new construct** — vocabulary is `SharedDataElement` + ADR-039, both of which already exist; context stays the ADR-054 edge. Two roles, two *existing* mechanisms, `reference_data` retired.
- **Portability and standardization become structural** — every vocabulary sits at a scope (portability) and passes the intake ladder (standardization); neither is optional or ad-hoc.
- **#189's retirement is unblocked and re-sized** into the migration program above — not one PR. The additive two-sided scoping already shipped (#317).

## Related

ADR-054 (references-context — the half this completes) · ADR-038 (`SharedDataElement`, scope = portability) · ADR-039 (vocabulary-intake ladder, standardization) · ADR-007 (profile floors) · ADR-012 (data references / dual anchor) · #189 (the retirement program) · #217 (engineering ratification).
