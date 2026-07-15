# UDLM ADR-007: Profile model — composed sets, floors, and fork-on-modify

**Status:** Proposed
**Date:** 2026-07-10
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `foundations/foundations.md` §Extensibility (profile scope note); `governance/governance-matrix.md` (profile-bound defaults); ADR-002 (adopt-by-reference); ADR-004 (provider capability declaration); ADR-005 (time-sync as a profile capability); ADR-006 (re-entrant policy); `contracts/policy-contract.md` (policy engine model)
**Tracking:** review of dcm #66 — "the human-approval/escalation ladder is organization-dependent"; and "are custom/admin-defined profiles a feature?"

## Context

Profiles were treated in places as a **linear ladder of levels** (minimal → standard → sovereign) and as "**policy defaults**." Both are too thin. Reviewing dcm #66 surfaced that the human-gate/escalation ladder is organization-dependent — which forced a precise statement of what a profile *is*, and whether operators can define their own.

## Decision

**1. A profile is a composed *set*, not a level.**
A profile is a named set of **policies + operational configuration + the required data/mechanics** that together ensure a deployment (and, later, a group) can meet the profile's intent. It is *not* a point on a severity scale — `sovereign` is not "more of" `standard`. Profiles are distinct sets that may overlay/compose; they are not ordered levels.

**2. Profiles set floors.**
A profile establishes the **minimum** required policies, configuration, and mechanics. Tenants/operators may restrict *further* (never below the floor). A profile guarantees the floor is present and operative.

**3. Built-in profiles are immutable; modification forks a custom profile.**
Built-in profiles are stable, referenceable, reproducible. **Any modification of a built-in profile produces a new *custom* profile** (copy-on-write); customization never mutates a built-in. This is the answer to "are custom profiles a feature?" — **yes, first-class**, and they are created by forking a built-in.

**4. Profile-governed mechanics are organization-dependent.**
Mechanisms like the **human-approval / escalation ladder** are defined by the profile (its operational config + policy set), not by a fixed platform ladder. Different organizations/profiles define different ladders. The platform provides the *mechanism*; the profile provides the *definition* — the same pattern as ADR-005 (time-sync) and ADR-004 (capabilities).

**5. Scope — platform-scoped now; finer scopes are mechanism-available but deliberately unpopulated.**
A profile is scoped to the **platform**: one resolved profile set per DCM instance. Finer scopes — per tenant / service / compliance domain / resource — are **group-scopable later** and the resolution mechanism for them already exists (`profile-resolution.md §1` precedence `resource_type → tenant → group → platform default`), but **below the platform default it is not populated**: an instance carries its one platform profile and no sub-scoped overrides. Available as mechanism, not populated as policy. See the profile-scope note in `foundations.md`.

*Why platform-scope now.* No release use case needs two profiles to coexist inside one platform, and enforcing per-scope floors is not free — every admission, placement, and policy decision would first have to resolve, compose, and verify *which* floor applies to *this* object (the machinery of `profile-resolution.md §2–§3`), and administration would have to reason about overlapping, composing floors. That is real cost in platform administration, implementation, and management for no present return. The precedence mechanism is kept dormant so a finer scope is a later switch-on, not a redesign.

*When a distinct profile is genuinely needed, prefer a separate instance.* Stand up a **separate DCM instance** for it rather than sub-scoping one platform — each instance's floor stays uniform and its conformance is trivially true. A **federated** DCM does *not* serve this: conformance is floor-containment (§2 — A satisfies B iff A's floor ⊇ B's), so when federated instances carry different profiles the looser instance is **non-conformant** to the stricter one, and federation across a profile boundary breaks the very guarantee the profile exists to make. The cost of separate instances (running more of them) is acceptable while distinct-profile needs are rare; revisit finer in-platform scoping only against a concrete multi-profile-in-one-platform need.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data** — the profile record: a set of policy references + operational configuration + declarations of the required data/mechanics; custom profiles as forked records; the floor declarations.
- **Policy** — the policies the profile bundles; the "may restrict, never below floor" composition rule; fork-on-modify enforcement; the org-defined approval/escalation ladder.
- **Provider** — the operational configuration names the mechanics providers must satisfy (e.g. an attestation provider for `sovereign`, a time-sync capability per ADR-005); placement/admission matches provider/node capability (ADR-004) against the profile's required mechanics.

## Options considered

- **(A) Profiles as levels** (minimal < standard < sovereign). Rejected: real deployments need distinct, composable sets, not one scale; `sovereign` differs in *kind*, not degree.
- **(B) Profiles as policy-only.** Rejected: a profile must also ensure the *mechanics and data* exist (attestation, time-sync capability, stores, retention), not just set policy defaults.
- **(C) Mutable built-in profiles.** Rejected: destroys the stable reference and reproducibility; fork-on-modify preserves both and keeps an audit trail.
- **(D) [chosen] Composed sets + floors + fork-on-modify custom profiles.**

*On scope granularity (§5):*
- **(E1) Author finer-scoped profiles now** (per tenant/provider/resource). Rejected for now: no use-case need, and per-scope floor resolution/composition + administration is real cost (§5).
- **(E2) Federate DCMs to host mixed profiles in one estate.** Rejected: differing floors make the looser instance non-conformant (§2 floor-containment); federation can't honor mixed floors.
- **(E3) [chosen] Platform-scope now; a separate instance per distinct profile.** Keeps each floor uniform and conformance trivial; the finer-scope precedence stays dormant for a later switch-on.

## Consequences

- **+** One profile bundles policy + config + required mechanics to *guarantee* intent (e.g. `sovereign` = FIPS/hardware attestation + tighter time-sync bound + audit retention + a specific approval ladder).
- **+** Custom profiles are first-class, reproducible, and auditable (fork-on-modify).
- **+** Human-gate/escalation ladders and other operational mechanics are organization-specific **without platform code changes** — the adaptability priority (`foundations.md`).
- **−** The profile record must reference operational configuration + required-mechanics, not only policies; placement/admission must verify a node/provider meets the profile's required mechanics (ADR-004/005).
- **−** Composition semantics (floor enforcement now; group-scope overlay later) must be specified as they land.
