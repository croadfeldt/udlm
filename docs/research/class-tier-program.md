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

### PR 0 — land what is open

| | |
|---|---|
| Content | merge #568 (`Container` Base) and #569 (the 068 register row) |
| Change first | reword #569's test clause to *"A Base Class is a deliverable that any member can realize: a resource declared at the Base must be satisfiable by every provider that declares an offering beneath it."* The applied clauses stand |
| Depends on | nothing |
| Owner | maintainer; both merges are the maintainer's call |

### PR 1 — the normative tier section and its two schema fields

The centre of the program. It lands first so every later PR cites a rule that exists instead of
an ADR that cannot be corrected.

| | |
|---|---|
| Content | a normative section in `docs/spec/foundations/` defining Base / Type / Provider Class; the three Base conditions; the Type-axis rule; offerings earn a Provider Class; folder Bases are non-instantiable; a technology's name appears only when it is the contract (Kubernetes, OCI, Redfish), never a vendor's; the `short_name` rule |
| Schema | `instantiable` (boolean, default true) and `short_name` (string, `resource_type` pattern) on `registry/class.schema.json` |
| Gates | **honorable-elements**: no Type or Provider Class leaves a Base element unhonorable — pairs with the Liskov check. **short-name uniqueness**: unique, case-insensitive, against every canonical name, every other short name, and every old name in `registry/renames.yaml`. **stored-canonical**: no short name in `$id`, `parent`, `scope`, an edge `target`, or an offering list |
| Tooling | a resolver that accepts a canonical or short name at every input surface and canonicalizes on write |
| Also | `registry-governance.md` stops delegating the model to ADR-038 and cites the section |
| Size | ~300 lines of spec, ~60 of schema, ~250 of gates; no class records touched |
| Depends on | PR 0 (cites the reworded row) |

### PR 2 — folder Bases become non-instantiable

| | |
|---|---|
| Content | `instantiable: false` and a one-line "what this groups" replacing "Empty category base — the promotion target" on `Storage`, `Data`, `Network`, `Security`, `Observability`, `Software`, `Facility`, `Hardware` |
| Bump | minor on each: description-only by the letter, but it changes what the Base means (survey D5) |
| Regenerate | class specs, type catalog, pin manifest (reset from `origin/main` first), model health |
| Size | 8 records plus generated output; small |
| Depends on | PR 1 (the field) |

### PR 3 — `Platform` dissolves into the Kubernetes Bases

| | |
|---|---|
| Content | `Compute.Cluster` → `KubernetesCluster` (Base, `short_name: K8sCluster`); `Platform.Namespace` → `KubernetesNamespace` (`K8sNamespace`); `Platform.NodePool` → `KubernetesNodePool` (`K8sNodePool`); `Platform.ResourceQuota` folds into namespace elements; `Platform.StorageClass` becomes a storage output; `Platform.Hub` becomes `fleet_manager` / `hosted_control_planes` role elements on the cluster; `Platform` deleted |
| Also | `KubernetesCluster.node_pools` (inline) versus `KubernetesNodePool` (a class): keep the class, the inline array becomes references — T7 reduce-to-existing |
| Sweep | 98 `Compute.Cluster` and 193 `Platform.*` references outside `docs/adr/`; every rename in `renames.yaml`; every citing record patch-bumped with `$id` in step; regenerate |
| Size | at the cap. **Split line:** 3a = cluster rename + node-pool reference; 3b = namespace and node-pool promotion, the three folds, and the `Platform` delete |
| Depends on | PR 1 (short names, gates) |

### PR 4 — `Compute` becomes `Machine`

| | |
|---|---|
| Content | `Compute` → `Machine`; `Compute.VM` → `Machine.VM`; `Compute.BareMetalHost` → `Machine.BareMetalHost` (`short_name: Machine.BMH`); guest firmware converges on Redfish `legacy` / `uefi` — VM's `bios` and BareMetalHost's `boot_mode` become one element; the `vm_firmware` vocabulary declaration is dropped and the enum is sole authority (closes #564); `Storage.Cluster`'s two `depends_on` edges follow |
| New | `Machine.LPAR` Type: processor units, capped or uncapped sharing, VIOS-backed I/O; Redfish has no LPAR profile, so the elements are named from the HMC vocabulary and marked `conditional` |
| Bump | MAJOR on `Machine.VM` (firmware rename); minor elsewhere |
| Size | comparable to #568 |
| Depends on | PR 3 (so `Compute` is empty of everything but VM and BareMetalHost when it renames) |

### PR 5 — the provider contract describes itself correctly

| | |
|---|---|
| Content | both projection comments in `docs/spec/contracts/provider-contract.md` say "PROJECTION of … Provider Classes" and list Types. Rewrite to: a provider binds at Base or Type; a Provider Class exists only for provider-specific data; declaring at a tier accepts orders at every tier above |
| Size | prose only; small |
| Depends on | PR 1 (cites the section) |

### PR 6 — amend ADR-038

Last, because an Accepted ADR is amended by addendum and the addendum should cite settled text.

| | |
|---|---|
| Content | addendum recording that the depth cap is three and already enforced by the `resource_type` pattern (the prose says "unbounded, but governed"); that the tier definitions now live in the spec section; that offerings can earn a Provider Class; and that "all Classes are instantiable" is qualified by `instantiable: false` |
| Size | one addendum |
| Depends on | PRs 1–5 |

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
