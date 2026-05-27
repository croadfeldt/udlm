# DCM Data Model — Operational Models


**Document Status:** ✅ Complete
**Document Type:** Architecture Reference

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: POLICY**
>
> The Policy abstraction — Recovery Policy types, trigger vocabulary, action vocabulary


**Related Documents:** [Four States](02-four-states.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Service Dependencies](07-service-dependencies.md) | [Policy Profiles](14-policy-profiles.md) | [Notification Model](23-notification-model.md)

---

## 1. Purpose

This document defines the operational models that govern DCM behavior at the edges of the normal provisioning lifecycle — when things go wrong, take too long, or produce ambiguous outcomes. Four operational models are defined:

1. **Timeout Model** — assembly, dispatch, and reserve-query timeouts
2. **Cancellation Propagation Model** — consumer-initiated cancellation at any lifecycle stage
3. **Discovery Scheduling Model** — what triggers discovery cycles and how they are managed
4. **Recovery Policy Model** — the unified, policy-governed response to all failure and ambiguity scenarios

The Recovery Policy Model is the foundational concept. Timeouts, cancellation outcomes, partial realization, and compensation failures all produce trigger conditions that Recovery Policies handle. Organizations declare their recovery posture via profile-bound Policy Groups — not via ad-hoc per-incident decisions.

---

## 2. Timeout Model

### 2.1 Three Timeout Scopes

There are three distinct timeout concerns in the DCM pipeline. Each is independently configurable and independently audited.

```yaml
timeout_declarations:
  assembly_timeout:
    description: "Maximum time for the Request Payload Processor to complete nine-step assembly"
    profile_defaults:
      minimal: PT5M
      dev: PT5M
      standard: PT3M
      prod: PT2M
      fsi: PT2M
      sovereign: PT2M
    on_timeout: trigger ASSEMBLY_TIMEOUT recovery policy
    includes: layer_resolution, policy_evaluation, placement_engine_loop
    # Assembly timeout fires if the total assembly pipeline exceeds this duration
    # Individual sub-steps also have per-step timeouts (see below)

  dispatch_timeout:
    description: "Maximum time to wait for provider realization after dispatch"
    profile_defaults:
      minimal: PT2H
      dev: PT1H
      standard: PT1H
      prod: PT30M
      fsi: PT30M
      sovereign: PT30M
    resource_type_overrides:
      # Some resource types legitimately take longer to provision
      Compute.BareMetalServer: PT4H
      Storage.LargeVolume: PT2H
    on_timeout: trigger DISPATCH_TIMEOUT recovery policy

  reserve_query_timeout:
    description: "Maximum time for a single provider to respond to a reserve query"
    profile_defaults:
      minimal: PT30S
      dev: PT30S
      standard: PT10S
      prod: PT5S
      fsi: PT5S
      sovereign: PT10S
    on_timeout: skip this provider; continue placement loop with remaining candidates
    # Reserve query timeout does not trigger RESERVE_QUERY_TIMEOUT recovery policy
    # unless ALL candidates have timed out or been exhausted
```

### 2.2 Per-Step Assembly Sub-Timeouts

The nine-step assembly has per-step sub-timeouts. These are not independently configurable — they are proportional fractions of the assembly_timeout:

| Step | Fraction of assembly_timeout |
|------|----------------------------|
| Layer Resolution | 20% |
| Layer Merge | 10% |
| Policy Evaluation (each policy) | 15% total, 5% per Mode 1/2, 30s per Internal evaluation, PT2M per external evaluation |
| Placement Engine Loop | 40% |
| Requested State Persistence | 10% |

A external policy evaluation that takes longer than PT2M per query causes an ASSEMBLY_TIMEOUT regardless of the overall assembly_timeout remaining. This prevents a single slow External Policy Evaluator from consuming the entire assembly budget.

### 2.3 Timeout Audit Records

Every timeout produces an audit record:

```yaml
audit_record:
  action: ASSEMBLY_TIMEOUT | DISPATCH_TIMEOUT | RESERVE_QUERY_TIMEOUT
  actor:
    type: system
    system_actor:
      component: request_payload_processor | provider_dispatch | placement_engine
      trigger: timeout
  entity_uuid: <uuid>
  details:
    timeout_duration: <configured duration>
    actual_elapsed: <ISO 8601 duration>
    step_at_timeout: <step name>
    recovery_policy_triggered: <policy uuid>
```

---

## 3. Cancellation Propagation Model

### 3.1 Three Cancellation Scenarios

Cancellation behavior depends on the entity's lifecycle state at the time the consumer submits a cancellation request.

**Scenario 1 — Cancel before dispatch (ACKNOWLEDGED → ASSEMBLING → AWAITING_APPROVAL):**

```
Consumer submits DELETE /api/v1/requests/{uuid}
  │
  ▼ Entity state: pre-DISPATCHED
  │   Assembly halted immediately
  │   No provider interaction required
  │   Intent State record marked CANCELLED
  │   Entity enters CANCELLED state (terminal)
  │   Audit: REQUEST_CANCELLED
  │   Recovery Policy: not triggered (clean cancel)
  │
  └── Response: 200 OK { "status": "CANCELLED" }
```

**Scenario 2 — Cancel after dispatch, provider not yet started (DISPATCHED):**

```
Consumer submits DELETE /api/v1/requests/{uuid}
  │
  ▼ Entity state: DISPATCHED (provider received payload but has not started)
  │   DCM sends cancellation payload to provider cancel endpoint
  │   Provider acknowledges: "not started, cancellation clean"
  │   Entity enters CANCELLED state (terminal)
  │   Recovery Policy: not triggered (clean cancel)
  │
  └── Response: 202 Accepted { "status": "CANCELLING" }
      → status polling shows CANCELLED when provider confirms
```

**Scenario 3 — Cancel while provider is executing (PROVISIONING):**

```
Consumer submits DELETE /api/v1/requests/{uuid}
  │
  ▼ Entity state: PROVISIONING
  │   DCM checks provider.supports_cancellation
  │
  ├── Provider supports cancellation:
  │   DCM sends cancellation payload
  │   Provider attempts rollback
  │   ├── Rollback clean: entity → CANCELLED (terminal)
  │   ├── Rollback partial: trigger CANCELLATION_FAILED recovery policy
  │   └── No response: trigger CANCELLATION_FAILED recovery policy
  │
  └── Provider does not support cancellation:
      Entity enters CANCEL_PENDING state
      DCM waits for provider to complete
      On provider REALIZED response:
        Recovery Policy LATE_RESPONSE_RECEIVED fires
        (configured action: typically DISCARD_AND_REQUEUE for cancellation context)
      On provider FAILED response:
        Entity → FAILED (terminal) — no compensation needed
```

### 3.2 Provider Cancellation Capability Declaration

Providers declare cancellation support in their registration:

```yaml
provider_cancellation_capabilities:
  supports_cancellation: true
  cancellation_supported_during: [DISPATCHED, PROVISIONING]
  # DISPATCHED: can cancel before work begins
  # PROVISIONING: can cancel and roll back mid-execution
  cancellation_endpoint: POST /api/v1/provider/entities/{entity_uuid}/cancel
  cancellation_response_time: PT30S    # SLA for cancellation response
  partial_rollback_possible: true
  # true: cancellation may leave partial resources → CANCELLATION_FAILED path
  # false: cancellation is all-or-nothing (rare)
```

### 3.3 Cancellation Payload

```json
{
  "cancellation_uuid": "<uuid>",
  "entity_uuid": "<uuid>",
  "requested_state_uuid": "<uuid>",
  "reason": "consumer_requested | timeout | policy_triggered",
  "requested_at": "<ISO 8601>",
  "best_effort": true
}
```

`best_effort: true` is always set — DCM never guarantees cancellation success. The provider makes a best-effort attempt; outcomes flow through the Recovery Policy model.

---

## 4. Discovery Scheduling Model

### 4.1 The Discovery Scheduler Component

The **Discovery Scheduler** is a DCM control plane component responsible for triggering discovery cycles. It maintains a priority queue of pending discovery requests and dispatches them to the appropriate Service Provider's discovery endpoint.

The Discovery Scheduler is distinct from drift detection. The Discovery Scheduler triggers discovery and writes Discovered State. Drift Detection reads Discovered State and compares it to Realized State. These are separate, independent components.

### 4.2 Three Discovery Trigger Types

**Trigger Type 1 — Scheduled (cron-based):**

Discovery schedules are declared in the Resource Type Specification and in provider registrations. The Discovery Scheduler runs these on the declared cadence.

```yaml
resource_type_spec:
  fqn: Compute.VirtualMachine
  discovery_schedule:
    default_interval: PT15M      # discover VMs every 15 minutes
    # Override by profile:
    profile_overrides:
      minimal: PT4H              # less frequent in home lab
      fsi: PT5M                  # more frequent in regulated environments
      sovereign: PT5M

  # Per-provider discovery endpoint
  discovery_endpoint_path: /api/v1/provider/discover
  discovery_method: api_query    # api_query | passive_event | hybrid
```

```yaml
provider_registration:
  discovery_capabilities:
    supports_discovery: true
    discovery_endpoint: POST /api/v1/provider/entities/discover
    max_entities_per_discovery_batch: 1000
    discovery_latency_p95: PT10S    # how long discovery typically takes
    supports_incremental_discovery: true
    # incremental: only entities changed since last_discovery_timestamp
    # full: all entities every time
```

**Trigger Type 2 — Event-triggered:**

Specific DCM events automatically schedule an out-of-cycle discovery pass:

```yaml
event_triggered_discovery:
  triggers:
    - event: entity.realized
      discovery_delay: PT30S           # allow provider to stabilize
      scope: this_entity
      reason: "Confirm realization matches Requested State"

    - event: drift.resolved
      discovery_delay: PT60S
      scope: this_entity
      reason: "Confirm remediation took effect"

    - event: provider_update.approved
      discovery_delay: PT30S
      scope: this_entity
      reason: "Confirm provider update is reflected in infrastructure"

    - event: provider.degraded
      discovery_delay: PT0S           # immediate
      scope: all_entities_on_provider
      reason: "Assess impact of provider degradation"

    - event: TIMEOUT_PENDING          # recovery trigger
      discovery_delay: PT5M
      scope: this_entity
      reason: "Orphan detection after timeout"

    - event: COMPENSATION_FAILED
      discovery_delay: PT0S           # immediate
      scope: this_entity_and_dependents
      reason: "Find orphaned resources after compensation failure"
```

**Trigger Type 3 — On-demand:**

Platform admins and SREs can trigger discovery manually:

```
POST /api/v1/admin/discovery:trigger

{
  "scope": "entity | resource_type | provider | tenant",
  "entity_uuid": "<uuid>",          # if scope: entity
  "resource_type": "<fqn>",         # if scope: resource_type
  "provider_uuid": "<uuid>",         # if scope: provider
  "tenant_uuid": "<uuid>",           # if scope: tenant
  "reason": "incident investigation",
  "priority": "high"
}
```

On-demand discovery is also used by:
- The CI/CD pipeline pre-validation step (confirm current state before assembly)
- The brownfield ingestion pipeline (initial discovery of existing infrastructure)
- The orphan detection pipeline (targeted search for potentially-orphaned resources)

### 4.3 Discovery Queue Management

The Discovery Scheduler manages a priority queue. Priority order:

1. **Critical** — COMPENSATION_FAILED orphan detection, sovereignty violation assessment
2. **High** — on-demand from platform admin, event-triggered (provider.degraded)
3. **Standard** — event-triggered (entity.realized, drift.resolved)
4. **Background** — scheduled discovery passes

Queue depth is bounded per profile. When the queue is full, new Background-priority items are dropped (with a log entry). Standard and above are never dropped — they wait.

### 4.4 Discovery Audit

Every discovery cycle produces an audit record:

```yaml
audit_record:
  action: DISCOVERY_CYCLE_COMPLETED | DISCOVERY_CYCLE_FAILED
  actor:
    type: system
    system_actor:
      component: discovery_scheduler
      trigger: scheduled | event_triggered | on_demand
      trigger_event_uuid: <uuid|null>
  entity_uuid: <uuid|null>          # null for batch discovery
  details:
    entities_discovered: 47
    new_entities_found: 2           # brownfield candidates
    duration: PT8S
```

---

## 5. Recovery Policy Model

### 5.1 Recovery Policy as a Policy Type

Recovery Policies are a formal DCM policy type alongside GateKeeper, Validation, and Transformation. They use the same authoring model, the same GitOps store, the same shadow mode validation, the same activation workflow, and the same audit trail.

```yaml
recovery_policy:
  artifact_metadata:
    uuid: <uuid>
    handle: "system/recovery/discard-on-timeout"
    version: "1.0.0"
    status: active
    owned_by: { display_name: "DCM Core Team" }

  policy_type: recovery
  trigger: DISPATCH_TIMEOUT         # the trigger condition this policy handles
  action: DISCARD_AND_REQUEUE       # the action to take

  # Optional additional conditions
  conditions:
    - field: entity.resource_type
      operator: in
      value: [Compute.VirtualMachine, Container.Pod]
    - field: entity.owned_by_tenant.profile
      operator: equals
      value: prod

  # Action parameters (depend on action type)
  action_parameters:
    requeue_delay: PT0S             # immediate requeue
    notify_before_action: true
    notification_urgency: high

  # Deadline for NOTIFY_AND_WAIT actions
  deadline: null                    # not applicable for DISCARD_AND_REQUEUE
  on_deadline_exceeded: null
```

### 5.2 Trigger Vocabulary (Closed)

| Trigger | Description |
|---------|-------------|
| `ASSEMBLY_TIMEOUT` | Assembly pipeline exceeded configured timeout |
| `DISPATCH_TIMEOUT` | Provider did not respond within dispatch_timeout |
| `RESERVE_QUERY_ALL_EXHAUSTED` | All placement candidates timed out or rejected |
| `LATE_RESPONSE_RECEIVED` | Provider responded after DCM declared timeout |
| `CANCELLATION_SENT` | DCM sent cancellation to provider |
| `CANCELLATION_CONFIRMED` | Provider confirmed clean cancellation |
| `CANCELLATION_FAILED` | Provider could not cancel; partial state possible |
| `PARTIAL_REALIZATION` | Compound service partially realized |
| `COMPENSATION_IN_PROGRESS` | Rollback of partial components underway |
| `COMPENSATION_FAILED` | Rollback itself failed; orphaned resources possible |

### 5.3 Action Vocabulary (Closed)

| Action | Description |
|--------|-------------|
| `DRIFT_RECONCILE` | Schedule discovery pass; let drift detection resolve actual state via configured drift response policy |
| `DISCARD_AND_REQUEUE` | Best-effort cleanup sent to provider; new request cycle created immediately from Intent State |
| `DISCARD_NO_REQUEUE` | Best-effort cleanup sent to provider; entity FAILED; no automatic requeue |
| `ACCEPT_LATE_REALIZATION` | Accept late provider response; write Realized State; entity proceeds to OPERATIONAL |
| `COMPENSATE_AND_FAIL` | Execute compensation rollback for composite service; entity FAILED when complete |
| `NOTIFY_AND_WAIT` | Fire notification to configured audience; wait for human decision up to deadline |
| `ESCALATE` | Notify platform admin immediately; no automatic action |
| `RETRY` | Retry the failed operation with configured backoff |

### 5.4 The Four Built-in Recovery Profile Groups

#### recovery-automated-reconciliation

"Let the system converge on correct state — trust drift detection and policy."

Appropriate for: standard and dev environments where operational continuity takes priority over strict consistency.

```yaml
recovery_policy_group:
  handle: "system/group/recovery-automated-reconciliation"
  concern_type: recovery_posture
  policies:
    - trigger: ASSEMBLY_TIMEOUT
      action: RETRY
      max_attempts: 3
      backoff: exponential
      initial_interval: PT30S
      on_exhaustion: ESCALATE

    - trigger: DISPATCH_TIMEOUT
      action: DRIFT_RECONCILE
      # Discovery finds what actually exists; drift response policy handles it

    - trigger: LATE_RESPONSE_RECEIVED
      action: ACCEPT_LATE_REALIZATION
      # Provider did the work; accept it

    - trigger: CANCELLATION_FAILED
      action: DRIFT_RECONCILE
      # Cannot confirm cleanup; discovery finds orphans

    - trigger: PARTIAL_REALIZATION
      action: DRIFT_RECONCILE
      # Discover what's there; drift policy handles component gaps

    - trigger: COMPENSATION_FAILED
      action: ESCALATE
      # Human needed when cleanup itself fails
```

#### recovery-discard-and-requeue

"On any ambiguity, clean up and start fresh — prioritize consistency over continuity."

Appropriate for: environments where reproducibility is paramount, resources are cheap to reprovision, untracked resources are a compliance concern.

```yaml
recovery_policy_group:
  handle: "system/group/recovery-discard-and-requeue"
  concern_type: recovery_posture
  policies:
    - trigger: ASSEMBLY_TIMEOUT
      action: RETRY
      max_attempts: 2
      on_exhaustion: DISCARD_NO_REQUEUE

    - trigger: DISPATCH_TIMEOUT
      action: DISCARD_AND_REQUEUE
      # Best-effort cleanup; new request cycle immediately

    - trigger: LATE_RESPONSE_RECEIVED
      action: DISCARD_AND_REQUEUE
      # Provider completed after DCM moved on; discard that work
      # (requeue already happened on timeout; this prevents duplicate resources)

    - trigger: CANCELLATION_FAILED
      action: DISCARD_NO_REQUEUE
      # Cannot clean up; FAILED; human reviews orphans before requeue

    - trigger: PARTIAL_REALIZATION
      action: COMPENSATE_AND_FAIL
      # Roll back everything; start fresh

    - trigger: COMPENSATION_FAILED
      action: ESCALATE
      # Cannot even roll back; human needed
```

#### recovery-notify-and-wait

"Never act automatically — always notify a human and wait for explicit authorization."

Appropriate for: FSI and sovereign environments where automated resource creation or deletion has regulatory implications, where change control processes must be honored.

```yaml
recovery_policy_group:
  handle: "system/group/recovery-notify-and-wait"
  concern_type: recovery_posture
  policies:
    - trigger: ASSEMBLY_TIMEOUT
      action: NOTIFY_AND_WAIT
      deadline: PT2H
      notification_urgency: high
      on_deadline_exceeded: ESCALATE

    - trigger: DISPATCH_TIMEOUT
      action: NOTIFY_AND_WAIT
      deadline: PT4H
      notification_urgency: high
      on_deadline_exceeded: ESCALATE

    - trigger: LATE_RESPONSE_RECEIVED
      action: NOTIFY_AND_WAIT
      deadline: PT4H
      notification_urgency: medium
      on_deadline_exceeded: DISCARD_NO_REQUEUE

    - trigger: CANCELLATION_FAILED
      action: NOTIFY_AND_WAIT
      deadline: PT8H
      notification_urgency: high
      on_deadline_exceeded: ESCALATE

    - trigger: PARTIAL_REALIZATION
      action: NOTIFY_AND_WAIT
      deadline: PT8H
      notification_urgency: high
      on_deadline_exceeded: COMPENSATE_AND_FAIL

    - trigger: COMPENSATION_FAILED
      action: ESCALATE
      # Always escalate compensation failures — no deadline
```

#### recovery-aggressive-retry

"Retry everything before giving up — maximize first-time success rate."

Appropriate for: environments with transient provider issues, where retries are cheap and manual intervention capacity is limited.

```yaml
recovery_policy_group:
  handle: "system/group/recovery-aggressive-retry"
  concern_type: recovery_posture
  policies:
    - trigger: ASSEMBLY_TIMEOUT
      action: RETRY
      max_attempts: 5
      backoff: exponential
      initial_interval: PT15S
      max_interval: PT5M
      on_exhaustion: NOTIFY_AND_WAIT
      deadline: PT2H

    - trigger: DISPATCH_TIMEOUT
      action: RETRY
      max_attempts: 3
      backoff: linear
      interval: PT5M
      on_exhaustion: DRIFT_RECONCILE

    - trigger: RESERVE_QUERY_ALL_EXHAUSTED
      action: RETRY
      max_attempts: 3
      backoff: exponential
      initial_interval: PT1M
      on_exhaustion: ESCALATE

    - trigger: PARTIAL_REALIZATION
      action: RETRY
      retry_scope: failed_components_only   # preserve succeeded components
      max_attempts: 3
      interval: PT15M
      on_exhaustion: COMPENSATE_AND_FAIL

    - trigger: CANCELLATION_FAILED
      action: DRIFT_RECONCILE

    - trigger: COMPENSATION_FAILED
      action: ESCALATE
```

### 5.5 Profile Binding

Recovery profile groups bind to deployment profiles as defaults, with override at Tenant and resource-type levels:

```yaml
profile_recovery_defaults:
  minimal:    recovery-automated-reconciliation
  dev:        recovery-automated-reconciliation
  standard:   recovery-automated-reconciliation
  prod:       recovery-notify-and-wait
  fsi:        recovery-notify-and-wait
  sovereign:  recovery-notify-and-wait

# Tenant-level override
tenant_config:
  tenant_uuid: <uuid>
  recovery_profile_override: recovery-discard-and-requeue

# Resource-type-level override (most specific; wins over Tenant and profile)
resource_type_recovery_override:
  resource_type: Compute.VirtualMachine
  recovery_profile: recovery-aggressive-retry
  # VMs use aggressive retry; other types use Tenant/profile default
```

### 5.6 NOTIFY_AND_WAIT Consumer Interface

When a recovery policy fires `NOTIFY_AND_WAIT`, a notification is sent to the entity owner with a time-bounded decision interface:

```
GET /api/v1/resources/{entity_uuid}/recovery-decisions

Response:
{
  "recovery_decision_uuid": "<uuid>",
  "trigger": "DISPATCH_TIMEOUT",
  "entity_uuid": "<uuid>",
  "deadline": "<ISO 8601>",
  "available_actions": [
    {
      "action": "DRIFT_RECONCILE",
      "description": "Let discovery determine actual state and reconcile automatically"
    },
    {
      "action": "DISCARD_AND_REQUEUE",
      "description": "Best-effort cleanup, then requeue as a new request"
    },
    {
      "action": "DISCARD_NO_REQUEUE",
      "description": "Best-effort cleanup only; no automatic requeue"
    }
  ]
}

POST /api/v1/resources/{entity_uuid}/recovery-decisions/{recovery_decision_uuid}
{
  "action": "DISCARD_AND_REQUEUE",
  "reason": "Provider was known to be degraded at time of timeout"
}
```

Platform admins may also use the Admin API to resolve pending recovery decisions for any entity regardless of Tenant.

### 5.7 Recovery Policy Evaluation Precedence

The Policy Engine evaluates recovery policies in domain precedence order, same as all other policies:

```
1. Resource-type-level override (most specific)
2. Tenant-level override
3. Active profile's recovery posture group
4. System default (automated-reconciliation)

First matching policy for the trigger condition wins.
Multiple recovery policies for the same trigger at the same domain level
→ policy conflict; CONFLICT_ERROR at ingestion; platform admin notified.
```

---

## 6. Composite Service Compensation Model

### 6.1 Compensation Declaration in Service Dependencies

Each component in a composite service declares its compensation behavior:

```yaml
composite_service_spec:
  service_type: ApplicationStack.WebApp
  components:
    - id: vm
      resource_type: Compute.VirtualMachine
      required_for_delivery: atomic        # must succeed; failure triggers compensation
      compensation_on_failure: decommission_immediately
      compensation_order: 3                # decommissioned last (highest number = last)

    - id: ip
      resource_type: Network.IPAddress
      required_for_delivery: atomic
      compensation_on_failure: release_allocation
      compensation_order: 1                # decommissioned first
      depends_on: []

    - id: dns
      resource_type: DNS.Record
      required_for_delivery: partial       # failure → DEGRADED, not FAILED
      compensation_on_failure: skip        # DNS failure doesn't trigger VM decommission
      depends_on: [vm, ip]

    - id: loadbalancer
      resource_type: Network.LoadBalancer
      required_for_delivery: partial
      compensation_on_failure: skip
      depends_on: [vm, ip]

  partial_delivery_policy:
    min_required_components: [vm, ip]     # composite DEGRADED if only these succeed
    degraded_is_acceptable: true          # DEGRADED entity is delivered; not FAILED
    auto_retry_optional_components:
      enabled: true
      max_attempts: 3
      interval: PT15M
      on_exhaustion: notify_owner
```

### 6.2 Compensation Execution Order

Compensation always runs in reverse dependency order — last-provisioned is first-decommissioned:

```
Successful so far: vm ✓, ip ✓
Failed: dns ✗ (atomic)
Compensation triggered:
  Step 1: decommission vm (compensation_order: 3 → runs first in reverse)
  Step 2: release ip allocation (compensation_order: 1 → runs second in reverse)
  Compound entity → FAILED (terminal for this request cycle)
```

### 6.3 Compensation Failure

If a compensation step fails (the VM decommission itself fails):

```
Compensation of vm FAILED
  Entity enters COMPENSATION_FAILED state
  COMPENSATION_FAILED recovery policy fires:
    default: ESCALATE to platform admin
  Orphan detection triggered immediately:
    Scoped to provider + entity characteristics
    Finds the VM that couldn't be decommissioned
    Creates ORPHAN_CANDIDATE record
  Platform admin reviews:
    Manually decommission at provider
    OR adopt into DCM lifecycle as a new entity
```

---

## 7. Orphan Detection Pipeline

When cleanup cannot be guaranteed, DCM runs an orphan detection pass to find resources that may have been provisioned but have no corresponding Realized State record.

### 7.1 Orphan Detection Triggers

- Dispatch timeout with cancellation sent
- Cancellation failed
- Compensation failed
- DISCARD_NO_REQUEUE action taken
- Manual platform admin trigger

### 7.2 Orphan Detection Query

```yaml
orphan_detection_query:
  provider_uuid: <uuid>
  time_window:
    from: <request_dispatched_at - PT5M>
    to: <now>
  match_criteria:
    resource_type: <from Requested State>
    characteristics:             # key fields from the Requested State
      name_pattern: <if name was declared>
      size_class: <cpu/memory range>
      tags: <tags from request>
  exclude:
    known_realized_state_uuids: [<uuid>, ...]   # entities DCM knows about
```

### 7.3 Orphan Candidate Lifecycle

```yaml
orphan_candidate:
  orphan_candidate_uuid: <uuid>
  suspected_request_uuid: <uuid>     # the request that may have created this
  provider_entity_id: <string>       # what the provider calls it
  provider_uuid: <uuid>
  discovered_at: <ISO 8601>
  characteristics: { ... }
  status: <under_review | confirmed_orphan | adopted | false_positive>
  resolution:
    action: <manual_decommission | adopt_into_dcm | mark_false_positive>
    resolved_by: <actor_uuid>
    resolved_at: <ISO 8601>
```

Orphan candidates are surfaced in the Platform Admin dashboard and generate a NOTIFICATION (audience: Platform Admin) with urgency: high.

---

## 8. New Lifecycle States

Five new states are added to the Infrastructure Resource Entity lifecycle:

| State | Meaning | Recovery Policy Trigger |
|-------|---------|------------------------|
| `TIMEOUT_PENDING` | Dispatch timeout fired; cancellation sent; awaiting outcome | `DISPATCH_TIMEOUT` |
| `LATE_REALIZATION_PENDING` | Provider responded after timeout; NOTIFY_AND_WAIT active | `LATE_RESPONSE_RECEIVED` |
| `INDETERMINATE_REALIZATION` | State is ambiguous; drift detection resolving | — (drift detection runs) |
| `COMPENSATION_IN_PROGRESS` | Compound service rollback underway | — |
| `COMPENSATION_FAILED` | Rollback itself failed; orphaned resources possible | `COMPENSATION_FAILED` |

Updated state machine (additions to doc 02 and doc 06):

```
Normal flow:
REQUESTED → PENDING → PROVISIONING → REALIZED → OPERATIONAL → DECOMMISSIONED

Recovery states:
PROVISIONING → [timeout] → TIMEOUT_PENDING
  TIMEOUT_PENDING → [late response + NOTIFY_AND_WAIT] → LATE_REALIZATION_PENDING
  TIMEOUT_PENDING → [DRIFT_RECONCILE] → INDETERMINATE_REALIZATION
  TIMEOUT_PENDING → [DISCARD_AND_REQUEUE] → FAILED + new REQUESTED (new cycle)

PROVISIONING → [partial failure] → COMPENSATION_IN_PROGRESS
  COMPENSATION_IN_PROGRESS → [all compensated] → FAILED
  COMPENSATION_IN_PROGRESS → [compensation fails] → COMPENSATION_FAILED

LATE_REALIZATION_PENDING → [human accepts / ACCEPT_LATE] → REALIZED → OPERATIONAL
LATE_REALIZATION_PENDING → [human discards / DISCARD] → FAILED

INDETERMINATE_REALIZATION → [drift reconciles] → REALIZED or FAILED
COMPENSATION_FAILED → [human resolves] → FAILED (after manual cleanup)
```

---

## 9. System Policies

| Policy | Rule |
|--------|------|
| `OPS-010` | Assembly timeout, dispatch timeout, and reserve-query timeout are independently configurable. All are profile-governed with resource-type overrides permitted for types with legitimately long provisioning times. |
| `OPS-011` | Cancellation is always best-effort. DCM never guarantees cancellation success. All cancellation outcomes flow through the Recovery Policy model. |
| `OPS-012` | Provider cancellation capability is declared at registration. Providers that do not support cancellation use the CANCEL_PENDING → LATE_RESPONSE_RECEIVED path when a cancel is requested during PROVISIONING. |
| `OPS-013` | Discovery is triggered by three independent mechanisms: scheduled (cron), event-triggered, and on-demand. All three write to the Discovered Store independently. |
| `OPS-014` | Recovery Policies are a formal DCM policy type. They use the same authoring, activation, shadow mode, and audit model as GateKeeper, Validation, and Transformation policies. |
| `OPS-015` | Four built-in recovery profile groups are provided: recovery-automated-reconciliation, recovery-discard-and-requeue, recovery-notify-and-wait, recovery-aggressive-retry. |
| `OPS-016` | Recovery profile defaults are bound to deployment profiles. Organizations may override at Tenant or resource-type level. Resource-type override wins over Tenant override wins over profile default. |
| `OPS-017` | Compound service compensation runs in reverse dependency order. Compensation failure triggers COMPENSATION_FAILED state and immediate orphan detection. |
| `OPS-018` | Orphan detection triggers on any path where cleanup cannot be guaranteed. Orphan candidates are surfaced to platform admin with urgency: high. |
| `OPS-019` | NOTIFY_AND_WAIT recovery actions carry a deadline. If the deadline passes without human resolution, the configured on_deadline_exceeded action fires automatically. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
