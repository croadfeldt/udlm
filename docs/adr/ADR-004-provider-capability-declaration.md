# UDLM ADR-004: Provider capability declaration (topology + mobility + operational + sovereignty)

**Status:** Proposed
**Date:** 2026-06-27 (amended 2026-07-14 — blocks scoped per capability, not per provider; sovereignty added)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-001 (`Topology` — the abstract domains this declares fulfillment *of*); ADR-003 (data mobility — `mobility` derives from §3); ADR-PROV-002 (capabilities are `(verb × domain)` categories — the scoping this aligns to); ADR-009/010/011 (how a per-capability sovereignty constraint propagates down the fulfillment graph and is proven at the reserve/commit barrier); DCM ADR-022 (trust/attestation); `governance/accreditation-and-authorization-matrix.md` §3.3/§3.3.1 (the accreditation record + the 1-1 match / binding-grain rules); `registry/provider-adopted-standards.schema.json` (the declaration schema — the exact field structure); `contracts/provider-contract.md` §2/§8.1a; DCM ADR-005, **DCM ADR-019 (Placement)**.
**Tracking:** placement-data family — providers must declare topology/mobility/operational/sovereignty capability to satisfy placement + operational/SRE policies.

## Context

`Topology` (ADR-001) and `data_mobility` (ADR-003) are consumer-side abstractions; they only resolve if **providers declare what they can offer** — which topology dimensions, jurisdictions, migration guarantees, and operational primitives (drain, online-migrate, rehearsal). Placement matches consumer requirements ↔ provider capability; operational/SRE policies key off the primitives. UDLM already has a provider declaration (`provider-adopted-standards.schema.json`); this generalizes it.

## Decision

### 1. A provider capability declaration — data, not a type

Alongside the existing `adopted_standard_support`, the provider declares, **per capability**, four blocks: `topology_capability` (the abstract topologies it can *fulfill* — not a `Topology` instance, ADR-001), `mobility` (migration methods/guarantees per resource type; the mechanism stays provider-internal, ADR-003 §3), `operational_capability` (SRE primitives — drain/online-migrate/rehearsal/health-reporting), and `sovereignty` (§3). It is provider **data**; matching/negotiation is **Policy** (Placement Engine + operational policies). Field shapes are in `provider-adopted-standards.schema.json`.

### 2. Blocks are scoped per capability, finest-granularity-wins — not per provider

A provider's capabilities are `(verb × domain)` categories (ADR-PROV-002), and these blocks **legitimately differ per category**: `realize_resources/Compute` may guarantee `zone` separation and online-migrate while `realize_resources/Storage` guarantees only `rack` and cannot drain. A single provider-wide `max_separation` or `drain: true` is wrong the moment a provider offers more than one thing. So a block is declared **on each capability**, overriding an optional provider-level default; the per-capability value is what placement/policy matches — the provider block is the default, never the ceiling. This aligns with §8.1a capacity advertisement (already per capability) and with `mobility` (already resource-type-scoped).

**The versioned, accreditable unit is coarser than the per-category grain.** Identity, `version`, and accreditation attach to a capability that may span more than one `(verb × domain)` category, while topology/sovereignty vary *within* it per category. The exact nesting (an offering that contains category blocks vs a flat per-category list) is a **schema decision** (`provider-adopted-standards.schema.json`), not settled here; this ADR fixes only that blocks are per-category + finest-wins, and that the accreditable/versioned unit is distinct from the category grain.

### 3. Sovereignty is a claim, trusted only by a 1-1 accreditation match

A per-capability `sovereignty` block overrides the provider-wide `sovereignty_declaration` (finest wins) — residency differs by what is realized (Compute EU-only, Storage global). It is a **CLAIM**; trust requires a **1-1 match** with an accreditation attesting **exactly** its scope — provider × capability × jurisdiction. **No partial or inherited credit:** an unmatched claim is `self_asserted` and not honored for sovereign/restricted placement. The accreditation record carries the explicit scope, and the match + binding-grain rules live in `governance/accreditation-and-authorization-matrix.md` §3.3/§3.3.1. (`topology_capability.jurisdictions` is the *placement* input — where it can spread; `sovereignty` is the *authorization* stance for the same category — reconciled, not duplicated.)

### 4. A per-capability sovereignty claim is a pipeline-wide obligation

Declaring sovereignty at the capability scope obligates the provider to **guarantee it the whole way down that capability's realization pipeline** — every brokered dependency (ADR-009), sub-processor, and downstream hop must satisfy the same stance, **re-attested 1-1 at its own hop**. The *constraint* propagates along the fulfillment/dependency graph (ADR-009/010); **trust never inherits** — only the constraint does. It is proven across the reserved graph at the commit barrier (ADR-011), before anything is built. This is a *stronger* commitment than provider-scope and MUST be available. Enforcement is platform policy (DCM, ADR-022); UDLM carries the propagation + per-hop-attestation data (ADR-008 boundary).

### 5. Determinism is a configurable platform-admin dial

How deterministic an accreditation binding must be is org/platform policy (profile-governed), not a fixed rule: **per provider** (survives capability changes) · **per capability category** (survives version bumps) · **per exact `(capability_uuid, version)`** (a capability change is a new version the accreditation does not cover, so the claim reverts to `self_asserted` until re-attested). To enable the strict grain, each capability carries a stable `capability_uuid` + immutable `version`; `provider.capability_changed` (provider-contract §6) fires accreditation re-evaluation. Grains + expiry: `accreditation-and-authorization-matrix.md` §3.3.1.

### 6. Boundary (ADR-008)

The declaration shape, the four blocks' wire meaning, and the sovereignty-claim vocabulary are **UDLM** — a peer must read them identically. The matching/scoring, the 1-1 reconciliation, placement, and pipeline enforcement are **DCM**.

## Options considered

- **Undeclared capability (discover at runtime only)** — rejected: placement/SRE must match *before* committing; declaration enables negotiation + conformance.
- **A new capability resource type** — rejected: this is a provider declaration (extends the existing one), not a managed resource.
- **Provider-wide blocks (the pre-amendment shape)** — rejected: wrong for any multi-capability provider (Compute ≠ Storage).
- **Sovereignty trust = the claim alone, or claim ∩ attestation (intersection)** — rejected: trust requires a **1-1** claim↔accreditation match; no partial credit.
- **A fixed determinism/binding grain** — rejected: it is a platform-policy dial (dev lax, sovereign/fsi strict).

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** the per-capability declaration (topology/mobility/operational/sovereignty), each capability's `capability_uuid` + `version`, and the accreditation record's explicit scope.
- **Policy (DCM):** matching/scoring/gating (ADR-019/020); the 1-1 claim↔accreditation reconciliation that decides *trusted* residency; the binding-grain + pipeline-propagation enforcement.
- **Provider:** authors the declaration, executes it (naturalization, migration, rehearsal), and — for a per-capability sovereignty claim — guarantees it down the whole pipeline.

## Consequences

- **Schema (follow-on, not yet implemented):** extend `provider-adopted-standards.schema.json` — the four blocks + accreditation binding nested per capability, with `capability_uuid`/`version`; the exact nesting is settled there. A new `accreditation.schema.json` encodes the §3.3 record.
- **All provider "what I can do for X" data is uniformly per capability** (capacity §8.1a, topology, mobility, operational, sovereignty) — a multi-capability provider is never one global claim.
- **Sovereignty is a propagating constraint, not a static field** — guaranteed down the pipeline, re-attested 1-1 per hop, proven at the reserve/commit barrier.
- DCM side (separate ADR): the matching/scoring, 1-1 reconciliation, and pipeline enforcement that consume this.
