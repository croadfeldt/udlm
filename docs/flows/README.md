# Flows — how the model composes into a working system

**What this settles:** the layer of documentation **above definitions and contracts**. A contract says
*what one piece guarantees in isolation*; a **flow** says *how the pieces run together, in order, to
accomplish one real outcome* — so the composition is understood and implementable, not something an
engineer has to reverse-engineer out of a dozen ADRs. Flows do not restate contracts; they **sequence**
them and name the invariant each step must uphold.

## The stage and the actors

A flow has two tellings, and this repo owns one of them:

- **UDLM sets the stage.** The UDLM flow defines the outcome in terms of the *model*: the abstractions
  in play, the four-state transitions, the contract obligations, and the **invariant every phase must
  uphold** — provider-neutral and implementation-neutral. It is the script and the rules of the stage: *any*
  conformant implementation performing this flow must honor these, whatever engine it uses.
- **DCM is the actors creating the play.** The companion flow in
  [dcm-project/dcm `docs/flows/`](https://github.com/dcm-project/dcm/tree/main/docs/flows) tells the *same*
  flow as a concrete performance: which components run, in what sequence, with what data, and what an
  implementer must build. It performs the flow this repo stages.

Read the UDLM flow to understand *what must be true and why*; read the DCM flow to understand *how it is
made true*. Each UDLM flow links its DCM counterpart and vice versa.

## Index

| Flow | What it stages | DCM counterpart |
|---|---|---|
| [Lifecycle convergence](lifecycle-convergence.md) | The one loop beneath every entity — Intent vs Realized, a gap, and Converge closing it; realize/reconcile/rehydrate/teardown as one act, archetypes and day-0/1/2 as parameters | `docs/flows/lifecycle-convergence.md` |
| [Request implementation](request-realization.md) | An abstract, portable request becomes a provider-ready one — filled and validated before anything is created | `docs/flows/request-realization.md` |
| [Provider lifecycle](provider-lifecycle.md) | The provider's side of the same story — register, declare the inputs it needs (namespaces, storage classes, …), get dispatched, report realized state — so placement and enrichment have the data to fill a request | `docs/flows/provider-lifecycle.md` |
| [Template assembly](template-assembly.md) | Pattern → Template → System — a reusable design becomes an orderable definition becomes a running instance; two definitions related by `refines`, and one instance that carries the four states (ADR-033) | `docs/flows/template-assembly.md` |
| [Automation migration & promotion](automation-migration-and-promotion.md) | Automation moves like everything else — engines declare a shared process type, a green engine verifies against blue by typed-output diff, cutover is a placement preference, and versions promote through stages like an application release. |
| [Change-control adoption](change-control-adoption.md) | The calendar and ceremony around class adoption — a declared change policy branches on change class; scheduling gates decide when, evidence gates decide whether; waiting is typed, visible debt; propagation is dependency-ordered and batch-verified. |
| [Storage-array maintenance with dependents](storage-array-maintenance-dr.md) | Disruptive maintenance on an array serving ten applications — impact set derived from the graph, per-client tolerance policies split window-quiesce from DR cutover, the DR gate precedes scheduling, cutover is a re-bind on declared outputs, and failure halts resumably with DR still carrying the continuity clients. |

**[request-realization](request-realization.md) is the foundational flow** — it walks the whole model end
to end. Every other flow is intentionally **lighter and uses it as its base**: it assumes request-realization
and *references* the shared steps (assemble, place, enrich, reserve, converge) rather than re-explaining
them, so each use-case flow stays short and specific to what makes that case different. Read
request-realization first.

**The 21 September-release use cases** are documented as flows here, each
labeled by its Use Case number and built on request-realization. Grouped by persona in
**[by-persona.md](by-persona.md)** — the usage-by-role view. **UC-22 (governed automation)** extends the
set — governing an automation by its *effect*, not just the artifact (inspect → govern → tenancy).

### Intent fulfillment — dependencies (with a nature) + a convergence window

One flow per case for the intent-requirement side — how a multi-resource intent behaves when it
cannot be fully satisfied at once. They stage the permutation matrix in
[`../design/intent-fulfillment-model.md`](../design/intent-fulfillment-model.md) (nature ×
member-status × window) and the corpus family
[`use-cases/intent-fulfillment/`](../../use-cases/intent-fulfillment/README.md).

| Flow | What it stages |
|---|---|
| [Operational dependency cascade](intent-fulfillment-operational-dependency-cascade.md) | container hard-depends on PVC; transient PVC → container blocked-transient, waits, converges; independents proceed; root surfaced |
| [Operational transitive refusal](intent-fulfillment-operational-transitive-refusal.md) | permanently-refused PVC → blocked-permanent propagates up the chain (container, app); one rooted refusal |
| [Request dependency, atomic](intent-fulfillment-request-dependency-atomic.md) | ten request-coupled peer VMs — hold-all until all can, cancel-all on permanent shortfall; both from one binding |
| [Request vs operational, the distinction](intent-fulfillment-request-vs-operational-distinction.md) | the same two members under an operational edge (directional) vs a request edge (mutual) — the nature is what differs |
| [The convergence window](intent-fulfillment-convergence-window.md) | the same transient member at `w=0` fail-fast, `w=N` converge-then-give-up, `w=∞` defer — the sole converge dial |
| [Soft operational does not block](intent-fulfillment-soft-operational-does-not-block.md) | soft DNS unrealized → container converges degraded, not blocked; strength is the switch |
| [Pending converges later](intent-fulfillment-pending-converges-later.md) | a blocked-transient member + operational dependents converge later via reconciliation, no re-request |
| [Surface names the root](intent-fulfillment-surface-names-root.md) (must-reject) | a chain failure naming only the proximate member, not the root + chain, is refused |
| [Surfacing is mandatory](intent-fulfillment-surfacing-mandatory.md) (must-reject) | a silent partial expressed only as a missable field, with no warning, is refused |

**Planned** (same shape): decommission & teardown ordering · dependency brokering (fulfillment: provider).
Drift detection → reconcile and rehydration are delivered — [uc-14](uc-14-drift-detection-remediation.md),
[uc-10](uc-10-dynamic-rehydration.md) (dynamic) and [uc-18](uc-18-provider-portable-rebuild.md) (provider-portable).

## The shape a flow follows

Each flow doc keeps this structure so the tier stays consistent:

1. **Thesis** — the outcome in one paragraph.
2. **The stage** — the model pieces the flow composes (by contract, with pointers — never restated).
3. **The sequence** — the phases in order; for each, *what is true before* and *the invariant it upholds after*.
4. **The invariants** — the stage rules any actor must obey, collected.
5. **What UDLM does not decide** — the seam handed to DCM, with the pointer.
6. **Data · Policy · Provider** — the required decomposition lens (SPEC-DESIGN §29).
7. **Where each piece is specified** — a pointer table to the governing docs/spec/contracts/ADRs.
