# UDLM ADR-001: `Topology` — cross-cutting failure/locality-domain type

**Status:** Proposed
**Date:** 2026-06-27
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** SPEC-DESIGN-REQUIREMENTS §17 (vendor-neutrality), §26/§27 (component granularity & instance identity), `registry/naming-conventions.md` §1; **DCM ADR-019 (Placement Policy)** — the control-plane consumer
**Tracking:** placement-informing data family; raised via dcm-project/dcm #64 ("what about placement policy?")

## Context

DCM's Placement Engine tie-breaks on `affinity`/`cost`/`load`, but nothing **authors** placement constraints and there is **no model** for them to resolve against. Expressing "spread across failure domains" / "co-locate" / "keep in EU" in **provider-native** terms (AZ ids, rack names) would destroy workload portability — UDLM's core promise.

## Decision

Introduce **`Topology`** — a UDLM data type that is the **abstract graph of failure/locality domains** placement, residency, fault-domain gating, and ordering resolve against.

1. **Cross-cutting, single-segment type.** `resource_type: "Topology"`, `family: Resource`, `entity_type: Infrastructure Resource`. Single-segment (not `Category.Type`) because it is **not owned by any single domain** — resources across Compute/Network/Storage/Facility reference it (`naming-conventions.md` §1; the meta-schema pattern already permits single-segment).
2. **Failure domains are addressable *data within* `Topology`, not their own type** — `spec.domains[]`, each keyed by a stable `id`, with `parent` forming an acyclic hierarchy. This applies §26 (data-element-by-default; entity only when independently tracked) and §27 (key by stable discriminator). The §26 escape hatch remains: a deployment may elevate domains to first-class entities if it genuinely needs independent lifecycle — not the default.
3. **Abstract `kind` vs concrete `id` (the portability discipline, §17 applied to topology):**
   - Each domain carries an **abstract `kind`** (`region`/`zone`/`rack`/`host`/`power-domain`/`network-segment`) — the dimension a constraint targets — and a **concrete `id`** (`ups-a`, `host-01`).
   - **Intent references kinds, never concrete ids.** Providers **declare** how their native topology fills those kinds (naturalization), so provider topology becomes a **declared capability** matched like any other → the engine can **allocate a workload to whichever provider's topology satisfies it**.
   - The concrete domain a resource lands in is **Realized/Discovered state, provider-attributed** (a resource's locality reference, carried on the *resource*, not here); it may differ per provider without changing portable intent. Provider-instance pinning is an explicit `portability: provider-specific` opt-out.
4. **Declared `spec` / observed `outputs`** — `spec` = the declared domain graph; `outputs.domain_status` = observed per-domain availability (`active|draining|unavailable`) for fault-domain gating and candidate filtering. (UDLM `outputs` is a name→`{type}` binding map, so per-domain detail rides in the output description.)
5. **Sovereignty/residency** is a placement constraint over jurisdiction-labeled domains (`domains[].labels`), unifying it with placement rather than special-casing it.

## Why it *helps* portability (not hinders)

Abstract constraints are the **portability-preserving** way to express spread/co-locate/residency; provider-native placement is what breaks it. See DCM ADR-019 for the worked example (shared-UPS power domain).

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the `Topology` type — kinds + concrete domains + labels — and each resource's locality reference.
- **Policy (DCM):** Placement Policy (ADR-019) resolves abstract constraints against it; sovereignty resolves over jurisdiction labels.
- **Provider:** declares `topology_capability` (ADR-004), naturalizes abstract kinds to its native topology, and contributes the concrete domains.

## Options considered

- **No `Topology`; constraints provider-native** — rejected (kills portability).
- **A `FailureDomain` type** — rejected; failure domains are structural data within `Topology` (§26), not independent entities, by default.
- **Domain-buried (`Platform.Topology` etc.)** — rejected; topology is cross-cutting, so single-segment top-level is the correct, domain-neutral placement.

## Consequences

- New UDLM type `Topology` (validates against the meta-schema today; `validate.py` green).
- Companion additions (separate, small): a **locality reference** common-element on resources (which domain they're in) and **affinity/placement labels**.
- **Reuse — one model, ≥3 consumers:** placement (DCM ADR-019), sovereignty/residency, homelab fault-domain maintenance gating (host = OCP-node + Ceph-OSD shared fault domain), and shutdown/startup/rehydrate ordering.
- **Conformance** must enforce that intent-side topology stays abstract (no provider-native ids in the portable spec).
- Future differentiation (topology policies, domain sub-types) is deferred until it earns inclusion.
