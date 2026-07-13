# Dependency-modeling example estate

A small, fully anonymized UDLM estate (15 resources, one tenant) that demonstrates the four
dependency-modeling patterns UDLM uses to keep a derived shutdown/startup order correct. All data is
synthetic — no real hostnames, domains, or addresses.

Every edge follows the estate-wide rule: an edge `source -> target` means **source depends on
target**, so in a shutdown the source stops *before* the target. The order is never stored; it is a
topological sort derived live from these files.

## The four patterns

### 1. Component chain / redundancy — power modeled on the PSU, not the host

`host-a` never declares a power dependency itself. Instead it *contains* two power supplies, and each
PSU points at its own feed:

```
psu-a1 --contained_by/chassis--> host-a      psu-a1 --powered_by--> feed-a   (rail A)
psu-a2 --contained_by/chassis--> host-a      psu-a2 --powered_by--> feed-b   (rail B, independent)
```

So `host-a`'s power dependency is the **union of both feeds**, carried through its PSUs. This is the
point of modeling power at the PSU level: a coarse host-level "host-a on UPS A" edge would silently
lose the second rail, and a single-feed loss would look fatal when it isn't. `host-b`, by contrast,
has one PSU on `feed-wall` (an unprotected utility outlet) — a single point of power failure, and the
model shows exactly that.

### 2. Direct edge — service-to-service

`svc-app --depends_on--> svc-db`: an explicit, authored runtime dependency. `svc-app` stops before
`svc-db` on shutdown and starts after it on startup. No indirection — the plainest form of edge.

### 3. Bundle — inherited, ambient dependencies

`realm` is a `Topology.DependencyBundle` whose own dependencies are the shared identity + address
services (`idm`, `dns`). Members attach with a **single** reference edge to the bundle:

```
host-a, host-b, svc-app, svc-db  --references--> realm
realm  --references-->  idm ,  dns          (the shared set)
```

At derivation time the bundle membership expands into a dependency on each of the bundle's targets, so
all four members inherit `idm` + `dns` (visible as eight `derived` edges) without hand-wiring identity
and DNS onto every resource. Add a new resource to the realm and it inherits the same ambient
dependencies for free.

### 4. Location — where it sits vs. what powers it

`host-a` references `loc-rack` (the server rack); `host-b` references `loc-bench` (the workbench).
Location answers "where is it", which is deliberately a **different question** from "what powers it" —
the two hosts sit in different places on different power, yet share one realm. Location carries no
power edge; power is on the PSUs (pattern 1).

## Files

| Resource | Type | Role in the example |
|----------|------|---------------------|
| `feed-a`, `feed-b` | Facility.PowerFeed | Two independent rack rails (redundant pair for host-a) |
| `feed-wall` | Facility.PowerFeed | Unprotected utility outlet (single feed for host-b) |
| `loc-rack`, `loc-bench` | Facility.Location | Rack vs. bench — different places, same realm |
| `host-a` | Compute.BareMetalHost | Compute host, dual-PSU redundant power |
| `host-b` | Compute.BareMetalHost | Bench host, single-PSU power |
| `psu-a1`, `psu-a2` | Hardware.PowerSupply | host-a's two PSUs, one per rail |
| `psu-b1` | Hardware.PowerSupply | host-b's single PSU |
| `idm` | Security.DirectoryService | Realm identity directory (control-plane) |
| `dns` | Network.AddressService | Realm DHCP/DNS service (control-plane) |
| `realm` | Topology.DependencyBundle | Shared idm+dns members inherit |
| `svc-app` | Software.Service | Application, depends on svc-db |
| `svc-db` | Software.Service | Database, depended on by svc-app |

## Deriving the order

```
python3 <estate-explorer>/ingest/shutdown_order.py examples/dependency-modeling
```

The derivation resolves cleanly — **0 cycles, 0 unresolved targets** — into tiers where leaf consumers
stop first and the control-plane identity/DNS services hold until last:

```
step 0   psu-a1, psu-a2, psu-b1, svc-app        (leaf consumers stop first)
step 1   feed-a, feed-b, feed-wall, host-a, svc-db
step 2   host-b, loc-rack
step 3   loc-bench, realm
step 4   dns, idm                               (control-plane gate — hold until last)
```

Startup is the exact reverse (`--startup`): identity/DNS come up first, leaf services last.
