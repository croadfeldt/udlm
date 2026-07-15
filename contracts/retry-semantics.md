# UDLM — Retry Semantics Contract

**Document Status:** 📋 Draft — Initial Specification
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA

> Defines the substrate contract for what is safely retryable, how retries
> preserve idempotency and state, what budgets and backoff parameters apply,
> and how peers coordinate retry behavior. Wire-compatible: any conformant
> peer MUST honor the retry signals (`retryable`, `retry_after_seconds`) any
> other peer emits.

---

## 1. Purpose

Without a shared retry contract, peers and consumers retry inconsistently:
some give up too early, some retry permanent errors, some retry without
idempotency keys and create duplicate effects. This contract eliminates that
ambiguity.

---

## 2. Retry eligibility

An operation is retryable IF AND ONLY IF the most recent error response carries
`retryable: true` (per [`error-model.md`](error-model.md)).

A consumer or peer MUST NOT:

- Retry operations whose last error had `retryable: false`.
- Infer retryability from HTTP status codes alone.
- Retry without honoring the `retry_after_seconds` minimum delay.

A conformant realization MUST set the `retryable` flag correctly per the
error-code definitions.

---

## 3. Idempotency requirement

Retried operations MUST be idempotent across attempts. The contract:

1. The retried request MUST reuse the **original `Idempotency-Key`** (or
   equivalent idempotency identifier per [`event-catalog.md`](event-catalog.md)).
2. The receiving peer MUST recognize the repeated key and:
   - Return the **same result** as the previous attempt if the previous attempt
     reached a terminal state.
   - Resume in-flight if the previous attempt is still pending.
   - Process freshly if no prior attempt is on record (within the deduplication window).
3. The deduplication window is at least **24 hours** (PT24H) from the first
   submission. Realizations MAY extend; MUST NOT shorten.
4. Idempotency-Key reuse with a **different payload** MUST be rejected with
   `validation.idempotency_key_mismatch`.

This applies to all interop surfaces: consumer API submissions, provider
callbacks, federation exchanges.

---

## 4. Backoff parameters

A conformant retry strategy MUST use **exponential backoff with jitter**.
Normative parameters:

| Parameter | Value | Notes |
|---|---|---|
| Base delay | 1 second | Initial wait before first retry |
| Multiplier | 2 | Each subsequent attempt doubles the base |
| Maximum delay | 60 seconds | Cap on any single delay |
| Jitter | full | Actual delay is uniform random in `[0, computed_delay]` |
| Maximum attempts | 5 | Including the initial attempt = 6 total |

If the error response includes `retry_after_seconds`, the consumer MUST wait
at least that long, then apply jitter on the remainder if necessary.

Realizations MAY use stricter parameters (more attempts, longer caps) per
profile. They MUST NOT use looser ones at interop boundaries — peers count
on the parameters as ceilings.

---

## 5. Retry budgets

A consumer or peer MUST NOT exceed:

- **Per-operation**: 5 retry attempts (6 total) before giving up.
- **Per-resource per-hour**: 30 retry attempts across all operations targeting
  the same resource (entity_uuid or request_uuid).
- **Global per-consumer per-minute**: subject to rate-limit per
  [`rate-limit-and-backpressure.md`](rate-limit-and-backpressure.md).

Exceeding the per-operation budget terminates the operation in `FAILED` state
with `system.retry_budget_exhausted`.

---

## 6. State during retry

A request being retried stays in its current lifecycle state until terminal:

- A `REQUESTED` request that hits a transient failure stays `REQUESTED` between
  retry attempts (not regressed to `INTENT`).
- The retry counter is incremented in the audit record.
- The `Idempotency-Key` is preserved.
- The `entity_uuid` (if assigned) MUST be preserved across retries.

Once retries exhaust:

- The request transitions to `FAILED`.
- The problem `type` (`error-model.md` §2) from the last attempt is recorded.
- Compensation MAY be invoked per the recovery policy (see
  [`operational-models.md`](../lifecycle/operational-models.md)).

---

## 7. Retry scope

When an operation has multiple steps (e.g., a dependency group), retry scope
is **the failed step**, not the whole operation:

- Successful dependencies are NOT re-executed.
- The failed step is retried with its original inputs.
- If the failed step depended on field-injection from a sibling that completed,
  the injected fields are reused.

---

## 8. Provider-side retries

A provider executing a request MAY internally retry transient failures before
reporting back to the realization. Provider-side retries are opaque to the
realization. The realization counts only the externally-visible retries (its
own request attempts to the provider).

A provider that has exhausted internal retries MUST report failure via the
standard callback (see [`provider-contract.md`](provider-contract.md)) with
`retryable` set per the failure semantics.

---

## 9. Federation retries

Cross-peer federation requests follow the same contract:

- The originating peer applies the standard backoff and budget.
- The receiving peer recognizes the same `Idempotency-Key`.
- `federation.peer_unreachable` is retryable; `federation.peer_version_incompatible`
  is not.

---

## 10. Validation rules (conformance checks)

A conformant realization MUST:

- Honor `retryable: false` (never retry permanent errors).
- Honor `retry_after_seconds`.
- Preserve `Idempotency-Key` across retries.
- Reject mismatched-payload reuse with `validation.idempotency_key_mismatch`.
- Stop retrying after the per-operation budget.
- Use exponential backoff + jitter within the prescribed bounds.
- Audit every retry attempt.

---

## 11. Related contracts

- [`error-model.md`](error-model.md) — the `retryable` flag and `retry_after_seconds`
- [`rate-limit-and-backpressure.md`](rate-limit-and-backpressure.md) — rate-limit-driven retries
- [`event-catalog.md`](event-catalog.md) — Idempotency-Key in event envelopes
- [`operational-models.md`](../lifecycle/operational-models.md) — recovery policies after exhaustion
- [`provider-contract.md`](provider-contract.md) — provider-side retry expectations
- [`universal-audit.md`](../observability/universal-audit.md) — retry attempts in audit chain
