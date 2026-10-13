#!/usr/bin/env python3
"""A YAML example in the normative tier says what it is, and a schema example uses only real fields (DOC-003).

Home: CONTRIBUTING.md (DOC family). Prose that shows fields no schema carries teaches readers to write records
CI rejects; a field audit in October 2026 found 57-66% of example keys in two contracts were a property of no
schema (#632, #634, #635). This gate stops that from growing back.

Every fenced YAML block (```yaml, ```yml or a bare ``` holding `key:` lines) under docs/spec/ begins with one of:

  # schema: <file>[#<json-pointer>]   the block is an instance of that schema. Every key must be a property the
                                      schema (after $ref, allOf/anyOf/oneOf and if/then) allows; values are NOT
                                      checked, so a template with `<uuid>` placeholders is fine.
  # illustrative[: reason]            the block shows a shape or a payload no schema governs (reference-data
                                      contents, a profile value table, a protocol message owned by DCM).

  DOC-003  a schema-marked block uses a key the schema does not allow, or names a schema that does not exist;
           an unmarked block that is not in tests/doc-examples-baseline.txt (new or edited since the baseline).

The baseline holds the content hash of each unmarked block present when the gate landed; it only shrinks. Editing
a baselined block changes its hash, so the edit must also declare the block. `--self-test` proves both arms fire.
"""
import glob, hashlib, json, os, re, sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REG = os.path.join(ROOT, "registry")
BASELINE = os.path.join(ROOT, "tests", "doc-examples-baseline.txt")
SCOPE = os.path.join(ROOT, "docs", "spec")
MARK = re.compile(r"^\s*#\s*(schema|illustrative)\b:?\s*(.*)$")

_SCHEMAS = {}


def schema_file(name):
    name = os.path.basename(name)
    if name not in _SCHEMAS:
        p = os.path.join(REG, name)
        _SCHEMAS[name] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return _SCHEMAS[name]


def pointer(doc, ptr):
    node = doc
    for part in [p for p in ptr.lstrip("/").split("/") if p]:
        node = node[part.replace("~1", "/").replace("~0", "~")]
    return node


def resolve(node, base, seen=0):
    """Follow a $ref to (node, base-file). Local refs resolve within base."""
    while isinstance(node, dict) and "$ref" in node and seen < 30:
        ref = node["$ref"]; seen += 1
        f, _, ptr = ref.partition("#")
        if f:
            base = os.path.basename(f)
        doc = schema_file(base)
        if doc is None:
            return None, base
        node = pointer(doc, ptr) if ptr else doc
    return node, base


def allowed(node, base, depth=0):
    """(set of allowed keys, open?, {key: (child-node, base)}) for an object schema node."""
    node, base = resolve(node, base)
    if not isinstance(node, dict) or depth > 12:
        return set(), True, {}
    keys, kids, closed = set(), {}, node.get("additionalProperties") is False
    for k, v in (node.get("properties") or {}).items():
        keys.add(k); kids[k] = (v, base)
    if node.get("patternProperties") or isinstance(node.get("additionalProperties"), dict):
        closed = False
    for comb in ("allOf", "anyOf", "oneOf"):
        for sub in node.get(comb) or []:
            k2, open2, kids2 = allowed(sub, base, depth + 1)
            keys |= k2
            for k, v in kids2.items():
                kids.setdefault(k, v)
    for branch in ("then", "else"):
        if isinstance(node.get(branch), dict):
            k2, _, kids2 = allowed(node[branch], base, depth + 1)
            keys |= k2
            for k, v in kids2.items():
                kids.setdefault(k, v)
    if "properties" not in node and not any(node.get(c) for c in ("allOf", "anyOf", "oneOf")) and not closed:
        return keys, True, kids
    return keys, not closed, kids


def check_keys(value, node, base, path, out):
    node, base = resolve(node, base)
    if isinstance(value, list):
        item = node.get("items") if isinstance(node, dict) else None
        for i, v in enumerate(value):
            if item is not None:
                check_keys(v, item, base, f"{path}[{i}]", out)
        return
    if not isinstance(value, dict) or not isinstance(node, dict):
        return
    keys, is_open, kids = allowed(node, base)
    for k, v in value.items():
        if k not in keys:
            if not is_open:
                out.append(f"{path + '.' if path else ''}{k}")
            continue
        check_keys(v, kids[k][0], kids[k][1], f"{path + '.' if path else ''}{k}", out)


def blocks(path):
    """(first line number, lines) for every YAML-ish fenced block."""
    out, fence, lang, cur, start = [], False, "", [], 0
    for i, l in enumerate(open(path, encoding="utf-8").read().split("\n"), 1):
        if l.startswith("```"):
            if fence:
                if lang in ("yaml", "yml") or (lang == "" and any(re.match(r"^\s*-?\s*[A-Za-z_][\w-]*:", x) for x in cur)):
                    out.append((start, cur))
                fence = False
            else:
                fence, lang, cur, start = True, l[3:].strip().lower(), [], i + 1
            continue
        if fence:
            cur.append(l)
    return out


def digest(lines):
    return hashlib.sha256("\n".join(x.rstrip() for x in lines).strip().encode()).hexdigest()[:16]


def judge(rel, start, lines, known):
    first = next((x for x in lines if x.strip()), "")
    m = MARK.match(first)
    if not m:
        key = f"{rel} {digest(lines)}"
        return ([] if key in known else
                [f"DOC-003 {rel}:{start}: YAML example declares neither `# schema: <file>` nor `# illustrative`"]), key
    if m.group(1) == "illustrative":
        return [], None
    target = m.group(2).strip().split()[0] if m.group(2).strip() else ""
    f, _, ptr = target.partition("#")
    doc = schema_file(f) if f else None
    if doc is None:
        return [f"DOC-003 {rel}:{start}: names schema {target!r}, which does not exist under registry/"], None
    try:
        node = pointer(doc, ptr) if ptr else doc
        value = yaml.safe_load("\n".join(lines))
    except Exception as e:
        return [f"DOC-003 {rel}:{start}: {target}: block does not parse or pointer does not resolve ({e.__class__.__name__})"], None
    bad = []
    check_keys(value, node, os.path.basename(f), "", bad)
    return [f"DOC-003 {rel}:{start}: `{k}` is not a field of {target}" for k in bad], None


def load_baseline():
    if not os.path.exists(BASELINE):
        return set()
    return {l.strip() for l in open(BASELINE, encoding="utf-8") if l.strip() and not l.startswith("#")}


def main():
    if "--self-test" in sys.argv:
        return self_test()
    known, fails, seen, n, marked = load_baseline(), [], set(), 0, 0
    for p in sorted(glob.glob(os.path.join(SCOPE, "**", "*.md"), recursive=True)):
        rel = os.path.relpath(p, ROOT)
        for start, lines in blocks(p):
            n += 1
            f, key = judge(rel, start, lines, known)
            fails += f
            if key:
                seen.add(key)
            else:
                marked += 1
    if "--write-baseline" in sys.argv:
        head = [l for l in open(BASELINE, encoding="utf-8")] if os.path.exists(BASELINE) else []
        head = [l for l in head if l.startswith("#")] or ["# DOC-003 baseline: unmarked YAML examples in docs/spec/ when the gate landed (file + content hash).\n",
                                                           "# It only shrinks: declare a block `# schema: <file>` or `# illustrative` and its line goes.\n"]
        open(BASELINE, "w", encoding="utf-8").write("".join(head) + "".join(k + "\n" for k in sorted(seen)))
        print(f"baseline written: {len(seen)} unmarked block(s)")
        return 0
    stale = sorted(known - seen)
    for f in fails:
        print("FAIL " + f)
    for s in stale[:10]:
        print(f"STALE-BASELINE {s} — the block was declared, edited or removed; drop the line")
    print(f"\ndoc examples: {n} YAML block(s) in docs/spec/; {marked} declared; {len(seen)} unmarked "
          f"({len(seen & known)} baselined); {len(fails)} finding(s); {len(stale)} stale baseline entr(y/ies)")
    return 1 if fails else 0


def self_test():
    ok = True
    def t(name, cond):
        nonlocal ok
        print(("ok   " if cond else "FAIL ") + "self-test: " + name); ok &= cond
    f, _ = judge("x.md", 1, ["# schema: layer.schema.json", "handle: a", "usage: z"], set())
    t("an unknown field on a closed schema is flagged", any("`usage`" in x for x in f))
    f, _ = judge("x.md", 1, ["# schema: layer.schema.json", "handle: <h>", "fields: {anything: 1}"], set())
    t("a template with placeholders and an open sub-object passes", not f)
    f, _ = judge("x.md", 1, ["# schema: state-record.schema.json", "dependencies:", "  - edge_type: depends_on", "    bogus: 1"], set())
    t("an unknown field inside a referenced array item is flagged", any("bogus" in x for x in f))
    f, _ = judge("x.md", 1, ["# schema: nope.schema.json", "a: 1"], set())
    t("a missing schema is flagged", bool(f))
    f, k = judge("x.md", 1, ["a: 1"], set())
    t("an unmarked block outside the baseline is flagged", bool(f) and bool(k))
    f, k = judge("x.md", 1, ["a: 1"], {f"x.md {digest(['a: 1'])}"})
    t("an unmarked baselined block passes", not f)
    f, _ = judge("x.md", 1, ["# illustrative: a profile table", "anything: goes"], set())
    t("an illustrative block passes", not f)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
