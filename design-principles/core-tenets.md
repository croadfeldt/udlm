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
transform** it. A spec carries values and *declarative* constraints — never executable behavior. Nor does
the substrate **translate intent into a provider's native spec** — that is the provider's naturalization
boundary, kept out of the substrate for peer portability *and* because only the provider can own the
translation's ramifications (`foundations/context-and-purpose.md` §7.1; DCM ADR-023).

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
`adopted-standards.md`. **This is an active review gate, not advice:** redefining a concept a credible
standard already solves — API versioning, auth/identity, DR objectives (RTO/RPO), health probes — is a
**review finding**; the default is "adopt by reference or justify why not" (`SPEC-DESIGN-REQUIREMENTS`
Design principles).

## T6 — Pre-validated outcomes, not testing during incidents
A declared resilience outcome (survive DR / move / rehydrate within an RTO/RPO) is only real if it is
**continuously validated**, not asserted. So **process validation is a lifecycle, not an event**: the
operational processes that satisfy an outcome (migration, failover, rehydration) are **rehearsed on a
cadence** — `simulated` (synthetic, schema-conformant, non-sensitive data, sovereignty-safe) or
`rehearsal` (real data to a reversible target) — each run producing **validation evidence** that backs
the claim, with **freshness** (a claim un-rehearsed within its cadence goes *stale*) and a **finding** on
failure. The consequence: **a real incident executes an already-validated path — it *validates the
outcome*, it does not *test an unknown*.** The cadence is driven by the workload's declared *criticality*
(data, consumer-set); whether to *gate* on stale validation (e.g. refuse to place a critical workload on
an unproven path) is **Policy** (DCM). The requirements, criticality, and evidence are **data**; the
rehearsal *mechanism* is the **provider**; the gating is **Policy**. (UDLM ADR-003.) This is the third
validation layer — **valid spec** (CONFORMANCE) + **valid data** (valid-by-construction + provenance) +
**valid process** (this) — over the same evidence/freshness machinery, never a parallel one.

## T7 — Reach for an existing mechanism before coining a new one
Before introducing a new primitive — a "module", a new field family, a new envelope, a parallel type —
first try to **compose it from mechanisms the model already has**: classification tags, profiles
(ADR-007), provider capability declaration (ADR-004), conformance tiers, must-ignore-unknown, object
references, and typed edges. Most "we need a new X" is an existing mechanism under a new name, and a
coined primitive is permanent surface — every peer must implement it and every reader must learn it.
**This is an active review gate, not advice:** a PR that introduces a net-new mechanism must show, in its
*Why*, that no existing mechanism (or composition of them) covers the need — otherwise the finding is
"reduce to existing." (This is exactly how ADR-029 dropped a proposed "inventory module" in favor of a
`classification` tag + profile inclusion + capability declaration + an optional conformance tier.) T5 is
this tenet aimed **outward** — don't re-express an external standard; T7 aims it **inward** — don't
multiply internal primitives. Occam's razor as a contract obligation.

## T8 — Adopt tools by reference: orchestrate, don't reimplement
Where a mature tool already owns a **mechanism** — building, scanning, signing, deploying, orchestrating
CI/CD — the realization (DCM) **wraps it as a Provider** and **never reimplements it**. This is the
tool-level twin of T5 and T7: T5 keeps the data model from re-expressing an external *standard*'s schema;
T7 keeps it from coining a redundant *primitive*; T8 keeps the *realization* from rebuilding a *mechanism*
a best-of-breed tool already provides. The **naturalization boundary** (DCM ADR-023) is the wrap point — a
Provider translates generic intent into the tool's native form and reports realized state back, so the tool
stays swappable and the substrate stays generic. **This is an active review gate, not advice:** a proposal
for the control plane to directly build / scan / sign / deploy must show that no existing tool can be wrapped
as a Provider — otherwise the finding is "wrap it, don't build it." The control plane's value is the layer
no single tool owns: the **cross-tool intent** and the **estate / realized graph**. Litmus — *does a mature
tool own this mechanism?* → Provider-wrap it; *does anyone own the cross-tool intent + estate graph?* → no →
that's ours.

---

**Consequence — what a UDLM spec contains and doesn't.**
- **Contains:** identity, versioning, the four-state shape, typed `spec` fields with *declarative*
  constraints (JSON Schema `if/then` · `dependentSchemas` · `enum` · bounds, plus declarative markers
  like `createOnly`), typed `outputs`, and typed relationship edges.
- **Does not contain:** embedded expression languages, transforms, computed values, or any executable
  behavior. Everything dynamic is a **Policy** evaluated by DCM and written to the audit log.

See `cross-cutting-requirements.md` for the pillar requirements these tenets serve, and
`registry/SPEC-DESIGN-REQUIREMENTS.md` for the per-entity authoring rubric.
