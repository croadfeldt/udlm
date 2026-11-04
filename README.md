# UDLM — Universal Data Lifecycle Model

UDLM is a wire-compatible substrate for systems that manage data through its
lifecycle from intent to realization. Any system conformant to UDLM produces
data that any other conformant system can read, interpret, and exchange.

## Start here

1. **[`docs/start-here/`](docs/start-here/README.md)** — the slow walk: one short step at a time,
   each ending with a command that proves it worked. Start here if the model is new to you.
2. **[`docs/guides/quickstart.md`](docs/guides/quickstart.md)** — the fast version: one VM followed
   through its four records in ten minutes; every step names the file to open.
3. **[`docs/spec/foundations/class-tiers.md`](docs/spec/foundations/class-tiers.md)** — the class system:
   Base, Type and Provider Class, and how where an element sits decides how portable it is.
4. **[`docs/spec/foundations/four-states.md`](docs/spec/foundations/four-states.md)** — the records:
   intent, requested, realized, discovered.
5. **[`docs/guides/working-with-udlm.md`](docs/guides/working-with-udlm.md)** — then go by role: author,
   reviewer, system builder, contributor.
6. **[`docs/guides/co-engineering.md`](docs/guides/co-engineering.md)** — joining from another
   organization: what to read, how to check your own records, how to change the spec, how decisions
   are made.
7. **[`docs/guides/udlm-0.1-engineering-handoff.md`](docs/guides/udlm-0.1-engineering-handoff.md)** — the
   engineering handoff: what is experimental, what is known open, how to check your work.

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
4. Runs the conformance test suite, `tests/conformance.py`, against the records it writes
   ([`CONFORMANCE.md`](CONFORMANCE.md) §8).

See [`CONFORMANCE.md`](CONFORMANCE.md) for full details.

## Versioning

**UDLM is `udlm/1.0`, at release candidate `udlm/1.0-rc1`.** 1.0 fixes the framework: the
version law, the four records and the class tiers, the conformance suite and the graduation
ladder. It declares no part stable: every part is experimental until a running implementation
has used it and the suite has judged its records ([`registry/stability.yaml`](registry/stability.yaml)).
The wire-compatibility promise applies to a part once it is stable. See
[`registry/VERSIONING.md`](registry/VERSIONING.md) for the two version axes (SPEC vs ENTITY).

The path to the tag is [`registry/UDLM-1.0-LOCKDOWN.md`](registry/UDLM-1.0-LOCKDOWN.md): the
surface is frozen, the open issues are binned into blockers and 1.x, and the cut follows the
exit criteria there.

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

The split planning record is architecture/00-split-manifest.md in the DCM repo.
