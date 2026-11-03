# Storage provisioning — pool → dataset → volume / share (the flow)

**What this settles:** how the storage family composes into one implementation. A **pool** yields capacity;
a **dataset** (a `Volume.ZFS`) carves a bounded, policied slice of it; a **volume** or **file share** exposes
that slice to a consumer. A **lighter** flow: it **builds on [request-realization](request-realization.md)**
and [uc-06-persistent-volume-provision](uc-06-persistent-volume-provision.md) (the single-volume case). It
documents only what the *chain* adds: the ordered dependency and its failure branches.

> **Use Cases:** `storage/provision-volume-bound-to-pool`, `storage/provision-dataset-with-quota-compression`,
> `storage/composite-fileshare-backed-by-pool-dataset` (positive); `storage/volume-request-exceeds-quota-refused`,
> `storage/dataset-parent-pool-missing-refused`, `storage/fileshare-export-to-unauthorized-principal-refused`
> (must-reject). **Persona:** platform-engineer · **Profiles:** dev / prod.

**In one breath.** A pool declares capacity as a requirements floor (tier, IOPS, throughput, never a native
class; ADR-036). A dataset reserves a bounded slice with a quota and properties, operationally dependent on
its pool. A volume or file share exposes that slice to an authorized consumer. The chain realizes bottom-up,
each link an **operational dependency** on the one below. A missing pool refuses the dataset, an over-quota
request refuses the volume, an out-of-scope principal refuses the share, each naming the root cause
(ADR-052).

## The flow

```mermaid
flowchart TD
    A["Request: file share / volume<br/>over a dataset over a pool"] --> B{"Pool present + capacity<br/>meets the requirements floor?"}
    B -->|no pool / unrealizable| B1["Refuse dataset — name the missing<br/>parent pool (operational dependency)"]
    B -->|yes| C["Reserve dataset slice<br/>quota + properties, ADR-011 reserve-not-activate"]
    C --> D{"Requested size ≤ pool<br/>available / quota?"}
    D -->|exceeds| D1["Refuse volume — name the<br/>quota constraint + resolution"]
    D -->|fits| E{"Consumer principal within<br/>authorized directory scope?"}
    E -->|out of scope| E1["Refuse share export —<br/>name the unauthorized principal"]
    E -->|authorized| F["Realize volume / share<br/>bind to dataset, decrement quota"]
    F --> G["Record implementation + the<br/>pool→dataset→share chain"]
```

## What the chain adds over the single-volume case

- **An ordered operational dependency** — share **depends_on** dataset **depends_on** pool. Implementation is
  bottom-up, and each link cascades its failure upward, naming the *root* (ADR-052), never a bare field.
- **Requirements-floor capacity, not a native tier** — the pool's tier is a named requirements bundle
  (min_iops, min_throughput), name-selectable but requirements-authoritative (ADR-036). Portability is
  retained across providers that meet the floor.
- **Three distinct refusals, three roots** — missing parent (dataset), quota exceeded (volume), unauthorized
  principal (share). Each is a must-reject with a resolution, not a silent partial.

## What UDLM does not decide

Which provider backs the pool (ZFS, Ceph, an array), and how it naturalizes a quota or an export into native
form (the naturalization boundary, DCM ADR-023). The give-up bound on a transiently unrealizable link: the
convergence window is control-plane policy (ADR-052). UDLM defines the resource shapes, the
operational-dependency chain, the requirements-floor capacity contract, and the surfacing contract. The
control plane places, reserves, and realizes.

## Where each piece is specified

| Piece | Contract |
|---|---|
| Requirements-floor capacity (tier = named requirements, not native class) | ADR-036 |
| Operational dependency, root-cause surfacing, reserve-not-activate | ADR-052 / ADR-011 |
| The resource shapes + their examples | `registry/generated/storage-pool.json`, `volume.json`, `volume.zfs.json`, `file-share.json`, `storage-class.json` (`spec_examples`; register row 055) |
| Corpus | `use-cases/storage/`, `use-cases/storage-redundancy/` |
