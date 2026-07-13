# UDLM ADR-011: Validate-and-reserve — two-phase realization

**Status:** Proposed
**Date:** 2026-07-13
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-006 (convergence control model — the re-entrant loop this two-phase realization runs *inside*); ADR-009 (dependency fulfillment — `fulfillment: provider` needs realize-time criteria, which reserve supplies without side effects); ADR-004 (provider capability declaration); `contracts/provider-contract.md` §6 (lifecycle verbs); `lifecycle/operational-models.md` §2 (the `reserve_query_timeout` + `RESERVE_QUERY_ALL_EXHAUSTED` machinery that survived); `entities/service-dependencies.md` §11 (`reservation_hold_uuid` in `placement.yaml`); `foundations/four-states.md` (Requested → Realized)
**Tracking:** review of #70 — resolving the chicken-and-egg in provider-mode fulfillment: a dependency's criteria derive from the parent's realize-time facts, but the parent needs the dependency. Validate-and-reserve is how the original design broke that cycle; this ADR restores it as a decision of record.

## Context

`fulfillment: provider` (ADR-009) has a chicken-and-egg: the `Network.IPAddress` criteria need the VM's assigned port (a realize-time fact), but the VM needs the IP. ADR-009 currently resolves it by "partially realize the VM to obtain the port, then re-drive" — which **mutates live state mid-convergence** (a half-built VM exists before the graph is known good). That is the wrong shape.

**Validate-and-reserve is the right shape, and it was in the original design — it got scattered.** The machinery still visible:

- `lifecycle/operational-models.md` §2 defines a **`reserve_query_timeout`** ("maximum time for a single provider to respond to a reserve query") and the `RESERVE_QUERY_ALL_EXHAUSTED` recovery trigger — so providers *are* reserve-queried before dispatch.
- `entities/service-dependencies.md` §11 records **`reserved_entity_uuid` + `reservation_hold_uuid`** per dependency in `placement.yaml` — so reservations were **held**.

But the concept was **narrowed and orphaned**. The `trim: move operational/runtime leaks out of UDLM (placement, caches, capacity)` change (commit `2c48a44`) correctly moved *placement orchestration* to DCM-runtime — and in doing so demoted reserve to a **provider-selection** step ("which provider can host"), dropping the parts that are genuinely UDLM **wire contract**: the **reserve/commit/release provider verbs**, the **reservation-hold object**, and the **whole-graph commit barrier**. Its home ADR (placement) was never written — ADR-006 references an ADR-019 that does not exist. So reserve survives as a timeout and a `placement.yaml` field with no contract and no decision of record. This ADR restores the contract half without re-importing the orchestration DCM correctly owns.

## Decision

**Realization is two-phase: RESERVE, then COMMIT. Nothing is built until the whole reserved graph validates.**

### 1. Two phases with a commit barrier

- **Phase 1 — RESERVE (validate + hold, no side effects).** DCM walks the dependency graph and issues a **reserve** to each target provider. A reserve **validates** the request against the provider's capacity/identity/policy and **holds** the result — capacity, an identity, an allocatable address — returning a **`reservation_hold_uuid`** and the **provider's computed realize-time facts** (the reserved placement's port, the reserved address). It **does not build**. Because reserve returns facts, `fulfillment: provider` criteria are computed here: the VM is *reserved* (yielding its port), the parent provider computes the IP criteria from that reserved port, and the IP is *reserved* on the reachable segment — all before anything is committed. Policy is evaluated **as each reservation lands** (ADR-006 re-entrant); reserve outcomes (including denial) re-enter the loop.
- **Commit barrier.** DCM commits **nothing** until **every** reservation in the effective graph is held-and-valid **and** every applicable policy (placement, governance-matrix, cycle, quota) is green against the **fully reserved** graph. This is "validate everything before we pull the trigger."
- **Phase 2 — COMMIT (execute the holds).** On a clean barrier, DCM issues **commit** per target in dependency order; each provider **executes its held reservation** and writes Realized State. Commit is the only phase that mutates infrastructure.
- **RELEASE (abort / expire).** Any held reservation not committed is **released** — on validation failure, consumer cancellation, or **hold-TTL expiry**. Release returns the held capacity/identity and is the compensation primitive for the reserve phase (no built resource to roll back — only holds to drop).

### 2. The reservation hold is a first-class, TTL'd object

A reservation hold (`reservation_hold_uuid`) is durable for the request cycle, carries a **TTL**, and is **idempotent**: re-issuing the same reserve returns the same hold, never a second one. Holds are recorded in the Requested-state resolution (`placement.yaml`, §11) so the whole reserved graph is auditable before commit. TTL expiry maps to the existing `RESERVE_QUERY_*` recovery triggers.

### 3. Provider verbs (provider-contract §6)

The base lifecycle floor (§1a item 4) splits `realize` into the two-phase pair and keeps the rest:

| Verb | Phase | Obligation |
|------|-------|------------|
| **`reserve`** | validate + hold | Validate the request; hold capacity/identity; return `reservation_hold_uuid` + computed realize-time facts. **No side effects.** MUST be idempotent. |
| **`commit`** | execute | Realize the held reservation; write Realized State. MUST be idempotent / re-entrant (re-drive-safe). |
| **`release`** | abort / expire | Drop the hold; return reserved capacity/identity. MUST be idempotent (releasing an already-released or expired hold is a no-op). |
| `converge` / `decommission` | (unchanged) | As today (ADR-006). |

A provider that cannot reserve (no capacity to hold, e.g. a purely idempotent config target) MAY implement `reserve` as a **validate-only** hold (validates + returns facts, holds nothing) and `commit` as its realize — the two-phase contract still holds; only the hold is empty.

### 4. This resolves the chicken-and-egg without side effects

The staged mutual dependency (ADR-009) resolves in the **reserve** phase: reserve the VM → it returns the reserved port → compute the IP criteria → reserve the IP → barrier validates the whole graph → **commit** VM and IP together. No half-built VM ever exists. The catalog `depends_on` graph stays acyclic (reserve is a distinct pass; the "VM needs IP" completion is a commit-order fact, not a modeled edge), so `graph-integrity.md` cycle detection is unaffected. A **genuine** hard cycle — where no reserve order yields the facts the next reserve needs — surfaces as `RESERVE_QUERY_ALL_EXHAUSTED` / `DependencyCycle` and is **denied**, not looped.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data** — the reservation hold (`reservation_hold_uuid`, TTL, held capacity/identity, computed facts) recorded in the Requested-state resolution; the commit writes Realized State. Reserve produces no Realized record.
- **Policy** — evaluated re-entrantly as each reservation lands, and as the **commit-barrier gate**: the full reserved graph must pass before any commit. Denial at reserve re-enters the loop (re-reserve elsewhere) — cheap, because nothing was built.
- **Provider** — implements `reserve` / `commit` / `release`; supplies the realize-time facts at reserve so brokered (`fulfillment: provider`) criteria are computed pre-commit.

## Options considered

- **(A) Partial-realize-then-re-drive (ADR-009 as written).** Rejected: mutates live infrastructure before the graph is validated; a half-built parent exists during convergence; compensation means tearing down real resources.
- **(B) Reserve as provider-selection only (the trimmed status quo).** Rejected: picks a provider but does not hold cross-graph state, has no commit barrier, and cannot compute-and-validate `fulfillment: provider` criteria across the graph before building.
- **(C) [chosen] Two-phase reserve → barrier → commit, with reserve/commit/release provider verbs and a first-class TTL'd hold.** Validates the whole graph with zero side effects, computes realize-time criteria in the reserve phase, and makes abort a hold-drop rather than a teardown.

## Consequences

- **+** `fulfillment: provider` is safe and side-effect-free: criteria are computed against reserved facts, the whole graph is validated, *then* built.
- **+** Abort is cheap — release a hold, no built resource to compensate. Failed placements never leave orphans.
- **+** Reconnects the orphaned `reserve_query`/`reservation_hold_uuid` machinery to a decision of record and a provider contract.
- **+** Policy runs against the fully-reserved graph before commit — "validate everything before we pull the trigger" is a modeled barrier, not an aspiration.
- **−** Providers now implement three dispatch verbs, not one. Mitigated: validate-only reserve for holdless targets keeps the floor low.
- **−** Reservation holds are stateful and TTL'd — DCM must expire and release them (bounded via the existing `RESERVE_QUERY_*` timeouts), and a provider's held capacity is briefly unavailable to others.
- **Companion schema changes (follow-on):** `compute.virtual-machine.json` gains a typed realize-time `placement` / `bound_port` output (so the reserved port is a declarable binding source); `catalog-item.schema.json` binding gains a `phase: dispatch | reserve` marker; provider registration advertises reserve/commit/release support. Tracked separately from this ADR.
