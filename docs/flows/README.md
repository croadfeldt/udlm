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
  uphold** — provider-neutral and realization-neutral. It is the script and the rules of the stage: *any*
  conformant realization performing this flow must honor these, whatever engine it uses.
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
| [Request realization](request-realization.md) | An abstract, portable request becomes a provider-ready one — filled and validated before anything is created | `docs/flows/request-realization.md` |
| [Provider lifecycle](provider-lifecycle.md) | The provider's side of the same story — register, declare the inputs it needs (namespaces, storage classes, …), get dispatched, report realized state — so placement and enrichment have the data to fill a request | `docs/flows/provider-lifecycle.md` |
| [Template assembly](template-assembly.md) | Pattern → Template → System — a reusable design becomes an orderable definition becomes a running instance; the assembly-scale projection of Intent → Requested → Realized (ADR-033) | `docs/flows/template-assembly.md` |

**[request-realization](request-realization.md) is the foundational flow** — it walks the whole model end
to end. Every other flow is intentionally **lighter and uses it as its base**: it assumes request-realization
and *references* the shared steps (assemble, place, enrich, reserve, converge) rather than re-explaining
them, so each use-case flow stays short and specific to what makes that case different. Read
request-realization first.

**The 21 September-release use cases** are documented as flows here, each
labeled by its Use Case number and built on request-realization. Grouped by persona in
**[by-persona.md](by-persona.md)** — the usage-by-role view.

**Planned** (same shape): decommission & teardown ordering · drift detection → reconcile · rehydration
(faithful / provider-portable) · dependency brokering (fulfillment: provider).

## The shape a flow follows

Each flow doc keeps this structure so the tier stays consistent:

1. **Thesis** — the outcome in one paragraph.
2. **The stage** — the model pieces the flow composes (by contract, with pointers — never restated).
3. **The sequence** — the phases in order; for each, *what is true before* and *the invariant it upholds after*.
4. **The invariants** — the stage rules any actor must obey, collected.
5. **What UDLM does not decide** — the seam handed to DCM, with the pointer.
6. **Data · Policy · Provider** — the required decomposition lens (SPEC-DESIGN §29).
7. **Where each piece is specified** — a pointer table to the governing contracts/ADRs.
