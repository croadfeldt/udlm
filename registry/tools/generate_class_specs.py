#!/usr/bin/env python3
"""Spec generator (ADR-038 / realization-plan P0): compile each Type Class into the flat
resource-type-spec shape consumers read today, so Classes are the authoring layer and the flat
specs are generated artifacts (never hand-edited). A Type Class's compiled spec is its own elements
plus every ancestor's, merged under `spec.properties`; `required` is the set of non-optional
elements; a `compilation_provenance` block records the source Classes + versions + this generator's
version (ADR-045 §7), so `--check` verifies the committed artifact by faithful recompilation.

Output: registry/generated/<Type>.json — validated against resource-type-spec.schema.json
in-process (so a compiled spec is provably a conformant flat spec). validate.py does NOT rescan the
generated dir (it would double-count identities); this generator is the authority on it.

  generate_class_specs.py            regenerate + write, print a summary
  generate_class_specs.py --check    regenerate in-memory, diff against committed; nonzero on drift
"""
import glob
import json
import os
import sys

import yaml
from jsonschema import Draft202012Validator

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLASSES = os.path.join(ROOT, "classes")
OUT = os.path.join(ROOT, "generated")
GENERATOR_VERSION = "class-spec-gen/1.1.0"
SPEC_VALIDATOR = Draft202012Validator(json.load(open(os.path.join(ROOT, "resource-type-spec.schema.json"))))


def load_classes():
    by_name = {}
    for path in sorted(glob.glob(os.path.join(CLASSES, "*.yaml"))):
        doc = yaml.safe_load(open(path, encoding="utf-8")) or {}
        if doc.get("record_type") == "class":
            by_name[doc["resource_type"]] = doc
    return by_name


def chain(cls, by_name):
    """Ancestors Base→…→self (so a nearer Class's redeclare overrides)."""
    order, seen, cur = [], set(), cls
    stack = []
    while cur and cur["resource_type"] not in seen:
        seen.add(cur["resource_type"])
        stack.append(cur)
        cur = by_name.get(cur.get("parent"))
    return list(reversed(stack))  # Base first


def rel_identity(rel):
    """Relationship identity for the union: declared name wins; else the structural triple."""
    return rel.get("name") or (rel.get("edge_type"), rel.get("target"), rel.get("target_field"))


def compile_spec(cls, by_name):
    """Compile the FULL definition surface (#323): elements → spec, plus outputs (merged,
    nearer overrides), relationships (union by identity, nearest-class-wins on a legal tightening redeclare — consumer-declared), immutable
    (union, sorted), adopts (union, deduplicated by standard+standard_name, pass-through —
    the class item shape IS adopted_standard_ref), and the Type Class's own context verbatim."""
    props, required, sources = {}, [], []
    outputs, rel_seen = {}, {}
    immutable, adopts, adopts_seen = set(), [], set()
    for c in chain(cls, by_name):
        sources.append({"class": c["resource_type"], "version": c["version"], "uuid": c["uuid"]})
        for el in c.get("elements") or []:
            schema = dict(el.get("schema") or {})
            if el.get("values"):  # governed vocabulary — the compiled property notes its kind (ADR-036/PVD-001)
                note = f"Governed vocabulary `{el['values']['reference_data_type']}` (ADR-038 §2); " \
                       "name-selectable but requirements-authoritative (ADR-036). Profile decides bare-vs-reference."
                if note not in schema.get("description", ""):
                    schema["description"] = (schema.get("description", "") + " " + note).strip()
            if el.get("description") and "description" not in schema:
                schema["description"] = el["description"]
            props[el["element"]] = schema           # nearer Class overrides by name
            if not el.get("optional"):
                if el["element"] not in required:
                    required.append(el["element"])
            elif el["element"] in required:
                required.remove(el["element"])       # a descendant may relax? no — Liskov gate forbids; kept defensive
        for name, out in (c.get("outputs") or {}).items():
            outputs[name] = dict(out)                # nearer Class overrides; Liskov gate enforces refine
        for rel in c.get("relationships") or []:
            ident = rel_identity(rel)                # nearest class wins: a legal redeclare TIGHTENS (gate-enforced)
            rel_seen[ident] = dict(rel)
        immutable.update(c.get("immutable") or [])
        for a in c.get("adopts") or []:
            key = (a.get("standard"), a.get("standard_name"))
            if key not in adopts_seen:
                adopts_seen.add(key)
                adopts.append(dict(a))
    spec = {
        "$id": f"https://udlm.dev/registry/udlm/{cls['conforms_to'].split('/')[1]}/{cls['resource_type']}/{cls['version']}",
        "conforms_to": cls["conforms_to"],
        "uuid": cls["uuid"],
        "resource_type": cls["resource_type"],
        "version": cls["version"],
        "family": cls["family"],
        "status": cls["status"],
        "metadata": {**(cls.get("metadata") or {}),
                     "generated": True,
                     "compilation_provenance": {"generator": GENERATOR_VERSION, "sources": sources}},
        "spec": {"type": "object", "additionalProperties": False,   # the closed-spec norm (SPEC-DESIGN §16)
                 "properties": props, **({"required": sorted(required)} if required else {}),
                 **(cls.get("spec_constraints") or {})},               # cross-element constraints, verbatim (type tier)
        "outputs": outputs,
    }
    if immutable:
        spec["immutable"] = sorted(immutable)
    if rel_seen:
        spec["relationships"] = list(rel_seen.values())
    if adopts:
        spec["adopts"] = adopts
    if cls.get("context"):                           # type tier only (schema-enforced); copied verbatim
        spec["context"] = cls["context"]
    if cls.get("spec_examples"):                     # rule-36/ADR-055: the worked example rides the compiled spec
        spec["spec"]["examples"] = cls["spec_examples"]
    _canonicalize_refs(spec)                         # generated specs live at a different depth than authored ones:
    return spec                                      # relative refs are rebased to generated/ depth (../../X -> ../X), staying relative per G8


def _canonicalize_refs(node):
    """Rewrite relative registry-schema $refs to their canonical https://udlm.dev/registry/ URL so the
    compiled artifact is location-independent (authored specs sit two levels deep; generated/ sits one)."""
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            m = __import__("re").match(r"^(?:\.\./)+([A-Za-z0-9.-]+\.schema\.json(?:#.*)?)$", ref)
            if m:
                node["$ref"] = "../" + m.group(1)   # generated/ sits one level below registry/ (G8: relative refs)
        for v in node.values():
            _canonicalize_refs(v)
    elif isinstance(node, list):
        for v in node:
            _canonicalize_refs(v)


def _standard_filename(resource_type):
    """naming-conventions: files are `category.type.<ext>` — lowercase, dot-joined, PascalCase
    segments rendered kebab-case with acronym runs kept whole (VirtualMachine -> virtual-machine,
    IPAddress -> ip-address, OSPatch -> os-patch, VM -> vm)."""
    import re as _re
    def kebab(seg):
        # words (Upper+lower runs) separate with hyphens: VirtualMachine -> virtual-machine,
        # BareMetalHost -> bare-metal-host. An ACRONYM run merges with what follows, no hyphen
        # (maintainer ruling 2026-08-04): OSPatch -> ospatch, VM -> vm, IPAddress -> ipaddress.
        tokens = _re.findall(r"[A-Z]+(?![a-z])|[A-Z][a-z0-9]*|[0-9]+", seg)
        out = ""
        for i, t in enumerate(tokens):
            if i and not tokens[i - 1].isupper():   # previous token was a word -> hyphen boundary
                out += "-"
            out += t.lower()
        return out or seg.lower()
    return ".".join(kebab(seg) for seg in resource_type.split(".")) + ".json"


def main():
    check = "--check" in sys.argv
    by_name = load_classes()
    has_children = {n: any(c.get("parent") == n for c in by_name.values()) for n in by_name}
    # served classes: every type tier + any CHILDLESS base (instantiable directly — the Job
    # pattern; a base with children is abstract-by-use, its types are the served surface)
    types = {n: c for n, c in by_name.items()
             if c.get("class") == "type" or (c.get("class") == "base" and not has_children[n])}
    os.makedirs(OUT, exist_ok=True)
    drift, n = [], 0
    for name, cls in sorted(types.items()):
        n += 1
        spec = compile_spec(cls, by_name)
        errs = sorted(SPEC_VALIDATOR.iter_errors(spec), key=lambda e: list(e.path))
        if errs:
            print(f"FAIL [GEN-002] {name}: compiled spec is not a conformant resource-type-spec:")
            for e in errs[:5]:
                print("   - " + "/".join(str(p) for p in e.path) + ": " + e.message)
            drift.append(name); continue
        text = json.dumps(spec, indent=2, ensure_ascii=False) + "\n"
        out = os.path.join(OUT, _standard_filename(name))
        if check:
            existing = open(out, encoding="utf-8").read() if os.path.exists(out) else ""
            if existing != text:
                print(f"FAIL [GEN-001] {name}: generated spec is stale — regenerate (registry/generated/)")
                drift.append(name)
            else:
                print(f"ok (fresh)  {name} → {os.path.relpath(out, ROOT)} ({len(spec['spec']['properties'])} props)")
        else:
            open(out, "w", encoding="utf-8").write(text)
            print(f"wrote  {name} → {os.path.relpath(out, ROOT)} ({len(spec['spec']['properties'])} props)")
    print(f"{n} Type Class(es) compiled, {len(drift)} issue(s)")
    return 1 if drift else 0


if __name__ == "__main__":
    sys.exit(main())
