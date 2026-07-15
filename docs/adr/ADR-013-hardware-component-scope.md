# UDLM ADR-013: UDLM/DCM is not a hardware component system-of-record (for now)

**Status:** Accepted (maintainer decision, 2026-07-15)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-008 (UDLM/DCM boundary); DCM ADR-017 (brownfield/discovered ingestion); the DMTF Redfish adoption (`registry/standards-adoption-register.md`); reviewer feedback on `dcm-project/udlm` #40 (Ondra Macháček / `machacekondra`, Noam `NoamNakash`).

## Context

During estate **discovery**, hardware was mapped all the way down to the component level — individual memory modules, processors, storage devices, GPUs, power supplies — as `Hardware.*` resource types, in order to **validate the dependency graph** end to end. Those component types were then carried into the registry as first-class `Infrastructure Resource` types with the default **`provisioning`** lifecycle archetype (Intent→Requested→Realized→Discovered via a provider).

Reviewers rightly flagged this (#40): *"how would DCM manage a bare-metal memory module? These are physical things."* Modeling a DIMM as a provisioning-archetype resource implies a managed lifecycle it does not have — DCM never requests, places, or provisions a memory module. It only ever **discovers** one, as a component of a host.

## Decision

**UDLM/DCM is a control plane for provisioning and governing resources — it is not a hardware component system-of-record (DCIM).** Component-level hardware types are **out of scope** for the 1.0 catalog:

- **Removed:** `Hardware.MemoryModule`, `Hardware.Processor`, `Hardware.StorageDevice`, `Hardware.GraphicsProcessor`, `Hardware.PowerSupply` — pure component inventory that DCM does not manage.
- **Kept — DCM genuinely acts on these:** `Hardware.BMC` (Redfish power/reset), `Hardware.BiosProfile` (BIOS apply), `Hardware.NetworkInterface` (bond/bridge configuration — part of the host-network model). These are *managed*, not merely discovered.
- **Placement facts live on the host, not as components.** Aggregate capacity (memory, CPU, disk) and accelerator presence (GPU) are **attributes/capabilities of the Compute host** (`Compute.ComputerSystem` / `Compute.BareMetalHost`) — which is all placement actually needs — rather than a graph of component records.

## Why

1. **Control plane, not DCIM.** Everything in the managed catalog should be requestable/provisioned. A component the platform can only ever *observe* doesn't belong in the same surface as a VM or a cluster.
2. **We don't want the toil.** Maintaining discovered inventory we don't manage carries real, ongoing cost — data retention, staleness, and continuous reconciliation against physical reality — for **no control-plane value**. The maintainer's call: not worth it.
3. **The dependency graph doesn't need DIMM-level nodes.** Host-level modeling (a VM depends on a host with sufficient memory/CPU/GPU) validates the graph without component records. The component-level detail was a *discovery-validation* artifact, not a modeling requirement.
4. **Managed-vs-discovered clarity.** Keeping these out removes the ambiguity that a `provisioning`-archetype hardware type creates.

## How it could be done in the future (if a real need arises)

If UDLM/DCM ever needs to be a hardware asset/inventory authority, do it **without** polluting the managed request surface:

- **A discovery-only lifecycle archetype.** Add a third `lifecycle_archetype` (e.g. `discovery`) beyond `provisioning`/`curation` — a discovered asset that is never requested or provisioned, populated by a discovery provider / brownfield ingestion (DCM ADR-017), with its own retention policy, explicitly outside the request catalog.
- **Or integrate an external DCIM / Redfish aggregator** as an *information provider* (the `information-providers` contract) — let the SoR live where SoRs live, and reference it, rather than modeling every component natively.

Either path is additive and does not disturb the managed model. Until there's a concrete driver, we don't build it.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the managed catalog no longer carries component-inventory types; hardware facts placement needs are attributes/capabilities on the Compute host. The DMTF Redfish *vocabulary* adoption stays (it grounds `ComputerSystem`/`BMC`/`BiosProfile`).
- **Policy (DCM):** placement scores against host aggregate capacity + declared capabilities, not a component graph.
- **Provider:** a provider declares host capacity/GPU capability; no provider is asked to "provision a memory module."

## Consequences
- Remove the five component `Hardware.*` type specs and repoint the references in `compute.bare-metal-host`, `storage.volume`, `storage.pool`, and `facility.location` to host aggregate-capacity attributes (or drop the component relationship).
- The estate (`roadfeldt-dcm`, ~58 files that model components) stops modeling hardware below the host — a coordinated cleanup, tracked separately since it's a different repo.
- Trim the Redfish register "Where" note (Processor/Memory/Drive lines) — Redfish remains adopted for the host + BMC/BIOS vocabulary.
- Reviewer threads on #40 (Ondra, Noam) resolve to "removed, out of scope — here's the ADR."
