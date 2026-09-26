# Use-case enablement map — the 21 release use cases across three layers

**What this is:** one row per release use case in `registry/UDLM-0.1-SCOPE.md`, with a cell for each
of the three layers that has to exist before the use case runs. **What it settles:** what "Covered" in
the scope manifest means. It means the model layer only. This map says, per row, what exists in the
other two layers today and where.

Snapshot date: 2026-09-27 (first snapshot 2026-09-15). Evidence is a path or a commit in one of five
repositories; a cell with no evidence says `none`. Control-plane code cells name the branch: `main` is the
fork's upstream-synced main; `udlm-native` is the fork's integration branch for UDLM work; its plan document is
docs/udlm-native.md in that repository.

## The three layers

| Layer | What it means | Where the evidence lives |
|---|---|---|
| **Model** | The UDLM shape exists: a class, a record schema, or a contract section, checked by the registry gates. | croadfeldt/udlm, this repository. The cell repeats the manifest's "UDLM basis" column. |
| **Control plane** | Something evaluates, orders, places, records, or refuses. Two sub-cells: **design** (a DCM architecture decision whose title covers the row) and **code** (a code path in the control-plane monolith). | Design: croadfeldt/dcm, `architecture/adr/`. Code: croadfeldt/control-plane, a fork of the dcm-project monolith, synced with upstream at dd2caea (2026-09-23) on 2026-09-27; the `udlm-native` branch carries increments 1–5 of its UDLM plan. |
| **Provider** | Something realizes the resource from intent, or reports what it found. | croadfeldt/dcm-provider-libvirt (Ansible VM reconciler, DCM wrap is design-only). The homelab discovery sweep, which writes records into the homelab estate repository (private). No OSAC provider exists. |

Cell vocabulary: `shape` (model layer present), `designed` (a DCM ADR covers it), `code` (a code path
exists and does what the row needs), `partial` (a code path exists but does less than the row needs;
the cell says what), `reports` (a provider writes discovered records for it), `realizes` (a provider
builds it from intent), `none`.

## The map

| # | Use case | Model | Control plane: design | Control plane: code | Provider |
|---|---|---|---|---|---|
| 1 | compute/vm-resource-representation | shape: `Machine.VM` 2.0.0, state-record / entity-view | designed: DCM ADR-003 four lifecycle states | code (`udlm-native`): the VM service type is generated from `registry/generated/machine.vm.json` (main, #4); an intent record is persisted per resource, a realized record is written from the agent's report, and both are retrievable as records or as the computed entity view over `GET /api/v1alpha1/udlm/entities/{uuid}` (#6, #7). Missing: nothing this row asks for. | realizes: dcm-provider-libvirt builds VMs from its own Ansible spec, not from a UDLM intent record. reports: the discovery sweep writes VM records into the homelab estate repository. |
| 2 | architecture/solution-architecture-decomposition | shape: `Template.Application`, composition record | designed: DCM ADR-016 application definition language | partial (main): multi-resource catalog items with `depends_on` between components, executed as a run that provisions level by level (upstream #39, #53) and rehydrates as a whole (upstream #67). No composition record, no realized receipt. | none |
| 3 | compute/provision-vm-standard | shape: profile-resolution, policy §7.7, universal-audit | designed: DCM ADR-004 catalog, ADR-007 placement, ADR-006 policy engine | partial (`udlm-native`): catalog → placement → OPA policy → agent dispatch, with intent, requested and realized records written along the way (#6). No profile resolution, no audit record. | realizes: dcm-provider-libvirt, from its own spec. |
| 4 | compute/vm-intent-osac-placement | shape: provider-contract §8, provider provenance | designed: DCM ADR-007, ADR-019 placement policy, ADR-011 data residency | partial: placement selects a provider through policy. No provider provenance on the result. | none: no OSAC provider is registered anywhere. |
| 5 | compute/vm-status-provenance | shape: per-state records, field-level provenance | designed: DCM ADR-003 | code (`udlm-native`): the realized record carries every output the agent reported with `provenance` naming the agent and the status event's time; a later report with changed outputs supersedes the record and appends to that output's provenance, an unchanged one keeps its origin entry (#8). Missing: provenance covers outputs, not every realized field (the registry's own example does the same); no discovered records. | none: dcm-provider-libvirt reads `virsh` status but writes no record. |
| 6 | storage/provision-volume-bound-to-pool | shape: `Storage.Volume`, tenancy, quota | none by title | partial: a storage service type exists in the catalog (upstream #22). No tenancy, no quota. | reports: the discovery sweep records pools and volumes. No storage provider realizes from intent. |
| 7 | cross-domain/udlm-dependency-graph-data-model | shape: ordering `edge_type`s, ADR-010 derivation | designed: DCM ADR-008 dependency resolution, ADR-024 change impact | partial: `depends_on` exists only inside a multi-resource catalog item. No graph query, no blast radius. Outside the control plane, the homelab estate repository derives shutdown and startup order from stored edges (tools/shutdown_order.py). | reports: the discovery sweep writes `contained_by` and `depends_on` edges. |
| 8 | compute/cross-provider-dependency-ordering | shape: graph-integrity DAG, ADR-011 reserve ordering | designed: DCM ADR-008 | partial (main): a run provisions DAG level by level as RUNNING events arrive, each resource routed to its own agent, and deletes in reverse DAG order (upstream #53, hardened with compare-and-swap and callback retry in #62). A dependent stays PENDING until its prerequisites run. Missing: the edges are `requires_resources` on the catalog item, not UDLM `depends_on` edges on records. | none |
| 9 | intent-fulfillment/operational-dependency-cascade | shape: ADR-010 `UnmetDependency` | designed: DCM ADR-008 | partial (main): a dependent whose prerequisite has not reached RUNNING is held PENDING, and a FAILED prerequisite reaches `OnResourceFailed` (upstream #53, #62). Missing: no typed `UnmetDependency`, no blast radius. | none |
| 10 | cross-domain/dynamic-rehydration | shape: four-states §5, intent replayed, UUID preserved | designed: DCM ADR-020 migration and operational gating | partial (main): `RehydrateResource` re-evaluates the stored spec through policy and provisions a new resource under a new run id, then deletes the old one; composite instances rehydrate as a whole (upstream #67). The entity UUID is not preserved and nothing is derived from the graph. On `udlm-native` the intent record exists to replay from, but the rehydrate path does not read it yet. | none |
| 11 | compute/vm-provision-provider-failure-refused | shape: policy §13 recovery, ADR-011 release | designed: DCM ADR-005 provider abstraction, ADR-006 | partial (main): a FAILED status event reaches `OnResourceFailed`, and the rehydrate path rolls back when provisioning fails. No typed refusal record. | none |
| 12 | observability/rehydration-rto-measurement | shape: ADR-003 rto/rpo | none by title | none | none |
| 13 | compute/idempotent-reconvergence | shape: `generation` / `observed_generation` | designed: DCM ADR-003 | partial (`udlm-native`): status transitions are compare-and-swap so a retried callback is a no-op (upstream #62); a retried realized report that repeats the latest record's outputs writes nothing, and a changed one supersedes with `generation` + 1 (#11). The computed view carries `generation` / `observed_generation`. Missing: no generation on the intent side; nothing re-converges a running resource toward changed intent. | none |
| 14 | observability/drift-detection-remediation | shape: four-states §6 drift record | designed: DCM ADR-017 discovered ingestion | partial (`udlm-native`): a status event whose outputs differ from the latest realized record produces a superseding realized record with the previous value in that output's provenance (#8, #11). Missing: no discovered records, no drift record, no remediation. Outside the control plane, the homelab estate repository diffs a new sweep against stored records (tools/discovery_diff.py, discovery_apply.py). | reports: each sweep is a drift input. |
| 15 | governance/audit-merkle-tree-verification | shape: universal-audit §8 | designed: DCM ADR-010 tamper-evident audit | none for the audit log. Each per-state record on `udlm-native` is sealed into its entity's resource chain (ADR-059's chain, verified with the registry's `integrity_chain.py` algorithm, #6); that is the per-entity chain, not the Merkle audit log this row needs. The homelab estate repository materializes provenance from git history (tools/provenance.py, minimal profile). | none |
| 16 | governance/policy-override-approval | shape: policy-contract §18, `override` policy_type | designed: DCM ADR-013 override governance | none | none |
| 17 | osac/cloud-provider-registration | shape: provider-contract §8.1a capacity advertisement | designed: DCM ADR-005, ADR-023 naturalization boundary | partial (main): agents register the service types they provide, an environment, and a relative cost, and heartbeat; placement selects among ready agents by policy (upstream #51). Missing: no resource types with versions, no capacity, no provider provenance on the result beyond `dcm/agents/<name>` on the realized record. | none: no OSAC provider. |
| 18 | osac/provider-portability-new-cloud | shape: naturalization, `bound_providers` | designed: DCM ADR-023 | none beyond the re-placement in row 10. | none |
| 19 | governance/policy-resolution-capability | shape: policy-contract §7.7 three-state | designed: DCM ADR-006, ADR-027 policy firewall | partial: OPA evaluates policy on placement (internal/policy/opa, internal/placement/policy). The three-state verdict is not verified in code. | none |
| 20 | cross-domain/profile-resolution-capability | shape: `profile` record and instances | designed: DCM ADR-012 data assembly layering | none | none |
| 21 | governance/audit-chain-proofs-capability | shape: universal-audit §8 | designed: DCM ADR-010 | none | none |

## Counts

| Layer | Present | Partial | None |
|---|---|---|---|
| Model | 21 | 0 | 0 |
| Control plane: design | 19 | 0 | 2 (rows 6, 12) |
| Control plane: code | 2 (rows 1, 5, on `udlm-native`) | 13 (rows 2, 3, 4, 6, 7, 8, 9, 10, 11, 13, 14, 17, 19) | 6 (rows 12, 15, 16, 18, 20, 21) |
| Provider: realizes from a UDLM intent record | 0 | 1 (row 1: libvirt reconciler, from its own spec) | 20 |
| Provider: reports discovered records | 4 (rows 1, 6, 7, 14) | 0 | 17 |

## What moved since 2026-09-15

- **The fork's `udlm-native` branch** (croadfeldt/control-plane, PRs #4 to #11): service types generated
  from `registry/generated/` with UDLM `outputs` as read-only fields; intent, requested and realized
  records written from placement, validated against `registry/state-record.schema.json` and sealed
  into the entity's chain; a read API serving the records and the entity view (a port of
  `registry/tools/entity_view.py`, parity-tested on the registry's worked example); field-level
  provenance; CEL output bindings checked against the class's declared outputs. Rows 1 and 5 move to
  `code`; rows 3, 13, 14 gain their first code.
- **Upstream** (dcm-project/control-plane, synced to dd2caea): agent-based provisioning, DAG progression
  and reversion with compare-and-swap and retries, composite rehydration, runtime output fields.
  Rows 8, 9 move from `none` to `partial`; rows 2, 10, 11, 17 gain code.
- **Upstream still has no UDLM code.** Nothing on `udlm-native` is upstream.

## What the evidence says

1. **The model is complete for the release set, and two rows now run end to end on the fork.**
   Every row has a shape, gated in this repository. On `udlm-native`, a VM request produces an intent
   record, a requested record and a realized record that validate against the registry's schema and
   verify with its integrity checker, and the entity view reads back as the registry defines it. That
   is rows 1 and 5. Every other row is at most partial.
2. **The monolith's own path has widened, without the model.** Upstream now orders a run level by
   level across agents, retries and de-duplicates callbacks, rehydrates composites, and carries
   read-only output fields. It still knows nothing of records, provenance, the audit chain, drift
   records, override, quota, tenancy, or sovereignty. Those exist only on the fork's branch or not at
   all.
3. **The registry link is repaired.** The generator reads the served flat specs and emits the class
   and output tables the control plane uses; regeneration after each upstream sync is a branch rule.
4. **The only real estate data is still in the superseded record shape.** The homelab estate repository holds 291 records
   under a folded `states:` block and validates them against the read-model schema. This repository
   forbids that shape for stored records (RHY-006). Discovered records dominate: 284 discovered, 5
   intent, 1 realized, 1 decommissioned.
5. **The one provider is still not wired.** dcm-provider-libvirt reconciles VMs idempotently from its own
   Ansible spec. Its UDLM wrap (intent in, realized record out) is a design note, dated 2026-06-22,
   with no code. On the fork, the provider side of a record is an agent, so wiring means an agent
   that fronts the reconciler.

## What follows from it

These are the gaps in the order they block each other. Each names the row it unblocks.

- **Migrate the homelab estate repository to per-state records** (one record per state, RHY-006). This gives the
  homelab a discovered-record set the control plane can read. Rows 5, 7, 14.
- **An agent that fronts dcm-provider-libvirt**: accept a dispatched spec, run the reconciler, report
  status with outputs. With the branch's writers, that is the first provider that closes the loop on
  real hardware. Rows 1, 3, 5.
- **Rehydrate from the intent record**, preserving the entity UUID, instead of re-placing under a new
  id. The record exists; the path does not read it. Row 10.
- **Discovered records** from status events and sweeps, and a drift record between discovered and
  realized. Row 14.
- **Audit chain.** Rows 15, 21 need a writer for the Merkle log; the per-record chain does not
  substitute for it.
- **Graph queries.** Convergence order and blast radius over stored `depends_on` edges, not catalog
  `requires_resources`. Rows 7, 8, 9.
- **Policy three-state and override**, and **agent registration as capability advertisement**, are
  increments 7 and 6 of the branch plan. Rows 11, 16, 19; row 17.

Rows 4, 17, 18 wait on an OSAC provider, which is outside this program's repositories.
