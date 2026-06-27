# UDLM — Registry Governance

**Document Status:** ✅ Stable — UDLM substrate contract
**Related Documents:** [Resource Type Hierarchy](../entities/resource-type-hierarchy.md) | [Auth Providers](auth-providers.md) | [Federated Contribution Model](federated-contribution-model.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM substrate.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](../foundations/foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: DATA + PROVIDER**
>
> Data: registry artifacts. Provider: Resource Type Registry extension.

---

## 1. Purpose

The Resource Type Registry is the authoritative catalog of Resource Type Specifications available to a UDLM-conformant deployment. It governs what resources can be requested, how they are defined, and how those definitions evolve over time. Registry governance defines how new types are proposed, reviewed, approved, versioned, deprecated, and distributed — including in air-gapped and sovereign deployments.

Registry governance follows the same substrate principles as all other UDLM governance: artifact-based, policy-driven, profile-governed for ease of use, and audited.

---

## 2. The Three-Tier Registry

### 2.1 Registry Tiers

| Tier | Name | Maintained By | Contains | Governed By |
|------|------|--------------|---------|------------|
| 1 | **UDLM Core** | UDLM project team | Universal resource types | UDLM maintainers + community |
| 2 | **Verified Community** | Named community maintainers | Technology/platform-specific types | Named maintainer(s) + UDLM oversight |
| 3 | **Organization** | Deploying organization | Organization-specific/proprietary types | Organization's own process |

**Tier 1 examples:** `Compute.VirtualMachine`, `Network.VLAN`, `Network.IPAddress`, `Storage.Block`, `Storage.File`, `Container.Pod`

**Tier 2 examples:** `OpenStack.HeatStack`, `VMware.NSXSegment`, `KubeVirt.VirtualMachine`, `Ansible.Playbook`

**Tier 3 examples:** `Acme.LegacyMainframeJob`, `Corp.ServiceNowTicket`, `Internal.ComplianceReport`

### 2a. Three-Tier Model Applied to All Artifact Types

The three-tier registry model applies to all UDLM artifact types, not just resource type specs. Every artifact in the substrate has a tier that determines its trust level and the review requirements for changes:

| Tier | Maintained by | Examples | Review for changes |
|------|--------------|---------|-------------------|
| **Core** | UDLM project | Built-in policies, base layers, system resource types | UDLM project PR process |
| **Verified Community** | Named community maintainers | Community resource types, shared policy templates, vetted provider specs | Community review + platform admin acceptance |
| **Organization** | Deploying organization | Tenant policies, provider catalog items, org-specific specs | Per profile (auto → authorized) |

**Contributor sub-tiers within Organization tier:**
- `organization/platform` — authored by platform admins; highest trust in org tier
- `organization/provider` — authored by registered Service Providers; scoped to their resource types
- `organization/tenant` — authored by Consumer/Tenant actors; scoped to their Tenant

This means a tenant-authored GateKeeper policy is Organization/Tenant tier — it has lower inherent trust than a platform-authored policy at the same domain level, and may require additional review per the active profile. See [Federated Contribution Model](federated-contribution-model.md).

### 2.2 The Federated Registry Model

The registry uses a federated model — not centralized, not fully distributed. This supports air-gapped and sovereign deployments without external dependencies. The model is normative; the specific hosting endpoints below are illustrative.

```
UDLM Project Registry (authoritative origin)
  Published at: <upstream registry URL>
  Contains: Tier 1 Core + Tier 2 Verified Community
  │
  ▼  Sync (scheduled pull)
Organization Registry (local mirror)
  Hosted internally by the deploying organization
  Adds: Tier 3 Organization-specific types
  Authoritative for: this organization's deployments
  Can operate offline: yes — pulls during sync windows
  │
  ▼  Signed bundle transfer (for air-gapped)
Air-gapped Registry (offline copy)
  No external connectivity required
  Updated via signed bundles verified against org public key
  Authoritative for: this sovereign/air-gapped deployment
```

---

## 3. Proposal and Review Workflow (Artifact Lifecycle Contract)

### 3.1 The Submission Flow

The substrate requires an artifact-based proposal workflow. A common implementation transport is GitOps (PR-based), but the contract requirements are independent of transport.

The submitter becomes the **Resource Type Authority** for the submitted specification unless an alternative authority is declared in the `owned_by` field. The authority is the required approver for all future version changes against that specification — no version of the specification can be activated without the authority's approval (or the authority designating a successor via a formal authority transfer).

> **Resource Type Authority:** The submitter becomes the **Resource Type Authority**
> for the specification unless an alternative is declared in the `owned_by` field.
> The authority is the required approver for all future version changes — no new version
> activates without their approval. Authority can be transferred via a formal transfer.
> This is the same `owned_by` governance model applied to all UDLM artifacts.

> **`developing` / `proposed` here are review-WORKFLOW stages, not the spec's `status` field.** They
> describe an artifact's journey *into* the registry (draft → under review → accepted). The meta-schema
> `status` enum (`active | deprecated | retired`, `registry/resource-type-spec.schema.json`) is the
> separate *published-lifecycle* axis, and maturity is the *version* (`0.x` → `1.0`) — see VERSIONING.md
> "Lifecycle vs. maturity". A spec only enters the validated registry once accepted, at which point it
> is `status: active`. Don't conflate the workflow stage with `status`.

```
1. Author creates Resource Type Specification draft
   ├── Standard artifact format (uuid, handle, version, status: developing)
   ├── Schema definition
   ├── Lifecycle declarations
   ├── Declared dependencies (must exist in registry)
   └── At least one example request payload

2. Author submits proposal
   ├── Use case justification, example provider implementation,
   │   test cases, schema validation passing
   └── Status automatically set to: proposed

3. Automated validation gates (must all pass before review begins)
   ├── Schema validator passes
   ├── No FQN conflict with existing active entries
   ├── All declared dependencies resolve
   ├── Breaking change detector (if version > 1.0.0)
   └── Test case coverage (at least one valid example payload)

4. Community review period (see Section 3.2)

5. Maintainer approval + acceptance
   └── Status: proposed → enters shadow validation

6. Shadow validation period (same duration as review period)
   ├── Specification available to deployments opted into proposed feed
   ├── Issues reported back as comments
   └── Must pass without critical issues before promotion

7. Promotion to active
   └── Status: active → available in standard registry feed
```

### 3.2 Review Periods by Change Type (Substrate Defaults)

| Change Type | Min Review Period | Shadow Validation | Approvers Required |
|-------------|-----------------|-------------------|-------------------|
| New Tier 1 resource type | 14 days | 14 days | 2 UDLM maintainers |
| New Tier 2 resource type | 7 days | 7 days | 1 UDLM maintainer + named tier maintainer |
| Minor version (non-breaking) | 7 days | 7 days | 1 UDLM maintainer |
| Revision (config data only) | 3 days | 3 days | 1 UDLM maintainer (or auto-approve if CI passes) |
| Breaking change (major version) | 21 days | 21 days | 2 UDLM maintainers + community comment period |
| Deprecation | 30 days | N/A | 2 UDLM maintainers + affected provider notification |
| Emergency (security) | Waived | 7 days minimum | 2 UDLM maintainers + immediate notification |

---

## 4. Versioning

### 4.1 Version Schema

Resource Type Specifications use semantic versioning: `Major.Minor.Revision`

| Component | Meaning | Compatibility |
|-----------|---------|--------------|
| **Major** | Breaking change — field removed, type changed, behavior incompatible | Not compatible with previous major |
| **Minor** | Non-breaking addition — new optional fields, new lifecycle states | Compatible within major |
| **Revision** | Configuration data change — no structural change | Compatible within minor |

### 4.2 Version Resolution Policy

Version constraints in requests are **strictly enforced** — a conformant realization MUST NEVER silently resolve to a different version than declared. The resolution policy governs how much flexibility a consumer has:

```yaml
resource_type_version_constraint:
  resource_type: Compute.VirtualMachine
  version_policy: <exact|compatible|latest_minor|latest>
  # exact:        Must match — "1.2.3" means only 1.2.3
  # compatible:   Same major — "^1.2.3" means >= 1.2.3 < 2.0.0
  # latest_minor: Latest revision of specified minor — "~1.2" means 1.2.x
  # latest:       Always use the latest active version
  pinned_version: "1.2.3"   # required if version_policy: exact
```

**A conformant realization MUST NEVER automatically upgrade across major versions regardless of `version_policy`.** Moving from v1.x to v2.x always requires explicit consumer action.

### 4.3 Profile-Governed Version Policy Defaults

| Profile | Default Version Policy | Rationale |
|---------|----------------------|-----------|
| `minimal` | `latest` | Home lab — always current, no pinning overhead |
| `dev` | `compatible` | Dev — tracks major version, picks up fixes automatically |
| `standard` | `compatible` | Production — stable within major version |
| `prod` | `compatible` | Production — explicit major version control |
| `fsi` | `exact` | Regulatory — version-controlled for auditability |
| `sovereign` | `exact` | Maximum control — exact versions for reproducibility |

---

## 5. Deprecation Lifecycle (Contract)

### 5.1 The Default Deprecation Policy

Deprecation lifecycle is governed by **default substrate policies** — not hard-coded values. These defaults can be overridden using the standard policy priority mechanism. Higher-priority organizational policies can shorten, extend, or lock any of these values.

```yaml
# Default deprecation lifecycle policies (platform domain — overridable)
deprecation_lifecycle_policies:

  REG-DP-001:
    name: "Default deprecation notification period"
    value: P30D           # 30 days notice before deprecation status applied
    override: allow       # organizations may change this

  REG-DP-002:
    name: "Default sunset period by tier"
    values:
      tier_1: P12M        # 12 months for Core registry types
      tier_2: P6M         # 6 months for Verified Community types
      tier_3: organization_governed
    override: allow
    profile_locks:
      fsi: immutable      # FSI profile locks sunset periods
      sovereign: immutable

  REG-DP-003:
    name: "Default migration window after retirement"
    value: P90D           # 90 days after retirement — realizations enter DEPRECATED_RUNTIME
    override: allow

  REG-DP-004:
    name: "Migration target declaration"
    requirement: required_in_deprecation_notice
    # Deprecation notice must declare: successor type or explicit migration guidance
    override: allow

  REG-DP-005:
    name: "Behavior on retirement — new requests"
    value: reject         # retired types reject new requests (not warn — reject)
    override: not_permitted   # this is structural — cannot be changed

  REG-DP-006:
    name: "Behavior on retirement — existing realizations"
    value: deprecated_runtime_state
    # Existing realizations enter DEPRECATED_RUNTIME state:
    # - Eligible for: modify, decommission, drift detection
    # - Not eligible for: rehydration using deprecated type
    # - Not automatically destroyed
    override: allow

  REG-DP-007:
    name: "Emergency deprecation migration window"
    value: P30D           # minimum 30 days even for security emergency
    override: not_permitted   # floor cannot be removed
```

### 5.2 Deprecation Lifecycle Flow

```
Resource Type in active status
  │
  ▼  Deprecation proposal (P30D review)
Status: deprecated
  │  Notification dispatched to:
  │  - All registered providers implementing this type
  │  - All organizations with active realizations
  │  - All webhook registrations subscribed to registry events
  │
  ▼  Sunset period (P12M Tier 1 / P6M Tier 2 — per REG-DP-002)
  │  During sunset:
  │  - New requests: succeed with deprecation warning
  │  - Existing realizations: unaffected
  │  - Drift detection: continues
  │  - Provider implementations: remain valid
  │
  ▼  Retirement (status: retired)
  │  Existing realizations → DEPRECATED_RUNTIME state
  │  New requests → rejected (REG-DP-005)
  │
  ▼  Migration window (P90D — per REG-DP-003)
  │  Organizations migrate realizations to successor type
  │  DEPRECATED_RUNTIME entities can be decommissioned or migrated
  │
  ▼  Post-migration window
     DEPRECATED_RUNTIME entities remain operational but unsupported
     Drift detection: continues but remediation is manual
```

### 5.3 Overriding Deprecation Defaults

Organizations use standard policy priority to customize deprecation behavior:

```yaml
# Organizational policy: extend Tier 2 sunset to 12 months
policy:
  domain: platform
  priority: 600.0.0
  type: gatekeeper
  rule: >
    If registry.deprecation.tier == tier_2
    THEN override: sunset_period = P12M
    basis: "Our tooling requires longer migration windows"
```

```yaml
# FSI profile lock: sunset periods immutable
policy:
  domain: system
  priority: 900.0.0
  immutable_ceiling: absolute
  rule: >
    If active_profile IN [fsi, sovereign]
    THEN lock: REG-DP-002 as immutable
    rationale: "Regulatory change control requirements"
```

---

## 6. The Resource Type Registry (Provider Contract)

### 6.1 Concept

The Resource Type Registry is a specialized sub-type of Information Provider — the mechanism through which a UDLM deployment accesses its authoritative Resource Type Registry. Every deployment has exactly one active Resource Type Registry.

### 6.2 Registration (Wire Contract)

The registration shape is normative:

```yaml
internal_registry_registration:
  artifact_metadata:
    uuid: <uuid>
    handle: "providers/registry/org-primary"
    version: "1.0.0"
    status: active

  name: "Organization Primary Registry"
  provider_type: registry              # sub-type of information_provider

  # Registry source
  registry_url: https://registry.corp.example.com
  tier_1_source: <upstream UDLM registry URL>
  tier_2_sources:
    - <upstream UDLM registry URL>
    - https://registry.partner-org.example.com            # verified partner

  # Sync configuration
  sync:
    schedule: "0 2 * * *"            # nightly pull from upstream
    on_sync_failure: <alert|use_cached|block_new_requests>
    cache_ttl: P7D                   # use cached if upstream unavailable

  # Air-gapped / sovereign configuration
  offline_mode: false                # true: no external connectivity
  signed_bundle_import: false        # true: updates via signed bundles only
  bundle_signing_key_ref:
    service_provider_uuid: <uuid>
    secret_path: "registry/bundle-verification-key"

  # Sovereignty filtering
  sovereignty_filter:
    enabled: true
    permitted_jurisdictions: [eu-west, eu-central]
    # Only activate resource types flagged as compatible with these jurisdictions

  # Vendor approval list
  vendor_allowlist:
    enabled: false                   # true in prod/fsi/sovereign
    permitted_vendors: [udlm-project, vmware, redhat, hashicorp]
    # Resource types from non-listed vendors are not activated
```

### 6.3 Signed Bundle Model (Air-Gapped Updates) — Contract

```
Online workstation (with registry access)
  │
  Pull registry delta since last sync
  Sign with organization private key (via credential provider)
  Package: registry-update-YYYY-MM-DD.bundle
  │
  Transfer via approved secure channel
  │
Air-gapped deployment
  │
  Verify signature against organization public key
  Import bundle → update local registry
  Emit: registry.sync_completed audit event
```

---

## 7. UDLM System Policies

| Policy | Rule |
|--------|------|
| `REG-001` | Resource Type proposals follow an artifact-based workflow with automated validation gates (schema, FQN conflict, dependency resolution, breaking change detection) that must all pass before review begins. |
| `REG-002` | All registry changes require a minimum review period by change type and a mandatory shadow validation period in `proposed` status before promotion to `active`. |
| `REG-003` | Deprecation lifecycle is governed by default policies REG-DP-001 through REG-DP-007. These defaults are overridable via standard policy priority except where locked by active profile. |
| `REG-004` | Version constraints in requests are strictly enforced. A conformant realization MUST NEVER automatically upgrade across major versions regardless of `version_policy`. Version resolution policy is profile-governed. |
| `REG-006` | The registry uses a federated model. Air-gapped and sovereign deployments use offline registries populated via signed bundles verified against the organization's public key. |
| `REG-007` | The Resource Type Registry is policy-governed. Profile-appropriate registry policy groups are activated by default. Organizations may extend or replace these groups using standard Policy Group composition. |
| `REG-008` | A formal fourth registry tier is not introduced. Resource Type Specifications in any tier may carry certification metadata from recognized certifying bodies. Certification metadata is a filter criterion — not a structural tier boundary. |
| `REG-009` | Organizations may promote Tier 3 Resource Type Specifications to Tier 2 via the standard promotion pathway with additional requirements: at least one production deployment, OSS-compatible license, named community maintainer, and documented migration path from the Tier 3 handle. |
| `REG-010` | The Organization Registry mirror operates independently from the upstream UDLM Project Registry. Permanent upstream unavailability does not affect existing operations. New community type adoption requires a designated community mirror, organizational fork, or independent operation decision. |
| `REG-DP-001` | Default deprecation notification period: P30D before deprecation status is applied. Overridable. |
| `REG-DP-002` | Default sunset period: Tier 1 = P12M, Tier 2 = P6M. Overridable; locked as immutable in fsi and sovereign profiles. |
| `REG-DP-003` | Default migration window after retirement: P90D. Overridable. |
| `REG-DP-004` | Deprecation notices must declare a successor type or explicit migration guidance. Overridable. |
| `REG-DP-005` | Retired resource types reject new requests. Not overridable — structural. |
| `REG-DP-006` | Existing realizations of retired types enter DEPRECATED_RUNTIME state — eligible for modify and decommission, not rehydration. Overridable. |
| `REG-DP-007` | Emergency deprecation minimum migration window: P30D. Not overridable — floor cannot be removed. |

---

## 8. Related Concepts

- **Resource Type Hierarchy** ([../entities/resource-type-hierarchy.md](../entities/resource-type-hierarchy.md)) — the structure of Resource Type Specifications
- **Auth Providers** ([auth-providers.md](auth-providers.md)) — authentication for registry access
- **Universal Audit Model** ([../observability/universal-audit.md](../observability/universal-audit.md)) — all registry operations produce audit records
- **Federated Contribution Model** ([federated-contribution-model.md](federated-contribution-model.md)) — broader contribution pipeline for all artifact types

---

*UDLM substrate document. Realization-specific registry enforcement, provider selection tie-breaking algorithms, artifact lifecycle storage and warning mechanisms, and review queue / approval workflow mechanics live in the consuming realization's documentation.*
