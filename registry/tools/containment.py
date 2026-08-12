#!/usr/bin/env python3
"""Constraint-clause containment — one routine, both tiers.

The same question is asked at two places in the model, and it is the same question:

    class tier   is this Provider Class's `supports` inside its parent's?   (a GATE — a Class is
                                                                             UDLM's own artifact)
    layer  tier   is this layer's `limits` inside its ancestors' envelopes?  (a POLICY — a layer is
                                                                             the estate's config)

Different authority, identical math. Two implementations would drift, and the drift would be
invisible: each would look right in its own file.

WHY THE CLAUSES ARE DATA. `when` is equality over scalars, deliberately. Given operators, "is the
child inside the parent" is undecidable in general — so the envelope would be a comment rather than
a contract. Everything here relies on that restriction.

WHY THIS RETURNS A BINDING CLAUSE, NOT A BOOLEAN. `LAY-010` requires a denial to name the layer that
bound it, the clause, and its reason. Extension chains are deep and multi-parent by design, so at
any real depth "value not permitted" cannot be acted on: the reader cannot tell which of a dozen
ancestors objected. A checker that returns True/False cannot produce that answer afterwards — the
information is gone by the time anyone needs it — so it is returned in the first place.
"""
import re

_UNIT = {"": 1, "K": 10**3, "M": 10**6, "G": 10**9, "T": 10**12, "P": 10**15,
         "Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "Pi": 2**50,
         "m": 1e-3, "u": 1e-6, "n": 1e-9}
_QTY = re.compile(r"^[0-9]+(\.[0-9]+)?(m|u|n|K|M|G|T|P|Ki|Mi|Gi|Ti|Pi)?B?$")


def magnitude(v):
    """A comparable magnitude for a bound — a plain number, or a Quantity string normalised to a
    base unit. None when it is neither: a bound we cannot compare is REPORTED, never silently
    treated as satisfied."""
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if not isinstance(v, str) or not _QTY.match(v):
        return None
    m = re.match(r"^([0-9]+(?:\.[0-9]+)?)(.*)$", v)
    unit = m.group(2)
    unit = "" if unit == "B" else unit.rstrip("B")
    return float(m.group(1)) * _UNIT.get(unit, 1)


def clause_applies(clause, selections):
    """Does this clause's `when` hold for the given selections?

    A clause with no `when` always applies. Equality only — and an UNKNOWN key does not match: if
    the selection was never made, a clause conditioned on it cannot be known to apply, and assuming
    it does not is the safe direction only for VALUE checks. For containment between envelopes the
    caller passes selections=None, which treats every clause as applicable — because a child must
    fit its parent under every context the parent could be evaluated in, not merely today's."""
    when = clause.get("when")
    if not when:
        return True
    if selections is None:
        return True
    return all(str(selections.get(k)) == str(v) for k, v in when.items())


def value_binding_clause(value, clauses, selections=None):
    """The clause that REFUSES `value`, or None if some applicable clause permits it.

    The union of applicable clauses is the permitted set, so a value is permitted if ANY of them
    accepts it. When none does, the returned clause is the one a human should be shown: the nearest
    miss (smallest distance to its bound), because "you asked for 512Gi and the ceiling is 384Gi" is
    actionable where "no clause matched" is not."""
    applicable = [c for c in clauses if clause_applies(c, selections)]
    if not applicable:
        return None                       # nothing bounds this field in this context
    best, best_dist = None, None
    for c in applicable:
        vals = c.get("values")
        if vals is not None and any(str(v) == str(value) for v in vals):
            return None
        lo, hi, step = magnitude(c.get("min")), magnitude(c.get("max")), magnitude(c.get("step"))
        mv = magnitude(value)
        if mv is None:
            if vals is None:
                # A non-comparable value against a range clause: we cannot say it fits, and we do
                # not pretend it does.
                dist = float("inf")
            else:
                dist = float("inf")
        else:
            below = lo is not None and mv < lo
            above = hi is not None and mv > hi
            offstep = (step is not None and step > 0 and lo is not None
                       and abs(((mv - lo) / step) - round((mv - lo) / step)) > 1e-9)
            if not (below or above or offstep):
                if vals is None:
                    return None
                dist = float("inf")       # clause is a discrete set and the value was not in it
            else:
                dist = (lo - mv) if below else (mv - hi) if above else 0.0
        if best_dist is None or dist < best_dist:
            best, best_dist = c, dist
    return best


def clause_inside(child, parents):
    """Is `child` contained in SOME parent clause? Returns the parent it fits, or None.

    Containment, not equality: a child may narrow freely. A parent that declares no bound at all
    contains nothing measurable, so a child range under it is a widening — that case returns None
    rather than quietly passing, because "the parent said nothing" is exactly when a child could
    otherwise invent an envelope its ancestor never granted."""
    clo, chi = magnitude(child.get("min")), magnitude(child.get("max"))
    cvals = set(map(str, child.get("values") or []))
    for p in parents:
        plo, phi = magnitude(p.get("min")), magnitude(p.get("max"))
        pvals = set(map(str, p.get("values") or []))
        if cvals:
            in_set = cvals <= pvals
            in_range = (plo is not None or phi is not None) and all(
                magnitude(v) is not None
                and (plo is None or magnitude(v) >= plo)
                and (phi is None or magnitude(v) <= phi) for v in cvals)
            if not (in_set or in_range):
                continue
        if clo is not None and plo is not None and clo < plo:
            continue
        if chi is not None and phi is not None and chi > phi:
            continue
        if chi is None and phi is not None and not cvals:
            continue                      # unbounded above under a capped parent is a widening
        if clo is None and plo is not None and not cvals:
            # Unbounded BELOW under a floored parent is a widening — but only for a RANGE child.
            # A discrete child was already checked against the parent's floor above (`in_range`),
            # so reaching here with values means it cleared it.
            continue
        if (clo is not None or chi is not None) and not pvals and plo is None and phi is None:
            continue                      # parent bounds nothing measurable
        cstep, pstep = magnitude(child.get("step")), magnitude(p.get("step"))
        if pstep and (cstep is None or abs((cstep / pstep) - round(cstep / pstep)) > 1e-9):
            continue                      # a finer step offers values the parent does not
        return p
    return None


def envelope_containment(child_clauses, parent_envelopes):
    """Every child clause must fit inside EVERY applicable ancestor envelope.

    `parent_envelopes` is a list of (source, clauses) — one per ancestor that bounds this field.

    LIMITS INTERSECT WHERE VALUES OVERRIDE, and this loop is where that lives: the child is checked
    against each ancestor separately, so satisfying a permissive ancestor never excuses violating a
    restrictive one. Merging the envelopes first and checking once would let a wide parent dissolve
    a narrow one, and permission could then be bought by extending one more layer.

    Returns [(child_clause, source, reason)] for each violation — empty when contained."""
    out = []
    for c in child_clauses:
        for source, pclauses in parent_envelopes:
            if not pclauses:
                continue                  # ancestor bounds nothing here: absent means unbounded
            if clause_inside(c, pclauses) is None:
                bound = min(pclauses, key=lambda p: (magnitude(p.get("max")) is None,
                                                     magnitude(p.get("max")) or 0))
                out.append((c, source, bound))
    return out
