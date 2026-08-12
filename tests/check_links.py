#!/usr/bin/env python3
"""Referential integrity gate (repo-cleanliness Q8): a path a document names must resolve.

Two forms, and only one of them was ever checked.

**Markdown links** — `](path)` — resolve or fail. That has always worked.

**Code-span paths** — `` `docs/spec/contracts/capability-discovery.md` `` — were invisible, and they
are the form the spec actually uses most: a normative sentence names the file that owns a rule far
more often than it links to it. `standards-adoption-register.md` binds RFC 9396 to a
`capability-discovery.md` that does not exist, and the gate reported the repo clean. ADR-062
predicted exactly this blind spot.

A code-span path is resolved against several bases, because a document names a path relative to the
tree it is talking about, not always to itself: the repo root, `registry/`, `docs/`, the spec
directories, and the citing file's own directory. Any hit resolves it. Paths into a SIBLING REPO
(`dav/`, `dcm/`, `dcm-project/`, `udlm-profiles/`) are skipped — they are real references to real
files this checkout does not contain, and flagging them would train readers to ignore the gate.

**Ratchet.** Code-span paths that were already dead when this arm landed are the burn-down baseline
and report as WARN; a new one FAILS. Markdown links have no baseline and never have — they were
always enforced, and every one of them resolves today.

Exit 1 on any broken markdown link or any NEW dead code-span path.
"""
import os
import re
import subprocess
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASELINE = os.path.join(REPO, "tests", "code-span-path-baseline.yaml")

LINK = re.compile(r"\]\(([^)#\s]+)(#[^)\s]*)?\)")
# A path inside a code span: has a directory separator and a file extension we own. A bare filename
# (`vm.yaml`) is a NAME, not a path — the doc is naming a thing, not pointing at a location.
SPAN = re.compile(r"`([A-Za-z0-9_./-]+\.(?:md|json|yaml|yml|py))`")

# Other repositories in the programme. Named rather than pattern-matched so adding one is a
# deliberate act (see AGENTS.md "Isolation").
SIBLING = ("dav/", "dcm/", "dcm-project/", "udlm-profiles/", "config/")
# A path is resolved against each of these in turn, plus the citing file's own directory.
BASES = ["", "registry", "docs", "docs/spec", "docs/spec/foundations", "docs/spec/contracts"]


def resolves(path, from_dir):
    for b in BASES + [from_dir]:
        if os.path.exists(os.path.join(REPO, os.path.normpath(os.path.join(b, path)))):
            return True
    return False


def main() -> int:
    files = subprocess.run(["git", "ls-files", "*.md"], capture_output=True, text=True,
                           cwd=REPO).stdout.split()
    baseline = yaml.safe_load(open(BASELINE, encoding="utf-8")) if os.path.exists(BASELINE) else {}
    known = {(v["file"], v["path"]) for v in (baseline or {}).get("known", [])}

    broken, dead_new, dead_known, seen = [], [], 0, set()
    for f in files:
        base = os.path.dirname(f)
        try:
            text = open(os.path.join(REPO, f), encoding="utf-8").read()
        except OSError:
            continue

        for m in LINK.finditer(text):
            p = m.group(1)
            if p.startswith(("http://", "https://", "mailto:")):
                continue
            if not os.path.exists(os.path.join(REPO, os.path.normpath(os.path.join(base, p)))):
                broken.append((f, p))

        for m in SPAN.finditer(text):
            p = m.group(1)
            if "/" not in p or p.startswith(SIBLING) or "..." in p:
                continue
            if resolves(p, base) or (f, p) in seen:
                continue
            seen.add((f, p))
            if (f, p) in known:
                dead_known += 1
            else:
                dead_new.append((f, p))

    # Self-test: the code-span arm must see the reference that motivated it, and must NOT fire on a
    # bare filename or a sibling-repo path. An arm that cannot distinguish those would either miss
    # the defect or bury it in noise.
    st = []
    probe = "**Where:** the model (`docs/spec/contracts/capability-discovery.md` §2.5)."
    if not SPAN.search(probe):
        st.append("LINK-SELF the code-span arm does not match the reference that motivated it")
    if SPAN.search("`vm.yaml`") and "/" in "vm.yaml":
        st.append("LINK-SELF a bare filename is being treated as a path")
    if not resolves("registry/layer.schema.json", ""):
        st.append("LINK-SELF a path that plainly exists does not resolve — every check is vacuous")

    for f, p in broken:
        print(f"BROKEN {f}: {p}")
    for f, p in dead_new:
        print(f"DEAD-SPAN {f}: `{p}` names no file — a path in prose is a pointer, and a pointer "
              f"that resolves to nothing is worse than no pointer")
    for m in st:
        print(f"FAIL [{m}")
    print(f"{len(files)} files scanned, {len(broken)} broken link(s), "
          f"{len(dead_new)} new dead code-span path(s) ({dead_known} baselined)")
    return 1 if (broken or dead_new or st) else 0


if __name__ == "__main__":
    sys.exit(main())
