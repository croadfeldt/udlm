# UDLM ADR-042: Enable, don't mandate — opt-in standards governance without an approved-standards list (portability strictness is the consumer-gated illustration)

**Status:** Proposed (croadfeldt upstream) — records the **pattern**; the illustrating mechanism (a `neutrality`
property + a portability-strictness knob) is **consumer-gated — recorded, not built** — until a use case pulls it
(ADR-032: pay to remove a future-contradiction, never pre-build a feature).
**Date:** 2026-07-22
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** This decision sits on the standards-adoption mechanism
([`adopted-standards.md`](../../design-principles/adopted-standards.md) — the `adopts[]` / `adopted_standard_support`
absorb/embed/adopt dispositions) and the **existing** per-standard record
([`standards-adoption-register.md`](../../registry/standards-adoption-register.md), rule `ADOPT-001`), whose
`Body:` field already names each standard's **governing body** — the signal `neutrality` derives from. The
evaluation rides the policy firewall ([ADR-041](ADR-041-policy-information-firewall.md)); the neutral-vs-provider
trade-off is the same **portability-by-scope** it has in the data-element domain
([ADR-038](ADR-038-scoped-resource-type-classes.md)). Putting the *stance* in a profile rather than the data
applies the established **strictness-is-Policy** pattern ([ADR-025 §6](ADR-025-resource-references.md),
[`DPO-001`](../../design-principles/design-priorities.md)); *deriving* the property rather than storing it follows
[ADR-027](ADR-027-entity-family-model.md)'s addendum discipline. The **DCM realization** belongs on the
control-plane side — **DCM ADR-021** (adopting external standards) + `adopted-standards-dcm.md`. Throughout,
[core-tenets **T5**](../../design-principles/core-tenets.md) (adopt outward) and the standing directive: UDLM is an
**enablement** substrate, not an arbiter.

**Settles:** the **pattern** for adding an *opt-in* governance capability over adopted standards **without UDLM
shipping an approved-standards list or mandating one answer**: (1) derive a **descriptive** property of the
standard from data UDLM already holds; (2) let **policy evaluate** it at the adoption boundary (ADR-041); (3) let
an **org profile set the stance**, scoped to its own estate. **UDLM describes the standard; the org decides for
itself.** The concrete illustration — a `neutrality` property + a portability-strictness stance
(`off`/`warn`/`deny`) — **demonstrates** the pattern but is **consumer-gated: recorded, not built, until a use
case asks.**

## Context

The design question: an org may want to steer its estate toward vendor-neutral standards (for portability), but
**UDLM cannot and must not mandate that on anyone** — authorities author under their own authority (ADR-038), and
adopting a provider-native standard is a legitimate choice. So how do you offer the governance *option* without
UDLM deciding for everyone?

The trigger was an **observation, not a demand**: a type's `adopts[]` (adopted-standards.md §3.1) may reference a
**vendor-neutral** standard (Redfish, FOCUS, OSV — a portable join-key) or a **provider-native** one (KubeVirt,
vSphere — no portability when carried on the type). `Compute.VM` adopting KubeVirt at type scope is real, and it
silently shrinks the portable subset. Surfacing that could help a portability-strict estate — but **no consumer
is asking for it today.**

The instinct to make it a governance/profile item hits a trap: enforcing it seems to require an
**approved-standards allowlist** — UDLM deciding *for everyone* (who curates it? whose list?), which is exactly
the top-down mandate we reject. This ADR records how to avoid that trap; it does **not** build the feature.

## Decision

### The pattern — what this ADR settles

To make a governance stance over adopted standards **opt-in without UDLM deciding for everyone**, split it into
**fact / mechanism / stance** — no layer ships an allowlist or a mandate:

1. **Fact — a *derived, descriptive* property of the standard.** Compute a property *about the standard itself*
   from data UDLM already holds (adopt-by-reference) — never a hand-curated allowlist, never an assessment of
   anyone's adoption. **Derive, don't store** (ADR-027 addendum).
2. **Mechanism — policy *may* evaluate it (ADR-041).** The adoption is an authoring/ingress crossing; the firewall
   *can* evaluate the property there. UDLM ships the **ability**, never a rule that fires by default.
3. **Stance — the org's profile sets it.** The org dials the response for **its own estate** — the established
   **strictness-is-Policy** pattern (ADR-025 §6 / `DPO-001`): the stance is a **profile dial, never a data field.**

**The line:** UDLM **classifies / describes** the standard; the **org governs its own estate.** An
approved-standards *list* is UDLM mandating one answer for everyone; a *derivable property + a profile knob* is
each org governing itself. It reuses the ADR-041 firewall + the profile mechanism — no new primitive.

### The illustration — `neutrality` + portability strictness (consumer-gated, unbuilt)

Applied to the case that prompted this:
- **Fact:** `neutrality` — a standard governed by a **multi-vendor / open body** (DMTF, FinOps, OpenSSF, IETF) is
  `vendor-neutral`; one owned by a **single vendor / project** (KubeVirt, vSphere) is `provider-native`. Read off
  the **`Body:`** already recorded per standard in the adoption register (Related); `unknown` when absent.
- **Mechanism:** evaluate `standard.neutrality` + the scope it sits at (type surface vs the provider's
  `adopted_standard_support`) at the `adopts[]` crossing.
- **Stance:** portability strictness — `off` (default; adopt anything) / `warn` (surface a provider-native adopt
  at type scope) / `deny` (reject it) — scoped to the org's estate.

> **Consumer-gated — recorded, not built.** No use case pulls this today; it came from an observation (KubeVirt on
> `Compute.VM`), not a demand. Per **ADR-032** ("pre-1.0, pay only to remove a future-contradiction, never
> pre-build a feature"), we record the *pattern* — which removes the future contradiction of someone hard-coding
> an allowlist or a global prohibition — and **do not build** the `neutrality` derivation or the profile knob
> until a use case (e.g. a sovereign / exit-strategy estate that must stay portable across providers) asks.

## Consequences

- **The decision recorded is the *pattern*, not a feature.** Nothing is built; default behavior is unchanged
  (adopt anything; nothing is a "finding").
- The best-practice ("*for portability*, prefer vendor-neutral standards at type scope") stays **documented
  advice**; the pattern is *how* a strict estate would later opt into enforcing it **on itself** — once a UC
  exists.
- **When a consumer appears**, nothing new is invented: `neutrality` derives from the register's existing `Body:`
  (no new store); the stance is a profile setting; the DCM realization is control-plane (**DCM ADR-021**, Related)
  — evaluate at the contribution pipeline. **No new rule family, no new primitive, no new store** (defines no
  `PREFIX-NNN` rules).
- **If no consumer ever appears**, the ADR still earns its keep: it prevents the recurring wrong-turn (an
  approved-standards list / global prohibition) by recording why that is not the shape.

## Alternatives considered

- **UDLM ships an approved-standards allowlist / prohibits provider-native `adopts[]` globally** — rejected: UDLM
  mandating one answer for everyone; unanswerable "whose list?"; overrides legitimate authoring choices (VMs are
  commonly KubeVirt); the exact trap this ADR exists to avoid.
- **Build the `neutrality` derivation + profile knob now** — rejected: no use case pulls it (**ADR-032** — don't
  pre-build). Record the pattern; build when a consumer asks.
- **Store `neutrality` as an authored per-standard flag** — rejected in favor of deriving it from the recorded
  governing body (derive-don't-store; a hand-set flag drifts and reintroduces the curation/assessment burden).
- **Do nothing — no ADR** — rejected: the allowlist trap kept recurring in discussion; recording the
  enable-don't-mandate resolution is the future-contradiction this pays to remove.
