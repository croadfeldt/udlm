# UDLM ADR-036: Storage selection is requirements-based (not a native-class reference)

**Status:** Accepted (croadfeldt upstream) — an application of ADR-037 (PVD)
**Date:** 2026-07-21
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)
**Related:** ADR-035 (reference-vocabulary portability); ADR-004 (capability declaration); ADR-029 (discovery);
core-tenets **T2** (transformation is Policy) / **T5** (adopt, don't re-express); ADR-008 (naturalization
boundary); ADR-037 (PVD)

**Settles:** storage selection is **requirements-based**, not a reference to a (Kubernetes-native) storage class.

## Context
A reference to `Platform.StorageClass` is the obvious first move — but pressed on portability (*is that
spec portable across bare-metal / VMs?*), the answer is **no**. `Platform.StorageClass` `adopts: Kubernetes` and
carries `provisioner` (a CSI driver id), `volume_binding_mode` (PVC binding), `parameters` (CSI params),
`reclaim_policy` — all k8s/CSI-native; only its `capabilities` block (`iops`, `throughput_mbps`, `encryption`,
`replication_factor`, `snapshot_support`) is vendor-neutral. Bare-metal (LVM/ZFS/SAN/NFS) has no CSI provisioner;
a VM's storage (vSphere datastore, oVirt storage domain, libvirt pool) isn't a storage class at all. So a
portable VM/volume that *references* `Platform.StorageClass` drags k8s into the substrate — the same leak as
re-expressing an adopted standard inline (PVD-002).

## Decision
1. **Storage selection is requirements-only.** `disks[].storage` is a **requirements descriptor** — capability
   minima the provider MATCHES to a native backing: `tier` (neutral codelist), `min_iops`, `min_throughput_mbps`,
   `min_replication`, `encryption`, `snapshot`. The fields mirror `Platform.StorageClass.capabilities`, so request
   and advertisement speak one language. **No named-class-reference arm** — a named class is inherently
   vendor-specific and does not port.
2. **The chosen native class is a realized fact, not intent.** The provider records which native backing it
   selected in an output (`outputs.storage_backing` — a k8s SC name, a datastore, a ZFS dataset). Captured,
   auditable, vendor-specific — never in the portable intent.
3. **`Platform.StorageClass` is honestly a k8s realization type** (it `adopts: Kubernetes`). It stays valid as a
   k8s provider's advertised/discovered vocabulary; it is simply **not referenced by portable intent**.

## Data · Policy · Provider
- **Data** — the requirements descriptor (portable); the realized `storage_backing` (provider fact).
- **Policy** — the requirements→backing **match** is DCM (T2).
- **Provider** — advertises capabilities; naturalizes to native storage (CSI class, datastore, ZFS pool).

## Options considered
- **(A)** Named-class reference only. *Rejected* — forces vendor knowledge on the consumer; not portable.
- **(B)** `oneOf { class reference | requirements }`. *Rejected* — the reference arm targets a k8s-native type,
  re-opening the portability leak even when the requirements arm exists; the escape hatch becomes the norm.
- **(C) [chosen]** Requirements-only, with the realized native class recorded as an output.

## Consequences
- **Sharpens PVD-001's selection rule:** *reference* when the vocabulary is itself portable (`os_image` with a
  standard identity, ADR-035); *requirement* when the candidate set is inherently vendor-native (storage classes);
  *codelist* for a small neutral enum. Not everything should be a reference — this is the discriminator.
- Defines a reusable **requirements descriptor** pattern (compute tiers, network QoS can reuse it).
