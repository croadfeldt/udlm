# ADR-033: Templates — the orderable assembly, and the Pattern → Template → System lifecycle

**Status:** Proposed (2026-07-19) — a post-1.0 direction (ADR-031/032) unless a September use case pulls it in; introduces **no schema change** here.
**Related:** ADR-030 (the convergence lifecycle / four states — the spine this projects); ADR-027 (the `Composite` entity_type — **unchanged** here; a separate PR renames its *values*); `lifecycle/subscription-lifecycle.md` (the binding + `lifecycle_policy` this reuses); [lifecycle-convergence flow](../flows/lifecycle-convergence.md) (triggers, day-N as projection); ADR-006 (each activity is a convergence firing); ADR-004 (provider capability — where *composable infrastructure* lives); `registry/standards-adoption-register.md` (TOSCA); AAP/AWX composite-process naturalization.

## Context

A recurring need: order and manage **a set of resources together with the processes that stand them up and operate them** — a stack of VMs/DBs plus its provisioning workflow, nightly backup, and monthly patch — as **one** lifecycle-coupled unit spanning **Day 0/1/2**. Modelling it raised a fork: *widen the definition of "Composite," or introduce a term above it?*

Two facts decided it:
1. **The process↔resource link is operational *binding*, not containment.** A backup isn't a *part* of the stack the way a VM is — it *operates on* it. Widening `Composite` (structural, same-family, `contained_by`) to "own" processes would relabel a binding as containment, re-blurring the line ADR-026's edge model just sharpened. → **a term above Composite; the `Composite` entity_type is untouched.**
2. **The tiers we kept reaching for already exist in the model — as lifecycle states.** "Reusable design → orderable definition → running instance" is not a new taxonomy; it is **Intent → Requested → Realized** (ADR-030) at assembly scale. So the decision is to *name* that projection, not invent a parallel one.

## Decision

**The orderable assembly is a `Template`, and `Pattern` / `Template` / `System` is the ADR-030 lifecycle (Intent → Requested → Realized) at assembly scale.** No new states, no new primitive — the three tiers are the entity lifecycle viewed at a different scope.

### The three tiers are three states

| Tier | ADR-030 state | What it is | Home |
|---|---|---|---|
| **Pattern** | **Intent** — at the *type / design-time* level | the reusable, provider-neutral design ("how a 3-tier app is built"); names shape and rules, not parts — **not orderable** | Knowledge — the twin of `Antipattern` |
| **Template** | **Requested** | that intent *resolved* — profile applied, providers placed, sizes enriched, sovereignty validated — a concrete, **orderable** definition | Catalog (DCM) |
| **System** | **Realized** | the Template converged: real instances + the provider's specific output (IDs/addresses) | Realized entity |

ADR-030's capstone already blesses this: "nature declared at the type level *is* design-time intent." That is exactly what keeps a **Pattern** reusable — it is intent *before any instance exists*, so it stays provider- and size-neutral. A **Template** is that intent once it has been resolved into the Requested state; a **System** is the Requested state Realized.

### The two arrows are the request-realization flow

The transitions between the tiers are not new mechanics — they are the model's own pipeline, at assembly scope:

- **Pattern → Template = Intent → Requested.** Policy/profile *resolution*: enrich, validate, place. This is where "FSI profile, OpenShift, HA Postgres, sovereign placement" gets pinned. Authoring/codification — the **Pattern persists**, so **one Pattern → many Templates** (a homelab/dev Template and an FSI/prod Template of the same design), exactly as one `resource_type` → many requests.
- **Template → System = Requested → Realized.** `Converge` (ADR-030). The **Template persists**, so **one Template → many Systems** (one per customer/environment), exactly as one request → many realized instances.
- **Fourth state — Discovered.** A System observed with *no* Template behind it is brownfield; it is greened by **adopting** it back to a Template/Pattern via convergence-in-dry-run (ADR-030's adoption flow). Same machinery, no new path.

The whole thing is fractal: `resource_type → request → realized` for a single entity is `Pattern → Template → System` for an assembly.

### Why `Template`, not `Blueprint`

- **It is the standards term.** TOSCA **Service Template**, ARM / Heat / Proton "template," OAM **Application** all name the deployable composite. The adopt-by-reference tenet (T5) favors the standards word over a vendor one.
- **"Blueprint" is a vendor term in retreat** — Azure Blueprints is deprecating (→ Template Specs), VMware Aria renamed its "Blueprints" to "Cloud Templates." Building a tier name on it courts churn.
- **It pairs with `System`** — you *instantiate a template*; the Template → System reading is native.
- **Disambiguation (must state, because "template" is overloaded):** ours is a **deployable, TOSCA-Service-Template-class definition**, *not* a Backstage-style text/scaffold template. This ADR claims capital-**T** `Template` as the tier term.
- **`Pattern` keeps the descriptive meaning** the industry already gives it — GoF / Azure Cloud Design Patterns / C4 / ArchiMate — as `Antipattern`'s positive twin in Knowledge, so the two words never compete.

### A Template composes consumables, related by binding

Per ADR-030, resources and processes are both **consumables** (they differ only in archetype). A Template composes them uniformly:
- **structural constituents** — the resources that make up the System (a `Composite` Resource, `contained_by`, ADR-027 — unchanged);
- **bound activities** — the processes that operate on it (provision, backup, patch, scale, teardown), related by **binding** (the subscription `manages` model), **not** containment.

So a Template is *a Composite (resources) + a set of bound processes*, packaged as one orderable, lifecycle-coupled unit. It does **not** make `Composite` hold mixed-family constituents.

### Activities fire on triggers; Day-N is a projection

Each bound activity declares a **trigger** — a lifecycle hook (`on_provision`, `on_decommission`, …), a schedule (recurring), or an event (drift/alert) — generalizing the subscription `lifecycle_policy` `on_source_*` set. **Day 0/1/2 is a projection over triggers, not a stored field** (flow doc §5): bootstrap/provision hooks read as Day-0/1, operate/drift hooks read as Day-2. Each firing is a `Converge` on the bound consumable (ADR-030) — there is no separate "Day-2 subsystem."

### Lifecycle coupling

The System has one lifecycle; its bound activities couple to it through the **existing** subscription `lifecycle_policy` (`on_source_suspend` / `on_source_cancel` / `on_source_expire`) — suspend the System and its recurring processes pause; decommission it and its bound processes deregister. No new coupling mechanism.

### Grounded in standards

A Template is essentially a **TOSCA Service Template** — a topology of nodes (resources) + **workflows** (processes) + policies as one deployable unit — and maps cleanly to **OAM** (components + traits + application). UDLM already adopts TOSCA relationship types; "Template ≈ Service Template" grounds the term rather than inventing one (standards-adoption methodology).

### Composable infrastructure is a Provider capability, not a tier

"Composable infrastructure" (HPE Synergy, Dell MX, Liqid / GigaIO, CXL memory pooling) means *disaggregated physical resources assembled on demand via API*. That is a **Provider capability** (ADR-004) — a provider declares it can compose a logical machine from pooled resources — **not** an assembly tier and **not** the `Composite` shape. It is named here only to keep "compose / composable / Composite / Template" from blurring: they are four distinct things.

### Scope

Per ADR-031/032 this is a **direction**, not a 1.0 build: **no schema change**, nothing existing is touched. It is implemented only when a use case needs it (the combine-Day-0/1/2 case) — reusing catalog items, the subscription binding, and consumables, and adding only the Template packaging.

## Data · Policy · Provider
- **Data** — a Template is a catalog definition (Requested); a System is a realized composite + bound-activity records (Realized); a Pattern is Knowledge (type-level intent).
- **Policy** — placement/validation apply per constituent as today; resolving a Pattern into a Template *is* policy (Intent → Requested); the `lifecycle_policy` on each binding governs the coupling (suspend/cancel propagation).
- **Provider** — constituents are fulfilled by their ordinary providers; bound processes are executed by process/automation providers (AAP/AWX naturalization); *composable-infrastructure* providers assemble constituents from pools. No new provider role — a capability declaration (ADR-004).

## Consequences
- The combined Day-0/1/2 unit is expressible with **no new states, no change to `Composite`, and no new entity shape** — a packaging + binding over the existing lifecycle. The tiers *are* Intent/Requested/Realized (T7: reduce to what exists).
- `Antipattern` gains its positive twin (`Pattern`); the architecture-pattern concept gets a real home in Knowledge/DAV, and it reads as type-level intent rather than a fourth thing.
- Templates are the concrete application of ADR-030's consumable model and the flow doc's trigger/day-N picture — they read cleanly only on top of those.
- The `entity_type` value pair (`Atomic` / `Composite`) is being renamed to say what it asserts (single- vs multi-constituent orchestration) in **its own PR** — this ADR depends on nothing about that rename and is written to survive it.
- **On-ramp to standardized architecture formats (post-1.0).** A Template is an orderable topology, and LikeC4 / C4 / TOSCA / ArchiMate / OAM are topology-description languages — so the mapping is near-mechanical (components → consumables, relationships → edges, workflows → bound processes). Three directions, all post-1.0:
  - **Ingest** — import a *descriptive* model (C4 / LikeC4 / ArchiMate) → a **Pattern** (Knowledge); a *deployable* one (TOSCA Service Template, RH Validated Pattern) → a **Template**. *(Pattern-lives-in-Knowledge pays off: a Pattern gains a standard interchange format, and DAV becomes the pattern library.)*
  - **Emit** — render a System / the estate *as* LikeC4 / C4. The model already carries the dependency graph, so a UDLM-data visualizer is a natural (post-1.0) DCM capability; the rendering is a formatter over that graph.
  - **Derive** — build a Template *from* deployed architecture: capture a running System (Realized / Discovered) as a reusable Template or Pattern. The reverse of instantiation; ties to brownfield ingestion and rehydration-from-intent.
  Because UDLM carries intent **and** realized and converges between them (ADR-030), an emitted or derived view is **never stale** — it can render the intended topology, the actual one, and the drift. Adopt the formats as I/O, don't reinvent; graduate to its own ADR when a use case makes it real.
- Deferred until a UC pulls it in (ADR-031).

## Alternatives considered
- **Widen `Composite` to mixed-family constituents** — rejected: relabels operational binding as structural containment, blurring the edge model.
- **Invent a standalone three-level taxonomy** — rejected: the tiers are already Intent/Requested/Realized; naming a projection beats coining a parallel model (T7).
- **Keep "Blueprint" as the tier name** — rejected: it is a vendor term in retreat and overloaded across the descriptive/deployable line; "Template" is the standards word (TOSCA/OAM) and pairs with System, while "Pattern" keeps the descriptive meaning.
- **Model it as a subscription only** — rejected: the subscription is the *binding* half; a Template is the *orderable definition* (Requested) + the binding + the structural composite. The subscription is reused, not renamed.
