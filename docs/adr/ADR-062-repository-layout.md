# ADR-062: Repository layout — prose is docs, the normative tier is a path prefix

**Status:** Proposed
**Realized by:** _not yet_ — decided, no machine surface.
**Date:** 2026-08-04

**Background — read first (the cold reader's on-ramp; skip if you have the context).**
[ADR-061](ADR-061-class-directory-hierarchy.md) — the same path-as-verified-projection
discipline this ADR extends from class records to documents; the engineering ratification pass
(#217) — the process whose surface this layout makes a single path expression;
[`docs/file-index.md`](../file-index.md) — the per-file ownership index the layout composes
with.

## Context

The repository had grown fifteen top-level directories: seven normative prose
directories as peers (foundations, entities, contracts, governance, lifecycle,
observability, design-principles), three single-file or near-empty stragglers
(reference, topology, examples), a `docs/` tree mixing four different roles, and
the machine surfaces. Which directories were normative — what engineering
ratification (#217) actually covers — was tribal knowledge, not structure.

## Decision

Three rules decide where everything lives:

1. **Prose lives under `docs/`.** Everything a human reads is one tree,
   organized by role. The normative tier is the path prefix **`docs/spec/`** —
   ratification covers exactly `docs/spec/` + `registry/`; everything beside
   `spec/` (`adr/`, `design/`, `authoring/`, `flows/`, `guides/`, `examples/`,
   `research/`) is commentary and never the contract.
2. **A directory must earn its existence.** Single-file directories dissolve
   into their logical home; a directory whose contents split by nature splits
   (`observability/`: the group model is foundations, the audit contracts are
   contracts). Substructure is added when a directory's contents demand it, not
   pre-emptively.
3. **Machine surfaces and corpora stay out of `docs/`**: `registry/` (schemas,
   classes, generated specs, instances, tooling), `use-cases/` (the CI-consumed
   coverage corpus), `tests/`, `scripts/`.

The resulting top level is five directories — `docs/`, `registry/`,
`use-cases/`, `tests/`, `scripts/` — plus the root entry points (`README.md`,
`GLOSSARY.md`, `CONFORMANCE.md`, `AGENTS.md`, `CONTRIBUTING.md`, `LICENSE`).

Inside `docs/spec/`: `foundations/` (the core model — four states, entity
types and families, the entity deep-dives, layering, ownership, groups,
topology), `contracts/` (every wire contract, including audit),
`governance/`, `lifecycle/`, and `principles/` (formerly `design-principles/`
— they are spec tenets, not design notes).

## Consequences

- The ratification surface is one path expression. A document's standing —
  contract or commentary — is readable from its path, the same property
  ADR-061 gives class records.
- Rule homes in `registry/rule-id-registry.yaml` and every cross-reference
  moved with the files; `tests/check_links.py` plus a code-span grep sweep
  verify the rewrite (the link checker does not parse code-span paths).
- `docs/guides/` collects the contributor/consumer handbooks that sat loose at
  the `docs/` root; `docs/file-index.md` stays at the root of `docs/` as the
  ownership index.
- `registry/standards-catalog.md` (from `reference/`) now sits beside
  `standards-adoption-register.md`; whether the two collapse into one is a
  content question, deliberately out of scope here.
