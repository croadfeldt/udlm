# UDLM 0.1 — Conformance Suite: scope, options, recommendation

**Status:** 📋 Review artifact (decision-support). Frames the build-vs-defer decision for the one
heavy 0.1 exit criterion (`../../registry/UDLM-0.1-SCOPE.md` §5.3).

**The tension:** `VERSIONING.md` makes *"the `CONFORMANCE.md` suite passes"* the literal 0.1 gate.
Today CI runs only registry validators (`validate_registry.py`, `ci_compat_gate.py`,
`check_estate_tokens.py`) — meta-schema validation of the spec *repo*, not conformance of a
*realization*. `CONFORMANCE.md` (still Draft) and `tests/test-framework-specification.md` *specify* a
suite; no runner exists. So a 0.1 tag today cannot honestly claim the conformance bar.

## Two tiers of conformance (they are not the same effort)

**Tier 1 — Static / surface conformance.** Given a realization's *published artifacts* (its
`/.well-known/udlm/schema-bundle` and `/.well-known/udlm/conformance` declaration), verify they are
well-formed and self-consistent **without a live realization**:
- bundle validates against the bundle-manifest shape (schema-sharing §3);
- every referenced schema is fetchable, is valid JSON Schema 2020-12, and its `$id` matches its
  manifest entry (schema-sharing §9);
- `$id` spec-segment == declared `conforms_to`, version-segment == `version` (already enforced for the
  repo by `validate_registry.py` — extend to a peer bundle);
- the core-schema baseline (schema-sharing §10) is present/depended-on, not re-published;
- the conformance declaration validates against the `CONFORMANCE.md` declaration schema and its claimed
  capabilities/surfaces are internally consistent.

**Tier 2 — Behavioral / wire conformance.** Given a *running* realization, issue live operations and
check responses against the contracts: reserve→commit→release with TTL/expiry (ADR-011), policy
resolved-profile + three-state outcome, four-state transitions + provenance, audit inclusion/consistency
proofs (universal-audit §8), schema-fetch-on-unknown-type (schema-sharing §6), recovery/drift. This is
the `CONFORMANCE.md` §6 wire checklist. It needs a reference realization (DCM) to test against and a
fixtured harness.

## Effort + dependencies

| | Tier 1 (static) | Tier 2 (behavioral) |
|---|---|---|
| Needs a live realization? | No | Yes (DCM reference) |
| Builds on | `validate_registry.py`, `CONFORMANCE.md` decl schema (to finish), schema-sharing (#78) | Tier 1 + a running DCM + fixtures |
| New artifacts | bundle+declaration validator; a `schema-bundle.schema.json`; the CONFORMANCE.md declaration schema; fixtures | operation harness per surface; golden transcripts; a reference deployment |
| Rough effort | **~2–3 days** | **weeks** (overlaps DCM/test-infra) |
| Blocks a 0.1 tag? | Yes, for an honest "surface-0.1" | No — legitimately post-0.1 |

## Recommendation

**Build Tier 1 now; schedule Tier 2 post-0.1.** Concretely:

1. Finish the `CONFORMANCE.md` declaration schema + move CONFORMANCE.md Draft→Complete, scoping its
   "the suite is executable" claim to **Tier 1 (surface conformance)** for the 0.1 bar, and stating
   Tier 2 (behavioral) is the post-0.1 certification.
2. Add `registry/schema-bundle.schema.json` (the schema-sharing §3 shape, machine-validatable) — the
   one follow-on schema-sharing §10 already flags.
3. Add `tests/validate_conformance.py`: validate a bundle + declaration (self-test against this repo's
   own schemas as the reference bundle) and wire it into CI. This makes "surface conformance passes" a
   real, green gate.
4. Then 0.1 tags honestly as a **surface-complete + surface-conformant** release; behavioral
   certification (Tier 2) is a named post-0.1 milestone, not a silent gap.

This keeps the 0.1 claim truthful without blocking on the weeks-long behavioral harness — and Tier 1 is
genuinely useful on its own (it's what catches a peer publishing a malformed or drifted bundle).

**Alternative if you want 0.1 sooner:** skip even Tier 1 and soften `VERSIONING.md` + `CONFORMANCE.md`
to define the 0.1 bar as *surface-complete + registry-valid* (what CI already proves), with **all**
conformance testing post-0.1. Faster, but "0.1" then makes a weaker interop promise. I recommend Tier 1
— it's small and it's the difference between "the spec is internally valid" and "a peer's published
surface is checkably conformant."
