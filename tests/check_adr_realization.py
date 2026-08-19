#!/usr/bin/env python3
"""A decision declares where it is realized (ADR-REAL-001/002).

**`Realized by` is a local extension, not part of the standard.** Nygard's ADR model — which MADR
and most variants keep — puts only the DECISION's standing in `Status`: proposed, accepted,
rejected, deprecated, superseded. Implementation is deliberately absent from it, and the normal
sequence is propose → accept → implement.

This repo adds a second, independent axis because it is a SPECIFICATION: the ADR holds the reasoning
and `docs/spec/` + `registry/` hold the artifact, so "where does this decision actually live" is a
question a reader asks constantly and nothing answered.

**IN THIS PHASE THE TWO AXES ARE COUPLED, and that is a deliberate local rule** (maintainer,
2026-08-15). While the base standards are being developed, `Accepted` means IMPLEMENTED:

    Proposed  decided, not built
    Accepted  decided and built — the surface exists
    Rejected  considered and declined

The standard keeps status to agreement alone and would call this a conflation. It is a conflation,
chosen knowingly: the stakeholder set is one maintainer right now, so an "agreed but unbuilt" state
carries no information nobody already has, while "is this real yet" is the question every reader
actually asks. When engineering ratification becomes a live gate (#217), agreement and
implementation separate again and this rule is revisited — that is a decision, not a drift.

  ADR-REAL-005  `Accepted` iff realized. Both directions, because in this phase they are the same
                fact stated twice: a decision is Accepted when it is implemented.

                    Proposed + not yet    decided, not built
                    Accepted + realized   built
                    Accepted + not yet    claims something that does not exist
                    Proposed + realized   built but says otherwise

                The last two are both refused. `Realized by` is written when a record's decision is
                carried — checked by reading the decision against the surface, not inferred from a
                path existing — and `Status` moves with it.

  ADR-REAL-001  every decision record declares `**Realized by:**` — either the surfaces that carry
                it, or an explicit `_not yet_`. Silence is the one unacceptable answer, because
                silence and "nobody checked" are indistinguishable.
  ADR-REAL-002  every path a record names exists. A realization claim pointing at a missing file is
                worse than `_not yet_`: it reads as done.
  ADR-REAL-004  an `Accepted` record is not edited in place. `CONTRIBUTING.md` has always said
                decision records are immutable once Accepted — superseded, not edited — and nothing
                enforced it: the identity gate covers records carrying a `record_type`, and a
                markdown ADR carries none. A decision record exists to say what was decided AT THE
                TIME, including where that turned out to be wrong; editing an accepted one destroys
                the only thing it was keeping. Exposure is one record today and grows with every
                ratification, so this lands before the #217 pass rather than after.
                A REFERENCE QUALIFIER IS NOT A REWRITE. Adding `DCM `/`DAV ` in front of an
                `ADR-NNN` already in the text does not change what was decided — it makes an
                existing pointer land on the record it always meant, in a repo where both projects
                number from 1 and a bare number resolves to the wrong decision. Bodies are compared
                with those qualifiers normalised away, so a citation fix passes and any other change
                to the same sentence still fails.

                THE BODY IS WHAT IS IMMUTABLE, not the whole file. The header fields —
                `Status`, `Realized by`, `Superseded by` — record where the decision STANDS and
                where it LIVES, and both move by definition: a status that could never change would
                make the lifecycle unrecordable, and a realization pointer that could never be
                filled in would make an accepted decision permanently unlocatable. What may not
                change is the reasoning: context, decision, alternatives, consequences. This check
                compares everything below the header block.
  ADR-REAL-003  `Status` is one of the five standard values — Proposed, Accepted, Rejected,
                Deprecated, Superseded. A record that says "no" while marked Proposed is mis-stated:
                a rejection IS a decision, and reading it as undecided invites someone to re-open
                what was settled.

**What this does NOT check.** Whether the surface is *adequate* — whether a schema truly carries a
decision is a reading, not a computation, and a gate claiming to answer it would be asserting
judgement it does not have. What it checks is that a surface was named and exists, which is the part
that went wrong nine times in one audit.

Exit 0 = every decision says where it lives, and every surface it names exists.
"""
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# TEMPLATE.md matches ADR-*.md by name and is not a decision — counting it would put a permanent
# `_not yet_` in the burn-down that can never be cleared.
RECORDS = sorted(f for f in glob.glob(os.path.join(REPO, "docs", "adr", "ADR-*.md"))
                 + glob.glob(os.path.join(REPO, "docs", "dr", "DR-*.md"))
                 if os.path.basename(f) != "TEMPLATE.md")

STATUS = re.compile(r"^\*\*Status:\*\*\s*(\w+)", re.M)
# Nygard's set, as carried by MADR. `Superseded` is normally written `Superseded by ADR-N`; the
# first word is what this matches.
STANDARD = {"proposed", "accepted", "rejected", "deprecated", "superseded"}
REALIZED = re.compile(r"^\*\*Realized by:\*\*\s*(.+?)$", re.M)
NOT_YET = re.compile(r"^_not yet_", re.I)
# A decision whose OUTCOME is that nothing is modelled is realized — by the absence, and by whatever
# holds the absence in place. Distinct from `_not yet_`, which is work outstanding.
BY_DESIGN = re.compile(r"^_by design_", re.I)
# A path inside a code span. `$defs` fragments and § sections ride along on a file that must exist.
PATH = re.compile(r"`([A-Za-z0-9_./-]+\.(?:json|yaml|yml|md|py))(?:#[^`]*)?`")


BASE = os.environ.get("UDLM_BASE_REF", "origin/main")
# The header block: the `**Field:** value` lines between the title and the first `##`. These record
# standing and location and are expected to move; everything after is the reasoning.
HEADER_LINE = re.compile(r"^\*\*[A-Za-z][A-Za-z /—-]{2,30}:\*\*")


# An owner qualifier on a citation. Normalised out before comparing bodies: adding one corrects
# where a reference points, it does not change the decision.
QUALIFIER = re.compile(r"\b(?:DCM|DAV)\s+(ADR-)")


def _body(text):
    """A record's reasoning, normalized — header fields, citation qualifiers and whitespace
    removed."""
    lines, seen_section = [], False
    for ln in text.splitlines():
        if ln.startswith("## "):
            seen_section = True
        if not seen_section and (HEADER_LINE.match(ln) or ln.startswith("# ")):
            continue
        lines.append(ln)
    return re.sub(r"\s+", " ", QUALIFIER.sub(r"\1", "\n".join(lines))).strip()


def accepted_edits():
    """ADR-REAL-004 — an Accepted record whose body changed against the base ref."""
    out = []
    r = subprocess.run(["git", "-C", REPO, "diff", "--name-only", BASE, "--", "docs/adr", "docs/dr"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        return out                       # no base ref available; the CI step reports that itself
    for rel in r.stdout.split():
        base = os.path.basename(rel)
        if not rel.endswith(".md") or base in ("README.md", "TEMPLATE.md"):
            continue
        old = subprocess.run(["git", "-C", REPO, "show", f"{BASE}:{rel}"],
                             capture_output=True, text=True)
        if old.returncode != 0:
            continue                     # a new record, not an edit
        sm = STATUS.search(old.stdout)
        if not sm or sm.group(1).lower() != "accepted":
            continue
        try:
            new = open(os.path.join(REPO, rel), encoding="utf-8").read()
        except OSError:
            continue
        if _body(new) != _body(old.stdout):
            out.append(f"ADR-REAL-004 {rel}: an Accepted record was edited. A change to an agreed "
                       f"decision is a NEW record that supersedes this one — the record exists to "
                       f"say what was decided at the time, including where that turned out wrong")
    return out


def main():
    fails = []
    quad = {}

    for path in RECORDS:
        rel = os.path.relpath(path, REPO)
        text = open(path, encoding="utf-8").read()
        sm, rm = STATUS.search(text), REALIZED.search(text)

        if not rm:
            fails.append(f"ADR-REAL-001 {rel}: no `**Realized by:**`. Name the surfaces that carry "
                         f"this decision, or say `_not yet_` — silence and 'nobody checked' are "
                         f"indistinguishable")
            continue

        claim = rm.group(1).strip()
        status = (sm.group(1) if sm else "Proposed").lower()
        realized = not NOT_YET.match(claim)
        by_design = bool(BY_DESIGN.match(claim))
        if status not in STANDARD:
            fails.append(f"ADR-REAL-003 {rel}: Status {status!r} is not one of the five standard "
                         f"values ({', '.join(sorted(STANDARD))})")
        key = f"{status}/{'by design' if by_design else 'realized' if realized else 'not yet'}"
        quad[key] = quad.get(key, 0) + 1

        # ADR-REAL-005 — the two are one fact in this phase.
        if realized and status == "proposed":
            fails.append(f"ADR-REAL-005 {rel}: realized but still Proposed. `Realized by` says the "
                         f"decision is carried, so the status says so too")
        if not realized and status == "accepted":
            fails.append(f"ADR-REAL-005 {rel}: Accepted with no realization. In this phase Accepted "
                         f"means implemented, so this claims something that does not exist")

        if realized and not by_design:
            for p in PATH.findall(claim):
                if not os.path.exists(os.path.join(REPO, p)):
                    fails.append(f"ADR-REAL-002 {rel}: names `{p}`, which does not exist. A "
                                 f"realization claim pointing at a missing file is worse than "
                                 f"`_not yet_` — it reads as done")
            if not PATH.search(claim):
                fails.append(f"ADR-REAL-002 {rel}: claims realization but names no file — "
                             f"{claim[:70]!r}")

    fails += accepted_edits()

    # Self-test: each arm on a planted case, and the corpus must have loaded.
    st = []
    if not RECORDS:
        st.append("REAL-SELF no decision records found — every arm would pass vacuously")
    if NOT_YET.match("`registry/x.json`"):
        st.append("REAL-SELF a real claim is read as `_not yet_`")
    if not NOT_YET.match("_not yet_ — decided, no machine surface."):
        st.append("REAL-SELF the `_not yet_` marker is not recognised, so honest records would fail")
    if not PATH.findall("`registry/common-elements.schema.json#/$defs/TimeSync`"):
        st.append("REAL-SELF a path carrying a `#` fragment is not extracted")
    if "rejected" not in STANDARD or "invented" in STANDARD:
        st.append("REAL-SELF the standard status set is wrong")
    if not (BY_DESIGN.match("_by design_ — nothing is modelled")
            and NOT_YET.match("_not yet_ — decided, no machine surface.")):
        st.append("REAL-SELF the two markers are not both recognised, so the coupling arm would "
                  "mis-classify every record it reads")

    print(f"adr realization: {len(RECORDS)} decision record(s) — "
          + ", ".join(f"{v} {k}" for k, v in sorted(quad.items())))
    for m in st:
        print(f"  FAIL [{m}")
    for m in fails:
        print(f"  ✗ {m}")
    if fails or st:
        return 1
    print("OK — every decision says where it lives; every named surface exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())
