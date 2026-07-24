#!/usr/bin/env python3
"""Render registry/TYPE-CATALOG.md from the type specs' `context` blocks (rule 36(l)).

Generated, never hand-edited — regenerate after any context change:
    python3 registry/tools/generate_type_catalog.py            # write the catalog
    python3 registry/tools/generate_type_catalog.py --check    # CI: fail if stale
"""
import glob
import json
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, "registry", "TYPE-CATALOG.md")


def render():
    types = []
    for f in sorted(glob.glob(os.path.join(ROOT, "registry", "resource-types", "*.json")) +
                    glob.glob(os.path.join(ROOT, "registry", "resource-types", "*.yaml"))):
        with open(f, encoding="utf-8") as fh:
            d = json.load(fh) if f.endswith(".json") else yaml.safe_load(fh)
        if isinstance(d, dict):
            types.append(d)
    lines = ["# Type catalog — every resource type, in plain English", "",
             "> GENERATED from the `context` blocks in `registry/resource-types/` by",
             "> `registry/tools/generate_type_catalog.py` — edit the spec, regenerate, never edit here.",
             "> Missing entries are types without a `context` block yet (tracked by the rule-36 gate).", ""]
    by_cat = {}
    for d in types:
        rt = d.get("resource_type", "?")
        by_cat.setdefault(rt.split(".")[0], []).append(d)
    missing = 0
    for cat in sorted(by_cat):
        lines += [f"## {cat}", ""]
        for d in sorted(by_cat[cat], key=lambda x: x.get("resource_type", "")):
            rt, ver = d.get("resource_type"), d.get("version", "")
            ctx = d.get("context")
            if not ctx:
                lines += [f"### {rt} ({ver})", "", "*No plain-English context yet — pending the context wave.*", ""]
                missing += 1
                continue
            lines += [f"### {rt} ({ver})", "", f"**Purpose:** {ctx['purpose']}", "", ctx["plain_description"], "",
                      "**Use when:**"]
            lines += [f"- {u}" for u in ctx.get("use_when", [])]
            if ctx.get("not_for"):
                lines += ["", "**Not for:**"] + [f"- {u}" for u in ctx["not_for"]]
            if ctx.get("works_with"):
                lines += ["", "**Works with:**"] + [f"- {u}" for u in ctx["works_with"]]
            lines += [""]
    lines += ["---", f"*{len(types)} types; {len(types)-missing} with context, {missing} pending.*", ""]
    return "\n".join(lines)


def main():
    text = render()
    if "--check" in sys.argv:
        current = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if current != text:
            print("STALE: registry/TYPE-CATALOG.md does not match the specs' context blocks — regenerate.")
            return 1
        print("TYPE-CATALOG.md is current.")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
