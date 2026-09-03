# Research: portability classification across the data-center and homelab stack

**What this settles:** a survey of the technology stacks found in a data center or a homelab, and
for each, what the portability contract is and where it sits in Base / Type / Provider under
ruling 068. It answers one question that came up while applying 068 to `Compute.Cluster` — *if a
Kubernetes cluster gets its own Base, what about a storage cluster, or a VM-host cluster?* — and
turns the answer into a Base roster and a rule for clusters. It is a proposal with decisions
called out at the end, not a ruling.

**Status:** research. Nothing here is applied. The plan for the `Compute` split (the applied list in ruling 068) changes if
the recommendations hold; the changes are listed in the last section.

## The question under test

Ruling 068 says a Base Class is earned by a shared portability contract: its members are things
one consumer intent can move between, and a grouping whose members share no contract is a folder.
Applying it to `Compute` produced `Container` (PR #568) and proposed a `KubernetesCluster` Base.

"Cluster" recurs at every layer of an estate. Ceph is a cluster. vSphere and Proxmox are clusters.
Patroni, Galera, Kafka, etcd, OpenSearch are clusters. A switch stack, a firewall pair, and a Kea
HA pair are clusters. If the Kubernetes cluster earns a Base because it is a cluster, every one of
these does too, and the tier model collapses into a list of products. So the real question is not
what to call `Compute.Cluster`; it is **what makes a cluster a class at all, and under which Base
it belongs when it is one.**

## What is already established — do not re-derive

| Established | Where | Consequence here |
|---|---|---|
| Base = category scope; Type extends Base; Provider extends Type; portability is read off scope | ADR-038 §Decision 1–4 | the classification is a placement of each stack at a scope |
| A Base is earned by a shared portability contract | ruling 068, register row (PR #569, open) | the test applied throughout |
| The concrete technology is the **provider**, never in the type name | `Storage.Cluster`, `Storage.Pool`, `Storage.Volume` record descriptions | stated only in three class records; nowhere in the spec |
| `Platform` is defined as "Kubernetes clusters, application platforms" | `resource-type-hierarchy.md` §2.2 | by 068 that is a folder: two members, no shared contract |
| 9 of 12 Resource Bases describe themselves as "Empty category base — the promotion target" | `registry/classes/resource/*/_base.yaml` | none states a contract; by 068 none is yet earned |
| Only `Network` (`zone`, `tier`), `Hardware` (`device_class`) and `Compute` carry Base elements | same | the three that already say what they are |
| Adopting a standard's object by name is existing practice | `Storage.Volume` "Adopts Kubernetes PersistentVolumeClaim/CSI + SNIA Swordfish"; Redfish `ComputerSystem` spelling for firmware (068) | a standard's name in a class is not a vendor's name |
| Field-level portability classes `universal / conditional / provider-specific / exclusive` | `resource-type-hierarchy.md` §4 | orthogonal to this survey: that classifies fields, this classifies classes |

## Method

For every stack I recorded four things and derived the placement from them:

1. **Intent** — what a consumer actually asks for, in their words.
2. **Contract** — what any provider must honor for that intent to be realized.
3. **Movement set** — the implementations one intent moves between without rewriting it.
4. **Placement** — Base, Type, element, or provider, by these rules:
   - Two things with the same contract share a Base. A different contract is a different Base,
     even if the things look alike (068).
   - A cluster is a **Type** only when the cluster itself is what the consumer asks for. When a
     cluster is how a provider delivers HA for something else the consumer asked for, it is a
     **topology element** on that Type (`replicas`, `ha`), not a class.
   - A technology name belongs in a class name only when the technology **is the contract**: a
     conformance-tested API standard (Kubernetes, OCI, Redfish, Swordfish). A vendor or
     distribution (OpenShift, EKS, Ceph, vSphere, Proxmox) is a provider and never appears.
   - A Type lives under the Base whose API it serves, not under the Base of what it is built from.
     `Storage.Cluster` serves the storage contract even though it is built from machines.

Examples are drawn from both ends of the range: an enterprise data center and this homelab (an
OpenShift cluster whose control plane and two workers are KVM guests on one libvirt host, three Ceph
VMs on the same host, a ZFS workstation, Kea DHCP in HA on two Raspberry Pis, FreeIPA, a Quay
registry on Ceph RGW, GPU inference under KServe).

## The survey

### Physical and machine layers

| Stack | Intent | Contract | Moves between | Placement |
|---|---|---|---|---|
| Rack, room, PDU feed, cooling, cabling | "a rack position with two power feeds" | physical placement: position, power, cooling budget | any site | **`Facility`** Base (exists; contract unstated) |
| Server chassis, CPU, GPU, NIC, drive, BMC, BIOS profile, switch hardware | "a host with 2×25GbE and one GPU" | a device requirement, discriminated by `device_class` | any vendor meeting the spec | **`Hardware`** Base (exists; `device_class` is its discriminator) |
| Bare metal via Redfish / iPXE / Ignition / kickstart | "a host booted into this image" | boot an image with cpu, memory, disk, nic, firmware, guest init | any BMC-managed server | **`Machine.BareMetalHost`** (`Compute` split, step 2) |
| VM on KVM/libvirt, Proxmox, vSphere, Hyper-V, Xen, Nutanix AHV, OpenStack Nova, KubeVirt / OpenShift Virtualization, EC2, GCE, Azure | "a VM with 4 vCPU, 16 GiB, this image" | same contract as bare metal, plus an image | every hypervisor and cloud listed | **`Machine.VM`** (`Compute` split, step 2) |
| Hypervisor cluster: vSphere DRS/HA, Proxmox VE, oVirt, Nutanix, Hyper-V failover, Harvester, OpenStack host aggregates, a single libvirt host | "a VM-host cluster of N hosts with shared storage, live migration and HA" | hypervisor management: membership, shared storage attach, migration domain, HA policy | every product listed | **new `Virtualization` Base, `Virtualization.Cluster`** — see D2 |

The hypervisor cluster is the case that decides the pattern. It does **not** share `Machine`'s
contract (nobody boots an image into a vSphere cluster), so it is not `Machine.HostCluster` — the
same reason `Container` left `Compute`. It is the platform that realizes `Machine.VM`, the way a
Kubernetes cluster is the platform that realizes `Container`. That symmetry is the shape of the
whole roster: **workload contracts** and **platform contracts** are different Bases.

### Container and orchestration layers

| Stack | Intent | Contract | Moves between | Placement |
|---|---|---|---|---|
| podman, docker, quadlets, a Kubernetes pod | "run this image" | OCI image + runtime | all of them | **`Container`** Base (PR #568) |
| Kubernetes cluster: OpenShift, OKD, EKS, AKS, GKE, RKE2, k3s, Talos, kubeadm, MicroShift, HyperShift hosted control planes | "a cluster at release 1.30 with these node pools" | the Kubernetes API (conformance-tested) | every distribution listed | **`Kubernetes.Cluster`** — see D1 |
| Namespace, NodePool, ResourceQuota, StorageClass | "a namespace with an 8-CPU quota on cluster X" | Kubernetes API objects | every distribution | **`Kubernetes.Namespace`** etc. (today `Platform.*`) |
| Fleet hub: ACM / OCM, HyperShift management cluster | "a hub managing these spokes" | OCM ManagedCluster semantics | OCM-family only | **`Kubernetes.Hub`** (today `Platform.Hub`) |
| Nomad, Docker Swarm, ECS | "run this workload with 3 replicas" | not the Kubernetes API; Nomad has namespaces and node pools, ECS has clusters, Swarm has neither | the workload moves (`Container`, `Template.Application`); the platform objects do not | provider of `Container`; **no** shared platform Base with Kubernetes |

Why `Kubernetes` and not `Platform` or `Orchestrator`: the contract *is* the Kubernetes API.
`pod_cidr`, `service_cidr`, `StorageClass`, `ResourceQuota`, and the hub's ManagedCluster semantics
have no meaning outside it. A neutral name over a Kubernetes-only contract is the folder 068
forbids. Kubernetes is a CNCF conformance standard, not a vendor, so naming it obeys the same rule
as adopting Redfish or OCI. OpenShift, EKS and k3s are the providers.

Why not `KubernetesCluster` as its own Base (ruling 068 as rowed): it strands Namespace, NodePool,
StorageClass and Hub in `Platform`, three of which already carry edges to the cluster. The family
has one contract; it should have one Base.

### Storage and data layers

| Stack | Intent | Contract | Moves between | Placement |
|---|---|---|---|---|
| Ceph (RBD/CephFS/RGW), Gluster, Longhorn, Rook, MinIO, Linstor/DRBD, vSAN, NetApp/Pure/Dell arrays, TrueNAS | "a storage cluster serving block and object, 200 TiB, 3× replicated" | protocols served + capacity + data protection | every product listed | **`Storage.Cluster`** (exists — the precedent this survey generalizes) |
| ZFS pool, LVM VG, mdraid, hardware RAID, btrfs | "a redundant pool on this host's drives" | host-local capacity with a redundancy topology | every product listed | **`Storage.Pool`** (exists) |
| PVC/CSI volume, EBS, NFS share, iSCSI LUN, dataset | "500 GiB block, attach to this workload" | block/file volume with class and size | every provisioner | **`Storage.Volume`**, `Storage.FileShare`, `Storage.Dataset` (exist) |
| PostgreSQL via Patroni, CloudNativePG, Crunchy, RDS; MySQL Galera / InnoDB Cluster; SQL Server AG; MongoDB replica set | "a Postgres 16, 100 GiB, highly available" | engine + version + resources + availability | every operator and managed service | **`Data.Database`** with a **topology element** (`replicas`, `ha`) — the cluster is the provider's HA mechanism, not the ask |
| Redis Cluster, etcd, OpenSearch / Elasticsearch | same shape as above | same | same | `Data.Database` engines, topology element |
| Kafka, RabbitMQ, NATS, pipelines | "a stream with 3 partitions, 7-day retention" | stream/queue semantics | every broker | `Data.Stream` / `Data.Queue` — **gap**, category table names them, no Type exists |

`Storage` and `Data` are both earned by 068 and both currently describe themselves as empty. The
contract lines above are what their Base records should say.

### Network, identity, security, observability

| Stack | Intent | Contract | Moves between | Placement |
|---|---|---|---|---|
| VLAN, subnet, IP, pool, virtual network, gateway, DNS zone, DHCP scope, connection profile | "a /24 on VLAN 20 with a gateway" | connectivity, discriminated by `zone` and `tier` | every switch, SDN and IPAM | **`Network`** Base (exists; contract already stated) |
| Switch stack / MLAG pair, firewall HA pair, Kea HA pair, BIND primaries, HAProxy pair, MetalLB | "DHCP for this subnet" (not "a Kea pair") | the service; the pair is how the provider makes it survive | any implementation | **topology on the Type**, or the provider's own concern. The homelab's Kea HA on two Pis is one `Network.DHCPScope` |
| FreeIPA, Active Directory, LDAP, Keycloak; Vault, cert-manager, step-ca, HSM | "a directory for this realm", "a credential reference" | directory service semantics; credential reference | every implementation | **`Security.DirectoryService`**, `Security.CredentialRef` (exist). Multi-master replicas are topology |
| Person, Group, ServiceAccount | information, not a resource | identity data | any IdP | **`Identity`** Base (information family, exists) |
| Prometheus / Thanos / Mimir, Loki, OpenTelemetry collector, Elastic, Grafana | "ship logs from these hosts", "scrape these endpoints" | OTLP and Prometheus exposition — both standards, adopt by name | every backend | **`Observability`** Base (exists; `LogShipper` only) |

### Automation, batch, serving, edge

| Stack | Intent | Contract | Moves between | Placement |
|---|---|---|---|---|
| AAP / AWX, Terraform / OpenTofu, ArgoCD / Flux, Foreman / Satellite, MAAS, Flightctl | "run this automation against these targets" | what a run is, regardless of engine | every engine | **`Automation`** (Process family; contract stated); `Job` is the receipt |
| Slurm, PBS, HTCondor, Ray, Kueue | "a batch cluster with 8 GPU nodes" / "run this job" | job-scheduler API | every scheduler | **gap.** `Job` covers the run; nothing covers the cluster. Record, do not add — no use case asks for one yet |
| vLLM, KServe, Triton, Ray Serve, Ollama | "an inference endpoint for model X" | a served service with replicas | every server | **`Software.Service`** (exists, `service_kind`) on `Kubernetes` or `Machine`; the homelab's `llm-serving` is this |
| Flightctl fleets, MicroShift, Raspberry Pi, field laptops | "this device runs this image" / "these devices form a fleet" | `Machine` + `Kubernetes`; a fleet is a `Grouping` | — | existing classes; no new Base |
| Application composition | "the three-tier app" | composition mechanism | — | **`Template.Application`** (exists) |

## The cluster rule

Reading the survey down the placement column gives one rule:

> **"Cluster" is a topology, not a kind.** A cluster is a Type only when the cluster itself is the
> deliverable, and then it lives under the Base whose API it serves. A cluster that exists to make
> some other deliverable highly available is a topology element on that deliverable's Type.

| Cluster | Is the cluster the ask? | Where it goes |
|---|---|---|
| Kubernetes cluster | yes | `Kubernetes.Cluster` |
| Fleet hub | yes | `Kubernetes.Hub` |
| VM-host cluster | yes, by the infrastructure operator | `Virtualization.Cluster` (new) |
| Storage cluster | yes | `Storage.Cluster` (exists) |
| Database cluster | no — the ask is a database | `Data.Database` topology element |
| Kafka / Redis / etcd / OpenSearch cluster | no | `Data.*` topology element |
| Switch stack, firewall pair, DHCP HA pair | no — the ask is the network service | `Network.*` topology, or the provider's concern |
| Directory replicas | no | `Security.DirectoryService` topology |
| Batch / HPC cluster | yes | gap; no Base until a use case asks |

## The Base roster after 068

Only the Resource family Bases that a technology stack lands in. Knowledge, Access, Grouping,
Template, Topology and SovereigntyZone are not "stacks" and are out of scope here.

| Base | Contract, in one line | Today | Action |
|---|---|---|---|
| `Facility` | physical placement: position, power, cooling | empty | state the contract |
| `Hardware` | a device requirement, by `device_class` | discriminator present | state the contract |
| `Machine` (was `Compute`) | boot an image: cpu, memory, disk, nic, firmware, guest init | VM + BareMetalHost | `Compute` split, step 2 |
| `Virtualization` | hypervisor management: membership, shared storage, migration, HA | does not exist | **new** — D2 |
| `Container` | OCI: run this image | PR #568 | merge |
| `Kubernetes` (was `Platform`) | the Kubernetes API | folder named `Platform` | **rename**, absorb `Compute.Cluster` — D1 |
| `Storage` | protocols served, capacity, data protection | empty | state the contract |
| `Data` | a managed data service: engine, version, resources, availability | empty | state the contract; `Stream`/`Queue` gap |
| `Network` | connectivity, by `zone` and `tier` | stated | none |
| `Security` | directory and credential semantics | empty | state the contract |
| `Observability` | telemetry: OTLP, Prometheus exposition | empty | state the contract |
| `Software` | installed or served software | empty | state the contract |

"State the contract" means the Base record's description says what its members share and what a
provider must honor, replacing "Empty category base — the promotion target". That is a description
change; whether it is a patch or a minor bump is D5.

## What this changes in the `Compute` split plan

| Step | Change |
|---|---|
| **Merge #569** | the 068 row names `KubernetesCluster`. If D1 holds, edit the row before merge to say `Kubernetes` Base and `Kubernetes.Cluster`; the PR is still open so this is a plain edit, not an amendment |
| **Step 1** (`Compute.Cluster` → new Base) | becomes two moves in one PR: `Platform` → `Kubernetes` (6 Types, 193 references) and `Compute.Cluster` → `Kubernetes.Cluster` (98 references). Same sweep discipline: `registry/renames.yaml`, patch bumps with `$id` in step, regenerate, `docs/adr/` excluded |
| **Step 2** (`Compute` → `Machine`) | unchanged; the sweep now also catches `Storage.Cluster`'s two `depends_on` edges to `Compute.VM` / `Compute.BareMetalHost` |
| **new Step 2b** | `Virtualization` Base + `Virtualization.Cluster`, after `Machine` exists. Small: one Base record, one Type record, edges `depends_on Machine.BareMetalHost`, and `Machine.VM` gains an optional `contained_by Virtualization.Cluster` |
| **Step 3** (normative spec section) | gains three rules from this survey: every Base states its contract; the cluster rule; standard-in-the-name, vendor-never. And the nine "state the contract" edits above land with it |
| **Step 4, 5** | unchanged |
| **Follow-up** | `Compute.Cluster.node_pools` (inline array) and `Platform.NodePool` (a Type with `contained_by` the cluster) model the same thing twice. T7 reduce-to-existing says keep one. Not in this sweep |

## Decisions for the maintainer

- **D1 — `Kubernetes` as the Base name.** Recommended. The alternative is to keep `Platform` and
  write "contract: the Kubernetes API" in its record, which keeps a neutral name over a
  non-neutral contract. `KubernetesCluster` as a standalone Base is the weakest option and is what
  #569 currently records.
- **D2 — add `Virtualization` now or defer.** Recommended now, as step 2b, because the homelab
  already needs it: the single libvirt host carrying every OpenShift and Ceph VM, and today there is no
  class for it. Deferring costs nothing in the sweep, so this is about whether a use case demands it
  yet.
- **D3 — a single libvirt host.** Is the single libvirt host a `Virtualization.Cluster` of one, or a
  `Machine.BareMetalHost` with a role? `Storage.Pool` vs `Storage.Cluster` is the precedent for a
  host-local / distributed split, which argues for `Virtualization.Host` alongside `.Cluster`. I
  lean cluster-of-one until a second consumer asks for the host shape.
- **D4 — the batch/HPC gap.** Record only. No use case in the 22 asks for a scheduler cluster.
- **D5 — bump class for stating a contract on an empty Base.** Description-only, so patch by the
  letter of the rules; but it changes what the Base *means*, so minor is the honest call.

## Out of scope

Field-level portability classification (`universal / conditional / provider-specific /
exclusive`) is a separate axis and is not revisited. Provider Class naming is untouched. The
Knowledge family is untouched.
