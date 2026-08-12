#!/usr/bin/env python3
"""No YAML mapping declares the same key twice (DUP-001).

PyYAML resolves a duplicated mapping key by silently keeping the LAST one. Nothing in the toolchain
noticed: the document parses, validates against its schema, digests cleanly, and the earlier value
is simply gone. A `subnet:` key duplicated in `vm.yaml` shipped exactly that way — the first
declaration, which was the considered one, was discarded without a word.

This is a different failure from a schema violation and that is why it needs its own gate: schema
validation runs on the PARSED document, so by the time any validator sees it, the evidence has been
destroyed. It has to be caught at parse time or not at all.

  DUP-001  a mapping in a tracked YAML file declares the same key twice — at any depth, in any
           document of a multi-document stream.

Exit 0 = every mapping key is declared once.
"""
import os
import subprocess
import sys

import yaml

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_PREFIX = ("node_modules/", ".git/")


class DuplicateKeyLoader(yaml.SafeLoader):
    """A SafeLoader that reports duplicate keys instead of silently resolving them.

    Subclassed rather than post-processing the parsed result, because after parsing the duplicate is
    gone — one key remains and nothing records that another was overwritten."""


def _construct_mapping(loader, node, deep=False):
    found = {}
    dupes = []
    for key_node, _value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        try:
            hash(key)
        except TypeError:
            continue
        if key in found:
            dupes.append((key, found[key], key_node.start_mark.line + 1))
        else:
            found[key] = key_node.start_mark.line + 1
    if dupes:
        loader.duplicates.extend(dupes)
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


DuplicateKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def duplicates_in(path):
    """Every duplicated key in the file, as (key, first_line, second_line)."""
    loader = None
    try:
        text = open(path, encoding="utf-8").read()
    except (OSError, UnicodeDecodeError):
        return []
    out = []
    try:
        loader = DuplicateKeyLoader(text)
        loader.duplicates = []
        while loader.check_data():
            loader.get_data()
        out = loader.duplicates
    except yaml.YAMLError:
        return []                      # malformed YAML is another gate\'s finding, not this one
    finally:
        if loader is not None:
            loader.dispose()
    return out


def tracked():
    out = subprocess.run(["git", "ls-files", "*.yaml", "*.yml"],
                         capture_output=True, text=True, check=True, cwd=REPO).stdout
    for p in out.splitlines():
        if not p.startswith(SKIP_PREFIX):
            yield p


def main():
    hits, scanned = [], 0
    for rel in tracked():
        scanned += 1
        for key, first, second in duplicates_in(os.path.join(REPO, rel)):
            hits.append((rel, key, first, second))

    # Self-test: the loader must actually see a duplicate. Without this the gate would report a
    # clean sweep the moment the constructor hook stopped being registered — which is the same
    # silent-pass shape as the bug it exists to catch.
    st = []
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False) as fh:
        fh.write("a: 1\nb:\n  c: 2\n  c: 3\na: 4\n")
        probe = fh.name
    found = {k for k, _f, _s in duplicates_in(probe)}
    os.unlink(probe)
    if found != {"a", "c"}:
        st.append(f"DUP-SELF the loader saw {sorted(found)} in a probe with duplicated `a` and `c` "
                  f"— a nested duplicate or a top-level one is invisible")

    print(f"duplicate yaml keys: {scanned} file(s) scanned")
    for m in st:
        print(f"  FAIL [{m}")
    for rel, key, first, second in hits:
        print(f"  \u2717 DUP-001 {rel}:{second} declares `{key}` again (first at line {first}) — YAML "
              f"keeps the LAST silently, so the earlier value is gone with no error")
    if hits or st:
        return 1
    print("OK — every mapping key is declared once")
    return 0


if __name__ == "__main__":
    sys.exit(main())
