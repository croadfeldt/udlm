# UDLM ADR-082: A class is defined once and filed under usage groups like hard links

**Status:** Accepted (croadfeldt upstream) — requires engineering ratification; maintainer decision 2026-09-29
**Realized by:** `docs/spec/foundations/class-tiers.md` §3, §8 (`CLS-001`, `CLS-003`, `CLS-010`..`CLS-013`) · `registry/taxonomies/usage-group.yaml` · `registry/class.schema.json` (`filed_under`) · `registry/resource-type-spec.schema.json` (`filed_under`) · `registry/entity-view.schema.json` (computed `filed_under`) · `registry/tools/generate_class_specs.py` (filing rides the flat spec; `registry/generated/groups/`) · `registry/tools/generate_pin_manifest.py` (`filed_under` identity-excluded) · `tests/check_class_groups.py` · `tests/check_class_paths.py` (hosting group) · `registry/tools/urf.py` and `docs/spec/contracts/identifier-scheme.md` §9.2, §9.9 (`URF-010`, `URF-011`) · `tests/check_urf_conformance.py` · `registry/examples/must-reject/023-record-carries-a-filing.yaml`. The dissolutions and renames in §Consequences land per family in follow-up PRs; each is a register row.
**Date:** 2026-09-29
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).**
`ADR-038 — scope is portability: an element ports across exactly the classes beneath the scope it is declared at`.
`ADR-061 — the classes directory is a verified projection of the class hierarchy; a class's directory is named for the class`.
`register row 069 / CLS-002 — the Base test: a widely used API abstracts over the members; every Base element is honorable beneath it; an offering at any tier accepts orders above it`.
`register row 063 — Grouping is the native grouping anchor for instances`.
`ADR-075 — UPS is a Base of its own; Facility and a Power base both fail the Base test`.

---

## The problem

The registry has one tree doing two jobs. `Hardware`, `Network`, `Storage`, `Security`, `Software`,
`Data`, `Facility` and `Observability` are Bases in the schema and folders in fact: none passes the
Base test, so each carries `instantiable: false` (the old `CLS-003`) and every member carries a name
that promises a family contract the folder cannot honour. `Storage.Pool` and `Storage.Volume` share
nothing an order could move between; `Hardware.Processor` and `Hardware.BMC` share one discriminator.
ADR-075 hit this from the other side: a UPS could not go under `Facility` because a folder gives a
member nothing, and a `Power` Base failed the test too, so the unit became a Base and the register
recorded "`Facility` then holds one entry" as an open question.

The folder also had to be *the* place a class lived. A directory service belongs with security and
with identity; a topology belongs with facility and with network. One tree cannot say that, so the
tree said one thing and people remembered the other.

## Decision

Two systems, one registry.

1. **The definition system is the three tiers, keyed to portability.** The tier comes from `class`
   and `parent`, never from the segment count; the name renders the ancestry (`CLS-001`). A Base
   passes the Base test (`CLS-002`); a Type is one form or one dialect (`CLS-004`); a Provider Class
   is provider-specific data only (`CLS-005`). A name carries definition only: `StorageCluster`,
   `StorageCluster.Ceph`, `StorageCluster.Ceph.<Provider>`.

2. **The grouping system for classes is usage groups**, a governed vocabulary on the existing
   TaxonomyTerm machinery: `registry/taxonomies/usage-group.yaml`, root `usage-group`, terms
   `compute`, `storage`, `network`, `hardware`, `power`, `facility`, `data`, `security`, `identity`,
   `observability`, `services`, `automation`. A Base declares `filed_under: [hardware, storage]`,
   many allowed. Unix hard-link semantics: the class is the inode (one identity, tier, parent,
   elements, version); a group is a directory; a filing is a link; the link count of every
   instantiable Resource Base is at least one (`CLS-010`, `CLS-011`). Adding or removing a filing
   changes nothing about the class: no version bump, no digest change (`filed_under` is
   identity-excluded, like `coverage`). Grouping of instances stays `Grouping` (row 063); there is no
   fourth mechanism.

3. **The eight folder Bases dissolve into group terms.** Each former member becomes a Base in its
   own right if it passes `CLS-002`, else is re-homed under a Base that does. `Hardware` is a group
   and not a Base: it represents no portable data; `device_class` is a discriminator, not a
   deliverable.

4. **On disk, ADR-061 is kept.** A class's directory is named for the class (kebab, as today). A
   Base has one hosting group, its canonical path in git:
   `registry/classes/resource/storage/storage-cluster/_base.yaml` and `storage-cluster/ceph.yaml`.
   Git has no hard links, so every other filing is a generated view,
   `registry/generated/groups/<group>.json` (`CLS-013`). Delimiters are never shared: `/` is a
   directory or locator, `.` is a tier. `storage/storage-cluster/ceph` is a locator;
   `StorageCluster.Ceph` is the name; `Storage.StorageCluster` is forbidden because it reads as
   Base.Type (`CLS-012`). Access, Knowledge and Process keep `<family>/<class>` until a family has two
   groups.

5. **A Base name stands alone.** It is filed in several directories and referenced with none. Where
   a widely used standard spells it, that spelling wins (Redfish, Swordfish: `StoragePool`,
   `NetworkAdapter`). The hosting group is the wider API family (Redfish → `hardware`, Swordfish →
   `storage`); moving a home is a `git mv`.

6. **URF.** The path axis carries definition only: `StorageCluster/Ceph` ↔ `StorageCluster.Ceph`,
   the bijection kept; groups never appear in the path axis (the group directories are outside URF).
   `filed_under` is the second sanctioned virtual field beside `member_of` (identifier-scheme §9.2),
   resolved through the record's `resource_type` to the class's *current* filing; it is declared and
   identity-stable, so stored criteria, `Grouping` criteria and layer targets may say
   `filed_under==hardware`. A stored value that is not a canonical term is refused (`URF-010`). A
   stored criterion spelled under a dissolved folder (`resource_type==Hardware.*`) is refused once the
   folder is gone; while it exists the gate warns (`URF-011`).

7. **A filing is never on a record.** No record kind carries `filed_under`, and it is never in the
   dispatch slice; a record's groups resolve through `resource_type` to the current filing, not the
   pinned version. Content is versioned; links are current. The entity view (a read model, never
   stored) may carry a computed `filed_under`, the way it carries `lifecycle_state`. Renames are
   identity and touch records once (`registry/renames.yaml`, the estate's conversion); filings are
   organization and touch none.

8. **Catalog and control plane, one chain.** Compile carries `filed_under` from the Base into the
   flat spec (`registry/generated/*.json`). The service-type generator and catalog expose it
   read-only on service types and catalog items, inherited from the class; an offering never declares
   its own. `GET /groups` and a `?filed_under=` filter use the same terms. A deployment-local shelf is
   a TaxonomyTerm in its own subtree (ADR-PROV-002's pattern), never `labels.category`.

## Alternatives considered

- **Keep folders as non-instantiable Bases** (the old `CLS-003`). Rejected: the name still claims a
  family, the schema still serves an inheritance nobody honours, and one tree still cannot file a
  class in two places.
- **A `groups` element on the class with a primary marker.** Rejected: an inode does not know which
  directory entry came first; the git path is the home, and the gate checks it is one of the
  filings.
- **A fourth grouping mechanism** (a group record with a member list). Rejected: `Grouping` already
  groups instances by stored criterion; `filed_under` groups classes by declaration; TaxonomyTerm
  already governs the vocabulary. Nothing new is needed.
- **Groups in the URF path axis** (`storage/StorageCluster`). Rejected: a path segment would then
  mean two things, and a filing change would change an address.
- **Group directories for every family now.** Deferred: Access, Knowledge and Process each have one
  group today; adding a level that repeats the family name says nothing.

## Consequences

Easier: a class is found under every group it belongs to; a name says only what a thing is;
`filed_under==hardware` replaces a folder glob that broke on every promotion; the catalog inherits
the same terms with no second vocabulary.

Harder, and owed as follow-up PRs, one per family, in this order so the estate can pin as each
lands: (1) this ADR, rules, meta-schema, taxonomy, gates — done here; (2) renames per family, each
with its Base's `CLS-002` case in the description and its `registry/renames.yaml` block. The names
from the estate's classes, as ruled:

| Today | Becomes | Note |
|---|---|---|
| `Storage.Pool` | `StoragePool` | Swordfish spelling |
| `Storage.Cluster` | `StorageCluster` | Types by dialect: `StorageCluster.Ceph` |
| `Storage.FileShare` | `FileShare` | |
| `Storage.Volume` | `Volume` | |
| `Storage.Dataset` | `Volume.ZFS` | a dialect Type: nothing wide abstracts a ZFS dataset. `Volume` spends its Type axis on dialect (`CLS-004`); form stays the `volume_mode` element |
| `Hardware.StorageDevice` | `StorageDevice` | Types by form (NVMe, SATA, …); `device_class` stays an element |
| `Hardware.NetworkInterface` | `NetworkInterface` | Types Ethernet, Bond, Bridge, VLAN |
| `Hardware.Processor` | `Processor` | |
| `Hardware.BMC` | `BMC` | |
| `Network.IPAddress` | `IPAddress` | |
| `Network.VirtualNetwork` | `VirtualNetwork` | Types are host/overlay dialects (OVN, libvirt, bridge); there is no `VirtualNetwork.VLAN` |
| `Network.Gateway` | `NetworkGateway` | |
| `Network.Switch` | `NetworkSwitch` | |
| `Network.AddressService` | `AddressService` | Types DHCP, DNS |
| `Security.DirectoryService` | `DirectoryService` | Types LDAP, IPA; filed under `identity` and `services` |
| `Facility.PowerFeed` | `PowerFeed` | ADR-075's recorded follow-up |

Unchanged: `Machine.*`, `Container`, `KubernetesCluster`, `KubernetesNamespace`,
`KubernetesNodePool`, `UPS`, `Job`, `Topology`, `Template`.

Ruled the same day for the members the brief did not name — leaf-name promotion: `Data.Database`
→ `Database`; `Facility.Location` → `Location`; `Observability.LogShipper` → `LogShipper`;
`Security.CredentialRef` → `CredentialRef`; `Network.ConnectionProfile` → `ConnectionProfile`;
`Network.DHCPScope` → `DHCPScope` and `Network.DNSZone` → `DNSZone` (served data, distinct from the
`AddressService` that serves it: Service = act, Resource = thing); `Network.IPAddressPool` →
`IPAddressPool`; `Network.Subnet` → `Subnet`; `Network.VLAN` → `VLAN` (an 802.1Q fabric segment, a
Base of its own); `Storage.Class` → `StorageClass`; `Storage.Layout` → `StorageLayout`.

Open, for the maintainer: `Hardware.GraphicsProcessor` (`Processor.GPU` Type or a `GPU` Base);
`Hardware.BiosProfile` (an element of `Machine.BareMetalHost` or a `FirmwareProfile` Base);
`Software.Service` (held for the Service/Resource ruling, #232).

Costs to state plainly. `Hardware.device_class` is inherited by six members and `Network.zone` and
`Network.tier` by eleven; after dissolution each new Base declares them itself, with the vocabulary
kept in one place in `common-elements.schema.json` so the enum has one home. Every generated spec
gained a `filed_under` line once; because the field is identity-excluded, no digest and no pin
manifest row moved. Stored criteria spelled under a folder (`resource_type==Network.VLAN`) are
warned now and refused when the folder goes; the estate's conversion (B.2) rewrites them with the
rename map. Filings for `Template` (`services`) and `Topology` (`facility`) are first filings, not
rulings; a second filing is a one-line change.

## Data · Policy · Provider

**Data:** the class carries `filed_under`; the flat spec and the view carry it read-only; no record
does. The usage-group vocabulary is a TaxonomyTerm seed.
**Policy:** nothing. A filing is not a fact a policy reads; a policy that wants "everything under
hardware" says `filed_under==hardware` in a stored criterion and reads the class's current filing.
**Provider:** nothing. A provider binds a class by name and tier; it never sees a filing, and a
filing is never in the dispatch slice (`DSP-002`).

**Peer test (ADR-008):** a conformant peer must keep definition and filing apart, must resolve a
record's groups through its class rather than store them, and must honour the Base test for every
class it serves — that is substrate. Where it hosts a class on disk, how it renders the group views,
and which terms an organization adds are implementation.
