# DCM Data Model — Registry Governance


**Document Status:** ✅ Complete  
**Related Documents:** [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Policy Organization](14-policy-profiles.md) | [Deployment and Redundancy](17-deployment-redundancy.md) | [Auth Providers](19-auth-providers.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA + PROVIDER**
>
> Data: registry artifacts. Provider: Registry Provider extension



---

## 1. Purpose

The Resource Type Registry is the authoritative catalog of Resource Type Specifications available to DCM deployments. It governs what resources can be requested, how they are defined, and how those definitions evolve over time. Registry governance defines how new types are proposed, reviewed, approved, versioned, deprecated, and distributed — including in air-gapped and sovereign deployments.

Registry governance follows the same principles as all other DCM governance: GitOps-managed, policy-driven, profile-governed for ease of use, and audited.

---

## 2. The Three-Tier Registry

### 2.1 Registry Tiers

| Tier | Name | Maintained By | Contains | Governed By |
|------|------|--------------|---------|------------|
| 1 | **DCM Core** | DCM Project team | Universal resource types | DCM maintainers + community |
| 2 | **Verified Community** | Named community maintainers | Technology/platform-specific types | Named maintainer(s) + DCM oversight |
| 3 | **Organization** | Deploying organization | Organization-specific/proprietary types | Organization's own process |

**Tier 1 examples:** `Compute.VirtualMachine`, `Network.VLAN`, `Network.IPAddress`, `Storage.Block`, `Storage.File`, `Container.Pod`

**Tier 2 examples:** `OpenStack.HeatStack`, `VMware.NSXSegment`, `KubeVirt.VirtualMachine`, `Ansible.Playbook`

**Tier 3 examples:** `Acme.LegacyMainframeJob`, `Corp.ServiceNowTicket`, `Internal.ComplianceReport`


### 2a. Three-Tier Model Applied to All Artifact Types

The three-tier registry model applies to all DCM artifact types, not just resource type specs. Every artifact in DCM has a tier that determines its trust level and the review requirements for changes:

| Tier | Maintained by | Examples | Review for changes |
|------|--------------|---------|-------------------|
| **Core** | DCM Project | Built-in policies, base layers, system resource types | DCM project PR process |
| **Verified Community** | Named community maintainers | Community resource types, shared policy templates, vetted provider specs | Community review + platform admin acceptance |
| **Organization** | Deploying organization | Tenant policies, provider catalog items, org-specific specs | Per profile (auto → authorized) |

**Contributor sub-tiers within Organization tier:**
- `organization/platform` — authored by platform admins; highest trust in org tier
- `organization/provider` — authored by registered Service Providers; scoped to their resource types
- `organization/tenant` — authored by Consumer/Tenant actors; scoped to their Tenant

This means a tenant-authored GateKeeper policy is Organization/Tenant tier — it has lower inherent trust than a platform-authored policy at the same domain level, and may require additional review per the active profile. See [Federated Contribution Model](28-federated-contribution-model.md).


### 2.2 The Federated Registry Model

The registry uses a federated model — not centralized, not fully distributed. This supports air-gapped and sovereign deployments without external dependencies.

```
DCM Project Registry (authoritative origin)
  Published at: registry.dcm-project.github.io
  Contains: Tier 1 Core + Tier 2 Verified Community
  │
  ▼  Sync (scheduled pull)
Organization Registry (local mirror)
  Hosted internally by the deploying organization
  Adds: Tier 3 Organization-specific types
  Authoritative for: this organization's DCM deployments
  Can operate offline: yes — pulls during sync windows
  │
  ▼  Signed bundle transfer (for air-gapped)
Air-gapped Registry (offline copy)
  No external connectivity required
  Updated via signed bundles verified against org public key
  Authoritative for: this sovereign/air-gapped deployment
```

---

## 3. Proposal and Review Workflow

### 3.1 The PR-Based Proposal Flow

The PR submitter becomes the **Resource Type Authority** for the submitted specification
unless an alternative authority is declared in the `owned_by` field. The authority is
the required approver for all future version PRs against that specification — no version
of the specification can be activated without the authority's approval (or the authority
designating a successor via a formal authority transfer PR).

Resource Type proposals follow a GitOps PR-based workflow — not form submissions or tickets. A proposal is a Pull Request against the registry repository.

> **Resource Type Authority:** The PR submitter becomes the **Resource Type Authority**
> for the specification unless an alternative is declared in the `owned_by` field.
> The authority is the required approver for all future version PRs — no new version
> activates without their approval. Authority can be transferred via a formal transfer PR.
> This is the same `owned_by` governance model applied to all DCM artifacts.



```
1. Author creates Resource Type Specification draft
   ├── Standard artifact format (uuid, handle, version, status: developing)
   ├── Schema definition
   ├── Lifecycle declarations
   ├── Declared dependencies (must exist in registry)
   └── At least one example request payload

2. Author opens Pull Request
   ├── PR template: use case justification, example provider implementation,
   │   test cases, schema validation passing
   └── Status automatically set to: proposed (on PR open)

3. Automated validation gates (must all pass before review begins)
   ├── Schema validator passes
   ├── No FQN conflict with existing active entries
   ├── All declared dependencies resolve
   ├── Breaking change detector (if version > 1.0.0)
   └── Test case coverage (at least one valid example payload)

4. Community review period (see Section 3.2)

5. Maintainer approval + merge
   └── Status: proposed → enters shadow validation

6. Shadow validation period (same duration as review period)
   ├── Specification available to DCM deployments opted into proposed feed
   ├── Issues reported back as PR comments
   └── Must pass without critical issues before promotion

7. Promotion to active
   └── Status: active → available in standard registry feed
```

### 3.2 Review Periods by Change Type

| Change Type | Min Review Period | Shadow Validation | Approvers Required |
|-------------|-----------------|-------------------|-------------------|
| New Tier 1 resource type | 14 days | 14 days | 2 DCM maintainers |
| New Tier 2 resource type | 7 days | 7 days | 1 DCM maintainer + named tier maintainer |
| Minor version (non-breaking) | 7 days | 7 days | 1 DCM maintainer |
| Revision (config data only) | 3 days | 3 days | 1 DCM maintainer (or auto-approve if CI passes) |
| Breaking change (major version) | 21 days | 21 days | 2 DCM maintainers + community comment period |
| Deprecation | 30 days | N/A | 2 DCM maintainers + affected provider notification |
| Emergency (security) | Waived | 7 days minimum | 2 DCM maintainers + immediate notification |

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

Version constraints in requests are **strictly enforced** — DCM never silently resolves to a different version than declared. The resolution policy governs how much flexibility a consumer has:

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

**DCM never automatically upgrades across major versions regardless of version_policy.** Moving from v1.x to v2.x always requires explicit consumer action.

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

## 5. Deprecation Lifecycle

### 5.1 The Default Deprecation Policy

Deprecation lifecycle is governed by **default DCM system policies** — not hard-coded values. These defaults can be overridden using the standard policy priority mechanism. Higher-priority organizational policies can shorten, extend, or lock any of these values.

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
  ▼  Deprecation proposal (PR + 30 day review)
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

## 6. Provider Selection Tie-Breaking

When the placement engine has multiple viable provider candidates that satisfy all constraints equally, the following hierarchy resolves the tie deterministically:

### 6.1 Tie-Breaking Hierarchy

```
Priority  Factor                    Condition
────────  ──────────────────────    ─────────────────────────────────────────
1         Policy preference         A Transformation policy injected a
                                    preference_score or preferred_provider_uuid

2         Provider priority         Providers declare a numeric priority
                                    Higher value = preferred (default: 50)

3         Tenant affinity           Tenant's Policy Group declares preferred
                                    providers for specific resource types

4         Cost analysis             Cost Analysis component has current data
                                    AND cost is determinable for candidates
                                    Prefer lower total cost (CapEx + OpEx)
                                    SKIP if cost data absent or incomparable

5         Least loaded              Current capacity utilization from reserve_query
                                    If utilization differs > 10%: prefer less loaded
                                    SKIP if utilization data unavailable

6         Consistent hash           SHA-256(request_uuid + resource_type + sorted_candidate_uuids)
                                    Deterministic — same request always resolves
                                    to same provider in a stable cluster
                                    Never round-robin
```

### 6.2 Cost Analysis Integration

Cost analysis ranks above operational load because cost is a business decision. When cost data is available and comparable:

- **CapEx consideration:** provider infrastructure cost allocation per resource type
- **OpEx consideration:** operational overhead, licensing, support costs per resource unit
- **Comparability requirement:** cost must be expressed in the same currency and time period; if not comparable (different currencies, missing data), skip to step 5

Cost data is sourced from the **Cost Analysis** control plane component. If Cost Analysis is not deployed or does not have current data for the candidate providers, this step is skipped without blocking placement.

```yaml
# Cost analysis in placement loop
placement_cost_evaluation:
  enabled: true                    # false if Cost Analysis unavailable
  data_freshness_max: PT1H         # reject cost data older than 1 hour
  comparison_threshold: 0.05       # 5% cost difference to trigger preference
  # If candidates are within 5% cost: skip cost as a tiebreaker
  cost_components:
    - capex_allocation_per_unit
    - opex_per_unit_per_hour
    - licensing_per_unit
```

### 6.3 Provider Priority Declaration

```yaml
provider_registration:
  provider_priority: 100   # default: 50; higher = preferred when equal
  cost_metadata:
    capex_allocation_per_unit: 12.50    # USD per VM-month
    opex_per_unit_per_hour: 0.08       # USD per VM-hour
    currency: USD
    last_updated: <ISO 8601>
```

---

## 7. The Registry Provider

### 7.1 Concept

The Registry Provider is a specialized sub-type of Information Provider — the mechanism through which a DCM deployment accesses its authoritative Resource Type Registry. Every DCM deployment has exactly one active Registry Provider.

### 7.2 Registration

```yaml
registry_provider_registration:
  artifact_metadata:
    uuid: <uuid>
    handle: "providers/registry/org-primary"
    version: "1.0.0"
    status: active

  name: "Organization Primary Registry"
  provider_type: registry              # sub-type of information_provider

  # Registry source
  registry_url: https://registry.corp.example.com
  tier_1_source: https://registry.dcm-project.github.io   # upstream pull
  tier_2_sources:
    - https://registry.dcm-project.github.io
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
    secret_path: "dcm/registry/bundle-verification-key"

  # Sovereignty filtering
  sovereignty_filter:
    enabled: true
    permitted_jurisdictions: [eu-west, eu-central]
    # Only activate resource types flagged as compatible with these jurisdictions

  # Vendor approval list
  vendor_allowlist:
    enabled: false                   # true in prod/fsi/sovereign
    permitted_vendors: [dcm-project, vmware, redhat, hashicorp]
    # Resource types from non-listed vendors are not activated
```

### 7.3 Signed Bundle Model (Air-Gapped Updates)

```
Online workstation (with registry access)
  │
  Pull registry delta since last sync
  Sign with organization private key (via Credential Provider)
  Package: registry-update-YYYY-MM-DD.bundle
  │
  Transfer via approved secure channel
  │
Air-gapped DCM deployment
  │
  Verify signature against organization public key
  Import bundle → update local registry
  Emit: registry.sync_completed audit event
```

### 7.4 Registry Provider Policies

The Registry Provider is fully policy-governed — policies act on registry operations at every stage:

**Sovereignty enforcement:**
```yaml
policy:
  type: gatekeeper
  target: registry_sync
  rule: "If resource_type.jurisdiction_compatibility NOT CONTAINS tenant.sovereignty_zone THEN reject_activation"
```

**Vendor allowlist:**
```yaml
policy:
  type: gatekeeper
  target: registry_activation
  rule: "If resource_type.publisher NOT IN approved_vendor_list THEN gatekeep: require_manual_approval"
```

**Bundle verification:**
```yaml
policy:
  type: gatekeeper
  target: registry_bundle_import
  rule: "If bundle.signature_valid == false THEN reject: unsigned bundles not permitted"
```

**Version pinning in production:**
```yaml
policy:
  type: gatekeeper
  target: registry_sync
  rule: "If active_profile == prod AND resource_type.version_delta.type == major THEN gatekeep: major version upgrades require manual approval"
```

**Audit all syncs:**
```yaml
policy:
  type: transformation
  target: registry_sync
  rule: "Always inject: sync_audit.required = true, sync_audit.reviewer = platform_admin"
```

### 7.5 Profile-Appropriate Registry Policy Groups

DCM ships built-in registry policy groups — one per profile, activated automatically:

| Group Handle | Profile | Key Behaviors |
|-------------|---------|--------------|
| `system/group/registry-minimal` | minimal | Advisory only; pull everything; no restrictions; warn on unverified sources |
| `system/group/registry-dev` | dev | Warn on unverified sources; pull Tier 1+2; no vendor restrictions |
| `system/group/registry-standard` | standard | Block unverified sources; Tier 1+2 only; sovereignty filter enabled |
| `system/group/registry-prod` | prod | Strict version pinning; approved vendor list; audit all syncs; major version manual approval |
| `system/group/registry-fsi` | fsi | Exact version pinning; approved vendor list; immutable sunset periods; all syncs audited with dual approval |
| `system/group/registry-sovereign` | sovereign | Signed bundles only; offline registry; no external connectivity; bundle verification required |

Organizations can replace or extend these groups using standard Policy Group composition.

---

## 8. DCM System Policies

| Policy | Rule |
|--------|------|
| `REG-001` | Resource Type proposals follow a PR-based GitOps workflow with automated validation gates (schema, FQN conflict, dependency resolution, breaking change detection) that must all pass before review begins. |
| `REG-002` | All registry changes require a minimum review period by change type and a mandatory shadow validation period in `proposed` status before promotion to `active`. |
| `REG-003` | Deprecation lifecycle is governed by default policies REG-DP-001 through REG-DP-007. These defaults are overridable via standard policy priority except where locked by active Profile. |
| `REG-004` | Version constraints in requests are strictly enforced. DCM never automatically upgrades across major versions regardless of version_policy. Version resolution policy is profile-governed. |
| `REG-005` | When multiple providers satisfy all placement criteria equally, the tie-breaking hierarchy applies: policy preference → provider priority → tenant affinity → cost analysis (if available) → least loaded → consistent hash on request_uuid. |
| `REG-006` | The registry uses a federated model. Air-gapped and sovereign deployments use offline registries populated via signed bundles verified against the organization's public key. |
| `REG-007` | The Registry Provider is policy-governed. Profile-appropriate registry policy groups are activated by default. Organizations may extend or replace these groups using standard Policy Group composition. |
| `REG-DP-001` | Default deprecation notification period: P30D before deprecation status is applied. Overridable. |
| `REG-DP-002` | Default sunset period: Tier 1 = P12M, Tier 2 = P6M. Overridable; locked as immutable in fsi and sovereign profiles. |
| `REG-DP-003` | Default migration window after retirement: P90D. Overridable. |
| `REG-DP-004` | Deprecation notices must declare a successor type or explicit migration guidance. Overridable. |
| `REG-DP-005` | Retired resource types reject new requests. Not overridable — structural. |
| `REG-DP-006` | Existing realizations of retired types enter DEPRECATED_RUNTIME state — eligible for modify and decommission, not rehydration. Overridable. |
| `REG-DP-007` | Emergency deprecation minimum migration window: P30D. Not overridable — floor cannot be removed. |

---

## 9. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should there be a certified registry tier between Tier 2 and DCM Core for formally audited types? | Ecosystem | ✅ Resolved — no fourth tier; certification metadata within existing tier structure serves same purpose (REG-008) |
| 2 | Should organizations be able to publish their Tier 3 types to the Verified Community registry? | Community | ✅ Resolved — Tier 3 to Tier 2 promotion via PR pathway with additional requirements: production deployment + OSS license + named maintainer + migration path (REG-009) |
| 3 | How does the Registry Provider handle a scenario where the upstream DCM Project Registry is permanently unavailable? | Resilience | ✅ Resolved — Organization Registry mirror is self-sufficient; upstream loss is governance decision not operational crisis; three long-term options (REG-010) |
| 4 | Should cost metadata on provider registrations be sourced from the Cost Analysis component or declared statically? | Architecture | ✅ Resolved — static or Cost Analysis sourcing; hybrid with Cost Analysis preferred; placement engine uses freshest available (REG-011) |

---

## 10. Related Concepts

- **Resource Type Hierarchy** (doc 05) — the structure of Resource Type Specifications
- **Policy Organization** (doc 14) — Policy Groups governing registry behavior
- **Deployment and Redundancy** (doc 17) — registry sync and offline operation
- **Auth Providers** (doc 19) — authentication for registry access
- **Universal Audit Model** (doc 16) — all registry operations produce audit records


## 11. Registry Governance Gap Resolutions

### 11.1 No Fourth Registry Tier — Certification Metadata Instead (Q1)

A formal fourth registry tier is not introduced. Resource Type Specifications in any tier may carry certification metadata from recognized certifying bodies. Certification provides equivalent assurance to a separate tier without the governance complexity.

```yaml
resource_type_spec:
  registry_tier: 2
  tier_certifications:
    - certifying_body: "OpenStack Foundation"
      certification: "OpenStack Powered"
      certified_versions: [">=2023.1"]
      certificate_ref: <uuid>
```

Users seeking "formally audited types" filter on certification metadata — same result as a separate tier, without the structural fragmentation.

### 11.2 Tier 3 to Tier 2 Promotion Pathway (Q2)

Organizations may promote Tier 3 Resource Type Specifications to Tier 2 (Verified Community) via the standard PR-based promotion pathway with additional requirements.

```yaml
tier_3_to_tier_2_promotion:
  requirements:
    - at_least_one_production_deployment: true
    - documented_use_case: true
    - open_source_license_compatible: true   # DCM is Apache 2.0
    - named_community_maintainer: true
    - test_suite_included: true
    - migration_path_from_tier3: documented  # handles name changes, schema diffs
  review_period: 14 days
  existing_tier3_users_notified: true        # current users notified of promotion
```

The promotion pathway gives organizations a route from internal tooling to community contribution without requiring a ground-up rewrite. The migration path documentation ensures existing Tier 3 deployments can upgrade smoothly.

### 11.3 Upstream Registry Permanently Unavailable (Q3)

The Organization Registry mirror operates independently from the upstream DCM Project Registry. Permanent upstream loss is a governance decision, not an operational crisis.

**Short-term:** Organization Registry mirror is self-sufficient for all operations. Existing types continue working normally.

**Medium-term:** Registry Provider enters "independent operation" mode — new Tier 1/2 types cannot be added (no upstream to sync from); existing types continue operating; Tier 3 unaffected (organization-governed).

**Long-term governance options:**
- **Option A:** Designate a community mirror as the new upstream (community self-governance)
- **Option B:** Fork the registry — organization takes ownership of their copy
- **Option C:** Continue as independent installation (no new community types)

The mirror's self-sufficiency means existing deployments never experience an operational outage due to upstream unavailability.

### 11.4 Provider Cost Metadata Source (Q4)

Provider cost metadata may be declared statically or sourced dynamically from the Cost Analysis component.

```yaml
provider_cost_metadata:
  source: <static|cost_analysis|hybrid>

  static:
    capex_allocation_per_unit: 12.50   # USD per VM-month
    opex_per_unit_per_hour: 0.08
    currency: USD
    last_updated: <ISO 8601>

  cost_analysis:
    query_interval: PT1H               # refresh cost data hourly
    fallback: static
    fallback_max_age: PT24H            # use static if Cost Analysis data older than 24h

  hybrid:
    prefer: cost_analysis
    static_for_unavailable: true
```

The placement engine's cost analysis step (tie-breaking step 4) uses whichever source is freshest and available — Cost Analysis preferred, static as fallback. No changes required to the placement tie-breaking model.

### 11.5 System Policies — Registry Governance Gaps

| Policy | Rule |
|--------|------|
| `REG-008` | A formal fourth registry tier is not introduced. Resource Type Specifications in any tier may carry certification metadata from recognized certifying bodies. Certification metadata is a filter criterion — not a structural tier boundary. |
| `REG-009` | Organizations may promote Tier 3 Resource Type Specifications to Tier 2 via the standard PR-based promotion pathway with additional requirements: at least one production deployment, OSS-compatible license, named community maintainer, and documented migration path from the Tier 3 handle. |
| `REG-010` | The Organization Registry mirror operates independently from the upstream DCM Project Registry. Permanent upstream unavailability does not affect existing operations. New community type adoption requires a designated community mirror, organizational fork, or independent operation decision. |
| `REG-011` | Provider cost metadata may be declared statically or sourced dynamically from the Cost Analysis component. Hybrid mode uses Cost Analysis when available and falls back to static. The placement engine uses whichever source is freshest and available. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
