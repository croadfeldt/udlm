# How to review a UDLM contribution — the review flow

**What this settles:** what your job is when a PR lands on the UDLM registry, and how to do it
consistently with everyone else who reviews. Read it before your first review; it makes you able to
approve or block a contribution on the standard, not on taste. The one promise: **CI proves the
artifact is complete and valid; you judge whether it should exist and whether a stranger can read it.**
Everything here is the review sweep in [`CONTRIBUTING.md`](../CONTRIBUTING.md) §"The review sweep",
turned into a procedure for the reviewer.

## The division of labor

The gates and you split the work cleanly, and the split is the whole point: the gates own the
bookkeeping so you can spend your attention on judgment.

- **Green CI has already decided the mechanical questions.** Do not re-check them by hand — if a
  gate is green, the property holds. Re-litigating a green gate wastes the author's time and yours.
- **You own the questions no gate can answer** — is this UDLM or DCM, did it reinvent something that
  already exists, should this artifact exist at all, can a newcomer read it. This is the review.
- **Nothing merges on green CI alone.** Green is the *entry* condition for review, not approval. A
  reviewer confirming the judgment checks and a maintainer merging are both still required.

## 1. What CI already guarantees — do not re-check it

When the `validate` workflow (`.github/workflows/validate.yml`) is green, every property below holds.
Read the checks list once so you recognize what you are *not* on the hook for.

| CI guarantees | So you need not verify | Gate(s) |
|---|---|---|
| **Valid by construction** — every type/instance/provider matrix validates against its meta-schema | that the JSON is well-formed or schema-conformant | `tests/validate_registry.py`, `registry/tools/validate.py` |
| **Identity is honest** — uuid frozen; a change bumps the version under the publish law; immutable records supersede, never edit | that the version bump is present and sufficient | `tests/check_identity_integrity.py` (ADR-051), `tests/ci_compat_gate.py` |
| **Spec-completeness — a spec travels with its story** — a UC, an in-spec example, and a flow, declared in a `coverage:` block that resolves | that the story *exists* and is wired to the spec | `registry/tools/spec_coverage.py` (COV-001/002), `tests/check_spec_examples.py` (EXG-001/002), `tests/check_type_standard.py` (rule 36) |
| **Vocabulary is settled** — agreed terms, dimensions, personas only; retired synonyms fail | that the words are on-charter | `tests/check_model_vocabulary.py`, `tests/check_uc_dimensions.py`, `tests/check_uc_personas.py`, `tests/check_terminology.py` |
| **Fuzz-discrimination** — every type is satisfiable *and* rejects malformed intent (dropped-required, enum-violation, wrong-type, unknown-key); composed graphs reject cycles/undeclared outputs | that the schema actually discriminates good input from bad | `registry/tools/fuzz_type_specs.py`, `tests/check_composition_hammer.py` |
| **Single source** — one rule / one definition, one home, one ID; reference, never restate | that nothing was duplicated | `tests/check_single_source.py`, `tests/check_definition_single_source.py` |

**Green CI means these hold.** If any is red, the PR is not ready for your review — the author fixes
what the gate named first. The author was told the same thing:
[`docs/authoring/authoring-flow.md`](authoring/authoring-flow.md) is the path they followed, and its
promise is "follow the path and the gates pass." You review against that path.

## 2. What only a human can judge — this is the review

The gates cannot decide any of the following. This is your checklist; a good PR has already argued
each in its *Why*, and your job is to confirm the argument holds — or name where it doesn't.

- **The boundary — is this UDLM or DCM? (ADR-008 — the peer test: could an independent conformant
  peer decide this differently and still be valid? yes → DCM/Policy, no → UDLM portable substrate).**
  This is the single most important call you make. Portable data and *declarative* constraints are
  UDLM; anything computed, negotiated, or executed is DCM. A realization mechanism smuggled into the
  portable model is a finding, however cleanly it validates. See
  [`docs/adr/ADR-008-udlm-dcm-boundary.md`](adr/ADR-008-udlm-dcm-boundary.md).
- **Reduce to existing before coining a mechanism (tenet T7 — reach for an existing mechanism before
  minting a new one).** If the PR adds a new envelope, module, or parallel type, the *Why* must show
  that nothing existing — classification, profiles, capability declaration, conformance tier,
  references, edges, an existing Class — composes to cover it. No such argument is itself the finding.
- **Adopt by reference, don't re-express (tenet T5 — adopt a credible external standard rather than
  restate it).** If the PR models something a mature standard already solves (API versioning,
  identity, RTO/RPO, health probes), it should adopt that standard or justify why not.
- **Wrap tools, don't reimplement them (tenet T8 — naturalize a mature tool as a Provider rather than
  rebuild its mechanism).** If the change has the control plane directly build/scan/sign/deploy where
  a tool already owns that mechanism, the fix is a Provider boundary, not a reimplementation.
- **Should this artifact exist at all?** The gates prove an artifact is complete; they cannot prove
  it is a good idea. If the need is already met, or the artifact is speculative with no consumer, say
  so — the strongest review often ends in "this shouldn't merge," not a list of nits.
- **Is it legible to a newcomer? (DOC-001 — write for a reader who wasn't there).** Read the prose
  cold, as if you were not in the room. Can you repeat the decision back at a whiteboard? Are internal
  working-context artifacts — session labels, private ticket numbers, colleague names — stripped? Does
  **every reference carry its gist in one line** (what it *decided*), never a bare "see ADR-NNN"? If
  you need a second document to understand this one, it fails.
- **Sizing.** One subject per PR, roughly ≤2–3k lines. If it bundles unrelated subjects or is
  oversized, ask for a split along logical boundaries — not a size-driven cut.

## 3. Reproduce the gates yourself when a result surprises you

You do not normally re-run CI — green is green. But when a result looks wrong, or you want to confirm
a fix before asking for it, run the exact same gates locally:

- **The whole sweep:** `./scripts/signoff.sh` — runs every automated gate the author was told to run
  before opening the PR, then prints the judgment checklist. Same gates as CI; procedure in
  [`docs/signoff.md`](signoff.md).
- **The CI set directly:** the checks in `.github/workflows/validate.yml`, e.g.
  `python3 registry/tools/validate.py`, `python3 tests/check_identity_integrity.py`,
  `python3 registry/tools/spec_coverage.py --check`, `python3 registry/tools/fuzz_type_specs.py`.
- **One suspect gate:** run just its `tests/check_*.py` or `registry/tools/*.py` to see the failure in
  isolation. A gate that is green locally but the PR still feels wrong is your signal that the finding
  is a judgment call from §2, not a mechanical one.

## 4. The merge norm — you raise findings, you do not rubber-stamp

**Nothing merges without the maintainer.** Your role as reviewer is to raise findings and confirm the
§2 judgment checks are satisfied — not to approve on green CI. Green is the price of admission to
review; it is never the verdict. Concretely: an all-green PR with a boundary violation (§2, ADR-008)
or an illegible spec (§2, DOC-001) is a PR you block, and green tells you nothing about either. Confirm
the judgment checks, record what you found, and leave the merge to the maintainer.

## 5. How to give feedback

A finding lands when the author sees the standard behind it, not your preference. Two rules:

- **Lead with genuine, specific appreciation for the point the PR raises** — name the actual thing it
  got right (the boundary call it navigated, the refusal case it thought through), not boilerplate
  praise. You are reviewing a colleague's work, not grading it.
- **Every finding names the tenet or gate it comes from**, so it is the standard talking, not taste.
  "This reads as a DCM realization mechanism in the portable model — ADR-008 peer test: a conformant
  peer could realize this differently" is reviewable. "I'd do this differently" is not. Cite the rule
  (ADR-008, T7, T5, T8, DOC-001, sizing) and, where it helps, the one-line gist of what it decided.

---

> **Related:** authors follow [`docs/authoring/authoring-flow.md`](authoring/authoring-flow.md) — the
> path you review against; the standards behind both live in [`CONTRIBUTING.md`](../CONTRIBUTING.md).
