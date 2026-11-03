# Host networking as data: adapters, IP addresses, and NetworkManager config

**Status:** Accepted — row 023 of the [decisions register](../adr/README.md) (host networking as data: adopt NMstate and RFC 8344 for the addressing family). This doc owns the mapping and worked-example detail; the row owns the decision.
**Driver:** I want host network facts to be first-class UDLM records so automation reads them from the
estate instead of from bespoke per-tool lists. The immediate trigger is small and concrete. When a host's
motherboard is swapped its NIC gets a new MAC, and its reserved IP (say `192.0.2.91`) should be
reassignable by editing one estate record. A DHCP provider then renders its reservation *from* that
record rather than from a hand-maintained list. The general goal is bigger: model the adapter, its MAC, its
IP, and its NetworkManager settings once, and let the DHCP provider, the host-network automation, and
OpenShift all consume the same source of truth.

## What has to be modeled

Three things, and the relationship between them:

1. **The ethernet adapter / port**, carrying its **MAC** — physical NICs *and* logical interfaces
   (macvlan, VLAN, bond, bridge).
2. **The IP address as its own record**, depending on an adapter — including static reservations.
3. **The NetworkManager-style config** (addressing method, routes, DNS, bond/bridge/VLAN membership) as a
   declarative resource that attaches to an adapter/port.

## Prior art — and it converges

The load-bearing result of a standards survey is that three independent, truly-open standards agree on
the shape, which is the strongest signal I can ask for before committing.

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
  UDLM models it: `parent_device` (1→N) / `lower_layer` (N→1), from issue #267 (the host-network model).
- **MAC is an attribute of the L2 port**, separable from the physical device (CIM, Redfish
  `PermanentMACAddress` vs `MACAddress`, NetBox's first-class MACAddress).

## Recommended UDLM model

The mapping reuses existing types and adds exactly one, per the adopt-by-reference methodology
(`docs/spec/principles/adopted-standards.md`).

### 1. Adapter + MAC → `NetworkInterface` (no change)
It carries `device_class`, `partition_mechanism`, `aggregation`, `bridge`, `identity`, `speed`, `mtu`,
`vlan_memberships`, the `parent_device`/`lower_layer` stacking references, and **`mac_address` as an
output**. This is the ethernet adapter resource, and it covers macvlan/VLAN/bond/bridge. MAC stays an
attribute of the adapter (one MAC per adapter is the common case); NetBox's separate MACAddress record
is the escalation path *if* permanent-vs-assigned or multi-MAC is ever needed.

### 2. IP → `IPAddress` as a **dependent record**
`IPAddress` carries `address`, `ip_family` and `allocation`. Model each address as its own
record with a `depends_on` (or `references … relation: attaches_to`) edge to its `NetworkInterface`.
Field shape follows the RFC 8344/NMstate convergent form (`address` CIDR + `allocation` as the `origin`
discriminator). **A static DHCP reservation is just `allocation: static`** bound to an interface — not a
new type. This matches RFC 8344 `origin=static`, NetBox `status=reserved`, Redfish `AddressOrigin=Static`.

### 3. NetworkManager config → **`ConnectionProfile`, adopting NMstate by reference (Tier 2)**
This is the one added type (`registry/classes/resource/network/connection-profile/_base.yaml`). Its body
**conforms to the NMstate interface schema** rather than re-inventing fields: `state`,
`ipv4`/`ipv6` (`enabled`/`dhcp`/`autoconf`/`address[]`), the type sub-objects (`vlan{base-iface,id}`,
`link-aggregation{mode,port[]}`, `bridge{port[]}`, `mac-vlan{base-iface,mode}`), plus `routes.config[]`
and `dns-resolver.config`. It attaches to an adapter by handle (`references … relation: configures`).
Per the adoption litmus ("if the standard shipping a new version forces a UDLM schema change, you
absorbed it") this is a **Tier 2 adopt**: UDLM owns identity + the conformance pointer, NMstate owns the
body. It is net-negative — it supersedes bespoke per-tool host-network vars — and it maps 1:1 to
OpenShift `NodeNetworkConfigurationPolicy.spec.desiredState` for free.

### 4. DHCP reservations → a projection, not a hand-list
**A reservation is derived** from every `IPAddress` with `allocation: static` that is bound to a
`NetworkInterface` (which carries the MAC), contained by a host (which gives the hostname). A DHCP
provider (e.g. Kea) realizing `AddressService` renders its reservations from that set.
`DHCPScope.reservations` is a derived output, a computed projection of the estate, never authored. So
"the DHCP provider's records live in UDLM format" is satisfied by construction — whichever provider.

## Data · Policy · Provider

- **Data** — `NetworkInterface` (adapter + MAC), `IPAddress` (the address, dynamic or
  static), `ConnectionProfile` (desired config), `DHCPScope`/`AddressService`
  (the DHCP surface). Bindings are dependency edges; identity is uuid/handle.
- **Policy** — which addresses are static vs pool; which pool an address allocates from
  (`ownership-sharing-allocation.md` IPAddressPool→IPAddress); reservation constraints (never hand out a
  reserved IP); who may own/allocate an address (tenant).
- **Provider** — a DHCP address service (e.g. Kea, `AddressService`) realizes reservations + leases
  from the Data under Policy; NetworkManager (via Ansible, later Kubernetes-NMState) realizes
  `ConnectionProfile` onto the host and reports back discovered MAC/address; the DHCP generator is the
  read-side provider that renders provider config from the estate.

## Applied to a host (worked example)

1. `host-a` — a `Machine.BareMetalHost` record (workstation role).
2. `host-a-eth0` — a `NetworkInterface`, `contained_by: host-a`, `mac_address: <new MAC>`.
3. `host-a-ip` — a `IPAddress`, `allocation: static`, `address: 192.0.2.91/24`,
   `depends_on: host-a-eth0`. **This record is the reservation.**
4. (optional now) `host-a-eth0-profile` — a `ConnectionProfile` (NMstate body) `configures: host-a-eth0`.
5. The DHCP provider renders `{mac: <new>, ip: 192.0.2.91, hostname: host-a}` from #2–#3; the old MAC
   disappears when the record changes. Same edit reassigns the IP on any future motherboard swap.

## Decisions

- **MAC placement:** MAC stays an attribute of the ethernet-adapter resource
  (`NetworkInterface`), not a separate record. (A separate NetBox-style MACAddress record
  remains the escalation path if multi-MAC / permanent-vs-assigned is ever needed.)
- **Config type:** adopt **NMstate as the whole body** of the config resource (Tier-2
  adopt-by-reference: UDLM owns identity + the conformance pointer, NMstate owns the body). Not just its
  vocabulary.
- **Config type name:** `ConnectionProfile`, attaching to the adapter via
  `references … relation: configures`.
- **Coverage:** all of a DHCP provider's reservation records live in UDLM format — "Kea stores
  its records in UDLM format." `DHCPScope.reservations` is a projection of the estate.

## Still open

- **Reservation rendering:** a generator tool in the estate's control-plane tooling that emits
  DHCP-provider reservations from the estate. Before the provider is switched to consume it, a
  byte-for-byte parity check against the existing hand-maintained reservation list is run, because this
  touches live DHCP. It is built as its own reviewed PR.

## Ties
#267 (host-network model: `parent_device`/`lower_layer`, `device_class`), `IPAddress` +
`DHCPScope` + `AddressService` (existing types), `ownership-sharing-allocation.md`
(IPAddressPool→IPAddress allocation), `docs/spec/principles/adopted-standards.md` (Tier-2 adopt-by-reference),
and the DHCP estate in the estate's Ansible + DCM repos.
