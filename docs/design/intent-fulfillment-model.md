# Intent fulfillment — dependencies (with a nature) + a convergence window

**What this settles:** how a declared multi-resource intent behaves when it cannot be fully
satisfied at once — which members realize, what happens to the ones that cannot, and what the
consumer is told. A DAV fixture review surfaced the question; across a design conversation the
maintainer reduced it to one insight: **peer-atomicity is not a flag — it is a dependency of a
different nature.** The earlier framings (best_effort / all_or_nothing, a three-outcome
cancellation axis, an `atomic` flag) all dissolved into it. The whole model is therefore
**dependencies + a convergence window** — it extends the dependency concept the registry already
ships (`dependencies[].strength`, the reconciliation loop) rather than adding a parallel
mechanism. This note is the reference; the corpus family `use-cases/intent-fulfillment/` samples
the matrix below, and a flow per case lives under [`docs/flows/`](../flows/README.md). The
intent-fulfillment ADR follows the corpus — the ruling surface is named at the end; nothing here
is Accepted.

## The two knobs

A dependency edge carries a **nature**:

- **operational** — a coupling at the **Realized** layer: "can't function without" (a container
  needs its PVC). It is **directional**. On failure it cascades down the directional operational
  chain; members independent of that chain proceed. This is exactly what today's
  `dependencies[].strength: hard|soft` already describes — the nature names the layer the coupling
  binds at, and `strength` says whether an unsatisfied operational edge blocks (hard) or merely
  degrades (soft).
- **request** — a coupling at the **Intent/Requested** layer: "I want these as a unit" (ten VMs
  all-or-none; a primary and its replica for one HA requirement). It can be **mutual**. It binds
  at **request time**, and that single binding yields both atomic faces for free: the unit is
  **held together** until every member is satisfiable (hold-all activation) and **cancelled
  together** if any member cannot be (cancel-all). No `atomic` flag is needed — atomicity is what a
  request-nature edge *is*.

The **convergence window** `w` is the only other dial: how long a member that cannot realize now
is allowed to converge before it is given up. `w=0` is fail-fast, `w=N` is
converge-then-give-up, `w=∞` is defer indefinitely. The window is the **sole**
converge-versus-fail-fast control.

The window governs **transient** members only. A member's **status** is orthogonal to the window:

- **transient** — cannot realize now for a reason that may clear (no capacity yet); it converges
  when it can, bounded by `w`.
- **permanent** — cannot realize at all unless the intent changes (a policy violation); it is
  **refused immediately, regardless of `w`**. Waiting cannot help, so the window is inert.

A member **blocked by a dependency** inherits the dependency's status **transitively**:
transient → waits (blocked-transient), permanent → refused (blocked-permanent),
cancelled → dependency-cancelled. That inheritance is what makes a chain behave coherently:
the root's status flows down the operational chain, and the request nature couples the unit.

### The convergence-status classification

Every member carries one of a closed set of statuses — this vocabulary is the data point UDLM
owns; DCM drives entities through it:

| Status | Meaning |
|---|---|
| `realized` | the member is live (Realized) |
| `converging` | actively being (re)attempted by the reconciliation loop |
| `blocked-transient` | held, waiting on a transiently-unsatisfied dependency; converges when it clears |
| `blocked-permanent` | refused because a dependency is permanently refused (inherited) |
| `refused` | permanently unrealizable under the current intent (needs an intent change) |
| `dependency-cancelled` | given up because a dependency it required was given up / cancelled |
| `cancelled` | given up as part of a request-unit cancel-all, or a fail-fast give-up at `w=0` |

## The complete permutation matrix

Every combination of **nature** {operational, request-mutual, soft} × **member status**
{transient, permanent} × **window** {`w=0`, `w=N`, `w=∞`} — eighteen cells. The running
illustration: an **operational** case is a container that depends on a PVC (and an app above the
container); a **request** case is ten peer VMs coupled as a unit; a **soft** case is a container
that soft-depends on DNS. In each cell, the *affected member* is the one that cannot realize now
(the dependency target, or the coupled peer). Each cell states **(realized members | affected
member fate | consumer surface)** and the corpus UC that exercises it — every cell is either
authored directly or an **explicit derivation** of another (permanence makes the window inert;
a soft dependent's fate is window-invariant), so no cell is unmapped.

### operational nature (directional; independents proceed)

| Status × window | Realized members | Affected member fate | Consumer surface | Corpus |
|---|---|---|---|---|
| transient · `w=0` | independents only | PVC given up now (fail-fast); container **dependency-cancelled** | refusal-with-resolution naming the PVC (given up at `w=0`) + the cancelled container | UC-005 (`w=0` arm) |
| transient · `w=N` | all, if the PVC converges within `N`; else independents only | PVC **blocked-transient** → realized, or given up at window expiry; container waits → proceeds, or dependency-cancelled | warning naming the PVC + expected resolution; escalates to refusal if the window expires | UC-001, UC-005 (`w=N` arm) |
| transient · `w=∞` | independents now; PVC + container on convergence | PVC **blocked-transient** (pending); container **blocked-transient** (inherited) | warning naming the root PVC + the chain, "will converge" | UC-001, UC-007, UC-005 (`w=∞` arm) |
| permanent · `w=0` | independents only | PVC **refused**; container **blocked-permanent**; app **blocked-permanent** (chain) | refusal-with-resolution naming the **root** PVC + its rule + the chain | UC-002 |
| permanent · `w=N` | independents only | identical to `w=0` — permanence makes the window inert | refusal-with-resolution, root + chain | derivation of permanent · `w=0` (UC-002) |
| permanent · `w=∞` | independents only | identical to `w=0` — refused immediately, never held | refusal-with-resolution, root + chain | derivation of permanent · `w=0` (UC-002) |

### request-mutual nature (binds at request time; hold-all up / cancel-all down)

| Status × window | Realized members | Affected member fate | Consumer surface | Corpus |
|---|---|---|---|---|
| transient · `w=0` | none | whole unit **cancelled** now (cancel-all); blocking peer given up | refusal-with-resolution naming the peer + the request coupling | UC-003 (cancel arm), UC-005 |
| transient · `w=N` | all atomically, if the peer converges within `N`; else none | unit **held** (hold-all) → all activate; or cancel-all at window expiry | warning: unit held, names the blocking peer; escalates to cancel-all refusal on expiry | UC-003 (hold arm), UC-005 |
| transient · `w=∞` | none until convergence, then all atomically | unit **held** (hold-all) indefinitely | warning: unit held, names the peer | UC-003, UC-007 (request-unit derivation) |
| permanent · `w=0` | none | whole unit **cancelled** (cancel-all); peer **refused** | refusal-with-resolution naming the peer + that the coupling cancels the unit | UC-003 (permanent cancel-all) |
| permanent · `w=N` | none | identical to `w=0` — permanence makes the window inert | refusal-with-resolution, peer + coupling | derivation of permanent · `w=0` (UC-003) |
| permanent · `w=∞` | none | identical to `w=0` — cancelled immediately, never held | refusal-with-resolution, peer + coupling | derivation of permanent · `w=0` (UC-003) |

### soft nature (operational-soft; the dependent never blocks)

A soft operational dependency never gates its dependent, so the **container's** fate is
window-invariant — it converges **degraded** in every cell. Only the **soft target's** own fate
(DNS) varies, and it varies exactly as an operational-transient / permanent member would (the rows
above). The window is therefore inert for the dependent.

| Status × window | Realized members | Affected member fate | Consumer surface | Corpus |
|---|---|---|---|---|
| transient · `w=0` | container (degraded) + independents | container **realized-degraded**; DNS given up per its own `w` | warning: container degraded, DNS unrealized, reduced capability | UC-006 |
| transient · `w=N` | container (degraded) + independents | container **realized-degraded** (heals if DNS converges); DNS blocked-transient | warning: container degraded; clears if DNS converges | derivation of soft transient · `w=0` (UC-006) + DNS follows operational-transient |
| transient · `w=∞` | container (degraded) + independents | container **realized-degraded**; DNS pending | warning: container degraded, DNS pending | derivation of soft transient · `w=0` (UC-006) |
| permanent · `w=0` | container (degraded) + independents | container **realized-degraded** (permanently); DNS **refused** | warning: container permanently degraded, DNS refused with reason | UC-006 (permanent derivation) |
| permanent · `w=N` | container (degraded) + independents | identical — soft never blocks, window inert | warning: permanently degraded | derivation of soft permanent · `w=0` (UC-006) |
| permanent · `w=∞` | container (degraded) + independents | identical — soft never blocks, window inert | warning: permanently degraded | derivation of soft permanent · `w=0` (UC-006) |

### What the matrix shows

Three readings fall straight out of it:

- **The window collapses under permanence.** Six of the eighteen cells (every permanent row at
  `w=N` and `w=∞`) are identical to their `w=0` sibling: a permanent member is refused immediately,
  so the converge-versus-fail-fast dial has nothing to act on. The window is a **transient-member**
  control.
- **Soft collapses the dependent's fate.** A soft edge never blocks, so the dependent converges
  degraded across all six soft cells; only the soft target's own fate moves, and it moves as an
  ordinary operational member. Six more cells are derivations for that reason.
- **The two must-reject cases are surface-column constraints, not cells.** UC-008
  (`surface-names-root`) and UC-009 (`surfacing-mandatory`) do not occupy a single cell — they
  assert what the **consumer surface** column must contain in *every* cell: a warning (transient)
  or a refusal-with-resolution (permanent) that names the **root** unsatisfied dependency and the
  chain, never a silent field and never only the proximate member. They gate the whole matrix.

Counting: **eighteen cells, zero unmapped** — ten exercised directly by an authored UC arm
(UC-001/002/003/005/006/007 across their `w` variants), eight explicit derivations (the six
window-inert permanent repeats plus the soft dependent-invariance repeats), and the surfacing
contract (UC-008/009) constraining every cell's surface column.

## Grounding in the existing model

Nothing above is a new mechanism; each piece names an existing surface:

- **`lifecycle_state` (Intent → Requested → Realized).** The natures bind at different states:
  a **request** coupling binds at Requested (the readiness barrier is a hold at Requested), an
  **operational** coupling binds at Realized (it is about functioning, which is a Realized-layer
  property). This is why request-atomicity is "held at Requested, activated to Realized as a unit."
- **ADR-011 (validate-and-reserve).** The request nature relies on **reservation being distinct
  from activation**: a held unit reserves each member where it can, and no reservation becomes an
  activation until every member can activate — so a member that reserved early is never left running
  while its siblings are held.
- **The reconciliation loop (`reserve → recompute-dependents`).** Convergence is not new code — it
  is the existing loop re-attempting a blocked-transient member and recomputing its dependents,
  which is what carries a `w>0` member from pending to realized and cascades a status change down
  the chain.
- **`dependencies[].strength: hard | soft`.** The operational nature's block-versus-degrade
  behavior *is* strength: hard operational blocks the dependent; soft operational lets it converge
  degraded. The nature names the layer; strength names the blocking behavior at that layer.
- **`DEGRADED` / `partial_delivery` (provider-contract).** A soft-degraded realization and a
  surfaced partial are expressed through the provider contract's existing degraded/partial vocabulary,
  not a new status.

## The UDLM / DCM boundary (ADR-008)

The single new data point UDLM adds is the **nature** on the dependency edge. Everything else
UDLM contributes is vocabulary and contract; the mechanics are DCM's.

| UDLM — the data points + contracts | DCM — operationalize, via policies |
|---|---|
| the **nature** on the dependency edge (`request` \| `operational`) — the ONE new field | the reconciler walking the graph + convergence order (`reserve → recompute-dependents`, exists) |
| the hard/soft dependency edges (`dependencies[].strength`, exist) | **policies** deciding the window value and the cascade behavior (cascade-cancel vs hold-and-surface) |
| the **convergence-status classification** {converging, blocked-transient, blocked-permanent, dependency-cancelled, realized, refused, cancelled} | the actual cancellation / rollback / cascade execution |
| the **propagation semantics** (operational cascades directionally; request couples the unit; soft never blocks) | evaluating the surfacing contract at runtime, emitting the warning / refusal |
| the **surfacing contract** (name the root dependency + the chain) + the **window** as an intent field | reading the window/nature off the intent and driving convergence to them |

UDLM defines the vocabulary of states and how they flow; DCM's policies decide what to do when a
chain cannot converge. No `atomic` flag and no best_effort/all_or_nothing axis exists anywhere in
either half.

## The ruling surface for the ADR (open — the maintainer decides)

The corpus measures the model; these calls are deliberately **not** made here:

- **The default window.** What `w` is when the intent does not state one (fail-fast, a bounded
  default, or defer) — a safety-versus-liveness default the profiles may set differently.
- **The placement of `nature` on the edge.** One attribute on a single edge, or edges expressed at
  both layers (a Requested-layer request edge distinct from a Realized-layer operational edge) —
  the data-model shape of the one new field.
- **The convergence-status enum.** Confirmation of the seven-value set above (names and
  completeness), and whether `cancelled` and `dependency-cancelled` stay distinct.
- **The surfacing contract's exact obligation.** The precise required content of a warning versus a
  refusal-with-resolution (UC-008/009 assert root-and-chain; the ADR fixes the shape).
- **The request/operational mapping itself.** Confirmation that request = intent-layer atomicity
  (hold-all/cancel-all from one binding) and operational = realized-layer functional coupling
  (directional cascade, independents proceed) — the load-bearing reduction this whole note rests on.

## Where each piece is specified

| Piece | Home |
|---|---|
| The corpus (the eighteen cells sampled) | [`use-cases/intent-fulfillment/`](../../use-cases/intent-fulfillment/README.md) |
| A flow per case | [`docs/flows/`](../flows/README.md) (intent-fulfillment entries) |
| Reservation-not-activation | ADR-011 (validate-and-reserve) |
| Edge model (`strength`, `edge_type`) | `entities/service-dependencies.md`, ADR-027 |
| Degraded / partial delivery | `contracts/provider-contract.md` (`DEGRADED`, `partial_delivery`) |
| The nature field + statuses + windows | proposed — the intent-fulfillment ADR (pending ruling) |
