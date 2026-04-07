# DCM Data Model — Location Topology Layer Model

**Document Status:** 📋 Draft — Ready for Implementation Feedback
**Document Type:** Core Data Model Specification
**Related Documents:** [Data Layers and Assembly](03-layering-and-versioning.md) | [Resource Type Hierarchy](05-resource-type-hierarchy.md) | [Control Plane Components](25-control-plane-components.md) | [Governance Matrix](27-governance-matrix.md) | [Scoring Model](29-scoring-model.md) | [Registry Governance](20-registry-governance.md) | [Service Catalog](05-resource-type-hierarchy.md)

> **AEP Alignment:** API endpoints follow [AEP](https://aep.dev) conventions.
> See `schemas/openapi/dcm-admin-api.yaml` for the normative admin API specification.

---

## 0. Pattern Context

Location layers are one application of the **Reference Data Layer** pattern (doc 03,
Section 3.7). The same pattern governs OS images, VM sizes, network zones, storage
classes, and any other field where valid values are a governed, versioned, authority-owned
set rather than a static list.

The concepts in this document — layer instances as field constraint sources, hierarchy
assembly, authority ownership, lifecycle governance — apply equally to all Reference Data
Layer types. Location is specified in detail here because it has the richest internal
hierarchy and the most complex assembly behaviour of all the standard reference data types.

**How location layers appear to consumers:**

In a catalog item response, the `location` field has a `layer_reference` constraint of
type `location.data_center`. The `allowed_values` list is the set of active location
layer instances the consumer is entitled to and that this resource type is eligible for.
The consumer submits a layer UUID; DCM assembles the full ancestor chain.

---

## 1. Purpose

Location topology layers are a subset of **Core Layers** (doc 03, Section 3.2) that encode
where resources exist or may be allocated. They define the physical and logical hierarchy of
an organization's infrastructure estate — from the broadest geographic unit down to the
individual rack — and carry the authoritative data that governs resource placement, sovereign
data routing, cost attribution, and capacity visibility.

Every DCM resource allocation happens *somewhere*. That somewhere is not a string the
consumer types — it is a structured, versioned, authority-owned layer. When a consumer
selects a location via the service catalog or API, they are selecting from the registered
location topology. DCM then assembles the appropriate location layers into the request
payload, enriching it with all data associated with that location hierarchy.

**What location topology layers answer:**
- *Where can this resource be placed?* — the consumer selection surface
- *What data applies at each level of that location?* — layer content injected into the payload
- *Who is responsible for this location?* — authority and ownership model
- *What constraints apply at this location?* — sovereignty, compliance, network, power
- *What capacity is available here?* — provider capacity scoped to this location

---

## 2. Design Principles

**Configurable names, standard types.** The names of topology nodes are organization-defined
(your organization may call them "Sites" not "Data Centers"). The *types* — the classification
of each level of the hierarchy — are standardized. Organizations configure instances of
standard types; they can also add custom type levels where needed.

**Hierarchical and composable.** Location types form a hierarchy from broadest to most
specific. A resource allocated to a Rack inherits data from its Row, Hall, Data Center, Zone,
Region, and Country layers — the full ancestry chain is assembled and merged.

**Layer-first, not field-first.** Location is not a single `location: DC1-ZONE-A-RACK-12`
string. It is a resolved chain of layers. Each layer in the chain carries structured data
about that location level. The assembled payload contains the full context of the
selected location.

**Authority-owned.** Each location type has a designated owning authority (the team
responsible for creating and maintaining instances of that type). The authority model
is configurable but DCM ships with sensible industry defaults.

**Linked to the service catalog.** Location topology nodes are exposed to consumers
through the catalog as selection dimensions. When a consumer requests a resource,
they select from available location nodes — filtered by their entitlements and the
resource type's placement policies.

---

## 3. Standard Location Type Hierarchy

DCM ships with nine standard location types. The hierarchy is ordered from broadest
to most specific. Each type has a standard name, a short code for handles and references,
and a set of standard data fields.

```
Level 1 — Country (CTY)
Level 2 — Region (RGN)
Level 3 — Zone / Availability Zone (AZ)
Level 4 — Campus / Site (SITE)
Level 5 — Data Center / Facility (DC)
Level 6 — Hall / Pod / Row (HALL)      [optional]
Level 7 — Cage / Enclosure (CAGE)     [optional]
Level 8 — Rack (RACK)
Level 9 — Unit / Slot (UNIT)           [optional — typically provider-managed]
```

Levels marked `[optional]` may be omitted if not relevant to an organization's estate.
The hierarchy is still valid when levels are skipped — a Rack can be a direct child
of a Data Center if Halls and Cages are not used.

**Custom types** may be inserted at any level. For example, a Navy context might insert
`Fleet / Ship` between Region and Data Center. Custom types follow the same format as
standard types and are registered in the Location Type Registry.

---

## 4. Location Type Definitions

Each standard type has a defined schema of fields. These fields become the data
carried by location layer instances of that type.

### 4.1 Country (CTY)

```yaml
location_type: country
code: CTY
level: 1

standard_fields:
  country_name:
    type: string
    required: true
    example: "Germany"

  iso_3166_1_alpha2:
    type: string
    pattern: '^[A-Z]{2}$'
    required: true
    example: "DE"

  iso_3166_1_alpha3:
    type: string
    pattern: '^[A-Z]{3}$'
    required: true
    example: "DEU"

  data_sovereignty_jurisdiction:
    type: string
    required: true
    description: "Primary legal jurisdiction for data sovereignty"
    example: "EU/GDPR"

  regulatory_frameworks:
    type: array
    items: string
    required: false
    example: [GDPR, NIS2, eIDAS]

  primary_currency:
    type: string
    format: ISO-4217
    required: false
    example: "EUR"

  utc_offsets:
    type: array
    items: string
    required: false
    example: ["UTC+1", "UTC+2"]    # CET/CEST

owning_authority_default: Platform Governance Team
```

### 4.2 Region (RGN)

```yaml
location_type: region
code: RGN
level: 2
parent_type: country

standard_fields:
  region_name:
    type: string
    required: true
    example: "EU West"

  region_code:
    type: string
    required: true
    example: "eu-west"

  geographic_bounds:
    type: object
    required: false
    description: "Approximate lat/lon bounding box"
    properties:
      lat_min: { type: number }
      lat_max: { type: number }
      lon_min: { type: number }
      lon_max: { type: number }

  primary_interconnect:
    type: string
    required: false
    description: "Primary network interconnect or IXP serving this region"
    example: "DE-CIX Frankfurt"

  failover_region:
    type: string
    format: location-handle
    required: false
    description: "Handle of the designated DR failover region"
    example: "regions/eu-north"

  latency_profile:
    type: object
    required: false
    properties:
      intra_region_ms: { type: number, example: 2 }
      to_regions:
        type: object
        additionalProperties: { type: number }
        example: { "eu-north": 15, "us-east": 85 }

owning_authority_default: Network Operations
```

### 4.3 Zone / Availability Zone (AZ)

```yaml
location_type: zone
code: AZ
level: 3
parent_type: region

standard_fields:
  zone_name:
    type: string
    required: true
    example: "EU West Zone A"

  zone_code:
    type: string
    required: true
    example: "eu-west-1a"

  isolation_boundary:
    type: string
    enum: [independent_power, independent_cooling, independent_network, full]
    required: true
    description: "What failure domains this zone is isolated from"

  high_availability_peer_zones:
    type: array
    items: { type: string, format: location-handle }
    required: false
    description: "Zones that form an HA pair with this zone"
    example: ["zones/eu-west-1b", "zones/eu-west-1c"]

  target_rpo_minutes:
    type: integer
    required: false
    description: "Recovery Point Objective for resources in this zone"

  target_rto_minutes:
    type: integer
    required: false
    description: "Recovery Time Objective for resources in this zone"

owning_authority_default: Data Center Operations
```

### 4.4 Campus / Site (SITE)

```yaml
location_type: site
code: SITE
level: 4
parent_type: zone

standard_fields:
  site_name:
    type: string
    required: true
    example: "Frankfurt Campus"

  site_code:
    type: string
    required: true
    example: "FRA-CAMPUS-01"

  physical_address:
    type: object
    required: true
    properties:
      street:   { type: string }
      city:     { type: string }
      postal_code: { type: string }
      country:  { type: string, format: iso-3166-1-alpha2 }

  owned_or_leased:
    type: string
    enum: [owned, leased, colocation, shared]
    required: true

  security_tier:
    type: integer
    enum: [1, 2, 3, 4]
    required: false
    description: "Physical security tier (1=highest)"

  noc_contact:
    type: object
    required: false
    properties:
      email:   { type: string }
      phone:   { type: string }
      escalation_url: { type: string }

owning_authority_default: Facilities Management
```

### 4.5 Data Center / Facility (DC)

```yaml
location_type: data_center
code: DC
level: 5
parent_type: site

standard_fields:
  dc_name:
    type: string
    required: true
    example: "DC1 — Frankfurt Alpha"

  dc_code:
    type: string
    required: true
    example: "FRA-DC1"

  tier_classification:
    type: string
    enum: [tier_1, tier_2, tier_3, tier_4]
    required: false
    description: "Uptime Institute Tier classification"

  power_capacity_kw:
    type: number
    required: false
    description: "Total available power in kilowatts"

  cooling_capacity_kw:
    type: number
    required: false

  pue_rating:
    type: number
    required: false
    description: "Power Usage Effectiveness rating (1.0 = perfect)"
    example: 1.35

  redundancy_model:
    type: string
    enum: [N, N+1, 2N, 2N+1]
    required: false
    description: "Power and cooling redundancy model"

  network_uplinks:
    type: array
    required: false
    items:
      type: object
      properties:
        carrier: { type: string }
        bandwidth_gbps: { type: number }
        redundant: { type: boolean }

  on_site_contact:
    type: object
    required: false
    properties:
      role:  { type: string }
      email: { type: string }
      phone: { type: string }

  dc_operations_team:
    type: string
    format: group-handle
    required: true
    description: "DCM group owning this data center"
    example: "groups/dc-operations-fra"

  certifications:
    type: array
    required: false
    items:
      type: object
      properties:
        standard: { type: string, example: "ISO 27001" }
        expires_at: { type: string, format: date }

owning_authority_default: Data Center Operations
```

### 4.6 Hall / Pod / Row (HALL) — Optional

```yaml
location_type: hall
code: HALL
level: 6
parent_type: data_center
optional: true

standard_fields:
  hall_name:
    type: string
    required: true
    example: "Hall A — High Density"

  hall_code:
    type: string
    required: true
    example: "FRA-DC1-HALL-A"

  network_segment:
    type: string
    required: false
    description: "Primary network segment / VLAN for this hall"

  power_phase:
    type: string
    required: false
    description: "Power phase distribution (3-phase, single-phase)"

  cooling_type:
    type: string
    enum: [air, liquid, rear_door, immersion]
    required: false

  max_rack_units:
    type: integer
    required: false
    description: "Total rack units available in this hall"

owning_authority_default: Data Center Operations
```

### 4.7 Cage / Enclosure (CAGE) — Optional

```yaml
location_type: cage
code: CAGE
level: 7
parent_type: hall
optional: true

standard_fields:
  cage_name:
    type: string
    required: true
    example: "Cage 12 — Payments Isolated Zone"

  cage_code:
    type: string
    required: true
    example: "FRA-DC1-HALL-A-CAGE-12"

  tenant_uuid:
    type: string
    format: uuid
    required: false
    description: "If this cage is dedicated to a specific DCM Tenant"

  security_classification:
    type: string
    required: false
    description: "Physical access classification for this cage"
    example: "restricted"

  access_control_system:
    type: string
    required: false
    example: "Lenel S2"

owning_authority_default: Data Center Operations
```

### 4.8 Rack (RACK)

```yaml
location_type: rack
code: RACK
level: 8
parent_type: cage   # or hall or data_center if cage/hall levels are omitted

standard_fields:
  rack_name:
    type: string
    required: true
    example: "Rack A-12-03"

  rack_code:
    type: string
    required: true
    example: "FRA-DC1-A-12-03"

  rack_units:
    type: integer
    required: true
    description: "Total rack units (U) capacity"
    example: 42

  rack_units_available:
    type: integer
    required: false
    description: "Current available rack units (maintained by Data Center Operations)"

  power_circuits:
    type: array
    required: false
    items:
      type: object
      properties:
        circuit_id: { type: string }
        amperage:   { type: number }
        phase:      { type: string }
        redundant:  { type: boolean }

  max_power_kw:
    type: number
    required: false
    description: "Maximum power draw for this rack"

  network_top_of_rack:
    type: object
    required: false
    properties:
      switch_model:    { type: string }
      uplink_gbps:     { type: number }
      port_count:      { type: integer }
      vlan_range:      { type: string }

  patch_panel_id:
    type: string
    required: false

owning_authority_default: Data Center Operations
```

---

## 5. Location Layer Instance Format

Each location node is a **Core Layer** artifact stored in GitOps and registered in DCM.
It follows the standard layer format (doc 03) with location-specific fields in its data block.

```yaml
layer:
  artifact_metadata:
    uuid: <uuid>
    handle: "locations/dc/fra-dc1"      # standard handle pattern: locations/{type}/{code}
    version: "1.2.0"
    status: active
    owned_by:
      display_name: "Data Center Operations — Frankfurt"
      group_handle: "groups/dc-operations-fra"
      notification_endpoint: <endpoint>
    created_via: pr
    created_at: <ISO 8601>

  # Layer classification
  layer_type: core                        # always 'core' for location layers
  location_type: data_center              # the standard type code from Section 4
  scope: type_agnostic                    # location layers apply to all resource types

  # Priority — location layers occupy a dedicated band in the priority space
  priority:
    value: "200.10.0"                     # see Section 7 for priority band allocation
    label: "core.location.dc.fra-dc1"
    category: core_location
    rationale: "Data Center location layer for FRA-DC1"

  # Hierarchy — parent location
  location_hierarchy:
    parent_handle: "locations/site/fra-campus-01"
    parent_type: site
    ancestors:
      - handle: "locations/az/eu-west-1a"
        type: zone
      - handle: "locations/region/eu-west"
        type: region
      - handle: "locations/country/de"
        type: country

  # The location data — fields from the type definition (Section 4.5)
  data:
    dc_name: "DC1 — Frankfurt Alpha"
    dc_code: "FRA-DC1"
    tier_classification: tier_3
    power_capacity_kw: 4000
    pue_rating: 1.35
    redundancy_model: "2N"
    network_uplinks:
      - carrier: "DE-CIX"
        bandwidth_gbps: 100
        redundant: true
      - carrier: "NTT"
        bandwidth_gbps: 100
        redundant: true
    dc_operations_team: "groups/dc-operations-fra"
    certifications:
      - standard: "ISO 27001"
        expires_at: "2027-06-30"
      - standard: "SOC 2 Type II"
        expires_at: "2026-12-31"

  # Sovereignty — consumed directly by the Governance Matrix
  sovereignty:
    zone_handle: "zones/eu-west-sovereign"
    data_residency: EU
    jurisdiction_codes: [DE]
    cross_border_permitted: false

  # Placement eligibility — which resource types may be placed here
  placement:
    eligible_resource_types: []         # empty = all resource types eligible
    ineligible_resource_types: []       # explicit exclusions
    max_data_classification: restricted # highest data classification accepted
    requires_accreditations: []         # accreditations providers must hold to serve this DC

  concern_tags: [location, data-center, frankfurt, eu-west, tier-3]
```

---

## 6. Location Hierarchy Assembly

When a consumer selects a location, DCM resolves the full ancestor chain and assembles
all location layers into the request payload in hierarchy order (lowest precedence first —
Country → Region → Zone → Site → Data Center → Hall → Cage → Rack).

**Example: Consumer selects Rack FRA-DC1-A-12-03**

```
Layer resolution (Core Layer phase of assembly):

  1. Country layer: locations/country/de
     Injects: iso_3166_1_alpha2=DE, data_sovereignty_jurisdiction=EU/GDPR,
              regulatory_frameworks=[GDPR, NIS2]

  2. Region layer: locations/region/eu-west
     Injects: region_code=eu-west, primary_interconnect=DE-CIX,
              latency_profile.intra_region_ms=2

  3. Zone layer: locations/az/eu-west-1a
     Injects: zone_code=eu-west-1a, isolation_boundary=full,
              target_rpo_minutes=15, target_rto_minutes=60

  4. Site layer: locations/site/fra-campus-01
     Injects: site_code=FRA-CAMPUS-01, physical_address={...},
              security_tier=2

  5. Data Center layer: locations/dc/fra-dc1
     Injects: dc_code=FRA-DC1, tier_classification=tier_3,
              network_uplinks=[...], certifications=[...]

  6. Hall layer: locations/hall/fra-dc1-hall-a
     Injects: hall_code=FRA-DC1-HALL-A, cooling_type=liquid,
              network_segment=vlan-100

  7. Rack layer: locations/rack/fra-dc1-a-12-03
     Injects: rack_code=FRA-DC1-A-12-03, rack_units=42,
              max_power_kw=20, network_top_of_rack={...}

Assembled location context in payload:
  location.country_code: DE
  location.jurisdiction: EU/GDPR
  location.regulatory_frameworks: [GDPR, NIS2]
  location.region_code: eu-west
  location.zone_code: eu-west-1a
  location.dc_code: FRA-DC1
  location.rack_code: FRA-DC1-A-12-03
  location.sovereignty_zone: eu-west-sovereign
  location.max_data_classification: restricted
  location.certifications: [ISO 27001, SOC 2 Type II]
  ... (all ancestor fields available to policies and providers)
```

Higher-precedence location layers override lower-precedence ones for the same field.
A Rack layer declaring `max_data_classification: internal` overrides the DC layer's
`restricted` — the most specific declaration wins.

---

## 7. Priority Band Allocation

Location layers occupy a dedicated band in the Core Layer priority space (doc 03).

```
Priority bands for Core Location Layers:

  100.xx.0 — Country layers
  200.xx.0 — Region layers
  300.xx.0 — Zone / Availability Zone layers
  400.xx.0 — Site / Campus layers
  500.xx.0 — Data Center layers
  600.xx.0 — Hall / Pod / Row layers
  700.xx.0 — Cage / Enclosure layers
  800.xx.0 — Rack layers
  900.xx.0 — Unit / Slot layers (provider-managed)

  xx = sequence number within the level (01, 02, ... 99)
  (Allows up to 99 instances at each level before a major priority change)
```

This ensures Country always has lower precedence than Region, which always has lower
precedence than Zone, etc. The specific location is always the most specific (highest
precedence) contributor to location data.

---

## 8. Consumer Selection Model

Consumers do not interact with location layers directly via a `/locations` endpoint.
Location selection is part of the **catalog item field schema**. When a consumer calls
`GET /api/v1/catalog/{catalog_item_uuid}`, the `location` field constraint of type
`layer_reference` includes the `allowed_values` list — the set of active location
Data Center layer instances the consumer is entitled to and that this resource type
is eligible for.

Each entry in `allowed_values` carries the display data the GUI needs (name, code,
zone, sovereignty, certifications, capacity status) and the layer UUID the consumer
submits as the field value.

**Consumer request:**

```json
POST /api/v1/requests
{
  "catalog_item_uuid": "<uuid>",
  "fields": {
    "location": "layer-uuid-fra-dc1",     // DC-level layer UUID
    "os_image": "layer-uuid-rhel-9-4",
    "cpu_count": 4
  }
}
```

If the consumer wants to express location at a coarser level (Zone or Region rather
than a specific DC), they submit the layer UUID of that level. DCM's Placement Engine
refines downward to a specific DC during placement. The Placement Engine then assembles
the full ancestor chain (Country → Region → Zone → Site → DC) into the payload.

**Filtering allowed_values:**

The catalog item declaration controls which location layer instances appear in
`allowed_values` via the `filter` clause on the `layer_reference` constraint:

```yaml
# In the catalog item's field constraint declaration:
constraint:
  type: layer_reference
  layer_type: location.data_center
  filter:
    tags: [production]              # only production DCs
    min_tier: tier_3               # only Tier 3 and above
    required_certifications: [iso_27001]   # only certified DCs
```

This means the Platform Team controls which DCs are eligible for each catalog item
by configuring the filter — without changing the location layers themselves.

---


## 9. Authority and Ownership Model

Each location type has a designated owning authority. The authority model determines:
- Who can create, modify, and retire location layer instances
- Who is notified when location layer data changes
- Who approves capacity changes

```yaml
location_authority_model:

  # Standard defaults — configurable per deployment
  country:
    creating_authority: Platform Governance Team
    approval_required: true
    approval_tier: platform_admin

  region:
    creating_authority: Network Operations
    approval_required: true
    approval_tier: platform_admin

  zone:
    creating_authority: Data Center Operations
    approval_required: true
    approval_tier: platform_admin

  site:
    creating_authority: Facilities Management
    approval_required: true
    approval_tier: team_lead

  data_center:
    creating_authority: Data Center Operations
    approval_required: true
    approval_tier: team_lead

  hall:
    creating_authority: Data Center Operations
    approval_required: false
    approval_tier: operator

  cage:
    creating_authority: Data Center Operations
    approval_required: false
    approval_tier: operator

  rack:
    creating_authority: Data Center Operations
    approval_required: false
    approval_tier: operator
```

All location layer changes follow the standard GitOps workflow — changes are submitted
as PRs, reviewed by the owning authority, and merged. DCM picks up changes on the next
policy/layer sync cycle. Location layers are **immutable once active** — a new version
is created for any change, preserving the full history of location data over time.

---

## 10. Custom Location Types

Organizations may define custom location types to extend the standard hierarchy. Custom
types are registered in the Location Type Registry alongside standard types.

**Example: Navy deployment with Fleet and Ship levels**

```yaml
custom_location_type:
  type_name: fleet
  code: FLEET
  display_name: "Fleet"
  level: 3.5            # inserted between Zone (3) and Site (4)
  parent_type: zone
  child_type: ship       # references the custom 'ship' type below

  standard_fields:
    fleet_name:      { type: string, required: true }
    fleet_code:      { type: string, required: true }
    command_node:    { type: string, required: false }
    operating_area:  { type: string, required: false }

  owning_authority: Fleet Operations Command

---
custom_location_type:
  type_name: ship
  code: SHIP
  display_name: "Ship / Vessel"
  level: 4.5            # inserted between Site (4) and Data Center (5)
  parent_type: fleet
  child_type: data_center

  standard_fields:
    vessel_name:     { type: string, required: true }
    hull_number:     { type: string, required: true }
    vessel_class:    { type: string, required: false }
    home_port:       { type: string, required: false }
    current_location_lat:  { type: number, required: false }
    current_location_lon:  { type: number, required: false }
    connectivity_profile:
      type: string
      enum: [satcom, fiber_pier, disconnected]
      required: true

  owning_authority: Fleet Data Center Operations
```

Custom type instances are created and managed exactly like standard type instances —
GitOps PRs, owned by the designated authority, versioned and immutable.

---

## 11. Relationship to Placement Engine

The Placement Engine (doc 25, Section 4) uses location topology data in Steps 1 and 3
of the six-step placement algorithm:

**Step 1 — Sovereignty Pre-Filter:**
Location layers carry `sovereignty.zone_handle`. The Placement Engine eliminates any
provider whose declared sovereignty zones do not include the zone associated with
the requested location.

**Step 3 — Capability Filter:**
Location layers carry `placement.max_data_classification` and
`placement.requires_accreditations`. Providers that cannot satisfy these
location-level constraints are eliminated, even if they satisfy the global
accreditation requirements.

**Step 6 — Tie-breaking:**
When multiple providers qualify, location-level `priority` declarations can be used
as a tie-breaking preference (e.g., "prefer providers in the same DC over providers
in a different DC in the same zone").

Location layers also populate `location.*` fields in the assembled payload, which
Placement policies (doc B) use in their constraint expressions:

```rego
# Example: Placement policy for PHI data
placement if {
    input.payload.location.jurisdiction == "EU/GDPR"
    input.payload.location.max_data_classification == "restricted"
    "hipaa_baa" in input.payload.location.required_accreditations
}
```

---

## 12. Location Layer Lifecycle

Location layers follow the standard layer lifecycle (doc 03):

```
developing → proposed → active → deprecated → retired
```

**Special considerations for location layers:**

**Decommissioning a location:** When a Data Center is being decommissioned, its location
layer transitions to `deprecated`. During the deprecation window, the Placement Engine
stops routing new requests to providers in that DC. Existing resources receive a
`location.decommission_warning` notification. The layer transitions to `retired` when
all resources have been migrated.

**Location data changes:** When a DC gets a new network uplink or achieves a new
certification, a new version of the location layer is published (minor version bump).
The Requested State for all existing resources in that DC is not retroactively updated —
provenance is preserved. Future requests and re-realizations will pick up the new data.

**Capacity changes:** Rack-level `rack_units_available` is a mutable field — it is
updated by Data Center Operations as capacity changes without a new version. All other
location fields require a new version to change.

---

## 13. System Policies

| Policy | Rule |
|--------|------|
| `LOC-001` | Every resource entity must have a resolved `location_uuid` at the DC level or below. Requests without a resolvable location are rejected at validation time. |
| `LOC-002` | Location layers are Core Layers. They must not contain service-specific or provider-specific data. Location layers that include resource-type-scoped fields are invalid. |
| `LOC-003` | The location hierarchy must be acyclic. A location node cannot be its own ancestor. DCM validates acyclicity at layer submission time. |
| `LOC-004` | Location layer handles follow the pattern `locations/{type}/{code}`. Any location layer with a non-conforming handle is rejected at registration. |
| `LOC-005` | When a consumer selects a location at a level above DC (e.g., Zone), the Placement Engine must resolve to a specific DC. A request may not remain at an abstract location level after dispatch. |
| `LOC-006` | `max_data_classification` declared by a location layer is an upper bound. A request carrying data classified above the location's maximum is rejected by the Placement Engine's capability filter before provider contact. |
| `LOC-007` | Location layer changes (new versions) are propagated to the Location Type Registry and the Service Catalog location list within the next sync cycle. Consumers see updated location data on next catalog query. |
| `LOC-008` | Custom location types must declare their level as a decimal between the two standard levels they insert between. Level values must be unique across all registered types (standard and custom). |
| `LOC-009` | All location layers must declare a `sovereignty.zone_handle` or explicitly declare `sovereignty: not_applicable`. A location layer with no sovereignty declaration is invalid for `standard` and above profiles. |

---

*Document maintained by the DCM Project. For questions or contributions see [GitHub](https://github.com/dcm-project).*
