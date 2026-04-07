# DCM Data Model — Test Framework Specification

**Document Status:** ✅ Complete
**Document Type:** Architecture Specification — Automated test framework contract for data model and architecture validation
**Related Documents:** [Foundations](00-foundations.md) | [Entity Types](01-entity-types.md) | [Four States](02-four-states.md) | [Policy Contract](B-policy-contract.md) | [Provider Contract](A-provider-contract.md) | [Infrastructure Requirements](51-infrastructure-optimization.md)

> **Purpose:** This document defines the contract for an automated, self-reflecting test framework
> that validates the DCM data model and architecture by generating random end-to-end use cases,
> executing them against the pipeline, and verifying invariants. The framework is designed to
> discover edge cases and feed required changes back into the architecture.

---

## 1. Framework Architecture

The test framework operates as a closed loop:

```
Generate → Execute → Verify → Analyze → Enhance → Generate
    ↑                                                 │
    └─────────────────────────────────────────────────┘
```

**Generate:** Create random but valid test scenarios from the architecture rules.
**Execute:** Run the scenario through the DCM pipeline (or a simulation of it).
**Verify:** Check all invariants — every rule in this document must hold.
**Analyze:** Identify failures, edge cases, and undocumented behaviors.
**Enhance:** Propose architecture or data model changes to accommodate discovered gaps.

---

## 2. Architecture Fundamentals (Framework Must Know)

### 2.1 Three Abstractions

Everything in DCM maps to one of three abstractions:

| Abstraction | What it governs | Key documents |
|-------------|----------------|---------------|
| **Data** | Entity lifecycle, four states, layering, versioning | docs 00-04, 11, 16 |
| **Provider** | External system integration, naturalization, discovery | doc A, docs 10, 19, 22, 30 |
| **Policy** | Evaluation, constraints, overrides, governance | doc B, doc 14 |

### 2.2 Four Data Domains

Every entity exists across four data domains simultaneously:

| Domain | Table | Immutability | Test assertion |
|--------|-------|-------------|----------------|
| Intent | `intent_records` | Append-only, never modified | `UPDATE` and `DELETE` must fail |
| Requested | `requested_records` | Append-only, never modified | `UPDATE` and `DELETE` must fail |
| Realized | `realized_entities` | Versioned snapshots, `is_current` flag | Only one `is_current=true` per entity_uuid |
| Discovered | `discovered_records` | Ephemeral, grouped by run | Records group by `discovery_run_uuid` |

### 2.3 Pipeline Stages

Every request flows through these stages in order:

```
1. Intent captured           → intent_records
2. Layers assembled          → core + service + tenant layers merged with precedence
3. Policies evaluated        → multi-pass convergence with Evaluation Context
4. Placement selected        → provider chosen from constrained candidates
5. Dispatched to provider    → payload sent via Operator Interface
6. Provider callback         → realized state received
7. Audit recorded            → Merkle tree leaf per mutation
```

### 2.4 Entity Types

| Type | Has persistent resources? | Lifecycle |
|------|--------------------------|-----------|
| `infrastructure_resource` | Yes | Full CRUD lifecycle |
| `composite_resource` | Yes (composed of children) | Parent lifecycle governs children |
| `process_resource` | No — ephemeral | PENDING → EXECUTING → terminal |
| `shared_resource` | Yes — multi-tenant | Stakeholder management |
| `allocatable_pool` | Yes — capacity tracking | Allocation/release |

### 2.5 Provider Types

| Type | Test scenarios |
|------|---------------|
| `service_provider` | Provisioning, decommission, discovery, drift |
| `information_provider` | Data queries, confidence scoring, staleness |
| `meta_provider` | Composition, dependency ordering, partial failure, compensation |
| `auth_provider` | Login, token validation, group claim mapping, session revocation |
| `peer_dcm` | Federation, cross-instance placement, entity migration |
| `process_provider` | Job execution, timeout, cancellation, result reporting |

### 2.6 Lifecycle Operation Types

| Operation | When | Full pipeline? | Placement? |
|-----------|------|---------------|------------|
| `initial_provisioning` | New resource | Yes | Yes |
| `update` | Modify existing | Partial — changed fields only | Only if placement-affecting fields changed |
| `scale` | Capacity change | Partial | Only if zone/provider-affecting |
| `rehydration` | Rebuild from state | Yes — all current policies | Yes |
| `decommission` | Remove resource | Decommission pipeline | No |
| `ownership_transfer` | Change tenant | Re-evaluate tenant policies | Possible |
| `subscription_renewal` | Subscription lifecycle | Subscription policies | Possible |
| `drift_remediation` | State divergence | Remediation policies | Possible |
| `provider_migration` | Move provider | Yes — full re-evaluation | Yes |
| `compliance_rescan` | Policy change | Re-evaluate all matching | Only if policy requires |

---

## 3. Policy Behavior Rules (Test Invariants)

### 3.1 Match Rules

| Rule ID | Invariant | Test |
|---------|-----------|------|
| MATCH-001 | A policy with no conditions fires on every request | Create universal policy → verify it fires on 10 random requests |
| MATCH-002 | A policy matching `resource_type: X` does not fire on resource_type Y | Create VM policy → verify it does not fire on Network.Port request |
| MATCH-003 | `condition_logic: all` requires all conditions to match | Create 3-condition policy → verify it fires only when all 3 match |
| MATCH-004 | `condition_logic: any` requires at least one condition | Create 3-condition policy with `any` → verify fires when 1 matches |
| MATCH-005 | Policies can match on `operation.type` | Create policy scoped to `rehydration` → verify it does not fire on `update` |
| MATCH-006 | `changed_field_filter` limits update/scale policy firing | Create policy with filter `["memory_gb"]` → verify it fires on memory change, not on tag change |
| MATCH-007 | Policies can match on `context.constraints.*` | Create policy that fires when `zone_restriction` exists in context → verify ordering |

### 3.2 Evaluation Rules

| Rule ID | Invariant | Test |
|---------|-----------|------|
| EVAL-001 | GateKeeper DENY blocks the request regardless of other policies | One ALLOW + one DENY → request blocked |
| EVAL-002 | Domain precedence: more-specific domain wins at same concern | System allows, tenant denies → denied for that tenant |
| EVAL-003 | Hard enforcement cannot be relaxed by downstream rules | System hard DENY → tenant ALLOW does not relax |
| EVAL-004 | Multi-pass convergence: max 3 passes then fail | Create irreconcilable constraints → verify failure after 3 passes |
| EVAL-005 | Constraint Type Registry: unregistered constraint types rejected at activation | Policy emitting unknown constraint type → activation fails |
| EVAL-006 | Template parameter validation: wrong types rejected | Create policy from template with invalid params → rejected |
| EVAL-007 | Evaluation Context is transient — does not persist between requests | Request A produces context → Request B does not see it |
| EVAL-008 | All policies produce audit records regardless of outcome | 5 policies fire → 5 audit leaves created |

### 3.3 Override Rules

| Rule ID | Invariant | Test |
|---------|-----------|------|
| OVRD-001 | Override Policy cannot target hard enforcement policy | Create override targeting hard policy → activation rejected |
| OVRD-002 | Exception Grant targeting hard policy requires dual-approval | Create grant without dual-approval → rejected |
| OVRD-003 | Manual Override of hard policy requires dual-approval | Submit manual override without second approver → rejected |
| OVRD-004 | Manual Override is single-request scoped | Use manual override → verify second request is still blocked |
| OVRD-005 | Exception Grant expires at declared time | Create grant expiring in 1 hour → verify grant inactive after expiry |
| OVRD-006 | Exception Grant usage tracking increments | Use grant 3 times → verify usage_count = 3 |
| OVRD-007 | fsi/sovereign profiles require dual-approval on ALL overrides | Standard-profile override without dual → accepted. Sovereign-profile → rejected |
| OVRD-008 | Every override produces an audit leaf | Manual override → verify audit leaf with override_target and justification |
| OVRD-009 | Compensating controls are enforced during exception grant | Grant requires enhanced-logging → verify field-granularity audit active during grant |
| OVRD-010 | Blocked request enters PENDING_OVERRIDE when no automatic resolution exists | Hard deny with no override policy/grant → verify status == PENDING_OVERRIDE |
| OVRD-011 | override.required event published when request enters PENDING_OVERRIDE | Block request → verify event published with blocking_policy and eligible_roles |
| OVRD-012 | Pipeline resumes from blocked stage after approval | Block at policy eval → approve → verify placement runs (not full restart) |
| OVRD-013 | Override timeout fails request with OVERRIDE_TIMEOUT | Block request → wait past timeout → verify status == OVERRIDE_TIMEOUT |
| OVRD-014 | Dual-approval: first approval alone does not resume pipeline | Hard block → first approve → verify status still PENDING_OVERRIDE |
| OVRD-015 | Dual-approval: same role cannot fill both slots | First approve as security_officer → second approve as security_officer → rejected |
| OVRD-016 | Override notification routes to correct channels per config | Configure webhook → block request → verify webhook called with correct payload |
| OVRD-017 | Escalation fires after configured delay with no response | Configure 1h escalation → block request → wait 1h → verify escalation notification |
| OVRD-018 | Blocked request presents resolution guidance with compliant values | Block on zone policy → verify guidance includes allowed zones |
| OVRD-019 | Consumer modify action re-enters pipeline from assembly | Block → modify to compliant value → verify pipeline resumes and succeeds |
| OVRD-020 | Consumer cancel action moves request to CANCELLED | Block → cancel → verify status == CANCELLED with audit trail |
| OVRD-021 | Block timeout auto-cancels request | Block request → wait past block timeout → verify status == CANCELLED |
| OVRD-022 | Consumer cannot request override if profile prohibits it | Configure profile to prohibit consumer overrides → block → verify override option unavailable |

### 3.4 Lifecycle Scope Rules

| Rule ID | Invariant | Test |
|---------|-----------|------|
| LSCOPE-001 | Policy with `lifecycle_scope: [initial_provisioning]` does not fire on update | Provision VM → update memory → verify policy fired on first, not second |
| LSCOPE-002 | fsi/sovereign cannot downgrade GateKeeper lifecycle scope below `all` | Create GateKeeper with scope `[initial_provisioning]` in sovereign profile → rejected |
| LSCOPE-003 | `changed_field_filter` is ignored for non-update operations | Initial provisioning with filter → filter ignored, policy fires |
| LSCOPE-004 | Default lifecycle scopes apply when not explicitly declared | Transformation policy with no scope → fires on `initial_provisioning` and `rehydration`, not on `scale` |

---

## 4. Data Integrity Invariants

### 4.1 Append-Only

| Rule ID | Invariant | Test |
|---------|-----------|------|
| DATA-001 | `intent_records` cannot be updated or deleted | Attempt UPDATE → verify failure |
| DATA-002 | `requested_records` cannot be updated or deleted | Attempt DELETE → verify failure |
| DATA-003 | `audit_records` cannot be updated or deleted | Attempt UPDATE by dcm_admin → verify failure (trigger guard) |

### 4.2 Merkle Tree

| Rule ID | Invariant | Test |
|---------|-----------|------|
| MRKL-001 | Every audit leaf has a valid signature | Fetch N random leaves → verify signatures against known keys |
| MRKL-002 | Inclusion proof verifies against current STH | Fetch random leaf → get inclusion proof → verify against latest STH |
| MRKL-003 | Consistency proof verifies append-only | Get STH at time T1 and T2 → consistency proof must validate |
| MRKL-004 | Request chain verification: output_hash[N] == input_hash[N+1] | Fetch all leaves for a request → verify hash chain |
| MRKL-005 | Tampering detection: modify any leaf → verification fails | Insert, verify, modify, re-verify → failure detected |
| MRKL-006 | Granularity level controls leaf count | Stage → ~6 leaves; mutation → ~15-30; field → same count, richer content |

### 4.3 Tenant Isolation

| Rule ID | Invariant | Test |
|---------|-----------|------|
| RLS-001 | dcm_app with tenant A context cannot read tenant B data | Set context to A → query B's records → zero rows |
| RLS-002 | RLS applies to all tenant-scoped tables | For each table with tenant_uuid: verify isolation |
| RLS-003 | dcm_admin bypasses RLS (separately audited) | Admin query → returns cross-tenant data + audit record |

---

## 5. Provider Contract Invariants

| Rule ID | Invariant | Test |
|---------|-----------|------|
| PROV-001 | Unregistered provider cannot receive dispatch | Attempt dispatch to unknown UUID → rejected |
| PROV-002 | Provider health check failure → provider marked degraded | Stop health endpoint → verify status change |
| PROV-003 | Provider callback must be signed with registered key | Callback with invalid signature → rejected |
| PROV-004 | Naturalization/denaturalization preserves entity UUID | Dispatch → callback → verify entity_uuid unchanged |
| PROV-005 | Meta provider failure triggers compensation | Fail constituent 2 of 3 → verify constituent 1 compensated |
| PROV-006 | Discovery produces discovered_records grouped by run | Trigger discovery → verify records share discovery_run_uuid |
| PROV-007 | Process provider reaches terminal state | Execute job → verify state is COMPLETED or FAILED, never OPERATIONAL |

---

## 6. Scenario Generation Rules

The framework generates random scenarios by combining:

### 6.1 Request Dimensions

| Dimension | Random selection from |
|-----------|---------------------|
| Resource type | Any registered resource type in catalog |
| Tenant | Random tenant from test tenant pool |
| Actor | Random actor with varying roles |
| Operation type | Random from 10 lifecycle operations |
| Profile | Random deployment profile |
| Data classification | Random from classification enum |
| Sovereignty zone | Random from available zones |
| Fields | Random field values within resource type schema |

### 6.2 Policy Environment

| Dimension | Random selection from |
|-----------|---------------------|
| Active policies | Random subset of policy library (1-20 policies) |
| Policy domains | Random domain assignments (system, platform, tenant) |
| Hard vs soft | Random enforcement levels |
| Constraint types | Random constraint emissions |
| Override state | Random active overrides (0-3 per scenario) |
| Exception grants | Random active grants (0-2 per scenario) |
| Profile constraints | Random profile with minimum lifecycle scope rules |

### 6.3 Provider Environment

| Dimension | Random selection from |
|-----------|---------------------|
| Available providers | Random subset (1-5 per resource type) |
| Provider health | Random health states (healthy, degraded, unavailable) |
| Capacity | Random capacity levels |
| Sovereignty zones | Random zone assignments per provider |
| Accreditation | Random accreditation states |

### 6.4 Expected Outcome Determination

For each generated scenario, the framework must be able to independently compute the expected outcome:

1. Which policies should fire (based on match conditions + lifecycle scope + operation type)
2. What constraints should be emitted (based on policy outputs)
3. Whether conflicts exist (based on constraint compatibility)
4. How conflicts resolve (based on on_conflict strategies)
5. Whether the request should succeed, fail, or escalate
6. What the audit trail should contain (based on granularity level)
7. Which overrides (if any) modify the evaluation

If the framework cannot determine the expected outcome from the architecture rules, that indicates an ambiguity in the architecture that needs resolution.

---

## 7. Edge Case Categories

The framework must specifically test:

### 7.1 Policy Interaction Edge Cases
- Two policies emitting contradictory hard constraints with no resolution strategy
- Policy A emits constraint → Policy B consumes it → Policy A changes on next pass → does B re-evaluate?
- Override policy targeting a policy that was deprecated between override creation and evaluation
- Exception grant expired mid-evaluation (between pass 1 and pass 2)
- Manual override authorized by actor who is deprovisioned before the request completes
- Compensating control policy that itself has a policy violation
- Circular constraint dependencies (A constrains B, B constrains A)

### 7.2 Provider Edge Cases
- Provider becomes unavailable between placement and dispatch
- Provider callback arrives after request timeout
- Meta provider: constituent 3 fails, compensation for constituent 1 also fails
- Discovery returns entity with confidence: unmatched while entity is in OPERATIONAL state
- Two providers claim the same external resource ID

### 7.3 Data Integrity Edge Cases
- Concurrent requests for the same entity (race condition)
- Audit leaf with timestamp before previous leaf (clock skew)
- Request that produces 0 audit leaves (should be impossible — test it)
- Merkle tree STH computed during concurrent writes
- Sovereignty zone boundary crossed during multi-pass evaluation

### 7.4 Lifecycle Edge Cases
- Decommission request while update request is in-flight for same entity
- Rehydration from intent where the original policy set no longer exists
- Scale operation that triggers placement re-evaluation (crosses zone capacity threshold)
- Ownership transfer where target tenant has different compliance profile
- Subscription renewal where provider has since been deregistered

---

## 8. Framework Output

### 8.1 Test Results

Each test run produces:
- Pass/fail for each invariant tested
- Scenario description (generated inputs + expected outcome + actual outcome)
- Mismatch details (expected vs actual with diff)
- Audit trail verification results

### 8.2 Architecture Enhancement Proposals

When the framework discovers a gap (an edge case with no defined behavior), it produces:

```yaml
enhancement_proposal:
  discovered_by: "test-run-2026-04-04-uuid"
  scenario: "Description of the edge case"
  gap: "What the architecture doesn't define"
  affected_documents: ["B-policy-contract.md", "16-universal-audit.md"]
  proposed_resolution: "Description of proposed fix"
  invariant_to_add: "New rule ID and assertion"
```

These proposals feed back into the architecture review cycle. The framework is a continuous validation mechanism, not a one-time test suite.

---

## 9. Machine-Readable Architecture Summary

This section provides the key facts in a format optimized for automated consumption.

```yaml
dcm_architecture:
  version: "0.1.0-alpha"

  required_infrastructure:
    - type: postgresql
      contract: "SQL, RLS, LISTEN/NOTIFY, JSONB, pgcrypto"

  internal_capabilities:
    authentication:
      method: "argon2id + DCM-issued JWT"
      table: actors
    secrets:
      method: "AES-256-GCM envelope encryption"
      table: secrets
    events:
      method: "LISTEN/NOTIFY on pipeline_events"
      table: pipeline_events

  provider_types: [service, information, meta, auth, peer_dcm, process]

  entity_types: [infrastructure_resource, composite_resource, process_resource, shared_resource, allocatable_pool]

  data_domains:
    - name: intent
      table: intent_records
      immutability: append_only
    - name: requested
      table: requested_records
      immutability: append_only
    - name: realized
      table: realized_entities
      immutability: versioned_snapshots
    - name: discovered
      table: discovered_records
      immutability: ephemeral

  lifecycle_operations:
    - initial_provisioning
    - update
    - scale
    - rehydration
    - decommission
    - ownership_transfer
    - subscription_renewal
    - drift_remediation
    - provider_migration
    - compliance_rescan

  policy:
    types: [gatekeeper, validation, transformation, recovery, orchestration_flow, governance_matrix_rule, lifecycle, itsm_action]
    evaluation_modes: [internal, external]
    match_sources: [request_payload, operation_context, evaluation_context, entity_metadata]
    max_evaluation_passes: 3
    constraint_resolution: [auto, escalate, deny]
    override_mechanisms: [override_policy, exception_grant, manual_override, dual_approval, compensating_control]

  audit:
    structure: merkle_tree
    standard: "RFC 9162"
    granularity_levels: [stage, mutation, field]
    verification: [inclusion_proof, consistency_proof, request_chain_verification]
    signing_algorithm: "Ed25519 or ECDSA-P256"
    hash_algorithm: "SHA-256"

  control_plane_services:
    - api_gateway
    - service_provider_manager
    - catalog_manager
    - policy_manager
    - placement_manager
    - request_orchestrator
    - request_processor
    - audit_service
    - discovery_service

  sql_tables: 18
  capabilities: 331
  capability_domains: 39
  consumer_api_paths: 74
  admin_api_paths: 61
  event_payloads: 109
  event_domains: 23
```

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
