# Example: dependency modeling

A small, anonymized estate (15 resources) demonstrating the ways UDLM lets you express dependencies —
and, importantly, how **bundling** and **secondary dependencies** fall out of the graph itself
without any special construct. Run it through the order derivation:

```
python3 <estate-explorer>/ingest/shutdown_order.py .
```

## The patterns it shows

### Direct edge
`svc-app` `depends_on` `svc-db` — an explicit, precise dependency. The base case.

### Component chain (and redundancy)
Power is modeled on the **component that carries it**, not the host. `host-a` contains two power
supplies; `psu-a1 → feed-a` and `psu-a2 → feed-b` — two independent rails. Because `host-a` depends on
its PSUs and each PSU depends on a feed, **host-a's power dependency is the union of both feeds** —
acquired as *secondary dependencies* through the PSUs. A single host-level "on this UPS" edge would
have silently dropped the second rail. `host-b` shows the non-redundant case: one PSU → `feed-wall`.

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
on the location (the PSUs carry it), because "where a thing is" and "what powers it" are different
questions — and here they differ: same realm, different power.

## Takeaway

Bundling and secondary dependencies are emergent: **depend on a node that carries a set of
dependencies, and you inherit them transitively.** The only thing the resolver *adds* beyond
transitivity is scope-derivation (turning the `tenant` field into edges). Everything else — direct
edges, component chains, node-bundles — is already in the authored graph.
