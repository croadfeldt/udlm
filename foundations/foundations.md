# DCM — Foundational Abstractions


**Document Status:** ✅ Complete
**Document Type:** Architecture Foundation — Read This First
**Related Documents:** [Data Model Context](context-and-purpose.md) | [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)

---

## 1. The Three Abstractions

DCM is built on three foundational abstractions. Every concept in the architecture is an instance of one of these three — or a combination of them. There is no fourth.

```mermaid
flowchart TD
    DATA["<b>DATA</b><br/>Everything that exists, is stored, has a lifecycle, and flows through the system. Entities, layers, policies, accreditations, audit records, groups, relationships — all Data."]
    PROVIDER["<b>PROVIDER</b><br/>Every external component DCM calls or that calls DCM.<br/>Typed capability extensions.<br/>One base contract."]
    POLICY["<b>POLICY</b><br/>Every rule that fires on Data, decides what happens, transforms values, or enforces constraints.<br/>Typed output schemas.<br/>One evaluation algorithm.<br/>Same lifecycle for all."]
    DATA -->|flows through| PROVIDER
    DATA -->|flows through| POLICY
```

**The runtime that connects them — a re-entrant convergence loop:**

The three abstractions are **peers** in the decomposition — no fixed importance order. At *runtime* they operate as a **trigger-driven control loop**, not a one-way pipeline: each stage is entered when its conditions are met and emits a completion/validation signal, and those signals are the triggers for the next stage. Crucially, provider outcomes feed back — **policy is re-entrant**.

```
Event  (a Data state change — or a provider change or DENIAL)
  → Policy Engine evaluates all matching Policies (each guarded by its conditions)
  → Policies produce decisions / mutations / actions, and signal convergence
  → Actions invoke Providers or produce new Data
  → a Provider acting, changing, or denying the request emits new Events
  → which re-trigger Policy — the loop re-enters, it does not exit
  → Repeat until the target state converges, or a terminal failure is surfaced
```

This is the complete DCM operational model: **Data · Policy · Provider are peers, connected by an event-condition-action loop in which policy is re-entrant** — re-evaluated on every provider change, denial, or drift. Everything else is a typed specialization operating through this loop. The loop's soundness rules — bounded convergence, idempotent re-entry, and causal audit of every trigger — are set out in [ADR-006 — Convergence control model](../docs/adr/ADR-006-convergence-control-model.md).

---

## 2. DATA — Everything That Exists

**Definition:** Data is any structured artifact in DCM with a type, fields, classification, provenance, and lifecycle state. Data is always versioned, always identified by UUID, and always carries provenance describing where each field value came from.

**The universal properties of all Data:**
- **UUID** — every Data artifact has a universally unique identifier, stable across its full lifecycle
- **Type** — every Data artifact has a declared type that determines its schema and valid field set
- **Lifecycle state** — every Data artifact is in exactly one lifecycle state at any moment
- **Artifact metadata** — every Data artifact carries a standard metadata block (handle, version, status, owned_by, created_by, created_via, contact modes); the **complete v1 field set** is defined canonically in [layering-and-versioning.md](layering-and-versioning.md) §4b, not a representative sample
- **Provenance** — every field in every Data artifact carries lineage metadata describing its origin and all modifications
- **Data classification** — every field carries a classification (public → classified) governing what may cross interaction boundaries
- **Immutability if versioned** — once a version is published, it cannot be modified; changes produce new versions
- **Contributor identity** — every Data artifact records who contributed it (platform admin, consumer/tenant, service provider, or peer DCM) and what review it received before activation. DCM defaults to a federated contribution model — all authorized actor types can create Data within the bounds their role permits. See [Federated Contribution Model](../governance/federated-contribution-model.md).

**The Data taxonomy** — the enumerated Data/resource types (resource and process entities, the four states, data layers, policies and policy groups, accreditations, groups, tokens, drift and audit records, and the rest) are defined canonically in the **[registry](../registry/)** (the Resource Type Specifications and the instance meta-schema). This document defines the Data *abstraction* and its universal properties; it does not restate the member list, so there is a single source of truth and no drift with the registry.

**How Data flows — the four lifecycle stages:**

Data flows through four lifecycle stages — the same entity observed at four points, not four separate things:

```mermaid
flowchart TD
    CI["Consumer Intent"]
    IS["Intent State"]
    RS["Requested State"]
    RLS["Realized State"]
    DS["Discovered State"]
    IS -.-> IR["intent_records (append-only)"]
    RS -.-> RR["requested_records (append-only)"]
    RLS -.-> RE["realized_entities (versioned snapshots)"]
    DS -.-> DR["discovered_records (ephemeral)"]
    CI -->|raw consumer declaration| IS
    IS -->|layer assembly + policy evaluation| RS
    RS -->|provider execution| RLS
    RLS -->|independent observation| DS
```

These four stages are defined canonically in **[The Four States](four-states.md)** — this section shows only how Data flows through them, it does not redefine each stage.

**How Data is composed — the layering model:**

Data fields are assembled from multiple contributing layers in a deterministic precedence order. See [Data Model Context](context-and-purpose.md) and [Layering and Versioning](layering-and-versioning.md) for the complete assembly algorithm.

---

## 3. PROVIDER — Everything External

**Definition:** A Provider is any external component that DCM interacts with through a defined contract. Providers receive Data from DCM, act on it, and return Data to DCM. The contract governs how this exchange happens — not what the Provider does internally.

**The universal properties of all Providers:**
- **Registration** — every Provider registers with DCM, declaring its capabilities, sovereignty, and accreditation
- **Health check** — every Provider exposes a health endpoint; DCM monitors it continuously
- **Sovereignty declaration** — every Provider declares where it operates and what jurisdictions it covers
- **Accreditation** — every Provider declares its compliance certifications; DCM enforces these via the Governance Matrix
- **Governance Matrix enforcement** — every interaction with a Provider is subject to the Governance Matrix before data crosses the boundary
- **Zero trust** — every Provider interaction is authenticated and authorized; no implicit trust from network position
- **Lifecycle** — every Provider registration goes through a defined lifecycle (SUBMITTED → VALIDATING → ACTIVE → DEREGISTERED)

The single interface every Provider implements — the base contract, and the capability declaration that distinguishes one Provider type from another — is defined in [provider-contract.md](../contracts/provider-contract.md).

**The Provider taxonomy** — the enumerated Provider types (Service Provider, Information Provider, data store, External Policy Evaluator, credential management service, Auth Provider, notification service, event routing service, Resource Type Registry, Peer realization, ITSM integration, …) and their capability declarations are defined canonically in the **[Provider Contract](../contracts/provider-contract.md)**. This document defines the Provider *abstraction* and its universal properties; the member list lives in one place there, not restated here.

**The unified Provider base contract** is defined in [provider-contract.md](../contracts/provider-contract.md). All Provider types implement this base contract. What varies is the capability declaration — what operations the Provider exposes and what data flows in which direction.

**Peer DCM as Provider:** A federated DCM instance is a typed Provider. The federation tunnel is the Provider's communication channel. Federation routing is policy-governed provider selection. There is no separate "federation abstraction" — federation is the Provider abstraction applied across DCM instances.

---

## 4. POLICY — Everything That Decides

**Definition:** A Policy is a rule artifact that fires when Data matches declared conditions, produces a typed output (decision, mutation, action, or directive), and is enforced according to a declared level. Policies govern every transition, transformation, and constraint in DCM.

**The universal properties of all Policies:**
- **Match conditions** — every Policy declares when it fires, using the four governance matrix axes (subject, data, target, context) or payload type + field conditions
- **Typed output schema** — every Policy produces one of seven output types; the output type determines how the Policy Engine applies the result
- **Enforcement level** — hard (cannot be overridden) or soft (can be tightened by more-specific policies)
- **Domain precedence** — policies at more-specific domains win within their concern type; system > platform > tenant > resource_type > entity
- **Lifecycle** — every Policy follows the standard artifact lifecycle (developing → proposed → active → deprecated → retired)
- **Shadow mode** — proposed Policies execute against real traffic without applying results; safe validation before activation
- **Audit** — every Policy evaluation produces an audit record regardless of outcome

UDLM is deliberately **policy-language-agnostic**: it defines the policy *contract* (match conditions, typed output schemas, evaluation model) — not a policy language. What data is in scope during evaluation, and the required output schema per policy type, are defined in [policy-contract.md](../contracts/policy-contract.md).

**The Policy taxonomy** — the enumerated Policy types (Validation, Transformation, Recovery, Orchestration Flow, Governance Matrix Rule, Lifecycle, ITSM Action, …) and their typed output schemas are defined canonically in the **[Policy Contract](../contracts/policy-contract.md)**. This document defines the Policy *abstraction* and its universal properties; the member list is not restated here.

**The unified Policy base contract** is defined in [policy-contract.md](../contracts/policy-contract.md). All Policy types implement this base contract. What varies is the output schema.

**Policies as orchestration — two levels that compose:**

*Level 1 — Named Workflow Artifacts (explicit, visible, auditable):*
An Orchestration Flow Policy with `concern_type: orchestration_flow` and `ordered: true` is a named workflow. It declares steps in explicit sequence. Named workflows are first-class Data artifacts — versioned, GitOps-managed, profile-bound. Adding an explicit pipeline step = adding a step to a workflow Policy artifact.

*Level 2 — Dynamic Policies (conditional, inline):*
Compliance-class Validation Policy, Transformation, Recovery, and Governance Matrix Policies fire when their match conditions are satisfied — within or alongside workflow steps, without being declared in the workflow. Adding conditional behavior = writing a dynamic policy.

Both levels are evaluated by the same Policy Engine and triggered through the same Request Orchestrator event bus. They compose naturally: a named workflow provides the sequence skeleton; dynamic policies provide conditional behavior within it.

**The Governance Matrix as Policy:** The Governance Matrix rules (see [`governance-matrix.md`](../governance/governance-matrix.md)) are typed Policies with the `boundary_control` output schema. They fire at every cross-boundary interaction. They follow the same match conditions, enforcement levels, and lifecycle as all other Policies. The governance matrix is not a separate system — it is the Policy abstraction applied at interaction boundaries.

---

## 5. The Runtime — Connecting the Three

The Request Orchestrator and Policy Engine are the runtime that connects the three abstractions. They are not a fourth abstraction — they are the implementation machinery.

```mermaid
flowchart TD
    subgraph RO["Request Orchestrator (event bus — not a sequencer)"]
        direction TB
        A["Receives events → routes to Policy Engine"]
        B["Policy Engine evaluates all matching Policies"]
        C["Results: invoke Providers OR produce new Data"]
        D["New Data → new events → new Policy evaluations"]
        A --> B --> C --> D
    end
```

**Key runtime properties:**
- The Request Orchestrator contains no pipeline logic — Policies define what happens
- Every pipeline step is a Policy firing on a payload type event
- Parallel execution: Policies with no data dependencies evaluate concurrently
- Static flows: Orchestration Flow Policies with `ordered: true`
- Dynamic flows: conditional Policies that fire based on payload state

**Control plane components as runtime specializations (nine total):**

The control plane components are specialized runtime implementations, not separate abstractions (implementation-specific; see DCM repo):

| Component | Abstraction it implements |
|-----------|--------------------------|
| Request Orchestrator | The runtime event bus |
| Policy Engine | The runtime Policy evaluator |
| Placement Engine | Policy evaluation specialized for provider selection |
| Cost Analysis | Information Provider (internal; data derivation) |
| Lifecycle Constraint Enforcer | Scheduled Recovery Policy trigger |
| Discovery Scheduler | Scheduled Provider invocation |
| Notification Router | Transformation Policy + notification service invocation |
| Drift Reconciliation | Data comparison producing new Data (drift records) |
| Search Index | PostgreSQL store contract (queryable projection) |

---

## 6. Extension Points

DCM is designed to be extended without modifying the core. Every extension fits within the three abstractions:

**Extending Data:** New entity types, new artifact types, new resource types, new group classes — all are typed extensions of the Data abstraction. Register them in the Resource Type Registry or DCMGroup registry.

**Extending Providers:** New provider types (a Billing Provider, a CMDB Provider, an AI/ML Provider) — implement the unified Provider base contract with a new capability declaration extension. Register in the Provider Type Registry.

**Extending Policies:** New policy types, new governance matrix rules, new orchestration flows — implement the unified Policy base contract with a new output schema. Register in the Policy Store via GitOps.

**The extension principle:** If you can express it as Data, Provider, or Policy — it belongs in DCM. If you cannot express it within these three abstractions, it is either a runtime implementation detail or a genuinely novel concept that should be explicitly identified and documented as such.

---

## 7. The Core Ethos

These three abstractions serve DCM's core ethos:

**Effective at the core mission** — managing the lifecycle of infrastructure resources across a sovereign private cloud. The Data abstraction ensures every resource is tracked, versioned, and auditable. The Provider abstraction ensures every external integration is governed and trustworthy. The Policy abstraction ensures every decision is declared, reproducible, and auditable.

**Easy to use** — consumers interact with Data (submit an intent, receive a resource). Policies govern what happens without consumers needing to understand them. Providers handle the implementation details.

**Easy to implement** — implementors implement one base contract (Provider) with a typed capability extension. The Policy Engine handles all policy evaluation. The Data model handles all storage and provenance.

**Easy to extend and integrate** — add a new provider type by implementing the base contract. Add a new policy type by defining an output schema. Add a new data type by defining a schema. No core changes required.

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*


---

## Design Priority Order

> **Full specification:** See [Design Priorities](../design-principles/design-priorities.md) for the complete priority framework, decision framework, profile scaling table, and DPO-001–006 system policies.


Every design decision is evaluated against a fixed priority order; when priorities conflict, higher wins, and where there is no conflict all four apply. Highest first:

1. **Industry best practices for security** — the baseline every decision respects; where security and convenience conflict, security wins (and the design makes the secure path the easy path).
2. **Ease of use** — the secure, governed, auditable path must be the path of least resistance, or teams route around it.
3. **Extensibility and capability grouping** — adapt to arbitrary organizational requirements through profiles / policies / capabilities, not code changes.
4. **Fit for purpose (always required)** — none of the above matters if the system cannot provision, track drift on, and cleanly decommission real infrastructure.

The full framework — the decision procedure, the profile scaling table, and the `DPO-*` policies — is defined once in [Design Priorities](../design-principles/design-priorities.md) and is not restated here.

---

**The implication for profiles:** A `minimal` profile is "security with minimal operational overhead" — not "minimal security." The security architecture is present and correct in every profile. What varies is how much automation, how strict the thresholds, and how much manual intervention is acceptable. This is the principle that makes DCM trustworthy in a homelab and in a sovereign government deployment using the same codebase.

**Profile scope (current vs. future).** In this version a profile is **deployment-scoped** — one active profile applies **platform-wide** (a homelab or a single sovereign deployment selects one). The model is deliberately designed so profiles can later be **group-scoped** — bound to a Tenant, a Service, or a compliance domain and **composing over** the platform default (e.g. a per-Tenant `sovereign` profile inside an otherwise `standard` platform). Group-scoped profiles are future work; today, read "profile" as platform-wide — but do not assume it is *only* platform-wide. Any profile-governed field (time-sync tolerance per ADR-005, provenance policy group, credential assurance floor, version policy) is a candidate for group-scoped override once the scoping mechanism lands. See [ADR-007 — Profile model](../docs/adr/ADR-007-profile-model.md) for the full model: profiles are composed **sets** (policies + operational config + required mechanics), not levels; they set floors; and modifying a built-in forks a new custom profile.

