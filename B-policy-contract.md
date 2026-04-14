# DCM — Unified Policy Contract


**Document Status:** ✅ Complete
**Document Type:** Architecture Foundation
**Related Documents:** [Foundational Abstractions](00-foundations.md) | [Provider Contract](A-provider-contract.md) | [Policy Profiles](14-policy-profiles.md) | [Governance Matrix](27-governance-matrix.md) | [OPA Integration](../specifications/dcm-opa-integration-spec.md)

---

## 1. The Unified Policy Contract

Every Policy in DCM — regardless of type — implements a single base contract. What varies between policy types is the **output schema**: what the Policy produces when its match conditions are satisfied.

```
┌─────────────────────────────────────────────────────────┐
│                 BASE POLICY CONTRACT                     │
│                                                          │
│  Match Conditions · Enforcement Level · Domain          │
│  Lifecycle · Audit · Shadow Mode                         │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │              OUTPUT SCHEMA                       │   │
│  │                                                  │   │
│  │  What this policy type produces when it fires.   │   │
│  │  Eight typed output schemas.                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Adding a new policy type** = define a new output schema. The base contract, evaluation algorithm, lifecycle, and audit obligations are inherited.

---

## 2. Base Contract — Match Conditions

**A policy fires when the data says it should fire.** There is no pre-assignment of policies to resource types, no routing tables, no static configuration. A policy declares its match conditions against data fields. If the data matches, the policy evaluates. Any piece of data in the request can be an inclusion trigger for a policy.

### 2.1 Four Match Sources

Policies can match against data from four sources, all available during evaluation:

| Source | What it contains | Examples |
|--------|-----------------|---------|
| **Request payload** | Consumer's declared fields + assembled layers + provenance | `resource_type`, `cpu_count`, `network_segment`, `sovereignty_zone`, `environment`, `application_uuid`, custom tags |
| **Operation context** | What lifecycle operation is being performed and what changed | `operation.type`, `operation.changed_fields`, `operation.pipeline_stage` |
| **Evaluation Context** | Constraints emitted by policies earlier in this evaluation pass | `allowed_zones`, `distribution_requirement`, `cost_ceiling`, `excluded_providers` |
| **Entity metadata** | Tenant, actor, resource classification, lifecycle state | `tenant_uuid`, `actor.roles`, `data_classification`, `lifecycle_state`, `cost_center` |

All four sources are addressable via dot-notation field paths.

### 2.2 Lifecycle Operation Types

Every request into DCM carries an `operation.type` that identifies what lifecycle operation is being performed. This is the primary dimension for scoping which policies fire on which operations.

| Operation Type | When it occurs | Description |
|---------------|---------------|-------------|
| `initial_provisioning` | Day 0 — first request for a new resource | Full pipeline: assembly, all policies, placement, dispatch |
| `update` | Day 2 — modify an existing operational resource | Partial pipeline: assembly with existing entity as base, policies evaluate changed fields |
| `scale` | Day 2 — change capacity (replicas, CPU, memory, storage) | Subset of update — only scaling-related fields change |
| `rehydration` | Rebuild from stored state (DR, migration, refresh) | Full pipeline: all current policies re-evaluate from intent or realized state |
| `decommission` | Day N — request to remove a resource | Decommission pipeline: dependency checks, notification, revocation, provider teardown |
| `ownership_transfer` | Transfer entity between tenants | Re-evaluates tenant-scoped policies under new tenant context |
| `subscription_renewal` | Subscription approaching expiry or renewal | Subscription lifecycle policies fire; may trigger re-evaluation of placement |
| `drift_remediation` | Discovered state diverges from realized state | Remediation policies fire; may re-provision or accept drift |
| `provider_migration` | Move entity to a different provider | Full placement re-evaluation; sovereignty re-evaluation |
| `compliance_rescan` | Policy change triggers re-evaluation of existing resources | All matching policies re-evaluate; no placement unless policy requires it |

**`operation.changed_fields`** — For `update` and `scale` operations, this is an array of field paths that changed from the current realized state. This enables policies to fire only when relevant fields change:

```yaml
# Fire only when placement-affecting fields change
match:
  conditions:
    - field: operation.type
      operator: in
      value: [initial_provisioning, rehydration, provider_migration]
  condition_logic: any

# OR: fire on updates, but only when network or zone fields changed
match:
  conditions:
    - field: operation.type
      operator: equals
      value: "update"
    - field: operation.changed_fields
      operator: contains
      value: "placement.zone"
  condition_logic: all
```

### 2.3 Policy Lifecycle Scope

Each policy declares which lifecycle operations it applies to. This is configured per policy via `lifecycle_scope`:

```yaml
policy_artifact:
  handle: "placement/sovereignty-zone-check"
  lifecycle_scope:
    operations: [initial_provisioning, rehydration, provider_migration]
    # This policy fires on: new resources, rebuilds, and provider moves
    # Does NOT fire on: memory updates, scaling, decommissions

policy_artifact:
  handle: "validation/vm-size-limits"
  lifecycle_scope:
    operations: [initial_provisioning, update, scale]
    changed_field_filter: ["cpu_count", "memory_gb", "storage_gb"]
    # Fires on new resources AND on updates that change sizing fields
    # Does NOT fire on: tag changes, owner changes, etc.

policy_artifact:
  handle: "sovereignty/data-residency"
  lifecycle_scope:
    operations: all                         # fires on EVERY lifecycle operation
    # Sovereignty is always checked — no exceptions
```

**Default lifecycle scope by policy type:**

| Policy Type | Default `lifecycle_scope.operations` | Rationale |
|-------------|-------------------------------------|-----------|
| GateKeeper | `all` | Gatekeeping rules should always be checked |
| Validation | `[initial_provisioning, update, scale, rehydration]` | Structural validation on any data change |
| Transformation | `[initial_provisioning, rehydration]` | Inject/enrich on new builds and rebuilds; skip on minor updates |
| Recovery | `all` | Recovery posture always applicable |
| Orchestration Flow | `[initial_provisioning, rehydration, decommission]` | Pipeline orchestration on major lifecycle transitions |
| Governance Matrix Rule | `all` | Boundary controls always checked |
| Lifecycle | `all` | TTL/expiry constraints always active |
| ITSM Action | `[initial_provisioning, update, decommission]` | ITSM records on provisioning, changes, and teardown |

These defaults can be overridden per policy. Profile-governed minimums prevent downgrading below security requirements:

| Profile | Minimum lifecycle scope |
|---------|------------------------|
| `minimal`, `dev` | No minimum — any scope permitted |
| `standard`, `prod` | GateKeeper and Governance Matrix must be `all` |
| `fsi`, `sovereign` | GateKeeper, Governance Matrix, and sovereignty-concern policies must be `all` — cannot be scoped to skip any lifecycle operation |

### 2.4 Specificity Spectrum

The same match model expresses policies at every level of specificity:

```yaml
# Universal — fires on everything (no conditions)
match:
  conditions: []

# Classification-scoped — fires on any resource handling PHI
match:
  conditions:
    - field: request.data_classification
      operator: in
      value: ["phi", "pci"]

# Resource-type scoped — fires on all VMs
match:
  conditions:
    - field: request.resource_type
      operator: equals
      value: "Compute.VirtualMachine"

# Zone + segment scoped — fires on any resource in DMZ in zone A
match:
  conditions:
    - field: request.network_segment
      operator: equals
      value: "dmz"
    - field: request.placement.zone
      operator: equals
      value: "zone-a"
  condition_logic: all

# Fully specific — VMs in DMZ in zone A for one application
match:
  conditions:
    - field: request.resource_type
      operator: equals
      value: "Compute.VirtualMachine"
    - field: request.network_segment
      operator: equals
      value: "dmz"
    - field: request.placement.zone
      operator: equals
      value: "zone-a"
    - field: request.application_uuid
      operator: equals
      value: "xxxx-xxxx-xxxx"
  condition_logic: all

# Context-aware — fires when sovereignty has restricted zones
match:
  conditions:
    - field: context.constraints.zone_restriction
      operator: exists
  condition_logic: all
```

### 2.5 Match Operators

| Operator | Description |
|----------|------------|
| `equals` | Exact match |
| `not_equals` | Negation |
| `in` | Value is in a list |
| `not_in` | Value is not in a list |
| `exists` | Field is present (any value) |
| `not_exists` | Field is absent |
| `minimum` | Numeric ≥ threshold |
| `maximum` | Numeric ≤ threshold |
| `contains` | String/array contains substring/element |
| `matches` | Regex match |
| `starts_with` | Field path prefix match (for hierarchical resource types) |

`condition_logic: all` (default) requires all conditions to match. `condition_logic: any` requires at least one.

### 2.6 Boundary Match Conditions (Governance Matrix)

Governance Matrix Rules use a four-axis boundary model for matching — subject, data, target, and context. These are structurally the same as field conditions but organized by the four axes of the Governance Matrix:

```yaml
match:
  subject:
    type: <subject_type>
    identity: { ... }
    tenant: { ... }
  data:
    classification: <level>
    resource_type: <fqn>
    field_paths: { mode: allowlist | blocklist, paths: [...] }
  target:
    type: <target_type>
    sovereignty_zone: { match: <zone_id> }
    accreditation_held: { includes: [...] }
    trust_posture: <posture>
  context:
    profile: { deployment_posture: <posture> }
    zero_trust_posture: { minimum: <level> }
    federated: true | false
```

---

## 3. Base Contract — Enforcement Level

```yaml
enforcement: hard | soft

# hard: cannot be relaxed by any downstream rule at any domain level
#        A hard DENY cannot be overridden by any Tenant, entity, or operator override
#        Reserved for: sovereign/classified data boundaries, regulatory hard requirements

# soft: establishes a default that downstream rules can tighten
#        A soft ALLOW can be restricted to DENY by a more-specific rule
#        A soft DENY cannot be relaxed to ALLOW by a downstream rule
```

Most policies are soft. Hard enforcement is reserved for absolute security constraints.

---

## 4. Base Contract — Domain Precedence

Policies operate within a domain hierarchy. More-specific domains win within the same concern type:

```
system (most trusted — DCM built-in)
  └── platform (platform admin declared)
        └── tenant (Tenant admin declared)
              └── resource_type (per resource type spec)
                    └── entity (per specific entity — most specific)
```

Within the same domain level, DENY wins over ALLOW. More-specific domain wins over less-specific.

---

## 5. Base Contract — Artifact Structure

All policies are first-class DCM Data artifacts. They share the standard artifact metadata and lifecycle:

```yaml
policy_artifact:
  # Standard DCM artifact metadata (all artifacts carry this)
  artifact_metadata:
    uuid: <uuid>
    handle: "<domain>/<concern>/<name>"
    version: "1.0.0"
    status: developing | proposed | active | deprecated | retired
    owned_by: { display_name: "<team>", email: "<email>" }
    created_by: { display_name: "<actor>" }
    created_via: pr | api | migration | system

  # Policy classification
  policy_type: <type>                    # gatekeeper | validation | transformation |
                                         # recovery | orchestration_flow |
                                         # governance_matrix_rule | lifecycle
  concern_type: <concern>                # security | compliance | operational |
                                         # recovery_posture | zero_trust_posture |
                                         # data_authorization_boundary | orchestration_flow

  domain: system | platform | tenant | resource_type | entity

  # Match conditions (Model A or B — see Section 2)
  match: { ... }

  # Enforcement
  enforcement: hard | soft

  # Output schema (varies by policy_type — see Sections 8-14)
  output: { ... }

  # Audit
  audit_on: [ALLOW, DENY, STRIP_FIELD]   # which decisions produce audit records
  notification_on: [DENY]               # which decisions trigger notifications
  notification_urgency: low | medium | high | critical

  # Compliance reference
  compliance_basis: "<regulatory citation>"
  review_required_before: "<ISO 8601 date>"
```

---

## 6. Base Contract — Lifecycle

All policies follow the five-status lifecycle:

| Status | Behavior |
|--------|---------|
| `developing` | Dev mode only. Not applied in any environment. |
| `proposed` | Shadow mode: executes against real traffic; output captured but never applied. Used for safe validation. |
| `active` | Applied to all matching requests. |
| `deprecated` | Still active; replacement available; warning on evaluation. |
| `retired` | Terminal; cannot be used. |

**Shadow mode (proposed status):** The policy evaluates against real traffic. Its output is captured in the Validation Store. Platform admins review shadow results before promoting to active. This is the primary mechanism for safe policy change management.

---

## 7. Evaluation Model

### 7.1 Evaluation Context

Every request evaluation creates a transient **Evaluation Context** — a shared constraint space that policies read from and write to during evaluation. The context accumulates constraints, hints, and resolutions across evaluation passes.

```yaml
evaluation_context:
  request_uuid: <uuid>
  pass_number: 1
  max_passes: 3                         # configurable; default 3

  # Constraints accumulate — each has provenance
  constraints:
    - constraint_uuid: <uuid>
      source_policy: "<handle>"
      source_domain: system | platform | tenant | resource_type | entity
      constraint_type: <string>         # zone_restriction, distribution_requirement, cost_ceiling, etc.
      field: "<dot-notation path>"
      operator: restrict_to | require | prefer | exclude
      value: <any>
      binding: hard | soft              # hard = cannot be overridden; soft = preference
      reason: "<human-readable>"
      pass_added: <int>

  # Hints flow between policies — transient, never persisted as entity data
  hints:
    - from_policy: "<handle>"
      to_concern: "<concern_type>"      # placement, security, compliance, etc.
      hint_type: <string>
      value: <any>
      pass_added: <int>

  # Resolutions record how conflicts were handled
  resolutions:
    - conflict: "<description>"
      strategy: <string>                # from on_conflict declaration
      result: "<description>"
      resolved_by: auto | human | escalation
      pass_resolved: <int>

  # Resolved constraint set — what downstream policies and placement use
  resolved_constraints: { ... }
```

The Evaluation Context is **transient** — it exists only during request evaluation. Hints are ephemeral. But the complete context snapshot at each pass is captured in the audit record.

### 7.2 Three-Phase Evaluation

Each pass through the policy engine follows three phases:

**Phase 1 — Constraint Collection.** All policies whose match conditions are satisfied evaluate and emit constraints into the Evaluation Context. Sovereignty writes `allowed_zones`. Tier policy writes `min_replicas` and `min_zones`. Cost policy writes `preferred_zones`. No final decisions — only constraint declarations.

**Phase 2 — Constraint Resolution.** The Policy Engine examines collected constraints for conflicts. When constraints conflict, it checks if the conflicting policies declare resolution strategies via `on_conflict`. Auto-resolvable conflicts are resolved and recorded. Unresolvable conflicts are escalated (request paused for human decision).

**Phase 3 — Application and Validation.** Transformations apply using the resolved constraint set. Placement uses the constrained parameters. GateKeepers re-validate the final assembled payload against the full constraint set. If validation fails, the failure is added as a new constraint and the system loops to the next pass.

```
Pass 1:
  Phase 1: Collect constraints
    → sovereignty: allowed_zones = [A, B]
    → tier: min_replicas = 6, min_zones = 2, distribution = balanced
  Phase 2: Resolve conflicts
    → tier wants 3 zones, sovereignty allows 2
    → tier declares on_conflict.zone_shortage: redistribute
    → auto-resolve: 3/3 across zones A and B
  Phase 3: Apply and validate
    → transformations inject config
    → placement distributes 3/3
    → GateKeepers re-validate → PASS
  → Converged.

Pass 1 (loop scenario):
  Phase 3: Validate FAILS → cost optimization placed all 6 in zone A
    but tier requires balanced distribution
  Pass 2:
    New constraint: "zone-a max 4 replicas" (from tier validation failure)
    Re-resolve → 3/3
    Re-validate → PASS
  → Converged on pass 2.

Pass 1 (escalation scenario):
  Phase 2: sovereignty allows 1 zone, tier requires 2+ zones
    No auto-resolution → both are hard constraints
  → Request paused. Escalation with conflict report.
```

Maximum passes is configurable (default 3). If the evaluation does not converge, the request fails with a full conflict report showing every constraint, every conflict, and every attempted resolution.

### 7.3 Constraint Emission

Policies declare what constraints they emit via `emits_constraints` in their artifact:

```yaml
policy_artifact:
  handle: "sovereignty/eu-data-residency"
  policy_type: gatekeeper
  match:
    conditions:
      - field: request.data_classification
        operator: in
        value: ["restricted", "phi", "pci"]

  # What this policy contributes to the evaluation context
  emits_constraints:
    - field: "placement.allowed_zones"
      constraint_type: zone_restriction
      binding: hard
    - field: "placement.excluded_providers"
      constraint_type: provider_exclusion
      binding: hard

  # How to handle conflicts with this policy's constraints
  on_conflict:
    default: deny                       # hard sovereignty — no auto-resolution
```

```yaml
policy_artifact:
  handle: "tier/tier-1-ha-distribution"
  policy_type: transformation
  match:
    conditions:
      - field: request.tier
        operator: equals
        value: "tier-1"

  emits_constraints:
    - field: "placement.zone_distribution"
      constraint_type: distribution_requirement
      binding: hard

  on_conflict:
    zone_shortage: redistribute         # auto-resolve: spread across available zones
    replica_shortage: deny              # can't reduce replicas — deny
    default: escalate
```

### 7.4 Evaluation Order

Within a single pass:

1. **Domain precedence** — system evaluates first, then platform, then tenant, then resource_type, then entity. More-specific domains evaluate after (and can override) less-specific.
2. **Within a domain level** — policies evaluate in declared priority order.
3. **Parallel evaluation** — policies with no data dependencies on each other evaluate concurrently within the same domain level and phase.
4. **Context-dependent policies** — policies matching on `context.constraints.*` evaluate after the policies that emit those constraints.
5. **DENY wins** — at the same domain level, any DENY blocks regardless of other policies at that level.

### 7.5 Per-Pass Audit

Every evaluation pass produces an audit record. The record captures the complete state — not just the outcome:

```yaml
policy_evaluation_audit:
  request_uuid: <uuid>
  pass_number: <int>
  evaluation_context_snapshot: { ... }    # full context at this pass
  policies_evaluated:
    - policy_uuid: <uuid>
      policy_version: "<semver>"
      matched: true | false
      output: { ... }
      constraints_emitted: [...]
      hints_emitted: [...]
      duration_ms: <int>
  conflicts_detected: [...]
  resolutions_applied: [...]
  pass_result: converged | loop | escalated | failed
  total_duration_ms: <int>
```

Every pass, every constraint, every hint, every resolution — fully auditable. If an auditor asks "why 3/3 instead of 2/2/2?" the trail shows: sovereignty restricted zones, tier auto-resolved via redistribute, placement honored resolved constraints.

---

## 8. Constraint Type Registry

Constraint types are the shared vocabulary of the Evaluation Context. Every constraint emitted by a policy and every context field matched by a policy must reference a registered constraint type. Freeform strings are not permitted — if two policies should interact, they must agree on the vocabulary, and the registry enforces that agreement.

### 8.1 Registry Entry

```yaml
constraint_type:
  handle: "zone_restriction"
  version: "1.0.0"
  tier: core                              # core (DCM built-in) | organization (custom)
  schema:                                 # OpenAPI v3 schema for the constraint value
    type: object
    properties:
      allowed:
        type: array
        items: { type: string }
        description: "Zones where placement is permitted"
      excluded:
        type: array
        items: { type: string }
        description: "Zones where placement is prohibited"
    additionalProperties: false
  semantic: "Restricts which zones a resource may be placed in"
  binding_levels: [hard, soft]
  emittable_by: [gatekeeper, validation, governance_matrix_rule]
  consumable_by: [transformation, gatekeeper, validation]
```

### 8.2 Built-In Constraint Types (Core Tier)

| Constraint Type | Schema (key fields) | Emitted by | Consumed by |
|----------------|---------------------|------------|-------------|
| `zone_restriction` | `{allowed: [string], excluded: [string]}` | Sovereignty, compliance | Placement, distribution |
| `provider_restriction` | `{allowed: [uuid], excluded: [uuid]}` | Sovereignty, accreditation | Placement |
| `distribution_requirement` | `{min_replicas: int, min_zones: int, distribution: enum}` | Tier/HA policies | Placement |
| `cost_ceiling` | `{max_per_unit_hour: decimal, currency: string}` | Budget policies | Placement, approval |
| `network_restriction` | `{allowed_segments: [string], excluded: [string]}` | Security, compliance | Transformation, placement |
| `resource_limits` | `{max_cpu: int, max_memory_gb: int, max_storage_gb: int}` | Tier policies, quotas | Validation |
| `compliance_requirement` | `{frameworks: [string], controls: [string]}` | Compliance profiles | Validation, transformation |
| `sovereignty_boundary` | `{data_residency: string, jurisdictions: [string]}` | Sovereignty | All downstream |
| `approval_requirement` | `{required: bool, approvers: [string], quorum: int}` | Tier, compliance | Approval flow |
| `scheduling_constraint` | `{maintenance_window: cron, blackout_periods: [range]}` | Operational | Placement, lifecycle |

Organizations can register custom constraint types (same as custom resource types). A financial services org might register `trading_window_restriction` or `pci_scope_boundary`.

### 8.3 Hint Types

Hints are soft, advisory signals — not hard constraints. They follow the same registry pattern:

```yaml
hint_type:
  handle: "cost_preference"
  version: "1.0.0"
  schema:
    type: object
    properties:
      preferred_zones: { type: array, items: { type: string } }
      reason: { type: string }
  semantic: "Advisory preference for lower-cost zones"
  emittable_by: [transformation, validation]
  consumable_by: [gatekeeper, transformation]
```

### 8.4 Validation at Policy Activation

When a policy is promoted from `developing` to `proposed` (shadow mode), the Policy Engine validates:

1. Every `emits_constraints[].constraint_type` is a registered constraint type
2. The emitted value structure matches the registered schema
3. The emitting policy's type is in the constraint type's `emittable_by` list
4. Every `match.conditions[].field` referencing `context.constraints.*` corresponds to a registered constraint type
5. The consuming policy's type is in the constraint type's `consumable_by` list

If any check fails, the policy cannot be activated. Vocabulary mismatches are caught at authoring time, not when a production request fails silently.

---

## 9. Policy Templates

Policy templates separate reusable Rego logic from instance-specific configuration, following the OPA Gatekeeper ConstraintTemplate pattern. A template defines the logic and declares its parameter schema, emitted constraint types, and consumed constraint types. A policy artifact is an instance of a template with bound parameters and match conditions.

### 9.1 Template Definition

```yaml
policy_template:
  handle: "dcm.sovereignty.zone-restriction"
  version: "1.0.0"
  tier: core

  # Parameters this template accepts (OpenAPI v3 schema)
  parameter_schema:
    type: object
    required: [classification_levels, allowed_zones]
    properties:
      classification_levels:
        type: array
        items: { type: string }
      allowed_zones:
        type: array
        items: { type: string }

  # Registered constraint types this template emits
  emits: [zone_restriction, provider_restriction]

  # Registered constraint types this template reads from context
  consumes: []

  # Rego logic
  rego: |
    package dcm.sovereignty.zone_restriction
    import data.dcm.constraint_types

    emit_constraint[constraint] {
      input.request.data_classification == input.parameters.classification_levels[_]
      constraint := constraint_types.zone_restriction({
        "allowed": input.parameters.allowed_zones,
        "excluded": [],
      })
    }

    deny[msg] {
      not input.request.placement.zone == input.parameters.allowed_zones[_]
      msg := sprintf("Zone %v not in allowed zones %v for %v data",
        [input.request.placement.zone,
         input.parameters.allowed_zones,
         input.request.data_classification])
    }
```

### 9.2 Policy Artifact (Template Instance)

```yaml
policy_artifact:
  handle: "sovereignty/eu-data-residency"
  template: "dcm.sovereignty.zone-restriction"
  version: "1.0.0"
  domain: system
  policy_type: gatekeeper

  parameters:
    classification_levels: [restricted, phi, pci]
    allowed_zones: [eu-west-1, eu-central-1]

  match:
    conditions:
      - field: request.data_classification
        operator: in
        value: [restricted, phi, pci]

  enforcement: hard
  on_conflict:
    default: deny
```

### 9.3 DCM Constraint Types Library

DCM provides a Rego library (`data.dcm.constraint_types`) bundled with every OPA instance. It provides constructor functions for every registered constraint type that enforce the schema at compile time:

```rego
package dcm.constraint_types

zone_restriction(params) = constraint {
  is_array(params.allowed)
  constraint := {
    "constraint_type": "zone_restriction",
    "value": params,
  }
}

distribution_requirement(params) = constraint {
  is_number(params.min_replicas)
  is_number(params.min_zones)
  constraint := {
    "constraint_type": "distribution_requirement",
    "value": params,
  }
}
```

This library is auto-generated from the Constraint Type Registry. Policy authors call `constraint_types.zone_restriction(...)` instead of crafting raw constraint objects. Wrong field names or types are caught at bundle compilation — not at runtime.

### 9.4 Template Registration Validation

When a template is registered:

1. Rego compiles without errors
2. Parameter schema is valid OpenAPI v3
3. All emitted constraint types are registered in the Constraint Type Registry
4. All consumed constraint types are registered
5. Rego uses the `data.dcm.constraint_types` library for emissions (not raw objects)

When a policy artifact is created from a template:

1. Parameters validate against the template's parameter schema
2. Match conditions reference valid field paths
3. Emitted/consumed constraint types match the template's declarations

---

## 10. Output Schema — GateKeeper

**Fires on:** Request payload at assembly time.
**Produces:** An allow or deny decision for the request.

```yaml
gatekeeper_output:
  decision: allow | deny
  reason: "<human-readable — required for deny>"
  field_locks:                           # optional: lock specific fields as immutable
    - field: <field_path>
      lock_type: immutable | constrained
      constraint_schema: <JSON Schema>   # if constrained
  warnings: ["<optional advisory messages>"]
```

**Policy Engine behavior:**
- `allow` → request proceeds; field_locks applied to payload
- `deny` → request blocked; `reason` included in consumer error response
- Any active GateKeeper producing `deny` → request blocked (all must allow)

---

## 11. Output Schema — Validation

**Fires on:** Request payload; validates correctness of field values.
**Produces:** Pass or fail with field-level detail.

```yaml
validation_output:
  result: pass | fail
  field_results:
    - field: <field_path>
      result: valid | invalid
      message: "<validation failure description>"
      suggested_value: <value>           # optional
  advisory: ["<non-blocking notes>"]
```

**Policy Engine behavior:**
- `pass` → request proceeds
- `fail` → request blocked; `field_results` included in consumer error response

---

## 12. Output Schema — Transformation

**Fires on:** Request payload; enriches, modifies, or injects field values.
**Produces:** A set of field mutations to apply to the payload.

```yaml
transformation_output:
  mutations:
    - field: <field_path>
      operation: set | append | delete | lock
      value: <new_value>                 # for set/append
      reason: "<why this mutation was made>"
      source_type: enrichment | injection | normalization | correction
```

**Policy Engine behavior:** All mutations from all active Transformation policies are collected and applied to the payload. Each mutation is recorded in field-level provenance with the policy_uuid as source.

---

## 13. Output Schema — Recovery

**Fires on:** A failure or ambiguity trigger condition (DISPATCH_TIMEOUT, PARTIAL_REALIZATION, CANCELLATION_FAILED, etc.).
**Produces:** A recovery action and parameters.

```yaml
recovery_output:
  action: DRIFT_RECONCILE | DISCARD_AND_REQUEUE | DISCARD_NO_REQUEUE |
          ACCEPT_LATE_REALIZATION | COMPENSATE_AND_FAIL |
          NOTIFY_AND_WAIT | ESCALATE | RETRY
  action_parameters:
    requeue_delay: PT0S                  # for DISCARD_AND_REQUEUE
    max_attempts: 3                      # for RETRY
    backoff: exponential                 # for RETRY
    deadline: PT4H                       # for NOTIFY_AND_WAIT
    on_deadline_exceeded: ESCALATE       # for NOTIFY_AND_WAIT
  notify_before_action: true
  notification_urgency: high
```

**Policy Engine behavior:** The first matching Recovery policy's action is executed. Recovery policies follow the same domain precedence — resource_type override wins over tenant override wins over profile default.

---

## 14. Output Schema — Orchestration Flow

**The two-level orchestration model:**

Orchestration in DCM operates at two levels that compose through the same Policy Engine:

- **Level 1 — Named Workflow Artifacts:** Orchestration Flow Policies with `ordered: true` declare an explicit, visible, auditable sequence of steps. Each step references a payload type from the closed vocabulary. This is what operators see and reason about. Adding a step = adding to a workflow Policy.
- **Level 2 — Dynamic Policies:** GateKeeper, Transformation, Recovery, and Governance Matrix Policies fire when their conditions match, within or alongside workflow steps, without being declared in the workflow. Adding conditional behavior = writing a dynamic policy.

The Request Orchestrator (event bus) routes all payload type events through the Policy Engine. Both named workflow steps and dynamic policies evaluate against the same events. The workflow provides the skeleton; dynamic policies fill in conditional behavior.

**Fires on:** Pipeline payload type events.
**Produces:** A flow directive governing step ordering.

```yaml
orchestration_flow_output:
  ordered: true | false
  steps:
    - step: 1
      policy_handle: "<policy to execute at this step>"
      condition: "<additional condition for this step>"
      on_fail: halt | skip | escalate
  parallel_groups:                       # steps that may execute in parallel
    - [step_1_id, step_2_id]
```

**Step vocabulary** — steps reference payload types from the closed vocabulary, mapping to control plane operations:

| Payload type | Maps to |
|-------------|---------|
| `request.initiated` | Start of request pipeline |
| `request.layers_assembled` | Layer assembly complete |
| `request.policies_evaluated` | All policies evaluated |
| `request.placement_complete` | Provider selected |
| `request.dispatched` | Sent to provider |
| `discovery.cycle_complete` | Discovery cycle done |
| `drift.detected` | Drift found |
| `recovery.timeout_fired` | Dispatch timeout |
| `provider_update.received` | Provider update notification |

Custom steps extend this vocabulary by publishing new payload types.

**Policy Engine behavior:** When `ordered: true`, steps execute in declared sequence. When `ordered: false`, the Policy Engine executes steps in parallel where no data dependencies exist. Orchestration Flow policies compose with standard GateKeeper and Transformation policies — both types evaluate in the same pipeline.

---

## 15. Output Schema — Governance Matrix Rule

**Fires on:** Any cross-boundary interaction (DCM → Provider, DCM → Peer DCM, Provider → DCM).
**Produces:** A boundary control decision with optional field permissions.

```yaml
governance_matrix_output:
  decision: ALLOW | DENY | ALLOW_WITH_CONDITIONS | STRIP_FIELD | REDACT | AUDIT_ONLY
  conditions:                            # for ALLOW_WITH_CONDITIONS
    - field: <axis_field>
      operator: <operator>
      value: <value>
  field_permissions:
    mode: allowlist | blocklist | passthrough
    paths: ["<field_path>", ...]
    on_blocked_field: STRIP_FIELD | DENY_REQUEST | REDACT
  audit_on: [ALLOW, DENY, STRIP_FIELD]
  notification_on: [DENY]
  notification_urgency: critical
```

**Policy Engine behavior:** Hard DENY evaluated first — any hard DENY is terminal. Soft decisions evaluated by domain precedence; DENY wins over ALLOW at the same level. Field permissions applied after decision determined. Audit record always written.

---

## 16. Output Schema — Lifecycle Policy

**Fires on:** Relationship events (related entity state changes, relationship creation/release).
**Produces:** A lifecycle action to apply to related entities.

```yaml
lifecycle_policy_output:
  on_related_destroy: cascade | protect | detach | notify
  on_related_suspend: cascade | ignore | notify
  on_last_relationship_released: destroy | retain | notify
  propagation_depth: 1 | 2 | N          # how many relationship hops to propagate
  action_delay: PT0S                     # grace period before executing action
```

**Policy Engine behavior:** When a relationship event occurs, all matching Lifecycle policies on both related entities are evaluated. The most restrictive action wins (save beats destroy). Conflicts between policies at the same domain level produce a CONFLICT_ERROR at policy ingestion time.

---

## 17. Output Schema — ITSM Action

The ITSM Action policy type triggers actions in connected ITSM systems as a side-effect of DCM pipeline events.

```yaml
itsm_action_output:
  type: itsm_action
  itsm_provider_uuid: <uuid>       # registered ITSM Provider UUID
  action: create_change_request | update_change_request | close_change_request |
          create_incident | update_incident | close_incident |
          update_cmdb_ci | create_cmdb_ci | retire_cmdb_ci |
          create_service_request | link_parent_record
  action_payload:
    <field>: <value | "{{ template_expression }}">
  store_reference_on_entity: <bool>   # default: false
  reference_label: <string>
  block_until_created: <bool>         # default: false — see ITSM-005
  block_timeout: <ISO 8601 duration>  # required if block_until_created: true
  on_failure: log_and_continue | alert_and_continue | alert_only
```

> **See [ITSM Integration](42-itsm-integration.md)** for full ITSM Provider registration, capability declarations, supported ITSM systems (ServiceNow, Jira, Remedy, Freshservice, PagerDuty, generic REST), policy examples, and system policies (ITSM-001–007, ITSM-POL-001–004).

**Key constraints:**
- ITSM Action policies are side-effect only — they do not produce allow/deny decisions
- `block_until_created: true` creates a pipeline gate with mandatory timeout (ITSM-005)
- Multiple ITSM Action policies on the same event fire independently (ITSM-POL-004)
- Full audit record produced on every evaluation (ITSM-POL-003)

## 18. Policy Override Model

When a policy blocks a request and the block needs to be overridden, DCM provides five override mechanisms organized by severity. Every override — regardless of mechanism — produces a Merkle tree audit leaf capturing the override justification, authorizer identity, and the policy that was overridden.

### 18.1 Override Policy (Planned Exceptions)

A policy artifact that explicitly overrides another policy for a defined scope. Goes through the standard policy lifecycle (developing → proposed → active) with review and shadow testing.

```yaml
policy_artifact:
  handle: "override/payments-team-zone-c-exception"
  policy_type: override
  overrides: "sovereignty/eu-data-residency"
  scope:
    tenant_tags: ["payments"]
    resource_types: ["Compute.VirtualMachine"]
    operations: [rehydration, provider_migration]
  effect: relax                              # relax a deny → allow
  justification: "Payments team DR requires zone-c replica per BCP-2026-04"
  expires_at: "2027-01-01"
  review_required_before: "2026-10-01"
  compensating_controls: []                  # optional — see Model 5
```

**Constraint:** Override policies cannot target `enforcement: hard` policies. Hard policies can only be overridden via Exception Grant or Manual Override with dual-approval. This is validated at policy activation — attempting to create an override policy targeting a hard policy is rejected.

### 18.2 Exception Grant (Pre-Authorized Waivers)

A pre-authorized, time-bounded, scope-limited waiver registered before any specific request needs it. Used for known upcoming needs (DR exercises, compliance transition periods, migration windows).

```yaml
exception_grant:
  grant_uuid: <uuid>
  policy_handle: "sovereignty/eu-data-residency"
  scope:
    tenants: ["payments-team"]
    resource_types: ["Compute.VirtualMachine"]
    operations: [rehydration, provider_migration]
  effect: relax
  compensating_controls:
    - "audit/enhanced-logging"               # require field-granularity audit during grant
    - "notification/security-team-alert"     # notify security team on every use
  authorized_by: <actor_uuid>
  approved_by: <actor_uuid>                  # dual-approval required for hard policies
  justification: "BCP-2026-04 DR requires zone-c capability during Q2"
  effective_from: "2026-04-01"
  expires_at: "2026-07-01"
  review_required_before: "2026-06-15"
  renewable: true
  max_renewals: 2
  usage_count: 0                             # tracks how many times this grant was used
  max_usage: null                            # null = unlimited within time window
```

Exception Grants can target hard enforcement policies — but require dual-approval. Compensating controls are mandatory when overriding hard policies.

### 18.3 Manual Override (Immediate Authorization)

A human with override authority grants a one-time exception for a specific blocked request. Used when a request is blocked and needs to proceed immediately (DR scenario, production incident, time-sensitive deployment).

```yaml
manual_override:
  override_uuid: <uuid>
  request_uuid: <uuid>                       # tied to a specific request
  policy_overridden: "sovereignty/eu-data-residency"
  authorized_by: <actor_uuid>                # must have override authority role
  approved_by: <actor_uuid | null>           # second approver (required for hard policies)
  reason: "DR scenario — zone-a unavailable, need zone-c placement"
  scope: single_request                      # this request only — cannot be reused
  expires_at: "2026-04-05T00:00:00Z"         # expires if not used within window
  compensating_controls:
    - "audit/enhanced-logging"
```

**Constraint:** Manual overrides of `enforcement: hard` policies require dual-approval (see §18.4). A single person can never override a hard policy.

### 18.4 Dual-Approval Escalation

Not a separate override mechanism — a modifier on Exception Grants and Manual Overrides that applies whenever a `hard` enforcement policy is being overridden. Two authorized individuals from different roles must independently approve.

```yaml
dual_approval:
  first_approver:
    actor_uuid: <uuid>
    role: security_officer                   # must be from security role
    approved_at: <ISO 8601>
  second_approver:
    actor_uuid: <uuid>
    role: operations_lead                    # must be from operations role
    approved_at: <ISO 8601>
  role_separation_enforced: true             # same role cannot fill both slots
```

Dual-approval is automatically required whenever:
- A Manual Override targets a `hard` enforcement policy
- An Exception Grant targets a `hard` enforcement policy
- Profile is `fsi` or `sovereign` and any override mechanism is used

### 18.5 Compensating Control Substitution

Instead of overriding a policy, substitute a different set of controls that satisfies the same security/compliance intent through a different mechanism. The original policy is not relaxed — it is satisfied differently.

```yaml
compensating_control:
  control_uuid: <uuid>
  replaces_policy: "sovereignty/eu-data-residency"
  when:
    conditions:
      - field: operation.type
        operator: equals
        value: rehydration
  substitute_controls:
    - policy_handle: "sovereignty/sovereign-grade-encryption"
    - policy_handle: "audit/field-granularity-override"
    - policy_handle: "notification/security-team-immediate"
  justification: "Zone-c permitted for DR if sovereign-grade encryption and enhanced audit active"
  validated_by: <actor_uuid>                 # compliance officer who validated equivalence
```

Compensating controls are the only mechanism that does not actually override the policy — it replaces the enforcement with equivalent protection. Not all policies have meaningful compensating controls (data residency laws cannot be compensated by encryption).

### 18.6 Severity Spectrum Summary

| Severity | Mechanism | When | Who | Can target hard? | Audit |
|----------|-----------|------|-----|-----------------|-------|
| **Planned** | Override Policy | Known recurring exception | Policy author + reviewer | No — caught at activation | Full policy lifecycle |
| **Pre-authorized** | Exception Grant | Known upcoming need | Dual-approval authority | Yes — with dual-approval + compensating controls | Grant record + usage tracking |
| **Immediate** | Manual Override | Blocked request, needs to proceed now | Override authority | Yes — with dual-approval | Override record + justification |
| **Structural** | Compensating Control | Policy can be met differently | Policy author + compliance | N/A — policy is satisfied, not overridden | Substitute control record |
| **Modifier** | Dual-Approval | Any override of hard policy | Two individuals, different roles | Required | Both approver records |

### 18.7 Override Audit

Every override produces its own Merkle tree leaf:

```yaml
audit_leaf:
  stage: policy_override
  source: "override/payments-team-zone-c-exception"  # or exception_grant/manual_override UUID
  source_type: override_policy | exception_grant | manual_override | compensating_control
  override_target: "sovereignty/eu-data-residency"
  override_effect: relax
  authorized_by: <actor_uuid>
  approved_by: <actor_uuid | null>
  dual_approval: true | false
  compensating_controls: [...]
  justification: "..."
  input_payload_hash: <sha-256>
  output_payload_hash: <sha-256>
  before_context_hash: <sha-256>
  after_context_hash: <sha-256>
  signature: <ed25519>
```

An auditor asking "why did this request bypass sovereignty?" gets the complete answer: which override mechanism was used, who authorized it, what compensating controls were active, and the cryptographic proof that the override was properly authorized.

### 18.8 Policy Block Resolution

When a policy blocks a request and no automatic resolution exists, DCM does not silently enter an override queue. The consumer is notified with actionable guidance: what blocked the request, why, and what their options are to resolve it.

**Pipeline behavior when a policy blocks a request:**

```
Policy Engine evaluates request
  → Policy blocks request
  → Policy Engine checks automatic resolution:
      1. Active Override Policy covering this scope? → Apply, continue pipeline
      2. Active Exception Grant covering this scope? → Apply, continue pipeline
      3. Active Compensating Control covering this scope? → Substitute, continue pipeline
  → No automatic resolution available:
      4. Request enters POLICY_BLOCKED status
      5. Policy Engine builds resolution guidance (what blocked, why, options)
      6. request.policy_blocked event published with guidance
      7. Consumer notified with blocking details and resolution options
      8. Consumer chooses a resolution action
      9. Pipeline proceeds based on chosen action
```

**Resolution options presented to the consumer:**

| Option | Action | What happens |
|--------|--------|-------------|
| **Modify request** | Consumer changes the blocked fields to be compliant | Request re-enters pipeline from assembly with updated fields. All policies re-evaluate. |
| **Request override** | Consumer requests an override with justification | Request enters PENDING_OVERRIDE. Override approval flow begins (§18.9). |
| **Cancel request** | Consumer abandons the request | Request moves to CANCELLED. Audit trail records cancellation with blocking context. |
| **Escalate** | Consumer requests review by the responsible policy domain owner | Notification routed to the role responsible for the blocking policy domain (e.g., sovereignty admin, security admin, cost admin) with full context. The domain owner can modify policies, register exception grant, or advise consumer. Routing is configurable per policy domain and profile. |

**Resolution guidance (built by Policy Engine):**

```yaml
policy_block_resolution:
  request_uuid: <uuid>
  status: POLICY_BLOCKED
  blocking_details:
    - policy_handle: "sovereignty/eu-data-residency"
      enforcement: hard
      reason: "Zone eu-west-3 not in allowed zones [eu-west-1, eu-central-1]"
      blocking_fields:
        - field: placement.zone
          current_value: "eu-west-3"
          allowed_values: ["eu-west-1", "eu-central-1"]

  resolution_options:
    modify:
      available: true
      guidance:
        - field: placement.zone
          suggestion: "Change to eu-west-1 or eu-central-1 to comply with data residency policy"
          compliant_values: ["eu-west-1", "eu-central-1"]
    request_override:
      available: true                        # false if profile prohibits consumer-initiated overrides
      requires: dual_approval                # derived from enforcement level and profile
      eligible_approver_roles: [security_officer, operations_lead]
    cancel:
      available: true                        # always available
    escalate:
      available: true
      routes_to: [platform_admin]

  timeout_at: <ISO 8601>                     # how long the request stays in POLICY_BLOCKED before auto-cancel
```

DCM builds the `compliant_values` guidance from the blocking policy's constraint output. If the sovereignty policy says `allowed_zones: [eu-west-1, eu-central-1]`, DCM includes those as the suggestion. If a GateKeeper says `max_cpu: 32` and the request asked for 64, DCM suggests values ≤ 32. For complex constraints (multi-policy interactions), DCM provides what it can determine and indicates when manual review is needed.

**Consumer actions via API:**

```
# View blocking details and resolution options
GET /api/v1/requests/{request_uuid}/resolution

# Modify and resubmit blocked request
POST /api/v1/requests/{request_uuid}:resolve
Body: {
  action: "modify",
  modifications: { "placement.zone": "eu-west-1" }
}

# Request override (enters override approval flow)
POST /api/v1/requests/{request_uuid}:resolve
Body: {
  action: "request_override",
  justification: "DR scenario — zone-a unavailable",
  compensating_controls: ["audit/enhanced-logging"]
}

# Cancel blocked request
POST /api/v1/requests/{request_uuid}:resolve
Body: { action: "cancel" }

# Escalate to responsible policy domain owner
POST /api/v1/requests/{request_uuid}:resolve
Body: {
  action: "escalate",
  context: "Need guidance on zone placement for DR scenario"
}
```

**Events:**

| Event | Published when | Payload |
|-------|---------------|---------|
| `request.policy_blocked` | Pipeline blocked, no automatic resolution | request_uuid, blocking_details, resolution_options, timeout_at |
| `request.resolution_chosen` | Consumer selects a resolution action | request_uuid, action (modify/override/cancel/escalate) |
| `request.modified_resubmit` | Consumer modifies and resubmits | request_uuid, modified_fields, re-enters pipeline |
| `override.requested` | Consumer chooses request_override | request_uuid, justification, enters override approval flow |
| `override.first_approval` | First approver acts (dual-approval flow) | override_request_uuid, approver, awaiting second approval |
| `override.approved` | All required approvals received | override_request_uuid, approvers, compensating_controls |
| `override.rejected` | Approver explicitly rejects | override_request_uuid, rejector, reason |
| `override.expired` | Timeout reached with no decision | override_request_uuid, timeout_at |

### 18.9 Override Approval Flow

When the consumer chooses "request override," the request moves from `POLICY_BLOCKED` to `PENDING_OVERRIDE` and the approval flow begins. DCM provides the approval gate, the audit trail, and the API. The organization provides the deliberation process.

**Override request record:**

```yaml
override_request:
  override_request_uuid: <uuid>
  request_uuid: <uuid>
  blocking_policy_handle: "sovereignty/eu-data-residency"
  blocking_policy_enforcement: hard | soft
  blocking_reason: "Zone eu-west-3 not in allowed zones [eu-west-1, eu-central-1]"
  required_approval_type: single | dual
  eligible_approver_roles: [security_officer, operations_lead]
  consumer_justification: "DR scenario — zone-a unavailable"
  consumer_compensating_controls: ["audit/enhanced-logging"]
  status: pending | approved | rejected | expired
  timeout_at: <ISO 8601>
  created_at: <ISO 8601>
  first_approval:
    actor_uuid: <uuid>
    role: <role>
    justification: "Approved — DR scenario confirmed, enhanced logging active"
    approved_at: <ISO 8601>
  second_approval:
    actor_uuid: <uuid>
    role: <role>
    approved_at: <ISO 8601>
```

**Approver actions via Admin API:**

```
# Approve override
POST /api/v1/admin/overrides/{request_uuid}/approve
Body: { justification, compensating_controls[], role }

# Reject override
POST /api/v1/admin/overrides/{request_uuid}/reject
Body: { reason }

# Query pending overrides (approver dashboard)
GET /api/v1/admin/overrides?status=pending&role={role}

# Query override history
GET /api/v1/admin/overrides/{request_uuid}
```

**Notification routing (configurable per profile):**

```yaml
block_notification:
  # Consumer notification (always enabled)
  consumer:
    channels: [internal]                     # Consumer Portal shows blocked requests
    include_guidance: true                   # Include resolution options and compliant values

  # Override approver notification (when consumer requests override)
  override_approvers:
    channels:
      - type: internal                       # Consumer Portal approver dashboard
        enabled: true
      - type: webhook                        # External system integration
        url: "https://servicenow.example.com/api/dcm/override"
        enabled: true
      - type: webhook
        url: "https://slack.example.com/api/dcm/override"
        enabled: true
    routing:
      by_policy_domain:
        sovereignty: [security_officer, compliance_manager]
        platform: [operations_lead, platform_engineer]
        tenant: [tenant_admin]
      by_enforcement:
        hard: [security_officer, operations_lead]
        soft: [operations_lead]

  # Escalation notification
  escalation:
    routes_to: [platform_admin]
    channels: [internal, webhook]

  # Override approval escalation (no response within window)
  override_escalation:
    if_no_response_after: PT1H
    escalate_to: [platform_admin]
```

**Timeout behavior (profile-governed):**

| Profile | Block timeout (auto-cancel) | Override timeout | Override escalation |
|---------|---------------------------|-----------------|-------------------|
| `minimal` | PT48H | PT24H | PT12H |
| `dev` | PT48H | PT24H | PT12H |
| `standard` | PT8H | PT4H | PT2H |
| `prod` | PT8H | PT4H | PT1H |
| `fsi` | PT4H | PT1H | PT30M |
| `sovereign` | PT4H | PT1H | PT30M |

Block timeout: how long a `POLICY_BLOCKED` request waits for any consumer action before auto-cancelling. Override timeout: how long a `PENDING_OVERRIDE` request waits for approver action. Both are configurable per profile.

**Pipeline resume behavior:**

When the consumer modifies and resubmits, the request re-enters the pipeline from assembly. Policies re-evaluate against the modified fields. The modification is recorded as a Merkle tree audit leaf.

When an override is approved, the pipeline resumes from the exact stage where it was blocked. The assembled payload, earlier policy evaluations, and Evaluation Context are preserved. The approved override is injected into the Evaluation Context as a constraint modification before the blocked policy re-evaluates.

Both paths produce audit leaves:
- Modify path: modification leaf (what changed) + full re-evaluation leaves
- Override path: override approval leaf (§18.7) + re-evaluation leaf

---

## 19. Policy Composition

Policies compose through four mechanisms:

**Domain precedence** (Section 4) — more-specific domains override less-specific:
```
System policy (GateKeeper: cpu_count max 64)
  └── Platform policy (GateKeeper: prod VMs require manager approval)
        └── Tenant policy (GateKeeper: payments team max cpu_count 32)
              └── Resource-type policy (Transformation: inject monitoring)
```

**Evaluation Context** (Section 7) — policies inform each other through constraints and hints. Sovereignty emits zone restrictions; tier distribution reads them and adjusts. Conflicts are detected and resolved automatically or escalated.

**Policy Groups** — Data artifacts that group related policies by concern_type. Profiles activate Policy Groups. "Apply the HIPAA profile" activates the HIPAA compliance domain's Policy Group.

**Override Model** (Section 18) — Override policies, exception grants, manual overrides, compensating controls, and dual-approval provide governed mechanisms for exceptions. Every override is auditable and time-bounded.

For a single request, all active matching policies at all domain levels evaluate across multiple passes if needed. Active overrides modify the evaluation: an override policy relaxes or tightens a specific policy's effect; an exception grant temporarily suspends a policy for a scoped set of requests; a manual override suspends a policy for one request. Overrides participate in the Evaluation Context — downstream policies see the override's effect.

---

## 20. Related Policies

| Policy | Rule |
|--------|------|
| `POL-001` | All DCM policy types implement the unified base contract. The output schema is the only thing that varies. |
| `POL-002` | Every policy evaluation produces an audit record. No evaluation is silent. |
| `POL-003` | Hard enforcement policies require dual-approval to override. Override policies (Model 1) cannot target hard policies — caught at activation. |
| `POL-004` | Policies in `proposed` status execute in shadow mode — output is captured and never applied. Shadow mode is the primary mechanism for safe policy change management. |
| `POL-005` | The Policy Engine is the sole evaluator of all policies. No component bypasses the Policy Engine to enforce rules directly. |
| `POL-006` | Adding a new policy type requires defining a new output schema. The base contract, evaluation algorithm, lifecycle, and audit obligations are inherited. |
| `POL-007` | Policies ARE the orchestration. Pipeline steps are Policies firing on payload type events. Static flows are Orchestration Flow Policies with `ordered: true`. |
| `POL-008` | Every override produces a Merkle tree audit leaf. Override justification, authorizer identity, compensating controls, and the overridden policy are captured. |
| `POL-009` | Exception Grants and Manual Overrides must have expiry dates. Permanent overrides are not permitted — use an Override Policy with a review cycle instead. |
| `POL-010` | Compensating controls must be validated by a compliance officer role before activation. Self-validation is not permitted. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
