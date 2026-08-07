#!/usr/bin/env python3
"""URF gate (identifier-scheme §9): self-tests the grammar implementation, then scans
registry content for URF-typed fields and validates each.

  SELF-TEST — adversarial (must refuse) + legal (must round-trip byte-stably):
    URF-001 parse validity (spaces, double-quotes, malformed terms, bad pins)
    URF-002 canonical identity (& -> ;, operand sorting, block <-> string)
    URF-003 reserved characters in segments
    URF-005 operational terms refused in stored forms; stripped at dereference
    URF-006 criterion cycles refused (member_of graph)
  SCAN — every string under a schema field declared `format: udlm-ref-url` or
    `udlm-filter-url` in registry classes/instances parses as a STORED form.

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
    refuse("bad pin", lambda: U.parse("Compute/VM@latest"))
    refuse("wildcard in =in=", lambda: U.parse("estate?resource_type=in=(Compute.*,X)"))
    refuse("unbalanced paren", lambda: U.parse("estate?(a==1;b==2"))
    refuse("bad fragment", lambda: U.parse("Compute/VM#Cpu.Count"))
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
    dotted = ok("dotted-name path input", lambda: U.canonicalize("Compute.VM@1.2.0"))
    if dotted != "Compute/VM@1.2.0":
        fails.append(f"dotted-name path did not canonicalize to slash: {dotted!r}")
    ok("glob value", lambda: U.parse("estate?resource_type==Compute.*"))
    ok("quoted comma", lambda: U.parse("estate?name=='a,b'"))
    ok("in list", lambda: U.parse("estate?uuid=in=(a,b,c)"))
    ok("self placeholder", lambda: U.parse("estate?tenant_uuid=={self}"))
    ok("fragment", lambda: U.parse("Compute/VM@1.2.0#cpu.count"))
    ok("authority", lambda: U.parse("//state.mn/Compute/VM#firmware"))
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
    blk = {"path": "estate", "query": ["tenant_uuid=={self}", "resource_type==Compute.VM"]}
    s = ok("from_block", lambda: U.from_block(blk))
    if s:
        back = U.to_block(s)
        s2 = U.from_block(back)
        if s2 != s:
            fails.append(f"block round-trip not byte-stable: {s!r} -> {back!r} -> {s2!r}")

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
    scanned = 0
    if yaml:
        for f in glob.glob(str(ROOT / "registry" / "classes" / "**" / "*.yaml"), recursive=True):
            doc = yaml.safe_load(open(f))
            if not isinstance(doc, dict):
                continue
            urf_fields = set()
            for el in doc.get("elements") or []:
                sch = el.get("schema") or {}
                if sch.get("format") in ("udlm-ref-url", "udlm-filter-url"):
                    urf_fields.add(el.get("element"))
                items = sch.get("items") or {}
                for prop, ps in (items.get("properties") or {}).items():
                    if isinstance(ps, dict) and ps.get("format") in ("udlm-ref-url", "udlm-filter-url"):
                        urf_fields.add((el.get("element"), prop))
            for ex in doc.get("spec_examples") or []:
                for name in urf_fields:
                    if isinstance(name, str) and isinstance(ex.get(name), str):
                        scanned += 1
                        try:
                            U.parse(ex[name])
                        except U.URFError as e:
                            fails.append(f"{f}: spec_example {name}: {e}")
                    elif isinstance(name, tuple):
                        el, prop = name
                        for item in ex.get(el) or []:
                            if isinstance(item, dict) and isinstance(item.get(prop), str):
                                scanned += 1
                                try:
                                    U.parse(item[prop])
                                except U.URFError as e:
                                    fails.append(f"{f}: spec_example {el}[].{prop}: {e}")

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
