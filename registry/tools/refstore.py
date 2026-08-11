#!/usr/bin/env python3
"""One offline `$ref` store, shared by every tool that validates against a registry schema.

**Why this exists.** Three tools each built their own store and they did not agree.
`fuzz_type_specs.py` and `check_spec_examples.py` globbed every `registry/*.schema.json`;
`validate.py` carried a hardcoded list of four files; `generate_class_specs.py` had no store at all
and fell through to the network. So adding a shared `$defs` entry to `common-elements.schema.json`
and `$ref`-ing it — the mechanism SPEC-DESIGN §33 names for exactly this — resolved cleanly under
two gates, raised `Unresolvable` under a third, and tried a DNS lookup under the fourth.

That is the same defect the vocabulary arm of `check_single_source.py` exists to catch, one layer
down: one rule, four implementations, nothing comparing them. It is fixed the same way — declared
once, imported everywhere.

**Offline is a requirement, not a convenience.** A `$ref` that resolves by fetching
`https://udlm.dev/...` makes CI depend on a name server and on a published artifact matching the
working tree. Every ref must resolve from the checkout.

Each schema is registered under all three forms a `$ref` can arrive as:
  - its **file URI** — what a relative `../../common-elements.schema.json` ref resolves to;
  - its declared **`$id`** — what the absolute form resolves to, and the one that actually hits when
    the referring schema has an `$id` of its own (the base is the referrer's `$id`, not its path);
  - the **versioned** `https://udlm.dev/registry/udlm/0.1/<name>` form, because `catalog-item`'s
    `$id` carries a `/udlm/0.1/` segment its siblings do not, so a relative ref *from* it lands in
    that directory.
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent   # registry/


def build_store():
    """Every `registry/*.schema.json`, keyed every way a `$ref` can name it.

    Globbed rather than listed: a hardcoded list silently omits the next shared schema, which is how
    `validate.py` came to resolve four files and nothing else."""
    store = {}
    for p in sorted(ROOT.glob("*.schema.json")):
        doc = json.loads(p.read_text(encoding="utf-8"))
        store[p.as_uri()] = doc
        if isinstance(doc.get("$id"), str):
            store[doc["$id"]] = doc
        store[f"https://udlm.dev/registry/{p.name}"] = doc
        store[f"https://udlm.dev/registry/udlm/0.1/{p.name}"] = doc
    return store


def vocabulary(name):
    """The members of a shared vocabulary, read from its single home.

    A gate that needs `edge_type` reads it HERE rather than digging it out of whichever schema
    happens to use it. Two gates used to reach into `resource-type-spec.schema.json` and
    `realized-entity.schema.json` by literal path, which meant the vocabulary had two more de-facto
    homes: move the declaration and they break; change one copy and they silently disagree."""
    defs = json.loads((ROOT / "common-elements.schema.json").read_text(encoding="utf-8"))["$defs"]
    if name not in defs or "enum" not in defs[name]:
        raise KeyError(f"{name!r} is not a closed vocabulary in common-elements.schema.json#/$defs")
    return list(defs[name]["enum"])
