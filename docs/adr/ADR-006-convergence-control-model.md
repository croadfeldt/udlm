# UDLM ADR-006: Convergence control model — event-condition-action, re-entrant policy

**Status:** Proposed
**Date:** 2026-07-10
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `foundations/foundations.md` §1 (the Data·Policy·Provider runtime loop this specifies); ADR-005 (causal audit — the triggers are the causal edges); `contracts/event-catalog.md`; `contracts/policy-contract.md`; `contracts/provider-contract.md` (provider callback); the DCM convergence engine (loop runner); UCs `idempotent-reconvergence`, `drift-detection-remediation`, dependency-failure-surfaced, `vm-provision-with-provider-failure`
**Tracking:** review of udlm #16 — "Data·Policy·Provider: peers or a sequence?" and "does policy re-run when a provider changes or denies a request?"

## Context

`foundations.md` presents Data·Policy·Provider as three peer abstractions connected by a runtime loop. Reviewers read the diagram two ways: as **no order at all** (a defect — "how does it actually run?") or as a **strict pipeline** Data→Policy→Provider (too rigid — it can't express a provider changing or denying a request, or drift, re-triggering policy). Neither is right, and the contract never stated the loop's actual semantics: what triggers a stage, that **policy is re-entrant**, and the guarantees that keep the loop from oscillating.

## Decision

**1. Peers in decomposition; a trigger-driven control loop at runtime.**
Data·Policy·Provider are **peers** — no fixed importance order (the decomposition lens, ADR-002). At runtime they form an **event-condition-action (ECA) control loop**, not a pipeline. Each stage has **entry conditions** (a trigger fires it) and emits a **completion/validation signal** (which triggers the next stage). There *is* a primary direction — request → policy → provider — but it is a **loop, not a one-way flow**.

**2. Policy is re-entrant.**
A provider **acting, changing, or denying** a request — and drift, and any other Data state change — is an **Event** that re-triggers policy evaluation. Policy is never a one-shot gate: it is re-evaluated on every provider outcome and every state change. Provider denial is not a dead-end; it re-enters the loop (re-plan, alternative placement, or surface a failure).

**3. Soundness rules (MUST).** A re-entrant loop is only safe if it converges:
- **Bounded convergence** — retries are bounded with backoff, and there is a **terminal state that surfaces the failure** (the dependency-failure-surfaced UC). The loop MUST converge to the target state or terminate visibly; it MUST NOT oscillate indefinitely (deny → retry → deny …).
- **Idempotent re-entry** — re-triggered policy evaluation and re-entrant convergence MUST be idempotent; re-evaluating against unchanged state MUST NOT double-apply.
- **Causal audit of triggers** — every `trigger → stage → signal` transition is an audit event carrying *why* it fired. The triggers are the causal edges of the audit DAG (ADR-005); the loop's history is fully reconstructible.

**4. Homes in the existing model.** This is the substrate framing; it names what is already implied: the **four-state lifecycle** is the state machine (the stages), the **convergence engine** (DCM) is the loop runner, **events** are the triggers, and the **provider callback** is the provider→policy feedback edge.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data** — the Events (state changes), the guard conditions and completion signals, and the audit records of every transition (with causal references).
- **Policy** — the re-entrant evaluation; the definition of guards/triggers; the convergence/termination decision (retry, re-plan, or surface failure).
- **Provider** — the actor whose acting/change/**denial** emits the feedback Events; the callback carrying the outcome that re-triggers policy.

## Options considered

- **(A) Strict pipeline Data→Policy→Provider.** Rejected: cannot express re-evaluation on provider change/denial or drift; a one-way flow can't model convergence.
- **(B) Peers with no stated runtime order.** Rejected: leaves "how does it run" unspecified — the reviewer's complaint is valid there.
- **(C) [chosen] Peers in a re-entrant, trigger-driven (ECA) control loop with soundness rules.** Directional but looping; one model covers request, drift, denial, failure, and rehydration.

## Consequences

- **+** One model covers request, drift, provider denial, failure, and rehydration — all are the same loop re-entering. Resolves peers-vs-sequence (directional loop, not pipeline; not order-less).
- **+** Provider outcomes (including denial) are first-class inputs to policy, not dead-ends.
- **+** The loop's history is a causal audit DAG (ADR-005), so *why* each stage ran is provable.
- **−** Requires guard/trigger conditions to be modeled (ECA) and the soundness rules enforced — bounded convergence and idempotency are now conformance obligations, not implementation details.
- **−** Convergence/termination must be demonstrable (bounded retries + a terminal failure state) to prevent oscillation.
