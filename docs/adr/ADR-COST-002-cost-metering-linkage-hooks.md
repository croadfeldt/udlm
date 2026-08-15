# ADR-COST-002: Cost/metering linkage hooks — a reciprocal contract; the engine computes, it never decides

**Status:** Accepted
**Realized by:** _by design_ — linkage hooks only; the engine computes and UDLM carries the reference. No cost calculation surface is owed.
**Type:** Architecture Decision Record — a `DecisionRecord` with architecture scope (`docs/spec/foundations/knowledge-family.md` §4.5)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The surfaces this decision governs: `docs/spec/contracts/cost-metering-linkage.md` ·
`registry/resource-type-spec.schema.json` · `docs/spec/contracts/information-providers.md` ·
`docs/spec/contracts/provider-contract.md` §10 (capability discovery) · Prior decisions it builds on: ADR-COST-001

## Context

ADR-COST-001 placed cost OUTSIDE UDLM (reference, don't model). This record proposes the
concrete UDLM HOOKS that make that real — the substrate a cost engine consumes and returns
cost through, on a UDLM-conformant platform (e.g. DCM). Maintainer's requirement: UDLM must
(a) let a cost-model reference be injected onto a resource/type, (b) inform a cost engine
which resource is associated with which data, and (c) give the engine a method to look up the
resource data it needs (usage, bandwidth, storage, power). Maintainer's framings that shape
the design: it is a RECIPROCAL contract (we hand the engine metering inputs AND consume cost
back), and we are NOT certain we want to pull any decision-making into the costing calculation
— the engine computes, the realization decides. The method reuses existing primitives: typed
spec fields/outputs (the value sources), the Information-Provider serve_data bridge (the
engine + telemetry as providers), capability-discovery needs_from_realization (the reciprocal
declaration), and the ownership accountability edge (who bears the returned cost). Two new
optional data hooks are added: spec.metering (the meterable surface) and priced_by (the cost-
model reference, type-default + per-instance override). Deliberately NO formula/derived source
kind — UDLM declares sources, never computes, which is the line that keeps calculation out of
the data model. Proposed, not adopted — a possible method for review.

## Decision

Add two optional data hooks to UDLM: (1) spec.metering.dimensions[] on the Resource Type Spec
— each dimension carries name, unit, cost_class (capex|opex), and a source (kind
field|lifecycle|telemetry) declaring where the value is resolved from; (2) priced_by
(information_provider_uuid + opaque external_model_id) on the Resource Type Spec (default) and
on the realized entity (per-instance override). A conformant realization resolves each
dimension by its source and hands the resolved set + priced_by to the cost engine (a
serve_data:cost provider); the engine returns cost, which the realization consumes and
attributes to the owning tenant. The engine computes; the realization decides
(placement/budget/quota stay policy). No formula source kind. Documented in contracts/cost-
metering-linkage.md; demonstrated on Compute.BareMetalHost v0.2.0.

## Data · Policy · Provider

- **Data** — spec.metering (the meterable surface — what is measurable + where each value
comes from) and priced_by (the cost-model reference). No rates, no formulas — those are
external. This is UDLM's entire contribution to cost.
- **Policy** — Which priced_by wins (type default vs per-customer/contract instance override)
is admin policy; whether returned cost gates placement/budget/quota is admin policy in the
realization. Cost decisions are policy, never baked into the engine call.
- **Provider** — The cost engine is a serve_data:cost provider that declares
needs_from_realization (entity_lifecycle + metering) and returns cost.attributed; a telemetry
provider (serve_data) supplies opex usage values. Reciprocal: the realization consumes engine
output and never delegates a decision to it.

## Alternatives considered

- **Meterable surface as a dedicated spec.metering block (chosen)** — a second typed surface
alongside outputs
- **Overload existing spec.outputs by flagging some as meterable** — conflates the binding
surface with the cost surface; no natural home for cost_class/capex-opex or
lifecycle/telemetry sources *Rejected:* different concerns; outputs is the referenceable
binding surface, metering is the cost surface
- **Add a formula/derived source kind so UDLM can express derived meters** — puts CALCULATION
in the data model — exactly what ADR-COST-001 and Maintainer's 'no decision-making in costing'
preclude *Rejected:* calculation is the engine's; UDLM declares sources only
(field/lifecycle/telemetry)

## Consequences

['registry/resource-type-spec.schema.json (spec.metering + priced_by)', 'registry/realized-
entity.schema.json (priced_by instance override)', 'contracts/cost-metering-linkage.md',
'registry/resource-types/compute.bare-metal-host.json v0.2.0 (worked capex/opex example)']
