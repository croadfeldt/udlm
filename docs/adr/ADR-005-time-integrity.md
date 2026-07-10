# UDLM ADR-005: Time integrity — structural ordering, profile-scoped time-sync, mutual attestation

**Status:** Proposed
**Date:** 2026-07-10
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `contracts/time-and-clock.md` (the contract this governs); `contracts/identifier-scheme.md` (UUIDv7 policy); ADR-002 (adopt-by-reference / served pattern); ADR-004 (provider capability declaration); the trust/attestation model; `cross-dcm-audit-data-model` (corpus UC); `design-principles/core-tenets.md` (T5 adopt-by-reference)
**Tracking:** review feedback on udlm #18 (swapdisk: ±5 s tolerance too broad, leap-second smear over-mandated) → the broader question "how do independent peers agree on ordering and audit?"

## Context

The time-and-clock contract conflated three separate concerns and got each slightly wrong:

1. It made **wall-clock time the basis of ordering** (`(timestamp, sequence_uuid)`), so audit correctness depended on clock agreement.
2. It **hardcoded a ±5 s skew tolerance as a platform constant**. ±5 s is not a recognized standard for regulated/sensitive data — every established regime is tighter (FINRA CAT 50 ms; MiFID II RTS 25 1 s / 1 ms / 100 µs) — and baking one number into the substrate forces one regime on every deployment.
3. It **mandated leap-second smearing** as the sole conformant behavior, which conflicts with ISO 8601 permitting `:60`.

It also never addressed the federated case: two independent DCMs each keep their own audit chain, and may present different orderings (DCM 1 says XYZ, peer says YXZ). Forcing a single global total order across independent systems is impossible without consensus (FLP) and usually the wrong goal.

## Decision

**1. Ordering is structural (causal), not temporal.**
Total order *within* an audit stream comes from a hash-linked sequence with a UUIDv7 tiebreak (ms timestamp + monotonic counter, per RFC 9562) — never from comparing wall clocks. *Across* streams/DCMs, order is a **causal partial order (a DAG)** carried by causal references (happened-after links — already present as the audit record's references to the entities/events it acts on; HLC or vector clocks where fine cross-node granularity is needed). Concurrent events (no causal link) MAY be linearized differently by different observers — that is concurrency, **not** conflict. A genuine total order across DCMs for a *shared* resource is established only by an **explicit, audited authority** (the resource's single-writer owner) or a consensus round; that tie-break is itself a signed audit event.

**2. Time synchronization is a profile-declared, adopt-by-reference capability — the platform is standard-neutral.**
UDLM defines only the *shape*: a `TimeSync` requirement (UTC-traceable, a `max_divergence` bound, a mechanism class NTP/PTP) that MUST be attestable. It mandates **no** tolerance. The **profile** binds the standard by reference — base → **FINRA CAT (50 ms of UTC)**; regulated/FSI → **MiFID II RTS 25** tiers (1 s / 1 ms / 100 µs by activity); sovereign → its own regime. Providers/nodes **advertise and attest** the sync they can hold as a capability; **placement admits** a workload only where node capability meets its profile's declared bound. This is the same adopt-by-reference + capability pattern as ADR-002 (cost/capacity served overlays) and ADR-004 (provider capability declaration).

**3. Cross-system integrity is mutual attestation.**
Each realization's chain is Merkle/hash-linked (internally tamper-evident). Peers exchange **signed checkpoints** — a Merkle root plus the sequence/HLC high-water-mark — under **attested identity** (the trust model), and embed each other's roots when they cross-reference events. This is the Certificate-Transparency cross-witnessing pattern (no blockchain needed for a known federation). A peer that reorders or rewrites history breaks the cross-anchors the other holds, so divergence becomes **detectable and attributable to a signed identity** — case "XYZ vs YXZ" resolves to either concurrency (both valid views of one DAG) or a detected integrity fault, never opinion.

**4. Leap seconds.**
REQUIRE monotonic, UTC-traceable time (never steps backward). RECOMMEND smearing (Google / AWS Time Sync / Meta; the CGPM voted in 2022 to abandon leap seconds by 2035). Do NOT mandate a single mechanism — a leap-aware implementation that stays monotonic and UTC-traceable is conformant. Resolves the ISO 8601 `:60` conflict.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM)** — the `TimeSync` capability shape (UTC-traceable, `max_divergence`, mechanism class); causal references (and optional HLC) on events; the per-realization Merkle/hash-linked chain; the cross-signed checkpoints (root + watermark + attested identity).
- **Policy (DCM / profile)** — the *profile* declares which time standard it requires (adopt-by-reference); the "node capability ≥ profile bound" placement/admission rule; the choice of authority-per-shared-resource vs consensus; the checkpoint/witnessing cadence.
- **Provider** — NTP/PTP holding the sync; the attestation source signing identity + measured divergence; the witnessing/gossip exchange between peers; consensus where invoked.

## Options considered

- **(A) Keep a hardcoded platform skew (±5 s).** Rejected: not a recognized standard, not fit-for-purpose for regulated data, and forces one regime on all deployments.
- **(B) Global total order via distributed consensus for all events.** Rejected: impossible/unnecessary (FLP; concurrency is real and correct), heavy, and the wrong goal — most cross-DCM "disagreements" are legitimate concurrency.
- **(C) [chosen] Structural causal ordering + profile-scoped adopt-by-reference time-sync capability + mutual attestation.** Ordering correctness is clock-independent; the tolerance is regime-appropriate and enforceable; federated divergence is detectable.

## Consequences

- **+** Audit ordering is provable from the chain, independent of clock accuracy.
- **+** Time-sync is enforceable (placement-gating) and regime-appropriate per profile; multi-regime / sovereign deployments coexist on one platform without the substrate picking a winner.
- **+** Cross-DCM divergence is detectable and attributable; federation gets a real integrity story, not trust-by-assertion.
- **−** Events must carry causal references (largely already true via the dependency graph); HLC is needed where cross-node ordering granularity is tight.
- **−** Federated DCMs must run the checkpoint/witnessing exchange (ties to the trust model) — new mechanism, though it reuses attestation.
- Supersedes the ±5 s constant and the smear mandate in `contracts/time-and-clock.md` (redrafted alongside this ADR).
