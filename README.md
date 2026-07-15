# UDLM — Universal Data Lifecycle Model

UDLM is a wire-compatible substrate for systems that manage data through its
lifecycle from intent to realization. Any system conformant to UDLM produces
data that any other conformant system can read, interpret, and exchange.

## Layers

UDLM is the substrate layer. Above it sit **realizations** — operational
platforms that consume UDLM and turn it into a running system. The reference
realization is **DCM** (`github.com/dcm-project/dcm`), but UDLM is realization-
neutral: any operational platform that honors the UDLM interfaces is a peer.
Named realizations (DCM for the Resource family, DAV for the Knowledge family)
are **non-normative examples** — UDLM's definition, validation, and use depend
on none of them. Term definitions: [`GLOSSARY.md`](GLOSSARY.md).

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
├── design-principles/       Substrate design principles (core tenets, adopted standards)
├── registry/                Resource Type Registry — the meta-schema, type/instance
│                            definitions, provider support matrices, validation tooling
├── reference/               Normative external standards cited
├── docs/                    Narrative perspectives (consumer handbook)
└── tests/                   Test framework specification
```

For a per-file breakdown — what each document *owns*, so a rule lives in exactly one place — see [`docs/file-index.md`](docs/file-index.md).

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

**UDLM is currently `udlm/0.1` — a pre-1.0 (`0.x`) release.** The surface is still being
defined, so per semver anything may change and the contract is **not yet stable**; current
work *expands* the v0.x surface rather than refining a released spec. `1.0` is the earned
milestone — cut when the surface is complete, the conformance suite passes, and the project
commits to backward compatibility. See [`registry/VERSIONING.md`](registry/VERSIONING.md) for
the two version axes (SPEC vs ENTITY) and the full positioning.

Post-1.0, UDLM follows semver: two realizations conformant to the same major version are
wire-compatible, and cross-major interop requires a peer to support multiple majors
concurrently. See [`CONFORMANCE.md`](CONFORMANCE.md) §9.

## License

UDLM is licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE). This is the
project's single license declaration; other documents (e.g.
[`design-principles/adopted-standards.md`](design-principles/adopted-standards.md)) reference
it rather than restating it.

## Provenance

UDLM was extracted from the DCM repository's `architecture/data-model/`
directory in May 2026. Git history is preserved for files that originated
there. New substrate contracts (identifier-scheme, time-and-clock, error-model,
retry-semantics, rate-limit-and-backpressure, schema-sharing, CONFORMANCE)
were authored fresh during the split to make wire-compatibility explicit.

The split planning record lives in the DCM repo at
`architecture/00-split-manifest.md`.
