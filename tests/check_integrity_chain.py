#!/usr/bin/env python3
"""Every declared `integrity` head verifies (INT-001/002/003).

ADR-059 gave the working record a resource chain: `integrity.head` over the record's canonical bytes,
linking the previous version's head, so a record can answer *"have I been altered"* **without any
other system**. That clause is the whole design — records are unbounded in lifetime and stores are
not, so a verification that reached into the ledger would work until the day it silently did not.

A chain nothing recomputes is decoration, and worse than none: it looks like evidence.

  INT-001  a declared `head` recomputes from the record's current bytes and its claimed `previous`.
           This is what catches a record edited after sealing.
  INT-002  the block is well-formed — a named `algorithm`, and `previous` PRESENT (null means chain
           root; absent means a link never stated, and a verifier that conflated them would read
           every truncation as a fresh start).
  INT-003  the chain's rule and the identity digest's rule agree about a record's bytes. Both are
           the RFC 8785 subset in `generate_pin_manifest`; a second canonicalizer would eventually
           disagree, silently, in a way indistinguishable from tampering.

**Opt-in, deliberately.** A record with no `integrity` block is unchained and passes. UDLM ships the
mechanism; whether an estate chains a given record is the estate's call — the same split that makes
`limits` data here and policy there. What is NOT optional is that a DECLARED chain be real.

Exit 0 = every declared chain verifies.
"""
import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                "registry", "tools"))
import integrity_chain as IC  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def records():
    """Every registry document carrying an `integrity` block, with where it came from."""
    out = []
    for f in sorted(glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True)
                    + glob.glob(os.path.join(ROOT, "registry", "**", "*.json"), recursive=True)):
        if "must-reject" in f or os.sep + "generated" + os.sep in f:
            continue
        try:
            docs = list(yaml.safe_load_all(open(f, encoding="utf-8")))
        except Exception:
            continue
        for i, d in enumerate(docs):
            if isinstance(d, dict) and isinstance(d.get("integrity"), dict):
                out.append((os.path.relpath(f, ROOT), i, d))
    return out


def main():
    found = records()
    fails = []

    for rel, idx, doc in found:
        where = f"{rel}" + (f"#{idx}" if idx else "")
        integ = doc["integrity"]

        if "previous" not in integ:
            fails.append(f"INT-002 {where}: `previous` is absent. Null means chain ROOT; absent "
                         f"means a link that was never stated, and treating them alike would read "
                         f"every truncation as a fresh start")
            continue
        if integ.get("algorithm") != IC.ALGORITHM:
            fails.append(f"INT-002 {where}: algorithm {integ.get('algorithm')!r} is not "
                         f"{IC.ALGORITHM!r} — a head cannot be checked without the rule that made it")
            continue

        ok, detail = IC.verify(doc)
        if not ok:
            fails.append(f"INT-001 {where}: {detail}")

    # INT-003 — the chain and the identity digest must canonicalize the same way. Asserted by
    # construction (one module) and CHECKED, because "we reuse it" is a claim about an import that
    # a refactor can quietly falsify.
    import generate_pin_manifest as _pin
    probe = {"b": 2, "a": 1, "n": [3, {"z": 0, "y": 1}]}
    if _pin.jcs_bytes(probe) != IC._pin.jcs_bytes(probe):
        fails.append("INT-003 the chain and the identity digest are not using the same "
                     "canonicalizer — two rules for a record's bytes will disagree eventually, "
                     "and the disagreement is indistinguishable from tampering")

    # Self-test: each arm on a planted break. An arm that cannot fire proves only that the YAML
    # parsed — which is exactly the state a decorative chain would leave this gate in.
    st = []
    r1 = IC.seal({"record_type": "probe", "uuid": "a", "generation": 1})
    r2 = IC.seal({"record_type": "probe", "uuid": "a", "generation": 2},
                 previous=r1["integrity"]["head"])
    if not IC.verify(r1)[0]:
        st.append("INT-SELF a freshly sealed record does not verify — sealing and verifying "
                  "disagree, so every pass is meaningless")
    tampered = dict(r2, generation=99)
    if IC.verify(tampered)[0]:
        st.append("INT-SELF a record edited after sealing still verifies")
    r3 = IC.seal({"record_type": "probe", "uuid": "a", "generation": 3},
                 previous=r2["integrity"]["head"])
    if IC.verify_chain([r1, r3])[0]:
        st.append("INT-SELF a dropped version is not detected — the chain is behaving as a "
                  "per-record checksum, which cannot see order")
    if not IC.verify_chain([r1, r2, r3])[0]:
        st.append("INT-SELF an intact chain is reported broken")

    print(f"integrity chains: {len(found)} record(s) declare a chain")
    for m in st:
        print(f"  FAIL [{m}")
    for m in fails:
        print(f"  ✗ {m}")
    if fails or st:
        return 1
    print("OK — every declared chain verifies")
    return 0


if __name__ == "__main__":
    sys.exit(main())
