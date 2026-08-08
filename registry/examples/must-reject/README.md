# must-reject — worked examples of what the model **refuses**

**Do not copy anything in this directory.** Every record here is deliberately wrong. They are kept,
versioned, and executed for the same reason the valid examples are: a rule nobody has watched fail
is a rule nobody knows still works.

## Why they exist

`registry/examples/` shows what a conformant record looks like. That proves the model *accepts* the
right things and says nothing about whether it *refuses* the wrong ones — and a gate that cannot
fail proves only that its code runs. These are the other half: the boundary, written down.

They are also the teaching half. A reader learns as much from *"this is refused, and here is
exactly why"* as from a correct record — often more, because the correct record rarely shows where
the edge is.

## The case shape

Each file declares the refusal it expects, then the record that must provoke it:

```yaml
must_reject:
  rule: OWN-008                     # the rule that refuses it
  gate: check_ownership_declaration # the check that enforces that rule
  because: >-                       # the sentence a reader needs, not a restatement of the rule
    ...
  use_case: access/…                # OPTIONAL — the narrative scenario this makes executable
record:
  …                                 # the offending record, verbatim
```

The expectation lives **in the case**, not in a manifest beside it. A manifest is a second list that
drifts from the first; a self-describing case cannot disagree with itself.

## How they run

`tests/check_must_reject.py` reads each case, hands `record` to the named gate, and fails if the
gate **accepts** it. So the corpus fails in two directions, which is the point:

- the model stops refusing something it should → the case passes when it must not
- a case stops being wrong (the rule changed, the field moved) → it silently starts passing, and the
  runner reports a case that no longer proves anything

`registry/tools/validate.py` deliberately skips this directory. These records are *inputs to a gate*,
not documents to validate — running the ordinary validator over them would report the very errors
they exist to cause.

## Relationship to `use-cases/must-reject/`

That directory holds the **scenarios** — narrative, persona-framed, describing a refusal a conformant
implementation must produce. This one holds the **executable cases**. A case cites its scenario via
`use_case:` where one exists, which is what turns "we wrote down that this must be refused" into
"something checks that it is."

`001-cross-tenant-edge-without-grant.yaml` is the first pair: the scenario was written months before
the gate that enforces it, and nothing connected them until the case did.
