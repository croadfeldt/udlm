# UDLM ADR-050: The absolute provider pin — whether a pin may confer eligibility, or only express preference

**Status:** Proposed (croadfeldt upstream) — pending engineering ratification (#217); **drafted for decision, not decided**: the options below are stated so the ruling is a choice among them
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — each cited once.** `contracts/provider-contract.md` **PRV-009** (default-deny:
`effective_capabilities` is the intersecting ceiling and a provider can never invoke outside it)
and **PRV-011** (the dispatch-boundary check this ADR decides the shape of, §2b);
ADR-004 (capability declaration — declare-and-select, where an undeclared capability discovered
only at runtime is rejected);
`contracts/error-model.md` §3.2 (`placement.capability_mismatch`, already in the closed
vocabulary and already distinct from `provider.*` failures — the type exists, the enforcement
point does not);
`contracts/policy-contract.md` §18 (the override model: an override is a **data record** with an
approval flow and an audit trail — the precedent Option B would reuse; note that UDLM ADR-016
governs resource-type modeling and is *not* the override precedent, despite the number's
familiarity from the control-plane series);
[`use-cases/must-reject/005-provider-capability-mismatch-refused.yaml`](../../use-cases/must-reject/005-provider-capability-mismatch-refused.yaml)
(the case that measures this, and the one case in the refusal corpus where the model
affirmatively specifies the hazard rather than merely omitting the guard).

## Context

Declare-and-select is one of the model's load-bearing commitments. A provider declares what it
can do; an administrator admits some subset; the registry and the governance matrix narrow it
further; the intersection is the provider's effective capability set, and the contract says a
provider can never be invoked outside it. Eligibility is settled from declarations, not
discovered by trying.

The commitment is undermined by a mechanism that exists for good reasons. Placement supports a
pinned provider — an administrator or policy names the target directly — and the pin is specified
as *absolute*: it short-circuits the remaining steps of the placement algorithm, which include
the accreditation filter and the capability filter. Only the sovereignty pre-filter survives it.
Read together with the ceiling, the two texts contradict: one says a provider can never be
invoked outside its effective capabilities, the other describes a path that reaches dispatch
without consulting them. Where a specification contradicts itself, the operational text wins, and
here the operational text is the one that describes the algorithm.

The consequence is not theoretical. A stale routing rule or a mistaken pin sends work to a
provider that never declared for the resource type, the dispatch is attempted, and the provider
fails at something it never claimed to support. The operator sees a provider error and
investigates a provider that is working correctly; the actual fault — a routing mistake — is
invisible in the symptom. The provider may also have done partial work before failing, so a
misconfiguration becomes a cleanup. This is refusal-by-attempt, and it is the specific behavior
the must-reject case forbids: a capability mismatch is an eligibility fact known before dispatch,
and reporting it as a provider failure mistypes it.

Two things are worth saying about the pin before proposing to change it, because it is not a
mistake. Pinning solves real problems — migration to a specific target, an operator working
around a placement heuristic, a policy that must route a class of work to a named provider — and
a pin that quietly loses to a scoring function is its own kind of failure. Any change must
preserve the operator's ability to name a target and have that honored. And the corpus is not
yet self-consistent about the typing either: a sibling placement case classifies the same
scenario as a provider failure where the must-reject case classifies it as a policy violation.
That disagreement should be resolved by the same ruling.

## Decision

**The open question:** may a pin confer eligibility, or only express preference among providers
that are already eligible? `PRV-011` states that every dispatch re-checks the ceiling; what
remains is whether the pin is a legitimate exception to it, and if so, at what price.
**The recommendation is Option A — but this is drafted for the maintainer's ruling.**

### Option A — Demote the pin to preference within the eligible set *(recommended)*

The pin selects; it does not exempt. The eligibility filters always run, and the pin decides among
what survives them. A pin naming an ineligible provider yields `placement.capability_mismatch`
before dispatch, carrying the required-versus-declared comparison.

*Why it is recommended:* it removes the contradiction rather than documenting an exception to it,
and it preserves everything the pin was for. An operator naming a provider that *can* do the work
gets exactly what they asked for, unconditionally and without a scoring function overriding them —
the pin remains absolute over the choice, which is the part operators care about. What it stops
being is absolute over *capability*, and no operator has ever wanted a dispatch to a provider
that cannot serve it; they wanted the target honored, and it still is. It also makes one sentence
true everywhere instead of true-with-an-exception, which is worth a great deal in a specification
other people implement.

*Its cost:* an operator who today pins a provider whose declaration is stale or incomplete gets a
refusal where they previously got a dispatch that happened to work. That is a real regression in
one scenario — the provider that *can* do the thing but never declared it. The honest answer is
that this scenario is a declaration defect and should surface as one, and the remedy is to fix
the declaration, which is cheap and is the mechanism the whole model rests on. But it is a
behavior change with an operational tail, and the transition deserves a deprecation window rather
than a flag day.

### Option B — Keep the pin absolute, behind an explicit override record

The pin may bypass eligibility, but only when accompanied by an override record: an approver, a
reason, a scope, and a time bound, through the existing override-approval flow. Absent the
record, the pin is a preference and Option A's behavior applies.

*What it buys:* it keeps the escape hatch for the genuine case above — a provider that can do the
work despite its declarations — and prices it correctly. The machinery exists: the model already
treats an override as a first-class data record with approval and audit, and the regulated
profiles already require a time-bounded approval workflow for overriding hard policy. Nothing new
is invented.

*Its costs:* it concedes that the ceiling has an exception, which weakens the sentence
`PRV-009` is built on and gives every future reader a precedent to argue from. It adds an approval
step to a path that is often exercised under time pressure — migrations and incident response —
so the practical outcome may be a standing blanket override, which is the bypass with paperwork.
And it does not actually fix the underlying declaration defect; it institutionalizes working
around it.

### Option C — Split the field in two

Retire the single field in favor of two differently-named ones: one expressing preference among
eligible providers, one expressing a deliberate eligibility bypass. The name carries the
semantics, so no one is surprised by which they got.

*What it buys:* clarity at the point of authorship. A reader of a policy sees immediately whether
a bypass was intended, which today requires knowing the algorithm's step ordering. It also makes
the bypass greppable across an estate — a real auditing benefit.

*Its costs:* it is Option B with a second field instead of an approval record, and it keeps the
bypass while removing the price. Two fields also mean two code paths, two sets of documentation,
and a migration for every existing pin — the largest change surface of the three for the smallest
semantic gain. If the ruling is that a bypass must exist, Option B prices it better; if the ruling
is that it must not, Option A is simpler.

### What the ruling settles beyond the field itself

Whichever option is chosen, the same ruling should settle the corpus's typing disagreement: a
capability mismatch is an **eligibility** outcome — `placement.capability_mismatch`, refused
pre-dispatch — and not a provider failure, because the provider did not break; it was never
eligible. `provider.unavailable` and its neighbours remain reserved for providers that were
eligible and then failed.

## Data · Policy · Provider

- **Data** — the provider's registration declarations and the computed `effective_capabilities`
  ceiling are both resolvable records, which is what lets the refusal cite a
  required-versus-declared comparison instead of asserting a verdict.
- **Policy** — placement, pinning, and any override are policy decisions. This ADR is a ruling
  about what policy may *not* decide: whether a dispatch happens outside the declared ceiling.
- **Provider** — the provider is the party protected by the rule. It receives no work it never
  declared for, and it is not blamed for failing at work it never claimed.

## UDLM vs DCM — what lands where (the peer test, ADR-008)

| Piece | **UDLM** — model / contract (a peer MUST honor) | **DCM** — engine / mechanism (a peer MAY differ) |
|---|---|---|
| The ceiling | `effective_capabilities` and its formula | how the intersection is computed and cached |
| Enforcement point | the check happens at the dispatch boundary, on every path (`PRV-011`) | where in the pipeline the stage sits |
| Pin semantics | whether a pin may confer eligibility — this ADR | the placement algorithm's steps and scoring |
| The refusal | `placement.capability_mismatch`, carrying required-versus-declared | the comparison's rendering |
| Override (Option B) | that a bypass is a recorded, approved, time-bounded artifact | the approval flow |

## Consequences

- The contradiction between the ceiling and the placement algorithm is resolved in one direction
  rather than left for implementers to discover. Under Option A the control-plane text describing
  the pin as skipping the remaining steps is amended; under B or C it is qualified.
- Whatever is chosen, the eligibility check must be specified as unconditional at the dispatch
  boundary. A check every path may opt out of is not a check, and the pin is only the *known*
  opt-out — routing rules and operator overrides reach dispatch the same way.
- The refusal's required-versus-declared payload has a second use beyond the immediate error: it
  distinguishes a mis-routed request (another provider is eligible) from an unsatisfiable one
  (none is), which are different problems for different people.
- If Option A is chosen, the deprecation window and the declaration-defect remedy should be named
  in the same change, so operators relying on today's behavior have a path that is not "your pin
  stopped working".
