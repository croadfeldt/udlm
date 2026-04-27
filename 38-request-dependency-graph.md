# DCM Data Model — Consumer Request Dependency Graph

**Document Status:** ✅ Complete
**Document Type:** Architecture Reference — Cross-Request Ordering
**Related Documents:** [Service Dependencies](07-service-dependencies.md) | [Scheduled Requests](37-scheduled-requests.md) | [composite service definition Composability](30-meta-provider-model.md) | [Operational Models](24-operational-models.md) | [Consumer API Specification](../specifications/consumer-api-spec.md)

> **Events:** Dependency resolution events (`request.dependencies_resolved`, `dependency.state_changed`) are defined in the [Event Catalog](33-event-catalog.md).

> **This document maps to: DATA + PROVIDER**
>
> **Distinction from existing dependency models:**
> - Doc 07 (Service Dependencies): *type-level* dependencies — DCM knows that a VM *type* requires an IP type. Resolved automatically during layer assembly.
> - Doc 30 (composite service definition): *composite service* dependencies — a composite service definition declares its own constituents and DCM sequences them. Consumer does not manage this.
> - **This document**: *consumer-declared cross-request ordering* — a consumer submitting multiple independent requests says "Request B may not dispatch until Request A is realized." These are requests for different resource types that have no type-level dependency; the consumer is expressing an ordering constraint for their specific deployment.

---

## 1. The Problem

A consumer deploying a three-tier application submits three requests: a database VM, an application VM, and a load balancer. Without ordering, all three dispatch simultaneously. But the application VM's startup configuration needs the database's IP address, which only exists after the database is realized.

This is not a type-level dependency (the VM type does not require a VM type). It is a *deployment-time ordering constraint* declared by the consumer for this specific deployment.

composite service definition composition handles this when a platform team has pre-defined the composite service. But consumers also need to express ad-hoc ordering for their own deployments without requiring a composite service definition to exist.

---

## 2. The Request Dependency Graph

A Request Dependency Group is a consumer-declared set of requests with ordering constraints between them.

```yaml
request_dependency_group:
  group_uuid: <uuid>
  group_handle: "three-tier-app-deploy"   # optional, consumer-defined
  
  requests:
    - request_uuid: <uuid>               # database VM
      depends_on: []                     # no dependencies — dispatches immediately
      
    - request_uuid: <uuid>               # application VM
      depends_on:
        - request_uuid: <db_request_uuid>
          wait_for: realized             # dispatch only after db is REALIZED
          inject_fields:                 # optional: inject realized fields into this request
            - from_field: "realized_fields.primary_ip"
              to_field: "fields.db_host"
              
    - request_uuid: <uuid>               # load balancer
      depends_on:
        - request_uuid: <app_request_uuid>
          wait_for: realized
          inject_fields:
            - from_field: "realized_fields.primary_ip"
              to_field: "fields.backend_hosts[0]"
  
  # Group-level options
  on_failure: cancel_remaining | continue   # what to do if a request fails
  timeout: PT2H                             # group-level deadline
```

### 2.1 wait_for Values

| Value | Meaning |
|-------|---------|
| `acknowledged` | Dispatch as soon as dependency has an entity_uuid |
| `approved` | Dispatch when dependency has passed approval |
| `dispatched` | Dispatch when dependency has been sent to its provider |
| `realized` | Dispatch only when dependency is fully realized (default, most common) |

### 2.2 Field Injection

The `inject_fields` mechanism passes realized output fields from a dependency directly into a dependent request's fields — without the consumer having to poll and re-submit. The injection happens at dispatch time, after the dependency is realized.

```
Dependency realized → Realized State written
  │
  ▼ DCM reads inject_fields declarations for dependent requests
  │   For each injection: extract from_field from Realized State
  │   Inject into dependent request's field at to_field path
  │
  ▼ Dependent request proceeds to layer assembly with injected fields
```

Field injection is subject to the same transformation policies as any other field — if a policy transforms `db_host`, the injection result passes through it.

---

## 3. Submitting a Dependency Group

### 3.1 Declare and Submit in One Call

```
POST /api/v1/request-groups

{
  "group_handle": "three-tier-app-deploy",
  "on_failure": "cancel_remaining",
  "timeout": "PT2H",
  "requests": [
    {
      "ref": "db",                          # local reference within this submission
      "catalog_item_uuid": "<uuid>",
      "fields": { "cpu_count": 8, "memory_gb": 32, "role": "database" }
    },
    {
      "ref": "app",
      "catalog_item_uuid": "<uuid>",
      "fields": { "cpu_count": 4, "memory_gb": 16, "role": "application" },
      "depends_on": [
        {
          "ref": "db",
          "wait_for": "realized",
          "inject_fields": [
            { "from_field": "realized_fields.primary_ip", "to_field": "fields.db_host" }
          ]
        }
      ]
    },
    {
      "ref": "lb",
      "catalog_item_uuid": "<uuid>",
      "fields": { "backend_port": 8080 },
      "depends_on": [
        { "ref": "app", "wait_for": "realized",
          "inject_fields": [
            { "from_field": "realized_fields.primary_ip", "to_field": "fields.backend_hosts[0]" }
          ]
        }
      ]
    }
  ]
}

Response 202:
{
  "group_uuid": "<uuid>",
  "group_handle": "three-tier-app-deploy",
  "requests": [
    { "ref": "db",  "request_uuid": "<uuid>", "entity_uuid": "<uuid>", "status": "ACKNOWLEDGED" },
    { "ref": "app", "request_uuid": "<uuid>", "entity_uuid": "<uuid>", "status": "PENDING_DEPENDENCY" },
    { "ref": "lb",  "request_uuid": "<uuid>", "entity_uuid": "<uuid>", "status": "PENDING_DEPENDENCY" }
  ],
  "estimated_completion": "<ISO 8601>"
}
```

### 3.2 Add an Existing Request to a Group

```
POST /api/v1/request-groups/{group_uuid}/members

{
  "request_uuid": "<uuid>",
  "depends_on": [ ... ]
}
```

### 3.3 Query Group Status

```
GET /api/v1/request-groups/{group_uuid}

Response 200:
{
  "group_uuid": "<uuid>",
  "group_handle": "three-tier-app-deploy",
  "status": "in_progress | completed | failed | cancelled",
  "requests": [
    { "request_uuid": "<uuid>", "ref": "db",  "status": "REALIZED" },
    { "request_uuid": "<uuid>", "ref": "app", "status": "DISPATCHED" },
    { "request_uuid": "<uuid>", "ref": "lb",  "status": "PENDING_DEPENDENCY" }
  ],
  "created_at": "<ISO 8601>",
  "timeout_at": "<ISO 8601>"
}
```

### 3.4 Cancel a Group

```
DELETE /api/v1/request-groups/{group_uuid}

# Cancels all PENDING_DEPENDENCY and ACKNOWLEDGED requests in the group
# Already-dispatched requests follow standard cancellation model
Response 204
```

---

## 4. PENDING_DEPENDENCY Status

A request in a dependency group that is waiting for its dependency to reach `wait_for` state has status `PENDING_DEPENDENCY`. This is a new status in the Intent State lifecycle:

```
ACKNOWLEDGED → PENDING_DEPENDENCY → [dependency met] → LAYERS_ASSEMBLED → ... → REALIZED
```

`PENDING_DEPENDENCY` requests:
- Are visible in `GET /api/v1/requests` with `status=PENDING_DEPENDENCY`
- Can be cancelled: `DELETE /api/v1/requests/{uuid}`
- Receive the `request.pending_dependency` event (new, info urgency)
- Do not time out independently — the group-level `timeout` governs

---

## 5. Failure Handling

### 5.1 `on_failure: cancel_remaining`

When a request in the group fails and `on_failure: cancel_remaining` is set:

```
Request fails
  │
  ▼ All PENDING_DEPENDENCY and ACKNOWLEDGED requests in group → CANCELLED
  │   failure_reason: dependency_failed
  │
  ▼ request.failed event for the failing request
  │   request.cancelled events for each cancelled dependent
  │
  ▼ Group status → failed
```

### 5.2 `on_failure: continue`

Failed request is marked FAILED; dependents that depended on it are also marked FAILED with `dependency_failed`. Independent requests in the group continue unaffected.

### 5.3 Group Timeout

If the group `timeout` duration elapses without all requests reaching a terminal state:

```
Group timeout reached
  │
  ▼ All non-terminal requests → FAILED
  │   failure_reason: group_timeout
  │
  ▼ request.failed events for each
  │   Group status → failed
```

---

## 6. Relationship to composite service definitions

Request dependency groups and composite service definitions solve overlapping but distinct problems:

| | Request Dependency Group | composite service definition |
|--|---|---|
| **Who declares** | Consumer at request time | Platform team at catalog time |
| **Reusable** | No — ad hoc | Yes — catalog item |
| **Type constraints** | None — any resources | Defined by composite service definition spec |
| **Policy governance** | Standard consumer request policies | Composite Service composition policies (CMP-*) |
| **Field injection** | Consumer-declared inject_fields | composite service definition handles internally |
| **Use case** | Ad-hoc deployment ordering | Standard composite service |

When a standard composite service exists as a composite service definition, consumers should use it. Request dependency groups are for deployments that don't fit a predefined composite service pattern.

---

## 7. New Events

| Event Type | Urgency | Trigger |
|-----------|---------|---------|
| `request.pending_dependency` | info | Request entered PENDING_DEPENDENCY state |
| `request.dependency_met` | info | Dependency reached wait_for state; request proceeding |
| `request.group_completed` | medium | All requests in group reached terminal state |
| `request.group_failed` | high | Group failed or timed out |

---

## 9. Profile-Governed Dependency Group Configuration

| Profile | Max group size | Max group timeout | Field injection validation | Max nesting depth |
|---------|---------------|-------------------|---------------------------|-------------------|
| `minimal` | 100 | P30D | advisory (warn only) | 3 |
| `dev` | 100 | P7D | advisory | 3 |
| `standard` | 50 | P3D | enforced | 3 |
| `prod` | 25 | P1D | enforced + audited | 3 |
| `fsi` | 10 | PT8H | enforced + audited + policy gated | 2 |
| `sovereign` | 5 | PT4H | enforced + audited + policy gated | 2 |

**Max group size:** Maximum number of requests in a single dependency group. RDG-002 sets the absolute upper bound at 100; profiles may set lower limits.

**Max group timeout:** Maximum value of the `timeout` field. Groups declaring a timeout beyond the profile limit are rejected (422).

**Field injection validation:** `advisory` — warns if injected fields fail schema validation but proceeds; `enforced` — rejects dispatch if injected fields fail validation; `policy gated` — field injection also passes through GateKeeper policy evaluation.

**Max nesting depth:** Maximum depth of `depends_on` chains. A→B→C is depth 2. Exceeding this is rejected at submission (422).

## 8. System Policies

| Policy | Rule |
|--------|------|
| `RDG-001` | Circular dependencies within a request group are rejected at submission time (422 Unprocessable Entity). DCM validates the dependency graph is a DAG before acknowledging the group. |
| `RDG-002` | Maximum group size is 50 requests. Groups exceeding this must use composite service definition composition or be split into multiple groups. |
| `RDG-003` | Field injection (`inject_fields`) is subject to all active Transformation policies. Injected values are not exempt from policy evaluation. |
| `RDG-004` | `PENDING_DEPENDENCY` requests count against the consumer's quota. Resources are reserved at group submission, not at dispatch time. |
| `RDG-005` | Group-level `timeout` is measured from group submission. Individual requests do not have independent timeouts while in PENDING_DEPENDENCY status. |
| `RDG-006` | A request may belong to at most one dependency group. Attempts to add a request to a second group return 409 Conflict. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
