# Graph integrity — acyclicity and the dependency-cycle diagnostic

**What this settles:** the dependency graph the estate forms has one hard invariant — it must be a
**DAG** — and when that invariant is violated the violation is **first-class, exposed data**, not a
buried resolver error. This defines the invariant, the `DependencyCycle` diagnostic UDLM exposes, and
how policy addresses it. DCM computes it (see the DCM dependency-resolution architecture); UDLM owns
the shape and the invariant.

## The invariant

Every typed dependency edge (`depends_on`, `contained_by`, `binds_to` — the ordering kinds, aligned to
TOSCA `DependsOn`/`HostedOn`/`BindsTo`) contributes to one directed graph over the estate. That graph
**must be acyclic**: an ordered shutdown/startup, an impact/blast-radius traversal, and a realization
plan all require a topological order, which exists **iff** the graph is a DAG. A cycle means no such
order exists — the estate cannot be safely sequenced. Acyclicity is therefore a modeled invariant of
the estate, not an implementation detail of any one consumer.

This is not new graph theory — we adopt the standard result (a finite digraph is topologically
orderable iff it has no directed cycle) and TOSCA's DAG assumption for topology templates. UDLM adds
only the *exposed shape* of a violation.

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
- *default-deny blocking cycles* — `graph.cycle_severity eq blocking` → deny realization.
- *warn on degraded* — `graph.cycle_severity eq degraded` → advisory finding, allow.
- *quarantine an intent/reality conflict* — `graph.cycle_mechanisms in [discovered]` → hold the members
  for review.

## Consumers

The invariant is what every graph consumer already relies on — ordered shutdown/startup, topology
rendering, blast-radius. Exposing its violation as severity-ranked, provenance-tagged, policy-governed
data turns "the estate won't order" from an opaque dead end into an actionable signal. Reference
realizations today: the estate CI's **CYCLE-001** gate (fails the build and prints the offending chain)
and the estate-explorer `/api/order` `cycles[]` output.
