#!/usr/bin/env python3
"""Pin manifest — the digest referrer for every published (identity, version) (ADR-051).

Artifacts never carry their own digest (the OCI referrer rule); this generated manifest is
where digests live. Each row binds a qualified handle + published version to the sha256 of
the document's RFC 8785 (JCS) canonical form, so a `thing@version` pin resolves to exact
bytes and a `thing@sha256:<hex>` pin verifies them. The manifest is **append-only**: a
(handle, version) row, once written, is never rewritten or removed — regeneration refuses a
recomputed digest that disagrees with a recorded row, which makes this file the mechanical
republication detector behind the publish law (identity-integrity gate rule R2). Rows are
keyed by handle, not path, so they survive file renames; a handle that leaves the tree keeps
its rows (stranded entries are a declared follow-up, never silently dropped).

    python3 registry/tools/generate_pin_manifest.py            # regenerate (append-only)
    python3 registry/tools/generate_pin_manifest.py --check    # CI: current + append-only vs base
    python3 registry/tools/generate_pin_manifest.py --self-test

Canonicalization notes (the two silent-divergence traps, guarded loudly):
- YAML is parsed with a SafeLoader whose implicit *timestamp* resolver is removed — PyYAML
  would otherwise turn `2026-07-25` into a date object and the YAML and JSON serializations
  of one document would digest differently.
- `jcs_bytes()` is a minimal RFC 8785 subset (sorted keys, no insignificant whitespace,
  UTF-8) that REFUSES anything the subset cannot canonicalize provably: non-string or
  non-ASCII keys, NaN/Inf, integers beyond ±2^53, and floats whose serialization would hit
  ECMAScript exponent formatting (repr containing an exponent). A refusal here is a schema
  problem to fix, never something to paper over.
"""
import glob
import hashlib
import json
import math
import os
import subprocess
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(ROOT, "registry", "pin-manifest.json")
BASE = os.environ.get("PIN_MANIFEST_BASE", "origin/main")


class NoTimestampSafeLoader(yaml.SafeLoader):
    """SafeLoader minus the implicit timestamp resolver: YAML dates stay strings, so the
    YAML and JSON serializations of one document canonicalize identically."""


NoTimestampSafeLoader.yaml_implicit_resolvers = {
    ch: [(tag, regexp) for tag, regexp in resolvers if tag != "tag:yaml.org,2002:timestamp"]
    for ch, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}


def parse_documents(text, path):
    """All mapping documents in a file (JSON = one; YAML may be a `---` stream)."""
    if path.endswith(".json"):
        docs = [json.loads(text)]
    else:
        docs = list(yaml.load_all(text, Loader=NoTimestampSafeLoader))
    return [d for d in docs if isinstance(d, dict)]


class JCSError(ValueError):
    pass


def _jcs_string(s):
    return json.dumps(s, ensure_ascii=False)


def _jcs_number(x):
    if isinstance(x, bool):  # bool is int in Python; handled by caller
        raise JCSError("bool reached number serializer")
    if isinstance(x, int):
        if abs(x) > 2**53:
            raise JCSError(f"integer {x} outside ±2^53 (I-JSON safe range)")
        return str(x)
    if math.isnan(x) or math.isinf(x):
        raise JCSError("NaN/Infinity cannot be canonicalized")
    if x == int(x) and abs(x) <= 2**53:
        return str(int(x))  # ECMAScript String(1.0) == "1"
    r = repr(x)
    if "e" in r or "E" in r:
        raise JCSError(f"unsafe float {r}: exponent-form serialization diverges between "
                       f"canonicalizers — restate the value (string, or scaled integer)")
    return r


def _jcs(value, out):
    if value is None:
        out.append("null")
    elif value is True:
        out.append("true")
    elif value is False:
        out.append("false")
    elif isinstance(value, str):
        out.append(_jcs_string(value))
    elif isinstance(value, (int, float)):
        out.append(_jcs_number(value))
    elif isinstance(value, (list, tuple)):
        out.append("[")
        for i, item in enumerate(value):
            if i:
                out.append(",")
            _jcs(item, out)
        out.append("]")
    elif isinstance(value, dict):
        for k in value:
            if not isinstance(k, str):
                raise JCSError(f"non-string key {k!r}: JCS objects key on strings only")
            if not k.isascii():
                raise JCSError(f"non-ASCII key {k!r}: this minimal JCS sorts ASCII keys "
                               f"only (full RFC 8785 sorts UTF-16 code units)")
        out.append("{")
        for i, k in enumerate(sorted(value)):
            if i:
                out.append(",")
            out.append(_jcs_string(k))
            out.append(":")
            _jcs(value[k], out)
        out.append("}")
    else:
        raise JCSError(f"unserializable {type(value).__name__} (YAML date/binary leaked "
                       f"through? the loader must keep scalars as strings)")


def jcs_bytes(value):
    """Minimal RFC 8785: sorted keys, no insignificant whitespace, UTF-8 — with loud guards."""
    out = []
    _jcs(value, out)
    return "".join(out).encode("utf-8")


# Fields excluded from the identity digest (ADR-051 §"what identity covers"): a spec's identity is
# its NORMATIVE bytes. Two documentation surfaces are non-normative and excluded, so refreshing them
# never revs a spec's identity or forces a version bump:
#   - `coverage` (top level): the UCs / examples / flows that exercise the spec (ADR-054-adjacent);
#     the corpus grows over the spec's life.
#   - `spec.examples` (JSON Schema `examples` keyword): an ANNOTATION that JSON Schema defines as
#     having no effect on validation (ADR-055) — a worked example illustrates the schema, it is not
#     part of the contract. Refreshing an example must be digest-invariant.
# Stripping an absent field is a no-op, so only specs that carry these are affected, and for them the
# digest equals their pre-annotation published value (no republish, no manifest churn).
IDENTITY_EXCLUDED_FIELDS = ("coverage",)


def _strip_nonnormative(doc):
    if not isinstance(doc, dict):
        return doc
    if not (any(k in doc for k in IDENTITY_EXCLUDED_FIELDS)
            or isinstance(doc.get("spec"), dict) and "examples" in doc["spec"]):
        return doc
    out = {k: v for k, v in doc.items() if k not in IDENTITY_EXCLUDED_FIELDS}
    if isinstance(out.get("spec"), dict) and "examples" in out["spec"]:
        out["spec"] = {k: v for k, v in out["spec"].items() if k != "examples"}
    return out


def digest(doc):
    return "sha256:" + hashlib.sha256(jcs_bytes(_strip_nonnormative(doc))).hexdigest()


def qualified_handle(doc):
    """Kind-qualified stable name, or None if the document is not manifest-tracked.
    Tracked = an identity-bearing registry document with a handle-ish name AND a version."""
    version = doc.get("version")
    if "resource_type" in doc and "uuid" in doc and version:
        return f"type:{doc['resource_type']}", version
    if "record_type" in doc and version:
        name = doc.get("handle") or doc.get("name")
        if name:
            return f"{doc['record_type']}:{name}", version
    provider = doc.get("provider")
    if isinstance(provider, dict) and provider.get("name") and provider.get("version"):
        return f"provider:{provider['name']}", provider["version"]
    if "group_class" in doc and doc.get("handle") and version:
        return f"{doc['group_class']}:{doc['handle']}", version
    if "uuid" in doc and doc.get("handle") and version:
        return f"instance:{doc['handle']}", version
    return None


def tree_rows():
    """(qualified_handle, version, digest, rel_path) for every tracked doc in the tree."""
    rows = []
    paths = sorted(glob.glob(os.path.join(ROOT, "registry", "**", "*.json"), recursive=True) +
                   glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True))
    for p in paths:
        rel = os.path.relpath(p, ROOT)
        if os.path.abspath(p) == os.path.abspath(MANIFEST):
            continue
        # Generated artifacts (registry/generated/*) are compiled from Class sources, not authored —
        # they regenerate deterministically and are gated by generate_class_specs.py --check, so they
        # carry no independent publish-law identity here (a source-Class edit would otherwise trip it).
        if (os.sep + "generated" + os.sep) in (os.sep + rel + os.sep):
            continue
        for doc in parse_documents(open(p, encoding="utf-8").read(), p):
            qh = qualified_handle(doc)
            if qh:
                rows.append((qh[0], qh[1], digest(doc), rel))
    return rows


def _semver_key(v):
    try:
        return tuple(int(p) for p in v.split("."))
    except ValueError:
        return (0, 0, 0)


def build(existing):
    """Fold the tree into an existing manifest, append-only. Returns (manifest, violations)."""
    manifest = {k: {"current": v["current"], "path": v["path"], "versions": dict(v["versions"])}
                for k, v in (existing or {}).items()}
    violations = []
    for handle, version, dig, rel in tree_rows():
        entry = manifest.setdefault(handle, {"current": version, "path": rel, "versions": {}})
        recorded = entry["versions"].get(version)
        if recorded is not None and recorded != dig:
            violations.append(
                f"{handle}@{version}: recorded digest {recorded} != recomputed {dig} — a "
                f"published (identity, version) is immutable; bump the version (publish law)")
            continue
        entry["versions"][version] = dig
        if _semver_key(version) >= _semver_key(entry["current"]):
            entry["current"] = version
            entry["path"] = rel
    return manifest, violations


def load_manifest(text):
    return json.loads(text) if text else {}


def base_manifest():
    r = subprocess.run(["git", "-C", ROOT, "show", f"{BASE}:registry/pin-manifest.json"],
                       capture_output=True, text=True)
    return load_manifest(r.stdout) if r.returncode == 0 else {}


def serialize(manifest):
    return json.dumps(manifest, indent=1, sort_keys=True) + "\n"


def main():
    if "--self-test" in sys.argv:
        return self_test()

    on_disk = {}
    if os.path.exists(MANIFEST):
        on_disk = load_manifest(open(MANIFEST, encoding="utf-8").read())

    if "--check" in sys.argv:
        fails = []
        expected, violations = build(on_disk)
        fails += violations
        if expected != on_disk:
            fails.append("registry/pin-manifest.json is stale — regenerate "
                         "(python3 registry/tools/generate_pin_manifest.py)")
        base = base_manifest()
        for handle, entry in base.items():
            cur = on_disk.get(handle)
            if cur is None:
                fails.append(f"{handle}: entire entry dropped from the manifest — rows are "
                             f"append-only (a handle leaving the tree keeps its rows)")
                continue
            for version, dig in entry["versions"].items():
                if cur["versions"].get(version) != dig:
                    fails.append(f"{handle}@{version}: base row {dig} rewritten or removed — "
                                 f"the manifest is append-only (publish law)")
        for f in fails:
            print("FAIL", f)
        print(f"pin-manifest --check: {sum(len(e['versions']) for e in on_disk.values())} row(s), "
              f"{len(fails)} violation(s) (base: {BASE})")
        return 1 if fails else 0

    manifest, violations = build(on_disk)
    if violations:
        for v in violations:
            print("FAIL", v)
        print("refusing to regenerate over a publish-law violation")
        return 1
    with open(MANIFEST, "w", encoding="utf-8") as fh:
        fh.write(serialize(manifest))
    print(f"wrote registry/pin-manifest.json: {len(manifest)} handle(s), "
          f"{sum(len(e['versions']) for e in manifest.values())} (handle, version) row(s)")
    return 0


def self_test():
    fails = []

    def ok(name, cond):
        print(("  ok   " if cond else "  FAIL ") + name)
        if not cond:
            fails.append(name)

    def refuses(name, value):
        try:
            jcs_bytes(value)
            ok(name, False)
        except JCSError:
            ok(name, True)

    # JCS vectors
    ok("sorted keys, no whitespace",
       jcs_bytes({"b": 1, "a": "x"}) == b'{"a":"x","b":1}')
    ok("nested structures",
       jcs_bytes({"a": [1, {"c": None, "b": True}], "z": False})
       == b'{"a":[1,{"b":true,"c":null}],"z":false}')
    ok("non-ASCII string VALUE allowed, UTF-8 encoded",
       jcs_bytes({"a": "café"}) == '{"a":"café"}'.encode("utf-8"))
    ok("integral float serializes as integer", jcs_bytes([1.0]) == b"[1]")
    ok("plain float kept in shortest form", jcs_bytes([0.5]) == b"[0.5]")
    ok("control chars escaped as JSON", jcs_bytes(["a\nb"]) == b'["a\\nb"]')

    # loud guards
    refuses("non-string key refused", {1: 2})
    refuses("non-ASCII key refused", {"café": 1})
    refuses("NaN refused", float("nan"))
    refuses("Infinity refused", float("inf"))
    refuses("integer beyond 2^53 refused", 2**53 + 1)
    refuses("exponent-form float refused", 1e-07)

    # YAML and JSON serializations of one document digest identically —
    # incl. a date-shaped scalar (the removed timestamp resolver)
    y = parse_documents("a: 2026-07-25\nb: 1\nt: '2026-07-25T10:00:00Z'\n", "x.yaml")[0]
    j = parse_documents('{"a": "2026-07-25", "b": 1, "t": "2026-07-25T10:00:00Z"}', "x.json")[0]
    ok("YAML == JSON digest (timestamp resolver removed)", digest(y) == digest(j))

    # append-only law
    existing = {"type:Example.Thing": {"current": "1.0.0", "path": "registry/x.json",
                                       "versions": {"1.0.0": "sha256:" + "0" * 64}}}
    rebuilt, violations = build(existing)
    ok("append-only: absent-from-tree rows survive regeneration",
       not violations and rebuilt["type:Example.Thing"]["versions"]["1.0.0"] == "sha256:" + "0" * 64)

    print(f"\npin-manifest self-test: {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
