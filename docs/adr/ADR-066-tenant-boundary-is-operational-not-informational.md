# UDLM ADR-066: A tenant boundary is an **operational** boundary, not an audit or visibility one

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decision 2026-08-08
**Date:** 2026-08-08
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **ADR-041** (policy is an information firewall): establishes two inspection surfaces — **structural/L3-L4**, matching the *unresolved pointer* (edge `target`, `relation`, `nature`, the authority in the address) **without dereferencing**, and **value/L7**, matching the dereferenced datum. Its own words: *"**T4 (address ≠ dereference) cutting both ways**: you can police the address without dereferencing the data."* This ADR runs that sentence in the other direction.
- **`CTX-001`** (universal-groups §13.5): cross-tenant relationships require an active cross-tenant authorization **or** a resource type declared `publicly_stakeable` / `publicly_allocatable`. The standing-declaration escape hatch already exists in the rule.
- **`CMP-009`** (composite-service-model §10.1): bindings re-resolve at **request validation**, not only at catalog admission, *"so no constituent is provisioned and no compensation is needed… a binding caught here costs a rejected request, whereas the same binding caught at dispatch costs a partially realized composite and a compensation path."* The precedent for where a cross-tenant refusal belongs.
- **`GRP-INV-002`** (universal-groups §2.3): constituent relationships may not cross tenant_boundary boundaries — non-overridable. The reason a composite's cross-tenant parts are *edges*, and therefore the reason the required-grant set is computable from the edge graph.
- **ADR-008** (the UDLM/DCM boundary): access **determination** is external. UDLM carries the data and the contract, never the decision procedure. Unchanged here.

---

## Context

A consumer orders a composite. Some of its parts resolve to resources another tenant owns — a shared VLAN, a
platform namespace, a cluster. `CTX-001` requires an active authorization for each, and today the consumer
discovers which ones are missing **when dispatch fails**: a partially realized composite, a compensation path,
and a support ticket.

The failure is not the gate. The gate is correct. The failure is that **nothing tells the consumer in advance**,
and the reason nothing tells them is that the tenant boundary has been doing double duty — governing both what a
subject may *do* and what a subject may *know*. Ownership documentation states the second explicitly: a consumer
*"cannot see the pool entity"*, *"cannot … see its owner's configuration details"*, absent a grant.

Withholding the **payload** is right. Withholding the **fact that a governed relationship exists and needs a
grant** is not — it converts a governance requirement into a runtime surprise, and it does so without protecting
anything, because the consumer learns the same fact seconds later from a failure.

One direction of this is already open and nobody considers it a leak: a resource owner *"can see all active
stakes on their resource — this is how they know which consumers are affected by a planned decommission."*

## Decision

**1. The tenant boundary is operational. It is not an audit or visibility boundary.**

| | Surface | Question | Governed by |
|---|---|---|---|
| **Operational** | L7 / value | may I read this datum, act on it, own it? | tenancy — exclusive, structural, `CTX-001` |
| **Informational** | L3/L4 / structural | does this edge exist, whose is it, do I hold a grant? | a **release** decision, not an ownership one |

A subject that may not *act* on another tenant's resource may still be told that a governed relationship to it
exists. Address released, payload withheld — ADR-041's structural surface used for disclosure rather than for
policing. **No new inspection surface is introduced.**

**2. The required-grant set is DERIVED, never discovered.** For any request or catalog offering, walk the
constituent and dependency edges, resolve each target's owning tenant, and diff against the requesting tenant's
active authorizations. The result — the grants this act requires and which are missing — is computed from data
the model already holds. It is not stored (DRV-001).

**3. It is refused at admission, not at dispatch.** `CMP-009`'s argument transfers verbatim with "authorization"
substituted for "binding": the check runs after expansion and before policy and dispatch, so no constituent is
provisioned and no compensation is needed.

**4. What is released is the edge, never the target.** Edge existence, `relation`, `nature`, the owning
authority, the resource **type**, and the grant's status. Not the target's spec, not its configuration, not its
realized outputs. A profile may narrow this further; it may not widen it.

**5. A cross-tenant act is audited to BOTH tenants.** The granting tenant and the receiving tenant each see the
act. This closes the `CTX-004` asymmetry: platform-managed authorizations created *on behalf of* a tenant are
today *"visible in the platform admin audit log"* — a grant made in a tenant's name that the tenant cannot audit
is precisely the boundary this ADR says tenancy must not be.

### Proposed rules

Four rules are proposed. Their **definitions** must be authored in the `CTX` prefix's registered home —
`docs/spec/foundations/universal-groups.md` §13.5, per the rule-ID registry and `tests/check_single_source.py`
— and this ADR only describes what they are to say:

- **CTX-005 — derive, surface, refuse early.** The required-grant set for a request or catalog offering is
  derived from its edge graph and surfaced before admission; a cross-tenant relationship whose authorization is
  missing is refused at request validation, never first discovered at dispatch.
- **CTX-006 — structural release.** The existence of a cross-tenant edge, its relation and nature, its target's
  owning authority and resource type, and the grant's status are releasable to the requesting tenant. The
  target's spec, configuration, and realized outputs are not.
- **CTX-007 — both parties see the act.** A cross-tenant act is audited to the granting and the receiving tenant
  alike, and a `platform_managed` authorization is visible to the tenant on whose behalf it was created, not
  only to the platform administrator.
- **CTX-008 — standing declaration.** A resource type declared `publicly_stakeable` / `publicly_allocatable`
  satisfies CTX-001 as a standing declaration; the declaration is a field on the Resource Type Spec, and the
  required-grant set reports it as *satisfied by standing declaration* rather than omitting it.

## Data · Policy · Provider

- **Data** — no new stored field. The required-grant set is a projection over the edge graph plus the active
  `cross_tenant_authorization` records. `publicly_stakeable` / `publicly_allocatable` become real Resource Type
  Spec fields (today they are cited by `CTX-001` and exist in **no schema** — see Open questions).
- **Policy** — the release in Decision 4 is an ADR-041 **egress** decision on the structural surface, and a
  profile dial: a sovereign profile may narrow what is released; none may withhold the *existence* of a required
  grant, because that is the surprise this ADR removes.
- **Provider** — unchanged. Providers neither compute nor consume the grant set; the refusal happens before
  dispatch, which is the point.

## Open questions for engineering (what this ADR tees up)

1. **Three cited-but-absent fields.** `publicly_stakeable` / `publicly_allocatable` appear in one document and
   **zero schemas**; `ownership_model` appears in `ownership-sharing-allocation.md` examples and **zero
   schemas**; a `dcm-group.schema.json` under registry/ was cited three times and **did not exist**
   (superseded by `Grouping`; the citations are corrected under PR A). The rules are
   written as though these landed. Which are real intent and which are stale?
2. **Does the grant set surface at catalog render, or only at request validation?** Rendering it on the offering
   ("ordering this requires 2 authorizations you do not hold") is strictly better UX and strictly more
   disclosure. It is the same computation at a different moment.
3. **Reverse disclosure.** Should the *granting* tenant see pending demand — "3 tenants attempted to order
   something requiring a stake in VLAN-100"? Useful for capacity and for deciding whether to declare the type
   `publicly_stakeable`. Also the most disclosure-forward item here.
4. **Grant bounding.** Authorizations carry `valid_from` / `expires_at` / `auto_renew`, and `expires_at: null`
   means *perpetual until revoked* — the wrong default for a grant, and there is no **use** bound at all.
   Tracked separately (see Related).

## Consequences

- The common cross-tenant failure moves from **dispatch** to **admission**: a rejected request instead of a
  partially realized composite plus compensation. This is `CMP-009`'s trade, already accepted once.
- A composite becomes honestly orderable: what it needs from other tenants is legible before anyone commits.
- `CTX-004`'s audit asymmetry closes — a grant in a tenant's name is auditable by that tenant.
- The `publicly_stakeable` lever becomes usable, which removes the grant dance entirely for the shared
  infrastructure case (platform namespace, cluster, fabric) rather than merely making it visible.
- **Nothing about the operational boundary moves.** `GRP-INV-001`/`002` and `CTX-001` are untouched; exclusivity,
  ownership, and the structural lock are exactly as they were. This ADR only stops the boundary from silently
  doing a second job.

## Alternatives considered

- **Make tenancy an embeddable characteristic of a grouping.** Rejected: the cross-tenant issue exists *because*
  tenancy is exclusive (`GRP-INV-001`, `exclusivity.per_member: one`), not because of where it is stored.
  Embedding it in a many-per-member structure either preserves the exclusivity (no change but the spelling) or
  loses it (and every question tenancy answers — who pays, who may decommission, whose audit scope, who is
  accountable for drift — becomes ambiguous). A border is not dissolved by re-describing where it is kept.
- **Store the required-grant set on the catalog item.** Rejected as a DRV-001 violation: it is derivable from
  the edges and the active authorizations, and a stored copy goes stale the moment a grant is revoked.
- **Leave discovery at dispatch and improve the error message.** Rejected: the cost is a partially realized
  composite and a compensation path, which no error message recovers.

## Related

- **ADR-041** — policy as information firewall; the structural/value split this ADR reuses for disclosure.
- **`CMP-009`** — refuse at request validation, not dispatch; the precedent for Decision 3.
- **#405** — Pattern/Template/Provider class tiers; the worked composite whose cross-tenant edges motivated this.
- **Grant bounding issue** — time- and use-bounded authorization grants (Open question 4).
