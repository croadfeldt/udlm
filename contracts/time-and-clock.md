# UDLM — Time and Clock Model Contract

**Document Status:** 📋 Draft — Specification
**Document Type:** Wire-Compatibility Contract
**Established:** 2026-05-26
**Maps to:** DATA
**Governed by:** [ADR-005 — Time integrity](../docs/adr/ADR-005-time-integrity.md)

> Defines how time is represented, how events are ordered, how clock
> synchronization is required, and how independent peers agree on ordering and
> audit. Wire-compatible: any conformant peer MUST emit timestamps any other
> peer can interpret without ambiguity — and ordering MUST be reconstructible
> without trusting anyone's clock.

---

## 1. Purpose

Audit chains depend on ordering; federation depends on peers agreeing on that
ordering; regulated data depends on time being accurate to a known bound. This
contract keeps those three concerns **separate**, because conflating them is how
time models go wrong:

- **Ordering is structural, not temporal** (§4). Order comes from a hash-linked
  sequence and causal references — never from comparing wall clocks. Audit stays
  correct even when a clock is wrong.
- **Cross-peer agreement is a causal partial order plus mutual attestation** (§5),
  not a fictional single global line.
- **Clock accuracy is a profile-declared, adopt-by-reference capability** (§6).
  The platform mandates no tolerance; the profile binds the standard.

---

## 2. Time representation

A conformant realization MUST:

- Use **UTC** for all timestamps crossing interop boundaries. Local time is
  permitted only in UI rendering, converted to UTC before persistence or transport.
- Encode timestamps as **ISO 8601 / RFC 3339** with explicit `Z`. Example:
  `2026-05-26T14:32:18.456Z`.
- Use **millisecond precision** on the wire. Higher precision MAY be kept
  internally but MUST be truncated to milliseconds when emitted (finer accuracy
  than milliseconds is carried by the sync-capability attestation, §6, not by
  wire timestamps).
- NEVER use Unix epoch seconds, fractional days, or other non-ISO encodings on the wire.

A **UUIDv7** identifier is itself a conformant time source at millisecond resolution: per RFC 9562 it embeds
a Unix-epoch **millisecond** UTC timestamp. Where an artifact's identity and its creation time are the same
fact (e.g. `sequence_uuid`, §4), the UUIDv7 carries the time — no separate wire timestamp is needed for it.
It does not replace an ISO 8601 field where finer human-readable time is required, and it is a millisecond
source (not sub-millisecond — §4).

### 2.1 Required precision and format

| Field type | Required precision | Wire format example |
|---|---|---|
| Event timestamps | Millisecond | `2026-05-26T14:32:18.456Z` |
| Audit record timestamps | Millisecond | `2026-05-26T14:32:18.456Z` |
| Lifecycle state transitions | Millisecond | `2026-05-26T14:32:18.456Z` |
| Scheduled request times (`not_before`, etc.) | Second (millis permitted) | `2026-05-26T15:00:00Z` |
| Date-only fields (rare) | Day | `2026-05-26` |

Peers MUST reject timestamps lacking timezone indication or failing ISO 8601
parsing with `validation.timestamp_malformed`.

---

## 3. Authoritative timestamps

Where an artifact has multiple timestamp candidates, this is the authoritative one:

| Artifact | Authoritative timestamp source |
|---|---|
| Event | Set by the commit log at append time, NOT by the emitter |
| Audit record | Set by the audit log at append time |
| Lifecycle state transition | Set by the system effecting the transition |
| Scheduled request `not_before` | Set by the consumer at submission |
| Provider callback report | Provider-supplied; subject to §7 validation |

The authoritative timestamp is used for **correlation and display**. It is **not**
the basis of ordering — see §4.

---

## 4. Ordering is structural (not temporal)

Ordering MUST NOT depend on wall-clock comparison. A conformant realization
orders as follows:

1. **Within an audit stream — a total order by construction.** The audit chain
   ([`universal-audit.md`](../observability/universal-audit.md)) is hash-linked:
   each entry references the hash of its predecessor. Ties (entries appended in
   the same millisecond) break on `sequence_uuid`, a **UUIDv7** generated at
   append time. A UUIDv7 carries a **millisecond**-resolution Unix timestamp (not
   sub-millisecond); the same-millisecond tie-break is **structural, not
   temporal** — a **monotonic counter** seeded into its random field (RFC 9562
   §6.2 monotonicity), *not* finer-grained time. A conformant peer MUST
   reconstruct the total order of any contiguous segment from the hash links +
   `sequence_uuid` **alone** — the wall-clock timestamp (§3) is never transmitted
   or compared for ordering; it is for correlation and display only.
2. **Across streams — a causal partial order.** Every event carries **causal
   references** (the events/entities it depends on — already present as the audit
   record's references). A conformant peer MUST preserve *happened-after* order:
   if `X → Y` then no peer may order `Y` before `X`. Events with **no** causal
   link are **concurrent**; different peers MAY linearize them differently, and
   that is not a conflict — the shared truth is the DAG, not any single line.
   Hybrid Logical Clocks (HLC) or vector clocks MAY be used where tight cross-node
   ordering granularity is required.
3. **A genuine total order across peers** (needed only for a *shared* resource
   two peers both act on) is established by an **explicit, audited authority** —
   the resource's single-writer owner — or by a consensus round. The tie-break
   decision is itself a signed audit event; it is never implied by clocks.

---

## 5. Cross-peer agreement and attestation

When two independent realizations exchange or co-observe events, they reconcile
by causality and prove integrity by mutual attestation:

1. **Reconcile to the causal DAG** (§4.2). "Peer A says XYZ, peer B says YXZ" is
   either **concurrency** (both are valid linearizations of the same DAG — no
   conflict) or a **causal-order violation** (detected below).
2. **Mutual signed checkpoints.** Each peer periodically publishes a **signed
   checkpoint** — its audit-chain Merkle root plus its `sequence_uuid`/HLC
   high-water-mark — under an **attested identity** (see the trust/attestation
   model). When peer A cross-references an event from peer B, A embeds B's signed
   root at that point.
3. **Divergence is detectable and attributable.** A peer that reorders or rewrites
   its chain breaks the cross-anchors its peers hold; verification against the
   embedded roots fails, and the fault is attributable to a signed identity. This
   is the Certificate-Transparency cross-witnessing pattern (no shared ledger
   required for a known federation). See `cross-dcm-audit-data-model`.

---

## 6. Clock synchronization — a profile-declared capability

The platform mandates **no** fixed skew tolerance. Instead:

1. UDLM defines the **shape** of a `TimeSync` requirement: UTC-traceable, a
   `max_divergence` bound, and a mechanism class (NTP / PTP). The bound MUST be
   **attestable** — a node declares the sync it can hold.
2. The **profile declares the standard**, adopted **by reference** (T5), not a
   value coined here:

   | Profile | `max_divergence` | Adopted standard |
   |---|---|---|
   | Base | **50 ms** of UTC | FINRA **CAT** (business-clock sync to NIST) |
   | Regulated / FSI | **1 s / 1 ms / 100 µs** by activity | **MiFID II RTS 25** |
   | High-precision | sub-µs | **PTP (IEEE 1588)**, hardware timestamping |
   | Sovereign | per regime | the regime's national time standard |

3. **Providers advertise and attest** achievable sync as a capability
   ([ADR-004](../docs/adr/ADR-004-provider-capability-declaration.md)); **placement
   admits** a workload only where the node's attested capability meets its
   profile's declared `max_divergence`.
4. **Skew detection.** A peer MUST detect inbound artifacts whose divergence
   exceeds the **applicable profile bound** and:
   - provider-supplied: reject with `validation.timestamp_skew_exceeded`;
   - peer-supplied in federation: record an audit event and proceed, flagging the
     source for sync investigation.
   Any timestamp beyond the profile bound **in the future** MUST be rejected.

Traceability to UTC (NIST / BIPM) is required in every profile; only the bound and
mechanism vary. Because ordering is structural (§4), sync accuracy governs
**correlation and admission**, never order-correctness.

---

## 7. Provider timestamp validation

Provider callbacks include timestamps. A conformant peer:

1. MUST require the provider timestamp to be UTC + ISO 8601.
2. MUST validate it against the **applicable profile's `max_divergence`** (§6),
   not a fixed constant.
3. MUST, on failure, reject via the standard error envelope
   ([`error-model.md`](error-model.md)) — never silently rewrite a provider
   timestamp. Accept or reject.

---

## 8. Leap seconds

**Audit order is not at risk during a leap second**, because ordering is **structural** (§4): the hash
chain and the `sequence_uuid` monotonic counter are unaffected by any wall-clock adjustment. So this
section is about **clock accuracy**, not order — and it deliberately does **not** require a specific
leap-handling strategy, because there is no interoperable standard for one (smearing schemes differ across
public-cloud providers) and a peer's choice is not observable on the wire (timestamps are millisecond UTC
either way, §2).

A conformant realization MUST:
- Keep its clock **UTC-traceable** across a leap-second event — it stays within its profile's
  `max_divergence` bound (§6); the leap does not push it out of tolerance.
- **Declare its leap-handling strategy** in its conformance declaration.

It **MAY** use any strategy that preserves that traceability — smearing (a gradual adjustment over a window,
the common public-cloud approach, forward-compatible with the CGPM's decision to retire leap seconds by
2035) or a leap-aware representation (a repeated or `:60` second). Note that "monotonic" applies to **audit
ordering** (guaranteed structurally, §4), **not** to the wall-clock timestamp — a smeared or repeated second
is fine precisely because order never comes from the clock.

---

## 9. Time zones (consumer-facing)

- Storage and transport: **UTC**.
- Display: per-user preference (UI MAY render local time).
- Audit records: always UTC; the source of truth is UTC regardless of display.

---

## 10. Validation rules (conformance checks)

A conformant realization MUST:

- Reject non-UTC timestamps, and timestamps lacking explicit timezone, at ingest.
- Reject timestamps whose divergence exceeds the **applicable profile bound** (§6),
  categorized per §6.4.
- Truncate or reject sub-millisecond precision on the wire.
- Reconstruct total order from hash links + `sequence_uuid` **without** relying on
  wall-clock comparison (§4).
- Keep the clock UTC-traceable (within the profile bound) through leap events, and declare its
  leap-handling strategy (§8); audit order is structural (§4), never clock-derived.

---

## 11. Related contracts

- [ADR-005 — Time integrity](../docs/adr/ADR-005-time-integrity.md) — the decision this contract implements
- [`identifier-scheme.md`](identifier-scheme.md) — UUIDv4 identity / UUIDv7 time-ordered policy
- [`event-catalog.md`](event-catalog.md) — events carry authoritative timestamps + causal references
- [`universal-audit.md`](../observability/universal-audit.md) — hash-linked audit chain, total ordering
- `cross-dcm-audit-data-model` — federated causal reconciliation + cross-signed checkpoints
- [ADR-004](../docs/adr/ADR-004-provider-capability-declaration.md) — the capability model `TimeSync` uses
- [`error-model.md`](error-model.md) — timestamp-related error codes
- [`scheduled-requests.md`](../lifecycle/scheduled-requests.md) — `not_before` and recurring schedules
