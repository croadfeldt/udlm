# UDLM — Credentials

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Specification — Credential lifecycle, types, contracts
**Related Documents:** [Provider Contract](../contracts/provider-contract.md) | [Auth Providers](auth-providers.md) | [Accreditation and Authorization Matrix](accreditation-and-authorization-matrix.md) | [Provider Callback Auth](../contracts/provider-callback-auth.md) | [Standards Catalog](../reference/standards-catalog.md)

> **Foundation Document Reference**
>
> Credentials in UDLM are first-class Data artifacts. A Credential Provider is a substrate-defined Provider type. The Zero Trust model in [Accreditation and Authorization Matrix](accreditation-and-authorization-matrix.md) governs credential scope and lifetime — this document specifies the substrate contract that any conformant realization MUST honor.
>
> **This document maps to: DATA + PROVIDER**

---

> **Cryptographic Standards:** See [Standards Catalog](../reference/standards-catalog.md) for the complete list of permitted/forbidden algorithms, FIPS requirements per profile, and certificate protocol RFCs (RFC 7030, RFC 8555, RFC 8894, RFC 4210).

## 1. Credential Scope

> **The realization brokers credentials; it does not hold or issue them.**
> Credential **values** are produced and held by a registered Credential Provider and flow **directly** to the
> authorized consumer (CPX-001) — the realization (DCM) never sees, stores, or relays a value. The realization's
> role is to **select** a provider, **scope** the request, **gate** on attestation, and **audit** — the same
> declare → select → attest pattern the Placement Engine uses for any resource. A request **declares** what it
> needs (credential type, scope, assurance); each candidate provider **declares** what it can issue and to what
> assurance level (its credential capability); the realization **selects** the provider that meets the profile's
> trust floor. This is the credential expression of the DCM Trust Model (DCM `ADR-022`): DCM is a trust **broker**,
> not a credential authority. See the DCM trust documents for the cross-plane model; this document specifies the
> UDLM substrate contract — the data model, lifecycle, and provider interface — that the brokering rests on.
>
> **"Credential Provider" is a capability, not a separate provider kind.** Any provider that declares the
> credential-issuing capability — `Credential.*` in `supported_resource_types` plus a `credential_capability`
> block — *is* a Credential Provider for those types. There is no distinct `credential_provider` provider type to
> register; see [Provider Contract](../contracts/provider-contract.md).

UDLM distinguishes two scopes of credential management. Both share the same data model, lifecycle vocabulary, and substrate contracts.

### 1.1 Realization-Internal Credentials

The realization maintains its own operational secrets — provider authentication credentials, encryption keys for data-at-rest on sensitive fields, audit signing keys, internal service credentials. UDLM does not mandate a specific storage technology, but it does mandate substrate invariants:

- Credential **values** MUST NEVER appear in the realization's data model, artifact stores, Realized State Store, or Audit Store.
- Credential **metadata** (UUID, type, scope, expiry, status) MAY appear in the realization's stores.
- Credential values are held exclusively by a registered Credential Provider.

### 1.2 Consumer-Facing Credentials

When consumers request credential resources (API keys, certificates, SSH keys, secrets) or when realized resources require credentials (kubeconfigs, database passwords, service account tokens), the substrate requires that the credentials are issued by a provider that declares the **credential capability** — `Credential.*` in `supported_resource_types` plus a `credential_capability` block. Any provider that declares this capability handles such requests through the standard provider dispatch pipeline; there is no separate provider *kind*. The capability declaration is what the realization **selects against** (declare-and-select): it states which credential types the provider can issue, the assurance it can reach, and the secret-engine/attestation backing — so the realization can pick a provider that satisfies the active profile's trust floor.

```yaml
provider:
  # No special provider_type — credential issuance is a declared capability, not a kind.
  supported_resource_types:
    - "Credential.Secret"
    - "Credential.Certificate"
    - "Credential.SSHKey"
    - "Credential.APIKey"
  credential_capability:
    credential_types: [secret, x509_certificate, ssh_key, api_key]
    max_assurance: aal3            # highest AAL this provider can satisfy (NIST 800-63B; §12.2)
    attestation:                   # what the provider can attest about how values are protected
      level: hardware_attested     # self_asserted | vendor_attested | independently_verified | accredited | hardware_attested
      secret_engine: local_hsm     # vault | aws_secrets_manager | azure_key_vault | gcp_secret_manager | local_hsm
      fips_140_level: 3
    hsm_support: true
    rotation_protocol: automatic
    dynamic_secrets: true
    max_secret_size_bytes: 65536
    supported_algorithms: [rsa-2048, rsa-4096, ecdsa-p256, ecdsa-p384, ed25519]
```

The realization **selects** among providers declaring the needed `Credential.*` type by matching `credential_capability.max_assurance` and `attestation.level` against the profile's required floor (a `sovereign` profile may demand `hardware_attested` + `fips_140_level: 3`), then scoring on the usual placement signals. A provider whose declared (and verified) attestation does not meet the floor is filtered out before selection — a *claim* of capability is not *trust* in it (see DCM `ADR-022`, attestation ladder).

---

## 2. Credential Types (Closed Substrate Vocabulary)

| Credential Type | Resource Type | Use Case | Typical Lifetime | Rotation Trigger |
|----------------|--------------|----------|-----------------|-----------------|
| `dcm_interaction` | — | Component-to-provider auth for internal interactions | PT15M–PT1H (profile-governed) | Automatic; pre-expiry |
| `api_key` | `Credential.APIKey` | Programmatic consumer access | PT24H–P30D (configurable) | Scheduled or event-triggered |
| `jwt` | `Credential.JWT` | JSON Web Token with claims, issued by auth_provider | Short-lived | Per claim policy |
| `x509_certificate` | `Credential.Certificate` | mTLS identity for providers and components | P30D–P365D | P14D before expiry |
| `ssh_key` | `Credential.SSHKey` | SSH access to realized infrastructure | P30D–P90D (configurable) | Scheduled or on-demand |
| `secret` | `Credential.Secret` | Arbitrary secret value (password, connection string) | Per type defaults | Scheduled or on-demand |
| `signing_key` | `Credential.SigningKey` | Cryptographic key for signing operations | Per algorithm defaults | Pre-expiry |
| `service_account_token` | — | Workload identity for automated processes | PT1H–PT24H | Automatic; pre-expiry |
| `database_password` | — | Access credential for realized database resources | PT24H–P7D (configurable) | Scheduled or on-demand |
| `kubeconfig` | — | Access to realized Kubernetes clusters | PT8H–P30D (configurable) | Scheduled or on-demand |
| `hsm_backed_key` | — | Sovereign/FSI deployments requiring hardware attestation | P30D–P365D | P14D before expiry; HSM-managed |

The `Credential.*` resource types follow standard substrate resource-type contracts; the credential-type identifiers above are also closed substrate vocabulary used in credential records and provider declarations.

---

## 3. Credential Data Model (Wire Contract)

A credential is a UDLM Data artifact. Credential metadata is stored by the realization; credential **values** are held only by the Credential Provider (never in the realization's stores).

```yaml
credential_record:
  credential_uuid: <uuid>
  credential_type: api_key | x509_certificate | ssh_key | service_account_token |
                   database_password | kubeconfig | hsm_backed_key | dcm_interaction |
                   jwt | secret | signing_key

  # Lifecycle
  status: pending | active | rotating | revoked | expired
  issued_at: <ISO 8601>
  expires_at: <ISO 8601>
  last_rotated_at: <ISO 8601 | null>
  revoked_at: <ISO 8601 | null>
  revocation_reason: <string | null>

  # Scope — what this credential authorizes
  issued_to:
    actor_uuid: <uuid | null>          # consumer credential: issued to an actor
    entity_uuid: <uuid | null>         # resource credential: scoped to an entity
    component_uuid: <uuid | null>      # interaction credential: issued to a realization component
    provider_uuid: <uuid | null>       # interaction credential: scoped to a provider
  scope:
    operations: [dispatch, discover, query, read, write, admin]  # allowed operations
    resource_types: [Compute.VirtualMachine]                     # scoped resource types
    tenant_uuid: <uuid | null>                                   # Tenant scope
  non_transferable: true               # always true for substrate-issued credentials
  bound_to_ip: <IP | null>             # optional; enforced in fsi/sovereign profiles

  # Provenance
  credential_provider_uuid: <uuid>
  issuing_request_uuid: <uuid>         # which request triggered issuance
  entity_uuid: <uuid | null>           # the realized entity this credential accesses
  rotation_of: <credential_uuid | null>  # parent credential UUID if this is a rotation

  # Storage (values never in the realization's stores)
  value_held_by: <credential_provider_uuid>
  value_retrieval_endpoint: <url>      # how the authorized consumer retrieves the value
  value_retrieval_auth: bearer_token | mtls | step_up_mfa

  # Cryptographic metadata
  algorithm: Ed25519 | ECDSA-P-384 | RSA-4096 | HS256 | RS256 | random_256bit
  key_usage: [authentication]   # authentication | signing | encryption; declared at issuance
  retrieved_count_threshold: 48  # hours; idle alert fires if not retrieved within this window
```

### 3.1 Credential Value Separation

Credential values are never stored in the realization's data model, artifact stores, or Realized State Store. The realization stores only the credential metadata record. The credential value is held exclusively by the Credential Provider.

**`scope.resource_types` is not a read-grant.** It records which resource *types* a credential is valid *for* (e.g. a credential usable when acting on `Compute.VirtualMachine`) — it does **not** mean every resource of that type can read the value. Reading a value is a separate, per-credential authenticated and authorized act (next paragraph): the requester must be the credential's `issued_to` actor/entity, satisfy `value_retrieval_auth`, and pass the Governance Matrix. Scope narrows what a credential *authorizes*; it never widens who can *retrieve* it.

Authorized consumers retrieve the credential value via `value_retrieval_endpoint` — which resolves to the **registered Credential Provider that holds the value**, not a realization-core endpoint (the value flows producer → consumer directly; the realization is never on the value path, CPX-001). Retrieval uses `value_retrieval_auth`, is itself authenticated — typically a short-lived bearer token or mTLS — and is audited.

---

## 4. Credential Lifecycle

```
PENDING → ACTIVE → ROTATING → ACTIVE (new value)
                 → REVOKED
                 → EXPIRED
```

| State | Description |
|-------|------------|
| `PENDING` | Credential requested, not yet issued |
| `ACTIVE` | Credential is valid and in use |
| `ROTATING` | New credential issued, old credential in grace period |
| `REVOKED` | Credential permanently invalidated (security event or decommission) |
| `EXPIRED` | Credential reached TTL without renewal |

### 4.1 Issuance Flow Contract

A credential a resource needs is **a dependency like any other** — not a bespoke field. When a resource type requires a credential, that is expressed with the **same `requires` relationship** the dependency model uses for every other dependency (see [Entity Relationships](../entities/entity-relationships.md)): the dependent declares a `requires` edge to a `Credential.*` resource type, and Dependency Resolution issues a sub-request that Placement routes to a provider declaring the matching credential capability. There is no parallel `credential_requirements` mechanism — credentials reuse the dependency graph so that ordering, blast-radius, and lifecycle coupling come for free.

> **Worked example (grounds the use case).** A consumer requests `Compute.VirtualMachine`. The catalog item for that VM declares `requires: Credential.SSHKey` (so SSH access to the realized VM is provisioned automatically — no human key-paste, no long-lived shared key). After the VM realizes, Dependency Resolution emits a credential sub-request; Placement **selects a provider that declares the `Credential.SSHKey` capability at the profile's required assurance** and dispatches to it; **that provider** — not the realization — generates and holds the key, returning only metadata. The same pattern covers an application that `requires: Credential.Secret` for a database password, or a service that `requires: Credential.Certificate` for mTLS identity. In every case the realization **brokers** (selects, scopes, gates on attestation, audits); a Credential **Provider** issues and holds the value (CPX-001). DCM never issues a credential.

```
Consumer requests resource (e.g., Compute.VirtualMachine)
  │
  ▼ Layer assembly + policy evaluation
  │   Dependency Resolution reads the type's `requires` edges, e.g.:
  │     requires:
  │       - resource_type: Credential.SSHKey   # ordinary dependency, not a special field
  │         issued_to: requesting_actor
  │         scope: [ssh_access]
  │
  ▼ Placement selects the Service Provider for the VM
  │
  ▼ After VM realization: credential sub-request placed against
  │   providers declaring the Credential.SSHKey capability
  │   Placement filters on credential_capability (type + assurance +
  │   attestation level ≥ profile trust floor), then scores + selects
  │
  ▼ Selected Credential Provider receives the sub-request:
  │     entity_uuid: <vm_entity_uuid>
  │     credential_type: ssh_key
  │     issued_to.actor_uuid: <requesting_actor_uuid>
  │     scope.operations: [ssh_access]
  │     scope.resource_types: [Compute.VirtualMachine]
  │     expires_at: <now + profile_lifetime>
  │
  ▼ Credential Provider issues credential; returns credential_record
  │   (value held by provider; only metadata returned to the realization)
  │
  ▼ The realization writes credential_record to Realized State
  │   Links credential_uuid to entity_uuid (the dependency edge)
  │
  ▼ Consumer receives realized entity + credential_record metadata
  │   Consumer calls value_retrieval_endpoint (the provider's) to get the value
  │   (step-up MFA may be required per profile)
```

### 4.2 Interaction Credential Issuance Flow

Interaction credentials carry the **same zero-standing-trust rationale** as every other dispatch in the system (see [Provider Contract](../contracts/provider-contract.md) §provider auth): each interaction presents a freshly issued, narrowly scoped, short-lived credential rather than a long-lived shared key, so a leaked credential expires fast and every use is attributable and audited. They are issued automatically before each provider interaction:

```
The realization prepares to dispatch to a provider
  │
  ▼ Request interaction credential from Credential Provider:
  │   credential_type: dcm_interaction
  │   issued_to.component_uuid: <gateway_uuid>
  │   issued_to.provider_uuid: <target_provider_uuid>
  │   scope.operations: [dispatch]
  │   scope.resource_types: [Compute.VirtualMachine]
  │   entity_uuid: <entity_being_dispatched>
  │   expires_at: <now + PT15M>  (max; profile-governed)
  │
  ▼ Credential Provider issues scoped interaction credential
  │
  ▼ Credential included in provider dispatch
  │   Provider validates credential scope before executing
  │
  ▼ Credential expires after declared lifetime regardless of use
  │   (no renewal; new credential issued for next interaction)
```

### 4.3 Bootstrap Credential Issuance

Credential issuance has a chicken-and-egg problem: the realization needs a credential to talk to the first Credential Provider, but a Credential Provider cannot have issued it yet. The substrate resolves this with a one-time **bootstrap credential** — a short-lived, single-purpose anchor (a kubeadm/SPIRE-style bootstrap token or a pre-placed mTLS identity; the anchor type is profile-governed) whose **only** authorized scope is registering and authenticating to the first Credential Provider. The handoff is explicit and one-way:

```
Bootstrap anchor present (out-of-band; single-purpose; short TTL)
  │
  ▼ Realization registers + authenticates to the first Credential Provider
  │   using the bootstrap credential (its only permitted use)
  │
  ▼ Provider registered → realization requests its real interaction credential
  │   from the now-registered Credential Provider
  │
  ▼ Bootstrap credential revoked/expired (no further use)
  │   From here, ALL credentials flow through registered Credential Providers
```

After the handoff the bootstrap path is closed; there is no standing bootstrap credential. The bootstrap anchor is itself a `trust anchor` in the DCM Trust Model sense (DCM `ADR-022`); its `anchor_type` is selected by profile (homelab may use a TOFU/self-asserted anchor, sovereign demands a hardware-attested one).

---

## 5. Rotation Protocol (Parallel Validity)

Rotation is the primary mechanism for maintaining credential hygiene. The substrate distinguishes scheduled rotation, pre-expiry rotation, and event-triggered rotation. The two-phase parallel-validity contract is normative.

### 5.1 Rotation Triggers (Closed Substrate Vocabulary)

| Trigger | Description | Default behavior |
|---------|-------------|-----------------|
| `scheduled` | Regular rotation on a declared schedule | Most credential types; interval is credential-type specific |
| `pre_expiry` | Rotation initiated before the current credential expires | x509: P14D before expiry; ssh_key: P7D; dcm_interaction: PT5M |
| `provider_initiated` | Credential Provider notifies the realization of a rotation requirement | Handled via provider update notification model |
| `security_event` | Rotation triggered by a security signal (compromise, anomaly, policy change) | Immediate; see §5.4 |
| `actor_request` | Consumer requests rotation of their own credential | Subject to rate limiting and policy |

### 5.2 Two-Phase Rotation Protocol

Rotation uses a transition window to prevent downtime. The old credential remains valid during the transition window; the new credential is issued and delivered before the old one expires.

```
Rotation initiated (by any trigger):
  │
  ▼ The realization requests a new credential from Credential Provider
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

### 5.3 Rotation Notification (Wire Contract)

Before the old credential is revoked, the realization sends a rotation notification to any entity or actor whose credential is rotating:

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

On detection of a compromise or security event, the realization MUST trigger emergency rotation:

- No transition window — old credential revoked immediately
- New credential issued and delivered via the fastest available notification channel
- Security event record written to Audit Store with full context
- Compliance-class Validation Policy firing for this entity type audited against the event
- Platform admin notified regardless of profile

Closed substrate vocabulary for emergency rotation triggers:

```
security.credential_compromised      # realization or provider reports compromise
security.anomalous_usage_detected    # unusual access pattern detected
actor.deprovisioned                  # actor removed; all their credentials revoked
provider.deregistered                # provider leaving; all its interaction creds revoked
accreditation.revoked                # provider accreditation revoked; creds reassessed
```

---

## 6. Revocation Model and Propagation

Revocation makes a credential permanently invalid before its natural expiry. Unlike rotation (which maintains continuity), revocation is an immediate termination.

### 6.1 Revocation Triggers (Closed Substrate Vocabulary)

| Trigger | Initiator | Behavior |
|---------|-----------|----------|
| `actor_deprovisioned` | SCIM / Auth Provider | All credentials issued to the actor revoked immediately |
| `entity_decommissioned` | Lifecycle | All credentials scoped to the entity revoked |
| `security_event` | Platform admin or security automation | Immediate; no transition window |
| `provider_deregistered` | Platform admin | All interaction credentials for the provider revoked |
| `actor_request` | Consumer | Consumer may revoke their own credentials |
| `ttl_expired` | Lifecycle Constraint Enforcer | Credential expired; revocation recorded |

### 6.2 Revocation Propagation Contract

The realization MUST maintain a **Credential Revocation Registry** — a fast-queryable store of revoked credential UUIDs. All components that receive interaction credentials MUST check this registry at each use (not just at issuance time).

```
Credential revoked:
  │
  ▼ Credential record status: active → revoked
  │   revoked_at, revocation_reason written
  │
  ▼ Revocation event published to the realization's event bus
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

Providers receiving interaction credentials MUST validate the credential at use time, not only at receipt time:

1. Verify credential signature (if signed)
2. Check credential UUID against local revocation cache
3. Verify credential has not expired (`expires_at`)
4. Verify operation is within credential scope
5. Verify IP binding if `bound_to_ip` is set

A credential that passes issuance validation but fails use-time validation MUST be rejected. The provider MUST return `403 Forbidden` with `credential_revoked` or `credential_expired` error code.

---

## 7. Consumer Credential Delivery (Substrate Contract)

### 7.1 The Delivery Contract

Consumers never receive credential values directly through the substrate's API surface. Instead, the realization returns a **credential reference** — a provider-issued retrieval endpoint that the consumer's application resolves at runtime.

The consumer's application uses its own authentication (Kubernetes service account, AppRole, etc.) to retrieve the actual value. The audit trail records that the credential reference was issued — not the credential value.

### 7.2 Credential Retrieval API (Wire Contract)

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

```
GET /api/v1/credentials/{credential_uuid}/value
Authorization: Bearer <session-token>
X-StepUp-Token: <completed-challenge>  # if auth_required: step_up_mfa

Response 200:
{
  "credential_uuid": "<uuid>",
  "credential_type": "ssh_key",
  "value": {
    "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\n...",
    "public_key": "ssh-ed25519 AAAA... issued@entity-<uuid>",
    "username": "provisioned"
  },
  "expires_at": "<ISO 8601>",
  "retrieval_uuid": "<uuid>"   # idempotency key for this retrieval event; audited
}

Response 404:  credential_uuid not found or not associated with an entity the actor owns
Response 403:  step_up_mfa required but not completed
Response 410:  credential revoked or expired
```

Every value retrieval is audited: `credential_uuid`, `actor_uuid`, `retrieved_at`, `retrieval_uuid`.

---

## 8. Credential Provider API Contract (Normative)

A conformant Credential Provider MUST implement the following endpoint contract.

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

## 9. Credential Provider Registration (Wire Contract)

This is the full `credential_capability` declaration a provider registers (the summary form appears in §1.2). It is a **capability block on an ordinary provider**, not a distinct provider kind — `max_assurance` and `attestation` are what the realization selects against (declare-and-select; §4.1).

```yaml
credential_capability:        # declared on any provider that issues Credential.* types
  # Highest assurance + attestation this provider can satisfy (the select-against fields)
  max_assurance: aal3         # NIST 800-63B AAL (§12.2)
  attestation:
    level: hardware_attested  # self_asserted | vendor_attested | independently_verified | accredited | hardware_attested
    fips_140_level: 3

  # Credential types this provider can issue
  credential_types:
    - api_key
    - x509_certificate
    - ssh_key
    - service_account_token
    - database_password
    - kubeconfig
    - hsm_backed_key
    - dcm_interaction         # must declare if provider handles interaction creds

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

## 10. Cryptographic Requirements

UDLM defers algorithm specifics to the [Standards Catalog](../reference/standards-catalog.md). The substrate enforces the following invariants:

### 10.1 Algorithm Declaration

The credential record carries two normative cryptographic-metadata fields:

```yaml
credential_record:
  # ... existing fields ...
  algorithm: Ed25519 | ECDSA-P-384 | RSA-4096 | HS256 | RS256 | random_256bit | ...
  key_usage: [authentication, signing, encryption]   # declared at issuance; non-overlapping
  retrieved_count_threshold: 48           # hours after issuance before idle alert fires
```

`key_usage` enforces the principle of algorithm agility and purpose separation. A credential issued for `authentication` MUST NOT be used for `signing` even if the underlying algorithm supports both. The Credential Provider MUST validate `key_usage` at the validate endpoint.

### 10.2 Profile-Governed Minimums (Substrate Defaults)

| Profile | Minimum Key Size | Allowed Algorithms |
|---------|-----------------|-------------------|
| `minimal`, `dev` | RSA-2048, ECDSA P-256 | RSA, ECDSA, Ed25519 |
| `standard`, `prod` | RSA-3072, ECDSA P-256 | RSA, ECDSA, Ed25519 |
| `fsi`, `sovereign` | RSA-4096, ECDSA P-384 | RSA, ECDSA, Ed25519 (no RSA-2048) |

Forbidden algorithms in all profiles: MD5, SHA-1, DES, 3DES, RC4, RSA-1024, RSA-512, DSA-1024. The forbidden list is non-negotiable; it applies even to the `minimal` profile.

HSM backing is required for `sovereign` profile signing keys.

### 10.3 Approved Algorithm Defaults (Standard Profile)

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

### 10.4 Key Escrow

UDLM does not mandate key escrow. For `sovereign` profile deployments where key escrow is required by regulation, the Credential Provider declares escrow capability in its registration:

```yaml
credential_capability:
  key_escrow:
    supported: false           # default; no escrow
    # If true:
    escrow_model: m_of_n       # m-of-n key shares; Shamir's Secret Sharing
    escrow_quorum: "3 of 5"
    escrow_record_stored_by: hsm   # never by the realization
    role: audit_only               # realization audits escrow access; does not participate
```

---

## 11. Idle Credential Detection

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

Substrate invariant: idle detection is required in ALL profiles. The threshold and remediation action vary; the detection MUST be present.

---

## 12. Registration + Profile-Governed Configuration Vocabulary

Every credential security dimension is controlled by the active profile. This is the substrate-defined configuration vocabulary. Specific values within each dimension MAY vary per realization; the dimensions themselves are normative.

### 12.1 Credential Profile Configuration Block

```yaml
credential_profile:

  # --- Credential Type Restrictions ---
  permitted_credential_types:
    minimal:   [api_key, x509_certificate, ssh_key, service_account_token, database_password]
    dev:       [api_key, x509_certificate, ssh_key, service_account_token, database_password, kubeconfig]
    standard:  [api_key, x509_certificate, ssh_key, service_account_token, database_password, kubeconfig]
    prod:      [api_key, x509_certificate, ssh_key, service_account_token, database_password, kubeconfig]
    fsi:       [x509_certificate, ssh_key, service_account_token, database_password, kubeconfig, hsm_backed_key]
    sovereign: [x509_certificate, hsm_backed_key]     # all credentials must be hardware-backed

  # --- Lifetime Limits ---
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
    standard:   bearer_token    # step_up_mfa for sensitive types
    prod:       step_up_mfa     # all credential types require step-up
    fsi:        step_up_mfa     # hardware token MFA required
    sovereign:  mtls            # mutual TLS + hardware attestation
  step_up_sensitive_types:      # standard profile: step_up_mfa for these types
    - ssh_key
    - database_password
    - kubeconfig
    - hsm_backed_key

  # --- Retrieval Audit ---
  audit_every_retrieval:
    # Security-first: FIRST retrieval is always audited in ALL profiles (CPX-005).
    # audit_every_retrieval controls whether SUBSEQUENT retrievals are also audited.
    minimal:    false           # subsequent retrievals silent; first always audited
    dev:        false           # subsequent retrievals silent; first always audited
    standard:   true            # every retrieval audited
    prod:       true
    fsi:        true
    sovereign:  true
  idle_detection_threshold:     # alert if credential not retrieved within N after issuance
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

  # --- Revocation ---
  revocation_check_frequency:   # how often components must refresh revocation cache
    minimal:    PT5M
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

Profile credential requirements map to NIST 800-63B Authenticator Assurance Levels:

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

### 12.4 Design Priority and Cross-Profile Consistency

UDLM's design priority order applies directly to credential management:

1. **Security first:** Security properties — value separation, rotation, audit, idle detection, algorithm baselines, revocation — are architecturally present in ALL profiles. What profiles control is enforcement strictness, threshold values, and automation level. A `minimal` profile is "security with minimal operational overhead" — not "minimal security."

2. **Ease of use second:** The secure path must be the easy path. Homelab deployments use the same API contract, same data model, and same provider interface as sovereign deployments. The profile system eliminates the need to choose between security and operational simplicity.

3. **Extensibility third:** Compliance domain overlays, profile overrides, and algorithm configuration make the credential model adaptable without code changes.

Profile variation applies only to **enforcement level and required features** — never to the underlying protocol or data model. A credential issued under the `minimal` profile has the same data structure, the same API contract, the same revocation mechanism, and the same audit record format as one issued under the `sovereign` profile.

**CPX-001 (values never in the realization's stores) is non-negotiable in every profile including `minimal`.**

---

## 13. External CA Integration (Substrate Contract)

UDLM's Credential Provider model natively supports external Certificate Authorities as backends for the `x509_certificate` credential type. This is the correct place for enterprise PKI integration — not the Auth Provider.

### 13.1 Supported Protocols

| Protocol | RFC | Common Implementations | Use case |
|----------|-----|------------------------|----------|
| ACME | RFC 8555 | Let's Encrypt, cert-manager, Venafi, DigiCert | Public and enterprise CAs with ACME support |
| EST | RFC 7030 | Cisco CA, Microsoft NDES, Venafi | Enterprise PKI, IoT, internal use |
| SCEP | RFC 8894 | Microsoft NDES, Cisco iOS CA | Legacy enterprise PKI, network equipment |
| CMP | RFC 4210 | EJBCA, OpenXPKI | High-assurance enterprise PKI |
| Native API | — | HashiCorp Vault PKI, AWS ACM PCA, Azure Key Vault | Cloud-native PKI |

### 13.2 External CA Registration

```yaml
credential_provider_registration:
  # credential issuance is a declared capability, not a provider_type
  credential_capability:
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
      role_name: internal
      vault_token_credential_uuid: <uuid>

    # Common to all
    ca_chain_pem: <base64-encoded CA chain>  # for trust store installation
    issued_cert_lifetime: P90D              # profile-governed; may be overridden by CA
    subject_template: "CN={{component_type}}-{{component_uuid}},O=internal"
```

---

## 14. UDLM System Policies

| Policy | Rule |
|--------|------|
| `CPX-001` | Credential values are never stored in the realization's data model, artifact stores, Realized State Store, or Audit Store. Only credential metadata (UUID, type, scope, expiry, status) is stored. |
| `CPX-002` | Every interaction with a provider must present a scoped, short-lived `dcm_interaction` credential. A provider that receives an interaction without a valid scoped credential MUST reject it with `403 Forbidden`. |
| `CPX-003` | Credential revocation must propagate to the Credential Revocation Registry within the declared `revocation_sla`. Components must refresh their revocation cache no less frequently than the profile-governed cache TTL (PT1M standard; PT30S fsi/sovereign). |
| `CPX-004` | Emergency rotation (security_event trigger) has no transition window. The old credential is revoked immediately. The new credential is delivered via the fastest available notification channel. |
| `CPX-005` | The first credential value retrieval is audited in ALL profiles (credential_uuid, actor_uuid, retrieved_at, retrieval_uuid). Subsequent retrievals are audited in standard+ profiles. Emergency retrievals (rotation, security event) are always audited regardless of profile. |
| `CPX-006` | Actor deprovisioning triggers immediate revocation of all credentials issued to that actor. Revocation events are published to the realization's event bus before the deprovisioning event is acknowledged. |
| `CPX-007` | Entity decommissioning triggers revocation of all credentials scoped to that entity before the decommission is confirmed. A decommission that cannot revoke all credentials enters `COMPENSATION_IN_PROGRESS` state. |
| `CPX-008` | Credentials issued for `fsi` and `sovereign` profiles must be IP-bound (`bound_to_ip`) or hardware-attested (`hsm_backed_key`). Unbound credentials are rejected by the Governance Matrix for these profiles. |
| `CPX-009` | `algorithm` and `key_usage` must be declared on every credential record at issuance (standard+ profiles). The Credential Provider must validate `key_usage` at the validate endpoint — a credential issued for `authentication` cannot be used for `signing`. |
| `CPX-010` | Idle credential detection fires at the profile-governed threshold. Idle credentials are NOT automatically revoked — they trigger notification only. Auto-revocation after 2× threshold is profile-configurable. |
| `CPX-011` | Profile credential requirements are additive when compliance domains are active (HIPAA, PCI DSS, FedRAMP, DoD IL4). Compliance overlay requirements always tighten, never relax, the base profile. |
| `CPX-012` | CPX-001 (values never in the realization's stores) applies in ALL profiles including `minimal`. There is no profile that permits credential values to be stored by the realization. |

---

*UDLM substrate document. Realization-specific credential storage and access control implementation, credential generation code, issuance flow orchestration, rotation job scheduling, revocation enforcement code, consumer delivery mechanics, provider authentication validation pipelines, profile-governed enforcement, and integration with specific external services live in the consuming realization's documentation.*
