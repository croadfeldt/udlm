# UDLM ADR-060: Findings are sealed interpretations — drift is the first family member

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decisions 2026-08-03. Consumes ADR-059; ratifiable separately.
**Date:** 2026-08-03
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**What this settles:** how a detected condition — drift, tamper, staleness, a missed cadence —
is represented, deduplicated, and resolved: as a **sealed ledger interpretation with a
lifecycle**, never as a field on the working record.

**Background — read first (the cold reader's on-ramp; skip if you have the context).**

- **ADR-059** (definitions and receipts; consumed here): the working record carries state
  claims only (states + pin + resource chain); the ledger alone makes history claims; every
  change seal cites its causal pathway anchor (`pathway_ref` — request chain, discovery run, or
  provider event), and a write without a citable anchor is refused. This ADR sits entirely on
  those decisions.
- **[`docs/spec/foundations/four-states.md`](../spec/foundations/four-states.md)**: comparing the four
  states continuously is how the implementation detects drift — the comparison loop this ADR
  gives an output shape.
- **ADR-052** (intent fulfillment / convergence): the declared convergence window and derived
  convergence verdicts — what separates sanctioned divergence from drift.
- **ADR-048** (staleness as declared expectation): verdicts are derived, never stored — the
  precedent this ADR generalizes.
- **[`registry/finding-routing-record.schema.json`](../../registry/finding-routing-record.schema.json)**:
  the existing routing home findings flow through.
- **D6** (drift severity): one canonical enum — `minor | significant | critical`.

---

## Context

The model now detects several conditions by evaluation: state divergence (drift), a record
failing resource-chain verification (tamper), an observation missing against a declared cadence
(completeness), a claim un-refreshed within its window (staleness). Each needs permanent
evidence, deduplication, routing, and closure — and without one shape, each grows its own.
This ADR names the one shape.

## Decision — findings

A **finding** is a sealed interpretation of record state: permanent evidence that a condition
was detected at a time, over a version, from cited inputs. Findings live in the **ledger**,
never on the working record — a finding is a history claim, and storing one on the record would
be both a stored derivable and a lineage claim in the state store (ADR-059's claims
discipline). One facet shape, `udlm_finding`, with `finding_class` discriminating: **drift**,
**tamper**, **staleness**, **cadence-miss** — and whatever a profile adds. Distinct classes
carry distinct response postures (tamper is not drift); all share one mechanism, one routing
home, one lifecycle.

## Decision — drift, precisely

Drift is divergence among the states **outside an active convergence**. The comparator runs
**event-driven** — on each seal, which is the implementation's own loop (data change → policies
evaluate) — and consults convergence status first (ADR-052): desired ≠ actual during a
sanctioned window is progress, not drift; the window expiring un-met **is** drift (the
unmet-intent flavor, with the request chain as evidence). The comparator is **source-blind**
(ADR-059's admission rule): it evaluates state relationships after any seal, and the finding's
evidence carries whichever pathway anchor the triggering seal carried — request, discovery run,
or provider event.

A drift finding carries: the diverged fields with both sides' values; severity per the D6 enum
(classified by a drift *policy* — field relevance is organizational: observed-only fields and
benign jitter are policy-excluded, never hard-coded); `entered_at` — the exact resource-chain
version whose seal introduced the divergence (exact because detection is event-driven); and
evidence citations (the triggering seal + its pathway anchor).

## Decision — finding lifecycle

A finding is **opened once** (keyed on resource + diverged-field-set), confirmed-not-duplicated
by subsequent detections, and **closed by a resolution seal** — reconverged, accepted, or
reviewed — which cites it. The ledger then holds the full story as one citation walk:
divergence version → finding → disposition → resolution version. Current drift *status* is
always **derived on read** from the states — never answered from a finding (a finding says
"was detected," never "is drifted"). Flap debounce is policy.

## Resolution routing — policy dictates, the substrate enables

**Ruled 2026-08-05.** A drift finding routes to **policy first**; policies dictate what happens,
when, and *perform the action* — the substrate ships **no built-in action and no built-in
decision** for any finding class. What UDLM guarantees is that every resolution option is
*expressible*; the control plane carries example policies and profiles MAY bind defaults. The enabled
vocabulary:

| Resolution action | What it is on the wire |
|---|---|
| **Adopt** — intent updated to match reality | a change request on Intent (normal pathway) |
| **Accept** — realized kept, the difference noted on Intent | a change request annotating Intent |
| **Replay intent** — full re-realization through the pipeline | a re-realization request (policies re-applied) |
| **Replay request** — re-dispatch to the provider | re-dispatch of the naturalized request |
| **Replay realized** — re-assert the realized state | a converge request at the last hop |
| **Re-observe** — confirm before acting; close as observation-error if the re-read disagrees | a discovery run; false-positive closes the finding |
| **Quarantine / suspend** — interim containment pending decision | an entity state-change request (not a resolution) |
| **Defer** — explicitly not now, with a review timer | a recorded decision; the finding stays open |
| **Decommission** — the drift reveals the thing should not exist | a decommission request |

Policy may also **hand the decision off** — to a human, an AI, or an external policy system;
the handoff outcome lands as a **DecisionRecord citing the finding**. Because every action
above is an ordinary governed request, the audit capture is total *without new machinery*: the
finding is sealed, each policy evaluation and refusal is audited, the handoff is a
DecisionRecord, and the final action carries full request provenance — the resolution seal
cites the chain end-to-end, decision and resulting action included.

## Data · Policy · Provider

- **Data (UDLM):** the `udlm_finding` facet shape; the finding-class vocabulary's home; the
  lifecycle semantics (open-once keying, closure by citing seal); the derived-on-read rule for
  current status.
- **Policy (the control plane):** the comparator and when it speaks (convergence consulted first); the drift
  policy — field relevance, severity classification, flap debounce; the response matrix per
  finding class; the example resolution policies (OBL-003) and any profile-bound defaults.
- **Provider:** unaffected — providers report state (sealed, anchored); they never emit or
  interpret findings.

## Consequences

- The four detected-condition concepts stop growing parallel mechanisms — staleness (ADR-048),
  tamper (OBL-003's L1-verification failure), cadence-miss (discovery completeness), and drift
  are one family, routed through the existing finding-routing record.
- Dashboards, compliance surfaces, and the review console source the *timeline* from findings
  and *current status* from derivation — never the reverse.
- Drift response is dischargeable: OBL-003 carries the response-matrix mechanism (routing,
  the action vocabulary as matrix rows, example policies, profile defaults).
