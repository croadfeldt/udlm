# ADR-034: The orderable-composite tier is one thing — Composite Service becomes Template

**Status:** Proposed (2026-07-20) — a **discussion card for engineering review**; binds nothing until ratified.
**Background — read first (the cold reader's on-ramp; skip if you have the context).** ADR-033 (Templates — the tier this unifies into); ADR-027 (the shape — now **derived** `has_constituents`, ADR-027 addendum); `docs/spec/foundations/template-composition-model.md` + `registry/catalog-item.schema.json` (the Composite Service model this absorbs); ADR-028 / DCM ADR-024 (the rule-ID registry the `CMP-*`→`TPL-*` rename rides).

## The problem — two terms for one objective

The goal is a **simple** model. Today two terms name the *same* objective — *a catalog-level definition that composes constituent resources, delivered through one request*:

| | **Composite Service** (shipping) | **Template** (ADR-033, paper) |
|---|---|---|
| What | catalog item: constituent resource types + `depends_on` + bindings + `failure_effect` | the orderable assembly: a Resource **with constituents** (`has_constituents`) + bound processes |
| Schema | `catalog-item.schema.json` + `validate.py` cross-field checks | none yet ("no schema change") |
| Rules | `CMP-*` | — |
| Runtime | instantiates into a **Composite Entity** | instantiates into a **System** |
| Framing | "an application **IS** a Composite catalog item" | "an application **IS** a Template" |

These are the same tier. **Two names for one objective is not simple** — this ADR proposes collapsing them.

## Proposal (for discussion)

**Composite Service and Template are one tier. Keep one name — `Template`.**

- **Composite Service (catalog item) → `Template`.** Template **adopts `catalog-item.schema.json` as its 0.1 schema**; ADR-033's "+ **bound processes**" becomes the *post-1.0 generalization* on top. A Composite Service is simply a Template whose consumables are **resources only**.
- **Composite Entity (runtime) → `System`** (a realized Template).
- **`CMP-*` rule family → `TPL-*`** — a rule-ID renumber that rides the registry work (ADR-028 / DCM ADR-024), not a behavior change.

**Why `Template`, not `Pattern`.** A catalog item is *concrete and orderable* — every part names something a provider can realize, which is what makes it a **Template**. A `Pattern` leaves parts open (they name capabilities rather than realizable classes), so it is not orderable. An abstracted version of a Template would be a Pattern; the catalog artifact itself is a Template.

> **AMENDED 2026-08-10 (#418).** This paragraph originally identified the tiers with lifecycle states — *"the Requested tier"*, *"(Intent)"*, *"Pattern → Template → System = Intent → Requested → Realized"*. Withdrawn: **Pattern and Template are definitions and a System is an instance**, because one Pattern yields many Templates and one Template yields many Systems, and states are 1:1. Full reasoning in ADR-033's amendment. The ruling this paragraph exists to make — that a catalog item is a Template rather than a Pattern — is unaffected, and is now sharper: the discriminator is whether the parts are cut, not which state it sits in.

## What this buys

- **One term for one objective** — the simplicity goal, directly.
- **Template stops being paper.** It inherits a shipping, validated schema + rules + the application model, and slots straight into Pattern → Template → System. ADR-033 gains a 1.0 grounding instead of a post-1.0 promise.
- **Finishes killing the overloaded "composite" tag** — the Resource/Process shape is now **derived** (`has_constituents`, ADR-027 addendum), so there is no stored `composite` value left; this retires the remaining high-traffic use, the catalog-tier name.

## Open questions for engineering

1. ~~**The name.**~~ **ANSWERED 2026-08-09 (maintainer):** `Template`, single name, no dual naming. "Composite Service" is retired rather than kept as an alias — one concept had grown three names (`Composite Service`, the `composite` group class, `Template`), and the third existed only because the first two were never removed.
2. **`CMP-*` → `TPL-*`** rename + timing (rides the rule-ID registry renumber).
3. **Composite Entity → System** in the runtime/DCM docs — agree the runtime instance name. *(ADR-033's amendment sharpens what a System IS: the instance, and the only one of the three tiers carrying `states`.)*
4. ~~**Resources-only Template**~~ — **ANSWERED (#408, landed):** no marker. A constituent now carries `edge_type` (`contained_by` | `binds_to`), so "resources-only" is exactly *zero `binds_to` constituents* — readable from the composition itself. The shape stays derived (ADR-027 addendum), and adding a marker would store what the constituent list already answers (DRV-001).
5. **Migration sequencing.** `catalog-item.schema.json` is an *accepted, implemented* 0.1 surface — so this touches shipping code. Baseline-then-ratchet (the rule-ID path) or a single cut?

## What it does NOT change

- The **composition mechanics** — constituents, `depends_on` acyclicity, `binding ⊆ depends_on`, `failure_effect`, `composition_visibility`. Same rules, renamed family. **No behavior change.**
- The **provider model** — ordinary providers fulfill constituents; no meta-provider.

## Data · Policy · Provider
- **Data** — `Template` is the catalog definition (was the Composite Service catalog item); `System` is the realized instance (was Composite Entity); the composition rules are data.
- **Policy** — placement, execution sequencing (Orchestration Flow), and failure handling are unchanged — a renamed tier, same policy surface.
- **Provider** — constituents are fulfilled by ordinary Service Providers (`provided_by: self|external`); no new provider role.

## Decision

**Proposed — binds nothing.** Ratify at engineering review, then execute as a migration behind the prefix ruling (schema rename + `CMP→TPL` + `Composite Entity → System` + the ~20 referencing docs), sequenced like the derive-shape and rule-ID work.

## Alternatives considered

- **Keep both terms** — rejected as the thing this ADR exists to fix: two names for one objective is not simple.
- **Map Composite Service to `Pattern`** — rejected: a catalog item is concrete and orderable (Requested), not an abstract design (Intent).
- **Invent a third name** — rejected: `Template` is the standards-aligned word and already the ADR-033 tier; adding a third term is the opposite of simplifying.
