# DCM Data Model — Credential Management

**Document Status:** ✅ Complete
**Document Type:** Architecture Specification — Credential lifecycle, prescribed secrets infrastructure, consumer credential services
**Related Documents:** [Infrastructure Requirements](51-infrastructure-optimization.md) | [Internal Component Auth](36-internal-component-auth.md) | [Provider Callback Auth](43-provider-callback-auth.md)

> **Foundation Document Reference**
>
> Credential management in DCM operates at two levels:
> 1. **Prescribed infrastructure** — Vault-compatible secrets API for DCM's own operational secrets
> 2. **Consumer-facing services** — service_providers that handle `Credential.*` resource types
>
> **This document maps to: DATA + PROVIDER**

---

## 1. Two Levels of Credential Management

### 1.1 DCM Internal — Secrets Management

DCM manages its own operational secrets using an Internal/External pattern (same as policy evaluation):

**Internal mode (default):** Secrets are stored in DCM's PostgreSQL database in a `secrets` table using envelope encryption. Each value is encrypted with AES-256-GCM using a per-secret data encryption key (DEK). DEKs are encrypted with a master key (KEK) sourced from the deployment environment (environment variable for homelab, Kubernetes Secret for standard, HSM via PKCS#11 for sovereign). No external secrets infrastructure required.

**External mode (optional):** Organizations with existing Vault infrastructure can register a Vault-compatible API endpoint. DCM calls the Vault HTTP API for all secret operations. Vault, OpenBao, or any API-compatible implementation works.

DCM uses secrets management for:

- **Provider authentication credentials** — the PCA model (doc 43) stores credential references in DCM, actual values encrypted in the secrets store
- **Encryption keys** for data-at-rest on sensitive JSONB fields (PHI, PCI data classifications)
- **Audit signing keys** for hash chain integrity
- **Internal service credentials** — database connection strings, API keys for auth providers

For mTLS between control plane services, cert-manager or the service mesh handles certificate issuance — DCM does not manage those directly.

### 1.2 Consumer-Facing — Service Providers for Credential Resources

When consumers request credential resources (API keys, certificates, SSH keys, secrets), those requests go through the standard DCM pipeline. A `service_provider` that declares `Credential.*` in its `supported_resource_types` handles them:

```yaml
provider:
  provider_type: service_provider
  supported_resource_types:
    - "Credential.Secret"
    - "Credential.Certificate"
    - "Credential.SSHKey"
    - "Credential.APIKey"
  capability_extension:
    hsm_support: true
    rotation_protocol: automatic
    max_secret_size_bytes: 65536
    supported_algorithms: [rsa-2048, rsa-4096, ecdsa-p256, ecdsa-p384, ed25519]
```

The provider contract is the same as any service_provider: create, update (rotate), decommission (revoke), discover. The capability extension declares credential-specific capabilities.

---

## 2. Credential Types

| Type | Resource Type | Description |
|------|--------------|-------------|
| API Key | `Credential.APIKey` | Opaque bearer token for API authentication |
| JWT | `Credential.JWT` | JSON Web Token with claims, issued by auth_provider |
| mTLS Certificate | `Credential.Certificate` | X.509 certificate for mutual TLS |
| SSH Key | `Credential.SSHKey` | SSH public/private key pair |
| Secret | `Credential.Secret` | Arbitrary secret value (password, connection string) |
| Signing Key | `Credential.SigningKey` | Cryptographic key for signing operations |

---

## 3. Credential Lifecycle

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

### 3.1 Rotation Model

Credential rotation follows a two-phase model:

1. **New credential issued** — new value active, old value enters grace period
2. **Grace period expires** — old value revoked

The grace period allows consumers to update their references without downtime. Grace period duration is configurable per credential type and deployment profile.

**Rotation triggers:**
- Scheduled (TTL-based) — credential approaches expiry
- Security event — compromise detected, immediate rotation
- Policy-driven — compliance requirement mandates rotation interval
- Consumer-initiated — explicit rotation request

### 3.2 Revocation Model

Revocation is immediate and permanent. Revoked credentials cannot be reactivated.

**Revocation triggers:**
- Actor deprovisioned — all credentials for the actor are revoked
- Security event — credential compromise, immediate revocation with no grace period
- Provider deregistered — all credentials issued to the provider are revoked
- Consumer request — explicit revocation via API

---

## 4. Cryptographic Algorithm Requirements

| Profile | Minimum Key Size | Allowed Algorithms |
|---------|-----------------|-------------------|
| `minimal`, `dev` | RSA-2048, ECDSA P-256 | RSA, ECDSA, Ed25519 |
| `standard`, `prod` | RSA-3072, ECDSA P-256 | RSA, ECDSA, Ed25519 |
| `fsi`, `sovereign` | RSA-4096, ECDSA P-384 | RSA, ECDSA, Ed25519 (no RSA-2048) |

Forbidden algorithms (all profiles): MD5, SHA-1, DES, 3DES, RC4, RSA-1024.

HSM backing is required for `sovereign` profile signing keys. Vault's seal mechanism or transit engine backed by an HSM satisfies this requirement.

---

## 5. Credential Delivery to Consumers

Consumers never receive credential values through the DCM API. Instead, DCM returns a **credential reference** — a Vault path or equivalent that the consumer's application resolves at runtime:

```yaml
# DCM returns this in the realized entity:
credentials:
  db_password:
    ref: "vault:secret/data/tenant-alpha/pet-clinic-db/password"
    type: Credential.Secret
    rotation_schedule: "P90D"
    expires_at: "2026-07-01T00:00:00Z"
```

The consumer's application uses its own Vault authentication (Kubernetes service account, AppRole, etc.) to retrieve the actual value. DCM's audit trail records that the credential reference was issued — not the credential value.

---

## 6. Profile-Governed Configuration

| Setting | `minimal`/`dev` | `standard`/`prod` | `fsi`/`sovereign` |
|---------|-----------------|-------------------|-------------------|
| Default TTL | P365D | P90D | P30D |
| Max TTL | Unlimited | P365D | P90D |
| Rotation grace period | P7D | P3D | P1D |
| HSM required | No | No | Yes (signing keys) |
| Idle credential detection | Disabled | P90D warning | P30D auto-revoke |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
