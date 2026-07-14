# UDLM ADR-010: Dependency-graph completion — fault domains, blast radius, and the unmet-dependency diagnostic

**Status:** Proposed
**Date:** 2026-07-13
**Type:** Architecture Decision Record (`DecisionRecord`, architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `docs/graph-integrity.md` (acyclicity + `DependencyCycle` — the first graph consumer made first-class); `docs/foundational-resources.md` (roots that anchor fault domains); ADR-006 (convergence — terminal surface on a hard-unmet dependency); ADR-009 (relationships are guidance, not a gate); ADR-008 (UDLM/DCM boundary)
**Tracking:** September 1.0 gap analysis P4/P5 — UC-73071912 ("represent the dependency graph as first-class"), UC-4908573a ("surface a broken cross-resource dependency before realization").

## Context

`graph-integrity.md` made **one** consumer of the dependency graph first-class: acyclicity, exposed as the `DependencyCycle` diagnostic. But the September UCs lean on three others that are today only *asserted as derivable*, not *specified as exposed shapes*:

- **shared fault domain** — resources that co-depend on the same root (a `Facility.Location`, a `Facility.PowerFeed`, a host) fail together; nothing exposes that grouping.
- **blast radius / redundancy** — "what breaks if X is lost" and "does a dependent survive one fault-domain loss" have no exposed shape.
- **unmet dependency** — `DependencyCycle` has no sibling for a **broken/unresolvable/unrealized** edge; ADR-006 specifies the *behavior* (a hard-unmet dependency is terminal) but not the *diagnostic consumers act on*.

## Governing principle (applies to every shape below)

UDLM defines the **base shape and the enforcement mechanism**; the **organization ratifies what to enforce**, and **providers define their offerings**. A shape here is guidance plus a policy hook — never a mandate. Concretely: the org decides which foundational resources count as fault domains and how severe an unmet dependency must be to block; a provider may offer a variant base type (e.g. a `Network.Port` in place of `Network.VirtualNetwork`) and the org enforces, via policy/Governance-Matrix, which base or variant its providers must produce and consumers may consume. The dependency-graph shapes read whatever typed edges exist; they do not require a specific type vocabulary.

## Decision

### 1. `SharedFaultDomain` — derived, anchored on foundational resources

A fault domain is **not a new authored edge kind** (that would be authoring burden and drift-prone). It is **derived**: resources that transitively reference the same **foundational resource** (`docs/foundational-resources.md`) designated a fault-domain anchor share that fault domain. Exposed as data:

```
SharedFaultDomain: { anchor: <foundational resource ref>, kind: location|power|host|network|<org-defined>,
                     members: [<resource refs>], derived_from: [<the edges that put each member in>] }
```

**Which foundational resources are fault-domain anchors is org-ratified** (default set: `Facility.Location`, `Facility.PowerFeed`, the hosting `Compute.BareMetalHost`; extensible by policy). The homelab's "a host is both an OCP node and a Ceph OSD, so it's one fault domain" is exactly this: two members co-referencing one host anchor.

### 2. Blast radius + redundancy — derived queries over the same graph

- **`blast_radius(R)`** = the reverse-reachable set (everything that `depends_on` R, transitively) ∪ the members of any `SharedFaultDomain` R anchors. Exposed as derived data, distinguishing **hard** reach (a hard edge — the dependent cannot survive) from **soft** reach (a soft edge — degraded, remappable).
- **Redundancy** = a dependent has **≥2 independent paths** to the capability it needs across **distinct fault domains** (the dual PSU→feed pattern). Exposed as a per-dependent boolean + the paths; loss of one fault domain leaves a redundant dependent up.

### 3. `UnmetDependency` — the first-class sibling of `DependencyCycle`

A dependency edge whose target **does not resolve** (no such resource), **is not yet realized**, or **is decommissioned** is exposed as a diagnostic, so it is caught **before realization** (ADR-006 terminal surface), not discovered mid-dispatch:

```
UnmetDependency: { dependent: <ref>, edge: {kind, target|target_ref}, reason: unresolved|unrealized|decommissioned,
                   severity: blocking|degraded,   # blocking = hard edge; degraded = soft edge (remappable)
                   blast_radius: [<refs>] }
```

Same shape family as `DependencyCycle`: members + the offending edge + severity-from-strength + the reach. A **blocking** `UnmetDependency` denies realization by default (org-configurable, like the cycle case).

### 4. Policy addresses all three (Data · Policy · Provider)

- **Data (UDLM):** the three shapes above are the exposed diagnostics; derived, never stored on resources.
- **Provider (DCM):** computes them from the effective graph on each resolution (reverse-reachability + co-anchor grouping + edge-target resolution).
- **Policy (DCM policy engine):** new match sources — `graph.fault_domain`, `graph.blast_radius`, `graph.unmet_dependency` (severity/members/reason) — added to `policy.schema.json`, alongside the existing `graph.cycle*`. So an org authors "deny a blocking UnmetDependency," "warn if blast_radius > N," "require redundancy across fault domains for tier-1 workloads" — rather than the engine hard-coding any of it.

### 5. Boundary (ADR-008 test)

The **diagnostic shapes and the derivation definitions** are UDLM (a peer must interpret a `SharedFaultDomain` / `UnmetDependency` the same, or interop breaks). The **computation** (traversal, grouping) is DCM. A peer may compute differently; it must expose the same shapes.

## Options considered

- **Author fault domains as their own edge kind (or a first-class `FaultDomain` type).** Rejected — a fault domain is fully determined by which foundational resources members co-reference; authoring it separately is redundant work that drifts from the edges it should track. Derived from foundational-resource references, no new authored edges.
- **Compute blast radius / redundancy imperatively, outside the graph.** Rejected — impact analysis, ordered-shutdown, rehydration, and policy would each derive reach independently and disagree. It must fall out of the one graph so every consumer agrees by construction.
- **Surface unmet dependencies only at dispatch time (fail the realization when the edge can't be resolved).** Rejected — that discovers the break mid-dispatch. `UnmetDependency` surfaces it pre-realization as a diagnostic siblings act on (ADR-006 terminal surface), like `DependencyCycle`.
- **Coin a fixed type vocabulary the shapes require (e.g. mandate `Network.VirtualNetwork`).** Rejected — the shapes read whatever typed edges exist; the org ratifies anchors and providers offer base/variant types via policy. Fixing the vocabulary would break the guidance-plus-policy-hook principle and provider variation (ADR-009).

## Consequences

- The dependency graph is now first-class in **all four** of its consumers (cycles, fault domains, blast radius, unmet deps) — UC-73071912 satisfied; the estate-explorer/ordered-shutdown, impact analysis, and rehydration read one graph.
- **Broken cross-resource dependencies surface pre-realization** as `UnmetDependency` (UC-4908573a) — not as a mid-dispatch failure.
- **Fault-domain reasoning falls out of foundational-resource references** — no new authored edges, and the org tunes the anchor set + severity by policy.
- Reference realizations extend the estate CI (a CYCLE-001 sibling for unmet deps) and the estate-explorer (`/api/order` gains `unmet[]` + fault-domain overlay), same as `graph-integrity` shipped for cycles.
