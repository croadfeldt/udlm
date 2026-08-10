#!/usr/bin/env python3
"""SOV-006 — a cited sovereignty zone resolves to a declared one.

The accreditation side has always spoken ISO 3166: `scope.geographic_scope` is *"ISO 3166 country /
3166-2 subdivision, or a declared region grouping"*. The entity side carries `sovereignty.zone`, a
coined label — `eu-west`, `us-east-1` — and the schema types it as a bare string with no pattern and
no description.

So `accreditation-and-authorization-matrix.md` §3.8's residency-subsumption rule had nothing to
evaluate. There was no stated way an entity in `eu-west` meets an accreditation scoped `DE`, and
nothing to compute it from. The rule was written, the standard was adopted, and the two never met.

`SovereigntyZone` is the record that connects them, and this gate is what stops the connection being
optional:

  SOV-006  an entity's `sovereignty.zone` resolves to a declared SovereigntyZone.

**Why an unresolvable zone is worse than an absent one.** An entity with no `sovereignty` block makes
no claim, and nothing pretends otherwise. An entity citing `eu-west` where no such zone is declared
makes a claim that *looks* checkable and is not — it will pass every gate, appear in a compliance
report, and mean nothing. That is the failure mode this whole issue is about.

**What this gate does NOT do: evaluate §3.8.** Deciding whether an accreditation covers a zone needs
the subsumption rules — residency subsumes DOWN a jurisdiction hierarchy (an authorization for `US`
covers `US-MN` residency), while a distinct sovereignty regime matches EXACTLY (`US` does not cover a
Minnesota state regime). That is now *computable* because both sides speak ISO 3166, and it is the
next piece rather than this one. Named here so the gap is not mistaken for coverage.

Exit 0 = every cited zone resolves; 1 = at least one does not.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ZONE_TYPE = "SovereigntyZone"


def _fields(rec):
    for name in ("realized", "requested", "intent"):
        f = ((rec.get("states") or {}).get(name) or {}).get("fields")
        if f:
            return f
    return {}


def load_records():
    """Every instance under examples/ and instances/, excluding the negative corpus — those are
    inputs a case hands to a gate deliberately, not part of the estate being judged."""
    out = []
    for root in ("registry/examples", "registry/instances"):
        for p in sorted(glob.glob(os.path.join(ROOT, root, "**", "*.yaml"), recursive=True)):
            if "must-reject" in p.split(os.sep) or os.sep + "classes" + os.sep in p:
                continue
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            for d in docs:
                if isinstance(d, dict) and d.get("uuid"):
                    d.setdefault("_path", os.path.relpath(p, ROOT))
                    out.append(d)
    return out


def declared_zones(records):
    """handle -> the zone's declared fields. A zone is cited by handle, because a coined name is what
    an operator writes and what a peer reads."""
    return {r["handle"]: _fields(r) for r in records
            if r.get("resource_type") == ZONE_TYPE and r.get("handle")}


def evaluate(record, zones):
    """Judge ONE record against the declared zones. Bindable per #434's convention."""
    zone = (record.get("sovereignty") or {}).get("zone")
    if not zone:
        return []                      # no claim made; nothing to verify
    who = record.get("handle") or (record.get("uuid") or "?")[:8]
    if zone not in zones:
        return [f"SOV-006 {who}: sovereignty.zone {zone!r} resolves to no declared SovereigntyZone. "
                f"An accreditation states its scope in ISO 3166; an undeclared label cannot be "
                f"matched against it, so the placement reads as checked and is not"]
    if not (zones[zone] or {}).get("jurisdictions"):
        return [f"SOV-006 {who}: zone {zone!r} is declared but states no jurisdictions — it records a "
                f"name and answers nothing"]
    return []


def main():
    records = load_records()
    zones = declared_zones(records)
    fails, cited = [], 0
    for r in records:
        if (r.get("sovereignty") or {}).get("zone"):
            cited += 1
            fails += evaluate(r, zones)

    # self-test: both arms, or the gate only proves the walk ran
    probe = {"eu-west": {"jurisdictions": ["DE"]}, "hollow": {}}
    if not evaluate({"handle": "a", "sovereignty": {"zone": "nope"}}, probe):
        print("FAIL [SOV-SELF] an undeclared zone was accepted")
        fails.append("self-test")
    if not evaluate({"handle": "b", "sovereignty": {"zone": "hollow"}}, probe):
        print("FAIL [SOV-SELF] a zone with no jurisdictions was accepted")
        fails.append("self-test")
    if evaluate({"handle": "c", "sovereignty": {"zone": "eu-west"}}, probe):
        print("FAIL [SOV-SELF] a declared zone was refused")
        fails.append("self-test")

    print(f"sovereignty-zones: {len(zones)} zone(s) declared, {cited} entity citation(s) checked")
    for z, f in sorted(zones.items()):
        print(f"  {z:22s} {', '.join(f.get('jurisdictions') or []) or '(none)'}"
              + (f"  regimes: {', '.join(f.get('regimes') or [])}" if f.get("regimes") else ""))
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} unresolvable zone citation(s)")
        return 1
    print("OK — every cited sovereignty zone resolves to a declared one")
    return 0


if __name__ == "__main__":
    sys.exit(main())
