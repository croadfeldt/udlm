# DCM Data Model — Worked Examples


**Document Status:** ✅ Complete
**Document Type:** Reference Examples

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA + PROVIDER + POLICY**
>
> Worked examples showing all three abstractions in operation


**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Four States](02-four-states.md) | [Entity Types](01-entity-types.md) | [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md) | [Layering and Versioning](03-layering-and-versioning.md)

---

## 1. Purpose

This document provides end-to-end worked examples that make the DCM data model concrete. Each example traces the complete lifecycle of a resource through DCM — from consumer intent through the four states, showing exactly what data exists at each stage.

These examples also resolve outstanding implementation details deferred from other documents, specifically the Git repository structure for the Intent and Requested stores.

---

## 2. Git Repository Structure (Optional Ingress Adapter)

> **Note:** Git is an optional ingress adapter, not a required state store. All four data domains (Intent, Requested, Realized, Discovered) are stored in DCM's PostgreSQL database. These Git layouts apply only when teams choose to use Git/PR-based workflows for submitting intent. See [51-infrastructure-optimization.md](51-infrastructure-optimization.md) for the prescribed infrastructure model.

This resolves the deferred Q54 item from the Four States document (Section 4.1).

The Intent store uses a handle-based directory structure within Git when Git ingress is enabled. Tenant isolation is enforced at the directory level. Provider selection (the Q54 concern) is recorded in the assembled payload, not in the directory structure — so the directory structure is independent of which provider was selected.

### 2.1 Intent Store Layout

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

**Branch naming:** `intent/{tenant-uuid}/{entity-uuid}` for new requests. `intent/{tenant-uuid}/{entity-uuid}/v{n}` for revisions.

**Merge to main:** Triggers the CD pipeline — Request Payload Processor begins assembly.

### 2.2 Requested Store Layout

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

### 2.3 Layer and Policy Store Layout

**Core layers** are the organization's authoritative declarations — they define what the organization intends, not what providers report. For example, `datacenter-layer.yaml` declares the properties of datacenter `dc-us-east-1` (location, sovereignty zone, available VLANs). Providers are validated against these declarations. The Discovery Service detects drift when provider-reported state diverges from declared layers. Layers are not synced *from* providers — providers are measured *against* them.

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

apiVersion: dcm.io/v1
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

**CI pipeline runs immediately:**
- Policy pre-validation: no GateKeeper violations detected (4 CPU is within AppTeam's quota)
- Cost estimation: ~$0.32/hour based on current provider rates
- Dependency check: no dependencies declared — clean
- Sovereignty check: AppTeam's Tenant has `data_residency: EU-WEST` — placement must honor this
- Authorization check: actor b2c3d4e5 has `request:compute:vm` permission in AppTeam Tenant
- Auto-approve evaluation: meets all auto-approve criteria → PR auto-merged

### 3.2 Assembly Produces Requested State

After intent merge, the Request Payload Processor runs the nine-step assembly:

**Step 3 — Layer Resolution and Merge:**

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

**Step 5-7 — Policy Evaluation:**

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

**Step 6 — Placement Engine selects provider:**
- Sovereignty pre-filter: eligible providers must satisfy `data_residency: EU-WEST`
- Reserve query to 3 eligible OpenStack instances
- EU-WEST-Prod-1 responds: capacity available, confidence 94
- EU-WEST-Prod-2 responds: capacity available, confidence 87
- EU-WEST-Prod-3: insufficient capacity
- Tie-breaking: EU-WEST-Prod-1 selected (highest confidence score)

**Requested State committed:**

```yaml
# requested-store/a1b2c3d4-tenant/Compute/VirtualMachine/f5e6d7c8-entity/requested.yaml

apiVersion: dcm.io/v1
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

# DCM unified fields
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

# Assembly runs — placement engine finds eligible IPAddressPool
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

A VM discovered by the provider that DCM did not provision is brought under DCM lifecycle management.

```yaml
# Step 1: INGEST — discovery finds unknown VM
discovered_entity:
  provider_entity_id: "vm-legacy-0001"
  resource_type: Compute.VirtualMachine
  lifecycle_state: OPERATIONAL          # it's running
  discovered_at: 2026-03-15T06:00:00Z
  discovery_confidence: low             # no DCM provenance
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

After promotion, the entity is a full DCM-managed entity. Drift detection is active. The operator can now request updates (targeted delta) or decommission through DCM.

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
  unsanctioned: true               # no DCM Requested State explains this change
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

## 8. Example 6 — Three-Tier Application (Meta Provider with Binding Fields)

This example shows how a compound service request flows through the dependency graph, with runtime values from one resource injected into dependent resources via `binding_fields`.

### 8.1 Consumer Request

A consumer requests a "Web Application — Standard" from the catalog. This is a single catalog item backed by a Meta Provider that composes three resources:

```yaml
# Consumer submits via API
POST /api/v1/requests
{
  "catalog_item_uuid": "webapp-standard-uuid",
  "fields": {
    "app_name": "pet-clinic",
    "environment": "staging",
    "db_engine": "postgresql",
    "db_storage_gb": 50,
    "web_replicas": 2
  }
}
```

### 8.2 Resource Type Spec — WebApp.ThreeTier

The Meta Provider's resource type spec declares three constituent resources and the binding fields that connect them:

```yaml
resource_type: WebApp.ThreeTier
entity_type: composite_resource
constituents:
  - name: database
    resource_type: Database.PostgreSQL
    required: true
    fields_from_parent:
      - source: "db_engine"
        target: "engine"
      - source: "db_storage_gb"
        target: "storage_gb"
      - source: "environment"
        target: "environment"

  - name: backend
    resource_type: Compute.VirtualMachine
    required: true
    depends_on: [database]
    binding_fields:
      - source: "database.ip_address"      # ← from realized Database
        target: "backend.config.db_host"   # ← injected into Backend payload
      - source: "database.port"
        target: "backend.config.db_port"
      - source: "database.credentials_ref"
        target: "backend.config.db_credentials_ref"
    fields_from_parent:
      - source: "app_name"
        target: "hostname_prefix"
      - source: "environment"
        target: "environment"

  - name: frontend
    resource_type: Compute.VirtualMachine
    required: true
    depends_on: [backend]
    binding_fields:
      - source: "backend.ip_address"       # ← from realized Backend
        target: "frontend.config.api_host" # ← injected into Frontend payload
      - source: "backend.port"
        target: "frontend.config.api_port"
    fields_from_parent:
      - source: "app_name"
        target: "hostname_prefix"
      - source: "web_replicas"
        target: "replicas"
      - source: "environment"
        target: "environment"

lifecycle_policy:
  on_constituent_failure: rollback_all    # If any constituent fails, decommission all
```

### 8.3 Pipeline Execution

```
1. Intent captured — consumer's request stored in intent_records

2. Request Processor assembles the composite payload
   → Resolves WebApp.ThreeTier resource type spec
   → Identifies 3 constituent resources with dependency graph:
     Database (no deps) → Backend (depends on Database) → Frontend (depends on Backend)

3. Policy Engine evaluates the composite request
   → GateKeeper: staging environment authorized for this tenant
   → Validation: db_storage_gb within tier limits
   → Transformation: injects monitoring agent config into all 3 constituents

4. Placement Engine selects providers for each constituent
   → Database → dcm-provider-database (scored highest for PostgreSQL in staging zone)
   → Backend → dcm-provider-vm (KubeVirt provider)
   → Frontend → dcm-provider-vm (same provider, same zone)

5. Request Orchestrator dispatches in dependency order:

   Step 5a: Dispatch Database to dcm-provider-database
   → Provider realizes PostgreSQL instance
   → Callbacks: ip_address: 10.0.1.50, port: 5432, credentials_ref: vault:secret/pet-clinic-db

   Step 5b: Request Processor resolves binding_fields for Backend
   → Injects: config.db_host = 10.0.1.50 (from Database.ip_address)
   → Injects: config.db_port = 5432 (from Database.port)
   → Injects: config.db_credentials_ref = vault:secret/pet-clinic-db
   → Dispatch Backend to dcm-provider-vm
   → Provider realizes VM with application config containing DB connection
   → Callbacks: ip_address: 10.0.2.30, port: 8080

   Step 5c: Request Processor resolves binding_fields for Frontend
   → Injects: config.api_host = 10.0.2.30 (from Backend.ip_address)
   → Injects: config.api_port = 8080 (from Backend.port)
   → Dispatch Frontend to dcm-provider-vm
   → Provider realizes 2 VM replicas with backend endpoint configured
   → Callbacks: ip_addresses: [10.0.3.10, 10.0.3.11], port: 443

6. All constituents realized — composite entity status: OPERATIONAL
   → Audit records written for all 4 entities (composite + 3 constituents)
   → Consumer sees single "pet-clinic" application in their resource list
```

### 8.4 What the Consumer Sees

The consumer requested one catalog item and sees one composite resource. The three constituent resources are visible as children:

```
pet-clinic (WebApp.ThreeTier) — OPERATIONAL
├── pet-clinic-db (Database.PostgreSQL) — OPERATIONAL
│   ip_address: 10.0.1.50
├── pet-clinic-backend (Compute.VirtualMachine) — OPERATIONAL
│   ip_address: 10.0.2.30, config.db_host: 10.0.1.50
└── pet-clinic-frontend (Compute.VirtualMachine × 2) — OPERATIONAL
    ip_addresses: [10.0.3.10, 10.0.3.11], config.api_host: 10.0.2.30
```

If the database is decommissioned, the `lifecycle_policy: rollback_all` cascades to backend and frontend. If the consumer requests a tier upgrade, the Meta Provider coordinates the upgrade across all three constituents, maintaining the binding field connections throughout.

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
