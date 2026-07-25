#!/usr/bin/env python3
"""Provider contract cross-check: the references validate.py does NOT check.

registry/providers/* already validates against provider-adopted-standards.schema.json
(registry/tools/validate.py) — shape is covered there and not re-checked here. This gate
covers the CROSS-references between a provider doc and the rest of the registry:

  1. STANDARD RESOLUTION — every `adopted_standard_support[].standard` token must resolve to
     a **Covers:** token in registry/standards-adoption-register.md (the exact backticked
     token, the same discipline ADOPT-001 enforces for type-spec adopts[]). A provider naming
     a standard the register lacks is a HARD failure: the adoption decision (what/why/license)
     was never recorded.
  2. UUID DISCIPLINE — provider.uuid and every capability_uuid are canonical RFC 9562 v4 and
     unique ACROSS provider docs (they are accreditation anchors — subject_uuid and the
     capability grain; a shared anchor would let one attestation cover two subjects). A
     provider doc with no uuid is warned, not failed: the schema keeps it optional, but
     nothing can be accredited against it.
  3. VERSION RANGES — `supports` parses as a pin / wildcard / comparator range
     (">=1.2 <2.0", "1.x", "1.4"); `preferred`, when present, is a concrete pin or wildcard,
     never a comparator. Range RESOLUTION stays Policy (DCM ADS-003) — this only rejects
     strings no resolver could parse.

Provider docs today declare only adopted-standard support (+ capabilities); this check grows
with the provider contract. Exit non-zero on any failure. Wire into CI.
"""
import json
import pathlib
import re
import sys

try:
    import yaml
except ImportError:
    yaml = None

ROOT = pathlib.Path(__file__).resolve().parent.parent
PROVIDERS = ROOT / "registry" / "providers"
REGISTER = ROOT / "registry" / "standards-adoption-register.md"

UUID_V4 = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$")
# one whitespace-separated range token: optional comparator + dotted version, x/* wildcard tail
RANGE_TOKEN = re.compile(r"^(>=|<=|>|<|=)?[0-9]+(\.([0-9]+|[x*]))*$")
PIN_TOKEN = re.compile(r"^[0-9]+(\.([0-9]+|[x*]))*$")


def covered_tokens():
    """The register's exact token discipline: backticked tokens on **Covers:** lines —
    the same parse tests/validate_registry.py uses for ADOPT-001."""
    tokens = set()
    for line in REGISTER.read_text().splitlines():
        if "**Covers:**" in line:
            tokens.update(re.findall(r"`([^`]+)`", line.split("**Covers:**", 1)[1]))
    return tokens


def load(path: pathlib.Path):
    if path.suffix in (".yaml", ".yml"):
        if yaml is None:
            sys.exit(f"pyyaml required to load {path.name}")
        return yaml.safe_load(path.read_text())
    return json.loads(path.read_text())


def main():
    covered = covered_tokens()
    failures, warnings = [], []
    seen_uuids = {}  # uuid -> "file (role)"
    docs = 0

    for path in sorted(PROVIDERS.glob("*")):
        if path.suffix not in (".json", ".yaml", ".yml"):
            continue
        docs += 1
        doc = load(path)
        rel = path.name

        # 1. standard tokens resolve in the register — hard failure otherwise
        for entry in doc.get("adopted_standard_support") or []:
            std = entry.get("standard")
            if std and std not in covered:
                failures.append(f"{rel}: standard {std!r} has no **Covers:** entry in "
                                f"standards-adoption-register.md — register the adoption "
                                f"decision (what/why/license) in the same change")

            # 3. version-range sanity
            for field in ("supports", "preferred"):
                val = entry.get(field)
                if val is None:
                    continue
                if not isinstance(val, str) or not val.strip():
                    failures.append(f"{rel}: {std}.{field} is empty — declare a version or drop the field")
                    continue
                tokens = val.split()
                bad = [t for t in tokens if not RANGE_TOKEN.match(t)]
                if bad:
                    failures.append(f"{rel}: {std}.{field} {val!r} does not parse as a version "
                                    f"range (bad token(s): {', '.join(bad)})")
                elif field == "preferred" and (len(tokens) != 1 or not PIN_TOKEN.match(tokens[0])):
                    failures.append(f"{rel}: {std}.preferred {val!r} must be a single concrete "
                                    f"pin/wildcard, not a comparator range")

        # 2. uuid discipline — provider.uuid + every capability_uuid, one namespace
        anchors = []
        pu = (doc.get("provider") or {}).get("uuid")
        if pu is None:
            warnings.append(f"{rel}: provider has no uuid — schema-optional, but no "
                            f"accreditation can bind to this provider (subject_uuid anchor missing)")
        else:
            anchors.append((pu, "provider"))
        for cap in doc.get("capabilities") or []:
            cu = cap.get("capability_uuid")
            if cu is not None:
                anchors.append((cu, f"capability {cap.get('name', '?')!r}"))
        for u, role in anchors:
            if not UUID_V4.match(str(u)):
                failures.append(f"{rel}: {role} uuid {u!r} is not a canonical RFC 9562 v4 uuid")
                continue
            if u in seen_uuids:
                failures.append(f"{rel}: {role} uuid {u} duplicates {seen_uuids[u]} — "
                                f"accreditation anchors are never shared")
            seen_uuids[u] = f"{rel} ({role})"

    print(f"{docs} provider doc(s) cross-checked against {len(covered)} registered standard "
          f"token(s); {len(seen_uuids)} accreditation anchor(s)")
    for w in warnings:
        print(f"warn {w}")
    if failures:
        print(f"\nFAIL — {len(failures)} finding(s):")
        for f in failures:
            print(f"  {f}")
        return 1
    print("OK — every provider standard resolves, anchors unique, version ranges parse")
    return 0


if __name__ == "__main__":
    sys.exit(main())
