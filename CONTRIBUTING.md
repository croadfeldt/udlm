# Contributing to UDLM

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

## Document the why

Every non-trivial change records its rationale, not just its diff: a design note under `docs/`, an
update to a tenet/principle in `design-principles/`, or — for a decision — a pointer to the relevant
DCM Architecture Decision Record (`architecture/adr/` in the DCM repo). Don't land a contract change
without the why; a reviewer should be able to reconstruct *why* from the repo, not just *what*.

## Registry changes (valid-by-construction)

Every registry entry MUST validate against its meta-schema — run `python3 registry/tools/validate.py`
(types, instances, and provider support matrices all pass, 0 invalid). A new resource type, instance,
or provider matrix includes a worked example that passes the gate. Version per `registry/VERSIONING.md`;
`registry/tools/compat-check.py` enforces that the declared bump matches the change.

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
- **Registered standards** — `check_standards_registered.py`: a standard cited in prose has a register row
  (`adopted-standards.md` §8).

**Judgment (reviewer + author self-check).**
- **Scope — DCM vs UDLM (the peer test, `docs/adr/ADR-008`):** *could an independent conformant peer decide
  this differently and still be valid?* **Yes → DCM** (Policy / realization); **No → UDLM** (the portable
  substrate). Portable data and *declarative* constraints are UDLM; anything computed, negotiated, or
  executed is DCM. Putting realization mechanism into the portable model is a finding.
- **Reduce to existing (tenet T7):** does this coin a net-new mechanism (a "module", a new envelope, a
  parallel type)? If so, the *Why* must show that no existing mechanism — classification, profiles,
  capability declaration, conformance tier, references, edges — composes to cover it.
- **Adopt by reference (tenet T5):** does this re-express a concept a credible external standard already
  solves (API versioning, identity, RTO/RPO, health probes)? Adopt it, or justify why not.
- **Adopt tools by reference (tenet T8):** does this have the control plane *directly* build / scan / sign /
  deploy where a mature tool already owns the mechanism? Wrap the tool as a Provider (the naturalization
  boundary), don't reimplement it — the control plane owns the cross-tool intent + the estate graph.
- **Written for engineers, not for us (`docs/writing-for-humans.md`):** the audience is engineering teams
  and common human personas. Strip internal working-context — session/working-set labels, private
  enhancement/ticket numbers, colleague names, or internal tool artifacts. Every reference **carries its
  gist in one line** (what it *decided*), never a bare number. Concise; no duplication; cut anything that
  does not move a decision.
- **Document the why:** the rationale lives in the repo (design note / tenet / ADR pointer), not just the
  diff.

## Licensing

By contributing to UDLM you agree your contributions are licensed under Apache License 2.0, matching the
project license.
