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

## Licensing

By contributing to UDLM you agree your contributions are licensed under Apache License 2.0, matching the
project license.
