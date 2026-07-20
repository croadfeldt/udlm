# ADR-031: 1.0 scope and focus — the 21 use cases as the gravity well

**Status:** Accepted (2026-07-19)
**Related:** the 21 September-release use cases; ADR-030 (the model beneath — a *post-1.0* direction); ADR-032 (how we hold the future while shipping); ADR-007 (profiles).

## Context

UDLM 1.0 (September) is surface-complete on `main`, and its concrete deliverable is the **21 September-release use cases** — all enabled at the UDLM layer, across the five built-in profiles. Rich model directions keep surfacing (the convergence lifecycle, Templates, the provenance axis, inventory). Without a scope rule they leak into 1.0 and slip the tag. This records the rule.

## Decision

**The 21 use cases are the sole gravity well for 1.0 implementation.**

- A change earns **1.0 surface** only if it enables one of the 21. Nothing else does.
- Everything else is one of exactly two things:
  - an **operational unblock** — justified on its own operational merit and kept *minimal* (e.g. reviving the inventory types, ADR-029, to unstrand the estate — the types + the optional module, nothing more), or
  - a **Proposed ADR** — a card on the table that records a direction and **binds nothing** (ADR-030, ADR-032, and the Templates ADR (ADR-033) are these).
- **Remaining to tag 1.0:** ratify the ready ADRs, meet conformance Tier-1 (or deliberately soften the bar), and restamp `0.1 → 1.0`. **No new model surface.**

## Data · Policy · Provider

n/a — this is a **scope / process** decision, not a data-model one. (The ADR README permits an explicit n/a; the model decisions this scopes carry their own D·P·P in ADR-030 and the type specs.)

## Consequences

- The tag is predictable: 1.0 = the 21 UCs + the ratify / conformance / restamp closeout.
- Design momentum isn't lost — it's parked in Proposed ADRs; ADR-032 explains how that keeps the future open at zero build cost.
- Operational needs (like the homelab estate) are still served, but through the *minimal-unblock* lane, never by expanding 1.0 surface.

## Alternatives considered

- **Fold the unified-lifecycle model / Templates into 1.0** — rejected: scope blowout and a migration before the tag.
- **Freeze all new thinking until post-1.0** — rejected: loses the groundwork; Proposed ADRs capture it now at no build cost.
