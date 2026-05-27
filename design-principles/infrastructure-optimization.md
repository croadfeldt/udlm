# UDLM — Data Contracts and the Four Persistent Domains

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Specification — Data contracts and persistence requirements
**Related Documents:** [Foundational Abstractions](../foundations/foundations.md) | [Four States](../foundations/four-states.md) | [Provider Contract](../contracts/provider-contract.md)

---

## 1. Design Principle — Data Contracts, Not Abstraction Layers

UDLM prescribes **data contracts** (schemas, immutability rules, versioning, hash chains) — not infrastructure products. Where a contract maps directly to a single well-understood infrastructure category, UDLM prescribes the category and the contract, not an abstraction layer over it.

Abstraction layers earn their place when the underlying implementations have genuinely different interaction contracts — different APIs, different lifecycle semantics, different operational models. When the implementations share a standard protocol (SQL, OIDC, AMQP), the protocol is the abstraction. Adding a substrate-specific abstraction on top of a standard protocol is unnecessary indirection.

This is a substrate-level principle: any UDLM-conformant realization MUST follow it. A realization SHOULD NOT introduce abstraction layers between the data contracts defined in this document and the storage technology it chooses; it SHOULD enforce the contracts directly at the storage interface.

---

## 2. The Four Data Domains (Foundational)

UDLM tracks every resource through four lifecycle domains. These remain architecturally distinct — they represent different things, have different immutability rules, and serve different query patterns. They are foundational substrate concepts that any conformant realization MUST honor.

### 2.1 The Four Domains

| Domain | What it represents | Immutability | Primary consumers |
|--------|-------------------|-------------|-------------------|
| **Intent** | What the consumer asked for — raw declaration before processing | Append-only. A new intent version creates a new record. Previous intents are never modified. | Audit, portability (re-process intent through new policies), request history |
| **Requested** | What was approved and dispatched — assembled, policy-validated, placed | Append-only. Each policy evaluation produces a new version. Complete provenance chain. | Provider dispatch, audit, rollback comparison |
| **Realized** | What the provider actually built — confirmed state with provider metadata | Append-only versioned. Each state change creates a new snapshot. `is_current` flag for latest. | Operational queries, drift comparison baseline, inventory |
| **Discovered** | What actually exists right now — independently observed by discovery | Ephemeral. Each discovery run produces a fresh snapshot. Previous snapshots retained for trend analysis. | Drift detection (compare against Realized), capacity planning |

### 2.2 Substrate Invariants for the Four Domains

The substrate requires the following invariants regardless of storage technology:

- **Distinct domain identity:** Intent, Requested, Realized, and Discovered are addressable separately. Implementations MAY co-locate them in the same store; the substrate does NOT require physical separation.
- **Append-only for Intent, Requested, and Audit:** Once written, records in these domains MUST NOT be updated or deleted. Version supersession is achieved by writing a new record that supersedes the prior one.
- **Versioned snapshots for Realized:** Each state change produces a new snapshot. The current snapshot is identifiable.
- **Ephemeral snapshots for Discovered:** Each discovery run produces a fresh snapshot; the substrate permits retention policies for trend analysis.
- **Tamper-evidence on Audit:** The substrate requires that audit records carry tamper-evidence (e.g., a SHA-256 hash chain) so any modification is detectable.
- **Tenant isolation:** Cross-tenant data access MUST be enforced at the storage interface.

---

## 3. Mandatory Persistence Requirement (Substrate Contract)

The substrate requires that **all four domains are persistently queryable**. A UDLM-conformant realization MUST provide a durable storage mechanism for Intent, Requested, Realized, and Discovered records — including the audit chain — such that:

- Records survive process restarts, host failures, and reasonable infrastructure outages
- Queries return consistent results within the substrate's declared consistency model
- Tenant isolation is enforced at the storage interface
- Append-only and version-supersession semantics are honored
- Tamper-evidence on audit records is preserved

**The specific technology is not specified by the substrate.** A realization MAY use a relational database, an event store, a multi-model database, or any combination — provided the storage interface enforces the substrate contracts above.

A peer realization that uses different storage technology than another peer is still UDLM-conformant, provided both honor the data contracts. Federation interop is at the wire level (the event catalog, the entity record format, the audit envelope) — not at the storage level.

---

## 4. Implementation Independence (Federation Implication)

Because the substrate fixes contracts but not technology, federation peers MAY have different storage implementations. The wire-compatibility model (any conformant realization produces records other peers can read, interpret, and exchange) is enforced at:

- The event-catalog wire format
- The entity record JSON shape
- The audit envelope contract
- The data-classification field metadata
- The identifier-scheme contract (see [identifier-scheme.md](../contracts/identifier-scheme.md))

Storage choices (single relational database, event-sourced log, etc.) are not part of the wire contract. A peer realization may pick a different storage technology and still be a valid federation peer.

---

## 5. UDLM System Policies

| Policy | Rule |
|--------|------|
| `INF-001` | A UDLM-conformant realization MUST provide persistent storage for the four data domains (Intent, Requested, Realized, Discovered) and the Audit chain. The choice of storage technology is a realization decision; the contracts (append-only, versioning, tamper-evidence, tenant isolation) are substrate-required. |
| `INF-002` | The substrate prescribes data contracts, not infrastructure products. Realizations MUST NOT introduce abstraction layers between UDLM data contracts and the chosen storage technology that obscure or weaken those contracts. |
| `INF-003` | Intent, Requested, and Audit records MUST be append-only. Records are never modified or deleted after write; supersession is achieved by writing a new record. |
| `INF-004` | Realized records MUST be versioned snapshots with an identifiable current snapshot. Each state change produces a new snapshot. |
| `INF-005` | Discovered records MUST be retained per the realization's declared retention policy and MUST NOT be conflated with Realized records. |
| `INF-006` | Audit records MUST carry tamper-evidence (hash chain or equivalent cryptographic mechanism). Any modification of the audit chain MUST be detectable. |
| `INF-007` | Tenant isolation MUST be enforced at the storage interface. Cross-tenant data access requires explicit substrate-defined authorization. |

---

*UDLM substrate document. Specific storage technology choices (PostgreSQL, CockroachDB, event-sourced stores, etc.), schema design, indexing strategies, query optimization, data retention and archival policies, and control-plane service architecture are realization choices. The DCM realization's PostgreSQL mandate and concrete schema live in the DCM realization's documentation.*
