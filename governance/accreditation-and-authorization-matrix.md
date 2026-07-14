# UDLM — Accreditation, Data Authorization Matrix, and Zero Trust

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Reference

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM substrate.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](../foundations/foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: DATA + POLICY**
>
> Data: Accreditation artifacts. Policy: Zero Trust posture as policy concern type.

**Related Documents:** [Resource/Service Entities](../entities/resource-service-entities.md) | [Layering and Versioning](../foundations/layering-and-versioning.md) | [Operational Models](../lifecycle/operational-models.md) | [Standards Catalog](../reference/standards-catalog.md)

---

> **Authentication Assurance Levels:** See [Standards Catalog](../reference/standards-catalog.md) for the NIST SP 800-63B AAL mapping per profile.

## 1. Purpose

This document defines three interconnected substrate models that together govern how a UDLM-conformant realization handles trust, data handling obligations, and compliance verification across all interaction boundaries:

1. **Accreditation Model** — how the substrate records, verifies, and enforces third-party compliance certifications for providers, policy engines, and peer realizations themselves
2. **Data/Capability Authorization Matrix** — what data and capabilities are permitted across any interaction boundary given a component's accreditation level and the data's classification
3. **Zero Trust Interaction Model** — the authentication, authorization, and verification requirements for every interaction, regardless of network position

These three models compose: Zero Trust verifies identity and authorization on every call. Accreditation verifies compliance certification status. The Authorization Matrix declares what is permitted given that certification status. Together they ensure that no interaction is implicitly trusted — every boundary crossing is verified against all three models.

---

## 1b. Accreditation and the Scoring Model

The substrate distinguishes two distinct accreditation functions:

**Required Accreditation (boolean gate):** Whether a provider holds a specific accreditation required for a particular request. PHI data requires an active BAA. This is a Governance Matrix enforcement — always boolean, never scored. A provider without the required accreditation is ineligible for that request regardless of any other score.

**Accreditation Richness (placement score):** The breadth and depth of a provider's accreditation portfolio. A provider with ISO 27001 + SOC2 Type II + FedRAMP Moderate + HIPAA BAA is preferable for placement over one with only self-declaration, all else equal. This is a continuous scoring signal — it does not gate eligibility, it influences preference among eligible providers.

Accreditation richness score contributes to:
1. Placement tie-breaking (a richer portfolio is preferred)
2. Request risk scoring (inversely — higher richness reduces provider risk contribution)

---

## 2. Data Classification

Data classification is a **first-class field-level metadata property** in the UDLM data model. Every field in every payload carries a `data_classification` value. This classification is the primary axis of the authorization matrix and is the key input to sovereignty and compliance enforcement.

### 2.1 Classification Levels (Closed Substrate Vocabulary)

| Level | Description | Examples |
|-------|-------------|---------|
| `public` | No restrictions; freely shareable | Resource display names, catalog item descriptions |
| `internal` | Organization-internal; not for external disclosure | Configuration details, operational metadata |
| `confidential` | Sensitive business data; restricted access | Cost data, business unit assignments |
| `restricted` | Highly sensitive; regulated or contractually protected | Security group IDs, network topology details |
| `phi` | Protected Health Information under HIPAA/HITECH | Patient IDs, diagnosis codes, treatment plans |
| `pci` | Payment Card Industry data under PCI-DSS | Cardholder data, authentication data |
| `sovereign` | Nationally classified or sovereignty-restricted data | Data subject to national security law |
| `classified` | Government-classified information | Classified defense or intelligence data |

### 2.2 Classification as Field Metadata

Every field in a payload carries data classification as part of its field metadata:

```yaml
field_definition:
  field_name: patient_record_id
  value: "PAT-00421"
  data_classification: phi
  classification_basis: "Contains patient identifier — HIPAA 45 CFR 164.514"
  metadata:
    override: immutable           # classification cannot be changed by policy
    locked_by: system/compliance/hipaa-field-classifier
```

**Classification is declared in three places:**
- **Resource Type Specification** — default classification per field for all instances of that type
- **Data Layer** — classification applied across a domain (e.g., an org layer that marks all `cost_center` fields as `confidential`)
- **Field-level override** — explicit classification on a specific field instance (highest precedence, immutable once set for `phi`, `sovereign`, `classified`)

### 2.3 Classification Immutability

Fields classified as `phi`, `sovereign`, or `classified` cannot be downgraded by any layer or policy — their classification is immutable once set. A Validation policy attempting to downgrade a PHI field MUST be rejected with a classification violation audit record.

---

## 3. Accreditation Model

### 3.1 What Accreditation Is

An **Accreditation** is a formal, versioned, time-bounded attestation that a substrate-managed component — a Service Provider, an External Policy Evaluator, a data store, a notification service, or a peer realization itself — satisfies the requirements of a specific compliance framework. Accreditations are issued by an **Accreditor** and registered as first-class artifacts.

Accreditation answers: **"Is this component certified to handle this type of data?"**

### 3.2 Accreditation Types and Trust Levels (Closed Substrate Vocabulary)

| Type | Issued By | Trust Level | Examples |
|------|-----------|-------------|---------|
| `self_declared` | Component itself | Lowest | Dev/homelab; provider asserts own compliance |
| `first_party` | Realization's own audit team | Low-Medium | Internal compliance review |
| `third_party` | Independent certifying body | High | ISO 27001, SOC 2 Type II |
| `qsa_assessment` | Qualified Security Assessor | High | PCI-DSS QSA report |
| `baa` | Legal BAA with covered entity | High | HIPAA Business Associate Agreement |
| `regulatory_certification` | Government regulatory body | Highest | FedRAMP P-ATO, DoD Provisional Authorization |
| `sovereign_authorization` | National sovereignty authority | Highest | National cloud authorization |

### 3.3 Accreditation Record Structure (Wire Contract)

```yaml
accreditation:
  # Standard artifact metadata
  artifact_metadata:
    uuid: <uuid>
    handle: "accreditations/providers/eu-west-prod-1/fedramp-high"
    version: "1.0.0"
    status: active
    owned_by: { display_name: "Compliance Team" }

  subject_uuid: <provider-uuid>          # what is being accredited
  subject_type: service_provider | external_policy_evaluation |
                credential_provider | peer_realization

  accreditation_type: <type from 3.2>
  framework: fedramp_high | fedramp_moderate | hipaa | pci_dss_v4 |
             iso_27001 | soc2_type2 | dod_il4 | dod_il5 | dod_il6 |
             sovereign | classified | <custom>

  accreditor:
    uuid: <uuid>
    name: "DISA" | "HHS OIG" | "PCI SSC" | "BSI" | <organization>
    type: government | regulatory_body | qsa | certification_body | internal | self
    contact_url: <url>

  # Validity
  issued_at: <ISO 8601>
  expires_at: <ISO 8601|null>            # null = perpetual until revoked
  renewal_warning_before: P90D
  last_verified_at: <ISO 8601>            # when the realization last confirmed still active

  # What the accreditation covers — EXPLICITLY keyed to provider + capability so the sovereignty
  # 1-1 match (UDLM ADR-004 §4) is machine-checkable. `subject_uuid` above names the PROVIDER; the
  # fields here name WHICH of that provider's capabilities and WHICH residency scope it attests.
  scope:
    # BINDING GRAIN is org/platform-admin policy (profile-governed — UDLM ADR-004 §4). UDLM carries all
    # three grains; the platform picks the required strictness and whether a capability change EXPIRES it:
    capability_scope:
      - capability_uuid: <uuid>                 # binds a specific capability (matches capabilities[].capability_uuid).
        version: "1.2.0"                        #   + version => GRAIN 3 (deterministic): a NEW capability version is not
                                                #   covered, so a change reverts the claim to self_asserted until re-attested.
        category: realize_resources/Compute     #   + category (OPTIONAL) narrows to one (verb × domain) category within it.
      # GRAIN 2 — capability_uuid WITHOUT version: attests that capability across versions (survives version bumps):
      #   - capability_uuid: <uuid>
      # GRAIN 1 — a single provider-wide entry (attests every capability; survives capability changes):
      #   - provider_wide: true
    geographic_scope: [US]                      # residency/jurisdiction this attests — the axis a
                                                #   sovereignty claim's jurisdictions/residency match against
    data_classifications: [phi, restricted]     # which data classifications this covers
    framework_capabilities: [data_at_rest, data_in_transit, access_control, audit_logging]  # compliance-framework capabilities — a DIFFERENT axis from capability_scope (renamed from `capabilities` to disambiguate)
    exclusions: [<explicit exclusions from scope>]

  # Evidence
  certificate_ref: <URL or internal document store reference>
  audit_report_ref: <URL or internal document store reference>
  external_registry_id: "FR2024-0042"    # e.g., FedRAMP Marketplace ID

  # Status
  status: active | suspended | revoked | expired | pending_renewal | pending_review
  revocation_reason: <string|null>
  revoked_at: <ISO 8601|null>

  # Automated verification
  verification:
    tier: external_registry | document_currency | contract_webhook | expiry_only
    stale_after: P7D                # max gap between verifications before stale_action fires
    stale_action: warn | suspend | escalate
    verification_failure_count: 0
```

### 3.3.1 The sovereignty 1-1 match key (provider × capability × jurisdiction)

An accreditation must be **explicit about what it attests, in terms of provider *and* capability** — otherwise a per-capability sovereignty claim (UDLM ADR-004 §4) cannot be evaluated. For a claim to be **trusted**, an **active accreditation** must match it **1-1** on three axes, all carried explicitly in §3.3:

- **provider** — `subject_uuid` == the claiming provider;
- **capability** — `scope.capability_scope` covers the claim's capability (by `capability_uuid`, optionally pinned to a `version` and/or narrowed to a `category` within it — or `provider_wide: true`);
- **jurisdiction / residency** — `scope.geographic_scope` covers the claim's `operating_jurisdictions` / `data_residency_zones`.

No accreditation matching **all three** → the claim is `self_asserted` and is **not honored** for sovereign/restricted placement (§3.1, ADR-022). Because `capability_scope` is explicit, a FedRAMP accreditation scoped to `realize_resources/Compute` does **not** silently vouch for the same provider's `realize_resources/Storage` — the two are matched independently. And because the *same* key is checked at every hop, this is what makes ADR-004 §4's **pipeline propagation** enforceable: each downstream hop in a capability's realization pipeline must present its **own** 1-1-matching accreditation for the propagated constraint — trust is re-verified per hop, never inherited.

**Binding grain + expiry are configurable (platform-admin policy, profile-governed).** How deterministic the capability axis must be is the org's choice, not a fixed rule (UDLM ADR-004 §4): **grain 1** provider-wide, **grain 2** a capability across its versions (`capability_uuid`, no `version`), or **grain 3** an exact `(capability_uuid, version)` — any grain optionally narrowed to a single `category` within the capability. At grain 3, when a provider changes a capability (a new `version`), the accreditation bound to the prior version **no longer matches** and the claim reverts to `self_asserted` until re-attested — the deterministic, drift-proof posture (e.g. sovereign/fsi profiles). Grains 1–2 are looser (e.g. dev/eval). The **`provider.capability_changed`** lifecycle event (`provider-contract.md` §6) fires accreditation re-evaluation; whether that change **expires** a binding is decided by the grain the platform requires — so the same event supports both the strict "expire on any change" and the loose "provider-wide, survives changes" postures.

### 3.4 Accreditation Lifecycle

```
Accreditation submitted
  │
  ▼ Validate structure and accreditor registration
  │
  ▼ status: proposed
  │   Shadow mode: compliance policies use this accreditation in shadow evaluation
  │   Platform admin reviews certificate_ref and audit_report_ref
  │
  ▼ Platform admin approves → status: active
  │   Accreditation now enforced in compliance checks
  │   All affected providers/deployments re-evaluated against new accreditation
  │
  ▼ Expiry monitoring:
  │   At expires_at - renewal_warning_before:
  │     notification.accreditation_expiring → Compliance Team, Platform Admin
  │   At expires_at:
  │     status → expired
  │     Providers relying on this accreditation flagged: ACCREDITATION_GAP
  │
  ▼ External status change detected:
  │   status → pending_review
  │   Platform Admin notified (urgency: high)
  │   Exception: external status = Revoked → immediate revocation (no review)
  │
  ▼ Revocation:
      Accreditor or Platform Admin revokes
      status → revoked
      All active provider interactions using this accreditation suspended
      notification.accreditation_revoked → Platform Admin (urgency: critical)
```

### 3.5 Accreditation Gap (Closed Vocabulary)

When a required accreditation is missing, expired, or revoked, the substrate enters an **Accreditation Gap** state for the affected provider:

```yaml
accreditation_gap_record:
  uuid: <uuid>
  provider_uuid: <uuid>
  required_framework: hipaa
  required_for: [phi data fields in active requests]
  gap_type: missing | expired | revoked | suspended | verification_stale
  detected_at: <ISO 8601>
  severity: critical                    # accreditation gaps are always high or critical
  affected_entity_uuids: [<uuid>, ...]  # entities currently hosted at this provider
  # Which axes of the sovereignty 1-1 match (§3.3.1) had no matching accreditation — so the gap is
  # diagnosable at the capability grain, not just "provider lacks framework X":
  unmet_capability:                     # the capability (and optional version/category) with no match
    capability_uuid: <uuid>
    version: <semver | null>            # set when the required grain is grain-3 (exact version)
    category: <verb × domain | null>    # set when the requirement is narrowed to one category
  unmet_jurisdiction: [<geographic scope required, e.g. US-MN>]
  policy_response: <from Recovery Policy>
  # Default: NOTIFY_AND_WAIT for fsi/sovereign; ESCALATE for standard/prod
```

### 3.6 Peer Realization Accreditation

Peer realizations themselves can carry accreditations — a FedRAMP-authorized realization deployment, for example. This enables cross-organization trust: a consuming organization's realization can verify the providing organization's realization holds the required accreditation before federating with it.

```yaml
deployment_accreditation:
  subject_type: peer_realization
  subject_uuid: <peer-instance-uuid>
  framework: fedramp_high
  # The peer realization itself is accredited, not just the providers it manages
```

---

> **Scope:** This document covers the accreditation model (Sections 2-3) and zero trust interaction model (Section 5). Data and capability boundary enforcement is specified in the [Unified Governance Matrix](governance-matrix.md), which consumes the accreditation and classification models defined here as inputs.

## 4. Data/Capability Authorization Matrix

### 4.1 Purpose

The Data/Capability Authorization Matrix declares what data fields and provider capabilities are permitted across any substrate-managed interaction boundary given the data's classification and the receiving component's accreditation level. It is the enforcement model that sits between compliance domain policies and the actual provider interaction.

### 4.2 Matrix as a Policy Artifact (Wire Contract)

The authorization matrix is a **Policy Group artifact** with `concern_type: data_authorization_boundary`. It is activated as part of the compliance domain group — enabling the HIPAA compliance domain automatically activates the HIPAA boundary matrix. Organizations extend or restrict matrices via their own policy groups at the Tenant level.

```yaml
data_authorization_matrix:
  artifact_metadata:
    uuid: <uuid>
    handle: "system/matrix/hipaa-provider-boundary"
    version: "1.0.0"
    status: active

  concern_type: data_authorization_boundary
  applicable_compliance_domains: [hipaa]

  # OUTBOUND: what the realization may send to a provider
  outbound_data_permissions:
    - data_classification: phi
      required_accreditation_type: baa
      required_accreditation_framework: hipaa
      on_missing_accreditation: DENY_REQUEST
      # DENY_REQUEST: block the entire request (PHI is required; cannot strip)
      # STRIP_FIELD: remove field and proceed (for optional PHI fields)
      # WARN_AND_ALLOW: allow but audit (dev profile only)

    - data_classification: restricted
      required_accreditation_type: third_party
      on_missing_accreditation: STRIP_FIELD

    - data_classification: internal
      required_accreditation_type: self_declared
      on_missing_accreditation: WARN_AND_ALLOW   # always has self_declared minimum

    - data_classification: [public, internal]
      required_accreditation_type: self_declared
      on_missing_accreditation: ALLOW

  # CAPABILITY: what operations the provider may perform on classified data
  capability_permissions:
    - capability: STORE_AT_REST
      data_classification: phi
      required_accreditation_type: baa
      required_scope: [data_at_rest]
      on_missing_accreditation: DENY_CAPABILITY

    - capability: REPLICATE_CROSS_REGION
      data_classification: phi
      required_accreditation_type: baa
      additional_requirement: replication_target_has_baa
      on_missing_accreditation: DENY_CAPABILITY

    - capability: EXPORT_TO_EXTERNAL_SYSTEM
      data_classification: [phi, restricted, sovereign]
      required_accreditation_type: regulatory_certification
      on_missing_accreditation: DENY_CAPABILITY

    - capability: PROVIDER_UPDATE_NOTIFICATION
      data_classification: phi
      required_accreditation_type: baa
      on_missing_accreditation: DENY_CAPABILITY

  # INBOUND: what the provider may return to the realization
  inbound_data_permissions:
    - data_classification: phi
      provider_must_strip_before_return: false
      consumer_visibility_requires_accreditation: baa
      stored_in_partition: realized_store_phi
      # PHI partition has additional encryption and access control
```

### 4.3 Federation Boundary Matrix

A dedicated matrix governs what crosses peer-to-peer federation boundaries:

```yaml
federation_boundary_matrix:
  artifact_metadata:
    handle: "system/matrix/federation-boundary"
  concern_type: data_authorization_boundary
  applicable_to: federation_tunnel

  outbound_data_permissions:
    - data_classification: sovereign
      on_missing_accreditation: DENY_REQUEST
      # Sovereign data NEVER crosses a federation boundary
      # This is a hard substrate constraint, not a configurable policy
      hard_constraint: true

    - data_classification: classified
      on_missing_accreditation: DENY_REQUEST
      hard_constraint: true

    - data_classification: phi
      required_accreditation_type: baa
      on_missing_accreditation: DENY_REQUEST

    - data_classification: restricted
      required_accreditation_type: third_party
      additional_requirement: remote_peer_holds_equivalent_accreditation
      on_missing_accreditation: STRIP_FIELD

    - data_classification: [public, internal]
      required_accreditation_type: self_declared
      on_missing_accreditation: ALLOW
```

### 4.4 Matrix Evaluation Contract (Substrate-Required)

The authorization matrix check MUST be a distinct evaluation step executed at every interaction boundary by any conformant realization:

```
Outbound interaction assembled (peer → Provider OR peer → peer)
  │
  ▼ Data Classification Inventory:
  │   For every field in the payload:
  │     Resolve data_classification (field metadata → layer → resource type spec default)
  │     Record classification → field mapping
  │
  ▼ Accreditation Resolution:
  │   Load active accreditations for the target component
  │   For each required classification level in the payload:
  │     Does the target hold an active, in-scope accreditation?
  │     Is the accreditation within its expires_at date?
  │
  ▼ Matrix Evaluation (per field):
  │   Look up data_classification × accreditation_level in active matrix
  │   Determine: ALLOW | STRIP_FIELD | DENY_REQUEST | DENY_CAPABILITY | WARN_AND_ALLOW
  │
  ├── All ALLOW → proceed
  │
  ├── STRIP_FIELD → remove field from payload; write FIELD_STRIPPED audit record
  │     If stripped field is required for service → escalate to DENY_REQUEST
  │
  ├── DENY_REQUEST → block interaction; entity enters PENDING_REVIEW
  │     notification.accreditation_gap dispatched to owner + platform admin
  │
  └── WARN_AND_ALLOW → proceed but write ACCREDITATION_ADVISORY audit record
                       (dev profile only; blocked in standard+)
```

---

## 5. Zero Trust Interaction Model

### 5.1 Principle

**Network position grants zero trust.** A component inside the substrate's control plane has no more implicit trust than one outside it. Every interaction — internal or external, synchronous or asynchronous — is authenticated, authorized, and verified as if the caller were an untrusted external party.

Zero trust in UDLM is not a network topology — it is a **per-interaction verification discipline** applied at every call, every event, every tunnel message.

### 5.2 The Five-Check Boundary Model (Substrate Contract)

Every interaction boundary MUST apply the following five checks in sequence. All five MUST pass:

```
Interaction attempt
  │
  ▼ Check 1: Identity Verification
  │   mTLS certificate verification (mutual — both sides present certificates)
  │   Certificate chain validation against registered trust anchor
  │   Certificate not in revocation list
  │   Hardware attestation (fsi/sovereign profiles with hardware_attested posture)
  │   → FAIL: connection refused; IDENTITY_VERIFICATION_FAILED audit record
  │
  ▼ Check 2: Authorization Verification
  │   Does this identity have explicit permission for this operation type?
  │   Is the presented credential scoped to this operation?
  │   Has this credential been revoked or expired?
  │   Does the scope match the minimum necessary for this call?
  │   → FAIL: 403 Forbidden; AUTHORIZATION_DENIED audit record
  │
  ▼ Check 3: Accreditation Check
  │   Does the target hold the required accreditation for the data classifications present?
  │   Is the accreditation current and not suspended?
  │   → FAIL: ACCREDITATION_GAP; recovery policy evaluates response
  │
  ▼ Check 4: Data/Capability Matrix Check
  │   Is each field permitted to cross this boundary?
  │   Is each capability permitted for this data classification?
  │   → FAIL: FIELD_STRIPPED or DENY_REQUEST per matrix declaration
  │
  ▼ Check 5: Sovereignty Check
  │   Is the target endpoint within the sovereignty boundary?
  │   Does the interaction violate any sovereignty constraints?
  │   → FAIL: SOVEREIGNTY_VIOLATION; platform admin notified
  │
  ▼ All checks pass → interaction proceeds
  │
  └── Audit record written regardless of outcome:
        INTERACTION_AUTHORIZED or INTERACTION_DENIED_{CHECK}
        All five check results recorded
        Credential UUID, interaction UUID for correlation
```

### 5.3 Credential Model — Scoped, Short-Lived, Non-Transferable

Zero trust requires that credentials are scoped to the minimum necessary operation and expire quickly:

```yaml
interaction_credential:
  credential_uuid: <uuid>
  issued_to: <component-uuid>
  issued_at: <ISO 8601>
  expires_at: <ISO 8601>             # short-lived; typically minutes to hour
  operation_scope:
    operation_type: dispatch | discovery | cancel | query | notify
    entity_uuid: <uuid>               # scoped to specific entity
    provider_uuid: <uuid>             # scoped to specific provider
  non_transferable: true              # cannot be delegated or relayed
  bound_to_ip: <IP|null>              # optional IP binding for fsi/sovereign
```

**Credential lifetime profile guidance (substrate defaults):**

| Profile | Max credential lifetime | Renewal model |
|---------|------------------------|---------------|
| minimal | PT8H | Manual or long-lived |
| dev | PT4H | Automatic refresh |
| standard | PT1H | Automatic refresh |
| prod | PT30M | Automatic refresh |
| fsi | PT15M | Automatic refresh; dual approval for elevation |
| sovereign | PT15M + hardware attestation | Hardware-bound; HSM-required |

### 5.4 Zero Trust Posture as a Policy Group Concern Type

`zero_trust_posture` is the sixth Policy Group concern type. Four posture levels (closed substrate vocabulary):

| Posture | Description | Profile Default |
|---------|-------------|----------------|
| `none` | No zero trust enforcement; perimeter model acceptable | minimal |
| `boundary` | Zero trust at external boundaries (consumer→peer, peer→provider); internal components trust service mesh | dev, standard |
| `full` | Zero trust everywhere including internal component communication; every call authenticated and authorized | prod, fsi |
| `hardware_attested` | Full zero trust plus hardware attestation (TPM/HSM); component identity backed by hardware | sovereign |

```yaml
zero_trust_policy_group:
  handle: "system/group/zt-full"
  concern_type: zero_trust_posture
  posture: full
  policies:
    - all_component_communication: mtls_required
    - credential_lifetime: PT30M
    - revocation_check: every_call          # not just at credential issuance
    - session_continuation: re_verify_PT15M # re-verify identity during long operations
    - failed_verification_response: terminate_and_alert
```

---

## 6. Federation Zero Trust — The Tunnel Model

### 6.1 Federation Tunnel as a Zero Trust Boundary

A federation tunnel between peer realizations is a **mutually authenticated, encrypted, scoped channel** where both sides verify each other on every interaction. It is not a VPN — it does not establish perimeter trust. Every message crossing the tunnel is authenticated, authorized, and subject to the five-check model.

**"Zero trust to any outside peer/provider"** is implemented by: the remote peer has no implicit access to local resources. Every cross-instance operation requires a scoped federation credential. The tunnel establishes secure transport — it does not establish trust.

### 6.2 Federation Tunnel Structure (Wire Contract)

```yaml
federation_tunnel:
  uuid: <uuid>
  local_peer_uuid: <uuid>
  remote_peer_uuid: <uuid>
  tunnel_type: peer | parent_child | hub_spoke
  trust_model: zero_trust               # always; non-negotiable

  # Mutual authentication
  authentication:
    protocol: mtls
    local_certificate_ref: <cert-uuid>
    remote_certificate_pin: <fingerprint>  # pinned; not just chain-valid
    trust_anchor: <CA-uuid>               # common or cross-signed CA
    certificate_rotation_interval: P90D
    revocation_check: ocsp_stapling       # real-time revocation check

  # Per-message signing
  message_integrity:
    signing_algorithm: ed25519
    local_signing_key_ref: <key-uuid>
    remote_verification_key_ref: <key-uuid>
    replay_protection: true               # nonce + timestamp window PT5M

  # What the remote peer may request from this peer (inbound)
  inbound_authorization:
    - operation: catalog_query
      permitted_resource_types: [Compute.VirtualMachine, Network.VLAN]
      requires_cross_tenant_authorization: true
    - operation: allocation_request
      permitted_resource_types: [Network.IPAddress]
      max_allocations_per_request: 10
      requires_cross_tenant_authorization: true

  # What this peer may request from the remote (outbound)
  outbound_authorization:
    - operation: placement_query
      permitted_resource_types: [Compute.VirtualMachine]
    - operation: realized_state_query
      permitted_entity_uuids: [<uuid>]   # scoped to specific entities

  # Data classification boundary (hard constraints)
  data_boundary:
    max_outbound_classification: restricted  # never send sovereign/classified
    max_inbound_classification: restricted
    # sovereign profile: max_*_classification: internal
    # classified profile: no federation permitted

  # Sovereignty scope
  sovereignty_scope:
    local_jurisdiction: EU
    remote_jurisdiction: EU
    cross_jurisdiction_permitted: false   # fsi/sovereign: always false
```

### 6.3 Federation Credential Scoping

Federation credentials are scoped to the specific operations declared in the tunnel authorization. A federation credential issued for `catalog_query` cannot be used for `allocation_request`:

```yaml
federation_credential:
  credential_uuid: <uuid>
  issued_by_peer_uuid: <local-uuid>
  issued_to_peer_uuid: <remote-uuid>
  expires_at: <ISO 8601>             # PT15M for fsi/sovereign
  operation_scope: catalog_query
  scoped_resource_types: [Compute.VirtualMachine]
  non_transferable: true
  tunnel_uuid: <uuid>                 # bound to specific tunnel
```

### 6.4 Zero Trust in Hub-Spoke Federation

In hub-spoke federation, a Hub peer coordinates Regional peers. Zero trust means:
- The Hub peer does not have root-level access to Regional peers — it has explicitly scoped federation credentials
- A Regional peer cannot impersonate the Hub to another Regional peer
- Cross-Regional operations route through the Hub with the Hub's authorization, not the originating Regional's authorization
- The Hub's accreditation is visible to Regional peers — Regionals can verify the Hub before accepting federation messages

```
RegionalPeer-A → HubPeer:  authenticated; scoped to allocation_request
HubPeer → RegionalPeer-B:  authenticated; scoped to realization_request
                            Hub presents its own credential to RegionalPeer-B
                            Not RegionalPeer-A's credential
RegionalPeer-B verifies:    Hub certificate; Hub accreditation; data classification boundary
```

---

## 7. Profile-Governed Zero Trust Posture (Substrate Defaults)

Zero trust posture defaults are bound to deployment profiles. The profile determines which zero trust posture group is active:

| Profile | Zero Trust Posture | Data Boundary | Federation |
|---------|-------------------|---------------|-----------|
| `minimal` | none | public/internal only | Not recommended |
| `dev` | boundary | up to confidential | Permitted with warnings |
| `standard` | boundary | up to restricted (with third-party accreditation) | Permitted |
| `prod` | full | up to restricted | Permitted with accreditation |
| `fsi` | full | up to restricted (with regulatory cert) | Restricted to same jurisdiction |
| `sovereign` | hardware_attested | sovereign stays sovereign (no crossing) | Zero crossing of sovereign data |

The `sovereign` profile enforces the hardest constraint: **sovereign-classified data MUST NEVER cross any boundary** — not to providers, not to federation tunnels, not to notification services with external endpoints. The enforcement is at the Data/Capability Matrix level as a `hard_constraint: true` rule that cannot be overridden by any policy.

---

## 8. UDLM System Policies

| Policy | Rule |
|--------|------|
| `ZT-001` | Network position grants zero trust. Every interaction is subject to the five-check model regardless of the caller's network location. |
| `ZT-002` | All substrate-managed interaction credentials are scoped, short-lived, and non-transferable. Credential lifetime is profile-governed. |
| `ZT-003` | Data classified as `sovereign` or `classified` never crosses any interaction boundary (provider dispatch, federation tunnel, notification delivery). This is a hard constraint enforced by the Data/Capability Matrix, not a configurable policy. |
| `ZT-004` | Federation tunnels use mutual TLS with certificate pinning and per-message signing. A tunnel establishes secure transport, not implicit trust. |
| `ZT-005` | Every interaction boundary check produces an audit record regardless of outcome. A denied interaction is audited as rigorously as a permitted one. |
| `ACC-001` | Accreditations are first-class artifacts. They follow the standard lifecycle (developing → proposed → active → deprecated → retired) and are subject to substrate governance. |
| `ACC-002` | Accreditation gaps (missing, expired, or revoked accreditations required for active interactions) are always high or critical severity. The Recovery Policy governs the response. |
| `ACC-003` | PHI, sovereign, and classified field classifications are immutable once set. No policy may downgrade these classifications. |
| `ACC-004` | The Data/Capability Authorization Matrix is enforced at every outbound interaction boundary before dispatch. Fields failing the matrix check are stripped (STRIP_FIELD) or the request is blocked (DENY_REQUEST) per the matrix declaration. |
| `ACC-005` | Peer realizations themselves carry accreditations. A federation peer can verify the remote peer deployment's accreditation before accepting federation messages. |
| `ACC-006` | `zero_trust_posture` is the sixth Policy Group concern type. Profile defaults are: minimal=none, dev/standard=boundary, prod/fsi=full, sovereign=hardware_attested. |

---

*UDLM substrate document. Realization-specific accreditation governance enforcement, authorization evaluation runtime, zero trust boundary implementation, federation tunnel establishment and maintenance, and profile-governed accreditation enforcement live in the consuming realization's documentation.*
