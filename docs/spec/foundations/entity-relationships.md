# UDLM — Entity Relationships

**Related Documents:** [Context and Purpose](context-and-purpose.md) | [Resource Type Hierarchy](resource-type-hierarchy.md) | [Resource/Service Entities](resource-service-entities.md) | [Service Dependencies](service-dependencies.md) | [Resource Grouping](resource-grouping.md) | [Information Providers](../contracts/information-providers.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM data model.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](foundations.md).
> more of those three abstractions.
>
> **This document maps to: DATA + POLICY**
>
> Data: relationship records. Policy: Lifecycle Policy output schema

---

## 1. Purpose

One relationship model serves every case: two Resource/Service Entities, an entity and external
business data, entities at the service-definition level. There is no separate binding mechanism
for storage, no separate dependency-graph structure, no separate business-data association. The
authoritative edge model is [data-model-core §4](data-model-core.md); the relation vocabulary and
its rules (`REL-001..003`) are [common-elements §9](../../../registry/common-elements.md); the
machine shape is `dependencies[]` in `registry/realized-entity.schema.json`. This document owns
what builds ON that model: the cross-tenant rules (`XTA-*`), the allocated- and shared-resource
operational models, relationship lifecycle policies, the declaration tiers, bundled expansion,
notification traversal, and the graph itself (`ERL-*`, `REL-005+`).

**Why relationships exist at all.** Relationships are not bookkeeping — they are what lets the control plane act on a system instead of a pile of independent resources. From the graph the control plane **auto-resolves dependencies** (a VM that `requires` a network triggers the network's provisioning), **orders lifecycle operations** (build, suspend, destroy, and rehydrate in dependency order), computes **blast radius** (what is affected if this entity changes state), and rolls up cost and ownership. Without the relationship the platform cannot sequence or reason about impact; the relationship is the price of that automation.

**Users should rarely hand-write relationships.** The common case is **inferred**, not authored. A catalog item or resource type declares its standard relationships once (the structural ceiling, §10.1); when a consumer requests it, the control plane expands those automatically (§11). A consumer only writes an explicit relationship for the **exception** — a non-standard cross-link the catalog could not know about.

---

## 2. The Relationship Record

An edge is **declared one-sided and derived two-sided**: it lives on the declaring entity's
record as a `dependencies[]` entry (`registry/realized-entity.schema.json`), and the inverse
reading is **computed**, never stored — every `edge_type` has a derivable inverse, so the graph
is navigable both ways without a second record (`GRAPH-001..003`,
`tests/check_graph_integrity.py`). There is no relationship object with its own uuid, no
`direction` field, and no inverse *type* — an old `required_by` is just the inbound reading of a
`depends_on`.

**Authored by handle, resolved by uuid** (AEP-124 — author by handle, resolve at reserve): at
authoring time the target may not be realized, so the edge names it by `target_handle`; the
substrate resolves `target_uuid` at reserve. The uuid never has to be known in advance.

```yaml
# Authored — a VM's intent, by handle (no uuids yet). Three edge_types at work:
dependencies:
  - target_handle: "storage/primary"     # its boot disk
    edge_type: depends_on
    strength: hard                       # cannot function without it → constituent (derived)
    relation: disk                       # declared by Compute.VM (REL-001)

  - target_handle: "business-units/payments"
    edge_type: references                # informational (derived) — no lifecycle coupling
    relation: business_unit

  - target_handle: "vm/db-replica-b"     # equal HA partner
    edge_type: depends_on
    strength: soft                       # orders but never blocks (DEP-006)
    relation: cluster_peer

# Resolved — the same edges at reserve, uuids filled in:
dependencies:
  - target_uuid: "<storage uuid>"        # resolved from "storage/primary"
    edge_type: depends_on
    strength: hard
    relation: disk
```

The storage entity records nothing: its inbound `depends_on` reading is derived from the VM's
declaration when the graph is traversed.

---

## 3. Edge Model — edge_type + relation

Every edge carries two tiers, one authoritative field each (data-model-core §4, common-elements §9):

- **`edge_type`** — closed, universal: `depends_on` (`strength: hard|soft`), `contained_by`, `binds_to` (`target_field`), `references`. Ordering, traversal, and lifecycle projection consume ONLY `edge_type` + `strength`. Aligned with OASIS TOSCA root relationship types and ECMA-424 CycloneDX `dependsOn`.
- **`relation`** — domain tier: a name DECLARED by the pinned Resource Type (`relationships[].name`), adopted from a standard where one names the concept (RFC 8343/8345, TOSCA). A relation **refines** its edge_type and never overrides the edge_type's ordering semantics (REL-003); a consumer that does not understand a relation falls back to edge_type behaviour — the dependency graph is always a strict projection of the data.

**The inverse is derived** (§2): one edge, declared on the depending side; the inbound reading is computed at traversal. There is no separate inverse *type*.

`references` and a declared peer `relation` exist so `depends_on` is never overloaded to mean "just points at" — they carry **no** lifecycle coupling, which ordering edge_types must never imply. *Example:* a VM `references` its **Business Unit** / Cost Center / Product Owner so cost rollup, ownership, and reporting work — but destroying or suspending the Business Unit must **not** touch the VM. *Example (peer):* the members of a cluster (two database replicas, two firewall HA partners) each declare a `cluster_peer` relation — equal entities where neither owns or contains the other, so lifecycle authority sits on each side independently.

---

## 4. Relationship Nature (a derived axis)

**Nature is derived from the edge model, not stored as a field** (data-model-core §4). It is a reading of `edge_type`: `constituent` = `contained_by` / `constituents[]` membership; `operational` = an ordering edge_type (`depends_on` / `binds_to`); `informational` = `references`. It is retained as a vocabulary because the cross-tenant, matrix, and lifecycle rules below are stated in terms of it — but it is computed from `edge_type`, never authored independently.

Nature describes the **structural character** of a relationship — what it means for the entities involved.

| Nature | Meaning | Lifecycle Policy | Example |
|--------|---------|-----------------|---------|
| `constituent` | The related entity is a required component of this entity's definition | Required — declared on relationship | VM requires its boot disk |
| `operational` | The related entity is needed for operation but is not part of the definition | Required — declared on relationship | Web server depends on load balancer |
| `informational` | The related entity provides context or reference only — no operational dependency | Not applicable | Resource references its Business Unit |

> **`informational` is a nature reading, not a stored duplicate of `references`.** Under the derived model (this section's opening; data-model-core §4) nature is **computed from `edge_type`, never authored**: an edge is informational exactly when it is a `references` edge — the one `edge_type` that carries **no lifecycle coupling** ("track this edge but never cascade lifecycle across it"). A peer or management *relation* is expressed as a declared `relation` name **refining** a `references` edge — lifecycle-inert by construction; a peer or management concept is always a declared `relation` refining an edge_type (§3).

---

## 5. Common Patterns in the Edge Model

With nature derived from `edge_type` (§4, data-model-core §4), each `edge_type` has exactly one nature reading, so invalid
combinations are not representable. The recurring patterns:

| Pattern | Expressed as | Nature (derived) | Lifecycle policy |
|---|---|---|---|
| Core constituent (VM ↔ its boot disk) | `constituents[]` / `contained_by` | `constituent` | required |
| Operational dependency (incl. cross-tenant allocation) | `edge_type: depends_on` + `strength: hard\|soft` | `operational` | required |
| Business context (Business Unit, Cost Center, Owner) | `edge_type: references` | `informational` | none |
| Cluster members / HA partners | mutual `edge_type: depends_on` (`strength: soft`), one edge per direction, with a declared `relation` (e.g. `peer_of`) | `operational` | per side |
| Component management authority | a declared `relation` (e.g. `manages`) refining `depends_on` or `contained_by` | per edge_type | required |

**Behavioral rules:**

- Any `constituent` or `operational` relationship **must** declare a lifecycle policy (ERL-004, REL-008)
- Constituent edges are the strongest coupling — cross-tenant is prohibited (`GRP-INV-002`)
- `depends_on` with derived `operational` nature is the **allocated resource cell** — where cross-tenant allocations are modeled (§7)
- `references` with derived `informational` nature is the **business context cell** — Business Unit, Cost Center, Person relationships live here

---

## 6. Cross-Tenant Relationships

### 6.1 The Governing Principle

The relationship **nature** determines whether a cross-tenant relationship is permitted:

| Nature | Cross-Tenant Permitted? | Governing Rule |
|--------|------------------------|---------------|
| `constituent` | ❌ Never | `GRP-INV-002` — a non-overridable structural invariant |
| `operational` | ✅ With explicit dual authorization | REL-011 — both Tenants must authorize |
| `informational` | ✅ Unless denied by hard tenancy | REL-012 — blocked only by `deny_all` |

### 6.2 Hard Tenancy Declaration

Tenants declare their cross-tenant relationship policy. This is enforced by the Validation Policy Engine at request time:

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

### 6.2a What the refusal looks like

Closed-by-default settles *whether* an unauthorized crossing is permitted. It leaves open what
the submitter is handed when they attempt one — and that answer decides whether the boundary is
usable. Three failure modes are available to a naive implementation, and each is worse than the
refusal it replaces.

The first is **repair**: dropping the offending edge and realizing the rest. The graph now
validates, the request succeeds, and the consumer receives a resource whose dependency is
missing — a partial realization nobody asked for, discovered later as a runtime failure. The
whole intent is refused instead; a hard dependency is a required part of the declaration, and
removing a required part is a different request.

The second is **mistyping**: reporting the crossing as a schema error, an unresolvable
reference, or a bare authorization failure. All three are true in a sense and none routes the
submitter anywhere. The refusal is emitted as `authz.cross_tenant_unauthorized` and names the
mechanism that would make the reference legal — a `cross_tenant_authorization` grant from the
owning tenant, recorded as a grouping of that class (`registry/profile.schema.json` / `Grouping`).

The third is **over-explaining**. A refusal that helpfully describes what the submitter tried
to reach — its type, its name, its state — has disclosed another tenant's inventory to prove
they may not see it. The refusal discloses existence-as-forbidden and nothing further, and it
gives the same answer whether or not the target exists, so that the error channel cannot be
used to enumerate a foreign estate one identifier at a time
([`docs/spec/contracts/error-model.md`](../contracts/error-model.md) §3.3 — the existence-disclosure
rule, which is where not-found and not-authorized are separated for the whole model).

`XTA-006` binds these three. `XTA-007` covers the record: a cross-tenant refusal concerns two
tenants, so the refusal record names both — today's denial records carry a single
`tenant_uuid`, which leaves the owning tenant unable to see that their resource was reached for.

### 6.3 the control plane System Policies for Cross-Tenant Relationships

Three relationship rules govern this surface and are **defined in §13.1**, not restated here:
`GRP-INV-002` (a constituent relationship may not cross a tenant boundary), `REL-011` (a cross-tenant
operational relationship needs authorization from the owning *and* the consuming Tenant), and
`REL-012` (a Tenant set to `deny_all` participates in no cross-tenant relationship in either
direction). The cross-tenant authorization rules below are defined here.

| Policy | Rule |
|--------|------|
| `XTA-001` | Cross-tenant information sharing is closed by default — explicit authorization required for all cross-tenant relationships of any nature (see Policy Organization document Section 6) |
| `XTA-002` | Cross-tenant authorizations must specify who, what, when, and where |
| `XTA-003` | More specific authorizations take precedence: field_specific > resource_specific > tenant_global |
| `XTA-004` | All cross-tenant authorization decisions are policy-driven and control-plane-enforced |
| `XTA-005` | Sovereignty constraints declared by either Tenant must be honored by all cross-tenant relationships |
| `XTA-006` | An intent whose dependency targets an entity in another Tenant without an active `cross_tenant_authorization` is refused **whole** at request validation — never repaired by dropping the edge and realizing the remainder, and never partially accepted. The refusal is emitted as `authz.cross_tenant_unauthorized`, names the grant that would make the reference legal, and discloses nothing about the target beyond existence-as-forbidden: no attributes, no type, no state, and the same response whether or not the target exists (`docs/spec/contracts/error-model.md` §3.3) |
| `XTA-007` | The refusal record for a cross-tenant crossing names **both** Tenant identities and the attempted target identifier, alongside the refusing policy (`AUD-024` — a refusal record names every subject of the crossing it refused). A single-tenant denial record is insufficient: the owning Tenant is a party to the attempt and cannot audit what it cannot see |

---

## 7. Allocated Resources — Cross-Tenant Operational Model

### 7.1 Concept

An **Allocated Resource** is a pre-defined, discrete slice of a parent resource — provisioned by the owning Tenant and made available for consuming Tenants to claim. The allocated resource becomes a **first-class entity** in the consuming Tenant's scope with its own UUID, its own lifecycle, and its own governance — while maintaining a formal `depends_on` + `operational` relationship to the parent resource across the Tenant boundary.

This models real infrastructure practice: the network team pre-carves VLANs, the storage team pre-partitions pools, the platform team pre-defines availability zones. Consumers claim from what is available.

The relationship type is `depends_on` + `operational` — the allocated entity depends on the parent operationally but is not a constituent component of it. The allocation is the relationship; the entity itself is independently governed.

### 7.2 Parent Resource — Available Allocations

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

### 7.3 Allocated Entity — In the Consuming Tenant

When a consuming Tenant claims an available allocation, the control plane creates a first-class entity in the consuming Tenant's scope:

```yaml
allocated_entity:
  uuid: <uuid — consuming Tenant's own entity>
  family: Resource  # ownership_model: allocation (ADR-027); shape derived — Atomic (no constituents)
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

  lifecycle_state: Realized        # operational status is a status.condition (data-model-core §3)

  parent_lifecycle_policy:
    on_parent_destroy: notify_then_detach
    on_parent_suspend: suspend
    on_parent_maintenance: notify
    on_parent_degrade: notify
    on_parent_capacity_change: notify

  dependencies:
    - target_uuid: <parent resource uuid>
      related_entity_type: internal
      related_entity_tenant_uuid: <Infrastructure Tenant uuid>
      edge_type: depends_on
      strength: soft                    # operational allocation (nature derived)
      cross_tenant: true
      allocation_uuid: <uuid — links to parent's allocation record>
      authorized_by:
        owning_tenant_policy_uuid: <policy permitting this allocation>
        consuming_tenant_policy_uuid: <policy permitting this dependency>

  artifact_metadata:
    <standard — owned_by Tenant A>
```

### 7.4 Lifecycle Event Propagation

When the parent resource changes state, the control plane iterates all active allocations and propagates according to each allocation's `parent_lifecycle_policy`:

```
Parent resource enters MAINTENANCE
  │
  ▼
The control plane iterates active_allocations
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

### 7.5 Claiming Flow

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
The control plane creates:
  │  Allocated Entity (owned by Tenant A) with UUID
  │  depends_on edge on the allocated entity (the parent’s inbound reading is derived; cross_tenant: true)
  │  Updates parent's available_allocation status: available → claimed
  │  Adds record to parent's active_allocations
  │  Provenance recorded on both entities
  ▼
Infrastructure Tenant owner notified of new claim
  │  Via owned_by.notification_endpoint on the parent entity
```

---

## 8. Lifecycle Policies

Lifecycle policies declare what happens to an entity when its related entity changes state. They apply to `constituent` and `operational` relationships only — `informational` relationships have no lifecycle implications.

### 8.1 Policy Actions

| Action | Meaning |
|--------|---------|
| `destroy` | Destroy this entity when the related entity is destroyed |
| `retain` | Keep this entity when the related entity is destroyed — it becomes independent |
| `detach` | Detach this entity from the relationship — relationship terminated, entity retained |
| `notify` | Notify appropriate personas and trigger Policy Engine evaluation — no automatic action |
| `suspend` | Suspend this entity when the related entity is suspended |
| `cascade` | Cascade the change from the related entity to this entity |
| `ignore` | Take no action — the change to the related entity does not affect this entity |

### 8.2 Lifecycle Action Hierarchy — Save Overrides Destroy

When a shared resource has multiple active relationships and a lifecycle event triggers, each relationship may produce a different action recommendation. The control plane resolves conflicts using a deterministic hierarchy — **the most conservative action always wins**:

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

This rule applies automatically and silently when the hierarchy resolves cleanly (e.g., `retain` beats `destroy`). The resolution is recorded as an audit fact at severity `info`; no notification is required.

### 8.3 Lifecycle Conflict Detection

**Not all multi-recommendation scenarios are conflicts.** The hierarchy resolves most cases deterministically. A conflict worth surfacing occurs when:

1. **Adjacent hierarchy levels** — two relationships recommend actions that are one step apart (e.g., `notify` vs `suspend`) — the hierarchy resolves it but the ambiguity is worth surfacing
2. **An immutable lifecycle lock couldn't be honored** — a compliance-class Validation Policy set `on_related_destroy: destroy` with `immutable_ceiling: absolute` but `retain` from another relationship won per REL-018
3. **`notify` is the winning action** — inherently means human decision required; the notification should include the full conflict picture

**Conflict severity:**

| Scenario | Severity | Action |
|----------|---------|--------|
| `retain` beats `destroy` — non-adjacent levels | `info` | Logged only — working as designed |
| All relationships agree | None | No record needed |
| Adjacent levels (e.g., `notify` vs `suspend`) | `warning` | Notify entity owner and affected policy owners |
| `notify` is the winning action | `warning` | Notify owner — human decision required |
| Immutable lifecycle lock overridden by REL-018 | `critical` | Notify entity owner, policy owner, and platform admin |

**The record is an obligation, not a shape.** When a conflict is surfaced (REL-019), the control plane records
durably: the full recommendation set (per edge — the recommended action and the policy or
lifecycle declaration it came from), the resolved action and the rule that resolved it, the
severity, and the notifications dispatched — citable from the affected entity's audit trail.
The record's shape is the control plane's implementation; the content above is the contract.

### 8.4 Lifecycle Policy Authority Hierarchy

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
The control plane System Policy (non-overridable — sovereignty and compliance mandates)
```

**Example:** A control plane System Policy might declare that all storage entities in a PCI-DSS scope must `retain` when their parent VM is destroyed — regardless of what the provider default or consumer declared.

---

## 9. Shared Resource Model — Same-Tenant

### 9.1 Concept

A **Shared Resource** is an entity within a single Tenant that has active relationships from multiple parent entities. Rather than being exclusively owned by one parent, it is referenced by N parents — each with its own lifecycle relationship.

This is the same-tenant counterpart to the cross-tenant Allocated Resource model. Both use reference counting to defer destructive actions. The sharing model applies within a Tenant; the allocation model applies across Tenant boundaries.

**Examples:** Shared NFS volume mounted by multiple VMs. Shared database cluster used by multiple application services. Shared VLAN used by multiple VMs. Shared TLS certificate used by multiple services.

### 9.2 The `sharing_model` Declaration

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
    minimum_relationship_count: 0    # at or below this, on_last_relationship_released fires
    on_last_relationship_released: <destroy | retain | notify>
    # destroy: entity destroyed when last relationship is released
    # retain:  entity persists independently — becomes unowned
    # notify:  notify owner, entity enters PENDING_DECISION
```

**`shareability.allowed: false`** on a Resource Type (e.g., `Compute.BootDisk`) means the Policy Engine rejects any attempt to create a second active constituent or operational relationship to an instance. Boot disks, primary network interfaces, and similar exclusively-owned resources are non-shareable by type definition (REL-017).

### 9.3 Reference Count Lifecycle

The **active relationship count is derived, never stored**: it is the number of active
`constituent`/`operational` edges targeting the entity, computed from the graph at each
lifecycle event (informational edges never count — REL-016). A stored counter would duplicate
the graph and drift. The lifecycle over the derived count:

- **Edge created** → the derived count rises
- **Edge released** (parent decommissioned, relationship detached) → the derived count falls
- **Informational relationships** → never counted (REL-016)
- **Count reaches `minimum_relationship_count`** → `on_last_relationship_released` fires

When a parent entity is destroyed and has a relationship to a shared resource:

```
Parent entity destroyed
  │
  ▼
The control plane collects action recommendations from all active relationships on shared resource
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

### 9.4 Deferred Destruction — the Obligation

When a destruction is deferred because active edges remain (REL-015), the control plane records durably: the
triggering request, the entity whose edge was being released, the derived count before and
after, the remaining blocking edges (declaring entity + edge_type + strength), and the reason —
citable from the shared entity's audit trail. When the count later reaches the declared
`minimum_relationship_count` and destruction proceeds, the destruction audit record cites the
deferral, closing the loop. The record shapes are the control plane's implementation; this content is the
contract.

### 9.5 Unified with the Allocated Resource Model

The same-tenant sharing model and the cross-tenant allocated resource model are the same concept at different scopes:

| Dimension | Same-Tenant Sharing | Cross-Tenant Allocation |
|-----------|--------------------|-----------------------|
| Scope | Within one Tenant | Across Tenant boundaries |
| Pre-definition | Not required — relationships declared at request time | Parent pre-defines `available_allocations` |
| Reference tracking | derived active-edge count | `active_allocations` list on parent |
| Destruction deferral | Deferred until count reaches minimum | Deferred until last allocation released |
| Lifecycle events | `on_last_relationship_released` | `parent_lifecycle_policy` per allocation |
| Governed by | REL-015 through REL-019 | REL-011, REL-014 |

---

## 10. Relationship Declarations — Where They Live

Relationship declarations exist at multiple levels, each building on the previous:

### 10.1 Resource Type Specification (structural ceiling)

Declares what relationships are **possible** for a resource type. Sets the ceiling — lower levels can only declare relationships within these bounds.

```yaml
resource_type: Compute.VM
relationships:
  - name: disk
    edge_type: depends_on
    strength: hard
    permitted_related_types:
      - Storage.Block
      - Storage.File
    default_lifecycle_policy:
      on_related_destroy: destroy
      on_related_suspend: suspend
    binding_types_permitted: [owned, referenced]
    consumer_declarable: true
    # Consumer can declare binding_type and lifecycle_policy override

  - name: network_attachment
    edge_type: depends_on
    strength: hard
    permitted_related_types:
      - Network.IPAddress
    default_lifecycle_policy:
      on_related_destroy: destroy
    consumer_declarable: false
    # the control plane manages this automatically — consumer cannot override
```

### 10.2 Catalog Item (offering-specific)

Declares the **actual relationships** for a specific curated offering. Can only be more restrictive than the Resource Type Specification.

```yaml
catalog_item: Production VM
relationships:
  - name: disk
    edge_type: depends_on
    strength: hard
    related_catalog_item_uuid: <uuid of Standard Block Storage catalog item>
    lifecycle_policy:
      on_related_destroy: retain
      # Overrides Resource Type default of destroy
      # Storage persists even if VM is destroyed — production data protection
    binding_type: owned
```

### 10.3 Request Time (consumer-declared)

The consumer declares relationships in their request. Bundled declarations (storage fields within a VM request) are automatically expanded into relationship records by the Request Payload Processor.

```yaml
# Explicit relationship declaration in a request
request:
  resource_type: Compute.VM
  # ... other fields ...
  relationships:
    - relation: disk
      edge_type: depends_on
      strength: hard
      binding_type: referenced
      related_entity_uuid: <uuid of existing Storage Entity>
      # Consumer referencing existing storage — not creating new

# Bundled declaration — expanded automatically
request:
  resource_type: Compute.VM
  storage:
    disks:
      - name: boot
        capacity: 100GB
        # Processor expands this into a Storage Entity stub
        # and a relationship record with binding_type: owned
```

### 10.4 External Data Relationships

Relationships to external data entities follow the same structure with `related_entity_type: external`:

```yaml
# On a VM Entity — relationship to external Business Unit
dependencies:
  - target_uuid: <uuid of external_entity_reference>
    related_entity_type: external
    information_provider_uuid: <uuid of HR Information Provider>
    information_type: Business.BusinessUnit
    edge_type: references
    relation: business_unit
    lookup_method: primary_key
```

---

## 11. Bundled Declaration Expansion

When a consumer includes resource configuration as bundled fields (e.g., storage within a VM request), the Request Payload Processor expands these into first-class entities and relationship records.

### 11.1 Expansion Process

```
Consumer submits bundled VM request with storage fields
  │
  ▼
Request Payload Processor
  │  Reads expansion rules from Resource Type Specification
  │  For each expandable field:
  │    1. Creates a Resource/Service Entity stub (PENDING state)
  │       with its own UUID, Tenant membership, Resource Type
  │    2. Declares the dependency edge on the parent stub
  │       and the child stub
  │    3. Applies lifecycle policy from:
  │       consumer declaration → provider default → Resource Type default
  │       → the control plane System Policy override
  │    4. Adds the child entity stub to the relationship graph
  ▼
Policy Engine validates:
  │  Binding type is permitted by Resource Type Specification
  │  Consumer has override_matrix permission to declare binding type
  │  Lifecycle policy is not overridden by a control plane System Policy
  ▼
Service Provider receives:
  │  Parent entity request payload
  │  Child entity stub UUIDs embedded in parent payload
  │  Provisions resources natively
  │  Returns realized payloads for all entities in the control plane unified format
  ▼
The control plane updates:
  │  Parent entity: PENDING → REALIZED
  │  Child entities: PENDING → REALIZED
  │  All relationship records: status → active
  │  Full provenance recorded on all entities and relationships
```

### 11.2 Expansion Rules in Resource Type Specification

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

## 12. The Entity Relationship Graph

All relationships across all entities form a traversable **Entity Relationship Graph** — the complete map of how all entities in the control plane relate to each other.

### 12.1 Graph Properties

- Every node is a Resource/Service Entity (internal or external reference)
- Every edge is a typed dependency declared on exactly one entity
- The graph is traversable in both directions — the inverse reading of every edge is derived (GRAPH-003), never stored
- Every node exists exactly once — shared entities appear once with multiple relationship edges
- Cycles over the **ordering** edge_types (`depends_on`, `contained_by`) are invalid and must be rejected (the CYCLE gate); non-ordering `references` cycles — including reflexive self-reference (the multi-cluster self-managed hub, `docs/examples/multi-cluster-hub-example.md`) — are legal and outside the ordering sort

### 12.2 Graph and the Four States

The relationship graph exists across all four states:

| State | Graph Role |
|-------|-----------|
| Intent State | Graph declared at request time — nodes are intent stubs |
| Requested State | Graph fully assembled — nodes are PENDING entity stubs with UUIDs |
| Realized State | Graph populated — nodes are REALIZED entities with full provenance |
| Discovered State | Graph used for comparison — discovered entities matched against realized graph |

### 12.3 Graph Applications

| Application | How the Graph is Used |
|-------------|----------------------|
| **Rehydration** | Full graph traversal from a root entity — all related entities identified and realized in dependency order |
| **Cost Rollup** | Graph traversal accumulates costs across all related constituent entities |
| **Drift Detection** | Discovered State graph compared against Realized State graph — structural and data differences identified |
| **Decommission** | Graph traversal determines decommission order — lifecycle policies applied at each edge |
| **Placement** | Pre-realization graph used to understand full resource footprint for placement decisions |
| **Impact Analysis** | Graph traversal from any node identifies all entities affected by a change |

---

## 13. Relationship Integrity

### 13.1 the control plane System Policies for Relationships

| Policy | Rule |
|--------|------|
| `ERL-001` | Every edge at rest identifies its target by uuid (`target_uuid`, resolved from `target_handle` at reserve — AEP-124) |
| `ERL-002` | An edge is declared on exactly one entity; its inverse reading is derived, never stored (GRAPH-003) |
| `ERL-003` | Cycles over the ordering edge_types (`depends_on`, `contained_by`) are invalid and must be rejected; non-ordering `references` cycles (including reflexive self-reference, e.g. the multi-cluster self-managed hub) are legal and outside the ordering sort |
| `ERL-004` | A constituent or operational relationship must have a lifecycle policy declared somewhere in the authority chain before provider dispatch |
| `REL-005` | External relationships must reference a registered Information Provider |
| `REL-006` | `edge_type` must be from the closed set (`depends_on`, `contained_by`, `binds_to`, `references`); a named `relation` must be declared by the pinned type (REL-001/003) |
| `REL-007` | Consumer-declared binding types must be permitted by the Resource Type Specification |
| `REL-008` | A constituent relationship lifecycle policy may not be set to `ignore` for `on_related_destroy` |
| `REL-009` | Lifecycle policy conflicts between policies are resolved by the standard Policy Engine authority hierarchy — no special case |
| `REL-011` | Cross-tenant operational relationships require explicit authorization from both the owning Tenant and the consuming Tenant |
| `REL-012` | A Tenant with `hard_tenancy.cross_tenant_relationships: deny_all` may not participate in any cross-tenant relationship in any direction |
| `REL-014` | An allocated resource claim requires a matching `available` allocation record on the parent entity |
| `REL-015` | A destructive lifecycle action on a shared resource entity (`ownership_model: shareable` — [Ownership, Sharing, and Allocation](ownership-sharing-allocation.md)) is deferred until the derived active-edge count reaches the declared `minimum_relationship_count` |
| `REL-016` | Informational edges never contribute to the derived active-edge count on shared resource entities |
| `REL-017` | A Resource Type Specification with `shareability.allowed: false` must reject any attempt to create more than one active constituent or operational relationship to an instance of that type |
| `REL-018` | When a lifecycle event produces multiple action recommendations on a shared resource, the most conservative action wins per the hierarchy: `retain > notify > suspend > detach > cascade > destroy` (save_overrides_destroy) |
| `REL-019` | When lifecycle action recommendations conflict, a `lifecycle_conflict_record` is created. Conflicts at `warning` or `critical` severity trigger notifications to the entity owner and affected policy owners |

### 13.2 Lifecycle Policy Conflict Resolution

Lifecycle policy fields on relationships are fields. They carry the same `override` metadata, the same provenance obligations, and resolve under the same Policy Engine authority hierarchy as any other field in the control plane. There is no special case — minimum variance applies.

**Authority chain for a relationship lifecycle policy field (lowest to highest):**

```
Resource Type Specification default
  → Provider Catalog Item default
    → Consumer declaration at request time
      → Transformation Policy (may set override: constrained)
        → Validation Policy (checks — no modification; compliance-class may set override: immutable)
            → the control plane System Policies REL-008, REL-009 (non-overridable)
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
      locked_by_policy_uuid: <uuid of Global Validation Policy>
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

### 13.2a Cross-Tenant Dependency System Policies

| Policy | Rule |
|--------|------|
| `ERL-D01` | Cross-tenant constituent dependencies are prohibited — a dependency that would produce a constituent cross-tenant relationship is rejected at dependency graph construction time |
| `ERL-D02` | Cross-tenant operational dependencies require a valid available allocation record on the target resource — failure returns `CROSS_TENANT_DEPENDENCY_UNAVAILABLE` |
| `ERL-D03` | A Resource Type Specification may only declare cross-tenant dependencies if explicitly marked `cross_tenant: permitted` — default is `cross_tenant: not_permitted` |

### 13.3 Relationship Versioning and Deprecation

Relationships follow the universal versioning and deprecation model. A relationship version changes when its lifecycle policy or edge declaration changes. Terminated relationships are retained in provenance permanently.

---

## 14. Notification Traversal Rules

The entity relationship graph is the source of truth for notification audiences. This section defines how relationships govern notification traversal for the notification model ([subscription-lifecycle.md](../lifecycle/subscription-lifecycle.md)).

### 14.1 Stake Strength — Derived from the Edge

Notification audience resolution consumes a **stake strength** per edge, and it is derived from
the declaration — never a stored field:

| Edge declaration | Derived stake strength |
|---|---|
| `depends_on`, `strength: hard` (or `contained_by`/`binds_to`) | `required` |
| `depends_on`, `strength: soft` | `preferred` |
| `references` | `optional` |

Which events notify at which minimum stake, and how far traversal walks, are **platform-domain
policy configuration** (defaults below) — not type-spec fields and not per-edge data.

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

The minimum stake-strength threshold per event type is platform-domain policy configuration; the table above is the substrate default.

### 14.3 Notification Traversal and Graph Depth

**UDLM declares no traversal depth and no audience.** How far a notification travels, and who is
told about a security event, are governance choices — an estate may legitimately want the affected
tenant informed of a sovereignty violation immediately, or may want it contained to a security
function, and both are conformant. Depth per event type is declared by platform-domain policy
(`REL-022`); UDLM ships no default for it, because a default here has no provenance — it would apply
in every estate that ever used the model, with no record of who chose it (NDF-001).

**What UDLM does fix is the CONTENT, not the reach** (`REL-023`): a cross-tenant notification carries
only what the receiving tenant is authorized to see. That is an invariant rather than a threshold —
it does not vary with posture, and no estate may relax it. The line is the same one that governs
depth: the model bounds what may be *disclosed*; policy decides *how far* and *to whom*.

Walking the graph from a changed entity and dispatching the notifications — the traversal itself —
is implementation concern (foundations §5 lists notification routing as implementation machinery);
it consumes these declarations.

### 14.4 Notification Traversal Policies

| Policy | Rule |
|--------|------|
| `REL-022` | Notification traversal follows relationship edges from the changed entity. Traversal depth per event type is declared by platform-domain policy — **UDLM declares no default and fixes no depth for any event type**, including security events; how far a notice travels is a posture choice, and a shipped default would apply in every estate with no record of who chose it (NDF-001). Stake strength is derived from the edge declaration (§14.1), never stored. |
| `REL-023` | Notification traversal respects sovereignty boundaries. Cross-tenant notifications carry only content authorized for the receiving Tenant. |
| `REL-024` | The same actor reached via multiple relationship paths receives a single notification with all applicable audience_roles listed. |

---

## 15. Relationship Graph Depth

**There is no maximum relationship-graph depth in UDLM.** A traversal ceiling is a governance
choice, and the data model does not make governance choices (rule 42; ADR-060). An implementation
declares one as policy if it wants one. Cycle detection stays: a cycle makes traversal
non-terminating, which is a structural fact rather than a threshold.

**Note:** Relationship depth differs from dependency depth (service-dependencies §11c). Dependency depth counts the provisioning chain. Relationship depth counts the graph traversal distance between any two entities. A VM with 50 IP address relationships has depth 1, not 50. Neither is capped by the model; the distinction matters because a policy declaring a ceiling must say which one it means.

---

*Part of the UDLM specification. For contributions see [CONTRIBUTING.md](../../../CONTRIBUTING.md).*