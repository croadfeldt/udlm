# DCM Data Model — Infrastructure Requirements and Provider Types

**Document Status:** 📋 Draft — Ready for Review
**Document Type:** Architecture Specification — Infrastructure dependencies, provider type definitions, policy evaluation modes, control plane service inventory
**Related Documents:** [Foundational Abstractions](00-foundations.md) | [Four States](02-four-states.md) | [Provider Contract](A-provider-contract.md) | [Implementation Specifications](49-implementation-specifications.md)

---

## 1. Design Principle

DCM prescribes **data contracts** (schemas, immutability rules, versioning, hash chains) — not infrastructure products. Where a contract maps directly to a single well-understood infrastructure category, DCM prescribes the category and the contract, not an abstraction layer over it.

Abstraction layers earn their place when the underlying implementations have genuinely different interaction contracts — different APIs, different lifecycle semantics, different operational models. When the implementations share a standard protocol (SQL, OIDC, AMQP), the protocol is the abstraction. Adding a DCM-specific abstraction on top of a standard protocol is unnecessary indirection.

---

## 2. Four Data Domains, One Required Store

DCM tracks every resource through four lifecycle stages. These remain architecturally distinct — they represent different things, have different immutability rules, and serve different query patterns. But they do not require separate infrastructure.

### 2.1 The Four Data Domains

| Domain | What it represents | Immutability | Primary consumers |
|--------|-------------------|-------------|-------------------|
| **Intent** | What the consumer asked for — raw declaration before processing | Append-only. A new intent version creates a new record. Previous intents are never modified. | Audit, portability (re-process intent through new policies), request history |
| **Requested** | What was approved and dispatched — assembled, policy-validated, placed | Append-only. Each policy evaluation produces a new version. Complete provenance chain. | Provider dispatch, audit, rollback comparison |
| **Realized** | What the provider actually built — confirmed state with provider metadata | Append-only versioned. Each state change creates a new snapshot. `is_current` flag for latest. | Operational queries, drift comparison baseline, inventory |
| **Discovered** | What actually exists right now — independently observed by discovery | Ephemeral. Each discovery run produces a fresh snapshot. Previous snapshots retained for trend analysis. | Drift detection (compare against Realized), capacity planning |

### 2.2 Single Required Infrastructure

All four domains live in **PostgreSQL** (or any PostgreSQL-compatible database: CockroachDB, Aurora PostgreSQL, Crunchy Postgres). The data contracts are enforced by:

- **Append-only tables** with `REVOKE UPDATE, DELETE` for Intent, Requested, and Audit records
- **Row versioning** with `version_major.minor.revision` and `is_current` flag on Realized records
- **SHA-256 hash chain** on Audit records for tamper evidence
- **RLS (Row-Level Security)** for tenant isolation (STI-001, STI-002)
- **`LISTEN/NOTIFY`** for event-driven pipeline routing between control plane services
- **Materialized views** for cached read-heavy queries (catalog browsing, placement lookups)

### 2.3 Schema Design

```sql
-- ── Intent Domain ──────────────────────────────────────────────────────
-- Append-only. Raw consumer declarations. Never modified after write.

CREATE TABLE intent_records (
    intent_uuid         UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_uuid         UUID NOT NULL,              -- Stable entity identity
    tenant_uuid         UUID NOT NULL REFERENCES tenants(tenant_uuid),
    catalog_item_uuid   UUID NOT NULL,
    submitted_by        UUID NOT NULL,              -- Actor who submitted
    submitted_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    submitted_via       VARCHAR(32) NOT NULL         -- api | gitops | cli | message_bus
                            CHECK (submitted_via IN ('api', 'gitops', 'cli', 'message_bus')),
    intent_version      INTEGER NOT NULL DEFAULT 1,  -- Increments on resubmission
    fields              JSONB NOT NULL DEFAULT '{}', -- Consumer's raw field values
    provenance          JSONB NOT NULL DEFAULT '{}'  -- Ingress context
);

CREATE INDEX idx_intent_entity ON intent_records(entity_uuid, intent_version);
CREATE INDEX idx_intent_tenant ON intent_records(tenant_uuid, submitted_at);

REVOKE UPDATE, DELETE ON intent_records FROM dcm_app;

-- ── Requested Domain ───────────────────────────────────────────────────
-- Append-only. Assembled, policy-evaluated, placed payloads.

CREATE TABLE requested_records (
    requested_uuid      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_uuid         UUID NOT NULL,
    tenant_uuid         UUID NOT NULL REFERENCES tenants(tenant_uuid),
    operation_uuid      UUID NOT NULL REFERENCES operations(operation_uuid),
    intent_uuid         UUID NOT NULL REFERENCES intent_records(intent_uuid),
    resource_type       VARCHAR(256) NOT NULL,
    provider_uuid       UUID NOT NULL,              -- Selected provider
    assembled_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    assembled_payload   JSONB NOT NULL DEFAULT '{}', -- Full merged payload
    layer_sources       JSONB NOT NULL DEFAULT '[]', -- Which layers contributed
    policy_results      JSONB NOT NULL DEFAULT '{}', -- Policy evaluation outcomes
    placement_result    JSONB NOT NULL DEFAULT '{}', -- Placement decision + score
    provenance          JSONB NOT NULL DEFAULT '{}'  -- Field-level provenance
);

CREATE INDEX idx_requested_entity ON requested_records(entity_uuid);
CREATE INDEX idx_requested_tenant ON requested_records(tenant_uuid);
CREATE INDEX idx_requested_operation ON requested_records(operation_uuid);

REVOKE UPDATE, DELETE ON requested_records FROM dcm_app;

-- ── Realized Domain ────────────────────────────────────────────────────
-- (Existing realized_entities table from 001-initial.sql — unchanged)
-- Versioned rows, is_current flag, append-on-change semantics.

-- ── Discovered Domain ──────────────────────────────────────────────────
-- Ephemeral snapshots from provider discovery runs.

CREATE TABLE discovered_records (
    discovery_uuid      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_uuid         UUID,                       -- Matched entity (null if orphan)
    tenant_uuid         UUID REFERENCES tenants(tenant_uuid),
    provider_uuid       UUID NOT NULL,
    resource_type       VARCHAR(256) NOT NULL,
    discovered_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    discovery_run_uuid  UUID NOT NULL,              -- Groups records from same run
    discovered_fields   JSONB NOT NULL DEFAULT '{}', -- What the provider reported
    provider_native_id  VARCHAR(512),               -- Provider's identifier
    match_confidence    VARCHAR(16) DEFAULT 'exact'
                            CHECK (match_confidence IN ('exact', 'high', 'low', 'unmatched'))
);

CREATE INDEX idx_discovered_entity ON discovered_records(entity_uuid, discovered_at);
CREATE INDEX idx_discovered_run ON discovered_records(discovery_run_uuid);
CREATE INDEX idx_discovered_orphans ON discovered_records(entity_uuid) WHERE entity_uuid IS NULL;

-- ── Pipeline Events ────────────────────────────────────────────────────
-- Append-only event log. Replaces Kafka for pipeline routing in standard deployments.
-- LISTEN/NOTIFY provides real-time notification to pipeline consumers.

CREATE TABLE pipeline_events (
    event_uuid          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type          VARCHAR(128) NOT NULL,
    entity_uuid         UUID,
    request_uuid        UUID,
    tenant_uuid         UUID,
    actor_uuid          UUID,
    payload             JSONB NOT NULL DEFAULT '{}',
    published_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    consumed_by         JSONB NOT NULL DEFAULT '[]',  -- Track which services consumed
    consumed_at         TIMESTAMPTZ
);

CREATE INDEX idx_events_type ON pipeline_events(event_type, published_at);
CREATE INDEX idx_events_entity ON pipeline_events(entity_uuid, published_at);
CREATE INDEX idx_events_unconsumed ON pipeline_events(event_type, published_at) 
    WHERE consumed_at IS NULL;

REVOKE UPDATE, DELETE ON pipeline_events FROM dcm_app;

-- Notify function for real-time pipeline routing
CREATE OR REPLACE FUNCTION notify_pipeline_event() RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('dcm_pipeline', json_build_object(
        'event_uuid', NEW.event_uuid,
        'event_type', NEW.event_type,
        'entity_uuid', NEW.entity_uuid
    )::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pipeline_event_notify
    AFTER INSERT ON pipeline_events
    FOR EACH ROW EXECUTE FUNCTION notify_pipeline_event();

-- RLS on all new tables
ALTER TABLE intent_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE requested_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovered_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE pipeline_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_intent ON intent_records
    FOR ALL TO dcm_app
    USING (tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid);
CREATE POLICY tenant_isolation_requested ON requested_records
    FOR ALL TO dcm_app
    USING (tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid);
CREATE POLICY tenant_isolation_discovered ON discovered_records
    FOR ALL TO dcm_app
    USING (tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid);
CREATE POLICY tenant_isolation_events ON pipeline_events
    FOR SELECT TO dcm_app
    USING (tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid);
```

### 2.4 Why Not Separate Stores

| Concern | Four-store answer | Single-store answer |
|---------|------------------|-------------------|
| Immutability | Git commits are immutable | Append-only tables + REVOKE UPDATE, DELETE + audit trigger |
| Version history | Git log | Row versioning with semantic version fields |
| Audit trail | Git commit metadata | SHA-256 hash chain (stronger — explicit cryptographic chain vs Git's graph integrity) |
| PR-based review | Native Git workflow | DCM's Policy Engine + Scoring Model + Authority Tier routing (more sophisticated) |
| Tamper evidence | Git SHA integrity | Hash chain with `previous_record_hash` per entity (per-record, not per-repo) |
| Transactional consistency | Cross-store sync required | Native — intent + audit + operation in same transaction |
| Sovereignty partitioning | Separate Git/Kafka/Redis per zone | Separate PostgreSQL instance per zone (one thing to deploy, not four) |
| Air-gapped deployment | Git + Kafka + Redis + PostgreSQL (4 infra dependencies) | PostgreSQL only (1 dependency) |
| Operations skill set | Git admin + Kafka admin + Redis admin + DBA | DBA only |

---

## 3. Provider Types

### 3.1 Design Principle

A provider **type** is justified when the provider's **interaction contract** — the operations it supports, the lifecycle it follows, the data it exchanges — is fundamentally different from other types. If two "types" follow the same create/update/decommission/discover contract and differ only in what resource types they handle, they're the same type with different capabilities.

### 3.2 Provider Types (6)

| Type | Contract distinction | Examples |
|------|---------------------|----------|
| `service_provider` | Full lifecycle CRUD on resources — create, update, decommission, discover. Naturalization/denaturalization of payloads. Capacity reporting. Health events. | KubeVirt (VMs), NSX (networks), Vault (credentials), SMTP (notifications), ACM (clusters) |
| `information_provider` | Read-only data queries. No create/decommission. Authority levels, confidence models, scheduled/pushed/on-demand retrieval modes. | CMDB, LDAP directory, compliance scanner, cost data feed |

| `auth_provider` | Authentication and identity services. Provides actor authentication, token issuance, group/role claims, MFA capabilities. Multiple auth providers can be registered — tenant routing determines which provider authenticates a given actor. | Keycloak, Okta, Azure AD, LDAP + Dex, SAML IdP |
| `peer_dcm` | DCM-to-DCM federation protocol. Entity migration, cross-instance placement, distributed governance. | Regional DCM instances, sovereign DCM peers |
| `process_provider` | Executes ephemeral workflows to completion. No persistent resources — produces a result and terminates. May orchestrate external automation (AAP, Tekton). | Software install, backup execution, migration job, compliance scan |

### 3.3 Design Rationale — Why These Are Not Provider Types

Some infrastructure categories that might seem like provider types are intentionally excluded because they lack a genuinely different interaction contract, or because they are internal infrastructure that DCM consumes rather than manages.

| Category | Classification | Rationale |
|----------|---------------|-----------|
| Database (PostgreSQL) | **Prescribed infrastructure** | DCM's database is internal infrastructure, not a registered provider. DCM doesn't manage the DB's lifecycle; the DB stores DCM's data. |
| Event streaming (Kafka) | **Optional infrastructure** | Kafka is a deployment enhancement, not a registered provider. `LISTEN/NOTIFY` handles pipeline routing in standard deployments. |
| Resource Type Registry | **Internal component** | The Resource Type Registry is an internal function of the control plane, not an external provider. |
| Policy evaluation engine | **Policy Manager capability** | External policy evaluation is a mode of the Policy Manager (see Section 3.4), not a separate provider type. |
| Credential management (Vault) | **Service provider** | Vault is a service_provider that handles `Credential.*` resource types. Same contract — create, retrieve, rotate (update), revoke (decommission). HSM support and rotation protocols are capability declarations, not a different contract. |
| Notification delivery | **Service provider** | Email/Slack/webhook delivery is a service_provider that handles `Notification.*` resource types. Same contract. |

### 3.4 Policy Evaluation Modes

DCM supports two policy evaluation modes. The distinction is whether DCM or an external system performs the evaluation — not how policies are delivered to the evaluator.

**Two modes:**

| Mode | Name | How it works | Examples |
|------|------|-------------|----------|
| **Internal** | DCM evaluates | Policies arrive through any delivery mechanism (API, GitOps, OPA bundle server, external schema with naturalization). DCM's Policy Manager evaluates all of them via OPA. Where OPA runs (embedded, sidecar, remote instance) is a deployment topology decision, not a mode. | Rego policies in DCM database; OPA bundle from bundle server; non-Rego policies translated to Rego by DCM |
| **External** | External provider evaluates | DCM sends evaluation context to an external endpoint. External system returns structured results (pass/fail, score, enrichment fields). DCM does not see the policy logic — it trusts the results within scoped bounds. | Enterprise compliance engine; SaaS policy platform; organization-specific evaluation service |

**Internal mode delivery mechanisms** (all equivalent — same evaluation, different transport):

| Delivery | `delivery.mode` value | Description |
|----------|----------------------|-------------|
| API push/pull | `push` / `pull` / `webhook` | Policies stored in DCM's database, managed via API or GitOps adapter |
| OPA bundle | `opa_bundle` | Standard OPA bundle protocol — point OPA at a bundle server |
| External schema | `external_schema` | Policy in non-Rego format (e.g., XACML, custom JSON), DCM naturalizes to Rego before evaluation |

**External mode governance** (BBQ-001 through BBQ-009 — unchanged):
- Data sovereignty check before any query is sent
- Data minimization — only declared fields sent
- Full audit record per query-response cycle
- Default failure behavior is `gatekeep` — unknown is not safe
- Enrichment fields carry provenance with `source_type: external_external_policy_evaluator`
- External evaluation requires minimum `verified` trust level; GateKeeper authority requires `trusted`

### 3.5 Resource Type Categories as Capability Declarations

What the former provider types expressed — "this provider handles credentials" — is now expressed by the resource types a `service_provider` declares in its `supported_resource_types`:

```yaml
# Vault registers as a service_provider that handles credential resources
provider:
  provider_type: service_provider
  supported_resource_types:
    - "Credential.Secret"
    - "Credential.Certificate"
    - "Credential.SSHKey"
  capability_extension:
    hsm_support: true
    rotation_protocol: automatic
    max_secret_size_bytes: 65536

# SMTP gateway registers as a service_provider that handles notifications
provider:
  provider_type: service_provider
  supported_resource_types:
    - "Notification.Email"
    - "Notification.Webhook"
  capability_extension:
    delivery_guarantee: at_least_once
    sovereignty_aware_routing: true
```

---

## 4. Prescribed Infrastructure Requirements

Instead of provider registrations for infrastructure, DCM prescribes infrastructure categories with specific contracts:

### 4.1 Required Infrastructure

| Infrastructure | Contract | Examples |
|---------------|----------|----------|
| **PostgreSQL-compatible database** | SQL, RLS, `LISTEN/NOTIFY`, JSONB, triggers, append-only tables, `pgcrypto` for envelope encryption. Schema defined by DCM. Includes the `secrets` table for internal secrets management and the `actors` table for internal authentication. | PostgreSQL, CockroachDB, Aurora PostgreSQL, Crunchy Postgres |

PostgreSQL is the only required external infrastructure. All other dependencies — identity, secrets, event streaming, caching, Git ingress — can either be handled internally by DCM or optionally delegated to external systems.

### 4.2 Authentication — Internal and External

DCM manages authentication using the same Internal/External pattern as policy evaluation and secrets management.

**Internal mode (default):** Local user accounts stored in the `actors` table. Passwords stored as argon2id hashes. DCM issues its own JWT session tokens with configurable expiry. For a homelab deployment, you create a local admin account via the bootstrap CLI and you're done.

**External mode (optional):** Organizations with existing identity infrastructure register `auth_provider` instances. DCM validates their tokens, extracts claims, and maps groups to DCM roles. OIDC, SAML, LDAP — whatever the auth_provider supports. Multiple auth_providers enable tenant-routed authentication (Tenant A through AD, Tenant B through Okta). External auth_providers are registered via the standard provider registration contract.

| Feature | Internal | External (auth_provider) |
|---------|----------|--------------------------|
| User management | `actors` table — local accounts | External IdP manages users |
| Authentication | Password → argon2id hash → DCM-issued JWT | External token → DCM validates → extracts claims |
| MFA | TOTP (optional) | Delegated to IdP |
| Group/role mapping | Direct role assignment in `actors` table | JWT group claims mapped to DCM roles |
| Session management | `sessions` table with configurable TTL | Token lifetime governed by IdP + DCM validation |
| Federation | N/A (single instance) | Multiple auth_providers, tenant routing |

### 4.3 Secrets Management — Internal and External

DCM manages secrets using the same Internal/External pattern as policy evaluation.

**Internal mode (default):** Secrets are stored in DCM's PostgreSQL database in a `secrets` table using envelope encryption. Each secret value is encrypted with AES-256-GCM using a data encryption key (DEK). DEKs are encrypted with a master key (KEK) sourced from the deployment environment:

| KEK Source | Deployment | Security Level |
|------------|-----------|----------------|
| Environment variable | Homelab, dev | Basic — protects against database theft, not host compromise |
| Kubernetes Secret | Standard | Good — Kubernetes RBAC protects the KEK; etcd encryption at rest protects storage |
| HSM via PKCS#11 | Sovereign | Strong — KEK never leaves the hardware security module |

Internal mode requires no external secrets infrastructure. The `secrets` table has the same RLS, append-only audit, and tenant isolation as every other DCM table.

**External mode (optional):** Organizations with existing secrets infrastructure register a Vault-compatible API endpoint. DCM calls the Vault HTTP API for all secret operations. Vault, OpenBao, or any API-compatible implementation works. This is an optional deployment enhancement — not a required component.

| Feature | Internal | External (Vault) |
|---------|----------|------------------|
| Secret CRUD | PostgreSQL `secrets` table | Vault KV engine |
| PKI certificates | cert-manager / service mesh | Vault PKI engine |
| Dynamic DB credentials | Static credentials + rotation | Vault database engine |
| Transit encryption | `pgcrypto` AES-256-GCM | Vault transit engine |
| HSM backing | PKCS#11 for KEK only | Full HSM seal + transit |

### 4.4 Optional Infrastructure (Deployment Enhancements)

| Infrastructure | When to add | What it provides |
|---------------|------------|-----------------|
| **OIDC-compatible identity provider** | Organizations with existing identity infrastructure. Multi-tenant deployments requiring federated authentication across different IdPs. | External authentication — replaces internal PostgreSQL-based user management. Registered as `auth_provider`. |
| **Vault-compatible secrets management** | Organizations with existing Vault infrastructure. Deployments requiring dynamic database credentials, PKI certificate issuance, or full HSM-backed transit encryption. | External secrets backend — replaces internal PostgreSQL-based secrets management. |
| **Kafka-compatible event stream** | High-throughput deployments (>1000 events/sec). Multiple consumer groups needing independent replay. | Replaces `pipeline_events` table + `LISTEN/NOTIFY` for event routing. |
| **Redis-compatible cache** | Read-heavy catalog/placement workloads. Geographically distributed read replicas. | Replaces materialized views in PostgreSQL. |
| **Git repository** | CI/CD pipeline integration. Teams that want PR-based request ingress. | Adds Git as an ingress path alongside API/CLI. |
| **Service mesh** | Production deployments requiring mTLS between control plane services. | Replaces application-level TLS configuration. |

### 4.5 Deployment Profiles

| Profile | Required | Optional |
|---------|----------|----------|
| **Minimal** (homelab/dev) | PostgreSQL (single instance) | — |
| **Standard** (production) | PostgreSQL (HA) | Keycloak, Vault, Service mesh, Redis |
| **Enterprise** (large scale) | PostgreSQL (HA + read replicas) | Keycloak (HA), Vault (HA + HSM), Service mesh, Kafka, Redis, Git |
| **Sovereign** (air-gapped) | PostgreSQL (per-zone) | Keycloak (per-zone), Vault (per-zone + HSM seal), Service mesh |

---

## 5. Control Plane Services

### 5.1 Design Principle

A component is a separately deployable service when it has an independent scaling profile, a distinct failure domain, or a genuinely separate operational responsibility. Functions that share a scaling profile and failure domain with their host service are not separate deployments — they are internal modules.

### 5.2 Deployable Services (9)

| Service | Responsibility | Absorbs |
|---------|---------------|---------|
| **API Gateway** (Traefik) | Ingress routing, JWT validation, `X-DCM-Tenant` injection, `X-Request-ID` generation, rate limiting | — |
| **Catalog Manager** | Catalog CRUD — ServiceType, CatalogItem, subscription tiers. Consumer browsing. | — |
| **Service Provider Manager** | Provider registration, status lifecycle, capability tracking, health monitoring | — |
| **Policy Manager** | Policy artifact CRUD, OPA-backed evaluation, scoring | `scoring_engine` (scoring is a function of policy evaluation, not a separate service) |
| **Placement Manager** | Provider selection via specificity narrowing, capacity-aware placement | — |
| **Request Orchestrator** | Pipeline routing — consumes events, dispatches to stage services, manages pipeline state | `lifecycle_enforcer` (lifecycle events are pipeline events), `notification_router` (notifications are pipeline side-effects), `request_scheduler` (scheduling is a pipeline function) |
| **Request Processor** | Layer assembly — merges core/service/consumer layers into assembled payload | — |
| **Audit Service** | Append-only audit records, hash chain integrity, audit queries, chain verification | — |
| **Discovery Service** | Scheduled provider discovery, drift detection, orphan identification | `drift_reconciler` (drift is a discovery output), `discovery_scheduler` (scheduling is internal) |

### 5.3 Internal Functions (Not Separate Services)

These are functions within the services above — not independently deployed components.

| Function | Lives in | Rationale |
|-----------------|--------------|-----------|
| `scoring_engine` | Policy Manager | Scoring is the output of policy evaluation. Same request, same data, same transaction. No independent scaling need. |
| `lifecycle_enforcer` | Request Orchestrator | Lifecycle events (TTL expiry, state transitions) enter the same pipeline as any other event. The orchestrator routes them to policy evaluation. No separate service needed. |
| `notification_router` | Request Orchestrator | Notifications are pipeline side-effects. When the orchestrator completes a pipeline stage, it emits notification events. A `service_provider` for `Notification.*` resources handles delivery. |
| `session_store` | PostgreSQL table | Sessions are rows in a `sessions` table. JWT is stateless. Revocation is a status update. No separate infrastructure. |
| `service_provider_proxy` | Standard service_provider call | Credential retrieval is a standard API call to whichever service_provider handles `Credential.*` resource types. No proxy needed. |
| `drift_reconciler` | Discovery Service | Drift detection is the primary function of discovery. Compare Discovered vs Realized, produce drift records. Same data, same service. |
| `request_scheduler` | Request Orchestrator | Scheduled requests are cron entries that produce pipeline events. The orchestrator's scheduler emits events at the scheduled time. |
| `discovery_scheduler` | Discovery Service | Same pattern — built-in scheduler. |
| `internal_ca` | Service mesh | mTLS between control plane services is a service mesh responsibility (Istio/OpenShift Service Mesh), not a DCM component. |
| `message_bus` | `pipeline_events` table + `LISTEN/NOTIFY` | Standard deployments use PostgreSQL for event routing. Kafka added as enhancement for high-throughput. |

### 5.4 Service Interaction Model (Simplified)

```
Consumer → API Gateway → Catalog Manager (browse)
                       → Request Orchestrator (submit) → pipeline_events table
                                                            │
                           LISTEN/NOTIFY triggers:          │
                           ┌────────────────────────────────┘
                           ▼
                    Request Processor (assemble)
                           ▼
                    Policy Manager (evaluate + score)
                           ▼
                    Placement Manager (select provider)
                           ▼
                    Request Orchestrator (dispatch to provider)
                           ▼
                    Service Provider (realize)
                           ▼
                    Request Orchestrator (write Realized, emit events)
                           ▼
                    Audit Service (append audit record)

Discovery Service runs on schedule:
    → Calls each registered service_provider's discover endpoint
    → Compares against Realized domain
    → Writes drift records
    → Emits drift events → Policy Manager evaluates → actions
```

---

## 6. Git as Ingress Adapter

Git remains a valid and valuable ingress mechanism. But it is an ingress adapter — not a state store.

### 6.1 How Git Ingress Works

```
Developer writes intent YAML → commits to Git repo → PR reviewed and merged
    │
    ▼
GitOps Adapter (watches repo or triggered by CI/CD webhook)
    │
    ▼
POST /api/v1/requests (same API as any other consumer)
    │
    ▼
Standard pipeline: Intent → Assemble → Evaluate → Place → Dispatch → Realize
```

The GitOps Adapter is a lightweight service that:
1. Watches a Git repository for merged PRs (or receives CI/CD webhooks)
2. Parses intent YAML from the commit
3. Submits it to the DCM API as a standard request with `submitted_via: gitops`
4. The request enters the same pipeline as an API-submitted request

The Git repository is the consumer's workspace — not DCM's state store. DCM's state lives in PostgreSQL. The Git repo provides the PR-based review workflow that some teams prefer, but the actual approval authority is DCM's Policy Engine.

### 6.2 What the Git Repo Contains

```
dcm-intents/
├── {tenant-handle}/
│   ├── {resource-type}/
│   │   ├── {entity-handle}/
│   │   │   └── intent.yaml        ← Consumer's declaration
│   │   └── ...
│   └── ...
└── ...
```

This is a consumer convenience — a structured workspace for declaring intent. It is not the source of truth for DCM state.

---

## 7. Design Summary

| Aspect | Specification |
|--------|--------------|
| Required infrastructure | PostgreSQL-compatible DB |
| Internal capabilities | Authentication (local accounts + JWT), secrets (envelope encryption), event routing (`LISTEN/NOTIFY`) |
| Optional infrastructure | OIDC IdP (external auth), Vault (external secrets), Kafka (event streaming), Redis (caching), Git (ingress), Service mesh (mTLS) |
| Provider types | 5: `service_provider`, `information_provider`, `auth_provider`, `peer_dcm`, `process_provider` |
| Policy evaluation modes | 2: Internal (DCM evaluates via OPA, any delivery mechanism) and External (external provider evaluates) |
| Control plane services | 9 deployable services |
| Data domains | 4 logical domains (Intent, Requested, Realized, Discovered) in 1 database |
| Minimum deployment | 1 infrastructure component (PostgreSQL) + control plane services |
| Sovereign deployment | PostgreSQL per sovereignty zone (+ Keycloak, Vault optional) |

### 7.1 Architectural Invariants

These properties hold regardless of deployment profile or infrastructure choices:

- **Four data domains** — Intent, Requested, Realized, Discovered remain architecturally distinct
- **Append-only immutability** on Intent, Requested, and Audit records
- **SHA-256 hash chain** on audit records
- **RLS tenant isolation** (STI-001, STI-002)
- **Provider Contract** — registration, health, capability, sovereignty, naturalization/denaturalization
- **Policy Engine** — 8 policy types, OPA/Rego, scoring model
- **AEP compliance** on all APIs
- **331 capabilities** across 39 domains
- **101 event payloads** across 22 domains

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
