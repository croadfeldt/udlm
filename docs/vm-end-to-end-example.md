# Worked example — a VM, end to end, and the intermediary resources it surfaces

**What this settles:** a concrete trace of one VM request from intent to realized, naming **every** resource and relationship — so we can see which intermediary types the model actually needs. The headline: the **vNIC is not a new type** (`Hardware.NetworkInterface` with `device_class: virtual`), and the only genuine intermediary decision is **how VLAN/encapsulation is modeled**. This grounds ADR-009 (fulfillment), `foundational-resources.md` (selections), and the P1 VM enrichment in a real flow.

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
| `net-vlan-20` | `Network.VLAN` (`encapsulation: vlan`, `segment_id: 20`) | network/fabric provider — the shared segment `net-dmz` and `br0@kenny` ride |
| `pool-fast` | `Storage.Pool` | storage provider |
| `host-kenny` | `Compute.BareMetalHost` (the hypervisor) | discovered; `contained_by fac-rack3` |
| `br0@kenny` | `Hardware.NetworkInterface` `device_class: bridge`, `vlan_id: 20` | the host bridge carrying the DMZ VLAN (the OVN-localnet path) |

**Created by realization (provider-reported, ADR-009 / provider-contract §1b):**

| handle | type | key relationships |
|---|---|---|
| `vm-app` | `Compute.VirtualMachine` | `contained_by host-kenny` · `references fac-rack3` (placement) · `references net-dmz` (attachment) |
| `vnic-app-eth0` | **`Hardware.NetworkInterface` `device_class: virtual`, `vlan_id: 20`** | `contained_by vm-app` · `references net-dmz` · `parent_device br0@kenny` (rides the host bridge) |
| `ip-app` (10.0.20.55) | `Network.IPAddress` | `attaches_to vnic-app-eth0` — allocated by the network/IPAM provider |
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

## Gaps this example confirms (feeds the September plan)

- **(a) `Network.VirtualNetwork.encapsulation`** — small additive field (the VLAN decision above). *Recommend adding as base guidance.*
- **P1 already landed** the VM `networks[].network_ref` + `placement.location_ref` selections this trace relies on.
- **P4 fault domain** shows up literally: `vm-app` and every other guest on `host-kenny` share `host-kenny`'s fault domain, and everything in `fac-rack3` shares the rack's — derived from these `contained_by`/`references` edges (ADR-010), no new authoring.

**Net:** the model realizes a full VM with **no new intermediary types** — `device_class: virtual` covers the vNIC — and one small, org-ratifiable encapsulation decision on `Network.VirtualNetwork`.
