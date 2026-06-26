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
| **Tier 1 — value / codelist** | the allowed *values of a single field* | ISO 4217 (currency), ISO 8601 / RFC 3339 (time), RFC 4122 (UUID), ISO 3166 (country), IANA tz | a **referenced field constraint** ("conforms to ISO 4217") — reference it, never copy/enumerate it | no support matrix, no version negotiation, no translation, no effective-version provenance |
| **Tier 2 — record / schema** | the *shape + semantics of a whole dataset* | FOCUS, OpenCost, OSCAL, SCIM | the **full apparatus**: an `adopts[]` reference + identity join, a provider `adoptedStandardSupport` matrix, DCM negotiation/translation (ADS-001…010), effective-version provenance | — |

**Rule of thumb:** *does the standard version in a way that changes its shape?* **No → Tier 1** (a near-constant
vocabulary — pin nothing, negotiate nothing). **Yes → Tier 2** (the whole reason the ADS machinery exists).

Tier 2 standards routinely **contain** Tier 1 ones — FOCUS's `BillingCurrency` column *is* an ISO 4217
code — so adopting the record pulls its field-level codelists along for free; you don't adopt them
separately.

**Why this matters (integration cost):** mis-routing is expensive in both directions. Applying the ADS
machinery to a codelist is wasted surface area and config; treating a schema standard as a codelist
(a plain string) silently breaks the moment its version moves or a provider supports a different one.
Routing by tier is the integrator's first decision and the cheapest one to get right.

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
      "identityJoin": { "localField": "uuid", "standardColumn": "ResourceId" },
      "source": "https://focus.finops.org/",
      "license": "CC-BY-4.0",
      "licenseCompatibility": "compatible-reference"
    }
  ]
}
```
`version` is a pinned value or a range over the standard's own scheme (FOCUS/OpenCost use
`MAJOR.MINOR`). `identityJoin` is the anchor only UDLM can provide. The standard's columns are **not**
restated here.

**`source`, `license`, and `licenseCompatibility` are mandatory** (SPEC-DESIGN-REQUIREMENTS §22–23): the
provenance (name + version + canonical URL) and a recorded license-compatibility verdict against the
UDLM license (Apache-2.0). `licenseCompatibility` ∈ `{compatible-reference, compatible-vendor,
reference-only}` — `reference-only` flags a copyleft/file-scoped source (GPL/LGPL/MPL) whose **names may
be referenced but whose text/files MUST NOT be vendored** into UDLM. Because adoption only references
the standard's vocabulary (field names = facts) and never restates its columns, the default verdict is
`compatible-reference` regardless of the source license — adopt-by-reference is license-clean by
construction; the check exists to catch the cases where someone is tempted to *copy* (absorb) instead.

### 3.2 Provider support matrix (a provider capability declaration)
```json
{
  "adoptedStandardSupport": [
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
- **Provider contract** — the capability declaration gains `adoptedStandardSupport[]` (§3.2).
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
