# UDLM ADR-056: "Realization" (a system that implements UDLM) is renamed **implementation** — de-overloading it from the lifecycle

**Status:** Proposed (croadfeldt upstream) — foundations-legibility work; requires engineering ratification because it changes a wire enum value; decided 2026-07-28
**Date:** 2026-07-28
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The four-state
lifecycle names a state **Realized** ([`docs/spec/foundations/four-states.md`](../spec/foundations/four-states.md), ADR-030) and a verb **realize** — "make intent real." Separately, the spec used the noun **realization**
to mean *a system that implements UDLM's interfaces* (DCM and DAV are examples). Those are **unrelated
concepts sharing a root**, which is the exact legibility anti-pattern engineering flagged in review
("what does this term mean"). This ADR de-overloads them. Terminology discipline: CONTRIBUTING § TERM-001.

**Settles:** the noun for *a system that implements UDLM* is **implementation** (not "realization").
The lifecycle vocabulary — the verb **realize**, the state **Realized**, and the act-sense noun in
**two-phase realization** / the reserve-phase **realization** loop — is **unchanged**. UDLM is
**implementation-neutral** (was "realization-neutral").

## Context

`realization` carried two senses:
- **System sense** — "a realization," "conformant realization," "realization-neutral," and the
  accreditation enum value `peer_realization`. This is a system/implementation of the spec.
- **Act/state sense** — "two-phase realization," "the realization loop," `realization_timestamp`,
  `re_realization`. This belongs to the `realize → Realized` lifecycle family.

Mixing them means "realization" and "Realized" sit next to each other meaning different things — a
foundational reader cannot tell which is which. Only the **system sense** collides; the lifecycle sense
is legitimate and stays.

## Decision

1. **System sense → `implementation`.** Rename every system-sense use: "a realization" → "an
   implementation," "conformant realization" → "conformant implementation," "realization-neutral" →
   "implementation-neutral," etc. The glossary term is now **implementation**.
2. **Lifecycle/act sense unchanged.** `realize`, `Realized`, "two-phase realization," the reserve-phase
   realization loop, and the act-sense fields (`realization_timestamp`, `realization_request`,
   `re_realization`) keep their names — they are the `Intent → Requested → Realized` family, not the
   overload.
3. **One wire break, ratification-gated.** The accreditation enum value **`peer_realization` →
   `peer_implementation`** (`registry/accreditation.schema.json`). This is the only structural schema
   change — no schema *property key* named `realization` existed. **Migration:** the old value
   `peer_realization` is recorded as the legacy label in
   `registry/instances/provider-capability-taxonomy.yaml` so implementers can map forward. Because this
   changes the contract implementers build against, it does **not** merge without engineering sign-off.
4. **Immutable records are not rewritten.** Published `decision_record` instances that used the old word
   are left byte-for-byte unchanged (ADR-051 R4a — published records are immutable; you do not rewrite
   history to chase a rename).
5. **Revision bumps.** The five → four resource-type specs whose *descriptions* changed ship a REVISION
   bump per the publish law (identity.person, identity.service-account, network.dhcp-scope,
   storage.cluster; access.identity-escrow reverted — its only hit was an act-sense mis-catch).

## Consequences

- **Legibility:** the `implementation` vs `Realized` split is now unambiguous; the glossary "start here"
  names it as one of the six first terms.
- **Wire:** SPEC consumers keying on `peer_realization` must move to `peer_implementation`; the legacy
  label is documented for a compat window. Everything else is prose — no other consumer impact.
- **Naming charter:** updated to record `implementation` as the canonical term for the implementing
  system, and `realize`/`Realized` as the lifecycle family (this ADR is the ruling behind that row).
- **Follow-up (not in this change):** add TERM-001 guards for the retired system-sense phrases
  (`realization-neutral`, `conformant realization`, `peer_realization`) so the overload cannot regress —
  deferred because the guard must be authored alongside an allowance for this ADR's own explanatory text.

## Related

- ADR-030 (convergence lifecycle — the `Realized` state this protects) · ADR-051 (identity/version —
  why the decision records are not edited) · `docs/spec/foundations/four-states.md` · `GLOSSARY.md` (the term) ·
  `docs/spec/principles/naming-charter.md` (the canonical vocabulary) · CONTRIBUTING § TERM-001.
