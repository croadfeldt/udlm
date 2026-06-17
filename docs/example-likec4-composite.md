# Example — DCM manages a LikeC4-described service

A worked example of the LikeC4 ↔ UDLM ↔ DCM loop: **design the architecture in LikeC4 → it maps to a
UDLM composite (complex) catalog item → DCM realizes each component via a separate provider → the live
diagram is re-projected from Realized state.** This validates the hypothesis: a LikeC4 *system* is a
complex catalog item, and its components break out into separate back-end providers.

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

This is a *description* — boxes and arrows. It has no lifecycle, no provider, no realized state. It is
pure Data (an Intent blueprint).

## 2. The mapping → a UDLM composite catalog item

Each LikeC4 **element** → a constituent with a UDLM **resourceType + provider**; each **relationship** →
a `depends_on` edge (which becomes a typed binding over the dependency graph). External actors
(`customer`) aren't provisioned — they inform public-facing config.

| LikeC4 | UDLM constituent | Resource type | Provider (back end) |
|---|---|---|---|
| `db` | `db` | `Data.Database` | a database provider (placed by DCM) |
| `api` | `api` (`depends_on: [db]`) | `Compute.Container` | a container provider |
| `web` | `web` (`depends_on: [api]`) | `Compute.Container` | a container provider |
| `web -> api`, `api -> db` | dependency edges | — | (drive the DAG) |

```yaml
kind: CatalogItem            # a Composite Service — entities/composite-service-model.md
metadata: { name: online-shop }
spec:
  resources:                 # constituents, derived 1:1 from LikeC4 elements
    - name: db
      serviceType: Data.Database
      providedBy: external   # DCM's Placement Engine selects a DB provider
      fields:
        - { path: engine, default: postgres }
    - name: api
      serviceType: Compute.Container
      providedBy: external
      requiresResources: [db]            # from  api -> db
      fields:
        - { path: image.reference, default: registry.example.com/orders-api:1.0 }
        - { path: process.env[0].name,  default: DATABASE_URL }
        - { path: process.env[0].value, default: ${db.connectionString} }   # typed binding over the edge
    - name: web
      serviceType: Compute.Container
      providedBy: external
      requiresResources: [api]           # from  web -> api
      fields:
        - { path: image.reference, default: registry.example.com/shop-web:1.0 }
        - { path: process.env[0].name,  default: API_URL }
        - { path: process.env[0].value, default: ${api.endpoint} }
        - { path: network.ports[0].visibility, default: external }          # customer -> web
```

The `${db.connectionString}` / `${api.endpoint}` are **typed references over the dependency edges**
(bind a target's realized `outputs`) — data movement, not transformation (core-tenets T4). DCM resolves
them at dispatch once the upstream constituent reaches Realized.

## 3. DCM realizes it (runtime, Policy applied)

A `CatalogItemInstance` (the order) is the **Intent**. Then DCM — *where Policy is applied*:

1. **Requested** — assembles the payload (layers ⊕ policy), runs the Governance Matrix + sovereignty
   filter (e.g. place all three in an `fsi`/`sovereign` zone), validates the graph is a DAG (`RDG-001`).
2. **Dispatch per DAG level**, each to a **separate provider**:
   `db` (database provider) → publishes `connectionString` → `api` (container provider) binds it,
   publishes `endpoint` → `web` (container provider) binds it, publishes a public URL.
3. **Realized** — aggregates the constituents' realized state into one Composite Entity (one UUID).
4. **Discovered** — per-constituent + composite drift detection.
5. **Audit** — every transition is a leaf in the Merkle chain (`AUD-001/002`).

There is **no "LikeC4 provider"** and no meta-orchestrator: DCM's standard machinery places each primitive
with the appropriate provider, sequences by the dependency graph, and handles failure/compensation in
reverse. That is exactly your "break the primitives into separate providers on the back end."

## 4. The loop closes — live diagram from Realized state

Project the Composite Entity's **Realized** state back into a LikeC4 model → an always-accurate diagram of
what is *actually running* (with drift highlighted), instead of a hand-drawn approximation that rots.

## The boundary, in one line

| Step | Domain |
|---|---|
| LikeC4 model / catalog item / bindings / edges | **Data** (UDLM) — declarative nouns |
| LikeC4→catalog mapping, assembly, placement, DAG, realization, audit | **Policy/DCM** — the verbs |
| Realize each primitive | **Providers** |
| Realized state → LikeC4 diagram | **Data projection** (a view) |

So: **author in LikeC4 → UDLM is the substrate → DCM applies policy + realizes via per-primitive providers
→ visualize back in LikeC4.** One model, design-time and runtime, with governance and audit in the middle.
