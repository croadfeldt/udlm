#!/usr/bin/env python3
"""Guide-integrity gate (DOC-002): the contributor guides must not rot. Every repo path a guide points
at — a schema, a gate, a worked example, a sibling guide — must exist. A guide that references a deleted
gate or a renamed schema is worse than none, because a newcomer follows it verbatim.

Scope: the distribution guides — docs/guides/working-with-udlm.md, docs/authoring/**, and the role guides
(docs/guides/reviewing.md, docs/guides/consuming.md, docs/guides/contributing-guide.md). For each, this checks:
  - every Markdown link `[text](target)` to a relative path resolves to a real file;
  - every backticked repo path (registry/…, tests/…, scripts/…, use-cases/…, docs/…, .github/…) exists
    (globs and pure directory mentions are allowed — a dir must still exist).

Exit 0 = every reference resolves. This is how the guides stay accurate as the model evolves.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

GUIDE_GLOBS = [
    "docs/guides/working-with-udlm.md",
    "docs/authoring/*.md",
    "docs/guides/reviewing.md",
    "docs/guides/consuming.md",
    "docs/guides/contributing-guide.md",
]
REPO_DIRS = ("registry/", "tests/", "scripts/", "use-cases/", "docs/", ".github/")
LINK = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
BACKTICK = re.compile(r"`([^`]+)`")


def guide_files():
    out = []
    for g in GUIDE_GLOBS:
        out += glob.glob(os.path.join(ROOT, g))
    return sorted(set(out))


def _exists(rel):
    p = os.path.join(ROOT, rel)
    return os.path.exists(p)


def check_file(path):
    rel = os.path.relpath(path, ROOT)
    text = open(path, encoding="utf-8").read()
    d = os.path.dirname(path)
    fails = []

    # (1) Markdown links to relative paths must resolve (skip URLs and pure #anchors)
    for target in LINK.findall(text):
        t = target.split("#", 1)[0].strip()
        if not t or t.startswith(("http://", "https://", "mailto:")):
            continue
        resolved = os.path.normpath(os.path.join(d, t))
        if not os.path.exists(resolved):
            fails.append(f"{rel}: link target does not resolve -> {target}")

    # (2) Backticked repo paths must exist (globs allowed if the glob matches anything;
    #     a trailing-slash dir must exist as a directory)
    for tok in BACKTICK.findall(text):
        tok = tok.strip()
        if not tok.startswith(REPO_DIRS):
            continue
        if tok.endswith((".", ":")) or " " in tok:
            continue
        # placeholder templates (`registry/.../<type>.yaml`, `ADR-0NN-<title>`, `foo/...`) are
        # illustrative, not references — skip anything with a template marker.
        if "<" in tok or ">" in tok or "..." in tok:
            continue
        if any(c in tok for c in "*?{"):
            if not glob.glob(os.path.join(ROOT, tok)):
                fails.append(f"{rel}: backticked glob matches nothing -> {tok}")
            continue
        if not _exists(tok.rstrip("/")):
            fails.append(f"{rel}: backticked repo path does not exist -> {tok}")
    return fails


def main():
    files = guide_files()
    fails = []
    for p in files:
        fails += check_file(p)
    for f in fails:
        print("FAIL [DOC-002] " + f)
    print(f"{len(files)} guide file(s) checked, {len(fails)} dangling reference(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
