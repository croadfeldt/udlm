# UDLM ADR-011: Validate-and-reserve — two-phase realization

**Status:** Proposed
**Date:** 2026-07-13
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-009 (dependency fulfillment — `fulfillment: provider` needs realize-time criteria, which reserve supplies without side effects — the cycle this ADR breaks); ADR-006 (convergence control model — the re-entrant loop the reserve phase runs *inside*); ADR-004 (provider capability declaration); DCM ADR-019 (placement — the orchestration side reserve was over-narrowed into, which this ADR does not re-import). **Mechanism lives in the contracts:** `contracts/provider-contract.md` §6a (reserve/commit/release verbs, TTL negotiation, `reservation.*` events); `foundations/four-states.md` §2.3a (the reserve-then-commit transition + reconciliation loop); `lifecycle/operational-models.md` §2, §5 (`reservation_reconcile_grace`/`budget`, `RESERVATION_*` triggers/actions).
**Tracking:** review of #70 — restoring, as a decision of record, how the original design broke the provider-mode chicken-and-egg.

## Context

`fulfillment: provider` (ADR-009) has a chicken-and-egg: a `Network.IPAddress`'s criteria need the VM's assigned port (a realize-time fact), but the VM needs the IP. ADR-009 as written resolves it by "partially realize the VM to get the port, then re-drive" — which **mutates live infrastructure mid-convergence** (a half-built VM exists before the graph is known good). That is the wrong shape.

Validate-and-reserve is the right shape and was in the original design, but it got scattered and narrowed. A `reserve_query_timeout` and a `reservation_hold_uuid` field survived, but the `trim` commit `2c48a44` (moving placement orchestration to DCM-runtime, correctly) demoted reserve to a **provider-selection** step and dropped the parts that are genuinely UDLM **wire contract**: the reserve/commit/release verbs, the hold object, and the whole-graph commit barrier. Placement's decision home is DCM ADR-019; reserve was left with no UDLM contract and no decision of record. This ADR restores the contract half without re-importing the orchestration DCM owns.

## Decision

**Realization is two-phase: RESERVE, then COMMIT. Nothing is built until the whole reserved graph validates.**

1. **Two phases with a commit barrier.** DCM **reserves** every target across the dependency graph — each reserve validates against the provider's capacity/identity/policy, **holds** the result, and returns a `reservation_hold_uuid` plus the provider's **computed realize-time facts**, with **no side effects**. The **reconciliation loop is relocated into reserve, not removed**: reserved facts feed each other (reserve the VM → yields its port → compute the IP criteria → reserve the IP), iterating to a fixed point over holds rather than built resources. At the **commit barrier**, DCM commits nothing until every hold is valid and mutually consistent and every applicable policy is green against the *fully reserved* graph. Only then does **commit** execute the holds in dependency order — the sole phase that mutates infrastructure. Any hold not committed is **released** (validation failure, cancellation, or TTL expiry). Transition mechanics: `foundations/four-states.md` §2.3a; the `reserve`/`commit`/`release` verbs, idempotency, and TTL negotiation: `contracts/provider-contract.md` §6a.

2. **This resolves the ADR-009 chicken-and-egg without side effects.** Brokered criteria are computed against *reserved* facts, so no half-built parent ever exists; abort is a hold-drop, not a teardown. The catalog `depends_on` graph stays acyclic (reserve is a distinct pass; "VM needs IP" is a commit-order fact, not a modeled edge), so cycle detection is unaffected. A genuine hard cycle surfaces as `RESERVE_QUERY_ALL_EXHAUSTED` / `DependencyCycle` and is denied, not looped.

3. **The reserve loop is bounded multi-round negotiation, with stalemate as a first-class terminal.** Reserving one dependency can shift another's criteria, so convergence takes real time and multiple rounds; a profile-governed reconcile budget (max rounds + wall-clock) caps it (ADR-006's bounded-convergence rule, over holds). Exhausting the budget with no fixed point terminates at **`RESERVATION_RECONCILE_STALEMATE`** — *distinct from* `RESERVE_QUERY_ALL_EXHAUSTED` (that is **no capacity**; this is **no agreement**) — releasing every hold and surfacing for re-plan or human negotiation. Budget and trigger/action mechanics: `lifecycle/operational-models.md` §2, §5.

4. **DCM backstops expiry — it never trusts the provider to self-report.** A provider MUST emit `reservation.expired`, but DCM tracks each hold's expiry independently and arms a separate watchdog (`reservation_reconcile_grace`); on a missed event it authors its own `reservation.expiry_unconfirmed` and fires a policy-governed `RELEASE_AND_NOTIFY_AFFECTED` to the delinquent provider and every affected holder. This dead-man's-switch satisfies ADR-006's terminal-state soundness rule for the reserve phase: a lapsed hold always resolves — by the provider's event or DCM's backstop, never by silence. Watchdog mechanics: `lifecycle/operational-models.md` §2.

## Options considered

- **(A) Partial-realize-then-re-drive (ADR-009 as written).** Rejected: mutates live infrastructure before the graph is validated; a half-built parent exists during convergence; compensation means tearing down real resources.
- **(B) Reserve as provider-selection only (the trimmed status quo).** Rejected: picks a provider but holds no cross-graph state, has no commit barrier, and cannot compute-and-validate `fulfillment: provider` criteria across the graph before building.
- **(C) [chosen] Two-phase reserve → barrier → commit**, with reserve/commit/release provider verbs and a first-class TTL'd hold. Validates the whole graph with zero side effects, computes realize-time criteria in the reserve phase, and makes abort a hold-drop.

## Formal basis (adopt-not-absorb)

This is not an invented protocol — it is TCC/2PC + lease, mapped onto the existing dispatch channel. **TCC (Try-Confirm-Cancel)** is the exact shape (Try=`reserve`, Confirm=`commit`, Cancel=`release`). **2PC**, formalized as **X/Open XA** and **ISO/IEC 10026 (OSI-TP)**, gives coordinator/participant + commit barrier (DCM coordinates; a provider that cannot hold votes no by failing reserve). The **lease** (**RFC 2131 (DHCP)**: OFFER=reserve, REQUEST/ACK=commit, lease-expiry=implied release) gives our TTL semantics. Per the standards-adoption methodology we **adopt the pattern and map it onto UDLM's REST dispatch with UDLM vocabulary** — we do **not** absorb a wire protocol (no XA C API, no WS-AtomicTransaction envelopes), since the provider contract already defines transport. Registered as `PATTERN` entries in `registry/standards-adoption-register.md`. SAGA (commit-then-compensate) is the contrast: reserve-first needs no compensation because nothing is built until the barrier passes.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data** — the reservation hold (`reservation_hold_uuid`, TTL, held capacity/identity, computed facts) recorded in the Requested-state resolution; commit writes Realized State; reserve produces no Realized record.
- **Policy** — re-evaluated as each hold lands and as the commit-barrier gate: the full reserved graph must pass before any commit. Denial at reserve re-enters the loop cheaply — nothing was built.
- **Provider** — implements `reserve` / `commit` / `release` and supplies the realize-time facts at reserve so brokered criteria are computed pre-commit.
- **Data scoping is preserved across the split.** Each verb is an ordinary governed DCM→Provider crossing carrying only the `role: execution` slice; the Governance Matrix fires at every crossing (`contracts/data-roles.md`; `PRV-008`; provider-contract §6a). The two-phase model adds request *types*, not new data-exposure paths.

## Consequences

- **+** `fulfillment: provider` is safe and side-effect-free: criteria computed against reserved facts, whole graph validated, *then* built.
- **+** The reconciliation loop is preserved, not removed — relocated into reserve, where each iteration moves holds. Same re-entrant ADR-006 loop, run over holds first and infrastructure only after the barrier.
- **+** Reconciliation is honestly modeled as bounded multi-round negotiation with a distinct stalemate terminal; a stalemate costs only dropped holds.
- **+** Abort is cheap (drop a hold); failed placements never leave orphans. Policy runs against the fully-reserved graph — "validate before we pull the trigger" is a modeled barrier.
- **+** Reconnects the orphaned `reserve_query` / `reservation_hold_uuid` machinery to a decision of record and a provider contract.
- **−** DCM must carry reconcile-loop state (round count, wall-clock, per-hold TTLs) and enforce a budget; granted TTLs and the budget must be mutually coherent, or a slow provider's hold expires before the barrier and manufactures a stalemate.
- **−** Providers implement three dispatch verbs, not one — mitigated by validate-only reserve for holdless targets (the two-phase floor still holds, the hold is empty).
- **Companion schema changes (tracked separately):** `compute.virtual-machine.json`'s typed `target_segment` output landed on #71 (VM spec 0.3.0); still follow-on are the `phase: dispatch | reserve` binding marker and reserve/commit/release advertisement in provider registration.
