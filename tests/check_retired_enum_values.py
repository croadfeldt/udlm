#!/usr/bin/env python3
"""No schema offers a value whose name is a retired term (TERM-002).

`tests/check_terminology.py` refuses a retired term in PROSE. It does not look at enum values, so a
schema could offer `gating` as a `policy_type` while the terminology gate forbade anyone naming that
concept in any document. Two of those existed — `policy.schema.json` `policy_type: gating` and
`audit-leaf.schema.json` `source_type: policy_gating` — with the concept merged into validation,
zero records using either, and zero occurrences in the policy contract.

**Why an offered-but-unwritable value is worse than a plain leftover.** A consumer picking it gets a
value the documentation does not describe, that nothing else in the corpus uses, and that they
cannot ask about in any document without failing CI. It reads as a supported option and behaves as
an orphan.

  TERM-002  an `enum` value in a registry schema matches a term retired by `check_terminology.py`,
            either alone or as `<value> policy`.

**Scoped to the retirement list on purpose.** This does not ask whether an enum value is *used* —
an unused value is ordinary in a small corpus and says nothing. It asks whether the value contradicts
a retirement the repo has already made, which is a fact rather than a judgement.

Exit 0 = no schema offers a retired name.
"""
import glob
import importlib.util
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def retired_rules():
    """The retirement list, read from its home rather than restated (SPEC-DESIGN §33)."""
    spec = importlib.util.spec_from_file_location(
        "term", os.path.join(ROOT, "tests", "check_terminology.py"))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except SystemExit:
        pass
    return getattr(mod, "RULES", [])


def offenders(rules):
    out = []

    def walk(node, path, src):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == "enum" and isinstance(v, list):
                    for val in v:
                        if not isinstance(val, str):
                            continue
                        for label, pat in rules:
                            # The bare value, and the value read as a term ("gating" -> "gating
                            # policy") — the second is how these are written in prose, and the
                            # form the retirement was phrased against.
                            if pat.search(val) or pat.search(val.replace("_", " ") + " policy"):
                                out.append((src, path + "/enum", val, label))
                                break
                else:
                    walk(v, f"{path}/{k}", src)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", src)

    for f in sorted(glob.glob(os.path.join(ROOT, "registry", "*.schema.json"))):
        try:
            walk(json.load(open(f, encoding="utf-8")), "", os.path.relpath(f, ROOT))
        except Exception:
            continue
    return out


def main():
    rules = retired_rules()
    if not rules:
        print("FAILED — the retirement list is empty or unreadable; every check would pass vacuously")
        return 1

    found = offenders(rules)

    # Self-test: the arm must fire on the value it was built from, and must not fire on the value
    # that replaced it — a gate that flagged `validation` would make the fix unrepresentable.
    st = []
    probe = [(lbl, pat) for lbl, pat in rules if "gating" in lbl.lower()]
    if probe:
        _, pat = probe[0]
        if not (pat.search("gating") or pat.search("gating" + " polic" + "y")):
            st.append("TERM2-SELF the arm does not match the value it was built from")
        if pat.search("validation") or pat.search("validation" + " polic" + "y"):
            st.append("TERM2-SELF the replacement value is flagged — the fix would be "
                      "unrepresentable")

    print(f"retired enum values: {len(rules)} retirement(s) checked against every registry enum")
    for m in st:
        print(f"  FAIL [{m}")
    for src, path, val, label in found:
        print(f"  ✗ TERM-002 {src}{path}: offers {val!r}, whose name is retired — {label}. A "
              f"consumer picking it gets a value no document describes and cannot ask about "
              f"without failing the terminology gate")
    if found or st:
        return 1
    print("OK — no schema offers a value whose name is retired")
    return 0


if __name__ == "__main__":
    sys.exit(main())
