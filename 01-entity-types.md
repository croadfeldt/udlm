# DCM Data Model — Entity Types


**Document Status:** ✅ Complete
**Document Type:** Architecture Reference

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA**
>
> The Data abstraction — typed entity extensions (Infrastructure Resource, Composite, Process)


**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Four States](02-four-states.md) | [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md)

---

## 1. Purpose

This document defines the complete taxonomy of entity types in DCM. Every resource, service, group, and process managed by DCM is an entity — and every entity belongs to one of the types defined here. The entity type determines the lifecycle state machine, the ownership model, the decommission behavior, and which data model fields are applicable.

Understanding entity types is prerequisite to understanding:
- How lifecycle states are assigned and transition
- How ownership and allocation interact
- How drift detection operates at different levels
- How decommission cascades through dependent entities

---

## 2. The Three Primary Entity Types

DCM defines three primary entity types. Every entity is exactly one of these.

### 2.1 Infrastructure Resource Entity

An **Infrastructure Resource Entity** is a realized physical or virtual infrastructure resource that persists across time and has a full operational lifecycle.

**Characteristics:**
- Persists after provisioning — it continues to exist and consume resources until explicitly decommissioned
- Owned by exactly one Tenant at any point in time
- Has a full bidirectional lifecycle including OPERATIONAL and SUSPENDED states
- Subject to drift detection — its Realized State is continuously compared against Discovered State
- Subject to TTL management — may declare an expiry after which decommission is triggered
- May have relationships to other entities — dependencies, attachments, allocations, business data
- Carries field-level provenance across its full lifecycle

**Lifecycle State Machine:**

```
                    ┌─────────────────────────────────┐
                    │          REQUESTED               │
                    │  (Intent State assembled,        │
                    │   Requested State committed)     │
                    └───────────────┬─────────────────┘
                                    │  Provider dispatch
                                    ▼
                    ┌─────────────────────────────────┐
                    │           PENDING                │
                    │  (Awaiting provider capacity     │
                    │   or dependency resolution)      │
                    └───────────────┬─────────────────┘
                                    │  Provider begins work
                                    ▼
                    ┌─────────────────────────────────┐
                    │         PROVISIONING             │
                    │  (Provider actively realizing)   │
                    └───────────────┬─────────────────┘
                                    │  Provider confirms realization
                                    ▼
                    ┌─────────────────────────────────┐
                    │           REALIZED               │
                    │  (Provider-confirmed, DCM has    │
                    │   full Realized State record)    │
                    └───────────────┬─────────────────┘
                                    │  Passes health checks
                                    ▼
                    ┌─────────────────────────────────┐   ◄── Primary operational state
                    │         OPERATIONAL              │   Drift detection active
                    │  (Active, healthy, in use)       │   Cost analysis active
                    └───┬───────────────────┬─────────┘   Policy evaluation active
                        │                   │
              Suspend   │                   │  Decommission request
              request   ▼                   ▼
            ┌──────────────────┐  ┌──────────────────────┐
            │   SUSPENDED      │  │   DECOMMISSIONING     │
            │ (Paused, not in  │  │ (Provider removing,   │
            │  active use,     │  │  dependencies         │
            │  may be billed   │  │  being released)      │
            │  at reduced rate)│  └──────────┬───────────┘
            └────────┬─────────┘             │
                     │  Resume               │  Provider confirms removal
                     │  or decommission      ▼
                     │             ┌──────────────────────┐
                     └─────────────►   DECOMMISSIONED      │  ◄── Terminal state
                                   │ (Removed from infra,  │
                                   │  audit records        │
                                   │  preserved)           │
                                   └──────────────────────┘

Any state except DECOMMISSIONED:
  PROVISIONING_FAILED → rolls back to REQUESTED or terminal FAILED
  PENDING_REVIEW → sovereignty/tenancy conflict during rehydration (see Section 2.1.2)
```

**Applicable to:** VirtualMachine, VLAN, IPAddress, StorageVolume, Container, LoadBalancer, DNSRecord, FirewallRule, NetworkPort, Subnet, and all other persistent infrastructure resource types.

#### 2.1.1 Infrastructure Resource Entity Data Model

```yaml
infrastructure_resource_entity:
  # Universal artifact metadata
  uuid: <uuid>                          # stable across full lifecycle including rehydration
  handle: <string>                      # human-readable stable identifier
  resource_type: <fqn>                  # e.g., Compute.VirtualMachine
  resource_type_spec_version: <semver>
  lifecycle_state: <REQUESTED|PENDING|PROVISIONING|REALIZED|OPERATIONAL|
                    SUSPENDED|DECOMMISSIONING|DECOMMISSIONED|FAILED|PENDING_REVIEW>
  created_at: <ISO 8601>
  updated_at: <ISO 8601>

  # Ownership
  owned_by_tenant_uuid: <uuid>          # exactly one Tenant; mandatory
  created_by_actor_uuid: <uuid>

  # Ownership model — see doc 04b
  ownership_model: <whole_allocation|allocation|shareable>
  # whole_allocation: consumer owns this entity outright
  # allocation:       this entity is an allocation carved from a pool (consumer owns it)
  # shareable:        consumer has a stake; ownership remains with pool owner

  # If this is an allocation from a pool resource
  allocated_from_pool_uuid: <uuid>      # UUID of the pool entity; null if not an allocation
  allocation_ref_uuid: <uuid>           # UUID of the AllocationRecord relationship

  # If this is a shareable stake
  shared_resource_uuid: <uuid>          # UUID of the shared resource; null if not a stake

  # Provider details (populated after REALIZED)
  provider_uuid: <uuid>
  provider_entity_id: <string>          # provider's own identifier (e.g., "vm-12345")
  provider_entity_id_history: [...]     # history of provider IDs (rehydration changes these)

  # Lifecycle constraints
  ttl: <ISO 8601 duration|null>
  ttl_expires_at: <ISO 8601|null>
  on_expiry: <decommission|suspend|notify|escalate>
  billing_state: <billable|non_billable|reduced_rate>

  # Rehydration
  rehydration_constraints:
    min_auth_level: <level>
    allow_delegated_rehydration: <bool>
  rehydration_history: [...]

  # Drift tracking
  last_discovered_at: <ISO 8601|null>
  drift_status: <clean|drifted|unknown>
  last_drift_severity: <minor|significant|critical|null>

  # Relationships (see doc 09)
  relationships: [...]

  # Field-level provenance on all data fields (see doc 00, Section 4)
  # [all resource-type-specific fields carry provenance metadata]
```

#### 2.1.2 PENDING_REVIEW State

`PENDING_REVIEW` is a formal lifecycle state for Infrastructure Resource Entities (not Process Resources). An entity enters `PENDING_REVIEW` when an automated operation detects a conflict that requires human resolution before the operation can proceed:

| Trigger | Description |
|---------|-------------|
| Rehydration sovereignty conflict | Rehydration discovers the target provider no longer satisfies the entity's sovereignty constraints |
| Cross-tenant authorization revoked | An authorization enabling a cross-tenant resource reference was revoked while the resource is still allocated |
| Ownership transfer conflict | An ownership transfer request conflicts with active relationships that prevent transfer |

An entity in `PENDING_REVIEW`:
- Is not actively drifting from its Realized State (the underlying resource is unchanged)
- Has an active `pending_review_record` on the entity with trigger, timestamp, and resolution options
- Generates notifications to the entity owner, Tenant admin, and platform admin
- Remains in `PENDING_REVIEW` until a resolution action is taken (re_authorize, release, escalate, or manual override)
- Is never automatically resolved — all resolutions require explicit human or policy authorization

### 2.2 Composite Resource Entity

A **Composite Resource Entity** is produced by a compound resource type specification that orchestrates multiple constituent Infrastructure Resource Entities to deliver a higher-order service. The composite is a first-class entity — it has its own UUID, Tenant ownership, and lifecycle. Its constituents each retain their own entity identity.

**Characteristics:**
- Represents the logical aggregate, not a physical resource
- Owned by exactly one Tenant (the Tenant that requested the composite service)
- Constituents may be owned by the same Tenant or may be allocations/stakes in pool resources owned by another Tenant
- Drift detection operates at two levels: the composite level (is the composite healthy as a whole?) and the constituent level (is each underlying resource still in its expected state?)
- Decommission is staged: composite decommissioned first, then constituents in reverse dependency order

**Lifecycle state machine:** Same as Infrastructure Resource Entity. The composite's `lifecycle_state` reflects the aggregate health of all constituents — a composite is OPERATIONAL only when all required constituents are OPERATIONAL.

**Constituent relationship:** Each constituent is recorded as a `constituent_of` relationship from the constituent to the composite. The composite holds `has_constituent` relationships to each constituent. The composite UUID is the correlation key across all constituent audit records.

```yaml
composite_resource_entity:
  uuid: <uuid>
  resource_type: <fqn>                  # e.g., ApplicationStack.WebApp
  lifecycle_state: <same as Infrastructure>
  owned_by_tenant_uuid: <uuid>
  composition_visibility: <opaque|transparent|selective>
  # opaque:      consumers see composite only; constituents hidden
  # transparent: consumers see composite and all constituents
  # selective:   policy declares which constituents are visible

  constituents:
    - constituent_entity_uuid: <uuid>
      role: <primary|supporting|optional>
      required_for_composite_operational: <bool>
      # If a required constituent fails, the composite enters DEGRADED
      constituent_lifecycle_state: <mirrors constituent entity>
  composite_health: <healthy|degraded|failed>
```

### 2.3 Process Resource Entity

A **Process Resource Entity** represents an ephemeral execution — an automation job, playbook, pipeline, workflow, or script execution. It does not persist after completion. Its lifecycle is terminal-focused: every Process Resource Entity ends in either COMPLETED, FAILED, or CANCELLED.

**Characteristics:**
- Does not persist after reaching a terminal state — no ongoing Realized State to manage
- Must declare `max_execution_time` — mandatory, not optional
- If max_execution_time is exceeded, the process enters FAILED state and DCM generates a `PROCESS_TIMEOUT` event
- If the process modifies any Infrastructure Resource Entity, it must record the modified entity UUIDs in its provenance
- Owned by the Tenant that initiated the execution
- Subject to audit — every process execution produces a full audit trail

**Lifecycle state machine:**

```
REQUESTED → INITIATED → EXECUTING → COMPLETED (terminal)
                                  → FAILED     (terminal)
                                  → CANCELLED  (terminal — requires explicit cancel request)
```

No SUSPENDED state. No PENDING_REVIEW state. Process Resources are ephemeral — they do not enter states that require ongoing management.

```yaml
process_resource_entity:
  uuid: <uuid>
  resource_type: <fqn>                  # e.g., Automation.AnsiblePlaybook
  lifecycle_state: <REQUESTED|INITIATED|EXECUTING|COMPLETED|FAILED|CANCELLED>
  owned_by_tenant_uuid: <uuid>
  created_by_actor_uuid: <uuid>

  max_execution_time: <ISO 8601 duration>  # mandatory
  started_at: <ISO 8601|null>
  completed_at: <ISO 8601|null>
  execution_timeout_at: <ISO 8601|null>   # computed: started_at + max_execution_time

  # Entities this process modified (mandatory if any modifications made)
  affected_entity_uuids: [<uuid>, ...]

  # Execution details
  provider_uuid: <uuid>                 # which automation provider executed this
  provider_job_id: <string>             # provider's own job identifier
  exit_status: <success|failure|timeout|cancelled|null>
  execution_log_ref: <uuid|null>        # reference to log store entry

  # Provenance on all execution parameters carries field-level lineage
```

---

## 3. Sub-Types and Specializations

### 3.1 Shared Resource Entity (Infrastructure Resource sub-type)

A **Shared Resource Entity** is an Infrastructure Resource Entity where multiple consumers hold stakes — references, attachments, or dependencies — without any consumer owning an allocation of the resource. The resource has a single owner (typically a platform or network operations Tenant). Consumers reference it through relationships.

See [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md) for the complete model.

**Examples:** VLAN, NetworkSegment, SharedStorageCluster, DNS Zone, NTP Server, Certificate Authority.

**Key property:** `ownership_model: shareable`

Decommission is deferred while any active stakeholder relationships exist. The `minimum_relationship_count` on the resource type spec declares the safe minimum — typically 0 (can be decommissioned when all stakes are released) but may be higher for infrastructure that must always have at least one consumer.

### 3.2 Allocatable Pool Resource (Infrastructure Resource sub-type)

An **Allocatable Pool Resource** is an Infrastructure Resource Entity that serves as a pool from which consumers receive owned allocations. The pool itself is owned by a platform Tenant. Each allocation request produces a new, independently owned Infrastructure Resource Entity carved from the pool.

See [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md) for the complete model.

**Examples:** IPAddressPool (allocates IPAddress entities), SubnetPool (allocates Subnet entities), VLANPool (allocates VLAN entities), StoragePool (allocates StorageVolume entities).

**Key property:** `ownership_model: whole_allocation` on the pool entity; allocation products have `ownership_model: allocation`.

The pool tracks available capacity. Allocation requests go through the placement engine like any other resource request. The produced allocation entity is owned by the requesting Tenant.

---

## 4. Entity Identity Invariants

These invariants apply to all entity types without exception:

| Invariant | Rule |
|-----------|------|
| UUID stability | An entity's UUID never changes across its full lifecycle, including rehydration and provider migration |
| Single Tenant ownership | Every Infrastructure Resource Entity and Process Resource Entity is owned by exactly one Tenant at all times |
| Composite constituent ownership | A Composite Resource Entity's constituents are owned individually — the composite UUID does not override constituent Tenant ownership |
| Immutable Realized State | Realized State events are append-only; a new event is created for every state change |
| Audit trail preservation | Audit records for an entity are never destroyed while any related entity is active; preservation policy governs post-terminal retention |
| Provider ID separation | The entity UUID is the DCM stable identity; the provider entity ID is the provider's own reference. These are separate and the provider ID may change on rehydration |

---

## 5. Entity Type to Resource Type Mapping

Not all resource types produce the same entity type. The entity type is declared in the Resource Type Specification:

```yaml
resource_type_spec:
  fqn: Compute.VirtualMachine
  entity_type: infrastructure_resource   # infrastructure_resource | composite_resource | process_resource
  ownership_model: whole_allocation       # whole_allocation | allocation | shareable
  allocatable_from_pool_type: null        # if allocation: the pool resource type this comes from
  pool_resource_type: null                # if pool: declare this is a pool resource
  shareable: false                        # if shareable: true
```

---

## 6. Related Policies

| Policy | Rule |
|--------|------|
| `ENT-001` | Every Infrastructure Resource Entity must be owned by exactly one Tenant at all times |
| `ENT-002` | Process Resource Entities must declare max_execution_time — this field has no default and is not optional |
| `ENT-003` | Process Resource Entities must record all affected entity UUIDs if any infrastructure modifications are made during execution |
| `ENT-004` | Composite Resource Entity lifecycle_state reflects aggregate constituent health — OPERATIONAL only when all required constituents are OPERATIONAL |
| `ENT-005` | PENDING_REVIEW is a valid Infrastructure Resource Entity state requiring human resolution — it is never an error state and never automatically resolved |
| `ENT-006` | The entity UUID is immutable across the full entity lifecycle including rehydration, provider migration, and ownership transfer |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
