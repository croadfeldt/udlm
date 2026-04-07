# DCM Data Model — The Four States



**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Entity Relationships](09-entity-relationships.md) | [Storage Providers](11-storage-providers.md) | [Audit, Provenance, and Observability](12-audit-provenance-observability.md)

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
> The Data abstraction — four lifecycle stages and their storage models



---

## 1. Purpose

The four states are the foundational model for how DCM tracks the complete lifecycle of any resource or service. Every entity in DCM exists in one or more of these states simultaneously. The states are not sequential stages — they are parallel, independently maintained records that together provide a complete, auditable picture of what was requested, what was approved, what was built, and what actually exists.

The four states answer four distinct questions:

| State | Question Answered | Data Domain |
|-------|------------------|-------------|
| **Intent State** | What did the consumer ask for? | `intent_records` — append-only, immutable |
| **Requested State** | What was approved and dispatched to the provider? | `requested_records` — append-only, immutable |
| **Realized State** | What did the provider actually build? | `realized_entities` — versioned snapshots, `is_current` flag |
| **Discovered State** | What does DCM observe actually existing right now? | `discovered_records` — ephemeral, refreshed per discovery run |

> **Infrastructure note (doc 51):** All four data domains are stored in a single PostgreSQL-compatible database. The logical distinctions (immutability rules, versioning model, query patterns) are preserved via table design, `REVOKE UPDATE/DELETE`, and RLS. Git, Kafka, and Redis are optional deployment enhancements, not architectural requirements. See [51-infrastructure-optimization.md](51-infrastructure-optimization.md).

---

## 2. State Definitions

### 2.1 Intent State

The **Intent State** is the immutable record of a consumer's original declaration. It is captured at the moment a request is submitted — before any layer assembly, before any policy evaluation, before any provider selection.

**Characteristics:**
- Immutable once created — the consumer's original intent is never modified
- Stored in a GitOps store — branched, reviewed, merged
- The CI/CD pipeline operates on the Intent State — policy pre-validation, cost estimation, sovereignty check, approval workflow
- Versioned via Git history — every revision of an intent is traceable
- Supports human review and debate via the PR mechanism
- The entity UUID is assigned at Intent State creation — it follows the entity through all subsequent states

**When created:** Every request submission, every rehydration operation, every drift remediation authorization

**Content:** The consumer's raw declaration in DCM Unified Data Model format — what they want, not what will be built

### 2.2 Requested State

The **Requested State** is the fully assembled, policy-processed, provider-ready payload. It is produced by the Request Payload Processor from the Intent State — after layer assembly, after all policy evaluation, after provider selection.

**Characteristics:**
- Immutable once created — a new Requested State is created for each request cycle
- Stored in a GitOps store — committed, versioned, triggering CD pipeline
- The CD pipeline dispatches from the Requested State to the provider
- Contains the complete assembled payload with full field-level provenance
- Contains the results of all policy evaluations — which policies ran, what they did, what they locked
- Contains provider selection — which provider will realize this request
- Is the authoritative record of what DCM instructed a provider to build

**When created:** After Intent State approval (merge), after successful policy processing

**Content:** The complete assembled payload in DCM Unified Data Model format, with full provenance chain, policy evaluation results, provider selection, and override control metadata

### 2.3 Realized State

The **Realized State** is the provider-confirmed record of what was actually built. It is produced by the provider after successful realization — the denaturalized result of the provider's execution, translated back to DCM Unified Data Model format.

**Characteristics:**
- Write-once complete snapshots — each Realized State record is a full entity state, never modified after writing
- Every Realized State record is traceable to exactly one Requested State record — no exceptions
- Stored in a realized_entities table keyed by entity UUID
- Contains provider-specific details not in the Requested State — assigned IPs, generated passwords, actual storage sizes, provider-internal IDs
- Is the authoritative record of what actually exists from DCM's perspective
- Drift is detected by comparing the most recent Realized State snapshot against Discovered State
- Carries a supersession chain — each snapshot knows which snapshot it superseded and which superseded it

**Three write sources (all require a corresponding Requested State record):**

| Source | Requested State record type | Example |
|--------|---------------------------|---------|
| Initial realization | `initial_realization` | Consumer provisions a new VM |
| Consumer update request | `consumer_update` | Consumer patches an editable field |
| Provider update notification | `provider_update` | Provider reports an authorized state change (auto-healing, maintenance) |

**What does NOT write to the Realized Store:**
- Drift detection — drift only compares, never writes
- Discovery cycles — discovery writes to Discovered Store only
- Unsanctioned provider changes — these are drift events until DCM evaluates and explicitly approves them

**When created:** When a provider confirms realization of any authorized request (initial, consumer update, or approved provider update notification)

**Content:** Complete entity state snapshot in DCM Unified Data Model format, with provider-added fields, full field-level provenance including provider attribution, and supersession chain references

### 2.4 Discovered State

The **Discovered State** is what DCM observes actually existing through active discovery — polling providers, querying Kubernetes APIs, interrogating infrastructure. It is the ground truth of what physically exists, independent of what DCM thinks exists.

**Characteristics:**
- Append-only snapshot stream — each discovery cycle produces a new snapshot
- Stored in an pipeline_events table (ephemeral) — recent history retained, older snapshots archived or discarded
- High-frequency and machine-generated — not appropriate for human review
- Used exclusively for drift detection — comparing against Realized State
- May contain resources DCM did not provision — brownfield resources discovered for ingestion

**When created:** On every discovery cycle, on demand for specific entities

**Content:** Raw discovered resource state in DCM Unified Data Model format, with discovery metadata (timestamp, discovery method, provider interrogated)


### 2.5 Recovery States

Five additional states apply to Infrastructure Resource Entities when the normal provisioning lifecycle encounters timeouts, cancellation failures, or partial realization. These states are governed by Recovery Policies (see [Operational Models](24-operational-models.md) Section 5).

| State | Meaning | Entry Trigger |
|-------|---------|--------------|
| `TIMEOUT_PENDING` | Dispatch timeout fired; cancellation sent to provider | `DISPATCH_TIMEOUT` recovery trigger |
| `LATE_REALIZATION_PENDING` | Provider responded after timeout; NOTIFY_AND_WAIT active | `LATE_RESPONSE_RECEIVED` recovery trigger |
| `INDETERMINATE_REALIZATION` | State ambiguous; drift detection resolving | `DRIFT_RECONCILE` recovery action |
| `COMPENSATION_IN_PROGRESS` | Compound service rollback underway | `PARTIAL_REALIZATION` trigger |
| `COMPENSATION_FAILED` | Rollback itself failed; orphaned resources possible | Compensation step failure |

See [Operational Models](24-operational-models.md) for the complete recovery state machine and Recovery Policy model.


---

## 3. The Entity UUID — Universal Linking Key

Every entity has a single UUID assigned at Intent State creation. This UUID is the universal key linking the entity across all four states and all stores:

```
Intent Store:    file path includes entity_uuid, content declares entity_uuid
Requested Store: file path includes entity_uuid, content declares entity_uuid
Realized Store:  event stream keyed by entity_uuid
Discovered Store: snapshot stream keyed by entity_uuid (matched via provider labels)
Audit Store:     all provenance events indexed by entity_uuid
Search Index:    entity_uuid → git_path mapping for Git stores
```

Given an entity UUID, DCM can reconstruct the complete history of that entity across its entire lifecycle — from the consumer's original intent through every state transition to the current discovered state.

---

## 4. Physical Representation — Data Domain Model

All four states are stored in DCM's PostgreSQL-compatible database as distinct data domains. Each domain has specific immutability rules, access patterns, and enforcement mechanisms — but they share a single infrastructure dependency. See [Infrastructure Requirements](51-infrastructure-optimization.md) for the prescribed infrastructure model and [Data Store Contracts](#41-data-store-contracts) below for the enforcement rules.

Git is available as an optional ingress adapter — consumers who prefer PR-based workflows can submit intent via Git. But Git is an ingress path, not a state store. DCM's state lives in PostgreSQL.

### 4.1 Data Store Contracts

Each data domain enforces its contract through PostgreSQL-native mechanisms:

| Domain | Table | Immutability | Enforcement |
|--------|-------|-------------|-------------|
| **Intent** | `intent_records` | Append-only — new intent creates a new row, previous intents never modified | `REVOKE UPDATE, DELETE` on table; RLS per tenant |
| **Requested** | `requested_records` | Append-only — each policy evaluation produces a new version with full provenance | `REVOKE UPDATE, DELETE` on table; RLS per tenant |
| **Realized** | `realized_entities` | Versioned snapshots — each state change creates a new row with `is_current` flag | Append-on-change semantics; `is_current` enforces single latest; RLS per tenant |
| **Discovered** | `discovered_records` | Ephemeral — each discovery run produces fresh snapshots; previous runs retained for trend analysis | Grouped by `discovery_run_uuid`; RLS per tenant |

**Pipeline events** flow between control plane services via the `pipeline_events` table with PostgreSQL `LISTEN/NOTIFY` for real-time routing. For high-throughput deployments, Kafka can be added alongside as an optional enhancement.

**Audit records** are stored in `audit_records` with a SHA-256 hash chain (each record's hash includes the previous record's hash), append-only enforcement (`REVOKE UPDATE, DELETE` + trigger-based immutability guard), and per-entity chain sequence numbers.

### 4.2 Realized State Snapshot Model

The Realized domain uses a **snapshot model** — each record is a complete entity state, not a delta. This makes rehydration a direct lookup rather than an event replay, and point-in-time queries ("what was the state on March 15?") are direct lookups.

```yaml
realized_state_snapshot:
  realized_uuid: <uuid>                  # this snapshot's identity
  entity_uuid: <uuid>                    # stable entity identity across versions
  realized_at: <ISO 8601>

  # Always traceable to a request — mandatory, not nullable
  source_type: <initial_realization|consumer_update|provider_update>
  request_uuid: <uuid>

  # Versioning
  version_major: <int>
  version_minor: <int>
  version_revision: <int>
  is_current: <boolean>                  # only one current per entity_uuid

  # Complete entity state at this point — all fields, all provenance
  fields:
    # [full entity state in DCM Unified Data Model format]

  # Provider-added fields
  provider_metadata:
    provider_entity_id: <string>
    provider_reported_at: <ISO 8601>
```

**Why snapshots instead of events:** Rehydration requires a complete entity state, not a replay of field-level events. The Realized domain is written only when an authorized change completes — it does not need high-frequency write throughput.

### 4.3 Query and Caching

For read-heavy workloads (catalog browsing, placement lookups, resource listing), PostgreSQL materialized views provide derived projections optimized for specific query patterns. These views are explicitly non-authoritative — the base tables always win if a view and a table disagree.

For deployments requiring geographically distributed read performance, Redis can be added as an optional caching layer in front of materialized views.

---

## 5. Rehydration

Rehydration is the process of using a previously stored state record as the starting point for a new request. It is not a shortcut around governance — **all relevant governance policies always apply regardless of rehydration source.** Rehydration is a new request that happens to start from a known prior state.

### 5.1 Three Rehydration Sources

**From Intent State:**
- The consumer's original declaration is replayed
- Full layer assembly runs — current layers applied
- All governance policies run — current policies applied
- Provider selection runs fresh
- Most likely to produce a different result than the original — policies and layers may have changed
- Use cases: upgrade resource to current standards, apply new sovereignty constraints, environment refresh

**From Requested State:**
- The previously assembled, policy-processed payload is loaded
- Layer assembly is skipped — layers were already applied
- All governance policies run — current policies applied
- Provider selection: configurable via flag (see Section 5.3)
- Use cases: reproduce a resource as closely as possible to the approved specification

**From Realized State:**
- The provider-confirmed realized payload is loaded
- Provider-specific fields are stripped — DCM unified format only
- Layer assembly is skipped
- All governance policies run — current policies applied
- Provider selection: configurable via flag
- Use cases: exact reproduction for disaster recovery, environment cloning, replacing a failed resource

### 5.2 The Common Governance Pipeline

Regardless of rehydration source, all requests flow through the same governance pipeline:

```
Rehydration source selected and loaded
  │
  │  Source payload becomes the basis for a new Intent State record
  │  New entity UUID assigned (or existing UUID preserved — policy decision)
  │  Rehydration provenance recorded: source_store, source_record_uuid,
  │  rehydration_reason, requested_by_uuid, rehydration_timestamp
  ▼
If source = Intent:
  │  Full layer assembly runs (Steps 1-7)
  │  Current layers applied
  ▼
If source = Requested or Realized:
  │  Layer assembly skipped
  │  Payload loaded as pre-assembled
  │  If source = Realized: provider-specific fields stripped
  ▼
Placement evaluation
  │  See Section 5.3 — configurable
  ▼
Policy Engine — ALL governance policies applied
  │  Authorization policies: does this actor have permission to rehydrate?
  │  Transformation policies: current enrichment applied
  │  Validation policies: current constraints checked
  │  GateKeeper policies: current field locks applied
  │  Gatekeeping policies: is this resource type still permitted?
  │
  │  Governance is NEVER skippable — not for any rehydration source,
  │  not for any actor, not for any urgency claim
  ▼
New Requested State produced and stored
  │  New record — never overwrites the source record
  │  Source record remains immutable
  │  Provenance chain links to source record
  ▼
Provider dispatch
  │  Dispatched to selected provider
  ▼
New Realized State events produced
  │  New event stream or continuation of existing stream
  │  Provenance links to rehydration Requested State
```

### 5.3 Placement Flag — Provider-Portable Rehydration

When rehydrating from Requested State or Realized State, provider selection is configurable via an explicit flag in the rehydration request:

```yaml
rehydration_request:
  uuid: <uuid>
  source_store: <intent|requested|realized>
  source_record_uuid: <uuid of source record>

  placement:
    re_evaluate: false
    # false (default): honor provider selection from source record
    #   Use when: original provider is available and appropriate
    #   Result: resource reproduced on same provider
    #
    # true: strip provider selection, run placement policies fresh
    #   Use when: original provider unavailable, decommissioned,
    #   at capacity, or no longer sovereign-compliant
    #   Result: placement policies select provider from current landscape
    #   Named concept: Provider-Portable Rehydration

    placement_constraints:
      # Optional — additional constraints for re-evaluation
      # Only applicable when re_evaluate: true
      exclude_provider_uuids: [<uuid>, ...]
      require_region: <region>
      require_sovereignty_capability: <capability>

  governance:
    apply_all_policies: true
    # Always true — governance is never skippable
    # Included explicitly for auditability — the rehydration record
    # must declare that governance was applied

    policy_version: current
    # current (default): apply today's policies
    # pinned: apply policies as of a specific timestamp
    #   Use when: exact historical reproduction required
    #   (audit evidence, regulatory examination, environment reconstruction)
    #   Requires elevated authorization — bypasses current GateKeeper policies
    #   Only SRE and Admin actors may use pinned policy version

    pinned_timestamp: <ISO 8601>
    # Required when policy_version: pinned

  rehydration_reason: <human-readable — recorded in provenance>
  requested_by_uuid: <actor UUID — authorization checked>
```

### 5.4 The Four Rehydration Modes

Two independent axes — placement and policy version — produce four distinct rehydration configurations:

| Mode | re_evaluate | policy_version | Use Case |
|------|-------------|----------------|----------|
| **Faithful** | false | current | Same provider, current governance |
| **Provider-Portable** | true | current | New provider, current governance |
| **Historical Exact** | false | pinned | Same provider, historical governance (audit evidence) |
| **Historical Portable** | true | pinned | New provider, historical governance |

Historical modes require elevated authorization. All modes run governance — the difference is whether governance uses current or pinned policies.

### 5.5 Rehydration Tenancy and Sovereignty Controls

**Tenancy controls, sovereignty directives, and cross-tenant authorizations are always evaluated against current policies during rehydration — they cannot be pinned to historical versions.**

The `policy_version: pinned` setting governs resource configuration policies only. It does not apply to:
- Tenancy boundary enforcement
- Sovereignty constraints
- Cross-tenant authorization requirements

```yaml
rehydration:
  policy_version: pinned         # governs resource configuration policies
  # The following ALWAYS use current policies — cannot be pinned:
  tenancy_controls: always_current
  sovereignty_controls: always_current
  cross_tenant_authorizations: always_current
```

**When rehydration conflicts with current tenancy controls:**

If the current policy environment produces a tenancy or sovereignty constraint that conflicts with a cross-tenant allocation valid at original request time — for example, the consuming Tenant's authorization was revoked since the original request — the rehydration is **paused**, not failed or silently bypassed:

```
Rehydration detects cross-tenant authorization conflict
  │
  ▼
Entity enters PENDING_REVIEW state
  │  Allocation is not automatically released
  │  Rehydration_tenancy_conflict_record created
  ▼
Notifications dispatched:
  │  entity owner, owning Tenant admin,
  │  consuming Tenant admin, platform admin
  ▼
Resolution options:
  re_authorize  → issue new cross_tenant_authorization for this allocation
  release       → release the allocation, entity decommissioned
  escalate      → refer to platform admin for manual decision
  │
  └── A policy may declare automatic resolution:
      "on rehydration conflict → re_authorize if consuming Tenant
       still meets sovereignty requirements"
```

**System policies for rehydration tenancy:**

| Policy | Rule |
|--------|------|
| `RHY-001` | Tenancy, sovereignty, and cross-tenant authorizations always use current policies during rehydration — cannot be pinned |
| `RHY-002` | Rehydration that conflicts with current tenancy/sovereignty pauses and enters PENDING_REVIEW |
| `RHY-003` | A paused rehydration allocation is not automatically released — requires explicit resolution |
| `RHY-004` | A policy may declare automatic resolution behavior for rehydration tenancy conflicts |

### 5.6 Partial Resolution of Q54 — Provider Selection

The placement flag model clarifies the Q54 question (selected_provider as policy output vs placement component). The emerging answer:

**Policies set placement constraints — the placement component selects the provider.**

A GateKeeper policy may output: "must be in region EU-WEST, must support sovereignty capability PCI-DSS." The placement component reads these constraints and selects the specific provider within those constraints. The policy does not name the provider. The placement component names the provider.

This is consistent with the portability model — a policy that names a specific provider would be portability-breaking. Policies set constraints. Placement honors constraints and selects.

---

## 6. Drift Detection

Drift is the difference between what DCM believes exists (Realized State) and what actually exists (Discovered State).

### 6.1 Drift Detection Flow

```
Discovery cycle completes
  │  Provider interrogated → Discovered State snapshot written
  ▼
Drift Detection component
  │  Loads latest Discovered State for entity UUID
  │  Loads latest Realized State events for entity UUID
  │  Field-by-field comparison
  ▼
No drift detected
  │  Discovery timestamp updated
  │  No action
  ▼
Drift detected
  │  Drift record created with:
  │    - entity_uuid
  │    - drifted_fields: [{field_path, realized_value, discovered_value}]
  │    - discovery_timestamp
  │    - drift_severity: <minor|significant|critical>
  ▼
Policy Engine evaluates drift
  │  Drift response policy determines action:
  │    REVERT: submit a rehydration request from Realized State to restore
  │    UPDATE_DEFINITION: promote discovered state to new Realized State
  │    ALERT: notify personas, no automatic action
  │    ESCALATE: trigger human review workflow
  │
  │  Response determined by drift severity, resource type,
  │  resource ownership, and organizational policy
  ▼
Audit Store records drift event with full provenance
```


### 6.3 Drift Severity Classification

Drift severity is determined by combining three independent tiers. The final severity is the highest tier that applies.

**Tier 1 — Field criticality (declared in Resource Type Specification):**

```yaml
resource_type_spec:
  fields:
    display_name:
      drift_criticality: minor      # non-functional change
    cpu_count:
      drift_criticality: significant
    memory_gb:
      drift_criticality: significant
    security_group_ids:
      drift_criticality: critical   # security-relevant change
    firewall_rules:
      drift_criticality: critical
```

**Tier 2 — Profile/layer magnitude thresholds:**

```yaml
# system/drift/severity-thresholds layer (overridable at platform/tenant domain)
drift_severity_thresholds:
  significant_field_magnitude_upgrade:
    percentage_change_threshold: 50    # >50% change upgrades significant → critical
  minor_field_magnitude_upgrade:
    item_count_threshold: 10           # 10+ changed items upgrades minor → significant
```

**Tier 3 — Provider and consumer injection:**

Providers may suggest severity in update notifications (raise only):
```yaml
provider_drift_hint:
  field: memory_gb
  suggested_severity: critical
  reason: "Memory decrease on running workload risks OOM"
```

Consumers may override sensitivity on specific entities (raise or lower):
```yaml
entity:
  drift_sensitivity_overrides:
    - field: cpu_count
      override_criticality: critical
      reason: "Production payments workload — any CPU change is critical"
```

**Resolution rule:** The Drift Detection component takes the highest severity from all three tiers. Provider injection can raise but not lower the Tier 1/2 result. Consumer injection can raise or lower (entity owner controls their own resource's sensitivity). Profile governs whether consumer lowering is permitted.



### 6.3 Drift Severity Classification

Drift severity is determined by two independent dimensions declared in the Resource Type Specification — field criticality and change magnitude. The combination produces a deterministic severity classification for any drift event.

#### Field Criticality (declared per field in Resource Type Spec)

```yaml
resource_type_spec:
  fqn: Compute.VirtualMachine
  fields:
    display_name:
      drift_criticality: low          # cosmetic; never affects function
    cpu_count:
      drift_criticality: medium       # affects performance; not security
    memory_gb:
      drift_criticality: medium
    security_group_ids:
      drift_criticality: critical     # security boundary field; always critical
    os_image:
      drift_criticality: critical     # security posture; always critical
    storage_gb:
      drift_criticality: medium
    network_interface_ids:
      drift_criticality: high         # connectivity; significant operational impact
```

**Criticality levels:** `low | medium | high | critical`

#### Change Magnitude (profile-governed thresholds)

```yaml
drift_magnitude_thresholds:
  profile_defaults:
    standard:
      minor:       change_pct < 10%
      significant: change_pct 10-50%
      critical:    change_pct > 50% OR value_disappeared OR type_changed
    prod:
      minor:       change_pct < 5%
      significant: change_pct 5-25%
      critical:    change_pct > 25% OR value_disappeared OR type_changed
```

#### Severity Matrix

| Field Criticality | Change Magnitude | Drift Severity |
|------------------|-----------------|----------------|
| low | any | minor |
| medium | minor | minor |
| medium | significant | significant |
| medium | critical | significant |
| high | minor | significant |
| high | significant | significant |
| high | critical | critical |
| critical | any | critical |

**Unsanctioned changes** (no corresponding Requested State record) are always elevated one severity level above what the matrix produces. A `significant` unsanctioned change becomes `critical`.

**Multi-field drift:** when multiple fields drift simultaneously, the overall severity is the highest severity among all drifted fields.


### 6.2 Unsanctioned Changes

A specific category of drift — a change made directly to a resource without a corresponding DCM request. Detected by:
- Kubernetes: CR spec change without DCM request annotation
- VMware/OpenStack: resource modification not traceable to a DCM Requested State record
- General: any Discovered State field value that differs from Realized State without a Requested State record explaining the change

Unsanctioned changes are always reported to the Policy Engine as `UNSANCTIONED_CHANGE` events. Policy determines the response.

---

## 7. CI/CD Integration

The GitOps stores are the natural integration point for CI/CD pipelines. DCM does not prescribe a specific CI/CD tool — the GitOps store contract requires hook support, and the CI/CD tool is a deployment choice.

### 7.1 CI Pipeline (Intent State)

Triggered on: branch creation or update (new or revised intent)

```
CI pipeline executes:
  1. Policy pre-validation (dry run — no state changes)
     → Reports: which policies would apply, what they would do
  2. Cost estimation
     → Reports: estimated cost for lifecycle of this resource
  3. Dependency graph validation
     → Reports: all required dependent resources, any conflicts
  4. Sovereignty constraint check
     → Reports: which sovereignty constraints apply, any violations
  5. Authorization check
     → Reports: does this actor have permission to request this resource type?
  6. Auto-approve evaluation
     → Reports: can this be merged automatically, or does it require human review?

All results posted as PR comments on the Intent State branch
Consumer and approvers can review and debate before merge
```

### 7.2 CD Pipeline (Requested State)

Triggered on: Intent State merge (PR merged to main)

```
CD pipeline executes:
  1. Request Payload Processor assembles full payload
  2. Full policy evaluation (binding — not dry run)
  3. Provider selection (or re-evaluation if placement flag set)
  4. Requested State committed to Git store
  5. Provider dispatch via API Gateway
  6. Status monitoring — poll or receive callbacks until terminal state
  7. Status written back to PR or status file
  8. Consumer notification
```

### 7.3 The Third Rail — Direct API Ingress

Not all requests come through the GitOps PR workflow. Some requests come through direct API submission — automated systems, CI/CD pipelines, Terraform providers, programmatic consumers. These bypass the human review workflow but not governance.

Direct API ingress:
- Creates an Intent State record (the submitted payload becomes the intent)
- Runs the same CI validation pipeline but non-interactively
- If auto-approve policy permits: proceeds directly to assembly and dispatch
- If human review required: creates a PR for review before proceeding
- Same governance pipeline regardless of ingress path

The three ingress paths — PR workflow, direct API, and programmatic (Terraform/Ansible) — all converge on the same governance pipeline. The ingress path affects the review workflow; it never affects governance.

---

## 7a. Four States Operational Gaps — Q75 through Q78

### 7a.1 Entity UUID Preservation on Rehydration (Q75)

Entity UUIDs are **preserved on rehydration**. The UUID represents the stable logical identity of the resource across provider migrations, sovereignty changes, and lifecycle events. All external references — CMDB records, cost attribution, audit trails, cross-tenant relationships, dependency declarations — reference the entity by UUID. Generating a new UUID on rehydration would silently break all of those references.

What changes on rehydration is the **provider-side identifier** — the actual VM ID, container name, or resource handle at the provider. These are recorded in the rehydration history:

```yaml
entity:
  uuid: <original-uuid>              # PRESERVED across all rehydrations
  rehydration_history:
    - rehydration_uuid: <uuid>
      rehydrated_at: <ISO 8601>
      trigger: <provider_migration|sovereignty_violation|manual|provider_decommission>
      from_provider_uuid: <uuid>
      to_provider_uuid: <uuid>
      from_realized_entity_id: "vm-12345"   # provider's ID — no longer valid
      to_realized_entity_id: "vm-67890"     # new provider's ID after rehydration
      rehydrated_by: <actor-uuid>
      intent_state_ref: <uuid>
      previous_requested_state_ref: <uuid>
      new_requested_state_ref: <uuid>
```

**Rehydration is transactional:** If the target provider cannot accept the entity (capacity unavailable, sovereignty mismatch discovered mid-rehydration), the original entity remains in its current state with no UUID change and no partial state. Failure preserves the pre-rehydration state completely.

### 7a.2 Pinned Authentication Level for Rehydration (Q76)

Entities may declare a minimum authentication level required to rehydrate them. This prevents escalation of privilege through the rehydration mechanism — a resource provisioned with hardware-token MFA authorization should not be re-instantiatable by a simple API key.

```yaml
entity:
  rehydration_constraints:
    min_auth_level: hardware_token_mfa
    # Ascending levels: api_key | ldap_password | oidc | oidc_mfa |
    #                   hardware_token | hardware_token_mfa
    auth_level_source: <original_provisioning|policy_declared>
    allow_delegated_rehydration: false
    # true = DCM service accounts may rehydrate if explicitly authorized
```

**Profile-governed enforcement:**

| Profile | Enforcement |
|---------|------------|
| `minimal` | Not enforced — any auth level may rehydrate |
| `dev` | Not enforced |
| `standard` | Advisory — warn if rehydrating actor has lower auth |
| `prod` | Enforced — reject if rehydrating actor has lower auth |
| `fsi` | Enforced — dual approval required if auth level mismatch |
| `sovereign` | Enforced — dual approval always; logged in classified audit |

**Automated rehydration:** When DCM triggers rehydration automatically (sovereignty violation, provider decommission), the rehydration uses DCM's internal service account. This requires `allow_delegated_rehydration: true` OR a platform admin must manually authorize the operation. Authorization produces an audit record preserving accountability even when the action is automated.

### 7a.3 Concurrent Rehydration Handling (Q77)

Rehydration requests acquire an **exclusive rehydration lease** per entity. Only one rehydration may be active per entity at any time.

```yaml
rehydration_lease:
  entity_uuid: <uuid>
  lease_uuid: <uuid>
  acquired_by: <actor-uuid>
  acquired_at: <ISO 8601>
  lease_ttl: PT2H                     # expires after 2 hours if not released
  trigger: <manual|sovereignty_migration|provider_decommission|admin_request>
  status: <active|completed|failed|expired>
```

**Concurrent request handling:**

```
Second rehydration attempt arrives for entity <uuid>
  │
  ├── No active lease → acquire lease; proceed
  │
  └── Active lease exists:
        Priority higher than active → escalate to platform admin; queue
        Same or lower priority → reject:
          "Rehydration in progress — lease held since <timestamp>; retry after PT2H"
        REHYDRATION_BLOCKED audit event recorded
```

**Priority ordering:**
1. Security/compliance emergency (sovereignty violation at fsi/sovereign)
2. Manual platform admin rehydration
3. Automated sovereignty migration
4. Provider decommission migration
5. Manual consumer rehydration request

**Lease TTL expiry:** If rehydration hangs or crashes, the lease expires after TTL. DCM marks the rehydration `failed` in rehydration_history, releases the lease, and triggers drift detection to assess partial completion at the provider.

### 7a.4 Discovered State Retention (Q78)

Discovered State is ephemeral operational data — not the authoritative source of truth (Realized State is). It is a snapshot used for drift detection. Three retention modes, all profile-governed:

```yaml
discovered_state_retention:
  mode: <rolling_window|event_driven|hybrid>   # hybrid recommended

  rolling_window:
    retention: P7D              # keep last 7 days; useful for trending

  event_driven:
    retain_until: drift_resolved  # keep until associated drift record resolved
    # Ensures drift investigation has the discovery snapshot that triggered it

  hybrid:                         # recommended — combines both
    minimum_retention: P24H
    retain_until: drift_resolved  # extend beyond minimum until drift resolved
    maximum_retention: P30D       # hard ceiling regardless of drift status
```

**Profile-governed defaults:**

| Profile | Mode | Min Retention | Max Retention |
|---------|------|--------------|--------------|
| `minimal` | `rolling_window` | — | P3D |
| `dev` | `rolling_window` | — | P7D |
| `standard` | `hybrid` | P24H | P30D |
| `prod` | `hybrid` | P48H | P30D |
| `fsi` | `hybrid` | P7D | P90D |
| `sovereign` | `hybrid` | P7D | P90D |

**Discovered State and the Audit Store:**

Discovered State records are **NOT** stored in the Audit Store — they are too high-volume and too ephemeral for compliance-grade storage. However, drift events triggered by Discovered State ARE recorded in the Audit Store with a reference to the discovery snapshot UUID. After the Discovered State expires, the audit record still exists — it cannot link to the full snapshot, but the drift event itself is preserved.

---

## 7b. Rehydration System Policies — Complete Set

| Policy | Rule |
|--------|------|
| `RHY-001` | Tenancy and sovereignty are always current on rehydration — they cannot be pinned to historical state. |
| `RHY-002` | Sovereignty conflicts discovered during rehydration place the entity in PENDING_REVIEW state. |
| `RHY-003` | Resource allocations are not automatically released on rehydration. |
| `RHY-004` | Rehydration leases have TTL to prevent orphaned lease states. |
| `RHY-005` | Entity UUIDs are preserved on rehydration. The UUID represents stable logical identity across provider migrations. Provider-side identifiers change on rehydration and are recorded in rehydration_history. Rehydration is transactional — failure preserves pre-rehydration state without UUID change. |
| `RHY-006` | Entities may declare min_auth_level for rehydration. Profile governs enforcement. Automated rehydration by DCM service accounts requires allow_delegated_rehydration: true OR platform admin manual authorization with full audit trail. |
| `RHY-007` | Rehydration requests acquire an exclusive lease per entity before proceeding. Only one rehydration may be active per entity. Concurrent requests are queued (higher priority) or rejected (same/lower). Lease TTL prevents indefinite blocking. Expiry triggers drift detection for partial completion assessment. |
| `RHY-008` | Discovered State retention is profile-governed: rolling_window, event_driven, or hybrid. Discovered State is never stored in the Audit Store. Drift events triggered by Discovered State are recorded in the Audit Store with discovery snapshot UUID reference. Maximum retention: P30D for standard/prod; P90D for fsi/sovereign. |

---

## 8. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Git repository structure for Intent and Requested stores | Store design | ✅ Resolved — handle-based directory structure; 4 repos; tenant isolation (STO-005) |
| 2 | Should the entity UUID be preserved or regenerated on rehydration? | Entity identity | ✅ Resolved — UUID preserved; rehydration_history records provider-side ID changes; transactional (RHY-005) |
| 3 | For pinned policy version rehydration — what is the minimum authorization level required? | Security | ✅ Resolved — min_auth_level on entity; profile-governed enforcement; delegated rehydration requires explicit authorization (RHY-006) |
| 4 | How are concurrent rehydration requests for the same entity handled? | Concurrency | ✅ Resolved — exclusive rehydration lease; priority ordering; TTL expiry triggers drift detection (RHY-007) |
| 5 | Should the Discovered Store retain full history or only a configurable window? | Retention | ✅ Resolved — hybrid mode recommended; profile-governed min/max; event-driven until drift resolved; max P30-90D (RHY-008) |
| 6 | How does the Search Index handle Git store unavailability? | Reliability | ✅ Resolved — serve degraded (warn + direct to authoritative); rebuild on recovery (STO-002) |

---

## 9. Related Concepts

- **Storage Provider** — the formal provider type for all DCM stores
- **Entity UUID** — the universal linking key across all four states
- **Rehydration** — using a prior state record as the starting point for a new request
- **Provider-Portable Rehydration** — rehydration with provider selection re-evaluated
- **Drift Detection** — comparing Realized State against Discovered State
- **Unsanctioned Change** — a resource modification not traceable to a DCM request
- **CI/CD Integration** — GitOps stores as the natural CI/CD integration point
- **Search Index** — queryable projection of GitOps stores, explicitly non-authoritative

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
