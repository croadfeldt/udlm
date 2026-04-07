# DCM Data Model — Provider Callback Authentication

**Document Status:** ✅ Complete
**Document Type:** Architecture Reference
**Related Documents:** [Unified Provider Contract](A-provider-contract.md) | [Credential Provider Model](31-credential-provider-model.md) | [Accreditation, Auth Matrix, Zero Trust](26-accreditation-and-authorization-matrix.md) | [Internal Component Auth](36-internal-component-auth.md) | [Registration Specification](../specifications/dcm-registration-spec.md) | [Provider Callback API](../schemas/openapi/dcm-provider-callback-api.yaml)

> **Foundation Document Reference**
>
> This document maps to: **PROVIDER** (authentication of the provider-to-DCM interaction boundary)
> and **DATA** (the credential artifact that governs that boundary).
>
> See [00-foundations.md](00-foundations.md) · [A-provider-contract.md](A-provider-contract.md) · [B-policy-contract.md](B-policy-contract.md)

---

## 1. Purpose and Scope

This document specifies how Service Providers authenticate inbound calls to the DCM control plane — specifically, calls to the Provider Callback API endpoints:

- `POST /api/v1/providers` — Registration
- `POST /api/v1/providers/{provider_uuid}/capacity` — Capacity reporting
- `PUT /api/v1/instances/{resource_id}/status` — Realized state push
- `POST /api/v1/provider/entities/{entity_uuid}/status` — Interim progress
- `POST /api/v1/provider/entities/{entity_uuid}/update-notification` — Authorized state change notification
- `GET /api/v1/provider/notifications/{notification_uuid}` — Notification status poll
- `POST /api/v1/instances/{resource_id}/events` — Lifecycle event reporting

The outbound model (DCM authenticating to providers) is specified in [doc 31 Section 4.2](31-credential-provider-model.md) and [doc 26 Section 5.3](26-accreditation-and-authorization-matrix.md). This document specifies the **inbound** model.

---

## 2. The Authentication Problem

When DCM receives a callback at `PUT /api/v1/instances/{resource_id}/status`, it must verify:

1. **Identity:** Is this call genuinely from the registered Service Provider for this resource?
2. **Authorization:** Is this provider permitted to push realized state for this specific resource/entity?
3. **Integrity:** Has the payload been tampered with in transit?
4. **Freshness:** Is this a live call, not a replayed credential from a previous session?
5. **Scope:** Is this credential permitted for this specific operation type?

Network-level authentication alone (firewall rules, IP allowlisting) is insufficient under the DCM Zero Trust model — it establishes perimeter trust, not per-call identity. Every provider call to DCM must carry a credential that answers all five questions independently of network position.

---

## 3. Two-Layer Authentication Model

DCM uses a **two-layer** model for provider-to-DCM calls. Both layers must pass:

```
Provider calls DCM:
  │
  ▼ Layer 1: Transport Identity (mTLS)
  │   Provider presents its registered certificate
  │   DCM verifies the certificate chain against the provider's registered CA
  │   Proves: this connection is from the registered provider
  │   Does NOT prove: authorization for this specific operation
  │
  ▼ Layer 2: Operation Authorization (Provider Callback Credential)
  │   Provider presents a scoped short-lived credential in the Authorization header
  │   DCM validates: credential is active, scoped to this provider, scoped to this operation type
  │   Proves: this specific call is authorized for this specific operation
  │   Does NOT replace mTLS — both layers are required
  │
  ▼ Both pass → five-check boundary model evaluates (doc 26 Section 5.2)
  └── Audit record written regardless of outcome
```

**Why two layers?** mTLS proves the caller holds the private key for the registered certificate — it proves identity at the transport level. The interaction credential proves the specific call is authorized for the specific operation type and scope. A compromised credential without the private key cannot establish the mTLS connection. A valid mTLS connection without a valid credential cannot perform operations. The layers are complementary, not redundant.

---

## 4. Layer 1 — Transport Identity (mTLS)

### 4.1 Provider Certificate Registration

At registration, every provider declares a certificate:

```yaml
provider_registration:
  certificate:
    pem: <PEM-encoded provider certificate>
    ca_chain: <PEM-encoded CA certificate chain>
    rotation_interval: P90D
```

DCM validates:
- Certificate chain is valid and trusted
- Certificate is not in DCM's Credential Revocation Registry
- Certificate `CN` or `SAN` matches the provider's declared `handle`
- Certificate `expires_at` is not in the past

DCM stores the certificate fingerprint. On every subsequent inbound connection, DCM validates the presented certificate against the stored fingerprint for this provider.

### 4.2 Certificate Validation on Inbound Calls

When a provider initiates a TLS connection to DCM:

```
Provider → DCM:
  TLS ClientHello → ServerHello + DCM certificate
  Provider verifies DCM certificate (validates DCM's identity)
  Provider sends its certificate
  DCM validates:
    1. Certificate chain → registered CA for this provider
    2. Certificate fingerprint → matches stored fingerprint for provider_uuid in path/payload
    3. Certificate not in Credential Revocation Registry
    4. Certificate expires_at not expired
  If any check fails → TLS handshake rejected; connection refused
```

**Certificate rotation:** Providers must rotate certificates on the declared `rotation_interval`. DCM fires a `P14D` warning event when a certificate is approaching expiry. During the rotation transition window, DCM accepts both the current and new certificate simultaneously (P7D window). After the window, only the new certificate is accepted.

### 4.3 Certificate Binding to Operations

The mTLS certificate is **not sufficient alone** for operation authorization. Knowing a call came from Provider X does not mean Provider X is authorized to push realized state for entity Y owned by Tenant Z. The interaction credential (Layer 2) carries that authorization.

---

## 5. Layer 2 — Operation Authorization (Provider Callback Credential)

### 5.1 Provider Callback Credential

The **Provider Callback Credential** is a `dcm_interaction` type credential issued to the provider by DCM's Credential Provider at registration activation time. It is the mechanism by which providers prove authorization for specific callback operations.

```yaml
provider_callback_credential:
  credential_uuid: <uuid>
  credential_type: dcm_interaction
  issued_to:
    provider_uuid: <uuid>      # the specific registered provider
    provider_handle: <string>  # for human-readable audit records
  issued_at: <ISO 8601>
  expires_at: <ISO 8601>      # profile-governed lifetime; see Section 5.3
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
  revocation_check_url: <DCM revocation endpoint>
```

**Presented as:** `Authorization: Bearer <credential_value>` on all callback API calls.

**Key property:** The credential is scoped to the `provider_uuid` — not to specific entities or operations within that provider. Entity-level scope is enforced separately (Section 6). This means a provider holding the credential can call any callback endpoint, but DCM enforces entity-level ownership checks per call.

### 5.2 Credential Issuance

Provider callback credentials are issued through the following lifecycle:

```
Registration approved (provider status → ACTIVE):
  │
  ▼ DCM API Gateway requests credential from Credential Provider:
  │   credential_type: dcm_interaction
  │   issued_to.provider_uuid: <newly activated provider UUID>
  │   allowed_operations: [realized_state_push, capacity_report, interim_status,
  │                         update_notification, lifecycle_event, notification_poll]
  │   expires_at: <now + profile-governed lifetime>
  │
  ▼ Credential Provider issues credential
  │   Returns credential_value (the bearer token)
  │   Stores credential_record in Credential Store
  │
  ▼ DCM delivers credential to provider via the activation response:
  │   POST /api/v1/admin/providers/{uuid}:approve
  │   Response includes: credential_ref (UUID for retrieval)
  │
  ▼ Provider retrieves credential value via Credential Provider endpoint:
  │   GET {service_provider_endpoint}/credentials/{credential_ref}/value
  │   (Requires the registration token used at initial registration — one-time bootstrap)
  │
  ▼ Provider stores credential securely and uses it for all callback API calls
```

**Bootstrap case:** During initial registration (before activation), the provider uses the registration token to authenticate. After activation, the provider callback credential replaces the registration token for all subsequent calls. The registration token is single-use and expires after the first successful registration response.

### 5.3 Credential Lifetime by Profile

| Profile | Lifetime | Rotation trigger | IP binding |
|---------|----------|-----------------|------------|
| minimal | PT8H | Pre-expiry P1H | No |
| dev | PT4H | Pre-expiry P30M | No |
| standard | PT1H | Pre-expiry PT10M | No |
| prod | PT30M | Pre-expiry PT5M | Optional |
| fsi | PT15M | Pre-expiry PT3M | Required |
| sovereign | PT15M + hardware attestation | Pre-expiry PT3M | Required; HSM-bound |

**Pre-expiry rotation:** DCM initiates rotation automatically before the current credential expires. The transition window is 50% of the credential lifetime — the old credential remains valid during the window while the new one is delivered. Providers must implement credential refresh in their SDK or adapter.

### 5.4 Credential Rotation Protocol

```
PT{rotation_trigger} before credential expiry:
  │
  ▼ DCM initiates rotation:
  │   Requests new credential from Credential Provider
  │   rotation_of: <current credential_uuid>
  │   same allowed_operations scope; new expires_at
  │
  ▼ Credential Provider issues new credential
  │   Old credential NOT yet revoked
  │
  ▼ DCM pushes rotation notification to provider:
  │   POST {provider_health_endpoint}/credential-rotation (if provider supports it)
  │   OR: credential.rotating event published to Message Bus
  │   New credential_ref included; provider retrieves new value
  │
  ▼ Transition window opens:
  │   DCM accepts BOTH old and new credential during transition window
  │   Provider switches to new credential
  │
  ▼ Transition window closes:
  │   Old credential revoked
  │   Revocation event published → all components update revocation cache
```

If the provider fails to pick up the new credential before the transition window closes, the old credential is revoked and the provider's callback calls will return `403 Forbidden` with code `CREDENTIAL_EXPIRED`. The provider must re-register to obtain a new credential — this is a recoverable state.

### 5.5 DCM Validation on Inbound Calls

When DCM receives a callback call, Layer 2 validation performs these checks in order:

```
1. Extract credential_value from Authorization: Bearer header
   → Missing or malformed: 401 Unauthorized; MISSING_CREDENTIAL audit record

2. Look up credential_record by credential_value hash
   → Not found: 401 Unauthorized; CREDENTIAL_NOT_FOUND audit record

3. Check credential_record.status is 'active'
   → Revoked: 403 Forbidden; code: CREDENTIAL_REVOKED
   → Expired: 403 Forbidden; code: CREDENTIAL_EXPIRED

4. Check credential_record.expires_at > now
   → Expired: 403 Forbidden; code: CREDENTIAL_EXPIRED

5. Check credential_record.issued_to.provider_uuid matches:
   a. The provider_uuid in the URL path (where applicable)
   b. The mTLS certificate's registered provider (Layer 1 binding)
   → Mismatch: 403 Forbidden; code: CREDENTIAL_SCOPE_VIOLATION

6. Check that the operation_type for this endpoint is in allowed_operations
   → Not in scope: 403 Forbidden; code: OPERATION_NOT_IN_SCOPE

7. If bound_to_ip is set: verify client IP matches
   → Mismatch: 403 Forbidden; code: IP_BINDING_VIOLATION
```

All failures write an audit record with the credential_uuid, provider_uuid, endpoint, and failure reason. After 5 consecutive `CREDENTIAL_SCOPE_VIOLATION` or `IP_BINDING_VIOLATION` failures from the same provider within PT1H, DCM fires a `security.unsanctioned_provider_write` event and notifies the platform admin (urgency: critical).

---

## 6. Entity-Level Authorization

The provider callback credential proves the caller is the registered provider. It does not prove the provider is authorized to act on a specific entity. Entity-level authorization is a separate check that applies on each call.

### 6.1 Resource Ownership Binding

For `realized_state_push` and `interim_status` calls, DCM validates:

```
PUT /api/v1/instances/{resource_id}/status

DCM checks:
  1. Look up the Requested State record for resource_id
  2. Verify the credential's provider_uuid matches the provider_uuid
     in the Requested State record (i.e., this was the provider DCM dispatched to)
  3. Verify the entity is in a lifecycle state that permits this push
     (PROVISIONING, UPDATING, or DECOMMISSIONING — not OPERATIONAL, not DECOMMISSIONED)
  
  → Mismatch on provider_uuid: 403 Forbidden; code: ENTITY_NOT_OWNED_BY_PROVIDER
  → Wrong lifecycle state: 409 Conflict; code: INVALID_LIFECYCLE_STATE_FOR_PUSH
```

**Why this matters:** A provider that receives a `resource_id` (e.g., by observing network traffic or misconfiguration) cannot push realized state for an entity it was not dispatched to. The Requested State record binds the entity to the specific provider that received the dispatch.

### 6.2 Update Notification Binding

For `update_notification` calls, DCM validates:

```
POST /api/v1/provider/entities/{entity_uuid}/update-notification

DCM checks:
  1. Look up the Realized State record for entity_uuid
  2. Verify the credential's provider_uuid matches the provider_uuid
     in the most recent Realized State record
  3. Verify the provider's registration includes the update_capability
     declared in the notification_type field

  → Provider not current owner: 403 Forbidden; code: ENTITY_NOT_OWNED_BY_PROVIDER
  → Update type not declared at registration: 403 Forbidden;
    code: UPDATE_TYPE_NOT_DECLARED
    (provider must re-register to declare new update capability types)
```

### 6.3 Lifecycle Event Binding

For `lifecycle_event` calls, DCM validates:

```
POST /api/v1/instances/{resource_id}/events

DCM checks:
  1. Verify the credential's provider_uuid matches the provider on record for resource_id
  2. Verify the resource is in an operational state (not DECOMMISSIONED)
  3. Verify the event_type is in the standard event catalog

  → Provider not current owner: 403 Forbidden; code: ENTITY_NOT_OWNED_BY_PROVIDER
  → Entity decommissioned: 409 Conflict; code: ENTITY_DECOMMISSIONED
  → Unknown event_type: 400 Bad Request; code: UNKNOWN_EVENT_TYPE
```

---

## 7. Registration Authentication (Special Case)

The initial `POST /api/v1/providers` registration call cannot use the provider callback credential because no credential exists yet. Registration uses a different authentication mechanism:

### 7.1 Registration Token

The registration token is a short-lived, single-use credential issued by a platform admin before provider onboarding:

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

The registration token is passed as `Authorization: Bearer <token_value>` on the initial `POST /api/v1/providers` call. After the first successful registration, the token is marked `used: true` and cannot be reused. If a provider needs to re-register (e.g., after a sovereignty declaration change), a new registration token is required.

**mTLS still required for registration:** The mTLS layer (Layer 1) is enforced on the registration call. The provider must present the certificate declared in the registration payload. This ensures the entity performing the registration possesses the private key for the certificate it is claiming.

### 7.2 Re-Registration

For re-registration calls (same `name`, updating version or capabilities), the provider uses its active provider callback credential — not a new registration token. Re-registration that changes the sovereignty declaration requires a new registration token from the platform admin (treated as a new registration requiring a new approval).

---

## 8. Credential Revocation and Emergency Response

### 8.1 Revocation Triggers

| Trigger | What happens |
|---------|-------------|
| Provider deregistered | All callback credentials for that provider revoked immediately |
| Security event detected (5+ scope violations in PT1H) | Provider suspended; credential revoked; platform admin notified |
| Provider certificate expiry without rotation | Credential revoked at certificate expiry |
| Platform admin explicit revocation | Immediate revocation; provider must re-register |
| Provider compromise suspected | Emergency revocation; Recovery Policy evaluates affected entities |

### 8.2 Emergency Revocation Flow

```
Platform admin triggers emergency revocation:
  │
  ▼ POST /api/v1/admin/providers/{provider_uuid}/revoke-credential
  │   reason: <string>
  │   suspend_provider: true | false
  │
  ▼ DCM revokes credential immediately:
  │   credential_record.status → revoked
  │   Revocation event → Message Bus
  │   All DCM components update revocation cache (within PT30S)
  │
  ▼ If suspend_provider: true:
  │   Provider status → SUSPENDED
  │   New requests not routed to this provider
  │   Active realizations enter PENDING_REVIEW state
  │
  ▼ Recovery Policy evaluates affected entities:
      Entities currently hosted at provider: notify Tenant owners
      In-progress operations: depends on Recovery Policy profile
```

### 8.3 Revocation Cache

DCM components that validate inbound credentials maintain a local **Credential Revocation Cache**:

- Cache is populated from the Message Bus `credential.revoked` event stream
- Cache TTL matches the maximum credential lifetime for the active profile
- On cache miss: remote check against Credential Store (prevents stale cache from accepting revoked credentials)
- Cache invalidation is immediate on `credential.revoked` event receipt (not TTL-based)

The revocation cache ensures revocation propagates within PT30S even without a cache miss triggering a remote lookup.

---

## 9. System Policies

| Policy | Rule |
|--------|------|
| `PCA-001` | All provider-to-DCM calls must present both a valid mTLS certificate (Layer 1) and a valid provider callback credential (Layer 2). Neither layer alone is sufficient. |
| `PCA-002` | Provider callback credentials are scoped to the provider_uuid and cannot be used to act on entities hosted at other providers. |
| `PCA-003` | Entity-level authorization is checked on every realized_state_push, update_notification, and lifecycle_event call, independent of credential validity. A valid credential does not grant access to entities the provider was not dispatched to. |
| `PCA-004` | Five consecutive credential scope violations or IP binding violations from the same provider within PT1H triggers automatic provider suspension and platform admin notification. |
| `PCA-005` | Provider callback credentials are issued by the Credential Provider, not directly by the DCM API Gateway. The Credential Provider is the authoritative source for all credential issuance, rotation, and revocation. |
| `PCA-006` | Registration tokens are single-use. A registration token that has been used once is permanently invalidated regardless of its `expires_at` timestamp. |
| `PCA-007` | Re-registration that changes the sovereignty declaration requires a new registration token and triggers a new approval pipeline. Version and capability updates do not require a new registration token. |
| `PCA-008` | Provider callback credentials must be rotated before expiry. DCM initiates rotation automatically. If a credential expires without rotation, the provider enters a CREDENTIAL_EXPIRED state and must obtain a new credential via the platform admin. |
| `PCA-009` | For fsi and sovereign profiles, provider callback credentials are IP-bound. A credential presented from an IP address that does not match the `bound_to_ip` field is rejected regardless of its validity. |
| `PCA-010` | All inbound provider calls — including rejected calls — produce an audit record containing the credential_uuid, provider_uuid, endpoint, operation_type, outcome, and timestamp. There are no silent failures. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
