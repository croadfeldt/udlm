# UDLM Core Tenets

The foundational tenets that govern everything else in UDLM — the meta-schema, the registry, the
cross-cutting requirements, and every Resource Type Specification. They derive from UDLM's three
abstractions (**Data / Provider / Policy**, `foundations/foundations.md`) and the Layers-vs-Policies
distinction (`foundations/layering-and-versioning.md` §1a), and they settle the recurring design
question: **where does logic live?**

## This is a boundary, not a guideline
These tenets draw a **domain responsibility boundary** — a service / contract seam between two distinct
roles:

| Domain | Owner | Responsibility |
|---|---|---|
| **Data** | UDLM | Custody of data through its lifecycle: identity, the four states, versioning, relationships, provenance, audit, sovereignty. *Hold, move, reference, version, audit.* |
| **Policy** | DCM (the realization) | Transformation, enrichment, derivation, decision, governance. *Compute, derive, evaluate, decide.* |

UDLM *defines* the contracts (Data, Provider, **and** Policy); **DCM is where Policy is applied** — it
evaluates and enforces policy and performs all transformation and enrichment. UDLM never applies policy;
it carries the data that policy acts on, and records the decisions policy makes.

The seam between them is a **contract** (UDLM's existing Provider and Policy contracts). Crossing it is a
boundary violation: **logic embedded in data** is a breach *into* the Data domain; **data custody
implemented inside policy** is a breach *out of* it. Conformance can be checked at the boundary — a spec
that carries executable behavior, or a policy that becomes the system of record for lifecycle state, is
non-conformant. The tenets below define each side of that boundary.

## T1 — The data model is a lifecycle custodian, not a mutator
UDLM's role is to **maintain data through its lifecycle** — the four states (Intent → Requested →
Realized → Discovered), with identity, versioning, relationships, provenance, audit, and sovereignty.
It **holds, moves, references, versions, and audits** data; it **does not compute, derive, enrich, or
transform** it. A spec carries values and *declarative* constraints — never executable behavior.

## T2 — Transformation and enrichment are Policy
All logic that **derives, computes, modifies, or enriches** data is the **Policy** abstraction's
responsibility — evaluated and audited by the realization (DCM), never embedded in the portable data.
*Layers are data; Policies are logic.* If you find yourself wanting an expression inside the data, you
want a Policy.

## T3 — The contract layer is deterministic and reproducible
Definition and validation MUST yield the **same result from the immutable record at any future time** —
the precondition for tamper-evident audit (`AUD-002`) and for sovereignty. Therefore the **portable
data model carries no embedded expression language**: determinism is *structural*, not policed. A single
impure expression anywhere would break it, so we don't carry the evaluator at all. Genuinely dynamic
runtime decisions (e.g. placement by live capacity) live in **Policy** and are recorded **as decisions
in the audit log** — they never alter the reproducible contract.

## T4 — Cross-entity data flow is relationship, not transformation
Including one entity's realized output in another is a **typed binding over a declared dependency-graph
edge** — governed, sovereignty-visible *movement* of data, not modification of it. Binding belongs to
the data model (the edge + typed `outputs`); any *transform* of a bound value is Policy. This is why
data inclusion is safe: every cross-entity flow — including one that crosses a sovereignty boundary — is
an explicit, governable edge, not an opaque expression.

## T5 — Adopt external standards by reference, not absorption
When a credible external standard already models a domain's data — **FOCUS** for cost/usage, **OpenCost**
for Kubernetes allocation, **OSCAL** for compliance, **SCIM** for identity — UDLM **adopts** it: it
carries the *identity* (the join key), a *version-pinned conformance reference*, and the *binding*, but
**never re-expresses the standard's schema** in the portable model. *Absorbing* (a parallel UDLM type)
or *embedding* (baking the fields into every entity) duplicates an external system's data and its
lifecycle — a **T1** breach and the "copy the data in" anti-pattern (`../contracts/information-providers.md`
§2). The disposition is decided by a test: **absorb only when no credible external standard exists AND
the data's lifecycle is genuinely UDLM's to custody; otherwise adopt.** Providers declare which standard
*versions* they support and consumers declare the version they require (both **data**); **negotiating,
enforcing, and translating between versions is Policy** (T2), and the negotiated effective version is
recorded as provenance. The full disposition, constructs, and the version-negotiation contract are in
`adopted-standards.md`.

---

**Consequence — what a UDLM spec contains and doesn't.**
- **Contains:** identity, versioning, the four-state shape, typed `spec` fields with *declarative*
  constraints (JSON Schema `if/then` · `dependentSchemas` · `enum` · bounds, plus declarative markers
  like `createOnly`), typed `outputs`, and typed relationship edges.
- **Does not contain:** embedded expression languages, transforms, computed values, or any executable
  behavior. Everything dynamic is a **Policy** evaluated by DCM and written to the audit log.

See `cross-cutting-requirements.md` for the pillar requirements these tenets serve, and
`registry/SPEC-DESIGN-REQUIREMENTS.md` for the per-entity authoring rubric.
