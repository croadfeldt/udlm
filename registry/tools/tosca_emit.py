#!/usr/bin/env python3
"""Emit a candidate TOSCA v2.0 node type from a UDLM resource-type spec, and round-trip it.

This makes the TOSCA-profile spike's Q1 (docs/research/tosca-profile-spike.md) *mechanical*
rather than paper: the type + topology layer is emitted by rule, then the UDLM-relevant facts are
recovered back out of the emitted TOSCA and diffed against the source. An empty diff on
{properties, attributes, requirement-targets, version} is the by-construction implementability
proof — the contract transcribes to a standard node type with no loss and no invention.

What does NOT round-trip is the deliberate delta (four-state lifecycle, sovereignty/classification,
attestation) — TOSCA has no native home for it; it rides as opaque `metadata`. That absence is the
finding, not a defect (see the spike doc).

Usage:
  python3 registry/tools/tosca_emit.py --emit <spec.json|.yaml>        # print the TOSCA node type
  python3 registry/tools/tosca_emit.py --round-trip <spec.json|.yaml>  # emit → recover → diff
  python3 registry/tools/tosca_emit.py                                 # round-trip Compute.VM
"""
import argparse
import json
import os
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_SPEC = os.path.join(REPO, "registry/resource-types/compute/compute.virtual-machine.json")

# UDLM JSON-Schema types → TOSCA property types (the clean-mapping rows of the spike table).
TYPE_MAP = {"object": "map", "array": "list", "string": "string",
            "integer": "integer", "number": "float", "boolean": "boolean"}


def load(path):
    text = open(path).read()
    if path.endswith((".yaml", ".yml")):
        if yaml is None:
            sys.exit("PyYAML required to read a .yaml spec")
        return yaml.safe_load(text)
    return json.loads(text)


def _snake(seg):
    return re.sub(r"(?<!^)(?=[A-Z])", "_", seg).lower()


def tosca_type_name(resource_type):
    # Compute.VM → udlm.compute.VirtualMachine
    parts = resource_type.split(".")
    return "udlm." + parts[0].lower() + ("." + ".".join(parts[1:]) if len(parts) > 1 else "")


def req_name(target):
    # Network.VirtualNetwork → virtual_network  (the requirement's local name)
    return _snake(target.split(".")[-1])


def occurrences(card):
    # "0..1"→[0,1] · "0..n"/"1..n"→[0|1,"UNBOUNDED"] · bare "1"→[1,1]
    card = (card or "0..1").strip()
    if ".." not in card:
        return [int(card), int(card)] if card.isdigit() else [0, 1]
    lo, hi = card.split("..", 1)
    lo = int(lo) if lo.isdigit() else 0
    hi = "UNBOUNDED" if hi in ("n", "*", "N") else (int(hi) if hi.isdigit() else "UNBOUNDED")
    return [lo, hi]


def emit(spec):
    """UDLM resource-type spec → TOSCA v2.0 node type (the type + topology layer)."""
    rt = spec["resource_type"]
    sp = spec.get("spec", {}) or {}
    props, required = sp.get("properties", {}) or {}, set(sp.get("required", []) or [])
    outs = spec.get("outputs", {}) or {}
    rels = spec.get("relationships", []) or []

    node = {
        "version": spec.get("version"),
        "derived_from": "tosca.nodes.Root",
        "metadata": {
            "udlm_id": spec.get("$id", ""),
            # THE DELTA — no native TOSCA home; carried as opaque metadata (see spike doc):
            "_udlm_delta_not_native": "four-state lifecycle · sovereignty/data_classification · attestation",
        },
        "properties": {},   # ← spec.properties (INTENT)
        "attributes": {},   # ← outputs (REALIZED)
        "requirements": [], # ← relationships (EDGES)
    }
    for k, v in props.items():
        jtype = v.get("type") if isinstance(v, dict) else None
        node["properties"][k] = {"type": TYPE_MAP.get(jtype, "string"), "required": k in required}
    for k, v in outs.items():
        otype = v.get("type") if isinstance(v, dict) else None
        node["attributes"][k] = {"type": TYPE_MAP.get(otype, "string")}
    for r in rels:
        if not isinstance(r, dict) or not r.get("target"):
            continue
        node["requirements"].append({
            req_name(r["target"]): {
                "node": tosca_type_name(r["target"]),
                "occurrences": occurrences(r.get("cardinality")),
            }
        })
    return {"tosca_definitions_version": "tosca_2_0", "node_types": {tosca_type_name(rt): node}}


def recover(tosca):
    """Ingest: pull the UDLM-relevant fact sets back out of the emitted TOSCA."""
    node = next(iter(tosca["node_types"].values()))
    return {
        "properties": set(node["properties"]),
        "attributes": set(node["attributes"]),
        "targets": {next(iter(r.values()))["node"] for r in node["requirements"]},
        "version": node["version"],
    }


def source_facts(spec):
    return {
        "properties": set((spec.get("spec", {}) or {}).get("properties", {}) or {}),
        "attributes": set(spec.get("outputs", {}) or {}),
        "targets": {tosca_type_name(r["target"]) for r in (spec.get("relationships", []) or [])
                    if isinstance(r, dict) and r.get("target")},
        "version": spec.get("version"),
    }


def round_trip(spec):
    tosca = emit(spec)
    rec, src = recover(tosca), source_facts(spec)
    diffs = {k: {"missing": sorted(src[k] - rec[k]), "extra": sorted(rec[k] - src[k])}
             for k in ("properties", "attributes", "targets")}
    version_ok = rec["version"] == src["version"]
    clean = version_ok and all(not d["missing"] and not d["extra"] for d in diffs.values())
    return clean, diffs, version_ok, tosca, src


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--emit", metavar="SPEC")
    ap.add_argument("--round-trip", metavar="SPEC")
    args = ap.parse_args()

    if args.emit:
        tosca = emit(load(args.emit))
        print(yaml.safe_dump(tosca, sort_keys=False) if yaml else json.dumps(tosca, indent=2))
        return 0

    spec_path = args.round_trip or DEFAULT_SPEC
    spec = load(spec_path)
    clean, diffs, version_ok, _, src = round_trip(spec)
    rt = spec["resource_type"]
    print(f"round-trip: {rt}@{spec.get('version')}  ({os.path.relpath(spec_path, REPO)})")
    print(f"  version preserved: {version_ok}")
    for k in ("properties", "attributes", "targets"):
        n = len(src[k])
        status = "OK" if not diffs[k]["missing"] and not diffs[k]["extra"] else "DIFF"
        print(f"  {k:11} {n:2} mapped  [{status}]"
              + (f"  missing={diffs[k]['missing']} extra={diffs[k]['extra']}"
                 if status == "DIFF" else ""))
    print(f"\n  TYPE+TOPOLOGY ROUND-TRIP: {'CLEAN — 0 loss, 0 invention (Q1 mechanical)' if clean else 'LOSSY'}")
    print("  DELTA (expected, not carried natively): four-state lifecycle · sovereignty · attestation")
    return 0 if clean else 1


if __name__ == "__main__":
    sys.exit(main())
