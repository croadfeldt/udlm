# UDLM ADR-025: Resource references — AEP-124 resource association, resolved at reserve

**Status:** Proposed (2026-07-17)
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Adopts (T5):** **AEP-124 Resource association** (aep.dev/124) — reference another resource by its **resource path** (AEP-122); Apache-2.0, `compatible-reference`. UDLM adopts the AEP path-reference convention and adds only what AEP does not model: a resolved `target_uuid` as provenance (see §5). Concrete lineage: the Kubernetes `ObjectReference`/`ownerReference` idiom AEP generalizes (already cited by ADR-012).
**Related:** ADR-012 (data references — the *sibling* mechanism for reference-**data**, deliberately uuid-authoritative; this ADR does **not** change it); `registry/common-elements.md` §2.5 `Reference` (the resource-reference shape this ADR gives resolution semantics); `contracts/identifier-scheme.md` (handles + uuids); ADR-011 (validate-and-reserve — the execution-time gate this leans on); ADR-024 (post-placement enrichment fills provider-required inputs — many of which are resource references); `foundations/four-state-lifecycle.md` (Intent→Requested→Realized→Discovered); the four-state model this maps onto.

## Context

UDLM has **two distinct reference concepts**, and today's Platform.* work conflated them:

1. **Reference** (`common-elements.md` §2.5) — a typed cross-entity pointer to another **resource**: `{target_uuid, target_handle?, resource_type}`. A VM pointing at a `Platform.Namespace`, a `Network.VirtualNetwork`, a `Compute.Cluster`.
2. **Data reference** (ADR-012) — a pointer to an immutable **reference-data layer**: `{ref_uuid, ref_name?, reference_data_type}`. A field pointing at `os_image` v1, `vm_size` medium, `network_zone`.

These have **opposite requirements** and the difference is load-bearing:

- **Reference-data is versioned, immutable, and must reproduce exactly** — you reference *"os_image v1,"* and pinning the uuid *is the point* (deterministic replay, T3). ADR-012 correctly makes `ref_uuid` authoritative and rejects name-keyed references. **That decision stands, unchanged.**
- **A resource reference points at a *live* entity** with its own lifecycle — *"the namespace named `tenant-alpha-prod`,"* not a frozen version. You want the current one, resolved now.

The Platform.* types (and `provider-lifecycle.md`) authored their resource pointers (`cluster_ref`, `namespace_ref`, `storage_class_ref`) with the **ADR-012 data-reference shape and its uuid-authoritative, resolve-at-intent posture**. Applied to live resources that forces the author to supply a `ref_uuid` to an already-existing versioned record — which:

- **forbids claim-before-define** (you can't reference a namespace you'll create in the same batch),
- **forbids out-of-order authoring**, and
- **mismatches how the realization and Kubernetes actually work.** The DCM control-plane carries these as bare **name** strings today; the DCM enhancements catalog wires resources by **name** + CEL; Kubernetes references by **name** and sits *Pending* until the target exists. This string-vs-reference gap was flagged in review on `dcm-project/dcm` #69 and is unresolved.

The question this settles is not *whether* to use references but **which resolution process is situationally appropriate for the desired outcome**: a typed reference edge is always right, but *how* it resolves — a uuid pinned at authoring versus a handle resolved at reserve — must be chosen for what the reference points at (an immutable dataset versus a live resource) and the guarantee that outcome requires (reproducibility versus claim-before-define).

## Decision

**Resource references adopt AEP-124 resource association: authored by resource path/handle, the uuid resolved and recorded by the system at reserve. Reference-data (ADR-012) is untouched.**

### 1. Two kinds, cleanly separated
`Reference` (§2.5) is the **only** shape for a pointer to another **resource**; `data_reference` (ADR-012) is the **only** shape for a pointer to **reference-data**. A field picks by what it points at — a live entity vs an immutable governed dataset. They are never interchanged. (This ADR moves the Platform.* resource pointers off `data_reference` onto `Reference`; see Reconciliation.)

### 2. Author by handle; the system resolves and pins the uuid at reserve
A resource reference is written as `{target_handle, resource_type}` — a stable **resource path/handle**, not a uuid (AEP-124: reference by resource path; the `_id` suffix is reserved for "the ID component alone"). `target_uuid` is **resolution provenance**: populated by DCM when the reference resolves, frozen into the record for audit. **An author never types a uuid.** This is **AEP-124 resource association** — the standard the DCM realization already uses — generalizing the Kubernetes `ObjectReference` idiom. AEP-124's "embedded resource" variant (the field carries the referenced resource with only its path populated) is exactly this object-shaped `Reference`.

### 3. Two resolution modes; deferred is the default for live resources
- **`resolved`** — `target_uuid` already present and valid (the target exists now).
- **`deferred`** — resolved by `target_handle` at **reserve** (execution) time, and *tolerating a not-yet-existing target*: an unresolvable deferred reference holds the resource in **Requested** (≈ Kubernetes `Pending`) until it resolves, with a T6-style freshness finding if it stays stale. This is **claim-before-define** and it makes out-of-order authoring work.

Resolution and validation happen at the **reserve gate** (ADR-011) — the machinery already exists: the reserve → re-enrich → re-reserve convergence loop *is* "keep resolving until it converges." No new evaluator.

### 4. The four states carry it natively
`Intent` may carry deferred references by handle → `Requested` (placed; references pending resolution) → `Realized` (all resolved + built). A resource reference's `target_uuid` is guaranteed present only from `Realized` onward.

### 5. The uuid still matters — but only as the resolved record
Name-only (pure K8s) would lose three things UDLM exists to provide and a single cluster never has to: **deterministic tamper-evident replay** (T3 — a name resolves to "current" and drifts; the pinned resolved uuid replays identically), **version-pinned change-impact** (which version an edge resolved to), and **global identity across federation + sovereignty boundaries** (names are locally scoped and collide; a uuid is globally unique). So we keep the uuid — as **machine-resolved provenance**, not an authoring key.

### 6. Where deferred is allowed is Policy
Deferred resolution trades the resolve-at-intent guarantee for declarative flexibility. **Policy decides where deferred is disallowed** — a sovereignty- or audit-critical edge may require `resolved` at intent; a routine namespace may defer. Data carries the reference and its mode; DCM gates it.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)
- **Data (UDLM):** the `Reference` shape (`target_handle` authoring key, `resource_type`, `target_uuid` as resolved provenance) and the resolution-mode marker; the four-state guarantee about when `target_uuid` is present.
- **Policy (DCM):** resolves `target_handle` → `target_uuid` at reserve; runs the convergence loop for deferred references; gates where deferred is disallowed; records residency/resolving-authority provenance.
- **Provider:** validates the resolved reference at reserve (target exists and is usable); reports the realized target uuid back.

## Options considered
- **Keep uuid-authoritative, resolve-at-intent for resource references** (status quo) — rejected: too rigid for live resources; forbids claim-before-define and out-of-order authoring; mismatches the DCM realization and K8s.
- **Drop references for resources; use bare name strings** (pure K8s) — rejected: loses the typed graph edge, deterministic replay, version-pinned impact, and global identity — everything references buy. It also silently rebinds on name reuse (ADR-012 finding #1).
- **Name-authoritative with no uuid at all** — rejected: same loss of T3 replay, change-impact, and federation identity; the uuid is cheap to carry as resolved provenance.
- **Collapse Reference and data_reference into one shape** — rejected: they have opposite resolution requirements (live-current vs immutable-pinned); one shape would force one posture on both.
- **[chosen] Resource references handle-authored + uuid-resolved-at-reserve, two resolution modes (deferred default), Policy-gated; reference-data (ADR-012) unchanged.**

## Consequences
- **`common-elements.md` §2.5 + `common-elements.schema.json` `$defs/Reference`:** `required` becomes `[resource_type]` plus *at least one of* `{target_handle, target_uuid}`; `target_handle` documented as the authoring key; `target_uuid` documented as resolution provenance (system-populated, honesty-gated when present); an optional `resolution_mode: resolved|deferred` (default `deferred`). A dangling *resolved* uuid is still a hard fail; a *deferred* reference is not required to resolve until the resource leaves `Requested`.
- **Platform.* types** (`platform.namespace/storage-class/node-pool/resource-quota`, and any resource pointer on other types): `*_ref` fields move from the `data-reference.schema.json` shape to the `Reference` shape; `oneOf: [string-handle, Reference]` (short form = the handle). Claim-before-define enabled.
- **`provider-lifecycle.md`:** authoring/catalog examples reference by **handle**; the Phase-4 dispatch payload (post-reserve) legitimately shows resolved `target_uuid`s — that is the resolved end of the same reference.
- **`validate.py`:** resource-reference integrity is checked at the appropriate lifecycle state (deferred references exempt from resolve-now until `Requested`→`Realized`); reference-data integrity (`check_data_references`) is unchanged.
- **Compatibility:** converges with the DCM control-plane (name strings) and enhancements (name + CEL), and answers the open `dcm-project/dcm` #69 review gap — the reconciliation is "author by name, the substrate pins the uuid," not "pick strings or ids."
- **ADR-012 is untouched.** Reference-data stays uuid-authoritative and version-pinned; this ADR governs only resource→resource references.
