# UDLM Registry — Naming Conventions

How we name resource types, fields, outputs, files, and instances, so the registry stays consistent and
predictable. These conventions are normative for new definitions; existing entries are brought into line
as they are revised. Referenced by `SPEC-DESIGN-REQUIREMENTS.md` §18 (Identity & naming) and enforced in
part by the meta-schema patterns (`resource-type-spec.schema.json`).

Guiding rule: **name to an existing standard before inventing.** Where an industry standard already
names a thing, adopt its vocabulary by reference (`adopts[]`, see SPEC-DESIGN §22–23) and let our name
mirror the concept; only coin a UDLM name where no standard fits.

## 1. Type names — `Category.Type`

- **Shape:** `Category.Type`, both segments **PascalCase** (`Compute.VirtualMachine`,
  `Network.IPAddress`). Knowledge-family types are single-segment (`Capability`). Enforced by the
  `resourceType` / `$id` patterns in the meta-schema.
- **Tiered namespace** (`governance/registry-governance.md` §2):
  | Tier | Namespace form | Example | Vendor names? |
  |---|---|---|---|
  | 1 — Core | `Category.Type` (vendor-neutral, from the canonical categories below) | `Storage.Cluster` | **never** |
  | 2 — Verified Community | `Vendor.Type` / `Technology.Type` | `VMware.NsxSegment`, `Ceph.Cluster` | yes (the tech *is* the namespace) |
  | 3 — Organization | `Org.Type` | `Acme.LegacyMainframeJob` | org-scoped |
- **No vendor/product names in Tier-1.** A concrete technology is a **provider/implementation of** a
  vendor-neutral type, declared on the *instance* (`provider: ceph`) and in `adopts[]` — not baked into
  the type name. (This is why `Storage.CephCluster` is wrong and `Storage.Cluster` is right.)
- **Singular nouns** for the thing itself (`MemoryModule`, not `MemoryModules`). Plurality lives in
  cardinality/relationships, not the name.
- **Acronyms:** keep well-known initialisms uppercase in the Type segment per established precedent
  (`Network.IPAddress`, `Network.DnsZone` — DNS as `Dns` follows the existing `IPAddress` PascalCase
  treatment of multi-letter tokens; prefer the form that reads as one PascalCase token).

## 2. Categories

The canonical categories (`entities/resource-type-hierarchy.md` §2.2). Resource categories:
`Compute`, `Network`, `Storage`, `Platform`, `Security`, `Observability`, `Data`. Information
categories: `Business`, `Identity`, `Compliance`, `Operations`.

**Adding a category** is permitted ("implementors may define additional categories following the
specification") but is a registry-precedent decision — do it only when **both**:
1. no existing category is a reasonable home, **and**
2. the new category maps to a recognized industry model (so we adopt, not invent).

New categories established by this work, each anchored to **DMTF Redfish** (datacenter hardware/DCIM):
- **`Hardware`** — the **device/component layer** below the device boundary (DIMM, disk, NIC, CPU, GPU),
  the first-class side of the §26 component model. **Not physical-only**: a `deviceClass` discriminator
  (`physical | virtual | passthrough | partition`, common-elements §7) lets the same types model a real
  DIMM, a guest's virtual disk, a passed-through GPU, or a vGPU/SR-IOV/VLAN **slice of a physical parent**
  (via a `parentDevice` reference). Anchored to Redfish `Memory`/`Processor`/`Drive`/`NetworkAdapter`
  (+ `NetworkDeviceFunction`/`PCIeFunction` for the derived cases). Distinct from `Compute` (the whole
  machine/instance).
- **`Facility`** — physical-datacenter resources (power, later rack/cooling). Anchored to Redfish DCIM
  `PowerDistribution`/`Circuit`/`PowerDomain` (+ NUT for UPS telemetry).

Resource vs Information: a **provisioned server is a Resource**; the **data it holds is Information**.
A directory *server* is `Security.DirectoryService` (a Resource); `Identity.*` (Person/Group/
ServiceAccount) is the Information data — don't conflate them.

## 3. Suite products = composites, not monolithic types

A product that bundles several capabilities is modeled as **realizing multiple types**, not one bespoke
type. Example: FreeIPA → `Security.DirectoryService` (LDAP+Kerberos, RFC 4511/4512/4120) **+**
`Network.DnsZone` **+** (future) `Security.CertificateAuthority`. This keeps each type portable and
reusable and avoids a `FreeIPA.Everything` corner.

## 3a. Asset vs. allocation vs. instance — don't mint redundant types

Before adding a type, check whether the concept is already expressed by an existing mechanism:
- **An instance of a type** is a **realized entity** (`registry/realized-entity.schema.json`,
  `registry/instances/`) — `stark` is an instance of `Compute.BareMetalHost`. Don't create a type to
  mean "an instance of X."
- **An allocation of a resource to a consumer** is the **Ownership/Allocation model**
  (`foundations/ownership-sharing-allocation.md`: whole-allocation / carved-allocation / shareable) —
  not a new type. "Allocate a host to a tenant" = whole-allocation of `Compute.BareMetalHost`, not a
  separate `BareMetalInstance` type.
- **A new type** is warranted only for a genuinely distinct *kind of thing* with its own contract.

So `Compute.BareMetalHost` is the **asset**; "instance" and "allocation" are existing mechanisms over it.

## 3b. Alternative names (AKA / cross-walk for compatibility)

To translate to/from other ecosystems, a type carries its alternative names with provenance — the
`{alternative name, spec, spec version}` shape:
- **Names from a standard the type formally adopts** → set **`standardName`** on that `adopts[]` entry
  (it already carries `standard` + `version` + `source` + `license`). E.g. `Compute.BareMetalHost`
  adopts Redfish (`standardName: ComputerSystem`, v2024.4) and Metal3 (`standardName: BareMetalHost`).
  This *is* the {name, spec, specVersion} cross-walk, co-located with provenance — no duplication.
- **Names NOT tied to an adopted standard** (vendor/colloquial AKAs) → the top-level **`aliases[]`**
  (`{name, standard?, standardVersion?, note?}`), e.g. AWS "Dedicated Host", OpenStack "Ironic node".

(The Knowledge-family **`Alias`** entity is a different tool — *taxonomy-term* normalization
"avoid → use instead", `entities/knowledge-family.md` §4.3 — not type cross-walks.)

## 4. Field, output, and enum names (inside `spec`/`outputs`)

- **Fields:** `camelCase` (`memorySize`, `vcpu`, `nodePools`) — SPEC-DESIGN §25. Reuse the canonical
  shapes in `common-elements.md` (Quantity, ComputeResources, Identity, lifecycleState, cidr/ipFamily,
  Reference, Condition) instead of re-coining per type — SPEC-DESIGN §24.
- **Quantities** carry an explicit unit via the `Quantity` pattern; timestamps are RFC 3339.
- **Enums:** lowercase, hyphenated for multi-word (`compatible-reference`, `available`) — unless an
  adopted standard dictates its own casing, in which case mirror the standard and record it in
  `adopts[]`.
- **Outputs:** `camelCase` typed keys naming the capability, not the implementation
  (`rbdStorageClass`, `connectionString`) — consumers bind to these (E2).
- **Adopted vocabulary:** when a field mirrors a standard's element, keep the standard's field name
  where practical and record provenance + license in `adopts[]` (SPEC-DESIGN §22–23).

## 5. File names

Registry type files are `category.type.<json|yaml>` — lowercase, dot-joined, with the PascalCase Type
segment rendered **kebab-case** (`compute.virtual-machine.json`, `network.ip-address.json`). JSON is the
canonical interchange form; YAML is allowed for authoring (VERSIONING.md §Serialization).

## 6. Instance handles & IDs

- Instance / graph node ids: lowercase **kebab-case**, short and stable (`ocp-control01`, `ups-rack`).
- Type UUIDs are UUIDv4, immutable for the type's life; handles are mutable/rebindable
  (SPEC-DESIGN §18, `contracts/identifier-scheme.md`).

## 7. Standards-grounded type plan (this initiative)

The new types, their category/tier, and the standard each adopts by reference. All Tier-1 Core.

| Type | Category (new?) | Adopts (by reference) | Notes |
|---|---|---|---|
| `Hardware.MemoryModule` | Hardware ✚ | Redfish `Memory` | DIMM: capacity, slot (`DeviceLocator`), serial |
| `Hardware.Processor` | Hardware ✚ | Redfish `Processor` | CPU: cores/threads/model |
| `Hardware.GraphicsProcessor` | Hardware ✚ | Redfish `Processor` (ProcessorType=GPU) / `PCIeDevice` | GPU; extensible into PCIeDevice |
| `Hardware.StorageDevice` | Hardware ✚ | Redfish `Drive` (+ SNIA Swordfish) | disk/SSD: wwn, serial, bay |
| `Hardware.NetworkInterface` | Hardware ✚ | Redfish `NetworkAdapter`/`NetworkPort` | NIC: mac, speed |
| `Compute.BareMetalHost` | Compute | Redfish `ComputerSystem` + Metal3 `BareMetalHost` | the physical **asset** (raw resource, §28); rollup of Hardware.* (§26). An *allocation* to a consumer is the ownership model, not a separate type (§3a); a running *instance* is a realized entity. |
| `Storage.Cluster` | Storage | SNIA Swordfish `StorageSystem` + Rook `CephCluster` (provider) | vendor-neutral; provider on instance; protocol outputs |
| `Network.Gateway` | Network | K8s Gateway API (concept) / general L3 routing | routing/NAT/firewall edge |
| `Network.DnsZone` | Network | RFC 1035 / 1034 | authoritative zone; external-dns `DNSEndpoint` as k8s-native ref |
| `Network.DhcpScope` | Network | RFC 2131 (+ 8415) / ISC Kea subnet | address scope/range + reservations |
| `Security.DirectoryService` | Security | RFC 4511/4512 (LDAP) + RFC 4120 (Kerberos) | the directory server; FreeIPA realizes this + DnsZone |
| `Facility.PowerFeed` | Facility ✚ | Redfish DCIM `Circuit`/`PowerDistribution` + NUT (UPS) | power source; graph root for the homelab |

✚ = introduces a new category (Hardware, Facility), anchored to Redfish per §2.

Authoring follows the registry process (`governance/registry-governance.md` §3, `CONTRIBUTING.md`):
each type validates against the meta-schema (`tools/validate.py`), ships ≥1 worked example, records
`adopts[]` provenance + license, and starts at `status: developing` until promoted.
