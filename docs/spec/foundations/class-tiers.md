# Class tiers — Base, Type, and Provider Class

**Related Documents:** [Resource Type Hierarchy](resource-type-hierarchy.md) | [Registry Governance](../governance/registry-governance.md) | [Provider Contract](../contracts/provider-contract.md) | [Portable-value discipline](../principles/portable-values.md)

The home of the **CLS** rule family. This document defines the three class tiers the registry is
built from and the one question every tier answers: *who can realize an order placed here?*
ADR-038 (scoped Classes of shared data elements — portability read off where an element sits)
holds the why. ADR-068 (a Base is earned, not assumed — `Compute` split into `Container`,
`KubernetesCluster` and `Machine`) and ADR-069 (a Base is a deliverable any member can realize)
are the rulings this document turns into rules. ADR-082 (a class is defined once and filed under
usage groups like hard links; the folder Bases dissolve) adds the grouping system in §3. The rules
here are normative; the register rows and ADR-038 are cited, never restated.

---

## 1. In one breath

A **class** is a named data contract. There are three tiers. The tier is what `class` declares and
`parent` derives; the name renders the ancestry, one segment per tier:

| Tier | Name shape | Example | What an order here commits to |
|---|---|---|---|
| **Base Class** | one segment | `Container` | any provider that offers anything beneath it |
| **Type Class** | two segments | `Machine.VM` | any provider that offers this Type or a Provider Class under it |
| **Provider Class** | three segments | `Machine.VM.OCPVirt` | the providers that declare this class — a set, never one |

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
   declares `Machine.VM.OCPVirt` satisfies `Machine.VM` and bare `Machine`. Policy-fill
   (DCM ADR-024) completes the blanks a Base-level order leaves. This is what makes "every Class is
   instantiable" (ADR-038 §4) a fact rather than a sentence; the provider contract carries the
   obligation (see `PRV-*`).

The word *move* is deliberately absent. Nothing is migrated from a VM to bare metal. The
portability events are placement at order time, rebuild from stored intent, and provider
substitution; in each the intent stays put and a different member realizes it.

## 3. Groups — where a class is filed

Two systems share the registry and are kept apart on purpose (ADR-082):

- **The definition system** is the three tiers above. It answers *what is this and who can realize
  it*. A name carries definition only: `StorageCluster`, `StorageCluster.Ceph`,
  `StorageCluster.Ceph.<Provider>`.
- **The grouping system** answers *where do people look for it*. A class declares
  `filed_under: [hardware, storage]` — one or more terms of the usage-group vocabulary
  (`registry/taxonomies/usage-group.yaml`, on the TaxonomyTerm machinery). Unix hard-link semantics:
  the class is the inode (one identity, tier, parent, elements, version); a group is a directory; a
  filing is a link. Adding or removing a filing changes nothing about the class — no version bump,
  no digest change, no record touched.

The former folder Bases (`Hardware`, `Network`, `Storage`, `Security`, `Software`, `Data`,
`Facility`, `Observability`) mixed the two systems: a folder was a Base that could not pass the Base
test, and every member carried a name that promised a family contract the folder could not honour.
They dissolve into group terms. Each former member becomes a Base in its own right if it passes
CLS-002, or is re-homed under a Base that does; `Hardware` is a group, not a Base, because it
represents no portable data — `device_class` is a discriminator, not a deliverable.

**On disk** (ADR-061 kept): a class's directory is named for the class. Git has no hard links, so a
Base lives in ONE group directory — its hosting group, `registry/classes/<family>/<group>/<class>/`
— and every other filing is a generated view (`registry/generated/groups/<group>.json`). The hosting
group is one of the terms in `filed_under`; moving a home is a `git mv`. The Resource and Access families have the group level; Knowledge and
Process classes keep `<family>/<class>` until a family has two groups.

**Delimiters are never shared.** `/` is a locator (a directory, a URF path segment); `.` is a tier.
`storage/storage-cluster/ceph` is where a file is; `StorageCluster.Ceph` is what it is;
`Storage.StorageCluster` is forbidden, because it reads as Base.Type. A Base name therefore stands
alone: it is filed in several directories and referenced with none. Where a widely used standard
already spells the thing, that spelling wins (Redfish, Swordfish: `StoragePool`, `NetworkAdapter`).

**Grouping of instances** is `Grouping` (register row 063), not this. A filing is on the class
only: no record of any kind carries `filed_under`; a record's groups resolve through its
`resource_type` to the class's *current* filing, never to the version it pinned. Content is
versioned; links are current. The entity view may carry a computed `filed_under` for readers, the
way it carries `lifecycle_state`. A rename is identity and touches records once; a filing is
organization and touches none.

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
`Machine.BMH` for `Machine.BareMetalHost`). A short name is accepted wherever a class name is
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
| `CLS-001` | **Three tiers, keyed to the declaration.** `class` states the tier; `parent` derives it: a Base has no parent, a Type's parent is a Base, a Provider Class's parent is a Type. The name renders the ancestry — one segment per tier, `Base.Type.Provider` — and MUST agree with it; the name never defines the tier. Each tier extends the one above by add or refine, never contradict (`LSK-001`). Depth is three; the `resource_type` pattern is the cap. |
| `CLS-002` | **A Base Class is a deliverable that any member can realize.** A grouping earns a Base only when (a) an existing, widely used API already abstracts over its members, (b) every Base element is honorable by every descendant, and (c) an offering declared at any tier accepts orders at every tier above it. A grouping that fails (a) is a folder (`CLS-003`). |
| `CLS-003` | **A grouping that fails the Base test is a usage group, not a class.** Nothing is filed as a Base to be found; it is filed under a term of the usage-group vocabulary (`CLS-010`). A member of a former folder becomes a Base in its own right when it passes `CLS-002`, else is re-homed under a Base that does. An `instantiable: false` Base was tolerated only while its dissolution was in progress (ADR-082); none remains: the Access family gained its group level in row 089. |
| `CLS-004` | **The Type tier is spent on one axis per family.** The second segment narrows by form or by dialect, whichever carries the definition structure. Form and dialect MUST NOT both appear as Types under one Base. |
| `CLS-005` | **A Provider Class exists only for provider-specific data.** A provider needing nothing beyond the Type binds at the Type. Two deployments with the same data are instances on the authority axis. An offering that requires consumer-supplied data the Type lacks MUST declare a Provider Class carrying it as elements, never as an opaque blob. |
| `CLS-006` | **A class is named for its deliverable.** A technology name appears only when the technology is the contract (a conformance-tested standard), never when it is a product. A Base is never named for a vendor; a Type is a form or a dialect; a Provider Class is the offering. |
| `CLS-007` | **One short name, resolved on input, never stored.** A class MAY declare one `short_name` matching the `resource_type` pattern, unique case-insensitively against every canonical name and every other short name. It is accepted at every input surface, canonicalized on write, and MUST NOT appear in `$id`, `parent`, an element `scope`, a relationship `target`, or an offering list. Gate: `tests/check_class_short_names.py`. |
| `CLS-008` | **Instantiability belongs to the Base.** `instantiable` MAY appear only on a Base Class (`class: base`); absent means true. Gate: `tests/check_class_short_names.py`. |
| `CLS-010` | **A class is filed, not nested.** A Base MAY declare `filed_under`: a set of canonical terms of the usage-group taxonomy (`registry/taxonomies/usage-group.yaml`). Types and Provider Classes inherit their Base's filing and MUST NOT declare one. No record of any kind carries `filed_under`; a record's groups resolve through `resource_type` to the class's current filing. A filing is organization: adding or removing one bumps no version and changes no digest (identity-excluded). Gate: `tests/check_class_groups.py`. |
| `CLS-011` | **Link count is at least one.** Every instantiable Base of a family with a group level (Resource, Access) names at least one usage group. Gate: `tests/check_class_groups.py`. |
| `CLS-012` | **Delimiters are never shared.** `.` separates tiers and nothing else; `/` locates and never names. A group MUST NOT appear in a class name (`Storage.StorageCluster` is refused: it reads as Base.Type). A Base name stands alone; where a widely used standard spells it, that spelling wins. |
| `CLS-013` | **One hosting directory, many views.** A Base's file sits in exactly one group directory, `registry/classes/<family>/<group>/<class>/`, and that group is one of its filings (`CLS-PATH-001`); every other filing is a generated view under `registry/generated/groups/`. Moving a home is a `git mv`, never a record change. |
| `CLS-009` | **An element's `role` only narrows.** An element may declare a data role (`registry/class.schema.json`; vocabulary in `common-elements.schema.json`). Absent means execution: required by every provider that binds the class (DSP-002). A non-execution role removes the element from the required set for every descendant. No role adds to what a provider gets; only policy does (DSP-003). |

## 9. Conformance

| Enforced by | Rules |
|---|---|
| `registry/class.schema.json` (`class`, `parent`, `resource_type` pattern), `tests/check_class_paths.py` (name agrees with ancestry) and `tests/check_class_liskov.py` | CLS-001 |
| `tests/check_class_groups.py` (filing on a Base only, canonical terms, never on a record, link count); `registry/tools/generate_pin_manifest.py` (`filed_under` identity-excluded); `registry/examples/must-reject/023` | CLS-010, CLS-011 |
| `tests/check_class_paths.py` (hosting group is a filing) and `registry/tools/generate_class_specs.py` (group views) | CLS-013 |
| review against §3; the `resource_type` pattern admits the shape, the register records the spelling per family | CLS-012 |
| `tests/check_class_liskov.py` (`LSK-001`) plus the absence of an exclusion mechanism in the class schema | CLS-002 (b) |
| review against this document; (c) is a provider-contract obligation carried by `PRV-*` | CLS-002 (a), (c) |
| `registry/class.schema.json` (`instantiable`) and `tests/check_class_short_names.py`; `registry/tools/generate_class_specs.py` serves a flat spec for every instantiable Base, so an order at a Base validates its fields | CLS-003, CLS-008 |
| `registry/class.schema.json` (`short_name`), `tests/check_class_short_names.py`, and `registry/tools/resolve_class_address.py`, which accepts a short name and returns the canonical class | CLS-007 |
| review; the Type-axis and naming rules are judgment the register records per family | CLS-004, CLS-005, CLS-006 |
