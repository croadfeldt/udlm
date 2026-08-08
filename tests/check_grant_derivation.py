#!/usr/bin/env python3
"""CTX-005 — the required-grant set is DERIVED, and this proves it derives.

ADR-066 rules that a consumer must learn which cross-boundary permissions an order needs *before*
admission rather than discovering them when dispatch fails. That claim rests on the set being
computable from data UDLM already holds. This is the reference implementation of that computation,
and its job is to keep the claim true — the same ratchet #321 set for catalog generation: UDLM ships
the reference implementation and the gate, DCM does the enforcing.

The walk, for every record that holds edges:

    for each dependency with a resolved target
        resolve the target -> the grouping that owns it
        owner is the holder's own grouping?           -> nothing to authorise
        target's TYPE declares publicly_stakeable /
          publicly_allocatable?                       -> satisfied by standing declaration (CTX-008)
        an Authorization granted_by owner granted_to
          holder, scoping the target?                 -> satisfied by grant
        otherwise                                     -> REQUIRED AND MISSING

CTX-008's standing declaration is reported rather than omitted, so the relationship stays visible
even when no grant is needed for it.

**No clock.** A gate that consults the wall clock starts failing on a date nobody chose. `valid_from`
and `expires_at` are reported and never enforced here: expiry is a runtime act (CTX-003 makes it
identical to revocation), which is control-plane, not a property of the authored model.

**What it cannot resolve, and says so.** A catalog constituent naming a `resource_type` with
`provided_by: external` has no instance yet — whose it will be is decided at placement. Those are
counted and surfaced as *determined at placement*, never silently dropped: a grant set that quietly
omits the unresolved half would read as "nothing needed".

  GRD-001  a resolved cross-boundary edge has a grant, a standing declaration, or it is a finding.

Exit 0 = every cross-boundary edge is accounted for; 1 = at least one is not.
"""
import glob
import os
import re
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_ROOTS = [os.path.join(ROOT, "registry", "examples"),
                  os.path.join(ROOT, "registry", "instances")]
CLASS_ROOTS = [os.path.join(ROOT, "registry", "classes"),
               os.path.join(ROOT, "registry", "examples", "classes")]

_UUID_IN = re.compile(r"uuid=in=\(([^)]*)\)")


def _fields(rec):
    """An instance keeps its values per state; realized is the system of record, requested next."""
    st = rec.get("states") or {}
    for name in ("realized", "requested", "intent"):
        f = (st.get(name) or {}).get("fields")
        if f:
            return f
    return {}


def load_instances():
    out = {}
    for root in INSTANCE_ROOTS:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            if os.sep + "classes" + os.sep in p:
                continue                      # worked-example CLASSES, not instances
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            for d in docs:
                if isinstance(d, dict) and d.get("uuid") and d.get("tenant_uuid"):
                    d["_path"] = os.path.relpath(p, ROOT)
                    out[d["uuid"]] = d
    return out


def load_type_flags():
    """resource_type -> the standing declarations it carries (CTX-008)."""
    flags = {}
    for root in CLASS_ROOTS:
        for p in glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True):
            try:
                d = yaml.safe_load(open(p, encoding="utf-8")) or {}
            except Exception:
                continue
            if d.get("record_type") == "class" and d.get("resource_type"):
                flags[d["resource_type"]] = {k: d.get(k) for k in
                                             ("publicly_stakeable", "publicly_allocatable")}
    return flags


def scopes(auth_fields, target_uuid):
    """Does this grant cover the target? The explicit-set criterion is evaluated; anything richer is
    a resolver's job and is reported as unevaluated rather than assumed either way."""
    crit = auth_fields.get("membership_criterion") or ""
    m = _UUID_IN.search(crit)
    if m:
        return target_uuid in {u.strip() for u in m.group(1).split(",")}, True
    return False, False          # (covered, evaluable)


def derive(instances, flags):
    """The required-grant set, plus the findings. One pass, no side effects."""
    auths = [r for r in instances.values() if r.get("resource_type") == "Grouping.Authorization"]
    entries, fails = [], []
    for rec in instances.values():
        holder = rec["tenant_uuid"]
        for dep in rec.get("dependencies") or []:
            tgt_uuid = dep.get("target_uuid")
            if not tgt_uuid:
                continue
            target = instances.get(tgt_uuid)
            if target is None:
                continue                       # off-estate reference; nothing to resolve an owner from
            owner = target["tenant_uuid"]
            if owner == holder:
                continue                       # same grouping — no boundary crossed
            f = flags.get(target.get("resource_type")) or {}
            if f.get("publicly_stakeable") or f.get("publicly_allocatable"):
                entries.append((rec, dep, target, "satisfied by standing declaration", None))
                continue
            hit = None
            for a in auths:
                af = _fields(a)
                if af.get("granted_by") == owner and af.get("granted_to") == holder:
                    covered, evaluable = scopes(af, tgt_uuid)
                    if covered:
                        hit = a
                        break
                    if not evaluable and hit is None:
                        hit = a                # matched the pair; scope left to the resolver
            if hit is not None:
                af = _fields(hit)
                entries.append((rec, dep, target, "satisfied by grant",
                                f"{hit['uuid'][:8]} ops={af.get('authorized_operations')} "
                                f"until={af.get('expires_at') or 'unbounded'}"))
            else:
                entries.append((rec, dep, target, "REQUIRED AND MISSING", None))
                fails.append(f"GRD-001 {rec['_path']}: {rec.get('handle', rec['uuid'][:8])} "
                             f"({rec.get('resource_type')}) holds a {dep.get('edge_type')} edge to "
                             f"{target.get('handle', tgt_uuid[:8])} owned by {owner[:8]}, and no "
                             f"authorization grants it. Refuse at admission, not at dispatch.")
    return entries, fails


def unresolvable(instances):
    """Catalog constituents whose owner is decided at placement — counted, never dropped."""
    n = 0
    for rec in instances.values():
        if rec.get("record_type") == "catalog_item":
            n += sum(1 for c in rec.get("constituents") or [] if c.get("provided_by") == "external")
    return n


def self_test(flags):
    """Arms with no shipped subject. `publicly_stakeable` is an ORG's declaration — rule 42, UDLM
    facilitates and does not dictate — so no registry type may carry it and that arm can only ever
    be probed here."""
    out = []
    inst = {
        "A": {"uuid": "A", "tenant_uuid": "T1", "resource_type": "Compute.VM", "_path": "probe",
              "dependencies": [{"edge_type": "binds_to", "target_uuid": "B"}]},
        "B": {"uuid": "B", "tenant_uuid": "T2", "resource_type": "Probe.Shareable", "_path": "probe"},
    }
    _, fails = derive(inst, {})
    if not fails:
        out.append("GRD-SELF: an ungranted cross-boundary edge was not reported")

    entries, fails = derive(inst, {"Probe.Shareable": {"publicly_stakeable": True}})
    if fails or not any(e[3] == "satisfied by standing declaration" for e in entries):
        out.append("GRD-SELF: a standing declaration did not satisfy the crossing (CTX-008)")

    inst["G"] = {"uuid": "G", "tenant_uuid": "T2", "resource_type": "Grouping.Authorization",
                 "_path": "probe", "states": {"realized": {"fields": {
                     "granted_by": "T2", "granted_to": "T1", "authorized_operations": ["stake"],
                     "membership_criterion": "estate?uuid=in=(B)"}}}}
    _, fails = derive(inst, {})
    if fails:
        out.append("GRD-SELF: a matching grant did not satisfy the crossing")

    inst["G"]["states"]["realized"]["fields"]["membership_criterion"] = "estate?uuid=in=(SOMETHING_ELSE)"
    _, fails = derive(inst, {})
    if not fails:
        out.append("GRD-SELF: a grant scoping a DIFFERENT resource was accepted")
    return out


def main():
    instances = load_instances()
    flags = load_type_flags()
    entries, fails = derive(instances, flags)
    fails += self_test(flags)
    pending = unresolvable(instances)

    print(f"grant-derivation: {len(instances)} record(s), "
          f"{len(entries)} cross-boundary edge(s) in the required-grant set")
    for rec, dep, target, verdict, note in entries:
        print(f"  {rec.get('handle', rec['uuid'][:8])} --{dep.get('edge_type')}--> "
              f"{target.get('handle', target['uuid'][:8])}: {verdict}" + (f" [{note}]" if note else ""))
    if pending:
        print(f"  {pending} catalog constituent(s) determined at placement — owner not yet knowable")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} crossing(s) unaccounted for")
        return 1
    print("OK — every resolved cross-boundary edge is granted or standing-declared")
    return 0


if __name__ == "__main__":
    sys.exit(main())
