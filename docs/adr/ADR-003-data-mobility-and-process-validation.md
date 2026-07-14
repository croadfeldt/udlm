# UDLM ADR-003: Data mobility + process-validation lifecycle

**Status:** Proposed
**Date:** 2026-06-27
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `design-principles/core-tenets.md` **T6** (pre-validated outcomes), T2/T5; ADR-001 (`Topology`), ADR-002 (capacity/utilization); the cost served pattern; **DCM ADR (migration policy + gating)**
**Tracking:** placement-data family — "how is data migration handled, and how do we pre-validate it?"

## Context

Rehydrate, workload movement, topology-change, provider-switch, and DR are the **same operation**: move a resource's data to a new placement honoring requirements. It must be **declarable by deployments / applications / policies**, vendor-neutral, and — per **T6** — its process must be **continuously validated**, so a real incident executes a *validated* path rather than testing an unknown.

## Decision

Decompose across the boundary (same shape as placement): **consumer declares the *outcome*; the provider declares *methods* and *executes the mechanism*; Policy governs *permission* and *gating*; evidence is observed.** No new top-level type — the declarables are **common-elements** (attachable at resource / composite / policy layers) plus a provider-capability declaration plus observed evidence.

### 1. `data_mobility` — migration requirements (consumer intent; common-element)
The outcome a deployment requires of any move. Declarable on a resource, a composite/application (default), or mandated by Policy.
```json
"data_mobility": {
  "criticality": "critical | high | standard | low",
  "rto": "<duration>",                 "rpo": "<duration>",
  "downtime": "online | minimal | offline",
  "consistency": "strong | causal | eventual",
  "rollback_window": "<duration>",
  "method_class": ["online-streaming", "snapshot-ship", "logical-dump"]  // capability-level, NOT a mechanism
}
```
`rto`/`rpo` reuse the standard DR vocabulary (adopt-by-reference). `method_class` constrains at the *capability* level only — the consumer never names a mechanism (T-outcome).

### 2. `process_validation` — the validation lifecycle requirement (consumer intent; common-element)
Per **T6**: how continuously the mobility outcome must be proven.
```json
"process_validation": {
  "required_modes": ["simulated", "rehearsal"],
  "cadence": "<duration>",              // default derived from data_mobility.criticality
  "freshness_sla": "<duration>",        // claim is `stale` past this
  "synthetic_data": { "from": "schema", "classification": "non-sensitive" },
  "gate_on_stale": true                 // request DCM refuse to depend on an unproven path (enforced as Policy)
}
```

### 3. Provider mobility capability (provider declares; in the provider declaration)
What the provider can actually do — matched against `data_mobility`. Extends the provider-adopted-standards pattern.
```json
"mobility": [
  { "resource_type": "Data.Database", "methods": ["online-streaming", "snapshot-ship"],
    "guarantees": { "rpo_min": "0s", "cross_region": true, "online": true } }
]
```
The **mechanism** itself (rbd-mirror, pg logical replication, dual-write) is provider implementation — **not modeled** (naturalization).

### 4. Observed evidence (Discovered; served, like cost/capacity)
A migration *operation* and its validation result — observed, source-attributed, **not a new type** (a job/operation surfaced via status/events; defer first-classing it).
```json
"mobility_validation": {                // observed overlay on the resource / claim
  "mode": "simulated | rehearsal | live",
  "state": "validated | stale | failing",
  "last_validated": "<rfc3339>",
  "achieved": { "rto": "<duration>", "rpo": "<duration>" },
  "result": "pass | fail", "evidence_ref": "<audit/finding ref>"
}
```
Both **rehearsals and real incidents** write this — a real DR event *is* a validation event (**T6**).

## Why these shapes (not new types)
Consistent with ADR-002 and §-minimal-core: requirements/constraints are **common-elements** on resources/composites (like Identity/Quantity); capability is a **provider declaration**; evidence is an **observed overlay** (cost pattern). The only thing that could later earn first-classing is the migration **operation/job** — deferred until needed.

## Rehearsal & simulation — validating mobility claims (T6)
- **`simulated`** runs the process with **synthetic, schema-conformant, non-sensitive** data → validates the *process* with **no real regulated data moved** → **sovereignty-safe cross-jurisdiction DR rehearsal** (the high-value case for FSI/sovereign).
- **`rehearsal`** runs real data to a reversible/scratch target → validates the *real* path.
- Each run updates `mobility_validation` (state + freshness + achieved RTO/RPO) and raises a **finding** on failure.
- **Criticality → cadence**; **stale → gate** (Policy). A critical workload's resilience claim is a living, freshness-tracked property, not a one-time cert.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** `data_mobility` + `process_validation` requirements + `mobility_validation` evidence.
- **Policy (DCM):** migration permission/sequence + freshness gating + rehearsal scheduling (DCM ADR-020).
- **Provider:** declares `mobility` + `operational_capability` (ADR-004); **executes** the migration mechanism and the rehearsals (unmodeled "how").

## Options considered
- **Consumer authors the methodology** — rejected (violates intent-as-outcome; "how" is the provider's concern).
- **A `Migration`/`Mobility` first-class type** — rejected for the requirements/capability/evidence (common-element + provider-declaration + observed overlay, per ADR-002); only the live operation might later first-class.
- **Decomposed (requirements=data, methods=provider-declared, mechanism=provider, permission+gating=Policy, evidence=observed) + T6 rehearsal lifecycle** — **chosen.**

## Consequences
- New common-elements `data_mobility` + `process_validation` (declarable at resource/composite/policy layers); a provider `mobility` capability block; an observed `mobility_validation` overlay. No new top-level type.
- Makes ADR-001's "change topology → rebuild" **provable**: the rebuild path is rehearsed + freshness-tracked; the db tier's "not instant" caveat becomes a *matched, validated, policy-gated* contract.
- Ties to the rehydration demo (#213): a rehearsed rehydration is a validated one.
- DCM side (separate ADR): migration **policy** (sovereignty/windows/approval/serialization) + **gate-on-stale** enforcement + rehearsal **scheduling**.
