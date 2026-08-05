# Graph integrity — acyclicity and the dependency-cycle diagnostic

**What this settles:** the dependency graph the estate forms has one hard invariant — it must be a
**DAG** — and when that invariant is violated the violation is **first-class, exposed data**, not a
buried resolver error. This defines the invariant, the `DependencyCycle` diagnostic UDLM exposes, and
how policy addresses it. DCM computes it (see the DCM dependency-resolution architecture); UDLM owns
the shape and the invariant.

## The invariant

Every typed dependency edge (`depends_on`, `contained_by`, `binds_to` — the ordering kinds, aligned to
TOSCA `DependsOn`/`HostedOn`/`BindsTo`) contributes to one directed graph over the estate. That graph
**must be acyclic**: an ordered shutdown/startup, an impact/blast-radius traversal, and an implementation
plan all require a topological order, which exists **iff** the graph is a DAG. A cycle means no such
order exists — the estate cannot be safely sequenced. Acyclicity is therefore a modeled invariant of
the estate, not an implementation detail of any one consumer.

This is not new graph theory — we adopt the standard result (a finite digraph is topologically
orderable iff it has no directed cycle) and TOSCA's DAG assumption for topology templates. UDLM adds
only the *exposed shape* of a violation.

## Declared once, navigable both ways (the derived inverse)

A relationship edge is declared on **one** endpoint — its natural owner. A pool declares
`contained_by BareMetalHost`; the host does **not** carry a reciprocal `contains Pool`. This is
deliberate: storing both directions would duplicate the same fact in two places and let them drift,
which the single-source discipline forbids. The reverse direction is **derived, never stored** — the
same move as derived shape, nature, and portability.

Every `edge_type` has a defined inverse, registered once in
[`registry/edge-types.yaml`](../../registry/edge-types.yaml): `depends_on ⟷ required_by`,
`references ⟷ referenced_by`, `contained_by ⟷ contains`, `binds_to ⟷ bound_by`. The dependency graph
is the union of all declared edges, and it is navigable in **both** directions by inverting them: to
answer "what does this host contain?", invert the pools' `contained_by`. So a relationship that appears
"missing" on the far endpoint is not missing — it is derived. Declare once; traverse either way.

`tests/check_graph_integrity.py` keeps the derivation sound, so a one-sided *declaration* is never a
one-sided *graph*:

- **`GRAPH-001`** — the edge-type registry matches the `edge_type` enum in the spec meta-schema (the
  inverse map cannot drift from the allowed edge types).
- **`GRAPH-002`** — every edge `target` resolves to a real resource type or Class; a dangling target is
  refused, because the derived inverse would otherwise land on nothing.
- **`GRAPH-003`** — every declared edge has a derivable inverse; the gate builds the two-sided adjacency
  (declared + derived) and can emit it (`--emit` → `registry/generated/dependency-graph.json`) for a
  consumer or the estate-explorer that wants the materialized bidirectional graph.

## The exposed data: `DependencyCycle`

When the invariant is violated, each distinct cycle is exposed as a `DependencyCycle` diagnostic — the
same first-class, referenceable shape as any other finding the platform acts on:

| field | meaning |
|---|---|
| `members[]` | the resources caught in the cycle (uuids/handles) |
| `edge_chain[]` | the actual closing path, `a → b → … → a` — the offending edges, not just the set |
| `severity` | derived from the cycle's own edges (below) |
| `contributing_mechanisms[]` | which insertion mechanisms (authored / discovered / derived / provider / policy) contributed the edges — a cycle's *provenance* |
| `detector` | which detector/graph produced it (authored graph vs the effective graph with derived edges) |

**Severity is a property of the cycle, derived from edge strength** — it is not a fixed error level:

- **`blocking`** — every edge in the cycle is `hard`. No safe order exists; the estate cannot realize
  or sequence. This is the deny-by-default case.
- **`degraded`** — at least one edge in the cycle is `soft`. The cycle is *breakable*: dropping the
  soft edge yields a valid order, at the cost of that (non-load-bearing) dependency. Orderable, but
  flagged so the relaxation is a recorded decision, not a silent one.

Provenance matters as much as membership: an *authored ⇄ authored* cycle is an estate-authoring
mistake; an *authored ⇄ discovered* cycle is an intent-vs-reality conflict (what was declared disagrees
with what a probe observed); an *… ⇄ policy-injected* cycle means a broad rule closed a loop on a
specific resource. Same cycle shape, very different remediation — so the mechanism tags travel with it.

## Policy addresses it (Data·Policy·Provider)

- **Data (this spec).** UDLM carries the invariant and the `DependencyCycle` shape. It does **not**
  compute cycles — a cycle is derived state, never stored on the resources themselves.
- **Provider (DCM resolution).** Computes cycles from the effective graph on every resolution and emits
  the diagnostics (DCM: dependency-resolution — cycle detection is a core, always-run step).
- **Policy (DCM policy engine).** `DependencyCycle` findings are **policy inputs**. A `Policy` record
  matches on the graph-integrity attributes below and decides the response — deny admission, quarantine
  the members, warn, or auto-relax a soft edge with a recorded resolution. The response is *authored*,
  so an operator sets how strict an estate is, rather than the engine hard-coding it.

Policy `match` sources (see `policy.schema.json`): `graph.has_cycle` (bool), `graph.cycle_severity`
(`blocking` | `degraded`), `graph.cycle_members` (set membership — "any cycle touching this resource"),
and `graph.cycle_mechanisms` (e.g. deny only cycles that a discovered or policy-injected edge closed).

Example policy intents this enables (authored as records, not code):
- *default-deny blocking cycles* — `graph.cycle_severity eq blocking` → deny implementation.
- *warn on degraded* — `graph.cycle_severity eq degraded` → advisory finding, allow.
- *quarantine an intent/reality conflict* — `graph.cycle_mechanisms in [discovered]` → hold the members
  for review.

## Consumers

The invariant is what every graph consumer already relies on — ordered shutdown/startup, topology
rendering, blast-radius. Exposing its violation as severity-ranked, provenance-tagged, policy-governed
data turns "the estate won't order" from an opaque dead end into an actionable signal. Reference
implementations today: the estate CI's **CYCLE-001** gate (fails the build and prints the offending chain)
and the estate-explorer `/api/order` `cycles[]` output.
