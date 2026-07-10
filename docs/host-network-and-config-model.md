# Host networking as data: adapters, IP addresses, and NetworkManager config

**Status:** proposal / mapping (not yet an ADR — I want to react to this before ratifying it).
**Driver:** I want host network facts to be first-class UDLM records so automation reads them from the
estate instead of from bespoke per-tool lists. The immediate trigger is small and concrete: I swapped the
motherboard in `vis`, so its NIC has a new MAC, and I want to reassign its reserved IP `10.0.0.91` by
editing an estate record — then have Kea render its DHCP reservation *from* that record rather than from a
hand-maintained list in Ansible. The general goal is bigger: model the adapter, its MAC, its IP, and its
NetworkManager settings once, and let Kea, `configure_host_macvlans`, `safe_net_change`, and OpenShift all
consume the same source of truth.

## What has to be modeled

Three things, and the relationship between them:

1. **The ethernet adapter / port**, carrying its **MAC** — physical NICs *and* logical interfaces
   (macvlan, VLAN, bond, bridge).
2. **The IP address as its own record**, depending on an adapter — including static reservations.
3. **The NetworkManager-style config** (addressing method, routes, DNS, bond/bridge/VLAN membership) as a
   declarative resource that attaches to an adapter/port.

## Prior art — and it converges

I had the standards surveyed. The load-bearing result is that three independent, truly-open standards
agree on the shape, which is the strongest signal I can ask for before committing.

| Standard | Adapter + MAC | IP | Config as its own object | License | RH alignment |
|---|---|---|---|---|---|
| **IETF RFC 8343 `ietf-interfaces` + RFC 8344 `ietf-ip`** | `interface` keyed by name; MAC = `phys-address`; `type` identityref (ethernet/lag/l2vlan/bridge) | **separate keyed `address` list**; key `ip`; `prefix-length`; **`origin` = static/dhcp/link-layer/random** | config/state unified (NMDA) | Simplified BSD | normative substrate; NMstate derives from it |
| **NMstate** (nmstate.io) | `interfaces[]` keyed by name; `mac-address`; `type` ethernet/vlan/bond/linux-bridge/mac-vlan | `ipv4`/`ipv6` → `address:[{ip, prefix-length}]` + `enabled`/`dhcp`/`autoconf` | **yes** — the desired-state doc = NNCP `spec.desiredState` | **Apache-2.0** | **Red Hat project**; RHEL `network` role backend; OpenShift Kubernetes-NMState operator |
| **NetBox DCIM/IPAM** | `Device`→`Interface`; **MACAddress a first-class object** (4.2); `primary_mac_address` | **separate `IPAddress` record** (CIDR, `status`, `role`) assigned to the interface by reference | interface holds `mode`/`parent`/`bridge`/`lag` inline (state-of-record) | **Apache-2.0** | RH-certified `netbox.netbox` collection + AAP inventory |
| DMTF **Redfish** `EthernetInterface` | `MACAddress` / `PermanentMACAddress` | embedded `IPv4Addresses[]` `{Address, SubnetMask, Gateway, AddressOrigin}` | config = the resource | BSD-3 schemas | Metal3/Ironic BMC standard |
| DMTF **CIM** | `NetworkPort.PermanentAddress` → `LANEndpoint.MACAddress` → `IPProtocolEndpoint` | fully normalized, one IP per instance | association classes | BSD-3 | legacy (superseded by Redfish at RH) |

Three convergences matter:

- **An IP is a small object with `{address, prefix, origin}`, and static-vs-DHCP is a *field on that
  object*, not a separate type.** RFC 8344, NMstate, and Redfish all land here independently.
- **VLAN/bond/bridge children reference their parent/members by identifier**, not by nesting (RFC 8343
  `lower-layer-if`, NMstate `base-iface`/`port[]`, NetBox `parent`/`bridge`/`lag`). This is already how
  UDLM models it: `parent_device` (1→N) / `lower_layer` (N→1), from #267.
- **MAC is an attribute of the L2 port**, separable from the physical device (CIM, Redfish
  `PermanentMACAddress` vs `MACAddress`, NetBox's first-class MACAddress).

## Recommended UDLM model

UDLM already carries most of this. The mapping reuses existing types and adds exactly one, per the
adopt-by-reference methodology (`design-principles/adopted-standards.md`).

### 1. Adapter + MAC → reuse `Hardware.NetworkInterface` (no change)
It already has `device_class`, `partition_mechanism`, `aggregation`, `bridge`, `identity`, `mtu`,
`vlan_id`, the `parent_device`/`lower_layer` stacking edges, and **`mac_address` as an output**. This is
the "ethernet adapter resource" Chris means, and it already covers macvlan/VLAN/bond/bridge. I'd keep MAC
as an attribute of the adapter for now (our fleet is one-MAC-per-adapter); note that NetBox's separate
MACAddress record is the blessed escalation path *if* we ever need permanent-vs-assigned or multi-MAC.

### 2. IP → reuse `Network.IPAddress` as a **dependent record** (Chris's "IPaddress record dependency")
`Network.IPAddress` already exists (`family`, `allocation` → `address`). Model each address as its own
record with a `depends_on` (or `references … relation: assigned_to`) edge to its `Hardware.NetworkInterface`.
Field shape follows the RFC 8344/NMstate convergent form (`address` CIDR + `allocation` as the `origin`
discriminator). **A static DHCP reservation is just `allocation: static`** bound to an interface — not a
new type. This matches RFC 8344 `origin=static`, NetBox `status=reserved`, Redfish `AddressOrigin=Static`.

### 3. NetworkManager config → **one new type, adopting NMstate by reference (Tier 2)**
This is the only gap. Add a config resource (working name **`Network.ConnectionProfile`** / `Config.HostNetwork`)
whose body **conforms to the NMstate interface schema** rather than re-inventing fields: `state`,
`ipv4`/`ipv6` (`enabled`/`dhcp`/`autoconf`/`address[]`), the type sub-objects (`vlan{base-iface,id}`,
`link-aggregation{mode,port[]}`, `bridge{port[]}`, `mac-vlan{base-iface,mode}`), plus `routes.config[]`
and `dns-resolver.config`. It attaches to an adapter by handle (`references … relation: configures`).
Per the adoption litmus ("if the standard shipping a new version forces a UDLM schema change, you
absorbed it") this is a **Tier 2 adopt**: UDLM owns identity + the conformance pointer, NMstate owns the
body. It is net-negative — it supersedes the bespoke `host_macvlan`/`host_network`/`safe_net_change`
Ansible vars — and it maps 1:1 to OpenShift `NodeNetworkConfigurationPolicy.spec.desiredState` for free.

### 4. DHCP reservations → a projection, not a hand-list
Today `Network.DHCPScope.reservations` is an inline array and the truth lives in Ansible
`group_vars/dhcp_servers.yml`. Instead: **a reservation is derived** from every `Network.IPAddress` with
`allocation: static` that is bound to a `Hardware.NetworkInterface` (which carries the MAC), contained by a
host (which gives the hostname). Kea — which *is* a `Network.AddressService` in the model — renders its
reservations from that set. `Network.DHCPScope.reservations` becomes a computed projection of the estate,
so "Kea stores its records in UDLM format" is satisfied by construction.

## Data · Policy · Provider

- **Data** — `Hardware.NetworkInterface` (adapter + MAC), `Network.IPAddress` (the address, dynamic or
  static), `Network.ConnectionProfile` (desired config), `Network.DHCPScope`/`Network.AddressService`
  (the DHCP surface). Bindings are dependency edges; identity is uuid/handle.
- **Policy** — which addresses are static vs pool; which pool an address allocates from
  (`ownership-sharing-allocation.md` IPAddressPool→IPAddress); reservation constraints (never hand out a
  reserved IP); who may own/allocate an address (tenant).
- **Provider** — Kea (`Network.AddressService`) realizes reservations + leases from the Data under Policy;
  NetworkManager (via Ansible/`safe_net_change`, later Kubernetes-NMState) realizes `ConnectionProfile`
  onto the host and reports back discovered MAC/address; the DHCP generator is the read-side provider that
  renders Kea config from the estate.

## Applied to `vis` (the concrete case)

1. `vis` — a `Compute.BareMetalHost` record (workstation role). *Not modeled yet.*
2. `vis-eth0` — a `Hardware.NetworkInterface`, `contained_by: vis`, `mac_address: <new MAC>`.
3. `vis-ip-10-0-0-91` — a `Network.IPAddress`, `allocation: static`, `address: 10.0.0.91/24`,
   `depends_on: vis-eth0`. **This record is the reservation.**
4. (optional now) `vis-eth0-profile` — a `Network.ConnectionProfile` (NMstate body) `configures: vis-eth0`.
5. Kea renders `{mac: <new>, ip: 10.0.0.91, hostname: vis}` from #2–#3; the old MAC disappears when the
   record changes. Same edit reassigns the IP on any future motherboard swap.

## Decisions taken (2026-07-09)

- **MAC placement — DECIDED:** MAC stays an attribute of the ethernet-adapter resource
  (`Hardware.NetworkInterface`), not a separate record. (A separate NetBox-style MACAddress record
  remains the escalation path if multi-MAC / permanent-vs-assigned is ever needed.)
- **Config type — DECIDED:** adopt **NMstate as the whole body** of the config resource (Tier-2
  adopt-by-reference: UDLM owns identity + the conformance pointer, NMstate owns the body). Not just its
  vocabulary.
- **Coverage — DECIDED:** all of Kea's reservation records live in UDLM format (fleet + IoT) — "Kea stores
  its records in UDLM format." `Network.DHCPScope.reservations` becomes a projection of the estate.

## Still open

- **Config type name:** `Network.ConnectionProfile` vs `Config.HostNetwork` vs other; and its exact
  attachment relation to the adapter (`configures`).
- **Reservation rendering:** a generator tool in `roadfeldt-dcm/tools/` that emits Kea reservations (fits
  the repo idiom — `shutdown_order.py`, `provenance.py`), with a byte-for-byte parity check against
  today's `dhcp_servers.yml` before Kea is switched to consume it (this touches live DHCP). Built as its
  own reviewed PR after this proposal is ratified.

## Ties
#267 (host-network model: `parent_device`/`lower_layer`, `device_class`), `Network.IPAddress` +
`Network.DHCPScope` + `Network.AddressService` (existing types), `ownership-sharing-allocation.md`
(IPAddressPool→IPAddress allocation), `design-principles/adopted-standards.md` (Tier-2 adopt-by-reference),
and the Kea DHCP estate in `roadfeldt-ansible` + `roadfeldt-dcm`.
