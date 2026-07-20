# ADR-026: Typed-classification naming — the `<noun>_type` convention

**Status:** Accepted (2026-07-17)
**Related:** [ADR-027 — entity family model](ADR-027-entity-family-model.md); `registry/common-elements.md` §9 (relation vocabulary); ADR-025 (resource references)

## Context

UDLM classifies several first-class things along their own taxonomies: a resource's specific type (`Compute.VirtualMachine`), an entity's shape within its family (`single` | `multi`), a relationship edge's base semantics (`depends_on` | `contained_by` | `binds_to` | `references`). These need one consistent field-naming convention.

The edge tier was originally named `kind` — chosen to avoid overloading `type`, which `resource_type` and `entity_type` already use. Review found `kind` a poor fit **for edges** specifically:
- The domain standard for an edge's base classification is **`type`** — OASIS TOSCA "relationship type", Neo4j "relationship type", the RDF predicate-as-type.
- `kind` carries a *different* established meaning in the ecosystem we sit closest to: in Kubernetes `kind:` names the **object type** (Pod, Deployment), not an edge. A k8s-fluent reader misreads an edge `kind`.

Using a non-standard word that *also* collides with a conflicting meaning next door is an anti-pattern — worse than a plainly-overloaded standard word.

## Decision

**A typed classification of a first-class modeled thing is named `<noun>_type`,** where the noun scopes what is being typed. `type` is generic *by design*; namespacing it by noun disambiguates while keeping the standard semantics — the "overload" is scoping, not confusion. This is preferred over synonyms (`kind`, `flavor`, `category`, `class`) that diverge from the standard or collide with adjacent ecosystems.

Canonical fields:
- **`resource_type`** — the specific resource/process type (`Compute.VirtualMachine`, `Automation.AnsiblePlaybook`).
- **`entity_type`** — the coarse shape within a family (`single` | `multi`; `Capability` | … for Knowledge). See ADR-027.
- **`edge_type`** — a relationship edge's universal base semantics (`depends_on` | `contained_by` | `binds_to` | `references`), refined by a declared **`relation`** name (`common-elements` §9). `relation` is retained unchanged — it is the standard term (RFC 8288 link relations, TOSCA derived types).

`kind` is **retired for edges → `edge_type`.**

### Where `kind` may remain

`kind` stays acceptable **only** as a structural/source discriminator on a sub-record that is not itself a classified first-class entity, and where no domain standard says otherwise and the k8s object-`kind` sense does not apply — e.g. a provenance `source.kind` (`layer` | `actor` | `policy` | …), which tags the *shape of an origin record*, not the type of a modeled thing. New such fields SHOULD still prefer `_type` absent a specific reason. Existing non-edge `kind` fields (`source.kind`, a provider's `kind`) are flagged for a light audit, not a forced rename.

## Consequences

- One convention, distinct tokens (`resource_type` / `entity_type` / `edge_type`) — self-documenting, and greppable, which keeps drift-guards a simple grep rather than context-scoped parsing.
- No k8s collision on the edge tier; standard-aligned with TOSCA/Neo4j.
- A one-time, **value-scoped** rename `kind → edge_type` across the two schemas (`resource-type-spec`, `realized-entity`), `audit-record`, the resource-type specs' `relationships[]`, `data-model-core` §4, `common-elements` §9, and the `compat-check` tool. Value-scoped so the non-edge `kind` fields are untouched.

## Alternatives considered

- **Bare `type`** on the edge — the most standard word, contextually clear inside `relationships[]`, but it breaks the `<noun>_type` convention (it would be the only bare `type`) and forces drift-guards to become context-aware since `type:` is ubiquitous.
- **Keep `kind`** — rejected: non-standard for edges + the k8s object-`kind` collision (the anti-pattern this ADR names).
- **`category` / `predicate`** — `category` is looser than "type" (not a behavioural taxonomy); `predicate` is RDF-correct but the wrong register for an infrastructure audience.
