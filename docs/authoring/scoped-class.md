# Authoring a scoped Class

**What this gets you.** A Class in the Base/Type/Provider hierarchy (ADR-038 — scope *is* portability) that
extends its parent without contradicting it, compiles down to exactly the flat resource-type spec
consumers already read, and passes CI unchanged. When you author at the Class layer, one field can be
declared once and inherited by every type in a category — and two providers declaring one Type Class is
what turns an engine migration into a provider swap.

A **Class** is the authoring layer of the resource-type system. It lives in
`registry/classes/<name>.yaml`, validates against `registry/class.schema.json` (read it first), and is
built from **SharedDataElements**: a data element (`element` name), its declarative `schema` fragment,
its curation `state` (`proposed` → `canonical`), and the `scope` it is held at. There are three tiers:

- **Base** (`class: base`) — single-segment name (`Compute`). Elements here port across every type in
  the category.
- **Type** (`class: type`) — two segments (`Compute.VM`), `parent: Compute`. Elements port across the
  type's providers.
- **Provider** (`class: provider`) — three segments (`Compute.VM.OCPVirt`), provider-authored. Elements
  are provider-bound.

The scope position **is** the portability — there is no separate `portability` field to declare (ADR-038
§3). An element at `Compute` scope is portable across the category *because* it sits there.

## 1. When to use it — and when not

Author a Class when the thing you are adding is **a field or vocabulary that is shared, or refined, across
a family** — the CPU shape reused by VM, BareMetal, and Container; the OS-patching intent two engines both
honor. The Class layer is where you say it once and let the hierarchy carry it.

Do **not** author a Class when:

- You are adding **a governed list of values** an element draws from (the actual storage-tier terms) —
  that is reference data (`reference-data.md`). The Class *names* the vocabulary via `values.reference_data_type`;
  the terms are curated records elsewhere.
- The element would **contradict** its parent (change a type, widen an enum, loosen a bound). That is not
  a refinement — the Liskov gate refuses it, and correctly. Model it as a sibling, or fix the parent.

## 2. The steps, in order

1. **Pick the tier and name.** Base, Type, or Provider — the segment-count of `resource_type` must match
   `class` (`Compute` = base, `Compute.VM` = type). A Type or Provider Class names its `parent` (the
   dotted name one segment shorter); a Base Class has none. **Produces:** `registry/classes/<name>.yaml`
   with a valid header (`$id`, `uuid`, `record_type: class`, `class`, `resource_type`, `family`,
   `version`, `status`, `metadata`).
2. **Author the SharedDataElements.** Each element carries `element` (lowercase field name), `scope`
   (which MUST equal the Class's own `resource_type`), a declarative `schema` fragment (type / enum /
   bounds / pattern — data only, never executable behavior), `state`, and cold-reader `description`
   prose. **Produces:** the composable units this Class contributes.
3. **Refine, never contradict, on redeclare.** If your element name already exists on an ancestor, your
   `schema` must *narrow* the ancestor's: a tighter enum (a subset), a tighter numeric bound, an added
   `required` — never a type change, a widened enum, a looser bound, or a dropped `required`. A brand-new
   element name is always a legal add. **Produces:** a child that *is-a* parent (the Liskov invariant).
4. **Point governed values at reference data.** For an element whose values are a curated vocabulary, add
   `values.reference_data_type: <kind>` instead of an inline enum (e.g. `storage_tier`). The tier is a
   named requirements floor — name-selectable but requirements-authoritative (ADR-036); the profile
   decides whether an instance may write a bare string or must resolve a canonical term. **Produces:** a
   governed element, curatable independently.
5. **Add the `coverage:` block** — `use_cases:` and `flows:`. A Class is its own worked example, so
   `examples` is not required. Point at the `scoped-class/*` UCs and
   `docs/flows/scoped-class-lifecycle.md`. **Produces:** the story link.
6. **Compile.** Run the generator to compile your Type Class + its ancestors into the flat spec, and
   **commit** the generated artifact under `registry/generated/`. **Produces:** `registry/generated/<Type>.json`,
   the wire contract consumers read — proof your Class lands as a conformant flat spec.

## 3. Completeness checklist — and the gate that enforces each

| Ships with the Class | Enforced by |
|---|---|
| Validates against `class.schema.json`; a Type/Provider Class names its `parent` | `registry/tools/validate.py`, `tests/validate_registry.py` |
| `supports` clauses are well-formed (min ≤ max, bounds comparable, `step` inside a range) and never exceed the element's own schema | `tests/check_class_liskov.py` |
| A child's `supports` clauses are contained in its parent's — the offer narrows, never widens | `tests/check_class_liskov.py` |
| Every element's `scope` equals the Class's `resource_type` | `tests/check_class_liskov.py` — scope check |
| Every redeclared element **refines** its ancestor (add-or-refine, never contradict) | `tests/check_class_liskov.py` — **LSK-001** (type change / enum widen / looser bound / dropped required) |
| The Type Class compiles to a spec that validates against `resource-type-spec.schema.json` | `registry/tools/generate_class_specs.py --check` — **GEN-002** (compiled spec not conformant) |
| The committed `registry/generated/<Type>.json` is a faithful recompilation (not stale) | `registry/tools/generate_class_specs.py --check` — **GEN-001** (stale — regenerate) |
| A `coverage:` block whose UC handles and flow files resolve | `registry/tools/spec_coverage.py --check` — **COV-001** |

Three ideas the gates encode, worth holding in mind as you author:

- **SharedDataElements** are the composable unit — "base field," "shared vocabulary," and "provider
  extension" collapse into one shape distinguished only by `scope`. You promote an element across scopes
  (a governed contribution, visible in diffs), you don't copy it.
- **The Liskov invariant** — a Provider Class *is-a* Type Class *is-a* Base Class. A precise
  JSON-Schema subtype check is undecidable in general; the gate enforces the common, decidable refinement
  rules that catch real contradictions, and self-tests that it still catches a planted type-change.
- **Compile-to-flat-spec** — Classes author; flat specs are *generated*, never hand-edited. The generated
  spec is your Class's elements plus every ancestor's, landed under `spec.properties`, `required` = the
  non-optional set, with a `compilation_provenance` block recording the source Classes + versions so
  `--check` can verify by faithful recompilation. Consumers never break: same meta-schema, same wire
  contract.

## 3a. Declaring what a provider OFFERS — `supports`

A Provider Class does two things, and they are different declarations on the same element set:

| It says | How |
|---|---|
| **what I REQUIRE** to realize a request | add the element and mark it `optional: false` |
| **what I SUPPORT** — the values and ranges on offer | `supports` on the element |

`schema` says what shape is **valid** and stays portable. `supports` says what is **offered here**.
It narrows the offer; it may never widen what the schema permits, and a gate enforces both.

Read it two ways, because it is one declaration:

- as an **offer** — what this provider can satisfy
- as a **menu** — what a consumer may select

The catalog reads this. **It is not restated anywhere** — a second copy in a weaker vocabulary is a
DRV-001 violation, and it drifts.

```yaml
- element: memory
  scope: Compute.VM.CExampleCloud
  schema: { ... }                       # unchanged: what is VALID, and portable
  supports:
    - values: [512Mi, 1Gi, 2Gi, 4Gi]    # discrete — the small end is fixed sizes
    - min: 8Gi
      max: 384Gi
      step: 8Gi
      when: { instance_family: general }        # GROUPED: this range only under this family
    - min: 8Gi
      max: 768Gi
      step: 8Gi
      when: { instance_family: memory-optimized }
```

The supported set is the **union of the clauses**. A clause with no `when` always applies; a clause
with `when` applies only when those other selections hold. That is how a support **matrix** is
expressed — and it is why `512Gi` can be a real offer under one family and an invalid *combination*
under another.

**Why the matrix is data and not JSON Schema `if`/`then`.** Containment stays decidable: a child's
clauses must sit inside its parent's, which is a comparison over declared clauses. Conditional
schema *logic* is undecidable in general, so a Provider Class using it would validate as JSON Schema
while being ungated for subtyping. **Data narrows checkably; logic does not.**

**Use a governed vocabulary for named shapes.** Where the offer is a curated list that changes
without a spec edit — instance families, storage tiers, OS images — declare
`values.reference_data_type` rather than an inline enum. Ranges cover the continuous axes;
vocabularies cover the discrete rows.

**A request is this document with the ranges collapsed.** Each range becomes one selected value —
or nothing, where the element is optional. Layers and policies perform that collapse, and the
convergence loop runs until every range has become a value. That is also what makes placement
eligibility computable: a provider is eligible exactly when every selected value falls inside its
declared clauses and every required element is present.

## 4. A worked pointer

Copy the pair **`registry/classes/resource/compute/_base.yaml`** (the Base Class — `cpu`, `memory`, `storage`,
`storage_tier`, `guest_os` at `Compute` scope) and **`registry/classes/resource/compute/vm/_base.yaml`** (the Type Class
— `parent: Compute`, adding VM-only `firmware` and `boot_order`). Together they show a Base authored from
scratch, a Type extending it under Liskov, a governed-vocabulary element (`storage_tier` →
`values.reference_data_type`), and coverage pointing at `scoped-class/*` UCs. Their compiled output is
`registry/generated/compute.vm.json` (7 properties). The flow is
`docs/flows/scoped-class-lifecycle.md` — author → extend → compile → resolve.

For the **provider tier**, copy **`registry/classes/resource/compute/vm/cexample-cloud.yaml`**. It is the
worked case of an offer: `cpu` narrowed at a nested property, `memory` carrying a grouped
`supports` matrix a JSON Schema range cannot express, `networks` bounded by cardinality, and three
REQUIRED elements the provider adds because no portable intent carries them. Note what a provider
class does **not** carry: no `context`, no `spec_examples`, no `spec_constraints` — the provider tier
serves no portable spec surface.

## 5. Run the gates

From the repo root:

```
python3 tests/check_class_liskov.py
python3 registry/tools/generate_class_specs.py --check
python3 registry/tools/spec_coverage.py --check
```

A pass looks like:

- **check_class_liskov.py** — `N class(es) checked, 0 Liskov violation(s)` and exit 0 (no `FAIL [LSK-…`).
- **generate_class_specs.py --check** — one `ok (fresh)  <Type> → registry/generated/<Type>.json (N props)`
  line per Type Class, ending `N Type Class(es) compiled, 0 issue(s)`, exit 0. A `FAIL [GEN-001]` means
  the committed generated file is stale — rerun **without** `--check` to rewrite it, then commit.
- **spec_coverage.py --check** — your Class shows `✓ UC+example+flow`, `… 0 dangling`, exit 0.

`./scripts/signoff.sh` runs these with the full gate set before you open a PR.
