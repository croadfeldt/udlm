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

This means a tenant-authored Validation policy is Organization/Tenant tier — it has lower inherent trust than a platform-authored policy at the same domain level, and may require additional review per the active profile. See [Federated Contribution Model](federated-contribution-model.md).

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

Resource Type Specifications use the two-axis versioning defined once in [`registry/VERSIONING.md`](../registry/VERSIONING.md) (the SPEC `conforms_to` axis + the ENTITY `Major.Minor.Revision` axis, and the semver change classification). This document does not restate that schema — it governs only **registry request-time resolution** (§4.2) and **profile defaults** (§4.3) below.

### 4.2 Version Resolution Policy

Version constraints in requests are **strictly enforced** — a conformant implementation MUST NEVER silently resolve to a different version than declared. The resolution policy governs how much flexibility a consumer has; its names map onto the constraint grammar in [`VERSIONING.md`](../registry/VERSIONING.md) (`compatible` ≡ `^` same-major, `latest_minor` ≡ `~` same-minor, `exact` ≡ a pinned version) — same concept, this is the request-time selector:

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

**A conformant implementation MUST NEVER automatically upgrade across major versions regardless of `version_policy`.** Moving from v1.x to v2.x always requires explicit consumer action.

### 4.3 Profile-Governed Version Policy Defaults

| Profile | Default Version Policy | Rationale |
|---------|----------------------|-----------|
| `homelab` | `latest` | Home lab — always current, no pinning overhead |
| `dev` | `compatible` | Dev — tracks major version, picks up fixes automatically |
| `standard` | `compatible` | Production — stable within major version |
| `prod` | `compatible` | Production — explicit major version control |
| `fsi` | `exact` | Regulatory — version-controlled for auditability |
| `sovereign` | `exact` | Maximum control — exact versions for reproducibility |

---

## 5. Deprecation Lifecycle (Contract)

### 5.1 The Default Deprecation Policy

The base `active → deprecated → retired` lifecycle is the universal deprecation model ([`foundations/layering-and-versioning.md`](../foundations/layering-and-versioning.md)); this section adds only the **registry-specific** timing and sunset policy (`REG-DP-*`). Those are governed by **default substrate policies** — not hard-coded values. These defaults can be overridden using the standard policy priority mechanism. Higher-priority organizational policies can shorten, extend, or lock any of these values.

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
    value: P90D           # 90 days after retirement — implementations enter DEPRECATED_RUNTIME
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
    name: "Behavior on retirement — existing implementations"
    value: deprecated_runtime_state
    # Existing implementations enter DEPRECATED_RUNTIME state:
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
  │  - All organizations with active implementations
  │  - All webhook registrations subscribed to registry events
  │
  ▼  Sunset period (P12M Tier 1 / P6M Tier 2 — per REG-DP-002)
  │  During sunset:
  │  - New requests: succeed with deprecation warning
  │  - Existing implementations: unaffected
  │  - Drift detection: continues
  │  - Provider implementations: remain valid
  │
  ▼  Retirement (status: retired)
  │  Existing implementations → DEPRECATED_RUNTIME state
  │  New requests → rejected (REG-DP-005)
  │
  ▼  Migration window (P90D — per REG-DP-003)
  │  Organizations migrate implementations to successor type
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
  type: validation
  enforcement_class: compliance
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

## 6a. Class-evolution gates — what the registry refuses about its own artifacts

The registry governs artifacts that other artifacts are compiled from. Under the scoped-Class
model (ADR-038 — Base, Type, and Provider Classes composed of shared data elements, with
portability derived from where an element sits), one Base element serves dozens of descendants,
so an edit to it is not a local change: it is a change to every flat spec generated from it and
every estate compiled against those. Software inheritance met this as the fragile-base-class
problem and never solved it in general, because behavioral compatibility is undecidable. Here it
is decidable — classes are data contracts, descendants are compiled artifacts, and the affected
set is computable — which is precisely why it should be gated rather than reviewed.

ADR-045 (class evolution and pinning — recompilation is atomic, intra-registry references are by
handle, organization-edge pins are `@version`/`@digest`-exact (ADR-051), and element scope is part
of the compatibility
contract) and ADR-046 (promotion happens on typed-output evidence, never on a version claim)
decide the *policy*. This section states what the registry **refuses**, in the four-part refusal
form the rest of the model uses — typed, actionable, non-leaking, auditable
([`contracts/error-model.md`](../contracts/error-model.md) §6a).

**A caveat that belongs at the top, not in a footnote.** Class artifacts do not exist in the
registry yet: there is no class-artifact schema, no class-compat classifier, and no estate-side
pin resolver. Those are the P0 substrate items of the class implementation plan
(`docs/design/scoped-class-hierarchy/implementation-plan.md`). `REG-011` through `REG-016` are
therefore **specification, not enforcement** — they state the contract the P0 gates must satisfy
when they are built, in the same way the rest of this repository specifies behavior that DCM
realizes. The honest-enforcement ledger is
[`foundations/data-model-core.md`](../foundations/data-model-core.md) §8, and none of these rules
claims `[enforced]`. Two of them describe checks that already run on the flat-spec plane and are
being generalized rather than invented, and both are called out where they apply.

**Version sufficiency (`REG-011`).** A change is classified by rule against the bump table
(`registry/VERSIONING.md` — what bumps what), and a bump smaller than the classification is
refused. This runs today for resource-type specs (`registry/tools/compat-check.py` via
`tests/ci_compat_gate.py`), and the class plane reuses the same classification rules rather than
growing a second, divergent notion of "breaking". What the class plane adds is the refusal's
content: the element, the classification, and the minimum bump that would be accepted. A refusal
that reports only "insufficient" leaves the maintainer to re-derive the classification the gate
already computed.

**Scope narrowing (`REG-012`).** Portability is derived from where an element sits, so moving an
element from Base scope to Type or Provider scope shrinks the portable surface of every type
that carried it — breaking, even though no schema shape changed. This is the class of break a
schema differ structurally cannot see: nothing about the field's declaration changed, only its
position. The gate implements the scope comparison explicitly, and the refusal enumerates the
types whose portable surface would shrink, since that set is the actual cost of the change and
is computable rather than a matter of judgment. Widening (Provider → Type, Type → Base) is
compatible.

**Pins, on two planes (`REG-013`, `REG-014`).** The industry mapping ADR-045 adopts is that the
registry is a library and an organization's estate is the application: libraries declare
compatible ranges and never pin; applications pin exactly and own their upgrades. Both halves
have a refusal.

Inside the registry, a class reference that pins a fixed version is refused — a single release
would then carry two truths of the same Base Class, which is version skew inside one source.
References are by handle and compile against the release's current version; the registry ref
(commit) is the sole intra-registry pin, and it pins everything at once (`registry/VERSIONING.md`,
registry-resolution scope). The refusal names the offending reference and the by-handle
correction, because the fix is a one-line edit and the maintainer should not have to look it up.

At the organization edge, pins are first-class — `thing@version` under the publish law, or
`thing@sha256:<hex>` for exact bytes (ADR-051) — and the distinction that matters
is between a pin that is *behind* and a pin that resolves to nothing. Behind is legal and carries
enumerated debt — the estate is deliberately conservative and the distance is reported per
artifact, never silent. Ahead of the consumed registry ref, or naming a revision that exists
nowhere in it, is refused: it claims verification against a registry that does not exist. This
same discipline already runs one plane over, on consumer manifests against type versions
(`tests/check_consumer_conformance.py` distinguishes ahead from unknown from behind with separate
messages), and generalizing it is the cheaper path than inventing new semantics.

**Promotion (`REG-016`).** Retiring pin debt means moving an estate from pinned revisions to
candidate ones, and ADR-046's ruling is that this happens on evidence: compile the organization's
intent corpus under both, at the same recorded corpus ref, and diff the declared typed outputs. A
diff that is neither empty nor explicitly approved refuses the promotion outright — nothing
partially promotes — and, because the diff contradicts the upstream compatibility claim, it
routes home as a finding with the diff as provenance. That upstream route is the part with no
carrier today: the promotion-evidence record has no schema today, and the finding-routing record's schema (`registry/finding-routing-record.schema.json`) lands as its own change — this rule binds regardless of carrier availability, and a refusal that cannot yet file the record queues the filing rather than dropping it. Formerly: neither record existed as a
registry kind, and ADR-046's Consequences names both as owed before P0 freezes. `REG-016` states
the refusal contract; the record shapes remain to be defined.

**Which of these an organization may loosen.** Adoption is governed twice: by the gates above,
which decide whether a change is *sound*, and by an organization's change policy, which decides
*when* it may be adopted — the window, the approvals, the expedite path. The two are not
equivalent and should not be loosenable on the same terms. A maintenance window is the
organization's to widen; refusing an out-of-window adoption is a scheduling decision, and its
refusal names the policy clause, the next window, and the authorization that would permit an
exception. An evidence gate is not the organization's to remove: a change policy amended to drop
the typed-output diff before promotion, or the version-sufficiency check before adoption, is
refused, because the gate's purpose is to protect against a claim the organization cannot
independently verify. Loosening the schedule accepts risk knowingly; removing the evidence
removes the ability to know. The change-control corpus
([`use-cases/change-control/`](../use-cases/change-control/README.md) cases 004 and 016) measures
both halves.

**Recording (`REG-015`).** Every rule above ends in "and the refusal is recorded", and today that
resolves to a CI log line and an exit code — which is not a record. A refused change and an
unattempted one are indistinguishable a week later, and the class-versioning corpus asks for the
refusal as a durable gate outcome in every one of its cases. `REG-015` defines one artifact all
registry gates emit, so that the recording story is uniform rather than per-gate.

---

## 7. UDLM System Policies

| Policy | Rule |
|--------|------|
| `REG-001` | Resource Type proposals follow an artifact-based workflow with automated validation gates (schema, FQN conflict, dependency resolution, breaking change detection) that must all pass before review begins. |
| `REG-002` | All registry changes require a minimum review period by change type and a mandatory shadow validation period in `proposed` status before promotion to `active`. |
| `REG-003` | Deprecation lifecycle is governed by default policies REG-DP-001 through REG-DP-007. These defaults are overridable via standard policy priority except where locked by active profile. |
| `REG-004` | Version constraints in requests are strictly enforced. A conformant implementation MUST NEVER automatically upgrade across major versions regardless of `version_policy`. Version resolution policy is profile-governed. |
| `REG-006` | The registry uses a federated model. Air-gapped and sovereign deployments use offline registries populated via signed bundles verified against the organization's public key. |
| `REG-007` | The Resource Type Registry is policy-governed. Profile-appropriate registry policy groups are activated by default. Organizations may extend or replace these groups using standard Policy Group composition. |
| `REG-008` | A formal fourth registry tier is not introduced. Resource Type Specifications in any tier may carry certification metadata from recognized certifying bodies. Certification metadata is a filter criterion — not a structural tier boundary. |
| `REG-009` | Organizations may promote Tier 3 Resource Type Specifications to Tier 2 via the standard promotion pathway with additional requirements: at least one production deployment, OSS-compatible license, named community maintainer, and documented migration path from the Tier 3 handle. |
| `REG-010` | The Organization Registry mirror operates independently from the upstream UDLM Project Registry. Permanent upstream unavailability does not affect existing operations. New community type adoption requires a designated community mirror, organizational fork, or independent operation decision. |
| `REG-011` | A declared version increment smaller than the classification the change earns is refused (`validation.version_bump_insufficient`). Classification is by rule against the bump table (`registry/VERSIONING.md`), never review judgment, and applies uniformly to resource-type specs, class artifacts, and provider surface declarations. The refusal names the **element**, the **classification**, and the **minimum sufficient bump**; a refused change regenerates nothing downstream. Pre-1.0, the accepted floor for a breaking classification is a MINOR bump, never a REVISION. |
| `REG-012` | Narrowing a class element's scope (Base → Type, Type → Provider) is classified **breaking** even when no schema shape changes, because the portable surface of every carrier shrinks with it; widening is compatible. The comparison is explicit gate logic — a schema differ cannot observe a position change. The refusal names the portability impact and enumerates the types whose portable surface the move would shrink. |
| `REG-013` | A class reference **inside** the registry that pins a fixed version is refused at validation (`validation.intra_registry_version_pin`): one release carrying two revisions of the same Base Class is version skew within a single source. Intra-registry references are by handle and compile against the release's current version; the registry ref is the sole intra-registry pin. The refusal names the offending reference, the single-truth rule, and the by-handle correction. |
| `REG-014` | An organization-edge pin that names a version or digest absent from the registry ref the estate declares it consumes is refused (`validation.pin_unresolvable`), typed distinctly from a pin that is legally behind. The refusal names the pinned reference and the registry ref it failed to resolve against. A pin carrying both `version` and `digest` must carry a matching pair per the pin manifest; a mismatch is refused and the digest is authoritative (ADR-051). Pins that are behind continue to validate, each emitting its version-distance as enumerated debt — behind is legal, never silent. |
| `REG-015` | Every registry or estate gate refusal emits a **durable gate-outcome record**: the artifact and change under evaluation, the rule that refused, the classification or comparison that justified it, the named correction, and the actor and time. A CI log line and an exit code are not a gate-outcome record — a refused change and an unattempted one must remain distinguishable after the job that produced them has aged out. The record is the registry-plane counterpart of the `REFUSE` audit record (`AUD-023`) and carries the same content discipline. |
| `REG-016` | Promotion of an estate from pinned to candidate revisions is refused when the typed-output diff between the two dry-run compilations is neither empty nor explicitly approved (`policy.promotion_diff_unapproved`). The refusal carries the diff, naming each changed output and the consumers bound to it; the estate remains wholly on its pinned revisions — nothing partially promotes. Because a dirty diff contradicts the upstream compatibility claim, the refusal also produces a finding routed to the registry with the diff as provenance. Both comparisons are computed at the same recorded corpus ref; a corpus that moved between them voids the comparison. |
| `REG-DP-001` | Default deprecation notification period: P30D before deprecation status is applied. Overridable. |
| `REG-DP-002` | Default sunset period: Tier 1 = P12M, Tier 2 = P6M. Overridable; locked as immutable in fsi and sovereign profiles. |
| `REG-DP-003` | Default migration window after retirement: P90D. Overridable. |
| `REG-DP-004` | Deprecation notices must declare a successor type or explicit migration guidance. Overridable. |
| `REG-DP-005` | Retired resource types reject new requests. Not overridable — structural. |
| `REG-DP-006` | Existing implementations of retired types enter DEPRECATED_RUNTIME state — eligible for modify and decommission, not rehydration. Overridable. |
| `REG-DP-007` | Emergency deprecation minimum migration window: P30D. Not overridable — floor cannot be removed. |

---

## 8. Related Concepts

- **Resource Type Hierarchy** ([../entities/resource-type-hierarchy.md](../entities/resource-type-hierarchy.md)) — the structure of Resource Type Specifications
- **Auth Providers** ([auth-providers.md](auth-providers.md)) — authentication for registry access
- **Universal Audit Model** ([../observability/universal-audit.md](../observability/universal-audit.md)) — all registry operations produce audit records
- **Federated Contribution Model** ([federated-contribution-model.md](federated-contribution-model.md)) — broader contribution pipeline for all artifact types

---

*UDLM substrate document. Implementation-specific registry enforcement, provider selection tie-breaking algorithms, artifact lifecycle storage and warning mechanisms, and review queue / approval workflow mechanics live in the consuming implementation's documentation.*
