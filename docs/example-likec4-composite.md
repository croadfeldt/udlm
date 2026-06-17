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
