#!/usr/bin/env python3
"""No coined constant in a certification rule (CNF-001).

**The defect this closes.** `CONFORMANCE.md` is the one surface a third party certifies against.
Two of its rules tested a number the specification does not set:

    WIR-008  Skew ≤±5 seconds from peers
    WIR-009  Future timestamps >5s ahead are rejected

`time-and-clock.md` §6 says the opposite in as many words — *"The platform mandates **no** fixed skew
tolerance"* — and ADR-005 rejected the ±5 s constant explicitly, on the grounds that it is not a
recognized standard and that baking one number into the substrate forces one regime on every
deployment. So an implementation could have certified against a requirement the spec had withdrawn,
and a stricter one could have failed certification for being correct.

Nothing caught it, and the reason is worth stating: `WIR-*`'s registered home IS `CONFORMANCE.md`.
The single-source gate reads that as one definition in one file and passes. Two documents that each
own their own rule family can contradict each other cleanly forever — single-source is necessary and
not sufficient.

  CNF-001  a rule row in CONFORMANCE.md states a bare quantity — a number with a unit of time, size,
           ratio or count. UDLM ships no defaults (NDF-001) and adopts standards by reference (T5),
           so a certifiable quantity comes from a profile or an adopted standard, never from the
           checklist. The rule may still REQUIRE a bound: *"the declared `max_divergence` is
           enforced"* is testable and coins nothing.

**Escape hatches, both narrow and both leaving a trace.** A row may carry a quantity when it cites
the standard the quantity comes from (`RFC 3339`, `RFC 9562`, `MiFID II`) — that is adoption by
reference, which T5 requires rather than merely permits. Structural constants that are part of a
cited format are not policy: `RFC 3339` is a name, not a threshold.

**What this deliberately does NOT check.** Quantities anywhere outside the conformance rule rows.
Prose explaining a profile's 50 ms, a table of adopted standards, an ADR narrating a rejected
constant — all legitimate, and a gate that flagged them would be noise nobody reads. The narrow
scope is the point: this guards the surface where a coined number does real damage, which is the
surface that certifies.

Exit 0 = every certifiable quantity comes from somewhere with authority to set it.
"""
import os
import re
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFORMANCE = os.path.join(REPO, "CONFORMANCE.md")

# A rule row: the first cell is a rule ID in backticks.
ROW = re.compile(r"^\|\s*`([A-Z][A-Z0-9]{1,7}(?:-[A-Z]{1,5})*-\d{2,3})`\s*\|(.*)$")

# A bare quantity: a number bound to a unit. Deliberately unit-anchored — a bare integer is usually
# an index, a version or a count in prose, and flagging those would drown the signal.
QUANTITY = re.compile(
    r"(?<![\w.\-/])[±<>≤≥]?\s?\d+(?:\.\d+)?\s*"
    r"(seconds?|secs?|ms|milliseconds?|µs|us|microseconds?|minutes?|mins?|hours?|days?|weeks?|"
    r"months?|years?|%|KiB|MiB|GiB|TiB|KB|MB|GB|TB)(?![\w])",
    re.IGNORECASE)

# An adopted standard named in the same row. A quantity travelling with its source is adoption by
# reference (T5), which is the sanctioned way to carry one.
ADOPTED = re.compile(
    r"\b(RFC\s?\d{3,5}|ISO[\s/]?\d{3,5}|IEEE\s?\d{3,4}|NIST|BIPM|MiFID|FINRA|CAT\b|PTP|NTP|"
    r"OAuth|SPIFFE|OpenTelemetry|CloudEvents|JSON\s?Schema|RSQL|semver|SemVer)\b",
    re.IGNORECASE)

# A row that defers the value rather than setting one. These are the SHAPE this gate wants rules to
# take: require that a bound exists and is honoured, without saying what it is.
DEFERS = re.compile(r"\b(declared|profile[- ]declared|adopts?|adopted|by reference|"
                    r"the implementation declares|its own)\b", re.IGNORECASE)


def findings():
    out = []
    with open(CONFORMANCE, encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            m = ROW.match(line)
            if not m:
                continue
            rule, body = m.group(1), m.group(2)
            q = QUANTITY.search(body)
            if not q:
                continue
            if ADOPTED.search(body):
                continue
            out.append((lineno, rule, q.group(0).strip(), body.strip()[:120]))
    return out


def main():
    if not os.path.exists(CONFORMANCE):
        print("FAILED — CONFORMANCE.md is missing; the certification surface cannot be checked")
        return 1

    rows = sum(1 for l in open(CONFORMANCE, encoding="utf-8") if ROW.match(l))
    hits = findings()

    # Self-test: the arm must fire on the exact defect it was built for, and must NOT fire on the
    # two shapes that are legitimate. A gate that cannot distinguish them would either be ignored or
    # would push authors to delete real requirements.
    probe_bad = "| `WIR-008` | runtime | Skew ≤±5 seconds from peers |"
    probe_adopted = "| `WIR-007` | artifact | Timestamps are RFC 3339 instants, seconds precision |"
    probe_defer = "| `WIR-008` | runtime | The declared `max_divergence` bound is enforced |"
    selftest = []
    if not (ROW.match(probe_bad) and QUANTITY.search(probe_bad) and not ADOPTED.search(probe_bad)):
        selftest.append("CNF-SELF the arm does not fire on the ±5 s row it was built for")
    if not ADOPTED.search(probe_adopted):
        selftest.append("CNF-SELF an RFC-cited row is not recognized as adoption by reference — "
                        "this gate would flag correct rows")
    if QUANTITY.search(probe_defer):
        selftest.append("CNF-SELF a row that defers the value is read as coining one")
    if not DEFERS.search(probe_defer):
        selftest.append("CNF-SELF the deferral shape is unrecognized")

    print(f"conformance constants: {rows} rule row(s) checked; {len(hits)} coined quantit(y/ies)")
    for m in selftest:
        print(f"  FAIL [{m}")
    for lineno, rule, q, body in hits:
        print(f"  ✗ CNF-001 {rule} (CONFORMANCE.md:{lineno}) certifies {q!r}, a value UDLM does not "
              f"set — NDF-001 ships no defaults and T5 adopts by reference")
        print(f"      {body}")
    if hits or selftest:
        if hits:
            print("\nFix: state the REQUIREMENT and let the profile or an adopted standard carry the "
                  "value — \"the declared `max_divergence` is enforced\" is certifiable and coins "
                  "nothing. If the quantity does come from a standard, name the standard in the row.")
        return 1
    print("OK — no certification rule coins a value the specification does not set")
    return 0


if __name__ == "__main__":
    sys.exit(main())
