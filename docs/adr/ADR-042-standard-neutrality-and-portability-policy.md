# UDLM ADR-042: Standard neutrality as a derived property + a profile-dialed portability policy — enable, don't mandate

**Status:** Proposed (croadfeldt upstream)
**Date:** 2026-07-22
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related:** ADR-041 (policy as information firewall — the boundary the standards-adoption crossing rides);
ADR-038 (scoped-Class paradigm — portability by scope, the same trade-off in the data-element domain);
`design-principles/adopted-standards.md` (`adopts[]` / provider `adopted_standard_support`, the *absorb / embed /
adopt* dispositions); ADR-025 (DCM realization); core-tenets **T5** (adopt outward) — and the standing directive
that UDLM is an **enablement** substrate, not an arbiter.

**Settles:** how UDLM steers `adopts[]` toward vendor-neutral standards **without mandating a choice on an authority
and without shipping an approved-standards list.** It ships neither a global allowlist nor a prohibition. Instead
a three-layer split — **fact / mechanism / stance**: (1) a standard's **`neutrality`** is a *descriptive,
derivable* property read off its **governing body**, not an assessment; (2) **policy may evaluate** that property at
the authoring/ingress crossing (ADR-041 firewall); (3) an **org profile dials** the stance — `off` (default) /
`warn` / `deny` — scoped to that org's own estate. **UDLM classifies the standard; the org governs its own
estate.**

## Context

A type's `adopts[]` (adopted-standards.md §3.1) references an external standard by identity + version. That
standard may be **vendor-neutral** (Redfish, FOCUS, OSV — a portable conformance join-key) or **provider-native**
(KubeVirt, vSphere, EC2 — no portability when carried on the type). A provider-native standard on a *portable
type* buys no portability and biases the substrate toward one ecosystem — a real trade-off worth surfacing.

But **UDLM cannot and must not override an authority's choice** to adopt one. Authorities author under their own
authority (ADR-038); an implementation will make vendor-specific choices, and that is legitimate. An earlier
"audit + relocate provider-native `adopts[]`" framing was **closed as the wrong shape** — it treated a valid
authoring choice as a defect. The principle: **we enable and describe; we don't mandate a choice on an authority — document best practice, don't impose it.**

The instinct to make the trade-off a *governance/profile* item then hits a trap: enforcing it seems to require an
**approved-standards allowlist** — which is UDLM deciding *for everyone* (who curates it? whose list?), returning
to exactly the top-down mandate we rejected. This ADR resolves that.

## Decision

Split the one conflated "approved list" into **fact**, **mechanism**, and **stance** — no layer is UDLM mandating one answer.

### 1. Fact — `neutrality`, **derived** from the standard's governing body
A standard governed by a **multi-vendor / open body** (DMTF, FinOps Foundation, OpenSSF, IETF, OASIS) is
`vendor-neutral`; one owned by a **single vendor or project** (KubeVirt, vSphere, EC2) is `provider-native`. This
is **read off the `source` / governing-body already carried in the `adopts[]` entry** — descriptive metadata
*about the standard* (adopt-by-reference), **not a curated allowlist and not an assessment of any adoption.**
- **Derive, don't store** (ADR-027 addendum discipline): `neutrality` is *computed* from the standard's
  governance, not a hand-set flag that drifts and re-imports the curation/assessment problem.
- Where the governing-body signal is absent, `neutrality: unknown` — the profile decides how to treat unknown
  (default: allow).

### 2. Mechanism — policy **may** evaluate the property (ADR-041)
Adopting a standard is an **authoring / ingress crossing**; the policy firewall (ADR-041) can evaluate
`standard.neutrality` **and the scope it sits at** (type surface vs the provider's `adopted_standard_support`) at
that crossing. UDLM ships the *ability* to evaluate — never a rule that fires by default.

### 3. Stance — the **org's profile** dials it
A profile declares the org's **portability strictness** for **its own estate**:
- **`off`** — default. Pure enablement: adopt anything, anywhere. UDLM's out-of-the-box posture.
- **`warn`** — surface a provider-native standard adopted at type scope (advisory signal, no block).
- **`deny`** — reject a provider-native adoption at type scope in this estate.

The setting is **opt-in and org-scoped**. UDLM ships **no default mandate**; a strict-portability org dials it up,
and everyone else is unaffected.

### The line that keeps this out of the trap
**UDLM classifies the standard (describes it, from its governance); the org governs its own estate (opt-in
profile).** An approved-standards *list* is UDLM mandating one answer for everyone. A *derivable property + a
profile knob* is each org governing itself. Classification is a description of the standard; the stance is the
org's to set. It reuses the ADR-041 firewall machinery (a policy
reading a property at a boundary), not a new primitive.

## Consequences

- **No global allowlist, no prohibition.** The default posture is adopt-anything; nothing is a "finding."
- The best-practice ("*for portability*, prefer vendor-neutral standards at type scope; native ones on the
  provider surface") stays **documented advice**; the profile is how a strict org *chooses* to enforce it **on
  itself**.
- `neutrality` needs a governing-body signal; it is `unknown` when absent, and profiles treat unknown per their
  own stance (default allow). Deriving it (not storing) means it stays correct as the register grows.
- Reuses ADR-041 (firewall) + the existing profile mechanism — **no new rule family, no new primitive.** This ADR
  records a capability and a stance, and defines no `PREFIX-NNN` rules.
- A **DCM realization companion** may follow: evaluate the property at the contribution/authoring pipeline
  (ADR-025 / `contribution-pipeline.md`), and expose `portability_strictness` as a profile setting.

## Alternatives considered

- **UDLM ships an approved-standards allowlist / prohibits provider-native `adopts[]` globally** — rejected: UDLM
  mandating one answer for everyone; unanswerable "whose list?"; overrides legitimate authoring choices (VMs are
  commonly KubeVirt); the exact trap this ADR exists to avoid.
- **Store `neutrality` as an authored per-standard flag** — rejected in favor of deriving it from the governing
  body: a hand-set flag drifts and reintroduces the curation/assessment burden (derive-don't-store).
- **Do nothing — best-practice doc only** — this *is* the default (stance `off`); the ADR adds only the *opt-in
  enforcement path* for orgs that want it, changing no default behavior.
