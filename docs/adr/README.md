# UDLM Architecture Decision Records

Short, reviewable records of significant UDLM data-model decisions — the **why**. Each is a
`DecisionRecord` with architecture scope (the ADR specialization — `entities/knowledge-family.md`
§4.5); UDLM **adopts the ADR/MADR format by reference**, it does not coin its own. DCM keeps its
own ADRs in `architecture/adr/` (the control-plane side); UDLM ADRs here cross-reference them.

| ADR | Decision | Status |
|-----|----------|--------|
| [001](ADR-001-topology-type.md) | `Topology` — cross-cutting failure/locality-domain type (failure domains = data within it; abstract `kind` / concrete `id`) | Proposed |
| [002](ADR-002-capacity-utilization-served-overlay.md) | Capacity/Utilization — served observational overlay (cost pattern), **not** a UDLM type | Proposed |
| [003](ADR-003-data-mobility-and-process-validation.md) | Data mobility (requirements=data, methods=provider, mechanism=provider, permission=Policy) + process-validation lifecycle (rehearsal/simulation, freshness; T6) | Proposed |
