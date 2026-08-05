# Research — is there a standard for describing storage layouts in JSON?

**Status:** research (non-normative). **What it settles:** whether an external standard exists that UDLM
can adopt-by-reference for *host storage layout* — partition tables, filesystems + mounts, LUKS — across
the three consumers that need one vocabulary: a UDLM registry type (intent), estate records describing
real hosts (realized), and day-0 provisioning input. **Method:** survey of the official specs/schemas of
five primary candidates and six secondary prior-art systems, scored against the coverage the registry is
missing and the adoption tests in
[`../../design-principles/adopted-standards.md`](../../design-principles/adopted-standards.md)
(disposition, tier, net-negative, license compatibility). Registry baseline this must not duplicate:
`Storage.Pool` already owns RAID/pool topology (recursive `vdevs`, `pool_kind` zfs/md/hardware_raid/lvm/btrfs,
Swordfish `RAIDType`); `Hardware.StorageDevice` already owns drives and has `device_class: partition` +
`parent_device` (Redfish `Drive`).

## Short answer

**No.** There is no cross-vendor standard for describing a host's storage layout in JSON. The landscape
splits cleanly by orientation, and nothing crosses the line:

- **Intent (one-shot provisioning):** [Ignition spec v3.x](https://coreos.github.io/ignition/specs/) is the
  only JSON-native, machine-schema'd, multi-vendor format (FCOS, RHCOS, Flatcar, openSUSE MicroOS, SLE
  Micro). Coverage: GPT partitions, mdraid, LUKS(+Clevis), six filesystem formats. Holes: **no LVM**
  ([#1289](https://github.com/coreos/ignition/issues/1289), open since 2021), **no ZFS**
  ([#2078](https://github.com/coreos/ignition/issues/2078)), and even persistent mounts sit outside the
  storage model (raw systemd units; `with_mount_unit` is Butane sugar).
- **Realized (what a host actually has):** no standard exists, full stop. Each tool defines its own ad-hoc
  JSON — `lsblk --json` (default output explicitly *not* a stable API), `sfdisk --json` (output-only, can't
  re-ingest), `zpool status -j` (OpenZFS ≥ 2.3, with a versioned envelope). udisks2 has the best *object
  model* (Block / PartitionTable / Partition / Filesystem / Encrypted / MDRaid, + LVM2 module) but speaks
  only D-Bus, no JSON serialization.
- **The already-adopted standards stop above the layout.** Confirmed against the schema indexes: Redfish +
  Swordfish have **no Partition resource and no OS-mount concept anywhere** — depth ends at Drive →
  Volume/StoragePool → array-side FileSystem/FileShare. TOSCA `BlockStorage` is an opaque attachable
  volume (size/volume_id/snapshot_id). CDMI is object/data-namespace management, not block layout.

The most complete single vocabulary anywhere is **Curtin storage config** (disk/partition/format/mount/
lvm/dm_crypt/raid/bcache/zpool/zfs) — but it fails the adoption tests on independent grounds: AGPL-3.0,
YAML-native (JSON accepted only as a YAML subset, nowhere stated), **no published schema** (subiquity's
autoinstall schema declares storage as an opaque `{"type": "object"}`), single-vendor governance.

## Why model layout as standard data at all

Storage layout is the part of the model least tolerant of informal description, for four reasons:

1. **Layout is the map to the only non-fungible thing in the estate.** Compute is regenerable; data is
   not, and the layout is the *addressing scheme* for the data — which drive, which partition, which
   pool, decrypted how, mounted where. Today that map lives implicitly in tool artifacts and on-disk
   labels; when the host dies, the map dies with it and the surviving disks become a forensics exercise.
   First-class, comparable layout data is what turns "the disks survived" into "the data is reachable."
2. **Every abstraction above it looks away at exactly this level.** The survey shows it concretely:
   Redfish stops at the drive, Swordfish at the array volume, TOSCA/Terraform at "a volume of size N,"
   Kubernetes at the PVC. But hosts boot, encrypt, and fail at the layout level — the unmirrored ESP,
   the LUKS volume with an unrecorded key ceremony, the pool spanning the wrong fault domain. The gap
   between "volume of size N" and a bootable machine with reachable data is filled either with
   comparable data or with tribal knowledge.
3. **Redundancy claims are layout claims.** "Tolerates one drive loss" is not a volume-level property —
   it is a fact about which partitions sit on which physical drives and how the pool composes them.
   Fault-domain reasoning, blast-radius analysis, and honest DR claims all require the layout graph;
   without it redundancy is an assertion, with it it is derivable and checkable.
4. **Intent-vs-realized comparison requires both sides in the same terms.** The model's core loop —
   declare, observe, detect drift — is only mechanical if the realized layout reads back into the
   vocabulary the declaration was written in. A layout described once at build time and never
   re-expressible afterward can drift indefinitely without anything noticing.

## Comparison matrix

Coverage of the surface the registry is missing (✅ full · ◐ partial · ✗ none):

| | Part. table (GPT) | Partitions | sw RAID | LVM | ZFS | FS + mount | LUKS | JSON-native | Machine schema | License | Orientation |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **Ignition v3.6** | ✅ GPT-only | ✅ label/number/size/start/typeGuid | ✅ mdraid | ✗ | ✗ | ◐ format yes, mount via systemd | ✅ +Clevis/tang/tpm2 | ✅ | ✅ [per-version JSON Schema](https://github.com/coreos/ignition/blob/main/config/v3_6/schema/ignition.json) | Apache-2.0 | intent, one-shot |
| **Curtin v1/v2** | ✅ gpt/msdos/vtoc | ✅ | ✅ 0/1/5/6/10 | ✅ | ◐ experimental | ✅ format+mount first-class | ✅ dm_crypt | ◐ incidental | ✗ | AGPL-3.0 | intent (`preserve` asserts, doesn't capture) |
| **Redfish/Swordfish** | ✗ | ✗ | ◐ Volume RAIDType | ✗ | ✗ | ◐ array-side only | ✗ | ✅ | ✅ DSP8010 bundle | spec-reproduction terms | realized, BMC/array view |
| **lsblk/sfdisk/zpool -j** | ✅ (sfdisk, out-only) | ✅ | ✅ | ✅ | ✅ (zpool -j) | ✅ (lsblk) | ✅ (`crypt`) | ✅ | ✗ (ad-hoc, per-tool) | GPL-2.0+ / CDDL | realized, per-tool |
| **Metal3/Ironic RAID** | ✗ | ✗ | ◐ levels 0/1/1+0 | ✗ | ✗ | ✗ | ✗ | ✅ | ◐ CRD/API | Apache-2.0 | intent, RAID-only |

Per-candidate detail with sources is in the appendix below.

## The altitude caveat — these standards describe *specific* layout, not intent

None of the surveyed standards is an intent vocabulary. An Ignition config names `/dev/sdb`, partition 1,
1024 MiB from sector so-and-so — that is a **complete concrete plan**, which in
[ADR-033's](../adr/ADR-033-templates.md) tiers (Pattern / Template / System = Intent / Requested /
Realized, per ADR-030) sits at the **Requested** tier; the lsblk/zpool readback is the **Realized** tier.
The **Intent** tier — "boot redundancy, data encrypted at rest, ≥ N usable, tolerate one drive loss,"
with device *selectors* rather than device paths — is covered by **no surveyed standard**. The closest
things to intent-altitude prior art are compilers *down to* specific layout, not standards: Butane's
[`boot_device`](https://coreos.github.io/butane/config-fcos-v1_6/) (`mirror`/`luks` — "mirror the boot
disk" compiled to concrete Ignition partitions+raid), subiquity autoinstall's
[`layout` shortcuts](https://canonical-subiquity.readthedocs-hosted.com/en/latest/reference/autoinstall-reference.html)
(`lvm`/`zfs`/`hybrid` named outcomes + `match:` disk selectors), Metal3's `rootDeviceHints`
(selector-not-path — already adopted), and systemd-repart's constraint sizing
(`SizeMinBytes`/`SizeMaxBytes`/`Weight`).

**Direction (maintainer ruling): intent is based on the storage config itself — not a parallel
descriptor.** The intent tier is the *same* storage-config vocabulary with the concreteness relaxed,
not a second vocabulary invented beside it: device **selectors** in place of device paths (the
`rootDeviceHints` / autoinstall `match:` move), size **floors/ranges** in place of exact MiB (the
systemd-repart `SizeMinBytes`/`Weight` move), and redundancy expressed **structurally** — a mirror vdev
with unbound members *is* the intent "boot redundancy," no separate `redundancy_floor` field needed.
Binding intent → Requested is then selector resolution, not translation between vocabularies — which is
exactly what Butane's `boot_device` demonstrates mechanically.

This is not a new posture — it is the same move
[ADR-036](../adr/ADR-036-storage-selection-requirements.md) already made for storage *selection*
(**Proposed**, pending engineering ratification #217 — lean on it as the registry's direction, not
settled doctrine): its requirements descriptor deliberately mirrors the provider's advertised
capability fields "so request and advertisement speak one language," and the provider's concrete choice
lands in `outputs.storage_backing`, never in intent. Its PVD-001 discriminator (*reference* when the
vocabulary is portable, *requirement* when the candidate set is inherently vendor/host-specific) sorts
the layout fields cleanly: **topology is portable** — vdev/partition/filesystem structure may sit in
intent as-is; **device binding is host-specific** — the analog of the vendor-native storage class — so
intent carries selectors, never paths, and the concrete binding is a realized output.

**One boundary, so the two intents don't blur: selection vs arrangement.** ADR-036 governs *which
backing provides a volume* — capability minima (tier, min_iops), deliberately structure-blind, because
the candidate set belongs to the provider. Layout governs *how block space is arranged* — structural,
because the topology belongs to the consumer. A VM disk legitimately carries both (a selection
descriptor choosing its backing, a layout arranging what's on it); neither vocabulary leaks into the
other — no `min_iops` on a partition entry, no partition table in a selection descriptor.

So the adoption below buys the field vocabulary for **all three tiers**; what remains UDLM's own
surface is only the *relaxation grammar* (which fields may be selectors/ranges at the Intent tier),
not a new noun set.

### Reconciliation — `Storage.Layout` exists now (disk-set altitude)

While this research was in flight, the Compute reconciliation (PR #322) birthed a `Storage.Layout`
type. **Naming disambiguation:** that type is **disk-set layout** — *which disks a consumer has*
(named, sized entries with role/boot designation) — while this document's subject is **intra-disk
arrangement** (partition tables, filesystems, LUKS). Complementary altitudes, one word. The new
type's named `entries[]` are the natural anchor if the Ignition intra-disk vocabulary recommended
below is adopted later: an entry is a disk-shaped unit, so per-entry partition/filesystem/encryption
sub-shape attaches there without new surface. Two rulings recorded against that type
(2026-08-02): **`storage_tier` is the standardized entry-level intent** — providers MAY expose
storage classes but MUST map each class back to a tier so tier-authored intent resolves
(`Platform.StorageClass.tier`); the chosen class is a per-entry realized fact
(`storage_backing` in the realization map). And **layout records are per-consumer** — shape reuse
is the ADR-033 Template tier, keeping the realization map unambiguous.

**And the tiers must carry lineage.** A Requested layout is not merely *shaped like* its Intent — it
must reference the Intent record it was resolved from, carrying the resolutions that bound it (which
physical device each selector matched, which size each range settled at); Realized in turn references
Requested through the provider's populated outputs. This is what makes the tier stack operational
rather than three disconnected documents: drift detection is comparison **along a lineage edge** (does
Realized still satisfy the Intent it descends from?), and rehydration is **walking the lineage back**
to the Intent tier and replaying it — against new hardware, where the same selectors bind to different
devices, which is precisely why the intent record and the lineage, not the concrete layout alone, are
what must survive. Same-vocabulary tiers + recorded bindings; no lineage, no replay.

## Verdict

1. **The literal question — "is there a standard?" — has a negative answer**, and the doc should be
   citable for that: intent-side the nearest thing is Ignition (standard-shaped: versioned spec, JSON
   Schema, five independent consumer distros); realized-side there is nothing, only per-tool JSON.
2. **The gap decomposes along a line UDLM already draws.** Aggregation (RAID/pool) is *not* missing —
   `Storage.Pool.vdevs` covers it, and Ignition `raid[]` / Metal3-Ironic RAID / Curtin `raid` all map into
   `pool_kind: md|hardware_raid` without new surface. What is genuinely missing is exactly Ignition's
   remaining vocabulary: **partition entries on a device, filesystem format + mount, LUKS**.
3. **Ignition's holes don't hurt UDLM.** LVM/ZFS — the two things Ignition can't say — are precisely the
   things UDLM already says natively (`Storage.Pool` + `Storage.Dataset`, OpenZFS CANONICAL). The
   composite covers what no single standard does.

## Recommendation (disposition per candidate, pending maintainer ratification)

- **Ignition storage vocabulary → adopt, tier1_value** (vocabulary reference, not record shape — same tier
  as SMB share vocabulary on `Storage.FileShare`). Anchor the fields onto existing types per the
  net-negative test — no *new* type needed for the partition arm (the since-born `Storage.Layout` is
  disk-set altitude, see the reconciliation note above; its entries could later carry this vocabulary
  per-entry):
  - *Partitions:* extend `Hardware.StorageDevice` where `device_class: partition` — add the Ignition
    partition vocabulary (`label`, `number`, `size_mib`, `start_mib`, `type_guid`) alongside the existing
    `parent_device`. Redfish (the type's current anchor) has no partition concept, so there is no
    conflict — Ignition names the sub-drive layer Redfish declines to model.
  - *Filesystem + mount:* the real modeling decision. `Storage.Dataset` requires `depends_on → Storage.Pool`
    (1..1), so a plain ext4-on-a-partition cannot be a Dataset today. Either relax that edge to also accept
    `Hardware.StorageDevice`, or add a minimal `Storage.Filesystem` adopting Ignition
    `filesystems[]` (`format`, `label`, `uuid`, `mount path`, `mount options`). I lean **relax the edge**
    (reduce-to-existing), but it touches OpenZFS-anchored semantics — a maintainer decision.
  - *LUKS:* Ignition `luks[]` vocabulary (+Clevis tang/tpm2) — as an encryption block on the filesystem/
    device rather than a new type.
- **Curtin → PRIOR-ART** in the register: the completeness yardstick the composite is measured against,
  with the rejection grounds recorded (AGPL → `license_compatibility` fails `compatible-reference`;
  no schema; YAML; single-vendor). Not adopted, but its type inventory is the checklist.
- **Realized side → no adoption possible; record the finding.** Estate records keep the UDLM shape;
  `lsblk --json` / `sfdisk --json` / `zpool status -j` are *ingestion sources* a provider may emit
  (PRIOR-ART entries at most). udisks2's object model is corroborating vocabulary (its nouns — Partition,
  PartitionTable, Filesystem, Encrypted, MDRaid — are the same nouns as the recommendation above).
- **Redfish/Swordfish → no change**, but register the confirmed scope boundary ("no Partition resource,
  no OS mounts — verified against the 2025.3/v1.2.8 schema indexes") so the next person doesn't re-ask.
- **Metal3/Ironic RAID → note as PATTERN** adjacent to the existing `root_device_hints` adoption: hardware
  RAID intent arrives as `Storage.Pool` (`pool_kind: hardware_raid`) `contained_by` the host, which the
  pool type already documents as the provisioning driver.

**Consumer fit under this recommendation:** intent = UDLM types carrying Ignition vocabulary; provisioning
= mechanical projection from those fields to an Ignition config (RHCOS/FCOS path; kickstart/ansible
translation for package-mode RHEL — same fields, different emitter); realized = provider populates the
same fields from lsblk/zpool JSON. One vocabulary, three duties — which was the requirement.

## Open questions (maintainer)

1. **Anchor point:** partition/filesystem fields on `Hardware.StorageDevice` + a relaxed `Storage.Dataset`
   edge (as recommended), or a first-class `Storage.Layout` type referenced from
   `Compute.BareMetalHost` — the "named reference anchor" from the earlier discussion? ADR-013 (components
   are host rollups, not records) pushes against layout-as-separate-record for *hardware*, but partitions
   are arguably storage, not hardware components.
2. **`Storage.Dataset` edge relaxation** vs a new `Storage.Filesystem` type — the OpenZFS anchoring of
   Dataset is the thing at stake.
3. Whether the Ignition adoption should pin `3.x` as a range (its own semver-like scheme supports it:
   configs carry `ignition.version`, minor-forward compatible) or pin 3.6.0 exactly.

## Limits (honest scope)

- Paper survey of specs and schemas; nothing was executed against a real host or emitted to Ignition.
- Curtin's `dm_crypt` LUKS-version field and Canonical CLA status could not be confirmed from official
  sources; neither affects the verdict (the license alone disqualifies adoption).
- The provisioning projection (UDLM fields → Ignition config emitter) is asserted as mechanical by analogy
  with `tosca_emit.py`, not built.

---

## Appendix — per-candidate facts (official sources only)

### Ignition config spec v3.x (CoreOS / Red Hat)

- Spec versions 3.0.0–3.6.0 (+3.7.0-experimental); every config pins `ignition.version: X.Y.Z`; minor
  versions forward-compatible within the major. [Specs index](https://coreos.github.io/ignition/specs/),
  [v3.6 spec](https://coreos.github.io/ignition/configuration-v3_6/).
- Machine-readable: per-version JSON Schema in-repo
  ([`config/v3_6/schema/ignition.json`](https://github.com/coreos/ignition/blob/main/config/v3_6/schema/ignition.json));
  the Go types are *generated from* the schema, so the schema is authoritative.
- `storage.disks[].partitions[]`: `label`, `number`, `sizeMiB`, `startMiB`, `typeGuid`, `guid`,
  `shouldExist`, `wipePartitionEntry`, `resize`. GPT-only (no MBR). `storage.raid[]`: `name`, `level`,
  `devices`, `spares`, `options` (mdadm). `storage.filesystems[]`: `device`, `format`
  (ext4|btrfs|xfs|vfat|swap|none), `path`, `wipeFilesystem`, `label`, `uuid`, `options`, `mountOptions`.
  `storage.luks[]`: `name`, `device`, `keyFile`, `clevis` (tang/tpm2/threshold), `options`, `wipeVolume`,
  `discard`, `cex` (s390x, 3.5+).
- Cannot express: LVM ([#1289](https://github.com/coreos/ignition/issues/1289)), ZFS
  ([#2078](https://github.com/coreos/ignition/issues/2078)), bcache, multipath, MBR, persistent mount
  units (systemd units or [Butane](https://coreos.github.io/butane/config-fcos-v1_6/) `with_mount_unit`).
- Apache-2.0; `coreos` GitHub org (Red Hat-maintained, no foundation). Consumers: FCOS, RHCOS, Flatcar,
  openSUSE MicroOS, SLE Micro ([known users](https://coreos.github.io/ignition/)).
- One-shot first-boot intent by design: "provisioning tool, not a configuration management tool"; fail-hard
  ("the machine specified or no machine at all") — [rationale](https://coreos.github.io/ignition/rationale/).
  No realized-state readback, no drift model.

### Curtin storage config (Canonical)

- `storage: {version: 1|2, config: [...]}`; v2 makes partition actions a complete partition-table
  description (respects `offset`, adds `resize`, `partition_type`) but is "under active development and
  subject to change". [Storage doc](https://curtin.readthedocs.io/en/latest/topics/storage.html).
- Types: `disk` (ptable msdos/gpt/vtoc, serial/path/model matching, wipe, preserve, grub_device),
  `partition` (size, flag boot/bios_grub/logical/extended/raid/lvm, number, wipe, preserve), `format`
  (ext4/ext3/xfs/zfsroot/swap/fat32), `mount` (path, options, fstype, fstab spec/freq/passno),
  `lvm_volgroup`/`lvm_partition`, `dm_crypt` (key|keyfile), `raid` (0/1/5/6/10, spares, metadata),
  `bcache` (cache_mode), `zpool`/`zfs` (**experimental**), `dasd`, `nvme_controller` (experimental).
- `preserve: true` *asserts* existing state against the config (mismatch errors) — it is not a capture
  format for realized state.
- Loaded via `yaml.safe_load`; JSON works only as a YAML subset, nowhere documented. No schema —
  [subiquity's `autoinstall-schema.json`](https://github.com/canonical/subiquity/blob/main/autoinstall-schema.json)
  declares `"storage": {"type": "object"}` (validation is delegated to curtin at runtime).
- AGPL-3.0-only; Canonical governance. Consumers: curtin, subiquity/autoinstall (superset: `layout`
  shortcuts incl. zfs/hybrid-TPM, disk `match`), MAAS (emits JSON per its own custom-storage schema,
  translated via curtin `block-meta custom`).

### DMTF Redfish + SNIA Swordfish

- Schemas: [DSP8010 bundle](https://redfish.dmtf.org/schemas/) (CSDL + JSON Schema + OpenAPI), current
  2026.1; Swordfish v1.2.8 (SNIA Standard, July 2025, entering ISO).
- Depth: `Storage` → `StorageController` / `Drive` / `Volume`; Swordfish adds `StoragePool`, `FileSystem`
  (array-side namespace), `FileShare`, `Volume.RAIDType` (17 values). **No Partition resource exists in
  either [schema index](https://redfish.dmtf.org/redfish/schema_index); no OS mount concept.** The view
  is BMC/array-side, exactly where the registry already uses it (`Hardware.StorageDevice`,
  `Storage.Volume`, `Storage.Cluster`, `Storage.Pool.raid_type`).

### util-linux / udisks2 / OpenZFS (realized-side JSON)

- `lsblk --json`: full stack visible (TYPE part/disk/raid*/lvm/crypt/mpath, FSTYPE, MOUNTPOINT(S),
  PARTTYPE/PARTUUID, PKNAME parent chain, nested `children[]`) — but the man page directs scripts to pin
  `--output` explicitly; the default shape is not a stable API.
  [man lsblk](https://man7.org/linux/man-pages/man8/lsblk.8.html).
- `sfdisk --json`: complete GPT table dump (`partitiontable` with per-partition start/size/type-GUID/uuid/
  name/attrs) but **output-only** — "sfdisk is not able to use JSON as input format".
  [man sfdisk](https://man7.org/linux/man-pages/man8/sfdisk.8.html).
- OpenZFS ≥ 2.3.0: `zpool status -j` etc., with an explicit `output_version` envelope —
  [release notes](https://github.com/openzfs/zfs/releases/tag/zfs-2.3.0).
- udisks2: object model Block / PartitionTable / Partition / Filesystem / Encrypted / Swapspace / MDRaid
  (+ LVM2/BTRFS/iSCSI/NVMe modules) — D-Bus only, no JSON.
  [API docs](http://storaged.org/doc/udisks2-api/latest/).

### Metal3 / OpenStack Ironic (RAID intent)

- Metal3 `BareMetalHost.spec.raid`: `hardwareRAIDVolumes` (name, level 0/1/5/2/6/1+0/5+0/6+0, size,
  controller, physicalDisks, rotational), `softwareRAIDVolumes` (levels 0/1/1+0, max two, first must be
  RAID1); `rootDeviceHints` already adopted on `Compute.BareMetalHost`. Stops at RAID + root selection —
  no partitions/filesystems. [Metal3 book](https://book.metal3.io/bmo/raid). Apache-2.0, CNCF Incubating
  (2025-08-27).
- Ironic [`target_raid_config`](https://docs.openstack.org/ironic/latest/admin/raid.html): `logical_disks[]`
  (size_gb|MAX, raid_level, is_root_volume, controller incl. `"software"`, physical-disk hints).
  Apache-2.0, OpenInfra.

### Closed out (2–4 lines each)

- **CDMI** (ISO/IEC 17826:2022, v2.0.0): cloud *data-object/container/queue* management over REST —
  containers are namespace groupings, not block devices. Not applicable.
- **TOSCA `tosca.nodes.Storage.BlockStorage`** (Simple Profile v1.3): `size`, `volume_id`, `snapshot_id`,
  attached via `AttachesTo` — opaque volume, no layout. Already used where it fits (relationship vocabulary).
- **linux-system-roles.storage** (MIT, Ansible/RH): pools/volumes YAML over blivet — LVM/mdraid/LUKS/
  Stratis/VDO. A *consumer-shaped DSL*, not a standard; prior art for the vocabulary.
- **systemd-repart**: INI drop-ins, GPT-only, but notable coverage per partition (Format=, Encrypt= LUKS2/
  tpm2, Verity=) — prior art for "partition entry carries its filesystem+encryption intent".
- **Kickstart** (`part/raid/logvol/volgroup/autopart/mount`): own text DSL, no JSON form; Anaconda's
  modular interface is typed D-Bus, not JSON.
- **blivet**: programmatic Python DeviceTree, no serialization format. **libstorage-ng** (SUSE): devicegraph
  save/load is XML, not JSON.
- **Terraform / OpenTofu**: Terraform core is
  [BUSL-1.1 since 1.6.0](https://github.com/hashicorp/terraform/blob/main/LICENSE) — not OSI-approved,
  fails `license_compatibility` before any technical evaluation.
  [OpenTofu](https://github.com/opentofu/opentofu/blob/main/LICENSE) (Linux Foundation fork) is MPL-2.0
  and genuinely open — but license aside, neither defines a storage-layout vocabulary: core/HCL are
  engine + syntax, and ["every resource type is implemented by a
  provider"](https://opentofu.org/docs/language/providers/) — storage resources are provider-specific
  and volume-opaque (size/attachment altitude, same as TOSCA BlockStorage; no partition/filesystem/LUKS
  surface). Nothing to adopt.
