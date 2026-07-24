# Type catalog — every resource type, in plain English

> GENERATED from the `context` blocks in `registry/resource-types/` by
> `registry/tools/generate_type_catalog.py` — edit the spec, regenerate, never edit here.
> Missing entries are types without a `context` block yet (tracked by the rule-36 gate).

## Automation

### Automation.Job (0.4.0)

**Purpose:** Makes an automation job (playbook, pipeline, script) a first-class node in the dependency graph, so what the job needs stays up while it runs.

A record of a job that automation runs — an Ansible playbook, a CI pipeline, a backup script. It is modeled like infrastructure because it has real dependencies: the host it executes on, the network fabric it traverses, the name service it resolves through. While the job runs, none of those may be taken down, which is how ordered operations like a UPS-triggered graceful shutdown come out of the data instead of hand-written runbooks. The engine that runs the job (Ansible, Tekton, Argo) is a provider detail, not part of the type.

**Use when:**
- You need a shutdown or upgrade sequence to know an orchestration job is running and must finish before its executor host stops.
- You need to record which automation created or modified a resource, so the resource's provenance can cite the job.
- You need a scheduled or event-triggered job (cron, a UPS on-battery event) tracked with a hard execution-time limit.

**Not for:**
- The long-running service a job might deploy — that is Software.Service; a service has no scheduled end, a job must declare max_execution_time.
- The workload container a job runs in — that is Compute.Container; the job is the process, not the runtime.

**Works with:**
- Compute.BareMetalHost — the executor host a running job pins (the orchestrator stops last).
- Network.Switch — the fabric the job traverses; connectivity outlives whatever the job operates on.
- Network.AddressService — the name resolution the job needs to reach its targets.

## Capability

### Capability (0.2.0)

**Purpose:** Names one discrete platform capability so architecture analysis can track, normalize, and gap-score it.

A single named thing a platform can do — e.g. workload placement, or secret rotation — kept as a curated fact rather than provisioned infrastructure. Capabilities move through a curation lifecycle (proposed, under review, canonical, deprecated); once canonical, other records bind to the capability's normalized handle instead of free-text names, so the same capability spelled five ways converges onto one record. Nothing is ever built from a Capability — it is knowledge about the platform, not a resource in it.

**Use when:**
- You need to track which architectural capabilities a platform has, is missing, or has duplicated across teams.
- You need many differently-worded mentions of the same capability to converge onto one canonical name.

**Not for:**
- The vocabulary term a capability normalizes onto — that is TaxonomyTerm (the authority); Capability is the observed thing being normalized.
- A provider's concrete operation vocabulary (create-volume, allocate-address) — that lives as provider-capability terms under TaxonomyTerm, not here.

**Works with:**
- TaxonomyTerm — the canonical taxonomy a capability is mapped onto (normalized_to).
- Capability — capabilities depend on other capabilities, forming the capability map.

## Compute

### Compute.BareMetalHost (0.5.0)

**Purpose:** Models a physical machine as a managed asset — the box itself, whether or not anything is running on it yet.

One physical server: its identity (serial, model, asset tag), its aggregate capacity (CPU sockets and cores, memory, local storage), and its lifecycle state. It can sit unallocated in inventory before anything is deployed on it. Components like NICs can be modeled as their own records attached to the host; CPU, memory, and disk normally stay as rollup numbers on the host itself. Everything that runs — VMs, containers, storage daemons — ultimately sits on one of these, which makes it a central node in shutdown and startup ordering.

**Use when:**
- You need an inventory of physical servers, including ones not yet assigned to any workload.
- You need the dependency chain workload → host → power feed, so an outage or maintenance walk knows what stops when.
- You need per-host aggregate capacity (cores, memory, storage) for allocation decisions.

**Not for:**
- A virtual machine — that is Compute.VirtualMachine; a host is hardware you can touch.
- The host's out-of-band management controller — that is Hardware.BMC, its own record with its own address and power-control surface.
- Individual NICs, GPUs, or drives inside the host — those are Hardware.NetworkInterface / Hardware.GraphicsProcessor / Hardware.StorageDevice records contained by the host.

**Works with:**
- Facility.PowerFeed — the power source the host draws from; roots the shutdown ordering.
- Hardware.BiosProfile — the firmware configuration the host converges to.
- Hardware.NetworkInterface — the host's NICs, modeled as contained components.
- Compute.VirtualMachine — the guests the host runs.

### Compute.Cluster (0.4.0)

**Purpose:** Declares a managed Kubernetes/OpenShift cluster — release, node pools, and network ranges — as one provisionable intent.

The request for a whole container platform: which release, how many nodes of what shape in which pools, and what internal network ranges it uses. A provider (e.g. hosted control planes behind a management hub) turns this into a running cluster and publishes back the API URL, console URL, and admin access that everything deployed onto the cluster then uses. Namespaces, quotas, node pools, and workloads all hang off a cluster record.

**Use when:**
- You need to request a new Kubernetes/OpenShift cluster with a declared release and node shape rather than hand-building one.
- You need cluster-scoped resources (namespaces, node pools, storage classes) to have a single parent record they cannot outlive.

**Not for:**
- A distributed storage cluster (Ceph and kin) — that is Storage.Cluster; this type is the container-orchestration platform.
- A group of nodes inside an existing cluster — that is Platform.NodePool (this spec also carries inline node_pools; single ownership between the two is an open decision).

**Works with:**
- Platform.Namespace — the isolation boundaries carved inside the cluster.
- Platform.NodePool — homogeneous slices of the cluster's node capacity.
- Network.VirtualNetwork — the network the cluster is realized onto.
- Compute.Container — the workloads scheduled onto the cluster.
- Platform.Hub — the fleet manager above this cluster: contained_by when hub-provisioned/hosted, depends_on (soft) when imported; a cluster hosting a hub is just its contained_by target

### Compute.Container (0.5.0)

**Purpose:** Declares one container workload — image, resources, environment, mounts, ports — for a provider to run.

A single containerized workload: the image it runs, the CPU and memory it needs, its environment, mounted paths, and exposed ports. It runs either on a cluster or directly on a host (e.g. rootless podman). Secrets never appear inline — anything sensitive in env or mounts points at a Security.CredentialRef instead. The image can be given as a plain OCI reference or as a reference into governed image data, which is what lets change-impact analysis find every container affected when a base image is patched.

**Use when:**
- You need to run a specific image with declared resources, environment, and ports on a cluster or a host.
- You need workload records that secret-handling rules and image blast-radius analysis can reason over.

**Not for:**
- A multi-part application (several containers and/or systemd units behaving as one thing) — that is Software.Service, which references containers as constituents.
- The image itself as a fact (digest, bill-of-materials anchor) — that is SoftwareImage; the container runs an image, it is not the image.
- A one-shot automation task with a bounded runtime — that is Automation.Job.

**Works with:**
- Compute.Cluster / Compute.BareMetalHost — exactly one of them is where the container runs.
- Security.CredentialRef — every secret the container consumes, by reference only.
- SoftwareImage — the digest-identified image the container runs; the anchor for vulnerability analysis.
- Data.Database — connection outputs the container binds to.

### Compute.VirtualMachine (0.5.0)

**Purpose:** Declares a virtual machine — sizing, guest OS, disks, network attachments, placement — as portable intent any virtualization provider can realize.

The request for one VM: how big (a named size class, or explicit vCPU and memory), what guest OS, which disks backed by what storage class, and which existing networks its NICs attach to. Placement is a selection of an existing location, not an invention. Once the provider builds it, the record carries realized facts back: IP address, hostname, instance id. The hypervisor (KubeVirt, libvirt, a cloud) is a provider detail, never part of the type.

**Use when:**
- You need to request a VM with declared size, OS, disks, and network attachments, portable across hypervisors.
- You need VM records in the dependency graph so ordering (host before VM, VM before its services) is derivable.
- You need a VM's disks and addresses to reference existing Storage.Volume / Network.IPAddress records rather than duplicate them.

**Not for:**
- The physical machine it runs on — Compute.BareMetalHost.
- A containerized workload — Compute.Container; the VM carries a full guest OS.
- The vNIC as a device record — that is Hardware.NetworkInterface with a virtual device_class; the VM's networks list declares attachment intent, not device inventory.

**Works with:**
- Network.VirtualNetwork — the networks the VM's NICs attach to.
- Storage.Volume — the volumes behind the VM's disks.
- Facility.Location — where the VM is placed (selected from existing places, policy-governed).
- Network.IPAddress — pre-allocated addresses the VM consumes.

## Data

### Data.Database (0.4.0)

**Purpose:** Declares a managed relational database instance and publishes the connection facts other resources bind to.

The request for a database: engine (e.g. postgres), a version that may be concrete (16) or an abstract channel the provider resolves (latest, lts), and resource sizing. Once realized, it publishes host, port, and connection details that applications bind to, plus the concrete version actually provisioned — so a latest at request time is still an auditable fact afterwards. Where it runs (a VM, a cluster, a managed service) and which volume holds its data are first-class edges, not prose.

**Use when:**
- You need a database provisioned to a declared engine, version, and size, with its connection surface published for consumers.
- You need the database's backing volume and host in the graph so ordering (volume before database, database before app) is derivable.

**Not for:**
- The volume storing the data — Storage.Volume; the database references it.
- The secret material for connecting — that belongs with Security.CredentialRef (the current sensitive connection outputs are a known open decision).

**Works with:**
- Storage.Volume — the persistent volume backing the data directory.
- Compute.VirtualMachine / Compute.Cluster — where the database runs, when self-hosted.
- Software.Service / Compute.Container — the consumers that bind to its connection outputs.

## Facility

### Facility.Location (0.3.0)

**Purpose:** Names a physical place — site, room, rack, bench — that resources sit in, nesting into a containment hierarchy.

A physical place, at whatever granularity is useful: a site contains rooms, a room contains racks, a rack has positions. Resources declare where they physically sit by referencing a location; location-scoped concerns like cooling or a shared uplink attach at the right level of the hierarchy. Power is deliberately not carried here — each host declares its own power-feed edges, because two hosts in one rack can draw from different feeds.

**Use when:**
- You need to record where equipment physically is, down to a rack position.
- You need placement intent for a VM or workload to select among existing places.

**Not for:**
- Failure or locality domains for placement constraints (zone, power domain, rack-as-failure-domain) — that is Topology: put resources IN Locations, constrain placement AGAINST Topology.
- Power sources — Facility.PowerFeed, referenced per host, not per location.

**Works with:**
- Facility.Location — the parent place this one nests inside.
- Compute.BareMetalHost — the equipment that declares its location.
- Topology — the failure-domain view of the same physical reality.

### Facility.PowerFeed (0.3.0)

**Purpose:** Models a power source — utility circuit, UPS, PDU, generator — as the root that shutdown/startup ordering of everything drawing from it hangs on.

One source of power feeding equipment. Hosts and switches declare which feed they draw from, so what loses power when a UPS drains is a graph walk, not tribal knowledge. For UPS feeds it carries live status (online, on-battery, low-battery), battery charge, and estimated runtime — the facts an automated graceful shutdown triggers on. Rated capacity (watts, voltage, phases) and redundancy are declared up front.

**Use when:**
- You need equipment tied to its actual power source so a UPS on-battery event can drive an ordered shutdown of exactly what that UPS feeds.
- You need rated capacity and feed redundancy recorded per circuit/UPS/PDU.

**Not for:**
- The place equipment sits — Facility.Location; a rack is a place, a feed is a power source, and the two deliberately vary independently.
- Powering one host off — that action targets the host's Hardware.BMC control surface, not the feed.

**Works with:**
- Compute.BareMetalHost — hosts declare depends_on the feed(s) they draw from.
- Network.Switch — a UPS-backed switch outlives hosts in a shutdown; connectivity goes last.
- Automation.Job — the shutdown job a feed's on-battery status triggers.

## Hardware

### Hardware.BMC (0.4.0)

**Purpose:** Models a host's baseboard management controller so power and reset actions have a first-class, addressable target.

The always-on management controller inside a server that answers even when the host is off — iDRAC, iLO, a Supermicro/ASPEED BMC. This record carries its management address, the protocols it answers (Redfish, IPMI as fallback), and its vendor, and points at the one host it controls. Credentials are never stored here — they are referenced. It exists so that power that host off resolves to a concrete address and mechanism instead of prose.

**Use when:**
- You need out-of-band power/reset control of a host to be addressable data, for shutdown ordering and recovery automation.
- You need the management-network surface of the fleet inventoried separately from in-band host addresses.

**Not for:**
- The host itself — Compute.BareMetalHost; the BMC manages it, one-to-one.
- The BMC login secret — Security.CredentialRef, referenced not stored.

**Works with:**
- Compute.BareMetalHost — the host this BMC is the power/reset surface for.
- Security.CredentialRef — the BMC credential, by reference.
- Hardware.BiosProfile — firmware profiles applied over the BMC's out-of-band path.

### Hardware.BiosProfile (0.4.0)

**Purpose:** Captures a reusable desired BIOS/firmware configuration that a fleet of hosts converge to.

A named set of BIOS settings, written once and applied to many hosts. The attribute names and values are the vendor's own (Redfish BIOS attributes), carried as an opaque block and interpreted against a pinned attribute registry for the exact board and firmware — the profile does not re-describe what each setting means. Hosts reference the profile; the applied generation reported back is what drift detection compares against. A profile can derive from a base profile.

**Use when:**
- You need identical BIOS settings (e.g. SR-IOV enabled, boot order) enforced across a fleet of like hosts.
- You need to detect a host whose live BIOS no longer matches its declared profile.

**Not for:**
- Host network interface configuration — that is Network.ConnectionProfile: the same opaque-body-plus-pinned-registry pattern, against NMstate instead of a BIOS attribute registry.
- The host record itself — Compute.BareMetalHost references the profile it converges to.

**Works with:**
- Compute.BareMetalHost — the hosts that declare convergence to this profile.
- Hardware.BiosProfile — an optional base profile this one derives from.
- Hardware.BMC — the out-of-band path the profile is applied through.

### Hardware.GraphicsProcessor (0.2.0)

**Purpose:** Inventories a GPU or accelerator — physical card, whole-GPU passthrough, or a vGPU/MIG partition — as a component of its host or guest.

One GPU as a component record. The same type covers three shapes, distinguished by device_class: the physical card installed in a host, a whole card passed through to a guest, and a partition (a vGPU or MIG slice) carved from a physical card — a partition points at its parent physical device. Attributes (model, memory, architecture) are discovered facts; the type publishes no runtime binding surface because nothing binds to a GPU record directly — schedulers bind through the host or guest.

**Use when:**
- You need GPU inventory across hosts — which cards, where, with what memory and architecture.
- You need the passthrough/partition chain (guest slice → physical card → host) traversable for maintenance impact.

**Not for:**
- CPU sockets — Hardware.Processor.
- Requesting GPU capacity for a workload — that is placement against advertised capability (e.g. Platform.NodePool capabilities), not a GPU component record.

**Works with:**
- Compute.BareMetalHost — the host the physical card is installed in.
- Compute.VirtualMachine — the guest a passthrough or partition is presented to.
- Hardware.GraphicsProcessor — parent_device: the physical card a partition is carved from.

### Hardware.NetworkInterface (0.9.0)

**Purpose:** Models every kind of network interface — physical NIC, virtual NIC, SR-IOV slice, bond, bridge, and switch port — as one traversable device type.

One network interface, of any kind: device_class says whether it is a physical NIC, a fully virtual interface (virtio/veth), a whole-NIC passthrough, a partition carved from one physical NIC (an SR-IOV VF or VLAN sub-interface, pointing up at its parent), or a composite built from many members (a bond or a bridge, pointing down at its members). The same type also serves switch ports. A physical interface carries a connects_to edge to its discovered peer port, which is what makes host → NIC → switch port → switch a walkable path. VLAN membership is declared by referencing Network.VLAN records, never by retyping raw tags.

**Use when:**
- You need the full host interface stack — NICs, bond, bridge, sub-interfaces — as records whose parent/member links mirror reality.
- You need host-NIC-to-switch-port cabling (LLDP-discovered) in the graph for impact analysis.
- You need a port's VLAN membership (native/tagged) declared against shared VLAN records.

**Not for:**
- The attachment point guests plug into — Network.VirtualNetwork; a bridge here is the device, the VirtualNetwork is the workload-facing network on top of it.
- The desired configuration applied to an interface (addressing, routes, DNS) — Network.ConnectionProfile configures the device this type inventories.
- The VLAN segment itself — Network.VLAN; interfaces are members of a segment, they don't define it.

**Works with:**
- Compute.BareMetalHost / Network.Switch — what contains the interface (host NIC vs switch port).
- Hardware.NetworkInterface — parent_device, lower_layer, and connects_to: partition parentage, bond/bridge membership, cable adjacency.
- Network.VLAN — the segments the port is a member of.
- Network.ConnectionProfile — the declarative config realized onto this interface.

### Hardware.Processor (0.2.0)

**Purpose:** Inventories a CPU — a physical socket or a vCPU presented to a guest — as a first-class component when the host rollup is not enough.

One processor as its own record: model, cores, threads, architecture, clock. Most estates only need the aggregate CPU numbers already carried on the host; this type exists for when a socket must be individually addressable (asset tracking, heterogeneous sockets). device_class distinguishes the physical socket from a virtual CPU presented to a guest. Nothing binds to a processor at runtime, so it publishes no outputs — it is inventory.

**Use when:**
- You need per-socket inventory (exact model, position, serial) beyond the host's aggregate core/thread rollup.
- You need virtual CPUs presented to a guest tracked as components.

**Not for:**
- Ordinary capacity accounting — the cpu rollup on Compute.BareMetalHost covers that without per-socket records.
- GPUs and accelerators — Hardware.GraphicsProcessor.

**Works with:**
- Compute.BareMetalHost — the host the socket is installed in, which carries the reconciled rollup.
- Compute.VirtualMachine — the guest a virtual CPU is presented to.

### Hardware.StorageDevice (0.2.0)

**Purpose:** Inventories a disk/SSD/NVMe — physical drive or virtual disk — with the identity (WWN, serial, bay) that ties failures and replacements to one device.

One storage device as a record: where it sits (bay or slot), what it is (model, serial, world-wide name), its capacity, media and bus type, and its role (boot, data, cache, storage-cluster member). device_class separates a physical drive from a virtual disk presented to a guest; a virtual disk points at the storage that backs it. Once realized, the OS device path is published, tying the inventory record to what the host actually sees.

**Use when:**
- You need drive-level inventory — which drive, in which bay, of which host — so a failing disk maps to a physical pull-and-replace.
- You need pool or cluster membership grounded in real devices (a vdev's members, a storage daemon's backing drive).

**Not for:**
- The consumable volume a workload attaches — Storage.Volume; a device is hardware, a volume is provisioned capacity.
- The aggregation layer over drives — Storage.Pool (host-local) or Storage.Cluster (distributed).

**Works with:**
- Compute.BareMetalHost — the host the drive is installed in.
- Storage.Pool — pools whose vdevs group these drives.
- Compute.VirtualMachine — the guest a virtual disk is presented to.

## Identity

### Identity.Group (0.2.0)

**Purpose:** Models a group of identities — native or mirrored from a directory — that role bindings and memberships resolve through.

A named set of person and service-account identities. Two sources: a built_in group owns its member list locally; an external group mirrors a directory/IdP group and is referenced, never copied — membership stays authoritative in the directory. Access-control machinery binds roles to groups rather than to individuals, so joining or leaving a group is the whole access change.

**Use when:**
- You need role assignments to bind to a set of identities instead of to individuals.
- You need a directory (LDAP/IdP) group represented in the model without duplicating its membership.

**Not for:**
- The directory server that hosts an external group — Security.DirectoryService.
- The secret an account authenticates with — Security.CredentialRef; groups hold identities, never credentials.

**Works with:**
- Identity.Person / Identity.ServiceAccount — the members, for built_in groups.
- Security.DirectoryService — the source of an external group's membership.

### Identity.Person (0.3.0)

**Purpose:** Models a human account — the actor that gets authenticated, authorized, and audited.

One human's identity: login handle, display name, email, status, and how they authenticate (the built-in provider by default, or a directory/IdP when federated). It carries no secret material — a password or key is referenced through a Security.CredentialRef, never stored. Every audited action and role assignment points back at this record's stable actor id.

**Use when:**
- You need human accounts as records that role assignments and audit trails reference.
- You need a federated user tied to their external IdP subject without copying the IdP's data.

**Not for:**
- Automation, agents, or API-key holders — Identity.ServiceAccount.
- The credential itself — Security.CredentialRef; a person references credentials, never contains them.
- The directory server — Security.DirectoryService is the server; this is one identity in it.

**Works with:**
- Identity.Group — memberships that drive role binding.
- Security.CredentialRef — the person's credentials, by reference.
- Security.DirectoryService — the external authenticator when federated.

### Identity.ServiceAccount (0.3.0)

**Purpose:** Models a non-human account — automation, an agent, a provider integration — as an authenticated, auditable actor.

An account for something that is not a person: a pipeline, an agent, an integration holding an API key. Like a person it has a handle, an authenticator, and referenced-only credentials; unlike a person it declares an owner — the person or team accountable for it. Its stable actor id is what role assignments and audit records bind to.

**Use when:**
- You need automation to authenticate with its own identity instead of borrowing a person's.
- You need every non-human credential holder to have a named accountable owner.

**Not for:**
- A human account — Identity.Person.
- The API key or token itself — Security.CredentialRef, referenced not stored.

**Works with:**
- Identity.Person — the accountable owner.
- Security.CredentialRef — the account's key/token, by reference.
- Identity.Group — memberships that grant it roles.

## Network

### Network.AddressService (0.4.0)

**Purpose:** Represents a site's DHCP/DNS service as one operated capability the dependency graph can order around.

The thing that hands out addresses and answers name lookups, as a single, deliberately thin service record. It says which capabilities are served (DHCP, DNS) and whether service is redundant, and points at the host(s) or VM(s) running it. Its job in the model is ordering: hosts that need leases and name resolution depend on it, so it stops late and starts early. The software (Kea, BIND, dnsmasq, FreeIPA) is a provider; the data it serves is projected from address records and scope/zone records.

**Use when:**
- You need shutdown/startup ordering to account for everything here needing DHCP/DNS up first.
- You need the DHCP/DNS role pinned to the specific hosts that serve it.

**Not for:**
- A subnet's pools and options — Network.DHCPScope is the config surface.
- A zone and its records — Network.DNSZone.
- A single address — Network.IPAddress.

**Works with:**
- Compute.BareMetalHost / Compute.VirtualMachine — where the service runs; it stops before its host.
- Network.DHCPScope — the per-subnet config this service serves.
- Network.DNSZone — the zones it answers for.

### Network.ConnectionProfile (0.3.0)

**Purpose:** Captures a host interface's desired network configuration — addressing, routes, DNS, bond/bridge/VLAN membership — as declarative state a provider applies.

What a host interface's network configuration should be, in NMstate's own schema, carried as an opaque body against a pinned schema version — the profile does not re-describe NMstate's fields. A NetworkManager-family provider applies it (Ansible, Kubernetes-NMState); the state read back from the host is published, and a difference between desired and discovered is drift. It replaces per-tool host-network variable files with one governed record per interface.

**Use when:**
- You need host interface config (static addressing, routes, VLANs on a bond) declared once and converged by automation.
- You need drift in host networking detected from data, not by logging into hosts.

**Not for:**
- The interface device itself — Hardware.NetworkInterface; the profile configures a device that type inventories.
- BIOS settings — Hardware.BiosProfile: the same opaque-body-plus-pinned-registry pattern, for firmware.

**Works with:**
- Hardware.NetworkInterface — the adapter or port the profile applies to.
- Network.VLAN — the segments the configured VLANs and sub-interfaces ride.

### Network.DHCPScope (0.5.0)

**Purpose:** Declares a subnet's DHCP configuration — dynamic pools, options, lease time — as the neutral surface any DHCP provider serves.

One subnet's DHCP setup: the CIDR, the dynamic ranges leased from, common options (gateway, DNS servers, domain name), and lease time. Reservations are not authored here — they are derived: every statically-allocated address record bound to an interface projects into this scope's reservation list, so the fact that an address belongs to a MAC lives in exactly one place. The DHCP server software is a provider; this record is what it renders its config from.

**Use when:**
- You need a subnet's dynamic ranges and options declared portably, independent of which DHCP server serves them.
- You need static reservations to fall out of address records automatically instead of being maintained twice.

**Not for:**
- Allocation-side accounting of a range (who holds which address, is it exhausted) — Network.IPAddressPool; the scope is service-side config. The two overlap on ranges deliberately, and both document it.
- One address or reservation — Network.IPAddress with static allocation; it projects into the scope.

**Works with:**
- Network.IPAddress — the address records whose static allocations project into reservations.
- Network.AddressService — the operated service serving this scope.
- Compute.BareMetalHost / Compute.VirtualMachine — the servers the scope is served from.

### Network.DNSZone (0.3.0)

**Purpose:** Declares an authoritative DNS zone — its name, role, and records — independent of the software serving it.

One DNS zone (e.g. example.com) with its authoritative role (primary, secondary, stub, forward) and, optionally, its resource records. The serving software (BIND, directory-integrated DNS, a cloud DNS) is a provider. Once realized, the zone's nameservers are published. One asymmetry is a documented open decision: records here are authored inline, while the DHCP side derives its reservations from address records.

**Use when:**
- You need zones inventoried with their authoritative role and their serving relationships.
- You need zone data declared portably so the serving software can change without the model changing.

**Not for:**
- The DNS service as a running dependency — Network.AddressService; the zone is data, the service is what stops and starts.
- The address facts behind A/PTR entries — those originate on Network.IPAddress records; the zone holds the name-side projection.

**Works with:**
- Security.DirectoryService — when the directory (e.g. FreeIPA) serves the zone.
- Network.AddressService — the operated DNS capability answering for the zone.

### Network.Gateway (0.4.0)

**Purpose:** Models the network edge — routing, NAT, and firewalling between segments and to the outside — as a node the graph can reason about.

The router/firewall at the edge of a network: which functions it provides (routing, NAT, firewall, VPN) and which segments it connects, each segment referencing the VLAN it rides. The vendor box or software (pfSense, OPNsense, a vendor firewall) is a provider. Detailed routing tables and firewall rulesets are deliberately not modeled — the portable surface is functions and segments; once realized it publishes the external address it presents.

**Use when:**
- You need what connects this network to the outside as an explicit node with its segments.
- You need segment boundaries (LAN, DMZ, mgmt) and their VLANs recorded at the edge that routes between them.

**Not for:**
- An L2 switch — Network.Switch; the gateway is the L3 edge.
- Service-level L4/L7 traffic entry (the Kubernetes Gateway API sense) — that is the adopted naming ancestor, but this type is the broader network edge; application ingress belongs to the platform.
- Handing out addresses on its segments — Network.DHCPScope / Network.AddressService.

**Works with:**
- Network.VLAN — each gateway segment rides a referenced VLAN.
- Network.DHCPScope — scopes serving the segments the gateway routes.
- Network.Switch — the fabric behind the edge.

### Network.IPAddress (0.6.0)

**Purpose:** Makes a single IP address its own record — origin, interface binding, and allocation — so each address fact lives in exactly one place.

One IP address, bound to the interface it is configured on, with how it came to be: static (a fixed reservation — this IS the DHCP reservation; there is no second record), leased via DHCP, or self-assigned (SLAAC/privacy). A static record authors the address up front; a dynamic one gets its address filled in once observed. From this one record, projections are derived — a DHCP scope's reservation list, name-side entries — instead of the same fact being retyped per system.

**Use when:**
- You need address assignments tracked per interface with their origin (static, dhcp, auto).
- You need one authoritative record that DHCP reservation lists and other projections derive from.

**Not for:**
- The range addresses come from — Network.IPAddressPool.
- The subnet's DHCP service configuration — Network.DHCPScope.
- The interface itself — Hardware.NetworkInterface; the address attaches to it.

**Works with:**
- Hardware.NetworkInterface — the interface the address is configured on.
- Network.IPAddressPool — the pool the address was carved from.
- Compute.VirtualMachine — consumers that request or bring addresses.

### Network.IPAddressPool (0.3.0)

**Purpose:** Makes an allocatable IP range a first-class record so allocation ownership and exhaustion are visible facts.

A range of addresses that individual address records are carved from: the subnet prefix, the allocatable ranges inside it, exclusions (gateway, broadcast, known statics), and how addresses leave it (leased, reserved, or both). Once realized it reports totals — allocated, free, exhausted — the signal capacity and placement policies read before asking for another address. Same pattern as a storage pool feeding datasets: the pool is the source, the carved record depends on it.

**Use when:**
- You need to know which addresses are in play, who holds each, and when a range is close to exhausted.
- You need address allocation scoped to the one network segment the pool serves.

**Not for:**
- Service-side DHCP config for the subnet (options, lease time) — Network.DHCPScope; the pool is intent-side inventory. The range overlap between the two is deliberate and documented on both.
- A single address — Network.IPAddress, carved from this pool.

**Works with:**
- Network.IPAddress — the records carved from the pool (allocated_from).
- Network.VirtualNetwork — the segment the pool serves.
- Network.DHCPScope — the service-side projection of the same subnet.

### Network.Switch (0.4.0)

**Purpose:** Models a physical network switch as a managed asset — the fabric peer of a bare-metal host, with its ports as contained interface records.

One physical L2/L3 switch: chassis identity keyed by its LLDP chassis id (normally the chassis MAC — stable and discoverable), a port rollup, and its management addressing. Its individual ports are not a separate type — they are Hardware.NetworkInterface records contained by the switch, the same type host NICs use, which is what lets a cable be a single edge between two interface records. A switch can enter the model as discovered (via LLDP) before being formally adopted; vendor specifics stay with the provider.

**Use when:**
- You need the switching fabric in the dependency graph so connectivity-outlives-compute is derivable in shutdown ordering.
- You need per-port records (VLAN membership, host adjacency) on real switch hardware.
- You need brownfield discovery — switches found via LLDP, then adopted.

**Not for:**
- A software bridge on a host — Hardware.NetworkInterface with device_class bridge.
- The routed/NAT edge — Network.Gateway.
- The VLAN segments themselves — Network.VLAN; the switch carries segments, it doesn't define them.

**Works with:**
- Hardware.NetworkInterface — its ports, and the host NICs those ports connect to.
- Facility.PowerFeed — the power the switch draws; UPS-backed fabric stops last.
- Network.VLAN — segments carried on the fabric, including the referenced management VLAN.

### Network.VLAN (0.3.0)

**Purpose:** Names a network segment — an 802.1Q VLAN or an overlay VNI — once, as the shared object everything that rides it references.

The segment itself: its encapsulation (802.1Q tag, VXLAN/Geneve VNI, or flat/untagged) and its id. It exists so a segment id appears in exactly one record — switch ports, host sub-interfaces, gateway segments, and virtual networks all reference the VLAN record rather than each retyping the tag. It is a root resource: dependents select an existing VLAN, they do not invent one inline.

**Use when:**
- You need one authoritative record per segment that ports, virtual networks, and gateway segments all reference.
- You need overlay segments (VXLAN/Geneve VNIs) modeled with the same shape as 802.1Q VLANs.

**Not for:**
- The workload attachment point — Network.VirtualNetwork rides a VLAN; guests attach to the VirtualNetwork, not to the VLAN.
- A port's tagging configuration — that is vlan_memberships on Hardware.NetworkInterface, referencing this record.

**Works with:**
- Hardware.NetworkInterface — ports and sub-interfaces declare membership by reference.
- Network.VirtualNetwork — virtual networks ride a referenced segment.
- Network.Switch — the fabric carrying the segment.
- Network.Gateway — edge segments each ride a referenced VLAN.

### Network.VirtualNetwork (0.6.0)

**Purpose:** Models the attachment point workloads plug into — the host- or cluster-scoped network a guest names when it says attach me here.

The network a VM's or pod's NIC attaches to: a libvirt network, a Kubernetes NetworkAttachmentDefinition, an OVN logical switch — whichever; the mechanism is the provider. It declares how traffic leaves (bridged straight onto a host bridge, NATed, routed, or isolated) and references downward: the VLAN segment it rides and the host bridge or uplink interface supporting it. That downward reference completes the walkable path guest → virtual network → bridge → bond → NIC → switch.

**Use when:**
- You need VMs or pods to attach to networks by selecting an existing named network rather than describing L2 details inline.
- You need the guest-to-physical-network path traversable for impact analysis — e.g. which guests a bridge change affects.

**Not for:**
- The VLAN id or segment itself — Network.VLAN; a virtual network rides a segment, referenced not restated.
- The host bridge device — Hardware.NetworkInterface (device_class bridge) supports this network from below.
- Per-guest NIC intent — that lives on Compute.VirtualMachine's own networks list.

**Works with:**
- Compute.VirtualMachine / Compute.Cluster — the guests that attach, and the scope that hosts the network.
- Network.VLAN — the underlying segment, selected by reference.
- Hardware.NetworkInterface — the supporting bridge or uplink on the host.
- Network.IPAddressPool — the address pool scoped to this segment.

## Observability

### Observability.LogShipper (0.3.0)

**Purpose:** Declares the outcome that a host's logs reach the central sink — without saying anything about how.

A statement of outcome: logs from a target host, shipped to a named sink URL, tagged with the host's identity. The consumer never sees the mechanism — whether a provider satisfies it with an automation-managed agent, a container, or something else is the provider's private business, and swapping mechanisms changes nothing in this record. Realized state reports whether shipping is healthy and when the last successful delivery happened, which drives staleness detection.

**Use when:**
- You need logs-from-host-X-land-in-the-central-store as a declared, checkable fact per host.
- You need shipping health and last-delivery time surfaced for drift and staleness detection.

**Not for:**
- The log store itself — that is its own resource (e.g. a Software.Service running the sink); this type is the per-host shipping outcome.
- Metrics or trace collection — not covered; this type is logs.

**Works with:**
- Compute.BareMetalHost / Compute.VirtualMachine — the target host whose logs are shipped.
- Software.Service — the central log store the sink URL points at.

## Platform

### Platform.Hub (0.1.0)

**Purpose:** The multi-cluster management plane: the thing that provisions, imports, and lifecycle-manages a fleet of clusters.

A Hub is whatever sits above your clusters and manages them as a fleet — an ACM hub, a HyperShift/HCP management cluster, a Rancher server, or a hosted fleet manager. It may itself run on a cluster (including, in the self-managed pattern, the very cluster it manages) or be standalone software. Model the hub as its own entity; whether it lives on a cluster is just an edge.

**Use when:**
- you need to record which management plane provisioned or now manages a cluster
- a cluster's lifecycle operations flow through a fleet manager and shutdown/startup order must respect it
- you need the management plane's own sovereignty position (which jurisdiction governs the manager, distinct from its spokes)

**Not for:**
- the cluster a hub happens to run on — that host is a plain Compute.Cluster, and hub-ness on it is a derived role marker, never authored
- single-cluster platform services (GitOps controllers, ingress operators) — those are Software.Service on the cluster
- a peer DCM instance in federation — that is the federate capability on the provider contract, not a Hub

**Works with:**
- Compute.Cluster — spokes point at the hub (contained_by when hub-provisioned/hosted-control-plane; depends_on soft when imported), and a hosted hub points contained_by at its own host cluster
- Facility.Location — where the hub's control plane actually runs, for the sovereignty question
- Security.CredentialRef — the fleet-management credentials the hub holds are references, never inline

### Platform.Namespace (0.3.1)

**Purpose:** Declares the isolation boundary inside a cluster that workloads are placed into and tenancy binds to.

What Kubernetes calls a Namespace and OpenShift calls a Project: a named partition of a cluster that workloads live in. It binds a tenant, carries labels and annotations, and cannot outlive its cluster. Providers and placement policies use it to answer which namespace a request lands in; the realized name and platform UID are published for provider-side references to resolve.

**Use when:**
- You need workloads partitioned per tenant, team, or environment inside a shared cluster.
- You need quota and placement policy to operate on a governed namespace record, not an ad-hoc string.

**Not for:**
- The cluster itself — Compute.Cluster.
- The consumption limits inside the boundary — Platform.ResourceQuota constrains a namespace; it doesn't define one.

**Works with:**
- Compute.Cluster — the cluster the namespace exists within.
- Platform.ResourceQuota — hard limits scoped to this namespace.
- Compute.Container / Software.Service — workloads placed into it.

### Platform.NodePool (0.3.0)

**Purpose:** Declares a homogeneous slice of a cluster's node capacity — shared hardware traits, labels, taints — that placement matches workloads against.

A named group of like nodes in a cluster: how many, what they offer (GPU, architecture, memory tier), what labels they carry, and what taints a workload must tolerate to land there. Placement reads the capability advertisements to match a workload's requirements to a pool. Cloud platforms call this a node pool or machine set.

**Use when:**
- You need GPU or otherwise-special nodes grouped so only workloads that need (and tolerate) them land there.
- You need placement to select capacity by declared capability (architecture, memory tier) rather than by node names.

**Not for:**
- The cluster — Compute.Cluster (whose spec also carries inline node_pools; single ownership between the two is an open decision).
- One physical machine — Compute.BareMetalHost; a pool is a cluster-level grouping, not a host record.

**Works with:**
- Compute.Cluster — the cluster the pool belongs to.
- Platform.Namespace — namespaces whose workloads schedule onto pools.

### Platform.ResourceQuota (0.3.0)

**Purpose:** Declares hard consumption limits for one namespace so capacity questions are answerable before a workload is dispatched.

The Kubernetes ResourceQuota construct as a record: aggregate CPU, memory, pod count, storage, and object-count ceilings for a single namespace. Discovered usage is reported against the limits, so whether a namespace has room for a request is a data question a placement policy answers up front — and quota pressure is visible for capacity planning.

**Use when:**
- You need per-namespace ceilings on aggregate consumption enforced and visible.
- You need admission or placement to check remaining headroom before dispatching a workload.

**Not for:**
- Per-container resource requests — those live on the workload (Compute.Container resources).
- Node capacity — Platform.NodePool advertises capacity; a quota caps consumption within a namespace.

**Works with:**
- Platform.Namespace — the one namespace this quota constrains.
- Compute.Container — workloads whose aggregate consumption the quota caps.

### Platform.StorageClass (0.3.0)

**Purpose:** Names a storage provisioning policy — provisioner, reclaim, binding mode, capabilities — that volumes request storage by.

The Kubernetes StorageClass construct: a named policy saying which provisioner builds volumes, what happens to data on release, when binding happens, whether volumes can grow, and what the class can do (IOPS, encryption, replication, snapshots). A volume asks for storage by naming a class; placement policies select classes by capability. Provisioner-specific parameters ride along opaquely — the provisioner interprets them, the model does not.

**Use when:**
- You need volumes to request storage by named policy instead of naming backends.
- You need placement to pick storage by advertised capability (encrypted, fast, replicated).

**Not for:**
- The volume itself — Storage.Volume references a class.
- The backing storage system — Storage.Cluster; the class is the policy naming what the cluster serves.
- Host-local pools — Storage.Pool; a class is a platform-level provisioning policy.

**Works with:**
- Storage.Volume — volumes declare their class by reference.
- Storage.Cluster — the storage cluster backing the class.
- Compute.VirtualMachine — VM disks select a storage class.

## Security

### Security.CredentialRef (0.3.0)

**Purpose:** Points at a credential held by an issuing provider — which credential, held where, at what assurance — without the value ever entering the model.

A reference to a secret, never the secret. It names the kind of credential, the issuer that holds it, the provider-side path it resolves at, its scope (what it may operate on), and the minimum assurance the consumer requires. At realization the issuer resolves it and delivers the value directly to the authorized consumer — the value never passes through the model, audit, source control, or logs. What IS recorded: that it resolved, which version, and when it was first retrieved.

**Use when:**
- You need any resource (a container, a service, a BMC, a bind account) to consume a secret without the secret appearing in data.
- You need audit facts about credential resolution and first retrieval, without exposure.
- You need consumers to demand a minimum assurance level and have weaker issuers filtered out before binding.

**Not for:**
- The identity that authenticates with the credential — Identity.Person / Identity.ServiceAccount; an identity references its credentials, this is the credential side.
- Storing an actual password, key, or token anywhere — no type is for that; the value lives only with the issuer.

**Works with:**
- Identity.Person / Identity.ServiceAccount — whose credential this is.
- Compute.Container / Software.Service / Storage.FileShare — consumers that reference it from env, mounts, or config.

### Security.DirectoryService (0.4.0)

**Purpose:** Models the directory server — LDAP and optionally Kerberos — that identities authenticate against and services bind to.

The identity directory as a running server: which protocols it serves (LDAP, Kerberos), its realm and base DN, and its role in a replication topology (a replica depends on its primary). Consumers get endpoints once realized — the LDAP URL, the Kerberos KDC, the base DN to bind under. The server is distinct from the identity data in it: people, groups, and service accounts are their own records; a suite like FreeIPA realizes this server plus DNS zones.

**Use when:**
- You need services and hosts that authenticate against the directory to depend on it, so it stops last among them.
- You need the directory replication topology (primary/replica) explicit for recovery planning.

**Not for:**
- The identities inside — Identity.Person / Identity.Group / Identity.ServiceAccount.
- The DNS zones a directory suite serves — Network.DNSZone; related, but its own record.
- The bind credential — Security.CredentialRef.

**Works with:**
- Compute.VirtualMachine / Compute.BareMetalHost — where the directory runs.
- Identity.Group — external groups sourced from this directory.
- Software.Service — services requiring the directory, with hard/soft strength.
- Network.DNSZone — zones served when DNS is directory-integrated.

## Software

### Software.Service (0.4.0)

**Purpose:** Models a logical running service — one or more containers and/or systemd units acting as one thing — so application-level dependencies carry order.

The application layer: the mail service, the registry, model serving — a named service composed of constituents that are either referenced container records or named systemd units on a host. It declares what the service needs — a database, a directory, name service, storage, another service, each dependency hard or soft — which is what makes infrastructure-daemons-stop-after-applications derivable. Endpoints and a ready signal surface how it is reached and whether it is serving.

**Use when:**
- You need an application composed of several workloads treated as one node with one dependency surface.
- You need service-to-service and service-to-infrastructure dependencies (with hard/soft strength) to drive shutdown/startup order.
- You need host services (systemd units) and containerized services modeled uniformly.

**Not for:**
- A single container's runtime spec — Compute.Container; the service references containers as constituents.
- A bounded-runtime task — Automation.Job.
- The database a service uses — Data.Database, referenced as a dependency.

**Works with:**
- Compute.Container — containerized constituents, by reference.
- Compute.Cluster / Compute.BareMetalHost / Compute.VirtualMachine — where the constituents run.
- Data.Database / Security.DirectoryService / Network.AddressService — what the service requires.
- Security.CredentialRef — the service's secrets, by reference.

## SoftwareImage

### SoftwareImage (0.1.0)

**Purpose:** Records a container image as a digest-identified fact — the anchor a container's software bill of materials hangs from.

One container image, identified by its content digest (tags are recorded but advisory — tags move, the digest does not). It is knowledge about the estate, discovered by scanning, never provisioned: which repository and registry it came from, what OS and architecture it targets, and — through its contains edges — every package inside it. That containment is what turns which containers run something shipping a given library from an investigation into a graph walk.

**Use when:**
- You need every running container tied to the exact image digest it runs, deduplicated across the fleet.
- You need a bill-of-materials anchor: image → packages → vulnerabilities, walkable in both directions.

**Not for:**
- The running workload — Compute.Container runs an image; this is the image as a fact.
- A package inside the image — SoftwarePackage; the image contains packages.

**Works with:**
- Compute.Container — workloads that run this image.
- SoftwarePackage — the packages the image contains (the software bill of materials).

## SoftwarePackage

### SoftwarePackage (0.1.0)

**Purpose:** Records a software package or library as one shared fact per package URL, so every image containing it points at the same record.

One package at one version — identified by its purl (Package URL), the portable id that carries ecosystem, name, and version in one string. There is exactly one record per purl no matter how many images contain it, which is what makes blast-radius questions cheap: find the package once, walk back to every image and container that includes it. Discovered by scanners; never built or provisioned.

**Use when:**
- You need where-do-we-run-version-X-of-library-Y answerable as a graph walk.
- You need packages linked to the advisories affecting them.

**Not for:**
- The image bundling the package — SoftwareImage contains packages.
- The advisory itself — Vulnerability; a package is affected_by it.

**Works with:**
- SoftwareImage — the images that contain this package.
- Vulnerability — the advisories affecting this package version.

## Storage

### Storage.Cluster (0.4.0)

**Purpose:** Models a distributed storage system serving block, file, and/or object storage — the platform volumes are provisioned from.

A multi-node storage system — Ceph is the reference realization, but the technology is the provider, never the type. It declares which protocols it serves (block, file, object), its capacity, and its redundancy scheme, and publishes the consumption surfaces: the block and file storage-class names volumes provision through, and the S3-compatible object endpoint. Its own nodes are hosts or VMs it depends on — the cluster needs its quorum up.

**Use when:**
- You need the storage platform in the graph so volumes and their consumers order correctly against it and its member nodes.
- You need the cluster's protocols, capacity, and protection scheme declared vendor-neutrally.

**Not for:**
- A host-local pool of drives (ZFS zpool, LVM VG) — Storage.Pool; a Storage.Cluster is distributed across nodes.
- The consumable volume — Storage.Volume, provisioned from this cluster.
- The provisioning policy name — Platform.StorageClass; the cluster backs a class, the class is the policy record.

**Works with:**
- Compute.BareMetalHost / Compute.VirtualMachine — the nodes the cluster runs across.
- Storage.Volume — volumes provisioned from the cluster.
- Platform.StorageClass — the class records naming what this cluster serves.

### Storage.Dataset (0.3.0)

**Purpose:** Models a dataset carved from a host-local pool — the mounted filesystem or block device host workloads actually use.

The consumable unit of host-local storage: a ZFS filesystem or zvol (the same shape extends to LVM logical volumes and btrfs subvolumes), with its mountpoint, quota, and passthrough properties. It is what a podman container or host service bind-mounts, so it is the storage node those workloads depend on. Datasets nest (parent chains) and cannot outlive the pool they are carved from. Snapshot and replication policy is orchestration, deliberately not stored here.

**Use when:**
- You need host services and containers tied to the specific dataset they store on, so the dataset outlives them in shutdown order.
- You need the pool → dataset → workload chain explicit for capacity and migration planning.

**Not for:**
- The pool it is carved from — Storage.Pool owns the drives and redundancy.
- Cluster-provisioned volumes a platform attaches — Storage.Volume; a dataset is host-local.
- A network share exported to other machines — Storage.FileShare exposes storage; a dataset is the local storage itself.

**Works with:**
- Storage.Pool — the pool the dataset is carved from.
- Compute.BareMetalHost — the host the dataset is local to.
- Storage.Dataset — the parent dataset, when nested.

### Storage.FileShare (0.3.0)

**Purpose:** Declares a file-sharing service and its exported shares — who may reach which path over which protocol.

A file server's sharing surface: the protocol (SMB today, extensible to NFS), the exported shares with their paths and access rules, and the directory service that authenticates the principals named in them — membership stays in the directory, referenced not copied. Share-level knobs the model doesn't type ride through a passthrough field the provider serializes (e.g. into smb.conf). Once realized, the reachable share URI is published.

**Use when:**
- You need network file shares — their paths, access lists, read-only flags — governed as data rather than living only in a config file.
- You need share authentication tied to the directory service that actually holds the principals.

**Not for:**
- The local storage behind the share path — Storage.Dataset / Storage.Volume; the share exposes storage, it isn't the storage.
- The identity data of who may connect — Security.DirectoryService holds it; shares reference principals.

**Works with:**
- Security.DirectoryService — authenticates the share principals.
- Storage.Volume — the underlying storage the shares expose.
- Compute.BareMetalHost / Compute.Container — where the file service runs.
- Security.CredentialRef — service credentials (e.g. a keytab), by reference.

### Storage.Pool (0.3.0)

**Purpose:** Models a host-local aggregation of physical drives into redundancy-protected capacity that datasets are carved from.

The generic redundancy group — one shape for a ZFS zpool, an md array, a hardware-RAID virtual disk, an LVM VG, or a btrfs pool: a set of drives on one host grouped into vdevs, each vdev carrying a protection scheme (mirror, raidz). The vdev topology is why the type exists — a flat dataset-on-host edge would lose which drives protect which data and how many failures the pool survives. It sits between the physical drives below and the datasets above, and orders accordingly: a pool stops after its datasets and before its drives.

**Use when:**
- You need the drive → vdev → pool → dataset chain explicit so drive failures and maintenance map to affected data.
- You need host-local capacity facts (usable after redundancy, degraded state) as data.
- You have RAID anywhere — firmware, mdadm, zpool — and want one reusable model for it (declared hardware-RAID pools drive controller config at bare-metal provision time).

**Not for:**
- Distributed multi-node storage — Storage.Cluster.
- The consumable unit workloads mount — Storage.Dataset, carved from the pool.
- An allocatable range of IP addresses — Network.IPAddressPool is the same pool pattern in the network domain.
- RAID fields on the host type — a host never carries RAID; it contains pools (see Compute.BareMetalHost).

**Works with:**
- Compute.BareMetalHost — the host whose drives form the pool.
- Storage.Dataset — the datasets carved from the pool.
- Hardware.StorageDevice — the physical member drives of the vdevs.

### Storage.Volume (0.5.0)

**Purpose:** Declares a consumable persistent volume — the block or file storage a workload attaches — independent of what provisions it.

The unit of storage a workload asks for and attaches: requested capacity, how concurrently it may be attached (one writer, many readers, and so on), filesystem versus raw block, and which storage class provisions it. It is deliberately distinct from the platform that builds it and the devices that back it. Once realized, the provider's volume handle comes back, tying the request to the actual volume.

**Use when:**
- You need a workload's storage requested by capacity, access mode, and class, portable across provisioners.
- You need volumes ordered in the graph: realized before their consumer, never outliving their provisioning cluster.

**Not for:**
- The provisioning policy — Platform.StorageClass; the volume references a class by name.
- The storage platform — Storage.Cluster provisions volumes.
- Host-local ZFS/LVM storage a host service mounts — Storage.Dataset.
- The physical drive — Hardware.StorageDevice.

**Works with:**
- Platform.StorageClass — the class declaring what kind of storage the volume gets.
- Storage.Cluster — the platform provisioning it.
- Compute.VirtualMachine — the consumer(s) it attaches to.
- Data.Database — databases whose data directory it backs.

## TaxonomyTerm

### TaxonomyTerm (0.2.0)

**Purpose:** Holds one canonical vocabulary term — the fixed point that free-text mentions are normalized onto.

A term with an authoritative definition, living in a named vocabulary tree (its root), with a parent chain that never crosses into another vocabulary. Several vocabularies share this one type while staying disjoint — e.g. an architecture-capability taxonomy and a provider-operation vocabulary are separate roots. Terms are curated (proposed, under review, canonical, deprecated); once canonical, the term's handle is what other records bind to instead of restating names.

**Use when:**
- You need an authoritative vocabulary that observed, free-text items normalize onto.
- You need several disjoint controlled vocabularies without minting a new type per vocabulary.

**Not for:**
- The observed thing being normalized — Capability records normalize onto terms; the term is the authority, not the observation.
- Ad-hoc classification of resources — labels on resource records cover that; TaxonomyTerm is for governed vocabularies with curation.

**Works with:**
- Capability — capabilities normalize onto terms (normalized_to).
- TaxonomyTerm — the parent term; chains stay inside one vocabulary root.

## Topology

### Topology (0.3.0)

**Purpose:** Declares the failure and locality domains — region, zone, rack, power, network — that placement, residency, and maintenance gating resolve against.

One record describing a graph of domains, each with a stable id, an abstract kind (zone, rack, power, and so on), a parent, and labels (e.g. jurisdiction). Portable intent constrains against kinds — spread across power domains — while what a resource actually landed in is a concrete id. Domains are addressable data inside this one type, not separate records. Observed per-domain status (active, draining, unavailable) is the signal maintenance gating reads — a draining domain holds off further maintenance.

**Use when:**
- You need placement or anti-affinity constraints that reference abstract domain kinds portably.
- You need residency and sovereignty resolved against domain labels (jurisdiction, region).
- You need maintenance serialization gated on domain status — e.g. not starting the next host while a domain is draining.

**Not for:**
- The physical places themselves — Facility.Location is where things sit; Topology is the failure/locality view constraints resolve against. A rack appears in both, on purpose, in different roles.
- Network segments — Network.VLAN / Network.VirtualNetwork; a network domain here is a failure domain, not the segment object.

**Works with:**
- Facility.Location — the physical containment the domains often mirror.
- Compute.VirtualMachine — placement intent resolved against domain kinds.
- Storage.Cluster — fault-domain-aware placement and maintenance gating.

## Vulnerability

### Vulnerability (0.1.0)

**Purpose:** Records a known vulnerability — CVE, GHSA, or OSV advisory — once, as the shared fact every affected package points at.

One advisory, one record, keyed by its public id (e.g. a CVE id). It carries the working set — severity, CVSS score and vector, weakness class, affected version ranges — and points at the full advisory rather than restating it. It is the terminal node of the software-knowledge chain: packages reference it, and impact analysis reverse-walks from here — advisory → packages → images → running containers.

**Use when:**
- You need what-in-the-estate-is-exposed-to-this-advisory as a reverse graph walk.
- You need scanner findings deduplicated onto one record per advisory id, with severity and scoring at hand.

**Not for:**
- The affected package — SoftwarePackage points here via affected_by.
- Whether a particular deployment is actually exploitable — that applicability assessment (the VEX role) is analysis on top, not this record.

**Works with:**
- SoftwarePackage — the packages affected by this advisory.
- SoftwareImage — reached transitively for blast radius (advisory → package → image).

---
*47 types; 47 with context, 0 pending.*
