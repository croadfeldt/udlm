# UDLM Common Elements — canonical shared shapes & the consistency sweep

**Status:** 🟡 Working — referenced by SPEC-DESIGN-REQUIREMENTS §24–25
**Purpose:** Recurring concepts (CPU/memory, capacity, CIDR, references, quantities, time, status) get
**one** canonical shape, reused across resource types so element names/units/structure stay consistent.
A type that needs a shared concept references the canonical shape here rather than inventing its own.

## 1. Conventions (the rules, restated)

- **Field names:** `snake_case` (canonical data model + AEP-conformant; `guest_os`, `node_pools`, `ip_address`, `api_url`) — naming-conventions.md §4.
- **Type names:** `Category.Type`, vendor-neutral (SPEC-DESIGN-REQUIREMENTS §6).
- **Quantities:** an explicit unit in the value, never a bare number whose unit is implied by the field
  name (so memory is `"16GB"`, not `memoryGib: 16`). One `Quantity` pattern, registry-wide.
- **Time:** RFC 3339 / ISO 8601 strings.
- **Enums:** the canonical token set (below) — no per-type synonyms.

## 2. Canonical common elements

> **Machine source:** these shapes are defined as JSON-Schema `$defs` in
> [`registry/common-elements.schema.json`](common-elements.schema.json) — the normative, referenceable
> version. A type `$ref`s a shape (`common-elements.schema.json#/$defs/<Name>`) rather than reinventing
> it; this section is the prose companion (the §3 normalization plan's step 1 is now done).

### 2.1 `Quantity`
A magnitude + explicit unit as one string. Pattern `^[0-9]+(\.[0-9]+)?(m|[KMGTPE]i?B?)?$` — the
Kubernetes `resource.Quantity` form: decimal SI (`K/M/G/T/P/E`), binary (`Ki/Mi/Gi/Ti/Pi/Ei`), optional
trailing `B` (`MB`/`GiB`), or milli (`m`). Covers every existing type's memory/storage/capacity usage.
Use for memory, storage, bandwidth, power (`"650W"`), etc.

### 2.2 `ComputeResources`  *(the keystone — currently divergent, see §3)*
```json
{ "instance_size": "medium",          // OR provider-neutral size class (see below)
  "cpu":    { "count": 8 },
  "memory": { "size": "32GB" } }      // Quantity
```
Reused by anything that sizes compute: `Compute.VirtualMachine`, a `Compute.Cluster` node pool, a
`Data.Database` instance. `vcpu`/`cores`/`memory_gib` are **non-canonical synonyms** — normalize to
`cpu.count` + `memory.size`.

**`instance_size` — sizing by class (shared vocabulary, provider-mapped).** Any resource type that sizes
compute MAY carry an `instance_size` string — a **provider-neutral size class** (e.g. `small|medium|large|xlarge`,
an ordinal scale) — *in place of, or alongside,* explicit `cpu`/`memory`. Two halves, and the split is the
point:
- **UDLM owns the conformity.** `instance_size` is a **shared, comparable vocabulary**: `medium` must mean
  something *comparable* across adjacent compatible providers — the classes are ordinally ordered (a portable
  "roughly this big"), so consumer intent is portable and a workload can move between compatible providers
  without re-sizing. This is UDLM providing *conformity between providers*, not a free string.
- **The provider owns the concrete mapping.** *How* `medium` resolves to cores/RAM, or to a `db.r5.large`, is
  the **provider's** to define at naturalization (DCM ADR-023) — UDLM does not fix the resource math.

So UDLM carries the comparable *shape* (the class vocabulary + its ordering); the provider fills the concrete
*definition*. This lets a type ship sized-by-class (the common shape for managed databases, VMs, node pools)
portably, without UDLM prescribing a fixed resource math.

### 2.3 `StorageCapacity` / disk
```json
{ "size": "200GB", "storage_class": "ceph-rbd" }   // size is a Quantity
```

### 2.4 Network
- `cidr`: a CIDR string (`"192.0.2.0/24"`).
- `ip_family`: enum `{ ipv4, ipv6, dual }` (canonicalizes `network.ip-address`'s `family`).
- `address`: an IP string (an `outputs` value, per existing `network.ip-address`).

### 2.5 `Reference`
A typed cross-entity pointer to another **resource** — `resource_type` + a **handle** (`target_handle`),
which is the authoring key. DCM resolves the handle and pins `target_uuid` at reserve (ADR-025, adopting
**AEP-124 resource association**); a `deferred` reference tolerates a not-yet-existing target
(claim-before-define). Distinct from a
`data_reference` (ADR-012), which points at immutable reference-**data** by uuid. The only cross-type
binding surface besides typed `outputs` (E2). Never a provider-native id.

### 2.6 `Condition` (status)  *(adopt OSAC/K8s vocabulary)*
```json
{ "type": "Ready", "status": "True|False|Unknown",
  "last_transition_time": "<rfc3339>", "reason": "...", "message": "..." }
```
`status[].conditions[]` is the canonical realized/discovered signal across all types
(see `registry/resource-type-data-sources.md` §3 — adopt the OSAC envelope).

### 2.7 `Timestamp`
RFC 3339 string. Standard realized fields: `create_time`, `update_time`, `last_transition_time`.

## 3. Consistency sweep — current registry (2026-06-26)

How the existing types express shared concepts today, and the drift to normalize:

| Type | compute sizing | naming notes |
|---|---|---|
| `Compute.VirtualMachine` | `vcpu` + `memory.size` (Quantity) + `disks[]` | `vcpu` ≠ canonical `cpu.count` |
| `Compute.Cluster` | `node_pools[]` (each carries its own cpu/memory) | node-pool sizing not a shared shape |
| `Data.Database` | `resources` block | a *third* spelling of cpu/memory |
| `Network.IPAddress` | — | `family` ≠ canonical `ip_family` |

**Findings:** CPU/memory is expressed **three different ways** (`vcpu`/`memory`, `node_pools.*`,
`resources`); no shared `ComputeResources`. `family` vs the canonical `ip_family`. Outputs are already
consistently `snake_case` (`ip_address`/`api_url`/`console_url`/`connection_string`) — good.

**Normalization plan (additive, MINOR bumps; no breaking renames until a MAJOR):**
1. Define `ComputeResources` + `Quantity` + `ip_family` here (this doc) and as `$defs` the type specs `$ref`.
2. New types (`Compute.BareMetalInstance`, `Storage.CephCluster`, …) use the canonical shapes from day one.
3. Existing types add the canonical shape alongside the legacy field (deprecate the synonym), converging at the next MAJOR.

## 4. New types — apply the sweep up front

The infrastructure types in `resource-type-data-sources.md` MUST use these canonical elements:
`BareMetalInstance` discovered inventory → `ComputeResources` + `Quantity` (RAM) + `StorageCapacity`
(disks); `CephCluster` capacity → `Quantity`; `AddressService`/`Gateway` → `cidr`/`ip_family`; every
type's status → `Condition[]`. Vendor-exclusive elements (BMC-specific extensions, vendor SNMP MIBs) stay out of the portable
spec (SPEC-DESIGN-REQUIREMENTS §17) and live only in the extension surface.

## 5. Component granularity — data element *and* entity (both)

A physical component — a RAM DIMM, a disk, a NIC, a GPU, a CPU — can be modeled two ways, and UDLM
supports **both at once** (SPEC-DESIGN-REQUIREMENTS §26):

- **Data element (always present).** The containing resource carries the **rollup** (`memory.size:
  "64GB"`, `cpu.count: 16`) and MAY carry a structured inline inventory (`memory.modules[]`, `disks[]`).
  A consumer that only needs totals reads these; the **portable contract never requires** the component
  breakout.
- **First-class entity (optional).** A `Hardware.NetworkInterface` resource `contained_by` the parent (the one component UDLM keeps — it is *configured*, bond/bridge). Component-level memory/CPU/disk/GPU are **out of scope** (ADR-013 — DCM is not a hardware system-of-record); host capacity lives on the Compute host. Whether these exist is governed
  by **`composition_visibility`** (`opaque|transparent|selective`, `entities/service-dependencies.md`
  §11d): `opaque` → rollup only; `transparent` → every component an entity; `selective` → the org
  picks which.

**The relationship (the keystone):** where a component *is* a kept entity, it is `contained_by` the
parent and reconciles against the parent's rollup. Post-ADR-013 the only such component is
`Hardware.NetworkInterface` (DCM configures it — bond/bridge); a host's `nics[]` rollup and its
`Hardware.NetworkInterface` entities describe the same interfaces, and a mismatch is **drift** —
surfaced with provenance, never silently reconciled away. This is the same `transparent` composition
that registers sub-resources as DCM entities (service-dependencies §11d), applied below the device
boundary. For memory/CPU/disk/GPU there is **no component entity** to reconcile against: capacity is a
rollup *attribute* of the Compute host (`memory.size: "64GB"`, `cpu.count: 16`), full stop — the sum is
never re-derived from parts because the parts are out of scope (ADR-013).

**Why the rollup is always present** — it lets a homelab and an enterprise alike declare a host with
just its aggregate capacity, which is all placement needs. If UDLM ever needs to asset-track every
DIMM/GPU as a lifecycle entity, that is the **deferred discovery-archetype** path (ADR-013 — a
discovered-only asset outside the request catalog, or an external DCIM information-provider), *not* a
`provisioning` component type. The rollup still matches the adopted standards: Redfish exposes
`ComputerSystem.MemorySummary.TotalSystemMemoryGiB` and Metal3 `status.hardware.ramMebibytes`; the
per-DIMM `/Memory/<id>` resources those standards also expose stay on the discovery/DCIM side of that
boundary.

### 5a. Identity — distinguishing instances of the same type (SPEC-DESIGN-REQUIREMENTS §27)

Two identical 32 GB DIMMs, eight same-model drives — all the same type, size, often the same use. To
keep them individually addressable, every component (whether a `Hardware.*` entity or an inline
`modules[]`/`disks[]` element) carries the canonical **`Identity`** block:

```yaml
Identity:
  location:      "P1-DIMMA1"        # physical position WITHIN the parent — unique there, stable across
                                    # reboots (DIMM slot, drive bay "Bay 7", PCIe slot). Primary key.
  serial_number:  "S3F2NX0M..."      # globally unique hardware serial — survives a move to another parent
  wwn:           "0x5000c500..."    # storage-device World-Wide Name (drives); alt global key to serial
  asset_tag:     "RF-DIMM-0042"     # OPTIONAL org-assigned asset tag (renamed from assetTag in the snake_case reversal)
  model:         "M393A4K40DB3-CWE" # type identity (part number) — equal across identical units
  role:          "system"           # OPTIONAL semantic usage — distinguishes same-model by PURPOSE
                                    # (drive: boot|data|ceph-osd|cache; memory: system|persistent)
```

**Discriminator precedence:** `location` (always unique within a parent) → `serial_number`/`wwn`
(globally unique, identity-follows-the-part) → `role`/`usage` (semantic). The component **entity's own
UUID** is its UDLM identity; the `Identity` block is what **binds that UUID to one physical instance** and
survives reseat (same serial, new slot) or repurpose (same serial, new role). This makes both "**same
type, different unit**" (two 32 GB DIMMs → distinct `location`/`serial_number`) and "**same use,
different serial**" (two `ceph-osd` drives → same `role`, distinct `serial_number`/`wwn`) first-class.
Adopts Redfish (`Memory.SerialNumber`+`DeviceLocator`, `Drive.SerialNumber`+`WWN`+`PhysicalLocation`)
and Metal3 (`storage[].{name,serial_number,wwn,model}`, `nics[].mac`) — vocabulary by reference.

## 6. `lifecycle_state` — allocation / availability (SPEC-DESIGN-REQUIREMENTS §28)

A resource that exists physically but is not yet allocated (a racked-but-unassigned server, a spare
drive, a brownfield import) is **raw** — tracked with Discovered state and **no Intent**. The canonical
`lifecycle_state` marks where it sits:

```yaml
lifecycle_state: available   # available | allocated | retired   (extensible per type)
```

`available` = inventoried, unallocated, tracked. `allocated` = an Intent has been **adopted** onto it
(it entered the managed lifecycle, UUID preserved). `retired` = decommissioned but retained for history.
Adopts Metal3 `BareMetalHost.status.provisioning.state` (`available` is its canonical
inspected-but-unprovisioned state). See `foundations/four-states.md` §2.4 (raw / discovered-first entry)
and SPEC-DESIGN-REQUIREMENTS §28 (ingest-raw-then-adopt, UUID-preserving).

## 7. `device_class` — device realization (Hardware.* types)

A `Hardware.*` component is the **device/component layer** and may be physical, virtualized, passed
through to a guest, a slice carved from a physical parent, or a composite built from several interfaces.
The canonical `device_class` discriminator (with `partition_mechanism`, `aggregation`/`bridge`, and a
`parent_device` **or** `lower_layer` reference) keeps all of these expressible in the **same** five
`Hardware.*` types, so the whole device tree — physical → slices, and physical → aggregate → bridge →
sub-interface — is traversable.

```yaml
device_class: physical          # physical | virtual | passthrough | partition | aggregate | bridge
partition_mechanism: sr-iov     # OPTIONAL; only when device_class=partition: sr-iov | mediated | mig |
                               # vlan | macvlan | …  (the slicing mechanism; extensible)
# parent_device: a `references` relationship to the ONE parent Hardware.* entity (1→N) —
#   REQUIRED when device_class ∈ {passthrough, partition}.
# lower_layer:   a `references` relationship to the MANY member Hardware.* entities (N→1) —
#   REQUIRED when device_class ∈ {aggregate, bridge}. RFC 8343 lower-layer-if.
```

| device_class | meaning | example | member edge |
|---|---|---|---|
| `physical` | a whole dedicated device | a real DIMM / GPU / NIC PF / disk | — |
| `virtual` | fully synthetic, no hardware parent | virtio disk, emulated NIC, veth pair | — |
| `passthrough` | a whole physical device assigned to a guest | VFIO whole-GPU / whole-NIC | `parent_device` → the physical device |
| `partition` | a **slice of one** physical parent (1→N) | **SR-IOV VF, vGPU/MIG, VLAN/macvlan sub-interface** | `parent_device` → the physical parent |
| `aggregate` | a **composite of many** interfaces (N→1) | **bond / LACP LAG** (802.1AX) | `lower_layer` → the member NICs |
| `bridge` | a **software L2 bridge over many** ports (N→1) | **Linux bridge / OVS bridge** (802.1Q) | `lower_layer` → the bridged ports |

The device-partition mechanism applies to interfaces (GPU partitioning is deferred — GPU is a host capability, ADR-013): an **SR-IOV VF / vETH** =
`Hardware.NetworkInterface` `device_class: partition`, `partition_mechanism: sr-iov` (or `vlan`/`macvlan`),
`parent_device` → the physical NIC. A **bond** = `Hardware.NetworkInterface` `device_class: aggregate`,
`aggregation.mode: 802.3ad`, `lower_layer` → its member NICs; a **bridge** =
`Hardware.NetworkInterface` `device_class: bridge`, `lower_layer` → the bond (or NICs) it bridges. The
host L2 stack is thus one chain — `eno1`+`eno2` (physical) → `bond0` (aggregate) → `br0` (bridge) →
tenant sub-interfaces (partition) — and `parent_device` (1→N) vs `lower_layer` (N→1) are the two
**methods that relate a derived interface to its foundational components**. Both edges are
self-referential `references` relationships (`Hardware.X → Hardware.X`); the §27 `Identity` block still
distinguishes instances (a VF/vGPU keyed by `location`/index even with no hardware serial). Grounded in
SR-IOV, the Linux mdev/vGPU + NVIDIA MIG frameworks, IEEE 802.1AX (aggregation), IEEE 802.1Q (bridging),
and RFC 8343 interface stacking; mirrors Redfish `NetworkAdapter`→`NetworkDeviceFunction` /
`PCIeDevice`→`PCIeFunction`. `device_class` is a UDLM-defined cross-cutting classifier (no single
standard owns it).

### 7a. `connects_to` — physical adjacency (the third traversal method)

§7's `parent_device` (composition **down**, 1→N) and `lower_layer` (composition **up**, N→1) relate an
interface to its foundational components *within* one device. **`connects_to`** (renamed from `connected_to` when relation names were adopted from standards, §9) is the cross-device
edge: a physical interface's link to its **peer termination point** — host NIC ↔ switch port, switch ↔
switch uplink. A self-referential `references` relationship (`Hardware.NetworkInterface →
Hardware.NetworkInterface`, 0..1 per physical port), symmetric, declared once from either end.

```yaml
# host side                              # switch side
- id: host01-eno2                        - id: sw-leaf01-port14
  type: Hardware.NetworkInterface          type: Hardware.NetworkInterface
  contained_by: host01                     contained_by: sw-leaf01           # a Network.Switch
  connects_to: sw-leaf01-port14           attrs: { identity: { location: "Port 14" } }
```

Together the three make the estate graph traversable end-to-end from ANY resource:
`IP → bridge → (lower_layer) bond → (lower_layer) NIC → (connects_to) switch port → (contained_by)
switch → (depends_on) power feed` — and the reverse walk answers "what goes dark if this feed drops."

**Discovery & drift:** grounded in **IEEE 802.1AB (LLDP)** — the Chassis ID + Port ID TLVs name the peer,
so `connects_to` enters as **Discovered** state from an LLDP probe (`lldpcli show neighbors`); a mismatch
between declared cabling and the observed neighbor is **drift** (OBS-001), never silently merged.
**RFC 8345** (ietf-network-topology) models the same thing as a first-class *link* between two
*termination-points*; UDLM keeps it as a reference for minimal surface area — promote to a link entity
only if links ever need their own attributes (cable id, patch panel, medium).

## 8. Timestamps, notes, and audit-grade recording (normative)

Provenance is only actionable if its times and notes are. These rules apply to **every** time
field and note in the registry (type specs) and in instance records (realized-entity), and are
enforced by pattern in both schemas.

### 8.1 Timestamps

- **Format:** RFC 3339 (the internet profile of ISO 8601), **normalized to UTC** with the `Z`
  designator, seconds precision minimum: `2026-07-05T21:18:04Z`. Local offsets, date-only
  values, and zone-less times are non-conformant — the schemas reject them.
- **Source of time (`time_source`):** a timestamp without clock attribution is a claim, not
  evidence. State snapshots carry `time_source` naming the producing clock — host + sync
  discipline (e.g. `host01 chrony, stratum 2, NTP-traceable upstream`) — or, for a backfilled
  instant, the auditable carrier it came from (e.g. `git commit <sha> committer clock,
  NTP-synced workstation`).
- **No fabricated precision:** never widen a calendar-precision claim into an invented instant.
  Backfill only from an auditable carrier (git commit instants, log lines, NTP-disciplined
  capture at probe time) and say so in `time_source`.
- **Alignment:** RFC 9562 v7 UUIDs (identifier-scheme §2.1, declared time-ordered fields only)
  draw on the same clock discipline; a v7 field and its record's timestamps must not come from
  different unsynchronized clocks.

### 8.2 Notes are auditable records

`metadata.notes` is **attributed, timestamped entries** (`{at, author, text}`), never an
anonymous mutable blob. `author` is a person, an agent+session, or a process uuid (a Process
Resource that writes a note cites itself — the §6.4 obligation applies to notes too). Editing
history rides the store's carrier (git or the four-state store).

### 8.3 Field-level provenance is profile-implemented, never profile-optional

E4 field-level provenance and G3 (audit consumes the same record) hold in **every** profile —
foundations.md: a `minimal` profile implements the architecture with minimal operational
overhead; it does not disable it. What varies by profile is the **implementation**:

| Profile | Conforming provenance implementation |
|---|---|
| `minimal` / `dev` | **Derivable-carrier provenance**: records live in a git-carried store; field-level provenance entries are *materialized on demand* from the carrier's history by tooling, with the documented mapping — `source: {kind: actor, id: <commit author>}`, `timestamp` = committer instant normalized to UTC, previous value from the parent revision. The carrier must be able to produce a conforming `provenance` object for any record at any time; CI verifies derivability. |
| `standard` / `prod` | Materialized `provenance` written at assembly/realization time (DCM writes, UDLM carries). |
| `fsi` / `sovereign` | Materialized provenance **plus** the tamper-evident audit chain linkage (`audit.log_head`, AUD-001/002). |

A store that can neither carry nor derive field-level provenance for its records does not
conform in any profile.

## 9. Relation vocabulary — named, standards-adopted edge semantics (normative)

Edges carry two tiers of meaning, and each tier has one authoritative field:

- **`kind`** (universal, closed: `depends_on` | `contained_by` | `binds_to` | `references`) — the
  **dependency-graph tier**. Generic enough to apply to every resource type, specific enough to
  act on: ordering, traversal, DEP rules, and lifecycle projections consume ONLY kind + strength.
  Aligned with OASIS TOSCA root relationship types (`DependsOn`, `HostedOn`, `BindsTo`) and with
  ECMA-424 CycloneDX's minimal `dependsOn` graph.
- **`name`** (type layer) / **`relation`** (instance layer) — the **domain tier**. Each Resource
  Type declares its relationships with a machine-readable `name`; the type spec IS the relation
  registry for its instances (the RFC 8288 registered-vocabulary pattern, applied per type).
  Instance edges cite the declared name via `dependencies[].relation`.

| Rule | Statement |
|---|---|
| `REL-001` | An instance edge's `relation` MUST be a relationship `name` declared by the entity's pinned Resource Type. Undeclared relation strings are invalid. |
| `REL-002` | Relationship cardinalities declared by the type are enforceable on instances — a type-required relationship (cardinality `1..`) with no matching instance edge is a completeness failure. Conditional requirements (e.g. `lower_layer` required only for `device_class: aggregate\|bridge`) are enforced per the type's stated condition. |
| `REL-003` | A relation **refines** its declared kind and MUST NOT alter the kind's ordering semantics (the TOSCA derivation rule). A consumer that does not understand a relation falls back to kind behavior — the dependency graph is always a strict projection of the data. |
| `REL-004` | Relation names are **adopted, not invented**: where a standard names the concept, the relationship declares it in `adopted_from` (and the type's `adopts[]` carries the source + license verdict). Invented names are permitted only where no standard names the concept, and follow naming-conventions. |

**Adopted relation names (current):** `lower_layer`, `parent_device` (RFC 8343
`lower-layer-if`; parent_device is a declared 1→N refinement) · `connects_to` (OASIS TOSCA
`ConnectsTo`) · `attaches_to` (OASIS TOSCA `AttachesTo`) · `supporting_node` (RFC 8345
`supporting-node`).

**Prior art considered (2026-07-05):** OASIS TOSCA relationship types + derivation; IETF YANG
RFC 8343/8345; DMTF CIM associations / Redfish named `Links`; RFC 8288 / IANA link-relation
registry (mechanism adopted, web-document vocabulary rejected as poor domain fit); CNCF
Backstage catalog relations (paired vocabulary); ISO/IEC 5962 SPDX + ECMA-424 CycloneDX
(standardized dependency/relationship vocabularies); Google Zanzibar / SpiceDB (per-type
declared relations — the model behind Red Hat Project Kessel's relations-api); Kubernetes
ownerReferences + Service Binding for Kubernetes (grounds `binds_to`/`bound_field`). Red Hat
OSAC's fulfillment API references objects via named `*_ref` fields with no relation vocabulary
— UDLM's model is a superset; mapping at the Provider boundary is name↔ref-field.
