# DCM Data Model — Event Catalog

**Document Status:** ✅ Complete
**Document Type:** Architecture Reference — Authoritative Event Catalog
**Related Documents:** [Notification Model](23-notification-model.md) | [Webhooks and Messaging](18-webhooks-messaging.md) | [Universal Audit](16-universal-audit.md) | [Credential Provider Model](31-credential-provider-model.md) | [Authority Tier Model](32-authority-tier-model.md) | [Control Plane Components](25-control-plane-components.md)

> **This is the single authoritative source for all DCM event types.**
>
> The Notification Model (doc 23) defines delivery pipeline, audience resolution, and urgency routing. The Webhooks doc (doc 18) defines the Message Bus integration. This document defines **what events exist, when they fire, and what their payloads contain**. Any document referencing an event type is authoritative only if it agrees with this catalog. Conflicts resolve in favor of this document.

> **Implementation note:** Consumers (webhook receivers, Notification Providers, Message Bus subscribers, audit tooling) must implement idempotency using `event_uuid`. Events are delivered at-least-once. Per-entity ordering is guaranteed; cross-entity ordering is not.

---

## 1. Base Envelope

Every DCM event shares a common envelope. Event-specific fields are in the `payload` object.

```yaml
# DCM Event Envelope — all events
event_uuid: <uuid>                  # idempotency key; stable across retries
event_type: <string>                # fully qualified: domain.event_name
event_schema_version: "1.0"         # increments on breaking payload changes
timestamp: <ISO 8601>               # from Commit Log — authoritative source of truth
dcm_version: <semver>               # DCM instance version that generated the event
dcm_instance_uuid: <uuid>           # identifies the DCM instance (federation context)

subject:
  entity_uuid: <uuid | null>        # primary entity this event concerns
  entity_type: <string | null>      # entity type FQN (e.g. Compute.VirtualMachine)
  entity_handle: <string | null>    # human-readable identifier
  tenant_uuid: <uuid | null>        # tenant scope; null for system-scope events
  actor_uuid: <uuid | null>         # actor who triggered the event; null for system events

urgency: critical | high | medium | low | info   # governs notification routing

payload: {}                         # event-specific fields — see Section 3+

links:
  self: <url>                       # DCM API URL for the subject entity or record
  audit_record: <url>               # DCM API URL for the audit record for this event
```

### 1.1 Urgency Levels

| Urgency | Meaning | Delivery expectation |
|---------|---------|---------------------|
| `critical` | Security or compliance event requiring immediate action | Push notification; page if configured |
| `high` | Significant operational event; action likely required | Push notification |
| `medium` | Notable event; review recommended | Standard delivery |
| `low` | Informational; action unlikely required | Standard delivery |
| `info` | Observational; no action expected | Batch or webhook only |

### 1.2 Schema Versioning

`event_schema_version` increments when breaking changes occur to the `payload` schema for an event type. Consumers should validate against the declared version. Non-breaking additions (new optional fields) do not increment the version.

---

## 2. Event Domain Index

| Domain | Events | Description |
|--------|--------|-------------|
| `request.*` | 14 | Request pipeline lifecycle |
| `entity.*` | 13 | Resource entity lifecycle |
| `drift.*` | 4 | Drift detection and resolution |
| `provider.*` | 5 | Provider registration and health |
| `provider_update.*` | 5 | Provider-initiated update lifecycle |
| `rehydration.*` | 5 | Entity rehydration lifecycle |
| `policy.*` | 4 | Policy contribution lifecycle |
| `credential.*` | 4 | Credential lifecycle |
| `approval.*` | 4 | Approval pipeline |
| `tier_registry.*` | 4 | Authority tier registry changes |
| `audit.*` | 3 | Audit chain integrity |
| `dependency.*` | 2 | Entity dependency events |
| `stakeholder.*` | 1 | Stakeholder notifications |
| `allocation.*` | 2 | Resource allocation events |
| `ingestion.*` | 3 | Brownfield ingestion lifecycle |
| `governance.*` | 3 | Catalog and profile governance |
| `security.*` | 2 | Security and sovereignty events |
| `sovereignty.*` | 2 | Sovereignty constraint events |
| `federation.*` | 1 | Federation tunnel events |
| `auth.*` | 1 | Authentication provider events |
| **Total** | **82** | |

---

## 3. Request Events (`request.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `request.submitted` | info | Consumer submitted a request via API or UI |
| `request.intent_captured` | info | Intent State created; entity UUID assigned |
| `request.layers_assembled` | info | Layer assembly complete; compound payload ready for policy evaluation |
| `request.policies_evaluated` | info | Policy evaluation complete; score computed; routing tier determined |
| `request.requires_approval` | medium | Score routed to `reviewed`, `verified`, or `authorized` tier; pipeline holds |
| `request.approved` | info | Required tier approval recorded; pipeline resumes |
| `request.placement_complete` | info | Provider placement complete; Requested State committed |
| `request.dispatched` | info | Payload dispatched to provider(s) |
| `request.compound_assembled` | info | Compound service payload assembled (Meta Provider compound request) |
| `request.dependencies_resolved` | info | Constituent dependencies resolved (Meta Provider) |
| `request.realized` | medium | Provider confirmed realization; Realized State written |
| `request.failed` | high | Request failed at any stage |
| `request.gatekeeper_rejected` | high | GateKeeper policy denied the request |
| `request.cancelled` | low | Consumer cancelled; pipeline terminated |
| `request.progress_updated` | info | Provider sent interim progress update; constituent_status updated |

### 3.1 Payload Schemas

#### `request.submitted` / `request.intent_captured`
```yaml
payload:
  request_uuid: <uuid>
  catalog_item_uuid: <uuid>
  catalog_item_handle: <string>
  resource_type: <string>            # FQN e.g. Compute.VirtualMachine
  submitted_fields: {}               # consumer-declared fields (may be partial)
```

#### `request.layers_assembled` / `request.policies_evaluated`
```yaml
payload:
  request_uuid: <uuid>
  risk_score: <0-100>                # present after policies_evaluated
  routing_tier: auto | reviewed | verified | authorized | <custom>
  score_drivers:                     # top contributing signals
    - signal: operational_gatekeeper
      contribution: 12
```

#### `request.requires_approval`
```yaml
payload:
  request_uuid: <uuid>
  approval_uuid: <uuid>
  required_tier: reviewed | verified | authorized | <custom>
  required_tier_gravity: routine | elevated | critical
  risk_score: <0-100>
  window_expires_at: <ISO 8601>
  dcmgroup_uuid: <uuid | null>       # non-null for authorized tier
  quorum_required: <N | null>
```

#### `request.realized` / `request.failed`
```yaml
payload:
  request_uuid: <uuid>
  provider_uuid: <uuid>
  outcome: realized | failed | degraded
  failure_reason: <string | null>
  realized_fields: {}                # key provider-returned values (IP, VM ID, etc.)
  composite_status: <string | null>  # for compound requests
```

#### `request.gatekeeper_rejected`
```yaml
payload:
  request_uuid: <uuid>
  policy_handle: <string>
  enforcement_class: compliance | operational
  rejection_reason: <string>
  risk_score: <0-100>
```

---

## 4. Entity Lifecycle Events (`entity.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `entity.realized` | medium | Entity first realized; Realized State written |
| `entity.state_changed` | medium | Entity lifecycle state transition |
| `entity.modified` | info | Entity fields updated (Day-2 operation) |
| `entity.ttl_warning` | medium | TTL expires within declared warning window |
| `entity.ttl_expired` | high | TTL reached; expiry action triggered |
| `entity.suspended` | high | Entity entered SUSPENDED state |
| `entity.resumed` | medium | Entity exited SUSPENDED state |
| `entity.decommissioning` | medium | Decommission pipeline initiated |
| `entity.decommissioned` | low | Entity fully decommissioned; resources released |
| `entity.decommission_deferred` | medium | Decommission blocked by active stakes |
| `entity.ownership_transferred` | medium | Ownership moved to a different Tenant |
| `entity.pending_review` | medium | Entity entered PENDING_REVIEW state |
| `entity.expired` | high | Entity reached terminal expired state |

### 4.1 Payload Schemas

#### `entity.realized`
```yaml
payload:
  request_uuid: <uuid>
  provider_uuid: <uuid>
  realized_fields: {}                # key fields returned by provider
  composite_entity: <bool>           # true for Meta Provider compound services
  composite_status: <string | null>
```

#### `entity.state_changed`
```yaml
payload:
  previous_state: <string>
  new_state: <string>
  triggered_by: ttl | decommission | consumer | policy | provider | system
  reason: <string | null>
```

#### `entity.ttl_warning` / `entity.ttl_expired`
```yaml
payload:
  ttl_expires_at: <ISO 8601>
  expiry_action: decommission | suspend | notify_only
  warning_window: <ISO 8601 duration>  # e.g. P7D
```

#### `entity.decommissioning` / `entity.decommissioned`
```yaml
payload:
  initiated_by: <actor_uuid | null>
  initiated_at: <ISO 8601>
  reason: <string | null>
  stakes_resolved: <bool>
  credential_revocation_status: complete | partial | pending
```

#### `entity.decommission_deferred`
```yaml
payload:
  blocking_stakes:
    - stake_uuid: <uuid>
      stake_type: required | management
      stakeholder_tenant_uuid: <uuid>
      stakeholder_entity_uuid: <uuid>
  retry_after: <ISO 8601 | null>
```

#### `entity.ownership_transferred`
```yaml
payload:
  previous_owner_tenant_uuid: <uuid>
  new_owner_tenant_uuid: <uuid>
  transfer_reason: <string | null>
  transferred_by: <actor_uuid>
```

---

## 5. Drift Events (`drift.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `drift.detected` | high | Discovered State differs from Realized State |
| `drift.severity_escalated` | high | Drift severity increased (e.g. minor → significant) |
| `drift.resolved` | low | Drift resolved via REVERT or UPDATE_DEFINITION |
| `drift.escalated` | high | Drift escalated to human review |

### 5.1 Payload Schemas

#### `drift.detected`
```yaml
payload:
  drift_record_uuid: <uuid>
  drift_severity: minor | moderate | significant | critical
  drifted_fields:
    - field: <string>                # field path e.g. "cpu_count"
      realized_value: <any>
      discovered_value: <any>
  discovery_run_uuid: <uuid>
  discovered_at: <ISO 8601>
```

#### `drift.severity_escalated`
```yaml
payload:
  drift_record_uuid: <uuid>
  previous_severity: minor | moderate | significant | critical
  new_severity: minor | moderate | significant | critical
  escalation_trigger: time_elapsed | field_count | field_sensitivity
```

#### `drift.resolved`
```yaml
payload:
  drift_record_uuid: <uuid>
  resolution: REVERT | UPDATE_DEFINITION | MANUAL
  resolved_by: <actor_uuid | null>
  resolved_at: <ISO 8601>
```

---

## 6. Provider Events (`provider.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `provider.registered` | info | Provider successfully registered and activated |
| `provider.deregistered` | medium | Provider deregistered; active entities may be affected |
| `provider.healthy` | info | Provider health check returned healthy after unhealthy period |
| `provider.unhealthy` | high | Provider health check failed |
| `provider.degraded` | high | Provider reporting degraded capacity |

### 6.1 Payload Schemas

#### `provider.registered` / `provider.deregistered`
```yaml
payload:
  provider_uuid: <uuid>
  provider_type: service_provider | meta_provider | service_provider | auth_provider | ...
  provider_handle: <string>
  resource_types_affected: [<string>]  # on deregistered: types now unserviced
  active_entity_count: <int>           # on deregistered: entities at risk
```

#### `provider.unhealthy` / `provider.degraded`
```yaml
payload:
  provider_uuid: <uuid>
  health_check_uuid: <uuid>
  failure_reason: <string>
  consecutive_failures: <int>
  last_healthy_at: <ISO 8601>
  affected_resource_types: [<string>]
```

---

## 7. Provider Update Events (`provider_update.*`)

Provider-initiated update notifications — when a provider reports a change to an entity it manages.

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `provider_update.submitted` | medium | Provider submitted an update notification for a realized entity |
| `provider_update.requires_approval` | medium | Provider update requires consumer approval before applying |
| `provider_update.approved` | info | Consumer approved; Realized State updated |
| `provider_update.rejected` | medium | Consumer rejected; update becomes tracked drift |
| `provider_update.auto_approved` | info | Update auto-approved per policy |

### 7.1 Payload Schema

```yaml
payload:
  provider_update_uuid: <uuid>
  provider_uuid: <uuid>
  update_type: patch | deprecation | security_advisory | capacity_change
  update_summary: <string>
  proposed_field_changes: {}         # what the provider wants to change
  approval_required: <bool>
  approval_uuid: <uuid | null>
```

---

## 8. Rehydration Events (`rehydration.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `rehydration.started` | info | Rehydration pipeline initiated |
| `rehydration.paused` | medium | Rehydration paused (e.g. waiting on dependent constituent) |
| `rehydration.interrupted` | high | Rehydration interrupted by error or cancellation |
| `rehydration.completed` | medium | All constituents rehydrated; entity OPERATIONAL |
| `rehydration.blocked` | high | Rehydration blocked — provider unavailable or policy prevents |

### 8.1 Payload Schema

```yaml
payload:
  rehydration_uuid: <uuid>
  trigger: ttl_expiry | manual | drift_recovery | system
  constituents_total: <int>
  constituents_complete: <int>
  block_reason: <string | null>      # for rehydration.blocked
```

---

## 9. Policy Events (`policy.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `policy.activated` | medium | Policy promoted from shadow to active |
| `policy.deactivated` | medium | Policy deactivated |
| `policy.evaluated` | info | Policy evaluated against a request payload (shadow or active) |
| `policy.shadow_result` | info | Shadow evaluation diverged from expected outcome |

### 9.1 Payload Schema

#### `policy.activated` / `policy.deactivated`
```yaml
payload:
  policy_uuid: <uuid>
  policy_handle: <string>
  policy_type: gatekeeper | validation | transformation | recovery | orchestration_flow
  enforcement_class: compliance | operational    # for gatekeeper
  shadow_period_days: <int>
  approved_by: <actor_uuid>
```

#### `policy.shadow_result`
```yaml
payload:
  policy_uuid: <uuid>
  request_uuid: <uuid>
  shadow_decision: allow | deny | transform
  active_decision: allow | deny | transform      # what active policies decided
  diverged: <bool>
  divergence_detail: <string | null>
```

---

## 10. Credential Events (`credential.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `credential.rotating` | medium | Rotation initiated; transition window open |
| `credential.revoked` | high | Credential revoked; all holders must stop using |
| `credential.idle` | medium | Credential not retrieved within profile threshold |
| `credential.expired` | medium | Credential reached `expires_at`; no longer valid |

### 10.1 Payload Schema

#### `credential.rotating`
```yaml
payload:
  credential_uuid: <uuid>           # old credential
  new_credential_uuid: <uuid>
  rotation_trigger: pre_expiry | scheduled | security_event | actor_request
  transition_window_ends: <ISO 8601>
  retrieval_url: <url>              # where to retrieve new value
```

#### `credential.revoked`
```yaml
payload:
  credential_uuid: <uuid>
  revocation_trigger: actor_deprovisioned | entity_decommissioned | security_event | ...
  revocation_reason: <string>
  effective_at: <ISO 8601>
  entity_uuid: <uuid | null>
```

#### `credential.idle`
```yaml
payload:
  credential_uuid: <uuid>
  credential_type: <string>
  issued_at: <ISO 8601>
  threshold_elapsed: <ISO 8601 duration>
  retrieval_count: 0
```

---

## 11. Approval Events (`approval.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `approval.decision_recorded` | info | A reviewer recorded an approve or reject decision |
| `approval.quorum_reached` | medium | Authorized tier quorum satisfied; pipeline resuming |
| `approval.window_expiring` | medium | Approval window approaching expiry (75% elapsed) |
| `approval.expired` | high | Approval window expired without decision |

### 11.1 Payload Schema

#### `approval.decision_recorded`
```yaml
payload:
  approval_uuid: <uuid>
  subject_type: request | policy_contribution | provider_registration | federation_contribution
  subject_uuid: <uuid>
  required_tier: reviewed | verified | authorized | <custom>
  decision: approve | reject
  voter_uuid: <uuid>
  recorded_via: dcm_admin_ui | servicenow | jira | slack_bot | api_direct | other
  votes_recorded: <int>
  quorum_required: <int | null>
  quorum_reached: <bool>
```

#### `approval.expired`
```yaml
payload:
  approval_uuid: <uuid>
  subject_type: <string>
  subject_uuid: <uuid>
  required_tier: <string>
  votes_recorded: <int>
  quorum_required: <int | null>
  expiry_action: reject | escalate
```

---

## 12. Tier Registry Events (`tier_registry.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `tier_registry.proposed` | medium | Tier registry change proposed; impact assessment starting |
| `tier_registry.impact_assessed` | medium | Tier impact diff complete; review may be required |
| `tier_registry.degradation_detected` | high | SECURITY_DEGRADATION items found; activation blocked |
| `tier_registry.activated` | medium | Tier registry change activated; new list in effect |

### 12.1 Payload Schema

#### `tier_registry.proposed`
```yaml
payload:
  registry_change_uuid: <uuid>
  proposed_by: <actor_uuid>
  tiers_added: [<string>]
  tiers_removed: [<string>]
  tiers_repositioned: [<string>]
```

#### `tier_registry.impact_assessed`
```yaml
payload:
  registry_change_uuid: <uuid>
  degradations: <int>
  broken_references: <int>
  profile_gaps: <int>
  upgrades: <int>
  activation_blocked: <bool>
```

#### `tier_registry.degradation_detected`
```yaml
payload:
  registry_change_uuid: <uuid>
  affected_item_uuid: <uuid>
  affected_item_type: <string>
  tier_name: <string>
  old_gravity: none | routine | elevated | critical
  new_gravity: none | routine | elevated | critical
  acceptance_required_by: <ISO 8601>
```

---

## 13. Audit Events (`audit.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `audit.chain_integrity_alert` | critical | Hash chain verification failed; audit trail may be compromised |
| `audit.chain_break` | critical | Explicit break detected in audit hash chain |
| `audit.forward_failed` | high | Audit record failed to forward to external audit sink |

### 13.1 Payload Schema

#### `audit.chain_integrity_alert`
```yaml
payload:
  affected_record_uuid: <uuid>
  expected_hash: <string>
  actual_hash: <string>
  chain_segment_start: <uuid>
  chain_segment_end: <uuid>
  records_in_segment: <int>
```

---

## 14. Dependency and Stakeholder Events

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `dependency.state_changed` | medium | A dependency entity changed state; dependents may be affected |
| `stakeholder.resource_decommissioning` | medium | Resource this actor has a stake in is being decommissioned |
| `allocation.pool_capacity_low` | high | Allocation pool approaching capacity limit |
| `allocation.released` | info | Allocation returned to pool |

### 14.1 Payload Schemas

#### `dependency.state_changed`
```yaml
payload:
  dependency_entity_uuid: <uuid>
  previous_state: <string>
  new_state: <string>
  dependent_entity_uuids: [<uuid>]
  impact_assessment: degraded | blocked | unaffected
```

#### `stakeholder.resource_decommissioning`
```yaml
payload:
  resource_entity_uuid: <uuid>
  stake_type: required | management | informational
  decommission_at: <ISO 8601 | null>
  action_required: <bool>            # true for required stakes
  action_url: <url | null>
```

---

## 15. Ingestion Events (`ingestion.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `ingestion.transitional_created` | info | Brownfield entity created as Transitional entity |
| `ingestion.enriched` | info | Transitional entity enriched with additional data |
| `ingestion.promotion_approved` | medium | Transitional entity approved for promotion to full DCM entity |

### 15.1 Payload Schema

```yaml
payload:
  ingestion_record_uuid: <uuid>
  source_system: <string>
  entity_handle: <string>
  confidence_level: high | medium | low
  missing_fields: [<string>]         # for ingestion.enriched
  promoted_entity_uuid: <uuid | null> # for ingestion.promotion_approved
```

---

## 16. Governance Events (`governance.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `governance.catalog_item_deprecated` | medium | Service catalog item marked for deprecation |
| `governance.profile_changed` | high | Active profile configuration changed |
| `governance.policy_trust_elevated` | medium | Policy provider trust level elevated |

### 16.1 Payload Schema

#### `governance.profile_changed`
```yaml
payload:
  previous_profile: <string>
  new_profile: <string>
  changed_by: <actor_uuid>
  effective_at: <ISO 8601>
  affected_threshold_tiers: [<string>]
```

---

## 17. Security and Sovereignty Events

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `security.unsanctioned_provider_write` | critical | Provider wrote to an entity without a corresponding Requested State record |
| `sovereignty.violation` | critical | Data or operation crossed a declared sovereignty boundary |
| `sovereignty.migration_required` | high | Entity must migrate to comply with sovereignty constraints |
| `federation.tunnel_degraded` | high | Federation tunnel to peer DCM degraded or unavailable |
| `auth.provider_failover` | high | Auth Provider failed; failover to secondary |

### 17.1 Payload Schemas

#### `security.unsanctioned_provider_write`
```yaml
payload:
  provider_uuid: <uuid>
  entity_uuid: <uuid>
  write_detected_at: <ISO 8601>
  changed_fields: [<string>]
  discovery_run_uuid: <uuid>
```

#### `sovereignty.violation`
```yaml
payload:
  violation_type: data_boundary | operation_boundary | residency_requirement
  constraint_uuid: <uuid>
  constraint_handle: <string>
  triggering_operation: <string>
  remediation_required: <bool>
```

---

## 18. System Policies

| Policy | Rule |
|--------|------|
| `EVT-001` | Every event must include the base envelope fields (`event_uuid`, `event_type`, `event_schema_version`, `timestamp`, `dcm_version`, `dcm_instance_uuid`, `urgency`). Events omitting required envelope fields are invalid and must not be published. |
| `EVT-002` | `event_uuid` is the idempotency key. Consumers must treat duplicate `event_uuid` values as already-processed. DCM may re-deliver events on failure; this is not a bug. |
| `EVT-003` | `timestamp` is sourced from the Commit Log Stage 1 write. It represents when the event was authoritatively recorded, not when it was delivered. |
| `EVT-004` | `event_schema_version` must increment on any breaking change to a payload schema. Adding optional fields is not a breaking change. Removing fields, changing field types, or changing field semantics are breaking changes. |
| `EVT-005` | Events with `urgency: critical` must be delivered via the push channel if the Notification Provider supports it, regardless of consumer subscription preferences. |
| `EVT-006` | This catalog is the authoritative source for event type names. Any event type not in this catalog is non-standard. Non-standard events may be published by providers or extensions but must use a reverse-DNS prefix (e.g. `com.acme.custom_event`). |
| `EVT-007` | The `audit.*` events with `urgency: critical` are non-suppressable. They are delivered regardless of audience subscription rules and cannot be filtered by consumer preference. |

---

## 21. ITSM Events (`itsm.*`)

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `itsm.record_created` | info | ITSM Provider successfully created a record in the external ITSM system |
| `itsm.record_updated` | info | ITSM Provider successfully updated an existing ITSM record |
| `itsm.record_failed` | medium | ITSM Provider failed to create/update a record; or `block_until_created` timeout reached |

### 21.1 Payload Schema

#### `itsm.record_created` / `itsm.record_updated`
```yaml
payload:
  itsm_provider_uuid: <uuid>
  itsm_system: servicenow | jira_service_management | ...
  action: create_change_request | create_incident | ...
  record_type: change_request | incident | cmdb_ci | service_request
  record_id: "<external-record-id>"    # e.g. CHG0012345, INC-4821
  record_url: "<url>"                  # deep link to record in ITSM system
  policy_handle: "<string>"            # which ITSM Policy triggered this
  stored_on_entity: <bool>

```

#### `itsm.record_failed`
```yaml
payload:
  itsm_provider_uuid: <uuid>
  action: <string>
  failure_reason: <string>
  timeout_expired: <bool>             # true if block_until_created timeout hit
  policy_handle: <string>
```

---

## 20. Accreditation Events (`accreditation.*`)

Fired by the Accreditation Monitor (doc 47) when external verification
of a registered accreditation produces a result or requires attention.

| Event Type | Urgency | Description |
|-----------|---------|-------------|
| `accreditation.verified` | low | Periodic external confirmation — accreditation still active in external registry |
| `accreditation.status_changed` | high or critical | External registry reports a different status than DCM records — requires platform admin review |
| `accreditation.registry_mismatch` | high | External registry cannot find the accreditation by its `external_registry_id` — ID may need correction |
| `accreditation.verification_stale` | varies | `last_checked_at` exceeds `stale_after` threshold — stale_action applied per configuration |
| `accreditation.document_expired` | high | Evidence document (SOC 2 report, AoC) is older than `max_age` threshold — new document required |
| `accreditation.contract_event` | varies | Contract management webhook received (BAA signed, amended, or terminated) |
| `accreditation.expiry_approaching` | medium | Approaching `expires_at` within `renewal_warning_before` window (automated complement to TTL-based check) |

### 20.1 Payload Schemas

```yaml
# accreditation.status_changed — the most critical event
accreditation.status_changed:
  accreditation_uuid: <uuid>
  subject_uuid: <provider-or-deployment-uuid>
  framework: fedramp_high | iso_27001 | cmmc_2 | ...
  from_status: authorized | active | certified
  to_status: in_process | revoked | suspended | withdrawn
  external_source: fedramp_marketplace | cmmc_ab | iaf_certsearch | contract_webhook
  detected_at: <ISO 8601>
  action_taken: pending_review | immediate_revocation
  # immediate_revocation when to_status is 'revoked' or 'terminated'

# accreditation.verification_stale
accreditation.verification_stale:
  accreditation_uuid: <uuid>
  subject_uuid: <uuid>
  framework: <string>
  last_checked_at: <ISO 8601>
  stale_after: P7D
  stale_action_taken: warn | suspended | escalated
  consecutive_failures: <integer>

# accreditation.contract_event
accreditation.contract_event:
  accreditation_uuid: <uuid>
  subject_uuid: <uuid>
  framework: hipaa | dod_il4 | <custom>
  contract_event_type: signed | amended | terminated | renewal_due | renewed
  contract_id: <string>
  effective_date: <ISO 8601>
  dcm_action_taken: activated | pending_review | revoked | none
```

### 20.2 System Policy

| Policy | Rule |
|--------|------|
| `EVT-ACM-001` | `accreditation.status_changed` events with `action_taken: immediate_revocation` are non-suppressable — they are delivered to Compliance Team and Platform Admin regardless of notification preferences. |
| `EVT-ACM-002` | `accreditation.verification_stale` urgency is profile-governed: `low` for dev/standard; `medium` for prod; `high` for fsi/sovereign. |

---


## 19. Event Type Quick Reference

```
request.submitted          request.intent_captured      request.layers_assembled
request.policies_evaluated request.requires_approval    request.approved
request.placement_complete request.dispatched            request.compound_assembled
request.dependencies_resolved  request.realized          request.failed
request.gatekeeper_rejected    request.cancelled

entity.realized            entity.state_changed         entity.modified
entity.ttl_warning         entity.ttl_expired           entity.suspended
entity.resumed             entity.decommissioning       entity.decommissioned
entity.decommission_deferred   entity.ownership_transferred  entity.pending_review
entity.expired

drift.detected             drift.severity_escalated     drift.resolved
drift.escalated

provider.registered        provider.deregistered        provider.healthy
provider.unhealthy         provider.degraded

provider_update.submitted  provider_update.requires_approval  provider_update.approved
provider_update.rejected   provider_update.auto_approved

rehydration.started        rehydration.paused           rehydration.interrupted
rehydration.completed      rehydration.blocked

policy.activated           policy.deactivated           policy.evaluated
policy.shadow_result

credential.rotating        credential.revoked           credential.idle
credential.expired

approval.decision_recorded approval.quorum_reached      approval.window_expiring
approval.expired

tier_registry.proposed     tier_registry.impact_assessed
tier_registry.degradation_detected  tier_registry.activated

audit.chain_integrity_alert  audit.chain_break          audit.forward_failed

dependency.state_changed   stakeholder.resource_decommissioning
allocation.pool_capacity_low  allocation.released

ingestion.transitional_created  ingestion.enriched      ingestion.promotion_approved

governance.catalog_item_deprecated  governance.profile_changed
governance.policy_trust_elevated

security.unsanctioned_provider_write
sovereignty.violation      sovereignty.migration_required
federation.tunnel_degraded
auth.provider_failover
```

**Total: 85 event types across 21 domains**

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

### Additional Event Types

| Event Type | Description | Key Fields | Consumers |
|------------|-------------|-----------|----------|
| `entity.deleted` | An entity has been fully decommissioned and removed from inventory | entity_uuid, from_state, to_state (where applicable) | LCM, AUD, OBS |
| `entity.state_transition` | An entity lifecycle state has changed (e.g., OPERATIONAL → SUSPENDED) | entity_uuid, from_state, to_state (where applicable) | LCM, AUD, OBS |
| `group.deleted` | A DCMGroup has been deleted | entity_uuid, from_state, to_state (where applicable) | LCM, AUD, OBS |
| `group.member_added` | A member (actor or entity) has been added to a DCMGroup | entity_uuid, from_state, to_state (where applicable) | LCM, AUD, OBS |
| `group.member_removed` | A member (actor or entity) has been removed from a DCMGroup | entity_uuid, from_state, to_state (where applicable) | LCM, AUD, OBS |
| `authorization.granted` | A cross-tenant authorization has been granted | entity_uuid, from_state, to_state (where applicable) | LCM, AUD, OBS |
