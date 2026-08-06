# ADR-PROV-001: Data role classification — what goes to a provider is execution data only; the dispatch payload is the role:execution slice

**Status:** Proposed
**Type:** Architecture Decision Record — a `DecisionRecord` with architecture scope (`docs/spec/foundations/knowledge-family.md` §4.5)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The surfaces this decision governs: `docs/spec/contracts/data-roles.md` · `registry/realized-
entity.schema.json` · `docs/spec/contracts/provider-contract.md` ·
`docs/spec/contracts/policy-contract.md`

## Context

Full provenance requires recording not only what each field's value became and which layer it
came from (already in `provenance`), but also what was OFFERED and NOT applied, and why (the
'road not taken': overridden/narrowed/stripped/blocked contributions). That assembly record is
control-plane information — it must NOT go to the provider, and must not persist into the
realized state. Generalizing: what a provider actually needs is EXECUTION data only, and that
set should be formalized apart from the raw domain schema. The clean primitive is a data ROLE
— a purpose axis orthogonal to data_classification (sensitivity). data_classification already
answers 'who may see it'; data_role answers 'what is it for', and governs dispatch: only
role:execution crosses to a provider by default. This reuses existing machinery end-to-end —
data_classification is already field-level and already a policy match source, and the
Governance Matrix already fires on every DCM->Provider interaction with
STRIP_FIELD/DENY/REDACT — so role dispatch is a match source, not new policy. Providers opt
into non-execution roles via accepts_roles, and may tag data they return by role;
sovereignty/profile policy can strip a requested role but never widen beyond accepts_roles.
`unapplied`/`assembly` becomes one occupant of role:assembly rather than a special case.

## Decision

Introduce data_role (execution | assembly | governance | audit | cost; extensible) as a
purpose-axis classification orthogonal to data_classification. The provider dispatch payload
is DEFINED as the role:execution slice of the Requested snapshot; non-execution roles are
control-plane only and MUST NOT be naturalized to a provider nor copied into states.realized.
Roles are declared via a `roles` map (dot-path -> role) at field and section level with
precedence field > section > default(execution) — list only non-execution exceptions
(succinct). The Requested snapshot gains an `assembly` section (role:assembly) carrying
`unapplied[]` (offered-but-not-applied contributions + disposition + reason) and
`excluded_layers[]` (LAY-003). Providers declare `accepts_roles` (default [execution]) and may
tag returned data by role; the delivered set = accepts_roles INTERSECT Governance-Matrix-
permitted. data_role becomes a Governance-Matrix match source; the default rule STRIP_FIELDs
non-execution at the DCM->Provider boundary. Defined once in contracts/data-roles.md.

## Data · Policy · Provider

- **Data** — data_role is a classification ON data (field/section via the `roles` map), the
twin of data_classification. role:execution = the dispatch contract (domain fields +
execution-control data); assembly/governance/audit/cost = control-plane. The `assembly`
section on the Requested snapshot carries unapplied + excluded_layers — full 'road not taken'
provenance, co-located with the winning `provenance` chain, never a parallel model.
- **Policy** — Which roles reach which provider is Governance-Matrix policy: data_role is a
new match source (parallel to data_classification); the default boundary rule STRIP_FIELDs
non-execution. Sovereignty/profile policy can strip a requested role but never widen past
accepts_roles; fsi/sovereign strip hard + AUDIT_ONLY any widening.
- **Provider** — A provider declares accepts_roles (what it wants; default [execution]) and
may tag data it returns by role (execution state vs assembly context). It never receives more
than accepts_roles INTERSECT policy-permitted; assembly-tagged provider output is not
persisted as realized state.

## Alternatives considered

- **A positional non-dispatched section (states.requested.assembly) only** — position, not
classification — no field-granularity, no provider negotiation, doesn't generalize to
governance/audit/cost or provider-emitted tags *Rejected:* the real primitive is the data's
role, not its place in the record
- **A data_role classification axis; dispatch = the role:execution slice (chosen)** — a new
(extensible) enum + a cascade rule to learn
- **Add a formula/derived or bespoke per-field dispatch flag** — reinvents classification +
boundary policy that already exist; verbose (every field flagged) *Rejected:* duplicates
data_classification + Governance Matrix; not succinct

## Consequences

['contracts/data-roles.md', 'registry/realized-entity.schema.json ($defs.data_role +
state_snapshot.roles/.assembly + realized_snapshot.roles)', 'registry/policy.schema.json
(data_role match source)', 'contracts/provider-contract.md (accepts_roles + PRV-008)']
