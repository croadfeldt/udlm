# DCM Data Model — Standards and Compliance Catalog

**Document Status:** 🔄 In Progress
**Document Type:** Architecture Reference — Normative Standards
**Purpose:** Single authoritative source for all RFCs, protocols, specifications, and compliance frameworks referenced by the DCM architecture. For each standard: what it is, where DCM uses it, and what obligation it places on implementations.

> **How to read this document:**
> - **Normative** — DCM implementations MUST comply with this standard in the specified context
> - **Informative** — DCM draws on this standard as guidance or reference without strict compliance
> - **Optional** — DCM supports this standard in applicable profiles or configurations

---

## 1. Internet Standards (IETF RFCs)

### 1.1 Authentication and Authorization

| RFC | Title | Use in DCM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 7519** | JSON Web Token (JWT) | Bearer token format for session tokens and API key tokens; claims carry actor_uuid, roles, tenant_uuid, exp | Normative |
| **RFC 7517** | JSON Web Key (JWK) | Public key format for Auth Provider OIDC verification keys; JWKS endpoint for key discovery | Normative |
| **RFC 7662** | OAuth 2.0 Token Introspection | `POST /api/v1/auth:introspect` — validates bearer tokens; response format `{active, session_uuid, actor_uuid, exp, roles}` | Normative |
| **RFC 6749** | OAuth 2.0 Authorization Framework | Authorization flow for OIDC Auth Providers; client credentials flow for service account API keys | Informative |
| **RFC 4511** | Lightweight Directory Access Protocol (LDAP) | LDAP/FreeIPA/Active Directory Auth Provider integration; bind operations, search filters for group membership | Normative |
| **RFC 7643** | SCIM 2.0 Core Schema | Actor and group provisioning schema for enterprise IdP integration; SCIM deprovision triggers session + credential revocation | Normative |
| **RFC 7644** | SCIM 2.0 Protocol | SCIM REST API for actor provisioning; DELETE triggers AUTH-016 (session) and CPX-006 (credential) revocation in parallel | Normative |

### 1.2 Transport Security

| RFC | Title | Use in DCM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 8446** | TLS 1.3 | All external API communication; preferred TLS version; mandatory cipher suite compliance | Normative |
| **RFC 5246** | TLS 1.2 | Permitted TLS version for compatibility; minimum acceptable version; TLS 1.0/1.1 prohibited | Normative |
| **RFC 5280** | X.509 PKI Certificate and CRL Profile | All DCM certificates (component mTLS, Internal CA, credential management service certs); CRL format for revocation; certificate chain validation | Normative |
| **RFC 6960** | Online Certificate Status Protocol (OCSP) | Internal CA OCSP endpoint for real-time certificate status; Internal CA CRL supplement | Normative |

### 1.3 Certificate Enrollment

| RFC | Title | Use in DCM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 7030** | Enrollment over Secure Transport (EST) | Certificate enrollment for Internal CA (alternative to bootstrap token); preferred for automated cert lifecycle | Informative |
| **RFC 8555** | ACME — Automatic Certificate Management Environment | Automated certificate lifecycle for external-facing TLS certificates; provider certificates | Informative |
| **RFC 8894** | Simple Certificate Enrolment Protocol (SCEP) | Legacy certificate enrollment for environments without EST/ACME support | Optional |
| **RFC 4210** | Certificate Management Protocol (CMP) | X.509 PKI certificate management in enterprise PKI environments | Optional |

### 1.4 API Lifecycle

| RFC | Title | Use in DCM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 8594** | The Sunset HTTP Header Field | Deprecated API version responses include `Sunset: <timestamp>` header (VER-003); also `Deprecation` header | Normative |
| **RFC 9745** | The Deprecation HTTP Header Field | Deprecated API version responses include `Deprecation: <timestamp>` header paired with RFC 8594 Sunset | Normative |

### 1.5 Service Discovery and Health

| RFC | Title | Use in DCM | Obligation |
|-----|-------|-----------|-----------|
| **RFC 8615** | Well-Known Uniform Resource Identifiers | `GET /.well-known/dcm-api-versions` (version discovery); `/livez` and `/readyz` path conventions; IANA health+json media type | Normative |

### 1.6 Data Formats

| RFC | Title | Use in DCM | Obligation |
|-----|-------|-----------|-----------|
| **ISO 8601** | Date and Time Format | All timestamps in DCM: `created_at`, `expires_at`, `not_before`, `not_after`, event timestamps; durations as ISO 8601 periods (P90D, PT8H) | Normative |
| **RFC 8259** | The JavaScript Object Notation (JSON) Data Interchange Format | All DCM API request/response bodies; all entity definitions in stores | Normative |

---

## 2. Identity and Access Protocols

| Protocol | Specification | Use in DCM | Obligation |
|----------|--------------|-----------|-----------|
| **OIDC / OpenID Connect** | OpenID Foundation Core 1.0 | Primary enterprise Auth Provider type; ID token format; JWKS endpoint for key verification; userinfo endpoint for actor enrichment | Normative |
| **SAML 2.0** | OASIS SAML 2.0 | Auth Provider type for organizations without OIDC; assertion format for role mapping | Optional |
| **mTLS** | RFC 8446 + RFC 5280 | All internal component-to-component communication (ICOM-001); provider-to-DCM authentication in ZTS model | Normative |
| **LDAP v3** | RFC 4511 | FreeIPA, Active Directory, OpenLDAP Auth Provider types; group membership queries for RBAC | Normative |
| **SCIM 2.0** | RFC 7643 + RFC 7644 | Optional enterprise provisioning; actor creation, update, deprovision; deprovision triggers parallel session + credential revocation | Optional |

---

## 3. Cryptographic Standards

| Standard | Use in DCM | Profiles | Obligation |
|----------|-----------|---------|-----------|
| **ECDSA P-384** | Internal CA certificates; component mTLS certs; preferred curve for all DCM-issued certificates | All profiles | Normative for Internal CA |
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

DCM prohibits the following algorithms in all profiles:

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

| Standard | Specification | Use in DCM | Obligation |
|----------|--------------|-----------|-----------|
| **Prometheus / OpenMetrics** | Prometheus exposition format; OpenMetrics spec | `GET /metrics` scrape endpoint; all DCM metric families (HLT-005); provider health metrics | Normative |
| **OpenTelemetry (OTel)** | CNCF OpenTelemetry specification | Distributed tracing for request pipeline; X-DCM-Correlation-ID propagation; span context for audit provenance | Informative |
| **Kubernetes API** | kubernetes.io API conventions | Resource type spec format mirrors k8s YAML; CRD-based DCM Operator integration; probe endpoints (/livez, /readyz) | Normative (k8s deployments) |
| **GitOps / OpenGitOps** | OpenGitOps principles (v1.0) | All DCM data model artifacts stored in Git; PR-based contribution model; Git as source of truth for policy and layer definitions | Normative |
| **Unix cron** | POSIX cron expression format | Recurring schedule expressions in scheduled requests (doc 37) and maintenance window definitions | Normative |
| **IANA health+json** | RFC 8615 + IANA media type registry | Health response format for `/livez`, `/readyz`, `/api/v1/admin/health`, and OIS health endpoint | Normative |
| **W3C Server-Sent Events (SSE)** | W3C Living Standard | `GET /api/v1/requests/{uuid}/stream` live request status stream; events: status_change, progress_updated, approval_required, approval_recorded, heartbeat; stream closes on terminal status; alternative to polling for browser/CLI consumers | Normative |
| **OpenAPI 3.1** | OpenAPI Initiative 3.1 | REST API specification format for Consumer API, Admin API, and Operator Interface Specification; schema definitions for request/response bodies | Normative |
| **SPIFFE** | CNCF SPIFFE Specification v1.0 | Workload identity framework that inspired DCM's internal component identity model (ICOM); each DCM component has a stable UUID and certificate analogous to a SPIFFE ID; Istio/Envoy enforce SPIFFE-compatible workload identity | Informative |
| **Istio / Service Mesh** | Istio service mesh specification | Internal component mTLS enforcement; traffic policies; circuit breaking; observability; service-to-service authorization | Normative (distributed deployments) |

| **HashiCorp Vault PKI** | HashiCorp Vault PKI Secrets Engine | External CA credential management service backend (optional); issues x509 component certificates via native API or EST/ACME; recommended for fsi/sovereign profiles where enterprise PKI chain is required; typically operates as a subordinate CA of the organization root | Optional |
| **Venafi TLS Protect** | Venafi Platform | External CA credential management service backend (optional); enterprise certificate lifecycle management; ACME/EST/REST API integration | Optional |
| **EJBCA** | Enterprise JavaBeans Certificate Authority | External CA credential management service backend (optional); ACME/CMP/SCEP integration | Optional |

---

## 5. Compliance Frameworks

These frameworks drive specific DCM profiles, overlays, and policy constraints. DCM does not certify compliance — it provides the architectural primitives that enable compliant implementations.

### 5.1 US Federal and Defense

| Framework | Full Name | DCM Profile/Overlay | Key DCM Requirements |
|-----------|-----------|-------------------|---------------------|
| **NIST SP 800-53** | Security and Privacy Controls for Information Systems | `fedramp_moderate`, `fedramp_high` | Policy control families mapped to DCM policy domains; access control, audit, configuration management |
| **NIST SP 800-63B** | Digital Identity Guidelines | All profiles (AAL mapping) | AAL1 (minimal/dev), AAL2 (standard/prod), AAL2+ (fsi), AAL3 (sovereign); MFA requirements per level |
| **FedRAMP Moderate** | Federal Risk and Authorization Management Program — Moderate | `fedramp_moderate` overlay | NIST 800-53 Moderate baseline; FIPS 140-2 Level 1+; Federal data handling requirements |
| **FedRAMP High** | Federal Risk and Authorization Management Program — High | `fedramp_high` overlay | NIST 800-53 High baseline; FIPS 140-2 Level 2+; enhanced audit retention |
| **DoD IL4** | Department of Defense Impact Level 4 | `dod_il4` overlay | Controlled Unclassified Information; FIPS 140-2 Level 2; hardware attestation; enhanced logging |
| **FIPS 140-2/140-3** | Federal Information Processing Standard — Cryptographic Modules | fsi+ profiles | Cryptographic module validation; forbidden algorithm enforcement; key management requirements |

### 5.2 Industry Compliance

| Framework | Full Name | DCM Profile/Overlay | Key DCM Requirements |
|-----------|-----------|-------------------|---------------------|
| **PCI DSS** | Payment Card Industry Data Security Standard | `pci_dss` overlay | Req 8.3.9: P90D maximum credential rotation; network segmentation via sovereignty constraints; cardholder data access logging; 12-month audit retention |
| **HIPAA** | Health Insurance Portability and Accountability Act | `fsi` profile; `hipaa` overlay | PHI access logging; minimum necessary access (RBAC); audit controls; transmission security (TLS 1.2+); workforce authentication (MFA) |
| **SOC 2** | Service Organization Control 2 | `standard`+ profiles | Type II audit trail requirements; availability, security, confidentiality trust service criteria; change management via GitOps |
| **ISO 27001** | Information Security Management Systems | All profiles | Risk-based approach; asset management; access control; cryptography; operations security; incident management |

### 5.3 Data Protection / Sovereignty

| Framework | Full Name | DCM Feature | Key DCM Requirements |
|-----------|-----------|------------|---------------------|
| **GDPR** | General Data Protection Regulation (EU) | Sovereignty constraints; data classification | Data residency enforcement; right to erasure model (entity decommission + audit retention policy); data minimization via field-level classification; consent/purpose tracking via Governance Matrix |
| **Schrems II** | CJEU ruling on EU-US data transfers | Sovereignty constraints; federation boundaries | Data transfer restrictions between DCM federation peers; sovereign profile enforcement |

---

## 6. CNCF Ecosystem

DCM is designed for CNCF ecosystem compatibility. The following CNCF projects are referenced:

| Project | CNCF Status | DCM Use |
|---------|------------|---------|
| **Kubernetes** | Graduated | Deployment target; CRD-based DCM Operator; resource model inspiration |
| **Open Policy Agent (OPA)** | Graduated | Policy engine backend option; Rego policies for DCM GateKeeper and Validation policy types |
| **Prometheus** | Graduated | Metrics exposition format; DCM scrape endpoint |
| **OpenTelemetry** | Graduated | Distributed tracing; correlation ID propagation |
| **Istio** | Graduated | Service mesh for internal mTLS; traffic policies |
| **Argo CD / Flux** | Graduated | GitOps delivery for DCM layer definitions and policy artifacts |

---

## 7. Authentication Assurance Levels (NIST SP 800-63B)

DCM maps profile security postures to NIST Authentication Assurance Levels:

| Profile | AAL | Requirements |
|---------|-----|-------------|
| `minimal` | AAL1 | Single-factor authentication acceptable; password or API key |
| `dev` | AAL1 | Single-factor authentication acceptable |
| `standard` | AAL2 | MFA required for all actor sessions; phishing-resistant preferred |
| `prod` | AAL2 | MFA required; TOTP, FIDO2, or hardware token |
| `fsi` | AAL2+ | MFA required; phishing-resistant authenticator (FIDO2/hardware token) |
| `sovereign` | AAL3 | Hardware-based authenticator required; verifier impersonation resistance; physical authenticator possession |

---

## 8. Standard Usage Map — Where Each Standard Appears

| Standard | Documents |
|----------|----------|
| RFC 7519 (JWT) | 19-auth-providers, 35-session-revocation, consumer-api-spec |
| RFC 7517 (JWK) | 19-auth-providers |
| RFC 7662 (Token Introspection) | 35-session-revocation, consumer-api-spec |
| RFC 7643/7644 (SCIM 2.0) | 19-auth-providers |
| RFC 8446 (TLS 1.3) | 14-policy-profiles, 26-accreditation, 31-credential-provider, 36-internal-component-auth |
| RFC 5280 (X.509/CRL) | 31-credential-provider, 36-internal-component-auth |
| RFC 6960 (OCSP) | 36-internal-component-auth |
| RFC 7030 (EST) | 31-credential-provider |
| RFC 8555 (ACME) | 31-credential-provider |
| RFC 8894 (SCEP) | 31-credential-provider |
| RFC 4210 (CMP) | 31-credential-provider |
| RFC 8594 (Sunset) | 34-api-versioning-strategy, consumer-api-spec |
| RFC 9745 (Deprecation) | 34-api-versioning-strategy, consumer-api-spec |
| RFC 8615 (Well-Known URIs) | 34-api-versioning-strategy, 39-dcm-self-health, dcm-operator-interface-spec |
| RFC 8259 (JSON) | All specifications |
| ISO 8601 (timestamps) | All documents |
| OIDC / OpenID Connect | 19-auth-providers, consumer-api-spec |
| LDAP (RFC 4511) | 19-auth-providers |
| FIPS 140 | 14-policy-profiles, 31-credential-provider, 36-internal-component-auth |
| NIST SP 800-63B (AAL) | 31-credential-provider |
| NIST SP 800-53 | 14-policy-profiles |
| HIPAA | 14-policy-profiles, 31-credential-provider |
| PCI DSS | 14-policy-profiles, 31-credential-provider |
| FedRAMP | 14-policy-profiles |
| GDPR | 08-resource-grouping, 22-dcm-federation |
| ISO 27001 | 14-policy-profiles, 26-accreditation |
| Kubernetes | kubernetes-compatibility, dcm-operator-sdk-api |
| OPA | dcm-opa-integration-spec |
| Prometheus | 12-audit-provenance, 39-dcm-self-health |
| OpenTelemetry | 12-audit-provenance |
| Istio | 17-deployment-redundancy, 36-internal-component-auth |
| GitOps/OpenGitOps | 00-context-and-purpose, 20-registry-governance, 28-federated-contribution |
| W3C SSE (Server-Sent Events) | consumer-api-spec, 39-dcm-self-health |
| OpenAPI 3.1 | dcm-operator-interface-spec, consumer-api-spec, dcm-admin-api-spec |
| SPIFFE (conceptual) | 36-internal-component-auth |
| HashiCorp Vault PKI | 31-credential-provider-model, 36-internal-component-auth |
| RFC 7009 (Token Revocation) | 35-session-revocation |
| NIST SP 800-63B (AAL) | 31-credential-provider-model, 14-policy-profiles |
| SCH policies (scheduling) | 37-scheduled-requests |
| RDG policies (dependency graph) | 38-request-dependency-graph |
| HLT policies (self-health) | 39-dcm-self-health |
| SES policies (session revocation) | 35-session-revocation |
| ICOM policies (internal component auth) | 36-internal-component-auth |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

---

## 10. ITSM Integration Standards

These standards and protocols are used by ITSM integration implementations:

| Standard / Protocol | Use in DCM ITSM Integration | Obligation |
|--------------------|-----------------------------|------------|
| **ServiceNow REST Table API** | Primary integration for ServiceNow; create/read/update change_request, incident, cmdb_ci tables | Normative for ServiceNow provider |
| **Jira REST API v3** | Primary integration for Jira Service Management; issue create/update/transition | Normative for Jira provider |
| **BMC AR REST API v1** | Integration for BMC Remedy/Helix ITSM; form-based create/update | Normative for BMC provider |
| **PagerDuty Events API v2** | Incident creation and update for alert-type integrations | Normative for PagerDuty provider |
| **HMAC-SHA256** | Inbound webhook signature verification for all ITSM systems; shared secret via credential management service | Normative |
| **ITIL v4 Change Management** | Conceptual framework for DCM change record lifecycle mapping (Normal, Standard, Emergency change types) | Informative |
| **JSON:API** | Used by several ITSM REST APIs for response formatting | Informative |
| **JSONPath** | Template expression resolution for `generic_rest` action payloads; response field extraction | Normative for generic_rest |

## 9. Policy Family to Standard Mapping

Each DCM system policy family maps to one or more industry standards. This table supports compliance traceability.

| Policy Family | Standards Basis | Key Policies |
|--------------|----------------|-------------|
| **AUTH-001–015** | RFC 6749, RFC 7519, OIDC Core, NIST SP 800-63B, RFC 7643/7644 | Auth Provider lifecycle; session TTL; MFA enforcement; SCIM provisioning |
| **AUTH-016–022** | RFC 7662, RFC 6749 spirit, OAuth 2.0 best practices | Session revocation; token introspection; refresh token invalidation |
| **CPX-001–012** | FIPS 140-2/3, RFC 5280, RFC 8555/7030/8894/4210, NIST SP 800-57 | Credential never stored; rotation; revocation; algorithm baseline |
| **ATM-001–012** | ISO 27001 change management; organizational governance practices | Authority tier ordering; security degradation gate; profile gap detection |
| **EVT-001–007** | OpenTelemetry, CNCF event-driven best practices | Event envelope; idempotency; non-suppressable audit events |
| **VER-001–009** | RFC 8594, RFC 9745, industry API lifecycle practices | Breaking change definition; deprecation headers; migration guides |
| **SES-001–005** | RFC 7662, RFC 7009, OAuth 2.0 security best practices | Session lifecycle; concurrent limits; emergency revocation |
| **ICOM-001–009** | RFC 8446, RFC 5280, SPIFFE conceptual model, FIPS 140 | mTLS; component identity; Internal CA; bootstrap; certificate revocation |
| **SCH-001–006** | Industry job scheduling practices; dual-evaluation pattern | Scheduled request dual policy evaluation; deadline enforcement |
| **RDG-001–006** | DAG-based workflow ordering; dependency injection patterns | Circular dependency rejection; quota at group submission; field injection |
| **HLT-001–006** | RFC 8615, Kubernetes probe conventions, Prometheus OpenMetrics | Liveness/readiness; unauthenticated probes; profile-governed metrics exposure |
| **DPO-001–006** | Design-by-contract; security-first architecture principles | Design priority order; security as Priority 1 |
| **ZTS-001–005** | Zero Trust Architecture (NIST SP 800-207); NIST SP 800-63B | Five-check boundary model; mTLS; scoped interaction credentials |
| **CMP-001–008** | Service mesh composition patterns; dependency graph execution | Composite Service constituent dispatch; compensation |
| **SMX-001–010** | Risk scoring; NIST RMF; organizational risk tolerance | Hybrid scoring; approval routing; enforcement class |
| **FCM-001–008** | GitOps contribution model; CNCF governance practices | Federated policy contribution; shadow validation; trust levels |
| **GMX-001–006** | Governance Matrix; policy-as-code; organizational controls | Cross-domain policy enforcement; data classification |
| **ITSM-001–007 + ITSM-POL-001–004** | ITIL v4, ServiceNow/Jira/Remedy REST APIs, HMAC-SHA256, ITIL change management | ITSM integration registration; inbound webhook auth; ITSM Policy evaluation; blocking gate with timeout guarantee |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*