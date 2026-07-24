#!/usr/bin/env python3
"""Rule-36 base-standard gates (G1/G2/G3/G5/G6 from the 2026-07-25 fleet review) with a
baseline ratchet: violations listed in tests/type-standard-baseline.yaml are the known
burn-down set (reported as WARN); any violation NOT in the baseline is a regression and
fails CI. Shrink the baseline with every fix-wave PR; never grow it.

  G1 outputs-nonempty   realizable type (family Resource|Process) declares >=1 output OR an
                        explicit exclusion note ("outputs-exempt:" token in the spec description)
  G2 target-exists      every relationships[].target resolves to a registered resource_type
  G3 reference-lint     *_ref spec properties use the common-elements Reference oneOf, not bare string
  G5 adopts-parity      adoption claims in prose require adopts[] entries (structured half of
                        check_standards_registered)
  G6 property-strict    schema-authoring keys inside spec.properties subtrees come from the JSON
                        Schema keyword allowlist (catches mangled keys that are legal-but-wrong)

G7 context-present (rule 36(l)) rides the same ratchet. G4 (worked-example currency) is deferred pending the D8 example-bar ruling; the exists-half is
reported informationally, never failing.
"""
import glob
import json
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = os.path.join(ROOT, "registry", "resource-types")
BASELINE = os.path.join(ROOT, "tests", "type-standard-baseline.yaml")

SCHEMA_KEYWORDS = {
    "type", "description", "enum", "const", "default", "pattern", "format", "items",
    "properties", "additionalProperties", "required", "oneOf", "anyOf", "allOf", "not",
    "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength",
    "minItems", "maxItems", "uniqueItems", "propertyNames", "patternProperties", "$ref",
    "title", "examples", "deprecated", "readOnly", "sensitive", "x-udlm", "x-extensible-enum",
}
ADOPT_TOKENS = re.compile(r"\bADOPT\b|\badopts\b|\bOCI\b|\bpurl\b|\bSPDX\b|\bCycloneDX\b|\bOSV\b|\bCVSS\b|\bRedfish\b|\bSCIM\b|\bTOSCA\b", re.I)


def load_types():
    out = {}
    for f in sorted(glob.glob(os.path.join(TYPES, "*.json")) + glob.glob(os.path.join(TYPES, "*.yaml"))):
        with open(f, encoding="utf-8") as fh:
            out[f] = json.load(fh) if f.endswith(".json") else yaml.safe_load(fh)
    return out


def walk_props(node, path, hits):
    if not isinstance(node, dict):
        return
    for k, v in node.items():
        if k in ("properties", "patternProperties") and isinstance(v, dict):
            for pk, pv in v.items():
                walk_props(pv, f"{path}.{pk}", hits)
        elif k == "items" and isinstance(v, dict):
            walk_props(v, path + "[]", hits)
        elif k in ("oneOf", "anyOf", "allOf") and isinstance(v, list):
            for i, sub in enumerate(v):
                walk_props(sub, path, hits)
        elif k not in SCHEMA_KEYWORDS:
            hits.append((path, k))


def is_reference_shape(prop):
    """common-elements §2.5: oneOf(handle string | Reference object)."""
    if not isinstance(prop, dict):
        return False
    if "$ref" in json.dumps(prop):
        return True
    for alt in prop.get("oneOf", []):
        if isinstance(alt, dict) and alt.get("type") == "object" and \
           any(k in alt.get("properties", {}) for k in ("uuid", "ref_uuid", "handle")):
            return True
    return False


def main():
    types = load_types()
    registered = {d.get("resource_type") for d in types.values() if isinstance(d, dict)}
    baseline = {}
    if os.path.exists(BASELINE):
        baseline = yaml.safe_load(open(BASELINE, encoding="utf-8")) or {}
    known = {(v["gate"], v["type"], v["item"]) for v in baseline.get("known", [])}

    found = []  # (gate, resource_type, item, detail)
    for f, d in types.items():
        if not isinstance(d, dict):
            continue
        rt = d.get("resource_type", os.path.basename(f))
        fam = d.get("family")
        spec = d.get("spec", {}) or {}
        desc_all = json.dumps(d)

        # G1
        outputs = d.get("outputs")
        n_out = len(outputs) if isinstance(outputs, dict) else (len(outputs) if isinstance(outputs, list) else 0)
        if fam in ("Resource", "Process") and n_out == 0 and "outputs-exempt:" not in desc_all:
            found.append(("G1", rt, "outputs", "realizable type declares no outputs and no outputs-exempt note"))

        # G2
        for r in d.get("relationships", []) or []:
            tgt = r.get("target")
            if tgt and tgt not in registered and not tgt.endswith("*"):
                found.append(("G2", rt, tgt, "relationships[].target is not a registered resource_type"))

        # G3
        for pk, pv in (spec.get("properties") or {}).items():
            if pk.endswith("_ref") and isinstance(pv, dict) and pv.get("type") == "string" and not is_reference_shape(pv):
                found.append(("G3", rt, pk, "bare-string *_ref — use the common-elements Reference oneOf"))
            if isinstance(pv, dict):
                items = pv.get("items")
                if isinstance(items, dict):
                    for ik, iv in (items.get("properties") or {}).items():
                        if ik.endswith("_ref") and isinstance(iv, dict) and iv.get("type") == "string" and not is_reference_shape(iv):
                            found.append(("G3", rt, f"{pk}[].{ik}", "bare-string *_ref — use the common-elements Reference oneOf"))

        # G5
        meta_desc = (d.get("metadata", {}) or {}).get("description", "") or d.get("description", "") or ""
        if ADOPT_TOKENS.search(meta_desc) and not (d.get("adopts") or []):
            found.append(("G5", rt, "adopts[]", "prose claims adoption; adopts[] is empty"))

        # G7 — plain-English context present (rule 36(l))
        if not d.get("context"):
            found.append(("G7", rt, "context", "no plain-English context block (purpose/plain_description/use_when)"))

        # G6
        bad = []
        for pk, pv in (spec.get("properties") or {}).items():
            walk_props(pv, pk, bad)
        for path, key in bad:
            found.append(("G6", rt, f"{path}:{key}", "unknown schema-authoring key inside a property object"))

    regressions = [v for v in found if (v[0], v[1], v[2]) not in known]
    burned = [k for k in known if k not in {(v[0], v[1], v[2]) for v in found}]
    for g, rt, item, detail in sorted(found):
        tag = "WARN(baseline)" if (g, rt, item) in known else "FAIL(new)"
        print(f"{tag} [{g}] {rt} :: {item} — {detail}")
    for g, rt, item in sorted(burned):
        print(f"STALE-BASELINE [{g}] {rt} :: {item} — fixed; remove from tests/type-standard-baseline.yaml")
    print(f"\n{len(found)} violation(s): {len(found)-len(regressions)} baselined, {len(regressions)} NEW; {len(burned)} baseline entr(y|ies) now stale")
    return 1 if regressions or burned else 0


if __name__ == "__main__":
    sys.exit(main())
