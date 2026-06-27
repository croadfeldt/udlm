# UDLM Common Elements — canonical shared shapes & the consistency sweep

**Status:** 🟡 Working — referenced by SPEC-DESIGN-REQUIREMENTS §24–25
**Purpose:** Recurring concepts (CPU/memory, capacity, CIDR, references, quantities, time, status) get
**one** canonical shape, reused across resource types so element names/units/structure stay consistent.
A type that needs a shared concept references the canonical shape here rather than inventing its own.

## 1. Conventions (the rules, restated)

- **Field names:** `camelCase` (matches the existing registry: `guestOS`, `nodePools`, `ipAddress`, `apiURL`).
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
{ "size": "200GB", "storageClass": "ceph-rbd" }   // size is a Quantity
```

### 2.4 Network
- `cidr`: a CIDR string (`"10.0.0.0/24"`).
- `ipFamily`: enum `{ ipv4, ipv6, dual }` (canonicalizes `network.ip-address`'s `family`).
- `address`: an IP string (an `outputs` value, per existing `network.ip-address`).

### 2.5 `Reference`
A typed cross-entity pointer — UUID + the target `resourceType` (`contracts/identifier-scheme.md`).
The only cross-type binding surface besides typed `outputs` (E2). Never a provider-native id.

### 2.6 `Condition` (status)  *(adopt OSAC/K8s vocabulary)*
```json
{ "type": "Ready", "status": "True|False|Unknown",
  "lastTransitionTime": "<rfc3339>", "reason": "...", "message": "..." }
```
`status[].conditions[]` is the canonical realized/discovered signal across all types
(see `registry/resource-type-data-sources.md` §3 — adopt the OSAC envelope).

### 2.7 `Timestamp`
RFC 3339 string. Standard realized fields: `createTime`, `updateTime`, `lastTransitionTime`.

## 3. Consistency sweep — current registry (2026-06-26)

How the existing types express shared concepts today, and the drift to normalize:

| Type | compute sizing | naming notes |
|---|---|---|
| `Compute.VirtualMachine` | `vcpu` + `memory.size` (Quantity) + `disks[]` | `vcpu` ≠ canonical `cpu.count` |
| `Compute.Cluster` | `nodePools[]` (each carries its own cpu/memory) | node-pool sizing not a shared shape |
| `Data.Database` | `resources` block | a *third* spelling of cpu/memory |
| `Network.IPAddress` | — | `family` ≠ canonical `ipFamily` |

**Findings:** CPU/memory is expressed **three different ways** (`vcpu`/`memory`, `nodePools.*`,
`resources`); no shared `ComputeResources`. `family` vs the canonical `ipFamily`. Outputs are already
consistently camelCase (`ipAddress`/`apiURL`/`consoleURL`/`connectionString`) — good.

**Normalization plan (additive, MINOR bumps; no breaking renames until a MAJOR):**
1. Define `ComputeResources` + `Quantity` + `ipFamily` here (this doc) and as `$defs` the type specs `$ref`.
2. New types (`Compute.BareMetalInstance`, `Storage.CephCluster`, …) use the canonical shapes from day one.
3. Existing types add the canonical shape alongside the legacy field (deprecate the synonym), converging at the next MAJOR.

## 4. New types — apply the sweep up front

The infrastructure types in `resource-type-data-sources.md` MUST use these canonical elements:
`BareMetalInstance` discovered inventory → `ComputeResources` + `Quantity` (RAM) + `StorageCapacity`
(disks); `CephCluster` capacity → `Quantity`; `AddressService`/`Gateway` → `cidr`/`ipFamily`; every
type's status → `Condition[]`. Vendor-exclusive elements (iDRAC, vendor-UPS SNMP) stay out of the portable
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
  serialNumber:  "S3F2NX0M..."      # globally unique hardware serial — survives a move to another parent
  wwn:           "0x5000c500..."    # storage-device World-Wide Name (drives); alt global key to serial
  assetTag:      "RF-DIMM-0042"     # OPTIONAL org-assigned asset tag
  model:         "M393A4K40DB3-CWE" # type identity (part number) — equal across identical units
  role:          "system"           # OPTIONAL semantic usage — distinguishes same-model by PURPOSE
                                    # (drive: boot|data|ceph-osd|cache; memory: system|persistent)
```

**Discriminator precedence:** `location` (always unique within a parent) → `serialNumber`/`wwn`
(globally unique, identity-follows-the-part) → `role`/`usage` (semantic). The component **entity's own
UUID** is its UDLM identity; the `Identity` block is what **binds that UUID to one physical instance** and
survives reseat (same serial, new slot) or repurpose (same serial, new role). This makes both "**same
type, different unit**" (two 32 GB DIMMs → distinct `location`/`serialNumber`) and "**same use,
different serial**" (two `ceph-osd` drives → same `role`, distinct `serialNumber`/`wwn`) first-class.
Adopts Redfish (`Memory.SerialNumber`+`DeviceLocator`, `Drive.SerialNumber`+`WWN`+`PhysicalLocation`)
and Metal3 (`storage[].{name,serialNumber,wwn,model}`, `nics[].mac`) — vocabulary by reference.

## 6. `lifecycleState` — allocation / availability (SPEC-DESIGN-REQUIREMENTS §28)

A resource that exists physically but is not yet allocated (a racked-but-unassigned server, a spare
drive, a brownfield import) is **raw** — tracked with Discovered state and **no Intent**. The canonical
`lifecycleState` marks where it sits:

```yaml
lifecycleState: available   # available | allocated | retired   (extensible per type)
```

`available` = inventoried, unallocated, tracked. `allocated` = an Intent has been **adopted** onto it
(it entered the managed lifecycle, UUID preserved). `retired` = decommissioned but retained for history.
Adopts Metal3 `BareMetalHost.status.provisioning.state` (`available` is its canonical
inspected-but-unprovisioned state). See `foundations/four-states.md` §2.4 (raw / discovered-first entry)
and SPEC-DESIGN-REQUIREMENTS §28 (ingest-raw-then-adopt, UUID-preserving).

## 7. `deviceClass` — device realization (Hardware.* types)

A `Hardware.*` component is the **device/component layer** and may be physical, virtualized, passed
through to a guest, or a slice carved from a physical parent. The canonical `deviceClass` discriminator
(with `partitionMechanism` and a `parentDevice` reference) keeps all of these expressible in the **same**
five `Hardware.*` types, so the device tree (physical → slices → guest assignment) is traversable.

```yaml
deviceClass: physical          # physical | virtual | passthrough | partition   (default physical)
partitionMechanism: sr-iov     # OPTIONAL; only when deviceClass=partition: sr-iov | mediated | mig |
                               # vlan | macvlan | …  (the slicing mechanism; extensible)
# parentDevice: expressed as a relationship (kind: references) to the parent Hardware.* entity —
# REQUIRED when deviceClass ∈ {passthrough, partition}.
```

| deviceClass | meaning | example | `parentDevice` |
|---|---|---|---|
| `physical` | a whole dedicated device | a real DIMM / GPU / NIC PF / disk | — |
| `virtual` | fully synthetic, no hardware parent | virtio disk, emulated NIC, veth pair | — |
| `passthrough` | a whole physical device assigned to a guest | VFIO whole-GPU / whole-NIC | the physical device |
| `partition` | a slice of a physical parent | **SR-IOV VF, vGPU/MIG, VLAN/macvlan sub-interface** | the physical parent |

So a **vGPU** = `Hardware.GraphicsProcessor` `deviceClass: partition`, `partitionMechanism: mediated`
(or `mig`), `parentDevice` → the physical `Hardware.GraphicsProcessor`; an **SR-IOV VF / vETH** =
`Hardware.NetworkInterface` `deviceClass: partition`, `partitionMechanism: sr-iov` (or `vlan`/`macvlan`),
`parentDevice` → the physical NIC. The `parentDevice` edge is a self-referential `references` relationship
(`Hardware.X → Hardware.X`); the §27 `Identity` block still distinguishes instances (a VF/vGPU keyed by
`location`/index even with no hardware serial). Grounded in SR-IOV, the Linux mdev/vGPU + NVIDIA MIG
frameworks, and 802.1Q; mirrors Redfish `NetworkAdapter`→`NetworkDeviceFunction` /
`PCIeDevice`→`PCIeFunction`. `deviceClass` is a UDLM-defined cross-cutting classifier (no single standard
owns it).
