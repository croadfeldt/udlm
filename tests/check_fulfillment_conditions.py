#!/usr/bin/env python3
"""A member that has not realized must say WHY, and what it is waiting on (DEP-017).

**The problem this closes.** A request that is not finished could not say whether it was stuck.
Three situations were recorded identically: waiting on something that is coming (fine, wait),
waiting on something that is not moving (someone may need to act), and never going to finish (stop
waiting). The use-case corpus has designed all of this — `blocked-transient` converges when it can,
`blocked-permanent` is refused window-independently, a dependent inherits transitively — and one
flow states outright that *"UDLM owns the refused/blocked-permanent vocabulary, the
transitive-inheritance semantics, and the root-naming obligation."* None of it was in a schema.
`status.conditions[].type` was an unconstrained string, so two implementations could spell the same
blocked state differently and neither would be wrong.

  FUL-001  a fulfillment condition uses a governed type. The family is CLOSED because its members
           carry propagation semantics — a fifth spelling is not a new condition, it is a member of
           this family nobody can act on. Caught by matching the SHAPE of the family (a `blocked`
           stem, or a near-miss of a governed term) rather than by closing the whole condition
           vocabulary, which stays open for health, recovery and provider conditions.
  FUL-002  an inherited condition names its immediate blocker. "Blocked" without a blocker is not
           actionable, and the root-naming obligation depends on it: a blocked-permanent app three
           hops from the refused volume is only useful if the volume is reachable by walking.
           `refused` is exempt — it IS the root.
  FUL-003  the walk terminates. A blocked chain that cycles, or that points at a record which does
           not exist, can never be traced to a root — which is the one thing the family exists to
           make possible.

**What this deliberately does NOT check.** Whether a transient block SHOULD have become permanent.
That is the execution pipeline's call over the convergence window (ADR-008), it depends on elapsed
time and estate state rather than on the record, and a gate asserting it would be claiming the
model can decide something only the pipeline can see.

**Bindable (#434).** `evaluate(record, index)` judges ONE record against the resolved estate.

Exit 0 = every blocked member is actionable; 1 = at least one is not.
"""
import glob
import os
import sys

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCAN_ROOTS = [os.path.join(ROOT, "registry", "examples"),
              os.path.join(ROOT, "registry", "instances")]

# The closed family (DEP-017). `refused` is the root of a chain; the other three are links in one.
INHERITED = {"blocked-transient", "blocked-permanent", "dependency-cancelled"}
FULFILLMENT = INHERITED | {"refused"}


def _tail(ref):
    return (ref or "").rstrip("/").split("/")[-1]


def _looks_like_fulfillment(t):
    """Does this condition type CLAIM to be a fulfillment condition? Matched by shape, so a
    misspelling is caught while the open condition vocabulary stays open. `blocked_by_immutable`
    (an existing, unrelated condition elsewhere in the schema) is deliberately not swept in: the
    stem is `blocked-`, hyphenated, which is how this family spells itself."""
    t = (t or "").strip()
    if t in FULFILLMENT:
        return True
    low = t.lower().replace("_", "-")
    if low.startswith("blocked-"):
        return True
    return low in {"refuse", "refused", "dependency-cancel", "dependency-cancelled",
                   "dependency-canceled", "cancelled-dependency"}


def load_index():
    """uuid -> record, plus handle-tail aliases so a blocked_on written by handle resolves."""
    idx = {}
    for root in SCAN_ROOTS:
        for p in sorted(glob.glob(os.path.join(root, "**", "*.yaml"), recursive=True)):
            if "must-reject" in p.split(os.sep):
                continue
            try:
                docs = list(yaml.safe_load_all(open(p, encoding="utf-8")))
            except Exception:
                continue
            for d in docs:
                if not isinstance(d, dict) or not d.get("uuid"):
                    continue
                d.setdefault("_path", os.path.relpath(p, ROOT))
                idx[d["uuid"]] = d
                if d.get("handle"):
                    idx.setdefault(_tail(d["handle"]), d)
    return idx


def _conditions(rec):
    """`status` is a string on some record kinds (a policy's `status: {state: active}` is an object,
    but other kinds carry a bare string), so this must not assume the object form."""
    st = rec.get("status")
    if not isinstance(st, dict):
        return []
    conds = st.get("conditions")
    return conds if isinstance(conds, list) else []


def evaluate(record, index):
    """Judge ONE record. Returns error strings; empty means it holds."""
    errs = []
    who = record.get("handle") or (record.get("uuid") or "?")[:8]

    for c in _conditions(record):
        if not isinstance(c, dict):
            continue
        t = c.get("type")
        if not _looks_like_fulfillment(t):
            continue

        if t not in FULFILLMENT:
            errs.append(f"FUL-001 {who}: condition type {t!r} is not one of the governed "
                        f"fulfillment conditions ({', '.join(sorted(FULFILLMENT))}) — the family is "
                        f"closed because its members carry propagation semantics, so a near-miss "
                        f"spelling is a state nothing knows how to inherit")
            continue

        if t in INHERITED:
            blocker = c.get("blocked_on")
            if not blocker:
                errs.append(f"FUL-002 {who}: {t} without blocked_on — 'blocked' with no blocker is "
                            f"not actionable, and the root cannot be reached by walking")
                continue

            # FUL-003 — the walk terminates and lands somewhere real.
            seen, cur, hops = {record.get("uuid")}, _tail(blocker), 0
            while cur and hops < 32:
                nxt = index.get(cur)
                if nxt is None:
                    errs.append(f"FUL-003 {who}: {t} blocked_on {cur!r}, which resolves to no "
                                f"record — a chain that cannot be walked cannot name its root")
                    break
                if nxt.get("uuid") in seen:
                    errs.append(f"FUL-003 {who}: the blocked chain cycles through {cur!r} — no "
                                f"root exists, so nothing can ever explain the block")
                    break
                seen.add(nxt.get("uuid"))
                nb = None
                for c2 in _conditions(nxt):
                    if isinstance(c2, dict) and c2.get("type") in INHERITED:
                        nb = c2.get("blocked_on")
                        break
                cur, hops = (_tail(nb) if nb else None), hops + 1
    return errs


def main():
    index = load_index()
    fails, checked = [], 0
    seen = set()
    for rec in index.values():
        if id(rec) in seen:
            continue
        seen.add(id(rec))
        if not any(_looks_like_fulfillment((c or {}).get("type"))
                   for c in _conditions(rec) if isinstance(c, dict)):
            continue
        checked += 1
        fails += evaluate(rec, index)

    # self-test: each arm must fire on a planted violation, or this only proves the walk ran.
    probe = {"R": {"uuid": "R", "handle": "root",
                   "status": {"conditions": [{"type": "blocked-transient", "blocked_on": "S"}]}},
             "S": {"uuid": "S", "handle": "s",
                   "status": {"conditions": [{"type": "blocked-transient", "blocked_on": "R"}]}}}
    arms = {
        "FUL-001": evaluate({"uuid": "A", "handle": "a", "status": {"conditions": [
            {"type": "blocked_transient"}]}}, probe),
        "FUL-002": evaluate({"uuid": "B", "handle": "b", "status": {"conditions": [
            {"type": "blocked-permanent"}]}}, probe),
        "FUL-003": evaluate({"uuid": "C", "handle": "c", "status": {"conditions": [
            {"type": "blocked-transient", "blocked_on": "ghost"}]}}, probe),
    }
    for rule, got in arms.items():
        if not any(rule in e for e in got):
            print(f"FAIL [FUL-SELF] {rule} did not fire on a planted violation")
            fails.append("self-test")
    # and the governed spellings must NOT trip the near-miss arm
    clean = evaluate({"uuid": "D", "handle": "d", "status": {"conditions": [
        {"type": "refused", "reason": "no capacity, permanently"},
        {"type": "Ready", "status": "True"}]}}, probe)
    if clean:
        print(f"FAIL [FUL-SELF] a governed `refused` + an ordinary condition were flagged: {clean}")
        fails.append("self-test")

    print(f"fulfillment-conditions: {checked} blocked member(s) judged against FUL-001/002/003 "
          f"({len(seen)} record(s) in the estate)")
    for m in fails:
        print(f"  {m}")
    if fails:
        print(f"FAILED — {len(fails)} unactionable block(s)")
        return 1
    print("OK — every blocked member names what it waits on, and every chain reaches a root")
    return 0


if __name__ == "__main__":
    sys.exit(main())
