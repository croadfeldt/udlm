#!/usr/bin/env python3
"""URF — the reference/filter URL (identifier-scheme.md §9).

parse / canonicalize / block↔string round-trip for the one grammar every reference,
filter, criterion, and address uses. The canonical string is the ONLY identity (URF-002);
the block form is authoring ergonomics (§9.4). The accepted RSQL subset is pinned in §9.2 —
this module implements exactly that subset, nothing more.

Public surface:
  parse(url)            -> URF (raises URFError on any violation)
  canonicalize(url)     -> canonical string (parse + emit; operational terms stripped)
  from_block(dict)      -> canonical string (block form -> join -> parse -> emit)
  to_block(url)         -> dict (the inverse projection)
"""
import re
from urllib.parse import quote, unquote

OPERATIONAL_NAMES = {"page_size", "page_token", "order_by", "fields", "view"}
RESERVED_SEGMENT_CHARS = set("@?#")
COMPARATORS = ("==", "!=", "=gt=", "=ge=", "=lt=", "=le=", "=in=", "=out=")
_SEG_RE = re.compile(r"^[A-Za-z0-9._\-{}']+$")
_PIN_RE = re.compile(r"^(\d+\.\d+\.\d+|sha256:[a-f0-9]{64})$")
_SELECTOR_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(\.[A-Z][A-Za-z0-9]*)*$")


class URFError(ValueError):
    pass


class URF:
    __slots__ = ("authority", "path", "pin", "terms", "operational", "fragment")

    def __init__(self, authority, path, pin, terms, operational, fragment):
        self.authority = authority          # str | None
        self.path = path                    # list[str] segments
        self.pin = pin                      # str | None
        self.terms = terms                  # parsed RSQL AST ('and'/'or'/term tuples)
        self.operational = operational      # dict (live-dereference only)
        self.fragment = fragment            # str | None

    # ---- emit ----
    def canonical(self, keep_operational=False):
        out = ""
        if self.authority:
            out += "//" + self.authority + "/"
        out += "/".join(self.path)
        if self.pin:
            out += "@" + self.pin
        q = _emit(self.terms) if self.terms else ""
        if keep_operational and self.operational:
            ops = "&".join(f"{k}={v}" for k, v in sorted(self.operational.items()))
            q = q + ("&" if q else "") + ops
        if q:
            out += "?" + q
        if self.fragment:
            out += "#" + self.fragment
        return out


# ---------- RSQL expression: parse to AST, emit canonical ----------
def _tokenize_expr(s):
    """Split an expression into terms and connectives, honoring () and '…' quoting."""
    toks, buf, depth, i, inq = [], "", 0, 0, False
    while i < len(s):
        c = s[i]
        if inq:
            buf += c
            if c == "'":
                inq = False
        elif c == "'":
            inq = True
            buf += c
        elif c == "(":
            depth += 1
            buf += c
        elif c == ")":
            depth -= 1
            if depth < 0:
                raise URFError("unbalanced ')'")
            buf += c
        elif c in ";,&" and depth == 0:
            toks.append(buf)
            toks.append(";" if c == "&" else c)   # & is input-alias for AND (§9.2)
            buf = ""
        else:
            buf += c
        i += 1
    if inq:
        raise URFError("unterminated quote")
    if depth != 0:
        raise URFError("unbalanced '('")
    toks.append(buf)
    return toks


def _parse_expr(s):
    """OR (,) binds looser than AND (;): expr := and (',' and)* ; and := term (';' term)*"""
    toks = _tokenize_expr(s)
    or_groups, cur = [], []
    for t in toks:
        if t == ",":
            or_groups.append(cur)
            cur = []
        elif t == ";":
            continue_marker = True
        else:
            cur.append(t)
    or_groups.append(cur)
    ors = []
    for grp in or_groups:
        ands = [_parse_term(t) for t in grp if t != ""]
        if not ands:
            raise URFError("empty term")
        ors.append(("and", ands) if len(ands) > 1 else ands[0])
    return ("or", ors) if len(ors) > 1 else ors[0]


def _parse_term(t):
    t = t.strip()
    if t.startswith("(") and t.endswith(")"):
        return ("group", _parse_expr(t[1:-1]))
    for op in ("=gt=", "=ge=", "=lt=", "=le=", "=in=", "=out=", "==", "!="):
        if op in t:
            sel, _, val = t.partition(op)
            if not sel or not val:
                raise URFError(f"malformed term {t!r}")
            if " " in t and "'" not in t:
                raise URFError(f"unencoded space in term {t!r} (URF-001)")
            if '"' in t:
                raise URFError(f'double-quote not accepted (single-quote is canonical): {t!r}')
            if not _SELECTOR_RE.match(sel):
                raise URFError(f"selector {sel!r} is not a snake_case dot-path")
            if op in ("=in=", "=out="):
                if not (val.startswith("(") and val.endswith(")")):
                    raise URFError(f"{op} takes a parenthesized list: {t!r}")
                members = [m for m in val[1:-1].split(",") if m]
                if any("*" in m and not m.startswith("'") for m in members):
                    raise URFError(f"wildcard not valid inside {op} members (§9.2)")
                return (op, sel, sorted(members))
            return (op, sel, val)
    # single '=' -> operational term, only legal at live dereference; caller decides
    if "=" in t:
        k, _, v = t.partition("=")
        if k in OPERATIONAL_NAMES:
            return ("op", k, v)
        raise URFError(f"single '=' is reserved for operational terms; use '==' ({t!r})")
    raise URFError(f"unrecognized term {t!r}")


def _emit(ast):
    kind = ast[0]
    if kind == "or":
        return ",".join(sorted(_emit(a) for a in ast[1]))
    if kind == "and":
        return ";".join(sorted(_emit(a) for a in ast[1]))
    if kind == "group":
        return "(" + _emit(ast[1]) + ")"
    op, sel, val = ast
    if op in ("=in=", "=out="):
        return f"{sel}{op}({','.join(val)})"
    return f"{sel}{op}{val}"


# ---------- URL-level parse ----------
def parse(url, allow_operational=False):
    if not isinstance(url, str) or not url:
        raise URFError("empty URF")
    s = url
    authority = None
    if s.startswith("//"):
        rest = s[2:]
        authority, _, s = rest.partition("/")
        if not authority or not s:
            raise URFError("authority form requires //authority/path")
    frag = None
    if "#" in s:
        s, _, frag = s.partition("#")
        if not _SELECTOR_RE.match(frag or ""):
            raise URFError(f"fragment {frag!r} is not a dot-path")
    query = None
    if "?" in s:
        s, _, query = s.partition("?")
    pin = None
    if "@" in s:
        s, _, pin = s.partition("@")
        if not _PIN_RE.match(pin or ""):
            raise URFError(f"pin {pin!r} is not version or sha256 form (ADR-051)")
    raw_path = [seg for seg in s.split("/") if seg != ""]
    if not raw_path:
        raise URFError("empty path")
    # dotted-NAME input in the path position canonicalizes to slash form (§9.5)
    path = []
    for seg in raw_path:
        if RESERVED_SEGMENT_CHARS & set(seg):
            raise URFError(f"reserved character in segment {seg!r} (URF-003)")
        if _NAME_RE.match(seg) and "." in seg:
            path.extend(seg.split("."))
        elif _SEG_RE.match(seg):
            path.append(seg)
        else:
            raise URFError(f"illegal path segment {seg!r}")
    terms, operational = None, {}
    if query:
        ast = _parse_expr(query)
        terms, operational = _strip_operational(ast)
        if operational and not allow_operational:
            raise URFError(f"operational terms {sorted(operational)} are illegal in a stored URF (URF-005)")
    return URF(authority, path, pin, terms, operational, frag)


def _strip_operational(ast):
    """Remove ('op', k, v) terms from the AST; return (denotational_ast|None, ops dict)."""
    ops = {}
    def walk(node):
        kind = node[0]
        if kind in ("or", "and"):
            kept = [w for w in (walk(c) for c in node[1]) if w is not None]
            if not kept:
                return None
            return (kind, kept) if len(kept) > 1 else kept[0]
        if kind == "group":
            inner = walk(node[1])
            return ("group", inner) if inner is not None else None
        if kind == "op":
            ops[node[1]] = node[2]
            return None
        return node
    kept = walk(ast)
    return kept, ops


def canonicalize(url, keep_operational=False):
    return parse(url, allow_operational=True).canonical(keep_operational=keep_operational)


# ---------- block form (§9.4) ----------
BLOCK_KEYS = ("authority", "path", "pin", "query", "fragment")


def from_block(block):
    if not isinstance(block, dict) or set(block) - set(BLOCK_KEYS):
        raise URFError(f"block form keys must be within {BLOCK_KEYS}")
    out = ""
    if block.get("authority"):
        out += "//" + block["authority"] + "/"
    out += block.get("path", "")
    if block.get("pin"):
        out += "@" + str(block["pin"])
    q = block.get("query")
    if q:
        if isinstance(q, list):
            q = ";".join(q)
        out += "?" + q
    if block.get("fragment"):
        out += "#" + block["fragment"]
    return canonicalize(out)


def to_block(url):
    u = parse(url, allow_operational=True)
    block = {}
    if u.authority:
        block["authority"] = u.authority
    block["path"] = "/".join(u.path)
    if u.pin:
        block["pin"] = u.pin
    if u.terms:
        canon_q = _emit(u.terms)
        # top-level AND splits into items; anything else stays one item
        if canon_q and ("," not in _top_level(canon_q)):
            block["query"] = _split_top(canon_q)
        else:
            block["query"] = [canon_q]
    if u.fragment:
        block["fragment"] = u.fragment
    return block


def _top_level(s):
    out, depth, inq = "", 0, False
    for c in s:
        if inq:
            inq = c != "'"
        elif c == "'":
            inq = True
        elif c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
        elif depth == 0:
            out += c
    return out


def _split_top(s):
    items, buf, depth, inq = [], "", 0, False
    for c in s:
        if inq:
            buf += c
            inq = c != "'"
        elif c == "'":
            buf += c
            inq = True
        elif c == "(":
            depth += 1
            buf += c
        elif c == ")":
            depth -= 1
            buf += c
        elif c == ";" and depth == 0:
            items.append(buf)
            buf = ""
        else:
            buf += c
    items.append(buf)
    return items
