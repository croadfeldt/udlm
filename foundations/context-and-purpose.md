# DCM Data Model — Context and Purpose



**Document Status:** ✅ Complete  
**Related Documents:** [Entity Types](01-entity-types.md) | [Ownership, Sharing, and Allocation](04b-ownership-sharing-allocation.md) | [Four States](02-four-states.md) | [Layering and Versioning](03-layering-and-versioning.md) | [Examples](04-examples.md)

> **Foundation Document Reference**
>
> This document is a detailed reference for a specific domain of the DCM architecture.
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [00-foundations.md](00-foundations.md). All concepts in this document map to one or
> more of those three abstractions.
> See also: [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md)
>
> **This document maps to: DATA**
>
> The Data abstraction — foundational data model, provenance, four lifecycle states



---

## 1. Purpose

The DCM Data Model is the foundational layer upon which the entire DCM framework operates. It is not a storage mechanism or a database schema — it is the **lingua franca of DCM**. Every component in the DCM architecture communicates through the data model in some form, whether reading, writing, validating, enriching, transforming, or comparing data.

The data model exists to solve a problem that is endemic to enterprise IT: **there is no single, trustworthy, consistent representation of infrastructure state**. Tools proliferate, CMDBs diverge, and the result is that no one knows with confidence what exists, what was requested, what was provisioned, or whether the current state matches the intended state.

The DCM Data Model establishes a **unified, versioned, declarative single source of truth** for all infrastructure state across the full lifecycle of every resource DCM manages.

---

## 2. Role in the DCM Architecture

The data model is not owned by any single component — it is the contract between all components. Every major DCM capability acts on data in a specific and well-defined way:

| Component | Relationship to Data |
|-----------|---------------------|
| Request Payload Processor | Assembles and enriches data into a complete request payload |
| Policy Engine | Reads, validates, transforms, and gates data based on policy definitions |
| Service Provider | Consumes data (via Naturalization) and returns data (via Denaturalization) |
| Orchestration | Coordinates component interactions based on data state and dependencies |
| Audit | Records data at every state transition for compliance evidence |
| Drift Reconciliation | Compares versions of data across states to detect and remediate drift |
| Cost Analysis | Derives cost information from data throughout the resource lifecycle |
| Resource Discovery | Produces data representing the current discovered state of resources |
| IDM / IAM | Gates access to data and operations based on identity and role |
| Service Catalog | Exposes available services based on data definitions and RBAC policy |

This means the data model is effectively the **API between all DCM components** — even components that do not communicate directly are coupled through the data model. A well-designed data model makes every component easier to build, test, and evolve independently.

---

## 3. Universal Identity Requirement

Every data object in DCM must have a **UUID (Universally Unique Identifier)**. This is not optional — it is a foundational requirement that applies to every entity in the data model without exception.

UUIDs serve several critical functions:

- **Unambiguous reference** — any component, policy, layer, catalog item, or process that touches a data object can reference it precisely and without ambiguity
- **Provenance anchoring** — every change recorded in a data object's lineage references the UUID of the entity that caused the change
- **Dependency mapping** — relationships between resources, services, and components are expressed as UUID references, never by name alone
- **Audit fidelity** — audit records reference UUIDs, ensuring that even if names or labels change, the audit trail remains accurate and traceable
- **Cross-state correlation** — the same resource across Intent, Requested, Realized, and Discovered states can be correlated via UUID chains

This applies to all entities including but not limited to: resource definitions, catalog items, data layers, policies, policy sets, components, service providers, consumers, and requests.

---

## 4. Field-Level Provenance and Data Lineage

One of the most critical requirements of the DCM Data Model is the ability to trace the complete lineage of any piece of data at any stage of the pipeline. This is not a logging concern — it is a **structural requirement of the data model itself**.

### 4.1 The Requirement

At any point in the DCM pipeline, for any field in any data object, it must be possible to answer:

- What is the current value of this field?
- Where did this value originate? (catalog item, base layer, intermediate layer, policy, consumer input, discovery)
- Has this value been modified since origination?
- If modified:
  - What is the complete history of modifications?
  - Which entity caused each modification? (identified by UUID)
  - What type of entity caused it? (policy, layer, component, provider)
  - When did each modification occur?
  - What was the value before each modification?
  - Why was the modification made? (enrichment, validation, transformation, gatekeeping)
- What is the complete chain of custody of this field from origin to current value?

### 4.2 Why Field-Level Lineage Matters

Document-level versioning alone is insufficient for DCM's requirements. Consider a resource request flowing through the pipeline:

1. Consumer selects a catalog item — catalog item UUID recorded
2. Base resource definition layer applied — base layer UUID recorded, fields established
3. Intermediate layers applied — each layer UUID recorded, field overrides recorded
4. Policy Engine validates — policy UUID recorded, validation outcome recorded
5. Policy Engine enriches — policy UUID recorded, enriched field values and their source recorded
6. Policy Engine transforms — policy UUID recorded, transformation recorded with before/after values
7. Request payload submitted — complete provenance chain intact across all fields

Without field-level provenance, it is impossible to determine after the fact whether a specific field value came from a consumer request, a data layer, a security policy, or a business rule. This ambiguity is unacceptable in a governed, auditable system.

### 4.3 Provenance as a Structural Element

Field-level provenance must be carried within the data object itself — not in an external log. This ensures that:

- The data and its lineage are always co-located and cannot be separated
- Any consumer of the data can inspect its lineage without querying an external system
- Provenance survives data export, migration, and portability scenarios
- The audit capability reads provenance that is intrinsic to the data, not reconstructed from logs

### 4.4 Provenance Metadata Structure

Every field that can be created or modified by any DCM process carries provenance metadata alongside its value. The conceptual structure is:

```yaml
field_name:
  value: <current value>
  metadata:
    # Simple override declaration (Level 2) — most fields only need this
    override: <allow|constrained|immutable>
    # OR matrix declaration (Level 3) — for actor-specific governance
    override_matrix:
      default: <allow|constrained|deny>
      actors: <list of actor permissions>
      trusted_grants: <list of explicit expansion grants>

    # Always present regardless of level
    basis_for_value: <human-readable — why this value was set>
    baseline_value: <the original default before any override>
    locked_by_policy_uuid: <uuid of policy that set this>
    locked_at_level: <global|tenant|user>
    constraint_schema: <JSON Schema — if constrained>

  provenance:
    origin:
      value: <original value>
      source_type: <catalog_item|base_layer|intermediate_layer|service_layer|policy|consumer|discovery|provider>
      source_uuid: <uuid of originating entity>
      timestamp: <ISO 8601 timestamp>
    modifications:
      - sequence: 1
        previous_value: <value before this modification>
        modified_value: <value after this modification>
        source_type: <policy|layer|component|provider>
        source_uuid: <uuid of modifying entity>
        operation_type: <enrichment|transformation|validation|gatekeeping|override|lock|grant>
        actor: <actor type that performed this operation>
        timestamp: <ISO 8601 timestamp>
        reason: <human-readable description of why the change was made>
```

**Note:** The `metadata` block is set exclusively by the Policy Engine. Data layers and the Request Payload Processor never set override control. `operation_type: lock` is used when a GateKeeper policy sets `override: immutable`. `operation_type: grant` is used when a trusted_grant is issued. The three levels of override control are: Level 1 (no declaration — fully overridable), Level 2 (simple `override:` property), Level 3 (full `override_matrix:` with per-actor permissions). See the Layering and Assembly document Section 5a for the complete model.

### 4.5 Provenance Obligations

Every DCM component that reads and modifies data carries a provenance obligation:

| Component | Provenance Obligation |
|-----------|----------------------|
| Request Payload Processor | Record source UUID and type for every field assembled from layers and catalog items |
| Policy Engine | Record policy UUID, operation type, and reason for every field it enriches, transforms, or validates |
| Service Provider (Denaturalization) | Record provider UUID and timestamp for every field returned in the realized payload |
| Resource Discovery | Record provider UUID, discovery timestamp, and interrogation method for every field in the discovered payload |
| Data Layers | Each layer must declare its UUID so downstream provenance records can reference it |
| Catalog Items | Each catalog item must declare its UUID so downstream provenance records can reference it |

Provenance recording is **not optional** for any component that modifies data. A component that modifies data without recording provenance violates the data model contract.

### 4.6 Relationship to Audit

The Audit capability in DCM reads provenance data that is intrinsic to every data object. This means:

- Audit does not reconstruct history from logs — it reads lineage that was recorded at the point of change
- Any data object can be audited at any time, in any state, by any authorized persona
- The audit trail is as durable and immutable as the data itself
- Compliance evidence is produced from the data, not from a separate audit system that could diverge from the data

---

## 5. Foundational Constraints

The DCM Data Model is governed by three foundational constraints that apply universally and without exception:

### 5.1 Declarative

Data in DCM describes **what something is or should be**, not how to achieve it. Every entity in the data model is a complete, self-describing statement of state. The procedures required to achieve that state are the concern of the Service Provider, not the data model.

This means:
- A resource definition declares its desired configuration, not the steps to configure it
- A policy declares its conditions and outcomes, not its execution logic
- A layer declares its overrides, not the merge algorithm used to apply them

### 5.2 Idempotent in Operation

Applying the same data to the same system multiple times must always produce the same result. No operation on DCM data should have different outcomes based on how many times it has been applied.

This is critical for:
- **Drift reconciliation** — reapplying desired state to a drifted resource must produce correct results
- **DC rehydration** — replaying the full set of declared states must reconstruct the environment correctly
- **Retry scenarios** — failed operations can be safely retried without risk of inconsistent state
- **Audit and compliance** — the same data, applied by anyone at any time, produces the same verifiable outcome

### 5.3 Immutable if Versioned

Once a version of any entity is published, it cannot be modified. If a change is required, a new version must be created. The previous version remains intact and accessible.

This constraint is what makes the following capabilities trustworthy:
- **Audit trails** — every state at every point in time is preserved and verifiable
- **Drift detection** — comparison between states is meaningful because neither state can change retroactively
- **Intent portability** — a previously declared intent can be replayed against current policies with confidence that the original intent is unchanged
- **Rollback** — reverting to a previous version is always possible because previous versions are never destroyed
- **Chain of trust** — the provenance of any configuration can be traced through an unbroken chain of immutable versions

---

## 5a. Artifact Metadata Standard

Every DCM artifact — layers, policies, resource types, catalog items, provider registrations, entity definitions, and all other defined or stored objects — carries a universal **Artifact Metadata** block. This is a structural requirement that applies to all artifacts without exception.

### The Purpose

Artifact metadata answers: **who created this, when, who owns it, what changed, and how do we contact them?** It is the identity and accountability record for the artifact itself — distinct from field-level provenance which tracks data value lineage.

### The Five Artifact Statuses

All DCM artifacts follow a five-status lifecycle:

| Status | Meaning | Key Behavior |
|--------|---------|-------------|
| `developing` | In active development | Dev mode / dev pipeline only. Not applied in production. |
| `proposed` | Submitted for validation | Shadow execution for policies — output captured, not applied. In PR review for data artifacts. |
| `active` | Live and governing | Applied to all relevant requests. |
| `deprecated` | Being phased out | Still works, replacement available, warning on use. |
| `retired` | End of life | Cannot be used. Terminal status. |

### Key Design Decisions

**created_by vs owned_by:** Deliberately separate. The creator is the audit record — who physically submitted the artifact. The owner is the accountability record — who is responsible and receives notifications for conflicts, deprecation warnings, and policy violations.

**Contact info — two modes:** When an Identity Provider is registered, the `uuid` field links to the IdP record and `display_name` is a non-authoritative display cache. In standalone/air-gapped mode, `uuid` is absent and `display_name` + `email` are the primary identity fields. Both modes are fully supported.

**created_via:** Declares the ingestion path — `pr` (full GitOps review history), `api` (direct submission), `migration` (imported, limited provenance), `system` (DCM-created). Makes audit quality transparent.

**Proposed shadow execution:** Policy artifacts in `proposed` status execute in shadow mode against real traffic — output is captured and reported but never applied. Enables safe validation before activation.

See [Data Layers and Assembly — Section 4b](03-layering-and-versioning.md) for the complete artifact metadata structure and all field definitions.

---

## 6. The Four States

DCM tracks the lifecycle of every resource through four distinct states. Together, these four states provide complete visibility into the gap between what was wanted, what was asked for, what was built, and what actually exists.

### 6.1 Intent State

The **Intent State** represents what a consumer wants to happen. It is the declared desire, captured at the moment a consumer initiates a request, before any processing, validation, or enrichment has occurred.

- **When it is created:** When a consumer submits a request via the Web UI or Consumer API
- **Where it is stored:** Intent Store
- **Key characteristic:** Captures the consumer's raw intent — what they asked for in their own terms
- **Primary use:** Source for Intent Portability — replaying an intent through current policies to produce a new request for a different environment or provider

### 6.2 Requested State

The **Requested State** represents the fully processed, policy-validated, and enriched payload that has been submitted to a Service Provider for execution. It is the output of the Request Payload Processor after all policies have been applied and all data layers have been merged.

- **When it is created:** When the Request Payload Processor completes processing and submits to the API Gateway
- **Where it is stored:** Request Store
- **Key characteristic:** Represents a complete, validated, provider-ready declaration of desired state
- **Primary use:** Record of what was formally requested; input to audit and drift processes

### 6.3 Realized State

The **Realized State** represents what was actually provisioned or executed by a Service Provider, returned to DCM in unified data model format via Denaturalization. It is the ground truth of what was built.

- **When it is created:** When a Service Provider completes execution and returns the realized payload to the API Gateway
- **Where it is stored:** Realized Store
- **Key characteristic:** Must be a complete representation of the provisioned resource in DCM unified format — not a status code, but a full state description
- **Primary use:** Baseline for drift detection; source of truth for audit and reporting; input to cost analysis

### 6.4 Discovered State

The **Discovered State** represents what actually exists in the environment as interrogated by a Service Provider during a discovery operation. It is an independent observation of reality, not derived from any previous DCM state.

- **When it is created:** When a Service Provider completes a discovery cycle and returns the discovered payload to DCM
- **Where it is stored:** Discovered Store
- **Key characteristic:** Produced independently of the Realized State — it is what is actually there, regardless of what was supposed to be there
- **Primary use:** Drift detection (compared against Realized State); brownfield ingestion (pathway to lifecycle ownership of unmanaged resources)

### 6.5 State Relationships and Lifecycle Flow

The four states relate to each other as follows:

```
Consumer Request
      │
      ▼
┌─────────────┐
│ INTENT      │  ◄── What the consumer wants
│ STATE       │
└──────┬──────┘
       │  Policy Engine processes, enriches, validates
       ▼
┌─────────────┐
│ REQUESTED   │  ◄── What was formally submitted to the provider
│ STATE       │
└──────┬──────┘
       │  Service Provider executes
       ▼
┌─────────────┐
│ REALIZED    │  ◄── What was actually built
│ STATE       │
└──────┬──────┘
       │
       │                    ┌─────────────┐
       │  Compare ◄─────────│ DISCOVERED  │  ◄── What actually exists now
       │                    │ STATE       │
       ▼                    └─────────────┘
  Drift Detection
```

**Key operations across states:**
- **Drift Detection:** Discovered State vs. Realized State
- **Request Validation:** Requested State vs. Policy definitions
- **Intent Portability:** Intent State → re-process through current policies → new Requested State
- **Brownfield Ingestion:** Discovered State → enrichment → Realized State (lifecycle ownership)

---

## 7. Data as the Provider Contract Boundary

The data model defines the boundary between DCM and its Service Providers. DCM is explicitly **not concerned with how a provider accomplishes its work** — only with the data that crosses the boundary in both directions.

This means:
- Providers are interchangeable as long as they honor the data contract
- New providers can be added without changing DCM's core data model
- Provider implementation can evolve independently of DCM
- The contract is enforced at the data level — conformant data in, conformant data out

The two mechanisms that enforce this boundary are:
- **Naturalization** — the provider's responsibility to transform DCM unified data into its own tool-specific format for execution
- **Denaturalization** — the provider's responsibility to transform its tool-specific result data back into DCM unified format for return to the control plane

This separation of concerns is what makes DCM technology-agnostic while maintaining a consistent and trustworthy data model across all providers.

---

## 8. Open Questions

The following questions remain unresolved and require decisions before the data model specification can be considered complete:

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Where should data caches live? | Cache architecture, latency, sovereignty | ✅ Resolved — caches at Regional DCM level; Info Provider caches co-located with source; Sovereign DCM uses local static from signed bundles (CACHE-001) |
| 2 | Should cache synchronization be push, pull, or both? | Consistency model | ✅ Resolved — hybrid push-pull; pull on schedule; push for time-sensitive events via Message Bus (CACHE-002) |
| 3 | Which cache is authoritative when caches diverge? | Conflict resolution | ✅ Resolved — GitOps stores always authoritative; caches are projections; divergence triggers rebuild from authoritative store (CACHE-003) |
| 4 | What mechanism maintains consistency across distributed caches? | Data integrity | ✅ Resolved — hash-based heartbeat divergence detection + push invalidation; PT2H staleness alert; signed bundles for Sovereign DCM (CACHE-004) |
| 5 | Should the data model allow embedded target-technology-specific data bundles? | Portability | ✅ Resolved — native_passthrough field sanctioned; always audit-logged; opaque mode blocked in fsi/sovereign (DATA-001) |
| 6 | How are the four states represented physically? | Physical model | ✅ Resolved — Intent/Requested in Git; Realized in Event Stream; Discovered in Discovered Store (STO-005) |
| 7 | What is the performance impact of field-level provenance at scale? What optimization strategies are acceptable? | Scalability, storage cost | ✅ Resolved — three configurable provenance models: full_inline, deduplicated (Model B recommended), tiered; profile-appropriate Policy Groups; see docs 03 and 06 (OPS-001) |
| 8 | Should provenance metadata be stored inline with field data or in a linked provenance document? | Data model structure, query performance | ✅ Resolved — three-level structure: implicit chain ref, inline delta, linked history document; all reconstructable from stored facts; see doc 03 (OPS-002) |

---

## 9. Related Concepts

- **Sovereign Execution Posture** — the target end state the data model enables by providing a verified, auditable chain of custody through the full resource lifecycle
- **CMDB Replacement** — DCM's four-state model is intended to replace the fragmented multi-CMDB problem by becoming the singular resource domain
- **GitOps** — all entities in the data model are stored in Git, enabling version control, change tracking, and standard software lifecycle practices
- **Data Lineage** — the complete chain of custody of any field value from its origin through every modification, recorded within the data object itself
- **Field-Level Provenance** — the structural mechanism by which data lineage is captured, carried, and made available for audit and compliance purposes
- **UUID** — the universal identity mechanism that makes provenance references, dependency mapping, and cross-state correlation unambiguous and durable

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
