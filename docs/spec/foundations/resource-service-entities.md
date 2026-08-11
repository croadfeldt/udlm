# UDLM — Resource/Service Entities

**Related Documents:** [Context and Purpose](context-and-purpose.md) | [Operational Models](../lifecycle/operational-models.md) | [Entity Types](entity-types.md) | [Ownership, Sharing, and Allocation](ownership-sharing-allocation.md) | [Layering and Versioning](layering-and-versioning.md) | [Resource Type Hierarchy](resource-type-hierarchy.md) | [Service Dependencies](service-dependencies.md) | [Resource Grouping](resource-grouping.md)

> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](foundations.md).
>
> Data: entity lifecycle. Provider: lifecycle events and update notifications.

---

## 1. Purpose

This document defines the two fundamental transactional concepts in UDLM — the **Resource/Service Request** and the **Resource/Service Entity** — and establishes the ownership models, lifecycle principles, and provider relationship rules that govern them.

Understanding the distinction between a Request and an Entity, and the principle that the implementation is the authoritative system of record for all resource data regardless of operational ownership, is essential to understanding how a conformant UDLM peer achieves its core goals of auditability, lifecycle management, and sovereignty.

---

## 2. Core Terminology

### 2.1 Resource/Service Request

A **Resource/Service Request** is what a consumer submits to a UDLM implementation — the declared intent to consume a resource or service. It is the consumer side of the transaction.

- Created when a consumer submits a request via a supported ingress surface (Web UI, Consumer API)
- Captured as the **Intent State** before any processing
- Processed into the **Requested State** after assembly and policy validation
- Is the initiating event that causes a Resource/Service Entity to be created

A Request is not a thing — it is an **instruction**. It describes what the consumer wants. The provider acts on the Requested State to produce an Entity.

### 2.2 Resource/Service Entity

A **Resource/Service Entity** is the "thing" produced by a provider as a result of fulfilling a Resource/Service Request. It is the provider side of the transaction — the allocation made real.

- Created when a provider fulfills a Requested State payload
- Returned to the implementation in unified data model format via Denaturalization
- Captured as the **Realized State** in the Realized Store
- Assigned to a **Tenant** — the ownership boundary
- Has a UUID, full provenance chain, and complete lifecycle from creation to decommission
- Is the unit of consumption, cost attribution, drift detection, and audit

A Resource/Service Entity IS a thing — it exists, it has state, it has an owner, and the implementation manages its lifecycle.

### 2.3 The Critical Distinction

```
Consumer submits        →  Resource/Service REQUEST  →  Intent/Requested State
Provider fulfills       →  Resource/Service ENTITY   →  Realized State
Implementation manages     →  ENTITY persists            →  Drift/Audit/Cost/Rehydration
```

---

## 3. The Implementation as Authoritative Owner of All Resource Data

This is the most fundamental principle governing Resource/Service Entities:

**The UDLM implementation is ALWAYS the system of record for Resource/Service Entity data. The implementation is ALWAYS authoritative for the resource definition. The implementation ALWAYS owns the lifecycle. This applies regardless of the operational ownership model.**

The operational ownership model (described in Section 4) determines who has authority to operate on a Resource/Service Entity. It does not affect the implementation's data ownership. Specifically:

- The implementation owns the **data definition** of every Resource/Service Entity — what it is, what it should be, what it was
- The implementation owns the **lifecycle** — from Requested through Realized to Decommissioned
- The implementation is **authoritative** — if a provider reports a change the implementation was not aware of, the implementation acts on it according to policy
- The implementation acts as the **Tenant advocate** — it protects the Tenant's interests in all provider interactions
- Providers are **custodians** of the underlying infrastructure — they are not the system of record

**Unsanctioned change response vocabulary (typed interop baseline):**

If a provider reports a state change that was not initiated by an authorized request, the Policy Engine evaluates the change and selects from the following typed action vocabulary — the interop baseline: which responses an estate's policies reach for is the organization's declaration, and new response types may be proposed (`docs/design/operational-response-matrix.md`):

| Response | Description |
|----------|-------------|
| `ALERT` | Notify appropriate personas — Tenant owner, SRE, Auditor |
| `REVERT` | Instruct provider to revert to the declared realized state |
| `UPDATE_DEFINITION` | Accept the change and update the realized state definition |
| `INVESTIGATE` | Flag for human review before action |
| `DECOMMISSION` | Initiate decommission if the change represents unrecoverable deviation |
| `ESCALATE` | Escalate to higher policy tier for decision |

The response is selected by Policy Engine evaluation against:
- The Resource/Service definition
- Service/Resource dependencies
- Consumer preferences
- Organizational and Tenant policies
- Sovereignty requirements

---

## 4. Ownership Models

UDLM defines **three** ownership models, canonically in [`ownership-sharing-allocation.md`](ownership-sharing-allocation.md) — `whole_allocation`, `allocation`, and `shareable`. This section illustrates them and defines the **ownership-transfer event** (a change of owner, *not* a fourth model). Every Provider Catalog Item declares which model(s) it supports; the model is recorded in the entity's provenance at creation.

### 4.1 Allocation Model

The provider retains internal ownership of the underlying infrastructure. The consumer owns the Resource/Service Entity (the allocation) in their Tenant. The provider can reclaim the underlying resource when the entity is decommissioned.

**Characteristics:**
- Provider retains asset ownership
- Consumer owns the allocation — the Entity in their Tenant
- Provider has reclaim rights on decommission
- Underlying infrastructure may be shared or subdivided
- The implementation manages the Entity lifecycle; provider manages the underlying resource

**Examples:** Virtual Machine, Container, Network Port, IP Address, Firewall Rule, Database Instance

---

### 4.2 Whole Allocation Model

The entire physical or logical resource is allocated as a single indivisible unit to one consumer's Tenant. The provider retains internal ownership but the consumer has exclusive use of the whole resource. The resource cannot be subdivided or shared during the allocation period.

**Characteristics:**
- Provider retains asset ownership
- Consumer has exclusive, indivisible use
- The resource is not shared or subdivided
- Provider has reclaim rights on decommission
- The implementation manages the Entity lifecycle

**Examples:** Dedicated Bare Metal server (provider-owned), Dedicated Network appliance, Whole storage array allocation

---

### 4.3 Ownership transfer — a change of owner, not a fourth model

Ownership can move to a new Tenant. The hardware supply chain is the canonical case: a procurement provider racks and offers hardware; a hosting team consumes it and **takes over ownership *and* lifecycle authority** (the prior owner has no reclaim rights afterward); they then re-offer it — e.g. as VMs — to end customers, who own their own allocations. This is a **change of the owner** on whichever ownership model already applies — **not** a distinct ownership model.

A colocation-style split — the allocatee runs the device's business operations while the original owner **retains lifecycle management** — is *not* a transfer at all: it is a standard `allocation`/`shareable`, where ownership and lifecycle stay with the provider and the consumer holds the operating stake.

Transfer is governed and recorded immutably in the transfer provenance record (the ownership-transfer count is unlimited by default, each recorded with a monotonic `sequence` and a mandatory reason):

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

- The current owner is always exactly one Tenant; ownership can be reassigned any number of times.
- Every transfer is Policy-validated and the receiving Tenant must accept it — it cannot be forced.
- The implementation remains authoritative for data and lifecycle through all transfers.

**Examples:** a bare-metal server handed from procurement to a hosting team, then that team offering VMs on it; a hardware asset reassigned between business units.

---

### 4.4 Ownership Model Declaration

Every Provider Catalog Item must declare the ownership model(s) it supports:

```yaml
catalog_item:
  uuid: <uuid>
  ownership_models_supported:
    - whole_allocation
    - allocation
    - shareable
  default_ownership_model: <one of the above>
  transfer_policy_required: <true|false>
  # If true, a policy must govern any ownership-transfer event (§4.3)
```

---

## 5. Resource/Service Entity Lifecycle

Every Resource/Service Entity carries the five-value `lifecycle_state` (`Intent → Requested → Realized ↔ Discovered → Decommissioned`; data-model-core §3). On top of that coarse lifecycle it exposes finer **operational phase + health as `status.conditions`** — peers MUST recognize and propagate both. The machine below is that `status` overlay (how the operational phases flow); it is **not** a second `lifecycle_state` enum. Three phases coincide with lifecycle_state values (`REQUESTED`→Requested, `REALIZED`→Realized, `DECOMMISSIONED`→Decommissioned); the rest are status conditions on a Realized entity:

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

| Operational phase / status | Description |
|-------|-------------|
| `REQUESTED` | Request submitted, Intent State captured *(coincides with lifecycle_state `Requested`)* |
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

## 6. Processes

A **Process** is the family of bounded executions — and every execution is a record of the ONE
`Job` class (`registry/classes/process/job/_base.yaml`), the runs system-of-record. There are no
per-domain run subtypes: the domain derives from the definition the Job executes
(`executes_definition` → an Automation or other definition class; `job.running?family=automation`
is a filter, never a subtype). Starting an execution is submitting a Job intent; stopping one is
a change request on the Job.

### 6.1 Characteristics

- **Ephemeral lifecycle** — exists for the duration of execution, then terminates
- **No ongoing realized state to manage** — lifecycle ends at COMPLETED or FAILED
- **The run record is retained permanently** — the Job's receipt (states) and its seals are immutable and permanent
- **Must belong to a Tenant** — even ephemeral resources must be owned
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

### 6.3 Process Data Model

> **Machine-validatable:** the Process execution axis is the `process` block on `registry/realized-entity.schema.json` (`execution_state` + `affected_entities`). It is a SEPARATE axis from the four-state `lifecycle_state` (data-model-core §3 [D7]); `registry/tools/validate.py` requires it on `family: Process` instances and forbids it elsewhere. Everything else about a run lives where the Job class puts it: the intent in `spec` fields (`definition_ref`, `parameters`, `targets`, `max_execution_time`, `on_max_exceeded`, `trigger`, `schedule`), the run facts in typed `outputs` (`started_at`, `completed_at`, `results`), the executing provider in the record's provider field, and the authorizing policy in the write's seal (ADR-059 — authorization is a ledger claim, not record state).

```yaml
job_record:
  uuid: <uuid>
  family: Process           # ADR-027 family (bounded execution)
  resource_type: Job        # the one runs class — no per-domain subtypes
  tenant_uuid: <owning tenant uuid>
  version: <Major.Minor.Revision>
  lifecycle_state: <Intent|Requested|Realized|Discovered|Decommissioned>  # universal coarse lifecycle
  states:
    requested:
      fields:               # the Job intent — immutable [definition_ref, parameters]
        definition_ref: <Reference to the definition this run executes>
        parameters: { <validated by the bound definition's inputs_schema> }
        targets: [ <typed References> ]
        max_execution_time: PT2H        # mandatory (ENT-002)
        on_max_exceeded: terminate
        trigger: schedule
    realized:
      outputs:              # run facts are typed outputs of the Job
        started_at: <ISO 8601>
        completed_at: <ISO 8601 — when terminal state reached>
        results: { <validated by the bound definition's outputs_schema> }
  process:                  # the execution axis — data-model-core [D7]
    execution_state: <REQUESTED|INITIATED|EXECUTING|COMPLETED|FAILED|CANCELLED>
    affected_entities:
      - entity_uuid: <uuid of affected Resource/Service Entity>
        effect_type: <created|modified|decommissioned|read>
        effect_description: <human-readable description>
```

### 6.4 Provenance Obligation for Processes

If a Job modifies the state of a Resource/Service Entity, that Entity's realized-state provenance MUST reference the Job uuid as the source of the modification — every change to an entity is traceable to the run that caused it (this is udlm#330's start/stop model doing provenance work).

---

## 7. Provider Internal Lifecycle Model

Providers have their own internal infrastructure that underpins the Resource/Service Entities they create. While that internal infrastructure is opaque to consumers, the implementation needs visibility into it for placement, cost analysis, and operational governance. The substrate defines the contracts a provider must honor.

### 7.1 Provider Capacity Model

UDLM defines three capacity information modes. Mode 3 is mandatory for all providers. Modes 1 and 2 are configurable per provider registration.

**Mode 1 — Dynamic Query (on-demand)**
The implementation queries the provider for current capacity as part of request processing. Used when real-time accuracy is critical or when the provider cannot maintain a registration schedule.

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
Provider registers capacity data with the implementation on a configurable schedule. The implementation maintains an internal capacity rating per provider, per Resource Type, per location. Default minimum update frequency: twice daily. Update frequency is configurable per provider registration.

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
The provider validates it can fulfill a request before executing. If it cannot, it denies the request with reason `INSUFFICIENT_RESOURCES`. The implementation receives the denial and can retry with an alternative provider. The denial triggers an immediate update to the implementation's internal capacity rating for that provider.

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

Any provider event that affects Resource/Service Entity availability or operational characteristics MUST be reported to the implementation immediately. Providers have a contractual obligation to report these events — this is non-negotiable.

**Reportable Event Types (closed substrate vocabulary):**

| Event Type | Description |
|------------|-------------|
| `CAPACITY_CHANGE` | Available capacity increased or decreased |
| `DEGRADATION` | Underlying resource is degraded |
| `MAINTENANCE_SCHEDULED` | Planned maintenance window declared |
| `MAINTENANCE_STARTED` | Maintenance has begun |
| `MAINTENANCE_COMPLETED` | Maintenance completed |
| `UNSANCTIONED_CHANGE` | Change occurred that was not initiated by the implementation |
| `ENTITY_HEALTH_CHANGE` | Entity health status changed |
| `PROVIDER_DEGRADATION` | Provider itself is degraded |
| `DECOMMISSION_NOTICE` | Provider is decommissioning underlying resource |

**Event Payload Format (substrate-normative):**
All provider lifecycle events must be reported in unified data model format:

```yaml
provider_lifecycle_event:
  event_uuid: <uuid>
  event_type: <one of the types above>
  provider_uuid: <uuid>
  affected_entity_uuids:
    - <uuid of affected Resource/Service Entity>
  event_timestamp: <ISO 8601>
  event_details:
    <event-specific data in unified format>
  severity: <INFO|WARNING|CRITICAL>
  requires_immediate_action: <true|false>
```

**Maximum Reporting Latency:**
Providers must report lifecycle events within the timeframe declared in their provider registration. For CRITICAL severity events, immediate reporting is required. The reporting latency SLA is part of the Provider SLA/Operational Contract.

### 7.3 Provider Capacity — declaration vs rating

What UDLM carries is the provider's **capacity declaration** — reported at registration and refreshed on the provider's declared schedule (part of the provider contract). What an implementation does with it — maintaining an **internal capacity rating** per provider/type/location, its freshness/confidence bookkeeping, and the placement logic that consumes it — is a runtime optimization (a non-authoritative placement cache), not part of the data model. See control-plane architecture documentation for the rating structure and refresh mechanics.

---

## 7a. Provider Update Notification Model

### 7a.1 The Fundamental Constraint — Realized State Only Changes via a Request

UDLM enforces a single foundational rule for the Realized Store:

> **Realized State only changes when an authorized request produces a corresponding Requested State record. No exceptions.**

This constraint unifies all state change pathways and eliminates ambiguity:

- **Drift is always unsanctioned** — if Discovered State differs from Realized State and there is no corresponding Requested State record explaining the difference, it is drift. There is no such thing as "legitimate drift."
- **Discovery does not update Realized State** — discovery writes only to the Discovered Store. It never updates the Realized Store, even if discovery shows an authorized change (the authorization produces its own Requested State and Realized State records).
- **Providers cannot write directly to Realized State** — providers report changes via the Provider Update Notification contract. The implementation evaluates the notification and creates a Requested State record if approved. Only then does a new Realized State record get written.

### 7a.2 Provider Update Notification

A **Provider Update Notification** is the formal mechanism by which a Service Provider reports an authorized state change. This is distinct from a lifecycle event (which reports provider health) and distinct from an unsanctioned change (which triggers drift). A Provider Update Notification is the provider saying: "I made an authorized change to this entity — please record it as the new Realized State."

**When is a Provider Update Notification appropriate:**

| Scenario | Correct mechanism | Why |
|----------|------------------|-----|
| Provider auto-heals a failed disk | Provider Update Notification | Authorized maintenance action; new disk is the correct state |
| Provider scales resources per pre-authorized auto-scale policy | Provider Update Notification | The implementation pre-authorized the scaling policy; each scaling event is an authorized change |
| Provider performs planned maintenance that changes an IP assignment | Provider Update Notification | Planned, coordinated change |
| Unauthorized human modifies VM configuration at provider console | Drift event | No implementation authorization; treated as unsanctioned change |
| Provider silently changes configuration without notifying the implementation | Drift event (detected by discovery) | Unreported change is unsanctioned until evaluated |

### 7a.3 Provider Update Notification Contract

Service Providers submit update notifications via a dedicated endpoint on the implementation's API surface. The wire payload is normative:

```
POST /api/v1/provider/entities/{entity_uuid}/update-notification
Authorization: <provider auth credential per provider-callback-auth contract>

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

### 7a.4 Notification Outcomes (Typed Vocabulary)

The substrate defines the typed outcome vocabulary for Provider Update Notifications — the interop baseline; which outcomes an estate's policies select is the organization's declaration (`docs/design/operational-response-matrix.md`). The implementation evaluates the notification against policy and returns one of:

| Outcome | Meaning |
|---------|---------|
| `REJECTED` | The change is not authorized. Realized State is NOT updated. The discrepancy becomes drift. The provider receives a rejection response. |
| `REQUIRES_CONSUMER_APPROVAL` | The change is plausible but requires consumer sign-off. The entity enters a pending-review state. The provider receives a "pending_approval" response. |
| `APPROVED` | The implementation creates a Requested State record (source_type: provider_update) and writes a new Realized State snapshot referencing the new Requested State. |

### 7a.5 Pre-Authorization of Provider Updates (Contract)

Categories of provider updates can be pre-authorized through policy, eliminating the need for per-change human approval. The substrate provides the policy declaration shape:

```yaml
policy:
  type: validation
  enforcement_class: compliance
  handle: "tenant/payments/allow-auto-scale"
  rules:
    - condition:
        notification_type: auto_scale
        provider_uuid: <approved-provider-uuid>
        entity.resource_type: Compute.VM
        changed_fields: [memory_gb, cpu_count]
        change_within_bounds:
          memory_gb: { max_increase_factor: 2 }
          cpu_count: { max_increase_factor: 2 }
      action: approve
      audit_note: "Auto-scale approved per payments team scaling policy"
```

This pre-authorization pattern allows providers to implement auto-scaling, auto-healing, and maintenance operations without requiring per-change manual approval while keeping the Realized Store accurate and traceable.

### 7a.6 Mechanism Mapping (Substrate Table)

| Event Type | Mechanism | Realized Store Updated? |
|------------|-----------|------------------------|
| `CAPACITY_CHANGE` | Lifecycle event | No |
| `DEGRADATION` | Lifecycle event | No |
| `MAINTENANCE_SCHEDULED` | Lifecycle event | No |
| `MAINTENANCE_CHANGE` | **Provider Update Notification** | Yes (if approved) |
| `AUTO_SCALE` | **Provider Update Notification** | Yes (if approved) |
| `AUTO_HEAL` | **Provider Update Notification** | Yes (if approved) |
| `UNSANCTIONED_CHANGE` | Lifecycle event (no notification) | No (drift, not update) |
| `ENTITY_HEALTH_CHANGE` | Lifecycle event | No |
| `DECOMMISSION_NOTICE` | Lifecycle event | No |

### 7a.7 System Policies

| Policy | Rule |
|--------|------|
| `RSE-010` | Realized State only changes via an authorized request that produces a corresponding Requested State record. Drift detection, discovery cycles, and lifecycle events do not write to the Realized Store. |
| `RSE-011` | Provider Update Notifications are evaluated by the Policy Engine before any Realized State change. Rejected notifications do not update Realized State — the discrepancy becomes drift. |
| `RSE-012` | Categories of provider updates may be pre-authorized via Validation policy. Pre-authorized updates are processed automatically without per-change human approval. |
| `RSE-013` | Provider Update Notifications that require consumer approval place the entity in PENDING_REVIEW state. The provider receives a "pending_approval" response and the change is queued until resolution. |

---

### 7c. Provider Accreditation Registration

Every Service Provider must declare its accreditation status during registration. Accreditation declarations are references to accreditation records registered in the accreditation registry (see [Accreditation and Authorization Matrix](../governance/accreditation-and-authorization-matrix.md)).

```yaml
provider_registration:
  # ... existing fields ...
  accreditations:
    # Reference ONLY. status/expires_at are NOT restated here — the control plane resolves currency from the
    # registered accreditation record at evaluation time (a provider cannot assert a revoked
    # accreditation is still active). framework/accreditation_type are readability hints.
    - accreditation_uuid: <uuid>       # reference to registered accreditation record
      framework: fedramp_high

    - accreditation_uuid: <uuid>
      framework: hipaa
      accreditation_type: baa

  # Self-declared compliance (lowest trust; used when no formal accreditation exists)
  self_declared_compliance:
    frameworks: [iso_27001]
    last_self_review: "2026-01-15"
    evidence_ref: <url>

  # Maximum data classification this provider is permitted to handle — control-plane-COMPUTED from active
  # accreditations only; NOT self-declared. A provider without accreditations is capped at the hard
  # floor below (public/internal), so there is no self-declared fallback that could raise the ceiling
  # above what policy permits. A value supplied by the provider is ignored.
  # (computed field, control-plane-owned — resolved in the dcm registration verdict, not the submission)
```

Providers without any accreditation records are treated as `self_declared` level and are subject to the most restrictive authorization matrix rules. They may only receive data classified as `public` or `internal`.

---

## 8. Entity Relationships

Every Resource/Service Entity carries a `relationships` section declaring its relationships to other entities — internal entities, external data entities, and business context entities. The relationship model is universal — the same structure is used for all relationship types.

See [Entity Relationships](entity-relationships.md) for the complete relationship model.

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
      edge_type: <depends_on|contained_by|binds_to|references>
      strength: <hard|soft>          # depends_on only
      relation: <declared relation name (common-elements §9)>
      # nature (constituent|operational|informational) is derived from edge_type — see entity-relationships.md §6
      lifecycle_policy:
        on_related_destroy: <destroy|retain|detach|notify>
        on_related_suspend: <suspend|retain|detach|notify>
        on_related_modify: <cascade|ignore|notify>
      status: <active|suspended|terminated>
      provenance:
        <standard provenance metadata>
```

---

## 9. UDLM System Policies for Resource/Service Entities

The following are **non-overridable UDLM substrate policies** that apply to all Resource/Service Entities. Any conformant implementation MUST enforce these:

| Policy | Rule |
|--------|------|
| `RSE-001` | Every Resource/Service Entity must belong to exactly one Tenant. |
| `RSE-002` | Every Resource/Service Entity must have a UUID. |
| `RSE-003` | Every Resource/Service Entity must have a complete provenance chain. |
| `RSE-004` | Realized State payloads must be complete — not a status code. |
| `RSE-005` | Decommissioned Entity records are immutable and permanent. |
| `RSE-006` | Provider lifecycle events must be recorded in Entity provenance. |
| `RSE-007` | Ownership transfers must be authorized by policy. |
| `RSE-008` | Processes must reference all affected Entity UUIDs. |

---

## 9a. Lifecycle Time Constraints

### 9a.1 Concept

**Lifecycle time constraints** declare when a resource should cease to exist or trigger a lifecycle action. They are a first-class field on any resource entity — governed, provenance-tracked, and subject to the standard override control model.

Any source in the data model precedence chain can declare a time constraint: a consumer request, a Core Layer, a Service Layer, or a policy. The Policy Engine has full authority over constraints — a compliance-class Validation Policy can lock a TTL immutable or set `immutable_ceiling: absolute` on an expiry date.

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
  ↓  Validation Policy (highest — compliance-class may lock immutable)
```

### 9a.4 Expiry Enforcement Contract

The substrate requires that a conformant implementation provide a Lifecycle Constraint Enforcer (or equivalent) that monitors realized entities, fires `on_expiry` actions when constraints are reached, and records all enforcement in provenance and the Audit Store. Entities whose `on_expiry` action fails to execute MUST enter `PENDING_EXPIRY_ACTION` state and trigger an escalation (LTC-005). The mechanism by which this enforcement is implemented is an implementation choice.

### 9a.5 System Policies

| Policy | Rule |
|--------|------|
| `LTC-001` | Lifecycle time constraints follow standard data model precedence. |
| `LTC-002` | Compliance-class Validation policies may lock lifecycle constraints as immutable. |
| `LTC-003` | Expiry enforcement is a substrate-required control plane function. |
| `LTC-004` | When multiple time constraints exist, the earliest expiry wins. |
| `LTC-005` | Failed expiry action execution triggers `PENDING_EXPIRY_ACTION` state and escalation. |

---

## 9a-process. Lifecycle Time Constraints — Processes

Every Job declares a maximum execution time — `max_execution_time` is a mandatory Job element (ENT-002), not optional. A run with no execution bound creates operational blindness (the implementation cannot know if it is hung).

```yaml
job_record:
  resource_type: Job
  states:
    requested:
      fields:
        max_execution_time: PT2H      # mandatory Job element — ISO 8601 duration (ENT-002)
        on_max_exceeded: <escalate|terminate|notify>
        # escalate:  notify platform admin and provider; human decides
        # terminate: instruct provider to terminate the run
        # notify:    notify consumer and wait; no automatic action
  lifecycle_constraints:              # the general structure (§9a.2) carries the soft edges
    enforcement:
      warn_before_expiry: PT30M       # advisory expected-completion warning
      grace_period: PT15M             # grace after max before the action fires
      on_grace_period_expiry: escalate
```

`max_execution_time` is the run's `lifecycle_constraint.ttl` with `reference_point: realization_timestamp`; `on_max_exceeded` maps onto the standard `on_expiry` action vocabulary, and the softer edges (warning, grace) ride the general enforcement block (§9a.2).

Profile-governed defaults for `on_max_exceeded` are implementation-configurable; the substrate requires that profiles in the stricter direction (e.g., `fsi`, `sovereign`) default to deterministic termination, while looser profiles MAY default to `notify`.

---

## 9b. Billing State and SUSPENDED Entities

The substrate carries billing state as a first-class field. A consuming cost-analysis component reads this field. Organizations declare billing behavior via policy — the substrate does not decide what is billable.

```yaml
entity:
  lifecycle_state: Realized        # operational status "Suspended" is a status.condition (data-model-core §3)
  billing_state: <billable|non_billable|reduced_rate>
  billing_metadata:
    billing_rate_multiplier: 0.3       # 30% of normal rate if reduced_rate
    billing_reason: "Reserved capacity — suspended but resources held"
    billing_policy_uuid: <uuid>        # policy that determined this billing state
    billable_components: [storage, ip_address]   # which sub-resources are billed
    non_billable_components: [compute]
```

**Three billing models for SUSPENDED (closed vocabulary):**
- **`billable`** — resources reserved and capacity held (stopped VM still consuming reserved IP and storage)
- **`non_billable`** — resources fully released on suspension (spot/ephemeral resource)
- **`reduced_rate`** — partial resources held (storage retained, compute released)

Policy injects `billing_state` and `billing_metadata` during state transitions.

---

## 9c. Bare Metal Indivisibility

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
  - Notify immediately if any sharing attempt is detected (drift trigger)
```

---

## 9d. Capacity Confidence — Automatic Actions

Capacity confidence ratings trigger policy-governed automatic actions. Policy determines the action per confidence level. The substrate defines the closed action vocabulary; specific defaults per profile are implementation-configurable.

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

Typed action vocabulary (interop baseline — org policy declares which apply, and may propose additions, per the operational response matrix): `proceed`, `proceed_with_warning`, `refresh_before_placement`, `reject`.

---

## 9e. Ownership Transfer Count

Ownership transfers are unlimited by default; policy may declare a maximum per resource type.
Each transfer is an **audited ownership change** recording: both tenant identities, the
authorizing actor and policy, the timestamp, and a mandatory human-readable reason. The
transfer ordinal is **derived from the entity's ordered audit trail** — never a stored counter.
The audit surface is [universal-audit](../contracts/universal-audit.md); this is its content
contract for transfers.

Policy-governed maximum when needed:
```yaml
policy:
  type: validation
  enforcement_class: compliance
  rule: >
    If resource.ownership_transfer_count > 5
    AND resource_type == Compute.VM
    THEN deny: "VM has exceeded 5 ownership transfers — manual review required"
```

---

## 10. UDLM System Policies — Entity and Dependency Gaps

| Policy | Rule |
|--------|------|
| `RSE-014` | Ownership transfer count is unlimited by default. Policy may declare a maximum transfer count per resource type. Each transfer is immutably recorded with a monotonically incrementing transfer_number and mandatory reason field. |
| `RSE-015` | Bare metal resources declare `allocation_model: whole_unit` and `shareability.allowed: false`. Placement holds are exclusive. Providers must report the server's physical identity in the realized payload and notify of any sharing attempt. |
| `RSE-016` | Capacity confidence ratings trigger policy-governed automatic actions. LOW confidence triggers a Mode 1 Information Provider query by default in standard+ profiles. Profile determines the default action per confidence level. |
| `RSE-017` | Process Resource entities must declare `max_execution_time`. This field is mandatory. Execution time is enforced by the substrate-required Lifecycle Constraint Enforcer. Profile governs the default `on_max_exceeded` action. |
| `RSE-018` | Entity `billing_state` (billable, non_billable, or reduced_rate) is a first-class field injected by policy during state transitions. A consuming cost-analysis component reads `billing_state` for cost attribution. The substrate does not decide billing policy — it carries the billing signal. |

---

- **Tenant** — the mandatory ownership boundary for all Resource/Service Entities
- **Four States** — Intent, Requested, Realized, Discovered — the state lifecycle of a Resource/Service Request and Entity
- **Field-Level Provenance** — every state transition and ownership transfer is recorded in Entity provenance
- **Policy Engine** — evaluates provider events and unsanctioned changes, determines response actions
- **Service Dependencies** — Resource/Service Entities declare dependencies on other Entities
- **Resource Grouping** — Entities belong to a Tenant and optionally to additional Resource Groups
- **Provider Contract** — governs provider obligations including capacity reporting and event notification

---

*UDLM substrate document. Implementation-specific request/entity management mechanics, ownership enforcement at dispatch, provider notification consumption pipelines, and entity lifecycle monitoring implementations live in the consuming implementation's documentation.*
