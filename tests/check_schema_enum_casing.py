#!/usr/bin/env python3
"""Enum values in the record schemas are snake_case, or say why not (SEC-001..003).

Row 103 made every value UDLM mints snake_case; `check_type_standard.py` holds the classes to it.
This gate holds `registry/*.schema.json` to the same rule (row 134). A value that is not snake_case
must be one of three things, and the schema node says which:

  x-standard: "<standard>:<where>"   copied verbatim from an adopted standard, which the
                                     standards-adoption register names (`NoSchedule`, `True`)
  x-value-form: name                 the values are names in the PascalCase name grammar
                                     (families, the four states, class names used as values)
  x-value-form: notation             the values are a notation, not words (`0..n`)

  SEC-001  a stable schema has a non-snake value with no marker                       -> FAIL
  SEC-002  an x-standard names a standard the adoption register does not list           -> FAIL
  SEC-003  the same in a schema marked experimental in registry/stability.yaml          -> WARN

The one legacy spelling (`sha256-jcs`, row 121) is listed in check_record_values.LEGACY and is
accepted here for the same reason.
"""
import glob
import json
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_record_values import LEGACY  # noqa: E402

SNAKE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")
FORMS = {"name", "notation"}


def adopted_standards():
    text = open(os.path.join(REPO, "registry", "standards-adoption-register.md"), encoding="utf-8").read()
    return [h.strip() for h in re.findall(r"^### (.+?)(?: —.*)?$", text, re.M)]


def stability():
    doc = yaml.safe_load(open(os.path.join(REPO, "registry", "stability.yaml"), encoding="utf-8"))
    return {r["part"]: r["stability"] for r in doc.get("parts") or []}


def walk(node, path, schema_rel, standards, out):
    if isinstance(node, dict):
        values = node.get("enum")
        if isinstance(values, list):
            bad = [v for v in values if isinstance(v, str) and not SNAKE.match(v)
                   and (schema_rel, path, v) not in LEGACY]
            if bad:
                marker = node.get("x-standard")
                form = node.get("x-value-form")
                if isinstance(marker, str):
                    name = marker.split(":", 1)[0].strip()
                    if not any(name.lower() in h.lower() for h in standards):
                        out.append((path, f"x-standard names {name!r}, which the adoption register does not list"))
                elif form in FORMS:
                    pass
                else:
                    out.append((path, f"{bad} — not snake_case and no x-standard or x-value-form says why"))
        for k, v in node.items():
            if k in ("enum", "examples", "default", "const", "description"):
                continue
            walk(v, f"{path}/{k}", schema_rel, standards, out)
    elif isinstance(node, list):
        for i, v in enumerate(node):
            walk(v, f"{path}[{i}]", schema_rel, standards, out)


def main():
    standards = adopted_standards()
    stab = stability()
    fails, warns = [], []
    n = 0
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "*.schema.json"))):
        rel = os.path.relpath(f, REPO)
        n += 1
        found = []
        walk(json.load(open(f, encoding="utf-8")), "", rel, standards, found)
        level = stab.get("schema:" + os.path.basename(f), "stable")
        for path, why in found:
            rule = "SEC-002" if why.startswith("x-standard") else "SEC-001"
            line = f"{rule} {rel}{path}: {why}"
            (fails if level == "stable" else warns).append(line if level == "stable" else f"SEC-003 (experimental) {line}")
    for w in warns:
        print("WARN", w)
    for x in fails:
        print("FAIL", x)
    print(f"schema enum casing: {n} schema(s); {len(fails)} failure(s), {len(warns)} warning(s) in experimental schemas")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
