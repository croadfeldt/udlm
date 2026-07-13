# Worked example — a VM, end to end, and the intermediary resources it surfaces

**What this settles:** a concrete trace of one VM request from intent to realized, naming **every** resource and relationship — so we can see which intermediary types the model actually needs. The headline: the **vNIC is not a new type** (`Hardware.NetworkInterface` with `device_class: virtual`), and VLAN is a foundational **`Network.VLAN`** shared reference (like `Facility.Location`), not an inline field. This grounds ADR-009 (fulfillment), `foundational-resources.md` (selections), and the P1 VM enrichment in a real flow.

## The request

A consumer submits a catalog item `vm-service` — `consumer_fields`: `location_ref`, `network_ref`, `disk_size`. Their intent:

```yaml
catalog_ref: vm-service
location_ref: fac-rack3      # selects an existing Facility.Location
network_ref:  net-dmz        # selects an existing Network.VirtualNetwork
disk_size:    100Gi
```

Intent carries **no** IP, vNIC, host, or volume — none exist yet. It carries **selections of foundational resources** (`fac-rack3`, `net-dmz`) and VM-owned knobs.

## The resources (intent → realized)

**Foundational (pre-existing, selected — `foundational-resources.md`):**

| handle | type | how it got here |
|---|---|---|
| `fac-rack3` | `Facility.Location` | platform data layer / facilities provider |
| `net-dmz` | `Network.VirtualNetwork` (`forward_mode: bridge`) | platform layer / network provider; `references net-vlan-20` |
| `net-vlan-20` | `Network.VLAN` (`encapsulation: vlan`, `segment_id: 20`) | network/fabric provider — the shared segment `net-dmz` and `br0@host-a` ride |
| `pool-fast` | `Storage.Pool` | storage provider |
| `host-a` | `Compute.BareMetalHost` (the hypervisor) | discovered; `contained_by fac-rack3` |
| `br0@host-a` | `Hardware.NetworkInterface` `device_class: bridge`, vlan_membership→`net-vlan-20` (tagged) | the host bridge carrying the DMZ VLAN (the OVN-localnet path) |

**Created by realization (provider-reported, ADR-009 / provider-contract §1b):**

| handle | type | key relationships |
|---|---|---|
| `vm-app` | `Compute.VirtualMachine` | `contained_by host-a` · `references fac-rack3` (placement) · `references net-dmz` (attachment) |
| `vnic-app-eth0` | **`Hardware.NetworkInterface` `device_class: virtual`**, vlan_membership→`net-vlan-20` | `contained_by vm-app` · `references net-dmz` · `parent_device br0@host-a` (rides the host bridge) |
| `ip-app` (192.0.2.55) | `Network.IPAddress` | `attaches_to vnic-app-eth0` — allocated by the network/IPAM provider |
| `vol-app` (100Gi) | `Storage.Volume` | `provisioned_by pool-fast` · `attaches_to vm-app` |

That is the **entire** graph for one VM: 4 foundational + 4 realized resources, 9 typed edges. Every one resolves to an existing resource type.

## The fulfillment modes at play (ADR-009)

- **placement** (`fac-rack3`) — **consumer** selection of a foundational resource; DCM checks eligibility by policy.
- **network attachment** (`net-dmz`) — **consumer** selection; the **vNIC + IP** are then **platform/provider** fulfilled: `ip_mode: dynamic` → the network provider allocates `ip-app` and reports it back (realized relationship, provider-authoritative).
- **disk** — **platform** fulfilled: DCM provisions `vol-app` from `pool-fast` from `disk_size`.

## The intermediary types — what we actually need

1. **vNIC — already covered, do NOT add `Hardware.VirtualInterface`.** A virtual NIC is `Hardware.NetworkInterface` with `device_class: virtual` (the enum already has `virtual | passthrough | bridge | aggregate | partition`). It carries `vlan_id` and stacks on the host bridge via `parent_device` — exactly the physical/bond/bridge/virtual stack the estate already models. Adding a parallel `Hardware.VirtualInterface` would duplicate it (minimal-surface: reject).

2. **VLAN — a foundational reference, like `Facility.Location` (settled).** A VLAN/segment is **not** an inline field; it is a first-class **`Network.VLAN`** foundational resource, owned/advertised by a network/fabric provider (or a platform data layer) and **selected by reference** — a shared reference serving the information/operational layer. `net-dmz` (Network.VirtualNetwork) `references net-vlan-20` (`Network.VLAN`, `encapsulation: vlan`, `segment_id: 20`); the vNIC rides that segment via the network it attaches to. One source of truth for the segment, referenced by every resource on it — so blast-radius and dependency reasoning traverse it. (A provider may offer a `Network.Port` variant; the org ratifies which — base guidance, not a mandate.)

3. **Everything else exists** — VM, Location, VirtualNetwork, IPAddress, Volume, Pool, BareMetalHost, and the bridge/virtual NetworkInterface stack.

## The full lifecycle — where the rest of the shared references surface

Provisioning shows the storage/network/placement roots. The **operational lifecycle** is where the others appear — identity, DNS, credentials, time, telemetry, backup — each a shared reference with an owner. Walking all six phases roots them out:

| Phase | What happens | Shared references it introduces (owner) |
|---|---|---|
| **1. Provision** (`new_request`) | select foundational roots, provider allocates the rest | `Facility.Location` (facilities), `Network.VLAN`/`Network.VirtualNetwork` (network), `Network.IPAddress` (IPAM), `Storage.Pool`→`Storage.Volume` (storage), `Compute.BareMetalHost` (compute/hypervisor) |
| **2. Operate** (running) | the VM serves; steady-state dependencies bind | `Security.DirectoryService` realm — identity/auth (identity provider, scope-derived from `tenant_uuid`); **`Network.DNSZone`** record — name→IP (DNS provider); `Security.CredentialRef` — secrets (credential/secrets provider); **time-sync** capability (ADR-005, provider-attested); **observability sink** — logs/metrics (observability provider); `Facility.PowerFeed` via the host (facilities — the fault-domain anchor) |
| **3. Modify** (`modification`) | add a NIC / resize / re-home | new `Network.VirtualNetwork`+`IPAddress` refs; new `Storage.Volume` from the same `Storage.Pool`; the provider re-reports the changed realized relationships |
| **4. Drift** (`drift_detection`) | discovered ≠ realized (an out-of-band IP change, a moved disk) | reconciles the VM's references against the **same shared resources** — the roots are the truth the drift is measured against |
| **5. Rehydrate** (`rehydration_*`) | **replay the original intent** + migrate data per dependency | rehydration-from-intent **re-requests the captured intent** (rebuilds the resources + relationships, `uuid` preserved) **and activates the DR / data-migration process for each target resource** to bring its data across — not backup-restore-only. `IPAddress`/host/vNIC **remapped** (soft refs); `Location`/`VLAN`/`VirtualNetwork` **re-selected** (may differ in provider-portable mode); **`DNSZone` record remapped to the new IP**; each dependency's data migrated by its owning provider's DR path (the model must not restrict this to a single mechanism) |
| **6. Decommission** (`decommission`) | teardown in reverse dependency order | **the shared roots are NOT torn down** — `Location`, `VLAN`, `Pool`, realm, DNS zone are shared and survive; only the VM's *references* release (IP back to IPAM, volume detached — data retained per policy, DNS record withdrawn). This is the proof the model is right: killing the VM releases references, it does not delete the shared resources others depend on. |

## Shared resources & likely owners (the catalog this roots out)

Every shared/foundational resource a VM touches across its whole life, and who owns it — the reference-and-owner map to build against:

| Shared resource | Type | VM references it as | Likely owner (provider) | Foundational? |
|---|---|---|---|---|
| Location | `Facility.Location` | placement (`references`) | facilities / DC | ✔ |
| VLAN / segment id | `Network.VLAN` | segment (`references`, via the network) | network / fabric | ✔ |
| Virtual network | `Network.VirtualNetwork` | attachment (`references`) | network | ✔ |
| IP address | `Network.IPAddress` | `binds_to` (dynamic/static/byo) | IPAM | ✔ |
| DNS record/zone | `Network.DNSZone` | name→IP (operate; remap on rehydrate) | DNS | ✔ |
| Storage pool | `Storage.Pool` / `Storage.Cluster` | volume source | storage | ✔ |
| Volume | `Storage.Volume` | disk (`attaches_to`) | storage | — (consumable) |
| Hypervisor host | `Compute.BareMetalHost` | `contained_by` (placement result) | compute / hypervisor (libvirt, OCP) | ✔ |
| Realm / identity | `Security.DirectoryService` | auth (scope-derived from `tenant_uuid`) | identity (e.g. FreeIPA) | ✔ |
| Secret | `Security.CredentialRef` | `references` (never inline) | credential / secrets | ✔ |
| Power feed | `Facility.PowerFeed` | via the host's PSU (fault domain) | facilities | ✔ |
| Time sync | (ADR-005 capability) | clock discipline | provider-attested per profile | — (capability) |
| Telemetry sink | observability provider surface | logs/metrics | observability | ✔ |
| Backup / DR target | `Storage.*` | data replication (rehydrate) | backup / DR | ✔ |

**What this tells us for September:** the roots are almost all already typed (`Facility.Location`, `Network.VLAN` (new), `Network.VirtualNetwork`, `Network.IPAddress`, `Network.DNSZone`, `Storage.Pool`, `Security.DirectoryService`, `Security.CredentialRef`, `Facility.PowerFeed`, `Compute.BareMetalHost`). The gaps are **capacity/inventory advertisement** on their owning providers (September P3 — every ✔ owner must advertise what it offers so placement can select) and **quota** on consumption (P7). No new resource *types* fall out of the full lifecycle — only the provider-advertisement + eligibility surface around the roots already named here.

## Gaps this example confirms (feeds the September plan)

- **`Network.VLAN`** — created as a foundational shared reference (owned by a network/fabric provider, selected by reference like `Facility.Location`); `Network.VirtualNetwork references Network.VLAN`. No inline encapsulation field.
- **P1 already landed** the VM `networks[].network_ref` + `placement.location_ref` selections this trace relies on.
- **P4 fault domain** shows up literally: `vm-app` and every other guest on `host-a` share `host-a`'s fault domain, and everything in `fac-rack3` shares the rack's — derived from these `contained_by`/`references` edges (ADR-010), no new authoring.

**Net:** the model realizes a full VM with **no new intermediary types** — `device_class: virtual` covers the vNIC — and VLAN modeled as a `Network.VLAN` shared reference, consistent with every other foundational resource.
