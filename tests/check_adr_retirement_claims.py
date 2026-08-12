#!/usr/bin/env python3
"""An ADR must not claim a retirement the model never made (RET-001).

**Where this came from.** ADR-054 stated, present tense: *"`reference_data` is retired from
`layer_type`"* and *"`layer_type` is now assembly-only"*. It was in the enum the whole time, and not
vestigially — `data-reference.schema.json` requires an in-field reference to resolve to a layer with
`layer_type: reference_data`, `validate.py` enforces that, and corpus records depended on it. A
reader who trusted the record and built assembly-only layer types would have got an implementation
where every data reference failed to resolve.

Three things made it survive:

  - **ADR-054 is the one `Accepted` record**, so it is the highest-authority statement in the repo.
  - The record **contradicted itself**: its own header said the retirement was gated on ADR-058.
    Only the body claimed it done. Nothing compares a header to a body.
  - The rule-ID single-source gate reads a rule as defined in one file and passes; an ADR and a
    schema disagreeing are two files, each internally consistent.

The resolution was not to finish the retirement. `reference_data` marks a layer other layers
reference — shared data — which is sound, and the ruling (2026-08-11) kept it; what actually
happened is that two records were MISFILED under it. So the defect was never "an unfinished
migration". It was **an ADR asserting a state of the world that had not been checked against the
world**, and either direction of fix leaves that assertion needing to be true.

  RET-001  an ADR states in the PRESENT or PAST tense that a value is retired/removed from a named
           field, while a registry schema still carries that value in that field's enum.

**Deliberately narrow, and here is the line.** This does not police whether a decision is wise, nor
prose about future intent — "X SHOULD be retired", "X will be retired", "retiring X is gated on
ADR-058" are all fine and all say something true about a decision not yet made. It fires only on a
claim about a state that is checkable right now and is false right now. An ADR is for the context
and reasoning behind a question (maintainer ruling); the moment it narrates implementation status,
it can be wrong, and this is the mechanically checkable slice of that.

Exit 0 = no ADR claims a retirement the schemas contradict.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADRS = os.path.join(ROOT, "docs", "adr")
REGISTRY = os.path.join(ROOT, "registry")

# "`value` is retired from `field`" / "`value` removed from `field`" and the reversed word order
# "retired `value` from `field`". Present or past tense only — a modal ("should", "will", "is gated
# on") is a statement about intent, not about the world, and never fires.
CLAIMS = [
    re.compile(r"`(?P<value>[a-z][a-z0-9_]*)`\s+(?:is|was|has been|are|were)\s+"
               r"(?:now\s+)?(?:retired|removed|dropped)\s+from\s+`(?P<field>[a-z][a-z0-9_]*)`",
               re.IGNORECASE),
    re.compile(r"(?:retired|removed|dropped)\s+`(?P<value>[a-z][a-z0-9_]*)`\s+from\s+"
               r"`(?P<field>[a-z][a-z0-9_]*)`", re.IGNORECASE),
]
# A modal anywhere in the sentence makes it a statement of intent. Checked on the whole line because
# "the `x` retirement is gated on ADR-058" puts the qualifier well away from the verb.
MODAL = re.compile(r"\b(should|shall|will|would|must|to be|gated on|pending|once|when|if|proposes?|"
                   r"proposal|plan|planned|intends?|plans to|plan to|not retire|does not retire|"
                   r"stays|remains|keeps)\b", re.IGNORECASE)


def enum_values_for(field):
    """Every value any registry schema allows in a property of this name, with where.

    Walks the whole document rather than a fixed path: an enum nested in a `$defs` or under an
    `allOf` branch constrains the field just as much as one at the top, and the fixed-path habit is
    what let earlier gates report clean on surfaces nobody sampled."""
    found = {}

    def walk(node, path, src, key=None):
        if isinstance(node, dict):
            if key == field and isinstance(node.get("enum"), list):
                for v in node["enum"]:
                    if isinstance(v, str):
                        found.setdefault(v, []).append(f"{src}{path}")
            for k, v in node.items():
                walk(v, f"{path}/{k}", src, k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", src, key)

    for f in sorted(glob.glob(os.path.join(REGISTRY, "*.schema.json"))):
        try:
            walk(json.load(open(f, encoding="utf-8")), "", os.path.relpath(f, ROOT))
        except Exception:
            continue
    return found


def main():
    if not os.path.isdir(ADRS):
        print("FAILED — docs/adr is missing")
        return 1

    fails, claims_seen = [], 0
    for path in sorted(glob.glob(os.path.join(ADRS, "*.md"))):
        rel = os.path.relpath(path, ROOT)
        for lineno, line in enumerate(open(path, encoding="utf-8"), 1):
            for pat in CLAIMS:
                m = pat.search(line)
                if not m:
                    continue
                if MODAL.search(line):
                    continue                    # intent, not a claim about the world
                claims_seen += 1
                value, field = m.group("value"), m.group("field")
                where = enum_values_for(field).get(value)
                if where:
                    fails.append(
                        f"RET-001 {rel}:{lineno} states `{value}` is retired from `{field}`, and it "
                        f"is still in that enum: {', '.join(where[:3])}")
                    fails.append(f"          {line.strip()[:150]}")

    # Self-test. Each arm gets a planted case — an arm that cannot fire proves only that the files
    # parsed, and a gate over a claim nobody re-checks is how the original defect survived.
    probe_claim = "**`reference_data` is retired from `layer_type`**: context is never merged."
    probe_intent = "the `reference_data` retirement is **gated on ADR-058**, so `layer_type` waits."
    st = []
    if not any(p.search(probe_claim) for p in CLAIMS):
        st.append("RET-SELF the claim pattern does not match the sentence it was built from")
    if MODAL.search(probe_claim):
        st.append("RET-SELF a bare claim is misread as intent — the gate would never fire")
    if not MODAL.search(probe_intent):
        st.append("RET-SELF a gated/pending sentence is not recognized as intent — the gate would "
                  "flag honest statements about undecided work")
    if not enum_values_for("layer_type"):
        st.append("RET-SELF no `layer_type` enum was found in registry/*.schema.json — the enum "
                  "scan is not reaching the schemas, so every check would pass vacuously")

    print(f"adr retirement claims: {claims_seen} present-tense retirement claim(s) checked against "
          f"the registry enums")
    for m in st:
        print(f"  FAIL [{m}")
    for m in fails:
        print(f"  {'✗ ' if m.startswith('RET') else '   '}{m}")
    if fails or st:
        if fails:
            print("\nFix: either finish the retirement, or say what is true — an ADR records the "
                  "context and reasoning behind a decision; the moment it narrates implementation "
                  "status it can be, and here is, wrong.")
        return 1
    print("OK — no ADR claims a retirement the schemas contradict")
    return 0


if __name__ == "__main__":
    sys.exit(main())
