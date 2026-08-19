#!/usr/bin/env python3
"""Refresh the control-plane ADR index from croadfeldt/dcm.

The index is checked in rather than fetched at gate time, so CI stays offline and a network blip
cannot turn into a red build. That makes it a snapshot, and a snapshot goes stale — run this when
the control plane adds an ADR.

Needs `gh` authenticated against croadfeldt/dcm. Prints the diff rather than applying it silently:
a number LEAVING the index means UDLM citations to it are now dangling, which is a finding, not a
routine update.
"""
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX = os.path.join(ROOT, "tests", "dcm-adr-index.yaml")
PATH = re.compile(r"architecture/adr/(\d{3})-([a-z0-9-]+)\.md$")


def fetch():
    out = subprocess.run(
        ["gh", "api", "repos/croadfeldt/dcm/git/trees/HEAD?recursive=1"],
        capture_output=True, text=True)
    if out.returncode != 0:
        sys.exit(f"gh failed — is it authenticated for croadfeldt/dcm?\n{out.stderr.strip()}")
    found = {}
    for e in json.loads(out.stdout).get("tree", []):
        m = PATH.search(e.get("path", ""))
        if m:
            found[m.group(1)] = m.group(2).replace("-", " ")
    return found


def current():
    import yaml
    d = yaml.safe_load(open(INDEX, encoding="utf-8")) or {}
    return {str(k): v for k, v in (d.get("adrs") or {}).items()}


def main():
    new, old = fetch(), current()
    if not new:
        sys.exit("no ADRs found in the control-plane tree — refusing to write an empty index")

    added = sorted(set(new) - set(old))
    gone = sorted(set(old) - set(new))
    renamed = sorted(n for n in set(new) & set(old) if new[n] != old[n])

    if not (added or gone or renamed):
        print(f"control-plane ADR index is current — {len(new)} entr(ies)")
        return 0

    for n in added:
        print(f"  + ADR-{n} {new[n]}")
    for n in renamed:
        print(f"  ~ ADR-{n} {old[n]} -> {new[n]}")
    for n in gone:
        print(f"  - ADR-{n} {old[n]}  — any UDLM citation to it is now dangling")

    head = [ln for ln in open(INDEX, encoding="utf-8").read().splitlines()
            if ln.startswith("#") or ln.startswith("source:")]
    body = "\n".join(f"  '{n}': {new[n]}" for n in sorted(new))
    open(INDEX, "w").write("\n".join(head) + "\nadrs:\n" + body + "\n")
    print(f"\nwrote {os.path.relpath(INDEX, ROOT)} — {len(new)} entr(ies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
