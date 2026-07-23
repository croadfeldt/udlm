# UDLM ADR-018: The Dev profile — the evaluation / co-engineering target

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-007 (profile model — composed set + floor); ADR-017 (the homelab profile + the per-profile-ADR template this follows); the record: `registry/instances/profile-dev.yaml`; `docs/profile-resolution.md`; `../../registry/UDLM-0.1-SCOPE.md` §2 (profile posture — implement against dev)

> Owns the *rationale* for `dev`; the floor data is the record's (single-source, SPEC-DESIGN §33).

## Context

UDLM 0.1 has to be *built and evaluated* before any production floor is implemented. That work needs a profile whose floor is small enough to exercise the 21 release use cases end to end without standing up governance ceremony, attestation, or an attested clock first — but on the **same** architecture, types, and wire contracts as every production profile, so nothing learned against it is throwaway.

## Decision

**`dev` is the default profile and the September implementation / evaluation target.** Its floor is the smallest that still runs the release UCs: structural validation, single-tenant ownership, resolved-profile evaluation, append-only audit, four-state tracking, the three stores, and causal-only time (see the record for the authoritative list). No governance-matrix, no attestation, no drift/recovery mandate — those are exercised by the higher profiles.

`dev` is a floor to **test against**, not a posture to live on; its lived-on sibling is `homelab` (ADR-017), which shares the small substrate but pre-tunes the operational capabilities for a real home estate.

## Why these choices

- **Provable, not throwaway.** Because the architecture and wire contracts are identical across profiles (the ADR-007 invariant), validating the 21 UCs against `dev` validates them for every profile — only the required floor differs.
- **Lowest friction to the value.** An engineer can exercise the full model — resource types, the dependency graph, four-state, policy resolution — with no attestation provider or governance overlay to configure.
- **Floor is a minimum, not a filter** (ADR-007 §2). `dev` does not *disable* governance-matrix / merkle audit / attestation; it simply does not require them. Any of them can be turned on, or made required by forking (the custom-profile path).

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** `dev` is a `policy_profile` record, `is_builtin: true`, `approved: true`, **`default: true`** — the one profile that resolves when nothing more specific is selected.
- **Policy (DCM):** resolves `dev` as the platform default; its small floor is the minimum every request is evaluated against.
- **Provider:** need only satisfy `dev`'s small `required_mechanics` (three stores + causal time); no attestation or accreditation is asked of a provider under `dev`.

## Consequences

- The 21 UCs are built and validated against `dev`; the tag's conformance claim rests on it.
- `dev` remains the resolution default; adopting any other profile is an explicit operator choice (`homelab`, `standard`, …).
- Establishes the "test against dev, live on homelab/standard/…" split that the other profile ADRs build on.

## Options considered

- **(A) No default profile — require an explicit choice.** Rejected: a default is needed for the out-of-box path and the September evaluation target; `dev` is that default.
- **(B) Make `dev` the lived-on home profile too.** Rejected: evaluation and daily home operation are different intents — `dev` is a throwaway eval floor; `homelab` (ADR-017) pre-tunes the operational capabilities a real estate wants on.
- **(C) [chosen] A minimal default floor that runs the 21 UCs on the shared architecture.**
