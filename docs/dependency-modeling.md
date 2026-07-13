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

1. **Direct edge** — a resource names its dependency explicitly. Highest fidelity, per-edge effort.
   The base case; everything else composes from it.
2. **Component chain** — model the dependency through the component that carries it, not the whole
   resource. Canonically **power**: a host contains `Hardware.PowerSupply` units, each `powered_by` a
   `Facility.PowerFeed` — and the feeds need not match, so redundancy is preserved. A consumer
   follows `host → PSU → feed` transitively. Same shape for network fabric (NIC → switch port).
3. **Dependency bundle** — `Topology.DependencyBundle` is a named set of shared dependencies. A
   resource attaches with one edge and inherits the whole set. For ambient, cross-cutting
   dependencies applied uniformly to many members (a realm's identity/DNS, a site's shared services,
   a cooling domain). Bundles compose. Adopts TOSCA groups/policies.
4. **Scope** — some memberships are already fields. `tenant_uuid` **is** realm membership; a consumer
   can derive the realm's identity/DNS dependency without an edge. `Facility.Location` gives physical
   scope (site/room/rack) for location-scoped concerns — note it deliberately does **not** own power
   (PSUs do), because "where a thing is" and "what powers it" are different questions.

## Types that enable each pattern

| Pattern | Type(s) |
|---|---|
| Direct edge | every resource type (`dependencies[]`) |
| Component power | `Hardware.PowerSupply` → `Facility.PowerFeed` |
| Bundle | `Topology.DependencyBundle` (adopts OASIS TOSCA) |
| Physical scope | `Facility.Location` (adopts Redfish Location) |
| Realm scope | `Security.DirectoryService` + `Network.AddressService`, keyed by `tenant_uuid` |

## What the data model does NOT do

The model *stores* the authored dependencies; it does not compute the effective graph. Bundle
expansion, scope derivation, transitive-chain resolution, and merging discovered/provider/policy
dependencies are **resolution**, done at build time by the consumer (DCM) and never persisted — so
the effective graph always reflects the live model. Keeping resolution out of the stored data is what
lets one estate be authored coarsely or finely, or a mix, without changing the data model.
