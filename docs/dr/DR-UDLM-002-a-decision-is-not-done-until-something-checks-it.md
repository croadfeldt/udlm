# DR-UDLM-002: A decision is not done until something checks it

**Status:** Proposed
**Realized by:** _not yet_ — decided, no machine surface.
**Type:** Decision Record — a project/process decision (`docs/spec/foundations/knowledge-family.md` §4.5); architecture decisions are ADRs (`../adr/`)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** `registry/rule-id-registry.yaml` (one prefix, one family, one home — the mechanism this leans on) · `CONFORMANCE.md` §6 (the wire checklist, and the audit that produced most of the evidence below) · [ADR-060](../adr/ADR-060-findings-are-sealed-interpretations.md) (policies dictate, the substrate enables — the boundary this borrows for defaults).

## Context

The spec was outrunning the machinery that holds it honest, and the gap was invisible because nothing measured it.

Measured 2026-08-08, across `docs/spec/` and `CONFORMANCE.md`:

| | |
|---|---|
| normative statements (MUST / SHALL / REQUIRED) | **306** |
| inside a numbered rule row | **52** |
| loose in prose | **254 (83%)** |
| rule families with any gate citing them | **19 of 389 rule IDs** |

Two consequences followed, both observed repeatedly rather than theorised:

**Requirements that nothing enforces.** `OWN-007` — *"the ownership model for a resource type is declared in the Resource Type Specification"* — was normative from 0.1 and named a field that existed in no schema. Same for `publicly_stakeable` (cited by `CTX-001`), and for the handle grammar (`WIR-003`), stated in `identifier-scheme.md` and enforced by none of the nine schemas carrying a handle.

**The same requirement written twice, in different words, under different identities.** `REL-010` and `GRP-INV-002` both said constituent relationships may not cross a tenant boundary; the gate enforced one name and the document told readers to cite the other. `Composite Service` and `Template` named one tier. The "Priority Schema" in prose and `precedence_class`/`precedence_order` in the schema describe two different merge mechanisms for one job.

The through-line is not carelessness. **Every one of these was written down somewhere, correctly, and could not be found from where a reader would look.** The problem is retrieval, not authorship — and a rule nothing cites and nothing checks is indistinguishable from a rule nobody wrote.

## Decision

### 1. Definition of done: rule · schema · gate · example

A decision resolves when each of the four is present **or explicitly marked not-applicable with a reason**. Not "the prose is written."

The four are not ceremony; each closes a specific failure seen above. The **rule** gives the requirement an identity so it can be cited. The **schema** gives it a place in the data, so a record can carry the answer. The **gate** makes it fail when violated. The **example** proves the gate has a subject — a gate whose only cases are its own self-tests proves the code runs, not that the model holds.

"Not applicable, because…" is a first-class outcome. Most requirements bind a control plane or a wire exchange and cannot be checked in this repository; saying so is the point, because it separates *cannot* from *has not*.

### 2. A rule declares who it binds

Every rule states its conformance target: **`udlm-artifact`** (checkable against something in this repository), **`wire`** (checkable against a message an implementation emits), or **`runtime`** (checkable only against a running implementation over time).

Without it, "389 rules, 19 gated" reads as negligence. With it, the number that matters appears: of `CONFORMANCE.md` §6's 37 requirements, **8 are artifact-testable** and 29 need a live peer. That single number redirected the whole conformance programme — the in-repo corpus can reach 8, and no amount of corpus work reaches the rest.

First applied in §6; the other families are backfilled as they are touched, not in a sweep.

### 3. Where a source document carries its own conformance list, the consolidating section may not be shorter than it

`CONFORMANCE.md` §6 claims to consolidate the MUSTs of the contracts it links. Audited, five of eight areas were short: Errors carried 4 of 9, Retries 5 of 7, Rate limits 4 of 7, Events 3 of 7, Schema sharing 5 of 7.

The missing ones were not narration. Among them: *"neither `type`, `status`, `detail`, nor response timing varies on the existence of an out-of-scope target"* — the 403-over-404 posture. **An implementation conforming to §6 as it stood would have shipped an existence oracle and believed itself compliant.**

`tests/check_conformance_consolidation.py` (CNS-001) enforces the floor. It is a floor, not an equality check, and says so: it catches a source document gaining a requirement while §6 does not.

### 4. Capture, do not explore

An idea raised while another piece of work is open is filed as one paragraph under the `idea` label — the problem in plain terms, why it matters, what a resolution would settle. It is not designed on the spot.

The reason is not tidiness. Nine ideas were captured in one session; each would have opened a front, and open fronts are what turned a day's work into a day's circling. Triage the queue when the current piece closes.

### 5. Problem statements are written from outside the schema

State what is wrong in the words a person would use. Keep field names, rule IDs and file paths as supporting evidence, never as the opening.

The same facts framed from inside the schema describe a chore; framed from outside they describe something obviously wrong, and only the second makes the priority self-evident. Worked pair — the same issue, before and after:

> *"cross_tenant_authorization has no schema"*
> *"Groups have no kind — a tenant is indistinguishable from a label, and a permission grant cannot be written down at all"*

Identical facts. The second exposed that it blocked three other pieces of work.

### 6. Structure from ModSpec, lifecycle from ourselves

Requirements grouped into classes, each with a conformance class, each requirement mapped to a test — that is OGC ModSpec, and adopting it costs nothing because it is a structure rather than a tool (T5: adopt by reference).

The advancement ladder is already ours and must not be re-imported: `decision-record.schema.json` states `PROPOSED → UNDER_REVIEW → CANONICAL`, and `knowledge-family.md` §4.5 already says a **testable** decision reaches CANONICAL via a validation gate. That is advancement-by-evidence, in UDLM's own vocabulary. Two vocabularies for one ladder is the defect this DR exists to prevent.

### 7. No requirements-tracing tool

Evaluated and rejected: OpenFastTrace, StrictDoc, Doorstop, Metanorma. They measure internal coverage, which no consumer of UDLM ever touches, and each is a migration of the authoring surface.

Revisit only if the conformance suite exists and traceability still hurts. The measurement that made this decision — *which rules are cited by a gate* — is a grep, and the grep is what produced the numbers above.

### 8. DAV is evidence, not infrastructure

DAV is the only implementation of the Knowledge family, so it is the evidence base for advancing those rules. It must never become spec tooling: the case study rules that *"UDLM does not depend on DAV"*, and a CI gate cannot depend on a running console.

A console **over** the coverage data is fine later. The gate emits; DAV visualises. Never the reverse.

## Consequences

- Writing a rule costs more. That is the intent: the cost is what stops a rule being written and forgotten.
- **"Not applicable" must stay honest.** The escape hatch is the obvious way to defeat this, and the only defence is that the reason is written down and reviewable.
- The 254 loose normative statements are **not** swept. They are numbered where a requirement is peer-facing and touched anyway. A sweep would produce 254 rulings indistinguishable from 254 guesses — the same reason `ownership_model` was declared on five types and not on 37.
- The gate that enforces (3) can itself go blind: it initially matched only sections titled *"Validation rules (conformance checks)"* and only counted bullets, so `event-catalog.md` — which titles its list *"System Policies"* and writes it as a table — was invisible, and §6 was carrying 3 of its 7 rules with nothing watching. **A gate reporting clean on a surface nobody has sampled by hand is not yet evidence.**

## Alternatives considered

- **A coverage ledger** — a register mapping every rule to its gate. Rejected: it would have been the tenth hand-maintained register, and the two that already exist without generation or gating (`docs/file-index.md`, the decisions register) are precisely the ones that had drifted. Coverage is derivable by grep; deriving beats recording (DRV-001).
- **Numbering all 254 loose statements at once.** Rejected as above.
- **Softening requirements that cannot currently be met** — making `conformance_test_suite_version` optional because no suite exists, or relaxing §8's MUST. Rejected: it makes the document true by lowering the bar, and hides the gap instead of closing it.
