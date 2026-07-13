# Foundational (root) resources — the selectable base of the dependency graph

**What this settles:** a class of resources — **Locations, Networks, and their kin** — are not things a consumer or provider *invents per request*; they are **existing, selectable resources that everything else depends on**. This names that class, says how it is populated and selected, and fixes the rule that dependents **reference** a foundational resource rather than defining one inline.

## The class

A **foundational resource** (equivalently, a *root resource*) is one that:

1. **Is a root of the dependency graph** — other resources `depends_on` / `references` / `contained_by` it; it depends on little or nothing itself. In the derived shutdown order it sits in the **deepest tiers** (it outlives its dependents); in blast-radius it is the resource whose loss has the widest reach.
2. **Is selected, not invented** — a consumer's intent and a provider's realization **reference an existing** foundational resource by identity; they do not carry a free-form copy of it. A VM does not describe a network segment — it selects a `Network.VirtualNetwork`. It does not describe a rack — it selects a `Facility.Location`.
3. **Is populated by the platform and/or a responsible provider** — the selectable set of foundational resources comes from **a platform-level data layer** (an admin/SRE defines the catalog of locations/networks as a base layer, `layering-and-versioning.md`) **and/or** the **provider that owns them advertises them** (a Facility.Location provider, a network provider) with their capacity/capability (`provider-contract.md` registration).
4. **Is eligibility-governed** — which foundational resources a given consumer may select is **policy** (`policy-contract.md`) over the provider-supplied and platform-defined data, not a free choice. The responsible provider's data + policy decide the eligible set; the consumer selects within it.

## Base guidance, org ratification, provider variants

UDLM ships the **base definition** of each foundational resource as **guidance**, plus the **mechanisms to support and enforce** its production and consumption (typed relationships, policy match sources, the Governance Matrix). It does **not** mandate a closed vocabulary. **The organization ratifies** what a base resource definition is for their estate, and **providers define their offerings** — a provider may offer a variant base type (a `Network.Port` in place of `Network.VirtualNetwork`, say), and the org decides — via policy/Governance-Matrix — which base or variant its providers must **produce** and its consumers may **consume**. The graph, placement, and diagnostics read whatever typed edges exist; they never require one specific type. So this table is the *recommended* base set and starting guidance, not a fixed list.

## The members (initial set)

| Foundational resource | Owned/advertised by | Dependents select it as |
|---|---|---|
| **`Facility.Location`** (site/room/rack/row) | platform data layer and/or a facilities/location provider | placement — `references Facility.Location` |
| **`Network.VirtualNetwork`** (segment/VLAN/overlay) | platform data layer and/or a network provider | attachment — `references Network.VirtualNetwork` |
| **`Network.IPAddress`** | IPAM / network provider | `depends_on` (dynamic/static/byo — ADR-009 fulfillment) |
| **`Storage.Pool` / `Storage.Cluster`** | storage provider | volumes provisioned from — `depends_on` |
| **`Security.DirectoryService`** (realm/identity) | identity provider | scope-derived from `tenant_uuid` (the pervasive realm edge) |
| **`Facility.PowerFeed`** | facilities provider | power — `Hardware.PowerSupply references Facility.PowerFeed` |

The list is open — the test is the four properties above, not membership on this table.

## The rule (why placement/networks are references, not fields)

A dependent resource's spec carries **the reference and the intent knobs it owns**, never a redefinition of the foundational resource:

- **Right:** `Compute.VirtualMachine.spec.placement.location_ref → <Facility.Location handle>`, `networks[].network_ref → <Network.VirtualNetwork handle>`, plus VM-owned knobs (`ip_mode`, affinity to other resources).
- **Wrong:** `placement.location: "rack-3"` or `networks[].segment: "dmz"` as free-form strings — that invents a location/network the platform can't govern, dedup, place against, or reason about for blast-radius.

This keeps one source of truth per foundational resource, lets policy govern selection, and makes the dependency graph honest — the estate's ordered shutdown, blast-radius, and rehydration all traverse these references, so they must point at real resources, not strings.

## Consequences

- **Resource types that consume a foundational resource declare a `references`/`depends_on` relationship to it** (guidance/example per ADR-009 §4 — a template, not a gate), and put the *selection* (`*_ref`) in their spec.
- **Providers of foundational resources advertise their inventory + capacity** at registration (feeds placement — the September P3 capacity gap), and **policy governs eligibility** over that data.
- **Foundational resources anchor fault domains** — a `Facility.Location` is the natural home for the shared-fault-domain reasoning the dependency graph needs (the September P4 gap): resources selecting the same location share its fault domain.

See `entities/entity-relationships.md`, `foundations/layering-and-versioning.md` (the platform data layer), `contracts/provider-contract.md` §1b (selection vs realized relationships), and `docs/graph-integrity.md` (the graph these roots anchor).
