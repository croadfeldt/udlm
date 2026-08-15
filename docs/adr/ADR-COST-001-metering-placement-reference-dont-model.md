# ADR-COST-001: Metering & billing is referenced by UDLM, not modeled in it — cost decisions are admin policy, calculation is a provider

**Status:** Accepted
**Realized by:** _by design_ — the decision is that metering is REFERENCED and not modelled. Its realization is the absence of any cost type in the registry, held by `tests/check_implementation_neutrality.py` and the type registry itself.
**Type:** Architecture Decision Record — a `DecisionRecord` with architecture scope (`docs/spec/foundations/knowledge-family.md` §4.5)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The surfaces this decision governs: `docs/spec/contracts/information-providers.md` ·
`docs/spec/contracts/provider-contract.md` §10 (capability discovery) · `registry/policy.schema.json` · Prior
decisions it builds on: DR-UDLM-DCM-001

## Context

This settles where cost lives relative to UDLM.
Cost/metering/billing has its OWN lifecycle, independent of a resource's: prices differ per
customer, contracts have their own lifecycles, and there is no external cost STANDARD to
adopt-by-reference. Therefore UDLM does not model, calculate, or own cost. Its proper name is
'metering & billing', and a realization (the control plane or otherwise) works fully WITHOUT it — a homelab
estate is modeled in UDLM with no cost at all. This record is the first worked instance of the
the substrate/implementation boundary (DR-UDLM-DCM-001): calculation is realization/provider concern; UDLM
carries only the DATA that bridges to an external metering model and the POLICY that selects
it. Crucially, the substrate the meeting called for ALREADY EXISTS in UDLM 1.0: the external-
data bridge is contracts/information-providers.md (External Entity Reference — a control plane-UUID
wrapping an external-UUID, lookup/verify, never owned); metadata/tag injection onto resources
is information-providers §5.2 extended data (org-defined fields carried in payload explicitly
for 'cost analysis tools'); a metering provider declaring partial scope ('I implement 21 of 31
phases') is the capability-discovery.md unified capability model, which already ships a
cost_analysis capability and cost.estimated/cost.attributed streams. No new UDLM 1.0 core
structure is required — only this decision, recorded.

## Decision

UDLM does not model or calculate cost. Metering & billing is an external data model with its
own lifecycle, bridged from UDLM via the Information-Provider External Entity Reference
(contracts/information-providers.md) and enriched via extended-data injection. WHICH cost
model applies to a resource, plus quotas and budgets, are admin-defined POLICY
(policy.schema.json), evaluated by the realization's Policy Engine — quotas/budgets may
originate in a third system (e.g. ServiceNow) and synchronize in. The costing/metering engine
is a PROVIDER (serve_data cost domains + needs_from_realization), which MAY declare partial
phase coverage. The control plane consumes the engine's output and feeds it usage/quota/budget data; the control plane
never performs the calculation. A metering & billing extension vocabulary is deferred to the
metering-extension owners, authored against this substrate — not part of UDLM 1.0 core.

## Data · Policy · Provider

- **Data** — UDLM carries the REFERENCE/bridge to the external metering model — an
information-providers External Entity Reference plus extended-data fields tagging a resource
for cost attribution — never the cost VALUES or cost TYPES themselves. Cost types live in the
external model / deferred metering extension.
- **Policy** — 'Cost as admin policy' — which cost model applies to which resource, and the
quotas/budgets that gate provisioning, are admin-defined policy records (policy.schema.json).
Cost DECISIONS are policy, evaluated by the realization's Policy Engine; UDLM carries the
policy records. Quotas/budgets may be authored in a third system and synchronized.
- **Provider** — The metering/billing engine (Koku / Median / Cosmata / any FinOps tool) is a
Provider — capability serve_data over cost domains, with needs_from_realization for entity-
lifecycle + placement + cost-attribution streams (capability-discovery.md already models
exactly this, incl. the 'Acme FinOps Platform' example). A provider MAY cover only part of the
31-phase metering flow. The control plane consumes its output; the control plane never calculates.

## Alternatives considered

- **Model cost types natively in UDLM 1.0 core (review #274 — 'define cost types in UDLM')** —
cost has an independent lifecycle (per-customer pricing, contract cycles); no standard exists
to anchor it; bloats the core model for a concern many realizations don't use *Rejected:*
couples two lifecycles that the meeting agreed are separate; violates adopt-or-reference
(there is nothing to adopt, so REFERENCE, don't embed)
- **A UDLM cost/metering EXTENSION namespace shipped inside udlm core 1.0** — 1.0 core should
not carry an optional, still-being-authored vocabulary; the metering-extension owners own the
metering model, not UDLM core *Rejected:* deferred, not rejected — a metering & billing
extension MAY be authored against the substrate, but it is out of 1.0 core
- **UDLM references an external metering model via the existing Information-Provider bridge;
cost selection + quotas/budgets are admin policy; the costing engine is a provider (chosen)**
— the metering & billing vocabulary itself must still be authored (by the metering-extension
owners) as an extension against this substrate
