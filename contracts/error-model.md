# UDLM — Error Model Contract

**Document Status:** 📋 Draft — Initial Specification
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA

> Defines the wire-compatible error envelope, the closed vocabulary of error
> codes for interop surfaces, the categorization of errors as transient vs
> permanent, and the audit linkage every error must carry. Any conformant peer
> MUST produce errors any other peer can deserialize, categorize, and act on.

---

## 1. Purpose

Errors that cross interop boundaries — consumer-facing, provider-facing,
federation-facing — must have a closed, predictable shape so peers can:

- Categorize errors as retryable or permanent without parsing message strings.
- Link errors back to audit records for forensic analysis.
- Localize messages without changing semantics.
- Coordinate retry, backoff, and escalation across realizations.

This document defines the error envelope, code namespaces, status mappings,
and validation rules.

---

## 2. Error envelope

Every error emitted on an interop surface MUST conform to this envelope:

```json
{
  "error_code": "validation.scope_not_recognized",
  "message": "Scope 'tenant-foo' is not recognized by this realization.",
  "request_id": "f3b64dda-2c95-4a1b-8d3e-7a9c1b2e4f8d",
  "audit_uuid": "a1b2c3d4-...",
  "retryable": false,
  "retry_after_seconds": null,
  "details": {
    "scope_attempted": "tenant-foo",
    "scopes_known": ["tenant-a", "tenant-b"]
  },
  "timestamp": "2026-05-26T14:32:18.456Z"
}
```

### Field semantics

| Field | Required | Type | Description |
|---|---|---|---|
| `error_code` | yes | string | Closed-vocabulary code (see §3) |
| `message` | yes | string | Human-readable; localizable; informative only |
| `request_id` | yes | UUID | UUID of the request/operation that errored |
| `audit_uuid` | yes | UUID | UUID of the audit record for this error |
| `retryable` | yes | boolean | Whether the operation can safely be retried |
| `retry_after_seconds` | optional | number \| null | If retryable, suggested minimum delay before retry |
| `details` | optional | object | Structured error-specific context; schema per error code |
| `timestamp` | yes | RFC 3339 UTC | When the error occurred |

Peers MUST reject error responses missing required fields with
`validation.error_envelope_malformed`.

---

## 3. Closed error code vocabulary

Error codes use a `namespace.code` pattern. Namespaces are closed at the
udlm-conformance boundary; new namespaces require a udlm spec change.

### 3.1 Namespaces

| Namespace | Domain |
|---|---|
| `auth.*` | Authentication and identity errors |
| `authz.*` | Authorization and policy-decision errors |
| `validation.*` | Input or schema validation failures |
| `policy.*` | Policy evaluation outcomes (deny, strip, redact decisions surfaced as errors) |
| `lifecycle.*` | Lifecycle state machine violations |
| `system.*` | Internal system errors (with care — most should not leak details) |
| `rate_limit.*` | Rate limit and capacity errors |
| `credential.*` | Credential issuance, revocation, expiration |
| `federation.*` | Cross-peer federation errors |
| `provider.*` | Provider interaction errors |
| `schema.*` | Schema sharing, version, or compatibility errors |
| `timeout.*` | Operation deadline exceeded |
| `conformance.*` | udlm conformance, feature availability, version compatibility (see [`CONFORMANCE.md`](CONFORMANCE.md)) |

### 3.2 Required codes (minimum conformance set)

Every conformant realization MUST recognize and may emit these codes:

| Code | Retryable | HTTP status |
|---|---|---|
| `auth.unauthenticated` | no | 401 |
| `auth.token_expired` | no (re-auth) | 401 |
| `auth.token_revoked` | no | 401 |
| `authz.forbidden` | no | 403 |
| `authz.scope_insufficient` | no | 403 |
| `validation.malformed` | no | 400 |
| `validation.scope_not_recognized` | no | 400 |
| `validation.uuid_collision` | no | 409 |
| `validation.timestamp_malformed` | no | 400 |
| `validation.timestamp_skew_exceeded` | yes (after clock sync) | 400 |
| `validation.error_envelope_malformed` | no | 400 |
| `lifecycle.invalid_transition` | no | 409 |
| `lifecycle.terminal_state` | no | 409 |
| `lifecycle.dependency_unsatisfied` | yes (when dependency resolves) | 409 |
| `rate_limit.exceeded` | yes | 429 |
| `rate_limit.capacity_warning` | yes | 200 (warning header) |
| `credential.expired` | no (rotate) | 401 |
| `credential.revoked` | no | 401 |
| `system.transient` | yes | 503 |
| `system.unavailable` | yes | 503 |
| `timeout.deadline_exceeded` | yes (with caution) | 504 |
| `schema.version_incompatible` | no | 409 |
| `schema.unknown_type` | no | 422 |
| `federation.peer_unreachable` | yes | 503 |
| `federation.peer_version_incompatible` | no | 409 |
| `provider.callback_invalid` | no | 400 |
| `provider.unavailable` | yes | 503 |
| `conformance.feature_not_implemented` | no | 501 |
| `conformance.version_unsupported` | no | 409 |
| `conformance.declaration_unavailable` | yes | 503 |

Realizations MAY define additional codes within these namespaces for
implementation-specific scenarios, provided they:

- Honor the `retryable` flag accurately.
- Declare additional codes in their schema-sharing manifest
  (see [`schema-sharing.md`](schema-sharing.md)).
- Do NOT redefine the semantics of required codes.

---

## 4. Transient vs permanent

The `retryable` flag is normative:

- `true` — the same request, retried after the indicated delay, may succeed
  without modification.
- `false` — the operation will fail again on retry unless something external
  changes (re-authentication, schema update, policy change, etc.).

A consumer SHOULD NOT retry `retryable: false` errors. A conformant peer MUST
set the flag correctly per the code definitions in §3.2.

---

## 5. HTTP status code mapping

For HTTP-transport interop surfaces, the mapping in §3.2 is normative. Peers
MUST emit the prescribed status alongside the envelope. The envelope is the
authoritative description; the HTTP status is the transport-level summary.

For non-HTTP transports (gRPC, message bus), realizations map to equivalent
transport-level error codes per the transport's conventions.

---

## 6. Audit linkage

Every error envelope MUST include an `audit_uuid` linking to the audit record
written for the error. The audit record MUST contain:

- The `request_id` and `audit_uuid` from the envelope (same UUIDs).
- The originating actor (authenticated identity or `unauthenticated`).
- The operation attempted.
- The error_code and message.
- Structured `details` for reproducibility.
- Timestamp per [`time-and-clock.md`](time-and-clock.md).

This enables forensic lookup: from any error a consumer received, the operator
can find the full audit context. See [`universal-audit.md`](universal-audit.md).

---

## 7. Localization

- `error_code` is NEVER localized — codes are normative tokens.
- `message` MAY be localized. Localization is the emitter's responsibility.
- `details` field keys are normative; values MAY be localized where they are
  human-readable, but identifiers, codes, and other tokens remain in canonical
  form.

---

## 8. Internal vs interop errors

Errors that never cross an interop boundary (between dcm internal components,
for example) MAY use free-form representation. Only errors that flow to:

- Consumers (consumer API)
- Providers (provider callbacks)
- Peer realizations (federation)
- Audit log (always)

...are required to conform to this contract. The audit-log requirement
ensures that even internal errors are recoverable for forensics — internal
representation can be free-form, but the audit-log entry follows this contract.

---

## 9. Validation rules (conformance checks)

A conformant realization MUST:

- Emit only error codes in the closed vocabulary (or declared extensions).
- Set `retryable` correctly per the code semantics.
- Include `request_id` and `audit_uuid` in every error.
- Use the wire envelope schema exactly.
- Reject malformed envelopes from peers with `validation.error_envelope_malformed`.

---

## 10. Related contracts

- [`identifier-scheme.md`](identifier-scheme.md) — UUIDs for request_id and audit_uuid
- [`time-and-clock.md`](time-and-clock.md) — timestamp format
- [`retry-semantics.md`](retry-semantics.md) — how `retryable` and `retry_after_seconds` drive retry behavior
- [`rate-limit-and-backpressure.md`](rate-limit-and-backpressure.md) — `rate_limit.*` codes
- [`universal-audit.md`](universal-audit.md) — audit record requirements
- [`schema-sharing.md`](schema-sharing.md) — how extension codes are declared
