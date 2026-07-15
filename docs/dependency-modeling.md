# Dependency modeling in UDLM (data-model support)

**What this settles:** how the UDLM data model *represents* dependencies, and how it supports
expressing them several ways at the implementor's chosen granularity. This is the data-model side;
how a consumer **resolves** the authored model into one effective graph (and how dependencies get
*inserted* — discovered, derived, provider-reported) is a DCM concern (see the DCM architecture:
dependency resolution).

## The primitive: typed dependency edges

Every resource carries `dependencies[]`; each entry is a directed edge to another resource with a
`kind`, an optional named `relation`, and an optional `strength` (hard/soft). The four edge kinds are
aligned to OASIS TOSCA root relationship types:

| kind | TOSCA | meaning |
|---|---|---|
| `contained_by` | (containment) | physical/logical containment — a component within its parent |
| `depends_on` | DependsOn | a runtime/functional dependency |
| `references` | HostedOn / general | placement or a general reference |
| `binds_to` | BindsTo | a binding to a specific provider (e.g. a database) |

A type may **declare** the named relations it allows (`relationships[]`: name → kind + target type),
and the validator enforces that a used relation is declared and kind-consistent (REL-001/003). A
relation name is optional — an unnamed edge is valid — so a type need not enumerate every use.

Direction convention: `source → target` means "source depends on target". That single convention is
what lets a consumer topologically order the graph (e.g. a shutdown stops the source before the
target).

## Supported authoring patterns

The same data model expresses dependencies at several granularities. All reduce to typed edges; the
difference is *how many* edges an implementor authors and *where* they sit.

1. **Direct edge (incl. multi-edge redundancy)** — a resource names its dependency explicitly. Highest
   fidelity, per-edge effort. The base case; everything else composes from it. Redundancy is just
   *more than one* direct edge: a host declares `depends_on feed-a` **and** `depends_on feed-b`
   (`Compute.BareMetalHost → Facility.PowerFeed` is `0..n`), so a single feed loss leaves a second
   path across a distinct fault domain — authored, not inferred.
2. **Component chain** — where a dependency routes through a *managed* component, model it on the
   component, not the whole resource. Canonically **network fabric**: a `Hardware.NetworkInterface`
   `contained_by` a host `connects_to` a switch port, and a consumer follows `host → NIC → port`
   transitively. This applies only to components DCM actually manages/configures (ADR-013 — DCM is not
   a hardware system-of-record); inert inventory like a PSU is *not* modeled, so **power** is a direct
   host dependency instead — see pattern 1 / the multi-edge redundancy case below.
3. **Bundling (via a node)** — to share a set of dependencies across resources, declare them on a
   node and have each resource `depends_on` that node. The dependents inherit the set as **secondary
   dependencies** through the graph's transitivity — no expansion, no special type. Best for shared
   platform concerns routed through a real thing (a gateway, a control-plane service). One edge per
   member; the shared deps live in one place. (See the anti-pattern below on why a dedicated "bundle
   type" is *not* the answer.)
4. **Scope** — some memberships are already fields. `tenant_uuid` **is** realm membership; a consumer
   can derive the realm's identity/DNS dependency without an edge. `Facility.Location` gives physical
   scope (site/room/rack) for location-scoped concerns — note it deliberately does **not** own power
   (the host's own feed edges do), because "where a thing is" and "what powers it" are different questions.

## Types that enable each pattern

| Pattern | Type(s) |
|---|---|
| Direct edge | every resource type (`dependencies[]`) |
| Power | `Compute.BareMetalHost` `depends_on` → `Facility.PowerFeed` (`0..n`; one edge per feed) |
| Managed-component chain | `Hardware.NetworkInterface` `connects_to` → switch port |
| Bundling | *any* node the members `depends_on` — its deps become theirs transitively (no dedicated type) |
| Physical scope | `Facility.Location` (adopts Redfish Location) |
| Realm scope | `Security.DirectoryService` + `Network.AddressService`, keyed by `tenant_uuid` |

## Anti-pattern: a dedicated "bundle" type

It is tempting to add a first-class type — call it `DependencyBundle` — whose members "attach" and
"inherit" its dependencies. **Avoid it.** It buys nothing the graph doesn't already give you: a
resource that `depends_on` a node is *already* transitively dependent on that node's dependencies, and
the topological order already reflects it. A bundle type only adds a parallel mechanism (membership +
an expansion pass) that reproduces transitivity, plus surface area to learn, validate, and keep
consistent — for no functional gain. This is the minimal-surface / adopt-not-absorb tenet in action:
**do not introduce a construct when a primitive already expresses it.** If you need to mark a node as
a non-material grouping — something depended on for ordering but never actually acted on — use a
lightweight flag on the node, not a whole type. Bundling is `depends_on` a node; nothing more.

## What the data model does NOT do

The model *stores* the authored dependencies; it does not compute the effective graph. Bundle
expansion, scope derivation, transitive-chain resolution, and merging discovered/provider/policy
dependencies are **resolution**, done at build time by the consumer (DCM) and never persisted — so
the effective graph always reflects the live model. Keeping resolution out of the stored data is what
lets one estate be authored coarsely or finely, or a mix, without changing the data model.
