# DCM Data Model — Entity Relationships



**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Service Dependencies](07-service-dependencies.md) | [Resource Grouping](08-resource-grouping.md) | [Information Providers](10-information-providers.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA + POLICY**
>
> Data: relationship records. Policy: Lifecycle Policy output schema



---

## 1. Purpose

The DCM Entity Relationship model is the **universal mechanism for expressing relationships between any two entities in DCM** — whether between two Resource/Service Entities, between an entity and external business data, or between entities at the service definition level.

A single relationship model is used everywhere. There is no separate binding mechanism for storage, no separate dependency graph structure, no separate business data association mechanism. One model serves all relationship types across the full lifecycle — from pre-realization planning through to post-realization management, drift detection, cost rollup, and rehydration.

This document defines the Entity Relationship Graph, which is the data structure underlying service dependency declaration (doc 07) and rehydration ordering. The Service Dependencies document retains content on rehydration ordering and failure handling, which operate on the relationship graph defined here.

---

## 2. Design Principle

**Single model. Minimum variance. Simple by default.**

The worst outcome is a data model with different mechanisms for expressing similar concepts. Every relationship in DCM — whether a VM requires storage, an application contains a web server, or a resource references a Business Unit — is expressed using the same structure. The only things that vary are the relationship type, role, and nature — all of which are declared fields, not structural differences.

---

## 3. The Universal Relationship Structure

Every relationship is a first-class data object with its own UUID. It is recorded **bidirectionally** — on both participating entities. The same `relationship_uuid` appears on both sides, identifying the relationship itself.

### 3.1 Relationship Record Structure

```yaml
relationship:
  relationship_uuid: <uuid — same on both sides of the relationship>
  
  # This entity's perspective
  this_entity_uuid: <uuid of the entity carrying this relationship record>
  this_role: <role this entity plays in the relationship>
  
  # The related entity
  related_entity_uuid: <uuid of the related entity>
  related_entity_type: <internal|external>
  related_entity_role: <role the related entity plays>
  
  # For external entities only
  information_provider_uuid: <uuid of Information Provider — if external>
  information_type: <e.g., Business.BusinessUnit — if external>
  lookup_method: <primary_key|fallback — how to resolve the external reference>
  
  # Relationship semantics
  relationship_type: <see Section 4>
  nature: <constituent|operational|informational>
  
  # Lifecycle policy — for constituent and operational relationships only
  lifecycle_policy:
    on_related_destroy: <destroy|retain|detach|notify>
    on_related_suspend: <suspend|retain|detach|notify>
    on_related_modify: <cascade|ignore|notify>
  
  # Metadata
  version: <Major.Minor.Revision>
  status: <active|suspended|terminated>
  created_timestamp: <ISO 8601>
  created_by_uuid: <uuid of entity or process that created this relationship>
  
  provenance:
    <standard field-level provenance>
```

### 3.2 Bidirectional Recording

Every relationship is recorded on both participating entities. The `relationship_uuid` is identical on both sides — it identifies the relationship itself, not one side of it.

**Example — VM requires Storage:**

```yaml
# On the VM Entity
relationships:
  - relationship_uuid: "rel-uuid-001"
    this_entity_uuid: "vm-uuid-001"
    this_role: compute
    related_entity_uuid: "storage-uuid-001"
    related_entity_type: internal
    related_entity_role: storage
    relationship_type: requires
    nature: constituent
    lifecycle_policy:
      on_related_destroy: destroy
      on_related_suspend: suspend
      on_related_modify: notify

# On the Storage Entity
relationships:
  - relationship_uuid: "rel-uuid-001"
    this_entity_uuid: "storage-uuid-001"
    this_role: storage
    related_entity_uuid: "vm-uuid-001"
    related_entity_type: internal
    related_entity_role: compute
    relationship_type: required_by
    nature: constituent
    lifecycle_policy:
      on_related_destroy: destroy
      on_related_suspend: suspend
      on_related_modify: notify
```

---

## 4. Relationship Types

Relationship types form a fixed standard vocabulary. Every type has an inverse — when you record the relationship on both entities, the type is expressed from each entity's perspective.

| Type | Inverse | Meaning |
|------|---------|---------|
| `requires` | `required_by` | This entity cannot function without the related entity |
| `depends_on` | `dependency_of` | This entity uses the related entity but can degrade without it |
| `contains` | `contained_by` | This entity is a logical container for the related entity |
| `references` | `referenced_by` | This entity references the related entity without owning or requiring it |
| `peer` | `peer` | Equal relationship — neither owns, requires, or contains the other |
| `manages` | `managed_by` | This entity has lifecycle management authority over the related entity |

---

## 5. Relationship Roles

Roles describe the **function** a related entity serves in a relationship. They are semantic labels that carry meaning for humans and for policy evaluation — they do not affect system behavior directly.

### 5.1 Standard Roles (DCM-defined)

| Role | Description |
|------|-------------|
| `compute` | Processing resource — VM, container, bare metal |
| `storage` | Storage resource — block, object, file |
| `networking` | Network resource — IP, VLAN, subnet, port |
| `security` | Security resource — firewall rule, certificate, HSM |
| `database` | Database resource — relational, NoSQL, time-series |
| `web` | Web tier resource — web server, reverse proxy, CDN |
| `app` | Application tier resource — app server, runtime |
| `cache` | Caching resource — in-memory cache, CDN layer |
| `queue` | Messaging resource — message queue, event stream |
| `pipeline` | Pipeline resource — CI/CD, data pipeline |
| `identity` | Identity resource — service account, credential |
| `monitoring` | Monitoring resource — metrics, logging, alerting |
| `business_unit` | Business Unit association |
| `cost_center` | Cost Center association |
| `product_owner` | Product Owner association |
| `regulatory_scope` | Regulatory or compliance scope association |

### 5.2 Custom Roles (extensible)

Organizations register custom roles for domain-specific relationship semantics. Custom roles are semantic labels only — they do not change system behavior. DCM core ignores unknown custom roles in operational decisions but carries them in payloads for downstream consumers.

```yaml
custom_role_registration:
  uuid: <uuid>
  name: <role name — e.g., trading_engine>
  description: <description>
  registered_by_tenant_uuid: <uuid — or null for global>
  category: <domain context — e.g., financial_services>
  version: <Major.Minor.Revision>
  status: <active|deprecated|retired>
```

---

## 6. Relationship Nature

Nature describes the **structural character** of a relationship — what it means for the entities involved.

| Nature | Meaning | Lifecycle Policy | Example |
|--------|---------|-----------------|---------|
| `constituent` | The related entity is a required component of this entity's definition | Required — declared on relationship | VM requires its boot disk |
| `operational` | The related entity is needed for operation but is not part of the definition | Required — declared on relationship | Web server depends on load balancer |
| `informational` | The related entity provides context or reference only — no operational dependency | Not applicable | Resource references its Business Unit |

---

## 6a. Relationship Type × Nature Matrix

The two dimensions of every relationship — type and nature — form a matrix of valid combinations. This matrix makes explicit what each combination means semantically and what behavioral rules apply. Not all 18 combinations are valid.

| | `constituent` | `operational` | `informational` |
|---|---|---|---|
| **`requires`** | ✅ **Core constituent** — entity cannot function without this component; component is part of its definition. Lifecycle policy required. | ✅ **Hard operational dependency** — entity cannot function without this but it is not a component. Lifecycle policy required. | ⚠️ **Invalid** — if an entity truly requires something, it has an operational or constituent dependency, not merely informational context. |
| **`depends_on`** | ✅ **Soft constituent** — entity degrades without this component but is not fully broken. Lifecycle policy required. | ✅ **Primary cell for allocated resources** — soft operational dependency. Cross-tenant allocations live here. Lifecycle policy required. | ✅ **Awareness dependency** — entity is aware of and tracks this entity but has no hard operational dependency. No lifecycle policy. |
| **`contains`** | ✅ **Ownership container** — this entity logically owns and contains the related entity as a component. Lifecycle policy required. | ⚠️ **Rare** — containing something operationally is unusual; most containment is constituent. Use with explicit justification. | ❌ **Invalid** — containing something purely informational has no semantic meaning. |
| **`references`** | ❌ **Invalid** — a reference implies no ownership or dependency; constituent implies the opposite. | ❌ **Invalid** — if there is an operational dependency, use `depends_on`. A reference that creates operational coupling is mismodeled. | ✅ **Pure informational reference** — primary cell for Business Unit, Cost Center, Product Owner relationships. No lifecycle policy. |
| **`peer`** | ❌ **Invalid** — peers cannot be constituent components of each other. | ✅ **Operational peers** — equal entities with mutual operational interdependency. Lifecycle policy on each side. | ✅ **Informational peers** — equal entities that are aware of each other. No lifecycle policy. |
| **`manages`** | ✅ **Component management** — this entity has lifecycle authority over a component it manages. Lifecycle policy required. | ✅ **Operational management** — this entity manages the operations of another entity without owning it. Lifecycle policy required. | ✅ **Audit/reporting management** — management relationship for visibility only. No lifecycle policy. |

**Key behavioral rules derived from the matrix:**

- Any `constituent` or `operational` relationship **must** declare a lifecycle policy (REL-004, REL-008)
- `constituent` + `requires` is the strongest possible relationship — both the entity and its component are mutually dependent; cross-tenant is prohibited (REL-010)
- `operational` + `depends_on` is the **allocated resource cell** — this is where cross-tenant allocations are modeled
- `informational` + `references` is the **business context cell** — Business Unit, Cost Center, Person relationships live here
- `❌ Invalid` combinations must be rejected by the Policy Engine at request time

---

## 6b. Cross-Tenant Relationships

### 6b.1 The Governing Principle

The relationship **nature** determines whether a cross-tenant relationship is permitted:

| Nature | Cross-Tenant Permitted? | Governing Rule |
|--------|------------------------|---------------|
| `constituent` | ❌ Never | REL-010 — DCM System Policy |
| `operational` | ✅ With explicit dual authorization | REL-011 — both Tenants must authorize |
| `informational` | ✅ Unless denied by hard tenancy | REL-012 — blocked only by `deny_all` |

### 6b.2 Hard Tenancy Declaration

Tenants declare their cross-tenant relationship policy. This is enforced by the GateKeeper Policy Engine at request time:

```yaml
tenant:
  uuid: <uuid>
  hard_tenancy:
    cross_tenant_relationships: explicit_only
    # deny_all:            no relationships of any nature may cross this boundary
    # explicit_only:       ALL cross-tenant must be explicitly authorized (DEFAULT)
    # operational_permitted: operational cross-tenant permitted; informational requires explicit auth
    # allow_all:           all cross-tenant permitted — requires justification
```

**Default is `explicit_only` — informational sharing is not open by default.** Every cross-tenant relationship of any nature requires an explicit `cross_tenant_authorization` record. This closes the model — cross-tenant access must be deliberately granted, not passively permitted.

### 6b.3 DCM System Policies for Cross-Tenant Relationships

| Policy | Rule |
|--------|------|
| `REL-010` | Constituent relationships may not cross Tenant boundaries |
| `REL-011` | Cross-tenant operational relationships require explicit authorization from both the owning Tenant and the consuming Tenant |
| `REL-012` | A Tenant with `hard_tenancy.cross_tenant_relationships: deny_all` may not participate in any cross-tenant relationship in any direction |
| `XTA-001` | Cross-tenant information sharing is closed by default — explicit authorization required for all cross-tenant relationships of any nature (see Policy Organization document Section 6) |
| `XTA-002` | Cross-tenant authorizations must specify who, what, when, and where |
| `XTA-003` | More specific authorizations take precedence: field_specific > resource_specific > tenant_global |
| `XTA-004` | All cross-tenant authorization decisions are policy-driven and DCM-enforced |
| `XTA-005` | Sovereignty constraints declared by either Tenant must be honored by all cross-tenant relationships |

---

## 6c. Allocated Resources — Cross-Tenant Operational Model

### 6c.1 Concept

An **Allocated Resource** is a pre-defined, discrete slice of a parent resource — provisioned by the owning Tenant and made available for consuming Tenants to claim. The allocated resource becomes a **first-class entity** in the consuming Tenant's scope with its own UUID, its own lifecycle, and its own governance — while maintaining a formal `depends_on` + `operational` relationship to the parent resource across the Tenant boundary.

This models real infrastructure practice: the network team pre-carves VLANs, the storage team pre-partitions pools, the platform team pre-defines availability zones. Consumers claim from what is available.

The relationship type is `depends_on` + `operational` — the allocated entity depends on the parent operationally but is not a constituent component of it. The allocation is the relationship; the entity itself is independently governed.

### 6c.2 Parent Resource — Available Allocations

The owning Tenant pre-defines allocations on the parent resource:

```yaml
parent_resource_entity:
  uuid: <uuid>
  tenant_uuid: <Infrastructure Tenant uuid>

  available_allocations:
    - allocation_uuid: <uuid>
      allocation_type: Network.VLANRange
      allocation_spec:
        vlan_range: "100-199"
        bandwidth: "10Gbps"
      status: <available|claimed|reserved>
      claimable_by:
        - tenant_uuid: <Tenant A uuid>
        - tenant_uuid: <Tenant B uuid>
        # Empty list = any authorized Tenant may claim

  active_allocations:
    - allocation_uuid: <uuid — matches available_allocations entry>
      claimed_by_tenant_uuid: <Tenant A uuid>
      claimed_entity_uuid: <uuid of Tenant A's allocated entity>
      claimed_at: <ISO 8601>
      notification_endpoint: <Tenant A's contact — from artifact metadata>
      # Parent uses this to notify Tenant A of lifecycle changes
```

### 6c.3 Allocated Entity — In the Consuming Tenant

When a consuming Tenant claims an available allocation, DCM creates a first-class entity in the consuming Tenant's scope:

```yaml
allocated_entity:
  uuid: <uuid — consuming Tenant's own entity>
  entity_type: infrastructure_resource  # ownership_model: allocation
  resource_type_uuid: <uuid of the allocated resource type>
  tenant_uuid: <Tenant A uuid>  # Belongs to the consuming Tenant

  allocation_spec:
    vlan_range: "100-199"
    bandwidth: "10Gbps"
    # The specific slice allocated to this Tenant

  parent_allocation:
    parent_entity_uuid: <parent resource uuid>
    parent_tenant_uuid: <Infrastructure Tenant uuid>
    allocation_uuid: <uuid — matches parent's available_allocations entry>

  lifecycle_state: OPERATIONAL

  parent_lifecycle_policy:
    on_parent_destroy: notify_then_detach
    on_parent_suspend: suspend
    on_parent_maintenance: notify
    on_parent_degrade: notify
    on_parent_capacity_change: notify

  relationships:
    - relationship_uuid: <uuid>
      related_entity_uuid: <parent resource uuid>
      related_entity_type: internal
      related_entity_tenant_uuid: <Infrastructure Tenant uuid>
      relationship_type: depends_on
      nature: operational
      cross_tenant: true
      allocation_uuid: <uuid — links to parent's allocation record>
      authorized_by:
        owning_tenant_policy_uuid: <policy permitting this allocation>
        consuming_tenant_policy_uuid: <policy permitting this dependency>

  artifact_metadata:
    <standard — owned_by Tenant A>
```

### 6c.4 Lifecycle Event Propagation

When the parent resource changes state, DCM iterates all active allocations and propagates according to each allocation's `parent_lifecycle_policy`:

```
Parent resource enters MAINTENANCE
  │
  ▼
DCM iterates active_allocations
  │
  For each active allocation:
  │  Read parent_lifecycle_policy.on_parent_maintenance
  │  → notify: dispatch lifecycle event to consuming Tenant
  │  → suspend: transition allocated entity to SUSPENDED state
  │  → detach: terminate relationship, allocated entity becomes independent
  │
  Policy Engine evaluates each propagation:
  │  SLA commitments that gate maintenance?
  │  Override policies in consuming Tenant?
  ▼
Events dispatched via notification_endpoint on each active_allocation record
```

### 6c.5 Claiming Flow

```
Parent Tenant pre-defines available_allocations on parent resource
  │
  ▼
Consuming Tenant A submits claim request
  │  Specifies: parent_entity_uuid, allocation_uuid
  ▼
Policy Engine evaluates:
  │  Is allocation_uuid still available?
  │  Is Tenant A in claimable_by list (or list is open)?
  │  Does Tenant A's cross_tenant policy permit this?
  │  Does Infrastructure Tenant's cross_tenant policy permit this?
  ▼
DCM creates:
  │  Allocated Entity (owned by Tenant A) with UUID
  │  depends_on / dependency_of relationship (bidirectional, cross_tenant: true)
  │  Updates parent's available_allocation status: available → claimed
  │  Adds record to parent's active_allocations
  │  Provenance recorded on both entities
  ▼
Infrastructure Tenant owner notified of new claim
  │  Via owned_by.notification_endpoint on the parent entity
```

---

## 7. Lifecycle Policies

Lifecycle policies declare what happens to an entity when its related entity changes state. They apply to `constituent` and `operational` relationships only — `informational` relationships have no lifecycle implications.

### 7.1 Policy Actions

| Action | Meaning |
|--------|---------|
| `destroy` | Destroy this entity when the related entity is destroyed |
| `retain` | Keep this entity when the related entity is destroyed — it becomes independent |
| `detach` | Detach this entity from the relationship — relationship terminated, entity retained |
| `notify` | Notify appropriate personas and trigger Policy Engine evaluation — no automatic action |
| `suspend` | Suspend this entity when the related entity is suspended |
| `cascade` | Cascade the change from the related entity to this entity |
| `ignore` | Take no action — the change to the related entity does not affect this entity |

### 7.2 Lifecycle Action Hierarchy — Save Overrides Destroy

When a shared resource has multiple active relationships and a lifecycle event triggers, each relationship may produce a different action recommendation. DCM resolves conflicts using a deterministic hierarchy — **the most conservative action always wins**:

```
retain        ← most conservative — entity preserved unconditionally
  │
notify        ← inform and wait — human decision required
  │
suspend       ← temporarily inactive — reversible
  │
detach        ← relationship released — entity becomes independent
  │
cascade       ← propagate state change from related entity
  │
destroy       ← least conservative — entity terminated
```

**The save_overrides_destroy rule (REL-018):** If any active relationship recommends `retain`, the entity is retained regardless of what any other relationship recommends — including relationships with `override: immutable` lifecycle policies. `retain` is the save. It always beats `destroy`.

This rule applies automatically and silently when the hierarchy resolves cleanly (e.g., `retain` beats `destroy`). It is recorded in the `lifecycle_conflict_record` with severity `info` for audit purposes but requires no notification.

### 7.3 Lifecycle Conflict Detection

**Not all multi-recommendation scenarios are conflicts.** The hierarchy resolves most cases deterministically. A conflict worth surfacing occurs when:

1. **Adjacent hierarchy levels** — two relationships recommend actions that are one step apart (e.g., `notify` vs `suspend`) — the hierarchy resolves it but the ambiguity is worth surfacing
2. **An immutable lifecycle lock couldn't be honored** — a GateKeeper set `on_related_destroy: destroy` with `immutable_ceiling: absolute` but `retain` from another relationship won per REL-018
3. **`notify` is the winning action** — inherently means human decision required; the notification should include the full conflict picture

**Conflict severity:**

| Scenario | Severity | Action |
|----------|---------|--------|
| `retain` beats `destroy` — non-adjacent levels | `info` | Logged only — working as designed |
| All relationships agree | None | No record needed |
| Adjacent levels (e.g., `notify` vs `suspend`) | `warning` | Notify entity owner and affected policy owners |
| `notify` is the winning action | `warning` | Notify owner — human decision required |
| Immutable lifecycle lock overridden by REL-018 | `critical` | Notify entity owner, policy owner, and platform admin |

**Lifecycle conflict record:**

```yaml
lifecycle_conflict_record:
  entity_uuid: <shared resource uuid>
  event_trigger: <parent_destroy | parent_suspend | parent_modify>
  triggering_entity_uuid: <uuid of entity that changed state>
  action_recommendations:
    - relationship_uuid: <uuid>
      related_entity_uuid: <VM-A uuid>
      recommended_action: destroy
      source: lifecycle_policy
    - relationship_uuid: <uuid>
      related_entity_uuid: <VM-B uuid>
      recommended_action: retain
      source: gatekeeper_policy
      policy_uuid: <uuid>
    - relationship_uuid: <uuid>
      related_entity_uuid: <VM-C uuid>
      recommended_action: notify
      source: lifecycle_policy
  resolved_action: retain
  resolution_rule: save_overrides_destroy
  conflict_detected: true
  conflict_severity: info
  notifications_sent:
    - recipient_uuid: <entity owner>
      message: "Lifecycle conflict resolved: retain overrode destroy and notify."
  recorded_at: <ISO 8601>
```

### 7.4 Lifecycle Policy Authority Hierarchy

Lifecycle policies follow the same three-tier authority model as override control:

```
Resource Type Specification default (lowest — portable default)
  │
  ▼
Provider Catalog Item default (provider preference)
  │
  ▼
Consumer declaration (at request time — within Resource Type bounds)
  │
  ▼
DCM System Policy (non-overridable — sovereignty and compliance mandates)
```

**Example:** A DCM System Policy might declare that all storage entities in a PCI-DSS scope must `retain` when their parent VM is destroyed — regardless of what the provider default or consumer declared.

---

## 7a. Shared Resource Model — Same-Tenant

### 7a.1 Concept

A **Shared Resource** is an entity within a single Tenant that has active relationships from multiple parent entities. Rather than being exclusively owned by one parent, it is referenced by N parents — each with its own lifecycle relationship.

This is the same-tenant counterpart to the cross-tenant Allocated Resource model. Both use reference counting to defer destructive actions. The sharing model applies within a Tenant; the allocation model applies across Tenant boundaries.

**Examples:** Shared NFS volume mounted by multiple VMs. Shared database cluster used by multiple application services. Shared VLAN used by multiple VMs. Shared TLS certificate used by multiple services.

### 7a.2 The `sharing_model` Declaration

The Resource Type Specification declares whether instances of a type can be shared. Individual entities carry the runtime sharing state:

```yaml
# On the Resource Type Specification
resource_type_spec:
  fully_qualified_name: Storage.SharedVolume
  shareability:
    allowed: true
    default_sharing_scope: tenant    # tenant | cross_tenant
    max_active_relationships: null   # null = unlimited; integer = cap (e.g., license seats)

# On the entity instance
entity:
  uuid: <uuid>
  sharing_model:
    shareable: true
    sharing_scope: tenant
    active_relationship_count: 3     # DCM maintains this — do not set manually
    minimum_relationship_count: 0    # below this, on_last_relationship_released fires
    on_last_relationship_released: <destroy | retain | notify>
    # destroy: entity destroyed when last relationship is released
    # retain:  entity persists independently — becomes unowned
    # notify:  notify owner, entity enters PENDING_DECISION
```

**`shareability.allowed: false`** on a Resource Type (e.g., `Compute.BootDisk`) means the Policy Engine rejects any attempt to create a second active constituent or operational relationship to an instance. Boot disks, primary network interfaces, and similar exclusively-owned resources are non-shareable by type definition (REL-017).

### 7a.3 Reference Count Lifecycle

DCM maintains `active_relationship_count` automatically:

- **Relationship created** → `active_relationship_count` incremented
- **Relationship released** (parent decommissioned, relationship detached) → `active_relationship_count` decremented
- **Informational relationships** → never counted (REL-016)
- **Count reaches `minimum_relationship_count`** → `on_last_relationship_released` fires

When a parent entity is destroyed and has a relationship to a shared resource:

```
Parent entity destroyed
  │
  ▼
DCM collects action recommendations from all active relationships on shared resource
  │  Each relationship's lifecycle policy produces one recommendation
  │  Informational relationships excluded
  │
  ▼
Action resolution — save_overrides_destroy hierarchy (REL-018)
  │  Most conservative recommendation wins
  │  Lifecycle conflict record created if multiple recommendations differ
  │
  ▼
Execute winning action
  │  retain → shared resource unaffected
  │  notify → PENDING_DECISION state, notifications dispatched
  │  suspend → shared resource suspended
  │  detach → parent's relationship released, count decremented
  │  destroy → only if count reaches minimum_relationship_count (REL-015)
  │
  ▼
Deferred destruction record created (if action was deferred)
```

### 7a.4 Deferred Destruction Records

Every time a destructive action is deferred by the reference count mechanism:

```yaml
deferred_destruction_record:
  entity_uuid: <shared resource uuid>
  triggering_request_uuid: <uuid of parent's decommission request>
  triggering_relationship_uuid: <uuid of relationship being released>
  relationship_count_before: 3
  relationship_count_after: 2
  action_taken: deferred
  reason: "active_relationship_count above minimum. Destruction deferred."
  remaining_relationships:
    - relationship_uuid: <uuid>
      related_entity_uuid: <VM-B uuid>
      relationship_type: required_by
    - relationship_uuid: <uuid>
      related_entity_uuid: <VM-C uuid>
      relationship_type: dependency_of
  recorded_at: <ISO 8601>
```

When the last relationship is released:

```yaml
deferred_destruction_record:
  relationship_count_before: 1
  relationship_count_after: 0
  action_taken: "on_last_relationship_released → destroy"
  reason: "Last active relationship released. Executing on_last_relationship_released."
  recorded_at: <ISO 8601>
```

### 7a.5 Unified with the Allocated Resource Model

The same-tenant sharing model and the cross-tenant allocated resource model are the same concept at different scopes:

| Dimension | Same-Tenant Sharing | Cross-Tenant Allocation |
|-----------|--------------------|-----------------------|
| Scope | Within one Tenant | Across Tenant boundaries |
| Pre-definition | Not required — relationships declared at request time | Parent pre-defines `available_allocations` |
| Reference tracking | `active_relationship_count` on entity | `active_allocations` list on parent |
| Destruction deferral | Deferred until count reaches minimum | Deferred until last allocation released |
| Lifecycle events | `on_last_relationship_released` | `parent_lifecycle_policy` per allocation |
| Governed by | REL-015 through REL-019 | REL-011, REL-014 |

---

## 8. Relationship Declarations — Where They Live

Relationship declarations exist at multiple levels, each building on the previous:

### 8.1 Resource Type Specification (structural ceiling)

Declares what relationships are **possible** for a resource type. Sets the ceiling — lower levels can only declare relationships within these bounds.

```yaml
resource_type: Compute.VirtualMachine
possible_relationships:
  - role: storage
    relationship_type: requires
    nature: constituent
    permitted_related_types:
      - Storage.Block
      - Storage.File
    default_lifecycle_policy:
      on_related_destroy: destroy
      on_related_suspend: suspend
    binding_types_permitted: [owned, referenced]
    consumer_declarable: true
    # Consumer can declare binding_type and lifecycle_policy override

  - role: networking
    relationship_type: requires
    nature: constituent
    permitted_related_types:
      - Network.IPAddress
    default_lifecycle_policy:
      on_related_destroy: destroy
    consumer_declarable: false
    # DCM manages this automatically — consumer cannot override
```

### 8.2 Catalog Item (offering-specific)

Declares the **actual relationships** for a specific curated offering. Can only be more restrictive than the Resource Type Specification.

```yaml
catalog_item: Production VM
relationships:
  - role: storage
    relationship_type: requires
    nature: constituent
    related_catalog_item_uuid: <uuid of Standard Block Storage catalog item>
    lifecycle_policy:
      on_related_destroy: retain
      # Overrides Resource Type default of destroy
      # Storage persists even if VM is destroyed — production data protection
    binding_type: owned
```

### 8.3 Request Time (consumer-declared)

The consumer declares relationships in their request. Bundled declarations (storage fields within a VM request) are automatically expanded into relationship records by the Request Payload Processor.

```yaml
# Explicit relationship declaration in a request
request:
  resource_type: Compute.VirtualMachine
  # ... other fields ...
  relationships:
    - role: storage
      relationship_type: requires
      binding_type: referenced
      related_entity_uuid: <uuid of existing Storage Entity>
      # Consumer referencing existing storage — not creating new

# Bundled declaration — expanded automatically
request:
  resource_type: Compute.VirtualMachine
  storage:
    disks:
      - name: boot
        capacity: 100GB
        # Processor expands this into a Storage Entity stub
        # and a relationship record with binding_type: owned
```

### 8.4 External Data Relationships

Relationships to external data entities follow the same structure with `related_entity_type: external`:

```yaml
# On a VM Entity — relationship to external Business Unit
relationships:
  - relationship_uuid: <uuid>
    this_entity_uuid: <vm-uuid>
    this_role: <consumer>
    related_entity_uuid: <uuid of external_entity_reference>
    related_entity_type: external
    information_provider_uuid: <uuid of HR Information Provider>
    information_type: Business.BusinessUnit
    relationship_type: references
    role: business_unit
    nature: informational
    lookup_method: primary_key
```

---

## 9. Bundled Declaration Expansion

When a consumer includes resource configuration as bundled fields (e.g., storage within a VM request), the Request Payload Processor expands these into first-class entities and relationship records.

### 9.1 Expansion Process

```
Consumer submits bundled VM request with storage fields
  │
  ▼
Request Payload Processor
  │  Reads expansion rules from Resource Type Specification
  │  For each expandable field:
  │    1. Creates a Resource/Service Entity stub (PENDING state)
  │       with its own UUID, Tenant membership, Resource Type
  │    2. Creates a Relationship record on both the parent stub
  │       and the child stub
  │    3. Applies lifecycle policy from:
  │       consumer declaration → provider default → Resource Type default
  │       → DCM System Policy override
  │    4. Adds the child entity stub to the relationship graph
  ▼
Policy Engine validates:
  │  Binding type is permitted by Resource Type Specification
  │  Consumer has override_matrix permission to declare binding type
  │  Lifecycle policy is not overridden by a DCM System Policy
  ▼
Service Provider receives:
  │  Parent entity request payload
  │  Child entity stub UUIDs embedded in parent payload
  │  Provisions resources natively
  │  Returns realized payloads for all entities in DCM unified format
  ▼
DCM updates:
  │  Parent entity: PENDING → REALIZED
  │  Child entities: PENDING → REALIZED
  │  All relationship records: status → active
  │  Full provenance recorded on all entities and relationships
```

### 9.2 Expansion Rules in Resource Type Specification

The expansion rule declares which fields expand into entities and how:

```yaml
field_definition:
  field_name: storage
  type: object
  expansion:
    expand_to_entity: true
    entity_resource_type_uuid: <uuid of Storage.Block>
    entity_resource_type_name: Storage.Block
    default_binding_type: owned
    binding_types_permitted: [owned, referenced]
    default_lifecycle_policy:
      on_related_destroy: destroy
      on_related_suspend: suspend
    consumer_can_override_lifecycle: true
    consumer_can_override_binding_type: true
```

---

## 10. The Entity Relationship Graph

All relationships across all entities form a traversable **Entity Relationship Graph** — the complete map of how all entities in DCM relate to each other.

### 10.1 Graph Properties

- Every node is a Resource/Service Entity (internal or external reference)
- Every edge is a Relationship with a UUID
- The graph is bidirectional — traversable from any node in any direction
- Every node exists exactly once — shared entities appear once with multiple relationship edges
- Circular relationships are invalid and must be rejected

### 10.2 Graph and the Four States

The relationship graph exists across all four states:

| State | Graph Role |
|-------|-----------|
| Intent State | Graph declared at request time — nodes are intent stubs |
| Requested State | Graph fully assembled — nodes are PENDING entity stubs with UUIDs |
| Realized State | Graph populated — nodes are REALIZED entities with full provenance |
| Discovered State | Graph used for comparison — discovered entities matched against realized graph |

### 10.3 Graph Applications

| Application | How the Graph is Used |
|-------------|----------------------|
| **Rehydration** | Full graph traversal from a root entity — all related entities identified and realized in dependency order |
| **Cost Rollup** | Graph traversal accumulates costs across all related constituent entities |
| **Drift Detection** | Discovered State graph compared against Realized State graph — structural and data differences identified |
| **Decommission** | Graph traversal determines decommission order — lifecycle policies applied at each edge |
| **Placement** | Pre-realization graph used to understand full resource footprint for placement decisions |
| **Impact Analysis** | Graph traversal from any node identifies all entities affected by a change |

---

## 11. Relationship Integrity

### 11.1 DCM System Policies for Relationships

| Policy | Rule |
|--------|------|
| `REL-001` | Every relationship must have a UUID |
| `REL-002` | Every relationship must be recorded on both participating entities |
| `REL-003` | Circular relationships are invalid and must be rejected |
| `REL-004` | A constituent or operational relationship must have a lifecycle policy declared somewhere in the authority chain before provider dispatch |
| `REL-005` | External relationships must reference a registered Information Provider |
| `REL-006` | Relationship types must be from the standard vocabulary |
| `REL-007` | Consumer-declared binding types must be permitted by the Resource Type Specification |
| `REL-008` | A constituent relationship lifecycle policy may not be set to `ignore` for `on_related_destroy` |
| `REL-009` | Lifecycle policy conflicts between policies are resolved by the standard Policy Engine authority hierarchy — no special case |
| `REL-010` | Constituent relationships may not cross Tenant boundaries |
| `REL-011` | Cross-tenant operational relationships require explicit authorization from both the owning Tenant and the consuming Tenant |
| `REL-012` | A Tenant with `hard_tenancy.cross_tenant_relationships: deny_all` may not participate in any cross-tenant relationship in any direction |
| `REL-013` | `❌ Invalid` relationship type × nature combinations (per the matrix in Section 6a) must be rejected by the Policy Engine at request time |
| `REL-014` | An allocated resource claim requires a matching `available` allocation record on the parent entity |
| `REL-015` | A destructive lifecycle action on a shared resource entity (`ownership_model: shareable` (see [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md))) is deferred until `active_relationship_count` reaches `minimum_relationship_count` |
| `REL-016` | Informational relationships do not contribute to `active_relationship_count` on shared resource entities |
| `REL-017` | A Resource Type Specification with `shareability.allowed: false` must reject any attempt to create more than one active constituent or operational relationship to an instance of that type |
| `REL-018` | When a lifecycle event produces multiple action recommendations on a shared resource, the most conservative action wins per the hierarchy: `retain > notify > suspend > detach > cascade > destroy` (save_overrides_destroy) |
| `REL-019` | When lifecycle action recommendations conflict, a `lifecycle_conflict_record` is created. Conflicts at `warning` or `critical` severity trigger notifications to the entity owner and affected policy owners |

### 11.2 Lifecycle Policy Conflict Resolution

Lifecycle policy fields on relationships are fields. They carry the same `override` metadata, the same provenance obligations, and resolve under the same Policy Engine authority hierarchy as any other field in DCM. There is no special case — minimum variance applies.

**Authority chain for a relationship lifecycle policy field (lowest to highest):**

```
Resource Type Specification default
  → Provider Catalog Item default
    → Consumer declaration at request time
      → Transformation Policy (may set override: constrained)
        → Validation Policy (checks — no modification)
          → GateKeeper Policy (may set override: immutable)
            → DCM System Policies REL-008, REL-009 (non-overridable)
```

**Within the Policy Engine**, the priority schema governs conflicts between policies at the same tier. Highest numeric priority value within a tier runs first. The first policy to set `override: immutable` on a lifecycle policy field locks it — all subsequent policies in that execution find it locked and cannot modify it.

**Conflict detection at ingestion** applies to lifecycle policy declarations in policies exactly as it does to layer fields:
- Two policies both declare `on_related_destroy` for the same relationship type without priority differentiation → CONFLICT ERROR at ingestion — both owners notified
- One has higher priority value → Higher wins, documented in provenance
- Equal priority → CONFLICT ERROR

**`immutable_ceiling: absolute` applies here.** A sovereign compliance mandate that storage must always be retained when a VM is destroyed — `on_related_destroy: retain` with `immutable_ceiling: absolute` — cannot be overridden by any future policy regardless of priority.

**Example — compliant lifecycle policy field with override control:**

```yaml
lifecycle_policy:
  on_related_destroy:
    value: retain
    metadata:
      override: immutable
      locked_by_policy_uuid: <uuid of Global GateKeeper>
      locked_at_level: global
      basis_for_value: "Compliance mandate — storage must outlive VM for audit retention"
      immutable_ceiling: absolute
    provenance:
      origin:
        source_type: policy
        source_uuid: <policy uuid>
        timestamp: <ISO 8601>
      modifications: []
```

### 11.2a Cross-Tenant Dependency System Policies

| Policy | Rule |
|--------|------|
| `DEP-001` | Cross-tenant constituent dependencies are prohibited — a dependency that would produce a constituent cross-tenant relationship is rejected at dependency graph construction time |
| `DEP-002` | Cross-tenant operational dependencies require a valid available allocation record on the target resource — failure returns `CROSS_TENANT_DEPENDENCY_UNAVAILABLE` |
| `DEP-003` | A Resource Type Specification may only declare cross-tenant dependencies if explicitly marked `cross_tenant: permitted` — default is `cross_tenant: not_permitted` |

### 11.3 Relationship Versioning and Deprecation

Relationships follow the universal versioning and deprecation model. A relationship version changes when its lifecycle policy, nature, or role changes. Terminated relationships are retained in provenance permanently.

---

## 12. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | How are relationship conflicts resolved — two policies declare different lifecycle policies for the same relationship? | Policy model | ✅ Resolved — standard Policy Engine authority hierarchy; REL-008 and REL-009 |
| 2 | Should relationship roles be validated against the role registry at request time, or is validation advisory? | Operational complexity | ✅ Resolved — advisory default; Resource Type Spec may declare permitted_relationship_roles with role_validation: advisory/enforced; community role catalog; see doc 09 Section 12 (REL-020) |
| 3 | How does the relationship graph interact with multi-tenant scenarios — can a relationship cross Tenant boundaries? | Multi-tenancy | ✅ Resolved — nature governs; constituent never; operational with dual auth; informational unless deny_all; REL-010/011/012 |
| 4 | Should there be a maximum relationship graph depth to prevent runaway complexity? | Operational governance | ✅ Resolved — profile-governed max depth: 15 standard/prod, 10 fsi/sovereign; circular detection always enforced; depth = traversal distance; see doc 09 Section 12 (REL-021) |
| 5 | How are shared entities represented in the relationship graph — an entity required by multiple parents? | Graph model | ✅ Resolved — sharing_model declaration; active_relationship_count; save_overrides_destroy hierarchy (REL-018); lifecycle_conflict_record; REL-015 through REL-019 |


---

## 14. Notification Traversal Rules

The entity relationship graph is the source of truth for notification audiences. This section defines how relationships govern notification traversal for the Notification Model (doc 23).

### 14.1 Relationship Properties Relevant to Notifications

Every relationship carries two properties that the Notification Router uses for audience resolution:

```yaml
relationship:
  type: attached_to
  stake_strength: <required|preferred|optional>
  notification_relevance:
    # Declared in the Resource Type Spec for this relationship type
    # Can be overridden per relationship instance
    notifiable_events: [entity.decommissioning, entity.state_changed, entity.ttl_expired]
    traversal_depth: 1               # how many hops from this relationship
    audience_role: stakeholder       # role assigned to notified party
```

### 14.2 Stake Strength and Notification Threshold

Different event types use different minimum stake strengths for notification:

| Event Category | Minimum Stake Strength | Rationale |
|---------------|----------------------|-----------|
| `entity.decommissioning` | optional | All stakeholders should know |
| `entity.decommissioned` | optional | All stakeholders should know |
| `entity.state_changed` (to FAILED/DEGRADED) | required | Only required stakeholders are affected |
| `entity.state_changed` (to OPERATIONAL) | preferred | Recovery notification broader |
| `entity.ttl_expired` | required | Only required stakeholders need to act |
| `drift.detected` | — (owner only) | Drift is the owner's concern |
| `dependency.state_changed` | required | Only affects required dependents |

The minimum stake strength threshold per event type is declared in the resource type specification and can be overridden by a platform-domain policy.

### 14.3 Notification Traversal and Graph Depth

Notification traversal respects the same depth limits as other graph operations (REL-021: max depth 15 standard/prod, 10 fsi/sovereign). However, notification traversal depth is typically much shallower — most event types only traverse depth 1 (direct relationships).

```
VLAN-100 decommissioning (depth 1 traversal):
  Direct relationships:
    ├── VM-A (attached_to, required) → AppTeam notified as stakeholder
    ├── VM-B (attached_to, required) → DevTeam notified as stakeholder
    └── VM-C (attached_to, optional) → OpsTeam notified as observer
  No depth-2 traversal — VM-A's dependencies are not notified about VLAN changes
```

Security events (sovereignty violation, audit chain break) use depth 0 (system audiences only — no relationship traversal needed).

### 14.4 Notification Traversal Policies

| Policy | Rule |
|--------|------|
| `REL-022` | Notification traversal follows relationship edges from the changed entity. Traversal depth per event type is declared in the Resource Type Specification. Default traversal depth is 1. |
| `REL-023` | Notification traversal respects sovereignty boundaries. Cross-tenant notifications carry only content authorized for the receiving Tenant. |
| `REL-024` | The same actor reached via multiple relationship paths receives a single notification with all applicable audience_roles listed. |


---

## 13. Related Concepts

- **Entity Relationship Graph** — the complete traversable graph of all entity relationships in DCM
- **Information Provider** — provider type for external data entities referenced in relationships
- **Bundled Declaration Expansion** — processor mechanism for expanding bundled fields into entities and relationships
- **Lifecycle Policy** — declares what happens to an entity when its related entity changes state
- **Service Dependencies** — document covering rehydration ordering and failure handling on the relationship graph
- **Resource Type Specification** — declares possible relationships for a resource type
- **External Entity Reference** — stable pointer to data owned by an external system


## 12. Relationship Gap Resolutions — Q58 and Q60

### 12.1 Relationship Role Validation (Q58)

Relationship roles are semantic labels — human-readable identifiers for the function a member plays in a relationship. By default, role validation is advisory. Resource Type Specifications may declare a closed set of permitted roles with enforced validation.

```yaml
resource_type_spec:
  fully_qualified_name: Compute.VirtualMachine
  permitted_relationship_roles:
    - role: storage
      relationship_types: [requires]
      permitted_related_types: [Storage.Block, Storage.File]
    - role: networking
      relationship_types: [requires]
      permitted_related_types: [Network.IPAddress, Network.Port]
    - role: dns
      relationship_types: [depends_on]
      permitted_related_types: [DNS.Record]
    - role: load_balancer
      relationship_types: [depends_on]
      permitted_related_types: [Network.LoadBalancer]
  role_validation: advisory   # advisory | enforced
  # advisory: unknown roles produce a warning in assembly provenance
  # enforced: unknown roles are rejected at request time
```

**Community role catalog:** DCM ships a non-authoritative reference list of commonly-used roles. Organizations freely declare roles not in the catalog when role_validation is advisory.

### 12.2 Maximum Relationship Graph Depth (Q60)

Relationship graph depth is limited to a profile-governed maximum. Circular relationship detection is always enforced regardless of depth configuration.

```yaml
relationship_depth_policy:
  max_depth: 15                  # configurable via Policy Group
  on_max_exceeded: reject        # reject with clear error
  cycle_detection: always        # non-configurable — always enforced
  # Depth = maximum traversal distance between any two entities
  # NOT the count of relationships on one entity
```

**Profile-governed defaults:**

| Profile | Max Depth | Rationale |
|---------|----------|-----------|
| `minimal` | 25 | Home lab — free composition |
| `dev` | 20 | Development — generous |
| `standard` | 15 | Production baseline |
| `prod` | 15 | Production |
| `fsi` | 10 | Tighter — complex graphs harder to audit |
| `sovereign` | 10 | Maximum control |

**Note:** Relationship depth differs from dependency depth (ENT-008). Dependency depth counts the provisioning chain. Relationship depth counts the graph traversal distance between any two entities. A VM with 50 IP address relationships has depth 1, not 50.

---

## 13. System Policies — Relationship Gaps

| Policy | Rule |
|--------|------|
| `REL-020` | Relationship roles are semantic labels. Resource Type Specifications may declare permitted_relationship_roles with advisory or enforced validation. Advisory produces assembly warnings for unknown roles. Enforced rejects unknown roles at request time. DCM maintains a community role catalog as a non-authoritative reference. |
| `REL-021` | Relationship graph depth is limited to a profile-governed maximum (default: 15 for standard/prod; 10 for fsi/sovereign). Circular relationship detection is always enforced regardless of depth configuration. Depth is measured as the maximum traversal distance between any two entities in the relationship graph. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*