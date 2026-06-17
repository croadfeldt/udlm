# Example — DCM manages a LikeC4-described service

A worked example of the LikeC4 ↔ UDLM ↔ DCM loop: **design the architecture in LikeC4 → it maps to a
UDLM Composite Service → DCM realizes each component via a separate provider → the live diagram
re-projects from Realized state.** This validates the idea: **a LikeC4 system *is* a Composite Service**
(`entities/composite-service-model.md`), and its components break out into separate back-end providers.

A LikeC4 model and a UDLM Composite Service are **two serializations of the same composite graph** — LikeC4
is the human/visual one (design-time); the Composite Service is the operational/data one (runtime), and
only it carries the graph through realization, governance, and audit.

## 1. The architecture, in LikeC4 (design-time, Data)

```likec4
specification {
  element system
  element container
}
model {
  customer = actor 'Customer'
  shop = system 'Online Shop' {
    web = container 'Web Frontend'  { technology 'nginx' }
    api = container 'Orders API'    { technology 'Go' }
    db  = container 'Orders DB'     { technology 'PostgreSQL' }

    web -> api 'calls'
    api -> db  'reads/writes'
  }
  customer -> web 'uses'
}
```

Pure Data — boxes and arrows. No lifecycle, no provider, no realized state.

## 2. The mapping → a UDLM Composite Service

Each LikeC4 **element** → a **constituent** (`component_id` + `resource_type` + `provided_by`); each
**relationship** → a `depends_on` edge (which becomes a typed binding over the dependency graph). The
external actor (`customer`) isn't provisioned — it informs public-facing config.

| LikeC4 | Constituent (`component_id`) | `resource_type` | `provided_by` (back-end provider) |
|---|---|---|---|
| `db` | `db` | `Data.Database` | external — DCM places a DB provider |
| `api` (`depends_on: [db]`) | `api` | `Compute.Container` | external — a container provider |
| `web` (`depends_on: [api]`) | `web` | `Compute.Container` | external — a container provider |
| `web -> api`, `api -> db` | dependency edges | — | drive the DAG |

```yaml
# A Composite Service — entities/composite-service-model.md
compositeService:
  name: online-shop
  constituents:                       # derived 1:1 from LikeC4 elements
    - component_id: db
      resource_type: Data.Database
      provided_by: external
      depends_on: []
      required_for_delivery: required
    - component_id: api
      resource_type: Compute.Container
      provided_by: external
      depends_on: [db]                # from  api -> db
      required_for_delivery: required
      bindings:                       # typed references over the edge (core-tenets T4)
        - { field: process.env.DATABASE_URL, from: db.connectionString }
    - component_id: web
      resource_type: Compute.Container
      provided_by: external
      depends_on: [api]               # from  web -> api
      required_for_delivery: required
      bindings:
        - { field: process.env.API_URL, from: api.endpoint }
        - { field: network.ports[0].visibility, value: external }   # customer -> web
```

The `from:` bindings are **typed references over the `depends_on` edges** (bind a target's realized
`outputs`) — data movement, not transformation (core-tenets T4). DCM resolves each at dispatch once the
upstream constituent reaches Realized.

## 3. DCM realizes it (runtime, Policy applied)

The request produces a **Composite Entity** (one UUID) traversing the four states. DCM — *where Policy is
applied*:

1. **Requested** — assembles the payload (layers ⊕ policy), runs the Governance Matrix + sovereignty
   filter (e.g. place all three in an `fsi`/`sovereign` zone), validates the graph is a DAG (`RDG-001`).
2. **Dispatch per DAG level**, each to a **separate provider**:
   `db` (DB provider) → publishes `connectionString` → `api` (container provider) binds it, publishes
   `endpoint` → `web` (container provider) binds it, publishes a public URL.
3. **Realized** — aggregates constituents' realized state into the Composite Entity.
4. **Discovered** — per-constituent + composite drift.
5. **Audit** — every transition is a leaf in the Merkle chain (`AUD-001/002`).

There is **no "LikeC4 provider"** and no meta-orchestrator: DCM's standard machinery places each primitive
with the appropriate provider, sequences by the dependency graph, and compensates in reverse on failure.
That is the "break the primitives into separate providers on the back end."

## 4. The loop closes — live diagram from Realized state

Project the Composite Entity's **Realized** state back into a LikeC4 model → an always-accurate diagram of
what is *actually running* (drift highlighted), instead of a hand-drawn approximation that rots.

## 5. Translation gaps + how to close them

The two serializations agree on the *provisioning* graph; each side then has layer-specific richness that
does not round-trip — by design, not by defect.

**LikeC4 → Composite Service (lossy without annotation):**
- **Relationship meaning** — LikeC4 arrows are uniform descriptive edges; UDLM edges are *typed*
  (`depends_on` / `references` / `contained_by`). The translator must classify each (a `depends_on`
  provisioning order vs. an async `references` runtime call). LikeC4 doesn't carry that distinction.
- **Hierarchy / levels** — C4 nesting (System › Container › Component) + zoom levels → flat constituents
  (+ `contained_by`); the zoom concept has no substrate analog.
- **External systems / actors** — not provisioned → `references` or dropped.
- **`technology` → `resource_type`** — a mapping decision, not a fact ("nginx" could be a container or an LB).

**Composite Service → LikeC4 (lossy):** lifecycle / state / drift, `provided_by` /
`required_for_delivery` / field-level `bindings`, contract richness (schemas, typed outputs, `immutable`,
sovereignty), and cardinality (`×3`) have no native LikeC4 representation.

**Closing it — declarative annotations (stay on the Data side).** Annotate the `.c4` so the provisioning
subset is deterministic and lossless — no logic, just hints:
```likec4
db = container 'Orders DB' {
  technology 'PostgreSQL'
  metadata { udlm.resourceType 'Data.Database' }
}
api -> db 'reads/writes' {
  metadata { udlm.edge 'depends_on' }   // vs 'references' for async/runtime-only
}
```

## 6. What LikeC4 has that UDLM does not model (by design)

UDLM **can** represent LikeC4's *structural* model: elements → entities (mostly **Knowledge-family** —
architecture *descriptions*; the provisionable subset *also* maps to **Resource-family** types for
realization), relationships → typed edges, nesting → `contained_by`, tags / technology / description →
attributes. So a LikeC4 model spans both families: descriptive architecture (Knowledge) with a realizable
projection (Resource).

UDLM **does not** model — and shouldn't, per the presentation-agnostic tenet:
- **Presentation / rendering:** layout geometry, edge routing, colors, icons, shapes, themes.
- **Viewer behavior:** interactive zoom across C4 levels, navigation.
- **Views & dynamic views:** a *view* is a projection (a filtered rendering); a *dynamic view* is a
  narrative (an ordered scenario walk). UDLM holds the graph; views/narratives are **consumer
  projections** (DAV / viewer territory), not substrate.

So LikeC4's *architecture data* is representable in UDLM; its *presentation + views* sit on top as a
projection layer — the same place DAV's lenses live. Correct boundary, not a deficiency.

## The boundary, in one line

| Step | Domain |
|---|---|
| LikeC4 model / Composite Service / bindings / edges | **Data** (UDLM) — declarative nouns |
| LikeC4→Composite-Service mapping, assembly, placement, DAG, realization, audit | **Policy / DCM** — the verbs |
| Realize each primitive | **Providers** |
| Realized state → LikeC4 diagram | **Data projection** (a view) |

So: **author in LikeC4 → UDLM Composite Service is the substrate → DCM applies policy + realizes via
per-primitive providers → visualize back in LikeC4.** One model, design-time and runtime, with governance
and audit in the middle.
