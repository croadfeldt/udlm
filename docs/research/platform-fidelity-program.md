# Research: platform fidelity — what the platforms in a homelab actually expose, and where it lands

**What this settles:** the finding that a discovery sweep of a real estate already observes facts
today's classes cannot hold, why that is (the classes stop at the Type tier; no platform has a
Provider Class; observed facts are written as spec fields), and the program that closes it: one
platform at a time, adopt the platform's own model by reference, and give each observed fact a home
at the right tier. It is a research brief with a plan attached; the decisions it needs from the
maintainer are at the end.

**Status:** research. Nothing here is applied. Each platform below becomes one PR that carries its
own research note and its class changes together.

## The finding

An estate of about 300 records across 23 classes was compared with the registry as it stands. Two
things came out of it.

1. **Four classes the estate names no longer exist under those names.** They were renamed by the
   class-tier series (`Compute.VM` to `Machine.VM`, `Compute.BareMetalHost` to
   `Machine.BareMetalHost`, `Compute.Container` to `Container`, `Compute.Cluster` to
   `KubernetesCluster`), and every class the estate pins sits several versions behind. That is a
   migration problem for the estate, not a model problem, and it is planned there.
2. **The sweep observes facts the classes have no field for.** Of the fields present in the estate's
   discovered snapshots, a third have no property in the current class. Some are stale spellings of
   elements that now exist (`vcpus` is `cpu.count`, `family` is `ip_family`, a pool's `topology`
   string is `vdevs`). The rest are real: an interface's LACP partner and active members, its link
   state and its LLDP neighbour; a VM's libvirt `autostart`; a container's platform, namespace,
   host and observed run state; a switch's firmware and 802.1AB capabilities; a UPS behind a power
   feed; a directory server's replication peers; a job's playbook and kind. None of these is exotic.
   They are what the platforms report first.

The reason is structural. **No platform in the stack has a Provider Class.** The registry has three
provider-tier classes in total, two of them a worked example. The Machine, Container, Storage,
Network and Security classes stop at the Type tier, so anything libvirt-specific, Podman-specific,
ZFS-specific or FreeIPA-specific has nowhere to go but a free-form `properties` bag or the estate's
own extra keys. And most of the missing facts are **observed, not declared**: a link is up, a
partner is attached, a guest is shut off. Those are outputs, written by discovery or the provider,
not spec fields a consumer asks for. Several classes declare no output for them.

## The discipline

Three rules, all already in the spec, applied per platform:

- **Adopt, never invent** (T5, the standards-adoption methodology). Each platform has a
  native model with names: libvirt's domain XML, KubeVirt's VirtualMachine, Podman's quadlet unit,
  OpenZFS properties, Ceph's pool and cluster status, Kea's configuration, FreeIPA's topology, NUT's
  variable names, IEEE 802.1AB and 802.1AX, Redfish. The Provider Class binds to that model by
  reference and carries only what the platform adds beyond the Type.
- **Tier by portability** (ADR-038, ruling 068). A fact every member of the Base can report goes on
  the Base; a fact every provider of the Type reports goes on the Type; a platform's own goes on its
  Provider Class. `autostart` is libvirt's; "observed run state" is every VM's.
- **Observed facts are outputs.** Link state, LACP partner, observed power, scrub status, battery
  charge: a provider or a sweep writes them on the realized or discovered record. They are never
  spec fields, because nobody asks for a link to be up; they find it so.

## The platforms, one by one

Each row names the platform's source of truth, the standard or native model to adopt, the classes
it touches, what already exists, and what the sweep observes today that has no home. The last
column is the research question the platform's PR answers.

| Platform | Source of truth | Adopt | Classes | Exists today | Observed with no home | Research question |
|---|---|---|---|---|---|---|
| **libvirt / KVM** hypervisor | `virsh dumpxml`, `virsh dominfo`, `virsh list --all` | libvirt domain XML schema | `Machine.VM` and a new `Machine.VM.Libvirt` | `cpu`, `memory`, `firmware`, `run_state.desired_state`, `networks`, `placement`; outputs `observed_run_state`, `mac_addresses`, `ip_addresses` | `autostart`, machine type, CPU mode, on-crash and on-poweroff actions, video and graphics, the domain UUID as a correlation id | Which domain-XML elements are portable enough for the Type (all hypervisors have an equivalent) and which are libvirt's own |
| **KubeVirt / OpenShift Virtualization** | `VirtualMachine`, `VirtualMachineInstance` | KubeVirt API (already adopted on the Type) | `Machine.VM`, a new `Machine.VM.KubeVirt` | `run_state` maps to `runStrategy` | instance type and preference refs, namespace, node placement, live-migration state | Same split as libvirt; and whether the two providers agree on `observed_run_state` vocabulary |
| **Kubernetes / OpenShift** workloads | `Deployment`, `StatefulSet`, `Pod` | Kubernetes core/v1 and apps/v1 (core/v1 Container already adopted) | `Container`, a new `Container.Kubernetes` | `image`, `resources`, `process`, `network.ports`, `runtime.replicas`; outputs `endpoint`, `internal_dns` | namespace, workload kind, node, observed phase | Whether the observed phase becomes a Base output (`observed_state`) shared with Podman, and how the namespace is an edge (`contained_by` a `KubernetesNamespace`) rather than a string |
| **Podman** on hosts | quadlet units, `podman inspect`, systemd unit state | Podman quadlet, OCI runtime spec | `Container`, a new `Container.Podman` | as above | host, pod membership, unit name and enabled state, observed state | Same `observed_state` output; what a quadlet adds beyond the Type (unit, pod, auto-update label) |
| **OpenZFS** pools and datasets | `zpool status`, `zpool list`, `zfs get all` | OpenZFS (already adopted on Pool and Dataset) | `Storage.Pool`, `Storage.Dataset`, possibly `Storage.Pool.ZFS` | `vdevs` tree, `capacity`, `health`, `properties`; dataset `dataset_kind`, `quota`, `used`, `properties`; pool outputs `degraded`, `redundancy_status` | ashift, autotrim, last scrub and its result, read/write/checksum error counters, dataset's pool as an edge, snapshots as datasets | Whether pool-level ZFS properties earn typed elements on the Type (every pool kind has a "health check ran" fact) or stay in the provider bag; scrub and errors as outputs |
| **Ceph** | `ceph status`, `ceph osd pool ls detail`, `ceph df` | Ceph (Rook already adopted on Storage.Cluster); `ceph-fsid` is already a correlation scheme | `Storage.Cluster`, `Storage.Pool` (RADOS pools), new `Storage.Cluster.Ceph`, `Storage.Pool.Ceph` | cluster `capacity`, `data_protection`, `protocols` | mon/mgr/osd counts, PG health, per-pool size and min_size, crush rule, application, CephFS and RGW as protocols with endpoints | Whether a RADOS pool is a `Storage.Pool` (pool_kind ceph) with a Ceph provider class, and what the cluster's observed health looks like as outputs |
| **Kea DHCP** and **DNS** | Kea configuration and lease API; the DNS server's zones | ISC Kea (already adopted on DHCPScope), RFC 2131, IETF DNS | `Network.AddressService`, `Network.DHCPScope`, `Network.DNSZone`, new `Network.DHCPScope.Kea` | `services`, `ha`; scope `subnet`, `pools`, `options`, `lease_time` | which service instance serves which role (today two strings, `dhcp` and `dns`), HA peer state, reservations as observed | Whether a service's realizers are edges to `Software.Service` entities rather than names, and what Kea HA reports that the Type should carry as outputs |
| **FreeIPA** | `ipa topologysegment-find`, `ipa server-role-find`, replica status | RFC 4511, RFC 4120 (adopted); FreeIPA topology | `Security.DirectoryService`, new `Security.DirectoryService.FreeIPA` | `realm`, `base_dn`, `protocols`, `replication_role`; outputs `ldap_endpoint`, `kdc_endpoint` | replication peers (today two free-text strings), CA role, DNS role, observed replica state | Peers as `depends_on` edges between directory-server entities, roles as a typed element, replica health as an output |
| **NUT** (UPS) | `upsc`, `upsd` variables | NUT variable names (already adopted on PowerFeed) | `Facility.PowerFeed`, possibly a UPS entity or `Facility.PowerFeed.NUT` | `feed_type`, `capacity`, `redundancy`; outputs `status`, `battery_charge`, `runtime_seconds` | the UPS as a thing (today a string), its NUT server, driver, load, input voltage | Whether a UPS is its own entity that a feed `depends_on`, or the feed's provider class; which `ups.*` and `battery.*` variables become outputs |
| **Managed switches** (LLDP, a vendor controller) | `lldpcli show neighbors`, the controller's inventory | IEEE 802.1AB (adopted on Switch and NetworkInterface), Redfish, RFC 8345 | `Network.Switch`, `Hardware.NetworkInterface`, a vendor provider class | switch `identity.chassis_id`, `system_name`, `ports`; outputs `firmware_version`, `management_address` | 802.1AB system capabilities; per-port LLDP neighbour (chassis id, port id, system name); controller adoption state | An `lldp_neighbors` output on the interface that resolves to a switch by `chassis_id`; capabilities as a typed element; what the controller adds |
| **Bonds, bridges, VLANs** on hosts | `/proc/net/bonding/*`, NetworkManager, nmstate | IEEE 802.1AX, 802.1Q (adopted), NMstate (adopted on IPAddress) | `Hardware.NetworkInterface`, `Network.ConnectionProfile` | `device_class`, `aggregation` (mode, lacp_rate, miimon), `bridge`, `vlan_id`, `lower_layer` edges | observed LACP partner system id and active members, link state and negotiated speed, the address's gateway and route metric | Observed aggregation state and link state as outputs; gateway and metric on the connection profile per NMstate |
| **Bare-metal hosts and BMCs** | Redfish, IPMI, DMI via Ansible facts | Redfish (adopted), Metal3 (adopted) | `Machine.BareMetalHost`, `Hardware.BMC`, a vendor BMC provider class | host `identity`, `cpu`, `memory`, `firmware`, `boot_mac_address`; BMC `management_address`, `protocol`, `vendor` | the BMC's address recorded on the host, the host's boot MAC, host roles, Redfish version and BMC firmware, hosts with no BMC at all | The BMC as an entity the host `depends_on`; roles as metadata or a tag vocabulary; what a vendor's Redfish adds beyond the standard |
| **Ansible** jobs | playbooks, AAP job templates | Ansible (adopted on Job) | `Job`, the `Automation` family | `definition_ref`, `trigger`, `schedule`, `targets`, `max_execution_time`; outputs `results`, `started_at` | the playbook path (is `definition_ref`), the kind of process, the engine that ran it | Whether `Job` needs a kind, or the Automation Type classes already say it |
| **SMB file shares** | Samba configuration | SMB/CIFS (adopted) | `Storage.FileShare` | `protocol`, `shares`, `workgroup`, `directory_service_ref` | observed service state | An `observed_state` output, shared with the other service-like classes |

Two cross-cutting elements fall out of the table and should be settled once, not per platform:

- **`observed_state` as a Base-level output** for anything that runs: VM, container, service, share.
  Today `Machine.VM` has `observed_run_state` and nothing else does. One vocabulary, one home.
- **Peers, hosts and controllers are edges, not strings.** A directory server's replicas, a
  dataset's pool, a container's host, a feed's UPS, a service's realizer: each is an entity the
  record points at with `depends_on` or `contained_by`. The sweep already knows the target; the
  record should carry the reference.

## The program

One PR per platform, in the order the estate depends on them: hosts and BMCs, host networking and
switches, libvirt, ZFS, Ceph, Kubernetes and Podman containers, Kea and DNS, FreeIPA, NUT, Ansible,
SMB. Each PR carries:

1. a research note under `docs/research/` with the platform's native model quoted from its source,
   the adoption decision, and the tier decision per element;
2. the class changes: a Provider Class where the platform adds beyond the Type, new outputs on the
   Type or Base for observed facts, and any edge the platform implies;
3. the registry gates green, the flat spec regenerated, the consumer manifest updated;
4. a worked discovered record for the platform under `registry/examples/`.

Before the first platform PR, one PR settles the two cross-cutting elements above.

The estate side runs in parallel and is planned in the estate repository: the shape migration to
per-state records, then a fresh sweep that writes discovered records in the enriched classes. The
sweep waits for the platforms it covers.

## Decisions for the maintainer

1. **Provider Classes for a homelab's platforms are in scope for the registry.** The class-tier
   series left the provider tier to providers. These platforms have no vendor to author them; the
   registry authors them, as it did for the worked examples.
2. **`observed_state` on the Base for running things**, with one vocabulary, replacing
   `Machine.VM.observed_run_state`. A MAJOR on Machine.VM.
3. **A UPS is an entity.** Either a `Facility.UPS` class the feed depends on, or the feed's
   provider class. The first reads better in a graph whose root is power.
4. **Order.** Hosts and networking first, since every other platform's records hang off them.
