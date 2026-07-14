# Research: sovereignty attestation & enforcement — prior art

**Type:** research note (decision support — not normative)
**Date:** 2026-07-14 · **Method:** three-stream prior-art review (identity/attestation; sovereign-cloud/federation; authorization/admission), each claim checked against primary sources.
**Feeds:** `governance/accreditation-and-authorization-matrix.md` §3.7–§3.10, `registry/accreditation.schema.json`, `registry/provider-adopted-standards.schema.json` (`conformance_claims` + `enforcement_plane`), ADR-004 §4/§4a, `registry/standards-adoption-register.md` (Attestation section).

## What this settles

I built the accreditation model — providers **declare** a sovereignty stance (a claim), accreditors **attest** it, and trust requires a **1-1 match** between claim and attestation on provider × capability × jurisdiction — before checking it against how the rest of the world does this. This note records that check. The verdict: the spine is sound and matches independent prior art; five gaps needed closing; the fix in every case was to **adopt an existing vocabulary, not invent one**. It exists so nobody re-runs the survey, and so each field name in the schema has a citation behind it.

**Bottom line:** the model is fundamentally correct. The three-party spine (claimant → attester → relying party), the exact-match trust gate, and per-hop re-attestation down the pipeline each independently reproduce a deployed standard. What was missing was verifiability, the data-plane/control-plane split, jurisdiction subsumption, a conformance register, and a delegation dial — all closed additively.

## Streams reviewed

**Identity & attestation** — W3C Verifiable Credentials 2.0 (issuer/holder/subject/verifier, `proof`, `credentialStatus`, `validFrom/validUntil`); IETF RATS RFC 9334 (Attester/Verifier/Relying-Party, Evidence→Attestation-Result→policy, Passport vs Background-check); NIST OSCAL/FedRAMP (SSP self-assertion → assessment → ATO, authorization-boundary, leveraged-authorization, POA&M); SLSA + in-toto (per-link MATCH, VSA); SPIFFE/SPIRE (short-lived attested workload identity).

**Sovereign cloud & federation** — Gaia-X Trust Framework (self-descriptions as provider-authored VCs, GXDCH clearing, Trust Anchors, Label Levels L1/L2/L3); EUCS assurance levels; hyperscaler sovereign clouds (AWS European Sovereign Cloud, Azure sovereignty, Google EKM + Key Access Justifications, Oracle sovereign regions) — the recurring pattern is **separate operator-access controls from data-residency controls**.

**Authorization & admission** — IAM permission-boundaries, OAuth scopes, RAR (intersection semantics — the thing our model deliberately does *not* do for sovereignty); OPA/Kyverno admission (policy-as-code at the gate); ISO 3166 (jurisdiction containment hierarchy); eIDAS (qualified trust-service providers as real-world credential issuers).

## The five gaps and how each closed

1. **Verifiability — accreditations were unsigned assertions.** Closed by making an accreditation a **verifiable credential**: `proof` (accreditor signature) + `trust_anchor` (CAB / eIDAS TSP / government registry / DID / X.509), field-named after W3C VC. DCM verifies the signature and chains to the anchor *before* it appraises scope. (matrix §3.7; W3C VC + RATS Endorsement.)

2. **Data-plane vs control-plane — the universal leak.** Every sovereign-cloud offering I reviewed splits *who can operate/see telemetry* (control plane) from *where the bytes rest* (data plane); a single "sovereign" bit conflates them. Closed with `enforcement_plane` (`data` | `control` | `both`) on both the provider stance and the accreditation scope, matched exactly. UDLM/DCM is a **declaration-and-placement layer, not a byte enforcer** (Gaia-X's own posture) — so for a data-plane requirement DCM **conveys the requirement + execution-slice to the enforcing provider and verifies that provider's data-plane attestation**; the provider enforces residency of the bytes. (matrix §3.8.)

3. **Two-gate decision was implicit.** RATS separates *verification* (is the evidence authentic?) from *appraisal* (does it satisfy policy?); VC separates *verification* from *validation*. I had folded both into "does it match." Closed by making the two gates explicit and independently-failing: **(1) cryptographic verification** of proof/anchor/status/currency, then **(2) scope appraisal** (the 1-1 match). A forged-but-in-scope credential and a genuine-but-out-of-scope one are different failures. (matrix §3.7.)

4. **Residency vs sovereignty — jurisdiction had no hierarchy.** A US accreditation should cover a US-Minnesota *residency* requirement (containment) but a Minnesota *sovereignty regime* is a distinct authority that must be matched exactly. Closed by keying `geographic_scope` to the **ISO 3166 hierarchy**: residency **subsumes** down the tree (country covers subdivision); a sovereignty regime is **exact**. (matrix §3.8.)

5. **Delegation — no way to say "someone I trust already verified this."** SLSA VSA and OSCAL leveraged-authorization both formalize a verifier emitting a summary others rely on. Closed with a **verification summary / attestation result** (RATS Passport model) carried forward, plus a delegation dial that profiles set — off for sovereign/fsi, permitted for lower tiers. (matrix §3.9.)

**Bonus — conformance register.** Gaia-X self-descriptions and OSCAL SSPs are both "provider declares which standards it adheres to, self-asserted until assessed." I generalized the sovereignty claim→attestation escalation into `conformance_claims[]` (framework + optional level/statement) on the provider declaration: a declared framework is self-asserted until an accreditation attests it — the same two-tier shape, one axis wider. (matrix §3.7; ADR-004 §4a.)

## Why the spine was already right

- **Three-party spine.** Claimant → attester → relying party is VC's issuer/subject→holder→verifier and RATS's Attester→Verifier→Relying-Party. I had provider → accreditor → DCM-placement-gate. Same shape, independently.
- **Exact match, not intersection.** OAuth/RAR grant the *intersection* of requested and permitted scope. Sovereignty must not: partial credit on a residency claim is a compliance breach. The **1-1 match with no intersection credit** is the correct and deliberate divergence — and it matches in-toto's per-link MATCH and GDPR sub-processor chains, not IAM.
- **Per-hop re-attestation.** Trust is re-checked at every hop down the fulfillment graph and **never inherited** — only the *constraint* propagates, the *attestation* is fresh each hop. This is in-toto's layout MATCH and the zero-trust/GDPR sub-processor rule, reproduced in ADR-009/010/011's propagate-then-prove-at-the-barrier design.

## Adopt, absorb, or reject

I take **vocabulary** from W3C VC (`proof`, `verification_method`, `proof_purpose`, `trust_anchor`) and ISO 3166 (jurisdiction codes + hierarchy); I take **patterns** from RATS (two-gate, Passport), OSCAL (declare→assess→authorize, bounded, leverageable), Gaia-X (self-description + trust anchor + label levels), and SLSA/in-toto (per-hop match, VSA). I **reject** absorbing wire formats and machinery — no JSON-LD `@context`, no EAT/CoRIM tokens, no OSCAL catalog format, no Gaia-X credential-event service. Adopt-not-absorb: the model stays legible to anyone who knows these standards without inheriting their transport. The full field-by-field cross-walk is matrix §3.10; each adoption is registered in `standards-adoption-register.md`.

## Open follow-ons

- **TODO #24 — credential referencing / reference-passing.** A `Security.CredentialRef` carried in the reserve/commit dispatch as role:execution data (never the secret itself). SPIFFE/SPIRE is the reference model.
- **TODO #25 — just-in-time credentials.** Short-lived credentials issued at the reserve/commit barrier (SPIFFE-SVID-like), so a provider holds a secret only for the window it acts. Follows #24.
