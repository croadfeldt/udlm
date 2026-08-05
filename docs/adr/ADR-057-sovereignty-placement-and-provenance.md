# UDLM ADR-057: Sovereignty covers **placement AND provenance** — the approved-source / approved-list dimension

**Status:** Proposed (croadfeldt upstream) — foundations; **requires engineering ratification** (extends P4 and unifies existing admission mechanisms); decided 2026-07-28
**Date:** 2026-07-28
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **P4** ([`design-principles/cross-cutting-requirements.md`](../../design-principles/cross-cutting-requirements.md) — *sovereignty is structural, not advisory*): today sovereignty = **placement** — immutable `sovereignty_zone` / `data_classification` / jurisdiction fields; an entity cannot silently leave its zone; DCM's **Governance Matrix** enforces.
- **ADR-008** (UDLM/DCM boundary — *could a peer enforce this differently and still be valid? then it's DCM*): the split this ADR keeps.
- **core-tenets** (UDLM is **custodian, not enforcer**; Data · Policy · Provider): UDLM carries the record, DCM decides/enforces, the provider is the mechanism.
- **Attestation R2** (`registry/realized-entity.schema.json` — per-plane attestation that an entity's *sovereignty is **BACKED**, not merely claimed*): the evidence substrate.
- **Accreditation** (`registry/accreditation.schema.json` — vets **subjects**: service/credential providers, external policy evaluators, peer implementations) and **capability admission** (ADR-PROV-003 — platform-admin disposition over a provider's declared capabilities, **default-deny**): the admission substrate that exists but is not framed *as sovereignty*.

**Settles:** sovereignty has **two dimensions**, not one:
1. **Placement / containment** — an entity stays within its approved zone (P4 today).
2. **Provenance / admission** — an entity, and the things that realize it, come from sources **approved for that boundary**: *did this server come from an approved source? is this firewall / image on the approved list for my zone?*

For **both**, UDLM's role is identical and bounded (ADR-008): **codify the requirement as immutable data and communicate it to whoever enforces. UDLM does not vet or enforce.** DCM (the Governance Matrix) gets the decisions made and enables enforcement; providers, backed by attestation and gated by accreditation, are the enforcement substrate.

## Context

The provenance-admission need is real and already partly built — but **scattered and not unified as sovereignty**:
- **Attestation R2** proves an entity's sovereignty is *backed* by evidence, but doesn't say *which sources are approved* for a boundary.
- **Accreditation** vets *subjects* (a provider, a peer), and **capability admission** (ADR-PROV-003) gates a provider's *capabilities* default-deny — both are admission gates, but neither is expressed as "this boundary admits only entities/sources on its approved list."
- P4 covers *where a thing may live*, never *whether its origin is admitted here*.

So the operator question "is this server/image/firewall from an approved source, on the approved list for my sovereignty zone?" has enforcement pieces but **no codified requirement in the data model to point them at**. This ADR unifies them under sovereignty's second dimension — **without new enforcement machinery**.

## Decision (proposed)

1. **Sovereignty = placement + provenance-admission.** Amend P4 to name both dimensions under the same "structural, not advisory" spine.
2. **UDLM codifies, does not vet.** UDLM carries the **approved-source / approved-list requirement as immutable data** on the sovereignty contract, and communicates it. It never decides admission and never enforces. (Same boundary P4 already keeps for placement: immutable fields in UDLM, Matrix enforcement in DCM.)
3. **Reuse, don't invent** (T7 — minimal custom surface). The requirement expresses **by reference** to what exists — accreditation subjects + attestation evidence — rather than a parallel primitive. UDLM adds the *pointer and the obligation*, not a new admission engine.
4. **DCM enforces.** The Governance Matrix decides "is this entity's provenance approved for this boundary?" at admission/realization, reusing accreditation + capability-admission (default-deny) + attestation R2 as the evidence.

## Data · Policy · Provider

- **Data (UDLM):** the codified sovereignty requirement — zone/classification (placement) **plus** the approved-source / approved-list expression (admission), as immutable, communicable data referencing accreditation subjects + attestation evidence records. UDLM holds it; it does not evaluate it.
- **Policy (DCM):** the Governance Matrix evaluates provenance-admission — approved source for this boundary? — and gates realization; reuses accreditation + capability-admission (default-deny).
- **Provider:** presents provenance/attestation evidence, is itself subject to accreditation, and enforces at the mechanism edge.

## Open questions for engineering (what this ADR tees up)

- **Field shape** for the approved-source/approved-list requirement: reuse accreditation subject refs + attestation (recommended), or a new sovereignty-scoped `approved_sources` list? Keep it a *reference*, per decision 3.
- **P4 amend vs new principle:** amend P4 (recommended — same structural spine) or a sibling P5?
- **Relationship to ADR-PROV-003** capability admission (default-deny): is provenance-admission the *same* gate viewed at the sovereignty layer, or a distinct one?
- **Rehydration interaction:** the RHY floor keeps sovereignty *current* on replay (four-states §5.3) — provenance-admission must **re-evaluate on rebuild**, not replay a stale approval.

## Consequences

- **Legibility:** sovereignty stops meaning only "where it lives"; the glossary already carries the fuller sense — this makes the spec match it (closes the glossary-vs-spec gap, single-source).
- **No new machinery:** the enforcement substrate (attestation, accreditation, admission) already exists; this unifies it under sovereignty and gives it a codified requirement to enforce against.
- **Boundary held:** UDLM gains a *data obligation*, not an enforcement role — consistent with P4's existing shape and ADR-008.

## Related

P4 (`cross-cutting-requirements.md`) · ADR-008 (boundary) · ADR-051 (identity/attestation) · ADR-PROV-003 (capability admission) · `accreditation.schema.json` · `realized-entity.schema.json` (R2) · ADR-041 (information firewall — the flow-control sibling) · `GLOSSARY.md` (sovereignty).
