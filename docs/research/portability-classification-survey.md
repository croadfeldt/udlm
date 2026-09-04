# Research: what earns a Base Class, tested against the data-center and homelab stack

**What this settles:** the working definition of a Base Class after ruling 068 was applied to
`Compute`, and where every technology stack found in a data center or homelab lands under it.
Ruling 068 said a Base is earned by a shared portability contract. This brief sharpens that into
three checkable conditions, replaces the "members one intent can move between" wording, and
derives the class roster and the plan from them. It is a research brief with a plan attached;
the decisions it needs from the maintainer are listed at the end.

**Status:** research. Nothing here is applied. The `Compute` split plan changes as listed in the
last section.

## The question under test

Applying ruling 068 to `Compute.Cluster` raised a question the ruling did not answer: if a
Kubernetes cluster earns a Base, what about a storage cluster, a VM-host cluster, a database
cluster, a switch stack? "Cluster" recurs at every layer, so being a cluster cannot be what earns
a class. And "things one intent can move between" invites a thought experiment — how often does
anything move from a VM to bare metal? — that never happens in practice and so cannot be the test.

## What the model is for

UDLM is the matrix a provider declares its offerings against, so that an intent written once can
be realized by any provider whose offering is compatible, and its lifecycle managed afterwards.
The portability events in the use cases are not migrations. They are:

- **placement at order time** — the intent is written once and realized by whichever member the
  provider set offers (UC-04);
- **rebuild from stored intent** after loss, on the same or a different provider (UC-10, UC-18);
- **provider substitution** when a vendor exits.

In all three the intent stays put and a different member realizes it. Converting realized state
from one implementation to another (a libvirt guest from a VMware one) is a provider or DCM
operation and is outside the intent model. This homelab is the everyday case: an OpenShift
cluster whose workers came from one intent, "a worker with these resources", and are realized as
two bare-metal hosts and two KVM guests. Nothing moved; two members satisfied one order.

## The definition

> **A Base Class is a deliverable that any member can realize.** A resource declared at the Base
> must be satisfiable by every provider that declares an offering anywhere beneath it.

Three conditions, each checkable:

1. **An existing, widely used API already abstracts over the members.** OpenStack Nova serves VMs
   and Ironic bare metal behind one compute API; Cluster API's `Machine` is a VM or a bare-metal
   host by infrastructure provider; TOSCA's `Compute` node type is the same. Kubernetes
   conformance is the abstraction for clusters, OCI for containers, CSI for volumes. Where no
   credible API treats the members as one thing — a storage volume and a storage pool — the
   grouping is a folder. This is T5 adopt-by-reference applied to the tier model.
2. **Every Base element is honorable by every Type and every Provider beneath it.** This is how
   `Compute` failed: `Container` inherited `guest_os`, which no container provider can honor. It is
   a mechanical gate: a Type may add or refine Base elements (ADR-038's Liskov invariant) and may
   never leave one unhonorable.
3. **Declaring an offering at a tier accepts orders at every tier above it.** A provider that
   declares `Machine.VM.KubeVirt` satisfies `Machine.VM` and bare `Machine`. Policy-fill (DCM
   ADR-024) completes the blanks a Base-level order leaves. ADR-038 §4 already says every Class is
   instantiable; this is what makes that true rather than nominal.

The three tiers are the field-level portability classes of `resource-type-hierarchy.md` §4 seen
structurally: Base elements are `universal`, Type elements `conditional`, Provider elements
`provider-specific` or `exclusive`. The tree names and validates; field classification plus
capability advertisement (ADR-PROV-002) compute the portability of a given request. Neither
replaces the other.

### What this does to folder Bases

A category whose members fail condition 1 is a folder. Folders are harmless as names and harmful
as classes only because ADR-038 makes every Class instantiable: "give me a Storage" is not an
order any provider can fill. The fix is to mark such Bases **non-instantiable**, not to rename
their members. A kind is promoted to a Base of its own only when its family needs category, kind,
dialect and offering at once and overflows three segments — which is what forced `Container` out
and what the Kubernetes family hits below.

### What the Type tier is spent on

Whatever carries the definition structure for that family (ADR-038's shared-then-specialized
test), and it differs by family:

- **Form**, where the members realize one deliverable differently and each form adds elements.
  `Machine.VM` adds an image and hot-plug; `Machine.BareMetalHost` a BMC and boot order;
  `Machine.LPAR` processor units, capped or uncapped sharing, VIOS-backed I/O. Dialects (KubeVirt,
  libvirt, vSphere, the Power HMC) land at Provider.
- **Dialect**, where the deliverable has no form worth a tier and the distributions diverge.
  `KubernetesCluster.OpenShift` adds channel, FIPS, network type; `KubernetesCluster.EKS` adds
  authentication mode and add-ons. Offerings (ROSA, ARO, self-managed, OSAC-hosted) land at
  Provider, each with its own consumer-supplied data (account, region, IAM roles).

The normative section should say the axis is whatever carries the structure, not fix one. It
should also say plainly that an offering can require consumer-supplied data and therefore earns a
Provider Class; ADR-038 treats two deployments of one dialect as instances on the authority axis
differing only by advertised capability, and ROSA versus ARO shows that is not always enough.

## The survey

Each row records what a consumer asks for, the abstraction condition 1 relies on, and the
placement. Examples span an enterprise data center and this homelab (OpenShift on a mix of bare
metal and KVM guests on one libvirt host, Ceph on VMs, a ZFS workstation, Kea DHCP in HA on two
Raspberry Pis, FreeIPA, a Quay registry on Ceph RGW, GPU inference under KServe).

### Machines and what hosts them

| Stack | Intent | Abstraction | Placement |
|---|---|---|---|
| Bare metal via Redfish, iPXE, Ignition, kickstart | "a host booted into this image" | Nova/Ironic, CAPI `Machine`, TOSCA `Compute` | `Machine.BareMetalHost` |
| VM on KVM/libvirt, Proxmox, vSphere, Hyper-V, Xen, Nutanix, OpenStack, KubeVirt, EC2, GCE, Azure | "a VM with 4 vCPU, 16 GiB, this image" | same | `Machine.VM`; hypervisors are Provider Classes |
| IBM Power or z logical partition | "a Linux host with 8 cores, 64 GiB" | same intent, HMC-realized | **`Machine.LPAR`** (new Type) |
| Hypervisor cluster: vSphere DRS/HA, Proxmox VE, oVirt, Nutanix, Hyper-V failover, a single libvirt host | none from a workload consumer | — | a **provider instance** of `Machine.VM.<dialect>` on the authority axis. Whether an infrastructure operator can order a hypervisor cluster as a deliverable is an open gap (D3); no use case asks yet |
| Rack, PDU feed, cooling; chassis, CPU, GPU, NIC, drive, BMC | "a rack position with two feeds"; "a host with 2×25GbE and a GPU" | none across members | `Facility.*`, `Hardware.*` stay; both Bases become non-instantiable folders |

### Containers and Kubernetes

| Stack | Intent | Abstraction | Placement |
|---|---|---|---|
| podman, docker, quadlets, a pod | "run this image" | OCI | **`Container`** Base (PR #568) |
| OpenShift, OKD, EKS, AKS, GKE, RKE2, k3s, Talos, kubeadm, MicroShift, HyperShift | "a cluster at release 1.30 with these node pools" | Kubernetes conformance | **`KubernetesCluster`** Base as ruling 068 rowed it; Types are distributions; Providers are offerings |
| Namespace / Project | "a namespace on cluster X with an 8-CPU quota" — ordered by a tenant on an existing cluster, with its own lifecycle | Kubernetes conformance | **`KubernetesNamespace`** Base (today `Platform.Namespace`); Types are distributions where they diverge (an OpenShift Project adds elements) |
| Node pool / MachineSet / managed node group | "add a GPU pool to cluster X" — ordered, scaled and upgraded on its own | Kubernetes conformance, CAPI `MachineDeployment` | **`KubernetesNodePool`** Base (today `Platform.NodePool`); the cluster's inline `node_pools` element then references it or goes (T7) |
| ResourceQuota, LimitRange | never ordered apart from a namespace | — | elements of `KubernetesNamespace` |
| StorageClass | emitted by a storage provider, not ordered | — | an output of `Storage.Cluster` / the storage provider, as its own record already says |
| ACM / OCM hub, HyperShift management cluster | "make this cluster a hub" | OCM | role elements on `KubernetesCluster` (`fleet_manager`, `hosted_control_planes`), not a class |
| Nomad, Swarm, ECS | "run this workload" | not the Kubernetes API | providers of `Container` and `Template.Application`; no shared Base with Kubernetes |

`Platform` dissolves: three members become Bases, two become elements or outputs, one becomes a
role. Each of the three Kubernetes Bases is named for its deliverable and spells the standard out.
Distribution names come from one shared vocabulary so `.OpenShift` means the same under each.

### Storage and data

| Stack | Intent | Abstraction | Placement |
|---|---|---|---|
| Ceph, Gluster, Longhorn, Rook, MinIO, Linstor, vSAN, arrays, TrueNAS | "a storage cluster serving block and object, 3× replicated" | SNIA Swordfish `StorageSystem` | `Storage.Cluster` (exists) |
| ZFS pool, LVM VG, mdraid, hardware RAID | "a redundant pool on this host" | — | `Storage.Pool` (exists) |
| PVC/CSI, EBS, NFS share, iSCSI LUN | "500 GiB block, attach here" | CSI, Swordfish `Volume` | `Storage.Volume`, `.FileShare`, `.Dataset` (exist) |
| PostgreSQL (Patroni, CloudNativePG, RDS), MySQL Galera, SQL Server AG, MongoDB, Redis, etcd, OpenSearch | "a Postgres 16, 100 GiB, highly available" | the engine's own API | `Data.Database`; the cluster is the provider's HA mechanism, expressed as a topology element (`replicas`, `ha`) |
| Kafka, RabbitMQ, NATS | "a stream with 3 partitions" | broker API | gap: the category table names `Data.Stream`; no Type exists |

`Storage` and `Data` are folders: no order moves between a volume and a pool, or a database and a
stream. Both become non-instantiable; their members stay as they are.

### Network, identity, security, observability, automation, batch

| Stack | Intent | Placement |
|---|---|---|
| VLAN, subnet, IP, pool, virtual network, gateway, DNS zone, DHCP scope | "a /24 on VLAN 20 with a gateway" | `Network.*` stay; `Network` becomes a non-instantiable folder. `zone` and `tier` stay as the shared elements every member cites |
| Switch stack, firewall pair, Kea HA pair, BIND primaries, HAProxy pair | "DHCP for this subnet" | topology on the member, or the provider's concern. The homelab's Kea pair is one `Network.DHCPScope` |
| FreeIPA, AD, LDAP, Keycloak, Vault, cert-manager, step-ca | "a directory for this realm" | `Security.DirectoryService`, `.CredentialRef` (exist); replicas are topology |
| Prometheus, Loki, OpenTelemetry, Elastic | "ship logs from these hosts" | `Observability.LogShipper` (exists); OTLP and Prometheus exposition are the abstractions to adopt by name |
| AAP, Terraform, ArgoCD, Foreman, Flightctl | "run this automation" | **`Automation`** Base — earned: a run is realizable by any engine (condition 1: every engine exposes run / status / cancel) |
| Slurm, PBS, Ray, Kueue | "a batch cluster with 8 GPU nodes" | gap; `Job` covers the run; nothing covers the cluster, no use case asks |
| vLLM, KServe, Triton, Ollama | "an inference endpoint for model X" | `Software.Service` (exists) on a cluster or a machine |
| Flightctl fleets, MicroShift, Pi, field laptops | "this device runs this image" | `Machine` and `KubernetesCluster`; a fleet is a `Grouping` |

## The roster after the definition

| Base | Passes condition 1 by | Instantiable | Action |
|---|---|---|---|
| `Machine` (was `Compute`) | Nova/Ironic, CAPI `Machine`, TOSCA `Compute` | yes | `Compute` split step 2, plus `Machine.LPAR` |
| `Container` | OCI | yes | PR #568 |
| `KubernetesCluster` | Kubernetes conformance | yes | ruling 068 as rowed; absorbs `Compute.Cluster`; Types become distributions |
| `KubernetesNamespace` | Kubernetes conformance | yes | promoted from `Platform.Namespace` |
| `KubernetesNodePool` | Kubernetes conformance, CAPI | yes | promoted from `Platform.NodePool` |
| `Automation` | every engine's run API | yes | none |
| `Job` | — (one class for every execution) | yes | none |
| `Storage`, `Data`, `Network`, `Security`, `Observability`, `Software`, `Facility`, `Hardware` | no shared abstraction | **no** | mark non-instantiable; members unchanged; state what the folder groups |
| `Platform` | — | — | dissolved as above |

## What this changes in the `Compute` split plan

| Step | Change |
|---|---|
| **Merge #569** | the 068 row's *applied* clauses stand (`Container`, `KubernetesCluster`, `Machine`, Redfish firmware). Its *test* clause — "its members are things one consumer intent can move between" — is replaced by "a deliverable any member can realize", with the three conditions. One-line edit while the PR is open |
| **Step 1** (`Compute.Cluster` → `KubernetesCluster`) | unchanged in mechanics (98 references). In the same PR, `Platform.Namespace` → `KubernetesNamespace` and `Platform.NodePool` → `KubernetesNodePool`; `Platform.ResourceQuota` folds into the namespace, `Platform.StorageClass` into storage outputs, `Platform.Hub` into cluster role elements; `Platform` is deleted. 193 `Platform.*` references |
| **Step 2** (`Compute` → `Machine`) | unchanged, plus a `Machine.LPAR` Type and `Storage.Cluster`'s two edges to `Compute.*` |
| **Step 3** (normative spec section) | now the centre of the program and should land **before** steps 1–2 rather than after: the definition and three conditions, the tier axis rule, offerings earn a Provider Class, folder Bases are non-instantiable, technology in a name only when it is the standard. The eight folder Bases get their `instantiable: false` and a one-line "what this groups" in the same PR |
| **CI** | a gate for condition 2: no Type or Provider Class leaves a Base element unhonorable. Pairs with the existing Liskov check |
| **Steps 4, 5** | unchanged |
| **Dropped** | a `Virtualization` Base; `Kubernetes.Cluster` as a name; the registry-wide re-tiering considered mid-research |

## Decisions for the maintainer

- **D1 — the wording of the 068 test clause.** Proposed: *"A Base Class is a deliverable that any
  member can realize: a resource declared at the Base must be satisfiable by every provider that
  declares an offering beneath it."*
- **D2 — `instantiable: false` as a Base record field, or a spec rule keyed on an empty
  `elements` list.** A field is explicit and survives a folder gaining shared elements later
  (`Network` has `zone` and `tier` and is still a folder). Recommended: a field.
- **D3 — an orderable hypervisor cluster.** Gap, record only, until a use case asks.
- **D4 — ordering.** Step 3 first, so the mechanical PRs cite a rule that exists.

## Out of scope

Field-level portability metadata (§4) is unchanged. Provider Class naming is unchanged. The
Knowledge family is untouched.
