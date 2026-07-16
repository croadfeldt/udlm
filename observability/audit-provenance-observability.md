# UDLM — Audit, Provenance, and Observability



**Document Status:** ✅ Complete  
**Related Documents:** [Four States](../foundations/four-states.md) | [data stores](../contracts/storage-providers.md) | [Context and Purpose](../foundations/context-and-purpose.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the UDLM data model.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](../foundations/foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)
>
> **This document maps to: DATA**
>
> The Data abstraction — audit records, provenance as structural data



---

## 1. Purpose

Audit, Provenance, and Observability are three distinct but related capabilities in the model. They are often conflated — this document separates them precisely, defines their relationship, and establishes the architectural model for each.

| Capability | Question Answered | Audience | Time Orientation |
|------------|------------------|----------|-----------------|
| **Provenance** | Where did this data come from and how did it change? | System — embedded in data | Embedded in every payload |
| **Audit** | What happened, who authorized it, can you prove it? | Auditors, Compliance, Security | Backward-looking |
| **Observability** | Is the system healthy and performing within expectations? | SRE, Platform Engineers | Forward-looking, real-time |

---

## 2. Provenance

### 2.1 Definition

Provenance is the structural data-lineage mechanism embedded in every field of every managed payload. It is not a separate system — it is part of the data itself. Every field that can be created or modified by any process carries provenance metadata alongside its value.

Provenance answers: "where did this value come from, what modified it, and why?"

Audit queries provenance to answer its questions. Observability does not use provenance directly — it operates on event streams and metrics.

### 2.2 Provenance Structure

See [Context and Purpose — Section 4.4](../foundations/context-and-purpose.md) for the complete field-level provenance structure. The key elements:

```yaml
field_name:
  value: <current value>
  metadata:
    override: <allow|constrained|immutable>
    basis_for_value: <human-readable — why this value was set>
    baseline_value: <original default before any override>
    locked_by_policy_uuid: <uuid — if constrained or immutable>
    locked_at_level: <global|tenant|user>
  provenance:
    origin:
      value: <original value>
      source_type: <layer|policy|actor|provider|discovery|rehydration|override>
      # Canonical provenance source-kind vocabulary (data-model-core §6/§7,
      # realized-entity.schema.json provenance source.kind). The former `consumer`
      # value maps to `actor` — a consumer acts as an authenticated actor.
      source_uuid: <uuid of originating entity>
      timestamp: <ISO 8601>
    modifications:
      - sequence: 1
        previous_value: <value before>
        modified_value: <value after>
        source_uuid: <uuid of modifying entity>
        operation_type: <enrichment|transformation|gating|lock|grant|rehydration>
        actor_uuid: <uuid of actor that caused this modification>
        timestamp: <ISO 8601>
        reason: <human-readable>
```

### 2.3 Provenance Obligations

Every component that modifies data carries a provenance obligation — it must record its UUID, operation type, actor, timestamp, and reason for every field it touches. A component that modifies data without recording provenance violates the data model contract.

| Component | Provenance Obligation |
|-----------|----------------------|
| Request Payload Processor | Record source UUID and type for every field assembled from layers |
| Policy Engine | Record policy UUID, level, operation type, and reason for every field modified or locked |
| Service Provider (Denaturalization) | Record provider UUID and timestamp for every field in the realized payload |
| data store | Emit provenance event to Audit component on every write |
| Resource Discovery | Record provider UUID, timestamp, and method for every discovered field |
| Rehydration Pipeline | Record source store, source record UUID, rehydration reason, and actor UUID |

### 2.4 Provenance Across the Full Lifecycle

The provenance chain for a single field may span multiple lifecycle stages:

```
Base Layer sets encryption_standard: AES-128
  origin: {source_type: base_layer, source_uuid: layer-uuid-001}

Transformation Policy enriches to AES-256
  modification: {source_uuid: policy-uuid-001, operation: transformation,
                 reason: "Security standard requires AES-256 minimum"}

Compliance-class Validation Policy locks as immutable
  modification: {source_uuid: policy-uuid-002, operation: lock,
                 reason: "CISO mandate — encryption standard non-negotiable"}

Provider reports realized value: AES-256
  modification: {source_uuid: provider-uuid-001, operation: denaturalization,
                 reason: "Provider confirmed encryption standard applied"}

Drift detected: discovered value AES-128
  modification: {source_uuid: discovery-uuid-001, operation: discovery,
                 reason: "Direct modification detected outside the managed lifecycle"}
```

The complete chain tells the full story of that field across its entire existence.

---

## 3. Audit

Audit answers "what happened, who authorized it, can you prove it?" — backward-looking, for auditors and
compliance. The **universal audit record**, its action vocabulary, the composite actor ("who"), retention,
and the tamper-evidence (Merkle / RFC 9162) contract are defined canonically in
**[universal-audit.md](universal-audit.md)** — this document does not restate them.

What is provenance-specific and stays here: audit *queries provenance* to answer field-level "why"
questions, and any store holding state has the **provenance-emission obligation** (§2.3) — it emits an event
to the audit store on every write. How a realization implements the audit store, the audit query API, and
the synchronous-commit / async-enrich write path is realization architecture (see
[universal-audit.md](universal-audit.md) §7 and the DCM architecture docs).

---

## 4. Observability

Observability answers "is the system healthy and performing?" — forward-looking, real-time, for SRE. It
operates on **event streams and metrics**, not on provenance or the audit trail.

Observability is almost entirely **realization architecture**: the metrics surface (metric names, labels),
the collection pipeline, the dashboards, and the telemetry backends are owned by the DCM architecture docs,
not by the data model. The one durable data-model point is the **audit-vs-observability distinction**,
stated canonically in [universal-audit.md](universal-audit.md) §11 — audit is the tamper-evident record of
*what changed and who authorized it* (retained for years, compliance-grade, authoritative); observability is
*operational health signal* (retained for weeks, non-authoritative, rebuildable). They are different
concerns with different stores, retention, and integrity requirements; conflating them is the error this
separation exists to prevent.

---

## 5. System policies (audit / observability)

These are UDLM data (profile-governed where noted); the mechanism a realization uses to satisfy them lives
in the DCM architecture docs.

| ID | Policy |
|----|--------|
| `STO-004` | The audit store is a specialized store contract — append-only, hash-chain integrity, reference-based retention, compliance-grade queries. The event stream is the delivery channel only, not the compliance destination. |
| `AUD-018` | Audit records are replicated by live sync (regional peers) or signed-bundle export (sovereign peers); sovereignty checks are required before any replication, and hash-chain integrity is preserved across transport. A fully isolated sovereign peer keeps a local-only audit store with manual export. |
| `AUD-019` | Store failures are themselves recorded via the synchronous commit-log entry (a consensus-durable store independent of all data stores); an audit-store self-failure produces `pending_forward` records, and on recovery a gap record (`AUDIT_STORE_UNAVAILABLE`) with the outage window is inserted, so the hash-chain gap is explicit and auditable. |
| `OBS-002` | A realization ships a default observability dashboard (e.g. Grafana-based) for minimal/dev/standard profiles; standard+ may substitute enterprise platforms, FSI requires enterprise observability, and a sovereign peer uses a local dashboard only with no external connections. |

---

## 6. What is specified elsewhere (moved from this document)

- The **audit record, action vocabulary, actor, retention, and Merkle contract** →
  [universal-audit.md](universal-audit.md).
- The **audit store architecture, the audit query API / API gateway, the two-stage write pipeline,
  cross-site audit replication, and the observability metrics surface + collection pipeline + dashboards**
  → the DCM architecture docs (realization architecture; a peer implements them differently and still
  conforms).
