# DCM Data Model — Credential Provider Model


**Document Status:** ✅ Complete
**Document Type:** Architecture Reference — Credential Provider Specification
**Related Documents:** [Foundational Abstractions](00-foundations.md) | [Provider Contract](A-provider-contract.md) | [Auth Providers](19-auth-providers.md) | [Accreditation and Zero Trust](26-accreditation-and-authorization-matrix.md) | [Scoring Model](29-scoring-model.md) | [Federated Contribution Model](28-federated-contribution-model.md)

> **This document maps to: DATA + PROVIDER**
>
> Credentials are Data artifacts with UUID, type, lifecycle state, and provenance. The Credential Provider is a typed Provider with a defined capability extension. The Zero Trust model in [doc 26](26-accreditation-and-authorization-matrix.md) governs credential scope and lifetime — this document specifies how that model is implemented.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)

---

> **Cryptographic Standards:** See [Standards and Compliance Catalog](40-standards-catalog.md) for the complete list of permitted/forbidden algorithms, FIPS requirements per profile, and certificate protocol RFCs (RFC 7030, RFC 8555, RFC 8894, RFC 4210).

## 1. Purpose and Scope

### 1.1 What the Credential Provider Does

The Credential Provider is a typed DCM Provider responsible for issuing, rotating, and revoking credentials used within the DCM ecosystem. There are two categories of credential it manages:

**1. DCM interaction credentials** — short-lived, scoped credentials that DCM components and providers use to authenticate interactions. These implement the Zero Trust credential model from [doc 26](26-accreditation-and-authorization-matrix.md) Section 5.3. They are issued by DCM's Credential Provider and consumed entirely within the DCM control plane and its providers.

**2. Consumer-facing credentials** — credentials delivered to consumers as part of a realized service (kubeconfigs, database passwords, API keys, SSH keys, service account tokens). These are issued by the Credential Provider on behalf of a realized resource entity and delivered via the Consumer API.

### 1.2 What the Credential Provider Does Not Do

- It does not manage actor session tokens — that is the Auth Provider's responsibility
- It does not store secrets in DCM's data model — credential values are never written to the GitOps stores or Realized State Store; only credential metadata (UUID, type, scope, expiry, status) is stored
- It does not make authorization decisions — authorization is the Governance Matrix's responsibility; the Credential Provider only issues if DCM has already authorized the operation
- It does not replace secrets management for consumers' own applications — it manages credentials that DCM issues for DCM-managed resources

---

## 2. Credential Types

| Credential Type | Use Case | Typical Lifetime | Rotation Trigger |
|----------------|----------|-----------------|-----------------|
| `dcm_interaction` | DCM-internal component-to-provider auth | PT15M–PT1H (profile-governed) | Automatic; pre-expiry |
| `api_key` | Programmatic consumer access to a realized resource | PT24H–P30D (configurable) | Scheduled or event-triggered |
| `x509_certificate` | mTLS identity for providers and DCM components | P30D–P365D | P14D before expiry |
| `ssh_key` | SSH access to realized VMs or infrastructure | P30D–P90D (configurable) | Scheduled or on-demand |
| `service_account_token` | Workload identity for automated processes | PT1H–PT24H | Automatic; pre-expiry |
| `database_password` | Access credential for realized database resources | PT24H–P7D (configurable) | Scheduled or on-demand |
| `kubeconfig` | Access to realized Kubernetes clusters | PT8H–P30D (configurable) | Scheduled or on-demand |
| `hsm_backed_key` | Sovereign/FSI deployments requiring hardware attestation | P30D–P365D | P14D before expiry; HSM-managed |

---

## 3. Credential Data Model

A credential is a DCM Data artifact. Credential metadata is stored in DCM; credential values are held only by the Credential Provider (never in DCM stores).

```yaml
credential_record:
  credential_uuid: <uuid>
  credential_type: api_key | x509_certificate | ssh_key | service_account_token |
                   database_password | kubeconfig | hsm_backed_key | dcm_interaction

  # Lifecycle
  status: active | rotating | revoked | expired
  issued_at: <ISO 8601>
  expires_at: <ISO 8601>
  last_rotated_at: <ISO 8601 | null>
  revoked_at: <ISO 8601 | null>
  revocation_reason: <string | null>

  # Scope — what this credential authorizes
  issued_to:
    actor_uuid: <uuid | null>          # consumer credential: issued to an actor
    entity_uuid: <uuid | null>         # resource credential: scoped to an entity
    component_uuid: <uuid | null>      # interaction credential: issued to a DCM component
    provider_uuid: <uuid | null>       # interaction credential: scoped to a provider
  scope:
    operations: [dispatch, discover, query, read, write, admin]  # allowed operations
    resource_types: [Compute.VirtualMachine]                     # scoped resource types
    tenant_uuid: <uuid | null>                                   # Tenant scope
  non_transferable: true               # always true for DCM-issued credentials
  bound_to_ip: <IP | null>             # optional; enforced in fsi/sovereign profiles

  # Provenance
  credential_provider_uuid: <uuid>
  issuing_request_uuid: <uuid>         # which DCM request triggered issuance
  entity_uuid: <uuid | null>           # the realized entity this credential accesses
  rotation_of: <credential_uuid | null>  # parent credential UUID if this is a rotation

  # Storage (values never in DCM)
  value_held_by: <credential_provider_uuid>
  value_retrieval_endpoint: <url>      # how the authorized consumer retrieves the value
  value_retrieval_auth: bearer_token | mtls | step_up_mfa

  # Cryptographic metadata (Sections 13)
  algorithm: Ed25519 | ECDSA-P-384 | RSA-4096 | HS256 | RS256 | random_256bit
  key_usage: [authentication]   # authentication | signing | encryption; declared at issuance
  retrieved_count_threshold: 48  # hours; idle alert fires if not retrieved within this window
```

### 3.1 Credential Value Separation

Credential values are never stored in DCM's data model, GitOps stores, or Realized State Store. DCM stores only the credential metadata record. The credential value is held exclusively by the Credential Provider.

Authorized consumers retrieve the credential value via `value_retrieval_endpoint` using `value_retrieval_auth`. This retrieval is itself authenticated — typically with a short-lived bearer token or mTLS — and is audited.

---

## 4. Issuance Flows

### 4.1 Resource Credential Issuance (consumer-facing)

Credentials issued as part of resource realization flow through the standard provider dispatch pipeline.

```
Consumer requests resource (e.g., Compute.VirtualMachine)
  │
  ▼ Layer assembly + policy evaluation
  │   Transformation policy may inject credential requirements:
  │     fields.credential_requirements:
  │       - credential_type: ssh_key
  │         issued_to: requesting_actor
  │         scope: [ssh_access]
  │
  ▼ Placement selects Service Provider for the VM
  │
  ▼ After VM realization: Credential Provider dispatched
  │   DCM issues sub-request to Credential Provider:
  │     entity_uuid: <vm_entity_uuid>
  │     credential_type: ssh_key
  │     issued_to.actor_uuid: <requesting_actor_uuid>
  │     scope.operations: [ssh_access]
  │     scope.resource_types: [Compute.VirtualMachine]
  │     expires_at: <now + profile_lifetime>
  │
  ▼ Credential Provider issues credential; returns credential_record
  │   (value held by provider; metadata returned to DCM)
  │
  ▼ DCM writes credential_record to Realized State
  │   Links credential_uuid to entity_uuid
  │
  ▼ Consumer receives realized entity + credential_record metadata
  │   Consumer calls value_retrieval_endpoint to get actual credential
  │   (step-up MFA may be required per profile)
```

### 4.2 DCM Interaction Credential Issuance

DCM interaction credentials are issued automatically before each provider interaction. They implement the Zero Trust scoped credential model (ZTS-002).

```
DCM prepares to dispatch to a provider
  │
  ▼ Request interaction credential from Credential Provider:
  │   credential_type: dcm_interaction
  │   issued_to.component_uuid: <api_gateway_uuid>
  │   issued_to.provider_uuid: <target_provider_uuid>
  │   scope.operations: [dispatch]
  │   scope.resource_types: [Compute.VirtualMachine]
  │   entity_uuid: <entity_being_dispatched>
  │   expires_at: <now + PT15M>  (max; profile-governed)
  │
  ▼ Credential Provider issues scoped interaction credential
  │
  ▼ DCM includes credential in provider dispatch
  │   Provider validates credential scope before executing
  │
  ▼ Credential expires after PT15M regardless of use
  │   (no renewal; new credential issued for next interaction)
```

### 4.3 Bootstrap Credential Issuance

During bootstrap, before the Credential Provider is registered, DCM uses a bootstrap credential mechanism. See [Deployment and Redundancy](17-deployment-redundancy.md) BOOT-003 for the bootstrap credential model. After bootstrap, all credentials are issued through a registered Credential Provider.

---

## 5. Credential Rotation Model

Rotation is the primary mechanism for maintaining credential hygiene. DCM distinguishes scheduled rotation, pre-expiry rotation, and event-triggered rotation.

### 5.1 Rotation Triggers

| Trigger | Description | Default behavior |
|---------|-------------|-----------------|
| `scheduled` | Regular rotation on a declared schedule | Most credential types; interval is credential-type specific |
| `pre_expiry` | Rotation initiated before the current credential expires | x509: P14D before expiry; ssh_key: P7D; dcm_interaction: PT5M |
| `provider_initiated` | Credential Provider notifies DCM of a rotation requirement | Handled via provider update notification model |
| `security_event` | Rotation triggered by a security signal (compromise, anomaly, policy change) | Immediate; see Section 5.4 |
| `actor_request` | Consumer requests rotation of their own credential | Subject to rate limiting and policy |

### 5.2 Rotation Protocol

Rotation uses a transition window to prevent downtime. The old credential remains valid during the transition window; the new credential is issued and delivered before the old one expires.

```
Rotation initiated (by any trigger):
  │
  ▼ DCM requests new credential from Credential Provider
  │   rotation_of: <old_credential_uuid>
  │   same scope as original; new expires_at
  │
  ▼ Credential Provider issues new credential
  │   Returns new credential_record
  │   Old credential NOT yet revoked
  │
  ▼ New credential delivered to authorized consumer/component
  │   (same delivery mechanism as initial issuance)
  │
  ▼ Transition window: both credentials valid
  │   Window duration: P1D for consumer credentials (default)
  │                    PT5M for dcm_interaction credentials
  │                    P7D for x509_certificate credentials
  │   Configurable per credential type in Credential Provider registration
  │
  ▼ Old credential revoked at end of transition window
  │   Revocation propagated to all registered consumers
  │
  ▼ Rotation record written to audit trail
      old_credential_uuid, new_credential_uuid, rotation_trigger, rotation_at
```

### 5.3 Rotation Notification

Before the old credential is revoked, DCM sends a rotation notification to any entity or actor whose credential is rotating:

```yaml
rotation_notification:
  event_type: credential.rotating
  credential_uuid: <old_uuid>
  new_credential_uuid: <new_uuid>
  transition_window_ends: <ISO 8601>
  retrieval_url: <value_retrieval_endpoint>
  action_required: "Retrieve new credential before transition window ends"
```

### 5.4 Emergency Rotation (Security Event)

On detection of a compromise or security event, DCM triggers emergency rotation:

- No transition window — old credential revoked immediately
- New credential issued and delivered via the fastest available Notification Provider channel
- Security event record written to Audit Store with full context
- Compliance-class GateKeeper firing for this entity type audited against the event
- Platform admin notified regardless of profile

```
Triggers for emergency rotation:
  security.credential_compromised      # DCM or provider reports compromise
  security.anomalous_usage_detected    # unusual access pattern detected
  actor.deprovisioned                  # actor removed; all their credentials revoked
  provider.deregistered                # provider leaving; all its interaction creds revoked
  accreditation.revoked                # provider accreditation revoked; creds reassessed
```

---

## 6. Revocation Model

Revocation makes a credential permanently invalid before its natural expiry. Unlike rotation (which maintains continuity), revocation is an immediate termination.

### 6.1 Revocation Triggers

| Trigger | Initiator | Behavior |
|---------|-----------|----------|
| `actor_deprovisioned` | SCIM / Auth Provider | All credentials issued to the actor revoked immediately |
| `entity_decommissioned` | DCM lifecycle | All credentials scoped to the entity revoked |
| `security_event` | Platform admin or security automation | Immediate; no transition window |
| `provider_deregistered` | Platform admin | All interaction credentials for the provider revoked |
| `actor_request` | Consumer | Consumer may revoke their own credentials |
| `ttl_expired` | Lifecycle Constraint Enforcer | Credential expired; revocation recorded |

### 6.2 Revocation Propagation

DCM maintains a **Credential Revocation Registry** — a fast-queryable store of revoked credential UUIDs. All components that receive DCM interaction credentials must check this registry at each use (not just at issuance time).

```
Credential revoked:
  │
  ▼ Credential record status: active → revoked
  │   revoked_at, revocation_reason written
  │
  ▼ Revocation event published to Message Bus
  │   event_type: credential.revoked
  │   credential_uuid: <uuid>
  │   effective_at: <ISO 8601>
  │
  ▼ All subscribed components update local revocation cache
  │   (cache TTL: PT1M standard; PT30S fsi/sovereign)
  │
  ▼ Credential Provider notified to invalidate stored value
  │   Provider must honor revocation within declared SLA:
  │     standard/prod: PT5M
  │     fsi/sovereign: PT1M
  │
  ▼ Audit record written
      credential_uuid, revocation_trigger, revoked_by_actor, entity_uuid
```

### 6.3 Revocation Check at Use

Providers receiving DCM interaction credentials must validate the credential at use time, not only at receipt time:

1. Verify credential signature (if signed)
2. Check credential UUID against local revocation cache
3. Verify credential has not expired (`expires_at`)
4. Verify operation is within credential scope
5. Verify IP binding if `bound_to_ip` is set

A credential that passes issuance validation but fails use-time validation is rejected. The provider must return `403 Forbidden` with `credential_revoked` or `credential_expired` error code.

---

## 7. Consumer Credential Delivery

### 7.1 How Consumers Retrieve Credentials

After a resource is realized with an associated credential, the consumer receives the `credential_record` metadata in the realized entity response. The actual credential value is retrieved separately via `value_retrieval_endpoint`.

```
GET /api/v1/resources/{entity_uuid}/credentials

Response 200:
{
  "credentials": [
    {
      "credential_uuid": "<uuid>",
      "credential_type": "ssh_key",
      "status": "active",
      "issued_at": "<ISO 8601>",
      "expires_at": "<ISO 8601>",
      "scope": {
        "operations": ["ssh_access"],
        "entity_uuid": "<uuid>"
      },
      "retrieval": {
        "endpoint": "/api/v1/credentials/<uuid>/value",
        "auth_required": "step_up_mfa",    # none | bearer_token | step_up_mfa | mtls
        "retrieval_count": 1,              # how many times value has been retrieved
        "last_retrieved_at": "<ISO 8601>"
      },
      "rotation_schedule": {
        "next_rotation_at": "<ISO 8601>",
        "rotation_trigger": "scheduled",
        "transition_window_days": 1
      }
    }
  ]
}
```

### 7.2 Credential Value Retrieval

```
GET /api/v1/credentials/{credential_uuid}/value
Authorization: Bearer <session-token>
X-DCM-StepUp-Token: <completed-challenge>  # if auth_required: step_up_mfa

Response 200:
{
  "credential_uuid": "<uuid>",
  "credential_type": "ssh_key",
  "value": {
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n...",
    "public_key": "ssh-ed25519 AAAA... dcm-issued@entity-<uuid>",
    "username": "dcm-provisioned"
  },
  "expires_at": "<ISO 8601>",
  "retrieval_uuid": "<uuid>"   # idempotency key for this retrieval event; audited
}

Response 404:  credential_uuid not found or not associated with an entity the actor owns
Response 403:  step_up_mfa required but not completed
Response 410:  credential revoked or expired
```

Every value retrieval is audited: credential_uuid, actor_uuid, retrieved_at, retrieval_uuid.

---

## 8. Credential Provider API Contract

The full endpoint contract that all Credential Providers must implement.

### 8.1 Issue Credential

```
POST {issue_endpoint}

Request:
{
  "credential_type": "ssh_key",
  "issued_to": {
    "actor_uuid": "<uuid | null>",
    "entity_uuid": "<uuid | null>",
    "component_uuid": "<uuid | null>",
    "provider_uuid": "<uuid | null>"
  },
  "scope": {
    "operations": ["ssh_access"],
    "resource_types": ["Compute.VirtualMachine"],
    "tenant_uuid": "<uuid | null>"
  },
  "expires_at": "<ISO 8601>",
  "non_transferable": true,
  "bound_to_ip": "<IP | null>",
  "rotation_of": "<credential_uuid | null>",
  "issuing_request_uuid": "<uuid>",
  "entity_uuid": "<uuid | null>"
}

Response 201 Created:
{
  "credential_uuid": "<uuid>",
  "credential_type": "ssh_key",
  "issued_at": "<ISO 8601>",
  "expires_at": "<ISO 8601>",
  "value_retrieval_endpoint": "<url>",
  "value_retrieval_auth": "step_up_mfa",
  "metadata": {}   # provider-specific additional metadata
}

Response 422:  unsupported credential type
Response 403:  issued_to scope exceeds provider's declared authority
```

### 8.2 Rotate Credential

```
POST {rotate_endpoint}

Request:
{
  "credential_uuid": "<uuid>",           # credential being rotated
  "rotation_trigger": "pre_expiry | scheduled | security_event | actor_request",
  "transition_window": "P1D",            # how long old credential remains valid
  "new_expires_at": "<ISO 8601>"
}

Response 200:
{
  "old_credential_uuid": "<uuid>",
  "new_credential_uuid": "<uuid>",
  "new_expires_at": "<ISO 8601>",
  "old_credential_revokes_at": "<ISO 8601>",   # end of transition window
  "new_value_retrieval_endpoint": "<url>"
}
```

### 8.3 Revoke Credential

```
DELETE {revoke_endpoint}/{credential_uuid}

Request body:
{
  "revocation_trigger": "actor_deprovisioned | entity_decommissioned | security_event | ...",
  "revocation_reason": "<human-readable>",
  "effective_immediately": true          # false = honor transition window if rotating
}

Response 200:
{
  "credential_uuid": "<uuid>",
  "revoked_at": "<ISO 8601>",
  "effective_immediately": true
}

Response 404: credential not found
Response 409: credential already revoked
```

### 8.4 Validate Credential (Use-Time Check)

```
POST {validate_endpoint}

Request:
{
  "credential_uuid": "<uuid>",
  "operation_type": "dispatch",
  "entity_uuid": "<uuid | null>",
  "provider_uuid": "<uuid | null>"
}

Response 200:
{
  "valid": true,
  "expires_in_seconds": 423
}

Response 200 (invalid):
{
  "valid": false,
  "reason": "revoked | expired | scope_mismatch | ip_binding_failed"
}
```

### 8.5 List Credentials for Entity

```
GET {list_endpoint}?entity_uuid=<uuid>&status=active

Response 200:
{
  "credentials": [
    {
      "credential_uuid": "<uuid>",
      "credential_type": "ssh_key",
      "status": "active",
      "issued_to": {...},
      "expires_at": "<ISO 8601>"
    }
  ]
}
```

---

## 9. Credential Provider Registration

```yaml
credential_provider_capabilities:
  # Credential types this provider can issue
  credential_types:
    - api_key
    - x509_certificate
    - ssh_key
    - service_account_token
    - database_password
    - kubeconfig
    - hsm_backed_key
    - dcm_interaction         # must declare if provider handles DCM interaction creds

  # Secret engine backing (for audit and accreditation)
  secret_engines:
    - vault                   # HashiCorp Vault
    - aws_secrets_manager
    - azure_key_vault
    - gcp_secret_manager
    - local_hsm               # sovereign deployments

  # Security properties
  hsm_backed: false           # true if all keys are HSM-protected
  fips_140_2_level: 0         # 0=none, 1, 2, or 3
  dynamic_secrets: true       # can generate credentials on demand (not just store/retrieve)

  # Rotation capabilities
  rotation_support: true
  min_transition_window: PT5M
  max_transition_window: P7D
  supported_rotation_triggers:
    - pre_expiry
    - scheduled
    - security_event
    - actor_request

  # Revocation SLA (how quickly revocations take effect)
  revocation_sla: PT5M        # standard; PT1M for fsi/sovereign

  # Endpoints (all relative to provider base URL)
  endpoints:
    issue:    /v1/credentials
    rotate:   /v1/credentials/rotate
    revoke:   /v1/credentials/{uuid}
    validate: /v1/credentials/validate
    list:     /v1/credentials
```

---

## 10. Credential Lifecycle State Machine

```
                    ┌──────────────┐
        issuance    │              │    expiry / explicit
  ─────────────────►│    ACTIVE    │────revocation──────────►  REVOKED / EXPIRED
                    │              │
                    └──────┬───────┘
                           │ rotation initiated
                           ▼
                    ┌──────────────┐
                    │   ROTATING   │  both old and new valid
                    │              │  during transition window
                    └──────┬───────┘
                           │ transition window ends
                           │ or emergency revocation
                           ▼
                       REVOKED
```

State transitions and their audit requirements:

| Transition | Audited fields |
|-----------|---------------|
| issued → ACTIVE | credential_uuid, type, issued_to, scope, expires_at, issuing_request_uuid |
| ACTIVE → ROTATING | rotation_trigger, old_uuid, new_uuid, transition_window |
| ROTATING → ACTIVE (new) | new credential activated after old revoked |
| ACTIVE/ROTATING → REVOKED | revocation_trigger, revoked_by, effective_at, reason |
| ACTIVE → EXPIRED | expired_at (system record, no actor) |

---

---

## 12. Profile-Governed Credential Configuration

Every credential security dimension is controlled by the active profile. This is the single authoritative configuration point — a homelab deployment requires minimal configuration and implementation effort; an FSI or sovereign deployment gets full enforcement without per-deployment policy authoring.

### 12.1 Credential Profile Configuration Block

```yaml
credential_profile:

  # --- Credential Type Restrictions ---
  # Which credential types are permitted. Omitted types are rejected at issuance.
  permitted_credential_types:
    minimal:   [api_key, x509_certificate, ssh_key, service_account_token, database_password]
    dev:       [api_key, x509_certificate, ssh_key, service_account_token, database_password, kubeconfig]
    standard:  [api_key, x509_certificate, ssh_key, service_account_token, database_password, kubeconfig]
    prod:      [api_key, x509_certificate, ssh_key, service_account_token, database_password, kubeconfig]
    fsi:       [x509_certificate, ssh_key, service_account_token, database_password, kubeconfig, hsm_backed_key]
    sovereign: [x509_certificate, hsm_backed_key]     # all credentials must be hardware-backed

  # --- Lifetime Limits ---
  # Maximum expires_at per credential type. Provider may issue shorter; never longer.
  max_lifetime:
    #               minimal   dev     standard  prod    fsi     sovereign
    api_key:        [P365D,   P90D,   P90D,     P30D,   —,      —]
    x509_certificate:[P365D,  P365D,  P365D,    P180D,  P90D,   P90D]
    ssh_key:        [P365D,   P90D,   P90D,     P30D,   P30D,   P30D]
    service_account_token: [PT24H, PT24H, PT24H, PT12H, PT4H,  PT1H]
    database_password: [P365D, P90D,  P90D,     P30D,   P30D,   —]
    kubeconfig:     [P365D,   P30D,   P30D,     P14D,   P7D,    —]
    dcm_interaction:[PT1H,    PT30M,  PT1H,     PT30M,  PT15M,  PT15M]
    hsm_backed_key: [—,       —,      —,        P365D,  P180D,  P90D]

  # --- Rotation ---
  max_rotation_interval:        # PCI DSS req 8.3.9: 90-day maximum for regulated profiles
    standard:   P365D           # no enforcement; provider may choose longer
    prod:       P90D            # enforced; rotation older than P90D triggers alert
    fsi:        P90D            # enforced; PCI DSS compliance
    sovereign:  P90D            # enforced
  scheduled_rotation_required:
    # Security-first: rotation is architecturally required in ALL profiles.
    # What varies is the maximum interval, automation level, and trigger mechanism.
    minimal:    true    # required; manual trigger acceptable; P365D max interval
    dev:        true    # required; manual trigger acceptable; P180D max interval
    standard:   true    # required; automated pre-expiry rotation
    prod:       true    # required; automated; strict interval enforcement
    fsi:        true    # required; automated; P90D max (PCI DSS)
    sovereign:  true    # required; automated; hardware-triggered rotation
  min_transition_window:
    minimal:    PT0S            # homelab: immediate cutover acceptable
    dev:        PT1H
    standard:   P1D
    prod:       P1D
    fsi:        P1D             # PT15M for dcm_interaction
    sovereign:  P1D             # PT15M for dcm_interaction

  # --- Value Retrieval Security ---
  value_retrieval_auth_required:
    minimal:    bearer_token    # session token sufficient for homelab
    dev:        bearer_token
    standard:   bearer_token    # step_up_mfa for sensitive types (ssh_key, database_password)
    prod:       step_up_mfa     # all credential types require step-up
    fsi:        step_up_mfa     # hardware token MFA required
    sovereign:  mtls            # mutual TLS + hardware attestation
  step_up_sensitive_types:      # standard profile: step_up_mfa for these types even without full profile enforcement
    - ssh_key
    - database_password
    - kubeconfig
    - hsm_backed_key

  # --- Retrieval Audit ---
  audit_every_retrieval:
    # Security-first: FIRST retrieval is always audited in ALL profiles (CPX-005).
    # audit_every_retrieval controls whether SUBSEQUENT retrievals are also audited.
    # audit_first_retrieval is always true regardless of this setting.
    minimal:    false           # subsequent retrievals silent; first always audited
    dev:        false           # subsequent retrievals silent; first always audited
    standard:   true            # every retrieval audited
    prod:       true
    fsi:        true
    sovereign:  true
  idle_detection_threshold:     # alert if credential not retrieved within N after issuance
    # Security-first: idle detection is on in ALL profiles. Threshold varies.
    # Alert is notification-only; never blocks. No operational burden.
    minimal:    P30D            # generous; homelab credentials may sit unused longer
    dev:        P14D
    standard:   P7D
    prod:       P3D
    fsi:        P1D
    sovereign:  PT12H

  # --- Network Binding ---
  ip_binding_required:
    minimal:    false
    dev:        false
    standard:   false           # optional; recommended for prod
    prod:       false           # optional; recommended
    fsi:        true            # mandatory
    sovereign:  true            # mandatory

  # --- Cryptographic Requirements ---
  fips_140_level_required:
    minimal:    0               # no requirement
    dev:        0
    standard:   0
    prod:       1               # Level 1: software-only acceptable
    fsi:        2               # Level 2: role-based authentication required
    sovereign:  3               # Level 3: physical tamper evidence + identity-based auth
  approved_algorithms:
    minimal:              # negative list: anything not forbidden is permitted
      forbidden_algorithms: [MD5, SHA-1, DES, 3DES, RC4, RSA-1024, RSA-512, DSA-1024]
      # No weak/broken algorithms even in homelab. Real attacks hit all deployments.
    standard:
      api_key:              [random_256bit]
      x509_certificate:     [RSA-4096, ECDSA-P-384, Ed25519]
      ssh_key:              [Ed25519, ECDSA-P-384]
      service_account_token:[HS256, RS256, ES256]
      database_password:    [random_128bit_printable]
    prod:                   # same as standard; provider must declare algorithm in credential record
      inherits: standard
    fsi:
      x509_certificate:     [RSA-4096, ECDSA-P-384]    # Ed25519 not FIPS-approved in 140-2
      ssh_key:              [RSA-4096, ECDSA-P-384]
      service_account_token:[RS256, ES256]
      database_password:    [random_256bit]
    sovereign:
      inherits: fsi
      all_types:            hsm_backed_only              # all keys generated and stored in HSM

  # --- Revocation ---
  revocation_check_frequency:   # how often components must refresh revocation cache
    minimal:    PT5M            # lazy; acceptable for homelab
    dev:        PT5M
    standard:   PT1M
    prod:       PT1M
    fsi:        PT30S
    sovereign:  PT15S
  revocation_sla:               # how quickly Credential Provider must invalidate on revocation
    minimal:    PT10M
    dev:        PT5M
    standard:   PT5M
    prod:       PT2M
    fsi:        PT1M
    sovereign:  PT30S
```

### 12.2 Authenticator Assurance Levels (NIST 800-63B Mapping)

DCM profile credential requirements map to NIST 800-63B Authenticator Assurance Levels:

| Profile | AAL | What it means |
|---------|-----|--------------|
| `minimal` | AAL1 | Single-factor; bearer token sufficient for credential retrieval |
| `dev` | AAL1 | Same as minimal; shorter lifetimes |
| `standard` | AAL2 | MFA required for sensitive credential retrieval (ssh_key, database_password, kubeconfig) |
| `prod` | AAL2 | MFA required for all credential retrieval |
| `fsi` | AAL2+ | Hardware MFA token required; FIPS 140-2 Level 2 modules |
| `sovereign` | AAL3 | Hardware-bound authenticator; FIPS 140-2 Level 3; physical tamper evidence |

### 12.3 Compliance Domain Overlays

When a compliance domain is active, its credential requirements are **additive** to the profile base:

```yaml
compliance_credential_overlays:
  hipaa:
    min_key_size_bits: 256
    max_lifetime_override:
      api_key: P90D           # HIPAA requires rotation at least annually; 90-day recommended
    audit_every_retrieval: true   # all PHI-adjacent credential access audited
    idle_detection_threshold: P7D

  pci_dss:
    max_rotation_interval: P90D   # PCI DSS req 8.3.9 — mandatory
    min_password_complexity:
      database_password:
        length: 12
        character_classes: 4    # upper, lower, digit, special
    idle_detection_threshold: P30D

  fedramp_moderate:
    fips_140_level_required: 1
    approved_algorithms:
      inherits: standard

  fedramp_high:
    fips_140_level_required: 2
    approved_algorithms:
      inherits: fsi
    ip_binding_required: true

  dod_il4:
    fips_140_level_required: 2
    ip_binding_required: true
    max_lifetime_override:
      dcm_interaction: PT10M
      service_account_token: PT1H
```

### 12.4 Design Priority and Implementation Consistency Principle

The DCM design priority order applies directly to credential management:

1. **Security first:** Security properties — value separation, rotation, audit, idle detection, algorithm baselines, revocation — are architecturally present in ALL profiles. What profiles control is enforcement strictness, threshold values, and automation level. A `minimal` profile is "security with minimal operational overhead" — not "minimal security."

2. **Ease of use second:** The secure path must be the easy path. Homelab deployments use the same API contract, same data model, and same provider interface as sovereign deployments. The profile system eliminates the need to choose between security and operational simplicity.

3. **Extensibility third:** Compliance domain overlays, profile overrides, and algorithm configuration make the credential model adaptable without code changes.

Profile variation applies only to **enforcement level and required features** — never to the underlying protocol or data model. A credential issued under the `minimal` profile has the same data structure, the same API contract, the same revocation mechanism, and the same audit record format as one issued under the `sovereign` profile. What differs is what is required vs optional.

This means:
- A Credential Provider built for a homelab deployment is compatible with a production deployment — it just needs to demonstrate it satisfies the production profile's requirements
- Migration from `dev` to `prod` profile does not require replacing the Credential Provider or re-issuing credentials under a different protocol — it triggers more conservative enforcement of the same model
- Testing and tooling built against the `dev` profile works against `sovereign` profile with the same interfaces

**CPX-001 (values never in DCM stores) is non-negotiable in every profile including `minimal`.** This is the one property that does not scale down. It is the security property that makes the entire model trustworthy regardless of deployment size.

---

## 13. Cryptographic Algorithm Requirements

### 13.1 Algorithm Declaration in Credential Record

The credential record is extended with two new fields:

```yaml
credential_record:
  # ... existing fields ...
  algorithm: Ed25519 | ECDSA-P-384 | RSA-4096 | HS256 | RS256 | random_256bit | ...
  key_usage: [authentication, signing, encryption]   # declared at issuance; non-overlapping
  retrieved_count_threshold: 48           # hours after issuance before idle alert fires
```

`key_usage` enforces the principle of algorithm agility and purpose separation. A credential issued for `authentication` cannot be used for `signing` even if the underlying algorithm supports both. The Credential Provider must validate key_usage at the validate endpoint.

### 13.2 Approved Algorithm Defaults (Standard Profile)

| Credential Type | Algorithm | Key Size |
|----------------|-----------|----------|
| `api_key` | Cryptographically random | 256 bits minimum |
| `x509_certificate` | Ed25519 or ECDSA P-384 | Ed25519: 256-bit; P-384: 384-bit |
| `ssh_key` | Ed25519 (preferred), ECDSA P-384 | Ed25519: 256-bit |
| `service_account_token` | RS256 or ES256 | RSA: 4096-bit; EC: P-256 |
| `database_password` | Cryptographically random | 128-bit printable minimum |
| `kubeconfig` | As per cluster's auth configuration | — |
| `hsm_backed_key` | ECDSA P-384 or RSA-4096 | HSM-generated |
| `dcm_interaction` | HS256 or ES256 | AES-256 or P-256 |

### 13.3 Key Escrow Policy

DCM does not implement key escrow by default. For `sovereign` profile deployments, key escrow (if required by regulation) is declared in the Credential Provider's capability registration and governed by the provider — DCM's role is to audit that escrowed credentials are disclosed only via the standard revocation and access model:

```yaml
credential_provider_capabilities:
  key_escrow:
    supported: false           # default; no escrow
    # If true:
    escrow_model: m_of_n       # m-of-n key shares; Shamir's Secret Sharing
    escrow_quorum: "3 of 5"
    escrow_record_stored_by: hsm   # never by DCM
    dcm_role: audit_only           # DCM audits escrow access; does not participate
```

---

## 14. Idle Credential Detection

A credential issued but never retrieved within the declared threshold is a security signal — it may indicate a provisioning error, a failed delivery, or an abandoned resource.

```yaml
idle_credential_record:
  credential_uuid: <uuid>
  issued_at: <ISO 8601>
  threshold_hours: 48           # from profile credential_profile.idle_detection_threshold
  last_checked_at: <ISO 8601>
  retrieval_count: 0
  status: idle_alert_pending
```

When an idle alert fires:
- Platform admin notified: "Credential {uuid} for entity {entity_uuid} has not been retrieved in {N} hours"
- Consumer notified (if consumer exists): "Your credential for {resource_name} has not been accessed — confirm delivery"
- Credential is NOT automatically revoked — it remains valid until its `expires_at`
- If still idle after 2× the threshold: optional auto-revocation per profile configuration

---


## 11. System Policies

| Policy | Rule |
|--------|------|
| `CPX-001` | Credential values are never stored in DCM's data model, GitOps stores, Realized State Store, or Audit Store. Only credential metadata (UUID, type, scope, expiry, status) is stored in DCM. |
| `CPX-002` | Every DCM interaction with a provider must present a scoped, short-lived `dcm_interaction` credential. A provider that receives an interaction without a valid scoped credential must reject it with `403 Forbidden`. |
| `CPX-003` | Credential revocation must propagate to the Credential Revocation Registry within the declared `revocation_sla`. Components must refresh their revocation cache no less frequently than the profile-governed cache TTL (PT1M standard; PT30S fsi/sovereign). |
| `CPX-004` | Emergency rotation (security_event trigger) has no transition window. The old credential is revoked immediately. The new credential is delivered via the fastest available Notification Provider channel. |
| `CPX-005` | The first credential value retrieval is audited in ALL profiles (credential_uuid, actor_uuid, retrieved_at, retrieval_uuid). Subsequent retrievals are audited in standard+ profiles. Emergency retrievals (rotation, security event) are always audited regardless of profile. |
| `CPX-006` | Actor deprovisioning (via SCIM or manual) triggers immediate revocation of all credentials issued to that actor. Revocation events are published to the Message Bus before the deprovisioning event is acknowledged. |
| `CPX-007` | Entity decommissioning triggers revocation of all credentials scoped to that entity before the decommission is confirmed. A decommission that cannot revoke all credentials enters `COMPENSATION_IN_PROGRESS` state. |
| `CPX-008` | Credentials issued for `fsi` and `sovereign` profiles must be IP-bound (`bound_to_ip`) or hardware-attested (`hsm_backed_key`). Unbound credentials are rejected by the Governance Matrix for these profiles. |
| `CPX-009` | `algorithm` and `key_usage` must be declared on every credential record at issuance (standard+ profiles). The Credential Provider must validate `key_usage` at the validate endpoint — a credential issued for `authentication` cannot be used for `signing`. |
| `CPX-010` | Idle credential detection fires at the profile-governed threshold. Idle credentials are NOT automatically revoked — they trigger notification only. Auto-revocation after 2× threshold is profile-configurable. |
| `CPX-011` | Profile credential requirements are additive when compliance domains are active (HIPAA, PCI DSS, FedRAMP, DoD IL4). Compliance overlay requirements always tighten, never relax, the base profile. |
| `CPX-012` | CPX-001 (values never in DCM stores) applies in ALL profiles including `minimal`. There is no profile that permits credential values to be stored in DCM. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

## External CA Integration

DCM's Credential Provider model natively supports external Certificate Authorities as backends for the `x509_certificate` credential type. This is the correct place for enterprise PKI integration — not the Auth Provider.

### Supported Protocols

| Protocol | RFC | Common Implementations | Use case |
|----------|-----|------------------------|----------|
| ACME | RFC 8555 | Let's Encrypt, cert-manager, Venafi, DigiCert | Public and enterprise CAs with ACME support |
| EST | RFC 7030 | Cisco CA, Microsoft NDES, Venafi | Enterprise PKI, IoT, internal use |
| SCEP | RFC 8894 | Microsoft NDES, Cisco iOS CA | Legacy enterprise PKI, network equipment |
| CMP | RFC 4210 | EJBCA, OpenXPKI | High-assurance enterprise PKI |
| Native API | — | HashiCorp Vault PKI, AWS ACM PCA, Azure Key Vault | Cloud-native PKI |

### External CA Registration

```yaml
credential_provider_registration:
  provider_type: credential_provider
  credential_types: [x509_certificate]
  
  external_ca_config:
    ca_protocol: acme | est | scep | cmp | vault_pki | aws_acm_pca | azure_key_vault
    ca_endpoint: <url>
    
    # Protocol-specific
    acme_config:
      directory_url: <acme-directory-url>
      account_key_credential_uuid: <uuid>
      preferred_challenge: dns-01 | http-01 | tls-alpn-01
      
    vault_pki_config:
      vault_addr: <url>
      mount_path: pki
      role_name: dcm-internal
      vault_token_credential_uuid: <uuid>
      
    # Common to all
    ca_chain_pem: <base64-encoded CA chain>  # for trust store installation
    issued_cert_lifetime: P90D              # profile-governed; may be overridden by CA
    subject_template: "CN={{component_type}}-{{component_uuid}},O=dcm-internal"
```

### How DCM Uses External CA Credential Providers

When an external CA Credential Provider is registered and configured as the trust anchor for internal component auth (doc 36), DCM's component certificate requests flow through the Credential Provider interface instead of the built-in Internal CA:

```
Component needs certificate
  │
  ▼ Request to Credential Provider Proxy
  │   credential_type: x509_certificate
  │   subject: CN=<component_type>-<component_uuid>,O=dcm-internal
  │   san: [component_uuid, component_name, dns_name]
  │
  ▼ Credential Provider Proxy → External CA Credential Provider
  │   Issues certificate request via configured protocol (ACME/EST/Vault/etc.)
  │
  ▼ CA issues certificate (signed by enterprise root)
  │
  ▼ Certificate returned to component
  │   Component uses for mTLS — same as built-in CA path
  │   Certificate in enterprise PKI chain → auditable in enterprise tooling
```

This design means DCM's internal mTLS is fully auditable through existing enterprise PKI infrastructure when using an external CA — a key requirement for fsi and sovereign profiles.

