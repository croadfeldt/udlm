# UDLM — Entity-Type Families

**Document Status:** Draft (introduced 2026-06-08)
**Document Type:** Foundation Reference

> **Foundation Document Reference**
>
> The three foundational abstractions — Data, Provider, and Policy — are defined in
> [foundations.md](foundations.md). This document defines how the **Data** abstraction's
> entity-type *definitions* are organized as UDLM's vocabulary grows.
> **This document maps to: DATA** (organization of typed entity extensions)
>
> **Related:** [Entity Types](entity-types.md) | [Four States](four-states.md) |
> [Ownership, Sharing, and Allocation](ownership-sharing-allocation.md) |
> Case study: [`../docs/examples/case-study-dav-knowledge-realization.md`](../docs/examples/case-study-dav-knowledge-realization.md)

---

## 1. Purpose

UDLM is a realization-neutral substrate whose universal contracts (identifier, four-state
lifecycle, provenance, classification, events) are domain-independent. Its **entity-type
definitions** are not domain-independent in *meaning* — an `Resource` is
about the infrastructure domain, a `Capability` about the architecture/knowledge domain —
so as UDLM is used across domains, the set of definitions grows and benefits from logical
organization.

An **entity-type family** is that organization: a way to group related definitions for
discovery and coherence. It is **not** a boundary on who may use them.

## 2. Definition — Entity-Type Family

> **Entity-Type Family**
> A **logical grouping** of UDLM entity-type definitions, named for the domain in whose
> context they were first defined (e.g. the **Resource** family, first exercised by the DCM
> realization; the **Knowledge** family, first exercised by the DAV realization). A family
> organizes definitions; **it is not a usage boundary, a scope, a permission, or an
> ownership.** The named realizations are **non-normative examples** (`GLOSSARY.md`) —
> a family is defined by UDLM and depends on no realization.

The governing principle:

> **Grouping ≠ boundary. Definitions are universal — free to use by all realizations,
> regardless of family.**

A `Capability` definition that emerged in the context of DAV is equally available to DCM,
or to any peer realization, with no special status. Grouping it under the "Knowledge
family" records *where it came from and what it relates to* — nothing more. UDLM's entire
value is exchange; an organizational scheme must never fragment that.

**Why this is safe to say:** the universality lives at the **definition** level. Usage
constraints live at the **instance** level — actual entities carry ownership,
classification, and scope per [Ownership, Sharing, and Allocation](ownership-sharing-allocation.md)
and the [Four States](four-states.md). So a family can be freely shared as a *vocabulary*
while individual *artifacts* built from it remain owned and classified. Definitions are
the public dictionary; instances are the private documents written with it.

Families are **flat and peer** — "family" denotes a logical grouping, **not a rank** in a
multi-level biological-style hierarchy. (Distinct from the informal "OS Family" usage in
[Layering and Versioning](layering-and-versioning.md).) A definition has a **home family**
for organization, but that placement grants it no exclusivity and imposes no restriction;
a family may freely reference definitions grouped under another.

Every definition therefore carries a **`family` tag** — the mechanism for disambiguating
terminology that overlaps across domains (see §6).

**One definition, applied uniformly.** A family may group **entity-type definitions**
(e.g. Resource, Knowledge) or **vocabulary-term definitions** (e.g. DCM, Computing,
Automotive). These are **not two notions of "family"** — they are the one concept above
grouping different *kinds* of definition. A definition has a family; whether the
definition is a type or a term does not change what a family is. Consequently the two
things that can look like "two families" for one entity are really two *different
definitions*, each in one family: a `Capability` **type** lives in the **Knowledge**
family (recorded once, at the type level), while a specific **term** like "Provider"
lives in the **DCM** family (recorded on that term's row). No row carries two families;
no second definition of "family" exists.

## 3. Why families (design rationale)

Modeling a non-infrastructure system (DAV) on UDLM showed the universality lives in the
substrate/contracts while the entity-type *definitions* are domain-specific in meaning
(see the case study). Families are simply the catalog structure that follows: **one
universal substrate; a growing, universally-usable set of definitions; organized into
domain-named families for findability.** A realization does not "own" or "gate" a family —
it may *contribute* definitions (which then belong to everyone) and *use* any definition
from any family. This is what makes "realization-neutral; any conformant realization is a
peer" concrete and non-fragmenting.

## 4. Family registry

Families name the domain a set of definitions was organized under; usage is open to all.

| Family | Domain (organizing context) | Example realization (non-normative) | Entity-type definitions | Lifecycle archetype |
|--------|------------------------------|-------------|-------------------------|---------------------|
| **Resource** | Maintained-state resources (provisioned, reconciled) | DCM | shape (derived, `has_constituents`): Atomic \| Composite (+ ownership sub-types) — [Entity Types](entity-types.md) | Provisioning: REQUESTED → PENDING → PROVISIONING → REALIZED → OPERATIONAL … |
| **Process** | Bounded executions (automation runs) | DCM | shape (derived, `has_constituents`): Atomic \| Composite — [Entity Types](entity-types.md) §2.3 | Provisioning (terminal): REQUESTED → INITIATED → EXECUTING → COMPLETED / FAILED / CANCELLED |
| **Knowledge** | Architecture / capability knowledge (curated) | DAV | Capability, TaxonomyTerm, Alias, Antipattern, DecisionRecord (+ future UseCase, Gap, Assessment, Finding) — [Knowledge Family](../entities/knowledge-family.md) | Curation: PROPOSED → UNDER_REVIEW → CANONICAL (+ OBSERVED, DEPRECATED) |
| **Access** | Identity — who/what a request acts as | DCM | `Identity` (+ future identity-contract types) — [Auth Providers & Identity Contract](../governance/auth-providers.md) | Contract: identity is resolved/verified by DCM, never held as a maintained state |

The **Resource** family is the founding set (UDLM's original definitions, retroactively
grouped). The **Knowledge** family is the first proof that the same substrate organizes a
domain UDLM did not originally anticipate. A family may be referred to by its domain name
(Resource, Knowledge) or by its anchoring realization ("the DCM family", "the DAV family")
— they denote the same grouping. Future domains (People/Process, Enablement — see
`../docs/research/holistic-vision.md`) would be organized as additional families, their
definitions equally universal.

## 5. What a family definition document specifies

A document defining a family states, at minimum:
1. The **domain** (organizing context) and the realization(s) that anchor it.
2. The **lifecycle archetype** — how the four states are interpreted in this domain and
   the shared state-machine skeleton its definitions typically use (descriptive coherence,
   not a constraint on reuse).
3. The **entity-type definitions** grouped here — for each: definition, field set,
   relationships, classification defaults, terminal behavior, per-type state machine.
4. A reminder that definitions are **universal** — listed here for organization, usable by
   any realization; constraints apply to *instances* (ownership/classification/scope), not
   to the definitions.
5. Confirmation that all **universal contracts** are honored (identifier, four-state,
   provenance, classification, events, contributor identity).

## 6. Family tagging — terminology disambiguation

The same word means different things in different domains. **"Drive"** in a computing
family is a storage device; **"Drive"** in an automotive family is operating a vehicle —
same string, unrelated meanings. Natural language resolves this from context; a universal
data substrate cannot rely on context, so it must make the meaning-context **explicit**.

Every definition therefore carries a **`family` tag** recording the family (domain
context) whose vocabulary defines it. Overlapping terms become unambiguous by
qualification — `Drive [Computing]` vs `Drive [Automotive]`; within our own stack,
`Process [Resource]` (a Process) vs `Process [People/Process]` (a business
process); and `Policy`, `Service`, `Provider`, `Capability` are all collision-prone across
domains.

Mechanics:
- The same term string may have **multiple definitions, one per family**, each tagged with
  its family. Disambiguation is "**term + family**", not "term" alone.
- A definition normally carries **one** family tag (the home of its meaning); the tag set
  permits more where a definition is genuinely shared verbatim across families.
- Consistent with **grouping ≠ boundary**: the family tag is a *namespace for meaning* — a
  disambiguator. It does **not** restrict who may use the definition. Instance scope is a
  separate axis.

`family` is one of several **orthogonal** tag axes a definition/instance may carry:

| Axis | Answers | Example |
|------|---------|---------|
| **family** | Whose vocabulary defines this meaning? | `Drive [Computing]` |
| **domain / domain_prefix** | Which sub-domain within the family? | capability domain `PRV`, `automation` |
| **pillar** | Which realization pillar (DAV)? | platform / people-process / enablement |
| **scope** (instances) | Who may see/own this artifact? | global / shared / domain / project |

**Recommendation:** `family` should be a **standard tag on all UDLM Data** (a candidate for
the artifact-metadata block), so cross-family disambiguation works universally — not only
for the Knowledge family.
