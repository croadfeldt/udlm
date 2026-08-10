# UDLM ADR-067: A composition is a **record** until someone offers it

**Status:** Proposed (croadfeldt upstream) — **requires engineering ratification**; maintainer decision 2026-08-10
**Date:** 2026-08-10
**Type:** Architecture Decision Record (a `DecisionRecord`, architecture scope)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** Each cited once with what it settles.
- **#405 / the Template classes** (`Template` → `Template.<Category>` → `Template.<Cat>.<Author>`): the orderable composition. A platform team declares a composition, `supports` says what a consumer may choose, and the class is checked against its parent. This ADR is about compositions that have **none of that**.
- **ADR-038** (scoped Classes): a class is Base → Type → Provider, each refining the last, and **scope IS portability**. A class is a claim about the *shared vocabulary* — which is exactly what an ingested diagram must not become.
- **The ingestion model** (`ING-001`..`ING-015`): *"the unified substrate contract for bringing entities that exist outside lifecycle control into governance"*, with brownfield discovery and **manual import** as named sources, and `ING-006`/`ING-007` already making promotion an authorized act that transfers lifecycle ownership. This ADR is that contract one level up.
- **`origin: declared | discovered-derived | backfilled`** (realized-entity states): the existing rule that *inferred state is never silently presented as human-declared*. Reused verbatim rather than re-invented.
- **DR-UDLM-002 §6** (structure from ModSpec, lifecycle from ourselves): the advancement ladder `PROPOSED → UNDER_REVIEW → CANONICAL` is UDLM's own and **must not be re-imported**. Two vocabularies for one ladder is the defect that DR exists to prevent.
- **NDF-001 / rule 41** (UDLM ships no defaults) and **DRV-001** (the model does not store what it can derive).

---

## Context

You can now order a three-tier application: a platform team authors `Template.Application.AcmeThreeTier`, declares what a consumer may choose, and people order it. That is #405, and it is done.

It answers one half of the question. **Compositions also arrive in ways nobody is offering them.**

A LikeC4 diagram gets ingested. A CALM file gets converted. A consumer builds their own bundle and saves it (#335). Each of those is a real composition — parts, edges, wiring — and each has a shape the model could hold.

**None of them may mint a class.** A class enters the shared vocabulary: it is portable, curated, governed, versioned, and checked against its parent. If importing a diagram minted a class, then so would a consumer saving a favourite, and the registry meant to hold the estate's agreed types would fill with documents nobody agreed to. *A document someone wrote is not a claim about shared vocabulary.*

So the model had a shelf for offers and no shelf for documents. The consequence was not theoretical: it is why the class-versus-record question kept looking like a fork with two right answers.

**It is not a fork. It is a lifecycle.** A composition *starts* as a document and may *graduate* into an offer. That reframing is the whole content of this decision, and it is why both earlier answers looked correct — each was describing one end.

## Decision

### 1. A composition that nobody is offering is a `composition` record

A new record kind (`registry/composition-record.schema.json`), carrying **the same composition shape a class carries** — `composition.schema.json`'s constituents, `$ref`'d, not copied.

One shape is load-bearing: **promotion must not be a translation.** A translation is where meaning is quietly lost and where two semantic checkers begin to disagree about the same graph.

What it deliberately does **not** carry is the class machinery: no `supports`, no parent, no narrowing check, no version in the registry. With `additionalProperties: false`, "this is not an offer" is **structural** — an offered composition cannot be expressed — rather than a rule someone has to remember (`ING-016`).

It carries a `tenant_uuid`, and a class does not. That asymmetry is the boundary: a class is portable vocabulary belonging to nobody; a composition record is **a document owned by somebody**.

### 2. The kind is what it is; the state is where it sits

`record_type: composition` never changes. `state` moves: `PROPOSED` → `UNDER_REVIEW` → `CANONICAL`.

This is the maintainer's correction, and it prevents a specific error: **a lifecycle state is not a definition of what something is.** An earlier draft proposed `status: draft` on the class instead. That loses twice — a draft would have to name a parent and pass the narrowing check *to exist at all*, which is precisely what makes it a draft; and it would occupy the shared-vocabulary namespace before anyone agreed it belonged there. But the sharper reason is the first one: a thing that is not yet a claim about shared vocabulary is not a *draft class*, it is a composition.

The ladder is the one decision records already use (**DR-UDLM-002 §6**), not a second one. `PROPOSED` means authored or ingested — exactly as a freshly written ADR is Proposed. **Nomination is the move to `UNDER_REVIEW`**, and it is a distinct, recordable act: that is what makes the governed process auditable rather than a decision that happened once and left no trace.

### 3. Promotion is an act of ownership, and it is a round trip

A composition reaches `CANONICAL` only when a class has been minted from it, **the record names that class** (`promoted_to`), and **the class names the record** (`promoted_from`) — `ING-017`, gated by `tests/check_composition_promotion.py`.

Both halves, or neither counts. A one-way pointer is how a promotion that never happened still looks like one from whichever side you read first.

**The record survives promotion** (`ING-018`). The class does not consume it. Re-ingesting the same source resolves to the existing record rather than filing a second one — otherwise every re-export of an unchanged diagram appears as a brand-new composition and restarts the review.

### 4. What the review decides is the one thing nothing can compute

`ING-020`, and it is the reason promotion is *governed* rather than *converted*:

> **A composition record states fixed values. A class must declare what may VARY.**

The ingested diagram says `4 vCPU`. Promotion means someone deciding whether 4 was a **choice** — in which case it becomes a `supports` range a consumer picks from — or a **constraint of the composition**. Nothing derives that. It is a judgement, it is the substance of the review, and everything else about promotion (a parent, a version, a name in the shared vocabulary) follows from it.

That also gives promotion its definition: **a record has an author; a class has an owner.** Authorship is a fact about the past. Ownership is a standing commitment.

### 5. Ingesting a composition is the ingestion contract, one level up

These rules are `ING-*` and live in the ingestion model rather than in a new family (**T7 — reduce to existing**). The fit is exact, not convenient: that document already defines itself as the contract for bringing things outside lifecycle control **into governance**, already names manual import as a source, and already makes promotion an authorized act that transfers ownership (`ING-006`/`ING-007`).

**Brownfield greening is the same act on entities.** A resource appears Discovered-first with no intent behind it, is adopted, and the missing upstream states are backfilled with `origin` marking what was inferred. An ingested composition is brownfield discovery for shapes, and promotion is adoption — so `ING-019` reuses that `origin` vocabulary verbatim: content synthesized from an external artifact is `discovered-derived`, never `declared`, however clean the mapping was.

## Consequences

- **The shadow-catalog risk is real and is contained by `ING-016`.** The obvious failure mode is that the intermediary becomes a second, ungoverned catalog: compositions accumulate, people order from them anyway, and nothing forces promotion. The containing rule draws the line where it actually is — **a composition may be realized by its author, and may never be offered to another tenant.** Running something you wrote is expansion of a document; publishing it for others to order is a claim. That also keeps consumer-authored bundles (#335) working without minting a class per consumer.
- **`ING-016` and `ING-020` are ungated, for opposite reasons, and both are recorded.** `ING-016` needs no gate — the schema makes an offered composition inexpressible. `ING-020` *cannot* have one: a gate claiming to verify which values are choices would be asserting that a human judgement has a right answer.
- **The `refines` chain moved off the class.** Pattern → template → system is a chain of **records** related by reference, not three states of one record: ADR-033 asserts both, and its own cardinality (one pattern → many templates → many systems) decides it, because states are 1:1. `ADR-033`/`ADR-034` need the amendment tracked at **#418**; the mechanics of both survive, only the lifecycle mapping fails.
- **Governance and specificity are different axes, and must not be merged.** It is tempting to map `composition → class` onto `pattern → template`, since both are three-stage and they line up. They are orthogonal: an ingested LikeC4 model can be fully specific and completely ungoverned; a hand-drawn pattern can be governed and deliberately vague. Conflating them is the same error that killed the earlier attempt to make Pattern and Template *class tiers*, and it is recorded here so it is not reached for a third time.
- **A composition record has no `handle` uniqueness requirement**, deliberately. Two teams may each have written down their own `three-tier-app` and neither is making a claim about the other's. Uniqueness is a property of shared vocabulary, so it starts at promotion.

## Alternatives considered

- **`status: draft` on the class.** Rejected — §2 above. It is the wrong shelf, not a shelf in the wrong state.
- **A new rule prefix for composition governance.** Rejected under T7: the ingestion model already is this contract, and a parallel family would mean two homes for one idea, which is the exact defect the rule-ID registry exists to prevent.
- **Bringing back `composite` as the record-kind name.** Rejected on evidence: **Composite is a derived shape** (`has_constituents`, normative in data-model-core §2) that a System, a `Template.*` class and a composition record all share — so as a discriminator it names the only property that is not in question. It is also the name #418 just retired as the *third* name for what became Template. `composition` is neutral about specificity and about ownership, and unambiguous beside a derived shape called Composite.
- **Letting promotion consume the record.** Rejected — it destroys the provenance that makes re-ingestion idempotent, which is the difference between an import pipeline and a duplicate generator.
