# ADR-032: Post-1.0 direction, and how we hold it while building 1.0

**Status:** Proposed (2026-07-19)
**Related:** ADR-030 (the convergence lifecycle — the direction this protects); ADR-031 (1.0 focus); ADR-029 (inventory / observed provenance); ADR-027 (the family axis this eventually refines); the intent-vs-realized split; the managed-vs-observed axis.

## Context

The model has a visible post-1.0 shape (ADR-030): one convergence lifecycle — `Intent + Realized`, a gap, `Converge` closing it; nature as the durable axis; timeline / terminal / provenance as parameters; the entity families as archetypes over one loop. We want to build 1.0 without foreclosing that shape, and without doing the future's work now. This records the principle that reconciles those.

## Decision

**Pre-1.0, pay only to remove a future-contradiction; never pay to pre-build a future feature.**

- The future model is a **lens, not a deliverable**. The only pre-1.0 work it justifies is ensuring a 1.0 decision doesn't *contradict* it — which is cheap, usually just not over-committing. Building any of it is the needless work to avoid.
- **The one contradiction to actively avoid:** hardening Resource/Process into permanent, closed *species* with behaviour branching on the family. Leaving them as today's labels contradicts nothing and costs nothing; they become archetypes over the one model later (ADR-030).
- **Cards on the table are Proposed ADRs.** Each encodes a direction in a page of prose and binds nothing — the ADR *is* the groundwork. ADR-030 is the first; the Blueprints ADR and a future "consumable / nature-first" refinement are the rest.
- **The direction, recorded for future-us:** one convergence lifecycle (ADR-030); nature (maintained-state / work-product / curated) is fundamental; timeline, terminal-condition, and provenance (requested / observed / curated) are orthogonal parameters; Resource / Process / Credential / Inventory / Knowledge are archetype presets; Knowledge and Inventory are *provenances* of the one realized-state model, not separate ontologies.

## Data · Policy · Provider

n/a — a **direction / meta** decision. The Data·Policy·Provider specifics live in the ADRs it points to (ADR-030 carries the model's lens in full).

## Consequences

- 1.0 ships focused (ADR-031); the future stays open at zero cost.
- When a use case finally needs the unified model, the groundwork is already written — we build, we don't re-derive.
- A future superseding ADR promotes the convergence model + nature + archetypes and carries the migration; ADR-027's family axis becomes the archetype layer.

## Alternatives considered

- **Don't record the direction; just build 1.0** — rejected: future-us re-derives it and risks contradicting it in the meantime.
- **Adopt the direction now** — rejected: violates ADR-031 (scope) and would migrate before the tag.
