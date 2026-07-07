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

**Transport.** The contract is **HTTP/REST + JSON** (AEP-conformant). REST is the floor every provider can meet — it keeps the barrier to implementing a provider in any language low and matches the rest of the API surface. The contract is deliberately transport-shaped (operations + typed request/response schemas), so a **gRPC binding can be added post-1.0** if provider demand warrants it; it is not in v1. gRPC is a later projection of the same operations, not a parallel contract.

**The boundary.** Throughout this document "the boundary" is the **trust boundary between DCM and an external provider** — the point where an assembled payload leaves DCM's control (outbound) or a provider result enters it (inbound). The Governance Matrix (§4) is evaluated at *every* crossing of this boundary because that is precisely where data leaves DCM's governance.

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

  # Data ROLES this provider accepts across the dispatch boundary (ADR-PROV-001;
  # contracts/data-roles.md). Default [execution] — only execution-role data is naturalized
  # to the provider. A provider MAY opt into non-execution roles (e.g. assembly context).
  # The set actually delivered is the INTERSECTION of this declaration and what the
  # Governance Matrix permits at the DCM→Provider boundary — sovereignty policy can strip a
  # role the provider requested; it can never widen beyond this declaration.
  accepts_roles: [execution]             # e.g. [execution, assembly]

  # Endpoints (which endpoints are required varies by type — see extensions)
  health_endpoint: "https://<provider>/health"

  # Zero trust identity
  certificate:
    pem: <provider-certificate>          # provider's mTLS leaf cert (PEM)
    ca_chain: <ca-chain>                 # issuing chain DCM pins for this provider
    rotation_interval: P90D              # max age before DCM expects a rotated cert;
                                         # a cert older than this is flagged at health check

  # Trust posture — how much DCM trusts this provider's self-declarations (DCM ADR-022).
  # Set by attestation verification at registration, not by the provider's own claim.
  trust_posture: verified | vouched | provisional   # verified = attestation independently
                                         # checked; vouched = attested by a trusted third
                                         # party; provisional = self-asserted, capability-gated

  # Declared network reachability — so onboarding a provider is a DECLARATION, not a
  # manual firewall edit. DCM provisions the egress/ingress policy from this block; an
  # operator never hand-edits per-provider firewall rules (resolves the per-provider
  # firewall concern).
  network_reachability:
    egress:                              # destinations DCM must be allowed to reach
      - host: "<provider-host>"
        port: 443
        protocol: https
    ingress:                             # callbacks the provider makes back to DCM
      - endpoint: lifecycle              # maps to the DCM lifecycle endpoint (§6)
      - endpoint: telemetry              # telemetry delivery (§7)
    provisioned_by: platform             # platform provisions policy from this declaration
```

Field notes: `rotation_interval` is the maximum certificate age DCM tolerates before flagging; `trust_posture` is assigned by DCM's attestation verification (not accepted from the provider); `network_reachability` is consumed by the platform to provision connectivity so no per-provider manual firewall change is required.

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

**Provider operations (closed vocabulary).** A provider exposes more than registration; credential scope (`scope.operations`, see [Credentials](../governance/credentials.md) §3) is checked against whichever operation is executing:

| Operation | Direction | Endpoint(s) |
|-----------|-----------|-------------|
| `dispatch` | DCM → provider | `{dispatch_endpoint}` — realize/execute an assembled payload |
| `discover` | DCM → provider | `{discover_endpoint}` — enumerate or query existing state |
| `query` | DCM → provider | `{query_endpoint}`, `{capabilities_endpoint}` — read provider data/options |
| `introspect` | DCM → provider | `{dependency_introspection_endpoint}` — observed dependency edges |
| `lifecycle` | provider → DCM | `{dcm_lifecycle_endpoint}` — report a state change (§6) |
| `telemetry` | provider → DCM | telemetry delivery (§7) |

A credential issued for one operation cannot be used for another; a provider receiving an interaction whose scoped operation does not match the called endpoint MUST reject it (`403`).

---

## 5. Base Contract — Zero Trust

All provider interactions operate under the active zero trust posture. Minimum requirement for all providers at all profiles:

- Mutual TLS authentication on every call (both sides present certificates)
- Scoped, short-lived interaction credentials (not long-lived API keys)
- Every call authenticated; no implicit trust from network position or prior calls
- Certificate rotation on declared interval

**Why short-lived, scoped credentials** (not long-lived API keys): zero-standing-trust. Each dispatch presents a freshly issued credential scoped to that one operation and resource, so a leaked credential expires quickly and every use is attributable and audited. A long-lived shared key is standing liability — broad, slow to rotate, hard to attribute. Issuance and lifecycle of these credentials are specified in [Credentials](../governance/credentials.md) §4.2.

Higher profiles add: certificate pinning, per-message signing, hardware attestation.

---

## 6. Base Contract — Provider Lifecycle Events

Providers must report changes to the **lifecycle state of the realized resources they host** — drift from requested state, degradation, capacity events, or an unsanctioned out-of-band change — via lifecycle events. (This is why the base registration payload carries no `state` field: realized state is reported through this channel after realization, not declared at registration.) This is a base contract obligation — not optional:

```json
POST {dcm_lifecycle_endpoint}
{
  "event_uuid": "<uuid>",
  "event_type": "<event_type>",       // resource.drift_detected | resource.degraded |
                                      // resource.capacity_changed | resource.unsanctioned_change |
                                      // resource.decommissioned | provider.capability_changed
  "provider_uuid": "<uuid>",
  "affected_entity_uuids": ["<uuid>"],
  "event_timestamp": "<ISO 8601>",
  "severity": "INFO | WARNING | CRITICAL"
}
```

`event_type` draws from the substrate event vocabulary; the full schema for each type is in the [event catalog](event-catalog.md). DCM reconciles the reported state against the entity's requested state and drives drift/degradation handling from there.

---


## 7. Base Contract — Observability, Logs & Telemetry

Every provider contract includes observability as a base obligation — metrics,
logs, and telemetry for the resources a provider hosts are part of the
contract, not an optional extension.

**Division of responsibility:** DCM does **not need to be the arbiter of the
telemetry data itself** — it is not required to store, own, or adjudicate
metric/log content. DCM's obligation is to **manage the collection**: for
every appropriate resource it must be able to discover what telemetry a
provider can emit, configure where that telemetry is delivered, verify
collection is active, and record those facts in the audit trail. By default
the data flows to the deployment's observability platform; DCM governs that
the flow exists.

**DCM MAY be the arbiter.** Where no external observability platform exists —
or a packaged ("canned") solution is desired — DCM CAN serve as the
authoritative telemetry/monitoring platform itself, fulfilling the collection
obligation *and* the storage/query/alerting role through a deployable
observability component (**dcm-observability**). Both postures satisfy this
contract; the choice is a deployment decision, not an architectural fork.
The reference implementation of this component is being developed with an
observability stack as its test bed.

**Registration declaration (the telemetry descriptor):** providers declare
their telemetry surface at registration alongside other capabilities. **DCM
discovers what telemetry a provider can emit by reading this descriptor — it
does not probe or guess.** The descriptor is the single source of truth for
which signals exist, in what format, and where DCM configures delivery:

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
  per_resource_scoping: true                 # signals carry entity UUID/handle labels so
                                             # collection is attributable per resource
  per_tenant_scoping: true                   # signals carry tenant scope (X-DCM-Tenant /
                                             # tenant_uuid label) so collection + the
                                             # dashboards/alerts built on it isolate per tenant
```

**Obligations:**
- Telemetry MUST be attributable to the entities it describes (entity UUID /
  handle labels) so collection can be scoped per resource, per tenant, and
  per policy. Because entities carry their group memberships and ownership in
  their own definitions ([Universal Group Model](../observability/universal-groups.md)),
  this attribution is sufficient to scope dashboards, reporting, alerting —
  and the *management* of those artifacts — to the appropriate business /
  operational groups (DCMGroup) with **no side-channel scoping configuration**
  (capability OBS-008).
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


## 8. Capability Extensions — Provider Kinds and Capabilities

Each provider shares the base contract (Section 1–7) and adds a typed capability extension declaring what it can do. Two things are distinguished here:

- **Provider kinds** — distinguished by *interaction shape* (what data flows in which direction, what operations exist): **Service/Resource Provider**, **Information Provider**, **Process Provider**, and **Peer DCM**. A Composite Service is *not* a kind — it is an ordinary Service Provider registering a multi-resource definition (§8.3).
- **Provider capabilities** — *yields* a provider declares via resource types, independent of kind: **credential issuance** (`Credential.*`), **authentication** (the auth capability), **notification delivery** (`Notification.*`), **ITSM** (`ITSM.*`), and **telemetry** (§7). A capability is something a provider *yields*, not a separate kind of provider — any provider that declares the resource types and capability block exercises it. This is the reconciliation point with the Service/Resource taxonomy: name providers by what they *yield*, and treat credentials/auth/notifications as declared capabilities, not parallel provider kinds.

### 8.1 Service / Resource Provider

**What it does:** Realizes infrastructure resources. Receives assembled payloads, provisions the resource, returns realized state. The same kind also **yields** other capabilities by declaring their resource types: credential issuance (`Credential.*` — see [Credentials](../governance/credentials.md)), notification delivery (`Notification.*`), and ITSM integration (`ITSM.*`). These are **capabilities declared on a provider, not separate provider kinds** — a provider that declares `Credential.*` *is* a Credential Provider for those types.

**Additional endpoints:**
```
POST {dispatch_endpoint}                      # receive and execute dispatch payload
POST {cancel_endpoint}                        # receive cancellation request (if supported)
GET  {discover_endpoint}                      # parameterless full enumeration of discovered state
POST {discover_endpoint}                      # filtered/scoped discovery — takes a query body
                                              # (filters, scope, resource-type selectors)
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

### 8.2 Information Provider

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

### 8.3 Composite Service Definitions

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

### 8.4 Auth Capability

**Authentication is a capability, not a provider kind** (parallel to credential issuance — see [Credentials](../governance/credentials.md) §1). A provider that authenticates actors declares the **auth capability**; DCM consumes it the same way it consumes any other yield. Multiple providers may declare it — tenant routing determines which authenticates a given actor. (DCM is itself a consumer of this capability for its own user auth; it does not have to *be* the authenticator — it brokers/consumes, see DCM `ADR-022`.)

**Additional endpoints (a provider declaring the auth capability exposes):**
```
POST {authenticate_endpoint}     # receive credentials; return auth token + claims
POST {authorize_endpoint}        # receive token + operation; return allow/deny
GET  {identity_endpoint}         # return actor claims for a token
```

**Capability declaration:**
```yaml
auth_capability:                 # declared on any provider; not a provider_type
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

**Data direction:** Consumer sends credentials → the auth-capable provider validates → returns token + claims → DCM extracts actor identity.

> **Credential capability.** Credential issuance is the sibling capability, declared via `Credential.*` + a `credential_capability` block (assurance + attestation level the realization selects against). Its full contract — issuance, rotation, revocation, declare-and-select, the broker model — lives in [Credentials](../governance/credentials.md). Like auth, it is a declared capability, not a provider kind; DCM brokers it and never holds the value (CPX-001).

---

### 8.5 Peer DCM (Federation)

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

### 8.6 Process Provider

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

The registry lists the **provider kinds** (interaction shapes: `service_provider`/resource, `information_provider`, `process_provider`, `peer_dcm`). It does **not** list capabilities — auth, credential issuance, notification, ITSM, and telemetry are **yields declared on a provider** via its resource types and capability blocks, verified at registration (PRV-003), not separate registry entries. There is no `auth_provider` or `credential_provider` kind.

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
| `PRV-007` | Observability is part of the base contract: providers declare their telemetry surface (metrics, logs, events) at registration using standard exposition formats. DCM MUST be able to manage collection — discover, configure delivery, verify activity, and audit-record — for all appropriate resources; it is not required to arbiter the telemetry data itself, but MAY serve as the authoritative telemetry/monitoring platform (dcm-observability) where none exists or a canned solution is desired. Integration mechanism TBD (leading candidate: UDLM-modeled export). |
| `PRV-008` | Only `role: execution` data crosses the dispatch boundary by default (ADR-PROV-001; [data-roles.md](data-roles.md)). The payload a provider receives is the INTERSECTION of its declared `accepts_roles` and what the Governance Matrix permits at the DCM→Provider boundary. Sovereignty/profile policy may strip a role a provider requested; it can never widen beyond `accepts_roles`. `role: assembly` (and other control-plane roles) MUST NOT be naturalized to a provider that has not opted in, and MUST NOT be copied into `states.realized`. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
