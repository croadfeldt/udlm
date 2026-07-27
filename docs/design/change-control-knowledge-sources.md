# Change-control information as a knowledge domain — design note

**What this settles:** where change-control information actually comes from, and how the model
carries it. Maintenance windows, freeze calendars, approvals, and tolerance classes have more
than one source of truth in a real organization: some are authored inside the estate as policy
clauses, and some live in external systems of record — the change-management/ITSM platform
that owns the corporate change calendar, the CAB that owns approvals. This note models the
external sources the way the registry already models external knowledge (the SBOM/CVE domain):
as **Knowledge-family types supplied by information providers**, referenced by policies rather
than copied into them. Contracts here are **proposed pending the change-control ADR**; the
corpus cases (`change-control/013–015`) encode them for measurement first, per the
corpus-first discipline.

## The pattern, in plain terms

The registry has done this once already: vulnerabilities and software inventory are
Knowledge-family records ingested from external feeds, and policies reference them instead of
restating them. Change-control information is the same shape. A maintenance window is not a
fact the estate invents — for most organizations it is a record in the change-management
system — so the model treats it as knowledge with a source, not as policy text someone
re-types after every CAB meeting.

Three sources, one discipline:

| Source | Carried as | Refreshed by |
|---|---|---|
| Internal — the estate authors it | a policy clause (the pending ADR's temporal vocabulary) | policy change, normal review |
| External system of record (ITSM-archetype) | **Knowledge-family records** (change windows, freezes, approvals) | an **information provider** (`provider.kind: information` — the kind already exists) that declares the knowledge type as a capability and refreshes its records |
| Derived — computed from other model data | derived values (never stored as if authored) | recomputation |

The consuming policy **references knowledge by handle** — adopt-by-reference, never a re-typed
copy — and declares, per scope, which source is authoritative where both could answer. The
gate then evaluates policy-against-knowledge at decision time and cites the knowledge revision
it read.

## The three contracts the corpus encodes

- **UC-013 — sourcing.** Windows/freezes as Knowledge records (schedule, scope, source,
  validity); an information provider declares the change-calendar knowledge type and refreshes
  it; a calendar change upstream never touches policy text.
- **UC-014 — authority.** Multi-source answers are resolved by *declared* authority per scope;
  an undeclared conflict refuses the gating decision (typed, both sources and both answers
  named) rather than silently picking one — the single-truth ban, applied to information.
- **UC-015 — freshness, fail-closed.** Gates evaluate knowledge freshness before knowledge
  content; stale knowledge refuses (naming source, last refresh, validity horizon), with the
  expedite path as the sanctioned emergency route. Deciding on outdated windows is worse than
  refusing.

## What this asks of the model (validated against the registry, 2026-07-25)

| Surface | Status today |
|---|---|
| `provider.kind: information` | **EXISTS** (schema enum; the cost provider is the live precedent) |
| Knowledge family | **EXISTS** (five types; the SBOM/CVE ingestion method is the reusable pattern) |
| A change-calendar knowledge type (windows, freezes, approvals) | **MISSING** — the new type this note proposes |
| Provider declaration of *knowledge types supplied* | **PARTIAL** — the provider schema carries `capabilities`; declaring a knowledge type as the supplied capability needs the provider-contract extension |
| **A freshness surface on Knowledge records** (as-of, valid-until, refresh cadence) | **MISSING on every Knowledge type** — validated: not even Vulnerability carries one, so a stale CVE feed is the same undetectable failure as a stale calendar |
| Authority-per-scope declaration in consuming policies | **MISSING** — part of the pending change-control ADR's clause vocabulary |

The freshness row is the finding with reach beyond change control: it is a **family-level
element** — exactly the shape the class system's Base tier exists for. When the Knowledge
family gets its Base Class (the class-realization program), freshness elements belong there
once, and every knowledge domain — calendars, vulnerabilities, software inventory, whatever
comes next — inherits staleness decidability. Until then it is a per-type gap.

## Where this lands

The change-calendar knowledge type and the Knowledge-family freshness elements are registry
work (types + the family Base Class when P-phases reach Knowledge); the authority and
staleness clause vocabulary is ruled by [ADR-053](../adr/ADR-053-change-control-policy-vocabulary.md) (§6–7); the provider
declaration extension joins the provider contract. The corpus cases ride analysis runs now, so
every one of these gaps is measured from today — closure flips the cases, and the scoreboard
shows it.
