#!/usr/bin/env python3
"""A record's type_ref has one correct form (row 105).

`type_ref` names where the pinned class is served: the `$id` of its served spec,
`https://udlm.dev/registry/udlm/<spec>/<Class>/<version>`, the file a consumer fetches and
validates against. A Provider class has no served spec, so its records give the class `$id`,
`https://udlm.dev/registry/udlm/<spec>/class/<Class>/<version>`. Before row 105 a record could use
either form, so a resolver had to guess.

This gate checks every state record under registry/examples: the form follows from whether the
class is served (registry/generated/), and the version equals `type_version`.
Exit 0 = every type_ref has its one correct form.
"""
import glob
import json
import os
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://udlm.dev/registry/"


def served_classes():
    out = set()
    for f in glob.glob(os.path.join(REPO, "registry", "generated", "*.json")):
        with open(f, encoding="utf-8") as fh:
            out.add(json.load(fh).get("resource_type"))
    return out


def parse(ref, spec):
    """(class, version, served_form) from a type_ref, or None if it is neither form."""
    prefix = f"{BASE}{spec}/"
    if not isinstance(ref, str) or not ref.startswith(prefix):
        return None
    rest = ref[len(prefix):]
    served_form = not rest.startswith("class/")
    parts = (rest if served_form else rest[len("class/"):]).split("/")
    if len(parts) != 2:
        return None
    return parts[0], parts[1], served_form


def check(rec, served):
    """The problem with one record's type_ref, or None. The pinned class is the record's
    resource_type or a class beneath it (a Provider class the entity was placed on)."""
    ref = rec.get("type_ref")
    if ref is None:
        return None
    spec, rt = rec.get("conforms_to", ""), rec.get("resource_type", "")
    got = parse(ref, spec)
    if got is None:
        return f"type_ref {ref!r} is neither {BASE}{spec}/<Class>/<version> nor .../class/<Class>/<version>"
    cls, ver, served_form = got
    if cls != rt and not cls.startswith(rt + "."):
        return f"type_ref names {cls}, which is not {rt} or a class beneath it"
    if ver != rec.get("type_version"):
        return f"type_ref version {ver} is not type_version {rec.get('type_version')}"
    if served_form != (cls in served):
        want = f"{BASE}{spec}/{cls}/{ver}" if cls in served else f"{BASE}{spec}/class/{cls}/{ver}"
        kind = "served spec" if cls in served else "class (a Provider class is not served)"
        return f"type_ref {ref!r} should be the {kind}: {want!r}"
    return None


def self_test():
    served = {"Machine.VM"}
    base = {"conforms_to": "udlm/0.1", "resource_type": "Machine.VM", "type_version": "2.0.0"}
    assert check(dict(base, type_ref=BASE + "udlm/0.1/Machine.VM/2.0.0"), served) is None
    assert check(dict(base, type_ref=BASE + "udlm/0.1/class/Machine.VM/2.0.0"), served)
    assert check(dict(base, type_ref=BASE + "udlm/0.1/Machine.VM/2.1.0"), served)
    placed = dict(base, type_version="1.0.0")
    assert check(dict(placed, type_ref=BASE + "udlm/0.1/class/Machine.VM.X/1.0.0"), served) is None
    assert check(dict(placed, type_ref=BASE + "udlm/0.1/Machine.VM.X/1.0.0"), served)
    assert check(dict(placed, type_ref=BASE + "udlm/0.1/class/Volume.X/1.0.0"), served)


def main():
    self_test()
    served = served_classes()
    bad, n = [], 0
    for f in sorted(glob.glob(os.path.join(REPO, "registry", "examples", "**", "*.yaml"), recursive=True)):
        rel = os.path.relpath(f, REPO)
        if "/must-reject/" in rel:
            continue
        with open(f, encoding="utf-8") as fh:
            for i, rec in enumerate(yaml.safe_load_all(fh)):
                if not isinstance(rec, dict) or not str(rec.get("record_type", "")).endswith("_record"):
                    continue
                n += 1
                problem = check(rec, served)
                if problem:
                    bad.append(f"{rel}#{i}: {problem}")
    for b in bad:
        print(b)
    print(f"type-ref: {n} record(s); {len(bad)} with the wrong form")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
