# UDLM — Unified Governance Matrix

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
> **This document maps to: POLICY**
>
> The Policy abstraction — Governance Matrix Rule output schema for boundary control.

**Related Documents:** [Federated Contribution Model](federated-contribution-model.md) | [Accreditation and Authorization Matrix](accreditation-and-authorization-matrix.md) | [Layering and Versioning](../foundations/layering-and-versioning.md)

---

> **Federated Contribution:** The Governance Matrix enforces contributor permission boundaries at artifact submission time. See the [Federated Contribution Model](federated-contribution-model.md) for the complete contributor permission table and the hard DENY rules applied to out-of-scope contributions.

## 1. Purpose

The Unified Governance Matrix is the **single, declarative, multi-dimensional control surface** that governs every cross-boundary interaction in a UDLM-conformant realization. It answers one question at every interaction point:

> **Given this subject, this data, this target, and this context — is this interaction permitted, and under what conditions?**

The Governance Matrix unifies what could otherwise be several overlapping control mechanisms (data/capability authorization matrix, sovereignty constraints in federation tunnels, profile-governed data boundaries) into a single substrate model with a single evaluation pattern and a single enforcement contract.

The accreditation model and data classification model from [Accreditation and Authorization Matrix](accreditation-and-authorization-matrix.md) are inputs to this evaluation.

**Key substrate properties of the Governance Matrix:**

- **Single enforcement point** — every interaction boundary evaluates the same matrix. Parallel enforcement paths are forbidden by the substrate.
- **Fine-grained to broad** — rules can target a single field path on a specific entity, or broadly govern all data of a given classification. Both are first-class.
- **Profile-bound defaults** — every deployment profile ships with sensible default rules that are immediately operative.
- **Hard and soft enforcement** — hard rules cannot be relaxed by any downstream rule. Soft rules establish defaults that can be tightened but never relaxed.
- **Audited always** — every evaluation produces an audit record regardless of outcome.

---

## 1b. Governance Matrix and the Scoring Model

The Governance Matrix is **always boolean**. This is not a design limitation — it is an explicit substrate decision.

Governance Matrix decisions (ALLOW, DENY, ALLOW_WITH_CONDITIONS, STRIP_FIELD, REDACT, AUDIT_ONLY) govern whether data may cross a boundary. These are regulatory and legal facts — PHI either crosses a compliant boundary or it doesn't. "Mostly compliant" is not a legal defense. No Governance Matrix Rule may declare `scoring_weight` or `enforcement_class`.

**The Governance Matrix MUST fire before any scoring evaluation.** If a Governance Matrix Rule produces DENY, the request is halted and no risk score is calculated. Scoring only runs for requests that have already passed all Governance Matrix checks.

This substrate constraint ensures that scoring cannot be used to route around data sovereignty or regulatory boundaries.

---

## 2. The Four Matrix Axes (Substrate Contract)

Every governance matrix rule is expressed as a match across four axes. A rule fires when all declared axis conditions are satisfied. The axes and their fields below are normative — the names and value vocabularies are part of the wire contract.

### 2.1 Axis 1 — Subject (Who)

The subject is the entity initiating or involved in the interaction.

```yaml
subject:
  type: <subject_type>
  # Subject types (closed substrate vocabulary):
  # actor                — human or service account making a request
  # service_provider     — Service Provider sending/receiving data
  # peer_realization     — federated peer realization
  # external_policy_evaluation — External Policy Evaluator receiving payload data
  # data_store           — data store receiving/returning state data
  # notification_service — notification service receiving notification envelopes
  # information_provider — Information Provider returning external data
  # system               — internal control-plane component

  identity:
    provider_uuid: <uuid>              # specific provider instance
    peer_uuid: <uuid>                  # specific federated peer
    trust_posture: <verified|vouched|provisional>  # for peer subjects
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
    # Capabilities (closed substrate vocabulary):
    #   read | write | store | replicate | export | notify |
    #   execute | discover | query | federate
```

### 2.3 Axis 3 — Target (Where)

The target is where the data is going — provider, peer realization, storage, notification endpoint.

```yaml
target:
  type: <target_type>
  # service_provider | peer_realization | data_store | notification_service |
  # information_provider | external_policy_evaluation | external_endpoint

  # Identity
  provider_uuid: <uuid>
  peer_uuid: <uuid>

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

## 3. Rule Structure (Wire Contract)

### 3.1 The Governance Matrix Rule

```yaml
governance_matrix_rule:
  # Artifact metadata (standard substrate artifact)
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

### 3.2 Decision Vocabulary (Closed Substrate)

| Decision | Meaning | Field behavior |
|----------|---------|----------------|
| `ALLOW` | Interaction permitted unconditionally (within field_permissions) | Fields per field_permissions |
| `ALLOW_WITH_CONDITIONS` | Permitted only if all conditions are satisfied; DENY if conditions fail | Fields per field_permissions |
| `DENY` | Interaction blocked; interaction does not proceed | N/A — entire interaction stopped |
| `STRIP_FIELD` | Specific fields are removed from the payload; interaction proceeds with remaining fields | Named fields stripped |
| `REDACT` | Specific field values replaced with `<REDACTED>`; field presence is preserved | Named fields redacted |
| `AUDIT_ONLY` | Interaction proceeds but is flagged in the audit trail; no blocking | All fields pass |

### 3.3 Hard vs Soft Enforcement (Substrate Distinction)

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

## 4. Evaluation Contract (Substrate Required)

A conformant realization MUST evaluate matching rules and produce a single terminal decision according to the following substrate-required precedence:

1. **Collect** all active governance matrix rules whose `match` axes are satisfied by the interaction.
2. **Evaluate hard constraints first.** Any hard DENY that matches produces an immediate terminal DENY; no further evaluation is required.
3. **Evaluate soft constraints by domain precedence.** Sort matching soft rules: `entity > resource_type > tenant > platform > system`. At each precedence level, the most restrictive decision wins (`DENY > STRIP_FIELD > REDACT > ALLOW_WITH_CONDITIONS > AUDIT_ONLY > ALLOW`).
4. **Evaluate conditions for `ALLOW_WITH_CONDITIONS`.** If any declared condition fails, the decision MUST be downgraded to DENY.
5. **Apply field permissions.** For surviving ALLOW / ALLOW_WITH_CONDITIONS decisions: enforce the rule's `field_permissions` (allowlist, blocklist, or passthrough). A stripped REQUIRED field MUST escalate to DENY_REQUEST.
6. **Produce an audit record.** Record interaction_uuid, all matching rules, terminal decision, fields stripped/redacted, and the rule that governed the decision. Notification fires for decisions listed in the rule's `notification_on`.
7. **Enforce the decision.** ALLOW / ALLOW_WITH_CONDITIONS: interaction proceeds with permitted fields. DENY: interaction blocked with 403 and `governance_matrix_rule_uuid`. STRIP_FIELD / REDACT: interaction proceeds with modified payload. AUDIT_ONLY: interaction proceeds with flagged audit record.

The specific algorithm by which a realization performs collection, sorting, and caching is a realization choice; the precedence and decision-monotonicity above are the substrate contract.

---

## 5. Sovereignty Zones (Substrate Artifact Contract)

Sovereignty zones are first-class artifacts that define geopolitical and regulatory boundaries. They are an input to the governance matrix — rules reference zones, not raw country codes. The artifact shape is normative:

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

  # What accreditation providers must hold to operate in this zone
  required_provider_accreditation: gdpr_adequacy | third_party
  required_provider_accreditation_minimum_type: third_party
```

Zone instances and their inter-zone agreements are realization/organization data — but the artifact contract above is normative.

---

## 6. Field-Level Controls — Substrate Model

### 6.1 Field Path Syntax (Substrate-Normative)

Field paths use dot-notation to address specific fields within a payload:

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
  target.type: peer_realization
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
  target.type: peer_realization
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

### 6.3 Field-Level Redaction vs Stripping (Substrate Semantics)

| Operation | Effect on payload | Use case |
|-----------|------------------|----------|
| `STRIP_FIELD` | Field entirely removed from payload | Field is optional; receiver has no need to know it exists |
| `REDACT` | Field present with value `<REDACTED>` | Receiver needs to know field exists but not its value (e.g., audit evidence that a field was present) |
| `DENY_REQUEST` | Entire interaction blocked | Field is required for the operation to make sense; stripping would produce invalid state |

---

## 7. UDLM System Policies

| Policy | Rule |
|--------|------|
| `GMX-001` | The Governance Matrix is the single enforcement point for all cross-boundary data and capability decisions. Parallel enforcement mechanisms (standalone sovereignty checks, standalone accreditation checks) are inputs to the matrix — not independent enforcement paths. |
| `GMX-002` | Hard rules cannot be relaxed by any downstream rule at any domain level. Hard DENY is absolute. |
| `GMX-003` | Soft rules establish defaults that can only be tightened by downstream rules. Soft DENY cannot be relaxed to ALLOW by a more-specific rule. |
| `GMX-004` | Sovereign and classified data classifications carry hard DENY rules for all federation and external provider interactions in all profiles including minimal. This is the one rule that cannot be changed by any configuration. |
| `GMX-005` | Every governance matrix evaluation produces an audit record regardless of outcome. |
| `GMX-006` | Field-level stripping (STRIP_FIELD) is always audited with the field path and the `rule_uuid` that governed the stripping. |
| `GMX-007` | Profile default matrix rules are soft unless explicitly marked hard. Tenant and resource-type rules can tighten profile defaults but cannot relax hard rules. |
| `GMX-008` | Compliance domain matrix rules are automatically added to the active rule set when the compliance domain is active. They compose with profile rules — they do not replace them. |
| `GMX-009` | The Governance Matrix is evaluated before provider dispatch, before federation tunnel data transmission, before notification delivery, and before any cross-boundary capability invocation. |
| `GMX-010` | A STRIP_FIELD decision that removes a required field escalates to DENY_REQUEST automatically. Optional fields may be stripped without blocking the interaction. |

---

*UDLM substrate document. Realization-specific evaluation algorithm internals, hard/soft enforcement execution mechanics, sovereignty zone management runtime, profile-governed policy bundles and the registration-time evaluation pipeline, and policy caching/invalidation live in the consuming realization's documentation.*
