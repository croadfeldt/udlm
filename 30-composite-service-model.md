# DCM Data Model — Composite Service Composition Model

**Document Type:** Architecture Reference — Composite Service Specification
**Status:** Active
**Audience:** Architects, Service Provider implementers, Policy authors

> A Composite Service is a catalog item that delivers a composite payload — multiple constituent resource types, with declared dependencies and delivery requirements — through a single request. It is fulfilled by ordinary Service Providers (one or more), governed by ordinary DCM policies, and produces a Composite Entity at runtime. There is no separate "meta provider" type. A Service Provider that registers a Composite Service simply declares the composition definition and fulfills the constituents whose `provided_by: self` flag points at it; everything else is DCM's standard machinery.

---

## 1. What a Composite Service Is

### 1.1 The Core Model

A Composite Service is a **catalog-level definition** that declares:

1. A set of constituent resource types
2. Their dependencies on each other
3. Their delivery requirements (required, partial, optional)
4. Which provider fulfills each one

DCM uses that declaration to:

1. **Select appropriate constituent providers** via the standard Placement Engine
2. **Determine execution order** from the dependency graph
3. **Govern rehydration sequence** using the same dependency information

A Service Provider that registers a Composite Service operates as a standard Service Provider for each constituent resource type it owns (those flagged `provided_by: self`). DCM's standard machinery handles everything else: placement, sequencing, failure handling, compensation, and audit.

**A Composite Service is not an orchestrator.** Its definition does not:
- Select constituent providers — the Placement Engine does this
- Sequence execution rounds — the dependency graph informs DCM's Orchestration Flow Policy
- Manage parallel execution — parallelism is derived from the dependency graph (resources with no unresolved dependencies execute simultaneously)
- Run compensation — DCM's Recovery Policy executes compensation using the dependency graph in reverse
- Make routing decisions — these are DCM policy decisions

### 1.2 Why This Model Is Correct

Every DCM design principle is preserved:
- **Governance stays with DCM** — constituent provider selection goes through the Placement Engine, including sovereignty filtering, accreditation checking, and trust scoring
- **Policy stays with DCM** — GateKeeper, Validation, and Transformation policies fire on the composite payload; the same policies govern each constituent sub-request
- **Audit stays with DCM** — each constituent request is a standard DCM request with its own audit trail; the composite audit is assembled from constituent audit records
- **Recovery stays with DCM** — the Recovery Policy handles constituent failures using the dependency graph; the Composite Service definition does not make recovery decisions

### 1.3 The Practical Meaning

A Composite Service registration tells DCM: "Here is a Composite Service called `ApplicationStack.WebApp`. To fulfill it, you will need a `Compute.VirtualMachine`, a `Network.IPAddress`, a `DNS.Record` (which depends on both), and a `Network.LoadBalancer` (which also depends on both). I can provide the DNS and LoadBalancer; you should place the VM and IP with appropriate compute and network providers."

DCM then:
- Creates a Composite Entity with one entity UUID
- Runs the composite layer assembly to produce the full payload
- Applies policies to the composite payload
- Dispatches constituent sub-requests to the appropriate providers (compute provider for VM, network provider for IP, the registering provider for DNS and LoadBalancer)
- Sequences those sub-requests based on the declared dependency graph
- Handles any constituent failures using Recovery Policy
- Assembles the aggregate Realized State from all constituent realized states

The registering provider's execution responsibility is limited to: naturalizing and realizing the constituent resource types it owns, then denaturalizing and returning the realized state — exactly as a standard Service Provider does.

---

## 2. Composite Service Definition

A Composite Service registration declares a composite payload structure: which constituent resource types make up the service, how they relate, and who fulfills each one.

### 2.1 Constituent Declaration

Each constituent in the composition definition declares:

```yaml
constituents:
  - component_id: vm           # local identifier within this composite
    resource_type: Compute.VirtualMachine
    provided_by: external      # DCM places via Placement Engine
    depends_on: []
    required_for_delivery: required

  - component_id: ip
    resource_type: Network.IPAddress
    provided_by: external
    depends_on: []
    required_for_delivery: required

  - component_id: dns
    resource_type: DNS.Record
    provided_by: self          # registering provider fulfills directly
    depends_on: [vm, ip]
    required_for_delivery: required

  - component_id: lb
    resource_type: Network.LoadBalancer
    provided_by: self
    depends_on: [vm, ip]
    required_for_delivery: partial
```

Field semantics:

- **`component_id`** — Stable identifier for the constituent within this composite. Used in `depends_on` references, runtime status reporting (`constituent_status`), and (in transparent visibility mode) UUID derivation.
- **`resource_type`** — Standard resource type identifier from the Resource Type Registry.
- **`provided_by`** — Either `self` (the registering provider fulfills it) or `external` (DCM's Placement Engine selects a provider).
- **`depends_on`** — Component IDs whose realized state must exist before this constituent can be dispatched. The dependency graph is constructed from these declarations.
- **`required_for_delivery`** — See §2.4.

### 2.2 provided_by Declaration

Two values:

- **`self`** — The registering provider fulfills this constituent directly. At dispatch time, DCM sends a standard constituent payload to this provider's standard Services API endpoint. The provider returns a standard realized state. There is no special "composite dispatch" protocol — the provider receives one constituent's payload, just as it would for any standalone request for that resource type.
- **`external`** — DCM's Placement Engine selects an eligible provider for this constituent at request time. Sovereignty filtering, accreditation checking, and trust scoring all apply normally. The Composite Service definition has no influence on this selection.

A single Composite Service can mix `self` and `external` constituents freely.

### 2.3 Dependency Graph

DCM constructs a directed acyclic graph from the `depends_on` declarations. Constituents with no unresolved dependencies execute concurrently within DCM's standard pipeline. Each dependency edge encodes that the source constituent's realized state must exist before the target constituent can be dispatched.

The dependency graph drives:
- **Forward execution** — constituent dispatch order during request fulfillment
- **Compensation order** — dependency-reverse during teardown
- **Rehydration order** — dependency-forward during rehydration
- **Decommission cascade** — dependency-reverse during decommission

DCM detects cycles at registration time and rejects the composition definition.

### 2.4 required_for_delivery Classification

Each constituent declares how its failure affects the composite outcome:

- **`required`** — Failure halts the composite request and triggers compensation. Composite status becomes `FAILED`.
- **`partial`** — Failure is recorded but does not halt the composite. Composite status becomes `DEGRADED`. Whether DEGRADED is acceptable as a final state is a profile-level decision.
- **`optional`** — Failure is noted but ignored. Composite status reflects only required and partial constituents.

These classifications are evaluated by DCM, not by the registering provider, when computing composite status from constituent outcomes.

---

## 3. Composite Entity — Four-State Representation

A Composite Service request produces a Composite Entity that exists across all four DCM states (Intent, Requested, Realized, Discovered) as a single entity with one UUID.

### 3.1 Intent State

Intent records the consumer's declared intent without expansion. The Composite Entity Intent record contains the catalog reference and the consumer-supplied parameters; constituents are not yet enumerated.

```yaml
entity_kind: composite
catalog_ref: ApplicationStack.WebApp/v2
parameters:
  size: medium
  region: us-east-1
  domain: example.com
```

### 3.2 Requested State

Requested expands the intent: DCM applies the Composite Service definition, runs the layer assembly to inject defaults and standards, applies all policies, resolves `external` placements, and produces the full constituent block.

```yaml
entity_kind: composite
entity_uuid: <composite_uuid>
parent_composite_uuid: null
catalog_ref: ApplicationStack.WebApp/v2
constituents:
  - component_id: vm
    constituent_uuid: <vm_uuid>
    resource_type: Compute.VirtualMachine
    placement: { provider: dc1-vmware }
    payload: { ... }
  - component_id: ip
    ...
  - component_id: dns
    placement: { provider: <registering_provider> }
    payload: { ... }
  - component_id: lb
    ...
```

Constituent UUIDs are generated according to §5.1 (composition visibility).

The Requested state is fully assembled before any constituent dispatch occurs. Constituent payloads do not contain references to dependencies' realized state — those are filled in at dispatch time via binding fields (see doc 38, request dependency graph).

### 3.3 Realized State

Realized records the runtime outcome. As constituent dispatches return, their realized states are recorded against the corresponding component_id. The Composite Entity's `lifecycle_state` reflects the aggregate:

| Composite lifecycle_state | Meaning |
|---------------------------|---------|
| `OPERATIONAL` | All `required` constituents are OPERATIONAL. `partial` constituents are OPERATIONAL or accepted-degraded. |
| `DEGRADED` | All `required` constituents are OPERATIONAL but one or more `partial` constituents failed. Whether this is a valid terminal state depends on profile policy. |
| `FAILED` | One or more `required` constituents failed. Compensation has been triggered. |
| `COMPENSATING` | Recovery Policy is executing compensation (dependency-reverse decommission of successfully realized constituents). |
| `COMPENSATION_FAILED` | Compensation itself failed. Orphan detection is active for any constituents not cleanly torn down. |
| `PARTIALLY_COMPENSATED` | Compensation completed with one or more constituents that could not be torn down cleanly. |

Each constituent's individual `lifecycle_state` is also recorded and queryable via the standard request status endpoint and the SSE stream. The runtime status field surfaces both: top-level composite state plus per-constituent state.

### 3.4 Discovered State

Discovered State for a Composite Entity is derived: there is no provider-side "discover composite" call. Instead, each constituent's Discovered State is collected via that constituent's own provider, and the composite's Discovered State is the aggregate. Drift detection runs at two levels: per-constituent (standard provider drift detection) and composite-level (does the set of realized constituents still match the requested composition definition?).

---

## 4. What DCM Does vs What the Registering Provider Does

| Concern | DCM | Registering Provider |
|---------|-----|----------------------|
| Catalog publication | Stores Composite Service registrations; publishes as catalog items | Provides registration: composition definition + constituent declarations |
| Placement of `external` constituents | Selects providers via Placement Engine | — |
| Policy evaluation (composite payload) | Runs all policies on assembled payload | — |
| Dependency graph construction | Built from `depends_on` declarations | — |
| Constituent dispatch sequencing | Derived from dependency graph | — |
| Constituent dispatch (`self`) | Sends standard constituent payload to provider | Receives constituent payload via standard Services API; returns standard realized state |
| Constituent dispatch (`external`) | Sends standard constituent payload to placed provider | — |
| Composite status determination | Computed from constituent outcomes + `required_for_delivery` classifications | — |
| Failure handling | Recovery Policy decides response | Provides standard decommission handling for `self` constituents |
| Compensation | Executes dependency-reverse decommission | Receives standard decommission calls for `self` constituents |
| Audit | Aggregates per-constituent audit records into composite audit trail | — |

### 4.1 The Composite Orchestration Scope Is Narrow

The registering provider's responsibility for a Composite Service is structurally identical to a standard Service Provider's responsibility for a single resource type. It receives constituent payloads one at a time (one per dispatched constituent it owns), it returns realized states one at a time, and it implements standard decommission handling. There is no "composite dispatch" API, no "constituent orchestration loop" inside the provider, and no provider-side aggregation.

Aggregation is DCM's responsibility. Sequencing is DCM's responsibility. Failure handling is DCM's responsibility.

---

## 5. Composition Visibility

A Composite Service registration declares its `composition_visibility`:

| Mode | Meaning |
|------|---------|
| `opaque` | Only the Composite Entity UUID is exposed to consumers. Constituent UUIDs exist internally for DCM bookkeeping but are not surfaced. Status reporting reports composite-level state only. |
| `transparent` | All constituents are first-class DCM entities with their own UUIDs, queryable individually. Constituent state is surfaced in status reporting. |
| `selective` | A declared subset of constituents are surfaced as DCM entities; the remainder are opaque. Useful when some constituents are implementation detail and others are operationally relevant. |

Visibility affects:
- Status reporting: per-constituent state is surfaced for transparent and (selectively) for selective; not for opaque
- Audit query: queryable per-constituent for transparent and selective; only at composite level for opaque
- Decommission targeting: in transparent mode, an operator can decommission individual constituents (subject to policy); in opaque mode, only the composite as a whole

### 5.1 Transparent Mode Entity UUIDs

In transparent composition visibility mode, constituent entity UUIDs are deterministic:

```
constituent_uuid = deterministic_uuid(parent_composite_uuid + component_id)
```

This produces stable UUIDs across rehydration: a composite that gets rehydrated retains the same constituent UUIDs even after a state-store rebuild. Without this rule, constituent UUIDs would change on rehydration and external references to them would break.

In opaque and selective modes, internal-only constituent UUIDs follow the same rule for the same reason; only their visibility to consumers differs.

### 5.2 Decommission Cascade

A composite decommission triggers per-constituent decommission in dependency-reverse order. DCM dispatches standard decommission calls to each constituent's provider (the registering provider for `self` constituents, the placed provider for `external` constituents). Decommission failures invoke standard Recovery Policy.

In transparent or selective mode, a constituent can be decommissioned independently of the composite, but only if the constituent's `required_for_delivery` is `optional`. Decommissioning a `required` constituent independently is rejected; the composite must be decommissioned as a whole.

---

## 6. Rehydration

Composite Entity rehydration follows the dependency graph in dependency-forward order, restoring constituents to their previously realized state.

### 6.1 Rehydration Sequence

For each constituent in dependency-forward order:

1. Resolve the constituent's provider:
   - `self` constituents: dispatched to the registering provider as it stands at rehydration time
   - `external` constituents: re-resolved via Placement Engine using the rehydration policy (faithful, provider-portable, historical-exact, or historical-portable; see doc 17)
2. Send the standard rehydration payload to the resolved provider
3. Record the resulting realized state

### 6.2 Rehydration Provider Selection

For `external` constituents, the rehydration policy determines which provider receives the rehydration call:

- **`faithful`** — The same provider instance. If unavailable, rehydration fails.
- **`provider_portable`** — Any provider of the same provider type. Allows rehydration after the original provider has been retired.
- **`historical_exact`** — The provider type that was selected at original placement time, reading the historical placement record.
- **`historical_portable`** — Any provider of that type, with historical placement as a hint but not a hard requirement.

For `self` constituents, the registering provider is dispatched to as it currently exists; if the registering provider has changed (different version, different tenant, etc.) the rehydration may fail or succeed depending on whether the registration is still compatible with the recorded request.

---

## 7. Composite Request Pipeline

A Composite Service request flows through DCM's standard request pipeline with one additional phase (composite expansion):

```
1. Intent       Consumer submits catalog request (catalog_ref + parameters)
2. Expansion    DCM looks up the Composite Service definition; produces the
                constituent block. At this point the Requested state contains
                fully enumerated constituents but NO dependency-resolved
                runtime values.
3. Layer        Standard layer assembly applies to each constituent's payload
   assembly     (defaults, standards, organization layers, etc.).
4. Placement    For each `external` constituent, the Placement Engine selects
                a provider. `self` constituents bind to the registering
                provider.
5. Policy       All standard policies fire against the composite payload:
                Validation, Transformation, GateKeeper, Authorization. A
                policy decision rejecting any constituent rejects the
                composite.
6. Dispatch     DCM walks the dependency graph in dependency-forward order.
                Constituents with no unresolved dependencies dispatch
                concurrently. Each dispatch is a standard request to the
                resolved provider with that constituent's payload (plus any
                runtime values bound from previously realized constituents
                via binding fields).
7. Aggregation  As constituent realized states return, DCM records them
                against component_ids and updates the Composite Entity's
                lifecycle_state.
8. Resolution   When all constituents have terminated (succeeded or failed),
                the composite reaches a terminal state (OPERATIONAL,
                DEGRADED, FAILED, or one of the compensation terminal
                states).
```

Failure at any stage routes through Recovery Policy, which decides between retry, partial acceptance, or compensation.

---

## 8. Nested Composite Services

A Composite Service can declare another Composite Service as a constituent, producing nested composites. Maximum nesting depth is 3 (enforced at registration time; see §11, CMP-008).

Nested composites are expanded recursively: the outer composite's expansion phase produces an inner Composite Entity, which itself goes through expansion, layer assembly, placement, and policy. The dependency graph is constructed across the full expansion — inner constituents can declare dependencies on outer constituents through the parent_composite hierarchy if visibility permits.

Compensation in nested composites runs bottom-up: the innermost composite compensates first, then its parent, and so on.

---

## 9. Scoring Model Integration

The Placement Engine's standard scoring applies to composite placements, with one adjustment: when a Composite Service registration is chosen as a candidate, its score is the worst score among the constituents it would dispatch (the bottleneck score). This prevents a Composite Service registration with one strong constituent and one weak one from being preferred over a single-resource provider that scores well on the actually-needed resource.

`self` constituents are scored as the registering provider's standard score for that resource type. `external` constituents are scored as the placement scores of the providers that would be selected — meaning composite scoring depends on the current Placement Engine state.

---

## 10. Composite Service Registration Contract

A Composite Service registration consists of:

```yaml
registration:
  catalog_ref: ApplicationStack.WebApp/v2
  composite_definition:
    composition_visibility: transparent | opaque | selective
    selective_visible:                # only when visibility = selective
      - vm
      - lb
    constituents:
      - component_id: vm
        resource_type: Compute.VirtualMachine
        provided_by: external
        depends_on: []
        required_for_delivery: required
      - ...
    max_nesting_depth: 3              # cap on this composite's nesting (≤3)
  metadata:
    description: "..."
    version: "2.0.0"
    standards_compliance: [...]
```

A registration is rejected if:
- The dependency graph contains a cycle
- A `depends_on` references an undeclared component_id
- A constituent references a resource type not in the Resource Type Registry
- `max_nesting_depth` exceeds 3
- Total constituent count exceeds the system limit (see profile policy)
- `selective_visible` references undeclared component_ids

Registration is otherwise validated like any other catalog item.

---

## 11. System Policies

| Policy | Rule |
|--------|------|
| `CMP-001` | A Composite Service's `self` constituents are dispatched using the standard Services API. The registering provider receives a standard constituent payload and returns a standard realized state. No special dispatch protocol exists for composite constituents. |
| `CMP-002` | Constituent execution ordering is derived from the `depends_on` declaration by DCM. The registering provider does not sequence constituent dispatch. |
| `CMP-003` | Parallelism in constituent execution is derived from the dependency graph. Constituents with no unresolved dependencies execute concurrently within DCM's standard pipeline. The registering provider does not manage this. |
| `CMP-004` | Composite status determination (`OPERATIONAL` / `DEGRADED` / `FAILED`) is performed by DCM based on constituent outcomes and `required_for_delivery` classifications. |
| `CMP-005` | Recovery Policy governs all constituent failure handling and compensation. The Composite Service definition does not make recovery decisions. The registering provider implements standard decommission handling for `self` constituents when a decommission payload arrives. |
| `CMP-006` | `provided_by: external` constituents are placed by the Placement Engine using standard placement rules. The Composite Service definition does not influence external constituent provider selection. |
| `CMP-007` | In transparent composition visibility mode, constituent entity UUIDs are `deterministic_uuid(parent_composite_uuid + component_id)` — stable across rehydration. |
| `CMP-008` | Maximum Composite Service nesting depth is 3, enforced by DCM at registration time and at placement time by checking the composite definition chain depth. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
