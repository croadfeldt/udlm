# UDLM Architecture Decision Records

Short, reviewable records of significant UDLM data-model decisions — the **why**. Each is a
`DecisionRecord` with architecture scope (the ADR specialization — `entities/knowledge-family.md`
§4.5); UDLM **adopts the ADR/MADR format by reference**, it does not coin its own. DCM keeps its
own ADRs in `architecture/adr/` (the control-plane side); UDLM ADRs here cross-reference them.

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
| [005](ADR-005-mcp-server-type-and-dcm-mcp-surface.md) | MCP as a managed service — `AI.MCPServer` resource type + MCP-capable Provider; and DCM's control plane exposed *as* an MCP surface (`dcm-mcp`, agent proposes / policy disposes); an MCP tool = a `Capability` | Proposed |
