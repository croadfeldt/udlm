# DCM Data Model — Universal Group Model


**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Resource Grouping](08-resource-grouping.md) | [Entity Relationships](09-entity-relationships.md) | [Policy Organization](14-policy-profiles.md)

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
> The Data abstraction — DCMGroup as universal grouping artifact



---

## 1. Purpose

DCM previously used eight distinct grouping constructs — Tenant, Resource Groups, Custom Resource Groups, Policy Groups, Policy Profiles, Layer Domain, Activation Scope, and Cross-Tenant Authorization. Each had its own structure, its own API, its own documentation, and its own membership model. This fragmentation created cognitive overhead for operators and prevented natural organizational structures (such as "everything related to Payments") from being expressed as a single construct.

The **Universal Group Model** collapses all grouping into a single `DCMGroup` entity distinguished by `group_class` metadata. One mental model. One API. One registry. The same UUID, versioning, lifecycle, policy targeting, and audit trail apply to every group regardless of its class.

**What changes:**
- All grouping constructs become `group_class` values on `DCMGroup`
- Existing UUIDs, handles, and API references are preserved
- Existing APIs become class-filtered views of the universal group store
- Migration is additive — no breaking changes

**What does NOT change:**
- The structural invariants of each construct (one Tenant per resource, no constituent cross-tenant, etc.)
- Policy enforcement behavior — governed by the active Profile, not per-group configuration
- The hard-tenancy model — tenant_boundary groups retain all isolation guarantees

---

## 2. The DCMGroup Entity

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
  group_class: <see Section 2.2>
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
  # advisory:   group is a tag — no system behavior enforced by DCM
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
  child_groups: [<uuid>, ...]  # populated by DCM — do not set manually

  # POLICY TARGETING
  # Any policy can target this group by UUID or handle — no special declaration
  # Policy targeting a composite group applies to all member types by default
  # Policy can narrow with: member_type_filter: [resource_entity]
```

### 2.2 Group Classes

| group_class | Replaces | member_types_permitted | exclusivity.per_member | enforcement_model |
|-------------|---------|----------------------|----------------------|------------------|
| `tenant_boundary` | Tenant | resource_entity, group | one (structural lock) | profile-governed |
| `resource_grouping` | Resource Group, Custom Resource Group | resource_entity | many | advisory |
| `policy_collection` | Policy Group | policy | many | enforced |
| `policy_profile` | Policy Profile | group (policy_collection only) | many | enforced |
| `layer_grouping` | Layer Domain grouping | layer | many | enforced |
| `provider_grouping` | Provider collections | provider | many | advisory |
| `composite` | (new) | all types | many | configurable |
| `federation` | (new) | group (tenant_boundary) | many | advisory |

### 2.3 Structural Invariants — Non-Overridable

Regardless of `enforcement_model`, `group_class`, or active Profile, the following structural invariants always hold:

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

### 3.1 tenant_boundary

**Replaces:** Tenant entity  
**Purpose:** Ownership boundary, isolation enforcement, cost attribution, audit scope, sovereignty boundary

```yaml
dcm_group:
  group_class: tenant_boundary
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
- `minimal` profile → `enforcement_model: advisory` (tenancy optional)
- `dev` profile → `enforcement_model: enforced` (tenancy recommended)
- `standard` and above → `enforcement_model: mandatory` (tenancy required)

### 3.2 resource_grouping

**Replaces:** DCM Default Resource Group, Custom Resource Group  
**Purpose:** Flexible composable grouping of resource entities — structured tagging

```yaml
dcm_group:
  group_class: resource_grouping
  group_subclass: cost_center   # advisory — CostCenter, BusinessUnit, Project, Team...
  member_types_permitted: [resource_entity]
  exclusivity:
    per_member: many   # a resource can be in multiple resource groups
  enforcement_model: advisory
```

### 3.3 policy_collection

**Replaces:** Policy Group  
**Purpose:** Cohesive collection of policies addressing a single concern

```yaml
dcm_group:
  group_class: policy_collection
  concern_tags: [pci-dss, encryption, network-segmentation]
  member_types_permitted: [policy]
  enforcement_model: enforced
  # Source — local or External Policy Evaluator
  source:
    type: <local|external_policy_evaluation>
    provider_uuid: <uuid — if external_policy_evaluation>
    on_provider_update: <proposed|active>
```

### 3.4 policy_profile

**Replaces:** Policy Profile  
**Purpose:** Complete DCM configuration for a use case, composed of policy_collection groups

```yaml
dcm_group:
  group_class: policy_profile
  member_types_permitted: [group]   # only policy_collection groups
  extends: <parent profile uuid>    # inherits all parent's groups
  enforcement_model: enforced
```

### 3.5 composite

**New concept:** A group whose members span multiple member types — the organizational unit for a complete concern.

```yaml
dcm_group:
  group_class: composite
  name: "Payments Platform"
  concern_tags: [payments, pci-scope]
  member_types_permitted: [resource_entity, policy, layer, group, provider]
  enforcement_model: advisory   # composite groups are organizational — advisory default

  members:
    - member_uuid: <payments-vm-uuid>
      member_type: resource_entity
      member_role: compute
    - member_uuid: <pci-dss-group-uuid>
      member_type: group
      member_role: compliance_governance
    - member_uuid: <payments-resource-group-uuid>
      member_type: group
      member_role: resource_inventory
    - member_uuid: <payments-service-layer-uuid>
      member_type: layer
      member_role: configuration
```

**Policy targeting composite groups:**
```yaml
policy:
  target_groups:
    - group_uuid: <payments-platform-uuid>
      member_type_filter: [resource_entity]   # narrow to resources only
      # Omit member_type_filter to apply to ALL member types (default)
```

### 3.6 federation

**New concept:** A group of tenant_boundary groups that share governance, visibility, and resources while maintaining complete independence.

```yaml
dcm_group:
  group_class: federation
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
| `minimal`, `dev` | `opt_in` | Child Tenants must explicitly adopt parent policies |
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

All groups are stored in a single **Group Registry** — a GitOps store following the standard data store contract. The registry is queryable by any combination of fields.

### 6.2 Class-Filtered API Views

The universal registry exposes class-filtered views for convenience:

| Endpoint | Equivalent Query |
|----------|----------------|
| `GET /tenants` | `GET /groups?group_class=tenant_boundary` |
| `GET /resource-groups` | `GET /groups?group_class=resource_grouping` |
| `GET /policy-groups` | `GET /groups?group_class=policy_collection` |
| `GET /policy-profiles` | `GET /groups?group_class=policy_profile` |
| `GET /federations` | `GET /groups?group_class=federation` |

Existing API references continue to work unchanged. New API consumers can use the universal endpoint.

---

## 8. DCM System Policies

| Policy | Rule |
|--------|------|
| `GRP-INV-001` | A resource_entity may belong to exactly one active tenant_boundary group |
| `GRP-INV-002` | Constituent relationships may not cross tenant_boundary group boundaries |
| `GRP-INV-003` | Destroying a parent tenant_boundary group requires explicit resolution of all child groups first |
| `GRP-INV-004` | A resource in a child tenant_boundary group belongs to the child — never the parent |
| `GRP-INV-005` | Circular group membership is invalid and must be rejected |
| `GRP-INV-006` | A group cannot be a member of itself |
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

## 9. Grouping and Relationship Gap Resolutions

### 9.1 Community Subclass Catalog (Q35)

The `group_class` set is closed — system behavior is tied to declared classes only. `group_subclass` is open and advisory. DCM maintains a community subclass catalog as a non-authoritative reference shipped with the well-known Information Provider Registry:

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

### 9.2 Group Sovereignty Interaction (Q36)

Sovereignty interaction is group_class-specific:

| group_class | Cross-Sovereignty | Notes |
|-------------|-----------------|-------|
| `tenant_boundary` | **Never** | Structural — not configurable |
| `resource_grouping` | Permitted by default | Policy may restrict for classified resources |
| `policy_collection` | Always permitted | Policies have no sovereignty — governance artifacts |
| `layer_grouping` | Always permitted | Layers have no sovereignty |
| `composite` | Governed by most restrictive member | If contains cross-sovereignty resources, resource rules apply |
| `federation` | Permitted with DCM federation rules | DCM-003 governs data flows |

```yaml
# Policy restricting cross-sovereignty resource group membership
policy:
  type: gatekeeper
  rule: >
    If group.group_class == resource_grouping
    AND member.classification_level IN [confidential, restricted]
    AND member.sovereignty_zone != group.primary_sovereignty_zone
    THEN gatekeep: "Classified resources cannot join cross-sovereignty resource groups"
```

### 9.3 Tenant Decommission Lifecycle (Q37)

Tenant decommission is the highest-stakes lifecycle operation in DCM. It requires mandatory pre-decommission validation and follows a staged sequence.

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

### 9.4 Time-Bounded Group Membership (Q38)

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

Membership expiry produces a `MEMBER_REMOVE` audit record with `reason: membership_ttl_expired`.

### 9.5 Group Policy Inheritance — Nested Groups (Q39)

Policy inheritance for nested groups is group_class-specific and profile-governed:

| group_class | Default | Profile Override |
|-------------|---------|----------------|
| `tenant_boundary` | `opt_out` (parent cascades unless child excludes) | `opt_in` for minimal/dev/fsi/sovereign |
| `resource_grouping` | Not applicable | Resource groups are tags — policies target them, not inherit through them |
| `policy_collection` | Not applicable | Policy collections use `extends` for inheritance |
| `composite` | `opt_out` | Configurable per group |
| `federation` | `opt_in` | Peer consent always required — not configurable |

```yaml
# Nested group policy inheritance declaration
dcm_group:
  group_class: tenant_boundary
  parent_group_uuid: <corporate-tenant-uuid>
  policy_inheritance: opt_out     # governed by active Profile
  parent_policy_exclusions:
    - policy_uuid: <uuid>         # explicitly excluded from cascading to this child
```

---

## 10. System Policies — Grouping Gaps

| Policy | Rule |
|--------|------|
| `GRP-011` | The group_class set is closed — system behavior is tied to declared classes only. group_subclass is open and advisory. DCM maintains a community subclass catalog as a non-authoritative reference. No validation or enforcement on subclass values. |
| `GRP-012` | Sovereignty interaction is group_class-specific. tenant_boundary groups never span sovereignty boundaries (structural). resource_grouping groups may span sovereignty boundaries by default — policy may restrict for classified resources. policy_collection and layer_grouping groups always permitted cross-sovereignty. composite groups are governed by the sovereignty rules of their most restrictive member type. |
| `GRP-013` | Tenant decommission requires pre-decommission validation (resource state, cross-tenant relationships, compliance holds, child group resolution). Resources follow declared lifecycle policy. Child tenant_boundary groups must be resolved before parent decommission. Audit records enter post-lifecycle retention — never destroyed as part of Tenant decommission. |
| `GRP-014` | Group memberships support time-bounded validity via valid_from and expires_at. Membership expiry is enforced by the Lifecycle Constraint Enforcer. Expiry produces a MEMBER_REMOVE audit record. on_expiry action (remove, notify, suspend_member) declared per membership. Default: notify. |
| `GRP-015` | Group policy inheritance is group_class-specific and profile-governed. tenant_boundary: opt_out (standard/prod) or opt_in (minimal/dev/fsi/sovereign). federation: always opt_in — peer consent required. composite: opt_out by default. resource_grouping and policy_collection: not applicable. |


## 11. Related Concepts

- **Resource Grouping** (doc 08) — original resource grouping model, now implemented via `group_class: resource_grouping`
- **Policy Organization** (doc 14) — Policy Groups and Profiles, now implemented via `group_class: policy_collection` and `group_class: policy_profile`
- **Entity Relationships** (doc 09) — cross-tenant authorized relationships between groups
- **Universal Audit Model** (doc 16) — all group changes produce audit records
- **Ingestion Model** (doc 13) — migration of existing constructs to universal groups


---

## 13. Cross-Tenant Authorization Lifecycle

### 13.1 What Cross-Tenant Authorizations Are

A `cross_tenant_authorization` is a DCMGroup with `group_class: cross_tenant_authorization`. It is the formal mechanism by which one Tenant grants another Tenant permission to reference, allocate from, or stake a resource that belongs to the granting Tenant.

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


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
