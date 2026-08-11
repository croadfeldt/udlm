#!/usr/bin/env python3
"""Graph-integrity gate: the dependency graph is declared one-sided and made two-sided by DERIVATION.
An edge is declared once on its natural owner; the reverse is not stored, it is computed by inverting
the edge (registry/edge-types.yaml). For that to be sound, three things must hold — this gate enforces
them so a one-sided declaration is never a one-sided *graph*:

  GRAPH-001  every edge type in the vocabulary has an entry in the inverse map, and vice versa —
             so the inverse map can't drift from the allowed edge types. The vocabulary is read
             from its single home (common-elements.schema.json#/$defs/edge_type), itself a proven
             projection of this registry; the schemas that use it $ref that entry.
  GRAPH-002  every relationship edge's `target` resolves to a real node (a resource type or Class).
             A dangling target means the derived inverse would land on nothing — the graph tears.
  GRAPH-003  every declared edge has a defined inverse, so B→A is derivable for every A→B. Reported as
             the two-sided adjacency (declared + derived), proving the graph is navigable both ways.

This is why relationships are declared on one endpoint only (single-source, no drift) and still form a
complete bidirectional graph. Run with --emit to write the materialized two-sided graph.
"""
import glob
import json
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "registry", "tools"))
import refstore  # the vocabulary's single home


import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(p):
    t = open(p, encoding="utf-8").read()
    return (yaml.safe_load(t) if p.endswith((".yaml", ".yml")) else json.loads(t)) or {}


def nodes_and_edges():
    """Every resource type + Class is a node; collect each spec's declared relationship edges."""
    nodes, edges = set(), []
    for p in glob.glob(os.path.join(ROOT, "registry", "resource-types", "**", "*"), recursive=True):
        if p.endswith((".json", ".yaml", ".yml")):
            d = load(p)
            rt = d.get("resource_type")
            if rt and "record_type" not in d:
                nodes.add(rt)
                for e in d.get("relationships") or []:
                    edges.append((rt, e.get("edge_type"), e.get("target"), e.get("enforcement", "example")))
    for p in glob.glob(os.path.join(ROOT, "registry", "classes", "**", "*.yaml"), recursive=True):
        d = load(p)
        if d.get("record_type") == "class":
            nodes.add(d["resource_type"])
    return nodes, edges


def resolves(target, nodes):
    """A target resolves to an exact node, or to a family (single-segment target matching the first
    segment of some multi-segment node, e.g. `Compute` for `Compute.VM`)."""
    if target in nodes:
        return True
    if "." not in target:
        return any(n.split(".")[0] == target for n in nodes)
    return False


def main():
    reg = load(os.path.join(ROOT, "registry", "edge-types.yaml"))
    inv = {e["edge_type"]: e["inverse"] for e in reg.get("edge_types", [])}
    # The vocabulary's single home (common-elements.schema.json#/$defs/edge_type), not the schema
    # that happens to use it — resource-type-spec.schema.json now $refs that entry, so reaching in
    # by literal path would read a $ref node and find no enum at all.
    schema_enum = set(refstore.vocabulary("edge_type"))
    nodes, edges = nodes_and_edges()
    fails = []

    # GRAPH-001: registry ⟷ schema enum, no drift
    if set(inv) != schema_enum:
        fails.append(f"GRAPH-001: edge-types.yaml {sorted(inv)} != schema edge_type enum "
                     f"{sorted(schema_enum)} — the inverse map has drifted from the allowed edge types")

    # GRAPH-002 + GRAPH-003: targets resolve, inverses derivable; build the two-sided adjacency
    two_sided = []
    for src, et, tgt, enf in edges:
        if et not in inv:
            fails.append(f"GRAPH-003: {src} declares edge_type {et!r} with no inverse in edge-types.yaml")
            continue
        if not tgt or not resolves(tgt, nodes):
            fails.append(f"GRAPH-002: {src} --{et}--> {tgt!r} target does not resolve to any resource "
                         f"type or Class — a dangling edge tears the derived graph")
            continue
        two_sided.append((src, et, tgt))                 # declared A --et--> B
        two_sided.append((tgt, inv[et], src))            # derived  B --inv--> A

    if "--emit" in sys.argv and not fails:
        out = os.path.join(ROOT, "registry", "generated", "dependency-graph.json")
        os.makedirs(os.path.dirname(out), exist_ok=True)
        json.dump({"nodes": sorted(nodes),
                   "edges": [{"from": a, "edge": e, "to": b} for a, e, b in sorted(two_sided)]},
                  open(out, "w"), indent=2)
        print(f"wrote {os.path.relpath(out, ROOT)}")

    for f in fails:
        print("FAIL [" + f)
    declared = len(two_sided) // 2
    print(f"{len(nodes)} nodes, {declared} declared edge(s) → {len(two_sided)} two-sided (declared+derived); "
          f"{len(fails)} integrity violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
