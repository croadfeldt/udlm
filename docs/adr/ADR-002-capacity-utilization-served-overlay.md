# UDLM ADR-002: Capacity / Utilization — served overlay, not a type

**Status:** Proposed
**Date:** 2026-06-27
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `design-principles/core-tenets.md` (Data⇄Policy boundary, T5 adopt-by-reference); the **cost** decision (FOCUS adopted + served, not modeled — `docs/resource-type-registry-design-notes.md` §4a); ADR-001 (`Topology`); **DCM ADR-019 (Placement Policy)** — a consumer
**Tracking:** placement-informing data family — "is capacity/utilization a record type, or data on the resource?"

## Context

Placement scoring needs capacity/utilization. But:
- DCM is authoritative only for **allocated** (what it placed) — **not for available** (real usage includes drift, overhead, and things DCM didn't place; ground truth is the provider/infrastructure).
- Capacity/utilization is **multi-source** (provider + 3rd-party monitors) — needs per-source provenance + timestamps.
- Modeling question: capacity as its own type, or resource + capacity data?

## Decision

**The resource type is the grounding anchor; capacity/utilization *references* it. It is NOT its own UDLM type.** It splits by change-rate + authority:

| Quantity | Authority | Treatment |
|---|---|---|
| **Total capacity** | provider / discovered fact (slow) | **data element on the resource's observed (Realized/Discovered) state** |
| **Available / utilization** | provider **+** 3rd-party (fast, multi-source) | **served observational overlay** referencing the resource by id — provided by an information / `serve_data` provider, **adopt-by-reference** (K8s `capacity`/`allocatable` + Metrics API; OpenStack Placement `inventories`/`usages`; OpenMetrics). Multi-source provenance handled by source attribution + the existing **field-level provenance** (realized-entity schema). **Not a UDLM type.** |
| **Allocated** | DCM (it made the placements) | **derived projection** over DCM's own Realized entities — not a new type |

**This follows the cost pattern exactly.** Cost was deliberately *not* modeled as a UDLM type — it is adopted (FOCUS) and **served** by an information provider, referencing resources by id (`uuid ↔ ResourceId`). Capacity/utilization is the same shape (a multi-source observational overlay) and gets the same treatment. The principled line: **declared *structure* → a type (e.g. `Topology`, ADR-001); observed *measurement* → a served overlay (cost, capacity/utilization).**

It is **DATA** (Data⇄Policy): the DCM Placement Policy (ADR-019) consumes it; the engine computes; no embedded expressions.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** total capacity (resource attribute) + the served utilization overlay; allocated is derived.
- **Policy (DCM):** placement scoring + capacity/headroom gates consume it.
- **Provider:** serves the utilization overlay (information / `serve_data` provider) and is the authority for *available*.

## Options considered

- **Capacity as embedded resource metadata only** — rejected: a scalar field can't carry multiple authoritative sources, churns the resource system-of-record, and can't represent *available* (which DCM isn't authoritative for).
- **A first-class `Capacity`/`Utilization` type** — rejected: contradicts the cost precedent and §-minimal-core; observed measurement is a served overlay, not a managed entity. *(This reverses an earlier draft that proposed an observation record type.)*
- **Resource-anchored: total = data element, available/utilization = served overlay, allocated = derived** — **chosen.** Matches K8s, OpenStack Placement, Redfish, and the cost overlay; keeps the type surface minimal.

## Consequences

- **No new UDLM type.** Small additions to the realized/discovered shape for **total capacity**; available/utilization is an adopt-by-reference **served-data contract** (a provider capability), not a registry type.
- **Allocated** is computed in DCM (no model change).
- **Reuse:** the same overlay feeds FinOps/observability dashboards and the Placement Engine — one served contract, multiple consumers.
- Consistent with cost: resources are the nouns; cost and capacity/utilization are referencing observational overlays served by information providers.
