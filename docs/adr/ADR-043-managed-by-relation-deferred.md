# UDLM ADR-043: No `managed_by` relation — the typed target is the context (deferred, with a re-review trigger)

**Status:** Proposed (croadfeldt upstream) — records a **rejection with a defined revisit condition**.
**Date:** 2026-07-24
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** The relation-vocabulary discipline this applies
([`common-elements.md`](../../registry/common-elements.md) §9 / REL-001 — relations are declared, and an
unnamed edge is valid), the edge model it rides
([`data-model-core.md`](../../foundations/data-model-core.md) §4 — `edge_type` carries ordering; graphs
stay acyclic over ordering edge types), the reuse tenet it exercises (core-tenets **T7** — reach for an
existing mechanism before coining a new one), and the type whose design surfaced it (`Platform.Hub`,
the multi-cluster management plane — authored under rule 36).

## Context

Modeling multi-cluster management surfaced an apparent need for a `managed_by` relation: a spoke
cluster is *managed by* a hub, and the hub may itself be hosted on a cluster — including the cluster
it manages (the self-managed hub, ACM's `local-cluster` pattern). The candidate relation would have
named the spoke→hub edge.

Working the design showed the name adds no information:

- **Meaning already lives in the typed target.** An edge whose target is `Platform.Hub` *is* the
  management relationship. There is nothing else an edge to a management-plane type could mean.
- **Ordering already lives in `edge_type`.** Hosted/provisioned cluster = `contained_by → Platform.Hub`;
  imported cluster = `depends_on (soft) → Platform.Hub` (an imported cluster survives hub loss —
  degrade-don't-break); hub-on-a-cluster = `contained_by → Compute.Cluster`. The two spoke cases are
  mutually exclusive per cluster–hub pair, so `edge_type` alone distinguishes them completely.
- **The reflexive case is solved by demotion, not by a name.** A hub holds no ordering edge toward its
  own host chain — self-management is `references` (informational; it feeds the derived
  `roles: [hub]` marker) — because the containment edge already stated everything true about order,
  and an ordering edge back would close a cycle the acyclicity rule forbids. The CYCLE gate enforces
  this mechanically.

## Decision

**Do not introduce `managed_by`.** The management relationship is expressed entirely in existing
vocabulary: ordering via `edge_type`, meaning via the typed target, no relation name. This is the
**context model for future type authors**: a relation name earns its way in only when (a) a credible
standard names the concept (adopt its term), or (b) two same-`edge_type` edges to the same target pair
need disambiguating. Neither holds here.

**Re-review trigger (why this ADR exists):** if a future design puts two same-`edge_type` edges on one
cluster–hub pair — or a standard emerges that names the management edge (Cluster API and Open Cluster
Management name the *objects*, not the edge, today) — the name earns its keep and this decision is
re-opened with that case as the evidence. Until then, proposing `managed_by` again should land on this
ADR, not on a fresh debate.

## Data · Policy · Provider

- **Data:** no new vocabulary; the edge model and declared-relation rules are unchanged. The derived
  `roles: [hub]` marker is a reading of the reflexive `references` edge, never stored authority.
- **Policy:** policies target the typed edge (`target: Platform.Hub`, `edge_type`) — no name means one
  fewer aliasing surface for policy to drift on.
- **Provider:** a multi-cluster provider (ACM/OCM, Cluster API operators) declares the edges above at
  registration; nothing provider-facing depends on a relation name.

## Consequences

- `Platform.Hub`'s relationship descriptions cite this ADR as the worked exemplar of the
  name-only-when-it-adds-information rule.
- Shutdown/startup ordering falls out of the edges alone for all three topologies (standalone hub,
  hub-on-external-cluster, self-managed hub).
- The corpus gains a self-managed-hub UC (the sharpest test of the demotion rule, and of what
  "rehydrate the hub" means when its intent store lived on the cluster it manages).
