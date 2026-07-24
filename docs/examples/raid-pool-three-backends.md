# Worked example — one Pool type, three RAID implementations

**What this settles:** the same `Storage.Pool` shape modeling a ZFS pool, an md boot mirror, and a
hardware-RAID virtual disk declared at bare-metal provision time — one reusable redundancy model,
native vocabulary kept authoritative, canonical mapping for cross-backend queries.

## 1. ZFS (the shape's origin)

```yaml
resource_type: Storage.Pool
spec:
  pool_kind: zfs
  vdevs:
    - type: raidz2                 # native term, authoritative
      raid_type: RAID6             # canonical mapping: RAID6-CLASS tolerance, not "is RAID6"
      members: [sd-a, sd-b, sd-c, sd-d, sd-e, sd-f]   # References -> Hardware.StorageDevice
    - type: mirror
      raid_type: RAID1
      members: [nvme-a, nvme-b]
```

## 2. mdraid (an OS boot mirror)

```yaml
spec:
  pool_kind: md
  vdevs:
    - type: raid1
      raid_type: RAID1
      members: [nvme0, nvme1]      # the md array IS one vdev; datasets above are LVM LVs
```

## 3. Hardware RAID — declared as intent, built at provision

```yaml
# contained_by -> the Compute.BareMetalHost; lifecycle Intent BEFORE the host provisions
spec:
  pool_kind: hardware_raid
  vdevs:
    - type: raid10
      raid_type: RAID10
      members: [ctrl-disk-0, ctrl-disk-1, ctrl-disk-2, ctrl-disk-3]
```

The bare-metal provisioning provider (Metal3/BMC-class) derives its controller configuration FROM
this declared pool — the host type carries no RAID fields (see Compute.BareMetalHost 0.6.0's
provisioning-intent surface: image/root-hints/boot, with storage topology living here).

## What every backend gets for free

- **Blast radius as a graph walk:** members are References to `Hardware.StorageDevice` — a dead
  drive's inbound edges are the affected vdevs, whose pools, whose datasets.
- **Degradation as drift:** `redundancy_status` and `fault_tolerance_remaining` outputs — a
  degraded mirror publishes `fault_tolerance_remaining: 0`, the number an operator acts on.
- **Cross-backend queries:** `raid_type` (Swordfish RAIDType) answers "everything with ≥2-failure
  tolerance" across firmware, md, and zpool alike — while `type` never lies about what it natively is.
