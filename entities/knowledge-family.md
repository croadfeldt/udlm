# UDLM — Knowledge Entity-Type Family

**Document Status:** Draft (introduced 2026-06-08)
**Document Type:** Entity Reference
**Family:** Knowledge (architecture / capability knowledge) — first exercised by the **DAV**
realization (a non-normative example; UDLM depends on no realization — see `GLOSSARY.md`)

> The three foundational abstractions are in [foundations.md](../foundations/foundations.md);
> the family concept in [Entity-Type Families](../foundations/entity-type-families.md).
> **This document maps to: DATA.**
> **Universality:** these are UDLM definitions grouped here for organization. They are
> **free to use by any realization, regardless of family** — DCM or any peer may use a
> `Capability` exactly as DAV does. Constraints apply to *instances* (ownership,
> classification, scope), never to these definitions.
>
> **Realization:** `dav/docs/capability-catalog-design.md`. Case study:
> [`../docs/examples/case-study-dav-knowledge-realization.md`](../docs/examples/case-study-dav-knowledge-realization.md).

---

## 1. Domain

The Knowledge family models **architecture and capability knowledge** — the artifacts a
system reasons about when it asks *"what should be able to happen, what does it take, and
where are the gaps?"* Where the Resource family tracks resources through **provisioning**,
the Knowledge family tracks definitions through **curation**: proposed → reviewed →
canonical, against a backdrop of what is **observed** in the field.

## 2. Lifecycle archetype — curation (the family's four-state interpretation)

Every Knowledge entity is UDLM Data and exists in the four states; the family interprets
them for curated knowledge:

| UDLM state | Knowledge interpretation | Storage semantics |
|------------|--------------------------|-------------------|
| **Intent** | `PROPOSED` — a proposed definition ("what we think should exist") | append-only, immutable record of the proposal |
| **Requested** | `UNDER_REVIEW` — the proposal submitted into curation (the contribution under review) | append-only per review cycle |
| **Realized** | `CANONICAL` — accepted, authoritative | versioned snapshots, `is_current` flag |
| **Discovered** | `OBSERVED` — what an assessment / UC analysis observes in the field | ephemeral, refreshed per assessment/analysis run |

Shared state machine skeleton (per-type tweaks allowed):

```
OBSERVED ─┐                        (parallel evidence from the field)
          ▼
PROPOSED ──► UNDER_REVIEW ──► CANONICAL ──► DEPRECATED
   ▲             │
   └─────────────┘  (revision)
```

**The signature operation:** the gap between `CANONICAL` (what should be) and `OBSERVED`
(what an assessment found) is **drift detection applied to knowledge** — identical in shape
to the Resource family's Realized-vs-Discovered drift. This *is* DAV's gap analysis.

## 3. Shared semantics

- **Universal contracts honored:** UUID stable across lifecycle; the artifact-metadata
  block (handle, version, status, owned_by, created_by, created_via); field-level
  provenance; data classification; contributor identity (the LLM-proposes / human-curates
  step is UDLM's federated-contribution model).
- **Provenance is first-order:** every field records origin — e.g. a `Capability.domain`
  sourced from the DCM taxonomy vs an `evidence` field sourced from a specific assessment
  finding.
- **Classification defaults:** canonical, shared vocabulary (TaxonomyTerm, Alias,
  Antipattern seeded from public taxonomy) defaults **public**; field-derived
  instances (e.g. capabilities discovered in a client assessment) default
  **client-confidential**. Set per instance, per field.
- **Family tag:** every definition here carries `family: knowledge` — the disambiguation
  namespace (see [Entity-Type Families §6](../foundations/entity-type-families.md)). So
  `Capability [Knowledge]` is distinct from any same-named term in another family, and
  collision-prone words (`Process`, `Policy`, `Service`, `Provider`, `Capability`) stay
  unambiguous as "term + family". It disambiguates meaning; it does not restrict use.
- **Ownership / scope is instance-level**, per
  [Ownership, Sharing, and Allocation](../foundations/ownership-sharing-allocation.md):
  global / shared / domain / project tiers (DAV's tier+tags model maps onto this). The
  *definitions* below are universal; only the artifacts built from them are scoped.

## 4. Entity-type definitions

### 4.1 Capability
A discrete ability that must be present to realize use cases (platform, people/process, or
enablement). The unit the catalog inventories and the roadmap sequences.
- **Fields:** name (handle), description, pillar, domain (capability-domain prefix),
  normalization_status (normalized | proposed-gap | unmapped), demand (count/refs of UCs
  requiring it), leverage (foundational-dependency metric), evidence.
- **Relationships:** `normalized_to` → TaxonomyTerm; `depends_on` → Capability;
  `required_by` → UseCase *(future)*; `surfaced_by` → Assessment/Finding *(future)*.
- **States:** typically enters as `OBSERVED` (from an assessment) and/or `PROPOSED`, then
  `UNDER_REVIEW` → `CANONICAL`; `DEPRECATED` is terminal.

### 4.2 TaxonomyTerm
A canonical vocabulary term — the **normalization authority** the catalog normalizes onto.
- **Fields:** term (handle), definition, pillar, domain (prefix + name), parent
  (→ TaxonomyTerm), normalization_rules (how to normalize items for this subject matter),
  category (source grouping).
- **Relationships:** `parent` → TaxonomyTerm; normalized **by** Capability/Alias.
- **States:** `PROPOSED` (a back-fill candidate the catalog surfaced) → `UNDER_REVIEW` →
  `CANONICAL`. Seeded `CANONICAL` from an authoritative taxonomy (e.g. the DCM Taxonomy).
  `DEPRECATED` for retired terms.
- **Note:** TaxonomyTerm is the "spec"; Capability is "reality." Their gap drives back-fill
  (Discovered/OBSERVED capabilities with no term ⇒ propose a term ⇒ the taxonomy grows).

### 4.3 Alias
A normalization rule mapping a non-canonical string/term to its canonical TaxonomyTerm —
i.e. anti-vocabulary ("avoid → use instead") and discovered synonyms.
- **Fields:** avoid (handle), use_instead, reason, source (taxonomy | discovered | manual).
- **Relationships:** `resolves_to` → TaxonomyTerm.
- **States:** `CANONICAL` when seeded from a taxonomy's anti-vocabulary; `PROPOSED` →
  `CANONICAL` for synonyms discovered during normalization.

### 4.4 Antipattern
A pattern to avoid relative to the taxonomy/architecture (a "what not to do," with the
recommended alternative).
- **Fields:** name (handle), description, why, instead (recommended pattern), pillar,
  domain.
- **Relationships:** `related_to` → TaxonomyTerm / Capability.
- **States:** `PROPOSED` → `CANONICAL`; `DEPRECATED` when superseded.

### 4.5 DecisionRecord (a Decision Record / ADR — adopted, not invented)
> **Machine-validatable schema:** `registry/decision-record.schema.json` (data-model-core §2 [D8.6]); `registry/tools/validate.py` dispatches `record_type: decision_record`. The Data·Policy·Provider decomposition is schema-required (SPEC-DESIGN §29).
A `DecisionRecord` is the established **Decision Record (DR)** concept — of which an **ADR (Architecture Decision
Record) is the architecture-scoped kind** — expressed as a first-class UDLM entity. We **adopt the ADR/DR format
and lifecycle by reference** (per the "adopt, don't absorb" tenet, [core-tenets.md](../design-principles/core-tenets.md))
and add only what a loose markdown ADR lacks: **structure, anchoring, provenance, and (where applicable)
validation**. It records *why* a decision was made — the rationale resolving a Finding (or class) about a
Capability / dependency / spec element — so any realization carries decision provenance natively (pairs with
[Universal Audit](../observability/universal-audit.md) + field-level provenance). **An ADR = a DecisionRecord whose
anchor is architecture;** process/enablement decisions are DecisionRecords too.
- **Fields:** title (handle, e.g. `ADR-017`-style within an owning scope), **`rationale` / body (the prose ADR
  narrative — kept first-class; the structure is an *envelope* around it, never a replacement)**, question/finding
  refs, options_considered, decision, action (`answer | clarify | change-spec | defer | wontfix`),
  validation_evidence *(optional — see Note)*, supersedes, provenance (proposed_by: human + model/prompt version),
  **`abstraction_decomposition` (required: the `Data · Policy · Provider` aspects of the decision — the three
  foundational abstractions; SPEC-DESIGN-REQUIREMENTS §29). A record that can't name all three (or mark one
  "n/a, because…") isn't fully scoped.**
- **Relationships:** `decides` → Finding(s) *(future member; M:N — one record closes a class)*;
  `about` → Capability / TaxonomyTerm / spec element (the anchor it justifies); `produces` → a change/proposal
  *(realization-specific)*; `supersedes` → DecisionRecord.
- **States (curation = ADR status):** `PROPOSED` (drafted) → `UNDER_REVIEW` → `CANONICAL` (accepted / the
  authoritative WHY) → re-`OBSERVED` if its premises drift; `DEPRECATED`/superseded when a later record replaces
  it (ADR's "never edit, supersede" rule *is* UDLM immutability + `supersedes`).
- **Note (validation is a gate *where applicable*, not universal):** when the decision is testable, it reaches
  `CANONICAL` **only with passing use-case validation** (evaluated against UCs — submitted + generated-with-
  variance — on the same engine that finds gaps) — the WHY is *earned, not asserted*. Non-validatable decisions
  (e.g. a naming choice) may be `CANONICAL` without it, preserving compatibility with ordinary ADRs.
  Realization: `dav/docs/findings-resolution-design.md`; answers the "`depends_on` says *what* but not *why*"
  feedback by making the WHY a first-class, queryable record.
- **Scope & scope-appropriate validation.** A record's anchor places it in one of three scopes (the
  `Data · Policy · Provider` triad), and each reaches `CANONICAL` through *its own* mechanism — there is **no single
  "validation runner"**; validation is the scope's existing machinery:
  - **architecture-scoped** (an ADR; anchor = a foundational/architecture decision) → **use-case / conformance
    validation**.
  - **policy-scoped** (the *why* of a policy) → **Policy-Engine validation + Shadow Mode** (a `proposed` policy
    evaluated against real traffic, never applied).
  - **provider-scoped** (the *why* of a provider / capability adoption) → **attestation verification + conformance**.

  This is **distinct from a *runtime* decision** (a policy firing, a placement / provider selection), which is
  captured as **Audit + field-level provenance** ([Universal Audit](../observability/universal-audit.md)) — **not** a
  DecisionRecord. A DecisionRecord is the deliberate *why* at **authoring time** (any scope); audit is *what
  happened* at **runtime**. A consuming control plane (e.g. DCM) records its architecture decisions *as*
  architecture-scoped DecisionRecords (its ADRs) per this definition rather than maintaining a parallel form.

> **Fit with the UDLM model (coherence).** The ADR/DR sits cleanly on the substrate: it is `Data` (Knowledge),
> never a Provider/Policy (it may be *about* one); ADR's "supersede, don't edit" **is** UDLM immutability +
> versioning + `supersedes`; ADR status **is** the curation lifecycle; the `Discovered`/`OBSERVED` state adds
> *decision-drift* (do the premises still hold?) — a gain, not a clash. One semantic caveat: the four-state names
> carry provisioning connotation ("Requested" ≈ dispatched-to-a-provider), which the Knowledge family reinterprets
> as `UNDER_REVIEW` for curated artifacts. No structural incompatibility.

### 4.6 SoftwareImage · SoftwarePackage · Vulnerability — the software-supply-chain triad
Facts *about* resources (their bill-of-materials and its known vulnerabilities), discovered by a scanner sweep
and referenced by the resource estate — the first **knowledge-domain ingestion** under this family (the reusable
method: a discovery avenue → Knowledge classes → references-context edges → filter + blast-radius).

> **⚠ Proof of concept — not best practice.** Materializing these software facts as
> local-discovery Knowledge records is a **POC** to demonstrate filter + blast-radius; it is
> **not** the recommended production shape and **may be removed** for a more robust solution.
> The authoritative source for *what is deployed and its config* is the live **System of
> Record** — the cluster API and its **gitops repos** (once DCM-at-home lands, query OCP/gitops
> directly), and for SBOM a central SBOM/SCA/VEX store. The robust direction is to
> **reference / query the SOR on demand** rather than duplicate it here; a Knowledge record,
> where kept, should *point at* its SOR, not *be* it. *Which* SOR, refresh cadence, and
> precedence are an **operational detail each organization sets per its internal policy**.
> Tracked: [udlm#197](https://github.com/croadfeldt/udlm/issues/197) (principle),
> [udlm#188](https://github.com/croadfeldt/udlm/issues/188) (SBOM SoR),
> [dcm#66](https://github.com/croadfeldt/dcm/issues/66) (OCP/gitops SOR, DCM-at-home).
- **`SoftwareImage`** — a container image (correlation id: **digest**). *Adopts:* OCI image-spec. `contains`
  (→ SoftwarePackage) is its SBOM; referenced by `Compute.Container` via `runs_image`.
- **`SoftwarePackage`** — a library/package (correlation id: **purl**). *Adopts:* Package-URL + SPDX/CycloneDX
  component. One record per purl, shared by every image that contains it. `affected_by` (→ Vulnerability).
- **`Vulnerability`** — a CVE / GHSA / OSV advisory (correlation id: **id**). *Adopts:* OSV / NVD-CVE (+ VEX for
  status). Terminal in the chain; blast-radius reverse-walks from here.
- **Lifecycle:** curated upstream (NVD/OSV), **`Discovered`** locally (a scanner is a discovery avenue,
  dcm ADR-017) — never provider-realized.
- **Edges** are `kind: references` (non-ordering, so outside the shutdown sort) but **walked by
  blast-radius/impact in reverse** — "everything pointing to `Vulnerability#X`" = the affected package → image →
  container → app → host set.

## 5. Relationship graph (summary)

```
   Assessment/Finding ──surfaces──► Capability ──normalized_to──► TaxonomyTerm ◄──parent── TaxonomyTerm
        (future)                       │  ▲                            ▲
                                       │  └──depends_on (Capability)   │ resolves_to
                                  required_by                          │
                                       ▼                            Alias
                                   UseCase (future)        Antipattern ──related_to──► TaxonomyTerm / Capability
```

## 6. Future members
`Gap`, `Assessment`, `Finding`, **`Resolution`** extend this family as DAV's UDLM-conformance
expands beyond the capability catalog (the pilot). Each follows the curation archetype and
the universal contracts; all remain universal definitions, free to use by any realization.
(`SoftwareImage` / `SoftwarePackage` / `Vulnerability` have landed — §4.6.)

> **`Finding` / `Resolution`** arrive with the **Findings & Resolutions** realization
> (`dav/docs/findings-resolution-design.md`): a `Finding` is an externally-surfaced observation about the
> architecture (a review comment, a gap, an assessment finding); a `Resolution`/**`DecisionRecord`** (§4.5, defined
> now) is its validation-backed, capability-anchored answer — the **WHY**. Together they make this family the
> substrate's system of record for *why the model is the way it is*.
