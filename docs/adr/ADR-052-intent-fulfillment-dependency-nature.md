# UDLM ADR-052: Intent fulfillment — dependency nature and the convergence window

**Status:** Proposed (croadfeldt upstream) — 0.1 work; 1.0 conferred by engineering acceptance
(#217), not declared here; decided 2026-07-27
**Realized by:** `registry/realized-entity.schema.json` (`status.conditions[].type`) · `tests/check_fulfillment_conditions.py`
**Date:** 2026-07-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** This decision
assumes these; each is cited once with what it settles, not re-taught here. The design note it
ratifies: `docs/design/intent-fulfillment-model.md` (dependencies-with-a-nature + a convergence
window, and the complete permutation matrix). The corpus that measures it:
`use-cases/intent-fulfillment/` (nine UCs, mirrored to dcm `dav/use-cases/hammer-intent-fulfillment/`).
`docs/spec/principles/core-tenets.md` T7 (*extend before net-new*) — the tenet this is the worked
exemplar of. ADR-011 (validate-and-reserve) — the reservation law the request nature stands on.
`docs/spec/foundations/service-dependencies.md`, ADR-027 (`dependencies[].strength`) — the edge the new attribute
rides. ADR-048 (staleness verdicts derived, never stored) — the pattern the status classification
copies. ADR-008 — the substrate/implementation boundary.

## Context

An intent names things to bring about, and some cannot be realized the instant it is accepted — a
dependency isn't ready, capacity is momentarily absent, a sibling hasn't cleared policy. Two
questions had no ruled answer: **when a member cannot realize now, is it given up or allowed to
converge?** and **when members are coupled, does one member's fate bind the others?**

Early framings multiplied mechanisms — a `best_effort`/`all_or_nothing` axis, a three-outcome
cancellation dial, an `atomic` flag. Each dissolved into one reduction: **peer-atomicity is not a
flag — it is a dependency of a different nature.** What remains is *dependencies (each with a nature)
+ a convergence window*, built by extending the dependency edge the registry already ships. That is
the T7 exemplar; this ADR makes it contract. The design note's permutation matrix is the exhaustive
reference; the nine-UC corpus samples it and is engine-schema-valid and in-vocabulary. Corpus-first,
the corpus preceded this. The note left five calls to the maintainer; this ADR makes them.

## Decision

**1. The one new data point — `nature` on the dependency edge.** A dependency edge carries a
`nature`, one attribute on the *existing* `dependencies[]` edge — not a second edge family:

- **`operational`** — coupling at the **Realized** layer (*cannot function without* — a container
  needs its PVC). Directional; propagates at realization; on failure cascades *down* the operational
  chain while members off that chain proceed. Under it, today's `strength: hard|soft` means exactly
  what it means now — hard blocks the dependent, soft lets it converge degraded. Nature names the
  *layer*; strength names the *blocking behavior* at it.
- **`request`** — coupling at the **Intent/Requested** layer (*I want these as a unit* — ten VMs
  all-or-none). It binds at request time, yielding both atomic faces from one binding: held until the
  whole unit is satisfiable (hold-all) and cancelled together on any member's permanent failure
  (cancel-all). `strength` does not apply; the coupling is the unit.

Placement is ruled: one attribute on the single existing edge. A distinct Requested-layer edge was
considered and rejected — it reintroduces the parallel mechanism the reduction removed. `nature` is
the only new field.

**2. Convergence status is a derived projection, not a stored enum.** The seven outcomes —
`converging`, `blocked-transient`, `blocked-permanent`, `dependency-cancelled`, `realized`,
`refused`, `cancelled` — are the verdict vocabulary of a classification computed on read (the ADR-048
pattern), never a stored field, which keeps T3 intact (no new mutable state to police). It is a pure
function of `lifecycle_state`, each incoming edge's satisfaction, whether an unsatisfiable member is
transient or permanent, and the window; a blocked member inherits its dependency's verdict
transitively and the block cascades the chain. The seven are confirmed and complete; `cancelled`
(the request gave up) stays distinct from `dependency-cancelled` (cancelled because a dependency
was) — different provenance, and the surfacing contract (§4) must name the root.

**3. The default window is defer (converge); the give-up bound is control-plane policy.** The window `w` is an
intent field: `w=0` fail-fast, `w=N` converge-then-give-up, `w=∞` defer. Unstated, the default is
**defer** — converge-by-default removes toil, and it is safe here because surfacing is mandatory (§4)
so a deferring member is never silent (it reports `converging`/`blocked-transient` naming its root
the whole time). Fail-fast stays available explicitly; a profile may set a different default. UDLM
does *not* pick a wall-clock bound — a time value would violate T3 and is per-provider runtime — so
the `N` bound and what give-up executes are control-plane policy.

**4. The surfacing contract — name the root, always.** An unsatisfiable intent MUST be surfaced, not
left as a silent field. A transient block surfaces as a *warning*; a permanent refusal as a
*refusal-with-resolution*. Either MUST carry: (a) the **root** unsatisfied dependency (deepest
blocking node, not the immediate parent), (b) the **chain** to it, (c) the blocking edge's
**nature**, (d) the derived **verdict**; a refusal adds (e) the **resolution**. Reporting "container
failed" without naming the root PVC is insufficient (UC-008); a silent field-only partial is refused
(UC-009).

**5. The request/operational mapping is confirmed — the load-bearing reduction.** `request` =
intent-layer atomicity (hold-all/cancel-all from one binding); `operational` = realized-layer
functional coupling (directional cascade, independents proceed). Ratified as stated. No `atomic` flag
and no `best_effort`/`all_or_nothing` axis exists anywhere in either project.

## The UDLM / the control plane boundary (ADR-008)

| UDLM — data + contracts | The control plane — operationalize, via policies |
|---|---|
| the `nature` on the edge (`request`\|`operational`) — the one new field; `strength` (exists) | the reconciler walking the graph in convergence order (`reserve → recompute-dependents`, exists) |
| the derived convergence-status vocabulary (§2) and its computation | the cancellation / rollback / cascade execution; the window `N` value and cascade-vs-hold choice |
| the propagation semantics (operational cascades directionally; request couples the unit; soft never blocks) | evaluating the surfacing contract at runtime and emitting the warning/refusal |
| the surfacing contract (§4) + the window intent field with a `defer` default | reading window/nature off the intent and driving convergence to them |

Nothing here is new code: convergence is the existing `reserve → recompute-dependents` loop; the
request nature relies on ADR-011's reservation-distinct-from-activation; soft-degraded/partial reuse
the provider contract's `DEGRADED`/`partial_delivery`.

## Consequences

The portable model grows by exactly one attribute and one intent field; everything else is
derivation. Convergence status adds no stored state, so nothing new to keep consistent or cover for
tamper-evidence. And no transaction-semantics assumption is baked into the substrate — the deliberate
overrule the DAV precision fixture independently caught the analyzer making.

## What this does not decide

The control plane's policy defaults (the `N` value, cascade-vs-hold per domain) are the control plane's by the boundary; the
JSON-Schema shape of `nature` and the window field follows as an implementing PR against
`docs/spec/foundations/service-dependencies.md` once ratified.

## Status — 0.1

`udlm/0.1`; 1.0 is conferred by engineering acceptance (#217), not a date the maintainer picks.
`Proposed`. See `registry/VERSIONING.md` § "Spec status".
