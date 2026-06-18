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
  Intent. (= PR #55 `fields[]` = OSAC `FieldDefinition` = PR #60 `cost_model` per-tier narrowing; §4a.)
- **E2 Typed realized-state outputs** — named, typed outputs published on Realized; the contract-checked
  binding surface (PR #55 flagged this as follow-up). Implemented as `outputs` in the meta-schema.
  (PR #60's metered/computed cost figures are the clearest E2 case — see §4a.)
- **E3 Conditional/dependent field constraints** — value of B depends on value of A. (PR #60's
  three-tier "present-in-spec" model is a presence-conditional instance — §4a.)
- **E4 Layered-overlay provenance** — type-default ⊕ offering-default ⊕ user-value, recording which
  layer set each field.
- **E5 Instance↔version pinning** — drift measured against the exact offering/type version realized.

## 4a. Third witness — dcm-project/enhancements#60 ("cost service type", pgarciaq)

PR #60 adds a fifth DCM `serviceType`, `cost` (backed by Red Hat Lightspeed Cost Management /
Project Koku, consumed by the cost-SP enhancement #57). Unlike the four compute types it provisions
**visibility** (metering, overhead distribution, financial tracking) over *other* resources, not
infrastructure. We evaluated it for UDLM fit (evaluation only — not commented on the PR). It maps
cleanly and is a **third independent re-derivation of E1/E2/E3** (after #55 and OSAC) — it validates
the model rather than stressing it, and is the cleanest illustration yet of the Data ⇄ Policy boundary.

| PR #60 element | UDLM home | Refinement |
|---|---|---|
| `cost` type itself | **Resource family / `Process` entityType**, `provisioning` archetype — a long-running observational process realized by a provider (Koku). Not Knowledge. | — |
| `target{resource_id, resource_type}` | a **typed relationship** (`references`/`binds_to`, cardinality `0..n`) to compute targets — cross-cutting "applies to other resources" = relationship-not-transformation. | T4 / R5 |
| `cost_model` · `rates` · `markup` · `distribution` · `currency` | **declarative `spec` data** (enums/defaults/numbers; no expression language). Narrowable per offering. | **E1** |
| three-tier model ("maps to what is *present* in the spec": basic = `cost_model` absent; distribution = present, `rates` absent; full = `rates` present) | **conditional-by-presence** via JSON Schema native (`dependentSchemas` / `if`-`then`) — no DSL. | **E3** |
| metered usage + computed cost figures (`cost = metering × rate`, overhead distribution) | **typed Realized-state `outputs`** the provider publishes; the *computation itself* is **Policy** (the provider's realization act), not carried in the data. | **E2** + T2 |

**Why it's the cleanest boundary witness:** UDLM carries the **rate table** (a noun — declarative
config in `spec`); the provider **computes the cost** (a verb — `metering × rate`, distribution by
cpu/memory). The PR keeps the tier mapping as a prose table, not a formula, so it already sits on the
correct side of guardrail **G2** — if anyone later embeds `cost = metering × rate` as an expression /
CEL in the spec, that is exactly the line G2 draws (transformation is Policy, applied by DCM).

**Divergences (shared with #55, all resolve in UDLM's favor, none blocking):** flat short
`serviceType` enum vs UDLM namespaced `Category.Type` (`cost` → e.g. `Observability.CostMeter`);
`resource_id` (an *instance* id) sits in the type schema, where UDLM keeps it on the INSTANCE (the
realized edge) with the TYPE only declaring the relationship.

**Worked translation:** `registry/resource-types/observability.cost-meter.json` is the end-to-end
proof — a `Resource`/`Process` type (first use of the `Process` entityType) where the rate table is
declarative `spec` data, the three tiers are a real JSON-Schema presence-conditional (E3; tier-3
rejects a missing `currency`), the metered/computed figures are typed `outputs` (E2), and the metered
targets are `references` edges to the compute types (E2/T4) with the resource id resolved on the
instance. `cost = metering × rate` appears only as prose in `computedCost`'s description — never as an
embedded expression (G2).

### Portability finding (the keystone) — and how to service vendor-specific intent universally

A first cut of the cost type marked itself `portable` while carrying **provider-shaped vocabulary**:
dcm#60's CostSpec uses free-text `metric` names (`cpu_core_usage_per_hour`, `node_cost_per_month`) and
a `cost_type` {Infrastructure, Supplementary} taxonomy — both Koku/OpenShift-specific. A meter authored
against them is serviceable by *one* vendor, which violates the core requirement (a Resource Type must
be **vendor-neutral — no provider-specific data**, `entities/resource-type-hierarchy.md` §"Resource
Types must be vendor-neutral"; provider detail lives in the **Provider Catalog Item**, not the type).

The fix is the general principle, and it answers "can we keep the vendor's *intent* in universal
language?" — **yes: carry the concept the vendor term encodes, not the term; the provider naturalizes
its native vocabulary to the universal one** (`contracts/provider-contract.md` naturalize → realize →
denaturalize). Three layered mechanisms, in order of preference:

1. **Name the concept, not the vendor term** — replace native metric strings with an **abstract
   dimension** enum (`compute_time`, `memory_time`, `storage_capacity`, …) aligned to an existing open
   standard (**FOCUS**, the FinOps Open Cost & Usage Specification — so the universal vocabulary is
   *adopted*, not invented; Koku, cloud billing exports, and Kubecost already emit FOCUS). The provider
   maps dimension → its native metric in its Catalog Item. The vendor *intent* survives verbatim:
   `cost_type` {Infrastructure, Supplementary} encodes a direct-vs-allocated distinction, captured
   universally as `category` {`direct`, `overhead`} — the provider naturalizes its taxonomy onto it.
   One meter, every compliant provider, no loss of meaning.
2. **Govern the universal vocabulary as a Knowledge taxonomy** — when the vocabulary itself must grow
   (new dimensions/categories), model the terms as `Knowledge.TaxonomyTerm` entities and have rates
   *reference* a term. Adding a dimension becomes a **curation act** (governed, versioned) rather than a
   schema change or a vendor fork. (This is why the Knowledge family and the Resource family share one
   registry — the cost type's vocabulary is itself curatable Knowledge.)
3. **Declared, portability-breaking extension point** — only for genuinely vendor-unique intent with no
   universal equivalent: the spec declares a typed, namespaced slot a provider's Catalog Item *may*
   fill, explicitly marked portability-breaking (`resource-type-hierarchy.md` §"extension points"). The
   portable core stays serviceable by everyone; the extension is additive, visible, and **never
   required** to realize the type.

Discipline: the portable type must be fully serviceable by *every* compliant provider on its own;
extensions are additive and flagged, never load-bearing. The shipped `Observability.CostMeter` carries
**zero** provider vocabulary (mechanism 1 + the FOCUS alignment); mechanisms 2–3 are the scaling path.
**Feedback for dcm#60:** lift `metric` to FOCUS-aligned abstract dimensions and `cost_type` to a
`direct`/`overhead` category, pushing the native-metric mapping into the cost-SP's Catalog Item —
otherwise the `cost` type is serviceable only by Koku, not "any provider."

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
