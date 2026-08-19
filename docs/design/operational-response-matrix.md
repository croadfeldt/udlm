# The operational response matrix — surface, decide, enable

**What this settles:** the unifying doctrine behind everything versioning-shaped in this
registry — class evolution, generated specs, provider envelopes and capabilities, knowledge
records, and the instances realized from all of them. The platform's job is three verbs, in
order: **surface** the blast radius and the staleness of every artifact *relative to its
provenance*; let the **organization decide** the operational response through its declared
policies; and **enable** whichever typed response the policy picks — automated, approved,
delayed, or skipped — with the when, where, and why recorded. The platform never acts on its
own initiative, and it never judges the choice: best practices and profile defaults are
advisory overlays an organization may adopt, and a deliberate, permanent "skip" is a
legitimate, recorded decision — visible debt, not a violation. The focus is enablement, and
the goal behind the focus is **removal of toil**: every cell in this matrix replaces
operational labor a human used to perform by hand — compiling impact lists, tracking staleness
in spreadsheets, re-remembering the ceremony per change, assembling promotion evidence. An
organization that adds ceremony, or over-complicates by this document's standards, is
exercising exactly the control the platform exists to enable; the platform's job is that the
complexity they choose costs them declaration, not labor.

## Why provenance is the reference point

Staleness is meaningless without an anchor. An instance is not "behind" some abstract current
— it is at a measurable distance from *what governed it*, which its provenance records
immutably (ADR-045 §7: the compiled class chain; §8: the capability revision and engine
binding). Every distance in the matrix below is computed against provenance, which is also
what makes the false-drift trap impossible by construction: reconciliation compares an
instance to the revisions that produced it, never to the current tip, so an upstream release
manufactures visibility, never phantom drift.

## The matrix

Each row is a change origin; the columns follow the three verbs. Every cell cites the corpus
family/case that measures it — cells without coverage are named as gaps at the end, per the
exposure discipline.

| Change origin | SURFACE — blast radius & distance (vs provenance) | DECIDE — whose policy, on what | ENABLE — the typed responses | Corpus |
|---|---|---|---|---|
| **Base/Type class change** | regeneration manifest ([schema](../../registry/regeneration-manifest.schema.json)): affected classes + regenerated specs (class graph) + consumers accruing debt (DCM ADR-044 manifests) | estate change policy, branching on change class (additive/breaking) | auto-adopt · windowed adopt · full ceremony · blue/green re-pin · skip (stay pinned, visible debt) | cv-001..009, cc-001..008 |
| **Generated spec revision** | spec pin-lag per pinned artifact; re-opens on registry-ref advance | same estate change policy | re-pin under gates · skip-with-debt | cv-005/006; estate burn-down discipline |
| **Provider envelope (set) change** | capability set diff (added/removed); definition revision movement | estate change policy; placement policy if switching providers | adopt · provider swap (blue/green) · skip | cv-017 |
| **Provider capability revision** | bound consumers via `covers_types`; per-instance realized-under vs current distance (implementation provenance) | the organization's change policy — the capability movement itself triggers nothing | update · re-realize (blue/green when breaking) · deliberate no-action (recorded) · expedite | cv-016, 018, 019, 020 |
| **Capability deprecation/retirement** | countdown vs published window; realized instances counted as pinned consumers | migration scheduling under the change policy — retirement is the one calendared forcing function | governed migration by window · refusal-with-path after retirement | cv-017 c5, cv-021 |
| **Knowledge record change/staleness** (windows, calendars, CVE feeds) | freshness vs declared expectation (`current / stale_expected / stale_deviant`); authority per scope | the consuming policy's authority declarations; gates fail closed on staleness | refresh · expedite during staleness outage · refuse-on-conflict | cc-013..015 |
| **Estate's own artifacts** (dependent applications) | impact set derived from dependency edges; per-client tolerance from availability policies | per-client availability policy + estate window/ceremony | ordered quiesce/restart · DR cutover (re-bind on outputs) · resumable halt | cc-009..012 |

## The response taxonomy — dispositions × timing

"Automated, approved, delayed, skipped" are examples, not the enumeration. The full space the
corpus already cases has two orthogonal axes plus one platform-side complement:

**Dispositions** — what the organization decides to do about the surfaced change:

| Disposition | Meaning | Corpus |
|---|---|---|
| **Adopt — automated** | the policy pre-decided; no human per event | cc-001 |
| **Adopt — approved** | a named human authority accepts the evidence | cc-003 |
| **Skip** | deliberate, recorded no-action; visible debt, fully legitimate | cv-020 |
| **Substitute** | change the dependency instead of absorbing the change — provider swap, migration off, DR cutover | cv-014, cc-017, cc-009 |
| **Reverse** | undo an already-taken response — rollback, stay-on-blue, failback | cc-009, cv-008 |
| **Escalate** | contest the change: route the contradicted claim upstream as a finding ([schema](../../registry/finding-routing-record.schema.json)) | cv-008 (ADR-046 D4) |

**Timing modifiers** — orthogonal; they attach to any adopt disposition:

| Modifier | Meaning | Corpus |
|---|---|---|
| immediate | at the next sync | cc-001 |
| windowed | inside a declared maintenance window | cc-002 |
| queued | suspended pending a state change (freeze lift) — not scheduled, waiting | cc-007 |
| staged | incremental, with gates between stages/batches | cc-005, cc-008 |
| expedited | compressed schedule under elevated approval — evidence untouched | cc-006 |

**Platform-side complement:** **refused** — not an organizational response but the platform
enforcing the organization's own declared gates against a non-conforming attempt (cc-004
out-of-window, cv-019 wrong plane, cc-016 evidence-gate removal). Listed because it is what
makes every other entry trustworthy: a response vocabulary without enforcement is a suggestion
box.

The taxonomy is open by design — enablement means an organization can declare response types
these tables do not anticipate; a new disposition earns its row by arriving with the corpus
case that measures it.

A note on the ENABLE column's named mechanisms: entries like "blue/green" are **reference
approaches, not requirements** — the information (provenance, distances, evidence records)
lives in this model; the decision process and the mechanism that executes a response belong to
DCM and the estate's own choices (ADR-008 boundary; ADR-046 states this for promotion
explicitly). Any mechanism that produces and consumes the declared evidence surfaces complies.

Three invariants hold across every row:

- **Scheduling gates decide when; evidence gates decide whether.** No response path — not even
  expedite — waives the evidence gate for a breaking adoption (ADR-046).
- **Every waiting state is typed and visible** — windowed, queued, frozen, realized-under-
  distance, deprecation-countdown — so "behind" is always provably on-policy behind.
- **Every decision is recorded with its why**: the policy clause that authorized it, the
  evidence it read, the revisions (from provenance) it measured against — including the
  decision to do nothing.

## Defaults and best practices — advisory, by design

The profile ladder carries sensible defaults (a dev profile that auto-adopts additive changes;
a prod profile that windows everything; a regulated profile that freezes and expedites), and
best-practice guidance may recommend responses per change class. All of it is **advisory
overlay**: an organization adopts a default by referencing it, overrides it by declaring its
own clause, and ignores recommendations without penalty. The registry's own review discipline
applies here too — an authority's legitimate operational choice is never audited as a defect.
Enablement is the product; opinions are documentation; the measure of both is toil removed.

## Coverage gaps (named, per the exposure discipline)

Both former gaps are now cased: **cc-016** (change policies are themselves versioned,
meta-policy-gated, prospective-only, with evidence gates unloosenable) and **cc-017**
(whole-provider retirement as a governed wind-down — derived blast radius, standard-machinery
migrations, no completion while instances remain). The matrix's coverage is complete against
its own rows; both contracts join the pending change-control ADR's surface.
