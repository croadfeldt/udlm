# UDLM — Foundational Abstractions


**Document Status:** ✅ Complete
**Document Type:** Data Model Foundation — Read This First
**Related Documents:** [Data Model Context](context-and-purpose.md) | [Provider Contract](../contracts/provider-contract.md) | [Policy Contract](../contracts/policy-contract.md)

---

## 1. The Three Abstractions

UDLM is built on three foundational abstractions. Every concept in the model is an instance of one of these three — or a combination of them. There is no fourth.

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
│  component a         │   │  decides what happens, transforms    │
│  realization calls   │   │  values, or enforces constraints.    │
│  or that calls it.   │   │                                      │
│  Typed capability    │   │  Typed output schemas.               │
│  extensions over     │   │  One evaluation model.               │
│  one base contract.  │   │  Same lifecycle for all.             │
└─────────────────────┘   └─────────────────────────────────────┘
```

> The two arrows are **peers, not a sequence** — any Data can flow directly to a Provider *or* a Policy; there is no fixed Data→Policy→Provider order. Both emit new Data that re-enters at the top, so the diagram is a **cycle**, not a pipeline. The loop is the invariant, not the order.

The three abstractions compose through a simple loop: a change in **Data** is an event; **Policy** evaluates against that data and decides, transforms, or constrains; decisions invoke **Providers** or produce new **Data**, which is itself a new event. *How a specific realization implements that loop — the event bus, the policy evaluator, the named runtime components — is realization architecture, not part of the data model. See §5 and the DCM architecture documentation.*

---

## 2. DATA — Everything That Exists

**Definition:** Data is any structured artifact with a type, fields, classification, provenance, and lifecycle state. Data is always versioned, always identified by UUID, and always carries provenance describing where each field value came from.

**The universal properties of all Data:**
- **UUID** — every Data artifact has a universally unique identifier, stable across its full lifecycle
- **Type** — every Data artifact has a declared type that determines its schema and valid field set
- **Lifecycle state** — every Data artifact is in exactly one lifecycle state at any moment
- **Artifact metadata** — every Data artifact carries a standard metadata block (handle, version, status, owned_by, created_by, created_via)
- **Provenance** — every field in every Data artifact carries lineage metadata describing its origin and all modifications
- **Data classification** — every field carries a classification (public → classified) governing what may cross interaction boundaries
- **Immutability if versioned** — once a version is published, it cannot be modified; changes produce new versions
- **Contributor identity** — every Data artifact records who contributed it (platform admin, consumer/tenant, service provider, or peer realization) and what review it received before activation. The model defaults to a federated contribution model — all authorized actor types can create Data within the bounds their role permits. See [Federated Contribution Model](../governance/federated-contribution-model.md).

**The complete Data taxonomy:**

| Data Type | Description | Store contract |
|-----------|-------------|---------------|
| **Resource Entity** | A realized infrastructure resource; the primary managed thing | State Store (realized) |
| **Process Entity** | An ephemeral execution (job, playbook, pipeline) | State Store (realized) |
| **Composite Entity** | A composition of Resource Entities produced by a Composite Service request (see [`composite-service-model.md`](../entities/composite-service-model.md)) | State Store (realized) |
| **Intent State** | Consumer's raw declaration before processing | Commit Log (intent) |
| **Requested State** | Fully assembled, policy-validated provider payload | State Store (requested) |
| **Discovered State** | What actually exists per discovery observation | Discovered stream |
| **Data Layer** | A versioned artifact contributing fields to assembly | Commit Log (layers) |
| **Resource Type Specification** | Schema definition for a resource type | Registry |
| **Provider Catalog Item** | Provider-specific instantiation of a Resource Type Spec | Registry |
| **Policy** | A rule artifact with match conditions and output schema | Commit Log (policy) |
| **Policy Group** | A collection of policies grouped by concern_type | Commit Log (policy) |
| **Policy Profile** | A composition: one posture + zero or more compliance domains | Commit Log (policy) |
| **Accreditation** | A compliance certification artifact | State Store |
| **Sovereignty Zone** | A geopolitical/regulatory boundary artifact | State Store (config) |
| **Registration Token** | A scoped authorization artifact for provider registration | State Store (tokens) |
| **DCMGroup** | A grouping artifact (tenant_boundary, resource_grouping, etc.) | State Store (config) |
| **Drift Record** | A comparison result artifact | State Store (operational) |
| **Audit Record** | An immutable event record | Audit Store |
| **Governance Matrix Rule** | A boundary control rule artifact | Commit Log (policy) |
| **Orphan Candidate** | A potentially untracked resource artifact | State Store (operational) |

*The store contracts (Commit Log, State Store, Audit Store, Discovered stream) are defined by contract, not technology — a realization binds them to concrete stores per profile and sovereignty/tenancy policy ([data-model-core](data-model-core.md) §6, ruling D1).*

**How Data flows — the four lifecycle stages:**

Every Resource Entity flows through four stages. These are not four separate things — they are the same entity at four different lifecycle stages, each with distinct immutability and access patterns:

```
Consumer Intent
    │ raw consumer declaration
    ▼
Intent State ──────────────────────────────────── append-only (Commit Log)
    │ layer assembly + policy evaluation
    ▼
Requested State ────────────────────────────────── append-only (Commit Log → State Store)
    │ provider execution
    ▼
Realized State ─────────────────────────────────── versioned snapshots (State Store)
    │ independent observation
    ▼
Discovered State ───────────────────────────────── ephemeral (Discovered stream)
```

**How Data is composed — the layering model:**

Data fields are assembled from multiple contributing layers in a deterministic precedence order. See [Data Model Context](context-and-purpose.md) and [Layering and Versioning](layering-and-versioning.md) for the complete assembly algorithm.

---

## 3. PROVIDER — Everything External

**Definition:** A Provider is any external component that a realization interacts with through a defined contract. Providers receive Data, act on it, and return Data. The contract governs how this exchange happens — not what the Provider does internally.

**The universal properties of all Providers:**
- **Registration** — every Provider registers with the realization, declaring its capabilities, sovereignty, and accreditation
- **Health check** — every Provider exposes a health endpoint that the realization monitors continuously
- **Sovereignty declaration** — every Provider declares where it operates and what jurisdictions it covers
- **Accreditation** — every Provider declares its compliance certifications, enforced via the Governance Matrix
- **Governance Matrix enforcement** — every interaction with a Provider is subject to the Governance Matrix before data crosses the boundary
- **Zero trust** — every Provider interaction is authenticated and authorized; no implicit trust from network position
- **Lifecycle** — every Provider registration goes through a defined lifecycle (SUBMITTED → VALIDATING → ACTIVE → DEREGISTERED)

**The complete Provider taxonomy:**

| Provider Type | Capability | Data direction |
|--------------|-----------|---------------|
| **Service Provider** | Realizes infrastructure resources | realization → provider → realization |
| **Information Provider** | Serves authoritative external data | realization queries → provider responds |
| **data store** | Persists state | realization reads/writes ↔ provider |
| **External Policy Evaluator** | Evaluates policies externally | realization sends payload → provider decides |
| **credential management service** | Manages secrets and credentials | realization requests → provider issues |
| **Auth Provider** | Authenticates identities | realization verifies → provider confirms |
| **notification service** | Delivers notifications | realization sends envelope → provider delivers |
| **event routing service** | Async event streaming | realization publishes/subscribes ↔ provider |
| **Resource Type Registry** | Serves the resource type registry | realization pulls → provider serves |
| **Peer realization** | Another UDLM-conformant instance (federation) | realization ↔ realization via federation tunnel |
| **ITSM integration** | Bidirectional integration with ITSM systems (ServiceNow, Jira, Remedy, etc.); creates/updates ITSM records from realization events; routes ITSM approvals back | realization → ITSM (outbound) / ITSM → realization (inbound) |

**The unified Provider base contract** is defined in [provider-contract.md](../contracts/provider-contract.md). All Provider types implement this base contract. What varies is the capability declaration — what operations the Provider exposes and what data flows in which direction. (See [capability-discovery.md](../contracts/capability-discovery.md) for the unified capability model that supersedes fixed provider typing.)

**Peer realization as Provider:** A federated peer is a typed Provider. The federation tunnel is the Provider's communication channel. Federation routing is policy-governed provider selection. There is no separate "federation abstraction" — federation is the Provider abstraction applied across instances.

---

## 4. POLICY — Everything That Decides

**Definition:** A Policy is a rule artifact that fires when Data matches declared conditions, produces a typed output (decision, mutation, action, or directive), and is enforced according to a declared level. Policies govern every transition, transformation, and constraint in the model.

**The universal properties of all Policies:**
- **Match conditions** — every Policy declares when it fires, using the four governance matrix axes (subject, data, target, context) or payload type + field conditions
- **Typed output schema** — every Policy produces one of the typed output types; the output type determines how the result is applied
- **Enforcement level** — hard (cannot be overridden) or soft (can be tightened by more-specific policies)
- **Domain precedence** — policies at more-specific domains win within their concern type; system > platform > tenant > resource_type > entity
- **Lifecycle** — every Policy follows the standard artifact lifecycle (developing → proposed → active → deprecated → retired)
- **Shadow mode** — proposed Policies execute against real traffic without applying results; safe validation before activation
- **Audit** — every Policy evaluation produces an audit record regardless of outcome

**The complete Policy taxonomy:**

| Policy Type | Fires on | Output |
|-------------|---------|--------|
| **Validation Policy** | Request payload | `pass` or `fail` with field-level details; compliance-class: `allow` or `deny` with reason |
| **Transformation** | Request payload | `mutations[]` — field additions, changes, locks |
| **Recovery** | Failure/timeout trigger condition | `action` + parameters (DRIFT_RECONCILE, DISCARD_AND_REQUEUE, etc.) |
| **Orchestration Flow** | Payload type events | `flow_directive` — sequence ordering for pipeline steps |
| **Governance Matrix Rule** | Any cross-boundary interaction | `ALLOW / DENY / ALLOW_WITH_CONDITIONS / STRIP_FIELD / REDACT / AUDIT_ONLY` |
| **Lifecycle Policy** | Relationship events | `action` on the related entity (save, destroy, notify, cascade) |
| **ITSM Action** | Realization events (state transitions, drift, realization) | `itsm_action` — create/update/close ITSM records; non-blocking by default |

**The unified Policy base contract** is defined in [policy-contract.md](../contracts/policy-contract.md). All Policy types implement this base contract. What varies is the output schema.

**Policies as orchestration — two levels that compose:**

*Level 1 — Named Workflow Artifacts (explicit, visible, auditable):*
An Orchestration Flow Policy with `concern_type: orchestration_flow` and `ordered: true` is a named workflow. It declares steps in explicit sequence. Named workflows are first-class Data artifacts — versioned, GitOps-managed, profile-bound. Adding an explicit pipeline step = adding a step to a workflow Policy artifact.

*Level 2 — Dynamic Policies (conditional, inline):*
Compliance-class Validation Policy, Transformation, Recovery, and Governance Matrix Policies fire when their match conditions are satisfied — within or alongside workflow steps, without being declared in the workflow. Adding conditional behavior = writing a dynamic policy.

Both levels are evaluated by the same policy-evaluation model and triggered by the same data-change events. They compose naturally: a named workflow provides the sequence skeleton; dynamic policies provide conditional behavior within it.

**The Governance Matrix as Policy:** The Governance Matrix rules (see [`governance-matrix.md`](../governance/governance-matrix.md)) are typed Policies with the `boundary_control` output schema. They fire at every cross-boundary interaction. They follow the same match conditions, enforcement levels, and lifecycle as all other Policies. The governance matrix is not a separate system — it is the Policy abstraction applied at interaction boundaries.

---

## 5. The Runtime — Connecting the Three (realization concern)

The three abstractions compose through a runtime loop — events routed to policy evaluation, results invoking Providers or producing new Data, new Data raising new events. That runtime — the event bus, the policy evaluator, and the named control-plane components that specialize the abstractions (placement, discovery scheduling, drift reconciliation, notification routing, cost derivation, search indexing, etc.) — is **realization machinery, not part of the data model.**

*See the DCM architecture documentation for the concrete runtime: the Request Orchestrator event bus, the Policy Engine, and the control-plane component roster.*

---

## 6. Extension Points

UDLM is designed to be extended without modifying the core. Every extension fits within the three abstractions:

**Extending Data:** New entity types, new artifact types, new resource types, new group classes — all are typed extensions of the Data abstraction. Register them in the Resource Type Registry or DCMGroup registry.

**Extending Providers:** New provider types (a Billing Provider, a CMDB Provider, an AI/ML Provider) — implement the unified Provider base contract with a new capability declaration extension. Register in the Provider Type Registry.

**Extending Policies:** New policy types, new governance matrix rules, new orchestration flows — implement the unified Policy base contract with a new output schema. Register in the Policy Store via GitOps.

**The extension principle:** If you can express it as Data, Provider, or Policy — it belongs in the model. If you cannot express it within these three abstractions, it is either a realization implementation detail or a genuinely novel concept that should be explicitly identified and documented as such.

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*

> The realization's product ethos (effective / easy to use / easy to implement / easy to
> extend) and its design-priority framework (security-first, ease-of-use, extensibility,
> fit-for-purpose) are DCM design philosophy — see the DCM architecture documentation and
> [Design Priorities](../design-principles/design-priorities.md).
