# UDLM — Auth Capability and Identity Contract

**Document Status:** ✅ Stable — UDLM substrate contract
**Related Documents:** [Provider Contract](../contracts/provider-contract.md) | [Credentials](credentials.md) | [Authority Tier Model](authority-tier-model.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM substrate.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](../foundations/foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: PROVIDER**
>
> The Provider abstraction — Auth Provider taxonomy and credential model.

---

## 1. Purpose

UDLM defines a unified **auth capability**. Authentication/authorization is a **capability a provider declares**, not a separate provider kind (see [Provider Contract](../contracts/provider-contract.md) §8.4) — "Auth Provider" throughout this document means *a provider that declares the auth capability*. It answers two questions:

1. **Authentication** — is this identity who they claim to be?
2. **Authorization** — what is this identity permitted to do?

Every authentication mode UDLM admits — static API key, local users, GitHub OAuth, LDAP, FreeIPA, Active Directory, OIDC, mTLS — is a way a provider exercises the auth capability. The built-in auth capability is a substrate-required default that any conformant realization MUST ship with, enabling immediate evaluation and home-lab use without requiring an external identity system. Externally-provided auth is a registered artifact, versioned, lifecycle-managed, and audited. The realization **consumes** this capability (including for its own user auth) the same way it consumes any other yield — it brokers/consumes; it does not have to *be* the authenticator (`DCM ADR-022`).

**UDLM defines the contract authentication resolves against — the capability, the mode vocabulary, the registration shape, and the identity types. It never performs authentication; the realization does (`DCM ADR-022`).** This is the substrate/realization boundary (ADR-008): the vocabulary two independent realizations must share to federate, not the act of authenticating an actor.

**Authentication is always required — there is no anonymous access in any UDLM profile.** The difference between profiles is how much effort authentication setup requires, not whether it exists.

---

## 2. Auth and Credentials as Capabilities

Authentication and credential issuance are **capabilities** (yields) a provider declares — **not** separate provider kinds; there are no provider types, only capabilities (ADR-PROV-002). The verb vocabulary and capability categories are [capability-discovery](../contracts/capability-discovery.md) §2.2–2.4; the registration floor is [provider-contract](../contracts/provider-contract.md) §2. Auth is declared via `auth_capability`; credential issuance via `Credential.*` + `credential_capability` ([Credentials](credentials.md) §1, the broker model). There is no `auth_provider`, `credential_provider`, or `notification_service` *kind* — those are capabilities any provider declares.

> **Identity-model authority (UDLM vs a realization's auth architecture).** This document and the
> `Identity.*` types (`Identity.Person` / `Identity.ServiceAccount` / `Identity.Group`, ADR-RBAC-001)
> are the **authoritative data contract** for actors/identities and the actor-type vocabulary (incl. the
> `provider` actor). A realization's authentication *implementation* — e.g. DCM's IDM/IAM Authentication
> Layer (`dcm-project/enhancements/.../authentication/authentication.md`: Keycloak/IdP, middleware,
> OpenAPI security, flows, and its internal `Actor`/`Actor Identity` tables + status enforcement) — is
> **realization architecture** (ADR-008): it owns *how* actors authenticate and the external-identity
> binding/session/status state, which are deliberately **not** substrate data. Where the two meet — the
> actor/identity entity itself — **UDLM is authoritative**: a realization's `Actor` record is the
> *realized projection* of `Identity.Person`/`ServiceAccount`, and MUST reuse the UDLM identity types and
> actor-type vocabulary (`person` / `service_account` / `group` / `provider`) rather than define a parallel
> identity model. UDLM carries the contract that supports authentication; it does not prescribe the
> implementation.

---

## 3. Auth Provider Registration (Wire Contract)

The registration shape is normative — any conformant realization MUST accept registrations in this form:

```yaml
auth_provider_registration:
  artifact_metadata:
    uuid: <uuid>
    handle: "providers/auth/corporate-freeipa"
    version: "1.0.0"
    status: active
    owned_by:
      display_name: "Platform Team"

  name: "Corporate FreeIPA"
  description: "Primary enterprise directory — FreeIPA with Kerberos"

  # Capabilities
  capabilities:
    authentication: true
    authorization: true
    mfa: false                    # does this provider enforce MFA?
    session_management: true
    group_sync: true

  # Provider type — closed substrate vocabulary
  provider_type: <built_in|static_api_key|local_users|
                  ldap|active_directory|freeipa|
                  oidc|saml|github_oauth|gitlab_oauth|
                  kerberos|mtls|custom>

  # What actor types this provider can authenticate
  authenticates: [human, service_account, webhook_service_account]

  # Trust level — closed substrate vocabulary. PLATFORM-ADMIN-ASSIGNED, not self-declared (DCM ADR-022):
  # trust_level gates whether this provider's authz decisions are re-evaluated, so it is an
  # authorization input. In a self-service or federated registration a trust_level in the payload is
  # IGNORED — only a platform admin sets it (default: advisory). Mirrors the dcm_registration_verdict
  # pattern in provider-contract.md §2.
  trust_level: <authoritative|verified|advisory>
  # authoritative: realization accepts all decisions without re-evaluation
  # verified:      realization accepts with additional Policy Engine checks
  # advisory:      realization treats decisions as input — full re-evaluation always (default)

  # Connection credentials
  connection_credentials_ref:
    service_provider_uuid: <uuid>
    secret_path: "auth/freeipa/bind-password"

  # Health check
  health_check:
    interval_seconds: 30
    on_unhealthy: <alert|fallback_to_next|block_new_sessions>
    fallback_provider_uuid: <uuid>

  # Session configuration
  session:
    token_ttl: PT8H
    refresh_enabled: true
    refresh_ttl: P7D
    concurrent_sessions: 3

  # Role mapping — external groups → realization roles. `role` values are governed access-role
  # TaxonomyTerms (ADR-RBAC-001; registry/instances/access-role-taxonomy.yaml) — the ONE role
  # vocabulary, not free strings. An external-group→role map is one way to ASSIGN a role; the
  # authoritative record is a role_assignment (function-capability-matrix.schema.json).
  role_mapping:
    default_role: consumer
    group_role_map:
      - external_group: "cn=admins,cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
        role: platform_admin
      - external_group: "cn=sre,cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
        role: sre
      - external_group: "cn=consumers,cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
        role: consumer

  # Tenant mapping — external groups → Tenants
  tenant_mapping:
    strategy: <group_based|attribute_based|default_all>
    group_tenant_map:
      - external_group: "cn=payments-team,cn=groups,..."
        tenant_uuid: <payments-tenant-uuid>
      - external_group: "cn=platform-team,cn=groups,..."
        tenant_scope: [all]

  # Config changes go through shadow validation
  on_config_change: proposed
```

---

## 4. Authentication Modes (Taxonomy)

The substrate defines a closed taxonomy of authentication modes. Any conformant realization MUST recognize these mode identifiers and SHOULD support the modes appropriate for its target deployment profile. Realizations MAY extend with custom modes registered via the `custom` provider_type.

### 4.1 Built-In Auth Provider (zero configuration)

Substrate-required default. Always registered. Cannot be deregistered — only deprioritized.

This is the **default RBAC method** — DCM RBAC works with **zero external IdP** (ADR-RBAC-001): `local_users` are `Identity.Person` / `Identity.ServiceAccount` accounts, grouped for RBAC via a DCMGroup with `group_class: access_grouping`. At first-run **bootstrap** the initial account receives a `platform_admin` `role_assignment` (GOV-006) so the `platform_admin` gate (PRV-009) exists before anything else is admitted. Roles, the role→function matrix, and assignments are **governed data** (access-role taxonomy + FunctionCapabilityMatrix + role_assignment), not baked into the auth provider — and they project onto Kessel/SpiceDB later without changing this default path.

```yaml
built_in_auth_provider:
  handle: "providers/auth/builtin"
  provider_type: built_in
  modes:
    static_api_key:
      enabled: true             # generated at bootstrap — shown once
    local_users:
      enabled: true             # managed via realization-provided CLI
    github_oauth:
      enabled: false            # opt-in: requires client_id + secret
    gitlab_oauth:
      enabled: false            # opt-in: requires client_id + secret
```

### 4.2 GitHub / GitLab OAuth

```yaml
auth_provider:
  provider_type: github_oauth
  config:
    client_id: <github_oauth_app_client_id>
    client_secret_ref:
      service_provider: internal
      path: "auth/github/client-secret"
    role_mapping:
      default_role: consumer
      org_role_map:
        - github_org: "my-lab-org"
          role: platform_admin
```

### 4.3 LDAP / FreeIPA (RFC 4511)

```yaml
auth_provider:
  provider_type: freeipa          # or: ldap
  config:
    server: ldaps://freeipa.corp.example.com:636
    tls:
      mode: ldaps                 # ldaps | starttls
      ca_cert_ref:
        service_provider: internal
        path: "auth/freeipa/ca-cert"
    bind_dn: "uid=service,cn=users,cn=accounts,dc=corp,dc=example,dc=com"
    bind_password_ref:
      service_provider: internal
      path: "auth/freeipa/bind-password"

    user_search:
      base_dn: "cn=users,cn=accounts,dc=corp,dc=example,dc=com"
      filter: "(uid={username})"
      attributes:
        username: uid
        email: mail
        display_name: cn

    group_search:
      base_dn: "cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
      filter: "(member={user_dn})"
      attributes:
        group_name: cn

    # FreeIPA-specific integrations
    kerberos:
      enabled: true               # SSO for Linux CLI users
      keytab_ref:
        service_provider: internal
        path: "auth/freeipa/service.keytab"
      service_principal: "HTTP/host.corp.example.com@CORP.EXAMPLE.COM"
    hbac:
      enforce: true               # Honor FreeIPA Host-Based Access Control
    ca:
      trust_freeipa_ca: true      # Trust FreeIPA CA for mTLS

    group_sync:
      enabled: true
      interval_seconds: 300
      on_group_change: reauthorize
```

### 4.4 Active Directory

```yaml
auth_provider:
  provider_type: active_directory
  config:
    domain_controllers:
      - ldaps://dc01.corp.example.com:636
      - ldaps://dc02.corp.example.com:636   # automatic failover
    tls:
      mode: ldaps
      ca_cert_ref:
        service_provider: internal
        path: "auth/ad/ca-cert"
    bind_dn: "CN=Service,OU=Service Accounts,DC=corp,DC=example,DC=com"
    bind_password_ref:
      service_provider: internal
      path: "auth/ad/bind-password"

    user_search:
      base_dn: "DC=corp,DC=example,DC=com"
      filter: "(sAMAccountName={username})"
      # UPN alternative: "(userPrincipalName={username}@corp.example.com)"
      attributes:
        username: sAMAccountName
        email: userPrincipalName
        display_name: display_name
        sid: objectSid            # AD Security Identifier — for audit

    group_search:
      base_dn: "DC=corp,DC=example,DC=com"
      # LDAP_MATCHING_RULE_IN_CHAIN — resolves nested AD group membership
      filter: "(&(objectClass=group)(member:1.2.840.113556.1.4.1941:={user_dn}))"
      attributes:
        group_name: cn
        group_dn: distinguishedName
```

### 4.5 OIDC

```yaml
auth_provider:
  provider_type: oidc
  config:
    issuer: https://accounts.google.com      # or: Okta, Azure AD, Keycloak, Dex
    client_id: dcm-production
    client_secret_ref:
      service_provider: internal
      path: "auth/oidc/client-secret"
    scopes: [openid, profile, email, groups]
    claims_mapping:
      username: preferred_username
      email: email
      display_name: name
      groups: groups
      department: department          # custom claims
      cost_center: cost_center
```

### 4.6 mTLS

```yaml
auth_provider:
  provider_type: mtls
  config:
    ca_cert_ref:
      service_provider: internal
      path: "auth/mtls/ca-cert"
    # Client certificate CN → actor mapping
    cn_actor_mapping:
      - cn_pattern: "service-account-*"
        actor_type: service_account
        default_role: consumer
      - cn_pattern: "provider-*"
        actor_type: provider
```

---

## 5. Multiple Auth Providers — Routing Contract

Multiple Auth Providers MAY be registered simultaneously. The substrate requires that the realization route an inbound request to the appropriate Auth Provider based on the authentication signal present. The routing-order data structure is normative:

```yaml
auth_provider_resolution:
  resolution_order:
    - signal: mtls_client_cert
      provider_uuid: <mtls-provider-uuid>
    - signal: bearer_token_oidc
      provider_uuid: <corporate-oidc-uuid>
    - signal: bearer_token_apikey
      provider_uuid: <api-key-provider-uuid>
    - signal: basic_auth
      provider_uuid: <freeipa-ldap-uuid>
    - signal: hmac_signature
      provider_uuid: <webhook-auth-provider-uuid>
    - signal: none
      action: reject               # always — no anonymous access
```

### 5.1 Auth Provider Chain (Contract)

Authentication and authorization enrichment MAY be chained. The substrate defines the three-stage chain shape:

```yaml
auth_provider_chain:
  authentication:
    provider_uuid: <ldap-uuid>       # fast directory bind
  enrichment:
    provider_uuid: <ldap-uuid>       # group membership lookup
  augmentation:
    provider_uuid: <oidc-uuid>       # additional claims (department, cost center)
```

---

## 6. Credential Types and Issuance (Data Model)

Credential issuance is a **capability** a provider declares (`credential_capability` + `Credential.*` resource types — [credentials.md](credentials.md) §9), **not** a separate provider kind (§2; PROV-002/PROV-003 capability-not-kind). "Credential Provider" here means *a provider that declares that capability* — a cross-cutting dependency any realization component or provider registration references for secret resolution. The substrate REQUIRES that credentials are never stored directly by the realization; they are always referenced. The canonical capability declaration (assurance, attestation, credential types, secret engines) is defined once in [credentials.md](credentials.md) §9; the block below adds only the backend-connection specifics.

```yaml
credential_provider_registration:
  artifact_metadata:
    uuid: <uuid>
    handle: "providers/credentials/hashicorp-vault-prod"
    status: active

  name: "HashiCorp Vault Production"
  backend_type: <hashicorp_vault|aws_secrets_manager|azure_key_vault|
                 gcp_secret_manager|kubernetes_secrets|cyberark|
                 delinea|external_api|internal>

  connection:
    endpoint: https://vault.corp.example.com:8200
    auth_method: <kubernetes|approle|token|aws_iam|ldap>
    namespace: <vault namespace>

  # Credential types this backend can issue — drawn from the CLOSED substrate vocabulary in
  # credentials.md §2; this list does NOT redefine it. Backend-flavored names fold into canonical
  # types (nothing lost): a connection_string / username_password / ldap_bind / hmac_secret is a
  # `secret`; a bearer token is a `service_account_token`; a raw private key is `ssh_key`/`signing_key`.
  credential_types: [api_key, x509_certificate, ssh_key, secret, signing_key, service_account_token]

  health_check:
    interval_seconds: 60
    on_unhealthy: <alert|suspend_dependents|fail_open>
    # suspend_dependents: suspend all components using this provider
    # fail_open: continue using cached credentials (risk — use cautiously)

  caching:
    enabled: true
    ttl_seconds: 300             # refresh from credential provider every 5 minutes
```

**Credential reference shape** — normative; used wherever a secret is needed:

```yaml
# In webhook authentication
secret_ref:
  service_provider_uuid: <uuid>
  secret_path: "webhooks/payments/hmac-secret"
  version: latest

# In Auth Provider connection
bind_password_ref:
  service_provider_uuid: <uuid>
  secret_path: "auth/freeipa/bind-password"

# In Service Provider registration
credentials_ref:
  service_provider_uuid: <uuid>
  secret_path: "providers/kubevirt/service-account"
```

Substrate invariants: credential values never appear in audit records (only the `secret_path` is recorded), never in source control, never in logs. See [credentials](credentials.md) for the full credential model.

---

## 7. The Authentication Ladder (Profile Scaling)

Every rung is authenticated. The ladder is about setup effort — not whether authentication exists.

| Profile | Auth Modes Available | Setup Effort | Notes |
|---------|---------------------|-------------|-------|
| `minimal` | Static API key, Local user/password | Seconds to minutes | Generated at bootstrap; zero external config |
| `dev` | + GitHub/GitLab OAuth, FreeIPA/AD (direct bind) | Minutes | OAuth requires app registration; LDAP requires server config |
| `standard` | + OIDC via broker (Dex/Keycloak), AD/FreeIPA direct | Tens of minutes | Enterprise directory or IdP integration |
| `prod` | + OIDC direct, MFA | Hours | Full enterprise IdP; MFA configurable |
| `fsi` | + mTLS required, MFA required | Hours to days | Certificate infrastructure required |
| `sovereign` | + Air-gapped OIDC/mTLS | Days | No external auth dependencies |

---

## 8. Profile-Governed Mode Availability (Substrate Vocabulary)

| Feature | minimal | dev | standard | prod | fsi | sovereign |
|---------|---------|-----|---------|------|-----|----------|
| Static API key | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Local user/password | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| GitHub/GitLab OAuth | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| LDAP direct bind | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| OIDC (any provider) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| mTLS | ❌ | ❌ | Optional | Recommended | Required | Required |
| MFA | ❌ | ❌ | Optional | Configurable | Required | Required |
| Air-gapped OIDC | ❌ | ❌ | ❌ | ❌ | Optional | Required |
| Anonymous access | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |

---

## 9. System Policies

| Policy | Rule |
|--------|------|
| `AUTH-001` | All authentication must be handled through a registered Auth Provider. The built-in Auth Provider is always available and cannot be deregistered. |
| `AUTH-002` | Multiple Auth Providers may be registered simultaneously. The ingress layer routes to the appropriate provider based on the authentication signal in the request. |
| `AUTH-003` | Auth Provider trust level governs how decisions are treated: authoritative (accepted as-is), verified (with Policy Engine augmentation), advisory (full re-evaluation). |
| `AUTH-004` | Auth Provider role and tenant mappings are versioned artifacts subject to standard artifact lifecycle. Changes go through proposed → active validation. |
| `AUTH-005` | If an Auth Provider becomes unhealthy, existing sessions remain valid until TTL expiry. New authentication attempts route to the configured fallback provider or are rejected. |
| `AUTH-006` | The Auth Provider used to authenticate a request is recorded in the ingress block and carried into the audit record. Policies may act on `auth_provider_uuid` and `provider_type`. |
| `AUTH-007` | Auth Provider configuration credentials must reference a registered credential provider. Plaintext credentials are rejected. |
| `AUTH-008` | There is no anonymous access in any profile. Minimal and dev profiles support lightweight authenticated modes requiring minimal setup. |
| `AUTH-009` | Webhook and message bus inbound surfaces always require authentication regardless of active profile. Anonymous actors are never permitted on these surfaces. |
| `AUTH-010` | Rate limiting is enforced per authenticated actor. Limits are declared on the Auth Provider or webhook actor registration. |
| `AUTH-011` | Git PR actor identity resolution must use the registered Auth Provider. The realization trusts the Git server's verified identity assertion — not user-declared Git configuration. The resolved actor carries the same role, group, and tenant scope as any other user authenticated via the same Auth Provider. |
| `AUTH-012` | SCIM 2.0 is supported as an optional Auth Provider capability. SCIM provisions and deprovisions actors and group memberships. Roles are not SCIM-provisioned — they require explicit policy authorization: a role is a governed **access-role** TaxonomyTerm (ADR-RBAC-001), assigned by an admin-gated `role_assignment` (`function-capability-matrix.schema.json`; function `access.role.assign`, append-only audited) — never a free string and never SCIM-set. SCIM deprovisioning suspends actors by default; in-flight requests complete before suspension. |
| `AUTH-013` | In-flight requests authenticated before Auth Provider failure continue using cached session tokens. New requests follow the declared failover chain. Sessions remain valid for their declared TTL during outages. All providers unavailable → new authentication rejected. |
| `AUTH-014` | MFA enforcement is two-tier: per-session MFA (captured in `mfa_verified` field) and step-up MFA (additional challenge at sensitive operations). Policy declares which operations require step-up regardless of session MFA status. Step-up tokens are short-lived. Profile governs default requirements. |
| `AUTH-015` | The built-in Auth Provider uses a pluggable storage backend. FSI and sovereign profiles require encryption at rest. The local user store should only contain bootstrap users, service accounts, and API key holders. |

---

## 10. Git Identity Resolution Contract

When a UDLM realization processes Git PR ingress, it MUST resolve the Git server's verified actor identity to a substrate actor with full role, group, and tenant scope context — identical to web UI or API login for the same user.

### 10.1 The Trust Model

The realization trusts the **Git server's authentication assertion** — not user-declared Git configuration. The Git server has already authenticated the user (via SSH key, OAuth token, or LDAP password). The realization receives the Git server's verified identity from the PR merge webhook and resolves it through the registered Auth Provider.

```
Git server authenticates user → PR merge webhook → Auth Provider resolution → substrate actor
```

### 10.2 Resolution Methods (Closed Vocabulary)

| Method | When Used | Auth Provider |
|--------|----------|--------------|
| `oidc_subject_lookup` | Git server uses same OIDC/OAuth IdP as the realization | OIDC Auth Provider |
| `ldap_username_lookup` | Git server authenticates via LDAP/AD | LDAP/AD Auth Provider |
| `ssh_key_fingerprint` | SSH key-authenticated Git workflows | SSH key registry |
| `webhook_service_account` | Automated CI/CD Git workflows | Registered webhook actor |

### 10.3 Invariant

Git PR ingress does NOT grant different permissions than any other ingress surface. The same Auth Provider, the same group mappings, the same tenant scope enforcement.

---

## 11. SCIM 2.0 Capability (Contract Surface)

SCIM 2.0 (RFC 7643 / RFC 7644) is an optional Auth Provider capability for enterprise deployments. SCIM automates actor lifecycle management — provisioning, attribute updates, and deprovisioning — from enterprise IdPs (Okta, Azure AD, Ping Identity, JumpCloud).

```yaml
scim_provider_config:
  enabled: true
  scim_version: "2.0"
  endpoint: https://example.corp/scim/v2
  auth:
    mode: bearer_token
    token_ref:
      service_provider_uuid: <uuid>
      path: "auth/scim/bearer-token"

  provisioned_resources:
    actors: true                 # create/update/deactivate actor records
    group_memberships: true      # manage group memberships from IdP groups
    role_assignments: false      # roles managed by policy — not SCIM

  attribute_mapping:
    idp_userName: actor.username
    idp_email: actor.email
    idp_displayName: actor.display_name
    idp_department: actor.status_metadata.department
    idp_groups: actor.groups     # IdP groups → group memberships (where mapped)

  on_user_deprovisioned:
    action: suspend              # suspend | deactivate | archive
    in_flight_request_handling: complete_then_suspend
```

Substrate invariant: roles are NOT SCIM-provisioned. This prevents privilege escalation through the SCIM channel.

---

## 12. Related Concepts

- **Webhooks and Messaging** — ingress/egress actor model; webhook actor registration (realization-side)
- **Credentials** ([credentials.md](credentials.md)) — full credential lifecycle and types
- **Universal Audit Model** ([../observability/universal-audit.md](../observability/universal-audit.md)) — auth provider and ingress context in every audit record
- **Credential Provider** — resolves all Auth Provider connection secrets
- **Universal Group Model** ([../observability/universal-groups.md](../observability/universal-groups.md)) — group memberships resolved via Auth Provider group sync

---

*UDLM substrate document. Realization-specific authentication implementation (library choices, integration mechanics, session management runtime, routing logic, token lifecycle enforcement, storage backend selection, step-up MFA enforcement code) lives in the consuming realization's documentation.*
