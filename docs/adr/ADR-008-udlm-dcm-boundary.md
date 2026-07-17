# UDLM ADR-008: The UDLM/DCM boundary and the compatibility rule

**Status:** Proposed
**Date:** 2026-07-10
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `dcm-project/enhancements` #58 (the split proposal — this ADR is its decision-of-record home); `CONFORMANCE.md`; ADR-002 (adopt-by-reference); `design-principles/core-tenets.md` (T5); ADR-005 §5 (cross-peer federation)
**Tracking:** enh #58 review feedback: "this reads as a decision from a PM perspective; it should be a doc of the udlm itself rather than an enhancement"

## Context

DCM has kept two things that change for different reasons, and at different rates, in one repository:

- a universal **substrate** — the entity types, the four-state lifecycle, the provider/policy/event/data-store contracts, provenance, identity, conformance; and
- **one operational realization** of it — the convergence engine, control plane, runtime, and integrations.

While they share a repo, two things we need are impossible. **No one can point at the substrate** — you cannot reference, version, or conformance-test it on its own, so "what must any system honor to interoperate?" has no artifact behind it. And **a peer has nothing to build against** — without a standalone substrate, federation decays into "two architecturally similar systems and a pile of adapters" instead of literal interop. The split proposal has lived as an enhancement (#58); the review correctly notes it is a boundary **decision**, so it belongs here.

## Decision

**1. The boundary test.** Applied to every file or section:

> Could a peer of DCM, built independently, do this differently and still be a valid realization of the same data?
> - **Yes** → an implementation choice → **DCM**.
> - **No** — it would break interop or invalidate the data → a substrate invariant → **UDLM**.

**2. What each owns.** UDLM owns the **entity types, the four states and their transitions, the wire contracts, provenance, and identity**. DCM owns the **convergence engine, policy evaluation, provider orchestration, the control plane, runtime, and the integrations with specific systems**.

**3. The compatibility rule (load-bearing).** **UDLM guarantees wire compatibility, not implementation portability.** Two systems on the same UDLM major version can read and exchange each other's data — but their storage, internal APIs, and runtime are their own business. This is the Kubernetes precedent: the API and CRDs are wire-compatible across every distribution; the controllers are not portable. UDLM is the API-and-CRD layer; DCM is one distribution's controllers.

**4. The line held under pressure.** Where a hard design question arose mid-extraction, the answer reinforced the line: **cost** — UDLM carries only a *reference* to external metering; it models no prices and no formulas, while the realization computes and prices. The data that crosses to a provider is an *execution slice only*, never the whole record. Both were tempting to fold into the substrate; both stayed out, because a peer would do them differently.

**5. What this does not assert.** Not a higher-order "universal model" above UDLM (that waits until a real second realization creates the pressure to find what is genuinely shared); not implementation portability; not a re-litigation of DCM's internal design.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data** — UDLM *is* the Data substrate (types, states, provenance, identity); the boundary is literally "which Data and contracts are invariant across realizations."
- **Policy** — the boundary test is the governing rule; `CONFORMANCE.md` gates what counts as substrate (what must be honored vs. advised).
- **Provider** — a realization (DCM, or an independent peer) provides behavior over the substrate; realizations/peers interoperate at the **wire**, not by sharing controllers or storage.

## Options considered

- **(A) Keep substrate + realization in one repo.** Rejected: no referenceable/versionable/conformance-testable interop surface; a peer has nothing to build against.
- **(B) Guarantee implementation portability (portable controllers).** Rejected: over-constrains realizations, isn't needed for interop, and isn't the Kubernetes model that already works at scale.
- **(C) [chosen] A standalone, wire-compatible substrate (UDLM) + one realization (DCM), boundary drawn by the peer test.**

## Consequences

- **+** The interop surface becomes a real artifact — versioned, conformance-tested — that a peer can build against; federation is literal interop, not adapters.
- **+** UDLM PRs bump the substrate; DCM PRs reference a pinned UDLM version — no cross-repo mega-PRs.
- **−** Requires discipline at the boundary (the peer test) on every addition.
- **Open — governance.** A CNCF-ready substrate wants maintainers from more than one organization. That is the real remaining ask beyond the boundary itself, and it is a decision for the group, not settled here.
