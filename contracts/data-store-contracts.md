# UDLM — Data Store Contracts

**Document Status:** ✅ Complete
**Document Type:** Data Model Specification — Contracts the four data domains must satisfy
**Related Documents:** [Four States](../foundations/four-states.md) | [Data Model Core](../foundations/data-model-core.md) | [Universal Audit](../observability/universal-audit.md)

> **Foundation Document Reference**
>
> This document specifies the enforcement contracts for the four data domains and the audit
> domain. Stores are defined by CONTRACT, not technology ([data-model-core](../foundations/data-model-core.md)
> §6, ruling D1) — a conforming realization binds these contracts to concrete stores per profile
> and sovereignty/tenancy policy. The concrete enforcement mechanism (the reference PostgreSQL
> implementation, its SQL schema, RLS, and operators) is realization architecture — see the DCM
> architecture documentation.
>
> **This document maps to: DATA**

---

## 1. Purpose

Data-integrity guarantees are enforced at the **store** level, not the application level. Application code may have bugs; the store enforces the invariants regardless. This document specifies the contract each domain's store binding MUST satisfy. It states *what* must hold — append-only-ness, immutability, traceability, tenant isolation, tamper-evidence — not *how* a particular store enforces it.

---

## 2. Data Domain Contracts

### 2.1 Intent Domain

The Intent domain stores consumer declarations exactly as submitted — before any processing, enrichment, or policy application.

**Contract:**
- **Append-only** — records are never updated or deleted.
- **Versioned** — resubmissions create new records with an incrementing `intent_version`; previous versions are preserved.
- **Immutable fields** — `intent_uuid`, `entity_uuid`, `tenant_uuid`, `submitted_by`, `submitted_at`, `submitted_via` are set on insert and never change.
- **Ingress tracking** — `submitted_via` records the ingress path (`api`, `gitops`, `cli`, `message_bus`).
- **Tenant-isolated** — a tenant context can read/write only intents belonging to that tenant.

### 2.2 Requested Domain

The Requested domain stores fully assembled, policy-evaluated, placed payloads — the authorized dispatch record.

**Contract:**
- **Append-only** — records are never updated or deleted.
- **Traceable** — every record has a non-nullable `intent_uuid` (which intent produced this) and `operation_uuid` (which operation authorized this).
- **Complete provenance** — `layer_sources` records which layers contributed and how many fields each contributed; `policy_results` records which policies evaluated and their outcomes; `provenance` records field-level origin for every field.
- **Placement recorded** — `placement_result` records the provider selection decision, score, and constraints.
- **Tenant-isolated.**

### 2.3 Realized Domain

The Realized domain stores provider-confirmed state as versioned snapshots.

**Contract:**
- **Append-on-change** — state changes create new records; an `is_current` flag marks the latest version; previous versions are retained for point-in-time queries and rehydration.
- **Complete snapshots** — each record captures the full entity state, not a delta from previous state (makes rehydration a direct lookup rather than an event replay).
- **Traceable** — every record has `request_uuid` linking it to the authorized request that produced this state.
- **Versioned** — `version_major.minor.revision` follows semantic versioning: breaking field changes increment major; additive changes increment minor; data-only changes increment revision.
- **Tenant-isolated.**

### 2.4 Discovered Domain

The Discovered domain stores independently observed resource state from provider discovery runs.

**Contract:**
- **Ephemeral snapshot stream** — discovery runs produce fresh snapshots; previous runs are retained for trend analysis and drift history, subject to retention policy. (The durable per-UUID inventory role is exempt — see [four-states](../foundations/four-states.md) §2.4.)
- **Grouped by run** — `discovery_run_uuid` groups all records from a single discovery cycle.
- **Match tracking** — `entity_uuid` links discovered resources to known entities; a null `entity_uuid` indicates an orphan candidate (a resource that exists at the provider but has no entity).
- **Confidence scored** — `match_confidence` indicates how certain the match is (`exact`, `high`, `low`, `unmatched`).
- **Tenant-isolated** — discovered resources inherit tenant from their matched entity or provider.

---

## 3. Audit Record Contract

Audit records have the strictest contract — they are the compliance evidence trail.

**Contract:**
- **Append-only** — no actor may update or delete an audit record, including privileged roles.
- **Tamper-evident (Merkle)** — audit records are the leaves of an RFC 9162 (Certificate Transparency v2.0) Merkle tree — per-leaf signatures, signed tree heads, O(log n) inclusion and consistency proofs (ruling D2; the normative model is [universal-audit](../observability/universal-audit.md) `AUD-006`). Breaking the chain is detectable by verifying inclusion/consistency proofs; a conforming realization exposes a chain-verification operation.
- **Non-repudiable** — every record captures `immediate_actor_uuid`, `authorized_by_uuid`, `session_uuid`, and the complete before/after state.
- **Retention** — minimum P365D across all deployment profiles; `fsi`/`sovereign` profiles may require P2555D (7 years).
- **Separated privilege** — the roles that write audit records may INSERT and SELECT only; no role may UPDATE or DELETE.

*The tamper-evident property means a store restored to a point before the latest audit record produces a detectable chain break; how a realization detects and records that break is operational (see the DCM architecture documentation).*

---

## 4. Tenant Isolation Contract

Every tenant-scoped domain enforces the same isolation contract: **within a given tenant context, a reader or writer can see and modify only that tenant's rows.** Platform administration may operate across tenants, but only through a separately-audited path.

The tenant-scoped domains are: Intent, Requested, Realized, Discovered, Operations, Audit, and the subscription domains. *The mechanism that establishes tenant context (token claims → per-connection tenant binding → row filtering) is realization architecture.*

---

## 5. Sovereignty Partitioning Contract

For deployments spanning multiple sovereignty zones, the contract is: **data does not cross sovereignty boundaries at the store level.**

- Each sovereignty zone's data is bound to a store instance for that zone.
- Cross-zone reads are prohibited — a query in Zone A cannot read data from Zone B.
- Federation between zones uses the peer-realization protocol, which transfers only the minimum data required and is subject to sovereignty policy evaluation.

Store bindings satisfy this per profile ([D1]): a single instance at `homelab`/`standard`; per-zone instances with no cross-zone replication at `sovereign`. *The concrete per-zone deployment topology is realization architecture.*

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
