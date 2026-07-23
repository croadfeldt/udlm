# UDLM ↔ Architecture-as-Code — Topology Ingestion Pathway

_Status: proposal / vision. References public specifications from
[FINOS CALM](https://calm.finos.org/) and [LikeC4](https://likec4.dev/),
alongside UDLM's own model. This documents why architecture-as-code tools
are natural ingestion sources for UDLM Composites and how
the mapping would work under T5._

## The one-line story

**Architecture-as-code tools describe topology. UDLM manages its lifecycle.**
A CALM architecture or a LikeC4 model declares "these components compose into
this service" — which is what a Composite already represents.
UDLM wraps that topology with lifecycle, governance, provenance, and drift
detection — without re-expressing the topology language itself.

## Why they fit

1. **Same shape, different depth.** Both CALM and LikeC4 produce a graph of
   typed nodes connected by typed relationships. UDLM's entity + relationship
   model is a strict superset: every node maps to an entity, every edge maps
   to a relationship — and UDLM adds lifecycle state, four-state tracking,
   provenance, and policy that the topology languages do not model.

2. **Complementary layers, no overlap.**

   | Concern | CALM / LikeC4 | UDLM adds |
   |---------|---------------|-----------|
   | Topology (what exists, how it connects) | First-class | Not modeled — consumed, not re-expressed |
   | Lifecycle state | Not modeled | Full state machines per entity type |
   | Four-state tracking (Intent → Discovered) | Not modeled | First-class |
   | Drift detection | Not modeled (CALM `diff` compares documents, not live state) | Realized vs Discovered gap |
   | Policy / governance | CALM: declarative controls (annotations). LikeC4: none | Executable policy with typed output schemas, governance matrix |
   | Audit / provenance | Not modeled | Field-level provenance, append-only audit, Merkle proofs |
   | Provider contracts | Not modeled | Unified base contract, 12 typed provider types |

3. **T5 is designed for this.** Architecture-as-code specifications are
   Tier 2 adopted standards under the disposition test
   (`design-principles/adopted-standards.md` §1): they standardize the
   *shape of a whole dataset* (a topology graph), their versions change
   their shape, and UDLM should carry only the identity + pointer — never
   re-express the topology schema.

4. **Both are open.** CALM is Apache-2.0 under FINOS. LikeC4 is MIT. Clean
   to reference and integrate.

## How they compose

**Architecture-as-code becomes a topology source — an Information Provider.**
The topology tool produces a validated architecture document (CALM JSON or
LikeC4 model). A UDLM-conformant realization ingests that document through
an Information Provider contract, translating the topology graph into UDLM
entities and relationships. UDLM then owns lifecycle, governance, and audit
from that point forward.

```
Architecture-as-code tool
  │  (CALM JSON / LikeC4 model)
  ▼
Information Provider (topology ingestion)
  │  naturalize: nodes → entities, edges → relationships
  ▼
UDLM: Composite
  ├── constituent entities (one per node)
  ├── relationships (typed, with nature + lifecycle policy)
  ├── four-state tracking begins
  ├── policy evaluation fires
  └── audit chain records provenance of the import
```

The topology source remains authoritative for *structure*. UDLM does not
modify the upstream architecture — it references it. If the architecture
document changes (a node is added, a relationship rewired), the Information
Provider re-ingests and UDLM's drift detection surfaces the delta between
the previous Realized state and the new topology.

## The mapping

### Nodes → Entities

| Source concept | UDLM target | Notes |
|----------------|-------------|-------|
| CALM node (service, database, network, actor, webclient) | Resource or Composite | Node type informs UDLM entity type; a CALM node with `composed-of` children becomes a Composite whose children are constituents |
| LikeC4 element (system, container, component) | Resource or Composite | C4 abstraction level maps to entity type: systems and containers with children → Composite; leaf components → Resource |
| CALM actor / LikeC4 person | Not ingested as an entity | Actors/people are external to the managed topology; they become context on the request or contributor identity |

### Relationships → UDLM Relationships

| Source concept | UDLM relationship | UDLM nature |
|----------------|-------------------|-------------|
| CALM `composed-of` / LikeC4 nesting | `contained_by` (recorded on the component) | `constituent` |
| CALM `deployed-in` | `contained_by` (recorded on the component) | `operational` |
| CALM `interacts` / LikeC4 `->` | `depends_on` (+ `direction: inbound` record on the target) | `operational` |
| CALM `connects` (interface-to-interface) | `depends_on` (+ `direction: inbound` record on the target) | `operational` |

### Interfaces → Provider capability extensions

CALM interfaces (named interaction points on nodes) do not map to UDLM
entities. They map to the **capability extension** on the Provider contract
of the entity they belong to — the set of operations the entity exposes
through its boundary.

### Controls → Policy seed data

CALM controls (e.g., "only allow HTTPS") are declarative annotations.
On ingestion they become **seed data for Policy match conditions** or
**layer values** on the entity — not policies themselves, because UDLM
policies are executable with typed output schemas and evaluation semantics
that controls do not carry. The realization maps each control type to the
appropriate policy template.

### Metadata → Layer values

CALM metadata and LikeC4 tags (compliance labels, environment tags,
ownership annotations) map to **layer values** on the ingested entities,
assembled at the appropriate layer level (typically Core or Intermediate).

## What each side gains

- **Architecture-as-code tools gain:** lifecycle management, four-state
  tracking, drift detection, governance, audit, and provenance for the
  topologies they describe — without changing their own specification.
- **UDLM gains:** a structured, validated, machine-readable topology source
  that populates Composites without hand-authoring
  relationships — the topology tool has already validated the graph.
- **Users gain:** draw or code the architecture in the tool they prefer;
  the lifecycle platform picks it up automatically.

## T5 adoption mechanics

Under the adopted-standards framework (`design-principles/adopted-standards.md`):

- **Disposition:** Adopt (not absorb). UDLM carries the identity (entity
  UUIDs mapped from node unique-ids) and a version-pinned reference to the
  architecture document. It never re-expresses the topology schema.
- **Tier:** Tier 2 (record/schema) — the topology is a shaped dataset whose
  versions change its structure.
- **Provider support:** The Information Provider declares
  `adopted_standard_support` for CALM and/or LikeC4 with version ranges and
  `consume` direction.
- **Provenance:** Every field whose value originated from the topology
  document carries provenance recording the source (Information Provider
  UUID, document version, timestamp).

An entry in the Standards Adoption Register
(`registry/standards-adoption-register.md`) would formalize the decision
when this pathway moves beyond proposal.

## Scope and limitations

- This pathway covers **topology ingestion** — populating the structural
  skeleton of entities and relationships. It does not cover runtime
  provisioning (that is a Service Provider's job, not the topology source's).
- CALM's visual tooling (CALM Studio, VS Code extension) and LikeC4's
  diagram renderer remain upstream — UDLM does not provide or replace
  visualization.
- The mapping is **lossy in one direction**: UDLM adds lifecycle,
  governance, and provenance that the topology language cannot represent.
  Round-tripping back to CALM/LikeC4 would produce a topology-only
  projection, not the full UDLM entity.
