# UDLM — Layered Topology Contract

**Document Status:** ✅ Stable — UDLM substrate contract (abstract)
**Document Type:** Core Substrate Specification
**Related Documents:** [Data Layers and Assembly](../foundations/layering-and-versioning.md) | [Resource Type Hierarchy](../entities/resource-type-hierarchy.md) | [Governance Matrix](../governance/governance-matrix.md) | [Registry Governance](../governance/registry-governance.md)

---

## 0. Pattern Context

Location layers are one application of the **Reference Data Layer** pattern (see [layering-and-versioning.md](../foundations/layering-and-versioning.md)). The same pattern governs OS images, VM sizes, network zones, storage classes, and any other field where valid values are a governed, versioned, authority-owned set rather than a static list.

The substrate concepts in this document — layer instances as field constraint sources, hierarchy assembly, authority ownership, lifecycle governance — apply equally to all Reference Data Layer types. Location is specified in detail here because it has the richest internal hierarchy and the most complex assembly behaviour of all the standard reference data types.

The substrate is **abstract**: it defines that topology is layered and how layers compose, but it does NOT prescribe the specific layers a deployment uses. A consuming realization (e.g., DCM) declares its canonical layer hierarchy (DCM's canonical default is a 9-layer Country → Region → Zone → Site → Data Center → Hall → Cage → Rack → Unit scheme). A peer realization could pick a different scheme and still be UDLM-conformant.

---

## 1. Purpose

The substrate requires that every resource allocation be located *somewhere*, and that "somewhere" be a structured, versioned, authority-owned chain of layers — not a free-form string. The Layered Topology Contract specifies:

- *That* topology is composed of layers in a hierarchy
- *How* layers compose (parent/child relationships, ancestry assembly)
- *What* shape a layer instance has on the wire
- *How* layers are lifecycle-managed and extended

**What the substrate does NOT specify:**

- The specific layer types in the hierarchy (Country, Region, Zone, etc.) — these are a realization choice
- The number of layers in the hierarchy — realizations MAY have 3 layers or 12
- The specific fields each layer type carries — these are realization-declared via the schema-sharing protocol
- Placement engine algorithms — those are realization mechanics

---

## 2. Design Principles (Substrate)

**Configurable names, standard composition rules.** The names and types of topology nodes are realization-defined. The *composition rules* — that layers form a hierarchy, that each layer has at most one parent, that ancestry is assembled into the request payload — are substrate-normative.

**Hierarchical and composable.** Topology layers form a hierarchy from broadest to most specific. A resource allocated to a leaf layer inherits data from every ancestor layer — the full chain is assembled and merged in precedence order.

**Layer-first, not field-first.** Location is not a single flat string. It is a resolved chain of layers. Each layer in the chain carries structured data about that level. The assembled payload contains the full context of the selected location.

**Authority-owned.** Each layer type has a designated owning authority. The authority model itself is configurable; the substrate requires only that ownership be declared.

**Linked to the catalog.** Topology nodes are exposed to consumers through the catalog as selection dimensions. The substrate requires that selection happens via layer references, not free-form strings.

---

## 3. Layered-Topology Contract (Abstract)

The substrate requires the following:

### 3.1 Layers as Substrate Artifacts

Each topology layer instance is a first-class UDLM Data artifact:

- It has a UUID and a stable handle
- It is versioned (semver)
- It carries a `status` (`developing`, `proposed`, `active`, `deprecated`, `retired`)
- It is owned by a declared authority
- It is registered in a substrate-managed registry

### 3.2 Layers Have Typed Fields

Each layer type declares a schema of typed fields. Layer instances populate those fields. Field types follow the substrate's standard data-type vocabulary.

The specific set of layer types and their field schemas is declared by the consuming realization (or by the deploying organization) and exchanged via the [schema-sharing protocol](../contracts/schema-sharing.md). A federation peer can resolve a remote realization's layer types and field schemas by consulting the peer's published schema bundle.

### 3.3 Parent/Child Relationships

Layers form a hierarchy via `parent_handle` references:

- Each layer instance MAY declare a single `parent_handle`
- The hierarchy MUST be acyclic (the substrate validates this at registration)
- Each layer type MAY declare a `parent_type` constraint that restricts which parent types are valid

### 3.4 Ancestry Assembly Rules (Normative)

When a consumer selects a leaf layer, the realization MUST assemble the full ancestor chain into the request payload in hierarchy order. The substrate-required assembly rules are:

1. The leaf layer's ancestor chain is resolved by walking `parent_handle` references.
2. Each layer's data is merged into the payload in **precedence order**, lowest precedence first (root) to highest precedence last (leaf).
3. Higher-precedence layers override lower-precedence layers for the same field.
4. The assembled payload exposes the full ancestor chain so policies and providers can reason about every level of the hierarchy.

### 3.5 Custom/Extension Mechanism

The substrate requires that custom layer types can be added without modifying the substrate itself. Custom types follow the same registration and assembly contract as substrate-defined types:

- A custom layer type is registered with a unique `type_name`, a `parent_type` (or `null` for root-level custom types), and a field schema
- Layer instances of custom types are created and managed exactly like substrate-defined instances
- Custom types participate in ancestry assembly via the same rules
- Custom types are declared in the schema bundle so federation peers can resolve them

---

## 4. Location Layer Instance Format (Wire Contract)

Each location node is a first-class UDLM artifact. The wire shape is normative for all layer types:

```yaml
layer:
  artifact_metadata:
    uuid: <uuid>
    handle: "locations/<type>/<code>"     # standard handle pattern: locations/{type}/{code}
    version: "1.2.0"
    status: active
    owned_by:
      display_name: "Owning Authority"
      group_handle: "groups/<owning-group>"
      notification_endpoint: <endpoint>
    created_via: pr
    created_at: <ISO 8601>

  # Layer classification
  layer_type: core                        # always 'core' for location layers
  location_type: <type-name>              # realization-declared type identifier
  scope: type_agnostic                    # location layers apply to all resource types

  # Priority — location layers occupy a dedicated band in the priority space
  priority:
    value: "<priority-value>"             # specific bands realization-declared
    label: "core.location.<type>.<code>"
    category: core_location
    rationale: "<human-readable rationale>"

  # Hierarchy — parent location
  location_hierarchy:
    parent_handle: <parent-layer-handle | null>
    parent_type: <parent-type-name | null>
    ancestors:
      - handle: <ancestor-handle>
        type: <ancestor-type>
      # ... full ancestor chain

  # The location data — fields from the type definition
  data:
    # Fields declared in the layer-type schema; specific fields are realization-declared
    <field_name>: <value>

  # Sovereignty — consumed directly by the Governance Matrix
  sovereignty:
    zone_handle: <sovereignty-zone-handle>
    data_residency: <jurisdiction>
    jurisdiction_codes: [<ISO 3166-1 alpha-2 codes>]
    cross_border_permitted: <true|false>

  # Placement eligibility — which resource types may be placed here
  placement:
    eligible_resource_types: []         # empty = all resource types eligible
    ineligible_resource_types: []       # explicit exclusions
    max_data_classification: <classification>  # highest data classification accepted
    requires_accreditations: []         # accreditations providers must hold to serve this layer

  concern_tags: [location, ...]
```

---

## 5. Hierarchy Assembly Rules (Normative)

When a consumer selects a location, the realization MUST resolve the full ancestor chain and assemble all location layers into the request payload in hierarchy order (lowest precedence first — root → leaf).

**Substrate-required assembly behavior:**

1. **Walk the parent chain** from the selected leaf to the root, collecting all ancestor layer UUIDs.
2. **Order the layers** from lowest precedence (root) to highest precedence (leaf).
3. **Merge layer data** into the payload in that order; later (more-specific) layers override earlier (more-general) layers for the same field path.
4. **Expose the full chain** in the assembled payload so policies and providers can reason about every level.

**Illustrative example (the specific layer types are realization-declared; the substrate requires only that the assembly rules above are followed):**

```
Consumer selects: a leaf layer
  │
  ▼ Realization resolves ancestor chain: root → ... → leaf
  │
  ▼ Layer data merged into payload (lowest precedence first)
  │
  ▼ Assembled payload contains:
      - All ancestor field values
      - Most-specific value wins per field
      - Full ancestor chain available to policies and providers
```

Higher-precedence (more-specific) layers MUST override lower-precedence (more-general) layers for the same field. A leaf-layer declaration of `max_data_classification: internal` MUST override a parent-layer declaration of `restricted`.

---

## 6. Location Layer Lifecycle (Substrate Contract)

Location layers follow the standard substrate artifact lifecycle:

```
developing → proposed → active → deprecated → retired
```

**Substrate-required lifecycle behaviors:**

- **Decommissioning a layer:** When a layer is being decommissioned, its layer transitions to `deprecated`. During the deprecation window, the realization MUST stop routing new requests to entities placed at or below that layer. Existing resources MUST receive a `location.decommission_warning` notification. The layer transitions to `retired` when all resources have been migrated.

- **Layer data changes:** When layer data changes (a new property added, a certification achieved, etc.), a new version of the layer MUST be published. The Requested State for existing resources is NOT retroactively updated — provenance is preserved. Future requests and re-realizations pick up the new data.

- **Mutable vs immutable fields:** Layers MAY declare certain fields as mutable (capacity counters, availability flags) that can change without a new version. All other fields require a new version. Mutable-field declarations are part of the layer type schema.

---

## 7. Custom/Extension Mechanism (Contract)

The substrate requires that organizations can define custom layer types without modifying the substrate. Custom types are registered alongside substrate-defined types.

**Substrate-required properties of custom types:**

- A unique `type_name` within the deployment
- A `parent_type` (or `null` for root-level custom types) — must reference an existing layer type
- A `level` ordering value (substrate format permits decimal levels to allow insertion between existing levels)
- A field schema declared and exchanged via the schema-sharing protocol
- An owning authority declared at registration

Custom type instances are created and managed exactly like substrate-defined instances — same registration workflow, same authority ownership, same versioned/immutable model, same ancestry assembly rules.

```yaml
# Illustrative custom-type registration (the specific names are example-only)
custom_location_type:
  type_name: <custom-type-name>
  code: <SHORT_CODE>
  display_name: <"Display Name">
  level: 4.5                  # decimal between two standard levels
  parent_type: <parent-type-name>
  child_type: <child-type-name>
  standard_fields:
    <field_name>: { type: <type>, required: <bool> }
  owning_authority: <authority>
```

---

## 8. UDLM System Policies

| Policy | Rule |
|--------|------|
| `LOC-001` | Every resource entity MUST have a resolved leaf-layer UUID. Requests without a resolvable location are rejected at validation time. |
| `LOC-002` | Location layers are Core Layers. They MUST NOT contain service-specific or provider-specific data. Location layers that include resource-type-scoped fields are invalid. |
| `LOC-003` | The location hierarchy MUST be acyclic. A location node cannot be its own ancestor. The realization MUST validate acyclicity at layer submission time. |
| `LOC-004` | Location layer handles follow the pattern `locations/{type}/{code}`. Any location layer with a non-conforming handle MUST be rejected at registration. |
| `LOC-005` | When a consumer selects a location at a level above leaf, the realization MUST resolve to a specific leaf during placement. A request MAY NOT remain at an abstract location level after dispatch. |
| `LOC-006` | `max_data_classification` declared by a location layer is an upper bound. A request carrying data classified above the location's maximum MUST be rejected before provider contact. |
| `LOC-007` | Location layer changes (new versions) MUST be propagated to the consuming registries within the next sync cycle. Consumers see updated location data on next catalog query. |
| `LOC-008` | Custom location types MUST declare their level as a value (decimal allowed) that orders them within the existing hierarchy. Level values MUST be unique across all registered types (substrate-defined and custom). |
| `LOC-009` | All location layers MUST declare a `sovereignty.zone_handle` or explicitly declare `sovereignty: not_applicable`. A location layer with no sovereignty declaration is invalid for `standard` and above profiles. |

---

*UDLM substrate document. The specific layer hierarchy (e.g., DCM's canonical 9-layer Country → Region → Zone → Site → Data Center → Hall → Cage → Rack → Unit scheme), placement engine algorithms, priority band allocations, consumer selection mechanics, authority-and-ownership models, and capacity-tracking implementations are realization choices. The DCM realization's canonical hierarchy and operational mechanics live in the DCM realization's documentation.*
