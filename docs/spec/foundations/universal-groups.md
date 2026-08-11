# UDLM — Universal Group Model

> **Machine-validatable schema:** `Grouping` records validate against
> `registry/profile.schema.json` (profiles) / the `Grouping` class (groupings)
> (`registry/tools/validate.py` dispatches on `record_type` to it).

**Related Documents:** [Context and Purpose](context-and-purpose.md) | [Resource Grouping](resource-grouping.md) | [Entity Relationships](entity-relationships.md)

> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](foundations.md).
>
> The Data abstraction — grouping as universal grouping artifact

---

## 1. Purpose

The **Universal Group Model** expresses every grouping need — tenancy, resource groups, policy groups and profiles, layer domains, activation scopes, cross-tenant authorization — as a single `grouping` entity distinguished by the grouping record kind metadata. One mental model. One API. One registry. The same UUID, versioning, lifecycle, policy targeting, and audit trail apply to every group regardless of its class, and a natural organizational structure ("everything related to Payments") is one construct, not eight.

**The model:**
- Every grouping construct is one `Grouping` record; per-class APIs are class-filtered views of the one group store
- Structural invariants are per-class (one Tenant per resource, no constituent cross-tenant, etc.)
- Policy enforcement is governed by the active Profile, not per-group configuration
- `tenant_boundary` groups carry the hard-tenancy isolation guarantees

---

## 2. The grouping Entity

### 2.1 Universal Structure

```yaml
dcm_group:
  artifact_metadata:
    uuid: <uuid — immutable, assigned at creation>
    handle: <domain/class/name — e.g., org/tenant/payments-bu>
    version: <Major.Minor.Revision>
    status: <developing|proposed|active|deprecated|retired>
    created_by: <standard actor record>
    owned_by: <standard actor record>
    created_via: <pr|api|migration|system>
    modifications: <append-only history>

  # IDENTITY
  name: <human-readable name>
  description: <human-readable purpose>
  concern_tags: [payments, pci-scope, eu-west]  # free tagging — discoverability

  # WHAT KIND OF GROUP
  record kind: <see Section 2.2>
  group_subclass: <user-defined semantic label — advisory only, no system behavior>
  # group_subclass examples: cost_center, business_unit, compliance_scope, project

  # MEMBERSHIP
  member_types_permitted: [resource_entity, policy, layer, group, tenant]
  # Determines what can be a member of this group
  # Single-type groups declare one type (e.g., [policy] for policy_collection)
  # Composite groups declare multiple types

  exclusivity:
    per_member: <one | many>
    # one:  a member can belong to only one group of this class at a time
    # many: a member can belong to multiple groups of this class simultaneously
    per_group: <unlimited | capped>
    cap: <integer — if capped; e.g., license seat limits>

  members:
    - member_uuid: <uuid>
      member_type: <resource_entity|policy|layer|group|tenant|provider>
      member_role: <semantic label — e.g., compute, compliance_governance>
      added_at: <ISO 8601>
      added_by: <actor record>
      valid_from: <ISO 8601 — null = immediately>
      expires_at: <ISO 8601 — null = indefinite; time-bounded membership>
      membership_status: <active|suspended|expired>

  # BEHAVIOR
  enforcement_model: <advisory|enforced|mandatory>
  # advisory:   group is a tag — no system behavior enforced by the control plane
  # enforced:   group drives policy scoping and system behavior
  # mandatory:  group membership is non-optional (structural requirement)
  # NOTE: For tenant_boundary groups, enforcement_model is profile-governed
  # — the active Profile sets the enforcement floor, not per-group configuration

  cross_boundary:
    tenant_spanning: <false|permitted|required>
    sovereignty_spanning: <false|permitted|required>

  lifecycle_coupling:
    on_group_destroy: <detach|cascade|notify|retain>
    # detach (DEFAULT): destroying the group releases memberships but
    #                   does NOT destroy members
    # cascade: destroying the group destroys all members
    # notify:  destroying the group notifies owners and waits for confirmation
    # retain:  group cannot be destroyed while it has members
    on_member_destroy: <remove_from_group|retain_membership_record|notify>

  # INHERITANCE AND COMPOSITION
  extends: <group_uuid — inherits all members and behavior from parent group>
  includes_groups:
    - group_uuid: <uuid — pull in another group's members>
      member_type_filter: [resource_entity]  # optional — only include this type
      # If omitted: all member types from the included group are pulled in

  # NESTING (for tenant_boundary groups)
  parent_group_uuid: <uuid — if this group is nested within a parent group>
  child_groups: [<uuid>, ...]  # populated by the control plane — do not set manually

  # POLICY TARGETING
  # Any policy can target this group by UUID or handle — no special declaration
  # Policy targeting a composite group applies to all member types by default
  # Policy can narrow with: member_type_filter: [resource_entity]
```

### 2.2 Group Classes

**What kind a grouping is, is its `resource_type`.** Kinds that add something are type classes under
the `Grouping` base; kinds that add nothing are that base, instantiated. No separate discriminator is
stored, because the type name already answers the question (DRV-001).

| Kind | Is | member_types_permitted | exclusivity.per_member | enforcement_model |
|---|---|---|---|---|
| tenant | **`Grouping.Tenant`** | resource_entity, group | one (structural lock) | profile-governed |
| cross-tenant authorization | **`Grouping.Authorization`** | resource_entity | many | enforced |
| resource grouping | plain `Grouping` | resource_entity | many | advisory |
| policy collection | plain `Grouping` | policy | many | enforced |
| policy profile | plain `Grouping` | group (policy collections only) | many | enforced |
| layer grouping | plain `Grouping` | layer | many | enforced |
| provider grouping | plain `Grouping` | provider | many | advisory |
| federation | **parked** — see §3.6 | group (tenants) | many | advisory |
| composite | **retired** — it is a Template, see §3.5 | — | — | — |

A kind earns a type class only if it **adds** something. Tenant adds nesting and a required isolation
obligation; Authorization adds who granted, who received, what may be done, and until when. The five
plain groupings differ from each other in nothing but the three settings above, which is why they are
one class and not five.

> **Open — the three settings have no home in the model.** `member_types_permitted`,
> `exclusivity.per_member`, and `enforcement_model` are declared in this table and nowhere a machine
> can read them. Two candidates, neither obviously right: type-spec-level fields (the
> `ownership_model` precedent), or elements each type class narrows to a constant — which would put
> fully derivable data on every instance. Tracked; not settled in passing.

**Reading the rest of this document.** `tenant_boundary` is used throughout — including in the
structural invariants below — as the descriptive name for the kind now carried by `Grouping.Tenant`.
It names a kind; it is no longer how an instance declares itself. The `dcm_group:` wrapper in the
illustrative YAML likewise names a shape rather than a schema.


The `cross_tenant_authorization` class is the formal grant by which one Tenant authorizes
another to reference, allocate from, or stake its resources (§13; lifecycle also detailed in
[Resource Grouping](resource-grouping.md) §10). Its members are the authorized
resource entities; a resource may appear in many authorizations (`per_member: many`), and the
class is `enforced` — CTX-001 gates cross-tenant relationships on an active authorization.

### 2.3 Structural Invariants — Non-Overridable

Regardless of `enforcement_model`, grouping kind, or active profile, the following structural invariants always hold:

| Invariant | Applies To | Rule |
|-----------|-----------|------|
| `GRP-INV-001` | `tenant_boundary` | A resource_entity may belong to exactly one active tenant_boundary group |
| `GRP-INV-002` | `tenant_boundary` | Constituent relationships may not cross tenant_boundary group boundaries |
| `GRP-INV-003` | `tenant_boundary` | Destroying a parent tenant_boundary group requires explicit resolution of all child groups first — no silent cascade |
| `GRP-INV-004` | `tenant_boundary` | A resource in a child tenant_boundary group belongs to the child — never the parent |
| `GRP-INV-005` | All | Circular group membership is invalid |
| `GRP-INV-006` | All | A group cannot be a member of itself |

---

## 3. Group Class Reference

### 3.1 tenant — `Grouping.Tenant`

**Purpose:** Ownership boundary, isolation enforcement, cost attribution, audit scope, sovereignty boundary

```yaml
dcm_group:
  resource_type: Grouping
  member_types_permitted: [resource_entity, group]
  exclusivity:
    per_member: one   # STRUCTURAL LOCK — cannot be changed by policy
  enforcement_model: mandatory   # set by active Profile — not configurable per-group
  cross_boundary:
    tenant_spanning: false   # STRUCTURAL LOCK
  lifecycle_coupling:
    on_group_destroy: notify   # requires explicit resolution
    on_member_destroy: remove_from_group

  # Tenant-specific fields preserved from original model
  tenant_config:
    hard_tenancy:
      cross_tenant_relationships: explicit_only
    active_profile: system/profile/standard
    minimum_child_profile: null
```

**Profile-governed enforcement:**
- `homelab` profile → `enforcement_model: advisory` (tenancy optional)
- `dev` profile → `enforcement_model: enforced` (tenancy recommended)
- `standard` and above → `enforcement_model: mandatory` (tenancy required)

### 3.2 resource grouping — a plain `Grouping`

**Purpose:** Flexible composable grouping of resource entities — structured tagging

```yaml
dcm_group:
  resource_type: Grouping
  group_subclass: cost_center   # advisory — CostCenter, BusinessUnit, Project, Team...
  member_types_permitted: [resource_entity]
  exclusivity:
    per_member: many   # a resource can be in multiple resource groups
  enforcement_model: advisory
```

### 3.3 policy collection — a plain `Grouping`

**Purpose:** Cohesive collection of policies addressing a single concern

```yaml
dcm_group:
  record kind: policy_collection
  concern_tags: [pci-dss, encryption, network-segmentation]
  member_types_permitted: [policy]
  enforcement_model: enforced
  # Source — local or External Policy Evaluator
  source:
    type: <local|external_policy_evaluation>
    provider_uuid: <uuid — if external_policy_evaluation>
    on_provider_update: <proposed|active>
```

### 3.4 policy profile — a plain `Grouping`

**Purpose:** Complete control-plane configuration for a use case, composed of policy_collection groups

```yaml
dcm_group:
  record_type: profile
  member_types_permitted: [group]   # only policy_collection groups
  extends: <parent profile uuid>    # inherits all parent's groups
  enforcement_model: enforced
```

### 3.5 composite — retired

**A composite group is a Template.** A set of parts, each with a declared role, ordered as one unit
and meant to be reused — that is what a Template is, and it is modelled as one. Building it here as
well would model one concept twice in two documents.

The tell was structural rather than a matter of taste: a composite group specifies a **stored member
list with a role per member** (`member_role: compute`). A grouping does not have a member list — its
membership is worked out from a rule every time it is asked, so that it can never drift from reality.
There is nowhere to hang a per-member role, and adding one would undo the property derived membership
exists for. A Template *declares* its parts; a grouping *derives* its members. Only one of those was
ever going to fit.

Note this does not touch the derived `has_constituents` **shape** — a different use of the word
"composite", and unaffected.

### 3.6 federation — parked

> **Not buildable as specified.** Like the retired composite above, a federation declares a **stored
> member list with a role per member** (`member_role: shared_governance`), and a grouping derives its
> members from a rule instead. Unlike composite, a federation is *not* obviously a Template — a set of
> independent tenants sharing governance is a real and different idea — so this needs a decision
> rather than a deletion.
>
> Three ways out: the role is derived from the member's own data; the roles are dropped and a
> federation is a plain grouping of tenants; or it keeps a member list and is something other than a
> grouping. Until one is chosen, the description below records the intent and not a buildable shape.
> §5 (Federated Tenants) rests on this section and is parked with it.


**New concept:** A group of tenant_boundary groups that share governance, visibility, and resources while maintaining complete independence.

```yaml
dcm_group:
  record kind: federation
  name: "Global FSI Federation"
  member_types_permitted: [group]   # tenant_boundary groups only
  enforcement_model: advisory       # federation cannot override member Tenant isolation

  members:
    - member_uuid: <subsidiary-a-tenant-uuid>
      member_type: group
      member_role: member_tenant
    - member_uuid: <subsidiary-b-tenant-uuid>
      member_type: group
      member_role: member_tenant
    - member_uuid: <shared-compliance-policy-group-uuid>
      member_type: group
      member_role: shared_governance

  federation_config:
    shared_policy_inheritance: <opt_in|opt_out>
    # opt_in:  member Tenants must explicitly adopt shared policies
    # opt_out: shared policies apply to all members unless explicitly excluded
    cross_member_visibility: <none|audit_only|full>
    consolidated_reporting: true
```

---

## 4. Nested Tenants

### 4.1 Concept

A **Nested Tenant** is a `tenant_boundary` group that is a member of a parent `tenant_boundary` group. The child Tenant maintains complete isolation — its resources belong to it, not the parent. The parent Tenant has governance overlay, cost rollup authority, and audit aggregation across all children.

```
corporate_tenant (tenant_boundary)
  │  child_groups:
  ├── business_unit_a_tenant (tenant_boundary)
  │     └── resources, policies, layers owned by BU-A
  └── business_unit_b_tenant (tenant_boundary)
        └── resources, policies, layers owned by BU-B
```

### 4.2 Structural Invariants for Nested Tenants

- A resource belongs to the **leaf** tenant_boundary group — never the parent (GRP-INV-004)
- Parent Tenant has **governance overlay** — not ownership
- Parent Tenant destruction requires all child Tenants to be resolved first (GRP-INV-003)
- Constituent relationships cannot cross any tenant_boundary boundary — including parent-child (GRP-INV-002)

### 4.3 Policy Inheritance Direction

Policy inheritance from parent to child Tenant is profile-governed:

| Profile | Default | Meaning |
|---------|---------|---------|
| `homelab`, `dev` | `opt_in` | Child Tenants must explicitly adopt parent policies |
| `standard`, `prod` | `opt_out` | Parent policies cascade to children unless child excludes |
| `fsi`, `sovereign` | `opt_in` | Nothing crosses without consent |

```yaml
nested_tenant_config:
  parent_group_uuid: <corporate-tenant-uuid>
  policy_inheritance: opt_out   # governed by active Profile
  parent_policy_exclusions:
    - policy_uuid: <uuid>   # explicitly excluded from cascading to this child
  cost_rollup_to_parent: true
  audit_visible_to_parent: true
  sovereign_boundary: independent   # child sovereignty independent of parent
```

### 4.4 Nested Tenant Use Cases

- **Enterprise structure:** Corporate → Business Unit → Team Tenants
- **Multi-region deployment:** Global Tenant → Regional Tenants → Zone Tenants
- **Multi-tier compliance:** Organization Tenant → PCI-scope Tenant → Payment-processing Tenant
- **Partner/customer isolation:** Platform Tenant → Customer A Tenant → Customer B Tenant

---

## 5. Federated Tenants

> **Parked with §3.6.** Everything below describes the intent of a federation, not a shape the model
> can currently carry — a federation's per-member roles need a member list, and a grouping derives its
> members from a rule.

### 5.1 Concept

A **Federated Tenant** structure is a `federation` group containing multiple independent `tenant_boundary` groups. Member Tenants maintain complete independence — the federation provides shared governance, consolidated visibility, and mutual cross-tenant authorization within the federation scope.

### 5.2 Federation Capabilities

- **Shared policy application:** `policy_collection` groups included in the federation apply to all member Tenants (per `shared_policy_inheritance` setting)
- **Cross-member visibility:** federation members can declare mutual `cross_tenant_authorization` scoped to federation membership — without requiring separate bilateral authorizations
- **Consolidated reporting:** cost, audit, and observability queries scoped to the federation group return aggregated results across all member Tenants
- **Federation-level governance:** policies targeting the federation group apply to all member Tenants

### 5.3 Federation vs Nesting

| Dimension | Nested Tenants | Federated Tenants |
|-----------|---------------|-----------------|
| Relationship | Parent-child hierarchy | Peer membership |
| Governance direction | Top-down from parent | Shared among peers |
| Independence | Child subordinate to parent | Members fully independent |
| Cost rollup | Mandatory to parent | Configurable |
| Use case | Enterprise hierarchy | Multi-organization collaboration |

---

## 6. Group Registry and API

### 6.1 Universal Registry

All groups are stored in a single **Group Registry** — a lifecycle store bound by contract, not technology ([data-model-core](data-model-core.md) §6 [D1]; git is the conforming homelab-profile carrier). The registry is queryable by any combination of fields.

### 6.2 Class-Filtered API Views

The universal registry exposes class-filtered views for convenience:

| Endpoint | Equivalent Query |
|----------|----------------|
| `GET /tenants` | `GET /groups?record kind=tenant_boundary` |
| `GET /resource-groups` | `GET /groups?record kind=resource_grouping` |
| `GET /policy-groups` | `GET /groups?record kind=policy_collection` |
| `GET /policy-profiles` | `GET /groups?record kind=policy_profile` |
| `GET /federations` | `GET /groups?record kind=federation` |

Existing API references continue to work unchanged. New API consumers can use the universal endpoint.

---

## 8. System Policies

The structural invariants `GRP-INV-001`..`GRP-INV-006` are **defined once in §2.3** (every
GRP-* id has exactly one definition — this includes [Resource Grouping](resource-grouping.md),
whose former GRP-003 circular-nesting rule is now a pointer to `GRP-INV-005` here). The
policies below add behavior on top of those invariants:

| Policy | Rule |
|--------|------|
| `GRP-007` | Composite group `on_group_destroy` default is `detach` — destroying a group releases memberships but does not destroy members |
| `GRP-008` | Policies targeting a composite group apply to all member types by default; `member_type_filter` narrows scope |
| `GRP-009` | Federation groups cannot override member Tenant isolation boundaries |
| `GRP-010` | Nested Tenant policy inheritance direction is governed by the active Profile — not per-group configuration |

---

## 9. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should composite group policy targeting emit a linting warning when no member_type_filter is declared? | Operational safety | ✅ Resolved — linting warning (not error) when composite policy targeting has no member_type filter; suppress with explicit_no_filter: true (GRP-016) |
| 2 | Should there be a maximum nesting depth for tenant_boundary groups? | Operational governance | ✅ Resolved — Maximum nesting depth is profile-governed: standard/prod = 5 levels; fsi/sovereign = 3 levels. Deeper nesting creates policy inheritance complexity and audit graph depth issues. Enforced at group creation time. |
| 3 | How does group membership interact with the Search Index? | Performance | ✅ Resolved — Group membership is indexed in the Search Index as a field on each entity record (member_of_groups: [uuid, ...]). The Search Index supports querying by group_uuid. Group membership changes trigger an incremental index update (not full rebuild). Staleness follows the standard Search Index model (PT5M standard profile). |
| 4 | Should time-bounded memberships (expires_at) trigger notifications before expiry? | Consumer experience | ✅ Resolved — warn_before_expiry field on membership (GRP-014) |

---

## 9a. Grouping and Relationship Gap Resolutions

### 9a.1 Community Subclass Catalog (Q35)

The grouping vocabulary is closed — system behavior is tied to declared classes only. `group_subclass` is open and advisory. The control plane maintains a community subclass catalog as a non-authoritative reference shipped with the well-known Information Provider Registry:

```yaml
# Community subclass catalog (advisory — not enforced, not validated)
common_group_subclasses:
  resource_grouping:
    - subclass: cost_center
      description: "Financial cost attribution grouping"
    - subclass: business_unit
      description: "Organizational business unit"
    - subclass: project
      description: "Project-scoped resource collection"
    - subclass: environment
      description: "Environment grouping (prod/staging/dev)"
    - subclass: application
      description: "Application component grouping"
  policy_collection:
    - subclass: compliance_framework
      description: "Policies implementing a compliance framework"
    - subclass: technology_baseline
      description: "Technology-specific policy baseline"
```

Organizations freely declare subclasses not in the catalog — there is no validation or enforcement on subclass values.

### 9a.2 Group Sovereignty Interaction (Q36)

Sovereignty interaction is record kind-specific:

| record kind | Cross-Sovereignty | Notes |
|-------------|-----------------|-------|
| `tenant_boundary` | **Never** | Structural — not configurable |
| `resource_grouping` | Permitted by default | Policy may restrict for classified resources |
| `policy_collection` | Always permitted | Policies have no sovereignty — governance artifacts |
| `layer_grouping` | Always permitted | Layers have no sovereignty |
| `composite` | Governed by most restrictive member | If contains cross-sovereignty resources, resource rules apply |
| `federation` | Permitted with the control plane federation rules | control-plane-003 governs data flows |

```yaml
# Policy restricting cross-sovereignty resource group membership
policy:
  type: validation
  enforcement_class: compliance
  rule: >
    If group.record kind == resource_grouping
    AND member.classification_level IN [confidential, restricted]
    AND member.sovereignty_zone != group.primary_sovereignty_zone
    THEN gate: "Classified resources cannot join cross-sovereignty resource groups"
```

### 9a.3 Tenant Decommission Lifecycle (Q37)

Tenant decommission is the highest-stakes lifecycle operation in the control plane. It requires mandatory pre-decommission validation and follows a staged sequence.

**Phase 1 — Pre-decommission validation (blocking):**
- All resources in decommissionable state (not PROVISIONING or active incidents)
- Cross-tenant operational relationships accounted for (consuming Tenants notified)
- Allocated resources claimed by other Tenants addressed (returned or migrated)
- Active rehydration leases released
- Compliance holds reviewed (HIPAA/PCI records may need archival)
- Child tenant_boundary groups resolved first (GRP-INV-003)

**Phase 2 — Resource decommission (per lifecycle policy):**
```
For each resource in the Tenant:
  cascade → decommission resource (default for tenant_boundary)
  retain  → resource enters ORPHANED state (operator must rehome or destroy)
  notify  → alert owner; resource enters PENDING_DECOMMISSION
```

**Phase 3 — Group membership cleanup:**
- Remove Tenant from all group memberships
- Empty federation groups enter EMPTY state
- Orphaned child groups must have been resolved in Phase 1

**Phase 4 — Audit record archival:**
All audit records enter `all_retired` retention_status. They are **never destroyed** as part of Tenant decommission. Post-lifecycle retention clock starts per governing policy.

### 9a.4 Time-Bounded Group Membership (Q38)

Group memberships already support time-bounded validity via `valid_from` and `expires_at` in the Universal Group Model. The Lifecycle Constraint Enforcer handles expiry.

```yaml
member:
  member_uuid: <uuid>
  member_type: resource_entity
  valid_from: "2026-01-01T00:00:00Z"
  expires_at: "2026-12-31T23:59:59Z"
  membership_status: <active|suspended|expired>
  on_expiry: <remove|notify|suspend_member>
  # remove:         member silently removed from group on expiry
  # notify:         notify group owner; member remains with expired status (default)
  # suspend_member: transition the member entity to SUSPENDED state
  warn_before_expiry: P7D          # notify 7 days before expiry
```

Membership expiry produces a `MEMBERSHIP_EXPIRE` audit record (event
`group.membership_expired` — [event catalog](../contracts/event-catalog.md)) with
`reason: membership_ttl_expired`. `MEMBER_REMOVE` is emitted **only** when a member is
actually removed — i.e. the `remove` on_expiry action additionally produces a
`MEMBER_REMOVE` record; `notify` and `suspend_member` emit the expire event alone (the
membership persists with `membership_status: expired` / the member is suspended, nothing is
removed).

### 9a.5 Group Policy Inheritance — Nested Groups (Q39)

Policy inheritance for nested groups is record kind-specific and profile-governed:

| record kind | Default | Profile Override |
|-------------|---------|----------------|
| `tenant_boundary` | `opt_out` (parent cascades unless child excludes) | `opt_in` for homelab/dev/fsi/sovereign |
| `resource_grouping` | Not applicable | Resource groups are tags — policies target them, not inherit through them |
| `policy_collection` | Not applicable | Policy collections use `extends` for inheritance |
| `composite` | `opt_out` | Configurable per group |
| `federation` | `opt_in` | Peer consent always required — not configurable |

```yaml
# Nested group policy inheritance declaration
dcm_group:
  resource_type: Grouping
  parent_group_uuid: <corporate-tenant-uuid>
  policy_inheritance: opt_out     # governed by active Profile
  parent_policy_exclusions:
    - policy_uuid: <uuid>         # explicitly excluded from cascading to this child
```

---

## 10. System Policies — Grouping Gaps

| Policy | Rule |
|--------|------|
| `GRP-011` | The record kind set is closed — system behavior is tied to declared classes only. group_subclass is open and advisory. The control plane maintains a community subclass catalog as a non-authoritative reference. No validation or enforcement on subclass values. |
| `GRP-012` | Sovereignty interaction is record kind-specific. tenant_boundary groups never span sovereignty boundaries (structural). resource_grouping groups may span sovereignty boundaries by default — policy may restrict for classified resources. policy_collection and layer_grouping groups always permitted cross-sovereignty. composite groups are governed by the sovereignty rules of their most restrictive member type. |
| `GRP-013` | Tenant decommission requires pre-decommission validation (resource state, cross-tenant relationships, compliance holds, child group resolution). Resources follow declared lifecycle policy. Child tenant_boundary groups must be resolved before parent decommission. Audit records enter post-lifecycle retention — never destroyed as part of Tenant decommission. |
| `GRP-014` | Group memberships support time-bounded validity via valid_from and expires_at. Membership expiry is enforced by the Lifecycle Constraint Enforcer. Expiry produces a MEMBERSHIP_EXPIRE audit record (event group.membership_expired); MEMBER_REMOVE is additionally produced only by the `remove` on_expiry action, when the member is actually removed. on_expiry action (remove, notify, suspend_member) declared per membership. Default: notify. |
| `GRP-015` | Group policy inheritance is record kind-specific and profile-governed. tenant_boundary: opt_out (standard/prod) or opt_in (homelab/dev/fsi/sovereign). federation: always opt_in — peer consent required. composite: opt_out by default. resource_grouping and policy_collection: not applicable. |

## 11. Related Concepts

- **[resource-grouping.md](resource-grouping.md)** — original resource grouping model, now implemented via `resource_type: Grouping`
- **Policy Organization** (now the policy-contract / policy-groups model) — Policy Groups and Profiles, now implemented via `record kind: policy_collection` and `record_type: profile`
- **[entity-relationships.md](entity-relationships.md)** — cross-tenant authorized relationships between groups
- **[universal-audit.md](../contracts/universal-audit.md)** — all group changes produce audit records
- **[ingestion-model.md](../lifecycle/ingestion-model.md)** — migration of existing constructs to universal groups

---

## 13. Cross-Tenant Authorization Lifecycle

### 13.1 What Cross-Tenant Authorizations Are

A `cross_tenant_authorization` is a grouping with `record kind: cross_tenant_authorization`. It is the formal mechanism by which one Tenant grants another Tenant permission to reference, allocate from, or stake a resource that belongs to the granting Tenant.

Without a cross-tenant authorization, entities in different Tenants cannot form relationships. The authorization is the bridge that enables cross-Tenant resource sharing while maintaining isolation.

### 13.2 Authorization Lifecycle

```yaml
cross_tenant_authorization:
  artifact_metadata:
    uuid: <uuid>
    handle: "org/cross-tenant-auth/networkops-to-appteam-vlan100"
    version: "1.0.0"
    status: active

  granting_tenant_uuid: <networkops-tenant-uuid>
  receiving_tenant_uuid: <appteam-tenant-uuid>
  authorized_resources:
    - resource_uuid: <vlan-100-uuid>
      permitted_operations: [stake, read]
    - resource_type: Network.IPAddress
      source_pool_uuid: <ippool-uuid>
      permitted_operations: [allocate]

  # Duration
  valid_from: <ISO 8601>
  expires_at: <ISO 8601|null>       # null = perpetual until revoked
  auto_renew: false

  # Who created this
  granted_by_actor_uuid: <uuid>
  granted_at: <ISO 8601>
```

### 13.3 Who Creates Cross-Tenant Authorizations

| Creator | Scenario | Authorization type |
|---------|---------|-------------------|
| Granting Tenant Admin | Standard: NetworkOps authorizes AppTeam to use VLAN-100 | explicit |
| Platform Admin | Emergency or platform-managed shared infrastructure | platform_managed |
| Pre-authorization policy | Policy automatically authorizes based on conditions | policy_auto |

### 13.4 Revocation and Its Consequences

When a cross-tenant authorization is revoked:

```
Authorization revoked (by granting Tenant admin, platform admin, or expiry)
  │
  ▼ All active allocations and stakes under this authorization are identified
  │
  ▼ For each active allocation / stake:
  │   Entity enters PENDING_REVIEW state
  │   pending_review_record created:
  │     trigger: cross_tenant_auth.revoked
  │     resolution_options: [re_authorize, release, migrate, escalate]
  │
  ▼ Notifications sent:
  │   Granting Tenant Admin
  │   Receiving Tenant Admin
  │   Each affected resource owner
  │   Platform Admin (if platform_managed authorization)
  │
  ▼ Resolution deadline: PT72H (configurable per profile)
  │
  └── On deadline: on_deadline_exceeded recovery policy fires
```

### 13.5 System Policies — Cross-Tenant Authorization

| Policy | Rule |
|--------|------|
| `CTX-001` | Cross-tenant relationships require an active cross-tenant authorization or a resource type declared publicly_stakeable / publicly_allocatable in its Resource Type Spec. |
| `CTX-002` | Cross-tenant authorization revocation places all active dependent entities in PENDING_REVIEW. Revocation does not immediately release allocations. |
| `CTX-003` | Cross-tenant authorization expiry is treated identically to explicit revocation. |
| `CTX-004` | Platform Admin may create cross-tenant authorizations on behalf of any Tenant. All platform-managed authorizations carry a platform_managed flag and are visible in the platform admin audit log. |
| `CTX-005` | The **required-grant set** for a request or catalog offering is DERIVED from its edge graph — each cross-tenant edge resolved to its target's owning Tenant and diffed against the requesting Tenant's active authorizations — and surfaced to the requesting Tenant **before admission**. A cross-tenant relationship whose authorization is missing is refused at request validation, never first discovered at dispatch. The set is computed, never stored (DRV-001). |
| `CTX-006` | **Structural release.** The existence of a cross-tenant edge, its relation and nature, its target's owning authority and resource type, and the grant's status are releasable to the requesting Tenant. The target's spec, configuration, and realized outputs are NOT. A tenant boundary governs what a subject may *do*, not what a subject may *know*; a profile may narrow what is released but may not withhold the existence of a required grant. |
| `CTX-007` | A cross-tenant act is audited to **both** the granting and the receiving Tenant. A `platform_managed` authorization (CTX-004) is visible to the Tenant on whose behalf it was created, not only to the platform administrator — a grant made in a Tenant's name is auditable by that Tenant. |
| `CTX-008` | A resource type declaring `publicly_stakeable` / `publicly_allocatable` satisfies CTX-001 as a **standing declaration**. The required-grant set reports it as *satisfied by standing declaration* rather than omitting it, so the relationship stays visible. The declaration waives the per-grant authorization, never the boundary: ownership, revocation, and decommission behave exactly as for a granted stake. |

**Conformance targets (ADR-066; the discipline is #419).** Each rule above names the class of product
it binds, and whether this repository can check it. A rule this repository cannot check is not
thereby unenforced — it is evidenced by a peer implementation, and saying so is the point.

- **CTX-005** — target **control-plane**. Not checkable here: the derivation is provable (a reference
  implementation over the edge graph, the #321 split), but the refusal *timing* is runtime. Blocked on
  #425 — the authorization record has no schema, so there is nothing to diff against.
- **CTX-006** — target **control-plane**. Not checkable here: a release decision taken at query and
  enforcement time (ADR-041 egress, structural surface).
- **CTX-007** — target **control-plane**. Not checkable here: an audit-routing behavior.
- **CTX-008** — target **udlm-artifact** *and* control-plane. The declaration's coherence **is** checked
  here — `publicly_stakeable` requires `ownership_model: shareable`, `publicly_allocatable` requires a
  pool (`registry/tools/validate.py` `check_ownership_declaration`, landed with OWN-007/OWN-008). Its
  *effect* on the required-grant set is control-plane.

This is the first rule family authored under the conformance-target discipline; the other rule
families are backfilled separately rather than retrofitted here.

---

*Document maintained by the control plane Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
