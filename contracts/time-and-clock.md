# UDLM — Time and Clock Model Contract

**Document Status:** 📋 Draft — Initial Specification
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA

> Defines how time is represented, ordered, and tolerated across udlm-conformant
> realizations and between peers. Wire-compatible: any conformant peer MUST
> emit timestamps any other peer can interpret without ambiguity.

---

## 1. Purpose

Distributed systems coordinate on time. Audit chains depend on ordering. Federation
depends on event sequencing. Without a normative time model, peers cannot
exchange data with shared meaning.

This document defines: the required wall-clock representation, ordering
semantics, skew tolerance, validation rules, and how time appears in every
wire format.

---

## 2. Time representation

A conformant realization MUST:

- Use **UTC** for all timestamps that cross interop boundaries. Local time is
  permitted only within UI rendering layers; it MUST be converted to UTC before
  persistence or transport.
- Encode timestamps as **ISO 8601 / RFC 3339** strings with explicit `Z`
  suffix. Example: `2026-05-26T14:32:18.456Z`.
- Use **millisecond precision** in all wire-level timestamps. Higher precision
  (microseconds, nanoseconds) MAY be used internally but MUST be truncated to
  milliseconds when emitted.
- NEVER use Unix epoch seconds, fractional days, or other non-ISO encodings on
  the wire.

### 2.1 Required precision and format

| Field type | Required precision | Wire format example |
|---|---|---|
| Event timestamps | Millisecond | `2026-05-26T14:32:18.456Z` |
| Audit record timestamps | Millisecond | `2026-05-26T14:32:18.456Z` |
| Lifecycle state transitions | Millisecond | `2026-05-26T14:32:18.456Z` |
| Scheduled request times (`not_before`, etc.) | Second (millis permitted) | `2026-05-26T15:00:00Z` |
| Date-only fields (rare) | Day | `2026-05-26` |

Peers MUST reject timestamps that lack timezone indication or fail ISO 8601
parsing with `validation.timestamp_malformed`.

---

## 3. Authoritative timestamps

Some artifacts have multiple timestamp candidates (when received, when committed,
when audited). The contract defines which is authoritative:

| Artifact | Authoritative timestamp source |
|---|---|
| Event | Set by the commit log at append time, NOT by the emitter |
| Audit record | Set by the audit log at append time |
| Lifecycle state transition | Set by the system effecting the transition |
| Scheduled request `not_before` | Set by the consumer at submission |
| Provider callback report | Provider-supplied; subject to validation rules in §5 |

The authoritative timestamp is the one used for ordering and for audit-chain
linking.

---

## 4. Clock skew tolerance

Peers will have clocks that drift. The contract defines tolerance bounds:

- **Maximum acceptable skew**: ±5 seconds between a conformant peer and the
  source of an inbound artifact.
- **Recommended sync mechanism**: NTP or equivalent; peers SHOULD maintain sync
  to within 1 second of UTC reference time.
- **Skew detection**: peers MUST detect inbound artifacts whose timestamp
  exceeds tolerance and:
  - For provider-supplied timestamps: reject with `validation.timestamp_skew_exceeded`.
  - For peer-supplied timestamps in federation: log an audit event and proceed,
    but flag the source for sync investigation.
- **Future timestamps**: any timestamp more than 5 seconds in the future
  relative to the receiving peer's clock MUST be rejected.

---

## 5. Provider timestamp validation

Provider callbacks include timestamps. The contract requires:

1. Provider timestamp MUST be UTC + ISO 8601.
2. Provider timestamp MUST be within ±5 seconds of the receiving peer's clock.
3. If validation fails, the callback is rejected and the provider is notified
   via the standard error envelope (see [`error-model.md`](error-model.md)).
4. A conformant peer MUST NOT silently rewrite provider timestamps. Either
   accept or reject.

---

## 6. Total ordering and audit chain

The audit chain ([`universal-audit.md`](universal-audit.md)) requires total
ordering of events. Timestamps alone are insufficient when two events have
identical millisecond stamps. The contract:

1. The audit chain orders by `(timestamp, sequence_uuid)` where `sequence_uuid`
   is a UUIDv7 generated at append time.
2. UUIDv7 carries embedded time at sub-millisecond resolution, providing a
   stable tiebreak.
3. A conformant peer MUST be able to reconstruct total ordering from any
   contiguous segment of the audit chain using only `(timestamp, sequence_uuid)`.

---

## 7. Leap seconds

A conformant realization MUST:

- Use a **leap-second smearing** strategy (gradual ±N ms adjustment over a
  configured window) rather than a hard step.
- Reject the introduction of `:60` second values in timestamps. Smear instead.
- Document its smearing strategy in its conformance declaration.

This avoids audit-chain ordering anomalies during leap-second events.

---

## 8. Time zones (consumer-facing)

UI / consumer-facing rendering MAY display timestamps in local time. The
contract:

- Storage and transport: UTC.
- Display: per-user preference.
- Audit records: always UTC; UI may render in local but the source-of-truth
  is UTC.

---

## 9. Validation rules (conformance checks)

A conformant realization MUST:

- Reject non-UTC timestamps at ingest.
- Reject timestamps lacking explicit timezone indication.
- Reject timestamps with skew >5 seconds (with categorization per §4).
- Truncate or reject sub-millisecond precision on the wire.
- Smear, not step, through leap seconds.

---

## 10. Related contracts

- [`identifier-scheme.md`](identifier-scheme.md) — UUIDv7 carries embedded time
- [`event-catalog.md`](event-catalog.md) — events carry authoritative timestamps
- [`universal-audit.md`](universal-audit.md) — audit chain total ordering
- [`error-model.md`](error-model.md) — timestamp-related error codes
- [`scheduled-requests.md`](scheduled-requests.md) — `not_before` and recurring schedules
