# DCM Data Model — Data Layers and the Assembly Process



**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Entity Types](01-entity-types.md) | [Four States](02-four-states.md) | [Resource Type Hierarchy](05-resource-type-hierarchy.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA**
>
> The Data abstraction — how Data is assembled from layers



---

## 1. Purpose

Data Layers are the mechanism by which DCM assembles a complete, contextually correct request payload from a set of composable, reusable data definitions. Rather than requiring consumers to specify every field of every resource they request, layers allow standards, organizational context, service-specific configuration, and consumer intent to be declared independently and merged into a unified payload at request time.

Layers are the answer to the question: **how does a single consumer request become a complete, policy-validated, provider-ready payload?**

The layering model enables:
- **Reuse** — a base configuration defined once is inherited by thousands of resources
- **Standardization** — organizational standards are encoded in layers, not in every individual request
- **Separation of concerns** — infrastructure teams own core and service layers; consumers own request layers; policy owners own policy layers
- **Scale** — 36 layer definitions can govern 40,000 VMs without duplication
- **Auditability** — every field in the merged payload knows which layer set it and why

---

## 1a. Layers vs Policies — The Clear Distinction

Layers and policies are the two foundational mechanisms of DCM's assembly process. They are complementary and distinct — understanding the difference is critical to using DCM correctly.

### Layers Are Data

A layer is a **declarative, immutable, versioned unit of data**. It carries static configuration values, organizational defaults, compliance metadata, and contextual information. A layer answers the question: **"what values should these fields have?"**

Layers are **passive** — they declare values but do not execute logic. They do not evaluate the payload, make branching decisions, or enforce rules. The assembly process merges them in priority order. Layers come first.

**What belongs in a layer:**
- Infrastructure defaults (DNS servers, NTP servers, MTU values)
- Organizational context (data center location, rack assignment, environment tier)
- Service-specific configuration defaults (VM sizing defaults, storage class preferences)
- Compliance metadata (data classification labels, retention tags, jurisdiction markers)
- Provider-specific configuration (provider default settings, tooling parameters)
- Business context (cost center defaults, environment labels, team tags)

### Policies Are Logic

A policy is an **executable rule** that evaluates the assembled payload and takes action. A policy answers the question: **"given this data, is it valid? what should change? should this proceed?"**

Policies **execute** — they run logic (OPA Rego, DCM native rules, external evaluation calls). They can read every layer-provided value, validate correctness, transform fields, inject derived values, and gate requests. Policies come after layers — they operate on the assembled result.

**What belongs in a policy:**
- Validation rules ("this field must be present and within these bounds")
- Compliance enforcement ("all resources must have a classification label")
- Derived value injection ("inject cost center from OIDC claims")
- Placement constraints ("must be in EU sovereignty zone")
- Approval gates ("resources above X size require manager approval")
- Security enforcement ("encryption must be enabled — if not, enable it or reject")

### The Flow Is Strictly Unidirectional

```
Steps 1-4: LAYERS assembled → merged payload produced
  │  Layers contribute field values
  │  Higher priority layers override lower priority
  │  Immutable fields locked at this stage
  │
  ▼
Steps 5-9: POLICIES execute → payload evaluated and acted upon
  │  Policies read assembled payload
  │  Transformation: modify/inject derived fields
  │  Validation: verify correctness
  │  GateKeeper: approve or reject
  │
  ▼
Provider-ready payload dispatched
```

Policies cannot set static configuration — that is a layer's job. A policy that finds itself repeatedly injecting the same static value into every request should be refactored: that value belongs in a layer.

Layers cannot enforce rules — that is a policy's job. A layer that contains conditional logic or rule evaluation is being misused — that logic belongs in a policy.

### The Decision Rule for Practitioners

> "Is this a **value** that should appear in the payload? → **Layer**  
> Is this a **rule** about whether the payload is correct? → **Policy**  
> Is this a **value derived by evaluating** the payload? → **Policy** (Transformation type)"

### The Analogy

- Layers are the **ingredients** — pre-measured, pre-arranged, versioned
- Policies are the **chef** — decides what to do with the ingredients, can add derived elements, makes judgment calls, can reject the dish entirely

Both are necessary. Neither replaces the other.

---

## 2. What is a Layer?

A Layer is a **declarative, immutable, versioned unit of data** that contributes some or all of its fields to a merged payload. Layers do not execute — they declare. The assembly process is what merges them.

Every layer:
- Has a **UUID** that uniquely identifies it
- Has a **version** following the universal Major.Minor.Revision scheme
- Is **immutable once published** — changes produce a new version
- Carries a **reference to its parent entity** (UUID and version)
- Has an **origination timestamp**
- Can be **deprecated** following the universal deprecation model
- Contributes **provenance metadata** for every field it sets — any field set by a layer records that layer's UUID as its source

Layers are stored in Git following GitOps practices. They are the configuration source of truth — not the assembled payload.

---

## 3a. Provenance Model Configuration

### 3a.1 The Three Provenance Models

Field-level provenance tracks which layer set each field, which policy modified it, and the full change history. DCM supports three configurable models — organizations choose based on their scale, compliance requirements, and operational preferences. The active Profile provides a recommended default via its activated Policy Group.

**Model A — Full Inline**
All provenance stored explicitly on every entity record. Every field carries its complete provenance inline: source layer, modifying policies, previous values, timestamps, actor chain.

| Aspect | Detail |
|--------|--------|
| Storage cost | Very high — scales with entities × fields × changes |
| Query simplicity | Highest — all provenance in one record, no traversal |
| Write performance | Lowest — every field change requires provenance write |
| Audit clarity | Highest — regulators see everything in one record |
| Tooling required | Minimal |
| Best for | Small deployments; FSI/sovereign (regulatory clarity); home lab |

**Model B — Deduplicated (Content-Addressed) ← RECOMMENDED**
Classical content-addressed deduplication applied to provenance. The layer chain is the deduplication key — every entity sharing the same configuration references the same chain rather than storing a copy. Only fields deviating from the chain store unique delta records.

```
Full provenance = layer chain content (deduplicated, shared) + entity deltas (unique per entity)
```

**Why lossless:** Layer chains are immutable. A reference to `layer-chain-abc123` always resolves to exactly the same data — no cache invalidation, no drift. This is what makes the deduplication lossless for audit. The reference always reconstructs the original.

**Storage reduction:** 95-99% for standardized deployments (many entities, few unique chains). 36 layer definitions serving 40,000 VMs produces 36 chain references, not 8 million field provenance entries.

| Aspect | Detail |
|--------|--------|
| Storage cost | Low — scales with unique configurations, not entity count |
| Query simplicity | Medium — chain traversal required for layer-set fields |
| Write performance | Highest — only deltas write; chain-matching fields are free |
| Audit clarity | Complete — full reconstruction always possible |
| Tooling required | Moderate — chain traversal tooling |
| Best for | Standard and prod deployments; large-scale environments |

**Analogous to:** Git content-addressed objects, Docker image layers, ZFS block deduplication — all content-addressed, deduplicated, lossless.

**Model C — Tiered Archive**
Hot/warm/cold storage tiers with decreasing detail. Recent provenance at full detail and fast access; older provenance compressed to change events; oldest compressed to hash anchors only (tamper-evidence without full reconstruction).

| Aspect | Detail |
|--------|--------|
| Storage cost | Medium — time-dependent, degrades gracefully |
| Query simplicity | Medium — cross-tier joins for long time ranges |
| Write performance | Medium |
| Audit clarity | Full detail in hot tier; change events in warm; anchors in cold |
| Tooling required | Moderate — tier promotion jobs, consistency checks |
| Best for | Large deployments with long retention requirements |

**Models B and C are orthogonal** — combine them for maximum efficiency: deduplicate at the entity level (Model B) AND tier the storage of chains and deltas (Model C). This is the highest-efficiency option for very large-scale deployments with long retention requirements.

### 3a.2 Configurable Provenance Model

The provenance model is declared in the DCM deployment configuration and activated via a Policy Group:

```yaml
provenance_config:
  model: <full_inline|layer_chain_ref|tiered|layer_chain_ref_tiered>

  # Model A — Full Inline
  full_inline:
    include_previous_values: true
    include_actor_chain: true
    include_policy_rationale: true

  # Model B — Deduplicated (Content-Addressed)
  layer_chain_ref:
    store_layer_derivable: false      # do not store fields matching chain default
    delta_detail_level: <full|summary>
    history_document_retention: P7Y
    chain_store_retention: P7Y       # chains retained while any entity references them

  # Model C — Tiered Archive
  tiered:
    hot_tier_duration: P30D          # full detail, fast access
    warm_tier_duration: P365D        # change events only
    cold_tier_duration: P10Y         # hash anchors only
    warm_tier_detail: <change_events_with_values|change_events_only>

  # Model B + C — Deduplicated + Tiered (maximum efficiency)
  layer_chain_ref_tiered:
    chain_store_hot: P365D           # chains fast for 1 year
    chain_store_warm: P7Y            # chains slower for 7 years
    delta_store_hot: P90D            # deltas fast for 90 days
    delta_store_warm: P7Y            # deltas slower for 7 years
```

### 3a.3 Profile-Appropriate Provenance Policy Groups

DCM ships four provenance Policy Groups. The active Profile activates the appropriate group by default. Organizations override by swapping the active group.

| Group Handle | Model | Profile Default | Concern Type |
|-------------|-------|----------------|-------------|
| `system/group/provenance-full-inline` | A — Full Inline | minimal, dev, fsi, sovereign | implementation_posture |
| `system/group/provenance-deduplicated` | B — Deduplicated | standard, prod | implementation_posture |
| `system/group/provenance-tiered-archive` | C — Tiered | (available — not default) | implementation_posture |
| `system/group/provenance-deduplicated-tiered` | B+C — Combined | (available for large-scale) | implementation_posture |

**To change provenance model:**
```yaml
# Override profile default — swap the active provenance group
tenant_config:
  policy_group_overrides:
    replace:
      - from: system/group/provenance-full-inline
        to: system/group/provenance-deduplicated
        reason: "Deploying at scale — switching to deduplicated model"
```

### 3a.4 The Audit Completeness Guarantee

Regardless of provenance model, full provenance must always be reconstructable:

```
OPS-002  Regardless of provenance model, full provenance must always be
         reconstructable for any entity from the combination of: entity
         record, layer chain store, and Audit Store. The provenance model
         governs where data is stored and how it is accessed — not whether
         it is available.
```

For Model B: chain reference + entity deltas → full provenance (lossless, immutable source)
For Model C: hot tier (full) OR warm tier (events) + cold tier (anchors prove integrity)
For Model A: entity record alone is sufficient

### 3a.5 System Policies

| Policy | Rule |
|--------|------|
| `OPS-001` | Field-level provenance model is configurable: full_inline, layer_chain_ref (deduplicated), tiered, or layer_chain_ref_tiered. Profile activates the appropriate Policy Group as default. Organizations override by replacing the active provenance group. Model B (layer_chain_ref) is the recommended default for standard+ profiles. |
| `OPS-002` | Regardless of provenance model, full provenance must always be reconstructable from the combination of entity record, layer chain store, and Audit Store. The provenance model governs storage location and access pattern — not data availability. |

---


### 2a. Layer Contributors

Every layer type has a declared contributor type. The contributor determines what review is required before the layer becomes active in assembly. See [Federated Contribution Model](28-federated-contribution-model.md) Section 3 for the full contributor permission table.

| Layer Type | Contributor | Domain | Review |
|-----------|-------------|--------|--------|
| Base Layer | Platform Admin | system | auto |
| Core Layer | Platform Admin | platform | auto |
| Intermediate / Customization Layer | Platform Admin, Consumer/Tenant | platform, tenant | per profile |
| Service Layer | Platform Admin, Service Provider | provider | reviewed (standard+) |
| Request Layer | Consumer/Tenant | tenant | auto (applied directly to request) |
| Policy Layer | All contributor types | per contributor role | per profile + contributor type |

The Request Layer is the only layer type that does not require a PR review — it is a consumer's direct field declarations on a specific request. All other layers flow through the GitOps PR model.


## 3. Layer Types

DCM defines six layer types. Each has a distinct purpose, scope, ownership model, and position in the assembly precedence chain.

### 3.1 Base Layer

**Purpose:** The foundation entity for a resource. Defines the minimum required fields and their default values for a given resource context. Everything starts with a Base Layer.

**Scope:** Can be type-agnostic (a universal base) or type-scoped (a base specific to a Resource Type). A Base Layer that is type-scoped must declare its Resource Type.

**Ownership:** DCM platform or platform implementor.

**Characteristics:**
- Every layer chain must begin with a Base Layer
- Base Layers contain only universal fields — no provider-specific data
- A Base Layer for a typed resource must conform to the Resource Type Specification's universal field requirements
- Multiple Base Layers can exist for the same context — the applicable one is selected based on the request context

**Examples:**
- CIS Benchmark base configuration
- Baseline OS configuration
- DMZ network base configuration

---

### 3.2 Core Layers

**Purpose:** Provide data that is applicable across any resource type. Core Layers carry organizational, infrastructure, and contextual data that is not specific to any one service.

**Scope:** Type-agnostic by default. Core Layers apply to all resource types unless explicitly scoped. This is the primary distinction from Service Layers.

**Ownership:** DCM platform, infrastructure teams, or platform implementors.

**Characteristics:**
- Applied to every request regardless of resource type
- Cannot contain service-specific or provider-specific data
- Carry location, organizational, and infrastructure context
- Stored in the Core Layer Store
- Cached in the Service Layer Cache at deployment time

**Examples:**
- Data Center layer (DC1, DC2)
- Zone layer (Zone 1, Zone 2)
- Rack layer
- Geographic region layer
- Environment layer (production, staging, development)

> **Location Topology:** Location layers are one application of the Reference Data
> Layer pattern (Section 3.7). The standard schema for each location level —
> Country, Region, Zone, Site, Data Center, Hall, Cage, and Rack — is specified
> in [Location Topology Layer Model](48-location-topology-layers.md), including
> field definitions, priority bands, authority model, and hierarchy assembly.

---

### 3.3 Intermediate / Customization Layers

**Purpose:** Provide organizational or contextual overrides and customizations that sit between the base standards and the service-specific configuration. These layers encode the organizational hierarchy and deployment context.

**Scope:** Can be type-agnostic or type-scoped. Scope is declared per layer.

**Ownership:** Organizational teams, domain owners, platform implementors.

**Characteristics:**
- Stack between Core Layers and Service Layers in the precedence chain
- Encode organizational structure (business unit, enclave, logical unit)
- Allow organizational customization without modifying base standards
- The Git repo hierarchy typically mirrors the intermediate layer hierarchy

**Examples:**
- Ship layer (in Navy context: specific vessel configuration)
- Enclave layer (isolated network segment configuration)
- Business unit layer
- DMZ customization layer
- Production web tier layer

---

### 3.4 Service Layers

**Purpose:** Provide service-specific data required to build a complete request payload for a specific Resource Type. Service Layers are the bridge between general organizational context and provider-ready configuration.

**Scope:** **Must be type-scoped.** A Service Layer without a declared Resource Type scope is invalid. The scope inheritance behavior is configurable per Service Layer declaration.

**Type Scope Declaration:**
```yaml
type_scope:
  resource_type_uuid: <uuid of Resource Type>
  resource_type_fully_qualified_name: <Category.ResourceType>
  scope_inheritance: <exact|descendants>
  # exact: applies only to the declared Resource Type
  # descendants: applies to the declared Resource Type and all child types via inheritance
```

**Ownership:** Service Providers or service domain teams. Stored in Service Layer SCM (source control management). Registered with DCM as part of Service Provider registration.

**Characteristics:**
- Only applied when the request resource type matches the layer's declared type scope
- Carry service-specific configuration, defaults, and constraints
- Must not contain provider-specific data unless marked as portability-breaking
- Cached in the Service Layer Cache at Service Provider registration time

**Examples:**
- VM sizing layer (small, medium, large configurations for `Compute.VirtualMachine`)
- Web server configuration layer for `Compute.VirtualMachine`
- Network port configuration layer for `Network.Port`
- CL Web Service Data Layer for `Compute.VirtualMachine` (exact scope)
- General compute placement layer for `Compute.VirtualMachine` and descendants

---

### 3.5 Request Layer

**Purpose:** Carries the consumer's declared intent. The Request Layer is what the consumer provides — the fields they explicitly specify for their resource request.

**Scope:** Scoped to the Resource Type the consumer is requesting.

**Ownership:** Consumer (via Web UI or Consumer API).

**Characteristics:**
- Created at the time the consumer submits a request
- Contains only what the consumer explicitly declares — it does not need to be complete
- The gap between what the consumer declares and what the provider needs is filled by the lower layers in the chain
- Has higher precedence than all data layers below it — consumer-declared values override layer defaults
- Is the direct source of the **Intent State** — the Request Layer as submitted by the consumer is stored in the Intent Store before any processing occurs
- After assembly and policy processing, the enriched payload becomes the **Requested State**

**Examples:**
- Consumer requests a VM with `cpu_count: 8`, `ram_gb: 32`, `os: RHEL9`, `environment: production`
- Consumer requests a firewall rule with source/target network and port

---

### 3.6 Policy Layers

**Purpose:** Policy Layers are not data layers in the traditional sense — they do not add fields to the merge chain. Instead, they operate on the assembled payload after the data layers have been merged. They are the governance layer of the assembly process.

**Scope:** Scoped by policy type and domain. Core Policies apply to all requests. Service Policies apply to specific Resource Types. Organizational and domain policies apply to specific organizational scopes.

**Ownership:** Policy creators, security teams, compliance teams, organizational domain owners.

**Policy Layer Types and Their Behavior:**

| Policy Type | Behavior | Precedence Effect |
|-------------|----------|-------------------|
| **Validation** | Checks data against rules. Does not modify data. Returns pass/fail. If fail, request is rejected. | No precedence — pass/fail only |
| **Transformation** | Enriches or modifies data in the payload. Adds missing fields, applies standards, fills gaps. | Adds to or modifies the assembled payload — recorded in provenance |
| **GateKeeper** | Highest authority. Can override any field regardless of what was declared in lower layers or the Request Layer. Can halt execution entirely. Used for sovereignty constraints, security mandates, and hard compliance rules. | Overrides everything — including consumer input |

**Characteristics:**
- Policies operate only on the policy definition, core data, and the data in the request payload
- Policy outcomes are deterministic — same input always produces same output for a given policy version
- All policy modifications are recorded in field-level provenance with policy UUID, operation type, and reason
- Policies are versioned using the universal versioning scheme
- Policies are maintained via GitOps practices

---

### 3.7 Reference Data Layers

**All of DCM's data — including Resource Type Specifications — is built on the same
layer model.** A Resource Type Specification is itself a data layer artifact: versioned,
owned by a declared Resource Type Authority, stored in GitOps, subject to the standard
lifecycle, and subject to the same domain-based access control as all other layers. The
only distinction is that Resource Type Specifications live in the Resource Type Registry
(which is itself a specialized layer store) rather than the Core Layer Store.

This unified model means:
- The same governance tooling manages resource type definitions, reference data, and
  service configuration
- The same lifecycle (developing → proposed → active → deprecated → retired) applies
  to all three
- The same ownership declarations, the same GitOps workflow, the same authority tiers
- Provider extension layers (domain: `provider`) extend resource types for a specific
  catalog item without modifying the Resource Type Specification itself — they are
  injected during payload assembly only when that catalog item is selected

**Purpose:** Provide governed, versioned sets of allowed values for use as field
constraints in Resource Type Specifications and Provider Catalog Items. Reference Data
Layers are the source of truth for any enumerated choice a consumer makes when
requesting a resource.

**Scope:** Declared per layer type. A Reference Data Layer of type `os_image` is only
valid as a constraint source for fields that declare `layer_type: os_image`. Reference
Data Layers are not injected into the assembled request payload in the same way as other
layers — they are resolved at catalog render time to produce the `allowed_values` list
for a field constraint.

**Ownership:** The team or authority responsible for governing that category of data.

| Layer Type | Owning Authority | What it governs |
|------------|-----------------|-----------------|
| `location.*` | Data Center Operations | Where resources can be placed |
| `os_image` | Platform Security / OS Team | Approved OS images and versions |
| `vm_size` | Platform Team | Approved VM size profiles |
| `network_zone` | Network Operations | Available network zones and their properties |
| `environment` | Platform Governance | Deployment environments and their policy sets |
| `storage_class` | Storage Operations | Available storage tiers |
| `gpu_profile` | Platform Team | Approved GPU configurations |

**Characteristics:**
- Same lifecycle as all other layers: `developing → proposed → active → deprecated → retired`
- Same governance: GitOps workflow, owned by declared authority, approved by designated tier
- Same versioning: `Major.Minor.Revision` — breaking changes require a major bump
- Same security: domain-based access control, same policy enforcement
- **Not merged into the request payload directly** — they are resolved at catalog render time
  to produce the field constraint `allowed_values` list
- **Their structured data IS injected** when a consumer selects a value: selecting a
  location layer injects all location context; selecting an OS image layer injects
  image UUID, SHA, version, and EOL date into the payload

**Adding a new allowed value** for any layer-referenced field means adding a new
Reference Data Layer instance of the appropriate type. No changes to the Resource Type
Specification, the catalog item, or any policy. The new value becomes available to
all catalog items that reference that layer type on the next sync cycle.

**Retiring an allowed value** means retiring the Reference Data Layer instance.
Existing resources that used that value are unaffected. Future requests cannot
select it.

**Example — OS Image layer:**

```yaml
layer:
  artifact_metadata:
    uuid: <uuid>
    handle: "platform/os-images/rhel-9-4-approved"
    version: "1.0.0"
    status: active
    owned_by:
      display_name: "Platform Security Team"
      group_handle: "groups/platform-security"
    created_via: pr

  layer_type: reference_data
  reference_data_type: os_image
  scope: type_agnostic

  priority:
    value: "150.01.0"
    label: "platform.reference.os-image.rhel-9-4"
    category: platform_reference

  data:
    image_name: "RHEL 9.4"
    image_uuid: "img-rhel-9-4-20260315"
    image_sha256: "a1b2c3d4..."
    os_family: rhel
    major_version: 9
    minor_version: 4
    release_date: "2026-03-15"
    eol_date: "2032-05-31"
    approved_for_classifications: [public, internal, confidential, restricted]
    cis_benchmark_version: "CIS RHEL 9 Benchmark v1.0"
    fips_compliant: true

  concern_tags: [os-image, rhel, approved, fips-compliant]
```

**Example — VM Size layer:**

```yaml
layer:
  artifact_metadata:
    uuid: <uuid>
    handle: "platform/vm-sizes/medium-general-purpose"
    version: "2.1.0"
    status: active
    owned_by:
      display_name: "Platform Team"
      group_handle: "groups/platform-team"
    created_via: pr

  layer_type: reference_data
  reference_data_type: vm_size
  scope: type_agnostic   # applies across providers for Compute.VirtualMachine

  data:
    size_name: "Medium — General Purpose"
    size_code: "gp-medium"
    display_name: "Medium (8 CPU / 32 GB)"
    cpu_count: 8
    memory_gb: 32
    storage_gb: 80
    network_bandwidth_gbps: 10
    approved_for_workloads: [web, application, database, batch]
    cost_tier: standard

  concern_tags: [vm-size, general-purpose, approved]
```

---


## 4. Layer Identity — Domain, Handle, and Priority

Every layer has a formal identity model with three components that together make it uniquely identifiable, locatable, and orderable within DCM.

### 4.1 Layer Domain

The **Layer Domain** mirrors the Policy domain model exactly. It declares ownership, storage location, and authorization scope. The same domain hierarchy, the same authority model, the same override precedence.

| Domain | Meaning | Authorization | Can Override |
|--------|---------|--------------|-------------|
| `system` | DCM built-in layers — ship with DCM | DCM maintainers only | Nothing above system |
| `platform` | Platform team layers — apply across all Tenants | Platform team | tenant, service, provider |
| `tenant` | Tenant-specific layers — scoped to one Tenant | Tenant Admin | service, provider within Tenant |
| `service` | Service Provider contributed layers | Service Provider owner | provider |
| `provider` | Provider Catalog Item layers | Provider owner | Nothing above provider |
| `request` | Consumer-declared values in the request itself | Consumer | Nothing above request — lowest authority |

A lower-domain layer cannot override a higher-domain layer.

**Provider extension layers** (`domain: provider`) are contributed by Service Providers
as part of their catalog item registration. They add provider-specific fields to the
assembled payload for their offering only. They cannot override platform or tenant layers.
They carry the same portability implications as inline `provider_specific_extensions` in
the catalog item declaration — any request using them is non-portable and must be
explicitly marked. See [Resource Type Hierarchy](05-resource-type-hierarchy.md) Section 6.2
for the catalog item `provider_extension_layer_handles` declaration. A `tenant` layer cannot override a `platform` layer. This is enforced at ingestion — the conflict detection pipeline checks domain authority before allowing a merge.

**Domain mirrors policy authority:** Just as system-domain policies have highest authority in the Policy Engine, system-domain layers have highest authority in the assembly process. The same mental model applies to both.

### 4.2 Layer Groups — DCMGroup with group_class: layer_grouping

Just as Policy Groups organize policies into cohesive concern-based collections, **Layer Groups** organize layers. A Layer Group is a `DCMGroup` with `group_class: layer_grouping` — a versioned, audited, GitOps-managed collection of related layers.

Layer Groups enable:
- **Discovery** — "show me all layers related to PCI compliance"
- **Composition** — include a group in a profile rather than listing individual layers
- **Governance** — activate or deactivate a concern's worth of layers in one operation

```yaml
# A Layer Group — DCMGroup with group_class: layer_grouping
dcm_group:
  artifact_metadata:
    uuid: <uuid>
    handle: "platform/layer-groups/pci-network-standards"
    version: "1.0.0"
    status: active
  group_class: layer_grouping
  concern_tags: [pci-dss, networking, standards]
  members:
    - member_uuid: <layer-uuid>
      member_type: layer
      member_role: network_segmentation_defaults
    - member_uuid: <layer-uuid>
      member_type: layer
      member_role: firewall_baseline
    - member_uuid: <layer-uuid>
      member_type: layer
      member_role: tls_minimum_version
```

### 4.3 The Full Layer Structure

Every layer carries: identity, domain and authority, compatibility metadata, per-field override metadata, and usage context. This mirrors the richness of a Policy registration.

```yaml
layer:
  artifact_metadata:
    uuid: <uuid>
    handle: "platform/core/default-dns-config"
    version: "1.2.0"
    status: active
    owned_by:
      display_name: "Platform Infrastructure Team"
      notification_endpoint: <endpoint>
    created_via: pr   # pr | api | migration | system

  # DOMAIN AND AUTHORITY
  domain: platform
  priority:
    value: "500.20.0"
    label: "platform.networking.dns"
    category: platform
    rationale: "Platform DNS infrastructure — primary and secondary resolvers"

  # CONCERN TAGS — for discoverability and grouping
  concern_tags: [networking, dns, platform-defaults]

  # COMPATIBILITY METADATA — what this layer applies to
  compatibility:
    resource_types: [Compute.VirtualMachine, Compute.Container]
    resource_type_versions: "^1.0.0"
    provider_types: []              # empty = all providers
    profile_constraints: []         # empty = all profiles; or: [standard, prod, fsi]
    domains_applicable: [platform, tenant, service, provider]  # which domains may use this

  # CONDITIONAL INCLUSION (Q23) — activation condition
  activation_condition:
    # Layer only included if this condition evaluates true during Step 2 (Layer Resolution)
    field: tenant.tags
    operator: not_contains          # equals|not_equals|exists|not_exists|contains|in|not_in
    value: custom-dns
    # Compound conditions:
    # conditions:
    #   operator: and   # and | or
    #   rules:
    #     - field: request.gpu_requested
    #       operator: equals
    #       value: true
    #     - field: ingress.actor.roles
    #       operator: contains
    #       value: developer

  # FIELDS — with per-field override metadata
  fields:
    dns_servers:
      value: [10.0.0.53, 10.0.0.54]
      metadata:
        override: allow             # allow | constrained | immutable
        basis_for_value: "Platform DNS infrastructure — primary and secondary"
        provenance_note: "Set by platform infrastructure team per INFRA-2024-089"
    dns_search_domain:
      value: corp.example.com
      metadata:
        override: immutable         # lower layers cannot override this field
        locked_by_policy_uuid: <uuid>
        basis_for_value: "Corporate domain — cannot be customized per SECURITY-2024-034"

  # USAGE CONTEXT — human documentation embedded in the artifact
  usage:
    description: "Default DNS configuration for all platform VMs and containers"
    applies_when: "All requests unless consumer declares layer exclusion or tenant has custom-dns tag"
    excludes_when: "Tenant has custom_dns tag; consumer declares explicit layer exclusion"
    supersedes: []                  # handles of layers this replaces
    conflicts_with: []              # handles of layers this conflicts with — detected at ingestion

  # SOURCE OF TRUTH
  scm_location:
    repository: https://git.corp.example.com/dcm-layers
    path: platform/core/default-dns-config/v1.2.0.yaml
    commit: <sha>
```

### 4.4 Layer Handle

The **Layer Handle** is the human-readable, stable identifier for a layer within DCM.

**Format:** `{domain}/{concern_or_type}/{name}`

**Examples:**
```
platform/core/cis-benchmark-linux
platform/core/security-cpu-limits
tenant/service/payments-vm-standards
system/base/universal-defaults
service/service/kubevirt-vm-defaults
provider/service/cloudnativepg-database-config
```

**Git path from handle:**
```
{layer_store_root}/{domain}/{concern_or_type}/{name}/v{Major}.{Minor}.{Revision}.yaml

# Example:
dcm-layers/platform/core/security-cpu-limits/v1.2.0.yaml
dcm-layers/tenant/{tenant-uuid}/service/payments-vm-standards/v1.0.0.yaml
```

### 4.5 Priority Schema

The **Priority Schema** is the deterministic ordering mechanism for resolving conflicts between layers of the same type and scope.

**Format:** `{integer}.{integer}.{integer}...` — unlimited depth

**Comparison:** Left-to-right, segment by segment. **Higher numeric value = higher priority** (higher value = higher priority). No ceiling — you can always go higher.

```
900.10    beats    800.10    (900 > 800 at segment 1)
900.20    beats    900.10    (20 > 10 at segment 2)
900.10.5  beats    900.10    (longer path with matching prefix)
900.10.10 beats    900.10.5  (10 > 5 at segment 3)
```

**Reference Priority Taxonomy (advisory — not enforced by DCM):**

| Suggested Range | Category | Rationale |
|-----------------|----------|-----------|
| `900.*` | Compliance | Regulatory mandates — highest authority |
| `800.*` | Security | Security standards |
| `700.*` | Sovereignty | Data residency constraints |
| `600.*` | Operations | SRE and operational standards |
| `500.*` | Platform | Platform-level defaults |
| `400.*` | Service | Service-specific configuration |
| `300.*` | Organization | Organizational defaults |
| `200.*` | Site | Location-specific overrides |
| `100.*` | Custom | Implementor-defined — lowest standard category |

Higher number = higher priority. Organizations adopt, adapt, or ignore this taxonomy — DCM resolves conflicts purely by numeric comparison.

---

## 4b. Artifact Metadata Standard

Every DCM artifact — layers, policies, resource types, catalog items, provider registrations, entity definitions, and all other defined or stored objects — carries a standard **Artifact Metadata** block. This is a structural requirement, not optional.

The artifact metadata block answers: **who created this, when, who owns it, what changed, and how do we contact them?**

### 4b.1 Universal Artifact Metadata Structure

```yaml
artifact_metadata:

  # Identity
  uuid: <uuid — assigned by DCM at creation, immutable>
  handle: <domain/type/name — human-readable stable identifier>

  # Versioning
  version: <Major.Minor.Revision>
  status: <developing|proposed|active|deprecated|retired>

  # Status detail — populated per status
  status_detail:
    # When status: proposed
    proposed_at: <ISO 8601>
    proposed_by:
      uuid: <actor UUID — optional>
      display_name: <required>
      email: <optional>
    shadow_execution:
      enabled: <true|false — only meaningful for policy artifacts>
      started_at: <ISO 8601>
      evaluation_count: <integer — requests shadowed so far>
      validation_dashboard_url: <URL to shadow output review>

    # When status: deprecated
    deprecated_at: <ISO 8601>
    deprecated_by:
      uuid: <actor UUID>
      display_name: <required>
    replacement_uuid: <UUID of replacement artifact>
    replacement_handle: <handle of replacement artifact>
    deprecation_reason: <human-readable>
    migration_guidance: <what users should do>
    sunset_date: <ISO 8601 — when it becomes retired>

    # When status: retired
    retired_at: <ISO 8601>
    retired_by:
      uuid: <actor UUID>
      display_name: <required>

  # Origination
  created_by:
    uuid: <actor UUID — optional when no Identity Provider registered>
    display_name: <required — human-readable name>
    email: <optional — direct contact fallback>
    notification_endpoint: <optional — automated notification target>
  created_at: <ISO 8601>
  created_via: <pr|api|migration|system>
  # pr:        submitted via GitOps PR workflow — full review history available
  # api:       submitted via direct API
  # migration: imported from external system — provenance depth may be limited
  # system:    created by DCM itself (entity stubs, system artifacts)

  # Ownership — may differ from creator
  owned_by:
    uuid: <actor or team UUID — optional>
    display_name: <required — team or individual name>
    email: <optional>
    notification_endpoint: <optional — receives conflict and deprecation alerts>
  # Note: created_by is the audit record (who physically submitted it)
  # owned_by is the accountability record (who is responsible and gets notified)

  # Modification history — append-only
  modifications:
    - sequence: 1
      modified_by:
        uuid: <actor UUID — optional>
        display_name: <required>
        email: <optional>
      modified_at: <ISO 8601>
      modification_type: <create|update|deprecate|retire|restore|status_change>
      version_before: <Major.Minor.Revision>
      version_after: <Major.Minor.Revision>
      change_summary: <human-readable — what changed>
      pr_reference: <Git PR URL — if via PR workflow>
      reason: <why this change was made>
```

### 4b.2 The Five Artifact Statuses

| Status | Meaning | Executes? | Output Applied? | Output Captured? | Merges to Active? |
|--------|---------|-----------|----------------|-----------------|------------------|
| `developing` | In active development. Development mode / dev pipeline only. | Dev mode only | No | Dev logs only | No — must transition to proposed first |
| `proposed` | Development complete. Submitted for validation. Shadow mode for policies. | Yes (shadow) | No | Yes — validation report | Yes — after review approval |
| `active` | Live and governing. Applied to all relevant requests. | Yes | Yes | Yes — audit/provenance | N/A |
| `deprecated` | Being phased out. Replacement available. Works but warns. | Yes | Yes | Yes — with deprecation warning | N/A |
| `retired` | End of life. Cannot be used. | No | No | No | No |

**Status transition rules:**
```
developing → proposed  (author submits for review)
developing → retired   (author abandons without proposing)
proposed   → active    (reviewers approve — via PR merge or API approval)
proposed   → developing (returned for rework)
active     → deprecated (replacement available — sunset date declared)
deprecated → retired   (sunset date reached or manual retirement)
retired    → (terminal — no transitions out)
```

### 4b.3 Proposed Status — Shadow Execution for Policies

When a policy artifact is in `proposed` status, it runs in **shadow mode** against real request traffic:

- Executes alongside active policies on every relevant request
- Output is captured in a `proposed_evaluation_record` — what it would have done
- Output is **never applied** to the actual request
- Shadow output feeds the Validation Dashboard for reviewer analysis
- Policy authors can see aggregate impact before activation

```yaml
# Shadow output record — captured per real request evaluated
proposed_evaluation_record:
  policy_uuid: <uuid>
  policy_version: <version>
  request_uuid: <real request being shadowed>
  tenant_uuid: <tenant>
  evaluated_at: <ISO 8601>
  would_have_applied: <true|false>
  shadow_output:
    would_have_rejected: <true|false>
    rejection_reason: <if would_have_rejected>
    would_have_patched:
      - field: <field path>
        current_value: <value in real payload>
        would_have_set: <value policy would have applied>
        reason: <policy reason>
    would_have_locked:
      - field: <field path>
        lock_type: <constrained|immutable>
        reason: <policy reason>
    would_have_selected_provider: <provider UUID — if policy sets provider constraints>
  impact_assessment:
    category: <none|low|medium|high|critical>
    # none:     policy would not have applied to this request
    # low:      minor enrichment only
    # medium:   significant field modifications
    # high:     would have rejected or locked critical fields
    # critical: would have rejected or overridden consumer intent
```

### 4b.4 Contact Info — Two Modes

Contact information supports both IdP-backed and standalone deployments:

**Mode 1 — Identity Provider backed:**
The `uuid` field contains the DCM external entity reference UUID linking to an Identity.Person or Identity.Team in a registered Information Provider. The `display_name` is cached non-authoritatively for UI display. DCM can resolve the full identity record via the Information Provider on demand.

**Mode 2 — Standalone (no Identity Provider):**
The `uuid` field is absent. `display_name`, `email`, and `notification_endpoint` are the primary identity fields. DCM accepts and records these directly without external verification. This mode supports bootstrapping, air-gapped deployments, and organizations that have not yet registered an Identity Information Provider.

Both modes are fully supported. An organization can start in standalone mode and migrate to IdP-backed mode by adding `uuid` fields to existing artifact metadata — no other changes required.

### 4b.5 Notifications from Artifact Metadata

The `owned_by.notification_endpoint` is the target for all proactive DCM notifications about an artifact:

| Event | Who Is Notified |
|-------|----------------|
| Layer conflict detected at ingestion | Owner of new layer AND owner of conflicting existing layer |
| Layer deprecated | Owners of all artifacts that reference the deprecated layer |
| Provider deregistered | Owners of all catalog items backed by that provider |
| Policy violation | Owner of the entity that violated the policy |
| Drift detected | Owner of the entity that drifted |
| Proposed policy shadow shows high/critical impact | Policy owner and designated reviewers |
| Artifact approaching sunset date | Artifact owner |

---

## 4c. Conflict Detection at Ingestion

Conflict detection runs at layer ingestion time — not at request assembly time. This ensures all layers in DCM are conflict-free before they are ever used.

### 4c.1 Ingestion CI Pipeline

When a layer is committed to the Layer Store (Git branch created or updated):

```
Layer committed to Git branch
  │
  ▼
CI Pipeline fires automatically
  │
  ├── 1. Schema validation
  │      Is the layer well-formed per the layer schema?
  │      Does it carry required artifact metadata?
  │      Is the version correctly incremented?
  │
  ├── 2. Handle validation
  │      Is the handle unique in DCM?
  │      Does the handle match the Git path?
  │      Does the domain match the submitting actor's authorization?
  │
  ├── 3. Scope validation
  │      If type-scoped: do declared resource types exist in the registry?
  │      Is the layer type consistent with the domain?
  │
  ├── 4. Priority validation
  │      Is the priority value in valid dotted-notation format?
  │      Does the priority category match the domain advisory range?
  │      (Warning only if category/domain mismatch — not a block)
  │
  ├── 5. Conflict detection
  │      For each field in this layer:
  │        Find all active layers of the same type and overlapping scope
  │        Check if any declare the same field
  │        If conflict found:
  │          → Does the new layer declare a higher priority? → Allowed, documented
  │          → Does the existing layer declare a higher priority? → Allowed, documented
  │          → Neither declares priority? → CONFLICT ERROR — PR blocked
  │          → Both declare equal priority? → CONFLICT ERROR — PR blocked
  │          → Domain authority violation? → CONFLICT ERROR — PR blocked
  │
  │      Conflict notification:
  │        Posted as PR comment with: conflicting layer UUID, handle, owner
  │        Both layer owners notified via notification_endpoint
  │
  ├── 6. Deprecation reference validation
  │      If status: deprecated — does replacement UUID exist?
  │
  └── 7. Result
         All checks pass → PR approved for merge
         Any check fails → PR blocked, detailed error comment posted
```

### 4c.2 Conflict Resolution Rules

| Situation | Resolution | Action |
|-----------|-----------|--------|
| New layer and existing layer conflict, no priority on either | CONFLICT ERROR | PR blocked. Both owners notified. One must declare priority or remove the conflicting field. |
| New layer has higher priority (higher value) than existing | Allowed — new layer wins | Documented in provenance. Warning posted if domain authority is unusual. |
| Existing layer has higher priority | Allowed — existing layer wins | New layer is a lower-priority alternative. Documented. |
| Both layers have equal priority | CONFLICT ERROR | PR blocked. Priority must be differentiated. |
| New layer from lower domain overrides higher domain | CONFLICT ERROR | Domain authority violation. Platform cannot be overridden by service layer. |
| Priority category suggests domain mismatch | WARNING | PR comment posted, not blocked. Merge allowed but reviewers are notified. |

### 4c.3 Pre-Validation of All Layers

Because conflict detection runs at ingestion, all layers resident in DCM are pre-validated:

- No two active layers of the same type and scope conflict without explicit priority resolution
- The assembly process never encounters an ambiguous merge — all conflicts are resolved at definition time
- If a conflict is discovered after the fact (e.g., a new layer is activated that conflicts with an existing one that was already active when the new layer was ingested), the newer layer's ingestion pipeline should have caught this. A background validation job runs periodically to detect any edge cases.

---

## 4d. Complete Layer Definition Structure

Combining all elements — identity, artifact metadata, scope, priority, and fields:

```yaml
# Complete layer definition
layer:
  # === ARTIFACT METADATA (universal — required on all artifacts) ===
  artifact_metadata:
    uuid: "layer-uuid-001"
    handle: "platform/core/security-cpu-limits"
    version: "1.2.0"
    status: active
    created_by:
      uuid: "actor-uuid-001"       # Optional — present if IdP registered
      display_name: "Jane Smith"
      email: "jane.smith@example.com"
      notification_endpoint: "https://notify.example.com/webhooks/jane"
    created_at: "2026-01-15T10:30:00Z"
    created_via: pr
    owned_by:
      uuid: "team-uuid-security"   # Optional — present if IdP registered
      display_name: "Platform Security Team"
      email: "platform-security@example.com"
      notification_endpoint: "https://notify.example.com/webhooks/platform-security"
    modifications:
      - sequence: 1
        modified_by:
          display_name: "Jane Smith"
          email: "jane.smith@example.com"
        modified_at: "2026-01-15T10:30:00Z"
        modification_type: create
        version_before: null
        version_after: "1.0.0"
        change_summary: "Initial creation — CPU limits per CISO mandate SEC-2024-047"
        pr_reference: "https://github.com/org/dcm-layers/pull/42"
        reason: "CISO mandate SEC-2024-047 requires CPU limits on all containers"
      - sequence: 2
        modified_by:
          display_name: "Bob Jones"
          email: "bob.jones@example.com"
        modified_at: "2026-02-20T14:00:00Z"
        modification_type: update
        version_before: "1.0.0"
        version_after: "1.2.0"
        change_summary: "Increased CPU limit from 4 to 8 per updated mandate"
        pr_reference: "https://github.com/org/dcm-layers/pull/67"
        reason: "Updated CISO mandate SEC-2024-047-rev2 allows 8 CPU"

  # === LAYER IDENTITY ===
  domain: platform
  layer_type: core

  scope:
    resource_types:
      - Compute.Container
      - Compute.Pod
    # Empty list = type-agnostic (applies to all resource types)

  priority:
    value: "200.30.10"
    label: "security.container.cpu_limits"
    category: security
    rationale: >
      CPU limit enforcement for container workloads per
      CISO mandate SEC-2024-047. Overrides platform defaults.

  # === LAYER CHAIN ===
  parent_chain:
    - uuid: "base-layer-uuid-001"
      handle: "system/base/universal-defaults"
      version: "1.0.0"
      layer_type: base

  # === FIELDS ===
  fields:
    cpu_limit:
      value: 8
      metadata:
        basis_for_value: "CISO mandate SEC-2024-047-rev2"
        baseline_value: 4
      override: constrained
      constraint_schema:
        minimum: 1
        maximum: 8
```

---

---

## 5. Precedence and Merge Rules

When layers are merged to produce the assembled payload, fields from higher-precedence layers override fields from lower-precedence layers. The precedence order from lowest to highest is:

```
1. Base Layer                    (lowest precedence — foundation defaults)
2. Core Layers                   (organizational and infrastructure context)
3. Intermediate/Customization    (organizational hierarchy overrides)
4. Service Layers                (service-specific configuration)
5. Request Layer                 (consumer intent — overrides all data layers)
6. Transformation Policies       (enrichment — adds or modifies fields)
7. Validation Policies           (pass/fail — no field modification)
8. GateKeeper Policies           (highest authority — overrides everything)
```

### 5.1 Override Behavior

- A higher-precedence layer that declares a field **overrides** the value from all lower-precedence layers
- A higher-precedence layer that does **not** declare a field leaves the lower-precedence value intact
- Fields not declared at any layer level are absent from the payload — providers must declare all required fields as being covered by at least one layer in the chain
- GateKeeper policies can override **any** field including consumer-declared Request Layer values — this is the mechanism for enforcing sovereignty constraints, security mandates, and hard compliance rules

### 5.2 Additive vs. Override Fields

Some fields are **scalar** (a single value — one layer wins) and some are **additive** (a list or set — layers contribute to a collection). The field type in the Resource Type Specification declares which behavior applies:

```yaml
field_name:
  type: <string|integer|boolean|enum|uuid|object|list>
  merge_behavior: <override|additive>
  # override: higher precedence layer's value replaces lower precedence value
  # additive: all layers contribute their values to a merged collection
```

### 5.3 Conflict Resolution

When two layers at the same precedence level declare conflicting values for the same field:
- The conflict is recorded and surfaced as a validation error
- The request is not processed until the conflict is resolved
- Conflict resolution is never silent — it is always recorded in provenance

---

## 5a. Field Override Control

Field override control is the mechanism by which DCM governs **who can change what, under what conditions**, across the layer precedence chain. It was present in the original data model rules as "override preference" metadata on fields — this section formalizes that concept as a graduated model that is **simple by default and powerful when needed**.

**Design Principle:** A field with no override declaration is fully overridable by anyone. Restrictions are always opt-in. The model has three levels — you use only the level you need. Levels 1 and 2 cover the vast majority of real-world cases. Level 3 exists for fields that genuinely require nuanced, actor-specific governance.

---

### 5a.1 Two Categories of Override Rule

**Category 1 — Structural Rules (Request Payload Processor — non-overridable)**

Enforced by the Request Payload Processor as DCM System behavior. Not configurable. Always applied:

- A layer entity is immutable once versioned — no override can modify a published version
- A child layer cannot remove a field declared in a parent layer — it can only override the value
- The layer precedence order is fixed — Base → Core → Intermediate → Service → Request → Policy
- Circular layer references are rejected unconditionally
- A Service Layer without a declared type scope is rejected unconditionally

**Category 2 — Business Rules (Policy Engine — configurable)**

Enforced by the Policy Engine using the Validation/Transformation/GateKeeper mechanism. Override control metadata is set exclusively by the Policy Engine and carried in the payload as part of field-level provenance. Data layers and the Request Payload Processor never set override control.

---

### 5a.2 Where Override Control is Declared

Override control can be declared at two static levels and applied dynamically at runtime:

**Level A — Resource Type Specification (portable, sets the ceiling)**
Declares the default override behavior for a field across all implementations of that Resource Type. These defaults travel with the type definition and apply to all providers and catalog items that implement the type. This sets the maximum permissiveness ceiling — lower levels can only restrict further.

**Level B — Catalog Item (offering-specific, can only restrict)**
Declares additional restrictions for a specific curated offering beyond the Resource Type defaults. A "PCI Production VM" catalog item can lock `encryption_standard` to a single value even if the VM Resource Type allows a broader enum. Cannot expand beyond what the Resource Type permits.

**Level C — Policy Engine (runtime, within static bounds)**
Applies override control at request processing time based on current organizational policies. Can only restrict within the bounds established by the Catalog Item (or Resource Type if no Catalog Item restriction exists). Higher-authority policy levels (Global) can grant expansion to trusted actors within their authority scope.

**Inheritance Rule:** Override control can only be made more restrictive as it flows down the declaration hierarchy — Resource Type → Catalog Item → Runtime Policy. The sole exception is explicit trusted grants made by higher-authority actors (see Section 5a.6).

---

### 5a.3 Level 1 — No Declaration (Default)

No override control declaration on a field means it is fully overridable by any actor. This is the default for all fields. Zero configuration required.

```yaml
# Level 1 — fully overridable, no declaration needed
cpu_count:
  value: 4
```

This covers the majority of fields in most implementations.

---

### 5a.4 Level 2 — Simple Declaration

A single `override` property covers the most common governance needs without requiring a full matrix. Sufficient for most governed fields.

```yaml
# Level 2a — nobody can change this
sovereignty_zone:
  value: us-east
  override: immutable

# Level 2b — anyone can change but only within these values
encryption_standard:
  value: AES-256
  override: constrained
  constraint_schema:
    enum: [AES-256, AES-128]

# Level 2c — explicit allow (same as default, but self-documenting)
display_name:
  value: my-vm
  override: allow
```

| Value | Meaning | Enforcement |
|-------|---------|-------------|
| `allow` | Default. Any actor may override. | Structural rules |
| `constrained` | Any actor may override within `constraint_schema` | Policy Engine — Validation |
| `immutable` | No actor may override at any level | Policy Engine — GateKeeper |

---

### 5a.5 Level 3 — Matrix Declaration

Full actor-level control for fields that require nuanced governance. Used only when Level 2 is insufficient.

```yaml
billing_tag:
  value: engineering
  override_matrix:
    default: allow
    # Default permission for any actor not explicitly listed
    # Options: allow | constrained | deny

    inheritance: restrict_only
    # Catalog Items and lower-level declarations can only restrict
    # Higher-authority actors can grant expansion via trusted_grants

    actors:
      - actor: policy.global
        permission: allow
        can_expand: true
        # Global policies can always override and can grant expansion
        # to lower actors via trusted_grants

      - actor: policy.tenant
        permission: allow
        can_expand: true
        # Tenant policies can override and grant within global ceiling

      - actor: policy.user
        permission: deny
        can_expand: false
        # User policies cannot override and cannot grant to others

      - actor: consumer_request
        permission: constrained
        constraint_schema:
          pattern: "^[a-z0-9-]+$"
        can_expand: false
        # Consumers can override within pattern, cannot grant expansion

      - actor: process_resource
        permission: deny
        can_expand: false
        # Automation denied by default — grant via trusted_grants

      - actor: provider
        permission: deny
        can_expand: false
        # Providers cannot modify this field

      - actor: sre_override
        permission: allow
        can_expand: false
        # SREs have operational authority but cannot grant to others

      - actor: admin_override
        permission: allow
        can_expand: true
        # Admins can override and grant within their scope level

    trusted_grants:
      # Explicit expansion grants from higher-authority actors
      # Used when an actor needs more permission than their default
      - granted_to_uuid: <uuid of specific automation pipeline>
        actor_type: process_resource
        permission: allow
        granted_by_policy_uuid: <uuid of policy granting this>
        reason: Patching automation trusted to update billing_tag
        expires: <ISO 8601 timestamp — optional>

    constraint_schema:
      pattern: "^[a-z0-9-]+$"
      # Applied to all actors with permission: constrained
```

---

### 5a.6 Actor Registry

The actor list is extensible. DCM ships with built-in actors. Organizations register custom actors following the same model. Custom actors default to `deny` until explicitly granted permissions.

**Built-in actors:**

| Actor | Default Scope | Can Expand | Notes |
|-------|--------------|------------|-------|
| `policy.global` | All tenants | ✅ | Highest authority — can grant to any actor |
| `policy.tenant` | Single tenant | ✅ | Within global ceiling |
| `policy.user` | Single user | ❌ | Can only restrict |
| `consumer_request` | Request submitter | ❌ | Can only restrict |
| `process_resource` | Automation execution | ❌ by default | Requires trusted grant |
| `provider` | Service Provider | ❌ | Can only restrict |
| `sre_override` | SRE team | ❌ | Operational authority, cannot grant |
| `admin_override` | DCM Admin | ✅ | Within their scope level |

**Custom actor registration:**

```yaml
custom_actor:
  uuid: <uuid>
  name: <actor name>
  description: <description>
  registered_by_tenant_uuid: <uuid — or null for global>
  default_permission: deny
  # Custom actors always default to deny until explicitly granted
  can_expand: false
  # Custom actors cannot expand by default — requires explicit grant
  version: <Major.Minor.Revision>
  status: <active|deprecated|retired>
  provenance:
    <standard provenance metadata>
```

Custom actors follow the universal versioning and deprecation model. A custom actor registered at Tenant scope cannot be granted Global-level authority.

---

### 5a.7 Expansion Rules

Actor expansion follows a strict hierarchy:

- **`policy.global`** and **`admin_override`** at global scope — can grant expansion to any actor for any field, including fields declared `immutable` at lower levels
- **`policy.tenant`** and **`admin_override`** at tenant scope — can grant expansion within their tenant, cannot expand beyond what Global permits
- **`policy.user`**, **`consumer_request`**, **`provider`** — can never grant expansion regardless of what they receive
- **`sre_override`** — can never grant expansion but can be granted expansion by Tenant or Global
- **`process_resource`** — denied by default, can be granted expansion by Tenant or Global via `trusted_grants`
- **Custom actors** — denied by default, can be granted expansion by the level that registered them or higher

**Trusted grants expire** — if an `expires` timestamp is set, the grant is automatically revoked at that time. Expired grants are retained in provenance for audit purposes but are no longer applied.

---

### 5a.8 Override Control in the Assembly Process

Override control is applied during Step 5 (Policy Processing) of the assembly process:

```
Layer Merge complete (Steps 1-4)
  │  Fields have values — all fields default to Level 1 (allow)
  │  Static override declarations from Resource Type and Catalog Item are loaded
  ▼
Transformation Policies
  │  May set override: constrained or override_matrix on fields
  │  May set baseline_value and basis_for_value metadata
  │  Records policy UUID, level, and reason in field provenance
  ▼
Validation Policies
  │  Verify existing override declarations are not violated
  │  Verify actor permissions against current override_matrix
  │  Pass/fail — no modification to override control
  ▼
GateKeeper Policies
  │  May set override: immutable on fields
  │  May override field values before locking
  │  May issue trusted_grants to specific actors
  │  Records policy UUID, level, lock type, and reason in provenance
  ▼
Requested State
  │  All governed fields carry full override control metadata
  │  Provenance chain complete — every lock and grant is traceable
  ▼
```

---

### 5a.9 Override Control and Rehydration

During rehydration, the Intent State is replayed through the **current** Policy Engine. Override control declared in current policies is applied fresh. A field that was `allow` in the original request may be `immutable` if a new GateKeeper policy was added since. This is by design — rehydration applies current governance standards, not historical ones.

The original consumer intent is preserved unchanged in the Intent Store. The new realized state reflects current governance. Both are auditable and traceable.

The one exception is `pinned` policy version rehydration (Historical Exact or Historical Portable modes) — this deliberately replays historical policies and may bypass current immutable locks. Pinned rehydration requires elevated authorization precisely for this reason.

---

### 5a.11 Global Policy Self-Override — The Immutable Ceiling Model

**Q51 resolved:** When a Global GateKeeper policy sets `override: immutable` on a field, can a higher-priority Global policy still override it?

**The answer emerges from execution order.** Policies execute highest-priority-first (highest numeric value first within a tier). The first policy to set `override: immutable` on a field locks it. All subsequent policies — including other Global policies with lower priority values — find the field locked and cannot modify it. In normal request processing, **default `immutable` is effectively absolute** — not through a special rule, but through execution order.

**The `immutable_ceiling` declaration** is a forward-looking protection for fields that must remain locked even if a higher-priority policy is **added to the system later**:

```yaml
# Default immutable — protected by execution order during this request
# The highest-priority Global GateKeeper to run first locks it
# No subsequent policy in this execution can change it
sovereignty_zone:
  value: eu-west
  override: immutable
  # Safe in practice — execution order guarantees the first-runner wins
  # Does NOT protect against a new higher-priority policy being added tomorrow

# Absolute immutable — explicit forward-looking protection
# Protected even if a new higher-priority policy is added to the system
classification_level:
  value: RESTRICTED
  override: immutable
  immutable_ceiling: absolute
  # Cannot be overridden by ANY policy, ever
  # If a policy attempts to override this, it receives a hard rejection
  # The attempted override is logged in audit with full provenance
  # Use for: sovereignty zones, data classification, hard compliance mandates
```

**The formal rule:**

| Declaration | Protected During Execution? | Protected Against Future Policies? | Use Case |
|-------------|----------------------------|-------------------------------------|---------|
| `override: immutable` (default) | ✅ Yes — execution order | ❌ No | Most governed fields |
| `override: immutable` + `immutable_ceiling: absolute` | ✅ Yes | ✅ Yes — hard rejection | True non-negotiables |

**`immutable_ceiling: absolute` is the nuclear option.** Use it sparingly — only for fields where the governance requirement is genuinely non-negotiable regardless of any future organizational policy change. Sovereignty zone on a sovereign deployment. Data classification on a restricted system. Encryption standard under a regulatory mandate with no variance permitted.

**Audit behavior:** When a policy attempts to override a field with `immutable_ceiling: absolute`, the attempt is rejected silently from the requesting policy's perspective (the field simply doesn't change) but is fully logged in the Audit Store with the policy UUID, the attempted value, the rejection reason, and the UUID of the policy that set the ceiling.

---

### 5a.10 Override Control Metadata — Full Structure

The complete field metadata structure carrying override control in the payload:

```yaml
field_name:
  value: <current value>
  metadata:
    # Simple declaration (Level 2) — set by Policy Engine at runtime
    override: <allow|constrained|immutable>
    # OR matrix declaration (Level 3) — set by Policy Engine at runtime
    override_matrix:
      <full matrix structure per Section 5a.5>

    # Always present regardless of level
    basis_for_value: <human-readable — why this value was set>
    baseline_value: <the original default before any override>
    locked_by_policy_uuid: <uuid of policy that set this>
    locked_at_level: <global|tenant|user>
    constraint_schema: <JSON Schema — if constrained>

  provenance:
    origin:
      value: <original value>
      source_type: <layer type or source>
      source_uuid: <uuid>
      timestamp: <ISO 8601>
    modifications:
      - sequence: 1
        previous_value: <value before>
        modified_value: <value after>
        source_uuid: <uuid of modifying entity>
        operation_type: <enrichment|transformation|validation|gatekeeping|override|lock|grant>
        actor: <actor type that performed this operation>
        timestamp: <ISO 8601>
        reason: <human-readable>
```

---

The Request Payload Processor assembles the final payload by executing the following **nine steps** in order. Each step is recorded in the payload's provenance chain.

### Step 1 — Intent Capture
The consumer's Request Layer is received and stored as the **Intent State** in the Intent Store. No modification occurs at this step. The Intent State is the immutable record of what the consumer asked for.

### Step 2 — Layer Resolution
The Request Payload Processor determines which layers apply to this request:
- Identifies the Resource Type from the Request Layer
- Retrieves the applicable Base Layer for the request context
- Retrieves all applicable Core Layers (type-agnostic — all apply)
- Retrieves applicable Intermediate/Customization Layers based on organizational context
- Retrieves applicable Service Layers whose declared type scope matches the request Resource Type
- Orders all retrieved layers according to the precedence chain

### Step 3 — Layer Merge
Layers are merged in precedence order (lowest to highest). For each field:
- The value from the highest-precedence layer that declares it is used
- The source layer UUID and layer type are recorded in the field's provenance metadata
- Additive fields accumulate values from all layers that declare them

### Step 4 — Request Layer Application
The consumer's Request Layer is applied last in the data layer merge. Consumer-declared values override all data layer values. Each override is recorded in provenance.

### Step 5 — Pre-Placement Policy Processing
Policies matching the `request.layers_assembled` payload type are evaluated against the merged payload before any provider is known. GateKeeper, Transformation, Validation, and Governance Matrix policies may all fire at this stage — evaluated by the Policy Engine in domain precedence order:

1. **Transformation Policies** — enrich and modify the payload. May set `override: constrained` on fields. Each transformation records the policy UUID, operation type, reason, and any override control declarations in provenance.
2. **Validation Policies** — check the payload against rules. Pass/fail only — no field modification. Failures reject the request.
3. **GateKeeper Policies** — apply hard overrides and blocks. May set `override: immutable`. All overrides recorded in provenance.

Pre-placement policies produce **placement constraints** — declarative requirements a provider must satisfy (sovereignty zone, hardware class, conformance level, etc.). These constraints are carried forward as inputs to the Placement Engine.

### Step 6 — Placement Engine — Placement Loop

The Placement Engine takes the policy-processed payload and placement constraints, builds a candidate provider list (filtered by constraints, ordered by scoring criteria), and iterates through candidates until placement is confirmed or all candidates are exhausted.

**Placement loop governance** (configurable by policy):
```yaml
placement_loop_config:
  max_iterations: 5              # maximum candidates to attempt
  max_duration_seconds: 30       # timeout for entire loop
  on_exhaustion: <reject | escalate | manual_placement>
  hold_ttl_seconds: 300          # how long provider holds resources
```

**Per-candidate iteration:**

```
── RESERVE QUERY (single atomic call to provider) ──
  Request: constraints + resource spec + hold TTL + metadata_requested
  Response status:
    confirmed: resources held, constraints satisfied, metadata returned
    partial:   hold confirmed, some metadata unavailable
    insufficient: provider lacks capacity — skip to next candidate
    refused:   provider cannot satisfy constraints — skip to next candidate

── POLICY PHASE (placement_phase: loop) ──
  Policies evaluate: payload + constraints + reserve query response
  For each field declared in policy required_context:
    Field present:   evaluate normally
    Field absent, required_context declared:
      if_absent: gatekeep  → release hold, abort loop, REJECT REQUEST
      if_absent: warn      → record warning, continue
      if_absent: skip      → record as skipped, continue
    Field absent, no policy declares required_context:
      → record policy_gap_record (implicit_approval), continue
  Policy outcomes:
    gatekeep         → release hold, abort loop, REJECT REQUEST
    reject_candidate → release hold, skip to next candidate
    pass / warn      → PLACEMENT CONFIRMED — exit loop
```

**Reserve query structure:**
```yaml
reserve_query_request:
  request_uuid: <uuid>
  hold_uuid: <uuid — DCM-generated>
  resource_type: <e.g., Compute.VirtualMachine>
  placement_constraints: <from pre-placement policy outputs>
  resource_spec:
    cpu: 16
    ram_gb: 64
    storage_gb: 500
  hold_ttl_seconds: 300
  metadata_requested:
    - capacity_available
    - topology
    - sovereignty_certifications
    - patch_level
    - maintenance_windows

reserve_query_response:
  hold_uuid: <echoed>
  provider_hold_reference: <provider-native hold ID — opaque>
  hold_status: <confirmed | insufficient | refused | partial>
  hold_confirmed_spec:
    cpu: 16
    ram_gb: 64
    storage_gb: 500
    zone: eu-west-1a
    rack: rack-07
  metadata:
    topology:
      zone: eu-west-1a
      rack: rack-07
      network_segment: vlan-142
      available_ips: ["10.20.4.0/24"]
    sovereignty_certifications:
      - cert: ISO-27001
        expires_at: "2027-06-30"
    missing_metadata:
      - field: patch_level
        reason: "Provider does not track patch metadata at this conformance level"
```

**Non-hold queries** (available outside the placement loop for capacity checks, provider health, cost estimation, and pre-filtering):

| Query Type | Hold? | Purpose |
|-----------|-------|---------|
| `reserve_query` | Yes — atomic | Primary placement loop query |
| `capacity_query` | No | Pre-loop filtering, dashboard, cost estimation |
| `metadata_query` | No | Provider health checks, audit, policy pre-evaluation |
| `constraint_verification` | No | Rapid pre-filter before entering the loop |

**Policy gap records** — when a field is absent and no policy declares `required_context` for it:
```yaml
policy_gap_record:
  request_uuid: <uuid>
  field: patch_level
  field_value: null
  evaluation_result: implicit_approval
  reason: >
    No active policy declared required_context for this field.
    Field was absent in reserve query response.
    Request proceeded without policy evaluation of this field.
  provider_uuid: <uuid>
  recorded_at: <ISO 8601>
  resolution_expected: realized_payload
  # Provider expected to supply this field in the realized payload or discovery
```

**Provider metadata completeness — eventual consistency:**
Fields missing from the reserve query response are expected to be completed in:
1. **Realized payload** (primary) — provider returns full metadata when confirming realization
2. **Discovery loop** (fallback) — periodic discovery fills remaining gaps

The realized entity carries `enrichment_status: pending | partial | complete` reflecting how complete its metadata is. This is the same pattern as the ingestion model.

### Step 7 — Post-Placement Policy Processing
Policies with `placement_phase: post` (or `both`) execute after the Placement Engine has confirmed a provider selection. These policies have full access to the `placement` block of the payload including the provider selection, hold confirmation, and all returned metadata.

1. **Transformation Policies** — provider-aware enrichment. Inject zone-specific configuration, provider-specific defaults, topology-derived values that are only knowable after provider selection.
2. **Validation Policies** — post-placement checks. Verify the selected provider meets requirements that couldn't be expressed as pre-placement constraints.
3. **GateKeeper Policies** — post-placement hard overrides. May inject mandatory fields triggered by the specific provider selected (e.g., additional data handling requirements for a provider in a specific jurisdiction).

**Policy `placement_phase` values:**
```yaml
policy:
  placement_phase: <pre | loop | post | both>
  # pre:  steps 5 — before provider known (default)
  # loop: step 6 — inside placement loop, evaluates reserve query response
  # post: step 7 — after placement confirmed, provider known
  # both: pre and post (not loop)
```

**Policy `required_context` for missing metadata:**
```yaml
policy:
  placement_phase: loop
  required_context:
    - field: placement.provider_metadata.sovereignty_certifications
      if_absent: gatekeep
      if_absent_reason: >
        Cannot evaluate sovereignty compliance without provider
        certification data. Blocking request. Provider must register
        this metadata to participate in sovereignty-scoped requests.
    - field: placement.provider_metadata.patch_level
      if_absent: warn
      if_absent_reason: >
        Patch level not available. Proceeding with warning.
        Provider notified to register patch metadata.
```

### Step 8 — Requested State Storage
The fully assembled, policy-processed, placement-confirmed payload is stored as the **Requested State** in the Request Store. The Requested State includes:
- All assembled resource fields with full provenance chain
- Complete `placement` block: selected provider, hold UUID, all reserve query responses per iteration, all policy evaluations per iteration, placement constraints applied, alternatives considered
- All `policy_gap_record` entries for implicit approvals
- `enrichment_status` reflecting metadata completeness at dispatch time

### Step 9 — Provider Dispatch
The Requested State payload is dispatched to the selected Service Provider via the API Gateway. The resource hold placed during the Placement Loop is confirmed by dispatch. The provider uses the hold reference to fulfill the request against the reserved resources.

---

---

## 7. Layer Assembly Diagram

```
Consumer Request
      │
      ▼
┌─────────────────┐
│  REQUEST LAYER  │  ← Consumer declared intent → stored as INTENT STATE (Step 1)
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│             LAYER RESOLUTION + MERGE (Steps 2-4)         │
│                                                          │
│  Base Layer          (lowest precedence)                 │
│       ↓                                                  │
│  Core Layers         (type-agnostic context)             │
│       ↓                                                  │
│  Intermediate Layers (organizational context)            │
│       ↓                                                  │
│  Service Layers      (type-scoped service config)        │
│       ↓                                                  │
│  Request Layer       (consumer intent — highest          │
│                       data layer precedence)             │
└────────┬────────────────────────────────────────────────┘
         │  Merged payload with full provenance
         ▼
┌─────────────────────────────────────────────────────────┐
│          PRE-PLACEMENT POLICY PROCESSING (Step 5)        │
│                                                          │
│  Transformation Policies  (enrich / modify)              │
│       ↓                                                  │
│  Validation Policies      (pass / fail check)            │
│       ↓                                                  │
│  GateKeeper Policies      (override / block)             │
│       ↓ outputs: placement constraints                   │
└────────┬────────────────────────────────────────────────┘
         │  Policy-processed payload + placement constraints
         ▼
┌─────────────────────────────────────────────────────────┐
│              PLACEMENT ENGINE — LOOP (Step 6)            │
│                                                          │
│  For each candidate provider (filtered + scored):        │
│    │                                                     │
│    ├── Reserve Query (atomic: verify + metadata + hold)  │
│    │     confirmed / partial → policy phase              │
│    │     insufficient / refused → next candidate         │
│    │                                                     │
│    └── Loop Policy Phase (placement_phase: loop)         │
│          Field present → evaluate normally               │
│          Field absent + required_context → if_absent     │
│          Field absent + no policy → implicit_approval    │
│          pass/warn → PLACEMENT CONFIRMED                 │
│          reject_candidate → release hold, next           │
│          gatekeep → release hold, REJECT REQUEST         │
│                                                          │
│  No candidates remain → on_exhaustion behavior           │
└────────┬────────────────────────────────────────────────┘
         │  selected_provider_uuid + placement block
         ▼
┌─────────────────────────────────────────────────────────┐
│         POST-PLACEMENT POLICY PROCESSING (Step 7)        │
│                                                          │
│  Transformation Policies  (provider-aware enrichment)    │
│       ↓                                                  │
│  Validation Policies      (post-placement checks)        │
│       ↓                                                  │
│  GateKeeper Policies      (provider-triggered overrides) │
└────────┬────────────────────────────────────────────────┘
         │  Complete, validated, placement-confirmed payload
         ▼
┌─────────────────┐
│ REQUESTED STATE │  ← Stored in Request Store (Step 8)
└────────┬────────┘    includes: placement block, hold records,
         │             policy gap records, enrichment_status
         ▼
   Service Provider  (Step 9 — dispatch, hold confirmed)
```

---

## 8. Layer Scope and Type Enforcement

### 8.1 Core Layer Scope Enforcement
Core Layers are type-agnostic by default. They are applied to every request regardless of Resource Type. A Core Layer that contains service-specific or provider-specific data is invalid and must be rejected.

### 8.2 Service Layer Scope Enforcement
Service Layers must declare a Resource Type scope. The Request Payload Processor enforces this during Layer Resolution:
- A Service Layer whose declared Resource Type does not match the request Resource Type is excluded from the merge
- A Service Layer with `scope_inheritance: exact` is only included if the request Resource Type exactly matches the declared type
- A Service Layer with `scope_inheritance: descendants` is included if the request Resource Type is the declared type or any descendant type in the inheritance hierarchy
- A Service Layer with no declared type scope is invalid and must be rejected

### 8.3 Unanticipated Data Interaction Prevention
The type scoping rules for Service Layers are the primary mechanism for preventing unanticipated data interactions — one of the core data model objectives. Because Service Layers can only contribute to requests of their declared type, data from one service domain cannot inadvertently affect requests in another service domain.

---

## 9. Layer Versioning

All layers follow the universal DCM versioning scheme: **Major.Minor.Revision**

| Component | Trigger |
|-----------|---------|
| **Major** | Breaking changes — removing fields, changing field types, changing a field from optional to required |
| **Minor** | Additive changes — adding new optional fields, adding new contextual data |
| **Revision** | Data/configuration changes — updating field values, updating descriptions, updating metadata |

**Immutability:** Once a layer version is published it cannot be modified. Any change produces a new version. Previous versions remain accessible and can be referenced by existing realized entities.

**Parent Chain Versioning:** A layer's parent chain references specific versions of parent layers. Updating a parent layer does not automatically update child layers — child layers must be explicitly updated to reference the new parent version, producing a new version of the child layer.

---

## 10. Artifact Lifecycle — The Five Statuses

All DCM artifacts — layers, policies, resource types, catalog items, and all other defined objects — follow a five-status lifecycle. The statuses are defined in Section 4b.2. For layers specifically:

| Status | Layer Behavior |
|--------|---------------|
| `developing` | Layer is in active development. Only usable in development mode pipelines. Not loaded by the assembly process in production. |
| `proposed` | Layer has been submitted for review (PR open). Not yet active. For policy layers: shadow execution runs. For data layers: layer is visible in the registry but not applied. Cannot merge to active until PR is approved. |
| `active` | Layer is current and applied in assembly. Can be included in new layer chains. |
| `deprecated` | Layer is being phased out. Existing chains using it continue to function. New chains should use the replacement. Deprecation warning recorded in assembly provenance. Must include replacement UUID, reason, migration guidance, and sunset date. |
| `retired` | Layer cannot be included in new layer chains. Existing realized entities that reference it retain the reference for audit purposes but cannot be used for new requests. |

**Status transition rules for layers:**
```
developing → proposed   (author submits PR)
developing → retired    (author abandons)
proposed   → active     (PR merged — approval complete)
proposed   → developing (PR returned for rework)
active     → deprecated (replacement available — sunset declared)
deprecated → retired    (sunset date reached or manual retirement)
```

---

## 11. Scale Example — 40,000 Linux VMs

This example illustrates the power of the layering model at scale. 40,000 distinct VM configurations are governed by 36 layer definitions:

```
Base Entity (3 variants)
├── CIS Benchmark
├── Baseline
└── DMZ / Payments

  └── Layer Entity — OS Family (3 variants per base = 9 total)
      ├── Common Linux Config / RHEL
      ├── Common Linux Config / CoreOS
      └── Common Linux Config / OEL

        └── Layer Entity — OS Version (4 variants per OS layer = 36 total)
            ├── RHEL 6
            ├── RHEL 7
            ├── RHEL 8
            └── RHEL 9

              └── Realized Entity — one per VM (40,000 total)
                  Each realized entity carries FK references to its
                  full layer chain (Base UUID + Layer UUIDs)
                  and is stored in the CMDB
```

**Result:** 3 × 3 × 4 = **36 layer definitions** govern **40,000 VM configurations**. Each VM's realized entity is a lightweight reference to its layer chain — not a copy of all the configuration data.

This also means:
- Updating the CIS Benchmark base layer creates one new layer version that cascades to all 40,000 VMs at their next realization
- Drift detection compares each VM's discovered state against its realized entity's layer chain
- Any VM can be reproduced exactly by replaying its layer chain through the assembly process

---

## 12. Relationship to the Four States

| Layer | State Relationship |
|-------|-------------------|
| Request Layer (as submitted) | Directly captured as **Intent State** — stored in Intent Store before any processing |
| Assembled payload (post-merge, pre-policy) | Intermediate — not a named state, internal to assembly process |
| Assembled payload (post-policy) | Becomes **Requested State** — stored in Request Store |
| Provider execution result | Becomes **Realized State** — stored in Realized Store |
| Discovery interrogation result | Becomes **Discovered State** — stored in Discovered Store |

The layer chain of a Realized Entity is always traceable — given a Realized State record, the complete layer chain that produced it can be reconstructed, providing full audit capability back to the original Base Layer.

---

## 13. Layer Gaps — Q21 through Q24

### 13.1 Consumer Layer Exclusion (Q21)

Consumers may explicitly exclude specific layers from their request. Each exclusion carries a mandatory human-readable reason recorded in provenance and the audit trail.

```yaml
request:
  resource_type: Compute.VirtualMachine
  layer_exclusions:
    - layer_handle: "platform/networking/default-dns-config"
      reason: "This VM uses custom DNS — default config conflicts with application requirements"
    - layer_uuid: <uuid>
      reason: "Dev environment — monitoring layer not required"
```

**Exclusion mechanics:**
- Excluded layers are removed from the candidate set during **Step 2 (Layer Resolution)** before priority ordering
- Excluded layers produce no fields in the assembled payload
- If a validation policy requires a field that would have been injected by an excluded layer, the validation fails with a clear message identifying the excluded layer
- Exclusion is different from override — exclusion removes the entire layer; override changes specific field values

**Policy enforcement:** GateKeeper policies may declare specific layers non-excludable:

```yaml
policy:
  type: gatekeeper
  rule: >
    If request.layer_exclusions CONTAINS layer.concern_tags CONTAINS "security-baseline"
    THEN gatekeep: "Security baseline layers cannot be excluded"
  immutable_ceiling: absolute
```

### 13.2 Service Layer Versioning (Q22)

Service Layers are **independently versioned artifacts** — not coupled to Service Provider versions. Service Providers declare semver-compatible version constraints for the layers they use.

```yaml
# Service Provider registration — layer compatibility declarations
provider_registration:
  layer_compatibility:
    - layer_handle: "layers/vm-compute-defaults"
      compatible_versions: "^1.0.0"    # any 1.x version
    - layer_handle: "layers/vm-networking-config"
      compatible_versions: "~1.2"      # any 1.2.x revision
```

**Version lifecycle:** Service Layers follow the standard five-status artifact lifecycle. A deprecated Service Layer continues to work for existing realizations until retired. If a provider bumps to a new major version and updates its compatibility declaration, the old layer version is no longer used for new requests via that provider but continues to work for existing realizations.

**Cache invalidation:** Service Layer Cache entries carry the layer version. When the registered layer version increments, the cache entry is invalidated and refreshed before the next assembly.

### 13.3 Conditional Layer Inclusion (Q23)

Layers may declare an `activation_condition` — a field comparison evaluated during **Step 2 (Layer Resolution)**. Layers whose condition evaluates false are excluded from the candidate set.

```yaml
layer:
  handle: "platform/compute/gpu-config"
  activation_condition:
    field: request.gpu_requested
    operator: equals
    value: true
```

**Compound conditions:**
```yaml
activation_condition:
  conditions:
    operator: and   # and | or
    rules:
      - field: request.gpu_requested
        operator: equals
        value: true
      - field: request.resource_class
        operator: in
        value: [ml-training, gpu-compute]
```

**Condition field scope** — activation conditions may reference:
- Request fields (`request.gpu_requested`)
- Tenant attributes (`tenant.tags`, `tenant.profile`)
- Resource type fields (`resource_type.version`)
- Core Layer fields already resolved in Step 1 (`core_layers.location_region`)
- Ingress fields (`ingress.actor.roles`) — enabling role-specific layers

**Condition vs consumer exclusion:** Conditional inclusion is declared by the layer author and evaluated automatically. Consumer exclusion (Q21) is declared at request time by the consumer. Both result in the layer being absent from the candidate set — but for different reasons, recorded differently in provenance.

### 13.4 Layer Chain and Service Dependencies (Q24)

Each service dependency executes its **own independent layer chain** during assembly. Dependencies do not share the parent request's layer chain.

**Dependencies inherit from parent (read-only context):**
- Tenant UUID and sovereignty context
- Parent's resolved placement fields (declared by Resource Type Specification as `propagated_to_dependencies`)
- Parent's resolved identity fields (hostname, etc.)
- Active Profile

**Dependencies do NOT inherit:**
- Parent consumer declarations
- Resource-type-specific layers (each type has its own)
- Provider-specific layers (each provider has its own)

**Dependency assembly flow:**
```
Parent request: Compute.VirtualMachine
  │
  ▼  Steps 1-4: Parent layer chain → parent_assembled_payload
  │
  ▼  Step 5: Pre-placement policies on parent
  │
  ▼  Step 6: Placement loop — parent provider selected
  │           Also identifies required dependency providers
  │
  ▼  For each dependency (parallel where ordering allows):
  │  ├── Network.IPAddress → own layer chain (Steps 1-4)
  │  │     Context: inherits parent resolved placement fields
  │  ├── Network.Port → own layer chain (Steps 1-4)
  │  │     Context: inherits parent + IP resolution result
  │  └── DNS.Record → own layer chain (Steps 1-4)
  │         Context: inherits parent + IP + Port results
  │
  ▼  Steps 7-9: Post-placement, storage, dispatch
       Parent + all dependency payloads dispatched together
```

**Layer exclusions on dependencies** — consumers may declare per-dependency exclusions:
```yaml
request:
  resource_type: Compute.VirtualMachine
  dependencies:
    - resource_type: Network.IPAddress
      layer_exclusions:
        - layer_handle: "layers/ip-default-ttl-config"
          reason: "Custom TTL required — excluding default"
```

---

## 13b. Override Control and Constraint Visibility Gaps

### 13b.1 Override Preference Enforcement (Q50)

Layer fields declare override intent using three values. The Request Payload Processor enforces this during assembly Step 3 (Layer Merge) — no separate GateKeeper policy required.

```yaml
fields:
  dns_servers:
    value: [10.0.0.53, 10.0.0.54]
    metadata:
      override: allow          # lower layers and consumers may change this

  encryption_at_rest:
    value: true
    metadata:
      override: immutable      # no lower-domain layer or consumer may change this
      lock_reason: "CISO mandate SEC-2024-047 — encryption always required"

  cpu_count:
    value: 4
    metadata:
      override: constrained    # may change within declared bounds
      constraint:
        type: range
        min: 1
        max: 32
        step: 1
      constraint_reason: "Platform capacity planning bounds"
```

**Authority rule:** `immutable` prevents overrides only from *lower-authority domains*. A `platform` domain field marked `immutable` cannot be changed by `tenant`, `service`, `provider`, or `request` layers — but a `system` domain layer above it can still override it. Higher authority always wins.

**GateKeeper escalation:** A GateKeeper policy at a higher authority level may additionally lock a field that a layer marked `allow` — this is the compliance escape hatch for mandates the layer author did not anticipate.

**Enforcement point:** Step 3 (Layer Merge) — if a lower-priority layer or consumer request sets a field marked `immutable`, assembly halts with a clear error identifying the conflicting layer and the locking layer.

### 13b.2 Constraint Schema Visibility (Q52)

Constrained fields expose their constraint schema to consumers in the Service Catalog UI and Consumer API at a policy-governed disclosure level.

```yaml
constraint_visibility:
  level: <full|summary|hidden>
  # full:    Show constraint type, bounds, constraint_reason, suggested values
  # summary: Show bounds only — no reason, no suggestions
  # hidden:  Field appears free-form; constraint silently enforced at submission
```

**Profile defaults:**

| Profile | Default Level | Rationale |
|---------|--------------|-----------|
| `minimal` | `full` | All context helpful |
| `dev` | `full` | Developers benefit from full schema |
| `standard` | `full` | Good developer experience |
| `prod` | `summary` | Bounds visible; reasons may be sensitive |
| `fsi` | `summary` | Regulatory constraints may not need full exposure |
| `sovereign` | `hidden` | Constraint details may be operationally sensitive |

**UI rendering (full mode):**
```
VM Size — CPU Count
  Enter a value between 1 and 32 (whole numbers)
  Suggested: 2, 4, 8, 16
  Reason: Platform capacity planning bounds
```

**API endpoint:** `GET /api/v1/catalog/items/{id}/schema` returns field schemas at the declared visibility level for the authenticated consumer's Tenant profile.

Policy may override the profile default per field or resource type:
```yaml
policy:
  type: transformation
  rule: >
    If resource_type == Compute.VirtualMachine
    AND field.name == cpu_count
    THEN set: constraint_visibility.level = full
```

### 13b.3 System Policies — Override Control

| Policy | Rule |
|--------|------|
| `LAY-005` | Layer fields declare override intent as allow, constrained, or immutable. The Request Payload Processor enforces override declarations during assembly Step 3. immutable prevents overrides from lower-authority domains only — higher-domain layers may always override. GateKeeper policies may additionally lock allow or constrained fields at runtime. |
| `LAY-006` | Constraint schemas on constrained fields are visible to consumers in the Service Catalog UI and Consumer API at a policy-governed disclosure level: full (constraint, bounds, reason, suggestions), summary (bounds only), or hidden (enforced but not displayed). Profile sets the default. Policy may override per field or resource type. |


## 13a. Layer System Policies

| Policy | Rule |
|--------|------|
| `LAY-001` | Consumers may declare `layer_exclusions` in their request. Each exclusion must carry a human-readable reason recorded in provenance. GateKeeper policies may declare specific layers non-excludable. Excluded layers produce no fields in the assembled payload. |
| `LAY-002` | Service Layers are independently versioned artifacts. Service Providers declare layer compatibility using semver constraints. Service Layer Cache entries carry the layer version and are invalidated when the registered version changes. |
| `LAY-003` | Service Layers may declare `activation_condition` evaluated during Step 2 (Layer Resolution). Layers whose conditions evaluate false are excluded from the candidate set. Condition evaluation results are recorded in the assembly provenance. Conditions may reference request fields, tenant attributes, resource type fields, resolved core layer fields, and ingress fields. |
| `LAY-004` | Each service dependency executes its own independent layer chain during assembly. Dependencies inherit the parent's resolved placement and identity fields as declared by the Resource Type Specification. Dependencies do not inherit parent consumer declarations, resource-type-specific layers, or provider-specific layers. Layer exclusions may be declared per-dependency. |

---

## 14. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | How are conflicting Service Layers at the same precedence level resolved? | Assembly determinism | ✅ Resolved — priority schema + conflict detection at ingestion |
| 2 | Should Core Layers be ordered within their precedence level? | Merge determinism | ✅ Resolved — priority schema provides deterministic ordering |
| 3 | Can a consumer explicitly exclude a layer from their request? | Consumer control vs. standardization | ✅ Resolved — layer_exclusions with mandatory reason; GateKeeper can lock layers as non-excludable (LAY-001) |
| 4 | How are Service Layers registered and versioned relative to Service Provider registration? | Provider contract | ✅ Resolved — independently versioned; provider declares semver compatibility; cache invalidation on version change (LAY-002) |
| 5 | Should assembly support conditional layer inclusion? | Assembly flexibility | ✅ Resolved — activation_condition on layers; evaluated in Step 2; references request, tenant, resource type, core layer, and ingress fields (LAY-003) |
| 6 | How does the layer chain interact with service dependencies? | Dependency model | ✅ Resolved — each dependency has its own layer chain; inherits parent resolved placement context; no consumer declaration inheritance (LAY-004) |
| 7 | Should `override_preference` be declarable in layer definitions as a hint to the Policy Engine? | Override control | ✅ Resolved — override: allow/constrained/immutable enforced by Request Payload Processor at Step 3; GateKeeper may additionally lock (LAY-005) |
| 8 | When `override_preference: immutable` is set — can a higher-priority policy still override it? | Override control precedence | ✅ Resolved — immutable prevents lower-authority overrides only; higher-domain layers always win; GateKeeper can additionally lock (LAY-005) |
| 9 | Should the `constraint_schema` on a constrained field be visible to consumers in the Service Catalog UI? | Consumer experience | ✅ Resolved — full/summary/hidden disclosure levels; profile-governed defaults; API endpoint returns schema at declared visibility (LAY-006) |
| 10 | Should the background validation job for detecting post-ingestion conflicts run on a schedule or be event-triggered? | Operational | ✅ Resolved — event-triggered primary (on layer ingestion/update) + weekly scheduled sweep safety net; async non-blocking; both produce same conflict record format (OPS-003) |
| 11 | What is the minimum validation review period for a proposed policy before it can be activated? | Policy governance | ✅ Resolved — GateKeeper=14d, Validation=7d, Transformation=3d × profile multiplier (minimal=0×, dev=0.5×, standard=1×, prod=1.5×, fsi/sovereign=2×); DCM enforces; emergency bypass requires dual-approval audit (OPS-004) |

---

## 14. Related Concepts

- **Request Payload Processor** — the control plane component that executes the assembly process; enforces structural layer rules
- **Policy Engine** — executes Policy Layers (Validation, Transformation, GateKeeper) during the assembly process; the sole authority for setting field override control
- **Field Override Control** — the mechanism governing who can change what field, under what conditions, at what policy level
- **Override Preference** — per-field metadata declaring `allow`, `constrained`, or `immutable` — the formalization of the original data model "override preference" subtag
- **Service Layer Cache** — caches Service Layer data at Service Provider registration time for efficient retrieval during assembly
- **Core Layer Store** — stores all Core Layer definitions
- **Intent State** — the Request Layer as submitted, before assembly
- **Requested State** — the fully assembled, policy-processed payload
- **Field-Level Provenance** — every field in the assembled payload records which layer set it and which policy modified it
- **Resource Type Hierarchy** — defines the type scope that Service Layers must declare and that the assembly process enforces
- **GitOps** — all layers are stored in Git, versioned and immutable

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
