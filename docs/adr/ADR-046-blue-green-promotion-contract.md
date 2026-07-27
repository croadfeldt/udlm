# UDLM ADR-046: The blue/green promotion contract — typed-output diff as the gate, evidence to attestation

**Status:** Proposed (croadfeldt upstream) — pending engineering ratification (#217); decided 2026-07-25
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles. The pin lifecycle this completes (ADR-045
— organizational pins are legal enumerated debt; this contract is how the debt retires), the
binding surface it diffs (data-model-core §2 [D8.3] — declared typed outputs, the only comparable realization
facts), the migration pattern it generalizes (the Process-family engine-swap render — the same
machinery serves provider swap and class upgrade), the evidence pipeline it feeds (validation
results as signable attestation input, per the model-health emission), and the corpus that
measures it ([`use-cases/class-versioning/`](../../use-cases/class-versioning/README.md) 007
and 008).

## Context

ADR-045 lets an organization pin its estate to exact class revisions, with the lag shown as
a visible debt list. That debt must be retirable without a leap of faith — the way blue/green
deployment retires risk in software delivery: run old and new side by side, compare, and only
switch on evidence. Concretely: "the upstream change is compatible" is a claim, and claims about
someone else's estate deserve evidence, not trust. The evidence exists deterministically —
every realizable type declares typed outputs, and two compilations of the same intent are
mechanically comparable on them.

## Decision

**The boundary first (ADR-008 peer test, ruled 2026-07-25): the information lives in UDLM;
the decision, approach, and mechanisms belong in DCM.** What this ADR binds is the **evidence
contract** — the model surfaces below (comparable declared outputs, the promotion-evidence
record, the finding-routing record, the same-corpus-ref rule, volatile-output declaration) and
the invariant that promotion happens on evidence, never on version claims. **Blue/green is the
reference approach**, worked through here because it exercises every surface — it is not the
required mechanism. Canary, shadow, staged, or an organization's own approach complies
identically so long as it produces and consumes these evidence surfaces; choosing among them
is a DCM-side decision under the estate's policies, exactly as the operational response
matrix's open taxonomy treats every other response.

**Re-pins promote on evidence, not version claims.** The contract, in its reference form:

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

**One evidence surface, both migrations.** Provider swap (EngineBlue → EngineGreen) and class upgrade
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
