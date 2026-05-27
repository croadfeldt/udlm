# UDLM — Rate Limit and Backpressure Contract

**Document Status:** 📋 Draft — Initial Specification
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA

> Defines the substrate contract for declaring capacity, signaling backpressure,
> and coordinating load between consumers, realizations, providers, and peers.
> Wire-compatible: any conformant peer MUST recognize the `rate_limit.*` signals
> any other peer emits and respond per this contract.

---

## 1. Purpose

Every interop surface is finite. Consumers, providers, and peers must signal
capacity to each other so the system degrades gracefully under load instead of
collapsing. This contract defines how that signaling works on the wire.

---

## 2. Rate limit declaration

Every conformant interop surface (consumer API endpoints, provider callbacks,
federation endpoints, information provider queries) MAY publish a rate limit
declaration via the capability discovery mechanism
(see [`capability-discovery.md`](capability-discovery.md)).

A rate limit declaration:

```json
{
  "surface": "consumer.requests.submit",
  "scope": "per_consumer",
  "limit": 100,
  "window_seconds": 60,
  "burst": 150,
  "soft_thresholds": [
    { "level": "warning", "at_pct": 75 },
    { "level": "critical", "at_pct": 90 }
  ]
}
```

| Field | Description |
|---|---|
| `surface` | Stable identifier for the rate-limited surface |
| `scope` | One of: `per_consumer`, `per_tenant`, `per_provider`, `global`, `per_credential` |
| `limit` | Steady-state requests permitted within `window_seconds` |
| `window_seconds` | Sliding-window size for rate accounting |
| `burst` | Brief allowance above `limit`; consumed faster than refill |
| `soft_thresholds` | Optional: percentages that trigger advisory signals |

A peer MAY query a realization's rate limit declarations to plan request
patterns proactively.

---

## 3. Hard limit response (429)

When a request would exceed the limit, the conformant realization MUST:

1. Reject the request with `rate_limit.exceeded` per the error envelope
   ([`error-model.md`](error-model.md)).
2. Set `retryable: true`.
3. Set `retry_after_seconds` to the minimum delay until capacity is available.
4. Map to HTTP status `429 Too Many Requests` on HTTP transports.
5. Include a `Retry-After` HTTP header matching `retry_after_seconds`
   (HTTP transport only).

Example response:

```json
{
  "error_code": "rate_limit.exceeded",
  "message": "Submission rate exceeded for consumer 'tenant-a'. Retry in 12 seconds.",
  "request_id": "f3b64dda-...",
  "audit_uuid": "a1b2c3d4-...",
  "retryable": true,
  "retry_after_seconds": 12,
  "details": {
    "surface": "consumer.requests.submit",
    "scope": "per_consumer",
    "limit": 100,
    "window_seconds": 60,
    "current_count": 100
  },
  "timestamp": "2026-05-26T14:32:18.456Z"
}
```

---

## 4. Soft threshold signaling (warning, critical)

Soft thresholds enable proactive load shedding. When utilization crosses a soft
threshold:

1. The realization SHOULD include an advisory header (HTTP) or envelope field
   indicating the level. HTTP header: `X-Capacity-Level: warning|critical`.
2. The realization MAY emit an audit event `rate_limit.threshold_crossed` for
   the audit chain.
3. The consumer SHOULD reduce request rate but is not blocked.
4. The realization MUST NOT delay response delivery as a backpressure mechanism
   below the hard limit — only flag it.

---

## 5. Consumer obligations (mandatory)

A conformant consumer MUST:

- Recognize `rate_limit.exceeded` responses and back off.
- Honor `retry_after_seconds` as the minimum wait.
- Apply exponential backoff + jitter per [`retry-semantics.md`](retry-semantics.md)
  if multiple consecutive 429s occur.
- NOT retry a 429 response in a tight loop without backoff.

A consumer SHOULD:

- Subscribe to rate-limit declarations via capability discovery to plan
  proactively.
- React to soft-threshold signals by reducing request rate.

---

## 6. Provider capacity declaration

Information providers and service providers MAY declare their query/operation
capacity to the realization via the provider registration mechanism (see
[`provider-contract.md`](provider-contract.md)):

```json
{
  "capacity": {
    "queries_per_minute": 600,
    "concurrent_requests": 25,
    "burst": 1000
  }
}
```

The realization uses these declarations to:

- Throttle dispatched requests to the provider.
- Schedule scheduled requests within provider capacity.
- Surface capacity exhaustion to consumers as `provider.unavailable` (retryable).

A provider that finds itself overloaded MAY respond with `rate_limit.exceeded`
itself; the realization treats this as a transient provider failure and
applies retry semantics.

---

## 7. Federation backpressure

Cross-peer federation surfaces MUST honor the same contract:

- A peer being federated-to MAY rate-limit incoming federation requests.
- The federating peer MUST honor `rate_limit.exceeded` and back off.
- Federation rate limits MAY be declared per peer or globally.

---

## 8. Fairness

A realization that hosts multiple consumers MUST NOT permit one consumer to
starve others:

- Per-scope limits (per_consumer, per_tenant) ensure isolation.
- A global limit, if used alone without per-consumer scoping, MUST include a
  fairness policy in its declaration.

This is a substrate requirement: peers consuming each other's data assume
fair allocation across consumers.

---

## 9. Capacity warnings vs errors

| Signal | Severity | Wire form |
|---|---|---|
| Within limit, below soft thresholds | normal | No signal |
| Crossed warning threshold | advisory | `X-Capacity-Level: warning` header / envelope flag |
| Crossed critical threshold | strong advisory | `X-Capacity-Level: critical` header / envelope flag |
| At or beyond hard limit | rejection | `429` / `rate_limit.exceeded` |

---

## 10. Validation rules (conformance checks)

A conformant realization MUST:

- Publish rate limit declarations via capability discovery if any surface is
  limited.
- Reject overflow with `rate_limit.exceeded` + `retry_after_seconds`.
- Honor `Retry-After` headers on HTTP transports.
- Provide soft-threshold signaling where declared.
- Apply per-scope fairness.

A conformant consumer MUST:

- Recognize and back off on `rate_limit.exceeded`.
- Honor `retry_after_seconds`.

---

## 11. Related contracts

- [`error-model.md`](error-model.md) — `rate_limit.*` codes
- [`retry-semantics.md`](retry-semantics.md) — exponential backoff coordination
- [`capability-discovery.md`](capability-discovery.md) — rate-limit declaration surface
- [`provider-contract.md`](provider-contract.md) — provider capacity declaration
- [`information-providers.md`](10-information-providers.md) — query rate limits for information providers
