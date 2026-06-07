# DCM — Unified Provider Contract


**Document Status:** ✅ Complete
**Document Type:** Architecture Foundation
**Related Documents:** [Foundational Abstractions](../foundations/foundations.md) | [Policy Contract](policy-contract.md) | [Governance Matrix](../governance/governance-matrix.md) | [Accreditation](../governance/accreditation-and-authorization-matrix.md)

---

> > **Design Priority:** Provider types implement all four design priorities simultaneously. Security properties (mTLS, scoped credentials, sovereignty declarations, accreditation) are present in all provider registrations. The capability extension model (Priority 3) enables new provider types without changing the base contract. See [Design Priorities](../design-principles/design-priorities.md).

## 1. The Unified Provider Contract

Every Provider in DCM — regardless of type — implements a single base contract. What varies between provider types is the **capability extension**: the specific operations exposed, the data that flows in each direction, and the typed schemas for that exchange.

```
┌─────────────────────────────────────────────────────────┐
│                BASE PROVIDER CONTRACT                    │
│                                                          │
│  Registration · Health · Sovereignty · Accreditation    │
│  Governance Matrix · Zero Trust · Lifecycle              │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │           CAPABILITY EXTENSION                   │   │
│  │                                                  │   │
│  │  What operations this provider type exposes.     │   │
│  │  What data flows in which direction.             │   │
│  │  What schemas govern the exchange.               │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

**Adding a new provider type** = implement the base contract + define a capability extension. No changes to the core required.

---

## 2. Base Contract — Registration

All providers register through the same pipeline (registration specification is implementation-specific; see DCM repo for the complete flow).

```yaml
provider_base_registration:
  # Standard artifact metadata
  artifact_metadata:
    uuid: <uuid>
    handle: "<tier>/<category>/<name>"    # e.g., "org/compute/eu-west-prod-1"
    version: "1.0.0"
    status: submitted                      # submitted → validating → active
    owned_by: { display_name: "<team>" }

  provider_type_id: <type>               # from Provider Type Registry
  display_name: "<human-readable name>"
  description: "<what this provider does>"

  # All providers declare these
  sovereignty_declaration:
    operating_jurisdictions: [<country_codes>]
    data_residency_zones: [<zone_ids>]
    sub_processors: []                   # third parties with data access

  accreditations:
    - accreditation_uuid: <uuid>         # reference to registered accreditation
      framework: <framework>
      status: active

  # Endpoints (which endpoints are required varies by type — see extensions)
  health_endpoint: "https://<provider>/health"

  # Zero trust identity
  certificate:
    pem: <provider-certificate>
    ca_chain: <ca-chain>
    rotation_interval: P90D
```

**Registration lifecycle states:**
```
SUBMITTED → VALIDATING → PENDING_APPROVAL → ACTIVE
                       ↘ REJECTED
ACTIVE → SUSPENDED | DEREGISTERING → DEREGISTERED | FORCED_DEREGISTERED
```

---

## 3. Base Contract — Health Check

Every provider implements a health endpoint. DCM calls it on the declared interval.

```
GET {health_endpoint}

Response 200:
{
  "status": "healthy | degraded | unhealthy",
  "version": "<provider version>",
  "capabilities_available": ["<list of currently available capabilities>"],
  "details": { }    # provider-specific; DCM treats as opaque
}
```

**DCM response to health states:**
- `healthy` → normal operations; next poll scheduled
- `degraded` → reduced routing preference; platform admin notified (medium urgency)
- `unhealthy` / no response → after `failure_threshold`: status → DEGRADED; new requests not routed
- After 2× `failure_threshold`: status → UNAVAILABLE; drift detection triggered on all hosted entities

---

## 4. Base Contract — Governance Matrix Enforcement

Every interaction with every provider is evaluated against the Governance Matrix before data crosses the boundary. This is not optional and not configurable per provider — it is a base contract requirement.

```
Outbound interaction (DCM → Provider):
  1. Classify all fields in the payload by data_classification
  2. Resolve provider's active accreditations
  3. Evaluate Governance Matrix: permitted | strip_field | deny | redact
  4. Apply field permissions
  5. Audit record written (regardless of outcome)
  6. If DENY: interaction blocked; entity enters PENDING_REVIEW if appropriate

Inbound interaction (Provider → DCM):
  1. Authenticate provider identity (mTLS)
  2. Verify credential scope matches the operation
  3. Accept payload; apply data_classification tags
  4. Store in appropriate store per data_classification
```

---

## 5. Base Contract — Zero Trust

All provider interactions operate under the active zero trust posture. Minimum requirement for all providers at all profiles:

- Mutual TLS authentication on every call (both sides present certificates)
- Scoped, short-lived interaction credentials (not long-lived API keys)
- Every call authenticated; no implicit trust from network position or prior calls
- Certificate rotation on declared interval

Higher profiles add: certificate pinning, per-message signing, hardware attestation.

---

## 6. Base Contract — Provider Lifecycle Events

Providers must report state changes via lifecycle events. This is a base contract obligation — not optional:

```json
POST {dcm_lifecycle_endpoint}
{
  "event_uuid": "<uuid>",
  "event_type": "<event_type>",
  "provider_uuid": "<uuid>",
  "affected_entity_uuids": ["<uuid>"],
  "event_timestamp": "<ISO 8601>",
  "severity": "INFO | WARNING | CRITICAL"
}
```

---


## 7. Base Contract — Observability, Logs & Telemetry

Every provider contract includes observability as a base obligation — metrics,
logs, and telemetry for the resources a provider hosts are part of the
contract, not an optional extension.

**Division of responsibility:** DCM is **not the arbiter of the telemetry data
itself** — it does not need to store, own, or adjudicate metric/log content.
DCM's obligation is to **manage the collection**: for every appropriate
resource it must be able to discover what telemetry a provider can emit,
configure where that telemetry is delivered, verify collection is active, and
record those facts in the audit trail. The data flows to the deployment's
observability platform; DCM governs that the flow exists.

**Registration declaration:** providers declare their telemetry surface at
registration alongside other capabilities:

```yaml
telemetry:
  metrics:
    supported: true
    exposition: [prometheus, openmetrics]   # standard formats only
    endpoint: <metrics_endpoint>
  logs:
    supported: true
    transport: [syslog, otlp, http_push]
    endpoint: <log_sink_config_endpoint>     # where DCM configures delivery
  events:
    supported: true                          # lifecycle events (Section 6) are
                                             # the minimum; richer streams declared here
  per_resource_scoping: true                 # telemetry attributable to entity UUIDs
```

**Obligations:**
- Telemetry MUST be attributable to the entities it describes (entity UUID /
  handle labels) so collection can be scoped per resource, per tenant, and
  per policy.
- Collection configuration changes (enable, disable, redirect) are mutations —
  they are policy-evaluated and audit-recorded like any other change.
- Providers that cannot emit telemetry for a resource class declare that at
  registration; the substrate records `telemetry_unavailable` for affected
  entities (mirror of the dependency-introspection pattern).

**Integration mechanism:** TBD — the leading candidate is UDLM-modeled export
(telemetry entities + the [event catalog](event-catalog.md) with discoverable
schemas per [schema-sharing](schema-sharing.md)), making the telemetry surface
consumable by any external tool with no per-tool adapters. See the validation
use case `dav/use-cases/observability/udlm-universal-telemetry-export.yaml`
(DCM repo) and the Universal Audit Model for the audit-record component of
this surface.

---


## 8. Capability Extensions — Provider Types

DCM defines five provider types. Each shares the base contract (Section 1–7) and adds a typed capability extension declaring what the provider can do.

### 7.1 Service Provider

**What it does:** Realizes infrastructure resources. Receives assembled payloads, provisions the resource, returns realized state. Service providers also cover credential management (Credential.* resource types via Vault or similar), notification delivery (Notification.* resource types), and ITSM integration (ITSM.* resource types) — these are service providers with specific resource type declarations, not separate provider types.

**Additional endpoints:**
```
POST {dispatch_endpoint}                      # receive and execute dispatch payload
POST {cancel_endpoint}                        # receive cancellation request (if supported)
POST {discover_endpoint}                      # receive discovery request; return discovered state
POST {dependency_introspection_endpoint}      # receive entity_uuid; return observed dependency
                                              # edges for that entity (see entities/
                                              # service-dependencies.md §3a)
GET  {capabilities_endpoint}                  # return available options (networks, images, storage classes)
```

**Capability declaration extension:**
```yaml
service_provider_capabilities:
  resource_types:
    - fqn: Compute.VirtualMachine
      spec_version: "2.1.0"
      catalog_item_uuid: <uuid>
  cancellation:
    supports_cancellation: true
    cancellation_supported_during: [DISPATCHED, PROVISIONING]
  discovery:
    supports_discovery: true
    discovery_method: api_query | passive_event | hybrid
  dependency_introspection:
    supported: true | false
    # If supported: provider returns the observed dependency edges for any
    # entity it hosts when the substrate calls {dependency_introspection_endpoint}.
    # Observation is post-realization and observational only — it is NOT
    # consulted for orchestration. See entities/service-dependencies.md §3a
    # and policies OBS-001..OBS-005 for the contract.
    methods:
      - api_query             # actively query the underlying platform
      - passive_event         # surface dependencies that emit lifecycle events
      - inferred_from_config  # derived from provider-held configuration
    response_sla: PT30S       # MUST be ≤ discovery endpoint SLA (OBS-004)
    max_edges_per_response: 500
  naturalization:
    target_format: openstack_nova | vmware_vsphere | custom
  cost_metadata:
    opex_per_unit_per_hour: 0.28
    currency: USD
```

**Data direction:** DCM sends assembled Requested State → Provider naturalizes → executes → denaturalizes → returns Realized State. Separately, on demand, DCM sends `{entity_uuid}` to `{dependency_introspection_endpoint}` → Provider returns observed dependency edges → DCM records them in the Entity Relationship Graph under `edge_nature: observed`.

---

### 7.2 Information Provider

**What it does:** Serves authoritative external data to enrich DCM's understanding of resources and business context.

**Additional endpoints:**
```
POST {query_endpoint}            # receive query; return data in DCM unified format
POST {write_back_endpoint}       # optional; receive DCM updates to push to source system
```

**Capability declaration extension:**
```yaml
information_provider_capabilities:
  data_domains:
    - domain: business_data
      data_types: [business_unit, cost_center, product_owner]
      authority_level: primary | secondary | supplementary
  query_capacity:
    max_queries_per_second: 100
  confidence_model:
    data_freshness_sla: PT1H
  write_back_supported: false
```

**Data direction:** DCM sends lookup query → Provider returns data in DCM format → DCM enriches entity fields.

---

### 7.3 Composite Service Definitions

> DCM treats composite payloads (multiple constituent resource types delivered as one catalog item) as Composite Services registered by ordinary Service Providers. There is no separate provider type for composition — a Service Provider that handles a multi-resource catalog item registers a Composite Service definition and fulfills the constituents it owns (those flagged `provided_by: self`). DCM handles expansion, placement of `external` constituents, dependency resolution, binding field injection, sequencing, and compensation. See doc 05 (Resource Type Hierarchy) and doc 30 (Composite Service Composition Model) for the full model.

**What it does:** Delivers a composite payload — multiple constituent resource types with declared dependencies and delivery requirements — as a single catalog item. The registering Service Provider declares a Composite Service definition (constituent resource types, dependencies, and delivery requirements) so DCM can place, sequence, and govern the constituents. For its own resource types (`provided_by: self`), the registering provider executes as a standard Service Provider — one constituent payload in, one realized state out. All orchestration, placement, sequencing, failure handling, and compensation are performed by DCM using the declared dependency graph.

> **Full specification:** See [Composite Service Composition Model](../entities/composite-service-model.md) for the complete contract, four-state model, failure propagation, compensation, and system policies (CMP-001–CMP-008).

**Capability declaration extension (summary — full schema in doc 30):**
```yaml
composite_service_capabilities:
  constituent_provider_types: [service_provider, information_provider]
  composition_model:
    execution: dependency_ordered
    max_concurrent_realizations: 10
    max_constituent_count: 20
    max_nesting_depth: 3
  partial_delivery_supported: true
  compensation_supported: true
  resource_types_composed:
    - fqn: ApplicationStack.WebApp
      version: "2.0.0"
      constituents:
        - resource_type: Compute.VirtualMachine
          required_for_delivery: required
        - resource_type: Network.IPAddress
          required_for_delivery: required
        - resource_type: DNS.Record
          required_for_delivery: partial
      composition_visibility: selective
```

**Composite status determination:**
- `OPERATIONAL` — all required constituents succeeded
- `DEGRADED` — required constituents succeeded; one or more partial constituents failed
- `FAILED` — one or more required constituents failed → compensation executes

**Data direction:** DCM expands the catalog request, applies policies to the assembled composite payload, dispatches each constituent's payload to its resolved provider in dependency order (`self` constituents go to the registering provider, `external` constituents go to placed providers), and aggregates the returned realized states into the Composite Entity's realized state.

---

### 7.4 Auth Provider

**What it does:** Authenticates actor identities and resolves their roles and group memberships. Multiple auth providers can be registered — tenant routing determines which provider authenticates a given actor.

**Additional endpoints:**
```
POST {authenticate_endpoint}     # receive credentials; return auth token + claims
POST {authorize_endpoint}        # receive token + operation; return allow/deny
GET  {identity_endpoint}         # return actor claims for a token
```

**Capability declaration extension:**
```yaml
auth_provider_capabilities:
  authentication_modes: [oidc, ldap, saml, mtls, hardware_token]
  mfa_methods: [totp, push_notification, hardware_token]
  rbac_model: flat | hierarchical | abac
  step_up_supported: true
  token_lifetime:
    default: PT1H
    max: PT8H
  federation_capable: true
  supports_session_revocation: true
```

**Data direction:** Consumer sends credentials → Auth Provider validates → returns token + claims → DCM extracts actor identity.

---

### 7.5 Peer DCM (Federation)

**What it does:** Another DCM instance participating in federation. Treated as a typed Provider with a federation tunnel as the communication channel.

**Capability declaration extension:**
```yaml
peer_dcm_capabilities:
  dcm_version: "1.0.0"
  tunnel_type: peer | parent_child | hub_spoke
  deployment_accreditations: [<accreditation_uuids>]
  inbound_authorization:
    - operation: catalog_query
      resource_types: [Compute.VirtualMachine]
  outbound_authorization:
    - operation: placement_query
      resource_types: [Compute.VirtualMachine]
  data_boundary:
    max_classification: restricted
  trust_posture: verified | vouched | provisional
```

**Data direction:** Bidirectional within declared authorization scope. Federation tunnel with mTLS, certificate pinning, per-message signing.

---

### 7.6 Process Provider

**What it does:** Executes ephemeral workflows to completion. Unlike service providers that manage persistent resource lifecycle (create → operate → decommission), process providers execute a job and report a result. No persistent resource is created — the entity type is `process_resource` which reaches a terminal state on completion.

**Use cases:** Software installation, backup execution, compliance scan, data migration, certificate rotation, patch application, report generation.

**Additional endpoints:**
```
POST {execute_endpoint}          # receive job payload; begin execution
GET  {status_endpoint}/{job_id}  # poll execution status
POST {cancel_endpoint}/{job_id}  # cancel running execution (if supported)
```

**Capability declaration extension:**
```yaml
process_provider_capabilities:
  supported_process_types:
    - "Process.SoftwareInstall"
    - "Process.BackupExecution"
    - "Process.ComplianceScan"
    - "Process.DataMigration"
  max_concurrent_executions: 10
  timeout_default: PT30M
  idempotent: true
  cancellation_supported: true
  automation_platform: aap | tekton | argo_workflows | direct_api
```

**Data direction:** DCM sends job payload → Process Provider executes → reports progress via status polling or callback → returns result payload on completion. Result payload follows standard denaturalization — provider-native output translated to DCM unified format.

**Lifecycle:** `PENDING → EXECUTING → COMPLETED | FAILED | CANCELLED`. No ongoing lifecycle management — process resources reach a terminal state and stay there.

---

## 9. Provider Type Registry

The Provider Type Registry is the authoritative list of provider types that a DCM deployment accepts registrations for. It follows the three-tier registry model (Core / Verified Community / Organization).

```yaml
provider_type_registry_entry:
  provider_type_id: service_provider
  tier: core
  default_approval_method: reviewed   # auto | reviewed | verified | authorized
  enabled_in_profiles: [minimal, dev, standard, prod, fsi, sovereign]
  capability_extension_schema_ref: <uuid>
```

Profile-governed approval methods override provider type defaults. The complete approval method resolution model is implementation-specific (see DCM repo).

---

## 10. Related Policies

| Policy | Rule |
|--------|------|
| `PRV-001` | All providers implement the base contract. No provider is exempt from registration, health check, sovereignty declaration, governance matrix enforcement, or zero trust authentication. |
| `PRV-002` | Governance Matrix evaluation occurs before every provider interaction. It is not configurable per provider and cannot be bypassed. |
| `PRV-003` | Provider capability declarations are verified at registration. Capabilities not declared at registration cannot be invoked after activation. |
| `PRV-004` | Peer DCM instances are treated as typed providers. Federation is the Provider abstraction applied across DCM instances — not a separate abstraction. |
| `PRV-005` | Adding a new provider type requires implementing the base contract and defining a capability extension. No changes to DCM core are required. |
| `PRV-006` | Service Providers that declare `dependency_introspection.supported: true` MUST respond to the dependency-introspection endpoint for any entity they host. Returned edges are recorded as observed (not declared) per [Service Dependencies](../entities/service-dependencies.md) §3a and policies OBS-001..OBS-005. Providers that do not declare the capability are exempt; the substrate records `dependency_introspection_unavailable` for affected entities. |
| `PRV-007` | Observability is part of the base contract: providers declare their telemetry surface (metrics, logs, events) at registration using standard exposition formats. DCM is not the arbiter of telemetry data, but it MUST be able to manage collection — discover, configure delivery, verify activity, and audit-record — for all appropriate resources. Integration mechanism TBD (leading candidate: UDLM-modeled export). |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
