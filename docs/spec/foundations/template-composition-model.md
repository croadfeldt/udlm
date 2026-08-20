# UDLM — Template Composition Model

**Audience:** Architects, Service Provider implementers, Policy authors

> **A composited service offering is a Template.** This document is the composition mechanism of that
> one tier — what its constituents are, how they order, how data moves between them, how a failure is
> classified, and what a registration must satisfy. There is no separate "composite service" concept
> to hold alongside it.
>
> Template rather than Composite Service because *composite* describes the structure — a thing with
> parts — while the tier IS **a definition authored once and ordered many times**. Reusability is
> what distinguishes it from a one-off request, and only one of the two words carries it; "deploy a
> template" is also the settled reading in ARM, CloudFormation, Heat and TOSCA Service Template.
> Composite Service was considered and rejected as a second name for one function, because two names
> cost every reader the mapping between them.
>
> The prose below still says "Composite Service" in places, and the rule family is still `CMP-*`.
> Those are identifiers and wording, aligned under
> [#405](https://github.com/croadfeldt/udlm/issues/405); the tier they name is the one above.

> **Bindings are **output-resolved** — the validator checks each `bindings[].output` against the producer type's declared outputs (wave-3.2 deferral closed, wave 3.3). Machine-validatable schema:** Composite Service catalog items validate against
> [`registry/composition.schema.json`](../../../registry/composition.schema.json)
> (`registry/tools/validate.py` dispatches any instance carrying `record_type: class`
> to it, and additionally enforces the cross-field rules JSON Schema cannot express:
> component_id uniqueness, sibling depends_on/binding resolution, cycle rejection, and
> binding⊆depends_on ordering). Worked example:
> [`registry/classes/resource/template/application/acme-three-tier.yaml`](../../../registry/classes/resource/template/application/acme-three-tier.yaml).

> A Composite Service is a catalog item that delivers a composite payload — multiple constituent resource types, with declared dependencies and delivery requirements — through a single request. It is fulfilled by ordinary Service Providers (one or more), governed by ordinary control-plane policies, and produces a Composite Entity at runtime. There is no separate "meta provider" type. A Service Provider that registers a Composite Service simply declares the composition definition and fulfills the constituents whose `provided_by: self` flag points at it; everything else is the control plane's standard machinery.

---

## 1. What a Composite Service Is

### 1.1 The Core Model

A Composite Service is a **catalog-level definition** that declares:

1. A set of constituent resource types
2. Their dependencies on each other
3. Their delivery requirements (required, partial, optional)
4. Which provider fulfills each one

The control plane uses that declaration to:

1. **Select appropriate constituent providers** via the standard placement
2. **Determine execution order** from the dependency graph
3. **Govern rehydration sequence** using the same dependency information

A Service Provider that registers a Composite Service operates as a standard Service Provider for each constituent resource type it owns (those flagged `provided_by: self`). The control plane's standard machinery handles everything else: placement, sequencing, failure handling, compensation, and audit.

**A Composite Service is not an orchestrator.** Its definition does not:
- Select constituent providers — the placement does this
- Sequence execution rounds — the dependency graph informs the control plane's Orchestration Flow Policy
- Manage parallel execution — parallelism is derived from the dependency graph (resources with no unresolved dependencies execute simultaneously)
- Run compensation — the control plane's Recovery Policy executes compensation using the dependency graph in reverse
- Make routing decisions — these are control-plane policy decisions

### 1.2 Applications Are Composite Catalog Items

An "application" is modeled as a composition — constituents + dependency edges + bindings — not as a flat resource type. The application's structure (a database tier, an application tier bound to the database's connection output, a web tier bound to the application's endpoint) is exactly the constituent/`depends_on`/`bindings` declaration this document defines, and its provision/teardown ordering is the forward/reverse topological projection of those same edges (data-model-core §4). The worked example [`registry/classes/resource/template/application/acme-three-tier.yaml`](../../../registry/classes/resource/template/application/acme-three-tier.yaml) is a three-tier application expressed this way.

---

## 2. Composite Service Definition

A Composite Service registration declares a composite payload structure: which constituent resource types make up the service, how they relate, and who fulfills each one.

### 2.1 Constituent Declaration

**Owned or borrowed — `edge_type`.** A composite's constituent list holds two different things, and
until they are distinguished a reader cannot tell them apart:

- `contained_by` (the default) — the composite **creates and owns** this part. At realization it
  becomes an entry in the System's `constituents[]`, and `GRP-INV-002` makes it co-tenant with the
  composite, non-overridably.
- `binds_to` — the composite **uses** something that already exists and belongs to someone else: a
  stake in a shared VLAN, a platform namespace, an activity bound to the stack. At realization it
  becomes a `dependencies[]` edge carrying this edge_type, and it is how a relationship legitimately
  crosses a tenant boundary — behind a cross-tenant authorization (`CTX-001`).

The two fan out to different places on the realized record, which is why the declaration cannot be
left implicit: without it, a catalog item cannot state what the System is required to record.


Each constituent in the composition definition declares:

```yaml
constituents:
  - component_id: vm           # local identifier within this composite
    resource_type: Compute.VM
    provided_by: external      # placement selects the provider
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
- **`provided_by`** — Either `self` (the registering provider fulfills it) or `external` (placement selects a provider).
- **`depends_on`** — Component IDs whose realized state must exist before this constituent can be dispatched. The dependency graph is constructed from these declarations.
- **`required_for_delivery`** — See §2.4.

### 2.2 provided_by Declaration

Two values:

- **`self`** — The registering provider fulfills this constituent directly. At dispatch time, the control plane sends a standard constituent payload to this provider's standard Services API endpoint. The provider returns a standard realized state. There is no special "composite dispatch" protocol — the provider receives one constituent's payload, just as it would for any standalone request for that resource type.
- **`external`** — placement selects an eligible provider for this constituent at request time. Sovereignty filtering, accreditation checking, and trust scoring all apply normally. The Composite Service definition has no influence on this selection.

A single Composite Service can mix `self` and `external` constituents freely.

### 2.3 Dependency Graph

The control plane constructs a directed acyclic graph from the `depends_on` declarations. Constituents with no unresolved dependencies execute concurrently within the control plane's standard pipeline. Each dependency edge encodes that the source constituent's realized state must exist before the target constituent can be dispatched.

The dependency graph drives:
- **Forward execution** — constituent dispatch order during request fulfillment
- **Compensation order** — dependency-reverse during teardown
- **Rehydration order** — dependency-forward during rehydration
- **Decommission cascade** — dependency-reverse during decommission

The control plane detects cycles at registration time and rejects the composition definition.

### 2.4 required_for_delivery Classification

Each constituent declares how its failure affects the composite outcome:

- **`required`** — Failure halts the composite request and triggers compensation. Composite status becomes `FAILED`.
- **`partial`** — Failure is recorded but does not halt the composite. Composite status becomes `DEGRADED`. Whether DEGRADED is acceptable as a final state is a profile-level decision.
- **`optional`** — Failure is noted but ignored. Composite status reflects only required and partial constituents.

These classifications are evaluated by the control plane, not by the registering provider, when computing composite status from constituent outcomes.

### 2.4a Compensation Declaration (the one home)

Each constituent also declares its compensation behavior. This is the **single normative home** for the
declaration shape (`service-dependencies.md` §14 and `operational-models.md` §6.1 reference here); the runtime execution and failure handling live in `docs/spec/lifecycle/operational-models.md`
§6, governed by Recovery Policy (CMP-005).

```yaml
service_component:
  id: vm
  resource_type: Compute.VM
  required_for_delivery: <required|partial|optional>   # §2.4 — the one enum

  compensation_on_failure: <decommission_immediately|release_allocation|skip|notify>
  # decommission_immediately: decommission this component as part of rollback
  # release_allocation:       release allocation back to pool (for allocatable resources)
  # skip:                     do not compensate; used for partial-delivery components
  # notify:                   notify owner; human decides compensation

  compensation_order: <integer>
  # Compensation runs in REVERSE dependency order — the HIGHEST compensation_order
  # compensates first (last-provisioned is first-decommissioned). Reverse dependency
  # order is the default when not declared.

  depends_on: [<component_ids>]
```

```yaml
partial_delivery_policy:
  min_required_components: [vm, ip]   # composite DEGRADED if only these succeed
  degraded_is_acceptable: true
  auto_retry_optional_components:
    enabled: true
    max_attempts: 3
    interval: PT15M
    on_exhaustion: notify_owner
```

**Compensation semantics** (stated once): compensation executes in reverse dependency order, highest
`compensation_order` first; a compensation-step failure enters `COMPENSATION_FAILED` and triggers immediate
orphan detection (runtime detail: operational-models §6.3); `required_for_delivery: partial` constituents are
not compensation-triggering — their failure yields a `DEGRADED` composite (§2.4, CMP-004).

### 2.5 Interop — the control plane's catalog model

The field-by-field cross-walk to control-plane control plane's own catalog model lives with that control
plane: `dcm/docs/specifications/dcm-composite-orchestration.md`. Projection is lossless downward
(data-model-core §4) — a UDLM catalog item compiles onto their execution DAG; the reverse is lossy,
which is why the typed form is the data model and their DAG is a compiled artifact at the boundary.

---

## 3. Composite Entity — Four-State Representation

A Composite Service request produces a Composite Entity that exists across all four lifecycle states (Intent, Requested, Realized, Discovered) as a single entity with one UUID.

### 3.1 Intent State

Intent records the consumer's declared intent without expansion. The Composite Entity Intent record contains the catalog reference and the consumer-supplied parameters; constituents are not yet enumerated.

```yaml
# shape: Composite — derived (has_constituents, via the catalog definition's constituents)
catalog_ref: ApplicationStack.WebApp/v2
parameters:
  size: medium
  region: us-east-1
  domain: example.com
```

### 3.2 Requested State

Requested expands the intent: the control plane applies the Composite Service definition, runs the layer assembly to inject defaults and standards, applies all policies, resolves `external` placements, and produces the full constituent block.

```yaml
# shape: Composite — derived (has_constituents, from constituents[] below)
entity_uuid: <composite_uuid>
parent_composite_uuid: null
catalog_ref: ApplicationStack.WebApp/v2
constituents:
  - component_id: vm
    constituent_uuid: <vm_uuid>
    resource_type: Compute.VM
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

The Requested state is fully assembled before any constituent dispatch occurs. Constituent payloads do not contain references to dependencies' realized state — those are filled in at dispatch time via binding fields (see [request-dependency-graph.md](../lifecycle/request-dependency-graph.md)).

### 3.3 Realized State

Realized records the runtime outcome. As constituent dispatches return, their realized states are recorded against the corresponding component_id. The Composite Entity's coarse `lifecycle_state` stays the five-value enum (`Intent → Requested → Realized ↔ Discovered → Decommissioned`; data-model-core §3). Its **aggregate operational + compensation status** is carried as `status.conditions` — DEGRADED and the compensation states are condition types, **not** lifecycle states (data-model-core §3):

| Aggregate status condition | Meaning |
|---------------------------|---------|
| `OPERATIONAL` | All `required` constituents are operational. `partial` constituents are operational or accepted-degraded. |
| `DEGRADED` | All `required` constituents are operational but one or more `partial` constituents failed. Whether this is an acceptable resting condition depends on profile policy. |
| `FAILED` | One or more `required` constituents failed. Compensation has been triggered. |
| `COMPENSATING` | Recovery Policy is executing compensation (dependency-reverse decommission of successfully realized constituents). |
| `COMPENSATION_FAILED` | Compensation itself failed. Orphan detection is active for any constituents not cleanly torn down. |
| `PARTIALLY_COMPENSATED` | Compensation completed with one or more constituents that could not be torn down cleanly. |

Each constituent's individual `lifecycle_state` and `status` are also recorded and queryable via the standard request status endpoint and the SSE stream. The runtime status field surfaces both: top-level composite lifecycle_state + aggregate status conditions, plus per-constituent state.

### 3.4 Discovered State

Discovered State for a Composite Entity is derived: there is no provider-side "discover composite" call. Instead, each constituent's Discovered State is collected via that constituent's own provider, and the composite's Discovered State is the aggregate. Drift detection runs at two levels: per-constituent (standard provider drift detection) and composite-level (does the set of realized constituents still match the requested composition definition?).

---

## 4. What the control plane does with a composite

Expansion, placement of `external` constituents, dispatch sequencing, status computation,
compensation and audit aggregation are the control plane's, and are specified there:
`dcm/docs/specifications/dcm-composite-orchestration.md`. The registering provider's scope is
narrow by construction — it receives standard per-constituent calls and never sequences them.

This document defines what a composite IS. What a control plane does with one is that control
plane's (ADR-008).

---

## 5. Composition Visibility

A Composite Service registration declares its `composition_visibility`:

| Mode | Meaning |
|------|---------|
| `opaque` | Only the Composite Entity UUID is exposed to consumers. Constituent UUIDs exist internally for the control plane bookkeeping but are not surfaced. Status reporting reports composite-level state only. |
| `transparent` | All constituents are first-class control-plane entities with their own UUIDs, queryable individually. Constituent state is surfaced in status reporting. |
| `selective` | A declared subset of constituents are surfaced as control-plane entities; the remainder are opaque. Useful when some constituents are implementation detail and others are operationally relevant. |

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

A composite decommission triggers per-constituent decommission in dependency-reverse order. The control plane dispatches standard decommission calls to each constituent's provider (the registering provider for `self` constituents, the placed provider for `external` constituents). Decommission failures invoke standard Recovery Policy.

In transparent or selective mode, a constituent can be decommissioned independently of the composite, but only if the constituent's `required_for_delivery` is `optional`. Decommissioning a `required` constituent independently is rejected; the composite must be decommissioned as a whole.

---

## 6. Rehydration

Composite Entity rehydration follows the dependency graph in dependency-forward order, restoring constituents to their previously realized state.

### 6.1 Rehydration Sequence

For each constituent in dependency-forward order:

1. Resolve the constituent's provider:
   - `self` constituents: dispatched to the registering provider as it stands at rehydration time
   - `external` constituents: re-resolved via placement using the rehydration policy — `faithful`, `provider_portable`, `historical_exact` or `historical_portable` (§6.2)
2. Send the standard rehydration payload to the resolved provider
3. Record the resulting realized state

### 6.2 Rehydration Provider Selection

Which provider a rehydration call is sent to is **a policy decision, not a model default**. UDLM's
job is to make each choice expressible and to carry the answer; it ships no built-in decision, the
same line the drift ruling draws (ADR-060: policies dictate what happens, the substrate enables it).
A profile MAY bind a default, and an implementation MAY offer one — neither is stated here, because
a default in the spec would be one organisation's opinion shipped to every consumer.

The expressible set:

| Value | Which provider receives the call |
|---|---|
| `faithful` | the **same provider instance**. Unavailable means the rehydration fails rather than landing elsewhere |
| `provider_portable` | any provider of the **same provider type** — the original has been retired |
| `historical_exact` | the provider type recorded at **original placement**, read from the placement history rather than re-decided |
| `historical_portable` | any provider of that historical type, as a **hint** rather than a requirement |

Two things share the word "faithful" and are independent: `faithful` the *policy* (the same
instance) and the *Faithful mode* ([four-states](four-states.md) §5 — restore in place, UUID
preserved). A Provider-Portable rebuild can still select `historical_exact`.

**The composite-specific part** is that the choice is per constituent: one composite can hold its
database to the exact instance it had while letting stateless tiers land anywhere of the right type.
For `self` constituents the registering provider is dispatched to as it currently exists; if it has
changed, the constituent rehydrates against the current definition and any divergence surfaces as
ordinary drift.

---

## 7. Expansion — what a composite adds to the request pipeline

A composite request runs the standard pipeline ([request-realization](../../flows/request-realization.md))
with **one additional phase**, and that phase is the only part of it that is a data-model event:

**Expansion** — the definition is looked up and produces the constituent block. At this point the
**Requested state carries fully enumerated constituents and no dependency-resolved runtime values**.
That ordering is the model's, not an implementation's: a constituent's payload cannot carry a value
bound from a sibling that has not been realized, so those fields are filled at dispatch and not at
assembly. Everything downstream — layer assembly per constituent, placement of `external`
constituents, policy on the composite payload, dependency-forward dispatch, aggregation against
`component_id`, terminal resolution — is the standard pipeline applied constituent by constituent,
and is specified with it.

One consequence worth stating because it is a data rule rather than a sequencing choice: a policy
decision rejecting any constituent rejects the composite. There is no partial admission.

---

## 8. Nested Composite Services

A Composite Service can declare another Composite Service as a constituent, producing nested composites. **UDLM sets no nesting limit** — a ceiling is a governance choice, and an implementation declares one as policy if it wants one (rule 42). A three-tier application inside a platform stack inside an environment is three levels before anything unusual happens, which is why a model-side constant was the wrong home for it. Cycles are still refused: a composite that contains itself has no first step.

Nested composites are expanded recursively: the outer composite's expansion phase produces an inner Composite Entity, which itself goes through expansion, layer assembly, placement, and policy. The dependency graph is constructed across the full expansion — inner constituents can declare dependencies on outer constituents through the parent_composite hierarchy if visibility permits.

Compensation in nested composites runs bottom-up: the innermost composite compensates first, then its parent, and so on.

---

## 9. Scoring Model Integration

The only data-model-relevant rule for scoring a composite is the **bottleneck rule**: a composite candidate scores as its *weakest* constituent, so a composite with one strong and one weak constituent is not preferred over a single-resource provider that scores well on the actually-needed resource. How scores are computed — the placement scoring function, and the fact that an `external` constituent's contribution reflects current placement state — is implementation concern (see control-plane architecture documentation).

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
        resource_type: Compute.VM
        provided_by: external
        depends_on: []
        required_for_delivery: required
      - ...
  metadata:
    description: "..."
    version: "2.0.0"
    standards_compliance: [...]
```

A registration is rejected if any of the following holds. Two are defined here because they are
required nowhere else; the rest are consequences of rules that already exist and are cited, not
restated — one requirement, one definition.

| Rule | A registration is rejected if |
|---|---|
| `CMP-010` | A `depends_on` references an undeclared component_id. Ordering is derived from these edges (CMP-002), so an edge pointing at nothing leaves a constituent that can never become dispatchable — and it fails at expansion, long after the catalog accepted it. |
| `CMP-011` | A constituent references a resource type that resolves to neither a registered Class nor a flat resource type. Expansion has to compile the constituent against its type; a name resolving to nothing is a request that cannot be assembled, and the catalog is the last place it can be refused cheaply. |
| `CMP-012` | A constituent declares whether the composite OWNS it (`edge_type: contained_by`, the default) or merely USES it (`binds_to`). A constituent with `fulfillment: consumer` — the consumer supplying an existing resource — cannot be `contained_by`: a thing you were handed a reference to is not a thing you created. The distinction is structural rather than stylistic, because GRP-INV-002 is non-overridable — the parts of one thing may not span two owners — so a borrowed resource modelled as a part is either refused at realization or, worse, silently transfers ownership of something other tenants also use. |

Also rejected, by rules defined elsewhere:

- the dependency graph contains a cycle — ordering derives from `depends_on` (`CMP-002`), and a cycle has no first step
- a binding names an `output` the producing constituent's resource type does not declare (`CMP-009`)

Two further conditions are stated but **not currently enforced**, and are named here rather than
left to look like coverage: total constituent count exceeding the profile's limit (profile-governed,
so there is no single value to check against), and `selective_visible` referencing undeclared
component_ids.

Registration is otherwise validated like any other catalog item.

### 10.1 Admission is not the last check — bindings re-resolve at request time

The last rejection reason above is enforced today at admission, by the registry's
valid-by-construction gate (`registry/tools/validate.py` resolves every binding's `output`
against the producer type's declared output surface and names the declared alternatives when it
fails). That gate is necessary and it is not sufficient, for a reason that has nothing to do
with how well it is written: it ran *once*, against the state of the world on the day the
catalog item was admitted.

Two things move afterwards. A producer type is re-versioned, and an output the composite binds
against is removed or renamed — the catalog item that passed admission now names an output that
no longer exists, and no re-check is scheduled, because change-impact reporting in this model is
advisory by design and never rewrites an admitted artifact. Separately, a request may compose
items in a combination the catalog never checked together. In both cases the binding is invalid
at the moment it matters and valid according to the only gate that examined it.

So the resolution runs again against the *current* producer type version, as a stage of the
request pipeline (§7) — after expansion, before policy and dispatch, while the request is still
data. This placement is the point: a binding caught here costs a rejected request, whereas the
same binding caught at dispatch costs a partially realized composite and a compensation path.
Nothing is provisioned, so nothing is rolled back.

The refusal reuses the admission gate's message contract — it names the producer type, the
requested output, and the outputs the type actually declares — and is typed
`validation.binding_undeclared_output`, a binding-contract violation distinct from a policy
denial and from a provider failure. The declared output surface is cited as the authority for
the decision, because it is the authority: typed outputs are the type's referenceable binding
surface, and a binding names a declared output rather than guessing at a string. The rule is
`CMP-009`.

One consequence worth stating plainly, because it looks like an inconsistency and is not: this
means a catalog item can be admitted and later become unrequestable without anything having
been done to it. That is correct. The alternative — silently rewriting admitted items when a
producer re-versions — would make the catalog's contents depend on when they were last read.

---

## 11. System Policies

| Policy | Rule |
|--------|------|
| `CMP-001` | A Composite Service's `self` constituents are dispatched using the standard Services API. The registering provider receives a standard constituent payload and returns a standard realized state. No special dispatch protocol exists for composite constituents. |
| `CMP-002` | Constituent execution ordering is derived from the `depends_on` declaration by the control plane. The registering provider does not sequence constituent dispatch. |
| `CMP-003` | Parallelism in constituent execution is derived from the dependency graph. Constituents with no unresolved dependencies execute concurrently within the control plane's standard pipeline. The registering provider does not manage this. |
| `CMP-004` | Composite status determination (`OPERATIONAL` / `DEGRADED` / `FAILED`) is performed by the control plane based on constituent outcomes and `required_for_delivery` classifications. |
| `CMP-005` | Recovery Policy governs all constituent failure handling and compensation. The Composite Service definition does not make recovery decisions. The registering provider implements standard decommission handling for `self` constituents when a decommission payload arrives. |
| `CMP-006` | `provided_by: external` constituents are placed by the placement using standard placement rules. The Composite Service definition does not influence external constituent provider selection. |
| `CMP-007` | In transparent composition visibility mode, constituent entity UUIDs are `deterministic_uuid(parent_composite_uuid + component_id)` — stable across rehydration. |
| `CMP-009` | Constituent bindings are re-resolved against the producing type's **current** declared output surface at request validation, not only at catalog admission — so a producer re-versioned after admission, or a composition the catalog never checked together, still refuses. The check runs after expansion and before policy and dispatch (§7), so no constituent is provisioned and no compensation is needed. The refusal is emitted as `validation.binding_undeclared_output` and names the producer type, the requested output, and the outputs that type declares; the declared output surface is cited as the authority. A producer type absent from the registry is a refusal, not a skip — an unresolvable producer cannot be shown to declare anything. The refusal's audit record names the catalog item, the failing constituent, and the undeclared output as subjects (`AUD-024`) — stated here so an implementer working from this rule alone carries all three, not only the producer surface. |
| `CMP-013` | A consumer MUST be able to learn, **before ordering**, that a composition contains parts they would not be able to read once realized. The model carries the fact — `composition.unreadable_constituents`, the component_ids unreadable to THIS actor over THIS placement — and the decision is policy's: a catalog may withhold the item, mark it unorderable, or offer it anyway. UDLM picks none of those (rule 42). Where a policy refuses, the refusal NAMES the unreadable parts: "denied" alone tells a consumer nothing they can act on, whereas naming the database tells them exactly which access to request. Evaluated at catalog render and again at request validation — the CMP-009 placement, before dispatch, so nothing is provisioned and no compensation is needed. **`composition_visibility` does not cover this**: it declares ADDRESSABILITY — whether a part has an identity you could refer to — and a part can be fully addressable and still unreadable to you, because access is decided by the grouping it lands in. Real visibility is addressability AND access. *Conformance target: `runtime`* — it binds a live catalog and a live evaluation pass, so no in-repo artifact can test it; the artifact half is the fact's existence in the governed vocabulary (PFACT-001).

---

*Part of the UDLM specification. For contributions see [CONTRIBUTING.md](../../../CONTRIBUTING.md).*
