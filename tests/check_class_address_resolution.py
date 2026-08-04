#!/usr/bin/env python3
"""Guards dotted-address resolution over the scoped-Class hierarchy (ADR-038 / P0).

Asserts the resolver (registry/tools/resolve_class_address.py) walks inheritance correctly across
both the Compute (depth) and Process (multi-provider) chains, and that unresolvable addresses fail
deterministically. Doubles as a regression guard: renaming or moving an element, or breaking a
`parent` link, trips this. Exit 0 = all cases hold; 1 = a resolution changed.
"""
import importlib.util
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location(
    "resolve_class_address", os.path.join(ROOT, "registry", "tools", "resolve_class_address.py"))
R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R)
by_name = R.load_classes()

CASES = [
    # address                              owning_class          inherited
    # --- dot / compact notation ---
    ("Compute#cpu",                        "Compute",            False),   # declared on the Base itself
    ("Compute.VM#cpu",                     "Compute",            True),    # inherited from Base
    ("Compute.VM#firmware",                "Compute.VM",         False),   # declared on the Type
    ("Compute.VM#storage_tier",            "Compute",            True),    # governed-vocab element, inherited
    ("Automation.OSPatch#idempotency",        "Automation",            True),    # inherited from Process Base
    ("Automation.OSPatch#patch_policy",       "Automation.OSPatch",    False),   # declared on the Type
    ("Automation.OSPatch.EngineBlue#definition_ref", "Automation.OSPatch.EngineBlue", False),  # provider-scope
    ("Automation.OSPatch.EngineBlue#idempotency",    "Automation",     True),    # inherited two levels up
    # --- URL notation (the same coordinates, ADR-038's preferred form) ---
    ("https://udlm.dev/class/Compute/VM#cpu",              "Compute",         True),   # local URL
    ("https://state.mn/Compute/VM#firmware",              "Compute.VM",      False),  # federated authority
    ("https://udlm.dev/registry/udlm/0.1/class/Automation/OSPatch#idempotency", "Automation", True),  # $id-scaffolded URL
    ("https://peer.dcm.east/Automation/OSPatch/EngineBlue#definition_ref", "Automation.OSPatch.EngineBlue", False),
]
UNRESOLVABLE = [
    "Compute.VM#does_not_exist",   # no such element
    "Nonexistent.Class#cpu",       # no such class
    "Compute#firmware",            # firmware is on the Type, not visible from the Base
    "Compute.VM",                  # not an address (no '#')
]


def main():
    fails = []
    for addr, owner, inherited in CASES:
        try:
            r = R.resolve(addr, by_name)
        except KeyError as e:
            fails.append(f"{addr}: expected to resolve to {owner}, but raised {e}"); continue
        if r["owning_class"] != owner:
            fails.append(f"{addr}: owning_class {r['owning_class']!r} != expected {owner!r}")
        if r["inherited"] != inherited:
            fails.append(f"{addr}: inherited {r['inherited']} != expected {inherited}")
        if r["scope"] != owner:  # the SDE scope must equal its owning class (Liskov gate guarantees it)
            fails.append(f"{addr}: element scope {r['scope']!r} != owning_class {owner!r}")
    for addr in UNRESOLVABLE:
        try:
            R.resolve(addr, by_name)
            fails.append(f"{addr}: expected UNRESOLVED, but it resolved")
        except KeyError:
            pass
    # the two notations are the same coordinate — they must resolve identically
    for dot, url in [("Compute.VM#cpu", "https://udlm.dev/class/Compute/VM#cpu"),
                     ("Automation.OSPatch.EngineBlue#idempotency", "https://x/Automation/OSPatch/EngineBlue#idempotency")]:
        rd, ru = R.resolve(dot, by_name), R.resolve(url, by_name)
        if (rd["owning_class"], rd["element"], rd["scope"]) != (ru["owning_class"], ru["element"], ru["scope"]):
            fails.append(f"notation mismatch: {dot} vs {url} resolve differently")
    for f in fails:
        print("FAIL [ADR-RES] " + f)
    print(f"{len(CASES)} resolution(s) + {len(UNRESOLVABLE)} unresolvable case(s) checked, {len(fails)} failure(s)")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
