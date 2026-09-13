# The class-tier program: the series of changes that lands ruling 068

**What this is:** the ordered series of pull requests that takes the registry from where it is
today to the model settled on 2026-09-03 — a Base Class is a deliverable any member can realize —
with the naming, alias, and instantiability rules that go with it. Each entry is one reviewable
change with a stated size, its gates, and what it depends on. The reasoning behind the model is in
[the survey brief](portability-classification-survey.md); this document is the plan, and the
survey is the evidence.

**What it settles:** the order, the boundaries between changes, and what each must ship with.
It does not re-open any decision recorded in the brief.

## The decisions this series applies

| Decision | Recorded where |
|---|---|
| A Base Class is a deliverable that any member can realize; three checkable conditions | survey brief, "The definition"; the 068 register row once reworded (PR 0) |
| The Type tier is spent on whatever carries the structure: form (`Machine`) or dialect (`KubernetesCluster`) | survey brief, "What the Type tier is spent on" |
| An offering that needs consumer-supplied data earns a Provider Class | same |
| A category whose members share no abstraction is a folder: non-instantiable, members unchanged | survey brief, "What this does to folder Bases" |
| `Platform` dissolves into `KubernetesCluster`, `KubernetesNamespace`, `KubernetesNodePool`; the rest become elements, outputs, or a role | survey brief, "Containers and Kubernetes" |
| `Machine` stays and gains `LPAR`; guest firmware converges on Redfish `legacy` / `uefi` | ruling 068, applied clauses |
| Every class may declare one `short_name`, resolved on input, never stored, unique across all names | maintainer decision 2026-09-03, modelled on Kubernetes `shortNames` |
| No hypervisor-cluster Base, no `Kubernetes.Cluster` name, no registry-wide re-tiering | survey brief, "Dropped" |

## The series

Sizes are estimates against the reference point of PR #568, which swept 121 references across
53 files for +268/−359. The cap is 3,000 lines and one subject per PR; any entry that overflows
splits at the line marked.

**Reordered 2026-09-10.** `Machine` now lands third instead of fifth. The first order had the
`Compute` rename waiting on the whole `Platform` dissolution; the only real dependency is that
`Compute.Cluster` leaves `Compute` first, and that is one small PR. The register row 069 that
rewords the Base test landed with PR 1 rather than before #569 merged, because #569 merged with
the old clause.

### PR 0 — land what was open ✔

#568 (`Container` Base) and #569 (the 068 register row) merged 2026-09-10. #569 carries the old
test clause; row 069 in PR 1 supersedes it.

### PR 1 — the normative tier section and its two schema fields (#572)

| | |
|---|---|
| Content | the class-tiers spec document under docs/spec/foundations (`CLS-001`–`CLS-008`): the three tiers; the three Base conditions; the Type-axis rule; offerings earn a Provider Class; folder Bases are non-instantiable; a technology's name appears only when it is the contract; the `short_name` rule. Register row 069 |
| Schema | `instantiable` (Base only, default true) and `short_name` on `registry/class.schema.json` |
| Gates | a short-names gate under tests/: short names unique case-insensitively, never in a stored reference; `instantiable` only on a Base. Condition (b) is enforced by the existing Liskov gate plus the absence of an exclusion mechanism, so no separate gate |
| Tooling | `registry/tools/resolve_class_address.py` accepts a short name and canonicalizes it |
| Depends on | nothing |

### PR 2 — `Compute.Cluster` becomes the `KubernetesCluster` Base

| | |
|---|---|
| Content | the cluster record moves out of the former compute directory to the kebab-cased Base path under registry/classes/resource (kubernetes-cluster/_base.yaml); `class: base`, no parent, version 1.0.0, same uuid; description states the contract (Kubernetes conformance) and that Types will be distributions |
| Sweep | 98 references outside `docs/adr/` and `docs/research/`; 8 citing class records patch-bumped with `$id` in step; `renames.yaml`; regenerate class specs, type catalog, pin manifest, model health |
| Not yet | `short_name: K8sCluster` waits for PR 1's schema field; PR 4 adds it |
| Depends on | nothing (schema unchanged) |

### PR 3 — `Compute` becomes `Machine`

| | |
|---|---|
| Content | `Compute` → `Machine`; `Compute.VM` → `Machine.VM`; `Compute.BareMetalHost` → `Machine.BareMetalHost`; guest firmware converges on Redfish `legacy` / `uefi` — VM's `bios` and BareMetalHost's `boot_mode` become one element; the `vm_firmware` vocabulary declaration is dropped and the enum is sole authority (closes #564); `Storage.Cluster`'s two `depends_on` edges follow. The examples in `class-tiers.md` sweep to `Machine.*`; the history sentence about why `Compute` failed keeps its name |
| New | `Machine.LPAR` Type: processor units, capped or uncapped sharing, VIOS-backed I/O; Redfish has no LPAR profile, so the elements are named from the HMC vocabulary and marked `conditional` |
| Bump | MAJOR on `Machine.VM` (firmware rename); minor elsewhere |
| Short names | `Machine.BMH` once PR 1 has landed; otherwise a follow-up |
| Depends on | PR 2 |

### PR 4 — `Platform` dissolves into the remaining Kubernetes Bases

| | |
|---|---|
| Content | `Platform.Namespace` → `KubernetesNamespace` (`K8sNamespace`); `Platform.NodePool` → `KubernetesNodePool` (`K8sNodePool`); `Platform.ResourceQuota` folds into namespace elements; `Platform.StorageClass` becomes a storage output; `Platform.Hub` becomes `fleet_manager` / `hosted_control_planes` role elements on `KubernetesCluster`; `Platform` deleted; `KubernetesCluster` gains `short_name: K8sCluster` |
| Also | `KubernetesCluster.node_pools` (inline) versus `KubernetesNodePool` (a class): ruled 2026-09-12 (row 072) — the cluster carries no pools; every pool is a record; a cluster with pools is a composition |
| Sweep | 193 `Platform.*` references outside `docs/adr/` |
| Size | near the cap. **Split line:** 4a = namespace and node-pool promotion; 4b = the three folds and the `Platform` delete |
| Depends on | PR 1 (short names), PR 2 |

### PR 5 — folder Bases become non-instantiable

| | |
|---|---|
| Content | `instantiable: false` and a one-line "what this groups" on `Storage`, `Data`, `Network`, `Security`, `Observability`, `Software`, `Facility`, `Hardware` |
| Bump | minor on each |
| Depends on | PR 1 (the field) |

### PR 6 — the provider contract describes itself correctly

| | |
|---|---|
| Content | both projection comments in `docs/spec/contracts/provider-contract.md` say "PROJECTION of … Provider Classes" and list Types. Rewrite to: a provider binds at Base or Type; a Provider Class exists only for provider-specific data; declaring at a tier accepts orders at every tier above |
| Depends on | PR 1 |

### PR 7 — amend ADR-038

| | |
|---|---|
| Content | addendum: the depth cap is three and already enforced by the `resource_type` pattern; the tier definitions live in `class-tiers.md`; offerings can earn a Provider Class; "all Classes are instantiable" is qualified by `instantiable: false` |
| Depends on | PRs 1–6 |

## Status — 2026-09-12

| PR | What | State |
|---|---|---|
| 0 | #568 `Container` Base; #569 ruling 068 | merged |
| 1 | #572 class-tiers spec section, `instantiable` + `short_name`, gate, row 069 | merged |
| — | #573 series reorder; #570 survey; #571 per-state records brief | merged |
| 2 | #574 `Compute.Cluster` → `KubernetesCluster` | merged |
| 3 | #575 `Compute` → `Machine`, `LPAR`, Redfish firmware, closes #564 | merged |
| 4a | #576 `KubernetesNamespace`, `KubernetesNodePool`, the `K8s*` short names | merged |
| 4b | #577 `Storage.Class`, fleet-manager service kind, quota folded, `Platform` deprecated | merged |
| 5 | #579 folder Bases `instantiable: false` — eight records, minor bumps | merged |
| 6 | #580 provider-contract projection prose | merged |
| 7 | register row 070 amending ADR-038 (an Accepted record is immutable — ADR-REAL-004 — so the amendment is a row, as 069 was for 068) | **open** |

**Rulings waiting on the maintainer**

- `KubernetesCluster.node_pools` (inline) versus `KubernetesNodePool` (class): ruled 2026-09-12, row 072 —
  records only; the cluster's inline list is removed.
- Removing `Platform`, `Platform.Hub` and `Platform.ResourceQuota`: done 2026-09-13 on a pre-1.0
  override of the sunset window (row 073).

**Follow-ups outside the series**

- The per-state records program (#571): four record schemas replacing the folded one;
  coordinated with the DCM control plane; lands after PR 7.
- `realize_resources/Container` and `/KubernetesCluster` were added to the capability taxonomy
  in PR 3 because the triad gate required it; the `compute-provisioning` grouping label under
  them was not renamed.
- Gaps recorded, not built: an orderable hypervisor cluster; `Data.Stream`; a batch cluster;
  segment aliases; the #474 rule-ID renumber.

## Gaps recorded, not built

Each becomes an issue when the series is under way; none blocks it.

- An orderable hypervisor cluster as a deliverable of its own (vSphere, Proxmox, a libvirt
  host). No use case asks.
- `Data.Stream` / `Data.Queue`: named in the category table, no Type exists.
- A batch or HPC cluster (Slurm, Ray, Kueue). `Job` covers the run; nothing covers the cluster.
- Segment aliases (`K8s` for `Kubernetes` as a leading token). Whole-name short names first.
- The #474 step-3 rule-ID renumber (`CMP-*` → `TPL-*`) is unrelated mechanical work still unclaimed.

## Discipline that applies to every PR

- `docs/adr/` is excluded from every reference sweep; a decision record names the surface as it
  stood.
- Every touched published class record is patch-bumped with `$id` in step, then class specs,
  type catalog, pin manifest and model health are regenerated. Reset `registry/pin-manifest.json`
  from `origin/main` first.
- Every rename goes in `registry/renames.yaml` so compat and identity gates see a rename, not a
  delete-plus-add.
- `bash scripts/signoff.sh`, untruncated, before opening the PR. The estate-token scrub is a hard
  gate: no host names.
- Branch from a freshly fetched `origin/main`, never from another feature branch.
- Merging is the maintainer's action.
