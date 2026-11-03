#!/usr/bin/env python3
"""The spec stays readable (RDB-001..003, row 138).

The maintainer's standard: a person can read any part of the spec cold. One idea per sentence; a
register row is a short paragraph; a description says what the thing is and stops. This gate holds
three measurable parts of that standard. Fidelity is not negotiable: a sentence is shortened by
splitting it, never by dropping a MUST, a rule id or an invariant.

  RDB-001  a sentence over 40 words — in a register row, a rule row, a class or element
           description, a record-schema description, or spec prose                    -> FAIL
  RDB-002  a register row over 150 words                                                -> FAIL
  RDB-003  a class, element or record-schema description over 80 words                 -> FAIL

Scope: docs/adr/README.md rows, docs/spec/**/*.md, registry/classes/**/*.yaml, registry/*.schema.json.
Code blocks, tables other than rule rows, and YAML examples are not prose and are skipped.

Baseline: tests/readability-baseline.txt lists the violations that predate the gate, one per line
(`RULE key`). A listed violation only warns; an unlisted one fails; a listed one that no longer
violates is stale and fails, so the baseline can only shrink. `--update` rewrites it from the
current state (for the sweep PRs, never to hide a new violation).
"""
import glob
import hashlib
import json
import os
import re
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, "tests", "readability-baseline.txt")
SENTENCE_MAX, ROW_MAX, DESC_MAX = 40, 150, 80
RULE_ROW = re.compile(r"^\|\s*`?([A-Z][A-Z0-9]{1,7}(?:-[A-Z]{1,5})*-\d{2,3}(?:\.\d{1,2})?)`?\s*\|(.*)$")
REG_ROW = re.compile(r"^\|\s*(\d{3})\s*\|(.*)\|\s*$")


def sentences(text):
    """Split prose into sentences. A list item is its own sentence (the marker starts one); a bold
    lead-in like `**Why.**` ends one; a period inside a code span does not."""
    text = re.sub(r"`[^`]*`", lambda m: m.group(0).replace(". ", "·"), text)
    text = re.sub(r"\n\s*(?:[-*+]|\d+\.)\s+", "\n\u2063", text)          # list marker -> boundary mark
    text = text.replace("\n", " ")
    parts = re.split(r"(?<=[.!?:])\s+(?=[A-Z`*(\"'\[])|(?<=[.!?]\*\*)\s+|\s*\u2063", text)
    return [p.strip() for p in parts if p.strip()]


def words(text):
    return len(re.sub(r"`[^`]*`", "x", text).split())


def key(*parts):
    return ":".join(str(p) for p in parts)


def shash(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:10]


def findings():
    out = []  # (rule, key, detail)

    # register rows
    for line in open(os.path.join(REPO, "docs", "adr", "README.md"), encoding="utf-8"):
        m = REG_ROW.match(line)
        if not m:
            continue
        n, body = m.group(1), m.group(2)
        if words(body) > ROW_MAX:
            out.append(("RDB-002", key("register", n), f"row {n}: {words(body)} words"))
        for s in sentences(body):
            if words(s) > SENTENCE_MAX:
                out.append(("RDB-001", key("register", n, shash(s)), f"row {n}: {words(s)}-word sentence: {s[:70]}…"))

    # spec prose and rule rows
    for f in sorted(glob.glob(os.path.join(REPO, "docs", "spec", "**", "*.md"), recursive=True)):
        rel = os.path.relpath(f, REPO)
        text = open(f, encoding="utf-8").read()
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        para = []
        def flush():
            for s in sentences(" ".join(para)):
                if words(s) > SENTENCE_MAX:
                    out.append(("RDB-001", key(rel, shash(s)), f"{rel}: {words(s)}-word sentence: {s[:70]}…"))
            para.clear()
        for line in text.split("\n"):
            m = RULE_ROW.match(line)
            if m:
                flush()
                body = m.group(2).split("|")[0] if m.group(2) else ""
                for s in sentences(body):
                    if words(s) > SENTENCE_MAX:
                        out.append(("RDB-001", key(rel, m.group(1), shash(s)), f"{rel} {m.group(1)}: {words(s)}-word sentence: {s[:70]}…"))
                continue
            if not line.strip() or line.startswith("|") or line.startswith("#") or line.startswith(">"):
                flush()
                continue
            para.append(line.strip())
        flush()

    # classes
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "classes", "**", "*.yaml"), recursive=True)):
        d = yaml.safe_load(open(f, encoding="utf-8"))
        rt = d.get("resource_type", os.path.relpath(f, REPO))
        items = [(key("class", rt), (d.get("metadata") or {}).get("description") or "")]
        for e in d.get("elements") or []:
            items.append((key("class", rt, e.get("element")), e.get("description") or ""))
        for k, desc in items:
            if words(desc) > DESC_MAX:
                out.append(("RDB-003", k, f"{k}: {words(desc)}-word description"))
            for s in sentences(desc):
                if words(s) > SENTENCE_MAX:
                    out.append(("RDB-001", key(k, shash(s)), f"{k}: {words(s)}-word sentence: {s[:70]}…"))

    # record schemas
    def walk(node, path, rel):
        if isinstance(node, dict):
            desc = node.get("description")
            if isinstance(desc, str):
                k = key(rel, path or "/")
                if words(desc) > DESC_MAX:
                    out.append(("RDB-003", k, f"{k}: {words(desc)}-word description"))
                for s in sentences(desc):
                    if words(s) > SENTENCE_MAX:
                        out.append(("RDB-001", key(k, shash(s)), f"{k}: {words(s)}-word sentence: {s[:70]}…"))
            for kk, v in node.items():
                if kk != "description":
                    walk(v, f"{path}/{kk}", rel)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, f"{path}[{i}]", rel)
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "*.schema.json"))):
        walk(json.load(open(f, encoding="utf-8")), "", os.path.basename(f))
    return out


def main():
    found = findings()
    if "--update" in sys.argv:
        with open(BASELINE, "w", encoding="utf-8") as fh:
            fh.write("# Readability violations that predate the gate (tests/check_readability.py). Shrink only.\n")
            for rule, k in sorted(set((r, k) for r, k, _ in found)):
                fh.write(f"{rule} {k}\n")
        print(f"baseline rewritten: {len(set((r, k) for r, k, _ in found))} entr(y/ies)")
        return 0
    baseline = set()
    if os.path.exists(BASELINE):
        for line in open(BASELINE, encoding="utf-8"):
            line = line.strip()
            if line and not line.startswith("#"):
                rule, k = line.split(" ", 1)
                baseline.add((rule, k))
    current = {(r, k): d for r, k, d in found}
    new = [(rk, d) for rk, d in current.items() if rk not in baseline]
    stale = [rk for rk in baseline if rk not in current]
    for rk, d in sorted(new):
        print(f"FAIL [{rk[0]}] {d}")
    for rk in sorted(stale):
        print(f"FAIL [RDB-STALE] {rk[0]} {rk[1]} no longer violates — remove it from the baseline")
    by = {}
    for r, _ in current:
        by[r] = by.get(r, 0) + 1
    print(f"readability: {len(current)} violation(s) — " + ", ".join(f"{r} {n}" for r, n in sorted(by.items()))
          + f"; {len(current) - len(new)} baselined, {len(new)} new, {len(stale)} stale")
    return 1 if new or stale else 0


if __name__ == "__main__":
    sys.exit(main())
