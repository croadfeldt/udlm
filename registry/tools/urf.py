#!/usr/bin/env python3
"""URF — the reference/filter URL (identifier-scheme.md §9).

parse / canonicalize / block↔string round-trip for the one grammar every reference,
filter, criterion, and address uses. The canonical string is the ONLY identity (URF-002);
the block form is authoring ergonomics (§9.4). The accepted RSQL subset is pinned in §9.2 —
this module implements exactly that subset, nothing more, including the I-Regexp (RFC 9485)
check for `=match=` patterns (URF-012).

Public surface:
  parse(url)            -> URF (raises URFError on any violation)
  canonicalize(url)     -> canonical string (parse + emit; operational terms stripped)
  from_block(dict)      -> canonical string (block form -> join -> parse -> emit)
  to_block(url)         -> dict (the inverse projection)
  parse_expression(e)   -> canonical expression for a `udlm-filter-expr` field (URF-013)
"""
import re
from urllib.parse import quote, unquote

OPERATIONAL_NAMES = {"page_size", "page_token", "order_by", "fields", "view"}
RESERVED_SEGMENT_CHARS = set("@?#")
COMPARATORS = ("==", "!=", "=gt=", "=ge=", "=lt=", "=le=", "=in=", "=out=", "=match=")
# A term is <selector><comparator><value>. Selectors never contain `=` or `!`, so the comparator is
# the first `=…=`, `==` or `!=` in the term; reading it by position (not by searching for each
# comparator in turn) keeps a pattern that itself contains `==` or `=gt=` from splitting the term.
_TERM_RE = re.compile(r"^([^=!]*)(=[a-z]+=|==|!=)(.*)$", re.S)
_SEG_RE = re.compile(r"^[A-Za-z0-9._\-{}']+$")
# Regex metacharacters have no meaning in the value of a glob or literal comparator (§9.2): only
# `=match=` takes a pattern. Written after `==` they parse as a LITERAL and compare byte-for-byte —
# a criterion that silently never matches (a deny policy would fail OPEN). Refused, not coerced.
# `{` `}` are excluded here and handled separately: `{self}` is the one blessed RFC 6570 template.
_REGEX_METACHARS = set("^$[]|\\")
_SELF_TEMPLATE_RE = re.compile(r"\{self\}")
# RFC 3986 query charset: pchar / "/" / "?" — everything else percent-encodes (§9.5).
_QUERY_SAFE = set(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "-._~"            # unreserved
    "!$&'()*+,;="     # sub-delims (the RSQL operators live here)
    ":@/?"            # pchar extras
)
_PIN_RE = re.compile(r"^(\d+\.\d+\.\d+|sha256:[a-f0-9]{64})$")
_SELECTOR_RE = re.compile(r"^[a-z0-9_]+(\.[a-z0-9_]+)*$")
# VIRTUAL FIELDS (§9.2, closed set). A selector dot addresses WITHIN one record; crossing to another
# is a named traversal, never a longer dotted name — that is what keeps a cheap field read and an
# authorized dereference visibly different.
#   member_of      membership in a named grouping
#   filed_under    the usage-group terms the record's class is currently filed under (ADR-082)
#   via(<relation>) read a field on the other end of ONE declared relationship (URF-009)
_VIA_RE = re.compile(r"^via\(([a-z][a-z0-9_]*)\)$")
VIRTUAL_FIELDS = ("member_of", "filed_under")
_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9]*(\.[A-Z][A-Za-z0-9]*)*$")


class URFError(ValueError):
    pass


def _split_outside_quotes(s, ch):
    """Partition `s` at the FIRST `ch` that is not inside a single-quoted value.

    The axis delimiters are stripped left-to-right off the whole string, but `'…'` quoting is a
    QUERY-level construct — so a naive partition sees a delimiter inside a quoted value and splits
    there. `estate?q=='a#b'` used to fail as `fragment "b'" is not a dot-path`. Quote-awareness has
    to reach the axis split, not just the expression tokenizer.
    """
    inq = False
    for i, c in enumerate(s):
        if c == "'":
            inq = not inq
        elif c == ch and not inq:
            return s[:i], s[i + 1:]
    return s, None


def _encode_value(v):
    """Percent-encode a value for the canonical URL projection (§9.5: minimal, uppercase hex).

    Only characters outside RFC 3986's query charset are touched, so every RSQL operator and
    delimiter survives verbatim and the common case is byte-identical to its input. `{self}` is
    exempt: §9.5 requires it LITERAL in the canonical form (it is substituted at resolution, and
    encoding it would break identity comparison against an authored criterion).
    """
    def enc(chunk):
        return "".join(c if c in _QUERY_SAFE else "".join(f"%{b:02X}" for b in c.encode("utf-8"))
                       for c in chunk)
    out, pos = [], 0
    for m in _SELF_TEMPLATE_RE.finditer(v):
        out.append(enc(v[pos:m.start()]))
        out.append(m.group(0))
        pos = m.end()
    out.append(enc(v[pos:]))
    return "".join(out)


def _decode_value(v):
    """Inverse of _encode_value. Applied per-value AFTER tokenizing, never before: decoding first
    would let `%3B` inject a term separator that the author never wrote."""
    return unquote(v)


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
    m = _TERM_RE.match(t)
    if m and m.group(2) not in COMPARATORS:
        # A comparator this spec version does not define is refused, never read as something
        # else: a peer older than `=match=` must fail loudly on it (URF-001).
        raise URFError(f"unknown comparator {m.group(2)!r} in {t!r} (URF-001)")
    if m:
        sel, op, val = m.groups()
        if not sel or not val:
            raise URFError(f"malformed term {t!r}")
        if not _SELECTOR_RE.match(sel) and sel not in VIRTUAL_FIELDS and not _VIA_RE.match(sel):
            # `via(a)via(b)` and `via(a.b)` both land here: the first is a chain, which URF-009
            # refuses because a value depending on two other records belongs on the record in
            # between; the second is a dotted path smuggled through the traversal.
            if sel.startswith("via("):
                raise URFError(f"malformed or chained via selector {sel!r} — URF-009 "
                               f"permits exactly one hop, `via(<relation>)`")
            raise URFError(f"selector {sel!r} is not a snake_case dot-path")
        if op == "=match=":
            return (op, sel, _parse_pattern(val, t))
        if " " in t and "'" not in t:
            raise URFError(f"unencoded space in term {t!r} (URF-001)")
        if '"' in t:
            raise URFError(f'double-quote not accepted (single-quote is canonical): {t!r}')
        _refuse_regex(val, t)
        if op in ("=in=", "=out="):
            if not (val.startswith("(") and val.endswith(")")):
                raise URFError(f"{op} takes a parenthesized list: {t!r}")
            members = [x for x in val[1:-1].split(",") if x]
            if not members:
                # An empty set is a criterion that can never match — the same silent-failure
                # class as a regex-as-literal (URF-008). If the intent is "nothing", say so
                # some other way; do not spell it as a filter that quietly returns nothing.
                raise URFError(f"{op} with an empty member list matches nothing: {t!r}")
            if any("*" in x and not x.startswith("'") for x in members):
                raise URFError(f"wildcard not valid inside {op} members (§9.2)")
            return (op, sel, sorted(_decode_value(x) for x in members))
        return (op, sel, _decode_value(val))
    # single '=' -> operational term, only legal at live dereference; caller decides
    if "=" in t:
        k, _, v = t.partition("=")
        if k in OPERATIONAL_NAMES:
            return ("op", k, v)
        raise URFError(f"single '=' is reserved for operational terms; use '==' ({t!r})")
    raise URFError(f"unrecognized term {t!r}")


def _parse_pattern(val, term):
    """The value of `=match=`: a single-quoted I-Regexp pattern (URF-012).

    Returns the decoded pattern without its quotes. Decoding happens after tokenizing, as for every
    value, so a `%3B` in a pattern is a `;` the pattern matches, never a term separator.
    """
    if len(val) < 2 or not (val.startswith("'") and val.endswith("'")):
        raise URFError(f"=match= takes a single-quoted pattern: {term!r} (URF-012)")
    pattern = _decode_value(val[1:-1])
    if "'" in pattern:
        raise URFError(f"a pattern may not contain `'`, which ends the quote; match it with `.`: "
                       f"{term!r} (URF-012)")
    check_iregexp(pattern)
    return pattern


# ---------- I-Regexp (RFC 9485 §3) ----------
# A recursive-descent check against the RFC's ABNF, nothing looser: a pattern outside it is refused,
# never handed to an engine to read its own way. Plus one narrowing (URF-012): an unescaped `^` or
# `$` outside a class. I-Regexp reads both as literal characters and matching is whole-value, so a
# pattern written with anchors would silently never match.
_IRE_META = set("()*+.?[\\]{|}")                          # not NormalChar
_IRE_SINGLE_ESC = set("()*+-.?[\\]^{|}nrt")               # SingleCharEsc
_IRE_CATEGORIES = {
    "L": "lmotu", "M": "cen", "N": "dlo", "P": "cdefios", "Z": "lps", "S": "ckmo", "C": "cfno",
}


def check_iregexp(p):
    """Raise URFError unless `p` is an I-Regexp (RFC 9485) without literal-anchor characters."""
    pos = _IRegexp(p).parse()
    if pos != len(p):
        raise URFError(f"not I-Regexp at offset {pos} of {p!r} (URF-012)")


class _IRegexp:
    def __init__(self, p):
        self.p, self.i = p, 0

    def _err(self, why):
        raise URFError(f"not I-Regexp: {why} at offset {self.i} of {self.p!r} (URF-012)")

    def _peek(self):
        return self.p[self.i] if self.i < len(self.p) else None

    def parse(self):
        self._regexp()
        return self.i

    def _regexp(self):                      # i-regexp = branch *( "|" branch )
        self._branch()
        while self._peek() == "|":
            self.i += 1
            self._branch()

    def _branch(self):                      # branch = *piece
        while self._peek() is not None and self._peek() not in "|)":
            self._piece()

    def _piece(self):                       # piece = atom [ quantifier ]
        self._atom()
        c = self._peek()
        if c in ("*", "+", "?"):
            self.i += 1
        elif c == "{":
            self._range_quantifier()

    def _range_quantifier(self):            # "{" QuantExact [ "," [ QuantExact ] ] "}"
        self.i += 1
        lo = self._digits()
        if lo is None:
            self._err("a range quantifier needs a lower bound")
        hi = lo
        if self._peek() == ",":
            self.i += 1
            hi = self._digits()
        if self._peek() != "}":
            self._err("unterminated range quantifier")
        self.i += 1
        if hi is not None and hi < lo:
            self._err("range quantifier upper bound below its lower bound")

    def _digits(self):
        start = self.i
        while self._peek() is not None and self._peek().isdigit() and self._peek().isascii():
            self.i += 1
        return int(self.p[start:self.i]) if self.i > start else None

    def _atom(self):                        # NormalChar / charClass / "(" i-regexp ")"
        c = self._peek()
        if c == "(":
            self.i += 1
            if self._peek() == "?":
                self._err("groups take no `?` modifier (no lookaround, no named or non-capturing groups)")
            self._regexp()
            if self._peek() != ")":
                self._err("unbalanced `(`")
            self.i += 1
        elif c == ".":
            self.i += 1
        elif c == "[":
            self._class_expr()
        elif c == "\\":
            self._escape(in_class=False)
        elif c in ("^", "$"):
            self._err(f"`{c}` is a literal in I-Regexp and matching is already whole-value; "
                      f"write `\\^` or `[$]` for the character")
        elif c in _IRE_META:
            self._err(f"`{c}` cannot start an atom")
        elif 0xD800 <= ord(c) <= 0xDFFF:
            self._err("surrogate code point")
        else:
            self.i += 1

    def _escape(self, in_class):            # SingleCharEsc / catEsc / complEsc
        self.i += 1
        c = self._peek()
        if c is None:
            self._err("a pattern cannot end in `\\`")
        if c in ("p", "P"):
            self.i += 1
            if self._peek() != "{":
                self._err(f"`\\{c}` needs a {{category}}")
            self.i += 1
            major = self._peek()
            if major not in _IRE_CATEGORIES:
                self._err("unknown Unicode category")
            self.i += 1
            if self._peek() in _IRE_CATEGORIES[major]:
                self.i += 1
            if self._peek() != "}":
                self._err("unknown or unterminated Unicode category")
            self.i += 1
        elif c in _IRE_SINGLE_ESC:
            self.i += 1
        else:
            self._err(f"`\\{c}` is not an I-Regexp escape (no \\d, \\w, \\s, \\b or backreferences)")

    def _class_expr(self):                  # "[" [ "^" ] ( "-" / CCE1 ) *CCE1 [ "-" ] "]"
        self.i += 1
        if self._peek() == "^":
            self.i += 1
        if self._peek() == "-":
            self.i += 1
        elif self._peek() == "]":
            self._err("empty character class")
        else:
            self._cce1()
        while self._peek() is not None and self._peek() != "]":
            if self._peek() == "-":
                self.i += 1
                if self._peek() != "]":
                    self._err("`-` inside a class must be first, last, or a range")
                break
            self._cce1()
        if self._peek() != "]":
            self._err("unterminated character class")
        self.i += 1

    def _cce1(self):                        # ( CCchar [ "-" CCchar ] ) / charClassEsc
        if self._peek() == "\\" and self.i + 1 < len(self.p) and self.p[self.i + 1] in "pP":
            self._escape(in_class=True)
            return
        lo = self._ccchar()
        if self._peek() == "-" and self.i + 1 < len(self.p) and self.p[self.i + 1] != "]":
            self.i += 1
            hi = self._ccchar()
            if lo is not None and hi is not None and hi < lo:
                self._err("class range out of order")

    def _ccchar(self):
        c = self._peek()
        if c is None:
            self._err("unterminated character class")
        if c == "\\":
            nxt = self.p[self.i + 1] if self.i + 1 < len(self.p) else None
            self._escape(in_class=True)
            return {"n": "\n", "r": "\r", "t": "\t"}.get(nxt, nxt)
        if c in "[]-":
            self._err(f"`{c}` must be escaped inside a class")
        if 0xD800 <= ord(c) <= 0xDFFF:
            self._err("surrogate code point")
        self.i += 1
        return c


def _refuse_regex(val, term):
    """A regex written into a value is an author error, not a pattern (URF-008).

    Every comparator but `=match=` matches with `*` glob or literally. So `name=='^vm-[0-9]{4}$'`
    is compared as a literal string and matches nothing — silently. For a deny policy that is a
    fail-OPEN. Refuse at validation rather than let it validate green and mislead.
    """
    v = _SELF_TEMPLATE_RE.sub("", val)          # {self} is the one blessed template (RFC 6570 L1)
    hits = sorted(_REGEX_METACHARS & set(v))
    if "{" in v or "}" in v:
        hits.append("{}")
    if hits:
        raise URFError(
            f"regex metacharacter(s) {hits} in value of {term!r} — the accepted subset matches with "
            f"`*` glob, not regex; a regex here compares as a literal and silently never matches. "
            f"A pattern goes after `=match=` (URF-008, URF-012)")


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
        return f"{sel}{op}({','.join(_encode_value(m) for m in val)})"
    if op == "=match=":
        # A pattern is literal (URF-012): `{` `}` are quantifier braces, never a template, so the
        # whole pattern encodes with no `{self}` exemption.
        enc = "".join(c if c in _QUERY_SAFE else "".join(f"%{b:02X}" for b in c.encode("utf-8"))
                      for c in val)
        return f"{sel}{op}'{enc}'"
    return f"{sel}{op}{_encode_value(val)}"


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
    s, frag = _split_outside_quotes(s, "#")
    if frag is not None and not _SELECTOR_RE.match(frag):
        raise URFError(f"fragment {frag!r} is not a dot-path")
    s, query = _split_outside_quotes(s, "?")
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


def parse_expression(expr):
    """A `udlm-filter-expr` value: §9.2's expression alone, over a subject that is not a record (URF-013).

    No path, pin or fragment (there is no collection to name), no operational term, and no virtual
    field: `member_of`, `filed_under` and `via` read the estate graph, which the subject (a log line,
    say) is not part of. Returns the canonical expression.
    """
    if not isinstance(expr, str) or not expr:
        raise URFError("empty criterion (URF-013)")
    if _split_outside_quotes(expr, "?")[1] is not None or _split_outside_quotes(expr, "#")[1] is not None:
        raise URFError(f"a filter expression has no path, query mark or fragment: {expr!r} (URF-013)")
    ast = _parse_expr(expr)
    terms, operational = _strip_operational(ast)
    if operational:
        raise URFError(f"operational terms {sorted(operational)} are illegal in a filter expression (URF-013)")

    def walk(node):
        kind = node[0]
        if kind in ("and", "or"):
            for n in node[1]:
                walk(n)
        elif kind == "group":
            walk(node[1])
        elif node[1] in VIRTUAL_FIELDS or node[1].startswith("via("):
            raise URFError(f"virtual field {node[1]!r} reads the estate graph; a filter expression's "
                           f"subject is not in it (URF-013)")
    walk(terms)
    return _emit(terms)


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
