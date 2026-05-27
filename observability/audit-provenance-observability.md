# DCM Data Model — Audit, Provenance, and Observability



**Document Status:** ✅ Complete  
**Related Documents:** [Four States](02-four-states.md) | [data stores](11-storage-providers.md) | [Context and Purpose](00-context-and-purpose.md)

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
> The Data abstraction — audit records, provenance as structural data



---

## 1. Purpose

Audit, Provenance, and Observability are three distinct but related capabilities in DCM. They are often conflated — this document separates them precisely, defines their relationship, and establishes the architectural model for each.

| Capability | Question Answered | Audience | Time Orientation |
|------------|------------------|----------|-----------------|
| **Provenance** | Where did this data come from and how did it change? | System — embedded in data | Embedded in every payload |
| **Audit** | What happened, who authorized it, can you prove it? | Auditors, Compliance, Security | Backward-looking |
| **Observability** | Is the system healthy and performing within expectations? | SRE, Platform Engineers | Forward-looking, real-time |

---

## 2. Provenance

### 2.1 Definition

Provenance is the structural data lineage mechanism embedded in every field of every DCM payload. It is not a separate system — it is part of the data itself. Every field that can be created or modified by any DCM process carries provenance metadata alongside its value.

Provenance answers: "where did this value come from, what modified it, and why?"

Audit queries provenance to answer its questions. Observability does not use provenance directly — it operates on event streams and metrics.

### 2.2 Provenance Structure

See [Context and Purpose — Section 4.4](00-context-and-purpose.md) for the complete field-level provenance structure. The key elements:

```yaml
field_name:
  value: <current value>
  metadata:
    override: <allow|constrained|immutable>
    basis_for_value: <human-readable — why this value was set>
    baseline_value: <original default before any override>
    locked_by_policy_uuid: <uuid — if constrained or immutable>
    locked_at_level: <global|tenant|user>
  provenance:
    origin:
      value: <original value>
      source_type: <layer|policy|consumer|provider|discovery|rehydration>
      source_uuid: <uuid of originating entity>
      timestamp: <ISO 8601>
    modifications:
      - sequence: 1
        previous_value: <value before>
        modified_value: <value after>
        source_uuid: <uuid of modifying entity>
        operation_type: <enrichment|transformation|gatekeeping|lock|grant|rehydration>
        actor_uuid: <uuid of actor that caused this modification>
        timestamp: <ISO 8601>
        reason: <human-readable>
```

### 2.3 Provenance Obligations

Every DCM component that modifies data carries a provenance obligation — it must record its UUID, operation type, actor, timestamp, and reason for every field it touches. A component that modifies data without recording provenance violates the data model contract.

| Component | Provenance Obligation |
|-----------|----------------------|
| Request Payload Processor | Record source UUID and type for every field assembled from layers |
| Policy Engine | Record policy UUID, level, operation type, and reason for every field modified or locked |
| Service Provider (Denaturalization) | Record provider UUID and timestamp for every field in the realized payload |
| data store | Emit provenance event to Audit component on every write |
| Resource Discovery | Record provider UUID, timestamp, and method for every discovered field |
| Rehydration Pipeline | Record source store, source record UUID, rehydration reason, and actor UUID |

### 2.4 Provenance Across the Full Lifecycle

The provenance chain for a single field may span multiple lifecycle stages:

```
Base Layer sets encryption_standard: AES-128
  origin: {source_type: base_layer, source_uuid: layer-uuid-001}

Transformation Policy enriches to AES-256
  modification: {source_uuid: policy-uuid-001, operation: transformation,
                 reason: "Security standard requires AES-256 minimum"}

GateKeeper Policy locks as immutable
  modification: {source_uuid: policy-uuid-002, operation: lock,
                 reason: "CISO mandate — encryption standard non-negotiable"}

Provider reports realized value: AES-256
  modification: {source_uuid: provider-uuid-001, operation: denaturalization,
                 reason: "Provider confirmed encryption standard applied"}

Drift detected: discovered value AES-128
  modification: {source_uuid: discovery-uuid-001, operation: discovery,
                 reason: "Direct modification detected outside DCM lifecycle"}
```

The complete chain tells the full story of that field across its entire existence.

---

## 3. Audit

### 3.1 Definition

Audit is the compliance-grade, queryable record of all significant actions across the DCM lifecycle. It is backward-looking, human-readable, and access-controlled by persona. It answers: "what happened, who authorized it, can you prove it?"

Audit is a **separate component** — not a query against the GitOps stores, not a view into provenance directly. It aggregates and indexes provenance events from all stores and presents them through a structured query API surfaced by the DCM API Gateway.

### 3.2 Architecture

```
All data stores emit provenance events (contractual obligation)
  │
  │  Events include: entity_uuid, operation, actor_uuid,
  │  timestamp, payload_hash, store_reference
  ▼
Audit Component
  │  Receives provenance events from all stores
  │  Correlates events by entity_uuid across all stores
  │  Indexes for structured query: by entity, tenant, actor,
  │  time range, operation type, policy UUID
  │  Maintains immutable records — audit records are never modified
  │  Enforces long retention (regulatory periods — configurable,
  │  minimum 7 years for FSI deployments)
  │  Verifies payload hashes — detects store tampering
  ▼
DCM API Gateway
  │  Surfaces Audit query API with persona-based access control
  │  Auditor: full access — all entities, all tenants, all time
  │  SRE: full access within operational scope
  │  Admin: full access within administrative scope
  │  Consumer: own entities and requests only
  │  Provider: own provider's operations only
```

### 3.3 Audit API (via DCM API Gateway)

```
GET  /api/v1/audit/entities/{uuid}/history
     Returns: complete lifecycle history for an entity
     Fields: all state transitions, all provenance events, all actor actions

GET  /api/v1/audit/requests/{uuid}/provenance
     Returns: complete provenance chain for a specific request
     Fields: intent, assembly, policy evaluation, provider dispatch, realization

GET  /api/v1/audit/policies/{uuid}/evaluations
     Returns: all evaluations of a specific policy across all requests
     Fields: when it ran, what it did, which entities it affected

GET  /api/v1/audit/actors/{uuid}/activity
     Returns: all actions taken by a specific actor
     Fields: requests submitted, approvals given, policy evaluations triggered

GET  /api/v1/audit/tenants/{uuid}/activity
     Returns: all activity within a specific tenant
     Fields: requests, realizations, drift events, policy violations

POST /api/v1/audit/query
     Body: structured audit query with field filters, time range, pagination
     Returns: matching audit records
```

### 3.4 Audit Record Structure

```yaml
audit_record:
  audit_uuid: <uuid — immutable identifier for this audit record>
  entity_uuid: <entity UUID — links to all four states>
  tenant_uuid: <tenant UUID>
  event_type: <REQUEST_SUBMITTED|INTENT_CREATED|POLICY_EVALUATED|
               PROVIDER_DISPATCHED|RESOURCE_REALIZED|DRIFT_DETECTED|
               UNSANCTIONED_CHANGE|DECOMMISSIONED|REHYDRATED|...>
  timestamp: <ISO 8601>
  actor_uuid: <UUID of actor who triggered this event>
  actor_type: <consumer|policy|provider|sre|admin|automation>

  source_store:
    store_type: <gitops|event_stream|audit>
    store_uuid: <data store UUID>
    store_reference: <git commit hash | event ID | etc.>
    payload_hash: <hash of the payload at this store reference>

  provenance_summary:
    <condensed provenance — what changed, who did it, why>

  policy_context:
    policies_evaluated: [<policy UUIDs>]
    policies_applied: [<policy UUIDs>]
    policies_rejected: [<policy UUIDs with rejection reasons>]
    override_control_changes: [<field locks and grants applied>]

  related_records:
    intent_record_uuid: <uuid>
    requested_record_uuid: <uuid>
    realized_event_uuid: <uuid>
    rehydration_source_uuid: <uuid — if this is a rehydration>
```

### 3.5 Audit Integrity

Audit records are immutable. The Audit component verifies payload hashes against the data store's stored values on every read — if a hash mismatch is detected, the Audit component flags the record as potentially tampered and escalates to the Policy Engine.

The Audit Store itself is a data store with the highest consistency and durability requirements — linearizable consistency, synchronous replication, cryptographic payload hashing, and compliance-grade retention.

---

## 4. Observability

### 4.1 Definition

Observability is real-time insight into the health, performance, and behavior of the DCM system. It is forward-looking, machine-readable, and aggregated. It answers: "is the system healthy, where are the bottlenecks, what is the error rate?"

Observability is operationally oriented — SREs and platform engineers use it to understand system behavior and respond to incidents. It does not carry the compliance obligations of Audit.

### 4.2 The Three Pillars

**Metrics** — quantitative measurements of system state over time
- Request throughput: requests/second by resource type, tenant, provider
- Latency: assembly time, policy evaluation time, provider dispatch time, end-to-end time
- Error rates: policy rejection rate, provider failure rate, drift detection rate
- Capacity: provider utilization, store capacity, queue depth
- Cost: accumulated cost by tenant, resource type, provider

**Traces** — distributed traces of request execution across components
- Full request trace from Intent State creation through provider dispatch
- Policy evaluation trace — which policies ran, in what order, how long each took
- Assembly trace — which layers were applied, in what order, what each contributed

**Logs** — structured event logs from all DCM components
- Component startup and shutdown
- Registration events (provider registration, deregistration)
- Error conditions
- Drift detection events
- Unsanctioned change events

### 4.3 Architecture

```
DCM components emit metrics, traces, and logs
  │
  │  All telemetry in OpenTelemetry format
  │  Standardized metric names, trace context propagation,
  │  structured log format
  ▼
Observability Store
  │  Time-series metrics store (Prometheus-compatible)
  │  Distributed trace store (Jaeger/Zipkin compatible)
  │  Log aggregation (structured, indexed)
  │  Short-to-medium retention (configurable — typically 90 days)
  ▼
DCM API Gateway
  │  GET /api/v1/observability/metrics
  │  GET /api/v1/observability/traces/{request_uuid}
  │  GET /api/v1/observability/health
  │  GET /api/v1/observability/providers/{uuid}/performance
  ▼
Dashboards and alerting (external tooling)
  │  Grafana, DataDog, Splunk — implementor choice
  │  DCM provides OpenTelemetry-compatible telemetry
  │  Dashboards are deployment artifacts, not DCM artifacts
```

### 4.4 Standard DCM Metrics

```
# Request lifecycle
dcm_requests_total{resource_type, tenant, status}
dcm_request_duration_seconds{resource_type, stage}
dcm_requests_in_flight{resource_type, tenant}

# Policy Engine
dcm_policy_evaluations_total{policy_type, result}
dcm_policy_evaluation_duration_seconds{policy_type}
dcm_policy_rejections_total{policy_uuid, resource_type}

# Provider
dcm_provider_requests_total{provider_uuid, resource_type, status}
dcm_provider_response_duration_seconds{provider_uuid}
dcm_provider_capacity_available{provider_uuid, resource_type}
dcm_provider_health_status{provider_uuid}

# Drift
dcm_drift_detections_total{resource_type, severity}
dcm_unsanctioned_changes_total{resource_type, provider_uuid}
dcm_drift_resolution_duration_seconds{resolution_type}

# Storage
dcm_store_write_duration_seconds{store_type, store_uuid}
dcm_store_read_duration_seconds{store_type, store_uuid}
dcm_store_health_status{store_type, store_uuid}

# Rehydration
dcm_rehydrations_total{source_store, placement_mode, policy_version}
dcm_rehydration_duration_seconds{source_store}
```

### 4.5 Observability vs Audit — The Key Distinctions

| Dimension | Audit | Observability |
|-----------|-------|---------------|
| **Retention** | Regulatory period (years) | Operational window (days-months) |
| **Access control** | Strict persona-based | Operational teams |
| **Data volume** | Moderate — per-entity events | High — continuous time series |
| **Query model** | Structured, entity-centric | Aggregated, time-series |
| **Immutability** | Absolute — records never modified | Aggregated data may be downsampled |
| **Compliance** | Compliance-grade — hash-verified | Operational — best effort |
| **Use case** | Prove what happened | Understand what is happening |

---

## 5. The API Gateway — Unified Access

All three capabilities — Provenance (embedded in data), Audit (structured history), and Observability (operational telemetry) — are surfaced through the DCM API Gateway. There is no separate endpoint for audit or observability. All DCM capabilities live in a unified API hierarchy.

```
DCM API Gateway
  │
  ├── /api/v1/catalog/          # Service Catalog
  ├── /api/v1/requests/         # Request submission and management
  ├── /api/v1/entities/         # Entity lifecycle management
  ├── /api/v1/providers/        # Provider registration and management
  ├── /api/v1/policies/         # Policy management
  ├── /api/v1/audit/            # Audit queries
  ├── /api/v1/observability/    # Operational metrics and traces
  └── /api/v1/admin/            # Administrative functions
```

Persona-based access control is enforced at the API Gateway level for all endpoints. The same authentication and authorization model applies across the entire API surface.

---

## 6. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should the Audit Store be a specialized data store or can a general pipeline_events table satisfy the audit contract? | Architecture | ✅ Resolved — specialized PostgreSQL store contract; append-only; hash chain integrity; reference-based retention; compliance queries; see doc 11 (STO-004) |
| 2 | How are audit records replicated across sites in air-gapped or geographically distributed deployments? | Sovereignty | ✅ Resolved — live sync for Regional DCMs; signed bundle for Sovereign DCMs; sovereignty check required; hash chain preserved across transport (AUD-018) |
| 3 | Should DCM provide a default observability dashboard or only the telemetry? | Deployment | ✅ Resolved — default Grafana dashboard for minimal/dev/standard; enterprise integration recommended for prod; required for fsi; local-only for sovereign (OBS-002) |
| 4 | How does the Audit component handle provenance events from a data store that has been deregistered? | Operational | ✅ Resolved — two-stage model handles this; Commit Log independent of data stores; gap record inserted on Audit Store recovery; chain makes gap explicit (AUD-019) |

---

## 7. Related Concepts

- **Provenance** — field-level data lineage embedded in every DCM payload
- **Audit Store** — compliance-grade, immutable store of all audit records
- **Observability Store** — time-series metrics, traces, and logs
- **data store** — formal provider type for all DCM stores
- **API Gateway** — unified access point for all DCM capabilities including audit and observability
- **Drift Detection** — uses discovered vs realized state comparison; drift events feed the Audit component
- **Unsanctioned Change** — a specific audit event type triggered by unauthorized resource modification


## 7. Audit Provenance Observability Gap Resolutions

### 7.1 Audit Store Architecture (Q1)

Resolved as STO-004 in doc 11 (data stores). The Audit Store is a specialized PostgreSQL store contract — append-only with immutability enforcement, hash chain integrity, reference-based retention tracking, and compliance-grade multi-dimensional queries. The Event Stream is the delivery channel only, not the compliance destination.

### 7.2 Audit Record Replication Across Sites (Q2)

Each DCM instance maintains its own Audit Store. Replication uses live sync (Regional DCMs with connectivity) or signed bundle export (Sovereign DCMs without connectivity).

```yaml
audit_replication:
  model: <live_sync|signed_bundle|per_instance_only>

  live_sync:                        # Regional DCMs with Hub connectivity
    direction: regional_to_hub      # Regional pushes aggregated view to Hub
    filters:
      include: [SECURITY, GATEKEEPER_TRIGGERED, SOVEREIGNTY_VIOLATION]
    sovereignty_check: required     # before any replication

  signed_bundle:                    # Sovereign DCMs
    export_on: [scheduled, connectivity_window, on_demand]
    schedule: "0 0 * * 0"           # weekly during connectivity window
    encryption: required
    hash_chain_preserved: true      # chain integrity maintained across transport
    import_at: hub_dcm_audit_store

  per_instance_only:                # fully isolated Sovereign DCMs
    export_on_request: via_signed_bundle_manual_transfer
```

### 7.3 Default Observability Dashboard (Q3)

DCM ships a default Grafana-based observability dashboard for minimal/dev/standard profiles.

```yaml
default_observability_dashboard:
  implementation: grafana
  pre_built_dashboards:
    - dcm_overview              # request throughput, error rates, component health
    - resource_lifecycle        # entity state transitions, rehydration activity
    - policy_evaluation         # GateKeeper triggers, shadow results, validation failures
    - provider_health           # provider availability, capacity confidence, trust scores
    - audit_integrity           # hash chain status, pending forwards, chain breaks
    - federation_status         # federation tunnel health, cross-DCM traffic
  profile_behavior:
    minimal: included
    dev: included
    standard: included_optional         # shipped; organizations may substitute
    prod: integration_recommended       # integrate with enterprise observability
    fsi: integration_required
    sovereign: local_only               # local Grafana; no external connections
  export_formats: [prometheus, opentelemetry, json]
```

### 7.4 Audit Component Handling Failing data store (Q4)

The two-stage audit model handles this by design — the Stage 1 Commit Log (etcd) has no dependency on any data store.

```
store failure detected
  │
  ▼ Stage 1 Commit Log (etcd) — independent of data store
  │   Records: STORAGE_PROVIDER_FAILURE event immediately
  │
  ▼ Stage 2 Audit Forward Service — async, after recovery
  │   Forwards accumulated events including the failure event itself
  │
  ▼ For Audit Store self-failure specifically:
      Commit Log accumulates events as pending_forward
      On recovery: queue drains in order
      AUDIT_STORE_UNAVAILABLE gap record inserted with exact outage timestamps
      Hash chain makes the gap explicitly visible — not hidden
```

The gap record is not a failure — it is evidence of correct behavior. Auditors can see exactly when the Audit Store was unavailable and that no records were lost (all arrived after recovery).

### 7.5 System Policies — Audit Provenance Gaps

| Policy | Rule |
|--------|------|
| `STO-004` | The Audit Store is a specialized PostgreSQL store contract — append-only, hash chain integrity, reference-based retention, compliance-grade queries. Event Stream is the delivery channel only. (See doc 11) |
| `AUD-018` | Audit records are replicated using live sync (Regional DCMs) or signed bundle export (Sovereign DCMs). Sovereignty checks required before any replication. Hash chain integrity preserved across transport. Fully isolated Sovereign DCMs maintain local-only audit stores with manual export. |
| `OBS-002` | DCM ships a default Grafana-based observability dashboard for minimal/dev/standard profiles. Standard+ profiles may substitute enterprise platforms. FSI requires enterprise observability. Sovereign DCMs use local dashboard only with no external connections. |
| `AUD-019` | store failures are recorded via the Stage 1 Commit Log (etcd), which is independent of all data stores. Audit Store self-failures produce pending_forward records. On recovery, a gap record (AUDIT_STORE_UNAVAILABLE) is inserted with the outage window timestamps. The hash chain gap is explicit and auditable. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
