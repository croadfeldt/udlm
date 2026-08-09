#!/usr/bin/env python3
"""The structural invariants — the six rules that may never be bent, four of them checkable.

`universal-groups.md` §2.3 calls GRP-INV-001..006 non-overridable: true regardless of profile,
enforcement model, or anyone's preference. **Nothing checked any of them.** They were the most
load-bearing rules in the model and the least defended, and until `Grouping.Tenant` existed they
were not even expressible — nothing in the data said which groupings were tenants.

  GRP-INV-001  a record's tenant resolves to a real tenant, and to exactly one. The "exactly one"
               half is structural (the field is scalar); this checks the other half — that it points
               at something that IS a tenant rather than at a label, a policy collection, or nothing.
  GRP-INV-002  a `contained_by` edge may not cross a tenant boundary. The parts of one thing may not
               span two owners. Anything genuinely cross-tenant is `binds_to` or `references` — a
               stake in someone else's resource, never a part of yours.
  GRP-INV-005  grouping nesting is acyclic.
  GRP-INV-006  a grouping is not its own parent. Formally the one-cycle case of 005, kept separate
               because the rule is, and because a self-parent is the one a typo produces.

**Not checkable here, and why.** GRP-INV-003 (destroying a parent requires resolving its children
first) is a lifecycle act, not a property of a record at rest — control-plane. GRP-INV-004 (a
resource in a child tenant belongs to the child, never the parent) needs to know which tenant a
resource *should* have belonged to, which no record states; a record naming the parent is
indistinguishable from one that correctly belongs to it.

**Bindable (#434).** `evaluate(record, index)` judges ONE record against the resolved estate, so a
must-reject case can be handed to it directly without writing files into the tree mid-run. The
tree-walk below is a thin loop over it. That is the convention a gate needs to be usable by the
negative corpus, and gates that can only reason across the whole tree cannot follow it.

Exit 0 = every invariant holds; 1 = at least one does not.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INSTANCE_ROOTS = [os.path.join(ROOT, "registry", "examples"),
                  os.path.join(ROOT, "registry", "instances")]
TENANT_TYPE = "Grouping.Tenant"


def _fields(rec):
    st = rec.get("states") or {}
    for name in ("realized", "requested", "intent"):
        f = (st.get(name) or {}).get("fields")
        if f:
            return f
    return {}


def load_index():
    """uuid -> record, over the shipped estate. must-reject cases are excluded: they are inputs a
    case hands in deliberately, not part of the estate being judged."""
    idx = {}
    for root in INSTANCE_ROOTS:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            if "must-reject" in p.split(os.sep) or os.sep + "classes" + os.sep in p:
                continue
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            for d in docs:
                if isinstance(d, dict) and d.get("uuid"):
                    d.setdefault("_path", os.path.relpath(p, ROOT))
                    idx[d["uuid"]] = d
    return idx


def evaluate(record, index):
    """Judge ONE record. Returns error strings; empty means it holds."""
    errs = []
    who = record.get("handle") or (record.get("uuid") or "?")[:8]

    tid = record.get("tenant_uuid")
    if tid:
        t = index.get(tid)
        if t is None:
            errs.append(f"GRP-INV-001 {who}: tenant_uuid {tid[:8]} resolves to no record")
        elif t.get("resource_type") != TENANT_TYPE:
            errs.append(f"GRP-INV-001 {who}: tenant_uuid points at a "
                        f"{t.get('resource_type')!r}, which is not a {TENANT_TYPE} — a record must "
                        f"belong to a tenant, not to a grouping that merely collects things")

    for dep in record.get("dependencies") or []:
        if dep.get("edge_type") != "contained_by":
            continue                      # binds_to / references are how a crossing is legal
        tgt = index.get(dep.get("target_uuid"))
        if tgt is None or not tid:
            continue
        if tgt.get("tenant_uuid") and tgt["tenant_uuid"] != tid:
            errs.append(f"GRP-INV-002 {who}: contained_by edge to "
                        f"{tgt.get('handle', dep['target_uuid'][:8])}, owned by a different tenant. "
                        f"The parts of one thing may not span two owners — a cross-tenant "
                        f"relationship is binds_to or references, behind an authorization")

    if record.get("resource_type") == TENANT_TYPE:
        seen, cur, hops = {record["uuid"]}, _fields(record).get("parent_group_uuid"), 0
        if cur == record["uuid"]:
            errs.append(f"GRP-INV-006 {who}: is its own parent")
            cur = None
        while cur and hops < 64:
            if cur in seen:
                errs.append(f"GRP-INV-005 {who}: grouping nesting forms a cycle through "
                            f"{cur[:8]} — nesting must be acyclic")
                break
            seen.add(cur)
            nxt = index.get(cur)
            cur = _fields(nxt).get("parent_group_uuid") if nxt else None
            hops += 1
    return errs


def main():
    index = load_index()
    fails, checked = [], 0
    for rec in index.values():
        if not rec.get("tenant_uuid") and rec.get("resource_type") != TENANT_TYPE:
            continue
        checked += 1
        fails += evaluate(rec, index)

    # self-test: every arm must be able to fire, or the gate only proves the walk ran
    probe_idx = {
        "T": {"uuid": "T", "resource_type": TENANT_TYPE, "tenant_uuid": "T"},
        "L": {"uuid": "L", "resource_type": "Grouping", "tenant_uuid": "T"},
        "X": {"uuid": "X", "resource_type": "Compute.VM", "tenant_uuid": "T2"},
    }
    arms = {
        "GRP-INV-001": evaluate({"uuid": "A", "handle": "a", "tenant_uuid": "L"}, probe_idx),
        "GRP-INV-002": evaluate({"uuid": "B", "handle": "b", "tenant_uuid": "T",
                                 "dependencies": [{"edge_type": "contained_by", "target_uuid": "X"}]},
                                probe_idx),
        "GRP-INV-006": evaluate({"uuid": "C", "handle": "c", "resource_type": TENANT_TYPE,
                                 "states": {"realized": {"fields": {"parent_group_uuid": "C"}}}},
                                probe_idx),
    }
    for rule, got in arms.items():
        if not any(rule in e for e in got):
            print(f"FAIL [GRP-SELF] {rule} did not fire on a planted violation")
            fails.append("self-test")

    print(f"group-invariants: {checked} record(s) judged against GRP-INV-001/002/005/006 "
          f"({len(index)} in the estate)")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} invariant violation(s)")
        return 1
    print("OK — the structural invariants hold")
    return 0


if __name__ == "__main__":
    sys.exit(main())
