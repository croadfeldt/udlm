# UDLM ADR-019: The Standard profile — baseline production

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-007 (profile model); ADR-018 (dev — the floor this contains); ADR-017 (per-profile-ADR template); ADR-010 (drift/graph); the record: `registry/instances/profile-standard.yaml`; `docs/profile-resolution.md` (floors nest by set-containment)

> Owns the *rationale* for `standard`; the floor data is the record's (single-source, SPEC-DESIGN §33).

## Context

Between the evaluation floor (`dev`) and hardened/regulated production there is the common case: a real, non-regulated production estate. It needs more than `dev` guarantees — steady-state operation, not just a surface that runs the UCs — but not the change-control or compliance machinery of `prod`/`fsi`.

## Decision

**`standard` is the baseline production profile.** By set-containment it is `dev`'s floor **plus** the three things that separate "runs" from "operates" (see the record for the authoritative list):

- **`policy/governance-matrix`** — boundary enforcement on every DCM→Provider crossing, so provider interactions are governed, not implicit.
- **`policy/recovery`** — partial-realization and timeout handling, so a failed dispatch resolves deterministically.
- **`policy/drift-reconciliation`** (+ `discovery/scheduled`) — discovered-vs-realized drift is detected and remediated on a cadence.

Target demographic: a team running production workloads with no specific regulatory overlay.

## Why these choices

- **"Operate," not just "run."** The three additions are precisely the operational guarantees a production estate can't do without and an evaluation floor can skip — enforcement at the boundary, recovery from partial failure, and drift handling over time.
- **Containment keeps it honest.** `standard ⊃ dev`, so anything valid under `standard` is valid under `dev`; profiles compare by floor-containment (`profile-resolution.md §2`), and this is the first real rung of that ladder.
- **Floor is a minimum, not a filter** (ADR-007 §2). `standard` does not disable blast-radius gating, dual-approval, merkle audit, or attestation — it just doesn't require them. Raise them by config, or fork to require them (that is the `prod`/`fsi` direction, pre-composed).

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** `policy_profile` record, `is_builtin: true`, `approved: true`, `default: false`.
- **Policy (DCM):** governance-matrix now evaluates every crossing; drift + recovery policies run on the operational cadence.
- **Provider:** must support the discovery cadence that feeds drift; still no attestation/accreditation required.

## Consequences

- The default posture for non-regulated production; the base that `prod` hardens and `fsi`/`sovereign` regulate.
- Requires a discovery cadence to be provisioned (drift needs it) — a real operational prerequisite, checked at floor bring-up.

## Options considered

- **(A) Fold standard into dev (one production-ready default).** Rejected: it would force governance/drift/recovery onto evaluation, defeating `dev`'s low-friction purpose.
- **(B) Skip standard; jump dev → prod.** Rejected: many production estates don't need blast-radius change-control or dual-approval; `standard` is the honest middle set the ladder needs.
- **(C) [chosen] dev's floor + governance-matrix + recovery + drift reconciliation.**
