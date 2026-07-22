# UDLM ADR-038: Scoped resource-type Class hierarchy — Base / Type / Provider Class

**Number:** ADR-038 (foundational — the parent of the reference-discipline set ADR-035–037).
**Status:** Accepted on croadfeldt upstream (committed) — **downstream (dcm-project) adoption pending eng alignment** (it amends ADR-027, the `Category.Type` naming, and PRV-010; proposed to the team via the enhancements repo).
**Date:** 2026-07-21
**Type:** Architecture Decision Record (foundational — meta-model)
**Related:** ADR-027 (entity-family model — this extends it); ADR-024 (filling provider-required inputs — the policy-fill); ADR-004 (provider capability declaration); ADR-019 (Placement); ADR-012 (data-references + lineage); ADR-008 (wire-compatibility); ADR-010 (dependency-graph completion — the governed cross-entity surface §10 must not bypass); **T4** (cross-entity flow is edge, not address); **PRV-010** (provider extensions + Vendor.Type fork — *subsumed*); core-tenets **T1/T2/T3** (data is not logic), **T5** (adopt, don't re-express), **T7** (reduce to existing); the reference-discipline set (PVD-001 / ADR-035–037 — *recast as applications*)

**Settles:** resource types are layered **Base / Type / Provider Classes** of scoped `SharedDataElement`s — one meta-model that unifies base fields, shared vocabularies, and provider extensions, and makes portability legible from the name.

## Context
The reference-discipline work (PVD-001: reference over restate; requirements over vendor-native) kept running
into the same seam. Pushing on it revealed that **"base field," "shared vocabulary," and "provider extension"
are one structure — a data element + its value list — at different scopes.** Separately, types with overlapping
concepts (`Compute.VirtualMachine` and `Compute.BareMetalHost` both have cpu / memory / OS / storage / network)
define them **independently**, which is the source of the cross-type inconsistency surfaced in review (the
units/sizing thread across VM, container, cluster, and database). Rather than patch each field on each type,
this settles the meta-model: **resource types are layered Classes composed of scoped shared elements.**

## Decision

1. **Three Class layers, keyed to the name hierarchy.**
   - **Base Class** — *Category* scope (`Compute`): `SharedDataElement`s common to the category.
   - **Type Class** — *Type* scope (`Compute.VM`): extends the Base Class with type-specific elements.
   - **Provider Class** — *Provider* scope (`Compute.VM.OCPVirt`): extends the Type Class with provider-specific
     elements. UDLM defines the *grammar* for this layer; the definition itself is **provider-authored** (see
     *Authorship & domain*) — `Compute.VM.OCPVirt` here is illustrative of the grammar, not a UDLM-shipped class.
   Each **extends** the one above under the **Liskov invariant — add or refine, never contradict** (a Provider
   Class *is-a* Type Class *is-a* Base Class). This **subsumes** `provider_extensions` *and* the Vendor.Type
   fork into one uniform mechanism: a provider-specific element is just a `SharedDataElement` at the Provider
   Class, in a first-class, versioned, validatable definition — never an opaque per-instance blob.

   **Direction (vocabulary used throughout).** The hierarchy runs **Base (top) → Type → Provider (bottom)**,
   following the standard inheritance convention (general at top, specialization descends). Movement **up** =
   *generalize* — toward Base, more portable (this is a **promote**); movement **down** = *specialize* — toward
   Provider, more finite. Positional shorthand: **higher** = more general (nearer Base); **lower** = more finite
   (nearer Provider). In one line: **up/higher = more portable, down/lower = more finite** — used consistently
   below (a "lower Class" is a more specific one; "promote up" moves an element toward Base).

2. **`SharedDataElement` is the unit at every layer** — `{scope, element, schema, values, state}`: a data
   element + its value vocabulary, curated `proposed → canonical`. The distinctions "base field vs shared
   vocabulary vs extension" collapse into **scope**. Value lists are reference-data (ADR-012); the element is a
   declarative field (T1).

3. **Two-axis portability, read off scope.** An element's Class *is* its portability: Base = portable across
   the category's types (and, when adopted, providers); lower = more specific = **narrower, but never zero** —
   even a Provider Class stays portable across the *set* of providers declaring it (§4). Portability drops to a
   single target only when a specific provider **instance** is named (the authority/instance axis, §10). Same
   three dials as the extension ramp — authorship, scope, portability — now spanning **both** the provider axis
   and the type axis with one construct.

4. **All Classes are instantiable; the instantiation level is the portability commitment.**
   - Instantiate the **Base Class** (`Compute`) → maximum portability; Placement (ADR-019) resolves Type +
     Provider; policy-fill (ADR-024) completes the blanks. *Portability at its highest level.*
   - Instantiate the **Type Class** (`Compute.VM`) → portable across VM providers; Placement picks the provider.
   - Instantiate the **Provider Class** (`Compute.VM.OCPVirt`) → narrowed to the providers that declare this
     class. Portability does **not** drop to zero here: **multiple providers can declare the same Provider Class**
     (two OCPVirt deployments are both `Compute.VM.OCPVirt`), so a request stays portable **across that provider
     set** — Placement chooses among them by request criteria, advertised capabilities, and policy. The
     commitment is to the *class*, not to a single provider; only naming a specific provider *instance* (the
     authority/instance axis, §10) removes the remaining freedom.
   Portable **intent** (a Base Class request) resolves to a concrete **realized** placement; the resolution
   path (chosen Type, Provider, provider instance, policy-filled values) is recorded as provenance + audit. This
   *is* the Intent → Requested → Realized four-state model expressed structurally — and portability narrows
   **progressively**, never to zero, until an instance is named.

   **Re-porting — commitment is reversible.** The class a resource sits at is the projection of its *current*
   requirements, not a permanent lock. Update the requirements — a consumer relaxes intent, or a policy loosens —
   and the eligible class **re-derives**, enabling a port back *up* a level or *across* siblings. *Example:* a VM
   requiring `encryption: sev-snp` lands at `Compute.VM.OCPVirt` (only SEV-SNP-capable OCPVirt qualifies); when
   the requirement is later updated to "encryption-at-rest, any provider-satisfiable," the pin dissolves and the
   workload ports **up to `Compute.VM`** — any VM provider again; drop its VM-specific needs and it can port
   **cross-Type** to `Compute.BareMetalHost`. At the intent level this is the widened placement set; at the
   realized level it is a **migration / rehydration** (ADR-003 — replay the *updated* intent + migrate data).
   **Governed, not a loophole:** relaxing a *constraint* requirement is loosening — policy-gated like `skip`
   (break-glass, attested for compliance), and the re-port is recorded. So provider commitment is never a
   dead-end: it is a function of requirements, and requirements are updatable.

   **Operational expectations — enablement, not execution.** A re-port across providers (a VMware VM →
   `Compute.VM.OCPVirt`) is a "cast" at the *intent* level; realization is a separate, bounded effort:
   - **Enablement over execution.** UDLM supplies the *data framework* that makes a re-port **expressible and
     analysable** — the requirements, the dependency set (networking / storage / compute), and the eligible
     target providers. It does **not** perform the migration. Execution is DCM + the provider + **third-party
     automation**: moving data requires a mover (e.g. **MTV** for VMware→OCPVirt); DCM does not migrate a disk.
   - **A re-port is a rebuild, not a lift-and-shift.** Moving to a different provider **rebuilds** the resource
     from its requirements + dependencies on the target's *native* services — equivalent to redeploying to a new
     cloud. The substrate carries the **intent to rebuild**, never a copy of the source's native form (T1/T2,
     naturalization boundary ADR-023): a VMware VM on NSX becomes an OCPVirt VM on OVN by *re-realizing the
     requirements*, not by translating NSX.
   - **Portability is bounded.** Source-specific features with no target equivalent **cannot** re-port; a
     partial/assisted re-port is the expected outcome. The model makes the *achievable* portion explicit and
     **surfaces the non-portable remainder**.
   - **The data is the lever.** Minimal Base/Type classes + scoped `SharedDataElement`s carry the data to
     (a) evaluate vendor-lock-in vs flexibility and (b) drive the **downstream automation** for the complex cases
     (the NSX→OVN class). Scoping an element higher extends portability wherever a target can honour it.
   - **`how` is the realization's concern.** The migration/rebuild mechanics, per-source/target limitations, and
     automation live in **DCM ADR-025** (engine), migration **ADR-003**, and naturalization **ADR-023**. This
     section defines what re-porting *means*; the realization docs carry the concrete process and its limits.

5. **Policy-fill completes the blanks (ADR-024).** Type/provider-specific elements left blank at instantiation
   are filled by policy for the resolved Class — precedence **consumer-set ≻ policy-fill ≻ provider-default**,
   `source_type: policy`, audited. The fill is Policy (computed, recorded), never embedded in the portable data
   (T1/T2), and each fill is a recorded decision, so the contract stays reproducible (T3). This is what makes
   higher-Class instantiation *realizable* rather than merely expressible.

6. **Gated upward contribution.** A Class may define a `SharedDataElement` at its **own scope or any higher
   scope**, subject to **(a) no conflict** (the Liskov/no-shadow invariant on an upward write) and **(b) policy
   allows it** (governance, tightening with blast radius — Provider→Type affects all VM providers; →Base affects
   all Compute). An upward contribution lands **`proposed` at the target scope** and canonicalizes by governance
   (or immediately, if the profile grants that contributor authority). This gives portability *by contribution*,
   not only by later promotion — and makes the promotion backlog **observable**.

7. **Promotion = moving an element up a Class.** Triggered by PRV-010's ≥2-adopter recurrence *or* explicit
   upward contribution (6). The **base-type roadmap is the observable set** of upward-defined / recurring
   elements — evidence-driven standardization, not guesswork.

8. **The wire stays flat (ADR-008).** Classes are *authoring-time* composition; peers exchange the **resolved
   effective schema** (Base ⊕ Type ⊕ Provider, flattened, `additionalProperties: false`). Layering changes how
   we author and reuse, never the wire contract or wire-compatibility.

9. **Attestation deferred** — binds to a `SharedDataElement`/Class identity later (additive; the identity is
   established here). Until then reuse rests on shared `(scope, name, schema)` as a best-effort join, sufficient
   for the portability incentive; behavioral *proof* is picked up by attestation where trust must be proven
   (sovereignty, compliance).

10. **Unified addressing — one coordinate, native as a URL.** A single grammar names any data element, and it
    **is a native URL**: `https://<authority>/<entity-path>?<filters>#<field-path>`. **Dots and slashes are two
    serializations of the same hierarchy** — interconvertible 1:1 (segments are clean tokens; cf. Java
    `com.example.Foo`↔`com/example/Foo`, OData qualified-name↔URL-path, DNS): the **dotted** form is the compact
    logical name (`resource_type` `Compute.VirtualMachine`, the DNS authority `peer.dcm.east`,
    event-routing/wildcards `compute.vm.*`); the **slashed** form is the URL address (`/Compute/VM/OCPVirt`,
    path-routable, HTTP-native). Same hierarchy — pick the serialization by context. The *anchor* is an instance
    uuid (→ a value), a Class/type name (→ the element *definition*), or a layer uuid; the *field-path* addresses
    within the resolved typed schema. This is the **same coordinate as the Class hierarchy** — the Class name *is*
    the entity path — and it **consolidates** addressing the model already does piecemeal (T7): layer
    contributions (uuid + path + provenance, `layer.schema.json`), catalog-item `bound_field`, drift `field_path`,
    `createOnly` paths, and the field-reference kind.
    - **The coordinate maps 1:1 onto native URL components — the URL delimiters do the parsing.**
      `https://peer.dcm.east/Compute/VM/*?residency=state.mn#/power/capacity` —
      **authority → host** (`peer.dcm.east`), **entity → path** (`/Compute/VM/OCPVirt`), **attribute filters →
      query string** (`?residency=state.mn`, i.e. OData `$filter`), **field-path → fragment** (`#/power/capacity`,
      JSON Pointer RFC 6901). Because `://` `/` `?` `#` delimit the parts, there is **no ambiguity to resolve** —
      the host is the authority, the path is the entity, the query is the filter, the fragment is the field. The
      **compact dotted alias** uses `.` within a part and `#` for the field; a *lowercase dotted anchor* (a
      named-head like `facility.dc.dc-east`) still needs the explicit `#`, since dots alone can't split it from
      the field-path. One delimiter per part, never mixed within a part (authority always dotted-host; entity
      all-slash or all-dot, not `Compute/VM.OCPVirt`).
    - **Notation & filtering — conventions, enforced as design criteria.**
      **(a) One notation convention.** Two serializations of one hierarchy, each canonical in a role:
      **URL is canonical for anything that addresses or selects** — every coordinate, query, **selector
      (including `covers`)**, and federation reference is canonically a URL (`https://…/Compute/VM?…#…`).
      **Dotted is canonical for a bare identity name** — a type name used as a *field value*: `resource_type`,
      `extends`, a Class name (`Compute.VirtualMachine`). Dotted is *also* an **accepted compact alias** for
      addressing/selectors where readability favors it — a `covers` list or an inline reference
      (`Compute.VM.*[.residency = dc-east]`) — with the URL as its canonical equivalent. Rule of thumb: *names
      are dotted; anything that addresses or selects is a URL* (compact-dotted alias permitted for readability). **(b) One filter mechanism.** The
      coordinate **attribute predicate** (`?field=value` in URL form, `[.field op value]` compact) over
      name-structure **and any field value** is the *only* selector — a **label selector is a predicate on
      `.labels`**, a special case, never a second mechanism; operators track OData `$filter`
      (`eq`/`ne`/`in`/`exists`). Both are **design criteria**: the review sweep checks every example and spec for
      consistent notation and for any parallel filter/selector construct (which is a finding — reduce to the
      coordinate predicate).
    - **Resolvability.** The anchor pins the version — a uuid → an immutable version (ADR-012); a Class name →
      that Class's definition version — and the path resolves against the *typed* target schema, so a renamed
      field breaks loudly, never silently.
    - **Dual anchor (every reference carries two).** Not one anchor but **two**: an **immutable anchor**
      (`ref_uuid` — the exact original record, pinned forever: reproducible, auditable, deterministic, T3) **and**
      a **named-head anchor** (`ref_name`/handle — the *current binding of the name*, resolving to whatever that
      name points at *now*). The head follows the **name**, not the version lineage — a name is a mutable,
      repointable indirection, so it can move to a new version **or a different record entirely** (always within
      the same `reference_data_type`). Consumer/policy chooses which to resolve — the **pin** for reproducibility,
      the **named head** for currency, or both. This **resolves ADR-012's silent-rebind concern**: name
      resolution is safe *because* it is paired with the immutable pin — you are never silently rebound, and
      opting into the head is explicit. Drift = the pin vs what the named head resolves to now.
    - **Updating a named reference is governed, audited, and blast-radius-computable *in advance*.** Repointing a
      named head (the mutable binding now points elsewhere) is a **governed write** — **policy** decides who may
      repoint and with what approval — and an **audited event** (AUD-*, tamper-evident per AUD-002): old target →
      new target, actor, timestamp, justification. **UDLM records it, DCM enforces it — no silent repoint.** Its
      **blast radius is pre-calculable *before* committing**, from the **reverse-reference index + `impact_report()`**
      (ADR-012): the affected set is exactly the **named-head followers**, cascading transitively —
      **immutable-pin references are insulated**, so the dual anchor *bounds* the blast radius to whoever opted
      into currency. The pre-computed blast radius **informs the policy gate**: a repoint touching many, critical,
      or cross-sovereign resources escalates (dual approval / break-glass). So the dual anchor is not only a
      reproducibility tool — it is a **blast-radius containment** mechanism, and a repoint is never blind.
    - **Address ≠ dereference (load-bearing).** The coordinate is a **name** — free for provenance, audit, policy
      reference, impact analysis, layer contribution. **Dereferencing it across an entity or sovereignty boundary
      is governed** by the existing typed-edge / `outputs` / **T4** rules and the sovereignty gate — *not*
      licensed by the address itself. Address freely; cross-boundary *resolve* stays on the governed edge/outputs
      surface, so the dependency graph (ADR-010) stays complete and sovereignty stays visible. A universal
      address must never become an ungoverned pull-any-value channel.

    **Routing authority (federated addressing).** A coordinate is optionally rooted at an authority —
    **`[<authority>/]<anchor>.<field-path>`**; absent = local/default context. The **`/` is the one hard
    boundary** between authority and coordinate, which is what lets *both* be dotted hierarchies without
    ambiguity.
    - **The authority is itself dot-hierarchical and filterable.** First segment = **root-type** (`peer`,
      `tenant`, `jurisdiction`, …); remaining segments = its hierarchical id — `peer.dcm.eu-west`,
      `jurisdiction.eu.de`, `tenant.acme.div-x`. Lowercase, wildcard-routable/filterable (`peer.dcm.eu.*`),
      consistent with the event-route dotting (naming-conventions §154). Each root-type in the registry defines
      how its hierarchy is interpreted, resolved, and governed.
    - **Root vs attribute (keeps the root set from bloating).** A **routing root** changes *who resolves* — you
      route *through* it (a peer DCM, a tenant, a jurisdiction that fronts its own authority). This is
      `data_reference.resolving_authority` made explicit. An **attribute** is what you resolve *to*
      (`residency` / zone) — carried on the record, not a root. Zones/borders are attributes **unless** one fronts
      a distinct control plane (then it *is* a peer/authority root). The test: *does it change the resolver?*
      Yes → root; no → attribute.
    - **Extensible root registry.** Root-types are an open, curated registry (Data/UDLM); routing + resolution is
      Policy + peer (DCM). Demand-driven — start with the **`peer`** root (the federation case); add others when a
      use case makes them distinct authorities, not speculatively.
    - **Cross-boundary resolve is governed** — the §10 rule at federation scale. A rooted address you *name*
      freely; *resolving* it across a peer or sovereignty border fires the sovereignty hard-gate (ADR-024 §1) and
      is attributed via `resolving_authority`. A fully-qualified cross-border address never bypasses that gate.
    - **Native URL is the primary form** (OData/REST-shaped — the standard set §Prior-art aligns to), each part a
      URL component (above). The **authority is the host** — a *logical* authority name resolved by DCM's
      **governed resolver**, **not public DNS** (native-URL-shaped *and* governed; this refines the earlier
      "keep `udlm.dev` the host" lean). **Two URLs, two purposes:** **type-definition identity** lives at the
      naming authority (`$id` = `https://udlm.dev/registry/udlm/0.1/Compute.VirtualMachine/0.6.0`); an **instance
      address** lives at the owning DCM's authority (`https://peer.dcm.east/Compute/VM/…`). The URL is still a
      **name**, exactly like `$id` — HTTP-shaped does **not** imply a free GET; resolving one goes through the
      governed resolver (auth + sovereignty gate), which is what makes HTTP the natural *governed resolution
      transport* for the federation-resolution ADR. Percent-encode edge characters (minimal — tokens are clean).
    - **Full mechanics deferred** to the federation-resolution ADR (routing, cross-peer trust, caching, the
      sovereignty gate at the wire) — a substantial surface, demand-driven, starting with the `peer` root.

## Data · Policy · Provider (SPEC-DESIGN §29)
- **Data** — the Class definitions, their `SharedDataElement`s + value lists, curation states, provenance,
  lineage. All declarative.
- **Policy** — Placement resolves the Class path; policy-fill completes blanks; promotion/canonicalization and
  upward-contribution gating are governance.
- **Provider** — a Provider Class *is* the provider's declared realization surface; realization naturalizes to
  native and records the resolution.

## UDLM vs DCM — what lands where (the peer test, ADR-008)
Apply ADR-008 to every piece: *could an independent conformant peer of DCM do this differently and still be
valid?* **No → UDLM** (a substrate invariant, wire-compatible — a peer MUST honor it). **Yes → DCM** (a
realization choice — Policy/Provider). This determines the repo each piece lands in.

| Piece | **UDLM** — model / grammar / data (a peer MUST honor) | **DCM** — engine / decision (a peer MAY differ) |
|---|---|---|
| **Class hierarchy** | **canonical** Base/Type definitions; the Class **spec** for all layers (`extends`, Liskov invariant, flattening, `SharedDataElement` scoping) | org/provider-authored **class definitions** (any layer) — one register/validate/promote lifecycle, policy/profile-driven; optional example/default classes |
| **`SharedDataElement`** | the unit `{scope, element, schema, values, state}`, value vocabularies | promotion / canonicalization, ≥2-adopter promotion, upward-contribution gating |
| **Portability** | the `portable / partial / provider-specific` classification (declared) | computing the eligible set; grading an instance; re-derivation |
| **Addressing** | the coordinate grammar (dotted/URL, `$id`, dual-anchor shape, `covers`/`skip` declarations, notation convention) | resolution, the governed resolver, routing, the federation resolver, sovereignty gate at the wire |
| **References** | `data_reference`, the references-context **classified edge**, dual anchor | reference resolution, blast-radius computation (`impact_report` run), repoint enforcement |
| **Layers** | the layer **contract** — `covers`/`skip`/precedence/`narrow_only` grammar | the layer **definitions** (org-level) + assembly engine (gather-by-`covers`, precedence, override), group/request binding, skip authorization, optional example/default layers |
| **Instantiation** | the intent (Class + requirements) + the four-state shape | Placement (pick Type/Provider/instance, ADR-019), policy-fill (ADR-024), requirements↔capability matching |
| **Composite (`multi`)** | the `catalog-item` constituent / edge / binding declaration | expansion into a Composite Entity, orchestration |
| **Re-porting** | the requirements (updatable intent) | migration / rehydration, re-placement (ADR-003) |
| **Naturalization** | the generic/portable form (the contract) | the provider's native translation (naturalize / denaturalize) |
| **Governance** | audit records + provenance (the **data**) | policy gates (skip, repoint, promotion, break-glass) + enforcement |
| **Conformance** | the design criteria + meta-schema (what is *valid*) | CI runs the checks; DCM enforces at realization |

**One line:** UDLM owns the **model, grammar, classification, and data** — the portable, wire-compatible
substrate; DCM owns the **engine** — placement, policy-fill, assembly, resolution, promotion, matching,
migration, and governance. The coordinate *grammar* is UDLM; the `Compute.VM.OCPVirt` *definition* — and every
*decision* about it — is provider/DCM (next).

## Authorship & domain — UDLM defines the specs; DCM runs one contribution lifecycle over them
The three Class layers are **not** authored in the same place, and neither are data layers. Sharpening the peer
test (ADR-008) along the **authorship** axis:

- **UDLM owns the specs and ships the canonical library.** The normative **spec** for each contributable kind —
  a Class (Base/Type/Provider: `extends`, the Liskov invariant, effective-schema flattening, `SharedDataElement`
  scoping) and a data layer (`covers`/`skip`, precedence, override, `narrow_only`) — *and* a **canonical set of
  Base/Type classes** (`Compute`, `Compute.VM`, …) as the shared, portable baseline. UDLM defines the spec and
  **instructs DCM what to do with instances of it**; it does not itself author org/provider content.
- **Provider Classes are provider-authored.** A `Compute.VM.OCPVirt` definition is **by its nature a
  provider-created artifact** — the provider declares its realization surface as scoped `SharedDataElement`s
  under the Class spec. UDLM ships **no** concrete Provider Class; the `Compute.VM.OCPVirt` used throughout this
  ADR is **illustrative of the spec**, not a UDLM-owned definition.
- **Organizations may author their own Base, Type, and Provider classes — a DCM policy/profile feature.** When
  the canonical library lacks a type, an org authors its own class (any layer) **under its own authority**
  (`acme.example/Compute.VM` — a distinct identity that never shadows canonical `Compute.VM`; portability is
  authority-scoped — narrower, never zero). This is **not a UDLM meta-model act**: UDLM defines the spec the
  class conforms to and instructs DCM; **DCM implements class-authoring as a policy/profile-driven feature**,
  governed by org policy (same family as *Org standards*). Standardizing an *existing* class stays Policy/Profile
  (a constraint profile); authoring a *new* one your library lacks is this feature — told apart by **authority**,
  both Policy/DCM. **How to author one well:** `docs/design/scoped-class-hierarchy/custom-classes-best-practice.md`
  (the cheapest-tool ladder, custom Type vs Base, the discipline, anti-patterns, the lifecycle, the never-redefine guard).
- **Data-layer definitions are organization-level** — the layer *contract* is UDLM; *which* layers exist and what
  they hold (an org compliance overlay, a Data-Center info bundle) are org implementation details.
- **DCM runs one contribution lifecycle over all of them.** Provider/org classes, data layers, and
  `SharedDataElement`/vocabularies share **one** pipeline — **register → validate against the UDLM spec for that
  kind → bind/resolve → promote (`proposed → canonical`)** — the same process, differing only in the **data spec**
  validated against (Class spec, layer contract, element spec). This **subsumes vocab ingest (ADR-039) and
  Provider-Class registration into one engine**; who may contribute/promote is policy/profile + trust (ADR-022).
  **DCM MAY ship examples or defaults** (a starter class, a default compliance layer) — conveniences, never
  canon. (DCM's side: DCM ADR-025.)

In one line: **specs + canonical library = UDLM; anyone may author classes and layers under those specs,
authority-scoped and promotable, run through one DCM register/validate/promote lifecycle governed by
policy/profile.**

## Options considered
- **(A) Status quo** — independent per-type definitions + `provider_extensions` + Vendor.Type fork. *Rejected*:
  three mechanisms, structural cross-type drift, opaque provider blobs, no portability gradient.
- **(B) [chosen]** Layered Classes of `SharedDataElement`s, instantiable at every level, policy-fill completing
  blanks, gated upward contribution. One mechanism; portability legible from the name; subsumes three prior
  constructs.

## Consequences
- **Foundational and cross-cutting.** Amends **ADR-027** (adds the Class layering over the family model),
  extends the **`Category.Type` naming** with a Provider level + Class semantics, and **subsumes PRV-010**.
  Because a meta-model shift is felt directly by peers/downstream, it needs a **FlightPath / design-review
  alignment pass** before it supersedes shipped ground — flagged in Status.
- **Meta-schema.** Types become composable Classes; the **effective schema is resolved/flattened** for wire +
  conformance; versioning is multi-level (a Class's effective version incorporates its parent's).
- **Naming & dot-notation impact (for alignment review).** The three-segment Class name *and* the dotted
  addressing coordinate (§10) both extend the identity grammar, which today hard-codes **one-or-two segments in
  four places** — `$id`, `resource_type`, `relationship.target`, and the `layer.schema.json` type-ref, all
  `^[A-Z][A-Za-z0-9]+(\.[A-Z][A-Za-z0-9]+)?$`. A malformed name **fails validation loudly** — no silent
  corruption. The bounded work: extend those four patterns to allow up to two extra segments (`{0,2}`), amend
  **naming-charter §1** (single/two → add the Provider tier), add a **Provider-token rule** (a single PascalCase
  token, *not* a dotted DNS/namespace like `acme.io`, which would break segment parsing), and review two-level
  **event-routing** assumptions (more-specific `compute.vm.*` wildcards actually help). **Case discipline** — PascalCase
  type segments vs lowercase field paths — is what keeps the overloaded dot unambiguous across all five uses
  (type names, field paths, `reference_data_type`, file names, event routes).
- **Demand-driven rollout.** Prove on **Compute** — where the demand already exists (the cross-type cpu/memory
  inconsistency surfaced in review is exactly what a shared Base Class fixes) — then expand as commonality
  demonstrates itself. Not a big-bang re-type of the registry.
- **Recast, not discard.** The reference-discipline ADRs (035–037) and the vocab-ingest ADRs become
  **applications** of this paradigm (PVD-001 = "reference the right Class-scoped element, don't restate";
  storage requirements = Base/Type-Class `SharedDataElement`s; vocab ingest = how value lists get populated).
- **The recent VM reshape lands cleanly.** The `Compute.VirtualMachine` reference-discipline reshape is a valid
  `Compute.VM` (Type Class) under this model — it lands in today's registry and migrates cleanly when the
  paradigm rolls out.
- **Two sweep criteria + data checks this adds (generalized).** Both came from concrete catches; both are stated
  as *classes*, so the review sweep and CI catch orthogonal cases, not just the originals.
  1. **One canonical mechanism & notation** (from a duplicate-filter catch). Every construct that *filters,
     selects, addresses, or references* MUST reduce to the model's single canonical mechanism — the coordinate
     attribute predicate (filter/select), `data_reference` (reference), the URL coordinate (address) — and to the
     right notation role (identity → dotted; address/selector → URL). A **parallel construct** (a second
     selector/filter/query DSL, a duplicate identifier scheme, a parallel edge/binding type) or a
     **role-mismatched notation** (a bare name as a URL; a selector written as dotted-identity without being one)
     is a **finding — reduce to the one mechanism/form.** (T7, aimed at *mechanisms and notation*.)
  2. **Reference-discipline holds in data, not just definitions** (from a `guest_os`-as-string catch). A field the
     model declares as a **reference / codelist / requirement** (PVD-001) MUST appear *as such **everywhere** it
     occurs* — type spec, instance, layer-contributed `fields`, catalog binding, and **every example** — never a
     bare literal. A reference-typed field carrying a string, a codelist field carrying an off-list value, a
     requirements field carrying a vendor-native literal, or an `outputs` key string-spliced instead of typed-
     bound is a **finding.** (Extends `check_portable_values.py` from type specs to **instances + layer data +
     examples**.) Both are review-sweep judgment checks *and* wired data checks.

## Org standards & tenancy — Policy over the classes, not a fork of them
An organization's standards are **Policy over the shared classes**, not a fork of the shared ones (authoring your
*own* classes under your own authority is a separate, allowed capability — see the end of this section). The peer test (ADR-008)
routes it: *could another org do this differently and still be valid?* — yes, every org differs → **Policy
(DCM)**, not substrate. This is what keeps the classes valuable: Acme's and Globex's VMs are both `Compute.VM`
— *interoperable* — each governed by its own policy. Forking a class per org would destroy the portability the
paradigm exists to provide.

| Org wants | Mechanism | Not |
|---|---|---|
| **Template** (reusable pre-filled intent — "our standard VM") | ADR-033 **Template** (Requested tier, instance-level over `Compute.VM`) | a class |
| **Defaults** ("VMs default to RHEL9, gold storage, cost-center tag") | **policy-fill** (ADR-024) via the org **Profile** (ADR-007) | a class |
| **Standards / constraints** ("MUST be encrypted, approved OS images only, size ≤ X") | **constraint profile** (E1) — *narrows* class fields (required / tighter enum / bounds), never widens or redefines | a class |
| **Genuinely-new org data** (`cost_center`, `compliance_id`) | an org-scoped `SharedDataElement` — additive, portability-degrading, must-ignore-unknown; usually **cross-category** (a tenancy overlay), not Compute-specific | a Compute class |

**Never *shadow* a canonical class** (Liskov / no-shadow): inserting `Compute.ORG.VM` *into the canonical
hierarchy* to change what `Compute.VM` means fragments the shared type (per-org redefinition = no interop) and
couples governance into the wire contract (T1/T2) — that is what the Policy mechanisms above are for. **Authoring
your *own* classes under your *own* authority is different, and allowed** — `acme.example/Compute.VM` is a
distinct identity in the org's namespace, canon untouched, portability authority-scoped, promotable to canon when
proven; it runs through **DCM's policy/profile class-authoring feature** and the one contribution lifecycle (see
*Authorship & domain*). The line is **authority, not permission**: standardize a *shared* class → Policy/Profile;
author a type the library lacks → your own class under your authority. **Org = a governance/tenancy overlay on the
shared classes and, where the library falls short, an authority-scoped author of its own.** Best practice for that
authoring: `docs/design/scoped-class-hierarchy/custom-classes-best-practice.md`.

## Naming depth — unbounded, but governed
`Category.Type.Provider` is not a hard three-level cap — the notation is **unbounded** (the grammar recurses to
`+`, and `extends`, effective-schema flattening, and wildcard filtering all recurse with it). Depth is governed
by the **same earns-its-keep test as every level**: a lower Class is justified *only* by genuine
**shared-then-specialized definition structure** (≥2 sub-variants sharing elements, each adding). Before reaching
for depth, check the three cheaper axes (T7) — most apparent "sub-providers" are one of these, not a new Class:

- **Version axis — `Compute.VM.OCPVirt` at v2.0 vs v1.0**, not `Compute.VM.OCPVirt.new` / `.old`. A newer OCPVirt
  with added features is the *version* of the Provider Class, not a fourth Class segment; `.new`/`.old`
  duplicates versioning you already have.
- **Capability advertisement — two OCPVirt deployments, same Class, different features.** One cluster's OCPVirt
  offers GPU passthrough + SR-IOV, another doesn't. Both are `Compute.VM.OCPVirt`; each **advertises its own
  capabilities** (ADR-004). The difference is capability data on the provider, not a Class fork.
- **Authority / instance axis — *which* OCPVirt.** Two separate OCPVirt installations are two provider
  *instances*, addressed on the **authority axis** (`peer.dcm.east/…` vs `peer.dcm.west/…`, §10) — **orthogonal**
  to Class depth.

The distinction to hold: **Class depth is about the type *definition*; version / capability / instance are about
*which realized thing* and *what it offers*.**

> **Rule:** don't spend Class depth on what version, capability, or instance-identity already expresses. A lower
> Class level is for genuine shared-then-specialized *definition* structure only — e.g. an OCPVirt family that
> truly forks into a shared `Compute.VM.OCPVirt` plus specialized sub-definitions that each add distinct elements.
> `OCPVirt.new`/`.old` = version; "two slightly different OCPVirts" = capability advertisement on two instances.
> Neither is a new Class.

Depth stays *available* for the real case, but each level adds a versioning tier and cognitive/tooling cost, and
the case-boundary parse must hold (PascalCase Class segments until the lowercase field-path). Allow it, govern it
by the test, default to the cheaper axis.

## Composition vs inheritance — the *multi* axis
The Class hierarchy is **inheritance (*is-a*)** — vertical specialization of *one* resource's definition
(`Compute.VM extends Compute`). A **multi-resource is composition (*has-a*)** — horizontal orchestration of
*several* constituents through one request. They are **orthogonal**, both needed, and the model already carries
composition as the **Composite Service** (`entities/composite-service-model.md`, the `catalog-item`): multiple
constituent types + declared dependencies + T4 bindings + failure rollup, delivered through a **single request**
that produces a **Composite Entity — one UUID** across all four states, fulfilled by ordinary Service Providers
(no meta-provider). `entity_type` marks the axis: **`single`** = one constituent, **`multi`** = a composite.

**A "single-application cluster" (a cluster with its app inside, as one resource):**
```jsonc
{
  "record_type": "catalog_item",
  "handle": "app/single-app-cluster",
  "name": "Single-application cluster",
  "constituents": [
    { "component_id": "cluster",
      "resource_type": "Compute.Cluster", "type_version": "0.3.x" },
    { "component_id": "app",
      "resource_type": "Compute.Container", "type_version": "…",
      "depends_on": ["cluster"],
      "bindings": [ { "from": "cluster.kubeconfig", "to": "app.cluster_ref" } ],  // T4 data-movement, at dispatch
      "failure_effect": "…" }                                                     // how app failure rolls up
  ]
}
```
One request → one Composite Entity, one UUID (Intent holds the catalog ref + params; DCM expands to the
constituent graph at Requested; realized states record against each `component_id`; aggregate health rides
`status.conditions`). From the consumer's side it is a **single resource**; internally it is the wired
cluster+container graph.

**How the two axes compose:** the Class hierarchy *defines* each constituent type (`Compute.Cluster`,
`Compute.Container` — each with its own Base/Type/Provider structure); the Composite Service *references* them by
Class name + version and *orchestrates* them. **Classes for the parts (*is-a*), Composite Service for the whole
(*has-a*), `single|multi` marking which.** Nothing new is required.

## Orthogonal data — the references-context axis
Beyond *is-a* (Class inheritance) and *has-a* (Composite), a resource carries **orthogonal context** — data
*about* it that isn't part of its own definition: a Data-Center info bundle, an app profile, a compliance bundle.
This is the **third relationship axis — references-context** — modeled as a **classified, dereferenceable edge**
in the relationship/dependency graph (relation nature + strength, dual anchor, §10 coordinate), **not** an
assembly layer and **not** a bare untyped pointer. (**`reference_data` is retired from `layer_type`**: orthogonal
context is never merged into the assembly, so it was never a layer — it is a **linked entity**, reached by an edge.)

- **Precedent, reframed:** `app_profile` is a governed **entity** a resource links to by a **classified edge**
  (`references-context`, nature = context); the bundle can link further bundles (app_profile → network_zone) with
  transitive impact (ADR-012). A **Data-Center info bundle** is the same shape — one entity, linked by every
  resource in the DC via a `located-in` (context) edge.
- **Edge, not layer.** `layer_type` is now **assembly-only** (`base`/`core`/`intermediate`/`service`/`request`/
  `policy`) — layers build the resource's *own* effective spec. Orthogonal context is **not** a layer: DC
  power/cooling/zone data isn't part of the VM's spec; the VM **links** to the DC entity by a classified edge and
  **projects** the fields it needs (§*Projecting a related entity's field*). One entity, many linkers — no
  duplication — and the edge carries a **classified nature** (context vs dependency) a bare reference could not.
- **Same coordinate + dual anchor.** The reference rides the §10 coordinate (`<dc>.power.capacity`), resolved on
  demand, governed (T4 / sovereignty; address ≠ dereference), addressable/filterable (`…[.data_center = dc-east]`,
  the `state.mn` pattern one axis over). And it carries the **dual anchor** (§10): the immutable pin (the DC state
  at placement — reproducible/audit) **and** the named head (`dc-east-info` — the current DC state).
- **Layers declare their coverage as a filterable selector list.** A layer declares **`covers`**: a **list of
  §10 selectors** in the standard dotted language (authority +
  `Category.Type.Provider` + attribute predicates, with wildcards). A `core` encryption standard covers
  `Compute.*`; an org layer covers `Compute.VM.*` + `Storage.*`; a DC-info bundle covers
  `Compute.*[.residency = dc-east]` (or `peer.dcm.east/*`). DCM applies the layer to any resource matching **any**
  selector (union) — the **same match method** as addressing, query, and event routing. **One filter mechanism,
  not two:** a Kubernetes label selector is just this coordinate predicate applied to the `.labels` field
  (`Compute.VM.*[.labels.tier = web]`) — a special case, never a parallel construct. It also makes **layers
  themselves queryable** ("which layers cover `Compute.VM`?"). `covers` is Data (the declaration); the match is
  Policy (DCM's assembly engine). This generalizes today's single `resource_type` / `domain` coverage into a
  filterable list.
- **Layers can be skipped — governed.** A request or context declares **`skip`** (a §10 selector list of layers
  to bypass). Skippability is classed per layer: **contribution / default** layers are **freely skippable** (you
  supply the values yourself, and override supersedes them anyway); **`narrow_only` / compliance** layers are
  **not** — skipping one *loosens a constraint*, exactly what `narrow_only` forbids, so it requires **authorization
  (break-glass)**, attested and recorded; a **`policy`** layer is generally non-skippable (it *is* the gate).
  Every skip is written to the **audit log** (which layer, who authorized, why), so the assembly stays reproducible
  (T3) and a compliance bypass is never silent. **Skip-all** bypasses the whole stack — free for defaults, but each
  constraint layer still gates its own skip, so skipping the compliance layers is full, attested break-glass. How
  the stack itself assembles (precedence, override field-by-field, `narrow_only`, provenance) is the existing
  layering model (`foundations/layering-and-versioning.md`); this adds only `covers` and `skip`.
- **The contract is UDLM; the layer *definitions* are org-level.** Everything above (`covers`/`skip`/precedence/
  `narrow_only`) is the UDLM layer **contract**; *which* layers exist and what they hold (the DC-info bundle, the
  org compliance overlay) are **organization implementation details** in DCM's domain — see *Authorship & domain*.

**The three relationship axes — all existing mechanisms:**
| Axis | Relationship | Mechanism |
|---|---|---|
| **is-a** | a Class specializes a definition | `extends` (Base → Type → Provider) |
| **has-a** | a Composite orchestrates constituents | `catalog-item` constituents (`entity_type: multi`) |
| **references-context** | a resource links to orthogonal data / entities | a **classified edge** in the relationship graph (relation nature + strength, dual-anchor, §10 coordinate); dereferenceable, projectable |

### Projecting a related entity's field into the pipeline — the navigational coordinate
Referencing a bundle keeps the record **concise** (carry the linkage, don't inline the data). But often the
source needs **one specific value from the target in its own realized spec** — a bare-metal's network config
needs its Data Center's `network.fabric_id`; its power config needs the DC's `power.feed`. The linkage (edge),
the addressing (§10 coordinate), and the assembly (layers) all exist, but nothing yet **projects a target field
*along the edge* into the source's pipeline**. That is a **navigational coordinate** — the §10 coordinate reaching
its anchor by **traversing a classified edge from self**:

```
self.located-in.network.fabric_id
└ self   └ the located-in edge   └ field-path on the DataCenter at its far end
```

This is the shape of OData navigation properties / RDF property paths (both in the prior-art set) — a graph hop
in the address. It is **not a new construct**: edge (linkage) + coordinate (which field, now edge-traversing) +
layer (where it lands, with provenance) + dual anchor (reproducibility) + governed dereference. Resolving it
yields a **derived layer value** — computed by following the edge, landed in the effective spec with provenance
(LAY-008) and the dual anchor (the immutable pin captures the target field *at realization*; the named head
follows current).

**Worked example — DC info into a bare-metal request.**
```yaml
# ① DataCenter entity (rev-42), referenced by many        # ② concise bare-metal request (intent)
$id: acme.example/DataCenter#dc-east                       class: Compute.BareMetalHost
network:  { fabric_id: fab-7, mtu: 9000 }                  name: bm-genomics-01
power:    { feed: "A+B" }                                  requirements: { cpu: {min_cores: 64}, … }
location: { residency: state.mn }                          relationships:
                                                             - relation: located-in     # classified edge
# ③ a layer projects DC fields via the edge                    target: acme.example/DataCenter#dc-east
layer: core/baremetal-dc-binding                               nature: context          # not a lifecycle dep
covers: [ Compute.BareMetalHost.* ]
fields:
  network.uplink_fabric: { value: self.located-in.network.fabric_id }
  power.feed:            { value: self.located-in.power.feed }
  placement.residency:   { value: self.located-in.location.residency }   # sovereignty flows in

# ④ assembly resolves → realized spec, with provenance + pinned anchor
network:   { uplink_fabric: fab-7 }     # ⟵ dc-east.network.fabric_id (via located-in) [pin: dc-east@rev-42]
placement: { residency: state.mn }      # ⟵ dc-east.location.residency (via located-in) [head: dc-east]
```
On a later DC change (`fab-7 → fab-9`): **rehydrate** replays the pin (`fab-7`, reproducible); **`impact_report`**
surfaces `bm-genomics-01` as affected (the projection recorded a *data*-dependency); **governed re-resolve**
repoints to `fab-9` and re-pins. `nature: context` means it never gated the bare-metal's *lifecycle* — only its data.

**Policy safety — a projection must not let data bypass or hide from policy.** A projection is a *layer-contributed
value*, so policy-over-the-merged-result sees the concrete value (`residency = state.mn`) exactly as if typed — it
**feeds** policy, never skirts it. That holds under five invariants (to be formalized with the mechanism):
1. **Resolve-before-policy** — projections resolve *within the merge*; policy sees concrete values, never unresolved coordinates.
2. **Target-egress gate** — the dereference runs the *target's* egress/sovereignty policy (address ≠ dereference), not only the source's — the anti-exfil guarantee.
3. **Mandatory provenance** — source + edge + anchor recorded for every projected value; nothing enters the spec "from nowhere."
4. **Re-run policy on replay** — rehydration/re-realization re-evaluates *current* policy; a pin reproduces data, never exempts it from today's rules.
5. **Governed edge nature** — the relation's nature is validated, not self-asserted; no downgrading a dependency to `context` to escape gating.

## Layer → request data injection — two-sided scoping
A layer **injects data into a resource request** during assembly — a **static value** (`encryption: required`) or
an **edge-projected value** (`self.located-in.network.fabric_id`, §*Projecting…*). Which layer reaches which
request is a **two-sided handshake**, and both sides speak the one §10 selector language (no new construct):

**Target scoping — which requests receive the injection (the *layer* declares):**
- **Entity scope — `covers`** (§above): the §10 selector list over authority + `Category.Type.Provider` +
  attribute predicates. *Which entities.*
- **Process scope — `applies_on`**: the lifecycle operations the layer injects during (`provision`, `migrate`,
  `rehydrate`, `day2`, …) — the same lifecycle-scope vocabulary policies use. *Which processes.* A DC-binding layer
  injects on `provision` + `rehydrate`, not on a `label-update`.

**Source scoping — which layers feed a given request (the *request/profile* declares):**
- **Source selector — `from_layers`**: a §10 selector over the **layer graph** naming the layers a request draws
  from — usually inherited from the request's **profile** (the org/tenant layer stack), occasionally set
  explicitly. *Which sources.* This **bounds** the assembly: a tenant-A request draws tenant-A's layers even if a
  tenant-B layer's `covers` would match — the source selector, not `covers`, holds the boundary.
- **`skip`** (§above): the negative form — bypass named layers, governed (break-glass for constraint/compliance).

**Injection = the intersection.** A layer `L` injects into request `R` iff `R.target ∈ L.covers` (entity) **and**
`R.operation ∈ L.applies_on` (process) **and** `L ∈ R.from_layers` (source) **and not** `L ∈ R.skip`. Layers
*advertise* applicability (covers + applies_on); requests *select* sources (from_layers) — publish ⋈ subscribe,
one selector mechanism on both ends. Because injection lands data *into the spec*, it is an **ingress crossing**:
`PROJ-P6` admission applies, and source-selection is itself an ingress-policy surface (ADR-041).

**Example A — static injection, two-sided.**
```yaml
# the layer (source) declares its target scope
layer: core/compliance-encryption
covers:     [ Compute.*, Storage.* ]         # target: entity
applies_on: [ provision, migrate ]           # target: process
fields: { encryption: { value: required, authority: immutable } }   # static injected value

# the request declares its source scope (here, inherited from its profile)
request: Compute.VM  web-01   operation: provision
profile: acme/sovereign        # → from_layers: [ core/compliance-*, org/acme/* ]
# web-01 ∈ Compute.* (covers) ∧ provision ∈ applies_on ∧ core/compliance-encryption ∈ from_layers
#   → encryption: required (immutable) merged into web-01's effective spec, with provenance
```

**Example B — projected injection is the same mechanism.** The `core/baremetal-dc-binding` layer (§*Projecting…*)
carries `covers: [Compute.BareMetalHost.*]` + `applies_on: [provision, rehydrate]`; its `fields` are
edge-projected (`self.located-in.…`). Static and projected injection differ only in whether a field's value is a
literal or a navigational coordinate — the two-sided scoping is identical.

**Example C — source scoping holds a tenant boundary.** `tenant-a/net-defaults` and `tenant-b/net-defaults` both
`cover: [Compute.VM.*]`. A `tenant-a` request's `from_layers` (from its profile) includes only `tenant-a/*`, so it
receives A's defaults, **never** B's — even though B's `covers` matches. `covers` says *who may*; `from_layers`
says *who does*. Both are required; neither alone is the boundary.

## Worked illustrations
- **`encryption` ramp** — a Provider Class element (`Compute.VM.OCPVirt` offers `encryption: sev-snp`) recurs at
  a second provider, is contributed/promoted **up** to the `Compute.VM` Type Class, and — with enough adoption —
  to the `Compute` Base Class. Same data element + value list throughout; only its Class moved.
- **Compute Base Class** — `cpu`/`memory`/`guest_os`/`storage`(requirements)/`network` defined once at
  `Compute`; `Compute.VM` and `Compute.BareMetalHost` are Type Classes extending it; instantiating bare
  `Compute` lets Placement pick VM-vs-metal and policy-fill complete the type-specific blanks.
- **`state.mn` query pair — root vs attribute, structural vs predicate (the filtering payoff).** Two queries that
  *look* alike and mean opposite things, both expressible because §10 kept `resolving_authority` (root) and
  `residency` (attribute) distinct:

  ```
  compact:  state.mn / Compute.VM.*                              → VMs MANAGED BY Minnesota's DCM   (authority-rooted)
  URL:      https://state.mn/Compute/VM

  compact:  peer.dcm.* / Compute.VM.* [ .residency = state.mn ]  → VMs RESIDING in Minnesota, across ALL DCMs (attribute-filtered)
  URL:      https://peer.dcm.*/Compute/VM?residency=state.mn     (authority=host, entity=path, filter=query)
  ```

  A VM managed by `peer.dcm.us-central` but hosted in an MN datacenter appears in the **second**, never the first —
  a query an authority-only model cannot express. It composes **two filter mechanisms already in the grammar**:
  the **structural** filter is dotted prefix/wildcard over the *authority* (`peer.dcm.*` = fan out across every DCM)
  and *entity* (`Compute.VM.*` = all VMs, any Provider Class); the **attribute predicate** `[.residency = state.mn]`
  filters on a *field value* — the same `<anchor>.<field-path>` coordinate (§10) serving as the left-hand side of a
  comparison, so field addressing does double duty (name a value **and** filter on one). Maps directly to
  OData `$filter=residency eq 'state.mn'` federated across services, or a SPARQL `SERVICE` fan-out with `FILTER`.
  **Sovereignty at fan-out scale:** the gate applies **per authority** — each DCM runs its own sovereignty gate on
  the read, each cross-authority resolve is attributed (`resolving_authority`), and the result is **best-effort /
  sparse** (the union of what each sovereign estate chooses to expose). No silent global enumeration. And because
  `residency` is recorded as *provenance over time*, "VMs that **were** in MN" is the same predicate on the audit
  trail — the model answers *were* and *are* with one attribute on different time axes.

## Prior art / standards alignment
Every component lands on a mature standard — which is the **convergence signal** (ADR-023's argument: independent
standards agreeing on a shape is the strongest reason to adopt it, not invent). The synthesis is UDLM's; the
parts are not.

| Paradigm piece | Matches |
|---|---|
| Base/Type/Provider **extends** (add/refine, never contradict) | **OData** `BaseType`; **XSD** complexType extension/restriction (literally add/refine); **RDF/RDFS** `subClassOf`; **TOSCA** `derived_from`; DMTF **CIM** |
| `SharedDataElement` scoped to a class, inherited down | **RDF/RDFS** properties with `rdfs:domain`; **schema.org** class-scoped properties; OData structural properties |
| Dotted coordinate + **URL form** + field as fragment | **OData** URL addressing / `@odata.id` / `@odata.type`; **URI** (RFC 3986); **JSON Pointer** (RFC 6901); **Redfish** `@odata.id` |
| Class/instance identity as a URL | **Linked Data** (URI identity, governed dereference); OData; UDLM's own `$id` (already a URL) |
| Federated **authority** (dotted, delegable, wildcard) | **DNS** (delegation, wildcards); **URI** authority; **Matrix** / ActivityPub (server-authority federation) |
| **Filtering** across authority + entity + field segments | **DNS** wildcards; **LDAP** DN + filters; **OData** `$filter`; AMQP/MQTT topic routing; JSONPath |
| Policy-fill of blanks (defaults, layering) | **Kubernetes** defaulting/admission; **OSCAL** profiles; JSON Schema defaults |
| Provider capability declaration | **TOSCA** capabilities/requirements; OData annotations/vocabularies |

**Strongest single anchor: OData / Redfish** — it covers the most (typed inheritance + URL addressing + versioning
+ navigation + `$filter`), and **UDLM already adopts Redfish** (OData-based), so aligning is T5-*consistent*, not a
new adoption. **RDF / Linked Data** is the second (URI identity + class hierarchy + governed dereference +
federation; JSON-LD as the serialization bridge). **TOSCA** is the domain match (node-type inheritance +
capabilities). **DNS + URI** carry the federated dotted addressing.

**What is UDLM's own (no direct standard):** portability-**gradient-by-scope**, the **demand-driven promotion
ramp**, and the **sovereignty-gated dereference**. These compose the standards above; they aren't in any one of
them.

**T5 consequence (the discipline applied to the paradigm itself):** express this as an **adoption/profile of OData +
linked-data + URI/DNS conventions** where they fit (OData addressing, `@odata.id`/`@odata.type`, JSON Pointer
fragments, DNS-style authority) — not a bespoke re-invention. The dotted namespace's **natural filtering** — prefix/
wildcard match across *authority* (`peer.dcm.eu.*`), *entity* (`Compute.VM.*`, `Compute.*`), and *field-path*
(`*.cpu.encryption`) segments — is likewise a property these standards already exploit (DNS wildcards, LDAP/OData
`$filter`, topic routing), and it serves policy scoping, RBAC, routing, discovery, and impact analysis uniformly.

## Open / deferred
- **Base Class instantiability: DECIDED — yes** (portability at its highest level; §4).
- Generic-Compute request UX (how a Base-Class instantiation is surfaced to a consumer) — design later.
- Attestation — deferred (§9), additive.
