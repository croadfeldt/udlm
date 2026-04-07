# DCM Data Model — Authentication, Authorization, and Auth Providers


**Document Status:** ✅ Complete  
**Related Documents:** [Webhooks and Messaging](18-webhooks-messaging.md) | [Policy Organization](14-policy-profiles.md) | [Deployment and Redundancy](17-deployment-redundancy.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: PROVIDER**
>
> The Provider abstraction — Auth Provider and Credential Provider extensions



---

## 1. Purpose

DCM authenticates and authorizes every request — inbound and outbound — through a unified **Auth Provider** model. An Auth Provider is the eighth DCM provider type: an external (or built-in) system that answers two questions:

1. **Authentication** — is this identity who they claim to be?
2. **Authorization** — what is this identity permitted to do?

Every authentication mode DCM supports — static API key, local users, GitHub OAuth, LDAP, FreeIPA, Active Directory, OIDC, mTLS — is an Auth Provider implementation. The built-in Auth Provider ships with DCM and requires zero external configuration, enabling immediate home lab and evaluation use. External Auth Providers are registered artifacts, versioned, GitOps-managed, and audited.

**Authentication is always required — there is no anonymous access in any DCM profile.** The difference between profiles is how much effort authentication setup requires, not whether it exists.

---

## 2. Auth and Credential Provider Types

Auth Providers and Credential Providers are two of the eleven DCM provider types (see [Unified Provider Contract](A-provider-contract.md)). This section covers the authentication modes and configurations supported:

Auth Provider completes the DCM provider ecosystem:

| # | Type | Purpose |
|---|------|---------|
| 1 | **Service Provider** | Realizes resources |
| 2 | **Information Provider** | Serves authoritative external data |
| 3 | **Meta Provider** | Composes multiple providers |
| 4 | **Storage Provider** | Persists DCM state |
| 5 | **Policy Provider** | Evaluates policies externally |
| 6 | **Credential Provider** | Manages secrets and credentials |
| 7 | **Auth Provider** | Authenticates actor identities |
| 8 | **Notification Provider** | Delivers notifications |
| 9 | **Message Bus Provider** | Async event streaming |
| 10 | **Registry Provider** | Serves the Resource Type Registry |
| 11 | **Peer DCM** | Another DCM instance (federation) |

---

## 3. Auth Provider Registration

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

  # Provider type
  provider_type: <built_in|static_api_key|local_users|
                  ldap|active_directory|freeipa|
                  oidc|saml|github_oauth|gitlab_oauth|
                  kerberos|mtls|custom>

  # What actor types this provider can authenticate
  authenticates: [human, service_account, webhook_service_account]

  # Trust level
  trust_level: <authoritative|verified|advisory>
  # authoritative: DCM accepts all decisions without re-evaluation
  # verified:      DCM accepts with additional Policy Engine checks
  # advisory:      DCM treats decisions as input — full re-evaluation always

  # Connection credentials
  connection_credentials_ref:
    service_provider_uuid: <uuid>
    secret_path: "dcm/auth/freeipa/bind-password"

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

  # Role mapping — external groups → DCM roles
  role_mapping:
    default_role: consumer
    group_role_map:
      - external_group: "cn=dcm-admins,cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
        dcm_role: platform_admin
      - external_group: "cn=dcm-sre,cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
        dcm_role: sre
      - external_group: "cn=dcm-consumers,cn=groups,cn=accounts,dc=corp,dc=example,dc=com"
        dcm_role: consumer

  # Tenant mapping — external groups → DCM Tenants
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

## 4. Authentication Modes

### 4.1 Built-In Auth Provider (zero configuration)

Ships with DCM. Always registered. Cannot be deregistered — only deprioritized.

```yaml
built_in_auth_provider:
  handle: "providers/auth/dcm-builtin"
  provider_type: built_in
  modes:
    static_api_key:
      enabled: true             # generated at bootstrap — shown once
    local_users:
      enabled: true             # managed via: dcm user create
    github_oauth:
      enabled: false            # opt-in: requires client_id + secret
    gitlab_oauth:
      enabled: false            # opt-in: requires client_id + secret
```

**Static API Key** — generated at bootstrap, shown once:
```
✓ DCM is ready.
Your bootstrap API key (shown once — store it securely):
  dcm_sk_a1b2c3...f7g8

curl -H "Authorization: Bearer dcm_sk_a1b2c3...f7g8" https://localhost:8443/api/v1/catalog
```

**Local Users** — managed via CLI:
```bash
dcm user create --username admin --role platform_admin
dcm user create --username developer --role consumer --tenant payments
```

### 4.2 GitHub / GitLab OAuth

```yaml
auth_provider:
  provider_type: github_oauth
  config:
    client_id: <github_oauth_app_client_id>
    client_secret_ref:
      service_provider: dcm_internal
      path: "dcm/auth/github/client-secret"
    role_mapping:
      default_role: consumer
      org_role_map:
        - github_org: "my-lab-org"
          dcm_role: platform_admin
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
        service_provider: dcm_internal
        path: "dcm/auth/freeipa/ca-cert"
    bind_dn: "uid=dcm-service,cn=users,cn=accounts,dc=corp,dc=example,dc=com"
    bind_password_ref:
      service_provider: dcm_internal
      path: "dcm/auth/freeipa/bind-password"

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
        service_provider: dcm_internal
        path: "dcm/auth/freeipa/dcm.keytab"
      service_principal: "HTTP/dcm.corp.example.com@CORP.EXAMPLE.COM"
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
        service_provider: dcm_internal
        path: "dcm/auth/ad/ca-cert"
    bind_dn: "CN=DCM Service,OU=Service Accounts,DC=corp,DC=example,DC=com"
    bind_password_ref:
      service_provider: dcm_internal
      path: "dcm/auth/ad/bind-password"

    user_search:
      base_dn: "DC=corp,DC=example,DC=com"
      filter: "(sAMAccountName={username})"
      # UPN alternative: "(userPrincipalName={username}@corp.example.com)"
      attributes:
        username: sAMAccountName
        email: userPrincipalName
        display_name: displayName
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
      service_provider: dcm_internal
      path: "dcm/auth/oidc/client-secret"
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
      service_provider: dcm_internal
      path: "dcm/auth/mtls/ca-cert"
    # Client certificate CN → DCM actor mapping
    cn_actor_mapping:
      - cn_pattern: "service-account-*"
        actor_type: service_account
        default_role: consumer
      - cn_pattern: "provider-*"
        actor_type: provider
```

---

## 5. Multiple Auth Providers — Priority and Routing

DCM routes to the appropriate Auth Provider based on the authentication signal present in the request:

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

### 5.1 Auth Provider Chain

Authentication and authorization enrichment can be chained:

```yaml
auth_provider_chain:
  authentication:
    provider_uuid: <freeipa-ldap-uuid>   # fast LDAP bind
  enrichment:
    provider_uuid: <freeipa-ldap-uuid>   # LDAP group membership
  augmentation:
    provider_uuid: <corporate-oidc-uuid> # OIDC userinfo for rich claims
    # (department, cost_center, project codes from HR system)
```

---

## 6. Credential Provider

A **Credential Provider** is the seventh DCM provider type — a cross-cutting dependency that any DCM component or provider registration references for secret resolution. DCM never stores credentials directly.

```yaml
service_provider_registration:
  artifact_metadata:
    uuid: <uuid>
    handle: "providers/credentials/hashicorp-vault-prod"
    status: active

  name: "HashiCorp Vault Production"
  backend_type: <hashicorp_vault|aws_secrets_manager|azure_key_vault|
                 gcp_secret_manager|kubernetes_secrets|cyberark|
                 delinea|external_api|dcm_internal>

  connection:
    endpoint: https://vault.corp.example.com:8200
    auth_method: <kubernetes|approle|token|aws_iam|ldap>
    namespace: <vault namespace>

  credential_types: [hmac_secret, api_key, certificate, connection_string,
                     bearer_token, private_key, username_password, ldap_bind]

  health_check:
    interval_seconds: 60
    on_unhealthy: <alert|suspend_dependents|fail_open>
    # suspend_dependents: suspend all components using this provider
    # fail_open: continue using cached credentials (risk — use cautiously)

  caching:
    enabled: true
    ttl_seconds: 300             # refresh from vault every 5 minutes
```

**Credential references** — used everywhere a secret is needed:

```yaml
# In webhook authentication
secret_ref:
  service_provider_uuid: <uuid>
  secret_path: "dcm/webhooks/payments/hmac-secret"
  version: latest

# In Auth Provider connection
bind_password_ref:
  service_provider_uuid: <uuid>
  secret_path: "dcm/auth/freeipa/bind-password"

# In Service Provider registration
credentials_ref:
  service_provider_uuid: <uuid>
  secret_path: "dcm/providers/kubevirt/service-account"
```

Credentials are cached in memory per the configured TTL. On cache miss, DCM fetches from the Credential Provider. Credentials never appear in audit records (only the `secret_path` is recorded), never in Git, never in logs.

---

## 7. The Authentication Ladder

Every rung is authenticated. The ladder is about setup effort — not whether authentication exists.

| Profile | Auth Modes Available | Setup Effort | Notes |
|---------|---------------------|-------------|-------|
| `minimal` | Static API key, Local user/password | 30 seconds – 2 minutes | Generated at bootstrap; zero external config |
| `dev` | + GitHub/GitLab OAuth, FreeIPA/AD (direct bind) | 5–15 minutes | OAuth requires app registration; LDAP requires server config |
| `standard` | + OIDC via broker (Dex/Keycloak), AD/FreeIPA direct | 30–60 minutes | Enterprise directory or IdP integration |
| `prod` | + OIDC direct, MFA | 1–2 hours | Full enterprise IdP; MFA configurable |
| `fsi` | + mTLS required, MFA required | 4–8 hours | Certificate infrastructure required |
| `sovereign` | + Air-gapped OIDC/mTLS | 1–2 days | No external auth dependencies |

### 7.1 First-Run Setup

```
DCM First Run Setup
═══════════════════════════════════════════════════════

Welcome to DCM. Choose an authentication mode:

  [1] Static API Key    — Instant start. One key, full access.
                          Best for: solo home lab, quick evaluation.

  [2] Local Users       — Create usernames and passwords.
                          Best for: small team, dev environment.

  [3] GitHub OAuth      — Login with GitHub accounts.
                          Best for: dev teams using GitHub.

  [4] Configure later   — Start with API key, switch to OIDC/LDAP later.

Choice [1]:
```

### 7.2 The Upgrade Path

Authentication configuration is a DCM artifact — versioned, stored in Git, upgradeable via standard lifecycle:

```bash
# Upgrade from static API key to FreeIPA LDAP
dcm auth configure \
  --provider-type freeipa \
  --server ldaps://freeipa.corp.example.com:636 \
  --bind-dn "uid=dcm-service,..." \
  --bind-password-ref "dcm/auth/freeipa/bind-password"
# DCM validates, runs in shadow mode, cuts over — API key deprecated on schedule
```

---

## 8. Profile-Governed Enforcement

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

> **Session revocation lifecycle:** See [Session Token Revocation](35-session-revocation.md) for the complete session revocation model including AUTH-016–AUTH-022 (actor deprovisioning, revocation registry, token introspection, concurrent session enforcement).

## 9. System Policies

| Policy | Rule |
|--------|------|
| `AUTH-001` | All DCM authentication must be handled through a registered Auth Provider. The built-in Auth Provider is always available and cannot be deregistered. |
| `AUTH-002` | Multiple Auth Providers may be registered simultaneously. The ingress layer routes to the appropriate provider based on the authentication signal in the request. |
| `AUTH-003` | Auth Provider trust level governs how DCM treats decisions: authoritative (accepted as-is), verified (with Policy Engine augmentation), advisory (full re-evaluation). |
| `AUTH-004` | Auth Provider role and tenant mappings are versioned artifacts subject to standard DCM artifact lifecycle. Changes go through proposed → active validation. |
| `AUTH-005` | If an Auth Provider becomes unhealthy, existing sessions remain valid until TTL expiry. New authentication attempts route to the configured fallback provider or are rejected. |
| `AUTH-006` | The Auth Provider used to authenticate a request is recorded in the ingress block and carried into the audit record. Policies may act on auth_provider_uuid and provider_type. |
| `AUTH-007` | Auth Provider configuration credentials must reference a registered Credential Provider. Plaintext credentials are rejected. |
| `AUTH-008` | There is no anonymous access in any DCM profile. Minimal and dev profiles support lightweight authenticated modes requiring minimal setup. |
| `AUTH-009` | Webhook and message bus inbound surfaces always require authentication regardless of active Profile. Anonymous actors are never permitted on these surfaces. |
| `AUTH-010` | Rate limiting is enforced per authenticated actor. Limits are declared on the Auth Provider or webhook actor registration. |

---

## 10. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should DCM support SCIM for automated user provisioning from enterprise IdPs? | Enterprise integration | ✅ Resolved — SCIM 2.0 (RFC 7643 / RFC 7644) optional capability; provisions actors and group memberships; roles not SCIM-provisioned; suspend on deprovision default (AUTH-012) |
| 2 | How does Auth Provider failover interact with in-flight requests during the transition? | Reliability | ✅ Resolved — in-flight requests complete on cached tokens; failover chain for new auth; session TTL respected during outage; all providers unavailable → reject (AUTH-013) |
| 3 | Should MFA enforcement be per-operation (step-up MFA) or per-session? | Security UX | ✅ Resolved — two-tier MFA: per-session + step-up; policy declares which operations require step-up; PT10M step-up token TTL; profile-governed defaults (AUTH-014) |
| 4 | Should the built-in Auth Provider's local user store be backed by a pluggable database? | Architecture | ✅ Resolved — pluggable storage backend; SQLite for minimal/dev; PostgreSQL for standard+; encryption required for fsi/sovereign; local store for bootstrap/service accounts only (AUTH-015) |

---

## 11. Related Concepts

- **Webhooks and Messaging** (doc 18) — ingress/egress actor model; webhook actor registration
- **Policy Organization** (doc 14) — policies act on auth_provider_type and ingress fields
- **Universal Audit Model** (doc 16) — auth provider and ingress context in every audit record
- **Credential Provider** — resolves all Auth Provider connection secrets
- **Universal Group Model** (doc 15) — group memberships resolved via Auth Provider group sync

## 10. Git Identity Resolution

When DCM processes Git PR ingress, it must resolve the Git server's verified actor identity to a DCM actor with full role, group, and tenant scope context — identical to web UI or API login for the same user.

### 10.1 The Trust Model

DCM trusts the **Git server's authentication assertion** — not user-declared Git configuration. The Git server has already authenticated the user (via SSH key, OAuth token, or LDAP password). DCM receives the Git server's verified identity from the PR merge webhook and resolves it through the registered Auth Provider.

```
Git server authenticates user → PR merge webhook → DCM Auth Provider resolution → DCM actor
```

### 10.2 Resolution Methods

| Method | When Used | Auth Provider |
|--------|----------|--------------|
| `oidc_subject_lookup` | Git server uses same OIDC/OAuth IdP as DCM | OIDC Auth Provider |
| `ldap_username_lookup` | Git server authenticates via LDAP/AD | LDAP/AD Auth Provider |
| `ssh_key_fingerprint` | SSH key-authenticated Git workflows | DCM SSH key registry |
| `webhook_service_account` | Automated CI/CD Git workflows | Registered webhook actor |

### 10.3 The Resolved Actor

The resolved Git actor carries **identical** role, group, and tenant scope to the same user authenticating via web UI:

```yaml
# A user who logs into the web UI via FreeIPA LDAP gets:
# roles: [sre], tenant_scope: [payments-uuid], groups: [payments-team-uuid]

# The same user merging a Git PR via their Git account gets:
# roles: [sre], tenant_scope: [payments-uuid], groups: [payments-team-uuid]
# — identical — because both resolve through the same FreeIPA Auth Provider
```

This is the key invariant: **Git PR ingress does not grant different permissions than any other ingress surface.** The same Auth Provider, the same group mappings, the same tenant scope enforcement.

### 10.4 System Policy

| Policy | Rule |
|--------|------|
| `AUTH-011` | Git PR actor identity resolution must use the registered Auth Provider. DCM trusts the Git server's verified identity assertion — not user-declared Git configuration. The resolved actor carries the same role, group, and tenant scope as any other user authenticated via the same Auth Provider. |


## 11. Auth Provider Gap Resolutions

### 11.1 SCIM 2.0 User Provisioning (Q1)

DCM supports SCIM 2.0 as an optional Auth Provider capability for enterprise deployments. SCIM automates actor lifecycle management — provisioning, attribute updates, and deprovisioning — from enterprise IdPs (Okta, Azure AD, Ping Identity, JumpCloud).

```yaml
scim_provider_config:
  enabled: true
  scim_version: "2.0"
  endpoint: https://dcm.corp.example.com/scim/v2
  auth:
    mode: bearer_token
    token_ref:
      service_provider_uuid: <uuid>
      path: "dcm/auth/scim/bearer-token"

  provisioned_resources:
    dcm_actors: true             # create/update/deactivate DCM actor records
    group_memberships: true      # manage DCM group memberships from IdP groups
    role_assignments: false      # roles managed by DCM policy — not SCIM

  attribute_mapping:
    idp_userName: actor.username
    idp_email: actor.email
    idp_displayName: actor.display_name
    idp_department: actor.status_metadata.department
    idp_groups: actor.groups     # IdP groups → DCM group memberships (where mapped)

  on_user_deprovisioned:
    action: suspend              # suspend | deactivate | archive
    # suspend: reversible; sessions terminated; leases released
    in_flight_request_handling: complete_then_suspend
```

**What SCIM does NOT manage:** Roles are not SCIM-provisioned — they require explicit DCM policy authorization. This prevents privilege escalation through the SCIM channel.

### 11.2 Auth Provider Failover and In-Flight Requests (Q2)

In-flight requests authenticated before Auth Provider failure continue to completion using cached session tokens. New requests follow the declared failover chain.

```yaml
auth_failover_config:
  primary_provider_uuid: <ldap-uuid>
  failover_chain:
    - provider_uuid: <oidc-backup-uuid>
      promotion_delay: PT30S          # wait 30s before promoting failover
    - provider_uuid: <local-users-uuid>
  session_cache:
    enabled: true
    ttl: PT8H                         # valid sessions remain valid during outage
```

**Three scenarios:**
- **Mid-assembly request (already authenticated):** Continues to completion — session token carries resolved roles/groups/tenant scope; Auth Provider not needed for assembly
- **New request, Auth Provider down:** Follows failover chain; served from session cache if session still valid
- **Session expiry during outage:** Requires re-authentication via available failover provider; if all unavailable → reject with clear error

### 11.3 Step-Up MFA (Q3)

MFA enforcement is two-tier: per-session (validated at login, captured in `mfa_verified` field) and step-up (additional challenge at sensitive operations within an already-authenticated session).

```yaml
step_up_mfa_config:
  step_up_required_for:
    - platform_policy_activate
    - provider_decommission
    - tenant_decommission
    - sovereignty_zone_change
    - auth_provider_update
    - manual_rehydration          # if entity min_auth_level = hardware_token_mfa
  step_up_method: <totp|push_notification|hardware_token|sms>
  step_up_token_ttl: PT10M
  step_up_challenge_max_age: PT5M
```

**Profile defaults:**

| Profile | Per-Session MFA | Step-Up Required |
|---------|----------------|-----------------|
| minimal | No | No |
| dev | No | No |
| standard | Recommended | Optional |
| prod | Required | Destructive operations |
| fsi | Required | All policy changes |
| sovereign | Required (hardware token) | All administrative operations |

### 11.4 Built-In Auth Provider Storage Backend (Q4)

The built-in Auth Provider's local user store uses a pluggable storage backend following the Storage Provider model.

```yaml
builtin_auth_provider_config:
  user_store:
    profile_defaults:
      minimal: sqlite            # zero infrastructure; single-file
      dev: sqlite
      standard: postgresql       # durable; concurrent; backupable
      prod: postgresql
      fsi: postgresql            # encrypted storage (TDE required)
      sovereign: postgresql      # HSM-backed encryption required
    encryption_at_rest:
      required_profiles: [fsi, sovereign]
      key_ref:
        service_provider_uuid: <uuid>
        path: "dcm/auth/builtin/encryption-key"
```

**The local user store should only contain:** bootstrap users, service accounts, and API key holders. Enterprise users belong in external Auth Providers (LDAP, OIDC, SCIM).

### 11.5 System Policies — Auth Provider Gaps

| Policy | Rule |
|--------|------|
| `AUTH-012` | DCM supports SCIM 2.0 as an optional Auth Provider capability. SCIM provisions and deprovisions DCM actors and group memberships. Roles are not SCIM-provisioned — they require explicit DCM policy authorization. SCIM deprovisioning suspends actors by default; in-flight requests complete before suspension. |
| `AUTH-013` | In-flight requests authenticated before Auth Provider failure continue using cached session tokens. New requests follow the declared failover chain. Sessions remain valid for their declared TTL during outages. Session expiry during outage requires re-authentication via available failover provider. All providers unavailable → new authentication rejected. |
| `AUTH-014` | MFA enforcement is two-tier: per-session MFA (captured in mfa_verified field) and step-up MFA (additional challenge at sensitive operations). Policy declares which operations require step-up regardless of session MFA status. Step-up tokens are short-lived (PT10M default). Profile governs default requirements. |
| `AUTH-015` | The built-in Auth Provider uses a pluggable storage backend. SQLite is the default for minimal/dev profiles. PostgreSQL is the default for standard+ profiles. FSI and sovereign profiles require encryption at rest. The local user store should only contain bootstrap users, service accounts, and API key holders. |


---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
