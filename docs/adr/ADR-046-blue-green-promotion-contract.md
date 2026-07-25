# UDLM ADR-046: The blue/green promotion contract — typed-output diff as the gate, evidence to attestation

**Status:** Proposed (croadfeldt upstream) — rulings decided in-session 2026-07-25; engineering ratifies (#217 discipline)
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** The pin lifecycle this completes (ADR-045
— organizational pins are legal enumerated debt; this contract is how the debt retires), the
binding surface it diffs ([D8.3] — declared typed outputs, the only comparable realization
facts), the migration pattern it generalizes (the Process-family engine-swap render — the same
machinery serves provider swap and class upgrade), the evidence pipeline it feeds (validation
results as signable attestation input, per the model-health emission), and the corpus that
measures it ([`use-cases/class-versioning/`](../../use-cases/class-versioning/README.md) 007
and 008).

## Context

ADR-045 gives organizations complete pin control with visible debt. Debt must be retirable
without a leap of faith: "the upstream change is compatible" is a claim, and claims about
someone else's estate deserve evidence, not trust. The evidence exists deterministically —
every realizable type declares typed outputs, and two compilations of the same intent are
mechanically comparable on them.

## Decision

**Re-pins promote on evidence, not version claims.** The contract:

1. **Two compilations, one corpus, one corpus ref.** The organization's intent corpus
   compiles under blue (the pinned class revisions) and green (the candidate revisions) side by
   side — at the **same recorded corpus ref**. A corpus that moved between the two compilations
   voids the comparison; the evidence record carries the ref.
2. **Dry-run realization, typed-output diff.** Both sides realize in dry-run; their declared
   typed outputs — never provider internals — are diffed mechanically. Outputs declared
   **volatile** (timestamps, generated identifiers) are excluded by declaration, never ad hoc,
   so non-determinism cannot manufacture perpetually-dirty diffs. When the changed axis is the
   provider itself and green cannot dry-run, promotion routes through a staged environment —
   the P1 pilot defines that path. The diff is the entire promotion gate: empty, or every
   difference explicitly reviewed and approved.
3. **Promotion is atomic and evidenced.** On a clean-or-approved diff the pins advance, the
   ADR-045 debt entries close, and the diff plus approvals are preserved as the promotion's
   audit evidence — attestation input, same discipline as the registry's model-validation
   artifact.
4. **A dirty diff refuses and reports upstream.** Promotion is refused with the diff as the
   typed reason; the estate stays fully on blue — nothing partially promotes. The refused diff
   *contradicts the upstream compatibility claim*, so it routes back to the registry as a
   finding with the diff as provenance. Organizational testing thereby becomes upstream
   validation input — the loop the software world's lockfile ecosystems never closed.

**One mechanism, both migrations.** Provider swap (EngineBlue → EngineGreen) and class upgrade
(Base@v1 → Base@v2) are the same operation over the same portable surface: hold the
Base/Type-scoped elements constant, vary one axis, diff the declared outputs. Implementations
must not fork these paths.

## Consequences

- Unpinning becomes a tested act with preserved evidence; conservative estates get a
  standing, cheap upgrade path instead of accumulating permanent debt.
- Compatibility classification gains an empirical check: a compat-gate "compatible" verdict
  that produces dirty diffs in the field is a defect in the classifier, discoverable because
  refusals route home.
- The diff is only as good as the output surface — thin-output types (the standing scoreboard
  finding) are invisible to this contract, which makes output adequacy a prerequisite, not a
  nicety.
- Gate work this creates (realization-plan **P1**, consistently — the harness is pilot
  work): the dual-compile harness, the typed-output diff tool, and two **named record shapes
  the registry must define before P0 freezes**: the promotion-evidence record (corpus ref,
  both revision sets, diff, approvals) and the upstream **finding-routing record** — the
  registry kind that carries a contradicted compatibility claim home with the diff as
  provenance. Neither exists today (expressibility audit r2, finding N2); ADR prose is not a
  routing mechanism.
