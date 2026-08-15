# ADR-033: Templates — the orderable assembly, and the Pattern → Template → System chain

**Status:** Proposed (2026-07-19) — **requires engineering ratification**. Implemented: the `Template` classes (#405) and the `composition` record (ADR-067).
**Realized by:** `registry/composition.schema.json` · `docs/flows/template-assembly.md` · `tests/check_tier_state_conflation.py`
**Background — read first (the cold reader's on-ramp; skip if you have the context).** ADR-030 (the convergence lifecycle / four states — the spine this projects); ADR-027 (the `Composite` entity_type — **unchanged** here; a separate PR renames its *values*); `docs/spec/lifecycle/subscription-lifecycle.md` (the binding + `lifecycle_policy` this reuses); [lifecycle-convergence flow](../flows/lifecycle-convergence.md) (triggers, day-N as projection); ADR-006 (each activity is a convergence firing); ADR-PROV-002 (provider capability — where *composable infrastructure* lives); `registry/standards-adoption-register.md` (TOSCA); AAP/AWX composite-process naturalization.

## Context

A recurring need: order and manage **a set of resources together with the processes that stand them up and operate them** — a stack of VMs/DBs plus its provisioning workflow, nightly backup, and monthly patch — as **one** lifecycle-coupled unit spanning **Day 0/1/2**. Modelling it raised a fork: *widen the definition of "Composite," or introduce a term above it?*

Two facts decided it:
1. **The process↔resource link is operational *binding*, not containment.** A backup isn't a *part* of the stack the way a VM is — it *operates on* it. Widening `Composite` (structural, same-family, `contained_by`) to "own" processes would relabel a binding as containment, re-blurring the line ADR-026's edge model just sharpened. → **a term above Composite; the `Composite` entity_type is untouched.**
2. **The tiers we kept reaching for already exist in the model — as the definition/instance split.** "Reusable design → orderable definition → running instance" is not a new taxonomy; it is `resource_type → realized entity` at assembly scale, with one extra definition tier because a design can be refined before it is cut. So the decision is to *name* that projection, not invent a parallel one.

## Decision

**The orderable assembly is a `Template`, and `Pattern` / `Template` / `System` is a refinement chain at assembly scale: two definitions and one instance.** No new states and no new primitive — a definition is a class when someone offers it and a `composition` record when nobody does (ADR-067), and the instance is an ordinary realized entity.

### Two definitions and one instance

**The tiers are not lifecycle states.** One Pattern yields many Templates and one Template yields many Systems (below), while states are 1:1 within a record — one record has exactly one intent and exactly one realized. A many-from-one relationship is a reference between records, never a state transition.

| Tier | What it is | What it is, in the model | Home |
|---|---|---|---|
| **Pattern** | the reusable, provider-neutral design ("how a 3-tier app is built"); names shape and rules, not parts — **not orderable** | a **definition**: a composition whose parts name capabilities rather than realizable classes, so the shape is still open | a `composition` record, or a class if someone offers it (ADR-067) |
| **Template** | that design cut down to fixed parts — a concrete, **orderable** definition | a **definition**: a composition every part of which names something a provider can realize | a `Template.<Category>.<Author>` class when someone stands behind it as an offer; a `composition` record when nobody does |
| **System** | the Template realized: real instances + the provider's specific output (IDs/addresses) | an **instance** — and the ONLY one of the three that carries `states` | a realized entity |

**Which one a composition is stays derived, never declared.** A composition is a Template when every constituent names something a provider can realize; one naming a `Capability` leaves the shape open and it is still a Pattern. `lifecycle_archetype` already separates `provisioning` from `curation`, so this is computable today — no stored `is_pattern` flag, and the boundary is allowed to be fuzzy (a composition may have cut some parts and not others). Same discipline as `has_constituents` and `portability`: derived, never stored (DRV-001).

### The two arrows

They are different in kind, and each is named for what it does:

- **Pattern → Template is refinement** — a `refines` reference between two definitions. Policy/profile resolution is what happens along it: enrich, validate, place, and pin "FSI profile, OpenShift, HA Postgres, sovereign placement". The **Pattern persists**, so **one Pattern → many Templates** (a homelab/dev Template and an FSI/prod Template of the same design), exactly as one `resource_type` → many records written against it. The chain is walked, never flattened (DRV-001), and it may be arbitrarily deep: a broad Pattern refining into a narrower Pattern into a Template is an ordinary thing to want, and states could not have nested.
- **Template → System is realization** — `Converge` (ADR-030), the existing machinery. The **Template persists**, so **one Template → many Systems** (one per customer/environment), exactly as one definition → many realized instances. This is the arrow that *does* cross into the four states, because the System is where they live.
- **Brownfield.** A System observed with *no* Template behind it is greened by **ingesting it as a `composition` record and promoting it** (ADR-067) — the same adoption act one scope up. Same machinery, no new path.

The whole thing is fractal: `resource_type → request → realized` for a single entity is `Pattern → Template → System` for an assembly.

### Why the tiers are not the four states

The fractal reading above decides it. For a single entity a `resource_type` is a **class** — a record in the registry, portable vocabulary, no tenant — and a realized entity is a **different record**, with the four states inside it. `Compute.VM` is not the "Intent state" of a particular VM; it is a definition, and the VM's intent is a block on the VM's own record. One scope up, the same split gives two definitions and one instance.

Three properties confirm it, each independent of the cardinality argument:

- **Different lifecycles.** A Template is published, versioned and immutable under the publish law; a System is mutable and drifts. One record would force one lifecycle onto both.
- **Different tenancy.** A System belongs to exactly one tenant (`GRP-INV-001`, non-overridable). A Template offered to several teams belongs to none. Collapsing them makes portable vocabulary tenant-owned.
- **Different kinds of truth.** A definition is **declarative** — true because someone wrote it, and true until someone writes something else. A System is **observational** — true *as of an instant*, with `expected_observation` declaring how fast that truth decays (ADR-048). One record means one freshness contract, so a drawing would be re-validated on a cadence, or a stale System accepted because its Template had not changed.

`Pattern = Intent, Template = Requested, System = Realized` is the reading to avoid, and it is worth naming because it looks right: three tiers, three states, in order. It holds until someone orders the same Template twice.

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

"Composable infrastructure" (HPE Synergy, Dell MX, Liqid / GigaIO, CXL memory pooling) means *disaggregated physical resources assembled on demand via API*. That is a **Provider capability** (ADR-PROV-002) — a provider declares it can compose a logical machine from pooled resources — **not** an assembly tier and **not** the `Composite` shape. It is named here only to keep "compose / composable / Composite / Template" from blurring: they are four distinct things.

### Scope

Per ADR-031/032 this is a **direction**, not a 0.1 build: **no schema change**, nothing existing is touched. It is implemented only when a use case needs it (the combine-Day-0/1/2 case) — reusing catalog items, the subscription binding, and consumables, and adding only the Template packaging.

## Data · Policy · Provider
- **Data** — a Template and a Pattern are **definitions** (a class when offered, a `composition` record when not); a System is a realized composite + bound-activity records, and the only one of the three carrying `states`.
- **Policy** — placement/validation apply per constituent as today; resolving a Pattern into a Template *is* policy — enrich, validate, place; the `lifecycle_policy` on each binding governs the coupling (suspend/cancel propagation).
- **Provider** — constituents are fulfilled by their ordinary providers; bound processes are executed by process/automation providers (AAP/AWX naturalization); *composable-infrastructure* providers assemble constituents from pools. No new provider role — a capability declaration (ADR-PROV-002).

## Consequences
- The combined Day-0/1/2 unit is expressible with **no new states and no change to `Composite`** — a packaging + binding over the existing lifecycle. The one new artifact is the `composition` record (ADR-067), and it reuses the shared composition shape rather than coining a second one (T7).
- `Antipattern` gains its positive twin (`Pattern`); the architecture-pattern concept gets a real home in Knowledge/DAV, and it reads as a definition rather than a fourth thing.
- Templates are the concrete application of ADR-030's consumable model and the flow doc's trigger/day-N picture — they read cleanly only on top of those.
- **On-ramp to standardized architecture formats (post-1.0).** A Template is an orderable topology, and LikeC4 / C4 / TOSCA / ArchiMate / OAM are topology-description languages — so the mapping is near-mechanical (components → consumables, relationships → edges, workflows → bound processes). Three directions, all post-1.0:
  - **Ingest** — import a *descriptive* model (C4 / LikeC4 / ArchiMate) → a **Pattern** (Knowledge); a *deployable* one (TOSCA Service Template, RH Validated Pattern) → a **Template**. An ingested model arrives as a `composition` record and is promoted if someone offers it (ADR-067); a Pattern gains a standard interchange format, and DAV becomes the pattern library.
  - **Emit** — render a System / the estate *as* LikeC4 / C4. The model already carries the dependency graph, so a UDLM-data visualizer is a natural (post-1.0) control-plane capability; the rendering is a formatter over that graph.
  - **Derive** — build a Template *from* deployed architecture: capture a running System (Realized / Discovered) as a reusable Template or Pattern. The reverse of instantiation; ties to brownfield ingestion and rehydration-from-intent.
  Because UDLM carries intent **and** realized and converges between them (ADR-030), an emitted or derived view is **never stale** — it can render the intended topology, the actual one, and the drift. Adopt the formats as I/O, don't reinvent; graduate to its own ADR when a use case makes it real.
- Deferred until a UC pulls it in (ADR-031).

## Alternatives considered
- **Widen `Composite` to mixed-family constituents** — rejected: relabels operational binding as structural containment, blurring the edge model.
- **Invent a standalone three-level taxonomy** — rejected: the tiers are already the model's definition/instance split at assembly scale; naming a projection beats coining a parallel model (T7).
- **Keep "Blueprint" as the tier name** — rejected: it is a vendor term in retreat and overloaded across the descriptive/deployable line; "Template" is the standards word (TOSCA/OAM) and pairs with System, while "Pattern" keeps the descriptive meaning.
- **Model it as a subscription only** — rejected: the subscription is the *binding* half; a Template is the *orderable definition* + the binding + the structural composite. The subscription is reused, not renamed.
