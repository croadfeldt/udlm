# DCM Data Model — Information Providers: Confidence Scoring, Authority, and Conflict Resolution


**Document Status:** ✅ Complete  
**Related Documents:** [Information Providers](10-information-providers.md) | [Policy Organization](14-policy-profiles.md) | [Universal Audit Model](16-universal-audit.md) | [DCM Federation](22-dcm-federation.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: PROVIDER**
>
> The Provider abstraction — Information Provider advanced capabilities



---

## 1. Purpose

This document extends the base Information Provider model with the advanced concepts required for enterprise-grade information governance: confidence scoring for all provider-supplied data, authority and priority declarations as layer-defined organizational knowledge, ingestion-time conflict detection with policy-driven resolution, write-back capabilities, schema versioning, the well-known Information Provider Registry, and air-gapped verification.

---

## 2. Confidence Scoring — The Hybrid Descriptor Model

### 2.1 Purpose and Design Goals

Every field value supplied by an Information Provider carries a confidence descriptor. DCM aggregates data from multiple external sources — CMDB, HR systems, IPAM, asset management, monitoring tools — each with different freshness, authority, and reliability. The confidence model answers: **how much should you trust this field value?**

Three goals drive the design:
- **Accuracy** — each dimension of confidence is independently meaningful and auditable
- **Reliability** — a derived numeric score enables mathematical composition for placement decisions and conflict resolution
- **Ease of use** — a derived band (very_high through very_low) is what humans and policies work with day to day

### 2.2 The Primary Data Model — Confidence Descriptor

The **confidence_descriptor** is the primary data model. The score and band are derived from it — not the other way around. This separation removes false precision: the score is explicitly a convenience derivation, not an independent measurement.

```yaml
field_confidence:
  # PRIMARY — stored; set at specific lifecycle points
  authority_level: primary          # set at provider registration from authority layer
  corroboration: single_source      # set at ingestion; updated on subsequent pushes
  source_trust: verified            # maintained by trust scoring system (INF-009)
  last_updated_at: <ISO 8601>       # set at each push event
  source_provider_uuid: <uuid>      # set at ingestion

  # DERIVED — computed on demand; never stored as primary
  freshness: high                   # computed: (now - last_updated_at) vs thresholds
  data_age_minutes: 87              # computed: now - last_updated_at
  score: 86                         # computed: from descriptor components
  band: high                        # computed: from score vs band thresholds
```

### 2.3 Who Sets Each Descriptor Field

| Field | Set By | When | How |
|-------|--------|------|-----|
| `authority_level` | Authority declaration layer | Provider registration | Organizational knowledge — static per field per provider |
| `corroboration` | DCM ingestion pipeline | Each push event | Compared against existing values from other providers |
| `source_trust` | DCM trust scoring system | Event-triggered + weekly | Push failures, schema errors, health check, re-verification |
| `last_updated_at` | DCM ingestion pipeline | Each push event | Timestamp of the push event |
| `freshness` | DCM — derived | Query time | Computed from `now - last_updated_at` vs thresholds |
| `score` | DCM — derived | Query time | Computed from descriptor components |
| `band` | DCM — derived | Query time | Computed from score vs band thresholds |

**DCM computes all derived values — providers never self-declare confidence.**

### 2.4 Descriptor Component Values

**`authority_level`** — from the authority declaration layer:

| Value | Meaning |
|-------|---------|
| `primary` | Declared primary authoritative source for this field |
| `secondary` | Corroborating source; used if primary unavailable |
| `advisory` | Context only; never used for decisions |
| `discovered` | Value found via active interrogation |
| `self_reported` | Entity reported its own value |
| `inferred` | Value inferred from other data |

**`corroboration`** — computed at ingestion time:

| Value | Condition | Confidence Effect |
|-------|-----------|-----------------|
| `confirmed` | 2+ providers agree on this value | Increases confidence |
| `single_source` | Only one provider has asserted this value | Neutral |
| `contested` | 2+ providers disagree on this value | Reduces confidence |

**`source_trust`** — maintained by trust scoring system:

| Value | Condition | Confidence Effect |
|-------|-----------|-----------------|
| `verified` | Provider identity, sovereignty, certs all current | Full confidence |
| `degraded` | Provider has elevated error/conflict rate | Reduced confidence |
| `suspended` | Provider below trust threshold; pushes stopped | No new data |

**`freshness`** — computed from `data_age_minutes`:

| Value | Age Threshold |
|-------|-------------|
| `high` | < 1 hour |
| `medium` | 1 hour – 1 day |
| `low` | 1 day – 7 days |
| `stale` | > 7 days |

### 2.5 The Score Derivation Formula

The score is a convenience number derived deterministically from the descriptor. It enables mathematical composition (cross-DCM scoring, conflict resolution ordering) where a single number is needed.

```
score = min(100, base(authority_level)
              × freshness_multiplier(freshness)
              × corroboration_multiplier(corroboration)
              × trust_multiplier(source_trust))
```

**Base values by authority_level:**

| authority_level | Base Score |
|----------------|-----------|
| `primary` | 90 |
| `secondary` | 70 |
| `discovered` | 60 |
| `advisory` | 50 |
| `self_reported` | 40 |
| `inferred` | 30 |

**Freshness multipliers:**

| freshness | Multiplier |
|-----------|-----------|
| `high` | 1.00 |
| `medium` | 0.95 |
| `low` | 0.85 |
| `stale` | 0.50 |

**Corroboration multipliers:**

| corroboration | Multiplier |
|--------------|-----------|
| `confirmed` | 1.15 |
| `single_source` | 1.00 |
| `contested` | 0.60 |

**Trust multipliers:**

| source_trust | Multiplier |
|-------------|-----------|
| `verified` | 1.00 |
| `degraded` | 0.75 |
| `suspended` | 0.00 |

**Example:** Primary authority, fresh data (30 min old), single source, verified:
`min(100, 90 × 1.00 × 1.00 × 1.00)` = **90**

**Example:** Primary authority, medium freshness (4 hours), two sources agree, verified:
`min(100, 90 × 0.95 × 1.15 × 1.00)` = 98.3 → **98**

**Example:** Secondary authority, stale data (10 days), contested, degraded:
`min(100, 70 × 0.50 × 0.60 × 0.75)` = 15.75 → **16**

### 2.6 Score Bands — For Policy Use

Policies use bands, not raw scores. This avoids the brittleness of threshold values like "reject if score < 73":

| Band | Score Range | Policy Label |
|------|------------|-------------|
| Very High | 81-100 | `very_high` |
| High | 61-80 | `high` |
| Medium | 41-60 | `medium` |
| Low | 21-40 | `low` |
| Very Low | 0-20 | `very_low` |

```yaml
# Policy using band — clear and maintainable
policy:
  type: gatekeeper
  rule: >
    If field.owner_business_unit.band IN [very_low, low]
    THEN gatekeep: "Business unit confidence insufficient — manual verification required"

# Policy using individual descriptor dimensions — most precise
policy:
  type: gatekeeper
  rule: >
    If field.cost_center.corroboration == contested
    THEN gatekeep: "Cost center is contested between providers — resolve before provisioning"

# Policy using score — for mathematical thresholds
policy:
  type: gatekeeper
  rule: >
    If field.cost_center.score < 60
    THEN gatekeep: "Cost center confidence below required threshold"
```

### 2.7 Derivation Chain Summary

```
STORED (authoritative):
  authority_level + corroboration + source_trust + last_updated_at

DERIVED AT QUERY TIME (deterministic from stored):
  freshness ← (now - last_updated_at) vs thresholds
  score     ← base(authority_level) × freshness_mult × corroboration_mult × trust_mult
  band      ← score vs band thresholds

AUDIT RECORD (what auditors can reconstruct from):
  authority_level (from registration)
  corroboration (from ingestion event)
  source_trust (from trust audit at that time)
  last_updated_at (from push event timestamp)
  → score and band fully reconstructable from these four stored fields
```

### 2.8 Configurable Derivation

Organizations may configure the base scores, multipliers, and band thresholds via Policy Group. This allows domain-specific calibration without changing the underlying descriptor model:

```yaml
confidence_derivation_config:
  # Override defaults for this deployment
  base_scores:
    primary: 90           # default — can increase to 95 for high-trust environments
    secondary: 70
  freshness_thresholds:
    high_max_minutes: 60  # default 60; can tighten to 15 for real-time requirements
    medium_max_minutes: 1440
    low_max_minutes: 10080
  band_thresholds:
    very_high_min: 81     # default; adjust as needed
    high_min: 61
```

Adjusted derivation configs are stored as Policy Group artifacts — versioned, auditable, and profile-governed.

## 3. Authority and Priority — Layer-Defined

### 3.1 Authority as Layer Data

Information Provider authority scope and priority are **layer-defined** — not just policy-driven. They represent static organizational knowledge about information architecture ("our CMDB is the authoritative source for business unit data"). This knowledge belongs in a `platform` domain layer — versioned, GitOps-managed, and inherited by all requests.

```yaml
layer:
  handle: "platform/information-authority/cmdb-authority"
  domain: platform
  priority: 600.0.0
  concern_tags: [information-authority, cmdb, organizational-data]
  fields:
    information_authority:
      primary_sources:
        - provider_uuid: <cmdb-provider-uuid>
          fields: [owner_business_unit, cost_center, cmdb_id, cmdb_location]
          authority_level: primary
          priority: 900.0.0
        - provider_uuid: <asset-mgmt-provider-uuid>
          fields: [asset_tag, purchase_date, warranty_expiry, serial_number]
          authority_level: primary
          priority: 900.0.0
      secondary_sources:
        - provider_uuid: <hr-system-uuid>
          fields: [owner_business_unit, employee_id]
          authority_level: secondary
          priority: 500.0.0
          # Secondary: corroborates primary; used if primary unavailable
      advisory_sources:
        - provider_uuid: <monitoring-system-uuid>
          fields: [reported_hostname, reported_ip]
          authority_level: advisory
          priority: 200.0.0
          # Advisory: context only; never used for decisions
```

### 3.2 Priority Within Authority Level

When multiple providers have the same `authority_level`, the `priority` field (using the same numeric priority schema as layers and policies) determines which value wins:

```
Higher priority value → wins when authority levels are equal
Authority level hierarchy: primary > secondary > advisory
Within same authority level: higher priority number wins
```

### 3.3 Policy Acting on Authority

Policies can act on authority metadata at runtime:

```yaml
# Transformation: enrich payload with confidence-weighted values
policy:
  type: transformation
  rule: >
    If field.owner_business_unit.confidence_score < 60
    AND field.owner_business_unit.authority_level != primary
    THEN inject: request_flags.requires_manual_business_unit_verification = true

# GateKeeper: require high confidence for financial operations
policy:
  type: gatekeeper
  rule: >
    If resource_type == Compute.VirtualMachine
    AND field.cost_center.confidence_band IN [very_low, low]
    THEN gatekeep: "Cost center assignment confidence insufficient for VM provisioning"
```

---

## 4. Ingestion-Time Conflict Detection and Resolution

### 4.1 Conflict Detection at Ingestion

Conflict detection occurs at ingestion time — when DCM receives a push event from an Information Provider. This is the correct architectural moment: before the data enters the entity record, not after.

```
Information Provider push event received
  │
  ▼ 1. Schema validation
  │   Validate against provider's declared schema version
  │   Reject on violation (strict) or warn (lenient per policy)
  │
  ▼ 2. Authority scope check
  │   Is this provider authorized to assert values for these fields on this entity?
  │   Reject unauthorized field assertions (INF-001)
  │
  ▼ 3. Confidence score computation
  │   Compute per-field score using standard formula (Section 2.2)
  │   Factor: source authority level, data freshness, corroboration
  │
  ▼ 4. Conflict detection
  │   For each field: does an existing value exist from another provider?
  │   Same value → corroboration (confidence increases, multiplier applied)
  │   Different value → conflict record created
  │   No existing value → new assertion (accept)
  │
  ▼ 5. Conflict resolution policy
  │   Apply declared resolution strategy:
  │   higher_authority_wins → use higher authority_level value
  │   higher_confidence_wins → use higher confidence score
  │   higher_priority_wins → use value from higher-priority provider
  │   escalate → create conflict record; human resolves; existing value retained
  │   merge → combine values (array/set fields only)
  │
  ▼ 6. Entity record update
  │   Write accepted values with full field provenance
  │
  ▼ 7. Audit record — INGEST action
     All field changes, conflicts detected/resolved, confidence scores,
     authority assertions recorded in Audit Store
```

### 4.2 The Conflict Record

```yaml
information_provider_conflict_record:
  record_uuid: <uuid>
  detected_at: <ISO 8601>
  field_path: owner_business_unit
  subject_entity_uuid: <uuid>
  conflicting_values:
    - provider_uuid: <cmdb-provider-uuid>
      authority_level: primary
      priority: 900.0.0
      value: "Payments Team"
      confidence_score: 86
      received_at: <ISO 8601>
    - provider_uuid: <hr-system-uuid>
      authority_level: secondary
      priority: 500.0.0
      value: "Infrastructure Team"
      confidence_score: 72
      received_at: <ISO 8601>
  resolution_strategy: higher_authority_wins
  resolution_status: <auto_resolved|pending_human|resolved|overridden>
  auto_resolved_value: "Payments Team"
  auto_resolved_reason: "primary authority_level wins over secondary"
  # If escalated:
  resolved_by: <actor-uuid>
  resolved_value: "Payments Team"
  resolution_reason: "CMDB is authoritative for business unit — HR system has stale data"
  resolution_audit_record_uuid: <uuid>
```

### 4.3 Authority Scope Conflicts at Registration

When a new provider registers and declares authority over a field already claimed by an existing provider at the same or higher authority level, DCM detects the conflict at registration time and requires explicit resolution before the provider becomes active.

```
New provider registers authority_scope: [owner_business_unit, primary]
  │
  ▼ DCM checks: existing primary authority for owner_business_unit?
  │
  ├── No existing primary → register; no conflict
  │
  └── Existing primary provider found:
        Create: authority_scope_conflict_record
        Action required:
          - Demote new provider to secondary, or
          - Demote existing provider to secondary, or
          - Declare explicit resolution strategy for this field
        Provider registration blocked until resolved
```

---

## 5. Write-Back Capability (Q63)

Information Providers may optionally support write-back — DCM updating external records when entity state changes. Write-back is triggered by policy, never automatic.

```yaml
information_provider_registration:
  capabilities:
    read: true                       # always required
    write_back: true                 # optional
    write_back_operations:
      - operation: create
        resource_types: [Compute.VirtualMachine]
        fields: [hostname, ip_address, owner_business_unit, lifecycle_state]
      - operation: update
        resource_types: [Compute.VirtualMachine]
      - operation: delete
        resource_types: [Compute.VirtualMachine]
    write_back_authentication:
      mode: api_key
      key_ref:
        service_provider_uuid: <uuid>
        secret_path: "dcm/providers/info/cmdb/write-key"
```

**Policy triggers write-back:**

```yaml
policy:
  type: transformation
  placement_phase: post
  rule: >
    If action IN [CREATE, STATE_TRANSITION, DELETE]
    AND resource_type == Compute.VirtualMachine
    THEN trigger_write_back:
      provider_uuid: <cmdb-provider-uuid>
      operation: update
      fields: [hostname, ip_address, lifecycle_state, owner_business_unit]
```

Write-back produces an audit record with `ENRICH` action and `source_type: information_provider_write_back`.

---

## 6. Extended Schema Versioning (Q64)

Information Provider extended schemas follow semver semantics — the same model as Resource Type Specifications.

```yaml
information_provider_registration:
  extended_schema:
    version: "2.1.0"
    fields:
      - name: cmdb_id
        type: string
        required: false
      - name: cmdb_ci_class
        type: string
        required: false
      - name: cmdb_location
        type: object
        required: false
    changelog:
      "2.0.0": "Removed deprecated cmdb_legacy_id field (major — breaking)"
      "2.1.0": "Added cmdb_location optional field (minor — compatible)"
    migration_plan:              # required for major version bumps
      from_version: "1.x"
      migration_script_ref: "git://cmdb-provider/migrations/v1-to-v2.yaml"
      migration_window: P30D
```

**Semver semantics for extended schemas:**

| Change | Version Bump | Reason |
|--------|-------------|--------|
| Field removed | **Major** | Breaking — consumers may depend on it |
| Field type changed | **Major** | Breaking — consumers must update |
| New optional field added | **Minor** | Compatible — additive |
| Description or constraint changed | **Revision** | Compatible — no structural change |

DCM validates incoming push data against the declared schema version. Major version bumps require a declared migration plan before the new schema version activates.

---

## 7. Well-Known Information Provider Registry (Q65)

DCM maintains a three-tier Information Provider Registry following the same governance model as the Resource Type Registry.

| Tier | Name | Contains | Examples |
|------|------|---------|---------|
| 1 | DCM Core | Universal integration patterns | Generic CMDB, Generic IPAM, Generic DNS |
| 2 | Verified Community | Specific platform integrations | ServiceNow, Infoblox, NetBox, FreeIPA, AD, HashiCorp Vault |
| 3 | Organization | Internal/proprietary | Acme ERP, Corp Asset Database |

Well-known provider registrations include:
- Pre-configured authority scope declarations
- Pre-built extended schema definitions
- Pre-configured write-back operation mappings
- Connection templates with documented credential requirements
- Example Policy Group activations for common use cases
- Health check endpoint patterns

The Information Provider Registry is **distinct from the Resource Type Registry** — separate governance, separate GitOps repositories — but shares the same infrastructure pattern: federated, PR-based proposals, automated validation, shadow validation period, and signed bundles for air-gapped import.

---

## 8. Air-Gapped Verification (Q66)

Three modes for Information Provider verification in air-gapped environments:

### 8.1 Mode 1 — Pre-Verified Signed Bundle (Recommended)

```yaml
air_gapped_provider_bundle:
  bundle_uuid: <uuid>
  bundle_type: information_provider
  signed_at: <ISO 8601>
  signing_key_ref: <org-signing-key>
  provider_registration: <full provider registration YAML>
  tls_certificate_chain: <PEM>
  schema_definitions: <extended schema YAMLs>
  verification_token: <token>
  expires_at: <ISO 8601>        # bundles have expiry
```

### 8.2 Mode 2 — Internal mTLS (Internal Providers)

Providers that are themselves internal (internal CMDB, internal IPAM) register with `air_gap_mode: internal_only` and verify using internal mTLS certificates issued by the organization's internal CA (FreeIPA CA or equivalent).

### 8.3 Mode 3 — Periodic Online Re-Verification

For environments air-gapped most of the time but with occasional connectivity windows:

```yaml
provider_verification:
  mode: periodic_online
  cache_ttl: P30D                # how long cached verification is valid
  on_cache_expiry:
    minimal: continue            # continue without re-verification
    dev: alert                   # warn but continue
    standard: alert              # warn but continue
    prod: suspend                # suspend until re-verified
    fsi: suspend
    sovereign: suspend
```

---

## 8a. Information Provider Trust Score Validation (Q15)

### 8a.1 Dual-Trigger Model

Information Provider trust scores are maintained per provider using the same dual-trigger pattern as conflict validation: event-triggered updates (primary) with scheduled re-verification (safety net).

**Event-triggered updates:**
- Provider push fails schema validation → `source_trust` degraded
- Provider push conflicts with primary authority source → `source_trust` degraded
- Health check fails → `source_trust` degraded
- Sovereignty declaration change → trust re-evaluated against current Tenant requirements
- Provider registration update (new credentials, endpoint change) → re-verification triggered

**Scheduled re-verification:**
- Daily: health check against all active Information Providers
- Weekly: full re-verification (identity, sovereignty, certifications, schema compatibility)
- `fsi` / `sovereign` profiles: daily full re-verification

### 8a.2 Trust Score Structure

```yaml
information_provider_trust_score:
  provider_uuid: <uuid>
  score: 87                        # 0-100; contributes to source_trust field
  scored_at: <ISO 8601>
  components:
    identity_verified: true        # mTLS cert chain valid; re-checked weekly
    endpoint_reachable: true       # health check; re-checked daily
    schema_current: true           # schema version matches registered
    sovereignty_compatible: true   # sovereignty matches Tenant requirements
    certifications_current: true   # certifications not expired
    push_error_rate:
      rate: 0.02                   # 2% of pushes had schema/auth errors (7-day rolling)
      weight: 0.15                 # contributes 15% to score degradation
    conflict_rate:
      rate: 0.05                   # 5% of pushes had value conflicts (7-day rolling)
      weight: 0.10
  decay_rate: per_7_days           # score decays if not re-verified
  current_source_trust: verified   # verified | degraded | suspended
  action_on_score_below:
    threshold: 60
    action: <suspend|alert|reduce_weight>
    # suspend:       stop accepting pushes from this provider
    # alert:         notify platform admin; continue with degraded trust
    # reduce_weight: automatically degrade source_trust to degraded
```

### 8a.3 Trust Score to source_trust Mapping

| Trust Score | source_trust | Effect on Confidence |
|------------|-------------|---------------------|
| ≥ 80 | `verified` | Full confidence multiplier (1.00) |
| 60-79 | `degraded` | Reduced confidence multiplier (0.75) |
| < 60 | `suspended` | No new data accepted; score = 0 |


## 9. System Policies

| Policy | Rule |
|--------|------|
| `INF-001` | Information Providers declare authority_level (primary, secondary, advisory) and authority_scope (resource types and fields). Conflicting authority scope declarations are detected at registration time. Conflicting field values from different providers at ingestion time are resolved per declared strategy. All conflicts produce audit records. |
| `INF-002` | Information Providers may declare write_back capability with specific operations (create, update, delete) and resource types. Write-back is triggered by policy only — never automatic. Write-back produces audit records with ENRICH action. Credentials reference a registered Credential Provider. |
| `INF-003` | Information Provider extended schemas are versioned using semver. Removing a field or changing a field type is a major (breaking) version bump requiring a declared migration plan. Adding an optional field is a minor bump. DCM validates incoming push data against the declared schema version. |
| `INF-004` | DCM maintains a three-tier Information Provider Registry (Core, Verified Community, Organization) following the same governance model as the Resource Type Registry. |
| `INF-009` | Information Provider trust scores (0-100) are maintained per provider with event-triggered updates (push failure, schema mismatch, conflict, health check) and scheduled weekly re-verification. Trust score degradation transitions source_trust to degraded (reduced confidence multiplier). Suspension stops accepting pushes. Policy governs thresholds and actions per provider. |
| `INF-005` | In air-gapped environments, Information Providers verify via pre-verified signed bundles, internal mTLS, or periodic online re-verification with cached tokens. Profile governs cache expiry behavior. |
| `INF-006` | Information Provider field values carry a confidence score (0-100) computed from: source authority level, data freshness, and corroboration. DCM computes scores — providers do not self-declare confidence. Scores decay with data age. |
| `INF-007` | Authority scope and priority for Information Providers are declared in platform or system domain layers. Policy acts on confidence scores and bands — gating, filtering, and escalating based on threshold declarations. |
| `INF-008` | Conflict detection occurs at ingestion time. Policy governs automated resolution strategy. All conflicts — detected, auto-resolved, and escalated — produce INGEST audit records with the full conflict detail. |

---

## 10. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should confidence score decay be linear or exponential? | Scoring model | ✅ Resolved — freshness is discrete threshold bands not decay curve; stale multiplier 0.50 provides the cliff effect |
| 2 | Should DCM expose confidence score aggregation APIs — e.g., "average confidence across all fields for this entity"? | Consumer experience | ✅ Resolved — per-entity confidence aggregation endpoint; overall band = lowest field band; computed on demand; identifies contested and stale fields (INF-010) |
| 3 | Should conflicting providers receive notification when their value is overridden? | Provider relationship | ✅ Resolved — provider opt-in override notifications; webhook or Message Bus; payload policy-governed; overriding value may be redacted (INF-011) |


## 11. Information Provider Advanced Gap Resolutions

### 11.1 Confidence Score Aggregation API (Q2)

DCM exposes a per-entity confidence aggregation endpoint. The overall band reflects the lowest (most conservative) field band — preventing high-scoring fields from masking problematic ones. Aggregations are computed on demand — never stored (freshness changes continuously).

```yaml
confidence_aggregation_api:
  endpoint: GET /api/v1/entities/{uuid}/confidence
  response:
    entity_uuid: <uuid>
    overall_band: high              # lowest band across all fields (conservative)
    field_summaries:
      - field: owner_business_unit
        band: high
        score: 86
        authority_level: primary
        last_updated_at: <ISO 8601>
      - field: cost_center
        band: medium
        score: 54
        corroboration: contested    # two providers disagree
    lowest_confidence_fields:
      - field: cost_center
        reason: contested
      - field: asset_tag
        reason: stale               # data age > 7 days
    computed_at: <ISO 8601>
```

### 11.2 Conflicting Provider Override Notifications (Q3)

Information Providers may opt in to override notifications. Not a universal default — read-only public registries have no use for notifications; internal CMDBs may want to investigate discrepancies.

```yaml
information_provider_registration:
  conflict_notification:
    enabled: true                   # provider opts in
    notification_channel: webhook   # or: message_bus
    notification_endpoint: https://cmdb.corp.example.com/dcm-notifications
    notify_on: [value_overridden, value_contested, authority_superseded]
    notification_payload:
      field_path: true
      overriding_provider_uuid: true
      overriding_value: false       # may be redacted for confidentiality
      conflict_record_uuid: true
```

**Privacy:** The overriding value may be confidential (from a classified source). Policy governs what is included in the notification payload. GateKeeper can redact the overriding value if classified.

### 11.3 System Policies — Information Provider Advanced Gaps

| Policy | Rule |
|--------|------|
| `INF-010` | DCM exposes a confidence aggregation endpoint per entity (GET /api/v1/entities/{uuid}/confidence). The overall confidence band reflects the lowest (most conservative) field band. Aggregations are computed on demand — never stored. The response identifies contested and stale fields requiring attention. |
| `INF-011` | Information Providers may opt in to override notifications by declaring conflict_notification in their registration. Notifications sent via webhook or Message Bus. The notification payload is policy-governed — the overriding value may be redacted for confidentiality reasons. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
