# ADR-029: Inventory — optional ancillary observed-resource types

**Status:** Proposed (2026-07-19)
**Related:** ADR-013 (not a hardware SoR — **refined here**); ADR-027 (families); ADR-007 (profile model); ADR-004 (provider capability declaration); ADR-002 (observational overlay precedent); the managed-vs-observed axis; must-ignore-unknown (federation forward-compat)

## Context

An operator wants to use **DCM as their system inventory** — one authoritative model of everything in the estate (hosts, CPUs, drives, GPUs, NICs, switches) — to drive shutdown ordering, DR/rehydration, capacity/placement, blast-radius, cost, and audit (the C1–C8 use cases). The homelab estate already does exactly this.

ADR-013 ("not a hardware component system-of-record") removed `Hardware.Processor` / `Hardware.StorageDevice` / `Hardware.GraphicsProcessor`. That was **half right**: correct not to force hardware inventory on everyone, but wrong to *delete* it — real consumers need observed inventory, and the estate broke (every processor/drive/GPU record now fails type validation).

The governing constraint, in the operator's words: *use DCM as my system inventory, without causing needless work for institutions that don't want to track that.* So inventory must be **opt-in and zero-cost when unused** — powerful to adopt, invisible to skip.

## Decision

**Inventory is optional, delivered by ancillary observed-resource types — opt-in through existing mechanisms (classification, profiles, capability declaration), not a new container.**

### 1. `classification: substrate | ancillary` on the resource-type spec (default `substrate`)
An **ancillary** type is:
- **Observe-only** — valid solely as `Discovered`/`Realized` records; **never** on the Intent/catalog authoring surface. You *observe* inventory; you never *author* or *provision* it.
- **Structurally subordinate** — every instance is `contained_by` a substrate resource (a CPU with no host is meaningless; a checkable invariant).
- **Observed-provenance-bearing** — records which probe/provider observed it and when; MAY carry observed health/liveness.
- **Policy-readable, never authored** — placement/recovery/cost/audit *read* it; nothing writes intent to it.

### 2. Optionality via existing mechanisms — no new "module" primitive
The ancillary types are grouped only by their shared `classification: ancillary` tag ("Inventory" is the domain name for that set, not a container). Optionality reuses what UDLM already has: a **profile includes or omits** them via its composed set (ADR-007); a realization/peer **declares inventory as a capability** (ADR-004); conformance treats `ancillary` as an **optional tier** (non-Tier-1); and a peer that does not implement them **ignores them** (must-ignore-unknown), contributing no fields and staying fully conformant. Built-in profiles: homelab / sovereign **include** the ancillary types; a lean service-only profile **omits** them.

### 3. Zero-touch on substrate types
Ancillary records attach **inbound** (`contained_by` the host) — no substrate type (`BareMetalHost`, etc.) gains a required field, and nobody is forced to enumerate hardware. Adopting Inventory changes *nothing* for a non-adopter.

### 4. First members
Revive `Hardware.Processor`, `Hardware.StorageDevice`, `Hardware.GraphicsProcessor`, modernized to the current model (`family: Resource` + `entity_type: Atomic` per ADR-027; `edge_type` per ADR-026), classified `ancillary`. **`Hardware.BMC` / `NetworkInterface` / `BiosProfile` remain substrate** — they are control-plane-*actionable* (Redfish power, NMstate config, SUM), which is the line that separates substrate from ancillary.

### The refined ADR-013 boundary
> DCM is **always the system-of-record for the resources whose lifecycle it owns** (what it provisions and manages). It is **not currently designed to be a *complete* inventory system-of-record** for everything observed — carrying ancillary/observed inventory beyond what it manages is optional. It is **never a hardware authoring/provisioning surface**: ancillary items are populated by discovery or reported by providers at realize, never authored. ADR-013's real boundary stands, sharpened.

### Data · Policy · Provider
- **Data** — ancillary records are observed inventory the substrate carries (realized-only), identified by the `ancillary` classification (optional).
- **Policy** — excluded from placement/provisioning *intent*; policy may *read* ancillary state (a drive's SMART health → recovery gating) but never authors it.
- **Provider** — ancillary records are **injected by two sources**: a **discovery / fleet-probe provider** (observed provenance), and a **fulfillment provider reporting the inventory it realized onto** at realize time (created provenance) — e.g. a compute provider reporting the specific CPU / drive it provisioned onto. Both are `contained_by` the host they report; no provider *provisions* an ancillary item as a target — they observe or report it. A provider can inject inventory items **whether or not the deployment tracks system-wide inventory** — injection is per-provider and incremental, so even a deployment that is not a complete inventory SoR still gets whatever its providers report.

## Consequences
- The estate's hardware records validate again; the dcm-side `kind`→`edge_type` migration unblocks once the revived types land on udlm main and `UDLM_REF` is bumped.
- Conformance gains an optional **Inventory tier**; Tier-1 substrate conformance is unchanged. Non-adopters bear no cost.
- A clean home for future observed-inventory types — network switches/ports (UC C7), firmware/versions (UC C8) — without touching core substrate.
- **Deferred (not decided here):** observed-only *overlays on substrate types* (a NIC's live link state, a BMC's sensor readings). Ancillary is type-level for now; revisit if C7/C8 demand per-field observed overlays.

## Alternatives considered
- **Re-add the types as normal substrate types** — rejected: leaks hardware onto the catalog/authoring surface (the DCIM ADR-013 rightly refused) and burdens non-trackers.
- **Keep them deleted; model inventory outside UDLM** — rejected: fragments the estate system-of-record; consumers (placement/recovery/DR/blast-radius) need it *in the graph*.
- **A coined "module" container** to make optionality explicit — rejected: `classification: ancillary` + profile inclusion (ADR-007) + an optional conformance tier already deliver opt-in / opt-out; a new "module" primitive is surface UDLM uses nowhere else.
- **A new top-level entity `family`** (alongside Resource/Process/Knowledge/Access) — rejected: ancillary items *are* observed-state Resources; the state-vs-execution family axis is the wrong axis for "observed vs actionable." That distinction is a classification + profile inclusion, not a family.
