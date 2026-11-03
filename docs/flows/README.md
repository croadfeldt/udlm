# Flows — how the model composes into a working system

**What this settles:** the layer of documentation above definitions and contracts. A contract says
what one piece guarantees on its own. A **flow** says how the pieces run together, in order, to reach
one real outcome. Flows do not restate contracts. They sequence them and name the invariant each step
must uphold, so an engineer can implement the composition without reverse-engineering it from a dozen
decision records.

## The stage and the actors

A flow has two tellings, and this repo owns one of them.

- **UDLM sets the stage.** A UDLM flow defines the outcome in terms of the model: the abstractions in
  play, the four-state transitions, the contract obligations, and the invariant every phase must
  uphold. It names no provider and no engine. Any conformant implementation that performs the flow
  must honor these rules.
- **The control plane performs it.** An implementation's own flow tells the same story as a concrete
  performance: which components run, in what order, with what data. The example implementation (DCM,
  [croadfeldt/dcm](https://github.com/croadfeldt/dcm)) keeps those in its `docs/flows/`: a README,
  `request-realization.md` and one `uc-NN` flow per release use case.

Read the UDLM flow to learn what must be true and why. Read the implementation's flow to learn how it
is made true.

## Index

**[request-realization](request-realization.md) is the foundational flow.** It walks the whole model
end to end. Every other flow is lighter and builds on it: it assumes request-realization and refers to
the shared steps (assemble, place, enrich, reserve, converge) instead of re-explaining them. Read
request-realization first.

### The model's own lifecycles

| Flow | What it stages |
|---|---|
| [Lifecycle convergence](lifecycle-convergence.md) | The one loop beneath every entity: Intent versus Realized, a gap, and Converge closing it. Realize, reconcile, rehydrate and teardown are one act; archetypes and day-0/1/2 are parameters. |
| [Request implementation](request-realization.md) | An abstract, portable request becomes a provider-ready one, filled in and checked before anything is created. |
| [Provider lifecycle](provider-lifecycle.md) | The provider's side of the same story: register, declare what it needs, get dispatched, report realized state. |
| [Template assembly](template-assembly.md) | Pattern → Template → System. A reusable design becomes an orderable definition, which becomes a running instance. Two definitions related by `refines`, and one instance that carries the four states (ADR-033, Templates). |
| [Scoped-Class lifecycle](scoped-class-lifecycle.md) | A Class is authored, extended under the Liskov rule, compiled into the flat spec consumers read, and addressed. |
| [Estate observation](estate-observation-lifecycle.md) | How observed resources enter the model: normalize to the vocabulary, quarantine what is off-vocabulary, link into the graph. |

### Provisioning by family

| Flow | What it stages |
|---|---|
| [Compute provisioning](compute-provisioning-lifecycle.md) | A compute intent is placed on a provider whose declared capabilities meet its requirements floor. |
| [Container lifecycle](container-lifecycle-uniformity.md) | A container is a peer of a VM: same intent shape, same graph, same pipeline, on-prem or cloud. |
| [Storage provisioning](storage-provisioning-lifecycle.md) | Pool → dataset → volume or share, each link an operational dependency on the one below. |
| [Network provisioning](network-provisioning-lifecycle.md) | Segment → gateway → address services → allocation, with the subnet-overlap gate. |
| [Platform provisioning](platform-provisioning-lifecycle.md) | A hub provisions a namespace under a quota, backed by a node pool and a storage class. |
| [Application tier](application-tier-provisioning.md) | Package → image → service → database, through two admission gates. |
| [Log shipping](log-shipping-lifecycle.md) | A log store publishes its intake; one shipper per source binds it; a shipper that stops shipping is stale. |
| [Credential and identity](credential-and-identity-lifecycle.md) | A credential is a reference, resolved just in time and scope-checked; an identity escrow names what survives a recovery. |

### Operations and governance

| Flow | What it stages |
|---|---|
| [Automation migration and promotion](automation-migration-and-promotion.md) | Engines declare a shared process type. A green engine verifies against blue by typed-output diff. Cutover is a placement preference, and versions promote through stages like an application release. |
| [Change-control adoption](change-control-adoption.md) | A declared change policy branches on change class. Scheduling gates decide when; evidence gates decide whether. Waiting is typed, visible debt. Propagation is dependency-ordered and batch-verified. |
| [Storage-array maintenance with dependents](storage-array-maintenance-dr.md) | Disruptive maintenance on an array serving ten applications. The impact set comes from the graph, continuity clients cut over to DR first, and a failure halts resumably. |
| [Governed automation, end to end](governed-automation-end-to-end.md) | From a consumer's login to an audited result: visibility policy, validation, approval or window, a just-in-time credential, pre-flight, and post-run reconciliation. |
| [Secure software supply chain](secure-software-supply-chain.md) | A library or image update moves through blast radius, change window, policies, sign-off, lower-environment QA and a blue/green gate. |
| [Data mobility](data-mobility.md) | The data half of rehydration, migration and redeployment: the requirement is data, the mechanism is the provider's. |

**The 21 September-release use cases** are documented as flows here, each labeled by its use-case
number and built on request-realization. [by-persona.md](by-persona.md) groups them by the persona who
drives them. **UC-22 (governed automation)** extends the set: it governs an automation by its effect,
not just the artifact (inspect → govern → tenancy).

### Intent fulfillment — dependencies (with a nature) + a convergence window

One flow per case for the intent-requirement side: how a multi-resource intent behaves when it cannot
be fully satisfied at once. They stage the permutation matrix in
[`../design/intent-fulfillment-model.md`](../design/intent-fulfillment-model.md) (nature × member
status × window) and the corpus family
[`use-cases/intent-fulfillment/`](../../use-cases/intent-fulfillment/README.md).

| Flow | What it stages |
|---|---|
| [Operational dependency cascade](intent-fulfillment-operational-dependency-cascade.md) | container hard-depends on PVC; transient PVC → container blocked_transient, waits, converges; independents proceed; root surfaced |
| [Operational transitive refusal](intent-fulfillment-operational-transitive-refusal.md) | permanently-refused PVC → blocked_permanent propagates up the chain (container, app); one rooted refusal |
| [Request dependency, atomic](intent-fulfillment-request-dependency-atomic.md) | ten request-coupled peer VMs — hold-all until all can, cancel-all on permanent shortfall; both from one binding |
| [Request vs operational, the distinction](intent-fulfillment-request-vs-operational-distinction.md) | the same two members under an operational edge (directional) vs a request edge (mutual) — the nature is what differs |
| [The convergence window](intent-fulfillment-convergence-window.md) | the same transient member at `w=0` fail-fast, `w=N` converge-then-give-up, `w=∞` defer — the sole converge dial |
| [Soft operational does not block](intent-fulfillment-soft-operational-does-not-block.md) | soft DNS unrealized → container converges degraded, not blocked; strength is the switch |
| [Pending converges later](intent-fulfillment-pending-converges-later.md) | a blocked_transient member + operational dependents converge later via reconciliation, no re-request |
| [Surface names the root](intent-fulfillment-surface-names-root.md) (must-reject) | a chain failure naming only the proximate member, not the root + chain, is refused |
| [Surfacing is mandatory](intent-fulfillment-surfacing-mandatory.md) (must-reject) | a silent partial expressed only as a missable field, with no warning, is refused |

**Planned** (same shape): decommission and teardown ordering; dependency brokering (fulfillment by
the provider). Drift detection, reconcile and rehydration are delivered:
[uc-14](uc-14-drift-detection-remediation.md), [uc-10](uc-10-dynamic-rehydration.md) (dynamic) and
[uc-18](uc-18-provider-portable-rebuild.md) (provider-portable).

## The shape a flow follows

Each flow doc keeps this structure so the tier stays consistent:

1. **Thesis** — the outcome in one paragraph.
2. **The stage** — the model pieces the flow composes (by contract, with pointers, never restated).
3. **The sequence** — the phases in order; for each, what is true before and the invariant it upholds after.
4. **The invariants** — the stage rules any actor must obey, collected.
5. **What UDLM does not decide** — the seam handed to the control plane, with the pointer.
6. **Data · Policy · Provider** — the required decomposition lens (SPEC-DESIGN-REQUIREMENTS, hard constraint 29).
7. **Where each piece is specified** — a pointer table to the governing docs, spec, contracts and decision records.
