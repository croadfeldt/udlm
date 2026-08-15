#!/usr/bin/env python3
"""A ✅ cites an artifact that exists (STA-001).

`UDLM-0.1-SCOPE.md` marked two items complete on the strength of an ADR:

    | P4 | Fault domains / SharedFaultDomain | ✅ ADR-010 |

Neither had any machine surface — no schema, no vocabulary, nothing a consumer could resolve. The
tell is visible in the table itself: every other row cites an artifact (`compute.vm 0.3.0`,
`profile.schema.json`, `provider-contract §8.1a`), and those two cited a **decision**.

That distinction is the whole rule. **An ADR says something SHOULD exist.** Citing one as evidence
that it does is a category error, and a scope document is exactly where it does damage — it is what
a reader consults to learn what they can build against.

  STA-001  a ✅ / DONE / SHIPPED / COMPLETE row in a status table cites nothing resolvable: no file
           that exists, no schema property, no `§`-section reference. A row whose only citation is
           an ADR number fails, because a decision is not a surface.

**STA-002 — a corpus claim is checked against the corpus.** The same document said the decision
records were `ADR-001–016` while 46 existed numbered to 067, and that all were `Proposed` while one
was `Accepted`. A range or a count is a fact anyone can verify and nobody had to, so it went stale
silently and the roadmap sent a reader looking for work that was already done.

**Narrow, and here is the line.** A ✅ citing `provider-contract §8.1a` passes — a section reference
is a place a reader can go. A ✅ citing `ADR-010` and nothing else fails. A ✅ citing both passes:
the decision plus its realization is the ideal form, and the ADR is not the problem — being the ONLY
citation is.

`⏳`, `partial`, `pending` and prose rows are not checked at all. Saying what is missing is the
behaviour this encourages, so it must never be the thing that fails.

Exit 0 = every completion claim points at something that exists.
"""
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# A status-table row whose status cell claims completion.
DONE = re.compile(r"^\|(?P<item>[^|]*)\|(?P<mid>(?:[^|]*\|)*?)\s*(?P<status>[^|]*(?:✅|\bDONE\b|"
                  r"\bSHIPPED\b|\bCOMPLETE\b)[^|]*)\|\s*$")
ADR_ONLY = re.compile(r"^[\s✅*_]*(?:DONE|SHIPPED|COMPLETE)?[\s—:-]*"
                      r"(?:(?:UDLM|DCM|DAV)\s+)?ADR-[A-Z]*-?\d{2,3}[\s.*_]*$", re.IGNORECASE)
# Something resolvable: a file, a § section, a version, or ANY backticked identifier — a named
# schema value like `override` is as resolvable as a dotted path, and requiring a dot rejected a
# true claim (P6's `override` policy_type). The gate exists to catch a citation of a DECISION, not
# to prescribe how a real artifact is spelled.
RESOLVABLE = re.compile(r"(`[^`]+`|§\s?[\w.]+|\b\d+\.\d+\.\d+\b)")

SCAN = ("registry/UDLM-0.1-SCOPE.md",)
FILE_TOKEN = re.compile(r"`([A-Za-z0-9_./-]+\.(?:json|yaml|yml|md|py))`")
BASES = ["", "registry", "docs", "registry/taxonomies", "docs/spec"]


def resolves(token):
    return any(os.path.exists(os.path.join(REPO, b, token)) for b in BASES)


def corpus_claims(text, rel):
    """STA-002 — counts and ranges the scope document asserts about the ADR/DR corpus."""
    out = []
    adrs = sorted(int(os.path.basename(p)[4:7]) for p in glob.glob(os.path.join(REPO, "docs", "adr", "ADR-0*.md"))
                  if os.path.basename(p)[4:7].isdigit())
    n_adr = len(glob.glob(os.path.join(REPO, "docs", "adr", "ADR-*.md")))
    n_dr = len(glob.glob(os.path.join(REPO, "docs", "dr", "*.md"))) - len(
        glob.glob(os.path.join(REPO, "docs", "dr", "README.md")))

    for n, line in enumerate(text.splitlines(), 1):
        m = re.search(r"ADR-0*(\d{1,3})\s*[–—-]{1,2}\s*(?:ADR-)?0*(\d{1,3})", line)
        if m and adrs:
            hi = int(m.group(2))
            if hi < max(adrs):
                out.append(f"STA-002 {rel}:{n} — states the range ends at ADR-{hi:03d}; the corpus "
                           f"reaches ADR-{max(adrs):03d}")
        m2 = re.search(r"(\d+)\s+records?\s+in\s+`docs/adr/`", line)
        if m2 and int(m2.group(1)) != n_adr:
            out.append(f"STA-002 {rel}:{n} — states {m2.group(1)} records in docs/adr/; there are {n_adr}")
        m3 = re.search(r"(\d+)\s+in\s+`docs/dr/`", line)
        if m3 and int(m3.group(1)) != n_dr:
            out.append(f"STA-002 {rel}:{n} — states {m3.group(1)} in docs/dr/; there are {n_dr}")
    return out


def main():
    fails, rows = [], 0
    for rel in SCAN:
        path = os.path.join(REPO, rel)
        if not os.path.exists(path):
            print(f"FAILED — {rel} is missing; completion claims cannot be checked")
            return 1
        for n, line in enumerate(open(path, encoding="utf-8").read().splitlines(), 1):
            m = DONE.match(line)
            if not m:
                continue
            rows += 1
            status = m.group("status").strip()
            item = m.group("item").strip()
            if ADR_ONLY.match(status.replace("✅", "").strip()):
                fails.append(f"STA-001 {rel}:{n} — {item!r} is marked complete citing only "
                             f"{status!r}. An ADR is a decision that something SHOULD exist; it is "
                             f"not evidence that it does. Cite the schema, vocabulary or contract "
                             f"section — or say what is missing.")
                continue
            if not RESOLVABLE.search(status):
                fails.append(f"STA-001 {rel}:{n} — {item!r} is marked complete with nothing "
                             f"resolvable in {status!r}: no file, no schema property, no § section")
                continue
            for tok in FILE_TOKEN.findall(status):
                if not resolves(tok):
                    fails.append(f"STA-001 {rel}:{n} — {item!r} cites `{tok}`, which does not "
                                 f"exist. A completion claim pointing at a missing file is worse "
                                 f"than an unmarked row: it reads as checked.")

    for rel in SCAN:
        fails += corpus_claims(open(os.path.join(REPO, rel), encoding="utf-8").read(), rel)

    # Self-test: the arms must fire on the exact rows that shipped, and must NOT fire on the forms
    # that are correct — a gate that flagged an honest ⏳ would teach authors to write ✅ instead.
    st = []
    was_shipped = "| P4 | Fault domains / SharedFaultDomain | ✅ ADR-010 |"
    m = DONE.match(was_shipped)
    if not (m and ADR_ONLY.match(m.group("status").replace("✅", "").strip())):
        st.append("STA-SELF the ADR-only arm does not fire on the row it was built from")
    for ok_row in ("| P2 | Profile schema | ✅ `profile.schema.json` |",
                   "| P6 | Policy override | ✅ `override` policy_type + allOf |",
                   "| P3 | Advertisement | ✅ provider-contract §8.1a `resource_advertisement` |",
                   "| P1 | VM enrichment | ✅ `compute.vm` 0.3.0 |"):
        mm = DONE.match(ok_row)
        if not mm:
            st.append(f"STA-SELF a well-formed done row is not matched at all: {ok_row[:48]}")
        elif ADR_ONLY.match(mm.group("status").replace("✅", "").strip()) or \
                not RESOLVABLE.search(mm.group("status")):
            st.append(f"STA-SELF a correctly cited row is flagged: {ok_row[:48]}")
    if DONE.match("| P4 | Fault domains | ⏳ derivation ruled (ADR-010); no projection yet |"):
        st.append("STA-SELF a ⏳ row is treated as a completion claim — this would penalise saying "
                  "what is missing, which is the behaviour the gate exists to encourage")

    print(f"status claims: {rows} completion row(s) checked against what exists")
    for m2 in st:
        print(f"  FAIL [{m2}")
    for m2 in fails:
        print(f"  ✗ {m2}")
    if fails or st:
        return 1
    print("OK — every completion claim points at something that exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
