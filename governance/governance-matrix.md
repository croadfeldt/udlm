# DCM Data Model — Unified Governance Matrix


**Document Status:** ✅ Complete
**Document Type:** Architecture Reference

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: POLICY**
>
> The Policy abstraction — Governance Matrix Rule output schema for boundary control


**Related Documents:** [Federated Contribution Model](28-federated-contribution-model.md) | [Accreditation and Authorization Matrix](26-accreditation-and-authorization-matrix.md) | [DCM Federation](22-dcm-federation.md) | [Policy Profiles](14-policy-profiles.md) | [Layering and Versioning](03-layering-and-versioning.md) | [Control Plane Components](25-control-plane-components.md)

---

> **Federated Contribution:** The Governance Matrix enforces contributor permission boundaries at artifact submission time. See the [Federated Contribution Model](28-federated-contribution-model.md) for the complete contributor permission table and the hard DENY rules applied to out-of-scope contributions.

## 1. Purpose

The Unified Governance Matrix is the **single, declarative, multi-dimensional control surface** that governs every cross-boundary interaction in DCM. It answers one question at every interaction point:

> **Given this subject, this data, this target, and this context — is this interaction permitted, and under what conditions?**

Previous DCM documents established several overlapping control mechanisms: the Data/Capability Authorization Matrix (doc 26), sovereignty constraints in federation tunnels (doc 22), BBQ-001 sovereignty checks (doc 14), and profile-governed data boundaries. The Governance Matrix unifies all of these into a single model with a single evaluation algorithm and a single enforcement point.

The accreditation model and data classification model from doc 26 are inputs to the evaluation algorithm defined here. The accreditation model (Sections 2-3 of doc 26) and the zero trust interaction model (Section 5 of doc 26) remain current — the Governance Matrix consumes them as inputs.

**Key properties of the Governance Matrix:**

- **Fine-grained to broad** — rules can target a single field path on a specific entity, or broadly govern all data of a given classification. Both are first-class citizens of the same model.
- **Profile-bound defaults** — every deployment profile ships with sensible default rules that are immediately operative. Operators configure overrides rather than building from scratch.
- **Hard and soft enforcement** — hard rules cannot be relaxed by any downstream rule. Soft rules establish defaults that can be tightened but never relaxed.
- **Single evaluation algorithm** — every interaction boundary runs the same algorithm against the same rule set. No parallel enforcement paths.
- **Audited always** — every evaluation produces an audit record regardless of outcome.

---


## 1b. Governance Matrix and the Scoring Model

The Governance Matrix is **always boolean**. This is not a design limitation — it is an explicit architectural decision.

Governance Matrix decisions (ALLOW, DENY, ALLOW_WITH_CONDITIONS, STRIP_FIELD, REDACT, AUDIT_ONLY) govern whether data may cross a boundary. These are regulatory and legal facts — PHI either crosses a compliant boundary or it doesn't. "Mostly compliant" is not a legal defense. No Governance Matrix Rule may declare `scoring_weight` or `enforcement_class`.

**The Governance Matrix fires before the Scoring Model evaluates.** If a Governance Matrix Rule produces DENY, the request is halted and no risk score is calculated. The score pipeline only runs for requests that have already passed all Governance Matrix checks.

This ensures that scoring cannot be used to route around data sovereignty or regulatory boundaries. See [Scoring Model](29-scoring-model.md) Section 8 for the full pipeline sequence and SMX-004.


## 2. The Four Matrix Axes

Every governance matrix rule is expressed as a match across four axes. A rule fires when all declared axis conditions are satisfied.

### 2.1 Axis 1 — Subject (Who)

The subject is the entity initiating or involved in the interaction.

```yaml
subject:
  type: <subject_type>
  # Subject types:
  # actor                — human or service account making a request
  # service_provider     — Service Provider sending/receiving data
  # dcm_peer             — federated DCM instance
  # external_policy_evaluation      — External Policy Evaluator receiving payload data for evaluation
  # (prescribed infrastructure)     — data store receiving/returning state data
  # service_provider — notification service receiving notification envelopes
  # information_provider — Information Provider returning external data
  # system               — DCM internal component (Request Orchestrator, etc.)

  identity:
    provider_uuid: <uuid>              # specific provider instance
    dcm_peer_uuid: <uuid>              # specific federated DCM instance
    trust_posture: <verified|vouched|provisional>  # for dcm_peer subjects
    accreditation_level: <type>        # accreditation type the subject holds
    actor_role: <role>                 # for actor subjects

  tenant:
    uuid: <uuid>                       # specific Tenant
    match: any_tenant | cross_tenant | system_tenant
```

### 2.2 Axis 2 — Data (What)

The data axis declares what is being accessed, sent, or operated on. This is where field-level granularity lives.

```yaml
data:
  # Broad controls — classification level
  classification:
    match: <exact> | in: [<list>] | minimum: <level> | maximum: <level>
    # minimum: restricted means restricted and above (phi, sovereign, classified)
    # maximum: internal means internal and below (public, internal)

  # Resource-type scoping
  resource_type:
    match: <fqn> | category: <category> | any

  # Fine-grained controls — specific field paths
  field_paths:
    mode: allowlist | blocklist | any
    # allowlist: only these fields are permitted to cross the boundary
    # blocklist: these fields are explicitly prohibited
    # any: no field-level restriction (default)
    paths:
      - "fields.patient_id"
      - "fields.diagnosis_code"
      - "fields.treatment_plan"
    # Supports wildcards: "fields.phi_*" matches all fields prefixed phi_

  # Capability being exercised
  capability:
    match: <capability> | in: [<list>] | any
    # Capabilities: read | write | store | replicate | export | notify |
    #               execute | discover | query | federate
```

### 2.3 Axis 3 — Target (Where)

The target is where the data is going — provider, peer DCM, storage, notification endpoint.

```yaml
target:
  type: <target_type>
  # service_provider | dcm_peer | (prescribed infrastructure) | service_provider |
  # information_provider | external_policy_evaluation | external_endpoint

  # Identity
  provider_uuid: <uuid>                  # specific provider
  dcm_peer_uuid: <uuid>                  # specific peer

  # Sovereignty
  sovereignty_zone:
    match: <zone_id> | in: [<list>] | same_as_source | any
    not_in: [<list>]                     # exclusion list

  jurisdiction:
    includes: [<country_codes>]
    excludes: [<country_codes>]
    intersects: [<country_codes>]        # target jurisdiction overlaps with list

  # Trust and accreditation
  trust_posture:
    match: <posture> | minimum: <posture>
    # minimum: vouched means vouched or verified (not provisional)

  accreditation_held:
    includes: [<framework>]              # target MUST hold these accreditations
    not_includes: [<framework>]          # target must NOT hold (exclusion pattern)
    minimum_type: <accreditation_type>   # minimum trust level of accreditation
```

### 2.4 Axis 4 — Context (Under What Conditions)

Context captures the operational conditions at the time of the interaction.

```yaml
context:
  # Active deployment governance
  profile:
    deployment_posture: <posture> | in: [<list>]
    compliance_domains:
      includes: [<domain>]
      not_includes: [<domain>]

  # Security posture
  zero_trust_posture:
    minimum: <level>                     # none | boundary | full | hardware_attested
  tls_mutual: <required|present|absent>
  hardware_attestation: <required|present|absent>

  # Interaction characteristics
  federated: <true|false>
  cross_jurisdiction: <true|false>
  cross_tenant: <true|false>

  # Time-based conditions
  time_of_day: <range>                   # for regulated maintenance windows
  request_age_max: <ISO 8601 duration>   # reject stale requests
```

---

## 3. Rule Structure

### 3.1 The Governance Matrix Rule

```yaml
governance_matrix_rule:
  # Artifact metadata (standard DCM artifact)
  artifact_metadata:
    uuid: <uuid>
    handle: "system/matrix/phi-federation-boundary"
    version: "1.0.0"
    status: active                       # developing | proposed | active | deprecated | retired
    owned_by: { display_name: "Platform Security" }
    tier: system | platform | tenant | resource_type | entity

  description: "PHI must not cross to federated peers without HIPAA accreditation"
  rationale: "HIPAA 45 CFR 164.502 — minimum necessary standard for PHI disclosure"

  # Match conditions (all declared axes must match for rule to fire)
  match:
    subject: { ... }
    data: { ... }
    target: { ... }
    context: { ... }

  # Decision
  decision: ALLOW | DENY | ALLOW_WITH_CONDITIONS | STRIP_FIELD | REDACT | AUDIT_ONLY

  # Enforcement level
  enforcement: hard | soft
  # hard: cannot be relaxed by any downstream rule; ever
  # soft: downstream rules at same or higher domain can tighten further

  # Conditions that must be met for ALLOW_WITH_CONDITIONS
  conditions:
    - field: target.trust_posture
      operator: minimum
      value: verified
    - field: context.tls_mutual
      operator: equals
      value: required
    - field: target.accreditation_held
      operator: includes
      value: hipaa

  # Field permission model (for ALLOW and ALLOW_WITH_CONDITIONS)
  field_permissions:
    mode: allowlist | blocklist | passthrough
    paths: [<field_path_list>]
    on_blocked_field: STRIP_FIELD | DENY_REQUEST | REDACT
    # STRIP_FIELD: remove field and proceed (if field is optional)
    # DENY_REQUEST: block entire interaction (if field is required)
    # REDACT: replace field value with <REDACTED> in payload

  # Audit and notification
  audit_on: [ALLOW, DENY, STRIP_FIELD, REDACT]
  notification_on: [DENY]
  notification_urgency: low | medium | high | critical

  # Metadata
  applicable_profiles: [standard, prod, fsi, sovereign]    # which profiles activate this rule
  compliance_basis: "HIPAA 45 CFR 164.502"                 # regulatory basis
  review_required_before: "2027-01-01"                     # when rule should be reviewed
```

### 3.2 Decision Vocabulary

| Decision | Meaning | Field behavior |
|----------|---------|----------------|
| `ALLOW` | Interaction permitted unconditionally (within field_permissions) | Fields per field_permissions |
| `ALLOW_WITH_CONDITIONS` | Permitted only if all conditions are satisfied; DENY if conditions fail | Fields per field_permissions |
| `DENY` | Interaction blocked; interaction does not proceed | N/A — entire interaction stopped |
| `STRIP_FIELD` | Specific fields are removed from the payload; interaction proceeds with remaining fields | Named fields stripped |
| `REDACT` | Specific field values replaced with `<REDACTED>`; field presence is preserved | Named fields redacted |
| `AUDIT_ONLY` | Interaction proceeds but is flagged in the audit trail; no blocking | All fields pass |

### 3.3 Hard vs Soft Enforcement

**Hard enforcement (`enforcement: hard`):**
- The rule decision cannot be relaxed by any more-specific or higher-domain rule
- A hard DENY is absolute — no Tenant-level, entity-level, or operator override can permit the interaction
- Hard rules are reserved for: sovereign/classified data classification boundaries, regulatory hard requirements (HIPAA BAA requirement for PHI), and explicit security policies
- Hard ALLOW is rare — it means this interaction is always permitted regardless of other rules (use with extreme caution)

**Soft enforcement (`enforcement: soft`):**
- The rule establishes a default that can be tightened by more-specific downstream rules
- A soft ALLOW can be restricted to DENY or STRIP_FIELD by a more-specific rule
- A soft DENY cannot be relaxed to ALLOW by a downstream rule (DENY always wins at the same level)
- Most profile-level defaults are soft — they set sensible baselines that Tenants can restrict further

---

## 4. Evaluation Algorithm

The governance matrix evaluates all matching rules and produces a single terminal decision.

```
Interaction attempt:
  subject: { type: dcm_peer, trust_posture: verified, jurisdiction: [DE] }
  data: { classification: phi, field_paths: [patient_id, diagnosis_code] }
  target: { type: dcm_peer, accreditation_held: [], jurisdiction: [US] }
  context: { federated: true, zero_trust_posture: full, tls_mutual: required }

Step 1: Collect matching rules
  Load all active governance matrix rules across all tiers
  Evaluate match conditions for each rule against the four axes
  Result: set of matching rules with their decisions and enforcement levels

Step 2: Evaluate hard constraints first
  For each hard DENY rule that matches:
    → DENY immediately; record rule_uuid; no further evaluation
  For each hard ALLOW rule that matches:
    → Record as a hard allow candidate; still evaluate conditions
  If hard DENY exists: terminal decision = DENY

Step 3: Evaluate soft constraints by domain precedence
  Sort matching soft rules: entity > resource_type > tenant > platform > system
  For each precedence level, most restrictive decision wins:
    DENY > STRIP_FIELD > REDACT > ALLOW_WITH_CONDITIONS > AUDIT_ONLY > ALLOW
  If DENY at any level: terminal decision = DENY

Step 4: Evaluate conditions for ALLOW_WITH_CONDITIONS
  For each ALLOW_WITH_CONDITIONS rule that survived Steps 2-3:
    Evaluate all declared conditions
    If any condition fails: downgrade decision to DENY
    If all conditions pass: decision remains ALLOW_WITH_CONDITIONS

Step 5: Apply field permissions
  If terminal decision is ALLOW or ALLOW_WITH_CONDITIONS:
    Apply field_permissions from the governing rule:
      allowlist mode: strip all fields not in the allowed list
      blocklist mode: strip all fields in the blocked list
      passthrough mode: all fields pass
    For each stripped field:
      If field is required: escalate to DENY_REQUEST
      If field is optional: STRIP_FIELD (proceed without it)

Step 6: Produce audit record
  Record: interaction_uuid, all matching rules, terminal decision,
          fields stripped or redacted, rule that governed the decision
  Notification: if terminal decision is in rule's notification_on list

Step 7: Enforce decision
  ALLOW / ALLOW_WITH_CONDITIONS: interaction proceeds with permitted fields
  DENY: interaction blocked; 403 response with governance_matrix_rule_uuid
  STRIP_FIELD: interaction proceeds with stripped payload
  REDACT: interaction proceeds with redacted field values
  AUDIT_ONLY: interaction proceeds; flagged audit record written
```

---

## 5. Sovereignty Zones

Sovereignty zones are registered DCM artifacts that define geopolitical and regulatory boundaries. They are a first-class input to the governance matrix — rules reference zones, not raw country codes.

```yaml
sovereignty_zone:
  artifact_metadata:
    uuid: <uuid>
    handle: "zones/eu-west-sovereign"
    version: "1.0.0"
    status: active
    tier: system | platform

  display_name: "EU Western Europe Sovereign Zone"
  description: "GDPR-covered EU member states with NIS2 alignment"

  jurisdictions: [DE, FR, NL, BE, AT, CH, LU]
  excluded_jurisdictions: []             # explicit exclusions within the zone

  data_residency_guarantee: EU           # GDPR Article 44 transfer basis
  regulatory_frameworks: [GDPR, NIS2, eIDAS]

  cross_zone_permitted: false            # data does not leave this zone by default
  inter_zone_agreements:                 # zones this zone has data transfer agreements with
    - zone_id: eu-north-sovereign
      agreement_basis: "EU adequacy decision"
      permitted_classifications: [public, internal, confidential]
      # restricted, phi, sovereign: NOT included

  # What accreditation providers must hold to operate in this zone
  required_provider_accreditation: gdpr_adequacy | third_party
  required_provider_accreditation_minimum_type: third_party
```

---

## 6. Field-Level Controls — Complete Model

### 6.1 Field Path Syntax

Field paths use dot-notation to address specific fields within a DCM payload:

```
fields.<field_name>                      # top-level field
fields.<field_name>.<subfield>           # nested field
fields.phi_*                             # wildcard: all fields matching prefix
fields.*                                 # all fields
metadata.<field_name>                    # metadata fields
provenance.<field_name>                  # provenance fields (rarely restricted)
```

### 6.2 Broad to Fine-Grained Rule Examples

**Broadest — classification-level block:**
```yaml
# Block ALL phi fields from crossing to non-HIPAA peers
match:
  data.classification: phi
  target.type: dcm_peer
  target.accreditation_held.not_includes: hipaa
decision: DENY
enforcement: hard
```

**Mid-level — resource type + classification:**
```yaml
# For VM resources: restricted fields to EU zones only
match:
  data.classification: restricted
  data.resource_type: Compute.VirtualMachine
  target.sovereignty_zone.not_in: [eu-west-sovereign, eu-north-sovereign]
decision: STRIP_FIELD
field_permissions:
  mode: blocklist
  paths: ["fields.security_group_ids", "fields.network_interface_ids"]
  on_blocked_field: STRIP_FIELD
```

**Fine-grained — specific fields:**
```yaml
# Allow federated phi-accredited peers to receive limited PHI fields only
match:
  data.classification: phi
  target.type: dcm_peer
  target.accreditation_held.includes: hipaa
  target.trust_posture: verified
decision: ALLOW_WITH_CONDITIONS
conditions:
  - field: context.tls_mutual
    operator: equals
    value: required
  - field: context.zero_trust_posture
    operator: minimum
    value: full
field_permissions:
  mode: allowlist
  paths:
    - "fields.resource_type"
    - "fields.lifecycle_state"
    - "fields.provider_entity_id"
    # PHI-containing fields explicitly NOT in allowlist:
    # fields.patient_id, fields.diagnosis_code, fields.treatment_plan
    # are stripped automatically
  on_blocked_field: STRIP_FIELD
```

**Most specific — entity-level rule:**
```yaml
# Provider A: explicit PHI block regardless of accreditation
match:
  target.provider_uuid: provider-a-uuid
  data.classification: phi
decision: DENY
enforcement: hard
reason: "Provider A has unresolved data handling concerns — PHI explicitly prohibited"
```

### 6.3 Field-Level Redaction vs Stripping

| Operation | Effect on payload | Use case |
|-----------|------------------|----------|
| `STRIP_FIELD` | Field entirely removed from payload | Field is optional; receiver has no need to know it exists |
| `REDACT` | Field present with value `<REDACTED>` | Receiver needs to know field exists but not its value (e.g., audit evidence that a field was present) |
| `DENY_REQUEST` | Entire interaction blocked | Field is required for the operation to make sense; stripping would produce invalid state |

---

## 7. Profile-Bound Default Matrix Rules

Every deployment profile activates a set of default governance matrix rules. These are soft rules (tightenable by Tenant/resource-type overrides) unless marked hard.

### 7.1 minimal Profile Defaults

```yaml
profile_matrix_defaults:
  profile: minimal
  rules:
    - handle: "system/matrix/minimal-sovereign-hard"
      enforcement: hard
      match:
        data.classification: [sovereign, classified]
        target.type: [dcm_peer, service_provider, service_provider]
      decision: DENY
      reason: "Sovereign and classified data never crosses any boundary — any profile"

    - handle: "system/matrix/minimal-passthrough"
      enforcement: soft
      match:
        data.classification: [public, internal]
        target.type: any
      decision: ALLOW
      field_permissions:
        mode: passthrough
```

### 7.2 dev Profile Defaults

```yaml
profile_matrix_defaults:
  profile: dev
  inherits: minimal
  additional_rules:
    - handle: "system/matrix/dev-confidential-allow"
      enforcement: soft
      match:
        data.classification: confidential
        target.type: [service_provider, dcm_peer]
        target.trust_posture: [verified, vouched, provisional]
      decision: ALLOW_WITH_CONDITIONS
      conditions:
        - field: context.tls_mutual
          operator: equals
          value: required
      field_permissions:
        mode: passthrough
      # Dev allows confidential to flow broadly; standard+ tightens this
```

### 7.3 standard Profile Defaults

```yaml
profile_matrix_defaults:
  profile: standard
  inherits: minimal
  additional_rules:
    - handle: "system/matrix/standard-restricted-accreditation"
      enforcement: soft
      match:
        data.classification: restricted
        target.type: [service_provider, dcm_peer]
      decision: ALLOW_WITH_CONDITIONS
      conditions:
        - field: target.accreditation_held
          operator: minimum_type
          value: third_party
        - field: context.tls_mutual
          operator: equals
          value: required
      field_permissions:
        mode: passthrough

    - handle: "system/matrix/standard-phi-deny-default"
      enforcement: soft
      match:
        data.classification: phi
        target.type: [service_provider, dcm_peer]
      decision: DENY
      # Tenants with HIPAA compliance domain active override this with their own rules
```

### 7.4 prod Profile Defaults

```yaml
profile_matrix_defaults:
  profile: prod
  inherits: standard
  additional_rules:
    - handle: "system/matrix/prod-federation-verified-only"
      enforcement: soft
      match:
        data.classification: [confidential, restricted]
        target.type: dcm_peer
        target.trust_posture: [vouched, provisional]
      decision: DENY
      # prod: only verified peers receive confidential+ data

    - handle: "system/matrix/prod-notification-restricted"
      enforcement: soft
      match:
        data.classification: restricted
        target.type: service_provider
      decision: STRIP_FIELD
      field_permissions:
        mode: blocklist
        paths: ["fields.*"]      # strip all payload fields from notifications
        # Notification envelope metadata (entity_uuid, event_type) passes through
        # Actual field values do not appear in notification payloads for restricted data
```

### 7.5 fsi Profile Defaults

```yaml
profile_matrix_defaults:
  profile: fsi
  inherits: prod
  additional_rules:
    - handle: "system/matrix/fsi-cross-jurisdiction-deny"
      enforcement: hard
      match:
        data.classification: [restricted, phi, pci, sovereign]
        target.type: [service_provider, dcm_peer]
        context.cross_jurisdiction: true
      decision: DENY
      reason: "FSI profile: regulated data does not cross jurisdictional boundaries"

    - handle: "system/matrix/fsi-phi-baa-required"
      enforcement: hard
      match:
        data.classification: phi
        target.type: [service_provider, dcm_peer]
      decision: ALLOW_WITH_CONDITIONS
      conditions:
        - field: target.accreditation_held
          operator: includes
          value: hipaa_baa
        - field: target.trust_posture
          operator: minimum
          value: verified
        - field: context.zero_trust_posture
          operator: minimum
          value: full
      field_permissions:
        mode: passthrough          # HIPAA-accredited verified peers get full PHI scope
        # Tenant-level rules can further restrict to specific field paths

    - handle: "system/matrix/fsi-pci-qsa-required"
      enforcement: hard
      match:
        data.classification: pci
        target.type: [service_provider, dcm_peer]
      decision: ALLOW_WITH_CONDITIONS
      conditions:
        - field: target.accreditation_held
          operator: includes
          value: pci_dss_qsa
        - field: context.zero_trust_posture
          operator: minimum
          value: full
```

### 7.6 sovereign Profile Defaults

```yaml
profile_matrix_defaults:
  profile: sovereign
  inherits: fsi
  additional_rules:
    - handle: "system/matrix/sovereign-no-federation-sensitive"
      enforcement: hard
      match:
        data.classification: [restricted, phi, pci, sovereign, classified]
        target.type: dcm_peer
      decision: DENY
      reason: "Sovereign profile: sensitive data never crosses DCM federation boundaries"

    - handle: "system/matrix/sovereign-internal-only-federation"
      enforcement: hard
      match:
        data.classification: [public, internal]
        target.type: dcm_peer
        context.zero_trust_posture:
          not_minimum: hardware_attested
      decision: DENY
      reason: "Sovereign profile: federation requires hardware attestation"

    - handle: "system/matrix/sovereign-provider-sovereign-zone-only"
      enforcement: hard
      match:
        data.classification: [restricted, phi, pci, sovereign, classified]
        target.type: service_provider
        target.sovereignty_zone.not_in: [<deployment_sovereignty_zone>]
      decision: DENY
      reason: "Sovereign profile: sensitive data only to providers in declared sovereignty zone"
```

---

## 8. Compliance Domain Matrix Rules

When a compliance domain is active, its matrix rules are automatically added to the active rule set.

### 8.1 HIPAA Compliance Domain Matrix

```yaml
compliance_domain_matrix:
  domain: hipaa
  rules:
    - handle: "system/matrix/hipaa-phi-minimum-necessary"
      enforcement: hard
      match:
        data.classification: phi
        target.type: any
      decision: ALLOW_WITH_CONDITIONS
      conditions:
        - principle: minimum_necessary    # only fields required for the specific purpose
      field_permissions:
        mode: blocklist                   # default: all fields except explicitly blocked
        paths: []                         # Tenant adds specific field blocks
        on_blocked_field: STRIP_FIELD

    - handle: "system/matrix/hipaa-phi-no-export"
      enforcement: hard
      match:
        data.classification: phi
        data.capability: export
      decision: DENY
      reason: "HIPAA: PHI export to external systems requires explicit BAA and regulatory review"

    - handle: "system/matrix/hipaa-audit-all-phi"
      enforcement: hard
      match:
        data.classification: phi
        target.type: any
      decision: AUDIT_ONLY           # added to all PHI interactions — does not block
      audit_on: [ALLOW, DENY, STRIP_FIELD]
      # Every PHI interaction produces an audit record — HIPAA requirement
```

### 8.2 GDPR Compliance Domain Matrix

```yaml
compliance_domain_matrix:
  domain: gdpr
  rules:
    - handle: "system/matrix/gdpr-eu-residency"
      enforcement: hard
      match:
        data.classification: [restricted, phi]
        target.sovereignty_zone.not_in: <eu_zones>
        context.compliance_domains.includes: gdpr
      decision: DENY
      reason: "GDPR Article 44: personal data transfer outside EU requires adequacy decision"

    - handle: "system/matrix/gdpr-right-to-erasure-fields"
      enforcement: hard
      match:
        data.field_paths.includes: ["fields.personal_identifier_*", "fields.contact_*"]
        data.capability: [store, replicate]
        target.accreditation_held.not_includes: gdpr_adequacy
      decision: STRIP_FIELD
      field_permissions:
        mode: blocklist
        paths: ["fields.personal_identifier_*", "fields.contact_*"]
```

---

## 9. Tenant and Resource-Type Override Rules

Tenants and resource-type specifications declare additional rules that compose with system and profile rules per the standard precedence model.

### 9.1 Tenant Override Rule

```yaml
# Tenant payments-team: additional restriction on PHI fields
governance_matrix_rule:
  artifact_metadata:
    tier: tenant
    handle: "tenant/payments/phi-field-restriction"
  
  match:
    subject.tenant.uuid: payments-tenant-uuid
    data.classification: phi
    target.type: dcm_peer
    target.accreditation_held.includes: hipaa
  
  decision: ALLOW_WITH_CONDITIONS
  conditions:
    - field: target.trust_posture
      operator: equals
      value: verified                    # only verified (not vouched)
  
  field_permissions:
    mode: allowlist                      # tighter than the fsi default (passthrough)
    paths:
      - "fields.resource_type"
      - "fields.lifecycle_state"
      # PHI-containing fields not listed → automatically stripped
    on_blocked_field: STRIP_FIELD
```

### 9.2 Resource-Type Override Rule

```yaml
# For Patient Record resources: maximum restriction regardless of Tenant settings
governance_matrix_rule:
  artifact_metadata:
    tier: resource_type
    handle: "resource-type/patient-record/no-federation"
  
  match:
    data.resource_type: Healthcare.PatientRecord
    target.type: dcm_peer
  
  decision: DENY
  enforcement: hard
  reason: "Patient Record entities are never federated — local only"
```

---

## 10. Governance Matrix in the Registration Flow

When a provider attempts to register with DCM, the governance matrix is evaluated before the registration is accepted. This answers: "Is a provider of this type, with these accreditations, in this sovereignty zone, permitted to register in this DCM deployment?"

```
Provider submits registration
  │
  ▼ Governance matrix evaluation:
  │   subject: { type: <provider_type>, accreditation_held: [...], sovereignty_zone: <zone> }
  │   data: { capability: register }
  │   target: { type: dcm_instance, sovereignty_zone: <local_zone> }
  │   context: { profile: <active_posture>, compliance_domains: [...] }
  │
  ├── DENY: registration rejected immediately
  │   Provider type not permitted in this profile
  │   Provider in excluded jurisdiction
  │   Required accreditation not held
  │
  └── ALLOW / ALLOW_WITH_CONDITIONS: registration proceeds to validation pipeline
```

---

## 11. System Policies

| Policy | Rule |
|--------|------|
| `GMX-001` | The Governance Matrix is the single enforcement point for all cross-boundary data and capability decisions. Parallel enforcement mechanisms (standalone sovereignty checks, standalone accreditation checks) are inputs to the matrix — not independent enforcement paths. |
| `GMX-002` | Hard rules cannot be relaxed by any downstream rule at any domain level. Hard DENY is absolute. |
| `GMX-003` | Soft rules establish defaults that can only be tightened by downstream rules. Soft DENY cannot be relaxed to ALLOW by a more-specific rule. |
| `GMX-004` | Sovereign and classified data classifications carry hard DENY rules for all federation and external provider interactions in all profiles including minimal. This is the one rule that cannot be changed by any configuration. |
| `GMX-005` | Every governance matrix evaluation produces an audit record regardless of outcome. |
| `GMX-006` | Field-level stripping (STRIP_FIELD) is always audited with the field path and the rule_uuid that governed the stripping. |
| `GMX-007` | Profile default matrix rules are soft unless explicitly marked hard. Tenant and resource-type rules can tighten profile defaults but cannot relax hard rules. |
| `GMX-008` | Compliance domain matrix rules are automatically added to the active rule set when the compliance domain is active. They compose with profile rules — they do not replace them. |
| `GMX-009` | The Governance Matrix is evaluated before provider dispatch, before federation tunnel data transmission, before notification delivery, and before any cross-boundary capability invocation. |
| `GMX-010` | A STRIP_FIELD decision that removes a required field escalates to DENY_REQUEST automatically. Optional fields may be stripped without blocking the interaction. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
