# UDLM ADR-052: Intent fulfillment — dependency nature and the convergence window

**Status:** Proposed (croadfeldt upstream) — **0.1 work**; 1.0 is conferred by engineering
acceptance (#217), not declared here; decided 2026-07-27
**Date:** 2026-07-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** The design note this ratifies
(`docs/design/intent-fulfillment-model.md` — dependencies-with-a-nature + a convergence window,
plus the complete permutation matrix); the corpus that measures it
(`use-cases/intent-fulfillment/` — nine UCs, mirrored to dcm `dav/use-cases/hammer-intent-fulfillment/`);
the tenet this decision is the worked exemplar of (`design-principles/core-tenets.md` T7 —
*extend before net-new*); the reservation law the request nature stands on (ADR-011 —
validate-and-reserve); the edge the new attribute rides (`entities/service-dependencies.md`,
ADR-027 — `dependencies[].strength`); the derived-verdict pattern the status classification
copies (ADR-048 — staleness verdicts derived, never stored); and the boundary that splits this
decision between the two projects (ADR-008 — UDLM ships data + contracts, DCM operationalizes).

## Context

An intent names things to bring about. Some of those things cannot be realized the instant the
intent is accepted — a dependency is not ready, capacity is momentarily absent, a sibling in the
same request has not cleared policy. The platform needs a *ruled* answer to two questions, and it
had neither: **when a member cannot realize now, is it given up or is it allowed to converge?**
and **when members are coupled, does one member's fate bind the others?**

The first framings of this area multiplied mechanisms — a `best_effort` / `all_or_nothing` axis,
a separate three-outcome cancellation dial, an `atomic` flag on the request. Across the design
conversation every one of them dissolved into a single reduction: **peer-atomicity is not a flag
— it is a dependency of a different nature.** What remains is *dependencies (each carrying a
nature) + a convergence window*, and it is built by **extending the dependency edge the registry
already ships**, not by coining a parallel primitive. That reduction is the T7 exemplar now
recorded in the core tenets; this ADR is where it becomes contract.

The design note states the model and enumerates the complete permutation matrix; the nine-UC
corpus samples it and has been measured against the DAV engine (in-vocabulary, engine-schema
valid). Per corpus-first discipline the corpus preceded this ADR. The note deliberately left five
calls open "for the maintainer." This ADR makes them.

## Decision

### 1. The one new data point — `nature` on the dependency edge (extend, don't add)

A dependency edge carries a **`nature`**, one attribute on the *existing* `dependencies[]` edge —
**not** a second edge family, and **not** a parallel construct:

- **`operational`** — coupling at the **Realized** layer: *cannot function without* (a container
  needs its PVC). Directional. It binds when things run, so it propagates at realization and, on
  failure, cascades **down** the operational chain; members not on that chain proceed. This is the
  nature under which today's `dependencies[].strength: hard | soft` continues to mean exactly what
  it means now — `hard` operational blocks the dependent, `soft` operational lets it converge
  degraded. The nature names the **layer**; strength names the **blocking behavior** at that
  layer.
- **`request`** — coupling at the **Intent/Requested** layer: *I want these as a unit* (ten VMs
  all-or-none; a primary+replica that is only meaningful as a pair). It can be mutual, and it binds
  at request time — so it yields **both** atomic faces from one binding: held together until the
  whole unit is satisfiable (**hold-all** activation) and cancelled together on any member's
  permanent failure (**cancel-all**). `strength` does not apply to a request edge; the coupling is
  the unit itself.

**Placement is ruled: one attribute on the single existing edge.** Expressing request coupling as
a distinct Requested-layer edge alongside the operational edge was considered and rejected — it
reintroduces the parallel mechanism the reduction removed, and the layer the coupling binds at is
already recoverable from the nature. `nature` is the *only* new field this decision adds to the
portable model.

### 2. Convergence status is a **derived projection**, not a stored enum

The model speaks of seven convergence outcomes — `converging`, `blocked-transient`,
`blocked-permanent`, `dependency-cancelled`, `realized`, `refused`, `cancelled`. **These are the
verdict vocabulary of a derived classification, computed on read from signals the model already
carries — never a new stored status field.** This follows ADR-048 exactly (staleness verdicts are
derived, never stored) and keeps T3 intact (determinism is structural; no new mutable state to
police). The projection is a pure function of: `lifecycle_state` (Intent → Requested → Realized),
the satisfaction of each incoming dependency edge, whether an unsatisfiable member is **transient**
(can converge) or **permanent** (refused outright, regardless of window), and the window. A member
blocked by an unsatisfied dependency **inherits that dependency's verdict transitively** and the
block **cascades the chain** (PVC → container → app).

The seven values are **confirmed and complete**, and `cancelled` (a member the request itself gave
up) stays **distinct** from `dependency-cancelled` (a member cancelled *because* something it
depended on was) — the two carry different provenance, and the surfacing contract (§4) must name
the root, which collapsing them would erase.

### 3. The default window is **defer (converge)**; the give-up *bound* is DCM policy

The convergence window `w` is an intent field: `w=0` fail-fast, `w=N` converge-then-give-up,
`w=∞` defer. **When an intent does not state a window, the default is to converge (`defer`).** The
reasoning is the north star: converge-by-default removes toil — a transient blip self-heals with
no operator re-drive — and it is safe here specifically because **surfacing is mandatory (§4)**: a
deferring member is never silent; it reports `converging` / `blocked-transient` naming its root
dependency the entire time it waits. "Defer" is therefore *converge in the open*, not *hang in the
dark*. Fail-fast (`w=0`) remains available by explicit statement for intents that want it, and a
**profile may set a different default** for its domain.

Crucially, UDLM does **not** pick a wall-clock give-up bound. A time value in the portable data
would violate T3 (a magic number the model would have to police) and it is a runtime, per-provider
concern — so the *bound* on a `w=N` window is a **DCM policy**, exactly as the ADR-008 boundary
draws it. UDLM ships the window field and the qualitative default; DCM's policy decides how long
`N` is and what give-up executes.

### 4. The surfacing contract — name the root, always

An unsatisfiable intent MUST be **surfaced**, never left as a silent field. A field is not a
signal. The obligation, now fixed:

- A **transient** block surfaces as a **warning**; a **permanent** refusal surfaces as a
  **refusal-with-resolution**.
- Either surface MUST carry: **(a)** the **root** unsatisfied dependency (the deepest blocking
  node, not merely the immediate parent), **(b)** the **chain** from the affected entity to that
  root, **(c)** the **nature** of the blocking edge, and **(d)** the derived **verdict** (§2). A
  refusal MUST additionally carry **(e)** the **resolution** — what would unblock it.
- Reporting "container failed" without naming the PVC that is the actual root is **insufficient
  surfacing** and is a conformance finding (corpus UC-008). A silent partial — a status field with
  no warning — is **refused** (UC-009).

### 5. The request/operational mapping is **confirmed** — the load-bearing reduction

`request` = intent-layer atomicity (hold-all / cancel-all from a single binding); `operational` =
realized-layer functional coupling (directional cascade, independents proceed). This is the
reduction the entire model rests on, and it is ratified as stated. No `atomic` flag and no
`best_effort` / `all_or_nothing` axis exists anywhere in either project.

## The UDLM / DCM boundary (ADR-008)

| UDLM — data points + contracts | DCM — operationalize, via policies |
|---|---|
| the **`nature`** on the dependency edge (`request` \| `operational`) — the one new field | the reconciler walking the graph in convergence order (`reserve → recompute-dependents`, exists) |
| the hard/soft operational edges (`dependencies[].strength`, exist) | **policies** deciding the window *value* (`N`) and the cascade behavior (cascade-cancel vs hold-and-surface) |
| the **derived convergence-status** vocabulary (§2) and its computation from existing signals | the actual cancellation / rollback / cascade **execution** |
| the **propagation semantics** (operational cascades directionally; request couples the unit; soft never blocks) | evaluating the surfacing contract at runtime and emitting the warning / refusal |
| the **surfacing contract** (§4) + the **window** as an intent field with a `defer` default | reading the window/nature off the intent and driving convergence to them |

## Grounding — nothing here is a new mechanism (the T7 exemplar)

- **`lifecycle_state`.** The natures bind at different states: a request coupling holds at
  **Requested** (the readiness barrier), an operational coupling binds at **Realized** (functioning
  is a Realized-layer property). This is why request-atomicity is "held at Requested, activated to
  Realized as a unit."
- **ADR-011 (validate-and-reserve).** The request nature relies on **reservation being distinct
  from activation**: a held unit reserves members where it can, and no reservation activates until
  every member can — so an early-reserved member is never left running while its siblings are held.
- **The reconciliation loop.** Convergence is not new code — it is the existing
  `reserve → recompute-dependents` loop re-attempting a blocked-transient member and recomputing
  its dependents, carrying a `w>0` member from pending to realized.
- **`dependencies[].strength`** carries the operational block-vs-degrade behavior unchanged; the
  nature only names the layer above it.
- **`DEGRADED` / `partial_delivery`** (provider contract) expresses a soft-degraded realization and
  a surfaced partial — no new status invented.

## Consequences

- The portable model grows by exactly **one attribute** (`nature`) and **one intent field**
  (`window`, with a `defer` default). Everything else is derivation or existing surface.
- Convergence status adds **no stored state** — it is computed, so there is nothing new to keep
  consistent and nothing new for tamper-evidence to cover.
- DCM gains a clear, bounded job: read nature + window, drive the existing reconciler, and enforce
  the give-up bound and cascade as policy. No transaction-semantics assumption is baked into the
  substrate — the deliberate overrule the DAV precision fixture independently caught the analyzer
  making.
- The nine-UC corpus is the conformance surface for this ADR; the permutation matrix is its
  exhaustive reference. A UC that quarantines against a deployed engine is a corpus/model
  correction, not a silent gap.

## Status note — this is 0.1 work

Per the maintainer's ruling (2026-07-27), the current effort is **`udlm/0.1`**. **1.0 is not a
date the maintainer picks — it is conferred by engineering acceptance** (the ratification pass,
#217). This ADR is `Proposed` accordingly: the model is built, corpus-measured, and ready for that
review; it is not asserting a frozen 1.0 contract. See `registry/VERSIONING.md` § "Spec status".

## What this does not decide

The corpus and this ADR settle the *model*. They do not settle DCM's policy defaults (the `N`
value, the cascade-vs-hold choice per domain), which are DCM's by the boundary above; nor the
JSON-Schema shape of the `nature` attribute and window field on the dependency/intent envelopes,
which follows as an implementing PR against `entities/service-dependencies.md` once this ADR is
ratified.
