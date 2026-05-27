# UDLM — Worked Examples

**Document Status:** ✅ Stable — UDLM substrate illustration
**Document Type:** Reference Examples

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM substrate.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: DATA + PROVIDER + POLICY**
>
> Worked examples showing all three abstractions in operation.

**Related Documents:** [Context and Purpose](context-and-purpose.md) | [Four States](four-states.md) | [Entity Types](entity-types.md) | [Ownership, Sharing, and Allocation](ownership-sharing-allocation.md) | [Layering and Versioning](layering-and-versioning.md)

---

## 1. Purpose

This document provides end-to-end worked examples that make the UDLM data model concrete. Each example traces the complete lifecycle of a resource through the substrate — from consumer intent through the four states, showing exactly what data exists at each stage.

These examples describe substrate-level behavior. Specific orchestration scenarios, runtime mechanics, and realization-specific composite flows live in the consuming realization's documentation (for example, DCM's `orchestration-scenarios.md`).

---

## 2. Optional Git-Backed Ingress Layout (Illustrative)

> **Note:** Git is one possible ingress adapter, not a required state store. UDLM does not mandate Git for any of the four data domains (Intent, Requested, Realized, Discovered); a conformant realization MAY use Git as an ingress surface or as a working store, or it MAY not. The layouts below are illustrative — they show one way to organize handle-based directories when Git ingress is enabled.

The Intent store can use a handle-based directory structure within Git when Git ingress is enabled. Tenant isolation is enforced at the directory level. Provider selection is recorded in the assembled payload, not in the directory structure — so the directory structure is independent of which provider was selected.

### 2.1 Intent Store Layout (Illustrative)

```
intent-store/
├── {tenant-uuid}/
│   ├── {resource-type-category}/
│   │   ├── {resource-type}/
│   │   │   ├── {entity-uuid}/
│   │   │   │   ├── intent.yaml          ← consumer's raw declaration
│   │   │   │   └── .metadata.yaml       ← intent metadata (created_by, timestamp, ingress surface)
│   │   │   └── {entity-uuid-2}/
│   │   │       ├── intent.yaml
│   │   │       └── .metadata.yaml
│   │   └── ...
│   └── ...
└── ...

# Example:
intent-store/
└── a1b2c3d4-tenant-uuid/
    └── Compute/
        └── VirtualMachine/
            └── f5e6d7c8-entity-uuid/
                ├── intent.yaml
                └── .metadata.yaml
```

**Branch naming (illustrative):** `intent/{tenant-uuid}/{entity-uuid}` for new requests. `intent/{tenant-uuid}/{entity-uuid}/v{n}` for revisions.

**Merge to main (illustrative):** Triggers downstream assembly — the realization's Request Payload Processor begins assembly.

### 2.2 Requested Store Layout (Illustrative)

```
requested-store/
└── {tenant-uuid}/
    └── {resource-type-category}/
        └── {resource-type}/
            └── {entity-uuid}/
                ├── requested.yaml          ← fully assembled payload
                ├── assembly-provenance.yaml ← complete layer chain and policy evaluation record
                ├── placement.yaml           ← provider selection and placement constraints
                └── dependencies.yaml        ← resolved dependency graph (only present when entity has dependencies)

# Example:
requested-store/
└── a1b2c3d4-tenant-uuid/
    └── Compute/
        └── VirtualMachine/
            └── f5e6d7c8-entity-uuid/
                ├── requested.yaml
                ├── assembly-provenance.yaml
                └── placement.yaml
```

### 2.3 Layer and Policy Store Layout (Illustrative)

**Core layers** are the organization's authoritative declarations — they define what the organization intends, not what providers report. For example, `datacenter-layer.yaml` declares the properties of datacenter `dc-us-east-1` (location, sovereignty zone, available VLANs). Providers are validated against these declarations. A Discovery Service detects drift when provider-reported state diverges from declared layers. Layers are not synced *from* providers — providers are measured *against* them.

```
layers/
├── system/
│   ├── core/
│   │   ├── datacenter-layer.yaml
│   │   └── environment-layer.yaml
│   └── compliance/
│       └── pci-dss-layer.yaml
├── {tenant-uuid}/
│   └── org/
│       └── payments-team-layer.yaml
└── providers/
    └── {provider-uuid}/
        └── vm-defaults-layer.yaml

policies/
├── system/
│   ├── gatekeeper/
│   │   └── vm-size-limits.yaml
│   └── transformation/
│       └── inject-monitoring.yaml
└── {tenant-uuid}/
    └── gatekeeper/
        └── approved-os-images.yaml
```

---

## 3. Example 1 — VM Provision End-to-End

A developer on the AppTeam Tenant requests a standard Linux VM. This example traces the complete lifecycle through all four states.

### 3.1 Consumer Submits Intent (Intent State)

The developer submits the following intent via the Consumer API:

```yaml
# intent-store/a1b2c3d4-tenant/Compute/VirtualMachine/f5e6d7c8-entity/intent.yaml

apiVersion: udlm.io/v1
kind: ResourceIntent
metadata:
  entity_uuid: f5e6d7c8-e9f0-a1b2-c3d4-e5f6a7b8c9d0
  resource_type: Compute.VirtualMachine
  tenant_uuid: a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6   # AppTeam Tenant
  submitted_by: b2c3d4e5-actor-uuid
  submitted_at: 2026-03-15T09:00:00Z
  ingress_surface: consumer_api

spec:
  # Consumer declares what they need — not how to provision it
  cpu_count: 4
  memory_gb: 8
  storage_gb: 100
  os_family: rhel
  environment: production
  name: "payments-api-server-01"
  # No provider specified — consumer does not choose the provider
```

**Pre-assembly checks (substrate vocabulary):**
- Policy pre-validation: no GateKeeper violations detected (4 CPU is within AppTeam's quota)
- Cost estimation: ~$0.32/hour based on current provider rates
- Dependency check: no dependencies declared — clean
- Sovereignty check: AppTeam's Tenant has `data_residency: EU-WEST` — placement must honor this
- Authorization check: actor b2c3d4e5 has `request:compute:vm` permission in AppTeam Tenant
- Auto-approve evaluation: meets all auto-approve criteria → intent transitions toward Requested

### 3.2 Assembly Produces Requested State

After intent is accepted, the Request Payload Processor performs assembly:

**Layer Resolution and Merge:**

```yaml
# Layer chain assembled (in precedence order, highest to lowest):
# 1. system/core/datacenter-layer.yaml        (system domain)
# 2. system/core/environment-layer.yaml        (system domain)
# 3. system/compliance/eu-west-layer.yaml      (system domain)
# 4. org/appteam-defaults-layer.yaml           (tenant domain)
# 5. providers/openstack/vm-defaults-layer.yaml (provider domain — pre-selected by policy)
# 6. Consumer intent                            (request domain)

# Resulting merged fields before policy evaluation:
cpu_count:
  value: 4                         # from consumer intent
  provenance.origin.source_type: consumer
  provenance.origin.source_uuid: f5e6d7c8-entity

memory_gb:
  value: 8                         # from consumer intent
  provenance.origin.source_type: consumer

storage_gb:
  value: 100                       # from consumer intent

data_center:
  value: "EU-WEST-DC1"             # from datacenter layer
  provenance.origin.source_type: base_layer
  provenance.origin.source_uuid: dc-layer-uuid

environment:
  value: production                # from consumer intent (overrides layer default "dev")
  provenance.modifications:
    - sequence: 1
      previous_value: dev          # layer default
      modified_value: production   # consumer override
      source_type: consumer

monitoring_agent:
  value: "datadog-agent:7.42"     # injected by org layer — consumer did not declare this
  provenance.origin.source_type: intermediate_layer
  provenance.origin.source_uuid: appteam-defaults-layer-uuid

backup_policy:
  value: "daily-30d-eu-west"      # injected by compliance layer
  provenance.origin.source_type: intermediate_layer
  provenance.origin.source_uuid: eu-west-compliance-layer-uuid
```

**Policy Evaluation:**

```yaml
# GateKeeper policy: vm-size-limits evaluates
# Result: APPROVED (4 CPU within AppTeam's 16 CPU limit)

# Transformation policy: inject-monitoring evaluates
# Result: monitoring_endpoint field injected
monitoring_endpoint:
  value: "https://metrics.internal.eu-west.example.com"
  provenance.modifications:
    - sequence: 1
      previous_value: null
      modified_value: "https://metrics.internal.eu-west.example.com"
      source_type: policy
      source_uuid: inject-monitoring-policy-uuid
      operation_type: enrichment
      reason: "Standard monitoring endpoint for EU-WEST production resources"

# GateKeeper policy: approved-os-images evaluates (AppTeam's tenant policy)
# Result: APPROVED (rhel is in AppTeam's approved images list)
```

**Placement selects provider (substrate vocabulary):**
- Sovereignty pre-filter: eligible providers must satisfy `data_residency: EU-WEST`
- Reserve query to 3 eligible OpenStack instances
- EU-WEST-Prod-1 responds: capacity available, confidence 94
- EU-WEST-Prod-2 responds: capacity available, confidence 87
- EU-WEST-Prod-3: insufficient capacity
- Tie-breaking: EU-WEST-Prod-1 selected (highest confidence score)

**Requested State committed:**

```yaml
# requested-store/a1b2c3d4-tenant/Compute/VirtualMachine/f5e6d7c8-entity/requested.yaml

apiVersion: udlm.io/v1
kind: RequestedState
metadata:
  entity_uuid: f5e6d7c8-e9f0-a1b2-c3d4-e5f6a7b8c9d0
  resource_type: Compute.VirtualMachine
  tenant_uuid: a1b2c3d4-e5f6-a7b8-c9d0-e1f2a3b4c5d6
  assembled_at: 2026-03-15T09:00:47Z
  intent_state_ref: f5e6d7c8-intent-ref-uuid

spec:
  cpu_count: { value: 4, provenance: {...} }
  memory_gb: { value: 8, provenance: {...} }
  storage_gb: { value: 100, provenance: {...} }
  os_family: { value: rhel, provenance: {...} }
  environment: { value: production, provenance: {...} }
  name: { value: "payments-api-server-01", provenance: {...} }
  data_center: { value: "EU-WEST-DC1", provenance: {...} }
  monitoring_agent: { value: "datadog-agent:7.42", provenance: {...} }
  backup_policy: { value: "daily-30d-eu-west", provenance: {...} }
  monitoring_endpoint: { value: "https://metrics...", provenance: {...} }

placement:
  selected_provider_uuid: eu-west-prod-1-provider-uuid
  placement_reason: "highest confidence score among eligible providers"
  sovereignty_satisfied: true
  reserve_query_response_ref: <uuid>
```

### 3.3 Provider Realizes the Resource (Realized State)

OpenStack EU-WEST-Prod-1 receives the payload, naturalizes it to OpenStack format, provisions the VM, and returns the denaturalized result:

```yaml
# Event written to Realized Store event stream (entity_uuid key)

event_type: REALIZED
entity_uuid: f5e6d7c8-e9f0-a1b2-c3d4-e5f6a7b8c9d0
realized_at: 2026-03-15T09:03:12Z
provider_uuid: eu-west-prod-1-provider-uuid

# UDLM unified fields
cpu_count: { value: 4, provenance: { ...plus provider attribution } }
memory_gb: { value: 8, provenance: {...} }
storage_gb: { value: 100, provenance: {...} }

# Provider-added fields (not in Requested State — added by provider after realization)
provider_entity_id: "vm-0a1b2c3d"              # OpenStack's internal VM ID
assigned_ip_address: "10.1.45.23"              # IP assigned by provider at realization
hypervisor_host: "compute-node-07.eu-west"      # where the VM was physically placed
actual_storage_gb: 102                          # actual allocated (rounded up)
console_url: "https://console.eu-west.example.com/vm/0a1b2c3d"
```

### 3.4 Discovery Cycle (Discovered State)

24 hours after realization, the discovery cycle runs:

```yaml
# Snapshot written to Discovered Store

snapshot_type: DISCOVERED
entity_uuid: f5e6d7c8-e9f0-a1b2-c3d4-e5f6a7b8c9d0
discovered_at: 2026-03-16T09:00:00Z
discovery_method: openstack_api_query
provider_uuid: eu-west-prod-1-provider-uuid

cpu_count: 4          # matches Realized State — no drift
memory_gb: 8          # matches
storage_gb: 102       # matches (actual_storage_gb from provider)
provider_entity_id: "vm-0a1b2c3d"
status: ACTIVE
```

Drift Detection runs field-by-field comparison: all fields match Realized State. No drift event generated.

---

## 4. Example 2 — IP Address Allocation

An allocation request showing the `allocation` ownership model (pool → owned allocation).

```yaml
# Consumer submits intent for an IP address
# intent-store/a1b2c3d4-tenant/Network/IPAddress/ip-entity-uuid/intent.yaml

spec:
  requested_from: network                   # request from the network pool
  address_family: IPv4
  purpose: vm_interface
  attachment_ref: f5e6d7c8-entity-uuid     # the VM this IP will be assigned to

# Assembly runs — placement finds eligible IPAddressPool
# Pool: NetworkOps/Network/IPAddressPool/10.1.0.0-16 (owned by NetworkOps Tenant)
# Available capacity: 65420 addresses

# Provider carves allocation:
# New entity created: IPAddress 10.1.45.23/32
# Owned by: AppTeam Tenant (a1b2c3d4)
# AllocationRecord relationship created:
#   IPAddress 10.1.45.23/32 --[allocated_from]--> IPAddressPool 10.1.0.0/16

# Realized State event for the new IPAddress entity:
entity_uuid: ip-entity-uuid
resource_type: Network.IPAddress
ownership_model: allocation
owned_by_tenant_uuid: a1b2c3d4-appteam-uuid    # AppTeam owns this
allocated_from_pool_uuid: pool-entity-uuid      # NetworkOps owns the pool
address: "10.1.45.23"
prefix_length: 32
address_family: IPv4
```

When AppTeam decommissions their VM, the IP address entity can also be decommissioned. The pool's available capacity increases by 1. NetworkOps Tenant is unaffected.

---

## 5. Example 3 — VLAN Attachment (Shareable)

A VM attaches to an existing VLAN — the `shareable` ownership model (stake, not ownership).

```yaml
# VLAN-100 exists — owned by NetworkOps Tenant
# entity_uuid: vlan-100-entity-uuid
# ownership_model: shareable

# Consumer (AppTeam) requests VM attachment to VLAN-100
# No new VLAN entity is created — a stake relationship is established:

relationship:
  type: attached_to
  source_entity_uuid: f5e6d7c8-vm-entity-uuid   # AppTeam's VM
  target_entity_uuid: vlan-100-entity-uuid        # NetworkOps's VLAN
  source_tenant_uuid: a1b2c3d4-appteam-uuid
  target_tenant_uuid: netops-tenant-uuid
  stake:
    is_active: true
    stake_strength: required                       # VM cannot function without VLAN
    staked_at: 2026-03-15T09:03:12Z

# If NetworkOps tries to decommission VLAN-100:
# active required stakes: 3 (VM-A, VM-B, VM-C all have required stakes)
# Result: DECOMMISSION_DEFERRED
# NetworkOps notified: "VLAN-100 has 3 required stakeholders. Decommission deferred."
# Each stakeholder (AppTeam, DevTeam, OpsTeam) notified:
# "NetworkOps has requested decommission of VLAN-100. Please migrate your workloads."
```

---

## 6. Example 4 — Brownfield Ingestion

A VM discovered by the provider that the realization did not provision is brought under UDLM lifecycle management.

```yaml
# Step 1: INGEST — discovery finds unknown VM
discovered_entity:
  provider_entity_id: "vm-legacy-0001"
  resource_type: Compute.VirtualMachine
  lifecycle_state: OPERATIONAL          # it's running
  discovered_at: 2026-03-15T06:00:00Z
  discovery_confidence: low             # no UDLM provenance
  transitional_tenant: __transitional__ # held in transitional Tenant during ingestion

# Step 2: ENRICH — CMDB Information Provider enriches the entity
# CMDB lookup by IP address finds the business owner record:
enrichment:
  owner_business_unit: "Payments Platform"
  cost_center: "PAYM-4421"
  product_owner: "Jane Smith"
  compliance_scope: PCI-DSS
  confidence_descriptor:
    authority_level: primary            # CMDB is primary authority for ownership data
    corroboration: single_source        # only CMDB has this data
    source_trust: verified

# Step 3: PROMOTE — operator assigns to AppTeam Tenant, creates entity record
promotion:
  target_tenant_uuid: a1b2c3d4-appteam-uuid
  created_via: ingestion
  intent_state_created: true            # Intent State created from discovered configuration
  provenance_basis: discovered          # provenance chain starts from discovery
  promoted_by: operator-actor-uuid
  promoted_at: 2026-03-15T11:30:00Z
```

After promotion, the entity is a full lifecycle-managed entity. Drift detection is active. The operator can now request updates (targeted delta) or decommission through the substrate.

---

## 7. Example 5 — Drift Detection and Remediation

Six hours after the VM from Example 1 was realized, discovery finds a discrepancy:

```yaml
# Discovery finds:
cpu_count: 4       # matches
memory_gb: 16      # DRIFT — realized says 8, discovered says 16

# Drift record created:
drift_record:
  entity_uuid: f5e6d7c8-entity-uuid
  detected_at: 2026-03-15T15:00:00Z
  drifted_fields:
    - field_path: memory_gb
      realized_value: 8
      discovered_value: 16
  drift_severity: significant      # memory doubling is significant
  unsanctioned: true               # no Requested State explains this change
```

**Policy Engine evaluates the drift record:**

```yaml
# Drift response policy for Compute.VirtualMachine at significant severity:
# action: ESCALATE for unsanctioned changes

escalation:
  entity_uuid: f5e6d7c8-entity-uuid
  notified:
    - actor: b2c3d4e5-consumer-actor   # the entity owner
    - actor: appteam-admin-actor        # AppTeam admin
    - actor: sre-oncall-actor           # SRE on-call
  escalation_reason: "Unsanctioned memory change: 8Gi → 16Gi"
  resolution_options:
    - REVERT: "Submit rehydration from Realized State to restore 8Gi memory"
    - UPDATE_DEFINITION: "Promote discovered state — update entity definition to 16Gi"
    - ACCEPT: "Accept the change; add to next review cycle"
```

The consumer reviews and chooses UPDATE_DEFINITION — the memory was legitimately increased by the infrastructure team for a critical workload. They submit an UPDATE_DEFINITION resolution, which creates a new Requested State reflecting 16Gi memory and updates the Realized State record. Future drift detection will compare against 16Gi.

---

*UDLM substrate document. Realization-specific orchestration scenarios (e.g., composite three-tier application flows, retry-driven recovery scenarios, scoring-driven placement walkthroughs) live in the consuming realization's `orchestration-scenarios` documentation.*
