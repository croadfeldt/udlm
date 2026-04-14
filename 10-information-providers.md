# DCM Data Model — Information Providers



**Document Status:** ✅ Complete  
**Related Documents:** [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Entity Relationships](09-entity-relationships.md)

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
> The Provider abstraction — Information Provider capability extension



---

## 1. Purpose

An **Information Provider** is a registered DCM provider that serves as the authoritative source for a specific category of data that DCM needs to reference but does not own. It exposes external data to DCM through a standard interface, enabling DCM to look up, verify, and relate external records without caching or owning them.

Information Providers are a first-class provider type in DCM alongside Service Providers and compound service definitions. They follow the same registration, health check, trust, and contract model as Service Providers — adapted where applicable to the lookup-only nature of information retrieval.

---

## 2. Why Information Providers Exist

DCM manages the lifecycle of resources it provisions. But resources exist in a broader organizational context — they are owned by business units, attributed to cost centers, associated with product owners, governed by regulatory scopes. This contextual data lives in authoritative external systems (HR systems, finance systems, CMDBs, ITSM tools) that DCM does not and should not own.

Without a formal model for referencing external data, organizations face two bad choices:
- **Copy the data into DCM** — creating duplication, staleness, and an ownership conflict with the authoritative system
- **Ignore the data** — losing business context, cost attribution, and compliance traceability

Information Providers solve this by giving DCM a standard, stable, governed interface to external data without requiring ownership transfer.

---

## 3. Information Provider in the Provider Ecosystem

DCM defines eleven provider types, all implementing the unified Provider base contract. This document focuses on the Information Provider type. For the complete provider type list see [A-provider-contract.md](A-provider-contract.md).

| Provider Type | Purpose | Data Direction | DCM Owns Result? |
|--------------|---------|---------------|-----------------|
| **Service Provider** | Executes work, realizes resources | DCM → Provider → DCM | Yes — DCM owns the realized entity |
| **Information Provider** | Serves authoritative external data | DCM → Provider (lookup only) | No — external system is authoritative |
| **compound service definition** | Composes multiple providers | DCM → Meta → Child Providers → DCM | Yes — DCM owns the composite result |

---

## 4. Information Provider Contract

Information Providers follow the same provider contract model as Service Providers where applicable. The contract dimensions are:

### 4.1 Registration Contract
Same model as Service Providers. Information Providers register with DCM declaring their endpoint, the information types they implement, their lookup capabilities, and their extended schema.

### 4.2 Health Check Contract
Same model as Service Providers. Information Providers expose a `/health` endpoint. DCM polls it on the same configurable interval. `Ready`/`NotReady` state machine applies. An `NotReady` Information Provider is excluded from lookups — relationships referencing it are flagged for on-demand verification fallback.

### 4.3 Trust Contract
Same model as Service Providers. Information Providers must be registered, validated, and certified before DCM will accept their data. The chain of trust applies to data returned by Information Providers — provenance records the provider UUID for every field sourced from an Information Provider.

### 4.4 Capacity Contract
Adapted for lookup capacity rather than resource provisioning capacity. Information Providers declare and report their query capacity — requests per second, rate limits, availability windows.

```yaml
capacity_registration:
  provider_uuid: <uuid>
  registration_timestamp: <ISO 8601>
  capacity_by_information_type:
    - information_type_uuid: <uuid>
      queries_per_second: 1000
      rate_limit_window: 60s
      availability: 99.9%
```

### 4.5 Lifecycle Event Contract
Same model as Service Providers. Information Providers have a contractual obligation to notify DCM when records they have provided references for change status. DCM receives the notification and updates the external entity reference record accordingly.

**Reportable event types for Information Providers:**

| Event Type | Description | DCM Response |
|------------|-------------|--------------|
| `RECORD_DEACTIVATED` | A referenced record has been deactivated | Update reference status, Policy Engine evaluation |
| `RECORD_MERGED` | Two records merged — UUID may change | Update external_uuid in reference record |
| `RECORD_SPLIT` | One record split into multiple | Policy Engine evaluation — which new record applies? |
| `UUID_CHANGED` | Record UUID changed in external system | Update external_uuid, re-verify all references |
| `DATA_UPDATED` | Standard field values changed | Update last_verified, notify relationships |
| `PROVIDER_DEGRADED` | Provider is degraded but operational | DCM flags affected references for on-demand verification |

### 4.6 Naturalization/Denaturalization Contract
Information Providers translate their native data format (HR system JSON, finance system XML, LDAP records, REST APIs) into the DCM unified data model format. The translation is the provider's responsibility — DCM always receives data in DCM format.

---

## 5. Standard vs Extended Data

### 5.1 Standard Data (DCM-defined)

Fields that are part of the DCM-specified schema for an information type. DCM core uses these fields for lookups, relationship matching, policy evaluation, and display. They are portable across all implementations of that information type.

DCM only relies on standard data for operational decisions. Extended data is carried in the payload but is not used for DCM core operations.

### 5.2 Extended Data (organization-defined)

Additional fields organizations add to enrich the standard schema for their specific needs. Declared in the provider's extended schema registration. DCM carries extended data in the payload for downstream consumers — policy engines, cost analysis tools, reporting — that know how to use them.

```yaml
# Standard + Extended data example — Business.BusinessUnit
business_unit_record:
  # Standard fields — DCM defined, used for lookups
  uuid: "bu-uuid-001"
  name: "Payments Platform"
  code: "BU-PAY"
  parent_uuid: "bu-uuid-root"
  organization_uuid: "org-uuid-001"
  status: active

  # Extended fields — organization defined
  extensions:
    profit_center_code: "PC-4421"
    regulatory_jurisdiction: "EU"
    trading_desk_id: "TD-007"
    risk_tier: 1
    internal_charge_code: "IC-PAY-001"
```

---

## 6. Lookup Key Model

DCM looks up external records using a stable primary key — always the external UUID where available — with a fallback chain for systems that don't support UUID-based lookup.

### 6.1 External Entity Reference Structure

```yaml
external_entity_reference:
  uuid: <dcm-generated uuid — stable internal anchor>
  # DCM UUID is what gets stored in relationship declarations
  # If the external system changes its UUID, only this record changes
  # All relationships pointing to dcm-uuid remain valid

  external_uuid: <stable uuid from the external system>
  information_provider_uuid: <uuid of registered Information Provider>
  information_type_uuid: <uuid of information type in DCM registry>
  information_type_name: Business.BusinessUnit

  lookup_method:
    primary_key: external_uuid
    # Always attempted first
    fallback_keys:
      - field: code
        value: "BU-PAY"
      - field: name
        value: "Payments Platform"
    # Fallback keys tried in order if primary_key lookup fails

  # Non-authoritative display cache — for UI convenience only
  display_name: "Payments Platform"
  display_name_authoritative: false

  verification:
    last_verified: <ISO 8601>
    last_verified_method: <scheduled|on_demand|provider_push>
    verification_status: <verified|stale|unverifiable|deactivated>
    next_scheduled_verification: <ISO 8601>

  status:
    state: <active|stale|unverifiable|deactivated>

  provenance:
    <standard provenance metadata>
```

### 6.2 Why DCM UUID Wraps External UUID

The DCM-generated UUID is the stable internal anchor. This means:
- All relationship declarations inside DCM reference the DCM UUID
- If the external system changes its UUID (migration, system upgrade), only the `external_entity_reference` record needs updating
- All relationships pointing to the DCM UUID remain valid without modification
- The provenance chain tracks the change via the `UUID_CHANGED` lifecycle event

---

## 7. Three-Mode Verification Model

DCM uses a trust-but-verify approach to external entity references. The external system is trusted as authoritative for the data — DCM does not validate content. But DCM verifies that references remain valid — the UUID still exists and the record is still active.

### 7.1 Mode 1 — Scheduled Verification (DCM-initiated)

DCM calls the Information Provider's `/verify/{uuid}` endpoint on a configurable schedule for all registered external entity references. Default frequency: configurable — suggested minimum twice daily. Updates `last_verified` and `verification_status`.

### 7.2 Mode 2 — Provider Push (Information Provider obligation)

The Information Provider notifies DCM when a referenced record changes status. This is a contractual obligation — same model as Service Provider lifecycle events. DCM receives the notification, updates the external entity reference, and the Policy Engine evaluates the appropriate response.

### 7.3 Mode 3 — On-Demand Verification (fallback)

When a relationship involving an external entity reference is accessed during request processing, policy evaluation, or drift detection, DCM can verify the reference in real time before relying on it. Used when:
- `last_verified` is beyond the acceptable staleness window
- The operation requires high confidence
- Scheduled verification returned `stale` or `unverifiable`

### 7.4 Verification Fallback Chain

```
External entity reference accessed
  │
  ▼
Is verification_status: verified AND last_verified within window?
  │ Yes → proceed with reference
  │ No ↓
  ▼
Mode 3 — on-demand verify via Information Provider /verify/{uuid}
  │ Success → update last_verified, verification_status: verified, proceed
  │ Failure ↓
  ▼
Policy Engine evaluates:
  Options (configurable per information type and organizational policy):
    block_request   — reject request until reference is verified
    warn_and_proceed — proceed with warning recorded in provenance
    use_display_only — use display_name only, no operational reliance
    escalate        — notify appropriate personas for human resolution
```

---

## 8. Information Type Registry

Information types live in the same DCM Resource Type Registry as Resource Types, distinguished by category prefix. Same versioning, same deprecation model, same governance.

### 8.1 Standard Information Type Categories

| Category | Description | Examples |
|----------|-------------|---------|
| `Business.*` | Business organizational data | BusinessUnit, CostCenter, ProductOwner |
| `Identity.*` | Identity and access data | Person, ServiceAccount, Group |
| `Compliance.*` | Regulatory and compliance data | RegulatoryScope, AuditFramework |
| `Operations.*` | Operational reference data | Runbook, SLA, SupportContract |

### 8.2 DCM Default Information Types

```yaml
# Business.BusinessUnit
information_type:
  uuid: <uuid>
  name: Business.BusinessUnit
  category: Business
  version: 1.0.0
  standard_fields:
    - name: uuid
      type: string
      required: true
      lookup_supported: true
    - name: name
      type: string
      required: true
      lookup_supported: true
    - name: code
      type: string
      required: false
      lookup_supported: true
    - name: parent_uuid
      type: string
      required: false
      lookup_supported: false
    - name: organization_uuid
      type: string
      required: true
      lookup_supported: false
    - name: status
      type: enum
      values: [active, inactive]
      required: true
      lookup_supported: false
  extended_fields_permitted: true
  status: active

# Business.CostCenter
information_type:
  uuid: <uuid>
  name: Business.CostCenter
  standard_fields:
    - name: uuid
      lookup_supported: true
    - name: name
      lookup_supported: true
    - name: code
      lookup_supported: true
    - name: owner_uuid
      lookup_supported: false
    - name: budget_period
      lookup_supported: false
    - name: status
      lookup_supported: false

# Identity.Person
information_type:
  uuid: <uuid>
  name: Identity.Person
  standard_fields:
    - name: uuid
      lookup_supported: true
    - name: name
      lookup_supported: true
    - name: email
      lookup_supported: true
    - name: employee_id
      lookup_supported: true
    - name: department_uuid
      lookup_supported: false
    - name: status
      lookup_supported: false
```

### 8.3 Custom Information Types

Organizations register custom information types following the same model:

```yaml
custom_information_type:
  uuid: <uuid>
  name: <Category.TypeName>
  # Must use a non-reserved category prefix or register a new one
  category: <existing category or new custom category>
  version: <Major.Minor.Revision>
  registered_by_tenant_uuid: <uuid — or null for global>
  standard_fields:
    <list of standard fields>
  extended_fields_permitted: <true|false>
  status: <active|deprecated|retired>
```

---

## 9. Information Provider Registration

```yaml
information_provider_registration:
  uuid: <uuid>
  name: <provider name>
  display_name: <human-readable name>
  version: <Major.Minor.Revision>

  implements:
    - information_type_uuid: <uuid>
      information_type_name: Business.BusinessUnit
      information_type_version: <version>
      lookup_methods_supported: [primary_key, code]
      extended_fields_supported: true
      extended_schema:
        <JSON Schema for extended fields this provider exposes>

  endpoint: <base URL of the Information Provider API>

  capacity:
    queries_per_second: <integer>
    rate_limit_window: <duration>
    update_frequency: <how often provider pushes updates>

  sovereignty_constraints:
    <same model as Service Providers>

  trust_declaration:
    <same model as Service Providers>

  health_check:
    endpoint: /health
    poll_interval_seconds: <integer>

  status:
    state: <active|deprecated|retired>
    deprecation_date: <if applicable>
    sunset_date: <if applicable>
    replacement_uuid: <if deprecated>
    deprecation_reason: <if deprecated>
    migration_guidance: <if deprecated>

  provenance:
    <standard provenance metadata>
```

---

## 10. Mandatory Information Provider API Endpoints

All Information Providers must implement these endpoints as part of their provider contract:

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Provider health check — same as Service Provider |
| `GET` | `/lookup/{uuid}` | Returns standard + extended data for a record by external UUID |
| `GET` | `/verify/{uuid}` | Lightweight — confirms UUID exists and is active |
| `POST` | `/search` | Finds records matching standard field criteria (fallback lookup) |
| `POST` | `/notify` | DCM calls this to acknowledge receipt of provider push events |

---

## 11. Internally Owned Business Data

When an organization decides to manage business context data in DCM rather than reference an external system, they define it as a DCM Resource Type in the `Business.*` or custom category. Internally owned business data follows the **standard resource entity model** exactly:

- Has a UUID
- Has a Resource Type (`Business.BusinessUnit`, `Business.CostCenter`, etc.)
- Has provenance
- Has versioning
- Has relationships to other entities
- Follows the universal lifecycle (active → deprecated → retired)
- Can be grouped under Tenants and Resource Groups

The relationship model is identical whether the related entity is internal or external — the `related_entity_type` field (`internal` vs `external`) is the only difference from the consuming entity's perspective.

This means an organization can start with an external Information Provider reference and migrate to internally owned business data later — relationships remain structurally the same, only the `related_entity_type` changes.

---

## 12. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | How are conflicting provider push events handled — two Information Providers claim authority for the same record? | Data integrity | ✅ Resolved — authority_level (primary/secondary/advisory) + authority_scope; conflict_resolution strategies; ingestion-time conflict detection; conflict records; see doc 21 (INF-001) |
| 2 | Should Information Providers support write-back — DCM updating external records via the provider? | Scope expansion | ✅ Resolved — optional declared capability; policy-triggered write-back; audit records produced; credentials via Credential Provider; see doc 21 (INF-002) |
| 3 | How is the extended schema versioned — if a provider adds or removes extended fields, how are existing references affected? | Versioning | ✅ Resolved — semver semantics on extended schema; field removal/type change = major; new optional field = minor; migration plan required for major bumps; see doc 21 (INF-003) |
| 4 | Should DCM maintain a registry of well-known Information Providers (HR systems, finance systems) to simplify onboarding? | Adoption | ✅ Resolved — three-tier Information Provider Registry (Core/Community/Organization); same governance model as Resource Type Registry; separate registries; see doc 21 (INF-004) |
| 5 | How does the verification model interact with air-gapped environments where Information Providers may be unreachable? | Sovereignty | ✅ Resolved — three air-gap modes: pre-verified signed bundle, internal mTLS, periodic online re-verification with cached tokens; profile-governed cache expiry (prod/fsi/sovereign=suspend on expiry); see doc 21 (INF-005) |

---

## 13. Related Concepts

- **External Entity Reference** — the stable pointer record DCM uses to reference external data
- **Entity Relationships** — the universal relationship model that uses Information Provider references
- **Service Provider** — counterpart provider type for resource provisioning
- **Resource Type Registry** — the unified registry containing both Resource Types and Information Types
- **Trust Contract** — the provider trust model shared across all provider types
- **Naturalization/Denaturalization** — translation between external native format and DCM unified format

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
