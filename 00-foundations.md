# DCM — Foundational Abstractions


**Document Status:** ✅ Complete
**Document Type:** Architecture Foundation — Read This First
**Related Documents:** [Data Model Context](00-context-and-purpose.md) | [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)

---

## 1. The Three Abstractions

DCM is built on three foundational abstractions. Every concept in the architecture is an instance of one of these three — or a combination of them. There is no fourth.

```
┌─────────────────────────────────────────────────────────────────┐
│                          DATA                                    │
│                                                                  │
│  Everything that exists, is stored, has a lifecycle, and flows  │
│  through the system. Entities, layers, policies, accreditations, │
│  audit records, groups, relationships — all Data.                │
└──────────────────────────┬──────────────────────────────────────┘
                           │ flows through
              ┌────────────┴────────────┐
              ▼                         ▼
┌─────────────────────┐   ┌─────────────────────────────────────┐
│      PROVIDER        │   │              POLICY                  │
│                      │   │                                      │
│  Every external      │   │  Every rule that fires on Data,      │
│  component DCM       │   │  decides what happens, transforms    │
│  calls or that       │   │  values, or enforces constraints.    │
│  calls DCM.          │   │                                      │
│  Twelve typed       │   │  Eight typed output schemas.       │
│  capability          │   │  One evaluation algorithm.           │
│  extensions.         │   │  Same lifecycle for all.             │
│  One base contract.  │   │                                      │
└─────────────────────┘   └─────────────────────────────────────┘
```

**The runtime that connects them:**

```
Event (Data state change)
  → Policy Engine evaluates all matching Policies
  → Policies produce decisions / mutations / actions
  → Actions invoke Providers or produce new Data
  → New Data triggers new Events
  → Repeat
```

This is the complete DCM operational model. Everything else is a typed specialization of these three abstractions operating through this loop.

---

## 2. DATA — Everything That Exists

**Definition:** Data is any structured artifact in DCM with a type, fields, classification, provenance, and lifecycle state. Data is always versioned, always identified by UUID, and always carries provenance describing where each field value came from.

**The universal properties of all Data:**
- **UUID** — every Data artifact has a universally unique identifier, stable across its full lifecycle
- **Type** — every Data artifact has a declared type that determines its schema and valid field set
- **Lifecycle state** — every Data artifact is in exactly one lifecycle state at any moment
- **Artifact metadata** — every Data artifact carries a standard metadata block (handle, version, status, owned_by, created_by, created_via)
- **Provenance** — every field in every Data artifact carries lineage metadata describing its origin and all modifications
- **Data classification** — every field carries a classification (public → classified) governing what may cross interaction boundaries
- **Immutability if versioned** — once a version is published, it cannot be modified; changes produce new versions
- **Contributor identity** — every Data artifact records who contributed it (platform admin, consumer/tenant, service provider, or peer DCM) and what review it received before activation. DCM defaults to a federated contribution model — all authorized actor types can create Data within the bounds their role permits. See [Federated Contribution Model](28-federated-contribution-model.md).

**The complete Data taxonomy:**

| Data Type | Description | Storage |
|-----------|-------------|---------|
| **Resource Entity** | A realized infrastructure resource; the primary managed thing | Realized Store |
| **Process Entity** | An ephemeral execution (job, playbook, pipeline) | Realized Store |
| **Composite Entity** | A Meta Provider composition of Resource Entities | Realized Store |
| **Intent State** | Consumer's raw declaration before processing | Intent Store (GitOps) |
| **Requested State** | Fully assembled, policy-validated provider payload | Requested Store |
| **Discovered State** | What actually exists per discovery observation | Discovered Store |
| **Data Layer** | A versioned artifact contributing fields to assembly | Layer Store (GitOps) |
| **Resource Type Specification** | Schema definition for a resource type | Registry |
| **Provider Catalog Item** | Provider-specific instantiation of a Resource Type Spec | Registry |
| **Policy** | A rule artifact with match conditions and output schema | Policy Store (GitOps) |
| **Policy Group** | A collection of policies grouped by concern_type | Policy Store (GitOps) |
| **Policy Profile** | A composition: one posture + zero or more compliance domains | Policy Store (GitOps) |
| **Accreditation** | A compliance certification artifact | Accreditation Store |
| **Sovereignty Zone** | A geopolitical/regulatory boundary artifact | Config Store |
| **Registration Token** | A scoped authorization artifact for provider registration | Token Store |
| **DCMGroup** | A grouping artifact (tenant_boundary, resource_grouping, etc.) | Config Store |
| **Drift Record** | A comparison result artifact | Operational Store |
| **Audit Record** | An immutable event record | Audit Store |
| **Governance Matrix Rule** | A boundary control rule artifact | Policy Store (GitOps) |
| **Orphan Candidate** | A potentially untracked resource artifact | Operational Store |

**How Data flows — the four lifecycle stages:**

Every Resource Entity flows through four stages. These are not four separate things — they are the same entity at four different lifecycle stages, stored as four data domains in DCM's PostgreSQL database, each with distinct immutability and access patterns:

```
Consumer Intent
    │ raw consumer declaration
    ▼
Intent State ──────────────────────────────────── intent_records (append-only)
    │ layer assembly + policy evaluation
    ▼
Requested State ────────────────────────────────── requested_records (append-only)
    │ provider execution
    ▼
Realized State ─────────────────────────────────── realized_entities (versioned snapshots)
    │ independent observation
    ▼
Discovered State ───────────────────────────────── discovered_records (ephemeral)
```

**How Data is composed — the layering model:**

Data fields are assembled from multiple contributing layers in a deterministic precedence order. See [Data Model Context](00-context-and-purpose.md) and [Layering and Versioning](03-layering-and-versioning.md) for the complete assembly algorithm.

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

**The complete Provider taxonomy:**

| Provider Type | Capability | Data direction |
|--------------|-----------|---------------|
| **Service Provider** | Realizes infrastructure resources | DCM → Provider → DCM |
| **Information Provider** | Serves authoritative external data | DCM queries → Provider responds |
| **Storage Provider** | Persists DCM state | DCM reads/writes ↔ Provider |

| **Policy Provider** | Evaluates policies externally | DCM sends payload → Provider decides |
| **Credential Provider** | Manages secrets and credentials | DCM requests → Provider issues |
| **Auth Provider** | Authenticates identities | DCM verifies → Provider confirms |
| **Notification Provider** | Delivers notifications | DCM sends envelope → Provider delivers |
| **Message Bus Provider** | Async event streaming | DCM publishes/subscribes ↔ Provider |
| **Registry Provider** | Serves the resource type registry | DCM pulls → Provider serves |
| **Peer DCM** | Another DCM instance (federation) | DCM ↔ DCM via federation tunnel |
| **ITSM Provider** | Bidirectional integration with ITSM systems (ServiceNow, Jira, Remedy, etc.); creates/updates ITSM records from DCM events; routes ITSM approvals back to DCM | DCM → ITSM (outbound) / ITSM → DCM (inbound) |

**The unified Provider base contract** is defined in [A-provider-contract.md](A-provider-contract.md). All twelve Provider types implement this base contract. What varies is the capability declaration — what operations the Provider exposes and what data flows in which direction.

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

**The complete Policy taxonomy:**

| Policy Type | Fires on | Output |
|-------------|---------|--------|
| **GateKeeper** | Request payload | `allow` or `deny` with reason |
| **Validation** | Request payload | `pass` or `fail` with field-level details |
| **Transformation** | Request payload | `mutations[]` — field additions, changes, locks |
| **Recovery** | Failure/timeout trigger condition | `action` + parameters (DRIFT_RECONCILE, DISCARD_AND_REQUEUE, etc.) |
| **Orchestration Flow** | Payload type events | `flow_directive` — sequence ordering for pipeline steps |
| **Governance Matrix Rule** | Any cross-boundary interaction | `ALLOW / DENY / ALLOW_WITH_CONDITIONS / STRIP_FIELD / REDACT / AUDIT_ONLY` |
| **Lifecycle Policy** | Relationship events | `action` on the related entity (save, destroy, notify, cascade) |
| **ITSM Action** | DCM events (state transitions, drift, realization) | `itsm_action` — create/update/close ITSM records; non-blocking by default |

**The unified Policy base contract** is defined in [B-policy-contract.md](B-policy-contract.md). All eight Policy types implement this base contract. What varies is the output schema.

**Policies as orchestration — two levels that compose:**

*Level 1 — Named Workflow Artifacts (explicit, visible, auditable):*
An Orchestration Flow Policy with `concern_type: orchestration_flow` and `ordered: true` is a named workflow. It declares steps in explicit sequence. Named workflows are first-class Data artifacts — versioned, GitOps-managed, profile-bound. Adding an explicit pipeline step = adding a step to a workflow Policy artifact.

*Level 2 — Dynamic Policies (conditional, inline):*
GateKeeper, Transformation, Recovery, and Governance Matrix Policies fire when their match conditions are satisfied — within or alongside workflow steps, without being declared in the workflow. Adding conditional behavior = writing a dynamic policy.

Both levels are evaluated by the same Policy Engine and triggered through the same Request Orchestrator event bus. They compose naturally: a named workflow provides the sequence skeleton; dynamic policies provide conditional behavior within it.

**The Governance Matrix as Policy:** The Governance Matrix rules (doc 27) are typed Policies with the `boundary_control` output schema. They fire at every cross-boundary interaction. They follow the same match conditions, enforcement levels, and lifecycle as all other Policies. The governance matrix is not a separate system — it is the Policy abstraction applied at interaction boundaries.

---

## 5. The Runtime — Connecting the Three

The Request Orchestrator and Policy Engine are the runtime that connects the three abstractions. They are not a fourth abstraction — they are the implementation machinery.

```
┌─────────────────────────────────────────────────────────┐
│                   Request Orchestrator                   │
│              (event bus — not a sequencer)               │
│                                                          │
│  Receives events → routes to Policy Engine               │
│  Policy Engine evaluates all matching Policies           │
│  Results: invoke Providers OR produce new Data           │
│  New Data → new events → new Policy evaluations          │
└─────────────────────────────────────────────────────────┘
```

**Key runtime properties:**
- The Request Orchestrator contains no pipeline logic — Policies define what happens
- Every pipeline step is a Policy firing on a payload type event
- Parallel execution: Policies with no data dependencies evaluate concurrently
- Static flows: Orchestration Flow Policies with `ordered: true`
- Dynamic flows: conditional Policies that fire based on payload state

**Control plane components as runtime specializations (nine total):**

The components in [Control Plane Components](25-control-plane-components.md) are specialized runtime implementations, not separate abstractions:

| Component | Abstraction it implements |
|-----------|--------------------------|
| Request Orchestrator | The runtime event bus |
| Policy Engine | The runtime Policy evaluator |
| Placement Engine | Policy evaluation specialized for provider selection |
| Cost Analysis | Information Provider (internal; data derivation) |
| Lifecycle Constraint Enforcer | Scheduled Recovery Policy trigger |
| Discovery Scheduler | Scheduled Provider invocation |
| Notification Router | Transformation Policy + Notification Provider invocation |
| Drift Reconciliation | Data comparison producing new Data (drift records) |
| Search Index | Storage Provider sub-type (queryable projection) |

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

> **Full specification:** See [Design Priorities](00-design-priorities.md) for the complete priority framework, decision framework, profile scaling table, and DPO-001–006 system policies.


Every design decision in DCM is evaluated against this priority order. When priorities conflict, higher priorities win. When there is no conflict, all four apply simultaneously.

**1. Industry best practices for security**
Security is not a feature or a profile option. It is the baseline that every other design decision must respect. Where security and convenience conflict, security wins — but the design must find a way to make the secure path the easy path. A security model that is routinely bypassed because it is too burdensome has failed at both security and usability.

*In practice:* Security properties — value separation, non-transferable credentials, scoped permissions, rotation, audit, revocation propagation — are architecturally present in every profile. What profiles control is the enforcement strictness, operational automation, and threshold values. A `minimal` profile does not disable security; it implements security with minimal operational overhead.

**2. Ease of use**
DCM exists to enable self-service for application teams. If the right path is also the hard path, teams will find other paths. The goal is to make secure, governed, auditable infrastructure management the path of least resistance — not the path of compliance obligation.

*In practice:* Profile defaults should eliminate configuration burden for common cases. The standard pipeline should auto-approve ordinary requests without human intervention. Policy authoring should not require Rego expertise for common patterns. The Flow GUI, scoring model, and contribution endpoints all serve this priority.

**3. Extensibility and capability grouping**
The profile system, compliance domain overlays, policy groups, and registry governance exist to make DCM adaptable to arbitrary organizational requirements without code changes. This priority serves at scale — a platform that can only be configured by modifying source code is not a platform.

*In practice:* New compliance requirements should be expressible as policy additions within the existing framework. New provider types should fit the existing Provider base contract. New deployment contexts should be addressable through profile configuration.

**4. Fit for purpose (always required)**
DCM must actually manage data center infrastructure lifecycle. All of the above is in service of this purpose — not independent of it. An architecturally beautiful system that cannot provision a VM, track its drift, and decommission it cleanly has failed at its reason for existing.

*In practice:* Design decisions that serve priorities 1–3 but break the end-to-end lifecycle (request → provision → operate → decommission) are not acceptable. Every capability added must have a clear answer to "how does this serve the lifecycle management mission?"

---

**The implication for profiles:** A `minimal` profile is "security with minimal operational overhead" — not "minimal security." The security architecture is present and correct in every profile. What varies is how much automation, how strict the thresholds, and how much manual intervention is acceptable. This is the principle that makes DCM trustworthy in a homelab and in a sovereign government deployment using the same codebase.

