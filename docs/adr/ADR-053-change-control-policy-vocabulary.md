# UDLM ADR-053: Change-control — temporal policy clauses, typed debt, and sourced calendars

**Status:** Proposed (croadfeldt upstream) — **0.1 work**; 1.0 conferred by engineering acceptance
(#217); decided 2026-07-27
**Date:** 2026-07-27
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related — the complete picture, each cited once.** The corpus that measures this
(`use-cases/change-control/` — 17 UCs); the flow it ratifies
(`docs/flows/change-control-adoption.md` — the calendar-and-ceremony stage, with the
per-decision surface table validated against the registry); the multi-source design note
(`docs/design/change-control-knowledge-sources.md` — windows as sourced knowledge); the change
mechanics this sits on top of (ADR-045 — atomic recompilation, pins, visible debt); the evidence
standard it must never waive (ADR-046 — blue/green typed-output diff); the staleness machinery it
reuses (ADR-048 — staleness as a declared expectation, the KB-tier twin); the identity/publish law
the meta-policy and approvals ride (ADR-051); the derived-status pattern the debt states copy
(ADR-052 / ADR-048 — verdicts derived, never stored); and the boundary that splits it (ADR-008).

## Context

An upstream class change arrives already classified (additive | breaking) with its blast radius
computed (ADR-045/046). What an estate does *next* — adopt now, wait for a window, run the full
evidence-approval-window-verify ceremony, or hold under a freeze — is a **change-management
decision**, and today it lives in wikis and CAB meetings, not the model. The change-control flow
was authored to pull that decision into a declared policy; validating it against the registry
(2026-07-25) produced a precise finding: **the graph, the outputs, the policy machinery, and the
audit substrate all already exist — what is missing is exactly the vocabulary this corpus family
demands.** No temporal clause surface exists on the policy schema; debt is untyped pin-lag only;
there is no approval record shape; and no Knowledge type carries a freshness surface.

This ADR supplies that vocabulary. Per corpus-first discipline the 17 UCs and the flow preceded it;
this is where the flow's `PENDING-ADR` rows become contract. Almost nothing here is a new mechanism
— each ruling *extends* a surface the registry already ships (T7).

## Decision

### 1. Temporal clauses are a `schedule` clause family on the existing policy object

A gating / orchestration_flow policy may carry **`schedule`** clauses — the one new vocabulary,
added to the existing policy clause structure, **not** a new `policy_type` (the enum already has
`gating`, `orchestration_flow`, `override`; T7). Four clause kinds:

- **`window`** — the times an adoption may execute (allowed intervals; may be authored inline or
  sourced from calendar knowledge, §6).
- **`freeze`** — a dated suspension that queues adoptions rather than running them.
- **`expedite`** — a path that compresses the calendar **under elevated approval and a flagged
  audit record** (§4 approvals).
- **`precondition`** — this stage may proceed only when a named predecessor stage's evidence is
  present (declared multi-estate chains, UC-005/008).

### 2. The whether/when firewall — a schedule clause governs *when*, never *whether*

This is the load-bearing invariant, and it is **structural, not advisory**: a `schedule`-family
clause carries only timing; it **cannot** encode or waive an evidence decision. The evidence gate —
the blue/green typed-output diff (ADR-046) — is a separate `gating` clause, and no `schedule` clause
(expedite included) can reference it away. **There is no path to a promoted breaking change without
its diff.** Expedite compresses the calendar; it never skips the evidence. A policy that tries to
gate `whether` from a `schedule` clause is non-conformant — a review finding.

### 3. Typed adoption debt is a derived classification, not a stored enum

"Waiting is visible and typed" becomes a **derived** adoption-debt verdict — computed on read from
the policy clauses + the change record, never a new stored status (the ADR-048 / ADR-052 pattern):

- **`pin_behind`** — ordinary lag: a dependent is behind an available revision, no schedule holding
  it (today's untyped debt, now named).
- **`windowed`** — held by a `window` clause, waiting for the next opening.
- **`frozen`** — held by an active `freeze` clause.

An estate that is behind is thereby **provably on-policy behind** — the verdict names the clause and
the next transition (window open / freeze lift). Debt closes when the adoption run completes and
post-adoption verification passes (ADR-046).

### 4. An approval is a named sign-off bound to the evidence it accepts — reuse, don't coin

An approval (the human authority accepting the evidence, `override`-class) is recorded as a
**sign-off referrer**: the approver identity + the **digest of the evidence diff it accepts**
(ADR-051 digest-in-a-referrer, not in the artifact), plus scope and timestamp. This **reuses the
accreditation/attestation shape** (T7) — it is the same "a named authority binds a decision to an
attested digest" record, not a parallel one. An expedite (§1) requires an approval at an **elevated**
authority the policy declares, and its audit record is flagged.

### 5. A change policy is itself versioned; changes are prospective; a meta-policy governs them

Per UC-016: a change-management policy is a **versioned record** — changing it bumps its version
under the publish law (ADR-051), never a silent in-place rewrite. A change is **prospective only**:
in-flight adoptions complete under the revision that admitted them; a new revision governs only
adoptions that begin after it. A declared **meta-policy** (itself a policy, T7) governs who may
change which clauses, with the same approval/evidence discipline — and a meta-policy change can
**never loosen an evidence gate** (scheduling clauses are loosenable; evidence gates are not).

### 6. Windows may be *sourced* knowledge — adopt by reference, declare authority, fail closed

A `window`/`freeze` need not be authored inline; for most organizations it is a record in a
change-management system. The model treats it as **Knowledge**, sourced, not re-typed (the
CVE/SBOM precedent; T5):

- **Sourcing (UC-013)** — a **change-calendar Knowledge type** (schedule, scope, source, validity),
  refreshed by an **information provider** (`provider.kind: information` — exists) that declares the
  knowledge type as a supplied capability. The consuming policy **references it by handle**
  (adopt-by-reference, never a re-typed copy) and the gate cites the knowledge revision it read.
- **Authority (UC-014)** — where more than one source could answer, the consuming policy declares
  **authority per scope**; an **undeclared conflict refuses** the gating decision (typed, naming
  both sources and both answers) rather than silently picking one — the single-truth ban applied to
  information.
- **Freshness, fail-closed (UC-015)** — the gate evaluates **freshness before content**; stale
  knowledge **refuses** (naming source, last refresh, validity horizon), with **expedite as the
  sanctioned emergency route**. Deciding on an outdated window is worse than refusing.

### 7. Freshness is a Knowledge family-level element — reuse ADR-048, land it on the Base Class

The freshness surface (`as_of` / `valid_until` / `refresh_cadence`) is **missing on every Knowledge
type**, so a stale calendar and a stale CVE feed are the same undetectable failure. It is therefore
**not** a change-control-local field: it is the **KB-tier twin ADR-048 already named** as its
phase-2 destination, and it belongs **once on the Knowledge family's Base Class** (the
class-realization program), inherited by every knowledge domain. Ruling: freshness reuses ADR-048's
`expected_observation` / verdict machinery (no parallel staleness model), lands on the Base Class
when it exists, and until then is a **declared per-type stopgap** on the change-calendar type so
UC-015 is enforceable now.

## The UDLM / DCM boundary (ADR-008)

| UDLM — data points + contracts | DCM — operationalize, via policies + Process |
|---|---|
| the `schedule` clause vocabulary (window/freeze/expedite/precondition) | the engine that **evaluates** the clauses and **decides** run/defer/expedite/refuse |
| the whether/when firewall (evidence gates are separate, un-waivable) | enforcing it at evaluation; emitting the typed window-violation / stale-knowledge refusals |
| the derived adoption-debt verdicts + the change-calendar Knowledge type + freshness | computing the verdicts; ingesting/refreshing calendar knowledge via the information provider |
| the approval sign-off record shape + the meta-policy contract | the orchestrated adoption **run** — a Process-family job: dependency-ordered, batch-verified, resumable propagation |

## Grounding — what already exists (the T7 exemplar)

Policy object + `gating`/`orchestration_flow`/`override` types, the class graph + ADR-044 manifests
(blast radius), `dependencies[]` ordering (propagation order — the shutdown-order machinery),
declared `outputs` (batch verification), the audit-record model (the trail), the Knowledge family +
`provider.kind: information` (sourced calendars), ADR-045 (pins/debt), ADR-046 (evidence/refusal
routing), ADR-048 (staleness/freshness), ADR-051 (publish law + digest referrers). The ADR adds one
clause family, three derived verdict names, one Knowledge type, and reuses two record shapes.
Nothing here needs a surface that is neither present nor already on the build list.

## Consequences

- Change management becomes **declared data** — the human decision is made once, in the policy, not
  once per change; an estate's compliance posture is queryable, not tribal.
- The firewall (§2) makes "expedite" safe: it can never become "skip the diff," so the emergency
  path cannot erode the evidence guarantee.
- Sourced calendars (§6) mean an upstream CAB change never touches policy text, and a stale feed
  refuses rather than silently deciding on an outdated window.
- The freshness ruling (§7) is the finding with reach beyond change control — it hands the whole
  Knowledge family staleness-decidability through one Base Class element.

## Status note — 0.1

Per the maintainer's ruling, this is `udlm/0.1` work; 1.0 is conferred by engineering acceptance
(#217), not declared here. `Proposed` accordingly.

## What this does not decide

The JSON-Schema shapes (the `schedule` clause block on `policy.schema.json`, the change-calendar
Knowledge type, the approval referrer, the per-type freshness stopgap) follow as an implementing PR
once ratified. The genuinely open calls flagged for the ruling: the exact debt-verdict names
(`pin_behind | windowed | frozen` as proposed), whether freshness gets the per-type stopgap now or
waits for the Knowledge Base Class, and the elevation shape for expedite approval (a named higher
authority tier vs a dual-approval requirement). DCM's policy defaults — the actual window values,
freeze calendars, and approver ladders — are DCM's per the boundary, never in the portable model.
