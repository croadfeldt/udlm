# UDLM — Ingestion Model

**Document Status:** ✅ Stable — UDLM substrate contract
**Related Documents:** [Context and Purpose](../foundations/context-and-purpose.md) | [Four States](../foundations/four-states.md) | [Resource/Service Entities](../entities/resource-service-entities.md) | [Entity Relationships](../entities/entity-relationships.md) | [Resource Grouping](../entities/resource-grouping.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM substrate.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](../foundations/foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: DATA + PROVIDER**
>
> Data: ingestion state artifacts. Provider: discovery provider invocation.

---

## 1. Purpose

The UDLM Ingestion Model is the **unified substrate contract for bringing entities that exist outside lifecycle control into governance**. It applies to multiple distinct sources:

- **Brownfield Discovery** — entities discovered by a Service Provider that already exist in the infrastructure but are unknown to the realization
- **Manual Import** — entities imported from external systems (CMDBs, spreadsheets, legacy records) during onboarding
- **Legacy Import** — entities migrated from a prior incompatible system

All sources follow the same pattern: ingest, enrich, and promote. The same data structures, the same governance policies, the same audit trail, and the same transitional holding mechanism apply regardless of source.

**The three-step pattern:**

```
1. INGEST   — bring the entity into the substrate with whatever identity and metadata is available
2. ENRICH   — associate business data, ownership, Tenant assignment, and relationships
3. PROMOTE  — transition from holding state to full lifecycle ownership
```

---

## 2. Design Principles

**Unified model — minimum variance.** All ingestion sources are the same fundamental operation. One model, one audit record structure, one set of governance policies.

**Non-blocking.** Entities that cannot be immediately assigned a Tenant do not block migration or discovery. They land in the `__transitional__` Tenant and are resolved progressively. Migration does not require every entity to be assigned before any entity can proceed.

**Provenance transparency.** Ingested entities are honest about their provenance depth. `created_via: migration` or `created_via: discovery` on the artifact metadata signals that the chain has limited depth. The ingestion record carries the confidence level.

**Promotion gates governance.** An entity in a holding state cannot be the parent of a new allocated resource claim, cannot be used as a hard dependency by new requests, and cannot receive new operational relationships until promoted. Informational relationships are permitted — entities can be referenced during enrichment.

**Audit completeness.** Every ingested entity carries an `ingestion_record` in its provenance. Every Tenant assignment, enrichment action, and promotion event is recorded with actor, timestamp, and reason.

---

## 3. Ingestion Lifecycle States

Entities going through ingestion follow a distinct mini-lifecycle before entering the standard entity lifecycle:

```
INGESTED
  │  Entity exists in the substrate. Minimal metadata. Tenant may be __transitional__.
  │  Action: enrich — add business data, assign relationships, assign real Tenant
  ▼
ENRICHING
  │  Tenant assigned. Metadata being completed. Relationships being established.
  │  Action: complete enrichment, satisfy governance requirements
  ▼
PROMOTED
  │  All required fields present. Governance satisfied. Full lifecycle assumed.
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

The `__transitional__` Tenant is a substrate-required system artifact — a system-managed holding area for entities that have been ingested but not yet assigned to a real Tenant. Any UDLM-conformant realization MUST provide this Tenant.

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
      display_name: "Ingestion System"
    created_via: system
    status: active
```

**Substrate-required properties:**
- Cannot be deleted
- Cannot be renamed
- Cannot be used for new resource provisioning — only ingestion assignment
- Entities in `__transitional__` are fully auditable and visible
- Governance policy enforces maximum residency and escalation

---

## 5. The Ingestion Record

Every ingested entity carries an `ingestion_record` in its provenance chain. This is the audit record of how the entity entered the substrate. The wire shape is normative:

```yaml
ingestion_record:
  ingestion_uuid: <uuid>
  resource_entity_uuid: <uuid>
  ingestion_timestamp: <ISO 8601>

  ingestion_source: <legacy_import | brownfield_discovery | manual_import>

  # Legacy ingestion fields (when ingestion_source: legacy_import)
  legacy_identifier: <original identifier — name, IP, hostname, or prior-system UUID>
  legacy_metadata_snapshot: <key legacy fields captured at migration time>

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
    display_name: <person name or "Ingestion System">
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

## 6. Auto-Assignment Signals (Substrate Contract)

When an entity is ingested, the realization attempts auto-assignment to a real Tenant using the following signal taxonomy (closed substrate vocabulary):

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

The **priority order** in which signals are evaluated is a realization configuration choice (declared in a platform-domain layer), but the substrate requires:
- `explicit_tenant_tag` MUST always have highest priority when present.
- `default_tenant` MUST always have lowest priority.
- Middle signals MAY be reordered per realization or deployment.

---

## 8. Brownfield Ingestion

### 8.1 Overview

Brownfield ingestion brings infrastructure that already exists in the real world — but is unknown to the substrate — under lifecycle management. The source is the **Discovered State**: a Service Provider interrogates existing infrastructure and creates Discovered State records for everything it finds.

This is the "greening the brownfield" use case — taking an unmanaged estate and progressively bringing it under governance without requiring a big-bang cutover.

### 8.2 Brownfield Flow

```
Service Provider performs discovery scan
  │  Interrogates existing infrastructure
  │  Creates Discovered State records for all found entities
  │
  ▼  The realization identifies "unmanaged" discovered entities
  │  Discovered State records with no matching Realized State = unmanaged
  │  These are brownfield candidates
  │
  ▼  Ingestion initiation
  │  Platform admin or automated policy initiates ingestion
  │  The realization creates entity stubs with:
  │    - New UUID (realization-assigned)
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
  │  The realization assumes lifecycle ownership:
  │    - Discovered State record becomes the initial Realized State
  │    - Entity enters standard lifecycle (OPERATIONAL)
  │    - Drift detection active from this point forward
  │
  ▼  OPERATIONAL
     The realization now manages the full lifecycle of this previously unmanaged entity
```

### 8.3 Discovered → Realized Promotion Contract

When a brownfield entity is promoted, its Discovered State record is promoted to become the initial Realized State. This is the moment the realization assumes lifecycle authority. The wire shape of the promotion record is normative:

```yaml
realized_state_record:
  entity_uuid: <uuid>
  source: brownfield_promotion
  ingestion_uuid: <uuid — links to ingestion_record>
  discovered_state_uuid: <uuid — the Discovered State that seeded this>
  promoted_at: <ISO 8601>
  promoted_by:
    display_name: <actor>
  initial_realized_payload: <field values from discovery — unified format>
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
| Legacy import | Intent → Requested → (no Realized yet) | Legacy records treated as incomplete Requested State; migration creates minimal Realized State |
| Brownfield Discovery | Discovered → Realized | Discovered State is promoted to Realized State at promotion |
| Manual Import | None initially | Entity stub created; no prior state records; Realized State created at promotion from import data |

In all cases: once an entity reaches `PROMOTED`, it has a Realized State record and full Four States tracking begins.

---

## 10. UDLM System Policies — Full List

| Policy | Rule |
|--------|------|
| `ING-001` | Every entity ingested must be assigned to exactly one Tenant — either a real Tenant or `__transitional__` — before it is eligible for new requests. |
| `ING-002` | Entities in `INGESTED` or `ENRICHING` state may not be the parent resource for a new allocated resource claim. |
| `ING-003` | The `__transitional__` Tenant is system-managed — cannot be deleted, renamed, or used for new resource provisioning. |
| `ING-004` | Every ingested entity must carry an `ingestion_record` in its provenance chain. |
| `ING-005` | Entities in `__transitional__` beyond `max_residency_days` must trigger the configured escalation action. |
| `ING-006` | A brownfield entity may not be promoted to `PROMOTED` state without explicit actor authorization. |
| `ING-007` | At promotion, the Discovered State record must be promoted to Realized State — this is the moment the realization assumes lifecycle ownership. |
| `ING-012` | Ingestion signal priority order is declared in a platform domain layer and configurable per deployment. `explicit_tenant_tag` always has highest priority. `default_tenant` always has lowest priority. Middle signals are reorderable. |
| `ING-013` | Bulk entity promotion is supported with profile-governed maximum batch sizes and approval requirements. Preview required before confirmation. Rollback window applies. Single `BULK_PROMOTE` audit record with full member list. |
| `ING-014` | Maximum ingestion sources per entity is profile-governed. Exceeding the maximum triggers `warn` or `reject` per policy. |
| `ING-015` | Ingested entities may be associated with Resource Type Specifications and promoted to Service Catalog items. Drift detection operates bidirectionally between the ingested entity and its associated catalog item. |

---

## 11. Related Concepts

- **`__transitional__` Tenant** — system-managed holding Tenant for unassigned ingested entities
- **Ingestion Record** — provenance record carried by every ingested entity
- **Four States** — Discovered State is the entry point for brownfield ingestion; Realized State is the output of promotion
- **Brownfield** — existing infrastructure not yet under lifecycle management
- **Drift Detection** — begins for brownfield entities at the moment of promotion
- **Greening the Brownfield** — the progressive process of bringing unmanaged infrastructure under lifecycle control

---

*UDLM substrate document. Realization-specific ingestion engine implementation, Information Provider polling/webhook integration mechanics, enrichment policy enforcement code, auto-assignment execution, and ingestion scheduling live in the consuming realization's documentation.*
