# DCM Data Model — Data Store Contracts

**Document Status:** ✅ Complete
**Document Type:** Architecture Specification — Enforcement rules for the four data domains
**Related Documents:** [Four States](02-four-states.md) | [Universal Audit](16-universal-audit.md) | [Infrastructure Requirements](51-infrastructure-optimization.md)

> **Foundation Document Reference**
>
> This document specifies the enforcement contracts for DCM's four data domains.
> All four domains are stored in a single PostgreSQL-compatible database.
> See [51-infrastructure-optimization.md](51-infrastructure-optimization.md) for the
> infrastructure requirements and deployment profiles.
>
> **This document maps to: DATA**

---

## 1. Purpose

DCM's data integrity guarantees are enforced at the database level, not the application level. Application code may have bugs; the database enforces the invariants regardless. This document specifies the contracts that the database must satisfy for each data domain.

These contracts are implemented via PostgreSQL-native mechanisms: `REVOKE` grants, Row-Level Security (RLS), triggers, CHECK constraints, and append-only table design. The canonical SQL schema implementing these contracts is in `schemas/sql/001-initial.sql`.

---

## 2. Data Domain Contracts

### 2.1 Intent Domain (`intent_records`)

The Intent domain stores consumer declarations exactly as submitted — before any processing, enrichment, or policy application.

**Contract:**
- **Append-only** — rows are never updated or deleted. `REVOKE UPDATE, DELETE ON intent_records FROM dcm_app`.
- **Versioned** — resubmissions create new rows with incrementing `intent_version`. Previous versions are preserved.
- **Immutable fields** — `intent_uuid`, `entity_uuid`, `tenant_uuid`, `submitted_by`, `submitted_at`, `submitted_via` are set on insert and never change.
- **Ingress tracking** — `submitted_via` records the ingress path (`api`, `gitops`, `cli`, `message_bus`).
- **Tenant-isolated** — RLS ensures `dcm_app` can only read/write intents belonging to the current tenant (`SET dcm.current_tenant_uuid`).

### 2.2 Requested Domain (`requested_records`)

The Requested domain stores fully assembled, policy-evaluated, placed payloads — the authorized dispatch record.

**Contract:**
- **Append-only** — rows are never updated or deleted. `REVOKE UPDATE, DELETE ON requested_records FROM dcm_app`.
- **Traceable** — every record has a non-nullable `intent_uuid` (which intent produced this) and `operation_uuid` (which operation authorized this).
- **Complete provenance** — `layer_sources` records which layers contributed and how many fields each contributed. `policy_results` records which policies evaluated and their outcomes. `provenance` records field-level origin for every field.
- **Placement recorded** — `placement_result` records the provider selection decision, score, and constraints.
- **Tenant-isolated** — RLS per tenant.

### 2.3 Realized Domain (`realized_entities`)

The Realized domain stores provider-confirmed state as versioned snapshots.

**Contract:**
- **Append-on-change** — state changes create new rows. The `is_current` flag marks the latest version. Previous versions are retained for point-in-time queries and rehydration.
- **Complete snapshots** — each row captures the full entity state, not a delta from previous state. This makes rehydration a direct lookup rather than an event replay.
- **Traceable** — every record has `request_uuid` linking it to the authorized request that produced this state.
- **Versioned** — `version_major.minor.revision` follows semantic versioning. Breaking field changes increment major; additive changes increment minor; data-only changes increment revision.
- **Tenant-isolated** — RLS per tenant.

### 2.4 Discovered Domain (`discovered_records`)

The Discovered domain stores independently observed resource state from provider discovery runs.

**Contract:**
- **Ephemeral** — discovery runs produce fresh snapshots. Previous runs are retained for trend analysis and drift history, subject to retention policy.
- **Grouped by run** — `discovery_run_uuid` groups all records from a single discovery cycle.
- **Match tracking** — `entity_uuid` links discovered resources to known DCM entities. Null `entity_uuid` indicates an orphan candidate (resource exists at provider but has no DCM entity).
- **Confidence scored** — `match_confidence` indicates how certain the match is (`exact`, `high`, `low`, `unmatched`).
- **Tenant-isolated** — RLS per tenant (discovered resources inherit tenant from their matched entity or provider).

---

## 3. Audit Record Contract

Audit records have the strictest contract in DCM. They are the compliance evidence trail.

**Contract:**
- **Append-only** — `REVOKE UPDATE, DELETE ON audit_records FROM dcm_app`. Belt-and-suspenders trigger prevents modification even by privileged roles.
- **Hash chain** — each record's `record_hash` is `SHA-256(record_content + previous_record_hash)`. `chain_sequence` is monotonically increasing per entity. First record uses `GENESIS-HASH` as the previous hash.
- **Tamper-evident** — breaking the hash chain is detectable by verifying `chain_sequence` order and recomputing hashes. The Audit Service exposes `POST /api/v1/audit/chain/verify` for chain integrity verification.
- **Non-repudiable** — every record captures `immediate_actor_uuid`, `authorized_by_uuid`, `session_uuid`, and the complete before/after state.
- **Retention** — minimum P365D across all deployment profiles. FedRAMP/sovereign profiles may require P2555D (7 years).
- **Separate privilege** — `dcm_audit` role has INSERT+SELECT only. `dcm_app` has INSERT+SELECT only. No role has UPDATE or DELETE.

---

## 4. Pipeline Event Contract

Pipeline events route work between control plane services.

**Contract:**
- **Append-only** — events are never modified after publication.
- **Real-time notification** — PostgreSQL `LISTEN/NOTIFY` trigger fires on every insert, notifying subscribed services.
- **Consumption tracking** — `consumed_by` and `consumed_at` track which services have processed each event.
- **Ordered** — events within a single entity are ordered by `published_at`. Cross-entity ordering is not guaranteed.
- **Tenant-isolated** — RLS on SELECT ensures services only see events for the current tenant context.

For high-throughput deployments (>1000 events/sec), Kafka can be deployed alongside PostgreSQL. Events are written to both the `pipeline_events` table (for persistence and query) and the Kafka topic (for high-throughput consumer groups). The table is the source of truth; Kafka is the performance layer.

---

## 5. Tenant Isolation Enforcement

Row-Level Security (RLS) is the tenant isolation mechanism across all data domains.

**How it works:**
1. The API Gateway extracts tenant from the JWT claims and sets `X-DCM-Tenant` header
2. Each service sets `SET dcm.current_tenant_uuid = '{uuid}'` on its database connection before any query
3. RLS policies on every tenant-scoped table filter rows to the current tenant
4. `dcm_app` role is subject to RLS — it cannot query across tenants
5. `dcm_admin` role bypasses RLS for platform administration (separately audited)

**Tables with RLS:**
`intent_records`, `requested_records`, `realized_entities`, `discovered_records`, `operations`, `audit_records`, `subscriptions`, `subscription_entities`, `subscription_updates`, `pipeline_events`

---

## 6. Sovereignty Partitioning

For deployments spanning multiple sovereignty zones, DCM deploys separate PostgreSQL instances per zone. Data does not cross sovereignty boundaries at the database level.

**Model:**
- Each sovereignty zone has its own PostgreSQL instance with its own connection string
- The API Gateway routes requests to the correct zone's database based on tenant and resource sovereignty declarations
- Cross-zone queries are explicitly prohibited — a query in Zone A cannot read data from Zone B
- Federation between zones uses the Peer DCM protocol, which transfers only the minimum data required and is subject to sovereignty policy evaluation

**Deployment profiles:**
- **Minimal/Standard:** Single PostgreSQL instance (all data in one zone)
- **Enterprise:** PostgreSQL with read replicas (one write primary, read replicas per region)
- **Sovereign:** Separate PostgreSQL instance per sovereignty zone, no cross-zone replication

---

## 7. Resilience and Recovery

**Write-Ahead Log (WAL):**
PostgreSQL's WAL ensures that committed transactions survive process crashes. DCM does not implement its own WAL — it relies on PostgreSQL's native durability guarantees.

**Backup and point-in-time recovery:**
PostgreSQL's continuous archiving and point-in-time recovery (PITR) provide the disaster recovery mechanism. The Crunchy Postgres Operator (or equivalent) manages automated backups.

**Audit chain recovery:**
If the audit hash chain is broken (database restored from backup to a point before the latest audit record), the chain verification endpoint detects the break. The recovery procedure is:
1. Verify chain integrity — identify the break point
2. Records after the break point are marked with `chain_recovery: true`
3. A new chain segment begins from the break point with a `RECOVERY-HASH` seed
4. Both chain segments are retained — the original (broken) and the recovery segment
5. The break event itself is recorded as an audit record

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
