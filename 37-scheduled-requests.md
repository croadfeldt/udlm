# DCM Data Model — Scheduled and Deferred Requests

**Document Status:** ✅ Complete
**Document Type:** Architecture Reference — Request Scheduling
**Related Documents:** [Resource and Service Entities](06-resource-service-entities.md) | [Operational Models](24-operational-models.md) | [Request Dependency Graph](38-request-dependency-graph.md) | [Event Catalog](33-event-catalog.md) | [Consumer API Specification](../specifications/consumer-api-spec.md)

> **This document maps to: DATA + PROVIDER**
>
> A scheduled request is still a request — it goes through the same Intent → Requested → Realized pipeline. The only difference is when the pipeline's dispatch step fires. Scheduling is a field on the request, not a separate object type. The Request Orchestrator handles dispatch timing; the Policy Engine evaluates at declaration time (gatekeeping) and again at dispatch time (policy correctness at the moment of execution).

---

## 1. The Scheduling Model

### 1.1 Core Concept

Every DCM request has an implicit `schedule: immediate`. Scheduled requests make this explicit:

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
| Discovery trigger | ❌ | Handled by Discovery Scheduling Model (doc 24 §4) |

---

## 2. Request State During Deferral

A scheduled request moves through the four states with one additional intermediate status:

```
Submit request with schedule.dispatch: at
  │
  ▼ ACKNOWLEDGED (Intent State created)
  │   entity_uuid assigned
  │   schedule stored in Intent State
  │
  ▼ Policy evaluation at declaration time
  │   GateKeeper policies run immediately
  │   If rejected: request fails before entering queue
  │   If approved: request enters scheduled queue
  │
  ▼ SCHEDULED (new status within Intent State)
  │   stored in Request Scheduler queue
  │   visible via GET /api/v1/requests/{uuid}/status
  │   cancellable: DELETE /api/v1/requests/{uuid}
  │
  ▼ [at not_before time] → Policy re-evaluation at dispatch
  │   Transformation policies re-run (data may have changed)
  │   GateKeeper re-evaluation with current data
  │   If still approved: proceed to LAYERS_ASSEMBLED → dispatch
  │   If rejected at dispatch time: FAILED with reason schedule_policy_rejection
  │
  ▼ DISPATCHED → REALIZED (normal pipeline)
```

### 2.1 Why Policy Runs Twice

Policies are evaluated at declaration time to catch obvious rejections early (fail fast). They run again at dispatch time because data may have changed — quota may be exhausted, a compliance policy may have been activated, the actor's role may have changed. The dispatch-time evaluation uses the current policy set, not the one in effect at declaration.

**SCH-003:** Scheduled requests that fail dispatch-time policy re-evaluation enter FAILED state with `failure_reason: schedule_policy_rejection`. The consumer receives a `request.failed` event with the policy rejection detail.

---

## 3. Maintenance Windows

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

### 3.1 Maintenance Window API

```
# Platform admin operations
POST   /api/v1/admin/maintenance-windows
GET    /api/v1/admin/maintenance-windows
GET    /api/v1/admin/maintenance-windows/{window_uuid}
PATCH  /api/v1/admin/maintenance-windows/{window_uuid}
DELETE /api/v1/admin/maintenance-windows/{window_uuid}

# Consumer operations
GET    /api/v1/maintenance-windows          # list windows visible to consumer
GET    /api/v1/maintenance-windows/{uuid}  # describe a specific window
```

---

## 4. The Request Scheduler Component

The Request Scheduler is a DCM control plane component responsible for managing the scheduled request queue and triggering dispatch at the appropriate time.

```
Request Scheduler responsibilities:
  - Maintain a priority queue of SCHEDULED requests ordered by not_before
  - Poll queue; dispatch requests when not_before is reached
  - Check not_after deadlines; cancel expired requests with reason: schedule_deadline_missed
  - Listen for maintenance_window events to trigger window-scheduled requests
  - On dispatch: hand off to Request Orchestrator (same path as immediate requests)
  - Write SCHEDULED status updates to Intent State
  - Publish request.scheduled and request.schedule_cancelled events
```

### 4.1 Deadline Enforcement

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

---

## 5. Consumer API Additions

### 5.1 Submit Scheduled Request

Scheduling is an optional `schedule` field on the existing request submission body:

```
POST /api/v1/requests

{
  "catalog_item_uuid": "<uuid>",
  "fields": { ... },
  "schedule": {
    "dispatch": "at",
    "not_before": "2026-04-01T02:00:00Z",
    "not_after": "2026-04-01T06:00:00Z"
  }
}

Response 202:
{
  "request_uuid": "<uuid>",
  "entity_uuid": "<uuid>",
  "status": "SCHEDULED",
  "scheduled_dispatch_at": "2026-04-01T02:00:00Z",
  "schedule_deadline": "2026-04-01T06:00:00Z"
}
```

### 5.2 List Scheduled Requests

```
GET /api/v1/requests?status=SCHEDULED

Response 200:
{
  "items": [
    {
      "request_uuid": "<uuid>",
      "entity_uuid": "<uuid>",
      "status": "SCHEDULED",
      "catalog_item_handle": "compute.vm.standard",
      "scheduled_dispatch_at": "2026-04-01T02:00:00Z",
      "schedule_deadline": "2026-04-01T06:00:00Z",
      "created_at": "<ISO 8601>"
    }
  ],
  "total": 3
}
```

### 5.3 Cancel Scheduled Request

Cancellation uses the existing endpoint — no new endpoint needed:

```
DELETE /api/v1/requests/{request_uuid}

# Works on SCHEDULED requests; moves status to CANCELLED
# Returns 409 if request is already dispatched (past SCHEDULED)

Response 204 No Content
```

---

## 6. New Events

Two new event types for the Event Catalog (doc 33):

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `request.scheduled` | info | Request entered SCHEDULED queue |
| `request.schedule_cancelled` | low | Scheduled request cancelled before dispatch |
| `request.schedule_deadline_missed` | medium | not_after passed without dispatch |

These add to the `request.*` domain. Updated domain total: 17 request events.

---

## 8. Profile-Governed Scheduling Configuration

Scheduling constraints are profile-governed to reflect the operational risk tolerance of each deployment context:

| Profile | Max scheduling horizon | Max concurrent scheduled/actor | Recurring max frequency | Maintenance window approval tier |
|---------|----------------------|-------------------------------|------------------------|----------------------------------|
| `minimal` | P365D | unlimited | PT1H | auto |
| `dev` | P365D | 50 | PT1H | auto |
| `standard` | P90D | 20 | PT4H | reviewed |
| `prod` | P30D | 10 | PT12H | reviewed |
| `fsi` | P14D | 5 | PT24H | verified |
| `sovereign` | P7D | 3 | PT24H | authorized |

**Max scheduling horizon:** How far in the future a `not_before` may be set. Requests with `not_before` beyond the profile limit are rejected (422) at submission.

**Max concurrent scheduled/actor:** How many SCHEDULED (not yet dispatched) requests a single actor may have at one time. Exceeding this limit returns 429.

**Recurring max frequency:** The minimum interval between recurring dispatches. A cron expression that would dispatch more frequently than this is rejected.

**Maintenance window approval tier:** The authority tier required to create or modify a Maintenance Window (see ATM-001, doc 32).

## 7. System Policies

| Policy | Rule |
|--------|------|
| `SCH-001` | Scheduled requests undergo GateKeeper policy evaluation at declaration time (to catch rejections early) and again at dispatch time (to validate against current state). Both evaluations must pass. |
| `SCH-002` | The `not_before` field must be a future timestamp at submission time. DCM rejects scheduled requests with a past `not_before` (returns 422). |
| `SCH-003` | Requests that fail dispatch-time policy re-evaluation enter FAILED state with `failure_reason: schedule_policy_rejection`. Consumers receive a `request.failed` event with the rejection detail. |
| `SCH-004` | Scheduled requests are cancellable (DELETE /api/v1/requests/{uuid}) at any time before dispatch. Once the Request Orchestrator has accepted the handoff (status moves beyond SCHEDULED), cancellation follows the standard cancellation model. |
| `SCH-005` | If `not_after` is set and passes without dispatch, the request enters FAILED state with `failure_reason: schedule_deadline_missed`. No retry is attempted. |
| `SCH-006` | Maintenance Windows are platform-level or tenant-scoped artifacts requiring platform admin approval. Window schedules are versioned artifacts subject to standard DCM lifecycle. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
