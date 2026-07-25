# change-control — when changes happen, and who decided

Eight cases adding the temporal layer to class versioning: the change-management policies that
control, gate, and orchestrate *when* an upstream class change reaches an estate and its
downstream records. One upstream change meets varying regimes — continuous adoption (dev),
maintenance windows with full ceremony for breaking changes (prod), freezes and break-glass
expedites (regulated) — plus the staged rollout that composes estates into a chain by policy,
and dependency-ordered propagation inside one estate. 004 succeeds only if the system refuses
(the must-reject convention); the rest are expected to work.

Two rules run through every case: scheduling gates control *when*, evidence gates control
*whether* (nothing waives blue/green evidence, ADR-046); and waiting is visible — queued,
windowed, and frozen are typed debt states, so an estate that is behind is provably on-policy
behind, never silently stale (ADR-045's debt discipline, extended). Cases 009/010 carry the flagship
operational scenario — a storage array with ten dependent applications through DR-gated
maintenance (derived impact set, per-client tolerance, output-surface cutover, ordered
quiesce/restart) and its mid-maintenance failure hold. Worked example:
docs/examples/change-control-walkthrough.md. Flows: docs/flows/change-control-adoption.md and
docs/flows/storage-array-maintenance-dr.md. Cases 011/012 are surface probes:
each names an exact model surface the flows' decision tables validated as missing today, so an
analysis run *must* flag it until the surface lands.

**Gap-exposure map** (deterministically resolved against the registry, 2026-07-25 — every
known gap is exposed by at least one case, so closure is measurable, not asserted):

| Gap | Exposed by | Tracked |
|---|---|---|
| DR pairing not declared on Storage types | 011 (all criteria), 009 c3 | issue #250 |
| FileShare outputs too thin for cutover verification | 012 (c1–c3), 009 c4 | issue #251 |
| No temporal policy clauses (window/freeze/expedite) | 002 c1, 004 c2, 007 c1 | change-control ADR |
| No typed debt states | 005 c3, 007 c3 | change-control ADR |
| No change record / blast-radius manifest | 001 c5, 003 c5 | P0 (regeneration manifest) |
| Change-calendar knowledge type + information-provider declaration | 013 (all criteria) | proposed — docs/design/change-control-knowledge-sources.md |
| Authority-per-scope for multi-source knowledge | 014 (c1, c4) | change-control ADR |
| Knowledge-family freshness surface (family-wide — stale CVE feed = same class) | 015 (c1, c5) | proposed — Knowledge Base-tier element |
| Policy-self-change governance (matrix gap) | 016 (all criteria) | change-control ADR |
| Whole-provider retirement wind-down (matrix gap) | 017 (all criteria) | change-control ADR |
| Derived impact set + orders; pool health outputs | 009 c1/c3 — **MET today** | — |

The contracts are proposed pending the
change-control ADR — corpus first, ruling after.
