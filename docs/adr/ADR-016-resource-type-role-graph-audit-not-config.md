# UDLM ADR-016: What a Resource Type Models — the resource's portable definition; provider-specific config is stored extra; DCM is the state system-of-record

**Status:** Proposed (2026-07-15)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-008 (UDLM/DCM boundary — *could a peer realize this differently and still be valid? yes → DCM*); ADR-014 (optionality with conformity — the data carries transport + conformity, not the provider's policy); ADR-012 (data references — an image ref builds the dependency map) + DCM ADR-024 (reference resolution & change-impact); `contracts/provider-contract.md` §1a.3 (config-projection) and `PRV-010` (provider resource-type extension); DCM ADR-023 (naturalization). **Prior art:** Kubernetes CRD `spec` vs controller-owned behaviour; Crossplane Composition (the claim is thin, the composition is the provider's); OAM Component vs Trait.

## Context

A resource-type spec is tempting to grow into a full model of everything a resource can be configured with — every container env var and security-context field, every VM device knob. That instinct is wrong, and it breaks the UDLM/DCM boundary: a peer that realizes the same intent with a *different* provider cannot read a spec bloated with one provider's config surface, and the model swells into a copy of every runtime's API. The recurring question — *"how granular should a resource type be?"* — needs one settled answer. And its corollary: **when a provider genuinely can expose more, how does that get configured — without polluting the portable type?**

## Decision

**A resource type models the elements that bear the dependency graph and the audit trail; the provider projects the concrete configuration, and DCM is the means to configure it. UDLM is a *conduit* for config, not a *modeler* of it.**

### 1. The base type is the resource's *portable definition* — its standard config, its graph, its audit surface

The base resource-type spec defines **what the resource *is*** in DCM/UDLM, provider-neutrally — grounded in the adopted standard(s) for that resource (OAM Component + Kubernetes Container for a `Compute.Container`; Metal3 + Redfish for a bare-metal host). It carries, all portable:

- **Required + portable config** — the fields that *define* the resource and that **every provider of the type accepts**: a container's `image`, `resources`, `command`/`args`, `ports`, `mounts`, restart behaviour — the OAM/k8s shape. This is what a consumer authors to get *a container*, not *this vendor's container*.
- **Graph-bearing elements** — fields that form dependency edges: a `data_reference` (image → blast-radius, ADR-024), a relationship (`binds_to` a `Storage.Volume`, `contained_by` a `Cluster`, `references` a `Security.CredentialRef`), a network/route/port in the service graph.
- **Audit / provenance / identity / observability** — what the audit chain, sovereignty gate, tenancy, and drift baseline need.

The line that keeps the base thin is **portable vs provider-specific**, *not* config-vs-not-config: portable config that defines the resource belongs in the base; **provider-specific** config (a vendor's knobs) is the extra tier (§2). The per-field test: **is this portable across providers of this type (base), or specific to one provider (§2)?**

### 2. Provider-specific config is *extra data* — declared by the provider, configured through DCM, stored as state

Beyond the portable definition, a provider may accept **extra, provider-specific config**. UDLM does not model its schema field-by-field — the provider **declares it** (`provider-contract.md` §1a.3 config-projection: none → text passthrough; typed → a typed interface), and **DCM projects a configuration interface** so the consumer sets it *through DCM* — a real configuration channel across the config lifecycle, not an opaque dead-drop. The provider owns the *schema*.

The **values** are stored as provider-namespaced state — `provider_extensions` (`PRV-010`; **deprecated — subsumed by ADR-038's Provider-Class `SharedDataElement`, interim carrier retiring per #202**) — across Requested and Realized, governed like any state (audit, provenance, tenancy) and **portability-flagged** (`portability_breaking: true`, consumer notified — relying on a vendor's extra config isn't portable to another provider; silent non-portability is prohibited). So the two tiers are **portable base** (every provider satisfies it) → **provider-specific extra** (this provider, stored as `provider_extensions`), and **DCM stores both** (§3). The concrete *mechanism* never enters the substrate (naturalization, DCM ADR-023); the config *state* always does.

**Scope — where UDLM stops.** UDLM defines only **(a) the base resource type** and **(b) the extension model** (`provider_extensions`, `PRV-010`) that carries provider non-base data. The config **editor** is **pure DCM**: where a provider has a native editor for a thing (OpenShift's, for an OCP-backed resource), DCM **delegates to it**; where it does not, DCM exposes a **generic text editor and enforces the provider-declared schema** on it. That is the *realization* of config-projection (§1a.3), not the data model — named here only to place the boundary; it is specified DCM-side. **A delegated editor is never an audit bypass:** the contract binds a provider that exposes its own editor to **report the resulting realized updates back** and to support DCM's **before-and-after actor validation**, so audit / observability / provenance — **and the sovereignty hard-gate and tenant isolation** — hold at all times even when the edit happens in the provider's UI: the config tooling operates inside DCM's governance, never around it (`provider-contract.md` §1a.3).

### 3. DCM stores the config *state* — it is the state system-of-record

Ownership of the config *schema* is the provider's (§2). Ownership of the config *state* — the values across Requested / Realized / Discovered — is **DCM's**, and the two must not be conflated. *"The provider owns config"* is true of the schema, **not** of the state.

**DCM stores the config values — base *and* provider-specific — because that is what a system-of-record is for: drift is a diff** (Requested vs Realized vs Discovered), and **you cannot diff what you did not store.** This is consistent, not halfway: **if we store one component's config we store every component's, end to end across an application stack** — otherwise the stack's state is un-diffable and DCM is not the SoR. There is no "track the pointer instead of the values" shortcut; a `config_interface` reference (`{interface_type, endpoint | handle, schema_ref?}`) MAY *additionally* record where the provider exposes its edit UI, but it **never replaces** storing the state — it is a navigation/audit convenience only.

Provider-specific config values are stored as provider-namespaced state (`provider_extensions`, §2) — governed like any state (audit, provenance, tenancy) and portability-flagged — but stored. (This is *not* the ADR-013 case: ADR-013 declines to be the SoR for hardware components DCM does **not** manage; config of a resource DCM **does** manage is exactly its to record.)

**Corollary — complete coverage.** Every resource DCM manages has a **resource record type**, so its state (including config) is a stored, diffable record. Nothing DCM manages is a black box.

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
