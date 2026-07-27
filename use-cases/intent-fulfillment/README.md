# intent-fulfillment — how a multi-resource intent is fulfilled, converged, and surfaced

Nine cases (5 expected-work, 2 boundary/failure, 2 must-reject) for the **intent-requirement**
side of the platform — what happens when a declared multi-resource intent cannot be fully
satisfied at once. Surfaced by a DAV fixture review (2026-07-27) and ruled by the maintainer.

The model, in one breath: **intent is persistent desired state** (the `Intent` lifecycle_state),
the platform **converges toward it** (the existing reconciliation loop, `reconciliation.participates`),
and a not-yet-realized member is either **pending** (transient — keeps converging, k8s-style) or
**refused** (permanent — needs the intent to change). That classification, not a partial/complete
binary, drives everything.

- **Fulfillment policy is consumer-declared** (009), default `best_effort`: converge what you can,
  hold the rest, surface the shortfall. `all_or_nothing` (002) is a **readiness barrier** —
  **deferred atomic activation**, not a fail-fast transaction: it waits (converges) through
  transient blockers, then commits every member at once; a permanent refusal on any member blocks
  the whole intent immediately (005).
- **Surfacing is mandatory** (001, 008): an unsatisfiable intent must reach the consumer as an
  actionable warning — what was not realized, why, how to resolve — never only a missable
  `partial_failures` field. A field is not a signal.
- **The boundary** (006, 007): partial fulfillment of *independent* members is correct-with-a-warning;
  partial fulfillment that *breaks a hard dependency* is a failure. Dependents inherit their
  dependency's classification (held while transient, refused if permanent) — never realized dangling.

Contracts here are proposed pending the intent-fulfillment ADR; the corpus measures the decisions
first. Grounded in `lifecycle_state` (Intent→Requested→Realized), ADR-011 (validate-and-reserve),
the reconciliation loop (four-states §7.6), and `DEGRADED`/`partial_delivery` (provider-contract).
