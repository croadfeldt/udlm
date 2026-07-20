# ADR-030: The convergence lifecycle — one model beneath the entity families

**Status:** Proposed (2026-07-19) — records the unified model as the **post-1.0 direction**; 1.0 keeps the four families verbatim as its archetype vocabulary (see ADR-031 focus, ADR-032 direction).
**Related:** ADR-006 (convergence control — this *completes* it); ADR-027 (entity family model — this *refines* it, post-1.0); ADR-011 (validate-and-reserve — identity mint + reserve, at intent declaration); ADR-029 (inventory / observed provenance); ADR-031 (1.0 focus); ADR-032 (post-1.0 direction). Pictures: [lifecycle-convergence flow](../flows/lifecycle-convergence.md).

## Context

ADR-027 named four entity families — Resource, Process, Knowledge, Access — on a "state vs execution" axis. Working three things at once — the estate as system inventory (ADR-029), combining Day-0/1/2 activities into one unit (Blueprints), and JIT / short-lived credentials — showed the four aren't four peers. They share one lifecycle, and the distinctions we kept reaching for (Resource vs Process, long vs short, provision vs day-2) collapse into *parameters* of it. This ADR records that lifecycle so the model is understood as one thing, and so 1.0 decisions are made with the whole shape visible (ADR-032).

## Decision

**One state, one act, two triggers. Everything else is that, parameterized.**

### The three primitives
- **Intent** — the declared desired state (mutable; values include *exists-as-X* and *absent* (decommission)).
- **Realized** — the actual state: the **policy-resolved intent combined with the provider's specific output**. `Realized` = reality with an intent behind it; `Discovered` = observed reality with **no** intent.
- **Converge** — the one act (the Data·Policy·Provider loop of ADR-006) that drives Realized toward Intent. The thing it closes is a **gap** (Intent ≠ Realized).

### One act, two trigger-classes
A gap opens exactly two ways, and Converge closes it without caring which side moved:
- **intent moved** — a new / changed / withdrawn desired state (request, reconfigure, decommission-to-*absent*);
- **target moved** — reality diverged (drift, loss).

The events we name — Realize, Reconcile, Reconfigure, Rehydrate — are **not distinct acts; they are colloquial shortcuts for the one act** (Converge), each a handy name for a *scenario* by its **trigger** (intent-moved vs target-moved) and its **gap shape** (`∅→X` create, `X→Y` modify, `X→∅` remove, `lost→X` restore). They help you say which situation you are in — they are not different mechanisms, and **not** first-vs-later: a rehydrate is a `∅→X` (recreate) long after the first realize. ("Realize" tends to mean create-from-a-request; "reconcile", restore-to-target-after-drift.) **Decommission** likewise names the scenario where intent is set to *absent* — not an act but a target the one act converges to: Converge drives reality to nothing, the entity settles into the `Decommissioned` state, its realized resource reclaimed while the **record is retained** (immutable, for audit). You don't *do* a state; you set the intent and the act closes the gap.

### Nature is the durable axis; timeline / terminal / provenance are parameters
- **Nature** — *maintained-state* (a thing that is, reconciled while it lives), *work-product* (a bounded execution that completes), or *curated* (understanding, no fulfillment arc). This is ADR-027's real, surviving distinction.
- **Reconcile is an operational capability over maintained-state, regardless of timeline** — not a lifecycle state, and *not* gated by TTL. A short-lived credential is reconciled the same as a long-lived VM.
- **Timeline** (expected lifetime) and **terminal condition** (decommission / completion / TTL / revoke / reclaim / host-gone / deprecation) are orthogonal to nature.
- **Provenance of existence** — how an entity entered: *requested* (Intent→Realized), *observed* (→Discovered), *curated* (→Canonical). One type may support more than one entry (Inventory is *created* **and** *observed*).

### Archetypes are presets, not species
Resource / Process / Credential / Inventory / Knowledge are named `(nature + parameters)` **presets** over the one spine — the way profiles are composed sets, not fundamental levels. Critically, **Credential and Inventory are Resource-nature variants** (maintained-state, reconciled), differing only in timeline / terminal / provenance — not their own kinds. The full projection is in the [flow doc §4](../flows/lifecycle-convergence.md).

### Intent is the single root — of nature, lifecycle, and change

Intent is the one root, and reality is its expression.

- **Nature is rooted in intent.** Maintained-state / work-product / curated is *declared*, at the type level (a type spec is design-time intent) and inherited by instances — you don't discover a thing's nature, you intend it.
- **Lifecycle and change are rooted in intent by necessity.** No change — reconfigure, decommission, even "hold steady" — can be expressed without a desired state to converge toward.
- **`Realized` is the policy-resolved intent combined with the provider's specific output.** The intent runs the full policy pipeline — enrich → validate → transform → place (the `Requested` state) — and the provider then fulfils it and reports its actual work (assigned IDs, addresses, metadata). It is not a second source of truth: intent is the *target*, the provider the *actuator*. A complete authored intent leaves *enrichment* with nothing to fill, but validation / transformation / placement still run and the provider still supplies actuals — so realized is never the raw authored intent. Drift, rehydration, audit, and portability all require an intent to compare against, replay, attribute, and carry; there is no "realized-as-root".

**`Discovered` is the sole exception** — observed reality with no intent, read-only; it carries only the classification of the type it maps to. It joins the root by **adoption**.

**Adoption (greening the brownfield) is convergence with a *backported* intent — and the backport is itself convergence, run dry:**
1. **Build** a candidate intent from the discovered state + provider criteria.
2. **Run convergence in no-op (dry-run)** — the full policy pipeline fires (enrichment, validation, transformation, placement); nothing is acted on.
3. **Compare** the projected realization to the discovered state; **tweak the intent** and repeat until the projection is exact, or close, per the **faithfulness knob**.
4. **Approve** the resulting target intent.
5. **Converge for real** — reality is driven to the approved intent; the discovered parts that don't fit are **decommissioned**.

The same loop *builds* the intent in simulation, then *executes* it. Two policies steer it:
- **Faithfulness** — a policy/profile axis from "accept discovered as-is" to "conform to the nearest compliant variant, decommission deviations" — the same knob as rehydration's faithfulness modes, on a different trigger.
- **Approval** — because step 5 can decommission running infrastructure, the target intent is **approved** before convergence acts (the approval ladder profiles already model). No silent auto-destruction.

Two further intent-mediated writes complete the picture, neither a second root:
- **Validate-only** — a fully-detailed authored intent leaves *enrichment* with nothing to fill; the intent is still validated, transformed, and placed, and realized = that policy-resolved intent + the provider's specific output (never the raw authored intent).
- **Absorb** — legitimize an out-of-band change by snapping intent to the new realized (the `UPDATE_DEFINITION` path: accept, don't revert).

This reframes "intent vs realized": not two co-equal tracks, but **one root (intent) + one expression (realized)**, with `Discovered` as the read-only inlet that adoption turns into intent.

### Relationship to what exists
- **This completes ADR-006.** The re-entrant Data·Policy·Provider loop *is* the lifecycle; realize, reconcile, rehydrate, and teardown are one pipeline fired by different triggers; `request-realization` is one firing of it (the create scenario).
- **This refines ADR-027 — as direction, not a 1.0 change.** The four families' durable core is *nature*; the model is nature + parameters + archetypes. For 1.0 the four families stay verbatim (they *are* the archetype vocabulary); nothing in the schema or estate changes now. Per ADR-031/032, the only pre-1.0 obligation is to **avoid the one contradiction**: do not harden Resource/Process into closed *species* with behaviour branching on the family — the model makes them archetypes over one loop. Leaving them as today's labels contradicts nothing and costs nothing. Promotion (nature-first, convergence-primitive, archetypes) is a post-1.0 superseding ADR with migration.

## Data · Policy · Provider
- **Data** — Intent and Realized (and the gap between them) are UDLM data; provenance (`Realized` vs `Discovered`) is carried in the record.
- **Policy** — Policy is a peer *inside* Converge (ADR-006): it validates, transforms, gates, and places on every firing; the trigger-class selects the policy path, not a different mechanism.
- **Provider** — the Provider executes each firing (naturalize → act → denaturalize → report); observed provenance is provider-populated (discovery); curated is DAV.

## Consequences
- One mental model, one pipeline: DCM has no separate "provision" and "day-2" subsystems — only triggers into one convergence loop. This is what makes Blueprints and Day-0/1/2 fall out as parameters, not subsystems.
- 1.0 is untouched — four families, current schema, current estate. The model is *recorded*, not *rebuilt*.
- The requested / observed / curated provenance split lands ADR-029 coherently: inventory is Resource-nature entered by observation or creation, not a new family.
- Post-1.0, a superseding ADR can promote convergence + nature + archetypes and migrate; ADR-027's family axis becomes the archetype layer.

- **Adoption needs a simulation mode.** The dry-run backport step means convergence must run as a **no-op (rehearsal — ADR-003)** as well as for real; the same pipeline serves build-time intent-fitting and run-time execution.
- Recasts the intent-vs-realized question as **root + expression**, not two co-equal tracks — with `Discovered` the read-only inlet that adoption turns into intent.

## Alternatives considered
- **Leave the four families as unexamined peers** — rejected: the inventory + Blueprint + credential work each needs the shared spine visible, or every family gets modelled (and special-cased) separately.
- **Adopt the unified model now** (nature-first, archetypes, convergence-primitive in the schema) — rejected: violates 1.0 scope (ADR-031) and forces a migration pre-tag; it's a superseding change, post-1.0.
- **Collapse nature too** (everything is "an entity on a timeline") — rejected, and corrected during design: timeline is orthogonal to nature; a credential is a *short maintained-state*, reconciled — not a work-product. Maintained-state vs work-product vs curated is real and survives.
