# UDLM — Provider Callback Authentication Contract

**Document Status:** ✅ Stable — UDLM substrate contract (mechanism-neutral)
**Document Type:** Substrate Reference
**Related Documents:** [Provider Contract](provider-contract.md) | [Credentials](../governance/credentials.md) | [Accreditation, Auth Matrix, Zero Trust](../governance/accreditation-and-authorization-matrix.md) | [Schema Sharing](schema-sharing.md) | [Identifier Scheme](identifier-scheme.md)

> **Foundation Document Reference**
>
> This document maps to: **PROVIDER** (authentication of the provider-to-peer interaction boundary)
> and **DATA** (the credential artifact that governs that boundary).
>
> See [foundations.md](../foundations/foundations.md), [provider-contract.md](provider-contract.md), [policy-contract.md](policy-contract.md).

---

## 1. Purpose and Scope

This document specifies the **substrate contract** by which Service Providers authenticate inbound calls to a UDLM-conformant realization — specifically, calls to the provider callback surface:

- Provider registration
- Capacity reporting
- Realized state push
- Interim progress reporting
- Authorized state-change notification (Provider Update Notification)
- Notification status polling
- Lifecycle event reporting

The substrate contract is deliberately **mechanism-neutral**. UDLM defines *what* must be authenticated and *what* properties the authentication must guarantee; specific cryptographic mechanisms (mTLS, signed JWTs, hardware-bound assertions, HSM-attested tokens, etc.) are realization choices that MUST be declared via the [schema-sharing protocol](schema-sharing.md) so that federation peers can interoperate.

This means: a UDLM peer realization MAY choose mTLS + interaction-credential (the DCM realization's choice), or it MAY choose signed JWTs with replay protection, or any other two-factor mechanism that satisfies the contract below. Conformance is at the contract level, not the mechanism level.

The outbound model (the realization authenticating to providers) is specified in [credentials.md](../governance/credentials.md) and [accreditation-and-authorization-matrix.md](../governance/accreditation-and-authorization-matrix.md). This document specifies the **inbound** model.

---

## 2. The Authentication Problem (Substrate)

When a realization receives a callback, it MUST verify five properties:

1. **Identity:** Is this call genuinely from the registered Service Provider for this resource?
2. **Authorization:** Is this provider permitted to perform this operation on this specific resource/entity?
3. **Integrity:** Has the payload been tampered with in transit?
4. **Freshness:** Is this a live call, not a replayed credential from a previous session?
5. **Scope:** Is this credential permitted for this specific operation type?

Network-level authentication alone (firewall rules, IP allowlisting) is insufficient under the substrate's zero-trust model — it establishes perimeter trust, not per-call identity. Every provider call to a UDLM realization MUST carry credentials that answer all five questions independently of network position.

---

## 3. Two-Layer Authentication Contract (Abstract)

The substrate REQUIRES that a UDLM-conformant realization validate every provider callback via **two independent identity factors**:

- **Layer 1 — Identity Attestation Factor:** A factor that proves *who* is calling. The factor MUST be cryptographically bound to the entity that registered (i.e., possession of the factor proves the caller is the same party that registered). Substrate-compliant mechanisms include but are not limited to: mTLS certificates, signed registration assertions, HSM-attested keys.

- **Layer 2 — Operation Authorization Factor:** A factor that proves *this specific call* is authorized for this specific operation type. The factor MUST be scoped (cannot be used outside its declared operation set), short-lived (subject to rotation), and bound to the registered provider identity. Substrate-compliant mechanisms include but are not limited to: scoped bearer credentials, signed per-call assertions, capability tokens.

**Both layers MUST pass for any callback to be accepted.** Network position is not a substitute for either layer.

```
Provider calls peer realization:
  │
  ▼ Layer 1: Identity Attestation Factor
  │   Provider presents its identity attestation
  │   The realization validates the attestation against the provider's registration
  │   Proves: this connection is from the registered provider
  │   Does NOT prove: authorization for this specific operation
  │
  ▼ Layer 2: Operation Authorization Factor
  │   Provider presents a scoped operation-authorization factor
  │   The realization validates: factor is active, scoped to this provider, scoped to this operation type
  │   Proves: this specific call is authorized for this specific operation
  │   Does NOT replace Layer 1 — both layers are required
  │
  ▼ Both pass → five-check boundary model evaluates
  └── Audit record written regardless of outcome
```

**Why two layers?** Layer 1 proves the caller possesses the factor cryptographically bound to the registered identity. Layer 2 proves the specific call is authorized for the specific operation type and scope. A compromised Layer 2 factor without Layer 1 cannot pass identity attestation. A valid Layer 1 without a valid Layer 2 cannot perform operations. The layers are complementary, not redundant.

**Mechanism declaration:** Each realization MUST declare its chosen Layer 1 and Layer 2 mechanisms via the [schema-sharing protocol](schema-sharing.md) so federation peers and providers can interoperate.

---

## 4. Provider Identity Attestation Contract (Layer 1)

The substrate requires that a UDLM realization attest provider identity at registration via a verifiable mechanism. The realization's chosen mechanism MUST satisfy the following contract properties:

### 4.1 Registration-Time Identity Binding

At registration, the realization MUST capture verifiable identity-binding material for the provider. This material MUST be:

- Cryptographically bound (the provider must demonstrate possession of a private key or equivalent)
- Verifiable on every subsequent inbound call
- Subject to rotation (the realization MUST support rotation of identity material on a declared interval)
- Subject to revocation (the realization MUST be able to revoke the identity binding)

The specific format (X.509 certificate, signed JWT key pair, HSM key, ed25519 signing key, etc.) is a realization choice. The provider's registration record MUST include a mechanism declaration so federation peers can resolve verification.

### 4.2 Inbound Identity Verification

On every subsequent inbound connection, the realization MUST verify the presented Layer 1 factor:

1. The factor is cryptographically valid (signature/chain checks)
2. The factor matches the binding material stored at registration for the calling provider
3. The factor is not in the Credential Revocation Registry
4. The factor has not expired

Verification failure MUST result in rejection (connection refusal, 401, or equivalent) and an audit record.

### 4.3 Identity Rotation

Providers MUST rotate Layer 1 identity material on the declared rotation interval. The substrate requires:

- A pre-expiry warning is issued at a declared lead time (e.g., P14D for long-lived certificates)
- A transition window during which both old and new identity material are accepted
- After the transition window, only the new identity material is accepted
- All rotations are audited

### 4.4 Identity Binding Is Not Operation Authorization

The Layer 1 identity factor by itself does NOT grant operation authorization. Knowing a call came from Provider X does not mean Provider X is authorized to push realized state for entity Y owned by Tenant Z. Operation authorization comes from Layer 2.

---

## 5. Callback Credential Contract (Layer 2)

### 5.1 Substrate-Defined Properties

The substrate defines the following properties of the Layer 2 callback credential. The cryptographic format (opaque bearer token, signed JWT, capability macaroon, etc.) is a realization choice.

```yaml
callback_credential:
  credential_uuid: <uuid>
  credential_type: <substrate-defined: dcm_interaction (or realization-declared equivalent)>
  issued_to:
    provider_uuid: <uuid>      # the specific registered provider
    provider_handle: <string>  # for human-readable audit records
  issued_at: <ISO 8601>
  expires_at: <ISO 8601>      # profile-governed lifetime
  operation_scope:
    allowed_operations:
      - realized_state_push
      - capacity_report
      - interim_status
      - update_notification
      - lifecycle_event
      - notification_poll
      # Note: registration uses a registration_token, not this credential
    # Scope is bound to the provider_uuid — cannot be used for other providers
  non_transferable: true
  bound_to_ip: <IP|null>       # fsi/sovereign profiles: IP-bound
  revocation_check_url: <substrate revocation endpoint>
```

**Key substrate property:** The credential is scoped to the `provider_uuid` — not to specific entities or operations within that provider. Entity-level scope is enforced separately (Section 6). A provider holding the credential can call any callback endpoint in its scope, but the realization MUST enforce entity-level ownership checks per call.

### 5.2 Credential Lifecycle (Technology-Neutral)

The substrate requires the following credential lifecycle states. Specific issuance, delivery, and rotation mechanisms are realization choices.

```
Registration approved (provider status → ACTIVE)
  │
  ▼ Realization issues Layer 2 callback credential
  │   Bound to the activated provider
  │   Scoped to the substrate-defined callback operation vocabulary
  │   Expiry set per active profile
  │
  ▼ Credential delivered to provider
  │   Delivery mechanism is realization-declared
  │   Bootstrap delivery typically requires the single-use registration token
  │
  ▼ Provider stores credential securely and presents it on callbacks
  │
  ▼ Pre-expiry rotation
  │   Realization issues a new credential before expiry
  │   Transition window during which both old and new are accepted
  │   After transition window: old credential revoked
  │
  ▼ Revocation (immediate)
  │   Revocation event published
  │   All components reject the revoked credential within revocation SLA
```

### 5.3 Credential Lifetime by Profile (Substrate Defaults)

| Profile | Lifetime | Rotation trigger | IP binding |
|---------|----------|-----------------|------------|
| minimal | PT8H | Pre-expiry P1H | No |
| dev | PT4H | Pre-expiry P30M | No |
| standard | PT1H | Pre-expiry PT10M | No |
| prod | PT30M | Pre-expiry PT5M | Optional |
| fsi | PT15M | Pre-expiry PT3M | Required |
| sovereign | PT15M + hardware attestation | Pre-expiry PT3M | Required; HSM-bound |

The substrate requires that lifetime monotonically decrease with stricter profiles; specific values MAY vary per realization.

---

## 6. Authentication-at-Callback-Time Contract

Every callback MUST present both Layer 1 and Layer 2 factors. The receiving realization MUST validate both before accepting the call. The substrate-required validation sequence is:

```
1. Extract Layer 2 credential from the inbound call
   → Missing or malformed: 401 Unauthorized; MISSING_CREDENTIAL audit record

2. Look up the credential record
   → Not found: 401 Unauthorized; CREDENTIAL_NOT_FOUND audit record

3. Check credential status is 'active'
   → Revoked: 403 Forbidden; code: CREDENTIAL_REVOKED
   → Expired: 403 Forbidden; code: CREDENTIAL_EXPIRED

4. Check credential expires_at > now
   → Expired: 403 Forbidden; code: CREDENTIAL_EXPIRED

5. Check the Layer 1 identity factor binds to the same provider as the credential
   → Mismatch: 403 Forbidden; code: CREDENTIAL_SCOPE_VIOLATION

6. Check that the operation_type for this endpoint is in allowed_operations
   → Not in scope: 403 Forbidden; code: OPERATION_NOT_IN_SCOPE

7. If bound_to_ip is set: verify client IP matches
   → Mismatch: 403 Forbidden; code: IP_BINDING_VIOLATION
```

All failures MUST write an audit record with the credential_uuid, provider_uuid, endpoint, and failure reason. After repeated `CREDENTIAL_SCOPE_VIOLATION` or `IP_BINDING_VIOLATION` failures from the same provider within a rolling window, the realization MUST fire a `security.unsanctioned_provider_write` event and notify the platform admin (urgency: critical). The specific threshold and window are profile-governed defaults.

---

## 7. Entity-Level Authorization Contract

The callback credential proves the caller is the registered provider. It does NOT prove the provider is authorized to act on a specific entity. Entity-level authorization is a substrate-required separate check that MUST apply on each call.

### 7.1 Resource Ownership Binding

For `realized_state_push` and `interim_status` calls, the realization MUST validate:

1. Look up the Requested State record for the entity
2. Verify the credential's `provider_uuid` matches the `provider_uuid` in the Requested State record (i.e., this was the provider the realization dispatched to)
3. Verify the entity is in a lifecycle state that permits this push (e.g., PROVISIONING, UPDATING, or DECOMMISSIONING — not OPERATIONAL or DECOMMISSIONED)

Failures:
- Mismatch on `provider_uuid`: 403 Forbidden; code: `ENTITY_NOT_OWNED_BY_PROVIDER`
- Wrong lifecycle state: 409 Conflict; code: `INVALID_LIFECYCLE_STATE_FOR_PUSH`

**Why this matters:** A provider that obtains an entity identifier (e.g., by observing network traffic or misconfiguration) MUST NOT be able to push realized state for an entity it was not dispatched to. The Requested State record binds the entity to the specific provider that received the dispatch.

### 7.2 Update Notification Binding

For `update_notification` calls, the realization MUST validate:

1. Look up the Realized State record for the entity
2. Verify the credential's `provider_uuid` matches the `provider_uuid` in the most recent Realized State record
3. Verify the provider's registration includes the update capability declared in the notification's `notification_type` field

Failures:
- Provider not current owner: 403 Forbidden; code: `ENTITY_NOT_OWNED_BY_PROVIDER`
- Update type not declared at registration: 403 Forbidden; code: `UPDATE_TYPE_NOT_DECLARED`

### 7.3 Lifecycle Event Binding

For `lifecycle_event` calls, the realization MUST validate:

1. Verify the credential's `provider_uuid` matches the provider on record for the resource
2. Verify the resource is in an operational state (not DECOMMISSIONED)
3. Verify the event_type is in the substrate event catalog

Failures:
- Provider not current owner: 403 Forbidden; code: `ENTITY_NOT_OWNED_BY_PROVIDER`
- Entity decommissioned: 409 Conflict; code: `ENTITY_DECOMMISSIONED`
- Unknown event_type: 400 Bad Request; code: `UNKNOWN_EVENT_TYPE`

---

## 8. Bootstrap Contract

The initial registration call cannot use the callback credential because no credential exists yet. The substrate requires a bootstrap mechanism that uses an authenticated single-use token (the **registration token**) issued by a platform admin before provider onboarding. The cryptographic mechanism backing the token is realization-declared.

### 8.1 Registration Token Properties (Wire Contract)

```yaml
registration_token:
  token_uuid: <uuid>
  token_value: <present once; never retrievable again>
  issued_at: <ISO 8601>
  expires_at: <ISO 8601>   # typically PT72H
  scope:
    provider_type_id: service_provider
    provider_handle_pattern: "eu-west-*"   # optional constraint
    grants_auto_approval: true | false
  used: false              # single-use; set to true after first successful use
```

### 8.2 Bootstrap Invariants

- The registration token is single-use. A token marked `used: true` MUST NOT be reused regardless of its `expires_at`.
- The Layer 1 identity factor MUST also be enforced on the registration call — the provider must demonstrate possession of the identity material it is registering.
- If a provider needs to re-register with a sovereignty declaration change, a new registration token is required (treated as a new registration requiring fresh approval).
- Version and capability updates do NOT require a new registration token — the existing callback credential authenticates such re-registration calls.

---

## 9. Credential Revocation Contract

### 9.1 Revocation Triggers (Closed Substrate Vocabulary)

| Trigger | Effect |
|---------|--------|
| Provider deregistered | All callback credentials for that provider revoked immediately |
| Security event detected (repeated scope violations) | Provider suspended; credential revoked; platform admin notified |
| Identity material expiry without rotation | Credential revoked at identity expiry |
| Platform admin explicit revocation | Immediate revocation; provider must re-register |
| Provider compromise suspected | Emergency revocation; Recovery Policy evaluates affected entities |

### 9.2 Revocation Propagation (Substrate Required)

The substrate requires that revocation is **immediate** and that all components recognize and reject revoked credentials within the profile-governed revocation SLA.

```
Platform admin (or automation) triggers revocation:
  │
  ▼ The realization revokes the credential immediately
  │   credential_record.status → revoked
  │   Revocation event published
  │   All components update revocation cache (within profile-governed SLA)
  │
  ▼ If provider suspended:
  │   Provider status → SUSPENDED
  │   New requests not routed to this provider
  │   Active realizations enter PENDING_REVIEW state
  │
  ▼ Recovery Policy evaluates affected entities
```

### 9.3 Revocation Cache Contract

Components that validate inbound credentials MUST maintain a local revocation cache:

- Cache populated from the substrate's revocation event stream
- Cache TTL bounded by the maximum credential lifetime for the active profile
- On cache miss: remote check against the revocation registry (prevents stale cache from accepting revoked credentials)
- Cache invalidation is immediate on revocation event receipt (not TTL-based)

The revocation cache MUST ensure revocation propagates within the profile-governed SLA (PT30S standard; PT15S sovereign).

---

## 10. UDLM System Policies

| Policy | Rule |
|--------|------|
| `PCA-001` | All provider-to-realization calls MUST present both a valid Layer 1 identity attestation factor and a valid Layer 2 callback credential. Neither layer alone is sufficient. |
| `PCA-002` | Callback credentials are scoped to the `provider_uuid` and MUST NOT be used to act on entities hosted at other providers. |
| `PCA-003` | Entity-level authorization MUST be checked on every realized_state_push, update_notification, and lifecycle_event call, independent of credential validity. A valid credential does not grant access to entities the provider was not dispatched to. |
| `PCA-004` | Repeated credential scope violations or IP binding violations from the same provider within a rolling window MUST trigger automatic provider suspension and platform admin notification. |
| `PCA-005` | Callback credentials are issued by a registered Credential Provider, not directly by the realization's API surface. The Credential Provider is the authoritative source for all credential issuance, rotation, and revocation. |
| `PCA-006` | Registration tokens are single-use. A registration token that has been used once MUST be permanently invalidated regardless of its `expires_at` timestamp. |
| `PCA-007` | Re-registration that changes the sovereignty declaration MUST require a new registration token and triggers a new approval pipeline. Version and capability updates do not require a new registration token. |
| `PCA-008` | Callback credentials MUST be rotated before expiry. The realization MUST initiate rotation automatically. If a credential expires without rotation, the provider enters a CREDENTIAL_EXPIRED state and must obtain a new credential via the platform admin. |
| `PCA-009` | For `fsi` and `sovereign` profiles, callback credentials MUST be IP-bound. A credential presented from an IP address that does not match the `bound_to_ip` field MUST be rejected regardless of its validity. |
| `PCA-010` | All inbound provider calls — including rejected calls — MUST produce an audit record containing the credential_uuid, provider_uuid, endpoint, operation_type, outcome, and timestamp. There are no silent failures. |
| `PCA-011` | The specific mechanisms backing Layer 1 and Layer 2 are realization choices. Each realization MUST declare its chosen mechanisms via the [schema-sharing protocol](schema-sharing.md) so federation peers can interoperate. |

---

*UDLM substrate document. The DCM realization implements Layer 1 via mTLS and Layer 2 via a scoped interaction credential; those specific mechanism details and operational mechanics live in the DCM realization's documentation.*
