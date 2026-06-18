# Design Notes — Resource Type Registry + Cross-Cutting Requirements

Rationale, sources, and decision trail behind `registry/` and
`design-principles/cross-cutting-requirements.md`. Written 2026-06-17.

## 1. Trigger

`dcm-project/enhancements#55` ("Composite catalog item schema definition," jenniferubah, FLPATH-4221)
proposed a Service-Catalog schema: `CatalogItem` blueprints of `resources[]` (each with a
`serviceType`, `requiresResources` DAG ordering, and per-field `editable`/`default`/`validationSchema`),
`CatalogItemInstance` orders, and a resolution step producing an effective resource graph for placement,
with CEL (`${ordersDb.connectionString}`) cross-resource wiring.

## 2. Key finding — three independent re-derivations of one model

The PR's model is, almost 1:1, UDLM's **Composite Service Composition Model**
(`entities/composite-service-model.md`): CatalogItem ≈ Composite Service ("a catalog item"),
`resources[]` ≈ `constituents[]`, `requiresResources` ≈ `depends_on` → DAG, CEL wiring ≈ binding fields
filled from dependencies' realized state, the four states traversed by one Composite Entity.

Independently, **Red Hat OSAC** (Open Sovereign AI Cloud; public `osac-project` GitHub org) converged on
the *same* shape: Kubernetes-style `spec`/`status`+`conditions`, **JSON Schema 2020-12** validation, and a
**Template → CatalogItem → Instance** catalog. OSAC's `FieldDefinition{path, editable, default,
validation_schema}` is the same constrained-offering concept.

→ Three independent designs (UDLM's composite model, PR #55, OSAC's fulfillment API) re-derived the same
substrate. That is strong validation of UDLM's design, and it is the argument for making UDLM the shared
substrate rather than each project re-modeling it.

## 3. What we built

- **`registry/resource-type-spec.schema.json`** — meta-schema for a Resource Type Specification
  (instantiating `entities/resource-type-hierarchy.md`). JSON Schema 2020-12 (normative per
  `contracts/schema-sharing.md`). Two version axes: `conformsTo` (SPEC) + `version` (ENTITY).
  `spec` = Intent/Requested wire contract; `outputs` = typed Realized state.
- **`registry/resource-types/`** — Compute.VirtualMachine, Data.Database, Network.IPAddress (JSON),
  Compute.Container (YAML). JSON and YAML both native.
- **`registry/VERSIONING.md`**, **`registry/SPEC-DESIGN-REQUIREMENTS.md`**, **`registry/tools/`**
  (valid-by-construction + compat-check).
- **`design-principles/cross-cutting-requirements.md`** — the DCM pillars as UDLM principles.

## 4. Enhancements UDLM should absorb (from PR #55 / OSAC)

- **E1 Constraint Profile / Offering** — the curated, defaulted, *narrowed* projection over a type's
  wire contract (per-field editable/default/tightened-validation). The missing middle between Type and
  Intent. (= PR #55 `fields[]` = OSAC `FieldDefinition`.)
- **E2 Typed realized-state outputs** — named, typed outputs published on Realized; the contract-checked
  binding surface (PR #55 flagged this as follow-up). Implemented as `outputs` in the meta-schema.
- **E3 Conditional/dependent field constraints** — value of B depends on value of A.
- **E4 Layered-overlay provenance** — type-default ⊕ offering-default ⊕ user-value, recording which
  layer set each field.
- **E5 Instance↔version pinning** — drift measured against the exact offering/type version realized.

## 4a. Cost — and the absorb-vs-adopt boundary (dcm#60 / #57)

PR #60 adds a fifth DCM `serviceType`, `cost`; PR #57 is the **Cost Management Service Provider**
(cost-SP) that consumes it, backed by Red Hat Lightspeed Cost Management / Project Koku. We evaluated
cost for UDLM fit (evaluation only — not commented on the PRs). The investigation went down a wrong
path and back up, and the wrong path is the most useful part of the finding, so it is recorded here.

### What was tried, and why it was retired

A first attempt modeled cost as a UDLM Resource type — `Observability.CostMeter`
(`registry/resource-types/observability.cost-meter.json`, a `Resource`/`Process` type with a rate
table in `spec`, an E3 presence-conditional for the three tiers, FOCUS-aligned dimensions, and typed
`outputs`). **It has been retired (removed from the registry).** It was the experiment that *proved*
where the boundary is, and the three reasons it was wrong are the contribution:

1. **It absorbed data UDLM should not own.** `contracts/information-providers.md` §2 is explicit:
   contextual data like **cost attribution** "lives in authoritative external systems (finance
   systems…) that DCM does not and should not own," and it names the two anti-patterns — **copy the
   data in** (duplication, staleness, ownership conflict) vs ignore it. Re-modeling a cost schema in
   the registry *is* "copy the data in." It violates **T1** (the data model is the lifecycle custodian,
   not the owner of every domain's data).
2. **It reinvented an existing standard.** There is already a vendor-neutral cost data model —
   **FOCUS** (FinOps Open Cost & Usage Specification, FinOps Foundation; current **v1.4**, ratified
   2026-06-04) for cost/usage records, and **OpenCost** (CNCF) for Kubernetes cost allocation. A UDLM
   cost type would re-express FOCUS columns badly. Don't rebuild the wheel; **reference** it.
3. **#60 doesn't ask for it.** #60 lives in `service-type-definitions.md` — it *defines a service type
   for consumption* (the provider-facing contract a Service Provider implements), the same pattern as
   vm/container/database/cluster. It does **not** embed cost into the universal data model. The
   "absorb" instinct was ours, not the PR's; modeling a competing UDLM type would duplicate a
   correctly-placed DCM contract (**G3** — contract, not parallel implementation).

### The resolution — cost is *adopted*, not absorbed

"Adopt" = **reference an external standard/provider by conformance and binding, rather than re-model it
in the data substrate.** Three distinct dispositions, and cost takes the third:

- **Absorb** — define the schema inside UDLM (a Resource type). ✗ rejected (reasons above).
- **Embed** — bake cost fields into every realized entity. ✗ never proposed; same T1 violation, worse.
- **Adopt / reference** — UDLM owns only the **identity** (the join key) and the **binding**; the data
  conforms to **FOCUS/OpenCost** and is served by a provider. ✓

Concretely, #57 is already structurally a UDLM-shaped **cost-recovery provider** — a hybrid that maps
onto seams the substrate already has:

| What the cost-SP (#57) does | The seam it already *is* |
|---|---|
| Provisions Koku sources + cost models when infra is provisioned | **Service Provider** (the provisioning act) |
| "Read-only query API… exposes metering and cost data from Koku" | **Information Provider** (`contracts/information-providers.md`) — serves data DCM references but does not own |
| "Rego policies enforce rate ranges, markup, budgets" | **Policy** (rate *enforcement* is OPA/Rego — exactly T2/G2) |
| The CostSpec rate table | **Data** (the declarative rate noun) |

So UDLM's role for cost is small and bounded: **(a)** resource identity / handle = the join key
(FOCUS `ResourceId`); **(b)** an Information-Provider **binding** declaring "this resource has cost
data from source X, conforming to FOCUS, joined on identity"; **(c)** the confidence / authority /
provenance wrapper the IP contract (`contracts/information-providers-advanced.md`) already gives every
referenced field. The cost **model** is adopted (FOCUS + OpenCost); the **computation** is the
provider's; the **enforcement** is Policy. Nothing enters the registry.

### Keeping vendor intent in universal language (still applies — at the data, not a type)

The earlier finding survives, repositioned to the consumable cost *data* rather than a UDLM type:
**carry the concept a vendor term encodes, not the term; the provider naturalizes its native
vocabulary to the universal one** (`contracts/provider-contract.md` naturalize → realize →
denaturalize). The three mechanisms, in order:

1. **Name the concept via an adopted standard** — express usage over FOCUS dimensions / `ConsumedUnit`,
   not native metric strings; map the direct-vs-allocated intent (Koku's Infrastructure/Supplementary)
   to FOCUS 1.3 **allocation columns** + OpenCost's workload/idle split. The provider maps its native
   metrics → FOCUS in its own layer.
2. **Govern any gap vocabulary as a Knowledge taxonomy** — terms FOCUS/OpenCost don't yet cover become
   `Knowledge.TaxonomyTerm` entities (a curation act, governed + versioned), never a vendor fork.
3. **Declared, portability-breaking extension** — last resort for genuinely vendor-unique intent;
   additive, flagged, never required.

### Feedback for #60 / #57 (evaluation only)

Right layer (a consumable service type, not a data-model change) — but it defines a **bespoke** cost
vocabulary (Koku's 40+ dimensions, Infrastructure/Supplementary, its own rate model), so the
*consumable cost data* is Koku-shaped and a second cost provider couldn't serve the same contract. The
portability fix is **not** "move it into UDLM" — it is **"have the consumable cost data conform to
FOCUS (+ OpenCost for k8s allocation)."** Rate-card *authoring* can stay a thin provider offering
(rate cards are finance-policy by nature); the cost data tenants query should be FOCUS, so cost
recovery is provider-agnostic. Net: **UDLM absorbs nothing** — cost is an adopted standard
(FOCUS/OpenCost) served by an adopted provider pattern (cost-recovery SP + Information Provider), bound
to UDLM resources by identity.

## 5. Cross-cutting refinements (from the standards survey) + DCM-pillar impact

Six refinements (R1–R6) were adopted and analysed against DCM's hard requirements (`AUD-001/002` audit,
provider-contract §7 observability, `RDG-001` dependency-graph, Governance-Matrix sovereignty). **All
enhance** those pillars — see `design-principles/cross-cutting-requirements.md`. Two controls:
- **Guardrail G2 (no embedded expressions):** the portable data carries no expression language. Bindings
  are declarative typed references (`targetField` → output; Data, in the spec); all
  transformation/enrichment (incl. CEL) is **Policy**, applied by DCM. Determinism + reproducibility are
  therefore *structural* (the precondition for tamper-evident audit + sovereignty), not policed.
- **Discipline G3 (contract, not parallel implementation):** UDLM defines the provenance/dependency/policy
  *data contract*; DCM operationalizes it (Merkle audit, DAG engine, Governance Matrix). One model.

## 6. Decisions

- JSON Schema 2020-12 as the normative model; JSON **and** YAML native serialization.
- Two-axis versioning (modeled on NIST OSCAL's `version` + `oscal-version`); SPEC axis is major.minor only
  (CloudEvents); semver semantics machine-enforced by compat-check.
- `spec`/`outputs` = desired/observed seam (K8s/Crossplane/OSAC), but four-state, strongly typed.
- **Bindings vs expressions (settled):** cross-entity bindings are *declarative typed references*
  (`targetField` → output) carried in the spec; **expressions/transformation (incl. CEL) are not in the
  data model — they are Policy, applied by DCM.** Conditional constraints (E3) use JSON Schema native
  (`if`/`then`, `dependentSchemas`), not an expression language. (core-tenets T2/T4/G2 — not to be re-litigated.)
- Avoid: version-in-identity (GVK), `$dynamicRef`, version-in-name, coupling the model to a runtime,
  collapsing intent↔reality with silent drift correction, redundant proxy entities.

## 6a. Domain assignment — applying the Data ⇄ Policy boundary

Per the core tenets (`design-principles/core-tenets.md`), every capability splits along the domain
boundary: **UDLM carries the declarative record (the noun); DCM applies the act (the verb).** Nothing
is dropped — each is assigned to the domain that owns it.

| Capability | **Data domain — UDLM carries** | **Policy domain — DCM applies** |
|---|---|---|
| Four states | the 4 immutable state records + legal-shape | the act of transitioning / realization |
| Versioning (R1) | `$id`, `conformsTo`, `version`, compat rules as data | resolving a version constraint; conversion |
| E1 Constraint Profile | the narrowed contract (a data artifact) | applying profile defaults at Intent→Requested |
| E2 Typed outputs | the output schema + realized values | publishing (provider) + binding resolution |
| E3 Conditional constraints | **declarative only** (`if/then`, `dependentSchemas`, `enum`) | complex cross-field logic → policy evaluation |
| E4 Provenance | the per-field provenance record | the merge/overlay act + conflict resolution |
| E5 Version pinning | the recorded pin (a reference) | drift comparison against the pin |
| R3 Immutability | the `createOnly` marker | **enforcing** it (reject the change) |
| R4 Field ownership | the `managedFields` record | SSA conflict detection/resolution |
| R5 Relationships | typed edges + `targetField` refs | DAG construction, ordering, traversal, compensation |
| R6 Tombstones/bundling | `supersededBy` + Compound Document | — |
| Binding | the edge + typed reference | resolution at dispatch; **any transform** |
| Sovereignty | immutable zone/classification fields, closure bundle | Governance Matrix evaluation, placement filtering |
| Audit | the immutable records, provenance, hash-chain leaves | producing entries, Merkle proofs |
| Transformation / expressions | — (none; not carried) | **all of it** |

The test: a noun (a record, a contract, an edge, a marker, a pin) → Data/UDLM. A verb (assemble,
evaluate, decide, enforce, transform, resolve) → Policy/DCM. **CEL and any embedded expression fall
entirely on the Policy side and are not carried in the portable data.**

## 7. Open questions / not yet done — see §"left out" in the PR description.

## 8. Resources pulled in

**OSAC:** Red Hat Research project page (research.redhat.com/blog/research_project/open-sovereign-ai-cloud/);
`github.com/osac-project` (`fulfillment-service` protos `proto/public/osac/public/v1/`,
`fulfillment-api` OpenAPI, `docs/designdoc.md`).

**Standards surveyed (lessons in the survey synthesis):**
- TOSCA v1.3 (OASIS) — capability/requirement matching.
- OAM/KubeVela — `output` block = typed realized state.
- Crossplane XRD/Composition/Revisions — strict spec/status; immutable monotonic revisions.
- Terraform provider schema — `Computed`=realized; ordered StateUpgraders.
- AWS CloudFormation resource schema + Cloud Control API — `readOnly`/`createOnly` property classes; uniform CRUD-L.
- Azure ARM/Bicep — per-type dated apiVersion; `apiProfile` bundles.
- Google Config Connector — typed GVK+`targetField` refs; stability propagation.
- Open Service Broker + (retired) K8s Service Catalog — async 202→poll; cautionary bolt-on-catalog retirement.
- Backstage software catalog — relations derived from declared, validated fields.
- SCIM (RFC 7643/7644) — runtime schema discovery; URI-namespaced extensions; additive-only within major.
- Open Cluster Management — ManifestWork(requested) vs AppliedManifestWork(realized); per-entity maturity coexists.
- **NIST OSCAL** — the closest precedent: `version` + `oscal-version` metadata; import traceability.
- CloudEvents — `specversion` major.minor only.
- AsyncAPI — cautionary: no per-component version → name-mangling (validates our per-entity version).
- schema.org — `supersededBy` tombstones; never delete within a major.
- RDF/OWL/SHACL — declared versioned dependency; closed-world validation (we keep closed-world).
- JSON Schema 2020-12 — `$id` encodes versions; vocabularies for UDLM keywords; Compound Documents for offline
  bundling; avoid `$dynamicRef`.
- Kubernetes API machinery — CRD structural schemas, GVK (avoid version-in-name), spec/status, conversion +
  storage version, deprecation policy, server-side-apply/managedFields (field ownership), CEL
  `x-kubernetes-validations`, defaulting, subresources, discovery (KEP-3352), ownerReferences/finalizers.

**UDLM internal:** `entities/{composite-service-model,resource-type-hierarchy,resource-service-entities,
service-dependencies}.md`, `foundations/{four-states,layering-and-versioning,entity-type-families}.md`,
`contracts/{schema-sharing,identifier-scheme,provider-contract}.md`, the audit/observability/governance docs
(`AUD-001/002`, provider-contract §7, `RDG-001`, the Governance Matrix + sovereignty zones).
