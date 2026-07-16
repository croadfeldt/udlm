# UDLM — Storage Providers

**Document Status:** ✅ Complete
**Related Documents:** [Data Store Contracts](data-store-contracts.md) | [Provider Contract](provider-contract.md) | [Four States](../foundations/four-states.md) | [Audit, Provenance, and Observability](../observability/audit-provenance-observability.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM data model — the **Provider**
> abstraction ([foundations.md](../foundations/foundations.md)), specialized for storage.
>
> **Scope (ADR-008 boundary).** This document is the *contract* a storage provider satisfies: the
> capability it declares, the obligations it must meet, and the store sub-profiles it may occupy. The
> **portable store invariants** (write-once realized, append-only audit, caches-are-projections) are owned
> by [data-store-contracts.md](data-store-contracts.md); the **concrete store mechanisms** (Git/Kafka/search
> engines, file layouts, replication and migration topology, failure handling) are realization architecture,
> owned by the DCM architecture docs. A peer that persists the same data under the same invariants, by any
> mechanism, conforms.

---

## 1. Purpose

In the unified provider model ([capability-discovery.md](capability-discovery.md); ADR-PROV-002), a
**Storage Provider** is *not* a provider type — it is a provider that declares the **`realize_resources`
capability over the `Storage` domain** (the `realize_resources/Storage`, *storage-provisioning*, capability
category), and typically **`serve_data`** over what it stores as well. It is the interface through which a
realization persists, retrieves, and streams state data. The contract defines *what* each store must
guarantee; the implementation technology is a deployment choice. A provider MAY declare storage capabilities
alongside others; fixed provider *types* are superseded by capability declarations, and "Storage Provider"
is the convenience label for this capability profile.

The framework does not prescribe technology — it defines what is required and what is guaranteed. An
organization using GitHub and Kafka satisfies the same contracts as one using Gitea and EventStoreDB.

---

## 2. Store sub-profiles

There are no provider *types* in the unified model — a provider declares capabilities (verb × domain) and
occupies the **capability categories** they form ([capability-discovery.md](capability-discovery.md) §2.4;
ADR-PROV-002). "Storage Provider" is the convenience label for a provider in the `realize_resources/Storage`
category. Within storage, four **store sub-profiles** are defined, each optimized for a different access
pattern and consistency requirement (a provider may occupy several):

| Store sub-profile | What it holds | Portable invariant (owned by data-store-contracts.md) |
|---|---|---|
| **GitOps store** | Intent / Requested state | deterministic, handle-addressable, diff-readable, independently verifiable |
| **Write-once snapshot store** (Realized) | Realized-state snapshots | immutable, versioned, write-once (§ data-store-contracts §2.3) |
| **Event stream store** | State-change events | append-only, ordered, retention-bounded |
| **Search index** | Queryable projection | **non-authoritative, rebuildable** — never ground truth (D1) |
| **Audit store** | Provenance / audit records | append-only, tamper-evident (Merkle), § observability |

The **invariant** each must uphold is owned by [data-store-contracts.md](data-store-contracts.md). The
**concrete API, file layout, wire envelope, retention mechanism, replication and failure topology** for each
store are realization architecture — specified in the DCM architecture docs, not here.

---

## 3. Storage Provider contract — base requirements

A Storage Provider is a Provider ([provider-contract.md](provider-contract.md)); it inherits registration,
health check, and trust from the base contract. Two obligations are storage-specific and are the substance
of *this* contract:

### 3.1 Registration (base + storage extension)
Registration follows the base Provider model ([provider-contract.md](provider-contract.md) §2) — endpoint,
capabilities, sovereignty, and **attestation evidence** (trust is *not* self-declared: `trust_posture` is
assigned in the registration verdict, not stated by the provider; ADR-022). The storage extension adds
`store_type` (`gitops | write_once_snapshot | event_stream | search_index | audit | observability`) and the
consistency declaration (§3.3).

### 3.2 Provenance emission obligation
Every Storage Provider that holds state data has a **contractual obligation** to emit a provenance event to
the audit store on every write or modification. This is not optional — it is part of the Storage Provider
contract.

```yaml
# Provenance emission event — emitted to the audit store on every write
provenance_emission:
  store_type: <store type>
  operation: <write|update|delete|merge|commit>
  entity_uuid: <entity UUID affected>
  record_uuid: <UUID of the specific record written>
  actor_uuid: <UUID of the actor that triggered the write>
  timestamp: <ISO 8601>
  payload_hash: <cryptographic hash of the written payload>
  store_reference: <store-specific reference — commit hash, event ID, etc.>
```

### 3.3 Consistency guarantee declaration
Each Storage Provider MUST declare its consistency model at registration; consumers read this declaration
and adapt their behavior accordingly.

```yaml
consistency_declaration:
  consistency_model: <strong|eventual|linearizable>
  replication_factor: <integer>
  durability_guarantee: <fsync|replicated|acknowledged>
  max_data_loss_window: <duration — e.g., PT0S for zero data loss>
```

Multi-region replication is a **declared capability** in registration (a profile sets the minimum), not a
fixed requirement; how a store replicates, fails over, or migrates is realization architecture.

---

## 4. Caches are realization-internal

A realization MAY maintain internal performance caches in front of the authoritative stores. The only
data-model invariant is the one from D1: **caches are non-authoritative projections** — the authoritative
store always wins, a cache hit is never ground truth, and any cache is rebuildable from its authoritative
store. Cache topology, patterns (cache-aside, invalidation-on-write), staleness windows, and which
components cache what are realization concerns (see the DCM architecture docs) — they require no
registration or trust and are not Storage Providers.

---

## 5. Storage Provider vs Service Provider — key differences

| Dimension | Service Provider | Storage Provider |
|-----------|-----------------|-----------------|
| **Purpose** | Realizes resources | Persists state |
| **Data direction** | Platform sends, provider executes | Platform reads and writes |
| **Naturalization** | Required — data-model format → native | Not required — data-model format throughout |
| **Denaturalization** | Required — native → data-model format | Not required |
| **Provenance emission** | Required (realized state) | Required (all writes) |
| **Capacity model** | Resource capacity | Storage capacity and throughput |
| **Health model** | Is provider healthy? | Is store reachable and consistent? |

---

## 6. Sovereignty

A Storage Provider declares its sovereignty like any other provider. The `sovereignty_declaration`
*structure* is shared across all provider kinds; consolidating it into a single home
([provider-contract.md](provider-contract.md)) is tracked as an open dedup ruling (A4) and is deliberately
**not** pre-empted here. The provider-sovereignty policies (homed here until A4 lands) are:

| ID | Policy |
|----|--------|
| `SOV-001` | All provider registrations must include a `sovereignty_declaration` covering operating jurisdictions, legal frameworks, data-residency guarantees, external dependencies, certifications with validity periods, and government-access risk. |
| `SOV-002` | Providers must notify the platform when any declared sovereignty data changes; a sovereignty change is treated as discovered drift and triggers policy re-evaluation. The notification SLA is declared at registration. |
| `SOV-003` | When a provider sovereignty change violates a Tenant's sovereignty requirements, affected resources are re-evaluated and the declared action applied: `notify_only`, `pause`, `migrate`, or `emergency_migrate`. |
| `SOV-004` | Auto-migration triggered by SOV-003 uses provider-portable rehydration; the non-compliant provider is excluded from the placement candidate set, and the migration is a first-class, fully-audited operation. |
| `SOV-005` | Certification validity periods are tracked; a certification expiring within P30D warns the provider and affected Tenants, and an expired certification triggers SOV-003 re-evaluation. |

Storage-specific: a store holding state in a jurisdiction that falls out of compliance is a **data-at-rest**
sovereignty incident. SOV-002/003/004 state the *policy*; *how* a realization executes the response (pause,
migrate, quarantine) is control-plane, owned by the DCM architecture docs.

---

## 7. System policies (storage)

These profile-governed policies are UDLM data (a profile tightens them); the *mechanism* by which a
realization enforces them is DCM.

| ID | Policy |
|----|--------|
| `STO-001` | Storage Providers must declare replication capabilities. The active profile determines the minimum replication requirement; a provider below the profile minimum cannot be activated for that profile's stores. |
| `STO-002` | Storage Provider failure behavior is declared per store sub-profile and governed by the active profile: writes are queued, never silently dropped; a quorum loss on a strongly-consistent store aborts the triggering operation; audit unavailability accumulates rather than loses; a search-index outage degrades queries without impacting writes. The concrete per-store handling is realization architecture (DCM). |
| `STO-003` | The Search Index is a distinct store sub-profile — non-authoritative and rebuildable. A query may request `freshness: authoritative` to bypass the index. |

---

## 8. What is specified elsewhere (moved from this document)

To keep one home per concern, the following are **not** in this contract:

- **Portable store invariants** (write-once realized store, append-only audit, store-by-contract,
  audit-record-vs-object-history) → [data-store-contracts.md](data-store-contracts.md).
- **Concrete store mechanisms** — GitOps repo layout and APIs, event-stream naming/envelope/retention,
  snapshot-store APIs, search-index fields/queries, multi-region replication and failure-handling topology,
  auto-migration flow → the **DCM architecture docs** (realization architecture; a peer implements them
  differently and still conforms).
- **Sovereignty declaration structure + change response** → [provider-contract.md](provider-contract.md).
- **Storage-architecture system policies** (`STO-*`, `SOV-*`) → the policy store; this document does not
  restate them.
