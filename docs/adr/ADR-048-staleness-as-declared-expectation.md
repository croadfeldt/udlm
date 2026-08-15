# UDLM ADR-048: Staleness is judged against a declared expectation — `expected_observation`, verdicts derived, never stored

**Status:** Proposed (croadfeldt upstream)
**Realized by:** _not yet_ — decided, no machine surface.
**Date:** 2026-07-25
**Type:** Architecture Decision Record (a `DecisionRecord` with architecture scope — `docs/spec/foundations/knowledge-family.md` §4.5)
**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles. `docs/spec/foundations/four-states.md` (Discovered state carries the
observation facts: timestamp, method, provider — last-seen is already derivable);
`docs/spec/foundations/service-dependencies.md` OBS-005 (the profile-governed observation TTL this ADR
demotes to a fallback); `registry/accreditation.schema.json` `stale_after`/`stale_action`
(the in-schema precedent: a declared bound plus a declared consequence);
`docs/design/change-control-knowledge-sources.md` (independently logs freshness as missing on
every Knowledge type — the second demand corpus for the same element); ADR-015 (settings
composition — how a group-scope cadence value resolves onto a unit's envelope);
ADR-038 (the promotion signal: two independent corpora hitting one element).

## Context

A monitoring model that assumes everything should check in daily brands a healthy seasonal
fleet as broken. The demand case is an external field-device fleet adopter whose devices are
offline for most of the year *by design*: a unit last seen in April is healthy in June, and
the real alarm — a unit that never re-converged after the annual re-image window — is
invisible to a fixed TTL, because under a PT24H/PT4H default the entire fleet is permanently
"stale" and the one genuinely deviant unit is indistinguishable from the healthy ones.

The model already carries the *observation* side: Discovered state records when, how, and by
whom an entity was last observed, and the durable inventory is the latest reconciled
observation per entity. What it lacks is the **declared expectation** to judge that
observation against. Both precedents for that shape are already in schema: the accreditation
record's `stale_after` + `stale_action` (a declared bound and a declared consequence), and
OBS-005's TTL — the right idea at the wrong rigidity, because the bound is fixed by profile
rather than declarable per entity or group.

## Decision

**One new declared-expectation element, `expected_observation`, on the realized-entity
envelope; staleness verdicts are derived from it, never stored.**

1. **The element.** `expected_observation` declares the entity's observation rhythm: a
   `cadence` (ISO 8601 duration — "expect an observation this often"), or a `window`
   (a declared expected-contact period, optionally recurring — "expect observations only
   within this period"), plus `on_exceeded: normal | finding` — what an overdue observation
   *means*. Its home is the realized-entity envelope, beside the observation metadata it is
   judged against.
2. **Verdicts are derived, never stored.** The staleness verdict —
   `current | stale_expected | stale_deviant` — is computed as observation age against the
   declared expectation, by whatever consumer asks. `stale_expected` (overdue, and the
   declaration says that is normal) is a *healthy* state; `stale_deviant` (overdue where the
   declaration says overdue is a finding) is the alarm. No verdict field exists to drift.
3. **OBS-005's TTL is demoted to the fallback.** The profile TTL applies only where no
   `expected_observation` is declared. A declared expectation always wins over the profile
   default — that is the whole correction: the bound becomes declarable, the default remains
   for everyone who never declares one.
4. **The declared value composes like any setting.** An expected-offline window for a whole
   group of devices is a group-scope value resolved onto each unit through settings
   composition (ADR-015), so the envelope carries the *resolved* expectation with its
   provenance — never a hand-typed copy per unit.
5. **Phase 2 — the Knowledge-family Base-tier twin — is named, not built here.** "Is this
   *record or feed* fresh?" is the same shape at the Knowledge family level
   (`as_of` / `valid_until` / `refresh_cadence`), already logged as missing on every
   Knowledge type by the change-control corpus. That element lands once, on the Knowledge
   Base Class, when the class implementation program delivers the carrier — two independent
   corpora demanding one element is exactly the ADR-038 promotion signal. This ADR reserves
   the destination; it does not pre-build it.

**Fail-closed stays scoped to gating decisions.** A change-control gate deciding on outdated
windows still refuses (deciding on stale knowledge is worse than refusing). Fleet *display*
staleness is a judgment surface — a verdict, never a refusal.

## Consequences

- "Seasonally offline" becomes a declarable, healthy state instead of a permanent false
  alarm, and the real failure — overdue where overdue is deviant — becomes the *only* thing
  that alarms.
- The genuinely dangerous fleet condition (a unit that never re-converged after its declared
  window passed) derives with no further machinery: declared expectation exceeded AND the
  realized state still behind the current pin.
- Consumers that never declare an expectation see no change: the OBS-005 profile TTL governs
  exactly as before, as the fallback.
- The verdict vocabulary is fixed here (`current | stale_expected | stale_deviant`) so
  independent consumers derive the same answer from the same declarations — the same
  determinism contract settings resolution follows.
