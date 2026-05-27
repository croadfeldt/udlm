# DCM Data Model — Capability Discovery and Unified Provider Model

**Document Status:** ✅ Active  
**Document Type:** Architecture Reference — Provider Model and Service Discovery  
**Related Documents:** [Provider Contract](A-provider-contract.md) | [Control Plane Components](25-control-plane-components.md) | [Event Catalog](33-event-catalog.md) | [Webhooks and Messaging](18-webhooks-messaging.md) | [API Versioning](34-api-versioning-strategy.md)

> **Design principle:** DCM must be discoverable. External systems should be able to ask DCM "what can you do?" and get a machine-readable answer. Providers should be able to declare what they offer AND what they need. Integration should emerge from capability matching, not manual configuration.

---

## 1. The Problem with Typed Providers

DCM's original provider model defined rigid types (service_provider, information_provider, auth_provider, peer_dcm, process_provider). Each type had a fixed contract. A provider was exactly one type.

This creates three problems:

**Problem 1 — Artificial constraints.** An IPAM system like InfoBlox both serves data (IP availability queries) AND provisions resources (IP allocation). Under the typed model, it must register twice as two different providers. In reality, it's one system with two capabilities.

**Problem 2 — No discovery.** A FinOps tool wants to integrate with DCM. It needs cost data. Today, someone reads the docs, finds the right events, and manually wires the integration. There's no way for the FinOps tool to ask DCM "what cost-related capabilities do you expose?"

**Problem 3 — One-directional registration.** Providers register with DCM (provider → DCM). Nothing discovers DCM. External systems cannot query DCM's capabilities, subscribe to relevant data streams, or negotiate integration automatically.

## 2. Unified Provider Model

### 2.1 One Provider Type with Capability Declarations

A provider is an external system that DCM interacts with through a defined contract. All providers share the same base contract:

- Registration (identity, health endpoint, sovereignty, accreditation)
- Health check (liveness, readiness)
- Authentication (zero trust, scoped credentials)
- Audit (provenance emission, sovereignty compliance)

What varies is the **capabilities** the provider declares. Capabilities replace types:

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
      authority_level: authoritative
      query_interface: rest
      confidence_model: { default: 95, staleness_decay: true }
      
  sovereignty:
    zones: [eu-west-1, eu-west-2]
    federation_eligibility: selective
```

This single registration replaces what previously required two separate registrations (one as information_provider, one as service_provider).

### 2.2 Capability Types

| Capability | What it means | Replaces |
|-----------|--------------|----------|
| `realize_resources` | Provider provisions, updates, and decommissions infrastructure resources | service_provider |
| `serve_data` | Provider responds to queries with authoritative external data | information_provider |
| `authenticate` | Provider authenticates identities and returns tokens/roles/groups | auth_provider |
| `federate` | Provider is another DCM instance — mTLS mandatory, dual audit, sovereignty pre-check | peer_dcm |
| `execute_workflows` | Provider runs ephemeral workflows without producing persistent resources | process_provider |

A provider can declare **multiple capabilities**. The capability declaration includes everything DCM needs to interact with the provider for that capability — resource types, data domains, auth methods, etc.

### 2.3 Backward Compatibility

The old type names become convenience labels — shorthand for common capability profiles:

| Old type | Equivalent capability profile |
|----------|------------------------------|
| service_provider | `capabilities: [realize_resources]` |
| information_provider | `capabilities: [serve_data]` |
| auth_provider | `capabilities: [authenticate]` |
| peer_dcm | `capabilities: [federate]` |
| process_provider | `capabilities: [execute_workflows]` |

Existing provider registrations continue to work. The `provider_type` field becomes a resolved label derived from the declared capabilities.

---

## 3. Capability Discovery — DCM Side

### 3.1 The Capability Advertisement Endpoint

DCM exposes a machine-readable endpoint that describes what it can do:

```
GET /api/v1/capabilities
```

Response:

```json
{
  "dcm_instance": "dcm-emea-prod-1",
  "version": "1.0.0",
  "capabilities": {
    "lifecycle_management": {
      "description": "Full lifecycle management of infrastructure resources",
      "operations": ["create", "update", "scale", "decommission", "rehydrate"],
      "resource_types": ["Compute.VirtualMachine", "Network.IPAddress", "..."],
      "api_endpoint": "/api/v1/requests"
    },
    "policy_evaluation": {
      "description": "Policy-as-code evaluation on every request",
      "policy_types": ["gatekeeper", "validation", "transformation", "recovery", "orchestration_flow", "governance_matrix"],
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

### 3.2 Capability Query

External systems can query for specific capabilities:

```
GET /api/v1/capabilities?domain=cost
GET /api/v1/capabilities?domain=audit
GET /api/v1/capabilities?data_stream=true
GET /api/v1/capabilities?operation=create&resource_type=Compute.VirtualMachine
```

The response includes only matching capabilities with their API endpoints and subscription mechanisms.

### 3.3 The Integration Flow

A FinOps tool integrating with DCM:

```
1. FinOps tool queries:  GET /api/v1/capabilities?domain=cost
   
2. DCM responds with:
   - cost.estimated event stream (subscribe via webhook)
   - cost.attributed event stream (subscribe via webhook)  
   - cost estimation API (GET /api/v1/requests/{uuid}/cost-estimate)
   - payload schemas for each

3. FinOps tool subscribes: POST /api/v1/webhooks
   {
     "event_types": ["cost.estimated", "cost.attributed", "entity.realized"],
     "callback_url": "https://finops.example.com/dcm/events",
     "auth": { "type": "hmac_sha256", "secret_ref": "..." }
   }

4. Data flows automatically — no manual wiring
```

---

## 4. Capability Discovery — Provider Side

### 4.1 Provider Capability Advertisement

When a provider registers, it declares what it offers AND what it needs from DCM:

```yaml
provider:
  name: "Acme FinOps Platform"
  
  capabilities:
    serve_data:
      data_domains:
        - cost_optimization_recommendations
        - budget_forecasts
      query_interface: rest
      
  needs_from_dcm:
    - domain: cost
      description: "Cost estimation and attribution data"
    - domain: entity_lifecycle
      description: "Entity create/update/decommission events"
    - domain: placement_decisions
      description: "Placement scoring rationale for cost analysis"
```

### 4.2 Automatic Pipeline Establishment

When a provider registers with `needs_from_dcm`, DCM matches the declared needs against its capability advertisement and automatically offers subscription endpoints:

```json
// Registration response includes:
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

The provider then activates the subscriptions it wants. DCM never auto-subscribes — the provider explicitly opts in. But DCM tells the provider exactly what's available and how to get it.

### 4.3 Bidirectional Discovery

The pattern works in both directions:

```
Provider → DCM: "Here's what I can do" (capabilities)
Provider → DCM: "Here's what I need from you" (needs_from_dcm)
DCM → Provider: "Here's what I have that matches your needs" (matched_capabilities)
DCM → Provider: "Here's what I need from you" (dispatch payloads via the provider contract)
```

This replaces the current one-directional model where providers register with DCM but DCM doesn't advertise anything back.

---

## 5. How Capability Discovery Interacts with DCM

### 5.1 With the Service Catalog

The capability advertisement endpoint exposes what resource types DCM manages, but NOT the service catalog itself (which is tenant-scoped and RBAC-filtered). The capability endpoint is infrastructure-level: "DCM manages VMs, networks, databases." The catalog is consumer-level: "Here are the specific offerings you can request."

### 5.2 With Policy

Capability discovery does not bypass policy. A provider that discovers DCM's cost stream and subscribes to it still has its webhook authenticated, its data filtered by tenant scope, and its subscription audited.

### 5.3 With Audit

Every capability query, subscription establishment, and data stream delivery is audited. The audit trail shows: who queried capabilities, what they subscribed to, and what data was delivered.

### 5.4 With Federation

A peer_dcm provider (another DCM instance) uses capability discovery to understand what the remote instance can do before establishing a federation tunnel. This replaces the static federation scope declaration with a dynamic capability negotiation.

---

## 6. System Policies

| ID | Policy | Description |
|----|--------|-------------|
| DISC-001 | Capability advertisement is read-only and requires authentication | No anonymous capability queries |
| DISC-002 | Webhook subscriptions are tenant-scoped | A provider's subscription only receives events for entities in its authorized scope |
| DISC-003 | Capability query is rate-limited | Prevents enumeration attacks |
| DISC-004 | needs_from_dcm matching is advisory, not automatic | DCM suggests matches; provider activates subscriptions explicitly |
| DISC-005 | Capability schema versions follow API versioning strategy | Capability response format is versioned and backward-compatible |

---

## 7. Migration from Typed to Unified Model

Existing provider registrations continue to work. The `provider_type` field is retained as a resolved label derived from capabilities:

```
provider_type = "service_provider"  →  capabilities: [realize_resources]
provider_type = "information_provider"  →  capabilities: [serve_data]
```

New registrations can use either form. The control plane normalizes to the capability model internally. Over time, the type field becomes optional — capabilities are authoritative.
