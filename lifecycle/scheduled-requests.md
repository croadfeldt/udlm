# UDLM — Scheduled and Deferred Requests

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Reference — Request Scheduling
**Related Documents:** [Resource and Service Entities](../entities/resource-service-entities.md) | [Operational Models](operational-models.md) | [Request Dependency Graph](request-dependency-graph.md) | [Event Catalog](../contracts/event-catalog.md)

> **This document maps to: DATA + PROVIDER**
>
> A scheduled request is still a request — it goes through the same Intent → Requested → Realized pipeline. The only difference is when the pipeline's dispatch step fires. Scheduling is a field on the request, not a separate object type. The substrate requires that policy be evaluated at declaration time (gating) and again at dispatch time (policy correctness at the moment of execution).

---

## 1. The Scheduling Model

### 1.1 Core Concept (Substrate Contract)

Every request has an implicit `schedule: immediate`. Scheduled requests make this explicit. The closed substrate vocabulary for `dispatch` is `immediate`, `at`, `window`, `recurring`.

```yaml
# Standard immediate request (implicit)
schedule:
  dispatch: immediate

# Deferred — dispatch at a specific time
schedule:
  dispatch: at
  not_before: "2026-04-01T02:00:00Z"   # UTC; dispatch begins at or after this time
  not_after: "2026-04-01T04:00:00Z"    # optional deadline; cancel if missed

# Maintenance window — dispatch during the next matching window
schedule:
  dispatch: window
  window_id: <maintenance_window_uuid>  # references a declared Maintenance Window
  not_after: "2026-04-30T00:00:00Z"    # optional: cancel if no window occurs before this

# Recurring — for decommission, TTL extension, or rehydration operations
schedule:
  dispatch: recurring
  cron: "0 2 * * 0"                    # cron expression (UTC)
  max_occurrences: 4                   # optional limit
  not_after: "2026-12-31T00:00:00Z"   # optional end date
```

### 1.2 What Can Be Scheduled

Scheduling applies to any request operation that results in a dispatch to a provider. This includes:

| Operation | Scheduling supported | Notes |
|-----------|---------------------|-------|
| Resource creation | ✅ | Full scheduling model |
| Resource update (PATCH) | ✅ | Full scheduling model |
| Suspend | ✅ | Full scheduling model |
| Resume | ✅ | Full scheduling model |
| Decommission | ✅ | Full scheduling model; `not_after` recommended |
| Rehydration | ✅ | Full scheduling model |
| TTL extension | ✅ | Full scheduling model |
| Discovery trigger | ❌ | Handled by Discovery Scheduling Model ([operational-models.md §4](operational-models.md)) |

---

## 2. Request State During Deferral (SCHEDULED state contract)

A scheduled request moves through the four states with one additional intermediate status. The `SCHEDULED` status is part of the closed substrate state vocabulary.

```
Submit request with schedule.dispatch: at
  │
  ▼ ACKNOWLEDGED (Intent State created)
  │   entity_uuid assigned
  │   schedule stored in Intent State
  │
  ▼ Policy evaluation at declaration time
  │   Compliance-class Validation policies run immediately
  │   If rejected: request fails before entering queue
  │   If approved: request enters scheduled queue
  │
  ▼ SCHEDULED (new status within Intent State)
  │   stored in the realization's scheduled-request queue
  │   visible via status endpoint
  │   cancellable via standard cancellation endpoint
  │
  ▼ [at not_before time] → Policy re-evaluation at dispatch
  │   Transformation policies re-run (data may have changed)
  │   Compliance-class Validation Policy re-evaluation with current data
  │   If still approved: proceed to LAYERS_ASSEMBLED → dispatch
  │   If rejected at dispatch time: FAILED with reason schedule_policy_rejection
  │
  ▼ DISPATCHED → REALIZED (normal pipeline)
```

### 2.1 Why Policy Runs Twice (Substrate Contract)

Policies are evaluated at declaration time to catch obvious rejections early (fail fast). They MUST run again at dispatch time because data may have changed — quota may be exhausted, a compliance policy may have been activated, the actor's role may have changed. The dispatch-time evaluation uses the current policy set, not the one in effect at declaration.

**SCH-003:** Scheduled requests that fail dispatch-time policy re-evaluation enter FAILED state with `failure_reason: schedule_policy_rejection`. The consumer receives a `request.failed` event with the policy rejection detail.

---

## 3. Maintenance Windows (Coordination Contract)

A Maintenance Window is a reusable schedule artifact — a named recurrence that scheduled requests can reference. This allows operations teams to declare approved change windows once and have requests automatically slot into them.

```yaml
maintenance_window:
  window_uuid: <uuid>
  window_handle: "weekly-sunday-0200-utc"
  description: "Weekly maintenance window — low traffic period"

  # Recurrence
  cron: "0 2 * * 0"          # every Sunday at 02:00 UTC
  duration: PT2H              # window is 2 hours long

  # Scope
  tenant_uuid: <uuid | null>  # null = platform-wide window
  resource_types: [<fqn>]     # empty = all resource types

  # Approval
  status: active | suspended
  approved_by: <actor_uuid>
  effective_from: <ISO 8601>

  # Metadata
  created_at: <ISO 8601>
  created_by: <actor_uuid>
```

---

## 4. Deadline Enforcement (Substrate Contract)

If a request has `not_after` set and the deadline passes before dispatch:

```
not_after reached without dispatch
  │
  ▼ Request status → FAILED
  │   failure_reason: schedule_deadline_missed
  │
  ▼ request.failed event published (urgency: medium)
  │   consumer notified
  │
  ▼ Intent State marked terminal — no further retries
```

The realization MUST emit a `request.schedule_deadline_missed` event when a `not_after` deadline expires before dispatch. The `failure_reason: schedule_deadline_missed` value is part of the closed substrate vocabulary.

---

## 5. UDLM System Policies

| Policy | Rule |
|--------|------|
| `SCH-001` | Scheduled requests undergo compliance-class Validation policy evaluation at declaration time (to catch rejections early) and again at dispatch time (to validate against current state). Both evaluations must pass. |
| `SCH-002` | The `not_before` field must be a future timestamp at submission time. The realization rejects scheduled requests with a past `not_before` (returns 422). |
| `SCH-003` | Requests that fail dispatch-time policy re-evaluation enter FAILED state with `failure_reason: schedule_policy_rejection`. Consumers receive a `request.failed` event with the rejection detail. |
| `SCH-004` | Scheduled requests are cancellable at any time before dispatch. Once the realization has accepted the dispatch handoff (status moves beyond SCHEDULED), cancellation follows the standard cancellation model. |
| `SCH-005` | If `not_after` is set and passes without dispatch, the request enters FAILED state with `failure_reason: schedule_deadline_missed`. No retry is attempted. |
| `SCH-006` | Maintenance Windows are platform-level or tenant-scoped artifacts requiring platform admin approval. Window schedules are versioned artifacts subject to the standard substrate lifecycle. |

---

*UDLM substrate document. Realization-specific request scheduler component design, deferred request lifecycle management mechanics, maintenance window scheduling logic, deadline evaluation/enforcement code, consumer API endpoint additions, new event implementations, and profile-governed scheduling constraint enforcement live in the consuming realization's documentation.*
