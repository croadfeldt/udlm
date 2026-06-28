# UDLM — Standards and Compliance Catalog

**Document Status:** ✅ Stable — UDLM substrate reference
**Document Type:** Substrate Reference — Normative External Standards
**Purpose:** Single authoritative source for all RFCs, protocols, specifications, and compliance frameworks referenced by the UDLM substrate. For each standard: what it is, where the substrate uses it, and what obligation it places on conformant realizations.

> **How to read this document:**
> - **Normative** — UDLM-conformant realizations MUST comply with this standard in the specified context
> - **Informative** — UDLM draws on this standard as guidance or reference without strict compliance
> - **Optional** — UDLM supports this standard in applicable profiles or configurations

---

## 1. Internet Standards (IETF RFCs)

### 1.1 Authentication and Authorization

| RFC | Title | Use in UDLM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 7519** | JSON Web Token (JWT) | Bearer token format for session tokens and API key tokens; claims carry actor_uuid, roles, tenant_uuid, exp | Normative |
| **RFC 7517** | JSON Web Key (JWK) | Public key format for Auth Provider OIDC verification keys; JWKS endpoint for key discovery | Normative |
| **RFC 7662** | OAuth 2.0 Token Introspection | Session/token validation contract; response format `{active, session_uuid, actor_uuid, exp, roles}` | Normative |
| **RFC 6749** | OAuth 2.0 Authorization Framework | Authorization flow for OIDC Auth Providers; client credentials flow for service account API keys | Informative |
| **RFC 4511** | Lightweight Directory Access Protocol (LDAP) | LDAP/FreeIPA/Active Directory Auth Provider integration; bind operations, search filters for group membership | Normative |
| **RFC 7643** | SCIM 2.0 Core Schema | Actor and group provisioning schema for enterprise IdP integration | Normative |
| **RFC 7644** | SCIM 2.0 Protocol | SCIM REST API for actor provisioning; deprovisioning triggers session + credential revocation | Normative |
| **RFC 7009** | OAuth 2.0 Token Revocation | Token revocation surface for actor session and refresh tokens | Normative |

### 1.2 Transport Security

| RFC | Title | Use in UDLM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 8446** | TLS 1.3 | All external API communication; preferred TLS version; mandatory cipher suite compliance | Normative |
| **RFC 5246** | TLS 1.2 | Permitted TLS version for compatibility; minimum acceptable version; TLS 1.0/1.1 prohibited | Normative |
| **RFC 5280** | X.509 PKI Certificate and CRL Profile | All UDLM-substrate certificates (component mTLS, Internal CA, credential provider certs); CRL format for revocation; certificate chain validation | Normative |
| **RFC 6960** | Online Certificate Status Protocol (OCSP) | Internal CA OCSP endpoint for real-time certificate status; Internal CA CRL supplement | Normative |

### 1.3 Certificate Enrollment

| RFC | Title | Use in UDLM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 7030** | Enrollment over Secure Transport (EST) | Certificate enrollment for Internal CA (alternative to bootstrap token); preferred for automated cert lifecycle | Informative |
| **RFC 8555** | ACME — Automatic Certificate Management Environment | Automated certificate lifecycle for external-facing TLS certificates; provider certificates | Informative |
| **RFC 8894** | Simple Certificate Enrolment Protocol (SCEP) | Legacy certificate enrollment for environments without EST/ACME support | Optional |
| **RFC 4210** | Certificate Management Protocol (CMP) | X.509 PKI certificate management in enterprise PKI environments | Optional |

### 1.4 API Lifecycle

| RFC | Title | Use in UDLM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 8594** | The Sunset HTTP Header Field | Deprecated API version responses include `Sunset: <timestamp>` header | Normative |
| **RFC 9745** | The Deprecation HTTP Header Field | Deprecated API version responses include `Deprecation: <timestamp>` header paired with RFC 8594 Sunset | Normative |

### 1.5 Service Discovery and Health

| RFC | Title | Use in UDLM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 8615** | Well-Known Uniform Resource Identifiers | Version discovery endpoints; `/livez` and `/readyz` path conventions; IANA health+json media type | Normative |

### 1.6 Data Formats

| RFC | Title | Use in UDLM | Obligation |
|-----|-------|-----------|-----------|
| **ISO 8601** | Date and Time Format | All substrate timestamps: `created_at`, `expires_at`, `not_before`, `not_after`, event timestamps; durations as ISO 8601 periods (P90D, PT8H) | Normative |
| **RFC 8259** | The JavaScript Object Notation (JSON) Data Interchange Format | All UDLM API request/response bodies; all entity definitions in stores | Normative |

---

## 2. Identity and Access Protocols

| Protocol | Specification | Use in UDLM | Obligation |
|----------|--------------|-----------|-----------|
| **OIDC / OpenID Connect** | OpenID Foundation Core 1.0 | Primary enterprise Auth Provider type; ID token format; JWKS endpoint for key verification; userinfo endpoint for actor enrichment | Normative |
| **SAML 2.0** | OASIS SAML 2.0 | Auth Provider type for organizations without OIDC; assertion format for role mapping | Optional |
| **mTLS** | RFC 8446 + RFC 5280 | All internal component-to-component communication; provider-to-realization authentication in zero-trust model | Normative |
| **LDAP v3** | RFC 4511 | FreeIPA, Active Directory, OpenLDAP Auth Provider types; group membership queries for RBAC | Normative |
| **SCIM 2.0** | RFC 7643 + RFC 7644 | Optional enterprise provisioning; actor creation, update, deprovision; deprovision triggers parallel session + credential revocation | Optional |

---

## 3. Cryptographic Standards

| Standard | Use in UDLM | Profiles | Obligation |
|----------|-----------|---------|-----------|
| **ECDSA P-384** | Internal CA certificates; component mTLS certs; preferred curve for substrate-issued certificates | All profiles | Normative for Internal CA |
| **ECDSA P-256** | Permitted for performance-constrained contexts where P-384 is not available | minimal, dev | Optional |
| **RSA ≥ 2048** | Permitted for compatibility with legacy systems; RSA < 2048 prohibited | All profiles | Conditional |
| **AES-256-GCM** | Credential encryption at rest; audit record encryption (sovereign); data classification-driven | standard+ | Normative |
| **AES-128-GCM** | Permitted for minimal/dev profiles where performance matters | minimal, dev | Conditional |
| **SHA-256** | Hash function for audit chain integrity; entity handle generation; minimum acceptable | All profiles | Normative |
| **SHA-384 / SHA-512** | Preferred hash function for fsi/sovereign profiles | fsi, sovereign | Normative for fsi+ |
| **FIPS 140-2 Level 1** | Minimum cryptographic module requirement for standard/prod | standard, prod | Normative |
| **FIPS 140-2 Level 2** | Cryptographic module requirement for regulated environments | fsi, fedramp_moderate | Normative |
| **FIPS 140-3 Level 3** | Cryptographic module requirement for sovereign deployments | sovereign, dod_il4 | Normative |
| **TLS 1.3** | Preferred; mandatory cipher suites; forward secrecy required | All profiles | Normative (preferred) |
| **TLS 1.2** | Minimum acceptable; TLS 1.0/1.1 strictly prohibited | All profiles | Normative (minimum) |

### 3.1 Forbidden Algorithms

The substrate prohibits the following algorithms in all profiles:

| Algorithm | Reason |
|-----------|--------|
| MD5 | Cryptographically broken |
| SHA-1 | Deprecated; collision attacks demonstrated |
| DES | 56-bit key; insecure |
| 3DES / Triple-DES | Deprecated; Sweet32 attack |
| RC4 | Cryptographically broken |
| RSA < 2048 | Insufficient key length |
| ECDSA curves weaker than P-256 | Insufficient security level |

---

## 4. Operational Standards and Protocols

| Standard | Specification | Use in UDLM | Obligation |
|----------|--------------|-----------|-----------|
| **Prometheus / OpenMetrics** | Prometheus exposition format; OpenMetrics spec | `GET /metrics` scrape endpoint; all metric families; provider health metrics | Normative |
| **OpenTelemetry (OTel)** | CNCF OpenTelemetry specification | Distributed tracing for request pipeline; correlation ID propagation; span context for audit provenance | Informative |
| **Kubernetes API** | kubernetes.io API conventions | Resource type spec format mirrors k8s YAML; CRD-based realization integration; probe endpoints (/livez, /readyz) | Normative (k8s deployments) |
| **GitOps / OpenGitOps** | OpenGitOps principles (v1.0) | UDLM data model artifacts MAY be stored in Git; PR-based contribution model is one realization transport; Git as source of truth for policy and layer definitions where adopted | Informative |
| **Unix cron** | POSIX cron expression format | Recurring schedule expressions in scheduled requests and maintenance window definitions | Normative |
| **IANA health+json** | RFC 8615 + IANA media type registry | Health response format for `/livez`, `/readyz`, and substrate health endpoints | Normative |
| **W3C Server-Sent Events (SSE)** | W3C Living Standard | Optional live request status stream; alternative to polling for browser/CLI consumers | Normative (where supported) |
| **OpenAPI 3.1** | OpenAPI Initiative 3.1 | REST API specification format for Consumer API, Admin API, and substrate interface specifications; schema definitions for request/response bodies | Normative |
| **SPIFFE** | CNCF SPIFFE Specification v1.0 | Workload identity framework that informs the substrate's internal component identity model | Informative |
| **Istio / Service Mesh** | Istio service mesh specification | Internal component mTLS enforcement; traffic policies; circuit breaking; observability; service-to-service authorization | Normative (distributed deployments) |

---

## 5. Compliance Frameworks

These frameworks drive specific UDLM profiles, overlays, and policy constraints. UDLM does not certify compliance — it provides the substrate primitives that enable compliant realizations.

### 5.1 US Federal and Defense

| Framework | Full Name | UDLM Profile/Overlay | Key Substrate Requirements |
|-----------|-----------|-------------------|---------------------|
| **NIST SP 800-53** | Security and Privacy Controls for Information Systems | `fedramp_moderate`, `fedramp_high` | Policy control families mapped to UDLM policy domains; access control, audit, configuration management |
| **NIST SP 800-63B** | Digital Identity Guidelines | All profiles (AAL mapping) | AAL1 (minimal/dev), AAL2 (standard/prod), AAL2+ (fsi), AAL3 (sovereign); MFA requirements per level |
| **NIST SP 800-207** | Zero Trust Architecture | All profiles | Zero-trust posture defaults; five-check boundary model substrate |
| **FedRAMP Moderate** | Federal Risk and Authorization Management Program — Moderate | `fedramp_moderate` overlay | NIST 800-53 Moderate baseline; FIPS 140-2 Level 1+; Federal data handling requirements |
| **FedRAMP High** | Federal Risk and Authorization Management Program — High | `fedramp_high` overlay | NIST 800-53 High baseline; FIPS 140-2 Level 2+; enhanced audit retention |
| **DoD IL4** | Department of Defense Impact Level 4 | `dod_il4` overlay | Controlled Unclassified Information; FIPS 140-2 Level 2; hardware attestation; enhanced logging |
| **FIPS 140-2/140-3** | Federal Information Processing Standard — Cryptographic Modules | fsi+ profiles | Cryptographic module validation; forbidden algorithm enforcement; key management requirements |

### 5.2 Industry Compliance

| Framework | Full Name | UDLM Profile/Overlay | Key Substrate Requirements |
|-----------|-----------|-------------------|---------------------|
| **PCI DSS** | Payment Card Industry Data Security Standard | `pci_dss` overlay | Req 8.3.9: P90D maximum credential rotation; network segmentation via sovereignty constraints; cardholder data access logging; 12-month audit retention |
| **HIPAA** | Health Insurance Portability and Accountability Act | `fsi` profile; `hipaa` overlay | PHI access logging; minimum necessary access (RBAC); audit controls; transmission security (TLS 1.2+); workforce authentication (MFA) |
| **SOC 2** | Service Organization Control 2 | `standard`+ profiles | Type II audit trail requirements; availability, security, confidentiality trust service criteria; change management via artifact lifecycle |
| **ISO 27001** | Information Security Management Systems | All profiles | Risk-based approach; asset management; access control; cryptography; operations security; incident management |

### 5.3 Data Protection / Sovereignty

| Framework | Full Name | UDLM Feature | Key Substrate Requirements |
|-----------|-----------|------------|---------------------|
| **GDPR** | General Data Protection Regulation (EU) | Sovereignty constraints; data classification | Data residency enforcement; right to erasure model (entity decommission + audit retention policy); data minimization via field-level classification; consent/purpose tracking via Governance Matrix |
| **Schrems II** | CJEU ruling on EU-US data transfers | Sovereignty constraints; federation boundaries | Data transfer restrictions between federation peers; sovereign profile enforcement |

---

## 6. CNCF Ecosystem

UDLM is designed for CNCF ecosystem compatibility. The following CNCF projects are referenced as substrate context:

| Project | CNCF Status | UDLM Reference |
|---------|------------|---------|
| **Kubernetes** | Graduated | Deployment target; CRD-based realization integration; resource model inspiration |
| **Open Policy Agent (OPA)** | Graduated | Policy engine backend option; Rego policies for UDLM Gating Policy and Validation policy types |
| **Prometheus** | Graduated | Metrics exposition format; substrate scrape endpoint |
| **OpenTelemetry** | Graduated | Distributed tracing; correlation ID propagation |
| **Istio** | Graduated | Service mesh for internal mTLS; traffic policies |
| **Argo CD / Flux** | Graduated | GitOps delivery for substrate layer definitions and policy artifacts |

---

## 7. Authentication Assurance Levels (NIST SP 800-63B)

UDLM maps profile security postures to NIST Authentication Assurance Levels:

| Profile | AAL | Requirements |
|---------|-----|-------------|
| `minimal` | AAL1 | Single-factor authentication acceptable; password or API key |
| `dev` | AAL1 | Single-factor authentication acceptable |
| `standard` | AAL2 | MFA required for all actor sessions; phishing-resistant preferred |
| `prod` | AAL2 | MFA required; TOTP, FIDO2, or hardware token |
| `fsi` | AAL2+ | MFA required; phishing-resistant authenticator (FIDO2/hardware token) |
| `sovereign` | AAL3 | Hardware-based authenticator required; verifier impersonation resistance; physical authenticator possession |

---

*UDLM substrate reference document. Realization-specific implementation choices (which TLS libraries, which OAuth libraries, which Prometheus exporters, which Kubernetes CRDs, which compliance frameworks are enforced per profile, certificate and key management procedures, etc.) live in the consuming realization's documentation.*
