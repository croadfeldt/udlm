# UDLM prior art & positioning — why this model, and why not just Terraform

**Status:** design note. A companion ADR promotes the decision half (§5/§8/§9). **Scope:** a recurring
question — is there a state-of-the-art comparison, are we reinventing the wheel, and why not start from
or extend Terraform? This consolidates the prior-art analysis already scattered across the ADRs and
design notes into one place.

**What this settles:** what the model adopts and from where, the genuine delta over the field, and —
per the adopt-outward tenet (T5) — the **adopt / map / build** verdict for each neighbor and the
conditions under which "build" flips to "adopt." It does not claim novelty it can't defend.

---

## 1. Short answer

- **We are not greenfield-in-ignorance.** The registry design notes §8 already survey and borrow from
  fifteen systems — TOSCA, Crossplane, Terraform, CloudFormation/Cloud Control, ARM/Bicep, Google
  Config Connector, OAM/KubeVela, Open Service Broker, Backstage, SCIM, Open Cluster Management, plus
  NIST OSCAL, CloudEvents, JSON Schema 2020-12. Each was taken *from*, not reinvented.
- **The comparison is mis-framed as UDLM-vs-Terraform.** UDLM is a **data model / spec**; Terraform is
  a **provisioning engine**. They are different layers. Terraform (and Crossplane) are strong
  candidates to *realize* UDLM intent under DCM — backends, not competitors.
- **The genuine delta over the union of prior art is small and specific:** (1) intent as a
  provider-independent contract with a four-state lifecycle that survives destruction (portability /
  rehydration-from-intent); (2) sovereignty + policy-firewall + attestation as first-class *data*
  properties, not a bolt-on gate; (3) a shared, CI-gated, vendor-neutral *type catalog* rather than
  build-your-own-abstraction; (4) a strict Data⇄Policy split — the model carries only nouns.
- **The strongest "why not just X" is TOSCA (the closest standard) and Crossplane (the closest
  engine).** The doc maps to both explicitly and records the falsifiable exit: if TOSCA node-types +
  capabilities can carry the intent lifecycle + sovereignty with acceptable ergonomics, the honest
  outcome is *extend TOSCA*, and the #54 interop track keeps that door open by design.

## 2. We are not greenfield — the receipts

Prior art is already load-bearing in the model, just never collected in one place:

| Area | What UDLM already adopts / aligns to | Where |
|---|---|---|
| Edge/relationship vocabulary | OASIS **TOSCA** root relationship types (`depends_on`/`contained_by`/`binds_to`/`references`), RFC 8288 link relations, Neo4j relationship-type | ADR-026, ADR-014, dependency-modeling.md, graph-integrity.md |
| Class extension (Base/Type/Provider) | **TOSCA** `derived_from`, **OData** `BaseType`, **XSD** extension/restriction, **RDF/RDFS** `subClassOf`, DMTF **CIM** | ADR-038 |
| Assembly / template tier | **TOSCA Service Template**, **OAM** Application (chosen over the vendor term "Blueprint") | ADR-033, ADR-034 |
| Desired/observed seam | **K8s** spec/status, **Crossplane** XRD/Composition, **Terraform** `Computed`, **OAM** `output` — generalized to four states + strong typing | registry-design-notes §6/§8, ADR-016 |
| Networking model | IETF **RFC 8343/8344**, **NMstate**, **NetBox**, **Redfish** (noted as converging → committed) | ADR-023 |
| Versioning | **NIST OSCAL** two-axis, **CloudEvents** major.minor, **SCIM** additive-only, **Redfish** deprecation annotation | registry-design-notes §6 |
| Adopt-by-reference mechanism | core-tenet **T5** ("adopt outward"), `adopts[]` / `adopted_standard_support`, the standards-adoption register (per-standard governing **Body**) | ADR-042, adopted-standards.md |
| Cost | **FinOps FOCUS** (by reference) | cost-metering-linkage |

The point: the design's default is *adopt the standard's word and shape*; it invents a term only where
it argued one doesn't exist (ADR-033 rejects the vendor "Blueprint" **for** the TOSCA word). What was
missing was this page — the consolidated answer — not the homework.

## 3. The category frame — model vs engine vs realizer

Three layers, and the neighbors sit in different ones. Comparing across layers is the source of the
"reinventing the wheel" impression.

| Layer | What it is | Neighbors | UDLM/DCM piece |
|---|---|---|---|
| **Model** | vendor-neutral *data contract* — resource types, relationships, capabilities, lifecycle, policy fields | **TOSCA**, OAM, CIM, OSCAL, CMDB/CSDM schemas | **UDLM** |
| **Engine** | reconciler that turns desired state into realized state, continuously | **Crossplane**, K8s controllers, Config Connector, OCM | **DCM** |
| **Realizer** | the thing that actually calls provider APIs / mutates hosts | **Terraform/OpenTofu**, Pulumi, CloudFormation, **Ansible**, KubeVirt | a **DCM Provider** |

UDLM's peer set is the **Model** row (TOSCA is the match). Terraform is two layers down — which is why
"start from Terraform" answers a different question than "what is the model."

## 4. The neighbors — one table

| System | Category | What UDLM takes / shares | What UDLM adds over it | Verdict |
|---|---|---|---|---|
| **Terraform / OpenTofu** | Realizer (IaC) | the `Computed`=realized idea; ordered state upgraders | intent is provider-*independent* (TF's is `aws_instance`, not "a VM"); intent survives destruction; policy/sovereignty first-class | **realize through it** (Provider) |
| **Pulumi / CloudFormation / ARM/Bicep** | Realizer | property classes (`readOnly`/`createOnly`), dated apiVersion | same as TF — provider-coupled, no neutral intent | **realize through / borrow markers** |
| **Crossplane** | Engine (closest) | spec/status seam; Composition; immutable monotonic revisions | substrate-neutral (not K8s-bound); a *shared* catalog vs author-your-own Composition; four states; sovereignty/attestation | **map to; candidate DCM backend** |
| **Kubernetes CRD + operators** | Engine/Model | declarative desired-state + reconcile; enum/extensibility discipline; GC/finalizer semantics | cross-domain neutral semantics; not cluster-scoped; intent lifecycle | **borrow patterns; realize through** |
| **OAM / KubeVela** | Model (app) | Application≈Template; `output` = typed realized | whole-estate scope (not just apps); sovereignty; four states | **map to (ADR-033)** |
| **TOSCA v1.3 (OASIS)** | Model (closest) | node types, capability/requirement matching, `derived_from`, Service Template, relationship types | intent lifecycle + rehydration; sovereignty/attestation; data-first not orchestration-first; lighter ergonomics; live tooling | **map to; interop #54; candidate to extend** |
| **Config Connector / Cloud Control** | Realizer/Model | typed GVK + `target_field` refs; uniform CRUD-L | neutrality; intent portability | **borrow ref shape** |
| **Open Service Broker + K8s Service Catalog** | Engine | async 202→poll | a cautionary tale (bolt-on catalog was retired) — informs "don't bolt a catalog on a runtime" | **avoid the anti-pattern** |
| **Backstage catalog** | Model (inventory) | relations *derived from* declared validated fields (= our derive-don't-store) | intent + policy, not just inventory | **align (graph integrity)** |
| **ServiceNow CSDM / CMDB** | Model (realized inventory) | configuration-item + relationship graph of the *observed* estate | intent track + policy + portability, not recorded-inventory-only | **map to (brownfield/estate)** |
| **SCIM (RFC 7643/44)** | Model | runtime schema discovery; URI-namespaced extensions; additive-only | domain scope; lifecycle | **borrow extension rule** |
| **NIST OSCAL / CloudEvents / JSON Schema** | Format | two-axis versioning; envelope; the normative schema language itself | — | **adopted outright** |

## 5. The genuine delta — the kernel that is actually new

Strip the adopted parts away and what remains — the thing no single neighbor, and arguably not their
union, gives you:

1. **Intent as a portable, provider-independent contract with a four-state lifecycle**
   (Intent → Requested → Realized, UUID-stable across destruction). TF/CFN/ARM couple desired
   config to one provider; K8s/Crossplane have a two-state spec/status bound to a cluster. UDLM's
   intent is *not* a provider's config, so it can be re-realized elsewhere or **rehydrated from intent
   alone** after total loss (uc-10). This is the portability thesis, and it is the load-bearing claim.
2. **Sovereignty, policy-as-information-firewall, and attestation as first-class *data* properties**
   (ADR-041 firewall, sovereignty zones/closure bundles, attestation subjects) — not a Sentinel/OPA
   gate stapled next to the artifact, but fields the model carries and the audit chain covers.
3. **A shared, CI-gated, vendor-neutral *type catalog*** — TOSCA has the shape but adoption/tooling is
   thin and orchestration-first; Crossplane makes each org *author its own* abstraction per provider.
   UDLM ships one standardized registry with meta-schema gates, so "a VM" means the same thing across
   consumers.
4. **A strict Data⇄Policy split** — the model carries only nouns (records, edges, markers, pins); every
   verb (transform, evaluate, enforce, resolve) is DCM/Policy. Most tools embed logic in the artifact
   (HCL functions, Composition patches, CEL); UDLM deliberately does not, which is what makes the data
   tamper-evidently auditable and portable. (decision trail retired to git history 2026-08-04.)

If a reviewer accepts (1)+(2) as real and valuable, the model earns its existence; (3)+(4) are *how*,
not *why*. If they don't, the honest path is §9.

## 6. "Why not just start from Terraform?"

Because Terraform answers "make these specific resources exist on this specific provider," and UDLM's
job starts one layer up: "here is provider-independent intent, choose the provider by policy, and let
me rebuild it anywhere." Concretely, in Terraform:

- Intent **is** the provider's schema. `aws_instance` and `azurerm_linux_virtual_machine` are different
  resources; there is no "a VM" you re-target by policy. Portability means rewriting HCL.
- State is realized-coupled-to-provider; there is no provider-neutral intent that survives the provider
  going away — so no rehydrate-from-intent.
- Policy (Sentinel/OPA) is a gate beside the pipeline, not a property of the data; sovereignty and
  attestation aren't in the model at all.

**But** Terraform/OpenTofu is an excellent *realizer*: DCM resolves a provider and hands it a target;
Terraform (or CDKTF) makes it exist. That's additive to the customers who already run it — their
Terraform keeps working *under* the model rather than being replaced. Same for Ansible (our own estate)
and Crossplane.

## 7. The strongest challengers — TOSCA and Crossplane

- **TOSCA** is the closest *standard* and deserves the most honest treatment. UDLM already adopts its
  relationship types, `derived_from`, and Service-Template concept (ADR-026/033/038). The reasons we
  extended rather than authored *in* TOSCA: it is orchestration-template-first (not data/intent-first),
  its lifecycle model doesn't carry the four-state intent/rehydration semantics or sovereignty, and its
  tooling/adoption is thinner than the IaC/K8s world our consumers live in. **This is a defensible
  "extend, don't reinvent" only if we keep the interop promise** (#54: ingest/emit TOSCA). If we don't,
  the criticism lands.
- **Crossplane** is the closest *engine*, and the overlap is with **DCM**, not UDLM. Crossplane's
  spec/status + Composition + revisions is close to DCM's convergence engine. The honest framing: UDLM
  is the standardized *model* Crossplane leaves to each org to build as Compositions; and DCM **could be
  implemented on Crossplane** or expose Crossplane as a Provider. That's a strength to state plainly,
  not a threat to hide.

## 8. Adopt / map / build ledger (per T5)

- **Adopt outright:** JSON Schema 2020-12, OSCAL versioning, CloudEvents envelope, FinOps FOCUS, IETF
  8343/8344 + NMstate, RFC 8288, SCIM extension discipline. *(done / in the model)*
- **Map & interop (roadmap #54):** TOSCA, OAM, ArchiMate, C4/LikeC4, CSDM/CMDB — ingest/emit/derive.
- **Realize through (Providers):** Terraform/OpenTofu, Crossplane, Ansible, KubeVirt, cloud APIs.
- **Build (the delta only):** the four-state intent lifecycle + rehydration, the sovereignty/
  policy-firewall/attestation data properties, the neutral type catalog + gates, the Data⇄Policy split.

The build column is deliberately thin. Anything not in it, we don't own.

## 9. Falsifiable exits — what would flip "build" to "adopt"

Stated so this is decided on evidence, not conviction:

- **If** a TOSCA profile (node-type + capability extensions) can carry the four-state intent lifecycle,
  UUID-stable rehydration, and sovereignty/attestation with acceptable authoring ergonomics → **the
  outcome is "publish a TOSCA profile," not a parallel model.** A spike against TOSCA v2.0 would settle
  it. *(Recommend we actually run this spike before 1.0 freeze.)*
- **If** Crossplane Compositions + a shared XRD library can express the neutral catalog + policy fields
  → **DCM is built on Crossplane** and UDLM narrows to the XRD schema layer.
- **If** neither the portability/rehydration claim nor the sovereignty-as-data claim survives a
  customer test (they'd accept per-provider intent + a policy gate) → **the delta collapses** and we
  should adopt IaC+OPA and stop.

None of these are rhetorical. The interop track (#54) is the hedge that keeps all three reachable.

## 10. Recommendation

1. Land this as `docs/design/prior-art-and-positioning.md`; promote §5/§8/§9 to an **ADR: "Relationship
   to prior art and the build/adopt line"** so the decision is citable and testable.
2. **Run the TOSCA-profile spike** (§9, exit 1) before the 1.0 freeze — it either strengthens the
   position with evidence or changes it. Either is a win; conviction is not.
3. Where the question recurs, answer with this page, not a paragraph — the position is meant to be
   attacked at §5 and §9, since that's where it is actually falsifiable.
