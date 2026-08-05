# UDLM Registry — Naming Conventions

How we name resource types, fields, outputs, files, and instances, so the registry stays consistent and
predictable. These conventions are normative for new definitions; existing entries are brought into line
as they are revised. Referenced by `SPEC-DESIGN-REQUIREMENTS.md` §18 (Identity & naming) and enforced in
part by the meta-schema patterns (`resource-type-spec.schema.json`).

Guiding rule: **name to an existing standard before inventing.** Where an industry standard already
names a thing, adopt its vocabulary by reference (`adopts[]`, see SPEC-DESIGN §22–23) and let our name
mirror the concept; only coin a UDLM name where no standard fits.

## 1. Type names — `Category.Type`

- **Shape — domain-owned vs cross-cutting:**
  - **Domain-owned types → `Category.Type`**, both segments **PascalCase** (`Compute.VirtualMachine`,
    `Network.IPAddress`).
  - **Cross-cutting / foundational types (not owned by any single domain) → single-segment**
    PascalCase (`Capability`, `Topology`). This covers Knowledge-family entities *and* cross-domain
    Resource types like `Topology` that resources across many domains reference. The `family` field
    disambiguates. (The single-segment form signals "domain-neutral," not "Knowledge-only"; the
    meta-schema `resource_type` pattern already permits both forms.)
  - Enforced by the `resource_type` / `$id` patterns in the meta-schema.
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
- **Acronyms:** keep well-known initialisms **uppercase** in the Type segment, per the existing
  `Network.IPAddress` precedent — `Network.DNSZone`, `Network.DHCPScope` (not `DnsZone`/`DhcpScope`).

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
  the first-class side of the §26 component model. **Not physical-only**: a `device_class` discriminator
  (`physical | virtual | passthrough | partition`, common-elements §7) lets the same types model a real
  DIMM, a guest's virtual disk, a passed-through GPU, or a vGPU/SR-IOV/VLAN **slice of a physical parent**
  (via a `parent_device` reference). Anchored to Redfish `Memory`/`Processor`/`Drive`/`NetworkAdapter`
  (+ `NetworkDeviceFunction`/`PCIeFunction` for the derived cases). Distinct from `Compute` (the whole
  machine/instance).
- **`Facility`** — physical-datacenter resources (power, later rack/cooling). Anchored to Redfish DCIM
  `PowerDistribution`/`Circuit`/`PowerDomain` (+ NUT for UPS telemetry).

Resource vs Information: a **provisioned server is a Resource**; the **data it holds is Information**.
A directory *server* is `Security.DirectoryService` (a Resource); `Identity.*` (Person/Group/
ServiceAccount) is the Information data — don't conflate them.

## 2a. Provider capabilities and capability categories (ADR-PROV-002)

Three terms here are easy to collide; keep them distinct.

- **Provider capability** — what operation a provider exposes at the unified interface, as **(verb × domain)**:
  a closed-vocabulary verb (`realize_resources`, `serve_data`, `authenticate`, `federate`, `execute_workflows`)
  scoped to a resource-type **Category** (§2, the domain). Declared explicitly by the provider; organized by
  the governed **provider-capability taxonomy** (a `TaxonomyTerm` subtree under the `provider-capability` root,
  `registry/instances/provider-capability-taxonomy.yaml`). This is **not** the Knowledge-family
  **`Capability [Knowledge]`** — that is DAV's *architecture-capability* sense ("what an architecture
  provides," `entities/knowledge-family.md §4.1`), a **disjoint** `TaxonomyTerm` subtree under
  `architecture-capability`. One shared `TaxonomyTerm` **type**, two disjoint subtrees; parent chains never cross.
- **Capability category** — a **(verb × §2-Category)** term in the provider-capability taxonomy (e.g.
  `realize_resources/Storage` = *storage-provisioning*). Its domain axis **is** a §2 Category — a capability
  category composes on the resource-type Category, it does not replace or shadow it. **Non-exclusive**: a
  provider occupies every capability category its declared capabilities place it in (an InfoBlox IPAM sits in
  both `realize_resources/Network` and `serve_data/Network`). Always write **"capability category"** — never bare
  "category," which means the §2 resource-type Category. Policy targets a capability category, a capability verb,
  or the data itself (`data_classification`/`data_role`) — replacing the old `provider type` match axis.
- **Not "role."** A provider's capability grouping is a **capability category**, never a "role" — `role`/`data_role`
  is the data-purpose axis (`execution | assembly | governance | audit | cost`, ADR-PROV-001).

## 3. Suite products = composites, not monolithic types

A product that bundles several capabilities is modeled as **realizing multiple types**, not one bespoke
type. Example: FreeIPA → `Security.DirectoryService` (LDAP+Kerberos, RFC 4511/4512/4120) **+**
`Network.DNSZone` **+** (future) `Security.CertificateAuthority`. This keeps each type portable and
reusable and avoids a `FreeIPA.Everything` corner.

## 3a. Asset vs. allocation vs. instance — don't mint redundant types

Before adding a type, check whether the concept is already expressed by an existing mechanism:
- **An instance of a type** is a **realized entity** (`registry/realized-entity.schema.json`,
  `registry/instances/`) — `host-01` is an instance of `Compute.BareMetalHost`. Don't create a type to
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
- **Names from a standard the type formally adopts** → set **`standard_name`** on that `adopts[]` entry
  (it already carries `standard` + `version` + `source` + `license`). E.g. `Compute.BareMetalHost`
  adopts Redfish (`standard_name: ComputerSystem`, v2024.4) and Metal3 (`standard_name: BareMetalHost`).
  This *is* the {name, standard, standard_version} cross-walk, co-located with provenance — no duplication.
- **Names NOT tied to an adopted standard** (vendor/colloquial AKAs) → the top-level **`aliases[]`**
  (`{name, standard?, standard_version?, note?}`), e.g. AWS "Dedicated Host", OpenStack "Ironic node".

(The Knowledge-family **`Alias`** entity is a different tool — *taxonomy-term* normalization
"avoid → use instead", `entities/knowledge-family.md` §4.3 — not type cross-walks.)

## 4. Field, output, and enum names — casing (data model)

This section governs the **casing of the data model itself** (the keys in a resource definition). The
*runtime* concerns — how the API / event bus serialize it, Go/Python mapping, CloudEvents envelope,
broker routing — are a **DCM** concern: see DCM **ADR-018 (Wire serialization & event conventions)**.
DCM follows the same casing for the reason below, so there is no translation seam.

**Decision: `snake_case` keys.** UDLM is a **canonical data model meant to be consumed natively** by
every component (the "consume UDLM natively or it isn't universal" rule). Native consumption means the
model **is** the wire form — there is no separate "API casing" to translate to. DCM's API is the consumer
with a hard external constraint: it conforms to **AEP** (`aep.dev`, the dcm-project engineering team's
adopted API-design standard, enforced by the `aep-dev/aep-openapi-linter`), and AEP's prescribed fields
are snake_case (`page_size`, `*_time`). Native-universal consumption **+** AEP-bound API therefore jointly
force one casing — **snake_case** — across UDLM and DCM. (camelCase would re-introduce the very
translation layer native consumption exists to eliminate; it was tried and reverted — VERSIONING.md
surface-change log.) snake_case is also native to UDLM's actual stack: Python (providers, tooling), SQL stores,
protobuf/gRPC, and AEP itself; fully supported via tags in Go; only K8s/CRDs prefer camelCase, reached by
an **export adapter** at that domain boundary (not native consumption).

- **Field & output keys → `snake_case`** (`memory_size`, `block_storage_class`, `resource_id`). Reuse the
  canonical `common-elements.md` shapes (Quantity, ComputeResources, Identity, lifecycle_state,
  cidr/ip_family, Reference, Condition) — SPEC-DESIGN §24.
- **Don't use `camelCase` or `PascalCase` keys** (would diverge from the canonical/AEP casing) or
  **`kebab-case` keys** (forces `data['a-b']` bracket access).
- **Enum values → lowercase, hyphenated for multi-word** (`compatible-reference`, `whole-allocation`).
  These are string *values*, never keys, and AEP governs field *names* not *values*.
- **Quantities** carry an explicit unit via the `Quantity` pattern; timestamps are RFC 3339.
- **Outputs** are `snake_case` typed keys naming the capability, not the implementation
  (`block_storage_class`, `connection_string`) — the cross-entity binding surface (E2).
- **Initialisms** are lowercased within a snake key (`pod_cidr`, `api_url`, `internal_dns`, `vlan_id`),
  never split into letters. (The PascalCase *Type segment* keeps uppercase initialisms — §1 — that is the
  type **name**, not a field key.)

**Event-type identifiers** (UDLM event-catalog names, e.g. `resource.discovered`, `entity.realized`) use
lowercase **dot notation** so brokers can wildcard-route — distinct from payload property keys. The
routing mechanics live in DCM (ADR-018).

### Carve-outs — keep foreign / idiomatic casing
- **Adopted vocabulary is referenced, not minted as a live key.** The live field name is always the
  native (snake_case) form (`serial_number`); the adopted standard's source name — any casing — is
  recorded as a **metadata value**, not a key: `adopts[].standard_name` (`"SerialNumber"`, Redfish),
  a field-level `x-standard` pointer, or `aliases[]`. Foreign casing (camelCase/PascalCase) may appear
  **only** as a metadata value, an enum/string value, or inside an explicitly-opaque extension/raw blob
  (e.g. `provider_hints`, `x-…`, discovered-raw) — **never** as a typed resource key. This keeps the
  AEP-bound wire uniformly snake_case (SPEC-DESIGN §22–23, §23a).
- **SQL / store identifiers stay `snake_case`** (`discovered_records`, `intent_records`) — same casing as
  the model, so the projection is identity.

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
| `Hardware.NetworkInterface` | Hardware ✚ | Redfish `NetworkAdapter`/`NetworkPort` | NIC: mac, speed |
| `Compute.BareMetalHost` | Compute | Redfish `ComputerSystem` + Metal3 `BareMetalHost` | the physical **asset** (raw resource, §28); rollup of Hardware.* (§26). An *allocation* to a consumer is the ownership model, not a separate type (§3a); a running *instance* is a realized entity. |
| `Storage.Cluster` | Storage | SNIA Swordfish `StorageSystem` + Rook `CephCluster` (provider) | vendor-neutral; provider on instance; protocol outputs |
| `Network.Gateway` | Network | K8s Gateway API (concept) / general L3 routing | routing/NAT/firewall edge |
| `Network.DNSZone` | Network | RFC 1035 / 1034 | authoritative zone; external-dns `DNSEndpoint` as k8s-native ref |
| `Network.DHCPScope` | Network | RFC 2131 (+ 8415) / ISC Kea subnet | address scope/range + reservations |
| `Security.DirectoryService` | Security | RFC 4511/4512 (LDAP) + RFC 4120 (Kerberos) | the directory server; FreeIPA realizes this + DNSZone |
| `Facility.PowerFeed` | Facility ✚ | Redfish DCIM `Circuit`/`PowerDistribution` + NUT (UPS) | power source; graph root for the homelab |

✚ = introduces a new category (Hardware, Facility), anchored to Redfish per §2.

Authoring follows the registry process (`governance/registry-governance.md` §3, `CONTRIBUTING.md`):
each type validates against the meta-schema (`tools/validate.py`), ships ≥1 worked example, records
`adopts[]` provenance + license, and starts at `status: developing` until promoted.

## Extension model — augment, don't fork (seed for #198)

Grounded in RFC 8345's augmentation discipline and its documented failure mode (≥92 modules
augmenting the base with inconsistent patterns — the inconsistency itself broke multi-layer
composability). Normative rules:

1. **Never add vendor/org fields to a Tier-1 spec.** Vendor and organization specifics live at
   the extension surface only: a Tier-2 `Vendor.Type` / Tier-3 `Org.Type` in its own namespace,
   or `provider_hints` on the instance (SPEC-DESIGN §17/§24).
2. **Extensions are additive against the base** — a Tier-2/3 type layers new properties and
   non-topological references onto a Tier-1 concept; it does not redefine or remove base
   semantics (the RFC 8345 "augmentations in a new module" pattern).
3. **A recurring need is a base revision, not N vendor forks.** When the same extension appears
   across ≥2 independent vendors/orgs, the remedy is a backward-compatible Tier-1 MINOR (the
   IETF response to augmentation fragmentation), promoted through registry governance §3.
4. **The formal `extends` mechanism** is **RESOLVED** — Provider-Class `SharedDataElement`s
   (ADR-038; supersedes ADR-PROV-004/#198 — the `provider_extensions` carrier is retired and
   removed, #202 executed). A provider extends an instance **additively** at its Provider Class,
   never by modifying the closed base spec. **No-override is structural**: the base type-spec is
   `additionalProperties: false`, and an element may not shadow a base field. Any provider-specific
   data **computes a portability degradation** (`portability_breaking: true`, classification
   narrowed, the elements + bound provider recorded) that **MUST be surfaced to the consumer** —
   silent non-portability is prohibited. A Tier-2 `Vendor.Type` fork remains the path
   for a genuinely *new* type; a recurrence across ≥2 providers promotes to a base MINOR (rule 3). See
   docs/research/minimal-custom-surface-and-graph-resilience.md.
