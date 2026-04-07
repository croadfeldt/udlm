# DCM Data Model — Subscription Lifecycle Management

**Document Status:** 📋 Draft — Ready for Review
**Document Type:** Architecture Specification — Subscription as First-Class Data
**Related Documents:** [Foundational Abstractions](00-foundations.md) | [Entity Types](01-entity-types.md) | [Four States](02-four-states.md) | [Resource/Service Entities](06-resource-service-entities.md) | [Provider Contract](A-provider-contract.md) | [Policy Contract](B-policy-contract.md) | [Scheduled Requests](37-scheduled-requests.md) | [Event Catalog](33-event-catalog.md) | [Scoring Model](29-scoring-model.md)

---

## 1. What a Subscription Is

A **Subscription** is a first-class DCM Data artifact representing an ongoing, managed relationship between a Tenant and a set of capabilities delivered by one or more Providers. Unlike a one-time request that produces a resource and completes, a subscription persists — it has terms, renewal cycles, tier levels, and ongoing obligations that both DCM and the Provider must honor.

A subscription manages the lifecycle of the **binding** — what the consumer is entitled to receive, under what terms, for how long. The **resources** that the subscription produces and maintains are standard DCM entities (infrastructure_resource, process_resource, composite_resource) with their own lifecycles. The subscription governs them; it is not them.

**Examples of subscriptions:**
- A managed database service — ongoing provisioning, patching, backup, scaling within subscription tier
- A software license — entitlement to install, update, and receive patches for a software package
- A monitoring service — ongoing collection, alerting, and retention of metrics for subscribed resources
- A managed Kubernetes namespace — capacity allocation, policy enforcement, and upgrade management
- A compliance scanning service — periodic scanning, reporting, and remediation of subscribed resources

---

## 2. Subscription as Data

A Subscription follows every universal Data property defined in [00-foundations.md](00-foundations.md):

- **UUID** — stable across full lifecycle
- **Type** — `dcm.subscription` (registered in the Resource Type Registry)
- **Lifecycle state** — exactly one state at any moment (see Section 4)
- **Artifact metadata** — handle, version, status, owned_by, created_by
- **Provenance** — field-level lineage on every modification
- **Data classification** — per-field classification, inherited from managed entities and subscription terms
- **Immutability if versioned** — subscription terms are versioned; published terms cannot be modified
- **Audit trail** — every subscription operation produces an audit record

### 2.1 Subscription Artifact Structure

```yaml
subscription:
  # ── Identity ───────────────────────────────────────────────────
  subscription_uuid: <uuid>
  handle: "team-alpha/managed-postgres-prod"
  display_name: "Production PostgreSQL — Team Alpha"

  # ── Binding ────────────────────────────────────────────────────
  tenant_uuid: <uuid>                    # Who subscribes
  catalog_item_uuid: <uuid>              # What they subscribed to
  resource_type: "Database.PostgreSQL"   # FQN of the subscribed resource type
  provider_uuid: <uuid>                  # Who fulfills the subscription

  # ── Terms ──────────────────────────────────────────────────────
  terms:
    tier: "standard"                     # Subscription tier (from catalog item tiers)
    consumption_model: "subscription"    # subscription | reserved | on_demand
    billing_period: "monthly"
    auto_renew: true
    renewal_advance_notice: "P30D"       # Notify before renewal
    started_at: "2026-04-01T00:00:00Z"
    expires_at: "2027-04-01T00:00:00Z"  # null if auto_renew with no end date
    terms_version: "1.0.0"              # Versioned — immutable once active

  # ── Entitlements ───────────────────────────────────────────────
  entitlements:
    max_instances: 5                     # How many entities the subscription covers
    resource_limits:                     # Per-entity limits within subscription
      vcpus: 16
      memory_gb: 64
      storage_gb: 500
    capabilities:                        # What the provider will do under this subscription
      - provision
      - patch
      - backup
      - scale_vertical
      - monitor
    update_channels:                     # What update streams the consumer subscribes to
      - channel: "stable"
        auto_apply: true                 # Provider applies updates automatically
      - channel: "security"
        auto_apply: true
      - channel: "feature"
        auto_apply: false                # Requires consumer approval

  # ── Managed Entities ───────────────────────────────────────────
  managed_entities:                       # Entities produced/maintained by this subscription
    - entity_uuid: <uuid>
      role: "primary"
    - entity_uuid: <uuid>
      role: "replica"

  # ── Lifecycle ──────────────────────────────────────────────────
  lifecycle_state: "ACTIVE"
  
  # ── Standard artifact metadata ─────────────────────────────────
  version: "1.0.0"
  created_at: "2026-04-01T00:00:00Z"
  created_by: <actor_uuid>
  provenance: { ... }                    # Field-level provenance per universal model
```

### 2.2 Relationship to Existing Entity Types

A Subscription is **not** a new entity type alongside infrastructure_resource, process_resource, and composite_resource. It is a **binding artifact** — a Data object that governs the lifecycle of entities. The entities it manages are standard DCM entities with their own types, states, and lifecycles.

```
Subscription (binding — terms, entitlements, renewal)
    │
    ├── manages → Entity A (infrastructure_resource — the database primary)
    ├── manages → Entity B (infrastructure_resource — the database replica)
    ├── manages → Entity C (process_resource — nightly backup job)
    └── manages → Entity D (process_resource — monthly patching job)
```

The `manages` relationship uses the standard Entity Relationship model (doc 09) with relationship nature `subscription_binding`:

```yaml
relationship:
  source_uuid: <subscription_uuid>
  target_uuid: <entity_uuid>
  nature: subscription_binding
  role: managed_entity
  lifecycle_policy:
    on_source_suspend: suspend           # Suspend entity when subscription suspends
    on_source_cancel: decommission       # Decommission entity when subscription cancels
    on_source_expire: notify             # Notify before decommissioning on expiry
```

---

## 3. Subscription in the Catalog

Catalog items declare whether they support subscription consumption by including subscription terms in their field schema. This is configurable per catalog item — not every resource type requires subscription support.

### 3.1 Catalog Item with Subscription Support

```yaml
catalog_item:
  handle: "managed-postgres"
  resource_type: "Database.PostgreSQL"
  consumption_models: ["on_demand", "subscription"]   # What models this item supports
  
  subscription_tiers:                                   # Available when consumption_model = subscription
    - tier: "basic"
      entitlements:
        max_instances: 1
        capabilities: [provision, monitor]
        update_channels: [security]
      cost:
        monthly: 500
        currency: "USD"
    - tier: "standard"
      entitlements:
        max_instances: 5
        capabilities: [provision, patch, backup, monitor]
        update_channels: [stable, security]
      cost:
        monthly: 2000
        currency: "USD"
    - tier: "premium"
      entitlements:
        max_instances: 20
        capabilities: [provision, patch, backup, scale_vertical, scale_horizontal, monitor, disaster_recovery]
        update_channels: [stable, security, feature]
      cost:
        monthly: 8000
        currency: "USD"

  field_schema:
    properties:
      consumption_model:
        type: string
        enum: ["on_demand", "subscription"]
        default: "on_demand"
      subscription_tier:
        type: string
        enum: ["basic", "standard", "premium"]
        depends_on:
          consumption_model: "subscription"
      auto_renew:
        type: boolean
        default: true
        depends_on:
          consumption_model: "subscription"
```

### 3.2 Catalog Items Without Subscription Support

Catalog items that only support one-time requests simply omit `subscription_tiers` and set `consumption_models: ["on_demand"]`. The subscription machinery is not invoked. This is the default behavior — subscription support is opt-in per catalog item.

---

## 4. Subscription Lifecycle States

```
Consumer submits subscription request
    │
    ▼
PENDING ──────────── Policy evaluation + approval routing
    │
    ▼
PROVISIONING ─────── Provider creates initial managed entities
    │
    ▼
ACTIVE ───────────── Ongoing — provider fulfills subscription obligations
    │
    ├──→ SUSPENDED ── Consumer or policy suspends; managed entities suspended
    │       │
    │       └──→ ACTIVE (resumed)
    │
    ├──→ RENEWAL_PENDING ── Approaching expiry with auto_renew
    │       │
    │       ├──→ ACTIVE (renewed — new terms_version)
    │       └──→ EXPIRED (renewal failed or declined)
    │
    ├──→ TIER_CHANGE_PENDING ── Consumer requested tier change
    │       │
    │       └──→ ACTIVE (new tier applied)
    │
    ├──→ EXPIRED ──── Terms expired without renewal
    │       │
    │       └──→ DECOMMISSIONING (grace period passed)
    │
    └──→ CANCELLED ── Consumer or admin cancels
            │
            └──→ DECOMMISSIONING → DECOMMISSIONED
```

**Terminal states:** DECOMMISSIONED, CANCELLED (after entity cleanup).

**Grace period:** When a subscription transitions to EXPIRED or CANCELLED, managed entities are not immediately decommissioned. A configurable grace period (default: P30D) allows the consumer to renew, export data, or transition to a different subscription. During the grace period, entities remain in OPERATIONAL but new provisioning under the subscription is blocked.

### 4.1 State Transitions and Policy Triggers

Every state transition fires a subscription lifecycle event (see Section 7) and triggers Policy Engine evaluation. Policies govern:

- Whether auto-renewal is permitted for this tenant/tier/resource type
- Whether tier upgrades require approval (GateKeeper)
- Whether downgrades trigger capacity validation (Validation)
- What happens to managed entities on suspension (Lifecycle Policy)
- Cost attribution changes on tier change (Transformation)

---

## 5. Provider-Originated Changes Through Subscriptions

This is the critical integration point. When a provider has updates to deliver under a subscription — a software patch, a version upgrade, a configuration change, a capacity adjustment — those changes flow through DCM as **provider-originated updates**, following the standard flow documented in [A-provider-contract.md](A-provider-contract.md).

### 5.1 The Standard Provider-Originated Update Flow

Subscriptions do not introduce a new flow — they create a **context** in which the existing flow fires more frequently and with pre-negotiated terms.

```
Provider has an update for a managed entity
    │
    ▼
POST /api/v1/provider/entities/{entity_uuid}/update-notification
    │
    ▼
DCM validates: Is this entity managed by an active subscription?
    │
    ├── Yes → Check subscription entitlements:
    │         Is this update type within the subscription's capabilities?
    │         Is this update channel auto_apply for this subscription?
    │         │
    │         ├── Auto-apply enabled → Pre-authorized update flow
    │         │   → Policy Engine evaluates (pre-authorization GateKeeper)
    │         │   → If within declared bounds → write Realized State snapshot
    │         │   → Audit record: source_type = subscription_update
    │         │   → Events: entity.modified, subscription.update_applied
    │         │
    │         └── Auto-apply disabled → Consumer approval required
    │             → Consumer notification with update details
    │             → Consumer approves/rejects via API or GitOps
    │             → Standard provider_update approval flow
    │
    └── No → Standard provider-originated update (non-subscription context)
```

### 5.2 Pre-Authorization via Subscription Terms

Subscriptions extend the existing pre-authorization model (RSE-012). When a provider registers subscription capabilities, the subscription terms define what categories of updates are pre-authorized:

```yaml
# In the subscription's update_channels:
update_channels:
  - channel: "security"
    auto_apply: true           # Security patches are pre-authorized
    max_downtime: "PT5M"       # Pre-authorized only if downtime ≤ 5 minutes
  - channel: "feature"
    auto_apply: false          # Feature updates require consumer approval
    preview_period: "P7D"      # Consumer gets 7 days to review before deadline
```

The GateKeeper policy that evaluates pre-authorization checks:

1. Is the update from a registered provider with an active subscription?
2. Is the update channel declared in the subscription's `update_channels`?
3. Is `auto_apply` true for this channel?
4. Are the declared constraints (max_downtime, resource_limit bounds) satisfied?
5. Does the update pass all active Validation policies?

If all checks pass, the update is applied without consumer intervention. This is the "subscribe and forget" model for security patches — the consumer opted in at subscription time.

### 5.3 Provider Obligations Under Subscription

When a provider accepts a subscription (by acknowledging the subscription dispatch), it takes on contractual obligations:

- **Delivery:** Provide the capabilities declared in the subscription tier
- **Update delivery:** Push updates through DCM's standard callback API — never directly to managed entities
- **Health reporting:** Report health of managed entities through the standard health endpoint
- **Capacity honoring:** Stay within the resource limits declared in subscription entitlements
- **Discovery:** Include managed entities in discovery responses so DCM can detect drift
- **Decommission compliance:** Clean up managed entities when subscription is cancelled/expired after grace period

These obligations are enforced by the existing Provider Contract mechanisms — health monitoring, drift detection, and the Governance Matrix. The subscription doesn't create new enforcement — it creates a context that existing enforcement applies to.

---

## 6. Subscription Request Pipeline

A subscription request follows the standard DCM request pipeline with subscription-specific Transformation and GateKeeper policies:

### 6.1 Consumer Submits Subscription Request

Via API:
```
POST /api/v1/requests
{
  "catalog_item_uuid": "<managed-postgres-uuid>",
  "fields": {
    "consumption_model": "subscription",
    "subscription_tier": "standard",
    "auto_renew": true,
    "display_name": "prod-postgres",
    "vcpus": 8,
    "memory_gb": 32
  }
}
```

Via GitOps:
```yaml
# intent-store/{tenant_uuid}/Database/PostgreSQL/{entity_uuid}/intent.yaml
apiVersion: dcm/v1
kind: SubscriptionRequest
metadata:
  handle: "team-alpha/prod-postgres"
spec:
  catalog_item: "managed-postgres"
  consumption_model: subscription
  subscription_tier: standard
  auto_renew: true
  fields:
    vcpus: 8
    memory_gb: 32
```

### 6.2 Pipeline Processing

```
Intent captured
    │
    ▼
Layer Assembly (Request Processor)
    │  ── Core layers (profile defaults)
    │  ── Service layers (subscription tier defaults)
    │  ── Consumer fields (overrides)
    │  ── Subscription terms injected by Transformation Policy
    ▼
Policy Evaluation
    │  ── Validation: tier exists, entitlements valid, resource limits within tier
    │  ── GateKeeper: tenant authorized for subscription model, budget approval
    │  ── Transformation: inject subscription_uuid, terms, renewal schedule
    │  ── Scoring: aggregate risk score for approval routing
    ▼
Placement (if applicable — select provider)
    ▼
Subscription Created (PENDING → PROVISIONING)
    │  ── Subscription artifact written to Subscription Store
    │  ── Provider dispatched to create initial managed entities
    ▼
Provider Realizes Initial Entities
    │  ── Standard realization flow for each managed entity
    │  ── Each entity linked to subscription via subscription_binding relationship
    ▼
Subscription ACTIVE
    │  ── Ongoing: provider pushes updates via callback
    │  ── DCM applies updates per subscription terms
    │  ── Discovery monitors managed entities for drift
```

---

## 7. Subscription Events

All subscription events use the standard DCM event envelope (doc 33) and are published to the `dcm-events` Kafka topic.

| Event Type | Fires When | Urgency |
|------------|-----------|---------|
| `subscription.created` | New subscription enters PENDING | medium |
| `subscription.activated` | Subscription transitions to ACTIVE | medium |
| `subscription.suspended` | Subscription suspended (consumer or policy) | high |
| `subscription.resumed` | Subscription resumes from SUSPENDED | medium |
| `subscription.renewal_pending` | Approaching expiry with auto_renew | medium |
| `subscription.renewed` | Renewal completed — new terms_version | medium |
| `subscription.renewal_failed` | Renewal attempt failed (payment, policy, provider) | high |
| `subscription.tier_changed` | Tier upgrade or downgrade applied | medium |
| `subscription.update_applied` | Provider-originated update applied to managed entity | low |
| `subscription.update_rejected` | Consumer rejected a provider-originated update | medium |
| `subscription.expiry_approaching` | Within renewal_advance_notice of expiry | high |
| `subscription.expired` | Subscription reached expiry without renewal | high |
| `subscription.cancelled` | Consumer or admin cancelled subscription | high |
| `subscription.decommissioning` | Grace period ended — entities being decommissioned | critical |
| `subscription.decommissioned` | All managed entities decommissioned — terminal | medium |

---

## 8. Subscription Policies

Subscriptions are governed by the same Policy Engine as all other DCM operations. No new policy types are needed — existing types apply:

### 8.1 GateKeeper Policies

- **Subscription authorization:** Which tenants/groups can use subscription consumption model
- **Tier authorization:** Which tiers are available to which tenants (e.g., "premium" requires FSI profile)
- **Budget gates:** Subscription cost within tenant budget allocation
- **Renewal authorization:** Whether auto-renewal is permitted for this tenant/resource type

### 8.2 Validation Policies

- **Entitlement validation:** Requested instances within tier's max_instances
- **Resource limit validation:** Requested resources within tier's limits
- **Tier downgrade validation:** Ensure current usage fits within lower tier before allowing downgrade

### 8.3 Transformation Policies

- **Subscription term injection:** Inject subscription_uuid, terms, schedule, and entitlements into the request payload
- **Cost attribution:** Attach subscription cost to tenant's cost allocation
- **Update channel defaults:** Inject default update channel configuration based on tier

### 8.4 Lifecycle Policies

- **Managed entity lifecycle:** What happens to managed entities when subscription state changes
- **Expiry action:** Trigger renewal, notification, or decommission on TTL expiry
- **Cascade suspension:** Suspend all managed entities when subscription suspends

### 8.5 Recovery Policies

- **Renewal failure recovery:** What happens when auto-renewal fails (retry, notify, suspend, expire)
- **Provider failure recovery:** What happens when the subscription's provider goes unhealthy

---

## 9. Consumer API Endpoints

Subscription management is exposed through the Consumer API:

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/subscriptions` | Create a subscription (via request pipeline) |
| `GET` | `/api/v1/subscriptions` | List tenant's subscriptions (paginated) |
| `GET` | `/api/v1/subscriptions/{uuid}` | Get subscription details |
| `PATCH` | `/api/v1/subscriptions/{uuid}` | Update subscription (tier change, auto_renew toggle) |
| `POST` | `/api/v1/subscriptions/{uuid}:cancel` | Cancel subscription (starts grace period) |
| `POST` | `/api/v1/subscriptions/{uuid}:renew` | Manually renew subscription |
| `POST` | `/api/v1/subscriptions/{uuid}:suspend` | Suspend subscription |
| `POST` | `/api/v1/subscriptions/{uuid}:resume` | Resume suspended subscription |
| `GET` | `/api/v1/subscriptions/{uuid}/entities` | List managed entities under this subscription |
| `GET` | `/api/v1/subscriptions/{uuid}/updates` | List pending and applied updates |
| `POST` | `/api/v1/subscriptions/{uuid}/updates/{update_uuid}:approve` | Approve a pending update |
| `POST` | `/api/v1/subscriptions/{uuid}/updates/{update_uuid}:reject` | Reject a pending update |

Admin API extensions:

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/admin/subscriptions` | List all subscriptions across tenants |
| `GET` | `/api/v1/admin/subscriptions/expiring` | Subscriptions approaching expiry |
| `POST` | `/api/v1/admin/subscriptions/{uuid}:force-cancel` | Admin force cancellation |

---

## 10. Subscription Store

Subscriptions are stored in the DCM operational store alongside other first-class artifacts. The store implementation follows the Storage Provider contract (doc 11).

```sql
CREATE TABLE subscriptions (
    subscription_uuid       UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_uuid             UUID NOT NULL REFERENCES tenants(tenant_uuid),
    handle                  VARCHAR(256) NOT NULL,
    display_name            VARCHAR(256) NOT NULL,
    catalog_item_uuid       UUID NOT NULL,
    resource_type           VARCHAR(256) NOT NULL,
    provider_uuid           UUID NOT NULL,
    lifecycle_state         VARCHAR(32) NOT NULL DEFAULT 'PENDING'
                                CHECK (lifecycle_state IN (
                                    'PENDING', 'PROVISIONING', 'ACTIVE',
                                    'SUSPENDED', 'RENEWAL_PENDING', 'TIER_CHANGE_PENDING',
                                    'EXPIRED', 'CANCELLED', 'DECOMMISSIONING', 'DECOMMISSIONED'
                                )),
    terms                   JSONB NOT NULL DEFAULT '{}',
    entitlements            JSONB NOT NULL DEFAULT '{}',
    update_channels         JSONB NOT NULL DEFAULT '[]',
    terms_version           VARCHAR(32) NOT NULL DEFAULT '1.0.0',
    started_at              TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,
    grace_period            INTERVAL NOT NULL DEFAULT '30 days',
    auto_renew              BOOLEAN NOT NULL DEFAULT true,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(tenant_uuid, handle)
);

CREATE INDEX idx_subscriptions_tenant ON subscriptions(tenant_uuid, lifecycle_state);
CREATE INDEX idx_subscriptions_provider ON subscriptions(provider_uuid);
CREATE INDEX idx_subscriptions_expiry ON subscriptions(expires_at) WHERE lifecycle_state = 'ACTIVE';

-- Managed entity bindings
CREATE TABLE subscription_entities (
    subscription_uuid       UUID NOT NULL REFERENCES subscriptions(subscription_uuid),
    entity_uuid             UUID NOT NULL,
    role                    VARCHAR(64) NOT NULL DEFAULT 'managed',
    bound_at                TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (subscription_uuid, entity_uuid)
);

-- Update tracking
CREATE TABLE subscription_updates (
    update_uuid             UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_uuid       UUID NOT NULL REFERENCES subscriptions(subscription_uuid),
    entity_uuid             UUID NOT NULL,
    provider_uuid           UUID NOT NULL,
    channel                 VARCHAR(64) NOT NULL,
    status                  VARCHAR(32) NOT NULL DEFAULT 'PENDING'
                                CHECK (status IN ('PENDING', 'APPROVED', 'REJECTED',
                                                  'APPLIED', 'FAILED', 'EXPIRED')),
    update_payload          JSONB NOT NULL DEFAULT '{}',
    submitted_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at              TIMESTAMPTZ,
    decided_by              UUID,
    applied_at              TIMESTAMPTZ,
    auto_applied            BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX idx_sub_updates_subscription ON subscription_updates(subscription_uuid, status);
CREATE INDEX idx_sub_updates_pending ON subscription_updates(status, submitted_at) WHERE status = 'PENDING';

-- RLS
ALTER TABLE subscriptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_entities ENABLE ROW LEVEL SECURITY;
ALTER TABLE subscription_updates ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_subscriptions
    ON subscriptions FOR ALL TO dcm_app
    USING (tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid);

CREATE POLICY tenant_isolation_sub_entities
    ON subscription_entities FOR ALL TO dcm_app
    USING (subscription_uuid IN (
        SELECT subscription_uuid FROM subscriptions
        WHERE tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid
    ));

CREATE POLICY tenant_isolation_sub_updates
    ON subscription_updates FOR ALL TO dcm_app
    USING (subscription_uuid IN (
        SELECT subscription_uuid FROM subscriptions
        WHERE tenant_uuid = current_setting('dcm.current_tenant_uuid')::uuid
    ));
```

---

## 11. Capability Domain — SUB (Subscription Management)

| ID | Capability | Consumer | Provider | Platform/Admin |
|----|-----------|----------|----------|----------------|
| SUB-001 | Create subscription | Submit subscription request with tier and terms | Acknowledge subscription, provision initial entities | Approve subscription creation |
| SUB-002 | Manage subscription lifecycle | Suspend, resume, cancel own subscriptions | Report managed entity status | Force-cancel, view all subscriptions |
| SUB-003 | Change subscription tier | Request tier upgrade/downgrade | Adjust capacity for managed entities | Approve tier changes that require admin |
| SUB-004 | Subscription renewal | Approve/decline renewal; view renewal status | Honor renewed terms | Configure renewal policies |
| SUB-005 | Provider-originated updates | Approve/reject non-auto updates | Submit updates via standard callback | View update audit trail |
| SUB-006 | Update channel management | Configure auto_apply per channel | Declare available update channels | Set organization-wide channel policies |
| SUB-007 | Subscription cost attribution | View subscription cost | Declare cost model per tier | Configure cost allocation rules |
| SUB-008 | Entitlement enforcement | View remaining capacity | Stay within entitlement bounds | Override entitlements in exceptional cases |
| SUB-009 | Grace period management | View grace period status; request extension | Continue health reporting during grace | Configure grace period defaults |
| SUB-010 | Subscription audit trail | View own subscription audit history | — | View all subscription audit records |

---

## 12. Open Questions

| # | Question | Impact | Status |
|---|----------|--------|--------|
| 1 | Should subscription-to-subscription dependencies be supported (e.g., a monitoring subscription that depends on a compute subscription)? | Dependency model complexity | ✅ Resolved — use standard Entity Relationship model with `subscription_binding` nature; subscriptions can reference other subscriptions via relationship |
| 2 | How does subscription interact with the Meta Provider model — can a Meta Provider compose subscriptions from multiple child providers? | Compound subscription complexity | ✅ Resolved — yes, a Meta Provider subscription creates child subscriptions on constituent providers; parent subscription lifecycle governs children per standard Meta Provider composition model (doc 30) |
| 3 | Should subscription cost be pre-computed or dynamic? | Cost attribution accuracy | ✅ Resolved — both; pre-computed estimate at request time (displayed in catalog), actual cost tracked via ongoing cost attribution (Transformation Policy injects cost records on each billing period) |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
