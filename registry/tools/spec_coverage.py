#!/usr/bin/env python3
"""Spec-completeness gate (rule-36 — CONTRIBUTING "a spec travels with its story"): every
resource-type spec and Class ships with a Use Case, a worked example, and a flow.

The link is STRUCTURAL: a spec carries a `coverage:` block naming its use_cases / examples / flows
(maintainer ruling 2026-07-27, option (a) — the story stays attached to the spec). This tool is the
authority on that link:

  spec_coverage.py            human scoreboard — covered vs backlog, and any dangling referents (exit 0)
  spec_coverage.py --check    CI gate: (1) every declared coverage referent RESOLVES (UC handle / flow
                              file / example instance exists), else fail; (2) the backfill backlog
                              (registry/spec-coverage-backlog.yaml — specs with no coverage block yet)
                              is regenerated and compared, so a new uncovered spec can't slip in
                              silently — it either declares coverage or visibly grows the backlog.

A spec with a coverage block whose referents all resolve is COVERED. A spec with no block is in the
BACKLOG (the shrinking backfill list). A block with a dangling referent is a hard failure — that is
the bite the heuristic name-match never had.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKLOG = os.path.join(ROOT, "registry", "spec-coverage-backlog.yaml")


def load(p):
    t = open(p, encoding="utf-8").read()
    return (yaml.safe_load(t) if p.endswith((".yaml", ".yml")) else __import__("json").loads(t)) or {}


def specs():
    """(kind, resource_type, path, coverage-dict-or-None) for every spec and Class."""
    out = []
    for p in glob.glob(os.path.join(ROOT, "registry", "resource-types", "**", "*"), recursive=True):
        if p.endswith((".json", ".yaml", ".yml")):
            d = load(p)
            if d.get("resource_type") and "record_type" not in d:
                # A type's example leg is satisfied by in-spec spec.examples (ADR-055) — but only
                # AUGMENT an existing coverage block, never synthesize one: a spec with examples but
                # no coverage block stays in the backlog (its UCs/flows are still owed) rather than
                # looking partially covered and demanding the other legs early.
                cov = d.get("coverage")
                if cov and (d.get("spec") or {}).get("examples"):
                    cov = {**cov, "examples": (cov.get("examples") or []) + ["spec.examples"]}
                out.append(("type", d["resource_type"], p, cov))
    for p in glob.glob(os.path.join(ROOT, "registry", "classes", "*.yaml")):
        d = load(p)
        if d.get("record_type") == "class":
            out.append(("class", d["resource_type"], p, d.get("coverage")))
    return sorted(set((k, rt, pa, __import__("json").dumps(c, sort_keys=True) if c else None) for k, rt, pa, c in out))


def _uc_handles():
    hs = set()
    for p in glob.glob(os.path.join(ROOT, "use-cases", "**", "*"), recursive=True):
        if p.endswith((".yaml", ".yml")):
            h = load(p).get("handle")
            if h:
                hs.add(h)
    return hs


def _docs(p):
    """All YAML/JSON documents in a file (instance files may be multi-doc `---` streams)."""
    t = open(p, encoding="utf-8").read()
    if p.endswith(".json"):
        return [__import__("json").loads(t) or {}]
    return [d for d in yaml.safe_load_all(t) if isinstance(d, dict)]


def _instance_handles():
    hs = set()
    for p in glob.glob(os.path.join(ROOT, "registry", "instances", "**", "*"), recursive=True):
        if p.endswith((".yaml", ".yml", ".json")):
            for d in _docs(p):
                for k in ("handle", "$id", "uuid"):
                    if d.get(k):
                        hs.add(d[k])
    return hs


def _resolve(referent, kind, uc_handles, inst_handles):
    """A coverage referent resolves if it names an existing UC handle / instance handle, or a file
    on disk (path relative to repo root)."""
    if os.path.isfile(os.path.join(ROOT, referent)):
        return True
    if kind == "use_cases":
        return referent in uc_handles
    if kind == "examples":
        # `spec.examples` is the in-spec worked example (ADR-055); anything else names an instance.
        return referent == "spec.examples" or referent in inst_handles
    if kind == "flows":
        # a flow given by bare name resolves to docs/flows/<name>.md
        return os.path.isfile(os.path.join(ROOT, "docs", "flows", os.path.basename(referent)))
    return False


def main():
    mode_check = "--check" in sys.argv
    uc, inst = _uc_handles(), _instance_handles()
    covered, backlog, dangling = [], [], []
    print(f"{'spec':42} coverage")
    for kind, rt, path, cov_json in specs():
        cov = __import__("json").loads(cov_json) if cov_json else None
        if not cov:
            backlog.append(rt)
            print(f"{rt:42} · backlog (no coverage block)")
            continue
        need = ["use_cases", "flows"] + (["examples"] if kind == "type" else [])
        bad = []
        for field in need:
            for ref in cov.get(field) or []:
                if not _resolve(ref, field, uc, inst):
                    bad.append(f"{field}:{ref}")
            if not (cov.get(field) or []):
                bad.append(f"{field}:(empty)")
        if bad:
            dangling.append((rt, bad))
            print(f"{rt:42} ✗ DANGLING {', '.join(bad)}")
        else:
            covered.append(rt)
            print(f"{rt:42} ✓ UC+example+flow")
    n = len(covered) + len(backlog) + len(dangling)
    print(f"\n{len(covered)}/{n} covered · {len(backlog)} in backlog · {len(dangling)} dangling")

    if not mode_check:
        return 0
    # --check: declared coverage must resolve, and the backlog file must match the tree.
    rc = 0
    for rt, bad in dangling:
        print(f"FAIL [COV-001] {rt}: coverage referent does not resolve — {', '.join(bad)}")
        rc = 1
    want = sorted(set(backlog))
    have = (load(BACKLOG) or {}).get("uncovered", []) if os.path.isfile(BACKLOG) else None
    if have != want:
        with open(BACKLOG, "w", encoding="utf-8") as fh:
            yaml.safe_dump({"uncovered": want}, fh, default_flow_style=False, sort_keys=False)
        if have is None:
            print(f"[COV-002] wrote {os.path.relpath(BACKLOG, ROOT)} ({len(want)} spec(s) awaiting coverage)")
        else:
            print(f"FAIL [COV-002] spec-coverage-backlog.yaml was stale — regenerated. "
                  f"A new spec must declare a `coverage:` block or explicitly join the backlog (commit the update).")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main())
