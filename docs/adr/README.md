# UDLM Architecture Decision Records

Short, reviewable records of significant UDLM data-model decisions — the **why**. Each is a
`DecisionRecord` with architecture scope (the ADR specialization — `entities/knowledge-family.md`
§4.5); UDLM **adopts the ADR/MADR format by reference**, it does not coin its own. DCM keeps its
own ADRs in `architecture/adr/` (the control-plane side); UDLM ADRs here cross-reference them.

**Referenced DCM ADRs (external — resolve in the DCM repo `architecture/adr/`).** UDLM docs cite these
control-plane decisions by their `DCM ADR-0XX` name; they are not defined here:

| Ref | Topic (as cited in UDLM) |
|---|---|
| DCM ADR-012 | (control-plane; cited by UDLM docs) |
| DCM ADR-013 | Override model (control-plane side of policy override) |
| DCM ADR-014 | Layer/authority seam |
| DCM ADR-016 / 017 / 018 | Discovery/inventory control-plane decisions |
| DCM ADR-019 | Placement (the placement engine + algorithm) |
| DCM ADR-020 | Placement-adjacent control-plane decision |
| DCM ADR-022 | Trust model (DCM brokers trust, never custodies it) |
| DCM ADR-023 | Scale-of-integration / denaturalization tiers |

The local sequence below (ADR-001…011) is UDLM's own; any `ADR-0XX` above 011 without a file is a
`DCM ADR-` reference — always write it qualified so it resolves cross-repo.

**Required lens (every ADR / DecisionRecord).** Each decision MUST state its **Data · Policy · Provider**
aspects — the three foundational abstractions (DCM ADR-002). *Data* = what's modeled/held (UDLM);
*Policy* = what's decided/computed/governed (DCM); *Provider* = what's declared as possible and what
executes the mechanism. A decision that can't name all three (or explicitly say "n/a, because…") isn't
fully scoped. Foundational across UDLM, DCM, and DAV (`SPEC-DESIGN-REQUIREMENTS` §29).

| ADR | Decision | Status |
|-----|----------|--------|
| [001](ADR-001-topology-type.md) | `Topology` — cross-cutting failure/locality-domain type (failure domains = data within it; abstract `kind` / concrete `id`) | Proposed |
| [002](ADR-002-capacity-utilization-served-overlay.md) | Capacity/Utilization — served observational overlay (cost pattern), **not** a UDLM type | Proposed |
| [003](ADR-003-data-mobility-and-process-validation.md) | Data mobility (requirements=data, methods=provider, mechanism=provider, permission=Policy) + process-validation lifecycle (rehearsal/simulation, freshness; T6) | Proposed |
| [004](ADR-004-provider-capability-declaration.md) | Provider capability declaration — `topology_capability` + `mobility` + `operational_capability`; what placement & operational/SRE policies match against | Proposed |
| [005](ADR-005-time-integrity.md) | Time integrity — ordering is structural (hash-linked sequence + causal DAG, not clocks); time-sync is a profile-declared adopt-by-reference capability enforced by placement; cross-peer integrity via mutual signed checkpoints; leap-seconds require-monotonic/recommend-smear | Proposed |
| [006](ADR-006-convergence-control-model.md) | Convergence control model — Data·Policy·Provider are peers in an event-condition-action loop where **policy is re-entrant** (re-triggered by provider change/denial/drift); soundness rules = bounded convergence, idempotent re-entry, causal audit of triggers | Proposed |
| [007](ADR-007-profile-model.md) | Profile model — profiles are composed **sets** (policies + operational config + required mechanics), not levels; they set floors; built-in profiles are immutable and modification **forks a custom profile**; org-defined mechanics (e.g. approval ladder); platform-scoped now, group-scopable later | Proposed |
| [008](ADR-008-udlm-dcm-boundary.md) | The UDLM/DCM boundary — the peer test (could an independent peer do this differently and still be valid? yes→DCM, no→UDLM); UDLM = wire-compatible substrate, DCM = one realization; wire-compatibility not implementation portability (K8s precedent); decision home for enh #58 | Proposed |
