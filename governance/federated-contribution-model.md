# UDLM — Federated Contribution Model

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Reference — Read This First for Multi-User Data Governance
**Related Documents:** [Foundational Abstractions](../foundations/foundations.md) | [Layering and Versioning](../foundations/layering-and-versioning.md) | [Registry Governance](registry-governance.md) | [Governance Matrix](governance-matrix.md) | [Authority Tier Model](authority-tier-model.md)

> **This document maps to: DATA + POLICY + PROVIDER**
>
> The federated contribution model governs how Data artifacts are created and managed across all contributor types. It extends the Data abstraction with explicit contributor identity, applies Policies to govern contribution permissions and review requirements, and uses the Provider abstraction for cross-peer federation of contributions.

---

> **Authority Tier Reference:** Contribution approval tiers (`reviewed`, `verified`, `authorized`) are named positions in the [Authority Tier Model](authority-tier-model.md) ordered list. Organizations may add custom tiers between existing ones. Changes to the tier registry that affect contribution approval requirements trigger impact detection (ATM-009–ATM-012).

## 1. Purpose and Principle

A UDLM realization is a multi-user, multi-contributor system. Platform admins are not the only actors who create data. Consumers define their own service configurations, resource groups, and policy overlays. Service Providers publish their own resource type specs and catalog items. Peer realizations contribute registry entries across federation boundaries. Organizations extend with their own artifact types.

**The federated contribution model** is the substrate framework for how all of these actors create, review, activate, and lifecycle-manage data artifacts. It extends the Data abstraction with one additional universal property:

> **Every UDLM data artifact has a contributor** — an actor or system that authored it — and that contributor's role determines what review is required before the artifact becomes active.

This is not a special model for special cases. It is the same artifact lifecycle (developing → proposed → active → deprecated → retired), and the same domain precedence (system → platform → tenant → resource_type → entity) — applied consistently across all contributor types.

**The core substrate principle:** UDLM defaults to a federated model for data creation, import, usage, and lifecycle. Every authorized actor can contribute within the bounds their role permits. The Governance Matrix governs the boundaries. Profile-bound auto-approval policies determine what needs human review and what does not.

The specific transport (GitOps PR, REST API, message bus) is a realization choice. The substrate requires only that there be a reviewable, auditable contribution channel that honors the contributor permission table and the universal pipeline.

---

## 2. Contributor Types and Permissions (Substrate Contract)

### 2.1 The Four Contributor Types (Closed Substrate Vocabulary)

| Contributor | Examples | Default domain scope |
|-------------|---------|---------------------|
| **Platform Admin** | Realization operators, SRE team | system, platform — all artifact types |
| **Consumer / Tenant** | Application teams, developers, Tenant admins | tenant — scoped to their Tenant |
| **Service Provider** | Infrastructure teams, automation platforms | provider — resource types they offer |
| **Peer Realization** | Federated peer realizations, Hub peer, community registry | federated — governed by federation trust posture |

### 2.2 What Each Contributor Can Contribute

**Platform Admin:** All artifact types at all domain levels. No restrictions within the local deployment.

**Consumer / Tenant:**
- Tenant-domain policies (GateKeeper, Transformation, Recovery, Lifecycle, Orchestration Flow)
- Resource groups and group memberships within their Tenant
- Notification subscriptions for their Tenant
- Webhook registrations for their Tenant
- Custom catalog item definitions (within their Tenant's resource type scope)
- Tenant-scoped data layers (Request Layer — directly attached to their requests)
- Cross-tenant authorization records (requires counterpart Tenant acceptance)

**Service Provider:**
- Resource Type Specifications for resource types they offer (Organization or Verified Community tier)
- Provider Catalog Items for their registered resource types
- Service Layers for their offered resource types
- Provider-specific GateKeeper and Validation policies (provider domain)
- Cost metadata updates
- Sovereignty declaration updates

**Peer Realization:**
- Registry entries (Resource Type Specs, provider type definitions) contributed through federation channels
- Policy bundles contributed through verified federation relationships
- Layer contributions through Hub-governed federation
- Accreditation vouching for providers registered with the contributing peer

### 2.3 What Each Contributor Cannot Contribute

| Contributor | Cannot contribute |
|-------------|-----------------|
| Consumer | System or platform domain policies; core layers; resource type specs (unless granted elevated role); provider catalog items for other providers |
| Service Provider | Policies outside their resource type domain; core layers; other providers' catalog items; tenant-domain policies for specific Tenants |
| Peer Realization | Artifacts above the federation trust level granted; system-domain policies without authorized approval; sovereignty zones for jurisdictions not in their declared scope |

---

## 3. Contribution Artifact Types (Substrate Permission Matrix)

Every UDLM data artifact type has a declared set of contributor permissions. The following matrix is normative:

| Artifact Type | Platform Admin | Consumer/Tenant | Service Provider | Peer Realization |
|--------------|---------------|-----------------|-----------------|---------|
| Resource Type Specification | All tiers | ❌ | Org + Community tiers | Community tier (via federation) |
| Provider Catalog Item | All | ❌ | Their resource types only | ❌ |
| Core Layer | ✅ | ❌ | ❌ | ❌ |
| Service Layer | ✅ | ❌ | Their resource types only | ❌ |
| Request Layer | ✅ | Their requests only | ❌ | ❌ |
| GateKeeper Policy | All domains | Tenant domain only | Provider domain only | Via federation governance |
| Transformation Policy | All domains | Tenant domain only | Provider domain only | Via federation governance |
| Recovery Policy | All domains | Tenant domain only | Provider domain only | Via federation governance |
| Orchestration Flow Policy | All domains | Tenant domain only | ❌ | ❌ |
| Governance Matrix Rule | All domains | Tenant domain only | ❌ | ❌ |
| Lifecycle Policy | All domains | Tenant domain (on their entities) | ❌ | ❌ |
| Accreditation | All | ❌ | Their own accreditations | Vouching for their providers |
| Sovereignty Zone | ✅ | ❌ | ❌ | ❌ |
| Group / Resource Group | All | Tenant domain only | ❌ | ❌ |
| Notification Subscription | All | Their Tenant only | ❌ | ❌ |
| Webhook Registration | All | Their Tenant only | ❌ | ❌ |

---

## 4. The Universal Contribution Pipeline (Substrate Contract)

All contributions — regardless of contributor type — MUST flow through the same substrate pipeline. What varies is:
- **The target store** (which artifact repository receives the contribution)
- **The review requirement** (auto-approval vs human review vs dual approval)
- **The shadow mode behavior** (policies enter shadow mode automatically; other artifacts enter proposed status)

### 4.1 The Pipeline

```
Contributor authors a data artifact
  │
  │ Via a contribution surface offered by the realization
  │ (GUI, API, source-control PR, message bus, etc.)
  │
  ▼ Artifact submitted → status: developing (local only)
  │
  ▼ Contributor submits for review → status: proposed
  │   For policies: shadow mode activates automatically
  │   For other artifacts: staged in proposed state
  │
  ▼ Governance Matrix evaluates the contribution:
  │   Is this contributor permitted to contribute this artifact type?
  │   Is the artifact in the correct domain for this contributor?
  │   Does the artifact pass structural validation?
  │   DENY → rejected with reason; no further processing
  │
  ▼ Review flow (per profile + artifact type):
  │   auto:         artifact activates immediately
  │   reviewed:     one platform admin or designated reviewer approves
  │   verified:     two independent reviewers approve
  │   authorized:   N members of declared authority group record decisions
  │
  ▼ On approval → status: active
  │   For policies: shadow mode results reviewed; full enforcement begins
  │   For resource type specs: available in registry
  │   For catalog items: visible in service catalog (per RBAC)
  │
  ▼ Lifecycle managed by contributor (deprecate, retire)
      Subject to platform admin override at any time
```

### 4.2 Review Requirements by Contributor and Artifact Type (Substrate Defaults)

Review requirements are profile-governed. The substrate defaults are:

| Artifact Type | Platform Admin | Consumer/Tenant | Service Provider |
|--------------|---------------|-----------------|-----------------|
| Tenant-domain policy | auto | reviewed (standard+) | reviewed |
| Resource Type Spec (Org tier) | auto | ❌ | reviewed |
| Resource Type Spec (Community tier) | reviewed | ❌ | verified |
| Provider Catalog Item | auto | ❌ | reviewed |
| Service Layer | auto | ❌ | reviewed |
| Governance Matrix Rule (tenant) | auto | verified | ❌ |
| Governance Matrix Rule (platform) | reviewed | ❌ | ❌ |
| Accreditation | reviewed | ❌ | reviewed |

**Profile override pattern (defaults):**
- `dev`: most contributions auto-approved; shadow mode optional
- `standard`: consumer policies require reviewed; provider specs require reviewed
- `prod`: consumer governance matrix rules require verified; provider specs require verified
- `fsi`: all contributions require verified; community registry entries require authorized
- `sovereign`: all contributions require authorized approval

---

## 5. Consumer Contribution Model (Contract)

### 5.1 Consumer as Policy Author

Consumers are not passive requesters. Tenant admins and designated Tenant members with `policy_author` role can define and maintain their own Tenant-domain policies directly.

**What this enables:**
- A Payments team defining their own cost ceiling GateKeeper: "Reject any VM request over $500/month"
- An Operations team defining their own expiry Transformation: "All dev VMs get a 30-day TTL injected"
- A Security team defining their own governance matrix rule: "Our Tenant never sends confidential data to unaccredited providers"

**The scope constraint MUST be enforced by the substrate, not by convention.** When a consumer submits a policy with `domain: tenant`, the realization MUST validate that the contributing actor belongs to that Tenant. Attempts to submit platform or system domain policies MUST be rejected by the Governance Matrix at contribution time.

### 5.2 Consumer Contribution Wire Shape (Normative)

```
POST /api/v1/contribute/policy

Authorization: Bearer <token>
X-Tenant: <tenant-uuid>

{
  "policy_type": "gatekeeper",
  "handle": "tenant/payments/gatekeeper/cost-ceiling",
  "domain": "tenant",
  "concern_type": "operational",
  "enforcement": "soft",
  "match": {
    "payload_type": "request.policies_evaluated",
    "conditions": [
      { "field": "payload.cost_estimate.per_month", "operator": "gt", "value": 500 }
    ]
  },
  "output": {
    "decision": "deny",
    "reason": "Estimated monthly cost exceeds Tenant budget ceiling of $500"
  },
  "shadow_mode": true,           # start in shadow mode (proposed status)
  "commit_message": "Add monthly cost ceiling GateKeeper for Payments Tenant"
}

Response 202 Accepted:
{
  "contribution_uuid": "<uuid>",
  "artifact_type": "policy",
  "policy_handle": "tenant/payments/gatekeeper/cost-ceiling",
  "status": "proposed",
  "shadow_mode": true,
  "review_required": true,
  "review_type": "reviewed",
  "reviewer_group": "platform-admins",
  "shadow_results_url": "/.../shadow/<policy_uuid>"
}
```

---

## 6. Service Provider Contribution Model (Contract)

### 6.1 Provider as Resource Type Publisher

**Resource Type Authority vs Service Provider Publisher — the distinction:**

The **Resource Type Authority** is the team responsible for defining and maintaining the Resource Type Specification — the vendor-neutral contract all providers must implement. The authority may be a UDLM project maintainer (Tier 1), a named community maintainer (Tier 2), or an organization's domain team (Tier 3).

A **Service Provider** implements that specification in their Catalog Item and publishes provider-specific extensions and Service Layers on top of it. A provider is the publisher of their catalog item — not necessarily the author of the underlying Resource Type Spec.

In many cases they are the same team: a networking team may both define `Network.VLAN` as the Resource Type Authority AND register as the Service Provider that realizes VLANs. In other cases they are different: a platform team defines `Compute.VirtualMachine` as the Resource Type Authority, and multiple compute providers each independently register Catalog Items implementing that specification.

Service Providers are first-class contributors of the resource type definitions that consumers request. A provider registering a new virtual machine offering publishes the Resource Type Specification, the Catalog Item, and the Service Layer that consumers use to interact with it.

Provider contributions flow through the same registry governance as all other registry entries — submitted, reviewed per profile requirements, activated when approved.

### 6.2 Provider Contribution Wire Shape (Normative)

```
POST /api/v1/provider/contribute/resource-type-spec

Authorization: mTLS + provider credential

{
  "resource_type_fqn": "Storage.DistributedVolume",
  "tier": "organization",
  "version": "1.0.0",
  "schema": {
    "fields": [
      { "field_name": "capacity_gb", "type": "integer", "required": true },
      { "field_name": "replication_factor", "type": "integer",
        "default": 3, "constraint": { "min": 1, "max": 5 } },
      { "field_name": "encryption_at_rest", "type": "boolean", "default": true }
    ]
  },
  "portability_class": "provider_specific",
  "commit_message": "Publish DistributedVolume resource type v1.0.0"
}

Response 202 Accepted:
{
  "contribution_uuid": "<uuid>",
  "resource_type_fqn": "Storage.DistributedVolume",
  "status": "proposed",
  "review_required": true,
  "review_type": "reviewed"
}
```

### 6.3 Provider Service Layer Contribution

Providers contribute Service Layers that are applied during request assembly for their resource types:

```
POST /api/v1/provider/contribute/service-layer

{
  "resource_type_fqn": "Compute.VirtualMachine",
  "layer_handle": "providers/eu-west-prod-1/layers/vm-defaults",
  "layer_domain": "service",
  "provider_uuid": "<uuid>",
  "version": "2.0.0",
  "fields": {
    "hypervisor": { "value": "KVM", "metadata": { "override": "immutable" } },
    "network_segment": { "value": "prod-segment-01" },
    "backup_enabled": { "value": true }
  }
}
```

---

## 7. Federation Contribution Model (Contract)

### 7.1 Peer Realization as Contributor

A federated peer realization is a contributor to the receiving realization's artifact stores, subject to the federation trust posture. This enables:

- **Hub realization contributing policy templates** to Regional peers — standard compliance policies distributed from a central Hub
- **Community registry contributions** — a community-maintained peer publishing Verified Community resource type specs to subscribing organizations
- **Provider contributions across peer boundaries** — a provider registered with Peer-A contributing its resource type specs to Peer-B through a verified federation relationship

### 7.2 Federation Contribution Trust Model (Closed Vocabulary)

Federation contributions inherit the federation trust posture of the contributing peer:

| Peer trust posture | Contribution review requirement | Artifact types permitted |
|-------------------|--------------------------------|------------------------|
| `verified` | reviewed (standard+); auto (dev) | Registry entries, policy templates, service layers |
| `vouched` | reviewed always | Registry entries, service layers only |
| `provisional` | `authorized` tier approval | Registry entries only (no policies) |

**Hard substrate rule:** A peer realization MUST NOT contribute artifacts at a higher domain level than its trust posture permits. A `vouched` peer cannot contribute system-domain policies. This is enforced by the Governance Matrix at the federation contribution boundary.

### 7.3 Federation Contribution Flow

```
Peer realization publishes a contribution bundle:
  Content: resource type specs, policy templates, or layers
  Transport: federation tunnel (mTLS, signed, scoped credential)
  Metadata: contributing_peer_uuid, trust_posture, artifact_list

Receiving realization evaluates:
  1. Governance Matrix: is this peer permitted to contribute this artifact type?
  2. Signature verification: bundle signed by peer's private key?
  3. Structural validation: artifacts conform to substrate schemas?
  4. Domain scope check: artifacts within peer's permitted domain?

On validation pass:
  Artifacts enter proposed status in receiving realization's policy/registry store
  Review flow per receiving realization's profile + peer trust posture

On approval:
  Artifacts become active in receiving realization
  Source attribution: contributed_by.peer_uuid, contributed_by.trust_posture
```

### 7.4 Hub Policy Distribution (Contract)

In a Hub-Spoke federation, the Hub peer is the authoritative source for platform-wide policy templates. Regional peers subscribe to the Hub's policy distribution feed:

```yaml
hub_policy_distribution:
  hub_peer_uuid: <uuid>
  distribution_type: push          # Hub pushes on policy change
  auto_approve_from_hub:           # profile-governed; security-first: prod+ always requires review
    minimal: true
    dev: true
    standard: true
    prod: false         # reviewed required even from verified Hub
    fsi: false          # verified required
    sovereign: false    # authorized approval required
  policy_handles_subscribed:
    - "system/compliance/hipaa/*"
    - "system/governance/drift-remediation"
  # Regional peer always reviews before activating
  # Hub cannot force-activate policies on Regional peers
```

---

## 8. Artifact Lifecycle Across Contributors

### 8.1 Contributor Ownership and Transfer

Every artifact is owned by its contributor at creation. Ownership can be transferred:
- Consumer-authored policies transfer to a new Tenant admin when the original actor departs
- Provider-contributed catalog items remain owned by the provider registration
- Federation-contributed artifacts are owned by the contributing peer realization

Ownership transfer requires the receiving owner's explicit acceptance (same model as entity ownership transfer in the Consumer API).

### 8.2 Platform Admin Override

Platform admins can override any contributor's artifact lifecycle at any time:
- Suspend an active consumer-authored policy that is causing harm
- Retire a provider-contributed resource type spec that is no longer safe
- Reject a proposed federation contribution without providing a public reason (security discretion)

Override actions MUST always be audited with the overriding admin's actor UUID and reason.

### 8.3 Deprecation and Sunset

Contributors deprecate their own artifacts. When a Service Provider deprecates a resource type spec:
1. All consumers using that type receive deprecation notifications
2. A sunset period is declared (minimum: P30D for standard profile; P90D for prod/fsi/sovereign)
3. During sunset: new requests using the deprecated spec are warned; existing resources unaffected
4. After sunset: new requests using the deprecated spec are blocked
5. Platform admin must confirm final retirement

### 8.4 Orphaned Artifacts

When a contributor's access is revoked (actor departs, provider deregisters, peer federation ends):
- Active artifacts remain active — orphaned artifacts do not automatically deactivate
- A platform admin is notified: "Artifact tenant/payments/gatekeeper/cost-ceiling has no active owner"
- Platform admin assigns a new owner or explicitly retires the artifact
- Auto-retire-on-orphan is configurable per profile (enabled in sovereign profile; disabled in standard)

---

## 9. Contributor Attribution (Wire Contract)

Every artifact MUST include a `contributed_by` block in its artifact metadata. Shape is normative:

```yaml
artifact_metadata:
  uuid: <uuid>
  handle: "tenant/payments/gatekeeper/cost-ceiling"
  version: "1.0.0"
  status: active
  contributed_by:
    contributor_type: consumer       # platform_admin | consumer | service_provider | peer_realization
    actor_uuid: <uuid>               # for consumer/platform_admin contributions
    tenant_uuid: <uuid>              # for consumer contributions
    provider_uuid: <uuid>            # for provider contributions
    peer_uuid: <uuid>                # for federation contributions
    contribution_method: api         # realization-specific (api | gui | git_pr | federation_push | ...)
    pr_url: "https://..."            # if submitted via a source-control PR
    reviewed_by: [<actor_uuid>]      # actors who approved
    reviewed_at: <ISO 8601>
```

---

## 10. UDLM System Policies

| Policy | Rule |
|--------|------|
| `FCM-001` | Every UDLM data artifact has a contributor. The contributor is recorded in `artifact_metadata.contributed_by` at creation and is immutable. |
| `FCM-002` | Contributor permissions are enforced by the Governance Matrix at submission time. Domain scope violations are hard DENY — they cannot be overridden by the contributor. |
| `FCM-003` | All contributions flow through the universal pipeline. No contributor can write directly to the authoritative artifact store without review (unless the active profile grants auto-approval for that contributor type and artifact type combination). |
| `FCM-004` | Policies submitted by any contributor enter proposed (shadow) status by default. Shadow mode results must be available before the active profile's shadow review period expires. |
| `FCM-005` | Platform admins may override any contributor's artifact lifecycle at any time. Override actions are audited. |
| `FCM-006` | Orphaned artifacts (contributor access revoked) do not automatically deactivate. A platform admin assigns a new owner or explicitly retires them. Exception: sovereign profile auto-retires orphaned artifacts. |
| `FCM-007` | Federation contributions from peer realizations are scoped by the peer's federation trust posture. Verified peers: reviewed (standard+). Vouched peers: reviewed always. Provisional peers: authorized approval. |
| `FCM-008` | Contributor-tier scope limits are absolute. A consumer-authored policy in the tenant domain cannot affect the system or platform domain regardless of the policy's declared match conditions. |

---

*UDLM substrate document. Realization-specific contribution store structure, review queue / approval workflow mechanics (GitOps PR transport, branch protection rules), contribution pipeline orchestration, consumer/provider contribution enforcement code, and federation contribution synchronization mechanics live in the consuming realization's documentation.*
