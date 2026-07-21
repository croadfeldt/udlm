# UDLM Adopted Standards — the *Adopt* disposition

When a domain's data is already modeled by a credible external standard, UDLM does not re-model it.
It **adopts** the standard: it carries the *identity* that lets external data attach, a *version-pinned
reference* to the standard, and the *binding* — but never re-expresses the standard's schema in the
portable model. This document formalizes that disposition, the constructs it introduces, and the split
between what the **Data** model carries and what **Policy** does.

It is the elaboration of **core tenet T5** (`core-tenets.md`). The worked example is cost
(`../docs/resource-type-registry-design-notes.md` §4a): FOCUS + OpenCost, adopted, not absorbed.

## 1. The disposition test — absorb / embed / adopt

Every time a domain bumps against UDLM, pick one disposition:

| Disposition | Meaning | When |
|---|---|---|
| **Absorb** | Define the schema *inside* UDLM (a Resource Type). UDLM owns a model of the domain. | Only when **(a)** no credible external standard exists **AND (b)** the data's lifecycle is genuinely UDLM's to custody (e.g. a resource's own desired/realized state — the registry's whole job). |
| **Embed** | Bake the domain's fields into every entity. | Never — a stronger T1 violation than absorb. |
| **Adopt** | **Reference** an external standard by conformance + binding; UDLM owns only identity + the pointer. | Whenever a credible external standard already models the data (the common case for adjacent domains). |

The litmus for "adopt vs absorb": **if the external standard releasing a new version would force a
change to a UDLM schema, you absorbed it.** True adoption means UDLM changes nothing when the standard
revs — because it never held the standard's columns.

Absorbing adjacent-domain data duplicates an external system's record and its lifecycle — a breach of
**T1** (the data model is a custodian, not the owner of every domain's data) and of the
Information-Provider contract's explicit warning against "copy the data in"
(`../contracts/information-providers.md` §2).

## 1a. Two tiers of adopted standard — route by kind

Not every adopted standard needs the same machinery. Before integrating, classify the standard — it
tells you exactly what to build and what to skip:

| Tier | What it standardizes | Examples | Implement | Do **not** build |
|---|---|---|---|---|
| **Tier 1 — value / codelist** | the allowed *values of a single field* | ISO 4217 (currency), ISO 8601 / RFC 3339 (time), RFC 9562 (UUID), ISO 3166 (country), IANA tz | a **referenced field constraint** ("conforms to ISO 4217") — reference it, never copy/enumerate it | no support matrix, no version negotiation, no translation, no effective-version provenance |
| **Tier 2 — record / schema** | the *shape + semantics of a whole dataset* | FOCUS, OpenCost, OSCAL, SCIM | the **full apparatus**: an `adopts[]` reference + identity join, a provider `adopted_standard_support` matrix, DCM negotiation/translation (ADS-001…010), effective-version provenance | — |

**Rule of thumb:** *does the standard version in a way that changes its shape?* **No → Tier 1** (a near-constant
vocabulary — pin nothing, negotiate nothing). **Yes → Tier 2** (the whole reason the ADS machinery exists).

Tier 2 standards routinely **contain** Tier 1 ones — FOCUS's `BillingCurrency` column *is* an ISO 4217
code — so adopting the record pulls its field-level codelists along for free; you don't adopt them
separately.

**Why this matters (integration cost):** mis-routing is expensive in both directions. Applying the ADS
machinery to a codelist is wasted surface area and config; treating a schema standard as a codelist
(a plain string) silently breaks the moment its version moves or a provider supports a different one.
Routing by tier is the integrator's first decision and the cheapest one to get right.

## 1b. The adoption decision procedure (and the net-negative test)

The disposition test (§1) answers *absorb / embed / adopt* for a single standard. This is the procedure that
governs **every** proposal to add a definition, type, or mechanism — its aim is to keep the model small: **a good
adoption should be net-negative on bespoke surface area** (it retires homegrown things, not just adds).

Run these in order:

1. **Gate — non-duplication.** Don't add anything to the substrate unless it has **clear usefulness that does not
   duplicate existing functionality.** Strip the candidate to its genuinely new slice; **reuse the universal
   contracts** (audit, field-level provenance, versioning, identifiers, events) rather than re-describing them.
2. **Clean fit? → adopt; don't repeat.** If a wide/established standard cleanly fits, **adopt it** — do not build a
   parallel bespoke form alongside it.
3. **Clean replacement? → adopt *and retire the bespoke*.** If the standard cleanly subsumes an existing homegrown
   definition (or a pattern we built more than once), **consolidate onto the one standard form** and remove the
   duplicate. This is where surface area goes *down*.
4. **No clean fit? → adopt the principles + format, and supersede.** Extend the standard rather than inventing from
   zero; take its vocabulary/shape and go beyond it where the domain requires. **Don't force** a poor fit.
5. **Ground in producers & consumers.** A definition earns its fields only if real producers write them and real
   consumers read them; that same flow defines the validation the realization must do. No field without a
   produce/consume path.

> **In one line:** *use wide standards where they cleanly fit, otherwise roll our own; don't force, adopt if
> clean, don't repeat; if it doesn't fit cleanly, adopt the principles and format to supersede while adopting.*

**Worked example (DecisionRecord / ADR).** The decision-record need → adopt the **ADR / MADR** standard (don't coin
a new term); it is *complementary* to UDLM audit/provenance/versioning (reuse, step 1); it cleanly *consolidates*
two homegrown forms a realization built twice — DAV's self-improvement `improvement_proposals` and its architecture
resolutions — into **one target-parameterized Resolution/Decision Record** (step 3, net-negative); **SARIF** does not
cleanly fit architecture findings → adopt its principles only (step 4); the Knowledge-family `Antipattern` is related
but not the same → don't force. Defined as a Knowledge entity type in `../entities/knowledge-family.md` §4.5.

## 2. What adoption carries (Data) vs delegates (Policy)

| Concern | Owner |
|---|---|
| Resource **identity / handle** — the join key external data attaches to | **UDLM (Data)** |
| **Version-pinned conformance reference** to the standard (which standard, which version/range) | **UDLM (Data)** |
| The **binding** (this resource has data of standard X, joined on identity ↔ column Y) | **UDLM (Data)** |
| **Provider support matrix** — which standard versions a provider can emit/consume | **UDLM (Data)** — a provider capability record |
| **Consumer/type requirement** — which version a consumer needs | **UDLM (Data)** |
| The standard's **schema / columns / semantics** | the **external standard** (referenced, never copied) |
| **Version negotiation** (required ∩ supported), **enforcement** (reject on no overlap), **translation** between versions | **Policy (DCM)** |
| The **effective negotiated version** + any translation performed | **UDLM (Data)** — recorded as provenance (E4) |

The pattern restates the data/policy boundary: **the data declares which standard versions are in
play; Policy decides what to do about them.**

## 3. The adoption constructs (Data)

Three declarative records. All are nouns — no logic.

### 3.1 Adopted-standard reference (on a type, a binding, or a requirement)
```json
{
  "adopts": [
    {
      "standard": "FOCUS",
      "version": ">=1.3 <2.0",
      "role": "cost-and-usage data for this resource",
      "identity_join": { "local_field": "uuid", "standard_column": "ResourceId" },
      "source": "https://focus.finops.org/",
      "license": "CC-BY-4.0",
      "license_compatibility": "compatible-reference"
    }
  ]
}
```
`version` is a pinned value or a range over the standard's own scheme (FOCUS/OpenCost use
`MAJOR.MINOR`). `identity_join` is the anchor only UDLM can provide. The standard's columns are **not**
restated here.

**`source`, `license`, and `license_compatibility` are mandatory** (SPEC-DESIGN-REQUIREMENTS §22–23): the
provenance (name + version + canonical URL) and a recorded license-compatibility verdict against the
UDLM license (Apache-2.0 — declared once in [`README.md` § License](../README.md#license) /
the repository `LICENSE` file). `license_compatibility` ∈ `{compatible-reference, compatible-vendor,
reference-only}` — `reference-only` flags a copyleft/file-scoped source (GPL/LGPL/MPL) whose **names may
be referenced but whose text/files MUST NOT be vendored** into UDLM. Because adoption only references
the standard's vocabulary (field names = facts) and never restates its columns, the default verdict is
`compatible-reference` regardless of the source license — adopt-by-reference is license-clean by
construction; the check exists to catch the cases where someone is tempted to *copy* (absorb) instead.

### 3.2 Provider support matrix (a provider capability declaration)
```json
{
  "adopted_standard_support": [
    { "standard": "FOCUS",    "supports": ">=1.2 <2.0", "preferred": "1.4", "direction": "emit" },
    { "standard": "OpenCost", "supports": "1.x",         "preferred": "1.x", "direction": "emit" }
  ]
}
```
This is how a provider **details which versions it can support** — pure data, validated and trust-stamped
like any other provider capability (`../contracts/provider-contract.md`, IP advanced contract). A
provider may emit, consume, or both (`direction`).

### 3.3 Consumer / type requirement
A consumer (or a type) expresses what it needs as an `adopts` reference with a `version` range — e.g. a
report that needs FOCUS allocation columns requires `FOCUS >=1.3`. Also pure data.

### 3.4 Where a standard lives, and what `direction` means (Proposed)

Two rules govern *where* a standard is declared and *how* its data crosses the boundary. Both follow from
the naturalization boundary (ADR-023): **native touches the edge, and nothing else** — internally the model
is always UDLM.

**(a) Substrate adopts neutral; providers declare native.**
- A **type's `adopts[]`** (§3.1) carries the *vendor-neutral* standard the type maps to — the shared
  join-key / conformance reference (Redfish `ComputerSystem` for `Compute.*`, FOCUS for cost). It must be a
  credible vendor-neutral standard, because it sits on the portable substrate.
- A **provider's `adopted_standard_support`** (§3.2) carries the *native* standards **that provider** can
  emit/consume (KubeVirt, vSphere, EC2, Metal3). Provider-specific, declared on the provider.
- **Why:** the adopt is a join-key, not the portable shape — the spec is UDLM-generic and the provider
  naturalizes it either way, so a provider-native standard on the *type* buys no portability and biases the
  substrate toward one ecosystem. This is T5 sharpened by *where*.
- **Review finding + audit:** a type adopting a single-ecosystem standard as tier1 (as
  `Compute.VirtualMachine` did with KubeVirt) moves it to the provider surface; sweep all types for
  provider-native `adopts[]`.

**(b) `direction` is edge translation, never a bypass.** `emit` / `consume` describe translation *at the
boundary*, one direction each:
- **`consume` (in)** = the provider **ingests a native artifact and naturalizes it INTO UDLM** — the
  **greening-the-brownfield** ingress: a discovered/imported KubeVirt VM, an OVA, or existing state becomes a
  generic `Compute.VirtualMachine` (Discovered → adopted to intent), then managed through the full machinery
  (policy, placement, dependency graph, provenance, the four states). *Adoption is convergence-based — see
  ADR-030 (adopt discovered state) and DCM brownfield ingestion.*
- **`emit` (out)** = the provider **denaturalizes UDLM → native** for a downstream consumer (FOCUS cost data,
  an OVA export).
- **`consume` ≠ accept-and-run.** A provider that *applied a native spec without naturalizing it to UDLM*
  would bypass the control plane — a **review finding**, not a supported mode. Greening-the-brownfield is the
  only sanctioned way native input enters, and it always lands as UDLM.

**So what `adopted_standard_support` is *for*.** It is the provider's **edge-translation menu** — which native
standards it can naturalize **in** (import/discovery/greening) and **out** (emit/export), at which versions.
DCM uses it to (1) route **brownfield ingestion** (which provider can green a KubeVirt or vSphere estate),
(2) route **emit/export** (which provider can produce FOCUS / an OVA), and (3) run **version negotiation**
(§4). It is **not** the provider's internal realization mechanism — how a provider *provisions* from UDLM
intent is opaque naturalization and is never declared. **Earn-its-keep:** an `adopted_standard_support` entry
is warranted only where it is a real *edge* capability a consumer or the greening flow uses; an entry that
merely restates "this is how I internally realize" is opaque and does not belong (same test we apply to
fields and data points).

## 4. Version negotiation, enforcement, translation (Policy)

Given a **requirement** (range) and a provider's **support matrix** (range), Policy resolves the
intersection and acts — this is the only "logic" in the model, and it lives in DCM:

1. **Accept** — requirement ∩ supported is non-empty → bind at the highest common version (or
   `preferred` if inside the overlap). Record the effective version.
2. **Translate** — no direct overlap, but a deterministic mapping exists between a supported version and
   a required one (e.g. provider emits FOCUS 1.2, consumer needs 1.4; allocation columns are derivable
   or null-filled). Policy performs the translation — **transformation is Policy (T2)** — preferably by
   reference to the standard's own published migration, never via an evaluator embedded in the data.
3. **Reject** — no overlap and no translation path → the binding is non-conformant; surfaced, not
   silently dropped.

Determinism is preserved (**T3**): the *data* only declares versions; the translation is an explicit,
audited Policy decision. Provenance records the **effective version** and, when Policy translated, the
source version + translation reference, with confidence/authority adjusted for the derived value
(`../contracts/information-providers-advanced.md`). "As needed, based on the implementor's needs" =
the requirement range + the provider matrix are the implementor's inputs; Policy is the negotiator.

## 5. Worked example — cost (FOCUS + OpenCost)

- **Identity:** the `Compute.Cluster` resource's `uuid`/handle ↔ FOCUS `ResourceId`. UDLM owns this.
- **Provider matrix:** the cost-SP (`dcm#57`) declares `FOCUS supports ">=1.2 <2.0" preferred 1.4`,
  `OpenCost supports "1.x"` — emit direction.
- **Requirement:** a chargeback view needs allocation columns → requires `FOCUS >=1.3`.
- **Policy:** provider at 1.4 → **accept**, bind at 1.4. A different provider that only emits 1.2 →
  **translate** 1.2→1.3 if the mapping is deterministic, else **reject**. The effective version is
  recorded on the realized entity as provenance.
- **Result:** any FOCUS-emitting cost provider satisfies the same binding; cost is vendor-agnostic
  *because* it was adopted, not modeled.

## 6. Where it plugs in (contract surfaces)

- **Meta-schema** — a Resource Type / binding MAY carry an `adopts[]` reference (§3.1).
- **Provider contract** — the capability declaration gains `adopted_standard_support[]` (§3.2).
- **Policy contract** — version negotiation/translation is a Policy responsibility (§4).
- **Realized-entity** — the negotiated effective version (+ translation) is provenance (E4).

> Wiring these into the JSON meta-schema / provider-contract schema is the follow-up implementation;
> this document is the normative contract they implement.

## 7. Other adoption candidates (the pattern generalizes)

"Adopt the standard, bind by identity, serve via a provider, negotiate versions in Policy" applies
beyond cost:

| Domain | Adopt | UDLM keeps |
|---|---|---|
| Cost / usage | **FOCUS** (+ **OpenCost** for k8s allocation) | identity + binding + effective-version provenance |
| Compliance / controls | **OSCAL** | identity + control-binding |
| Identity / people | **SCIM** | the join key; data served by an HR Information Provider |
| Telemetry | **OpenTelemetry** semantic conventions | resource identity ↔ `resource` attributes |
| Currency | **ISO 4217** | already de-facto adopted (we reference codes, don't enumerate) |

Each keeps UDLM **thin** — the substrate that holds identity, lifecycle, relationships, and bindings —
rather than swelling into a model of every adjacent domain. That is the architectural form of "don't
reinvent the wheel."

## 8. Changing an adopted standard — the runbook

Adopting, version-bumping, or replacing a standard touches four places. Do them in order; `ADOPT-001`
gates the register step. This is the end-to-end process the pieces above assume.

**A. Adopt a new standard.**
1. **Disposition test** (§1): absorb, embed, or adopt? Only *adopt* uses this doc.
2. **Net-negative test** (§1b): the adoption must remove more bespoke surface than it adds.
3. **Record the decision** in [`registry/standards-adoption-register.md`](../registry/standards-adoption-register.md) — a DecisionRecord-shaped entry: what, why *including alternatives considered*, where, when (git instant), who, and the license verdict. `ADOPT-001` (`tests/validate_registry.py`) fails CI if a type/provider `adopts[]` a standard string with no entry.
4. **Reference it:** add the `adopts[]` entry on the type/binding (§3.1) and the provider support matrix (§3.2). Cite the standard by name; never restate its schema (T5 + the single-source rule).

**B. Bump the version of an adopted standard.**
1. Update the requirement/support ranges (§3.3, §3.2) — the data only declares versions.
2. **Negotiation is Policy** (§4): DCM resolves requirement ∩ support and Accepts / Translates / Rejects at bind time; the effective version is recorded as provenance. No spec change is needed for a peer to run a different in-range version.
3. If the *adopted range itself* changes (drop an old major, add a new one), amend the register entry — **append, don't rewrite** (statuses reuse DecisionRecord curation states).

**C. Replace or retire a standard** (e.g. the bespoke error envelope → RFC 9457).
1. **Record the retirement and the new adoption** in the register — retirements and rejections are first-class rows, so the next reader sees *why* the old one went.
2. **Change the binding once**, at the standard's single home (the [file index](../docs/file-index.md) says which file owns it), and reference it everywhere else — do not restate it (single-source rule, `SPEC-DESIGN §33`).
3. The spec change flows through normal versioning ([`VERSIONING.md`](../registry/VERSIONING.md)): a breaking change is a SPEC MAJOR, an additive one a MINOR.

**Rule of thumb.** The *decision* lives in the register (one row, immutable, superseded not edited); the *binding* lives in one spec file (referenced, never restated); *version reconciliation* is Policy at runtime. **If a standard is cited in prose but has no register row, that is the gap to close** — register it (this is exactly how RFC 9457 slipped; it is now registered).
