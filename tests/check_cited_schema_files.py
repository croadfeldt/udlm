#!/usr/bin/env python3
"""Every `*.schema.json` a document or schema names must exist.

A citation to a schema file that is not there is a silent lie: it reads as a pointer to an
authoritative shape and resolves to nothing. This landed as a real defect —
`registry/dcm-group.schema.json` was superseded by `Access.Grouping` and deleted, and three
citations survived it, including the description of `realized-entity.schema.json`'s own
`tenant_uuid`. The single most load-bearing field in the tenancy model pointed at a missing file,
and every gate in the repo passed.

  CSF-001  a cited `<name>.schema.json` resolves to a file that exists.

**Deliberately narrow.** This checks FILE citations only — a token ending `.schema.json` — because
that is decidable. The broader defect this came from (normative prose naming a *field* that no
schema declares — `ownership_model`, `publicly_stakeable`) is NOT checked here: matching field
names out of prose needs a curated list, not a regex, and a fuzzy version would produce noise
until it was ignored. Tracked as a follow-up rather than approximated.

**Scope, and what is deliberately excluded.** Two citation forms are decidable and both are checked:

  - every string in a JSON schema under registry/ — descriptions AND `$ref` values, since a broken
    relative `$ref` is resolved lazily by jsonschema and can go unnoticed until that branch is
    exercised. This is where the defect above lived.
  - a path-qualified citation anywhere (`registry/x.schema.json`) — unambiguous wherever it appears.

Two forms are NOT checked, each for a reason:

  - **a bare basename in prose** (`entity.schema.json` in a Proposed ADR). Every ADR here is
    Proposed, and naming the schema a decision *would* create is legitimate authorship, not a
    dangling pointer. Failing those would train the reader to ignore this gate.
  - **a bare basename in a YAML comment** — prose, judged the same way as prose in markdown.

Authored class `$ref`s ARE checked. They were excluded while ~20 of them pointed one directory
level too high — written against a two-deep convention that ADR-061's hierarchy made three-deep.
Nothing broke, because the generator rebases any depth to one level and the GENERATED artifact
resolved correctly, which is what a consumer reads. The authored file did not, which is what an
editor, an IDE, or anything resolving a class directly reads. Corrected, so the exclusion is gone
and a `$ref` that stops resolving now fails here.

Canonical `https://udlm.dev/...` URLs are identity, not paths, and are skipped.

Exit 0 = every cited schema file exists; 1 = at least one does not.
"""
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOPLEVEL = ("registry/", "docs/", "tests/", "use-cases/", "scripts/")
# a schema-file token, optionally path-qualified; stops at whitespace, quotes, parens, commas
CITATION = re.compile(r"(?<![\w/.-])((?:[\w.-]+/)*[\w.-]+\.schema\.json)")


def _iter_strings(node):
    """Every string in a JSON document — descriptions, $refs, enum members, the lot."""
    if isinstance(node, dict):
        for v in node.values():
            yield from _iter_strings(v)
    elif isinstance(node, list):
        for v in node:
            yield from _iter_strings(v)
    elif isinstance(node, str):
        yield node


def resolve(citation, citing_file):
    """Does this citation name a file that exists? Mirrors how a reader would follow it."""
    if citation.startswith(TOPLEVEL):
        return os.path.exists(os.path.join(ROOT, citation))
    if "/" in citation:
        # relative to the citing file, the way a $ref resolves
        if os.path.exists(os.path.normpath(os.path.join(os.path.dirname(citing_file), citation))):
            return True
        return os.path.exists(os.path.join(ROOT, citation))
    # a bare basename — resolves if the file exists anywhere under registry/
    return bool(glob.glob(os.path.join(ROOT, "registry", "**", citation), recursive=True))


def citations_in(path):
    """(citation, checked?) pairs — see the module docstring for what is out of scope and why."""
    rel = os.path.relpath(path, ROOT)
    out = []
    if path.endswith(".json"):
        try:
            doc = json.load(open(path, encoding="utf-8"))
        except Exception:
            return out
        for s in _iter_strings(doc):
            if s.startswith("https://"):        # a canonical URL is an identity, not a path on disk
                continue
            for m in CITATION.findall(s):
                out.append((m, rel))
        return out
    # YAML: $ref targets resolve relative to the citing file, like any other reference
    for line in open(path, encoding="utf-8", errors="replace"):
        if "https://" in line and ".schema.json" in line:
            line = re.sub(r"https://\S+", " ", line)
        stripped = line.lstrip()
        is_ref = stripped.startswith("$ref:") or stripped.startswith("- $ref:")
        for m in CITATION.findall(line):
            if m.startswith(TOPLEVEL) or (is_ref and not stripped.startswith("#")):
                out.append((m, rel))
    return out


def scan():
    files = []
    for pat in ("registry/**/*.json", "registry/**/*.yaml", "registry/**/*.md", "docs/**/*.md"):
        files += glob.glob(os.path.join(ROOT, pat), recursive=True)
    seen, fails = set(), []
    for path in sorted(set(files)):
        if os.sep + "generated" + os.sep in path:
            continue            # generated artifacts mirror their sources; the source is the subject
        for citation, rel in citations_in(path):
            if (citation, rel) in seen:
                continue
            seen.add((citation, rel))
            if not resolve(citation, path):
                fails.append(f"CSF-001 {rel}: cites `{citation}`, which does not exist")
    return len(seen), fails


def main():
    total, fails = scan()

    # self-test: the gate must be able to fail, or it only proves the walk ran
    if resolve("registry/definitely-not-a-real.schema.json", os.path.join(ROOT, "registry", "x.json")):
        print("FAIL [CSF-SELF] the resolver accepted a path that does not exist")
        fails.append("self-test")
    if not resolve("class.schema.json", os.path.join(ROOT, "registry", "x.json")):
        print("FAIL [CSF-SELF] the resolver rejected a bare basename that does exist")
        fails.append("self-test")

    print(f"cited-schema-files: {total} citation(s) checked")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} citation(s) resolve to nothing")
        return 1
    print("OK — every cited schema file exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
