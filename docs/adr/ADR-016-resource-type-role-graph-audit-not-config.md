# UDLM ADR-016: What a Resource Type Models — the dependency graph and the audit trail; the provider projects the configuration

**Status:** Proposed (2026-07-15)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-008 (UDLM/DCM boundary — *could a peer realize this differently and still be valid? yes → DCM*); ADR-014 (optionality with conformity — the data carries transport + conformity, not the provider's policy); ADR-012 (data references — an image ref builds the dependency map) + DCM ADR-024 (reference resolution & change-impact); `contracts/provider-contract.md` §1a.3 (config-projection) and `PRV-010` (provider resource-type extension); DCM ADR-023 (naturalization). **Prior art:** Kubernetes CRD `spec` vs controller-owned behaviour; Crossplane Composition (the claim is thin, the composition is the provider's); OAM Component vs Trait.

## Context

A resource-type spec is tempting to grow into a full model of everything a resource can be configured with — every container env var and security-context field, every VM device knob. That instinct is wrong, and it breaks the UDLM/DCM boundary: a peer that realizes the same intent with a *different* provider cannot read a spec bloated with one provider's config surface, and the model swells into a copy of every runtime's API. The recurring question — *"how granular should a resource type be?"* — needs one settled answer. And its corollary: **when a provider genuinely can expose more, how does that get configured — without polluting the portable type?**

## Decision

**A resource type models the elements that bear the dependency graph and the audit trail; the provider projects the concrete configuration, and DCM is the means to configure it. UDLM is a *conduit* for config, not a *modeler* of it.**

### 1. What earns a field a place in the base type — three tests

A field belongs in the portable resource-type spec **only** if it is one of:
- **Graph-bearing** — it forms a dependency edge: a `data_reference` (image → a governed image record → base-image/library blast-radius, ADR-024), a relationship (`binds_to` a `Storage.Volume`, `contained_by` a `Cluster`, `references` a `Security.CredentialRef`), or a network/route/port that places the resource in the service graph.
- **Audit / provenance / identity-bearing** — the audit chain, sovereignty gate, or tenancy needs it: `uuid`, owner, `tenant_uuid`, `data_classification`, a pinned digest/version for provenance.
- **Observability / drift-bearing** — a typed output or realized signal the realization reconciles Discovered against Realized on.

The per-field review test: **"Does this form an edge, or does the audit chain / drift detector / sovereignty gate need it?"** Yes → model it (typed, reference-able, relationship-declared). No → it is provider-projected config (below).

### 2. The provider may expose more — and DCM is the means to configure it

Everything beyond the §1 subset is the **provider's configuration surface**. UDLM does not model it field-by-field, but a provider that wants to expose deeper config is not blocked — there is a governed channel:
- The provider **declares its config schema** at whatever depth it supports (`provider-contract.md` §1a.3): none → DCM projects a **text passthrough**; typed → DCM projects a **typed configuration interface**.
- **DCM projects that interface and the consumer configures it *through DCM*.** This is the means — a real configuration channel across the config lifecycle, not an opaque dead-drop.
- The set values are captured as **provider-namespaced extension data** (`PRV-010` `provider_extensions`): governed like any data (audit, provenance, tenancy) but **outside the portable base type**, and DCM computes `portability_breaking: true` and **notifies the consumer** — a consumer that relies on provider-X's extra config is not portable to provider-Y, and silent non-portability is prohibited.

So there are three tiers, not two: **portable base** (graph/audit/observability, every provider satisfies it) → **provider-projected config** (declared by the provider, projected + configured through DCM) → **provider extensions** (the captured values, namespaced, audited, portability-flagged). The concrete mechanism never enters the substrate (the naturalization boundary, DCM ADR-023).

### Worked example — container
- **Model (base):** `image` as a `data_reference` (dependency map + base-image blast-radius); mounts → `Storage.Volume` / `Security.CredentialRef` edges; `ports` → the service graph; the pinned digest (provenance); the `contained_by` / `references` / `depends_on` relationships.
- **Project + configure via DCM, don't model:** command/args, restart policy, replicas, security context, the runtime's remaining knobs — the provider declares them, DCM projects the interface, the consumer sets them, they land in `provider_extensions`, portability-flagged.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the graph/audit/observability-bearing subset — the portable, conformity-bearing base type.
- **Policy (DCM/org):** which projected config a consumer may set; the config interface DCM projects across the lifecycle.
- **Provider:** owns the concrete config schema, declares its config-projection depth, and naturalizes it (ADR-023).

## Options considered
- **(A) Model the full config surface in the type** — rejected: breaks the UDLM/DCM boundary, swells the model into a copy of every runtime's API, and the moment two providers differ the spec can no longer be shared.
- **(B) Model nothing; everything is provider config** — rejected: then there is no dependency graph, no audit trail, no drift baseline — UDLM's whole reason to exist.
- **(C) [chosen]** Model the graph + audit + observability subset as the portable base; project the rest through DCM (config-projection), captured as portability-flagged provider extensions.

## Consequences
- Resource-type specs stay thin, portable, and provider-neutral (ADR-008); any peer reads any spec.
- The dependency graph and audit trail are complete *because* the fields that bear them are exactly the fields we model — nothing rides on modeling config.
- A richer provider gives a richer configuration interface **without a spec change** — config depth is the provider's to offer and DCM's to project.
- Portability is honest: reliance on provider-exposed config is flagged, never silent (`PRV-010`).
- Enforced by SPEC-DESIGN §34.
- Reframes R6/containers: we model `image`/`storage`/`routes` as references **because they build the dependency map** — the audit/observability role, not config for its own sake.
