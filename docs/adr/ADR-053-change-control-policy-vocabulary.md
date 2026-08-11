# UDLM ADR-053: Change-control — temporal policy clauses, typed debt, and sourced calendars

**Status:** Proposed (croadfeldt upstream) — 0.1 work; 1.0 conferred by engineering acceptance
(#217); decided 2026-07-27
**Date:** 2026-07-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** This decision
assumes these; each is cited once with what it settles, not re-taught here. Corpus:
`use-cases/change-control/` (17 UCs). Flow it ratifies: `docs/flows/change-control-adoption.md` (the
calendar-and-ceremony stage). Design note: `docs/design/change-control-knowledge-sources.md` (windows
as sourced knowledge). ADR-045 (atomic recompilation, pins, visible debt) — the change mechanics this
sits on. ADR-046 (blue/green typed-output diff) — the evidence this must never waive. ADR-048
(staleness as a declared expectation) — the freshness machinery §7 reuses. ADR-051 (publish law +
digest referrers) — how the meta-policy and approvals bind. ADR-052/048 (verdicts derived, never
stored) — the debt-state pattern. ADR-003/T6 (RTO/RPO — a provider-backed validated time bound) —
what §8 generalizes. ADR-008 — the the substrate and its control plane boundary.

## Context

An upstream class change arrives already classified (additive | breaking) with its blast radius
computed (ADR-045/046). What an estate does next — adopt now, wait for a window, run the full
evidence-approval-window-verify ceremony, or hold under a freeze — is a change-management decision
that today lives in wikis and CAB meetings, not the model. Validating the change-control flow
against the registry (2026-07-25) found the operative point: the graph, outputs, policy machinery,
and audit substrate all already exist; what is missing is exactly the vocabulary this corpus family
demands — no temporal clause on the policy schema, debt untyped, no approval record shape, no
freshness surface on any Knowledge type. This ADR supplies it, corpus-first (the 17 UCs and the flow
preceded it). Net additions: one clause family, three derived verdict names, one Knowledge type, one
estimate datum — reusing two record shapes and the RTO/advertisement machinery. Each ruling extends
an existing surface (T7).

## Decision

**1. Temporal clauses are a `schedule` family on the existing policy object.** A gating /
orchestration_flow policy may carry `schedule` clauses — added to the existing clause structure, not
a new `policy_type`. Four kinds: `window` (allowed execution times; inline or sourced, §6), `freeze`
(a dated suspension that queues rather than runs), `expedite` (compress the calendar under elevated
approval + a flagged audit record, §4), `precondition` (proceed only when a named predecessor
stage's evidence is present — declared multi-estate chains, UC-005/008).

**2. A schedule clause governs *when*, never *whether* — structurally.** A `schedule` clause carries
only timing; it cannot encode or waive an evidence decision. The evidence gate (the ADR-046 diff) is
a separate `gating` clause no `schedule` clause — expedite included — can reference away. Expedite
compresses the calendar; it never skips the diff. A policy that gates *whether* from a `schedule`
clause is non-conformant.

**3. Typed adoption debt is a derived verdict, not a stored enum.** Computed on read from the policy
clauses + the change record (the ADR-048/052 pattern): `pin_behind` (ordinary lag, no schedule
holding it), `windowed` (held by a `window`), `frozen` (held by a `freeze`). The verdict names the
clause and the next transition, so an estate behind is provably *on-policy* behind. Debt closes when
the run completes and post-adoption verification passes.

**4. An approval is a sign-off bound to the evidence it accepts — reuse, don't coin.** The human
authority accepting the evidence (`override`-class) is a sign-off referrer: approver identity + the
digest of the diff it accepts (ADR-051), plus scope and timestamp. This is the accreditation shape,
not a parallel one. Expedite requires an approval at an elevated authority the policy declares.

**5. A change policy is itself versioned; changes are prospective; a meta-policy governs them.**
(UC-016.) Changing a change-management policy bumps its version under the publish law (ADR-051),
never a silent rewrite. In-flight adoptions complete under the revision that admitted them; a new
revision governs only adoptions begun after it. A declared meta-policy governs who may change which
clauses — and can never loosen an evidence gate (scheduling clauses are loosenable; evidence gates
are not).

**6. Windows may be *sourced* knowledge — by reference, authority-scoped, fail-closed.** A
window/freeze is often a record in a change-management system, so the model treats it as Knowledge,
sourced not re-typed (the CVE/SBOM precedent, T5). *Sourcing* (UC-013): a change-calendar Knowledge
type refreshed by an information provider (`provider.kind: information`); the policy references it by
handle and the gate cites the revision it read. *Authority* (UC-014): where sources could conflict,
the policy declares authority per scope; an undeclared conflict refuses (naming both sources and
answers) rather than silently picking. *Freshness* (UC-015): the gate checks freshness before
content; stale knowledge refuses (naming source, last refresh, horizon), expedite the sanctioned
emergency route.

**7. Freshness is a Knowledge family-level element — reuse ADR-048, land it on the Base Class.** No
Knowledge type carries `as_of` / `valid_until` / `refresh_cadence` today, so a stale calendar and a
stale CVE feed fail the same undetectable way. It is the KB-tier twin ADR-048 already named: it
reuses that machinery (no parallel staleness model) and belongs once on the Knowledge Base Class
(class-implementation program), inherited by every domain — a per-type stopgap on the change-calendar
type until then, so UC-015 is enforceable now.

**8. The window gate checks *fit*, not openness — and the provider estimates.** An open window is
necessary but not sufficient: an implementation that won't complete in the time remaining must not start.
The gate evaluates `estimate + margin ≤ window_remaining`, and the three roles split:

- **Provider gives the estimate.** Implementation time is provider- and substrate-specific, so the
  provider is the only authority on its own duration. It advertises an expected time-to-complete (the
  capacity-advertisement precedent) and reports the realized duration back (the realized-state
  callback). Those actuals are the T6 evidence that keeps the estimate honest and drive its freshness
  (ADR-048; a stale estimate is low-confidence / fail-closed, as in §6).
- **UDLM encodes it.** The estimate datum on the provider advertisement, the realized-duration field
  on its realized-state report, and the provenance/freshness contract. Not a new mechanism: an RTO is
  already a provider-backed validated time bound, and implementation time-to-complete generalizes it
  (RTO becomes a special case).
- **the control plane/policy acts.** The fit gate reads the estimate, and on a miss refuses (naming estimate,
  source, remaining) and applies the policy's response — defer, batch-fit, or expedite. Because
  propagation is dependency-ordered, batched, and resumable, batch-fit runs the batches that fit and
  carries the rest as `windowed` debt with recorded progress — partial-but-safe, never a mid-batch
  overrun.

## The UDLM / the control plane boundary (ADR-008)

| UDLM — data + contracts | The control plane — evaluates + runs |
|---|---|
| the `schedule` clause vocabulary; the whether/when firewall | evaluates clauses; decides run/defer/expedite/refuse; emits the typed refusals |
| the derived debt verdicts; the change-calendar Knowledge type + freshness | computes the verdicts; ingests/refreshes calendar knowledge |
| the approval referrer; the meta-policy contract | the orchestrated adoption run — a Process-family job: dependency-ordered, batch-verified, resumable |
| the time-to-complete estimate datum, realized-duration report, and fit obligation (§8) | evaluates fit; owns the safety margin and the fit-miss response; the provider produces the estimate + reports actuals |

## Consequences

The one that reaches past change-control: the freshness ruling (§7) hands the whole Knowledge family
staleness-decidability through a single Base Class element. And the firewall (§2) is what makes
expedite safe to offer at all — the emergency path can compress the calendar but can never erode the
evidence guarantee.

## What this does not decide

The JSON-Schema shapes (the `schedule` block on `policy.schema.json`, the change-calendar Knowledge
type, the approval referrer, the freshness stopgap, the estimate datum) follow as an implementing PR
once ratified. The control plane owns the policy defaults — window values, freeze calendars, approver ladders, the
§8 safety margin and fit-miss response — never the portable model. Genuinely open for your ruling:
the debt-verdict names (`pin_behind | windowed | frozen`), whether freshness gets the per-type
stopgap now or waits for the Base Class, and the expedite-elevation shape (a higher-authority tier vs
dual approval).

## Status — 0.1

`udlm/0.1`; 1.0 is conferred by engineering acceptance (#217), not declared here. `Proposed`.
