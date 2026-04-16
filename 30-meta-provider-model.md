# DCM Data Model — Meta Provider Composability Model


**Document Status:** ✅ Complete
**Document Type:** Architecture Reference — Meta Provider Specification
**Related Documents:** [Foundational Abstractions](00-foundations.md) | [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md) | [Service Dependencies](07-service-dependencies.md) | [Four States](02-four-states.md) | [Operational Models](24-operational-models.md) | [Scoring Model](29-scoring-model.md) | [Control Plane Components](25-control-plane-components.md)

> **This document maps to: DATA + PROVIDER**
>
> A Meta Provider is a typed Provider that declares a compound service composition to DCM. The compound service it delivers is Data — a Composite Entity across all four states. DCM's standard machinery (Placement Engine, Orchestration Flow Policy, Recovery Policy) handles everything beyond registration and constituent execution. The Meta Provider is not an orchestrator — it is a compound service definition plus a set of standard Service Providers that happen to serve multiple resource types within the same system.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)

---

## 1. What a Meta Provider Is

### 1.1 The Core Model

A Meta Provider is a **compound Service Provider** that uses other providers in the DCM catalog to fulfill a higher-order service request. Its defining characteristic is that it registers a **compound service definition** — a declaration of constituent resource types, their dependencies, and their delivery requirements — so that DCM has enough information to:

1. **Select appropriate constituent providers** via the standard Placement Engine
2. **Determine execution order** from the dependency graph
3. **Govern rehydration sequence** using the same dependency information

Beyond providing that definition, a Meta Provider operates as a standard Service Provider for each constituent resource type it owns. DCM's standard machinery handles everything else: placement, sequencing, failure handling, compensation, and audit.

**A Meta Provider is not an orchestrator.** It does not:
- Select constituent providers — the Placement Engine does this
- Sequence execution rounds — the dependency graph informs DCM's Orchestration Flow Policy
- Manage parallel execution — parallelism is derived from the dependency graph (resources with no unresolved dependencies execute simultaneously)
- Run compensation — DCM's Recovery Policy executes compensation using the dependency graph in reverse
- Make routing decisions — these are DCM policy decisions

### 1.2 Why This Model Is Correct

Every DCM design principle is preserved:
- **Governance stays with DCM** — constituent provider selection goes through the Placement Engine, including sovereignty filtering, accreditation checking, and trust scoring
- **Policy stays with DCM** — GateKeeper, Validation, and Transformation policies fire on the compound payload; the same policies govern each constituent sub-request
- **Audit stays with DCM** — each constituent request is a standard DCM request with its own audit trail; the compound audit is assembled from constituent audit records
- **Recovery stays with DCM** — the Recovery Policy handles constituent failures using the dependency graph; the Meta Provider does not make recovery decisions

### 1.3 The Practical Meaning

A Meta Provider registration tells DCM: "Here is a compound service called `ApplicationStack.WebApp`. To fulfill it, you will need a `Compute.VirtualMachine`, a `Network.IPAddress`, a `DNS.Record` (which depends on both), and a `Network.LoadBalancer` (which also depends on both). I can provide the DNS and LoadBalancer; you should place the VM and IP with appropriate compute and network providers."

DCM then:
- Creates a Composite Entity with one entity UUID
- Runs the compound layer assembly to produce the full payload
- Applies policies to the compound payload
- Dispatches constituent sub-requests to the appropriate providers (compute provider for VM, network provider for IP, Meta Provider for DNS and LoadBalancer)
- Sequences those sub-requests based on the declared dependency graph
- Handles any constituent failures using Recovery Policy
- Assembles the aggregate Realized State from all constituent realized states

The Meta Provider's execution responsibility is limited to: naturalizing and realizing the constituent resource types it owns, then denaturalizing and returning the realized state — exactly as a standard Service Provider does.

---

## 2. Compound Service Definition

The compound service definition is the primary contribution of compound resource type specifications to DCM. It is declared at registration and stored in the Resource Type Registry as a compound Resource Type Specification.

### 2.1 Constituent Declaration

```yaml
resource_types_composed:
  - fqn: ApplicationStack.WebApp
    version: "2.0.0"

    constituents:
      - component_id: vm-primary
        resource_type: Compute.VirtualMachine
        provided_by: external    # DCM places this with an appropriate compute provider
        depends_on: []
        required_for_delivery: required

      - component_id: ip-primary
        resource_type: Network.IPAddress
        provided_by: external    # DCM places this with an appropriate network provider
        depends_on: []
        required_for_delivery: required

      - component_id: dns-primary
        resource_type: DNS.Record
        provided_by: self        # This Meta Provider handles DNS
        depends_on: [vm-primary, ip-primary]
        required_for_delivery: partial

      - component_id: lb-frontend
        resource_type: Network.LoadBalancer
        provided_by: self        # This Meta Provider handles LoadBalancer
        depends_on: [vm-primary, ip-primary]
        required_for_delivery: partial

    composition_visibility: selective   # opaque | transparent | selective
    dcm_visible_sub_resources:
      - resource_type: Compute.VirtualMachine
        role: application_host
      - resource_type: Network.LoadBalancer
        role: ingress_endpoint
```

### 2.2 provided_by Declaration

`provided_by` is the key field that tells DCM who is responsible for each constituent:

| Value | Meaning |
|-------|---------|
| `self` | This Meta Provider handles this constituent. DCM dispatches it to the Meta Provider. |
| `external` | DCM places this constituent with the best available provider via the standard Placement Engine. |
| `<provider_uuid>` | DCM dispatches this constituent to a specific named provider. |

For `external` constituents, DCM runs a full placement cycle — sovereignty filtering, accreditation checking, trust scoring, reserve query — exactly as it would for any standalone request.

For `self` constituents, DCM dispatches to the Meta Provider using the standard Services API. The Meta Provider receives a standard constituent payload and responds with a standard realized state — no special handling required.

### 2.3 Dependency Graph

The `depends_on` list is the mechanism by which the Meta Provider informs DCM of execution ordering. DCM reads this graph and:

- Identifies which constituents have no dependencies → dispatches these first (or simultaneously)
- Identifies which constituents have dependencies on already-realized constituents → dispatches these when their dependencies are complete
- Derives parallelism directly from the graph — constituents with no shared unresolved dependencies execute concurrently within DCM's standard pipeline

**The Meta Provider does not manage this sequencing.** It declares the graph. DCM executes it.

```
depends_on: []                          → eligible for immediate dispatch
depends_on: [vm-primary]                → dispatched after vm-primary is REALIZED
depends_on: [vm-primary, ip-primary]    → dispatched after BOTH are REALIZED
```

### 2.4 required_for_delivery Classification

Each constituent declares how its success or failure affects the compound service:

| Classification | Failure effect |
|----------------|---------------|
| `required` | DCM halts the compound request; triggers Recovery Policy; unrealized constituents are not dispatched |
| `partial` | DCM notes the failure; compound service continues; final status may be `DEGRADED` |
| `optional` | DCM notes the failure; compound service continues unaffected |

The Recovery Policy governs what happens on `required` constituent failure — the same Recovery Policy that governs any request failure. No special Meta Provider recovery logic exists.

---

## 3. Composite Entity — Four-State Representation

A compound service request produces a **Composite Entity** — a single DCM entity that aggregates constituent sub-entities. The Composite Entity has one entity UUID that links it across all four states.

### 3.1 Intent State

The consumer submits one request against the compound catalog item. The intent payload contains consumer-declared fields for the compound service — not individual constituent fields.

```yaml
entity_uuid: <uuid>          # assigned at intent creation; stable across all states
catalog_item_uuid: <uuid>    # ApplicationStack.WebApp
fields:
  app_name: payments-api
  environment: production
  region: EU-WEST
  cpu_count: 4
  memory_gb: 16
  dns_hostname: payments-api.internal.corp.example
```

DCM does not expand this into constituent requests at Intent State. The intent is stored as-is.

### 3.2 Requested State

The Request Payload Processor expands the compound intent into the full constituent payload. This is where the compound service definition from the Meta Provider registration is applied.

```yaml
entity_uuid: <uuid>
composite_entity: true
compound_service_provider_uuid: <uuid>

top_level:
  app_name: payments-api
  environment: production
  region: EU-WEST

constituents:
  - component_id: vm-primary
    resource_type: Compute.VirtualMachine
    provided_by: external
    provider_uuid: null        # resolved by Placement Engine
    fields:
      cpu_count: 4
      memory_gb: 16
      os_family: rhel
    depends_on: []
    required_for_delivery: required

  - component_id: ip-primary
    resource_type: Network.IPAddress
    provided_by: external
    provider_uuid: null        # resolved by Placement Engine
    fields:
      ip_version: 4
      allocation_pool: prod-EU-WEST
    depends_on: []
    required_for_delivery: required

  - component_id: dns-primary
    resource_type: DNS.Record
    provided_by: self
    provider_uuid: <provider_uuid>
    fields:
      hostname: payments-api.internal.corp.example
      record_type: A
    depends_on: [vm-primary, ip-primary]
    required_for_delivery: partial

  - component_id: lb-frontend
    resource_type: Network.LoadBalancer
    provided_by: self
    provider_uuid: <provider_uuid>
    fields:
      backend_component: vm-primary
    depends_on: [vm-primary, ip-primary]
    required_for_delivery: partial
```

### 3.3 Realized State

The Realized State is assembled by DCM from the constituent realized payloads returned by each dispatched provider. DCM writes it as a unified composite record.

```yaml
entity_uuid: <uuid>
composite_entity: true
composite_status: DEGRADED    # REALIZED | DEGRADED | FAILED

composite_fields:             # synthesized consumer-facing view
  primary_ip: 10.1.45.23
  vm_id: vm-0a1b2c3d
  lb_endpoint: lb-7f8e9d.eu-west.corp
  dns_name: null              # absent — dns constituent failed

constituents_realized:
  - component_id: vm-primary
    status: REALIZED
    provider_uuid: <compute_provider_uuid>
    realized_fields:
      vm_id: vm-0a1b2c3d
      hypervisor_host: host-eu-w-04
    required_for_delivery: required

  - component_id: ip-primary
    status: REALIZED
    provider_uuid: <network_provider_uuid>
    realized_fields:
      assigned_ip: 10.1.45.23
    required_for_delivery: required

  - component_id: dns-primary
    status: FAILED
    provider_uuid: <provider_uuid>
    failure_reason: "DNS service degraded — record not created"
    required_for_delivery: partial

  - component_id: lb-frontend
    status: REALIZED
    provider_uuid: <provider_uuid>
    realized_fields:
      lb_id: lb-7f8e9d
      endpoint: lb-7f8e9d.eu-west.corp
    required_for_delivery: partial

degradation_summary:
  - component_id: dns-primary
    impact: "DNS name resolution unavailable — access via IP only"
    recovery_eligible: true
```

### 3.4 Discovered State

Discovery for composite entities follows the composition visibility mode:

- `opaque` — DCM schedules one discovery call to the Meta Provider; it returns the compound discovered state as a single payload
- `transparent` — DCM schedules independent discovery calls to each constituent's provider; drift detection runs on each constituent independently
- `selective` — DCM schedules discovery calls for DCM-visible constituents; opaque discovery for the rest via Meta Provider

---

## 4. What DCM Does vs What the Meta Provider Does

This table is the definitive statement of responsibility.

| Concern | DCM | Meta Provider |
|---------|-----|---------------|
| Compound catalog item presentation | ✅ — Service Catalog manages the compound item | Declares the compound service definition at registration |
| Consumer-facing API | ✅ — Consumer API handles compound requests identically to simple requests | — |
| Layer assembly | ✅ — Request Payload Processor assembles constituent blocks from compound service definition | — |
| Policy evaluation on compound payload | ✅ — Same Policy Engine, same policies, same scoring model | May contribute provider-domain policies for its own constituents |
| External constituent placement | ✅ — Placement Engine selects provider for each `provided_by: external` constituent | Declares what resource types each constituent needs so placement can filter appropriately |
| Self constituent dispatch | ✅ — API Gateway dispatches to Meta Provider using standard Services API | Receives constituent payload; naturalizes; executes; denaturalizes; returns realized state |
| Execution ordering from dependency graph | ✅ — Derived from `depends_on` declarations; DCM dispatches in order | Declares `depends_on` relationships for each constituent |
| Parallelism | ✅ — Constituents with no unresolved dependencies execute concurrently within DCM's pipeline | Emerges from the dependency graph declaration; Meta Provider does not manage this |
| Constituent failure handling | ✅ — Recovery Policy fires based on `required_for_delivery` classification | Declares `required_for_delivery` for each constituent |
| Compensation (teardown of realized constituents on failure) | ✅ — Recovery Policy executes compensation using dependency graph in reverse | Implements standard decommission handling for `self` constituents |
| Composite status determination | ✅ — Determined by DCM from constituent outcomes and `required_for_delivery` | — |
| Realized State assembly | ✅ — DCM assembles composite Realized State from constituent realized payloads | Returns standard realized payload for `self` constituents |
| Drift detection | ✅ — Standard drift detection per composition visibility mode | Implements standard discovery endpoint for `self` constituents |
| Lifecycle management of Composite Entity | ✅ — Standard DCM entity lifecycle | Handles decommission of `self` constituents when decommission payload received |
| Audit trail | ✅ — Each constituent request has its own audit record; composite audit assembled by DCM | — |

### 4.1 The Compound Orchestration Scope Is Narrow

For each `self` constituent, the Meta Provider:
1. Receives a standard DCM constituent payload (already fully assembled by DCM)
2. Naturalizes it to its native format
3. Executes the realization
4. Denaturalizes the result
5. Returns a standard realized payload

This is identical to what any Service Provider does. The Meta Provider is not special during execution — it is simply a Service Provider that happens to be registered for multiple resource types within the same underlying system.

---

## 5. Composition Visibility

Introduced in [07-service-dependencies.md](07-service-dependencies.md), this section specifies the operational implications.

| Mode | Consumer sees | DCM manages independently | Drift detection |
|------|--------------|--------------------------|-----------------|
| `opaque` | Top-level entity only | Composite entity only | Via Meta Provider discovery endpoint |
| `transparent` | All constituents as DCM entities | All constituent entities individually | Per-constituent via each provider |
| `selective` | Declared visible constituents | Declared visible constituents | Per-constituent for visible; via Meta Provider for rest |

### 5.1 Transparent Mode Entity UUIDs

In transparent mode, constituent entities receive stable DCM entity UUIDs:
```
constituent_entity_uuid = deterministic_uuid(parent_entity_uuid + component_id)
```

These UUIDs are stable across rehydration — the same compound entity always produces the same constituent UUIDs. This enables consistent audit trail linkage.

### 5.2 Decommission Cascade

When a composite entity is decommissioned:
- DCM dispatches constituent decommission sub-requests in dependency-reverse order
- Each constituent's provider (whether `self` or `external`) receives a standard decommission payload
- The composite entity's lifecycle state transitions to DECOMMISSIONED only after all constituents confirm decommission

---

## 6. Rehydration

Rehydration of a composite entity is the primary use case for the dependency graph declaration — which the Meta Provider provides precisely for this purpose.

### 6.1 Rehydration Sequence

DCM reads the `depends_on` graph and rehydrates constituents in dependency order:

```
Round 1: components with depends_on: []          → rehydrate first
Round 2: components whose depends_on are realized → rehydrate next
Round N: continue until all constituents complete
```

The compound spec's dependency declarations give DCM exactly the information it needs to sequence rehydration correctly without requiring any special Meta Provider involvement beyond standard constituent execution.

### 6.2 Rehydration Provider Selection

`provided_by: external` constituents are re-placed by the Placement Engine during rehydration — they may end up on a different provider than the original realization if the original provider is no longer eligible. `provided_by: self` constituents always return to the same Meta Provider.

---

## 7. Compound Request Pipeline

A compound service request flows through DCM's standard pipeline with compound-specific extensions at the Request Payload Processor step.

```
Consumer submits compound request
  │
  ▼ Intent State captured (compound intent, no constituent expansion)
  │
  ▼ Request Payload Processor:
  │   Layer assembly on compound payload
  │   Expansion: compound service definition → constituent blocks
  │     (resource_type, provided_by, fields, depends_on, required_for_delivery per constituent)
  │   Policy evaluation on compound payload (GateKeeper, Validation, Transformation, scoring)
  │   Placement: external constituents → Placement Engine
  │             self constituents     → Meta Provider
  │
  ▼ Requested State written (full constituent specification with provider assignments)
  │
  ▼ Constituent dispatch — dependency-ordered by DCM:
  │   Round 1 (no dependencies): dispatch vm-primary, ip-primary in parallel
  │     vm-primary → compute_provider (standard Services API)
  │     ip-primary → network_provider (standard Services API)
  │
  │   Round 2 (vm+ip REALIZED): dispatch dns-primary, lb-frontend in parallel
  │     dns-primary → designated_service_provider (standard Services API)
  │     lb-frontend → designated_service_provider (standard Services API)
  │
  │   Any constituent FAILS:
  │     required  → Recovery Policy fires; unstarted constituents cancelled
  │     partial   → noted as degraded; execution continues
  │     optional  → noted; execution continues
  │
  ▼ Constituent realized payloads collected by DCM
  │
  ▼ Composite status determined: REALIZED | DEGRADED | FAILED
  │
  ▼ Realized State written (composite record assembled by DCM)
  │
  ▼ Consumer notified of compound request outcome
```

---

## 8. Nested Meta Providers

A Meta Provider may declare a constituent with `provided_by: external` where the appropriate provider is itself another Meta Provider. DCM's Placement Engine handles this transparently — it places the constituent with whichever registered provider best satisfies the constraints, whether that is a simple Service Provider or another Meta Provider.

**Maximum nesting depth: 3** — enforced by DCM at placement time by checking the compound service definition chain depth. Deeper nesting creates dependency graph complexity that exceeds DCM's governance model.

**The nested Meta Provider has no special awareness** that it is being called as a constituent of an outer compound service. It receives a standard constituent payload and responds with a standard realized state. Nesting is a DCM-level concept, not a provider-level one.

---

## 9. Scoring Model Integration

Compound service requests are scored using the standard five-signal model with two compound-specific behaviors:

**Operational GateKeepers** fire on the compound payload assembled from the top-level fields and declared constituent types. They do not fire per-constituent (constituent-level policy evaluation happens in each constituent sub-request's own pipeline).

**Provider accreditation richness (Signal 5)** for compound entities uses the lowest richness score among all `required_for_delivery: required` constituents across all their assigned providers. The compound service is only as well-accredited as its least-accredited required constituent.

---

## 10. Meta Provider Registration Contract

```yaml
compound_service_capabilities:
  # Resource types this Meta Provider handles as a self provider
  resource_types_provided:
    - DNS.Record
    - Network.LoadBalancer

  # Compound service definitions this Meta Provider offers
  resource_types_composed:
    - fqn: ApplicationStack.WebApp
      version: "2.0.0"
      constituents:
        - component_id: vm-primary
          resource_type: Compute.VirtualMachine
          provided_by: external
          depends_on: []
          required_for_delivery: required
        - component_id: ip-primary
          resource_type: Network.IPAddress
          provided_by: external
          depends_on: []
          required_for_delivery: required
        - component_id: dns-primary
          resource_type: DNS.Record
          provided_by: self
          depends_on: [vm-primary, ip-primary]
          required_for_delivery: partial
        - component_id: lb-frontend
          resource_type: Network.LoadBalancer
          provided_by: self
          depends_on: [vm-primary, ip-primary]
          required_for_delivery: partial
      composition_visibility: selective
      dcm_visible_sub_resources:
        - resource_type: Compute.VirtualMachine
          role: application_host
        - resource_type: Network.LoadBalancer
          role: ingress_endpoint

  # Standard provider declarations apply as for any Service Provider
  # (sovereignty, accreditations, capacity reporting, health check, etc.)
```

---

## 11. System Policies

| Policy | Rule |
|--------|------|
| `MPX-001` | A Meta Provider's `self` constituents are dispatched using the standard Services API. The Meta Provider receives a standard constituent payload and returns a standard realized state. No special dispatch protocol exists for Meta Provider self-constituents. |
| `MPX-002` | Constituent execution ordering is derived from the `depends_on` declaration by DCM. The Meta Provider does not sequence constituent dispatch. |
| `MPX-003` | Parallelism in constituent execution is derived from the dependency graph. Constituents with no unresolved dependencies execute concurrently within DCM's standard pipeline. The Meta Provider does not manage this. |
| `MPX-004` | Composite status determination (`REALIZED` / `DEGRADED` / `FAILED`) is performed by DCM based on constituent outcomes and `required_for_delivery` classifications. |
| `MPX-005` | Recovery Policy governs all constituent failure handling and compensation. The Meta Provider does not make recovery decisions. It implements standard decommission handling for `self` constituents when a decommission payload arrives. |
| `MPX-006` | `provided_by: external` constituents are placed by the Placement Engine using standard placement rules. The Meta Provider does not influence external constituent provider selection. |
| `MPX-007` | In transparent composition visibility mode, constituent entity UUIDs are `deterministic_uuid(parent_entity_uuid + component_id)` — stable across rehydration. |
| `MPX-008` | Maximum Meta Provider nesting depth is 3, enforced by DCM at placement time by checking the compound service definition chain depth. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
