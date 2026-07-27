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

## 2. Error envelope — RFC 9457 Problem Details

The error envelope **adopts [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) (Problem Details for HTTP APIs)** via **[AEP-193](https://aep.dev/193/)** (ADR-AEP-001; a Tier-2 record adoption per [adopted-standards.md](../design-principles/adopted-standards.md) §1a). This *replaces* UDLM's former bespoke envelope — the closed error-code vocabulary (§3) and the `retryable` semantics survive as the problem `type` and extension members; the custom envelope shape is retired (net-negative surface). Every error emitted on an interop surface MUST be an RFC 9457 problem object:

```json
{
  "type": "validation.scope_not_recognized",
  "status": 400,
  "title": "Scope not recognized",
  "detail": "Scope 'tenant-foo' is not recognized by this realization.",
  "instance": "urn:udlm:audit:a1b2c3d4-2c95-4a1b-8d3e-7a9c1b2e4f8d",
  "request_id": "f3b64dda-2c95-4a1b-8d3e-7a9c1b2e4f8d",
  "retryable": false,
  "retry_after_seconds": null,
  "timestamp": "2026-05-26T14:32:18.456Z",
  "scope_attempted": "tenant-foo"
}
```

### Field semantics

**RFC 9457 core members:**

| Field | Required | Type | Description |
|---|---|---|---|
| `type` | yes | string | The problem-type token from the closed vocabulary (§3), e.g. `validation.scope_not_recognized` — the stable identifier a peer matches on (never the `detail` string). MAY be a dereferenceable `https://udlm.dev/errors/<type>` URI. |
| `status` | yes | integer | HTTP status (§5). The envelope is authoritative; status is the transport-level summary. |
| `title` | yes | string | Short, human-readable description of the problem **type** — stable across occurrences, no PII. Localizable. |
| `detail` | optional | string | Explanation specific to **this occurrence**. Developer-facing; MAY include PII (do not log); never string-matched by clients. |
| `instance` | yes | string | Identifies this specific occurrence — the URN of the audit record, `urn:udlm:audit:<audit_uuid>`, which carries the forensic link (§6). |

**UDLM extension members** — RFC 9457 §3.2 sanctions additional top-level members; per AEP-193, any dynamic/context values MUST appear as top-level members (not nested) so peers can read them without knowing an error-specific schema:

| Field | Required | Type | Description |
|---|---|---|---|
| `request_id` | yes | UUID | The request/operation that errored (RFC 9562). |
| `retryable` | yes | boolean | Whether the operation can safely be retried (§4). |
| `retry_after_seconds` | optional | number \| null | If retryable, suggested minimum delay; mirrors the HTTP `Retry-After` header. |
| `timestamp` | yes | RFC 3339 UTC | When the error occurred. |
| *(context)* | optional | any | Error-specific structured context as **top-level** members (e.g. `scope_attempted`) — the former nested `details.*`, flattened per AEP-193. Context members pass the §8a egress guard: they may echo what the actor submitted, never enumerate what the actor did not (a `scopes_known` list is the canonical violation). |

Peers MUST reject problem objects missing required members with `type: validation.error_envelope_malformed`.

### 2a. Mapping from the former bespoke envelope

| Was | Now |
|---|---|
| `error_code` | **`type`** (same closed vocabulary, §3) |
| `message` | split into **`title`** (stable problem-type text) + **`detail`** (this-occurrence text) |
| `audit_uuid` | carried by **`instance`** as `urn:udlm:audit:<uuid>` |
| `details` (nested object) | **flattened to top-level extension members** (AEP-193) |
| `request_id`, `retryable`, `retry_after_seconds`, `timestamp` | **RFC 9457 extension members** (unchanged semantics) |

---

## 3. Closed error code vocabulary

Error codes use a `namespace.code` pattern and are the values of the problem
`type` member (§2). Namespaces are closed at the udlm-conformance boundary; new
namespaces require a udlm spec change.

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
| `placement.*` | Placement/scheduling failures — no eligible provider, capacity or locality unsatisfiable, capability mismatch (distinct from `rate_limit.*` capacity) |
| `schema.*` | Schema sharing, version, or compatibility errors |
| `timeout.*` | Operation deadline exceeded |
| `conformance.*` | udlm conformance, feature availability, version compatibility (see [`CONFORMANCE.md`](../CONFORMANCE.md)) |

### 3.2 Required codes (minimum conformance set)

Every conformant realization MUST recognize and may emit these codes:

| Code | Retryable | HTTP status |
|---|---|---|
| `auth.unauthenticated` | no | 401 |
| `auth.token_expired` | no (re-auth) | 401 |
| `auth.token_revoked` | no | 401 |
| `authz.forbidden` | no | 403 |
| `authz.scope_insufficient` | no | 403 |
| `authz.cross_tenant_unauthorized` | no | 403 |
| `validation.malformed` | no | 400 |
| `validation.reference_not_found` | no | 404 |
| `validation.inline_credential_material` | no | 422 |
| `validation.binding_undeclared_output` | no | 422 |
| `validation.version_bump_insufficient` | no | 422 |
| `validation.intra_registry_version_pin` | no | 422 |
| `validation.pin_unresolvable` | no | 422 |
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
| `placement.no_eligible_provider` | no | 409 |
| `placement.capacity_exhausted` | yes | 503 |
| `placement.locality_unsatisfiable` | no | 409 |
| `placement.capability_mismatch` | no | 422 |
| `policy.sovereignty_egress_denied` | no | 403 |
| `policy.field_scope_violation` | no | 403 |
| `policy.promotion_diff_unapproved` | no | 409 |
| `conformance.feature_not_implemented` | no | 501 |
| `conformance.version_unsupported` | no | 409 |
| `conformance.declaration_unavailable` | yes | 503 |

Realizations MAY define additional codes within these namespaces for
implementation-specific scenarios, provided they:

- Honor the `retryable` flag accurately.
- Declare additional codes in their schema-sharing manifest
  (see [`schema-sharing.md`](schema-sharing.md)).
- Do NOT redefine the semantics of required codes.

### 3.3 Not-found versus not-authorized — the existence-disclosure rule

The vocabulary carries both `validation.reference_not_found` and
`authz.cross_tenant_unauthorized` because a refusal that cannot distinguish "this does not
exist" from "this is not yours" is unactionable — the submitter cannot tell a typo from a
missing grant. Distinguishing them, though, is an oracle: an actor who can probe foreign UUIDs
and read back not-found-versus-forbidden can enumerate another tenant's estate one identifier
at a time. Both concerns are real, so the rule is directional rather than a choice between them:

- **Inside the actor's own authorization scope**, an unresolvable reference is
  `validation.reference_not_found`. The actor is entitled to know the thing is absent.
- **Outside it**, the refusal is the authorization code — `authz.cross_tenant_unauthorized` for
  a tenancy crossing, `authz.forbidden` otherwise — **whether or not the target exists**. A
  realization MUST NOT vary the emitted `type`, `status`, `detail`, or timing on the existence
  of an out-of-scope target. This is the web's standard 403-over-404 existence-hiding posture,
  stated once here so every surface inherits it.

The authorization refusal is still actionable without disclosing anything: it names the
mechanism that would make the reference legal (the grant), never the target's attributes.

The same directional rule covers the create-time collision oracle: `validation.uuid_collision`
(409) reveals that *some* entity holds a submitted identifier, and an actor who deliberately
submits foreign UUIDs at create time can probe existence one identifier at a time. A
realization MUST emit `validation.uuid_collision` identically — same `type`, `status`,
`detail`, timing — whether the colliding entity is inside or outside the actor's scope, and
each such refusal writes its `REFUSE` record, so a probing pattern is legible in audit as an
enumeration attempt rather than invisible in an error branch. (Legitimate v4 collisions are
vanishingly rare; a run of them from one actor is signal, not noise.) See
`entities/entity-relationships.md` §6b (`XTA-006` — the cross-tenant refusal contract).

### 3.4 Refusal surfaces — where each code is emitted

A refusal is only as good as its enforcement point: the same violation caught at intake is
cheap, caught at realization is a rollback, and caught after a crossing is a disclosure that
cannot be withdrawn. This table maps the measured refusal corpus
([`use-cases/must-reject/`](../use-cases/must-reject/README.md) and the refusal cases of
[`use-cases/class-versioning/`](../use-cases/class-versioning/README.md)) to the code each
surface emits and the rule that governs it. The rules are defined in their home documents;
this is the index, not a second definition.

| Refusal surface | Enforcement point | Code | Governing rule |
|---|---|---|---|
| Unauthorized cross-tenant reference | intent validation | `authz.cross_tenant_unauthorized` | `XTA-006`, `XTA-007` (`entities/entity-relationships.md`) |
| Sovereignty egress across a declared boundary | pre-crossing, before dispatch or serialization | `policy.sovereignty_egress_denied` | `GMX-011` (`governance/governance-matrix.md`) |
| Inline credential material where a reference is required | intent intake, before any persistence | `validation.inline_credential_material` | `CPX-013`, `CPX-014` (`governance/credentials.md`) |
| Binding to an undeclared producer output | request validation, before any constituent realizes | `validation.binding_undeclared_output` | `CMP-009` (`entities/composite-service-model.md`) |
| Dispatch to a provider that never declared the capability | pre-dispatch eligibility | `placement.capability_mismatch` | `PRV-011` (`contracts/provider-contract.md`) |
| Write through a policy-reduced projection | modification validation | `policy.field_scope_violation` | `GMX-012`, `GMX-013` (`governance/governance-matrix.md`) |
| Version bump insufficient for the classification | registry validation | `validation.version_bump_insufficient` | `REG-011` (`governance/registry-governance.md`) |
| Element scope narrowed under a compatible bump | registry validation | `validation.version_bump_insufficient` | `REG-012` (`governance/registry-governance.md`) |
| Fixed-version class reference inside the registry | registry validation | `validation.intra_registry_version_pin` | `REG-013` (`governance/registry-governance.md`) |
| Pin (a `@version` or `@sha256` revision name, ADR-051) ahead of, or absent from, the consumed registry ref | estate validation | `validation.pin_unresolvable` | `REG-014` (`governance/registry-governance.md`) |
| Promotion whose output diff contradicts the compatibility claim | promotion | `policy.promotion_diff_unapproved` | `REG-016` (`governance/registry-governance.md`) |

Codes are not interchangeable across surfaces. A capability mismatch reported as
`provider.unavailable`, or a scope violation reported as `validation.malformed`, satisfies the
letter of "an error was returned" and defeats the purpose: the consumer cannot route the
failure to the person who can fix it.

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

Every error envelope carries its audit linkage in **`instance`** — `urn:udlm:audit:<audit_uuid>` (§2) — the URN of the audit record written for the error. (There is no separate top-level `audit_uuid` member; it lives in the `instance` URN, per §2a.) The audit record MUST contain:

- The `request_id` (envelope extension member) and the `audit_uuid` (from the `instance` URN) — same UUIDs.
- The originating actor (authenticated identity or `unauthenticated`).
- The operation attempted.
- The problem `type`, `title`, and `detail`.
- Structured `details` for reproducibility.
- Timestamp per [`time-and-clock.md`](time-and-clock.md).

This enables forensic lookup: from any error a consumer received, the operator
can find the full audit context. See [`universal-audit.md`](../observability/universal-audit.md).

### 6a. The refusal contract — what a rejection owes its reader

A refusal is a product, not an absence of one. Rejecting a request is the substrate's most
consequential output on the paths that matter most — a crossing that must not happen, a secret
that must not land, a provider that must not be handed work it cannot do — and a rejection that
is untyped, unexplained, leaky, or unrecorded fails the operator even though the dangerous
thing did not happen. Four obligations apply to **every** refusal emitted on an interop
surface, whatever the surface:

1. **Typed.** The refusal carries a `type` from the closed vocabulary (§3) that names the
   *violation class*, matchable without parsing prose. A violation reported under a code that
   describes a different class — a capability mismatch as a provider failure, a scope violation
   as a malformed payload — is a contract breach even though the request was rejected.
2. **Actionable.** The refusal names the mechanism that would make the request legal: the grant
   to obtain, the field to convert, the declared surface to bind against, the bump to declare,
   the authorization to seek. "Denied" without a route is a dead end, and the reader's next
   move is to retry the same thing.
3. **Non-leaking.** The refusal discloses no more than the refusal itself requires — see §8a.
4. **Auditable.** The refusal produces a durable record, linked by `instance` (§6), naming the
   rule that refused and the enforcement point that ran it. Refusals are recorded under the
   `REFUSE` audit action (`AUD-023` — refusals are first-class, not inferred from an evaluation
   record's outcome field), with the record shape and its subject list per `AUD-024`.

The four are jointly necessary. A refusal satisfying three of them is the failure mode the
must-reject corpus exists to catch, which is why every case's success criteria enumerate all
four rather than asserting "the request is rejected".

**The audit record of a refusal excludes what the refusal protected.** §6 requires the audit
record to carry the problem `detail`, and `detail` MAY carry sensitive occurrence text (§2) —
a tension that resolves in one direction on the refusal path: where the refused content is
itself the protected thing (credential material, a masked field's value, a foreign tenant's
attributes), the emitter MUST NOT place it in `detail`, and the audit record therefore carries
a `detail` that never held it. Field *paths*, violation classes, and rule identities are
recorded; values are not. This is the existing hash-only discipline of the audit leaf
(`universal-audit.md` §8 — leaves carry field paths and value hashes, never values) applied to
the error path that feeds it.

---

## 7. Localization

- `type` is NEVER localized — problem-type tokens are normative.
- `title` and `detail` MAY be localized. Localization is the emitter's responsibility.
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

### 8a. A refusal is itself a boundary crossing

An error travels outward, to an actor the substrate has just decided is not entitled to
something. It is therefore a payload leaving a boundary, and it gets the same treatment as any
other payload leaving that boundary: **the refusal passes the egress guard that produced it.**
This is the exfiltration-via-the-error-channel problem, and it is not hypothetical in this
model — the substrate's own error surfaces reach for exactly the content the refusal was
protecting. A policy denial's structural-validation output names failing field paths
(`contracts/policy-contract.md` §11 — `field_results` "included in consumer error response",
now guarded by §11's egress clause), and this document's own §2 example originally explained an
unrecognized scope by enumerating every known one in a `scopes_known` member — helpful, and an
enumeration of protected structure. Both shapes are the reason this rule exists.

The rule, applied to every refusal on every surface:

- **The refusal MUST NOT carry a value the refusal existed to protect.** No masked field value,
  no submitted credential material, no attribute of an out-of-scope entity — in `detail`, in an
  extension member, or in any nested structure.
- **The refusal MUST NOT enumerate protected structure.** Naming the *one* field or reference
  the actor named is disclosure the actor already possesses and is what makes the refusal
  actionable. Listing the fields, scopes, or entities the actor did *not* name — the
  `scopes_known` shape — discloses the protected set and is prohibited on any surface where
  that set is itself governed. Where enumeration is genuinely useful and genuinely
  unprotected — the declared outputs of a producer type the actor is entitled to bind against,
  the capabilities a provider publicly declares — it is permitted and expected, because that
  content is already the actor's to read.
- **Filtering happens before serialization, not after.** The guard runs on the refusal
  *object*, so the pre-guard form never exists on the wire.
- **The same rule governs the audit record** (§6a), because the audit store is a different
  boundary with its own readers.

The practical test: read the refusal as the actor who triggered it, and ask what they now know
that they did not know before. The answer must be exactly "the thing I asked for is not
permitted, and here is the mechanism that would permit it".

---

## 9. Validation rules (conformance checks)

A conformant realization MUST:

- Emit only error codes in the closed vocabulary (or declared extensions).
- Set `retryable` correctly per the code semantics.
- Include `request_id` (extension member) and the audit link in `instance` (`urn:udlm:audit:<audit_uuid>`, §2) in every error.
- Emit the RFC 9457 problem object exactly (§2), with `type` from the closed vocabulary.
- Reject malformed envelopes from peers with `validation.error_envelope_malformed`.
- Emit the code that names the **violation class** for the surface, per §3.4 — not a
  neighbouring code that happens to carry a plausible status.
- Vary neither `type`, `status`, `detail`, nor response timing on the existence of a target
  outside the actor's authorization scope (§3.3).
- Carry, on every refusal, the remediation mechanism in `detail` or a named extension member,
  and carry no value or enumeration the refusal existed to protect (§6a, §8a).
- Write a `REFUSE` audit record for every refusal, linked by `instance`, naming the refusing
  rule and the enforcement point (`AUD-023`, `AUD-024`).

---

## 10. Adopted standards & related contracts

**Adopted (ADR-AEP-001, Tier-2 per [adopted-standards.md](../design-principles/adopted-standards.md)):**
- [RFC 9457](https://www.rfc-editor.org/rfc/rfc9457) — Problem Details for HTTP APIs (the error envelope, §2)
- [AEP-193](https://aep.dev/193/) — the AEP error model, which adopts RFC 9457
- [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562) — UUIDs (`request_id`, audit id) · [RFC 3339](https://www.rfc-editor.org/rfc/rfc3339) — `timestamp`

**Related contracts:**
- [`identifier-scheme.md`](identifier-scheme.md) — UUIDs for request_id and audit_uuid
- [`time-and-clock.md`](time-and-clock.md) — timestamp format
- [`retry-semantics.md`](retry-semantics.md) — how `retryable` and `retry_after_seconds` drive retry behavior
- [`rate-limit-and-backpressure.md`](rate-limit-and-backpressure.md) — `rate_limit.*` codes
- [`universal-audit.md`](../observability/universal-audit.md) — audit record requirements
- [`schema-sharing.md`](schema-sharing.md) — how extension codes are declared
