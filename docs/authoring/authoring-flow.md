# How an artifact gets built — the authoring flow

**What this settles:** the path any artifact takes from an idea to a merged, CI-accepted part of the
model — for someone doing it the first time. Read this before the per-kind HOWTOs; it's the map they
sit inside. The one promise: **follow the path and the gates pass; skip a step and a gate names it.**

**In one breath.** You start not by writing a schema but by checking whether the model *already* covers
your need. If it doesn't, you author the artifact, give it a worked example that validates against its
own schema, exercise it with 2–3 use cases (a success, a refusal, and a compose), place it in a flow, and
declare that story in a `coverage:` block. Then you run the gates — the same ones CI runs — and fix what
they name. Nothing merges without a person; the gates make the person's job about judgment, not
bookkeeping.

## The flow

```mermaid
flowchart TD
    A[An idea: the model should express X] --> B{Does something existing\ncompose to cover X?\n(classification, profiles, references,\nedges, an existing Class)}
    B -->|yes| B1[Extend it — no new artifact.\nThat is the T7 discipline, and a win]
    B -->|no| C[Pick the artifact kind\n→ its HOWTO in this folder]
    C --> D[Author the artifact\nagainst its schema in registry/*.schema.json]
    D --> E[Add a worked example\nthat validates against its own schema]
    E --> F[Write 2–3 use cases\npositive · negative/refusal · composite]
    F --> G[Place it in a flow\n(a lifecycle doc with the failure branch shown)]
    G --> H[Declare the story:\ncoverage: { use_cases, flows }]
    H --> I{Run the gates\n./scripts/signoff.sh + the full validate.yml set}
    I -->|a gate names a gap| J[Fix exactly what it named\n→ back to the step it points at]
    J --> I
    I -->|all green| K[Open a subject-scoped PR\n→ a human reviews judgment, not bookkeeping]
    K --> L[Merged: part of the model,\nand CI keeps it complete forever]
```

## Why the order is what it is

- **Reduce before you build (B).** The first question is never "how do I write this schema" — it's "is a
  new artifact even warranted." Most needs are met by extending what exists. A new mechanism has to earn
  its place by showing nothing composed to cover it (review-sweep tenet T7). This is the step newcomers
  skip and reviewers catch.
- **Example before use cases (E→F).** The example is the first proof the artifact is real — it either
  validates against its own schema or it doesn't. Getting it valid forces you to understand the shape
  before you write prose about it.
- **The refusal is not optional (F).** A type that only has a happy-path use case is half-specified. The
  *negative* — what the system must refuse, and how it must say so — is where the real contract lives.
  Every must-reject use case carries the same refusal contract: typed, actionable, whole, non-leaking,
  auditable.
- **Coverage is a declaration, not a discovery (H).** You *state* which use cases and flows exercise the
  artifact, in a `coverage:` block on it. The gate then checks that what you named actually resolves and
  references the artifact — so the story can't silently drift from the thing.

## The gates, and what each is really asking

| The gate asks | You satisfy it by | Enforced by |
|---|---|---|
| Is it valid against its schema? | authoring to `registry/*.schema.json` | `validate_registry.py`, `validate.py` |
| Is its identity honest? | new uuid for new; version bump for a change | `check_identity_integrity.py` (ADR-051) |
| Does it ship a valid example? | one in `spec.examples`, validated | `check_spec_examples.py` (EXG-001/002) |
| Does it travel with its story? | a `coverage:` block that resolves + references it | `spec_coverage.py` (COV-001/002/004) |
| Do its use cases speak the model's vocabulary? | reusing the agreed dimensions + personas | `check_uc_dimensions.py`, `check_uc_personas.py` |
| Does the type reject malformed intent? | a discriminating schema | `fuzz_type_specs.py` |

## What this flow does not decide

Whether your artifact is a *good idea* — that's the human review and, over time, the DAV analysis measuring
whether the corpus is coherent against the model. The gates prove your artifact is complete, valid, and
its story hangs together. They cannot prove it should exist. That judgment stays with the reviewer — which
is exactly why the gates handle the bookkeeping, so the reviewer can spend attention on the decision.

> **Next:** pick your kind in [`README.md`](README.md) → its HOWTO. Reviewing an artifact instead of
> authoring one? See [`../reviewing.md`](../reviewing.md). Building a system on the model? See
> [`../consuming.md`](../consuming.md).
