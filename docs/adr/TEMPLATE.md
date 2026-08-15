# UDLM ADR-NNN: <a short noun phrase — what was decided, not what was discussed>

**Status:** Proposed (<who> upstream) — pending engineering ratification (#217); decided <YYYY-MM-DD>
**Realized by:** _not yet_ — decided, no machine surface.
**Date:** <YYYY-MM-DD>
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited
once with what it settles — never a bare number. `ADR-008 — the substrate/implementation boundary test`, not `see ADR-008`.

---

## Context

The forces at play, and what made a decision necessary. Written so someone arriving in a year
understands the pressure without having been in the room.

State the problem in plain terms before any schema detail. A reader who cannot restate the problem
will not be able to judge the decision.

## Decision

What was decided, in the present tense: *"A composition is a record until someone offers it."* One
decision per record where possible; a record settling four things is four records someone will have
to untangle later.

## Alternatives considered

What else was on the table and why it lost. This is the section that stops the same option being
re-proposed every six months — and the one most often skipped, which is why it is most often
re-litigated.

## Consequences

What becomes easier, and what becomes harder. Both halves: a record listing only benefits is a
pitch, not a decision record.

## Data · Policy · Provider

Required by SPEC-DESIGN §29 — decompose the decision across the triad. What the DATA model carries,
what POLICY decides, what a PROVIDER does. If a decision has nothing to say about one of them, say
so; an empty row is information.

**Peer test (ADR-008):** could a conformant peer implement this differently and still be valid? Yes
→ it belongs to the implementation. No → it belongs to the substrate.

---

## How to use this file

**Status is agreement, never implementation.** `Proposed` · `Accepted` · `Rejected` · `Deprecated` ·
`Superseded by ADR-N`. The standard sequence is propose → accept → implement, and a status field
that also tried to report implementation would be answering two questions with one value. See
`docs/adr/README.md`.

**`Realized by` is where the decision lives** — the schemas, contracts, vocabularies or gates that
carry it, or an explicit `_not yet_`. Silence is the only unacceptable answer, because silence and
"nobody checked" are indistinguishable. Checked by `tests/check_adr_realization.py`.

**Once `Accepted`, the record is immutable.** A change is a NEW record that supersedes this one, and
this one gains `Superseded by ADR-N`. Never an edit — the point of a decision record is that it
still says what was decided at the time, including where that turned out to be wrong.

**Section names are a guide, not a schema.** Several existing records use `## The problem` for
Context or `## What this buys` for Consequences and read perfectly well. What matters is that the
forces, the decision, the alternatives and the consequences are all present.
