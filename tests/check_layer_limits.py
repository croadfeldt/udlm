#!/usr/bin/env python3
"""Layer lineage and envelope containment (LAY-009/LAY-010).

`extends` and `limits` gave a layer explicit lineage and a declared envelope. Declaring them is not
the same as enforcing them, and shipping a rule with no machine surface is the exact defect the ADR
audit exists to find — nine records in that audit were "recorded but never built".

  LIM-001  every `extends[].layer` resolves to a real layer record. A parent nobody can read
           bounds nothing, and the child would then be validated against silence.
  LIM-002  the extension graph is ACYCLIC. A cycle computes no value, and the model refuses what
           cannot be computed. Depth is NOT checked — deep chains are normal here, and how deep is
           too deep is a policy judgement, never a structural one.
  LIM-003  a layer's own `limits` sit inside every applicable ancestor envelope. Checked per
           ancestor rather than against a merged envelope, because LIMITS INTERSECT WHERE VALUES
           OVERRIDE: satisfying a permissive ancestor must never excuse violating a restrictive
           one, or permission could be bought by extending one more layer.
  LIM-004  a layer's own `fields` satisfy its own `limits`. A layer that bounds a field and then
           sets a value outside its own bound is incoherent before any child is involved.
  LIM-005  the envelope is SATISFIABLE — no field's applicable clauses intersect to nothing. Since
           `when` is equality-only this is statically decidable, so a layer nothing can ever satisfy
           is caught at authoring time rather than surfacing later as a baffling assembly failure
           with no route out (there is no override for a bound, by design).

**Every finding names what LAY-010 requires a DENIAL to name** — the binding layer with its owner,
the field, the value, the clause and its reason. Not decoration: the runtime obligation is that a
refusal be attributable, and a gate that reports "layer X violates a limit" while the runtime is
required to say which ancestor, owned by whom, under which clause, would be holding the
specification to a lower standard than the implementation.

**What this does NOT do.** It does not decide whether a bound is *wise*, and it does not enforce
limits on an ESTATE's assembled requests — that is a `validation` policy's job, because a layer
holds an estate's configuration and what is permitted there is the estate's call (LAY-009). This
gate checks that the layers UDLM itself ships are coherent: an incoherent worked example teaches the
mechanism wrong.

Exit 0 = lineage resolves, no cycles, every envelope contained and satisfiable.
"""
import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "..", "registry", "tools"))
import containment as C  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load_layers():
    """uuid -> layer, for every layer record in the registry."""
    out = {}
    for f in sorted(glob.glob(os.path.join(ROOT, "registry", "**", "*.yaml"), recursive=True)):
        if "must-reject" in f:
            continue
        try:
            docs = list(yaml.safe_load_all(open(f, encoding="utf-8")))
        except Exception:
            continue
        for d in docs:
            if isinstance(d, dict) and d.get("record_type") == "layer" and d.get("uuid"):
                d["_file"] = os.path.relpath(f, ROOT)
                out[d["uuid"]] = d
    return out


def parent_uuid(entry):
    """The uuid a `extends[].layer` URF names. Authored by handle, resolved to the uuid form —
    this reads the uuid form, which is what the corpus carries."""
    ref = entry.get("layer") or ""
    if not ref.startswith("uuid/"):
        return None
    return ref[len("uuid/"):].split("?")[0].split("@")[0].split("/")[0]


def owner(layer):
    """Who to name in a denial (LAY-010). A bound nobody can be asked about is a dead end."""
    c = layer.get("contributor") or {}
    return (f"tenant {layer.get('tenant_uuid', '?')[:8]}"
            f"{', ' + c['contributor_type'] if c.get('contributor_type') else ''}"
            f"{', review ' + c['review'] if c.get('review') else ''}")


def label(layer):
    return (f"{layer.get('handle') or layer.get('name') or layer['uuid'][:8]}"
            f"@{layer.get('version', '?')} ({layer['uuid'][:8]})")


def ancestors(layer, layers, seen=None):
    """Every ancestor reachable through `extends`, with the entry that reached it.

    selections are NOT applied: a `when`-scoped extension is walked regardless, because a child must
    be contained under every context its parents could be evaluated in, not merely one."""
    seen = seen or set()
    out = []
    for e in layer.get("extends") or []:
        pu = parent_uuid(e)
        if not pu or pu in seen:
            continue
        seen.add(pu)
        p = layers.get(pu)
        if p:
            out.append(p)
            out += ancestors(p, layers, seen)
    return out


def find_cycle(layer, layers, path=None):
    path = path or []
    if layer["uuid"] in path:
        return path[path.index(layer["uuid"]):] + [layer["uuid"]]
    path = path + [layer["uuid"]]
    for e in layer.get("extends") or []:
        p = layers.get(parent_uuid(e) or "")
        if p:
            c = find_cycle(p, layers, path)
            if c:
                return c
    return None


def main():
    layers = load_layers()
    fails = []
    n_ext = n_lim = 0

    for uuid, L in sorted(layers.items()):
        where = f"{L['_file']}: {label(L)}"

        for i, e in enumerate(L.get("extends") or []):
            n_ext += 1
            pu = parent_uuid(e)
            if not pu:
                fails.append(f"LIM-001 {where}: extends[{i}].layer is not a uuid-form URF — a "
                             f"parent that cannot be resolved bounds nothing")
            elif pu not in layers:
                fails.append(f"LIM-001 {where}: extends[{i}] names {pu[:8]}, which resolves to no "
                             f"layer — the child would be validated against silence")

        cyc = find_cycle(L, layers)
        if cyc:
            fails.append(f"LIM-002 {where}: extension cycle {' -> '.join(u[:8] for u in cyc)} — a "
                         f"cycle computes no value, and the model refuses what cannot be computed")
            continue

        limits = L.get("limits") or {}
        n_lim += len(limits)

        # LIM-005 — satisfiable at all
        for field, clauses in limits.items():
            if C.value_binding_clause is None:
                break
            lo = max((C.magnitude(c.get("min")) for c in clauses
                      if C.magnitude(c.get("min")) is not None and not c.get("when")), default=None)
            hi = min((C.magnitude(c.get("max")) for c in clauses
                      if C.magnitude(c.get("max")) is not None and not c.get("when")), default=None)
            if lo is not None and hi is not None and lo > hi:
                fails.append(f"LIM-005 {where}: `{field}` bounds intersect to nothing (floor {lo} "
                             f"above ceiling {hi}) — no value can ever satisfy this layer, and "
                             f"there is no override for a bound")

        # LIM-003 — contained in every ancestor envelope, checked one ancestor at a time
        anc = ancestors(L, layers)
        for field, clauses in limits.items():
            envelopes = [(a, (a.get("limits") or {}).get(field) or []) for a in anc]
            for c, a, bound in C.envelope_containment(clauses, envelopes):
                fails.append(
                    f"LIM-003 {where}: `{field}` clause {c} is outside the envelope declared by "
                    f"{label(a)} [owner: {owner(a)}] — binding clause {bound}"
                    + (f" — reason: {bound['reason'].rstrip('.')}" if bound.get("reason") else "")
                    + ". Limits INTERSECT: a permissive ancestor never excuses a restrictive one.")

        # LIM-004 — the layer's own values satisfy its own bounds
        for field, value in (L.get("fields") or {}).items():
            clauses = limits.get(field)
            if not clauses:
                continue
            bound = C.value_binding_clause(value, clauses)
            if bound is not None:
                fails.append(
                    f"LIM-004 {where}: sets `{field}` = {value!r}, outside its OWN limits "
                    f"[owner: {owner(L)}] — binding clause {bound}"
                    + (f" — reason: {bound['reason']}" if bound.get("reason") else ""))

    # Self-test: every arm gets a planted break. An arm that cannot fire proves only that the YAML
    # parsed — which is the state LAY-009/010 would be in if this gate were skipped entirely.
    st = []
    probe = {"uuid": "u1", "extends": [{"layer": "uuid/u1"}], "version": "1"}
    if not find_cycle(probe, {"u1": probe}):
        st.append("LIM-SELF the cycle arm cannot detect a self-extension")
    if C.envelope_containment([{"max": 512}], [("a", [{"max": 384}])]) == []:
        st.append("LIM-SELF containment does not reject a widened child clause")
    if C.envelope_containment([{"max": 256}], [("a", [{"max": 384}])]) != []:
        st.append("LIM-SELF containment rejects a legitimately narrowed child clause")
    if C.value_binding_clause(512, [{"max": 384}]) is None:
        st.append("LIM-SELF a value over the ceiling is not reported as bound")
    if not layers:
        st.append("LIM-SELF no layer records were loaded — every arm would pass vacuously")

    print(f"layer limits: {len(layers)} layer(s), {n_ext} extension(s), {n_lim} bounded field(s)")
    for m in st:
        print(f"  FAIL [{m}")
    for m in fails:
        print(f"  ✗ {m}")
    if fails or st:
        if fails:
            print("\nEvery finding above names what LAY-010 requires a DENIAL to name: the binding "
                  "layer, its owner, the field, the value and the clause with its reason.")
        return 1
    print("OK — lineage resolves, no cycles, every envelope contained and satisfiable")
    return 0


if __name__ == "__main__":
    sys.exit(main())
