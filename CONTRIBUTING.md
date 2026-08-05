# Contributing to UDLM

> **New here? Start with [`docs/working-with-udlm.md`](docs/working-with-udlm.md)** — it routes you by
> what you're here to do (author · review · consume/build · contribute). This file is the canonical
> *rules*; the guide is the *procedure* that satisfies them.

UDLM — the Universal Data Lifecycle Model — is a vendor-neutral data substrate, released under
Apache License 2.0. Both specification/prose and registry/schema contributions are welcome. Project
governance lives in `governance/` (see `federated-contribution-model.md` and `registry-governance.md`);
the design principles that bound every change are in `design-principles/` (start with `core-tenets.md`).

## Subject-scoped pull requests (default)

The default unit of contribution is **one subject per PR** — a single, complete logical change, titled
by its subject (e.g. "Add the Knowledge family to the meta-schema", "Adopt FOCUS 1.4 for cost"). Keep
PRs to roughly ≤2–3k lines; if a subject is larger, split it along logical boundaries into a sequence of
independently reviewable, subject-scoped PRs rather than forcing one oversized change. Prefer logical
boundaries over size-driven cuts, and never bundle unrelated subjects. Lead every PR description with a
short **Why** (the rationale), linking the design note or DCM ADR when one exists.

## Write for a reader who wasn't there (DOC-001 — rule #1 for every document)

Existing document formats stay exactly as they are — the ADR skeleton (header, Related,
Context / Decision / Consequences), the design-note shapes, the README conventions. This rule
governs the **prose inside them**: every document is written so a competent engineer who was
not in the room can read it cold and repeat the decision back at a whiteboard.

The standard, concretely:

- **Context sections read as narrative, not notation.** Name the problem the way the industry
  names it (the fragile-base-class problem, a lockfile, blue/green deployment), say why the
  question came up, and say what the stakes are — in ordinary sentences, before any rule-ID,
  type name, or internal shorthand appears.
- **Decisions state the rule and what it means in practice**, in that order: the readable
  sentence first ("organizations may pin exactly, and the cost is a visible debt list, not a
  fork"), the precise gate-enforceable contract language with it — both are requirements, and
  when they fight, add explanatory words; never remove precision.
- **References carry their gist** — never a bare "see ADR-NNN"; one line on what it decided.
- **Jargon is introduced, not assumed**: the first use of an internal term in a document gets
  a clause saying what it is.
- **The cold-reader test**: hand the document to someone who has never seen this repo. If they
  can say what was decided and why it matters, it passes; if they need a second document
  first, it fails.

This rule exists because the repository's precision was outrunning its readability: documents
were correct, gate-enforceable, and unreadable cold. The fix is not a summary bolted on top —
it is writing the document's own prose at this level throughout.

**Concise, clear, contextual, complete — as minimally needed (the aligning principle, the
default for every ADR and document going forward).** Cold-reader-openable and *less is more* are
one standard, not two in tension. The reconciliation: a cold reader is served by **orientation,
not re-teaching** — point to where foundational context lives, then stay on the decision.
Concretely:

- **Background belongs in foundational documents, referenced — not inlined.** A definition,
  primer, or prior decision a reader needs for context lives in its home document; this one links
  to it with a one-line gist and does not reproduce it. Every document opens with an on-ramp — a
  **"Background — read first"** block (ADRs) or a *Prerequisites / read-first* pointer (other
  docs): the foundational reading a third party needs, each cited once with what it settles,
  labeled so a reader who already has the context skips it. Foundational material is a *denoted
  reading path*, not inlined prose.
- **Complete as *minimally* needed.** Include exactly what moves the decision or the task, and cut
  everything else — including a point another section already made, and rhetorical flourish.
  Precision is never cut; restatement and emphasis are.
- **Know what the document *is* (Diátaxis).** Explanation (an ADR — *why*), reference (a
  schema/spec — *what*), how-to (a task), or tutorial (learning). Do not blend modes — an ADR
  *points to* the schema, it does not reproduce it. Mode-blending is the main source of bloat.

**How the standards align (so they are one, not competing):** DOC-001 (above) supplies the
*orientation* obligation — a cold reader must be able to repeat the decision back; the *aligning
principle* supplies the *minimality* obligation — serve that with an on-ramp and gist-carrying
references, never with inlined re-teaching or restatement. MADR/Nygard supply the ADR shape
(Context / Decision / Consequences, one decision each); Diátaxis supplies the mode discipline; and
decision records are **immutable once Accepted** — superseded, not edited. The ADR specialization
of this standard is `docs/adr/README.md` § "How these ADRs are written."

## Terminology discipline (TERM-001)

When a ruling retires a term, the term stops being available for new writing. It does not stop
being writable *about*: the sentence that records the retirement ("`gating policy` was merged into
Validation Policy") is documentation of the decision, not a use of the term. That is the whole
distinction the gate encodes — a retired term in living text is a defect; a retired term in a line
that says it was retired is the record working as intended.

This exists because retirement without enforcement decays. "Gating policy" was retired by ruling
and then regressed into a corpus file and two flow documents, caught only by the downstream repo's
copy of the check; the term list belongs upstream, where the ruling was made.

| Rule | Statement |
|---|---|
| `TERM-001` | A term retired by a ruling MUST NOT appear in the repository's living text (tracked `.md`/`.yaml`/`.json`/`.py`/`.sh` files). It MAY appear on a line that documents the change itself — the line carries a history marker (*formerly*, *renamed*, *superseded*, *retired*, *no longer*, *deprecated*, …) — or in a file exempted **for that specific term** because recording it is the file's purpose (the rules table, the agent context file, the enforcement code that refuses the retired surface, an immutable instance revision). Exemptions are per file **and** per rule: a file that legitimately names one retired term is not thereby licensed to reintroduce another. The retired-term table is `tests/check_terminology.py`; grow it with the ruling that retires a term. |

## Document the why

Every non-trivial change records its rationale, not just its diff: a design note under `docs/`, an
update to a tenet/principle in `design-principles/`, or — for a decision — a pointer to the relevant
DCM Architecture Decision Record (`architecture/adr/` in the DCM repo). Don't land a contract change
without the why; a reviewer should be able to reconstruct *why* from the repo, not just *what*.

## Registry changes (valid-by-construction)

Every registry entry MUST validate against its meta-schema — run `python3 registry/tools/validate.py`
(types, instances, and provider support matrices all pass, 0 invalid). A new resource type, instance,
or provider matrix includes a worked example that passes the gate. Version per `registry/VERSIONING.md` — including the **publish law** (ADR-051): the uuid is frozen identity and never changes; any content change bumps the version (≥ REVISION), and a published (identity, version) is never republished with different bytes. Immutable records (layers, decision records, audit records, manifests) change by superseding, never by editing.
`registry/tools/compat-check.py` enforces that the declared bump matches the change; `tests/check_identity_integrity.py` enforces the identity/publish rules.

**A new resource type also meets the base standard** — SPEC-DESIGN rule 36, the eleven expectations
(a–k): standards cross-walk with documented exclusions, typed Realized outputs or exempt-by-family,
minimal required surface, references-not-strings, declared relationship surface, lifecycle
completeness, brownfield instantiability, credential/sensitive discipline, an observability
position, a *current* worked example, and **corpus use cases** (`use-cases/`) covering the six
capability axes: usage, migration, rehydration, portability, sovereignty, tenancy. The type PR and
its use-case PR travel together; a type without its UCs is not done.

## The review sweep — what every PR is checked against

Before a PR merges it is swept against the standing checks below. The **automated** ones run in CI
(`.github/workflows/validate.yml` → `tests/check_*.py`); the **judgment** ones are the reviewer's, and a
good PR self-checks them in its *Why*. These are the recurring findings distilled into a checklist so they
are caught once, not re-litigated per PR.

**Before you open a PR or publish content, run the signoff:** `./scripts/signoff.sh` runs every automated
gate below and prints the judgment checklist. The full procedure is in [`docs/signoff.md`](docs/signoff.md).

**Automated (CI).**
- **Valid by construction** — `registry/tools/validate.py` + `tests/validate_registry.py` (`ADOPT-001`,
  `$id`↔version). Every type/instance/provider matrix passes with a worked example.
- **Rule-IDs — naming + registry (ADR-028)** — every normative rule carries a `PREFIX-NNN` ID;
  **one prefix = one family = one home file**, and the prefix is **registered in
  `registry/rule-id-registry.yaml` before use**; IDs are immutable once published (retire + supersede,
  never repoint); a family that legitimately spans files uses `additional_homes` (sanctioned
  co-definition), never a duplicate ID. `check_single_source.py` (registry-backed, CI-wired) fails on an
  unregistered prefix, a definition outside its home, or a colliding ID.
- **Single source** — `check_single_source.py` + `check_definition_single_source.py`: one rule / one
  definition, **one home, one ID; reference, never restate** (`SPEC-DESIGN §33`). A duplicate definition is
  a build failure, not a style note.
- **Settled vocabulary** — `check_model_vocabulary.py`: the agreed terms only; retired synonyms fail.
- **Retired terminology (`TERM-001`, above)** — `check_terminology.py`: a term a ruling retired does not
  reappear in living text; the scan reads wrapped lines and hyphenated forms, and exemptions are per file
  *and* per rule.
- **Derivability (`DRV-001` — `SPEC-DESIGN` rule 37, "a type does not store what the model already
  computes")** — `check_derivability.py`: a history- or aggregation-shaped field declares **DERIVED**
  (with its source) or **OBSERVED**, or does not exist on the type.
- **Registered standards** — `check_standards_registered.py`: a standard cited in prose has a register row
  (`adopted-standards.md` §8).
- **Spec completeness — UC + example + flow** — `registry/tools/spec_coverage.py --check`: every
  resource-type spec and Class declares its story in a structural **`coverage:` block** — the **Use Case(s)**
  (`use-cases/`), **worked example(s)**, and **flow(s)** (`docs/flows/`) that exercise it. Every declared
  referent must resolve (`COV-001`), and the backfill backlog (`registry/spec-coverage-backlog.yaml`) must
  match the tree (`COV-002`) so a new spec can't ship uncovered without either declaring coverage or visibly
  joining the backlog in its diff.
- **Spec examples — in the spec, CI-validated (ADR-055)** — `tests/check_spec_examples.py`: a type's worked
  example lives at **`spec.examples`** (the JSON Schema / OpenAPI keyword, co-located with the schema), never
  in a side file. Every in-spec example **validates against its own spec schema** (`EXG-001`, hard — a rotted
  example fails the build), and every spec carries one unless burn-down-baselined (`EXG-002`). The example is
  non-normative (excluded from the identity digest), so refreshing it never forces a version bump.

**Judgment (reviewer + author self-check).**
- **Scope — DCM vs UDLM (the peer test, `docs/adr/ADR-008`):** *could an independent conformant peer decide
  this differently and still be valid?* **Yes → DCM** (Policy / implementation); **No → UDLM** (the portable
  substrate). Portable data and *declarative* constraints are UDLM; anything computed, negotiated, or
  executed is DCM. Putting implementation mechanism into the portable model is a finding.
- **Reduce to existing (tenet T7):** does this coin a net-new mechanism (a "module", a new envelope, a
  parallel type)? If so, the *Why* must show that no existing mechanism — classification, profiles,
  capability declaration, conformance tier, references, edges — composes to cover it.
- **Adopt by reference (tenet T5):** does this re-express a concept a credible external standard already
  solves (API versioning, identity, RTO/RPO, health probes)? Adopt it, or justify why not.
- **Adopt tools by reference (tenet T8):** does this have the control plane *directly* build / scan / sign /
  deploy where a mature tool already owns the mechanism? Wrap the tool as a Provider (the naturalization
  boundary), don't reimplement it — the control plane owns the cross-tool intent + the estate graph.
- **Written for engineers, not for us (DOC-001 — "Write for a reader who wasn't there", above):** the audience is engineering teams
  and common human personas. Strip internal working-context — session/working-set labels, private
  enhancement/ticket numbers, colleague names, or internal tool artifacts. Every reference **carries its
  gist in one line** (what it *decided*), never a bare number. Concise; no duplication; cut anything that
  does not move a decision.
- **A spec travels with its story (rule-36):** a new or changed resource type / Class does not merge alone —
  it ships with its Use Cases, its in-spec example, and a flow. The minimums:
  - **Use Cases — 2–3:** a **positive** (happy path), a **negative** (a refusal / must-reject), and a
    **composite** where the type genuinely composes with others. Intent types get bespoke UCs; observed /
    inventory types (Hardware.\*, Facility.\*, Identity.\*) lean on the shared *estate-observation* UC.
  - **Example — 1+ in `spec.examples`** (ADR-055, gated by `check_spec_examples.py`), not a side file.
  - **Flow — 1 bespoke** lifecycle flow (failure branches shown inline) + the **shared composite** flow for
    the multi-resource story (not duplicated per spec) + a **separate negative/rollback flow only where the
    failure path is substantive** (DR, mid-maintenance failure). Observed types lean on the dependency-graph flow.
  The scoreboard shows the gap; the reviewer confirms the story is present, not just the schema.
- **Claims match their governing rule (flow/doc ⟷ rule consistency):** a flow, example, or doc that asserts
  *rule-governed* behavior must **cite the rule-ID and state it consistently with the rule's home** — never
  paraphrase a rule into a contradiction. The exemplar: `uc-10-dynamic-rehydration` once flatly said "UUIDs
  are preserved," contradicting **`RHY-005`** (UUID preserved *only* on a Faithful restore; a Provider-Portable
  rebuild mints a **new** UUID kept traceable by lineage). A claim that omits its governing rule, or restates
  it wrongly, is a finding. The *semantic* version of this — does the corpus as a whole cohere with the model
  — is measured by the **DAV coherence analysis** against this corpus; a per-rule-ID citation-integrity CI
  gate is buildable once a complete rule-ID definition index exists (today ~3% of citations resolve only by
  heuristic, too noisy to hard-gate).
- **Document the why:** the rationale lives in the repo (design note / tenet / ADR pointer), not just the
  diff.

## Licensing

By contributing to UDLM you agree your contributions are licensed under Apache License 2.0, matching the
project license.
