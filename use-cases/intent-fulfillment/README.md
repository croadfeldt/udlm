# intent-fulfillment — dependencies (with a nature) + a convergence window

Nine cases (7 expected-work, 2 must-reject) for the **intent-requirement** side of the
platform — what happens when a declared multi-resource intent cannot be fully satisfied at once.
Surfaced by a DAV fixture review (2026-07-27) and reduced by the maintainer to one insight:
**peer-atomicity is not a flag — it is a dependency of a different nature.** There is no `atomic`
flag and no best_effort/all_or_nothing axis; the whole model is **dependencies + a convergence
window**, extending the dependency concept the registry already ships.

The model, in one breath. A dependency edge carries a **nature**:

- **operational** — a Realized-layer coupling ("can't function without"): directional, cascades
  down the operational chain on failure, independents proceed. This is what today's
  `dependencies[].strength: hard|soft` describes.
- **request** — an Intent/Requested-layer coupling ("want these as a unit"): mutual-capable,
  binds at request time, so it yields BOTH atomic faces from one nature — **hold-all** activation
  and **cancel-all** on failure.

The **convergence window** `w` is the only other dial — `w=0` fail-fast, `w=N` converge-then-give-up,
`w=∞` defer — governing how long a **transient** member (converges when it can) may converge. A
**permanent** member is refused immediately regardless of `w`. A member blocked by a dependency
inherits the dependency's status transitively (transient→waits, permanent→refused,
cancelled→dependency-cancelled).

## The cases

- **Operational nature** (001, 002): a container operationally depends on a PVC. Transient PVC →
  container **blocked-transient**, waits, converges (001); permanently-refused PVC →
  **blocked-permanent** propagating up the chain to the app, surfaced together with the root (002).
- **Request nature** (003): ten request-coupled peer VMs — one unsatisfiable holds the whole unit
  (hold-all), and a permanent shortfall cancels the whole unit (cancel-all); both from one binding.
- **The distinction** (004): the same two members under an operational edge (directional cascade,
  independents proceed) versus a request edge (mutual, whole-unit) behave differently and
  legitimately — the nature is what differs.
- **The window** (005): the same transient member at `w=0` (fail-fast), `w=N` (converge-then-give-up),
  and `w=∞` (defer) — the sole converge-vs-fail-fast dial.
- **Soft never blocks** (006): a soft operational dependency (DNS) unrealized → the container
  converges degraded and surfaced, not blocked — the hard/soft strength read through the nature.
- **Persistence** (007): a blocked-transient member and its operational dependents converge later
  via reconciliation, no re-request, traceable to the original intent.
- **Surfacing is mandatory** (008, 009 — must-reject): a chain failure that names only the
  immediate member and not the root dependency + chain is refused (008); a silent partial
  expressed only as a missable field, with no warning, is refused (009). A field is not a signal.

## Grounding

`lifecycle_state` (Intent→Requested→Realized — where the request/operational natures bind),
ADR-011 (validate-and-reserve — the reservation-not-activation the request nature relies on), the
reconciliation loop (`reserve→recompute-dependents`), `dependencies[].strength` (hard|soft), and
`DEGRADED`/`partial_delivery` (provider-contract).

The **complete permutation matrix** these cases sample from — nature × member-status × window —
is enumerated in [`docs/design/intent-fulfillment-model.md`](../../docs/design/intent-fulfillment-model.md),
with a flow per case under [`docs/flows/`](../../docs/flows/README.md). Contracts here are proposed
pending the intent-fulfillment ADR; the corpus measures the decisions first.
