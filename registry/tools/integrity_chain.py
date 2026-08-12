#!/usr/bin/env python3
"""The resource chain — compute and verify a record's `integrity.head` (ADR-059 Decision 2).

The head is SHA-256 over the RFC 8785 (JCS) canonical form of the record **minus `integrity`
itself**, with the previous head folded in. Two properties of that definition are load-bearing:

**Self-exclusion is a necessity, not a convention.** A digest that covered itself would be
uncomputable — the same reason OCI keeps a digest in a manifest *about* an artifact rather than
inside it (ADR-051 Decision 4).

**The canonicalizer is the one the identity digest already uses.** `generate_pin_manifest.jcs_bytes`
refuses anything its RFC 8785 subset cannot canonicalize provably (non-ASCII keys, NaN/Inf, integers
past ±2^53, exponent-formatted floats). Reusing it means the chain and the identity digest can never
disagree about what the bytes of a record are — and a second canonicalizer would disagree eventually,
silently, in a way that reads as tampering.

**Folding in `previous` is what makes it a chain rather than a checksum.** Without it each version
would be independently verifiable and the ORDER would not be: an attacker could drop a version and
every remaining head would still check out. With it, removing a version breaks the link at the seam.
"""
import hashlib
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import generate_pin_manifest as _pin  # noqa: E402  (path must be set first)

ALGORITHM = "sha256-jcs"


def head_for(record, previous=None):
    """The `integrity.head` a record should carry, given its predecessor's head.

    `previous` is taken from the argument rather than from `record["integrity"]["previous"]`, so a
    caller verifying a chain supplies what the chain SAYS came before and a caller computing a new
    head supplies what actually did. A function that read the claim it is checking would confirm
    any self-consistent forgery."""
    body = {k: v for k, v in record.items() if k != "integrity"}
    payload = {"previous": previous, "record": body}
    return "sha256:" + hashlib.sha256(_pin.jcs_bytes(payload)).hexdigest()


def verify(record):
    """(ok, detail) for one record against its own claimed `integrity`.

    Verifies the head recomputes from the record's current bytes and its CLAIMED previous. It cannot
    verify that the claimed previous is the real predecessor — that needs the prior version, which
    is `verify_chain`'s job. Reporting one as the other would overstate what a single record proves."""
    integ = record.get("integrity")
    if not isinstance(integ, dict):
        return True, "no integrity block — unchained (permitted; the chain is opt-in per record)"
    if integ.get("algorithm") != ALGORITHM:
        return False, (f"algorithm {integ.get('algorithm')!r} is not {ALGORITHM!r} — a head cannot "
                       f"be checked without knowing the rule that produced it")
    if "previous" not in integ:
        return False, ("`previous` is absent. Null means chain ROOT; absent means a link that was "
                       "never stated, and a verifier that treated them alike would read every "
                       "truncation as a fresh start")
    try:
        expect = head_for(record, integ.get("previous"))
    except Exception as e:
        return False, f"record is not canonicalizable: {e}"
    if expect != integ.get("head"):
        return False, (f"head {integ.get('head')} does not recompute — the bytes changed after it "
                       f"was sealed (recomputed {expect})")
    return True, "head verifies"


def verify_chain(versions):
    """(ok, findings) for an ordered list of a record's versions, oldest first.

    Checks each head recomputes AND that each `previous` names the actual prior head — the second is
    what a single record cannot establish about itself, and what makes dropping a version detectable."""
    findings, prior = [], None
    for i, rec in enumerate(versions):
        ok, detail = verify(rec)
        if not ok:
            findings.append(f"version[{i}]: {detail}")
            prior = (rec.get("integrity") or {}).get("head")
            continue
        integ = rec.get("integrity") or {}
        if not integ:
            prior = None
            continue
        claimed = integ.get("previous")
        if i == 0:
            if claimed is not None:
                findings.append(f"version[0]: claims previous {claimed} but is the first version — "
                                f"a chain root's `previous` is null")
        elif claimed != prior:
            findings.append(f"version[{i}]: claims previous {claimed}, but version[{i-1}]'s head is "
                            f"{prior} — a version was dropped, reordered, or rewritten")
        prior = integ.get("head")
    return (not findings), findings


def seal(record, previous=None, hashed_by=None):
    """Return the record with a freshly computed `integrity` block. The control plane is the sole
    hasher (ADR-059); this is the reference implementation of that computation."""
    out = {k: v for k, v in record.items() if k != "integrity"}
    integ = {"head": head_for(out, previous), "previous": previous, "algorithm": ALGORITHM}
    if hashed_by:
        integ["hashed_by"] = hashed_by
    out["integrity"] = integ
    return out


if __name__ == "__main__":
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
    ok, detail = verify(doc)
    print(("OK  " if ok else "FAIL") + f" {sys.argv[1]}: {detail}")
    sys.exit(0 if ok else 1)
