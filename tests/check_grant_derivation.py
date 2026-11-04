#!/usr/bin/env python3
"""CTX-010 — a cross-tenant edge states its target's tenant and names its grant; both are verified.

CTX-005 — the required-grant set is listed as a PREVIEW, so a consumer learns what to ask for first.

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

  CTX-010  a resolved cross-tenant edge states target_tenant_uuid and names an authorization_ref that
           exists, is granted by the target's tenant to the holder and scopes the target, or its
           target's type is a standing declaration (CTX-008). Anything else is a finding.

Exit 0 = every cross-boundary edge is accounted for; 1 = at least one is not.
"""
import glob
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "registry", "tools"))
import entity_view as _ev  # the merged read model, computed from per-state records (ruling 071)
import re

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
    """uuid -> the entity view (registry/tools/entity_view.py): per-state records fold by entity_uuid,
    a document already in the folded shape is itself. Gate logic reads the view."""
    out = {}
    for u, v in _ev.load_views(INSTANCE_ROOTS).items():
        if v.get("tenant_uuid"):
            out[u] = v
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
    """Verify every cross-tenant edge's stated tenancy and grant (CTX-010), and list the required-grant
    set (CTX-005) as a preview. One pass, no side effects.

    Nothing here is inferred. The edge states its target's tenant and names its grant; the gate checks
    each statement against the records. A grant that merely fits is not a grant: an edge naming none is
    refused even when one exists, because "who authorized this?" must be read, not searched for."""
    entries, fails = [], []

    def refuse(rec, dep, target, verdict, why):
        entries.append((rec, dep, target, verdict, None))
        fails.append(f"CTX-010 {rec['_path']}: {rec.get('handle', rec['uuid'][:8])} "
                     f"({rec.get('resource_type')}) holds a {dep.get('edge_type')} edge to "
                     f"{target.get('handle', target['uuid'][:8])} owned by {target['tenant_uuid'][:8]}: {why}")

    for rec in instances.values():
        holder = rec["tenant_uuid"]
        for dep in rec.get("dependencies") or []:
            tgt_uuid = dep.get("target_uuid")
            if not tgt_uuid:
                continue
            target = instances.get(tgt_uuid)
            if target is None:
                continue                       # off-estate reference; nothing to verify against
            owner = target["tenant_uuid"]
            if owner == holder:
                continue                       # same tenant: no boundary crossed
            stated = dep.get("target_tenant_uuid")
            if not stated:
                refuse(rec, dep, target, "REFUSED: tenancy not stated",
                       "the edge crosses a tenant boundary but states no target_tenant_uuid. "
                       "Tenancy is recorded, never looked up.")
                continue
            if stated != owner:
                refuse(rec, dep, target, "REFUSED: tenancy misstated",
                       f"the edge states target_tenant_uuid {stated[:8]}, but the target belongs to {owner[:8]}.")
                continue
            f = flags.get(target.get("resource_type")) or {}
            if f.get("publicly_stakeable") or f.get("publicly_allocatable"):
                entries.append((rec, dep, target, "satisfied by standing declaration", None))
                continue
            ref = dep.get("authorization_ref")
            if not ref:
                refuse(rec, dep, target, "REFUSED: no grant named",
                       "the edge names no authorization_ref. A cross-tenant edge names the grant that "
                       "allows it; the gate never searches for one.")
                continue
            grant = instances.get(ref)
            if grant is None or grant.get("resource_type") != "Grouping.Authorization":
                refuse(rec, dep, target, "REFUSED: named grant not found",
                       f"authorization_ref {ref[:8]} is not a Grouping.Authorization this estate holds.")
                continue
            af = _fields(grant)
            if af.get("granted_by") != owner or af.get("granted_to") != holder:
                refuse(rec, dep, target, "REFUSED: named grant does not match",
                       f"authorization {ref[:8]} is granted by {str(af.get('granted_by'))[:8]} to "
                       f"{str(af.get('granted_to'))[:8]}, not by the target's tenant to this holder.")
                continue
            covered, evaluable = scopes(af, tgt_uuid)
            if not evaluable:
                refuse(rec, dep, target, "REFUSED: grant scope is not an explicit set",
                       f"authorization {ref[:8]} scopes by a filter, not an explicit uuid set. A grant names "
                       f"what it covers (#723).")
                continue
            if not covered:
                refuse(rec, dep, target, "REFUSED: named grant does not cover the target",
                       f"authorization {ref[:8]} does not scope this target.")
                continue
            entries.append((rec, dep, target, "satisfied by the named grant",
                            f"{ref[:8]} ops={af.get('authorized_operations')} "
                            f"until={af.get('expires_at') or 'unbounded'}"
))
    return entries, fails


def unresolvable(instances):
    """Catalog constituents whose owner is decided at placement — counted, never dropped."""
    n = 0
    for rec in instances.values():
        if rec.get("record_type") == "catalog_item":
            n += sum(1 for c in rec.get("constituents") or [] if c.get("provided_by") == "external")
    return n


def self_test(flags):
    """Arms with no shipped subject. `publicly_stakeable` is an ORG's declaration (rule 42: UDLM
    facilitates, it does not dictate), so no registry type carries it and that arm is probed here."""
    out = []

    def probe(extra, criterion="estate?uuid=in=(B)"):
        return {
            "A": {"uuid": "A", "tenant_uuid": "T1", "resource_type": "Machine.VM", "_path": "probe",
                  "dependencies": [dict({"edge_type": "binds_to", "target_uuid": "B"}, **extra)]},
            "B": {"uuid": "B", "tenant_uuid": "T2", "resource_type": "Probe.Shareable", "_path": "probe"},
            "G": {"uuid": "G", "tenant_uuid": "T2", "resource_type": "Grouping.Authorization", "_path": "probe",
                  "states": {"realized": {"fields": {"granted_by": "T2", "granted_to": "T1",
                                                     "authorized_operations": ["stake"],
                                                     "membership_criterion": criterion}}}},
        }

    def refused(extra, flg=None, **kw):
        return bool(derive(probe(extra, **kw), flg or {})[1])

    ok = {"target_tenant_uuid": "T2", "authorization_ref": "G"}
    if refused(ok):
        out.append("CTX-SELF: an edge naming a matching grant was refused")
    if not refused({"authorization_ref": "G"}):
        out.append("CTX-SELF: an edge stating no target_tenant_uuid was accepted")
    if not refused({"target_tenant_uuid": "T9", "authorization_ref": "G"}):
        out.append("CTX-SELF: an edge misstating its target's tenant was accepted")
    if not refused({"target_tenant_uuid": "T2"}):
        out.append("CTX-SELF: an edge naming no grant was accepted because one exists (inferred)")
    if not refused({"target_tenant_uuid": "T2", "authorization_ref": "NOPE"}):
        out.append("CTX-SELF: an edge naming a grant that does not exist was accepted")
    if not refused(ok, criterion="estate?uuid=in=(OTHER)"):
        out.append("CTX-SELF: a named grant scoping a DIFFERENT resource was accepted")
    if not refused(ok, criterion="estate?labels.concern==payments"):
        out.append("CTX-SELF: a named grant scoped by a label filter, not an explicit set, was accepted")
    if refused({"target_tenant_uuid": "T2"}, {"Probe.Shareable": {"publicly_stakeable": True}}):
        out.append("CTX-SELF: a standing declaration did not satisfy the crossing (CTX-008)")
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
