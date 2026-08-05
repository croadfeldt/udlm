# UDLM — Universal Data Lifecycle Model

UDLM is a wire-compatible substrate for systems that manage data through its
lifecycle from intent to realization. Any system conformant to UDLM produces
data that any other conformant system can read, interpret, and exchange.

> **Working with UDLM?** Start at **[`docs/guides/working-with-udlm.md`](docs/guides/working-with-udlm.md)** — it
> routes you by what you're here to do: author an artifact, review a contribution, build a system that
> consumes the model, or contribute to the project.

## Layers

UDLM is the substrate layer. Above it sit **implementations** — operational
platforms that consume UDLM and turn it into a running system. The reference
implementation is **DCM** (`github.com/dcm-project/dcm`), but UDLM is implementation-
neutral: any operational platform that honors the UDLM interfaces is a peer.
Named implementations (DCM for the Resource family, DAV for the Knowledge family)
are **non-normative examples** — UDLM's definition, validation, and use depend
on none of them. Term definitions: [`GLOSSARY.md`](GLOSSARY.md).

## Structure

```
udlm/
├── CONFORMANCE.md           What a conformant implementation must provide
├── docs/
│   ├── spec/                THE normative tier — what ratification covers
│   │   ├── foundations/       Core model: four states, entity types/families,
│   │   │                      entities, layering, ownership, groups, topology
│   │   ├── contracts/         Wire contracts: identifier, time, error, retry,
│   │   │                      events, provider/policy/data-store, audit
│   │   ├── governance/        Auth, registry governance, governance matrix,
│   │   │                      accreditation, credentials, authority tiers
│   │   ├── lifecycle/         Ingestion, operational models, subscriptions
│   │   └── principles/        Core tenets, priorities, adopted standards
│   ├── adr/  design/  authoring/  flows/  guides/  examples/  research/
│   └── file-index.md        Per-file ownership index
├── registry/                Resource Type Registry — meta-schemas, the authored
│                            classes/, generated flat specs, instances, tooling
├── use-cases/               The CI-consumed coverage corpus
├── tests/                   The gate suite
└── scripts/                 signoff and tooling
```

For a per-file breakdown — what each document *owns*, so a rule lives in exactly one place — see [`docs/file-index.md`](docs/file-index.md).

## Conformance

An implementation that claims UDLM conformance:

1. Implements every required contract in `docs/spec/` (foundations, contracts,
   lifecycle, governance, principles).
2. Publishes a schema bundle at `/.well-known/udlm/schema-bundle` per
   [`docs/spec/contracts/schema-sharing.md`](docs/spec/contracts/schema-sharing.md).
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

Post-1.0, UDLM follows semver: two implementations conformant to the same major version are
wire-compatible, and cross-major interop requires a peer to support multiple majors
concurrently. See [`CONFORMANCE.md`](CONFORMANCE.md) §9.

## License

UDLM is licensed under the **Apache License 2.0** — see [`LICENSE`](LICENSE). This is the
project's single license declaration; other documents (e.g.
[`docs/spec/principles/adopted-standards.md`](docs/spec/principles/adopted-standards.md)) reference
it rather than restating it.

## Provenance

UDLM was extracted from the DCM repository's `architecture/data-model/`
directory in May 2026. Git history is preserved for files that originated
there. New substrate contracts (identifier-scheme, time-and-clock, error-model,
retry-semantics, rate-limit-and-backpressure, schema-sharing, CONFORMANCE)
were authored fresh during the split to make wire-compatibility explicit.

The split planning record lives in the DCM repo at
`architecture/00-split-manifest.md`.
