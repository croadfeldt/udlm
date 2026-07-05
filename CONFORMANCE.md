# UDLM — Conformance Specification

**Document Status:** 📋 Draft — Initial Specification
**Document Type:** Top-Level Conformance Surface
**Established:** 2026-05-26
**Maps to:** DATA (umbrella)

> Defines what a realization MUST implement to be **udlm-conformant**. A
> conformant realization is wire-compatible with any other conformant
> realization of the same major udlm version — its data can be read, its
> events can be parsed, its contracts can be honored by peers without
> per-realization adapters. This document is the conformance surface that
> an independent verifier tests against.

---

## 1. Purpose

A peer realization that claims udlm conformance commits to:

- Producing data, events, and errors that any other conformant peer can
  deserialize and act on.
- Honoring the contracts defined in `contracts/`, `lifecycle/`, `governance/`,
  `entities/`, and `foundations/`.
- Publishing schemas, capabilities, and a conformance declaration via the
  schema-sharing protocol so peers can discover compatibility.
- Maintaining versioning discipline so peers can negotiate.

This document defines the conformance surface in one place. Each individual
contract doc carries its own validation rules; CONFORMANCE.md consolidates them
and adds the meta-rules (declaration format, versioning, certification).

---

## 2. What conformance certifies

Conformance certifies **wire-level interoperability** within a major udlm
version. Specifically, a conformant realization:

| Certifies | Does NOT certify |
|---|---|
| Wire-compatible data exchange with peers | Implementation portability across realizations |
| Schema-compatible extensions via schema-sharing | Internal storage, APIs, or runtime mechanics |
| Closed-vocabulary errors and codes on interop surfaces | Operational performance, scale, or reliability |
| Conformant identifier, timestamp, and event formats | Specific deployment topology |
| Honoring the lifecycle state machine | UX, ergonomics, or operator tooling |

Two conformant realizations with disjoint runtime implementations can federate
and exchange data; they cannot necessarily swap controllers or share storage.

---

## 3. Conformance levels

### 3.1 Full Conformance

Implements every required contract listed in §5. Publishes a conformance
declaration with `level: "full"` and no exclusions.

### 3.2 Declared Partial Conformance

Implements a documented subset of required contracts. The realization MUST:

- Publish a conformance declaration with `level: "partial"`.
- Enumerate excluded contracts in the `exclusions` field.
- Reject operations on excluded features with `conformance.feature_not_implemented`
  (see §7).
- NOT silently fail or partially implement an excluded contract.

A peer interacting with a partially-conformant realization MUST check the
conformance declaration before depending on an excluded feature.

### 3.3 Conformance with Extensions

Implements full conformance AND publishes extensions (custom resource types,
custom event types, custom credential types, etc.) via the schema-sharing
protocol. Extensions MUST:

- Be published in the realization's schema bundle.
- Use only allowed extension points (e.g., custom resource types within the
  resource type registry, not redefinitions of core types).
- Not break existing contracts.

Full Conformance and Conformance with Extensions are not separate levels in
the declaration; the latter is signaled by the presence of `extensions` in
the schema bundle.

---

## 4. Conformance declaration

Every conformant realization MUST publish a conformance declaration at:

```
GET /.well-known/udlm/conformance
```

### 4.1 Declaration schema

```json
{
  "realization": {
    "name": "DCM",
    "vendor": "example-org",
    "version": "1.4.2"
  },
  "udlm_version": "0.1.0",
  "level": "full",
  "exclusions": [],
  "extensions_published": true,
  "schema_bundle_url": "/.well-known/udlm/schema-bundle",
  "interop_surfaces": {
    "consumer_api": { "available": true, "transport": "http", "base_url": "https://dcm.example/api/v1" },
    "provider_callbacks": { "available": true, "transport": "http", "auth": "mtls+credential" },
    "federation": { "available": true, "transport": "http", "auth": "mtls+credential" },
    "audit_export": { "available": true, "transport": "http" }
  },
  "leap_second_strategy": "smear",
  "auth_mechanism_for_schema_endpoints": "credential",
  "conformance_test_suite_version": "1.0.0",
  "self_certified_at": "2026-05-26T14:32:18.456Z",
  "independent_verification": {
    "verifier": "example-verifier",
    "verifier_version": "0.9.45",
    "verification_uuid": "f3b64dda-...",
    "verified_at": "2026-05-26T16:00:00.000Z",
    "report_url": "https://dav.example/reports/f3b64dda"
  }
}
```

### 4.2 Field semantics

| Field | Required | Description |
|---|---|---|
| `realization` | yes | Self-identification |
| `udlm_version` | yes | udlm semver this realization conforms to |
| `level` | yes | `"full"` or `"partial"` |
| `exclusions` | required if level=partial | List of contract names not implemented |
| `extensions_published` | yes | Whether schema bundle includes extensions |
| `schema_bundle_url` | yes | Where to fetch the schema bundle |
| `interop_surfaces` | yes | Which surfaces are available and how to reach them |
| `leap_second_strategy` | yes | `"smear"` (required by `time-and-clock.md`) |
| `auth_mechanism_for_schema_endpoints` | yes | How peers authenticate to fetch schemas |
| `conformance_test_suite_version` | yes | Which version of the test suite (see §8) was run |
| `self_certified_at` | yes | RFC 3339 UTC; when self-certification was performed |
| `independent_verification` | optional | Present if an independent verifier has validated |

---

## 5. Required contracts

A Full Conformance realization MUST implement every contract below. Partial
Conformance realizations MAY exclude contracts marked **excludable**.

### 5.1 Foundations (NOT excludable)

- `foundations/context-and-purpose.md`
- `foundations/foundations.md`
- `foundations/entity-types.md`
- `foundations/four-states.md` — the four-state lifecycle is non-negotiable
- `foundations/layering-and-versioning.md`
- `foundations/ownership-sharing-allocation.md`

### 5.2 Wire-compatibility contracts (NOT excludable)

These are the contracts that make wire-compatibility work. Excluding any of
them disqualifies the realization from any conformance level.

- `contracts/identifier-scheme.md`
- `contracts/time-and-clock.md`
- `contracts/error-model.md`
- `contracts/event-catalog.md`
- `contracts/schema-sharing.md`

### 5.3 Operational contracts (NOT excludable)

- `contracts/retry-semantics.md`
- `contracts/rate-limit-and-backpressure.md`
- `contracts/provider-contract.md`
- `contracts/policy-contract.md`
- `contracts/data-store-contracts.md`

### 5.4 Entity and lifecycle contracts (mostly required)

- `entities/resource-service-entities.md` — required
- `entities/resource-type-hierarchy.md` — required
- `entities/entity-relationships.md` — required
- `lifecycle/operational-models.md` — required
- `entities/composite-service-model.md` — **excludable**
- `lifecycle/scheduled-requests.md` — **excludable**
- `lifecycle/request-dependency-graph.md` — **excludable**
- `lifecycle/subscription-lifecycle.md` — **excludable**
- `lifecycle/ingestion-model.md` — **excludable** (peer may not support brownfield)

### 5.5 Governance contracts (mostly required, some excludable)

- `governance/governance-matrix.md` — required
- `governance/auth-providers.md` — required (at least one auth mode)
- `governance/credentials.md` — required
- `governance/authority-tier-model.md` — required
- `governance/accreditation-and-authorization-matrix.md` — required
- `governance/registry-governance.md` — **excludable** (peer may not host a registry)
- `governance/federated-contribution-model.md` — **excludable** (peer may not accept federation contributions)

### 5.6 Observability (required minima)

- `observability/audit-provenance-observability.md` — required
- `observability/universal-audit.md` — required
- `observability/universal-groups.md` — required

### 5.7 Topology and design principles

- `topology/location-topology-layers.md` — required (the layered-topology contract; specific hierarchies are realization choice)
- `design-principles/design-priorities.md` — required (the four principles as contracts)
- `design-principles/infrastructure-optimization.md` — required (the data-contract principle; persistence required, technology is realization choice)

### 5.8 Reference

- `reference/standards-catalog.md` — required as the normative external-standards basis

---

## 6. Wire-compatibility checklist

Consolidated MUSTs from all wire-compat contract docs. A conformant realization
MUST satisfy every item.

### Identifiers ([`identifier-scheme.md`](contracts/identifier-scheme.md))

- [ ] UUIDs use RFC 9562 canonical form (lowercase hyphenated; RFC 4122 citations read as 9562)
- [ ] UUIDv4 for identity; UUIDv7 ONLY for declared time-ordered fields; v1/v3/v5/v6/v8 REJECTED at ingest (version nibble + variant bits checked)
- [ ] Handles match `[a-z0-9][a-z0-9-]{0,61}[a-z0-9]` with namespace pattern
- [ ] References include `ref_type` and `uuid`; `uuid` is authoritative, `handle` advisory — resolution never by name alone
- [ ] Identifier reassignment is rejected; uuids are never reused after decommission
- [ ] Handle changes are audited

### Time ([`time-and-clock.md`](contracts/time-and-clock.md))

- [ ] All wire timestamps are UTC, ISO 8601, millisecond precision, `Z` suffix
- [ ] Skew ≤±5 seconds from peers
- [ ] Future timestamps >5s ahead are rejected
- [ ] Leap-second smearing in use
- [ ] Total ordering via `(timestamp, sequence_uuid)` available

### Errors ([`error-model.md`](contracts/error-model.md))

- [ ] Error envelope schema matches §2 exactly
- [ ] Error codes drawn from closed vocabulary or declared extensions
- [ ] `retryable` flag set correctly per code definitions
- [ ] `request_id` and `audit_uuid` present in every error
- [ ] HTTP status mapping per §3.2 for HTTP transports

### Events ([`event-catalog.md`](contracts/event-catalog.md))

- [ ] Event envelope schema matches the catalog
- [ ] Event timestamps set by commit log, not emitter
- [ ] `event_uuid` enables idempotent processing

### Retries ([`retry-semantics.md`](contracts/retry-semantics.md))

- [ ] `retryable: false` is never retried
- [ ] `retry_after_seconds` honored
- [ ] Idempotency-Key preserved across attempts
- [ ] Exponential backoff with jitter within prescribed bounds
- [ ] Per-operation budget enforced (5 attempts / 6 total)

### Rate limits ([`rate-limit-and-backpressure.md`](contracts/rate-limit-and-backpressure.md))

- [ ] Rate-limit declarations published via capability discovery
- [ ] `rate_limit.exceeded` with `retry_after_seconds` on overflow
- [ ] `Retry-After` HTTP header on HTTP transports
- [ ] Per-scope fairness enforced

### Schema sharing ([`schema-sharing.md`](contracts/schema-sharing.md))

- [ ] Schema bundle published at `/.well-known/udlm/schema-bundle`
- [ ] JSON Schema Draft 2020-12 for all schemas
- [ ] Per-schema URLs immutable for `(id, version)` tuples
- [ ] Version negotiation honors semver
- [ ] Unknown-type data triggers schema fetch or graceful degradation

### Conformance declaration (this doc)

- [ ] Declaration published at `/.well-known/udlm/conformance`
- [ ] Declaration matches §4 schema exactly
- [ ] Exclusions enumerated for partial conformance
- [ ] Excluded features respond with `conformance.feature_not_implemented`

---

## 7. New error code added by this contract

This document adds one error code namespace to the closed vocabulary:

| Code | Retryable | HTTP status |
|---|---|---|
| `conformance.feature_not_implemented` | no | 501 |
| `conformance.version_unsupported` | no | 409 |
| `conformance.declaration_unavailable` | yes (transient retrieval failure) | 503 |

These extend the error vocabulary in [`error-model.md`](contracts/error-model.md).
The `error-model.md` doc SHOULD be updated to include the `conformance.*`
namespace in its closed vocabulary at next revision.

---

## 8. Test suite

Conformance is verified by the udlm conformance test suite. The suite:

- Is specified in [`tests/test-framework-specification.md`](tests/test-framework-specification.md).
- Is executable: it issues operations against a realization's interop surfaces
  and validates responses against the contracts.
- Is versioned with the udlm spec — test suite version maps to udlm version.
- Covers every checklist item in §6.

Realizations MUST run the test suite as part of self-certification. The test
suite version is recorded in the conformance declaration
(`conformance_test_suite_version`).

A realization MAY undergo **independent verification** by a third-party
verifier. Independent verification:

- Runs the same test suite from outside the realization's trust boundary.
- Produces a verification report linked from the conformance declaration.
- Carries more weight for peers evaluating whether to federate.

---

## 9. Versioning and compatibility windows

### 9.1 udlm versioning

udlm follows semver:

- **Major** (1.x → 2.x): backward-incompatible changes to required contracts.
- **Minor** (1.0 → 1.1): backward-compatible additions (new optional contracts,
  new error codes within existing namespaces, new fields with safe defaults).
- **Patch** (1.0.0 → 1.0.1): documentation, examples, clarifications. No
  conformance impact.

### 9.2 Compatibility windows

- Two realizations conformant to the **same major version** of udlm are
  wire-compatible. Schema version negotiation per
  [`schema-sharing.md`](contracts/schema-sharing.md) handles minor-version
  differences.
- Cross-major-version interoperation is NOT guaranteed. Realizations MAY
  support multiple major versions concurrently by publishing schemas and
  conformance declarations for each.
- A realization deprecating support for an older major version MUST give peers
  at least **6 months** notice via federation events
  (`conformance.version_deprecated`).

### 9.3 Deprecation policy

- Contracts deprecated in a minor version remain functional until the next
  major version.
- Deprecation is signaled in the schema bundle and conformance declaration.
- Peers SHOULD migrate before the major version transition.

---

## 10. Self-certification process

A realization claiming conformance follows this process:

1. **Implement** the required contracts per §5.
2. **Publish** schema bundle, capability declarations, and conformance
   declaration at the well-known endpoints.
3. **Run** the conformance test suite against the running realization.
4. **Record** the test results, suite version, and timestamp in the conformance
   declaration.
5. **Make public** the conformance declaration URL so peers can verify before
   federating.
6. **Re-run** the test suite after any change affecting interop surfaces. Update
   the `self_certified_at` timestamp.

Self-certification is the baseline. Independent verification (§8) is stronger
but optional.

---

## 11. Peer verification flow

Before federating, a peer SHOULD:

1. Fetch the remote realization's conformance declaration.
2. Verify `udlm_version` is compatible with the local realization's version.
3. Check `level` and `exclusions` against the features needed for the planned
   federation.
4. Optionally verify `independent_verification.report_url` for third-party
   validation.
5. Fetch the remote schema bundle and cache it.
6. Proceed with federation per the relevant contracts.

If any check fails, the peer MUST refuse federation with the appropriate
error (`conformance.version_unsupported`, `conformance.feature_not_implemented`,
or `federation.peer_version_incompatible`).

---

## 12. Conformance state and reporting

The conformance state of a realization is **public** by design. Peers and
operators can:

- Fetch `/.well-known/udlm/conformance` at any time.
- Subscribe to the `conformance.*` federation events (see
  [`event-catalog.md`](contracts/event-catalog.md)) for change notifications.
- Compare independent verification reports across realizations.

A realization MUST NOT misrepresent its conformance state. False claims are
detectable by running the test suite; verifiers MAY publish discrepancies.

---

## 13. Related documents

- [`contracts/identifier-scheme.md`](contracts/identifier-scheme.md)
- [`contracts/time-and-clock.md`](contracts/time-and-clock.md)
- [`contracts/error-model.md`](contracts/error-model.md)
- [`contracts/retry-semantics.md`](contracts/retry-semantics.md)
- [`contracts/rate-limit-and-backpressure.md`](contracts/rate-limit-and-backpressure.md)
- [`contracts/schema-sharing.md`](contracts/schema-sharing.md)
- [`contracts/event-catalog.md`](contracts/event-catalog.md)
- [`contracts/provider-contract.md`](contracts/provider-contract.md)
- [`contracts/policy-contract.md`](contracts/policy-contract.md)
- [`tests/test-framework-specification.md`](tests/test-framework-specification.md) — the conformance test suite
- [`foundations/layering-and-versioning.md`](foundations/layering-and-versioning.md) — semver basis
