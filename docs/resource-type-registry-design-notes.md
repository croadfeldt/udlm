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

## 5. Cross-cutting refinements (from the standards survey) + DCM-pillar impact

Six refinements (R1–R6) were adopted and analysed against DCM's hard requirements (`AUD-001/002` audit,
provider-contract §7 observability, `RDG-001` dependency-graph, Governance-Matrix sovereignty). **All
enhance** those pillars — see `design-principles/cross-cutting-requirements.md`. Two controls:
- **Guardrail G2 (hermetic expressions):** CEL/embedded expressions MUST be pure (no I/O) or they break
  air-gap and become an exfiltration path across a sovereignty boundary.
- **Discipline G3 (contract, not parallel implementation):** UDLM defines the provenance/dependency/policy
  *data contract*; DCM operationalizes it (Merkle audit, DAG engine, Governance Matrix). One model.

## 6. Decisions

- JSON Schema 2020-12 as the normative model; JSON **and** YAML native serialization.
- Two-axis versioning (modeled on NIST OSCAL's `version` + `oscal-version`); SPEC axis is major.minor only
  (CloudEvents); semver semantics machine-enforced by compat-check.
- `spec`/`outputs` = desired/observed seam (K8s/Crossplane/OSAC), but four-state, strongly typed.
- Avoid: version-in-identity (GVK), `$dynamicRef`, version-in-name, coupling the model to a runtime,
  collapsing intent↔reality with silent drift correction, redundant proxy entities.

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
