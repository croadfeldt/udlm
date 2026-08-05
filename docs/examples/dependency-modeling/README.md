# Example: dependency modeling

A small, anonymized estate (12 resources) demonstrating the ways UDLM lets you express dependencies —
and, importantly, how **bundling** and **secondary dependencies** fall out of the graph itself
without any special construct. Run it through the order derivation:

```
python3 <estate-explorer>/ingest/shutdown_order.py .
```

## The patterns it shows

### Direct edge
`svc-app` `depends_on` `svc-db` — an explicit, precise dependency. The base case.

### Multi-edge (and redundancy)
Power is a **direct dependency of the host** on the feed(s) it draws from — `Compute.BareMetalHost
depends_on Facility.PowerFeed` is `0..n`, so redundancy is authored as *more than one edge*, not
inferred through a component. `host-a` declares **two** feed edges — `depends_on feed-a` +
`depends_on feed-b`, two independent rails — so losing one feed leaves it up; the blast radius of
`feed-a` includes `host-a`, but `host-a` survives because it has a second path across a distinct
power fault domain. `host-b` shows the non-redundant case: a single `depends_on feed-wall`. (Component
inventory like a PSU is out of scope — ADR-013; DCM is not a hardware system-of-record. Where a
dependency genuinely routes through a *managed* component, model it there — e.g. a
`Hardware.NetworkInterface` `connects_to` a switch port — but power roots at the host.)

### Bundling — declare deps on a node, depend on the node
`core-services` declares the shared platform dependencies **once**: `depends_on idm` + `depends_on
dns`. `svc-app` and `svc-db` each add a single `depends_on core-services`, and thereby inherit `idm`
and `dns` as **secondary dependencies** — the topological order carries it (`svc-app → core-services →
{idm, dns}`, so idm/dns rank above svc-app). **This is all "bundling" is**: there is no special bundle
type — you group a set of dependencies on a node and depend on that node.

### Scope-derived
The hosts get the *same* identity/DNS a different way: they share the realm via `tenant_uuid`, and the
resolver derives the realm's `idm`/`dns` from that field (no edge authored). Use this when the
dependency is ambient to a whole realm rather than routed through a shared node.

### Location
`host-a` is in `loc-rack`, `host-b` at `loc-bench` — physical placement. Note power is *not* modeled
on the location (the host's own feed edges carry it), because "where a thing is" and "what powers it"
are different questions — and here they differ: same realm, different power.

## Takeaway

Bundling and secondary dependencies are emergent: **depend on a node that carries a set of
dependencies, and you inherit them transitively.** The only thing the resolver *adds* beyond
transitivity is scope-derivation (turning the `tenant` field into edges). Everything else — direct
edges, multi-edge redundancy, node-bundles — is already in the authored graph.
