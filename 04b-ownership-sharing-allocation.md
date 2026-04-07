# DCM Data Model — Ownership, Sharing, and Allocation


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
> The Data abstraction — ownership models for entity data


**Related Documents:** [Entity Types](01-entity-types.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Entity Relationships](09-entity-relationships.md) | [Resource Grouping](08-resource-grouping.md)

---

## 1. Purpose

This document defines the complete ownership model for DCM entities — specifically the three ownership patterns that govern how resources are owned, shared, and allocated across Tenants. It establishes precise vocabulary and clear boundaries between concepts that are frequently conflated:

- **Ownership** — who is accountable for a resource's lifecycle and costs
- **Shareable** — multiple entities have a stake in a single resource that they do not own
- **Allocatable** — a pool resource yields independently owned sub-resources to consumers

Getting this model right is foundational. It governs decommission safety (can this resource be removed?), cost attribution (who pays for this?), cross-tenant visibility (who can see this?), drift accountability (whose responsibility is remediation?), and placement decisions (which providers serve allocation requests?).

---

## 2. The Three Ownership Patterns

### 2.1 Whole Allocation (Consumer Owns the Entity)

**What it means:** The consumer receives the entire resource entity. It belongs exclusively to them. They own it outright — it is in their Tenant, they control its lifecycle, they bear its costs.

**Structural model:**
```
Platform Tenant owns: the infrastructure, compute capacity, network fabric
Consumer Tenant owns: VirtualMachine-A (a distinct entity)
Consumer Tenant owns: VirtualMachine-B (another distinct entity)
```
There is no relationship between VirtualMachine-A and the infrastructure Tenant — the consumer simply used DCM's Service Provider to provision a resource. Once provisioned, the entity belongs to the consumer's Tenant entirely. The platform Tenant has no visibility into the consumer's entity unless an explicit Information Provider or cross-tenant relationship is established.

**Examples:** VirtualMachine, Container, StorageVolume, NetworkInterface, DNSRecord.

**Resource Type Spec declaration:**
```yaml
resource_type_spec:
  fqn: Compute.VirtualMachine
  ownership_model: whole_allocation
  # Each consumer request produces an entity owned entirely by the requesting Tenant
```

**Decommission behavior:** Straightforward. The owning Tenant decommissions the entity. The provider releases the underlying physical resources. No other Tenant is affected.

---

### 2.2 Allocation (Consumer Owns a Carved Portion)

**What it means:** A *pool* resource is owned by a platform or provider Tenant (the pool owner). When a consumer requests a resource of this type, they receive an *allocation* — a new, distinct entity carved from the pool. The consumer **owns** their allocation. The pool owner retains ownership of the pool.

**The key distinction from Shareable:** The consumer's allocation is an independent entity with its own UUID, its own Tenant membership, its own lifecycle. It is not a reference to the pool — it is a new thing that came from the pool.

**Structural model:**
```
NetworkOps Tenant owns: IPAddressPool 10.0.0.0/16 (pool entity)
  │
  ├── AppTeam Tenant owns: IPAddress 10.0.1.45/32  ← allocation entity (new UUID, AppTeam's Tenant)
  ├── DevTeam Tenant owns: IPAddress 10.0.1.46/32  ← allocation entity (new UUID, DevTeam's Tenant)
  └── OpsTeam Tenant owns: IPAddress 10.0.1.47/32  ← allocation entity (new UUID, OpsTeam's Tenant)
```

The IPAddress entities are not pointers to the pool — they are real entities owned by their Tenants. If AppTeam decommissions 10.0.1.45/32, it is released back to the pool. The pool capacity increases. No other Tenant's allocation is affected.

**Examples:** IPAddress (from IPAddressPool), Subnet (from SubnetPool), VLAN ID (from VLANIDPool), StorageVolume (from StoragePool), PublicCertificate (from CertificateAuthorityPool).

**Resource Type Spec declarations (both pool and allocation):**
```yaml
# The pool resource type
resource_type_spec:
  fqn: Network.IPAddressPool
  ownership_model: whole_allocation    # the pool entity is owned outright by the platform Tenant
  is_pool: true
  allocation_produces_type: Network.IPAddress
  capacity_tracking: true              # DCM tracks used/available capacity

# The allocation resource type
resource_type_spec:
  fqn: Network.IPAddress
  ownership_model: allocation          # each instance is an allocation from a pool
  allocated_from_pool_type: Network.IPAddressPool
  # When a consumer requests Network.IPAddress, DCM:
  # 1. Runs placement to find an eligible IPAddressPool
  # 2. The pool provider carves out a specific IP
  # 3. DCM creates a new IPAddress entity owned by the requesting Tenant
  # 4. Records an AllocationRecord relationship between the entity and the pool
```

**AllocationRecord relationship:**
Every allocation entity carries an `allocated_from` relationship to its source pool:

```yaml
relationship:
  relationship_uuid: <uuid>
  type: allocated_from
  source_entity_uuid: <uuid>       # the allocation (e.g., IPAddress 10.0.1.45/32)
  target_entity_uuid: <uuid>       # the pool (e.g., IPAddressPool 10.0.0.0/16)
  source_tenant_uuid: <uuid>       # AppTeam Tenant
  target_tenant_uuid: <uuid>       # NetworkOps Tenant — cross-tenant relationship
  allocation_ref:
    allocation_size: "1/32"        # what was carved from the pool
    allocated_at: <ISO 8601>
    allocated_by_actor_uuid: <uuid>
    allocation_metadata:
      pool_capacity_before: 65534
      pool_capacity_after: 65533
```

**Decommission behavior:** When the consumer decommissions their allocation entity, DCM dispatches a decommission payload to the provider. The provider releases the specific allocated resource back to the pool. The pool's available capacity increases. The AllocationRecord relationship is terminated. The allocation entity enters DECOMMISSIONED state. The pool entity is unaffected.

**Cross-tenant visibility:** The allocation entity is in the consumer's Tenant. The consumer cannot see the pool entity unless an explicit cross-tenant relationship or Information Provider is configured. The pool owner can see allocation counts and capacity via the Cost Analysis component and the provider's capacity reporting API — they cannot see the consumer's entity data.

---

### 2.3 Shareable (Consumer Has a Stake, Not Ownership)

**What it means:** A single resource entity is owned by one Tenant (the resource owner) and multiple consumers attach to, depend on, or reference it. Consumers have a *stake* — a relationship that affects the resource's lifecycle — but they do not own any portion of it. The resource's lifecycle is governed entirely by its owner.

**The key distinction from Allocation:** No new entity is created for the consumer. The consumer receives a relationship to the existing resource, not a new sub-entity. The consumer does not own anything — they hold a stake.

**Structural model:**
```
NetworkOps Tenant owns: VLAN-100 (single entity — there is only one VLAN-100)
  │
  ├── AppTeam has stake: VM-A attached to VLAN-100   (relationship, not ownership)
  ├── DevTeam has stake: VM-B attached to VLAN-100   (relationship, not ownership)
  └── OpsTeam has stake: VM-C attached to VLAN-100   (relationship, not ownership)
```

VLAN-100 belongs to NetworkOps. AppTeam, DevTeam, and OpsTeam each have a VM attached to it. If DevTeam decommissions VM-B, VLAN-100 is unaffected — it still exists and serves VM-A and VM-C. If NetworkOps wants to decommission VLAN-100, they cannot do so while VMs are attached. Decommission is deferred until all stakes are released.

**Examples:** VLAN (network fabric shared by many VMs), NetworkSegment, SharedFileSystem, DNS Zone, NTP Server, Certificate Authority (as a service), Transit Gateway.

**Resource Type Spec declaration:**
```yaml
resource_type_spec:
  fqn: Network.VLAN
  ownership_model: shareable
  # A single VLAN entity exists; consumers attach to it via relationships
  # Consumers do not receive their own VLAN entity
  decommission_policy:
    defer_while_active_stakes: true
    minimum_stake_count: 0       # can decommission when all stakes released
    # Some resources may require minimum_stake_count: 1
    # e.g., a DNS Zone that should never be empty
```

**Stake relationship:**
```yaml
relationship:
  relationship_uuid: <uuid>
  type: attached_to          # or: depends_on, references, uses
  source_entity_uuid: <uuid>   # VM-A (consumer's entity)
  target_entity_uuid: <uuid>   # VLAN-100 (shared resource)
  source_tenant_uuid: <uuid>   # AppTeam Tenant
  target_tenant_uuid: <uuid>   # NetworkOps Tenant
  stake:
    is_active: true
    staked_at: <ISO 8601>
    staked_by_actor_uuid: <uuid>
    stake_strength: <required|preferred|optional>
    # required: VM cannot function without VLAN attachment (blocks VLAN decommission)
    # preferred: VM prefers attachment but can function without it
    # optional: informational stake only
```

**Decommission behavior:** VLAN-100 cannot be decommissioned while any `stake_strength: required` stakes exist. The decommission attempt is deferred — not rejected — and a `DECOMMISSION_DEFERRED` event is generated. DCM notifies the resource owner of all active required stakes. The owner can request that stakeholders release their stakes (by decommissioning their VMs or migrating to a different VLAN) before decommission proceeds.

**Cross-tenant visibility:** The consumer's VM can reference VLAN-100 (read access for attachment purposes). The consumer cannot modify VLAN-100 or see its owner's configuration details unless an explicit cross-tenant authorization grants that. The resource owner (NetworkOps) can see all active stakes on their resource — this is how they know which consumers are affected by a planned decommission.

---

## 3. Hybrid Case — Allocation from a Shareable Pool

Some resources combine both patterns. A Subnet Pool is an allocatable pool. Each allocation (a specific /28) is owned by the consumer. But the /28 has a stake relationship to the parent /16 (which is shareable — owned by the network team, referenced by all subnets).

```
NetworkOps Tenant owns: SupernetPool 10.0.0.0/8 (allocatable pool)
  │
  ├── NetworkOps Tenant owns: 10.0.0.0/16 (allocation from /8 — NetworkOps-owned)
  │     NetworkOps Tenant owns: 10.0.0.0/24 (allocation from /16 — NetworkOps-owned)
  │
  └── NetworkOps Tenant owns: 10.1.0.0/16 (allocation from /8 — NetworkOps-owned, shared)
        ├── AppTeam Tenant owns: 10.1.0.0/24  ← consumer allocation (owned by AppTeam)
        │     └── stake: attached to 10.1.0.0/16 (shareable — NetworkOps)
        └── DevTeam Tenant owns: 10.1.1.0/24  ← consumer allocation (owned by DevTeam)
              └── stake: attached to 10.1.0.0/16 (shareable — NetworkOps)
```

The consumer-facing 10.1.0.0/24 is an allocation — AppTeam owns it. The parent 10.1.0.0/16 is shareable — NetworkOps owns it, AppTeam and DevTeam both have stakes. The 10.1.0.0/24 has both an `allocated_from` relationship (to the /24 pool that produced it) and an `attached_to` relationship (stake in the parent /16).

---

## 4. Ownership Model Summary

| Pattern | Consumer Gets | Consumer Owns | New Entity Created | Lifecycle Governed By | Cost Attribution |
|---------|--------------|--------------|-------------------|----------------------|-----------------|
| **Whole Allocation** | The entire resource | Yes, outright | Yes (same type) | Consumer Tenant | Consumer Tenant |
| **Allocation** | A carved sub-resource | Yes, the allocation | Yes (sub-type) | Consumer Tenant | Consumer Tenant |
| **Shareable** | A stake/relationship | No — stake only | No new entity | Resource Owner Tenant | Resource Owner Tenant (shared cost attribution possible via policy) |

---

## 5. Placement Engine Interaction

The placement engine handles all three ownership models, but the selection criteria differ:

**Whole Allocation:** Standard placement. The placement engine selects a provider with available capacity. The provider provisions the resource and returns it owned by the requesting Tenant.

**Allocation:** The placement engine selects an eligible pool resource owned by a platform Tenant with sufficient available capacity. The pool provider carves an allocation and returns it. DCM creates the new allocation entity in the requesting Tenant.

```yaml
# Placement engine for allocation requests:
# Step 1: Find providers that offer Network.IPAddressPool
# Step 2: Filter by sovereignty constraints
# Step 3: Filter by available capacity (pool.available_count > 0)
# Step 4: Apply tie-breaking hierarchy
# Step 5: Dispatch allocation request to selected pool provider
# Step 6: Provider returns the specific carved allocation
# Step 7: DCM creates IPAddress entity in requesting Tenant
# Step 8: AllocationRecord relationship created
```

**Shareable:** The placement engine finds the shareable resource instance that satisfies the consumer's attachment constraints. No new entity is provisioned — the provider registers the stake relationship. If no eligible shareable instance exists, the request fails with a clear error (unlike Allocation where failure means insufficient pool capacity).

---

## 6. Decommission Safety Model

The three patterns have different decommission safety behaviors:

**Whole Allocation decommission:**
- Owner Tenant initiates decommission
- Policy checks for required relationships (do other entities depend on this?)
- If required dependencies exist → `DECOMMISSION_DEFERRED` until dependencies release
- If no required dependencies → dispatch decommission to provider → DECOMMISSIONED

**Allocation decommission:**
- Consumer Tenant initiates decommission of their allocation entity
- DCM dispatches decommission to pool provider
- Pool provider releases the resource back to pool
- AllocationRecord relationship terminated
- Pool `available_count` increases
- Allocation entity → DECOMMISSIONED
- Pool entity is unaffected

**Shareable decommission:**
- Resource owner Tenant initiates decommission of the shared resource
- DCM checks `active_stake_count` for `stake_strength: required` stakes
- If required stakes > 0 → `DECOMMISSION_DEFERRED`
  - Notifications to all required stakeholders
  - Owner retries decommission after stakeholders release
- If required stakes == 0 → dispatch decommission to provider → DECOMMISSIONED
  - Any remaining `optional` stakes are automatically terminated

---

## 7. Cost Attribution Model

**Whole Allocation and Allocation:** Cost is attributed entirely to the owning Tenant. Standard Cost Analysis billing. The entity's `billing_state` governs the rate (billable/non_billable/reduced_rate).

**Shareable:** The shared resource's cost is attributed to its owner Tenant by default. Organizations that want to distribute shared resource costs to stakeholders configure a cost attribution policy:

```yaml
cost_attribution_policy:
  resource_type: Network.VLAN
  model: <owner_bears_all|equal_split|proportional_by_usage|chargeback>
  # owner_bears_all: NetworkOps Tenant pays for VLAN regardless of how many VMs attach
  # equal_split:     cost divided equally among active stakeholders
  # proportional_by_usage: cost allocated by traffic volume or similar metric
  # chargeback:      each stakeholder is invoiced for their declared portion
```

---

## 8. System Policies

| Policy | Rule |
|--------|------|
| `OWN-001` | `whole_allocation` resources are owned entirely by the requesting Tenant from the moment of realization. The providing platform Tenant has no ownership claim. |
| `OWN-002` | `allocation` resources are owned entirely by the requesting Tenant. The pool owner retains ownership of the pool entity only. AllocationRecord relationships are the only cross-Tenant link. |
| `OWN-003` | `shareable` resources are owned by a single Tenant. Consumers hold stakes (relationships) only. No consumer owns any portion of a shareable resource. |
| `OWN-004` | Decommission of a shareable resource is deferred while any `required` strength stakes are active. Optional stakes are terminated automatically on shareable resource decommission. |
| `OWN-005` | Allocation entity decommission releases the allocation back to the source pool. The pool entity is never decommissioned by an allocation decommission. |
| `OWN-006` | Cost attribution for shareable resources defaults to the resource owner Tenant. A cost attribution policy may redistribute costs to stakeholders. |
| `OWN-007` | The ownership model for a resource type is declared in the Resource Type Specification and cannot be changed at the entity level. Ownership model is a type-level invariant. |
| `OWN-008` | Cross-tenant AllocationRecord and stake relationships require that the requesting Tenant has either an active cross-tenant authorization or the resource type is declared as publicly allocatable/stakeable in its Resource Type Spec. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
