# UDLM/DCM ADR-040 (STUB): Federation resolution — resolving rooted addresses across peers, tenants, and sovereignty borders

**Status:** Proposed — **STUB.** Full mechanics deferred, demand-driven; starts with the `peer` root. Needs eng alignment (federation + sovereignty are cross-cutting).
**Date:** 2026-07-21
**Type:** Architecture Decision Record (foundational — federation)
**Related:** ADR-038 **§10** (the addressing coordinate + routing authority this resolves); ADR-008 (peer wire-compatibility); ADR-005 §5 (cross-peer federation); **ADR-024 §1** (sovereignty hard-gate); ADR-012 (`data_reference` — `resolving_authority` + `residency`); ADR-010 (dependency-graph completion); URI (RFC 3986); DNS; JSON Pointer (RFC 6901)

**Settles (stub):** how rooted addresses *resolve* across peers / tenants / sovereignty borders — deferred, demand-driven, `peer` root first.

## Context
The scoped-Class ADR §10 defines a fully-qualifiable address — **`[<authority>/]<anchor>.<field-path>`** — with an
extensible routing-root registry (`peer`, `tenant`, `jurisdiction`, …), a dotted/filterable authority, and a
canonical HTTP-URL form. §10 deliberately deferred *how such an address is actually resolved*. This ADR settles
that: routing to the authority, cross-peer trust, the sovereignty gate at the wire, and caching.

## Decision — SHAPE (to be filled; leans recorded)
- **HTTP is the governed resolution transport.** A peer DCM exposes a governed resolver; a fully-qualified URL +
  auth + the sovereignty gate = resolution. Grounded in the `$id`-URL precedent — the address is a *name*;
  resolving it is a **governed GET**, never a free fetch (§10: address ≠ dereference).
- **Provenance + attribution via existing fields.** `resolving_authority` records *who* resolved; `residency`
  records *where the target resides*; a cross-authority / cross-border resolve is attributed and **hard-gated**
  (ADR-024 §1). No new provenance surface.
- **Authority resolution is Policy + peer, not DNS.** The dotted authority (`peer.dcm.eu-west`) is a *logical*
  routing key; how it maps to a reachable resolver is DCM policy (a peer registry), so the logical authority is
  never bound to a physical DNS host.
- **Demand-driven roots.** `peer` first (the federation case). `tenant`, `jurisdiction` when a use case makes
  them distinct authorities.

## Open questions (to resolve when scheduled)
- Peer discovery / registry: how a DCM learns its peers and their resolver endpoints.
- Cross-peer trust establishment: attestation/accreditation across control planes (ties to DCM ADR-022).
- Caching + staleness: may a resolved value be cached across a border, and for how long?
- Partition / failure semantics: what a cross-peer resolve returns when the peer is unreachable.
- The resolver API shape (likely OData/linked-data-aligned — see the paradigm's standards alignment).
- Wildcard/filter semantics on the authority hierarchy (`peer.dcm.eu.*`) for policy and routing.

## Consequences
- Turns §10's addressing frame into a working federated resolution path — without which cross-peer addresses are
  names with no resolver.
- Cross-cutting (federation + sovereignty) → eng-alignment gated, like its parent paradigm ADR.
