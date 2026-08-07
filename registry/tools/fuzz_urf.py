#!/usr/bin/env python3
"""URF grammar fuzz — systematic coverage of every reference and filter form the grammar admits.

`check_urf.py` is a self-test over hand-picked cases and `check_urf_conformance.py` proves the two
declared conformance tests. Neither exercises the grammar *combinatorially*, so a form nobody
happened to think of has never been parsed. This does: it generates the cross-product of the axes
(§9.1), the accepted RSQL subset (§9.2), and the value forms, then asserts the properties that must
hold for EVERY member — the same shape as `fuzz_type_specs.py` does for type specs.

  ACCEPT   every generated legal form parses.
  STABLE   parse → emit → parse is idempotent (URF-002: canonical form is the identity).
  EQUIV    every equivalent spelling of one filter reaches ONE canonical form — `&`/`;`,
           operand order, in-list order, redundant grouping.
  PROJECT  the block form round-trips verbatim (§9.4: a projection, never a second parse surface).
  URLSAFE  the canonical form carries no URL-illegal byte (§9.5 percent-encoding).
  REJECT   the negative matrix — every URF-00N rule has at least one form that MUST be refused,
           and a rule whose refusals all pass is reported as unexercised rather than silently green.

Deterministic: the matrix is enumerated, not randomly sampled, so a failure is always reproducible
and the count is a coverage number rather than a seed.

Exit 0 = every generated form behaves; 1 = at least one violation.
"""
import itertools
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "registry", "tools"))
import urf as U  # noqa: E402

UUID = "b7a3f0c1-1010-4d20-8a40-0f1e2d3c4b50"

# ---- the axes (§9.1) ----------------------------------------------------------------
AUTHORITIES = ["", "//state.mn/", "//peer.dcm.east/"]
PATHS       = ["Compute/VM", "Compute/VM/OCPVirt", f"uuid/{UUID}", "estate", "estate/web-tier"]
PINS        = ["", "@1.2.0", "@sha256:" + "a" * 64]
FRAGMENTS   = ["", "#cpu", "#cpu.count"]

# ---- the accepted RSQL subset (§9.2) ------------------------------------------------
SCALAR_OPS  = ["==", "!=", "=gt=", "=ge=", "=lt=", "=le="]
SET_OPS     = ["=in=", "=out="]
SELECTORS   = ["tenant_uuid", "resource_type", "labels.concern", "spec.cpu.count"]
VALUES      = [
    "abc",                    # bare unreserved
    "Compute.VM",             # dotted NAME as a value
    "{self}",                 # RFC 6570 level 1
    "'quoted value'",         # single-quote quoting
    "'a,b'",                  # separator inside quotes
    "'has space'",            # forces percent-encoding
    "*",                      # exists idiom
    "pre*",                   # prefix glob
    "*post",                  # suffix glob
    "*mid*",                  # contains glob
    "10.0.90.*",              # dotted + glob
]

fails, unexercised = [], []


def _check_form(url, label):
    """ACCEPT + STABLE + URLSAFE for one generated form."""
    try:
        canon = U.canonicalize(url)
    except U.URFError as e:
        fails.append(f"ACCEPT {label}: legal form refused: {url}  — {e}")
        return None
    try:
        again = U.canonicalize(canon)
    except U.URFError as e:
        fails.append(f"STABLE {label}: canonical form does not re-parse: {canon}  — {e}")
        return None
    if again != canon:
        fails.append(f"STABLE {label}: not idempotent: {url} → {canon} → {again}")
    illegal = sorted({c for c in canon if c in ' "<>\\^`{|}'} - set("{}"))
    if illegal:
        fails.append(f"URLSAFE {label}: canonical form carries URL-illegal {illegal}: {canon}")
    return canon


def gen_axes():
    """Cross-product of authority × path × pin × fragment, with and without a query."""
    n = 0
    for auth, path, pin, frag in itertools.product(AUTHORITIES, PATHS, PINS, FRAGMENTS):
        # a fragment projects a cardinality-1 resolution; skip it on the set-shaped estate root
        if frag and path == "estate":
            continue
        for q in ("", "?tenant_uuid==abc"):
            url = f"{auth}{path}{pin}{q}{frag}"
            _check_form(url, "axes")
            n += 1
    return n


def gen_operators():
    """Every comparator against every selector and every value form."""
    n = 0
    for sel, op, val in itertools.product(SELECTORS, SCALAR_OPS, VALUES):
        # a glob is defined for ==/!= only (§9.2 — the FIQL-native wildcard)
        if "*" in val and op not in ("==", "!="):
            continue
        _check_form(f"estate?{sel}{op}{val}", f"op {op}")
        n += 1
    for sel, op in itertools.product(SELECTORS, SET_OPS):
        for members in ("(a)", "(a,b)", "(a,b,c)", "('x y',b)"):
            _check_form(f"estate?{sel}{op}{members}", f"op {op}")
            n += 1
    return n


def gen_connectives():
    """AND / OR / grouping, to depth 2."""
    n = 0
    exprs = [
        "a==1;b==2",
        "a==1,b==2",
        "a==1;b==2;c==3",
        "a==1,b==2,c==3",
        "(a==1,b==2);c==3",
        "a==1;(b==2,c==3)",
        "(a==1;b==2),(c==3;d==4)",
        "a=in=(x,y);b!=*",
    ]
    for e in exprs:
        _check_form(f"estate?{e}", "connective")
        n += 1
    return n


def gen_equivalence():
    """EQUIV — every equivalent spelling of one filter reaches ONE canonical form."""
    n = 0
    classes = [
        # (label, spellings that MUST be one identity)
        ("and-separator",  ["estate?a==1;b==2", "estate?a==1&b==2"]),
        ("operand-order",  ["estate?a==1;b==2", "estate?b==2;a==1"]),
        ("in-list-order",  ["estate?z=in=(a,b,c)", "estate?z=in=(c,b,a)"]),
        ("or-order",       ["estate?a==1,b==2", "estate?b==2,a==1"]),
        ("operational",    ["estate?a==1", "estate?a==1&page_size=50", "estate?a==1&page_size=99"]),
        ("dotted-path",    ["Compute.VM@1.2.0", "Compute/VM@1.2.0"]),
    ]
    for label, spellings in classes:
        canons = {}
        for s in spellings:
            try:
                canons[s] = U.canonicalize(s)
            except U.URFError as e:
                fails.append(f"EQUIV {label}: spelling refused: {s} — {e}")
        if len(set(canons.values())) > 1:
            fails.append(f"EQUIV {label}: spellings are not one identity: {canons}")
        n += 1
    return n


def gen_projection():
    """PROJECT — block form is a one-way projection that round-trips verbatim (§9.4)."""
    n = 0
    for url in [
        "estate?tenant_uuid=={self}",
        "estate?a==1;b==2",
        f"uuid/{UUID}@1.2.0?reference_data_type==network_zone",
        "//state.mn/Compute/VM@1.2.0#cpu.count",
        "estate?z=in=(a,b);q=='has space'",
    ]:
        try:
            canon = U.canonicalize(url)
            back = U.from_block(U.to_block(canon))
            if back != canon:
                fails.append(f"PROJECT: block round-trip not verbatim: {canon} → {back}")
        except U.URFError as e:
            fails.append(f"PROJECT: refused during round-trip: {url} — {e}")
        n += 1
    return n


# ---- REJECT: every rule must have a form that is actually refused -------------------
NEGATIVE = {
    "URF-001": ["estate?zone != b", 'estate?name=="dq"', "estate?(a==1;b==2", "estate?a==",
                "", "estate?a=='unterminated"],
    "URF-003": ["estate/bad@seg/x?a==1", "estate/bad?seg?a==1", "estate/bad#seg?a==1"],
    "URF-005": ["estate?page_size=50", "estate?zone=b", "estate?unknown_op=1"],
    "URF-008": ["estate?name==^vm", "estate?name==vm$", "estate?name=='[0-9]'",
                "estate?name=='a|b'", "estate?name=='a\\b'", "estate?name=='{4}'"],
    "pin":     ["Compute/VM@latest", "Compute/VM@1.2", "Compute/VM@sha256:short"],
    "set-op":  ["estate?z=in=(Compute.*,X)", "estate?z=in=a", "estate?z=in=()"],
    "fragment": ["Compute/VM#Cpu.Count", "Compute/VM#-bad"],
}


def gen_negative():
    n = 0
    for rule, cases in NEGATIVE.items():
        refused = 0
        for c in cases:
            try:
                U.parse(c)
                fails.append(f"REJECT {rule}: illegal form ACCEPTED: {c!r}")
            except U.URFError:
                refused += 1
            except Exception as e:                       # a crash is not a refusal
                fails.append(f"REJECT {rule}: {c!r} raised {type(e).__name__}, not URFError: {e}")
            n += 1
        if refused == 0:
            unexercised.append(rule)
    return n


def main():
    counts = {
        "axes":        gen_axes(),
        "operators":   gen_operators(),
        "connectives": gen_connectives(),
        "equivalence": gen_equivalence(),
        "projection":  gen_projection(),
        "negative":    gen_negative(),
    }
    total = sum(counts.values())
    print("urf-fuzz: " + " · ".join(f"{k} {v}" for k, v in counts.items()) + f" = {total} form(s)")
    for r in unexercised:
        print(f"  UNEXERCISED: no negative case for {r} was refused — the arm proves nothing")
    if unexercised:
        fails.append(f"{len(unexercised)} rule arm(s) unexercised")
    if fails:
        for m in fails[:40]:
            print(f"  {m}")
        if len(fails) > 40:
            print(f"  … and {len(fails) - 40} more")
        print(f"FAILED — {len(fails)} violation(s) across {total} generated form(s)")
        return 1
    print(f"OK — {total} generated forms: all legal parse and are stable, equivalent spellings are "
          f"one identity, block projections verbatim, illegal forms refused")
    return 0


if __name__ == "__main__":
    sys.exit(main())
