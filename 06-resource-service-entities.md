# DCM Data Model — Resource/Service Entities



**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Operational Models](24-operational-models.md) | [Entity Types](01-entity-types.md) | [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md) | [Layering and Versioning](03-layering-and-versioning.md) | [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Service Dependencies](07-service-dependencies.md) | [Resource Grouping](08-resource-grouping.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA + PROVIDER**
>
> Data: entity lifecycle. Provider: lifecycle events and update notifications



---

## 1. Purpose

This document defines the two fundamental transactional concepts in DCM — the **Resource/Service Request** and the **Resource/Service Entity** — and establishes the ownership models, lifecycle principles, and provider relationship rules that govern them.

Understanding the distinction between a Request and an Entity, and understanding DCM's role as the authoritative owner of all resource data regardless of operational ownership, is essential to understanding how DCM achieves its core goals of auditability, lifecycle management, and sovereignty.

---

## 2. Core Terminology

### 2.1 Resource/Service Request

A **Resource/Service Request** is what a consumer submits to DCM — the declared intent to consume a resource or service. It is the consumer side of the transaction.

- Created when a consumer submits a request via the Web UI or Consumer API
- Captured as the **Intent State** before any processing
- Processed into the **Requested State** after assembly and policy validation
- Is the initiating event that causes a Resource/Service Entity to be created

A Request is not a thing — it is an **instruction**. It describes what the consumer wants. The provider acts on the Requested State to produce an Entity.

### 2.2 Resource/Service Entity

A **Resource/Service Entity** is the "thing" produced by a provider as a result of fulfilling a Resource/Service Request. It is the provider side of the transaction — the allocation made real.

- Created when a provider fulfills a Requested State payload
- Returned to DCM in unified data model format via Denaturalization
- Captured as the **Realized State** in the Realized Store
- Assigned to a **DCM Tenant** — the ownership boundary
- Has a UUID, full provenance chain, and complete lifecycle from creation to decommission
- Is the unit of consumption, cost attribution, drift detection, and audit in DCM

A Resource/Service Entity IS a thing — it exists, it has state, it has an owner, and DCM manages its lifecycle.

### 2.3 The Critical Distinction

```
Consumer submits        →  Resource/Service REQUEST  →  Intent/Requested State
Provider fulfills       →  Resource/Service ENTITY   →  Realized State
DCM manages lifecycle   →  ENTITY persists            →  Drift/Audit/Cost/Rehydration
```

---

## 3. DCM as Authoritative Owner of All Resource Data

This is the most fundamental principle governing Resource/Service Entities:

**DCM is ALWAYS the system of record for Resource/Service Entity data. DCM is ALWAYS authoritative for the resource definition. DCM ALWAYS owns the lifecycle. This applies regardless of the operational ownership model.**

The operational ownership model (described in Section 4) determines who has authority to operate on a Resource/Service Entity. It does not affect DCM's data ownership. Specifically:

- DCM owns the **data definition** of every Resource/Service Entity — what it is, what it should be, what it was
- DCM owns the **lifecycle** — from Requested through Realized to Decommissioned
- DCM is **authoritative** — if a provider reports a change DCM was not aware of, DCM acts on it according to policy
- DCM acts as the **Tenant advocate** — it protects the Tenant's interests in all provider interactions
- Providers are **custodians** of the underlying infrastructure — they are not the system of record

**When a provider reports an unsanctioned change:**

If a provider reports a state change that was not initiated by a DCM request, the Policy Engine evaluates the change and determines the appropriate response:

| Response | Description |
|----------|-------------|
| `ALERT` | Notify appropriate personas — Tenant owner, SRE, Auditor |
| `REVERT` | Instruct provider to revert to DCM-declared realized state |
| `UPDATE_DEFINITION` | Accept the change and update the realized state definition |
| `INVESTIGATE` | Flag for human review before action |
| `DECOMMISSION` | Initiate decommission if the change represents unrecoverable deviation |
| `ESCALATE` | Escalate to higher policy tier for decision |

The response is determined by Policy Engine evaluation against:
- The Resource/Service definition
- Service/Resource dependencies
- Consumer preferences
- Organizational and Tenant policies
- Sovereignty requirements

---

## 4. Ownership Models

DCM supports four ownership models for Resource/Service Entities. Every Provider Catalog Item must declare which ownership model(s) it supports. The ownership model is recorded in the Resource/Service Entity's provenance at creation time.

### 4.1 Allocation Model

The provider retains internal ownership of the underlying infrastructure. The consumer owns the Resource/Service Entity (the allocation) in their DCM Tenant. The provider can reclaim the underlying resource when the entity is decommissioned.

**Characteristics:**
- Provider retains asset ownership
- Consumer owns the allocation — the Entity in their DCM Tenant
- Provider has reclaim rights on decommission
- Underlying infrastructure may be shared or subdivided
- DCM manages the Entity lifecycle; provider manages the underlying resource

**Examples:** Virtual Machine, Container, Network Port, IP Address, Firewall Rule, Database Instance

---

### 4.2 Whole Allocation Model

The entire physical or logical resource is allocated as a single indivisible unit to one consumer's DCM Tenant. The provider retains internal ownership but the consumer has exclusive use of the whole resource. The resource cannot be subdivided or shared during the allocation period.

**Characteristics:**
- Provider retains asset ownership
- Consumer has exclusive, indivisible use
- The resource is not shared or subdivided
- Provider has reclaim rights on decommission
- DCM manages the Entity lifecycle

**Examples:** Dedicated Bare Metal server (provider-owned), Dedicated Network appliance, Whole storage array allocation

---

### 4.3 Full Transfer Model

The provider transfers complete ownership of the underlying resource to the consumer's DCM Tenant. The Resource/Service Entity IS the resource — there is no separation between the allocation and the underlying infrastructure from DCM's perspective. The consumer controls the full lifecycle including decommissioning. The provider has no reclaim rights after transfer.

**Characteristics:**
- Ownership of the underlying resource transfers to consumer's DCM Tenant
- The Entity IS the resource — no allocation/infrastructure separation
- Consumer controls full lifecycle including decommission
- Provider has no reclaim rights post-transfer
- Transfer is recorded in provenance — permanent audit record
- DCM remains authoritative for data and lifecycle regardless of transfer

**Examples:** Transferred Bare Metal server, Licensed software asset, Dedicated hardware appliance transferred to consumer

---

### 4.4 Hybrid Transfer Model

Ownership can transfer multiple times across the lifecycle of the Resource/Service Entity. The current owner is always exactly one DCM Tenant, but ownership can be formally reassigned through a DCM-governed ownership transfer process. Every transfer is tracked, auditable, and policy-governed.

**Characteristics:**
- Ownership is held by exactly one DCM Tenant at any point in time
- Ownership can be transferred to another DCM Tenant through a formal DCM process
- Every transfer is recorded in the Entity's provenance chain — complete ownership history
- Transfer requires Policy Engine validation and authorization
- The receiving Tenant must accept the transfer — it cannot be forced
- DCM remains authoritative for data and lifecycle through all transfers

**Transfer Provenance Record:**
```yaml
ownership_transfer:
  sequence: <transfer number — 1 for first transfer, 2 for second, etc.>
  from_tenant_uuid: <uuid of transferring tenant>
  to_tenant_uuid: <uuid of receiving tenant>
  transfer_timestamp: <ISO 8601>
  authorized_by: <uuid of authorizing policy or persona>
  transfer_reason: <human-readable reason>
  policy_uuid: <uuid of policy that governed this transfer>
```

**Examples:** Bare Metal server reallocated between tenants, Hardware asset transferred between business units, Licensed resource reassigned

---

### 4.5 Ownership Model Declaration

Every Provider Catalog Item must declare the ownership model(s) it supports:

```yaml
catalog_item:
  uuid: <uuid>
  ownership_models_supported:
    - allocation
    - whole_allocation
    - full_transfer
    - hybrid_transfer
  default_ownership_model: <one of the above>
  transfer_policy_required: <true|false>
  # If true, a policy must be referenced in any transfer request
```

---

## 5. Resource/Service Entity Lifecycle

Every Resource/Service Entity progresses through a defined lifecycle. The lifecycle states are:

```
REQUESTED → PENDING → PROVISIONING → REALIZED → OPERATIONAL
                                                      │
                                          ┌───────────┼───────────┐
                                          ▼           ▼           ▼
                                      DEGRADED   MAINTENANCE  SUSPENDED
                                          │           │           │
                                          └───────────┼───────────┘
                                                      ▼
                                                DECOMMISSIONING
                                                      │
                                                      ▼
                                                DECOMMISSIONED
```

| State | Description |
|-------|-------------|
| `REQUESTED` | Request submitted, Intent State captured |
| `PENDING` | Requested State assembled, awaiting provider dispatch |
| `PROVISIONING` | Provider is fulfilling the request |
| `REALIZED` | Provider has fulfilled the request, Entity exists, Realized State captured |
| `OPERATIONAL` | Entity is in active use |
| `DEGRADED` | Entity is functioning but below expected operational characteristics |
| `MAINTENANCE` | Entity is undergoing planned maintenance |
| `SUSPENDED` | Entity is temporarily suspended — not operational but not decommissioned |
| `DECOMMISSIONING` | Decommission process initiated |
| `DECOMMISSIONED` | Entity no longer exists. Record retained permanently for audit. |

**Terminal states:** `DECOMMISSIONED` is the only terminal state. Once decommissioned, the Entity record is immutable and retained permanently.

---

## 6. Process Resource Entities

A **Process Resource Entity** is a distinct class of Resource/Service Entity representing ephemeral execution resources — automation jobs, playbooks, pipelines, workflows, and similar process-oriented resources.

### 6.1 Characteristics

- **Ephemeral lifecycle** — exists for the duration of execution, then terminates
- **No ongoing realized state to manage** — lifecycle ends at COMPLETED or FAILED
- **Execution record retained permanently** — the record of what the process did is immutable and permanent
- **Must belong to a DCM Tenant** — even ephemeral resources must be owned
- **Must be in the provenance chain** of any Resource/Service Entity they affect

### 6.2 Process Resource Lifecycle

```
REQUESTED → INITIATED → EXECUTING → COMPLETED
                                  → FAILED
                                  → CANCELLED
```

| State | Description |
|-------|-------------|
| `REQUESTED` | Process request submitted |
| `INITIATED` | Provider has begun execution |
| `EXECUTING` | Process is actively running |
| `COMPLETED` | Process completed successfully — terminal |
| `FAILED` | Process failed — terminal |
| `CANCELLED` | Process cancelled before completion — terminal |

All terminal states are permanent. The execution record is immutable after reaching a terminal state.

### 6.3 Process Resource Entity Data Model

```yaml
process_resource_entity:
  uuid: <uuid>
  entity_class: process
  process_type: <playbook|workflow|pipeline|automation_job|script|other>
  tenant_uuid: <owning tenant uuid>
  version: <Major.Minor.Revision>
  lifecycle_state: <REQUESTED|INITIATED|EXECUTING|COMPLETED|FAILED|CANCELLED>
  input_payload:
    <the Requested State payload that initiated this process>
  output_payload:
    <what the process produced — in DCM unified format>
  affected_entities:
    - entity_uuid: <uuid of affected Resource/Service Entity>
      effect_type: <created|modified|decommissioned|read>
      effect_description: <human-readable description>
  execution_record:
    initiated_timestamp: <ISO 8601>
    completed_timestamp: <ISO 8601 — when terminal state reached>
    executing_provider_uuid: <uuid of provider that executed>
    authorized_by_policy_uuid: <uuid of policy that authorized execution>
  provenance:
    <standard provenance metadata>
```

### 6.4 Provenance Obligation for Process Resources

If a Process Resource modifies the state of a Resource/Service Entity, that Entity's realized state provenance MUST reference the Process Resource Entity UUID as the source of the modification. This ensures that every change to an Infrastructure Entity can be traced back to the Process that caused it.

---

## 7. Provider Internal Lifecycle Model

Providers have their own internal infrastructure that underpins the Resource/Service Entities they create. While that internal infrastructure is opaque to consumers, DCM needs visibility into it for placement, cost analysis, and operational governance.

### 7.1 Provider Capacity Model

DCM supports three capacity information modes. Mode 3 is mandatory for all providers. Modes 1 and 2 are configurable per provider registration.

**Mode 1 — Dynamic Query (on-demand)**
DCM queries the provider for current capacity as part of request processing. Used when real-time accuracy is critical or when the provider cannot maintain a registration schedule.

```yaml
capacity_query_response:
  provider_uuid: <uuid>
  resource_type_uuid: <uuid>
  location_uuid: <uuid>
  query_timestamp: <ISO 8601>
  available_capacity: <units>
  reserved_capacity: <units>
  committed_capacity: <units>
  sovereignty_capabilities: <list>
```

**Mode 2 — Provider Registration (scheduled, preferred)**
Provider registers capacity data with DCM on a configurable schedule. DCM maintains an internal capacity rating per provider, per Resource Type, per location. Default minimum update frequency: twice daily. Update frequency is configurable per provider registration.

```yaml
capacity_registration:
  provider_uuid: <uuid>
  registration_timestamp: <ISO 8601>
  next_scheduled_registration: <ISO 8601>
  capacity_by_resource_type:
    - resource_type_uuid: <uuid>
      location_uuid: <uuid>
      available_capacity: <units>
      reserved_capacity: <units>
      committed_capacity: <units>
      sovereignty_capabilities: <list>
```

**Mode 3 — Provider Denial (reactive, mandatory)**
The provider validates it can fulfill a request before executing. If it cannot, it denies the request with reason `INSUFFICIENT_RESOURCES`. DCM receives the denial and can retry with an alternative provider. The denial triggers an immediate update to DCM's internal capacity rating for that provider.

```yaml
provider_denial:
  provider_uuid: <uuid>
  request_uuid: <uuid>
  denial_reason: INSUFFICIENT_RESOURCES
  denial_timestamp: <ISO 8601>
  resource_type_uuid: <uuid>
  location_uuid: <uuid>
  estimated_available_at: <ISO 8601 — optional, if provider can estimate>
```

### 7.2 Provider Lifecycle Events

Any provider event that affects Resource/Service Entity availability or operational characteristics MUST be reported to DCM immediately. Providers have a contractual obligation to report these events — this is non-negotiable.

**Reportable Event Types:**

| Event Type | Description | DCM Response |
|------------|-------------|--------------|
| `CAPACITY_CHANGE` | Available capacity increased or decreased | Update internal capacity rating |
| `DEGRADATION` | Underlying resource is degraded | Policy Engine evaluation → ALERT/REVERT/ESCALATE |
| `MAINTENANCE_SCHEDULED` | Planned maintenance window declared | Policy Engine evaluation → notify, migrate if needed |
| `MAINTENANCE_STARTED` | Maintenance has begun | Update Entity state to MAINTENANCE |
| `MAINTENANCE_COMPLETED` | Maintenance completed | Restore Entity state, trigger drift detection |
| `UNSANCTIONED_CHANGE` | Change occurred that was not initiated by DCM | Policy Engine evaluation → REVERT/UPDATE/ALERT |
| `ENTITY_HEALTH_CHANGE` | Entity health status changed | Policy Engine evaluation |
| `PROVIDER_DEGRADATION` | Provider itself is degraded | Policy Engine evaluation → reroute new requests |
| `DECOMMISSION_NOTICE` | Provider is decommissioning underlying resource | Policy Engine evaluation → migrate or decommission Entity |

**Event Payload Format:**
All provider lifecycle events must be reported in DCM unified data model format:

```yaml
provider_lifecycle_event:
  event_uuid: <uuid>
  event_type: <one of the types above>
  provider_uuid: <uuid>
  affected_entity_uuids:
    - <uuid of affected Resource/Service Entity>
  event_timestamp: <ISO 8601>
  event_details:
    <event-specific data in DCM unified format>
  severity: <INFO|WARNING|CRITICAL>
  requires_immediate_action: <true|false>
```

**Maximum Reporting Latency:**
Providers must report lifecycle events within the timeframe declared in their provider registration. For CRITICAL severity events, immediate reporting is required. The reporting latency SLA is part of the Provider SLA/Operational Contract.

### 7.3 DCM Capacity Rating

DCM maintains an internal capacity rating per provider, per Resource Type, per location. This rating is used by the Policy Engine for placement decisions.

```yaml
dcm_capacity_rating:
  provider_uuid: <uuid>
  resource_type_uuid: <uuid>
  location_uuid: <uuid>
  last_updated: <ISO 8601>
  update_source: <mode_1_query|mode_2_registration|mode_3_denial>
  available_capacity: <units>
  capacity_confidence: <high|medium|low>
  # high: updated within last scheduled window
  # medium: updated within 2x scheduled window
  # low: stale — beyond 2x scheduled window
  next_scheduled_update: <ISO 8601>
```

---


---

## 7a. Provider Update Notification Model

### 7a.1 The Fundamental Constraint — Realized State Only Changes via a Request

DCM enforces a single foundational rule for the Realized Store:

> **Realized State only changes when an authorized request produces a corresponding Requested State record. No exceptions.**

This constraint unifies all state change pathways and eliminates ambiguity:

- **Drift is always unsanctioned** — if Discovered State differs from Realized State and there is no corresponding Requested State record explaining the difference, it is drift. There is no such thing as "legitimate drift."
- **Discovery does not update Realized State** — discovery writes only to the Discovered Store. It never updates the Realized Store, even if discovery shows an authorized change (the authorization produces its own Requested State and Realized State records).
- **Providers cannot write directly to Realized State** — providers report changes via the Provider Update Notification API. DCM evaluates the notification and creates a Requested State record if approved. Only then does a new Realized State record get written.

### 7a.2 Provider Update Notification

A **Provider Update Notification** is a formal mechanism by which a Service Provider reports an authorized state change to DCM. This is distinct from a lifecycle event (which reports provider health) and distinct from an unsanctioned change (which triggers drift). A Provider Update Notification is the provider saying: "I made an authorized change to this entity — please record it as the new Realized State."

**When is a Provider Update Notification appropriate:**

| Scenario | Correct mechanism | Why |
|----------|------------------|-----|
| Provider auto-heals a failed disk | Provider Update Notification | Authorized maintenance action; new disk is the correct state |
| Provider scales resources per pre-authorized auto-scale policy | Provider Update Notification | DCM pre-authorized the scaling policy; each scaling event is an authorized change |
| Provider performs planned maintenance that changes an IP assignment | Provider Update Notification | Planned, coordinated change |
| Unauthorized human modifies VM configuration at provider console | Drift event | No DCM authorization; treated as unsanctioned change |
| Provider silently changes configuration without notifying DCM | Drift event (detected by discovery) | Unreported change is unsanctioned until evaluated |

### 7a.3 Provider Update Notification API

Service Providers submit update notifications via a dedicated endpoint on the DCM API Gateway:

```
POST /api/v1/provider/entities/{entity_uuid}/update-notification
Authorization: <provider mTLS certificate>

Request body:
{
  "provider_uuid": "<uuid>",
  "notification_uuid": "<uuid>",      # idempotency key
  "notification_type": "<authorized_change|maintenance_change|auto_scale>",
  "changed_fields": {
    "memory_gb": {
      "previous_value": 8,
      "new_value": 16,
      "change_reason": "Auto-scale policy: payments-api-scale-up triggered at 85% memory utilization",
      "authorizing_policy_ref": "<uuid of pre-authorized policy>"
    }
  },
  "effective_at": "<ISO 8601>",
  "provider_evidence_ref": "<provider-side reference for this change>"
}
```

### 7a.4 DCM Processing of Provider Update Notifications

```
Provider submits update notification
  │
  ▼ Authentication and authorization check
  │   Verify: provider UUID is registered and active
  │   Verify: provider has authority over this entity
  │
  ▼ Policy Engine evaluates notification
  │   Evaluate: is this type of change pre-authorized for this entity/provider?
  │   Evaluate: does the change violate any GateKeeper constraints?
  │   Evaluate: does this change require consumer notification or approval?
  │
  ├── REJECTED
  │   The change is not authorized.
  │   DCM does NOT update Realized State.
  │   The discrepancy between provider state and DCM Realized State becomes drift.
  │   Provider receives rejection response with reason.
  │   UNSANCTIONED_CHANGE event logged.
  │
  ├── REQUIRES_CONSUMER_APPROVAL
  │   The change is plausible but requires consumer sign-off.
  │   Notification queued. Consumer notified.
  │   Entity enters PENDING_REVIEW state.
  │   Provider receives "pending_approval" response.
  │   On consumer approval → proceeds to APPROVED path.
  │   On consumer rejection → treated as REJECTED.
  │
  └── APPROVED
      DCM creates a Requested State record:
        source_type: provider_update
        actor: provider (service account)
        authorizing_policy_uuid: <policy that approved>
        changed_fields: [as reported by provider]
      
      DCM writes new Realized State snapshot:
        source_type: provider_update
        corresponding_requested_state_uuid: <newly created record>
        supersedes_realized_state_uuid: <previous snapshot>
      
      Audit record written: PROVIDER_UPDATE_APPLIED
      Provider receives "accepted" response.
```

### 7a.5 Pre-Authorization of Provider Updates

Organizations can pre-authorize categories of provider updates through policy, eliminating the need for per-change human approval:

```yaml
policy:
  type: gatekeeper
  handle: "tenant/payments/allow-auto-scale"
  rules:
    - condition:
        notification_type: auto_scale
        provider_uuid: <approved-provider-uuid>
        entity.resource_type: Compute.VirtualMachine
        changed_fields: [memory_gb, cpu_count]
        change_within_bounds:
          memory_gb: { max_increase_factor: 2 }
          cpu_count: { max_increase_factor: 2 }
      action: approve
      audit_note: "Auto-scale approved per payments team scaling policy"
```

This pre-authorization pattern allows providers to implement auto-scaling, auto-healing, and maintenance operations without requiring per-change manual approval, while keeping DCM's Realized Store accurate and traceable.

### 7a.6 Provider Lifecycle Events


| Event Type | Mechanism | DCM Response | Realized Store Updated? |
|------------|-----------|-------------|------------------------|
| `CAPACITY_CHANGE` | Lifecycle event | Update internal capacity rating | No |
| `DEGRADATION` | Lifecycle event | Policy Engine → ALERT/ESCALATE | No |
| `MAINTENANCE_SCHEDULED` | Lifecycle event | Notify, plan migration if needed | No |
| `MAINTENANCE_CHANGE` | **Provider Update Notification** | Evaluate → Requested State if approved | Yes (if approved) |
| `AUTO_SCALE` | **Provider Update Notification** | Evaluate per pre-auth policy → Requested State if approved | Yes (if approved) |
| `AUTO_HEAL` | **Provider Update Notification** | Evaluate per pre-auth policy → Requested State if approved | Yes (if approved) |
| `UNSANCTIONED_CHANGE` | Lifecycle event (no notification) | Drift event → Policy Engine → REVERT/ALERT/ESCALATE | No (drift, not update) |
| `ENTITY_HEALTH_CHANGE` | Lifecycle event | Policy Engine evaluation | No |
| `DECOMMISSION_NOTICE` | Lifecycle event | Policy Engine → migrate or decommission | No |

### 7a.7 System Policies

| Policy | Rule |
|--------|------|
| `RSE-010` | Realized State only changes via an authorized request that produces a corresponding Requested State record. Drift detection, discovery cycles, and lifecycle events do not write to the Realized Store. |
| `RSE-011` | Provider Update Notifications are evaluated by the Policy Engine before any Realized State change. Rejected notifications do not update Realized State — the discrepancy becomes drift. |
| `RSE-012` | Categories of provider updates may be pre-authorized via GateKeeper policy. Pre-authorized updates are processed automatically without per-change human approval. |
| `RSE-013` | Provider Update Notifications that require consumer approval place the entity in PENDING_REVIEW state. The provider receives a "pending_approval" response and the change is queued until resolution. |



### 7c. Provider Accreditation Registration

Every Service Provider must declare its accreditation status during registration. Accreditation declarations are references to accreditation records registered in DCM's accreditation registry (see [doc 26](26-accreditation-and-authorization-matrix.md)).

```yaml
provider_registration:
  # ... existing fields ...
  accreditations:
    - accreditation_uuid: <uuid>       # reference to registered accreditation record
      framework: fedramp_high
      status: active
      expires_at: "2026-12-31"

    - accreditation_uuid: <uuid>
      framework: hipaa
      accreditation_type: baa
      status: active

  # Self-declared compliance (lowest trust; used when no formal accreditation exists)
  self_declared_compliance:
    frameworks: [iso_27001]
    last_self_review: "2026-01-15"
    evidence_ref: <url>

  # Maximum data classification this provider is permitted to handle
  # DCM computes this from active accreditations; self_declared_max is the fallback
  self_declared_max_data_classification: confidential
```

Providers without any accreditation records are treated as `self_declared` level and are subject to the most restrictive authorization matrix rules. They may only receive data classified as `public` or `internal`.


## 8. Entity Relationships

Every Resource/Service Entity carries a `relationships` section declaring its relationships to other entities — internal DCM entities, external data entities, and business context entities. The relationship model is universal — the same structure is used for all relationship types.

See [Entity Relationships](09-entity-relationships.md) for the complete relationship model.

```yaml
resource_service_entity:
  uuid: <uuid>
  # ... other entity fields ...
  relationships:
    - relationship_uuid: <uuid — same on both sides>
      this_entity_uuid: <this entity's uuid>
      this_role: <role this entity plays>
      related_entity_uuid: <uuid of related entity or external reference>
      related_entity_type: <internal|external>
      relationship_type: <requires|depends_on|contains|references|peer|manages>
      nature: <constituent|operational|informational>
      lifecycle_policy:
        on_related_destroy: <destroy|retain|detach|notify>
        on_related_suspend: <suspend|retain|detach|notify>
        on_related_modify: <cascade|ignore|notify>
      status: <active|suspended|terminated>
      provenance:
        <standard provenance metadata>
```

---

## 9. DCM System Policies for Resource/Service Entities

The following are **non-overridable DCM System Policies** that apply to all Resource/Service Entities:

| Policy | Rule | Enforcement |
|--------|------|-------------|
| `RSE-001` | Every Resource/Service Entity must belong to exactly one DCM Tenant | Enforced at Entity creation — no Tenant = request rejected |
| `RSE-002` | Every Resource/Service Entity must have a UUID | Enforced at Entity creation |
| `RSE-003` | Every Resource/Service Entity must have a complete provenance chain | Enforced at every state transition |
| `RSE-004` | Realized State payloads must be complete — not a status code | Enforced at provider response receipt |
| `RSE-005` | Decommissioned Entity records are immutable and permanent | Enforced at decommission — records cannot be deleted |
| `RSE-006` | Provider lifecycle events must be recorded in Entity provenance | Enforced at event receipt |
| `RSE-007` | Ownership transfers must be authorized by policy | Enforced at transfer initiation |
| `RSE-008` | Process Resource Entities must reference all affected Entity UUIDs | Enforced at process completion |

---

## 9a. Lifecycle Time Constraints

### 9a.1 Concept

**Lifecycle time constraints** declare when a resource should cease to exist or trigger a lifecycle action. They are a first-class field on any resource entity — governed, provenance-tracked, and subject to the standard override control model.

Any source in the data model precedence chain can declare a time constraint: a consumer request, a Core Layer, a Service Layer, or a policy. The Policy Engine has full authority over constraints — a GateKeeper can lock a TTL immutable or set `immutable_ceiling: absolute` on an expiry date.

### 9a.2 Constraint Structure

```yaml
lifecycle_constraints:
  ttl:
    duration: P14D                            # ISO 8601 duration
    reference_point: realization_timestamp    # created_at | realization_timestamp | last_modified
    on_expiry: <destroy | suspend | notify | review>
    metadata:
      override: allow                         # standard override control
      basis_for_value: "Consumer declared ephemeral — 14-day lab resource"

  expires_at:
    timestamp: "2026-06-30T23:59:59Z"         # absolute calendar date
    on_expiry: notify
    metadata:
      override: immutable
      locked_by_policy_uuid: <uuid>
      basis_for_value: "Project deadline — resource must not persist beyond Q2"

  enforcement:
    warn_before_expiry: P1D                   # warn 1 day before expiry
    grace_period: PT1H                        # 1 hour grace after expiry before action
    on_grace_period_expiry: <execute | escalate>
```

When both `ttl` and `expires_at` are declared, the earliest expiry wins (LTC-004).

### 9a.3 Precedence

Time constraints follow the same precedence as all other resource fields:

```
Base Layer (lowest — e.g., no TTL by default)
  ↓  Core Layer (e.g., all dev resources: TTL 90 days)
  ↓  Service Layer (e.g., ephemeral compute: TTL 7 days)
  ↓  Request Layer (consumer declared)
  ↓  Transformation Policy (enrich from business context)
  ↓  GateKeeper Policy (highest — may lock immutable)
```

### 9a.4 Expiry Enforcement

The **Lifecycle Constraint Enforcer** is a DCM control plane component — not a provider concern. It monitors realized entities, fires `on_expiry` actions when constraints are reached, and records all enforcement in provenance and the Audit Store.

Entities whose `on_expiry` action fails to execute enter `PENDING_EXPIRY_ACTION` state and trigger an escalation (LTC-005).

### 9a.5 System Policies

| Policy | Rule |
|--------|------|
| `LTC-001` | Lifecycle time constraints follow standard data model precedence |
| `LTC-002` | GateKeeper policies may lock lifecycle constraints as immutable |
| `LTC-003` | Expiry enforcement is a DCM control plane function |
| `LTC-004` | When multiple time constraints exist, the earliest expiry wins |
| `LTC-005` | Failed expiry action execution triggers `PENDING_EXPIRY_ACTION` state and escalation |

---

## 9a. Lifecycle Time Constraints — Process Resources (Q28)

Process Resource entities must declare a maximum execution time. This is a mandatory field — not optional. A Process Resource with no execution time limit creates operational blindness (DCM cannot know if it is hung).

```yaml
process_resource_entity:
  resource_type: Process.AnsiblePlaybook
  execution_constraints:
    max_execution_time: PT2H          # mandatory — ISO 8601 duration
    expected_completion: PT30M        # advisory — when we expect completion
    grace_period: PT15M               # grace period after max before action fires
    on_max_exceeded: <escalate|terminate|notify>
    # escalate:  notify platform admin and provider; human decides
    # terminate: DCM instructs provider to terminate the process
    # notify:    notify consumer and wait; no automatic action
    escalation_recipient: <actor-uuid>
```

The Lifecycle Constraint Enforcer handles this — process execution time is a `lifecycle_constraint.ttl` with `reference_point: realization_timestamp`. The `on_max_exceeded` action maps to the standard `on_expiry` lifecycle action vocabulary.

**Profile-governed default `on_max_exceeded`:**

| Profile | Default Action |
|---------|---------------|
| `minimal` | `notify` |
| `dev` | `notify` |
| `standard` | `escalate` |
| `prod` | `escalate` |
| `fsi` | `terminate` |
| `sovereign` | `terminate` |

---

## 9b. Billing State and SUSPENDED Entities (Q29)

DCM carries billing state as a first-class field — the Cost Analysis component consumes it. Organizations declare billing behavior via policy — DCM does not decide what is billable.

```yaml
entity:
  lifecycle_state: SUSPENDED
  billing_state: <billable|non_billable|reduced_rate>
  billing_metadata:
    billing_rate_multiplier: 0.3       # 30% of normal rate if reduced_rate
    billing_reason: "Reserved capacity — suspended but resources held"
    billing_policy_uuid: <uuid>        # policy that determined this billing state
    billable_components: [storage, ip_address]   # which sub-resources are billed
    non_billable_components: [compute]
```

**Three billing models for SUSPENDED:**
- **`billable`** — resources reserved and capacity held (stopped VM still consuming reserved IP and storage)
- **`non_billable`** — resources fully released on suspension (spot/ephemeral resource)
- **`reduced_rate`** — partial resources held (storage retained, compute released)

Policy injects `billing_state` and `billing_metadata` during state transitions. A GateKeeper can declare: "all suspended VMs in the payments Tenant are billed at 30% — compute released but storage and IP retained."

---

## 9c. Bare Metal Indivisibility (Q26)

Bare metal Whole Allocation uses the same `shareability.allowed: false` mechanism as any non-shareable resource (REL-017), plus an explicit `allocation_model` declaration:

```yaml
resource_type_spec:
  fully_qualified_name: Compute.BareMetal
  allocation_model: whole_unit         # whole_unit | fractional | pooled
  shareability:
    allowed: false                     # structural lock — cannot be changed by policy
    indivisibility_reason: "Physical hardware — cannot be partitioned"
  capacity:
    unit: server
    minimum_allocation: 1
    maximum_allocation: 1              # whole unit only

# Provider contract obligations for bare metal:
provider_contract_obligations:
  - Report full physical identity in realized payload (serial_number, hardware_profile)
  - Exclusive placement hold during reserve_query — no concurrent holds on same server
  - Notify DCM immediately if any sharing attempt is detected (drift trigger)
```

---

## 9d. Capacity Confidence — Automatic Actions (Q27)

Capacity confidence ratings trigger policy-governed automatic actions. Policy determines the action per confidence level; the active Profile sets defaults.

```yaml
capacity_confidence_policy:
  HIGH:
    action: proceed
    max_data_age: PT5M
  MEDIUM:
    action: proceed_with_warning      # default — overridable by policy
    max_data_age: PT30M
  LOW:
    action: refresh_before_placement  # default — trigger Mode 1 query
    max_data_age: PT1H
    trigger_mode1_query: true
```

**Profile-governed defaults:**

| Profile | HIGH | MEDIUM | LOW |
|---------|------|--------|-----|
| `minimal` | proceed | proceed | proceed_with_warning |
| `dev` | proceed | proceed | refresh_before_placement |
| `standard` | proceed | proceed_with_warning | refresh_before_placement |
| `prod` | proceed | refresh_before_placement | reject |
| `fsi` | proceed | refresh_before_placement | reject |
| `sovereign` | proceed | refresh_before_placement | reject |

---

## 9e. Ownership Transfer Count (Q25)

Ownership transfers are unlimited by default. Each transfer is immutably recorded with a monotonically incrementing `transfer_number`. Policy may declare a maximum per resource type.

```yaml
ownership_transfer_record:
  transfer_uuid: <uuid>
  transfer_number: 3              # monotonically incrementing — never resets
  from_tenant_uuid: <uuid>
  to_tenant_uuid: <uuid>
  authorized_by: <actor>
  transfer_timestamp: <ISO 8601>
  reason: <human-readable — mandatory>
  policy_uuid: <uuid>
```

Policy-governed maximum when needed:
```yaml
policy:
  type: gatekeeper
  rule: >
    If resource.ownership_transfer_count > 5
    AND resource_type == Compute.VirtualMachine
    THEN gatekeep: "VM has exceeded 5 ownership transfers — manual review required"
```

---

## 10. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | For Hybrid Transfer — what is the maximum number of ownership transfers allowed, or is it unlimited? | Operational complexity | ✅ Resolved — unlimited by default; policy may declare maximum; monotonically incrementing transfer_number (ENT-001) |
| 2 | For Whole Allocation of bare metal — how is the indivisibility enforced at the provider level? | Provider contract | ✅ Resolved — allocation_model: whole_unit; shareability.allowed: false; exclusive hold; provider reports physical identity (ENT-002) |
| 3 | Should capacity confidence ratings trigger automatic actions? | Capacity model | ✅ Resolved — policy-governed actions per confidence level; LOW triggers Mode 1 query by default in standard+; profile-governed (ENT-003) |
| 4 | For Process Resources — should there be a maximum execution time? | Operational governance | ✅ Resolved — mandatory max_execution_time; enforced by Lifecycle Constraint Enforcer; profile-governed on_max_exceeded (ENT-004) |
| 5 | How does the SUSPENDED state interact with cost analysis? | Cost model | ✅ Resolved — billing_state field (billable/non_billable/reduced_rate); policy injects on state transition; Cost Analysis consumes (ENT-005) |

---

## 11. DCM System Policies — Entity and Dependency Gaps

| Policy | Rule |
|--------|------|
| `ENT-001` | Ownership transfer count is unlimited by default. Policy may declare a maximum transfer count per resource type. Each transfer is immutably recorded with a monotonically incrementing transfer_number and mandatory reason field. |
| `ENT-002` | Bare metal resources declare `allocation_model: whole_unit` and `shareability.allowed: false`. Placement holds are exclusive. Providers must report the server's physical identity in the realized payload and notify DCM of any sharing attempt. |
| `ENT-003` | Capacity confidence ratings trigger policy-governed automatic actions. LOW confidence triggers a Mode 1 Information Provider query by default in standard+ profiles. Profile determines the default action per confidence level. |
| `ENT-004` | Process Resource entities must declare `max_execution_time`. This field is mandatory. Execution time is enforced by the Lifecycle Constraint Enforcer. Profile governs the default `on_max_exceeded` action. |
| `ENT-005` | Entity `billing_state` (billable, non_billable, or reduced_rate) is a first-class field injected by policy during state transitions. The Cost Analysis component consumes `billing_state` for cost attribution. DCM does not decide billing policy — it carries the billing signal. |

---



- **DCM Tenant** — the mandatory ownership boundary for all Resource/Service Entities
- **Four States** — Intent, Requested, Realized, Discovered — the state lifecycle of a Resource/Service Request and Entity
- **Field-Level Provenance** — every state transition and ownership transfer is recorded in Entity provenance
- **Policy Engine** — evaluates provider events and unsanctioned changes, determines response actions
- **Service Dependencies** — Resource/Service Entities declare dependencies on other Entities
- **Resource Grouping** — Entities belong to a Tenant and optionally to additional Resource Groups
- **Provider Contract** — governs provider obligations including capacity reporting and event notification

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
