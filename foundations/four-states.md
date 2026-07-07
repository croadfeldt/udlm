# UDLM — The Four States



**Document Status:** ✅ Complete
**Related Documents:** [Context and Purpose](context-and-purpose.md) | [Entity Relationships](../entities/entity-relationships.md) | [data stores](../contracts/storage-providers.md) | [Audit, Provenance, and Observability](../observability/audit-provenance-observability.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM data model.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: DATA**
>
> The Data abstraction — four lifecycle stages and their storage models



---

## 1. Purpose

The four states are the foundational model for how UDLM tracks the complete lifecycle of any resource or service. Every entity exists in one or more of these states simultaneously. The states are not sequential stages — they are parallel, independently maintained records that together provide a complete, auditable picture of what was requested, what was approved, what was built, and what actually exists.

The four states answer four distinct questions:

| State | Question Answered | Data Domain |
|-------|------------------|-------------|
| **Intent State** | What did the consumer ask for? | Commit Log (intent) — append-only, immutable |
| **Requested State** | What was approved and dispatched to the provider? | State Store (requested) — append-only, immutable |
| **Realized State** | What did the provider actually build? | State Store (realized) — versioned snapshots, `is_current` flag |
| **Discovered State** | What is observed actually existing right now? | Discovered stream — ephemeral, refreshed per discovery run |

> **Store note:** Stores are defined by CONTRACT, not technology ([data-model-core](data-model-core.md) §6, ruling D1). The four states bind to conforming stores per profile and sovereignty/tenancy policy — a single PostgreSQL-compatible database at `standard`/`prod` (the reference implementation), git as a conforming carrier at `minimal`, and per-tenant/zone store instances, WORM audit tiers, or accredited substitutes at `fsi`/`sovereign`. The concrete storage mechanics are realization architecture (see the DCM architecture documentation).

---

## 2. State Definitions

### 2.1 Intent State

The **Intent State** is the immutable record of a consumer's original declaration. It is captured at the moment a request is submitted — before any layer assembly, before any policy evaluation, before any provider selection.

**Characteristics:**
- Immutable once created — the consumer's original intent is never modified
- Stored in a profile-bound Commit Log per the [D1] contract — append-only, versioned, tenant-isolated; git is the conforming carrier at `minimal` and the PR-based ingress at `standard`/`prod`
- Fully versioned — every revision of an intent is traceable
- The entity UUID is assigned at Intent State creation — it follows the entity through all subsequent states

**When created:** Every request submission, every rehydration operation, every drift remediation authorization

**Content:** The consumer's raw declaration in UDLM format — what they want, not what will be built

### 2.2 Requested State

The **Requested State** is the fully assembled, policy-processed, provider-ready payload. It is produced from the Intent State by request assembly — after layer assembly, after all policy evaluation, after provider selection.

**Characteristics:**
- Immutable once created — a new Requested State is created for each request cycle
- Stored in a profile-bound State Store per the [D1] contract — committed, versioned
- Contains the complete assembled payload with full field-level provenance
- Contains the results of all policy evaluations — which policies ran, what they did, what they locked
- Contains provider selection — which provider will realize this request
- Is the authoritative record of what was instructed to be built

**When created:** After Intent State approval, after successful policy processing

**Content:** The complete assembled payload in UDLM format, with full provenance chain, policy evaluation results, provider selection, and override control metadata

### 2.3 Realized State

The **Realized State** is the provider-confirmed record of what was actually built. It is the denaturalized result of the provider's execution, translated back to UDLM format.

**Characteristics:**
- Write-once complete snapshots — each Realized State record is a full entity state, never modified after writing
- Every Realized State record is traceable to exactly one Requested State record — no exceptions
- Contains provider-specific details not in the Requested State — assigned IPs, generated passwords, actual storage sizes, provider-internal IDs
- Is the authoritative record of what actually exists
- Drift is detected by comparing the most recent Realized State snapshot against Discovered State
- Carries a supersession chain — each snapshot knows which snapshot it superseded and which superseded it

**Three write sources (all require a corresponding Requested State record):**

| Source | Requested State record type | Example |
|--------|---------------------------|---------|
| Initial realization | `initial_realization` | Consumer provisions a new VM |
| Consumer update request | `consumer_update` | Consumer patches an editable field |
| Provider update notification | `provider_update` | Provider reports an authorized state change (auto-healing, maintenance) |

**What does NOT write to the Realized store:**
- Drift detection — drift only compares, never writes
- Discovery cycles — discovery writes to the Discovered stream only
- Unsanctioned provider changes — these are drift events until evaluated and explicitly approved

**When created:** When a provider confirms realization of any authorized request (initial, consumer update, or approved provider update notification)

**Content:** Complete entity state snapshot in UDLM format, with provider-added fields, full field-level provenance including provider attribution, and supersession chain references

### 2.4 Discovered State

The **Discovered State** is what is observed actually existing through active discovery — polling providers, querying infrastructure APIs, interrogating resources. It is the ground truth of what physically exists, independent of what the model believes exists.

**Characteristics:**
- Append-only snapshot stream — each discovery cycle produces a new snapshot
- Ephemeral — recent history retained, older snapshots archived or discarded
- High-frequency and machine-generated — not appropriate for human review
- Used exclusively for drift detection — comparing against Realized State
- May contain resources that were never provisioned — brownfield resources discovered for ingestion

**When created:** On every discovery cycle, on demand for specific entities

**Content:** Raw discovered resource state in UDLM format, with discovery metadata (timestamp, discovery method, provider interrogated)

**Raw / unallocated resources (discovered-first entry).** A resource MAY exist with **only** its Discovered State populated and **no Intent** — a freshly racked server, a spare drive, any brownfield asset that physically exists but has not been allocated. This is the **discovered-first** lifecycle entry, the peer of intent-first (declare → realize): the estate ingests the raw resource purely for **inventory and tracking**, carrying `lifecycle_state: available` (unallocated). The resource is later **adopted** — an Intent is attached (allocation / brownfield ingestion), moving it into the managed lifecycle — and adoption **preserves the Entity UUID** (§3), so all inventory history accrues to the same entity.

**Discovered has a dual role (dcm ADR-017 Decision A, #222).** Discovered is (1) the **ephemeral per-cycle snapshot stream** consumed by drift detection, *and* (2) a **durable, per-UUID entity inventory** — the source of truth for *what exists*, including discovered-but-**unclaimed** resources (no provider attached). These are one domain, not two stores: the durable inventory record is the latest reconciled observation per entity; the snapshot stream is its history. The durable-inventory role is exempt from snapshot-stream retention ceilings; the reconciled inventory record persists until claim or retirement ([data-model-core](data-model-core.md) §3). **Unclaimed = inventoried, not managed** (queryable, excluded from lifecycle operations); a provider claim/adoption moves the entity Discovered → Realized preserving its UUID, and a long-lived unclaimed resource is the recorded Antipattern (claim it or retire it). Multiple discovery sources correlate to ONE entity via `correlation_ids` (realized-entity.schema.json; every discovery source MUST emit them). See [SPEC-DESIGN-REQUIREMENTS](../registry/SPEC-DESIGN-REQUIREMENTS.md) §28 and the canonical `lifecycle_state` element (`registry/common-elements.md` §6).

### 2.5 Recovery Conditions — a `status.conditions` overlay, NOT lifecycle states

**Recovery and health are `status.conditions`, not lifecycle states** ([data-model-core](data-model-core.md) §3): `lifecycle_state` never leaves its five canonical values (`Intent → Requested → Realized ↔ Discovered` + `Decommissioned`). When the normal provisioning lifecycle encounters timeouts, cancellation failures, or partial realization on an Infrastructure Resource Entity, the situation is expressed as a **condition type** on the entity's `status.conditions` (realized-entity.schema.json `status`) — an overlay on whatever lifecycle state the entity is in. Conditions are governed by Recovery Policies.

| Condition type | Meaning | Entry Trigger |
|----------------|---------|--------------|
| `TIMEOUT_PENDING` | Dispatch timeout fired; cancellation sent to provider | `DISPATCH_TIMEOUT` recovery trigger |
| `LATE_REALIZATION_PENDING` | Provider responded after timeout; NOTIFY_AND_WAIT active | `LATE_RESPONSE_RECEIVED` recovery trigger |
| `INDETERMINATE_REALIZATION` | State ambiguous; drift detection resolving | `DRIFT_RECONCILE` recovery action |
| `COMPENSATION_IN_PROGRESS` | Compound service rollback underway | `PARTIAL_REALIZATION` trigger |
| `COMPENSATION_FAILED` | Rollback itself failed; orphaned resources possible | Compensation step failure |

The complete recovery-condition machine and Recovery Policy model — how a realization drives these conditions — is realization concern; see the DCM operational model. (Earlier revisions called these "five additional states" — superseded; they never extend the lifecycle enum.)

---

## 3. The Entity UUID — Universal Linking Key

Every entity has a single UUID assigned at Intent State creation. This UUID is the universal key linking the entity across all four states and all stores:

```
Commit Log (intent):     records keyed by entity_uuid
State Store (requested):  records keyed by entity_uuid
State Store (realized):   snapshot stream keyed by entity_uuid
Discovered stream:        snapshot stream keyed by entity_uuid (matched via provider labels)
Audit Store:              all provenance events indexed by entity_uuid
```

Given an entity UUID, the complete history of that entity can be reconstructed across its entire lifecycle — from the consumer's original intent through every state transition to the current discovered state.

---

## 4. The Data Domain Model

All four states are distinct data domains, each with specific immutability rules and access patterns. These immutability contracts are part of the data model; any conforming store binding MUST satisfy them (the concrete enforcement mechanism is realization architecture — see the DCM architecture documentation for the reference PostgreSQL implementation).

| Domain | Immutability contract |
|--------|----------------------|
| **Intent** | Append-only — a new intent creates a new record; previous intents are never modified. Tenant-isolated. |
| **Requested** | Append-only — each policy evaluation produces a new version with full provenance. Tenant-isolated. |
| **Realized** | Versioned snapshots — each state change creates a new record; exactly one is current per entity. Tenant-isolated. |
| **Discovered** | Ephemeral snapshot stream — each discovery run produces fresh snapshots; grouped per discovery run. Tenant-isolated. |

**Audit records** are stored as leaves of an **RFC 9162 (Certificate Transparency v2.0) Merkle tree** — per-leaf signatures, signed tree heads, O(log n) inclusion and consistency proofs (ruling D2; see [universal-audit](../observability/universal-audit.md) `AUD-006`) — append-only with per-entity chain sequence numbers. The Merkle audit model is the data-model audit contract; its storage binding is realization architecture.

**The Realized snapshot model — snapshots, not deltas.** The Realized domain uses a **snapshot model**: each record is a complete entity state, not a delta. This makes rehydration a direct lookup rather than an event replay, and makes point-in-time queries ("what was the state on March 15?") direct lookups. The authoritative snapshot shape is [`realized-entity.schema.json`](../registry/realized-entity.schema.json) (`realized_uuid`, `entity_uuid`, `source_type` + `request_uuid` — mandatory, never nullable — versioning, `is_current`, complete `fields`, and `provider_metadata`).

---

## 5. Rehydration

Rehydration is the process of using a previously stored state record as the starting point for a new request. It is not a shortcut around governance — **all relevant governance policies always apply regardless of rehydration source.** Rehydration is a new request that happens to start from a known prior state.

*This section defines the data-model aspects of rehydration — the sources, the preserved identity, the record shapes, and the mode taxonomy. The rehydration RUNTIME — the governance pipeline, placement re-evaluation, exclusive leases, TTL/concurrency handling, and the tenancy-conflict pause mechanism — is realization concern; see the DCM operational model (`operations/rehydration.md`).*

### 5.1 Three Rehydration Sources

| Source | What is loaded | Layer assembly | Typical use |
|--------|----------------|----------------|-------------|
| **From Intent** | The consumer's original declaration is replayed | Full assembly runs (current layers) | Upgrade to current standards, apply new sovereignty constraints, environment refresh |
| **From Requested** | The previously assembled, policy-processed payload | Skipped (already applied) | Reproduce close to the approved specification |
| **From Realized** | The provider-confirmed payload (provider-specific fields stripped) | Skipped | Exact reproduction for DR, environment cloning, replacing a failed resource |

All three run all current governance policies. Provider selection is configurable (see the four modes below).

### 5.2 Entity UUID Preservation

Entity UUIDs are **preserved on rehydration**. The UUID represents the stable logical identity of the resource across provider migrations, sovereignty changes, and lifecycle events. All external references — CMDB records, cost attribution, audit trails, cross-tenant relationships, dependency declarations — reference the entity by UUID; regenerating it would silently break all of them. What changes on rehydration is the **provider-side identifier** (the actual VM ID, container name, or resource handle), recorded in the rehydration history:

```yaml
entity:
  uuid: <original-uuid>              # PRESERVED across all rehydrations
  rehydration_history:
    - rehydration_uuid: <uuid>
      rehydrated_at: <ISO 8601>
      trigger: <provider_migration|sovereignty_violation|manual|provider_decommission>
      from_provider_uuid: <uuid>
      to_provider_uuid: <uuid>
      from_realized_entity_id: "vm-12345"   # provider's ID — no longer valid
      to_realized_entity_id: "vm-67890"     # new provider's ID after rehydration
      rehydrated_by: <actor-uuid>
      intent_state_ref: <uuid>
      previous_requested_state_ref: <uuid>
      new_requested_state_ref: <uuid>
```

Rehydration is **transactional**: if the target provider cannot accept the entity, the original entity remains in its current state with no UUID change and no partial state.

Every rehydration also records its provenance on the new Intent State: `source_store`, `source_record_uuid`, `rehydration_reason`, `requested_by_uuid`, `rehydration_timestamp`.

### 5.3 Rehydration Constraints

An entity MAY declare a minimum authentication level required to rehydrate it, preventing privilege escalation through the rehydration mechanism:

```yaml
entity:
  rehydration_constraints:
    min_auth_level: hardware_token_mfa
    # Ascending: api_key | ldap_password | oidc | oidc_mfa | hardware_token | hardware_token_mfa
    auth_level_source: <original_provisioning|policy_declared>
    allow_delegated_rehydration: false   # true = authorized service accounts may rehydrate
```

How strictly a realization enforces this is profile-governed (advisory at `standard`, rejecting at `prod`, dual-approval at `fsi`/`sovereign`) — an operational binding, not part of the data model.

### 5.4 The Four Rehydration Modes

Two independent axes — placement and policy version — produce four distinct rehydration configurations:

| Mode | Provider re-evaluated | Policy version | Use Case |
|------|-----------------------|----------------|----------|
| **Faithful** | no | current | Same provider, current governance |
| **Provider-Portable** | yes | current | New provider, current governance |
| **Historical Exact** | no | pinned | Same provider, historical governance (audit evidence) |
| **Historical Portable** | yes | pinned | New provider, historical governance |

Historical (pinned) modes require elevated authorization. **Policies set placement constraints; the placement component selects the provider** — a policy that names a specific provider would be portability-breaking.

### 5.5 Rehydration Tenancy and Sovereignty — always current

**Tenancy controls, sovereignty directives, and cross-tenant authorizations are always evaluated against current policies during rehydration — they cannot be pinned to historical versions.** The `policy_version: pinned` setting governs resource configuration policies only.

```yaml
rehydration:
  policy_version: pinned                 # governs resource configuration policies
  tenancy_controls: always_current       # cannot be pinned
  sovereignty_controls: always_current
  cross_tenant_authorizations: always_current
```

| Policy | Rule |
|--------|------|
| `RHY-001` | Tenancy, sovereignty, and cross-tenant authorizations always use current policies during rehydration — cannot be pinned. |
| `RHY-005` | Entity UUIDs are preserved on rehydration; provider-side identifiers change and are recorded in `rehydration_history`; rehydration is transactional. |

*The remaining rehydration policies (`RHY-002/003/004/006/007/008/010/011/012`) govern the runtime — the PENDING_REVIEW pause, lease acquisition, TTL, concurrency priority, and snapshot-stream retention windows — and live with the DCM operational model.*

---

## 6. Drift Detection

Drift is the difference between what the model believes exists (Realized State) and what actually exists (Discovered State). The drift-detection **runtime** — the comparison cycle, the drift-response actions (REVERT / UPDATE_DEFINITION / ALERT / ESCALATE), and their evaluation — is realization concern (see the DCM operational model). The **drift record shape and severity model** are data model:

A drift record carries `entity_uuid`, `drifted_fields: [{field_path, realized_value, discovered_value}]`, `discovery_timestamp`, and `drift_severity`.

### 6.1 Drift Severity Classification

Drift severity uses the canonical enum **`minor | significant | critical`** ([data-model-core](data-model-core.md) §7, ruling D6) — every drift-severity grading anywhere in the spec resolves to one of these three values. Severity is the highest tier that applies across three independent tiers:

**Tier 1 — Field criticality (declared in the Resource Type Specification):**

```yaml
resource_type_spec:
  fields:
    display_name:      { drift_criticality: minor }        # non-functional change
    cpu_count:         { drift_criticality: significant }
    memory_gb:         { drift_criticality: significant }
    security_group_ids: { drift_criticality: critical }    # security-relevant change
    firewall_rules:    { drift_criticality: critical }
```

**Tier 2 — Profile/layer magnitude thresholds:** a `drift_severity_thresholds` layer may upgrade severity by percentage-change or changed-item-count (e.g. >50% change upgrades `significant` → `critical`).

**Tier 3 — Provider and consumer injection:** providers may *suggest* severity in update notifications (raise only); consumers may *override* sensitivity on specific entities (raise or lower, profile-permitting).

**Resolution rule:** the highest severity across all three tiers wins. Provider injection can raise but not lower the Tier 1/2 result; consumer injection can raise or lower (entity owner controls their own resource's sensitivity). For **multi-field drift**, the overall severity is the highest among all drifted fields. **Unsanctioned changes** are always elevated one level above the resolved result.

### 6.2 Unsanctioned Changes

An **unsanctioned change** is a change made directly to a resource without a corresponding request — any Discovered State field value that differs from Realized State with no Requested State record explaining it. It is a data-model category (a discovered delta with no request provenance); how a realization detects and responds to it is operational.

---

## 7. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should the entity UUID be preserved or regenerated on rehydration? | Entity identity | ✅ Resolved — UUID preserved; `rehydration_history` records provider-side ID changes; transactional (RHY-005) |
| 2 | Should the Discovered stream retain full history or only a configurable window? | Retention | ✅ Resolved — snapshot-stream retention is profile-governed (operational); the durable per-UUID inventory record is exempt and persists until claim/retirement (RHY-008) |

---

## 8. Related Concepts

- **data store** — the formal provider type for all stores
- **Entity UUID** — the universal linking key across all four states
- **Rehydration** — using a prior state record as the starting point for a new request (data-model aspects here; runtime in the DCM operational model)
- **Provider-Portable Rehydration** — rehydration with provider selection re-evaluated
- **Drift Detection** — comparing Realized State against Discovered State
- **Unsanctioned Change** — a discovered resource modification with no corresponding request

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
