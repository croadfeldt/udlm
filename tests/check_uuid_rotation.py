#!/usr/bin/env python3
"""UUID-rotation gate: a definition's uuid IS its revision identity.

Maintainer rule (2026-07-25): if ANYTHING in a uuid-bearing definition document changes, its
uuid changes. The stable identity is the handle (resource_type / handle field); the uuid pins
one immutable revision — exactly the discipline instances already follow ("each version mints a
new UUID; the handle remains stable", provider-lifecycle). Consequences enforced here:

  1. ROTATION  — a document whose content differs from origin/main MUST carry a different uuid.
  2. UNIQUENESS — no uuid appears in more than one document (a rotated uuid is never reused).
  3. NO-OP     — a document whose only change IS the uuid is flagged (rotation without a change
                 is noise; revert or make the intended change).

Scope: every registry/**/*.{json,yaml} document with a top-level `uuid` field. New files are
exempt from rotation (their uuid is new by construction) but join the uniqueness set.
Operational doctrine: registry/VERSIONING.md § "UUID rotation".
"""
import glob
import json
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = os.environ.get("UUID_GATE_BASE", "origin/main")


def load(text, path):
    try:
        return json.loads(text) if path.endswith(".json") else yaml.safe_load(text)
    except Exception:
        return None


def main():
    paths = sorted(glob.glob(os.path.join(ROOT, "registry", "**", "*.json"), recursive=True) +
                   glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True))
    fails, seen = [], {}
    for p in paths:
        rel = os.path.relpath(p, ROOT)
        cur_text = open(p, encoding="utf-8").read()
        cur = load(cur_text, p)
        if not isinstance(cur, dict) or "uuid" not in cur:
            continue
        u = cur["uuid"]
        if u in seen:
            fails.append(f"{rel}: uuid {u[:13]}… duplicates {seen[u]} (uuids are never shared or reused)")
        seen[u] = rel
        r = subprocess.run(["git", "-C", ROOT, "show", f"{BASE}:{rel}"], capture_output=True, text=True)
        if r.returncode != 0:
            continue  # new file — uniqueness already checked
        old_text = r.stdout
        if old_text == cur_text:
            continue
        old = load(old_text, p)
        old_uuid = old.get("uuid") if isinstance(old, dict) else None
        if old_uuid == u:
            fails.append(f"{rel}: content changed vs {BASE} but uuid did not rotate — mint a new uuid "
                         f"(the old uuid stays the immutable identity of the prior revision)")
        else:
            body_old = dict(old); body_old.pop("uuid", None)
            body_new = dict(cur); body_new.pop("uuid", None)
            if body_old == body_new:
                fails.append(f"{rel}: uuid rotated with NO other change — rotation is a consequence of "
                             f"change, never a change itself")
    for f in fails:
        print("FAIL", f)
    print(f"\n{len(seen)} uuid-bearing definition(s) checked vs {BASE}; {len(fails)} violation(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
