# UDLM — Data Contracts and the Four Persistent Domains

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Specification — data contracts and persistence requirements (the data-contract *principle* is stated once here; the enforceable form is the `INF-*` policies in §4)
**Related Documents:** [design-principles index](README.md) | [Foundational Abstractions](../foundations/foundations.md) | [Four States](../foundations/four-states.md) | [Conformance](../CONFORMANCE.md) | [Provider Contract](../contracts/provider-contract.md)

---

## 1. Design Principle — Data Contracts, Not Abstraction Layers

UDLM prescribes **data contracts** (schemas, immutability rules, versioning, hash chains) — not infrastructure products. Where a contract maps directly to a single well-understood infrastructure category, UDLM prescribes the category and the contract, not an abstraction layer over it.

Abstraction layers earn their place when the underlying implementations have genuinely different interaction contracts — different APIs, different lifecycle semantics, different operational models. When the implementations share a standard protocol (SQL, OIDC, AMQP), the protocol is the abstraction. Adding a substrate-specific abstraction on top of a standard protocol is unnecessary indirection.

This is a substrate-level principle: any UDLM-conformant realization MUST follow it. A realization SHOULD NOT introduce abstraction layers between the data contracts defined in this document and the storage technology it chooses; it SHOULD enforce the contracts directly at the storage interface. (Enforceable form: `INF-002`.)

---

## 2. The Four Data Domains (Foundational)

UDLM tracks every resource through four lifecycle domains. The domains themselves — what each represents and how they relate — are defined canonically in [`foundations/four-states.md`](../foundations/four-states.md); this section states only the **persistence invariants** the substrate places on them.

### 2.1 The Four Domains (summary — see four-states.md for the canonical definition)

| Domain | What it represents | Immutability | Primary consumers |
|--------|-------------------|-------------|-------------------|
| **Intent** | What the consumer asked for — raw declaration before processing | Append-only. A new intent version creates a new record. | Audit, portability, request history |
| **Requested** | What was approved and dispatched — assembled, policy-validated, placed | Append-only. Each policy evaluation produces a new version. | Provider dispatch, audit, rollback comparison |
| **Realized** | What the provider actually built — confirmed state with provider metadata | Append-only versioned. Each state change creates a new snapshot; `is_current` marks the latest. | Operational queries, drift baseline, inventory |
| **Discovered** | What actually exists right now — independently observed | Ephemeral. Each discovery run produces a fresh snapshot; retention is a realization policy. | Drift detection, capacity planning |

### 2.2 Substrate Invariants for the Four Domains

These are the invariants the substrate places on the domains, **stated once here** and enforced by the `INF-*` policies in §4. They hold regardless of storage technology:

- **Distinct domain identity:** Intent, Requested, Realized, and Discovered are addressable separately. Implementations MAY co-locate them in one store; physical separation is not required.
- **Append-only for Intent, Requested, and Audit:** once written, records in these domains are never updated or deleted. Supersession is a new record that supersedes the prior one.
- **Versioned snapshots for Realized:** each state change produces a new snapshot; the current one is identifiable.
- **Ephemeral snapshots for Discovered:** each discovery run produces a fresh snapshot; retention is a declared realization policy.
- **Tamper-evidence on Audit:** audit records carry tamper-evidence (e.g. a SHA-256 hash chain) so any modification is detectable.
- **Tenant isolation:** cross-tenant data access is enforced at the storage interface.

---

## 3. Persistence and Implementation Independence

**Persistence (durability).** The substrate requires that all four domains — including the audit chain — are **durably persistent and queryable**: records survive process restarts, host failures, and reasonable infrastructure outages, and queries return consistent results within the realization's declared consistency model. The invariants that govern *how* records are written (append-only, versioning, tamper-evidence, tenant isolation) are stated once in §2.2; this section adds only the durability requirement on top of them.

**Technology is a realization choice.** The substrate does **not** specify storage technology. A realization MAY use a relational database, an event store, a multi-model database, or any combination, provided the storage interface enforces the §2.2 invariants. Two peers on different storage technologies are both conformant as long as both honor the data contracts.

**Federation interop is at the wire, not the store.** Because the substrate fixes contracts but not technology, federation peers may have entirely different storage implementations and still exchange data. Interoperability is certified at the **wire level** — the event catalog, entity-record shape, and audit envelope — never at the storage level. The authoritative list of wire-compatibility contracts is [`CONFORMANCE.md`](../CONFORMANCE.md) §5.2; it is not restated here.

---

## 4. System Policies (the enforceable form of §1–§3)

The `INF-*` policies below are the **normative, enforceable encoding** of the principle (§1) and invariants (§2.2). They read as a restatement by design — a reviewer or a conformance test cites the policy ID, not the prose. The prose explains; the policy IDs gate.

| Policy | Rule |
|--------|------|
| `INF-001` | A UDLM-conformant realization MUST provide persistent, queryable storage for the four data domains (Intent, Requested, Realized, Discovered) and the Audit chain. Storage technology is a realization decision; the §2.2 contracts are substrate-required. |
| `INF-002` | The substrate prescribes data contracts, not infrastructure products. Realizations MUST NOT introduce abstraction layers between UDLM data contracts and the chosen storage technology that obscure or weaken those contracts. |
| `INF-003` | Intent, Requested, and Audit records MUST be append-only — never modified or deleted after write; supersession is a new record. |
| `INF-004` | Realized records MUST be versioned snapshots with an identifiable current snapshot; each state change produces a new snapshot. |
| `INF-005` | Discovered records MUST be retained per the realization's declared retention policy and MUST NOT be conflated with Realized records. |
| `INF-006` | Audit records MUST carry tamper-evidence (hash chain or equivalent). Any modification of the audit chain MUST be detectable. |
| `INF-007` | Tenant isolation MUST be enforced at the storage interface. Cross-tenant data access requires explicit substrate-defined authorization. |

---

*UDLM substrate document. Specific storage technology (PostgreSQL, CockroachDB, event-sourced stores, etc.), schema design, indexing, query optimization, retention/archival, and control-plane service architecture are realization choices. The DCM realization's PostgreSQL mandate and concrete schema live in the DCM realization's documentation.*
