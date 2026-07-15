# UDLM ADR-020: The Prod profile — hardened production

**Status:** Accepted (maintainer decision, 2026-07-15)
**Date:** 2026-07-15
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** ADR-007 (profile model); ADR-019 (standard — the floor this contains); ADR-010 (blast-radius/impact); ADR-006 (bounded convergence); ADR-011 (validate-and-reserve); ADR-017 (per-profile-ADR template); the record: `registry/instances/profile-prod.yaml`

> Owns the *rationale* for `prod`; the floor data is the record's (single-source, SPEC-DESIGN §33).

## Context

`standard` operates an estate correctly, but it does not defend against the two failure modes that hurt at scale: a change with a wider blast radius than the operator realized, and an unbounded retry/convergence loop. Hardened production needs change-control and bounded execution on top of steady-state operation.

## Decision

**`prod` is the hardened-production profile.** By set-containment it is `standard`'s floor **plus** blast-radius-aware change control and bounded execution (see the record for the authoritative list):

- **`policy/blast-radius-impact`** — changes are gated against the graph's blast radius (ADR-010): the operator sees, and policy can block on, what a change actually reaches.
- **`policy/dual-approval-destructive`** — destructive operations require a second approver (a human gate on irreversible actions).
- **`recovery/bounded-convergence`** (+ tighter dispatch timeouts) — retries are bounded with a terminal-failure surface (ADR-006), so convergence can't loop indefinitely.

Target demographic: production where a mistake is costly and change must be controlled — the posture most enterprises run steady state.

## Why these choices

- **Contain the mistake.** Blast-radius gating turns "I didn't know that would take X down" into a pre-change diagnostic policy can act on; dual-approval puts a human between intent and an irreversible act.
- **Bound the machine.** `bounded-convergence` guarantees a reconcile loop terminates — essential when the estate is large and a runaway retry is itself an incident.
- **Containment ladder.** `prod ⊃ standard ⊃ dev`; each is a strict floor-superset, so conformance comparisons stay a clean set-containment check (`profile-resolution.md §2`).
- **Floor is a minimum, not a filter** (ADR-007 §2). `prod` still doesn't *require* tamper-evident audit, attestation, or regulatory retention — those are the `fsi` direction — but every one remains available to switch on.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** `policy_profile` record, `is_builtin: true`, `approved: true`, `default: false`.
- **Policy (DCM):** blast-radius and dual-approval gates run on every applicable change; convergence is bounded per ADR-006.
- **Provider:** must honor the reserve/commit/release protocol under tighter timeouts (ADR-011); no attestation required yet.

## Consequences

- The recommended posture for non-regulated production at scale; the floor `fsi` regulates and `sovereign` further confines.
- Dual-approval and blast-radius gating add human/operational latency to destructive and wide-reach changes — by design.

## Options considered

- **(A) Make blast-radius/dual-approval part of `standard`.** Rejected: many production estates don't want a dual-approval gate; keeping it in `prod` lets `standard` stay the lighter baseline.
- **(B) Leave change-control entirely to org policy overlays.** Rejected: a *named* hardened posture (a floor teams can require by reference) is worth more than every org re-deriving the same set.
- **(C) [chosen] standard's floor + blast-radius impact + dual-approval-destructive + bounded convergence.**
