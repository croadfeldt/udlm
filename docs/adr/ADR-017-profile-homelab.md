# UDLM ADR-017: The Homelab profile — the single-operator on-ramp

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-007 (profile model — a profile is a composed *set* with a *floor*, built-ins immutable, fork-on-modify; §5 platform-scope + why); `docs/profile-resolution.md` (resolution, floor-containment, atomic onboarding §5); the record this ADR governs is `registry/instances/profile-homelab.yaml`; sibling profile records `registry/instances/profile-{dev,standard,prod,fsi,sovereign}.yaml`
**Tracking:** "map a homelab profile for UDLM 1.0 to run at home" — the first of the per-profile ADRs (dev/standard/prod/fsi/sovereign to follow, same template).

> This ADR owns the **rationale** for the homelab profile — its intent, target environment, and *why* its floor is what it is. The concrete floor/mechanics/config are the record's (`profile-homelab.yaml`); this document does not restate them (single-source, SPEC-DESIGN §33).

## Context

ADR-007 fixed *what a profile is* (a composed set with a floor) and shipped five built-ins aimed at the product's evaluation-through-regulated spectrum (`dev → standard → prod → fsi/sovereign`). None of them targets the audience that most naturally adopts an open estate model first: **the single operator running a self-hosted lab.** `dev` is close but is framed as the *evaluation/co-engineering* target (a throwaway floor to exercise the UCs), not a posture someone *lives on* day to day.

## Decision

**Ship `homelab` as a sixth built-in profile: the single-operator on-ramp.** Its explicit goal is **pure value for the individual user — easy to adopt, easy to configure — to build community and gather feedback.** It is the profile a homelabber sets and keeps.

The design follows two rules that make it an on-ramp rather than a stripped-down mode:

1. **Smallest floor that still delivers the headline value.** The guaranteed substrate is deliberately `dev`-sized — structural validation, single-tenant ownership, resolved-profile evaluation, append-only audit, four-state tracking — because four-state + the dependency graph are what power the demo that sells UDLM at home: ordered shutdown/startup, drift visibility, rehydration. Nothing heavier is *required* to get that.
2. **Nothing is shut off; the optional capabilities are pre-tuned and one toggle away.** A profile floor is a *minimum*, not a filter (ADR-007 §2). Homelab does **not** remove governance-matrix, attestation, merkle-transparency audit, or approval gates — every capability the production profiles require stays fully available. Homelab simply does not *mandate* them, and its `operational_config` pre-tunes the operational ones (drift/recovery/discovery **on** at low ceremony; governance-matrix **advisory**; approval ladder **none**; merkle/attestation **off**) for a home environment. Raising any of them to production-grade is a value change, not a profile change — and forking homelab to make one floor-*required* is the documented custom-profile path (DCM how-to).

## Why these choices

- **On-ramp, not a rung.** `homelab` is a sibling of `dev`, not a level on the production ladder. By floor-containment (`profile-resolution.md §2`) it is not "below `standard`" — it is a distinct set: a small substrate with operational capabilities turned on by *config* rather than mandated by *floor*. This is exactly the "composed sets, not levels" tenet (ADR-007 §1).
- **Value first.** Everything a single operator would find delightful (see your whole estate's dependency graph, get a correct shutdown order, notice drift, rebuild from intent) is available with no attestation provider, no dual-approval, no atomic clock, no governance ceremony to stand up first.
- **Growth path is honest.** Because nothing is disabled, a homelab that grows into wanting enforcement doesn't migrate to a different product surface — it flips config values, or forks homelab into a custom profile that mandates them. Same architecture, types, and wire contracts throughout (the ADR-007 invariant).

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** `homelab` is a `policy_profile` record (`profile-homelab.yaml`), `is_builtin: true`, `approved: true`, `default: false` (dev stays the September default). Small floor; the optional capabilities live in free-form `operational_config`.
- **Policy (DCM):** homelab resolves as the platform profile when an operator sets it; the low-ceremony `operational_config` values are the profile-layer defaults (ADR-015 config bundles), overridable per-request without leaving the profile. "Restrict further, never below floor" still holds.
- **Provider:** a provider need only satisfy homelab's small `required_mechanics` (the three stores + causal time). Providers that *can* offer more (attestation, etc.) are matched only if the operator opts in — the capability advertisement is unchanged (ADR-004).

## Consequences

- A self-hoster can adopt UDLM/DCM with a one-line profile choice and get the headline value immediately — the intended community/feedback flywheel.
- The homelab floor is a stable, referenceable baseline that custom profiles fork from (the canonical worked example in the DCM custom-profile how-to).
- `homelab` is a sixth built-in; the 1.0 scope profile set and `profile-resolution` examples include it. It does not change any wire contract or the September `dev` default.
- **Establishes the per-profile-ADR pattern:** each built-in profile gets an ADR owning its intent + floor rationale, referencing its record for the data. `dev/standard/prod/fsi/sovereign` ADRs follow on this template.

## Options considered

- **(A) Just tell homelabbers to use `dev`.** Rejected: `dev` is framed as the throwaway evaluation floor, and it doesn't pre-tune the operational capabilities (drift/recovery/discovery) a real home estate wants on. Homelab is a posture to *live on*, not to test against.
- **(B) Make homelab a thin strip-down that disables enterprise capabilities.** Rejected: violates "don't shut off capabilities" — it would break the honest growth path and the single-architecture invariant. Small *floor* + available-and-pre-tuned optionals is the correct shape.
- **(C) [chosen] A sixth built-in: small floor, capabilities pre-tuned and one toggle away.**
