# Class tiers — Base, Type, and Provider Class

**Related Documents:** [Resource Type Hierarchy](resource-type-hierarchy.md) | [Registry Governance](../governance/registry-governance.md) | [Provider Contract](../contracts/provider-contract.md) | [Portable-value discipline](../principles/portable-values.md)

The home of the **CLS** rule family. This document defines the three class tiers the registry is
built from and the one question every tier answers: *who can realize an order placed here?*
ADR-038 (scoped Classes of shared data elements — portability read off where an element sits)
holds the why. ADR-068 (a Base is earned, not assumed — `Compute` split into `Container`,
`KubernetesCluster` and `Machine`) and ADR-069 (a Base is a deliverable any member can realize)
are the rulings this document turns into rules. The rules here are normative; the register rows
and ADR-038 are cited, never restated.

---

## 1. In one breath

A **class** is a named data contract. There are three tiers, keyed to the name:

| Tier | Name shape | Example | What an order here commits to |
|---|---|---|---|
| **Base Class** | one segment | `Container` | any provider that offers anything beneath it |
| **Type Class** | two segments | `Compute.VM` | any provider that offers this Type or a Provider Class under it |
| **Provider Class** | three segments | `Compute.VM.OCPVirt` | the providers that declare this class — a set, never one |

Each tier extends the one above it by adding or refining elements, never by contradicting them.
Where an element sits is its portability: an element on the Base is honored by every provider in
the family; an element on a Provider Class is honored by the providers that declare that class.
An order may be placed at any tier, and the tier chosen is the portability the consumer is
committing to. That is the whole model. The rest of this document says what earns each tier and
what a name may say.

## 2. What earns a Base Class

A Base Class is **a deliverable that any member can realize**. If a consumer orders a `Machine`,
every provider offering a VM, a bare-metal host, or an LPAR must be able to fill that order. If
that is not true of a grouping, the grouping is a folder, and a folder is not a class anyone can
order from.

This is testable. A grouping earns a Base when all three hold:

1. **An existing, widely used API already treats the members as one thing.** OpenStack Nova with
   Ironic serves VMs and bare metal behind one compute API. Cluster API's `Machine` is a VM or a
   bare-metal host by infrastructure provider. Kubernetes conformance is the abstraction for
   clusters, OCI for containers, CSI for volumes. Where no credible API abstracts over the
   members — a storage volume and a storage pool — there is no contract to share. This is
   adopt-by-reference (core tenet T5) applied to the tier model: the registry does not invent a
   portability claim the industry has not already made.
2. **Every Base element is honorable by every Type and every Provider Class beneath it.** This is
   how `Compute` failed: `Container` inherited `guest_os`, which no container provider can honor.
   The Liskov gate (`LSK-001`, `tests/check_class_liskov.py`) enforces the half of this that is
   decidable — a descendant may add or refine, and may never contradict or drop what its
   ancestors declared — and the class schema offers no way to exclude an inherited element, so
   the other half holds by construction.
3. **An offering declared at any tier accepts orders at every tier above it.** A provider that
   declares `Compute.VM.OCPVirt` satisfies `Compute.VM` and bare `Compute`. Policy-fill
   (DCM ADR-024) completes the blanks a Base-level order leaves. This is what makes "every Class is
   instantiable" (ADR-038 §4) a fact rather than a sentence; the provider contract carries the
   obligation (see `PRV-*`).

The word *move* is deliberately absent. Nothing is migrated from a VM to bare metal. The
portability events are placement at order time, rebuild from stored intent, and provider
substitution; in each the intent stays put and a different member realizes it.

## 3. Folders

A category whose members fail condition 1 is a folder: `Storage` groups volumes, pools and
clusters; `Network` groups VLANs, subnets and DNS zones. Folders are useful as names and harmful
as classes only because every class is orderable. The fix is a flag, not a rename: a folder Base
carries `instantiable: false`, its description says what it groups, and an order placed at it is
refused. It may still carry elements its members inherit — `Network` carries `zone` and `tier`
and is still a folder, because no order moves between a VLAN and a DNS zone.

A member is promoted out of a folder into a Base of its own only when its family needs category,
kind, dialect and offering at once and overflows three segments. That is what forced `Container`
out of `Compute`, and it is the exception, not the pattern.

## 4. What the Type tier is spent on

The second segment narrows the Base along whichever axis carries the definition structure for
that family — ADR-038's shared-then-specialized test — and families legitimately differ:

- **Form.** The members realize one deliverable differently and each form adds elements. A VM
  adds an image and hot-plug; a bare-metal host adds a BMC and boot order; an LPAR adds processor
  units and VIOS-backed I/O. Dialects (KubeVirt, libvirt, vSphere, the Power HMC) land at the
  Provider tier.
- **Dialect.** The deliverable has no form worth a tier and the distributions diverge. An
  OpenShift cluster adds a release channel, FIPS mode and a network type; an EKS cluster adds an
  authentication mode and add-ons. Offerings (a managed service on one cloud, a self-managed
  install, a hosted control plane) land at the Provider tier.

A family spends the Type tier on one axis. Mixing form and dialect as siblings under one Base
makes the second segment mean two things, and the name stops being legible.

## 5. Provider Classes

A Provider Class exists for one reason: the offering needs data the Type does not carry. A
provider that needs nothing beyond the Type binds at the Type and declares no class. Two
deployments of one offering with the same data are two provider *instances* on the authority
axis (ADR-038 §10), distinguished by advertised capability, not two classes. An offering that
requires consumer-supplied data the Type lacks — an account, a region, a set of roles — earns a
Provider Class, because that data must be a declared, versioned element and never an opaque blob.

Depth stops at three. The `resource_type` pattern in `registry/class.schema.json` allows at most
three segments, and that is the cap; version, capability advertisement and authority are the
three cheaper axes to reach for first (ADR-038, *Naming depth*).

## 6. What a name may say

A class is named for its deliverable. A technology name appears only when the technology is the
contract itself — a conformance-tested standard such as Kubernetes, OCI, or Redfish — and never
when it is a product. At the Base tier that means `KubernetesCluster`, `Container`, `Machine`,
and never a vendor. At the Type tier a name is a form or a dialect. At the Provider tier a name
is the offering. The storage class records state the same rule from the other side: the concrete
technology is the provider, never the type name.

### 6.1 Short names

Canonical names are long on purpose; short names are for people. Modelled on Kubernetes
`shortNames`, a class may declare one `short_name` (`K8sCluster` for `KubernetesCluster`,
`Compute.BMH` for `Compute.BareMetalHost`). A short name is accepted wherever a class name is
accepted and is resolved to the canonical name on input. It is never stored: not in `$id`, a
`parent`, an element's `scope`, a relationship `target`, or a provider's offering list. It must
be unique, compared case-insensitively, against every canonical name and every other short name,
and it must match the same pattern a canonical name does so it parses wherever a name parses.
Renaming a short name is a rename and goes through `registry/renames.yaml`. Bare generic words
(`Cluster`, `Namespace`) are not short names; they collide with the next family that needs them.

## 7. Portability, read off the tree

The three tiers are the field-level portability classes of
[resource-type-hierarchy.md §4](resource-type-hierarchy.md#4-portability-classification) seen
structurally: Base elements are `universal`, Type elements `conditional`, Provider Class elements
`provider-specific` or `exclusive`. The tree names and validates. The portability of a given
*request* is computed from field classification and what providers advertise (ADR-PROV-002),
never from the tree alone. Neither replaces the other.

## 8. Rules

| Rule | Statement |
|---|---|
| `CLS-001` | **Three tiers, keyed to the name.** A Base Class has one name segment, a Type Class two, a Provider Class three; `class` MUST match the segment count. Each tier extends the one above by add or refine, never contradict (`LSK-001`). Depth is three; the `resource_type` pattern is the cap. |
| `CLS-002` | **A Base Class is a deliverable that any member can realize.** A grouping earns a Base only when (a) an existing, widely used API already abstracts over its members, (b) every Base element is honorable by every descendant, and (c) an offering declared at any tier accepts orders at every tier above it. A grouping that fails (a) is a folder (`CLS-003`). |
| `CLS-003` | **A folder is non-instantiable, not renamed.** A Base whose members share no abstraction MUST carry `instantiable: false` and a description stating what it groups. An order at a non-instantiable class is refused. Its members stay where they are; a member is promoted to its own Base only when its family overflows three segments. |
| `CLS-004` | **The Type tier is spent on one axis per family.** The second segment narrows by form or by dialect, whichever carries the definition structure. Form and dialect MUST NOT both appear as Types under one Base. |
| `CLS-005` | **A Provider Class exists only for provider-specific data.** A provider needing nothing beyond the Type binds at the Type. Two deployments with the same data are instances on the authority axis. An offering that requires consumer-supplied data the Type lacks MUST declare a Provider Class carrying it as elements, never as an opaque blob. |
| `CLS-006` | **A class is named for its deliverable.** A technology name appears only when the technology is the contract (a conformance-tested standard), never when it is a product. A Base is never named for a vendor; a Type is a form or a dialect; a Provider Class is the offering. |
| `CLS-007` | **One short name, resolved on input, never stored.** A class MAY declare one `short_name` matching the `resource_type` pattern, unique case-insensitively against every canonical name and every other short name. It is accepted at every input surface, canonicalized on write, and MUST NOT appear in `$id`, `parent`, an element `scope`, a relationship `target`, or an offering list. Gate: `tests/check_class_short_names.py`. |
| `CLS-008` | **Instantiability belongs to the Base.** `instantiable` MAY appear only on a Base Class (`class: base`); absent means true. Gate: `tests/check_class_short_names.py`. |

## 9. Conformance

| Enforced by | Rules |
|---|---|
| `registry/class.schema.json` (`class` vs segment count, `resource_type` pattern) and `tests/check_class_liskov.py` | CLS-001 |
| `tests/check_class_liskov.py` (`LSK-001`) plus the absence of an exclusion mechanism in the class schema | CLS-002 (b) |
| review against this document; (c) is a provider-contract obligation carried by `PRV-*` | CLS-002 (a), (c) |
| `registry/class.schema.json` (`instantiable`) and `tests/check_class_short_names.py` | CLS-003, CLS-008 |
| `registry/class.schema.json` (`short_name`), `tests/check_class_short_names.py`, and `registry/tools/resolve_class_address.py`, which accepts a short name and returns the canonical class | CLS-007 |
| review; the Type-axis and naming rules are judgment the register records per family | CLS-004, CLS-005, CLS-006 |
