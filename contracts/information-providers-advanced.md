# UDLM — Information Providers: Confidence, Authority, and Schema Versioning

**Document Status:** ✅ Stable — UDLM substrate contract
**Related Documents:** [Information Providers](information-providers.md) | [Universal Audit Model](../observability/universal-audit.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM substrate.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](../foundations/foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](provider-contract.md) | [Policy Contract](policy-contract.md)
>
> **This document maps to: PROVIDER**
>
> The Provider abstraction — Information Provider advanced capabilities.

---

## 1. Purpose

This document extends the base Information Provider model with the substrate concepts required for enterprise-grade information governance: confidence scoring for all provider-supplied data, authority and priority declarations as layer-defined organizational knowledge, the schema versioning contract for extended Information Provider schemas, and the well-known Information Provider Registry contract.

Realization-specific enforcement (ingestion-time conflict detection mechanics, write-back execution, air-gapped verification orchestration, provider priority and fallback logic) lives in the consuming realization's documentation.

---

## 2. Confidence Scoring — The Hybrid Descriptor Model

### 2.1 Purpose and Design Goals

Every field value supplied by an Information Provider carries a confidence descriptor. A UDLM realization aggregates data from multiple external sources — CMDB, HR systems, IPAM, asset management, monitoring tools — each with different freshness, authority, and reliability. The confidence model answers: **how much should you trust this field value?**

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
| `corroboration` | Realization ingestion pipeline | Each push event | Compared against existing values from other providers |
| `source_trust` | Realization trust scoring system | Event-triggered + scheduled | Push failures, schema errors, health check, re-verification |
| `last_updated_at` | Realization ingestion pipeline | Each push event | Timestamp of the push event |
| `freshness` | Realization — derived | Query time | Computed from `now - last_updated_at` vs thresholds |
| `score` | Realization — derived | Query time | Computed from descriptor components |
| `band` | Realization — derived | Query time | Computed from score vs band thresholds |

**The realization computes all derived values — providers never self-declare confidence.**

### 2.4 Descriptor Component Values

**`authority_level`** — closed substrate vocabulary; declared in the authority layer:

| Value | Meaning |
|-------|---------|
| `primary` | Declared primary authoritative source for this field |
| `secondary` | Corroborating source; used if primary unavailable |
| `advisory` | Context only; never used for decisions |
| `discovered` | Value found via active interrogation |
| `self_reported` | Entity reported its own value |
| `inferred` | Value inferred from other data |

**`corroboration`** — closed substrate vocabulary; computed at ingestion time:

| Value | Condition | Confidence Effect |
|-------|-----------|-----------------|
| `confirmed` | 2+ providers agree on this value | Increases confidence |
| `single_source` | Only one provider has asserted this value | Neutral |
| `contested` | 2+ providers disagree on this value | Reduces confidence |

**`source_trust`** — closed substrate vocabulary; maintained by trust scoring system:

| Value | Condition | Confidence Effect |
|-------|-----------|-----------------|
| `verified` | Provider identity, sovereignty, certs all current | Full confidence |
| `degraded` | Provider has elevated error/conflict rate | Reduced confidence |
| `suspended` | Provider below trust threshold; pushes stopped | No new data |

**`freshness`** — closed substrate vocabulary; computed from `data_age_minutes`. The specific age thresholds below are the substrate defaults; realizations MAY adjust them via configuration (see §2.8):

| Value | Age Threshold (default) |
|-------|-------------|
| `high` | < 1 hour |
| `medium` | 1 hour – 1 day |
| `low` | 1 day – 7 days |
| `stale` | > 7 days |

### 2.5 The Score Derivation Formula (Substrate Default)

The score is a convenience number derived deterministically from the descriptor. It enables mathematical composition (cross-peer scoring, conflict resolution ordering) where a single number is needed. The substrate defines the default formula; realizations MAY adjust component weights via Policy Group (see §2.8).

```
score = min(100, base(authority_level)
              × freshness_multiplier(freshness)
              × corroboration_multiplier(corroboration)
              × trust_multiplier(source_trust))
```

**Base values by authority_level (defaults):**

| authority_level | Base Score |
|----------------|-----------|
| `primary` | 90 |
| `secondary` | 70 |
| `discovered` | 60 |
| `advisory` | 50 |
| `self_reported` | 40 |
| `inferred` | 30 |

**Freshness multipliers (defaults):**

| freshness | Multiplier |
|-----------|-----------|
| `high` | 1.00 |
| `medium` | 0.95 |
| `low` | 0.85 |
| `stale` | 0.50 |

**Corroboration multipliers (defaults):**

| corroboration | Multiplier |
|--------------|-----------|
| `confirmed` | 1.15 |
| `single_source` | 1.00 |
| `contested` | 0.60 |

**Trust multipliers (defaults):**

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

### 2.6 Score Bands — For Policy Use (Closed Substrate Vocabulary)

Policies use bands, not raw scores. This avoids the brittleness of threshold values like "reject if score < 73":

| Band | Score Range (default) | Policy Label |
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

### 2.8 Configurable Derivation (Contract)

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

---

## 3. Authority and Priority — Layer-Defined

### 3.1 Authority as Layer Data

Information Provider authority scope and priority are **layer-defined** — not just policy-driven. They represent static organizational knowledge about information architecture ("our CMDB is the authoritative source for business unit data"). This knowledge belongs in a `platform` domain layer — versioned, lifecycle-managed, and inherited by all requests.

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

## 4. Extended Schema Versioning

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

A conformant realization MUST validate incoming push data against the declared schema version. Major version bumps require a declared migration plan before the new schema version activates.

---

## 5. Well-Known Information Provider Registry

UDLM defines a three-tier Information Provider Registry following the same governance model as the Resource Type Registry.

| Tier | Name | Contains | Examples |
|------|------|---------|---------|
| 1 | UDLM Core | Universal integration patterns | Generic CMDB, Generic IPAM, Generic DNS |
| 2 | Verified Community | Specific platform integrations | ServiceNow, Infoblox, NetBox, FreeIPA, AD, HashiCorp Vault |
| 3 | Organization | Internal/proprietary | Acme ERP, Corp Asset Database |

Well-known provider registrations include:
- Pre-configured authority scope declarations
- Pre-built extended schema definitions
- Pre-configured write-back operation mappings
- Connection templates with documented credential requirements
- Example Policy Group activations for common use cases
- Health check endpoint patterns

The Information Provider Registry is **distinct from the Resource Type Registry** — separate governance, separate repositories — but shares the same infrastructure pattern: federated, proposal-based with automated validation, shadow validation period, and signed bundles for air-gapped import.

---

## 6. Trust Score Model (Substrate Contract)

A UDLM realization MUST maintain a trust score per Information Provider. The substrate defines the score's role in the confidence model and the closed `source_trust` vocabulary it maps to. Specific event triggers, scheduling intervals, and remediation actions are realization choices.

### 6.1 Trust Score Structure

```yaml
information_provider_trust_score:
  provider_uuid: <uuid>
  score: 87                        # 0-100; contributes to source_trust field
  scored_at: <ISO 8601>
  components:
    identity_verified: true        # mTLS cert chain valid
    endpoint_reachable: true       # health check
    schema_current: true           # schema version matches registered
    sovereignty_compatible: true   # sovereignty matches Tenant requirements
    certifications_current: true   # certifications not expired
    push_error_rate:
      rate: 0.02                   # rolling-window push errors
      weight: 0.15
    conflict_rate:
      rate: 0.05                   # rolling-window value conflicts
      weight: 0.10
  decay_rate: per_7_days
  current_source_trust: verified   # verified | degraded | suspended
  action_on_score_below:
    threshold: 60
    action: <suspend|alert|reduce_weight>
```

### 6.2 Trust Score to source_trust Mapping (Substrate Default)

| Trust Score | source_trust | Effect on Confidence |
|------------|-------------|---------------------|
| ≥ 80 | `verified` | Full confidence multiplier (1.00) |
| 60-79 | `degraded` | Reduced confidence multiplier (0.75) |
| < 60 | `suspended` | No new data accepted; score = 0 |

---

## 7. Confidence Aggregation Contract

A UDLM-conformant realization MUST expose a per-entity confidence aggregation endpoint. The aggregation response shape is normative:

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

Substrate invariants:
- The overall band reflects the lowest (most conservative) field band — high-scoring fields do NOT mask problematic ones.
- Aggregations are computed on demand — never stored (freshness changes continuously).

---

## 8. Override Notification Capability (Contract)

Information Providers MAY opt in to override notifications. This is a capability declared at registration; not a universal default. The registration shape is normative:

```yaml
information_provider_registration:
  conflict_notification:
    enabled: true                   # provider opts in
    notification_channel: webhook   # or: message_bus
    notification_endpoint: https://cmdb.corp.example.com/notifications
    notify_on: [value_overridden, value_contested, authority_superseded]
    notification_payload:
      field_path: true
      overriding_provider_uuid: true
      overriding_value: false       # may be redacted for confidentiality
      conflict_record_uuid: true
```

Substrate invariants:
- Notification triggers (`value_overridden`, `value_contested`, `authority_superseded`) are closed substrate vocabulary.
- The overriding value MAY be confidential. The notification payload contents are policy-governed; the realization MUST honor policy-declared redaction.

---

## 9. UDLM System Policies

| Policy | Rule |
|--------|------|
| `INF-001` | Information Providers declare `authority_level` (primary, secondary, advisory) and `authority_scope` (resource types and fields). Conflicting authority scope declarations are detected at registration time. Conflicting field values from different providers at ingestion time are resolved per declared strategy. All conflicts produce audit records. |
| `INF-003` | Information Provider extended schemas are versioned using semver. Removing a field or changing a field type is a major (breaking) version bump requiring a declared migration plan. Adding an optional field is a minor bump. A conformant realization validates incoming push data against the declared schema version. |
| `INF-004` | A UDLM realization maintains a three-tier Information Provider Registry (Core, Verified Community, Organization) following the same governance model as the Resource Type Registry. |
| `INF-006` | Information Provider field values carry a confidence score (0-100) computed from: source authority level, data freshness, and corroboration. The realization computes scores — providers do not self-declare confidence. Scores decay with data age. |
| `INF-007` | Authority scope and priority for Information Providers are declared in platform or system domain layers. Policy acts on confidence scores and bands — gating, filtering, and escalating based on threshold declarations. |
| `INF-009` | Information Provider trust scores (0-100) are maintained per provider with event-triggered updates and scheduled re-verification. Trust score degradation transitions `source_trust` to `degraded` (reduced confidence multiplier). Suspension stops accepting pushes. Policy governs thresholds and actions per provider. |
| `INF-010` | A UDLM realization exposes a confidence aggregation endpoint per entity (GET /api/v1/entities/{uuid}/confidence). The overall confidence band reflects the lowest (most conservative) field band. Aggregations are computed on demand — never stored. The response identifies contested and stale fields requiring attention. |
| `INF-011` | Information Providers may opt in to override notifications by declaring `conflict_notification` in their registration. Notifications sent via webhook or Message Bus. The notification payload is policy-governed — the overriding value may be redacted for confidentiality reasons. |

---

*UDLM substrate document. Realization-specific ingestion-time conflict detection mechanics, write-back execution, air-gapped verification orchestration, and provider priority/fallback logic live in the consuming realization's documentation.*
