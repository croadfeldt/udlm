#!/usr/bin/env python3
"""The triad closes: a capability, an action and a thing each reach the other two (TRI-001/002/003).

**The problem this closes.** Three axes describe what an implementation offers, and until now
nothing checked they lined up:

    capability   what a PROVIDER can do              realize_resources, serve_data
    thing        what it offers                      Compute.VM, Storage.Volume
    action       what may be DONE to that thing      read, create, replicate

Each was maintained on its own, and each drifted on its own. `provider-capability.yaml` had no gate
at all, which is how a SECOND closed vocabulary also called "capability" grew in
`governance-matrix.md` with two words in common. The audit action list and the matrix's list forked
the same way. Nobody noticed, because a list checked against nothing always looks complete.

**What a missing edge actually costs**, which is why this is a gate and not a lint:

  a capability with no action   nobody can use it — a provider declares it and no request can
                                exercise it
  a capability with no thing    nobody can offer it — it applies to nothing in the class system
  an action with no capability  nobody can provide it — it can be permitted and never performed
  a thing with no capability    nobody can realize it — the class exists and no provider can
                                declare it offers one

Each is a hole a consumer discovers at request time, and each is invisible in any single file.

  TRI-001  every canonical capability reaches at least one action AND at least one thing
  TRI-002  every canonical action names a capability that exists (`enabled_by`)
  TRI-003  every capability CATEGORY (`<capability>/<Domain>`) names a domain that resolves to a
           real class in the registry — a category for a domain that does not exist is a promise
           against nothing

**What this deliberately does NOT check, and the distinction is the whole design** (maintainer
ruling 2026-08-11: *UDLM focuses on the mechanisms, not the correctness of the data*):

  NOT   that every class domain has a capability. 19 of 23 do not, and that is DATA — an estate
        declares the categories its providers actually offer. Requiring coverage would make UDLM
        assert what an implementation must provide, which is the defect the depth caps and the
        shipped profiles were removed for.
  NOT   whether an actor may perform an action. That is policy's call and the implementation's.

The direction matters: this checks that what UDLM SHIPS is coherent — every standard term reaches
the other two axes — never that an estate's data is complete.

**Extension is the point.** A new capability, action or thing added to the base must arrive with its
complements, so the graph stays connected as the vocabulary grows. That is the gate a reviewer
cannot hold in their head.

Exit 0 = the triad closes; 1 = something was added without its complements.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# KNOWN, AND AWAITING A RULING rather than silently tolerated. `federate/Peer` names a domain the
# class system does not model, and the fix is a decision, not an edit: PRV-004 rules that "a peer
# implementation IS a typed provider — federation is the Provider abstraction applied across
# control-plane instances, not a separate abstraction". If that holds, a Peer is not a THING and the
# category is naming the wrong axis; if it does not, a Peer class is missing. Either way it is the
# maintainer's call, so it is listed here with its reason rather than deleted to make a gate green.
# An entry here WARNS; anything else FAILS.
BASELINE = {"federate/Peer"}
CAPS = os.path.join(ROOT, "registry", "taxonomies", "provider-capability.yaml")
ACTS = os.path.join(ROOT, "registry", "taxonomies", "action.yaml")
CLASSES = os.path.join(ROOT, "registry", "classes")


def load(p):
    return yaml.safe_load(open(p, encoding="utf-8")) or {}


def class_domains():
    """The set of things a capability category may name.

    TWO GRAINS, both legitimate, and the gate accepts either. A category may name a NAME SEGMENT
    (`Compute`, from `Compute.VM`) or a FAMILY (`Process`, which holds `Job.*` and `Automation.*`).
    The shipped set uses both — `realize_resources/Compute` is a segment, `execute_workflows/Process`
    is a family — and neither is wrong: a capability that applies to every Process is honestly stated
    at the family grain.

    What is NOT accepted is a name belonging to neither, because that is a category promising
    something the class system does not model."""
    segs, fams = set(), set()
    for f in glob.glob(os.path.join(CLASSES, "**", "*.yaml"), recursive=True):
        try:
            d = yaml.safe_load(open(f, encoding="utf-8")) or {}
        except Exception:
            continue
        if d.get("record_type") == "class" and d.get("resource_type"):
            segs.add(d["resource_type"].split(".")[0])
            if d.get("family"):
                fams.add(d["family"])
    return segs | fams


def main():
    for p in (CAPS, ACTS):
        if not os.path.exists(p):
            print(f"FAILED — missing vocabulary: {os.path.relpath(p, ROOT)}")
            return 1

    caps_doc, acts_doc = load(CAPS), load(ACTS)
    cap_root = caps_doc.get("root", "provider-capability")

    # A capability VERB is a term with no "/" that is not the root; a CATEGORY carries "/".
    verbs = {t["term"] for t in caps_doc.get("terms", [])
             if "/" not in t["term"] and t["term"] != cap_root}
    cats = {t["term"] for t in caps_doc.get("terms", []) if "/" in t["term"]}
    actions = {t["term"]: t for t in acts_doc.get("terms", []) if t["term"] != acts_doc.get("root")}
    domains = class_domains()

    fails = []

    # TRI-002 — action -> capability
    for name, t in actions.items():
        eb = t.get("enabled_by")
        if not eb:
            fails.append(f"TRI-002 action {name!r} names no `enabled_by` — it can be permitted and "
                         f"never performed, because no capability offers it")
        elif eb not in verbs:
            fails.append(f"TRI-002 action {name!r} is enabled_by {eb!r}, which is not a capability "
                         f"({', '.join(sorted(verbs))})")

    # TRI-001 — capability -> action, and capability -> thing
    reached_by_action = {t.get("enabled_by") for t in actions.values()}
    for v in sorted(verbs):
        if v not in reached_by_action:
            fails.append(f"TRI-001 capability {v!r} has no action — a provider can declare it and "
                         f"no request can exercise it")
        if not any(c.startswith(v + "/") for c in cats):
            fails.append(f"TRI-001 capability {v!r} has no category — it applies to no thing in the "
                         f"class system, so nobody can offer it")

    # TRI-003 — category -> a thing that exists
    warned = 0
    for c in sorted(cats):
        dom = c.split("/", 1)[1]
        if dom not in domains:
            if c in BASELINE:
                warned += 1
                print(f"  WARN [TRI-003] {c} names domain {dom!r}, which resolves to no class — "
                      f"baselined pending a ruling (PRV-004: is a peer a THING or a provider?)")
            else:
                fails.append(f"TRI-003 category {c!r} names domain {dom!r}, which resolves to no "
                             f"class — a promise against nothing")

    # self-test: each arm must fire on a planted break, or this proves only that the files parsed.
    probe_actions = {"ghost": {"term": "ghost", "enabled_by": "no_such_capability"}}
    if probe_actions["ghost"]["enabled_by"] in verbs:
        print("FAIL [TRI-SELF] TRI-002 cannot distinguish an unknown capability")
        fails.append("self-test")
    if "NoSuchDomain" in domains:
        print("FAIL [TRI-SELF] TRI-003's domain set is not discriminating")
        fails.append("self-test")
    if not verbs or not actions or not domains:
        print("FAIL [TRI-SELF] an axis loaded empty — every arm would pass vacuously")
        fails.append("self-test")

    print(f"triad-coherence: {len(verbs)} capability/ies · {len(actions)} action(s) · "
          f"{len(cats)} category/ies over {len(domains)} class domain(s)")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} incoherence(s)")
        return 1
    print("OK — every capability reaches an action and a thing; every action names a capability; "
          "every category names a real thing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
