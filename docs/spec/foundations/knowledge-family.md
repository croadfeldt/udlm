# UDLM — Knowledge Entity-Type Family

**Family:** Knowledge (architecture / capability knowledge) — first exercised by the **DAV** implementation (a non-normative example; UDLM depends on no implementation — see `GLOSSARY.md`)

> The three foundational abstractions are in [foundations.md](foundations.md);
> the family concept in [Entity-Type Families](entity-type-families.md).
> **This document maps to: DATA.**
> **Universality:** these are UDLM definitions grouped here for organization. They are
> **free to use by any implementation, regardless of family** — the control plane or any peer may use a
> `Capability` exactly as the first implementation does. Constraints apply to *instances* (ownership,
> classification, scope), never to these definitions.
> **Implementation:** `dav/docs/capability-catalog-design.md`. Case study:
> [`../../examples/case-study-dav-knowledge-realization.md`](../../examples/case-study-dav-knowledge-realization.md).

---

## 1. Domain

The Knowledge family models **architecture and capability knowledge** — the artifacts a
system reasons about when it asks *"what should be able to happen, what does it take, and
where are the gaps"*? Where the Resource family tracks resources through **provisioning**,
the Knowledge family tracks definitions through **curation**: proposed → reviewed →
canonical, against a backdrop of what is **observed** in the field.

## 2. Lifecycle archetype — curation (the family's four-state interpretation)

Every Knowledge entity is UDLM Data and exists in the four states; the family interprets
them for curated knowledge:

| UDLM state | Knowledge interpretation | Storage semantics |
|------------|--------------------------|-------------------|
| **Intent** | `proposed` — a proposed definition ("what we think should exist") | append-only, immutable record of the proposal |
| **Requested** | `under_review` — the proposal submitted into curation (the contribution under review) | append-only per review cycle |
| **Realized** | `canonical` — accepted, authoritative | versioned snapshots, `is_current` flag |
| **Discovered** | `observed` — what an assessment / UC analysis observes in the field | ephemeral, refreshed per assessment/analysis run |

Shared state machine skeleton (per-type tweaks allowed):

```
observed ─┐                        (parallel evidence from the field)
          ▼
proposed ──► under_review ──► canonical ──► deprecated
   ▲             │
   └─────────────┘  (revision)
```

**The signature operation:** the gap between `canonical` (what should be) and `observed`
(what an assessment found) is **drift detection applied to knowledge** — identical in shape
to the Resource family's Realized-vs-Discovered drift. This *is* the first implementation's gap analysis.

## 3. Shared semantics

- **Universal contracts honored:** UUID stable across lifecycle; record identity, version
  and status (layering-and-versioning §4b); field-level
  provenance; data classification; contributor identity (the LLM-proposes / human-curates
  step is UDLM's federated-contribution model).

- **Provenance is first-order:** every field records origin — e.g. a `Capability.domain`
  sourced from the control plane taxonomy vs an `evidence` field sourced from a specific assessment
  finding.

- **Classification defaults:** canonical, shared vocabulary (TaxonomyTerm, Alias,
  Antipattern seeded from public taxonomy) defaults **public**; field-derived
  instances (e.g. capabilities discovered in a client assessment) default
  **client-confidential**. Set per instance, per field.

- **Family tag:** every definition here carries `family: Knowledge` — the disambiguation
  namespace (see [Entity-Type Families §6](entity-type-families.md)). So
  `Capability [Knowledge]` is distinct from any same-named term in another family, and
  collision-prone words (`Process`, `Policy`, `Service`, `Provider`, `Capability`) stay
  unambiguous as "term + family". It disambiguates meaning; it does not restrict use.

- **Ownership / scope is instance-level**, per
  [Ownership, Sharing, and Allocation](ownership-sharing-allocation.md):
  global / shared / domain / project tiers (the first implementation's tier+tags model maps onto this). The
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

- **States:** typically enters as `observed` (from an assessment) and/or `proposed`, then
  `under_review` → `canonical`; `deprecated` is terminal.

### 4.2 TaxonomyTerm
A canonical vocabulary term — the **normalization authority** the catalog normalizes onto.

- **Fields:** term (handle), definition, pillar, domain (prefix + name), parent
  (→ TaxonomyTerm), normalization_rules (how to normalize items for this subject matter),
  category (source grouping).

- **Relationships:** `parent` → TaxonomyTerm; normalized **by** Capability/Alias.

- **States:** `proposed` (a back-fill candidate the catalog surfaced) → `under_review` →
  `canonical`. Seeded `canonical` from an authoritative taxonomy (an implementation's own, for example).
  `deprecated` for retired terms.

- **Note:** TaxonomyTerm is the "spec"; Capability is "reality." Their gap drives back-fill
  (Discovered/observed capabilities with no term ⇒ propose a term ⇒ the taxonomy grows).

### 4.3 Alias
A normalization rule mapping a non-canonical string/term to its canonical TaxonomyTerm —
i.e. anti-vocabulary ("avoid → use instead") and discovered synonyms.

- **Fields:** avoid (handle), use_instead, reason, source (taxonomy | discovered | manual).

- **Relationships:** `resolves_to` → TaxonomyTerm.

- **States:** `canonical` when seeded from a taxonomy's anti-vocabulary; `proposed` →
  `canonical` for synonyms discovered during normalization.

### 4.4 Antipattern
A pattern to avoid relative to the taxonomy/architecture (a "what not to do," with the
recommended alternative).

- **Fields:** name (handle), description, why, instead (recommended pattern), pillar,
  domain.

- **Relationships:** `related_to` → TaxonomyTerm / Capability.

- **States:** `proposed` → `canonical`; `deprecated` when superseded.

### 4.5 DecisionRecord (a Decision Record / ADR — adopted, not invented)
> **Machine-validatable schema:** `registry/decision-record.schema.json` (data-model-core §2 [D8.6]); `registry/tools/validate.py` dispatches `record_type: decision_record`. The Data·Policy·Provider decomposition is schema-required (SPEC-DESIGN §29).
A `DecisionRecord` is the established **Decision Record (DR)** concept — of which an **ADR (Architecture Decision
Record) is the architecture-scoped kind** — expressed as a first-class UDLM entity. We **adopt the ADR/DR format
and lifecycle by reference** (per the "adopt, don't absorb" tenet, [core-tenets.md](../principles/core-tenets.md))
and add only what a loose markdown ADR lacks: **structure, anchoring, provenance, and (where applicable)
validation**. It records *why* a decision was made — the rationale resolving a Finding (or class) about a
Capability / dependency / spec element — so any implementation carries decision provenance natively (pairs with
[Universal Audit](../contracts/universal-audit.md) + field-level provenance). **An ADR = a DecisionRecord whose
anchor is architecture;** process/enablement decisions are DecisionRecords too.

- **Fields:** title (handle, e.g. `DCM ADR-017`-style within an owning scope). **`rationale` / body is the prose
  ADR narrative — kept first-class; the structure is an *envelope* around it, never a replacement**. The remaining
  fields: question/finding refs, options_considered, decision, action (`answer | clarify | change_spec | defer |
  wontfix`), validation_evidence *(optional — see Note)*, supersedes, provenance (proposed_by: human + model/prompt
  version). **`abstraction_decomposition` is required: the `Data · Policy · Provider` aspects of the decision — the
  three foundational abstractions; SPEC-DESIGN-REQUIREMENTS §29. A record that can't name all three (or mark one
  "n/a, because…") isn't fully scoped.**

- **Relationships:** `decides` → Finding(s) *(future member; M:N — one record closes a class)*;
  `about` → Capability / TaxonomyTerm / spec element (the anchor it justifies); `produces` → a change/proposal
  *(implementation-specific)*; `supersedes` → DecisionRecord.

- **States (curation = ADR status):** `proposed` (drafted) → `under_review` → `canonical` (accepted / the
  authoritative WHY) → re-`observed` if its premises drift; `deprecated`/superseded when a later record replaces
  it (ADR's "never edit, supersede" rule *is* UDLM immutability + `supersedes`).

- **Note (validation is a gate *where applicable*, not universal):** when the decision is testable, it reaches
  `canonical` **only with passing use-case validation** (evaluated against UCs — submitted + generated-with-
  variance — on the same engine that finds gaps). The WHY is *earned, not asserted*. Non-validatable decisions
  (e.g. a naming choice) may be `canonical` without it, preserving compatibility with ordinary ADRs.
  Implementation: `dav/docs/findings-resolution-design.md`; answers the "`depends_on` says *what* but not *why*"
  feedback by making the WHY a first-class, queryable record.

- **Scope & scope-appropriate validation.** A record's anchor places it in one of three scopes (the
  `Data · Policy · Provider` triad), and each reaches `canonical` through *its own* mechanism — there is **no single
  "validation runner"**; validation is the scope's existing machinery:

  - **architecture-scoped** (an ADR; anchor = a foundational/architecture decision) → **use-case / conformance
    validation**.

  - **policy-scoped** (the *why* of a policy) → **Policy-Engine validation + Shadow Mode** (a `proposed` policy
    evaluated against real traffic, never applied).

  - **provider-scoped** (the *why* of a provider / capability adoption) → **attestation verification + conformance**.

  This is **distinct from a *runtime* decision** (a policy firing, a placement / provider selection), which is
  captured as **Audit + field-level provenance** ([Universal Audit](../contracts/universal-audit.md)) — **not** a
  DecisionRecord. A DecisionRecord is the deliberate *why* at **authoring time** (any scope); audit is *what
  happened* at **runtime**. A consuming control plane records its architecture decisions *as*
  architecture-scoped DecisionRecords (its ADRs) per this definition rather than maintaining a parallel form.

> **Fit with the UDLM model (coherence).** The ADR/DR sits cleanly on the substrate: it is `Data` (Knowledge),
> never a Provider/Policy (it may be *about* one); ADR's "supersede, don't edit" **is** UDLM immutability +
> versioning + `supersedes`; ADR status **is** the curation lifecycle; the `Discovered`/`observed` state adds
> *decision-drift* (do the premises still hold?) — a gain, not a clash. One semantic caveat: the four-state names
> carry provisioning connotation ("Requested" ≈ dispatched-to-a-provider), which the Knowledge family reinterprets
> as `under_review` for curated artifacts. No structural incompatibility.

### 4.6 SoftwareImage · SoftwarePackage · Vulnerability — the software-supply-chain triad
Facts *about* resources (their bill-of-materials and its known vulnerabilities), discovered by a scanner sweep
and referenced by the resource estate — the first **knowledge-domain ingestion** under this family. The reusable
method: a discovery avenue → Knowledge classes → references-context edges → filter + blast-radius.

> **⚠ Proof of concept — not best practice.** Materializing these software facts as
> local-discovery Knowledge records is a **POC** to demonstrate filter + blast-radius; it is
> **not** the recommended production shape and **may be removed** for a more robust solution.
> The authoritative source for *what is deployed and its config* is the live **System of
> Record** — the cluster API and its **gitops repos** (once control-plane-at-home lands, query OCP/gitops
> directly), and for SBOM a central SBOM/SCA/VEX store. The robust direction is to
> **reference / query the SOR on demand** rather than duplicate it here; a Knowledge record,
> where kept, should *point at* its SOR, not *be* it. *Which* SOR, refresh cadence, and
> precedence are an **operational detail each organization sets per its internal policy**.
> Tracked: [udlm#197](https://github.com/croadfeldt/udlm/issues/197) (principle),
> [udlm#188](https://github.com/croadfeldt/udlm/issues/188) (SBOM SoR),
> [dcm#66](https://github.com/croadfeldt/dcm/issues/66) (OCP/gitops SOR, control-plane-at-home).

- **`SoftwareImage`** — a container image (correlation id: **digest**). *Adopts:* OCI image-spec. `contains`
  (→ SoftwarePackage) is its SBOM; referenced by `Container` via `runs_image`.

- **`SoftwarePackage`** — a library/package (correlation id: **purl**). *Adopts:* Package-URL + SPDX/CycloneDX
  component. One record per purl, shared by every image that contains it. `affected_by` (→ Vulnerability).

- **`Vulnerability`** — a CVE / GHSA / OSV advisory (correlation id: **id**). *Adopts:* OSV / NVD-CVE (+ VEX for
  status). Terminal in the chain; blast-radius reverse-walks from here.

- **Lifecycle:** curated upstream (NVD/OSV), **`Discovered`** locally (a scanner is a discovery avenue,
  DCM ADR-017) — never provider-realized.

- **Edges** are `edge_type: references` (non-ordering, so outside the shutdown sort) but **walked by
  blast-radius/impact in reverse** — "everything pointing to `Vulnerability#X`" = the affected package → image →
  container → app → host set.

### 4.7 Pattern
A pattern to follow — the reusable "what a thing of this kind IS" at type level: Antipattern's
twin, positive polarity. ADR-033 places Pattern in Knowledge as a **definition** — the first of the
Pattern → Template → System chain's two definition tiers, where a Pattern leaves parts open and a
Template has cut them. ADR-033 also deliberately deferred the schema implementation "unless a use
case pulls it in". The pull arrived: an external field-device fleet adopter models "what a field device of role X is"
(the capabilities a role requires, the shape a season build asserts) as reusable role
definitions, exactly this member.

- **Fields:** name (handle), description, why (the outcome the pattern serves), pillar,
  domain — Antipattern's field shape at positive polarity.

- **Relationships:** `related_to` → TaxonomyTerm / Capability (the capabilities the pattern
  requires or asserts); a Template (ADR-033) `refines` a Pattern — a reference between two
  definitions, so one Pattern yields many Templates.

- **States:** `proposed` → `canonical`; `deprecated` when superseded.

### 4.8 SovereigntyZone
What a coined zone name means jurisdictionally. The accreditation side speaks ISO 3166
(`scope.geographic_scope`); the entity side carries `sovereignty.zone`, a coined label such as
`eu-west`. Nothing connected them, so the §3.8 residency-subsumption rule had nothing to evaluate.
A zone declares the jurisdictions it spans in the accreditation's own vocabulary, which turns that
match from an assumption into a computation. Knowledge rather than Resource because a zone is
declared, curated and never realized by a provider — the Vulnerability shape: a structured record
whose truth is held by the party that declares it.

- **Fields:** jurisdictions (ISO 3166-1/3166-2, required and non-empty), regimes (supranational,
  e.g. EU), description. **Physical location is deliberately absent** — that is `Location`,
  and it does not cross a peer boundary.

- **Relationships:** cited by a realized entity's `sovereignty.zone`; matched against an
  accreditation's `scope.geographic_scope`.

- **States:** `proposed` → `canonical`; established at setup and governed thereafter.

### 4.9 TestEvidence
The evidence one test provides about a subject — any test, from any suite, in the result format the
suite already emits (CTRF or JUnit). A suite that checks a vulnerability binds at the Type
`TestEvidence.VulnerabilityCheck`. Class: `registry/classes/knowledge/test-evidence/_base.yaml`.

- **Fields:** test_id, subject_ref, category, result, job_ref, file_path, file_digest, scope.

- **Relationships:** `references` → Job (`produced_by` — the run that executed the test).

### 4.10 VexStatement
One exploitability claim about one vulnerability in one package version, with the evidence it rests
on. It carries the OpenVEX status (affected, not affected, fixed, under investigation), the
justification label when the status is not affected, and references to the tests that back it. A harness or a scanner
drafts it (the intent record); product security confirms it (the realized record). Class:
`registry/classes/knowledge/vex-statement/_base.yaml`.

- **Fields:** vulnerability_ref, software_package_ref, status, justification, status_notes,
  evidence_refs, document_url.

- **Relationships:** `references` → Vulnerability (`about`), → SoftwarePackage, → TestEvidence.

- **States:** `proposed` (drafted) → `canonical` (confirmed); `deprecated` when superseded.

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
`Gap`, `Assessment`, `Finding`, **`Resolution`** extend this family as the first implementation's UDLM-conformance
expands beyond the capability catalog (the pilot). Each follows the curation archetype and
the universal contracts; all remain universal definitions, free to use by any implementation.
(`SoftwareImage` / `SoftwarePackage` / `Vulnerability` have landed — §4.6.)

> **`Finding` / `Resolution`** arrive with the **Findings & Resolutions** implementation
> (`dav/docs/findings-resolution-design.md`): a `Finding` is an externally-surfaced observation about the
> architecture (a review comment, a gap, an assessment finding); a `Resolution`/**`DecisionRecord`** (§4.5, defined
> now) is its validation-backed, capability-anchored answer — the **WHY**. Together they make this family the
> substrate's system of record for *why the model is the way it is*.
