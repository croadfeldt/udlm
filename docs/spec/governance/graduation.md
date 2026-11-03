# UDLM — Graduation: how a part earns stability

**Normative.** How a class, record schema or contract document moves from experimental to stable,
what each stage promises, and what evidence each step needs. The current stage of every part is
`registry/stability.yaml`; the gate is `tests/check_stability.py`. Decided by the maintainer on
2026-11-03 (register rows 144 and 145), after a review of ten graduation ladders
([`docs/research/udlm-graduation-research.md`](../../research/udlm-graduation-research.md)).

## 1. Three stages

| Stage | What it promises | Who may rely on it |
|---|---|---|
| **experimental** | Nothing. It may change or go in a minor version, without notice. | Nobody, beyond trying it. |
| **candidate** | A breaking change needs a register row and `supersedes`; it is never silent. | An implementation that follows the register. |
| **stable** | The 1.0 promise: nothing removed, renamed or narrowed inside the spec major; removal only by deprecation, then a major. | Any conformant peer. |

Every part starts experimental. Stable is earned, never declared: a part is stable once a running
implementation has used it and the conformance suite has judged its records (row 144).

## 2. The steps

**Experimental to candidate.** The paperwork is done and the clock starts. All of these hold:

- A worked record of the part is in `registry/examples/`. For a class that is a state record of it.
  For a schema it is an instance. For a document its examples are schema-checked or marked illustrative.

- Every rule the part carries has a must-reject case. The suite would notice if the rule stopped refusing.

- The part's text passes the readability gate with no baseline entry.

- No open issue labelled as a 1.0 blocker names the part.

- A register row proposes it and names that evidence. The row's date is `candidate_since`.

**Candidate to stable.** Use and validation have proven it. All of these hold:

- A conformance report from a running implementation names the part, with at least ten of its
  records judged. The report is kept where a reader can open it.

- The part has been a candidate for at least 90 days with no breaking change.

- The suite applies every rule the part carries, not only some.

- A register row promotes it, citing the report and the dates. The row's date is `stable_since`.

**Down a step.** A breaking change to a candidate or stable part moves it down one step, by a
register row that says why. The clock restarts.

## 3. Rules

| Rule | Statement |
|---|---|
| `GRD-001` | Every part has exactly one stage: `experimental`, `candidate` or `stable`; a document that states no rule is `reference`. The stage is read from `registry/stability.yaml`, nowhere else. |
| `GRD-002` | A part becomes a candidate only with a worked record, a must-reject case for each of its rules, readable text, no open blocker, and a register row that names them. |
| `GRD-003` | A part becomes stable only after 90 days as a candidate with no breaking change, a conformance report from a running implementation that judged at least ten of its records, and a register row that cites the report. |
| `GRD-004` | A breaking change to a candidate or stable part moves it down one stage, by a register row. The 90-day clock restarts. |
| `GRD-005` | A promotion or demotion is a register row, dated. `candidate_since` and `stable_since` in the manifest are those dates, and the gate checks the 90 days against them. |
| `GRD-006` | The 1.0 tag covers the stable parts at that time, and the maintainer decides when that set is enough (row 127, rulings 1 and 6). |

## 4. What this does not yet require

One running implementation suffices today, because one exists. When a second independent
implementation runs the suite, "two independent implementations" becomes a further promotion
step, as the IETF, W3C and TC39 require for their top level. That step is defined when it is
reachable, not before.
