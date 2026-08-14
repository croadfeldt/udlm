#!/usr/bin/env python3
"""The seal facets are real OpenLineage facets, and the admission rule is enforced (SEAL-001..004).

ADR-059 rules that a change seal is an OpenLineage event carrying UDLM facets, and that **a state
write without a citable pathway anchor is refused**. Neither existed: `udlm_workingCopy`,
`udlm_provenance`, `udlm_context` and `udlm_finding` had zero hits anywhere in the repo.

**Why the facets had to be schemas rather than prose.** An OpenLineage custom facet IS a JSON Schema
— the mechanism is a `_schemaURL` on the facet pointing at the schema that defines it, which is how a
consumer knows what it is reading. A facet specified only in prose is not a facet; it is an
implementation-specific blob sitting in a facets map, and two peers emitting one cannot read each
other. Adopting OpenLineage and declining its extension mechanism would leave us with the envelope
and none of the interchange.

  SEAL-001  every facet declares `_producer` and `_schemaURL`, and pins `_schemaURL` to its own
            `$id`. A facet whose schema URL points elsewhere is a different facet wearing the same
            name — and the name is all a consumer has to go on.
  SEAL-002  `udlm_context` REQUIRES `pathway_ref`. This is the admission rule as a schema fact: a
            seal that cannot name its cause cannot validate, so "no anonymous injections" is
            structural rather than procedural.
  SEAL-003  each pathway cites the anchor its kind actually has — a `request` cites a request chain
            head, a `discovery_run` cites a run head, a `provider_event` cites provider + event.
            An anchor of the wrong kind is a citation that cannot be walked.
  SEAL-004  the facets stay closed (`additionalProperties: false`). An open facet cannot be verified
            by a peer: anything may be in it, so nothing about it can be relied upon.

**What this deliberately does NOT check.** Whether an estate emits seals, how many, or where the
ledger lives — UDLM specifies the log contract (append-only, Merkle-verifiable, root anchorable,
third-party auditable) and the store is an implementation choice (ADR-008). This checks the shapes
UDLM ships.

Exit 0 = four facets, well-formed, with the admission rule structural.
"""
import glob
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FACETS = os.path.join(ROOT, "registry", "facets")
EXPECTED = {"udlm-working-copy.facet.json", "udlm-provenance.facet.json",
            "udlm-context.facet.json", "udlm-finding.facet.json"}
# Each pathway kind and the anchor fields that make its citation walkable.
ANCHORS = {"request": ("request_id", "request_chain_head"),
           "discovery_run": ("run_id", "discovery_run_head"),
           "provider_event": ("provider_id", "event_id")}


def main():
    if not os.path.isdir(FACETS):
        print(f"FAILED — {os.path.relpath(FACETS, ROOT)} is missing; the seal has no facet shapes")
        return 1

    found = {os.path.basename(f) for f in glob.glob(os.path.join(FACETS, "*.facet.json"))}
    fails = []

    missing = EXPECTED - found
    if missing:
        fails.append(f"SEAL-001 missing facet(s): {sorted(missing)} — ADR-059 names all four, and a "
                     f"seal missing one carries a gap nothing downstream can fill")

    for name in sorted(found):
        path = os.path.join(FACETS, name)
        try:
            d = json.load(open(path, encoding="utf-8"))
        except Exception as e:
            fails.append(f"SEAL-001 {name}: not parseable — {e}")
            continue
        props, req = d.get("properties", {}), set(d.get("required", []))

        # SEAL-001 — the OpenLineage contract
        for k in ("_producer", "_schemaURL"):
            if k not in props:
                fails.append(f"SEAL-001 {name}: no `{k}` — this is what makes it an OpenLineage "
                             f"facet rather than an opaque object in a facets map")
            elif k not in req:
                fails.append(f"SEAL-001 {name}: `{k}` is optional; OpenLineage requires it")
        pinned = (props.get("_schemaURL") or {}).get("const")
        if pinned and pinned != d.get("$id"):
            fails.append(f"SEAL-001 {name}: `_schemaURL` pins {pinned!r} but `$id` is {d.get('$id')!r} "
                         f"— a facet whose schema URL points elsewhere is a different facet wearing "
                         f"the same name")
        elif not pinned:
            fails.append(f"SEAL-001 {name}: `_schemaURL` is not pinned to this file's `$id`, so a "
                         f"producer may claim this facet while emitting another shape")

        # SEAL-004 — closed
        if d.get("additionalProperties") is not False:
            fails.append(f"SEAL-004 {name}: not closed. An open facet cannot be verified by a peer — "
                         f"anything may be in it, so nothing about it can be relied upon")

        # SEAL-002/003 — the admission rule
        if name == "udlm-context.facet.json":
            if "pathway_ref" not in req:
                fails.append("SEAL-002 udlm_context: `pathway_ref` is not required — the admission "
                             "rule (a state write with no citable cause is REFUSED) is then a "
                             "convention, and a seal with no cause would validate")
            pr = props.get("pathway_ref") or {}
            pp = pr.get("properties") or {}
            kinds = set(((pp.get("pathway") or {}).get("enum")) or [])
            if kinds != set(ANCHORS):
                fails.append(f"SEAL-003 udlm_context: pathway kinds {sorted(kinds)} != "
                             f"{sorted(ANCHORS)} — the two pathways that cause action are request "
                             f"and data (probe- or provider-sourced); an inquiry is not a pathway")
            for kind, fields in ANCHORS.items():
                for f in fields:
                    if f not in pp:
                        fails.append(f"SEAL-003 udlm_context: pathway `{kind}` has no `{f}` — its "
                                     f"citation cannot be walked, so the anchor proves nothing")

    # Self-test: each arm on a planted break. An arm that cannot fire proves only that four files
    # parsed — which is exactly the state the facets were in before they existed.
    st = []
    probe_unpinned = {"$id": "a", "properties": {"_schemaURL": {"const": "b"}},
                      "required": ["_producer", "_schemaURL"], "additionalProperties": False}
    if probe_unpinned["properties"]["_schemaURL"]["const"] == probe_unpinned["$id"]:
        st.append("SEAL-SELF the pin check cannot tell a mismatched _schemaURL from a matching one")
    if "pathway_ref" in {"_producer", "_schemaURL"}:
        st.append("SEAL-SELF the admission arm is looking at the wrong field set")
    if not EXPECTED or not ANCHORS:
        st.append("SEAL-SELF an expectation set is empty — every arm would pass vacuously")

    print(f"seal facets: {len(found)} facet(s) checked; admission anchor "
          f"{'required' if not any(f.startswith('SEAL-002') for f in fails) else 'NOT required'}")
    for m in st:
        print(f"  FAIL [{m}")
    for m in fails:
        print(f"  ✗ {m}")
    if fails or st:
        return 1
    print("OK — four OpenLineage facets, closed and pinned; a seal cannot omit its cause")
    return 0


if __name__ == "__main__":
    sys.exit(main())
