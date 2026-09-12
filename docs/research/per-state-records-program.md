# The per-state records program: the series of changes that lands ruling 071

**What this is:** the ordered series of pull requests that takes the registry from one folded
instance record to one record per lifecycle state, as ruling 071 decided and
[the brief](per-state-records.md) argued. Each entry is one reviewable change with its content,
size, gates, and what it depends on. The brief is the evidence; this is the plan.

**The decisions this series applies.** The brief left five for review and recommended an answer
to each; the program started on those recommendations (maintainer, 2026-09-12), so they are
recorded here as settled unless overturned:

| Decision | Settled as |
|---|---|
| D1 — the identity of a record | `record_uuid` is a time-ordered UUID (v7); `entity_uuid` stays the stable v4 |
| D2 — the merged view | kept, renamed as an explicit read model assembled from the records and never written |
| D3 — how to record the decision | register row 071; no new ADR |
| D4 — sequencing | after the class-tier series; coordinated with the DCM control plane for the write path |
| D5 — `ownership` | dropped; one author per record leaves it no job |

One implementation choice differed from the brief and is recorded in PR 1: one closed schema
with four kinds rather than four schemas sharing an envelope, because the shared-envelope form
resolves through a path that ignores the offline schema store and fails CI. Same guarantees,
stronger closure.

## The series

### PR 1 — the stored form (#582)

| | |
|---|---|
| Content | the state-record schema under registry/ (added by #582): one envelope, four kinds, per-state rules, self-tested; validator dispatch and a coherence check; the four kinds registered as immutable with the identity gate; the four-state vocabulary given one home in `common-elements.schema.json`; `four-states.md` §2.7 in plain words; `REALIZED-ENTITY.md` marked a read model; one VM as three records under `registry/examples/`, the realized one sealed |
| Removes | nothing |
| Depends on | nothing |

### PR 2 — the examples and the gates that read them

| | |
|---|---|
| Content | the twelve worked examples in the folded shape become per-state records: an intent record and a realized record each, or the one record the example demonstrates. The four gates that read `states.realized` out of the folded document (`check_grant_derivation`, `check_group_invariants`, `check_offer_collapse`, `check_sovereignty_zones`) and the validator's `check_realized_entity` read the realized record instead. Each example keeps its `# asserts` / `# proves` header |
| Gates | every converted example validates; the four gates keep their self-tests non-vacuous on the new shape |
| Size | twelve examples, five test files; medium |
| Depends on | PR 1 |

### PR 3 — the merged shape becomes the read model, by name

| | |
|---|---|
| Content | `realized-entity.schema.json` is renamed to say what it now is — an entity view assembled from the records — and `REALIZED-ENTITY.md` with it. The shared blocks (`provenance`, `dependencies`, `status`, `sovereignty`, `correlation_ids`, `adopted_standards`, `portability`, `integrity`, …) move into the state-record schema's `$defs`, so the stored form owns them and the view references them, not the reverse. `drift` and `ownership` are removed from the view: drift is computed from the latest realized and discovered records, ownership has no writers to referee. The sixteen documents that name the old schema are swept; the rename goes in `registry/renames.yaml` |
| Size | one schema rename, one prose rename, sixteen documents; medium, mostly mechanical |
| Depends on | PR 2 |

### PR 4 — the flows say who writes which record

| | |
|---|---|
| Content | `docs/flows/request-realization.md` and the provider-lifecycle flow describe the write path per record: the consumer's submission writes an intent record; assembly and policy write a requested record naming it; the provider's commit writes a realized record naming that; each discovery sweep appends a discovered record. Drift and the entity view are described as reads |
| Size | prose; small |
| Depends on | PR 3 |

### Outside this repository

The DCM control plane writes these records. Its read and write paths change with PR 1's
schema and PR 3's rename, and that work is coordinated across the UDLM / DCM boundary rather
than done here.

## Discipline that applies to every PR

- A per-state record is immutable: a correction is a new `record_uuid` naming the old one in
  `supersedes`, never an edit. The identity gate enforces it for all four kinds.
- A realized record carrying `integrity` must be resealed on any change, as a new version chained
  to its previous head.
- The four-state vocabulary has one home; do not restate it.
- `bash scripts/signoff.sh`, untruncated, before opening the PR. Merging is the maintainer's action.

## Status — 2026-09-12, evening

| PR | State |
|---|---|
| 1 (#582) | merged |
| 2 (#584) | merged |
| 3 (#585) | merged |
| 4 | open — the flows say who writes which record |
