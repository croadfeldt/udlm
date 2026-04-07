# DCM Data Model — Service Dependencies



**Document Status:** ✅ Complete  
**Related Documents:** [Entity Relationships](09-entity-relationships.md) | [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Resource/Service Entities](06-resource-service-entities.md)

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
> The Data abstraction — dependency graph as embedded data structure



> **Scope:** This document covers dependency declaration, rehydration ordering, and failure handling. The underlying data structure is the Entity Relationship Graph defined in [Entity Relationships](09-entity-relationships.md).

---

## 1. Purpose

This document defines how service dependencies are declared, resolved, and managed within DCM. Dependencies are a core data model concern — not an orchestration concern. The data structures defined here enable DCM to know the complete resource footprint of any request before execution begins, which is essential for cost analysis, placement decisions, rehydration, and audit.

---

## 2. Why Dependencies Must Be Declared in Advance

Dependencies must be declared in the data model — not discovered at runtime by providers. This is a hard requirement driven by four core DCM goals:

**Auditability** — the complete dependency graph must be known before execution. Every resource that will be created as part of fulfilling a request must be visible in the request's provenance chain from the start.

**Cost Analysis** — accurate cost estimation and cost-based placement require knowing the full resource footprint before provisioning. Hidden dependencies produce hidden costs that only become visible after the fact.

**Placement** — the Policy Engine cannot make optimal placement decisions without knowing all resources that will be created. A Web Server request that implicitly spawns a VM, IP address, and firewall rule has placement requirements that span multiple resource types.

**Idempotency and Consistency** — if dependencies are declared in the service definition, the same request always produces the same dependency graph. Provider-driven dependency discovery at runtime breaks idempotency — different provider implementations could produce different dependency graphs for the same logical request.

---

## 3. Hybrid Dependency Declaration Model

DCM uses a hybrid model for dependency declaration that operates at two levels:

### 3.1 Type-Level Dependencies (Resource Type Specification)

Dependencies declared at the Resource Type Specification level are **portable and provider-agnostic**. They define what kinds of resources are needed — not which specific provider supplies them.

- Declared in the Resource Type Specification
- Apply to all Provider Catalog Items implementing that Resource Type
- Use Resource Type UUIDs — not provider-specific references
- Required for all implementations of the Resource Type
- Portable — the dependency can be fulfilled by any provider implementing the required Resource Type

**Example:**
```yaml
resource_type: Compute.VirtualMachine
type_level_dependencies:
  - dependency_uuid: <uuid>
    required_resource_type_uuid: <uuid of Network.IPAddress>
    required_resource_type_name: Network.IPAddress
    dependency_type: hard
    cardinality: one_to_one
    description: Every VM requires exactly one IP address
  - dependency_uuid: <uuid>
    required_resource_type_uuid: <uuid of Network.FirewallRule>
    required_resource_type_name: Network.FirewallRule
    dependency_type: hard
    cardinality: one_to_many
    description: Every VM requires at least one firewall rule
```

### 3.2 Provider-Specific Dependencies (Provider Catalog Item)

Dependencies declared at the Provider Catalog Item level are **provider-specific additions** beyond the type-level dependencies. They must be marked as portability-breaking.

- Declared in the Provider Catalog Item registration
- Apply only to requests fulfilled by that specific provider
- Must be marked `portability_breaking: true`
- Visible to the Policy Engine for governance decisions
- Surfaced to consumers as portability warnings

**Example:**
```yaml
catalog_item: Nutanix.VM.Small
provider_specific_dependencies:
  - dependency_uuid: <uuid>
    required_resource_type_uuid: <uuid of Nutanix.StorageContainer>
    required_resource_type_name: Nutanix.StorageContainer
    dependency_type: hard
    portability_breaking: true
    description: Nutanix VMs require a Nutanix Storage Container
    portability_warning: This dependency locks this request to Nutanix providers
```

---

## 4. Dependency Types

Every declared dependency must specify its type:

| Type | Description | Behavior |
|------|-------------|----------|
| `hard` | Must be realized before or alongside the dependent resource | Failure of dependency fails the dependent resource |
| `soft` | Preferred but not blocking | Failure of dependency is recorded but does not block the dependent resource |
| `conditional` | Required only if specific conditions in the request payload are met | Evaluated by Policy Engine against request data |

---

## 5. Dependency Cardinality

Every declared dependency must specify its cardinality:

| Cardinality | Description | Example |
|-------------|-------------|---------|
| `one_to_one` | Exactly one dependency resource required | One VM needs exactly one primary IP |
| `one_to_many` | One or more dependency resources required | One VM needs one or more firewall rules |
| `one_to_optional` | Zero or one dependency resource | One VM may optionally have a secondary IP |
| `one_to_range` | A specific numeric range required | One load balancer needs 2-6 backend VMs |

---

## 6. Dependency Graph

When a request is processed, the Request Payload Processor constructs a **Dependency Graph** — a complete map of all resources that must be created to fulfill the request, including all transitive dependencies.

### 6.1 Dependency Graph Structure

```yaml
dependency_graph:
  graph_uuid: <uuid>
  root_request_uuid: <uuid of the originating request>
  tenant_uuid: <uuid of owning tenant>
  created_timestamp: <ISO 8601>
  nodes:
    - node_uuid: <uuid>
      resource_type_uuid: <uuid>
      resource_type_name: <Category.ResourceType>
      request_uuid: <uuid of the request for this node>
      entity_uuid: <uuid of realized entity — null until realized>
      lifecycle_state: <PENDING|REALIZED|FAILED>
      dependencies:
        - dependency_uuid: <uuid of dependency declaration>
          dependent_node_uuid: <uuid of node this depends on>
          dependency_type: <hard|soft|conditional>
          status: <PENDING|SATISFIED|FAILED>
  edges:
    - from_node_uuid: <uuid>
      to_node_uuid: <uuid>
      dependency_uuid: <uuid>
      dependency_type: <hard|soft|conditional>
```

### 6.2 Transitive Dependencies

DCM resolves transitive dependencies — the full chain of dependencies, not just direct ones.

**Example — Web Server request:**
```
Web Server (requested)
  ├── VM (hard dependency of Web Server)
  │     ├── IP Address (hard dependency of VM)
  │     │     └── Network (hard dependency of IP Address)
  │     └── Firewall Rule (hard dependency of VM)
  │           └── IP Address (reference — already in graph)
  └── DNS Record (soft dependency of Web Server)
        └── IP Address (reference — already in graph)
```

The dependency graph contains each resource exactly once — circular references and duplicate nodes are detected and resolved. A resource that appears as a dependency of multiple nodes is represented as a single node with multiple incoming edges.

### 6.3 Dependency Graph and the Four States

The dependency graph is part of the request's data from the moment it is constructed:

- **Intent State** — consumer's request, no dependency graph yet
- **Requested State** — dependency graph constructed and attached, all nodes in PENDING state
- **Realized State** — nodes updated to REALIZED as providers fulfill each dependency
- **Discovered State** — dependency graph used to scope discovery — discover all nodes in the graph

---

## 7. Dependency Payload Passing

When a dependency resource is realized, its realized payload must be passed to the dependent resource's provider. This is how a provider knows the details of the resources it depends on — IP addresses, network configurations, security group IDs, etc.

### 7.1 The Payload Passing Mechanism

```
Dependency Resource realized
  │
  ▼
Realized State payload captured in Realized Store
  │
  ▼
Dependency node in graph updated: entity_uuid recorded, status → SATISFIED
  │
  ▼
Dependent resource's Requested State payload enriched with dependency data
  │  Recorded in field-level provenance — source_type: dependency_payload
  │  source_uuid: <uuid of realized dependency entity>
  ▼
Enriched payload dispatched to dependent resource's provider
```

### 7.2 Dependency Data in Request Payloads

When a dependency is satisfied, the dependent resource's Requested State payload is enriched with the dependency entity's UUID and relevant realized data:

```yaml
# Original request payload for VM
vm_request:
  cpu_count: 8
  ram_gb: 32
  os: RHEL9

# After IP Address dependency is realized
vm_request:
  cpu_count: 8
  ram_gb: 32
  os: RHEL9
  dependencies:
    ip_address:
      entity_uuid: <uuid of realized IP Address entity>
      ip_address: 192.168.1.45
      network_uuid: <uuid of network entity>
      subnet: 192.168.1.0/24
      provenance:
        source_type: dependency_payload
        source_uuid: <uuid of IP Address realized entity>
        timestamp: <ISO 8601>
```

---

## 8. Dependency Resolution Order

The dependency graph determines resolution order. Resources with no unsatisfied hard dependencies can be dispatched immediately. Resources with unsatisfied hard dependencies wait until their dependencies are satisfied.

### 8.1 Resolution Rules

- A resource node can only be dispatched when all its `hard` dependencies are in SATISFIED state
- `soft` dependencies do not block dispatch — they are attempted but failure does not block
- `conditional` dependencies are evaluated by the Policy Engine before the graph is constructed — if conditions are not met, the conditional dependency node is not added to the graph
- Independent branches of the dependency graph can be resolved in parallel — the Orchestration component determines parallelism
- Circular dependencies are invalid — the Policy Engine rejects any dependency graph with circular references

### 8.2 Failure Handling

Dependency failure handling is **configurable per request or per policy**:

| Failure Mode | Behavior |
|-------------|---------|
| `fail_all` | Any hard dependency failure fails the entire request. All partially realized nodes are decommissioned. |
| `fail_dependent` | A hard dependency failure fails only the dependent resource and its dependents. Independent branches continue. |
| `retry` | Failed dependencies are retried with the same or alternative provider before failing. Retry count and provider selection policy are configurable. |
| `partial_complete` | Request is marked partially complete. Failed nodes are flagged for retry or manual intervention. |

The failure mode is declared in the request payload or in an applicable organizational policy.

---

## 9. Rehydration and the Dependency Graph

The dependency graph is the primary mechanism enabling **DC Rehydration** — the ability to reconstruct any resource and its dependencies from scratch.

### 9.1 Rehydration Process

Rehydration uses the **Intent State** of the original request — not the Realized State — to reconstruct the dependency graph. This ensures that rehydration applies current policies and standards rather than replaying an old realized state.

```
Rehydration initiated for a Tenant / Group / Entity
  │
  ▼
Intent State(s) retrieved from Intent Store
  │
  ▼
Dependency graphs reconstructed from Intent States
  │
  ▼
Graphs processed through current Policy Engine
  │  Current policies applied — may differ from original request
  │  Current placement policies applied
  │  Current sovereignty constraints applied
  ▼
New Requested State payloads generated
  │
  ▼
Resources realized in dependency order
  │
  ▼
New Realized States recorded
```

### 9.2 Intent Portability in Rehydration

Because rehydration uses Intent State rather than Realized State:
- Resources can be rehydrated to a different provider — as long as the provider supports the required Resource Types
- Current organizational standards and policies are applied — ensuring rehydrated resources meet current compliance requirements
- Provider-specific dependencies (portability-breaking) may prevent rehydration to a different provider — this is surfaced as a portability warning during rehydration planning

### 9.3 Rehydration Scope

Rehydration can be scoped to:
- A single Resource/Service Entity and its full dependency graph
- A Resource Group — all entities in the group and their dependency graphs
- A Tenant — all entities owned by the Tenant
- A full Data Center — all entities across all Tenants in a location

The dependency graph ensures that rehydration is always complete — no orphaned resources, no missing dependencies.

---

## 10. Dependency Declaration in Service Catalog Items

Service Catalog Items must declare their dependencies as part of their definition. A catalog item with undeclared dependencies is invalid and will be rejected by the Policy Engine.

```yaml
catalog_item:
  uuid: <uuid>
  name: Web Server Service
  resource_type_uuid: <uuid of Compute.WebServer>
  type_level_dependencies:
    - dependency_uuid: <uuid>
      required_resource_type_uuid: <uuid of Compute.VirtualMachine>
      dependency_type: hard
      cardinality: one_to_one
  provider_specific_dependencies: []
  conditional_dependencies:
    - dependency_uuid: <uuid>
      required_resource_type_uuid: <uuid of Network.LoadBalancer>
      dependency_type: conditional
      condition:
        field: high_availability
        operator: equals
        value: true
      description: Load balancer required when high_availability is true
```

---

## 11. DCM System Policies for Dependencies

| Policy | Rule | Enforcement |
|--------|------|-------------|
| `DEP-001` | All dependencies must be declared before a catalog item is active | Enforced at catalog item registration |
| `DEP-002` | Circular dependencies are invalid | Enforced at dependency graph construction |
| `DEP-003` | Provider-specific dependencies must be marked portability-breaking | Enforced at provider catalog item registration |
| `DEP-004` | Dependency payloads must be passed to dependent providers in DCM unified format | Enforced at dependency satisfaction |
| `DEP-005` | Every node in a dependency graph must have a UUID | Enforced at graph construction |

---

## 11a. Dependency Graph Versioning (Q30)

Dependency graphs are versioned as properties of their parent catalog item — not as independent artifacts. When the dependency graph changes, the catalog item version increments following standard semver semantics:

| Change | Semver Impact | Reason |
|--------|--------------|--------|
| Dependency version constraint tightened | Revision bump | Compatible — narrower constraint |
| New optional dependency added | Minor bump | Compatible — additive |
| New required dependency added | **Major bump** | Breaking — consumers must update |
| Required dependency removed | **Major bump** | Breaking — consumers may depend on it |
| Dependency type changed | **Major bump** | Breaking — structural change |

**At request time:** The catalog item version determines the dependency graph. A consumer pinning to `catalog_item_version: "1.5.3"` gets exactly the dependency graph declared in that version.

**For existing realizations:** The dependency graph version is captured in the Requested State assembly provenance. Rehydration with `re_evaluate: false` replays from the Requested State. Rehydration with `re_evaluate: true` uses the current dependency graph for the selected version.

---

## 11b. Dependency Graph Storage (Q31)

The dependency graph is embedded in assembly provenance — not a separate entity.

| Level | What is stored | Where |
|-------|---------------|-------|
| Declared dependency graph | Part of Resource Type Specification | GitOps Layer/Policy Store |
| Resolved dependency graph | `placement.yaml` in Requested State | GitOps Requested Store |
| Realized dependency graph | Realized State events per dependency | Event Stream / Realized Store |

```yaml
# In placement.yaml — resolved dependency graph
dependency_resolution:
  - dependency_role: storage
    resource_type: Storage.Block
    resolved_provider_uuid: <uuid>
    resolved_catalog_item_version: "1.2.0"
    reserved_entity_uuid: <uuid>
    reservation_hold_uuid: <uuid>
  - dependency_role: networking
    resource_type: Network.IPAddress
    resolved_provider_uuid: <uuid>
    reserved_entity_uuid: <uuid>
```

The full dependency chain is always traceable from the Requested State record — no separate entity needed.

---

## 11c. Dependency Graph Depth (Q33)

Dependency graph depth is limited to a profile-governed maximum. Circular dependency detection is always enforced regardless of depth configuration.

```yaml
dependency_depth_policy:
  max_depth: 10                  # configurable via Policy Group
  on_max_exceeded: reject        # reject with clear error identifying depth + chain
  cycle_detection: always        # non-configurable — always enforced
```

**Profile-governed defaults:**

| Profile | Default Max Depth | Rationale |
|---------|-----------------|-----------|
| `minimal` | 20 | Home lab — free composition |
| `dev` | 15 | Development — generous |
| `standard` | 10 | Production baseline |
| `prod` | 10 | Production |
| `fsi` | 7 | Tight — complex dependencies harder to audit |
| `sovereign` | 7 | Maximum control |

In practice, well-designed service compositions rarely exceed 5-6 levels. Depth 10 provides headroom without allowing pathological compositions.

---

## 11d. Meta Provider Composition Visibility (Q34)

Meta Providers declare how their internal composition is exposed to DCM. This determines whether sub-resources are DCM entities subject to standard lifecycle management, or opaque to DCM.

```yaml
meta_provider_registration:
  composition_visibility:
    mode: <opaque|transparent|selective>
    # opaque:      Consumer sees only top-level service entity
    #              Sub-resources not visible in DCM
    # transparent: All sub-resources registered as DCM entities
    #              Full dependency graph visible; drift detection on all
    # selective:   Provider declares which sub-resources are DCM-visible
    dcm_visible_sub_resources:    # if selective
      - resource_type: Compute.VirtualMachine
        role: control_plane_node
      - resource_type: Network.LoadBalancer
        role: api_endpoint
```

**Drift detection interaction:**
- `opaque` — drift detection only on what the Meta Provider reports via realized payload; sub-resources are provider's responsibility
- `transparent` — drift detection on all sub-resources as full DCM entities
- `selective` — drift detection on declared DCM-visible sub-resources only

---

## 12. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | How are dependency graphs versioned — does a new version of a catalog item invalidate existing dependency graphs? | Versioning model | ✅ Resolved — versioned as part of catalog item; semver semantics; captured in assembly provenance (ENT-006) |
| 2 | Should the dependency graph be stored as a separate entity or embedded in the request payload? | Data model structure | ✅ Resolved — embedded in assembly provenance; declared in Resource Type Spec; resolved in placement.yaml (ENT-007) |
| 3 | How are cross-tenant dependencies handled? | Multi-tenancy | ✅ Resolved — governed by REL-010/011/012 and DEP-001/002/003; see Entity Relationships doc |
| 4 | Should there be a maximum dependency graph depth? | Operational complexity | ✅ Resolved — profile-governed max (10 standard/prod, 7 fsi/sovereign); circular detection always enforced (ENT-008) |
| 5 | How does the dependency graph interact with the Meta Provider model? | Provider model | ✅ Resolved — composition_visibility (opaque/transparent/selective); transparent/selective registers sub-resources as DCM entities (ENT-009) |

---

## 13. DCM System Policies — Dependency Gaps

| Policy | Rule |
|--------|------|
| `ENT-006` | Dependency graphs are versioned as properties of their parent catalog item. New required dependency or removed dependency is a major (breaking) version bump. The dependency graph version used in a realization is captured in assembly provenance. |
| `ENT-007` | The declared dependency graph is embedded in the Resource Type Specification. The resolved dependency graph is embedded in the Requested State assembly provenance (placement.yaml). No separate dependency graph entity is required. |
| `ENT-008` | Dependency graph depth is limited to a profile-governed maximum (default: 10 for standard/prod; 7 for fsi/sovereign). Requests exceeding the maximum depth are rejected with a clear error. Circular dependency detection is always enforced regardless of depth configuration. |
| `ENT-009` | Meta Providers declare composition_visibility as opaque, transparent, or selective. Transparent and selective modes register sub-resources as DCM entities subject to standard lifecycle management and drift detection. Opaque mode delegates sub-resource management entirely to the provider. |

---



- **Resource Type Specification** — declares type-level dependencies for a Resource Type
- **Provider Catalog Item** — declares provider-specific additional dependencies
- **Request Payload Processor** — constructs the dependency graph during assembly
- **Policy Engine** — evaluates conditional dependencies, enforces dependency policies, governs failure handling
- **Intent Portability** — rehydration uses Intent State to allow replay with different providers
- **Field-Level Provenance** — dependency payload data is recorded with source Entity UUID
- **Resource Grouping** — rehydration can be scoped to groups and tenants


---

## 8. Compound Service Compensation Declaration

### 8.1 Overview

Compound services (delivered by Meta Providers) must declare compensation behavior for each component. This declaration is part of the service definition — not discovered at runtime. See [Operational Models](24-operational-models.md) Section 6 for the full compensation execution model.

### 8.2 Compensation Fields on Service Components

```yaml
service_component:
  id: vm
  resource_type: Compute.VirtualMachine
  required_for_delivery: <atomic|partial>
  # atomic: must succeed; failure triggers full compensation rollback
  # partial: failure → DEGRADED state; compound service delivered partially

  compensation_on_failure: <decommission_immediately|release_allocation|skip|notify>
  # decommission_immediately: decommission this component as part of rollback
  # release_allocation:       release allocation back to pool (for allocatable resources)
  # skip:                     do not compensate; used for partial delivery components
  # notify:                   notify owner; human decides compensation

  compensation_order: <integer>
  # Lower numbers compensate first; higher numbers compensate last
  # Reverse dependency order is the default if not declared

  depends_on: [<component_ids>]
```

### 8.3 Partial Delivery Policy

```yaml
partial_delivery_policy:
  min_required_components: [vm, ip]  # compound DEGRADED if only these succeed
  degraded_is_acceptable: true
  auto_retry_optional_components:
    enabled: true
    max_attempts: 3
    interval: PT15M
    on_exhaustion: notify_owner
```

### 8.4 System Policies — Compensation

| Policy | Rule |
|--------|------|
| `DEP-010` | Compensation executes in reverse dependency order (highest compensation_order first). |
| `DEP-011` | Compensation failure triggers COMPENSATION_FAILED state and immediate orphan detection. |
| `DEP-012` | Components with required_for_delivery: partial are not compensation-triggering. Their failure produces a DEGRADED compound entity. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
