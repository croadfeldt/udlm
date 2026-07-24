# Worked example — Platform.Hub: one hub, three topologies

**What this settles:** how the multi-cluster management plane models in practice — the three real
topologies, the edges that express them, and why shutdown order falls out correctly in each,
including the reflexive self-managed case. Relationship semantics per ADR-043 (meaning in the typed
target, ordering in `edge_type`, names only where they add information).

## The cast

| handle | type | what it is |
|---|---|---|
| `hub-prod` | `Platform.Hub` (`hosted_control_planes: true`) | the fleet manager (ACM/HCP-style) |
| `cluster-mgmt` | `Compute.Cluster` | the cluster hub-prod runs on |
| `cluster-hcp-a` | `Compute.Cluster` | a hosted-control-plane spoke (control plane lives inside hub-prod) |
| `cluster-edge-1` | `Compute.Cluster` | an imported spoke (existed before the hub; adopted into the fleet) |

## The edges

```yaml
# hub-prod — hosted on cluster-mgmt
- edge_type: contained_by      # ordering: cluster-mgmt must outlive hub-prod
  target_handle: cluster-mgmt

# cluster-hcp-a — hub-provisioned, control plane hosted in the hub
- edge_type: contained_by      # ordering: hub-prod must outlive cluster-hcp-a
  target_handle: hub-prod

# cluster-edge-1 — imported (OCM ManagedCluster semantics)
- edge_type: depends_on        # ordering only; an imported cluster SURVIVES hub loss
  strength: soft               # degrade-don't-break (DEP-006)
  target_handle: hub-prod

# cluster-mgmt — ALSO managed by the hub it hosts (the self-managed pattern)
- edge_type: references        # NON-ordering by rule: an ordering edge here would close a
  target_handle: hub-prod      # cycle with hub-prod's contained_by — the CYCLE gate rejects it.
                               # This edge is what the derived roles: [hub] marker reads from.
```

## Why the order falls out right

Walking only the ordering edges (`contained_by`/`depends_on`): shutdown =
`cluster-hcp-a` → `cluster-edge-1`'s management detach → `hub-prod` → `cluster-mgmt`.
No cycle exists to break, because the reflexive management edge never entered the ordering graph.
Startup is the reverse; `cluster-edge-1` starts independently (soft) and re-attaches when the hub
returns.

## The outputs a binder consumes

At Realized, `hub-prod` publishes `hub_ready`, `api_endpoint`, `managed_cluster_count` — a
spoke-provisioning request binds on `hub_ready`; a fleet dashboard binds `managed_cluster_count`
(a published reading of the inbound edges, not a second source of truth).

## The rehydration question this example plants

`hub-prod`'s intent store lives on `cluster-mgmt` — the cluster it manages. Rehydrating the hub
after losing that cluster means replaying hub intent from the estate (the repo, not the hub) and
re-adopting the surviving spokes: `cluster-edge-1` re-attaches (soft edge, nothing lost);
`cluster-hcp-a` is gone with its control plane and rebuilds from *its* intent. The corpus UC
`multi-cluster/self-managed-hub-rehydration` validates exactly this.
