#!/usr/bin/env python3
"""URF gate (identifier-scheme §9): self-tests the grammar implementation, then scans
registry content for URF-typed fields and validates each.

  SELF-TEST — adversarial (must refuse) + legal (must round-trip byte-stably):
    URF-001 parse validity (spaces, double-quotes, malformed terms, bad pins)
    URF-002 canonical identity (& -> ;, operand sorting, block <-> string)
    URF-003 reserved characters in segments
    URF-005 operational terms refused in stored forms; stripped at dereference
    URF-006 criterion cycles refused (member_of graph)
    URF-012 `=match=` takes a quoted I-Regexp (RFC 9485) pattern; anything looser is refused
    URF-013 a filter expression carries the query axis alone: no path, operational term or virtual field
  SCAN — every string under a schema field declared `format: udlm-ref-url` or
    `udlm-filter-url` in registry classes/instances parses as a STORED form; one declared
    `udlm-filter-expr` parses as an expression alone (URF-013).

Exit non-zero on any self-test failure or scan violation.
"""
import glob
import importlib.util
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("urf", ROOT / "registry" / "tools" / "urf.py")
U = importlib.util.module_from_spec(spec)
spec.loader.exec_module(U)

try:
    import yaml
except ImportError:
    yaml = None

fails = []


def refuse(label, fn):
    try:
        fn()
        fails.append(f"{label}: ACCEPTED (must refuse)")
    except U.URFError:
        pass


def ok(label, fn):
    try:
        return fn()
    except U.URFError as e:
        fails.append(f"{label}: refused legal input — {e}")


def main():
    # --- adversarial ---
    refuse("space in expression", lambda: U.parse("estate?zone != b"))
    refuse("double quote", lambda: U.parse('estate?name=="a b"'))
    refuse("single = stored", lambda: U.parse("estate?page_size=50"))
    refuse("single = unknown key", lambda: U.parse("estate?zone=b"))
    refuse("reserved char in segment", lambda: U.parse("estate/bad@seg/x?a==1"))
    refuse("bad pin", lambda: U.parse("Machine/VM@latest"))
    refuse("wildcard in =in=", lambda: U.parse("estate?resource_type=in=(Machine.*,X)"))
    refuse("unbalanced paren", lambda: U.parse("estate?(a==1;b==2"))
    refuse("bad fragment", lambda: U.parse("Machine/VM#Cpu.Count"))
    refuse("empty", lambda: U.parse(""))
    # URF-008 — a regex in a value parses as a LITERAL and silently never matches. On a deny
    # criterion that is a fail-OPEN, so it is refused rather than accepted-and-misleading.
    refuse("regex anchors", lambda: U.parse("estate?name==^vm-.*$"))
    refuse("regex char class", lambda: U.parse("estate?name=='^vm-[0-9]{4}$'"))
    refuse("regex alternation", lambda: U.parse("estate?env==(prod|staging)"))
    refuse("regex in quoted value", lambda: U.parse("estate?n=='a|b'"))

    # --- legal + canonicalization ---
    c1 = ok("& alias", lambda: U.canonicalize("estate?b==2&a==1"))
    c2 = ok("; form", lambda: U.canonicalize("estate?a==1;b==2"))
    if c1 != c2:
        fails.append(f"URF-002: '&' and ';' forms differ: {c1!r} vs {c2!r}")
    s1 = ok("sort", lambda: U.canonicalize("estate?b==2;a==1"))
    if s1 != c2:
        fails.append(f"URF-002: operand order changes identity: {s1!r} vs {c2!r}")
    op = ok("operational strip", lambda: U.canonicalize("estate?tenant_uuid==abc&page_size=50"))
    op2 = ok("operational strip 2", lambda: U.canonicalize("estate?tenant_uuid==abc&page_size=99"))
    if op != op2 or "page_size" in (op or ""):
        fails.append(f"URF-005: operational params leaked into identity: {op!r} / {op2!r}")
    live = ok("keep-operational emit", lambda: U.canonicalize("estate?tenant_uuid==abc&page_size=50", keep_operational=True))
    if live and "page_size=50" not in live:
        fails.append(f"operational term lost at live dereference: {live!r}")
    dotted = ok("dotted-name path input", lambda: U.canonicalize("Machine.VM@1.2.0"))
    if dotted != "Machine/VM@1.2.0":
        fails.append(f"dotted-name path did not canonicalize to slash: {dotted!r}")
    ok("glob value", lambda: U.parse("estate?resource_type==Machine.*"))
    ok("quoted comma", lambda: U.parse("estate?name=='a,b'"))
    ok("in list", lambda: U.parse("estate?uuid=in=(a,b,c)"))
    ok("self placeholder", lambda: U.parse("estate?tenant_uuid=={self}"))
    ok("fragment", lambda: U.parse("Machine/VM@1.2.0#cpu.count"))
    ok("authority", lambda: U.parse("//state.mn/Machine/VM#firmware"))
    inl = ok("in-list sort", lambda: U.canonicalize("estate?uuid=in=(c,a,b)"))
    if inl != "estate?uuid=in=(a,b,c)":
        fails.append(f"in-list not sorted: {inl!r}")

    # --- axis splitting is quote-aware: a delimiter inside a quoted value is DATA, not an axis ---
    hashq = ok("'#' inside quoted value", lambda: U.canonicalize("estate?q=='a#b'"))
    if hashq and U.canonicalize(hashq) != hashq:
        fails.append(f"quoted '#' not idempotent: {hashq!r}")

    # --- §9.5 percent-encoding: the canonical form is URL-projectable, stably ---
    enc = ok("space encodes", lambda: U.canonicalize("estate?q=='has space'"))
    if enc:
        illegal = sorted({ch for ch in enc if ch in ' "<>\\^`{|}'})
        if illegal:
            fails.append(f"URF-001: canonical form carries URL-illegal char(s) {illegal}: {enc!r}")
        if U.canonicalize(enc) != enc:
            fails.append(f"canonicalization not idempotent under encoding: {enc!r} -> {U.canonicalize(enc)!r}")
    slf = ok("{self} stays literal", lambda: U.canonicalize("estate?tenant_uuid=={self}"))
    if slf != "estate?tenant_uuid=={self}":
        fails.append(f"§9.5: {{self}} must be literal in canonical form, got {slf!r}")

    # --- block round-trip ---
    blk = {"path": "estate", "query": ["tenant_uuid=={self}", "resource_type==Machine.VM"]}
    s = ok("from_block", lambda: U.from_block(blk))
    if s:
        back = U.to_block(s)
        s2 = U.from_block(back)
        if s2 != s:
            fails.append(f"block round-trip not byte-stable: {s!r} -> {back!r} -> {s2!r}")

    # --- URF-009: `via` traverses ONE declared relationship ---
    # The virtual-field set is CLOSED, so a new member needs arms that prove it discriminates.
    # Accepting `via(x)` is the easy half; the half that matters is refusing a CHAIN, because a
    # chain is how a one-hop traversal quietly becomes a graph query.
    for expr, want_ok, why in [
        ("estate?via(located_in)==abc", True, "one hop over a declared relation"),
        ("estate?via(located_in)via(rack)==x", False, "chained via — URF-009 permits one hop"),
        ("estate?via(a.b)==x", False, "a dotted path smuggled through the traversal"),
        ("estate?via()==x", False, "no relation named"),
        ("estate?member_of==access/groupings/hold", True, "the other virtual field still parses"),
        ("estate?tenant_uuid==abc", True, "an ordinary selector is unaffected"),
    ]:
        try:
            U.canonicalize(expr); got = True
        except Exception:
            got = False
        if got != want_ok:
            fails.append(f"URF-009 {'accepted' if got else 'refused'} {expr!r} — expected the "
                         f"opposite ({why})")

    # --- URF-012: `=match=` takes a single-quoted I-Regexp pattern (RFC 9485) ---
    # The comparator declares the value's language, so a pattern is legal after `=match=` and still
    # refused after `==` (URF-008 above). The refusals that matter are the engine-specific features
    # (lookaround, backreferences, \d) and anchors: I-Regexp reads `^`/`$` as literal characters,
    # and matching is already whole-value, so an anchored pattern would silently never match.
    for expr, want_ok, why in [
        ("estate?host_name=match='db-[0-9]+'", True, "a class and a quantifier"),
        ("estate?body=match='.*(timeout|refused).*'", True, "alternation inside a group"),
        ("estate?body=match='a==b=gt=c;d'", True, "comparator text and `;` inside the quotes are data"),
        ("estate?host_name=match='x{2,}'", True, "an open range quantifier"),
        ("estate?name=match='\\p{Lu}[\\p{Ll}-]*'", True, "Unicode categories, `-` last in a class"),
        ("estate?name=match='\\^lit[$]'", True, "the literal `^` and `$`, spelled as I-Regexp allows"),
        ("estate?name==db-*;host_name=match='db-[0-9]+'", True, "a glob and a pattern in one criterion"),
        ("estate?host_name=match=db-.*", False, "an unquoted pattern"),
        ("estate?host_name=match='^db-.*'", False, "an anchor (a literal in I-Regexp: never matches)"),
        ("estate?host_name=match='db-.*$'", False, "an anchor at the end"),
        ("estate?body=match='(?=x)y'", False, "lookahead"),
        ("estate?body=match='(a)\\1'", False, "a backreference"),
        ("estate?body=match='\\d+'", False, "\\d is not I-Regexp; write [0-9]"),
        ("estate?body=match='x{3,2}'", False, "a range quantifier upside down"),
        ("estate?body=match='[a'", False, "an unterminated class"),
        ("estate?body=match='*a'", False, "a quantifier with nothing to repeat"),
        ("estate?body=foo='a'", False, "an unknown comparator is refused (URF-001), never guessed at"),
    ]:
        try:
            U.canonicalize(expr); got = True
        except U.URFError:
            got = False
        if got != want_ok:
            fails.append(f"URF-012 {'accepted' if got else 'refused'} {expr!r} — expected the "
                         f"opposite ({why})")
    pat = ok("pattern canonical form", lambda: U.canonicalize("estate?body=match='a{2}(b|c)'"))
    if pat:
        if pat != "estate?body=match='a%7B2%7D(b%7Cc)'":
            fails.append(f"URF-012/§9.5: a pattern encodes like any value, braces included: {pat!r}")
        if U.canonicalize(pat) != pat:
            fails.append(f"pattern canonicalization not idempotent: {pat!r}")
    # --- URF-013: a filter expression is the query axis alone, over a subject that is not a record ---
    for expr, want_ok, why in [
        ("severity_number=ge=13;resource.host.name==db-*", True, "comparators and a glob"),
        ("body==*timeout*,body==*refused*", True, "OR of two globs"),
        ("attributes.syslog.facility=in=(kern,auth)", True, "a set over a nested attribute"),
        ("estate?severity_number=ge=13", False, "a path — there is no collection to name"),
        ("member_of==access/groupings/ops", False, "a virtual field reads the estate graph"),
        ("via(host)==x", False, "a traversal reads the estate graph"),
        ("page_size=50", False, "an operational term"),
        ("severity_number=ge=13#body", False, "a fragment"),
    ]:
        try:
            U.parse_expression(expr); got = True
        except U.URFError:
            got = False
        if got != want_ok:
            fails.append(f"URF-013 {'accepted' if got else 'refused'} {expr!r} — expected the "
                         f"opposite ({why})")

    # --- URF-006 cycle refusal (criterion graph walk over member_of) ---
    criteria = {
        "access/groupings/g1": "estate?member_of==access/groupings/g2",
        "access/groupings/g2": "estate?member_of==access/groupings/g1",
    }
    def cycle_check(crits):
        import re as _re
        edges = {k: _re.findall(r"member_of[=!]=+\(?([A-Za-z0-9/_\-,]+)\)?", v) for k, v in crits.items()}
        edges = {k: [t for grp in v for t in grp.split(",")] for k, v in edges.items()}
        seen, stack = set(), set()
        def dfs(n):
            if n in stack:
                raise U.URFError(f"criterion cycle through {n}")
            if n in seen:
                return
            stack.add(n); seen.add(n)
            for t in edges.get(n, []):
                dfs(t)
            stack.discard(n)
        for k in edges:
            dfs(k)
    refuse("criterion cycle", lambda: cycle_check(criteria))
    ok("acyclic criteria", lambda: cycle_check({"g1": "estate?member_of==g2", "g2": "estate?tenant_uuid==x"}))

    # --- scan registry content for declared URF fields ---
    # A URF field can sit anywhere in an element's schema — nested in objects and lists, or behind a
    # `$ref` to a shared definition — so the scan walks the schema to every declared format and then
    # follows the same path through each example.
    scanned = 0
    if yaml:
        import json
        common = json.load(open(ROOT / "registry" / "common-elements.schema.json")).get("$defs", {})
        parsers = {"udlm-ref-url": U.parse, "udlm-filter-url": U.parse,
                   "udlm-filter-expr": U.parse_expression}

        def formats(sch, path=()):
            if not isinstance(sch, dict):
                return
            ref = sch.get("$ref", "")
            if "common-elements.schema.json#/$defs/" in ref:
                sch = {**common.get(ref.rsplit("/", 1)[-1], {}), **{k: v for k, v in sch.items() if k != "$ref"}}
            if sch.get("format") in parsers:
                yield path, sch["format"]
            for prop, ps in (sch.get("properties") or {}).items():
                yield from formats(ps, path + (prop,))
            if isinstance(sch.get("items"), dict):
                yield from formats(sch["items"], path + ("[]",))

        def values(node, path):
            if not path:
                if isinstance(node, str):
                    yield node
                return
            head, rest = path[0], path[1:]
            if head == "[]":
                for item in node if isinstance(node, list) else []:
                    yield from values(item, rest)
            elif isinstance(node, dict) and head in node:
                yield from values(node[head], rest)

        for f in glob.glob(str(ROOT / "registry" / "classes" / "**" / "*.yaml"), recursive=True):
            doc = yaml.safe_load(open(f))
            if not isinstance(doc, dict):
                continue
            fields = []
            for el in doc.get("elements") or []:
                for path, fmt in formats(el.get("schema") or {}):
                    fields.append(((el.get("element"),) + path, fmt))
            for ex in doc.get("spec_examples") or []:
                for path, fmt in fields:
                    for v in values(ex, path):
                        scanned += 1
                        try:
                            parsers[fmt](v)
                        except U.URFError as e:
                            fails.append(f"{f}: spec_example {'.'.join(path)}: {e}")

    print(f"urf: self-test complete; {scanned} stored URF value(s) scanned in registry content")
    if fails:
        print(f"\nFAIL — {len(fails)} finding(s):")
        for x in fails:
            print(f"  {x}")
        return 1
    print("OK — adversarial refused, legal round-trips byte-stable, stored forms clean")
    return 0


if __name__ == "__main__":
    sys.exit(main())
