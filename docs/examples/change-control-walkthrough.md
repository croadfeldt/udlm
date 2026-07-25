# Worked example: one class change, three change-management regimes

**What this settles:** how change control weaves into class updates — the mechanisms and
policies that decide *when* and *under what ceremony* a change adopted upstream actually
reaches an organization's estate and its downstream records. ADR-045 settled the mechanics
(pins, debt, atomic recompilation) and ADR-046 the evidence (blue/green promotion); this
walkthrough adds the temporal layer: change windows, ceremonies, freezes, and orchestration,
varied across three estates that share one registry. Every section is backed by a corpus case
(`use-cases/change-control/`), and those cases ride every normal analysis run. The contracts
here are **proposed pending the change-control ADR** — this document and its use cases are the
corpus-first input to that ruling.

The running example: the maintainer adds a new optional element — say `memory.hugepages` — to
the Compute Base Class. Upstream this is one atomic change: descendants regenerate, gates
re-prove them, and the change record carries the classification (**additive**) and the
computed blast radius. Then it meets three very different estates.

## The principle: policy decides the calendar, evidence decides the outcome

An estate's change-management policy is a declared artifact (a Policy object, same machinery
as every other policy), not a wiki page. It branches on the **change class** the upstream
record already carries — additive or breaking — and declares, per class: the adoption mode
(automatic, windowed, full ceremony), the gates (evidence, approval, verification), and the
schedule (windows, freezes, expedite paths). Two rules hold everywhere:

- **Scheduling gates control *when*; evidence gates control *whether*.** An expedite clause
  can compress the calendar; nothing can waive the blue/green evidence for a breaking change.
- **Waiting is visible.** From the moment an upstream change is classified, every estate that
  hasn't adopted it shows it as debt — queued, windowed, or frozen, each typed distinctly. An
  estate that is behind is always *provably on-policy* behind, never silently stale.

## Estate 1 — development: continuous adoption (UC-001)

The dev estate's policy says: additive changes adopt automatically at the nightly sync;
breaking changes wait for a human. `hugepages` arrives overnight — the estate re-pins, its
Compute.* records regenerate in the same orchestrated run, and the adoption record names the
policy clause that authorized it. Nobody was asked, because the decision was made once, in the
policy, instead of once per change.

## Estate 2 — production: windows and ceremony (UC-002, UC-003, UC-004, UC-008)

The prod estate's policy says: *all* class adoptions execute only inside the Saturday
maintenance window; breaking changes additionally require blue/green evidence, a named
approval, and post-adoption verification, in that order. `hugepages` (additive) lands upstream
on Tuesday: the debt list shows it immediately; Saturday's orchestrated job adopts it — and the
job must fit the window whole or defer whole, never straddle. A breaking change runs the full
ceremony: evidence → approval → window → verify → debt closes, one recorded trail, halting at
the first unmet gate. An operator who tries to re-pin on Tuesday afternoon is refused — typed
as a window violation, naming the policy clause, the next window, and the expedite path.

Inside the estate, propagation itself is ordered: the adoption job derives its update sequence
from the estate's own dependency edges (the same graph that derives shutdown order), updates
in batches with per-batch verification, and on a failed batch halts with a recorded, resumable
partial-adoption state. A fleet is never rewritten unordered.

## Estate 3 — regulated: freezes and break-glass (UC-006, UC-007)

The regulated estate adds two clauses. A **freeze** (its audit period) suspends every adoption
path including automatic ones; upstream changes accumulate as queued debt, ordered and typed
distinctly from ordinary lag, and drain in arrival order under normal gates when the freeze
lifts — so a quarter of silence is provably policy, not neglect. And an **expedite** clause is
the sanctioned exception for the security fix that cannot wait: elevated approver, named
justification, flagged audit record — and the evidence gate untouched, because break-glass
compresses schedules, never proof.

## Across estates — the staged rollout (UC-005)

The three estates compose into a rollout chain by policy alone: staging's policy names dev's
clean soak evidence as a precondition; production's names staging's. A breaking change
therefore *cannot reach* production before it has survived two earlier estates — and a failure
at staging halts production automatically, because the chain is declared topology, not a
runbook someone remembers to follow. The full rollout reads end-to-end from three linked
adoption trails.

## The mechanisms this asks of the model (the candidate ADR surface)

Each is an extension of something that already exists, not a new subsystem: the
change-management policy as a Policy object branching on the upstream change record's
classification; window/freeze/expedite as dated policy clauses the orchestration evaluates;
adoption runs as Process-family jobs (change management is itself automation intent — the same
class system it serves); queued/windowed/frozen as typed debt states extending ADR-045's debt
list; soak/adoption evidence as typed records ADR-046's promotion evidence already shapes; and
the adoption trail as audit records. What is genuinely new is small and nameable: the policy
clause vocabulary (window, freeze, expedite, precondition-on-evidence) and the typed debt
states. That is the decision surface for the change-control ADR.
