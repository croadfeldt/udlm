# DCM Data Model — Ingestion Model


**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Four States](02-four-states.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Entity Relationships](09-entity-relationships.md) | [Resource Grouping](08-resource-grouping.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA + PROVIDER**
>
> Data: ingestion state artifacts. Provider: discovery provider invocation



---

## 1. Purpose

The DCM Ingestion Model is the **unified mechanism for bringing entities that exist outside DCM's lifecycle control into DCM's governance model**. It applies to three distinct sources:

- **Brownfield Discovery** — entities discovered by a Service Provider that already exist in the infrastructure but are unknown to DCM
- **Manual Import** — entities imported from external systems (CMDBs, spreadsheets, legacy records) during onboarding

All three sources follow the same pattern: ingest, enrich, and promote. The same data structures, the same governance policies, the same audit trail, and the same transitional holding mechanism apply regardless of source.

**The three-step pattern:**

```
1. INGEST   — bring the entity into DCM with whatever identity and metadata is available
2. ENRICH   — associate business data, ownership, Tenant assignment, and relationships
3. PROMOTE  — transition from holding state to full DCM lifecycle ownership
```

---

## 2. Design Principles

**Unified model — minimum variance.** brownfield ingestion and brownfield ingestion are the same fundamental operation. One model, one audit record structure, one set of governance policies.

**Non-blocking.** Entities that cannot be immediately assigned a Tenant do not block migration or discovery. They land in the `__transitional__` Tenant and are resolved progressively. Migration does not require every entity to be assigned before any entity can proceed.

**Provenance transparency.** Ingested entities are honest about their provenance depth. `created_via: migration` or `created_via: discovery` on the artifact metadata signals that the chain has limited depth. The ingestion record carries the confidence level.

**Promotion gates governance.** An entity in a holding state cannot be the parent of a new allocated resource claim, cannot be used as a hard dependency by new requests, and cannot receive new operational relationships until promoted. Informational relationships are permitted — entities can be referenced during enrichment.

**Audit completeness.** Every ingested entity carries an `ingestion_record` in its provenance. Every Tenant assignment, enrichment action, and promotion event is recorded with actor, timestamp, and reason.

---

## 3. Ingestion Lifecycle States

Entities going through ingestion follow a distinct mini-lifecycle before entering the standard entity lifecycle:

```
INGESTED
  │  Entity exists in DCM. Minimal metadata. Tenant may be __transitional__.
  │  Action: enrich — add business data, assign relationships, assign real Tenant
  ▼
ENRICHING
  │  Tenant assigned. Metadata being completed. Relationships being established.
  │  Action: complete enrichment, satisfy governance requirements
  ▼
PROMOTED
  │  All required fields present. Governance satisfied. Full DCM lifecycle assumed.
  ▼
OPERATIONAL  (standard entity lifecycle from here)
```

### 3.1 State Behavior

| State | Tenant | New Requests Can Use? | Parent for Allocations? | New Relationships? |
|-------|--------|----------------------|------------------------|-------------------|
| `INGESTED` | `__transitional__` or assigned | No | No | Informational only |
| `ENRICHING` | Assigned | No | No | Operational (read-only) |
| `PROMOTED` | Assigned | Yes | Yes | All types |
| `OPERATIONAL` | Assigned | Yes | Yes | All types |

### 3.2 Promotion Requirements

Before an entity can be promoted, the following must be satisfied:

- Assigned to a real Tenant (not `__transitional__`)
- All `universal` fields on the Resource Type Specification are populated
- All `constituent` relationships declared on the Resource Type Specification are resolved
- At least one actor has reviewed and authorized the promotion
- `ingestion_record.enrichment_status` is `complete`

---

## 4. The `__transitional__` Tenant

The `__transitional__` Tenant is a DCM System artifact — a system-managed holding area for entities that have been ingested but not yet assigned to a real Tenant.

```yaml
tenant:
  uuid: <system-assigned — stable across deployments>
  handle: "__transitional__"
  type: system_managed
  purpose: ingestion_holding
  governance:
    max_residency_days: 90          # configurable per deployment
    on_max_residency: escalate      # escalate | block | alert
    escalation_endpoint: <notification endpoint — platform admin>
  hard_tenancy:
    cross_tenant_relationships: operational_only
  artifact_metadata:
    created_by:
      display_name: "DCM Ingestion System"
    created_via: system
    status: active
```

**Properties:**
- Cannot be deleted
- Cannot be renamed
- Cannot be used for new resource provisioning — only ingestion assignment
- Entities in `__transitional__` are fully auditable and visible in DCM
- Governance policy enforces maximum residency and escalation

---

## 5. The Ingestion Record

Every ingested entity carries an `ingestion_record` in its provenance chain. This is the audit record of how the entity entered DCM.

```yaml
ingestion_record:
  ingestion_uuid: <uuid>
  resource_entity_uuid: <uuid>
  ingestion_timestamp: <ISO 8601>

  ingestion_source: <legacy_import | brownfield_discovery | manual_import>

  # brownfield ingestion fields (when ingestion_source: legacy_import)
  legacy_identifier: <original V1 identifier — name, IP, hostname, or DCM V1 UUID>
  legacy_metadata_snapshot: <key V1 fields captured at migration time>

  # Brownfield discovery fields (when ingestion_source: brownfield_discovery)
  discovered_state_uuid: <uuid of Discovered State record>
  discovery_provider_uuid: <uuid of provider that performed discovery>
  discovery_timestamp: <ISO 8601 — when the entity was first discovered>

  # Manual import fields (when ingestion_source: manual_import)
  import_source_system: <name of source system — e.g., "Legacy CMDB", "Spreadsheet">
  import_reference: <source system identifier>

  # Common fields
  assigned_tenant_uuid: <uuid — or null if still in __transitional__>
  assignment_method: <auto | manual | transitional>
  assignment_signal: >
    Human-readable description of what drove auto-assignment.
    e.g., "Resource group membership: payments-group → Payments Tenant"
    e.g., "Business unit metadata: BU-PAY → Payments Tenant"
    e.g., "No signal found — assigned to __transitional__"
  assigned_by:
    uuid: <actor UUID — optional>
    display_name: <person name or "DCM Ingestion System">
    timestamp: <ISO 8601>

  ingestion_confidence: <high | medium | low>
  # high:   strong unambiguous signal — auto-assignment reliable
  # medium: inferred from metadata — reasonable confidence, human review recommended
  # low:    orphaned or conflicting signals — assigned to __transitional__

  enrichment_status: <pending | partial | complete>
  enrichment_history:
    - sequence: 1
      action: <tenant_assigned | relationship_added | field_enriched | promoted>
      performed_by:
        display_name: <actor>
      timestamp: <ISO 8601>
      detail: <human-readable description>

  promoted_at: <ISO 8601 — populated when entity reaches PROMOTED state>
  promoted_by:
    display_name: <actor who authorized promotion>
```

---

## 6. Auto-Assignment Signals

When DCM ingests an entity, it attempts auto-assignment to a real Tenant using the following signals in priority order:

| Signal | Confidence | Description |
|--------|-----------|-------------|
| Explicit ownership metadata | High | Business unit, cost center, or team tag on the resource maps unambiguously to a Tenant |
| Resource group membership | High | Resource belongs to a group that maps to a known Tenant |
| Request history | High | Legacy record identifies the requesting team, which maps to a Tenant |
| Network / location context | Medium | Resource's location, VLAN, or network segment maps to a Tenant by convention |
| Naming convention | Medium | Resource name matches a known Tenant naming pattern |
| Provider context | Medium | Resource was provisioned by a known provider associated with a Tenant |
| No signal found | Low | No auto-assignment possible — entity goes to `__transitional__` |

Multiple signals can be combined. If signals conflict, the higher-confidence signal wins and the conflict is recorded in the ingestion record with `ingestion_confidence: medium` regardless of individual signal strengths.

---

## 8. Brownfield Ingestion

### 8.1 Overview

Brownfield ingestion brings infrastructure that already exists in the real world — but is unknown to DCM — under DCM lifecycle management. The source is the **Discovered State**: a Service Provider interrogates existing infrastructure and creates Discovered State records for everything it finds.

This is the "greening the brownfield" use case — taking an unmanaged estate and progressively bringing it under DCM governance without requiring a big-bang cutover.

### 8.2 Brownfield Flow

```
Service Provider performs discovery scan
  │  Interrogates existing infrastructure
  │  Creates Discovered State records for all found entities
  │
  ▼  DCM identifies "unmanaged" discovered entities
  │  Discovered State records with no matching Realized State = unmanaged
  │  These are brownfield candidates
  │
  ▼  Ingestion initiation
  │  Platform admin or automated policy initiates ingestion
  │  DCM creates entity stubs with:
  │    - New UUID (DCM-assigned)
  │    - ingestion_source: brownfield_discovery
  │    - State: INGESTED
  │    - Tenant: __transitional__ (pending enrichment)
  │    - ingestion_record linking to Discovered State UUID
  │
  ▼  Enrichment
  │  Business data associated (owner, cost center, purpose)
  │  Tenant assigned based on auto-assignment signals
  │  Relationships established to other entities
  │  Missing fields populated from discovery data
  │
  ▼  Promotion
  │  Review and authorization by responsible actor
  │  State: ENRICHING → PROMOTED
  │  DCM assumes lifecycle ownership:
  │    - Discovered State record becomes the initial Realized State
  │    - Entity enters standard DCM lifecycle (OPERATIONAL)
  │    - Drift detection active from this point forward
  │
  ▼  OPERATIONAL
     DCM now manages the full lifecycle of this previously unmanaged entity
```

### 8.3 Discovered → Realized Promotion

When a brownfield entity is promoted, its Discovered State record is promoted to become the initial Realized State. This is the moment DCM assumes lifecycle authority:

```yaml
realized_state_record:
  entity_uuid: <uuid>
  source: brownfield_promotion
  ingestion_uuid: <uuid — links to ingestion_record>
  discovered_state_uuid: <uuid — the Discovered State that seeded this>
  promoted_at: <ISO 8601>
  promoted_by:
    display_name: <actor>
  initial_realized_payload: <field values from discovery — DCM format>
  provenance:
    origin:
      source_type: brownfield_discovery
      source_uuid: <discovered_state_uuid>
      timestamp: <ISO 8601>
```

From this point, the standard drift detection cycle runs: future discoveries are compared against the Realized State and any deviations are flagged as drift.

---

## 9. Relationship to the Four States

Ingestion interacts with the Four States model as follows:

| Ingestion Source | States Involved | Flow |
|-----------------|----------------|------|
| brownfield ingestion | Intent → Requested → (no Realized yet) | Legacy records treated as incomplete Requested State; migration creates minimal Realized State |
| Brownfield Discovery | Discovered → Realized | Discovered State is promoted to Realized State at promotion |
| Manual Import | None initially | Entity stub created; no prior state records; Realized State created at promotion from import data |

In all cases: once an entity reaches `PROMOTED`, it has a Realized State record and full Four States tracking begins.

---

## 10. DCM System Policies — Full List

| Policy | Rule |
|--------|------|
| `ING-001` | Every entity ingested into DCM must be assigned to exactly one Tenant — either a real Tenant or `__transitional__` — before it is eligible for new requests |
| `ING-002` | Entities in `INGESTED` or `ENRICHING` state may not be the parent resource for a new allocated resource claim |
| `ING-003` | The `__transitional__` Tenant is system-managed — cannot be deleted, renamed, or used for new resource provisioning |
| `ING-004` | Every ingested entity must carry an `ingestion_record` in its provenance chain |
| `ING-005` | Entities in `__transitional__` beyond `max_residency_days` must trigger the configured escalation action |
| `ING-006` | A brownfield entity may not be promoted to `PROMOTED` state without explicit actor authorization |
| `ING-007` | At promotion, the Discovered State record must be promoted to Realized State — this is the moment DCM assumes lifecycle ownership |

---

## 11. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should the auto-assignment signal priority order be configurable per deployment? | Migration flexibility | ✅ Resolved — platform domain layer declares priority; explicit_tenant_tag fixed first; default_tenant fixed last; middle signals configurable (ING-012) |
| 2 | Can multiple entities be promoted in bulk? | Operational efficiency | ✅ Resolved — bulk promotion supported; profile-governed max batch sizes; preview required; PT24H rollback; BULK_PROMOTE audit (ING-013) |
| 3 | Should there be a maximum number of ingestion sources per entity? | Data integrity | ✅ Resolved — profile-governed max (5 standard/prod, 3 fsi/sovereign); warn or reject on exceed (ING-014) |
| 4 | How does ingestion interact with the Service Catalog? | Catalog model | ✅ Resolved — ingested entities promotable to catalog items; bidirectional drift detection (ING-015) |

---

## 12. Related Concepts

- **`__transitional__` Tenant** — system-managed holding Tenant for unassigned ingested entities
- **Ingestion Record** — provenance record carried by every ingested entity
- **Four States** — Discovered State is the entry point for brownfield ingestion; Realized State is the output of promotion
- **Brownfield** — existing infrastructure not yet under DCM lifecycle management
- **Drift Detection** — begins for brownfield entities at the moment of promotion
- **Greening the Brownfield** — the progressive process of bringing unmanaged infrastructure under DCM lifecycle control


## 8. Ingestion Gap Resolutions

### 8.1 Configurable Signal Priority Order (Q1)

The ingestion signal priority order is declared in a platform-domain layer and configurable per deployment. `explicit_tenant_tag` always has highest priority; `default_tenant` always has lowest. The middle signals may be reordered.

```yaml
layer:
  handle: "platform/ingestion/signal-priority"
  domain: platform
  fields:
    ingestion_signal_priority:
      - explicit_tenant_tag         # fixed: always first
      - provider_declared_tenant    # configurable order
      - network_segment_mapping     # configurable order
      - hardware_class_mapping      # configurable order
      - geographic_location         # configurable order
      - default_tenant              # fixed: always last
```

### 8.2 Bulk Entity Promotion (Q2)

Bulk promotion is supported with profile-governed limits and approval requirements.

```yaml
bulk_promotion_config:
  max_entities_per_bulk: 500        # configurable per profile
  requires_approval: true
  preview_required: true            # must review bulk preview before confirming
  rollback_window: PT24H
  audit_record: BULK_PROMOTE        # single audit event with full member list
```

| Profile | Max per Bulk | Approval Required |
|---------|-------------|-----------------|
| minimal | Unlimited | No |
| dev | 1000 | No |
| standard | 500 | Recommended |
| prod | 100 | Yes |
| fsi | 50 | Yes + dual approval |
| sovereign | 25 | Yes + dual approval |

### 8.3 Maximum Ingestion Sources per Entity (Q3)

Profile-governed maximum to encourage clear data ownership and manageable conflict resolution.

```yaml
ingestion_source_limits:
  max_sources_per_entity: 5         # default for standard/prod
  on_max_exceeded: <warn|reject>
  profile_defaults:
    minimal: unlimited
    dev: 10
    standard: 5
    prod: 5
    fsi: 3
    sovereign: 3
```

### 8.4 Ingestion to Service Catalog Promotion (Q4)

Ingested entities may be promoted to Service Catalog items — the pathway from brownfield discovery to catalog-driven management.

```
Ingested entity
  → Operator associates entity with Resource Type Specification
  → Fields validated against spec
  → Service Catalog item created from entity's configuration
  → Entity becomes template ("golden example") for this catalog item
  → Future requests use catalog item
  → Drift detection bidirectional:
      entity drifts from catalog item → drift event
      catalog item updated → entity flagged for review
```

### 8.5 System Policies — Ingestion Gaps

| Policy | Rule |
|--------|------|
| `ING-012` | Ingestion signal priority order is declared in a platform domain layer and configurable per deployment. explicit_tenant_tag always has highest priority. default_tenant always has lowest priority. Middle signals are reorderable. |
| `ING-013` | Bulk entity promotion is supported with profile-governed maximum batch sizes and approval requirements. Preview required before confirmation. Rollback window PT24H. Single BULK_PROMOTE audit record with full member list. |
| `ING-014` | Maximum ingestion sources per entity is profile-governed (default: 5 for standard/prod; 3 for fsi/sovereign). Exceeding the maximum triggers warn or reject per policy. |
| `ING-015` | Ingested entities may be associated with Resource Type Specifications and promoted to Service Catalog items. Drift detection operates bidirectionally between the ingested entity and its associated catalog item. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
