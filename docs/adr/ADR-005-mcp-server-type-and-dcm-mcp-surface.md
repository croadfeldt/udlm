# UDLM ADR-005: MCP as a managed service (`AI.MCPServer`) + DCM control plane as an MCP surface

**Status:** Proposed
**Date:** 2026-07-04
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `entities/knowledge-family.md` §4.5)
**Related:** `registry/resource-types/ai.mcp-server.yaml` (this ADR's type); `registry/resource-types/compute.container.yaml` (analog); ADR-004 (provider capability declaration); `capability.json` (Capability type — an MCP tool is a machine-invocable capability); DCM ADR-005 (Provider Abstraction); DCM convergence-engine + governance docs
**Tracking:** AI service types as UDLM resource types; agentic operation of the control plane (sovereign-AI-cloud direction)

## Context

MCP (Model Context Protocol) is how AI agents discover and invoke tools. It has **two faces**, and a
data-center manager can relate to each:

1. **MCP servers are managed services.** An MCP server is a container that exposes a toolset over a
   transport — the same operational shape as any other managed service (`Compute.Container`,
   `Observability.LogShipper`): an image, a port/endpoint, auth, config, placement, and a lifecycle.
   Today these run **ad hoc** (rootless containers on a host for some; an orchestrated platform for
   others; some undeployed) with **no inventory, no lifecycle, no governance** — exactly the state a
   declarative control plane exists to remove.
2. **The control plane can *speak* MCP.** The set of operations a data-center manager exposes
   (declare intent, query realized state, request placement, approve a change) is itself a natural
   MCP toolset — which is how an agent would *operate* the estate.

UDLM is where the durable shapes live; DCM is where mechanism and policy live. This ADR decides how
MCP enters both.

## Decision

### 1. Model the MCP server as a first-class Resource type — `AI.MCPServer`

The **server is the Resource** (the thing); *serving tools* is the Service (the act) — consistent
with the Service/Resource taxonomy. `AI.MCPServer` (`family: Resource`, `portability: portable`)
carries as **intent (Data)**: `image`, `transport` (stdio / sse / streamable-http), `backend`,
`toolset`, `auth` (mode + `credential_ref`), `resources`, `network`, and a substrate-agnostic
`placement`. Its **realized outputs**: `endpoint`, `health`, `tools_advertised`, `replicas`. It does
**not** encode a mechanism — a Provider maps it onto whatever substrate it owns.

### 2. Realize it with an MCP-capable Provider (mechanism stays provider-side)

A Provider realizes `AI.MCPServer` onto its substrate. The two substrate classes in `placement`
(`container-platform` = orchestrated; `container-host` = a single rootless-container host) let one
Provider — or two — cover both current deployment styles without UDLM knowing the mechanism. The
convergence engine drives declared → realized (drift detection, recovery), so the estate's MCP
servers become an inventory with health and lifecycle instead of hand-managed processes.

### 3. Expose the DCM control plane *as* an MCP server (`dcm-mcp`) — agent proposes, policy disposes

DCM offers its operations as MCP tools (`list_resources`, `get_resource`, `submit_intent`,
`preview_plan`, `get_convergence_status`, `approve_change`). Agents thereby **operate the data
center conversationally, but every mutation flows through DCM's policy + governance + convergence
engine** — the agent submits *intent*; DCM validates, places, and converges; nothing bypasses
policy. This is the safe seam for agentic infrastructure (versus handing an agent raw platform
credentials), and the concrete shape of the sovereign-AI-cloud direction.

### 4. An MCP tool *is* a capability

An MCP tool is a machine-invocable **Capability** (the existing `Capability` type). `AI.MCPServer`'s
`toolset[].capability_ref` links an advertised tool to a capability-catalog entry, closing the loop:
what a server *offers* (2/3) and what the control plane *exposes to agents* (3) are both capabilities.
The tool/capability registry is the shared vocabulary.

## Data · Policy · Provider (required lens — SPEC-DESIGN §29)

- **Data (UDLM):** the `AI.MCPServer` resource type — the durable shape of an MCP server (toolset,
  transport, auth, placement intent, realized endpoint/health/tools). An MCP tool ⇒ a `Capability`.
- **Policy (DCM):** *placement* (which substrate/Provider realizes a given server); *consumption*
  (which persona/agent may reach which server + toolset); *governance* on the `dcm-mcp` surface
  (which agent-submitted intents auto-apply vs require approval). Convergence reconciles declared ↔
  realized.
- **Provider:** authors the realization mechanism (orchestrated Deployment+Service+Route, or a
  rootless container unit on a host) and reports realized outputs. `dcm-mcp` itself is a control-plane
  component, not a Provider — it is a client-facing surface over the engine.

## Options considered

- **Leave MCP servers unmodeled (manage them ad hoc).** Rejected: no inventory, no lifecycle, no
  governance; drift is invisible — the problem this platform exists to remove.
- **Model an MCP server as just a `Compute.Container`.** Rejected: loses the MCP-specific intent
  (transport, toolset, auth mode, tools_advertised) that placement/consumption/governance need to
  match on; a dedicated type keeps those first-class while reusing the container shape.
- **A generic `Service` supertype instead of `AI.MCPServer`.** Deferred: a service supertype is a
  broader taxonomy decision (see the Service-taxonomy reconciliation); `AI.MCPServer` can adopt/rebase
  onto it later via the registry's `adopts`/`aliases` without breaking consumers.
- **Only do (3) — DCM speaks MCP — and skip the resource type.** Rejected: (1/2) is the low-risk,
  immediately-useful step (organizes the existing fleet); (3) is higher-leverage but larger and rides
  on governance. Do (1/2) first, then (3).

## Consequences

- New registry type `registry/resource-types/ai.mcp-server.yaml` (validates against
  `resource-type-spec.schema.json`). No change to existing types.
- DCM gains (or extends a compute Provider with) an MCP realization backend for the two substrate
  classes; a follow-on DCM ADR specifies the `dcm-mcp` surface + its governance gates.
- `credential_ref` and `auth` presume a required-key/credential entity (bearer/LDAP/mTLS material as
  a referenced secret, not inline) — tracked with the broader required-keys modeling.
- Sequencing: (1/2) resource type + Provider first; (3) `dcm-mcp` agentic surface second, behind
  policy/governance.
