# DCM Data Model — Universal Audit Model


**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Audit, Provenance, and Observability](12-audit-provenance-observability.md) | [data stores](11-storage-providers.md) | [Universal Groups](15-universal-groups.md)

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
> The Data abstraction — Audit Record structure and tamper-evident chain



---

## 1. Purpose

The Universal Audit Model defines the **unconditional obligation** for every DCM component to record every change to every artifact in a uniform, tamper-evident, retention-governed audit trail. No change is silent. No change is exempt.

**The four required fields for every audit record:**
- **Date and time** — when the change occurred (ISO 8601 with milliseconds)
- **Who** — the complete actor chain (immediate actor + human authorization chain)
- **What** — the subject of the change (entity UUID, type, handle)
- **Action** — what happened (closed vocabulary — not free text)

**The retention requirement:** Audit records must survive at least as long as any referenced resource or group is live. Policy governs what happens after all affected parties reach terminal state.

---

## 2. Design Principles

**Universal — no exceptions.** Every mutation to every DCM artifact produces an audit record. Resources, policies, layers, groups, relationships, providers, configurations, authorizations, external evaluation queries, ingestion events, rehydration events, drift events, login events — all covered.

**Append-only — tamper-evident.** Audit records are never modified or deleted while retention obligations apply. Each record carries a hash of its own content and a reference to the previous record's hash — forming a tamper-evident chain per entity.

**Guaranteed delivery — not guaranteed synchrony.** Audit writes use a write-ahead log (WAL) pattern — the change and its audit record are written to a local WAL first, then delivered to the Audit Store asynchronously with retry. A change is never silent — it may be briefly buffered, but delivery is guaranteed before the WAL is cleared.

**Reference-based retention — not time-based.** Audit records are retained while any referenced entity is live. Fixed time schedules (7 years, 10 years) are applied only after all referenced entities reach terminal state. A record created 20 years ago is retained unconditionally if any entity it references is still operational.

**Policy-governed post-lifecycle retention.** After all referenced entities reach terminal state, policy determines how long to keep the audit record. Default is 7 years post-retirement (FSI-aligned). Organizations configure per Profile.

---

## 3. The Universal Audit Record

```yaml
audit_record:
  # IDENTITY — immutable once written
  record_uuid: <uuid>
  record_timestamp: <ISO 8601 with milliseconds — when the change occurred>
  dcm_version: <DCM version that produced this record>

  # WHO — composite actor chain
  actor:
    # The immediate actor that performed the change
    immediate:
      type: <human|system_component|policy|provider|scheduled_job|mode4_provider>
      uuid: <uuid of the actor — policy UUID, provider UUID, component UUID, etc.>
      display_name: <human-readable name>
      session_uuid: <session UUID — for human actors>

    # The human who ultimately authorized this action (traceable chain)
    authorized_by:
      uuid: <human actor UUID — if traceable to a person>
      display_name: <name>
      authorization_method: <direct_action|request_submission|policy_activation|system_policy|scheduled>
      # direct_action:      human directly performed this
      # request_submission: human submitted the request that triggered this
      # policy_activation:  human activated the policy that triggered this
      # system_policy:      DCM System Policy — no individual human
      # scheduled:          scheduled job — authorized by job owner

    # Links to originating context
    request_uuid: <uuid — originating request, if applicable>
    policy_uuid: <uuid — policy that triggered this, if applicable>
    policy_version: <version — of the policy at time of execution>
    correlation_id: <cross-system ID — e.g., external evaluation audit_token>

  # WHAT — the subject of the change
  subject:
    entity_uuid: <uuid of the artifact that changed>
    entity_type: <resource_entity|policy|layer|group|relationship|provider|
                  configuration|authorization|ingestion_record|audit_record>
    entity_handle: <human-readable handle — non-authoritative, display only>
    entity_version_before: <Major.Minor.Revision — version before change>
    entity_version_after: <Major.Minor.Revision — version after change>

  # ACTION — closed vocabulary
  action: <see Section 4>

  # ACTION DETAIL — structured per action type
  action_detail:
    # For MODIFY, ENRICH, LOCK
    field_changes:
      - field: <field path — e.g., lifecycle_constraints.ttl.duration>
        previous_value: <value>
        new_value: <value>
        change_reason: <human-readable>
        locked_after: <true|false — if LOCK action set immutable>

    # For STATE_TRANSITION
    state_transition:
      from_state: <state>
      to_state: <state>
      transition_reason: <human-readable>
      triggered_by: <actor or policy>

    # For RELATIONSHIP_CREATE, RELATIONSHIP_RELEASE
    relationship_detail:
      related_entity_uuid: <uuid>
      related_entity_type: <type>
      relationship_type: <type from standard vocabulary>
      relationship_nature: <constituent|operational|informational>
      cross_tenant: <true|false>

    # For MEMBER_ADD, MEMBER_REMOVE
    membership_detail:
      group_uuid: <uuid>
      group_class: <class>
      member_role: <role>
      time_bounded: <true|false>
      expires_at: <ISO 8601 — if time-bounded>

    # For EVALUATE (policy evaluation)
    evaluation_detail:
      policy_uuid: <uuid>
      policy_version: <version>
      outcome: <pass|fail|warn|gatekeep|implicit_approval>
      placement_phase: <pre|loop|post>
      missing_fields: [<field paths if implicit_approval>]

    # For QUERY (external evaluation)
    query_detail:
      provider_uuid: <uuid>
      fields_queried: [<field names — not values>]
      result_type: <pass_fail|score|enrichment|multi_factor>
      outcome: <pass|fail|score_value>
      audit_token: <provider audit token>
      cached_result: <true|false>

    # For DRIFT_DETECT
    drift_detail:
      drifted_fields:
        - field: <path>
          realized_value: <value>
          discovered_value: <value>
      drift_severity: <minor|significant|critical>
      policy_response: <REVERT|UPDATE_DEFINITION|ALERT|ESCALATE>

  # CONTEXT
  context:
    tenant_uuid: <uuid — owning Tenant of the subject>
    request_uuid: <originating request — if part of request lifecycle>
    session_uuid: <actor session — for human actors>
    profile_active: <handle of active Profile at time of change>
    tags: [...]   # arbitrary searchable tags

  # RETENTION
  retention:
    referenced_entities:
      - entity_uuid: <uuid>
        entity_type: <type>
        last_known_state: <state — updated by DCM lifecycle events>
    retention_status: <live|all_retired|policy_governed>
    # live:           at least one referenced entity is non-retired — retain unconditionally
    # all_retired:    all referenced entities have reached terminal state
    # policy_governed: apply governing_policy after all_retired
    governing_policy_uuid: <uuid>
    retain_until: <ISO 8601 — null if live; calculated when status becomes policy_governed>

  # INTEGRITY — tamper-evident hash chain
  integrity:
    record_hash: <SHA-256 of this record's content>
    previous_record_hash: <hash of the immediately preceding audit record for this entity>
    # Forms a per-entity hash chain — inserting, modifying, or deleting a
    # historical record breaks the chain, detectable by verification
    chain_sequence: <integer — monotonically increasing per entity>
    signed_by: <signing authority UUID — if audit signing is configured>
    signature: <cryptographic signature — if configured>
```

---

## 4. Action Vocabulary

The `action` field uses a closed vocabulary. Free-text actions are invalid and rejected at write time (AUD-007).

| Action | Applies To | Description |
|--------|-----------|-------------|
| `CREATE` | All | New artifact created |
| `MODIFY` | All | Artifact field changed |
| `STATE_TRANSITION` | Entities, groups | Lifecycle state changed |
| `DELETE` | All | Artifact destroyed / decommissioned |
| `ACTIVATE` | Policies, profiles, groups | Artifact made active |
| `DEACTIVATE` | Policies, profiles, groups | Artifact made inactive |
| `DEPRECATE` | All | Artifact deprecated |
| `RETIRE` | All | Artifact retired |
| `MEMBER_ADD` | Groups | Member added to group |
| `MEMBER_REMOVE` | Groups | Member removed from group |
| `RELATIONSHIP_CREATE` | Entities | Relationship established |
| `RELATIONSHIP_RELEASE` | Entities | Relationship released |
| `AUTHORIZE` | Cross-tenant, actors | Authorization granted |
| `REVOKE` | Cross-tenant, actors | Authorization revoked |
| `EVALUATE` | Policies | Policy evaluated (with outcome) |
| `ENRICH` | Fields | Field enriched by policy, layer, or external policy evaluation |
| `LOCK` | Fields | Field locked (override: immutable set) |
| `HOLD_PLACE` | Resources | Resource hold placed with provider |
| `HOLD_CONFIRM` | Resources | Resource hold confirmed |
| `HOLD_RELEASE` | Resources | Resource hold released |
| `DRIFT_DETECT` | Entities | Drift detected between Realized and Discovered |
| `DRIFT_RESOLVE` | Entities | Drift resolved |
| `INGEST` | Entities | Entity ingested (brownfield or import) |
| `PROMOTE` | Entities | Ingested entity promoted to full lifecycle |
| `EXPIRE` | Entities | Lifecycle time constraint expiry action fired |
| `REHYDRATE` | Entities | Rehydration requested |
| `QUERY` | external evaluation | Black box query sent and result received |
| `DISCOVER` | Entities | Discovery cycle completed |
| `LOGIN` | Actors | Actor authentication event |
| `LOGOUT` | Actors | Actor session ended |
| `CONFIG_CHANGE` | Platform | DCM configuration changed (profile activated, etc.) |

---

## 5. The "Who" — Composite Actor Record

The `who` in an audit record is not a single identity — it is a **composite actor chain** tracing from the immediate action back to the human who ultimately authorized it.

### 5.1 Actor Types

| Type | Example | authorized_by |
|------|---------|--------------|
| `human` | Platform admin changes a policy | Self |
| `system_component` | Lifecycle Constraint Enforcer fires expiry | Policy that set the constraint → human who activated policy |
| `policy` | Transformation Policy enriches a field | Human who activated the policy |
| `provider` | Service Provider updates Realized State | Dispatch that triggered it → human who submitted request |
| `scheduled_job` | Discovery cycle runs | Owner of the scheduled job |
| `mode4_provider` | Black box enriches a field | Policy that triggered the query → human who activated policy |

### 5.2 System-Initiated Actions

For system-initiated changes where there is no immediate human actor, the authorization chain traces back as far as possible:

```yaml
actor:
  immediate:
    type: system_component
    uuid: <lifecycle-constraint-enforcer-uuid>
    display_name: "Lifecycle Constraint Enforcer"
  authorized_by:
    uuid: null   # no specific human — system policy
    display_name: "DCM System Policy LTC-003"
    authorization_method: system_policy
  policy_uuid: <uuid of LTC-003>
  policy_version: "1.0.0"
```

---

## 6. Retention Model

### 6.1 Reference-Based Retention

Audit records are retained based on the lifecycle state of all referenced entities — not on a fixed time schedule.

```
Audit record created
  │  retention_status: live (all referenced entities tracked)
  │
  ▼  [continuous monitoring]
  │
  As referenced entities change state:
  │  DCM updates last_known_state on each referenced_entity
  │  When all reach terminal state → retention_status: all_retired
  │
  ▼  retention_status: all_retired
  │  Governing policy determines retain_until date
  │  retention_status: policy_governed
  │
  ▼  retain_until reached
     Audit record eligible for destruction / archival
```

### 6.2 Post-Lifecycle Retention Options

| Policy Setting | Meaning | Default Profile |
|---------------|---------|----------------|
| `destroy_immediately` | Destroy when last entity retires | (not available in standard+) |
| `retain_for: P90D` | 90 days post-retirement | dev profile |
| `retain_for: P3Y` | 3 years post-retirement | standard profile |
| `retain_for: P7Y` | 7 years post-retirement | prod, fsi profiles (DEFAULT) |
| `retain_for: P10Y` | 10 years post-retirement | sovereign profile |
| `retain_indefinitely` | Never destroy | optional — maximum compliance |
| `archive_after: P1Y` | Move to cold storage 1 year post-retirement | configurable |

### 6.3 Retention Shorter Than Referenced Entity Lifetime

This cannot happen. While any referenced entity is live, `retention_status: live` and the record is retained unconditionally. The retention policy only applies **after** all referenced entities reach terminal state. A 90-day retention policy means "90 days after the last referenced entity is retired" — not "90 days after creation."

---

## 7. Two-Stage Audit — Synchronous Commit + Async Enrichment

### 7.1 The Design

DCM uses a **two-stage audit model** that provides synchronous durability guarantees without impacting request processing performance.

```
Stage 1 — Commit Log (synchronous, in critical path, < 1ms)
Stage 2 — Audit Store (asynchronous, out of critical path, full record)
```

**Stage 1** writes a minimal Commit Log entry synchronously using consensus protocol (Raft). The write is confirmed when a quorum of Commit Log replicas acknowledges it. The operation returns success after Stage 1 confirms — not after the Audit Store write.

**Stage 2** runs asynchronously via the Audit Forward Service: enriches the minimal Commit Log entry into a full audit_record, computes the hash chain, and writes to the Audit Store with retry.

### 7.2 Stage 1 — Commit Log Entry (minimal, ultra-fast)

```yaml
commit_log_entry:
  entry_uuid: <uuid>            # links to full audit_record in Stage 2
  sequence: <integer>           # monotonically increasing — global ordering
  timestamp: <ISO 8601 microseconds>   # authoritative audit timestamp
  entity_uuid: <uuid>
  entity_type: <type>
  action: <closed vocabulary>
  actor_uuid: <uuid>            # immediate actor only
  request_uuid: <uuid>          # if applicable
  tenant_uuid: <uuid>
  change_fingerprint: <SHA-256 of change payload>
  # change_fingerprint enables Stage 2 to verify full record matches Stage 1

  status: <pending_forward|forwarded|forward_failed>
  forwarded_at: <ISO 8601>      # populated by Audit Forward Service
  audit_record_uuid: <uuid>     # UUID of full audit_record in Audit Store
```

**Stage 1 guarantees:** the change happened, at this exact time, this actor performed it, this entity was affected, this action was taken. Full detail follows in Stage 2.

**Commit Log quorum write** (distributed deployment):
```
Write confirmed when quorum acknowledges:
  ├── Replica 1 (local node)     → ACK ─┐
  ├── Replica 2 (different node) → ACK ─┤ quorum (2/3) — write confirmed
  └── Replica 3 (different zone) → (async best-effort)
```

### 7.3 Stage 2 — Audit Forward Service

```
Audit Forward Service reads pending_forward Commit Log entries
  │
  ├── Retrieve full change context from DCM internal state
  │   (field values before/after, complete actor chain, relationship detail)
  │
  ├── Construct complete audit_record (full structure per Section 3)
  │   - Compute record_hash + previous_record_hash (hash chain)
  │   - Set retention.referenced_entities
  │
  ├── Write to Audit Store
  │   → Success: mark commit_log_entry status: forwarded
  │   → Failure: retry with exponential backoff
  │              N retries exhausted → status: forward_failed, alert admin
  │
  └── Commit Log entry eligible for cleanup after:
      status: forwarded AND entry age > Commit Log retention window
```

### 7.4 Recoverability

| Failure Scenario | Recovery |
|-----------------|---------|
| DCM crashes after Stage 1, before Stage 2 | On restart, Audit Forward Service replays all `pending_forward` entries |
| Audit Store unavailable | Commit Log accumulates; Audit Forward Service retries when Audit Store recovers |
| Stage 2 fails mid-enrichment | Commit Log entry remains `pending_forward`; retried from committed Stage 1 data |
| Commit Log quorum unavailable | Stage 1 fails → operation aborted → no silent change |
| All Commit Log replicas lost | Recovery from replica backup; forward_failed entries investigated |

### 7.5 Performance Characteristics

| Component | Latency | In Critical Path? |
|-----------|---------|-----------------|
| Stage 1 — Commit Log quorum write | < 1ms (local NVMe + Raft) | Yes |
| Stage 2 — Audit Store write | 5–50ms (network + indexing) | No |
| Full audit record visible | Seconds to minutes after Stage 1 | No |

**The Stage 1 timestamp is the authoritative audit timestamp.** Stage 2 write time is when the full record became queryable — not when the change occurred.

---

---

## 8. Tamper-Evidence and Payload Integrity — Merkle Tree

DCM unifies audit trail integrity and payload chain-of-custody verification into a single mechanism: a **Merkle tree** following the RFC 9162 (Certificate Transparency v2.0) pattern. Each audit record is a leaf in the tree. The tree provides O(log n) inclusion proofs (prove a record exists) and O(log n) consistency proofs (prove the log is append-only). Signed Tree Heads provide the root of trust.

This model satisfies NIST SP 800-53 AU-9(3) (cryptographic protection of audit information), AU-10 (non-repudiation with AU-10(2) producer identity binding, AU-10(3) chain of custody, AU-10(5) digital signatures), SI-7 (information integrity), and NIST SP 800-171 3.3 (audit and accountability for CUI/CMMC).

### 8.1 Audit Granularity Levels

Administrators configure how granular the audit trail is. Higher granularity produces more leaves per request, enabling more precise forensics at the cost of more storage and processing.

| Level | Leaves per request | What is tracked | Use case |
|-------|-------------------|----------------|----------|
| **stage** | ~5–6 | One leaf per pipeline stage (intent, assembly, policy, placement, dispatch, callback). Each leaf includes before/after payload hash for the entire stage. | Homelab, dev, demo — proves the pipeline executed correctly. |
| **mutation** | ~15–30 | One leaf per individual change — each layer merge, each policy evaluation, each constraint resolution, each placement decision. Before/after payload hash per mutation. | Production — full chain of custody. Shows exactly which policy or layer caused each change. |
| **field** | ~15–30 (same leaf count, richer content) | Mutation-level plus per-field old/new value hashes on every mutation. For overrides, records both old and new value hashes. | FedRAMP, sovereign, FSI — maximum auditability. An auditor can verify not just that a field changed, but what it changed from and to. |

**Profile defaults:**

| Profile | Default granularity | Override permitted? |
|---------|-------------------|-------------------|
| `minimal` | stage | Yes — can increase |
| `dev` | stage | Yes |
| `standard` | mutation | Yes — can increase to field |
| `prod` | mutation | Yes |
| `fsi` | field | No — field is minimum for FSI |
| `sovereign` | field | No — field is minimum for sovereign |

**Configuration:**
```yaml
audit:
  granularity: stage | mutation | field      # default per profile
  signed_tree_head_interval: 100             # compute STH every N leaves (default)
  signed_tree_head_max_delay: PT60S          # or every T seconds, whichever comes first
  verification_mode: synchronous | asynchronous | disabled
  tree_node_storage: materialized | computed # store intermediate nodes or recompute
```

`verification_mode` controls whether the next pipeline stage verifies the previous stage's signature before processing:
- `synchronous` — next stage blocks until verification passes (required for fsi/sovereign)
- `asynchronous` — verification runs in background; pipeline proceeds optimistically
- `disabled` — no inter-stage verification (homelab only)

### 8.2 Leaf Structure

Every audit record (regardless of granularity level) is a Merkle tree leaf with this structure:

```yaml
audit_leaf:
  # Identity
  leaf_uuid: <uuid>
  leaf_index: <int>                         # position in global Merkle tree
  request_uuid: <uuid>                      # which request this belongs to
  entity_uuid: <uuid | null>                # primary entity (null for system events)
  tenant_uuid: <uuid>

  # What happened
  stage: intent_submitted | layer_applied | policy_evaluated | constraint_resolved |
         placement_scored | dispatched | provider_callback | ...
  source: "<handle>"                        # which layer, policy, or service
  source_type: actor | layer_merge | policy_gatekeeper | policy_transformation |
               policy_validation | constraint_resolution | placement | dispatch |
               provider_callback | system
  action: <closed vocabulary>               # from Section 4
  decision: <allow | deny | applied | resolved | ...>

  # Chain of custody — payload integrity
  input_payload_hash: <sha-256>             # hash of payload BEFORE this mutation
  output_payload_hash: <sha-256>            # hash of payload AFTER this mutation
  context_hash: <sha-256 | null>            # evaluation context hash (policy stages only)

  # Field-level detail (mutation and field granularity only)
  fields_changed: ["field.path.one", "field.path.two"]    # mutation+ only
  field_mutations:                                         # field granularity only
    - field: "monitoring.agent_config"
      action: injected | overridden | removed
      old_value_hash: <sha-256 | null>      # null for injected (no previous value)
      new_value_hash: <sha-256>

  # Who
  signer_uuid: <uuid>                       # service or actor identity
  signer_type: service | actor | provider
  timestamp: <ISO 8601>

  # Cryptographic binding
  signature: <Ed25519 or ECDSA-P256>        # signature over all above fields
  previous_leaf_hash: <sha-256>             # hash of the previous leaf for this request
```

At **stage** granularity, `fields_changed` and `field_mutations` are omitted. The leaf records only the before/after payload hash for the entire stage.

At **mutation** granularity, `fields_changed` is populated (which fields changed) but `field_mutations` (old/new value hashes per field) is omitted.

At **field** granularity, both are populated. Full forensic detail.

### 8.3 Signed Tree Heads

The Audit Service periodically computes a new Merkle root and signs it:

```yaml
signed_tree_head:
  tree_size: <int>                          # number of leaves in the tree
  timestamp: <ISO 8601>
  sha256_root_hash: <sha-256>               # Merkle root
  signature: <Ed25519>                      # signed by DCM's audit signing key
```

Signed Tree Heads are computed every N leaves or every T seconds (configurable). They are the root of trust for all verification. External auditors verify records against the signed tree head — they don't need access to the database, only the tree head and the inclusion proof.

### 8.4 Verification

**Inclusion proof** — prove a specific record exists in the tree:
```
POST /api/v1/audit/tree/inclusion-proof
Input: leaf_hash, tree_size
Output: proof path (O(log n) hashes from leaf to root)
```

**Consistency proof** — prove the current tree is a strict superset of a previous tree:
```
POST /api/v1/audit/tree/consistency-proof
Input: old_tree_size, new_tree_size
Output: proof path (O(log n) hashes)
```

**Request chain verification** — prove a specific request's full pipeline integrity:
```
POST /api/v1/audit/tree/verify-request/{request_uuid}
Output: all leaves for the request + inclusion proofs + payload hash chain verification
  - Verifies each leaf is in the tree (inclusion proofs)
  - Verifies output_payload_hash[N] == input_payload_hash[N+1] (chain of custody)
  - Verifies all signatures against known signing keys
  - Verifies timestamps are monotonically increasing
  - Returns: VERIFIED | CHAIN_BREAK (with break location) | SIGNATURE_INVALID
```

### 8.5 Applicable Standards

| Standard | Control | How DCM satisfies it |
|----------|---------|---------------------|
| RFC 9162 | Certificate Transparency v2.0 — Merkle tree, inclusion/consistency proofs, signed tree heads | Structural model for DCM's audit tree |
| NIST 800-53 AU-9(3) | Cryptographic protection of audit information | Merkle tree + signed tree heads |
| NIST 800-53 AU-10(2) | Validate binding of information producer identity | Each leaf signed by producing service |
| NIST 800-53 AU-10(3) | Chain of custody | input/output payload hash linking across leaves |
| NIST 800-53 AU-10(5) | Digital signatures on audit records | Ed25519/ECDSA-P256 per leaf + tree head |
| NIST 800-53 SI-7(1) | Integrity checks | Payload hash verification at each stage transition |
| NIST 800-171 3.3 | Audit and accountability for CUI | Full audit trail with integrity protection |
| FIPS 186-5 | Digital Signature Standard | Ed25519 or ECDSA-P256 for signatures; ML-DSA ready for post-quantum |
| FIPS 180-4 | SHA-2 | SHA-256 for all hashing |
| FedRAMP High | AU-10 non-repudiation required | Merkle tree + signing satisfies all AU-10 enhancements |
| SOC 2 Type II CC7.2 | Detection of unauthorized changes | Consistency proofs detect any log modification |

---

## 9. DCM System Policies

| Policy | Rule |
|--------|------|
| `AUD-001` | Every modification to any DCM artifact must produce a Commit Log entry synchronously before the operation returns success. Commit Log write failure aborts the operation — no silent unaudited changes. |
| `AUD-002` | Audit records are append-only and immutable. No audit record may be modified or deleted while retention_status is `live` or `policy_governed`. |
| `AUD-003` | Audit records must survive at least as long as any referenced entity is in a non-retired/non-decommissioned state (retention_status: live). |
| `AUD-004` | Post-lifecycle retention is governed by policy. Default is `retain_for: P7Y` after all referenced entities reach terminal state. |
| `AUD-005` | The actor field must identify both the immediate actor and the authorized_by human actor chain to the extent traceable. |
| `AUD-006` | Audit records form a Merkle tree (RFC 9162 pattern). Each leaf carries a signature from the producing service and a payload hash linking it to adjacent leaves in the request chain. |
| `AUD-007` | The action field must use the closed vocabulary — free-text action fields are invalid and must be rejected at write time. |
| `AUD-008` | Audit Store implementations must support queries by: entity_uuid, actor_uuid, action, timestamp range, tenant_uuid, request_uuid, leaf_index, and retention_status. |
| `AUD-009` | The Audit Forward Service must deliver all Commit Log entries to the Audit Store with exponential backoff retry. Commit Log entries may only be cleared after both: (a) Audit Store confirms receipt AND (b) entry has aged beyond the Commit Log retention window. |
| `AUD-010` | Merkle tree verification (inclusion proofs, consistency proofs, request chain verification) must be available as first-class DCM operations. Verification failures trigger immediate security alerts. |
| `AUD-011` | On DCM restart, the Audit Forward Service must replay all `status: pending_forward` Commit Log entries before accepting new operations. |
| `AUD-012` | Signed Tree Heads must be computed at the interval configured by the deployment profile. STH signing key must be stored in the secrets table (internal) or Vault (external). |
| `AUD-013` | The Stage 1 timestamp in the Commit Log is the authoritative audit timestamp. Stage 2 enrichment timestamps record when the full audit record became queryable — not when the change occurred. |
| `AUD-014` | Audit granularity level is configured per deployment profile. `fsi` and `sovereign` profiles require `field` granularity — this cannot be downgraded. |
| `AUD-015` | Inter-stage verification mode is configured per deployment profile. `fsi` and `sovereign` profiles require `synchronous` verification — the pipeline halts if any signature verification fails. |

---

## 10. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should hash chain verification run continuously or on-demand? | Security | ✅ Resolved — three levels: continuous write (chain construction), scheduled sweep (weekly to 6-hourly per profile), on-demand (operator-triggered); failure → security alert + integrity incident (AUD-014) |
| 2 | Should the WAL have a configurable maximum capacity, and what happens when it is reached? | Availability | ✅ Resolved — configurable max capacity; alert_and_continue (standard/prod); reject_new_ops (fsi/sovereign); backpressure at 75%/90%; P7D max age escalation (AUD-015) |
| 3 | Should audit records for system-initiated changes (no human actor) be flagged differently in the dashboard? | Operational | ✅ Resolved — actor.type: human/service_account/system; system_actor block with component/trigger/policy; full audit records; enables filtering in queries and dashboards (AUD-016) |
| 4 | How does hash chain verification interact with distributed DCM deployments where audit records may be written to multiple regional stores? | Architecture | ✅ Resolved — per-instance hash chains; daily Merkle root federation integrity proof at Hub DCM; cross-instance queries via parallel chains + correlation_id (AUD-017) |

---

## 11. Related Concepts

- **Audit, Provenance, and Observability** (doc 12) — three distinct concerns; this document covers the audit concern in full
- **Field-Level Provenance** — data lineage embedded in every payload; separate from audit records
- **data stores** (doc 11) — Audit Store contract: append-only, WAL delivery, hash chain, retention tracking
- **Universal Groups** (doc 15) — all group changes produce audit records per this model
- **Policy Organization** (doc 14) — policy activation, shadow evaluation, and external evaluation queries all produce audit records


## 10. Universal Audit Gap Resolutions

### 10.1 Hash Chain Verification Modes (Q1)

Hash chain verification operates at three independent levels:

```yaml
hash_chain_verification:
  continuous_write: true              # always — hash computed on every write (chain construction)

  scheduled_sweep:
    enabled: true
    schedule:
      standard: "0 2 * * 0"          # weekly
      prod: "0 2 * * *"              # daily
      fsi: "0 */6 * * *"            # every 6 hours
      sovereign: "0 */6 * * *"

  on_demand:
    enabled: true                     # always available to platform admin
    max_range: P365D                  # maximum time range per verification run

  on_verification_failure:
    action: alert_security_team
    halt_new_writes: false            # do not halt — alert and investigate
    # Halting writes is itself a security risk; alerting is the correct response
    create_integrity_incident: true
```

Continuous verification is part of chain construction (not a separate process). Scheduled sweep catches tampering between writes. On-demand is available for incident investigation, compliance audit, and pre-report verification.

### 10.2 Commit Log Maximum Capacity (Q2)

The Commit Log has a configurable maximum capacity with a declared overflow policy — different profiles have different trade-offs between availability and audit completeness.

```yaml
commit_log_capacity:
  max_size: 10Gi                      # configurable; profile-governed
  max_age: P7D                        # records older than 7d escalate regardless
  on_capacity_exceeded:
    profile_defaults:
      minimal: alert_and_continue     # availability priority
      dev: alert_and_continue
      standard: alert_and_continue
      prod: alert_and_continue
      fsi: reject_new_ops             # audit completeness priority
      sovereign: reject_new_ops
  warn_at_percent: 75                 # alert at 75% capacity
  urgent_at_percent: 90              # urgent alert at 90%
```

**`reject_new_ops` for fsi/sovereign:** Operating without a functional audit trail is a compliance violation in regulated environments. Stopping operations is preferable to operating unaudited — same principle as Commit Log quorum unavailability → abort operation (STO-002).

### 10.3 System-Initiated Audit Records (Q3)

Audit records for system-initiated changes declare `actor.type: system` with a `system_actor` block identifying the DCM component, trigger, and authorizing policy.

```yaml
audit_record:
  action: REHYDRATE
  actor:
    uuid: <system-actor-uuid>
    type: system                      # human | service_account | system
    system_actor:
      component: lifecycle_constraint_enforcer
      trigger: entity_ttl_expired
      entity_uuid: <triggering-entity-uuid>
      policy_uuid: <policy-that-triggered>
    authorization: implicit           # implicit = authorized by DCM architecture
                                      # explicit = authorized by named policy
```

System actor records are full audit records — they appear in all queries and compliance reports. `actor.type` enables filtering:
- `filter: actor.type = human` → all human-initiated changes
- `filter: actor.type = system` → all automated lifecycle operations
- `filter: actor.type = service_account` → all API/programmatic changes

### 10.4 Distributed Hash Chain Integrity (Q4)

In distributed DCM deployments (Hub + Regional + Sovereign DCMs), each instance maintains its own independent hash chain. Federation-level integrity is provided by daily Merkle root proofs.

```yaml
distributed_hash_chain:
  model: per_instance               # each DCM instance has its own chain
  instance_chain:
    chain_id: <dcm-instance-uuid>   # chain scoped to this instance

  federation_integrity_proof:
    enabled: true
    schedule: "0 0 * * *"           # daily
    mechanism: merkle_root
    # Hub DCM collects chain tip hashes from all Regional DCMs
    # Computes Merkle root → stores as federation_integrity_record
    # Any chain break in any instance is detectable against this root
    stored_at: hub_dcm_audit_store
    signed_by: hub_dcm_service_account
```

**Cross-instance queries:** Records from different chains are presented as parallel chains with cross-references via `correlation_id`. Not merged into a single chain — each instance's chain remains independently verifiable. Federation-level verification requires Hub DCM connectivity; per-instance verification is always available locally.

### 10.5 System Policies — Universal Audit Gaps

| Policy | Rule |
|--------|------|
| `AUD-014` | Hash chain verification operates at three levels: continuous (hash computed on every write), scheduled sweep (weekly to every 6 hours per profile), and on-demand (operator-triggered for any time range). Verification failure triggers a security alert and integrity incident. New audit writes continue — halting writes is itself a security risk. |
| `AUD-015` | The Commit Log has configurable maximum capacity with a declared overflow policy: alert_and_continue (standard/prod) or reject_new_ops (fsi/sovereign). Backpressure alerts fire at 75% and 90% capacity. Records older than P7D trigger escalation regardless of capacity. |
| `AUD-016` | Audit records for system-initiated changes declare actor.type: system with a system_actor block identifying the DCM component, trigger, and authorizing policy. System actor records are full audit records appearing in all queries and compliance reports. actor.type enables filtering between human, service_account, and system-initiated changes. |
| `AUD-017` | In distributed DCM deployments, each instance maintains its own independent hash chain scoped to that instance. Federation-level integrity is maintained via daily Merkle root proofs computed from all instance chain tips, stored at the Hub DCM. Cross-instance audit queries present parallel chains with cross-references via correlation_id. |


## 9a. Audit vs Observability — The Definitive Distinction (Q16)

Audit and Observability are separate components with separate storage contracts, separate consumers, and opposite fundamental trade-offs. They cannot be combined without violating one contract or the other.

### 9a.1 Comparison

| Dimension | Audit | Observability |
|-----------|-------|--------------|
| **Purpose** | Immutable record of WHAT HAPPENED and WHO authorized it | Real-time visibility into SYSTEM HEALTH and PERFORMANCE |
| **Primary consumers** | Auditors, compliance, security, legal, regulators | SREs, platform engineers, operators, dashboards |
| **Write rate** | Low — one record per action | Very high — multiple per second per component |
| **Retention** | Very long — P7Y+ (compliance-driven) | Short — days to months (operational) |
| **Mutability** | Never — append-only, hash-chained | Downsampling and aggregation acceptable |
| **Accuracy** | 100% required — no sampling | Statistical sampling acceptable |
| **Compliance grade** | Required | Not required |
| **Cost per event** | High — hash chain computation | Low — time series append |
| **Failure behavior** | Missing audit = compliance violation | Missing observability = operational inconvenience |
| **Query model** | Point-in-time, actor-based, compliance reports | Time-series, rate queries, anomaly detection |
| **Data model** | Closed 30-action vocabulary, structured | Open schema — any component emits any metric |
| **Storage type** | Audit Store (specialized sub-type) | Time-series database (Prometheus, InfluxDB) |

### 9a.2 The Relationship

Observability data MAY reference audit record UUIDs for correlation — a spike in error rate can link to audit records from that time window. But they live in separate stores with separate contracts.

- **Audit** answers: "What happened and who authorized it?"
- **Observability** answers: "Is the system healthy and how is it performing?"

These are different questions requiring different storage architectures.

### 9a.3 System Policy

| Policy | Rule |
|--------|------|
| `AUD-013` | Audit and Observability are separate components with separate storage contracts, consumers, and failure behaviors. Audit is compliance-grade, append-only, hash-chained, long-retention. Observability is operational, time-series, high-throughput, short-retention. They serve different consumers and cannot be combined without violating one contract or the other. Observability data may reference audit record UUIDs for correlation but is stored separately. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
