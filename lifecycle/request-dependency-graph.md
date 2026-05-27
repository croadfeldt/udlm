# UDLM — Consumer Request Dependency Graph

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Reference — Cross-Request Ordering
**Related Documents:** [Service Dependencies](../entities/service-dependencies.md) | [Scheduled Requests](scheduled-requests.md) | [Composite Service Model](../entities/composite-service-model.md) | [Operational Models](operational-models.md)

> **Events:** Dependency resolution events (`request.dependencies_resolved`, `dependency.state_changed`) are defined in the [Event Catalog](../contracts/event-catalog.md).

> **This document maps to: DATA + PROVIDER**
>
> **Distinction from existing dependency models:**
> - Service Dependencies: *type-level* dependencies — the substrate knows that a VM *type* requires an IP type. Resolved automatically during layer assembly.
> - Composite Service Model: *composite service* dependencies — a composite service definition declares its own constituents and the realization sequences them. Consumer does not manage this.
> - **This document**: *consumer-declared cross-request ordering* — a consumer submitting multiple independent requests says "Request B may not dispatch until Request A is realized." These are requests for different resource types that have no type-level dependency; the consumer is expressing an ordering constraint for their specific deployment.

---

## 1. The Problem

A consumer deploying a three-tier application submits three requests: a database VM, an application VM, and a load balancer. Without ordering, all three dispatch simultaneously. But the application VM's startup configuration needs the database's IP address, which only exists after the database is realized.

This is not a type-level dependency (the VM type does not require a VM type). It is a *deployment-time ordering constraint* declared by the consumer for this specific deployment.

Composite service composition handles this when a platform team has pre-defined the composite service. But consumers also need to express ad-hoc ordering for their own deployments without requiring a composite service definition to exist.

---

## 2. The Request Dependency Group (Wire Contract)

A Request Dependency Group is a consumer-declared set of requests with ordering constraints between them. The structure below is normative.

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

### 2.1 wait_for Values (Closed Substrate Vocabulary)

| Value | Meaning |
|-------|---------|
| `acknowledged` | Dispatch as soon as dependency has an `entity_uuid` |
| `approved` | Dispatch when dependency has passed approval |
| `dispatched` | Dispatch when dependency has been sent to its provider |
| `realized` | Dispatch only when dependency is fully realized (default, most common) |

### 2.2 Field Injection Mechanism (Propagation Contract)

The `inject_fields` mechanism passes realized output fields from a dependency directly into a dependent request's fields — without the consumer having to poll and re-submit. The injection happens at dispatch time, after the dependency is realized.

```
Dependency realized → Realized State written
  │
  ▼ The realization reads inject_fields declarations for dependent requests
  │   For each injection: extract from_field from Realized State
  │   Inject into dependent request's field at to_field path
  │
  ▼ Dependent request proceeds to layer assembly with injected fields
```

Field injection is subject to the same Transformation policies as any other field — if a policy transforms `db_host`, the injection result passes through it.

---

## 3. PENDING_DEPENDENCY Status (Substrate Vocabulary)

A request in a dependency group that is waiting for its dependency to reach `wait_for` state has status `PENDING_DEPENDENCY`. This is part of the closed substrate state vocabulary in the Intent State lifecycle:

```
ACKNOWLEDGED → PENDING_DEPENDENCY → [dependency met] → LAYERS_ASSEMBLED → ... → REALIZED
```

Substrate-required properties of `PENDING_DEPENDENCY` requests:
- MUST be queryable with `status=PENDING_DEPENDENCY`
- MUST be cancellable via the standard cancellation endpoint
- MUST emit a `request.pending_dependency` event (closed substrate vocabulary; info urgency)
- MUST NOT time out independently — the group-level `timeout` governs

---

## 4. Failure Handling (Propagation Policy Contract)

### 4.1 `on_failure: cancel_remaining`

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

### 4.2 `on_failure: continue`

Failed request is marked FAILED; dependents that depended on it are also marked FAILED with `dependency_failed`. Independent requests in the group continue unaffected.

---

## 5. Group Timeout (Group-Level Deadline Contract)

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

The `failure_reason: group_timeout` and the propagation behavior are normative.

---

## 6. Relationship to Composite Service Definitions

Request dependency groups and composite service definitions solve overlapping but distinct problems:

| | Request Dependency Group | Composite Service Definition |
|--|---|---|
| **Who declares** | Consumer at request time | Platform team at catalog time |
| **Reusable** | No — ad hoc | Yes — catalog item |
| **Type constraints** | None — any resources | Defined by composite service definition spec |
| **Policy governance** | Standard consumer request policies | Composite Service composition policies |
| **Field injection** | Consumer-declared `inject_fields` | Composite service definition handles internally |
| **Use case** | Ad-hoc deployment ordering | Standard composite service |

When a standard composite service exists as a composite service definition, consumers should use it. Request dependency groups are for deployments that don't fit a predefined composite service pattern.

---

## 7. UDLM System Policies

| Policy | Rule |
|--------|------|
| `RDG-001` | Circular dependencies within a request group MUST be rejected at submission time (422 Unprocessable Entity). The realization MUST validate the dependency graph is a DAG before acknowledging the group. |
| `RDG-002` | Maximum group size is 50 requests by substrate default. Profile may set a lower limit; groups exceeding the limit must use composite service definition composition or be split into multiple groups. |
| `RDG-003` | Field injection (`inject_fields`) is subject to all active Transformation policies. Injected values are NOT exempt from policy evaluation. |
| `RDG-004` | `PENDING_DEPENDENCY` requests count against the consumer's quota. Resources are reserved at group submission, not at dispatch time. |
| `RDG-005` | Group-level `timeout` is measured from group submission. Individual requests do not have independent timeouts while in `PENDING_DEPENDENCY` status. |
| `RDG-006` | A request may belong to at most one dependency group. Attempts to add a request to a second group MUST return 409 Conflict. |

---

*UDLM substrate document. Realization-specific group submission/parsing, dependency resolution and dispatch orchestration, PENDING_DEPENDENCY lifecycle internals, failure handling execution code, group timeout enforcement, consumer API endpoint additions, new event implementations, and profile-governed dependency group constraints live in the consuming realization's documentation.*
