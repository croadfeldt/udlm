# UDLM — Universal Data Lifecycle Model

UDLM is a wire-compatible substrate for systems that manage data through its
lifecycle from intent to realization. Any system conformant to UDLM produces
data that any other conformant system can read, interpret, and exchange.

## Layers

UDLM is the substrate layer. Above it sit **realizations** — operational
platforms that consume UDLM and turn it into a running system. The reference
realization is **DCM** (`github.com/croadfeldt/dcm`), but UDLM is realization-
neutral: any operational platform that honors the UDLM contracts is a peer.

## Structure

```
udlm/
├── CONFORMANCE.md           What a conformant realization must provide
├── foundations/             Context, entity types, four-state lifecycle
├── entities/                Resource and service entity model
├── contracts/               Wire-compatibility contracts (identifier, time,
│                            error, retry, rate-limit, schema-sharing, events,
│                            provider/policy/data-store contracts, etc.)
├── lifecycle/               Lifecycle contracts (ingestion, operational
│                            models, scheduling, dependency graphs, subscriptions)
├── governance/              Auth, registry, governance matrix, accreditation,
│                            federated contribution, credentials, authority tiers
├── observability/           Audit, provenance, observability contracts
├── topology/                Layered-topology contract
├── design-principles/       Substrate design principles
├── reference/               Normative external standards cited
├── docs/                    Narrative perspectives (consumer handbook)
└── tests/                   Test framework specification
```

## Conformance

A realization that claims UDLM conformance:

1. Implements every required contract in `contracts/`, `foundations/`,
   `entities/`, `lifecycle/`, `governance/`, `observability/`, `topology/`,
   `design-principles/`, `reference/`.
2. Publishes a schema bundle at `/.well-known/udlm/schema-bundle` per
   [`contracts/schema-sharing.md`](contracts/schema-sharing.md).
3. Publishes a conformance declaration at `/.well-known/udlm/conformance`
   per [`CONFORMANCE.md`](CONFORMANCE.md).
4. Passes the conformance test suite per
   [`tests/test-framework-specification.md`](tests/test-framework-specification.md).

See [`CONFORMANCE.md`](CONFORMANCE.md) for full details.

## Versioning

UDLM follows semver. Two realizations conformant to the same major version
are wire-compatible. Cross-major-version interop requires a peer to support
multiple major versions concurrently. See [`CONFORMANCE.md`](CONFORMANCE.md) §9.

## Provenance

UDLM was extracted from the DCM repository's `architecture/data-model/`
directory in May 2026. Git history is preserved for files that originated
there. New substrate contracts (identifier-scheme, time-and-clock, error-model,
retry-semantics, rate-limit-and-backpressure, schema-sharing, CONFORMANCE)
were authored fresh during the split to make wire-compatibility explicit.

The split planning record lives in the DCM repo at
`architecture/00-split-manifest.md`.
