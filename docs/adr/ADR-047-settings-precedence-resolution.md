# UDLM ADR-047: Settings precedence resolution is a derived projection — ratified as reuse, plus the same-tier tie-break

**Status:** Proposed (croadfeldt upstream)
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles. ADR-015 (settings and config bundles — the §2a select/order/compose
resolution algorithm this ADR ratifies as *the* answer); ADR-038 (scoped resource-type Classes —
the scoping question that prompted this ruling); ADR-008 (the UDLM/DCM boundary test — contract in
UDLM, assembly engine in DCM); ADR-045 §7 (compilation provenance on generated artifacts, verified
by byte-comparable recompilation); `foundations/layering-and-versioning.md` (LAY-005 override
intent, LAY-008 per-field provenance reconstructability).

## Context

An external field-device fleet adopter mapped its scoped-configuration model onto the registry: a
value may be set at system, site, group, or per-unit scope, the narrowest applicable scope wins,
some values carry a floor below which they may not be overridden, and an operator must always be
able to ask "where did this effective value come from?". The adopter's design question was whether
ADR-038's scoping needed *extending* to express that resolution — whether "which declaration wins,
and how do I prove it" required new model surface.

The stakes: if resolution semantics were genuinely unstated, every adopter would invent its own
merge order, and two conformant peers reading the same layered declarations could disagree about
the effective configuration — the exact failure the layer model exists to prevent.

## Decision

**Resolution needs no new mechanism. It is already specified, split correctly across the
UDLM/DCM boundary — this ADR ratifies that reading and adds one missing clause (same-tier
ordering).** The pieces, each existing:

1. **The derivation rule is ADR-015 §2a, verbatim.** Select every bundle whose scoping filter the
   request's coordinates satisfy → order by precedence tier → compose per setting, taking the
   highest-tier value at or below the setting's ceiling, rejecting ceiling violations and
   `tighten_only` weakenings → the result is the effective value plus its provenance (the winning
   bundle's filter). The adopter's system < site < group < unit ladder is this algorithm with
   fleet coordinates; "this value may never be set below site scope" is the `scope` ceiling;
   "this value is per-unit" is ceiling `unit`. Nothing in the ladder is new surface.
2. **Compute-never-store holds.** ADR-015 §4: the effective value is *composed*, never restated.
   The layer *contract* — coverage, precedence grammar, `narrow_only`, the composition rule — is
   UDLM's; the *assembly engine* that executes it is DCM's (the ADR-008 peer test: a peer may
   implement assembly differently and stay conformant, because the contract fixes the outcome).
   An adopter's own resolver is a conformant assembly engine, not a fork of the model.
3. **Per-value provenance is a required property of the merge, not an extension.** LAY-005 gives
   each layer contribution its override intent; LAY-008 requires that full provenance — which
   layer set each effective field — is always reconstructable from the entity record, the layer
   chain store, and the Audit Store. "Where did each value come from" is therefore answerable by
   contract on every conformant resolution.
4. **Rendered artifacts carry compilation provenance.** A flat generated projection of the
   resolved configuration (an inventory file, a rendered config) is a generated artifact under
   ADR-045 §7: it names every input revision and the generator version, and is verified by
   byte-comparable recompilation. A hand edit to the projection is refused at the gate — the
   provenance block replaces trust with verification.

**The one genuinely unstated clause — same-tier ordering — is ruled as follows.** ADR-015 ranks
precedence *tiers* but says nothing about two bundles at the *same* tier. `layer.schema.json`
already carries the needed primitive: `precedence_order` within a `precedence_class`. The rule:

- Same-tier composition is ordered by **explicit `precedence_order`** — deterministic, declared,
  auditable.
- Two same-tier bundles that set the **same setting** with **no declared order** are a **refused
  conflict**: the refusal is typed, and it names both sources and both values. Nothing is
  silently picked. This is the declared-authority rule the change-control corpus already
  established (`use-cases/change-control/014` — undeclared multi-source conflict refuses rather
  than guessing), applied to settings composition.

## Consequences

- Adopters get a guarantee, not a convention: any two conformant resolvers produce the same
  effective configuration and the same per-value provenance from the same declarations, or a
  typed refusal — never a divergent silent merge.
- The refuse-on-undeclared-conflict clause makes a missing `precedence_order` declaration a
  visible authoring defect at resolution time, instead of a latent ordering bug.
- What this ADR does *not* do: it does not realize the unbuilt carriers. The ADR-015 Setting
  schema, the per-field override ceiling/direction in machine form, and the ADR-038
  `covers`/`skip` selectors remain schema work tracked by the class-implementation program — that
  is missing *carrier*, not missing *semantics*, and nothing in this ruling changes shape when
  those land.
- Corpus anchors: the adopter's scoped-configuration and blast-radius cases, and
  `use-cases/class-versioning/` 010–012 (render provenance and historical reconstruction)
  exercise every clause above.
