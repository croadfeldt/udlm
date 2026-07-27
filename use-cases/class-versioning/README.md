# class-versioning — how class inheritance evolves, pins, and proves itself

Nine cases probing the scoped-Class system's evolution contract before it is ruled: what a
Base Class change does to everything built on it, where version pins are legal, and how
blue/green typed-output diffing turns unpinning into a tested act. Mixed semantics: 001, 003,
005, and 007 are expected to work; 002, 004, 006, 008, and 009 succeed only if the system
**refuses** (the must-reject convention — refusals typed, actionable, audited).

The family encodes candidate rulings the ADRs will settle, so a gap analysis over it measures
the decisions, not just the mechanics: intra-registry references are by handle with the
registry ref as the only internal pin (004); organizational pins are `@version`/`@digest`-exact
(ADR-051), honored
completely, and visible as enumerated debt (005, 006); compatibility claims are promoted on
typed-output evidence, not trust (007, 008); and portability is part of the compat contract —
narrowing an element's scope is breaking even when no schema shape changes (009). Cases
010–012 carry the provenance contract (ADR-045 §7): generated specs declare their full
compilation chain (classes, layers, schemas, generator) and realized instances their provider
definition revision — live, historically reconstructible, and verified by recompilation with
mismatches refused. Cases 013–015 carry provider versioning (ADR-045 §8): internal
changes past the naturalization boundary are free (provable by empty output diff), declared-
surface changes classify and version under the standard rules, and under-declared surface
changes are refused naming the dropped output and its bound consumers. Cases 016–019 carry
the two-plane refinement: capabilities version individually (breaking changes scoped to
covers_types consumers, no sibling churn), the envelope versions the set only, whole-provider
pins ride definition revisions, blue/green runs at capability granularity, and plane-misplaced
classification is refused naming the correct plane and bump. Cases 020–021 carry
realized-instance stability: capability movement is visibility never action (drift compares
against provenance, not current), mixed-version day-2 operation is contractual within the
deprecation window, and retirement is the one calendared forcing function — refusals carry
the migration path. The unifying doctrine: docs/design/operational-response-matrix.md
(surface → decide → enable).

**Where the refusal cases' enforcement is specified.** The refusal contract each of these cases
asserts — typed, actionable, non-leaking, auditable — is stated once in
[`contracts/error-model.md`](../../contracts/error-model.md) §6a, and the registry-plane
mechanisms in [`governance/registry-governance.md`](../../governance/registry-governance.md) §6a:
`REG-011` (version sufficiency — 002), `REG-012` (scope narrowing is breaking — 009), `REG-013`
(intra-registry fixed-version pin refused — 004), `REG-014` (pin ahead or unknown refused, behind
is enumerated debt — 006), `REG-016` (promotion refused on a dirty typed-output diff — 008), and
`REG-015` (the durable gate-outcome record every case's "recorded" criterion depends on). Those
rules are specification, not enforcement: the class artifacts, classifier, and pin resolver they
run against are P0 items of `docs/design/scoped-class-hierarchy/realization-plan.md`, and the
blue/green harness behind 008 is scheduled with the P1 pilot.
