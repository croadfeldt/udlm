# Use-case enablement map — the 21 release use cases across three layers

**What this is:** one row per release use case in `registry/UDLM-0.1-SCOPE.md`, with a cell for each
of the three layers that has to exist before the use case runs. **What it settles:** what "Covered" in
the scope manifest means. It means the model layer only. This map says, per row, what exists in the
other two layers today and where.

Snapshot date: 2026-09-15. Evidence is a path or a commit in one of five repositories; a cell with no
evidence says `none`.

## The three layers

| Layer | What it means | Where the evidence lives |
|---|---|---|
| **Model** | The UDLM shape exists: a class, a record schema, or a contract section, checked by the registry gates. | croadfeldt/udlm, this repository. The cell repeats the manifest's "UDLM basis" column. |
| **Control plane** | Something evaluates, orders, places, records, or refuses. Two sub-cells: **design** (a DCM architecture decision whose title covers the row) and **code** (a code path in the control-plane monolith). | Design: croadfeldt/dcm, `architecture/adr/`. Code: croadfeldt/control-plane, a fork of the dcm-project monolith, last synced with upstream 2026-07-23, 28 commits. |
| **Provider** | Something realizes the resource from intent, or reports what it found. | croadfeldt/dcm-provider-libvirt (Ansible VM reconciler, DCM wrap is design-only). The homelab discovery sweep, which writes records into the homelab estate repository (private). No OSAC provider exists. |

Cell vocabulary: `shape` (model layer present), `designed` (a DCM ADR covers it), `code` (a code path
exists and does what the row needs), `partial` (a code path exists but does less than the row needs;
the cell says what), `reports` (a provider writes discovered records for it), `realizes` (a provider
builds it from intent), `none`.

## The map

| # | Use case | Model | Control plane: design | Control plane: code | Provider |
|---|---|---|---|---|---|
| 1 | compute/vm-resource-representation | shape: `Machine.VM` 2.0.0, state-record / entity-view | designed: DCM ADR-003 four lifecycle states | partial: the catalog holds a VM service type generated from the registry (cmd/udlm-servicetype-gen). No per-state records. The generator reads a registry directory that is now empty (finding 3 below). | realizes: dcm-provider-libvirt builds VMs from its own Ansible spec, not from a UDLM intent record. reports: the discovery sweep writes VM records into the homelab estate repository. |
| 2 | architecture/solution-architecture-decomposition | shape: `Template.Application`, composition record | designed: DCM ADR-016 application definition language | partial: multi-resource catalog items with `depends_on` between components (internal/catalog). No composition record, no realized receipt. | none |
| 3 | compute/provision-vm-standard | shape: profile-resolution, policy §7.7, universal-audit | designed: DCM ADR-004 catalog, ADR-007 placement, ADR-006 policy engine | partial: the monolith's main path is catalog → placement → OPA policy → service-provider provisioning. No profile resolution, no audit record. | realizes: dcm-provider-libvirt, from its own spec. |
| 4 | compute/vm-intent-osac-placement | shape: provider-contract §8, provider provenance | designed: DCM ADR-007, ADR-019 placement policy, ADR-011 data residency | partial: placement selects a provider through policy. No provider provenance on the result. | none: no OSAC provider is registered anywhere. |
| 5 | compute/vm-status-provenance | shape: per-state records, field-level provenance | designed: DCM ADR-003 | none | none: dcm-provider-libvirt reads `virsh` status but writes no record. |
| 6 | storage/provision-volume-bound-to-pool | shape: `Storage.Volume`, tenancy, quota | none by title | partial: a storage service type exists in the catalog (upstream #22). No tenancy, no quota. | reports: the discovery sweep records pools and volumes. No storage provider realizes from intent. |
| 7 | cross-domain/udlm-dependency-graph-data-model | shape: ordering `edge_type`s, ADR-010 derivation | designed: DCM ADR-008 dependency resolution, ADR-024 change impact | partial: `depends_on` exists only inside a multi-resource catalog item. No graph query, no blast radius. Outside the control plane, the homelab estate repository derives shutdown and startup order from stored edges (tools/shutdown_order.py). | reports: the discovery sweep writes `contained_by` and `depends_on` edges. |
| 8 | compute/cross-provider-dependency-ordering | shape: graph-integrity DAG, ADR-011 reserve ordering | designed: DCM ADR-008 | none | none |
| 9 | intent-fulfillment/operational-dependency-cascade | shape: ADR-010 `UnmetDependency` | designed: DCM ADR-008 | none | none |
| 10 | cross-domain/dynamic-rehydration | shape: four-states §5, intent replayed, UUID preserved | designed: DCM ADR-020 migration and operational gating | partial: `RehydrateResource` re-evaluates the stored spec through policy and provisions a new resource under a new ID, then deletes the old one (internal/placement/service/placement.go). The UUID is not preserved and nothing is derived from the graph. | none |
| 11 | compute/vm-provision-provider-failure-refused | shape: policy §13 recovery, ADR-011 release | designed: DCM ADR-005 provider abstraction, ADR-006 | partial: the rehydrate path rolls back when provider provisioning fails. No typed refusal record. | none |
| 12 | observability/rehydration-rto-measurement | shape: ADR-003 rto/rpo | none by title | none | none |
| 13 | compute/idempotent-reconvergence | shape: `generation` / `observed_generation` | designed: DCM ADR-003 | none: no generation tracking. | none |
| 14 | observability/drift-detection-remediation | shape: four-states §6 drift record | designed: DCM ADR-017 discovered ingestion | none in the control plane. the homelab estate repository diffs a new sweep against stored records (tools/discovery_diff.py, discovery_apply.py). | reports: each sweep is a drift input. |
| 15 | governance/audit-merkle-tree-verification | shape: universal-audit §8 | designed: DCM ADR-010 tamper-evident audit | none: the word audit does not appear in the monolith's code. the homelab estate repository materializes provenance from git history (tools/provenance.py, minimal profile). | none |
| 16 | governance/policy-override-approval | shape: policy-contract §18, `override` policy_type | designed: DCM ADR-013 override governance | none | none |
| 17 | osac/cloud-provider-registration | shape: provider-contract §8.1a capacity advertisement | designed: DCM ADR-005, ADR-023 naturalization boundary | partial: providers register and are health-checked (internal/sp). Capacity advertisement not verified in code. | none: no OSAC provider. |
| 18 | osac/provider-portability-new-cloud | shape: naturalization, `bound_providers` | designed: DCM ADR-023 | none beyond the re-placement in row 10. | none |
| 19 | governance/policy-resolution-capability | shape: policy-contract §7.7 three-state | designed: DCM ADR-006, ADR-027 policy firewall | partial: OPA evaluates policy on placement (internal/policy/opa, internal/placement/policy). The three-state verdict is not verified in code. | none |
| 20 | cross-domain/profile-resolution-capability | shape: `profile` record and instances | designed: DCM ADR-012 data assembly layering | none | none |
| 21 | governance/audit-chain-proofs-capability | shape: universal-audit §8 | designed: DCM ADR-010 | none | none |

## Counts

| Layer | Present | Partial | None |
|---|---|---|---|
| Model | 21 | 0 | 0 |
| Control plane: design | 19 | 0 | 2 (rows 6, 12) |
| Control plane: code | 0 | 10 (rows 1, 2, 3, 4, 6, 7, 10, 11, 17, 19) | 11 |
| Provider: realizes from a UDLM intent record | 0 | 1 (row 1: libvirt reconciler, from its own spec) | 20 |
| Provider: reports discovered records | 4 (rows 1, 6, 7, 14) | 0 | 17 |

## What the evidence says

1. **The model is complete for the release set and nothing runs it.** Every row has a shape, gated in
   this repository. No row has a control-plane code path that does what the row needs, and no provider
   consumes a UDLM intent record or writes a realized record.
2. **The monolith implements one path.** Catalog, placement, OPA policy, and service-provider
   provisioning. That path touches rows 3, 4, 17, and 19. Everything the model added since the split
   is absent from it: per-state records, provenance, the audit chain, drift, generation tracking,
   graph queries, override, quota, tenancy, sovereignty.
3. **The monolith's link to the registry is broken.** Its service-type generator reads
   `registry/resource-types/<file>` for five classes (compute.virtual-machine, compute.container,
   data.database, compute.cluster, storage.volume). That directory is empty in this repository. The
   classes now live under `registry/classes/` with the names `Machine.VM`, `Compute.Container`,
   `Data.Database`, `KubernetesCluster`, and `Storage.Volume`, and the class record shape changed with
   them. The generator has no input to read.
4. **The only real estate data is in the superseded record shape.** The homelab estate repository holds 291 records
   under a folded `states:` block and validates them against the read-model schema. This repository
   forbids that shape for stored records (RHY-006). Discovered records dominate: 284 discovered, 5
   intent, 1 realized, 1 decommissioned.
5. **The one provider is not wired.** dcm-provider-libvirt reconciles VMs idempotently from its own
   Ansible spec. Its UDLM wrap (intent in, realized record out) is a design note, dated 2026-06-22,
   with no code.

## What follows from it

These are the gaps in the order they block each other. Each names the row it unblocks.

- **Point the monolith's service-type generator at `registry/classes/`** and the five current class
  names. Unblocks nothing on its own, but every later item reads the registry through it. Rows 1, 6.
- **Migrate the homelab estate repository to per-state records** (one record per state, RHY-006). This gives the
  homelab a discovered-record set the control plane can read. Rows 5, 7, 14.
- **Wire dcm-provider-libvirt as a provider**: accept an intent record, emit a realized record with
  per-field provenance. This is the first provider that closes the loop. Rows 1, 3, 5.
- **Per-state records in the control plane write path.** Until the monolith writes intent, requested,
  and realized records, none of rows 5, 10, 13, 14 can be checked against a running system.
- **Audit chain.** Rows 15, 21 need a writer. Nothing in the monolith produces an audit record.
- **Graph queries.** Convergence order and blast radius over stored edges. Rows 7, 8, 9.

Rows 4, 17, 18 wait on an OSAC provider, which is outside this program's repositories.
