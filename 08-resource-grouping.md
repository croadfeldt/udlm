# DCM Data Model — Resource Grouping



> **Related:** See [Universal Group Model](15-universal-groups.md) for the canonical group model. The constructs here (Tenants, Resource Groups) map 1:1 to `group_class` values in that model.

**Document Status:** ✅ Complete  
**Related Documents:** [Context and Purpose](00-context-and-purpose.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Service Dependencies](07-service-dependencies.md)

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
> The Data abstraction — DCMGroup typed extensions (Tenant, Resource Group, Cross-Tenant Auth)



---

## 1. Purpose

This document defines how Resource/Service Entities are organized into groups within DCM. Grouping provides the ownership, organizational context, cost attribution, policy scope, and rehydration targeting that makes DCM operationally meaningful at scale.

Two concepts are defined here:
1. **DCM Tenant** — the mandatory, first-class ownership boundary for all Resource/Service Entities
2. **Resource Groups** — flexible, composable grouping entities that provide additional organizational context

---

## 2. DCM Tenant

### 2.1 Definition

A **DCM Tenant** is the primary ownership and isolation boundary for Resource/Service Entities in DCM. Every Resource/Service Entity — including Process Resources — must belong to exactly one DCM Tenant at any point in time.

Tenant membership is the answer to the question: **who owns this resource?**

### 2.2 Tenant as a DCM System Policy

Mandatory Tenant membership is a **non-overridable DCM System Policy**:

| Policy | Rule | Enforcement |
|--------|------|-------------|
| `TEN-001` | Every Resource/Service Entity must belong to exactly one DCM Tenant | Enforced at Entity creation — no Tenant = request rejected |
| `TEN-002` | Tenant membership cannot be empty — a Tenant must exist before resources can be created in it | Enforced at request processing |
| `TEN-003` | A Resource/Service Entity cannot exist without a Tenant | Enforced at all lifecycle states |

### 2.3 What Tenant Provides

The Tenant boundary enables the following DCM capabilities for all resources it owns:

| Capability | Description |
|------------|-------------|
| **Ownership** | Unambiguous answer to "who owns this resource" — always answerable, always auditable |
| **Isolation** | Resources in one Tenant are isolated from resources in another — hard tenancy enforcement |
| **Cost Attribution** | All resource costs roll up to the owning Tenant |
| **Policy Scope** | Tenant-level policies apply to all resources in the Tenant |
| **Drift Detection Scope** | Drift detection can be scoped to a Tenant |
| **Rehydration Scope** | A full Tenant can be targeted for rehydration |
| **Audit Scope** | All activity within a Tenant is auditable as a unit |
| **Sovereignty Boundary** | Sovereignty constraints can be applied at the Tenant level |

### 2.4 Tenant Entity Definition

```yaml
dcm_tenant:
  uuid: <uuid>
  name: <human-readable name>
  description: <description>
  version: <Major.Minor.Revision>
  status:
    state: <active|deprecated|retired>
    deprecation_date: <if applicable>
    sunset_date: <if applicable>
    replacement_uuid: <if deprecated>
    deprecation_reason: <if deprecated>
    migration_guidance: <if deprecated>
  ownership:
    owner_uuid: <uuid of persona or entity that owns this tenant>
    owner_type: <persona|business_unit|organization>
    created_timestamp: <ISO 8601>
  membership_policy:
    exclusive: true
    # A resource belongs to exactly one Tenant
    # This is non-overridable
  sovereignty_constraints:
    <list of applicable sovereignty requirements>
  policies:
    <list of tenant-level policy UUIDs>
  provenance:
    <standard provenance metadata>
```

### 2.5 Tenant and Resource Consumption

A resource belongs to exactly one Tenant — its **owner**. However, a resource can be **consumed** by multiple Tenants via the DCM Service Catalog. Ownership and consumption are distinct:

- **Ownership** (Tenant membership) — who is responsible for the lifecycle, cost, and compliance of this resource
- **Consumption** — who uses or depends on this resource as a service

Cross-tenant consumption is tracked through service requests and cost attribution — not through Tenant membership. A shared DNS service owned by a Platform Tenant can be consumed by any number of application Tenants. The DNS Entity belongs to the Platform Tenant. Consumption is tracked via service requests from each consuming Tenant.

---

## 3. Resource Groups

### 3.1 Definition

A **Resource Group** is a flexible, composable grouping entity that provides organizational context, operational scope, and policy targeting beyond what Tenant membership provides.

Resource Groups function like **structured tags** — a resource accumulates group memberships that describe its context from multiple dimensions simultaneously. A VM could simultaneously belong to:
- `Deployment: WebApp-v2` (what deployment it is part of)
- `BusinessUnit: Payments` (which business unit owns the workload)
- `RegulatoryScope: PCI-DSS` (which compliance regime applies)
- `CostCenter: CC-4421` (where costs are attributed)

Each group membership is a different dimension of context — not a hierarchy within a single dimension.

### 3.2 Resource Group Classes

DCM defines two classes of Resource Group, both implementing the same **Resource Group Interface**:

**Class 1 — DCM Default Resource Group**
Built into DCM. The standard mechanism for grouping resources. No implementor customization required to use it.

**Class 2 — Custom Resource Group**
Implementor-defined grouping entities. Tied to internal business structures — business units, product lines, regulatory scopes, cost centers, etc. Full parity with DCM Default Resource Groups in terms of DCM capabilities.

Both classes implement the same interface. The DCM Default Resource Group is simply DCM's own implementation of the Resource Group Interface. Custom groups are implementor-defined implementations of the same interface.

### 3.3 The Resource Group Interface

Every Resource Group — both DCM default and custom — must implement this interface:

```yaml
resource_group:
  uuid: <uuid>
  name: <human-readable name>
  description: <description>
  group_class: <dcm_default|custom>
  group_type: <for custom groups — e.g., CostCenter, BusinessUnit, RegulatoryScope>
  version: <Major.Minor.Revision>
  status:
    state: <active|deprecated|retired>
    deprecation_date: <if applicable>
    sunset_date: <if applicable>
    replacement_uuid: <if deprecated>
    deprecation_reason: <if deprecated>
    migration_guidance: <if deprecated>
  nesting:
    supported: <true|false>
    # If true, this group can contain other groups as members
    max_depth: <integer|unlimited>
  membership:
    members:
      - member_uuid: <uuid of Resource/Service Entity or child Resource Group>
        member_type: <entity|resource_group>
        joined_timestamp: <ISO 8601>
        joined_by_uuid: <uuid of persona or policy that added this member>
    membership_policy:
      exclusive: <true|false>
      # If true, a resource can only belong to one group of this type at a time
      # If false, a resource can belong to multiple groups of this type
      max_memberships: <integer|unlimited>
      # Maximum number of groups of this type a resource can belong to
      allowed_entity_types:
        <list of Resource Type UUIDs allowed as members — empty means all types allowed>
  policies:
    <list of group-level policy UUIDs>
  provenance:
    <standard provenance metadata>
```

### 3.4 Multi-Group Membership

A Resource/Service Entity can belong to multiple Resource Groups across all classes. This multi-dimensional membership is what gives groups their tag-like flexibility.

**Membership constraints are configurable per group definition:**
- A group can declare `exclusive: true` — meaning a resource can only belong to one group of that type at a time
- Example: A `RegulatoryScope` group might declare `exclusive: true` — a resource cannot be in both EU-GDPR and US-FISMA regulatory scopes simultaneously
- Example: A `Deployment` group might declare `exclusive: false` — a resource could participate in multiple deployments

**Policy-governed membership:**
Organizational policies can further restrict multi-group membership. For example, a sovereignty policy could declare that resources in a PCI-DSS scope cannot be in the same group as resources in a non-PCI scope.

### 3.5 Nesting

Resource Groups that declare `nesting: true` can contain other Resource Groups as members in addition to individual Resource/Service Entities.

**Example nesting structure:**
```
Tenant: Payments Platform
  │
  └── Resource Group: Deployment — WebApp-v2         (nesting: true)
        ├── Resource Group: Service — Frontend        (nesting: true)
        │     ├── Entity: Web Server VM 1
        │     ├── Entity: Web Server VM 2
        │     └── Entity: Load Balancer
        └── Resource Group: Service — Backend         (nesting: true)
              ├── Entity: App Server VM 1
              ├── Entity: App Server VM 2
              └── Entity: Database
```

**Nesting rules:**
- Circular nesting is invalid — a group cannot contain itself directly or transitively
- Nesting depth is declared per group — `max_depth: unlimited` allows arbitrary depth
- A child group inherits policy scope from parent groups — policies applied to a parent group propagate to all child groups and their members
- Cost rollup propagates up the nesting hierarchy

---

## 4. DCM System Policies for Resource Grouping

| Policy | Rule | Enforcement |
|--------|------|-------------|
| `GRP-001` | Every Resource/Service Entity must belong to exactly one DCM Tenant | Enforced at Entity creation |
| `GRP-002` | A Resource/Service Entity cannot be removed from its Tenant without being transferred to another Tenant | Enforced at all lifecycle states |
| `GRP-003` | Circular nesting in Resource Groups is invalid | Enforced at group membership modification |
| `GRP-004` | Custom Resource Groups must implement the full Resource Group Interface | Enforced at group registration |
| `GRP-005` | Exclusive membership groups must reject membership requests that violate exclusivity | Enforced at group membership addition |

---

## 5. Grouping and DCM Capabilities

Resource Groups enable the following DCM capabilities at the group scope:

| Capability | Tenant | Resource Group |
|------------|--------|---------------|
| Cost Attribution | ✅ Primary | ✅ Rollup within group |
| Policy Scope | ✅ | ✅ |
| Drift Detection Scope | ✅ | ✅ |
| Rehydration Scope | ✅ Full Tenant | ✅ Group and dependencies |
| Audit Scope | ✅ | ✅ |
| Placement Constraints | ✅ | ✅ |
| Sovereignty Boundary | ✅ | ✅ |

---

## 6. Process Resources and Grouping

Process Resource Entities follow the same grouping rules as Infrastructure Resource Entities:

- Must belong to exactly one DCM Tenant — non-overridable
- Can optionally belong to Resource Groups
- Typically grouped under the same Deployment or Service group as the resources they operate on
- Tenant membership ensures cost attribution for execution resources
- Group membership enables operational scoping — "show me all automation jobs that ran against this Deployment"

---

## 7. Custom Resource Group Registration

Implementors register custom Resource Group types as part of their DCM implementation. Custom group types must declare their full interface implementation:

```yaml
custom_group_type_registration:
  uuid: <uuid>
  type_name: <e.g., CostCenter, BusinessUnit, RegulatoryScope>
  version: <Major.Minor.Revision>
  description: <description>
  implementing_organization_uuid: <uuid>
  interface_version: <version of Resource Group Interface this implements>
  default_membership_policy:
    exclusive: <true|false>
    max_memberships: <integer|unlimited>
  nesting_supported: <true|false>
  allowed_entity_types: <list or empty for all>
  status:
    state: <active|deprecated|retired>
```

---

## 8. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should there be a DCM-maintained registry of well-known custom group types to encourage standardization? | Interoperability | ✅ Resolved — group_subclass open and advisory; community subclass catalog as non-authoritative reference; no validation or enforcement; see doc 15 (GRP-011) |
| 2 | How does group membership interact with sovereignty — can a group span sovereignty boundaries? | Sovereignty model | ✅ Resolved — class-specific: tenant_boundary never cross-sovereignty (structural); resource_grouping permitted+policy restriction; policy_collection always permitted; composite governed by most restrictive member; see doc 15 (GRP-012) |
| 3 | When a Tenant is decommissioned, what happens to its resources and group memberships? | Lifecycle management | ✅ Resolved — four-phase staged decommission: pre-validation → resource decommission → membership cleanup → audit archival; child groups must be resolved first; audit records never destroyed; see doc 15 (GRP-013) |
| 4 | Should Resource Groups support time-bounded membership — a resource belongs to a group for a defined period? | Operational flexibility | ✅ Resolved — valid_from/expires_at already in Universal Group Model; on_expiry (remove/notify/suspend_member); Lifecycle Constraint Enforcer handles; MEMBER_REMOVE audit record; see doc 15 (GRP-014) |
| 5 | How are group-level policies inherited by nested child groups — is inheritance opt-in or opt-out? | Policy model | ✅ Resolved — class-specific defaults profile-governed; tenant_boundary: opt_out (standard/prod), opt_in (fsi/sovereign); federation always opt_in; composite opt_out; see doc 15 (GRP-015) |

---

## 9. Related Concepts

- **DCM Tenant** — primary ownership boundary, mandatory for all entities
- **Resource/Service Entity** — the thing being grouped
- **Policy Engine** — enforces grouping system policies and evaluates group-level organizational policies
- **Cost Analysis** — rolls up costs through group hierarchies
- **Drift Detection** — can be scoped to a group
- **Rehydration** — can target a group as the unit of reconstruction
- **Field-Level Provenance** — group membership changes are recorded in entity provenance


---

## 10. Cross-Tenant Authorization Lifecycle

Cross-tenant authorizations are the formal mechanism by which one Tenant grants another Tenant access to a shared resource or allocation. They are DCMGroup instances with `group_class: cross_tenant_authorization`.

### 10.1 Creation

Cross-tenant authorizations are created by:

| Actor | Mechanism | When |
|-------|-----------|------|
| Granting Tenant Admin | Explicit manual grant via Admin API | Normal cross-tenant sharing setup |
| Platform Admin | Emergency authorization | Operational incident; requires dual approval in fsi/sovereign |
| Policy (pre-authorization) | GateKeeper policy auto-creates authorization | Pre-approved sharing patterns |

```yaml
cross_tenant_authorization:
  artifact_metadata:
    uuid: <uuid>
    handle: "xta/networkops/appteam/vlan-100"
    version: "1.0.0"
    status: active
  group_class: cross_tenant_authorization
  granting_tenant_uuid: <networkops-tenant-uuid>
  consuming_tenant_uuid: <appteam-tenant-uuid>
  authorized_resource_types: [Network.VLAN, Network.IPAddressPool]
  authorized_entity_uuids: [<vlan-100-uuid>]    # null = all resources of declared types
  duration: P1Y                                   # null = perpetual until revoked
  expires_at: <ISO 8601|null>
  created_by: <actor-uuid>
  created_at: <ISO 8601>
  purpose: "AppTeam VMs require VLAN-100 attachment for production network access"
```

### 10.2 Duration and Renewal

- **Fixed duration** (`duration: P1Y`): expires automatically. Notification sent P30D before expiry. Consuming Tenant must request renewal. If not renewed, enters EXPIRING state, then EXPIRED.
- **Perpetual** (`duration: null`): active until explicitly revoked. No automatic expiry.
- **Renewal**: consuming Tenant submits a new authorization request. Granting Tenant approves. New authorization created; old one superseded.

### 10.3 Revocation

```
Granting Tenant admin revokes authorization
  │
  ▼ Authorization status → REVOKED
  │
  ▼ Identify active allocations and stakes under this authorization
  │   All cross-tenant allocations/stakes enter PENDING_REVIEW
  │
  ▼ Notifications sent to:
  │   Consuming Tenant Admin (action required: migrate or release)
  │   Affected resource owners in consuming Tenant
  │   Platform Admin (informational)
  │
  ▼ Resolution deadline: P30D (configurable; P7D for fsi/sovereign)
  │
  ├── Consuming Tenant releases stakes/allocations → authorization closes cleanly
  └── Deadline exceeded → Platform Admin escalation
      Policy may declare automatic release on deadline exceeded
```

### 10.4 What Happens to Active Allocations on Revocation

Resources already allocated under a now-revoked authorization are NOT immediately decommissioned — this would break production workloads. Instead:
- The allocation/stake relationship enters PENDING_REVIEW
- The authorization revocation is recorded as the `pending_review_trigger`
- The consuming Tenant has a grace period to migrate or release
- Automatic decommission on deadline exceeded is a policy declaration, not a default

### 10.5 System Policies

| Policy | Rule |
|--------|------|
| `XTA-001` | Cross-tenant authorizations require explicit creation by the granting Tenant admin, a platform admin, or a pre-authorization policy. They are never implicitly created. |
| `XTA-002` | Fixed-duration authorizations generate a P30D expiry warning notification. Non-renewal results in EXPIRING then EXPIRED states. |
| `XTA-003` | Authorization revocation places active allocations and stakes in PENDING_REVIEW with a policy-governed grace period. Resources are not automatically decommissioned on revocation. |
| `XTA-004` | Automatic decommission of resources on authorization expiry or revocation requires explicit policy declaration. It is not the default behavior. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
