# UDLM — Capability Discovery and Unified Provider Model

**Document Status:** ✅ Stable — UDLM substrate contract
**Document Type:** Substrate Reference — Provider Model and Service Discovery
**Related Documents:** [Provider Contract](provider-contract.md) | [Event Catalog](event-catalog.md) | [Schema Sharing](schema-sharing.md)

> **Design principle:** A UDLM-conformant realization MUST be discoverable. External systems should be able to ask the realization "what can you do?" and get a machine-readable answer. Providers should be able to declare what they offer AND what they need. Integration should emerge from capability matching, not manual configuration.

---

## 1. The Problem with Typed Providers (Modeling Contract)

An earlier model defined rigid provider types (service_provider, information_provider, auth_provider, peer, process_provider). Each type had a fixed contract. A provider was exactly one type.

This creates three problems the substrate must address:

**Problem 1 — Artificial constraints.** An IPAM system like InfoBlox both serves data (IP availability queries) AND provisions resources (IP allocation). Under the typed model, it must register twice as two different providers. In reality, it's one system with two capabilities.

**Problem 2 — No discovery.** A FinOps tool wants to integrate with the realization. It needs cost data. Without discovery, someone reads the docs, finds the right events, and manually wires the integration. There's no way for the FinOps tool to ask the realization "what cost-related capabilities do you expose?"

**Problem 3 — One-directional registration.** Providers register with the realization (provider → realization). Nothing discovers the realization. External systems cannot query the realization's capabilities, subscribe to relevant data streams, or negotiate integration automatically.

---

## 2. Unified Provider Model (Substrate Registration Contract)

### 2.1 One Base Provider Contract with Capability Declarations

A provider is an external system that the realization interacts with through a defined contract. All providers share the same base contract:

- Registration (identity, health endpoint, sovereignty, accreditation)
- Health check (liveness, readiness)
- Authentication (zero trust, scoped credentials)
- Audit (provenance emission, sovereignty compliance)

What varies is the **capabilities** the provider declares. Capabilities replace fixed types. The registration shape is normative:

```yaml
provider:
  name: "InfoBlox IPAM"
  version: "3.2.0"

  capabilities:
    realize_resources:
      resource_types:
        - Network.IPAddress
        - Network.Subnet
      operations: [create, update, decommission]
      naturalization_format: infoblox_wapi_v2
      supports_discovery: true
      supports_capacity_query: true

    serve_data:
      data_domains:
        - ip_availability
        - subnet_utilization
      query_interface: rest
      # authority_level + confidence are NOT self-declared — DCM assigns authority_level, the realization
      # COMPUTES confidence; a value supplied here is ignored. Rule defined once in
      # information-providers-advanced.md (the authority/confidence model).

  sovereignty:
    zones: [eu-west-1, eu-west-2]
    federation_eligibility: selective
```

This single registration replaces what previously required two separate registrations (one as information_provider, one as service_provider).

### 2.2 Capability Types (Closed Substrate Vocabulary)

| Capability | What it means | Legacy type label |
|-----------|--------------|----------|
| `realize_resources` | Provider provisions, updates, and decommissions resources | service_provider |
| `serve_data` | Provider responds to queries with authoritative external data | information_provider |
| `authenticate` | Provider authenticates identities and returns tokens/roles/groups | auth_provider |
| `federate` | Provider is another UDLM-conformant peer — mTLS mandatory, dual audit, sovereignty pre-check | peer_realization |
| `execute_workflows` | Provider runs ephemeral workflows without producing persistent resources | process_provider |

A provider MAY declare **multiple capabilities**, and each capability is explicitly **(verb × domain)** — a verb from the vocabulary above scoped to the resource-type **Category** (`naming-conventions §2`) it operates over. The declaration MUST name that domain **uniformly**: `realize_resources.resource_types` and `serve_data.data_domains` are the same idea under different names — the domain a capability acts on — and both are the domain axis. Beyond the domain, the declaration MUST include everything else the realization needs for that capability (operations, auth methods, etc.). The verbs above are the top of the governed **provider-capability taxonomy** (`TaxonomyTerm`; `registry/instances/provider-capability-taxonomy.yaml`), and a (verb × domain) leaf is a **capability category** (§2.4). See ADR-PROV-002.

### 2.3 Type-Label Compatibility

The legacy type names become convenience labels — shorthand for common capability profiles:

| Legacy type | Equivalent capability profile |
|----------|------------------------------|
| service_provider | `capabilities: [realize_resources]` |
| information_provider | `capabilities: [serve_data]` |
| auth_provider | `capabilities: [authenticate]` |
| peer_realization | `capabilities: [federate]` |
| process_provider | `capabilities: [execute_workflows]` |

The `provider_type` field becomes a resolved label derived from the declared capabilities. Substrate consumers MAY rely on the capability set; the type label is informational.

### 2.4 Capability Categories (Policy-Targetable Groupings)

A **capability category** is a **(verb × domain)** term in the provider-capability taxonomy — e.g. `realize_resources/Storage` (*storage-provisioning*), `serve_data/Network` (*network-information*). It is:

- **Derived, not declared.** A provider's categories follow from the capabilities it declares and the domains they operate over — no separate registration.
- **Non-exclusive.** A provider occupies *every* category its capabilities place it in. An InfoBlox IPAM that both allocates IPs and answers availability queries is in **both** `realize_resources/Network` and `serve_data/Network` — one registration, two categories (the double-registration the typed model forced is gone).
- **The policy target.** The Governance Matrix targets a capability category, a capability verb, or the data itself (`data_classification`/`data_role`), replacing the old `provider_type` match axis. Differentiated policy per domain falls out — an encryption-at-rest rule binds `realize_resources/Storage` without touching `realize_resources/Compute`.

Write **"capability category"** in full: bare "category" is the resource-type Category (`naming-conventions §2`) — the domain axis a capability category *composes on* — and it is never a "role" (that is `data_role`, ADR-PROV-001). See ADR-PROV-002.

### 2.5 Capability Admission (Default-Deny)

Declaring a capability is a **claim, not a permission** — **default-deny**: by default no use of a provider is allowed, and a declared capability/category is **unusable until admitted** (ADR-PROV-003; `effective_capabilities` starts empty). Two levels, separated by concern:

- **Platform level (admin).** A **platform admin** admits a capability/category — a *coarse* per-`(provider × capability/category)` disposition `pending | approved | provisional | denied`, recorded in the DCM-assigned registration verdict (`provider-contract.md §2`, `capability_admissions`). Approval stringency is **profile-governed** ("default safe" — derived from the platform profile(s) in use; no profile weakens default-deny). `provisional` = admitted but restricted/shadowed (reuses the federation provisional posture).
- **Granular (policy).** Conditional approval — per tenant / zone / resource-type / context — is **policy**: Governance-Matrix rules (`ALLOW_WITH_CONDITIONS`), not an admin field. Domain granularity is inherent (a category *is* verb × domain, so `realize_resources/Storage` is admitted independently of `realize_resources/Compute`).

What a provider may actually do is the **computed intersecting ceiling**:

> `effective_capabilities = declared ∩ admitted ∩ registry-enabled ∩ Governance-Matrix-permitted`

— never an independent grant list; a provider can exceed neither its declaration nor its admission. This adopts, by reference, the **IAM permission-boundary / SCP** and **OAuth 2.0 scope** intersection semantics (effective = requested ∩ granted; the grantor echoes the granted set back), with **OAuth RAR (RFC 9396)** as the structured `verb × domain` shape (SPEC-DESIGN adopt-by-ref §22–23). Enforcement is the *one* Governance Matrix (§2.4) keyed on the provider + capability category — not a parallel path; the admission record **sources** those rules. Every admission change is an immutable, append-only `CAPABILITY_ADMIT` audit event (actor + reason), reconstructed **LIFO**. See ADR-PROV-003.

---

## 3. Capability Declaration Format and Semantics (Wire Contract)

### 3.1 The Capability Advertisement Endpoint

A UDLM-conformant realization MUST expose a machine-readable endpoint that describes what it can do:

```
GET /api/v1/capabilities
```

The response shape is normative:

```json
{
  "realization_instance": "<instance-handle>",
  "version": "1.0.0",
  "capabilities": {
    "lifecycle_management": {
      "description": "Full lifecycle management of resources",
      "operations": ["create", "update", "scale", "decommission", "rehydrate"],
      "resource_types": ["Compute.VirtualMachine", "Network.IPAddress", "..."],
      "api_endpoint": "/api/v1/requests"
    },
    "policy_evaluation": {
      "description": "Policy-as-code evaluation on every request",
      "policy_types": ["validation", "transformation", "recovery", "orchestration_flow", "governance_matrix"],
      "framework": "opa_rego",
      "api_endpoint": "/api/v1/admin/policies"
    },
    "cost_analysis": {
      "description": "Cost estimation at placement time, cost attribution per tenant",
      "data_streams": {
        "cost_estimated": {
          "description": "Emitted when placement scores include cost",
          "payload_schema": "/api/v1/schemas/events/cost.estimated",
          "subscribe_endpoint": "/api/v1/webhooks"
        },
        "cost_attributed": {
          "description": "Emitted when realized entity cost is recorded",
          "payload_schema": "/api/v1/schemas/events/cost.attributed",
          "subscribe_endpoint": "/api/v1/webhooks"
        }
      }
    },
    "audit_trail": {
      "description": "Tamper-evident Merkle tree audit with configurable granularity",
      "proof_types": ["inclusion", "consistency"],
      "api_endpoint": "/api/v1/audit"
    },
    "placement_decisions": {
      "description": "Provider selection with sovereignty pre-filter and policy scoring",
      "data_streams": {
        "placement_decided": {
          "description": "Full scoring rationale for every placement decision",
          "payload_schema": "/api/v1/schemas/events/placement.decided",
          "subscribe_endpoint": "/api/v1/webhooks"
        }
      }
    },
    "drift_detection": {
      "description": "Discovered vs realized state comparison",
      "data_streams": {
        "drift_detected": {
          "payload_schema": "/api/v1/schemas/events/drift.detected",
          "subscribe_endpoint": "/api/v1/webhooks"
        }
      }
    },
    "entity_lifecycle": {
      "description": "Full entity state change events",
      "data_streams": {
        "entity_created": { "subscribe_endpoint": "/api/v1/webhooks" },
        "entity_realized": { "subscribe_endpoint": "/api/v1/webhooks" },
        "entity_updated": { "subscribe_endpoint": "/api/v1/webhooks" },
        "entity_decommissioned": { "subscribe_endpoint": "/api/v1/webhooks" }
      }
    }
  }
}
```

### 3.2 Capability Query (Substrate Required)

External systems MUST be able to query for specific capabilities:

```
GET /api/v1/capabilities?domain=cost
GET /api/v1/capabilities?domain=audit
GET /api/v1/capabilities?data_stream=true
GET /api/v1/capabilities?operation=create&resource_type=Compute.VirtualMachine
```

The response MUST include only matching capabilities with their API endpoints and subscription mechanisms.

### 3.3 The Integration Flow (Substrate Pattern)

A consuming system integrating with a UDLM-conformant realization:

```
1. Consumer queries:  GET /api/v1/capabilities?domain=cost

2. Realization responds with:
   - cost.estimated event stream (subscribe via webhook)
   - cost.attributed event stream (subscribe via webhook)
   - cost estimation API (GET /api/v1/requests/{uuid}/cost-estimate)
   - payload schemas for each

3. Consumer subscribes: POST /api/v1/webhooks
   {
     "event_types": ["cost.estimated", "cost.attributed", "entity.realized"],
     "callback_url": "https://consumer.example.com/events",
     "auth": { "type": "hmac_sha256", "secret_ref": "..." }
   }

4. Data flows automatically — no manual wiring
```

---

## 4. Provider Capability Advertisement (Wire Contract)

When a provider registers, it MAY declare what it offers AND what it needs from the realization:

```yaml
provider:
  name: "Acme FinOps Platform"

  capabilities:
    serve_data:
      data_domains:
        - cost_optimization_recommendations
        - budget_forecasts
      query_interface: rest

  needs_from_realization:
    - domain: cost
      description: "Cost estimation and attribution data"
    - domain: entity_lifecycle
      description: "Entity create/update/decommission events"
    - domain: placement_decisions
      description: "Placement scoring rationale for cost analysis"
```

### 4.1 Matched-Capabilities Response (Wire Contract)

When a provider registers with `needs_from_realization`, the realization MUST match the declared needs against its capability advertisement and offer subscription endpoints in the registration response:

```json
{
  "matched_capabilities": {
    "cost": {
      "streams": ["cost.estimated", "cost.attributed"],
      "subscribe_endpoint": "/api/v1/webhooks",
      "auto_subscribed": false,
      "action_required": "POST to subscribe_endpoint to activate"
    },
    "entity_lifecycle": {
      "streams": ["entity.created", "entity.realized", "entity.updated", "entity.decommissioned"],
      "subscribe_endpoint": "/api/v1/webhooks",
      "auto_subscribed": false
    },
    "placement_decisions": {
      "streams": ["placement.decided"],
      "subscribe_endpoint": "/api/v1/webhooks",
      "auto_subscribed": false
    }
  },
  "unmatched_needs": []
}
```

Substrate invariants:
- The provider then activates the subscriptions it wants. The realization MUST NEVER auto-subscribe — the provider explicitly opts in.
- The realization MUST advertise exactly what's available and how to obtain it.

### 4.2 Bidirectional Discovery Pattern

The pattern works in both directions:

```
Provider → Realization: "Here's what I can do" (capabilities)
Provider → Realization: "Here's what I need from you" (needs_from_realization)
Realization → Provider: "Here's what I have that matches your needs" (matched_capabilities)
Realization → Provider: "Here's what I need from you" (dispatch payloads via the provider contract)
```

---

## 5. Capability Discovery — Substrate Invariants

The substrate requires the following invariants on capability discovery interactions:

- **Catalog separation:** The capability advertisement endpoint exposes resource types the realization manages, but NOT the tenant-scoped, RBAC-filtered service catalog itself.
- **Policy enforcement:** Capability discovery MUST NOT bypass policy. A provider that discovers a data stream and subscribes to it still has its webhook authenticated, its data filtered by tenant scope, and its subscription audited.
- **Audit:** Every capability query, subscription establishment, and data stream delivery MUST be audited. The audit trail shows: who queried capabilities, what they subscribed to, and what data was delivered.
- **Federation use:** A peer realization (`federate` capability) MAY use capability discovery to understand what a remote instance can do before establishing a federation tunnel. This replaces static federation scope declarations with dynamic capability negotiation.

---

## 6. UDLM System Policies

| ID | Policy |
|----|--------|
| `DISC-001` | Capability advertisement is read-only and requires authentication. No anonymous capability queries. |
| `DISC-002` | Webhook subscriptions MUST be tenant-scoped. A provider's subscription only receives events for entities in its authorized scope. |
| `DISC-003` | Capability query MUST be rate-limited. Prevents enumeration attacks. |
| `DISC-004` | `needs_from_realization` matching is advisory, not automatic. The realization suggests matches; the provider activates subscriptions explicitly. |
| `DISC-005` | Capability schema versions follow the substrate's API versioning strategy. Capability response format is versioned and backward-compatible. |

---

*UDLM substrate document. Realization-specific provider registry implementation with capabilities, capability matching algorithms for dispatch decisions, type-based backward compatibility shims, and capability validation / conflict resolution mechanics live in the consuming realization's documentation.*
