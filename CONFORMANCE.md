# UDLM — Conformance Specification

**Draft** — pre-ratification (#217); the wire-compat promise binds at 1.0.
**Established:** 2026-05-26
**Maps to:** DATA (umbrella)

> Defines what an implementation MUST implement to be **udlm-conformant**. A
> conformant implementation is wire-compatible with any other conformant
> implementation of the same major udlm version — its data can be read, its
> events can be parsed, its contracts can be honored by peers without
> per-implementation adapters. This document is the conformance surface that
> an independent verifier tests against.

---

## 1. Conformance commitment and document purpose

### 1.1 The conformance commitment

A peer implementation that claims udlm conformance commits to:

- Producing data, events, and errors that any other conformant peer can
  deserialize and act on.
- Honoring the interface specifications in `docs/spec/` — contracts, lifecycle,
  governance, foundations (UDLM reserves the word
  *[contract](GLOSSARY.md)* for exactly these specs).
- Publishing schemas, capabilities, and a conformance declaration via the
  [schema-sharing protocol](docs/spec/contracts/schema-sharing.md) (the schema bundle at
  `/.well-known/udlm/schema-bundle`, consolidated in §6) so peers can discover
  compatibility.
- Maintaining versioning discipline so peers can negotiate.

### 1.2 Purpose of this document

This document defines the conformance surface in one place. Each individual
contract doc carries its own validation rules; CONFORMANCE.md consolidates them
and adds the meta-rules (declaration format, versioning, certification).

> **Transport binding.** The conformance and schema surfaces defined here — the
> conformance declaration, the schema bundle, and the error/event envelopes —
> are **transport-agnostic**. **HTTP is the normative v1 binding**: the
> `/.well-known/udlm/...` paths and the §3.2 status mapping are the HTTP binding
> of these surfaces, not a requirement that HTTP be the only transport. Other
> bindings MAY be defined in later versions; the HTTP-specific rules (well-known
> paths, status mapping, `Retry-After` header) apply only to peers using the
> HTTP binding.

---

## 2. What conformance certifies

Conformance certifies **wire-level interoperability** within a major udlm
version. Specifically, a conformant implementation:

| Certifies | Does NOT certify |
|---|---|
| Wire-compatible data exchange with peers | Implementation portability across implementations |
| Schema-compatible extensions via schema-sharing | Internal storage, APIs, or runtime mechanics |
| Closed-vocabulary errors and codes on interop surfaces | Operational performance, scale, or reliability |
| Conformant identifier, timestamp, and event formats | Specific deployment topology |
| Honoring the lifecycle state machine | UX, ergonomics, or operator tooling |

Two conformant implementations with disjoint runtime implementations can federate
and exchange data; they cannot necessarily swap controllers or share storage.

Requiring a document in [§5](#5-required-contracts) — including
`docs/spec/principles/design-priorities.md` and
`docs/spec/principles/data-contracts.md` — means requiring its **data
contracts** (append-only, versioning, tamper-evidence, tenant isolation, the
four design principles as constraints), **not** certifying storage technology,
internal APIs, or runtime mechanics. Contracts are certified; mechanics are not.

---

## 3. Conformance levels

### 3.1 Full Conformance

Implements every required contract listed in [§5](#5-required-contracts).
Publishes a conformance declaration with `level: "full"` and no exclusions.

### 3.2 Declared Partial Conformance

Implements a documented subset of required contracts. The implementation MUST:

- Publish a conformance declaration with `level: "partial"`.
- Enumerate excluded contracts in the `exclusions` field.
- Reject operations on excluded features with `conformance.feature_not_implemented`
  (see [§7](#7-new-error-code-added-by-this-contract)).
- NOT silently fail or partially implement an excluded contract.

A peer interacting with a partially-conformant implementation MUST check the
conformance declaration before depending on an excluded feature.

### 3.3 Conformance with Extensions

Implements full conformance AND publishes extensions (custom resource types,
custom event types, custom credential types, etc.) via the schema-sharing
protocol. Extensions MUST:

- Be published in the implementation's schema bundle.
- Use only allowed extension points (e.g., custom resource types within the
  resource type registry, not redefinitions of core types).
- Not break existing contracts.

Full Conformance and Conformance with Extensions are not separate levels in
the declaration; the latter is signaled by the presence of `extensions` in
the schema bundle.

---

## 4. Conformance declaration

Every conformant implementation MUST publish a conformance declaration. Over the
HTTP binding (the normative v1 binding — see the transport-binding note in §1)
it is served at:

```
GET /.well-known/udlm/conformance
```

### 4.1 Declaration schema

The declaration body (the JSON response served at the endpoint above) has the
following shape:

```json
{
  "implementation": {
    "name": "example-implementation",
    "vendor": "example-org",
    "version": "1.4.2"
  },
  "udlm_version": "0.1.0",
  "profile": "standard",
  "level": "full",
  "exclusions": [],
  "extensions_published": true,
  "schema_bundle_url": "/.well-known/udlm/schema-bundle",
  "interop_surfaces": {
    "consumer_api": { "available": true, "transport": "http", "base_url": "https://example-implementation/api/v1" },
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
| `implementation` | yes | Self-identification |
| `udlm_version` | yes | udlm semver this implementation conforms to |
| `profile` | yes | The implementation's active **base profile** (from the [profile vocabulary](docs/spec/principles/design-priorities.md)). In v1 a profile is advertised **platform-wide** (one active base profile per deployment); the model is designed to become **group-scopable** later (bound to a tenant/service/domain) — see the profile-scope note in [foundations.md](docs/spec/foundations/foundations.md) and [ADR-007](docs/adr/ADR-007-profile-model.md). `fsi`/`sovereign` compose as overlays on the base profile. |
| `level` | yes | `"full"` or `"partial"` |
| `exclusions` | required if level=partial | List of contract names not implemented |
| `extensions_published` | yes | Whether schema bundle includes extensions |
| `schema_bundle_url` | yes | Where to fetch the schema bundle |
| `interop_surfaces` | yes | Which surfaces are available and how to reach them |
| `leap_second_strategy` | yes | The peer's **declared** leap-second handling, drawn from the named, open set defined in [`time-and-clock.md`](docs/spec/contracts/time-and-clock.md) §8 (e.g. `smear`, `step`). A monotonic clock is **required**; smearing is **recommended**. The peer states its strategy rather than being forced to a single one. |
| `auth_mechanism_for_schema_endpoints` | yes | How peers authenticate to fetch schemas |
| `conformance_test_suite_version` | yes | Which version of the test suite (see §8) was run |
| `self_certified_at` | yes | RFC 3339 UTC; when self-certification was performed |
| `independent_verification` | optional | Present if an independent verifier has validated |

### 4.3 Declaring multiple major versions

An implementation MAY conform to more than one major udlm version concurrently
(see [§9.2](#92-compatibility-windows)). The conformance declaration is a
**single document** that expresses **all** supported majors: its top-level
`declarations` field is a list of per-major declaration objects, each object
carrying the §4.1 shape (`udlm_version`, `profile`, `level`, `exclusions`,
`interop_surfaces`, and the rest). An implementation that supports exactly one major
MAY serve the bare §4.1 object directly.

Whether that single document is served at one `/.well-known/udlm/conformance`
path or split across per-major paths is a **implementation choice at the HTTP
binding** (§1), not part of the data model. The **v1 HTTP binding is one path**:
`GET /.well-known/udlm/conformance` returns the multi-version document.

---

## 5. Required contracts

A Full Conformance implementation MUST implement every contract below. Each
contract is either **required (not excludable)** or **excludable (must
declare)** — a partial-conformance implementation MAY omit an excludable contract
only if it enumerates the exclusion in its declaration (§3.2).

> Resource and entity **types** referenced by these contracts are defined
> canonically in the [registry](registry) — the Resource Type Specifications
> and the meta-schema. The contracts below bind their *behavior*; the registry
> is where the type members live.

### 5.1 Foundations (required — not excludable)

- `docs/spec/foundations/context-and-purpose.md`
- `docs/spec/foundations/data-model-core.md` — the settled core decisions ([D1]-[D9]: edge model, status conditions, derived shape)
- `docs/spec/foundations/foundations.md`
- `docs/spec/foundations/entity-types.md`
- `docs/spec/foundations/four-states.md` — the four-state lifecycle is non-negotiable
- `docs/spec/foundations/layering-and-versioning.md`
- `docs/spec/foundations/ownership-sharing-allocation.md`

### 5.2 Wire-compatibility contracts (required — not excludable)

These are the contracts that make wire-compatibility work. Excluding any of
them disqualifies the implementation from any conformance level.

- `docs/spec/contracts/identifier-scheme.md`
- `docs/spec/contracts/time-and-clock.md`
- `docs/spec/contracts/error-model.md`
- `docs/spec/contracts/event-catalog.md`
- `docs/spec/contracts/schema-sharing.md`

### 5.3 Operational contracts (required — not excludable)

- `docs/spec/contracts/retry-semantics.md`
- `docs/spec/contracts/rate-limit-and-backpressure.md`
- `docs/spec/contracts/provider-contract.md`
- `docs/spec/contracts/policy-contract.md`
- `docs/spec/contracts/data-store-contracts.md`

### 5.4 Entity and lifecycle contracts (required and excludable)

- `docs/spec/foundations/resource-service-entities.md` — required (not excludable)
- `docs/spec/foundations/resource-type-hierarchy.md` — required (not excludable)
- `docs/spec/foundations/entity-relationships.md` — required (not excludable)
- `docs/spec/lifecycle/operational-models.md` — required (not excludable)
- `docs/spec/foundations/composite-service-model.md` — **excludable (must declare)**
- `docs/spec/lifecycle/scheduled-requests.md` — **excludable (must declare)**
- `docs/spec/lifecycle/request-dependency-graph.md` — **excludable (must declare)**
- `docs/spec/lifecycle/subscription-lifecycle.md` — **excludable (must declare)**
- `docs/spec/lifecycle/ingestion-model.md` — **excludable (must declare)** (peer may not support brownfield)

### 5.5 Governance contracts (required and excludable)

- `docs/spec/governance/governance-matrix.md` — required (not excludable)
- `docs/spec/governance/auth-providers.md` — required (not excludable; at least one auth mode)
- `docs/spec/governance/credentials.md` — required (not excludable)
- `docs/spec/governance/authority-tier-model.md` — required (not excludable)
- `docs/spec/governance/accreditation-and-authorization-matrix.md` — required (not excludable)
- `docs/spec/governance/registry-governance.md` — **excludable (must declare)** (peer may not host a registry)
- `docs/spec/governance/federated-contribution-model.md` — **excludable (must declare)** (peer may not accept federation contributions)

### 5.6 Observability (required — not excludable)

- `docs/spec/contracts/audit-provenance-observability.md` — required (not excludable)
- `docs/spec/contracts/universal-audit.md` — required (not excludable)
- `docs/spec/foundations/universal-groups.md` — required (not excludable)

### 5.7 Topology and design principles

- `docs/spec/foundations/location-topology-layers.md` — required (the layered-topology contract; specific hierarchies are implementation choice)
- `docs/spec/principles/design-priorities.md` — required (the four principles as contracts)
- `docs/spec/principles/data-contracts.md` — required (the data-contract principle; persistence required, technology is implementation choice)

### 5.8 Reference

- `registry/standards-catalog.md` — required as the normative external-standards basis

---

## 6. Wire-compatibility checklist

Consolidated MUSTs from all wire-compat contract docs. A conformant implementation
MUST satisfy every item.

### Identifiers ([`identifier-scheme.md`](docs/spec/contracts/identifier-scheme.md))

- [ ] UUIDs use RFC 9562 canonical form (lowercase hyphenated)
- [ ] UUIDv4 for identity; UUIDv7 ONLY for declared time-ordered fields; v1/v3/v5/v6/v8 REJECTED at ingest (version nibble + variant bits checked)
- [ ] Handles match `[a-z0-9][a-z0-9-]{0,61}[a-z0-9]` with namespace pattern
- [ ] References include `ref_type` and `uuid`; `uuid` is authoritative, `handle` advisory — resolution never by name alone
- [ ] Identifier reassignment is rejected; uuids are never reused after decommission
- [ ] Handle changes are audited

### Time ([`time-and-clock.md`](docs/spec/contracts/time-and-clock.md))

- [ ] All wire timestamps are UTC, ISO 8601, millisecond precision, `Z` suffix
- [ ] Skew ≤±5 seconds from peers
- [ ] Future timestamps >5s ahead are rejected
- [ ] Leap-second strategy declared (monotonic clock required; smear recommended) per [`time-and-clock.md`](docs/spec/contracts/time-and-clock.md) §8
- [ ] Total ordering via `(timestamp, sequence_uuid)` available

### Errors ([`error-model.md`](docs/spec/contracts/error-model.md))

- [ ] Error envelope schema matches §2 exactly
- [ ] Error codes drawn from closed vocabulary or declared extensions
- [ ] `retryable` flag set correctly per code definitions
- [ ] `request_id` and `audit_uuid` present in every error
- [ ] HTTP status mapping per §3.2 for HTTP transports

### Events ([`event-catalog.md`](docs/spec/contracts/event-catalog.md))

- [ ] Event envelope schema matches the catalog
- [ ] Event timestamps set by commit log, not emitter
- [ ] `event_uuid` enables idempotent processing

### Retries ([`retry-semantics.md`](docs/spec/contracts/retry-semantics.md))

- [ ] `retryable: false` is never retried
- [ ] `retry_after_seconds` honored
- [ ] Idempotency-Key preserved across attempts
- [ ] Exponential backoff with jitter within prescribed bounds
- [ ] Per-operation budget enforced (5 attempts / 6 total)

### Rate limits ([`rate-limit-and-backpressure.md`](docs/spec/contracts/rate-limit-and-backpressure.md))

- [ ] Rate-limit declarations published via capability discovery
- [ ] `rate_limit.exceeded` with `retry_after_seconds` on overflow
- [ ] `Retry-After` HTTP header on HTTP transports
- [ ] Per-scope fairness enforced

### Schema sharing ([`schema-sharing.md`](docs/spec/contracts/schema-sharing.md))

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

The `conformance.*` codes are **defined here and registered into** the closed
error vocabulary in [`error-model.md`](docs/spec/contracts/error-model.md).

---

## 8. Test suite

Conformance is verified by the udlm conformance test suite. The suite:

- Is executable: it issues operations against an implementation's interop surfaces
  and validates responses against the contracts.
- Is versioned with the udlm spec — test suite version maps to udlm version.
- Covers every checklist item in §6.

> **Status — the suite is under construction, and this section states a commitment rather than
> a shipped artifact.** Read it as what an implementation will be asked to run, not as something
> it can run today.
>
> **What exists.** A corpus in `registry/examples/`, executed by CI on every change, in three
> parts: worked records that state the rule each demonstrates (`check_example_coverage.py`);
> a negative corpus of records that MUST be refused, which fails both when the model stops
> refusing one and when a case stops provoking the rule it names (`check_must_reject.py`); and
> per-rule gates the cases bind to. It validates **this repository's own records** — UDLM as its
> own first implementation.
>
> **What does not exist.** Anything a third party can run against their own implementation.
> Every gate here scans this tree. So the §6 checklist below is the assertion list a conformance
> suite must cover, and nothing yet executes it against an external implementation — which means
> `conformance_test_suite_version` in §4.1 cannot be populated honestly yet.
>
> This section previously cited `tests/test-framework-specification.md` as the suite's
> specification. That document specifies a different thing — an architecture fuzzer generating
> scenarios against DCM's pipeline, naming DCM's own tables — and mentions none of the seven wire
> contracts §6 draws from. The citation is removed rather than repointed: pointing a reader at an
> artifact that answers a different question is worse than pointing at nothing. Tracked at #417.

Implementations MUST run the test suite as part of self-certification. The test
suite version is recorded in the conformance declaration
(`conformance_test_suite_version`).

An implementation MAY undergo **independent verification** by a third-party
verifier. Independent verification:

- Runs the same test suite from outside the implementation's trust boundary.
- Produces a verification report linked from the conformance declaration.
- Carries more weight for peers evaluating whether to federate.

**Certification progression.** Self-certification is the **v0 baseline** — a
implementation runs the suite and records the suite version and results in its
declaration. Independent verification is **optional at 0.x** but **carries more
weight** for peers deciding whether to federate. A **required run of the shared
certified suite** is the **1.0 conformance bar**: at 1.0, self-certification
alone no longer suffices for a full conformance claim. This is a deliberate
escalation, not "self-signed forever."

---

## 9. Versioning and compatibility windows

### 9.1 udlm versioning

udlm follows semver — the two-axis (SPEC / ENTITY) definition is owned by [`registry/VERSIONING.md`](registry/VERSIONING.md); this section states only the **conformance** implication of the SPEC major axis:

- **Major** (1.x → 2.x): backward-incompatible changes to required contracts.
- **Minor** (1.0 → 1.1): backward-compatible additions (new optional contracts,
  new error codes within existing namespaces, new fields with safe defaults).
- **Patch** (1.0.0 → 1.0.1): documentation, examples, clarifications. No
  conformance impact.

### 9.2 Compatibility windows

- Two implementations conformant to the **same major version** of udlm are
  wire-compatible. Schema version negotiation per
  [`schema-sharing.md`](docs/spec/contracts/schema-sharing.md) handles minor-version
  differences.
- Cross-major-version interoperation is NOT guaranteed. Implementations MAY
  support multiple major versions concurrently by publishing schemas for each
  and expressing every supported major in the single conformance declaration
  (see [§4.3](#43-declaring-multiple-major-versions)).
- An implementation deprecating support for an older major version MUST give peers
  at least **6 months** notice via federation events
  (`conformance.version_deprecated`; see [`event-catalog.md`](docs/spec/contracts/event-catalog.md)).

### 9.3 Deprecation policy

- Contracts deprecated in a minor version remain functional until the next
  major version.
- Deprecation is signaled in the schema bundle and conformance declaration.
- Peers SHOULD migrate before the major version transition.

---

## 10. Self-certification process

An implementation claiming conformance follows this process:

1. **Implement** the required contracts per §5.
2. **Publish** schema bundle, capability declarations, and conformance
   declaration at the well-known endpoints.
3. **Run** the conformance test suite against the running implementation.
4. **Record** the test results, suite version, and timestamp in the conformance
   declaration.
5. **Make public** the conformance declaration URL so peers can verify before
   federating.
6. **Re-run** the test suite after any change affecting interop surfaces. Update
   the `self_certified_at` timestamp.

Self-certification is the v0 baseline. Independent verification
([§8](#8-test-suite)) is stronger but optional at 0.x, and a required certified-
suite run becomes the 1.0 bar (see the certification progression in §8).

---

## 11. Peer verification flow

Before federating, a peer SHOULD:

1. Fetch the remote implementation's conformance declaration.
2. Verify `udlm_version` is compatible with the local implementation's version.
3. Check `profile` compatibility — confirm the remote's advertised base profile
   (and any overlays) satisfies local policy for federation (e.g. a `sovereign`
   peer may refuse to federate with a `homelab` peer).
4. Check `level` and `exclusions` against the features needed for the planned
   federation.
5. For each interop surface the federation will use, confirm that surface's
   `available` flag (and its declared transport/auth) in the remote
   `interop_surfaces`; if a required surface is unavailable, refuse with
   `conformance.feature_not_implemented`.
6. Optionally verify `independent_verification.report_url` for third-party
   validation.
7. Fetch the remote schema bundle and cache it.
8. Proceed with federation per the relevant contracts.

The substrate carries the **declaration and the compatibility check**; how a
implementation orchestrates the resulting federation is an implementation concern.

If any check fails, the peer MUST refuse federation with the appropriate
error (`conformance.version_unsupported`, `conformance.feature_not_implemented`,
or `federation.peer_version_incompatible`).

---

## 12. Conformance state and reporting

The conformance state of an implementation is **public** by design. Peers and
operators can:

- Fetch `/.well-known/udlm/conformance` at any time.
- Subscribe to the `conformance.*` federation events (see
  [`event-catalog.md`](docs/spec/contracts/event-catalog.md)) for change notifications.
- Compare independent verification reports across implementations.

An implementation MUST NOT misrepresent its conformance state. False claims are
detectable by running the test suite; verifiers MAY publish discrepancies.

---

## 13. Related documents

- [`docs/spec/contracts/identifier-scheme.md`](docs/spec/contracts/identifier-scheme.md)
- [`docs/spec/contracts/time-and-clock.md`](docs/spec/contracts/time-and-clock.md)
- [`docs/spec/contracts/error-model.md`](docs/spec/contracts/error-model.md)
- [`docs/spec/contracts/retry-semantics.md`](docs/spec/contracts/retry-semantics.md)
- [`docs/spec/contracts/rate-limit-and-backpressure.md`](docs/spec/contracts/rate-limit-and-backpressure.md)
- [`docs/spec/contracts/schema-sharing.md`](docs/spec/contracts/schema-sharing.md)
- [`docs/spec/contracts/event-catalog.md`](docs/spec/contracts/event-catalog.md)
- [`docs/spec/contracts/provider-contract.md`](docs/spec/contracts/provider-contract.md)
- [`docs/spec/contracts/policy-contract.md`](docs/spec/contracts/policy-contract.md)
- [`tests/test-framework-specification.md`](tests/test-framework-specification.md) — the conformance test suite
- [`docs/spec/foundations/data-model-core.md`](docs/spec/foundations/data-model-core.md) — the settled core decisions
- [`docs/spec/foundations/layering-and-versioning.md`](docs/spec/foundations/layering-and-versioning.md) — semver basis
