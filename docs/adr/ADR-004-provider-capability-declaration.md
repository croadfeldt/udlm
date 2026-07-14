# UDLM ADR-004: Provider capability declaration (topology + mobility + operational)

**Status:** Proposed
**Date:** 2026-06-27 (amended 2026-07-14 — capability blocks scoped per capability category, not per provider)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-001 (`Topology`), ADR-003 (data mobility + process validation), ADR-PROV-002 (capabilities are `(verb × domain)` categories — the scoping this amendment aligns to); `registry/provider-adopted-standards.schema.json` (existing provider declaration); `contracts/provider-contract.md` §8.1/§8.1a; DCM ADR-005 (Provider Abstraction — capability declarations + bidirectional discovery), **DCM ADR-019 (Placement Policy)**
**Tracking:** placement-data family — "providers must declare capabilities/compatibility with topology and data portability/migration, to satisfy placement and operational/SRE policies."

## Context

`Topology` (ADR-001) and `data_mobility` (ADR-003) are **consumer-side** abstractions. They only resolve if **providers declare what they can actually offer**: which topology dimensions they expose, which jurisdictions they cover, what migration methods/guarantees they support, and which operational primitives (drain, online-migrate, rehearsal) they implement. Placement *matches* consumer requirements ↔ provider capability; operational/SRE policies *key off* the operational primitives. UDLM already has a provider declaration artifact (`registry/providers/*` validated by `provider-adopted-standards.schema.json`) and DCM already declares "providers declare capabilities" (ADR-005) — this generalizes that declaration.

## Decision

Generalize the provider declaration into a **provider capability declaration** — the provider-authored record of what it can satisfy. It carries the existing `adopted_standard_support` plus, **per declared capability**, three capability blocks. It is a **provider declaration (data)**, not a resource type; matching/negotiation against consumer requirements is **Policy** (the Placement Engine + operational policies).

### 0. Scope — declared per capability category, not per provider

A provider's capabilities are **`(verb × domain)` categories** (ADR-PROV-002), each scoped to the resource-type Category it realizes, and PROV-002 requires the declaration to "include everything else the realization needs **for that capability**." Topology fulfillment, data mobility, and operational primitives *are* that — and they **legitimately differ per category**: a provider's `realize_resources/Compute` may guarantee `zone` separation and online-migrate, while its `realize_resources/Storage` guarantees only `rack` and cannot drain. A single provider-wide `max_separation` or `drain: true` is wrong the moment a provider offers more than one thing.

So the three blocks below are declared **on each capability entry** — the same shape as the provider's advertised inventory/capacity (`provider-contract.md` §8.1a, which is already per capability category). `mobility` was already resource-type-scoped; this amendment aligns `topology_capability` and `operational_capability` to the same rule.

```json
"capabilities": [
  {
    "category": "realize_resources/Compute",           // (verb × domain), ADR-PROV-002
    "resource_types": ["Compute.VirtualMachine"],
    "topology_capability": { /* §1 — for THIS category */ },
    "mobility": [ /* §2 */ ],
    "operational_capability": { /* §3 */ }
  },
  {
    "category": "realize_resources/Storage",
    "resource_types": ["Storage.Volume"],
    "topology_capability": { "kinds_supported": ["rack"], "max_separation": "rack" }
  }
]
```

A provider whose *entire* offering shares one topology/operational profile MAY set a provider-level default block, but any per-capability entry **overrides** it and is the value placement matches against. Per-capability is the floor; provider-wide is a convenience, never the authority.

### 1. `topology_capability` — the topologies a provider can *fulfill* for a capability (compat with ADR-001)
**A provider does not author a `Topology` instance — it declares the topologies it can *fulfill*, as a capability.** (The concrete `Topology` instance — the actual domains — is realized/discovered, a separate artifact from this declaration; ADR-001.) Matched against a workload's abstract topology constraints.
```json
"topology_capability": {
  "kinds_supported": ["region","zone","host","power-domain"],   // separation it can GUARANTEE
  "native_mapping":  { "zone": "aws-az", "host": "hypervisor" },// native → abstract kind (naturalization)
  "jurisdictions":   ["us","eu"],                                // residency/sovereignty coverage
  "max_separation":  "zone",                                     // strongest anti-affinity it can promise
  "reference_topologies": ["ha-3zone","single-zone"]             // optional: named topology archetypes it can fulfill
}
```
This is the provider-declared side of ADR-001's "providers declare how their native topology fills the abstract kinds." A provider with no failure-domain concept declares `kinds_supported: []` → fails the capability filter for any spread constraint (correct). `reference_topologies` lets a provider advertise fulfillment of **named topology archetypes** (a future reference-topology catalog); the primitive capabilities (kinds / separation / jurisdictions) are the floor matching always uses.

### 2. `mobility` — data portability / migration capability (from ADR-003 §3)
```json
"mobility": [
  { "resource_type": "Data.Database", "methods": ["online-streaming","snapshot-ship"],
    "guarantees": { "rpo_min": "0s", "cross_region": true, "online": true } }
]
```
Matched against the consumer's `data_mobility` requirements. The *mechanism* stays provider implementation (unmodeled).

### 3. `operational_capability` — SRE-pattern primitives
What the provider supports so operational policies / SRE patterns can rely on it:
```json
"operational_capability": {
  "drain": true,                 "maintenance_mode": true,
  "online_migrate": true,        "rolling_update": true,
  "rehearsal_support": ["simulated","rehearsal"],   // enables ADR-003 / T6 validation
  "health_reporting": ["domain","resource"]          // feeds fault-domain gating + Topology.outputs
}
```
Fault-domain maintenance gating, rehearsal-based process validation (T6), and rolling cutover all require these primitives; if a provider can't `drain`, the SRE pattern that depends on draining can't be promised on it.

## How it's consumed (matching, not just storage)

- **Placement** (DCM ADR-019): filter/score providers by the `topology_capability` **of the capability category that would realize the resource** (can *that* category satisfy the abstract spread/anti-affinity/jurisdiction?) + its `mobility` (can it meet `data_mobility`?). A provider is not eligible because *some* capability of its clears the filter — the eligible capability is the one whose `resource_types` cover the request.
- **Operational / SRE policies**: gate on the `operational_capability` of the realizing capability — e.g. "critical Compute workloads only on providers whose `realize_resources/Compute` capability has `online_migrate` + `rehearsal_support` + `drain`" (a provider that can drain hosts but not its storage is gated correctly).
- **Process validation** (T6): `rehearsal_support` is what makes the mobility claim *validatable*; an un-rehearsable provider can't carry a fresh resilience claim.

Capability declaration says what's **possible**; the `Topology` instance (ADR-001) is the **concrete** graph the provider contributes; placement uses the former to negotiate and the latter to place.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the provider capability declaration shape — `topology_capability` + `mobility` + `operational_capability`.
- **Policy (DCM):** matching/scoring/gating consume it (DCM ADR-019/020) — requirements ↔ capability negotiation.
- **Provider:** **authors** the declaration and **executes** what it declares (naturalization, migration, rehearsal).

## Options considered
- **Implicit/undeclared capability (discover at runtime only)** — rejected: placement and SRE policies need to match *before* committing; declaration enables negotiation + conformance.
- **A new capability resource type** — rejected: this is a **provider declaration** (extends the existing one), not a managed resource — consistent with the adopted-standards declaration and DCM ADR-005.
- **Generalize the provider declaration with topology + mobility + operational blocks** — **chosen.**

## Consequences
- Extend `provider-adopted-standards.schema.json` → a **provider capability declaration** schema. The `topology_capability` / `mobility` / `operational_capability` blocks are nested **under each declared capability entry** (keyed by the ADR-PROV-002 `(verb × domain)` category + its `resource_types`), not at the provider root; an optional provider-level default block is permitted, overridden by any per-capability entry. Existing `adopted_standard_support` unchanged. (Not yet implemented — this ADR is the shape the schema will encode.)
- **Consistency:** this makes all provider-declared "what I can do for X" data — advertised inventory/capacity (`provider-contract.md` §8.1a), mobility, topology, and operational primitives — uniformly **per capability category**, so a multi-capability provider is never described by a single global claim.
- Closes the loop: consumer requirements (`Topology` constraints + `data_mobility`) ↔ provider capability ↔ Policy matching/gating. Placement, sovereignty, fault-domain gating, and process validation (T6) all negotiate against one declaration.
- DCM side (separate ADR): the matching/scoring + operational gating that consume this.
