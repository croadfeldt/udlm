#!/usr/bin/env python3
"""A provider registration that changes what it supports declares a sufficient bump (REG-018).

A provider's bound class versions are its statement of support (VERSIONING.md, "Versions carry down
the class tree"). The registration is itself a versioned contract (ADR-045 Decision 8), so changing
a binding moves the registration's own version:

  a binding added, or its version raised   -> at least a MINOR  (the provider honours more)
  a binding removed, or its version lowered -> a MAJOR           (the provider withdraws support)

While the registration is still 0.x a MAJOR may ship as a MINOR, the same pre-1.0 floor compat-check
applies to classes. Registrations are matched to the base ref by uuid. One that is new has nothing
to compare with and is skipped.

Usage: check_registration_bumps.py [base-ref]   (default origin/main; env UDLM_BASE_REF)
       check_registration_bumps.py --self-test
Exit 0 = every changed registration declares enough; 1 = at least one does not; 2 = base unreadable.
"""
import glob
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RANK = {None: 0, "revision": 1, "minor": 2, "major": 3}


def parts(version):
    return [int(x) for x in str(version).split(".")]


def declared(old, new):
    o, n = parts(old), parts(new)
    if n <= o:
        return None
    if n[0] != o[0]:
        return "major"
    if n[1] != o[1]:
        return "minor"
    return "revision"


def bindings(doc):
    profile = ((doc.get("capability_profiles") or {}).get("realize_resources") or {})
    return {b["fqn"]: b["version"] for b in profile.get("resource_types") or []
            if isinstance(b, dict) and "fqn" in b and "version" in b}


def required(old_doc, new_doc):
    """(level, reasons) the change to the bindings asks for; level None when they did not change."""
    old, new = bindings(old_doc), bindings(new_doc)
    major, minor = [], []
    for fqn, version in old.items():
        if fqn not in new:
            major.append(f"dropped {fqn}")
        elif parts(new[fqn]) < parts(version):
            major.append(f"lowered {fqn} {version} -> {new[fqn]}")
        elif parts(new[fqn]) > parts(version):
            minor.append(f"raised {fqn} {version} -> {new[fqn]}")
    minor += [f"added {fqn} {new[fqn]}" for fqn in new if fqn not in old]
    if major:
        return "major", major + minor
    if minor:
        return "minor", minor
    return None, []


def judge(old_doc, new_doc):
    """None when the change is declared sufficiently, else the sentence that says why not."""
    level, reasons = required(old_doc, new_doc)
    if level is None:
        return None
    enforced = "minor" if (level == "major" and parts(new_doc["version"])[0] == 0) else level
    got = declared(old_doc["version"], new_doc["version"])
    if RANK[got] >= RANK[enforced]:
        return None
    return (f"REG-018 {new_doc.get('handle')}: the bindings changed ({'; '.join(reasons)}), which needs at "
            f"least a {enforced} bump; the registration went {old_doc['version']} -> {new_doc['version']}")


def registrations(text):
    for doc in yaml.safe_load_all(text):
        if isinstance(doc, dict) and doc.get("record_type") == "provider_registration" and doc.get("uuid"):
            yield doc


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def self_test():
    def reg(version, **b):
        return {"handle": "t", "version": version, "capability_profiles": {"realize_resources": {
            "resource_types": [{"fqn": k.replace("_", "."), "version": v} for k, v in b.items()]}}}
    cases = [
        ("raise needs a minor", reg("1.0.0", A="1.0.0"), reg("1.0.1", A="1.1.0"), False),
        ("raise with a minor", reg("1.0.0", A="1.0.0"), reg("1.1.0", A="1.1.0"), True),
        ("add with a minor", reg("1.0.0", A="1.0.0"), reg("1.1.0", A="1.0.0", B="0.1.0"), True),
        ("lower needs a major", reg("1.0.0", A="1.1.0"), reg("1.1.0", A="1.0.0"), False),
        ("lower with a major", reg("1.0.0", A="1.1.0"), reg("2.0.0", A="1.0.0"), True),
        ("drop needs a major", reg("1.0.0", A="1.0.0", B="1.0.0"), reg("1.1.0", A="1.0.0"), False),
        ("0.x drop may be a minor", reg("0.3.0", A="1.0.0", B="1.0.0"), reg("0.4.0", A="1.0.0"), True),
        ("no binding change, no demand", reg("1.0.0", A="1.0.0"), reg("1.0.0", A="1.0.0"), True),
        ("raise with no bump at all", reg("1.0.0", A="1.0.0"), reg("1.0.0", A="1.1.0"), False),
    ]
    bad = [name for name, old, new, ok in cases if (judge(old, new) is None) != ok]
    for name in bad:
        print("FAIL self-test:", name)
    print(f"check_registration_bumps --self-test: {len(cases)} case(s), {len(bad)} failure(s)")
    return 1 if bad else 0


def main():
    if "--self-test" in sys.argv:
        return self_test()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    base = args[0] if args else os.environ.get("UDLM_BASE_REF", "origin/main")
    if git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        print(f"ERROR: base ref {base!r} does not resolve; cannot compare registrations.", file=sys.stderr)
        return 2
    before = {}
    listing = git("ls-tree", "-r", "--name-only", base, "--", "registry/examples")
    for rel in listing.stdout.splitlines():
        if rel.endswith(".yaml") and "/must-reject/" not in rel:
            blob = git("show", f"{base}:{rel}")
            if blob.returncode == 0 and "provider_registration" in blob.stdout:
                for doc in registrations(blob.stdout):
                    before[doc["uuid"]] = doc
    fails, seen = [], 0
    for path in sorted(glob.glob(os.path.join(ROOT, "registry", "examples", "*.yaml"))):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if "provider_registration" not in text:
            continue
        for doc in registrations(text):
            seen += 1
            old = before.get(doc["uuid"])
            verdict = judge(old, doc) if old else None
            if verdict:
                fails.append(verdict)
    for f in fails:
        print("FAIL", f)
    print(f"registration bumps: {seen} registration(s), {len(fails)} under-declared (base: {base})")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
