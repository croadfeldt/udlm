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

### 2.1 `Quantity`
A magnitude + explicit unit as one string. Pattern `^[0-9]+(\.[0-9]+)?(m|M|G|T|P|Mi|Gi|Ti|MB|GB|TB)?$`
(aligns with the existing `compute.virtual-machine` `memory.size` and Kubernetes `resource.Quantity`).
Use for memory, storage, bandwidth, power (`"650W"`), etc.

### 2.2 `ComputeResources`  *(the keystone — currently divergent, see §3)*
```json
{ "cpu":    { "count": 8 },
  "memory": { "size": "32GB" } }      // Quantity
```
Reused by anything that sizes compute: `Compute.VirtualMachine`, a `Compute.Cluster` node pool, a
`Data.Database` instance. `vcpu`/`cores`/`memory_gib` are **non-canonical synonyms** — normalize to
`cpu.count` + `memory.size`.

### 2.3 `StorageCapacity` / disk
```json
{ "size": "200GB", "storage_class": "ceph-rbd" }   // size is a Quantity
```

### 2.4 Network
- `cidr`: a CIDR string (`"10.0.0.0/24"`).
- `ip_family`: enum `{ ipv4, ipv6, dual }` (canonicalizes `network.ip-address`'s `family`).
- `address`: an IP string (an `outputs` value, per existing `network.ip-address`).

### 2.5 `Reference`
A typed cross-entity pointer — UUID + the target `resource_type` (`contracts/identifier-scheme.md`).
The only cross-type binding surface besides typed `outputs` (E2). Never a provider-native id.

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
type's status → `Condition[]`. Vendor-exclusive elements (iDRAC, Liebert SNMP) stay out of the portable
spec (SPEC-DESIGN-REQUIREMENTS §17) and live only in the extension surface.

## 5. Component granularity — data element *and* entity (both)

A physical component — a RAM DIMM, a disk, a NIC, a GPU, a CPU — can be modeled two ways, and UDLM
supports **both at once** (SPEC-DESIGN-REQUIREMENTS §26):

- **Data element (always present).** The containing resource carries the **rollup** (`memory.size:
  "64GB"`, `cpu.count: 16`) and MAY carry a structured inline inventory (`memory.modules[]`, `disks[]`).
  A consumer that only needs totals reads these; the **portable contract never requires** the component
  breakout.
- **First-class entity (optional).** A `Hardware.*` resource — `Hardware.MemoryModule`,
  `Hardware.StorageDevice`, `Hardware.NetworkInterface`, `Hardware.GraphicsProcessor`,
  `Hardware.Processor` — `contained_by` the parent, for organizations that track components
  **independently** (serial, slot, firmware, RMA, lifecycle, warranty). Whether these exist is governed
  by **`composition_visibility`** (`opaque|transparent|selective`, `entities/service-dependencies.md`
  §11d): `opaque` → rollup only; `transparent` → every component an entity; `selective` → the org
  picks which.

**The relationship (the keystone):** when components are entities, the parent's rollup is the
**aggregate of its contained components** — `Compute.BareMetalInstance.memory.size = "64GB"` is the sum
of two `Hardware.MemoryModule` entities (32GB each), each `contained_by` the host. The rollup is the
authoritative realized value; the components reconcile against it, and a mismatch (parent reports 65GB,
modules sum to 64GB) is **drift** — surfaced with provenance, never silently summed away. This is the
same `transparent` composition that registers sub-resources as DCM entities (service-dependencies §11d),
applied below the device boundary.

**Why both** — it lets a homelab declare `BareMetalInstance` with just a rollup today, and an enterprise
asset-track every DIMM/GPU as a lifecycle entity tomorrow, **without changing the type** — only its
`composition_visibility`. It also matches the adopted standards: Redfish exposes
`ComputerSystem.MemorySummary.TotalSystemMemoryGiB` (rollup) **and** `/Memory/<id>` per-DIMM resources;
Metal3 exposes `status.hardware.ramMebibytes` (rollup) + `nics[]`/`storage[]` arrays. The `Hardware.*`
family is a registry addition tracked alongside the other new types.

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
  assetTag:      "RF-DIMM-0042"     # OPTIONAL org-assigned asset tag
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

So a **vGPU** = `Hardware.GraphicsProcessor` `device_class: partition`, `partition_mechanism: mediated`
(or `mig`), `parent_device` → the physical `Hardware.GraphicsProcessor`; an **SR-IOV VF / vETH** =
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

### 7a. `connected_to` — physical adjacency (the third traversal method)

§7's `parent_device` (composition **down**, 1→N) and `lower_layer` (composition **up**, N→1) relate an
interface to its foundational components *within* one device. **`connected_to`** is the cross-device
edge: a physical interface's link to its **peer termination point** — host NIC ↔ switch port, switch ↔
switch uplink. A self-referential `references` relationship (`Hardware.NetworkInterface →
Hardware.NetworkInterface`, 0..1 per physical port), symmetric, declared once from either end.

```yaml
# host side                              # switch side
- id: cartman-eno2                       - id: sw-usw-ent24-7d8f-port14
  type: Hardware.NetworkInterface          type: Hardware.NetworkInterface
  contained_by: cartman                    contained_by: sw-usw-ent24-7d8f   # a Network.Switch
  connected_to: sw-usw-ent24-7d8f-port14   attrs: { identity: { location: "Port 14" } }
```

Together the three make the estate graph traversable end-to-end from ANY resource:
`IP → bridge → (lower_layer) bond → (lower_layer) NIC → (connected_to) switch port → (contained_by)
switch → (depends_on) power feed` — and the reverse walk answers "what goes dark if this feed drops."

**Discovery & drift:** grounded in **IEEE 802.1AB (LLDP)** — the Chassis ID + Port ID TLVs name the peer,
so `connected_to` enters as **Discovered** state from an LLDP probe (`lldpcli show neighbors`); a mismatch
between declared cabling and the observed neighbor is **drift** (OBS-001), never silently merged.
**RFC 8345** (ietf-network-topology) models the same thing as a first-class *link* between two
*termination-points*; UDLM keeps it as a reference for minimal surface area — promote to a link entity
only if links ever need their own attributes (cable id, patch panel, medium).
