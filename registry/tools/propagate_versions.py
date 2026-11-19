#!/usr/bin/env python3
"""Carry a class's version bump down to every class beneath it (ADR-045 Decision 1, register row 171).

A descendant's served spec is compiled from its ancestors, so a change to an ancestor changes what the
descendant's version stands for. This tool makes the version say so: when a class's version moved
against the base ref, every class beneath it advances by at least the same level (revision, minor or
major), measured from its own version on the base ref. Each descendant version therefore names exactly
one version of every ancestor, which the compiled spec records in `compilation_provenance.sources`.

Usage:
  propagate_versions.py [base-ref]           write the bumps into the class files, and move the examples
                                             that pinned the old version (base-ref defaults to origin/main)
  propagate_versions.py --check [base-ref]   fail if any descendant is behind; write nothing
  propagate_versions.py --self-test          prove the level arithmetic

A class that is new against the base ref has no earlier version to advance from and is left alone.
Classes are matched to the base ref by uuid, so a moved file is still the same class.
"""
import glob
import os
import re
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CLASSES = os.path.join(ROOT, "registry", "classes")
EXAMPLES = os.path.join(ROOT, "registry", "examples")
RANK = {None: 0, "revision": 1, "minor": 2, "major": 3}
LEVEL = {v: k for k, v in RANK.items()}


def parts(version):
    return [int(x) for x in version.split(".")]


def bump_level(old, new):
    """The level a version moved by, or None when it did not move."""
    if old is None or old == new:
        return None
    o, n = parts(old), parts(new)
    if n[0] != o[0]:
        return "major"
    if n[1] != o[1]:
        return "minor"
    return "revision"


def advance(version, level):
    """The lowest version that is `level` ahead of `version`."""
    major, minor, revision = parts(version)
    if level == "major":
        return f"{major + 1}.0.0"
    if level == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{revision + 1}"


def plan(classes, base_versions):
    """What each class must do, parents before children.

    classes:        {resource_type: {"parent": name-or-None, "version": str, "uuid": str}}
    base_versions:  {uuid: version on the base ref}
    Returns [(resource_type, from_version, to_version, level, because)] for every class that is behind.
    A class already ahead by the needed level is not listed.
    """
    effective = {}          # resource_type -> the level it moved by, once any needed bump is applied
    out = []

    def depth(name):
        seen, d = set(), 0
        while name and name not in seen:
            seen.add(name)
            name = (classes.get(name) or {}).get("parent")
            d += 1
        return d

    for name in sorted(classes, key=lambda n: (depth(n), n)):
        cls = classes[name]
        base = base_versions.get(cls["uuid"])
        own = bump_level(base, cls["version"])
        parent = cls.get("parent")
        need = effective.get(parent) if parent in classes else None
        if base is None or RANK[need] <= RANK[own]:
            effective[name] = own if base is not None else None
            continue
        target = advance(base, need)
        out.append((name, cls["version"], target, need, parent))
        effective[name] = need
    return out


def load_classes():
    classes, paths = {}, {}
    for path in sorted(glob.glob(os.path.join(CLASSES, "**", "*.yaml"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            doc = yaml.safe_load(fh)
        if not isinstance(doc, dict) or doc.get("record_type") != "class":
            continue
        name = doc["resource_type"]
        classes[name] = {"parent": doc.get("parent"), "version": doc["version"], "uuid": doc["uuid"]}
        paths[name] = path
    return classes, paths


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True)


def load_base_versions(base):
    """{uuid: version} for every class on the base ref. Exits 2 when the ref does not resolve: an
    unreadable base would make every class look new and pass the check with nothing checked."""
    if git("rev-parse", "--verify", "--quiet", f"{base}^{{commit}}").returncode != 0:
        print(f"ERROR: base ref {base!r} does not resolve; cannot tell which versions moved.", file=sys.stderr)
        sys.exit(2)
    listing = git("ls-tree", "-r", "--name-only", base, "--", "registry/classes")
    out = {}
    for rel in listing.stdout.splitlines():
        if not rel.endswith(".yaml"):
            continue
        blob = git("show", f"{base}:{rel}")
        if blob.returncode != 0:
            continue
        doc = yaml.safe_load(blob.stdout)
        if isinstance(doc, dict) and doc.get("record_type") == "class" and doc.get("uuid"):
            out[doc["uuid"]] = doc["version"]
    return out


def rewrite_class(path, old, new):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    text, n_version = re.subn(rf"(?m)^version: {re.escape(old)}$", f"version: {new}", text, count=1)
    text, n_id = re.subn(rf"(?m)^(\$id: \S+/){re.escape(old)}$", rf"\g<1>{new}", text, count=1)
    if n_version != 1 or n_id != 1:
        sys.exit(f"ERROR: {os.path.relpath(path, ROOT)}: expected one `version:` and one `$id:` line at {old}")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def repin_examples(name, old, new):
    """Move example records that pinned `name` at `old` to `new`. A record pinned to a version that is
    no longer current is not judged by the example gates, so an example left behind stops proving anything."""
    moved = []
    ref = re.compile(rf"(?m)^(\s*type_ref: \S+/){re.escape(name)}/{re.escape(old)}$")
    pin = re.compile(rf"(?m)^(\s*type_version: ){re.escape(old)}$")
    kind = re.compile(r"(?m)^\s*resource_type: (\S+)$")
    for path in sorted(glob.glob(os.path.join(EXAMPLES, "**", "*.yaml"), recursive=True)):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if not ref.search(text):
            continue
        if set(kind.findall(text)) != {name}:
            print(f"  NOTE {os.path.relpath(path, ROOT)}: holds more than one resource_type; repin it by hand")
            continue
        text = ref.sub(rf"\g<1>{name}/{new}", text)
        text = pin.sub(rf"\g<1>{new}", text)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        moved.append(os.path.relpath(path, ROOT))
    return moved


def self_test():
    cases = [
        ("revision", bump_level("1.2.3", "1.2.4")), ("minor", bump_level("1.2.3", "1.3.0")),
        ("major", bump_level("1.2.3", "2.0.0")), (None, bump_level("1.2.3", "1.2.3")),
        ("1.2.4", advance("1.2.3", "revision")), ("1.3.0", advance("1.2.3", "minor")),
        ("2.0.0", advance("1.2.3", "major")),
    ]
    bad = [c for c in cases if c[0] != c[1]]

    def cls(parent, version, uuid):
        return {"parent": parent, "version": version, "uuid": uuid}

    # A minor on the base reaches the type and the provider class beneath it.
    tree = {"A": cls(None, "1.1.0", "a"), "A.B": cls("A", "2.0.0", "b"), "A.B.C": cls("A.B", "0.3.1", "c")}
    got = plan(tree, {"a": "1.0.0", "b": "2.0.0", "c": "0.3.1"})
    if [(g[0], g[2]) for g in got] != [("A.B", "2.1.0"), ("A.B.C", "0.4.0")]:
        bad.append(("minor reaches every descendant", got))
    # A descendant already ahead by the needed level is left alone; one ahead by less is raised.
    tree = {"A": cls(None, "1.1.0", "a"), "A.B": cls("A", "2.1.0", "b"), "A.D": cls("A", "3.0.1", "d")}
    got = plan(tree, {"a": "1.0.0", "b": "2.0.0", "d": "3.0.0"})
    if [(g[0], g[2]) for g in got] != [("A.D", "3.1.0")]:
        bad.append(("already ahead is left alone", got))
    # A new descendant has nothing to advance from; an unchanged parent asks nothing.
    tree = {"A": cls(None, "1.0.0", "a"), "A.B": cls("A", "0.1.0", "new"), "A.E": cls("A", "1.0.0", "e")}
    if plan(tree, {"a": "1.0.0", "e": "1.0.0"}):
        bad.append(("no move, no bump", None))
    # A major outranks the child's own minor.
    tree = {"A": cls(None, "2.0.0", "a"), "A.B": cls("A", "1.1.0", "b")}
    got = plan(tree, {"a": "1.4.0", "b": "1.0.0"})
    if [(g[0], g[2]) for g in got] != [("A.B", "2.0.0")]:
        bad.append(("major outranks minor", got))
    for b in bad:
        print("FAIL self-test:", b)
    print(f"propagate_versions --self-test: {len(cases) + 4} case(s), {len(bad)} failure(s)")
    return 1 if bad else 0


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--self-test" in sys.argv:
        return self_test()
    base = args[0] if args else os.environ.get("UDLM_BASE_REF", "origin/main")
    classes, paths = load_classes()
    todo = plan(classes, load_base_versions(base))
    if "--check" in sys.argv:
        for name, cur, target, level, parent in todo:
            print(f"FAIL {name}: {parent} moved by a {level} against {base}, so {name} must reach at least "
                  f"{target} (is {cur}). Run scripts/regen.sh.")
        print(f"propagate_versions --check: {len(classes)} class(es), {len(todo)} behind (base: {base})")
        return 1 if todo else 0
    for name, cur, target, level, parent in todo:
        rewrite_class(paths[name], cur, target)
        moved = repin_examples(name, cur, target)
        print(f"  {name} {cur} -> {target} ({level}, follows {parent}); {len(moved)} example(s) repinned")
    print(f"propagate_versions: {len(todo)} class(es) advanced (base: {base})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
