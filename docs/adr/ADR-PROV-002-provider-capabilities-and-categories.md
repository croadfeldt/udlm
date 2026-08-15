# ADR-PROV-002: Provider capabilities and capability categories — one unified interface; providers declare capabilities as (verb × domain), explicitly domain-scoped; a governed capability taxonomy (TaxonomyTerm) organizes them; categories (capability × resource-domain, non-exclusive) group them; policy targets category, capability, or data

**Status:** Proposed
**Realized by:** _not yet_ — decided, no machine surface.
**Type:** Architecture Decision Record — a `DecisionRecord` with architecture scope (`docs/spec/foundations/knowledge-family.md` §4.5)

**Background — read first (the cold reader's on-ramp; skip if you have the context).** The surfaces this decision governs: `docs/spec/contracts/provider-contract.md` §10 (capability discovery) ·
`docs/spec/contracts/provider-contract.md` · `docs/spec/contracts/storage-providers.md` ·
`docs/spec/contracts/information-providers.md`

## Context

The unified provider model already replaced fixed provider types with a closed capability
vocabulary (capability-discovery.md §2 — a provider declares capabilities, not a type; an
InfoBlox IPAM both serves data AND provisions, so a single system with two capabilities must
not register twice). Two gaps remain. FIRST, the legacy type names
(Storage/Service/Information/Auth Provider) still appear as first-class TYPES in places —
storage-providers.md calls a Storage Provider 'the fourth formal the control plane provider type … one of
eleven'; provider-contract.md keeps a 'Provider Type Registry' and a provider_type_id; and the
Governance Matrix still matches on target.type (policy-evaluation.md:43). The migration is
half-done, so the mutually-exclusive-type bug the unified model rejected still lives in the
drift. SECOND, the model has no first-class grouping between the fine-grained capability atom
and the whole provider. To write differentiated policy ('encrypt at rest for storage
provisioning but not compute') you must target a GROUPING; to let one provider serve multiple
roles those groupings must be NON-EXCLUSIVE. The clean primitive is a CATEGORY: a named, non-
exclusive grouping defined as capability × resource-domain, DERIVED from the capabilities a
provider declares and the domains they operate over. A provider that both provisions storage
(realize_resources / Storage.*) and serves what is stored (serve_data) belongs to BOTH the
storage-provisioning and information categories at once — no double registration. Categories
reuse the existing capability vocabulary (no new atoms) and the resource-type domains already
in the registry, and become a Governance-Matrix match source alongside capability and the
existing data axes (data_classification, data_role) — so policy can target a category, a
capability, or the data itself. This finishes the type→capability migration (types become
categories, never exclusive), keeps the provider INTERFACE uniform (the standardize-the-
mechanics / simplify-integration goal), and gives policy the targeting granularity the
platform needs. NB: the grouping is a 'category', NOT a 'role' — 'role' is already the data-
purpose axis (data_role: execution | assembly | governance | audit | cost, ADR-PROV-001).
Provider-grouping and data-purpose must not collide in policy authors' minds. THIRD,
capability domain-dependence must be EXPLICIT, not inferred: a capability declaration already
half-carries its domain (realize_resources carries resource_types; serve_data carries
data_domains) but in inconsistent shapes — a capability is properly (verb × domain-scope) and
MUST declare the domain(s) it operates over uniformly, because both category derivation and
per-domain policy depend on it. FOURTH, the capability vocabulary should be a GOVERNED
TAXONOMY, not a flat closed list — new capabilities and domains arrive over time and need the
same tiered governance (Core / Verified / Org) and hierarchy as other registry vocabularies.
The substrate already has the machinery: TaxonomyTerm (Knowledge family, knowledge-family.md
§4.2) is the canonical hierarchical vocabulary type (parent → TaxonomyTerm), paired with
Capability [Knowledge] ('reality' normalized to the 'spec'). NB a naming collision to resolve:
Capability [Knowledge] is DAV's architecture-capability sense (what an architecture provides),
distinct from a PROVIDER capability (the substrate operation verb realize_resources |
serve_data | …). The provider-capability taxonomy reuses the TaxonomyTerm TYPE as shared
machinery but occupies its own disjoint term-space (a 'provider-capability' root, separate
from the 'architecture-capability' subtree that holds Capability [Knowledge]) — resolved
2026-07-11.

## Decision

(a) Affirm the single unified provider INTERFACE + closed capability vocabulary
(realize_resources | serve_data | authenticate | federate | execute_workflows; extensible) as
the ONLY contract-shape axis, and finish retiring 'provider type' as a contract concept —
storage-providers.md and the other per-type docs become capability/category references exactly
as information-providers.md already frames itself ('an Information Provider is a provider that
declares serve_data'). (b) Introduce CATEGORY as a first-class, NON-EXCLUSIVE grouping =
capability × resource-type domain, DERIVED from a provider's declared capabilities and the
domains they operate over; the legacy type labels become named categories (e.g. storage-
provisioning = realize_resources / Storage.*; information = serve_data; authentication =
authenticate). (c) Make category and capability first-class Governance-Matrix match sources on
the subject/target axes, REPLACING the stale target.type, so policy binds at category
(storage-provisioning), capability (serve_data), or data (data_classification / data_role)
granularity — a provider in multiple categories is evaluated per category. (d) Reframe the
'Provider Type Registry' as the governed registry of the capabilities + categories a
deployment accepts (three-tier Core / Verified / Org preserved); provider_type_id becomes a
reference to a registered capability/category profile, not a mutually-exclusive type. (e)
Reserve 'role' for the data axis (data_role, ADR-PROV-001); provider groupings are
'categories'. 'resource-domain' means the Category segment of a resource type's $id (Storage,
Compute, Network…; naming-conventions §1). (f) Clarify DCM ADR-023's resource-vs-process
'modes' as capability groupings (resource = realize_resources; process = execute_workflows),
not a reintroduced type. (g) A capability is EXPLICITLY (verb × domain-scope): every
capability declaration MUST name the resource-type domain(s) it operates over, uniformly —
reconcile today's split shapes (realize_resources.resource_types, serve_data.data_domains)
into one explicit domain-scope on the capability. Category derivation then reads directly off
the declared (verb × domain). (h) Provider capabilities are organized by a GOVERNED CAPABILITY
TAXONOMY built on the existing TaxonomyTerm machinery (hierarchical parent → TaxonomyTerm;
three-tier Core / Verified / Org governance); categories are terms in that taxonomy (a
category = a (verb × domain) node providers are classified under and policy targets).
Disambiguate the substrate 'provider capability' from the Knowledge-family 'Capability
[Knowledge]' (DAV architecture-capability sense) explicitly in naming-conventions. RESOLVED
(2026-07-11): reuse the TaxonomyTerm TYPE as shared vocabulary machinery, but provider
capabilities occupy their OWN term-space — a 'provider-capability' taxonomy root, a disjoint
subtree from the 'architecture-capability' (Capability [Knowledge]) subtree. One vocabulary
type, two disjoint subtrees; policy targets a provider-capability term (= a category).

## Data · Policy · Provider

- **Data** — Capability is the declared unit ON a provider, EXPLICITLY (verb × domain-scope) —
the verb from the substrate vocabulary and the resource-type domain(s) it operates over,
declared uniformly (reconciling today's realize_resources.resource_types /
serve_data.data_domains split). The capability vocabulary is a GOVERNED TAXONOMY on the
existing TaxonomyTerm machinery (Knowledge family; hierarchical parent → TaxonomyTerm;
Core/Verified/Org tiers), NOT a flat closed list — new verbs/domains register with governance.
Category is a DERIVED grouping = a (verb × domain) term in that taxonomy, a queryable view
over a provider's declared capabilities, NOT a second stored truth; legacy type names become
category terms; resource-domain = the Category segment of a resource-type $id (Storage,
Compute, Network…). Naming-conventions must disambiguate substrate 'provider capability' from
the Knowledge-family 'Capability [Knowledge]'.
- **Policy** — The Governance Matrix gains CATEGORY and CAPABILITY as match sources on the
subject/target axes, parallel to the existing data_classification and data_role axes,
replacing the stale target.type. Policy can bind differentiated rules at category (e.g.
encryption-at-rest ON storage-provisioning only), capability (any provider exercising
serve_data), or the data itself (classification / role). A provider that occupies several
categories is evaluated per category — the grouping is non-exclusive, so rules compose rather
than pick one type.
- **Provider** — The provider INTERFACE is unchanged and UNIFORM across categories — this is
the standardize-the-mechanics / simplify-integration goal. A provider declares its
capabilities (and the domains they cover) ONCE; category membership follows and is non-
exclusive; there is no double registration for a multi-capability provider (the InfoBlox
case). 'Provider type' survives only as a governance profile (a named, approved bundle of
capabilities/categories), never as a contract shape.

## Alternatives considered

- **Keep fixed provider types (status-quo drift)** — mutually-exclusive types force double
registration (the InfoBlox problem the unified model already rejected); cannot express a
provider that sits in two groups; policy stuck matching a single type *Rejected:* reintroduces
the exact defect the unified capability model was adopted to remove
- **Capabilities only, no category layer** — policy can bind to the atom or the whole provider
but has no grouping to attach differentiated policy to; 'serves multiple roles' has no first-
class expression; every policy must enumerate capabilities *Rejected:* the platform needs a
targetable grouping for differentiated policy and multi-role providers
- **Category = capability verb alone (domain-agnostic)** — cannot differentiate storage-
provisioning from compute-provisioning (both realize_resources) without a separate domain axis
on every rule; less expressive for the stated policy-targeting goal *Rejected:* Maintainer's
storage example requires policy to differ by domain, which the verb alone cannot carry
- **Category = capability × resource-domain, non-exclusive, derived (chosen)** — a larger
category set; category derivation must be specified (capability + the resource-domain it
targets)

## Consequences

['contracts/capability-discovery.md (capability = explicit verb × domain-scope, uniform
declaration; define Category = a (verb × domain) taxonomy term; category derivation; retire
the residual type framing)', 'registry/resource-types/ + registry (a governed capability
TAXONOMY on TaxonomyTerm — the provider-capability vocabulary as hierarchical terms with
Core/Verified/Org tiers; categories are terms in it)', "registry/naming-conventions.md
(disambiguate substrate 'provider capability' from Knowledge-family 'Capability [Knowledge]';
resolve the reuse-vs-adopt sub-decision)", "contracts/provider-contract.md (capability +
category declaration; reframe 'Provider Type Registry' → capability/category profile registry;
align the *_provider_capabilities block names to the capability verbs)", "contracts/storage-
providers.md (reframe as a capability/category reference, matching information-providers.md;
undo the 'fourth formal type / eleven types' framing and the MED-2 provider-type
enumeration)", 'dcm: architecture/convergence-engine/policy-evaluation.md + Governance Matrix
(add category + capability match sources; retire target.type)', "dcm:
architecture/adr/023-provider-naturalization-boundary.md (clarify resource/process 'modes' =
capability groupings, not types)"]
