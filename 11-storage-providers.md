# DCM Data Model — Storage Providers



**Document Status:** ✅ Complete  
**Related Documents:** [Four States](02-four-states.md) | [Audit, Provenance, and Observability](12-audit-provenance-observability.md) | [Information Providers](10-information-providers.md)

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
> The Provider abstraction — Storage Provider capability extension



---

> **Operational guidance:** GitOps store-at-scale and migration are covered in [Operational Reference](41-operational-reference.md) Sections 1 and 2.

## 1. Purpose

A **Storage Provider** is the fourth formal DCM provider type. It is the interface through which DCM persists, retrieves, and streams all state data. DCM defines the contract — the characteristics, capabilities, and obligations each store must satisfy. The implementation technology is a deployment choice made by implementors.

This is consistent with DCM's governing framework philosophy: DCM does not prescribe technology. It defines what is required and what is guaranteed. An organization using GitHub and Kafka satisfies the same contracts as one using Gitea and EventStoreDB.

---

## 2. Storage Provider Sub-Types

Storage Providers are one of eleven DCM provider types (see [Unified Provider Contract](A-provider-contract.md)). Within the Storage Provider type, four storage sub-types are defined, each optimized for different access patterns and consistency requirements:

| Provider Type | Purpose | Data Direction | DCM Owns Result? |
|--------------|---------|---------------|-----------------|
| **Service Provider** | Realizes resources; may register Composite Services to deliver compound payloads | DCM → Provider → DCM | Yes |
| **Information Provider** | Serves external authoritative data | DCM → Provider (lookup) | No |
| **Storage Provider** | Persists and streams DCM state | DCM ↔ Provider | Yes — DCM is authoritative |

---

## 3. Storage Provider Contract — Base Requirements

All Storage Providers share these base contract requirements regardless of store type:

### 3.1 Registration
Same model as Service and Information Providers. Storage Providers register with DCM declaring their endpoint, store type, capabilities, and sovereignty characteristics.

```yaml
storage_provider_registration:
  uuid: <uuid>
  name: <provider name>
  display_name: <human-readable name>
  store_type: <gitops|write_once_snapshot|event_stream|search_index|audit|observability>
  version: <Major.Minor.Revision>
  endpoint: <base URL>
  capabilities: <list — store-type specific>
  sovereignty_constraints: <same model as all providers>
  trust_declaration: <same model as all providers>
  status: <active|deprecated|retired>
```

### 3.2 Health Check
Same model as all providers. `GET /health` endpoint, DCM polls on configurable interval.

### 3.3 Trust
Same model as all providers. DCM validates Storage Provider identity before writing or reading state data. A compromised Storage Provider is treated as a sovereignty incident.

### 3.4 Provenance Emission Obligation
Every Storage Provider that holds state data has a contractual obligation to emit provenance events to the Audit component when state is written or modified. This is not optional — it is part of the Storage Provider contract.

```yaml
# Provenance emission event — sent to Audit component on every write
provenance_emission:
  store_type: <store type>
  operation: <write|update|delete|merge|commit>
  entity_uuid: <entity UUID affected>
  record_uuid: <UUID of the specific record written>
  actor_uuid: <UUID of the actor that triggered the write>
  timestamp: <ISO 8601>
  payload_hash: <cryptographic hash of the written payload>
  store_reference: <store-specific reference — git commit hash, event ID, etc.>
```

### 3.5 Consistency Guarantee Declaration
Each Storage Provider must declare its consistency model in registration. DCM components read this declaration and adapt their behavior accordingly.

```yaml
consistency_declaration:
  consistency_model: <strong|eventual|linearizable>
  replication_factor: <integer>
  durability_guarantee: <fsync|replicated|acknowledged>
  max_data_loss_window: <duration — e.g., PT0S for zero data loss>
```

---

## 4. GitOps Store Contract

Used for: Intent State, Requested State, Layer Store, Policy Store

### 4.1 Required Capabilities

```yaml
gitops_capabilities:
  branching: true              # Branch-per-request support
  pull_request: true           # PR creation, review, merge
  immutable_history: true      # Commits are permanent
  ci_cd_hooks: true            # Webhook triggers on push/merge
  search_index_integration: true # Search Index companion required
  access_control: true         # Per-branch, per-path access control
  signed_commits: optional     # Recommended for audit integrity
```

### 4.2 Required API Operations

| Operation | Description | Used By |
|-----------|-------------|---------|
| `create_branch` | Create a new branch from main | Intent State creation |
| `commit_file` | Commit a file to a branch | Intent and Requested State write |
| `create_pr` | Open a Pull Request for review | Intent State review workflow |
| `merge_pr` | Merge an approved PR to main | Intent State approval |
| `get_file` | Retrieve a file by path or commit | State retrieval |
| `get_history` | Retrieve commit history for a path | Audit and rehydration |
| `trigger_ci` | Trigger CI pipeline on branch | Policy pre-validation |
| `trigger_cd` | Trigger CD pipeline on merge | Requested State assembly and dispatch |
| `post_comment` | Post a comment on a PR | CI pipeline result reporting |

### 4.3 File Structure Convention

```
{store_root}/
  tenants/
    {tenant_uuid}/
      {entity_uuid}/
        intent.yaml          # Intent State record
        # OR
        requested-state.yaml # Requested State record
```

### 4.4 Search Index Companion

Every GitOps store deployment requires a companion Search Index. The Search Index is a separate Storage Provider that maintains a queryable projection of the GitOps store. See Section 6.

---

## 5. Event Stream Store Contract

Used for: Realized State, Discovered State

### 5.1 Required Capabilities

```yaml
event_stream_capabilities:
  append_only: true            # Events are never modified or deleted
  entity_keyed_streams: true   # Each entity has its own event stream
  stream_replay: true          # Streams can be replayed from any offset
  entity_uuid_lookup: true     # O(1) lookup of stream by entity UUID
  at_least_once_delivery: true # Events are never silently lost
  configurable_retention: true # Retention period configurable per stream type
  distributed_replication: true # Data replicated across nodes
  high_throughput_write: true  # Optimized for machine-generated writes
```

### 5.2 Stream Naming Convention

```
dcm.realized.{entity_uuid}    # Realized State stream per entity
dcm.discovered.{entity_uuid}  # Discovered State stream per entity
dcm.audit.{tenant_uuid}       # Audit event stream per tenant
dcm.system                    # DCM system-level events
```

### 5.3 Required API Operations

| Operation | Description | Used By |
|-----------|-------------|---------|
| `append_event` | Append an event to an entity stream | Provider callbacks, discovery |
| `read_stream` | Read events from an entity stream from offset | State retrieval, drift detection |
| `read_latest` | Read the most recent event in a stream | Current state queries |
| `replay_stream` | Replay all events from beginning | Audit, historical reconstruction |
| `list_streams` | List streams matching a pattern | Tenant-level queries |
| `get_stream_metadata` | Get stream statistics and metadata | Health monitoring |

### 5.4 Event Envelope

Every event written to the Event Stream Store uses this envelope:

```yaml
event_envelope:
  event_uuid: <uuid>
  stream_id: <stream name>
  entity_uuid: <entity UUID>
  tenant_uuid: <tenant UUID>
  event_type: <DCM event type>
  sequence_number: <monotonic integer within stream>
  timestamp: <ISO 8601>
  schema_version: <Major.Minor.Revision>
  payload_hash: <cryptographic hash>
  payload: <event-specific payload in DCM Unified Data Model format>
  provenance:
    written_by_uuid: <UUID of component that wrote this event>
    triggered_by_request_uuid: <UUID of DCM request that caused this event>
    triggered_by_actor_uuid: <UUID of actor who initiated the action>
```

### 5.5 Retention Model

| Stream Type | Default Retention | Rationale |
|-------------|------------------|-----------|
| Realized State | Permanent | Complete audit trail required |
| Discovered State | Configurable window | Operational use only — older snapshots archived |
| Audit | Regulatory period (configurable — minimum 7 years for FSI) | Compliance requirement |

---


---

## 5a. Write-once Snapshot Store Contract (Realized Store)

The Realized Store is a **write-once snapshot store** — distinct from the Event Stream Store used for Discovered State. It holds complete entity state snapshots where every record is traceable to an authorized DCM request.

### 5a.1 Store Characteristics

The Realized Store occupies a middle ground between the GitOps store (structured, human-navigable, PR-mediated) and the Event Stream store (high-frequency, field-level events, ephemeral). The Realized Store is:

- **Write-once** — records are immutable after creation; a new record is created for each authorized state change
- **Snapshot-based** — each record is a complete entity state, not a field-level delta
- **Request-traceable** — every record has a non-nullable `corresponding_requested_state_uuid`
- **Moderate frequency** — written only on authorized changes (initial realization, consumer updates, approved provider updates), not on every event
- **Long-lived** — records persist for the full entity lifetime plus audit retention period

### 5a.2 Write Authorization Model

The Realized Store has a strictly controlled set of write sources. No component may write to the Realized Store without a corresponding Requested State record:

```yaml
realized_store_write_authorization:
  allowed_sources:
    - source_type: initial_realization
      trigger: provider_confirms_realization
      required: corresponding_requested_state_uuid (type: initial_realization)

    - source_type: consumer_update
      trigger: provider_confirms_targeted_delta
      required: corresponding_requested_state_uuid (type: consumer_update)

    - source_type: provider_update
      trigger: dcm_approves_provider_update_notification
      required: corresponding_requested_state_uuid (type: provider_update)

  explicitly_forbidden:
    - drift_detection          # drift only reads, never writes
    - discovery_cycles         # discovery writes to Discovered Store only
    - unsanctioned_changes     # unsanctioned changes remain drift events
    - direct_admin_writes      # no bypassing the request pipeline
```

**Enforcement:** The write authorization model is enforced at the Realized Store API level — not by convention. A write without a valid `corresponding_requested_state_uuid` is rejected with `401 Unauthorized`.

### 5a.3 Required Capabilities

```yaml
write_once_snapshot_store:
  write_once_enforcement: true       # writes without corresponding_requested_state_uuid rejected
  entity_uuid_keyed: true            # O(1) lookup by entity UUID
  snapshot_retention: per_entity     # all snapshots for an entity retained per retention policy
  point_in_time_query: true          # query state as of any timestamp
  supersession_chain: true           # each record knows predecessor and successor
  hash_chain_integrity: true         # each record hashes previous — tamper evident
  concurrent_write_handling: optimistic_lock  # retry on conflict, no silent overwrite
```

### 5a.4 Required API Operations

| Operation | Description |
|-----------|-------------|
| `write_snapshot(entity_uuid, payload, requested_state_uuid)` | Write new snapshot; validate non-null requested_state_uuid; return snapshot UUID |
| `get_current(entity_uuid)` | Return the most recent snapshot for entity |
| `get_at_timestamp(entity_uuid, timestamp)` | Return snapshot valid at given timestamp |
| `get_by_uuid(realized_state_uuid)` | Return specific snapshot |
| `list_history(entity_uuid)` | Return supersession chain for entity |
| `verify_chain(entity_uuid)` | Verify hash chain integrity for entity's snapshots |

### 5a.5 Retention Policy

Realized State snapshots are retained for the full entity lifecycle. After an entity is DECOMMISSIONED, snapshots are retained per the audit retention policy — the same policy that governs Audit Store records. The entity's final Realized State snapshot is preserved even after all preceding snapshots are archived.

### 5a.6 Relationship to the Audit Store

The Realized Store and Audit Store are complementary — not redundant:

| Aspect | Realized Store | Audit Store |
|--------|---------------|-------------|
| Content | Complete entity state snapshots | Atomic action records (who did what when) |
| Query pattern | "What was the state of X at time T?" | "Who changed X and why?" |
| Write frequency | Per authorized change | Per every DCM action |
| Hash chain | Per entity | Per instance |
| Rehydration source | Yes | No |

The Audit Store records the action. The Realized Store records the result. Both are required for complete auditability.

### 5a.7 Typical Implementations

| Scale | Implementation | Notes |
|-------|---------------|-------|
| Minimal / dev | SQLite or PostgreSQL single-instance | Simple; acceptable for evaluation |
| Standard | PostgreSQL with write-once constraints | Reliable; familiar operational model |
| Production | CockroachDB or PostgreSQL HA | Geo-distributed; strong consistency |
| FSI / Sovereign | PostgreSQL with HSM-backed encryption | Encryption at rest required |


## 6. Search Index Contract

Used for: Queryable projection of GitOps stores

### 6.1 Role and Authority

The Search Index is explicitly **non-authoritative**. If the Search Index and the GitOps store disagree on any record, the GitOps store wins unconditionally. The Search Index is a performance layer — it is never the source of truth.

The Search Index can be rebuilt from scratch from Git history at any time. This replaceability is a contract requirement — implementors must support full index rebuild from the GitOps store.

### 6.2 Required Indexed Fields

At minimum the Search Index must index these fields from Intent and Requested State records:

```yaml
indexed_fields:
  - entity_uuid          # Universal linking key
  - tenant_uuid          # Tenant ownership
  - resource_type_name   # e.g., Compute.VirtualMachine
  - resource_type_uuid   # Registry UUID
  - lifecycle_state      # Current state
  - provider_uuid        # Selected provider
  - created_timestamp    # When the record was created
  - updated_timestamp    # When the record was last updated
  - cost_center          # Business context (if declared)
  - business_unit_uuid   # Business context (if declared)
  - git_path             # Path in GitOps store — used to retrieve full record
  - git_commit_hash      # Specific commit — used for point-in-time retrieval
```

### 6.3 Required Query Operations

| Operation | Example | Used By |
|-----------|---------|---------|
| `find_by_entity_uuid` | Find all records for entity xyz | Rehydration, audit |
| `find_by_tenant` | All entities for Tenant A | Tenant management |
| `find_by_resource_type` | All VMs across all tenants | Catalog reporting |
| `find_by_lifecycle_state` | All PENDING entities | Operational monitoring |
| `find_by_field` | All entities with cost_center=BU-PAY | FinOps reporting |
| `full_text_search` | Search across all indexed text fields | Discovery, debugging |
| `count_by_field` | Count entities grouped by resource_type | Analytics |

---

## 7. DCM-Internal Caches

DCM may maintain internal performance caches between components and stores. These are not Storage Providers — they are internal implementation details that do not require external registration or trust.

### 7.1 Cache Characteristics

- **Non-authoritative** — explicitly marked. Cache hits are not treated as ground truth.
- **Cache-aside pattern** — DCM checks cache first; on miss, reads from authoritative store and populates cache
- **Invalidation on write** — any write to an authoritative store invalidates the corresponding cache entry
- **Bounded staleness** — maximum staleness window configured per cache; entries older than the window are treated as misses
- **Rebuildable** — any cache can be cleared and rebuilt from its authoritative store

### 7.2 Candidate Cache Locations

| Cache | Authoritative Source | Purpose |
|-------|---------------------|---------|
| Layer Cache | Layer Store (Git) | Avoid repeated Git reads for frequently used layers |
| Policy Cache | Policy Store (Git) | OPA policy bundles cached in Policy Engine memory |
| Catalog Cache | Catalog Store (Git) | Service catalog items cached for presentation |
| Provider Registry Cache | Provider Registry | Registered provider list cached for routing |
| Search Index | GitOps stores | Queryable projection (also functions as a cache) |

---

## 8. Storage Provider vs Service Provider — Key Differences

| Dimension | Service Provider | Storage Provider |
|-----------|-----------------|-----------------|
| **Purpose** | Realizes resources | Persists DCM state |
| **Data direction** | DCM sends, provider executes | DCM reads and writes |
| **Naturalization** | Required — DCM format → native | Not required — DCM format throughout |
| **Denaturalization** | Required — native → DCM format | Not required |
| **Provenance emission** | Required (realized state) | Required (all writes) |
| **Capacity model** | Resource capacity | Storage capacity and throughput |
| **Health model** | Is provider healthy? | Is store reachable and consistent? |

---

## 9. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should Storage Providers support multi-region replication as a declared capability? | Sovereignty | ✅ Resolved — declared capability in registration; Profile determines minimum (STO-001) |
| 2 | How are Storage Provider failures handled — failover, queuing, or rejection? | Reliability | ✅ Resolved — per store type: Commit Log aborts; GitOps queues; Event Stream queues; Audit accumulates; Search degrades (STO-002) |
| 3 | Should the Search Index be a separate registered Storage Provider or bundled with the GitOps store? | Architecture | ✅ Resolved — separate sub-type; non-authoritative; rebuildable (STO-003) |
| 4 | How does the Storage Provider model interact with air-gapped environments? | Sovereignty | ✅ Resolved — sovereignty_declaration on all providers; air_gap_capable flag; offline registry; signed bundles (SOV-001) |

---


## 10. Storage Architecture — Q79 through Q83

### 10.1 Git Repository Structure — Intent and Requested Stores (Q79)

GitOps stores use a deterministic handle-based directory structure. Every artifact lives at a path derivable from its identity — human-navigable, diff-readable, and independently verifiable without DCM tooling.

```
dcm-intent/                              ← Intent Store repository
  tenants/
    {tenant-uuid}/
      requests/
        {request-uuid}/
          intent.yaml                    ← Consumer's original submission
          metadata.yaml                  ← Timestamp, actor, ingress block

dcm-requested/                           ← Requested Store repository
  tenants/
    {tenant-uuid}/
      requests/
        {request-uuid}/
          requested-payload.yaml         ← Fully assembled, policy-processed payload
          assembly-provenance.yaml       ← Layer chain, policy evaluation results
          placement.yaml                 ← Selected provider, placement constraints
          dependencies/
            {dependency-uuid}/
              requested-payload.yaml     ← Each dependency's assembled payload

dcm-layers/                              ← Layer Store repository
  {domain}/
    {concern-or-type}/
      {name}/
        v{Major}.{Minor}.{Revision}.yaml

dcm-policies/                            ← Policy Store repository
  {domain}/
    {concern-or-type}/
      {name}/
        v{Major}.{Minor}.{Revision}.yaml
```

**Tenant isolation:** Each Tenant's requests live under their `{tenant-uuid}` directory. Access control is enforced at the DCM API layer — the Git repository uses DCM's service account for all reads/writes. Individual Tenants never have direct Git access.

**Branching model:** `main` is the authoritative branch. No feature branches for operational stores — all writes go directly to `main` via the DCM service account. The Git history IS the audit trail for the GitOps stores.

**Repository count:**
- `minimal` and `dev` profiles: monorepo (all four stores in one repository — simpler, single backup target)
- `standard` and above: separate repositories per store type (cleaner governance boundaries, independent scaling, independent access control)

**System policy (STO-005):** GitOps stores use a handle-based directory structure. `main` is authoritative. Minimal/dev may use monorepo; standard+ should use separate repos.

### 10.2 Multi-Region Replication Capability Declaration (Q80)

Storage Providers declare their replication capabilities in their registration. The active Profile determines the minimum replication requirement.

```yaml
storage_provider_registration:
  capabilities:
    replication:
      multi_region: true
      supported_regions: [eu-west-1, eu-west-2, us-east-1]
      replication_modes: [active_active, active_passive]
      consistency_model: <eventual|strong|bounded_staleness>
    redundancy:
      replicas: 3
      write_quorum: 2
      zone_spread: required
    backup:
      automated: true
      schedule: "0 */6 * * *"
      retention: P30D
      cross_region: true
```

**Profile minimum replication requirements:**

| Profile | Multi-Region | Min Replicas | Consistency |
|---------|-------------|-------------|------------|
| `minimal` | No | 1 | Any |
| `dev` | No | 1 | Any |
| `standard` | No | 3 | Strong or bounded |
| `prod` | Yes | 3 | Strong |
| `fsi` | Yes | 5 | Strong |
| `sovereign` | Yes (within boundary) | 5 | Strong |

For `sovereign` profile: `multi_region: true` is required but all regions must be within the declared sovereignty boundary. Cross-boundary replication is blocked by sovereign policy groups.

**System policy (STO-001):** Storage Providers must declare replication capabilities. Active Profile determines minimum requirements. Providers not meeting Profile minimum cannot be activated for that Profile's stores.

### 10.3 Storage Provider Failure Handling (Q81)

Failure behavior is declared per store type and governed by the active Profile.

```yaml
storage_failure_policy:
  commit_log:
    on_quorum_unavailable: abort_operation      # hard — no silent changes
    on_minority_failure: continue               # transparent via Raft
  gitops_store:
    on_unavailable: queue_writes                # local buffer; serve reads from cache
    max_queue_size: 10000
    max_queue_age: PT1H                         # reject if queued > 1 hour
    on_queue_exhausted: reject                  # explicit rejection — not silent drop
  event_stream:
    on_unavailable: queue_locally               # producer-side queuing
    consumer_behavior: resume_from_offset       # no data loss on recovery
  audit_store:
    on_unavailable: accumulate_in_commit_log    # two-stage audit handles this
    max_accumulation_age: P7D                   # alert if pending > 7 days
  search_index:
    on_unavailable: serve_degraded              # warn + direct to authoritative
    on_recovery: rebuild_from_authoritative     # full index rebuild
```

**By store type:**
- **Commit Log:** Quorum unavailable → operation aborted. Minority failure → continues via Raft reelection.
- **GitOps Stores:** Unavailable → writes queue locally; reads serve from cache. Queue exhausted → explicit rejection.
- **Event Stream (Discovered Store):** Producer queues locally. Consumer resumes from last committed offset on recovery. No data loss.
- **Write-once Snapshot Store (Realized Store):** Writes queue locally with the same WAL pattern as the Audit Store. Write retry on recovery. Rejected writes (missing requested_state_uuid) are never retried — they are logged as security events.
- **Audit Store:** Two-stage model — Commit Log accumulates `pending_forward` entries. Operations not blocked.
- **Search Index:** Non-authoritative. Unavailable → degraded response + reference to authoritative store. Recovery → full index rebuild.

`fsi` and `sovereign` profiles tighten GitOps failure policy: write buffer age limit drops to PT15M; queue exhaustion triggers platform alert and operator notification.

**System policy (STO-002):** Storage Provider failure behavior declared per store type and governed by Profile. GitOps unavailability queues writes — does not silently drop. Commit Log quorum loss aborts operation. Audit Store unavailability accumulates in Commit Log. Search Index unavailability degrades queries without impacting writes.

### 10.4 Search Index — Separate Storage Provider Sub-Type (Q82)

The Search Index is a **separate Storage Provider sub-type** distinct from GitOps stores. Treating them as the same type would obscure the critical distinction: GitOps stores are authoritative and cannot be lost; the Search Index is non-authoritative and rebuildable.

```yaml
search_index_provider:
  provider_type: search_index              # distinct sub-type of storage_provider
  implementation: elasticsearch           # or: opensearch
  authoritative: false                    # explicitly non-authoritative
  rebuildable_from: [gitops_store, event_stream]
  rebuild_trigger: <on_failure|on_demand|scheduled>
  rebuild_schedule: "0 3 * * 0"          # weekly full rebuild
  consistency_lag: PT5M                   # acceptable lag behind authoritative stores
```

**Indexing model:** DCM control plane emits index update events on every authoritative store write. Search Index Storage Provider consumes these events and updates incrementally. On failure, rebuilds from authoritative stores.

**API freshness:** Queries may specify `freshness: authoritative` to bypass the index and query the GitOps store directly for guaranteed-current results.

**System policy (STO-003):** Search Index is a separate Storage Provider sub-type — non-authoritative, rebuildable, distinct backend from GitOps. API queries may specify `freshness: authoritative` to bypass the index.

### 10.5 Audit Store — Specialized Storage Provider Sub-Type (Q83)

The Audit Store is a **specialized Storage Provider sub-type** with compliance properties no general Event Stream Store satisfies:

- **Append-only with immutability enforcement** — records cannot be modified or deleted while retention obligations apply
- **Hash chain integrity** — maintains and verifies the per-entity hash chain (AUD-006)
- **Reference-based retention tracking** — tracks entity lifecycle states for retention eligibility (AUD-003)
- **Compliance-grade query** — multi-dimensional queries by entity_uuid, actor_uuid, action, timestamp range, tenant_uuid

The Event Stream (Kafka) is the **delivery channel** to the Audit Store — transient, cleared after Audit Store confirms receipt. The Audit Store is the **compliance destination** — permanent for the duration of retention obligations.

```yaml
audit_store_provider:
  provider_type: audit_store             # specialized sub-type of storage_provider
  implementation: elasticsearch          # or: opensearch
  authoritative: true
  append_only_enforced: true
  hash_chain_verification: true
  retention_tracking: reference_based
  query_capabilities:
    - entity_uuid
    - actor_uuid
    - action
    - timestamp_range
    - tenant_uuid
    - request_uuid
    - retention_status
    - ingress_surface
    - auth_provider_type
  compliance_certifications: [SOC2, ISO-27001, PCI-DSS]
```

```
Commit Log → Audit Forward Service → Event Stream → Audit Store
(Stage 1)    (enrichment + hash)     (delivery)     (compliance storage)
```

**System policy (STO-004):** Audit Store is a specialized Storage Provider sub-type — append-only, hash chain integrity, reference-based retention, compliance-grade queries. Event Stream is the delivery channel only.

---

## 11. Provider Sovereignty Declaration

### 11.1 Obligation

Every provider registration — Service Provider, Information Provider, Message Bus Provider, Policy Provider, and Auth Provider — must include a `sovereignty_declaration` block. This is a contractual obligation, not optional metadata. DCM uses sovereignty declarations to make placement decisions, enforce Tenant sovereignty requirements, and detect drift between declared and actual posture.

### 11.2 Sovereignty Declaration Structure

```yaml
sovereignty_declaration:
  # JURISDICTIONAL DATA
  operating_jurisdictions:
    - country: DE
      legal_system: eu_gdpr
      data_center_location: Frankfurt
    - country: FR
      legal_system: eu_gdpr
      data_center_location: Paris
  # Does data ever transit through other jurisdictions?
  data_transit_jurisdictions: []          # empty = data stays in declared jurisdictions
  data_residency_guarantee: true          # data never leaves declared jurisdictions
  
  # LEGAL FRAMEWORKS
  legal_frameworks: [eu_gdpr, eu_nis2]
  excluded_frameworks: []                 # frameworks this provider explicitly cannot support

  # EXTERNAL DEPENDENCIES — does the provider require external connectivity?
  external_dependencies:
    air_gap_capable: false               # true = can operate without external connectivity
    external_services:
      - service: licensing_server
        jurisdiction: US
        data_shared: [license_key, hostname]
      - service: telemetry_endpoint
        jurisdiction: US
        data_shared: [usage_metrics]
    opt_out_available:
      telemetry: true                    # telemetry can be disabled

  # THIRD-PARTY SUB-PROCESSORS
  sub_processors:
    - name: "Acme Cloud Storage"
      jurisdiction: US
      data_handled: [vm_disk_images]
      gdpr_dpa_in_place: true

  # GOVERNMENT ACCESS RISK
  government_access_risk:
    jurisdictions_with_compelled_access: [US]
    # US CLOUD Act, FISA Section 702, etc.
    legal_challenge_policy: notify_customer_where_legally_permitted

  # CERTIFICATIONS — with validity periods
  certifications:
    - name: ISO-27001
      issuer: BSI
      valid_from: "2024-03-01"
      expires_at: "2027-03-01"
      scope: "Cloud Infrastructure Operations"
      certificate_ref:
        credential_provider_uuid: <uuid>
        path: "dcm/providers/kubevirt/certs/iso27001"
    - name: SOC2-Type-II
      issuer: Deloitte
      valid_from: "2025-01-01"
      expires_at: "2026-01-01"
      scope: "Infrastructure as a Service"

  # AUDIT RIGHTS
  audit_rights:
    customer_audit_right: true
    audit_notice_days: 30
    third_party_audit_accepted: true

  # CHANGE NOTIFICATION OBLIGATION
  change_notification:
    # Provider MUST notify DCM when any sovereignty data changes
    notification_endpoint: <provider's DCM notification webhook>
    # Changes that MUST be notified:
    mandatory_notification_events:
      - certification_expiry
      - new_jurisdiction_added
      - jurisdiction_removed
      - new_sub_processor
      - sub_processor_removed
      - new_external_dependency
      - government_access_event
    notification_sla: PT24H              # must notify within 24 hours of change
```

### 11.3 Change Notification and DCM Response

When a provider notifies DCM of a sovereignty change (or DCM discovers one via periodic verification):

```
Provider sovereignty change detected
  │
  ▼
Policy Engine evaluates: does the change violate any Tenant's
sovereignty requirements for resources currently placed with this provider?
  │
  ├── No violations:
  │     Update sovereignty record
  │     Emit: provider.sovereignty_changed webhook event
  │     Notify: affected Tenants (informational)
  │
  └── Violations found — for each affected resource:
        Policy determines action:
          notify_only       — inform Tenant; no automatic action
          pause             — suspend resource; Tenant must act
          migrate           — Provider-Portable Rehydration to compliant provider
          emergency_migrate — immediate parallel provisioning; decommission after
        Record: sovereignty_violation_record (in Audit Store)
        Notify: Tenant owner, platform admin, data_protection_officer (if declared)
```

### 11.4 Sovereignty Violation Record

```yaml
sovereignty_violation_record:
  record_uuid: <uuid>
  detected_at: <ISO 8601>
  detection_method: <provider_notification|periodic_verification|drift_detection>
  provider_uuid: <uuid>
  change_type: <certification_expired|new_jurisdiction|new_sub_processor|...>
  previous_value: <what was declared>
  new_value: <what changed>
  affected_resources:
    - entity_uuid: <uuid>
      tenant_uuid: <uuid>
      sovereignty_requirement_violated: "Data must not transit US jurisdiction"
      policy_action: migrate
      migration_request_uuid: <uuid>   # if migrate or emergency_migrate
  notifications_sent:
    - recipient: tenant_owner
    - recipient: platform_admin
    - recipient: data_protection_officer
```

### 11.5 Auto-Migration

Auto-migration (`migrate` or `emergency_migrate` policy action) uses Provider-Portable Rehydration:

```
Sovereignty violation detected → policy declares: migrate
  │
  ▼
DCM assembles migration request:
  │  Same entity declaration — new placement constraints
  │  Placement engine excludes non-compliant provider from candidate set
  │  Selects compliant alternative provider
  │
  ▼
emergency_migrate: parallel provisioning
  │  New resource provisioned BEFORE old one decommissioned
  │  Traffic/workload cutover coordinated with Tenant
  │
standard migrate: sequential
  │  Old resource suspended → new resource provisioned → old decommissioned
  │
  ▼
Full audit trail: sovereignty_violation_record links to migration request
```

### 11.6 System Policies — Provider Sovereignty

| Policy | Rule |
|--------|------|
| `SOV-001` | All provider registrations must include a `sovereignty_declaration` block covering operating_jurisdictions, legal_frameworks, data_residency_guarantees, external_dependencies, certifications with validity periods, and government_access_risk. |
| `SOV-002` | Providers must notify DCM when any declared sovereignty data changes. Sovereignty change notifications are treated as discovered drift and trigger Policy Engine re-evaluation. Notification SLA is declared in the provider registration. |
| `SOV-003` | When a provider sovereignty change violates a Tenant's sovereignty requirements, the Policy Engine evaluates affected resources and applies the declared action: notify_only, pause, migrate, or emergency_migrate. |
| `SOV-004` | Auto-migration triggered by SOV-003 uses Provider-Portable Rehydration. The non-compliant provider is excluded from the placement candidate set. The migration is a first-class DCM operation with full audit trail. |
| `SOV-005` | Certification validity periods are tracked by DCM. Certifications expiring within P30D trigger a warning notification to the provider and affected Tenants. Expired certifications trigger SOV-003 re-evaluation. |

---

## 12. System Policies — Storage Architecture

| Policy | Rule |
|--------|------|
| `STO-001` | Storage Providers must declare replication capabilities. Active Profile determines minimum replication requirements. Providers not meeting Profile minimum cannot be activated for that Profile's stores. |
| `STO-002` | Storage Provider failure behavior is declared per store type and governed by the active Profile. GitOps unavailability queues writes locally — does not silently drop. Commit Log quorum loss aborts the triggering operation. Audit Store unavailability accumulates entries in the Commit Log. Search Index unavailability degrades query responses without impacting write operations. |
| `STO-003` | The Search Index is a separate Storage Provider sub-type — non-authoritative and rebuildable. API queries may specify `freshness: authoritative` to bypass the index. |
| `STO-007` | The Realized Store is a write-once snapshot store. Every write requires a non-nullable corresponding_requested_state_uuid. Drift detection, discovery cycles, and unsanctioned provider changes do not write to the Realized Store. Enforcement is at the store API level, not by convention. |
| `STO-008` | The Intent Store requires a GitOps implementation. The Requested Store requires write-once semantics; GitOps is the reference implementation; write-once document stores are supported for production scale. |
| `STO-004` | The Audit Store is a specialized Storage Provider sub-type — append-only, hash chain integrity, reference-based retention, compliance-grade queries. The Event Stream is the delivery channel only. |
| `STO-005` | GitOps stores use a handle-based directory structure. The main branch is authoritative. Minimal and dev profiles may use a monorepo; standard and above should use separate repositories per store type. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
