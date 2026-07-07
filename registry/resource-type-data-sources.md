# Resource-Type Data Sources — what each infrastructure type adopts by reference

**Document Status:** 🟡 Working — design input for the infrastructure Resource Types
**Related:** [design-principles/adopted-standards.md](../design-principles/adopted-standards.md) (the
absorb/adopt disposition) · [reference/standards-catalog.md](../reference/standards-catalog.md) (the
authoritative standards list) · [registry/resource-type-spec.schema.json](resource-type-spec.schema.json)
(`spec`/`outputs`/`relationships` shape) · [docs/osac-better-together.md](../docs/osac-better-together.md)

## 1. Purpose

A new wave of infrastructure Resource Types (Compute.BareMetalHost, Storage.Cluster, Network.Gateway,
Network.AddressService, Security.DirectoryService, Facility.PowerFeed — plus Compute.VirtualMachine and
Compute.Cluster) bumps against well-established external
schemas. Per **T5 / the Adopt disposition**, UDLM should **reference industry-standard data elements
for validation and vocabulary** rather than re-express them, and remain **extensible by vendor-specific
elements** where a deployment needs them. This document records, per type, *which* standard supplies the
vocabulary and *which disposition* applies — the design input for the type specs and for new entries in
the standards catalog.

Research basis (2026-06-26): OSAC (`osac-project/fulfillment-service` protos), dcm-project
(`control-plane` service-type OpenAPI + provider contract), heatmiser (`dcm-site-ui` discovery manifest,
`dcm-dnsmasq`, `dcm-haproxy`), and the primary standards (DMTF Redfish, Metal3, Rook, ISC Kea, IETF DNS,
NUT, Kubernetes Gateway API, RFC 4512).

## 2. The disposition for a Resource Type (refining §1 of adopted-standards)

A Resource Type's **Intent** (the desired-state a consumer declares + UDLM orchestrates) is genuinely
UDLM's to custody — it is **absorbed** (that's the registry's job). But the type's **field vocabulary**
and especially its **Discovered/Realized inventory** are frequently already modeled by a standard, and
there UDLM **adopts** — references the standard's element names so validation + provenance point at the
canonical definition, and a standard rev never forces a UDLM schema change.

The clean split, worked on bare metal:
- **Intent** (provision *this* host, image, role, power target) → **absorb** into the Compute.BareMetalHost `spec`.
- **Discovered hardware** (cpu/ram/nics/disks/firmware) → **adopt** Metal3 `status.hardware` + Redfish
  `ComputerSystem` element names; do not re-express the hardware schema.

This is the same "declared-vs-observed = two projections" shape as Metal3↔Redfish, and as DHCP↔DNS over
one address allocation.

## 3. Convergence to adopt wholesale — the OSAC envelope

OSAC (`osac-project/fulfillment-service`) independently converged on the four-state shape: every resource
is `{ id, metadata, spec, status }` with `status.conditions[]` (Kubernetes-style), `OUTPUT_ONLY` outputs,
`IMMUTABLE/REQUIRED` field-behavior, and an `owner-reference` annotation = `contained_by`. This lines up
1:1 with UDLM Intent/Requested/Realized/Discovered and the `resource-type-spec.schema.json`
`spec`/`outputs`/`relationships` model. **Recommendation: adopt the OSAC envelope + field-behavior
vocabulary as the cross-cutting convention** (see [osac-better-together.md](../docs/osac-better-together.md)),
and take OSAC **VirtualMachine** (`ComputeInstance`) and **Cluster** (`ClusterSpec`) nearly verbatim.

## 4. Per-type sources & disposition

| Resource Type | Adopt (reference vocabulary) | Absorb (UDLM-owned intent) | Vendor extension |
|---|---|---|---|
| **Compute.VirtualMachine** | OSAC `ComputeInstance` (`cores`,`memory_gib`,`boot_disk`,`network_attachments[]`,`run_strategy`,`image`; status `state`+`conditions`+ips) — Tier 2 | the type itself | KubeVirt/libvirt specifics |
| **Compute.Cluster** | OSAC `ClusterSpec` (`node_sets{host_type,size}`,`release_image`,`network{pod,service cidr}`; `api_url`/`console_url`) + heatmiser day-0 VIPs/CIDRs — Tier 2 | the type | — |
| **Compute.BareMetalHost** (§4 row previously said BareMetalInstance — registry authored BareMetalHost; instance = realized entity of it) | **Metal3 `BareMetalHost`** (`bmc.address`,`bootMACAddress`,`online`,`image`,`rootDeviceHints`; `status.hardware.{cpu,ramMebibytes,nics[],storage[],firmware}`,`provisioning.state`) + **Redfish `ComputerSystem`** (`ProcessorSummary`,`MemorySummary`,`PowerState`,`Boot*`,`UUID`) + heatmiser discovery manifest — Tier 2 | provision intent (role, image, target) | iDRAC/a supported board BMC |
| **Storage.Cluster** (authored name; the Ceph-backed cluster type) | **Rook `CephCluster`** (`mon.count`,`storage`,`cephVersion.image`,`network`,`dashboard`; `status.ceph.{health,fsid}`) + native `ceph -s -f json` (`osdmap`,`pgmap`) — Tier 2 | cluster intent | — |
| **Network.Gateway** | **K8s Gateway API `Gateway`** (`gatewayClassName`,`listeners[]`,`addresses[]`) + OSAC `SecurityGroup` rule shape; NAT 5-tuple absorbed — Tier 2 | routing/NAT intent | pfSense/OPNsense |
| **Network.AddressService** | **ISC Kea `Dhcp4`** (`subnet4[]`,`pools`,`reservations[]`,`option-data`) + **DNS RRs** (RFC 1035 `A/PTR/CNAME/NS/SOA`, RFC 3596 `AAAA`) — Tier 2; *DHCP+DNS = two projections of one allocation* | the address-service intent | — |
| **Security.DirectoryService** (authored under Security, not Identity) | **RFC 4512** (`namingContexts`,`subschemaSubentry`,baseDN — already in catalog via RFC 4511) + FreeIPA (realm/KDC, CA=Dogtag, replicas) + OSAC `LdapConfig` connection facet — Tier 2 | the operated-directory intent | — |
| **Facility.PowerFeed** | **NUT** variable namespace (`ups.status` OL/OB/LB, `battery.charge`,`battery.runtime`,`battery.runtime.low`,`input.voltage`,`ups.realpower`,`ups.load`) + **Redfish `PowerSubsystem`/`PowerSupply`** (`CapacityWatts`,`InputPowerWatts`,`LineInputStatus`) — Tier 2 | which hosts a feed protects (intent) | vendor-UPS SNMP |

**Net coverage:** reusable definitions exist for all 8 types in the table (VirtualMachine, Cluster,
BareMetalHost, Gateway, and DirectoryService have OSAC/heatmiser sibling-project sources;
Storage.Cluster, AddressService, and PowerFeed reference industry standards directly). dcm-project's
service-type scope *explicitly excludes* bare metal, storage, networking, DHCP/DNS, identity, and
power/facility — so for those the adoption target is the **industry standard**, not a sibling project.

## 5. The reference + vendor-extension mechanism (already in the registry)

UDLM has the hooks to encode this without new machinery:
- **`registry/provider-adopted-standards.schema.json`** — the type/provider declares the standard it
  conforms to (the Tier-2 `adopts[]` + `adopted_standard_support` apparatus from adopted-standards §1a).
- **`spec` field annotations** — a field carries an `x-standard` pointer (e.g.
  `x-standard: "metal3:BareMetalHost.status.hardware.cpu"`) so validation + provenance resolve to the
  canonical element. Tier-1 codelists are referenced as field constraints, never enumerated.
- **`portability: portable|partial|provider-specific`** + an OSAC-style `provider_hints` block = the
  **vendor-extension slot**. Vendor-specific elements live here, marked portability-affecting, surfaced
  to policy — the model stays referenceable AND extensible (ties to the vendor/custom extension model).

## 6. New entries proposed for `reference/standards-catalog.md`

These resource-domain standards are not yet in the catalog. Proposed additions (all **Tier 2** record
schemas unless noted), to be merged into a new "Infrastructure Resource Domain Standards" section:

| Standard | Use in UDLM | Obligation |
|---|---|---|
| **DMTF Redfish** (`ComputerSystem`, `PowerSubsystem`/`PowerSupply`) | Bare-metal out-of-band inventory + power; PowerFeed telemetry | Informative |
| **Metal3 `BareMetalHost`** (metal3.io/v1alpha1) | Declarative bare-metal provision intent + discovered `status.hardware` | Informative |
| **Rook `CephCluster`** (ceph.rook.io/v1) + `ceph -s` | Ceph storage-cluster spec + health/topology status | Informative |
| **ISC Kea `Dhcp4`** | DHCP service intent (subnets/pools/reservations/options) | Informative |
| **IETF DNS** (RFC 1035, RFC 3596 AAAA) | DNS zone records (A/AAAA/PTR/CNAME/NS/SOA) | Normative for DNS records |
| **NUT variable namespace** | UPS/PowerFeed device telemetry (`ups.status`, `battery.*`, `input.*`) | Informative |
| **Kubernetes Gateway API** (gateway.networking.k8s.io/v1) | L4–L7 gateway/edge vocabulary | Informative |

(RFC 4511 LDAP and RFC 4512 directory model are already cataloged under Identity §1.1/§2.)

## 7. Source provenance & license compatibility (per SPEC-DESIGN-REQUIREMENTS §22–23)

Every adopted source carries its license + a compatibility verdict against UDLM's **Apache-2.0**.
Verdicts: `compatible-vendor` = Apache-2.0-compatible, text may even be vendored (absorb-safe);
`compatible-reference` = permissive doc/standard, reference its vocabulary freely;
`reference-only` = copyleft / file-scoped — **reference names only, do NOT vendor text/files**.
Because adoption references vocabulary (field names = facts) and never restates a source's schema, even
`reference-only` sources are safe to adopt — the verdict guards against *copying*.

| Source | License | Verdict | Note |
|---|---|---|---|
| OSAC `fulfillment-service` protos | **verify** (expected Apache-2.0) | compatible-vendor *(pending verify)* | confirm before vendoring any proto text |
| dcm-project `control-plane` | Apache-2.0 (sibling project) | compatible-vendor | |
| heatmiser `dcm-site-ui` / appliance roles | **verify** (repo license) | compatible-reference *(pending verify)* | our own ecosystem; confirm |
| DMTF Redfish schemas | DMTF permissive doc license | compatible-reference | implementation/reference permitted |
| Metal3 `BareMetalHost` | Apache-2.0 | compatible-vendor | |
| Rook `CephCluster` | Apache-2.0 | compatible-vendor | Ceph `-s` JSON keys are facts |
| ISC Kea config schema | **MPL-2.0** | **reference-only** | reference field names; don't vendor Kea source/docs |
| IETF DNS (RFC 1035 / 3596) | IETF Trust (BSD-like reuse) | compatible-reference | |
| **NUT** variable namespace | **GPL-2.0+** | **reference-only** | variable *names* are facts; don't copy NUT docs/text |
| Kubernetes Gateway API | Apache-2.0 | compatible-vendor | |
| IETF LDAP RFC 4511/4512 | IETF Trust | compatible-reference | already cataloged |
| IETF RFC 8343 (ietf-interfaces) | IETF Trust (BSD-like reuse) | compatible-reference | `lower-layer-if`/`higher-layer-if` stacking terms — facts (Hardware.NetworkInterface aggregate/bridge) |
| IEEE 802.1AX (Link Aggregation) | **IEEE (copyright)** | **reference-only** | bond/LACP *term names* only; don't copy IEEE standard text |
| IEEE 802.1Q (Bridges & Bridged Networks) | **IEEE (copyright)** | **reference-only** | bridge/VLAN *term names* only; don't copy IEEE standard text |
| IEEE 802.1AB (LLDP) | **IEEE (copyright)** | **reference-only** | Chassis ID / Port ID / System Name *TLV names* only — connects_to discovery + Network.Switch identity |
| IETF RFC 8345 (ietf-network-topology) | IETF Trust (BSD-like reuse) | compatible-reference | node / termination-point / link vocabulary — facts (Network.Switch, connects_to) |
| k8snetworkplumbingwg NetworkAttachmentDefinition | Apache-2.0 | compatible-reference | attachable-network concept (Network.VirtualNetwork) |
| libvirt network XML docs | **LGPL-2.1+** | **reference-only** | forward-mode *vocabulary* only; don't vendor libvirt docs/text |

**TODO when defining the types:** verify the three `**verify**` licenses (OSAC, heatmiser repos) and
record the confirmed value in each type's `adopts[]` entry.
